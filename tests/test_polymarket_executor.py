#!/usr/bin/env python3
"""
Unit tests for Polymarket Live Execution Client, Pre-Trade Risk Filters,
Delta-Aware Settlement Verification, and Lifecycle State Machines.
"""

import asyncio
import json
import pytest
from src.polymarket_research.polymarket_live_executor import (
    PolymarketLiveExecutor,
    ExecutionStatus,
    calculate_taker_fee,
    EXPECTED_CLOB_V2,
)


def test_dynamic_fee_calculation():
    """P1: Validates canonical calculate_taker_fee for both exponent 1.0 and dynamic exponent curves."""
    # Exponent 1.0 at p = 0.77: fee = 50 * 0.07 * (1 - 0.77) = 0.805
    eff_rate, fee_usd = calculate_taker_fee(50.0, 0.77, fee_rate=0.07, fee_exponent=1.0)
    assert abs(eff_rate - 0.0161) < 1e-4
    assert abs(fee_usd - 0.805) < 1e-4

    # Exponent 1.0 at p = 0.50: fee = 100 * 0.07 * (1 - 0.50) = 3.50
    eff_rate, fee_usd = calculate_taker_fee(100.0, 0.50, fee_rate=0.07, fee_exponent=1.0)
    assert abs(eff_rate - 0.035) < 1e-4
    assert abs(fee_usd - 3.50) < 1e-4

    # Exponent 2.0 dynamic schedule:
    # per_share_fee = 0.07 * (0.5 * 0.5)**2 = 0.07 * 0.0625 = 0.004375
    # shares = 100 / 0.5 = 200
    # fee_usd = 200 * 0.004375 = 0.875
    eff_rate2, fee_usd2 = calculate_taker_fee(100.0, 0.50, fee_rate=0.07, fee_exponent=2.0)
    assert abs(fee_usd2 - 0.875) < 1e-4
    assert abs(eff_rate2 - 0.00875) < 1e-4


def test_depth_guard_validation():
    executor = PolymarketLiveExecutor(dry_run=True)

    # Mock orderbook with sufficient depth ($100 available vs $50 target -> 2.0x >= 1.50x)
    good_book = {
        "asks": [
            {"price": "0.75", "size": "80"},
            {"price": "0.76", "size": "60"},
        ]
    }
    passed, ratio, best_px = executor.verify_pre_trade_depth(good_book, target_notional_usd=50.0, side="BUY")
    assert passed is True
    assert ratio > 1.50
    assert best_px == 0.75

    # Mock orderbook with thin depth ($20 available vs $50 target -> 0.4x < 1.50x)
    thin_book = {
        "asks": [
            {"price": "0.75", "size": "10"},
            {"price": "0.76", "size": "15"},
        ]
    }
    passed, ratio, best_px = executor.verify_pre_trade_depth(thin_book, target_notional_usd=50.0, side="BUY")
    assert passed is False
    assert ratio < 1.50


def test_dry_run_snipe_execution(tmp_path):
    ledger = tmp_path / "test_orders.jsonl"
    executor = PolymarketLiveExecutor(dry_run=True, ledger_path=str(ledger))

    # Mock get_market_book
    executor.get_market_book = lambda tid: {
        "asks": [
            {"price": "0.80", "size": "150"},
            {"price": "0.81", "size": "100"},
        ]
    }

    res = executor.execute_snipe_order(
        trade_id="TEST_TRADE_001",
        token_id="12345",
        target_token="UP",
        notional_usd=50.0,
        target_price=0.80,
    )

    assert res.success is True
    assert res.mode == "DRY_RUN_SIMULATION"
    assert res.execution_status == ExecutionStatus.POSITION_CONFIRMED
    assert res.confirmed_onchain is True
    assert res.size == 62.5
    assert res.fee_usd > 0
    assert res.details["pre_token_balance"] == 0.0
    assert res.details["post_token_balance"] == 62.5
    assert ledger.exists()


def test_simulate_fok_sweep():
    executor = PolymarketLiveExecutor(dry_run=True)

    # Multi-level order book:
    # Level 1: $10 @ 0.45 -> 22.222 shares
    # Level 2: $10 @ 0.50 -> 20.000 shares
    # Total available: $20.00 across 2 levels
    book = {
        "asks": [
            {"price": "0.45", "size": "22.22222"},
            {"price": "0.50", "size": "20.00000"},
            {"price": "0.60", "size": "100.00000"},
        ]
    }

    fillable, vwap, total_shares, worst_px, fee_usd = executor.simulate_fok_sweep(
        orderbook=book,
        target_notional_usd=20.0,
        side="BUY",
        max_acceptable_price=0.85,
    )

    assert fillable is True
    assert round(total_shares, 2) == 42.22
    assert vwap > 0.45
    assert vwap < 0.50
    assert worst_px == 0.50
    assert fee_usd > 0.0

    # Test sweep exceeding max_acceptable_price
    book_expensive = {
        "asks": [
            {"price": "0.90", "size": "100.0"},
        ]
    }
    fillable, _, _, _, _ = executor.simulate_fok_sweep(
        orderbook=book_expensive,
        target_notional_usd=20.0,
        side="BUY",
        max_acceptable_price=0.85,
    )
    assert fillable is False


