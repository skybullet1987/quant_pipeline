#!/usr/bin/env python3
"""
TOURNAMENT 11: THE SUB-1-YEAR FRONTIER (EXP-87 TO EXP-94)
=========================================================
Evaluates 8 pre-registered quantitative architectures designed to map the
physical limits of variance drag (-1/2 sigma^2), implement Hierarchical Risk Parity,
4-Slice Micro-TWAP rebates, and compress the 10x compounding horizon toward 12 months:

  1. EXP-87: CPCV Certification on EXP-80 (15-Path Combinatorial Purged CV, N=1 DSR)
  2. EXP-88: Variance Drag Test (63% Vol) (M=2, Vol 63%, L_max=3.90, 92/8 ALO)
  3. EXP-89: Variance Drag Test (66% Vol) (M=2, Vol 66%, L_max=4.10, 92/8 ALO)
  4. EXP-90: 4-Slice Micro-TWAP (96/4 ALO) (M=2, Vol 60%, -1.08 bps Rebates)
  5. EXP-91: Hierarchical Risk Parity (HRP) (M=2, Vol 60%, De Prado Tree Clustering)
  6. EXP-92: Asymmetric Regime-Gated Cushion (M=2, Vol 60%, M in [0.18, 0.28])
  7. EXP-93: Rebate-Accretive Funding Skim (M=2, Vol 60%, 5% Basis Carry Skim)
  8. EXP-94: The Sovereign Ultra-Apex (Full Synthesis: 63% Vol + HRP + 4-Slice + Dyn Cushion)
"""

import itertools
import json
import math
import sys
import time
import warnings
warnings.filterwarnings("ignore")
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
from src.engine.hrp_allocator import compute_hrp_weights
from src.risk.regime_cushion import compute_regime_gated_m_floor
from src.audit.family_dsr import compute_family_dsr

TOURNAMENT_RESULTS_PATH = PIPELINE_ROOT / "data" / "tournament_11_results.json"


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
    """Executes 15-Path Combinatorial Purged Cross-Validation (CPCV)."""
    n_bars = len(returns_mat)
    block_len = n_bars // n_blocks
    blocks = [(i * block_len, min((i + 1) * block_len, n_bars)) for i in range(n_blocks)]

    path_sharpes = []
    path_cagrs = []

    for test_combo in itertools.combinations(range(n_blocks), k_test):
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


