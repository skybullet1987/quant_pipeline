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


def test_fast_v2_order_signer_byte_exact_parity():
    from dataclasses import asdict
    import pytest
    try:
        from py_clob_client_v2.client import ClobClient
        from py_clob_client_v2.clob_types import OrderArgs
    except Exception:
        pytest.skip("py_clob_client_v2 not installed in this environment")
    from src.polymarket_research.polymarket_live_executor import FastV2OrderSigner

    test_pk = "0x4c0883a69102937d6231471b5dbb6204fe5129617082792ae468d01a3f362318"
    test_funder = "0x1111111111111111111111111111111111111111"
    test_tok = "580531616296768985464990134503"
    for sig_type in (0, 1, 2, 3):
        cli = ClobClient(
            host="https://clob.polymarket.com",
            chain_id=137,
            key=test_pk,
            signature_type=sig_type,
            funder=test_funder if sig_type != 0 else None,
        )
        cli._ClobClient__tick_sizes[test_tok] = "0.01"
        for neg_flag in (False, True):
            cli._ClobClient__neg_risk[test_tok] = neg_flag
            fast_signer = FastV2OrderSigner.from_clob_client(cli)
            assert fast_signer is not None
            oa = OrderArgs(token_id=test_tok, price=0.76, size=20.0, side="BUY")
            fast_ord = fast_signer.create_order(oa)
            assert fast_ord.tokenId == test_tok
            assert fast_ord.signature.startswith("0x")
            if sig_type == 3:
                assert len(fast_ord.signature) > 260
            else:
                assert len(fast_ord.signature) == 132
            sdk_exch = fast_signer._neg_exchange if neg_flag else fast_signer._std_exchange
            sdk_b = fast_signer._ExchangeOrderBuilderV2(
                sdk_exch, 137, cli.builder.signer, generate_salt=lambda: 424242, domain_version="2"
            )
            od = fast_signer._OrderDataV2(
                maker=fast_signer._maker_addr,
                tokenId=test_tok,
                makerAmount="15200000",
                takerAmount="20000000",
                side=fast_signer._Side.BUY,
                signer=fast_signer._signer_addr,
                signatureType=fast_signer._signature_type,
                timestamp="1700000123456",
                metadata=fast_signer._bytes32_zero_hex,
                builder=fast_signer._bytes32_zero_hex,
                expiration="0",
            )
            assert asdict(
                fast_signer.sign_v2_order_data(
                    token_id=test_tok,
                    maker_amount="15200000",
                    taker_amount="20000000",
                    side=fast_signer._Side.BUY,
                    neg_risk=neg_flag,
                    salt=424242,
                    timestamp="1700000123456",
                )
            ) == asdict(sdk_b.build_signed_order(od))


def test_presigned_ladder_near_max_share_delta_and_notional_cap():
    from src.polymarket_research.polymarket_live_executor import PreSignedOrderLadderCache

    cache = PreSignedOrderLadderCache(ttl_seconds=300.0)
    tok = "998877665544332211009988776655"
    cache.store_presigned_order(tok, 0.75, 22.0, {"shares": 22})
    hit = cache.get_presigned_order_near(tok, 0.75, 19.0, max_share_delta=3, max_notional_usd=17.0)
    assert hit == ({"shares": 22}, 22)
    cache.store_presigned_order(tok, 0.75, 22.0, {"shares": 22})
    miss = cache.get_presigned_order_near(tok, 0.75, 19.0, max_share_delta=3, max_notional_usd=16.0)
    assert miss is None


def test_bg_pool_isolates_readonly_gets_from_hot_post_pool():
    from unittest.mock import MagicMock
    from src.polymarket_research.polymarket_live_executor import _ThreadLocalClobHttpClient

    pool_cli = _ThreadLocalClobHttpClient(timeout=4.0, max_pool_size=8)
    created = []

    class _FakeCli:
        def __init__(self):
            self.is_closed = False
            created.append(self)

        def request(self, method="GET", url="", **kw):
            resp = MagicMock(status_code=200)
            resp.headers = {"cf-ray": "abc123-HEL", "Poly-RateLimit-Remaining": "99"}
            return resp

        def close(self):
            self.is_closed = True

    pool_cli._make_client = _FakeCli
    assert pool_cli.warm_pool(min_warm=4, max_idle_sec=0.0) == 4
    hot_sockets = list(pool_cli._pool.queue)
    assert len(hot_sockets) == 4
    assert pool_cli._bg_pool.qsize() == 0

    pool_cli.request("GET", "https://clob.polymarket.com/book?token_id=12345")
    assert pool_cli._pool.qsize() == 4
    assert list(pool_cli._pool.queue) == hot_sockets
    assert pool_cli._bg_pool.qsize() == 1
    assert pool_cli.get_last_response_meta().get("cf_ray") == "abc123-HEL"


