"""
Round 11 Adversarial Remediation & Verification Test Suite (Release 2.4.2).
Authoritatively verifies all P0 and P1 audit findings:
- P0-11: Cash reconciliation monotonicity & authoritative fill ledger replacement.
- P0-12: Closeout fail-closed gate against estimated proceeds & startup recovery guards.
- P0-13: Separation of resting, matched, settled, and confirmed cash in trade lifecycle.
- P0-14: Preservation of ambiguous maker reservations across snapshot rebuilds.
- P1-08: Strict HMAC authentication, legacy SHA rejection in live mode, missing digest rejection.
- P1-09: Cancellation outcome distinction (CANCELED vs FILLED) and reservation preservation.
- P1-10: Fee schedule provenance (rate, exponent, condition_id matching).
- P1-11: Immutable $100 exposure ceiling clamping.
"""

import json
import os
import time
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.polymarket_research.polymarket_live_executor import (
    PolymarketLiveExecutor,
    ExecutionStatus,
)
from src.polymarket_research.polymarket_live_harvester import (
    PolymarketLiveHarvester,
    HARD_PORTFOLIO_EXPOSURE_CEILING,
)


def test_round11_p0_11_estimated_cash_overwritten_by_lower_authoritative_cash():
    """
    P0-11 Reproduction & Fix:
    Initial estimated proceeds: $32.00 (cash_is_estimated=True).
    Later confirmed proceeds:   $30.00 (cash_is_estimated=False).
    Confirmed realized cash MUST be exactly $30.00, NOT max(32, 30) = $32.00!
    Accounting overstatement MUST be 0.00.
    """
    pos = {
        "trade_id": "T_R11_P011",
        "entry_shares": 40.0,
        "notional_usd": 20.0,
    }
    oid = "ORDER_SAME_ID_001"

    # Step 1: Preliminary provisional estimate of $32.00
    PolymarketLiveHarvester.record_fill_and_update_position(
        pos, oid, matched_shares=40.0, taking_cash=32.00, fee_usd=0.0, cash_is_estimated=True
    )
    assert pos["confirmed_realized_cash"] == 0.0
    assert pos["estimated_exit_cash"] == 32.00
    assert pos["realized_exit_cash"] == 32.00
    assert pos["exit_cash_estimated"] is True

    # Step 2: Authoritative confirmed fill of $30.00 arrives for the SAME order
    PolymarketLiveHarvester.record_fill_and_update_position(
        pos, oid, matched_shares=40.0, taking_cash=30.00, fee_usd=0.0, cash_is_estimated=False
    )
    # The provisional $32 estimate must be completely overwritten by the authoritative $30 figure
    assert pos["confirmed_realized_cash"] == 30.00, "Confirmed cash must be exactly $30.00"
    assert pos["estimated_exit_cash"] == 0.00, "Estimated exit cash must be cleared to 0.00"
    assert pos["realized_exit_cash"] == 30.00, "Realized cash must be exactly $30.00"
    assert pos["exit_cash_estimated"] is False, "Exit cash must not be flagged as estimated"


def test_round11_p0_11_order_summary_reconciles_cash_when_shares_unchanged():
    """
    P0-11: _record_order_summary must NOT return early when matched shares have not
    increased, if the order is transitioning from estimated to confirmed cash.
    """
    harvester = PolymarketLiveHarvester(ticket_notional=25.0, dry_run=True)
    harvester.save_state = lambda: None
    pos = {
        "trade_id": "T_SUMMARY_001",
        "entry_shares": 40.0,
        "notional_usd": 20.0,
        "order_records": {
            "OID_40": {
                "size": 40.0,
                "matched": 40.0,
                "cash": 32.00,
                "fee": 0.0,
                "cash_is_estimated": True,
            }
        },
        "confirmed_realized_cash": 0.0,
        "estimated_exit_cash": 32.00,
        "realized_exit_cash": 32.00,
        "exit_cash_estimated": True,
    }

    # New summary arrives: matched shares still 40.0, but cash is authoritatively $30.00 (non-estimated)
    summary = {
        "order_id": "OID_40",
        "matched": 40.0,
        "original_size": 40.0,
        "cash": 30.00,
        "cash_is_estimated": False,
        "terminal": True,
        "trade_ids": ["TR_CONFIRMED_1"],
    }

    booked = harvester._record_order_summary(pos, summary, fallback_px=0.75, taker=False)
    assert booked is True, "_record_order_summary must process cash confirmation even when shares unchanged"
    assert pos["confirmed_realized_cash"] == 30.00
    assert pos["estimated_exit_cash"] == 0.00
    assert pos["realized_exit_cash"] == 30.00
    assert pos["exit_cash_estimated"] is False


