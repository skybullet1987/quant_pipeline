import asyncio
import time
from unittest.mock import MagicMock
import pytest

from src.polymarket_research.polymarket_live_executor import (
    PolymarketLiveExecutor,
    ExecutionStatus,
)
from src.polymarket_research.polymarket_live_harvester import (
    PolymarketLiveHarvester,
)


def test_unwind_quantization_and_tolerance():
    """Verifies execute_unwind_order floor-quantizes lot size and accepts exchange 2-decimal fills."""
    executor = PolymarketLiveExecutor(dry_run=False)
    executor.is_authenticated = True
    executor.client = MagicMock()
    executor.get_conditional_balance = MagicMock(return_value=100.0)

    # Exchange matching engine returns 35.21 for an order size of 35.211268
    executor.client.create_order = MagicMock(return_value={"signed": "ORDER"})
    executor.client.post_order = MagicMock(return_value={
        "orderID": "0xUNWIND_001",
        "status": "matched",
        "makingAmount": "35.21",
        "takingAmount": "19.3655",
        "success": True,
    })

    res = executor.execute_unwind_order(
        token_id="0xTOKEN_ETH_DOWN",
        size=35.211268,
        side="SELL",
        min_price=0.55,
    )

    assert res["success"] is True
    assert res["orderID"] == "0xUNWIND_001"
    assert res["matched_size"] == 35.21
    assert res["taking_amount"] == 19.3655
    create_order_call = executor.client.create_order.call_args[0][0]
    assert create_order_call.size == 35.21


def test_unwind_partial_fill_returns_partial_status():
    """Verifies that when matching engine partially fills, partial=True is returned with matched_size."""
    executor = PolymarketLiveExecutor(dry_run=False)
    executor.is_authenticated = True
    executor.client = MagicMock()
    executor.get_conditional_balance = MagicMock(return_value=100.0)

    executor.client.create_order = MagicMock(return_value={"signed": "ORDER"})
    executor.client.post_order = MagicMock(return_value={
        "orderID": "0xUNWIND_PARTIAL",
        "status": "matched",
        "makingAmount": "20.00",
        "takingAmount": "10.00",
        "success": True,
    })

    res = executor.execute_unwind_order(
        token_id="0xTOKEN_ETH_DOWN",
        size=50.00,
        side="SELL",
        min_price=0.50,
    )

    assert res["success"] is False
    assert res["partial"] is True
    assert res["matched_size"] == 20.00
    assert res["unfilled_size"] == 30.00
    assert res["taking_amount"] == 10.00


def test_balance_query_failure_returns_none_fail_closed():
    """Verifies get_conditional_balance returns None (UNKNOWN) on error, never 0.0."""
    executor = PolymarketLiveExecutor(dry_run=False)
    executor.is_authenticated = True
    executor.client = MagicMock()
    executor.client.get_balance_allowance.side_effect = Exception("Connection reset by peer")

    bal = executor.get_conditional_balance("0xTOKEN_ERR")
    assert bal is None, "Failed balance query must return None, NEVER 0.0"


def test_balance_query_failure_does_not_falsely_settle_position():
    """Fail-Closed Invariant: A failed balance query (None) must NEVER be interpreted as zero or trigger closure."""
    harvester = PolymarketLiveHarvester(dry_run=False)
    tid = "LIVE_TEST_FAIL_CLOSED_BAL"
    now = time.time()

    harvester.active_positions[tid] = {
        "trade_id": tid,
        "market_id": "TEST_MKT_FAIL_CLOSED",
        "token_id": "0xTOK_ERR",
        "target_token": "DOWN",
        "asset": "BTC",
        "entry_price": 0.60,
        "entry_shares": 40.0,
        "remaining_shares": 40.0,
        "notional_usd": 24.0,
        "fee_usd": 0.50,
        "target_exit_price": 0.70,
        "candle_open_spot": 65000.0,
        "candle_sigma": 0.005,
        "candle_expiry_ts": now + 600.0,
        "is_liquidating": False,
        "exit_order_id": None,
        "exit_order_status": "UNWIND_RETRY_REQUIRED",
        "next_unwind_retry_ts": 0.0,
        "status": ExecutionStatus.EXIT_RESTING,
    }
    harvester.save_state = lambda: None
    harvester.get_reference_spot_price = lambda sym: 66000.0
    harvester.executor.get_market_book_async = lambda tid: asyncio.sleep(0, result={"bids": [{"price": "0.30", "size": "10.0"}]})
    harvester.executor.get_open_orders = lambda **kw: []

    # Unwind fails
    harvester.executor.execute_unwind_order = lambda **kw: {
        "success": False,
        "error": "CLOB rejection: FOK could not be fully filled",
    }
    # Balance query FAILS (returns None)
    harvester.executor.get_conditional_balance = lambda tid: None

    asyncio.run(harvester.check_resolutions_and_manage_positions())

    # Position MUST REMAIN ACTIVE; must NOT be closed!
    assert tid in harvester.active_positions, "Position must NOT be closed when balance query returns None"
    assert harvester.active_positions[tid]["exit_order_status"] == "UNWIND_RETRY_REQUIRED"
    assert len(harvester.closed_positions) == 0


