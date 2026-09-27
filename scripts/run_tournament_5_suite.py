#!/usr/bin/env python3
"""
TOURNAMENT 5: THE MASTER COMPOUNDING FRONTIER (EXP-39 TO EXP-46)
================================================================
Evaluates 8 pre-registered quantitative architectures designed to compress the
10x compounding timeline from 25.2 months toward 16-18 months without breaching
any of the 7 IronCore gates:

  1. EXP-39: Decoupled 6H Baseline (6H Alpha / 4H Risk, Vol 45%, sqrt(C(t)) Ramp)
  2. EXP-40: Decoupled 8H Baseline (8H Alpha / 4H Risk, synchronized to 8H funding)
  3. EXP-41: Dynamic Vol-Deadband (tau_i in [0.015, 0.050] on 4H base)
  4. EXP-42: Multi-Factor: OI Momentum (80% FracDiff + 20% F_Delta_OI)
  5. EXP-43: Multi-Factor: Basis Term Shield (85% FracDiff + 15% F_basis)
  6. EXP-44: Regime-Adaptive Volatility (Adaptive sigma in [30%, 48%] on Hurst & Correlation)
  7. EXP-45: Gearing Frontier (6H Alpha, Vol 48%, Dynamic tau_i, 80/20 ALO)
  8. EXP-46: The Grand Laboratory Synthesis (6H Alpha, Adaptive sigma [32%, 48%], Multi-Factor, tau_i, ALO)
"""

import json
import math
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple, Any

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

TOURNAMENT_RESULTS_PATH = PIPELINE_ROOT / "data" / "tournament_5_results.json"


def calculate_compounding_milestones(cagr: float) -> Tuple[float, float, float]:
    """Calculates time in months to reach 2x, 5x, and 10x equity."""
    if cagr <= 0:
        return float("inf"), float("inf"), float("inf")
    g = math.log(1.0 + cagr / 100.0)
    t_2x = (math.log(2.0) / g) * 12.0
    t_5x = (math.log(5.0) / g) * 12.0
    t_10x = (math.log(10.0) / g) * 12.0
    return t_2x, t_5x, t_10x


def compute_rolling_hurst(series: np.ndarray, window: int = 72) -> np.ndarray:
    """
    Computes rolling Hurst exponent using rescaled range / variogram over lookback window.
    H > 0.55 indicates persistent trending; H < 0.45 indicates mean-reverting chop.
    """
    n = len(series)
    hurst = np.full(n, 0.50)
    lags = [2, 4, 8, 16]
    log_lags = np.log(lags)

    for t in range(window, n):
        sub = series[t - window : t]
        stds = []
        for lag in lags:
            diffs = sub[lag:] - sub[:-lag]
            s = np.std(diffs)
            stds.append(s if s > 1e-8 else 1e-8)
        poly = np.polyfit(log_lags, np.log(stds), 1)
        h_val = float(np.clip(poly[0], 0.20, 0.85))
        hurst[t] = h_val
    hurst[:window] = hurst[window]
    return hurst


def compute_rolling_pairwise_correlation(returns_mat: np.ndarray, valid_mask: np.ndarray, window: int = 36) -> np.ndarray:
    """Computes median pairwise cross-sectional correlation across active assets."""
    n_bars, n_symbols = returns_mat.shape
    median_corr = np.full(n_bars, 0.50)

    for t in range(window, n_bars):
        m_t = valid_mask[t]
        v_idx = np.where(m_t)[0]
        if len(v_idx) >= 10:
            sub_ret = returns_mat[t - window : t, v_idx]
            stds = np.std(sub_ret, axis=0)
            active = stds > 1e-8
            if np.sum(active) >= 10:
                corr = np.corrcoef(sub_ret[:, active].T)
                upper_tri = corr[np.triu_indices_from(corr, k=1)]
                clean_tri = upper_tri[~np.isnan(upper_tri)]
                if len(clean_tri) > 0:
                    median_corr[t] = float(np.median(clean_tri))
    median_corr[:window] = median_corr[window]
    return median_corr


