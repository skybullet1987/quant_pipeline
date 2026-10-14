import asyncio
import json
import os
import time
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.polymarket_research.polymarket_live_executor import (
    PolymarketLiveExecutor,
    ExecutionStatus,
)
from src.polymarket_research.polymarket_live_harvester import (
    PolymarketLiveHarvester,
    position_may_post_new_maker_exit,
    position_requires_global_halt,
)


def test_round9_p0_01_unresolved_unwind_maintains_monotonic_global_halt_across_restart(tmp_path, monkeypatch):
    """
    Finding P0-01: Global reconciliation halt must persist monotonically across restarts
    as long as an unknown/unresolved unwind outcome remains in active positions.
    """
    state_file = tmp_path / "p0_01_state.json"
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", state_file)

    now = time.time()
    initial_state = {
        "state_version": "2.3.8",
        "updated_at_utc": "2026-10-13T00:00:00Z",
        "ticket_notional": 25.0,
        "dry_run": False,
        "active_positions_count": 1,
        "closed_positions_count": 0,
        "active_positions": {
            "UNRESOLVED_UNWIND_001": {
                "trade_id": "UNRESOLVED_UNWIND_001",
                "market_id": "MKT_P0_01",
                "token_id": "0xTOK_UNWIND_UNKNOWN",
                "target_token": "UP",
                "entry_price": 0.55,
                "entry_shares": 50.0,
                "remaining_shares": 50.0,
                "notional_usd": 27.50,
                "fee_usd": 0.60,
                "target_exit_price": 0.65,
                "status": ExecutionStatus.POSITION_CONFIRMED,
                "is_liquidating": True,
                "unwind_order_id": "0xUNWIND_INFLIGHT_001",
                "exit_order_status": "UNWIND_EXECUTION_OUTCOME_UNKNOWN",
            }
        },
        "active_position_ids": ["UNRESOLVED_UNWIND_001"],
        "closed_positions": [],
        "risk_state": {
            "halted": True,
            "halt_reason": "UNWIND_EXECUTION_OUTCOME_UNKNOWN: exchange reconciliation required",
            "consecutive_losses": 0,
            "daily_realized_loss": 0.0,
        },
        "risk_halt": True,
        "reconciliation_required": True,
        "global_halt_reasons": ["UNRESOLVED_UNWIND_001:UNWIND_EXECUTION_OUTCOME_UNKNOWN"],
        "status": "RUNNING",
    }
    with open(state_file, "w") as f:
        json.dump(initial_state, f)

    # Initialize harvester simulating restart
    harvester = PolymarketLiveHarvester(ticket_notional=25.0, dry_run=False)
    harvester.executor.dry_run = False
    harvester.executor.is_authenticated = True

    # Exchange reports empty open orders and status for in-flight order is unavailable
    harvester.executor.get_open_orders = lambda **kw: []
    harvester.executor.get_order_status = lambda oid: None
    harvester.executor.get_account_fills = lambda *args, **kw: []

    harvester.load_state()
    assert harvester.risk_halt is True
    assert harvester.reconciliation_required is True

    # Run startup reconciliation
    harvester.reconcile_with_exchange()

    # Invariant: Global halt MUST NOT clear because the unwind outcome is still unresolved!
    assert harvester.risk_halt is True, "P0-01: Risk halt must stay active when unwind outcome is unresolved"
    assert harvester.reconciliation_required is True
    assert "UNRESOLVED_UNWIND_001:UNWIND_EXECUTION_OUTCOME_UNKNOWN" in harvester.global_halt_reasons

    # Invariant: New entries are strictly blocked while halted
    can_enter = harvester.can_enter_new_position()
    assert can_enter is False, "New entries must be rejected while global halt is active"