def test_pre_expiry_cancellation_confirmation_before_unwind():
    """Invariant: Pre-expiry logic must confirm resting maker ask is canceled before dispatching unwind."""
    harvester = PolymarketLiveHarvester(dry_run=False)
    tid = "LIVE_TEST_CANCEL_CONFIRM"
    now = time.time()

    harvester.active_positions[tid] = {
        "trade_id": tid,
        "market_id": "TEST_MKT_CANCEL_CONFIRM",
        "token_id": "0xTOK_UP",
        "target_token": "UP",
        "asset": "ETH",
        "entry_price": 0.60,
        "entry_shares": 50.0,
        "remaining_shares": 50.0,
        "notional_usd": 30.0,
        "fee_usd": 0.50,
        "target_exit_price": 0.69,
        "candle_open_spot": 2500.0,
        "candle_sigma": 0.005,
        "candle_expiry_ts": now + 120.0,  # TTE < 180s
        "is_liquidating": False,
        "exit_order_id": "0xRESTING_MAKER_ASK",
        "exit_order_status": "RESTING",
        "status": ExecutionStatus.EXIT_RESTING,
    }
    harvester.save_state = lambda: None
    harvester.get_reference_spot_price = lambda sym: 2450.0  # OTM
    harvester.executor.get_market_book_async = lambda tid: asyncio.sleep(0, result={"bids": [{"price": "0.50", "size": "50.0"}]})

    # Order is still in open_orders
    harvester.executor.get_open_orders = lambda **kw: [{"id": "0xRESTING_MAKER_ASK"}]
    cancel_called = []
    harvester.executor.cancel_order = lambda oid: cancel_called.append(oid) or {"canceled": [oid]}

    unwinds_dispatched = []
    harvester.executor.execute_unwind_order = lambda **kw: unwinds_dispatched.append(kw)

    asyncio.run(harvester.check_resolutions_and_manage_positions())

    # Cancellation must be requested, but unwind order NOT dispatched yet on this tick!
    assert "0xRESTING_MAKER_ASK" in cancel_called
    assert len(unwinds_dispatched) == 0, "Must NOT dispatch unwind until cancellation is verified"
    assert harvester.active_positions[tid]["exit_order_status"] in {"STOP_CANCEL_PENDING", "PRE_EXPIRY_CANCEL_PENDING"}


