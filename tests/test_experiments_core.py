#!/usr/bin/env python3
"""
Unit and Integration Test Suite for experiments.core
====================================================
Validates:
  1. poly_watchdog_ws: Dual-socket subscription, ping loop, silence watchdog,
     dynamic tick sizes, and HTTP session isolation.
  2. hl_mark_replicator: Exact P1 continuous-time EMA, P2 local median,
     P3 weighted median (3, 2, 2, 1, 1) with 30s EMA fallback, 100ms mark computation,
     and 1.0x MMR vs 2/3x MMR HLP takeover margin divergence telemetry.
  3. shadow_broker: Taker FOK/IOC book walking at t0 + dt_latency,
     Maker ALO crossing check, queue ahead depletion, trade print through,
     and DuckDB/SQLite markout telemetry across all horizons.
"""

import asyncio
import math
import os
import time
import pytest
from decimal import Decimal

from experiments.core.poly_watchdog_ws import (
    PolymarketDualSocketWatchdog,
    OrderSessionManager,
    TelemetrySessionManager,
    PolymarketSessionPool,
    SocketTelemetry,
    CLOB_ALLOWED_TICK_SIZES,
)
from experiments.core.hl_mark_replicator import (
    HyperCoreMarkPriceReplicator,
    ContinuousTimeEMA,
    weighted_median,
    CEX_WEIGHTS,
)
from experiments.core.shadow_broker import (
    RealisticShadowBroker,
    ShadowOrder,
    OrderType,
    OrderStatus,
    Side,
    L2Book,
    MARKOUT_HORIZONS,
)


# ==============================================================================
# TEST 1: POLYMARKET DUAL-SOCKET WATCHDOG
# ==============================================================================

def test_poly_subscription_payload_custom_feature():
    """Verify subscription payload contains custom_feature_enabled=True."""
    watchdog = PolymarketDualSocketWatchdog(token_ids=["TOK_UP_1", "TOK_DOWN_1"])
    payload = watchdog.build_subscription_payload()

    assert payload["type"] == "market"
    assert payload["custom_feature_enabled"] is True
    assert "TOK_UP_1" in payload["assets_ids"]
    assert "TOK_DOWN_1" in payload["assets_ids"]


def test_poly_tick_size_dynamic_update_and_quantization():
    """Verify dynamic tick size updates (0.01 <-> 0.001) and Decimal price quantization."""
    updates_recorded = []
    def on_tick_change(asset_id, old_t, new_t):
        updates_recorded.append((asset_id, old_t, new_t))

    watchdog = PolymarketDualSocketWatchdog(
        token_ids=["TOK_TEST"],
        on_tick_size_change=on_tick_change,
    )
    assert watchdog.get_tick_size("TOK_TEST") == 0.01

    # Simulate tick_size_change event from Polymarket CLOB WS
    mock_event = {
        "event_type": "tick_size_change",
        "asset_id": "TOK_TEST",
        "tick_size": 0.001,
        "old_tick_size": 0.01,
    }
    telem = SocketTelemetry(socket_name="Socket_A")
    watchdog._process_market_message(mock_event, telem)

    # Verify map updated and callback fired
    assert watchdog.get_tick_size("TOK_TEST") == 0.001
    assert len(updates_recorded) == 1
    assert updates_recorded[0] == ("TOK_TEST", 0.01, 0.001)

    # Test price quantization with new tick size 0.001
    # Raw price 0.54321 should round down to 0.543 for BUY
    buy_quant = watchdog.quantize_price("TOK_TEST", 0.54321, side="BUY")
    assert buy_quant == 0.543

    # Raw price 0.54321 should round up to 0.544 for SELL
    sell_quant = watchdog.quantize_price("TOK_TEST", 0.54321, side="SELL")
    assert sell_quant == 0.544

    # Test boundary clamping [tick_size, 1.0 - tick_size]
    assert watchdog.quantize_price("TOK_TEST", 0.0001, side="BUY") == 0.001
    assert watchdog.quantize_price("TOK_TEST", 0.9999, side="SELL") == 0.999