def test_round9_p0_02_reconstructed_entry_finality_immediately_posts_maker_exit(tmp_path, monkeypatch):
    """
    Finding P0-02: Reconstructed BUY entry from exchange trade history extracts authoritative
    trade_ids and transaction hashes, and immediately posts maker exit upon wallet verification.
    """
    state_file = tmp_path / "p0_02_state.json"
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", state_file)

    crashed_state = {
        "state_version": "2.3.8",
        "updated_at_utc": "2026-10-13T00:00:00Z",
        "ticket_notional": 20.0,
        "dry_run": False,
        "active_positions_count": 0,
        "closed_positions_count": 0,
        "active_positions": {},
        "active_position_ids": [],
        "closed_positions": [],
        "pending_entry_intents": {
            "INTENT_CRASH_002": {
                "trade_id": "INTENT_CRASH_002",
                "market_id": "MKT_CRASH_002",
                "token_id": "0xTOK_CRASH_RECOVER",
                "target_token": "UP",
                "asset": "BTC",
                "target_price": 0.50,
                "intended_notional_usd": 20.0,
                "submitted_ts": time.time() - 30.0,
                "candle_open_spot": 60000.0,
                "candle_sigma": 0.005,
                "candle_expiry_ts": time.time() + 600.0,
                "pre_token_balance": 0.0,
                "entry_order_id": "0xENTRY_OID_RECOVER",
            }
        },
        "risk_state": {"halted": False, "halt_reason": "", "consecutive_losses": 0, "daily_realized_loss": 0.0},
        "status": "RUNNING",
    }
    with open(state_file, "w") as f:
        json.dump(crashed_state, f)

    harvester = PolymarketLiveHarvester(ticket_notional=20.0, dry_run=False)
    harvester.executor.dry_run = False
    harvester.executor.is_authenticated = True

    # Exchange trade history returns fill with finality identifiers
    harvester.executor.get_account_fills = lambda *args, **kw: [{
        "fill_id": "FILL_001",
        "order_id": "0xENTRY_OID_RECOVER",
        "trade_id": "TR_FINALITY_999",
        "transaction_hash": "0xTX_HASH_FINAL_888",
        "size": 40.0,
        "price": 0.50,
        "cash": 20.0,
        "fee": 0.20,
        "side": "BUY",
        "timestamp": time.time() - 25.0,
    }]
    harvester.executor.get_open_orders = lambda **kw: []
    harvester.executor.get_conditional_balance = lambda tid: 40.0

    posted_exits = []
    harvester.executor.post_maker_exit_order = lambda token_id, price, size, side: (
        posted_exits.append({"token_id": token_id, "price": price, "size": size, "side": side}) or
        {"success": True, "orderID": "0xRECOVERED_MAKER_EXIT_002"}
    )

    harvester.load_state()
    harvester.reconcile_with_exchange()

    # Invariant: Intent recovered into active position with authoritative finality identifiers
    assert "INTENT_CRASH_002" in harvester.active_positions
    pos = harvester.active_positions["INTENT_CRASH_002"]
    assert "TR_FINALITY_999" in pos.get("trade_ids", [])
    assert "0xTX_HASH_FINAL_888" in pos.get("transactions_hashes", [])
    assert pos.get("inventory_reconciled") is True

    # Invariant: Maker exit order posted immediately upon recovery
    assert len(posted_exits) == 1, "P0-02: Recovered position must immediately post maker exit"
    assert pos["exit_order_id"] == "0xRECOVERED_MAKER_EXIT_002"
    assert pos["exit_order_status"] == "RESTING"


def test_round9_p0_03_corrupt_durable_reservation_file_fails_closed(tmp_path, monkeypatch):
    """
    Finding P0-03: Corrupt durable reservation file is quarantined, marks reservations
    untrusted, blocks sell submissions, and rebuilds cleanly from open orders.
    """
    res_path = tmp_path / "inventory_reservations.json"
    monkeypatch.setattr(PolymarketLiveExecutor, "RESERVATIONS_STATE_PATH", res_path)

    # 1. Write corrupted content (invalid checksum envelope)
    corrupted_payload = {
        "schema": "pm-reservations/2.3.8",
        "sha256": "BAD_CHECKSUM_TAMPERED",
        "data": {"records": {"RES_1": {"token_id": "0xTOK", "size": 50.0}}},
    }
    with open(res_path, "w") as f:
        json.dump(corrupted_payload, f)

    # Initialize executor
    executor = PolymarketLiveExecutor(dry_run=False)
    executor.is_authenticated = True
    executor.client = MagicMock()

    # Invariant: Corrupt file was quarantined and reservations are marked untrusted
    assert executor.reservations_trusted is False, "Corrupted reservation file must mark reservations untrusted"
    corrupt_files = list(tmp_path.glob("inventory_reservations.json.corrupt.*"))
    assert len(corrupt_files) == 1, "Corrupted file must be quarantined"

    # Invariant: get_unreserved_conditional_balance fails closed (returns None)
    executor.get_conditional_balance = MagicMock(return_value=100.0)
    unreserved = executor.get_unreserved_conditional_balance("0xTOK")
    assert unreserved is None, "Must return None when reservations are untrusted"

    # Invariant: Rebuilding from open orders restores trust
    open_orders_snapshot = [
        {"id": "0xRESTING_SELL_1", "side": "SELL", "asset_id": "0xTOK", "original_size": "25.0", "size_matched": "0.0"}
    ]
    rebuilt_ok = executor.rebuild_reservations_from_exchange(open_orders_snapshot)
    assert rebuilt_ok is True
    assert executor.reservations_trusted is True
    assert executor.reserved_inventory.get("0xTOK") == 25.0
    assert executor.get_unreserved_conditional_balance("0xTOK") == 75.0