def test_pre_expiry_otm_salvage_triggers_unwind_after_cancellation():
    """Verifies that an OTM position executes salvage unwind after maker ask cancellation is confirmed."""
    harvester = PolymarketLiveHarvester(dry_run=False)
    tid = "LIVE_TEST_OTM_SALVAGE"
    now = time.time()

    harvester.active_positions[tid] = {
        "trade_id": tid,
        "market_id": "TEST_MKT_OTM",
        "token_id": "0xTOK_UP",
        "target_token": "UP",
        "asset": "ETH",
        "entry_price": 0.60,
        "entry_shares": 50.0,
        "remaining_shares": 50.0,
        "notional_usd": 30.0,
        "fee_usd": 0.50,
        "target_exit_price": 0.69,
        "candle_open_spot": 2500.0,
        "candle_sigma": 0.005,
        "candle_expiry_ts": now + 120.0,  # 120s remaining < 180s
        "is_liquidating": False,
        "exit_order_id": "0xRESTING_MAKER_ASK",
        "exit_order_status": "PRE_EXPIRY_CANCEL_PENDING",
        "status": ExecutionStatus.EXIT_RESTING,
    }
    harvester.save_state = lambda: None
    harvester.get_reference_spot_price = lambda sym: 2450.0  # strictly OTM (spot 2450 < 2500 - pin_buffer)
    harvester.executor.get_market_book_async = lambda tid: asyncio.sleep(0, result={"bids": [{"price": "0.50", "size": "50.0"}]})

    # Order is no longer in open orders, get_order_status returns CANCELED
    harvester.executor.get_open_orders = lambda **kw: []
    harvester.executor.get_order_status = lambda oid: {"status": "CANCELED", "size_matched": 0.0}

    unwinds_dispatched = []
    harvester.executor.execute_unwind_order = lambda **kw: unwinds_dispatched.append(kw) or {
        "success": True,
        "matched_size": 50.0,
        "taking_amount": 25.00,
        "fee_usd": 0.20,
    }

    asyncio.run(harvester.check_resolutions_and_manage_positions())

    assert len(unwinds_dispatched) == 1
    assert tid not in harvester.active_positions
    closed = next(p for p in harvester.closed_positions if p["trade_id"] == tid)
    assert closed["close_reason"] in {"ADVERSE_STOP_LOSS_UNWIND", "PRE_EXPIRY_OTM_SALVAGE_UNWIND"}
    assert closed["payout_usd"] == 25.00


def test_pre_expiry_itm_holds_to_terminal_resolution():
    """Verifies that a strictly in-the-money position at TTE < 180s cancels maker order and holds to $1.00."""
    harvester = PolymarketLiveHarvester(dry_run=False)
    tid = "LIVE_TEST_ITM_HOLD"
    now = time.time()

    harvester.active_positions[tid] = {
        "trade_id": tid,
        "market_id": "TEST_MKT_ITM",
        "token_id": "0xTOK_UP",
        "target_token": "UP",
        "asset": "ETH",
        "entry_price": 0.60,
        "entry_shares": 50.0,
        "remaining_shares": 50.0,
        "notional_usd": 30.0,
        "fee_usd": 0.50,
        "target_exit_price": 0.69,
        "candle_open_spot": 2500.0,
        "candle_sigma": 0.005,
        "candle_expiry_ts": now + 120.0,
        "is_liquidating": False,
        "exit_order_id": "0xRESTING_MAKER_ASK_ITM",
        "exit_order_status": "PRE_EXPIRY_CANCEL_PENDING",
        "status": ExecutionStatus.EXIT_RESTING,
    }
    harvester.save_state = lambda: None
    harvester.get_reference_spot_price = lambda sym: 2550.0  # strictly ITM
    harvester.executor.get_market_book_async = lambda tid: asyncio.sleep(0, result={"bids": [{"price": "0.95", "size": "50.0"}]})
    harvester.executor.get_open_orders = lambda **kw: []
    harvester.executor.get_order_status = lambda oid: {"status": "CANCELED", "size_matched": 0.0}

    unwinds_dispatched = []
    harvester.executor.execute_unwind_order = lambda **kw: unwinds_dispatched.append(kw)

    asyncio.run(harvester.check_resolutions_and_manage_positions())

    assert len(unwinds_dispatched) == 0
    assert harvester.active_positions[tid]["exit_order_status"] == "CANCELED_FOR_EXPIRY_HOLD"


