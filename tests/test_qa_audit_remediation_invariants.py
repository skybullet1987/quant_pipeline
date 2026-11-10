#!/usr/bin/env python3
"""
Regression & Edge-Case Suite for QA & Riskless-Profit Audit Remediation (`S-01`..`S-06`, `V-01`..`V-05`, `I-01`..`I-06`, PAA Zero-Trust & KMIA Freeze).
"""

from __future__ import annotations

import asyncio
import json
import threading
import time
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.paa_os.accountant import PAAAccountant
from src.paa_os.budget import BudgetManager
from src.paa_os.permissions import PermissionGate
from src.paa_os.task_db import PAATaskDB
from src.paa_os.zero_trust import _parse_session_c_verdict
from src.polymarket_research.holistic_strategy_governance import (
    DEFAULT_HOLISTIC_CONFIG,
    passes_capital_velocity_hurdle,
)
from src.polymarket_research.polymarket_direct_feeds import (
    LiveMultiSportGame,
    reconcile_multisport_dual_source_boards,
)
from src.polymarket_research.polymarket_live_executor import (
    CancelOrderResult,
    quantize_fok_buy_box_legs,
)
from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester
from src.polymarket_research.riskless_frontier_v2_engine import (
    EsportsBo3Spec,
    evaluate_api1_esports_bo3_opportunities,
)
from src.polymarket_research.riskless_protocol_v2_expansion import (
    eval_sll_live_book_poll,
    execute_guarded_complement_merge_impl,
)
from src.polymarket_research.stage_c_zero_loss_velocity import (
    _is_standalone_recyclable_carry,
    execute_clinched_dead_leg_split_arb,
)


def test_s01_split_arb_delivery_timeout_merges_or_tracks_par_value() -> None:
    """[S-01] If ERC-1155 delivery lags past timeout after split, merge back or track par-value winning shares (never orphan!)."""
    now = 1_765_000_000.0
    ex = MagicMock()
    ex.get_conditional_balance.return_value = 0.0
    ex.attempt_onchain_complete_set_merge.return_value = None  # Simulate merge unavailable due to RPC lag

    harv = types.SimpleNamespace(
        dry_run=False,
        executor=ex,
        active_positions={},
        _last_known_collateral=50.0,
        save_state=MagicMock(),
    )
    cand = {
        "box_id": "SP_TEST_1",
        "condition_id": "0x" + "ab" * 32,
        "leg_a_market_id": "99001",
        "leg_a_token_id": "tok_win_yes",
        "leg_a_opp_token_id": "tok_dead_no",
        "leg_a_side": "YES",
        "leg_a_neg_risk": False,
        "expiry_ts": now + 3600.0,
        "sleeve_source": "W_PRUNE1_DEAD_NO_BOND",
        "asset": "WEATHER",
    }
    plan = {
        "condition_id": "0x" + "ab" * 32,
        "winner_token_id": "tok_win_yes",
        "dead_token_id": "tok_dead_no",
        "shares": 10,
        "min_dead_sell_px": 0.015,
        "neg_risk": False,
    }
    with patch(
        "src.polymarket_research.riskless_machine_gun_engine.attempt_onchain_split_position",
        return_value={"success": True, "tx_hash": "0xsplit123", "shares": 10.0},
    ), patch(
        "src.polymarket_research.riskless_machine_gun_engine.wait_for_erc1155_delivery",
        return_value=False,
    ):
        res = execute_clinched_dead_leg_split_arb(harv, cand, plan, now_ts=now)

    assert res["executed"] is True
    assert res["split_tx_hash"] == "0xsplit123"
    assert len(harv.active_positions) == 1
    tracked = next(iter(harv.active_positions.values()))
    assert tracked["entry_shares"] == 10.0
    assert tracked["notional_usd"] == 10.0
    assert tracked["unmerged_dead_opp_shares"] == 10.0
    assert harv._last_known_collateral == pytest.approx(40.0)


def test_s02_user_ws_fast_cancel_rejects_stale_live_status() -> None:
    """[S-02] Stale User WS snapshot with status=='LIVE' MUST NOT short-circuit REST get_order_fill_summary."""
    h = PolymarketLiveHarvester.__new__(PolymarketLiveHarvester)
    h.dry_run = False
    summary_calls = []

    class _StaleLiveWsExec:
        client = object()
        _user_ws_cache = types.SimpleNamespace(
            is_healthy=lambda: True,
            get_order_snapshot=lambda oid, max_age_sec=10.0: {
                "order_id": oid,
                "size_matched": 0.0,
                "status": "LIVE",  # Pre-cancel placement event!
            },
        )

        def cancel_order(self, oid: str, token_id: str = "", pre_token_balance=None):
            return {"is_canceled": True, "matched": 0.0, "outcome": "CANCELED"}

        def get_order_fill_summary(self, oid: str, token_id: str):
            summary_calls.append(oid)
            return {"order_id": oid, "matched": 10.0, "avg_price": 0.990, "cash": 9.90, "fee": 0.0, "terminal": True, "resting": False}

    h.executor = _StaleLiveWsExec()
    _, summ, matched_sh, _ = asyncio.run(
        h._reconcile_maker_entry_fill("OID_RACE_LIVE", "901" * 9, False, 10.0, 0.990, 0.0)
    )
    assert len(summary_calls) == 1
    assert (summ or {}).get("source") != "USER_WS_FAST_CANCEL"
    assert matched_sh == pytest.approx(10.0)


def test_s03_guarded_complement_merge_tracks_unmerged_opp_shares_and_cancel_dataclass() -> None:
    """[S-03] Unwraps CancelOrderResult and records unmerged opp_tok shares in active_positions on merge failure."""
    now = 1_765_000_100.0
    harv = PolymarketLiveHarvester.__new__(PolymarketLiveHarvester)
    harv.dry_run = False
    harv.active_positions = {}
    harv._last_known_collateral = 45.0
    harv.save_state = MagicMock()
    harv._close_position = MagicMock()

    ex = MagicMock()
    ex.buy_complement_leg_fak.return_value = {"success": True, "matched_shares": 25.0, "cost_usd": 0.25}
    ex.cancel_order.return_value = CancelOrderResult(order_id="oid_tp", is_canceled=True, outcome="CANCELED")
    ex.get_order_fill_summary.return_value = None
    ex.attempt_onchain_complete_set_merge.return_value = None  # Merge fails transiently
    harv.executor = ex

    pos = {
        "trade_id": "TID_MAIN",
        "market_id": "5551",
        "condition_id": "0x" + "cc" * 32,
        "token_id": "tok_up",
        "target_token": "UP",
        "exit_order_id": "oid_tp",
        "remaining_shares": 25.0,
        "target_exit_price": 0.98,
        "neg_risk": False,
        "candle_expiry_ts": now + 600.0,
    }
    harv.active_positions["TID_MAIN"] = pos
    plan = {"opp_ask": 0.01, "req_opp_shares": 25.0, "tick_size": "0.001", "total_opp_cost_usd": 0.25}
    ok = asyncio.run(execute_guarded_complement_merge_impl(harv, "TID_MAIN", pos, "tok_dn", plan, now, types.SimpleNamespace(FILLED="FILLED", SETTLED="SETTLED")))
    assert ok is False
    resid_keys = [k for k in harv.active_positions if k.startswith("COMP_RESID_")]
    assert len(resid_keys) == 1
    assert harv.active_positions[resid_keys[0]]["remaining_shares"] == 25.0
    assert pos["is_dominance_box"] is True
    assert pos["_comp_merge_pending_resid"] == resid_keys[0]
    ok_retry = asyncio.run(execute_guarded_complement_merge_impl(harv, "TID_MAIN", pos, "tok_dn", plan, now + 5.0, types.SimpleNamespace(FILLED="FILLED", SETTLED="SETTLED")))
    assert ok_retry is False
    assert ex.buy_complement_leg_fak.call_count == 1