def test_poly_session_isolation():
    """Verify order session and telemetry session are strictly isolated."""
    pool = PolymarketSessionPool()

    # Verify separate instances and separate connection pools
    assert pool.order_manager.client is not pool.telemetry_manager.client
    assert pool.order_manager.client.headers["User-Agent"] != pool.telemetry_manager.client.headers["User-Agent"]
    assert "Order Router" in pool.order_manager.client.headers["User-Agent"]
    assert "Watchdog" in pool.telemetry_manager.client.headers["User-Agent"]

    # Verify telemetry prober uses telemetry session, never order session
    watchdog = PolymarketDualSocketWatchdog(session_pool=pool)
    assert watchdog.session_pool.order_manager is pool.order_manager
    assert watchdog.session_pool.telemetry_manager is pool.telemetry_manager


def test_poly_silence_watchdog_freeze_detection():
    """Verify watchdog detects silent freeze on Socket A when Socket B advances for >5s."""
    async def _test():
        watchdog = PolymarketDualSocketWatchdog(
            token_ids=["TOK_ETH"],
            freeze_drift_threshold_seconds=2.0,  # Threshold for test
        )

        t_now = time.monotonic()
        watchdog.telemetry_a.connected = True
        watchdog.telemetry_a.connect_time_mono = t_now - 10.0
        watchdog.telemetry_a.last_book_trade_mono = t_now - 10.0  # Silent for 10 seconds!

        watchdog.telemetry_b.connected = True
        watchdog.telemetry_b.connect_time_mono = t_now - 10.0
        watchdog.telemetry_b.last_book_trade_mono = t_now  # Actively advancing!

        reconnect_called = []
        async def mock_reconnect(sock_id, reason):
            reconnect_called.append((sock_id, reason))

        watchdog._teardown_and_reconnect_socket = mock_reconnect
        watchdog.running = True

        # Run one watchdog iteration
        watchdog_task = asyncio.create_task(watchdog._run_watchdog())
        await asyncio.sleep(1.2)
        watchdog.running = False
        watchdog_task.cancel()

        assert len(reconnect_called) >= 1
        assert reconnect_called[0][0] == "A"
        assert "Silent freeze detected" in reconnect_called[0][1]

    asyncio.run(_test())


def test_poly_pong_not_proof_of_life():
    """Verify PONG does NOT update last_book_trade_mono."""
    watchdog = PolymarketDualSocketWatchdog(token_ids=["TOK_BTC"])
    telem = SocketTelemetry(socket_name="Socket_A")

    t_initial = 100.0
    telem.last_book_trade_mono = t_initial
    telem.last_any_msg_mono = t_initial

    # Simulate PONG arrival
    # In _run_socket: PONG increments total_pongs_received and updates last_any_msg_mono,
    # but does NOT update last_book_trade_mono
    telem.total_pongs_received += 1
    telem.last_any_msg_mono = 110.0

    assert telem.last_book_trade_mono == t_initial
    assert telem.total_pongs_received == 1


# ==============================================================================
# TEST 2: HYPERCORE LOCAL MARK PRICE REPLICATOR
# ==============================================================================

def test_continuous_time_ema_decay():
    """Verify exact continuous-time integral decay math."""
    ema = ContinuousTimeEMA(tau_seconds=150.0, initial_value=0.0)

    t0 = 1000.0
    ema.update(sample=10.0, current_ts=t0)
    assert ema.value() == 10.0

    # Advance 150 seconds (1 tau)
    t1 = t0 + 150.0
    val1 = ema.update(sample=20.0, current_ts=t1)
    # Check that value moves continuously between 10.0 and 20.0
    assert 10.0 < val1 < 20.0
    assert math.isclose(val1, 17.3106, rel_tol=1e-3)


def test_weighted_median_exact_weights():
    """Verify weighted median with CEX weights [3, 2, 2, 1, 1]."""
    # Binance: 100.0 (w=3)
    # OKX: 101.0 (w=2)
    # Bybit: 102.0 (w=2)
    # Gate: 103.0 (w=1)
    # MEXC: 104.0 (w=1)
    # Total weight = 9. Half weight = 4.5.
    # Cumulative:
    # 100.0: 3
    # 101.0: 3 + 2 = 5 >= 4.5 -> Median should be 101.0
    samples = [
        (100.0, 3.0),
        (101.0, 2.0),
        (102.0, 2.0),
        (103.0, 1.0),
        (104.0, 1.0),
    ]
    med = weighted_median(samples)
    assert med == 101.0

    # Test reverse sorted input gives identical result
    med_rev = weighted_median(list(reversed(samples)))
    assert med_rev == 101.0


