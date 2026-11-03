#!/usr/bin/env python3
"""
End-to-End Verification Suite for the v5.0 Holistic Quantitative Architecture & Profit-Maximization Overhaul:
  1. Unified `ev_terminal_twap_t5` Exit Supervisor:
     - Salvages shallow `-2.5 bps` wrong-side `15m` 60s-TWAP reversals when CLOB bid collapses (`$0.36 <= entry - 0.24`)
       while legacy `Zone 3` (`6.0 bps`) froze into `-$18..-$21` terminal wipeouts.
     - Zero false cuts on noise wicks when CLOB bid stays healthy (`$0.68`) or spot rebounds (`v_spot_15s >= +0.03%`).
  2. Isolated Single-Market Zero-Bid (`LIQUIDITY_CRISIS`):
     - Single illiquid market at `T - 40s` isolates to `DETERMINISTIC_TERMINAL_HOLD` without global `risk_halt = True`.
     - Global halt trips only if `>= 2` distinct active markets simultaneously lose all bids at `TTE > 120s`.
  3. Dual-Budget Risk Controller & `BOND1` Single-Leg Maker Unblocking:
     - Directional daily-loss cooldown halts directional entries (`is_halted() == True`) while keeping `D1`, `D1_QUIET_BOOK`,
       `BOND1` (`SINGLE_LEG_MAKER_LOCK`), and fast `<= 6h` `CM_B3` boxes live (`_is_d1_box_halted() == False`), and never
       throttles `target_budget` via `rem_daily * 10.0`.
     - `2`-leg `ZERO_FEE_MAKER_ANCHOR` remains disabled while `1`-leg `SINGLE_LEG_MAKER_LOCK` (`BOND1`) dispatches cleanly.
  4. Zero-Downtime Config Hot-Reload (`HotReloadConfigManager`):
     - Atomic `st_mtime_ns` / `SIGHUP` reload updates live caps in-memory; malformed/out-of-range JSON fails closed.
  5. Live `1h [150s, 2400s]` Window, `15m` Taker Hard-Disable -> Subordinate `<= $0.72` Maker, `5m` Kill & `XAU` Synth Anchor.
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

import pytest

from src.polymarket_research.directional_wfo_shadow_sleeves import (
    MAX_MAKER_JOIN_QUEUE_USD,
    DirectionalWfoShadowManager,
    compute_synthetic_xau_usd_anchor,
)
from src.polymarket_research.holistic_strategy_governance import (
    HotReloadConfigManager,
    compute_stop_risk_fractional_kelly_ticket,
    evaluate_ev_terminal_twap_t5_salvage,
    get_unleashed_v5_tier_profile,
    passes_capital_velocity_hurdle,
)
from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester
from src.polymarket_research.polymarket_terminal_recorder import ASSET_CONFIGS, PolymarketDualFeed1HRecorder
from scripts.weekly_wfo_governance import evaluate_ledger_file


def test_ev_terminal_twap_t5_catches_shallow_twap_reversal_without_false_wick_cuts():
    now_t = 1_793_400_000.0
    pos = {"asset": "BTC", "target_token": "DOWN", "entry_price": 0.72}

    # Case A: Shallow -2.5 bps wrong-side reversal on 15m candle at TTE=55s with banked adverse TWAP & collapsed $0.36 bid
    # Legacy Zone 3 required >= 6.0 bps and froze until $0.00; ev_terminal_twap_t5 salvages cleanly after 3.0s!
    trig0, ws0, diag0 = evaluate_ev_terminal_twap_t5_salvage(
        pos=pos, now_ts=now_t, tte_rem=55.0, spot_valid=True, open_spot=70000.0,
        spot_disp=-17.5,  # -2.5 bps wrong-side for DOWN (spot 70017.5 > strike 70000.0)
        sigma_valid=True, candle_sigma=0.0018, is_subhourly_pos=True, is_5m_pos=False,
        best_b=0.36, entry_px=0.72, v_spot_15s_pct=-0.02, exit_fee_rate=0.07, fee_exp=1.0,
        twap_locked_mean=70022.0, twap_locked_weight=5.0 / 60.0, current_spot=70017.5, is_live_auth=True,
    )
    assert trig0 is False and ws0 == pytest.approx(0.025, abs=1e-4)
    assert pos.get("opposite_breakout_start_ts") == now_t

    trig1, _, diag1 = evaluate_ev_terminal_twap_t5_salvage(
        pos=pos, now_ts=now_t + 3.2, tte_rem=51.8, spot_valid=True, open_spot=70000.0,
        spot_disp=-17.5, sigma_valid=True, candle_sigma=0.0018, is_subhourly_pos=True, is_5m_pos=False,
        best_b=0.36, entry_px=0.72, v_spot_15s_pct=-0.02, exit_fee_rate=0.07, fee_exp=1.0,
        twap_locked_mean=70022.0, twap_locked_weight=8.2 / 60.0, current_spot=70017.5, is_live_auth=True,
    )
    assert trig1 is True
    assert diag1["v_salvage_net"] > diag1["p_win_t5"] + 0.04

    # Case B: Noise wick (-2.5 bps) where CLOB bid remains healthy at $0.66 -> MUST NOT cut rebounding winner!
    pos_healthy = {"asset": "BTC", "target_token": "DOWN", "entry_price": 0.72, "opposite_breakout_start_ts": now_t - 10.0}
    trig_h, _, _ = evaluate_ev_terminal_twap_t5_salvage(
        pos=pos_healthy, now_ts=now_t, tte_rem=80.0, spot_valid=True, open_spot=70000.0,
        spot_disp=-17.5, sigma_valid=True, candle_sigma=0.0022, is_subhourly_pos=True, is_5m_pos=False,
        best_b=0.66, entry_px=0.72, v_spot_15s_pct=0.0, exit_fee_rate=0.07, fee_exp=1.0,
    )
    assert trig_h is False


def test_single_market_zero_bid_isolated_vs_multi_market_global_halt(tmp_path, monkeypatch):
    import src.polymarket_research.polymarket_live_harvester as plh

    monkeypatch.setattr(plh, "DATA_DIR", tmp_path)
    monkeypatch.setattr(plh, "STATE_FILE", tmp_path / "zb_state.json")
    monkeypatch.setattr(plh, "read_fast_tick", lambda *a, **kw: None)

    h = PolymarketLiveHarvester(dry_run=True)
    h.low_bid_persistence_seconds = 1.5
    h.executor.get_market_book = lambda _tid: {"bids": [], "asks": [{"price": "0.99", "size": "50"}]}
    h.executor.get_order_fill_summary = lambda oid, _tok: {"order_id": oid, "matched": 0.0, "terminal": False, "resting": True}
    h.get_reference_spot_price = lambda _a: 70000.0
    now_t = time.time()

    h.active_positions["P1"] = {
        "trade_id": "P1", "sleeve": "SLEEVE_1_CORE_302", "market_id": "M1", "condition_id": "0x1",
        "token_id": "1" * 25, "target_token": "UP", "asset": "BTC", "horizon": "1h",
        "candle_open_spot": 70100.0, "entry_price": 0.70, "entry_shares": 15.0,
        "remaining_shares": 15.0, "remaining_exit_shares": 15.0, "notional_usd": 10.50,
        "exit_order_id": "MOCK_EXIT_P1", "exit_order_status": "RESTING", "target_exit_price": 0.98,
        "candle_expiry_ts": now_t + 200.0, "zero_bid_detected_ts": now_t - 3.0,
    }
    asyncio.run(h.check_resolutions_and_manage_positions())
    assert h.active_positions["P1"]["status"] == "LIQUIDITY_CRISIS"
    assert h.active_positions["P1"]["terminal_policy"] == "DETERMINISTIC_TERMINAL_HOLD"
    assert h.risk_halt is False, "Single illiquid market must NOT globally halt the harvester!"

    # Second simultaneous market losing all bids at TTE > 120s -> systemic CLOB outage -> global risk_halt!
    h.active_positions["P2"] = dict(
        h.active_positions["P1"], trade_id="P2", market_id="M2", token_id="2" * 25,
        exit_order_id="MOCK_EXIT_P2", exit_order_status="RESTING",
        status="POSITION_CONFIRMED", zero_bid_detected_ts=now_t - 3.0,
    )
    asyncio.run(h.check_resolutions_and_manage_positions())
    assert h.risk_halt is True


def test_dual_budget_decoupling_and_bond1_single_leg_maker_unblocking(tmp_path, monkeypatch):
    import src.polymarket_research.polymarket_live_harvester as plh

    monkeypatch.setattr(plh, "DATA_DIR", tmp_path)
    monkeypatch.setattr(plh, "STATE_FILE", tmp_path / "db_state.json")

    h = PolymarketLiveHarvester(dry_run=True)
    h._last_known_collateral = 69.06
    h.risk_controller.record_trade_pnl(-21.0)
    assert h.risk_controller.is_halted() is True
    assert h.risk_controller.is_riskless_box_halted() is False
    assert h._is_d1_box_halted() is False

    # Verify BOND1 SINGLE_LEG_MAKER_LOCK dispatches in _poll_d1_live_box_candidates while 2-leg Maker Anchor stays blocked
    spawned = []
    h._spawn_live_maker_anchor_box_task = lambda c: spawned.append(c["box_type"]) or True
    cand_file = tmp_path / "d1_live_box_candidates.jsonl"
    now_t = time.time()
    cands = [
        {"emit_id": "E_2LEG", "ts_unix": now_t, "box_type": "ZERO_FEE_MAKER_ANCHOR", "dedupe_key": "DK_2LEG", "box_cost_net": 0.985, "shares": 12},
        {"emit_id": "E_BOND1", "ts_unix": now_t, "box_type": "SINGLE_LEG_MAKER_LOCK", "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY", "dedupe_key": "DK_BOND1", "box_cost_net": 0.992, "shares": 15},
    ]
    cand_file.write_text("\n".join(json.dumps(x) for x in cands) + "\n", encoding="utf-8")
    h._d1_cand_initialized = True
    h._last_d1_cand_offset = 0
    asyncio.run(h._poll_d1_live_box_candidates(now_t))
    assert spawned == ["SINGLE_LEG_MAKER_LOCK"]


def test_hot_reload_config_manager_and_fail_closed_validation(tmp_path):
    cfg_p = tmp_path / "strategy.json"
    cfg_p.write_text(json.dumps({"schema_version": "5.0.1", "directional": {"max_taker_price_1h": 0.72}}), encoding="utf-8")
    mgr = HotReloadConfigManager(config_path=cfg_p, poll_interval_sec=0.0)
    assert mgr.snapshot["directional"]["max_taker_price_1h"] == pytest.approx(0.72)

    # Out-of-range ceiling ($0.95 > $0.85 hard safety bound) MUST fail closed and retain 0.72!
    time.sleep(0.01)
    cfg_p.write_text(json.dumps({"schema_version": "5.0.2", "directional": {"max_taker_price_1h": 0.95}}), encoding="utf-8")
    changed, snap = mgr.maybe_reload(force=True)
    assert changed is False
    assert mgr.rejected_reload_count == 1
    assert snap["directional"]["max_taker_price_1h"] == pytest.approx(0.72)


def test_sol_canary_kelly_xau_recorder_and_shadow_repairs(tmp_path):
    assert MAX_MAKER_JOIN_QUEUE_USD == pytest.approx(350.0)
    assert "XAU" in ASSET_CONFIGS and ASSET_CONFIGS["XAU"]["coinbase_product"] == "USDT-USD"
    anch = compute_synthetic_xau_usd_anchor(2745.50, 1.0001)
    assert anch["valid"] is True and anch["xau_usd"] == pytest.approx(2745.775, abs=1e-3)
    rec_xau = PolymarketDualFeed1HRecorder(asset="XAU")
    rec_xau.spot_price = 3890.87
    rec_xau.coinbase_spot = 0.99875
    rec_xau.coinbase_spot_ts = time.time()
    assert rec_xau.get_coinbase_spot() == pytest.approx(3886.0064, abs=1e-3)
    assert abs(rec_xau.get_venue_divergence_bps()) < 25.0

    btc_sz = compute_stop_risk_fractional_kelly_ticket(live_equity=69.06, p_win=0.85, entry_px=0.68, asset="BTC")
    sol_sz = compute_stop_risk_fractional_kelly_ticket(live_equity=69.06, p_win=0.85, entry_px=0.68, asset="SOL")
    mkr15_sz = compute_stop_risk_fractional_kelly_ticket(
        live_equity=69.06, p_win=0.84, entry_px=0.68, is_maker=True, is_subhourly_15m=True, asset="BTC"
    )
    assert btc_sz == pytest.approx(15.19, abs=0.05)
    assert sol_sz == pytest.approx(12.91, abs=0.05)
    assert mkr15_sz == pytest.approx(12.15, abs=0.05)

    ok_fast, _ = passes_capital_velocity_hurdle(collat_usd=69.06, rem_tte_sec=8.0 * 3600, box_cost_net=0.985, box_type="BARRIER_MONO")
    ok_20h_hi, _ = passes_capital_velocity_hurdle(collat_usd=69.06, rem_tte_sec=18.0 * 3600, box_cost_net=0.940, box_type="BARRIER_MONO")
    ok_slow, _ = passes_capital_velocity_hurdle(collat_usd=69.06, rem_tte_sec=36.0 * 3600, box_cost_net=0.980, box_type="BARRIER_MONO")
    assert ok_fast is True and ok_20h_hi is True and ok_slow is False

    mgr_prod = DirectionalWfoShadowManager(tmp_path / "shdw", production_mode=True)
    assert mgr_prod.production_mode is True

    ledger_p = tmp_path / "test_promote.jsonl"
    ledger_p.write_text(
        "\n".join(json.dumps({"net_pnl_usd": x}) for x in ([4.5, 4.2, -5.0] * 25)) + "\n",
        encoding="utf-8",
    )
    rep = evaluate_ledger_file(ledger_p, min_trades=50, min_pf=1.45, max_pbo=0.20)
    assert rep["verdict"] == "PROMOTE"
    assert rep["cpcv_6_2_paths"] == "15/15"


def test_v51_unleashed_full_throttle_tiers_slots_and_box_velocity(tmp_path, monkeypatch):
    import src.polymarket_research.polymarket_live_harvester as plh

    monkeypatch.setattr(plh, "DATA_DIR", tmp_path)
    monkeypatch.setattr(plh, "STATE_FILE", tmp_path / "v51_state.json")

    # 1. Verify all 4 Sweet-Spot Balanced Compounder (v5.2) tiers & +$3.00 upward hysteresis
    p_launch = get_unleashed_v5_tier_profile(69.06)
    assert p_launch["tier"] == "UNLEASHED_LAUNCH"
    assert p_launch["alpha_notional"] == pytest.approx(0.22)
    assert p_launch["alpha_stop_risk"] == pytest.approx(0.135)
    assert p_launch["max_directional_slots"] == 4
    assert p_launch["max_daily_loss"] == pytest.approx(16.57)
    assert p_launch["d1_free_cash_pct"] == pytest.approx(0.90)
    assert p_launch["bond1_free_cash_pct"] == pytest.approx(0.78)

    # Hysteresis: $96.50 stays UNLEASHED_LAUNCH when previous_tier == UNLEASHED_LAUNCH, graduates at $98.50
    assert get_unleashed_v5_tier_profile(96.50, previous_tier="UNLEASHED_LAUNCH")["tier"] == "UNLEASHED_LAUNCH"
    p_hyper = get_unleashed_v5_tier_profile(98.50, previous_tier="UNLEASHED_LAUNCH")
    assert p_hyper["tier"] == "HYPER_GROWTH" and p_hyper["max_directional_slots"] == 4 and p_hyper["alpha_notional"] == pytest.approx(0.26)
    p_scale = get_unleashed_v5_tier_profile(300.00)
    assert p_scale["tier"] == "SCALE" and p_scale["max_directional_slots"] == 4 and p_scale["alpha_notional"] == pytest.approx(0.22)
    p_inst = get_unleashed_v5_tier_profile(1200.00)
    assert p_inst["tier"] == "INSTITUTIONAL" and p_inst["d1_free_cash_pct"] == pytest.approx(0.90) and p_inst["alpha_notional"] == pytest.approx(0.16)

    # 2. Verify live harvester slot reservation: at $69.06 (4 slots open from day 1)
    h = PolymarketLiveHarvester(dry_run=True, allowed_assets={"BTC", "SOL"})
    h.holistic_v5_live_mode = True
    h._last_known_collateral = 69.06
    lim = h._update_equity_tier(69.06)
    assert lim["tier"] == "UNLEASHED_LAUNCH"
    assert h.max_concurrent_positions == 4
    assert h._effective_directional_slot_cap() == 4
    assert h.risk_controller.min_equity_floor_usd == pytest.approx(42.0)
    assert h.risk_controller.max_consecutive_losses == 4

    # Correlation haircut on Slot #2 same-window same-direction vs $0.00 veto on opposite-direction
    now_t = time.time()
    open_pos = {
        "T1": {
            "status": "POSITION_CONFIRMED",
            "sleeve": "SLEEVE_1_CORE_302",
            "asset": "BTC",
            "target_token": "UP",
            "remaining_shares": 35.0,
            "candle_expiry_ts": now_t + 900.0,
        }
    }
    same_dir_sol = compute_stop_risk_fractional_kelly_ticket(
        live_equity=69.06, p_win=0.85, entry_px=0.68, asset="SOL",
        active_positions=open_pos, cand_expiry_ts=now_t + 900.0, cand_direction="UP",
    )
    opp_dir_sol = compute_stop_risk_fractional_kelly_ticket(
        live_equity=69.06, p_win=0.85, entry_px=0.68, asset="SOL",
        active_positions=open_pos, cand_expiry_ts=now_t + 900.0, cand_direction="DOWN",
    )
    diff_window_sol = compute_stop_risk_fractional_kelly_ticket(
        live_equity=69.06, p_win=0.85, entry_px=0.68, asset="SOL",
        active_positions=open_pos, cand_expiry_ts=now_t + 2700.0, cand_direction="DOWN",
    )
    assert same_dir_sol == pytest.approx(8.00, abs=0.10)
    assert opp_dir_sol == 0.0
    assert diff_window_sol == pytest.approx(12.91, abs=0.05)
    # Deep-ITM violent shock where erf(z) saturates to 1.0 must clamp p_win=0.995 and size full ticket (never 0.0!)
    assert compute_stop_risk_fractional_kelly_ticket(live_equity=69.06, p_win=1.0, entry_px=0.68, asset="BTC") == pytest.approx(15.19, abs=0.05)


def test_v530_eth_canary_surgical_15m_taker_z135_maker_and_mfe_ratchet(tmp_path, monkeypatch):
    from unittest.mock import MagicMock
    import src.polymarket_research.polymarket_live_harvester as plh
    from src.polymarket_research.polymarket_live_executor import ExecutionStatus, OrderResult

    monkeypatch.setattr(plh, "DATA_DIR", tmp_path)
    monkeypatch.setattr(plh, "STATE_FILE", tmp_path / "v53_state.json")
    monkeypatch.setattr(plh, "read_fast_tick", lambda *a, **kw: None)

    # 1. B1: ETH live graduation + 0.85x canary Kelly sizing (XRP stays paused)
    h = PolymarketLiveHarvester(dry_run=True, allowed_assets={"BTC", "SOL"})
    h.holistic_v5_live_mode = True
    grad = h.get_graduated_allowed_assets(69.06)
    assert {"BTC", "SOL", "ETH"}.issubset(grad) and "XRP" not in grad
    eth_sz = compute_stop_risk_fractional_kelly_ticket(live_equity=69.06, p_win=0.85, entry_px=0.68, asset="ETH")
    assert eth_sz == pytest.approx(12.91, abs=0.05)

    # 2. B2 + 1h z_immediate_taker_cut=1.35: Surgical 15m [240s, 360s] <=$0.72 Taker vs 0%-fee Maker outside window / low-z 1h
    import copy
    v530_snap = copy.deepcopy(plh.GLOBAL_GOVERNANCE_MANAGER.snapshot)
    v530_snap["schema_version"] = "5.3.0"
    v530_snap["directional"].update({
        "enable_1h_taker": True, "enable_1h_shielded_maker": True,
        "enable_15m_taker": True, "enable_15m_subordinate_maker": True,
        "min_tte_1h_sec": 150.0, "max_tte_1h_sec": 2400.0, "regime_b_max_tte_1h_sec": 600.0,
        "min_tte_15m_maker_sec": 180.0, "max_tte_15m_maker_sec": 390.0,
        "min_tte_15m_taker_sec": 240.0, "max_tte_15m_taker_sec": 360.0,
        "max_taker_price_1h": 0.74, "max_maker_price_1h": 0.76,
        "max_taker_price_15m": 0.72, "max_maker_price_15m": 0.72,
        "min_z_1h_regime_b": 0.78, "min_z_1h_regime_a": 0.85,
        "min_z_15m_maker": 0.90, "min_z_15m_taker": 0.90,
        "min_cushion_pct_1h_regime_b": 0.04, "min_cushion_pct_1h_regime_a": 0.15,
        "min_cushion_pct_15m_maker": 0.06,
    })
    v530_snap["routing"]["z_immediate_taker_cut"] = 1.35
    monkeypatch.setattr(plh.GLOBAL_GOVERNANCE_MANAGER, "_snapshot", v530_snap)
    h.dry_run = False
    h.enable_live_phase3a_maker_fallback = True
    h.executor.auth_mode = "LIVE"
    h.executor.signature_type = 2
    h.executor.is_heartbeat_healthy = lambda: True
    h.check_recorder_freshness = lambda *a, **kw: (True, 0.05, "OK")
    h._last_known_collateral = 120.0
    h.executor.get_collateral_balance = lambda *a, **kw: 120.0
    h.executor.get_conditional_balance = lambda *a, **kw: 20.0
    h.get_reference_spot_price = lambda _a: 3110.0
    h.get_usd_reference_spot_price = lambda _a: 3110.0
    monkeypatch.setenv("PM_LIVE_PHASE3A_TTL_SEC", "0.05")

    taker_calls, maker_calls = [], []

    async def _fake_snipe(**kw):
        taker_calls.append(kw)
        return OrderResult(
            success=True, order_id=f"TKR_{len(taker_calls)}", trade_id=kw["trade_id"],
            token_id=kw["token_id"], target_token=kw["target_token"], side=kw["side"],
            price=0.68, size=18.0, notional_usd=12.24, fee_usd=0.18, latency_ms=25.0,
            mode="LIVE_CLOB", execution_status=ExecutionStatus.FILLED, confirmed_onchain=True,
        )

    h.executor.execute_snipe_order_async = _fake_snipe
    h.executor.place_passive_maker_entry = lambda **kw: (maker_calls.append(kw) or {"success": True, "orderID": f"MKR_{len(maker_calls)}", "price": kw["price"], "shares": 18.0})
    h.executor.cancel_order = lambda _oid: {"is_canceled": True, "outcome": "CANCELED", "matched": 0.0}
    h.executor.get_order_fill_summary = lambda _oid, _tok: {"matched": 0.0, "terminal": True, "resting": False}
    h.executor.post_maker_exit_order = lambda **kw: {"success": True, "orderID": "EX_V53"}

    def _mk_shock(ev_id: str, m_id: str, horizon: str, tte: float, dist_pct: float, sig: float, tok_digit: str):
        now_s = time.time()
        return {
            "event_id": ev_id, "market_id": m_id, "condition_id": f"0x{m_id}", "t0_unix": now_s,
            "title": f"Ethereum Up or Down - {horizon}", "asset": "ETH", "horizon": horizon, "shock_direction": "BUY",
            "seconds_to_expiry": tte, "spot_at_t0": 3100.0 * (1.0 + dist_pct / 100.0), "trigger_price": 3100.0 * (1.0 + dist_pct / 100.0),
            "candle_open_spot": 3100.0, "twap_60s_open": 3100.0, "candle_distance_pct": dist_pct,
            "candle_sigma": sig, "shock_volume_100ms": 1_800_000.0, "shock_ofi": 0.90,
            "fee_metadata": {"fee_rate_market": 0.07, "fee_exponent": 1.0, "condition_id": f"0x{m_id}"},
            "pre_shock_features_t0": {
                "UP": {
                    "token_id": tok_digit * 26, "raw_top_asks": [[0.68, 120.0]], "raw_top_bids": [[0.66, 120.0]],
                    "effective_price_$25": 0.68, "vwap_$25": 0.68, "age_ask_ms": 250.0, "obi_l1": 0.25,
                    "age_book_ms": 20.0, "book_timestamp": now_s,
                }
            },
        }

    # 2a. ETH 15m inside [240s, 360s] (TTE=300s) @ $0.68 <= $0.72 -> immediate Taker capped at <= $0.72!
    asyncio.run(h.evaluate_shock_and_execute(_mk_shock("E_15M_IN", "9501", "15m", 300.0, 0.22, 0.0018, "7")))
    assert len(taker_calls) == 1 and len(maker_calls) == 0
    assert taker_calls[0]["max_price_ceiling"] <= 0.72
    h.active_positions.clear()

    # 2b. ETH 15m outside [240s, 360s] (TTE=200s) @ $0.68 -> strictly 0%-fee subordinate Maker <= $0.72!
    asyncio.run(h.evaluate_shock_and_execute(_mk_shock("E_15M_OUT", "9502", "15m", 200.0, 0.22, 0.0018, "8")))
    assert len(taker_calls) == 1 and len(maker_calls) == 1
    assert maker_calls[0]["price"] <= 0.72

    # 2c. ETH 1h moderate z_strike (~1.05 < 1.35) @ $0.68 -> 0%-fee Shielded Maker; high z_strike (~1.75 >= 1.35) -> immediate Taker!
    asyncio.run(h.evaluate_shock_and_execute(_mk_shock("E_1H_MODZ", "9503", "1h", 360.0, 0.16, 0.0048, "9")))
    assert len(taker_calls) == 1 and len(maker_calls) == 2
    asyncio.run(h.evaluate_shock_and_execute(_mk_shock("E_1H_HIZ", "9504", "1h", 360.0, 0.28, 0.0048, "6")))
    assert len(taker_calls) == 2 and len(maker_calls) == 2

    # 3. B3: $0.93 High-Zone MFE Profit-Lock Ratchet locks >=$0.93 peaks on 4c drop after 2.0s even when _deep_itm_z >= 1.50
    h.active_positions.clear()
    now_u = time.time()
    h.get_reference_spot_price = lambda _a: 3112.0  # deep ITM (+0.39% on TTE=90s -> _deep_itm_z > 2.0)
    h.get_usd_reference_spot_price = lambda _a: 3112.0
    h.active_positions["HZ_POS"] = {
        "trade_id": "HZ_POS", "sleeve": "SLEEVE_1_CORE_302", "market_id": "9601", "condition_id": "0x9601",
        "token_id": "3" * 28, "target_token": "UP", "asset": "ETH", "horizon": "1h", "is_subhourly": False,
        "candle_open_spot": 3100.0, "entry_spot_ref": 3108.0, "spot_denomination": "USD", "candle_sigma": 0.0050,
        "entry_price": 0.70, "entry_shares": 20.0, "gross_entry_shares": 20.0, "remaining_shares": 20.0,
        "remaining_exit_shares": 20.0, "filled_exit_shares": 0.0, "remaining_cost_basis": 14.0, "notional_usd": 14.0,
        "fee_usd": 0.0, "target_exit_price": 0.98, "entry_ts": now_u - 180.0, "candle_expiry_ts": now_u + 90.0,
        "max_seen_bid": 0.95, "status": ExecutionStatus.POSITION_CONFIRMED, "inventory_reconciled": True,
        "exit_order_id": "0xHZ_TP98", "exit_order_status": "RESTING_MAKER_POSTED", "is_liquidating": False,
    }
    h.executor.get_order_fill_summary = MagicMock(return_value={"order_id": "0xHZ_TP98", "status": "LIVE", "resting": True, "matched": 0.0, "terminal": False})
    unwind_mock = MagicMock(return_value={"success": True, "orderID": "0xHZ_UNW", "matched_size": 20.0, "taking_amount": 18.0, "fee_usd": 0.14})
    h.executor.execute_unwind_order = unwind_mock
    h.executor.get_conditional_balance = lambda *a, **kw: 0.0

    # 3a. 2c dip ($0.95 -> $0.93 > $0.91 floor) MUST NOT arm or cut clean winner!
    bk_dip2 = {"bids": [{"price": "0.93", "size": "90"}], "asks": [{"price": "0.95", "size": "90"}]}
    h.executor.get_market_book = MagicMock(return_value=bk_dip2)

    async def _bk_dip2_async(_tid):
        return bk_dip2

    h.executor.get_market_book_async = _bk_dip2_async
    asyncio.run(h.check_resolutions_and_manage_positions())
    assert unwind_mock.call_count == 0 and "trail_stop_detected_ts" not in h.active_positions["HZ_POS"]

    # 3b. >=4c drop ($0.95 -> $0.90 <= $0.91 floor) held >= 2.0s unwinds immediately via FAK (no 3s passive delay)!
    h.active_positions["HZ_POS"]["trail_stop_detected_ts"] = time.time() - 2.3
    h.active_positions["HZ_POS"]["trailing_ratchet_detected_ts"] = time.time() - 2.3
    bk_drop5 = {"bids": [{"price": "0.90", "size": "90"}], "asks": [{"price": "0.95", "size": "90"}]}
    h.executor.get_market_book = MagicMock(return_value=bk_drop5)

    async def _bk_drop5_async(_tid):
        return bk_drop5

    h.executor.get_market_book_async = _bk_drop5_async
    asyncio.run(h.check_resolutions_and_manage_positions())
    assert unwind_mock.call_count == 1
    assert len(h.closed_positions) == 1
    assert h.closed_positions[-1]["net_pnl_usd"] > 3.5
    assert h.closed_positions[-1]["exit_decomposition_bucket"] == "PROFIT_RATCHET"


def test_pre_redeemed_winning_position_not_misclassified_as_no_inventory(tmp_path, monkeypatch):
    import src.polymarket_research.polymarket_live_harvester as plh
    from src.polymarket_research.polymarket_live_executor import ExecutionStatus

    monkeypatch.setattr(plh, "DATA_DIR", tmp_path)
    monkeypatch.setattr(plh, "STATE_FILE", tmp_path / "preredeem_state.json")
    monkeypatch.setattr(plh, "read_fast_tick", lambda *a, **kw: None)

    h = PolymarketLiveHarvester(dry_run=True, allowed_assets={"BTC", "SOL", "ETH"})
    h.dry_run = False
    h.holistic_v5_live_mode = True
    h._last_known_collateral = 69.23
    h._wallet_token_balance = lambda _tok: (0.0, h.ONCHAIN_SOURCE)
    h.executor.get_onchain_erc1155_balance = lambda _tok: 0.0
    h.executor.get_current_block_number = lambda: 96572339
    h.executor.find_redemption_payouts = lambda *a, **kw: []
    h.executor.attempt_onchain_redemption = lambda *a, **kw: None

    # Case A: Confirmed CLOB BUY (22.05 sh @ $0.992), 0 SELLs, 0 ERC-1155 after YES win -> +$0.18 win (not -$21.87 loss!)
    def _fills_confirmed(tok, since_ts, side, oid):
        if side == "BUY":
            return [{"size": 22.05, "price": 0.992, "cash": 21.8736, "status": "CONFIRMED", "side": "BUY"}]
        return []

    h.executor.get_account_fills = _fills_confirmed
    pos_win = {
        "trade_id": "MKR_LOCK1_TEST_5924168",
        "box_id": "MKR_LOCK1_TEST_5924168",
        "is_single_leg_lock": True,
        "hold_to_maturity_lock": True,
        "sleeve": "BOND1_UMA_RESOLUTION_CARRY",
        "market_id": "5924168",
        "condition_id": "0x8cf4ea8b67e66bcd38f408d3cac45b3b210afba50be61893b6e5e82bc1156dee",
        "token_id": "4" * 30,
        "target_token": "YES",
        "asset": "SPORTS_TOTALS",
        "horizon": "maker_lock_1leg",
        "entry_price": 0.992,
        "entry_shares": 22.05,
        "gross_entry_shares": 22.05,
        "remaining_shares": 22.05,
        "remaining_exit_shares": 22.05,
        "filled_exit_shares": 0.0,
        "remaining_cost_basis": 21.8736,
        "notional_usd": 21.8736,
        "fee_usd": 0.0,
        "entry_fee_cash_usd": 0.0,
        "entry_ts": time.time() - 3600.0,
        "status": ExecutionStatus.POSITION_CONFIRMED,
        "exit_order_id": None,
        "exit_order_status": "DETERMINISTIC_TERMINAL_HOLD",
    }
    h.active_positions["MKR_LOCK1_TEST_5924168"] = pos_win
    asyncio.run(h._apply_market_resolution("MKR_LOCK1_TEST_5924168", pos_win, "YES"))
    assert "MKR_LOCK1_TEST_5924168" not in h.active_positions
    settled_win = h.closed_positions[-1]
    assert settled_win["won"] is True
    assert settled_win["close_reason"] == "ONCHAIN_REDEMPTION_CONFIRMED"
    assert settled_win["payout_usd"] == pytest.approx(22.05, abs=0.01)
    assert settled_win["net_pnl_usd"] == pytest.approx(0.18, abs=0.01)
    # Must NOT synthetically double-add $22.05 onto already-refreshed $69.23 wallet collateral
    assert h._last_known_collateral == pytest.approx(69.23, abs=0.01)

    # Case B: Unconfirmed/ghost BUY (0 BUY fills, 0 redemption receipts, 0 ERC-1155) -> MARKET_RESOLVED_NO_INVENTORY
    h.executor.get_account_fills = lambda *a, **kw: []
    pos_ghost = {
        "trade_id": "GHOST_BUY_TEST",
        "box_id": "GHOST_BUY_TEST",
        "is_single_leg_lock": True,
        "hold_to_maturity_lock": True,
        "sleeve": "BOND1_UMA_RESOLUTION_CARRY",
        "market_id": "5924169",
        "condition_id": "0x9cf4ea8b67e66bcd38f408d3cac45b3b210afba50be61893b6e5e82bc1156dee",
        "token_id": "5" * 30,
        "target_token": "YES",
        "asset": "SPORTS_TOTALS",
        "horizon": "maker_lock_1leg",
        "entry_price": 0.992,
        "entry_shares": 22.05,
        "gross_entry_shares": 22.05,
        "remaining_shares": 22.05,
        "remaining_exit_shares": 22.05,
        "filled_exit_shares": 0.0,
        "realized_exit_cash": 0.0,
        "confirmed_realized_cash": 0.0,
        "remaining_cost_basis": 21.8736,
        "notional_usd": 21.8736,
        "fee_usd": 0.0,
        "entry_fee_cash_usd": 0.0,
        "entry_ts": time.time() - 3600.0,
        "status": ExecutionStatus.POSITION_CONFIRMED,
        "exit_order_id": None,
        "exit_order_status": "DETERMINISTIC_TERMINAL_HOLD",
    }
    h.active_positions["GHOST_BUY_TEST"] = pos_ghost
    asyncio.run(h._apply_market_resolution("GHOST_BUY_TEST", pos_ghost, "YES"))
    settled_ghost = h.closed_positions[-1]
    assert settled_ghost["won"] is False
    assert settled_ghost["close_reason"] == "MARKET_RESOLVED_NO_INVENTORY"


def test_maker_entry_tick_size_rule_400_retries_with_resigned_tick_and_guards(monkeypatch, tmp_path):
    """
    Verifies deterministic 0-parameter handling when Polymarket's /tick-size endpoint returns
    0.001 above $0.96 while the CLOB matching engine rejects @ $0.991 with:
      PolyApiException[status_code=400, error_message={'error': 'price 0.991 breaks minimum tick size rule 0.01'}]
    Covers:
      A. Re-signs EIP-712 order with PartialCreateOrderOptions(tick_size="0.01") at $0.99 (ROUND_FLOOR)
         and pins 30s authoritative tick override so price_hint >= 0.96 cannot revert to stale 0.001.
      B. Chains cleanly into post_only non-crossing step-down ($0.99 -> $0.98) if best_ask == $0.99.
      C. Enforces min_price_floor ($0.94 on BOND1) and refuses out-of-band coarse tick (0.1 -> $0.90).
      D. Protects zero-hop post_maker_entry_order_async identically.
    """
    from types import SimpleNamespace
    import src.polymarket_research.polymarket_live_executor as ex_mod
    from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor

    class FakeOrderArgs:
        def __init__(self, price, size, side, token_id):
            self.price = price
            self.size = size
            self.side = side
            self.token_id = token_id

    class FakePartialOpts:
        def __init__(self, tick_size=None, neg_risk=None, version=None):
            self.tick_size = tick_size
            self.neg_risk = neg_risk
            self.version = version

    class FakePolyApiExc(Exception):
        def __init__(self, status_code, error_message):
            super().__init__(f"PolyApiException[status_code={status_code}, error_message={error_message}]")
            self.status_code = status_code
            self.error_message = error_message

    monkeypatch.setattr(ex_mod, "OrderArgsV2", FakeOrderArgs)
    monkeypatch.setattr(ex_mod, "PartialCreateOrderOptions", FakePartialOpts)
    monkeypatch.setattr(ex_mod, "OrderType", SimpleNamespace(GTC="GTC", FAK="FAK", FOK="FOK"))

    def _make_exec(post_fn, book_asks=None):
        ex = PolymarketLiveExecutor.__new__(PolymarketLiveExecutor)
        ex.dry_run = False
        ex.is_authenticated = True
        ex.auth_mode = "MOCK_LIVE"
        ex._tick_size_cache = {}
        ex._neg_risk_cache = {}
        ex._fee_cache = {}
        ex._log_order = lambda _res: None
        ex.get_market_book = lambda _tok: {"bids": [{"price": "0.98", "size": "100"}], "asks": book_asks or []}
        signed_calls = []

        class FakeClient:
            def __init__(self):
                self._ClobClient__tick_sizes = {}
                self._ClobClient__neg_risk = {}

            def get_tick_size(self, _tok):
                # Simulates lagging /tick-size endpoint returning 0.001 while matching engine requires 0.01
                return "0.001"

            def create_order(self, order_args, options=None):
                rec = {
                    "price": order_args.price,
                    "size": order_args.size,
                    "side": order_args.side,
                    "tick_size": getattr(options, "tick_size", None),
                    "neg_risk": getattr(options, "neg_risk", None),
                }
                signed_calls.append(rec)
                return rec

            def post_order(self, signed_ord, order_type, post_only=False, defer_exec=False):
                return post_fn(signed_ord, order_type, post_only, defer_exec)

        ex.client = FakeClient()
        return ex, signed_calls

    tok_a = "98838330768872909771006402805675604528304524418007549305891386390492235479747"

    # --- Case A: Exact BOND1 0.991 -> 0.99 retry with tick_size="0.01" re-signing ---
    attempts_a = []

    def _post_case_a(signed_ord, _ot, post_only, _de):
        assert post_only is True
        attempts_a.append(signed_ord)
        if len(attempts_a) == 1:
            assert signed_ord["price"] == pytest.approx(0.991)
            assert signed_ord["tick_size"] == "0.001"
            raise FakePolyApiExc(400, {"error": "price 0.991 breaks minimum tick size rule 0.01"})
        assert signed_ord["price"] == pytest.approx(0.99)
        assert signed_ord["tick_size"] == "0.01"
        return {"orderID": "0xBOND1_RETRY_OK", "status": "LIVE"}

    ex_a, signed_a = _make_exec(_post_case_a, book_asks=[{"price": "1.00", "size": "200"}])
    res_a = ex_a.post_maker_entry_order(
        token_id=tok_a, price=0.991, notional_usd=51.5419, side="BUY",
        neg_risk=False, min_price_floor=0.94, max_price_ceiling=0.995,
    )
    assert res_a["success"] is True
    assert res_a["orderID"] == "0xBOND1_RETRY_OK"
    assert res_a["price"] == pytest.approx(0.99)
    assert res_a["shares"] == pytest.approx(52.0)
    assert len(signed_a) == 2
    assert ex_a.client._ClobClient__tick_sizes[tok_a] == "0.01"
    # Even with price_hint >= 0.96, 30s override prevents reverting to lagging "0.001" SDK response
    assert ex_a.get_token_tick_size(tok_a, price_hint=0.991) == pytest.approx(0.01)

    # --- Case B: 0.991 tick reject + best_ask == 0.99 post_only cross -> steps down to $0.98 cleanly ---
    attempts_b = []

    def _post_case_b(signed_ord, _ot, post_only, _de):
        assert post_only is True
        attempts_b.append(signed_ord)
        if len(attempts_b) == 1:
            raise FakePolyApiExc(400, {"error": "price 0.991 breaks minimum tick size rule 0.01"})
        if len(attempts_b) == 2:
            assert signed_ord["price"] == pytest.approx(0.99)
            assert signed_ord["tick_size"] == "0.01"
            raise FakePolyApiExc(400, {"error": "invalid post-only order: order crosses book"})
        assert signed_ord["price"] == pytest.approx(0.98)
        assert signed_ord["tick_size"] == "0.01"
        return {"orderID": "0xBOND1_STEPDOWN_98", "status": "LIVE"}

    ex_b, signed_b = _make_exec(_post_case_b, book_asks=[{"price": "0.99", "size": "50"}])
    res_b = ex_b.post_maker_entry_order(
        token_id=tok_a, price=0.991, notional_usd=51.5419, side="BUY",
        neg_risk=False, min_price_floor=0.94, max_price_ceiling=0.995,
    )
    assert res_b["success"] is True
    assert res_b["orderID"] == "0xBOND1_STEPDOWN_98"
    assert res_b["price"] == pytest.approx(0.98)
    assert len(signed_b) == 3

    # --- Case C: Coarse tick 0.1 floors 0.991 -> 0.90 < min_price_floor (0.94) -> refuses retry ---
    attempts_c = []

    def _post_case_c(signed_ord, _ot, _po, _de):
        attempts_c.append(signed_ord)
        raise FakePolyApiExc(400, {"error": "price 0.991 breaks minimum tick size rule 0.1"})

    ex_c, signed_c = _make_exec(_post_case_c)
    res_c = ex_c.post_maker_entry_order(
        token_id=tok_a, price=0.991, notional_usd=51.5419, side="BUY",
        neg_risk=False, min_price_floor=0.94, max_price_ceiling=0.995,
    )
    assert res_c["success"] is False
    assert res_c["orderID"] is None
    assert res_c["outcome_unknown"] is False
    assert len(signed_c) == 1

    # --- Case D: Async zero-hop path handles 0.991 -> 0.99 tick-size 400 retry identically ---
    ex_d, _ = _make_exec(_post_case_a)
    ex_d._can_use_native_async_post_order = lambda: True
    zh_calls = []

    async def _fake_zero_hop(tok, px, sh, side, ot, create_options=None, stage=None, max_notional_usd=None, post_only=False):
        zh_calls.append({"px": px, "sh": sh, "tick": getattr(create_options, "tick_size", None), "post_only": post_only})
        if stage is not None:
            stage["submitted"] = True
            stage["signed_shares"] = sh
        if len(zh_calls) == 1:
            raise FakePolyApiExc(400, {"error": "price 0.991 breaks minimum tick size rule 0.01"})
        return {"post_resp": {"orderID": "0xASYNC_TICK_OK"}, "post_ms": 41.2, "sign_ms": 0.3}

    ex_d._sign_and_post_async_zero_hop = _fake_zero_hop
    res_d = asyncio.run(ex_d.post_maker_entry_order_async(
        token_id=tok_a, price=0.991, notional_usd=51.5419, side="BUY",
        neg_risk=False, min_price_floor=0.94, max_price_ceiling=0.995,
    ))
    assert res_d["success"] is True
    assert res_d["orderID"] == "0xASYNC_TICK_OK"
    assert res_d["price"] == pytest.approx(0.99)
    assert len(zh_calls) == 2
    assert zh_calls[0]["tick"] == "0.001" and zh_calls[1]["tick"] == "0.01"


def test_bond1_1800s_ttl_alignment_and_zero_latency_crypto_d1_preemption(tmp_path, monkeypatch):
    """
    Verifies BOND1 1800s (30m) maker lifecycle alignment with alpha-124 + zero-block preemption:
      1. Default max_keep_s with healthy User WS extends past 180s up to 1800s (capturing 3m..30m fills).
      2. Preemption cancels resting BOND1 in <120ms (BOND1_MAKER_PREEMPTED -> MAKER_TTL_QUIET / MAKER PREEMPTED)
         and automatically re-posts sized to refreshed residual collateral if free cash remains.
      3. Resting BOND1 intent (live_maker_anchor_inflight=True) does NOT inflate directional current_exposure,
         and cross-market D1 Dominance Box preempts resting BOND1 to unlock full collateral.
    """
    import src.polymarket_research.polymarket_live_harvester as plh
    from src.polymarket_research.latency_trace import classify_shock_attempt

    monkeypatch.setattr(plh, "DATA_DIR", tmp_path)
    monkeypatch.setattr(plh, "STATE_FILE", tmp_path / "bond1_1800_state.json")
    monkeypatch.setattr(plh, "read_fast_tick", lambda *a, **kw: None)

    a124_state = {
        "by_sleeve": {
            "BOND1_UMA_RESOLUTION_CARRY": {
                "closed": 21, "wins": 21, "losses": 0, "win_rate_pct": 100.0,
                "realized_pnl_t1000_usd": 8.92, "legging_adjusted_pnl_t1000_usd": 8.92,
                "quarantined": False, "grad8_live_promoted": True,
            },
            "D1_SAME_ORACLE_DOMINANCE_BOX": {
                "closed": 32, "wins": 32, "losses": 0, "win_rate_pct": 100.0,
                "realized_pnl_t1000_usd": 151.95, "legging_adjusted_pnl_t1000_usd": 151.95,
                "quarantined": False, "grad8_live_promoted": True,
            },
        },
        "by_d1_asset": {
            "BTC": {
                "closed": 12, "wins": 12, "losses": 0, "win_rate_pct": 100.0,
                "realized_pnl_t1000_usd": 52.0, "legging_adjusted_pnl_t1000_usd": 52.0, "net_pnl_t1000_usd": 52.0,
            },
        },
    }
    (tmp_path / "alpha124_shadow_state.json").write_text(json.dumps(a124_state), encoding="utf-8")

    h = PolymarketLiveHarvester(dry_run=True, allowed_assets={"BTC", "SOL", "ETH"})
    h.dry_run = False
    h._startup_reconciled = True
    h.holistic_v5_live_mode = True
    h._last_known_collateral = 69.23
    h.max_exposure = 65.0
    h.executor.auth_mode = "LIVE"
    h._wallet_token_balance = lambda _tok: (0.0, h.ONCHAIN_SOURCE)
    h.executor.invalidate_collateral_cache = lambda: None

    wtok = "7" * 32
    ltok = "8" * 32
    books = {
        wtok: {"asks": [], "bids": [{"price": "0.99", "size": "400"}]},
        ltok: {"asks": [{"price": "0.015", "size": "200"}], "bids": [{"price": "0.002", "size": "200"}]},
    }
    h.executor.get_market_book = lambda tid: books[tid]

    emitted_forensics = []
    monkeypatch.setattr(plh, "_emit_shock_attempt", lambda payload: emitted_forensics.append(payload))

    # --- 1. Default 1800s keepalive survives past 180s (3m) and captures a 330s (5.5m) WS fill ---
    import time as _std_time
    _real_mono = _std_time.monotonic
    fake_mono = {"offset": 0.0}
    monkeypatch.setattr(plh.time, "monotonic", lambda: _real_mono() + fake_mono["offset"])

    class FakeHealthyUWS:
        fill_sequence = 1

        def is_healthy(self):
            return True

        async def wait_for_fill_or_timeout(self, timeout_s, prev_seq=0):
            # Advance simulated monotonic offset by +110s per iteration: crosses 180s on step 2, fills at 330s on step 3!
            fake_mono["offset"] += 110.0
            await asyncio.sleep(0)

        def get_order_snapshot(self, oid, max_age_sec=5.0):
            if fake_mono["offset"] >= 320.0:
                return {"status": "MATCHED", "size_matched": 52.0}
            return {"status": "LIVE", "size_matched": 0.0}

    h.executor._user_ws_cache = FakeHealthyUWS()
    h.executor.post_maker_entry_order = lambda **kw: {
        "success": True, "orderID": "0xBOND1_315S", "price": 0.99, "shares": 52.0,
    }
    h.executor.cancel_order = lambda oid: {"is_canceled": False, "outcome": "FILLED", "matched": 52.0}
    h.executor.get_order_fill_summary = lambda oid, tid: (
        {"matched": 52.0, "avg_price": 0.99, "cash": 51.48, "fee": 0.0, "terminal": True}
        if fake_mono["offset"] >= 320.0
        else {"matched": 0.0, "avg_price": 0.0, "cash": 0.0, "fee": 0.0, "terminal": False}
    )

    cand_315 = {
        "box_id": "MKR_LOCK1_315S",
        "box_type": "SINGLE_LEG_MAKER_LOCK",
        "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
        "dedupe_key": "BOND1_MKR_6326001",
        "pair_dedupe_key": "BOND1_6326001",
        "asset": "SPORTS_TOTALS",
        "leg_a_market_id": "6326001",
        "leg_a_condition_id": "0xabc6326001",
        "leg_a_token_id": wtok,
        "leg_a_opp_token_id": ltok,
        "leg_a_side": "YES",
        "anchor_bid_px": 0.99,
        "min_resting_bid": 0.94,
        "max_box_cost_net": 0.994,
        "max_opp_bid": 0.008,
        "expiry_ts": time.time() + 3600.0,
        "ts_unix": time.time(),
    }
    res_315 = asyncio.run(h.maybe_execute_graduated_single_leg_maker_lock(cand_315))
    assert res_315["executed"] is True
    assert fake_mono["offset"] >= 320.0  # Proves order stayed alive well past legacy 180s cutoff!
    h.active_positions.clear()
    h._last_known_collateral = 69.23

    # Restore real monotonic clock for async preemption + repost test
    monkeypatch.setattr(plh.time, "monotonic", _real_mono)

    # --- 2. Preemption cancels BOND1 in <120ms, emits BOND1_MAKER_PREEMPTED, and re-posts on residual cash ---
    if isinstance(getattr(h, "risk_config", None), dict):
        monkeypatch.setitem(h.risk_config, "bond1_preempt_repost_delay_sec", 0.06)
    monkeypatch.setitem(plh.RISK_CONFIG, "bond1_preempt_repost_delay_sec", 0.06)

    class RealWaitUWS:
        fill_sequence = 1

        def is_healthy(self):
            return True

        async def wait_for_fill_or_timeout(self, timeout_s, prev_seq=0):
            await asyncio.sleep(min(timeout_s, 0.03))

        def get_order_snapshot(self, oid, max_age_sec=5.0):
            return {"status": "LIVE", "size_matched": 0.0}

    h.executor._user_ws_cache = RealWaitUWS()
    posted_calls = []

    def _post_seq(**kw):
        idx = len(posted_calls) + 1
        sh = int(kw["notional_usd"] // kw["price"])
        posted_calls.append({"idx": idx, "sh": sh, **kw})
        return {"success": True, "orderID": f"0xBOND1_PRE_{idx}", "price": kw["price"], "shares": float(sh)}

    h.executor.post_maker_entry_order = _post_seq
    h.executor.cancel_order = lambda oid: {"is_canceled": True, "outcome": "CANCELED", "matched": 0.0}
    h.executor.get_order_fill_summary = lambda oid, tid: {
        "matched": 0.0, "avg_price": 0.0, "cash": 0.0, "fee": 0.0, "terminal": False,
    }
    # Simulate Crypto Slot #1 having spent $14.50 while BOND1 was preempted -> $54.73 residual cash
    wallet_state = {"usdc": 69.23}
    h.executor.get_collateral_balance = lambda *a, **kw: wallet_state["usdc"]

    async def _run_preempt_and_repost():
        h._main_loop = asyncio.get_running_loop()
        cand_pre = {
            **cand_315,
            "box_id": "MKR_LOCK1_PREEMPT",
            "dedupe_key": "BOND1_MKR_6326099",
            "pair_dedupe_key": "BOND1_6326099",
            "leg_a_market_id": "6326099",
            "ts_unix": time.time(),
        }
        t1 = asyncio.create_task(h.maybe_execute_graduated_single_leg_maker_lock(cand_pre))
        for _ in range(20):
            if any(v.get("live_maker_anchor_inflight") for v in h.pending_entry_intents.values()):
                break
            await asyncio.sleep(0.01)
        assert len(posted_calls) == 1
        assert posted_calls[0]["sh"] == 54  # $69.23 * 0.78 = $54.00 -> 54 sh @ $0.99

        # Verify directional current_exposure ignores live_maker_anchor_inflight
        dir_exp = sum(
            float(i.get("notional_usd", 0.0) or 0.0)
            for k, i in h.pending_entry_intents.items()
            if k not in h._risk_bearing_positions() and not (isinstance(i, dict) and i.get("live_maker_anchor_inflight"))
        )
        assert dir_exp == pytest.approx(0.0)

        # Simulate Crypto Slot #1 taking $14.50 and signaling preemption
        wallet_state["usdc"] = 54.73
        signaled = h._preempt_resting_maker_anchors(reason="DIR_SHOCK:BTC_1h")
        assert signaled == 1
        out1 = await t1
        assert out1["executed"] is False
        assert out1["reason"] == "BOND1_MAKER_PREEMPTED"

        # Wait ~90ms for automatic residual re-post task to post BOND1 #2 sized to $54.73 * 0.78 = $42.69 (43 sh)
        for _ in range(25):
            if len(posted_calls) >= 2:
                break
            await asyncio.sleep(0.01)
        assert len(posted_calls) == 2
        assert posted_calls[1]["sh"] == 43

        # Cross-market D1 Dominance Box (market 9990001 != 6326099) preempts resting BOND1 #2 on worker thread!
        d1_tok_a = "1" * 32
        d1_tok_b = "2" * 32
        d1_opp_a = "3" * 32
        d1_opp_b = "4" * 32
        books[d1_tok_a] = {"asks": [{"price": "0.48", "size": "150"}], "bids": [{"price": "0.47", "size": "150"}]}
        books[d1_tok_b] = {"asks": [{"price": "0.49", "size": "150"}], "bids": [{"price": "0.48", "size": "150"}]}
        books[d1_opp_a] = {"asks": [{"price": "0.53", "size": "150"}], "bids": [{"price": "0.51", "size": "150"}]}
        books[d1_opp_b] = {"asks": [{"price": "0.52", "size": "150"}], "bids": [{"price": "0.50", "size": "150"}]}
        h.executor.prewarm_token_market_cache = lambda **kw: None
        h.executor.post_maker_exit_order = lambda **kw: {"success": True, "orderID": "0xD1_EX"}
        d1_call_shares = []

        def _fake_atomic_d1(**kw):
            sh_c = float(kw["shares"])
            d1_call_shares.append(sh_c)
            return {
                "success": True,
                "shares": sh_c,
                "leg_1": {"token_id": d1_tok_a, "price": 0.48, "matched_shares": sh_c, "orderID": "0xD1A"},
                "leg_2": {"token_id": d1_tok_b, "price": 0.49, "matched_shares": sh_c, "orderID": "0xD1B"},
            }

        h.executor.execute_atomic_dominance_box = _fake_atomic_d1
        d1_cand = {
            "box_id": "D1_CROSS_MKT_PREEMPT",
            "box_type": "DOMINANCE",
            "sleeve_source": "D1_SAME_ORACLE_DOMINANCE_BOX",
            "dedupe_key": "D1_BTC_9990001",
            "asset": "BTC",
            "corridor_bps": 12.0,
            "leg_a_strike": 78000.0,
            "leg_b_strike": 78100.0,
            "leg_a_side": "UP",
            "leg_b_side": "DOWN",
            "shares": 30.0,
            "box_cost_net": 0.97,
            "leg_a_market_id": "9990001",
            "leg_b_market_id": "9990002",
            "leg_a_token_id": d1_tok_a,
            "leg_b_token_id": d1_tok_b,
            "leg_a_opp_token_id": d1_opp_a,
            "leg_b_opp_token_id": d1_opp_b,
            "leg_a_limit_price": 0.48,
            "leg_b_limit_price": 0.49,
            "leg_a_fee_rate": 0.0,
            "leg_b_fee_rate": 0.0,
            "expiry_ts": time.time() + 240.0,
            "ts_unix": time.time(),
        }
        d1_out = await asyncio.to_thread(h.maybe_execute_graduated_d1_box, d1_cand)
        assert d1_out["executed"] is True
        # Without cross-market BOND1 preemption, collat_f=$14.14 (<15 sh); with preemption, collat_f=$54.73 (>=35 sh)!
        assert len(d1_call_shares) == 1 and d1_call_shares[0] >= 35.0
        # Clean up any pending background repost tasks before exiting event loop
        for tk in list(getattr(h, "_bond1_repost_bg_tasks", set())):
            tk.cancel()
        for tk in list(getattr(h, "_maker_anchor_bg_tasks", set())):
            tk.cancel()
        await asyncio.sleep(0.02)

    asyncio.run(_run_preempt_and_repost())

    preempt_evts = [e for e in emitted_forensics if e.get("stage_outcome") == "BOND1_MAKER_PREEMPTED"]
    assert len(preempt_evts) >= 1
    cls_p = classify_shock_attempt(preempt_evts[0])
    assert cls_p["speed_verdict"] == "MAKER_TTL_QUIET"
    assert cls_p["badge"] == "MAKER PREEMPTED"
    assert cls_p["is_speed_miss"] is False


def test_v531_premature_uma_veto_bond1_taker_cap_and_disputed_lock_recycle(tmp_path, monkeypatch):
    from unittest.mock import MagicMock
    import src.polymarket_research.uma_nba_endgame_engine as uee
    import src.polymarket_research.polymarket_live_harvester as plh
    from src.polymarket_research.polymarket_live_executor import ExecutionStatus, OrderResult

    monkeypatch.setattr(plh, "DATA_DIR", tmp_path)
    monkeypatch.setattr(plh, "STATE_FILE", tmp_path / "v531_state.json")
    monkeypatch.setattr(plh, "read_fast_tick", lambda *a, **kw: None)

    # 1. Premature UMA proposal submitted BEFORE endDate (Market 6476073 exact timestamps!) MUST be rejected!
    anc_raw = b"q: title: Ethereum Up or Down on November 2?, res_data: p1: 0, p2: 1, p3: 0.5. Where p1 corresponds to Down, p2 to Up"
    anc_pad = anc_raw + b"\x00" * ((32 - len(anc_raw) % 32) % 32)
    gq_words = [0] * 14
    gq_words[1] = 1793550000          # requestTimestamp
    gq_words[4] = 7200                # adapter_liveness = 2h
    gq_words[12] = 13 * 32            # ancillary offset relative to word 1
    gq_hex = "0x" + "".join(w.to_bytes(32, "big").hex() for w in gq_words) + len(anc_raw).to_bytes(32, "big").hex() + anc_pad.hex()

    rq_words = [0] * 16
    rq_words[0] = int("11" * 20, 16)  # proposer != 0
    rq_words[10] = 7200               # customLiveness = 7200s
    rq_words[11] = 10**18             # proposedPrice = 1e18 ("Up")
    rq_words[13] = 1793639523         # expiration_ts = 12:12:03 EST -> proposal_ts = 10:12:03 EST (< 12:00:00 EST endDate!)
    rq_hex = "0x" + "".join(w.to_bytes(32, "big").hex() for w in rq_words)

    def _fake_rpc(_url, payload, timeout=5.0):
        out = []
        for item in payload:
            cid = item["id"]
            if cid == 1:
                out.append({"id": 1, "result": gq_hex})
            elif cid == 2:
                out.append({"id": 2, "result": "0x" + ("00" * 12) + ("22" * 20)})
            elif cid == 10:
                out.append({"id": 10, "result": "0x" + (2).to_bytes(32, "big").hex()})
            elif cid == 11:
                out.append({"id": 11, "result": rq_hex})
        return out

    monkeypatch.setattr(uee, "_rpc_post", _fake_rpc)
    mkt_6476073 = {
        "id": "6476073",
        "question": "Ethereum Up or Down on November 2?",
        "description": "Resolves to Up if Binance.com ETH/USDT 1m close at Nov 2 12:00 ET >= Nov 1 12:00 ET.",
        "endDate": "2026-11-02T17:00:00Z",  # 1793638800
        "closed": False,
        "archived": False,
        "acceptingOrders": True,
        "umaResolutionStatus": "proposed",
        "umaResolutionStatuses": '["proposed"]',
        "resolvedBy": "0x65070be91477460d8a7aeeb94ef92fe056c2f2a7",
        "questionID": "0x" + ("ab" * 32),
        "outcomes": '["Up", "Down"]',
        "outcomePrices": '["0.995", "0.005"]',
        "clobTokenIds": json.dumps(["1" * 26, "2" * 26]),
    }
    res_premature = uee.verify_uma_onchain_proposal_sync(mkt_6476073, now_ts=1793639242.0)
    assert res_premature["verified"] is False
    assert "PREMATURE_PROPOSAL_BEFORE_END_DATE" in res_premature["reason"]

    # Valid post-endDate proposal (submitted at 17:01:00Z -> expiration 19:01:00Z) MUST verify cleanly!
    rq_words[13] = 1793638860 + 7200
    rq_hex = "0x" + "".join(w.to_bytes(32, "big").hex() for w in rq_words)
    res_valid = uee.verify_uma_onchain_proposal_sync(mkt_6476073, now_ts=1793639100.0)
    assert res_valid["verified"] is True and res_valid["win_outcome_name"] == "Up"

    # 2. _finish_single_leg_lock enforces $45.00 bond1_per_market_cap_usd on $69.48 Seed bankroll (<= $45.00, NOT 52!)
    h = PolymarketLiveHarvester(dry_run=True, allowed_assets={"BTC", "SOL", "ETH"})
    h.dry_run = False
    h.holistic_v5_live_mode = True
    h.enforce_bond1_smart_queue = True
    h.executor.auth_mode = "LIVE"
    h._last_known_collateral = 69.48
    h.executor.get_collateral_balance = lambda *a, **kw: 69.48
    h._wallet_token_balance = lambda _tok: (0.0, h.ONCHAIN_SOURCE)
    h.executor.get_token_tick_size = lambda _tok: 0.001
    h.executor.prewarm_token_market_cache = lambda **kw: None
    wtok, ltok = "7" * 26, "8" * 26
    h.executor.get_market_book = lambda tid: (
        {"asks": [{"price": "0.995", "size": "200"}], "bids": [{"price": "0.994", "size": "200"}]}
        if tid == wtok else {"asks": [{"price": "0.006", "size": "200"}], "bids": [{"price": "0.001", "size": "200"}]}
    )
    snipe_notional = []

    def _mock_snipe(**kw):
        snipe_notional.append(kw["notional_usd"])
        sh = round(kw["notional_usd"] / kw["target_price"], 2)
        return OrderResult(
            success=True, order_id="0xB1_TKR", trade_id=kw["trade_id"], token_id=kw["token_id"],
            target_token=kw["target_token"], side="BUY", price=0.995, size=sh,
            notional_usd=kw["notional_usd"], fee_usd=0.009, latency_ms=15.0,
            mode="LIVE_CLOB", execution_status=ExecutionStatus.POSITION_CONFIRMED, confirmed_onchain=True,
        )

    h.executor.execute_snipe_order = _mock_snipe
    now_t = time.time()
    out_1l = h._finish_single_leg_lock(
        cand={
            "box_id": "LOCK1_CAP_TEST", "leg_a_opp_token_id": ltok, "leg_a_condition_id": "0x6476073",
            "ts_unix": now_t, "expiry_ts": now_t + 900.0, "leg_a_fee_rate": 0.07, "leg_a_fee_exponent": 1.0,
            "max_box_cost_net": 0.9955, "max_opp_bid": 0.008, "leg_a_side": "UP", "leg_a_neg_risk": False,
        },
        sleeve_src="BOND1_UMA_RESOLUTION_CARRY", tok_a=wtok, mid_a="6476073",
        dedupe_k="BOND1_6476073", retry_cd={}, now_ts=now_t, _rcfg=h.risk_config, own_grad=True,
    )
    assert out_1l["executed"] is True
    assert len(snipe_notional) == 1 and 40.0 <= snipe_notional[0] <= 45.00

    # 3. Automatic UMA-disputed HTM lock profit-recycler unwinds 52 shares @ $0.998 -> +$0.13 net profit!
    h.active_positions.clear()
    h.closed_positions.clear()
    h.active_positions["LOCK1_DISPUTED_6476073"] = {
        "trade_id": "LOCK1_DISPUTED_6476073",
        "sleeve": "BOND1_UMA_RESOLUTION_CARRY",
        "box_type": "SINGLE_LEG_LOCK",
        "is_dominance_box": True,
        "is_single_leg_lock": True,
        "hold_to_maturity_lock": True,
        "market_id": "6476073",
        "condition_id": "0x6476073",
        "token_id": wtok,
        "target_token": "UP",
        "neg_risk": False,
        "fee_rate_market": 0.07,
        "fee_exponent": 1.0,
        "entry_price": 0.995,
        "entry_shares": 52.0,
        "gross_entry_shares": 52.0,
        "remaining_shares": 52.0,
        "remaining_exit_shares": 52.0,
        "filled_exit_shares": 0.0,
        "notional_usd": 51.74,
        "remaining_cost_basis": 51.74,
        "fee_usd": 0.0181,
        "entry_fee_cash_usd": 0.0181,
        "entry_ts": now_t - 600.0,
        "candle_expiry_ts": now_t - 120.0,
        "status": ExecutionStatus.POSITION_CONFIRMED,
        "inventory_reconciled": True,
        "exit_order_status": "DETERMINISTIC_TERMINAL_HOLD",
        "terminal_policy": "DETERMINISTIC_TERMINAL_HOLD",
        "is_liquidating": False,
    }
    gm_resp = MagicMock()
    gm_resp.json.return_value = {"id": "6476073", "closed": False, "umaResolutionStatus": "disputed"}
    h.executor._sync_session = MagicMock()
    h.executor._sync_session.get.return_value = gm_resp

    async def _disputed_bk(_tid):
        return {"bids": [{"price": "0.998", "size": "36000"}], "asks": []}

    h.executor.get_market_book_async = _disputed_bk
    h.executor.invalidate_collateral_cache = lambda: None
    h.executor.execute_unwind_order = MagicMock(
        return_value={
            "success": True, "orderID": "0xRECYCLE_6476073",
            "matched_size": 52.0, "taking_amount": 51.896, "fee_usd": 0.0073,
        }
    )
    asyncio.run(h.check_resolutions_and_manage_positions())
    assert "LOCK1_DISPUTED_6476073" not in h.active_positions
    assert len(h.closed_positions) == 1
    closed_rec = h.closed_positions[0]
    assert closed_rec["close_reason"] == "UMA_DISPUTED_LOCK_PROFIT_RECYCLE"
    assert closed_rec["won"] is True
    assert closed_rec["net_pnl_usd"] == pytest.approx(0.13, abs=0.01)


def test_v540_option_b_z90_px82_taker_only_routing(tmp_path, monkeypatch):
    import src.polymarket_research.polymarket_live_harvester as plh
    from src.polymarket_research.polymarket_live_executor import ExecutionStatus, OrderResult

    monkeypatch.setattr(plh, "DATA_DIR", tmp_path)
    monkeypatch.setattr(plh, "STATE_FILE", tmp_path / "v540_state.json")
    monkeypatch.setattr(plh, "read_fast_tick", lambda *a, **kw: None)

    plh.GLOBAL_GOVERNANCE_MANAGER.maybe_reload(force=True)
    snap = plh.GLOBAL_GOVERNANCE_MANAGER.snapshot
    assert snap["schema_version"] == "5.4.3"
    assert snap["riskless_boxes"]["reward_harvester_cap_usd_seed"] == pytest.approx(12.0)
    assert snap["directional"]["enable_1h_shielded_maker"] is False
    assert snap["directional"]["enable_15m_subordinate_maker"] is True
    assert snap["directional"]["max_taker_price_1h"] == pytest.approx(0.81)
    assert snap["directional"]["max_taker_price_15m"] == pytest.approx(0.81)
    assert snap["directional"]["max_maker_price_15m"] == pytest.approx(0.78)
    assert snap["directional"]["min_z_15m_taker"] == pytest.approx(1.20)
    assert snap["directional"]["min_z_15m_maker"] == pytest.approx(0.90)
    assert snap["directional"]["max_tte_1h_sec"] == pytest.approx(2100.0)
    assert snap["directional"]["min_cushion_pct_1h_regime_a"] == pytest.approx(0.15)
    assert snap["directional"]["min_tte_15m_taker_sec"] == pytest.approx(120.0)
    assert snap["directional"]["max_tte_15m_taker_sec"] == pytest.approx(420.0)
    assert snap["routing"]["z_immediate_taker_cut"] == pytest.approx(1.00)
    assert snap["routing"]["maker_ttl_sec"] == pytest.approx(6.0)
    assert snap["riskless_boxes"]["seed_max_lockup_hours"] == pytest.approx(8.0)
    assert snap["riskless_boxes"]["seed_min_bps_per_hour"] == pytest.approx(15.0)

    h = PolymarketLiveHarvester(dry_run=True, max_price_ceiling=0.82, max_tte=2400.0, allowed_assets={"BTC", "ETH", "SOL"})
    h.dry_run = False
    h.holistic_v5_live_mode = True
    h.enable_live_phase3a_maker_fallback = True
    h.executor.auth_mode = "LIVE"
    h.executor.signature_type = 2
    h.executor.is_heartbeat_healthy = lambda: True
    h.check_recorder_freshness = lambda *a, **kw: (True, 0.05, "OK")
    h._last_known_collateral = 69.61
    h.executor.get_collateral_balance = lambda *a, **kw: 69.61
    h.executor.get_conditional_balance = lambda *a, **kw: 20.0
    h.get_reference_spot_price = lambda _a: 70250.0
    h.get_usd_reference_spot_price = lambda _a: 70250.0

    taker_calls, maker_calls = [], []
    snipe_mode = {"miss": False}

    async def _fake_snipe(**kw):
        taker_calls.append(kw)
        if snipe_mode["miss"]:
            return OrderResult(
                success=False, order_id=None, trade_id=kw["trade_id"],
                token_id=kw["token_id"], target_token=kw["target_token"], side=kw["side"],
                price=kw["target_price"], size=0.0, notional_usd=kw["notional_usd"], fee_usd=0.0, latency_ms=22.0,
                mode="FAK_KILLED_NO_MATCH", execution_status=ExecutionStatus.REJECTED,
                details={"fak_killed": True}, error="FAK_KILLED_NO_MATCH",
            )
        return OrderResult(
            success=True, order_id=f"TKR54_{len(taker_calls)}", trade_id=kw["trade_id"],
            token_id=kw["token_id"], target_token=kw["target_token"], side=kw["side"],
            price=kw["target_price"], size=18.0, notional_usd=14.22, fee_usd=0.14, latency_ms=22.0,
            mode="LIVE_CLOB", execution_status=ExecutionStatus.FILLED, confirmed_onchain=True,
        )

    h.executor.execute_snipe_order_async = _fake_snipe
    h.executor.place_passive_maker_entry = lambda **kw: (maker_calls.append(kw) or {"success": True, "orderID": "MKR_Z_SPLIT", "price": kw["price"], "shares": 18.0})
    h.executor.cancel_order_safe = lambda _oid: True
    h.executor.get_order_fill_summary = lambda _oid, _tok: {"matched": 0.0, "terminal": True, "resting": False}
    h.executor.post_maker_exit_order = lambda **kw: {"success": True, "orderID": "EX_V54"}

    def _mk_shock(ev_id: str, m_id: str, horizon: str, tte: float, dist_pct: float, sig: float, ask_px: float, tok_digit: str):
        now_s = time.time()
        return {
            "event_id": ev_id, "market_id": m_id, "condition_id": f"0x{m_id}", "t0_unix": now_s,
            "title": f"Bitcoin Up or Down - {horizon}", "asset": "BTC", "horizon": horizon, "shock_direction": "BUY",
            "seconds_to_expiry": tte, "spot_at_t0": 70000.0 * (1.0 + dist_pct / 100.0), "trigger_price": 70000.0 * (1.0 + dist_pct / 100.0),
            "candle_open_spot": 70000.0, "twap_60s_open": 70000.0, "candle_distance_pct": dist_pct,
            "candle_sigma": sig, "shock_volume_100ms": 1_800_000.0, "shock_ofi": 0.90,
            "fee_metadata": {"fee_rate_market": 0.07, "fee_exponent": 1.0, "condition_id": f"0x{m_id}"},
            "pre_shock_features_t0": {
                "UP": {
                    "token_id": tok_digit * 26, "raw_top_asks": [[ask_px, 120.0]], "raw_top_bids": [[round(ask_px - 0.02, 2), 120.0]],
                    "effective_price_$25": ask_px, "vwap_$25": ask_px, "age_ask_ms": 250.0, "obi_l1": 0.25,
                    "age_book_ms": 20.0, "book_timestamp": now_s,
                }
            },
        }

    # 1. BTC 1h TTE=720s <= 900s (Regime B) & TTE=1200s <= 2100s (Regime A, dist=0.35% >= 0.15%) -> immediate Taker!
    asyncio.run(h.evaluate_shock_and_execute(_mk_shock("OPTB_1H_OK", "9801", "1h", 720.0, 0.25, 0.0050, 0.79, "1")))
    assert len(taker_calls) == 1 and len(maker_calls) == 0
    assert taker_calls[0]["max_price_ceiling"] <= 0.81
    h.active_positions.clear()
    h._last_known_collateral = 69.61

    asyncio.run(h.evaluate_shock_and_execute(_mk_shock("OPTB_1H_REGA", "9803", "1h", 1200.0, 0.35, 0.0050, 0.75, "3")))
    assert len(taker_calls) == 2 and len(maker_calls) == 0
    h.active_positions.clear()
    h._last_known_collateral = 69.61

    # 2. BTC 15m TTE=420s (in [120s, 420s]), z_strike ~ 1.29 >= 1.20, ask=$0.80 <= $0.81 -> executes immediate Taker!
    asyncio.run(h.evaluate_shock_and_execute(_mk_shock("OPTB_15M_OK", "9802", "15m", 420.0, 0.22, 0.0025, 0.80, "2")))
    assert len(taker_calls) == 3 and len(maker_calls) == 0
    assert taker_calls[2]["max_price_ceiling"] <= 0.81
    h.active_positions.clear()
    h._last_known_collateral = 69.61

    # 3. 15m Hybrid Rebate Z-Split (0.90 <= z < 1.20, ask=$0.75 <= $0.78) -> 0 Taker calls, routes to 0%-fee Shielded Maker!
    _orig_sleep = asyncio.sleep
    monkeypatch.setattr(asyncio, "sleep", lambda _s: _orig_sleep(0))
    asyncio.run(h.evaluate_shock_and_execute(_mk_shock("OPTB_15M_MARG_Z", "9807", "15m", 300.0, 0.15, 0.0025, 0.75, "7")))
    assert len(taker_calls) == 3 and len(maker_calls) == 1
    assert maker_calls[0]["price"] <= 0.78
    h.active_positions.clear()
    h.pending_entry_intents.clear()

    # 4. Rejects: (a) 1h TTE=2250s > 2100s, (b) 1h Regime A dist=0.10% < 0.15%, (c) z_strike ~ 0.76 < 1.00,
    #    (d) ask=$0.84 > $0.81, (e) FAK_KILLED_NO_MATCH at ask=$0.80 on 1h (0 post-FAK Maker fallback!)
    asyncio.run(h.evaluate_shock_and_execute(_mk_shock("OPTB_1H_TOO_EARLY", "9810", "1h", 2250.0, 0.45, 0.0050, 0.75, "9")))
    asyncio.run(h.evaluate_shock_and_execute(_mk_shock("OPTB_1H_REGA_SMALL_CUSH", "9811", "1h", 1200.0, 0.10, 0.0020, 0.72, "8")))
    asyncio.run(h.evaluate_shock_and_execute(_mk_shock("OPTB_LOW_Z", "9804", "1h", 600.0, 0.155, 0.0050, 0.68, "4")))
    asyncio.run(h.evaluate_shock_and_execute(_mk_shock("OPTB_HI_PX", "9805", "1h", 600.0, 0.35, 0.0050, 0.84, "5")))
    assert len(taker_calls) == 3 and len(maker_calls) == 1

    snipe_mode["miss"] = True
    asyncio.run(h.evaluate_shock_and_execute(_mk_shock("OPTB_FAK_MISS", "9806", "1h", 600.0, 0.30, 0.0050, 0.80, "6")))
    assert len(taker_calls) == 4 and len(maker_calls) == 1

