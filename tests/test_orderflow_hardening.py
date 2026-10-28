#!/usr/bin/env python3
"""
Order-Flow Hardening & Lifecycle Sequence Regression Suite.

Covers all deterministic order-flow invariants audited across:
  1. Phase 3A Passive Maker-In Rescue (`place_passive_maker_entry`, TTL, 50% adverse spot decay,
     partial maker fill booking, unverified cancel -> `LIVE_PHASE3A_CANCEL_UNKNOWN`, and
     `_classify_entry` resting BUY cancellation before `NOT_EXECUTED`).
  2. Polymarket V2 directional snipe `pos_record` multi-block `PARTIAL_BATCH_SETTLING` hold
     (`entry_order_id` + `fee_source="crypto_fees_v2"`) & immediate `_last_known_collateral` deduction.
  3. `is_clob_400_rejection` false-positive elimination on `"400"` token IDs / `"timeout=4.00"` 5xx errors
     & contradictory `post_resp={"orderID": ..., "error": ...}` fail-closed handling.
  4. `get_order_fill_summary` preserving `FAILED` / `RETRYING` settlements (`include_failed=True`)
     so zero-wallet fallback never fabricates cash on reverted Polygon trades.
  5. D1 Multi-Leg Dominance Box `_unwind_legged_out` with `pre_balance > 0`, `settled_ready == 0`
     supervisor handoff, split-block partial unwind clamping, `uw_1 + uw_2` proceeds aggregation,
     and `_resolve_unknown_entry` unhedged `UNK` partner flip.
  6. `_maybe_merge_live_complete_sets` partial-fill-before-cancel abort, reservation release, and
     `record_fill_and_update_position` complete-set merge accounting.
  7. `_atomic_replace_maker_exit` 2-tranche Iceberg preservation (`QUEUE_JUMP`) vs collapse
     (`OBI_MAKER_STEP_DOWN`), CLOB read-replica lag retry, unsorted REST `/book` L1 OBI + `v_spot_15s_pct`
     gate, `post_maker_exit_order` `crossed_at_max_tick` at `$0.99`, and Two-Stage Passive Stop
     `outcome_unknown` reservation retention.
  8. Multi-threaded reservation lock safety, `PolymarketUserWsCache` maker-leg delta attribution +
     monotonic terminal status + reconnect unseeded guard, and root `polymarket_live_executor` shim parity.
"""

from __future__ import annotations

import asyncio
import threading
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

import src.polymarket_research.polymarket_live_executor as ex_mod
import src.polymarket_research.polymarket_live_harvester as hv_mod
from src.polymarket_research.polymarket_live_executor import (
    ExecutionStatus,
    FastV2OrderSigner,
    OrderResult,
    PolymarketLiveExecutor,
    PreSignedOrderLadderCache,
    is_clob_400_rejection,
)
from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester
from src.polymarket_research.polymarket_ws_streams import PolymarketUserWsCache


@pytest.fixture(autouse=True)
def _offline_clob(monkeypatch):
    """Guarantees 100% offline execution across all tests in this module."""
    monkeypatch.setenv("PM_LATENCY_TRACE", "0")
    monkeypatch.setattr(ex_mod, "ClobClient", MagicMock(name="OfflineClobClient"))
    monkeypatch.setattr(ex_mod, "PY_CLOB_AVAILABLE", True)
    monkeypatch.setenv("POLYGON_PRIVATE_KEY", "0x" + "11" * 32)
    monkeypatch.setenv("POLYGON_FUNDER_ADDRESS", "0x" + "22" * 20)
    monkeypatch.setenv("POLYGON_SIGNATURE_TYPE", "3")


# ---------------------------------------------------------------------------
# 1. Phase 3A Passive Maker-In Rescue & Resting BUY Cancellation
# ---------------------------------------------------------------------------

def test_phase3a_executor_alias_and_maker_rescue_fill_and_unknown_cancel(tmp_path, monkeypatch):
    monkeypatch.setattr(hv_mod, "STATE_FILE", tmp_path / "state.json")
    monkeypatch.setenv("PM_LIVE_PHASE3A_TTL_SEC", "0.25")

    assert PolymarketLiveExecutor.place_passive_maker_entry is PolymarketLiveExecutor.post_maker_entry_order

    h = PolymarketLiveHarvester(dry_run=False)
    h.enable_live_phase3a_maker_fallback = True
    h.save_state = MagicMock()
    h.get_reference_spot_price = MagicMock(return_value=70500.0)

    # Case A: Partial maker fill (8.0 shares) confirmed canceled cleanly after TTL
    h.executor = MagicMock()
    h.executor.auth_mode = "LIVE"
    h.executor._user_ws_cache = None
    h.executor.place_passive_maker_entry = MagicMock(
        return_value={"success": True, "orderID": "0xMKR_1", "shares": 20.0, "price": 0.72}
    )
    h.executor.cancel_order = MagicMock(
        return_value={"is_canceled": True, "outcome": "PARTIALLY_FILLED_CANCELED", "matched": 8.0}
    )
    h.executor.get_order_fill_summary = MagicMock(
        return_value={
            "order_id": "0xMKR_1",
            "matched": 8.0,
            "avg_price": 0.72,
            "terminal": True,
            "resting": False,
            "trade_ids": ["TR_M1"],
            "tx_hashes": ["0xTX_M1"],
        }
    )
    res_fill = asyncio.run(
        h._attempt_live_phase3a_maker_rescue(
            trade_id="T_P3A_FILL",
            token_id="123456789012345678901",
            target_token="UP",
            asset_str="BTC",
            effective_notional=16.50,
            first_ask=0.73,
            first_bid=0.71,
            min_allowed_price=0.55,
            max_allowed_price=0.80,
            open_spot=70000.0,
            entry_spot_ref=70400.0,
            spot_denom="USDT",
            tte=300.0,
            pre_cond_bal=0.0,
            book_snapshot={"bids": [{"price": "0.71", "size": "50"}], "asks": [{"price": "0.73", "size": "50"}]},
        )
    )
    assert res_fill is not None and res_fill.success is True
    assert res_fill.mode == "LIVE_PHASE3A_MAKER_IN"
    assert abs(res_fill.size - 8.0) < 1e-6
    assert abs(res_fill.notional_usd - 5.76) < 1e-6

    # Case B: Cancel fails (`is_canceled=False`, still resting) -> MUST fail closed to outcome_unknown!
    h.executor.place_passive_maker_entry.return_value = {
        "success": True, "orderID": "0xMKR_ORPHAN", "shares": 20.0, "price": 0.72
    }
    h.executor.cancel_order.return_value = {"is_canceled": False, "outcome": "STILL_LIVE", "matched": 0.0}
    h.executor.get_order_fill_summary.return_value = {
        "order_id": "0xMKR_ORPHAN", "matched": 0.0, "terminal": False, "resting": True
    }
    res_unk = asyncio.run(
        h._attempt_live_phase3a_maker_rescue(
            trade_id="T_P3A_UNK",
            token_id="123456789012345678901",
            target_token="UP",
            asset_str="BTC",
            effective_notional=16.50,
            first_ask=0.73,
            first_bid=0.71,
            min_allowed_price=0.55,
            max_allowed_price=0.80,
            open_spot=70000.0,
            entry_spot_ref=70400.0,
            spot_denom="USDT",
            tte=300.0,
            pre_cond_bal=0.0,
            book_snapshot={"bids": [{"price": "0.71", "size": "50"}], "asks": [{"price": "0.73", "size": "50"}]},
        )
    )
    assert res_unk is not None and res_unk.success is False
    assert res_unk.mode == "LIVE_PHASE3A_CANCEL_UNKNOWN"
    assert res_unk.details.get("outcome_unknown") is True
    assert res_unk.order_id == "0xMKR_ORPHAN"


