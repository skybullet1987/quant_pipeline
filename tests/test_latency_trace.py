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


def test_warm_pool_never_drains_lifo_pool_during_refresh():
    from unittest.mock import MagicMock
    from src.polymarket_research.polymarket_live_executor import _ThreadLocalClobHttpClient

    pool_cli = _ThreadLocalClobHttpClient(timeout=4.0, max_pool_size=8)
    min_qsize_observed = []
    created = []

    class _FakeCli:
        def __init__(self):
            self.is_closed = False
            self.calls = 0
            created.append(self)

        def request(self, method="GET", url="", **kw):
            if len(created) == 4 and self.calls >= 1:
                # During refresh of an already-populated 4-socket pool, >=3 hot sockets MUST remain in _pool!
                min_qsize_observed.append(pool_cli._pool.qsize())
            self.calls += 1
            return MagicMock(status_code=200)

        def close(self):
            self.is_closed = True

    pool_cli._make_client = _FakeCli
    assert pool_cli.warm_pool(min_warm=4, max_idle_sec=0.0) == 4
    assert len(created) == 4
    # Refresh all 4 sockets (max_idle_sec=0.0 forces GET on each) and verify _pool was NEVER drained:
    assert pool_cli.warm_pool(min_warm=4, max_idle_sec=0.0) == 4
    assert min_qsize_observed and min(min_qsize_observed) >= 3
    assert len(created) == 4


def test_live_15m_instantaneous_usd_spot_and_85c_fak_buffer(tmp_path, monkeypatch):
    import asyncio
    from unittest.mock import MagicMock
    from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester

    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", tmp_path / "live_st.json")
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.RESOLUTIONS_FILE", tmp_path / "live_res.jsonl")
    h = PolymarketLiveHarvester(ticket_notional=16.50, dry_run=True, dynamic_sizing=True)
    h.dry_run = False
    h.executor.dry_run = False
    h.state_file = tmp_path / "live_st.json"
    h.poll_onchain_redemptions = lambda: None
    h.executor.auth_mode = "AUTHENTICATED_L2"
    h.executor.is_authenticated = True
    h.executor.is_heartbeat_healthy = lambda: True
    h.executor.get_collateral_balance = lambda *a, **kw: 120.38
    h._last_known_collateral = 120.38
    h.check_recorder_freshness = lambda asset, now_t: (True, 0.05, "OK")

    dispatched = []

    async def _mock_snipe(**kw):
        dispatched.append(dict(kw))
        return MagicMock(success=False, mode="FAK_KILLED_NO_MATCH", error="no match", details={"fak_killed": True})

    h.executor.execute_snipe_order_async = _mock_snipe
    now_t = time.time()
    real_tok_up = "112233445566778899001122334455"
    real_tok_dn = "580531616296768985464990134503"

    # 1. Replay 23:07:09 UTC (BTC 15m UP @ $0.79, cl_spot=+0.0710% / z=0.83, lagging 60s TWAP=+0.0285%) -> MUST DISPATCH!
    shk_2307 = {
        "shock_id": "SHK_230709",
        "event_id": "SHK_230709",
        "market_id": "6280100",
        "condition_id": "0x6280100",
        "t0_unix": now_t,
        "title": "Bitcoin Up or Down - October 27, 7:00PM-7:15PM ET",
        "asset": "BTC",
        "horizon": "15m",
        "candle_interval": "15m",
        "resolution_source": "https://data.chain.link/streams/btc-usd",
        "seconds_to_expiry": 470.3,
        "shock_direction": "BUY",
        "shock_ofi": 1.0,
        "shock_volume_100ms": 1_800_000.0,
        "delta_basis_100ms": 1.2,
        "candle_sigma": 0.0012,
        "candle_distance_pct": 0.0710,
        "authoritative_chainlink_open": 80795.0802,
        "chainlink_proxy_spot": 80852.4591,
        "coinbase_spot": 80852.46,
        "chainlink_twap_60s": 80818.10,  # Lagging 60s TWAP (+0.0285%) must NOT erase the +0.0710% shock!
        "spot_at_t0": 80961.29,
        "candle_open_spot": 80905.00,
        "fee_metadata": {"condition_id": "0x6280100", "fee_rate_market": 0.07, "fee_exponent": 1.0},
        "pre_shock_features_t0": {
            "UP": {
                "token_id": real_tok_up,
                "best_bid": 0.78,
                "best_ask": 0.79,
                "spread": 0.01,
                "book_timestamp": now_t - 0.05,
                "age_book_ms": 50.0,
                "age_ask_ms": 11192.2,
                "obi_l1": 0.672,
                "raw_top_asks": [[0.79, 200.0]],
                "raw_top_bids": [[0.78, 200.0]],
            }
        },
    }
    asyncio.run(h.evaluate_shock_and_execute(shk_2307))
    assert len(dispatched) >= 1, "23:07:09 BTC 15m UP @ $0.79 must NOT be killed by lagging 60s TWAP!"

    # 2. Replay 23:23:51 UTC (BTC 15m DOWN @ $0.85, z_strike=1.23) -> MUST dispatch with >= $0.86 FAK limit buffer (NOT clamped to $0.85)!
    dispatched.clear()
    shk_2323 = {
        "shock_id": "SHK_232351",
        "event_id": "SHK_232351",
        "market_id": "6280299",
        "condition_id": "0x6280299",
        "t0_unix": now_t,
        "title": "Bitcoin Up or Down - October 27, 7:15PM-7:30PM ET",
        "asset": "BTC",
        "horizon": "15m",
        "candle_interval": "15m",
        "resolution_source": "https://data.chain.link/streams/btc-usd",
        "seconds_to_expiry": 368.9,
        "shock_direction": "SELL",
        "shock_ofi": -1.0,
        "shock_volume_100ms": 2_000_000.0,
        "delta_basis_100ms": -1.5,
        "candle_sigma": 0.00105,
        "candle_distance_pct": -0.0836,
        "authoritative_chainlink_open": 80822.8680,
        "chainlink_proxy_spot": 80755.3244,
        "coinbase_spot": 80755.32,
        "chainlink_twap_60s": 80757.20,
        "spot_at_t0": 80873.90,
        "candle_open_spot": 80940.00,
        "fee_metadata": {"condition_id": "0x6280299", "fee_rate_market": 0.07, "fee_exponent": 1.0},
        "pre_shock_features_t0": {
            "DOWN": {
                "token_id": real_tok_dn,
                "best_bid": 0.84,
                "best_ask": 0.85,
                "spread": 0.01,
                "book_timestamp": now_t - 0.05,
                "age_book_ms": 56.0,
                "age_ask_ms": 4433.8,
                "obi_l1": 0.706,
                "raw_top_asks": [[0.85, 180.0], [0.86, 180.0]],
                "raw_top_bids": [[0.84, 250.0]],
            }
        },
    }
    asyncio.run(h.evaluate_shock_and_execute(shk_2323))
    assert len(dispatched) >= 1
    assert dispatched[0]["target_price"] >= 0.86, f"Expected >= $0.86 FAK buffer on $0.85 ask, got {dispatched[0]['target_price']}"


