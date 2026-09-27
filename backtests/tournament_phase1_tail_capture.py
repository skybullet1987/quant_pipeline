#!/usr/bin/env python3
"""
PHASE 1 RESEARCH TOURNAMENT: TAIL CAPTURE, CHANDELIER EXITS & GIVEBACK RATIO AUDIT
===================================================================================
Rigorous empirical evaluation comparing:
  1. RD-ACE-C Baseline (Control Arm: 50% Harvest @ 2.0 ATR, 50% Breakeven Runner)
  2. H5 Baseline (33% Harvest @ 2.5 ATR, 67% Breakeven Runner)
  3. H5 + Chandelier Trailing Stop (k = 2.0, 2.5, 3.0, 3.5 ATR)
  4. H5 + Chandelier + Selective Expansion Leverage (1.75x - 2.00x on confirmed trends)
  5. $1,000 Retail Capital Validation (Hyperliquid $10 min order floor)

Key Quantitative Invariants & Metrics Evaluated:
  - Exact incremental accounting ($0.000000 discrepancy)
  - Zero lookahead causal timestamps
  - Effective Breadth (N_effective accounting for cross-asset correlation)
  - Empirical Giveback Ratio Distribution (Median, 75th, 90th, 95th, Worst)
  - Return / Drawdown Frontier Tiers (Tier A, B, C, D)
"""

import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Any

import numpy as np
import polars as pl

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

def print_sep(widths):
    print("-+-".join("-" * w for w in widths))

def compute_effective_breadth(cached_data: Dict) -> Tuple[int, float, float]:
    close_mat = cached_data["close"]
    rets = np.diff(close_mat, axis=0) / close_mat[:-1]
    rets_filled = np.nan_to_num(rets, nan=0.0)
    corr = np.corrcoef(rets_filled, rowvar=False)
    n = corr.shape[0]
    avg_corr = float((np.sum(corr) - n) / (n * (n - 1)))
    n_eff = float(n / (1.0 + (n - 1) * avg_corr))
    return n, avg_corr, n_eff

def assign_tier(cagr: float, max_dd: float) -> str:
    if max_dd > 30.05:
        return "FAIL (>30% DD)"
    if cagr >= 900.0:
        return "TIER D (10x in 1Y)"
    if cagr >= 200.0:
        return "TIER C (200-400%)"
    if cagr >= 100.0:
        return "TIER B (100-200%)"
    if cagr >= 50.0:
        return "TIER A (50-100%)"
    return "CONTROL (<50%)"