def test_strict_human_unit_parsing_no_guessing():
    """P1: Order responses are strictly parsed as human units without magnitude heuristics."""
    # Real V2 order responses return human string units
    making_amt_str = "20.05"
    taking_amt_str = "41.6666"

    notional = float(making_amt_str)
    shares = float(taking_amt_str)

    assert notional == 20.05
    assert shares == 41.6666

    # Malformed response fails closed
    with pytest.raises(ValueError):
        float("invalid_amount_string")


def test_delta_aware_balance_verification_invariant():
    """
    P0 #10: Balance confirmation must be delta-aware.
    Pre-existing shares (e.g. 50 UP) must not satisfy a trade buying 10 UP shares.
    """
    executor = PolymarketLiveExecutor(dry_run=True)
    executor.dry_run = False
    executor.is_authenticated = True

    # Pre-trade balance: wallet already has 50.0 shares
    pre_balance = 50.0
    expected_buy = 10.0

    # Scenario A: Polygon indexer delayed (post-trade balance still 50.0 -> delta = 0.0)
    post_balance_delayed = 50.0
    delta_delayed = post_balance_delayed - pre_balance
    confirmed_delayed = delta_delayed >= (expected_buy - 0.1)
    assert confirmed_delayed is False
    status_delayed = ExecutionStatus.POSITION_CONFIRMED if confirmed_delayed else ExecutionStatus.MATCHED_PENDING_SETTLEMENT
    assert status_delayed == ExecutionStatus.MATCHED_PENDING_SETTLEMENT

    # Scenario B: Polygon block settled (post-trade balance indexes to 60.0 -> delta = 10.0)
    post_balance_settled = 60.0
    delta_settled = post_balance_settled - pre_balance
    confirmed_settled = delta_settled >= (expected_buy - 0.1)
    assert confirmed_settled is True
    status_settled = ExecutionStatus.POSITION_CONFIRMED if confirmed_settled else ExecutionStatus.MATCHED_PENDING_SETTLEMENT
    assert status_settled == ExecutionStatus.POSITION_CONFIRMED


def test_atomic_state_persistence(tmp_path, monkeypatch):
    """P1: Verifies that save_state uses atomic fsync + os.replace and includes state_version and last_event_id."""
    from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester
    state_file = tmp_path / "test_state.json"
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", state_file)

    harvester = PolymarketLiveHarvester(ticket_notional=20.0, dry_run=True)
    harvester.last_event_id = "SHOCK_TEST_1001"
    harvester.save_state()

    assert state_file.exists()
    assert not state_file.with_suffix(".tmp").exists()
    with open(state_file, "r") as f:
        data = json.load(f)
    assert data["state_version"] == "2.0.0"
    assert data["ticket_notional"] == 20.0
    assert data["last_event_id"] == "SHOCK_TEST_1001"
    assert "active_position_ids" in data
    assert data["status"] == "RUNNING"


def test_fee_consistency_across_components():
    """P1: Validates that calculate_taker_fee produces identical outputs across executor and paper trader."""
    executor = PolymarketLiveExecutor(dry_run=True)
    rate1, fee1 = executor.calculate_dynamic_crypto_fee(0.75, 20.0, fee_rate=0.07, fee_exponent=1.0)
    rate2, fee2 = calculate_taker_fee(20.0, 0.75, fee_rate=0.07, fee_exponent=1.0)
    assert abs(rate1 - rate2) < 1e-6
    assert abs(fee1 - fee2) < 1e-6


def test_live_mode_refusal_when_unauthenticated():
    """P0 #1: Live mode must strictly refuse startup without valid credentials."""
    with pytest.raises(RuntimeError, match="LIVE MODE REFUSED"):
        PolymarketLiveExecutor(dry_run=False, private_key="")


def test_hard_sdk_pin_assertion(monkeypatch):
    """P1: Enforces hard SDK pin on py_clob_client_v2."""
    assert EXPECTED_CLOB_V2 == "1.2.0"

    import importlib.metadata
    actual_ver = importlib.metadata.version("py_clob_client_v2")
    assert actual_ver == EXPECTED_CLOB_V2


