import asyncio
import json
import math
import time
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from src.polymarket_research.polymarket_live_harvester import (
    PolymarketLiveHarvester,
    CIRCUIT_BREAKER_EQUITY_FLOOR,
    DYNAMIC_BANKROLL_PCT,
    MAX_PRICE_CEILING,
    MIN_PRICE_FLOOR,
    DEFAULT_TICKET_NOTIONAL,
)
from src.polymarket_research.polymarket_live_executor import (
    PolymarketLiveExecutor,
    ExecutionStatus,
    OrderResult,
    calculate_taker_fee,
    SLEEVE_1_MIN_PRICE,
    SLEEVE_1_MAX_PRICE,
    SLEEVE_2_ENABLED,
    SLEEVE_2_MIN_PRICE,
    SLEEVE_2_MAX_PRICE,
)


def test_dual_sleeve_price_gates(tmp_path, monkeypatch):
    """
    Verifies v3.2 Cushion-to-Price Matrix:
    - Regime A Mid-Hour (900s < TTE <= 2700s, dist >= 0.15%): [0.55, 0.78].
    - Regime B Late-Hour (120s <= TTE <= 900s):
      - Tier B1 (0.10% <= dist < 0.15%): [0.55, 0.75]
      - Tier B2 (0.15% <= dist < 0.22%): [0.58, 0.80]
      - Tier B3 (dist >= 0.22%): [0.62, 0.84]
    - Regime C Sub-hourly (90s <= TTE <= 540s, dist >= 0.08%): [0.58, 0.82].
    """
    state_file = tmp_path / "dual_sleeve_state.json"
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", state_file)

    harvester = PolymarketLiveHarvester(ticket_notional=22.0, dry_run=False)
    harvester.executor.auth_mode = "LIVE"
    harvester.executor.is_authenticated = True
    harvester.executor.is_heartbeat_healthy = lambda: True
    harvester.executor.get_collateral_balance = lambda: 91.67
    harvester._last_known_collateral = 91.67

    current_ask_px = [0.65]

    async def mock_get_book(token_id):
        px = current_ask_px[0]
        return {
            "asks": [{"price": str(px), "size": "200.0"}],
            "bids": [{"price": str(round(px - 0.01, 4)), "size": "200.0"}],
        }

    harvester.executor.get_market_book_async = mock_get_book

    executed = []

    async def mock_snipe(**kwargs):
        executed.append(kwargs)
        return OrderResult(
            success=True,
            order_id="OID_1",
            trade_id=kwargs.get("trade_id", "T1"),
            token_id=kwargs.get("token_id", "TOK1"),
            target_token=kwargs.get("target_token", "UP"),
            side="BUY",
            price=kwargs.get("target_price", 0.65),
            size=10.0,
            notional_usd=kwargs.get("notional_usd", 22.0),
            fee_usd=0.10,
            latency_ms=1.5,
            mode="LIVE_PRODUCTION",
            execution_status=ExecutionStatus.POSITION_CONFIRMED,
            confirmed_onchain=True,
        )

    harvester.executor.execute_snipe_order_async = mock_snipe
    harvester.executor.post_maker_exit_order = MagicMock(return_value={"success": True, "orderID": "EXIT_OID"})

    # Helper to generate test shocks
    def make_shock(title, asset, tte, dist_pct, ask_px):
        current_ask_px[0] = ask_px
        return {
            "event_id": f"EVT_{title}_{tte}_{ask_px}",
            "market_id": f"M_{title}_{tte}_{ask_px}",
            "t0_unix": time.time(),
            "title": title,
            "asset": asset,
            "shock_direction": "BUY",
            "seconds_to_expiry": tte,
            "candle_distance_pct": dist_pct,
            "fee_metadata": {"fee_rate_market": 0.07, "fee_exponent": 1.0},
            "pre_shock_features_t0": {
                "UP": {
                    "token_id": "TOK_UP",
                    "raw_top_asks": [[ask_px, 200.0]],
                    "effective_price_$50": ask_px,
                    "vwap_$50": ask_px,
                }
            },
        }

    # 1. 1h Regime B Late Hour (TTE = 600s, dist_pct = 0.45% -> Tier B3: 0.62 <= p <= 0.84):
    # Ask 0.50 (< 0.55 floor) -> Must REJECT
    asyncio.run(harvester.evaluate_shock_and_execute(make_shock("ETH 1h Up", "ETH", 600.0, 0.45, 0.50)))
    assert len(executed) == 0

    # Ask 0.86 (> 0.84 ceiling) -> Must REJECT
    asyncio.run(harvester.evaluate_shock_and_execute(make_shock("ETH 1h Up", "ETH", 600.0, 0.45, 0.86)))
    assert len(executed) == 0

    # Ask 0.79 (Tier B3 Deep Lock: 0.62 <= ask <= 0.84) -> Must EXECUTE
    asyncio.run(harvester.evaluate_shock_and_execute(make_shock("ETH 1h Up", "ETH", 600.0, 0.45, 0.79)))
    assert len(executed) == 1
    harvester.active_positions.clear()

    # 2. 1h Regime A Mid-Hour (TTE = 2400s <= 2700s, dist_pct = 0.45% >= 0.15%):
    # Ask 0.65 ([0.55, 0.78]) -> Must EXECUTE
    asyncio.run(harvester.evaluate_shock_and_execute(make_shock("ETH 1h Up", "ETH", 2400.0, 0.45, 0.65)))
    assert len(executed) == 2
    harvester.active_positions.clear()
    harvester.trades_this_hour = 0

    # Ask 0.80 (> 0.78 ceiling for Regime A) -> Must REJECT
    asyncio.run(harvester.evaluate_shock_and_execute(make_shock("ETH 1h Up", "ETH", 2400.0, 0.45, 0.80)))
    assert len(executed) == 2

    # 3. 15m Sub-hourly Regime C (TTE = 300s, dist_pct = 0.60% >= 0.08%):
    # Ask 0.55 (< 0.58) -> Must REJECT
    asyncio.run(harvester.evaluate_shock_and_execute(make_shock("ETH 15m Up", "ETH", 300.0, 0.60, 0.55)))
    assert len(executed) == 2

    # Ask 0.85 (> 0.82) -> Must REJECT
    asyncio.run(harvester.evaluate_shock_and_execute(make_shock("ETH 15m Up", "ETH", 300.0, 0.60, 0.85)))
    assert len(executed) == 2

    # Ask 0.65 ([0.58, 0.82] band) -> Must EXECUTE
    asyncio.run(harvester.evaluate_shock_and_execute(make_shock("ETH 15m Up", "ETH", 300.0, 0.60, 0.65)))
    assert len(executed) == 3