def test_round9_p0_04_uncertain_unwind_blocks_new_maker_sell_on_restart(tmp_path, monkeypatch):
    """
    Finding P0-04: Startup recovery must not post maker sells for positions with unresolved
    exit or unwind states (UNWIND_RECONCILIATION_REQUIRED / EXIT_POST_OUTCOME_UNKNOWN).
    """
    state_file = tmp_path / "p0_04_state.json"
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", state_file)

    now = time.time()
    crashed_state = {
        "state_version": "2.3.8",
        "updated_at_utc": "2026-10-13T00:00:00Z",
        "ticket_notional": 20.0,
        "dry_run": False,
        "active_positions_count": 2,
        "closed_positions_count": 0,
        "active_positions": {
            "POS_UNRESOLVED_UNWIND": {
                "trade_id": "POS_UNRESOLVED_UNWIND",
                "market_id": "MKT_P0_04_A",
                "token_id": "0xTOK_A",
                "target_token": "UP",
                "entry_price": 0.50,
                "entry_shares": 40.0,
                "remaining_shares": 40.0,
                "notional_usd": 20.0,
                "fee_usd": 0.50,
                "target_exit_price": 0.60,
                "candle_expiry_ts": now + 600.0,
                "status": ExecutionStatus.POSITION_CONFIRMED,
                "is_liquidating": True,
                "unwind_order_id": "0xU_UNKNOWN",
                "exit_order_status": "UNWIND_RECONCILIATION_REQUIRED",
            },
            "POS_UNKNOWN_EXIT_POST": {
                "trade_id": "POS_UNKNOWN_EXIT_POST",
                "market_id": "MKT_P0_04_B",
                "token_id": "0xTOK_B",
                "target_token": "DOWN",
                "entry_price": 0.60,
                "entry_shares": 30.0,
                "remaining_shares": 30.0,
                "notional_usd": 18.0,
                "fee_usd": 0.40,
                "target_exit_price": 0.70,
                "candle_expiry_ts": now + 600.0,
                "status": ExecutionStatus.POSITION_CONFIRMED,
                "exit_order_id": None,
                "exit_order_status": "EXIT_POST_OUTCOME_UNKNOWN",
            },
        },
        "active_position_ids": ["POS_UNRESOLVED_UNWIND", "POS_UNKNOWN_EXIT_POST"],
        "closed_positions": [],
        "risk_state": {"halted": True, "halt_reason": "UNRESOLVED_OUTCOMES", "consecutive_losses": 0, "daily_realized_loss": 0.0},
        "risk_halt": True,
        "reconciliation_required": True,
        "status": "RUNNING",
    }
    with open(state_file, "w") as f:
        json.dump(crashed_state, f)

    harvester = PolymarketLiveHarvester(ticket_notional=20.0, dry_run=False)
    harvester.executor.dry_run = False
    harvester.executor.is_authenticated = True

    maker_posts = []
    harvester.executor.post_maker_exit_order = lambda *a, **kw: maker_posts.append(kw)
    harvester.executor.get_open_orders = lambda **kw: []
    harvester.executor.get_order_status = lambda oid: None
    harvester.executor.get_account_fills = lambda *a, **kw: []

    harvester.load_state()
    harvester.reconcile_with_exchange()

    # Invariant: Neither position may post a new maker order while exit/unwind outcome is unresolved
    assert len(maker_posts) == 0, "P0-04: Must NOT post maker sells for positions with unresolved exit/unwind states"
    assert position_may_post_new_maker_exit(harvester.active_positions["POS_UNRESOLVED_UNWIND"]) is False
    assert position_may_post_new_maker_exit(harvester.active_positions["POS_UNKNOWN_EXIT_POST"]) is False