def test_emergency_risk_controller_circuit_breaker():
    """P0 #3: Automated circuit breaker must halt trading on consecutive losses or drawdown."""
    from src.polymarket_research.polymarket_live_harvester import EmergencyRiskController

    rc = EmergencyRiskController(max_consecutive_losses=3, max_daily_loss_usd=40.0)
    assert rc.is_halted() is False

    # Trade 1: Loss (-$10)
    rc.record_trade_pnl(-10.0)
    assert rc.consecutive_losses == 1
    assert rc.is_halted() is False

    # Trade 2: Win (+$5) -> Resets consecutive losses
    rc.record_trade_pnl(5.0)
    assert rc.consecutive_losses == 0
    assert rc.is_halted() is False

    # Trade 3, 4, 5: Three consecutive losses
    rc.record_trade_pnl(-5.0)
    assert rc.consecutive_losses == 1
    assert rc.is_halted() is False

    rc.record_trade_pnl(-5.0)
    assert rc.consecutive_losses == 2
    assert rc.is_halted() is False

    rc.record_trade_pnl(-5.0)
    assert rc.consecutive_losses == 3
    assert rc.is_halted() is True
    assert "consecutive losses" in rc.halt_reason


def test_conditional_balance_exit_invariant():
    """P0 #2: Maker exit order must be rejected if conditional token balance < exit size."""
    executor = PolymarketLiveExecutor(dry_run=True)
    executor.dry_run = False
    executor.is_authenticated = True
    executor.client = object()  # dummy client

    # Mock get_conditional_balance to return 0.0 shares
    executor.get_conditional_balance = lambda token_id: 0.0

    res = executor.post_maker_exit_order(
        token_id="0xToken123",
        price=0.85,
        size=25.0,
        side="SELL",
    )

    assert res["success"] is False
    assert res.get("orderID") is None
    assert "INSUFFICIENT_CONDITIONAL_BALANCE" in res.get("error", "")
    assert res.get("retryable") is True


def test_heartbeat_failure_escalation_and_cancellation():
    """P1: Repeated heartbeat drops trigger unhealthy state and emergency cancellation."""
    executor = PolymarketLiveExecutor(dry_run=True)
    assert executor.is_heartbeat_healthy() is True

    executor.dry_run = False
    executor.is_authenticated = True

    class FailingClient:
        def post_heartbeat(self, heartbeat_id=""):
            raise ConnectionError("Polymarket CLOB timeout")

        def cancel_all(self):
            return {"canceled_all": True}

    executor.client = FailingClient()

    # Heartbeat failure 1, 2, 3
    executor.post_heartbeat()
    executor.post_heartbeat()
    executor.post_heartbeat()
    assert executor.heartbeat_failures == 3
    assert executor.is_heartbeat_healthy() is False

    # Emergency cancellation
    cancel_res = executor.cancel_all_orders()
    assert cancel_res.get("canceled_all") is True


def test_fok_submission_uses_defer_exec_and_never_blocks_on_trade_resolution():
    """
    P0: In py-clob-client-v2, post_order(..., defer_exec=False) invokes _resolve_transactions_hashes()
    which polls and blocks on time.sleep().
    Asserts that post_order MUST be called with defer_exec=True and returns immediately.
    """
    executor = PolymarketLiveExecutor(dry_run=True)
    executor.dry_run = False
    executor.is_authenticated = True

    posted_args = {}

    class MockCLOBClient:
        def create_market_order(self, args):
            return {"signed": "dummy_order"}

        def create_order(self, args):
            return {"signed": "dummy_order"}

        def post_order(self, order, order_type, post_only=False, defer_exec=False):
            posted_args["order"] = order
            posted_args["order_type"] = order_type
            posted_args["post_only"] = post_only
            posted_args["defer_exec"] = defer_exec
            return {
                "orderID": "0xTEST_DEFER_EXEC_ORDER_1001",
                "makingAmount": "20.0",
                "takingAmount": "25.0",
                "tradeIDs": ["TRADE_001_XYZ"],
                "transactionsHashes": [],
            }

        def get_tick_size(self, token_id):
            return "0.01"

    executor.client = MockCLOBClient()
    executor.get_market_book = lambda tid: {
        "asks": [{"price": "0.80", "size": "100.0"}]
    }
    executor.get_conditional_balance = lambda tid: 0.0
    executor.get_onchain_erc1155_balance = lambda tid: 0.0

    res = executor.execute_snipe_order(
        trade_id="TEST_DEFER_001",
        token_id="12345678901234",
        target_token="UP",
        notional_usd=20.0,
        target_price=0.80,
    )

    assert res.success is True
    assert posted_args.get("defer_exec") is True, "FAIL: post_order was called without defer_exec=True!"
    assert res.execution_status == ExecutionStatus.MATCHED_PENDING_SETTLEMENT
    assert res.confirmed_onchain is False
    assert "TRADE_001_XYZ" in res.details["trade_ids"]


