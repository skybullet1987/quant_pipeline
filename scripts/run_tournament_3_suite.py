"""
TOURNAMENT 3: COMPRESSING THE 10X COMPOUNDING HORIZON (EXP-21 TO EXP-30)
========================================================================
Benchmarks the 4 structural acceleration levers on the EXP-19 Alpha Champion:
  1. Leverage Modulation Deadband (Delta L >= 0.15x)
  2. Convex Power-Rank Weighting (alpha in [1.25, 1.50])
  3. Shielded Target Volatility Scaling (35% to 45%)
  4. Momentum-Congruent Carry Booster & Toxic Funding Veto
  5. The Grand Apex Architecture (EXP-30)
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
from src.alpha.congruent_carry_engine import CongruentCarryEngine


def build_tournament_3_matrices(
    close_mat: np.ndarray,
    oracle_mat: np.ndarray,
    volume_mat: np.ndarray,
    valid_mask: np.ndarray,
    returns_mat: np.ndarray,
    predicted_funding: np.ndarray,
    symbols: List[str],
    btc_idx: int,
    eth_idx: int
) -> Dict[str, Tuple[np.ndarray, np.ndarray, str]]:
    """Builds weight matrices for EXP-21 through EXP-30."""
    n_bars, n_symbols = close_mat.shape
    experiments = {}

    print("\n[1/3] Extracting Fractional Differentiation (d* = 0.38) & Residual Momentum...")
    fd_series_38 = apply_fractional_differentiation(close_mat, d=0.38, max_len=18)
    fd_diff = fd_series_38 - np.roll(fd_series_38, 1, axis=0)
    fd_diff[0] = 0.0
    f5_base, residuals = compute_multi_beta_residual_momentum(
        fd_diff, fd_diff[:, btc_idx], fd_diff[:, eth_idx], valid_mask, lookback_h=18
    )

    allocator_base = DeadbandExecutionAllocator(deadband_base=0.030)
    f5_smoothed = allocator_base.smooth_multi_horizon_alpha(f5_base)

    print("[2/3] Computing Momentum-Congruent Carry Scores...")
    carry_engine = CongruentCarryEngine()
    f5_congruent = carry_engine.compute_congruent_carry_scores(
        f5_smoothed, predicted_funding, valid_mask
    )

    print("[3/3] Generating Factory Portfolios (EXP-21 to EXP-30)...")
    governor = DynamicGearingGovernor()

    # Pre-simulate baseline return series for volatility estimation
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

    # Helper function to simulate a rank-buffered, risk-governed portfolio
    def simulate_strategy(
        target_vol: float,
        l_min: float,
        l_max: float,
        target_k: int,
        entry_k: int,
        exit_k: int,
        use_power_sizing: bool = False,
        alpha: float = 1.25,
        use_leverage_deadband: bool = True,
        delta_l_thresh: float = 0.15,
        signal_matrix: np.ndarray = f5_smoothed
    ) -> np.ndarray:
        allocator = RankBufferAllocator(target_k=target_k, entry_k=entry_k, exit_k=exit_k, deadband_tau=0.030)
        w_mat = np.zeros((n_bars, n_symbols))
        curr_w = np.zeros(n_symbols)
        active_lev = 1.00
        cum_nav = 10000.0
        governor.reset_state(initial_nav=cum_nav)

        for t in range(n_bars):
            if t > 0:
                bar_pnl = float(np.sum(w_mat[t-1] * returns_mat[t]))
                cum_nav *= (1.0 + bar_pnl)

            if t % 6 == 0:
                m_t = valid_mask[t]
                if np.sum(m_t) >= (exit_k * 2):
                    v_idx = np.where(m_t)[0]
                    recent_p_ret = baseline_bar_returns[max(0, t-24):t]
                    raw_lev = governor.compute_composite_risk_shield_leverage(
                        recent_p_ret, cum_nav, sigma_target=target_vol, l_min=l_min, l_max=l_max
                    )

                    # Apply leverage deadband if enabled
                    if use_leverage_deadband:
                        active_lev = allocator.apply_leverage_deadband(raw_lev, active_lev, delta_thresh=delta_l_thresh)
                    else:
                        active_lev = raw_lev

                    longs, shorts = allocator.update_holdings_with_hysteresis(
                        scores=signal_matrix[t], valid_idx=v_idx
                    )

                    if use_power_sizing:
                        tgt_w = allocator.compute_convex_power_weights(
                            longs, shorts, signal_matrix[t], returns_mat[max(0, t-36):t],
                            n_symbols, target_gross_leverage=active_lev, alpha=alpha, max_single_weight=0.20
                        )
                    else:
                        tgt_w = allocator.compute_risk_parity_weights(
                            longs, shorts, returns_mat[max(0, t-36):t], n_symbols, target_gross_leverage=active_lev
                        )

                    curr_w = allocator.apply_leland_deadband(tgt_w, curr_w, tau=0.030)
            w_mat[t] = curr_w
        return w_mat

    # -------------------------------------------------------------------------
    # EXP-21: EXP-19 + Leverage Deadband (Delta L >= 0.15)
    # -------------------------------------------------------------------------
    w_exp21 = simulate_strategy(
        target_vol=0.30, l_min=0.50, l_max=1.80, target_k=12, entry_k=8, exit_k=18,
        use_power_sizing=False, use_leverage_deadband=True, delta_l_thresh=0.15
    )
    experiments["EXP-21: EXP-19 + Leverage Deadband"] = (
        w_exp21, f5_smoothed, "Vol-Target 30% + GZ Floor + Rank Buffer + Delta L >= 0.15x"
    )

    # -------------------------------------------------------------------------
    # EXP-22: EXP-19 + Convex Power Sizing (alpha = 1.25)
    # -------------------------------------------------------------------------
    w_exp22 = simulate_strategy(
        target_vol=0.30, l_min=0.50, l_max=1.80, target_k=12, entry_k=8, exit_k=18,
        use_power_sizing=True, alpha=1.25, use_leverage_deadband=True, delta_l_thresh=0.15
    )
    experiments["EXP-22: EXP-19 + Power Sizing (a=1.25)"] = (
        w_exp22, f5_smoothed, "Vol-Target 30% + GZ Floor + Rank Buffer + Convex Power a=1.25"
    )

    # -------------------------------------------------------------------------
    # EXP-23: EXP-19 + Aggressive Power Sizing (alpha = 1.50)
    # -------------------------------------------------------------------------
    w_exp23 = simulate_strategy(
        target_vol=0.30, l_min=0.50, l_max=1.80, target_k=12, entry_k=8, exit_k=18,
        use_power_sizing=True, alpha=1.50, use_leverage_deadband=True, delta_l_thresh=0.15
    )
    experiments["EXP-23: EXP-19 + Power Sizing (a=1.50)"] = (
        w_exp23, f5_smoothed, "Vol-Target 30% + GZ Floor + Rank Buffer + Aggressive Power a=1.50"
    )

    # -------------------------------------------------------------------------
    # EXP-24: Shielded Vol-Target Scaling (35% Vol)
    # -------------------------------------------------------------------------
    w_exp24 = simulate_strategy(
        target_vol=0.35, l_min=0.60, l_max=2.00, target_k=12, entry_k=8, exit_k=18,
        use_power_sizing=False, use_leverage_deadband=True, delta_l_thresh=0.15
    )
    experiments["EXP-24: Shielded Vol-Target Scaling (35%)"] = (
        w_exp24, f5_smoothed, "sigma_target=35%, L in [0.6, 2.0], GZ Floor, Delta L >= 0.15x"
    )

    # -------------------------------------------------------------------------
    # EXP-25: Shielded Vol-Target Scaling (40% Vol)
    # -------------------------------------------------------------------------
    w_exp25 = simulate_strategy(
        target_vol=0.40, l_min=0.70, l_max=2.40, target_k=12, entry_k=8, exit_k=18,
        use_power_sizing=False, use_leverage_deadband=True, delta_l_thresh=0.15
    )
    experiments["EXP-25: Shielded Vol-Target Scaling (40%)"] = (
        w_exp25, f5_smoothed, "sigma_target=40%, L in [0.7, 2.4], GZ Floor, Delta L >= 0.15x"
    )

    # -------------------------------------------------------------------------
    # EXP-26: Shielded Vol-Target Scaling (45% Vol)
    # -------------------------------------------------------------------------
    w_exp26 = simulate_strategy(
        target_vol=0.45, l_min=0.80, l_max=2.80, target_k=12, entry_k=8, exit_k=18,
        use_power_sizing=False, use_leverage_deadband=True, delta_l_thresh=0.15
    )
    experiments["EXP-26: Shielded Vol-Target Scaling (45%)"] = (
        w_exp26, f5_smoothed, "sigma_target=45%, L in [0.8, 2.8], GZ Floor, Delta L >= 0.15x"
    )

    # -------------------------------------------------------------------------
    # EXP-27: Narrow Focused Breadth (Top 5 / Exit 12)
    # -------------------------------------------------------------------------
    w_exp27 = simulate_strategy(
        target_vol=0.30, l_min=0.50, l_max=1.80, target_k=5, entry_k=5, exit_k=12,
        use_power_sizing=False, use_leverage_deadband=True, delta_l_thresh=0.15
    )
    experiments["EXP-27: Narrow Breadth (Top 5 / Exit 12)"] = (
        w_exp27, f5_smoothed, "5 Longs / 5 Shorts (Top 5 Entry / Exit 12 Retention)"
    )

    # -------------------------------------------------------------------------
    # EXP-28: Momentum-Congruent Carry Booster
    # -------------------------------------------------------------------------
    w_exp28 = simulate_strategy(
        target_vol=0.30, l_min=0.50, l_max=1.80, target_k=12, entry_k=8, exit_k=18,
        use_power_sizing=False, use_leverage_deadband=True, delta_l_thresh=0.15,
        signal_matrix=f5_congruent
    )
    experiments["EXP-28: Momentum-Congruent Carry Booster"] = (
        w_exp28, f5_congruent, "FracDiff + Congruent Carry Overlay + Toxic Funding Veto"
    )

    # -------------------------------------------------------------------------
    # EXP-29: Dual Synthesis (Power Sizing + 35% Vol)
    # -------------------------------------------------------------------------
    w_exp29 = simulate_strategy(
        target_vol=0.35, l_min=0.60, l_max=2.00, target_k=12, entry_k=8, exit_k=18,
        use_power_sizing=True, alpha=1.25, use_leverage_deadband=True, delta_l_thresh=0.15
    )
    experiments["EXP-29: Dual Synthesis (Power + 35% Vol)"] = (
        w_exp29, f5_smoothed, "Vol-Target 35% + GZ Floor + Power Sizing a=1.25 + Delta L >= 0.15x"
    )

    # -------------------------------------------------------------------------
    # EXP-30: The Grand Apex Architecture
    # -------------------------------------------------------------------------
    w_exp30 = simulate_strategy(
        target_vol=0.38, l_min=0.60, l_max=2.20, target_k=6, entry_k=6, exit_k=14,
        use_power_sizing=True, alpha=1.25, use_leverage_deadband=True, delta_l_thresh=0.15,
        signal_matrix=f5_congruent
    )
    experiments["EXP-30: The Grand Apex Architecture"] = (
        w_exp30, f5_congruent, "Full Synthesis: Vol-Target 38%, GZ Floor, 6/14 Buffer, Power a=1.25, Congruent Carry"
    )

    return experiments


def calculate_compounding_milestones(cagr: float) -> Tuple[float, float, float]:
    """Calculates time in months to reach 2x, 5x, and 10x equity."""
    if cagr <= 0:
        return float("inf"), float("inf"), float("inf")
    g = math.log(1.0 + cagr / 100.0)
    t_2x = (math.log(2.0) / g) * 12.0
    t_5x = (math.log(5.0) / g) * 12.0
    t_10x = (math.log(10.0) / g) * 12.0
    return t_2x, t_5x, t_10x


def main():
    print("=" * 145)
    print("   IRONCORE INSTITUTIONAL FACTORIAL TOURNAMENT 3 (EXP-21 TO EXP-30)")
    print("   Compressing the 10x Compounding Horizon via Structural Levers")
    print("=" * 145)

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
    print("\n[BUILDING TOURNAMENT 3 MATRICES...]")
    experiments = build_tournament_3_matrices(
        close_mat, oracle_mat, volume_mat, valid_mask, returns_mat, predicted_funding, symbols, btc_idx, eth_idx
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

    print("=" * 155)
    print(f"{'EXPERIMENT ID & CONFIGURATION':<44} | {'CAGR':<8} | {'SHARPE':<6} | {'MAX DD':<7} | {'FRIC RATIO':<10} | {'P(PERM)':<7} | {'TIME TO 10X':<11} | {'VERDICT':<8}")
    print("-" * 155)

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

        t_2x, t_5x, t_10x = calculate_compounding_milestones(p["cagr"])
        t_10x_str = f"{t_10x:.1f} mo" if not math.isinf(t_10x) else "Never"

        failed = [g.split("(")[1].split(")")[0] for g, passed in gates.items() if not passed]
        failed_str = ", ".join(failed) if failed else "None"

        print(f"{exp_name:<44} | {p['cagr']:>7.2f}% | {p['sharpe']:>6.2f} | {p['max_dd']:>6.2f}% | {p['fric_ratio']:>8.2f}% | {p_perm:>7.4f} | {t_10x_str:>11} | {v_str:<8}", flush=True)

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
            "t_2x": t_2x,
            "t_5x": t_5x,
            "t_10x": t_10x,
            "failed_gates": failed_str,
            "elapsed": elapsed
        })

    print("=" * 155)

    # 4. Compounding Progression & Final Forensic Analysis
    print("\n\n" + "=" * 155)
    print("                      TOURNAMENT 3 COMPOUNDING ACCELERATION & FORENSIC AUDIT")
    print("=" * 155)
    for r in results:
        status_icon = "[CERTIFIED FOR PROD]" if r["verdict"] == "PASSED" else "[KILLED]"
        t10_str = f"{r['t_10x']:.1f} months ({r['t_10x']/12.0:.1f} years)" if not math.isinf(r['t_10x']) else "Liquidated / Never"
        t2_str = f"{r['t_2x']:.1f} mo" if not math.isinf(r['t_2x']) else "Never"
        t5_str = f"{r['t_5x']:.1f} mo" if not math.isinf(r['t_5x']) else "Never"

        print(f"\n>>> {r['name']}: {status_icon}")
        print(f"    Architecture: {r['description']}")
        print(f"    Net CAGR: {r['cagr']:.2f}% | Sharpe: {r['sharpe']:.2f} | Max DD: {r['max_dd']:.2f}% | Turnover: {r['turnover']:.1f}x")
        print(f"    Friction Drag: {r['friction_ratio']:.2f}% of Gross PnL (Gate 3 Max <= 25.0%)")
        print(f"    Placebo p-value: {r['p_perm']:.4f} (Gate 2 Req < 0.0100) | Ruin Prob: {r['ruin_prob']*100:.2f}% | DSR: {r['dsr']:.4f}")
        print(f"    Compounding Milestones: Time to 2x: {t2_str} | Time to 5x: {t5_str} | Time to 10x: {t10_str}")
        print(f"    Failed Gates: {r['failed_gates']}")

    print("\n" + "=" * 155)


if __name__ == "__main__":
    main()