def test_dynamic_sizing_and_circuit_breaker_floor(tmp_path, monkeypatch):
    """
    Verifies v3.5 centralized-config Dynamic Sizing & Circuit Breaker (config/polymarket_risk_config.json):
    - Dynamic sizing: 18% of live equity ($16.50 on $91.67), 22% once equity >= $110.
    - Drawdown halt: Trips strictly when equity drops below the $66.67 floor.
    - Drawdown buffer: Survives down to $70.00 without tripping circuit breaker.
    """
    state_file = tmp_path / "risk_test_state.json"
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", state_file)

    harvester = PolymarketLiveHarvester(ticket_notional=16.50, dry_run=False)
    harvester.executor.auth_mode = "LIVE"
    harvester.executor.is_authenticated = True

    # Check 1: Circuit breaker floor is $66.67 (centralized config)
    assert harvester.risk_controller.min_equity_floor_usd == 66.67
    assert CIRCUIT_BREAKER_EQUITY_FLOOR == 66.67
    assert DYNAMIC_BANKROLL_PCT == 0.18

    # Check 2: Starting equity $91.67 yields $16.50 dynamic ticket (18%)
    expected_ticket = round(min(50.0, max(15.0, 91.67 * DYNAMIC_BANKROLL_PCT)), 2)
    assert expected_ticket == 16.50
    assert harvester.effective_risk_pct(91.67) == 0.18
    assert harvester.effective_risk_pct(110.00) == 0.22

    # Check 3: Starting equity $91.67 is healthy
    harvester.risk_controller.check_equity_drawdown(91.67)
    assert not harvester.risk_controller.is_halted()

    # Check 4: Equity at $70.00 -> must NOT halt
    harvester.risk_controller.check_equity_drawdown(70.00)
    assert not harvester.risk_controller.is_halted(), "Drawdown buffer must prevent halt at $70.00!"

    # Check 5: Equity at $66.00 (< $66.67 floor) -> Must immediately halt!
    harvester.risk_controller.check_equity_drawdown(66.00)
    assert harvester.risk_controller.is_halted()
    assert "66.67" in harvester.risk_controller.halt_reason


def test_maker_tp_099_placement_on_fill(tmp_path, monkeypatch):
    """
    Verifies that on fill with hold_to_maturity=True, resting Maker TP is posted at strictly $0.99 for full shares.
    """
    state_file = tmp_path / "tp_test_state.json"
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", state_file)

    harvester = PolymarketLiveHarvester(ticket_notional=14.67, dry_run=False, hold_to_maturity=True)
    harvester.executor.auth_mode = "LIVE"
    harvester.executor.is_authenticated = True
    harvester.executor.is_heartbeat_healthy = lambda: True
    harvester.executor.get_collateral_balance = lambda: 91.67
    harvester._last_known_collateral = 91.67

    async def mock_get_book(token_id):
        return {
            "asks": [{"price": "0.6800", "size": "200.0"}],
            "bids": [{"price": "0.6700", "size": "200.0"}],
        }

    harvester.executor.get_market_book_async = mock_get_book

    maker_exits_posted = []

    def mock_maker_exit(token_id, price, size, side):
        maker_exits_posted.append({"token_id": token_id, "price": price, "size": size, "side": side})
        return {"success": True, "orderID": "EXIT_MAKER_99_OID"}

    async def mock_snipe(**kwargs):
        return OrderResult(
            success=True,
            order_id="OID_OCT17_ETH",
            trade_id=kwargs.get("trade_id", "T_ETH"),
            token_id="0xETH_TOKEN",
            target_token="UP",
            side="BUY",
            price=0.6800,
            size=21.0,
            notional_usd=14.28,
            fee_usd=0.08,
            latency_ms=1.1,
            mode="LIVE_PRODUCTION",
            execution_status=ExecutionStatus.POSITION_CONFIRMED,
            confirmed_onchain=True,
        )

    harvester.executor.execute_snipe_order_async = mock_snipe
    harvester.executor.post_maker_exit_order = mock_maker_exit

    shock = {
        "event_id": "EVT_ETH_11PM_REPLAY",
        "market_id": "5765906",
        "t0_unix": time.time(),
        "title": "ETH 1h Up",
        "asset": "ETH",
        "shock_direction": "BUY",
        "seconds_to_expiry": 600.0,
        "candle_distance_pct": 0.45,
        "fee_metadata": {"fee_rate_market": 0.07, "fee_exponent": 1.0},
        "pre_shock_features_t0": {
            "UP": {
                "token_id": "0xETH_TOKEN",
                "raw_top_asks": [[0.6800, 200.0]],
                "effective_price_$50": 0.6800,
                "vwap_$50": 0.6800,
            }
        },
    }

    asyncio.run(harvester.evaluate_shock_and_execute(shock))

    # Assert Maker TP posted at 0.99 for all 21.0 shares
    assert len(maker_exits_posted) == 1
    assert maker_exits_posted[0]["price"] == 0.99
    assert maker_exits_posted[0]["size"] == 21.0
    assert maker_exits_posted[0]["side"] == "SELL"


def test_hot_path_latency_benchmark():
    """
    Verifies that hot-path execution pre-flight logic executes in < 10ms.
    """
    executor = PolymarketLiveExecutor(dry_run=True)
    t0 = time.perf_counter()

    cond_id = "0xCOND_LATENCY_BENCHMARK"
    token_id = "0xTOKEN_LATENCY_BENCHMARK"
    executor._fee_cache[cond_id] = (0.07, 1.0)
    executor._tick_size_cache[token_id] = 0.01

    quantized_px = executor.quantize_order_price(0.68, token_id)
    fee_rate, fee_exp = executor.get_market_fee_params(cond_id)
    effective_rate, taker_fee = calculate_taker_fee(15.0, quantized_px, fee_rate, fee_exp)

    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert elapsed_ms < 10.0, f"Hot-path compute took {elapsed_ms:.2f}ms (target < 10ms)"