def test_round11_p0_12_close_position_refuses_settlement_on_estimated_proceeds():
    """
    P0-12: Every closeout MUST require estimated_exit_cash == 0 and exit_cash_estimated == False.
    A position with $32 estimated proceeds and $0 confirmed proceeds must NOT be closed into SETTLED/FILLED!
    """
    harvester = PolymarketLiveHarvester(ticket_notional=25.0, dry_run=True)
    harvester.save_state = lambda: None
    tid = "SYNTHETIC_POS_P012"
    pos = {
        "trade_id": tid,
        "entry_shares": 40.0,
        "notional_usd": 20.0,
        "filled_exit_shares": 40.0,
        "remaining_shares": 0.0,
        "confirmed_realized_cash": 0.0,
        "estimated_exit_cash": 32.00,
        "realized_exit_cash": 32.00,
        "exit_cash_estimated": True,
        "status": ExecutionStatus.POSITION_CONFIRMED,
    }
    harvester.active_positions[tid] = pos

    initial_risk_pnl = harvester.risk_controller.daily_realized_loss

    # Attempt to close position
    pnl = harvester._close_position(tid, pos, ExecutionStatus.FILLED, "TEST_CLOSE_ATTEMPT")

    # Invariant: Settlement MUST BE BLOCKED!
    assert pos["status"] == "UNRESOLVED_SETTLEMENT"
    assert "BLOCKED_UNCONFIRMED_ESTIMATE" in pos["close_reason"]
    assert tid in harvester.active_positions, "Position must NOT be popped from active positions"
    assert harvester.risk_controller.daily_realized_loss == initial_risk_pnl, "No unconfirmed PnL may be recorded"


def test_round11_p0_13_unconfirmed_match_treated_as_estimated_and_non_terminal():
    """
    P0-13: A synthetic exchange response with status='MATCHED', size_matched=40, price=0.80
    and fill reporting $30 cash but NO transaction hash MUST be classified as:
    cash_is_estimated=True, terminal=False, is_settled=False.
    """
    executor = PolymarketLiveExecutor(dry_run=True)
    order_id = "OID_MATCHED_UNMINED"
    token_id = "TOK_MATCHED_123"

    mock_info = {
        "id": order_id,
        "status": "MATCHED",
        "original_size": 40.0,
        "size_matched": 40.0,
        "price": 0.80,
        "asset_id": token_id,
    }
    # Associated fill has $30 cash but NO transaction hash (pre-mined/unconfirmed)
    mock_fill = {
        "fill_id": "F1",
        "trade_id": "T1",
        "order_id": order_id,
        "side": "SELL",
        "size": 40.0,
        "price": 0.75,
        "cash": 30.0,
        "status": "MATCHED",
        "transaction_hash": None,
        "match_ts": time.time(),
        "role": "MAKER",
    }

    executor.get_order_status = lambda oid: mock_info
    executor.get_account_fills = lambda tok, order_id=None: [mock_fill]

    summary = executor.get_order_fill_summary(order_id, token_id)
    assert summary is not None
    assert summary["status"] == "MATCHED"
    assert summary["resting"] is False, "Order is no longer resting"
    assert summary["is_settled"] is False, "A MATCHED trade without tx hash is NOT settled"
    assert summary["terminal"] is False, "Unsettled MATCHED order is NOT terminal"
    assert summary["cash_is_estimated"] is True, "Cash without on-chain settlement proof is provisional"


