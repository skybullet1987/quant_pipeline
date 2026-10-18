import asyncio
import json
import math
import time
import pytest
from unittest.mock import MagicMock, AsyncMock

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
    Verifies Table 1 Refinement 1:
    - 1h Sleeve 1 (TTE <= 1350s): strictly [0.84, 0.88].
    - 1h Sleeve 2 (1350s < TTE <= 3300s, ETH): strictly [0.65, 0.85].
    - 15m sub-hourly: strictly [0.65, 0.88].
    """
    state_file = tmp_path / "dual_sleeve_state.json"
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", state_file)

    harvester = PolymarketLiveHarvester(ticket_notional=32.0, dry_run=False)
    harvester.executor.auth_mode = "LIVE"
    harvester.executor.is_authenticated = True
    harvester.executor.is_heartbeat_healthy = lambda: True
    harvester.executor.get_collateral_balance = lambda: 159.69
    harvester._last_known_collateral = 159.69

    current_ask_px = [0.85]

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
            price=kwargs.get("max_price", 0.85),
            size=10.0,
            notional_usd=kwargs.get("notional_usd", 32.0),
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

    # 1. 1h Sleeve 1 Late Hour (TTE = 600s):
    # Ask 0.80 (< 0.82 floor) -> Must REJECT
    asyncio.run(harvester.evaluate_shock_and_execute(make_shock("ETH 1h Up", "ETH", 600.0, 0.20, 0.80)))
    assert len(executed) == 0

    # Ask 0.91 (Crumbs zone > 0.89) -> Must REJECT
    asyncio.run(harvester.evaluate_shock_and_execute(make_shock("ETH 1h Up", "ETH", 600.0, 0.20, 0.91)))
    assert len(executed) == 0

    # Ask 0.86 (Table 1 Sweet spot: 0.82 <= p <= 0.89, 93.4% WR) -> Must EXECUTE
    asyncio.run(harvester.evaluate_shock_and_execute(make_shock("ETH 1h Up", "ETH", 600.0, 0.20, 0.86)))
    assert len(executed) == 1
    harvester.active_positions.clear()

    # 2. 1h Sleeve 2 Early/Mid Hour (TTE = 2400s):
    # Ask 0.68 (< 0.72 floor) -> Must REJECT
    asyncio.run(harvester.evaluate_shock_and_execute(make_shock("ETH 1h Up", "ETH", 2400.0, 0.20, 0.68)))
    assert len(executed) == 1

    # Ask 0.87 (> 0.85 for early window) -> Must REJECT
    asyncio.run(harvester.evaluate_shock_and_execute(make_shock("ETH 1h Up", "ETH", 2400.0, 0.20, 0.87)))
    assert len(executed) == 1

    # Ask 0.75 (Sleeve 2 Sweet spot: 0.72 <= p <= 0.85) -> Must EXECUTE
    asyncio.run(harvester.evaluate_shock_and_execute(make_shock("ETH 1h Up", "ETH", 2400.0, 0.20, 0.75)))
    assert len(executed) == 2
    harvester.active_positions.clear()
    harvester.trades_this_hour = 0

    # 3. 15m Sub-hourly (TTE = 600s):
    # Ask 0.62 (< 0.65) -> Must REJECT
    asyncio.run(harvester.evaluate_shock_and_execute(make_shock("ETH 15m Up", "ETH", 600.0, 0.20, 0.62)))
    assert len(executed) == 2

    # Ask 0.91 (> 0.89) -> Must REJECT
    asyncio.run(harvester.evaluate_shock_and_execute(make_shock("ETH 15m Up", "ETH", 600.0, 0.20, 0.91)))
    assert len(executed) == 2

    # Ask 0.72 ([0.65, 0.89] band) -> Must EXECUTE
    asyncio.run(harvester.evaluate_shock_and_execute(make_shock("ETH 15m Up", "ETH", 600.0, 0.20, 0.72)))
    assert len(executed) == 3


def test_dynamic_sizing_and_circuit_breaker_floor(tmp_path, monkeypatch):
    """
    Verifies 24/7 Dynamic Auto-Compounding Ticket Sizing & Circuit Breaker:
    - Dynamic sizing: 25% of live equity ($39.92 on $159.69, clamped between $25.00 and $250.00).
    - Drawdown halt: Trips strictly when equity drops below $95.00 floor.
    - 1-loss buffer: $119.77 after 1 loss does NOT trip circuit breaker.
    """
    state_file = tmp_path / "risk_test_state.json"
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", state_file)

    harvester = PolymarketLiveHarvester(ticket_notional=39.92, dry_run=False)
    harvester.executor.auth_mode = "LIVE"
    harvester.executor.is_authenticated = True

    # Check 1: Circuit breaker floor is $95.00
    assert harvester.risk_controller.min_equity_floor_usd == 95.00
    assert CIRCUIT_BREAKER_EQUITY_FLOOR == 95.00
    assert DYNAMIC_BANKROLL_PCT == 0.25

    # Check 2: Starting equity $159.69 yields $39.92 dynamic ticket (25%)
    expected_ticket = round(min(250.0, max(25.0, 159.69 * DYNAMIC_BANKROLL_PCT)), 2)
    assert expected_ticket == 39.92

    # Check 3: Starting equity $159.69 is healthy
    harvester.risk_controller.check_equity_drawdown(159.69)
    assert not harvester.risk_controller.is_halted()

    # Check 4: After 1 full loss (-$39.92), equity is $119.77 -> must NOT halt (survives 1 loss!)
    harvester.risk_controller.check_equity_drawdown(119.77)
    assert not harvester.risk_controller.is_halted(), "1-loss buffer must prevent halt at $119.77!"

    # Check 5: Equity at $94.50 (after 2 consecutive losses) -> Must immediately halt!
    harvester.risk_controller.check_equity_drawdown(94.50)
    assert harvester.risk_controller.is_halted()
    assert "95.00" in harvester.risk_controller.halt_reason


def test_maker_tp_099_placement_on_fill(tmp_path, monkeypatch):
    """
    Verifies that on fill, resting Maker TP is posted at strictly $0.99 for full shares.
    """
    state_file = tmp_path / "tp_test_state.json"
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", state_file)

    harvester = PolymarketLiveHarvester(ticket_notional=32.0, dry_run=False, hold_to_maturity=True)
    harvester.executor.auth_mode = "LIVE"
    harvester.executor.is_authenticated = True
    harvester.executor.is_heartbeat_healthy = lambda: True
    harvester.executor.get_collateral_balance = lambda: 159.69
    harvester._last_known_collateral = 159.69

    async def mock_get_book(token_id):
        return {
            "asks": [{"price": "0.7800", "size": "200.0"}],
            "bids": [{"price": "0.7700", "size": "200.0"}],
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
            price=0.7800,
            size=41.0,
            notional_usd=32.00,
            fee_usd=0.10,
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
        "seconds_to_expiry": 2400.0,
        "candle_distance_pct": 0.20,
        "fee_metadata": {"fee_rate_market": 0.07, "fee_exponent": 1.0},
        "pre_shock_features_t0": {
            "UP": {
                "token_id": "0xETH_TOKEN",
                "raw_top_asks": [[0.7800, 200.0]],
                "effective_price_$50": 0.7800,
                "vwap_$50": 0.7800,
            }
        },
    }

    asyncio.run(harvester.evaluate_shock_and_execute(shock))

    # Assert Maker TP posted at 0.99 for all 41.0 shares
    assert len(maker_exits_posted) == 1
    assert maker_exits_posted[0]["price"] == 0.99
    assert maker_exits_posted[0]["size"] == 41.0
    assert maker_exits_posted[0]["side"] == "SELL"


def test_hot_path_latency_benchmark():
    """
    Verifies that hot-path execution pre-flight logic executes in < 370ms.
    """
    executor = PolymarketLiveExecutor(dry_run=True)
    t0 = time.perf_counter()

    # Pre-warm and qualify order parameters
    cond_id = "0xCOND_LATENCY_BENCHMARK"
    token_id = "0xTOKEN_LATENCY_BENCHMARK"
    executor._fee_cache[cond_id] = (0.07, 1.0)
    executor._tick_size_cache[token_id] = 0.01

    quantized_px = executor.quantize_order_price(0.86, token_id)
    fee_rate, fee_exp = executor.get_market_fee_params(cond_id)
    effective_rate, taker_fee = calculate_taker_fee(32.0, quantized_px, fee_rate, fee_exp)

    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert elapsed_ms < 10.0, f"Hot-path compute took {elapsed_ms:.2f}ms (target < 10ms, total budget < 370ms)"


def test_parallel_multi_market_capacity_and_per_market_dedup(tmp_path, monkeypatch):
    """
    Verifies Section 2:
    1. Strict Per-Market Mutual Exclusion (max_positions_per_market_id = 1):
       Never enters the same market_id twice across sleeves.
    2. Parallel Multi-Market Capacity (MAX_CONCURRENT_POSITIONS = 3):
       Allows up to 3 simultaneous positions across DIFFERENT contracts.
       Rejects 4th simultaneous position when concurrency cap of 3 is reached.
    """
    state_file = tmp_path / "multi_pos_test_state.json"
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", state_file)

    harvester = PolymarketLiveHarvester(
        ticket_notional=39.92,
        dry_run=False,
        max_concurrent=3,
        max_exposure=120.0,
        max_trades_per_hour=10,
    )
    harvester.executor.auth_mode = "LIVE"
    harvester.executor.is_authenticated = True
    harvester.executor.is_heartbeat_healthy = lambda: True
    harvester.executor.get_collateral_balance = lambda: 159.69
    harvester._last_known_collateral = 159.69

    async def mock_get_book(token_id):
        return {
            "asks": [{"price": "0.8500", "size": "500.0"}],
            "bids": [{"price": "0.8400", "size": "500.0"}],
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
            price=0.8500,
            size=40.0,
            notional_usd=34.0,
            fee_usd=0.10,
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
            "candle_distance_pct": 0.20,
            "fee_metadata": {"fee_rate_market": 0.07, "fee_exponent": 1.0},
            "pre_shock_features_t0": {
                "UP": {
                    "token_id": f"TOK_{market_id}",
                    "raw_top_asks": [[0.8500, 500.0]],
                    "effective_price_$50": 0.8500,
                    "vwap_$50": 0.8500,
                }
            },
        }

    # Contract 1: ETH 1h -> Must execute (Position 1 of 3)
    asyncio.run(harvester.evaluate_shock_and_execute(make_contract_shock("MKT_ETH_1H", "ETH 1h Up", "ETH")))
    assert len(executed) == 1
    assert len(harvester.active_positions) == 1

    # Attempt Duplicate Entry on Contract 1: MKT_ETH_1H -> Must REJECT via per-market mutual exclusion
    asyncio.run(harvester.evaluate_shock_and_execute(make_contract_shock("MKT_ETH_1H", "ETH 1h Up", "ETH")))
    assert len(executed) == 1  # Blocked! Single-order-per-market enforced
    assert len(harvester.active_positions) == 1

    # Contract 2: BTC 1h -> Must execute (Position 2 of 3)
    asyncio.run(harvester.evaluate_shock_and_execute(make_contract_shock("MKT_BTC_1H", "BTC 1h Up", "BTC")))
    assert len(executed) == 2
    assert len(harvester.active_positions) == 2

    # Contract 3: ETH 15m -> Must execute (Position 3 of 3)
    asyncio.run(harvester.evaluate_shock_and_execute(make_contract_shock("MKT_ETH_15M", "ETH 15m Up", "ETH")))
    assert len(executed) == 3
    assert len(harvester.active_positions) == 3

    # Contract 4: BTC 15m -> Must REJECT because max_concurrent_positions == 3
    asyncio.run(harvester.evaluate_shock_and_execute(make_contract_shock("MKT_BTC_15M", "BTC 15m Up", "BTC")))
    assert len(executed) == 3  # Blocked by concurrency limit (3 active positions)
    assert len(harvester.active_positions) == 3
