import json
import threading
import time

from src.polymarket_research import latency_trace as lt
from src.polymarket_research.polymarket_live_executor import _HOT_DISPATCH_ACTIVE


def test_active_counter_overlapping_dispatches():
    c = lt.ActiveCounter()
    c.enter()
    c.enter()
    assert c.is_set()
    c.leave()  # first finisher must NOT mark the hot path idle
    assert c.is_set() and c.count == 1
    c.leave()
    assert not c.is_set()
    c.leave()  # never goes negative
    assert c.count == 0


def test_active_counter_threadsafe():
    c = lt.ActiveCounter()

    def work():
        for _ in range(1000):
            c.enter()
            c.leave()

    ts = [threading.Thread(target=work) for _ in range(8)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert c.count == 0


def test_executor_uses_refcounted_flag():
    assert hasattr(_HOT_DISPATCH_ACTIVE, "enter") and hasattr(_HOT_DISPATCH_ACTIVE, "leave")


def test_trace_emit_writes_jsonl(tmp_path, monkeypatch):
    out = tmp_path / "trace.jsonl"
    monkeypatch.setenv("PM_LATENCY_TRACE_FILE", str(out))
    monkeypatch.setenv("PM_LATENCY_TRACE", "1")
    t = lt.LatencyTrace(sleeve="TEST", asset="BTC")
    t.stamp("trigger_consumed")
    time.sleep(0.002)
    t.stamp("dispatch_call")
    t.emit(outcome="posted", sign_ms=1.5)
    lt.flush(5.0)
    deadline = time.time() + 5
    while not out.exists() and time.time() < deadline:
        time.sleep(0.05)
    rec = json.loads(out.read_text().strip().splitlines()[0])
    assert rec["sleeve"] == "TEST" and rec["outcome"] == "posted"
    assert rec["stamps_rel_ms"]["dispatch_call"] > rec["stamps_rel_ms"]["trigger_consumed"]
    assert rec["attempt"] == 0


def test_trace_disabled_is_noop(tmp_path, monkeypatch):
    out = tmp_path / "off.jsonl"
    monkeypatch.setenv("PM_LATENCY_TRACE_FILE", str(out))
    monkeypatch.setenv("PM_LATENCY_TRACE", "0")
    lt.LatencyTrace(a=1).emit()
    time.sleep(0.4)
    assert not out.exists()


def test_emit_never_raises_on_unserialisable():
    class Weird:
        def __str__(self):
            raise RuntimeError("boom")

    lt.LatencyTrace(x=Weird()).emit()  # must not propagate


def test_l2_orderbook_directional_age_ask_preservation():
    from src.polymarket_research.polymarket_terminal_recorder import L2OrderBook

    book = L2OrderBook("TOK_TEST")
    book.apply_snapshot(
        bids=[{"price": "0.68", "size": "100"}],
        asks=[{"price": "0.70", "size": "100"}],
    )
    # Age the resting quotes by 500ms
    t_initial = book.last_best_ask_change_ts - 0.500
    book.last_best_ask_change_ts = t_initial
    book.last_best_bid_change_ts = t_initial

    # 1. Maker improves ask downward ($0.70 -> $0.69) and bid upward ($0.68 -> $0.685):
    # Must NOT reset last_best_ask_change_ts or last_best_bid_change_ts!
    book.apply_price_changes([
        {"price": "0.69", "size": "50", "side": "SELL"},
        {"price": "0.685", "size": "50", "side": "BUY"},
    ])
    assert book.last_best_ask_change_ts == t_initial
    assert book.last_best_bid_change_ts == t_initial

    # 2. MM pulls/cancels the improved ask ($0.69 -> $0.70) and bid ($0.685 -> $0.68):
    # Adverse move MUST reset both timestamps!
    book.apply_price_changes([
        {"price": "0.69", "size": "0", "side": "SELL"},
        {"price": "0.685", "size": "0", "side": "BUY"},
    ])
    assert book.last_best_ask_change_ts > t_initial
    assert book.last_best_bid_change_ts > t_initial


def test_evaluate_shock_uses_true_usd_dist_in_composite_edge_score(tmp_path, monkeypatch):
    import asyncio
    from src.polymarket_research.polymarket_live_harvester import (
        PolymarketLiveHarvester,
        compute_composite_edge_score,
    )

    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", tmp_path / "harv_state.json")
    h = PolymarketLiveHarvester(dry_run=True)

    # Raw USDT candle_distance_pct is 0.06% (< 0.09%), which on its own triggers
    # "Heavy L1 ask wall against thin cushion" when obi_l1 = -0.70.
    # However, authoritative True-USD Chainlink open is 2340.00 and USD spot is 2343.51 (+0.15% cushion >= 0.09%).
    raw_shock = {
        "shock_id": "SHK_USD_EDGE_1",
        "event_id": "SHK_USD_EDGE_1",
        "t0_unix": time.time(),
        "asset": "ETH",
        "horizon": "15m",
        "candle_interval": "15m",
        "resolution_source": "https://data.chain.link/streams/eth-usd",
        "market_id": "MKT_ETH_15M_USD",
        "title": "Ethereum Up or Down - October 27, 4:30PM-4:45PM ET",
        "seconds_to_expiry": 240.0,
        "shock_direction": "BUY",
        "shock_ofi": 0.85,
        "shock_volume_100ms": 1_200_000.0,
        "delta_basis_100ms": 1.5,
        "candle_distance_pct": 0.06,  # Unadjusted USDT distance (< 0.09%)
        "authoritative_chainlink_open": 2340.00,
        "chainlink_proxy_spot": 2343.51,  # True USD distance = +0.15% (>= 0.09%)
        "coinbase_spot": 2343.51,
        "spot_at_t0": 2345.00,
        "candle_open_spot": 2343.60,
        "pre_shock_features_t0": {
            "UP": {
                "token_id": "0xTOK_ETH_UP_USD",
                "age_ask_ms": 400.0,
                "obi_l1": -0.70,
                "obi_depth": 0.10,
                "spread": 0.01,
                "best_ask": 0.65,
                "vwap_$25": 0.65,
                "raw_top_asks": [[0.65, 200.0]],
                "raw_top_bids": [[0.64, 200.0]],
            }
        },
    }
    # Confirm unadjusted shock would be vetoed by L1 ask wall check:
    assert compute_composite_edge_score(raw_shock)["veto"] is True

    # Confirm evaluate_shock_and_execute resolves True-USD dist_pct (+0.15%) BEFORE calling compute_composite_edge_score:
    seen_edge_shocks = []
    orig_edge_fn = compute_composite_edge_score

    def _spy_edge(shk):
        seen_edge_shocks.append(dict(shk))
        return orig_edge_fn(shk)

    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.compute_composite_edge_score", _spy_edge)
    asyncio.run(h.evaluate_shock_and_execute(raw_shock))
    assert len(seen_edge_shocks) == 1
    assert seen_edge_shocks[0]["candle_distance_pct"] > 0.14
    assert orig_edge_fn(seen_edge_shocks[0])["veto"] is False