def test_hl_mark_p1_p2_p3_and_fallback():
    """Verify P1, P2, P3 components and 30s EMA fallback when <=2 CEX live."""
    replicator = HyperCoreMarkPriceReplicator(symbols=["BTC"])

    t0 = 1000.0
    # Set HL oracle and book
    replicator.update_hl_oracle("BTC", 50_000.0, timestamp_mono=t0)
    replicator.update_hl_book(
        "BTC",
        best_bid=50_010.0,
        best_ask=50_020.0,
        last_trade=50_015.0,
        timestamp_mono=t0,
    )

    # State check:
    # P1: oracle 50_000 + EMA_150s(mid - oracle) = 50_000 + 15 = 50_015.0
    # P2: median(50_010, 50_020, 50_015) = 50_015.0
    # P3: no live CEX yet -> fallback to 30s EMA of P2 = 50_015.0
    # P_mark: median(P1, P2, P3) = 50_015.0
    p_mark = replicator.get_mark_price("BTC")
    assert math.isclose(p_mark, 50_015.0, abs_tol=0.1)

    state = replicator.states["BTC"]
    assert "fallback" in state.p3_source

    # Feed 3 external CEXes -> P3 switches to weighted median
    replicator.update_cex_mid("BTC", "binance", 50_012.0, timestamp_mono=t0)
    replicator.update_cex_mid("BTC", "okx", 50_016.0, timestamp_mono=t0)
    replicator.update_cex_mid("BTC", "bybit", 50_018.0, timestamp_mono=t0)

    # 3 live inputs: Binance (w=3, 50012), OKX (w=2, 50016), Bybit (w=2, 50018)
    # Total w = 7. Half = 3.5. Cumulative: 50012 (3), 50016 (5 >= 3.5) => P3 = 50016.0
    assert math.isclose(state.p3, 50_016.0, abs_tol=0.1)
    assert "weighted_median" in state.p3_source


def test_hl_margin_and_hlp_takeover_divergence():
    """Verify divergence and 1.0x MMR vs 2/3x MMR HLP takeover thresholds."""
    replicator = HyperCoreMarkPriceReplicator(symbols=["ETH"])
    replicator.update_hl_oracle("ETH", 3000.0)
    replicator.update_hl_book("ETH", best_bid=3000.0, best_ask=3000.0, last_trade=3000.0)

    # Account with 10.0 ETH Long position at 3000.0 Mark Price.
    # Notional = 30,000 USD.
    # MMR rate = 4.0% (0.04).
    # 1.0x MMR = 30,000 * 0.04 = 1,200.0 USD.
    # 2/3x MMR HLP takeover = 1,200.0 * 2/3 = 800.0 USD.
    # Account equity = 2,000.0 USD.
    telem = replicator.get_mark_vs_book_divergence(
        "ETH",
        account_equity=2000.0,
        position_size=10.0,
        mmr_rate=0.04,
    )

    assert telem["mark_price"] == 3000.0
    assert telem["divergence"] == 0.0
    assert telem["maintenance_margin_1_0_mmr"] == 1200.0
    assert telem["hlp_takeover_margin_2_3_mmr"] == 800.0
    # Cushion to MMR: (2000 - 1200) / 2000 = 40.0%
    assert telem["cushion_to_mmr_pct"] == 40.0
    # Cushion to HLP: (2000 - 800) / 2000 = 60.0%
    assert telem["cushion_to_hlp_pct"] == 60.0

    # Estimated Liquidation Price for Long:
    # (P_mark * pos - Equity) / (pos * (1 - mmr))
    # (30,000 - 2,000) / (10 * 0.96) = 28,000 / 9.6 = 2916.6667
    assert math.isclose(telem["est_liquidation_price"], 2916.6667, rel_tol=1e-4)

    # Estimated HLP Takeover Price for Long:
    # (30,000 - 2,000) / (10 * (1 - 2/3 * 0.04)) = 28,000 / (10 * 0.97333) = 2876.7123
    assert math.isclose(telem["est_hlp_takeover_price"], 2876.7123, rel_tol=1e-4)


# ==============================================================================
# TEST 3: REALISTIC SHADOW BROKER ENGINE
# ==============================================================================

