#!/usr/bin/env python3
"""
Institutional 10x Convex Compounding Benchmark Suite
Runs the full institutional compounding engine under exact mark-to-market accounting.
"""

import math
import sys
from pathlib import Path
import numpy as np

PIPELINE_ROOT = Path(__file__).resolve().parents[1]
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from backtest_10x_convex_compounding import InstitutionalCompoundingEngine

def main():
    print("=" * 90)
    print("   INSTITUTIONAL 10X+ CONVEX COMPOUNDING BENCHMARK SUITE")
    print("   Execution Physics: IronCore v2.4.0 E3 Causal Standard")
    print("=" * 90)

    print("\n--> [1/3] Loading and Preprocessing Point-in-Time 4H Data Lake...")
    _, _, cached_data = InstitutionalCompoundingEngine().load_and_preprocess_data()
    print("    Data Lake preprocessed successfully.")

    # Sweep operational leverage and architectures
    configs = [
        ("1. Unlevered Baseline (1.0x)", {"fixed_leverage": 1.0, "turnover_lambda": 0.85}),
        ("2. Compounding Intermediate (2.0x)", {"fixed_leverage": 2.0, "turnover_lambda": 0.85}),
        ("3. High-Convexity Compounding (2.5x)", {"fixed_leverage": 2.5, "turnover_lambda": 0.85}),
        ("4. 10x Target Gearing (3.0x)", {"fixed_leverage": 3.0, "turnover_lambda": 0.85}),
        ("5. RD-ACE-C Baseline (1.5x Expansion, Two-Tranche)", {
            "rd_ace_mode": True, "lev_shock": 0.0, "lev_recovery": 0.75, "lev_chop": 0.50,
            "lev_expansion": 1.50, "turnover_lambda": 0.85, "two_tranche_enabled": True
        }),
        ("6. RD-ACE-C High Expansion (2.75x Expansion, Two-Tranche)", {
            "rd_ace_mode": True, "lev_shock": 0.0, "lev_recovery": 0.75, "lev_chop": 0.50,
            "lev_expansion": 2.75, "turnover_lambda": 0.85, "two_tranche_enabled": True
        }),
        ("7. Mode D Adaptive Cushion Governor", {
            "mode_layer": "D", "turnover_lambda": 0.85, "two_tranche_enabled": True, "trailing_runner_enabled": True
        }),
    ]

    results = []
    for label, kwargs in configs:
        print(f"\n--> Running: {label}...")
        r = InstitutionalCompoundingEngine(**kwargs).run(cached_data)
        results.append((label, r))
        mult = r["ending_equity"] / 10000.0
        print(f"    Ending Equity: ${r['ending_equity']:,.2f} ({mult:.2f}x)")
        print(f"    CAGR: {r['net_cagr']:+.2f}%, Sharpe: {r['sharpe']:.2f}, MDD: {r['max_drawdown']:.2f}%, Calmar: {r['calmar']:.2f}")
        print(f"    Accounting Discrepancy: ${r['accounting_discrepancy_usd']:.12f}")

    print("\n" + "=" * 110)
    print(f"{'Configuration':<55} | {'Ending Equity':<12} | {'Mult':<6} | {'CAGR':<9} | {'Sharpe':<6} | {'MDD':<6} | {'Calmar':<6} | {'Discrepancy'}")
    print("-" * 110)
    for label, r in results:
        mult = r["ending_equity"] / 10000.0
        print(f"{label:<55} | ${r['ending_equity']:>10.2f} | {mult:>5.2f}x | {r['net_cagr']:>+8.2f}% | {r['sharpe']:>6.2f} | {r['max_drawdown']:>5.2f}% | {r['calmar']:>6.2f} | ${r['accounting_discrepancy_usd']:.10f}")
    print("=" * 110)

if __name__ == "__main__":
    main()