def test_execute_atomic_dominance_box_batch_post_orders_zero_skew():
    from unittest.mock import MagicMock
    from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor

    ex = PolymarketLiveExecutor(dry_run=True)
    ex.dry_run = False
    ex.is_authenticated = True
    fake_cli = MagicMock()
    fake_cli.create_order.side_effect = lambda args, options=None: {"tok": args.token_id, "px": args.price, "sz": args.size}
    fake_cli.post_orders.return_value = [
        {"orderID": "0xBATCH_1", "status": "matched", "takingAmount": "15.0", "makingAmount": "6.90"},
        {"orderID": "0xBATCH_2", "status": "matched", "takingAmount": "15.0", "makingAmount": "7.20"},
    ]
    ex.client = fake_cli
    tok_a = "1" * 30
    tok_b = "2" * 30
    ex.prewarm_token_market_cache(tok_a, tick_size="0.01", neg_risk=False, fee_rate_bps=700, condition_id="0xc1")
    ex.prewarm_token_market_cache(tok_b, tick_size="0.01", neg_risk=False, fee_rate_bps=700, condition_id="0xc2")

    res = ex.execute_atomic_dominance_box(
        box_id="BOX_BATCH_1",
        leg_a_token_id=tok_a,
        leg_a_label="15M_UP",
        leg_a_limit_price=0.46,
        leg_b_token_id=tok_b,
        leg_b_label="5M_DOWN",
        leg_b_limit_price=0.48,
        shares=15,
        max_box_cost_net=0.985,
        parallel_dispatch=True,
    )
    assert res["success"] is True
    assert res["dispatch_mode"] == "BATCH_POST_ORDERS_FOK"
    assert res["inter_leg_skew_ms"] == 0.0
    assert fake_cli.post_orders.call_count == 1
    assert fake_cli.post_order.call_count == 0


def test_harvester_recorder_freshness_ram_short_circuit_and_expired_d1_slot_release(tmp_path, monkeypatch):
    from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester

    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", tmp_path / "st.json")
    h = PolymarketLiveHarvester(dry_run=True)

    now_t = time.time()
    fast_tick = tmp_path / "pm_fast_tick_BTC.json"
    fast_tick.write_text(json.dumps({"ts": now_t, "spot_px": 81000.0}), encoding="utf-8")
    monkeypatch.setenv("PM_FAST_TICK_DIR", str(tmp_path))
    monkeypatch.setenv("PM_TELEMETRY_DIR", str(tmp_path / "missing_telemetry_dir"))

    ok, age_s, detail = h.check_recorder_freshness("BTC", now_t)
    assert ok is True and age_s < 1.0 and "fast_tick_age=" in detail

    for idx in range(4):
        h.active_positions[f"EXP_BOX_{idx}_A"] = {
            "box_id": f"OLD_BOX_{idx}",
            "is_dominance_box": True,
            "candle_expiry_ts": now_t - 5.0,
            "status": "HOLDING_TO_MATURITY",
        }
    res_slot = h.maybe_execute_graduated_d1_box({
        "box_id": "NEW_BOX_AFTER_EXPIRY",
        "dedupe_key": "D1_BTC_SLOT_CHECK",
        "asset": "ZEC",
        "corridor_bps": 10.0,
        "leg_a_market_id": "m1",
        "leg_b_market_id": "m2",
        "leg_a_token_id": "1" * 30,
        "leg_b_token_id": "2" * 30,
    })
    assert res_slot["reason"] == "UNSUPPORTED_D1_ASSET:ZEC"