def test_s04_doubleheader_proximity_and_strict_esports_quote_veto() -> None:
    """[S-04] Doubleheader Game 1 (>3h apart) cannot mark live Game 2 completed, and quote-inferred BO3 winners are blocked by default."""
    now = 1_765_000_000.0
    espn_g2_live = [
        LiveMultiSportGame(
            sport="MLB",
            game_id="espn_g2",
            start_ts=now - 1800.0,
            state="in",
            completed=False,
            is_halftime=False,
            period=3,
            clock_sec=0.0,
            home_name="New York Mets",
            away_name="Atlanta Braves",
            home_score=1,
            away_score=1,
        )
    ]
    mlb_g1_final = [
        LiveMultiSportGame(
            sport="MLB",
            game_id="mlb_g1",
            start_ts=now - 18_000.0,  # 5 hours earlier (Game 1 Final!)
            state="post",
            completed=True,
            is_halftime=False,
            period=9,
            clock_sec=0.0,
            home_name="New York Mets",
            away_name="Atlanta Braves",
            home_score=5,
            away_score=2,
        )
    ]
    merged_dh = reconcile_multisport_dual_source_boards("MLB", espn_g2_live, mlb_g1_final)
    assert merged_dh[0].completed is False

    # Same game (<3h start_ts difference) when official MLB scorer marks Final in 9th inning upgrades cleanly
    espn_g1_late = [
        LiveMultiSportGame(
            sport="MLB",
            game_id="espn_g1",
            start_ts=now - 17_950.0,
            state="in",
            completed=False,
            is_halftime=False,
            period=9,
            clock_sec=0.0,
            home_name="New York Mets",
            away_name="Atlanta Braves",
            home_score=5,
            away_score=2,
        )
    ]
    merged_ok = reconcile_multisport_dual_source_boards("MLB", espn_g1_late, mlb_g1_final)
    assert merged_ok[0].completed is True

    # Quote-inferred Map 1 winner (`m1b bid == 0.995`, no official score) blocked when allow_quote_inferred=False
    spec = EsportsBo3Spec(
        event_id="esp_1",
        slug="cs2-test",
        title="Team A vs Team B (BO3)",
        end_ts=now + 3600.0,
        team_a="Team A",
        team_b="Team B",
        ml_market_id="1",
        ml_condition_id="0x1",
        ml_a_token="mla",
        ml_b_token="mlb",
        ml_fee_rate=0.0,
        ml_fee_exp=1.0,
        hc_market_id="2",
        hc_condition_id="0x2",
        hc_fav_is_a=True,
        hc_minus_token="hcm",
        hc_plus_token="hcp",
        hc_fee_rate=0.0,
        hc_fee_exp=1.0,
        map1_a_token="m1a",
        map1_b_token="m1b",
        map2_a_token="m2a",
        map2_b_token="m2b",
        ou25_over_token="ov",
        ou25_under_token="un",
        ou25_market_id="3",
        ou25_condition_id="0x3",
        ou25_fee_rate=0.0,
    )
    bks = {
        "m1a": {"bids": [], "asks": [{"price": "0.01", "size": "200"}]},
        "m1b": {"bids": [{"price": "0.995", "size": "200"}], "asks": []},
        "hcp": {"bids": [{"price": "0.94", "size": "200"}], "asks": [{"price": "0.95", "size": "200"}]},
        "mla": {"bids": [{"price": "0.50", "size": "200"}], "asks": [{"price": "0.55", "size": "200"}]},
        "mlb": {"bids": [], "asks": [{"price": "0.48", "size": "200"}]},
    }
    res_strict = evaluate_api1_esports_bo3_opportunities(spec, bks, {"hcp": 0.95, "mla": 0.55}, allow_quote_inferred=False)
    assert res_strict["single_leg_locks"] == []
    res_perm = evaluate_api1_esports_bo3_opportunities(spec, bks, {"hcp": 0.95, "mla": 0.55}, allow_quote_inferred=True)
    assert len(res_perm["single_leg_locks"]) >= 1


def test_s05_exchange_v2_cash_fee_box_quantization_cap() -> None:
    """[S-05] quantize_fok_buy_box_legs enforces Exchange V2 cash-fee total cost <= max_box_cost_net and <= max_budget_usd."""
    h_leg = 0.07 * 0.51  # ~0.0357 fee fraction at px=0.49
    bad_v2 = quantize_fok_buy_box_legs(
        20.0,
        0.49,
        0.49,
        h_a=h_leg,
        h_b=h_leg,
        max_box_cost_net=0.990,
        max_budget_usd=50.0,
    )
    assert bad_v2 is None

    h_leg_ok = 0.07 * 0.53  # ~0.0371 fee fraction at px=0.47
    good_v2 = quantize_fok_buy_box_legs(
        25.0,
        0.47,
        0.47,
        h_a=h_leg_ok,
        h_b=h_leg_ok,
        max_box_cost_net=0.990,
        max_budget_usd=20.0,
    )
    assert good_v2 is not None
    assert good_v2["v2_box_cost_net"] <= 0.990
    assert good_v2["v2_total_cash_usd"] <= 20.0 + 1e-6


def test_v01_v04_kmia_freeze_protection_and_uma_2h_velocity() -> None:
    """[V-01..V-04 & KMIA] Stale dust bid on winning book does not trigger false ADVERSE; KMIA disputed locks stay 100% untouched."""
    now = time.time()
    cand = {"sleeve_source": "BOND1_UMA_RESOLUTION_CARRY", "p_model": 1.0, "uma_liveness_verified": True}
    act, _, _, _ = eval_sll_live_book_poll(
        {"bids": [{"price": "0.001", "size": "100"}], "asks": [{"price": "0.999", "size": "100"}]},
        {"bids": [{"price": "0.990", "size": "20"}, {"price": "0.05", "size": "5"}], "asks": [{"price": "0.994", "size": "50"}]},
        cand,
        0.990,
        0.80,
        0.994,
        0.025,
        0.001,
        True,
        False,
        0,
        250.0,
        90.0,
        now + 7200.0,
        None,
        collat_usd=100.0,
    )
    assert act == "OK"

    ok_uma, _ = passes_capital_velocity_hurdle(
        collat_usd=97.0,
        rem_tte_sec=48 * 3600.0,
        box_cost_net=0.992,
        box_type="SINGLE_LEG_MAKER_LOCK",
        sleeve_src="BOND1_UMA_RESOLUTION_CARRY",
        fast_recycle_eligible=True,
    )
    assert ok_uma is True

    kmia_pos = {
        "trade_id": "WS_SNIPE_Miami_KMIA_242960",
        "asset": "KMIA",
        "sleeve": "W_PRUNE1_DEAD_NO_BOND",
        "box_type": "SINGLE_LEG_LOCK",
        "is_single_leg_lock": True,
        "hold_to_maturity_lock": True,
        "inventory_reconciled": True,
        "umaResolutionStatus": "disputed",
        "token_id": "tok_kmia",
        "remaining_shares": 15.0,
        "entry_shares": 15.0,
        "notional_usd": 14.85,
        "fee_rate_applied": 0.0,
        "candle_expiry_ts": now - 86400.0,
    }
    assert _is_standalone_recyclable_carry(kmia_pos) is False

    h = PolymarketLiveHarvester.__new__(PolymarketLiveHarvester)
    h.dry_run = False
    h.executor = MagicMock()
    assert asyncio.run(h._maybe_recycle_disputed_htm_lock("WS_SNIPE_Miami_KMIA_242960", kmia_pos, now)) is False
    h.executor.get_market_book_async.assert_not_called()


def test_paa_session_c_fail_closed_json_and_permission_gate_ceilings(tmp_path: Path) -> None:
    """Session C fails closed on malformed/string/prose responses, and PermissionGate blocks raised box cost ceilings."""
    gate = PermissionGate(approvals_dir=tmp_path / "approvals")
    base_cfg = json.loads(json.dumps(DEFAULT_HOLISTIC_CONFIG))
    base_cfg["riskless_boxes"]["enable_s2_twap_lock_live"] = False
    cand_bad = json.loads(json.dumps(base_cfg))
    cand_bad["riskless_boxes"]["d1_max_box_cost_net"] = 0.995
    cand_bad["riskless_boxes"]["enable_s2_twap_lock_live"] = True
    ok_env, viols = gate.inspect_config_envelope(base_cfg, cand_bad)
    assert ok_env is False
    assert any("d1_max_box_cost_net" in v for v in viols)
    assert any("enable_s2_twap_lock_live" in v for v in viols)

    db = PAATaskDB(tmp_path / "paa_test.sqlite3")
    budget = BudgetManager(db)
    acc = PAAAccountant(db=db, budget=budget, data_dir=tmp_path)
    ok_acc, _, anom = acc.verify_accounting_integrity(
        {"free_cash_pusd": 52.10, "free_cash_pusd_only": 46.10, "open_positions": []},
        state_override={"live_bankroll": 46.10, "active_positions": {}, "pending_entry_intents": {}},
    )
    assert ok_acc is True
    assert anom == []

    assert _parse_session_c_verdict("") is False
    assert _parse_session_c_verdict("Looks great, approved!") is False
    assert _parse_session_c_verdict('{"approved":false,"findings":"risk"}') is False
    assert _parse_session_c_verdict('{"approved":"true","findings":"string_not_bool"}') is False
    assert _parse_session_c_verdict('{"approved": true, "findings": "protected_file touched"}') is False
    assert _parse_session_c_verdict('```json\n{"approved": true, "findings": "clean"}\n```') is True