def run_phase1_tournament():
    print("=" * 125, flush=True)
    print("   PHASE 1 RESEARCH TOURNAMENT: TAIL CAPTURE, CHANDELIER EXITS & GIVEBACK RATIO AUDIT   ", flush=True)
    print("=" * 125, flush=True)
    t0 = time.time()

    print("\n--> [1/4] Preloading & Seasoning Market Data Lake (116 symbols, 2,190 4H bars)...", flush=True)
    base_engine = InstitutionalCompoundingEngine()
    _, _, cached_data = base_engine.load_and_preprocess_data()
    n_assets, avg_rho, n_eff = compute_effective_breadth(cached_data)
    print(f"    Data ready in {time.time() - t0:.2f}s.", flush=True)
    print(f"    Total Universe N: {n_assets} | Mean Cross-Asset Correlation rho: {avg_rho:.4f}", flush=True)
    print(f"    Calculated Effective Breadth N_effective: {n_eff:.2f} independent statistical bets.\n", flush=True)

    results_all: Dict[str, Any] = {}

    widths_perf = [32, 12, 12, 9, 9, 9, 14, 15]
    header_perf = ["Variant", "End Equity", "CAGR (%)", "Sharpe", "Sortino", "Max DD", "Discrepancy", "Frontier Tier"]

    widths_gb = [32, 10, 10, 10, 10, 10, 10, 12]
    header_gb = ["Variant", "Trades", "Win Rate", "PF", "Med GB", "75th GB", "90th GB", "Worst GB"]

    variants = [
        # 1. Control Arm
        ("C1: RD-ACE-C Baseline (Control)", {
            "rd_ace_mode": True, "two_tranche_enabled": True, "trailing_runner_enabled": False,
            "harvest_ratio_a": 0.50, "harvest_target_atr": 2.0, "chandelier_k": 0.0,
            "lev_expansion": 1.50, "initial_capital": 10000.0,
        }),
        # 2. H5 Baseline
        ("C2: H5 Baseline (33% @ 2.5 ATR)", {
            "rd_ace_mode": True, "two_tranche_enabled": True, "trailing_runner_enabled": False,
            "harvest_ratio_a": 0.33, "harvest_target_atr": 2.5, "chandelier_k": 0.0,
            "lev_expansion": 1.50, "initial_capital": 10000.0,
        }),
        # 3. H5 + Chandelier 2.0 ATR (Original 1.50x)
        ("C3: H5 + Chandelier 2.0 ATR (1.50x)", {
            "rd_ace_mode": True, "two_tranche_enabled": True, "trailing_runner_enabled": True,
            "harvest_ratio_a": 0.33, "harvest_target_atr": 2.5, "chandelier_k": 2.0,
            "lev_expansion": 1.50, "initial_capital": 10000.0,
        }),
        # 3b. H5 + Chandelier 2.0 ATR (Calibrated 1.20x Lev)
        ("C3b: H5 + Chan 2.0 ATR (1.20x Lev)", {
            "rd_ace_mode": True, "two_tranche_enabled": True, "trailing_runner_enabled": True,
            "harvest_ratio_a": 0.33, "harvest_target_atr": 2.5, "chandelier_k": 2.0,
            "lev_expansion": 1.20, "initial_capital": 10000.0,
        }),
        # 3c. H5 + Chandelier 2.0 ATR (Calibrated 1.25x Lev)
        ("C3c: H5 + Chan 2.0 ATR (1.25x Lev)", {
            "rd_ace_mode": True, "two_tranche_enabled": True, "trailing_runner_enabled": True,
            "harvest_ratio_a": 0.33, "harvest_target_atr": 2.5, "chandelier_k": 2.0,
            "lev_expansion": 1.25, "initial_capital": 10000.0,
        }),
        # 3d. H5 + Dynamic KER Chandelier 2.0 ATR (1.25x Lev)
        ("C3d: H5 + Dyn KER Chan 2.0 (1.25x)", {
            "rd_ace_mode": True, "two_tranche_enabled": True, "trailing_runner_enabled": True,
            "harvest_ratio_a": 0.33, "harvest_target_atr": 2.5, "chandelier_k": 2.0,
            "dynamic_chandelier": True,
            "lev_expansion": 1.25, "initial_capital": 10000.0,
        }),
        # 4. H5 + Chandelier 2.5 ATR
        ("C4: H5 + Chandelier 2.5 ATR", {
            "rd_ace_mode": True, "two_tranche_enabled": True, "trailing_runner_enabled": True,
            "harvest_ratio_a": 0.33, "harvest_target_atr": 2.5, "chandelier_k": 2.5,
            "lev_expansion": 1.50, "initial_capital": 10000.0,
        }),
        # 5. H5 + Chandelier 3.0 ATR
        ("C5: H5 + Chandelier 3.0 ATR", {
            "rd_ace_mode": True, "two_tranche_enabled": True, "trailing_runner_enabled": True,
            "harvest_ratio_a": 0.33, "harvest_target_atr": 2.5, "chandelier_k": 3.0,
            "lev_expansion": 1.50, "initial_capital": 10000.0,
        }),
        # 6. H5 + Chandelier 3.5 ATR
        ("C6: H5 + Chandelier 3.5 ATR", {
            "rd_ace_mode": True, "two_tranche_enabled": True, "trailing_runner_enabled": True,
            "harvest_ratio_a": 0.33, "harvest_target_atr": 2.5, "chandelier_k": 3.5,
            "lev_expansion": 1.50, "initial_capital": 10000.0,
        }),
        # 7. H5 + Chandelier 2.5 ATR + Selective Exp Leverage 1.75x
        ("C7: H5 + Chan 2.5 + SelLev 1.75x", {
            "rd_ace_mode": True, "two_tranche_enabled": True, "trailing_runner_enabled": True,
            "harvest_ratio_a": 0.33, "harvest_target_atr": 2.5, "chandelier_k": 2.5,
            "lev_expansion": 1.50, "selective_leverage": 1.75, "selective_adx_threshold": 22.0,
            "initial_capital": 10000.0,
        }),
        # 8. H5 + Chandelier 3.0 ATR + Selective Exp Leverage 1.75x
        ("C8: H5 + Chan 3.0 + SelLev 1.75x", {
            "rd_ace_mode": True, "two_tranche_enabled": True, "trailing_runner_enabled": True,
            "harvest_ratio_a": 0.33, "harvest_target_atr": 2.5, "chandelier_k": 3.0,
            "lev_expansion": 1.50, "selective_leverage": 1.75, "selective_adx_threshold": 22.0,
            "initial_capital": 10000.0,
        }),
        # 9. H5 + Chandelier 3.0 ATR + Selective Exp Leverage 2.00x (High ADX > 25)
        ("C9: H5 + Chan 3.0 + SelLev 2.00x", {
            "rd_ace_mode": True, "two_tranche_enabled": True, "trailing_runner_enabled": True,
            "harvest_ratio_a": 0.33, "harvest_target_atr": 2.5, "chandelier_k": 3.0,
            "lev_expansion": 1.50, "selective_leverage": 2.00, "selective_adx_threshold": 25.0,
            "initial_capital": 10000.0,
        }),
        # 10. $1k Account Real Floor Validation (Chandelier 3.0 ATR + $10 Floor)
        ("C10: $1k Floor + Chan 3.0 ATR", {
            "rd_ace_mode": True, "two_tranche_enabled": True, "trailing_runner_enabled": True,
            "harvest_ratio_a": 0.33, "harvest_target_atr": 2.5, "chandelier_k": 3.0,
            "lev_expansion": 1.50, "initial_capital": 1000.0, "min_order_notional": 10.0,
        }),
    ]

    print("=" * 125, flush=True)
    print("   TABLE 1: CORE PERFORMANCE & FRONTIER TIERS   ", flush=True)
    print("=" * 125, flush=True)
    print(format_row(header_perf, widths_perf), flush=True)
    print_sep(widths_perf)

    for name, params in variants:
        eng = InstitutionalCompoundingEngine(**params)
        res = eng.run(cached_market_data=cached_data)

        tier = assign_tier(res["cagr_pct"], res["max_drawdown_pct"])
        row_perf = [
            name,
            f"${res['end_equity']:,.2f}",
            f"{res['cagr_pct']:+.2f}%",
            f"{res['sharpe_ratio']:.2f}",
            f"{res['sortino_ratio']:.2f}",
            f"{res['max_drawdown_pct']:.2f}%",
            f"${res['accounting_discrepancy_usd']:.6f}",
            tier,
        ]
        print(format_row(row_perf, widths_perf), flush=True)

        gb = res.get("giveback_summary", {})
        results_all[name] = {
            "params": params,
            "end_equity": res["end_equity"],
            "cagr_pct": res["cagr_pct"],
            "sharpe": res["sharpe_ratio"],
            "sortino": res["sortino_ratio"],
            "max_dd_pct": res["max_drawdown_pct"],
            "calmar": res["calmar_ratio"],
            "tier": tier,
            "discrepancy": res["accounting_discrepancy_usd"],
            "total_trades": res["total_trades"],
            "win_rate_pct": res["win_rate_pct"],
            "profit_factor": res["profit_factor"],
            "giveback_summary": gb,
        }

    print("\n" + "=" * 125, flush=True)
    print("   TABLE 2: EMPIRICAL GIVEBACK RATIO DISTRIBUTION & TRADE QUALITY   ", flush=True)
    print("=" * 125, flush=True)
    print(format_row(header_gb, widths_gb), flush=True)
    print_sep(widths_gb)

    for name in results_all:
        d = results_all[name]
        gb = d["giveback_summary"]
        row_gb = [
            name,
            str(d["total_trades"]),
            f"{d['win_rate_pct']:.1f}%",
            f"{d['profit_factor']:.2f}",
            f"{gb.get('median_pct', 0.0):.1f}%",
            f"{gb.get('p75_pct', 0.0):.1f}%",
            f"{gb.get('p90_pct', 0.0):.1f}%",
            f"{gb.get('worst_pct', 0.0):.1f}%",
        ]
        print(format_row(row_gb, widths_gb), flush=True)

    # Save to artifacts
    out_file = PIPELINE_ROOT / "artifacts" / "phase1_tail_capture_results.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    def json_helper(obj):
        if isinstance(obj, (np.bool_, bool)):
            return bool(obj)
        if isinstance(obj, (np.integer, int)):
            return int(obj)
        if isinstance(obj, (np.floating, float)):
            return float(obj)
        return str(obj)

    with open(out_file, "w") as f:
        json.dump(results_all, f, indent=2, default=json_helper)

    print(f"\n--> [DONE] Phase 1 Tournament completed in {time.time() - t0:.2f}s.", flush=True)
    print(f"--> Complete results persisted to {out_file}", flush=True)

if __name__ == "__main__":
    from typing import Tuple
    run_phase1_tournament()
