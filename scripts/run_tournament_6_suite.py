#!/usr/bin/env python3
"""
TOURNAMENT 6: THE SUB-20-MONTH FRONTIER (EXP-47 TO EXP-54)
=========================================================
Evaluates 8 pre-registered quantitative architectures designed to smash through
the Gate 3 friction ceiling (24.84% in EXP-45) and compress the 10x compounding
horizon below 18-20 months:

  1. EXP-47: ADV-Pruned Frontier (Top 75 ADV Filter + FracDiff Core, Vol 48%)
  2. EXP-48: FIP Momentum Quality (FracDiff + Information Discreteness, Vol 48%)
  3. EXP-49: Idiosyncratic t-Statistic (Newey-West Residual t-Stat Sizing, Vol 48%)
  4. EXP-50: Interleaved Stagger (M=2) (2x Staggered 6H, Vol 48%)
  5. EXP-51: Interleaved Stagger (M=3) (3x Staggered 6H, Vol 48%)
  6. EXP-52: Compounding Expansion (52% Vol) (2x Staggered 6H + ADV Pruning, Vol 52%)
  7. EXP-53: Compounding Expansion (55% Vol) (2x Staggered 6H + ADV Pruning, Vol 55%)
  8. EXP-54: The Apex Grand Synthesis (2x Staggered 6H + FIP + ADV Pruning, Vol 52%)
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

TOURNAMENT_RESULTS_PATH = PIPELINE_ROOT / "data" / "tournament_6_results.json"


def calculate_compounding_milestones(cagr: float) -> Tuple[float, float, float]:
    """Calculates time in months to reach 2x, 5x, and 10x equity."""
    if cagr <= 0:
        return float("inf"), float("inf"), float("inf")
    g = math.log(1.0 + cagr / 100.0)
    t_2x = (math.log(2.0) / g) * 12.0
    t_5x = (math.log(5.0) / g) * 12.0
    t_10x = (math.log(10.0) / g) * 12.0
    return t_2x, t_5x, t_10x


def compute_rolling_adv_dollars(volume_mat: np.ndarray, close_mat: np.ndarray, window: int = 6) -> np.ndarray:
    """Computes rolling 24-hour dollar volume across all assets (6 x 4H bars = 24H)."""
    n_bars, n_symbols = close_mat.shape
    dollar_vol = np.nan_to_num(volume_mat * close_mat, nan=0.0)
    adv_24h = np.zeros_like(dollar_vol)
    for t in range(window, n_bars):
        adv_24h[t] = np.sum(dollar_vol[t - window : t], axis=0)
    adv_24h[:window] = adv_24h[window]
    return adv_24h


def compute_fip_quality_factor(
    residuals: np.ndarray,
    raw_f5_scores: np.ndarray,
    valid_mask: np.ndarray,
    allocator_base: DeadbandExecutionAllocator,
    lookback: int = 18,
) -> np.ndarray:
    """
    Vector 2: Frog-in-the-Pan (FIP) Momentum Quality Factor.
    Penalizes tokens whose 72H momentum was driven by an isolated outlier wick.
    """
    n_bars, n_symbols = raw_f5_scores.shape
    f_fip = np.zeros_like(raw_f5_scores)

    for t in range(lookback, n_bars):
        m_t = valid_mask[t]
        if np.sum(m_t) >= 10:
            res_win = residuals[t - lookback : t]  # shape (lookback, n_symbols)
            max_abs_jump = np.max(np.abs(res_win), axis=0)
            total_abs_drift = np.sum(np.abs(res_win), axis=0) + 1e-8
            jump_ratio = max_abs_jump / total_abs_drift

            # Information Discreteness: proportion of positive vs negative returns
            num_pos = (res_win > 0).sum(axis=0)
            num_neg = (res_win < 0).sum(axis=0)
            id_measure = np.abs(num_pos - num_neg) / float(lookback)

            # Continuous quality multiplier: downweight assets driven by large jumps
            fip_quality_multiplier = 1.0 - np.clip(jump_ratio * 1.50, 0.0, 0.60)
            f_fip[t] = raw_f5_scores[t] * fip_quality_multiplier

    f_fip[:lookback] = f_fip[lookback]
    return allocator_base.smooth_multi_horizon_alpha(f_fip)


def compute_idiosyncratic_tstat_factor(
    residuals: np.ndarray,
    valid_mask: np.ndarray,
    allocator_base: DeadbandExecutionAllocator,
    lookback: int = 18,
) -> np.ndarray:
    """
    Vector 3: Idiosyncratic t-Statistic Sizing (Residual Volatility Weighting).
    Ranks assets by their Newey-West serial-correlation adjusted t-statistic of drift.
    """
    n_bars, n_symbols = residuals.shape
    f_tstat = np.zeros((n_bars, n_symbols))

    for t in range(lookback, n_bars):
        m_t = valid_mask[t]
        v_idx = np.where(m_t)[0]
        if len(v_idx) >= 10:
            res_win = residuals[t - lookback : t, v_idx]  # (lookback, len(v_idx))
            mean_drift = np.mean(res_win, axis=0)
            var_drift = np.var(res_win, axis=0, ddof=1) + 1e-8

            # Lag-1 and Lag-2 sample autocorrelations
            cov_1 = np.mean((res_win[1:] - mean_drift) * (res_win[:-1] - mean_drift), axis=0)
            rho_1 = np.clip(cov_1 / var_drift, -0.50, 0.50)
            cov_2 = np.mean((res_win[2:] - mean_drift) * (res_win[:-2] - mean_drift), axis=0)
            rho_2 = np.clip(cov_2 / var_drift, -0.50, 0.50)

            # Bartlett kernel Newey-West adjustment
            nw_factor = np.maximum(0.20, 1.0 + 2.0 * ((2.0 / 3.0) * rho_1 + (1.0 / 3.0) * rho_2))
            se_drift = np.sqrt((var_drift / float(lookback)) * nw_factor) + 1e-8
            raw_t = mean_drift / se_drift

            t_std = np.std(raw_t) + 1e-8
            f_tstat[t, v_idx] = (raw_t - np.mean(raw_t)) / t_std

    f_tstat[:lookback] = f_tstat[lookback]
    return allocator_base.smooth_multi_horizon_alpha(f_tstat)


def simulate_tournament_6_portfolio(
    close_mat: np.ndarray,
    returns_mat: np.ndarray,
    valid_mask: np.ndarray,
    adv_24h: np.ndarray,
    asset_vols_24h: np.ndarray,
    baseline_bar_returns: np.ndarray,
    signal_matrix: np.ndarray,
    num_sub_portfolios: int,      # 1 (single), 2, 3
    target_vol: float,            # 0.48, 0.52, 0.55
    use_adv_pruning: bool,        # True / False
    l_min: float = 0.90,
    l_max: float = 3.20,
    target_k: int = 12,
    entry_k: int = 8,
    exit_k: int = 18,
    delta_l_thresh: float = 0.20,
    m_floor: float = 0.25,
    use_dynamic_tau: bool = True,
) -> np.ndarray:
    """
    Unified multi-sub-portfolio simulation engine supporting:
    - 6H Single Portfolio execution (EXP-47, EXP-48, EXP-49)
    - 2x and 3x Interleaved Staggered execution (EXP-50, EXP-51, EXP-52, EXP-53, EXP-54)
    - Dynamic ADV Tier Pruning (Vector 4)
    - Concave cushion leverage scaling sqrt(C(t))
    - Dynamic volatility deadband tau_i
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

        def is_6h_alpha_step(step_idx: int) -> bool:
            return (step_idx % 3 == 0) or (step_idx % 3 == 1)

        for t in range(n_bars):
            if t > 0:
                bar_pnl = float(np.sum(w_mat[t - 1] * returns_mat[t]))
                cum_nav *= (1.0 + bar_pnl)

            # Continuous Fast Risk Shield on EVERY 4H bar
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
            v_idx_all = np.where(m_t)[0]

            if len(v_idx_all) >= (allocator.exit_k * 2):
                if use_adv_pruning:
                    adv_t = adv_24h[t, v_idx_all]
                    n_keep = min(75, max(36, int(len(v_idx_all) * 0.70)))
                    order_adv = np.argsort(-adv_t)
                    eligible_cand = v_idx_all[order_adv[:n_keep]]
                    high_liq = [idx for idx in eligible_cand if adv_24h[t, idx] >= 5_000_000]
                    v_idx = np.array(high_liq) if len(high_liq) >= 36 else eligible_cand
                else:
                    v_idx = v_idx_all

                if is_6h_alpha_step(t):
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

                if use_dynamic_tau:
                    vols_t = asset_vols_24h[t]
                    med_vol = np.median(vols_t[v_idx]) if len(v_idx) > 0 else 0.80
                    tau_i = np.clip(0.030 * np.sqrt(vols_t / (med_vol + 1e-8)), 0.015, 0.050)
                    dw = tgt_w - curr_w
                    exec_mask = np.abs(dw) >= tau_i
                    curr_w = np.where(exec_mask, tgt_w, curr_w)
                else:
                    curr_w = allocator.apply_leland_deadband(tgt_w, curr_w, tau=0.030)

            w_mat[t] = curr_w

        return w_mat

    else:
        # Multi-Sub-Portfolio Interleaved Staggering (M=2 or M=3)
        sub_allocators = [
            RankBufferAllocator(target_k=entry_k, entry_k=entry_k, exit_k=int(entry_k * 2.0), deadband_tau=0.030)
            for _ in range(num_sub_portfolios)
        ]
        sub_w = np.zeros((num_sub_portfolios, n_symbols))

        def should_sub_rebalance(sub_idx: int, step_idx: int) -> bool:
            if num_sub_portfolios == 2:
                # 6H cadence for both:
                # Sub 0 on bars (0, 1 mod 3), Sub 1 on bars (1, 2 mod 3)
                if sub_idx == 0:
                    return (step_idx % 3 == 0) or (step_idx % 3 == 1)
                elif sub_idx == 1:
                    return (step_idx % 3 == 1) or (step_idx % 3 == 2)
            elif num_sub_portfolios == 3:
                # Rotated 6H cadence across 3 sub-portfolios
                mod6 = step_idx % 6
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

            # Continuous Fast Risk Shield on EVERY 4H bar
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
            v_idx_all = np.where(m_t)[0]

            if len(v_idx_all) >= 32:
                if use_adv_pruning:
                    adv_t = adv_24h[t, v_idx_all]
                    n_keep = min(75, max(32, int(len(v_idx_all) * 0.70)))
                    order_adv = np.argsort(-adv_t)
                    eligible_cand = v_idx_all[order_adv[:n_keep]]
                    high_liq = [idx for idx in eligible_cand if adv_24h[t, idx] >= 5_000_000]
                    v_idx = np.array(high_liq) if len(high_liq) >= 32 else eligible_cand
                else:
                    v_idx = v_idx_all

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

                if use_dynamic_tau:
                    vols_t = asset_vols_24h[t]
                    med_vol = np.median(vols_t[v_idx]) if len(v_idx) > 0 else 0.80
                    tau_i = np.clip(0.030 * np.sqrt(vols_t / (med_vol + 1e-8)), 0.015, 0.050)
                    dw = blended_target - curr_w
                    exec_mask = np.abs(dw) >= tau_i
                    curr_w = np.where(exec_mask, blended_target, curr_w)
                else:
                    dw = blended_target - curr_w
                    exec_mask = np.abs(dw) >= 0.030
                    curr_w = np.where(exec_mask, blended_target, curr_w)

            w_mat[t] = curr_w

        return w_mat