def test_s03_live_executor_cancel_first_erc1155_poll_and_comp_resid_retry() -> None:
    """[S-03] Real non-mock live executor cancels TP BEFORE buying complement, polls ERC-1155 without ImportError/TypeError, tracks <5sh FAK, and retries COMP_RESID_*."""
    from src.polymarket_research.riskless_protocol_v2_expansion import maybe_merge_live_complete_sets_impl

    now = 1_765_000_500.0
    call_order: list[str] = []
    fak_sh_box = [3.0]
    merge_ok_box = [False]

    class _RealLiveExec:
        client = object()

        def cancel_order(self, oid: str, token_id: str = "", pre_token_balance=None):
            call_order.append(f"cancel:{oid}")
            return CancelOrderResult(order_id=oid, is_canceled=True, outcome="CANCELED")

        def get_order_fill_summary(self, oid: str, token_id: str):
            return {"order_id": oid, "matched": 0.0, "terminal": True}

        def release_inventory(self, **kwargs):
            return None

        def get_conditional_balance(self, tok: str) -> float:
            return 25.0

        def buy_complement_leg_fak(self, *args, **kwargs):
            call_order.append("buy_fak")
            return {"success": True, "matched_shares": fak_sh_box[0], "cost_usd": round(0.01 * fak_sh_box[0], 4)}

        def attempt_onchain_complete_set_merge(self, condition_id: str, min_pairs: float = 0.0, max_pairs: float = 0.0, neg_risk: bool = False):
            call_order.append(f"merge:{min_pairs}")
            if not merge_ok_box[0]:
                return None
            return ("0xmerged_comp_resid", float(min_pairs))

        def get_collateral_balance(self) -> float:
            return 69.75

    harv = PolymarketLiveHarvester.__new__(PolymarketLiveHarvester)
    harv.dry_run = False
    harv.ONCHAIN_SOURCE = "ONCHAIN"
    harv.executor = _RealLiveExec()
    harv._wallet_token_balance = lambda tok: (25.0, "CLOB_BALANCE_API")
    harv.active_positions = {
        "TID_LIVE_S03": {
            "trade_id": "TID_LIVE_S03",
            "market_id": "7701",
            "condition_id": "0x" + "dd" * 32,
            "token_id": "tok_up_s03",
            "target_token": "UP",
            "exit_order_id": "oid_tp_live",
            "entry_shares": 25.0,
            "remaining_shares": 25.0,
            "filled_exit_shares": 0.0,
            "notional_usd": 24.50,
            "inventory_reconciled": True,
            "target_exit_price": 0.98,
            "neg_risk": False,
            "candle_expiry_ts": now + 600.0,
        }
    }
    harv._last_known_collateral = 45.0
    harv.save_state = MagicMock()
    harv._close_position = MagicMock(side_effect=lambda tid, *a, **kw: harv.active_positions.pop(tid, None))

    wait_calls: list[tuple] = []

    def _spy_wait(ex, tok_ids, min_sh, *, timeout_sec=8.0, poll_sec=0.35):
        wait_calls.append((tuple(tok_ids), float(min_sh), float(timeout_sec), float(poll_sec)))
        return True

    plan = {"opp_ask": 0.01, "req_opp_shares": 25.0, "tick_size": "0.001", "total_opp_cost_usd": 0.25}
    # 1) <5.0-share partial FAK fill cancels TP BEFORE buy_fak and records COMP_RESID_* (never silently dropped!)
    ok_sub5 = asyncio.run(
        execute_guarded_complement_merge_impl(
            harv,
            "TID_LIVE_S03",
            harv.active_positions["TID_LIVE_S03"],
            "tok_dn_s03",
            plan,
            now,
            types.SimpleNamespace(FILLED="FILLED", SETTLED="SETTLED"),
        )
    )
    assert ok_sub5 is False
    assert call_order[:2] == ["cancel:oid_tp_live", "buy_fak"]
    resid_ids = [k for k in harv.active_positions if k.startswith("COMP_RESID_")]
    assert len(resid_ids) == 1
    assert harv.active_positions[resid_ids[0]]["remaining_shares"] == pytest.approx(3.0)

    # 2) Full 25.0-share complement leg exercises wait_for_erc1155_delivery (6.0s, 0.30s) without ImportError/TypeError!
    harv.active_positions.pop(resid_ids[0], None)
    harv.active_positions["TID_LIVE_S03"].pop("_comp_merge_pending_resid", None)
    harv.active_positions["TID_LIVE_S03"]["exit_order_id"] = "oid_tp_live_2"
    fak_sh_box[0] = 25.0
    with patch("src.polymarket_research.riskless_machine_gun_engine.wait_for_erc1155_delivery", side_effect=_spy_wait):
        ok_25 = asyncio.run(
            execute_guarded_complement_merge_impl(
                harv,
                "TID_LIVE_S03",
                harv.active_positions["TID_LIVE_S03"],
                "tok_dn_s03",
                plan,
                now + 2.0,
                types.SimpleNamespace(FILLED="FILLED", SETTLED="SETTLED"),
            )
        )
    assert ok_25 is False
    assert len(wait_calls) == 1
    assert wait_calls[0][2:] == (6.0, 0.30)

    # 3) maybe_merge_live_complete_sets_impl retries and merges the COMP_RESID_* pair on-chain!
    merge_ok_box[0] = True
    harv._last_complete_set_merge_ts = 0.0
    harv._onchain_merges_completed = 0
    asyncio.run(
        maybe_merge_live_complete_sets_impl(harv, now + 30.0, types.SimpleNamespace(FILLED="FILLED", SETTLED="SETTLED"), MagicMock())
    )
    assert harv.active_positions == {}


def test_s05_maker_anchor_hedge_blocks_lot_step_round_up_loss() -> None:
    """[S-05] execute_maker_anchor_hedge_or_unwind vetoes 5.0->6.0 lot-step round-up + V2 cash-fee breach ($5.202 > $5.00)."""
    from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor

    ex = PolymarketLiveExecutor.__new__(PolymarketLiveExecutor)
    ex.dry_run = False
    ex.auth_mode = "DRY_RUN"
    ex.client = MagicMock()
    ex.get_token_neg_risk = lambda tok, fallback=None: False
    ex.quantize_order_price = lambda px, tok, rounding=None: round(float(px), 2)
    ex.execute_unwind_order = MagicMock(return_value={"success": True, "matched_size": 5.0, "outcome_unknown": False})
    res = ex.execute_maker_anchor_hedge_or_unwind(
        box_id="B_LOT_ROUNDUP",
        anchor_token_id="tok_anc",
        anchor_label="YES",
        anchor_price=0.65,
        anchor_matched_shares=5.0,
        anchor_order_id="oid_anc_1",
        hedge_token_id="tok_hdg",
        hedge_label="NO",
        hedge_limit_price=0.31,
        max_box_cost_net=0.985,
        hedge_fee_rate=0.072,
        hedge_fee_exponent=1.0,
    )
    assert res["success"] is False
    assert "MAKER_ANCHOR_PRE_HEDGE_VETO" in res["error"]
    ex.client.post_order.assert_not_called()
    ex.execute_unwind_order.assert_called_once()


def test_s01_split_arb_unwind_exception_and_dead_opp_merge_retry_and_event_cap() -> None:
    """[S-01] Post-split unwind timeout preserves provisional CLINCH_SPLIT_*, maybe_merge_live_complete_sets_impl merges unmerged_dead_opp_shares, and event key maps KMIA."""
    from src.polymarket_research.riskless_protocol_v2_expansion import (
        extract_sll_event_group_key,
        maybe_merge_live_complete_sets_impl,
    )

    now = 1_765_001_000.0
    assert extract_sll_event_group_key(
        {"event_id": "CLINCH_SPLIT_Miami_KMIA_1", "asset": "Miami_KMIA", "candle_expiry_ts": 1_794_113_999.0}
    ).startswith("EVTWX:KMIA:")

    ex = MagicMock()
    ex.signature_type = 1
    ex.get_conditional_balance.return_value = 0.0
    ex.execute_unwind_order.side_effect = TimeoutError("CLOB HTTP read timeout")
    ex.attempt_onchain_complete_set_merge.return_value = ("0xshould_not_race_ambiguous_sell", 10.0)
    ex.get_collateral_balance.return_value = 40.0

    harv = types.SimpleNamespace(
        dry_run=False,
        executor=ex,
        active_positions={},
        _last_known_collateral=50.0,
        _last_complete_set_merge_ts=0.0,
        _onchain_merges_completed=0,
        save_state=MagicMock(),
        _close_position=MagicMock(),
    )
    cand = {
        "box_id": "SP_TIMEOUT_1",
        "condition_id": "0x" + "ef" * 32,
        "leg_a_market_id": "99002",
        "leg_a_token_id": "tok_win_t",
        "leg_a_opp_token_id": "tok_dead_t",
        "leg_a_side": "YES",
        "leg_a_neg_risk": False,
        "expiry_ts": now + 3600.0,
        "sleeve_source": "W_PRUNE1_DEAD_NO_BOND",
        "asset": "WEATHER",
    }
    plan = {
        "condition_id": "0x" + "ef" * 32,
        "winner_token_id": "tok_win_t",
        "dead_token_id": "tok_dead_t",
        "shares": 10,
        "min_dead_sell_px": 0.02,
        "neg_risk": False,
    }
    with patch(
        "src.polymarket_research.riskless_machine_gun_engine.attempt_onchain_split_position",
        return_value={"success": True, "tx_hash": "0xsplit_to", "shares": 10.0},
    ), patch(
        "src.polymarket_research.riskless_machine_gun_engine.wait_for_erc1155_delivery",
        return_value=True,
    ):
        res = execute_clinched_dead_leg_split_arb(harv, cand, plan, now_ts=now)

    # Because execute_unwind_order timed out (ambiguous outcome), merge MUST NOT race the CLOB sell, and provisional position MUST exist!
    assert res["executed"] is True
    ex.attempt_onchain_complete_set_merge.assert_not_called()
    assert len(harv.active_positions) == 1
    tid_sp, pos_sp = next(iter(harv.active_positions.items()))
    assert pos_sp["dead_leg_unwind_outcome_unknown"] is True

    # Once dead_leg_unwind_outcome_unknown is cleared (unfilled confirmed), maybe_merge_live_complete_sets_impl merges unmerged_dead_opp_shares!
    pos_sp["dead_leg_unwind_outcome_unknown"] = False
    pos_sp["unmerged_dead_opp_shares"] = 10.0
    ex.attempt_onchain_complete_set_merge.return_value = ("0xmerged_dead_opp", 10.0)
    ex.get_collateral_balance.return_value = 50.0
    harv._close_position.side_effect = lambda t, *a, **kw: harv.active_positions.pop(t, None)
    asyncio.run(
        maybe_merge_live_complete_sets_impl(harv, now + 30.0, types.SimpleNamespace(FILLED="FILLED", SETTLED="SETTLED"), MagicMock())
    )
    assert tid_sp not in harv.active_positions
    assert harv._last_known_collateral == pytest.approx(50.0)


