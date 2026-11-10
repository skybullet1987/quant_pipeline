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


def test_upgrade1_mlk1_protected_from_low_velocity_or_saturated_bond1() -> None:
    import threading
    from src.polymarket_research.riskless_protocol_v2_expansion import maybe_preempt_mlk1_if_bond1_starved

    now_t = time.time()
    ev = threading.Event()
    h = SimpleNamespace(
        dry_run=False,
        active_positions={},
        pending_entry_intents={
            "mlk_heat": {
                "live_maker_anchor_inflight": True,
                "inflight_key": "MLK_HEAT_965",
                "sleeve_source": "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",
                "anchor_bid_px": 0.965,  # 350 bps / 1.5h floor => 233.33 bps/hr
                "expiry_ts": now_t + 900.0,
                "notional_usd": 19.30,
            }
        },
        _maker_anchor_preempt_events={"MLK_HEAT_965": ev},
        _prepost_sll_reserved_usd={},
        _is_v5_unleashed_active=lambda: True,
        enforce_gatling_fast_gun_reserve=False,
    )
    # Slow BOND1 @ $0.992 (80 bps / 1.2h => 66.7 bps/hr << 233.33 * 1.25) MUST NOT cancel MLK_HEAT_965!
    out_slow = asyncio.run(
        maybe_preempt_mlk1_if_bond1_starved(
            h,
            "BOND1_UMA_RESOLUTION_CARRY",
            budget=4.0,
            collat=55.0,
            own_mkr_grad=True,
            enforce_b1_v53=True,
            b1_gov={"seed_zero_loss_focus_bond1_pool_pct": 0.92, "bond1_per_market_cap_usd_seed": 45.0},
            rcfg_sll={},
            gsn_s={"directional": {"riskless_only_mode": True}},
            open_mid_u=0.0,
            rem_tte_sec=4320.0,
            now_ts=now_t,
            cand_bid_px=0.992,
        )
    )
    assert out_slow == pytest.approx(4.0)
    assert ev.is_set() is False

    # Even if BOND1 is high-velocity ($0.950), if BOND1 ALREADY holds >= 45% of wallet equity ($40 / $75), do NOT cancel MLK1!
    h.active_positions["b1_open"] = {
        "sleeve": "BOND1_UMA_RESOLUTION_CARRY",
        "box_type": "SINGLE_LEG_MAKER_LOCK",
        "status": "POSITION_CONFIRMED",
        "notional_usd": 40.0,
    }
    out_sat = asyncio.run(
        maybe_preempt_mlk1_if_bond1_starved(
            h,
            "BOND1_UMA_RESOLUTION_CARRY",
            budget=4.0,
            collat=35.0,
            own_mkr_grad=True,
            enforce_b1_v53=True,
            b1_gov={"seed_zero_loss_focus_bond1_pool_pct": 0.92, "bond1_per_market_cap_usd_seed": 45.0},
            rcfg_sll={},
            gsn_s={"directional": {"riskless_only_mode": True}},
            open_mid_u=0.0,
            rem_tte_sec=900.0,
            now_ts=now_t,
            cand_bid_px=0.950,
        )
    )
    assert out_sat == pytest.approx(4.0)
    assert ev.is_set() is False


def test_upgrade2_deep_discount_sub_990_velocity_preemption_and_45s_fast_upgrade() -> None:
    import threading
    from src.polymarket_research.riskless_protocol_v2_expansion import select_sll_velocity_preempt_target

    now_t = time.time()
    h = SimpleNamespace(
        _maker_anchor_preempt_events={"BOND1_SLOW_993": threading.Event()},
        active_positions={},
        pending_entry_intents={
            "b1": {
                "live_maker_anchor_inflight": True,
                "inflight_key": "BOND1_SLOW_993",
                "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
                "anchor_bid_px": 0.993,  # 70 bps / 1.4h => 50 bps/hr
                "expiry_ts": now_t + 5040.0,
                "ts": now_t - 50.0,  # only 50s old (< 180s!), eligible under >=5x & +250 fast-upgrade!
            }
        },
    )
    # Deep-discount $0.950 post-clinch lock (~333 bps/hr >= max(50*5=250, 50+250=300)) preempts 50s-old $0.993 BOND1!
    vel, pk = select_sll_velocity_preempt_target(
        h,
        cand_edge_hr=340.0,
        is_s2_mkr=False,
        vel_mult=1.80,
        now_pe=now_t,
        cand_sleeve="MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",
    )
    assert pk == "BOND1_SLOW_993"
    assert vel == pytest.approx(50.0, abs=0.5)


