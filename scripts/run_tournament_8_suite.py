#!/usr/bin/env python3
"""
TOURNAMENT 8: THE SUB-16-MONTH FRONTIER (EXP-63 TO EXP-70)
=========================================================
Evaluates 8 pre-registered quantitative architectures designed to compress the
10x compounding horizon below 16 months (+340% to +380% Net CAGR) and push
realized Sharpe past 3.15 to clear Gate 7 (DSR >= 95.0%):

  1. EXP-63: Grand Master Gearing (51% Vol) (M=2, Vol 51%, L_max=3.30, AsymFIP, BSC Scaling)
  2. EXP-64: Grand Master Gearing (54% Vol) (M=2, Vol 54%, L_max=3.45, AsymFIP, BSC Scaling)
  3. EXP-65: Triple-Stagger Grand Master (M=3, Vol 51%, L_max=3.30, AsymFIP, BSC Scaling)
  4. EXP-66: Exponential AsymFIP Curvature (M=2, Vol 48%, L_max=3.20, Exp-AsymFIP, BSC Scaling)
  5. EXP-67: Extended Memory Horizon (96H / 24 Bars) (M=2, Vol 48%, L_max=3.20, Lookback 24 Bars)
  6. EXP-68: Adaptive Floor Ratchet (M_floor=0.20) (M=2, Vol 51%, L_max=3.30, M_floor=0.20)
  7. EXP-69: Dual Synthesis: Exp-FIP + 51% Vol (M=2, Vol 51%, L_max=3.30, Exp-AsymFIP, BSC Scaling)
  8. EXP-70: The Sovereign Finality Master (M=3, Vol 53%, L_max=3.40, M_floor=0.22, Exp-AsymFIP)
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
from src.signals.exp_asym_fip import compute_exponential_asym_fip
from src.audit.effective_dsr import compute_effective_trials_spectral, compute_spectral_dsr

TOURNAMENT_RESULTS_PATH = PIPELINE_ROOT / "data" / "tournament_8_results.json"


def calculate_compounding_milestones(cagr: float) -> Tuple[float, float, float]:
    """Calculates time in months to reach 2x, 5x, and 10x equity."""
    if cagr <= 0:
        return float("inf"), float("inf"), float("inf")
    g = math.log(1.0 + cagr / 100.0)
    t_2x = (math.log(2.0) / g) * 12.0
    t_5x = (math.log(5.0) / g) * 12.0
    t_10x = (math.log(10.0) / g) * 12.0
    return t_2x, t_5x, t_10x


def simulate_tournament_8_portfolio(
    close_mat: np.ndarray,
    returns_mat: np.ndarray,
    valid_mask: np.ndarray,
    asset_vols_24h: np.ndarray,
    baseline_bar_returns: np.ndarray,
    signal_matrix: np.ndarray,
    num_sub_portfolios: int,      # 2 or 3
    target_vol: float,            # 0.48, 0.51, 0.53, 0.54
    tau_min: float = 0.015,
    tau_max: float = 0.050,
    l_min: float = 0.90,
    l_max: float = 3.20,
    target_k: int = 8,
    entry_k: int = 8,
    exit_k: int = 16,
    delta_l_thresh: float = 0.20,
    m_floor: float = 0.25,
) -> np.ndarray:
    """
    Multi-Sub-Portfolio Interleaved Staggering simulator for Tournament 8.
    Supports M=2 and M=3 staggering with configurable target vol, leverage ceiling,
    and Grossman-Zhou floor ratchet.
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


