#!/usr/bin/env python3
"""
Forensic Causality Audit of EXP-103 Baseline
============================================
Evaluates whether EXP-103 (11.36x / $113,596.45) in backtest_10x_convex_compounding.py
was also contaminated by the intra-bar synthetic pyramiding fill bug.
"""

import sys
import time
from pathlib import Path

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from backtest_10x_convex_compounding import InstitutionalCompoundingEngine

def main():
    print("=" * 80)
    print("FORENSIC AUDIT OF EXP-103 BENCHMARK (backtest_10x_convex_compounding.py)")
    print("=" * 80)

    engine_loader = InstitutionalCompoundingEngine()
    print("--> Loading canonical data lake...")
    eval_timestamps, symbols, cached_data = engine_loader.load_and_preprocess_data()

    # Test 1: Original EXP-103 Baseline (pyramid_ratio=0.50 default, two_tranche_enabled=False, fixed_leverage=3.0)
    print("\n--> [Run 1] Evaluating Baseline EXP-103 (pyramid_ratio=0.50 default)...")
    t0 = time.time()
    res_orig = InstitutionalCompoundingEngine(
        fixed_leverage=3.0,
        turnover_lambda=0.85,
        two_tranche_enabled=False,
        pyramid_ratio=0.50,
    ).run(cached_data)
    print(f"--> Done in {time.time()-t0:.1f}s")
    print(f"    Ending Equity: ${res_orig['ending_equity']:,.2f} ({res_orig['ending_equity']/10000:.2f}x)")
    print(f"    Net CAGR:      {res_orig['net_cagr']:+.2f}%")
    print(f"    Sharpe:        {res_orig['sharpe']:.2f}")
    print(f"    Max Drawdown:  {res_orig['max_drawdown']:.2f}%")

    # Test 2: EXP-103 with Zero Pyramiding (pyramid_ratio=0.0)
    print("\n--> [Run 2] Evaluating EXP-103 with ZERO PYRAMIDING (pyramid_ratio=0.0)...")
    t0 = time.time()
    res_noprob = InstitutionalCompoundingEngine(
        fixed_leverage=3.0,
        turnover_lambda=0.85,
        two_tranche_enabled=False,
        pyramid_ratio=0.0,
    ).run(cached_data)
    print(f"--> Done in {time.time()-t0:.1f}s")
    print(f"    Ending Equity: ${res_noprob['ending_equity']:,.2f} ({res_noprob['ending_equity']/10000:.2f}x)")
    print(f"    Net CAGR:      {res_noprob['net_cagr']:+.2f}%")
    print(f"    Sharpe:        {res_noprob['sharpe']:.2f}")
    print(f"    Max Drawdown:  {res_noprob['max_drawdown']:.2f}%")

    # Test 3: Unlevered 1.0x Baseline (pyramid_ratio=0.50 vs 0.0)
    print("\n--> [Run 3] Evaluating Unlevered 1.0x with ZERO PYRAMIDING...")
    res_1x_noprob = InstitutionalCompoundingEngine(
        fixed_leverage=1.0,
        turnover_lambda=0.85,
        two_tranche_enabled=False,
        pyramid_ratio=0.0,
    ).run(cached_data)
    print(f"    Ending Equity: ${res_1x_noprob['ending_equity']:,.2f} ({res_1x_noprob['ending_equity']/10000:.2f}x)")
    print(f"    Max Drawdown:  {res_1x_noprob['max_drawdown']:.2f}%")

    print("\n" + "=" * 80)
    print("EXP-103 AUDIT COMPARISON SUMMARY")
    print("=" * 80)
    print(f"EXP-103 Original (with intra-bar pyramid): ${res_orig['ending_equity']:,.2f} ({res_orig['ending_equity']/10000:.2f}x) | MDD: {res_orig['max_drawdown']:.2f}%")
    print(f"EXP-103 Zero-Pyramiding (clean directional): ${res_noprob['ending_equity']:,.2f} ({res_noprob['ending_equity']/10000:.2f}x) | MDD: {res_noprob['max_drawdown']:.2f}%")
    delta_equity = res_orig['ending_equity'] - res_noprob['ending_equity']
    phantom_pct = (delta_equity / res_orig['ending_equity']) * 100.0
    print(f"Phantom Intra-Bar Pyramiding Contribution:  ${delta_equity:,.2f} ({phantom_pct:.1f}% of total reported return!)")
    print("=" * 80)

if __name__ == "__main__":
    main()
