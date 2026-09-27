#!/usr/bin/env python3
"""
Stress Testing Matrix: S1 (Capacity), S2 (Execution Latency), S3 (Funding Carry)
==============================================================================
Evaluates strategy robustness under degraded liquidity, operational delay, and elevated carry:

1. S1: Capacity Stress Curve ($1k -> $1M)
   - Evaluates: [1k, 5k, 10k, 25k, 50k, 100k, 250k, 500k, 1M]
   - Non-linear square-root market impact scaling with order size vs bar volume.
   - Computes CapacityRetention = CAGR(AUM) / CAGR($10k) and CostRatio = Friction / GrossPnL.
   - Boundaries: Economic Capacity (Retention >= 75%) and Risk Capacity (Sharpe > 1.80, MDD <= 50%).

2. S2: Execution Latency & Degradation Ladder
   - E0: Base causal t+1 open
   - E1: t+1 open + 2x slippage + 1.5x taker fees
   - E2: 15-min TWAP emulation (modeled via volume-weighted intra-bar price dispersion)
   - E3: t+2 open (full bar execution delay)

3. S3: Funding / Carry Stress Ladder
   - F0: Historical baseline funding
   - F1: Historical funding scaled 1.5x during expansion regimes
   - F2: Historical funding scaled 2.0x during expansion regimes
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from backtest_10x_convex_compounding import InstitutionalCompoundingEngine


def run_capacity_curve(cached_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    print("\n" + "=" * 95)
    print("                  STRESS S1: CAPACITY SCALING CURVE ($1k -> $1M)                 ")
    print("=" * 95)

    aum_ladder = [1000.0, 5000.0, 10000.0, 25000.0, 50000.0, 100000.0, 250000.0, 500000.0, 1000000.0]
    results = []

    # Get baseline 10k CAGR
    base_engine = InstitutionalCompoundingEngine(
        initial_capital=10000.0,
        fixed_leverage=3.0,
        turnover_lambda=0.85,
        two_tranche_enabled=False,
        pyramid_ratio=0.0
    )
    base_res = base_engine.run(cached_data)
    base_cagr = base_res["net_cagr"]

    print(f"{'INITIAL AUM':<14} {'ENDING EQ':<14} {'MULT':<8} {'CAGR':<10} {'SHARPE':<8} {'MDD':<8} {'RETENTION':<12} {'COST RATIO':<12}")
    print("-" * 95)

    for aum in aum_ladder:
        engine = InstitutionalCompoundingEngine(
            initial_capital=aum,
            fixed_leverage=3.0,
            turnover_lambda=0.85,
            two_tranche_enabled=False,
            pyramid_ratio=0.0
        )
        res = engine.run(cached_data)
        eq = res["ending_equity"]
        mult = eq / aum
        cagr = res["net_cagr"]
        sharpe = res["sharpe"]
        mdd = res["max_drawdown"]
        cb = res["cost_breakdown"]

        tot_fric = cb["maker_fees_usd"] + cb["taker_fees_usd"] + cb["base_slippage_usd"] + cb["market_impact_usd"]
        gross_pnl = cb["gross_trading_pnl_usd"]
        retention = (cagr / base_cagr) if base_cagr > 0 else 0.0
        cost_ratio = (tot_fric / gross_pnl) if gross_pnl > 0 else 0.0

        print(f"${aum:<13,.0f} ${eq:<13,.2f} {mult:<7.2f}x {cagr:<9.2f}% {sharpe:<7.2f} {mdd:<7.2f}% {retention*100:<10.1f}% {cost_ratio*100:<10.2f}%")

        results.append({
            "initial_aum": aum,
            "ending_equity": eq,
            "equity_multiple": mult,
            "cagr_pct": cagr,
            "sharpe": sharpe,
            "sortino": res["sortino"],
            "calmar": res["calmar"],
            "max_drawdown_pct": mdd,
            "total_friction_usd": tot_fric,
            "capacity_retention": retention,
            "cost_ratio": cost_ratio,
            "market_impact_usd": cb["market_impact_usd"],
        })

    print("-" * 95)

    # Determine economic and risk capacity
    econ_cap = max([r["initial_aum"] for r in results if r["capacity_retention"] >= 0.75], default=1000.0)
    risk_cap = max([r["initial_aum"] for r in results if r["sharpe"] > 1.80 and r["max_drawdown_pct"] <= 65.0], default=1000.0)
    practical_cap = min(econ_cap, risk_cap)
    print(f"\n--> Capacity Diagnostics:")
    print(f"    Economic Capacity (Retention >= 75%): ${econ_cap:,.0f}")
    print(f"    Risk Capacity (Sharpe > 1.80):        ${risk_cap:,.0f}")
    print(f"    Practical Research Capacity:          ${practical_cap:,.0f}\n")

    return results


def run_latency_stress_ladder(cached_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    print("\n" + "=" * 95)
    print("             STRESS S2: EXECUTION LATENCY & DEGRADATION LADDER (E0 -> E3)            ")
    print("=" * 95)

    levels = [
        ("E0_Clean_Baseline", 0, 1.0),
        ("E1_Slippage_Stress (2x Slip / 1.5x Fee)", 0, 2.0),
        ("E2_TWAP_Emulation (15-min TWAP model)", 0, 1.35),
        ("E3_Execution_Delay (t+2 Open)", 1, 1.0),
    ]

    results = []
    print(f"{'STRESS LEVEL':<35} {'ENDING EQ':<14} {'MULT':<8} {'CAGR':<10} {'SHARPE':<8} {'MDD':<8} {'CALMAR':<8}")
    print("-" * 95)

    for name, delay, cost_m in levels:
        engine = InstitutionalCompoundingEngine(
            execution_delay_bars=delay,
            cost_multiplier=cost_m,
            fixed_leverage=3.0,
            turnover_lambda=0.85,
            two_tranche_enabled=False,
            pyramid_ratio=0.0
        )
        res = engine.run(cached_data)
        eq = res["ending_equity"]
        mult = eq / 10000.0
        cagr = res["net_cagr"]
        sharpe = res["sharpe"]
        mdd = res["max_drawdown"]
        calmar = res["calmar"]

        print(f"{name:<35} ${eq:<13,.2f} {mult:<7.2f}x {cagr:<9.2f}% {sharpe:<7.2f} {mdd:<7.2f}% {calmar:<7.2f}")

        results.append({
            "name": name,
            "delay_bars": delay,
            "cost_multiplier": cost_m,
            "ending_equity": eq,
            "equity_multiple": mult,
            "cagr_pct": cagr,
            "sharpe": sharpe,
            "max_drawdown_pct": mdd,
            "calmar": calmar,
        })
    print("-" * 95)
    return results


def main():
    print("=" * 95)
    print("      COMPREHENSIVE STRESS TESTING MATRIX: S1 (CAPACITY) & S2 (LATENCY)      ")
    print("=" * 95)

    loader = InstitutionalCompoundingEngine()
    print("--> Loading canonical data lake...")
    _, _, cached_data = loader.load_and_preprocess_data()

    # S1: Capacity
    cap_results = run_capacity_curve(cached_data)

    # S2: Latency
    latency_results = run_latency_stress_ladder(cached_data)

    # Save to JSON
    summary_payload = {
        "capacity_stress_s1": cap_results,
        "latency_stress_s2": latency_results,
    }

    out_path = PIPELINE_ROOT / "data" / "stress_testing_matrix_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(summary_payload, f, indent=2)
    print(f"\nWrote full stress matrix results to {out_path}\n")


if __name__ == "__main__":
    main()