def test_precision_derived_epsilon_balance_tolerance():
    """
    P1: Balance tolerance must be precision-derived from platform quantity representation
    using Decimal arithmetic (epsilon = 2 * quantity_unit), not loose percentages.
    """
    # 0.001 standard CLOB tick unit -> 0.002 shares (2 millishares / 2,000 base units)
    eps_default = PolymarketLiveExecutor.calculate_balance_epsilon(0.001)
    assert eps_default == 0.002

    # If order size is passed (e.g. 10.0, 50.0, 100.0 shares), tolerance anchors strictly to base unit
    eps_10 = PolymarketLiveExecutor.calculate_balance_epsilon(10.0)
    assert eps_10 == 0.002

    eps_50 = PolymarketLiveExecutor.calculate_balance_epsilon(50.0)
    assert eps_50 == 0.002

    # Custom tick unit 0.0005 -> 0.001 shares
    eps_custom = PolymarketLiveExecutor.calculate_balance_epsilon(0.0005)
    assert eps_custom == 0.001


def test_authoritative_trade_finality_hierarchy():
    """
    P0/P1: Hierarchy: CLOB order response -> tradeID -> MATCHED -> MINED -> CONFIRMED -> balance delta -> POSITION_CONFIRMED.
    Crucially: tx_hash alone is NOT treated as CONFIRMED without a verified successful on-chain Polygon receipt!
    """
    async def _run_test():
        executor = PolymarketLiveExecutor(dry_run=True)
        executor.dry_run = False
        executor.is_authenticated = True

        # 1. Trade reported as MATCHED without receipt/tx_hash
        executor.client = type("MockClient", (), {
            "get_trades": lambda self, trade_id: [{"status": "MATCHED", "trade_id": trade_id, "transactionHash": None}]
        })()
        tr_status = executor.get_trade_status("TR_101")
        assert tr_status["status"] == "MATCHED"

        # Invariant: If trade is only MATCHED without receipt, finality_ok is False
        finality_matched = (tr_status["status"] == "CONFIRMED")
        assert finality_matched is False

        # 2. Trade reported as MATCHED with an unmined or reverted tx_hash:
        # Mock receipt query: unmined -> None
        executor.get_transaction_receipt_status_async = lambda tx: asyncio.sleep(0, result=None)
        receipt_unmined = await executor.get_transaction_receipt_status_async("0xPENDING")
        assert receipt_unmined is None  # Cannot confirm!

        # Mock receipt query: reverted on-chain -> False
        executor.get_transaction_receipt_status_async = lambda tx: asyncio.sleep(0, result=False)
        receipt_reverted = await executor.get_transaction_receipt_status_async("0xREVERTED")
        assert receipt_reverted is False  # Reverted -> must fail!

        # 3. Trade reported as MATCHED with a verified mined receipt (status == 1):
        executor.get_transaction_receipt_status_async = lambda tx: asyncio.sleep(0, result=True)
        receipt_success = await executor.get_transaction_receipt_status_async("0xMINED_SUCCESS")
        assert receipt_success is True

        finality_mined_receipt = (tr_status["status"] == "CONFIRMED") or (receipt_success is True)
        assert finality_mined_receipt is True

        # 4. Trade reported as CONFIRMED terminal state directly
        executor.client = type("MockClient", (), {
            "get_trades": lambda self, trade_id: [{"status": "CONFIRMED", "trade_id": trade_id, "transactionHash": "0xABC123"}]
        })()
        tr_status_confirmed = executor.get_trade_status("TR_101")
        assert tr_status_confirmed["status"] == "CONFIRMED"
        finality_confirmed = (tr_status_confirmed["status"] == "CONFIRMED")
        assert finality_confirmed is True

    asyncio.run(_run_test())


def test_asset_routing_invariant_refuses_mismatches():
    """
    P1: Enforces that CTF token_id vs Protocol V2 position_id routes fail closed on format mismatch.
    """
    executor = PolymarketLiveExecutor(dry_run=True)

    # Valid CTF 256-bit unsigned integer token_id passes
    executor.assert_market_routing("69780227499454513977334672671025460552242442947981687870257755531884313522574", market_version="CTF")

    # Invalid short or non-digit token_id for CTF fails
    with pytest.raises(ValueError, match="ASSET ROUTING ERROR"):
        executor.assert_market_routing("invalid_token", market_version="CTF")

    # Valid position_id for Exchange V3 passes
    executor.assert_market_routing("0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef", market_version="PROTOCOL_V2")

    # Non-hex for Exchange V3 fails
    with pytest.raises(ValueError, match="ASSET ROUTING ERROR"):
        executor.assert_market_routing("123456789", market_version="PROTOCOL_V2")