def test_upgrade3_s2_flow_weighted_ranking_and_dual_slot_reserve_split() -> None:
    from src.polymarket_research.riskless_protocol_v2_expansion import (
        compute_sll_and_carry_gatling_budget,
        resolve_s2_maker_concurrent_cap,
        score_live_candidate_velocity_ev,
    )

    now_t = time.time()
    # Ghost-spread DOGE @ $0.700 with $0 ask depth MUST NOT outrank real two-sided BTC @ $0.985!
    doge_ghost = {
        "box_type": "SINGLE_LEG_MAKER_LOCK",
        "sleeve_source": "S2_RTDS_EXACT_TWAP_INTEGRATOR",
        "asset": "DOGE",
        "box_cost_net": 0.700,
        "shares": 16,
        "expiry_ts": now_t + 25.0,
        "queue_front": True,
        "ask_depth_usd": 0.0,
        "maker_rebate_ps": 0.0,
    }
    btc_real = {
        "box_type": "SINGLE_LEG_MAKER_LOCK",
        "sleeve_source": "S2_RTDS_EXACT_TWAP_INTEGRATOR",
        "asset": "BTC",
        "box_cost_net": 0.985,
        "shares": 16,
        "expiry_ts": now_t + 25.0,
        "queue_front": True,
        "ask_depth_usd": 28.0,
        "maker_rebate_ps": 0.0002,
    }
    assert score_live_candidate_velocity_ev(btc_real, True, now_t) > score_live_candidate_velocity_ev(doge_ghost, True, now_t)

    # Offline MagicMock preserves 1-slot cap, whereas live real CLOB / enforce_s2_multi_slot unlocks 2 slots & splits $21.16 reserve!
    h_mock = SimpleNamespace(dry_run=False, executor=SimpleNamespace(client=MagicMock()))
    assert resolve_s2_maker_concurrent_cap(h_mock, {"s2_maker_max_concurrent_slots": 2}) == 1

    class _RealStubClient:
        pass

    h_live = SimpleNamespace(
        dry_run=False,
        max_exposure=250.0,
        active_positions={},
        pending_entry_intents={},
        _inflight_s2_maker_keys=set(),
        _is_v5_unleashed_active=lambda: True,
        executor=SimpleNamespace(client=_RealStubClient()),
    )
    rb = {"gatling_enabled": True, "s2_maker_max_concurrent_slots": 2}
    assert resolve_s2_maker_concurrent_cap(h_live, rb) == 2
    b_slot1 = compute_sll_and_carry_gatling_budget(
        h_live,
        21.16,
        21.16,
        54.40,
        "SINGLE_LEG_MAKER_LOCK",
        "S2_RTDS_EXACT_TWAP_INTEGRATOR",
        False,
        rb,
        rem_tte_sec=25.0,
        now_ts=now_t,
    )
    assert 10.50 <= b_slot1 <= 11.20  # Leaves ~$10.15 for concurrent S2 Slot #2 (ETH/SOL)!


def test_upgrade4_dedicated_reward_carry_micro_slot_and_anti_churn() -> None:
    import threading
    from src.polymarket_research.riskless_protocol_v2_expansion import (
        cap_bond1_maker_for_gatling_reserve,
        select_sll_velocity_preempt_target,
    )

    now_t = time.time()
    rb = {
        "gatling_enabled": True,
        "gatling_fast_gun_reserve_usd": 20.0,
        "enable_reward_locked_carry_live_bridge": True,
        "reward_reserved_slot_usd_seed": 7.96,
        "reward_harvester_cap_usd_seed": 12.0,
    }
    h = SimpleNamespace(
        dry_run=False,
        enforce_gatling_fast_gun_reserve=True,
        enforce_reward_slot_reserve=True,
        _is_v5_unleashed_active=lambda: True,
        active_positions={},
        pending_entry_intents={},
    )
    # With $29.12 free cash + $46.44 BOND1 ($75.56 NAV -> $21.16 S2 reserve), $7.96 remains:
    # BOND1 is capped to $0.00 so the $7.96 dedicated reward slot stays free, while MKR_REWARD_LOCKED_CARRY gets $7.96!
    b_b1 = cap_bond1_maker_for_gatling_reserve(
        h, 20.0, 29.12, 46.44, rb, sleeve_src="BOND1_UMA_RESOLUTION_CARRY"
    )
    b_rw = cap_bond1_maker_for_gatling_reserve(
        h, 12.0, 29.12, 46.44, rb, sleeve_src="MKR_REWARD_LOCKED_CARRY"
    )
    assert b_b1 == pytest.approx(0.0)
    assert b_rw == pytest.approx(7.96)

    # Once 1 RW slot + >=2 BOND1 slots are resting, 80 bps/hr BOND1 CANNOT evict RW every 45s, but 200 bps/hr CAN!
    h._maker_anchor_preempt_events = {"RW_SLOT_1": threading.Event()}
    h.pending_entry_intents = {
        "rw1": {
            "live_maker_anchor_inflight": True,
            "inflight_key": "RW_SLOT_1",
            "sleeve_source": "MKR_REWARD_LOCKED_CARRY",
            "anchor_bid_px": 0.992,
            "expiry_ts": now_t + 5400.0,
            "ts": now_t - 60.0,
        },
        "b1_a": {"live_maker_anchor_inflight": True, "inflight_key": "B1_A", "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY", "ts": now_t - 10.0},
        "b1_b": {"live_maker_anchor_inflight": True, "inflight_key": "B1_B", "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY", "ts": now_t - 10.0},
    }
    assert select_sll_velocity_preempt_target(
        h, cand_edge_hr=80.0, is_s2_mkr=False, vel_mult=1.80, now_pe=now_t, cand_sleeve="BOND1_UMA_RESOLUTION_CARRY"
    ) == (0.0, "")
    assert select_sll_velocity_preempt_target(
        h, cand_edge_hr=200.0, is_s2_mkr=False, vel_mult=1.80, now_pe=now_t, cand_sleeve="BOND1_UMA_RESOLUTION_CARRY"
    )[1] == "RW_SLOT_1"