def test_round9_condition_3_cash_conservation_receivable_and_redemption():
    """
    Condition 3 (Cash conservation):
    1. Theoretical winning settlement books $0 realized cash; expected payout is a separate receivable.
    2. Realized cash is credited strictly upon verified on-chain PayoutRedemption receipt.
    3. Duplicate redemption transaction hashes are ignored (idempotent).
    4. Contradictory partial fill quantities (positive taking with zero matched) route to UNKNOWN.
    """
    harvester = PolymarketLiveHarvester(dry_run=False)
    harvester.save_state = lambda: None
    tid = "POS_SETTLE_RECEIVABLE_001"
    now = time.time()

    pos = {
        "trade_id": tid,
        "market_id": "MKT_SETTLE_001",
        "token_id": "0xTOK_WINNER",
        "target_token": "UP",
        "asset": "BTC",
        "entry_price": 0.60,
        "entry_shares": 50.0,
        "remaining_shares": 50.0,
        "notional_usd": 30.0,
        "fee_usd": 0.50,
        "target_exit_price": 0.70,
        "candle_open_spot": 65000.0,
        "candle_sigma": 0.005,
        "candle_expiry_ts": now - 10.0,  # Expired
        "status": ExecutionStatus.POSITION_CONFIRMED,
        "exit_order_id": None,
        "exit_order_status": "NONE",
    }
    harvester.active_positions[tid] = pos

    harvester.executor.get_conditional_balance = lambda tid: 50.0
    harvester.executor.get_current_block_number = lambda: 65000000

    # 1. Market resolves UP (won=True)
    asyncio.run(harvester._apply_market_resolution(tid, pos, winning_outcome="UP"))

    # Invariants for Step 1:
    assert pos["status"] == "AWAITING_ONCHAIN_SETTLEMENT"
    assert pos["redemption_receivable_usd"] == 50.0
    assert pos["expected_terminal_payout_usd"] == 50.0
    assert float(pos.get("realized_exit_cash", 0.0) or 0.0) == 0.0, "Realized cash must be 0 prior to redemption"
    assert len(harvester.closed_positions) == 0, "Must not close position until verified redemption"

    # 2. On-chain redemption arrives: verified receipt credits cash and closes position
    tx_hash = "0xREDEMPTION_TX_HASH_001"
    harvester.executor.find_redemption_payouts = lambda condition_id, from_block=None, tx_hash=None: [
        {"transaction_hash": tx_hash, "payout_usd": 50.0}
    ]
    ok = harvester.confirm_onchain_redemption(tid, verified_usdc_received=50.0, tx_hash=tx_hash)
    assert ok is True
    assert tid not in harvester.active_positions
    closed = next(p for p in harvester.closed_positions if p["trade_id"] == tid)
    assert closed["payout_usd"] == 50.0
    assert closed["net_pnl_usd"] == round(50.0 - 30.0 - 0.50, 2)  # +$19.50
    assert closed["redemption_tx_hash"] == tx_hash

    # 3. Duplicate redemption receipt is safely ignored
    dup_ok = harvester.confirm_onchain_redemption(tid, verified_usdc_received=50.0, tx_hash=tx_hash)
    assert dup_ok is False

    # 4. Contradictory partial fill quantity routes to UNKNOWN
    unwind_contradictory = {
        "success": False,
        "orderID": "0xUNWIND_CONTRADICTORY",
        "matched_size": 0.0,
        "taking_amount": 25.0,  # Contradictory: positive taking with 0 matched!
    }
    outcome = harvester._handle_unwind_response(
        "DUMMY_TID", {}, unwind_contradictory, 50.0, "STOP_LOSS", "PARTIAL", 0.50
    )
    assert outcome == "UNKNOWN", "Contradictory fill quantity must route to UNKNOWN"


def test_round9_unconstrained_half_kelly_compounding():
    """
    Verifies that default configuration safely respects the $37.50 cap, while
    unconstrained_kelly=True allows proportional Half-Kelly scaling (12% of bankroll).
    """
    # 1. Default mode: clamped at $37.50
    harvester_default = PolymarketLiveHarvester(dry_run=True, unconstrained_kelly=False)
    t_clamped = harvester_default.compute_kelly_ticket_size(0.84, 0.75, 1000.0)
    assert t_clamped == 37.50

    # 2. Unconstrained mode: scales with 12% of bankroll ($120.00 on $1,000)
    harvester_unconstrained = PolymarketLiveHarvester(dry_run=True, unconstrained_kelly=True)
    t_unconstrained = harvester_unconstrained.compute_kelly_ticket_size(0.84, 0.75, 1000.0)
    assert t_unconstrained == 120.00

    # 3. Explicit ticket cap parameter works as upper bound
    harvester_capped = PolymarketLiveHarvester(dry_run=True, unconstrained_kelly=True, max_absolute_ticket_usd=50.0)
    t_custom_cap = harvester_capped.compute_kelly_ticket_size(0.84, 0.75, 1000.0)
    assert t_custom_cap == 50.00


def test_round9_live_sizing_uses_frozen_calibration_for_production_shaped_shock():
    """
    Regression (2026-10-13 04:35 UTC daemon crash): production recorder shocks carry NO
    `probability_model` / `p_model`, so live sizing falls back to the frozen calibration.
    That fallback read `self.calibrated_model_id`, which a refactor had deleted, raising
    AttributeError on the first qualifying signal and terminating the daemon.
    """
    harvester = PolymarketLiveHarvester(ticket_notional=35.0, dry_run=False)
    assert harvester.calibrated_model_id, "Frozen calibration id must be defined for live sizing"
    harvester.save_state = lambda: None
    harvester.executor.get_collateral_balance = lambda: 231.66
    sizing_calls = []

    def spy_kelly(p, px, bankroll):
        sizing_calls.append((p, px, bankroll))
        return 0.0  # stop before order submission; we only need the sizing path to be reached

    harvester.compute_kelly_ticket_size = spy_kelly
    executed = []
    harvester.executor.execute_snipe_order_async = lambda **kwargs: executed.append(kwargs)

    shock = {  # production shape: no probability_model, no p_model
        "event_id": "EVT_PROD_SHAPE_CALIB_01",
        "market_id": "5599001",
        "title": "Bitcoin Up or Down - Calibration Fallback Regression",
        "shock_direction": "BUY",
        "seconds_to_expiry": 1200.0,
        "candle_distance_pct": 0.30,
        "fee_metadata": {"fee_rate_market": 0.07, "fee_exponent": 1.0},
        "pre_shock_features_t0": {
            "UP": {"token_id": "0xTOKCALIB", "raw_top_asks": [[0.80, 200.0]], "raw_top_bids": [[0.79, 200.0]]}
        },
    }
    asyncio.run(harvester.evaluate_shock_and_execute(shock))  # must not raise AttributeError
    assert sizing_calls, "Live sizing path must be reached for a qualifying production-shaped shock"
    assert sizing_calls[0][0] == pytest.approx(harvester.calibrated_p_model)
    assert executed == []