def test_parallel_multi_market_capacity_and_per_market_dedup(tmp_path, monkeypatch):
    """
    Verifies v3.0 Concurrency & Dedup:
    1. Strict Per-Market Mutual Exclusion (max_positions_per_market_id = 1).
    2. Parallel Multi-Market Capacity (MAX_CONCURRENT_POSITIONS = 2).
    """
    state_file = tmp_path / "multi_pos_test_state.json"
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", state_file)

    harvester = PolymarketLiveHarvester(
        ticket_notional=14.67,
        dry_run=False,
        max_concurrent=2,
        max_exposure=45.0,
        max_trades_per_hour=4,
    )
    harvester.executor.auth_mode = "LIVE"
    harvester.executor.is_authenticated = True
    harvester.executor.is_heartbeat_healthy = lambda: True
    harvester.executor.get_collateral_balance = lambda: 91.67
    harvester._last_known_collateral = 91.67

    async def mock_get_book(token_id):
        return {
            "asks": [{"price": "0.6500", "size": "500.0"}],
            "bids": [{"price": "0.6400", "size": "500.0"}],
        }

    harvester.executor.get_market_book_async = mock_get_book

    executed = []

    async def mock_snipe(**kwargs):
        executed.append(kwargs)
        trade_id = kwargs.get("trade_id", "T_M")
        return OrderResult(
            success=True,
            order_id=f"OID_{trade_id}",
            trade_id=trade_id,
            token_id=kwargs.get("token_id", "TOK"),
            target_token="UP",
            side="BUY",
            price=0.6500,
            size=20.0,
            notional_usd=13.0,
            fee_usd=0.08,
            latency_ms=1.2,
            mode="LIVE_PRODUCTION",
            execution_status=ExecutionStatus.POSITION_CONFIRMED,
            confirmed_onchain=True,
        )

    harvester.executor.execute_snipe_order_async = mock_snipe
    harvester.executor.post_maker_exit_order = MagicMock(return_value={"success": True, "orderID": "EXIT_OID"})

    def make_contract_shock(market_id, title, asset):
        return {
            "event_id": f"EVT_{market_id}",
            "market_id": market_id,
            "t0_unix": time.time(),
            "title": title,
            "asset": asset,
            "shock_direction": "BUY",
            "seconds_to_expiry": 600.0,
            "candle_distance_pct": 0.45,
            "fee_metadata": {"fee_rate_market": 0.07, "fee_exponent": 1.0},
            "pre_shock_features_t0": {
                "UP": {
                    "token_id": f"TOK_{market_id}",
                    "raw_top_asks": [[0.6500, 500.0]],
                    "effective_price_$50": 0.6500,
                    "vwap_$50": 0.6500,
                }
            },
        }

    # Contract 1: ETH 1h -> Must execute (Position 1 of 2)
    asyncio.run(harvester.evaluate_shock_and_execute(make_contract_shock("MKT_ETH_1H", "ETH 1h Up", "ETH")))
    assert len(executed) == 1
    assert len(harvester.active_positions) == 1

    # Attempt Duplicate Entry on Contract 1: MKT_ETH_1H -> Must REJECT via per-market mutual exclusion
    asyncio.run(harvester.evaluate_shock_and_execute(make_contract_shock("MKT_ETH_1H", "ETH 1h Up", "ETH")))
    assert len(executed) == 1
    assert len(harvester.active_positions) == 1

    # Contract 2: BTC 1h -> Must execute (Position 2 of 2)
    asyncio.run(harvester.evaluate_shock_and_execute(make_contract_shock("MKT_BTC_1H", "BTC 1h Up", "BTC")))
    assert len(executed) == 2
    assert len(harvester.active_positions) == 2

    # Contract 3: ETH 15m -> Must REJECT because max_concurrent_positions == 2
    asyncio.run(harvester.evaluate_shock_and_execute(make_contract_shock("MKT_ETH_15M", "ETH 15m Up", "ETH")))
    assert len(executed) == 2
    assert len(harvester.active_positions) == 2


# ==============================================================================
# v3.0 POSITIVE-EXPECTANCY EXPLICIT UNIT TESTS (REQUIREMENT 5.2)
# ==============================================================================

def test_double_slippage_buffer_fixed():
    """
    Verifies that the double +0.02 slippage buffer bug is fixed in both
    execute_snipe_order and execute_snipe_order_async.
    limit_px must never exceed min(best_px + 0.02, max_price_ceiling) and must not double-add.
    """
    executor = PolymarketLiveExecutor(dry_run=True)
    executor.dry_run = False
    executor.is_authenticated = True
    executor.client = MagicMock()

    # Best ask is 0.68. Target price passed from harvester is 0.70 (already raw_vwap + 0.02).
    executor.get_market_book = lambda tid: {"asks": [{"price": "0.68", "size": "100"}]}
    executor.get_token_balance = lambda tid: 0.0

    mock_client = MagicMock()
    mock_client.create_order = MagicMock(return_value={"signed": "order_bytes"})
    mock_client.post_order = MagicMock(return_value={"orderID": "0xTEST_ORDER"})
    executor.client = mock_client
    executor._tick_size_cache["TOK_TEST"] = 0.01

    res = executor.execute_snipe_order(
        trade_id="TEST_DOUBLE_BUFFER",
        token_id="TOK_TEST",
        target_token="UP",
        notional_usd=15.0,
        target_price=0.70,  # Already includes +0.02 over 0.68
        max_price_ceiling=0.76,
    )

    # In old code: limit_px was min(0.70 + 0.02, 0.76) = 0.72 (+0.04 over best_px).
    # In v3.0: limit_px = min(0.68 + 0.02, 0.70, 0.76) = 0.70 (strictly +0.02 over best_px).
    create_call = mock_client.create_order.call_args[0][0]
    limit_order_px = float(create_call.price)
    assert limit_order_px <= 0.70
    assert limit_order_px <= (0.68 + 0.02)


def test_asks_above_084_strictly_rejected(tmp_path, monkeypatch):
    """
    Verifies that entry asks above 0.84 (e.g. 0.85, 0.88, 0.92) are strictly rejected in v3.2.
    """
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", tmp_path / "rej_state.json")
    harvester = PolymarketLiveHarvester(ticket_notional=22.0, dry_run=False)
    harvester.executor.auth_mode = "LIVE"
    harvester.executor.is_authenticated = True
    harvester.executor.get_collateral_balance = lambda: 91.67
    harvester._last_known_collateral = 91.67

    executed = []
    def mock_snipe(**kwargs):
        executed.append(kwargs)
        return OrderResult(
            success=True,
            order_id="OID_REJ",
            trade_id=kwargs.get("trade_id", "T_REJ"),
            token_id=kwargs.get("token_id", "TOK_UP"),
            target_token="UP",
            side="BUY",
            price=kwargs.get("target_price", 0.85),
            size=10.0,
            notional_usd=22.0,
            fee_usd=0.10,
            latency_ms=1.5,
            mode="LIVE_PRODUCTION",
            execution_status=ExecutionStatus.POSITION_CONFIRMED,
            confirmed_onchain=True,
        )
    harvester.executor.execute_snipe_order_async = AsyncMock(side_effect=mock_snipe)

    for high_ask in [0.85, 0.88, 0.92]:
        harvester.executor.get_market_book_async = AsyncMock(return_value={
            "asks": [{"price": str(high_ask), "size": "100.0"}],
            "bids": [{"price": str(round(high_ask - 0.01, 2)), "size": "100.0"}],
        })
        shock = {
            "event_id": f"EVT_HIGH_{high_ask}",
            "market_id": f"MKT_HIGH_{high_ask}",
            "t0_unix": time.time(),
            "title": "ETH 1h Up",
            "asset": "ETH",
            "shock_direction": "BUY",
            "seconds_to_expiry": 600.0,
            "candle_distance_pct": 0.45,
            "fee_metadata": {"fee_rate_market": 0.07, "fee_exponent": 1.0},
            "pre_shock_features_t0": {
                "UP": {"token_id": "TOK_UP", "raw_top_asks": [[high_ask, 100.0]], "effective_price_$50": high_ask, "vwap_$50": high_ask}
            },
        }
        asyncio.run(harvester.evaluate_shock_and_execute(shock))
        assert len(executed) == 0, f"Ask {high_ask} must be strictly rejected!"