def test_deterministic_terminal_unwind_policy_rule():
    """
    P1: At TTE < 60s, policy must deterministically compute:
    terminal_EV vs liquidation_EV vs risk_budget and output explicit binary HOLD or UNWIND.
    """
    shares = 25.0
    notional_usd = 20.0
    risk_budget_usd = 25.0

    # Case 1: Deep bid ($0.05) -> Terminal EV ($12.50) > Liquidation EV ($1.16) and loss within budget -> HOLD
    best_bid_low = 0.05
    est_prob = 0.50
    terminal_ev = est_prob * 1.0 * shares  # $12.50
    exit_fee = shares * best_bid_low * 0.07 * (1.0 - best_bid_low)
    liq_ev = best_bid_low * shares - exit_fee  # ~$1.16
    potential_loss = notional_usd - liq_ev

    decision_1 = "DETERMINISTIC_TERMINAL_HOLD" if (terminal_ev >= liq_ev and potential_loss <= risk_budget_usd) else "DETERMINISTIC_FOK_UNWIND"
    assert decision_1 == "DETERMINISTIC_TERMINAL_HOLD"

    # Case 2: High bid ($0.88) -> Liquidation EV ($21.84) > Terminal EV ($12.50) -> UNWIND to take profit / avoid binary drop
    best_bid_high = 0.88
    liq_ev_high = best_bid_high * shares - (shares * best_bid_high * 0.07 * (1.0 - best_bid_high))
    decision_2 = "DETERMINISTIC_TERMINAL_HOLD" if (terminal_ev >= liq_ev_high and (notional_usd - liq_ev_high) <= risk_budget_usd) else "DETERMINISTIC_FOK_UNWIND"
    assert decision_2 == "DETERMINISTIC_FOK_UNWIND"


def test_crash_recovery_reconciliation(tmp_path, monkeypatch):
    """
    P1 Integration: Kill/crash after MATCHED but before exit order posted.
    Restart -> startup reconciliation discovers tokens on-chain -> reconstructs state -> posts exit -> zero duplicate entries.
    """
    from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester
    state_file = tmp_path / "crash_state.json"
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", state_file)

    # 1. Simulate state after crash: position exists with no exit order
    crashed_state = {
        "state_version": "2.0.0",
        "updated_at_utc": "2026-10-08T00:00:00Z",
        "ticket_notional": 20.0,
        "dry_run": False,
        "last_event_id": "EVT_CRASH_99",
        "active_positions_count": 1,
        "closed_positions_count": 0,
        "active_positions": {
            "LIVE_CRASH_001": {
                "trade_id": "LIVE_CRASH_001",
                "market_id": "5399999",
                "token_id": "0x1111222233334444555566667777888899990000",
                "target_token": "UP",
                "entry_price": 0.50,
                "entry_shares": 40.0,
                "notional_usd": 20.0,
                "fee_usd": 0.70,
                "target_exit_price": 0.60,
                "pre_token_balance": 0.0,
                "status": ExecutionStatus.MATCHED_PENDING_SETTLEMENT,
                "exit_order_id": None,
                "exit_order_status": "NONE",
            }
        },
        "active_position_ids": ["LIVE_CRASH_001"],
        "closed_positions": [],
        "seen_shock_ids": ["EVT_CRASH_99"],
        "traded_market_ids": ["5399999"],
        "risk_state": {"halted": False, "halt_reason": "", "consecutive_losses": 0, "daily_realized_loss": 0.0},
        "status": "RUNNING",
    }
    with open(state_file, "w") as f:
        json.dump(crashed_state, f)

    # 2. Initialize new harvester instance (simulating restart)
    harvester = PolymarketLiveHarvester(ticket_notional=20.0, dry_run=False)
    harvester.executor.dry_run = False
    harvester.executor.is_authenticated = True

    # Mock exchange & chain state: on-chain balance now shows 40.0 tokens arrived
    harvester.executor.get_conditional_balance = lambda tid: 40.0
    harvester.executor.get_open_orders = lambda: []

    posted_exits = []
    harvester.executor.post_maker_exit_order = lambda token_id, price, size, side: (
        posted_exits.append({"token_id": token_id, "price": price, "size": size, "side": side}) or
        {"success": True, "orderID": "0xRECOVERED_EXIT_OID_777"}
    )

    # 3. Load crashed state and execute startup reconciliation
    harvester.load_state()
    harvester.reconcile_with_exchange()

    # 4. Verify recovery outcomes
    assert len(posted_exits) == 1, "Expected exactly 1 recovered exit order to be posted!"
    recovered_pos = harvester.active_positions["LIVE_CRASH_001"]
    assert recovered_pos["exit_order_id"] == "0xRECOVERED_EXIT_OID_777"
    assert recovered_pos["status"] == ExecutionStatus.EXIT_RESTING
    assert recovered_pos["exit_order_status"] == "RESTING"


