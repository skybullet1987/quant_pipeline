#!/usr/bin/env python3
"""
Branch A1: Causal Pyramiding Ablation Sweep
==========================================
Isolates whether adding exposure to winning positions adds genuine predictive alpha
when execution artifacts are strictly eliminated.

Physics Standard:
- Breakout condition evaluated strictly at bar t close (close_t >= entry + 2.0 * atr_0).
- Execution strictly at bar t+1 open with base slippage, square-root impact, and exchange fees.
- Risk caps enforced against portfolio equity at fill time (max 25% equity per asset).
- Sweep: pyramid_ratio in [0.00, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30].

Evaluation Metrics (No double-counting):
1. Primary: Delta CAGR_net = CAGR_A1 - CAGR_A0
2. Cost Decomposition: Delta Cost = Delta Fees + Delta Impact + Delta Funding
3. Incremental Pyramid Trade Expectancy: E[R_pyr,net] = sum(PnL_pyr,net) / sum(Capital_pyr)
4. Log Wealth Delta: Delta LogWealth = ln(W_A1 / W_A0)
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


def main():
    print("=" * 115)
    print("      BRANCH A1: CAUSAL PYRAMIDING ABLATION SWEEP (Next-Bar Open Standard)      ")
    print("=" * 115)

    loader = InstitutionalCompoundingEngine()
    print("--> Loading canonical data lake...")
    _, _, cached_data = loader.load_and_preprocess_data()

    sweep_ratios = [0.00, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30]
    results = []

    print(f"\nEvaluating {len(sweep_ratios)} configurations under strict t+1 causal execution...\n")

    t_start = time.time()
    for ratio in sweep_ratios:
        t0 = time.time()
        print(f"--> [A1 Sweep] Running pyramid_ratio = {ratio:.2f} ...", end=" ", flush=True)
        engine = InstitutionalCompoundingEngine(
            fixed_leverage=3.0,
            turnover_lambda=0.85,
            two_tranche_enabled=False,
            pyramid_ratio=ratio,
            pyramid_causal_mode="next_bar_open",
            enforce_pyramid_risk_caps=True,
        )
        res = engine.run(cached_data)
        elapsed = time.time() - t0
        print(f"Done in {elapsed:.1f}s | Equity: ${res['ending_equity']:,.2f} ({res['ending_equity']/10000:.2f}x) | Sharpe: {res['sharpe']:.2f} | MDD: {res['max_drawdown']:.2f}% | Calmar: {res['calmar']:.2f}")
        res["pyramid_ratio"] = ratio
        results.append(res)

    print(f"\nAll sweep runs completed in {time.time() - t_start:.1f}s.")

    # Base reference A0 (pyramid_ratio=0.00)
    a0 = results[0]
    a0_equity = a0["ending_equity"]
    a0_cagr = a0["net_cagr"]
    a0_sharpe = a0["sharpe"]
    a0_mdd = a0["max_drawdown"]
    cb_a0 = a0["cost_breakdown"]
    a0_cost = cb_a0["maker_fees_usd"] + cb_a0["taker_fees_usd"] + cb_a0["market_impact_usd"] + cb_a0["base_slippage_usd"] - cb_a0["funding_pnl_usd"]

    print("\n" + "=" * 125)
    print(f"{'RATIO':<8} {'ENDING EQ':<12} {'MULT':<8} {'CAGR':<10} {'SHARPE':<8} {'MDD':<8} {'CALMAR':<8} {'ΔCAGR_net':<11} {'ΔLogWealth':<12} {'E[R_pyr]%':<10} {'PYR COUNT':<10}")
    print("=" * 125)

    summary_rows = []
    for r in results:
        ratio = r["pyramid_ratio"]
        eq = r["ending_equity"]
        mult = eq / 10000.0
        cagr = r["net_cagr"]
        sharpe = r["sharpe"]
        mdd = r["max_drawdown"]
        calmar = r["calmar"]
        cb = r["cost_breakdown"]

        tot_fees = cb["maker_fees_usd"] + cb["taker_fees_usd"]
        tot_impact = cb["market_impact_usd"]
        tot_funding = cb["funding_pnl_usd"]

        delta_cagr = cagr - a0_cagr
        delta_log_w = math.log(eq / a0_equity)
        pyr_alloc = cb.get("pyramid_allocated_capital_usd", 0.0)
        pyr_net_pnl = cb.get("pyramid_net_pnl_usd", 0.0)
        e_pyr = (pyr_net_pnl / pyr_alloc * 100.0) if pyr_alloc > 0 else 0.0
        pyr_count = cb.get("pyramid_count", 0)

        print(f"{ratio:<8.2f} ${eq:<11,.2f} {mult:<7.2f}x {cagr:<9.2f}% {sharpe:<7.2f} {mdd:<7.2f}% {calmar:<7.2f} {delta_cagr:<+10.2f}% {delta_log_w:<+11.4f} {e_pyr:<9.2f}% {pyr_count:<10}")

        summary_rows.append({
            "pyramid_ratio": ratio,
            "ending_equity": eq,
            "equity_multiple": mult,
            "cagr_pct": cagr,
            "sharpe": sharpe,
            "sortino": r["sortino"],
            "calmar": calmar,
            "max_drawdown_pct": mdd,
            "total_turnover": r["total_turnover_nav"],
            "total_fees": tot_fees,
            "market_impact": tot_impact,
            "funding_pnl": tot_funding,
            "delta_cagr_net": delta_cagr,
            "delta_log_wealth": delta_log_w,
            "pyramid_count": pyr_count,
            "pyramid_expectancy_pct": e_pyr,
            "pyramid_allocated_capital": pyr_alloc,
            "pyramid_net_pnl": pyr_net_pnl,
        })

    print("=" * 125)

    # Save summary artifact
    out_path = PIPELINE_ROOT / "data" / "branch_a1_pyramiding_sweep_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(summary_rows, f, indent=2)
    print(f"\nWrote full A1 sweep ledger to {out_path}\n")


if __name__ == "__main__":
    main()