def test_weather_slate_dynamic_bucket_fee_accounting():
    from datetime import date
    from src.polymarket_research.weather_metar_engine import (
        WeatherBucket,
        WeatherEventSpec,
        evaluate_weather_event_slate,
    )

    buckets_zero = [
        WeatherBucket("m1", "c1", "<=10C", "q1", "t1", "n1", "C", float("-inf"), 10.0, fee_rate=0.0),
        WeatherBucket("m2", "c2", "11C", "q2", "t2", "n2", "C", 11.0, 11.0, fee_rate=0.0),
        WeatherBucket("m3", "c3", ">=12C", "q3", "t3", "n3", "C", 12.0, float("inf"), fee_rate=0.0),
    ]
    spec_zero = WeatherEventSpec(
        "ev1", "slug1", "tokyo-daily-weather", "Tokyo High", "RJTT", "Tokyo",
        35.55, 139.78, "Asia/Tokyo", date(2026, 10, 27), "HIGH", "C", "zero_fees", "2026-10-27T15:00:00Z",
        buckets=buckets_zero,
    )
    bucket_books = {
        "m1": {"ask_yes": 0.31, "ask_yes_shares": 100.0},
        "m2": {"ask_yes": 0.32, "ask_yes_shares": 100.0},
        "m3": {"ask_yes": 0.33, "ask_yes_shares": 100.0},
    }
    res_zero = evaluate_weather_event_slate(spec_zero, [0.33, 0.34, 0.33], bucket_books, max_underround_sum=0.97)
    assert res_zero["full_slate_arb"] is not None
    assert abs(res_zero["full_slate_arb"]["sum_asks"] - 0.96) < 1e-4

    for b in buckets_zero:
        b.fee_rate = 0.07
    res_fee = evaluate_weather_event_slate(spec_zero, [0.33, 0.34, 0.33], bucket_books, max_underround_sum=0.97)
    assert res_fee["full_slate_arb"] is None


def test_alpha124_ws_book_cache_snapshot_delta_and_single_scan_bypass(tmp_path, monkeypatch):
    import asyncio
    from src.polymarket_research import alpha_124_shadow_daemon as a124

    monkeypatch.setattr(a124, "STATE_FILE", tmp_path / "a124_state.json")
    monkeypatch.setattr(a124, "LEDGER_FILE", tmp_path / "a124_ledger.jsonl")

    d_live = a124.Alpha124ShadowDaemon(single_scan=False)
    now_t = time.time()
    d_live._apply_ws_book_snapshot(
        "TOK_WS_1",
        bids_raw=[{"price": "0.45", "size": "100"}],
        asks_raw=[{"price": "0.47", "size": "80"}],
        now_ts=now_t,
    )
    assert d_live._apply_ws_price_changes(
        "TOK_WS_1",
        changes=[{"price": "0.46", "size": "120", "side": "SELL"}],
        now_ts=now_t,
    ) is True
    # Live daemon serves fresh WS book in 0 HTTP calls
    bks = asyncio.run(d_live.fetch_books_batch(["TOK_WS_1"]))
    assert bks["TOK_WS_1"]["asks"][0]["price"] == "0.4600"
    # Delta on unseeded token must return False (never fabricate partial delta-only book)
    assert d_live._apply_ws_price_changes("UNSEEDED_TOK", [{"price": "0.50", "size": "10", "side": "BUY"}], now_t) is False


