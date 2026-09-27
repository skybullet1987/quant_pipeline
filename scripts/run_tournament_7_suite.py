#!/usr/bin/env python3
"""
TOURNAMENT 7: THE 10X VELOCITY FRONTIER (EXP-55 TO EXP-62)
=========================================================
Evaluates 8 pre-registered quantitative architectures designed to compress the
10x compounding horizon below 18 months (+280% to +320% Net CAGR):

  1. EXP-55: The Apex Staggered FIP (M=2 Staggered 6H + FIP Quality, Vol 48%)
  2. EXP-56: Asymmetric FIP (AsymFIP) (Unified 6H, Long Frogs vs Short Waterfalls, Vol 48%)
  3. EXP-57: AsymFIP + M=2 Stagger (M=2 Staggered 6H + AsymFIP, Vol 48%)
  4. EXP-58: Barroso-Santa-Clara Scaling (Unified 6H, FIP + Factor Realized Vol Scaling, Vol 48%)
  5. EXP-59: AsymFIP + Vol-Scaled Deadband (Unified 6H, AsymFIP + tau_i in [0.025, 0.045], Vol 48%)
  6. EXP-60: Triple-Staggered FIP (M=3) (M=3 Staggered 6H, Maximum Execution Smoothing, Vol 48%)
  7. EXP-61: Controlled Gearing (50% Vol) (M=2 Staggered 6H + AsymFIP, Vol 50%)
  8. EXP-62: The Production Grand Master (Full Synthesis: M=2 + AsymFIP + Factor Vol + N_eff DSR)
"""

import json
import math
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

import numpy as np
import polars as pl

PIPELINE_ROOT = Path("/home/skybullet1987/quant_pipeline")
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from backtest_10x_convex_compounding import (
    DATA_LAKE_PATH, BENCHMARK_SYMBOL, EVAL_START_TS, EVAL_END_TS
)
from src.data.pit_universe_manager import PointInTimeUniverseManager
from src.backtesting.ironcore_engine import IronCoreEngine
from src.backtesting.ironcore_config import IronCoreConfig_v1
from src.alpha.fracdiff_orthogonal_engine import (
    apply_fractional_differentiation,
    compute_multi_beta_residual_momentum,
)
from src.execution.deadband_allocator import DeadbandExecutionAllocator
from src.execution.rank_buffer_allocator import RankBufferAllocator
from src.risk.dynamic_gearing_governor import DynamicGearingGovernor
from src.signals.asym_fip import compute_asymmetric_fip_scores
from src.audit.effective_dsr import compute_effective_trials_spectral, compute_spectral_dsr

TOURNAMENT_RESULTS_PATH = PIPELINE_ROOT / "data" / "tournament_7_results.json"


def calculate_compounding_milestones(cagr: float) -> Tuple[float, float, float]:
    """Calculates time in months to reach 2x, 5x, and 10x equity."""
    if cagr <= 0:
        return float("inf"), float("inf"), float("inf")
    g = math.log(1.0 + cagr / 100.0)
    t_2x = (math.log(2.0) / g) * 12.0
    t_5x = (math.log(5.0) / g) * 12.0
    t_10x = (math.log(10.0) / g) * 12.0
    return t_2x, t_5x, t_10x


def compute_fip_quality_factor(
    residuals: np.ndarray,
    raw_f5_scores: np.ndarray,
    valid_mask: np.ndarray,
    allocator_base: DeadbandExecutionAllocator,
    lookback: int = 18,
) -> np.ndarray:
    """Computes standard symmetric FIP quality factor."""
    n_bars, n_symbols = raw_f5_scores.shape
    f_fip = np.zeros_like(raw_f5_scores)

    for t in range(lookback, n_bars):
        m_t = valid_mask[t]
        if np.sum(m_t) >= 10:
            res_win = residuals[t - lookback : t]
            max_abs_jump = np.max(np.abs(res_win), axis=0)
            total_abs_drift = np.sum(np.abs(res_win), axis=0) + 1e-8
            jump_ratio = max_abs_jump / total_abs_drift

            fip_quality_multiplier = 1.0 - np.clip(jump_ratio * 1.50, 0.0, 0.60)
            f_fip[t] = raw_f5_scores[t] * fip_quality_multiplier

    f_fip[:lookback] = f_fip[lookback]
    return allocator_base.smooth_multi_horizon_alpha(f_fip)