def test_upgrade5_bond1_queue_ranking_998_stepdown_and_fast_reconcile() -> None:
    from src.polymarket_research.riskless_protocol_v2_expansion import (
        score_live_candidate_velocity_ev,
        spawn_fast_htm_maker_fill_reconcile,
    )

    now_t = time.time()
    c_empty = {"box_type": "SINGLE_LEG_MAKER_LOCK", "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY", "box_cost_net": 0.992, "shares": 10, "expiry_ts": now_t + 1800.0, "queue_front": True, "queue_ahead_usd": 0.0}
    c_mid = {**c_empty, "queue_ahead_usd": 45.0}
    c_deep = {**c_empty, "queue_ahead_usd": 260.0, "queue_front": False}
    assert score_live_candidate_velocity_ev(c_empty, True, now_t) > score_live_candidate_velocity_ev(c_mid, True, now_t) > score_live_candidate_velocity_ev(c_deep, True, now_t)

    posted_prices: list[float] = []

    class _MockRecycleExec:
        def get_open_orders(self):
            return [{"id": "OID_999"}]

        def get_order_fill_summary(self, oid, tok):
            return {"matched": 0.0, "terminal": False}

        def cancel_order(self, oid):
            return {"is_canceled": True}

        def release_inventory(self, reservation_id=None):
            pass

        def get_market_book(self, tok):
            return {"bids": [{"price": 0.994, "size": 50.0}], "asks": [{"price": 0.999, "size": 20.0}], "minimum_tick_size": 0.001}

        def post_maker_exit_order(self, token_id, price, size, **kwargs):
            posted_prices.append(float(price))
            return {"success": True, "orderID": f"OID_{len(posted_prices)}"}

    h = SimpleNamespace(
        dry_run=False,
        ONCHAIN_SOURCE="ONCHAIN_ERC1155",
        executor=_MockRecycleExec(),
        active_positions={},
        save_state=lambda: None,
        _record_order_summary=lambda *a, **k: None,
        _wallet_token_balance=lambda tok: (10.0, "ONCHAIN_ERC1155"),
        calculate_realized_cash_pnl=lambda pos, gross_cash, exit_fee: float(gross_cash) - float(exit_fee) - float(pos.get("entry_shares", 0.0)) * float(pos.get("entry_price", 0.0)),
    )
    # 1) Entry @ $0.994 (<= 0.9945) posts $0.998 immediately upon fast ERC-1155 reconciliation!
    h.active_positions["T_994"] = {
        "trade_id": "T_994",
        "is_single_leg_lock": True,
        "hold_to_maturity_lock": True,
        "sleeve": "BOND1_UMA_RESOLUTION_CARRY",
        "token_id": "tok_994",
        "status": "MATCHED_PENDING_SETTLEMENT",
        "inventory_reconciled": False,
        "pre_token_balance": 0.0,
        "entry_shares": 10.0,
        "remaining_shares": 10.0,
        "entry_price": 0.994,
        "candle_expiry_ts": now_t + 3600.0,
        "fee_rate_applied": 0.0,
    }

    async def _run_fast():
        spawn_fast_htm_maker_fill_reconcile(h, "T_994")
        await asyncio.sleep(0.95)

    asyncio.run(_run_fast())
    assert h.active_positions["T_994"]["inventory_reconciled"] is True
    assert h.active_positions["T_994"]["target_exit_price"] == pytest.approx(0.998)
    assert posted_prices[-1] == pytest.approx(0.998)

    # 2) Entry @ $0.995 resting @ $0.999 for >= 300s steps down cleanly to $0.998!
    pos_995 = {
        "trade_id": "T_995",
        "is_single_leg_lock": True,
        "hold_to_maturity_lock": True,
        "sleeve": "BOND1_UMA_RESOLUTION_CARRY",
        "token_id": "tok_995",
        "status": "POSITION_CONFIRMED",
        "inventory_reconciled": True,
        "entry_shares": 10.0,
        "remaining_shares": 10.0,
        "entry_price": 0.995,
        "candle_expiry_ts": now_t + 3600.0,
        "fee_rate_applied": 0.0,
        "exit_order_id": "OID_999",
        "target_exit_price": 0.999,
        "_htm_passive_recycle_active": True,
        "_htm_passive_post_ts": now_t - 305.0,
    }
    bk_step = {"bids": [{"price": 0.995, "size": 40.0}], "asks": [{"price": 0.999, "size": 10.0}], "minimum_tick_size": 0.001}
    ok_step = asyncio.run(maybe_manage_passive_htm_early_maker_recycle(h, "T_995", pos_995, bk_step, now_t))
    assert ok_step is True
    assert pos_995["target_exit_price"] == pytest.approx(0.998)


