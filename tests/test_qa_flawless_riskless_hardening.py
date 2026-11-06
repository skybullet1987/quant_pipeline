"""
Deterministic Regression & QA Suite for Flawless Riskless Execution & Profit Hardening (v5.4.5+).

Covers:
  1. Persistent ghost-order quarantine (`is_verified_zero_fill_cancel_purge`, `record_purged_ghost_order`,
     `filter_purged_ghost_orders`, and `PolymarketLiveExecutor.get_open_orders`).
  2. Share-denominated Taker fee haircut (`px / (1.0 - h)`) in `scan_d1_zero_fee_bridged_crypto_cross_market`
     and deferred Leg-2 FOK gross resolution (`_resolve_deferred_fok_gross`) in `execute_maker_anchor_hedge_or_unwind`.
  3. Pre-cancel velocity-preemption budget projection (`exclude_inflight_key` in `compute_sll_entry_budget`).
  4. CLOB HTTP `425`/`429` deterministic rejection (`is_clob_400_rejection`) & expired-session `post_heartbeat` reset.
  5. `riskless_only_mode` gating of directional ladder prewarm & fast-IPC datagrams + batch `trade_id` fill attribution.
  6. `_close_position` `HTM_PASSIVE_MAKER_RECYCLE_FILLED` -> `MAKER_SCALP` bucket, safe `_maybe_recycle_uma_disputed_lock`
     resting-order reconciliation, Polygon 900-block OO log chunking & sticky disputed market eviction.
  7. `_default_d1_calibration_events` 1-leg filtering & `dominus_command_center` pre-redeemed / synced-intent equity accounting.
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import src.polymarket_research.polymarket_live_harvester as plh
from src.polymarket_research.orderflow_wfo_simulators import _default_d1_calibration_events
from src.polymarket_research.polymarket_live_executor import (
    PolymarketLiveExecutor,
    is_clob_400_rejection,
)
from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester
from src.polymarket_research.riskless_protocol_v2_expansion import (
    _HTM_PASSIVE_MAKER_RECYCLE_SLEEVES,
    augment_uma_proposed_from_universe_and_polygon,
    compute_sll_entry_budget,
    eval_sll_live_book_poll,
    execute_binary_ctf_overround_mint_sell,
    filter_purged_ghost_orders,
    finish_protocol_v2_special_box_sync,
    is_verified_zero_fill_cancel_purge,
    maybe_early_profit_recycle_htm_lock,
    maybe_manage_passive_htm_early_maker_recycle,
    position_own_exit_order_ids,
)


def test_ghost_order_quarantine_and_open_orders_filtering(tmp_path: Path) -> None:
    ghost_file = tmp_path / "purged_ghosts.json"
    ex = PolymarketLiveExecutor(dry_run=True)
    ex.dry_run = False
    ex.is_authenticated = True
    ex._purged_ghost_orders_file = ghost_file
    ex.client = SimpleNamespace(
        get_open_orders=lambda: [
            {"id": "0xghost_closed_1", "asset_id": "tok_a", "price": "0.991", "original_size": "25", "size_matched": "0"},
            {"id": "0xlive_working_2", "asset_id": "tok_b", "price": "0.992", "original_size": "10", "size_matched": "0"},
        ]
    )
    ex.get_account_fills = lambda tok, since_ts, side, oid=None: []  # type: ignore[method-assign]
    ex.get_conditional_balance = lambda tok: 0.0  # type: ignore[method-assign]

    purged = is_verified_zero_fill_cancel_purge(
        ex,
        "0xghost_closed_1",
        0.0,
        "order can't be canceled - market is closed",
        {"asset_id": "tok_a", "associate_trades": []},
        token_id="tok_a",
        pre_token_balance=0.0,
        market_closed=True,
    )
    assert purged is True
    assert ghost_file.exists()

    open_ords = ex.get_open_orders()
    assert open_ords is not None
    assert [o["id"] for o in open_ords] == ["0xlive_working_2"]
    assert len(filter_purged_ghost_orders(ex, [{"orderID": "0xghost_closed_1"}])) == 0


def test_share_denominated_taker_fee_haircut_and_delayed_leg2_hedge_resolution() -> None:
    # 1. Share-denominated fee haircut: 0% Maker @ 0.474 + 7% fee-bearing crypto Taker @ 0.500:
    #    additive = 0.474 + 0.500 + 0.0175 = 0.9915 (<= 0.992), whereas share-haircut = 0.474 + 0.500 / (1 - 0.035) = 0.992135 (> 0.992)!
    ex_veto = PolymarketLiveExecutor(dry_run=True)
    ex_veto.get_token_tick_size = lambda *a, **k: 0.001  # type: ignore[method-assign]
    ex_veto.get_token_neg_risk = lambda *a, **k: False  # type: ignore[method-assign]
    ex_veto.execute_unwind_order = MagicMock(return_value={"success": True, "matched_size": 10.0, "outcome_unknown": False})  # type: ignore[method-assign]
    res_veto = ex_veto.execute_maker_anchor_hedge_or_unwind(
        box_id="BOX_HAIRCUT_VETO",
        anchor_token_id="tok_anc_zf",
        anchor_label="YES",
        anchor_price=0.474,
        anchor_matched_shares=10.0,
        anchor_order_id="oid_anc_zf",
        hedge_token_id="tok_hdg_fee",
        hedge_label="NO",
        hedge_limit_price=0.500,
        max_box_cost_net=0.992,
        hedge_fee_rate=0.07,
        hedge_fee_exponent=1.0,
    )
    assert res_veto["success"] is False
    assert res_veto["stage"] == "ANCHOR_PARTIAL_OR_CAP_UNWOUND"
    assert "MAKER_ANCHOR_PRE_HEDGE_VETO" in str(res_veto.get("error") or "")

    # 2. Delayed Leg-2 FOK hedge resolves cleanly via `_resolve_deferred_fok_gross` -> `get_order_fill_summary`
    ex = PolymarketLiveExecutor(dry_run=True)
    ex.dry_run = False
    ex.is_authenticated = True
    ex.auth_mode = "AUTHENTICATED_L2"
    ex.get_token_tick_size = lambda *a, **k: 0.01  # type: ignore[method-assign]
    ex.get_token_neg_risk = lambda *a, **k: False  # type: ignore[method-assign]
    ex.client = MagicMock()
    ex.client.create_order.return_value = MagicMock()
    ex.client.post_order.return_value = {"orderID": "oid_hdg_delayed", "status": "DELAYED"}
    ex.get_order_fill_summary = MagicMock(return_value={"status": "MATCHED", "matched": 10.0, "terminal": True})  # type: ignore[method-assign]

    res = ex.execute_maker_anchor_hedge_or_unwind(
        box_id="BOX_DELAYED_L2",
        anchor_token_id="tok_anc",
        anchor_label="YES",
        anchor_price=0.48,
        anchor_matched_shares=10.0,
        anchor_order_id="oid_anc_1",
        hedge_token_id="tok_hdg",
        hedge_label="NO",
        hedge_limit_price=0.50,
        max_box_cost_net=0.990,
        hedge_fee_rate=0.0,
        hedge_fee_exponent=1.0,
    )
    assert res["success"] is True
    assert res["outcome_unknown"] is False
    assert res["shares"] == pytest.approx(10.0)


def test_sll_velocity_preemption_exclude_inflight_key_budget_projection() -> None:
    now_ts = time.time()
    harv = SimpleNamespace(
        dry_run=False,
        max_exposure=100.0,
        active_positions={},
        pending_entry_intents={
            "INT_SLOW": {
                "inflight_key": "K_SLOW",
                "is_maker_anchor": True,
                "live_maker_anchor_inflight": True,
                "notional_usd": 18.0,
                "ts": now_ts,
                "heartbeat_ts": now_ts,
            },
            "INT_OTHER": {
                "inflight_key": "K_OTHER",
                "is_maker_anchor": True,
                "live_maker_anchor_inflight": True,
                "notional_usd": 15.0,
                "ts": now_ts,
                "heartbeat_ts": now_ts,
            },
        },
        _prepost_sll_reserved_usd={},
        _is_v5_unleashed_active=lambda: True,
    )
    # With $35 total wallet cash ($18 slow + $15 other = $33 reserved -> only $2 free):
    # Without excluding K_SLOW, budget is <= $2 (< 5 shares); excluding K_SLOW frees $18 -> $20 free!
    b_no_excl, _, _ = compute_sll_entry_budget(
        harv, "BOND1_UMA_RESOLUTION_CARRY", "m_new", 35.0, True, True, {}, {}, {}, 600.0, now_ts, post_vel_preempt=True
    )
    b_excl, _, _ = compute_sll_entry_budget(
        harv,
        "BOND1_UMA_RESOLUTION_CARRY",
        "m_new",
        35.0,
        True,
        True,
        {},
        {},
        {},
        600.0,
        now_ts,
        post_vel_preempt=True,
        exclude_inflight_key="K_SLOW",
    )
    assert b_no_excl < 4.95
    assert b_excl == pytest.approx(12.30)


def test_clob_425_429_rejection_and_expired_heartbeat_session_reset() -> None:
    e425 = SimpleNamespace(status_code=425, error_message="Too Early - matching engine restarting")
    e429 = SimpleNamespace(status_code=429, error_message="Rate limit exceeded")
    e502 = SimpleNamespace(status_code=502, error_message="Bad Gateway")
    assert is_clob_400_rejection(e425) is True
    assert is_clob_400_rejection(e429) is True
    assert is_clob_400_rejection(e502) is False

    ex = PolymarketLiveExecutor(dry_run=True)
    ex.dry_run = False
    ex.is_authenticated = True
    ex.last_heartbeat_id = "stale-expired-hid-123"
    calls = []

    def _fake_hb(heartbeat_id: str = ""):
        calls.append(heartbeat_id)
        if heartbeat_id == "stale-expired-hid-123":
            raise RuntimeError("PolyApiException[status_code=400, error_message={'error': 'Invalid heartbeat id'}]")
        return {"heartbeat_id": "fresh-hid-456"}

    ex.client = SimpleNamespace(post_heartbeat=_fake_hb)
    resp = ex.post_heartbeat()
    assert calls == ["stale-expired-hid-123", ""]
    assert resp["heartbeat_id"] == "fresh-hid-456"
    assert ex.last_heartbeat_id == "fresh-hid-456"
    assert ex.heartbeat_failures == 0


def test_riskless_only_gates_and_batch_trade_id_fill_attribution(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(plh, "DATA_DIR", tmp_path)
    monkeypatch.setattr(plh, "STATE_FILE", tmp_path / "state.json")
    harv = PolymarketLiveHarvester(dry_run=True)
    harv._is_riskless_only_mode = lambda: True  # type: ignore[method-assign]

    # Directional ladder pre-signing thread must NOT spawn when riskless_only_mode is True
    harv._spawn_ladder_prewarm(["tok_dir_1", "tok_dir_2"])
    assert getattr(harv, "_ladder_prewarm_thread", None) is None

    # Shared batch `trade_id` across two legs of an atomic `/orders` submission must STILL attribute Leg-2 when `req_oid == f_oid`
    harv.active_positions["BOX_1_L1"] = {
        "trade_id": "BOX_1_L1",
        "token_id": "tok_l1",
        "entry_order_id": "oid_l1",
        "entry_fill_ids": ["fill_l1"],
        "trade_ids": ["shared_batch_tid_99"],
    }
    pos_l2 = {
        "trade_id": "BOX_1_L2",
        "token_id": "tok_l2",
        "entry_order_id": "oid_l2",
        "entry_fill_ids": [],
        "trade_ids": [],
    }
    harv.active_positions["BOX_1_L2"] = pos_l2
    harv.executor.get_account_fills = lambda tok, after_ts=0.0, side="BUY", order_id=None: [  # type: ignore[method-assign]
        {
            "fill_id": "fill_l2",
            "trade_id": "shared_batch_tid_99",
            "order_id": "oid_l2",
            "side": "BUY",
            "size": 10.0,
            "price": 0.49,
            "fee_usd": 0.0,
        }
    ]
    fills_out = harv._fetch_account_fills("tok_l2", 0.0, "BUY", order_id="oid_l2", exclude_tid="BOX_1_L2")
    assert fills_out is not None and len(fills_out) == 1
    assert fills_out[0]["fill_id"] == "fill_l2"


def test_htm_maker_recycle_bucket_uma_dispute_reconcile_and_sticky_dispute_eviction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(plh, "DATA_DIR", tmp_path)
    monkeypatch.setattr(plh, "STATE_FILE", tmp_path / "state_htm.json")
    harv = PolymarketLiveHarvester(dry_run=True)

    # 1. `HTM_PASSIVE_MAKER_RECYCLE_FILLED` must classify into `MAKER_SCALP` (never `TERMINAL_LOSS`!)
    pos_win = {
        "trade_id": "T_MKR_REC_1",
        "market_id": "m_1",
        "token_id": "tok_1",
        "sleeve": "BOND1_UMA_RESOLUTION_CARRY",
        "is_single_leg_lock": True,
        "entry_price": 0.992,
        "entry_shares": 10.0,
        "remaining_shares": 0.0,
        "notional_usd": 9.92,
        "filled_exit_shares": 10.0,
        "realized_exit_cash": 9.99,
        "realized_exit_fees": 0.0,
    }
    harv.active_positions["T_MKR_REC_1"] = pos_win
    harv._close_position("T_MKR_REC_1", pos_win, "FILLED", "HTM_PASSIVE_MAKER_RECYCLE_FILLED", won=True)
    assert pos_win["exit_decomposition_bucket"] == "MAKER_SCALP"
    assert pos_win["net_pnl_usd"] == pytest.approx(0.07)

    # 2. Fee-bearing HTM profit-recycle exit must veto fee-negative 0.999 Taker FOK exits
    now_fee = time.time()
    pos_fee_htm = {
        "status": "POSITION_CONFIRMED",
        "inventory_reconciled": True,
        "hold_to_maturity_lock": True,
        "token_id": "tok_fee_htm",
        "candle_expiry_ts": now_fee + 900.0,
        "entry_price": 0.9985,
        "entry_shares": 20.0,
        "remaining_shares": 20.0,
        "notional_usd": 19.97,
        "fee_rate_applied": 0.07,
        "fee_exponent_applied": 1.0,
    }
    harv_live_chk = SimpleNamespace(
        dry_run=False,
        executor=SimpleNamespace(execute_unwind_order=MagicMock()),
        calculate_realized_cash_pnl=harv.calculate_realized_cash_pnl,
    )
    trig_fee = asyncio.run(
        maybe_early_profit_recycle_htm_lock(
            harv_live_chk, "T_FEE_HTM", pos_fee_htm, {"bids": [{"price": 0.999, "size": 50.0}]}, now_fee
        )
    )
    assert trig_fee is False
    assert harv_live_chk.executor.execute_unwind_order.call_count == 0

    # 3. `_maybe_recycle_uma_disputed_lock` reconciles already-filled resting passive Maker SELL instead of double-selling
    pos_disp = {
        "trade_id": "T_DISP_1",
        "market_id": "m_disp",
        "token_id": "tok_disp",
        "sleeve": "BOND1_UMA_RESOLUTION_CARRY",
        "status": "POSITION_CONFIRMED",
        "inventory_reconciled": True,
        "hold_to_maturity_lock": True,
        "is_single_leg_lock": True,
        "entry_price": 0.992,
        "entry_shares": 10.0,
        "remaining_shares": 10.0,
        "notional_usd": 9.92,
        "fee_rate_applied": 0.0,
        "exit_order_id": "oid_rest_999",
        "target_exit_price": 0.999,
        "_htm_passive_recycle_active": True,
    }
    harv.dry_run = False
    harv.active_positions["T_DISP_1"] = pos_disp
    harv.executor.get_market_book_async = lambda tok: asyncio.sleep(0, result={"bids": [{"price": 0.998, "size": 25.0}]})  # type: ignore[method-assign]
    harv.executor.cancel_order = MagicMock(return_value={"is_canceled": False, "not_canceled": {"oid_rest_999": "already matched"}})  # type: ignore[method-assign]
    harv.executor.get_order_fill_summary = MagicMock(  # type: ignore[method-assign]
        return_value={"order_id": "oid_rest_999", "status": "MATCHED", "matched": 10.0, "cash": 9.99, "terminal": True}
    )
    harv.executor.execute_unwind_order = MagicMock()  # type: ignore[method-assign]
    rec_ok = asyncio.run(harv._maybe_recycle_disputed_htm_lock("T_DISP_1", pos_disp, time.time()))
    assert rec_ok is True
    assert harv.executor.execute_unwind_order.call_count == 0
    assert "T_DISP_1" not in harv.active_positions
    assert pos_disp["close_reason"] == "HTM_PASSIVE_MAKER_RECYCLE_FILLED"

    # 4. Sticky disputed market eviction inside `< 10s` throttle window
    now_t = time.time()
    dm = SimpleNamespace(
        single_scan=False,
        uma_proposed_markets={"777111": {"id": "777111"}},
        uma_onchain_cache={"777111": (now_t, {"verified": True})},
    )
    r1 = asyncio.run(augment_uma_proposed_from_universe_and_polygon(dm, now_t, poll_fn=lambda _bn: (100, [], ["777111"])))
    assert r1["disputed_evicted"] == 1
    assert "777111" not in dm.uma_proposed_markets
    # Simulate Gamma discovery re-inserting `777111` 2 seconds later (inside 10s throttle without poll_fn)
    dm.uma_proposed_markets["777111"] = {"id": "777111"}
    r2 = asyncio.run(augment_uma_proposed_from_universe_and_polygon(dm, now_t + 2.0))
    assert r2["disputed_evicted"] == 1
    assert "777111" not in dm.uma_proposed_markets


def test_simulator_1leg_filtering_and_command_center_probe_compiles(tmp_path: Path) -> None:
    cand_f = tmp_path / "d1_live_box_candidates.jsonl"
    rows = [
        json.dumps({"box_type": "SINGLE_LEG_MAKER_LOCK", "shares": 10.0, "leg_a_avail_shares": 30.0})
        for _ in range(12)
    ] + [
        json.dumps(
            {
                "box_type": "DOMINANCE",
                "shares": 10.0,
                "leg_a_token_id": f"tok1_{i}",
                "leg_b_token_id": f"tok2_{i}",
                "leg_a_avail_shares": 25.0,
                "leg_b_avail_shares": 25.0,
                "expected_edge_per_share": 0.015,
            }
        )
        for i in range(38)
    ]
    cand_f.write_text("\n".join(rows) + "\n", encoding="utf-8")
    ev = _default_d1_calibration_events(tmp_path)
    assert len(ev) == 38

    import scripts.dominus_command_center as dcc

    code_obj = compile(dcc.REMOTE_PROBE_PY, "<dominus_remote_probe>", "exec")
    assert code_obj is not None


def test_mkr_lock1_passive_recycle_sleeves_resting_guard_and_cancel_ownership(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for real_sl in (
        "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",
        "SP4_INGAME_MILESTONE_IRREVERSIBLE_LOCK",
        "SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION",
        "CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH",
        "API1_ESPORTS_BO3_MAP1_HANDICAP_LOCK",
        "TW1_COUNTING_TRUNCATION_AND_BOX",
        "W1_SOLAR_PEAK_LOCK",
        "W1_LOW_TROUGH_LOCK",
        "NFL_PRP1_MILESTONE_AND_MAX_LOCKS",
        "SOC2_EXACT_SCORE_2D_LATTICE",
    ):
        assert real_sl in _HTM_PASSIVE_MAKER_RECYCLE_SLEEVES

    monkeypatch.setattr(plh, "DATA_DIR", tmp_path)
    monkeypatch.setattr(plh, "STATE_FILE", tmp_path / "state_mkr_lk1.json")
    harv = PolymarketLiveHarvester(dry_run=True)
    harv.dry_run = False
    now_t = time.time()
    pos = {
        "trade_id": "T_MLK1_1",
        "market_id": "m_mlk1",
        "token_id": "tok_mlk1",
        "sleeve": "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",
        "status": "POSITION_CONFIRMED",
        "inventory_reconciled": True,
        "hold_to_maturity_lock": True,
        "is_single_leg_lock": True,
        "is_dominance_box": False,
        "entry_price": 0.992,
        "entry_shares": 10.0,
        "remaining_shares": 10.0,
        "notional_usd": 9.92,
        "fee_rate_applied": 0.0,
        "candle_expiry_ts": now_t + 2400.0,
    }
    harv.active_positions["T_MLK1_1"] = pos
    harv.executor.get_token_tick_size = lambda *a, **k: 0.001  # type: ignore[method-assign]
    harv.executor.post_maker_exit_order = MagicMock(  # type: ignore[method-assign]
        return_value={"success": True, "orderID": "oid_mlk1_998", "price": 0.998}
    )

    # 1. Posts $0.998 passive Maker exit on MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER
    posted = asyncio.run(
        maybe_manage_passive_htm_early_maker_recycle(
            harv, "T_MLK1_1", pos, {"bids": [{"price": 0.992, "size": 20.0}]}, now_t, set()
        )
    )
    assert posted is True
    assert pos["exit_order_id"] == "oid_mlk1_998"
    assert pos["_htm_passive_recycle_active"] is True

    # 2. Resting poll with partial fill (3.0 shares) returns True (preventing Phase D fallthrough) & sets PARTIALLY_FILLED
    harv.executor.get_order_fill_summary = MagicMock(  # type: ignore[method-assign]
        return_value={"order_id": "oid_mlk1_998", "status": "LIVE", "matched": 3.0, "cash": 2.994, "terminal": False}
    )
    handled_resting = asyncio.run(
        maybe_manage_passive_htm_early_maker_recycle(
            harv, "T_MLK1_1", pos, {"bids": [{"price": 0.992, "size": 20.0}]}, now_t + 10.0, {"oid_mlk1_998"}
        )
    )
    assert handled_resting is True
    assert pos["status"] == "PARTIALLY_FILLED"
    assert pos["remaining_shares"] == pytest.approx(7.0)

    # 3. T-6m (< 360s) cancels resting order, records `oid_mlk1_998` in `canceled_maker_exit_oids`, and allows Taker 998 sweep
    harv.executor.cancel_order = MagicMock(return_value={"is_canceled": True, "canceled": ["oid_mlk1_998"]})  # type: ignore[method-assign]
    harv.executor.get_order_fill_summary = MagicMock(  # type: ignore[method-assign]
        return_value={"order_id": "oid_mlk1_998", "status": "CANCELED", "matched": 3.0, "cash": 2.994, "terminal": True}
    )
    pos["candle_expiry_ts"] = (now_t + 20.0) + 320.0
    handled_cancel = asyncio.run(
        maybe_manage_passive_htm_early_maker_recycle(
            harv, "T_MLK1_1", pos, {"bids": [{"price": 0.992, "size": 20.0}]}, now_t + 20.0, set()
        )
    )
    assert handled_cancel is False
    assert pos["exit_order_id"] is None
    assert pos["_htm_passive_recycle_active"] is False
    assert "oid_mlk1_998" in pos["canceled_maker_exit_oids"]
    assert "oid_mlk1_998" in position_own_exit_order_ids(pos)
    assert pos["status"] == "PARTIALLY_FILLED"

    # 4. `maybe_early_profit_recycle_htm_lock` accepts `PARTIALLY_FILLED` when $0.998 bid arrives at TTE >= 300s
    pos["candle_expiry_ts"] = (now_t + 40.0) + 600.0
    harv.executor.execute_unwind_order = MagicMock(  # type: ignore[method-assign]
        return_value={"success": True, "orderID": "oid_sweep_998", "matched_size": 7.0, "taking_amount": 6.986, "outcome_unknown": False}
    )
    swept = asyncio.run(
        maybe_early_profit_recycle_htm_lock(
            harv, "T_MLK1_1", pos, {"bids": [{"price": 0.998, "size": 25.0}]}, now_t + 40.0
        )
    )
    assert swept is True
    assert harv.executor.execute_unwind_order.call_count == 1


def test_ctf_overround_failed_merge_and_residual_supervision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(plh, "DATA_DIR", tmp_path)
    monkeypatch.setattr(plh, "STATE_FILE", tmp_path / "state_ctfovr.json")
    now_t = time.time()
    cid = "0x" + "a" * 64

    # Case A: Both FOK sells reject after `splitPosition`, AND `attempt_onchain_complete_set_merge` fails (`None`):
    # BOTH `YES` and `NO` legs MUST be registered in `active_positions` as a reconciled `COMPLETE_SET` (zero stranded tokens!).
    class _FailedMergeExec:
        def get_collateral_balance(self) -> float:
            return 60.0

        def get_market_book(self, token_id: str) -> dict:
            return {"bids": [{"price": "0.54", "size": "40"}], "asks": [{"price": "0.56", "size": "40"}]}

        def split_collateral_to_complete_set(self, condition_id: str, shares: float, neg_risk: bool = False) -> dict:
            return {"success": True, "tx_hash": "0xsplit_ok_1"}

        def execute_atomic_box_overround_unwind(self, *args, **kwargs) -> dict:
            return {
                "success": False,
                "partial_leg_unwind": False,
                "outcome_unknown": False,
                "leg_a": {"filled": False, "outcome_unknown": False},
                "leg_b": {"filled": False, "outcome_unknown": False},
            }

        def attempt_onchain_complete_set_merge(self, *args, **kwargs):
            return None

        def invalidate_collateral_cache(self) -> None:
            pass

    harv_fm = PolymarketLiveHarvester(dry_run=True)
    harv_fm.dry_run = False
    harv_fm._last_known_collateral = 60.0
    harv_fm.executor = _FailedMergeExec()  # type: ignore[assignment]

    out_fm = finish_protocol_v2_special_box_sync(
        harv_fm,
        {
            "box_id": "CTF_FM_1",
            "box_type": "CTF_OVERROUND",
            "sleeve_source": "CTF_OVERROUND_MINT_SELL",
            "asset": "POLY",
            "leg_a_market_id": "998877",
            "condition_id": cid,
            "yes_token_id": "1" * 28,
            "no_token_id": "2" * 28,
            "yes_bid": 0.54,
            "no_bid": 0.54,
            "max_fillable_shares": 10.0,
            "expiry_ts": now_t + 3600.0,
        },
        dedupe_k="DK_FM_1",
        retry_cd={},
        now_ts=now_t,
        rcfg={},
        own_grad=False,
    )
    assert out_fm["executed"] is False
    assert out_fm["merged_back"] is False
    assert out_fm["complete_set_supervised"] is True
    assert len(harv_fm.active_positions) == 2
    legs_fm = list(harv_fm.active_positions.values())
    assert {lg["target_token"] for lg in legs_fm} == {"YES", "NO"}
    assert all(
        lg["box_type"] == "COMPLETE_SET"
        and lg["is_dominance_box"] is True
        and lg["inventory_reconciled"] is True
        and lg["market_id"] == "998877"
        and lg["exit_order_status"] == "DETERMINISTIC_TERMINAL_HOLD"
        for lg in legs_fm
    )

    # Async helper parity when merge fails
    harv_fm_async = SimpleNamespace(active_positions={}, _last_known_collateral=50.0)
    res_fm_async = asyncio.run(
        execute_binary_ctf_overround_mint_sell(
            _FailedMergeExec(),
            condition_id=cid,
            yes_token_id="1" * 28,
            no_token_id="2" * 28,
            yes_min_bid=0.54,
            no_min_bid=0.54,
            shares=10.0,
            harvester=harv_fm_async,
            expiry_ts=now_t + 3600.0,
        )
    )
    assert res_fm_async["merged_back"] is False
    assert res_fm_async["complete_set_supervised"] is True
    assert len(harv_fm_async.active_positions) == 2

    # Case B: Partial leg unwind failure registers `is_legged_out_residual=True`, `hold_to_maturity_lock=False`, `UNWIND_RETRY_REQUIRED`
    class _PartialFailExec(_FailedMergeExec):
        def execute_atomic_box_overround_unwind(self, *args, **kwargs) -> dict:
            return {
                "success": False,
                "partial_leg_unwind": True,
                "outcome_unknown": False,
                "leg_a": {"filled": True, "taking_amount": 5.40, "fee_usd": 0.0, "outcome_unknown": False},
                "leg_b": {"filled": False, "outcome_unknown": False},
            }

        def execute_unwind_order(self, *args, **kwargs) -> dict:
            return {"success": False, "outcome_unknown": False}

    harv_pf = PolymarketLiveHarvester(dry_run=True)
    harv_pf.dry_run = False
    harv_pf._last_known_collateral = 60.0
    harv_pf.executor = _PartialFailExec()  # type: ignore[assignment]
    out_pf = finish_protocol_v2_special_box_sync(
        harv_pf,
        {
            "box_id": "CTF_PF_1",
            "box_type": "CTF_OVERROUND",
            "sleeve_source": "CTF_OVERROUND_MINT_SELL",
            "asset": "POLY",
            "leg_a_market_id": "554433",
            "condition_id": cid,
            "yes_token_id": "1" * 28,
            "no_token_id": "2" * 28,
            "yes_bid": 0.54,
            "no_bid": 0.54,
            "max_fillable_shares": 10.0,
            "expiry_ts": now_t + 3600.0,
        },
        dedupe_k="DK_PF_1",
        retry_cd={},
        now_ts=now_t,
        rcfg={},
        own_grad=False,
    )
    assert out_pf["executed"] is False
    assert len(harv_pf.active_positions) == 1
    r_pf = next(iter(harv_pf.active_positions.values()))
    assert r_pf["is_legged_out_residual"] is True
    assert r_pf["hold_to_maturity_lock"] is False
    assert r_pf["is_single_leg_lock"] is False
    assert r_pf["inventory_reconciled"] is True
    assert r_pf["exit_order_status"] == "UNWIND_RETRY_REQUIRED"
    assert r_pf["market_id"] == "554433"


def test_eval_sll_live_book_poll_outbid_repeg_resets_whale_queue_baseline() -> None:
    now_t = time.time()
    cand_box = {
        "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
        "p_model": 0.9985,
        "min_maker_edge": 0.004,
        "maker_rebate_ps": 0.0,
        "_posted_notional_usd": 15.0,
        "_init_l1_q_usd": 950.0,
        "_whale_q_since_mono": time.monotonic() - 25.0,
    }
    action, next_px, _, reason = eval_sll_live_book_poll(
        bk_oc={"bids": [{"price": 0.002, "size": 50.0}]},
        bk_wc={"bids": [{"price": 0.991, "size": 20.0}], "asks": [{"price": 0.995, "size": 40.0}]},
        candidate_box=cand_box,
        posted_px=0.990,
        min_rb=0.950,
        max_rb=0.994,
        max_opp=0.015,
        tk_wf=0.001,
        enforce_b1_v53=True,
        is_s2_mkr=False,
        repost_n_in=0,
        b1_q_cap=250.0,
        b1_buried_s=15.0,
        exp_ts=now_t + 600.0,
        buried_since_mono=None,
        collat_usd=75.0,
    )
    assert action == "REPEG"
    assert next_px == pytest.approx(0.992)
    assert "outbid" in reason
    assert cand_box["_init_l1_q_usd"] is None
    assert cand_box["_whale_q_since_mono"] is None