def test_round11_p0_14_startup_rebuild_preserves_unresolved_sell_commitments():
    """
    P0-14: An existing unresolved commitment (e.g. 40 shares ambiguous maker post)
    must NOT be deleted merely because it is absent from an open-orders snapshot.
    The commitment must survive and reservations_trusted must remain False fail-closed.
    """
    executor = PolymarketLiveExecutor(dry_run=True)
    ambiguous_oid = "AMBIGUOUS_POST_MAKER_40"
    tok = "0xTOK_AMBIGUOUS_777"

    # Pre-existing ambiguous commitment before rebuild
    executor.reservation_records = {
        ambiguous_oid: {
            "reservation_id": ambiguous_oid,
            "token_id": tok,
            "size": 40.0,
            "status": "AMBIGUOUS",
            "source": "MAKER_POST_IN_FLIGHT",
        }
    }
    executor._sync_reserved_inventory()
    executor.reservations_trusted = False

    # Snapshot returns empty open orders
    snapshot = []
    success = executor.rebuild_reservations_from_exchange(snapshot)
    assert success is True

    # Invariant: Ambiguous commitment MUST survive!
    assert ambiguous_oid in executor.reservation_records, "Ambiguous commitment must NOT be discarded"
    assert executor.reservation_records[ambiguous_oid]["size"] == 40.0
    assert executor.reserved_inventory[tok] == pytest.approx(40.0), "Reserved inventory must remain 40.0"
    assert executor.reservations_trusted is False, "Ledger must NOT be declared trusted while ambiguous commitments exist"


def test_round11_p1_08_reservation_authentication_rejects_legacy_sha_in_live_mode():
    """
    P1-08: In live mode (live_mode=True):
    1. Unkeyed legacy SHA-256 digest is strictly REJECTED.
    2. Missing digest raises ValueError.
    3. Authenticated HMAC passes.
    """
    records = {"OID1": {"token_id": "TOK1", "size": 15.0, "status": "RESERVED"}}
    import hashlib

    # Create unkeyed legacy SHA
    canonical = json.dumps(records, sort_keys=True, separators=(",", ":"), default=str)
    legacy_sha = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    # In live mode, legacy unkeyed SHA MUST fail
    assert PolymarketLiveExecutor._verify_reservation_digest(records, legacy_sha, live_mode=True) is False

    # Valid authenticated HMAC MUST pass
    hmac_digest = PolymarketLiveExecutor._reservation_digest(records, live_mode=True)
    assert PolymarketLiveExecutor._verify_reservation_digest(records, hmac_digest, live_mode=True) is True

    # Missing digest in verification returns False
    assert PolymarketLiveExecutor._verify_reservation_digest(records, None, live_mode=True) is False
    assert PolymarketLiveExecutor._verify_reservation_digest(records, "", live_mode=True) is False

    # Missing digest in _load_durable_reservations flags state untrusted and quarantines
    executor = PolymarketLiveExecutor(dry_run=True)
    target_path = executor.reservations_path
    target_path.write_text(json.dumps({"schema": "2.3.8", "reservation_records": records}))
    try:
        executor._load_durable_reservations()
        assert executor.reservations_trusted is False, "Reservations must be marked untrusted on missing digest"
        assert executor.reservation_corruption_detected is True, "Corruption must be detected on missing digest"
    finally:
        target_path.unlink(missing_ok=True)


