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
    augment_uma_proposed_from_universe_and_polygon,
    compute_sll_entry_budget,
    filter_purged_ghost_orders,
    is_verified_zero_fill_cancel_purge,
    maybe_early_profit_recycle_htm_lock,
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
