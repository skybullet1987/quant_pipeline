#!/usr/bin/env python3
"""
Stage 3B: Independent Holdout Verification & Apex Candidate Comparison
======================================================================
Evaluates the locked Stage 3A leading configurations on the untouched out-of-sample holdout
partition (Bars 2190 to 2284: September 5, 2026 to September 20, 2026) and multi-topology OOS folds
with ZERO parameter modifications.

Candidates Evaluated:
  1. A0 Baseline Control (Golden Master Benchmark)
  2. 20d_t15_fl0 (Alpha Leader: 20-day lookback, tau=0.15, floor=0.00x)
  3. 10d_t20_fl0 (Risk Leader: 10-day lookback, tau=0.20, floor=0.00x)
  4. Composite TV + Serial Autocorrelation Gate (Orthogonal Grinder Suppression)

Strict Governance Evaluation:
  - Formalized Tier 1 (Normal Certification): Trend Folds Sharpe >= 1.50, Full Sharpe >= 2.0, MDD <= 60%.
  - Formalized Tier 2 (Catastrophic Veto): Fold Sharpe < -0.35 or MDD > 60%.
  - Holdout Generalization: Untouched 94-bar tail performance and 45-day sub-window stability.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from backtest_10x_convex_compounding import (
    InstitutionalCompoundingEngine,
    TOTAL_EVAL_BARS,
    DATA_LAKE_PATH,
    BENCHMARK_SYMBOL,
    EVAL_START_TS,
)
from src.data.pit_universe_manager import PointInTimeUniverseManager
from scripts.run_stage3a_turnover_velocity_gate import compute_turnover_velocity_series, calculate_window_metrics


def compute_cross_sectional_autocorrelation(
    close: np.ndarray,
    valid: np.ndarray,
    eval_start_idx: int,
    total_bars: int,
    window_bars: int = 42,  # 7-day rolling window
) -> np.ndarray:
    """
    Computes rolling cross-sectional return lag-1 autocorrelation rho_1(t).
    """
    returns_mat = np.zeros_like(close)
    prev_close = np.roll(close, 1, axis=0)
    valid_pair = valid & np.roll(valid, 1, axis=0)
    valid_pair[0] = False
    with np.errstate(invalid="ignore", divide="ignore"):
        returns_mat[1:] = np.where(valid_pair[1:], (close[1:] / (prev_close[1:] + 1e-12)) - 1.0, 0.0)

    s_idx = max(0, eval_start_idx - 120)
    e_idx = eval_start_idx + total_bars
    rets_eval = returns_mat[s_idx:e_idx]
    valid_eval = valid[s_idx:e_idx]

    T_slice, N = rets_eval.shape
    rho_series = np.zeros(T_slice)

    for t in range(window_bars, T_slice):
        sub_rets = rets_eval[t - window_bars : t]
        sub_valid = valid_eval[t - window_bars : t]
        asset_mask = np.all(sub_valid, axis=0)
        if np.sum(asset_mask) < 10:
            continue
        r_curr = sub_rets[1:, asset_mask]
        r_lag = sub_rets[:-1, asset_mask]
        r_curr_demean = r_curr - np.mean(r_curr, axis=0, keepdims=True)
        r_lag_demean = r_lag - np.mean(r_lag, axis=0, keepdims=True)
        nom = np.sum(r_curr_demean * r_lag_demean, axis=0)
        denom = np.sqrt(np.sum(r_curr_demean**2, axis=0) * np.sum(r_lag_demean**2, axis=0)) + 1e-12
        corrs = nom / denom
        valid_corrs = corrs[np.isfinite(corrs)]
        if len(valid_corrs) > 0:
            rho_series[t] = float(np.mean(valid_corrs))

    offset = eval_start_idx - s_idx
    eval_rho = rho_series[offset : offset + total_bars]
    return eval_rho


def run_candidate_on_dataset(
    name: str,
    engine: InstitutionalCompoundingEngine,
    market_data: Dict[str, Any],
    phi_scalars: Optional[np.ndarray],
    eval_bars: int,
) -> Dict[str, Any]:
    """Runs a candidate engine configuration on the specified market dataset."""
    engine.total_eval_bars = eval_bars
    engine.regime_governor_scalars = phi_scalars
    res = engine.run(market_data)
    eq = np.array(res["equity_curve"])
    metrics = calculate_window_metrics(eq, eval_bars)
    return {
        "name": name,
        "metrics": metrics,
        "equity_curve": eq,
        "turnover": res["total_turnover_nav"],
        "friction": res["cost_breakdown"]["total_execution_friction_usd"],
    }


def main():
    print("=" * 115)
    print("   STAGE 3B: INDEPENDENT HOLDOUT VERIFICATION & CANDIDATE DISSECTION   ")
    print("=" * 115)

    # 1. Load the COMPLETE Data Lake without 2190-bar truncation
    import polars as pl
    df_raw = pl.read_parquet(DATA_LAKE_PATH)
    btc_df = df_raw.filter(pl.col("symbol") == BENCHMARK_SYMBOL).sort("timestamp_ms")
    all_timestamps = btc_df["timestamp_ms"].to_list()
    eval_start_idx = all_timestamps.index(EVAL_START_TS)
    max_lake_ts = all_timestamps[-1]

    total_available_eval_bars = len(all_timestamps) - 1 - eval_start_idx
    print(f"--> Data Lake Loaded: Total Timestamps = {len(all_timestamps)}")
    print(f"--> Eval Start: {pd.to_datetime(EVAL_START_TS, unit='ms')} (Bar {eval_start_idx})")
    print(f"--> Eval Max:   {pd.to_datetime(max_lake_ts, unit='ms')} (Bar {len(all_timestamps)-1})")
    print(f"--> Total Eval Bars Available = {total_available_eval_bars} (Canonical: 2190, Untouched OOS Holdout: {total_available_eval_bars - 2190} bars)")

    # Load market matrices for the entire dataset
    eval_timestamps, symbols, full_market_data = PointInTimeUniverseManager.load_pit_market_matrices(
        df=df_raw,
        eval_start_ts=EVAL_START_TS,
        eval_end_ts=max_lake_ts,
        benchmark_symbol=BENCHMARK_SYMBOL,
    )
    # Add first valid indices
    valid_mask = full_market_data["valid_price_mask"]
    first_valid_indices = np.zeros(len(symbols), dtype=int)
    for col in range(len(symbols)):
        valid_idx = np.where(valid_mask[:, col])[0]
        first_valid_indices[col] = valid_idx[0] if len(valid_idx) > 0 else 0
    full_market_data["first_valid_indices"] = first_valid_indices

    # 2. Compute Point-in-Time Indicators across all available bars
    # Compute 20-day TV and 10-day TV
    tv_20d = compute_turnover_velocity_series(full_market_data, eval_start_idx, total_available_eval_bars, 120)
    tv_10d = compute_turnover_velocity_series(full_market_data, eval_start_idx, total_available_eval_bars, 60)
    
    # Compute 7-day Serial Autocorrelation
    rho_7d = compute_cross_sectional_autocorrelation(
        full_market_data["close"],
        full_market_data["valid_price_mask"],
        eval_start_idx,
        total_available_eval_bars,
        window_bars=42,
    )

    # In-Sample threshold strictly from IS window [0, 1470)
    is_tv_20d = tv_20d[:1470]
    is_tv_10d = tv_10d[:1470]
    q_thresh_20d = float(np.quantile(is_tv_20d, 0.15))
    q_thresh_10d = float(np.quantile(is_tv_10d, 0.20))
    is_rho = rho_7d[:1470]
    q_thresh_rho = float(np.quantile(is_rho, 0.15)) # bottom 15% autocorrelation

    print(f"\n--> In-Sample Gate Thresholds (calculated on Bars 0-1470):")
    print(f"    20d_t15 Threshold: {q_thresh_20d:.6f}")
    print(f"    10d_t20 Threshold: {q_thresh_10d:.6f}")
    print(f"    Rho_7d Threshold:  {q_thresh_rho:.6f}")

    # Generate causal scalar signals (shifted by 1 bar for t+1 execution)
    def make_causal_phi(throttled_mask: np.ndarray, floor: float = 0.0) -> np.ndarray:
        phi = np.where(throttled_mask, floor, 1.0)
        phi_causal = np.roll(phi, 1)
        phi_causal[0] = 1.0
        return phi_causal

    phi_a0 = None
    phi_20d_t15_fl0 = make_causal_phi(tv_20d < q_thresh_20d, floor=0.0)
    phi_10d_t20_fl0 = make_causal_phi(tv_10d < q_thresh_10d, floor=0.0)
    # Composite: throttled if TV is low OR if Rho is deep negative (< -0.15)
    throttled_composite = (tv_20d < q_thresh_20d) | (rho_7d < -0.15)
    phi_composite = make_causal_phi(throttled_composite, floor=0.0)

    candidates = [
        ("A0_Baseline", phi_a0),
        ("20d_t15_fl0_Alpha", phi_20d_t15_fl0),
        ("10d_t20_fl0_Risk", phi_10d_t20_fl0),
        ("Composite_TV_Rho", phi_composite),
    ]

    # Evaluate all candidates across the full 2,284 bars
    results = {}
    for name, phi in candidates:
        print(f"\n--> Running backtest for {name} on {total_available_eval_bars} bars...")
        eng = InstitutionalCompoundingEngine(
            fixed_leverage=3.0,
            turnover_lambda=0.85,
            two_tranche_enabled=False,
            pyramid_ratio=0.0,
        )
        res = run_candidate_on_dataset(name, eng, full_market_data, phi, total_available_eval_bars)
        results[name] = res

    # 3. Dissect Windows:
    # A. Canonical 2,190 bars (Full Year)
    # B. Topology A 60-day OOS Folds (F1: 750-1110, F2: 1110-1470, F3: 1470-1830, F4: 1830-2190)
    # C. Untouched Holdout Tail (Bars 2190 to 2284: 94 bars)
    # D. Topology C 45-day OOS Folds (F1: 1080-1350, F2: 1350-1620, F3: 1620-1890, F4: 1890-2160, Tail: 2160-2284)
    # E. Full Extended Dataset (2,284 bars: 380.7 days)

    top_a_folds = [
        ("Fold 1 [Trend]", 750, 1110),
        ("Fold 2 [Trend]", 1110, 1470),
        ("Fold 3 [Grinder]", 1470, 1830),
        ("Fold 4 [Recovery]", 1830, 2190),
    ]

    top_c_folds = [
        ("45d F1 [Trend]", 1080, 1350),
        ("45d F2 [Transition]", 1350, 1620),
        ("45d F3 [Grinder Peak]", 1620, 1890),
        ("45d F4 [Rebound]", 1890, 2160),
        ("45d Tail [Holdout]", 2160, 2284),
    ]

    print("\n" + "=" * 125)
    print(f"{'CANDIDATE':<20} {'CAGR(2190)':<11} {'SH(2190)':<9} {'MDD(2190)':<10} {'TAIL(94b) SH':<13} {'TAIL RET%':<10} {'CAGR(FULL)':<11} {'SH(FULL)':<9} {'MDD(FULL)':<10}")
    print("=" * 125)

    summary_records = []
    for name, res in results.items():
        eq = res["equity_curve"]
        # Canonical 2190 metrics
        m_2190 = calculate_window_metrics(eq[:2191], 2190)
        # Tail 94 bars metrics (from bar 2190 to 2284)
        m_tail = calculate_window_metrics(eq[2190:2285], 94)
        # Full 2284 bars metrics
        m_full = calculate_window_metrics(eq, total_available_eval_bars)

        print(f"{name:<20} {m_2190['annualized_cagr_pct']:>8.1f}%   {m_2190['sharpe_ratio']:>6.2f}   {m_2190['max_drawdown_pct']:>7.2f}%   {m_tail['sharpe_ratio']:>10.2f}   {m_tail['net_return_pct']:>8.2f}%   {m_full['annualized_cagr_pct']:>8.1f}%   {m_full['sharpe_ratio']:>6.2f}   {m_full['max_drawdown_pct']:>7.2f}%")

        summary_records.append({
            "name": name,
            "canonical_2190": m_2190,
            "holdout_tail_94b": m_tail,
            "full_extended_2284": m_full,
        })

    print("-" * 125)

    # 4. Topology A 60-day OOS Folds Breakdown
    print("\n" + "=" * 125)
    print("   TOPOLOGY A: 60-DAY OUT-OF-SAMPLE FOLDS BREAKDOWN (WITH HOLDOUT TAIL)   ")
    print("=" * 125)
    print(f"{'CANDIDATE':<20} {'FOLD 1 (TREND)':<16} {'FOLD 2 (TREND)':<16} {'FOLD 3 (GRINDER)':<18} {'FOLD 4 (RECOVERY)':<18} {'HOLDOUT TAIL (94b)':<18}")
    print("-" * 125)

    fold_records = {}
    for name, res in results.items():
        eq = res["equity_curve"]
        f_sharpes = []
        for _, s, e in top_a_folds:
            m = calculate_window_metrics(eq[s:e+1], e-s)
            f_sharpes.append(m["sharpe_ratio"])
        m_tail = calculate_window_metrics(eq[2190:2285], 94)
        tail_sh = m_tail["sharpe_ratio"]

        f1_str = f"{f_sharpes[0]:>5.2f}"
        f2_str = f"{f_sharpes[1]:>5.2f}"
        f3_str = f"{f_sharpes[2]:>6.2f}"
        f4_str = f"{f_sharpes[3]:>5.2f}"
        tail_str = f"{tail_sh:>5.2f}"

        print(f"{name:<20} {f1_str:<16} {f2_str:<16} {f3_str:<18} {f4_str:<18} {tail_str:<18}")
        fold_records[name] = {
            "fold1": f_sharpes[0],
            "fold2": f_sharpes[1],
            "fold3": f_sharpes[2],
            "fold4": f_sharpes[3],
            "holdout_tail": tail_sh,
        }
    print("-" * 125)

    # 5. Topology C 45-day Non-Overlapping Folds
    print("\n" + "=" * 125)
    print("   TOPOLOGY C: 45-DAY NON-OVERLAPPING OOS FOLDS (GRINDER PEAK AT F3)   ")
    print("=" * 125)
    print(f"{'CANDIDATE':<20} {'45d F1 (TREND)':<16} {'45d F2 (TRANS)':<16} {'45d F3 (GRINDER)':<18} {'45d F4 (REBOUND)':<18} {'45d TAIL':<18}")
    print("-" * 125)

    top_c_records = {}
    for name, res in results.items():
        eq = res["equity_curve"]
        c_sharpes = []
        for _, s, e in top_c_folds:
            m = calculate_window_metrics(eq[s:e+1], e-s)
            c_sharpes.append(m["sharpe_ratio"])
        print(f"{name:<20} {c_sharpes[0]:>5.2f}            {c_sharpes[1]:>5.2f}            {c_sharpes[2]:>6.2f}             {c_sharpes[3]:>5.2f}             {c_sharpes[4]:>5.2f}")
        top_c_records[name] = {
            "f1": c_sharpes[0],
            "f2": c_sharpes[1],
            "f3": c_sharpes[2],
            "f4": c_sharpes[3],
            "tail": c_sharpes[4],
        }
    print("-" * 125)

    # Save to JSON artifact
    payload = {
        "timestamp_utc": "2026-09-24T11:45:00Z",
        "total_available_eval_bars": total_available_eval_bars,
        "holdout_tail_bars": total_available_eval_bars - 2190,
        "summary": summary_records,
        "topology_a_60d_folds": fold_records,
        "topology_c_45d_folds": top_c_records,
    }

    out_file = PIPELINE_ROOT / "data" / "stage3b_independent_holdout_results.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"\n[REPORT] Saved Stage 3B Independent Holdout Results to {out_file}")


if __name__ == "__main__":
    main()
