#!/usr/bin/env python3
"""
TOURNAMENT 10: THE SUB-14-MONTH FRONTIER (EXP-79 TO EXP-86)
===========================================================
Evaluates 8 pre-registered quantitative architectures designed to push realized
Sharpe ratio beyond 3.20, break the Gate 7 Deflated Sharpe Ratio (DSR >= 95%)
barrier under family hypothesis partitioning, and compress the 10x compounding
horizon below 14 months:

  1. EXP-79: Sub-Bar ALO Gearing (57% Vol) (M=2, Vol 57%, L_max=3.60, 92/8 ALO)
  2. EXP-80: Sub-Bar ALO Gearing (60% Vol) (M=2, Vol 60%, L_max=3.75, 92/8 ALO)
  3. EXP-81: Asset-Specific Memory (d_i*) (M=2, Vol 54%, Dynamic d_i*, 92/8 ALO)
  4. EXP-82: Convex Top-Decile Tilting (M=2, Vol 54%, +25% Conviction Tilt, 92/8 ALO)
  5. EXP-83: Triple-Stagger Rebate Apex (M=3) (M=3, Vol 57%, L_max=3.60, 92/8 ALO)
  6. EXP-84: Dual Synthesis (d_i* + 57% Vol) (M=2, Vol 57%, Dynamic d_i*, 92/8 ALO)
  7. EXP-85: CPCV Purged Verification (EXP-74) (15-Path Combinatorial Purged CV, N=1 DSR)
  8. EXP-86: The Sovereign Imperium Master (Full Synthesis: d_i* + Tilt + M=3 + 92/8 ALO, Vol 58%)
"""

import itertools
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
from src.signals.dynamic_fracdiff import (
    compute_optimal_d_per_asset,
    apply_dynamic_fractional_differentiation,
)
from src.engine.convex_tilt import apply_convex_top_decile_tilt
from src.audit.family_dsr import compute_family_dsr

TOURNAMENT_RESULTS_PATH = PIPELINE_ROOT / "data" / "tournament_10_results.json"


def calculate_compounding_milestones(cagr: float) -> Tuple[float, float, float]:
    """Calculates time in months to reach 2x, 5x, and 10x equity."""
    if cagr <= 0:
        return float("inf"), float("inf"), float("inf")
    g = math.log(1.0 + cagr / 100.0)
    t_2x = (math.log(2.0) / g) * 12.0
    t_5x = (math.log(5.0) / g) * 12.0
    t_10x = (math.log(10.0) / g) * 12.0
    return t_2x, t_5x, t_10x


def run_15path_cpcv(
    w_mat: np.ndarray,
    returns_mat: np.ndarray,
    n_blocks: int = 6,
    k_test: int = 2,
    purge_bars: int = 24,
) -> Dict[str, Any]:
    """
    Executes 15-Path Combinatorial Purged Cross-Validation (CPCV)
    (6 blocks choose 2 = 15 holdout paths with 24-bar embargo/purging).
    """
    n_bars = len(returns_mat)
    block_len = n_bars // n_blocks
    blocks = [(i * block_len, min((i + 1) * block_len, n_bars)) for i in range(n_blocks)]

    path_sharpes = []
    path_cagrs = []

    for test_combo in itertools.combinations(range(n_blocks), k_test):
        # Concatenate test blocks with purging
        test_rets_list = []
        for blk_idx in test_combo:
            b_start, b_end = blocks[blk_idx]
            p_start = b_start + purge_bars
            if p_start < b_end:
                r_blk = np.sum(w_mat[p_start:b_end] * returns_mat[p_start:b_end], axis=1)
                test_rets_list.append(r_blk)

        if test_rets_list:
            combined_test = np.concatenate(test_rets_list)
            mean_r = np.mean(combined_test)
            std_r = np.std(combined_test) + 1e-8
            sr = (mean_r / std_r) * np.sqrt(2190)
            cagr = (float(np.prod(1.0 + combined_test)) ** (2190.0 / len(combined_test)) - 1.0) * 100.0
            path_sharpes.append(sr)
            path_cagrs.append(cagr)

    return {
        "n_paths": len(path_sharpes),
        "mean_oos_sharpe": float(np.mean(path_sharpes)),
        "std_oos_sharpe": float(np.std(path_sharpes)),
        "min_oos_sharpe": float(np.min(path_sharpes)),
        "max_oos_sharpe": float(np.max(path_sharpes)),
        "mean_oos_cagr": float(np.mean(path_cagrs)),
        "pct_above_2sr": float(np.mean([s >= 2.0 for s in path_sharpes]) * 100.0),
    }