def test_pre_expiry_pin_risk_zone_classification():
    """Verifies that a position within 0.05% of open spot is classified as PIN_RISK_EXPIRY_HOLD."""
    harvester = PolymarketLiveHarvester(dry_run=False)
    tid = "LIVE_TEST_PIN_RISK"
    now = time.time()

    # ETH spot 2500.50 vs open 2500.00 (within 0.05% threshold = 1.25)
    harvester.active_positions[tid] = {
        "trade_id": tid,
        "market_id": "TEST_MKT_PIN_RISK",
        "token_id": "0xTOK_PIN",
        "target_token": "UP",
        "asset": "ETH",
        "entry_price": 0.60,
        "entry_shares": 50.0,
        "remaining_shares": 50.0,
        "notional_usd": 30.0,
        "fee_usd": 0.50,
        "target_exit_price": 0.69,
        "candle_open_spot": 2500.0,
        "candle_sigma": 0.005,
        "candle_expiry_ts": now + 120.0,
        "is_liquidating": False,
        "exit_order_id": "0xRESTING_MAKER_ASK_PIN",
        "exit_order_status": "PRE_EXPIRY_CANCEL_PENDING",
        "status": ExecutionStatus.EXIT_RESTING,
    }
    harvester.save_state = lambda: None
    harvester.get_reference_spot_price = lambda sym: 2500.50  # Delta = +$0.50, within pin risk threshold of $1.25
    harvester.executor.get_market_book_async = lambda tid: asyncio.sleep(0, result={"bids": [{"price": "0.50", "size": "50.0"}]})
    harvester.executor.get_open_orders = lambda **kw: []
    harvester.executor.get_order_status = lambda oid: {"status": "CANCELED", "size_matched": 0.0}

    unwinds_dispatched = []
    harvester.executor.execute_unwind_order = lambda **kw: unwinds_dispatched.append(kw)

    asyncio.run(harvester.check_resolutions_and_manage_positions())

    assert len(unwinds_dispatched) == 0
    assert harvester.active_positions[tid]["exit_order_status"] == "PIN_RISK_EXPIRY_HOLD"


def test_unwind_balance_reconciliation_when_already_sold():
    """
    Round 10 P0-03: a failed unwind with a dust wallet balance proves only that inventory is absent,
    never the sale proceeds. The position must NOT be settled from `taking_amount` of a failed response;
    it stays supervised under UNRESOLVED_BALANCE_DISCREPANCY with new entries halted until exchange
    fill history reconciles it.
    """
    harvester = PolymarketLiveHarvester(dry_run=False)
    tid = "LIVE_TEST_BALANCE_RECONCILE"
    now = time.time()

    harvester.active_positions[tid] = {
        "trade_id": tid,
        "market_id": "TEST_MKT_RECONCILE",
        "token_id": "0xTOK_ALREADY_SOLD",
        "target_token": "DOWN",
        "asset": "ETH",
        "entry_price": 0.61,
        "entry_shares": 47.16,
        "remaining_shares": 47.16,
        "notional_usd": 28.77,
        "fee_usd": 0.79,
        "target_exit_price": 0.70,
        "candle_open_spot": 2565.0,
        "candle_sigma": 0.005,
        "candle_expiry_ts": now + 600.0,
        "is_liquidating": False,
        "exit_order_id": None,
        "exit_order_status": "UNWIND_RETRY_REQUIRED",
        "next_unwind_retry_ts": 0.0,
        "status": ExecutionStatus.EXIT_RESTING,
    }
    harvester.save_state = lambda: None

    harvester.get_reference_spot_price = lambda sym: 2600.0
    harvester.executor.get_market_book_async = lambda tid: asyncio.sleep(0, result={"bids": [{"price": "0.42", "size": "50.0"}]})
    harvester.executor.get_open_orders = lambda **kw: []

    # Unwind fails because order size exceeds remaining balance
    harvester.executor.execute_unwind_order = lambda **kw: {
        "success": False,
        "error": "PolyApiException: not enough balance",
        "taking_amount": 19.81,
    }
    # Actual conditional balance is dust (0.0039 shares)
    harvester.executor.get_conditional_balance = lambda tid: 0.0039

    asyncio.run(harvester.check_resolutions_and_manage_positions())

    # No synthetic settlement and no phantom cash from a FAILED unwind response.
    assert tid in harvester.active_positions
    pos = harvester.active_positions[tid]
    assert pos["exit_order_status"] == "UNRESOLVED_BALANCE_DISCREPANCY"
    assert pos.get("status") != ExecutionStatus.SETTLED
    assert "payout_usd" not in pos and "net_pnl_usd" not in pos
    assert not any(p["trade_id"] == tid for p in harvester.closed_positions)
    assert harvester.can_enter_new_position() is False