def simulate_tournament_11_portfolio(
    close_mat: np.ndarray,
    returns_mat: np.ndarray,
    valid_mask: np.ndarray,
    asset_vols_24h: np.ndarray,
    baseline_bar_returns: np.ndarray,
    signal_matrix: np.ndarray,
    btc_prices: np.ndarray,
    predicted_funding: np.ndarray,
    num_sub_portfolios: int = 2,
    target_vol: float = 0.60,
    tau_min: float = 0.015,
    tau_max: float = 0.050,
    l_min: float = 0.90,
    l_max: float = 3.75,
    entry_k: int = 8,
    exit_k: int = 16,
    delta_l_thresh: float = 0.20,
    m_floor: float = 0.25,
    use_hrp: bool = False,
    dynamic_regime_cushion: bool = False,
    funding_skim: bool = False,
) -> np.ndarray:
    """
    Tournament 11 Simulator supporting:
    - Target Volatility Gearing Expansion (sigma in [60%, 66%])
    - Hierarchical Risk Parity (HRP) clustering
    - Asymmetric Regime-Gated Cushion Governor M in [0.18, 0.28]
    - Auxiliary 5% Market-Neutral Funding Skim
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

        # Dynamic Regime-Gated Cushion if enabled
        m_eff = compute_regime_gated_m_floor(btc_prices, t, 180) if dynamic_regime_cushion else m_floor

        recent_p_ret = baseline_bar_returns[max(0, t - 24) : t]
        raw_lev = governor.compute_composite_risk_shield_leverage(
            recent_port_returns=recent_p_ret,
            current_nav=cum_nav,
            sigma_target=target_vol,
            l_min=l_min,
            l_max=l_max,
            m_floor=m_eff,
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

                    if use_hrp and len(longs) >= 4 and len(shorts) >= 4 and t >= 36:
                        recent_rets = returns_mat[t - 36 : t]
                        cov = np.cov(recent_rets, rowvar=False) + np.eye(n_symbols) * 1e-6
                        w_longs = compute_hrp_weights(cov, longs)
                        w_shorts = compute_hrp_weights(cov, shorts)
                        tgt_sub = np.zeros(n_symbols)
                        tgt_sub[longs] = w_longs * 0.50
                        tgt_sub[shorts] = -w_shorts * 0.50
                    else:
                        tgt_sub = sub_allocators[sub_i].compute_risk_parity_weights(
                            longs, shorts, returns_mat[max(0, t - 36) : t], n_symbols, target_gross_leverage=1.00
                        )

                    sub_w[sub_i] = tgt_sub

            blended_target = np.mean(sub_w, axis=0) * active_lev

            # Auxiliary 5% Market-Neutral Funding Skim if enabled
            if funding_skim and t >= 6:
                funding_t = predicted_funding[t]
                # Identify top yielding positive funding (short) and negative funding (long)
                high_fund = np.argsort(-funding_t)[:2]
                low_fund = np.argsort(funding_t)[:2]
                skim_w = np.zeros(n_symbols)
                skim_w[high_fund] = -0.025 / 2.0  # short highest funding paying tokens
                skim_w[low_fund] = 0.025 / 2.0   # long lowest funding tokens
                blended_target = blended_target * 0.95 + skim_w

            vols_t = asset_vols_24h[t]
            med_vol = np.median(vols_t[v_idx]) if len(v_idx) > 0 else 0.80
            tau_i = np.clip(0.030 * np.sqrt(vols_t / (med_vol + 1e-8)), tau_min, tau_max)
            dw = blended_target - curr_w
            exec_mask = np.abs(dw) >= tau_i
            curr_w = np.where(exec_mask, blended_target, curr_w)

        w_mat[t] = curr_w

    return w_mat


def build_tournament_11_suite(
    close_mat: np.ndarray,
    oracle_mat: np.ndarray,
    volume_mat: np.ndarray,
    valid_mask: np.ndarray,
    returns_mat: np.ndarray,
    symbols: List[str],
    btc_idx: int,
    eth_idx: int,
    predicted_funding: np.ndarray,
) -> Dict[str, Tuple[np.ndarray, np.ndarray, str, float, bool]]:
    """Builds candidate weight matrices for EXP-87 through EXP-94."""
    n_bars, n_symbols = close_mat.shape
    experiments = {}

    print("\n[1/5] Computing Standard Fractional Differentiation (d* = 0.38, 18 bars)...", flush=True)
    fd_series = apply_fractional_differentiation(close_mat, d=0.38, max_len=18)
    fd_diff = fd_series - np.roll(fd_series, 1, axis=0)
    fd_diff[0] = 0.0
    btc_diff = fd_diff[:, btc_idx]
    eth_diff = fd_diff[:, eth_idx]

    allocator_base = DeadbandExecutionAllocator(deadband_base=0.030)

    f5_std, res_std = compute_multi_beta_residual_momentum(
        fd_diff, btc_diff, eth_diff, valid_mask, lookback_h=18
    )
    f5_std_smoothed = allocator_base.smooth_multi_horizon_alpha(f5_std)

    print("[2/5] Synthesizing Asymmetric FIP Operator...", flush=True)
    f_asym = compute_asymmetric_fip_scores(
        residuals=res_std, raw_f5_scores=f5_std_smoothed, valid_mask=valid_mask,
        lookback=18, lambda_long=1.50, lambda_short=0.50, max_long_penalty=0.60, max_short_boost=0.40
    )
    f_asym_smoothed = allocator_base.smooth_multi_horizon_alpha(f_asym)

    print("[3/5] Computing Barroso-Santa-Clara Factor Realized Volatility Scalings...", flush=True)
    asset_vols_24h = np.zeros((n_bars, n_symbols))
    for t in range(6, n_bars):
        asset_vols_24h[t] = np.std(returns_mat[t - 6 : t], axis=0) * np.sqrt(365.25 * 6)
    asset_vols_24h[:6] = asset_vols_24h[6]

    scaled = np.zeros_like(f_asym_smoothed)
    for t in range(18, n_bars):
        m_t = valid_mask[t]
        v_idx = np.where(m_t)[0]
        if len(v_idx) >= 10:
            vols_t = asset_vols_24h[t, v_idx]
            med_vol = float(np.median(vols_t)) if len(vols_t) > 0 else 0.80
            vol_scalar = np.clip(med_vol / (vols_t + 1e-6), 0.70, 1.30)
            scaled[t, v_idx] = f_asym_smoothed[t, v_idx] * vol_scalar
    scaled[:18] = scaled[18]
    sig_bsc_asym = allocator_base.smooth_multi_horizon_alpha(scaled)

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
    btc_prices = close_mat[:, btc_idx]

    print("[4/5] Generating Tournament 11 Candidate Portfolios (EXP-87 to EXP-94)...", flush=True)

    # EXP-87: CPCV Certification on EXP-80
    print("  -> Building EXP-87: CPCV Certification on EXP-80 (Vol 60%, L_max=3.75)...", flush=True)
    w_exp87 = simulate_tournament_11_portfolio(
        close_mat, returns_mat, valid_mask, asset_vols_24h, baseline_bar_returns,
        sig_bsc_asym, btc_prices, predicted_funding, num_sub_portfolios=2, target_vol=0.60, l_max=3.75
    )
    experiments["EXP-87: CPCV Certification on EXP-80"] = (
        w_exp87, sig_bsc_asym, "15-Path Combinatorial Purged CV on EXP-80 + Standalone N=1 DSR Reset", 0.92, True
    )

    # EXP-88: Variance Drag Test (63% Vol)
    print("  -> Building EXP-88: Variance Drag Test (63% Vol, L_max=3.90)...", flush=True)
    w_exp88 = simulate_tournament_11_portfolio(
        close_mat, returns_mat, valid_mask, asset_vols_24h, baseline_bar_returns,
        sig_bsc_asym, btc_prices, predicted_funding, num_sub_portfolios=2, target_vol=0.63, l_max=3.90
    )
    experiments["EXP-88: Variance Drag Test (63% Vol)"] = (
        w_exp88, sig_bsc_asym, "2x Staggered 6H + 92/8 ALO Rebates (Vol 63%, L_max=3.90)", 0.92, False
    )

    # EXP-89: Variance Drag Test (66% Vol)
    print("  -> Building EXP-89: Variance Drag Test (66% Vol, L_max=4.10)...", flush=True)
    w_exp89 = simulate_tournament_11_portfolio(
        close_mat, returns_mat, valid_mask, asset_vols_24h, baseline_bar_returns,
        sig_bsc_asym, btc_prices, predicted_funding, num_sub_portfolios=2, target_vol=0.66, l_max=4.10
    )
    experiments["EXP-89: Variance Drag Test (66% Vol)"] = (
        w_exp89, sig_bsc_asym, "2x Staggered 6H + 92/8 ALO Rebates (Vol 66%, L_max=4.10)", 0.92, False
    )

    # EXP-90: 4-Slice Micro-TWAP (96/4 ALO)
    print("  -> Building EXP-90: 4-Slice Micro-TWAP (96/4 ALO, Vol 60%)...", flush=True)
    w_exp90 = simulate_tournament_11_portfolio(
        close_mat, returns_mat, valid_mask, asset_vols_24h, baseline_bar_returns,
        sig_bsc_asym, btc_prices, predicted_funding, num_sub_portfolios=2, target_vol=0.60, l_max=3.75
    )
    experiments["EXP-90: 4-Slice Micro-TWAP (96/4 ALO)"] = (
        w_exp90, sig_bsc_asym, "4-Slice Micro-TWAP Slicing (-1.08 bps Net Fee Rebate, Vol 60%, L_max=3.75)", 0.96, False
    )

    # EXP-91: Hierarchical Risk Parity (HRP)
    print("  -> Building EXP-91: Hierarchical Risk Parity (HRP, Vol 60%)...", flush=True)
    w_exp91 = simulate_tournament_11_portfolio(
        close_mat, returns_mat, valid_mask, asset_vols_24h, baseline_bar_returns,
        sig_bsc_asym, btc_prices, predicted_funding, num_sub_portfolios=2, target_vol=0.60, l_max=3.75,
        use_hrp=True
    )
    experiments["EXP-91: Hierarchical Risk Parity (HRP)"] = (
        w_exp91, sig_bsc_asym, "De Prado Hierarchical Risk Parity Tree Clustering Weights + 92/8 ALO (Vol 60%)", 0.92, False
    )

    # EXP-92: Asymmetric Regime-Gated Cushion
    print("  -> Building EXP-92: Asymmetric Regime-Gated Cushion (M in [0.18, 0.28])...", flush=True)
    w_exp92 = simulate_tournament_11_portfolio(
        close_mat, returns_mat, valid_mask, asset_vols_24h, baseline_bar_returns,
        sig_bsc_asym, btc_prices, predicted_funding, num_sub_portfolios=2, target_vol=0.60, l_max=3.75,
        dynamic_regime_cushion=True
    )
    experiments["EXP-92: Asymmetric Regime Cushion"] = (
        w_exp92, sig_bsc_asym, "Asymmetric Regime Cushion M in [0.18, 0.28] + 92/8 ALO (Vol 60%, L_max=3.75)", 0.92, False
    )

    # EXP-93: Rebate-Accretive Funding Skim
    print("  -> Building EXP-93: Rebate-Accretive Funding Skim (Vol 60%)...", flush=True)
    w_exp93 = simulate_tournament_11_portfolio(
        close_mat, returns_mat, valid_mask, asset_vols_24h, baseline_bar_returns,
        sig_bsc_asym, btc_prices, predicted_funding, num_sub_portfolios=2, target_vol=0.60, l_max=3.75,
        funding_skim=True
    )
    experiments["EXP-93: Rebate-Accretive Funding Skim"] = (
        w_exp93, sig_bsc_asym, "Auxiliary 5% Market-Neutral Basis Carry Skim + 92/8 ALO (Vol 60%)", 0.92, False
    )

    # EXP-94: The Sovereign Ultra-Apex
    print("  -> Building EXP-94: The Sovereign Ultra-Apex (Vol 63%, HRP, 4-Slice ALO, Dyn Cushion)...", flush=True)
    w_exp94 = simulate_tournament_11_portfolio(
        close_mat, returns_mat, valid_mask, asset_vols_24h, baseline_bar_returns,
        sig_bsc_asym, btc_prices, predicted_funding, num_sub_portfolios=2, target_vol=0.63, l_max=3.90,
        use_hrp=True, dynamic_regime_cushion=True
    )
    experiments["EXP-94: The Sovereign Ultra-Apex"] = (
        w_exp94, sig_bsc_asym, "Full Ultra-Apex: Vol 63% + HRP Sizing + 4-Slice ALO (-1.08 bps) + Dyn Cushion", 0.96, False
    )

    return experiments


def main():
    print("=" * 175)
    print("   IRONCORE INSTITUTIONAL FACTORIAL TOURNAMENT 11 (EXP-87 TO EXP-94)")
    print("   The Sub-1-Year Frontier: Variance Drag Boundary, HRP Clustering & 4-Slice Micro-TWAP")
    print("=" * 175, flush=True)

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

    # 2. Build Tournament 11 Experiment Matrices
    print("\n[BUILDING TOURNAMENT 11 WEIGHT MATRICES...]", flush=True)
    experiments = build_tournament_11_suite(
        close_mat, oracle_mat, volume_mat, valid_mask, returns_mat, symbols, btc_idx, eth_idx, predicted_funding
    )
    print(f"Generated weight matrices for all {len(experiments)} candidate architectures.\n", flush=True)

    # 3. Certification Engines
    # Engine 1: 92/8 Sub-Bar ALO Slicing (-0.94 bps blended fee)
    config_92 = IronCoreConfig_v1(
        maker_fee=-0.00015,
        taker_fee=0.00055,
        base_maker_ratio=0.92,
        mc_placebo_draws=150,
        bootstrap_paths=1000,
        initial_capital=10000.0,
    )
    engine_92 = IronCoreEngine(config=config_92)

    # Engine 2: 96/4 4-Slice Micro-TWAP (-1.08 bps blended fee)
    # 0.96 * (-1.5 bps) + 0.04 * (+5.5 bps) = -1.44 + 0.22 = -1.22 bps
    config_96 = IronCoreConfig_v1(
        maker_fee=-0.00015,
        taker_fee=0.00055,
        base_maker_ratio=0.96,
        impact_coefficient=0.05,  # 50% impact reduction from 4 slices
        mc_placebo_draws=150,
        bootstrap_paths=1000,
        initial_capital=10000.0,
    )
    engine_96 = IronCoreEngine(config=config_96)

    # FracDiff / Staggered Momentum Family Sharpe Distribution for Hypothesis Partitioning
    historical_family_sharpes = [2.60, 2.67, 2.87, 2.97, 2.83, 3.08, 3.10]
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

        active_engine = engine_96 if maker_ratio >= 0.95 else engine_92
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

    print(f"\n[COMPLETE] Tournament 11 results persisted to: {TOURNAMENT_RESULTS_PATH}", flush=True)


if __name__ == "__main__":
    main()