def test_v04_fractional_taker_share_carry_recycling_proportional_cost() -> None:
    """[V-04] Fractional Taker carry (10.6 sh @ $0.990) retires proportional 10/10.6 cost and recycles integer 10-sh lot."""
    from src.polymarket_research.stage_c_zero_loss_velocity import (
        find_recyclable_zero_loss_open_carries,
        recycle_open_zero_loss_carry_for_fast_arb,
    )

    now = 1_765_002_000.0
    ex = MagicMock()
    ex.get_market_book.return_value = {"bids": [{"price": "0.992", "size": "50"}], "asks": [{"price": "0.995", "size": "50"}]}
    ex.execute_unwind_order.return_value = {
        "success": True,
        "matched_size": 10.0,
        "taking_amount": 9.92,
        "fee_usd": 0.0,
        "orderID": "OID_FRAC_UW",
        "outcome_unknown": False,
    }
    harv = types.SimpleNamespace(
        dry_run=False,
        executor=ex,
        active_positions={
            "SLL_FRAC_1": {
                "trade_id": "SLL_FRAC_1",
                "asset": "MACRO",
                "sleeve": "BOND1_UMA_RESOLUTION_CARRY",
                "box_type": "SINGLE_LEG_LOCK",
                "is_single_leg_lock": True,
                "hold_to_maturity_lock": True,
                "inventory_reconciled": True,
                "token_id": "tok_frac_b1",
                "entry_shares": 10.6,
                "remaining_shares": 10.6,
                "entry_price": 0.990,
                "notional_usd": 10.494,
                "fee_rate_applied": 0.0,
                "candle_expiry_ts": now + 18 * 3600.0,
            }
        },
        _last_known_collateral=5.0,
        save_state=MagicMock(),
        _close_position=MagicMock(),
    )
    cands = find_recyclable_zero_loss_open_carries(
        harv,
        challenger_net_cost=0.975,
        challenger_rem_tte_sec=900.0,
        now_ts=now,
    )
    assert len(cands) == 1
    assert cands[0]["shares"] == 10
    assert cands[0]["est_net_pnl_usd"] == pytest.approx(0.01, abs=1e-4)

    rec = recycle_open_zero_loss_carry_for_fast_arb(
        harv,
        needed_cash_gap_usd=9.5,
        challenger_net_cost=0.975,
        challenger_rem_tte_sec=900.0,
        now_ts=now,
    )
    assert rec["recycled_count"] == 1
    rem_pos = harv.active_positions["SLL_FRAC_1"]
    assert rem_pos["remaining_shares"] == pytest.approx(0.6)
    assert rem_pos["remaining_cost_basis"] == pytest.approx(0.594, abs=1e-3)


def test_s06_pending_negrisk_convert_sweep_and_sub5_fak_bundle_tracking() -> None:
    """[S-06] maybe_merge_live_complete_sets_impl retries unconverted HOLD_NO_* baskets, and _execute_multi_leg_bundle_sync tracks <5sh partial FAK fills."""
    from src.polymarket_research.riskless_protocol_v2_expansion import (
        _execute_multi_leg_bundle_sync,
        maybe_merge_live_complete_sets_impl,
    )

    now = 1_765_003_000.0
    ex_nr = MagicMock()
    ex_nr.signature_type = 1
    ex_nr.attempt_onchain_complete_set_merge.return_value = None
    ex_nr.attempt_negrisk_convert_positions.return_value = {"success": True, "tx_hash": "0xconv_ok"}
    ex_nr.get_collateral_balance.return_value = 60.0

    def _rec_fill(pos, oid, sh, cash, fee, cash_is_estimated=False):
        pos["remaining_shares"] = max(0.0, float(pos.get("remaining_shares", 0.0)) - float(sh))
        pos["realized_exit_cash"] = float(pos.get("realized_exit_cash", 0.0)) + float(cash)

    harv_nr = types.SimpleNamespace(
        dry_run=False,
        executor=ex_nr,
        active_positions={
            "NR_CONV_1_HOLD_NO_0": {
                "trade_id": "NR_CONV_1_HOLD_NO_0",
                "box_id": "NR_CONV_1",
                "box_expected_legs": 2,
                "box_type": "NEGRISK_CONVERT_ARB_UNCONVERTED_HOLD",
                "pending_negrisk_convert": True,
                "neg_risk_market_id": "0x" + "11" * 32,
                "question_index": 0,
                "convert_fee_bips": 0.0,
                "remaining_shares": 10.0,
                "notional_usd": 4.80,
                "pending_liquid_yes_sells": [],
            },
            "NR_CONV_1_HOLD_NO_1": {
                "trade_id": "NR_CONV_1_HOLD_NO_1",
                "box_id": "NR_CONV_1",
                "box_expected_legs": 2,
                "box_type": "NEGRISK_CONVERT_ARB_UNCONVERTED_HOLD",
                "pending_negrisk_convert": True,
                "neg_risk_market_id": "0x" + "11" * 32,
                "question_index": 1,
                "convert_fee_bips": 0.0,
                "remaining_shares": 10.0,
                "notional_usd": 4.80,
                "pending_liquid_yes_sells": [],
            },
        },
        _last_known_collateral=50.0,
        _last_complete_set_merge_ts=0.0,
        _onchain_merges_completed=0,
        record_fill_and_update_position=_rec_fill,
        save_state=MagicMock(),
        _close_position=MagicMock(),
    )
    harv_nr._close_position.side_effect = lambda t, *a, **kw: harv_nr.active_positions.pop(t, None)
    asyncio.run(
        maybe_merge_live_complete_sets_impl(harv_nr, now + 30.0, types.SimpleNamespace(FILLED="FILLED", SETTLED="SETTLED"), MagicMock())
    )
    ex_nr.attempt_negrisk_convert_positions.assert_called_once()
    assert harv_nr.active_positions == {}

    # <5.0-share partial FAK fill on Leg 1 (ok=False, matched_shares=2.5) MUST be tracked via UNWRESID, never dropped!
    ex_fak = types.SimpleNamespace(
        dry_run=True,
        execute_snipe_order=lambda **kw: {"success": False, "matched_shares": 2.5, "price": 0.40, "order_id": "OID_SUB5"},
        execute_unwind_order=lambda *a, **kw: {"success": False, "matched_size": 0.0, "outcome_unknown": False},
    )
    harv_b = types.SimpleNamespace(
        dry_run=True,
        active_positions={},
        closed_positions=[],
        save_state=MagicMock(),
    )
    legs = [
        {"market_id": "m1", "token_id": "tok_sub5_1", "ask_px": 0.30, "fee_rate": 0.0},
        {"market_id": "m2", "token_id": "tok_sub5_2", "ask_px": 0.32, "fee_rate": 0.0},
        {"market_id": "m3", "token_id": "tok_sub5_3", "ask_px": 0.33, "fee_rate": 0.0},
    ]
    res_b = _execute_multi_leg_bundle_sync(ex_fak, legs, shares=10.0, bundle_id="B_SUB5", harvester=harv_b, exp_ts=now + 600.0)
    assert res_b["success"] is False
    unw_keys = [k for k in harv_b.active_positions if "UNWRESID" in k]
    assert len(unw_keys) == 1
    assert harv_b.active_positions[unw_keys[0]]["remaining_shares"] == pytest.approx(2.5)


def test_v02_v05_s04_i02_i06_doubleheader_2h5_shadow_keys_withdrawal_floor_and_pm_cache(tmp_path: Path) -> None:
    """[S-04/V-05/I-02/I-06] 2.5h single-admission MLB doubleheader blocked; canonical 5m shadow keys wired; withdrawal lowers floor; PolymarketConnector caches fee-rate & slug."""
    from src.polymarket_research.cross_venue_connectors import PolymarketConnector, ResilientReadOnlyTransport
    from src.polymarket_research.directional_wfo_shadow_sleeves import DirectionalWfoShadowManager
    from src.polymarket_research.holistic_strategy_governance import get_unleashed_v5_tier_profile

    now = 1_765_004_000.0
    # 2.5h (9000s) single-admission back-to-back MLB doubleheader Game 1 Final MUST NOT mark live Game 2 completed!
    espn_g2 = [
        LiveMultiSportGame(
            sport="MLB", game_id="eg2", start_ts=now - 900.0, state="in", completed=False,
            is_halftime=False, period=2, clock_sec=0.0, home_name="Chicago Cubs", away_name="St. Louis Cardinals",
            home_score=0, away_score=0,
        )
    ]
    off_g1 = [
        LiveMultiSportGame(
            sport="MLB", game_id="og1", start_ts=now - 9900.0, state="post", completed=True,
            is_halftime=False, period=9, clock_sec=0.0, home_name="Chicago Cubs", away_name="St. Louis Cardinals",
            home_score=4, away_score=1,
        )
    ]
    assert reconcile_multisport_dual_source_boards("MLB", espn_g2, off_g1)[0].completed is False

    # Post-lock operator withdrawal ($15) lowers hard_ruin_floor_usd ($42 -> $27) and HWM ($65 -> $50)
    cfg_wd = json.loads(json.dumps(DEFAULT_HOLISTIC_CONFIG))
    cfg_wd["_net_withdrawals_post_lock_usd"] = 15.0
    prof_wd = get_unleashed_v5_tier_profile(total_equity=45.0, high_water_mark_equity=65.0, cfg=cfg_wd)
    assert prof_wd["min_equity_floor"] == pytest.approx(27.0)

    # Canonical enable_btc_5m_sniper_shadow key tails b5 telemetry in production_mode
    mgr = DirectionalWfoShadowManager(data_dir=tmp_path, production_mode=True)
    (tmp_path / "polymarket_5m_telemetry_btc.jsonl").write_text(
        json.dumps({"market_id": "m_b5", "timestamp_unix": now, "tte_sec": 120.0}) + "\n",
        encoding="utf-8",
    )
    with patch.object(mgr, "_ingest_btc_5m_telemetry_tick") as spy_b5, patch(
        "src.polymarket_research.holistic_strategy_governance.GLOBAL_GOVERNANCE_MANAGER",
        types.SimpleNamespace(snapshot={"shadow_governance": {"enable_btc_5m_sniper_shadow": True, "enable_sol_5m_canary_shadow": False}}),
    ):
        mgr.poll_tick(False)
        assert spy_b5.call_count == 1

    # PolymarketConnector live-cache path deduplicates /fee-rate and ?slug= within TTL
    pm_c = PolymarketConnector(max_pages=1, enable_realtime_ws=False)
    pm_c._fee_rate_cache["tok_yes_1"] = (0.0, float(int(now)))
    assert pm_c._fee_rate_cache["tok_yes_1"][0] == 0.0
    tr_off = ResilientReadOnlyTransport(network_disabled=True)
    assert pm_c._can_use_live_ws(tr_off) is False


