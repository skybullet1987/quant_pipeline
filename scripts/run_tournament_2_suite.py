"""
TOURNAMENT 2: PRODUCTION ALPHA FRONTIER (EXP-11 TO EXP-20)
===========================================================
Executes the second institutional tournament benchmarking risk-governed gearing,
rank-buffer hysteresis, multi-memory fracdiff ensemble, lottery skew vetoes,
and exhaustion wick fading against the 7-Gate IronCore Adversarial Engine.
"""

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
from src.alpha.orthogonal_alpha_ensemble import OrthogonalAlphaEnsemble


from backtest_10x_convex_compounding import (
    DATA_LAKE_PATH, BENCHMARK_SYMBOL, EVAL_START_TS, EVAL_END_TS
)


def build_tournament_2_matrices(
    close_mat: np.ndarray,
    oracle_mat: np.ndarray,
    volume_mat: np.ndarray,
    valid_mask: np.ndarray,
    returns_mat: np.ndarray,
    symbols: List[str],
    btc_idx: int,
    eth_idx: int
) -> Dict[str, Tuple[np.ndarray, np.ndarray, str]]:
    """Builds the weight and signal matrices for EXP-11 through EXP-20."""
    n_bars, n_symbols = close_mat.shape
    experiments = {}

    print("\n[1/5] Computing Base Fractional Differentiation (d* = 0.38)...")
    fd_series_38 = apply_fractional_differentiation(close_mat, d=0.38, max_len=18)
    fd_diff = fd_series_38 - np.roll(fd_series_38, 1, axis=0)
    fd_diff[0] = 0.0
    f5_base, residuals = compute_multi_beta_residual_momentum(
        fd_diff, fd_diff[:, btc_idx], fd_diff[:, eth_idx], valid_mask, lookback_h=18
    )

    allocator_base = DeadbandExecutionAllocator(deadband_base=0.030)
    f5_smoothed = allocator_base.smooth_multi_horizon_alpha(f5_base)

    print("[2/5] Computing Multi-Memory FracDiff Ensemble...")
    ensemble_engine = OrthogonalAlphaEnsemble()
    f_ensemble = ensemble_engine.compute_multi_memory_fracdiff_composite(close_mat, valid_mask, btc_idx, eth_idx)
    f_ensemble_smoothed = allocator_base.smooth_multi_horizon_alpha(f_ensemble)

    print("[3/5] Extracting Residuals & Computing Lottery Skew Veto Mask...")
    skew_veto_mask = ensemble_engine.compute_lottery_skewness_veto_mask(
        residuals, close_mat, valid_mask, lookback_bars=180, skew_threshold=1.50
    )

    print("[4/5] Computing Exhaustion Wick Fader Weights...")
    fader_weights_raw = ensemble_engine.compute_exhaustion_wick_fader_weights(
        residuals, close_mat, volume_mat, valid_mask, fader_allocation=0.15
    )

    print("[5/5] Synthesizing Portfolios with Rank-Buffer & Gearing Governors...")
    rank_allocator = RankBufferAllocator(target_k=12, entry_k=8, exit_k=18, deadband_tau=0.030)
    governor = DynamicGearingGovernor()

    # Pre-simulate baseline EXP-04 return series for vol-target estimation
    w_exp04_raw = np.zeros((n_bars, n_symbols))
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
        w_exp04_raw[t] = curr_w

    exp04_bar_returns = np.sum(w_exp04_raw * returns_mat, axis=1)

    # -------------------------------------------------------------------------
    # EXP-11: EXP-04 + Rank-Buffer Hysteresis (Fixed 1.0x, Top 8 / Exit 18)
    # -------------------------------------------------------------------------
    w_exp11 = np.zeros((n_bars, n_symbols))
    curr_w = np.zeros(n_symbols)
    rank_allocator.reset_state()
    for t in range(n_bars):
        if t % 6 == 0:
            m_t = valid_mask[t]
            if np.sum(m_t) >= 20:
                v_idx = np.where(m_t)[0]
                longs, shorts = rank_allocator.update_holdings_with_hysteresis(
                    scores=f5_smoothed[t], valid_idx=v_idx
                )
                tgt_w = rank_allocator.compute_risk_parity_weights(
                    longs, shorts, returns_mat[max(0, t-36):t], n_symbols, target_gross_leverage=1.00
                )
                curr_w = rank_allocator.apply_leland_deadband(tgt_w, curr_w, tau=0.030)
        w_exp11[t] = curr_w
    experiments["EXP-11: EXP-04 + Rank-Buffer Hysteresis"] = (
        w_exp11, f5_smoothed, "Fixed 1.0x, Top 8 Entry / Exit 18 Sieve, tau=0.030"
    )

    # -------------------------------------------------------------------------
    # EXP-12: EXP-04 + Target Volatility Gearing (sigma_target = 25%)
    # -------------------------------------------------------------------------
    w_exp12 = np.zeros((n_bars, n_symbols))
    curr_w = np.zeros(n_symbols)
    for t in range(n_bars):
        if t % 6 == 0:
            m_t = valid_mask[t]
            if np.sum(m_t) >= 20:
                v_idx = np.where(m_t)[0]
                recent_p_ret = exp04_bar_returns[max(0, t-24):t]
                scale = governor.compute_vol_target_scale(recent_p_ret, sigma_target=0.25, l_min=0.50, l_max=1.60)
                tgt_w = allocator_base.compute_risk_parity_weights(
                    scores=f5_smoothed[t],
                    valid_idx=v_idx,
                    recent_returns=returns_mat[max(0, t-36):t],
                    top_k=10,
                    target_gross_leverage=scale
                )
                curr_w = allocator_base.apply_leland_deadband(tgt_w, curr_w, tau=0.030)
        w_exp12[t] = curr_w
    experiments["EXP-12: EXP-04 + Target Vol Gearing (25%)"] = (
        w_exp12, f5_smoothed, "sigma_target=25%, L in [0.5, 1.6], Leland tau=0.030"
    )

    # -------------------------------------------------------------------------
    # EXP-13: EXP-04 + Target Volatility Gearing (sigma_target = 30%)
    # -------------------------------------------------------------------------
    w_exp13 = np.zeros((n_bars, n_symbols))
    curr_w = np.zeros(n_symbols)
    for t in range(n_bars):
        if t % 6 == 0:
            m_t = valid_mask[t]
            if np.sum(m_t) >= 20:
                v_idx = np.where(m_t)[0]
                recent_p_ret = exp04_bar_returns[max(0, t-24):t]
                scale = governor.compute_vol_target_scale(recent_p_ret, sigma_target=0.30, l_min=0.60, l_max=1.80)
                tgt_w = allocator_base.compute_risk_parity_weights(
                    scores=f5_smoothed[t],
                    valid_idx=v_idx,
                    recent_returns=returns_mat[max(0, t-36):t],
                    top_k=10,
                    target_gross_leverage=scale
                )
                curr_w = allocator_base.apply_leland_deadband(tgt_w, curr_w, tau=0.030)
        w_exp13[t] = curr_w
    experiments["EXP-13: EXP-04 + Target Vol Gearing (30%)"] = (
        w_exp13, f5_smoothed, "sigma_target=30%, L in [0.6, 1.8], Leland tau=0.030"
    )

    # -------------------------------------------------------------------------
    # EXP-14: EXP-04 + Target Volatility Gearing (sigma_target = 35%)
    # -------------------------------------------------------------------------
    w_exp14 = np.zeros((n_bars, n_symbols))
    curr_w = np.zeros(n_symbols)
    for t in range(n_bars):
        if t % 6 == 0:
            m_t = valid_mask[t]
            if np.sum(m_t) >= 20:
                v_idx = np.where(m_t)[0]
                recent_p_ret = exp04_bar_returns[max(0, t-24):t]
                scale = governor.compute_vol_target_scale(recent_p_ret, sigma_target=0.35, l_min=0.80, l_max=2.20)
                tgt_w = allocator_base.compute_risk_parity_weights(
                    scores=f5_smoothed[t],
                    valid_idx=v_idx,
                    recent_returns=returns_mat[max(0, t-36):t],
                    top_k=10,
                    target_gross_leverage=scale
                )
                curr_w = allocator_base.apply_leland_deadband(tgt_w, curr_w, tau=0.030)
        w_exp14[t] = curr_w
    experiments["EXP-14: EXP-04 + Target Vol Gearing (35%)"] = (
        w_exp14, f5_smoothed, "sigma_target=35%, L in [0.8, 2.2], Leland tau=0.030"
    )

    # -------------------------------------------------------------------------
    # EXP-15: EXP-04 + Grossman-Zhou Floor (M = 0.25, gamma = 0.75)
    # -------------------------------------------------------------------------
    w_exp15 = np.zeros((n_bars, n_symbols))
    curr_w = np.zeros(n_symbols)
    governor.reset_state(initial_nav=10000.0)
    cum_nav = 10000.0
    for t in range(n_bars):
        if t > 0:
            bar_pnl = float(np.sum(w_exp15[t-1] * returns_mat[t]))
            cum_nav *= (1.0 + bar_pnl)
        if t % 6 == 0:
            m_t = valid_mask[t]
            if np.sum(m_t) >= 20:
                v_idx = np.where(m_t)[0]
                scale = governor.compute_grossman_zhou_cushion(cum_nav, l_min=0.50, l_max=1.80)
                tgt_w = allocator_base.compute_risk_parity_weights(
                    scores=f5_smoothed[t],
                    valid_idx=v_idx,
                    recent_returns=returns_mat[max(0, t-36):t],
                    top_k=10,
                    target_gross_leverage=scale
                )
                curr_w = allocator_base.apply_leland_deadband(tgt_w, curr_w, tau=0.030)
        w_exp15[t] = curr_w
    experiments["EXP-15: EXP-04 + Grossman-Zhou Floor"] = (
        w_exp15, f5_smoothed, "GZ Floor M=0.25, gamma=0.75, L in [0.5, 1.8]"
    )

    # -------------------------------------------------------------------------
    # EXP-16: Multi-Memory FracDiff Ensemble (d in [0.28, 0.38, 0.45])
    # -------------------------------------------------------------------------
    w_exp16 = np.zeros((n_bars, n_symbols))
    curr_w = np.zeros(n_symbols)
    for t in range(n_bars):
        if t % 6 == 0:
            m_t = valid_mask[t]
            if np.sum(m_t) >= 20:
                v_idx = np.where(m_t)[0]
                tgt_w = allocator_base.compute_risk_parity_weights(
                    scores=f_ensemble_smoothed[t],
                    valid_idx=v_idx,
                    recent_returns=returns_mat[max(0, t-36):t],
                    top_k=10,
                    target_gross_leverage=1.50
                )
                curr_w = allocator_base.apply_leland_deadband(tgt_w, curr_w, tau=0.030)
        w_exp16[t] = curr_w
    experiments["EXP-16: Multi-Memory FracDiff Ensemble"] = (
        w_exp16, f_ensemble_smoothed, "3-Horizon FracDiff Ensemble, 1.5x Leverage, tau=0.030"
    )

    # -------------------------------------------------------------------------
    # EXP-17: EXP-04 + Lottery Skewness Veto
    # -------------------------------------------------------------------------
    w_exp17 = np.zeros((n_bars, n_symbols))
    curr_w = np.zeros(n_symbols)
    for t in range(n_bars):
        if t % 6 == 0:
            m_t = valid_mask[t]
            if np.sum(m_t) >= 20:
                v_idx = np.where(m_t)[0]
                # Zero out scores for vetoed assets on Long side
                masked_scores = f5_smoothed[t].copy()
                for idx in v_idx:
                    if skew_veto_mask[t, idx] and masked_scores[idx] > 0:
                        masked_scores[idx] = -999.0  # Disqualify from Long basket
                tgt_w = allocator_base.compute_risk_parity_weights(
                    scores=masked_scores,
                    valid_idx=v_idx,
                    recent_returns=returns_mat[max(0, t-36):t],
                    top_k=10,
                    target_gross_leverage=1.50
                )
                curr_w = allocator_base.apply_leland_deadband(tgt_w, curr_w, tau=0.030)
        w_exp17[t] = curr_w
    experiments["EXP-17: EXP-04 + Lottery Skewness Veto"] = (
        w_exp17, f5_smoothed, "FracDiff + S_eps > 1.50 Long Veto, 1.5x Lev, tau=0.030"
    )

    # -------------------------------------------------------------------------
    # EXP-18: EXP-04 + Exhaustion Wick Fading (85% Core / 15% ALO Wick Fade)
    # -------------------------------------------------------------------------
    w_exp18 = (0.85 * w_exp04_raw) + fader_weights_raw
    experiments["EXP-18: EXP-04 + Exhaustion Wick Fading"] = (
        w_exp18, f5_smoothed, "85% EXP-04 Core + 15% Maker ALO Wick Fader"
    )

    # -------------------------------------------------------------------------
    # EXP-19: Composite Risk Shield (sigma_target=30% + GZ Floor + Rank Buffer)
    # -------------------------------------------------------------------------
    w_exp19 = np.zeros((n_bars, n_symbols))
    curr_w = np.zeros(n_symbols)
    rank_allocator.reset_state()
    governor.reset_state(initial_nav=10000.0)
    cum_nav = 10000.0
    for t in range(n_bars):
        if t > 0:
            bar_pnl = float(np.sum(w_exp19[t-1] * returns_mat[t]))
            cum_nav *= (1.0 + bar_pnl)
        if t % 6 == 0:
            m_t = valid_mask[t]
            if np.sum(m_t) >= 20:
                v_idx = np.where(m_t)[0]
                recent_p_ret = exp04_bar_returns[max(0, t-24):t]
                composite_lev = governor.compute_composite_risk_shield_leverage(
                    recent_p_ret, cum_nav, sigma_target=0.30, l_min=0.50, l_max=1.80
                )
                longs, shorts = rank_allocator.update_holdings_with_hysteresis(
                    scores=f5_smoothed[t], valid_idx=v_idx
                )
                tgt_w = rank_allocator.compute_risk_parity_weights(
                    longs, shorts, returns_mat[max(0, t-36):t], n_symbols, target_gross_leverage=composite_lev
                )
                curr_w = rank_allocator.apply_leland_deadband(tgt_w, curr_w, tau=0.030)
        w_exp19[t] = curr_w
    experiments["EXP-19: Composite Risk Shield"] = (
        w_exp19, f5_smoothed, "Vol-Target 30% + GZ Floor + Rank-Buffer Sieve (Top 8/Exit 18)"
    )

    # -------------------------------------------------------------------------
    # EXP-20: Production Apex Core Synthesis
    # -------------------------------------------------------------------------
    w_exp20_core = np.zeros((n_bars, n_symbols))
    curr_w = np.zeros(n_symbols)
    rank_allocator.reset_state()
    governor.reset_state(initial_nav=10000.0)
    cum_nav = 10000.0
    for t in range(n_bars):
        if t > 0:
            bar_pnl = float(np.sum(w_exp20_core[t-1] * returns_mat[t]))
            cum_nav *= (1.0 + bar_pnl)
        if t % 6 == 0:
            m_t = valid_mask[t]
            if np.sum(m_t) >= 20:
                v_idx = np.where(m_t)[0]
                recent_p_ret = exp04_bar_returns[max(0, t-24):t]
                composite_lev = governor.compute_composite_risk_shield_leverage(
                    recent_p_ret, cum_nav, sigma_target=0.30, l_min=0.50, l_max=1.80
                )
                longs, shorts = rank_allocator.update_holdings_with_hysteresis(
                    scores=f_ensemble_smoothed[t], valid_idx=v_idx, veto_mask=skew_veto_mask[t]
                )
                tgt_w = rank_allocator.compute_risk_parity_weights(
                    longs, shorts, returns_mat[max(0, t-36):t], n_symbols, target_gross_leverage=composite_lev
                )
                curr_w = rank_allocator.apply_leland_deadband(tgt_w, curr_w, tau=0.030)
        w_exp20_core[t] = curr_w

    # Blend 85% Composite Risk Shield Core + 15% Exhaustion Wick Fader
    w_exp20 = (0.85 * w_exp20_core) + fader_weights_raw
    experiments["EXP-20: Production Apex Core Synthesis"] = (
        w_exp20, f_ensemble_smoothed, "Full Synthesis: Vol-Target 30%, GZ Cushion, Rank Buffer, Skew Veto, Wick Fader"
    )

    return experiments