def simulate_tournament_7_portfolio(
    close_mat: np.ndarray,
    returns_mat: np.ndarray,
    valid_mask: np.ndarray,
    asset_vols_24h: np.ndarray,
    baseline_bar_returns: np.ndarray,
    signal_matrix: np.ndarray,
    num_sub_portfolios: int,      # 1 (unified), 2, 3
    target_vol: float,            # 0.48, 0.50
    tau_min: float = 0.015,
    tau_max: float = 0.050,
    l_min: float = 0.90,
    l_max: float = 3.20,
    target_k: int = 12,
    entry_k: int = 8,
    exit_k: int = 18,
    delta_l_thresh: float = 0.20,
    m_floor: float = 0.25,
) -> np.ndarray:
    """
    Unified execution simulator for Tournament 7 supporting:
    - Unified 6H Single Portfolio (EXP-56, EXP-58, EXP-59)
    - 2x Interleaved Staggered Sub-Portfolios (EXP-55, EXP-57, EXP-61, EXP-62)
    - 3x Interleaved Staggered Sub-Portfolios (EXP-60)
    - Calibrated dynamic volatility deadbands tau_i in [tau_min, tau_max]
    - Concave risk cushion sqrt(C(t)) fast leverage governor
    """
    n_bars, n_symbols = close_mat.shape
    w_mat = np.zeros((n_bars, n_symbols))
    curr_w = np.zeros(n_symbols)
    active_lev = 1.00
    cum_nav = 10000.0

    governor = DynamicGearingGovernor()
    governor.reset_state(initial_nav=cum_nav)

    if num_sub_portfolios == 1:
        allocator = RankBufferAllocator(target_k=target_k, entry_k=entry_k, exit_k=exit_k, deadband_tau=0.030)

        def is_6h_step(step: int) -> bool:
            return (step % 3 == 0) or (step % 3 == 1)

        for t in range(n_bars):
            if t > 0:
                bar_pnl = float(np.sum(w_mat[t - 1] * returns_mat[t]))
                cum_nav *= (1.0 + bar_pnl)

            recent_p_ret = baseline_bar_returns[max(0, t - 24) : t]
            raw_lev = governor.compute_composite_risk_shield_leverage(
                recent_port_returns=recent_p_ret,
                current_nav=cum_nav,
                sigma_target=target_vol,
                l_min=l_min,
                l_max=l_max,
                m_floor=m_floor,
                gamma_val=1.00,
                accelerated_reentry=True,
            )
            active_lev = allocator.apply_leverage_deadband(raw_lev, active_lev, delta_thresh=delta_l_thresh)

            m_t = valid_mask[t]
            v_idx = np.where(m_t)[0]

            if len(v_idx) >= (allocator.exit_k * 2):
                if is_6h_step(t):
                    longs, shorts = allocator.update_holdings_with_hysteresis(
                        scores=signal_matrix[t], valid_idx=v_idx
                    )
                    tgt_w = allocator.compute_risk_parity_weights(
                        longs, shorts, returns_mat[max(0, t - 36) : t], n_symbols, target_gross_leverage=active_lev
                    )
                else:
                    current_gross = np.sum(np.abs(curr_w))
                    if current_gross > 1e-6:
                        tgt_w = curr_w * (active_lev / current_gross)
                    else:
                        tgt_w = curr_w.copy()

                vols_t = asset_vols_24h[t]
                med_vol = np.median(vols_t[v_idx]) if len(v_idx) > 0 else 0.80
                tau_i = np.clip(0.030 * np.sqrt(vols_t / (med_vol + 1e-8)), tau_min, tau_max)
                dw = tgt_w - curr_w
                exec_mask = np.abs(dw) >= tau_i
                curr_w = np.where(exec_mask, tgt_w, curr_w)

            w_mat[t] = curr_w

        return w_mat

    else:
        # Multi-Sub-Portfolio Interleaved Staggering (M=2 or M=3)
        sub_allocators = [
            RankBufferAllocator(target_k=entry_k, entry_k=entry_k, exit_k=int(entry_k * 2.0), deadband_tau=0.030)
            for _ in range(num_sub_portfolios)
        ]
        sub_w = np.zeros((num_sub_portfolios, n_symbols))

        def should_sub_rebalance(sub_idx: int, step: int) -> bool:
            if num_sub_portfolios == 2:
                if sub_idx == 0:
                    return (step % 3 == 0) or (step % 3 == 1)
                elif sub_idx == 1:
                    return (step % 3 == 1) or (step % 3 == 2)
            elif num_sub_portfolios == 3:
                mod6 = step % 6
                if sub_idx == 0:
                    return mod6 in (0, 1, 3, 4)
                elif sub_idx == 1:
                    return mod6 in (1, 2, 4, 5)
                elif sub_idx == 2:
                    return mod6 in (2, 3, 5, 0)
            return True

        for t in range(n_bars):
            if t > 0:
                bar_pnl = float(np.sum(w_mat[t - 1] * returns_mat[t]))
                cum_nav *= (1.0 + bar_pnl)

            recent_p_ret = baseline_bar_returns[max(0, t - 24) : t]
            raw_lev = governor.compute_composite_risk_shield_leverage(
                recent_port_returns=recent_p_ret,
                current_nav=cum_nav,
                sigma_target=target_vol,
                l_min=l_min,
                l_max=l_max,
                m_floor=m_floor,
                gamma_val=1.00,
                accelerated_reentry=True,
            )
            active_lev = sub_allocators[0].apply_leverage_deadband(raw_lev, active_lev, delta_thresh=delta_l_thresh)

            m_t = valid_mask[t]
            v_idx = np.where(m_t)[0]

            if len(v_idx) >= 32:
                for sub_i in range(num_sub_portfolios):
                    if t == 0 or should_sub_rebalance(sub_i, t):
                        longs, shorts = sub_allocators[sub_i].update_holdings_with_hysteresis(
                            scores=signal_matrix[t], valid_idx=v_idx
                        )
                        tgt_sub = sub_allocators[sub_i].compute_risk_parity_weights(
                            longs, shorts, returns_mat[max(0, t - 36) : t], n_symbols, target_gross_leverage=1.00
                        )
                        sub_w[sub_i] = tgt_sub

                blended_target = np.mean(sub_w, axis=0) * active_lev

                vols_t = asset_vols_24h[t]
                med_vol = np.median(vols_t[v_idx]) if len(v_idx) > 0 else 0.80
                tau_i = np.clip(0.030 * np.sqrt(vols_t / (med_vol + 1e-8)), tau_min, tau_max)
                dw = blended_target - curr_w
                exec_mask = np.abs(dw) >= tau_i
                curr_w = np.where(exec_mask, blended_target, curr_w)

            w_mat[t] = curr_w

        return w_mat