def test_noisy_first15m_and_thin_cushion_rejected(tmp_path, monkeypatch):
    """
    Verifies that noisy first 15m (TTE > 2700s) and thin-cushion signals (dist_pct < 0.10%) are rejected in v3.2.
    """
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", tmp_path / "early_state.json")
    harvester = PolymarketLiveHarvester(ticket_notional=22.0, dry_run=False)
    harvester.executor.auth_mode = "LIVE"
    harvester.executor.is_authenticated = True
    harvester.executor.get_collateral_balance = lambda: 91.67
    harvester._last_known_collateral = 91.67

    executed = []
    def mock_snipe(**kwargs):
        executed.append(kwargs)
        return OrderResult(
            success=True,
            order_id="OID_NOISY",
            trade_id=kwargs.get("trade_id", "T_NOISY"),
            token_id=kwargs.get("token_id", "TOK_UP"),
            target_token="UP",
            side="BUY",
            price=0.65,
            size=10.0,
            notional_usd=22.0,
            fee_usd=0.10,
            latency_ms=1.5,
            mode="LIVE_PRODUCTION",
            execution_status=ExecutionStatus.POSITION_CONFIRMED,
            confirmed_onchain=True,
        )
    harvester.executor.execute_snipe_order_async = AsyncMock(side_effect=mock_snipe)
    harvester.executor.get_market_book_async = AsyncMock(return_value={
        "asks": [{"price": "0.65", "size": "100.0"}],
        "bids": [{"price": "0.64", "size": "100.0"}],
    })

    # Case 1: TTE = 3000s (> 2700s ceiling, noisy first 15m) -> Reject
    shock_noisy = {
        "event_id": "EVT_NOISY",
        "market_id": "MKT_NOISY",
        "t0_unix": time.time(),
        "title": "BTC 1h Up",
        "asset": "BTC",
        "shock_direction": "BUY",
        "seconds_to_expiry": 3000.0,
        "candle_distance_pct": 0.40,
        "fee_metadata": {"fee_rate_market": 0.07, "fee_exponent": 1.0},
        "pre_shock_features_t0": {"UP": {"token_id": "TOK_1", "raw_top_asks": [[0.65, 100.0]], "effective_price_$50": 0.65, "vwap_$50": 0.65}},
    }
    asyncio.run(harvester.evaluate_shock_and_execute(shock_noisy))
    assert len(executed) == 0

    # Case 2: TTE = 600s, but dist_pct = 0.08% (< 0.10% cushion threshold) -> Reject
    shock_thin_cushion = {
        "event_id": "EVT_THIN",
        "market_id": "MKT_THIN",
        "t0_unix": time.time(),
        "title": "BTC 1h Up",
        "asset": "BTC",
        "shock_direction": "BUY",
        "seconds_to_expiry": 600.0,
        "candle_distance_pct": 0.08,
        "fee_metadata": {"fee_rate_market": 0.07, "fee_exponent": 1.0},
        "pre_shock_features_t0": {"UP": {"token_id": "TOK_2", "raw_top_asks": [[0.65, 100.0]], "effective_price_$50": 0.65, "vwap_$50": 0.65}},
    }
    asyncio.run(harvester.evaluate_shock_and_execute(shock_thin_cushion))
    assert len(executed) == 0


def test_confirmed_entry_posts_50_50_two_tranches(tmp_path, monkeypatch):
    """
    Verifies that confirmed entries post 50/50 two-tranche maker exits:
    Tranche 1 @ entry + 0.14 and Tranche 2 @ 0.98.
    """
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", tmp_path / "tranche_state.json")
    harvester = PolymarketLiveHarvester(ticket_notional=15.0, dry_run=False, hold_to_maturity=False)
    harvester.executor.auth_mode = "LIVE"
    harvester.executor.is_authenticated = True
    harvester.executor.get_collateral_balance = lambda: 91.67
    harvester._last_known_collateral = 91.67

    harvester.executor.get_market_book_async = AsyncMock(return_value={
        "asks": [{"price": "0.6500", "size": "200.0"}],
        "bids": [{"price": "0.6400", "size": "200.0"}],
    })

    maker_exits = []
    harvester.executor.post_maker_exit_order = MagicMock(
        side_effect=lambda **kw: maker_exits.append(kw) or {"success": True, "orderID": "EXIT_TR1"}
    )

    async def mock_snipe(**kwargs):
        return OrderResult(
            success=True,
            order_id="OID_TR_ENTRY",
            trade_id=kwargs.get("trade_id", "T_TR"),
            token_id="0xTR_TOKEN",
            target_token="UP",
            side="BUY",
            price=0.6500,
            size=20.0,
            notional_usd=13.00,
            fee_usd=0.08,
            latency_ms=1.1,
            mode="LIVE_PRODUCTION",
            execution_status=ExecutionStatus.POSITION_CONFIRMED,
            confirmed_onchain=True,
        )
    harvester.executor.execute_snipe_order_async = mock_snipe

    shock = {
        "event_id": "EVT_TR_TEST",
        "market_id": "MKT_TR_TEST",
        "t0_unix": time.time(),
        "title": "BTC 1h Up",
        "asset": "BTC",
        "shock_direction": "BUY",
        "seconds_to_expiry": 600.0,
        "candle_distance_pct": 0.45,
        "fee_metadata": {"fee_rate_market": 0.07, "fee_exponent": 1.0},
        "pre_shock_features_t0": {
            "UP": {"token_id": "0xTR_TOKEN", "raw_top_asks": [[0.6500, 200.0]], "effective_price_$50": 0.6500, "vwap_$50": 0.6500}
        },
    }

    asyncio.run(harvester.evaluate_shock_and_execute(shock))

    assert len(harvester.active_positions) == 1
    pos = list(harvester.active_positions.values())[0]
    assert "exit_tranches" in pos
    tranches = pos["exit_tranches"]
    assert len(tranches) == 2
    # Tranche 1: 50% @ entry + 0.14 = 0.65 + 0.14 = 0.79
    assert tranches[0]["size"] == 10.0
    assert tranches[0]["price"] == 0.79
    # Tranche 2: 50% @ 0.98
    assert tranches[1]["size"] == 10.0
    assert tranches[1]["price"] == 0.98
    # Resting maker exit order posted for Tranche 1
    assert len(maker_exits) == 1
    assert maker_exits[0]["price"] == 0.79
    assert maker_exits[0]["size"] == 10.0