def main():
    print("=" * 135)
    print("   IRONCORE INSTITUTIONAL FACTORIAL TOURNAMENT 2 (EXP-11 TO EXP-20)")
    print("   Evaluating Risk-Governed Gearing, Rank-Buffer Hysteresis & Orthogonal Multi-Alpha")
    print("=" * 135)

    # 1. Load Data
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
    print("\n[BUILDING TOURNAMENT 2 MATRICES...]")
    experiments = build_tournament_2_matrices(
        close_mat, oracle_mat, volume_mat, valid_mask, returns_mat, symbols, btc_idx, eth_idx
    )
    print(f"Generated weight matrices for all {len(experiments)} canonical experiments.\n")

    # 3. Configure IronCore Engine
    config = IronCoreConfig_v1(
        mc_placebo_draws=150,
        bootstrap_paths=1000,
        initial_capital=10000.0,
    )
    engine = IronCoreEngine(config=config)

    results = []

    print("=" * 140)
    print(f"{'EXPERIMENT ID & CONFIGURATION':<45} | {'CAGR':<8} | {'SHARPE':<6} | {'MAX DD':<7} | {'FRIC RATIO':<10} | {'P(PERM)':<7} | {'DSR':<6} | {'VERDICT':<8}")
    print("-" * 140)

    for exp_name, (w_mat, sig_mat, desc) in experiments.items():
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

        failed = [g.split("(")[1].split(")")[0] for g, passed in gates.items() if not passed]
        failed_str = ", ".join(failed) if failed else "None"

        print(f"{exp_name:<45} | {p['cagr']:>7.2f}% | {p['sharpe']:>6.2f} | {p['max_dd']:>6.2f}% | {p['fric_ratio']:>8.2f}% | {p_perm:>7.4f} | {dsr:>6.4f} | {v_str:<8}", flush=True)

        results.append({
            "name": exp_name,
            "description": desc,
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
            "failed_gates": failed_str,
            "elapsed": elapsed
        })

    print("=" * 140)

    # 4. Summary Table & Forensic Progression
    print("\n\n" + "=" * 140)
    print("                      TOURNAMENT 2 STEPWISE FORENSIC PROGRESSION AUDIT")
    print("=" * 140)
    for r in results:
        status_icon = "[CERTIFIED FOR PROD]" if r["verdict"] == "PASSED" else "[KILLED]"
        print(f"\n>>> {r['name']}: {status_icon}")
        print(f"    Architecture: {r['description']}")
        print(f"    Net CAGR: {r['cagr']:.2f}% | Sharpe: {r['sharpe']:.2f} | Max DD: {r['max_dd']:.2f}% | Turnover: {r['turnover']:.1f}x")
        print(f"    Friction Drag: {r['friction_ratio']:.2f}% of Gross PnL (Gate 3 Max <= 25.0%)")
        print(f"    Placebo p-value: {r['p_perm']:.4f} (Gate 2 Req < 0.0100) | Ruin Prob: {r['ruin_prob']*100:.2f}% | DSR: {r['dsr']:.4f}")
        print(f"    Failed Gates: {r['failed_gates']}")

    print("\n" + "=" * 140)


if __name__ == "__main__":
    main()
