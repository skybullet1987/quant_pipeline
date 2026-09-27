#!/usr/bin/env python3
"""
TOURNAMENT RD-ACE-X: CONDITIONAL CONVEXITY & 10x FRONTIER EXPLORATION
====================================================================
Systematic Tournament Suite testing:
  - Tournament F: Regime Leverage Mapping (Expansion Scaling)
  - Tournament G: Conviction-Scaled Dynamic Leverage (Alpha Dispersion)
  - Tournament H: Tranche Tail Harvesting Optimization (2-Tranche vs 3-Tranche)
  - Tournament J: High-Conviction Convex Overlay with 3.5% DD Auto-Kill Switch
  - Tournament K: Combined Asymmetric Convexity ($10k & $1k Accounts)

All runs strictly enforced with:
  1. Invariant Auditing: Causal timestamp assertion (regime_ts < exec_ts)
  2. Zero Lookahead: t-1 decision, t execution
  3. Exact Incremental Accounting: Accounting Discrepancy == $0.000000
  4. Hard Survival Constraint: Max DD <= 30.0%
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Any

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from backtest_10x_convex_compounding import InstitutionalCompoundingEngine

def format_row(cols, widths):
    out = []
    for c, w in zip(cols, widths):
        s = str(c)
        if len(s) > w:
            s = s[:w]
        out.append(s.ljust(w))
    return " | ".join(out)

def print_separator(widths):
    print("-+-".join("-" * w for w in widths))

def run_suite():
    print("=" * 115)
    print("   TOURNAMENT RD-ACE-X: CONDITIONAL CONVEXITY & MULTI-FOLD COMPOUNDING BAKE-OFF   ")
    print("=" * 115)
    t0 = time.time()

    # Preload and cache market data once
    print("\n--> [1/6] Preloading & Seasoning Market Data Lake (116 symbols, 2190 4H bars)...")
    base_engine = InstitutionalCompoundingEngine()
    _, _, cached_data = base_engine.load_and_preprocess_data()
    print(f"    Data ready in {time.time() - t0:.2f}s.")

    results_all: Dict[str, Any] = {}

    widths = [26, 12, 12, 10, 10, 10, 14, 12]
    header = ["Variant", "End Equity", "CAGR (%)", "Sharpe", "Sortino", "Max DD", "Discrepancy", "DD Check"]

    def run_variant(name: str, **kwargs) -> Dict:
        eng = InstitutionalCompoundingEngine(**kwargs)
        res = eng.run(cached_market_data=cached_data)
        dd_ok = "PASS (<=30%)" if res["max_drawdown_pct"] <= 30.05 else "FAIL (>30%)"
        row = [
            name,
            f"${res['end_equity']:,.2f}",
            f"{res['cagr_pct']:+.2f}%",
            f"{res['sharpe_ratio']:.2f}",
            f"{res['sortino_ratio']:.2f}",
            f"{res['max_drawdown_pct']:.2f}%",
            f"${res['accounting_discrepancy_usd']:.6f}",
            dd_ok,
        ]
        print(format_row(row, widths), flush=True)
        results_all[name] = {
            "end_equity": res["end_equity"],
            "cagr_pct": res["cagr_pct"],
            "sharpe": res["sharpe_ratio"],
            "sortino": res["sortino_ratio"],
            "max_dd_pct": res["max_drawdown_pct"],
            "calmar": res["calmar_ratio"],
            "win_rate": res["win_rate_pct"],
            "profit_factor": res["profit_factor"],
            "total_trades": res["total_trades"],
            "discrepancy": res["accounting_discrepancy_usd"],
            "passed_dd_constraint": res["max_drawdown_pct"] <= 30.05,
            "params": kwargs,
        }
        return res

    # --------------------------------------------------------------------------
    # TOURNAMENT F: Regime Leverage Mapping (Expansion Leverage)
    # --------------------------------------------------------------------------
    print("\n" + "=" * 115)
    print("   TOURNAMENT F: REGIME LEVERAGE MAPPING (EXPANSION SCALING)   ")
    print("   Baseline: Shock=0x, Recovery=0.75x, Chop=0.50x, 2-Tranche 50/50 @ 2 ATR   ")
    print("=" * 115)
    print(format_row(header, widths))
    print_separator(widths)

    expansion_candidates = [
        ("F1: Lev Exp 1.25x", 1.25),
        ("F2: Lev Exp 1.50x (RD-C)", 1.50),
        ("F3: Lev Exp 1.75x", 1.75),
        ("F4: Lev Exp 2.00x", 2.00),
        ("F5: Lev Exp 2.50x", 2.50),
    ]

    for label, lev in expansion_candidates:
        run_variant(
            label,
            rd_ace_mode=True,
            lev_shock=0.0,
            lev_recovery=0.75,
            lev_chop=0.50,
            lev_expansion=lev,
            two_tranche_enabled=True,
            trailing_runner_enabled=False,
            harvest_ratio_a=0.50,
            harvest_target_atr=2.0,
            turnover_lambda=0.50,
            initial_capital=10000.0,
        )

    # --------------------------------------------------------------------------
    # TOURNAMENT G: Conviction-Scaled Dynamic Leverage
    # --------------------------------------------------------------------------
    print("\n" + "=" * 115)
    print("   TOURNAMENT G: CONVICTION-SCALED DYNAMIC LEVERAGE (ALPHA DISPERSION)   ")
    print("   Modulates Expansion Leverage by Cross-Sectional Dispersion Percentile   ")
    print("=" * 115)
    print(format_row(header, widths))
    print_separator(widths)

    conviction_candidates = [
        ("G1: Static 1.50x (RD-C)", False, 1.50),
        ("G2: Conviction 1.50x Base", True, 1.50),
        ("G3: Conviction 1.75x Base", True, 1.75),
        ("G4: Conviction 2.00x Base", True, 2.00),
    ]

    for label, conv_on, lev in conviction_candidates:
        run_variant(
            label,
            rd_ace_mode=True,
            lev_shock=0.0,
            lev_recovery=0.75,
            lev_chop=0.50,
            lev_expansion=lev,
            conviction_leverage_enabled=conv_on,
            two_tranche_enabled=True,
            trailing_runner_enabled=False,
            harvest_ratio_a=0.50,
            harvest_target_atr=2.0,
            turnover_lambda=0.50,
            initial_capital=10000.0,
        )

    # --------------------------------------------------------------------------
    # TOURNAMENT H: Tranche Tail Harvesting Optimization
    # --------------------------------------------------------------------------
    print("\n" + "=" * 115)
    print("   TOURNAMENT H: TRANCHE TAIL HARVESTING OPTIMIZATION   ")
    print("   Testing 2-Tranche vs 3-Tranche Tail Runners to Capture Right-Tail Excursions   ")
    print("=" * 115)
    print(format_row(header, widths))
    print_separator(widths)

    harvest_configs = [
        ("H1: 50% @ 2.0 ATR, 50% Run (RD-C)", 0.50, 2.0, 0.00, 0.0),
        ("H2: 33% @ 2.0 ATR, 67% Run", 0.33, 2.0, 0.00, 0.0),
        ("H3: 25% @ 2.0, 25% @ 3.5, 50% Run", 0.25, 2.0, 0.25, 3.5),
        ("H4: 20% @ 2.0, 30% @ 4.0, 50% Run", 0.20, 2.0, 0.30, 4.0),
        ("H5: 33% @ 2.5 ATR, 67% Run", 0.33, 2.5, 0.00, 0.0),
    ]

    for label, r_a, atr_a, r_b, atr_b in harvest_configs:
        run_variant(
            label,
            rd_ace_mode=True,
            lev_shock=0.0,
            lev_recovery=0.75,
            lev_chop=0.50,
            lev_expansion=1.50,
            two_tranche_enabled=True,
            trailing_runner_enabled=False,
            harvest_ratio_a=r_a,
            harvest_target_atr=atr_a,
            harvest_ratio_b=r_b,
            harvest_target_atr_b=atr_b,
            turnover_lambda=0.50,
            initial_capital=10000.0,
        )

    # --------------------------------------------------------------------------
    # TOURNAMENT J: Convex Overlay Engine + 3.5% DD Auto-Kill Switch
    # --------------------------------------------------------------------------
    print("\n" + "=" * 115)
    print("   TOURNAMENT J: CONVEX OVERLAY WITH 3.5% DRAWDOWN AUTO-KILL SWITCH   ")
    print("   Base Expansion 1.0x + Overlay in Top 15% Dispersion with Rapid Pull-Back Cut   ")
    print("=" * 115)
    print(format_row(header, widths))
    print_separator(widths)

    overlay_configs = [
        ("J1: No Overlay (Base 1.0x)", False, 1.00, 0.0, 0.035),
        ("J2: Base 1.0x + Overlay 0.50x", True, 1.00, 0.50, 0.035),
        ("J3: Base 1.0x + Overlay 0.75x", True, 1.00, 0.75, 0.035),
        ("J4: Base 1.0x + Overlay 1.00x", True, 1.00, 1.00, 0.035),
        ("J5: Base 1.25x + Overlay 0.75x", True, 1.25, 0.75, 0.035),
    ]

    for label, ov_on, base_lev, ov_lev, kill_dd in overlay_configs:
        run_variant(
            label,
            rd_ace_mode=True,
            lev_shock=0.0,
            lev_recovery=0.75,
            lev_chop=0.50,
            lev_expansion=base_lev,
            convex_overlay_enabled=ov_on,
            overlay_leverage=ov_lev,
            overlay_dd_kill_switch=kill_dd,
            two_tranche_enabled=True,
            trailing_runner_enabled=False,
            harvest_ratio_a=0.50,
            harvest_target_atr=2.0,
            turnover_lambda=0.50,
            initial_capital=10000.0,
        )

    # --------------------------------------------------------------------------
    # TOURNAMENT K: Combined Multi-Sleeve Pareto Frontiers ($10k & $1k Floors)
    # --------------------------------------------------------------------------
    print("\n" + "=" * 115)
    print("   TOURNAMENT K: COMBINED ASYMMETRIC CONVEXITY (PARETO FRONTIER SEARCH)   ")
    print("   Testing Combined Tranche + Conviction / Overlay under $10,000 & $1,000 Capitals   ")
    print("=" * 115)
    print(format_row(header, widths))
    print_separator(widths)

    combined_candidates = [
        # Baseline
        ("K1: RD-ACE-C Baseline ($10k)", {
            "initial_capital": 10000.0, "min_order_notional": 0.0,
            "lev_expansion": 1.50, "harvest_ratio_a": 0.50, "harvest_target_atr": 2.0,
            "harvest_ratio_b": 0.0, "harvest_target_atr_b": 0.0,
            "conviction_leverage_enabled": False, "convex_overlay_enabled": False,
        }),
        # 3-Tranche Runner + Conviction
        ("K2: 3-Tranche + Conv 1.5x ($10k)", {
            "initial_capital": 10000.0, "min_order_notional": 0.0,
            "lev_expansion": 1.50, "harvest_ratio_a": 0.25, "harvest_target_atr": 2.0,
            "harvest_ratio_b": 0.25, "harvest_target_atr_b": 3.5,
            "conviction_leverage_enabled": True, "convex_overlay_enabled": False,
        }),
        # 3-Tranche Runner + Overlay
        ("K3: 3-Tranche + Overlay 0.75x ($10k)", {
            "initial_capital": 10000.0, "min_order_notional": 0.0,
            "lev_expansion": 1.00, "harvest_ratio_a": 0.25, "harvest_target_atr": 2.0,
            "harvest_ratio_b": 0.25, "harvest_target_atr_b": 3.5,
            "convex_overlay_enabled": True, "overlay_leverage": 0.75,
        }),
        # $1k Account Baseline with $10 Floor
        ("K4: RD-ACE-C Floor ($1k, $10 Min)", {
            "initial_capital": 1000.0, "min_order_notional": 10.0,
            "lev_expansion": 1.50, "harvest_ratio_a": 0.50, "harvest_target_atr": 2.0,
            "harvest_ratio_b": 0.0, "harvest_target_atr_b": 0.0,
            "conviction_leverage_enabled": False, "convex_overlay_enabled": False,
        }),
        # $1k Account 3-Tranche + Conviction
        ("K5: 3-Tranche + Conv ($1k, $10 Min)", {
            "initial_capital": 1000.0, "min_order_notional": 10.0,
            "lev_expansion": 1.50, "harvest_ratio_a": 0.25, "harvest_target_atr": 2.0,
            "harvest_ratio_b": 0.25, "harvest_target_atr_b": 3.5,
            "conviction_leverage_enabled": True, "convex_overlay_enabled": False,
        }),
        # $1k Account 3-Tranche + Overlay
        ("K6: 3-Tranche + Overlay ($1k, $10 Min)", {
            "initial_capital": 1000.0, "min_order_notional": 10.0,
            "lev_expansion": 1.00, "harvest_ratio_a": 0.25, "harvest_target_atr": 2.0,
            "harvest_ratio_b": 0.25, "harvest_target_atr_b": 3.5,
            "convex_overlay_enabled": True, "overlay_leverage": 0.75,
        }),
    ]

    for label, p in combined_candidates:
        run_variant(
            label,
            rd_ace_mode=True,
            lev_shock=0.0,
            lev_recovery=0.75,
            lev_chop=0.50,
            lev_expansion=p.get("lev_expansion", 1.50),
            two_tranche_enabled=True,
            trailing_runner_enabled=False,
            harvest_ratio_a=p.get("harvest_ratio_a", 0.50),
            harvest_target_atr=p.get("harvest_target_atr", 2.0),
            harvest_ratio_b=p.get("harvest_ratio_b", 0.0),
            harvest_target_atr_b=p.get("harvest_target_atr_b", 0.0),
            conviction_leverage_enabled=p.get("conviction_leverage_enabled", False),
            convex_overlay_enabled=p.get("convex_overlay_enabled", False),
            overlay_leverage=p.get("overlay_leverage", 1.0),
            overlay_dd_kill_switch=0.035,
            turnover_lambda=0.50,
            initial_capital=p.get("initial_capital", 10000.0),
            min_order_notional=p.get("min_order_notional", 0.0),
        )

    # Save results to artifacts
    out_path = PIPELINE_ROOT / "artifacts" / "rd_ace_x_tournament_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    def json_serialize_helper(obj):
        if isinstance(obj, (np.bool_, bool)):
            return bool(obj)
        if isinstance(obj, (np.integer, int)):
            return int(obj)
        if isinstance(obj, (np.floating, float)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return str(obj)

    with open(out_path, "w") as f:
        json.dump(results_all, f, indent=2, default=json_serialize_helper)
    print(f"\n--> All tournament results saved to {out_path}", flush=True)
    print(f"--> Total Execution Time: {time.time() - t0:.2f}s")

if __name__ == "__main__":
    run_suite()
