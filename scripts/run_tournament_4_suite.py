"""
TOURNAMENT 4: THE PRODUCTION MASTER APEX SUITE (EXP-31 TO EXP-38)
==================================================================
Benchmarks the final 8 production configurations under the 7-Gate IronCore Engine:
  1. EXP-31: Dual-Shielded Apex (Vol 45% + M=0.25 + Delta L >= 0.20x + 8/18 Rank Buffer)
  2. EXP-32: Extreme Vol-Target Capacity (Vol 50% + L in [0.9, 3.2] + Delta L >= 0.20x)
  3. EXP-33: Asymmetric Cushion Curvature (M=0.20, gamma=1.25, Vol 45% + Delta L >= 0.20x)
  4. EXP-34: Capacity-Adaptive Breadth (Dynamic K in [8, 16] based on NAV + Vol 45%)
  5. EXP-35: Composite Memory Blend (Dual FracDiff d1*=0.38 / d2*=0.42, 60/40 blend)
  6. EXP-36: Pure Passive ALO Maker Bias (80/20 Maker Routing + Vol 45% + Delta L >= 0.20x)
  7. EXP-37: Drawdown-Accelerated Re-entry (Concave Cushion Ramp sqrt(C(t)) + Vol 45%)
  8. EXP-38: The Production Master Apex (Full Synthesis: Dual FracDiff + Capacity Breadth + 80/20 ALO + M=0.22 + Delta L >= 0.20x)
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


def calculate_compounding_milestones(cagr: float) -> Tuple[float, float, float]:
    """Calculates time in months to reach 2x, 5x, and 10x equity."""
    if cagr <= 0:
        return float("inf"), float("inf"), float("inf")
    g = math.log(1.0 + cagr / 100.0)
    t_2x = (math.log(2.0) / g) * 12.0
    t_5x = (math.log(5.0) / g) * 12.0
    t_10x = (math.log(10.0) / g) * 12.0
    return t_2x, t_5x, t_10x


def build_tournament_4_matrices(
    close_mat: np.ndarray,
    oracle_mat: np.ndarray,
    volume_mat: np.ndarray,
    valid_mask: np.ndarray,
    returns_mat: np.ndarray,
    symbols: List[str],
    btc_idx: int,
    eth_idx: int
) -> Tuple[Dict[str, Tuple[np.ndarray, np.ndarray, str, float]], Dict[str, np.ndarray]]:
    """Builds weight matrices for EXP-31 through EXP-38."""
    n_bars, n_symbols = close_mat.shape
    experiments = {}

    print("\n[1/3] Extracting Fractional Differentiation (d1* = 0.38 & d2* = 0.42)...")
    # Signal 1: d1* = 0.38
    fd_series_38 = apply_fractional_differentiation(close_mat, d=0.38, max_len=18)
    fd_diff_38 = fd_series_38 - np.roll(fd_series_38, 1, axis=0)
    fd_diff_38[0] = 0.0
    f5_38, _ = compute_multi_beta_residual_momentum(
        fd_diff_38, fd_diff_38[:, btc_idx], fd_diff_38[:, eth_idx], valid_mask, lookback_h=18
    )

    # Signal 2: d2* = 0.42
    fd_series_42 = apply_fractional_differentiation(close_mat, d=0.42, max_len=18)
    fd_diff_42 = fd_series_42 - np.roll(fd_series_42, 1, axis=0)
    fd_diff_42[0] = 0.0
    f5_42, _ = compute_multi_beta_residual_momentum(
        fd_diff_42, fd_diff_42[:, btc_idx], fd_diff_42[:, eth_idx], valid_mask, lookback_h=18
    )

    allocator_base = DeadbandExecutionAllocator(deadband_base=0.030)
    f5_smoothed_38 = allocator_base.smooth_multi_horizon_alpha(f5_38)
    f5_smoothed_42 = allocator_base.smooth_multi_horizon_alpha(f5_42)

    # Blend 60% d*=0.38 + 40% d*=0.42
    f5_dual_blend = allocator_base.smooth_multi_horizon_alpha(0.60 * f5_38 + 0.40 * f5_42)

    signals_dict = {
        "f5_38": f5_smoothed_38,
        "f5_42": f5_smoothed_42,
        "f5_dual": f5_dual_blend,
    }

    print("[2/3] Computing Pre-Simulated Baseline Return Series for Volatility Gearing...")
    # Baseline for governor volatility lookback
    w_baseline_raw = np.zeros((n_bars, n_symbols))
    curr_w = np.zeros(n_symbols)
    for t in range(n_bars):
        if t % 6 == 0:
            m_t = valid_mask[t]
            if np.sum(m_t) >= 20:
                v_idx = np.where(m_t)[0]
                tgt_w = allocator_base.compute_risk_parity_weights(
                    scores=f5_smoothed_38[t],
                    valid_idx=v_idx,
                    recent_returns=returns_mat[max(0, t-36):t],
                    top_k=10,
                    target_gross_leverage=1.50
                )
                curr_w = allocator_base.apply_leland_deadband(tgt_w, curr_w, tau=0.030)
        w_baseline_raw[t] = curr_w

    baseline_bar_returns = np.sum(w_baseline_raw * returns_mat, axis=1)

    print("[3/3] Generating Factory Portfolios (EXP-31 to EXP-38)...")
    governor = DynamicGearingGovernor()

    def simulate_strategy(
        target_vol: float,
        l_min: float,
        l_max: float,
        target_k: int = 12,
        entry_k: int = 8,
        exit_k: int = 18,
        delta_l_thresh: float = 0.20,
        m_floor: float = 0.25,
        gamma_val: float = 1.00,
        accelerated_reentry: bool = False,
        adaptive_breadth: bool = False,
        signal_matrix: np.ndarray = f5_smoothed_38
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
                
                # Check adaptive breadth if enabled
                if adaptive_breadth:
                    allocator.set_capacity_breadth(cum_nav, base_k=8, min_k=8, max_k=16)

                if np.sum(m_t) >= (allocator.exit_k * 2):
                    v_idx = np.where(m_t)[0]
                    recent_p_ret = baseline_bar_returns[max(0, t-24):t]
                    raw_lev = governor.compute_composite_risk_shield_leverage(
                        recent_port_returns=recent_p_ret,
                        current_nav=cum_nav,
                        sigma_target=target_vol,
                        l_min=l_min,
                        l_max=l_max,
                        m_floor=m_floor,
                        gamma_val=gamma_val,
                        accelerated_reentry=accelerated_reentry
                    )

                    # Apply leverage deadband
                    active_lev = allocator.apply_leverage_deadband(raw_lev, active_lev, delta_thresh=delta_l_thresh)

                    longs, shorts = allocator.update_holdings_with_hysteresis(
                        scores=signal_matrix[t], valid_idx=v_idx
                    )

                    tgt_w = allocator.compute_risk_parity_weights(
                        longs, shorts, returns_mat[max(0, t-36):t], n_symbols, target_gross_leverage=active_lev
                    )

                    curr_w = allocator.apply_leland_deadband(tgt_w, curr_w, tau=0.030)
            w_mat[t] = curr_w
        return w_mat

    # -------------------------------------------------------------------------
    # EXP-31: Dual-Shielded Apex (Vol 45% + M=0.25 + Delta L >= 0.20x)
    # -------------------------------------------------------------------------
    w_exp31 = simulate_strategy(
        target_vol=0.45, l_min=0.80, l_max=2.80, target_k=12, entry_k=8, exit_k=18,
        delta_l_thresh=0.20, m_floor=0.25, gamma_val=1.00, accelerated_reentry=False,
        adaptive_breadth=False, signal_matrix=f5_smoothed_38
    )
    experiments["EXP-31: Dual-Shielded Apex"] = (
        w_exp31, f5_smoothed_38, "Vol-Target 45% + GZ Floor M=0.25 + Delta L >= 0.20x + 8/18 Rank Buffer", 0.60
    )

    # -------------------------------------------------------------------------
    # EXP-32: Extreme Vol-Target Capacity (Vol 50% + L in [0.9, 3.2] + Delta L >= 0.20x)
    # -------------------------------------------------------------------------
    w_exp32 = simulate_strategy(
        target_vol=0.50, l_min=0.90, l_max=3.20, target_k=12, entry_k=8, exit_k=18,
        delta_l_thresh=0.20, m_floor=0.25, gamma_val=1.00, accelerated_reentry=False,
        adaptive_breadth=False, signal_matrix=f5_smoothed_38
    )
    experiments["EXP-32: Extreme Vol-Target Capacity"] = (
        w_exp32, f5_smoothed_38, "Vol-Target 50% + L in [0.9, 3.2] + GZ Floor M=0.25 + Delta L >= 0.20x", 0.60
    )

    # -------------------------------------------------------------------------
    # EXP-33: Asymmetric Cushion Curvature (M=0.20, gamma=1.25, Vol 45%)
    # -------------------------------------------------------------------------
    w_exp33 = simulate_strategy(
        target_vol=0.45, l_min=0.80, l_max=2.80, target_k=12, entry_k=8, exit_k=18,
        delta_l_thresh=0.20, m_floor=0.20, gamma_val=1.25, accelerated_reentry=False,
        adaptive_breadth=False, signal_matrix=f5_smoothed_38
    )
    experiments["EXP-33: Asymmetric Cushion Curvature"] = (
        w_exp33, f5_smoothed_38, "Vol-Target 45% + Tighter Floor M=0.20 + Convex Cushion gamma=1.25", 0.60
    )

    # -------------------------------------------------------------------------
    # EXP-34: Capacity-Adaptive Breadth (Dynamic K in [8, 16] based on NAV)
    # -------------------------------------------------------------------------
    w_exp34 = simulate_strategy(
        target_vol=0.45, l_min=0.80, l_max=2.80, target_k=8, entry_k=8, exit_k=18,
        delta_l_thresh=0.20, m_floor=0.25, gamma_val=1.00, accelerated_reentry=False,
        adaptive_breadth=True, signal_matrix=f5_smoothed_38
    )
    experiments["EXP-34: Capacity-Adaptive Breadth"] = (
        w_exp34, f5_smoothed_38, "Dynamic Breadth K in [8, 16] scaling with NAV + Vol 45% + Delta L >= 0.20x", 0.60
    )

    # -------------------------------------------------------------------------
    # EXP-35: Composite Memory Blend (d1*=0.38 / d2*=0.42 60/40 Blend)
    # -------------------------------------------------------------------------
    w_exp35 = simulate_strategy(
        target_vol=0.45, l_min=0.80, l_max=2.80, target_k=12, entry_k=8, exit_k=18,
        delta_l_thresh=0.20, m_floor=0.25, gamma_val=1.00, accelerated_reentry=False,
        adaptive_breadth=False, signal_matrix=f5_dual_blend
    )
    experiments["EXP-35: Composite Memory Blend"] = (
        w_exp35, f5_dual_blend, "Dual FracDiff (d1*=0.38, d2*=0.42) 60/40 Memory Blend + Vol 45%", 0.60
    )

    # -------------------------------------------------------------------------
    # EXP-36: Pure Passive ALO Maker Bias (80/20 Maker Routing)
    # -------------------------------------------------------------------------
    # Uses same weights as EXP-31, but tested with base_maker_ratio = 0.80
    experiments["EXP-36: Pure Passive ALO Maker Bias"] = (
        w_exp31, f5_smoothed_38, "80/20 ALO Maker Routing (+1.5 bps rebate) + Vol 45% + Delta L >= 0.20x", 0.80
    )

    # -------------------------------------------------------------------------
    # EXP-37: Drawdown-Accelerated Re-entry (Concave Cushion Ramp)
    # -------------------------------------------------------------------------
    w_exp37 = simulate_strategy(
        target_vol=0.45, l_min=0.80, l_max=2.80, target_k=12, entry_k=8, exit_k=18,
        delta_l_thresh=0.20, m_floor=0.25, gamma_val=1.00, accelerated_reentry=True,
        adaptive_breadth=False, signal_matrix=f5_smoothed_38
    )
    experiments["EXP-37: Drawdown-Accelerated Re-entry"] = (
        w_exp37, f5_smoothed_38, "Concave Cushion Recovery sqrt(C(t)) + Vol 45% + Delta L >= 0.20x", 0.60
    )

    # -------------------------------------------------------------------------
    # EXP-38: The Production Master Apex (Full Synthesis)
    # -------------------------------------------------------------------------
    w_exp38 = simulate_strategy(
        target_vol=0.45, l_min=0.80, l_max=2.80, target_k=8, entry_k=8, exit_k=18,
        delta_l_thresh=0.20, m_floor=0.22, gamma_val=1.10, accelerated_reentry=True,
        adaptive_breadth=True, signal_matrix=f5_dual_blend
    )
    experiments["EXP-38: The Production Master Apex"] = (
        w_exp38, f5_dual_blend, "Full Synthesis: Dual FracDiff + Adaptive Breadth + Accel Re-entry + M=0.22 + 80/20 ALO", 0.80
    )

    return experiments, signals_dict


def main():
    print("=" * 155)
    print("   IRONCORE INSTITUTIONAL FACTORIAL TOURNAMENT 4 (EXP-31 TO EXP-38)")
    print("   The Production Master Apex Suite: Compressing the 10x Horizon")
    print("=" * 155)

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
    print("\n[BUILDING TOURNAMENT 4 MATRICES...]")
    experiments, _ = build_tournament_4_matrices(
        close_mat, oracle_mat, volume_mat, valid_mask, returns_mat, symbols, btc_idx, eth_idx
    )
    print(f"Generated weight matrices for all {len(experiments)} candidate configurations.\n")

    # Engines for 60% ALO and 80% ALO
    config_60 = IronCoreConfig_v1(
        base_maker_ratio=0.60,
        mc_placebo_draws=150,
        bootstrap_paths=1000,
        initial_capital=10000.0,
    )
    engine_60 = IronCoreEngine(config=config_60)

    config_80 = IronCoreConfig_v1(
        base_maker_ratio=0.80,
        mc_placebo_draws=150,
        bootstrap_paths=1000,
        initial_capital=10000.0,
    )
    engine_80 = IronCoreEngine(config=config_80)

    results = []

    print("=" * 165)
    print(f"{'EXPERIMENT ID & CONFIGURATION':<46} | {'CAGR':<8} | {'SHARPE':<6} | {'MAX DD':<7} | {'FRIC RATIO':<10} | {'P(PERM)':<7} | {'RUIN(%)':<7} | {'TIME TO 10X':<11} | {'VERDICT':<8}")
    print("-" * 165)

    for exp_name, (w_mat, sig_mat, desc, maker_ratio) in experiments.items():
        engine = engine_80 if maker_ratio > 0.70 else engine_60
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

        print(f"{exp_name:<46} | {p['cagr']:>7.2f}% | {p['sharpe']:>6.2f} | {p['max_dd']:>6.2f}% | {p['fric_ratio']:>8.2f}% | {p_perm:>7.4f} | {ruin*100:>6.2f}% | {t_10x_str:>11} | {v_str:<8}", flush=True)

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
            "calmar": p["cagr"] / max(p["max_dd"], 0.01),
        })

    print("=" * 165)

    # Save results to JSON for auditing and reporting
    out_path = PIPELINE_ROOT / "data" / "tournament_4_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n[TOURNAMENT 4 COMPLETE] Audit results saved to: {out_path}")


if __name__ == "__main__":
    main()