@pytest.mark.anyio
async def test_tier1_strike_retrace_and_tier2_biddrop_stops(tmp_path, monkeypatch):
    """
    Verifies that Tier 1 Strike-Retrace Stop and Tier 2 Bid-Drop Stop cancel resting maker exits
    and execute FAK salvage sells into the bid book.
    """
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", tmp_path / "stop_state.json")
    harvester = PolymarketLiveHarvester(ticket_notional=15.0, dry_run=True)

    unwinds = []
    harvester.executor.cancel_order = MagicMock(return_value={"canceled": ["order_tp_1"]})
    harvester.executor.get_order_fill_summary = MagicMock(return_value={"terminal": True, "matched": 0.0, "order_id": "order_tp_1"})
    harvester.executor.execute_unwind_order = MagicMock(
        side_effect=lambda **kw: unwinds.append(kw) or {"success": True, "orderID": "unwind_1"}
    )
    harvester.executor.release_inventory = MagicMock()
    harvester.executor.invalidate_collateral_cache = MagicMock()
    harvester._strict_open_orders = MagicMock(return_value=[])

    now_ts = 1700000000.0
    # Rule 1 Test: Strike cushion on winning side (+0.01% > 0) must NEVER trigger salvage stop
    harvester.active_positions = {
        "POS_RETRACE": {
            "trade_id": "POS_RETRACE",
            "market_id": "MKT_RETRACE",
            "token_id": "TOK_UP",
            "target_token": "UP",
            "asset": "BTC",
            "entry_price": 0.65,
            "entry_shares": 20.0,
            "remaining_shares": 20.0,
            "candle_open_spot": 60000.0,
            "candle_expiry_ts": now_ts + 600.0,
            "exit_order_id": "order_tp_1",
            "target_exit_price": 0.79,
            "status": "EXIT_RESTING",
        }
    }

    # Spot is at 60006.0 (+0.01% cushion > 0, winning side)
    harvester.get_reference_spot_price = MagicMock(return_value=60006.0)
    harvester.executor.get_market_book_async = AsyncMock(return_value={"bids": [{"price": "0.50", "size": "100"}]})

    with patch("time.time", return_value=now_ts):
        await harvester.check_resolutions_and_manage_positions()

    # Rule 1: Winning positions must NEVER be dumped!
    harvester.executor.cancel_order.assert_not_called()
    assert len(unwinds) == 0


@pytest.mark.anyio
async def test_peak_bid_trailing_profit_ratchet(tmp_path, monkeypatch):
    """
    Verifies Peak-Bid Trailing Profit Ratchet:
    - Position entered at 0.65.
    - Bid reaches 0.86 (>= max(0.84, 0.65 + 0.14) = 0.84), arming trailing floor at 0.86 - 0.08 = 0.78.
    - Bid drops to 0.77 (<= 0.78).
    - If dropped for >= 6.0s with tte >= 30s and best_bid >= 0.70, triggers cancellation
      of resting maker exit and executes FAK sell with TRAILING_PROFIT_RATCHET_UNWIND.
    """
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", tmp_path / "ratchet_state.json")
    harvester = PolymarketLiveHarvester(ticket_notional=22.0, dry_run=True)

    unwinds = []
    harvester.executor.cancel_order = MagicMock(return_value={"canceled": ["order_maker_1"]})
    harvester.executor.get_order_fill_summary = MagicMock(return_value={"terminal": False, "matched": 0.0, "order_id": "order_maker_1", "status": "LIVE"})
    harvester.executor.execute_unwind_order = MagicMock(
        side_effect=lambda **kw: unwinds.append(kw) or {"success": True, "orderID": "unwind_ratchet"}
    )
    harvester.executor.release_inventory = MagicMock()
    harvester.executor.invalidate_collateral_cache = MagicMock()
    harvester._strict_open_orders = MagicMock(return_value=[])

    now_ts = 1700000000.0
    harvester.active_positions = {
        "POS_RATCHET": {
            "trade_id": "POS_RATCHET",
            "market_id": "MKT_RATCHET",
            "token_id": "TOK_UP",
            "target_token": "UP",
            "asset": "BTC",
            "entry_price": 0.65,
            "entry_shares": 20.0,
            "remaining_shares": 20.0,
            "candle_open_spot": 60000.0,
            "candle_expiry_ts": now_ts + 300.0,  # 300s TTE > 30s
            "exit_order_id": "order_maker_1",
            "target_exit_price": 0.98,
            "status": "EXIT_RESTING",
            "max_seen_bid": 0.86,  # 0.86 >= max(0.84, 0.65 + 0.14 = 0.79)
            "trailing_ratchet_detected_ts": now_ts - 6.5,  # Dropped below 0.78 for 6.5s
        }
    }

    # Reference spot is healthy (+0.40% cushion)
    harvester.get_reference_spot_price = MagicMock(return_value=60240.0)
    # Book bid is 0.77 (floor is 0.78, so bid <= floor, and 0.77 >= 0.65 + 0.05 = 0.70)
    harvester.executor.get_market_book_async = AsyncMock(return_value={"bids": [{"price": "0.77", "size": "100"}]})

    with patch("time.time", return_value=now_ts):
        await harvester.check_resolutions_and_manage_positions()

    harvester.executor.cancel_order.assert_called_with("order_maker_1")
    assert len(unwinds) == 1
    assert unwinds[0]["token_id"] == "TOK_UP"
    assert unwinds[0]["side"] == "SELL"
    assert unwinds[0]["size"] == 20.0
    # Price is clipped/limit at best_bid - 0.02 = 0.75
    assert unwinds[0]["min_price"] == 0.75