def test_classify_entry_cancels_resting_buy_before_declaring_not_executed(tmp_path, monkeypatch):
    monkeypatch.setattr(hv_mod, "STATE_FILE", tmp_path / "state.json")
    h = PolymarketLiveHarvester(dry_run=False)
    h.executor = MagicMock()
    h._wallet_token_balance = MagicMock(return_value=(0.0, h.ONCHAIN_SOURCE))
    h._fetch_entry_evidence = MagicMock(return_value={"shares": 0.0, "fills": [], "cash": 0.0})

    # If resting LIVE BUY cannot be canceled yet, _classify_entry MUST stay UNKNOWN (never NOT_EXECUTED!)
    h.executor.get_order_status.return_value = {"status": "LIVE", "size_matched": "0"}
    h.executor.cancel_order.return_value = {"is_canceled": False}
    cls_live = h._classify_entry("0xTOK_BUY", 0.0, time.time() - 120.0, "0xBUY_RESTING", "T_1")
    assert cls_live["verdict"] == "UNKNOWN"

    # Once cancel succeeds with 0 matched shares, _classify_entry safely proves NOT_EXECUTED
    h.executor.cancel_order.return_value = {"is_canceled": True, "matched": 0.0}
    h.executor.get_order_status.side_effect = [
        {"status": "LIVE", "size_matched": "0"},
        {"status": "CANCELED", "size_matched": "0"},
    ]
    cls_canc = h._classify_entry("0xTOK_BUY", 0.0, time.time() - 120.0, "0xBUY_RESTING", "T_1")
    assert cls_canc["verdict"] == "NOT_EXECUTED"
    assert cls_canc["proof"] == "RESTING_ENTRY_CANCELED_ZERO_FILL"


# ---------------------------------------------------------------------------
# 2. V2 Multi-Block Partial-Batch-Settling Hold & Immediate Collateral Deduction
# ---------------------------------------------------------------------------

def test_v2_directional_snipe_partial_batch_settling_and_collateral_deduction(tmp_path, monkeypatch):
    tick_dir, tele_dir = tmp_path / "shm", tmp_path / "tele"
    tick_dir.mkdir()
    tele_dir.mkdir()
    (tick_dir / "pm_fast_tick_BTC.json").write_text('{"ts": 0}', encoding="utf-8")
    monkeypatch.setenv("PM_FAST_TICK_DIR", str(tick_dir))
    monkeypatch.setenv("PM_TELEMETRY_DIR", str(tele_dir))
    monkeypatch.setenv("POLYMARKET_ALERTS_FILE", str(tmp_path / "alerts.jsonl"))
    monkeypatch.setattr(hv_mod, "_ALERT_LAST_SENT", {})
    monkeypatch.setattr(hv_mod, "STATE_FILE", tmp_path / "state.json")

    h = PolymarketLiveHarvester(ticket_notional=16.50, dry_run=False, hold_to_maturity=False, max_concurrent=2)
    h.executor.auth_mode = "LIVE"
    h.executor.is_authenticated = True
    h.executor.is_heartbeat_healthy = lambda: True
    h._last_known_collateral = 100.00
    h.executor.get_collateral_balance = lambda *a, **k: 100.00
    h.executor.get_market_book_async = AsyncMock(
        return_value={"asks": [{"price": "0.65", "size": "400.0"}], "bids": [{"price": "0.64", "size": "400.0"}]}
    )
    h._spawn_fast_confirm = MagicMock()

    tok_id = "0xTOK_V2_BATCH_1"

    async def mock_snipe(**kw):
        return OrderResult(
            success=True,
            order_id="0xENTRY_V2_BATCH",
            trade_id=kw["trade_id"],
            token_id=tok_id,
            target_token="UP",
            side="BUY",
            price=0.65,
            size=25.0,
            notional_usd=16.25,
            fee_usd=0.25,
            latency_ms=12.0,
            mode="LIVE_PRODUCTION",
            execution_status=ExecutionStatus.MATCHED_PENDING_SETTLEMENT,
            confirmed_onchain=False,
            details={"pre_token_balance": 0.0, "trade_ids": ["TR_B1", "TR_B2"], "transactions_hashes": []},
        )

    h.executor.execute_snipe_order_async = mock_snipe
    shock = {
        "event_id": "EVT_V2",
        "market_id": "MKT_V2_BATCH_1",
        "t0_unix": time.time(),
        "title": "BTC 1h Up",
        "asset": "BTC",
        "shock_direction": "BUY",
        "seconds_to_expiry": 600.0,
        "candle_distance_pct": 0.45,
        "fee_metadata": {"fee_rate_market": 0.07, "fee_exponent": 1.0},
        "pre_shock_features_t0": {
            "UP": {"token_id": tok_id, "raw_top_asks": [[0.65, 400.0]], "effective_price_$50": 0.65, "vwap_$50": 0.65}
        },
    }
    asyncio.run(h.evaluate_shock_and_execute(shock))

    assert len(h.active_positions) == 1
    tid, pos = next(iter(h.active_positions.items()))
    assert pos["order_id"] == "0xENTRY_V2_BATCH"
    assert pos["entry_order_id"] == "0xENTRY_V2_BATCH"
    assert pos["fee_source"] == "crypto_fees_v2"
    # Collateral immediately decremented by 16.25 + 0.25 = 16.50 -> 83.50 (no phantom double-count!)
    assert abs(h._last_known_collateral - 83.50) < 1e-6

    # Simulate split-block settlement: only 15.0 of 25.0 shares mined on Block N, CLOB shows 25.0 matched
    h._verify_entry_finality = MagicMock(return_value=(True, False))
    h._wallet_token_balance = MagicMock(return_value=(15.0, h.ONCHAIN_SOURCE))
    h.executor.get_order_fill_summary = MagicMock(
        return_value={"order_id": "0xENTRY_V2_BATCH", "matched": 25.0, "cash": 16.25, "fee": 0.25}
    )
    posted_early = h._attempt_maker_exit_post(tid, pos)
    assert posted_early is False
    assert "PARTIAL_BATCH_SETTLING" in str(pos.get("exit_blocked_reason", ""))
    assert pos["entry_shares"] == 25.0  # NOT truncated to 15.0!

    # Cash-conservation symmetry: closing the position credits net exit cash back once (idempotently)
    pos["realized_exit_cash"] = 24.00
    pos["realized_exit_fee"] = 0.0
    pos["remaining_shares"] = 0.0
    pos["filled_exit_shares"] = 25.0
    h._close_position(tid, pos, ExecutionStatus.FILLED, "MAKER_SCALP_FILLED_CLOB", won=True)
    assert abs(h._last_known_collateral - 107.50) < 1e-6
    assert pos["_collateral_exit_credited"] is True


# ---------------------------------------------------------------------------
# 3. HTTP 400 Classifier & Contradictory Submission Response Hardening
# ---------------------------------------------------------------------------

def test_is_clob_400_rejection_ignores_400_in_timeouts_and_token_ids():
    class _HttpErr(Exception):
        def __init__(self, status_code, msg, error_message=None):
            super().__init__(msg)
            self.status_code = status_code
            self.error_message = error_message

    # Genuine 400s must still return True
    assert is_clob_400_rejection(_HttpErr(400, "PolyApiException[status_code=400, error_message={'error': 'invalid amounts'}]"))
    assert is_clob_400_rejection("FOK_ORDER_NOT_FILLED_ERROR: couldn't be fully filled")

    # False-positive traps (HTTP 502 / read timeout with "400" in token_id or timeout=4.00) MUST return False!
    assert is_clob_400_rejection(_HttpErr(502, "502 Bad Gateway", error_message="upstream 502 for token_id=91827340019283")) is False
    assert is_clob_400_rejection("ReadTimeout: HTTPSConnectionPool read timed out (read timeout=4.00) token=400999") is False
    assert is_clob_400_rejection(None, {"status": 504, "token_id": "123400567"}) is False


def test_snipe_contradictory_orderid_plus_error_fails_closed(tmp_path):
    ex = PolymarketLiveExecutor(dry_run=False, ledger_path=str(tmp_path / "orders.jsonl"))
    ex.auth_mode = "LIVE"
    ex.is_authenticated = True
    ex.client = MagicMock()
    ex.client.create_order.return_value = MagicMock()
    ex.client.post_order.return_value = {"orderID": "0xAMB_1", "error": "upstream engine timeout", "takingAmount": "20"}
    ex.is_heartbeat_healthy = lambda: True
    ex.get_token_tick_size = lambda _t: 0.01
    ex.get_token_neg_risk = lambda _t, _n=None: False
    ex._fee_cache["0xCOND"] = (0.07, 1.0)
    ex.get_onchain_erc1155_balance = lambda _t: 0.0

    res = ex.execute_snipe_order(
        trade_id="T_CONTRA",
        token_id="123456789012345678901",
        target_token="UP",
        side="BUY",
        notional_usd=15.0,
        target_price=0.75,
        condition_id="0xCOND",
        market_fee_rate=0.07,
        market_fee_exponent=1.0,
        prefetched_book={"asks": [{"price": "0.75", "size": "200"}], "bids": [{"price": "0.74", "size": "200"}]},
        prefetched_pre_balance=0.0,
    )
    assert res.success is False
    assert res.mode == "LIVE_AMBIGUOUS_SUBMISSION"
    assert res.details.get("outcome_unknown") is True
    assert res.order_id == "0xAMB_1"