def test_user_ws_cache_open_orders_and_confirmed_fill_deltas():
    from src.polymarket_research.polymarket_ws_streams import PolymarketUserWsCache
    from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor

    fills_cb = []
    uws = PolymarketUserWsCache("k", "s", "p", on_fill_callback=lambda ev: fills_cb.append(ev))
    uws._connected = True
    uws._last_rx_mono = time.monotonic()

    # Unseeded WS cache must return None so caller performs initial REST reconciliation
    assert uws.get_open_orders_snapshot() is None

    uws.seed_open_orders([{"id": "OID_1", "asset_id": "TOK_1", "status": "LIVE", "original_size": "20", "size_matched": "0"}])
    snap1 = uws.get_open_orders_snapshot()
    assert snap1 is not None and len(snap1) == 1 and snap1[0]["id"] == "OID_1"

    # Placement adds open order; cancellation removes it immediately
    uws.process_ws_payload(json.dumps({
        "event_type": "order", "type": "PLACEMENT", "id": "OID_2", "asset_id": "TOK_2",
        "original_size": "15", "size_matched": "0", "status": "LIVE",
    }))
    assert {o["id"] for o in uws.get_open_orders_snapshot()} == {"OID_1", "OID_2"}

    uws.process_ws_payload(json.dumps({
        "event_type": "order", "type": "CANCELLATION", "id": "OID_1", "asset_id": "TOK_1",
        "original_size": "20", "size_matched": "0",
    }))
    assert {o["id"] for o in uws.get_open_orders_snapshot()} == {"OID_2"}

    # Trade MINED/CONFIRMED records token fill activity & share delta exactly once
    t_fill = time.time()
    uws.process_ws_payload(json.dumps({
        "event_type": "trade", "id": "TR_99", "status": "MINED", "asset_id": "TOK_2",
        "side": "BUY", "size": "15", "taker_order_id": "OID_2", "transaction_hash": "0xabc123",
    }), now_unix=t_fill)
    uws.process_ws_payload(json.dumps({
        "event_type": "trade", "id": "TR_99", "status": "CONFIRMED", "asset_id": "TOK_2",
        "side": "BUY", "size": "15", "taker_order_id": "OID_2", "transaction_hash": "0xabc123",
    }), now_unix=t_fill)
    assert uws.has_token_fill_since("TOK_2", t_fill - 1.0) is True
    assert abs(uws._confirmed_token_deltas["TOK_2"] - 15.0) < 1e-6
    assert len(fills_cb) == 2

    # Executor get_open_orders serves fresh WS snapshot with 0 REST calls
    ex = PolymarketLiveExecutor(dry_run=True)
    ex.dry_run = False
    ex.is_authenticated = True

    class _RealLikeClient:
        def __init__(self):
            self.calls = 0

        def get_open_orders(self):
            self.calls += 1
            return []

    cli = _RealLikeClient()
    ex.client = cli
    ex._user_ws_cache = uws
    res_oo = ex.get_open_orders(strict=True)
    assert len(res_oo) == 1 and res_oo[0]["id"] == "OID_2"
    assert cli.calls == 0


def test_chainlink_live_stream_18dec_boundary_twap_and_0s_strike():
    from src.polymarket_research.polymarket_ws_streams import PolymarketChainlinkLiveStream

    ticks_seen = []
    cl = PolymarketChainlinkLiveStream(on_tick=lambda sym, ts, px: ticks_seen.append((sym, ts, px)))
    b_ts = 1793152500  # exact 5m boundary
    for i in range(60):
        ts_ms = (b_ts - 59 + i) * 1000
        # Exact $100.50 in 18-decimal Chainlink integer format
        cl.process_ws_message(json.dumps({
            "topic": "crypto_prices_chainlink",
            "type": "update",
            "payload": {
                "symbol": "sol/usd",
                "timestamp": ts_ms,
                "full_accuracy_value": str(100500000000000000000),
                "value": 100.5,
            },
        }))
    tw = cl.get_boundary_twap_60s("SOL", b_ts)
    assert tw is not None and abs(tw - 100.5) < 1e-9
    assert cl.get_latest_spot("SOL", now_ts=float(b_ts) + 0.5) == 100.5
    assert len(cl.get_recent_samples("SOL", b_ts - 30)) >= 30
    assert len(ticks_seen) == 60