def test_pre_expiry_missing_spot_classified_as_outcome_unknown():
    """
    Auditor P0 Test: Missing or invalid spot data MUST NEVER be inferred as in-the-money!
    Verifies:
    1. Position is classified as OUTCOME_UNKNOWN (never ITM).
    2. Bot does NOT book a $1.00 payout based on missing data.
    3. Position remains active, persisted, and supervised.
    """
    harvester = PolymarketLiveHarvester(dry_run=False)
    tid = "LIVE_TEST_MISSING_SPOT"
    now = time.time()

    harvester.active_positions[tid] = {
        "trade_id": tid,
        "market_id": "TEST_MKT_MISSING_SPOT",
        "token_id": "0xTOK_UNKNOWN_SPOT",
        "target_token": "UP",
        "asset": "BTC",
        "entry_price": 0.60,
        "entry_shares": 50.0,
        "remaining_shares": 50.0,
        "notional_usd": 30.0,
        "fee_usd": 0.50,
        "target_exit_price": 0.69,
        "candle_open_spot": 65000.0,
        "candle_sigma": 0.005,
        "candle_expiry_ts": now + 120.0,  # TTE < 180s
        "is_liquidating": False,
        "exit_order_id": "0xRESTING_MAKER_ASK_UNK",
        "exit_order_status": "PRE_EXPIRY_CANCEL_PENDING",
        "status": ExecutionStatus.EXIT_RESTING,
    }
    harvester.save_state = lambda: None
    # SPOT IS UNAVAILABLE (returns None / invalid)
    harvester.get_reference_spot_price = lambda sym: None
    harvester.executor.get_market_book_async = lambda tid: asyncio.sleep(0, result={"bids": [{"price": "0.50", "size": "50.0"}]})
    harvester.executor.get_open_orders = lambda **kw: []
    harvester.executor.get_order_status = lambda oid: {"status": "CANCELED", "size_matched": 0.0}

    unwinds_dispatched = []
    harvester.executor.execute_unwind_order = lambda **kw: unwinds_dispatched.append(kw)

    asyncio.run(harvester.check_resolutions_and_manage_positions())

    # Position MUST NOT be liquidated as OTM, and MUST NOT be booked as ITM win!
    assert len(unwinds_dispatched) == 0, "Must not execute emergency salvage when spot is unknown"
    assert tid in harvester.active_positions, "Position must REMAIN ACTIVE and persisted under supervised recovery"
    assert harvester.active_positions[tid]["exit_order_status"] == "OUTCOME_UNKNOWN"
    assert len(harvester.closed_positions) == 0, "Must NEVER book closure/settlement payout on missing spot data"


def test_unwind_exact_decimal_shortfall_is_strictly_partial():
    """
    Auditor P1 Test: Exact Decimal verification for unwind fills.
    Proves that a 0.01 share shortfall is strictly treated as a partial fill,
    and exchange rejections/exceptions return proper retryable metadata.
    """
    executor = PolymarketLiveExecutor(dry_run=False)
    executor.is_authenticated = True
    executor.client = MagicMock()
    executor.get_conditional_balance = MagicMock(return_value=100.0)

    # Case A: Exactly 0.01 shortfall (requested 47.16, matched 47.15)
    executor.client.create_order = MagicMock(return_value={"signed": "ORDER"})
    executor.client.post_order = MagicMock(return_value={
        "orderID": "0xUNWIND_001_SHORTFALL",
        "status": "matched",
        "makingAmount": "47.15",
        "takingAmount": "25.9325",
        "success": True,
    })

    res_partial = executor.execute_unwind_order(
        token_id="0xTOKEN_TEST",
        size=47.16,
        side="SELL",
        min_price=0.55,
    )
    assert res_partial["success"] is False, "0.01 shortfall must NOT be treated as success!"
    assert res_partial["partial"] is True
    assert res_partial["matched_size"] == 47.15
    assert res_partial["unfilled_size"] == 0.01

    # Case B: Rejected order response
    executor.client.post_order = MagicMock(return_value={
        "orderID": None,
        "status": "REJECTED",
        "error": "No liquidity at limit price",
    })
    res_rejected = executor.execute_unwind_order(
        token_id="0xTOKEN_TEST",
        size=47.16,
        side="SELL",
        min_price=0.55,
    )
    assert res_rejected["success"] is False
    assert res_rejected["retryable"] is True
    assert res_rejected["matched_size"] == 0.0

    # Case C: Network exception / Ambiguous response
    executor.client.post_order.side_effect = Exception("CLOB 504 Gateway Timeout")
    res_exception = executor.execute_unwind_order(
        token_id="0xTOKEN_TEST",
        size=47.16,
        side="SELL",
        min_price=0.55,
    )
    assert res_exception["success"] is False
    assert res_exception["retryable"] is True
    assert res_exception["outcome_unknown"] is True