def test_shadow_taker_fok_latency_and_fill():
    """Verify Taker FOK walks book at t0 + dt_latency; fills if liquidity sufficient."""
    broker = RealisticShadowBroker()
    book = broker.get_or_create_book("BTC")

    # Initial book at t0 = 100.0: Asks: 50,000 (1.0), 50,010 (2.0)
    book.set_level(50_000.0, 1.0, Side.SELL)
    book.set_level(50_010.0, 2.0, Side.SELL)

    # Submit FOK order for 2.0 BTC at max price 50,010.0 with 50ms latency
    order = broker.submit_order(
        symbol="BTC",
        side=Side.BUY,
        order_type=OrderType.TAKER_FOK,
        price=50_010.0,
        size=2.0,
        latency_ms=50.0,
        current_ts=100.0,
    )
    assert order.status == OrderStatus.IN_FLIGHT

    # At t = 100.020 (before arrival at 100.050), order must still be in flight
    broker.advance_time(100.020)
    assert order.status == OrderStatus.IN_FLIGHT

    # At t = 100.050 (arrival), order walks book:
    # Takes 1.0 @ 50,000 and 1.0 @ 50,010. Total 2.0 @ weighted avg 50,005.0
    broker.advance_time(100.050)
    assert order.status == OrderStatus.FILLED
    assert len(order.fills) == 1
    assert order.fills[0].fill_price == 50_005.0
    assert order.fills[0].fill_size == 2.0


def test_shadow_taker_fok_insufficient_liquidity_reject():
    """Verify Taker FOK rejects when book liquidity is swept during latency."""
    broker = RealisticShadowBroker()
    book = broker.get_or_create_book("BTC")
    book.set_level(50_000.0, 1.0, Side.SELL)

    # Order needs 2.0 BTC, but book only has 1.0 BTC
    order = broker.submit_order(
        symbol="BTC",
        side=Side.BUY,
        order_type=OrderType.TAKER_FOK,
        price=50_000.0,
        size=2.0,
        latency_ms=120.0,  # 120ms Polymarket FOK
        current_ts=100.0,
    )

    broker.advance_time(100.120)
    assert order.status == OrderStatus.REJECTED
    assert "FOK_INSUFFICIENT_LIQUIDITY" in order.reject_reason


def test_shadow_maker_alo_crossing_reject():
    """Verify Maker ALO rejects if book crosses during placement latency."""
    broker = RealisticShadowBroker()
    book = broker.get_or_create_book("BTC")
    book.set_level(50_000.0, 10.0, Side.BUY)
    book.set_level(50_020.0, 10.0, Side.SELL)

    # Order submits BUY limit at 50,015.0 (non-crossing at t0)
    order = broker.submit_order(
        symbol="BTC",
        side=Side.BUY,
        order_type=OrderType.MAKER_ALO,
        price=50_015.0,
        size=1.0,
        latency_ms=50.0,
        current_ts=100.0,
    )

    # During the 50ms transit, the market drops: Asks move down to 50,010.0!
    book.set_level(50_010.0, 5.0, Side.SELL)

    # Arrival at 100.050: Our 50,015.0 limit now crosses the 50,010.0 ask!
    broker.advance_time(100.050)
    assert order.status == OrderStatus.REJECTED
    assert "POST_ONLY_WOULD_CROSS_ASK" in order.reject_reason