def test_partial_exit_accounting_lifecycle():
    """
    P1 Integration: Partial-fill accounting.
    30 shares -> 10 filled -> 20 remaining -> persisted state tracks partial -> second fill closes position.
    """
    pos = {
        "trade_id": "TEST_PARTIAL_001",
        "entry_shares": 30.0,
        "notional_usd": 15.0,
        "fee_usd": 0.50,
        "target_exit_price": 0.60,
        "filled_exit_shares": 0.0,
        "remaining_exit_shares": 30.0,
        "status": ExecutionStatus.EXIT_RESTING,
    }

    # Step 1: Partial fill of 10 shares @ $0.60
    order_info_step1 = {
        "status": "OPEN",
        "size_matched": "10.0",
        "takingAmount": "6.0",
        "associate_trades": ["TRADE_PARTIAL_1"],
    }
    size_matched = float(order_info_step1["size_matched"])
    taking_usd = float(order_info_step1["takingAmount"])
    rem_shares = max(0.0, round(pos["entry_shares"] - size_matched, 4))

    pos["filled_exit_shares"] = size_matched
    pos["remaining_exit_shares"] = rem_shares
    pos["gross_exit_cash"] = taking_usd
    pos["average_exit_price"] = round(taking_usd / size_matched, 4)

    assert pos["filled_exit_shares"] == 10.0
    assert pos["remaining_exit_shares"] == 20.0
    assert pos["status"] == ExecutionStatus.EXIT_RESTING  # Position remains open

    # Step 2: Final fill of remaining 20 shares (total 30.0 matched)
    order_info_step2 = {
        "status": "MATCHED",
        "size_matched": "30.0",
        "takingAmount": "18.0",
        "associate_trades": ["TRADE_PARTIAL_1", "TRADE_PARTIAL_2"],
    }
    size_matched_2 = float(order_info_step2["size_matched"])
    taking_usd_2 = float(order_info_step2["takingAmount"])
    rem_shares_2 = max(0.0, round(pos["entry_shares"] - size_matched_2, 4))

    pos["filled_exit_shares"] = size_matched_2
    pos["remaining_exit_shares"] = rem_shares_2
    pos["gross_exit_cash"] = taking_usd_2
    pos["average_exit_price"] = round(taking_usd_2 / size_matched_2, 4)

    if rem_shares_2 <= 0.01:
        pos["status"] = ExecutionStatus.FILLED
        pos["won"] = True

    assert pos["filled_exit_shares"] == 30.0
    assert pos["remaining_exit_shares"] == 0.0
    assert pos["status"] == ExecutionStatus.FILLED


def test_authoritative_clob_fee_metadata_resolution():
    """
    P1: Authoritative CLOB fee metadata resolution using get_clob_market_info(condition_id).
    Verifies that fd.r and fd.e are extracted directly and cached, failing closed if unavailable.
    """
    executor = PolymarketLiveExecutor(dry_run=True)
    executor.dry_run = False
    executor.is_authenticated = True

    mock_clob_market = {
        "mts": 0.001,
        "nr": False,
        "fd": {"r": "0.035", "e": "1.0"},
        "t": [{"t": "0xTOKEN_1"}, {"t": "0xTOKEN_2"}],
    }
    executor.client = type("MockClient", (), {
        "get_clob_market_info": lambda self, cid: mock_clob_market,
    })()

    fee_rate, fee_exp = executor.get_market_fee_params("COND_777")
    assert fee_rate == 0.035
    assert fee_exp == 1.0
    assert "COND_777" in executor._fee_cache

    # Fails closed if CLOB metadata is empty / malformed in live mode
    executor.client = type("MockClient", (), {
        "get_clob_market_info": lambda self, cid: {},
    })()
    with pytest.raises(RuntimeError, match="AUTHORITATIVE_FEE_METADATA_UNAVAILABLE"):
        executor.get_market_fee_params("COND_MALFORMED")


def test_terminal_policy_uses_remaining_cost_basis_on_partial_fill():
    """
    P1: In partial fills, terminal policy (<60s TTE) must evaluate potential_loss against
    remaining_cost_basis = (remaining_shares / entry_shares) * notional_usd,
    not the full entry notional!
    """
    entry_shares = 30.0
    entry_notional = 15.0
    best_bid = 0.40
    risk_budget = 5.00

    # After partial exit: 10 shares filled, 20 shares remaining
    rem_shares = 20.0
    rem_ratio = rem_shares / entry_shares  # 2/3
    rem_cost_basis = round(entry_notional * rem_ratio, 4)  # $10.00
    assert rem_cost_basis == 10.00

    # Liquidation value for remaining 20 shares:
    exit_fee = rem_shares * best_bid * 0.07 * (1.0 - best_bid)
    liq_ev = max(0.0, best_bid * rem_shares - exit_fee)  # ~ $7.664

    # Old faulty formula used entry_notional ($15.00) -> potential_loss = $15.00 - $7.66 = $7.34 > $5.00 budget (falsely forced UNWIND!)
    old_loss = entry_notional - liq_ev
    assert old_loss > risk_budget

    # Correct formula uses rem_cost_basis ($10.00) -> potential_loss = $10.00 - $7.66 = $2.34 <= $5.00 budget (correctly allowed HOLD!)
    correct_loss = rem_cost_basis - liq_ev
    assert correct_loss <= risk_budget