def test_subcent_partial_fill_redemption_and_startup_reconciliation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Sub-cent winning partial Maker fill (1.02 sh @ $0.996 -> +$0.0041) books won=True & net_pnl_usd=0.0041 across close, redemption, startup migration, and PAA ledger."""
    import scripts.paa_autonomous_controller as pac
    import src.polymarket_research.polymarket_live_harvester as plh

    pos_win = {
        "trade_id": "MKR_LOCK1_LIVE_SPORTS_CHILD_MONEYLINE_1794263184_03247",
        "sleeve": "BOND1_UMA_RESOLUTION_CARRY",
        "is_single_leg_lock": True,
        "hold_to_maturity_lock": True,
        "box_type": "SINGLE_LEG_MAKER_LOCK",
        "entry_price": 0.996,
        "entry_shares": 1.02,
        "notional_usd": 1.0159,
        "fee_usd": 0.0,
        "entry_fee_cash_usd": 0.0,
        "entry_fee_asset": "USDC",
        "status": "AWAITING_ONCHAIN_SETTLEMENT",
        "winning_shares_held": 1.02,
        "resolved_winning_outcome": "YES",
        "target_token": "YES",
    }
    assert plh.PolymarketLiveHarvester.calculate_realized_cash_pnl(pos_win, 1.02, 0.0) == pytest.approx(0.0041)
    # Boundary checks: exact break-even (0.0) and sub-cent loss (-0.0041) MUST stay won=False
    assert plh.PolymarketLiveHarvester.calculate_realized_cash_pnl({**pos_win, "notional_usd": 1.02}, 1.02, 0.0) == 0.0
    assert plh.PolymarketLiveHarvester.calculate_realized_cash_pnl({**pos_win, "notional_usd": 1.0241}, 1.02, 0.0) == pytest.approx(-0.0041)

    state_file = tmp_path / "live_harvester_state.json"
    monkeypatch.setattr(plh, "STATE_FILE", state_file)
    harv = plh.PolymarketLiveHarvester(dry_run=True)
    tid = pos_win["trade_id"]
    harv.active_positions[tid] = dict(pos_win)
    assert harv.confirm_onchain_redemption(tid, verified_usdc_received=1.02, tx_hash="0x77a4fc62") is True
    closed_rec = harv.closed_positions[-1]
    assert closed_rec["won"] is True
    assert closed_rec["net_pnl_usd"] == pytest.approx(0.0041)
    assert closed_rec["payout_usd"] == pytest.approx(1.02)

    # Simulate pre-fix persisted state with rounded net_pnl_usd=0.0, won=False + true flat record (must NOT flip won)
    legacy_closed = dict(closed_rec, net_pnl_usd=0.0, won=False)
    true_flat = dict(closed_rec, trade_id="TRUE_FLAT_BREAK_EVEN", notional_usd=1.02, net_pnl_usd=0.0, won=False)
    persisted = json.loads(state_file.read_text(encoding="utf-8"))
    persisted["live_bankroll"] = 47.12
    persisted["closed_positions"] = [legacy_closed, true_flat]
    state_file.write_text(json.dumps(persisted), encoding="utf-8")

    harv_reloaded = plh.PolymarketLiveHarvester(dry_run=True)
    harv_reloaded.risk_controller.non_directional_realized_pnl = 0.0
    persisted_before = json.loads(state_file.read_text(encoding="utf-8"))
    persisted_before.setdefault("risk_state", {})["non_directional_realized_pnl"] = 10.0
    state_file.write_text(json.dumps(persisted_before), encoding="utf-8")
    harv_reloaded.load_state()
    by_tid = {c["trade_id"]: c for c in harv_reloaded.closed_positions}
    assert by_tid[tid]["won"] is True
    assert by_tid[tid]["net_pnl_usd"] == pytest.approx(0.0041)
    assert by_tid["TRUE_FLAT_BREAK_EVEN"]["won"] is False
    assert by_tid["TRUE_FLAT_BREAK_EVEN"]["net_pnl_usd"] == 0.0
    assert harv_reloaded._last_known_collateral == pytest.approx(47.12)
    assert harv_reloaded.risk_controller.non_directional_realized_pnl == pytest.approx(10.0041)
    assert plh.PolymarketLiveHarvester.calculate_realized_cash_pnl({"notional_usd": 17.856}, 0.0, 0.0) == pytest.approx(-17.86)

    # Also verify PAA reconcile_closed_position_record reconciles pre-fix raw record cleanly
    c_norm, ver_pnl, raw_pnl, was_rec = pac.reconcile_closed_position_record(legacy_closed)
    assert was_rec is True
    assert raw_pnl == 0.0
    assert ver_pnl == pytest.approx(0.0041)
    assert c_norm["won"] is True


def test_per_event_maker_concurrency_race_and_repost_guard(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Concurrent MKR_LOCK1 tasks AND delayed _bond1_repost_count>=1 reposts on the same EVT:1284258 strictly obey max_concurrent_intents_per_event == 1."""
    import src.polymarket_research.polymarket_live_harvester as plh

    monkeypatch.setattr(plh, "DATA_DIR", tmp_path)
    monkeypatch.setattr(plh, "STATE_FILE", tmp_path / "live_harvester_state.json")
    now = time.time()
    (tmp_path / "alpha124_shadow_state.json").write_text(
        json.dumps(
            {
                "by_sleeve": {
                    "D1_SAME_ORACLE_DOMINANCE_BOX": {"closed": 10, "wins": 10, "losses": 0, "win_rate_pct": 100.0, "realized_pnl_t1000_usd": 25.0},
                    "BOND1_UMA_RESOLUTION_CARRY": {"closed": 12, "wins": 12, "losses": 0, "win_rate_pct": 100.0, "realized_pnl_t1000_usd": 14.0},
                    "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER": {"closed": 10, "wins": 10, "losses": 0, "win_rate_pct": 100.0, "realized_pnl_t1000_usd": 9.0},
                }
            }
        ),
        encoding="utf-8",
    )

    h = plh.PolymarketLiveHarvester(dry_run=True)
    h.dry_run = False
    h._startup_reconciled = True
    h._last_known_collateral = 65.0
    h.enforce_bond1_smart_queue = True
    h.enforce_event_concentration_cap = True
    h.holistic_v5_live_mode = True
    h.executor.auth_mode = "LIVE"
    h._pos_market_ws = None

    posted_oids: list[str] = []
    release_gate = threading.Event()

    def _slow_book(tok: str) -> dict:
        time.sleep(0.03)
        if "opp" in tok:
            return {"bids": [{"price": "0.002", "size": "100"}], "asks": [{"price": "0.008", "size": "100"}]}
        return {"bids": [{"price": "0.991", "size": "20"}], "asks": [{"price": "0.999", "size": "100"}], "minimum_tick_size": "0.001"}

    def _post_maker(*, token_id: str, price: float, notional_usd: float, **kw) -> dict:
        time.sleep(0.02)
        oid = f"0xoid_{token_id}"
        posted_oids.append(oid)
        return {"success": True, "orderID": oid, "price": price, "shares": round(notional_usd / price, 2)}

    monkeypatch.setattr(h.executor, "get_market_book", _slow_book)
    monkeypatch.setattr(h.executor, "post_maker_entry_order", _post_maker)
    monkeypatch.setattr(h.executor, "get_collateral_balance", lambda *a, **kw: 65.0)

    async def _fast_reconcile(maker_oid, tok_a, ws_filled, posted_sh, posted_px, pre_bal_a):
        return {"is_canceled": True, "outcome": "CANCELED"}, {"matched": 0.0, "terminal": True}, 0.0, posted_px

    monkeypatch.setattr(h, "_reconcile_maker_entry_fill", _fast_reconcile)

    base_cand = {
        "box_type": "SINGLE_LEG_MAKER_LOCK",
        "sleeve_source": "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",
        "asset": "NBA",
        "event_id": "1284258",
        "event_group_key": "EVT:1284258",
        "leg_a_condition_id": "0xcond_nba",
        "leg_a_side": "YES",
        "leg_a_neg_risk": False,
        "anchor_bid_px": 0.992,
        "min_resting_bid": 0.985,
        "max_box_cost_net": 0.995,
        "max_opp_bid": 0.008,
        "p_model": 0.9995,
        "official_final_confirmed": True,
        "expiry_ts": now + 3600.0,
        "ts_unix": now,
    }
    cand_1 = {
        **base_cand,
        "box_id": "MKR_LOCK1_LIVE_NBA_1794272429_04412",
        "dedupe_key": "MKR_LK1_6904412",
        "pair_dedupe_key": "LK1_6904412",
        "leg_a_market_id": "6904412",
        "leg_a_token_id": "tok_win_6904412",
        "leg_a_opp_token_id": "tok_opp_6904412",
    }
    cand_2 = {
        **base_cand,
        "box_id": "MKR_LOCK1_LIVE_NBA_1794272429_04420",
        "dedupe_key": "MKR_LK1_6904420",
        "pair_dedupe_key": "LK1_6904420",
        "leg_a_market_id": "6904420",
        "leg_a_token_id": "tok_win_6904420",
        "leg_a_opp_token_id": "tok_opp_6904420",
    }

    async def _race_and_repost() -> None:
        t1 = asyncio.create_task(h.maybe_execute_graduated_single_leg_maker_lock(cand_1))
        t2 = asyncio.create_task(h.maybe_execute_graduated_single_leg_maker_lock(cand_2))
        # Wait until one task rests in pending_entry_intents while the sibling has already exited
        for _ in range(40):
            await asyncio.sleep(0.02)
            if len(h.pending_entry_intents) >= 1 and (t1.done() or t2.done()):
                break
        assert len(h.pending_entry_intents) == 1
        assert len(posted_oids) == 1

        # Delayed preempt/outbid repost (_bond1_repost_count = 1) on the OTHER market of EVT:1284258 MUST ALSO be blocked!
        resting_mkt = next(iter(h.pending_entry_intents.values()))["market_id"]
        other_cand = cand_2 if resting_mkt == "6904412" else cand_1
        repost_res = await h.maybe_execute_graduated_single_leg_maker_lock(
            {**other_cand, "_bond1_repost_count": 1, "ts_unix": time.time()}
        )
        assert repost_res["executed"] is False
        assert repost_res["reason"] == "MAX_CONCURRENT_PER_EVENT_REACHED"
        assert len(posted_oids) == 1

        # Preempt the resting intent cleanly and verify zero leaked _prepost_sll_events reservations
        for ev in h._maker_anchor_preempt_events.values():
            ev.set()
        r1, r2 = await asyncio.gather(t1, t2)
        reasons = {r1.get("reason"), r2.get("reason")}
        assert "MAX_CONCURRENT_PER_EVENT_REACHED" in reasons
        assert h.pending_entry_intents == {}
        assert h._prepost_sll_events == {}
        release_gate.set()

    asyncio.run(_race_and_repost())
    assert release_gate.is_set()