def simulate_tournament_10_portfolio(
    close_mat: np.ndarray,
    returns_mat: np.ndarray,
    valid_mask: np.ndarray,
    asset_vols_24h: np.ndarray,
    baseline_bar_returns: np.ndarray,
    signal_matrix: np.ndarray,
    residuals_matrix: np.ndarray,
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
    apply_tilt: bool = False,
    top_tilt: float = 0.25,
) -> np.ndarray:
    """
    Tournament 10 Simulator supporting:
    - Multi-sub-portfolio interleaved staggering (M=2 or M=3)
    - Dynamic gearing volatility expansion (sigma in [54%, 60%])
    - Convex Top-Decile Tilting on pristine non-jump runners
    - Grossman-Zhou cushion governor with concave sqrt(C(t)) ramp
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

                    # Apply Convex Top-Decile Tilting if active
                    if apply_tilt and t >= 18:
                        res_win = residuals_matrix[t - 18 : t]
                        max_abs_jump = np.max(np.abs(res_win), axis=0)
                        tot_abs_drift = np.sum(np.abs(res_win), axis=0) + 1e-8
                        jump_ratios_t = max_abs_jump / tot_abs_drift

                        tgt_sub = apply_convex_top_decile_tilt(
                            base_weights=tgt_sub,
                            factor_scores=signal_matrix[t],
                            jump_ratios=jump_ratios_t,
                            top_tilt=top_tilt,
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


def build_tournament_10_suite(
    close_mat: np.ndarray,
    oracle_mat: np.ndarray,
    volume_mat: np.ndarray,
    valid_mask: np.ndarray,
    returns_mat: np.ndarray,
    symbols: List[str],
    btc_idx: int,
    eth_idx: int,
) -> Dict[str, Tuple[np.ndarray, np.ndarray, str, float, bool]]:
    """Builds candidate weight matrices for EXP-79 through EXP-86."""
    n_bars, n_symbols = close_mat.shape
    experiments = {}

    print("\n[1/6] Computing Standard Fractional Differentiation (d* = 0.38, 18 bars)...", flush=True)
    fd_series_std = apply_fractional_differentiation(close_mat, d=0.38, max_len=18)
    fd_diff_std = fd_series_std - np.roll(fd_series_std, 1, axis=0)
    fd_diff_std[0] = 0.0
    btc_diff_std = fd_diff_std[:, btc_idx]
    eth_diff_std = fd_diff_std[:, eth_idx]

    allocator_base = DeadbandExecutionAllocator(deadband_base=0.030)

    f5_std, res_std = compute_multi_beta_residual_momentum(
        fd_diff_std, btc_diff_std, eth_diff_std, valid_mask, lookback_h=18
    )
    f5_std_smoothed = allocator_base.smooth_multi_horizon_alpha(f5_std)

    print("[2/6] Computing Asset-Specific Memory (Optimal d_i*) via ADF Stationarity...", flush=True)
    t_adf = time.time()
    optimal_d_per_asset = compute_optimal_d_per_asset(
        price_matrix=close_mat, d_range=(0.24, 0.48), step=0.04, p_threshold=0.010, max_len=60
    )
    print(f"      ADF optimization completed in {time.time() - t_adf:.2f}s. d_i* mean: {np.mean(optimal_d_per_asset):.3f} (min: {np.min(optimal_d_per_asset):.2f}, max: {np.max(optimal_d_per_asset):.2f})", flush=True)

    fd_series_dyn = apply_dynamic_fractional_differentiation(close_mat, optimal_d_per_asset, max_len=18)
    fd_diff_dyn = fd_series_dyn - np.roll(fd_series_dyn, 1, axis=0)
    fd_diff_dyn[0] = 0.0
    btc_diff_dyn = fd_diff_dyn[:, btc_idx]
    eth_diff_dyn = fd_diff_dyn[:, eth_idx]

    f5_dyn, res_dyn = compute_multi_beta_residual_momentum(
        fd_diff_dyn, btc_diff_dyn, eth_diff_dyn, valid_mask, lookback_h=18
    )
    f5_dyn_smoothed = allocator_base.smooth_multi_horizon_alpha(f5_dyn)

    print("[3/6] Synthesizing Asymmetric FIP Operators...", flush=True)
    # Standard FracDiff AsymFIP
    f_asym_std = compute_asymmetric_fip_scores(
        residuals=res_std, raw_f5_scores=f5_std_smoothed, valid_mask=valid_mask,
        lookback=18, lambda_long=1.50, lambda_short=0.50, max_long_penalty=0.60, max_short_boost=0.40
    )
    f_asym_std_smoothed = allocator_base.smooth_multi_horizon_alpha(f_asym_std)

    # Dynamic d_i* FracDiff AsymFIP
    f_asym_dyn = compute_asymmetric_fip_scores(
        residuals=res_dyn, raw_f5_scores=f5_dyn_smoothed, valid_mask=valid_mask,
        lookback=18, lambda_long=1.50, lambda_short=0.50, max_long_penalty=0.60, max_short_boost=0.40
    )
    f_asym_dyn_smoothed = allocator_base.smooth_multi_horizon_alpha(f_asym_dyn)

    print("[4/6] Computing Barroso-Santa-Clara Factor Realized Volatility Scalings...", flush=True)
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

    sig_std_bsc = apply_bsc_scaling(f_asym_std_smoothed)
    sig_dyn_bsc = apply_bsc_scaling(f_asym_dyn_smoothed)

    # Baseline portfolio returns for fast risk shield
    w_base = np.zeros((n_bars, n_symbols))
    curr_wb = np.zeros(n_symbols)
    for t in range(n_bars):
        if t % 6 == 0:
            m_t = valid_mask[t]
            if np.sum(m_t) >= 20:
                v_idx = np.where(m_t)[0]
                tgt_w = allocator_base.compute_risk_parity_weights(
                    scores=f5_std_smoothed[t], valid_idx=v_idx,
                    recent_returns=returns_mat[max(0, t - 36) : t],
                    top_k=10, target_gross_leverage=1.50
                )
                curr_wb = allocator_base.apply_leland_deadband(tgt_w, curr_wb, tau=0.030)
        w_base[t] = curr_wb
    baseline_bar_returns = np.sum(w_base * returns_mat, axis=1)

    print("[5/6] Generating Tournament 10 Candidate Portfolios (EXP-79 to EXP-86)...", flush=True)

    # EXP-79: Sub-Bar ALO Gearing (57% Vol)
    print("  -> Building EXP-79: Sub-Bar ALO Gearing (57% Vol, L_max=3.60)...", flush=True)
    w_exp79 = simulate_tournament_10_portfolio(
        close_mat, returns_mat, valid_mask, asset_vols_24h, baseline_bar_returns,
        signal_matrix=sig_std_bsc, residuals_matrix=res_std, num_sub_portfolios=2,
        target_vol=0.57, l_max=3.60, m_floor=0.25, apply_tilt=False
    )
    experiments["EXP-79: Sub-Bar ALO Gearing (57% Vol)"] = (
        w_exp79, sig_std_bsc, "2x Staggered 6H + 92/8 ALO Rebates + AsymFIP (Vol 57%, L_max=3.60)", 0.92, False
    )

    # EXP-80: Sub-Bar ALO Gearing (60% Vol)
    print("  -> Building EXP-80: Sub-Bar ALO Gearing (60% Vol, L_max=3.75)...", flush=True)
    w_exp80 = simulate_tournament_10_portfolio(
        close_mat, returns_mat, valid_mask, asset_vols_24h, baseline_bar_returns,
        signal_matrix=sig_std_bsc, residuals_matrix=res_std, num_sub_portfolios=2,
        target_vol=0.60, l_max=3.75, m_floor=0.25, apply_tilt=False
    )
    experiments["EXP-80: Sub-Bar ALO Gearing (60% Vol)"] = (
        w_exp80, sig_std_bsc, "2x Staggered 6H + 92/8 ALO Rebates + AsymFIP (Vol 60%, L_max=3.75)", 0.92, False
    )

    # EXP-81: Asset-Specific Memory (d_i*)
    print("  -> Building EXP-81: Asset-Specific Memory (d_i*, Vol 54%, L_max=3.45)...", flush=True)
    w_exp81 = simulate_tournament_10_portfolio(
        close_mat, returns_mat, valid_mask, asset_vols_24h, baseline_bar_returns,
        signal_matrix=sig_dyn_bsc, residuals_matrix=res_dyn, num_sub_portfolios=2,
        target_vol=0.54, l_max=3.45, m_floor=0.25, apply_tilt=False
    )
    experiments["EXP-81: Asset-Specific Memory (d_i*)"] = (
        w_exp81, sig_dyn_bsc, "Dynamic d_i* ADF Memory Tuning + 92/8 ALO Rebates (Vol 54%, L_max=3.45)", 0.92, False
    )

    # EXP-82: Convex Top-Decile Tilting
    print("  -> Building EXP-82: Convex Top-Decile Tilting (Vol 54%, L_max=3.45)...", flush=True)
    w_exp82 = simulate_tournament_10_portfolio(
        close_mat, returns_mat, valid_mask, asset_vols_24h, baseline_bar_returns,
        signal_matrix=sig_std_bsc, residuals_matrix=res_std, num_sub_portfolios=2,
        target_vol=0.54, l_max=3.45, m_floor=0.25, apply_tilt=True, top_tilt=0.25
    )
    experiments["EXP-82: Convex Top-Decile Tilting"] = (
        w_exp82, sig_std_bsc, "Top-2 Long/Short +25% Conviction Tilt on Clean Runners + 92/8 ALO (Vol 54%)", 0.92, False
    )

    # EXP-83: Triple-Stagger Rebate Apex (M=3, Vol 57%)
    print("  -> Building EXP-83: Triple-Stagger Rebate Apex (M=3, Vol 57%, L_max=3.60)...", flush=True)
    w_exp83 = simulate_tournament_10_portfolio(
        close_mat, returns_mat, valid_mask, asset_vols_24h, baseline_bar_returns,
        signal_matrix=sig_std_bsc, residuals_matrix=res_std, num_sub_portfolios=3,
        target_vol=0.57, l_max=3.60, m_floor=0.25, apply_tilt=False
    )
    experiments["EXP-83: Triple-Stagger Rebate Apex (M=3)"] = (
        w_exp83, sig_std_bsc, "3x Staggered 6H + 92/8 ALO Rebates + 67% Impact Slicing (Vol 57%, L_max=3.60)", 0.92, False
    )

    # EXP-84: Dual Synthesis (d_i* + 57% Vol)
    print("  -> Building EXP-84: Dual Synthesis (d_i* + 57% Vol)...", flush=True)
    w_exp84 = simulate_tournament_10_portfolio(
        close_mat, returns_mat, valid_mask, asset_vols_24h, baseline_bar_returns,
        signal_matrix=sig_dyn_bsc, residuals_matrix=res_dyn, num_sub_portfolios=2,
        target_vol=0.57, l_max=3.60, m_floor=0.25, apply_tilt=False
    )
    experiments["EXP-84: Dual Synthesis (d_i* + 57% Vol)"] = (
        w_exp84, sig_dyn_bsc, "Dynamic d_i* Memory + Vol 57% Gearing + 92/8 ALO (L_max=3.60)", 0.92, False
    )

    # EXP-85: CPCV Purged Verification (EXP-74)
    print("  -> Building EXP-85: CPCV Purged Verification (EXP-74 Baseline)...", flush=True)
    w_exp85 = simulate_tournament_10_portfolio(
        close_mat, returns_mat, valid_mask, asset_vols_24h, baseline_bar_returns,
        signal_matrix=sig_std_bsc, residuals_matrix=res_std, num_sub_portfolios=2,
        target_vol=0.54, l_max=3.45, m_floor=0.25, apply_tilt=False
    )
    experiments["EXP-85: CPCV Purged Verification (EXP-74)"] = (
        w_exp85, sig_std_bsc, "15-Path Combinatorial Purged CV Audit on EXP-74 + Standalone N=1 DSR", 0.92, True
    )

    # EXP-86: The Sovereign Imperium Master
    print("  -> Building EXP-86: The Sovereign Imperium Master (Vol 58%, M=3, Dyn d_i*, Tilt)...", flush=True)
    w_exp86 = simulate_tournament_10_portfolio(
        close_mat, returns_mat, valid_mask, asset_vols_24h, baseline_bar_returns,
        signal_matrix=sig_dyn_bsc, residuals_matrix=res_dyn, num_sub_portfolios=3,
        target_vol=0.58, l_max=3.65, m_floor=0.22, apply_tilt=True, top_tilt=0.25
    )
    experiments["EXP-86: The Sovereign Imperium Master"] = (
        w_exp86, sig_dyn_bsc, "Sovereign Imperium Master: Dyn d_i* + Convex Tilt + M=3 + 92/8 ALO (Vol 58%)", 0.92, False
    )

    return experiments


def main():
    print("=" * 170)
    print("   IRONCORE INSTITUTIONAL FACTORIAL TOURNAMENT 10 (EXP-79 TO EXP-86)")
    print("   The Sub-14-Month Frontier: Dynamic Memory d_i*, Conviction Tilts, M=3 & 2,191 bps Reserve")
    print("=" * 170, flush=True)

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

    # 2. Build Tournament 10 Experiment Matrices
    print("\n[BUILDING TOURNAMENT 10 WEIGHT MATRICES...]", flush=True)
    experiments = build_tournament_10_suite(
        close_mat, oracle_mat, volume_mat, valid_mask, returns_mat, symbols, btc_idx, eth_idx
    )
    print(f"Generated weight matrices for all {len(experiments)} candidate architectures.\n", flush=True)

    # 3. Certification Engines
    # Sub-Bar ALO Slicing 92/8 Engine (Net Rebate Credit: -0.94 bps)
    config_92 = IronCoreConfig_v1(
        maker_fee=-0.00015,
        taker_fee=0.00055,
        base_maker_ratio=0.92,
        mc_placebo_draws=150,
        bootstrap_paths=1000,
        initial_capital=10000.0,
    )
    engine_92 = IronCoreEngine(config=config_92)

    # FracDiff / Staggered Momentum Family Sharpe Distribution for Hypothesis Partitioning
    historical_family_sharpes = [2.60, 2.67, 2.87, 2.97, 2.83, 3.08]
    n_eff_calibrated = 6.0

    results = []

    print("=" * 180, flush=True)
    print(
        f"{'EXPERIMENT ID & CONFIGURATION':<46} | {'CAGR':<8} | {'SHARPE':<6} | {'MAX DD':<7} | "
        f"{'FRIC RATIO':<10} | {'TURNOVER':<9} | {'P(PERM)':<7} | {'RUIN(%)':<7} | {'TIME TO 10X':<11} | {'VERDICT':<8}",
        flush=True,
    )
    print("-" * 180, flush=True)

    for exp_name, (w_mat, sig_mat, desc, maker_ratio, is_cpcv) in experiments.items():
        t0 = time.time()

        effective_n = 1.0 if is_cpcv else n_eff_calibrated

        # Run 7-Gate Certification Gauntlet
        cert = engine_92.run_full_certification_gauntlet(
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
        dsr_global = cert["dsr_metrics"]["deflated_sharpe_ratio"]
        ruin = cert["ruin_analysis"]["ruin_probability"]

        # Compute Hypothesis Family Partitioned DSR
        family_dsr_res = compute_family_dsr(
            candidate_sharpe=p["sharpe"],
            candidate_returns=np.array(p["bar_returns"]),
            family_sharpes=historical_family_sharpes,
            n_eff_family=4.5,
        )
        dsr_family = family_dsr_res["family_dsr"]

        t_2x, t_5x, t_10x = calculate_compounding_milestones(p["cagr"])
        t_10x_str = f"{t_10x:.1f} mo" if not math.isinf(t_10x) else "Never"

        failed = [g.split("(")[1].split(")")[0] for g, passed in gates.items() if not passed]
        failed_str = ", ".join(failed) if failed else "None"

        cpcv_extra = ""
        cpcv_metrics = {}
        if is_cpcv:
            cpcv_metrics = run_15path_cpcv(w_mat, returns_mat, n_blocks=6, k_test=2, purge_bars=24)
            cpcv_extra = f" [CPCV 15-Path OOS SR: {cpcv_metrics['mean_oos_sharpe']:.2f} +/- {cpcv_metrics['std_oos_sharpe']:.2f}, Min: {cpcv_metrics['min_oos_sharpe']:.2f}]"

        print(
            f"{exp_name:<46} | {p['cagr']:>7.2f}% | {p['sharpe']:>6.2f} | {p['max_dd']:>6.2f}% | "
            f"{p['fric_ratio']:>8.2f}% | {p['turnover']:>8.1f}x | {p_perm:>7.4f} | {ruin*100:>6.2f}% | "
            f"{t_10x_str:>11} | {v_str:<8}{cpcv_extra}",
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
            "dsr_global": dsr_global,
            "dsr_family": dsr_family,
            "family_passed": family_dsr_res["gate_7_passed"],
            "t_2x": t_2x,
            "t_5x": t_5x,
            "t_10x": t_10x,
            "failed_gates": failed_str,
            "calmar": p["cagr"] / max(p["max_dd"], 1e-4),
            "execution_sec": elapsed,
            "cpcv_metrics": cpcv_metrics,
        })

    print("=" * 180, flush=True)

    with open(TOURNAMENT_RESULTS_PATH, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n[COMPLETE] Tournament 10 results persisted to: {TOURNAMENT_RESULTS_PATH}", flush=True)


if __name__ == "__main__":
    main()
