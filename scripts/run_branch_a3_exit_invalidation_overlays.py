#!/usr/bin/env python3
"""
Branch A3: Close-Triggered Invalidation Exits (A0 + Exits)
=========================================================
Tests explicit adverse-trend invalidation rules evaluated strictly at bar t close,
updating trailing stop thresholds for subsequent bar execution with standard friction.

Pre-registered Rules (No in-flight optimization):
1. ATR Ratchet: K * ATR trailing peak price (K in [2.0, 3.0, 4.0])
2. Dynamic Efficiency-Weighted Chandelier Ratchet (K * (1 + KER))
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
    print("      BRANCH A3: CLOSE-TRIGGERED INVALIDATION EXITS SWEEP (A0 + ATR RATCHET)      ")
    print("=" * 115)

    loader = InstitutionalCompoundingEngine()
    print("--> Loading canonical data lake...")
    _, _, cached_data = loader.load_and_preprocess_data()

    configs = [
        {"name": "A0_Baseline_NoRatchet",   "k": 0.0, "dynamic": False},
        {"name": "ATR_Ratchet_K2.0_Fixed",  "k": 2.0, "dynamic": False},
        {"name": "ATR_Ratchet_K3.0_Fixed",  "k": 3.0, "dynamic": False},
        {"name": "ATR_Ratchet_K4.0_Fixed",  "k": 4.0, "dynamic": False},
        {"name": "ATR_Ratchet_K3.0_Dynamic","k": 3.0, "dynamic": True},
        {"name": "ATR_Ratchet_K4.0_Dynamic","k": 4.0, "dynamic": True},
    ]

    results = []
    print(f"\nEvaluating {len(configs)} configurations under strict causal execution...\n")

    t_start = time.time()
    for cfg in configs:
        t0 = time.time()
        print(f"--> [A3 Sweep] Running {cfg['name']} ...", end=" ", flush=True)
        engine = InstitutionalCompoundingEngine(
            fixed_leverage=3.0,
            turnover_lambda=0.85,
            two_tranche_enabled=False,
            pyramid_ratio=0.0,
            chandelier_k=cfg["k"],
            dynamic_chandelier=cfg["dynamic"],
        )
        res = engine.run(cached_data)
        elapsed = time.time() - t0
        eq = res["ending_equity"]
        mult = eq / 10000.0
        cagr = res["net_cagr"]
        sharpe = res["sharpe"]
        mdd = res["max_drawdown"]
        calmar = res["calmar"]

        print(f"Done in {elapsed:.1f}s | Equity: ${eq:,.2f} ({mult:.2f}x) | Sharpe: {sharpe:.2f} | MDD: {mdd:.2f}% | Calmar: {calmar:.2f}")

        cb = res["cost_breakdown"]
        results.append({
            "name": cfg["name"],
            "k_val": cfg["k"],
            "dynamic": cfg["dynamic"],
            "ending_equity": eq,
            "equity_multiple": mult,
            "cagr_pct": cagr,
            "sharpe": sharpe,
            "sortino": res["sortino"],
            "calmar": calmar,
            "max_drawdown_pct": mdd,
            "total_turnover": res["total_turnover_nav"],
            "total_fees": cb["maker_fees_usd"] + cb["taker_fees_usd"],
            "market_impact": cb["market_impact_usd"],
            "funding_pnl": cb["funding_pnl_usd"],
            "total_friction": cb["total_execution_friction_usd"],
        })

    print(f"\nAll A3 runs completed in {time.time() - t_start:.1f}s.")

    # Sort results by Calmar descending
    sorted_res = sorted(results, key=lambda x: x["calmar"], reverse=True)

    print("\n" + "=" * 115)
    print(f"{'CONFIG NAME':<28} {'ENDING EQ':<13} {'MULT':<8} {'CAGR':<10} {'SHARPE':<8} {'MDD':<8} {'CALMAR':<8} {'TURNOVER':<10}")
    print("=" * 115)
    for r in sorted_res:
        print(f"{r['name']:<28} ${r['ending_equity']:<12,.2f} {r['equity_multiple']:<7.2f}x {r['cagr_pct']:<9.2f}% {r['sharpe']:<7.2f} {r['max_drawdown_pct']:<7.2f}% {r['calmar']:<7.2f} {r['total_turnover']:<10.2f}")
    print("=" * 115)

    out_path = PIPELINE_ROOT / "data" / "branch_a3_exit_invalidation_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(sorted_res, f, indent=2)
    print(f"\nWrote full A3 results to {out_path}\n")


if __name__ == "__main__":
    main()