def build_tournament_5_matrices(
    close_mat: np.ndarray,
    oracle_mat: np.ndarray,
    volume_mat: np.ndarray,
    valid_mask: np.ndarray,
    returns_mat: np.ndarray,
    symbols: List[str],
    btc_idx: int,
    eth_idx: int,
) -> Tuple[Dict[str, Tuple[np.ndarray, np.ndarray, str, float]], Dict[str, Any]]:
    """Builds weight matrices for EXP-39 through EXP-46."""
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

    print("[2/5] Synthesizing Non-Price Derivatives Factors (OI Momentum & Basis Shield)...")
    dollar_vol = np.nan_to_num(volume_mat * close_mat, nan=0.0)
    vol_mean_72h = np.zeros_like(dollar_vol)
    vol_std_72h = np.zeros_like(dollar_vol)

    for t in range(18, n_bars):
        win = dollar_vol[t - 18 : t]
        vol_mean_72h[t] = np.mean(win, axis=0)
        vol_std_72h[t] = np.std(win, axis=0) + 1e-6
    vol_mean_72h[:18] = vol_mean_72h[18]
    vol_std_72h[:18] = vol_std_72h[18]

    # OI velocity z-score
    oi_change = (dollar_vol - vol_mean_72h) / vol_std_72h
    f_oi_momentum = np.zeros((n_bars, n_symbols))

    for t in range(n_bars):
        m_t = valid_mask[t]
        if np.sum(m_t) > 5:
            res_dir = np.sign(residuals[t, m_t])
            oi_acc = np.maximum(0.0, oi_change[t, m_t])
            raw_score = res_dir * oi_acc
            score_std = np.std(raw_score) + 1e-8
            f_oi_momentum[t, m_t] = (raw_score - np.mean(raw_score)) / score_std

    f_oi_smoothed = allocator_base.smooth_multi_horizon_alpha(f_oi_momentum)

    # 2. Speculative Basis Term Structure Factor: F_basis
    basis = np.nan_to_num((close_mat - oracle_mat) / (oracle_mat + 1e-8), nan=0.0)
    basis_ema = np.zeros_like(basis)
    basis_std = np.zeros_like(basis)

    for t in range(36, n_bars):
        w_b = basis[t - 36 : t]
        basis_ema[t] = np.mean(w_b, axis=0)
        basis_std[t] = np.std(w_b, axis=0) + 1e-6
    basis_ema[:36] = basis_ema[36]
    basis_std[:36] = basis_std[36]

    f_basis = np.zeros((n_bars, n_symbols))
    for t in range(n_bars):
        m_t = valid_mask[t]
        if np.sum(m_t) > 5:
            raw_basis_z = - (basis[t, m_t] - basis_ema[t, m_t]) / basis_std[t, m_t]
            b_std = np.std(raw_basis_z) + 1e-8
            f_basis[t, m_t] = (raw_basis_z - np.mean(raw_basis_z)) / b_std

    f_basis_smoothed = allocator_base.smooth_multi_horizon_alpha(f_basis)

    # Blended Alpha Composites
    f_composite_oi = allocator_base.smooth_multi_horizon_alpha(0.80 * f5_smoothed + 0.20 * f_oi_smoothed)
    f_composite_basis = allocator_base.smooth_multi_horizon_alpha(0.85 * f5_smoothed + 0.15 * f_basis_smoothed)

    print("[3/5] Computing Macro Regime Metrics (Market Hurst & Cross-Asset Correlation)...")
    btc_prices = close_mat[:, btc_idx]
    market_hurst = compute_rolling_hurst(btc_prices, window=72)
    market_corr = compute_rolling_pairwise_correlation(returns_mat, valid_mask, window=36)

    print("[4/5] Computing Asset-Specific Realized Volatilities for Dynamic Deadbands (tau_i)...")
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
                    recent_returns=returns_mat[max(0, t-36):t],
                    top_k=10,
                    target_gross_leverage=1.50
                )
                curr_w = allocator_base.apply_leland_deadband(tgt_w, curr_w, tau=0.030)
        w_baseline_raw[t] = curr_w

    baseline_bar_returns = np.sum(w_baseline_raw * returns_mat, axis=1)

    print("[5/5] Generating Tournament 5 Factory Portfolios (EXP-39 to EXP-46)...")
    governor = DynamicGearingGovernor()

    def simulate_decoupled_strategy(
        cadence_type: str,          # "4H", "6H", "8H"
        target_vol_mode: str,       # "static_45", "static_48", "adaptive"
        use_dynamic_tau: bool = False,
        signal_matrix: np.ndarray = f5_smoothed,
        l_min: float = 0.80,
        l_max: float = 2.80,
        target_k: int = 12,
        entry_k: int = 8,
        exit_k: int = 18,
        delta_l_thresh: float = 0.20,
        m_floor: float = 0.25,
        accelerated_reentry: bool = True,
    ) -> np.ndarray:
        allocator = RankBufferAllocator(target_k=target_k, entry_k=entry_k, exit_k=exit_k, deadband_tau=0.030)
        w_mat = np.zeros((n_bars, n_symbols))
        curr_w = np.zeros(n_symbols)
        active_lev = 1.00
        cum_nav = 10000.0
        governor.reset_state(initial_nav=cum_nav)

        def is_alpha_rebalance_step(step_idx: int) -> bool:
            if cadence_type == "4H":
                return True
            elif cadence_type == "8H":
                return (step_idx % 2 == 0)
            elif cadence_type == "6H":
                # Average 1.5 bars: rebalance at step 0, step 1 (1 bar step = 4H), step 3 (2 bar step = 8H) -> 12H / 2 = 6H
                return (step_idx % 3 == 0) or (step_idx % 3 == 1)
            return True

        for t in range(n_bars):
            if t > 0:
                bar_pnl = float(np.sum(w_mat[t - 1] * returns_mat[t]))
                cum_nav *= (1.0 + bar_pnl)

            if target_vol_mode == "static_45":
                target_vol = 0.45
            elif target_vol_mode == "static_48":
                target_vol = 0.48
            elif target_vol_mode == "adaptive":
                h_t = market_hurst[t]
                rho_t = market_corr[t]
                if h_t >= 0.58 and rho_t <= 0.45:
                    target_vol = 0.48  # Trend expansion / high dispersion
                elif h_t < 0.45 or rho_t >= 0.70:
                    target_vol = 0.30  # Macro contagion / chop
                else:
                    target_vol = 0.42  # Baseline normal
            else:
                target_vol = 0.45

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
                accelerated_reentry=accelerated_reentry,
            )

            # Leverage deadband
            active_lev = allocator.apply_leverage_deadband(raw_lev, active_lev, delta_thresh=delta_l_thresh)

            # Slow Alpha Clock
            m_t = valid_mask[t]
            if np.sum(m_t) >= (allocator.exit_k * 2):
                v_idx = np.where(m_t)[0]

                if is_alpha_rebalance_step(t):
                    longs, shorts = allocator.update_holdings_with_hysteresis(
                        scores=signal_matrix[t], valid_idx=v_idx
                    )
                    tgt_w = allocator.compute_risk_parity_weights(
                        longs, shorts, returns_mat[max(0, t - 36) : t], n_symbols, target_gross_leverage=active_lev
                    )
                else:
                    # Inaction zone: keep existing target weights scaled to current active leverage
                    current_gross = np.sum(np.abs(curr_w))
                    if current_gross > 1e-6:
                        tgt_w = curr_w * (active_lev / current_gross)
                    else:
                        tgt_w = curr_w.copy()

                # Dynamic Volatility Deadband (tau_i)
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

    # EXP-39: Decoupled 6H Baseline
    print("  -> Building EXP-39: Decoupled 6H Baseline...")
    w_exp39 = simulate_decoupled_strategy(
        cadence_type="6H", target_vol_mode="static_45", use_dynamic_tau=False,
        signal_matrix=f5_smoothed, l_min=0.80, l_max=2.80
    )
    experiments["EXP-39: Decoupled 6H Baseline"] = (
        w_exp39, f5_smoothed, "6H Alpha Rebalance / 4H Fast Risk Shield (Vol 45% + sqrt(C(t)) Ramp)", 0.80
    )

    # EXP-40: Decoupled 8H Baseline
    print("  -> Building EXP-40: Decoupled 8H Baseline...")
    w_exp40 = simulate_decoupled_strategy(
        cadence_type="8H", target_vol_mode="static_45", use_dynamic_tau=False,
        signal_matrix=f5_smoothed, l_min=0.80, l_max=2.80
    )
    experiments["EXP-40: Decoupled 8H Baseline"] = (
        w_exp40, f5_smoothed, "8H Alpha Rebalance / 4H Fast Risk Shield (Synchronized to 8H Funding Cycles)", 0.80
    )

    # EXP-41: Dynamic Vol-Deadband
    print("  -> Building EXP-41: Dynamic Vol-Deadband...")
    w_exp41 = simulate_decoupled_strategy(
        cadence_type="4H", target_vol_mode="static_45", use_dynamic_tau=True,
        signal_matrix=f5_smoothed, l_min=0.80, l_max=2.80
    )
    experiments["EXP-41: Dynamic Vol-Deadband (tau_i)"] = (
        w_exp41, f5_smoothed, "Asset-Specific Volatility Deadband tau_i in [0.015, 0.050] on 4H Base", 0.80
    )

    # EXP-42: Multi-Factor: OI Momentum
    print("  -> Building EXP-42: Multi-Factor: OI Momentum...")
    w_exp42 = simulate_decoupled_strategy(
        cadence_type="4H", target_vol_mode="static_45", use_dynamic_tau=False,
        signal_matrix=f_composite_oi, l_min=0.80, l_max=2.80
    )
    experiments["EXP-42: Multi-Factor: OI Momentum"] = (
        w_exp42, f_composite_oi, "80% FracDiff Residual Momentum + 20% OI Capital Accumulation Momentum", 0.80
    )

    # EXP-43: Multi-Factor: Basis Term Shield
    print("  -> Building EXP-43: Multi-Factor: Basis Term Shield...")
    w_exp43 = simulate_decoupled_strategy(
        cadence_type="4H", target_vol_mode="static_45", use_dynamic_tau=False,
        signal_matrix=f_composite_basis, l_min=0.80, l_max=2.80
    )
    experiments["EXP-43: Multi-Factor: Basis Term Shield"] = (
        w_exp43, f_composite_basis, "85% FracDiff Residual Momentum + 15% Speculative Basis Premium Shield", 0.80
    )

    # EXP-44: Regime-Adaptive Volatility
    print("  -> Building EXP-44: Regime-Adaptive Volatility...")
    w_exp44 = simulate_decoupled_strategy(
        cadence_type="4H", target_vol_mode="adaptive", use_dynamic_tau=False,
        signal_matrix=f5_smoothed, l_min=0.80, l_max=2.80
    )
    experiments["EXP-44: Regime-Adaptive Volatility"] = (
        w_exp44, f5_smoothed, "Dynamic Volatility Modulation in [30%, 48%] Governed by Market Hurst & Pairwise Correlation", 0.80
    )

    # EXP-45: Gearing Frontier
    print("  -> Building EXP-45: Gearing Frontier...")
    w_exp45 = simulate_decoupled_strategy(
        cadence_type="6H", target_vol_mode="static_48", use_dynamic_tau=True,
        signal_matrix=f5_smoothed, l_min=0.90, l_max=3.20
    )
    experiments["EXP-45: Gearing Frontier (sigma=48%)"] = (
        w_exp45, f5_smoothed, "6H Decoupled Cadence + Vol 48% + L in [0.90, 3.20] + Dynamic tau_i + 80/20 ALO", 0.80
    )

    # EXP-46: The Grand Laboratory Synthesis
    print("  -> Building EXP-46: The Grand Laboratory Synthesis...")
    w_exp46 = simulate_decoupled_strategy(
        cadence_type="6H", target_vol_mode="adaptive", use_dynamic_tau=True,
        signal_matrix=f_composite_oi, l_min=0.85, l_max=3.00
    )
    experiments["EXP-46: The Grand Laboratory Synthesis"] = (
        w_exp46, f_composite_oi, "Full Synthesis: 6H Decoupled + Adaptive Vol [32%, 48%] + OI Momentum + Dynamic tau_i + 80/20 ALO", 0.80
    )

    meta = {
        "market_hurst": market_hurst,
        "market_corr": market_corr,
    }

    return experiments, meta