def test_maker_exit_persists_tick_quantized_posted_price():
    """
    Live 2026-10-13 13:40 UTC: target 0.8827 was ceiling-rounded by the executor and rested at 0.89,
    but the position kept 0.8827. The persisted target must equal the price actually on the book.
    """
    harvester = PolymarketLiveHarvester(dry_run=True)
    pos = {"trade_id": "T_EXIT_PX", "target_exit_price": 0.8827}
    assert harvester._apply_exit_post_result(pos, {"success": True, "orderID": "0xEXIT", "price": 0.89}, 27.33)
    assert pos["target_exit_price"] == pytest.approx(0.89)
    assert pos["requested_exit_price"] == pytest.approx(0.8827)
    assert pos["exit_order_status"] == "RESTING"

    # Missing / non-numeric price (e.g. dry-run mock result) leaves the target untouched.
    pos2 = {"trade_id": "T_EXIT_PX2", "target_exit_price": 0.78}
    assert harvester._apply_exit_post_result(pos2, {"success": True, "orderID": "0xEXIT2", "price": MagicMock()}, 10.0)
    assert pos2["target_exit_price"] == pytest.approx(0.78)
    assert "requested_exit_price" not in pos2


def test_option2_slippage_kelly_guard_rejects_when_limit_price_has_no_edge():
    """
    Option 2 (Honest Slippage Kelly Sizing):
    When execution limit (worst_acceptable_px) slips into a zone where model edge
    shrinks below hurdle (ticket size < $5.00 min lot), executor must reject the order
    BEFORE posting to exchange, preventing high-slippage zero-edge fills.
    """
    executor = PolymarketLiveExecutor(dry_run=True)
    # Orderbook ask at 0.78, limit at 0.81
    mock_book = {
        "asks": [{"price": "0.78", "size": "100.0"}, {"price": "0.81", "size": "100.0"}],
        "bids": [{"price": "0.77", "size": "100.0"}]
    }
    executor.get_market_book = lambda token_id: mock_book
    async def mock_book_async(token_id):
        return mock_book
    executor.get_market_book_async = mock_book_async

    # sizing_fn simulates Kelly: positive at 0.77 ($25), but $0.00 at 0.81 (edge extinguished)
    def mock_kelly(px):
        if px <= 0.78:
            return 25.0
        return 0.0  # zero ticket at 0.81

    token_id = "0x1234567890abcdef1234"

    # 1. Sync snipe order
    res_sync = executor.execute_snipe_order(
        trade_id="T_SLIP_REJECT_SYNC",
        token_id=token_id,
        target_token="UP",
        notional_usd=25.0,
        target_price=0.77,
        sizing_fn=mock_kelly,
    )
    assert res_sync.success is False
    assert res_sync.execution_status == ExecutionStatus.REJECTED
    assert "SlippageKellyGuard Rejected" in res_sync.error
    assert res_sync.size == 0.0

    # 2. Async snipe order parity
    res_async = asyncio.run(executor.execute_snipe_order_async(
        trade_id="T_SLIP_REJECT_ASYNC",
        token_id=token_id,
        target_token="UP",
        notional_usd=25.0,
        target_price=0.77,
        sizing_fn=mock_kelly,
    ))
    assert res_async.success is False
    assert res_async.execution_status == ExecutionStatus.REJECTED
    assert "SlippageKellyGuard Rejected" in res_async.error
    assert res_async.size == 0.0


