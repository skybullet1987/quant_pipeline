#!/usr/bin/env python3
"""
Branch A2: Pure Volatility Targeting (A0 + VT)
==============================================
Tests whether dynamic volatility scaling compresses portfolio risk and drawdown
WITHOUT altering the underlying momentum signal or expanding leverage.

Causal Standard:
- Realized portfolio volatility estimated strictly at bar t close using backward-looking returns.
- Bounded scalar: w_i(t+1) = w_i_base * clip(sigma_target / sigma_realized(t), lambda_min, lambda_max)
- Strict Risk Reduction: lambda_min = 0.25, lambda_max = 1.00 (Zero leverage expansion!).
- Hard Gross Leverage Ceiling: sum |w_i| <= 3.0x unconditionally.
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


def main():
    print("=" * 115)
    print("      BRANCH A2: PURE VOLATILITY TARGETING SWEEP (λ ∈ [0.25, 1.00])      ")
    print("=" * 115)

    loader = InstitutionalCompoundingEngine()
    print("--> Loading canonical data lake...")
    _, _, cached_data = loader.load_and_preprocess_data()

    vol_targets = [0.30, 0.40, 0.50, 0.60]
    lookback_days_list = [20, 40]

    results = []
    total_runs = len(vol_targets) * len(lookback_days_list)
    print(f"\nEvaluating {total_runs} configurations (Pure risk-reduction clamp: λ <= 1.00)...\n")

    t_start = time.time()
    for lb_days in lookback_days_list:
        lb_bars = lb_days * 6
        for vt in vol_targets:
            t0 = time.time()
            print(f"--> [A2 Sweep] VolTarget={vt*100:.0f}% | Lookback={lb_days}d ...", end=" ", flush=True)
            engine = InstitutionalCompoundingEngine(
                fixed_leverage=3.0,
                turnover_lambda=0.85,
                two_tranche_enabled=False,
                pyramid_ratio=0.0,
                volatility_target=vt,
                vol_lookback_bars=lb_bars,
                vol_lambda_min=0.25,
                vol_lambda_max=1.00,
            )
            res = engine.run(cached_data)
            elapsed = time.time() - t0
            eq = res["ending_equity"]
            mult = eq / 10000.0
            sharpe = res["sharpe"]
            mdd = res["max_drawdown"]
            calmar = res["calmar"]
            cagr = res["net_cagr"]

            print(f"Done in {elapsed:.1f}s | Equity: ${eq:,.2f} ({mult:.2f}x) | Sharpe: {sharpe:.2f} | MDD: {mdd:.2f}% | Calmar: {calmar:.2f}")

            results.append({
                "target_vol": vt,
                "lookback_days": lb_days,
                "ending_equity": eq,
                "equity_multiple": mult,
                "cagr_pct": cagr,
                "sharpe": sharpe,
                "sortino": res["sortino"],
                "calmar": calmar,
                "max_drawdown_pct": mdd,
                "total_turnover": res["total_turnover_nav"],
                "total_fees": res["cost_breakdown"]["maker_fees_usd"] + res["cost_breakdown"]["taker_fees_usd"],
                "market_impact": res["cost_breakdown"]["market_impact_usd"],
                "funding_pnl": res["cost_breakdown"]["funding_pnl_usd"],
                "total_friction": res["cost_breakdown"]["total_execution_friction_usd"],
            })

    print(f"\nAll A2 runs completed in {time.time() - t_start:.1f}s.")

    # Sort results by Calmar ratio descending
    sorted_res = sorted(results, key=lambda x: x["calmar"], reverse=True)

    print("\n" + "=" * 115)
    print(f"{'VOL TGT':<10} {'LOOKBACK':<10} {'ENDING EQ':<14} {'MULT':<8} {'CAGR':<10} {'SHARPE':<8} {'MDD':<8} {'CALMAR':<8} {'TURNOVER':<10}")
    print("=" * 115)
    for r in sorted_res:
        print(f"{r['target_vol']*100:<9.0f}% {r['lookback_days']:<9}d ${r['ending_equity']:<13,.2f} {r['equity_multiple']:<7.2f}x {r['cagr_pct']:<9.2f}% {r['sharpe']:<7.2f} {r['max_drawdown_pct']:<7.2f}% {r['calmar']:<7.2f} {r['total_turnover']:<10.2f}")
    print("=" * 115)

    # Save to JSON
    out_path = PIPELINE_ROOT / "data" / "branch_a2_volatility_targeting_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(sorted_res, f, indent=2)
    print(f"\nWrote full A2 results to {out_path}\n")


if __name__ == "__main__":
    main()