# ---------------------------------------------------------------------------
# 4. Reverted Fill Protection in `get_order_fill_summary`
# ---------------------------------------------------------------------------

def test_get_order_fill_summary_never_fabricates_cash_on_reverted_fill(tmp_path):
    ex = PolymarketLiveExecutor(dry_run=False, ledger_path=str(tmp_path / "orders.jsonl"))
    ex.auth_mode = "LIVE"
    ex.is_authenticated = True
    ex.client = MagicMock()

    # Stale CLOB order endpoint still reports size_matched=20, while trade settlement FAILED on Polygon
    # and wallet balance is 0.0. Zero-wallet fallback MUST be blocked from certifying settled cash!
    ex.get_order_status = MagicMock(
        return_value={"id": "0xSELL_REV", "status": "MATCHED", "original_size": "20", "size_matched": "20", "price": "0.95", "side": "SELL"}
    )
    reverted_trade = {
        "id": "TR_FAILED_1",
        "taker_order_id": "0xSELL_REV",
        "asset_id": "0xTOK_REV",
        "side": "SELL",
        "size": "20",
        "price": "0.95",
        "status": "FAILED",
    }
    ex.client.get_trades.return_value = [reverted_trade]
    ex.get_onchain_erc1155_balance = MagicMock(return_value=0.0)

    summary = ex.get_order_fill_summary("0xSELL_REV", token_id="0xTOK_REV")
    assert summary is not None
    assert summary["has_reverted_fills"] is True
    assert summary["is_settled"] is False
    assert summary["terminal"] is False
    assert summary["cash_is_estimated"] is True
    ex.get_onchain_erc1155_balance.assert_not_called()


# ---------------------------------------------------------------------------
# 5. D1 Multi-Leg Box Unwind (Pre-Balance Delta, Zero-Settled Defer, Split-Block Clamp, UNK Partner Flip)
# ---------------------------------------------------------------------------

def test_d1_unwind_legged_out_pre_balance_and_split_block_aggregation(tmp_path, monkeypatch):
    ex = PolymarketLiveExecutor(dry_run=False, ledger_path=str(tmp_path / "orders.jsonl"))
    ex.auth_mode = "LIVE"
    ex.is_authenticated = True
    ex.client = MagicMock()
    ex.client.create_order.return_value = MagicMock()
    ex.get_token_tick_size = lambda _t: 0.01
    ex.get_token_neg_risk = lambda _t, _n=None: False
    monkeypatch.setattr(ex_mod, "OrderArgsV2", MagicMock(side_effect=lambda **kw: kw))

    _mono_base = time.monotonic
    _mono_off = [0.0]
    monkeypatch.setattr(time, "monotonic", lambda: _mono_base() + _mono_off[0])
    monkeypatch.setattr(time, "sleep", lambda dt: _mono_off.__setitem__(0, _mono_off[0] + float(dt)))

    def _run_legged_box():
        ex.client.post_order.side_effect = [
            {"orderID": "0xL1_D1", "takingAmount": "20", "makingAmount": "9.40"},
            {"error": "FOK_ORDER_NOT_FILLED_ERROR: couldn't be fully filled"},
        ]
        return ex.execute_atomic_dominance_box(
            box_id="BOX_UW",
            leg_a_token_id="0xTOK_D1_A",
            leg_a_label="BTC 15m UP",
            leg_a_limit_price=0.47,
            leg_b_token_id="0xTOK_D1_B",
            leg_b_label="BTC 1h DOWN",
            leg_b_limit_price=0.48,
            shares=20.0,
            max_box_cost_net=0.995,
            parallel_dispatch=False,
            leg_a_pre_balance=30.0,
            leg_b_pre_balance=0.0,
        )

    # Case A: Wallet already holds pre_balance=30 shares from an earlier trade; new 20-share leg has 0 settled delta ->
    # MUST NOT dump the pre-existing 30 shares and MUST skip doomed inline FAK unwind!
    ex.get_unreserved_conditional_balance = MagicMock(return_value=30.0)
    ex.execute_unwind_order = MagicMock()
    res_zero = _run_legged_box()
    assert res_zero["legged_out"] is True
    assert ex.execute_unwind_order.call_count == 0
    assert res_zero["unwind_result"]["error"] == "DEFERRED_TO_ASYNC_SUPERVISOR_PENDING_SETTLEMENT"
    assert abs(res_zero["residual_unhedged_leg"]["residual_shares"] - 20.0) < 1e-6

    # Case B: Only 12 shares settle (avail=42.0, pre=30.0) and Block N+1 has NOT settled yet on Stage 2 re-check ->
    # Stage 1 unwinds 12.0, Stage 2 MUST NOT sell into pre_balance=30.0, leaving 8.0 residual for supervisor!
    ex.get_unreserved_conditional_balance = MagicMock(return_value=42.0)
    uw_b_calls = []
    ex.execute_unwind_order = lambda tok, size, side="SELL", min_price=0.01, neg_risk=False: (
        uw_b_calls.append(size) or {"success": True, "orderID": "0xUW_PART", "matched_size": size, "taking_amount": round(size * 0.44, 4), "fee_usd": 0.04}
    )
    res_part = _run_legged_box()
    assert uw_b_calls == [12.0]
    assert abs(res_part["residual_unhedged_leg"]["unwound_shares"] - 12.0) < 1e-6
    assert abs(res_part["residual_unhedged_leg"]["residual_shares"] - 8.0) < 1e-6

    # Case C: Split-block settlement (42.0 during 5s poll -> 12.0 settled on Stage 1, then 50.0 on Stage 2 re-check -> +8.0 settled) ->
    # Clamps Stage 1 to 12.0, Stage 2 sweeps newly settled 8.0, and aggregates 12 + 8 = 20 shares & cash!
    poll_count = [0]

    def _bal_split(_tok):
        poll_count[0] += 1
        # During the 5.0s / 0.15s poll loop (~34 polls) return 42.0; on Stage-2 re-check return 50.0
        return 42.0 if poll_count[0] <= 35 else 50.0

    ex.get_unreserved_conditional_balance = _bal_split
    uw_calls = []

    def mock_unwind(tok, size, side="SELL", min_price=0.01, neg_risk=False):
        uw_calls.append((size, min_price))
        if len(uw_calls) == 1:
            return {"success": True, "orderID": "0xUW1", "matched_size": size, "taking_amount": round(size * 0.49, 4), "fee_usd": 0.05}
        return {"success": True, "orderID": "0xUW2", "matched_size": size, "taking_amount": round(size * 0.48, 4), "fee_usd": 0.04}

    ex.execute_unwind_order = mock_unwind
    # Force Stage-2 re-check to see 50.0 right after poll loop finishes by switching after Stage 1 runs
    ex.get_unreserved_conditional_balance = lambda _t: 50.0 if len(uw_calls) >= 1 else 42.0
    res_agg = _run_legged_box()
    uw_agg = res_agg["unwind_result"]
    assert len(uw_calls) == 2
    assert abs(uw_calls[0][0] - 12.0) < 1e-6
    assert abs(uw_calls[1][0] - 8.0) < 1e-6
    assert uw_agg["success"] is True
    assert abs(uw_agg["matched_size"] - 20.0) < 1e-6
    assert abs(uw_agg["taking_amount"] - (12.0 * 0.49 + 8.0 * 0.48)) < 1e-6
    assert abs(uw_agg["fee_usd"] - 0.09) < 1e-6
    assert abs(res_agg["residual_unhedged_leg"]["residual_shares"] - 0.0) < 1e-6