def main():
    print("=" * 160)
    print("   IRONCORE INSTITUTIONAL FACTORIAL TOURNAMENT 5 (EXP-39 TO EXP-46)")
    print("   The Master Compounding Frontier: Compressing the 10x Horizon")
    print("=" * 160)

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

    print(f"\n[DATASET READY] Loaded {len(timestamps)} bars across {len(symbols)} symbols.")

    # 2. Build Experiment Matrices
    print("\n[BUILDING TOURNAMENT 5 WEIGHT MATRICES...]")
    experiments, _ = build_tournament_5_matrices(
        close_mat, oracle_mat, volume_mat, valid_mask, returns_mat, symbols, btc_idx, eth_idx
    )
    print(f"Generated weight matrices for all {len(experiments)} candidate architectures.\n")

    # 3. Certification Engine (80% ALO Maker Parity)
    config_80 = IronCoreConfig_v1(
        base_maker_ratio=0.80,
        mc_placebo_draws=150,
        bootstrap_paths=1000,
        initial_capital=10000.0,
    )
    engine = IronCoreEngine(config=config_80)

    results = []

    print("=" * 175)
    print(f"{'EXPERIMENT ID & CONFIGURATION':<46} | {'CAGR':<8} | {'SHARPE':<6} | {'MAX DD':<7} | {'FRIC RATIO':<10} | {'TURNOVER':<9} | {'P(PERM)':<7} | {'RUIN(%)':<7} | {'TIME TO 10X':<11} | {'VERDICT':<8}")
    print("-" * 175)

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

    print("=" * 175)

    with open(TOURNAMENT_RESULTS_PATH, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n[COMPLETE] Tournament 5 results persisted to: {TOURNAMENT_RESULTS_PATH}")


if __name__ == "__main__":
    main()