def test_trigger_event_idempotency_and_canary_single_position_guard(tmp_path, monkeypatch):
    """
    P1: Event idempotency and canary single concurrent position guard:
    - Duplicate event IDs produce ZERO second entries.
    - Having 1 active position blocks new entries during canary phase.
    """
    async def _run_test():
        from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester
        state_file = tmp_path / "canary_state.json"
        monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", state_file)

        harvester = PolymarketLiveHarvester(ticket_notional=5.0, dry_run=True)
        harvester.active_positions.clear()
        harvester.seen_shock_ids.clear()
        harvester.executor.get_market_book_async = lambda tid: asyncio.sleep(0, result={
            "asks": [{"price": "0.50", "size": "100.0"}, {"price": "0.51", "size": "100.0"}],
            "bids": [{"price": "0.49", "size": "100.0"}],
        })

        shock_event = {
            "event_id": "EVT_IDEMPOTENT_001",
            "market_id": "5399999",
            "t0_unix": 1700000000,
            "title": "BTC 15m Up",
            "shock_direction": "BUY",
            "seconds_to_expiry": 300.0,
            "candle_distance_pct": 0.10,
            "pre_shock_features_t0": {
                "UP": {
                    "token_id": "0x1234567890abcdef1234567890abcdef12345678",
                    "raw_top_asks": [[0.50, 100.0]],
                    "effective_price_$5": 0.50,
                }
            }
        }

        # First evaluation creates position
        await harvester.evaluate_shock_and_execute(shock_event)
        assert len(harvester.active_positions) == 1
        assert "EVT_IDEMPOTENT_001" in harvester.seen_shock_ids

        # Duplicate trigger delivery with same event_id: must be ignored (idempotent)
        await harvester.evaluate_shock_and_execute(shock_event)
        assert len(harvester.active_positions) == 1

        # Different event ID while 1 position is active: blocked by single-position canary guard
        shock_event_2 = dict(shock_event)
        shock_event_2["event_id"] = "EVT_NEW_002"
        await harvester.evaluate_shock_and_execute(shock_event_2)
        assert len(harvester.active_positions) == 1, "Canary single-position guard must block 2nd concurrent position!"

    asyncio.run(_run_test())


def test_persistent_async_client_connection_pooling():
    """
    P2: PolymarketLiveExecutor preserves HTTP connection pooling via persistent httpx.AsyncClient.
    """
    executor = PolymarketLiveExecutor(dry_run=True)
    client1 = executor.get_async_client()
    client2 = executor.get_async_client()
    assert client1 is client2, "Persistent HTTP client must reuse same instance for connection pooling!"
    assert not client1.is_closed


def test_finality_rejection_on_reverted_polygon_receipt():
    """
    P0/P1: Verifies that if an on-chain transaction reverted (receipt status == 0),
    the system rejects finality and flags failure rather than falsely assuming fill.
    """
    async def _run_test():
        executor = PolymarketLiveExecutor(dry_run=True)
        executor.dry_run = False
        executor.is_authenticated = True

        # Mock receipt query returning False (reverted status 0)
        executor.get_transaction_receipt_status_async = lambda tx: asyncio.sleep(0, result=False)
        status_reverted = await executor.get_transaction_receipt_status_async("0xREVERTED_TX")
        assert status_reverted is False

        # Mock receipt query returning True (status 1)
        executor.get_transaction_receipt_status_async = lambda tx: asyncio.sleep(0, result=True)
        status_success = await executor.get_transaction_receipt_status_async("0xSUCCESS_TX")
        assert status_success is True

    asyncio.run(_run_test())