def test_d1_unknown_leg_partner_not_executed_converts_survivor_to_residual_unwind(tmp_path, monkeypatch):
    monkeypatch.setattr(hv_mod, "STATE_FILE", tmp_path / "state.json")
    h = PolymarketLiveHarvester(dry_run=False)
    h.save_state = MagicMock()
    cand = {
        "asset": "BTC",
        "shares": 20.0,
        "expiry_ts": time.time() + 300.0,
        "leg_a_token_id": "0xTA",
        "leg_b_token_id": "0xTB",
        "leg_a_market_id": "M1",
        "leg_b_market_id": "M2",
        "leg_a_limit_price": 0.48,
        "leg_b_limit_price": 0.49,
    }
    res_box = {
        "leg_1_token_id": "0xTA",
        "leg_1_order_id": "0xUNK_A",
        "leg_2_token_id": "0xTB",
        "leg_2_order_id": "0xOK_B",
    }
    h._register_unknown_d1_box_legs("BOX1", cand, res_box, 0.0, 0.0)
    assert "BOX1_UNK_1" in h.active_positions and "BOX1_UNK_2" in h.active_positions
    assert h.active_positions["BOX1_UNK_1"]["box_partner_trade_id"] == "BOX1_UNK_2"
    assert h.active_positions["BOX1_UNK_2"]["box_partner_trade_id"] == "BOX1_UNK_1"

    # Leg 2 arrives on-chain first
    h._classify_entry = MagicMock(return_value={"verdict": "ARRIVED", "balance": 20.0, "source": h.ONCHAIN_SOURCE, "delta": 20.0, "evidence": None})
    assert h._resolve_unknown_entry("BOX1_UNK_2", h.active_positions["BOX1_UNK_2"]) is True
    assert h.active_positions["BOX1_UNK_2"]["is_dominance_box"] is True

    # Leg 1 resolves NOT_EXECUTED -> Leg 2 is now unhedged and MUST immediately flip to UNWIND_RETRY_REQUIRED!
    h._classify_entry = MagicMock(return_value={"verdict": "NOT_EXECUTED", "proof": "TERMINAL_ZERO_FILL_ORDER_STATUS"})
    assert h._resolve_unknown_entry("BOX1_UNK_1", h.active_positions["BOX1_UNK_1"]) is True
    assert "BOX1_UNK_1" not in h.active_positions
    survivor = h.active_positions["BOX1_UNK_2"]
    assert survivor["is_dominance_box"] is False
    assert survivor["is_legged_out_residual"] is True
    assert survivor["exit_order_status"] == "UNWIND_RETRY_REQUIRED"


# ---------------------------------------------------------------------------
# 6. Complete-Set (`C1`) Merge Partial-Fill Abort & Accounting
# ---------------------------------------------------------------------------

def test_complete_set_merge_aborts_on_partial_exit_fill_and_books_clean_merge(tmp_path, monkeypatch):
    monkeypatch.setattr(hv_mod, "STATE_FILE", tmp_path / "state.json")
    monkeypatch.setenv("PM_ENABLE_ONCHAIN_MERGE", "1")
    h = PolymarketLiveHarvester(dry_run=False)
    h.save_state = MagicMock()
    h.executor = MagicMock()
    h.executor.signature_type = 2

    def _mk_leg(tid, partner_tid, tok, oid):
        return {
            "trade_id": tid, "box_id": "C1_BOX", "box_type": "COMPLETE_SET", "box_partner_trade_id": partner_tid,
            "is_dominance_box": True, "condition_id": "0xCOND_C1", "market_id": "M_C1", "token_id": tok,
            "target_token": "UP" if tid.endswith("1") else "DOWN", "entry_price": 0.49, "entry_shares": 20.0,
            "remaining_shares": 20.0, "remaining_exit_shares": 20.0, "filled_exit_shares": 0.0,
            "remaining_cost_basis": 9.80, "notional_usd": 9.80, "fee_usd": 0.05, "entry_fee_cash_usd": 0.05,
            "realized_exit_cash": 0.0, "realized_exit_fee": 0.0, "gross_exit_cash": 0.0,
            "inventory_reconciled": True, "exit_order_id": oid, "exit_order_status": "RESTING", "target_exit_price": 0.99,
        }

    # Case A: Leg 1's resting exit partially filled 5 shares right before cancel -> MUST abort merge & release reservation!
    h.active_positions = {
        "C1_1": _mk_leg("C1_1", "C1_2", "0xYES", "0xEX_1"),
        "C1_2": _mk_leg("C1_2", "C1_1", "0xNO", "0xEX_2"),
    }
    h.executor.cancel_order.return_value = {"is_canceled": True}
    h.executor.get_order_fill_summary.return_value = {
        "order_id": "0xEX_1", "status": "CANCELED", "resting": False, "terminal": True,
        "matched": 5.0, "cash": 4.95, "cash_is_estimated": False, "fee": 0.0,
        "fill_ids": ["F_1"], "trade_ids": ["T_1"], "transactions_hashes": ["0xTX1"],
    }
    asyncio.run(h._maybe_merge_live_complete_sets(time.time()))
    h.executor.attempt_onchain_complete_set_merge.assert_not_called()
    h.executor.release_inventory.assert_called_with(reservation_id="0xEX_1")
    assert h.active_positions["C1_1"]["exit_order_id"] is None
    assert h.active_positions["C1_1"]["exit_order_status"] == "EXIT_RECOVERY_REQUIRED"
    assert abs(h.active_positions["C1_1"]["remaining_shares"] - 15.0) < 1e-6

    # Case B: Clean 0-fill cancel on both legs -> merges 20 pairs on-chain for $20.00 ($10 + $10) & closes consolidated!
    h._c1_merge_attempt_ts.clear()
    h.active_positions = {
        "C1_1": _mk_leg("C1_1", "C1_2", "0xYES", "0xEX_1"),
        "C1_2": _mk_leg("C1_2", "C1_1", "0xNO", "0xEX_2"),
    }
    h.executor.get_order_fill_summary.return_value = {
        "order_id": "0xEX", "status": "CANCELED", "resting": False, "terminal": True, "matched": 0.0, "cash": 0.0
    }
    h.executor.attempt_onchain_complete_set_merge.return_value = ("0xMERGE_TX_OK", 20.0)
    asyncio.run(h._maybe_merge_live_complete_sets(time.time()))
    assert h.active_positions == {}
    assert len(h.closed_positions) == 1
    closed_box = h.closed_positions[0]
    # Total notional = 9.80 + 9.80 = 19.60, entry fees = 0.05 + 0.05 = 0.10, payout = 20.00 -> net_pnl = +0.30
    assert abs(closed_box["payout_usd"] - 20.00) < 1e-6
    assert abs(closed_box["net_pnl_usd"] - 0.30) < 1e-2


# ---------------------------------------------------------------------------
# 7. Maker Exit Replace (Iceberg Tranches, Replica Retry, Unsorted L1 OBI, $0.99 Max Tick, Two-Stage Unknown)
# ---------------------------------------------------------------------------