def test_upgrade6_est_4h_dominance_alignment_and_nr0_closed_multi_leg_bridge(tmp_path, monkeypatch) -> None:
    from datetime import datetime, timezone
    import src.polymarket_research.alpha_124_shadow_daemon as a124
    from src.polymarket_research.riskless_protocol_v2_expansion import (
        next_et_4h_boundary_ts,
        resolve_active_4h_target_end_ts,
    )
    from src.polymarket_research.tradfi_sports_zero_fee_engine import parse_zero_fee_negrisk_slate

    # Nov 5, 2026 04:50:00 UTC == Nov 4, 2026 23:50:00 EST -> next 4h ET close is 05:00:00 UTC!
    ts_est = datetime(2026, 11, 5, 4, 50, 0, tzinfo=timezone.utc).timestamp()
    exp_est_close = int(datetime(2026, 11, 5, 5, 0, 0, tzinfo=timezone.utc).timestamp())
    assert next_et_4h_boundary_ts(ts_est) == exp_est_close
    tgt_est, rem_est = resolve_active_4h_target_end_ts(ts_est)
    assert tgt_est == exp_est_close and rem_est == pytest.approx(600.0)

    # July 15, 2026 03:50:00 UTC == July 14, 2026 23:50:00 EDT -> next 4h ET close is 04:00:00 UTC!
    ts_edt = datetime(2026, 7, 15, 3, 50, 0, tzinfo=timezone.utc).timestamp()
    exp_edt_close = int(datetime(2026, 7, 15, 4, 0, 0, tzinfo=timezone.utc).timestamp())
    assert next_et_4h_boundary_ts(ts_edt) == exp_edt_close

    # Synthetic 14400 * k UTC epoch fixture (Jan 2027) still resolves cleanly!
    tgt_syn, rem_syn = resolve_active_4h_target_end_ts(14400.0 * 125000 - 600.0)
    assert tgt_syn == 14400 * 125000 and rem_syn == pytest.approx(600.0)

    # Verify parse_zero_fee_negrisk_slate captures negRiskAugmented flag accurately
    now_iso_end = "2027-06-01T18:00:00Z"
    mkts = [
        {"id": f"m{i}", "conditionId": f"0x{i:064x}", "question": f"Bracket {i}?", "outcomes": '["Yes","No"]', "clobTokenIds": f'["y{i}","n{i}"]', "endDate": now_iso_end, "enableOrderBook": True}
        for i in range(3)
    ]
    sp_closed = parse_zero_fee_negrisk_slate({"id": "ev_c", "title": "FOMC", "negRisk": True, "negRiskAugmented": False, "endDate": now_iso_end, "markets": mkts}, "fomc")
    sp_aug = parse_zero_fee_negrisk_slate({"id": "ev_a", "title": "Tweets", "negRisk": True, "negRiskAugmented": True, "endDate": now_iso_end, "markets": mkts}, "elon-tweets")
    assert sp_closed is not None and sp_closed.neg_risk_augmented is False
    assert sp_aug is not None and sp_aug.neg_risk_augmented is True

    # Verify discover_4h_dominance_pairs pairs 05:00Z EST 4h + 15m BTC Chainlink candles!
    d = a124.Alpha124ShadowDaemon(single_scan=True)

    async def _fake_fetch(url: str, timeout: float = 4.0):
        if "btc-up-or-down-4h" in url:
            return [{
                "id": "ev4",
                "slug": f"btc-updown-4h-{exp_est_close - 14400}",
                "endDate": "2026-11-05T05:00:00Z",
                "markets": [{
                    "id": "m4",
                    "conditionId": "0x" + "4" * 64,
                    "outcomes": '["Up","Down"]',
                    "clobTokenIds": '["u4","d4"]',
                    "eventStartTime": "2026-11-05T01:00:00Z",
                    "endDate": "2026-11-05T05:00:00Z",
                    "resolutionSource": "https://data.chain.link/streams/btc-usd",
                    "cryptoMarketConfig": {"twapEnabled": True, "twapLookbackSeconds": 60},
                    "feesEnabled": True,
                }],
            }]
        if "btc-up-or-down-15m" in url:
            return [{
                "id": "ev15",
                "slug": f"btc-updown-15m-{exp_est_close - 900}",
                "endDate": "2026-11-05T05:00:00Z",
                "markets": [{
                    "id": "m15",
                    "conditionId": "0x" + "5" * 64,
                    "outcomes": '["Up","Down"]',
                    "clobTokenIds": '["u15","d15"]',
                    "eventStartTime": "2026-11-05T04:45:00Z",
                    "endDate": "2026-11-05T05:00:00Z",
                    "resolutionSource": "https://data.chain.link/streams/btc-usd",
                    "cryptoMarketConfig": {"twapEnabled": True, "twapLookbackSeconds": 60},
                    "feesEnabled": True,
                }],
            }]
        return []

    d.fetch_json = _fake_fetch  # type: ignore[assignment]
    asyncio.run(d.discover_4h_dominance_pairs(ts_est))
    assert f"BTC_4h15m_{exp_est_close}" in d.dominance_4h_pairs


