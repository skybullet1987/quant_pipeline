"""
APEX v5.0 Comprehensive Bug-Fix & Shared-Kernel Parity Test Suite
=================================================================
Verifies all 11 deterministic bug fixes and strategy parity invariants:
  1. `place_trigger_tp` limit collar direction (buy-to-close above trigger, sell-to-close below trigger).
  2. `close_position` partial-IOC remainder tracking and Stage 2/3 escalation without orphaning.
  3. Transient `502/503/504` gateway error re-raising so `call_with_gateway_retry` actually retries.
  4. `F5` (`fracdiff_orthogonal_engine.py`) and `AsymFIP` (`asym_fip.py`) `[t-lookback+1:t+1]` bar-t inclusion.
  5. `waterfill_capped_weights` iterative pro-rata redistribution without gross leverage leakage.
  6. True `0.0x` Grossman-Zhou floor when `cushion <= 0.0`.
  7. `_exit_satellite` BTC/ETH hedge unwind when core holds a larger opposing leg.
  8. `HALTED` micro-cycle read-only ledger sync without 60s IOC bracket sweeps.
  9. `arm_position_brackets` self-front-running guard when native L1 trigger is already resting.
  10. Wide `V5_CATASTROPHE_STOP` L1 brackets + `latest_atr_map` / `position_hwm_map` restart persistence.
  11. Exact `1e-12` numerical parity between `ProductionApexExecutor` and `src.strategy.apex_v5_kernel`.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.alpha.fracdiff_orthogonal_engine import compute_multi_beta_residual_momentum
from src.execution.exchange_gateway import HyperliquidGateway
from src.execution.production_apex_daemon import (
    MAX_SINGLE_ALT_WEIGHT,
    PEAK_LEVERAGE,
    STRATEGY_VERSION,
    V5_GP_KEEP_WEIGHT,
    V5_GROSSMAN_ZHOU_MAX_DD,
    V5_TARGET_PORTFOLIO_VOL_ANN,
    V5_TOP_N_MAJORS,
    V5_TURNOVER_DEADBAND_NAV,
    CircuitBreakerState,
    ProductionApexExecutor,
    call_with_gateway_retry,
)
from src.signals.asym_fip import compute_asymmetric_fip_scores
from src.strategy.apex_v5_kernel import (
    compute_apex_v5_raw_unit_weights,
    scale_and_smooth_apex_v5_weights,
    waterfill_capped_weights,
)


def _make_mock_gateway_instance():
    gw = HyperliquidGateway.__new__(HyperliquidGateway)
    gw.testnet = True
    gw.base_url = "https://api.hyperliquid-testnet.xyz"
    gw.account_address = "0x0000000000000000000000000000000000000001"
    gw.sz_decimals = {"BTC": 5, "ETH": 4, "SOL": 2, "XMR": 2}
    gw.info = MagicMock()
    gw.exchange = MagicMock()
    return gw


def test_place_trigger_tp_limit_collar_direction():
    gw = _make_mock_gateway_instance()
    gw.exchange.order.return_value = {
        "status": "ok",
        "response": {"data": {"statuses": [{"resting": {"oid": 701}}]}},
    }

    # Closing a LONG (`is_buy_to_close=False`, selling at TP = $110): marketable limit collar MUST be <= $110 (0.97 * 110)
    gw.place_trigger_tp("SOL", False, 2.0, 110.0)
    args_long_tp, _ = gw.exchange.order.call_args
    limit_px_long_tp = float(args_long_tp[3])
    assert limit_px_long_tp < 110.0
    assert abs(limit_px_long_tp - 110.0 * 0.970) < 0.2

    # Closing a SHORT (`is_buy_to_close=True`, buying at TP = $90): marketable limit collar MUST be >= $90 (1.03 * 90)
    gw.place_trigger_tp("SOL", True, 2.0, 90.0)
    args_short_tp, _ = gw.exchange.order.call_args
    limit_px_short_tp = float(args_short_tp[3])
    assert limit_px_short_tp > 90.0
    assert abs(limit_px_short_tp - 90.0 * 1.030) < 0.2


def test_close_position_partial_ioc_escalates_only_unfilled_remainder():
    gw = _make_mock_gateway_instance()
    gw.get_mid_price = MagicMock(return_value=100.0)

    # Stage 1 fills only 4.00 out of 10.00 SOL; Stage 2 fills remaining 6.00 SOL
    stage1_partial = {
        "status": "ok",
        "response": {"data": {"statuses": [{"filled": {"totalSz": "4.0", "oid": 11}}]}},
    }
    stage2_remainder = {
        "status": "ok",
        "response": {"data": {"statuses": [{"filled": {"totalSz": "6.0", "oid": 12}}]}},
    }
    gw.exchange.order.side_effect = [stage1_partial, stage2_remainder]

    res = gw.close_position("SOL", size=10.0, is_long=True)
    assert gw.exchange.order.call_count == 2
    first_call_sz = float(gw.exchange.order.call_args_list[0][0][2])
    second_call_sz = float(gw.exchange.order.call_args_list[1][0][2])
    assert abs(first_call_sz - 10.0) < 1e-6
    assert abs(second_call_sz - 6.0) < 1e-6
    assert res["response"]["data"]["statuses"][0]["filled"]["oid"] == 12


def test_gateway_transient_502_reraises_and_call_with_gateway_retry_recovers():
    gw = _make_mock_gateway_instance()
    gw.exchange.order.side_effect = [
        RuntimeError("502 Bad Gateway: CloudFlare upstream error"),
        {"status": "ok", "response": {"data": {"statuses": [{"resting": {"oid": 999}}]}}},
    ]

    with patch("src.execution.production_apex_daemon.time.sleep"):
        res = call_with_gateway_retry(gw.place_trigger_stop, "SOL", False, 5.0, 90.0, base_delay=0.01)

    assert gw.exchange.order.call_count == 2
    assert res["status"] == "ok"
    assert res["response"]["data"]["statuses"][0]["resting"]["oid"] == 999


def test_f5_and_asym_fip_include_completed_bar_t():
    rng = np.random.default_rng(7)
    n_bars, n_syms = 35, 12
    rets_a = rng.normal(0.0, 0.015, (n_bars, n_syms))
    btc_r = rets_a[:, 0].copy()
    eth_r = rets_a[:, 1].copy()
    mask = np.ones((n_bars, n_syms), dtype=bool)

    rets_b = rets_a.copy()
    # Shock completed bar t = 34 on symbol 5
    rets_b[34, 5] += 0.25

    f5_a, res_a = compute_multi_beta_residual_momentum(rets_a, btc_r, eth_r, mask, lookback_h=18)
    f5_b, res_b = compute_multi_beta_residual_momentum(rets_b, btc_r, eth_r, mask, lookback_h=18)

    # Strict causality prior to t=34 AND immediate inclusion of completed bar t=34
    np.testing.assert_allclose(f5_a[:34], f5_b[:34], rtol=1e-12)
    np.testing.assert_allclose(res_a[:34], res_b[:34], rtol=1e-12)
    assert abs(res_b[34, 5] - res_a[34, 5]) > 0.15
    assert f5_b[34, 5] > f5_a[34, 5]

    fip_a = compute_asymmetric_fip_scores(res_a, np.full_like(f5_a, 2.0), mask, lookback=18)
    fip_b = compute_asymmetric_fip_scores(res_b, np.full_like(f5_b, 2.0), mask, lookback=18)
    np.testing.assert_allclose(fip_a[:34], fip_b[:34], rtol=1e-12)
    # Single-bar +25% pump at bar 34 increases max_pos/sum|eps| -> stronger long wick penalty at bar 34
    assert fip_b[34, 5] < fip_a[34, 5]


def test_waterfill_capped_weights_preserves_target_exposure():
    raw = np.array([10.0, 1.0, 1.0])
    w = waterfill_capped_weights(raw, target_sum=0.50, cap=0.25)
    assert abs(np.sum(w) - 0.50) < 1e-9
    assert abs(w[0] - 0.25) < 1e-9
    assert abs(w[1] - 0.125) < 1e-9
    assert abs(w[2] - 0.125) < 1e-9


def test_grossman_zhou_true_zero_floor_at_cushion_zero():
    raw_w = np.array([0.0, 0.30, -0.30, 0.20])
    prev_w = np.array([0.0, 0.25, -0.25, 0.15])
    betas = np.array([1.0, 1.1, 1.2, 0.9])
    vol_bar = np.array([0.015, 0.025, 0.028, 0.022])
    idio_vol = np.array([0.0, 0.020, 0.022, 0.018])

    # Equity down 26% vs HWM ($740 vs $1000) with gz_max_dd = 25% -> cushion == 0.0 -> strictly 0.0x!
    w_zero, gross_zero, cushion = scale_and_smooth_apex_v5_weights(
        raw_w=raw_w,
        prev_w=prev_w,
        betas=betas,
        vol_bar=vol_bar,
        idio_vol=idio_vol,
        btc_idx=0,
        current_equity=740.0,
        historical_hwm=1000.0,
        gz_max_dd=0.25,
    )
    assert cushion == 0.0
    assert gross_zero == 0.0
    assert np.all(w_zero == 0.0)


def test_exit_satellite_unwinds_hedge_when_core_holds_opposing_leg(tmp_path):
    ex = ProductionApexExecutor(
        testnet=False,
        dry_run=True,
        acquire_lock=False,
        journal_path=tmp_path / "j.jsonl",
        state_path=tmp_path / "s.json",
    )
    now_ms = int(time.time() * 1000)
    # Seed a larger core SHORT on BTC (-0.020 BTC @ $80,000 = -$1,600)
    ex.journal.append_event(
        "FILL_RECONCILED",
        {
            "fill_key": f"DRY_BTC_SHORT_{now_ms}",
            "coin": "BTC",
            "oid": 1,
            "tid": 1,
            "time_ms": now_ms,
            "closed_pnl": 0.0,
            "fee": 0.0,
            "px": 80000.0,
            "sz": 0.020,
            "side": "SELL",
        },
    )
    ex.state = ex.journal.replay_and_project()
    ex.state.frozen_target_weights["BTC"] = -1.60

    gw = MagicMock()
    gw.sz_decimals = {"BTC": 5, "ETH": 4, "XMR": 2}
    gw.get_mid_price.side_effect = lambda s: {"BTC": 80000.0, "ETH": 2500.0, "XMR": 500.0}[s]
    ex.gateway = gw

    rng = np.random.default_rng(11)
    btc_r = rng.normal(0, 0.01, 100)
    eth_r = rng.normal(0, 0.01, 100)
    xmr_r = 1.0 * btc_r + rng.normal(0, 0.002, 100)
    rets = np.column_stack([btc_r, eth_r, xmr_r])

    assert ex._open_satellite("XMR", -0.10, 1000.0, rets, ["BTC", "ETH", "XMR"], 0, 1)
    # BTC position is still net negative (~ -0.01875), opposite sign to the +0.00125 BTC satellite hedge!
    assert ex.state.paper_positions["BTC"]["size"] < 0.0
    assert ex.state.satellites["XMR"]["hedges"]["BTC"] > 0.0

    assert ex._exit_satellite("XMR", "dwell expired", {})
    assert "XMR" not in ex.state.paper_positions
    # Core -0.020 BTC short must be restored cleanly instead of skipping the unwind!
    assert abs(ex.state.paper_positions["BTC"]["size"] - (-0.020)) < 1e-6


def test_halted_micro_cycle_reconciles_readonly_without_ioc_bracket_sweeps(tmp_path):
    ex = ProductionApexExecutor(
        testnet=True,
        dry_run=False,
        acquire_lock=False,
        journal_path=tmp_path / "j.jsonl",
        state_path=tmp_path / "s.json",
    )
    ex.journal.append_event("EPOCH_INIT", {"initial_equity": 600.0, "hwm": 600.0, "epoch_start_ms": 1000})
    ex.journal.append_event("CIRCUIT_BREAKER", {"state": "HALTED", "reason": "Prior fault"})
    ex.state = ex.journal.replay_and_project()
    assert ex.state.circuit_breaker == CircuitBreakerState.HALTED

    gw = MagicMock()
    gw.account_address = "0xabc"
    gw.get_account_state.return_value = (595.0, 595.0, {})
    gw.info.user_state.return_value = {"assetPositions": []}
    gw.info.user_fills_by_time.return_value = [
        {
            "coin": "SOL",
            "oid": 55,
            "tid": 56,
            "time": 2000,
            "px": "150.0",
            "sz": "1.0",
            "side": "B",
            "closedPnl": "-4.80",
            "fee": "0.20",
        }
    ]
    gw.info.post.return_value = []
    ex.gateway = gw
    ex.check_clock_drift = MagicMock(return_value=True)
    ex.arm_position_brackets = MagicMock()

    ex.execute_micro_risk_cycle()

    # Bracket arming / IOC sweeps MUST NOT run while HALTED, but on-chain fill MUST be journaled!
    assert ex.arm_position_brackets.call_count == 0
    assert gw.place_alo_order.call_count == 0
    assert abs(ex.state.cumulative_realized_pnl - (-4.80)) < 1e-6
    assert ex.state.circuit_breaker == CircuitBreakerState.HALTED
    assert (tmp_path / "s.json").exists()


def test_do_arm_prevents_self_front_running_and_persists_catastrophe_atr(tmp_path):
    j_path = tmp_path / "j.jsonl"
    s_path = tmp_path / "s.json"
    ex = ProductionApexExecutor(
        testnet=True,
        dry_run=False,
        acquire_lock=False,
        journal_path=j_path,
        state_path=s_path,
    )
    ex.journal.append_event("EPOCH_INIT", {"initial_equity": 1000.0, "hwm": 1000.0, "epoch_start_ms": 1000})
    ex.state = ex.journal.replay_and_project()
    ex.latest_atr_map = {"SOL": 2.50}  # 2.5% of $100 -> 5*ATR = 12.5% catastrophe stop ($87.50)
    ex.position_hwm_map = {"SOL": 104.0}

    gw = MagicMock()
    gw.sz_decimals = {"SOL": 2}
    # Mark is $87.40 (tiny 0.11% dip below $87.50 resting L1 stop — < 0.50% emergency threshold)
    gw.get_account_state.return_value = (
        1000.0,
        1000.0,
        {"SOL": {"size": 2.0, "entry_px": 100.0, "mark_px": 87.40}},
    )
    gw.get_frontend_open_orders.return_value = [
        {"oid": 301, "coin": "SOL", "isTrigger": True, "orderType": "Stop Market", "tpsl": "sl", "sz": "2.0", "triggerPx": "87.5"},
        {"oid": 302, "coin": "SOL", "isTrigger": True, "orderType": "Take Profit Market", "tpsl": "tp", "sz": "2.0", "triggerPx": "135.0"},
    ]
    ex.gateway = gw

    armed = ex.arm_position_brackets()
    assert armed["SOL"]["sl_armed"] is True
    assert armed["SOL"]["ratchet_stage"] == "V5_CATASTROPHE_STOP"
    # Native L1 trigger must NOT be cancelled or front-run by an IOC market dump!
    assert gw.close_position.call_count == 0
    assert gw.exchange.cancel.call_count == 0

    ex.save_materialized_state_cache({"SOL": {"size": 2.0}}, armed)
    ex2 = ProductionApexExecutor(
        testnet=True,
        dry_run=False,
        acquire_lock=False,
        journal_path=j_path,
        state_path=s_path,
    )
    assert ex2.latest_atr_map.get("SOL") == 2.50
    assert ex2.position_hwm_map.get("SOL") == 104.0


def test_exact_numerical_parity_between_live_executor_and_v5_kernel(tmp_path):
    assert STRATEGY_VERSION == "v5.0.0-two-sleeve-majors"
    ex = ProductionApexExecutor(
        testnet=False,
        dry_run=True,
        acquire_lock=False,
        journal_path=tmp_path / "j.jsonl",
        state_path=tmp_path / "s.json",
    )
    ex.state.current_strategy_equity = 960.0
    ex.state.historical_hwm = 1000.0
    ex.state.frozen_target_weights = {"BTC": 0.20, "SOL": 0.15, "ADA": -0.12}

    rng = np.random.default_rng(2026)
    n_bars = 210
    symbols = [
        "BTC", "ETH", "SOL", "XRP", "BNB", "DOGE", "SUI", "AVAX", "LINK", "LTC",
        "AAVE", "NEAR", "UNI", "APT", "ARB", "ADA", "DOT", "OP", "INJ", "TIA",
    ]
    n_syms = len(symbols)
    close_mat = np.zeros((n_bars, n_syms))
    vol_mat = np.zeros((n_bars, n_syms))
    btc_rets = rng.normal(0.001, 0.015, n_bars)
    close_mat[:, 0] = 60000.0 * np.exp(np.cumsum(btc_rets))
    vol_mat[:, 0] = 5000.0
    for j in range(1, n_syms):
        drift = 0.0025 if j <= 8 else (-0.0020 if j >= 13 else 0.0)
        r_j = 0.9 * btc_rets + drift + rng.normal(0.0, 0.018, n_bars)
        close_mat[:, j] = 100.0 * np.exp(np.cumsum(r_j))
        vol_mat[:, j] = float(25 - j) * 50_000.0

    valid_mask = np.ones((n_bars, n_syms), dtype=bool)
    atr_mat = close_mat * 0.02
    funding = np.linspace(-0.00003, 0.00005, n_syms)

    live_w, live_lev, live_cush, longs, shorts, locks = ex.compute_exp103_signals_and_weights(
        close_mat=close_mat,
        atr_mat=atr_mat,
        funding_rates=funding,
        valid_mask=valid_mask,
        symbols=symbols,
        btc_idx=0,
        eth_idx=1,
        vol_mat=vol_mat,
    )

    raw_w, betas, vol_bar, idio_vol, _, _ = compute_apex_v5_raw_unit_weights(
        close_mat=close_mat,
        valid_mask=valid_mask,
        funding_rates_1h=funding,
        symbols=symbols,
        btc_idx=0,
        eth_idx=1,
        vol_mat=vol_mat,
        top_n=V5_TOP_N_MAJORS,
        max_single_alt_weight=MAX_SINGLE_ALT_WEIGHT,
    )
    prev_w = np.array([float(ex.state.frozen_target_weights.get(s, 0.0)) for s in symbols])
    kern_w_arr, kern_lev, kern_cush = scale_and_smooth_apex_v5_weights(
        raw_w=raw_w,
        prev_w=prev_w,
        betas=betas,
        vol_bar=vol_bar,
        idio_vol=idio_vol,
        btc_idx=0,
        current_equity=960.0,
        historical_hwm=1000.0,
        target_vol_ann=V5_TARGET_PORTFOLIO_VOL_ANN,
        max_gross_leverage=PEAK_LEVERAGE,
        gz_max_dd=V5_GROSSMAN_ZHOU_MAX_DD,
        gp_keep=V5_GP_KEEP_WEIGHT,
        deadband_nav=V5_TURNOVER_DEADBAND_NAV,
        max_single_alt_weight=MAX_SINGLE_ALT_WEIGHT,
    )
    kern_w = {symbols[i]: float(kern_w_arr[i]) for i in range(n_syms) if abs(kern_w_arr[i]) >= 0.002}

    assert abs(live_lev - kern_lev) < 1e-12
    assert abs(live_cush - kern_cush) < 1e-12
    assert set(live_w.keys()) == set(kern_w.keys())
    for k in kern_w:
        assert abs(live_w[k] - kern_w[k]) < 1e-12
    assert set(locks.keys()) == (set(longs) | set(shorts))


def test_close_position_survives_one_sided_empty_orderbook():
    """Verify close_position does not crash when one side of L2 book is empty and escalates to Stage 3 GTC."""
    gw = HyperliquidGateway.__new__(HyperliquidGateway)
    gw.testnet = True
    gw.sz_decimals = {"HYPE": 2}
    gw.meta = {"universe": [{"name": "HYPE", "szDecimals": 2}]}

    class DummyInfo:
        def l2_snapshot(self, symbol):
            # Ask book is completely empty (exact Testnet HYPE failure mode)
            return {"levels": [[{"px": "55.164", "sz": "1.0"}], []]}

        def meta_and_asset_ctxs(self):
            return ({"universe": [{"name": "HYPE"}]}, [{"oraclePx": "77.658"}])

    calls = []

    class DummyExchange:
        def order(self, symbol, is_buy, sz, px, order_type, reduce_only=False, cloid=None):
            calls.append((symbol, is_buy, sz, px, order_type, reduce_only))
            if order_type == {"limit": {"tif": "Ioc"}}:
                return {"status": "ok", "response": {"data": {"statuses": [{"error": "Order could not immediately match against any resting orders."}]}}}
            return {"status": "ok", "response": {"data": {"statuses": [{"resting": {"oid": 999111}}]}}}

    gw.info = DummyInfo()
    gw.exchange = DummyExchange()

    # Closing a short (-0.28 HYPE) -> is_long=False -> is_buy_to_close=True
    res = gw.close_position("HYPE", 0.28, is_long=False)
    assert res["status"] == "ok"
    assert len(calls) == 3  # Stage 1 IOC -> Stage 2 IOC -> Stage 3 GTC reduce_only
    assert calls[-1][4] == {"limit": {"tif": "Gtc"}}
    assert calls[-1][5] is True


def test_trip_halt_cancels_resting_makers_and_persists_state(tmp_path):
    """Verify trip_halt immediately cancels resting non-trigger entry orders and flushes HALTED state JSON."""
    ex = ProductionApexExecutor(
        testnet=True,
        dry_run=False,
        acquire_lock=False,
        journal_path=tmp_path / "j_halt.jsonl",
        state_path=tmp_path / "s_halt.json",
    )
    gw = MagicMock()
    gw.cancel_stale_maker_orders.return_value = 3
    gw.get_account_state.return_value = (612.63, 560.0, {})
    ex.gateway = gw
    ex.trip_halt("Simulated protection fault")
    gw.cancel_stale_maker_orders.assert_called_once()
    assert ex.state.circuit_breaker == CircuitBreakerState.HALTED
    saved = json.loads(ex.state_file.read_text())
    assert saved["circuit_breaker"] == "HALTED"

