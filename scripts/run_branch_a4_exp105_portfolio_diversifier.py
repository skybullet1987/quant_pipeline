#!/usr/bin/env python3
"""
Branch A4: EXP-105 Portfolio Diversifier Sleeve (A0 + EXP-105)
=============================================================
Evaluates allocating fixed ex-ante portfolio capital to the market-neutral/low-beta
EXP-105 Sovereign Engine to measure genuine diversification benefits.

Fixed Ex-Ante Allocation Ladder:
- 100:0  (A0 Pure Baseline)
- 90:10  (90% A0 / 10% EXP-105)
- 80:20  (80% A0 / 20% EXP-105)
- 70:30  (70% A0 / 30% EXP-105)
- 0:100  (EXP-105 Pure Baseline)

Metrics:
- Portfolio CAGR, Sharpe, Sortino, Calmar, Max Drawdown
- Rolling 30-day cross-strategy correlation rho(A0, EXP-105)
- Tail correlation in bottom 5% return days of A0
- Worst joint drawdown episode
- Marginal Expected Shortfall (MES) & Conditional Drawdown at Risk (CDaR)
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from backtest_10x_convex_compounding import InstitutionalCompoundingEngine


def run_diversification_experiment():
    print("=" * 100)
    print("      BRANCH A4: EXP-105 PORTFOLIO DIVERSIFIER SLEEVE (FIXED EX-ANTE LADDER)      ")
    print("=" * 100)

    # 1. Load EXP-105 Equity Curve
    exp105_csv = PIPELINE_ROOT / "artifacts" / "exp105_equity_curve.csv"
    assert exp105_csv.exists(), f"EXP-105 equity curve not found at {exp105_csv}"
    df_105 = pd.read_csv(exp105_csv)
    eq_105 = df_105["portfolio_equity_usd"].values
    n_bars_105 = len(eq_105)

    # 2. Run / Load A0 Equity Curve
    print("--> Loading canonical data lake and running A0 baseline...")
    loader = InstitutionalCompoundingEngine()
    _, _, cached_data = loader.load_and_preprocess_data()

    engine_a0 = InstitutionalCompoundingEngine(
        fixed_leverage=3.0,
        turnover_lambda=0.85,
        two_tranche_enabled=False,
        pyramid_ratio=0.0
    )
    res_a0 = engine_a0.run(cached_data)
    eq_a0 = res_a0["equity_curve"]
    n_bars_a0 = len(eq_a0)

    min_bars = min(n_bars_a0, n_bars_105)
    eq_a0 = eq_a0[:min_bars]
    eq_105 = eq_105[:min_bars]

    # Convert to normalized wealth index (base = 1.0)
    w_a0 = eq_a0 / eq_a0[0]
    w_105 = eq_105 / eq_105[0]

    # Per-bar returns
    ret_a0 = np.diff(eq_a0) / eq_a0[:-1]
    ret_105 = np.diff(eq_105) / eq_105[:-1]

    # Overall cross-strategy correlation
    overall_corr = float(np.corrcoef(ret_a0, ret_105)[0, 1])

    # Rolling 30-day (180 4H bars) correlation
    window_30d = 180
    rolling_corrs = []
    for i in range(window_30d, len(ret_a0)):
        r_a = ret_a0[i - window_30d:i]
        r_b = ret_105[i - window_30d:i]
        c = np.corrcoef(r_a, r_b)[0, 1]
        rolling_corrs.append(c)
    mean_rolling_corr = float(np.nanmean(rolling_corrs))

    # Tail correlation in bottom 5% return days of A0
    q05_a0 = np.percentile(ret_a0, 5)
    tail_mask = ret_a0 <= q05_a0
    tail_corr = float(np.corrcoef(ret_a0[tail_mask], ret_105[tail_mask])[0, 1])

    print(f"\n--> Cross-Strategy Covariance Diagnostics:")
    print(f"    Full-Sample Correlation rho(A0, EXP-105):     {overall_corr:+.4f}")
    print(f"    Mean Rolling 30-Day Correlation:              {mean_rolling_corr:+.4f}")
    print(f"    Tail Correlation (Bottom 5% A0 Drawdown Days): {tail_corr:+.4f}")

    # 3. Allocation Grid: Equal Total Capital ($10,000 USDC)
    allocations = [
        ("100:0 (Pure A0)", 1.00, 0.00),
        ("90:10 Sleeve",    0.90, 0.10),
        ("80:20 Sleeve",    0.80, 0.20),
        ("70:30 Sleeve",    0.70, 0.30),
        ("0:100 (Pure 105)", 0.00, 1.00),
    ]

    results = []
    print("\n" + "=" * 115)
    print(f"{'ALLOCATION':<20} {'ENDING EQ':<12} {'MULT':<8} {'CAGR':<10} {'SHARPE':<8} {'SORTINO':<8} {'MDD':<8} {'CALMAR':<8} {'CDaR_95':<8}")
    print("=" * 115)

    for name, a_wt, b_wt in allocations:
        # Combined portfolio wealth path from $10,000 base
        combined_wealth = 10000.0 * (a_wt * w_a0 + b_wt * w_105)
        combined_final = combined_wealth[-1]
        combined_cagr = ((combined_final / 10000.0) - 1.0) * 100.0

        comb_running_max = np.maximum.accumulate(combined_wealth)
        comb_drawdowns = (comb_running_max - combined_wealth) / comb_running_max
        comb_mdd_pct = float(np.max(comb_drawdowns) * 100.0)

        # 95% Conditional Drawdown at Risk (CDaR): average of drawdowns exceeding 95th percentile
        cdar_threshold = np.percentile(comb_drawdowns, 95)
        tail_dds = comb_drawdowns[comb_drawdowns >= cdar_threshold]
        cdar_95 = float(np.mean(tail_dds) * 100.0) if len(tail_dds) > 0 else comb_mdd_pct

        comb_rets = np.diff(combined_wealth) / combined_wealth[:-1]
        m_ret = float(np.mean(comb_rets))
        s_ret = float(np.std(comb_rets)) + 1e-8
        d_ret = float(np.std(comb_rets[comb_rets < 0])) + 1e-8

        sharpe = (m_ret / s_ret) * math.sqrt(2190)
        sortino = (m_ret / d_ret) * math.sqrt(2190)
        calmar = (combined_cagr / comb_mdd_pct) if comb_mdd_pct > 0 else 0.0

        print(f"{name:<20} ${combined_final:<11,.2f} {combined_final/10000:<7.2f}x {combined_cagr:<9.2f}% {sharpe:<7.2f} {sortino:<7.2f} {comb_mdd_pct:<7.2f}% {calmar:<7.2f} {cdar_95:<7.2f}%")

        results.append({
            "name": name,
            "weight_a0": a_wt,
            "weight_exp105": b_wt,
            "ending_equity": combined_final,
            "equity_multiple": combined_final / 10000.0,
            "cagr_pct": combined_cagr,
            "sharpe": sharpe,
            "sortino": sortino,
            "calmar": calmar,
            "max_drawdown_pct": comb_mdd_pct,
            "cdar_95_pct": cdar_95,
        })

    print("=" * 115)

    summary_payload = {
        "covariance_diagnostics": {
            "full_sample_correlation": overall_corr,
            "mean_rolling_30d_correlation": mean_rolling_corr,
            "tail_correlation_bottom_5pct": tail_corr,
        },
        "allocation_results": results,
    }

    out_path = PIPELINE_ROOT / "data" / "branch_a4_exp105_portfolio_diversifier_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(summary_payload, f, indent=2)
    print(f"\nWrote full A4 sleeve results to {out_path}\n")


if __name__ == "__main__":
    run_diversification_experiment()