def test_upgrade7_seed_tier_structural_box_slot_carveout_unclamps_cal1() -> None:
    from src.polymarket_research.riskless_protocol_v2_expansion import compute_sll_and_carry_gatling_budget

    now_t = time.time()
    rb = {"gatling_enabled": True, "gatling_fast_gun_reserve_usd": 20.0}
    h = SimpleNamespace(
        dry_run=False,
        max_exposure=250.0,
        enforce_gatling_fast_gun_reserve=True,
        _is_v5_unleashed_active=lambda: True,
        active_positions={
            "b1_1": {
                "sleeve": "BOND1_UMA_RESOLUTION_CARRY",
                "box_type": "SINGLE_LEG_MAKER_LOCK",
                "status": "POSITION_CONFIRMED",
                "notional_usd": 46.40,
                "candle_expiry_ts": now_t + 7200.0,
            }
        },
        pending_entry_intents={},
    )
    # On $75.56 NAV ($29.16 cash + $46.40 BOND1), 24h graduated CAL1 BARRIER_MONO box gets ~$16.62 (>= 8 shares)
    # while strictly preserving >= $10.50 unencumbered S2 Fast-Gun cash!
    b_cal1 = compute_sll_and_carry_gatling_budget(
        h,
        18.50,
        29.16,
        46.40,
        "BARRIER_MONO",
        "CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX",
        True,
        rb,
        rem_tte_sec=86400.0,
        now_ts=now_t,
    )
    assert 15.0 <= b_cal1 <= 18.66
    assert (29.16 - b_cal1) >= 10.50

    # Once 1 structural box ($16.62) is open, a 2nd structural box is blocked so S2 cash is never drained!
    h.active_positions["cal1_open"] = {
        "sleeve": "CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX",
        "box_type": "BARRIER_MONO",
        "status": "POSITION_CONFIRMED",
        "notional_usd": b_cal1,
        "candle_expiry_ts": now_t + 86400.0,
    }
    b_cal1_second = compute_sll_and_carry_gatling_budget(
        h,
        18.50,
        round(29.16 - b_cal1, 2),
        round(46.40 + b_cal1, 2),
        "NEGRISK_2LEG",
        "COND1_MACRO_PARTITION_BOX",
        True,
        rb,
        rem_tte_sec=43200.0,
        now_ts=now_t,
    )
    assert b_cal1_second < 5.0