def test_option2_slippage_kelly_guard_downsizes_ticket_at_limit_price():
    """
    Option 2 (Honest Slippage Kelly Sizing):
    When execution limit slips to a price where model edge is lower but still viable
    (recomputed ticket < requested notional, but >= $5.00 min lot), executor must downsize
    the notional to match the edge at the limit price.
    """
    executor = PolymarketLiveExecutor(dry_run=True)
    # Orderbook ask at 0.68 -> worst_acceptable_px = 0.71
    mock_book = {
        "asks": [{"price": "0.68", "size": "100.0"}, {"price": "0.71", "size": "100.0"}],
        "bids": [{"price": "0.67", "size": "100.0"}]
    }
    executor.get_market_book = lambda token_id: mock_book
    async def mock_book_async(token_id):
        return mock_book
    executor.get_market_book_async = mock_book_async

    # sizing_fn returns $30 at 0.67, but $15 at 0.71
    def mock_kelly(px):
        if px <= 0.68:
            return 30.0
        elif px <= 0.71:
            return 15.0
        return 0.0

    token_id = "0x1234567890abcdef1234"

    res_sync = executor.execute_snipe_order(
        trade_id="T_SLIP_DOWNSIZE_SYNC",
        token_id=token_id,
        target_token="UP",
        notional_usd=30.0,
        target_price=0.67,
        sizing_fn=mock_kelly,
    )
    assert res_sync.success is True
    assert res_sync.notional_usd == pytest.approx(15.0)

    res_async = asyncio.run(executor.execute_snipe_order_async(
        trade_id="T_SLIP_DOWNSIZE_ASYNC",
        token_id=token_id,
        target_token="UP",
        notional_usd=30.0,
        target_price=0.67,
        sizing_fn=mock_kelly,
    ))
    assert res_async.success is True
    assert res_async.notional_usd == pytest.approx(15.0)


def test_executor_custom_ticket_cap_for_unconstrained_kelly():
    """
    Verifies that passing max_ticket_cap overrides the legacy $37.50 clamp
    in execute_snipe_order and execute_snipe_order_async, allowing proportional
    Half-Kelly compounding beyond $37.50.
    """
    executor = PolymarketLiveExecutor(dry_run=True)
    mock_book = {
        "asks": [{"price": "0.50", "size": "500.0"}],
        "bids": [{"price": "0.49", "size": "500.0"}]
    }
    executor.get_market_book = lambda token_id: mock_book
    async def mock_book_async(token_id):
        return mock_book
    executor.get_market_book_async = mock_book_async

    token_id = "0x1234567890abcdef1234"

    # Default cap clamp to $37.50 when max_ticket_cap is None
    res_default = executor.execute_snipe_order(
        trade_id="T_CAP_DEFAULT",
        token_id=token_id,
        target_token="UP",
        notional_usd=100.0,
        target_price=0.50,
        max_ticket_cap=None,
    )
    assert res_default.notional_usd == pytest.approx(37.50)

    # Custom cap allows $100.00
    res_custom = executor.execute_snipe_order(
        trade_id="T_CAP_CUSTOM",
        token_id=token_id,
        target_token="UP",
        notional_usd=100.0,
        target_price=0.50,
        max_ticket_cap=120.0,
    )
    assert res_custom.notional_usd == pytest.approx(100.0)

    # Async custom cap allows $100.00
    res_custom_async = asyncio.run(executor.execute_snipe_order_async(
        trade_id="T_CAP_CUSTOM_ASYNC",
        token_id=token_id,
        target_token="UP",
        notional_usd=100.0,
        target_price=0.50,
        max_ticket_cap=120.0,
    ))
    assert res_custom_async.notional_usd == pytest.approx(100.0)


def test_harvester_passes_sizing_fn_and_max_ticket_cap_to_async_snipe():
    """
    Verifies that PolymarketLiveHarvester passes sizing_fn and max_ticket_cap
    to executor.execute_snipe_order_async when dispatching entries.
    """
    harvester = PolymarketLiveHarvester(
        ticket_notional=35.0,
        dry_run=False,
        unconstrained_kelly=True,
        max_absolute_ticket_usd=150.0,
    )
    harvester.save_state = lambda: None
    harvester.executor.get_collateral_balance = lambda: 500.0
    harvester.executor.get_onchain_erc1155_balance = lambda tid: 0.0
    harvester.executor.is_authenticated = True
    harvester.executor.client = MagicMock()
    captured_kwargs = {}

    async def mock_snipe(**kwargs):
        captured_kwargs.update(kwargs)
        res = MagicMock()
        res.success = True
        res.details = {}
        res.price = 0.65
        res.size = 20.0
        res.notional_usd = 13.0
        res.fee_usd = 0.20
        res.order_id = "0xMOCK_SNIPE"
        return res

    harvester.executor.execute_snipe_order_async = mock_snipe

    token_id = "0x1234567890abcdef1234"
    shock = {
        "event_id": "EVT_TEST_PASS_ARGS",
        "market_id": "5599002",
        "condition_id": "0xCOND1234567890abcdef1234",
        "title": "Bitcoin Up or Down - Pass Args Test",
        "shock_direction": "BUY",
        "seconds_to_expiry": 1200.0,
        "candle_distance_pct": 0.30,
        "fee_metadata": {"fee_rate_market": 0.07, "fee_exponent": 1.0},
        "pre_shock_features_t0": {
            "UP": {"token_id": token_id, "raw_top_asks": [[0.65, 200.0]], "raw_top_bids": [[0.64, 200.0]]}
        },
    }
    asyncio.run(harvester.evaluate_shock_and_execute(shock))
    assert "sizing_fn" in captured_kwargs
    assert callable(captured_kwargs["sizing_fn"])
    assert captured_kwargs["max_ticket_cap"] == 150.0