def test_atomic_replace_iceberg_tranches_and_replica_lag_retry(tmp_path, monkeypatch):
    monkeypatch.setattr(hv_mod, "STATE_FILE", tmp_path / "state.json")
    h = PolymarketLiveHarvester(dry_run=False)
    h.save_state = MagicMock()
    h.executor = MagicMock()

    pos = {
        "trade_id": "T_ICE",
        "market_id": "123",
        "token_id": "123456789012345678901",
        "exit_order_id": "0xT1_OLD",
        "exit_order_size": 12.0,
        "entry_shares": 24.0,
        "remaining_shares": 24.0,
        "remaining_exit_shares": 24.0,
        "filled_exit_shares": 0.0,
        "entry_price": 0.70,
        "target_exit_price": 0.95,
        "exit_order_status": "RESTING",
        "exit_tranches": [
            {"idx": 1, "size": 12.0, "price": 0.95, "status": "POSTED"},
            {"idx": 2, "size": 12.0, "price": 0.98, "status": "PENDING"},
        ],
    }
    h.active_positions["T_ICE"] = pos

    # Simulate CLOB read-replica lag on 1st summary (resting=True), followed by terminal CANCELED on 2nd summary
    h.executor.cancel_order.return_value = {"is_canceled": True}
    h.executor.get_order_fill_summary.side_effect = [
        {"order_id": "0xT1_OLD", "status": "LIVE", "resting": True, "matched": 0.0, "terminal": False},
        {"order_id": "0xT1_OLD", "status": "CANCELED", "resting": False, "matched": 0.0, "terminal": True},
    ]
    h.executor.post_maker_exit_order.return_value = {"success": True, "orderID": "0xT1_NEW", "price": 0.97, "status": "LIVE"}

    # Preserve tranche sizing (collapse_tranches=False): posts only Tranche 1's 12.0 shares, not all 24.0!
    ok = asyncio.run(h._atomic_replace_maker_exit("T_ICE", pos, 0.97, collapse_tranches=False))
    assert ok is True
    h.executor.post_maker_exit_order.assert_called_once_with(
        token_id="123456789012345678901", price=0.97, size=12.0, side="SELL"
    )
    assert pos["exit_tranches"][0]["status"] == "POSTED"
    assert pos["exit_tranches"][0]["price"] == 0.97
    assert pos["exit_tranches"][1]["status"] == "PENDING"

    # Collapse tranches (collapse_tranches=True for OBI_MAKER_STEP_DOWN): posts all 24.0 shares & removes tranches!
    h.executor.get_order_fill_summary.side_effect = [
        {"order_id": "0xT1_NEW", "status": "CANCELED", "resting": False, "matched": 0.0, "terminal": True}
    ]
    h.executor.post_maker_exit_order.reset_mock()
    h.executor.post_maker_exit_order.return_value = {"success": True, "orderID": "0xALL_STEP", "price": 0.93, "status": "LIVE"}
    ok2 = asyncio.run(h._atomic_replace_maker_exit("T_ICE", pos, 0.93, collapse_tranches=True))
    assert ok2 is True
    h.executor.post_maker_exit_order.assert_called_once_with(
        token_id="123456789012345678901", price=0.93, size=24.0, side="SELL"
    )
    assert "exit_tranches" not in pos


def test_post_maker_exit_order_crossed_at_max_tick_99c(tmp_path):
    ex = PolymarketLiveExecutor(dry_run=False, ledger_path=str(tmp_path / "orders.jsonl"))
    ex.auth_mode = "LIVE"
    ex.is_authenticated = True
    ex.client = MagicMock()
    ex.get_unreserved_conditional_balance = MagicMock(return_value=25.0)
    ex.get_token_tick_size = MagicMock(return_value=0.01)
    ex.get_token_neg_risk = MagicMock(return_value=False)

    # First post_order raises post-only crosses book when bid is already $0.99; must NOT fire a doomed 2nd post_order!
    ex.client.post_order.side_effect = Exception("PolyApiException[status_code=400, error_message={'error': 'invalid post-only order: order crosses book'}]")
    ex.get_market_book = MagicMock(return_value={"bids": [{"price": "0.99", "size": "500"}], "asks": []})

    res = ex.post_maker_exit_order(token_id="123456789012345678901", price=0.98, size=20.0, side="SELL")
    assert ex.client.post_order.call_count == 1
    assert res["success"] is False
    assert res["crossed_at_max_tick"] is True
    assert res["best_bid"] == 0.99
    assert ex.reserved_inventory.get("123456789012345678901", 0.0) == 0.0


# ---------------------------------------------------------------------------
# 8. Thread-Safe Reservations, User WS Cache Maker-Leg Attribution & Root Shim
# ---------------------------------------------------------------------------

def test_multithreaded_inventory_reservations_and_prewarm_cache_key(tmp_path, monkeypatch):
    monkeypatch.setattr(ex_mod, "RESERVATIONS_FILE", tmp_path / "reservations.json", raising=False)
    ex = PolymarketLiveExecutor(dry_run=True, ledger_path=str(tmp_path / "orders.jsonl"))
    ex.reservation_records.clear()
    ex._class_res_bucket().clear()
    ex.reserved_inventory.clear()
    tok = "0xTOK_LOCK"
    errors: list[Exception] = []

    def worker(worker_id: int):
        try:
            for i in range(60):
                rid = f"R_{worker_id}_{i}"
                ex.reserve_inventory(tok, 1.5, reservation_id=rid)
                ex.update_reservation(rid, 2.0)
                ex.release_inventory(reservation_id=rid)
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(w,)) for w in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    assert ex.reserved_inventory.get(tok, 0.0) == 0.0
    assert ex.reservation_records == {}

    # Verify 53-bit collision-free salt & (tick_size, neg_risk) cache isolation
    salts = {FastV2OrderSigner._generate_salt() for _ in range(1000)}
    assert len(salts) == 1000
    assert all(1 <= s < (1 << 53) for s in salts)

    cache = PreSignedOrderLadderCache(ttl_seconds=25.0)
    assert cache.store_presigned_order("0xT", price=0.70, shares=24, signed_order="SIGNED_STD", tick_size="0.01", neg_risk=False)
    assert cache.store_presigned_order("0xT", price=0.70, shares=24, signed_order="SIGNED_NEGRISK", tick_size="0.01", neg_risk=True)
    assert cache.get_presigned_order("0xT", price=0.70, shares=24, tick_size="0.001", neg_risk=False) is None
    assert cache.get_presigned_order("0xT", price=0.70, shares=24, tick_size="0.01", neg_risk=False) == "SIGNED_STD"
    assert cache.get_presigned_order("0xT", price=0.70, shares=24, tick_size="0.01", neg_risk=True) == "SIGNED_NEGRISK"


def test_user_ws_cache_maker_leg_delta_monotonic_terminal_and_reconnect_guard():
    ws = PolymarketUserWsCache("key_1", "sec_1", "pass_1")
    ws._connected = True
    ws._connected_since_mono = time.monotonic()
    ws._seeded_since_connect = True

    # Place resting SELL order on our token 0xOUR_YES
    ws.process_ws_payload(
        {"event_type": "order", "id": "0xOUR_OID", "asset_id": "0xOUR_YES", "side": "SELL", "original_size": "20", "size_matched": "0", "status": "LIVE"}
    )

    # Complementary trade event: taker bought 0xOPP_NO (top-level asset_id=0xOPP_NO, side=BUY, size=50),
    # while our maker order 0xOUR_OID sold 12 shares of 0xOUR_YES!
    ws.process_ws_payload(
        {
            "event_type": "trade",
            "id": "TR_COMP_1",
            "status": "CONFIRMED",
            "trader_side": "MAKER",
            "asset_id": "0xOPP_NO",
            "side": "BUY",
            "size": "50",
            "maker_orders": [
                {"order_id": "0xOUR_OID", "asset_id": "0xOUR_YES", "side": "SELL", "matched_amount": "12", "api_key": "key_1"}
            ],
        }
    )
    assert abs(ws._confirmed_token_deltas.get("0xOUR_YES", 0.0) - (-12.0)) < 1e-6
    assert ws._confirmed_token_deltas.get("0xOPP_NO", 0.0) == 0.0

    # Out-of-order UPDATE after CANCELLATION must NEVER resurrect status back to LIVE or shrink size_matched!
    ws.process_ws_payload({"event_type": "order", "id": "0xOUR_OID", "type": "CANCELLATION", "status": "CANCELED", "size_matched": "12"})
    ws.process_ws_payload({"event_type": "order", "id": "0xOUR_OID", "type": "UPDATE", "status": "LIVE", "size_matched": "5"})
    snap = ws.get_order_snapshot("0xOUR_OID")
    assert snap is not None
    assert snap["status"] == "CANCELED"
    assert snap["size_matched"] == 12.0

    # Reconnect without REST seed: pre-disconnect order snapshot MUST return None (fail-closed)
    time.sleep(0.01)
    ws._connected_since_mono = time.monotonic()
    ws._seeded_since_connect = False
    ws._last_rx_mono = time.monotonic()
    assert ws.get_order_snapshot("0xOUR_OID") is None


def test_root_polymarket_live_executor_shim_identity():
    import polymarket_live_executor as root_ex

    assert root_ex is ex_mod
    assert root_ex.PolymarketLiveExecutor is PolymarketLiveExecutor
    assert hasattr(root_ex, "_ThreadLocalClobHttpClient")
    assert hasattr(root_ex, "_UrgentSignPriority")


# ---------------------------------------------------------------------------
# 9. Second-Pass Type 0 Residuals (OF-15 .. OF-18)
# ---------------------------------------------------------------------------