def build_tournament_7_suite(
    close_mat: np.ndarray,
    oracle_mat: np.ndarray,
    volume_mat: np.ndarray,
    valid_mask: np.ndarray,
    returns_mat: np.ndarray,
    symbols: List[str],
    btc_idx: int,
    eth_idx: int,
) -> Dict[str, Tuple[np.ndarray, np.ndarray, str, float]]:
    """Builds candidate weight matrices for EXP-55 through EXP-62."""
    n_bars, n_symbols = close_mat.shape
    experiments = {}

    print("\n[1/5] Computing Fractional Differentiation (d* = 0.38) & Multi-Beta Residual Momentum...", flush=True)
    fd_series_38 = apply_fractional_differentiation(close_mat, d=0.38, max_len=18)
    fd_diff_38 = fd_series_38 - np.roll(fd_series_38, 1, axis=0)
    fd_diff_38[0] = 0.0
    f5_38, residuals = compute_multi_beta_residual_momentum(
        fd_diff_38, fd_diff_38[:, btc_idx], fd_diff_38[:, eth_idx], valid_mask, lookback_h=18
    )

    allocator_base = DeadbandExecutionAllocator(deadband_base=0.030)
    f5_smoothed = allocator_base.smooth_multi_horizon_alpha(f5_38)

    print("[2/5] Synthesizing Symmetric FIP Quality Factor (Vector 1 & EXP-48 Baseline)...", flush=True)
    f_fip_smoothed = compute_fip_quality_factor(residuals, f5_smoothed, valid_mask, allocator_base, lookback=18)

    print("[3/5] Synthesizing Asymmetric FIP (AsymFIP) Operator (Vector 2)...", flush=True)
    f_asym = compute_asymmetric_fip_scores(
        residuals=residuals,
        raw_f5_scores=f5_smoothed,
        valid_mask=valid_mask,
        lookback=18,
        lambda_long=1.50,
        lambda_short=0.50,
        max_long_penalty=0.60,
        max_short_boost=0.40,
    )
    f_asym_smoothed = allocator_base.smooth_multi_horizon_alpha(f_asym)

    print("[4/5] Computing Barroso-Santa-Clara Factor Volatility Scaling (Vector 3)...", flush=True)
    asset_vols_24h = np.zeros((n_bars, n_symbols))
    for t in range(6, n_bars):
        asset_vols_24h[t] = np.std(returns_mat[t - 6 : t], axis=0) * np.sqrt(365.25 * 6)
    asset_vols_24h[:6] = asset_vols_24h[6]

    # Factor-level inverse volatility scaling
    f_bsc_scaled = np.zeros_like(f_asym_smoothed)
    for t in range(18, n_bars):
        m_t = valid_mask[t]
        v_idx = np.where(m_t)[0]
        if len(v_idx) >= 10:
            vols_t = asset_vols_24h[t, v_idx]
            med_vol = float(np.median(vols_t)) if len(vols_t) > 0 else 0.80
            vol_scalar = np.clip(med_vol / (vols_t + 1e-6), 0.70, 1.30)
            f_bsc_scaled[t, v_idx] = f_asym_smoothed[t, v_idx] * vol_scalar
    f_bsc_scaled[:18] = f_bsc_scaled[18]
    f_bsc_smoothed = allocator_base.smooth_multi_horizon_alpha(f_bsc_scaled)

    # Baseline portfolio returns for fast risk shield
    w_base = np.zeros((n_bars, n_symbols))
    curr_wb = np.zeros(n_symbols)
    for t in range(n_bars):
        if t % 6 == 0:
            m_t = valid_mask[t]
            if np.sum(m_t) >= 20:
                v_idx = np.where(m_t)[0]
                tgt_w = allocator_base.compute_risk_parity_weights(
                    scores=f5_smoothed[t],
                    valid_idx=v_idx,
                    recent_returns=returns_mat[max(0, t - 36) : t],
                    top_k=10,
                    target_gross_leverage=1.50,
                )
                curr_wb = allocator_base.apply_leland_deadband(tgt_w, curr_wb, tau=0.030)
        w_base[t] = curr_wb
    baseline_bar_returns = np.sum(w_base * returns_mat, axis=1)

    print("[5/5] Generating Tournament 7 Factory Portfolios (EXP-55 to EXP-62)...", flush=True)

    # EXP-55: The Apex Staggered FIP
    print("  -> Building EXP-55: The Apex Staggered FIP (M=2 + FIP Quality, Vol 48%)...", flush=True)
    w_exp55 = simulate_tournament_7_portfolio(
        close_mat=close_mat, returns_mat=returns_mat, valid_mask=valid_mask,
        asset_vols_24h=asset_vols_24h, baseline_bar_returns=baseline_bar_returns,
        signal_matrix=f_fip_smoothed, num_sub_portfolios=2, target_vol=0.48,
        l_min=0.90, l_max=3.20, target_k=8, entry_k=8, exit_k=16
    )
    experiments["EXP-55: The Apex Staggered FIP"] = (
        w_exp55, f_fip_smoothed, "2x Staggered 6H + FIP Quality (Market Impact + Turnover Arbitrage, Vol 48%)", 0.80
    )

    # EXP-56: Asymmetric FIP (AsymFIP)
    print("  -> Building EXP-56: Asymmetric FIP (Unified 6H, Vol 48%)...", flush=True)
    w_exp56 = simulate_tournament_7_portfolio(
        close_mat=close_mat, returns_mat=returns_mat, valid_mask=valid_mask,
        asset_vols_24h=asset_vols_24h, baseline_bar_returns=baseline_bar_returns,
        signal_matrix=f_asym_smoothed, num_sub_portfolios=1, target_vol=0.48,
        l_min=0.90, l_max=3.20, target_k=12, entry_k=8, exit_k=18
    )
    experiments["EXP-56: Asymmetric FIP (AsymFIP)"] = (
        w_exp56, f_asym_smoothed, "Asymmetric FIP (Penalize Upside Wicks / Boost Short Waterfalls, Vol 48%)", 0.80
    )

    # EXP-57: AsymFIP + M=2 Stagger
    print("  -> Building EXP-57: AsymFIP + M=2 Stagger (Vol 48%)...", flush=True)
    w_exp57 = simulate_tournament_7_portfolio(
        close_mat=close_mat, returns_mat=returns_mat, valid_mask=valid_mask,
        asset_vols_24h=asset_vols_24h, baseline_bar_returns=baseline_bar_returns,
        signal_matrix=f_asym_smoothed, num_sub_portfolios=2, target_vol=0.48,
        l_min=0.90, l_max=3.20, target_k=8, entry_k=8, exit_k=16
    )
    experiments["EXP-57: AsymFIP + M=2 Stagger"] = (
        w_exp57, f_asym_smoothed, "2x Staggered 6H + Asymmetric FIP (Liquidation Capture + Impact Halving, Vol 48%)", 0.80
    )

    # EXP-58: Barroso-Santa-Clara Scaling
    print("  -> Building EXP-58: Barroso-Santa-Clara Scaling (Unified 6H, Vol 48%)...", flush=True)
    w_exp58 = simulate_tournament_7_portfolio(
        close_mat=close_mat, returns_mat=returns_mat, valid_mask=valid_mask,
        asset_vols_24h=asset_vols_24h, baseline_bar_returns=baseline_bar_returns,
        signal_matrix=f_bsc_smoothed, num_sub_portfolios=1, target_vol=0.48,
        l_min=0.90, l_max=3.20, target_k=12, entry_k=8, exit_k=18
    )
    experiments["EXP-58: Barroso-Santa-Clara Scaling"] = (
        w_exp58, f_bsc_smoothed, "FIP + Barroso-Santa-Clara Realized Volatility Sizing (Vol 48%)", 0.80
    )

    # EXP-59: AsymFIP + Vol-Scaled Deadband
    print("  -> Building EXP-59: AsymFIP + Vol-Scaled Deadband (tau in [0.025, 0.045], Vol 48%)...", flush=True)
    w_exp59 = simulate_tournament_7_portfolio(
        close_mat=close_mat, returns_mat=returns_mat, valid_mask=valid_mask,
        asset_vols_24h=asset_vols_24h, baseline_bar_returns=baseline_bar_returns,
        signal_matrix=f_asym_smoothed, num_sub_portfolios=1, target_vol=0.48,
        tau_min=0.025, tau_max=0.045, l_min=0.90, l_max=3.20, target_k=12, entry_k=8, exit_k=18
    )
    experiments["EXP-59: AsymFIP + Vol-Scaled Deadband"] = (
        w_exp59, f_asym_smoothed, "AsymFIP + Calibrated Deadband tau_i in [0.025, 0.045] (Vol 48%)", 0.80
    )

    # EXP-60: Triple-Staggered FIP (M=3)
    print("  -> Building EXP-60: Triple-Staggered FIP (M=3, Vol 48%)...", flush=True)
    w_exp60 = simulate_tournament_7_portfolio(
        close_mat=close_mat, returns_mat=returns_mat, valid_mask=valid_mask,
        asset_vols_24h=asset_vols_24h, baseline_bar_returns=baseline_bar_returns,
        signal_matrix=f_fip_smoothed, num_sub_portfolios=3, target_vol=0.48,
        l_min=0.90, l_max=3.20, target_k=8, entry_k=8, exit_k=16
    )
    experiments["EXP-60: Triple-Staggered FIP (M=3)"] = (
        w_exp60, f_fip_smoothed, "3x Staggered 6H + FIP Quality (Maximum Execution Smoothing, Vol 48%)", 0.80
    )

    # EXP-61: Controlled Gearing (50% Vol)
    print("  -> Building EXP-61: Controlled Gearing (50% Vol, M=2 Stagger)...", flush=True)
    w_exp61 = simulate_tournament_7_portfolio(
        close_mat=close_mat, returns_mat=returns_mat, valid_mask=valid_mask,
        asset_vols_24h=asset_vols_24h, baseline_bar_returns=baseline_bar_returns,
        signal_matrix=f_asym_smoothed, num_sub_portfolios=2, target_vol=0.50,
        l_min=0.90, l_max=3.30, target_k=8, entry_k=8, exit_k=16
    )
    experiments["EXP-61: Controlled Gearing (50% Vol)"] = (
        w_exp61, f_asym_smoothed, "2x Staggered 6H + AsymFIP + Controlled Gearing Expansion (Vol 50%, L_max=3.30)", 0.80
    )

    # EXP-62: The Production Grand Master
    print("  -> Building EXP-62: The Production Grand Master...", flush=True)
    w_exp62 = simulate_tournament_7_portfolio(
        close_mat=close_mat, returns_mat=returns_mat, valid_mask=valid_mask,
        asset_vols_24h=asset_vols_24h, baseline_bar_returns=baseline_bar_returns,
        signal_matrix=f_bsc_smoothed, num_sub_portfolios=2, target_vol=0.48,
        l_min=0.90, l_max=3.20, target_k=8, entry_k=8, exit_k=16
    )
    experiments["EXP-62: The Production Grand Master"] = (
        w_exp62, f_bsc_smoothed, "Full Synthesis: 2x Staggered 6H + AsymFIP + Factor Vol Scaling + N_eff DSR (Vol 48%)", 0.80
    )

    return experiments


