#!/usr/bin/env python3
"""
Compounding Runway & Risk Allocator Simulator
=============================================
Institutional capital runway, compounding timeline, and dynamic risk envelope simulator:
  - Compounding equation: Equity(t) = InitialCapital * (1 + CAGR)^(t / 12)
  - Evaluates Milestone Capital Ladder from $10,000 to $100,000+ (10x Apex Goal)
  - Dynamically calculates Allowed Valley Floors under the 52.0% Dual-Envelope Kill Switch
  - Evaluates CAGR sensitivity basins [300% to 540%]
  - Runs Monte Carlo geometric Brownian path simulations calibrated to historical volatility
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

PIPELINE_ROOT = Path(__file__).resolve().parent.parent


def calculate_compounding_milestones(
    initial_capital: float = 10000.0,
    cagr_pct: float = 441.6,
    mdd_buffer_pct: float = 52.0,
) -> pd.DataFrame:
    """
    Computes exact chronological timeline to each milestone multiple under constant CAGR.
    """
    g = cagr_pct / 100.0
    growth_factor = 1.0 + g
    ln_growth = math.log(growth_factor)

    milestones = [
        ("Launch", 1.0),
        ("Milestone 1", 2.0),
        ("Milestone 2", 3.5),
        ("Milestone 3", 5.0),
        ("Milestone 4", 7.5),
        ("Apex Goal", 10.0),
    ]

    records = []
    floor_multiplier = 1.0 - (mdd_buffer_pct / 100.0)

    for label, mult in milestones:
        cap_target = initial_capital * mult
        if mult == 1.0:
            t_years = 0.0
        else:
            t_years = math.log(mult) / ln_growth
        t_months = t_years * 12.0
        t_days = t_years * 365.25

        valley_floor = cap_target * floor_multiplier

        records.append({
            "Milestone": label,
            "Multiple": f"{mult:.1f}x",
            "Capital Target ($)": f"${cap_target:,.2f}",
            "Target Month": f"Month {t_months:.1f}",
            "Target Days": f"{t_days:.0f} days",
            "Allowed Valley Floor (52% HWM)": f"${valley_floor:,.2f}",
            "Max Permissible Dollar Loss": f"${cap_target - valley_floor:,.2f}",
        })

    return pd.DataFrame(records)


def compute_cagr_sensitivity(
    initial_capital: float = 10000.0,
    target_capital: float = 100000.0,
    cagr_grid: Optional[List[float]] = None,
) -> pd.DataFrame:
    """
    Evaluates sensitivity of 10x horizon to CAGR assumptions across [300% to 540%].
    """
    if cagr_grid is None:
        cagr_grid = [300.0, 350.0, 400.0, 441.6, 500.0, 541.7]

    mult = target_capital / initial_capital
    records = []

    for cagr in cagr_grid:
        g = cagr / 100.0
        t_years = math.log(mult) / math.log(1.0 + g)
        t_months = t_years * 12.0
        t_days = t_years * 365.25
        calmar_canon = cagr / 44.77
        calmar_ext = cagr / 48.60

        tag = " (Certified Base)" if abs(cagr - 441.6) < 0.1 else (" (A0 Baseline)" if abs(cagr - 541.7) < 0.1 else "")

        records.append({
            "Annualized CAGR": f"{cagr:.1f}%{tag}",
            "Months to 10x": f"{t_months:.2f} mos",
            "Days to 10x": f"{t_days:.0f} days",
            "Canonical Calmar (MDD=44.8%)": f"{calmar_canon:.2f}",
            "Extended Calmar (MDD=48.6%)": f"{calmar_ext:.2f}",
        })

    return pd.DataFrame(records)


def run_monte_carlo_path_simulation(
    initial_capital: float = 10000.0,
    cagr_pct: float = 441.6,
    annual_vol_pct: float = 70.0,
    n_paths: int = 1000,
    horizon_days: int = 500,
    mdd_kill_switch_pct: float = 52.0,
    deposit_floor_usd: float = 4800.0,
) -> Dict[str, Any]:
    """
    Simulates geometric Brownian compounding paths with realistic volatility
    to quantify path-dependent kill switch probability and 10x attainment.
    """
    np.random.seed(42)
    dt = 1.0 / 365.25
    steps = horizon_days
    mu = math.log(1.0 + cagr_pct / 100.0)
    sigma = annual_vol_pct / 100.0

    hit_10x_count = 0
    kill_switch_breached_count = 0
    terminal_equities = []

    for _ in range(n_paths):
        # Daily returns
        z = np.random.standard_normal(steps)
        drift = (mu - 0.5 * sigma**2) * dt
        diffusion = sigma * math.sqrt(dt) * z
        daily_returns = np.exp(drift + diffusion)
        
        path = np.zeros(steps + 1)
        path[0] = initial_capital
        for s in range(steps):
            path[s + 1] = path[s] * daily_returns[s]

        # Drawdown tracking
        hwm = np.maximum.accumulate(path)
        dd = (hwm - path) / (hwm + 1e-12)

        breached_trailing = np.any(dd > (mdd_kill_switch_pct / 100.0))
        breached_floor = np.any(path < deposit_floor_usd)

        if breached_trailing or breached_floor:
            kill_switch_breached_count += 1

        if np.max(path) >= (initial_capital * 10.0):
            hit_10x_count += 1

        terminal_equities.append(path[-1])

    terminal_equities = np.array(terminal_equities)

    return {
        "n_paths": n_paths,
        "horizon_days": horizon_days,
        "prob_hit_10x_pct": round((hit_10x_count / n_paths) * 100.0, 1),
        "prob_kill_switch_breach_pct": round((kill_switch_breached_count / n_paths) * 100.0, 1),
        "median_terminal_equity": round(float(np.median(terminal_equities)), 2),
        "p10_terminal_equity": round(float(np.percentile(terminal_equities, 10)), 2),
        "p90_terminal_equity": round(float(np.percentile(terminal_equities, 90)), 2),
    }


def main():
    parser = argparse.ArgumentParser(description="Compounding Runway & Risk Allocator Simulator")
    parser.add_argument("--base", type=float, default=10000.0, help="Initial Starting Base (USDC)")
    parser.add_argument("--cagr", type=float, default=441.6, help="Annualized Growth Rate (pct)")
    parser.add_argument("--kill-buffer", type=float, default=52.0, help="Dual-Envelope Kill Switch Buffer (pct)")
    parser.add_argument("--mc-paths", type=int, default=1000, help="Monte Carlo Path Count")
    args = parser.parse_args()

    print("=" * 110)
    print("   COMPOUNDING RUNWAY & DYNAMIC RISK ALLOCATOR SIMULATOR   ")
    print(f"   Architecture Standard: Composite_TV_Rho (v2.5.0) | Starting Base: ${args.base:,.2f} USDC")
    print("=" * 110)

    # 1. Milestone Capital Ladder
    df_ladder = calculate_compounding_milestones(args.base, args.cagr, args.kill_buffer)
    print("\n>>> MILESTONE CAPITAL LADDER ($10,000 -> $100,000+) <<<")
    print("-" * 110)
    print(df_ladder.to_string(index=False))
    print("-" * 110)

    # 2. CAGR Sensitivity Table
    df_sens = compute_cagr_sensitivity(args.base, args.base * 10.0)
    print("\n>>> CAGR SENSITIVITY & COMPOUNDING VELOCITY BASIN <<<")
    print("-" * 110)
    print(df_sens.to_string(index=False))
    print("-" * 110)

    # 3. Monte Carlo Risk & Runway Analysis
    print("\n>>> MONTE CARLO STOCHASTIC PATH SIMULATION (N=1,000 PATHS, 500 DAYS) <<<")
    mc_res = run_monte_carlo_path_simulation(
        initial_capital=args.base,
        cagr_pct=args.cagr,
        annual_vol_pct=72.5,
        n_paths=args.mc_paths,
        horizon_days=498,
        mdd_kill_switch_pct=args.kill_buffer,
        deposit_floor_usd=args.base * (1.0 - args.kill_buffer / 100.0),
    )
    print(f"  • Probability of Touching 10x ($100,000+) within 498 Days: {mc_res['prob_hit_10x_pct']}%")
    print(f"  • Probability of Breaching 52.0% Dual-Envelope Kill Switch:   {mc_res['prob_kill_switch_breach_pct']}%")
    print(f"  • Median Simulated Terminal Equity at Day 498:               ${mc_res['median_terminal_equity']:,.2f}")
    print(f"  • 10th Percentile (Conservative Downside Valley):             ${mc_res['p10_terminal_equity']:,.2f}")
    print(f"  • 90th Percentile (Convex Upside Outlier):                    ${mc_res['p90_terminal_equity']:,.2f}")
    print("=" * 110)


if __name__ == "__main__":
    main()