def test_cross_venue_shadow_320m_ceiling_and_memory_compaction(tmp_path: Path) -> None:
    """polymarket-cross-venue-shadow.service enforces MemoryHigh=280M/MemoryMax=320M, and WS/engine buffers compact cleanly."""
    from src.polymarket_research.cross_venue_connectors import LimitlessMarketWsState, PolymarketMarketWsState
    from src.polymarket_research.cross_venue_riskless_shadow import (
        HonestCrossVenueShadowEngine,
        HonestShadowExecutionOutcome,
        RuleVerificationResult,
        ShadowArbitrageCandidate,
    )
    from src.polymarket_research.cross_venue_shadow_deployment_gates import validate_systemd_unit_text
    from src.polymarket_research.cross_venue_telemetry_and_watchdog import ShadowRuntimeWatchdog, ShadowTelemetryStore

    unit_path = Path(__file__).resolve().parents[1] / "systemd" / "polymarket-cross-venue-shadow.service"
    unit_txt = unit_path.read_text(encoding="utf-8")
    assert "MemoryHigh=280M" in unit_txt
    assert "MemoryMax=320M" in unit_txt
    rep_320 = validate_systemd_unit_text(unit_txt, str(unit_path))
    assert rep_320.valid, rep_320.errors
    rep_180 = validate_systemd_unit_text(unit_txt.replace("MemoryMax=320M", "MemoryMax=180M"), str(unit_path))
    assert rep_180.valid

    store = ShadowTelemetryStore(tmp_path / "cv_wd")
    try:
        wd = ShadowRuntimeWatchdog(store)
        assert wd.memory_budget_mb >= 320.0
    finally:
        store.close()

    # LimitlessMarketWsState caps rotating 5m slug subscriptions at <=120 and orderbook cache <=256
    lim_ws = LimitlessMarketWsState()
    lim_ws.build_full_subscription_payload([f"btc-5m-{i}" for i in range(90)])
    sub_2 = lim_ws.build_full_subscription_payload([f"btc-5m-{i}" for i in range(90, 160)])
    assert len(sub_2["data"]["marketSlugs"]) <= 120
    for i in range(1000):
        lim_ws.seed_from_rest(f"slug-{i}", {"asks": [{"price": 0.5, "size": 10}], "bids": []}, ts_ms=1000 + i)
    assert len(lim_ws.orderbooks_by_slug) <= 256

    # PolymarketMarketWsState prunes stale token books above 256 down to 160 (low-water) and never exceeds 256
    pm_ws = PolymarketMarketWsState()
    for i in range(257):
        pm_ws.apply_frame({"event_type": "book", "asset_id": f"tok_{i}", "timestamp": 1000 + i, "asks": [{"price": "0.55", "size": "10"}], "bids": []})
    assert len(pm_ws.books) == 160
    for i in range(257, 1000):
        pm_ws.apply_frame({"event_type": "book", "asset_id": f"tok_{i}", "timestamp": 1000 + i, "asks": [{"price": "0.55", "size": "10"}], "bids": []})
    assert len(pm_ws.books) <= 256

    # HonestCrossVenueShadowEngine compacts >512 outcomes without changing cumulative graduation metrics
    eng = HonestCrossVenueShadowEngine(data_dir=tmp_path / "cv_eng", enable_durable_store=False)
    sample_cand = ShadowArbitrageCandidate(
        family="XV_TAKER_BOX_OR_CORRIDOR",
        candidate_key="XV::test",
        venue_a="polymarket",
        venue_b="limitless",
        market_a_slug="pa",
        market_b_slug="lb",
        side_a="YES",
        side_b="NO",
        shares=25.0,
        gross_cost_usd=24.5,
        fees_usd=0.0,
        gas_usd=0.01,
        bridge_drag_usd=0.01,
        guaranteed_min_payout_usd=25.0,
        expected_net_profit_usd=0.48,
        net_edge_bps=195.0,
        est_unsettled_rebate_usd=0.02,
        effective_delay_ms=80.0,
        rule_check=RuleVerificationResult(True, ()),
    )
    for _ in range(600):
        eng.outcomes.append(
            HonestShadowExecutionOutcome(
                candidate=sample_cand,
                survived_latency_recheck=True,
                maker_queue_filled=False,
                locked_complete_basket=True,
                unwind_bleed_usd=0.0,
                realized_shadow_net_pnl_usd=0.50,
                reason="POST_DELAY_BOTH_LEGS_LOCKED",
            )
        )
    grad = eng.build_graduation_report(simulated_days=1.0)
    assert len(eng.outcomes) == 256
    assert grad.locked_complete_baskets == 600
    assert grad.total_realized_shadow_net_pnl_usd == pytest.approx(300.0)


def test_paa_accountant_persists_fresh_authoritative_financial_ledger_and_open_orders(tmp_path: Path) -> None:
    """PAAAccountant.measure_and_record refreshes paa/authoritative_financial_ledger.json and clob_open_orders_count every cycle."""
    from src.paa_os.accountant import PAAAccountant
    from src.paa_os.budget import BudgetManager
    from src.paa_os.task_db import PAATaskDB

    data_dir = tmp_path / "polymarket"
    paa_dir = data_dir / "paa"
    paa_dir.mkdir(parents=True, exist_ok=True)
    now = time.time()
    intents = {
        f"INTENT_{i}": {
            "trade_id": f"INTENT_{i}",
            "market_id": f"69000{i}",
            "entry_order_id": f"0xoid_{i}",
            "notional_usd": 8.928,
            "live_maker_anchor_inflight": True,
            "ts": now - 30.0,
            "heartbeat_ts": now - 2.0,
        }
        for i in range(5)
    }
    (data_dir / "live_harvester_state.json").write_text(
        json.dumps({"live_bankroll": 47.12, "active_positions": {}, "closed_positions": [], "pending_entry_intents": intents}),
        encoding="utf-8",
    )
    db = PAATaskDB(paa_dir / "paa_tasks.db")
    cfg = {"riskless_mandate": {"enforce_riskless_only_live": True, "riskless_epoch_start_utc": "2026-11-04T02:05:00Z"}}
    acc = PAAAccountant(db=db, budget=BudgetManager(db, autonomy_cfg=cfg), data_dir=data_dir, autonomy_cfg=cfg)
    acc.measure_and_record(live_rpc_check=False)

    ledger_path = paa_dir / "authoritative_financial_ledger.json"
    assert ledger_path.exists()
    persisted_ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert persisted_ledger["clob_open_orders_count"] == 5
    assert persisted_ledger["free_cash_pusd"] == pytest.approx(47.12)