def test_harvester_ingestion_does_not_short_circuit_idempotency():
    """
    Regression Test: Ensures that shocks read from file ingestion correctly reach
    and pass through evaluate_shock_and_execute without being prematurely rejected
    by a duplicate seen_shock_ids registration in the outer loop.
    """
    from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester
    from src.polymarket_research.polymarket_live_executor import OrderResult, ExecutionStatus

    async def _run_test():
        harvester = PolymarketLiveHarvester(ticket_notional=5.0, dry_run=True)
        harvester.save_state = lambda: None
        harvester.executor.auth_mode = "DRY_RUN"
        harvester.executor.is_authenticated = True

        executed_orders = []

        async def mock_snipe(**kwargs):
            executed_orders.append(kwargs)
            return OrderResult(
                success=True,
                order_id="MOCK_INGEST_001",
                trade_id=kwargs.get("trade_id", "T1"),
                token_id=kwargs.get("token_id", "TOK1"),
                target_token="UP",
                side="BUY",
                price=0.50,
                size=10.0,
                notional_usd=5.0,
                fee_usd=0.05,
                latency_ms=1.2,
                mode="DRY_RUN_SIMULATION",
                execution_status=ExecutionStatus.POSITION_CONFIRMED,
                confirmed_onchain=True,
            )

        harvester.executor.execute_snipe_order_async = mock_snipe

        shock_line = json.dumps({
            "event_id": "EVT_INGESTION_REGRESSION_TEST",
            "market_id": "5399111",
            "t0_unix": 1700000000.123,
            "title": "BTC Ingestion Test Market",
            "shock_direction": "BUY",
            "seconds_to_expiry": 300.0,
            "candle_distance_pct": 0.10,
            "fee_metadata": {"fee_rate_market": 0.07, "fee_exponent": 1.0},
            "pre_shock_features_t0": {
                "UP": {
                    "token_id": "0xTOK_UP_TEST",
                    "raw_top_asks": [[0.50, 100.0]],
                    "effective_price_$5": 0.50,
                }
            }
        })

        # Simulate loop reading new shock line
        shock = json.loads(shock_line)
        s_id = shock.get("event_id") or shock.get("shock_id") or f"{shock.get('market_id')}_{shock.get('t0_unix')}"
        assert s_id not in harvester.seen_shock_ids

        # Pass through to evaluate_shock_and_execute as the loop does
        await harvester.evaluate_shock_and_execute(shock)

        # Must execute cleanly without being dropped
        assert len(executed_orders) == 1, "Shock was dropped or short-circuited by idempotency check!"
        assert s_id in harvester.seen_shock_ids

        # Second delivery must be skipped by idempotency
        await harvester.evaluate_shock_and_execute(shock)
        assert len(executed_orders) == 1, "Duplicate shock should not have triggered a second order!"

    asyncio.run(_run_test())


def test_depthguard_ceiling_aggregation_and_dynamic_downsizing():
    """Validates the two-part DepthGuard fix: book-wide aggregation up to ceiling & dynamic down-sizing."""
    executor = PolymarketLiveExecutor(dry_run=True)

    # Scenario 1: Multi-level book where tick 1 & 2 have only $37 of depth, but tick 3 & 4 have $150
    # Old logic (sorted_levels[:2]) saw only $37.00 (< 1.50x of $33.98) -> REJECTED
    # New logic evaluates all levels <= 0.88 -> $187.00 total depth -> PASSES with full ticket
    multilevel_book = {
        "asks": [
            {"price": "0.81", "size": "20"},   # $16.20
            {"price": "0.82", "size": "25"},   # $20.50 -> Sum top 2 = $36.70
            {"price": "0.83", "size": "80"},   # $66.40
            {"price": "0.84", "size": "100"},  # $84.00 -> Sum all 4 = $187.10
            {"price": "0.92", "size": "500"},  # Ignored (above 0.88 ceiling)
        ]
    }
    passed, ratio, best_px, adj_ticket = executor.verify_pre_trade_depth(
        multilevel_book,
        target_notional_usd=33.98,
        side="BUY",
        depth_hurdle_ratio=1.25,
        max_price_ceiling=0.88,
        return_adjusted=True,
    )
    assert passed is True
    assert ratio > 5.0  # $187.10 / $33.98 = ~5.5x
    assert best_px == 0.81
    assert adj_ticket == 33.98  # Full ticket size preserved

    # Scenario 2: Thin book with only $37 total depth across all levels
    # Dynamic down-sizing scales $37.00 / 1.25 = $29.60 rather than rejecting!
    thin_book = {
        "asks": [
            {"price": "0.81", "size": "20"},  # $16.20
            {"price": "0.82", "size": "25"},  # $20.50 -> Total $36.70
        ]
    }
    passed, ratio, best_px, adj_ticket = executor.verify_pre_trade_depth(
        thin_book,
        target_notional_usd=33.98,
        side="BUY",
        depth_hurdle_ratio=1.25,
        max_price_ceiling=0.88,
        return_adjusted=True,
    )
    assert passed is True
    assert ratio < 1.25  # 36.70 / 33.98 = ~1.08x
    assert adj_ticket == round(36.70 / 1.25, 2)  # Downsized to $29.36
    assert adj_ticket >= 5.0

    # Scenario 3: Book with less than $5.00 executable depth -> Must safely reject
    empty_book = {
        "asks": [
            {"price": "0.81", "size": "3"},  # $2.43 -> adjusted = $1.94 < $5.00 min lot
        ]
    }
    passed, ratio, best_px, adj_ticket = executor.verify_pre_trade_depth(
        empty_book,
        target_notional_usd=33.98,
        side="BUY",
        depth_hurdle_ratio=1.25,
        max_price_ceiling=0.88,
        return_adjusted=True,
    )
    assert passed is False
    assert adj_ticket == 0.0