# ---------------------------------------------------------------------------
# Round 10 adversarial audit remediation (Release 2.4.1)
# ---------------------------------------------------------------------------

R10_TOKEN = "0x1234567890abcdef1234"


def _r10_executor(book):
    executor = PolymarketLiveExecutor(dry_run=True)
    executor.get_market_book = lambda token_id: book

    async def _book_async(token_id):
        return book

    executor.get_market_book_async = _book_async
    return executor


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf"), 0.0, -5.0, "abc", None])
def test_round10_p0_04_invalid_notional_rejected_sync_and_async(bad):
    """P0-04: invalid notionals must be rejected, never coerced into a $37.50 ticket."""
    book = {"asks": [{"price": "0.50", "size": "500.0"}], "bids": [{"price": "0.49", "size": "500.0"}]}
    executor = _r10_executor(book)
    kw = dict(trade_id="T_R10_BAD", token_id=R10_TOKEN, target_token="UP", notional_usd=bad, target_price=0.50)

    res = executor.execute_snipe_order(**kw)
    assert res.success is False and res.execution_status == ExecutionStatus.REJECTED
    assert res.notional_usd == 0.0 and res.size == 0.0
    assert "NotionalGuard" in res.error

    res_a = asyncio.run(executor.execute_snipe_order_async(**kw))
    assert res_a.success is False and res_a.execution_status == ExecutionStatus.REJECTED
    assert "NotionalGuard" in res_a.error


@pytest.mark.parametrize("bad_level", [
    {"price": "0.50", "size": "inf"},
    {"price": "0.50", "size": "nan"},
    {"price": "nan", "size": "100"},
    {"price": "1.50", "size": "100"},
    {"price": "0.50", "size": "-10"},
])
def test_round10_p1_02_malformed_book_level_fails_closed(bad_level):
    """P1-02: a single non-finite / out-of-range level invalidates the book side."""
    book = {"asks": [{"price": "0.49", "size": "100.0"}, bad_level], "bids": [{"price": "0.48", "size": "100.0"}]}
    executor = _r10_executor(book)
    res = executor.execute_snipe_order(
        trade_id="T_R10_BOOK", token_id=R10_TOKEN, target_token="UP", notional_usd=10.0, target_price=0.49,
    )
    assert res.success is False
    assert res.execution_status == ExecutionStatus.REJECTED


def test_round10_p1_06_quantize_rejects_non_finite():
    executor = PolymarketLiveExecutor(dry_run=True)
    for bad in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValueError):
            executor.quantize_order_price(bad, R10_TOKEN)
    assert executor.quantize_order_price(0.68 + 0.03, R10_TOKEN, rounding="ROUND_CEILING") == pytest.approx(0.71)


def test_round10_p0_01_unconstrained_kelly_cannot_breach_absolute_exposure_ceiling():
    """
    P0-01 auditor scenario: bankroll $1,000, ceiling $100, $90 already committed (in flight),
    unconstrained Kelly proposes ~$120. The submitted order must keep total <= $100.
    """
    harvester = PolymarketLiveHarvester(
        ticket_notional=35.0, dry_run=False, unconstrained_kelly=True, max_exposure=100.0, max_concurrent=3,
    )
    harvester.save_state = lambda: None
    harvester.executor.get_collateral_balance = lambda: 1000.0
    harvester.executor.get_onchain_erc1155_balance = lambda tid: 0.0
    harvester.executor.is_authenticated = True
    harvester.executor.client = MagicMock()
    # (In-flight intents globally halt entries outright, so the $90 is modelled as an open position.)
    harvester.active_positions["OPEN_90"] = {
        "trade_id": "OPEN_90", "status": "FILLED", "notional_usd": 90.0,
        "token_id": "OTHER_TOKEN_90", "market_id": "OTHER_MKT", "event_id": "OTHER_EVT",
        "condition_id": "0xOTHER", "direction": "UP", "entry_price": 0.60, "shares": 150.0,
    }
    captured = {}

    async def mock_snipe(**kwargs):
        captured.update(kwargs)
        res = MagicMock()
        res.success = False
        res.details = {}
        res.error = "test stop"
        return res

    harvester.executor.execute_snipe_order_async = mock_snipe
    shock = {
        "event_id": "EVT_R10_EXPOSURE",
        "market_id": "5599010",
        "condition_id": "0xCOND1234567890abcdef1234",
        "title": "Bitcoin Up or Down - Exposure Ceiling",
        "shock_direction": "BUY",
        "seconds_to_expiry": 1200.0,
        "candle_distance_pct": 0.30,
        "fee_metadata": {"fee_rate_market": 0.07, "fee_exponent": 1.0},
        "pre_shock_features_t0": {
            "UP": {"token_id": R10_TOKEN, "raw_top_asks": [[0.65, 2000.0]], "raw_top_bids": [[0.64, 2000.0]]}
        },
    }
    try:
        asyncio.run(harvester.evaluate_shock_and_execute(shock))
    except Exception:
        pass  # downstream handling of the mocked failure is irrelevant; only the submitted size matters
    assert captured, "Scenario must reach submission so the size bound is actually exercised"
    assert 90.0 + float(captured["notional_usd"]) <= 100.0 + 1e-6


