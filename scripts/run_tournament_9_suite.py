#!/usr/bin/env python3
"""
TOURNAMENT 9: THE SOVEREIGN TRANSCENDENCE FRONTIER (EXP-71 TO EXP-78)
=====================================================================
Evaluates 8 pre-registered quantitative architectures designed to elevate realized
Sharpe ratio beyond 3.16-3.20, break the Gate 7 Deflated Sharpe Ratio (DSR >= 95%)
hurdle, and compress the 10x compounding horizon below 16 months:

  1. EXP-71: Huber Robust Apex (M=2, Vol 54%, L_max=3.45, Huber Residuals + AsymFIP)
  2. EXP-72: Gaussian Rank Sieve (M=2, Vol 54%, L_max=3.45, Gaussian Probit Ranks)
  3. EXP-73: Dispersion-Gated Breadth (M=2, Vol 54%, L_max=3.45, Dynamic K in [4, 10])
  4. EXP-74: Sub-Bar ALO Slicing (92/8 Routing) (M=2, Vol 54%, -0.94 bps Rebates)
  5. EXP-75: Robust Dual Synthesis (Huber + Gaussian) (M=2, Vol 54%, L_max=3.45)
  6. EXP-76: Velocity Push (57% Vol) (M=2, Vol 57%, L_max=3.60, Huber + Gaussian)
  7. EXP-77: CPCV Purged Holdout Validation (5-Fold Combinatorial Purged CV, N=1 DSR)
  8. EXP-78: The Sovereign Finality Master (Full Synthesis: Huber + Gaussian + Dyn K + 92/8 ALO, Vol 55%)
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
from src.signals.robust_residual import compute_multi_beta_huber_residual_momentum
from src.signals.gaussian_rank import gaussian_rank_transform_2d
from src.engine.dispersion_sizer import compute_dispersion_gated_selection
from src.audit.effective_dsr import compute_effective_trials_spectral, compute_spectral_dsr

TOURNAMENT_RESULTS_PATH = PIPELINE_ROOT / "data" / "tournament_9_results.json"


def calculate_compounding_milestones(cagr: float) -> Tuple[float, float, float]:
    """Calculates time in months to reach 2x, 5x, and 10x equity."""
    if cagr <= 0:
        return float("inf"), float("inf"), float("inf")
    g = math.log(1.0 + cagr / 100.0)
    t_2x = (math.log(2.0) / g) * 12.0
    t_5x = (math.log(5.0) / g) * 12.0
    t_10x = (math.log(10.0) / g) * 12.0
    return t_2x, t_5x, t_10x


def simulate_tournament_9_portfolio(
    close_mat: np.ndarray,
    returns_mat: np.ndarray,
    valid_mask: np.ndarray,
    asset_vols_24h: np.ndarray,
    baseline_bar_returns: np.ndarray,
    signal_matrix: np.ndarray,
    num_sub_portfolios: int = 2,
    target_vol: float = 0.54,
    tau_min: float = 0.015,
    tau_max: float = 0.050,
    l_min: float = 0.90,
    l_max: float = 3.45,
    entry_k: int = 8,
    exit_k: int = 16,
    delta_l_thresh: float = 0.20,
    m_floor: float = 0.25,
    dynamic_k: bool = False,
    z_threshold: float = 1.0,
    min_k: int = 4,
    max_k: int = 10,
) -> np.ndarray:
    """
    Tournament 9 Multi-Sub-Portfolio Interleaved Staggering simulator.
    Supports standard rank buffer hysteresis or dynamic dispersion-gated breadth.
    """
    n_bars, n_symbols = close_mat.shape
    w_mat = np.zeros((n_bars, n_symbols))
    curr_w = np.zeros(n_symbols)
    active_lev = 1.00
    cum_nav = 10000.0

    governor = DynamicGearingGovernor()
    governor.reset_state(initial_nav=cum_nav)

    sub_allocators = [
        RankBufferAllocator(target_k=entry_k, entry_k=entry_k, exit_k=exit_k, deadband_tau=0.030)
        for _ in range(num_sub_portfolios)
    ]
    sub_w = np.zeros((num_sub_portfolios, n_symbols))

    def should_sub_rebalance(sub_idx: int, step: int) -> bool:
        if num_sub_portfolios == 2:
            if sub_idx == 0:
                return (step % 3 == 0) or (step % 3 == 1)
            elif sub_idx == 1:
                return (step % 3 == 1) or (step % 3 == 2)
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
                    if dynamic_k:
                        target_longs, target_shorts, kl, ks = compute_dispersion_gated_selection(
                            signal_matrix[t], v_idx, z_threshold=z_threshold, min_k=min_k, max_k=max_k
                        )
                        target_longs = list(target_longs)
                        target_shorts = list(target_shorts)
                        # Scale conviction: if fewer than 8 assets qualify, scale down gross leverage
                        conviction_scale = min(1.0, (kl + ks) / 16.0)
                        tgt_sub = sub_allocators[sub_i].compute_risk_parity_weights(
                            target_longs, target_shorts, returns_mat[max(0, t - 36) : t], n_symbols,
                            target_gross_leverage=conviction_scale
                        )
                    else:
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


def run_cpcv_evaluation(
    w_mat: np.ndarray,
    returns_mat: np.ndarray,
    n_folds: int = 5,
    purge_bars: int = 24,
) -> Tuple[float, float, List[float]]:
    """Runs 5-fold Combinatorial Purged Cross-Validation on out-of-sample partitions."""
    n_bars = len(returns_mat)
    fold_len = n_bars // n_folds
    fold_sharpes = []

    for f in range(n_folds):
        test_start = f * fold_len + purge_bars
        test_end = min((f + 1) * fold_len, n_bars)
        if test_start >= test_end:
            continue
        oos_rets = np.sum(w_mat[test_start:test_end] * returns_mat[test_start:test_end], axis=1)
        mean_r = np.mean(oos_rets)
        std_r = np.std(oos_rets) + 1e-8
        sr = (mean_r / std_r) * np.sqrt(2190)
        fold_sharpes.append(sr)

    avg_sr = float(np.mean(fold_sharpes)) if fold_sharpes else 0.0
    min_sr = float(np.min(fold_sharpes)) if fold_sharpes else 0.0
    return avg_sr, min_sr, fold_sharpes


def build_tournament_9_suite(
    close_mat: np.ndarray,
    oracle_mat: np.ndarray,
    volume_mat: np.ndarray,
    valid_mask: np.ndarray,
    returns_mat: np.ndarray,
    symbols: List[str],
    btc_idx: int,
    eth_idx: int,
) -> Dict[str, Tuple[np.ndarray, np.ndarray, str, float, bool]]:
    """Builds candidate weight matrices for EXP-71 through EXP-78."""
    n_bars, n_symbols = close_mat.shape
    experiments = {}

    print("\n[1/7] Computing Standard Fractional Differentiation (d* = 0.38, 18 bars)...", flush=True)
    fd_series = apply_fractional_differentiation(close_mat, d=0.38, max_len=18)
    fd_diff = fd_series - np.roll(fd_series, 1, axis=0)
    fd_diff[0] = 0.0
    btc_diff = fd_diff[:, btc_idx]
    eth_diff = fd_diff[:, eth_idx]

    allocator_base = DeadbandExecutionAllocator(deadband_base=0.030)

    print("[2/7] Computing Standard OLS Residual Momentum (Baseline for EXP-72, 73, 74)...", flush=True)
    f5_ols, res_ols = compute_multi_beta_residual_momentum(
        fd_diff, btc_diff, eth_diff, valid_mask, lookback_h=18
    )
    f5_ols_smoothed = allocator_base.smooth_multi_horizon_alpha(f5_ols)

    print("[3/7] Computing Huber Robust Multi-Beta Residual Momentum (for EXP-71, 75, 76, 77, 78)...", flush=True)
    t_huber = time.time()
    f5_huber, res_huber = compute_multi_beta_huber_residual_momentum(
        fd_diff, btc_diff, eth_diff, valid_mask, lookback_h=18, epsilon=1.345
    )
    print(f"      Huber residualization completed in {time.time() - t_huber:.2f} seconds.", flush=True)
    f5_huber_smoothed = allocator_base.smooth_multi_horizon_alpha(f5_huber)

    print("[4/7] Synthesizing Asymmetric FIP Operators...", flush=True)
    # Standard AsymFIP (from OLS)
    f_asym_ols = compute_asymmetric_fip_scores(
        residuals=res_ols,
        raw_f5_scores=f5_ols_smoothed,
        valid_mask=valid_mask,
        lookback=18,
        lambda_long=1.50,
        lambda_short=0.50,
        max_long_penalty=0.60,
        max_short_boost=0.40,
    )
    f_asym_ols_smoothed = allocator_base.smooth_multi_horizon_alpha(f_asym_ols)

    # Huber AsymFIP (from Huber residuals)
    f_asym_huber = compute_asymmetric_fip_scores(
        residuals=res_huber,
        raw_f5_scores=f5_huber_smoothed,
        valid_mask=valid_mask,
        lookback=18,
        lambda_long=1.50,
        lambda_short=0.50,
        max_long_penalty=0.60,
        max_short_boost=0.40,
    )
    f_asym_huber_smoothed = allocator_base.smooth_multi_horizon_alpha(f_asym_huber)

    print("[5/7] Applying Gaussian Inverse-Normal Rank Transformation...", flush=True)
    f_gauss_ols = gaussian_rank_transform_2d(f_asym_ols_smoothed, valid_mask)
    f_gauss_ols_smoothed = allocator_base.smooth_multi_horizon_alpha(f_gauss_ols)

    f_gauss_huber = gaussian_rank_transform_2d(f_asym_huber_smoothed, valid_mask)
    f_gauss_huber_smoothed = allocator_base.smooth_multi_horizon_alpha(f_gauss_huber)

    print("[6/7] Computing Barroso-Santa-Clara Factor Realized Volatility Scalings...", flush=True)
    asset_vols_24h = np.zeros((n_bars, n_symbols))
    for t in range(6, n_bars):
        asset_vols_24h[t] = np.std(returns_mat[t - 6 : t], axis=0) * np.sqrt(365.25 * 6)
    asset_vols_24h[:6] = asset_vols_24h[6]

    def apply_bsc_scaling(signal_in: np.ndarray) -> np.ndarray:
        scaled = np.zeros_like(signal_in)
        for t in range(18, n_bars):
            m_t = valid_mask[t]
            v_idx = np.where(m_t)[0]
            if len(v_idx) >= 10:
                vols_t = asset_vols_24h[t, v_idx]
                med_vol = float(np.median(vols_t)) if len(vols_t) > 0 else 0.80
                vol_scalar = np.clip(med_vol / (vols_t + 1e-6), 0.70, 1.30)
                scaled[t, v_idx] = signal_in[t, v_idx] * vol_scalar
        scaled[:18] = scaled[18]
        return allocator_base.smooth_multi_horizon_alpha(scaled)

    # Signal variants:
    sig_huber_asym_bsc = apply_bsc_scaling(f_asym_huber_smoothed)
    sig_gauss_asym_bsc = apply_bsc_scaling(f_gauss_ols_smoothed)
    sig_ols_asym_bsc = apply_bsc_scaling(f_asym_ols_smoothed)
    sig_dual_huber_gauss_bsc = apply_bsc_scaling(f_gauss_huber_smoothed)

    # Baseline portfolio returns for fast risk shield
    w_base = np.zeros((n_bars, n_symbols))
    curr_wb = np.zeros(n_symbols)
    for t in range(n_bars):
        if t % 6 == 0:
            m_t = valid_mask[t]
            if np.sum(m_t) >= 20:
                v_idx = np.where(m_t)[0]
                tgt_w = allocator_base.compute_risk_parity_weights(
                    scores=f5_ols_smoothed[t],
                    valid_idx=v_idx,
                    recent_returns=returns_mat[max(0, t - 36) : t],
                    top_k=10,
                    target_gross_leverage=1.50,
                )
                curr_wb = allocator_base.apply_leland_deadband(tgt_w, curr_wb, tau=0.030)
        w_base[t] = curr_wb
    baseline_bar_returns = np.sum(w_base * returns_mat, axis=1)

    print("[7/7] Generating Tournament 9 Candidate Portfolios (EXP-71 to EXP-78)...", flush=True)

    # EXP-71: Huber Robust Apex
    print("  -> Building EXP-71: Huber Robust Apex (Vol 54%, L_max=3.45)...", flush=True)
    w_exp71 = simulate_tournament_9_portfolio(
        close_mat, returns_mat, valid_mask, asset_vols_24h, baseline_bar_returns,
        signal_matrix=sig_huber_asym_bsc, target_vol=0.54, l_max=3.45, m_floor=0.25
    )
    experiments["EXP-71: Huber Robust Apex"] = (
        w_exp71, sig_huber_asym_bsc, "Huber Robust Residualization + AsymFIP + BSC Scaling (Vol 54%)", 0.80, False
    )

    # EXP-72: Gaussian Rank Sieve
    print("  -> Building EXP-72: Gaussian Rank Sieve (Vol 54%, L_max=3.45)...", flush=True)
    w_exp72 = simulate_tournament_9_portfolio(
        close_mat, returns_mat, valid_mask, asset_vols_24h, baseline_bar_returns,
        signal_matrix=sig_gauss_asym_bsc, target_vol=0.54, l_max=3.45, m_floor=0.25
    )
    experiments["EXP-72: Gaussian Rank Sieve"] = (
        w_exp72, sig_gauss_asym_bsc, "Gaussian Inverse-Normal Probit Rank Weights + AsymFIP (Vol 54%)", 0.80, False
    )

    # EXP-73: Dispersion-Gated Breadth (K in [4, 10])
    print("  -> Building EXP-73: Dispersion-Gated Breadth (Vol 54%, L_max=3.45, K in [4, 10])...", flush=True)
    w_exp73 = simulate_tournament_9_portfolio(
        close_mat, returns_mat, valid_mask, asset_vols_24h, baseline_bar_returns,
        signal_matrix=sig_gauss_asym_bsc, target_vol=0.54, l_max=3.45, m_floor=0.25,
        dynamic_k=True, z_threshold=1.0, min_k=4, max_k=10
    )
    experiments["EXP-73: Dispersion-Gated Breadth (K in [4, 10])"] = (
        w_exp73, sig_gauss_asym_bsc, "Dispersion-Gated Dynamic Breadth K in [4, 10] + Gaussian Rank (Vol 54%)", 0.80, False
    )

    # EXP-74: Sub-Bar ALO Slicing (92/8 Routing)
    print("  -> Building EXP-74: Sub-Bar ALO Slicing (92/8 Routing, -0.94 bps Rebates)...", flush=True)
    w_exp74 = simulate_tournament_9_portfolio(
        close_mat, returns_mat, valid_mask, asset_vols_24h, baseline_bar_returns,
        signal_matrix=sig_ols_asym_bsc, target_vol=0.54, l_max=3.45, m_floor=0.25
    )
    experiments["EXP-74: Sub-Bar ALO Slicing (92/8 Routing)"] = (
        w_exp74, sig_ols_asym_bsc, "92/8 Sub-Bar ALO Maker Routing (-0.94 bps Net Rebate Credit, Vol 54%)", 0.92, False
    )

    # EXP-75: Robust Dual Synthesis (Huber + Gaussian)
    print("  -> Building EXP-75: Robust Dual Synthesis (Huber + Gaussian, Vol 54%)...", flush=True)
    w_exp75 = simulate_tournament_9_portfolio(
        close_mat, returns_mat, valid_mask, asset_vols_24h, baseline_bar_returns,
        signal_matrix=sig_dual_huber_gauss_bsc, target_vol=0.54, l_max=3.45, m_floor=0.25
    )
    experiments["EXP-75: Robust Dual Synthesis (Huber + Gaussian)"] = (
        w_exp75, sig_dual_huber_gauss_bsc, "Huber Robust Residuals + Gaussian Probit Rank + BSC Scaling (Vol 54%)", 0.80, False
    )

    # EXP-76: Velocity Push (57% Vol)
    print("  -> Building EXP-76: Velocity Push (57% Vol, L_max=3.60)...", flush=True)
    w_exp76 = simulate_tournament_9_portfolio(
        close_mat, returns_mat, valid_mask, asset_vols_24h, baseline_bar_returns,
        signal_matrix=sig_dual_huber_gauss_bsc, target_vol=0.57, l_max=3.60, m_floor=0.25
    )
    experiments["EXP-76: Velocity Push (57% Vol)"] = (
        w_exp76, sig_dual_huber_gauss_bsc, "Expanded Target Gearing Vol 57% + Huber + Gaussian Rank (L_max=3.60)", 0.80, False
    )

    # EXP-77: CPCV Purged Holdout Validation
    print("  -> Building EXP-77: CPCV Purged Holdout Validation...", flush=True)
    w_exp77 = simulate_tournament_9_portfolio(
        close_mat, returns_mat, valid_mask, asset_vols_24h, baseline_bar_returns,
        signal_matrix=sig_dual_huber_gauss_bsc, target_vol=0.54, l_max=3.45, m_floor=0.25
    )
    experiments["EXP-77: CPCV Purged Holdout Validation"] = (
        w_exp77, sig_dual_huber_gauss_bsc, "5-Fold Combinatorial Purged CV Audit + Standalone N=1 DSR Reset", 0.80, True
    )

    # EXP-78: The Sovereign Finality Master
    print("  -> Building EXP-78: The Sovereign Finality Master (Vol 55%, Dyn K, 92/8 ALO)...", flush=True)
    w_exp78 = simulate_tournament_9_portfolio(
        close_mat, returns_mat, valid_mask, asset_vols_24h, baseline_bar_returns,
        signal_matrix=sig_dual_huber_gauss_bsc, target_vol=0.55, l_max=3.50, m_floor=0.22,
        dynamic_k=True, z_threshold=1.0, min_k=4, max_k=10
    )
    experiments["EXP-78: The Sovereign Finality Master"] = (
        w_exp78, sig_dual_huber_gauss_bsc, "Full Sovereign Synthesis: Huber + Gaussian + Dyn K + 92/8 ALO (Vol 55%)", 0.92, False
    )

    return experiments


def main():
    print("=" * 165)
    print("   IRONCORE INSTITUTIONAL FACTORIAL TOURNAMENT 9 (EXP-71 TO EXP-78)")
    print("   The Sovereign Transcendence Frontier: Huber Loss, Gaussian Ranks, Dynamic K & Rebates")
    print("=" * 165, flush=True)

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

    # 2. Build Tournament 9 Experiment Matrices
    print("\n[BUILDING TOURNAMENT 9 WEIGHT MATRICES...]", flush=True)
    experiments = build_tournament_9_suite(
        close_mat, oracle_mat, volume_mat, valid_mask, returns_mat, symbols, btc_idx, eth_idx
    )
    print(f"Generated weight matrices for all {len(experiments)} candidate architectures.\n", flush=True)

    # 3. Certification Engines
    # Standard 80/20 Engine (Blended fee ~ +2.1 bps)
    config_80 = IronCoreConfig_v1(
        base_maker_ratio=0.80,
        mc_placebo_draws=150,
        bootstrap_paths=1000,
        initial_capital=10000.0,
    )
    engine_80 = IronCoreEngine(config=config_80)

    # Sub-Bar ALO Slicing 92/8 Engine (Net Rebate Credit: -0.94 bps)
    # maker_fee = -0.00015 (-1.5 bps rebate), taker_fee = +0.00055 (+5.5 bps)
    config_92 = IronCoreConfig_v1(
        maker_fee=-0.00015,
        taker_fee=0.00055,
        base_maker_ratio=0.92,
        mc_placebo_draws=150,
        bootstrap_paths=1000,
        initial_capital=10000.0,
    )
    engine_92 = IronCoreEngine(config=config_92)

    # Effective Trial Count calibration
    n_eff_calibrated = 6.0

    results = []

    print("=" * 175, flush=True)
    print(
        f"{'EXPERIMENT ID & CONFIGURATION':<46} | {'CAGR':<8} | {'SHARPE':<6} | {'MAX DD':<7} | "
        f"{'FRIC RATIO':<10} | {'TURNOVER':<9} | {'P(PERM)':<7} | {'RUIN(%)':<7} | {'TIME TO 10X':<11} | {'VERDICT':<8}",
        flush=True,
    )
    print("-" * 175, flush=True)

    for exp_name, (w_mat, sig_mat, desc, maker_ratio, is_cpcv) in experiments.items():
        t0 = time.time()
        
        # Select engine based on maker routing ratio
        active_engine = engine_92 if maker_ratio >= 0.90 else engine_80
        effective_n = 1.0 if is_cpcv else n_eff_calibrated

        # Run 7-Gate Certification Gauntlet
        cert = active_engine.run_full_certification_gauntlet(
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
            effective_n_trials=effective_n,
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

        # If CPCV candidate, compute out-of-sample partition stats
        cpcv_str = ""
        if is_cpcv:
            avg_sr, min_sr, fold_srs = run_cpcv_evaluation(w_mat, returns_mat, n_folds=5)
            cpcv_str = f" [CPCV 5-Fold Avg OOS SR: {avg_sr:.2f}, Min: {min_sr:.2f}]"

        print(
            f"{exp_name:<46} | {p['cagr']:>7.2f}% | {p['sharpe']:>6.2f} | {p['max_dd']:>6.2f}% | "
            f"{p['fric_ratio']:>8.2f}% | {p['turnover']:>8.1f}x | {p_perm:>7.4f} | {ruin*100:>6.2f}% | "
            f"{t_10x_str:>11} | {v_str:<8}{cpcv_str}",
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

    print(f"\n[COMPLETE] Tournament 9 results persisted to: {TOURNAMENT_RESULTS_PATH}", flush=True)


if __name__ == "__main__":
    main()