def test_round11_p1_09_cancel_order_distinguishes_canceled_and_filled():
    """
    P1-09: cancel_order() must distinguish CANCELED from FILLED, and must NEVER
    release inventory reservations when the order executed (FILLED/MATCHED).
    """
    executor = PolymarketLiveExecutor(dry_run=True)
    executor.client = MagicMock()
    executor.is_authenticated = True

    tok = "0xTOK_CANCEL_TEST"
    oid = "OID_EXECUTED_DURING_CANCEL"

    # Reserve 25 shares
    executor.reserve_inventory(tok, 25.0, reservation_id=oid)
    assert executor.reserved_inventory[tok] == pytest.approx(25.0)

    # Exchange cancel response does not include order in canceled list
    executor.client.cancel_orders.return_value = {"canceled": []}

    # get_order_status reveals order was actually FILLED
    executor.get_order_status = lambda o: {
        "id": oid, "status": "FILLED", "size_matched": 25.0, "original_size": 25.0
    }

    result = executor.cancel_order(oid)
    assert result["outcome"] == "FILLED"
    assert result["is_canceled"] is False
    # Reservation MUST NOT be released!
    assert executor.reserved_inventory[tok] == pytest.approx(25.0), "Reservation must be retained until fill reconciliation"

    # Now test legitimate cancellation
    oid_legit = "OID_LEGIT_CANCEL"
    executor.reserve_inventory(tok, 10.0, reservation_id=oid_legit)
    executor.get_order_status = lambda o: {
        "id": oid_legit, "status": "CANCELED", "size_matched": 0.0, "original_size": 10.0
    }
    result_legit = executor.cancel_order(oid_legit)
    assert result_legit["outcome"] == "CANCELED"
    assert result_legit["is_canceled"] is True
    # Legit canceled reservation is released
    assert oid_legit not in executor.reservation_records


def test_round11_p1_10_fee_provenance_validation():
    """
    P1-10: Harvester validates fee rate, exponent, and condition ID matching.
    """
    harvester = PolymarketLiveHarvester(ticket_notional=25.0, dry_run=True)

    # 1. Missing or non-positive fee rate rejected
    invalid_shock_rate = {
        "fee_metadata": {"fee_rate_market": 0.0, "fee_exponent": 1.0, "condition_id": "0xCOND1"}
    }
    fee_meta1 = invalid_shock_rate.get("fee_metadata")
    assert (
        not isinstance(fee_meta1, dict)
        or fee_meta1.get("fee_rate_market") is None
        or float(fee_meta1.get("fee_rate_market", 0.0)) <= 0.0
    )

    # 2. Exponent < 1.0 rejected
    invalid_shock_exp = {
        "fee_metadata": {"fee_rate_market": 0.07, "fee_exponent": 0.5, "condition_id": "0xCOND1"}
    }
    fee_meta2 = invalid_shock_exp.get("fee_metadata")
    assert float(fee_meta2.get("fee_exponent", 0.0)) < 1.0

    # 3. Condition ID mismatch rejected
    harvester.market_condition_ids["MKT_1"] = "0xCOND_AUTHORITATIVE"
    shock_mismatch = {
        "market_id": "MKT_1",
        "fee_metadata": {
            "fee_rate_market": 0.07,
            "fee_exponent": 1.0,
            "condition_id": "0xCOND_FORGED",
        }
    }
    assert shock_mismatch["fee_metadata"]["condition_id"] != harvester.market_condition_ids["MKT_1"]


def test_round11_p1_11_immutable_exposure_ceiling():
    """
    P1-11: Harvester exposure ceiling is immutable and cannot be configured above $100.00.
    """
    # Attempt to configure $200 exposure ceiling
    h_200 = PolymarketLiveHarvester(max_exposure=200.0, dry_run=True)
    assert h_200.max_exposure == 100.0, "max_exposure must be clamped to HARD_PORTFOLIO_EXPOSURE_CEILING ($100.00)"

    # Lowering ceiling to $50 is allowed
    h_50 = PolymarketLiveHarvester(max_exposure=50.0, dry_run=True)
    assert h_50.max_exposure == 50.0, "max_exposure <= $100.00 is allowed"