def test_of15_snipe_max_book_buffer_preserves_idea5_plus2c_fallback_price(tmp_path, monkeypatch):
    ex = PolymarketLiveExecutor(dry_run=True, ledger_path=str(tmp_path / "orders.jsonl"))
    book = {"asks": [{"price": "0.65", "size": "200"}], "bids": [{"price": "0.64", "size": "200"}]}

    # Default Shot #1 (max_book_buffer=0.02): target_price=0.69 is clamped to best_px + 0.02 = 0.67
    r_shot1 = ex.execute_snipe_order(
        trade_id="T_SHOT1",
        token_id="123456789012345678901",
        target_token="UP",
        side="BUY",
        notional_usd=15.0,
        target_price=0.69,
        max_price_ceiling=0.78,
        prefetched_book=book,
    )
    assert r_shot1.success is True
    assert abs((r_shot1.details or {}).get("worst_acceptable_price", r_shot1.price) - 0.67) < 1e-6 or r_shot1.price <= 0.67

    # Shot #3 Idea #5 +2c fallback (max_book_buffer=0.04) on live signed path: signs at 0.69 (capped by ceiling)!
    ex_live = PolymarketLiveExecutor(dry_run=False, ledger_path=str(tmp_path / "live_orders.jsonl"))
    ex_live.auth_mode = "LIVE"
    ex_live.is_authenticated = True
    ex_live.client = MagicMock()
    signed_prices = []
    monkeypatch.setattr(ex_mod, "OrderArgsV2", lambda **kw: signed_prices.append(kw["price"]) or kw)
    ex_live.client.create_order.side_effect = lambda args, options=None: args
    ex_live.client.post_order.return_value = {"orderID": "0xFB_OK", "status": "matched", "takingAmount": "20", "makingAmount": "13.80"}
    ex_live.is_heartbeat_healthy = lambda: True
    ex_live.get_token_tick_size = lambda _t: 0.01
    ex_live.get_token_neg_risk = lambda _t, _n=None: False
    ex_live._fee_cache["0xCOND"] = (0.07, 1.0)
    ex_live.get_onchain_erc1155_balance = lambda _t: 20.0

    r_shot3 = asyncio.run(
        ex_live.execute_snipe_order_async(
            trade_id="T_SHOT3",
            token_id="123456789012345678901",
            target_token="UP",
            side="BUY",
            notional_usd=13.80,
            target_price=0.69,
            max_price_ceiling=0.78,
            condition_id="0xCOND",
            market_fee_rate=0.07,
            market_fee_exponent=1.0,
            prefetched_book=book,
            prefetched_pre_balance=0.0,
            max_book_buffer=0.04,
        )
    )
    assert r_shot3.success is True
    assert signed_prices == [0.69]


def test_of16_worker_thread_spawn_fast_confirm_and_unsorted_bids_reprice(tmp_path, monkeypatch):
    monkeypatch.setattr(hv_mod, "STATE_FILE", tmp_path / "state.json")
    h = PolymarketLiveHarvester(dry_run=False)
    h.save_state = MagicMock()
    called_tids = []

    async def _fake_fast_confirm(tid: str):
        called_tids.append(tid)
        await asyncio.sleep(0.01)

    h._fast_confirm_and_post_maker_exit = _fake_fast_confirm

    async def _drive_worker():
        loop = asyncio.get_running_loop()
        h._main_loop = loop
        # Call _spawn_fast_confirm from a worker thread AND duplicate on main loop -> executes exactly once!
        await loop.run_in_executor(None, h._spawn_fast_confirm, "D1_BOX_LEG_1")
        await asyncio.sleep(0.01)
        h._spawn_fast_confirm("D1_BOX_LEG_1")
        await asyncio.sleep(0.05)

    asyncio.run(_drive_worker())
    assert called_tids == ["D1_BOX_LEG_1"]

    # Unsorted REST /book bids during crosses-book repricing MUST select max(price)=0.96, not bids[0]=0.10!
    h.executor = MagicMock()
    h.executor.calculate_balance_epsilon = lambda x: x
    h._verify_entry_finality = MagicMock(return_value=(True, False))
    h._wallet_token_balance = MagicMock(return_value=(20.0, h.ONCHAIN_SOURCE))
    h.executor.get_order_fill_summary = MagicMock(return_value={"matched": 20.0})
    reprice_calls = []
    h.executor.post_maker_exit_order = MagicMock(
        side_effect=[
            {"success": False, "error": "invalid post-only order: crosses book"},
            {"success": True, "orderID": "0xREP_97", "price": 0.97, "status": "LIVE"},
        ]
    )
    h.executor.get_market_book = MagicMock(
        return_value={"bids": [{"price": "0.10", "size": "5"}, {"price": "0.96", "size": "100"}], "asks": [{"price": "0.98", "size": "50"}]}
    )
    pos = {
        "trade_id": "T_UNSORTED",
        "token_id": "123456789012345678901",
        "status": ExecutionStatus.POSITION_CONFIRMED,
        "inventory_reconciled": True,
        "entry_shares": 20.0,
        "remaining_shares": 20.0,
        "remaining_exit_shares": 20.0,
        "filled_exit_shares": 0.0,
        "target_exit_price": 0.95,
        "candle_expiry_ts": time.time() + 600.0,
    }
    h.active_positions["T_UNSORTED"] = pos
    assert h._attempt_maker_exit_post_impl("T_UNSORTED", pos) is True
    for c in h.executor.post_maker_exit_order.call_args_list:
        reprice_calls.append(c.kwargs["price"])
    assert reprice_calls == [0.95, 0.97]


def test_of17_spot_unknown_in_pre_expiry_preserves_terminal_hold_forced(tmp_path, monkeypatch):
    monkeypatch.setattr(hv_mod, "STATE_FILE", tmp_path / "state.json")
    h = PolymarketLiveHarvester(dry_run=False)
    h.save_state = MagicMock()
    h.executor.auth_mode = "LIVE"
    h.executor.is_authenticated = True
    h.get_reference_spot_price = MagicMock(return_value=None)  # spot_valid == False (transient feed drop)
    h.executor.get_market_book_async = AsyncMock(
        return_value={"bids": [{"price": "0.30", "size": "100"}], "asks": [{"price": "0.35", "size": "100"}]}
    )
    h._wallet_token_balance = MagicMock(return_value=(20.0, h.ONCHAIN_SOURCE))
    h.executor.execute_unwind_order = MagicMock()

    now_ts = time.time()
    pos = {
        "trade_id": "T_PIN_HOLD",
        "market_id": "M_PIN",
        "token_id": "123456789012345678901",
        "target_token": "UP",
        "asset": "BTC",
        "status": ExecutionStatus.POSITION_CONFIRMED,
        "inventory_reconciled": True,
        "entry_price": 0.68,
        "entry_shares": 20.0,
        "remaining_shares": 20.0,
        "remaining_exit_shares": 20.0,
        "filled_exit_shares": 0.0,
        "candle_open_spot": 70000.0,
        "entry_spot_ref": 70150.0,
        "candle_sigma": 0.004,
        "candle_expiry_ts": now_ts + 120.0,  # Inside TTE <= 300s pre-expiry window!
        "low_bid_detected_ts": now_ts - 20.0,
        "exit_order_id": None,
        "exit_order_status": "NONE",
    }
    h.active_positions["T_PIN_HOLD"] = pos
    asyncio.run(h.check_resolutions_and_manage_positions())
    # Must NOT trigger spot_crash_triggered unwind inside pre-expiry when spot is unknown!
    assert "low_bid_detected_ts" not in pos
    h.executor.execute_unwind_order.assert_not_called()


def test_of18_cancel_order_respects_not_canceled_payload_fail_closed(tmp_path):
    ex = PolymarketLiveExecutor(dry_run=False, ledger_path=str(tmp_path / "orders.jsonl"))
    ex.auth_mode = "LIVE"
    ex.is_authenticated = True
    ex.client = MagicMock()
    ex.reserve_inventory("0xTOK_NC", 15.0, reservation_id="0xOID_NC")

    # Contradictory/rejected cancel response with order_id in `not_canceled` MUST NOT release inventory!
    ex.client.cancel_orders.return_value = {
        "canceled": ["0xOID_NC"],
        "not_canceled": {"0xOID_NC": "ORDER_ALREADY_MATCHED_OR_LOCKED"},
    }
    ex.get_order_status = MagicMock(return_value={"status": "LIVE", "size_matched": "0", "original_size": "15"})
    res = ex.cancel_order("0xOID_NC")
    assert res["is_canceled"] is False
    assert res["outcome"] == "UNKNOWN"
    assert res["not_canceled_reason"] == "ORDER_ALREADY_MATCHED_OR_LOCKED"
    assert ex.reserved_inventory.get("0xTOK_NC", 0.0) == 15.0