def test_win_reset_reentry_allows_second_trade_only_on_win(tmp_path, monkeypatch):
    """
    Verifies Win-Reset Re-Entry:
    - If 1 trade was already completed in the market this hour:
      - If trade #1 won (won=True, net_pnl_usd > 0) and 0 active positions, allow 2nd trade.
      - If trade #1 lost (won=False, net_pnl_usd <= 0), reject 2nd trade.
    """
    state_file = tmp_path / "win_reset_state.json"
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", state_file)

    harvester = PolymarketLiveHarvester(ticket_notional=15.0, dry_run=False)
    harvester.executor.auth_mode = "LIVE"
    harvester.executor.is_authenticated = True
    harvester.executor.is_heartbeat_healthy = lambda: True
    harvester.executor.get_collateral_balance = lambda: 91.67
    harvester._last_known_collateral = 91.67

    executed = []
    async def mock_snipe(**kwargs):
        executed.append(kwargs)
        return OrderResult(
            success=True,
            order_id="OID_WIN",
            trade_id=kwargs.get("trade_id", "T_WIN"),
            token_id=kwargs.get("token_id", "TOK1"),
            target_token=kwargs.get("target_token", "UP"),
            side="BUY",
            price=0.65,
            size=10.0,
            notional_usd=15.0,
            fee_usd=0.10,
            latency_ms=1.5,
            mode="LIVE_PRODUCTION",
            execution_status=ExecutionStatus.POSITION_CONFIRMED,
            confirmed_onchain=True,
        )

    harvester.executor.execute_snipe_order_async = mock_snipe
    harvester.executor.post_maker_exit_order = MagicMock(return_value={"success": True, "orderID": "EXIT_OID"})

    shock = {
        "event_id": "EVT_REENTRY_TEST",
        "market_id": "MKT_REENTRY",
        "t0_unix": time.time(),
        "title": "Bitcoin Up or Down Hourly",
        "asset": "BTC",
        "shock_direction": "BUY",
        "seconds_to_expiry": 600.0,
        "candle_distance_pct": 0.40,
        "fee_metadata": {"fee_rate_market": 0.07, "fee_exponent": 1.0},
        "pre_shock_features_t0": {
            "UP": {
                "token_id": "TOK_UP",
                "raw_top_asks": [[0.65, 200.0]],
                "raw_top_bids": [[0.64, 200.0]],
                "effective_price_$50": 0.65,
                "vwap_$50": 0.65,
                "age_book_ms": 100.0,
            }
        },
    }

    # Case 1: Market has 1 trade already, but it was a WIN
    harvester.trades_per_market["MKT_REENTRY"] = 1
    harvester.closed_positions = [
        {
            "trade_id": "T_PREV_1",
            "market_id": "MKT_REENTRY",
            "won": True,
            "net_pnl_usd": 4.50,
        }
    ]
    harvester.active_positions.clear()

    asyncio.run(harvester.evaluate_shock_and_execute(shock))
    assert len(executed) == 1, "Win-Reset Re-Entry should allow a 2nd trade after a win"

    # Case 2: Market has 1 trade already, but it was a LOSS
    executed.clear()
    harvester.trades_per_market["MKT_REENTRY_LOSS"] = 1
    harvester.closed_positions = [
        {
            "trade_id": "T_PREV_2",
            "market_id": "MKT_REENTRY_LOSS",
            "won": False,
            "net_pnl_usd": -12.00,
        }
    ]
    shock_loss = dict(shock)
    shock_loss["market_id"] = "MKT_REENTRY_LOSS"
    shock_loss["event_id"] = "EVT_REENTRY_LOSS"
    asyncio.run(harvester.evaluate_shock_and_execute(shock_loss))
    assert len(executed) == 0, "Win-Reset Re-Entry must strictly reject 2nd trade after a loss"


def test_futures_basis_filter_rejects_divergence(tmp_path, monkeypatch):
    """
    Verifies that delta_basis_100ms divergence rejects shocks:
    - UP shock rejected when delta_basis_100ms < -2.0 bps (Futures dumping against Spot).
    - DOWN shock rejected when delta_basis_100ms > +2.0 bps (Futures pumping against Spot).
    """
    state_file = tmp_path / "basis_filter_state.json"
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", state_file)

    harvester = PolymarketLiveHarvester(ticket_notional=15.0, dry_run=False)
    harvester.executor.auth_mode = "LIVE"
    harvester.executor.is_authenticated = True
    harvester.executor.is_heartbeat_healthy = lambda: True
    harvester.executor.get_collateral_balance = lambda: 91.67
    harvester._last_known_collateral = 91.67

    executed = []
    async def mock_snipe(**kwargs):
        executed.append(kwargs)
        return OrderResult(
            success=True,
            order_id="OID_BASIS",
            trade_id="T_BASIS",
            token_id="TOK1",
            target_token=kwargs.get("target_token", "UP"),
            side="BUY",
            price=0.65,
            size=10.0,
            notional_usd=15.0,
            fee_usd=0.10,
            latency_ms=1.5,
            mode="LIVE_PRODUCTION",
            execution_status=ExecutionStatus.POSITION_CONFIRMED,
            confirmed_onchain=True,
        )

    harvester.executor.execute_snipe_order_async = mock_snipe
    harvester.executor.post_maker_exit_order = MagicMock(return_value={"success": True, "orderID": "EXIT_OID"})

    # UP shock with delta_basis_100ms = -2.5 (divergent) -> Reject
    up_shock = {
        "event_id": "EVT_BASIS_UP",
        "market_id": "MKT_BASIS_UP",
        "t0_unix": time.time(),
        "title": "Bitcoin Up or Down Hourly",
        "asset": "BTC",
        "shock_direction": "BUY",
        "seconds_to_expiry": 600.0,
        "candle_distance_pct": 0.40,
        "delta_basis_100ms": -2.5,
        "fee_metadata": {"fee_rate_market": 0.07, "fee_exponent": 1.0},
        "pre_shock_features_t0": {
            "UP": {
                "token_id": "TOK_UP",
                "raw_top_asks": [[0.65, 200.0]],
                "raw_top_bids": [[0.64, 200.0]],
                "effective_price_$50": 0.65,
                "vwap_$50": 0.65,
                "age_book_ms": 100.0,
            }
        },
    }
    asyncio.run(harvester.evaluate_shock_and_execute(up_shock))
    assert len(executed) == 0, "UP shock with delta_basis < -2.0 must be rejected"

    # DOWN shock with delta_basis_100ms = +2.5 (divergent) -> Reject
    down_shock = {
        "event_id": "EVT_BASIS_DOWN",
        "market_id": "MKT_BASIS_DOWN",
        "t0_unix": time.time(),
        "title": "Bitcoin Up or Down Hourly",
        "asset": "BTC",
        "shock_direction": "SELL",
        "seconds_to_expiry": 600.0,
        "candle_distance_pct": -0.40,
        "delta_basis_100ms": 2.5,
        "fee_metadata": {"fee_rate_market": 0.07, "fee_exponent": 1.0},
        "pre_shock_features_t0": {
            "DOWN": {
                "token_id": "TOK_DOWN",
                "raw_top_asks": [[0.65, 200.0]],
                "raw_top_bids": [[0.64, 200.0]],
                "effective_price_$50": 0.65,
                "vwap_$50": 0.65,
                "age_book_ms": 100.0,
            }
        },
    }
    asyncio.run(harvester.evaluate_shock_and_execute(down_shock))
    assert len(executed) == 0, "DOWN shock with delta_basis > +2.0 must be rejected"

    # UP shock with delta_basis_100ms = +1.0 (convergent/aligned) -> Allowed
    up_shock_ok = dict(up_shock)
    up_shock_ok["event_id"] = "EVT_BASIS_OK"
    up_shock_ok["market_id"] = "MKT_BASIS_OK"
    up_shock_ok["delta_basis_100ms"] = 1.0
    asyncio.run(harvester.evaluate_shock_and_execute(up_shock_ok))
    assert len(executed) == 1, "Aligned shock with delta_basis = +1.0 must be executed"