def test_round10_p0_01_exposure_cap_is_never_raised_by_bankroll_scaling():
    """Static check of the policy: scaling may shrink but never replace max_exposure."""
    import inspect
    src = inspect.getsource(PolymarketLiveHarvester.evaluate_shock_and_execute)
    assert "exposure_cap = max(self.max_exposure" not in src
    assert "(current_exposure + MIN_LOT_SIZE_USD) > self.max_exposure" not in src


def test_round10_p1_01_kelly_binds_to_authoritative_fee_schedule():
    """P1-01: Proves Kelly sizing recomputes consistently using authoritative fee parameters."""
    harvester = PolymarketLiveHarvester(dry_run=True)
    # At standard 0.07 fee:
    size_std = harvester.compute_kelly_ticket_size(0.75, 0.65, 200.0, fee_rate=0.07, fee_exponent=1.0)
    assert size_std > 0.0
    # At zero or invalid fee:
    size_bad = harvester.compute_kelly_ticket_size(0.75, 0.65, 200.0, fee_rate=float("nan"), fee_exponent=1.0)
    assert size_bad == 0.0
    # If fee rate increases dramatically (e.g. 0.30), edge evaporates and ticket must shrink or drop to 0
    size_high_fee = harvester.compute_kelly_ticket_size(0.75, 0.65, 200.0, fee_rate=0.30, fee_exponent=1.0)
    assert size_high_fee < size_std


def test_round10_p1_03_maker_reservation_convergence_and_remaining_size():
    """P1-03: Proves maker reservation tracks remaining size (original - matched) and updates on partial fill."""
    executor = PolymarketLiveExecutor(dry_run=True)
    tok = "0xR10_P103_TOKEN"
    oid = "OID_MAKER_P103"
    
    # 40 shares posted, 10 matched on submission -> reserves 30
    rem = 40.0 - 10.0
    executor.reserve_inventory(tok, rem, reservation_id=oid)
    assert executor.reserved_inventory[tok] == pytest.approx(30.0)
    
    # Subsequent partial fill: matched increases to 25 -> remaining converges to 15
    executor.update_reservation(oid, 40.0 - 25.0)
    assert executor.reserved_inventory[tok] == pytest.approx(15.0)
    
    # Order fully matched or canceled -> releases reservation
    executor.update_reservation(oid, 0.0)
    assert executor.reserved_inventory[tok] == pytest.approx(0.0)


def test_round10_p1_04_separate_confirmed_and_estimated_cash():
    """P1-04: Proves confirmed_realized_cash and estimated_exit_cash are maintained as separate ledger fields."""
    pos = {
        "trade_id": "T_P104", "entry_shares": 50.0, "notional_usd": 35.0,
    }
    # First fill: estimated from matched * limit_px
    PolymarketLiveHarvester.record_fill_and_update_position(
        pos, "OID_EST", matched_shares=20.0, taking_cash=16.0, fee_usd=0.0, cash_is_estimated=True,
    )
    assert pos["confirmed_realized_cash"] == 0.0
    assert pos["estimated_exit_cash"] == 16.0
    assert pos["realized_exit_cash"] == 16.0
    assert pos["exit_cash_estimated"] is True

    # Second fill: confirmed from exact account fill trade receipt
    PolymarketLiveHarvester.record_fill_and_update_position(
        pos, "OID_CONF", matched_shares=30.0, taking_cash=24.50, fee_usd=0.0, cash_is_estimated=False,
    )
    assert pos["confirmed_realized_cash"] == 24.50
    assert pos["estimated_exit_cash"] == 16.0
    assert pos["realized_exit_cash"] == pytest.approx(40.50)
    assert pos["exit_cash_estimated"] is True


def test_round10_p2_01_authenticated_reservation_hmac():
    """P2-01: Proves reservation file integrity uses authenticated HMAC digest."""
    rec = {"OID1": {"token_id": "TOK1", "size": 10.0, "status": "RESERVED"}}
    hmac_digest = PolymarketLiveExecutor._reservation_digest(rec)
    assert isinstance(hmac_digest, str) and len(hmac_digest) == 64
    assert PolymarketLiveExecutor._verify_reservation_digest(rec, hmac_digest) is True
    # Tampered records fail verification
    tampered = {"OID1": {"token_id": "TOK1", "size": 999.0, "status": "RESERVED"}}
    assert PolymarketLiveExecutor._verify_reservation_digest(tampered, hmac_digest) is False