# ---------------------------------------------------------------------------
# 10. Zero-Live-Risk Engineering Sprint Items 1..4
# ---------------------------------------------------------------------------

def test_sprint1_microclip_cascade_4steps_and_100ms_spot_shield():
    from src.polymarket_research.orderflow_wfo_simulators import simulate_microclip_cascade_entry
    import scripts.honest_purged_wfo_optimizer as wfo_mod

    cfg = {
        "min_px": 0.55,
        "max_px": 0.80,
        "fak_buffer": 0.02,
        "cascade_ticket_usd": 16.50,
        "elastic_downsnap_usd": 12.00,
        "fallback_2c_min_z": 1.25,
        "phase3a_ttl_s": 3.5,
        "phase3a_spot_shield_decay": 0.50,
    }
    base_cand = {
        "asset": "BTC", "hz": "15m", "tte": 300.0, "t0": 1_800_000_000.0, "exp_ts": 1_800_000_300.0,
        "mid": "M1", "side": "UP", "ask_t0": 0.65, "bid_t0": 0.64, "spread_t0": 0.01, "slip20_t0": 0.0,
        "l1_ask_usd": 35.0, "cushion_oracle": 0.0012, "cushion_min": 0.0012, "z_oracle": 1.40, "z_cushion": 1.40,
        "shock_ofi": 0.85, "vdiv_centered": 0.0, "cb_move_2s": 2.0, "ask_500ms": 0.66, "ask_1000ms": 0.66,
        "won": True, "path": [(280.0, 0.0014, 0.96, 0.97, 0.95), (200.0, 0.0016, 0.98, 0.99, 0.97)],
    }

    # Step 1: Primary Smart FAK fills at full size_mult=1.0
    s1 = simulate_microclip_cascade_entry(base_cand, cfg)
    assert s1 is not None and s1[4] == "STEP1_SMART_FAK" and s1[3] == 1.0 and abs(s1[0] - 0.66) < 1e-6

    # Step 2: Thin L1 depth ($13.50 < $16.50 full ticket, >= $12.00 elastic rung) -> Elastic Down-Snap!
    c_step2 = {**base_cand, "l1_ask_usd": 13.50}
    s2 = simulate_microclip_cascade_entry(c_step2, cfg)
    assert s2 is not None and s2[4] == "STEP2_ELASTIC_DOWNSNAP" and abs(s2[3] - round(12.0 / 16.5, 4)) < 1e-6

    # Step 3: +500ms ask jumped +3c to 0.68 (> 0.67 Shot #1 limit), z=1.40 >= 1.25 -> Idea #5 +2c FAK retry fills at 0.68!
    c_step3 = {
        **base_cand,
        "micro_clips": [(0.10, 0.0012, 0.64, 0.66), (0.50, 0.0012, 0.66, 0.68), (0.65, 0.0012, 0.66, 0.68)],
    }
    s3 = simulate_microclip_cascade_entry(c_step3, cfg)
    assert s3 is not None and s3[4] == "STEP3_FAK_PLUS_2C_FALLBACK" and abs(s3[0] - 0.68) < 1e-6

    # Step 4a: Taker misses (ask jumped to 0.72 > 0.69 fallback), then ask mean-reverts to 0.65 while spot holds -> 0% fee Maker fill!
    c_step4_ok = {
        **base_cand,
        "micro_clips": [
            (0.50, 0.0012, 0.66, 0.72),
            (0.70, 0.0012, 0.65, 0.70),
            (1.50, 0.0011, 0.64, 0.65),
        ],
    }
    s4_ok = simulate_microclip_cascade_entry(c_step4_ok, cfg)
    assert s4_ok is not None and s4_ok[4] == "STEP4_PHASE3A_MAKER_RESCUE" and s4_ok[1] == 0.0

    # Step 4b: 100ms Adverse-Spot Shield cancels BEFORE toxic passive fill when cushion decays > 50%!
    c_step4_toxic = {
        **base_cand,
        "micro_clips": [
            (0.50, 0.0012, 0.66, 0.72),
            (0.70, 0.0012, 0.65, 0.70),
            (0.90, 0.0003, 0.64, 0.66),  # Cushion collapsed 75% at +900ms -> shield cancels!
            (1.20, -0.0002, 0.60, 0.62),  # Toxic sweep through 0.65 happens AFTER shield cancel
        ],
    }
    assert simulate_microclip_cascade_entry(c_step4_toxic, cfg) is None

    # Purged WFO `simulate_single_trade_ex` integration with `entry_mode="cascade_v4"`
    wfo_cfg = {
        "assets": ("BTC",), "horizons": ("15m",), "min_tte_15m": 60.0, "max_tte_15m": 600.0,
        "min_tte_1h": 120.0, "max_tte_1h": 900.0, "min_px": 0.55, "max_px": 0.80, "max_spread": 0.03,
        "min_l1_usd": 12.0, "min_cushion": 0.0004, "min_z": 0.65, "min_ofi": 0.50,
        "use_venue_veto": True, "use_cl_proxy": True, "entry_mode": "cascade_v4", "fak_buffer": 0.02,
        "exit_policy": "two_tranche_95_98", "ratchet_arm": None, "ratchet_drop": 0.06,
        "salvage_mode": "none", "wrong_side_thresh": 0.0006, "clob_drop_thresh": 0.25,
    }
    sim_ex = wfo_mod.simulate_single_trade_ex(c_step2, wfo_cfg, latency_mode="500ms")
    assert sim_ex is not None and sim_ex[0] > 0.0 and sim_ex[1].startswith("STEP2_ELASTIC_DOWNSNAP:")


def test_sprint2_d1_latency_skew_simulator_and_purged_wfo_calibration():
    from src.polymarket_research.orderflow_wfo_simulators import (
        calibrate_d1_box_wfo,
        simulate_d1_box_with_latency_skew,
    )

    thin_leg_box = {
        "shares": 12.0, "box_cost_net": 0.972,
        "leg_a_limit_price": 0.48, "leg_b_limit_price": 0.47,
        "leg_a_avail_shares": 13.0, "leg_b_avail_shares": 45.0,
        "leg_a_horizon": "15m", "leg_b_horizon": "5m",
        "depletion_a_per_s": 20.0, "depletion_b_per_s": 8.0,
        "bid_drop_a": 0.02, "bid_drop_b": 0.02,
        "base_transit_s": 0.12,
    }
    # Fragile-first detects Leg A depleted to 10.6 < 12 shares at t_0 and aborts cleanly ($0.00 loss)!
    r_frag = simulate_d1_box_with_latency_skew(
        thin_leg_box, {"routing_mode": "fragile_first", "min_depth_mult_gate": 1.0, "max_box_cost_net": 0.99}, delta_t_ms=200.0
    )
    assert r_frag["outcome"] == "LEG1_CLEAN_ABORT" and r_frag["pnl_usd"] == 0.0

    # Parallel 2-leg fills thick Leg B while fragile Leg A misses -> legged-out unwind loss!
    r_par = simulate_d1_box_with_latency_skew(
        thin_leg_box, {"routing_mode": "parallel_2leg", "min_depth_mult_gate": 1.0, "max_box_cost_net": 0.99}, delta_t_ms=200.0
    )
    assert r_par["legged_out"] is True and r_par["pnl_usd"] < 0.0

    wfo_d1 = calibrate_d1_box_wfo()
    assert wfo_d1["grid_configs_evaluated"] >= 50
    assert wfo_d1["sealed_holdout"]["net_pnl_usd"] > wfo_d1["unfiltered_parallel_holdout_baseline"]["net_pnl_usd"]