def test_multileg_box_consolidation_and_paa_grouping_subcent_cash_conservation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Multi-leg boxes whose per-leg 2-decimal cent rounding sums to -0.01 or 0.0 preserve exact positive consolidated cash PnL."""
    import src.polymarket_research.polymarket_live_harvester as plh
    from src.paa_os.optimizer import group_closed_positions_by_box
    from src.polymarket_research.riskless_protocol_v2_expansion import consolidate_any_box_leg_close

    monkeypatch.setattr(plh, "STATE_FILE", tmp_path / "live_harvester_state.json")
    harv = plh.PolymarketLiveHarvester(dry_run=True)

    # 3-leg bundle: exact profit = 1.0200 - (0.3460 + 0.3360 + 0.3360) = +$0.0020,
    # whereas per-leg 2-decimal cent PnLs (+0.67, -0.34, -0.34) would sum to -$0.01 (false loss)!
    legs_3 = [
        {"trade_id": "ML3_L1", "box_id": "ML3_BOX", "is_dominance_box": True, "box_type": "MULTI_LEG_BUNDLE", "sleeve": "D1_SAME_ORACLE_DOMINANCE_BOX", "notional_usd": 0.3460, "payout": 1.0200},
        {"trade_id": "ML3_L2", "box_id": "ML3_BOX", "is_dominance_box": True, "box_type": "MULTI_LEG_BUNDLE", "sleeve": "D1_SAME_ORACLE_DOMINANCE_BOX", "notional_usd": 0.3360, "payout": 0.0},
        {"trade_id": "ML3_L3", "box_id": "ML3_BOX", "is_dominance_box": True, "box_type": "MULTI_LEG_BUNDLE", "sleeve": "D1_SAME_ORACLE_DOMINANCE_BOX", "notional_usd": 0.3360, "payout": 0.0},
    ]
    for lg in legs_3:
        harv.active_positions[lg["trade_id"]] = dict(lg)

    raw_closed_3 = []
    final_pos = None
    for idx, lg in enumerate(legs_3):
        tid = lg["trade_id"]
        pos = harv.active_positions[tid]
        leg_pnl = harv.calculate_realized_cash_pnl(pos, lg["payout"], 0.0)
        raw_closed_3.append(
            {
                **pos,
                "payout_usd": lg["payout"],
                "net_pnl_usd": leg_pnl,
                "won": leg_pnl > 0.0,
            }
        )
        deferred, tot_pnl = consolidate_any_box_leg_close(harv, tid, pos, lg["payout"], 0.0, leg_pnl, "SETTLED", True)
        if idx < 2:
            assert deferred is True
        else:
            assert deferred is False
            final_pos = pos
            assert tot_pnl == pytest.approx(0.0020)

    assert final_pos is not None
    assert final_pos["won"] is True
    assert final_pos["net_pnl_usd"] == pytest.approx(0.0020)

    grouped_3 = group_closed_positions_by_box(raw_closed_3, {})
    assert len(grouped_3) == 1
    assert grouped_3[0]["won"] is True
    assert grouped_3[0]["net_pnl_usd"] == pytest.approx(0.0020)

    # 2-leg box: exact profit = 1.0100 - (0.5060 + 0.4960) = +$0.0080 -> +$0.01 (not 0.0 from +0.50 - 0.50)
    harv.active_positions["D2_A"] = {"trade_id": "D2_A", "box_id": "D2_BOX", "box_partner_trade_id": "D2_B", "is_dominance_box": True, "notional_usd": 0.5060}
    harv.active_positions["D2_B"] = {"trade_id": "D2_B", "box_id": "D2_BOX", "box_partner_trade_id": "D2_A", "is_dominance_box": True, "notional_usd": 0.4960}
    pa = harv.active_positions["D2_A"]
    pnl_a = harv.calculate_realized_cash_pnl(pa, 1.0100, 0.0)
    def_a, _ = consolidate_any_box_leg_close(harv, "D2_A", pa, 1.0100, 0.0, pnl_a, "SETTLED", True)
    assert def_a is True
    pb = harv.active_positions["D2_B"]
    pnl_b = harv.calculate_realized_cash_pnl(pb, 0.0, 0.0)
    def_b, tot_2 = consolidate_any_box_leg_close(harv, "D2_B", pb, 0.0, 0.0, pnl_b, "SETTLED", True)
    assert def_b is False
    assert tot_2 == pytest.approx(0.01)
    assert pb["won"] is True


def test_post_fill_async_gap_blocks_sibling_maker_on_same_event(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When MKR_LOCK1 fills on EVT:1284258, _prepost_sll_events bridges the async get_account_fills window until active_positions is written."""
    import src.polymarket_research.polymarket_live_harvester as plh

    monkeypatch.setattr(plh, "DATA_DIR", tmp_path)
    monkeypatch.setattr(plh, "STATE_FILE", tmp_path / "live_harvester_state.json")
    now = time.time()
    (tmp_path / "alpha124_shadow_state.json").write_text(
        json.dumps(
            {
                "by_sleeve": {
                    "D1_SAME_ORACLE_DOMINANCE_BOX": {"closed": 10, "wins": 10, "losses": 0, "win_rate_pct": 100.0, "realized_pnl_t1000_usd": 25.0},
                    "BOND1_UMA_RESOLUTION_CARRY": {"closed": 12, "wins": 12, "losses": 0, "win_rate_pct": 100.0, "realized_pnl_t1000_usd": 14.0},
                    "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER": {"closed": 10, "wins": 10, "losses": 0, "win_rate_pct": 100.0, "realized_pnl_t1000_usd": 9.0},
                }
            }
        ),
        encoding="utf-8",
    )

    h = plh.PolymarketLiveHarvester(dry_run=True)
    h.dry_run = False
    h._startup_reconciled = True
    h._last_known_collateral = 65.0
    h.enforce_bond1_smart_queue = True
    h.enforce_event_concentration_cap = True
    h.holistic_v5_live_mode = True
    h.executor.auth_mode = "LIVE"
    h._pos_market_ws = None

    posted_oids: list[str] = []
    in_fills_event = threading.Event()
    release_fills_event = threading.Event()

    monkeypatch.setattr(
        h.executor,
        "get_market_book",
        lambda tok: {"bids": [{"price": "0.002", "size": "100"}], "asks": [{"price": "0.008", "size": "100"}]}
        if "opp" in tok
        else {"bids": [{"price": "0.991", "size": "20"}], "asks": [{"price": "0.999", "size": "100"}], "minimum_tick_size": "0.001"},
    )
    monkeypatch.setattr(
        h.executor,
        "post_maker_entry_order",
        lambda *, token_id, price, notional_usd, **kw: (
            posted_oids.append(f"0xoid_{token_id}") or {"success": True, "orderID": f"0xoid_{token_id}", "price": price, "shares": 6.0}
        ),
    )
    monkeypatch.setattr(h.executor, "get_collateral_balance", lambda *a, **kw: 65.0)

    async def _fill_reconcile(maker_oid, tok_a, ws_filled, posted_sh, posted_px, pre_bal_a):
        return {"is_canceled": False, "outcome": "FILLED"}, {"matched": 6.0, "cash": round(6.0 * posted_px, 4), "terminal": True}, 6.0, posted_px

    def _slow_fills(*_a, **_kw):
        in_fills_event.set()
        release_fills_event.wait(timeout=2.0)
        return [{"trade_id": "t_fill_1", "transaction_hash": "0xtx_fill_1"}]

    monkeypatch.setattr(h, "_reconcile_maker_entry_fill", _fill_reconcile)
    monkeypatch.setattr(h.executor, "get_account_fills", _slow_fills)

    base = {
        "box_type": "SINGLE_LEG_MAKER_LOCK",
        "sleeve_source": "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",
        "asset": "NBA",
        "event_id": "1284258",
        "event_group_key": "EVT:1284258",
        "leg_a_condition_id": "0xcond_nba",
        "leg_a_side": "YES",
        "leg_a_neg_risk": False,
        "anchor_bid_px": 0.992,
        "min_resting_bid": 0.985,
        "max_box_cost_net": 0.995,
        "max_opp_bid": 0.008,
        "p_model": 0.9995,
        "official_final_confirmed": True,
        "expiry_ts": now + 3600.0,
        "ts_unix": now,
    }
    cand_1 = {**base, "box_id": "MKR_FILL_1", "dedupe_key": "MKF_1", "pair_dedupe_key": "PKF_1", "leg_a_market_id": "6904412", "leg_a_token_id": "tok_w1", "leg_a_opp_token_id": "tok_opp_1"}
    cand_2 = {**base, "box_id": "MKR_SIB_2", "dedupe_key": "MKF_2", "pair_dedupe_key": "PKF_2", "leg_a_market_id": "6904420", "leg_a_token_id": "tok_w2", "leg_a_opp_token_id": "tok_opp_2", "_bond1_repost_count": 1}

    async def _run() -> None:
        t1 = asyncio.create_task(h.maybe_execute_graduated_single_leg_maker_lock(cand_1))
        for _ in range(150):
            await asyncio.sleep(0.02)
            if len(h.pending_entry_intents) >= 1 or t1.done():
                break
        if t1.done():
            raise AssertionError(f"t1 exited before resting: {t1.result()}")
        for ev in h._maker_anchor_preempt_events.values():
            ev.set()
        for _ in range(150):
            await asyncio.sleep(0.02)
            if in_fills_event.is_set() or t1.done():
                break
        if t1.done() and not in_fills_event.is_set():
            raise AssertionError(f"t1 exited before get_account_fills: {t1.result()}")
        assert in_fills_event.is_set()
        assert h.pending_entry_intents == {}
        assert "MKR_FILL_1" not in h.active_positions

        # Sibling arrives DURING get_account_fills await -> MUST be blocked by bridged _prepost_sll_events!
        r_sib = await h.maybe_execute_graduated_single_leg_maker_lock({**cand_2, "ts_unix": time.time()})
        assert r_sib["executed"] is False
        assert r_sib["reason"] == "MAX_CONCURRENT_PER_EVENT_REACHED"
        assert len(posted_oids) == 1

        release_fills_event.set()
        r1 = await t1
        assert r1["executed"] is True
        assert "MKR_FILL_1" in h.active_positions
        assert h._prepost_sll_events == {}

    asyncio.run(_run())