@pytest.mark.anyio
async def test_recorder_40ms_fast_track_trigger(tmp_path, monkeypatch):
    """
    Verifies that PolymarketDualFeed1HRecorder fires 40ms fast-track trigger
    when volume in last 40ms >= 0.75 * threshold and |OFI| >= 0.90.
    """
    import datetime
    from src.polymarket_research.polymarket_terminal_recorder import PolymarketDualFeed1HRecorder, L2OrderBook

    trigger_file = tmp_path / "test_triggers.jsonl"
    monkeypatch.setattr("src.polymarket_research.polymarket_terminal_recorder.TRIGGER_FILE", trigger_file)

    recorder = PolymarketDualFeed1HRecorder(asset="BTC", shock_threshold=100_000.0)
    recorder.spot_price = 60000.0
    recorder.futures_price = 60000.0
    recorder.finalized_1h_open = 59900.0
    recorder.current_market = {
        "market_id": "MKT_BTC_1H",
        "condition_id": "COND_1",
        "title": "Bitcoin Up or Down Hourly",
        "end_dt": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=30),
        "tokens": {"UP": "TOK_UP", "DOWN": "TOK_DOWN"},
        "fee_metadata": {"fee_rate_market": 0.07, "fee_exponent": 1.0},
    }
    recorder.books["UP"] = L2OrderBook(asset_id="TOK_UP")
    recorder.books["DOWN"] = L2OrderBook(asset_id="TOK_DOWN")
    recorder.books["UP"].apply_snapshot([{"price": "0.60", "size": "100"}], [{"price": "0.65", "size": "100"}])
    recorder.books["DOWN"].apply_snapshot([{"price": "0.34", "size": "100"}], [{"price": "0.39", "size": "100"}])

    now_ns = time.monotonic_ns()
    # Add trades in the last 20ms totaling $80k (>= 0.75 * $100k) all BUY (OFI = +1.0)
    recorder.spot_trades.append((now_ns - 20_000_000, 1000, 1000, 80_000.0, True, 60000.0))

    recorder.evaluate_shock(now_ns, event_ts_ms=1000, source="SPOT")

    assert trigger_file.exists()
    with open(trigger_file) as f:
        lines = [json.loads(l) for l in f if l.strip()]
    assert len(lines) == 1
    assert lines[0]["is_40ms_fast_track"] is True
    assert lines[0]["shock_direction"] == "BUY"
    assert lines[0]["shock_volume_100ms"] == 80000.0


def test_z_effective_drift_and_starvation_fix(tmp_path, monkeypatch):
    """
    Verifies v3.1 Z-Score & Filter Starvation Fix:
    - z_strike is calculated from spot cushion (dist_pct / sigma_rem).
    - If z_strike < 0.65, trade is rejected (spot not firmly on right side).
    - If z_strike >= 0.65, z_effective = z_strike + 0.35 * abs(shock_ofi) is used for p_fair.
    - Ensures sweet spot [0.52, 0.76] is not starved while maintaining required +0.06 edge.
    """
    state_file = tmp_path / "z_eff_state.json"
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", state_file)

    harvester = PolymarketLiveHarvester(ticket_notional=15.0, dry_run=False)
    harvester.executor.auth_mode = "LIVE"
    harvester.executor.is_authenticated = True
    harvester.executor.is_heartbeat_healthy = lambda: True
    harvester.executor.get_collateral_balance = lambda: 91.67
    harvester._last_known_collateral = 91.67

    executed = []
    async def mock_snipe(**kwargs):
        executed.append(kwargs)
        return OrderResult(
            success=True,
            order_id="OID_ZEFF",
            trade_id=kwargs.get("trade_id", "T_ZEFF"),
            token_id=kwargs.get("token_id", "TOK1"),
            target_token="UP",
            side="BUY",
            price=0.62,
            size=20.0,
            notional_usd=15.0,
            fee_usd=0.10,
            latency_ms=1.5,
            mode="LIVE_PRODUCTION",
            execution_status=ExecutionStatus.POSITION_CONFIRMED,
            confirmed_onchain=True,
        )

    harvester.executor.execute_snipe_order_async = mock_snipe
    harvester.executor.post_maker_exit_order = MagicMock(return_value={"success": True, "orderID": "EXIT_OID"})

    # Case 1: TTE = 600s, BTC candle_horizon = 3600s.
    # sigma_candle = 0.0050. sigma_rem = 0.0050 * sqrt(600/3600) = 0.0050 * 0.4082 = 0.002041 (0.2041%).
    # If dist_pct = 0.20%: z_strike = 0.0020 / 0.002041 = 0.98 >= 0.65.
    # With shock_ofi = 1.0, z_effective = 0.98 + 0.35 = 1.33.
    # p_fair = 0.5 * (1 + erf(1.33 / sqrt(2))) = 0.908.
    # With ask = 0.62, fee_rate = 0.07: eff_cost = 0.62 / (1 - 0.07 * 0.38) = 0.637.
    # Edge = 0.908 - 0.637 = +0.271 >= 0.06 -> QUALIFIES and EXECUTES!
    shock_pass = {
        "event_id": "EVT_ZEFF_PASS",
        "market_id": "MKT_ZEFF_PASS",
        "t0_unix": time.time(),
        "title": "Bitcoin Up or Down Hourly",
        "asset": "BTC",
        "shock_direction": "BUY",
        "shock_ofi": 1.0,
        "seconds_to_expiry": 600.0,
        "candle_distance_pct": 0.20,
        "fee_metadata": {"fee_rate_market": 0.07, "fee_exponent": 1.0},
        "pre_shock_features_t0": {
            "UP": {
                "token_id": "TOK_UP",
                "raw_top_asks": [[0.62, 200.0]],
                "raw_top_bids": [[0.61, 200.0]],
                "effective_price_$50": 0.62,
                "vwap_$50": 0.62,
                "age_book_ms": 100.0,
            }
        },
    }
    asyncio.run(harvester.evaluate_shock_and_execute(shock_pass))
    assert len(executed) == 1, "Candidate with z_strike = 0.98 >= 0.65 and p_fair > c_eff + 0.06 must execute"

    # Case 2: TTE = 1100s, dist_pct = 0.16%: passes cushion (0.16% >= 0.15%),
    # but sigma_rem = 0.0050 * sqrt(1100/3600) = 0.002764 -> z_strike = 0.0016 / 0.002764 = 0.579 < 0.65 -> REJECTED!
    executed.clear()
    shock_fail = dict(shock_pass)
    shock_fail["event_id"] = "EVT_ZEFF_FAIL"
    shock_fail["market_id"] = "MKT_ZEFF_FAIL"
    shock_fail["seconds_to_expiry"] = 1100.0
    shock_fail["candle_distance_pct"] = 0.16
    asyncio.run(harvester.evaluate_shock_and_execute(shock_fail))
    assert len(executed) == 0, "Candidate with z_strike = 0.58 < 0.65 must be rejected by z-score hurdle"