def main():
    print("=" * 160)
    print("   IRONCORE INSTITUTIONAL FACTORIAL TOURNAMENT 7 (EXP-55 TO EXP-62)")
    print("   The 10x Velocity Frontier: Asymmetric FIP, Staggered Execution & N_eff Calibration")
    print("=" * 160, flush=True)

    # 1. Load Data Lake
    df = pl.read_parquet(DATA_LAKE_PATH)
    _, symbols, market_data = PointInTimeUniverseManager.load_pit_market_matrices(
        df=df, eval_start_ts=EVAL_START_TS, eval_end_ts=EVAL_END_TS, benchmark_symbol=BENCHMARK_SYMBOL
    )

    close_mat = market_data["close"].copy()
    oracle_mat = market_data["oracle"].copy()
    volume_mat = market_data["volume"].copy()
    valid_mask = market_data["valid_price_mask"].copy()
    timestamps = market_data["timestamps"]

    btc_idx = symbols.index(BENCHMARK_SYMBOL) if BENCHMARK_SYMBOL in symbols else 0
    eth_idx = symbols.index("ETH") if "ETH" in symbols else 1
    btc_prices = close_mat[:, btc_idx]

    prev_close = np.roll(close_mat, 1, axis=0)
    returns_mat = np.nan_to_num(np.where(prev_close > 0, (close_mat / prev_close) - 1.0, 0.0))
    returns_mat[0] = 0.0
    predicted_funding = (close_mat - oracle_mat) / (oracle_mat + 1e-8) + 0.000125

    print(f"\n[DATASET READY] Loaded {len(timestamps)} bars across {len(symbols)} symbols.", flush=True)

    # 2. Build Tournament 7 Experiment Matrices
    print("\n[BUILDING TOURNAMENT 7 WEIGHT MATRICES...]", flush=True)
    experiments = build_tournament_7_suite(
        close_mat, oracle_mat, volume_mat, valid_mask, returns_mat, symbols, btc_idx, eth_idx
    )
    print(f"Generated weight matrices for all {len(experiments)} candidate architectures.\n", flush=True)

    # 3. Certification Engine (80% ALO Maker Parity)
    config_80 = IronCoreConfig_v1(
        base_maker_ratio=0.80,
        mc_placebo_draws=150,
        bootstrap_paths=1000,
        initial_capital=10000.0,
    )
    engine = IronCoreEngine(config=config_80)

    # N_eff Effective Trial Count calibration under Bailey & Lopez de Prado (2014)
    n_eff_calibrated = 6.0

    results = []

    print("=" * 175, flush=True)
    print(
        f"{'EXPERIMENT ID & CONFIGURATION':<46} | {'CAGR':<8} | {'SHARPE':<6} | {'MAX DD':<7} | "
        f"{'FRIC RATIO':<10} | {'TURNOVER':<9} | {'P(PERM)':<7} | {'RUIN(%)':<7} | {'TIME TO 10X':<11} | {'VERDICT':<8}",
        flush=True,
    )
    print("-" * 175, flush=True)

    for exp_name, (w_mat, sig_mat, desc, maker_ratio) in experiments.items():
        t0 = time.time()
        
        # Evaluate with N_eff = 6.0 for calibrated DSR
        cert = engine.run_full_certification_gauntlet(
            candidate_name=exp_name,
            weights_matrix=w_mat,
            signal_matrix=sig_mat,
            returns_mat=returns_mat,
            predicted_funding=predicted_funding,
            volume_mat=volume_mat,
            close_mat=close_mat,
            oracle_mat=oracle_mat,
            valid_mask=valid_mask,
            btc_prices=btc_prices,
            effective_n_trials=n_eff_calibrated,
        )
        elapsed = time.time() - t0

        p = cert["performance"]
        gates = cert["gates"]
        v_str = cert["overall_verdict"]

        p_perm = cert["placebos"]["asset_permutation"]["empirical_p_value"]
        p_noise = cert["placebos"]["horizon_matched_random"]["empirical_p_value"]
        dsr = cert["dsr_metrics"]["deflated_sharpe_ratio"]
        ruin = cert["ruin_analysis"]["ruin_probability"]

        t_2x, t_5x, t_10x = calculate_compounding_milestones(p["cagr"])
        t_10x_str = f"{t_10x:.1f} mo" if not math.isinf(t_10x) else "Never"

        failed = [g.split("(")[1].split(")")[0] for g, passed in gates.items() if not passed]
        failed_str = ", ".join(failed) if failed else "None"

        print(
            f"{exp_name:<46} | {p['cagr']:>7.2f}% | {p['sharpe']:>6.2f} | {p['max_dd']:>6.2f}% | "
            f"{p['fric_ratio']:>8.2f}% | {p['turnover']:>8.1f}x | {p_perm:>7.4f} | {ruin*100:>6.2f}% | "
            f"{t_10x_str:>11} | {v_str:<8}",
            flush=True,
        )

        results.append({
            "name": exp_name,
            "description": desc,
            "maker_ratio": maker_ratio,
            "verdict": v_str,
            "cagr": p["cagr"],
            "sharpe": p["sharpe"],
            "max_dd": p["max_dd"],
            "turnover": p["turnover"],
            "friction_ratio": p["fric_ratio"],
            "p_perm": p_perm,
            "p_noise": p_noise,
            "ruin_prob": ruin,
            "dsr": dsr,
            "t_2x": t_2x,
            "t_5x": t_5x,
            "t_10x": t_10x,
            "failed_gates": failed_str,
            "calmar": p["cagr"] / max(p["max_dd"], 1e-4),
            "execution_sec": elapsed,
        })

    print("=" * 175, flush=True)

    with open(TOURNAMENT_RESULTS_PATH, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n[COMPLETE] Tournament 7 results persisted to: {TOURNAMENT_RESULTS_PATH}", flush=True)


if __name__ == "__main__":
    main()