def build_tournament_6_suite(
    close_mat: np.ndarray,
    oracle_mat: np.ndarray,
    volume_mat: np.ndarray,
    valid_mask: np.ndarray,
    returns_mat: np.ndarray,
    symbols: List[str],
    btc_idx: int,
    eth_idx: int,
) -> Dict[str, Tuple[np.ndarray, np.ndarray, str, float]]:
    """Builds weight matrices for EXP-47 through EXP-54."""
    n_bars, n_symbols = close_mat.shape
    experiments = {}

    print("\n[1/5] Extracting Fractional Differentiation (d* = 0.38) & Multi-Beta Residual Momentum...")
    fd_series_38 = apply_fractional_differentiation(close_mat, d=0.38, max_len=18)
    fd_diff_38 = fd_series_38 - np.roll(fd_series_38, 1, axis=0)
    fd_diff_38[0] = 0.0
    f5_38, residuals = compute_multi_beta_residual_momentum(
        fd_diff_38, fd_diff_38[:, btc_idx], fd_diff_38[:, eth_idx], valid_mask, lookback_h=18
    )

    allocator_base = DeadbandExecutionAllocator(deadband_base=0.030)
    f5_smoothed = allocator_base.smooth_multi_horizon_alpha(f5_38)

    print("[2/5] Computing ADV 24-Hour Liquidity Field (Vector 4)...")
    adv_24h = compute_rolling_adv_dollars(volume_mat, close_mat, window=6)

    print("[3/5] Synthesizing Frog-in-the-Pan (FIP) Momentum Quality Factor (Vector 2)...")
    f_fip_smoothed = compute_fip_quality_factor(residuals, f5_smoothed, valid_mask, allocator_base, lookback=18)

    print("[4/5] Synthesizing Idiosyncratic Newey-West t-Statistic Factor (Vector 3)...")
    f_tstat_smoothed = compute_idiosyncratic_tstat_factor(residuals, valid_mask, allocator_base, lookback=18)

    print("[5/5] Computing Baseline Volatilities & Fast Risk Shield Benchmarks...")
    asset_vols_24h = np.zeros((n_bars, n_symbols))
    for t in range(6, n_bars):
        asset_vols_24h[t] = np.std(returns_mat[t - 6 : t], axis=0) * np.sqrt(365.25 * 6)
    asset_vols_24h[:6] = asset_vols_24h[6]

    w_baseline_raw = np.zeros((n_bars, n_symbols))
    curr_w = np.zeros(n_symbols)
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
                curr_w = allocator_base.apply_leland_deadband(tgt_w, curr_w, tau=0.030)
        w_baseline_raw[t] = curr_w

    baseline_bar_returns = np.sum(w_baseline_raw * returns_mat, axis=1)

    print("\n--- Generating Tournament 6 Candidate Portfolios (EXP-47 to EXP-54) ---")

    # EXP-47: ADV-Pruned Frontier
    print("  -> Building EXP-47: ADV-Pruned Frontier...")
    w_exp47 = simulate_tournament_6_portfolio(
        close_mat=close_mat, returns_mat=returns_mat, valid_mask=valid_mask, adv_24h=adv_24h,
        asset_vols_24h=asset_vols_24h, baseline_bar_returns=baseline_bar_returns,
        signal_matrix=f5_smoothed, num_sub_portfolios=1, target_vol=0.48, use_adv_pruning=True,
        l_min=0.90, l_max=3.20, target_k=12, entry_k=8, exit_k=18, use_dynamic_tau=True
    )
    experiments["EXP-47: ADV-Pruned Frontier"] = (
        w_exp47, f5_smoothed, "Top 75 ADV Filter + FracDiff Core (6H Alpha / 4H Risk, Vol 48%)", 0.80
    )

    # EXP-48: FIP Momentum Quality
    print("  -> Building EXP-48: FIP Momentum Quality...")
    w_exp48 = simulate_tournament_6_portfolio(
        close_mat=close_mat, returns_mat=returns_mat, valid_mask=valid_mask, adv_24h=adv_24h,
        asset_vols_24h=asset_vols_24h, baseline_bar_returns=baseline_bar_returns,
        signal_matrix=f_fip_smoothed, num_sub_portfolios=1, target_vol=0.48, use_adv_pruning=False,
        l_min=0.90, l_max=3.20, target_k=12, entry_k=8, exit_k=18, use_dynamic_tau=True
    )
    experiments["EXP-48: FIP Momentum Quality"] = (
        w_exp48, f_fip_smoothed, "FracDiff + Information Discreteness Jump Filter (6H Alpha / 4H Risk, Vol 48%)", 0.80
    )

    # EXP-49: Idiosyncratic t-Statistic
    print("  -> Building EXP-49: Idiosyncratic t-Statistic...")
    w_exp49 = simulate_tournament_6_portfolio(
        close_mat=close_mat, returns_mat=returns_mat, valid_mask=valid_mask, adv_24h=adv_24h,
        asset_vols_24h=asset_vols_24h, baseline_bar_returns=baseline_bar_returns,
        signal_matrix=f_tstat_smoothed, num_sub_portfolios=1, target_vol=0.48, use_adv_pruning=False,
        l_min=0.90, l_max=3.20, target_k=12, entry_k=8, exit_k=18, use_dynamic_tau=True
    )
    experiments["EXP-49: Idiosyncratic t-Statistic"] = (
        w_exp49, f_tstat_smoothed, "Newey-West Residual t-Stat Sizing (6H Alpha / 4H Risk, Vol 48%)", 0.80
    )

    # EXP-50: Interleaved Stagger (M=2)
    print("  -> Building EXP-50: Interleaved Stagger (M=2)...")
    w_exp50 = simulate_tournament_6_portfolio(
        close_mat=close_mat, returns_mat=returns_mat, valid_mask=valid_mask, adv_24h=adv_24h,
        asset_vols_24h=asset_vols_24h, baseline_bar_returns=baseline_bar_returns,
        signal_matrix=f5_smoothed, num_sub_portfolios=2, target_vol=0.48, use_adv_pruning=False,
        l_min=0.90, l_max=3.20, target_k=8, entry_k=8, exit_k=16, use_dynamic_tau=True
    )
    experiments["EXP-50: Interleaved Stagger (M=2)"] = (
        w_exp50, f5_smoothed, "2x Staggered 6H Sub-Portfolios (Market Impact Arbitrage, Vol 48%)", 0.80
    )

    # EXP-51: Interleaved Stagger (M=3)
    print("  -> Building EXP-51: Interleaved Stagger (M=3)...")
    w_exp51 = simulate_tournament_6_portfolio(
        close_mat=close_mat, returns_mat=returns_mat, valid_mask=valid_mask, adv_24h=adv_24h,
        asset_vols_24h=asset_vols_24h, baseline_bar_returns=baseline_bar_returns,
        signal_matrix=f5_smoothed, num_sub_portfolios=3, target_vol=0.48, use_adv_pruning=False,
        l_min=0.90, l_max=3.20, target_k=8, entry_k=8, exit_k=16, use_dynamic_tau=True
    )
    experiments["EXP-51: Interleaved Stagger (M=3)"] = (
        w_exp51, f5_smoothed, "3x Staggered 6H Sub-Portfolios (Maximum Execution Smoothing, Vol 48%)", 0.80
    )

    # EXP-52: Compounding Expansion (52% Vol)
    print("  -> Building EXP-52: Compounding Expansion (52% Vol)...")
    w_exp52 = simulate_tournament_6_portfolio(
        close_mat=close_mat, returns_mat=returns_mat, valid_mask=valid_mask, adv_24h=adv_24h,
        asset_vols_24h=asset_vols_24h, baseline_bar_returns=baseline_bar_returns,
        signal_matrix=f5_smoothed, num_sub_portfolios=2, target_vol=0.52, use_adv_pruning=True,
        l_min=0.90, l_max=3.40, target_k=8, entry_k=8, exit_k=16, use_dynamic_tau=True
    )
    experiments["EXP-52: Compounding Expansion (52% Vol)"] = (
        w_exp52, f5_smoothed, "2x Staggered 6H + ADV Pruning (Gearing Expansion to Vol 52%, L_max=3.40)", 0.80
    )

    # EXP-53: Compounding Expansion (55% Vol)
    print("  -> Building EXP-53: Compounding Expansion (55% Vol)...")
    w_exp53 = simulate_tournament_6_portfolio(
        close_mat=close_mat, returns_mat=returns_mat, valid_mask=valid_mask, adv_24h=adv_24h,
        asset_vols_24h=asset_vols_24h, baseline_bar_returns=baseline_bar_returns,
        signal_matrix=f5_smoothed, num_sub_portfolios=2, target_vol=0.55, use_adv_pruning=True,
        l_min=0.90, l_max=3.60, target_k=8, entry_k=8, exit_k=16, use_dynamic_tau=True
    )
    experiments["EXP-53: Compounding Expansion (55% Vol)"] = (
        w_exp53, f5_smoothed, "2x Staggered 6H + ADV Pruning (Stress Gearing to Vol 55%, L_max=3.60)", 0.80
    )

    # EXP-54: The Apex Grand Synthesis
    print("  -> Building EXP-54: The Apex Grand Synthesis...")
    w_exp54 = simulate_tournament_6_portfolio(
        close_mat=close_mat, returns_mat=returns_mat, valid_mask=valid_mask, adv_24h=adv_24h,
        asset_vols_24h=asset_vols_24h, baseline_bar_returns=baseline_bar_returns,
        signal_matrix=f_fip_smoothed, num_sub_portfolios=2, target_vol=0.52, use_adv_pruning=True,
        l_min=0.90, l_max=3.40, target_k=8, entry_k=8, exit_k=16, use_dynamic_tau=True
    )
    experiments["EXP-54: The Apex Grand Synthesis"] = (
        w_exp54, f_fip_smoothed, "Full Synthesis: 2x Staggered 6H + FIP Quality + ADV Pruning (Vol 52%)", 0.80
    )

    return experiments


def main():
    print("=" * 160)
    print("   IRONCORE INSTITUTIONAL FACTORIAL TOURNAMENT 6 (EXP-47 TO EXP-54)")
    print("   The Sub-20-Month Frontier: Market Impact Arbitrage & Quality Alpha")
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

    # 2. Build Tournament 6 Experiment Matrices
    print("\n[BUILDING TOURNAMENT 6 WEIGHT MATRICES...]", flush=True)
    experiments = build_tournament_6_suite(
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

    print(f"\n[COMPLETE] Tournament 6 results persisted to: {TOURNAMENT_RESULTS_PATH}", flush=True)


if __name__ == "__main__":
    main()
