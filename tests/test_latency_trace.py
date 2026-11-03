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
    # Age the resting quotes + per-level birth timestamps by 500ms
    t_initial = book.last_best_ask_change_ts - 0.500
    book.last_best_ask_change_ts = t_initial
    book.last_best_bid_change_ts = t_initial
    book._ask_birth_ts[0.70] = t_initial
    book._bid_birth_ts[0.68] = t_initial

    # 1. Retail micro-nibble (<25% size change) on resting $0.70 ask / $0.68 bid MUST preserve birth age:
    book.apply_price_changes([
        {"price": "0.70", "size": "90", "side": "SELL"},
        {"price": "0.68", "size": "90", "side": "BUY"},
    ])
    assert book.last_best_ask_change_ts == t_initial
    assert book.last_best_bid_change_ts == t_initial

    # 2. Institutional >=25% reload or new price level resets birth timestamp (> t_initial):
    book.apply_price_changes([
        {"price": "0.70", "size": "150", "side": "SELL"},
        {"price": "0.68", "size": "150", "side": "BUY"},
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


def test_fast_l2_headers_and_zero_hop_async_post_order(monkeypatch):
    import asyncio
    import base64
    import httpx
    import pytest
    try:
        from py_clob_client_v2.client import ClobClient
        from py_clob_client_v2.clob_types import ApiCreds, OrderArgsV2, OrderType, PartialCreateOrderOptions, RequestArgs
        from py_clob_client_v2.exceptions import PolyApiException
        from py_clob_client_v2.headers.headers import create_level_2_headers
    except Exception:
        pytest.skip("py_clob_client_v2 not installed in this environment")
    from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor

    test_pk = "0x4c0883a69102937d6231471b5dbb6204fe5129617082792ae468d01a3f362318"
    test_secret = base64.urlsafe_b64encode(b"0123456789abcdef0123456789abcdef").decode("ascii")
    creds = ApiCreds(api_key="test-key-wave3", api_secret=test_secret, api_passphrase="test-passphrase")
    cli = ClobClient(host="https://clob.polymarket.com", chain_id=137, key=test_pk, creds=creds, signature_type=0)
    tok = "776655443322110099887766554433"
    cli._ClobClient__tick_sizes[tok] = "0.01"
    cli._ClobClient__neg_risk[tok] = False

    ex = PolymarketLiveExecutor(dry_run=True)
    ex.dry_run = False
    ex.is_authenticated = True
    ex.client = cli
    ex._init_fast_l2_headers_cache(creds)
    assert ex._fast_l2_ready is True

    # 1. Byte-exact HMAC L2 header parity against py_clob_client_v2
    body_s = '{"order":{"salt":99},"owner":"test-key-wave3","orderType":"FAK","deferExec":true,"postOnly":false}'
    ref_h = create_level_2_headers(
        cli.signer, creds, RequestArgs(method="POST", request_path="/order", body={}, serialized_body=body_s), timestamp=1761700000
    )
    fast_h = ex._build_fast_l2_headers("POST", "/order", body_s, ts_override=1761700000)
    for k in ("POLY_ADDRESS", "POLY_SIGNATURE", "POLY_TIMESTAMP", "POLY_API_KEY", "POLY_PASSPHRASE"):
        assert fast_h[k] == ref_h[k]

    # 2. Zero-hop async POST /order with pre-signed ladder hit (200 matched + 400 FAK kill)
    ex.prewarm_token_market_cache(tok, tick_size="0.01", neg_risk=False, fee_rate_bps=700, condition_id="0xabc")
    signed_ord = cli.create_order(
        OrderArgsV2(price=0.76, size=20.0, side="BUY", token_id=tok),
        PartialCreateOrderOptions(tick_size="0.01", neg_risk=False, version=2),
    )
    ex.order_ladder_cache.store_presigned_order(tok, 0.76, 20.0, signed_ord, tick_size="0.01", neg_risk=False)

    seen_requests = []

    def _mock_handler(request: httpx.Request) -> httpx.Response:
        seen_requests.append(request)
        if len(seen_requests) == 1:
            return httpx.Response(
                200,
                headers={"cf-ray": "ray999-ARN", "Content-Type": "application/json"},
                json={"orderID": "0xZEROHOP_1", "status": "matched", "takingAmount": "20.0", "makingAmount": "15.20"},
            )
        return httpx.Response(
            400,
            headers={"cf-ray": "ray999-ARN", "Content-Type": "application/json"},
            json={
                "error": "no orders found to match with FAK order. FAK orders are partially filled or killed if no match is found.",
                "orderID": "0xFAK_KILL_1",
            },
        )

    async def _run_zero_hop_checks():
        ex._hot_order_async_client = httpx.AsyncClient(transport=httpx.MockTransport(_mock_handler))
        ex._hot_order_async_loop = asyncio.get_running_loop()
        ex._force_native_async_post = True
        assert ex._can_use_native_async_post_order() is True

        st1 = {}
        hop1 = await ex._sign_and_post_async_zero_hop(
            tok, 0.76, 20.0, "BUY", getattr(OrderType, "FAK", OrderType.FOK),
            PartialCreateOrderOptions(tick_size="0.01", neg_risk=False, version=2), st1, 16.50,
        )
        assert hop1["cache_hit"] is True
        assert hop1["thread_hop_ms"] == 0.0
        assert hop1["cf_ray"] == "ray999-ARN"
        assert hop1["post_resp"]["orderID"] == "0xZEROHOP_1"
        assert st1["submitted"] is True
        assert seen_requests[0].headers["POLY_API_KEY"] == "test-key-wave3"

        st2 = {}
        with pytest.raises(PolyApiException) as exc_info:
            await ex._sign_and_post_async_zero_hop(
                tok, 0.76, 20.0, "BUY", getattr(OrderType, "FAK", OrderType.FOK),
                PartialCreateOrderOptions(tick_size="0.01", neg_risk=False, version=2), st2, 16.50,
            )
        assert exc_info.value.status_code == 400
        assert st2["submitted"] is True
        assert st2["thread_hop_ms"] == 0.0
        assert st2["cf_ray"] == "ray999-ARN"
        await ex.close_async()

    asyncio.run(_run_zero_hop_checks())


def test_active_warmed_token_furthest_expiry_eviction_and_precursor_ipc(tmp_path, monkeypatch):
    import ast
    import asyncio
    from pathlib import Path
    from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester

    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", tmp_path / "w3_state.json")
    h = PolymarketLiveHarvester(dry_run=True)
    now_u = time.time()

    # Active 15m UP/DOWN tokens expiring in ~300s MUST survive even when 18 future candles are registered!
    active_up = "ACTIVE_15M_UP"
    active_dn = "ACTIVE_15M_DN"
    h._register_active_warmed_token(active_up, now_u + 300.0)
    h._register_active_warmed_token(active_dn, now_u + 300.0)
    for i in range(18):
        h._register_active_warmed_token(f"FUTURE_TOK_{i}", now_u + 900.0 + i * 300.0)

    reg = h._active_warmed_token_expiries
    assert len(reg) == 12
    assert active_up in reg and active_dn in reg
    assert "FUTURE_TOK_17" not in reg and "FUTURE_TOK_10" not in reg

    # Precursor IPC touches hot async CLOB socket with 1.5s debounce
    touched = []

    async def _fake_touch(max_idle=5.5):
        touched.append(max_idle)
        return True

    h.dry_run = False
    h.executor.touch_hot_async_clob_socket = _fake_touch

    async def _run_precursor():
        h._handle_prewarm_ipc_signal()
        h._handle_prewarm_ipc_signal()  # debounced (<1.5s)
        await asyncio.sleep(0.02)

    asyncio.run(_run_precursor())
    assert touched == [1.5]

    # Verify compression=None is set on every websockets.connect call across hot WS modules
    repo_root = Path(__file__).resolve().parent.parent
    for rel in ("src/polymarket_research/polymarket_ws_streams.py", "src/polymarket_research/polymarket_terminal_recorder.py"):
        tree = ast.parse((repo_root / rel).read_text(encoding="utf-8"))
        ws_calls = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "connect"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "websockets"
        ]
        assert len(ws_calls) >= 3, f"Expected websockets.connect calls in {rel}"
        for call in ws_calls:
            comp_kws = [kw for kw in call.keywords if kw.arg == "compression"]
            assert len(comp_kws) == 1 and isinstance(comp_kws[0].value, ast.Constant) and comp_kws[0].value.value is None, (
                f"Missing compression=None in {rel} line {call.lineno}"
            )


def test_fast_trigger_consumer_zero_hol_blocking_under_supervision_stall(tmp_path, monkeypatch):
    """Kaizen #1: @polymarket_shock_notify consumer MUST wake and dispatch in <25ms even while
    check_resolutions_and_manage_positions is mid-await on a 350ms REST/RPC stall."""
    import asyncio
    from collections import deque
    from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester

    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", tmp_path / "hol_state.json")
    trig_file = tmp_path / "live_shock_triggers.jsonl"
    trig_file.write_text("", encoding="utf-8")
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.TRIGGER_FILE", trig_file)

    h = PolymarketLiveHarvester(dry_run=True)
    h._fast_trigger_lines = deque(maxlen=512)
    h._triggers_scanned_count = 0

    consumed_latencies_ms = []
    supervision_finished = False

    async def _slow_supervision():
        nonlocal supervision_finished
        await asyncio.sleep(0.35)
        supervision_finished = True

    async def _mock_eval(shock):
        lag_ms = (time.perf_counter() - float(shock["_t0_perf"])) * 1000.0
        consumed_latencies_ms.append((shock["shock_id"], lag_ms, supervision_finished))

    h.evaluate_shock_and_execute = _mock_eval

    async def _run_hol_test():
        fast_ev = asyncio.Event()
        sup_ev = asyncio.Event()
        with open(trig_file, "rb") as fp:
            h.last_trigger_file_pos = 0
            consumer = asyncio.create_task(h._fast_trigger_consumer_loop(fast_ev, fp, sup_ev))
            sup_task = asyncio.create_task(_slow_supervision())

            # Wait 40ms so supervision is firmly mid-await on its 350ms I/O stall
            await asyncio.sleep(0.04)
            assert supervision_finished is False

            t_push = time.perf_counter()
            payload = {
                "shock_id": "SHK_KAIZEN_HOL_1",
                "market_id": "999001",
                "asset": "BTC",
                "t0_unix": time.time(),
                "_t0_perf": t_push,
            }
            h._fast_trigger_lines.append(json.dumps(payload))
            fast_ev.set()

            # Yield briefly (~5ms) while slow supervision STILL has ~300ms remaining
            await asyncio.sleep(0.01)
            assert len(consumed_latencies_ms) == 1, "Shock trigger was head-of-line blocked by supervision!"
            shk_id, lag_ms, sup_done_at_dispatch = consumed_latencies_ms[0]
            assert shk_id == "SHK_KAIZEN_HOL_1"
            assert sup_done_at_dispatch is False, "Consumer waited for 350ms supervision instead of running concurrently!"
            assert lag_ms < 25.0, f"Expected sub-millisecond wakeup, got {lag_ms:.2f}ms"
            assert h._triggers_scanned_count == 1

            # Also verify disk fallback (trigger_fp) while supervision is still in flight
            t_disk = time.perf_counter()
            disk_payload = {
                "shock_id": "SHK_KAIZEN_DISK_2",
                "market_id": "999002",
                "asset": "BTC",
                "t0_unix": time.time(),
                "_t0_perf": t_disk,
            }
            with open(trig_file, "ab") as wf:
                wf.write((json.dumps(disk_payload) + "\n").encode("utf-8"))
            fast_ev.set()
            await asyncio.sleep(0.01)
            assert len(consumed_latencies_ms) == 2
            assert consumed_latencies_ms[1][0] == "SHK_KAIZEN_DISK_2"
            assert consumed_latencies_ms[1][2] is False
            assert h._triggers_scanned_count == 2

            h._shutdown_requested = True
            fast_ev.set()
            await asyncio.gather(consumer, sup_task)
            assert sup_ev.is_set()

    asyncio.run(_run_hol_test())


def test_shock_attempt_speed_and_gate_classification(tmp_path, monkeypatch):
    # 1. Flight speed miss: FOK sent @ $0.73, MM repriced post_ask -> $0.77 during flight
    r_flight = lt.classify_shock_attempt({
        "asset": "BTC", "horizon": "1h", "side": "BUY", "target_token": "UP",
        "path_type": "TAKER_FOK", "stage_outcome": "FAK_KILLED",
        "t0_ask": 0.72, "eval_ask": 0.72, "target_px": 0.73, "post_ask": 0.77,
        "exch_lag_ms": 18.0, "ipc_ms": 1.4, "sign_ms": 0.04, "http_ms": 62.0, "presign_hit": True,
    })
    assert r_flight["side"] == "UP"
    assert r_flight["speed_verdict"] == "TOO_SLOW_FLIGHT"
    assert r_flight["is_speed_miss"] is True
    assert r_flight["is_order_attempt"] is True
    assert r_flight["ask_drift_flight_c"] == 5.0
    assert "TOO SLOW (Flight)" in r_flight["diagnosis"]

    # 2. Pre-Eval speed miss: Ask jumped $0.71 -> $0.78 (+7c > $0.76 cap) before dispatch
    r_pre = lt.classify_shock_attempt({
        "asset": "SOL", "horizon": "1h", "side": "DOWN", "path_type": "PRE_EVAL",
        "gate_code": "TAKER_ASYMMETRY_VETO", "t0_ask": 0.71, "eval_ask": 0.78, "cap_px": 0.76,
        "book_age_ms": 90.0, "ipc_ms": 4.2,
    })
    assert r_pre["speed_verdict"] == "TOO_SLOW_PRE_EVAL"
    assert r_pre["is_speed_miss"] is True
    assert r_pre["ask_drift_pre_c"] == 7.0

    # 3. Already Priced In (NOT a speed miss): Book already sat @ $0.88 for 6.5s before shock
    r_priced = lt.classify_shock_attempt({
        "asset": "BTC", "horizon": "1h", "side": "UP", "path_type": "PRE_EVAL",
        "gate_code": "TAKER_ASYMMETRY_VETO", "t0_ask": 0.88, "eval_ask": 0.88, "cap_px": 0.76,
        "book_age_ms": 6500.0, "ipc_ms": 1.1,
    })
    assert r_priced["speed_verdict"] == "ALREADY_PRICED_IN"
    assert r_priced["is_speed_miss"] is False
    assert "not a speed miss" in r_priced["diagnosis"]

    # 4. Maker Left Behind: Phase 3A 0%-fee Maker @ $0.76 expired while post_ask ran -> $0.81
    r_mkr = lt.classify_shock_attempt({
        "asset": "SOL", "horizon": "1h", "side": "UP", "path_type": "MAKER_P3A",
        "stage_outcome": "MAKER_TTL_EXPIRED", "eval_ask": 0.77, "target_px": 0.76, "post_ask": 0.81,
        "ttl_ms": 8000.0, "http_ms": 48.0,
    })
    assert r_mkr["speed_verdict"] == "LEFT_BEHIND_MAKER"
    assert r_mkr["is_speed_miss"] is True
    assert r_mkr["is_order_attempt"] is True

    # 5. Mid-TTL Adverse Shield save & Feed Lag
    r_shld = lt.classify_shock_attempt({
        "asset": "BTC", "horizon": "15m", "side": "DOWN", "path_type": "MAKER_P3A",
        "stage_outcome": "SHIELD_ADVERSE_TTL", "target_px": 0.71, "ttl_ms": 1400.0,
    })
    assert r_shld["speed_verdict"] == "SHIELD_SAVED"
    assert r_shld["is_speed_miss"] is False

    r_lag = lt.classify_shock_attempt({
        "asset": "BTC", "horizon": "1h", "side": "UP", "path_type": "PRE_EVAL",
        "gate_code": "EXCHANGE_LAG_REJECT", "exch_lag_ms": 1420.0, "gate_detail": "Binance lag 1420ms > 1200ms",
    })
    assert r_lag["speed_verdict"] == "TOO_SLOW_FEED_LAG"
    assert r_lag["is_speed_miss"] is True

    # 6. End-to-end non-blocking JSONL emission from LatencyTrace
    sf_out = tmp_path / "shock_attempt_forensics.jsonl"
    monkeypatch.setenv("PM_SHOCK_ATTEMPT_FILE", str(sf_out))
    monkeypatch.setenv("PM_LATENCY_TRACE", "1")
    tr = lt.LatencyTrace(
        shock_id="SHK_SF_1", trade_id="LIVE_999_1_UP", asset="BTC", horizon="1h",
        side="BUY", target_token="UP", path_type="TAKER_FOK", stage_outcome="FILLED_TAKER",
        target_px=0.70, fill_px=0.695, notional_usd=18.5, sign_ms=0.05, clob_http_post_ms=54.0,
        trigger_to_consume_wall_ms=1.2, dry_run=True,
    )
    tr.stamp("trigger_consumed")
    tr.stamp("dispatch_call")
    emitted = lt.emit_shock_attempt_from_trace(tr, {"t0_unix": time.time(), "exchange_event_ts_ms": time.time() * 1000.0 - 15.0})
    assert emitted is not None and emitted["speed_verdict"] == "FILLED" and emitted["side"] == "UP"
    lt.flush(5.0)
    assert sf_out.exists()
    persisted = json.loads(sf_out.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert persisted["trade_id"] == "LIVE_999_1_UP"
    assert persisted["speed_verdict"] == "FILLED"


def test_kaizen2_pre_dispatch_hot_shield_and_batch_prewarm(tmp_path, monkeypatch, caplog):
    import asyncio
    import logging
    from unittest.mock import MagicMock
    from src.polymarket_research import polymarket_live_executor as ex_mod
    from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester

    # 1. Batch freshness filter: 2,160 fresh orders checked in 1 lock acquisition (< 5 ms) + 1 popped order detected
    cache = ex_mod.PreSignedOrderLadderCache(ttl_seconds=300.0)
    tok = "778899001122334455667788990011"
    prices = [round(c / 100.0, 2) for c in range(55, 91)]
    shares_grid = list(range(6, 66))
    pairs = [(px, float(sh)) for px in prices for sh in shares_grid]
    for px, sh in pairs:
        cache.store_presigned_order(tok, px, sh, {"s": sh})

    t_scan0 = time.perf_counter()
    missing_all_fresh = cache.filter_missing_or_stale(tok, pairs)
    scan_ms = (time.perf_counter() - t_scan0) * 1000.0
    assert missing_all_fresh == []
    assert scan_ms < 15.0, f"Expected sub-15ms single-lock batch scan for 2,160 pairs, got {scan_ms:.2f}ms"

    assert cache.get_presigned_order(tok, 0.76, 22.0) == {"s": 22.0}
    assert cache.filter_missing_or_stale(tok, pairs) == [(0.76, 22.0)]

    # 2. End-to-end _HOT_DISPATCH_ACTIVE shield + post-wire call_soon log ordering
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", tmp_path / "k2_st.json")
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.RESOLUTIONS_FILE", tmp_path / "k2_res.jsonl")
    h = PolymarketLiveHarvester(ticket_notional=16.50, dry_run=True, dynamic_sizing=True)
    h.dry_run = False
    h.executor.dry_run = False
    h.state_file = tmp_path / "k2_st.json"
    h.poll_onchain_redemptions = lambda: None
    h.executor.auth_mode = "AUTHENTICATED_L2"
    h.executor.is_authenticated = True
    h.executor.is_heartbeat_healthy = lambda: True
    h.executor.get_collateral_balance = lambda *a, **kw: 120.38
    h._last_known_collateral = 120.38

    events = []
    hot_during_qualify = []
    hot_during_snipe = []
    hot_during_save = []

    def _mock_freshness(asset, now_t):
        hot_during_qualify.append(ex_mod._HOT_DISPATCH_ACTIVE.is_set())
        return (True, 0.04, "OK")

    h.check_recorder_freshness = _mock_freshness
    orig_save = h.save_state

    def _tracked_save():
        hot_during_save.append(ex_mod._HOT_DISPATCH_ACTIVE.count)
        return orig_save()

    h.save_state = _tracked_save

    async def _mock_snipe(**kw):
        hot_during_snipe.append(ex_mod._HOT_DISPATCH_ACTIVE.count)
        # Before yielding to event loop, pre-wire logs are queued on call_soon (zero pre-wire I/O!)
        events.append(("wire_write", len([r for r in caplog.records if "QUALIFIED OPPORTUNITY" in r.getMessage()])))
        await asyncio.sleep(0.005)
        # During network RTT await, call_soon flushes [DYNAMIC SIZING CONFIRMED] + [QUALIFIED OPPORTUNITY]
        events.append(("rtt_midflight", len([r for r in caplog.records if "QUALIFIED OPPORTUNITY" in r.getMessage()])))
        return MagicMock(success=False, mode="FAK_KILLED_NO_MATCH", error="no match", details={"fak_killed": True})

    async def _noop_rescue(**kw):
        return None

    h.executor.execute_snipe_order_async = _mock_snipe
    h._attempt_live_phase3a_maker_rescue = _noop_rescue

    now_t = time.time()
    shk = {
        "shock_id": "SHK_K2_1",
        "event_id": "SHK_K2_1",
        "market_id": "6280999",
        "condition_id": "0x6280999",
        "t0_unix": now_t,
        "title": "Bitcoin Up or Down - October 27, 8:00PM-8:15PM ET",
        "asset": "BTC",
        "horizon": "15m",
        "candle_interval": "15m",
        "resolution_source": "https://data.chain.link/streams/btc-usd",
        "seconds_to_expiry": 450.0,
        "shock_direction": "BUY",
        "shock_ofi": 1.0,
        "shock_volume_100ms": 1_800_000.0,
        "delta_basis_100ms": 1.2,
        "candle_sigma": 0.0012,
        "candle_distance_pct": 0.0820,
        "authoritative_chainlink_open": 80800.00,
        "chainlink_proxy_spot": 80866.26,
        "coinbase_spot": 80866.26,
        "chainlink_twap_60s": 80860.00,
        "spot_at_t0": 80960.00,
        "candle_open_spot": 80895.00,
        "fee_metadata": {"condition_id": "0x6280999", "fee_rate_market": 0.07, "fee_exponent": 1.0},
        "pre_shock_features_t0": {
            "UP": {
                "token_id": tok,
                "best_bid": 0.78,
                "best_ask": 0.79,
                "spread": 0.01,
                "book_timestamp": now_t - 0.04,
                "age_book_ms": 40.0,
                "age_ask_ms": 2500.0,
                "obi_l1": 0.68,
                "raw_top_asks": [[0.79, 200.0]],
                "raw_top_bids": [[0.78, 200.0]],
            }
        },
    }

    assert ex_mod._HOT_DISPATCH_ACTIVE.count == 0
    with caplog.at_level(logging.INFO):
        asyncio.run(h.evaluate_shock_and_execute(shk))
        # Early duplicate-idempotency gate must also release _HOT_DISPATCH_ACTIVE with zero leaks
        asyncio.run(h.evaluate_shock_and_execute(shk))

    assert hot_during_qualify == [True], "Qualification must hold _HOT_DISPATCH_ACTIVE shield"
    assert hot_during_snipe and hot_during_snipe[0] >= 1, "Primary dispatch must hold _HOT_DISPATCH_ACTIVE shield"
    assert hot_during_save and all(c == 0 for c in hot_during_save), "save_state disk I/O must run AFTER releasing _HOT_DISPATCH_ACTIVE"
    assert ex_mod._HOT_DISPATCH_ACTIVE.count == 0, "Zero _HOT_DISPATCH_ACTIVE refcount leak after completion/rejection"
    assert events == [("wire_write", 0), ("rtt_midflight", 1)], f"Expected zero pre-wire flush then mid-RTT flush, got {events}"
    msgs = [r.getMessage() for r in caplog.records]
    assert any("[DYNAMIC SIZING CONFIRMED]" in m for m in msgs)
    assert any("[QUALIFIED OPPORTUNITY]" in m for m in msgs)


def test_kaizen3_coalesced_recorder_ipc_and_zero_sleep_alt_dispatch(tmp_path, monkeypatch):
    import asyncio
    from collections import deque
    from src.polymarket_research import polymarket_live_executor as ex_mod
    from src.polymarket_research import polymarket_terminal_recorder as rec_mod
    from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester

    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", tmp_path / "k3_st.json")
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.RESOLUTIONS_FILE", tmp_path / "k3_res.jsonl")
    h = PolymarketLiveHarvester(ticket_notional=16.50, dry_run=True, dynamic_sizing=True)
    h.dry_run = False
    h.executor.dry_run = False
    h.allowed_assets = {"BTC", "SOL"}
    h.executor.is_heartbeat_healthy = lambda: True

    seen_order = []
    hot_counts_by_asset = {}

    async def _spy_eval(shk):
        a = shk.get("asset")
        seen_order.append((a, shk.get("horizon")))
        hot_counts_by_asset[a] = ex_mod._HOT_DISPATCH_ACTIVE.count

    h._evaluate_shock_and_execute_impl = _spy_eval
    h._fast_trigger_lines = deque(maxlen=64)

    # 1. Single-line SOL shock via RAM IPC must NOT incur the legacy 2.0ms sleep penalty
    now_t = time.time()
    raw_sol, line_sol = rec_mod._encode_trigger_fast({
        "shock_id": "K3_SOL_15M", "market_id": "7001", "asset": "SOL", "horizon": "15m",
        "t0_unix": now_t, "seconds_to_expiry": 400.0, "shock_direction": "BUY",
        "candle_distance_pct": 0.12, "z_val": 1.4, "title": "Solana Up or Down - 8:00PM-8:15PM ET",
        "pre_shock_features_t0": {"UP": {"token_id": "9001", "vwap_$25": 0.72}},
    })
    assert raw_sol.endswith(b"\n")
    h._fast_trigger_lines.append(line_sol.strip())

    async def _drain_once():
        t0 = time.perf_counter()
        cnt = await h._drain_and_dispatch_shock_triggers()
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        await asyncio.sleep(0.002)
        return cnt, elapsed_ms

    cnt_sol, sol_ms = asyncio.run(_drain_once())
    assert cnt_sol == 1
    assert sol_ms < 2.5, f"Expected zero 2ms artificial sleep on RAM IPC SOL shock, got {sol_ms:.2f}ms"
    assert hot_counts_by_asset["SOL"] >= 1

    # 2. Coalesced 15m + 1h datagram + disallowed XAU noise asset: 15m runs ahead of 1h, XAU never grabs _HOT_DISPATCH_ACTIVE
    seen_order.clear()
    _, ln_1h = rec_mod._encode_trigger_fast({
        "shock_id": "K3_BTC_1H", "market_id": "7002", "asset": "BTC", "horizon": "1h",
        "t0_unix": now_t, "seconds_to_expiry": 1800.0, "shock_direction": "BUY",
        "candle_distance_pct": 0.10, "z_val": 1.2, "title": "Bitcoin Up or Down - 8PM ET",
        "pre_shock_features_t0": {"UP": {"token_id": "9002", "vwap_$25": 0.72}},
    })
    _, ln_15m = rec_mod._encode_trigger_fast({
        "shock_id": "K3_BTC_15M", "market_id": "7003", "asset": "BTC", "horizon": "15m",
        "t0_unix": now_t, "seconds_to_expiry": 400.0, "shock_direction": "BUY",
        "candle_distance_pct": 0.10, "z_val": 1.2, "title": "Bitcoin Up or Down - 8:00PM-8:15PM ET",
        "pre_shock_features_t0": {"UP": {"token_id": "9003", "vwap_$25": 0.72}},
    })
    _, ln_xau = rec_mod._encode_trigger_fast({
        "shock_id": "K3_XAU_1H", "market_id": "7004", "asset": "XAU", "horizon": "1h",
        "t0_unix": now_t, "seconds_to_expiry": 1800.0, "shock_direction": "BUY",
        "candle_distance_pct": 0.15, "z_val": 1.5, "title": "Gold Up or Down",
        "pre_shock_features_t0": {"UP": {"token_id": "9004", "vwap_$25": 0.72}},
    })
    for ln in (ln_1h, ln_15m, ln_xau):
        h._fast_trigger_lines.append(ln.strip())

    cnt_b, _ = asyncio.run(_drain_once())
    assert cnt_b == 3
    assert seen_order[0] == ("BTC", "15m"), f"Expected 15m tie-break ahead of 1h, got {seen_order}"
    assert hot_counts_by_asset["XAU"] == 0, "Disallowed XAU shock must not acquire _HOT_DISPATCH_ACTIVE"
    assert ex_mod._HOT_DISPATCH_ACTIVE.count == 0


def test_kaizen4_empty_ask_book_and_sched_idle_ladder_no_thrash(tmp_path, monkeypatch):
    import asyncio
    from datetime import datetime, timedelta, timezone
    from unittest.mock import MagicMock
    from src.polymarket_research import latency_trace as lt_mod
    from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester
    from src.polymarket_research.polymarket_terminal_recorder import L2OrderBook

    # 1. Recorder L2OrderBook tracks empty_ask_ms when asks sweep to empty
    bk = L2OrderBook("111449419606434494624309765181971808888700798513526208026111136872543601001600")
    bk.apply_snapshot([{"price": "0.98", "size": "100"}], [{"price": "0.99", "size": "50"}])
    bk.apply_price_changes([{"price": "0.99", "size": "0", "side": "SELL"}, {"price": "0.99", "size": "215.98", "side": "BUY"}])
    m_empty = bk.get_metrics(obs_ts=time.time() + 0.05)
    assert m_empty["best_ask"] == 1.0 and m_empty["ask_size_l1"] == 0.0
    assert m_empty["age_ask_ms"] is None
    assert m_empty["empty_ask_ms"] is not None and m_empty["empty_ask_ms"] >= 40.0

    # 2. Exact 12:42:36 SOL 15m UP reproduction ($0.99 bid, 0 asks -> ALREADY_PRICED_IN, NOT FEED / IPC LAG)
    forensic_path = tmp_path / "k4_forensics.jsonl"
    monkeypatch.setenv("PM_SHOCK_ATTEMPT_FILE", str(forensic_path))
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", tmp_path / "k4_st.json")
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.RESOLUTIONS_FILE", tmp_path / "k4_res.jsonl")

    h = PolymarketLiveHarvester(ticket_notional=16.50, dry_run=True, dynamic_sizing=True)
    h.dry_run = False
    h.executor.dry_run = False
    h.allowed_assets = {"BTC", "SOL"}
    h.executor.is_heartbeat_healthy = lambda: True

    now_u = time.time()
    real_tok = "111449419606434494624309765181971808888700798513526208026111136872543601001600"
    shk_pinned = {
        "shock_id": "6458741_PINNED",
        "market_id": "6458741",
        "asset": "SOL",
        "horizon": "15m",
        "title": "Solana Up or Down - November 1, 7:30AM-7:45AM ET",
        "resolution_source": "https://data.chain.link/streams/sol-usd-twap-60s-streams",
        "t0_unix": now_u - 0.003,
        "exchange_event_ts_ms": int((now_u - 0.142) * 1000),
        "clob_ws_connected": True,
        "seconds_to_expiry": 143.8,
        "shock_direction": "BUY",
        "shock_ofi": 1.0,
        "spot_at_t0": 95.05,
        "coinbase_spot": 94.88,
        "chainlink_proxy_spot": 94.9008,
        "authoritative_chainlink_open": 94.47535,
        "candle_open_spot": 94.64,
        "candle_distance_pct": 0.4503,
        "fee_metadata": {"fee_rate_market": 0.07, "fee_exponent": 1.0},
        "pre_shock_features_t0": {
            "UP": {
                "token_id": real_tok,
                "best_bid": 0.99,
                "best_ask": 1.0,
                "bid_size_l1": 215.98,
                "ask_size_l1": 0.0,
                "obi_l1": 1.0,
                "age_book_ms": 19.7,
                "age_bid_ms": 9214.1,
                "age_ask_ms": None,
                "raw_top_bids": [[0.99, 215.98]],
                "raw_top_asks": [],
            }
        },
    }
    asyncio.run(h.evaluate_shock_and_execute(shk_pinned))

    # 3. Genuine missing age_ask_ms when resting asks DO exist (< $0.995) MUST still raise TOO_SLOW_FEED_LAG
    shk_real_missing = {
        **shk_pinned,
        "shock_id": "6458741_REAL_LAG",
        "pre_shock_features_t0": {
            "UP": {
                "token_id": real_tok,
                "best_bid": 0.71,
                "best_ask": 0.72,
                "bid_size_l1": 50.0,
                "ask_size_l1": 80.0,
                "obi_l1": 0.1,
                "age_book_ms": 19.7,
                "age_ask_ms": None,
                "raw_top_bids": [[0.71, 50.0]],
                "raw_top_asks": [[0.72, 80.0]],
            }
        },
    }
    asyncio.run(h.evaluate_shock_and_execute(shk_real_missing))
    lt_mod.flush(2.0)

    recs = [json.loads(x) for x in forensic_path.read_text(encoding="utf-8").splitlines() if x.strip()]
    by_id = {r["shock_id"]: r for r in recs}
    assert by_id["6458741_PINNED"]["speed_verdict"] == "ALREADY_PRICED_IN"
    assert by_id["6458741_PINNED"]["is_speed_miss"] is False
    assert by_id["6458741_REAL_LAG"]["speed_verdict"] == "TOO_SLOW_FEED_LAG"
    assert by_id["6458741_REAL_LAG"]["is_speed_miss"] is True

    # 4. _prewarm_next_candle_markets skips disallowed ETH and far-future t+30m 15m candles in ladder registry
    now_dt = datetime.now(timezone.utc)
    def _fake_get(url, timeout=3.0):
        resp = MagicMock(status_code=200)
        if "eth-up-or-down-15m" in url:
            resp.json.return_value = [{"markets": [{"id": "801", "conditionId": "0xc1", "endDate": (now_dt + timedelta(seconds=600)).isoformat(), "clobTokenIds": '["ETH_UP", "ETH_DN"]'}]}]
        elif "btc-up-or-down-15m" in url:
            resp.json.return_value = [{"markets": [
                {"id": "802", "conditionId": "0xc2", "endDate": (now_dt + timedelta(seconds=800)).isoformat(), "clobTokenIds": '["BTC_15_NEAR_U", "BTC_15_NEAR_D"]'},
                {"id": "803", "conditionId": "0xc3", "endDate": (now_dt + timedelta(seconds=1700)).isoformat(), "clobTokenIds": '["BTC_15_FAR_U", "BTC_15_FAR_D"]'},
            ]}]
        else:
            resp.json.return_value = []
        return resp

    h.executor._sync_session = MagicMock()
    h.executor._sync_session.get = _fake_get
    h._spawn_ladder_prewarm = lambda toks: None
    h._startup_prewarmed_logged = True
    asyncio.run(h._prewarm_next_candle_markets())
    reg = getattr(h, "_active_warmed_token_expiries", {})
    assert "BTC_15_NEAR_U" in reg and "BTC_15_NEAR_D" in reg
    assert "ETH_UP" not in reg, "Disallowed ETH tokens must not thrash the EIP-712 signing ladder"
    assert "BTC_15_FAR_U" not in reg, "t+28m 15m candle must wait until T-2m before entering ladder"


def test_track_a_realtime_trade_ws_and_empty_ask_routing():
    from src.polymarket_research.polymarket_terminal_recorder import ASSET_CONFIGS
    from src.polymarket_research.net_alpha_opportunity_engine import inspect_microstructure_feature_completeness
    from src.polymarket_research.latency_trace import classify_shock_attempt

    # 1. All 8 assets use unbatched /ws/<sym>@trade (never 100ms-batched /market/ws/<sym>@aggTrade)
    for sym_key, cfg in ASSET_CONFIGS.items():
        fut_ws = cfg["binance_futures_ws"]
        assert fut_ws.startswith("wss://fstream.binance.com:443/ws/") and fut_ws.endswith("@trade"), f"{sym_key}: {fut_ws}"
        assert "/market/ws/" not in fut_ws and "@aggTrade" not in fut_ws
        spot_ws = cfg["binance_spot_ws"]
        if spot_ws:
            assert spot_ws.startswith("wss://stream.binance.com:443/ws/") and spot_ws.endswith("@trade"), f"{sym_key}: {spot_ws}"

    # 2. Empty ask side (best_ask=1.0, ask_size_l1=0.0) with valid age_bid_ms is NOT treated as corrupt telemetry
    real_tok = "100434764618174237135201777197981253576172734064131101154122934005557319214073"
    ok_empty = inspect_microstructure_feature_completeness(
        {
            "fee_metadata": {"fee_rate_market": 0.07},
            "shock_ofi": 0.92,
            "coinbase_spot": 95000.0,
            "pre_shock_features_t0": {
                "UP": {
                    "token_id": real_tok,
                    "best_bid": 0.66,
                    "best_ask": 1.0,
                    "ask_size_l1": 0.0,
                    "obi_l1": 1.0,
                    "age_bid_ms": 340.0,
                    "age_ask_ms": None,
                }
            },
        },
        "UP",
        real_tok,
    )
    assert ok_empty["hard_veto_live"] is False and "age_ask_ms" not in ok_empty["missing_fields"]

    # 3. Pinned bid > cap_px (e.g. $0.75 > $0.72 15m cap) with 0 resting asks classifies as ALREADY_PRICED_IN
    rec_75 = classify_shock_attempt(
        {
            "shock_id": "TEST_75_PIN",
            "asset": "BTC",
            "horizon": "15m",
            "side": "UP",
            "gate_code": "PRICE_BAND_REJECT",
            "gate_detail": "Book pinned @$0.75 bid with 0 resting asks (> $0.72 cap)",
            "t0_ask": 1.0,
            "eval_ask": 1.0,
            "eval_bid": 0.75,
            "cap_px": 0.72,
            "book_age_ms": 850.0,
        }
    )
    assert rec_75["speed_verdict"] == "ALREADY_PRICED_IN"
    assert rec_75["badge"] == "ALREADY PRICED IN"
    assert rec_75["meaningful"] is True
    assert rec_75["is_speed_miss"] is False


def test_already_priced_in_hot_wave_priority_and_settled_99c(tmp_path, monkeypatch):
    import asyncio
    import json
    from collections import deque
    from src.polymarket_research.latency_trace import classify_shock_attempt
    from src.polymarket_research.polymarket_live_harvester import (
        PolymarketLiveHarvester,
        _HOT_DISPATCH_ACTIVE,
    )

    # 1. Idea 3: >=98.5c settled books get SETTLED 99c+ & meaningful=False; <98.5c stay ALREADY PRICED IN & meaningful=True
    settled_empty = classify_shock_attempt(
        {
            "shock_id": "S_99_EMPTY",
            "asset": "BTC",
            "horizon": "1h",
            "side": "UP",
            "gate_code": "PRICE_BAND_REJECT",
            "t0_ask": 1.0,
            "eval_ask": 1.0,
            "eval_bid": 0.99,
            "cap_px": 0.76,
            "dist_pct": 0.55,
            "book_age_ms": 1200.0,
        }
    )
    assert settled_empty["speed_verdict"] == "ALREADY_PRICED_IN"
    assert settled_empty["badge"] == "SETTLED 99c+"
    assert settled_empty["meaningful"] is False

    settled_99_ask = classify_shock_attempt(
        {
            "shock_id": "S_99_ASK",
            "asset": "SOL",
            "horizon": "1h",
            "side": "DOWN",
            "gate_code": "TAKER_ASYMMETRY_VETO",
            "t0_ask": 0.99,
            "eval_ask": 0.99,
            "eval_bid": 0.98,
            "cap_px": 0.76,
            "dist_pct": -0.60,
            "book_age_ms": 950.0,
        }
    )
    assert settled_99_ask["speed_verdict"] == "ALREADY_PRICED_IN"
    assert settled_99_ask["badge"] == "SETTLED 99c+"
    assert settled_99_ask["meaningful"] is False

    over_cap_93 = classify_shock_attempt(
        {
            "shock_id": "S_93_ASK",
            "asset": "BTC",
            "horizon": "1h",
            "side": "UP",
            "gate_code": "TAKER_ASYMMETRY_VETO",
            "t0_ask": 0.93,
            "eval_ask": 0.93,
            "eval_bid": 0.91,
            "cap_px": 0.76,
            "dist_pct": 0.28,
            "book_age_ms": 900.0,
        }
    )
    assert over_cap_93["speed_verdict"] == "ALREADY_PRICED_IN"
    assert over_cap_93["badge"] == "ALREADY PRICED IN"
    assert over_cap_93["meaningful"] is True

    # 2. Idea 2: _calc_priority_score resolves thin/empty asks via best_ask & aligns v5 strict ceilings without dropping Boundary/Maker rescue
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", tmp_path / "st_p.json")
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.RESOLUTIONS_FILE", tmp_path / "res_p.jsonl")
    h = PolymarketLiveHarvester(ticket_notional=15.0, dry_run=True, dynamic_sizing=True)
    h.dry_run = False
    h.holistic_v5_live_mode = True
    h.enable_live_phase3a_maker_fallback = True

    def _mk_shk(sid, hz, best_bid, best_ask, vwap25=None, tte=300.0, dist=0.18, z=1.5, src="BINANCE_FUTURES"):
        return {
            "shock_id": sid,
            "market_id": f"M_{sid}",
            "t0_unix": 1793500000.0,
            "asset": "BTC",
            "horizon": hz,
            "candle_interval": hz,
            "title": f"Bitcoin Up or Down - {hz} {sid}",
            "seconds_to_expiry": tte,
            "shock_direction": "BUY",
            "candle_distance_pct": dist,
            "z_val": z,
            "z_score": z,
            "shock_source": src,
            "pre_shock_features_t0": {
                "UP": {
                    "token_id": f"TOK_{sid}",
                    "best_bid": best_bid,
                    "best_ask": best_ask,
                    "vwap_$50": vwap25,
                    "vwap_$25": vwap25,
                }
            },
        }

    # Thin/empty $0.97 and $1.00 asks (vwap_$25=None) MUST score 0.0 (both v5 strict and legacy mode)
    assert h._calc_priority_score(_mk_shk("DEAD_100", "1h", 0.99, 1.00, vwap25=None)) == 0.0
    assert h._calc_priority_score(_mk_shk("THIN_97", "1h", 0.95, 0.97, vwap25=None)) == 0.0
    h.holistic_v5_live_mode = False
    assert h._calc_priority_score(_mk_shk("DEAD_100_LEG", "1h", 0.99, 1.00, vwap25=None)) == 0.0
    h.holistic_v5_live_mode = True

    # Thin $0.64 15m ask ($16 L1 depth -> vwap_$25=None) MUST score > 0.0 (not fall back to 0.50 < 0.52 floor!)
    assert h._calc_priority_score(_mk_shk("THIN_64", "15m", 0.63, 0.64, vwap25=None)) > 2.0

    # Valid Phase-3A Maker rescue (15m @$0.74 <= $0.72+3c; 1h @$0.78 <= $0.76+3c) and Boundary Lock (@$0.91, TTE=70s, z=3.4) MUST stay > 0.0
    assert h._calc_priority_score(_mk_shk("MKR_15M_74", "15m", 0.71, 0.74, vwap25=0.74, tte=220.0)) > 0.0
    assert h._calc_priority_score(_mk_shk("MKR_1H_78", "1h", 0.75, 0.78, vwap25=0.78, tte=300.0)) > 0.0
    assert h._calc_priority_score(_mk_shk("BND_70S_91", "15m", 0.89, 0.91, vwap25=0.91, tte=70.0, dist=0.22, z=3.4, src="BOUNDARY_LOCK")) > 0.0
    # Over-cap $0.86 non-boundary 1h shock scores 0.0 in v5 strict mode
    assert h._calc_priority_score(_mk_shk("OVER_86", "1h", 0.84, 0.86, vwap25=0.86, tte=900.0)) == 0.0

    # 3. Idea 1: Simultaneous micro-batch dispatches live 15m snipe BEFORE dead/over-cap 1h shocks with zero hot-lock or prewarm contention
    call_log = []
    prewarm_ids = []
    orig_eval = h.evaluate_shock_and_execute

    async def _stub_impl(shock):
        call_log.append((shock["shock_id"], _HOT_DISPATCH_ACTIVE.is_set()))
        await asyncio.sleep(0)

    h._evaluate_shock_and_execute_impl = _stub_impl
    h._prewarm_market_metadata = lambda shk: prewarm_ids.append(shk["shock_id"])
    h._fast_trigger_lines = deque(
        [
            json.dumps(_mk_shk("DEAD_1H_99", "1h", 0.99, 1.00, vwap25=None, tte=1200.0)),
            json.dumps(_mk_shk("OVER_1H_92", "1h", 0.90, 0.92, vwap25=0.92, tte=1200.0)),
            json.dumps(_mk_shk("LIVE_15M_62", "15m", 0.61, 0.62, vwap25=0.62, tte=300.0, dist=0.16, z=1.6)),
        ]
    )

    async def _run_batch():
        n = await h._drain_and_dispatch_shock_triggers()
        await asyncio.gather(*list(h._bg_shock_tasks))
        return n

    dispatched_n = asyncio.run(_run_batch())
    assert dispatched_n == 3
    assert call_log[0] == ("LIVE_15M_62", True), f"Expected LIVE_15M_62 hot first, got {call_log}"
    assert ("DEAD_1H_99", False) in call_log[1:]
    assert ("OVER_1H_92", False) in call_log[1:]
    assert prewarm_ids == ["LIVE_15M_62"]


def test_maker_ttl_quiet_upgrades_1_to_4(tmp_path, monkeypatch):
    import asyncio
    from unittest.mock import MagicMock
    from src.polymarket_research import polymarket_live_harvester as plh
    from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester
    from src.polymarket_research.polymarket_live_executor import CancelOrderResult

    monkeypatch.setattr(plh, "DATA_DIR", tmp_path)
    monkeypatch.setattr(plh, "STATE_FILE", tmp_path / "mkr_q_state.json")
    a124_state = {
        "updated_utc": "2026-11-01T22:00:00Z",
        "by_sleeve": {
            "BOND1_UMA_RESOLUTION_CARRY": {
                "closed": 12, "wins": 12, "losses": 0, "win_rate_pct": 100.0,
                "realized_pnl_t1000_usd": 48.0, "legging_adjusted_pnl_t1000_usd": 48.0,
            },
            "D1_SAME_ORACLE_DOMINANCE_BOX": {
                "closed": 32, "wins": 32, "losses": 0, "win_rate_pct": 100.0,
                "realized_pnl_t1000_usd": 151.95, "legging_adjusted_pnl_t1000_usd": 151.95,
            },
        },
    }
    (tmp_path / "alpha124_shadow_state.json").write_text(json.dumps(a124_state), encoding="utf-8")

    h = PolymarketLiveHarvester(dry_run=True, allowed_assets={"BTC", "SOL", "ETH"})
    h.dry_run = False
    h._startup_reconciled = True
    h.holistic_v5_live_mode = True
    h.enforce_bond1_smart_queue = True
    h._last_known_collateral = 69.23
    h.max_exposure = 65.0
    h.executor.auth_mode = "LIVE"
    h.executor.get_collateral_balance = lambda *a, **kw: 69.23
    h._wallet_token_balance = lambda _tok: (0.0, h.ONCHAIN_SOURCE)
    h.executor.invalidate_collateral_cache = lambda: None
    h.executor.prewarm_token_market_cache = lambda **kw: None
    for _cfg_d in (plh.RISK_CONFIG, h.risk_config):
        monkeypatch.setitem(_cfg_d, "bond1_maker_ttl_sec", 0.12)
        monkeypatch.setitem(_cfg_d, "bond1_maker_max_keep_sec", 0.12)
        monkeypatch.setitem(_cfg_d, "bond1_book_poll_sec", 0.04)
        monkeypatch.setitem(_cfg_d, "bond1_buried_cancel_sec", 0.08)

    books = {}

    def _slow_book(tid):
        time.sleep(0.015)
        return books[tid]

    h.executor.get_market_book = _slow_book
    posted_b1 = []

    def _post_b1(**kw):
        idx = len(posted_b1) + 1
        sh = int(kw["notional_usd"] // kw["price"])
        posted_b1.append({"idx": idx, "sh": sh, **kw})
        return {"success": True, "orderID": f"0xB1_{idx}", "price": kw["price"], "shares": float(sh)}

    h.executor.post_maker_entry_order = _post_b1
    h.executor.cancel_order = lambda oid: {"is_canceled": True, "outcome": "CANCELED", "matched": 0.0}
    h.executor.get_order_fill_summary = lambda oid, tid: {
        "matched": 0.0, "avg_price": 0.0, "cash": 0.0, "fee": 0.0, "terminal": False,
    }

    def _cand(mid: str, wtok: str, ltok: str, px: float = 0.990):
        return {
            "box_id": f"MKR_B1_{mid}",
            "box_type": "SINGLE_LEG_MAKER_LOCK",
            "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
            "dedupe_key": f"BOND1_MKR_{mid}",
            "pair_dedupe_key": f"BOND1_{mid}",
            "asset": "SPORTS_TOTALS",
            "leg_a_market_id": mid,
            "leg_a_condition_id": f"0x{mid}",
            "leg_a_token_id": wtok,
            "leg_a_opp_token_id": ltok,
            "leg_a_side": "YES",
            "anchor_bid_px": px,
            "min_resting_bid": 0.94,
            "max_box_cost_net": 0.994,
            "max_opp_bid": 0.008,
            "expiry_ts": time.time() + 3600.0,
            "ts_unix": time.time(),
        }

    # --- 1. Ideas 1, 3, & 4: Concurrent 3-task spawn reserves pre-await, diversifies at $25/mkt, and steps up stale 0.990 -> 0.993 ---
    for i in (1, 2, 3):
        books[f"W{i}"] = {"asks": [{"price": "1.000", "size": "200"}], "bids": [{"price": "0.992", "size": "100"}]}
        books[f"L{i}"] = {"asks": [{"price": "0.015", "size": "200"}], "bids": [{"price": "0.002", "size": "200"}]}

    async def _run_concurrent_3():
        return await asyncio.gather(
            h.maybe_execute_graduated_single_leg_maker_lock(_cand("7001", "W1", "L1", 0.990)),
            h.maybe_execute_graduated_single_leg_maker_lock(_cand("7002", "W2", "L2", 0.990)),
            h.maybe_execute_graduated_single_leg_maker_lock(_cand("7003", "W3", "L3", 0.990)),
        )

    r1, r2, r3 = asyncio.run(_run_concurrent_3())
    assert len(posted_b1) == 2
    assert posted_b1[0]["price"] == 0.993 and posted_b1[0]["sh"] == 25  # $25.00 // $0.993 = 25 sh (not 52!)
    assert posted_b1[1]["price"] == 0.993 and posted_b1[1]["sh"] == 25
    assert r3["executed"] is False and r3["reason"] == "INSUFFICIENT_MAKER_BOX_BUDGET"
    assert h._prepost_sll_reserved_usd == {}

    # --- 2. Idea 1: Whale queue veto (> $350 at tight 1-tick spread) & Outbid-above-cap veto (> $0.994) ---
    books["WQ"] = {"asks": [{"price": "0.994", "size": "500"}], "bids": [{"price": "0.993", "size": "800"}]}
    books["LQ"] = {"asks": [{"price": "0.010", "size": "100"}], "bids": [{"price": "0.002", "size": "100"}]}
    rq = asyncio.run(h.maybe_execute_graduated_single_leg_maker_lock(_cand("7004", "WQ", "LQ", 0.993)))
    assert rq["executed"] is False and rq["reason"].startswith("BOND1_QUEUE_TOO_DEEP:")

    books["WC"] = {"asks": [{"price": "0.998", "size": "500"}], "bids": [{"price": "0.995", "size": "100"}]}
    books["LC"] = {"asks": [{"price": "0.010", "size": "100"}], "bids": [{"price": "0.002", "size": "100"}]}
    rc = asyncio.run(h.maybe_execute_graduated_single_leg_maker_lock(_cand("7005", "WC", "LC", 0.994)))
    assert rc["executed"] is False and rc["reason"].startswith("BOND1_OUTBID_ABOVE_CAP:")

    # --- 3. Idea 2A: Mid-TTL BOND1 outbid auto re-peg (0.991 -> outbid @ 0.992 -> reposts @ 0.993) + buried early release ---
    posted_b1.clear()
    for _cfg_d in (plh.RISK_CONFIG, h.risk_config):
        monkeypatch.setitem(_cfg_d, "bond1_maker_ttl_sec", 0.60)
        monkeypatch.setitem(_cfg_d, "bond1_maker_max_keep_sec", 0.60)
    books["WRP"] = {"asks": [{"price": "1.000", "size": "200"}], "bids": [{"price": "0.990", "size": "50"}]}
    books["LRP"] = {"asks": [{"price": "0.012", "size": "200"}], "bids": [{"price": "0.002", "size": "50"}]}
    h.executor.get_market_book = lambda tid: books[tid]

    async def _run_b1_repeg():
        t_rp = asyncio.create_task(h.maybe_execute_graduated_single_leg_maker_lock(_cand("7006", "WRP", "LRP", 0.991)))
        await asyncio.sleep(0.03)
        assert len(posted_b1) == 1 and posted_b1[0]["price"] == 0.991
        # Competitor steps ahead to 0.992 while ask is 1.000 -> should cancel & schedule repost @ 0.993
        books["WRP"] = {"asks": [{"price": "1.000", "size": "200"}], "bids": [{"price": "0.992", "size": "50"}]}
        out_rp = await t_rp
        assert out_rp["reason"] == "BOND1_OUTBID_REPEGGED" and out_rp["repeg_px"] == 0.993
        await asyncio.sleep(0.26)
        assert len(posted_b1) >= 2 and posted_b1[1]["price"] == 0.993
        for tk in list(getattr(h, "_maker_anchor_bg_tasks", set())):
            await tk

    asyncio.run(_run_b1_repeg())

    # Buried above $0.994 cap -> releases early in ~0.15s instead of waiting full 0.60s TTL
    emitted_sf = []
    monkeypatch.setattr(plh, "_emit_shock_attempt", lambda p: emitted_sf.append(p))
    books["WBR"] = {"asks": [{"price": "0.999", "size": "200"}], "bids": [{"price": "0.993", "size": "50"}]}
    books["LBR"] = {"asks": [{"price": "0.012", "size": "200"}], "bids": [{"price": "0.002", "size": "50"}]}

    async def _run_b1_buried():
        t_br = asyncio.create_task(h.maybe_execute_graduated_single_leg_maker_lock(_cand("7007", "WBR", "LBR", 0.994)))
        await asyncio.sleep(0.03)
        books["WBR"] = {"asks": [{"price": "0.999", "size": "200"}], "bids": [{"price": "0.995", "size": "500"}]}
        t0_b = time.monotonic()
        out_br = await t_br
        return out_br, time.monotonic() - t0_b

    out_br, elapsed_br = asyncio.run(_run_b1_buried())
    assert out_br["reason"] == "BOND1_MAKER_OUTBID_RELEASED"
    assert elapsed_br < 0.45
    assert emitted_sf and lt.classify_shock_attempt(emitted_sf[-1])["badge"] == "OUTBID RELEASED"

    # --- 4. Idea 2B: Phase 3A mid-TTL outbid single re-peg ($0.70 -> $0.72) + cancel-race fill safety ---
    monkeypatch.setenv("PM_LIVE_PHASE3A_TTL_SEC", "1.6")
    h.holistic_v5_live_mode = False
    h.enable_live_phase3a_maker_fallback = True
    h.enable_phase3a_outbid_repeg = True
    h.get_usd_reference_spot_price = lambda _a: 81200.0
    p3a_tok = "9" * 30
    live_p3a_bk = {"asks": [{"price": "0.73", "size": "80"}], "bids": [{"price": "0.71", "size": "40"}]}
    h._pos_market_ws = MagicMock()
    h._pos_market_ws.get_book = lambda tid, max_age_sec=1.5: live_p3a_bk if tid == p3a_tok else None

    p3a_posts = []

    def _p3a_post(**kw):
        idx = len(p3a_posts) + 1
        p3a_posts.append(kw)
        return {"success": True, "orderID": f"OID_P3A_RP_{idx}", "price": kw["price"], "shares": 20.0}

    h.executor.place_passive_maker_entry = _p3a_post
    h.executor.cancel_order = lambda oid: (
        CancelOrderResult({"canceled": [oid]}, order_id=oid, outcome="CANCELED", is_canceled=True, matched=0.0)
        if oid == "OID_P3A_RP_1"
        else CancelOrderResult({}, order_id=oid, outcome="FILLED", is_canceled=False, matched=20.0)
    )
    h.executor.get_order_fill_summary = lambda oid, tid: (
        {"matched": 0.0, "terminal": True}
        if oid == "OID_P3A_RP_1"
        else {"matched": 20.0, "avg_price": 0.72, "terminal": True, "trade_ids": ["T_RP"], "tx_hashes": ["0xrp"]}
    )
    r_p3a = asyncio.run(h._attempt_live_phase3a_maker_rescue(
        trade_id="TR_P3A_RP", token_id=p3a_tok, target_token="UP", asset_str="BTC",
        effective_notional=16.50, first_ask=0.73, first_bid=0.69, min_allowed_price=0.52,
        max_allowed_price=0.72, open_spot=81000.0, entry_spot_ref=81200.0, spot_denom="USD",
        tte=220.0, pre_cond_bal=0.0,
        book_snapshot={"asks": [{"price": "0.73", "size": "80"}], "bids": [{"price": "0.69", "size": "40"}]},
    ))
    assert len(p3a_posts) == 2
    assert p3a_posts[0]["price"] == 0.70 and p3a_posts[1]["price"] == 0.72
    assert r_p3a is not None and r_p3a.success is True and r_p3a.price == 0.72

    # Cancel-race safety: if OID #1 already filled right as we attempt to cancel for re-peg, NEVER post OID #2!
    p3a_posts.clear()
    h.executor.cancel_order = lambda oid: CancelOrderResult({}, order_id=oid, outcome="FILLED", is_canceled=False, matched=20.0)
    h.executor.get_order_fill_summary = lambda oid, tid: {
        "matched": 20.0, "avg_price": 0.70, "terminal": True, "trade_ids": ["T_RACE"], "tx_hashes": ["0xrace"],
    }
    r_race = asyncio.run(h._attempt_live_phase3a_maker_rescue(
        trade_id="TR_P3A_RACE", token_id=p3a_tok, target_token="UP", asset_str="BTC",
        effective_notional=16.50, first_ask=0.73, first_bid=0.69, min_allowed_price=0.52,
        max_allowed_price=0.72, open_spot=81000.0, entry_spot_ref=81200.0, spot_denom="USD",
        tte=220.0, pre_cond_bal=0.0,
        book_snapshot={"asks": [{"price": "0.73", "size": "80"}], "bids": [{"price": "0.69", "size": "40"}]},
    ))
    assert len(p3a_posts) == 1
    assert r_race is not None and r_race.success is True and r_race.price == 0.70