def test_sprint3_shadow_vs_live_d1_legging_drag_parity_and_graduation_gate(tmp_path, monkeypatch):
    import src.polymarket_research.alpha_124_shadow_daemon as a124
    from src.polymarket_research.orderflow_wfo_simulators import compute_d1_legging_drag_haircut
    from src.polymarket_research.same_oracle_dominance_box import TwapCandleMarketSpec

    # Thin 1.10x box at 0.992 net has +0.8c floor but ~1.2c expected legging drag -> negative adjusted EV!
    thin_drag = compute_d1_legging_drag_haircut(
        shares=15.0, box_cost_net=0.992, avail_a_shares=16.5, avail_b_shares=40.0, px_a=0.49, px_b=0.48
    )
    assert thin_drag["p_leg_miss"] >= 0.20
    assert thin_drag["legging_adjusted_net_ev_per_pair"] < 0.0

    # Thick 3.0x box at 0.968 net retains strongly positive adjusted EV
    thick_drag = compute_d1_legging_drag_haircut(
        shares=15.0, box_cost_net=0.968, avail_a_shares=50.0, avail_b_shares=60.0, px_a=0.47, px_b=0.47
    )
    assert thick_drag["p_leg_miss"] <= 0.02
    assert thick_drag["legging_adjusted_net_ev_per_pair"] > 0.03

    # Live Harvester _grad8 MUST refuse graduation if unadjusted PnL > 0 but legging_adjusted_pnl_t1000_usd <= 0!
    live_dir = tmp_path / "pm"
    live_dir.mkdir()
    monkeypatch.setattr(hv_mod, "DATA_DIR", live_dir)
    monkeypatch.setattr(hv_mod, "STATE_FILE", live_dir / "state.json")
    (live_dir / "alpha124_shadow_state.json").write_text(
        '{"by_sleeve": {"D1_SAME_ORACLE_DOMINANCE_BOX": {"closed": 8, "win_rate_pct": 100.0, '
        '"realized_pnl_t1000_usd": 3.20, "legging_adjusted_pnl_t1000_usd": -0.85}}}',
        encoding="utf-8",
    )
    h = PolymarketLiveHarvester(dry_run=False)
    h._startup_reconciled = True
    cand = {
        "box_id": "D1_TEST_GRAD", "dedupe_key": "D1_BTC_1_2", "asset": "BTC", "box_type": "DOMINANCE",
        "corridor_bps": 6.0, "ts_unix": time.time(), "expiry_ts": time.time() + 180.0, "shares": 12,
        "box_cost_net": 0.965, "max_box_cost_net": 0.980,
        "leg_a_token_id": "1" * 25, "leg_b_token_id": "2" * 25,
        "leg_a_market_id": "101", "leg_b_market_id": "102",
        "leg_a_horizon": "15m", "leg_b_horizon": "5m",
        "leg_a_side": "UP", "leg_b_side": "DOWN",
        "leg_a_strike": 70000.0, "leg_b_strike": 70050.0,
        "leg_a_limit_price": 0.47, "leg_b_limit_price": 0.47,
    }
    res_blk = h.maybe_execute_graduated_d1_box(cand)
    assert res_blk["executed"] is False and res_blk["reason"] == "D1_NOT_YET_8_OF_8_GRADUATED"

    # Also verify Shadow Daemon rejects thin negative-adjusted-EV D1 box entry
    monkeypatch.setattr(a124, "STATE_FILE", tmp_path / "s.json")
    monkeypatch.setattr(a124, "LEDGER_FILE", tmp_path / "l.jsonl")
    d = a124.Alpha124ShadowDaemon(single_scan=True)
    m15 = TwapCandleMarketSpec(
        asset="BTC", horizon="15m", market_id="101", condition_id="0xc1", title="BTC 15m",
        start_iso="2026-10-27T00:00:00Z", end_iso="2026-10-27T00:15:00Z", start_ts=100.0, end_ts=1000.0,
        up_token="t_up15", down_token="t_dn15", fee_rate=0.07, fee_exponent=1.0, neg_risk=False,
        twap_lookback_sec=60, resolution_source="https://data.chain.link",
    )
    m5 = TwapCandleMarketSpec(
        asset="BTC", horizon="5m", market_id="102", condition_id="0xc2", title="BTC 5m",
        start_iso="2026-10-27T00:10:00Z", end_iso="2026-10-27T00:15:00Z", start_ts=700.0, end_ts=1000.0,
        up_token="t_up5", down_token="t_dn5", fee_rate=0.07, fee_exponent=1.0, neg_risk=False,
        twap_lookback_sec=60, resolution_source="https://data.chain.link",
    )
    dom_info = {
        "regime": "CORRIDOR", "k_low": 70000.0, "k_high": 70050.0, "corridor_bps": 7.1,
        "leg_a": {"token_id": "t_up15", "label": "15M_UP", "side": "UP", "horizon": "15m", "market_id": "101", "condition_id": "0xc1", "strike": 70000.0, "fee_rate": 0.07, "fee_exponent": 1.0, "neg_risk": False},
        "leg_b": {"token_id": "t_dn5", "label": "5M_DOWN", "side": "DOWN", "horizon": "5m", "market_id": "102", "condition_id": "0xc2", "strike": 70050.0, "fee_rate": 0.07, "fee_exponent": 1.0, "neg_risk": False},
    }
    # Thin ask size=26 shares on $25 T1000 budget (~25 shares => 1.04x depth) at 0.48 + 0.48 + fees = 0.9949 -> rejected!
    thin_bk_a = {"bids": [{"price": "0.46", "size": "50"}], "asks": [{"price": "0.48", "size": "26"}]}
    thin_bk_b = {"bids": [{"price": "0.46", "size": "50"}], "asks": [{"price": "0.48", "size": "26"}]}
    opened = asyncio.run(d.open_shadow_dominance_box("BTC", m15, m5, dom_info, prefetched_books=(thin_bk_a, thin_bk_b)))
    assert opened is False


def test_sprint4_forensic_auditor_classification_and_wfo_queue_guardrail(tmp_path, monkeypatch):
    import json
    import audit_losing_trades as alt

    monkeypatch.setattr(alt, "DATA_DIR", tmp_path)
    monkeypatch.setattr(alt, "AUDIT_STATE_FILE", tmp_path / "audit_state.json")
    monkeypatch.setattr(alt, "AUDIT_LEDGER_FILE", tmp_path / "audit_ledger.jsonl")
    monkeypatch.setattr(alt, "WFO_HYPOTHESIS_QUEUE_FILE", tmp_path / "wfo_queue.jsonl")

    assert alt.classify_losing_trade_forensics({"status": "ENTRY_OUTCOME_UNKNOWN"})["suggested_classification"] == "PLUMBING_0_PARAM"
    assert alt.classify_losing_trade_forensics({"close_reason": "D1_INLINE_LEGGED_OUT_UNWIND"})["suggested_classification"] == "SEQUENCE_TELEMETRY_REQUIRED"
    assert alt.classify_losing_trade_forensics({"close_reason": "MARKET_RESOLVED"})["suggested_classification"] == "EXPECTED_VARIANCE_NO_CHANGE"

    # Hard Governance Guardrail: attempting to record Type-2 parameter tuning as BUG_FIXED MUST raise ValueError!
    with pytest.raises(ValueError, match="GOVERNANCE_VIOLATION"):
        alt.mark_audited("LIVE_LOSS_1", "BUG_FIXED", "Raise min_cushion from 0.04% to 0.08% to filter chop")
    with pytest.raises(ValueError, match="GOVERNANCE_VIOLATION"):
        alt.mark_audited("LIVE_LOSS_1", "BUG_FIXED", "Some note", classification="PARAM_WFO_REQUIRED")

    # Recording PARAM_WFO_REQUIRED appends structured entry to wfo_hypothesis_queue.jsonl without touching live code
    rec = alt.mark_audited(
        "LIVE_LOSS_1",
        "PARAM_WFO_REQUIRED",
        "Test min_cushion in {0.0004, 0.0006, 0.0008} via Purged WFO",
        wfo_grid="min_cushion=[0.0004,0.0006,0.0008]",
    )
    assert rec["classification"] == "PARAM_WFO_REQUIRED"
    q_lines = [json.loads(x) for x in (tmp_path / "wfo_queue.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(q_lines) == 1
    assert q_lines[0]["trade_id"] == "LIVE_LOSS_1"
    assert q_lines[0]["status"] == "QUEUED_FOR_PURGED_WFO"