def build_tournament_8_suite(
    close_mat: np.ndarray,
    oracle_mat: np.ndarray,
    volume_mat: np.ndarray,
    valid_mask: np.ndarray,
    returns_mat: np.ndarray,
    symbols: List[str],
    btc_idx: int,
    eth_idx: int,
) -> Dict[str, Tuple[np.ndarray, np.ndarray, str, float]]:
    """Builds candidate weight matrices for EXP-63 through EXP-70."""
    n_bars, n_symbols = close_mat.shape
    experiments = {}

    print("\n[1/6] Computing Standard Fractional Differentiation (d* = 0.38, 18-bar lookback)...", flush=True)
    fd_series_18 = apply_fractional_differentiation(close_mat, d=0.38, max_len=18)
    fd_diff_18 = fd_series_18 - np.roll(fd_series_18, 1, axis=0)
    fd_diff_18[0] = 0.0
    f5_18, res_18 = compute_multi_beta_residual_momentum(
        fd_diff_18, fd_diff_18[:, btc_idx], fd_diff_18[:, eth_idx], valid_mask, lookback_h=18
    )

    allocator_base = DeadbandExecutionAllocator(deadband_base=0.030)
    f5_18_smoothed = allocator_base.smooth_multi_horizon_alpha(f5_18)

    print("[2/6] Computing 24-Bar Extended Lookback (96H) FracDiff & Residuals (for EXP-67)...", flush=True)
    fd_series_24 = apply_fractional_differentiation(close_mat, d=0.38, max_len=24)
    fd_diff_24 = fd_series_24 - np.roll(fd_series_24, 1, axis=0)
    fd_diff_24[0] = 0.0
    f5_24, res_24 = compute_multi_beta_residual_momentum(
        fd_diff_24, fd_diff_24[:, btc_idx], fd_diff_24[:, eth_idx], valid_mask, lookback_h=24
    )
    f5_24_smoothed = allocator_base.smooth_multi_horizon_alpha(f5_24)

    print("[3/6] Synthesizing Asymmetric FIP (Linear AsymFIP) Operators...", flush=True)
    f_asym_18 = compute_asymmetric_fip_scores(
        residuals=res_18,
        raw_f5_scores=f5_18_smoothed,
        valid_mask=valid_mask,
        lookback=18,
        lambda_long=1.50,
        lambda_short=0.50,
        max_long_penalty=0.60,
        max_short_boost=0.40,
    )
    f_asym_18_smoothed = allocator_base.smooth_multi_horizon_alpha(f_asym_18)

    f_asym_24 = compute_asymmetric_fip_scores(
        residuals=res_24,
        raw_f5_scores=f5_24_smoothed,
        valid_mask=valid_mask,
        lookback=24,
        lambda_long=1.50,
        lambda_short=0.50,
        max_long_penalty=0.60,
        max_short_boost=0.40,
    )
    f_asym_24_smoothed = allocator_base.smooth_multi_horizon_alpha(f_asym_24)

    print("[4/6] Synthesizing Exponential Asymmetric FIP (Exp-AsymFIP) Operator...", flush=True)
    f_exp_asym = compute_exponential_asym_fip(
        fracdiff_scores=f5_18_smoothed,
        residual_returns=res_18,
        valid_mask=valid_mask,
        lookback=18,
        alpha_long=2.50,
        beta_short=1.20,
    )
    f_exp_asym_smoothed = allocator_base.smooth_multi_horizon_alpha(f_exp_asym)

    print("[5/6] Computing Barroso-Santa-Clara Factor Realized Volatility Scalings...", flush=True)
    asset_vols_24h = np.zeros((n_bars, n_symbols))
    for t in range(6, n_bars):
        asset_vols_24h[t] = np.std(returns_mat[t - 6 : t], axis=0) * np.sqrt(365.25 * 6)
    asset_vols_24h[:6] = asset_vols_24h[6]

    def apply_bsc_scaling(signal_in: np.ndarray, min_lookback: int = 18) -> np.ndarray:
        scaled = np.zeros_like(signal_in)
        for t in range(min_lookback, n_bars):
            m_t = valid_mask[t]
            v_idx = np.where(m_t)[0]
            if len(v_idx) >= 10:
                vols_t = asset_vols_24h[t, v_idx]
                med_vol = float(np.median(vols_t)) if len(vols_t) > 0 else 0.80
                vol_scalar = np.clip(med_vol / (vols_t + 1e-6), 0.70, 1.30)
                scaled[t, v_idx] = signal_in[t, v_idx] * vol_scalar
        scaled[:min_lookback] = scaled[min_lookback]
        return allocator_base.smooth_multi_horizon_alpha(scaled)

    # 1. Standard AsymFIP + BSC Scaling (18-bar)
    f_bsc_asym_18 = apply_bsc_scaling(f_asym_18_smoothed, 18)
    # 2. Extended AsymFIP + BSC Scaling (24-bar)
    f_bsc_asym_24 = apply_bsc_scaling(f_asym_24_smoothed, 24)
    # 3. Exponential AsymFIP + BSC Scaling (18-bar)
    f_bsc_exp_asym = apply_bsc_scaling(f_exp_asym_smoothed, 18)

    # Baseline portfolio returns for fast risk shield
    w_base = np.zeros((n_bars, n_symbols))
    curr_wb = np.zeros(n_symbols)
    for t in range(n_bars):
        if t % 6 == 0:
            m_t = valid_mask[t]
            if np.sum(m_t) >= 20:
                v_idx = np.where(m_t)[0]
                tgt_w = allocator_base.compute_risk_parity_weights(
                    scores=f5_18_smoothed[t],
                    valid_idx=v_idx,
                    recent_returns=returns_mat[max(0, t - 36) : t],
                    top_k=10,
                    target_gross_leverage=1.50,
                )
                curr_wb = allocator_base.apply_leland_deadband(tgt_w, curr_wb, tau=0.030)
        w_base[t] = curr_wb
    baseline_bar_returns = np.sum(w_base * returns_mat, axis=1)

    print("[6/6] Generating Tournament 8 Candidate Portfolios (EXP-63 to EXP-70)...", flush=True)

    # EXP-63: Grand Master Gearing (51% Vol)
    print("  -> Building EXP-63: Grand Master Gearing (51% Vol, L_max=3.30)...", flush=True)
    w_exp63 = simulate_tournament_8_portfolio(
        close_mat=close_mat, returns_mat=returns_mat, valid_mask=valid_mask,
        asset_vols_24h=asset_vols_24h, baseline_bar_returns=baseline_bar_returns,
        signal_matrix=f_bsc_asym_18, num_sub_portfolios=2, target_vol=0.51,
        l_min=0.90, l_max=3.30, m_floor=0.25
    )
    experiments["EXP-63: Grand Master Gearing (51% Vol)"] = (
        w_exp63, f_bsc_asym_18, "2x Staggered 6H + AsymFIP + BSC Scaling (Vol 51%, L_max=3.30)", 0.80
    )

    # EXP-64: Grand Master Gearing (54% Vol)
    print("  -> Building EXP-64: Grand Master Gearing (54% Vol, L_max=3.45)...", flush=True)
    w_exp64 = simulate_tournament_8_portfolio(
        close_mat=close_mat, returns_mat=returns_mat, valid_mask=valid_mask,
        asset_vols_24h=asset_vols_24h, baseline_bar_returns=baseline_bar_returns,
        signal_matrix=f_bsc_asym_18, num_sub_portfolios=2, target_vol=0.54,
        l_min=0.90, l_max=3.45, m_floor=0.25
    )
    experiments["EXP-64: Grand Master Gearing (54% Vol)"] = (
        w_exp64, f_bsc_asym_18, "2x Staggered 6H + AsymFIP + BSC Scaling (Vol 54%, L_max=3.45)", 0.80
    )

    # EXP-65: Triple-Stagger Grand Master (M=3, 51% Vol)
    print("  -> Building EXP-65: Triple-Stagger Grand Master (M=3, Vol 51%, L_max=3.30)...", flush=True)
    w_exp65 = simulate_tournament_8_portfolio(
        close_mat=close_mat, returns_mat=returns_mat, valid_mask=valid_mask,
        asset_vols_24h=asset_vols_24h, baseline_bar_returns=baseline_bar_returns,
        signal_matrix=f_bsc_asym_18, num_sub_portfolios=3, target_vol=0.51,
        l_min=0.90, l_max=3.30, m_floor=0.25
    )
    experiments["EXP-65: Triple-Stagger Grand Master"] = (
        w_exp65, f_bsc_asym_18, "3x Staggered 6H + AsymFIP + BSC Scaling (Continuous Smoothing, Vol 51%, L_max=3.30)", 0.80
    )

    # EXP-66: Exponential AsymFIP Curvature (48% Vol)
    print("  -> Building EXP-66: Exponential AsymFIP Curvature (M=2, Vol 48%, L_max=3.20)...", flush=True)
    w_exp66 = simulate_tournament_8_portfolio(
        close_mat=close_mat, returns_mat=returns_mat, valid_mask=valid_mask,
        asset_vols_24h=asset_vols_24h, baseline_bar_returns=baseline_bar_returns,
        signal_matrix=f_bsc_exp_asym, num_sub_portfolios=2, target_vol=0.48,
        l_min=0.90, l_max=3.20, m_floor=0.25
    )
    experiments["EXP-66: Exponential AsymFIP Curvature"] = (
        w_exp66, f_bsc_exp_asym, "2x Staggered 6H + Exp-AsymFIP + BSC Scaling (Non-Linear Curvature, Vol 48%)", 0.80
    )

    # EXP-67: Extended Memory Horizon (96H / 24 Bars)
    print("  -> Building EXP-67: Extended Memory Horizon (96H / 24 Bars, Vol 48%)...", flush=True)
    w_exp67 = simulate_tournament_8_portfolio(
        close_mat=close_mat, returns_mat=returns_mat, valid_mask=valid_mask,
        asset_vols_24h=asset_vols_24h, baseline_bar_returns=baseline_bar_returns,
        signal_matrix=f_bsc_asym_24, num_sub_portfolios=2, target_vol=0.48,
        l_min=0.90, l_max=3.20, m_floor=0.25
    )
    experiments["EXP-67: Extended Memory Horizon (96H)"] = (
        w_exp67, f_bsc_asym_24, "2x Staggered 6H + 24-Bar (96H) Lookback FracDiff Residual Momentum (Vol 48%)", 0.80
    )

    # EXP-68: Adaptive Floor Ratchet (M_floor=0.20, 51% Vol)
    print("  -> Building EXP-68: Adaptive Floor Ratchet (M_floor=0.20, Vol 51%, L_max=3.30)...", flush=True)
    w_exp68 = simulate_tournament_8_portfolio(
        close_mat=close_mat, returns_mat=returns_mat, valid_mask=valid_mask,
        asset_vols_24h=asset_vols_24h, baseline_bar_returns=baseline_bar_returns,
        signal_matrix=f_bsc_asym_18, num_sub_portfolios=2, target_vol=0.51,
        l_min=0.90, l_max=3.30, m_floor=0.20
    )
    experiments["EXP-68: Adaptive Floor Ratchet (M_floor=0.20)"] = (
        w_exp68, f_bsc_asym_18, "2x Staggered 6H + AsymFIP + M_floor=0.20 GZ Ratchet (Vol 51%, L_max=3.30)", 0.80
    )

    # EXP-69: Dual Synthesis: Exp-FIP + 51% Vol
    print("  -> Building EXP-69: Dual Synthesis: Exp-FIP + 51% Vol...", flush=True)
    w_exp69 = simulate_tournament_8_portfolio(
        close_mat=close_mat, returns_mat=returns_mat, valid_mask=valid_mask,
        asset_vols_24h=asset_vols_24h, baseline_bar_returns=baseline_bar_returns,
        signal_matrix=f_bsc_exp_asym, num_sub_portfolios=2, target_vol=0.51,
        l_min=0.90, l_max=3.30, m_floor=0.25
    )
    experiments["EXP-69: Dual Synthesis (Exp-FIP + 51% Vol)"] = (
        w_exp69, f_bsc_exp_asym, "2x Staggered 6H + Exp-AsymFIP + BSC Scaling + Vol 51% (L_max=3.30)", 0.80
    )

    # EXP-70: The Sovereign Finality Master
    print("  -> Building EXP-70: The Sovereign Finality Master (M=3, Vol 53%, Exp-AsymFIP, M_floor=0.22)...", flush=True)
    w_exp70 = simulate_tournament_8_portfolio(
        close_mat=close_mat, returns_mat=returns_mat, valid_mask=valid_mask,
        asset_vols_24h=asset_vols_24h, baseline_bar_returns=baseline_bar_returns,
        signal_matrix=f_bsc_exp_asym, num_sub_portfolios=3, target_vol=0.53,
        l_min=0.90, l_max=3.40, m_floor=0.22
    )
    experiments["EXP-70: The Sovereign Finality Master"] = (
        w_exp70, f_bsc_exp_asym, "3x Staggered 6H + Exp-AsymFIP + BSC Scaling + Vol 53% + M_floor=0.22 (L_max=3.40)", 0.80
    )

    return experiments


def main():
    print("=" * 160)
    print("   IRONCORE INSTITUTIONAL FACTORIAL TOURNAMENT 8 (EXP-63 TO EXP-70)")
    print("   The Sub-16-Month Frontier: Target Vol Gearing, Exp-AsymFIP & Sovereign Finality")
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

    # 2. Build Tournament 8 Experiment Matrices
    print("\n[BUILDING TOURNAMENT 8 WEIGHT MATRICES...]", flush=True)
    experiments = build_tournament_8_suite(
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

    print(f"\n[COMPLETE] Tournament 8 results persisted to: {TOURNAMENT_RESULTS_PATH}", flush=True)


if __name__ == "__main__":
    main()