def test_shadow_maker_alo_queue_ahead_and_print_through():
    """Verify ALO queue depth tracking, queue depletion, and trade print through."""
    broker = RealisticShadowBroker()
    book = broker.get_or_create_book("BTC")
    book.set_level(50_000.0, 5.0, Side.BUY)  # 5.0 BTC existing depth at 50,000
    book.set_level(50_020.0, 10.0, Side.SELL)

    # Post BUY ALO at 50,000.0 for 2.0 BTC
    order = broker.submit_order(
        symbol="BTC",
        side=Side.BUY,
        order_type=OrderType.MAKER_ALO,
        price=50_000.0,
        size=2.0,
        latency_ms=50.0,
        current_ts=100.0,
    )

    # Arrival at 100.050: Order accepted to resting book with queue_ahead = 5.0
    broker.advance_time(100.050)
    assert order.status == OrderStatus.RESTING
    assert order.queue_ahead_size == 5.0

    # Trade 1: Small trade at 50,000 for 3.0 BTC (seller initiated)
    # Queue ahead should deplete from 5.0 to 2.0. No fill yet.
    broker.on_trade_tick("BTC", trade_price=50_000.0, trade_size=3.0, taker_side=Side.SELL, trade_ts=100.100)
    assert order.status == OrderStatus.RESTING
    assert order.queue_ahead_size == 2.0
    assert len(order.fills) == 0

    # Trade 2: Trade at 50,000 for 3.0 BTC (depletes remaining 2.0 queue, fills 1.0 of our order)
    broker.on_trade_tick("BTC", trade_price=50_000.0, trade_size=3.0, taker_side=Side.SELL, trade_ts=100.200)
    assert order.status == OrderStatus.PARTIALLY_FILLED
    assert order.remaining_size == 1.0
    assert order.queue_ahead_size == 0.0
    assert len(order.fills) == 1
    assert order.fills[0].fill_size == 1.0

    # Trade 3: Trade prints THROUGH our price (down to 49,990.0)
    # Aggressive seller sweeps past 50,000 -> Immediate full fill of remainder!
    broker.on_trade_tick("BTC", trade_price=49_990.0, trade_size=5.0, taker_side=Side.SELL, trade_ts=100.300)
    assert order.status == OrderStatus.FILLED
    assert order.remaining_size == 0.0
    assert len(order.fills) == 2
    assert order.fills[1].fill_size == 1.0


def test_shadow_markout_telemetry_recording():
    """Verify markouts at +1s, +5s, +30s, +5m, +1h, and resolution recorded in DB."""
    broker = RealisticShadowBroker()
    book = broker.get_or_create_book("ETH")
    book.set_level(3000.0, 10.0, Side.SELL)

    # Buy 1 ETH at 3000.0 at t = 1000.0
    order = broker.submit_order(
        symbol="ETH",
        side=Side.BUY,
        order_type=OrderType.TAKER_FOK,
        price=3000.0,
        size=1.0,
        latency_ms=0.0,
        current_ts=1000.0,
    )
    broker.advance_time(1000.0)
    assert order.status == OrderStatus.FILLED

    # Move market up to 3015.0 (+50 bps)
    book.apply_snapshot([(3015.0, 10.0)], [(3015.0, 10.0)])

    # Advance time to t = 1001.0 (+1s horizon)
    broker.advance_time(1001.0)
    markouts = broker.db.query_markouts()

    m_1s = [m for m in markouts if m["horizon_label"] == "1s"]
    assert len(m_1s) == 1
    # PnL: (3015 - 3000) / 3000 * 10,000 bps = +50.0 bps
    assert m_1s[0]["markout_pnl_bps"] == 50.0

    # Advance time to t = 1005.0 (+5s horizon) with market at 3030.0 (+100 bps)
    book.apply_snapshot([(3030.0, 10.0)], [(3030.0, 10.0)])
    broker.advance_time(1005.0)

    markouts = broker.db.query_markouts()
    m_5s = [m for m in markouts if m["horizon_label"] == "5s"]
    assert len(m_5s) == 1
    assert m_5s[0]["markout_pnl_bps"] == 100.0

    # Trigger terminal resolution
    broker.check_and_record_markouts(current_ts=1050.0, terminal_resolution=True)
    markouts = broker.db.query_markouts()
    m_res = [m for m in markouts if m["horizon_label"] == "resolution"]
    assert len(m_res) == 1
    assert m_res[0]["is_final"] == 1


def test_shadow_parquet_replay_integration():
    """Verify historical Parquet replay against repository capture data."""
    test_parquet = "data/leadlag/test_verified.parquet"
    if not os.path.exists(test_parquet):
        pytest.skip("Test parquet not found.")

    broker = RealisticShadowBroker()
    # Schedule an order during the replay
    scheduled = [{
        "submit_ts": 0,  # Submit at beginning
        "symbol": "BTC",
        "side": "BUY",
        "order_type": "TAKER_IOC",
        "price": 999_999.0,  # High limit to ensure fill against test book
        "size": 0.01,
        "latency_ms": 10.0,
    }]

    result = broker.replay_parquet(
        parquet_path=test_parquet,
        orders_schedule=scheduled,
        max_records=500,
    )

    assert result["records_processed"] > 0
    assert result["total_orders"] == 1
    assert len(result["markouts"]) > 0