def test_live_phase3a_maker_rescue_fill_and_clean_ttl_cancel(tmp_path, monkeypatch):
    import asyncio
    from unittest.mock import MagicMock
    from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester
    from src.polymarket_research.polymarket_live_executor import CancelOrderResult

    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", tmp_path / "p3a_state.json")
    monkeypatch.setenv("PM_LIVE_PHASE3A_TTL_SEC", "0.25")
    h = PolymarketLiveHarvester(dry_run=True)
    h.dry_run = False
    h.enable_live_phase3a_maker_fallback = True
    h.get_usd_reference_spot_price = lambda _a: 81200.0

    # Case 1: 3.5s (0.25s test) TTL expires with 0 shares matched -> clean cancel, returns None
    h.executor.place_passive_maker_entry = MagicMock(return_value={
        "success": True, "orderID": "OID_P3A_EMPTY", "price": 0.79, "shares": 20.0,
    })
    h.executor.cancel_order = MagicMock(return_value=CancelOrderResult(
        {"canceled": ["OID_P3A_EMPTY"]}, order_id="OID_P3A_EMPTY", outcome="CANCELED", is_canceled=True, matched=0.0,
    ))
    h.executor.get_order_fill_summary = MagicMock(return_value={"matched": 0.0, "terminal": True})
    r_empty = asyncio.run(h._attempt_live_phase3a_maker_rescue(
        trade_id="TR_P3A_1", token_id="1" * 30, target_token="UP", asset_str="BTC",
        effective_notional=16.50, first_ask=0.81, first_bid=0.78, min_allowed_price=0.55,
        max_allowed_price=0.80, open_spot=81000.0, entry_spot_ref=81200.0, spot_denom="USD",
        tte=180.0, pre_cond_bal=0.0, book_snapshot={"asks": [{"price": "0.81", "size": "50"}], "bids": [{"price": "0.78", "size": "50"}]},
    ))
    assert r_empty is None
    assert h.executor.place_passive_maker_entry.call_args.kwargs["price"] == 0.79
    assert h.executor.cancel_order.call_count == 1

    # Case 2: Passive Maker-In fills within TTL -> promotes to 0%-fee OrderResult(success=True)
    h.executor.place_passive_maker_entry = MagicMock(return_value={
        "success": True, "orderID": "OID_P3A_FILL", "price": 0.79, "shares": 20.0,
    })
    h.executor.cancel_order = MagicMock(return_value=CancelOrderResult(
        {}, order_id="OID_P3A_FILL", outcome="FILLED", is_canceled=False, matched=20.0,
    ))
    h.executor.get_order_fill_summary = MagicMock(return_value={
        "matched": 20.0, "avg_price": 0.79, "terminal": True, "trade_ids": ["T_MKR_1"], "tx_hashes": ["0xdef"],
    })
    r_fill = asyncio.run(h._attempt_live_phase3a_maker_rescue(
        trade_id="TR_P3A_2", token_id="1" * 30, target_token="UP", asset_str="BTC",
        effective_notional=16.50, first_ask=0.81, first_bid=0.78, min_allowed_price=0.55,
        max_allowed_price=0.80, open_spot=81000.0, entry_spot_ref=81200.0, spot_denom="USD",
        tte=180.0, pre_cond_bal=0.0, book_snapshot={"asks": [{"price": "0.81", "size": "50"}], "bids": [{"price": "0.78", "size": "50"}]},
    ))
    assert r_fill is not None and r_fill.success is True
    assert r_fill.mode == "LIVE_PHASE3A_MAKER_IN"
    assert r_fill.fee_usd == 0.0 and r_fill.size == 20.0 and r_fill.price == 0.79


def test_mixed_itode_4h_sequencing_and_clob_market_ws_recycle_trigger(tmp_path):
    from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor
    from src.polymarket_research.polymarket_ws_streams import PolymarketClobMarketWsTracker

    # 1. Mixed-itode 4h D1 box: 15m/5m (itode=True) leg MUST execute as leg_1 even when 4h leg is cheaper/thinner!
    ex = PolymarketLiveExecutor(dry_run=True, ledger_path=tmp_path / "m4h.jsonl")
    res_4h = ex.execute_atomic_dominance_box(
        box_id="BOX_4H_SEQ",
        leg_a_token_id="tok_4h_up",
        leg_a_label="4H_UP",
        leg_a_limit_price=0.35,
        leg_b_token_id="tok_15m_dn",
        leg_b_label="15M_DOWN",
        leg_b_limit_price=0.60,
        shares=20,
        max_box_cost_net=0.985,
        leg_a_avail_shares=50.0,   # 4h leg is BOTH thinner AND cheaper, yet 15m leg MUST still go first!
        leg_b_avail_shares=200.0,
        fee_rate_a=0.0,
        fee_rate_b=0.07,
    )
    assert res_4h["success"] is True
    assert res_4h["leg_1"]["token_id"] == "tok_15m_dn"
    assert res_4h["leg_2"]["token_id"] == "tok_4h_up"

    # 2. Harvester active-position WS tracker fires immediate recycle callback when bid >= $0.985
    hits = []
    tok_d1 = "9" * 30
    trk = PolymarketClobMarketWsTracker(recycle_bid_trigger=0.985, on_urgent_bid=lambda aid, bb: hits.append((aid, bb)))
    trk.set_desired_tokens([tok_d1])
    trk.process_ws_payload(json.dumps({
        "asset_id": tok_d1,
        "bids": [{"price": "0.97", "size": "40"}],
        "asks": [{"price": "0.99", "size": "40"}],
    }))
    assert hits == []
    trk.process_ws_payload(json.dumps({
        "event_type": "price_change",
        "price_changes": [{"asset_id": tok_d1, "price": "0.986", "size": "35", "side": "BUY"}],
    }))
    assert len(hits) == 1 and hits[0][0] == tok_d1 and abs(hits[0][1] - 0.986) < 1e-6
    bk = trk.get_book(tok_d1)
    assert bk is not None and float(bk["bids"][0]["price"]) == 0.986




