#!/usr/bin/env python3
"""
Economic Participation & Duty-Cycle Auditor (Gate 1C Preparation)
=================================================================
Evaluates the Economic Participation Rule for autocorrelation thresholds:
  - Objective: Select rho* that minimizes tail drawdown while guaranteeing
    a minimum strategy market active ratio (>= 75% active, or cash downtime <= 25%)
    during trending regimes (Folds 1, 2, and 4).
  - Evaluates both Candidate A (rho-only) and Candidate B (Composite TV + rho)
    across rho* in [-0.20, -0.175, -0.15, -0.125, -0.10].
  - Computes institutional risk utility U(Strategy) at gamma=2.0 and gamma threshold.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
import polars as pl

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from backtest_10x_convex_compounding import (
    DATA_LAKE_PATH,
    BENCHMARK_SYMBOL,
    EVAL_START_TS,
)
from src.data.pit_universe_manager import PointInTimeUniverseManager
from scripts.run_stage3a_turnover_velocity_gate import (
    compute_turnover_velocity_series,
)
from scripts.run_2x2_mechanism_ablation import (
    compute_cross_sectional_autocorrelation,
)


def run_duty_cycle_audit():
    print("=" * 115)
    print("   ECONOMIC PARTICIPATION & DUTY-CYCLE AUDIT (GATE 1C PREPARATION)   ")
    print("   Evaluating Duty-Cycle Downtime Invariant: Cash Downtime <= 25.0% in Trending Regimes")
    print("=" * 115)

    df_raw = pl.read_parquet(DATA_LAKE_PATH)
    btc_df = df_raw.filter(pl.col("symbol") == BENCHMARK_SYMBOL).sort("timestamp_ms")
    all_timestamps = btc_df["timestamp_ms"].to_list()
    eval_start_idx = all_timestamps.index(EVAL_START_TS)
    max_lake_ts = all_timestamps[-1]
    total_eval_bars = len(all_timestamps) - 1 - eval_start_idx

    eval_timestamps, symbols, full_market_data = PointInTimeUniverseManager.load_pit_market_matrices(
        df=df_raw,
        eval_start_ts=EVAL_START_TS,
        eval_end_ts=max_lake_ts,
        benchmark_symbol=BENCHMARK_SYMBOL,
    )

    # 1. Compute Indicators
    tv_20d = compute_turnover_velocity_series(full_market_data, eval_start_idx, total_eval_bars, 120)
    is_tv = tv_20d[:1470]
    q_thresh_tv = float(np.quantile(is_tv, 0.15))
    mask_tv = tv_20d < q_thresh_tv

    rho_7d = compute_cross_sectional_autocorrelation(
        full_market_data["close"],
        full_market_data["valid_price_mask"],
        eval_start_idx,
        total_eval_bars,
        window_bars=42,
    )

    # Partition indices
    partitions = {
        "Overall Extended (2,284b)": (0, total_eval_bars),
        "Fold 1 [Trending] (360b)": (750, 1110),
        "Fold 2 [Trending] (360b)": (1110, 1470),
        "Fold 3 [Chop Grinder] (360b)": (1470, 1830),
        "Fold 4 [Trending] (360b)": (1830, 2190),
        "Sept 2026 Tail [Downdraft] (94b)": (2190, total_eval_bars),
    }

    trending_bars_mask = np.zeros(total_eval_bars, dtype=bool)
    trending_bars_mask[750:1470] = True
    trending_bars_mask[1830:2190] = True
    n_trending = np.sum(trending_bars_mask)

    thresholds = [-0.20, -0.175, -0.15, -0.125, -0.10]
    records = []

    print("\n>>> CANDIDATE A (RHO-ONLY): CASH DOWNTIME BY REGIME <<<")
    print("-" * 115)
    print(f"{'RHO THRESHOLD':<15} {'OVERALL DOWNTIME':<18} {'TRENDING DOWNTIME':<20} {'FOLD 3 DOWNTIME':<18} {'SEPT TAIL DOWNTIME':<20} {'DUTY COMPLIANCE'}")
    print("-" * 115)

    for r_th in thresholds:
        m_rho = rho_7d < r_th
        downtime_overall = (np.sum(m_rho) / total_eval_bars) * 100.0
        downtime_trending = (np.sum(m_rho & trending_bars_mask) / n_trending) * 100.0
        downtime_f3 = (np.sum(m_rho[1470:1830]) / 360.0) * 100.0
        downtime_tail = (np.sum(m_rho[2190:total_eval_bars]) / (total_eval_bars - 2190)) * 100.0
        passed_rule = downtime_trending <= 25.0

        tag = " (BASE)" if r_th == -0.15 else ""
        comp_str = "PASS (<=25%)" if passed_rule else "VIOLATION (>25%)"
        print(f"{str(r_th) + tag:<15} {downtime_overall:>6.1f}% ({np.sum(m_rho):>4}b)     {downtime_trending:>6.1f}% ({np.sum(m_rho & trending_bars_mask):>4}b)     {downtime_f3:>6.1f}% ({np.sum(m_rho[1470:1830]):>3}b)     {downtime_tail:>6.1f}% ({np.sum(m_rho[2190:total_eval_bars]):>2}b)     {comp_str}")

        records.append({
            "model": "rho_only",
            "threshold": r_th,
            "downtime_overall_pct": round(downtime_overall, 2),
            "downtime_trending_pct": round(downtime_trending, 2),
            "downtime_f3_pct": round(downtime_f3, 2),
            "downtime_tail_pct": round(downtime_tail, 2),
            "duty_cycle_passed": bool(passed_rule),
        })

    print("-" * 115)

    print("\n>>> CANDIDATE B (COMPOSITE TV + RHO): CASH DOWNTIME BY REGIME <<<")
    print("-" * 115)
    print(f"{'RHO THRESHOLD':<15} {'OVERALL DOWNTIME':<18} {'TRENDING DOWNTIME':<20} {'FOLD 3 DOWNTIME':<18} {'SEPT TAIL DOWNTIME':<20} {'DUTY COMPLIANCE'}")
    print("-" * 115)

    for r_th in thresholds:
        m_comp = mask_tv | (rho_7d < r_th)
        downtime_overall = (np.sum(m_comp) / total_eval_bars) * 100.0
        downtime_trending = (np.sum(m_comp & trending_bars_mask) / n_trending) * 100.0
        downtime_f3 = (np.sum(m_comp[1470:1830]) / 360.0) * 100.0
        downtime_tail = (np.sum(m_comp[2190:total_eval_bars]) / (total_eval_bars - 2190)) * 100.0
        passed_rule = downtime_trending <= 25.0

        tag = " (BASE)" if r_th == -0.15 else ""
        comp_str = "PASS (<=25%)" if passed_rule else "VIOLATION (>25%)"
        print(f"{str(r_th) + tag:<15} {downtime_overall:>6.1f}% ({np.sum(m_comp):>4}b)     {downtime_trending:>6.1f}% ({np.sum(m_comp & trending_bars_mask):>4}b)     {downtime_f3:>6.1f}% ({np.sum(m_comp[1470:1830]):>3}b)     {downtime_tail:>6.1f}% ({np.sum(m_comp[2190:total_eval_bars]):>2}b)     {comp_str}")

        records.append({
            "model": "composite",
            "threshold": r_th,
            "downtime_overall_pct": round(downtime_overall, 2),
            "downtime_trending_pct": round(downtime_trending, 2),
            "downtime_f3_pct": round(downtime_f3, 2),
            "downtime_tail_pct": round(downtime_tail, 2),
            "duty_cycle_passed": bool(passed_rule),
        })

    print("-" * 115)

    # 3. Institutional Risk Utility Function
    print("\n>>> INSTITUTIONAL UTILITY U(STRATEGY) [MDD_target = 0.50, gamma = 2.0] <<<")
    print("-" * 115)
    print("Formula: U = Sharpe_ext - gamma * max(0, (MDD_ext - 0.50) / 0.50)")

    # Candidate A (-0.15): Sh=2.0651, MDD=0.5122
    sh_a = 2.0651
    mdd_a = 0.5122
    u_a = sh_a - 2.0 * max(0.0, (mdd_a - 0.50) / 0.50)

    # Candidate B (-0.15): Sh=1.8135, MDD=0.4860
    sh_b = 1.8135
    mdd_b = 0.4860
    u_b = sh_b - 2.0 * max(0.0, (mdd_b - 0.50) / 0.50)

    # Indifference gamma: sh_a - gamma * ((mdd_a - 0.50)/0.50) = sh_b
    gamma_indifference = (sh_a - sh_b) / ((mdd_a - 0.50) / 0.50)

    print(f"  • Candidate A (Rho-Only -0.15):   Sharpe={sh_a:.4f} | MDD={mdd_a*100:.2f}% | U(A) = {u_a:.4f}")
    print(f"  • Candidate B (Composite -0.15):  Sharpe={sh_b:.4f} | MDD={mdd_b*100:.2f}% | U(B) = {u_b:.4f}")
    print(f"  • Utility Delta:                 U(A) - U(B) = {u_a - u_b:+.4f} (Candidate A Dominates by +{((u_a/u_b)-1)*100:.1f}%)")
    print(f"  • Indifference Penalty Gamma:    gamma* = {gamma_indifference:.2f}")
    print(f"    (Candidate B only optimal if allocator penalty scalar exceeds {gamma_indifference:.1f}x)")
    print("=" * 115 + "\n")

    out_file = PIPELINE_ROOT / "data" / "duty_cycle_and_utility_audit.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w") as f:
        json.dump({
            "duty_cycle_records": records,
            "utility_comparison": {
                "candidate_a_rho_only": {"sharpe": sh_a, "mdd": mdd_a, "utility_gamma2": round(u_a, 4)},
                "candidate_b_composite": {"sharpe": sh_b, "mdd": mdd_b, "utility_gamma2": round(u_b, 4)},
                "indifference_gamma": round(gamma_indifference, 2),
            }
        }, f, indent=2)
    print(f"[SAVED] Duty-cycle and utility ledger written to {out_file}")


if __name__ == "__main__":
    run_duty_cycle_audit()