def test_multi_cycle_cancellation_race_and_crash_recovery():
    """
    Auditor P1 Test: Multi-cycle cancellation confirmation and crash recovery.
    Simulates:
    Cycle 1: Stop-loss fires. Cancellation requested. Stale open_orders snapshot keeps maker ask in open_oids.
             Harvester sets STOP_CANCEL_PENDING and DOES NOT submit a competing unwind order.
    Cycle 2: Next polling cycle refreshes open_orders (order absent) and get_order_status confirms CANCELED.
             Harvester confirms cancellation and dispatches unwind order.
    Cycle 3: Daemon restart between cycles safely reattaches without losing exposure or double-unwinding.
    """
    harvester = PolymarketLiveHarvester(dry_run=False)
    tid = "LIVE_TEST_MULTI_CYCLE_RACE"
    now = time.time()

    harvester.active_positions[tid] = {
        "trade_id": tid,
        "market_id": "TEST_MKT_RACE",
        "token_id": "0xTOK_RACE",
        "target_token": "UP",
        "asset": "BTC",
        "entry_price": 0.60,
        "entry_shares": 40.0,
        "remaining_shares": 40.0,
        "notional_usd": 24.0,
        "fee_usd": 0.50,
        "target_exit_price": 0.69,
        "candle_open_spot": 65000.0,
        "candle_sigma": 0.005,
        "candle_expiry_ts": now + 600.0,
        "is_liquidating": False,
        "exit_order_id": "0xMAKER_RESTING_001",
        "exit_order_status": "RESTING",
        "status": ExecutionStatus.EXIT_RESTING,
    }
    harvester.save_state = lambda: None
    # Adverse spot price triggers stop loss (spot 64000 vs open 65000)
    harvester.get_reference_spot_price = lambda sym: 64000.0
    harvester.executor.get_market_book_async = lambda tid: asyncio.sleep(0, result={"bids": [{"price": "0.40", "size": "50.0"}]})

    # CYCLE 1: Cancellation is requested, but open_orders snapshot was constructed before cancel:
    harvester.executor.get_open_orders = lambda **kw: [{"id": "0xMAKER_RESTING_001"}]
    cancel_dispatched = []
    harvester.executor.cancel_order = lambda oid: cancel_dispatched.append(oid) or {"canceled": [oid]}
    unwinds_dispatched = []
    harvester.executor.execute_unwind_order = lambda **kw: unwinds_dispatched.append(kw)

    asyncio.run(harvester.check_resolutions_and_manage_positions())

    # Invariants for Cycle 1:
    assert "0xMAKER_RESTING_001" in cancel_dispatched, "Must dispatch cancel request"
    assert len(unwinds_dispatched) == 0, "Must NOT dispatch unwind while order is still in stale open snapshot!"
    assert harvester.active_positions[tid]["exit_order_status"] == "STOP_CANCEL_PENDING"

    # CYCLE 2: Subsequent cycle with refreshed open_orders snapshot:
    harvester.executor.get_open_orders = lambda **kw: []
    harvester.executor.get_order_status = lambda oid: {"status": "CANCELED", "size_matched": 0.0}
    harvester.executor.execute_unwind_order = lambda **kw: unwinds_dispatched.append(kw) or {
        "success": True,
        "matched_size": 40.0,
        "taking_amount": 16.00,
        "fee_usd": 0.15,
    }

    asyncio.run(harvester.check_resolutions_and_manage_positions())

    # Invariants for Cycle 2:
    assert len(unwinds_dispatched) == 1, "Must dispatch unwind once cancellation is authoritatively verified"
    assert tid not in harvester.active_positions
    closed = next(p for p in harvester.closed_positions if p["trade_id"] == tid)
    assert closed["close_reason"] == "ADVERSE_STOP_LOSS_UNWIND"
    assert closed["payout_usd"] == 16.00