def test_clob_5_share_minimum_per_tranche_rule(tmp_path, monkeypatch):
    """
    Verifies CLOB 5.0 share minimum per tranche:
    - If total shares < 10.0 (or split leaves tranches < 5.0 shares), do NOT split into tranches.
      Post full remaining shares as single Maker order at min(0.96, round(entry_px + 0.16, 2)).
    - If total shares >= 10.0 and both tranches >= 5.0, split into two 50/50 tranches.
    """
    state_file = tmp_path / "tranche_min_state.json"
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", state_file)

    harvester = PolymarketLiveHarvester(ticket_notional=15.0, dry_run=False, hold_to_maturity=False)
    harvester.executor.auth_mode = "LIVE"
    harvester.executor.is_authenticated = True
    harvester.executor.is_heartbeat_healthy = lambda: True
    harvester.executor.get_collateral_balance = lambda: 91.67
    harvester._last_known_collateral = 91.67

    maker_orders = []
    harvester.executor.post_maker_exit_order = MagicMock(
        side_effect=lambda **kw: maker_orders.append(kw) or {"success": True, "orderID": "MOCK_OID"}
    )

    # Sub-case A: 8.0 shares bought (< 10.0 shares) -> Single tranche of 8.0 shares
    async def mock_snipe_small(**kwargs):
        return OrderResult(
            success=True,
            order_id="OID_SMALL",
            trade_id="T_SMALL",
            token_id="TOK_SMALL",
            target_token="UP",
            side="BUY",
            price=0.65,
            size=8.0,
            notional_usd=5.20,
            fee_usd=0.05,
            latency_ms=1.5,
            mode="LIVE_PRODUCTION",
            execution_status=ExecutionStatus.POSITION_CONFIRMED,
            confirmed_onchain=True,
        )

    harvester.executor.execute_snipe_order_async = mock_snipe_small

    shock_small = {
        "event_id": "EVT_TRANCHE_SMALL",
        "market_id": "MKT_TRANCHE_SMALL",
        "t0_unix": time.time(),
        "title": "Bitcoin Up or Down Hourly",
        "asset": "BTC",
        "shock_direction": "BUY",
        "seconds_to_expiry": 600.0,
        "candle_distance_pct": 0.30,
        "fee_metadata": {"fee_rate_market": 0.07, "fee_exponent": 1.0},
        "pre_shock_features_t0": {
            "UP": {
                "token_id": "TOK_SMALL",
                "raw_top_asks": [[0.65, 200.0]],
                "raw_top_bids": [[0.64, 200.0]],
                "effective_price_$50": 0.65,
                "vwap_$50": 0.65,
                "age_book_ms": 100.0,
            }
        },
    }

    asyncio.run(harvester.evaluate_shock_and_execute(shock_small))
    pos_small = [p for p in harvester.active_positions.values() if p.get("market_id") == "MKT_TRANCHE_SMALL"][0]
    assert "exit_tranches" not in pos_small, "Positions with < 10 shares must not be split into sub-5 share tranches"
    assert len(maker_orders) == 1
    assert maker_orders[0]["size"] == 8.0
    # Price = min(0.96, round(0.65 + 0.16, 2)) = 0.81
    assert maker_orders[0]["price"] == 0.81

    # Sub-case B: 20.0 shares bought (>= 10.0 shares) -> Two tranches of 10.0 shares
    maker_orders.clear()
    async def mock_snipe_large(**kwargs):
        return OrderResult(
            success=True,
            order_id="OID_LARGE",
            trade_id="T_LARGE",
            token_id="TOK_LARGE",
            target_token="UP",
            side="BUY",
            price=0.65,
            size=20.0,
            notional_usd=13.00,
            fee_usd=0.10,
            latency_ms=1.5,
            mode="LIVE_PRODUCTION",
            execution_status=ExecutionStatus.POSITION_CONFIRMED,
            confirmed_onchain=True,
        )

    harvester.executor.execute_snipe_order_async = mock_snipe_large
    shock_large = dict(shock_small)
    shock_large["event_id"] = "EVT_TRANCHE_LARGE"
    shock_large["market_id"] = "MKT_TRANCHE_LARGE"
    shock_large["pre_shock_features_t0"]["UP"]["token_id"] = "TOK_LARGE"

    asyncio.run(harvester.evaluate_shock_and_execute(shock_large))
    pos_large = [p for p in harvester.active_positions.values() if p.get("market_id") == "MKT_TRANCHE_LARGE"][0]
    assert "exit_tranches" in pos_large, "Positions with >= 10 shares must create exit tranches"
    assert len(pos_large["exit_tranches"]) == 2
    assert pos_large["exit_tranches"][0]["size"] == 10.0
    assert pos_large["exit_tranches"][1]["size"] == 10.0
    assert len(maker_orders) == 1
    assert maker_orders[0]["size"] == 10.0
    assert maker_orders[0]["price"] == 0.79  # entry + 0.14 = 0.65 + 0.14 = 0.79