def test_cross_venue_sqlite_covering_index_prune_ws_close_safety_and_sigterm_preempt(tmp_path: Path) -> None:
    """Covering index avoids table scans on orderbook_snapshots, 15d prune preserves 14d window, WS close / recovery clears last_error, and SIGTERM preempts cycles."""
    import sqlite3
    from src.polymarket_research.cross_venue_connectors import (
        ForecastExIBKRConnector,
        PolymarketConnector,
        PolymarketMarketWsState,
        PolymarketRealtimeClient,
        ResilientReadOnlyTransport,
    )
    from src.polymarket_research.cross_venue_riskless_shadow import NormalizedBinaryMarket, OrderLevel
    from src.polymarket_research.cross_venue_telemetry_and_watchdog import ShadowTelemetryStore

    store = ShadowTelemetryStore(tmp_path / "cv_idx")
    now = 1_795_000_000.0
    try:
        old_m = NormalizedBinaryMarket(
            venue="polymarket",
            market_id="m_old",
            slug="old-1",
            title="Old",
            category="macro",
            yes_asks=[OrderLevel(0.45, 50.0)],
            yes_bids=[OrderLevel(0.44, 50.0)],
            no_asks=[OrderLevel(0.56, 50.0)],
            no_bids=[OrderLevel(0.55, 50.0)],
            quote_ts_ms=int((now - 16 * 86_400) * 1000),
            data_origin="LIVE_VERIFIED",
        )
        fresh_m = NormalizedBinaryMarket(
            venue="polymarket",
            market_id="m_fresh",
            slug="fresh-1",
            title="Fresh",
            category="macro",
            yes_asks=[OrderLevel(0.45, 50.0)],
            yes_bids=[OrderLevel(0.44, 50.0)],
            no_asks=[OrderLevel(0.56, 50.0)],
            no_bids=[OrderLevel(0.55, 50.0)],
            quote_ts_ms=int((now - 2 * 86_400) * 1000),
            data_origin="LIVE_VERIFIED",
        )
        store.ingest_markets([old_m], now_unix=now - 16 * 86_400)
        store.ingest_markets([fresh_m], now_unix=now - 2 * 86_400)

        with sqlite3.connect(str(store.db_path)) as con:
            plan_rows = con.execute(
                "EXPLAIN QUERY PLAN SELECT COALESCE(AVG(total_depth_usd), 0.0) FROM orderbook_snapshots WHERE venue = 'polymarket' AND data_origin NOT IN ('OFFLINE_SYNTHETIC', 'TESTNET_SANDBOX')"
            ).fetchall()
            plan_txt = " ".join(str(x) for r in plan_rows for x in r)
            assert "COVERING INDEX idx_ob_venue_origin_depth" in plan_txt

        deleted = store.prune_expired_telemetry(now_unix=now, retention_sec=15 * 86_400)
        assert deleted == 1
        win = store.build_campaign_window_summaries(now_unix=now)
        assert win["14d"]["live_snapshots_ingested"] == 1
    finally:
        store.close()

    # PolymarketRealtimeClient._send_subscriptions catches concurrent WS close & _record_poll_success clears sticky last_error
    ws_client = PolymarketRealtimeClient(PolymarketMarketWsState())
    ws_client._subscribed_ids = ["tok_1"]
    ws_client._send_lock = asyncio.Lock()

    class _ClosedWs:
        async def send(self, _frame: str) -> None:
            raise RuntimeError("sent 1000 (OK); no close frame received")

    ws_client._active_ws = _ClosedWs()
    asyncio.run(ws_client._send_subscriptions(force=True))
    assert ws_client._active_ws is None
    assert "RuntimeError" in ws_client.last_error

    pm_conn = PolymarketConnector(enable_realtime_ws=False)
    pm_conn.snapshot.last_error = "UNHANDLED_CONNECTOR_ERR:sent 1000 (OK); no close frame received"
    pm_conn.snapshot.consecutive_transient_failures = 2
    pm_conn._record_poll_success()
    assert pm_conn.snapshot.last_error == ""
    assert pm_conn.snapshot.consecutive_transient_failures == 0
    assert pm_conn.snapshot.to_health_dict()["reason"] == pm_conn.snapshot.authorization_state

    # ForecastEx 300s live-transport cache serves cached contracts without hitting network when fresh
    fex = ForecastExIBKRConnector(env={"DOMINUS_NETWORK_MODE": "live_public"})
    cached_m = NormalizedBinaryMarket(
        venue="forecastex",
        market_id="FF_202612_4.5",
        slug="FF_202612_4.5",
        title="ForecastEx FF",
        category="macro",
        yes_asks=[OrderLevel(0.45, 25.0)],
        yes_bids=[OrderLevel(0.43, 25.0)],
        no_asks=[OrderLevel(0.57, 25.0)],
        no_bids=[OrderLevel(0.55, 25.0)],
        end_ts=int(time.time()) + 86400,
        data_origin="REGULATORY_PUBLIC_DELAYED",
    )
    fex._portal_cache = (time.time(), "20261109", [cached_m], 13288, 446)
    tr_fex = ResilientReadOnlyTransport(network_disabled=True)
    res_fex = asyncio.run(fex.poll_markets(tr_fex))
    assert len(res_fex) == 1
    assert fex.snapshot.protocol_detail == "FORECASTEX_PUBLIC_CFTC_PORTAL(date=20261109)"

    # SIGTERM preempts an active slow LiveCrossVenueShadowCollector.run_single_cycle in <2s (never 15s TimeoutStopSec)
    import os
    import signal as _sig
    import subprocess
    import sys

    if os.name != "nt":
        repo_root = str(Path(__file__).resolve().parents[1])
        child_code = (
            "import asyncio, sys\n"
            f"sys.path.insert(0, {repo_root!r})\n"
            "import scripts.shadow_cross_venue_riskless_probe as svp\n"
            "async def _slow(_self):\n"
            "    print('IN_SLOW_CYCLE', flush=True)\n"
            "    await asyncio.sleep(12.0)\n"
            "    return {}\n"
            "svp.LiveCrossVenueShadowCollector.run_single_cycle = _slow\n"
            f"raise SystemExit(svp.main(['--data-dir', {str(tmp_path / 'cv_stop')!r}, '--interval-sec', '15']))\n"
        )
        proc = subprocess.Popen(
            [sys.executable, "-c", child_code],
            env={k: v for k, v in os.environ.items() if k != "DOMINUS_NETWORK_MODE"},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            assert proc.stdout is not None
            ready_line = proc.stdout.readline().strip()
            assert ready_line == "IN_SLOW_CYCLE"
            t0_p = time.perf_counter()
            proc.send_signal(_sig.SIGTERM)
            rc_p = proc.wait(timeout=4.0)
            elapsed_stop = time.perf_counter() - t0_p
            assert rc_p == 0
            assert elapsed_stop < 2.5
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=2.0)
    else:
        import scripts.shadow_cross_venue_riskless_probe as svp

        async def _win_probe() -> float:
            args_p = svp.parse_args(["--data-dir", str(tmp_path / "cv_stop"), "--interval-sec", "15"])
            orig_run = svp.LiveCrossVenueShadowCollector.run_single_cycle
            in_slow = asyncio.Event()

            async def _slow_cycle(_self: object) -> dict:
                in_slow.set()
                await asyncio.sleep(10.0)
                return {}

            svp.LiveCrossVenueShadowCollector.run_single_cycle = _slow_cycle  # type: ignore[method-assign]
            try:
                probe_task = asyncio.create_task(svp.main_async(args_p))
                await asyncio.wait_for(in_slow.wait(), timeout=5.0)
                t0_w = time.perf_counter()
                _sig.raise_signal(_sig.SIGTERM)
                rc_w = await asyncio.wait_for(probe_task, timeout=2.0)
                assert rc_w == 0
                return time.perf_counter() - t0_w
            finally:
                svp.LiveCrossVenueShadowCollector.run_single_cycle = orig_run  # type: ignore[method-assign]

        assert asyncio.run(_win_probe()) < 1.5

