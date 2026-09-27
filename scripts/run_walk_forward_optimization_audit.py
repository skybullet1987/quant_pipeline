#!/usr/bin/env python3
"""
Pre-Registered Phase 3 Walk-Forward Optimization (WFO) Audit
============================================================
Evaluates out-of-sample persistence for the frozen A0 causal alpha engine under strict pre-registered gates:

Pre-Declared Pass/Fail Gates:
1. OOS Sharpe Ratio: Sharpe_OOS >= 1.50
2. Turnover Stability: Annualized Turnover in [250x, 550x] NAV
3. Downside Containment: MDD_OOS <= 65.0%

Decision Rule:
If ANY single OOS fold yields a negative Sharpe ratio or breaks the 65% drawdown ceiling,
A0 fails certification and cannot proceed to capital deployment.

Window Topologies Evaluated:
A. Primary Topology (4 Non-Overlapping 60-Day OOS Folds):
   - Fold 1: IS [0, 750) bars (125d)   -> OOS [750, 1110) bars (60d)
   - Fold 2: IS [360, 1110) bars (125d) -> OOS [1110, 1470) bars (60d)
   - Fold 3: IS [720, 1470) bars (125d) -> OOS [1470, 1830) bars (60d)
   - Fold 4: IS [1080, 1830) bars (125d)-> OOS [1830, 2190) bars (60d)

B. 180-Day In-Sample Topology (3 Full 60-Day OOS Folds + Tail):
   - Fold 1: IS [0, 1080) bars (180d)  -> OOS [1080, 1440) bars (60d)
   - Fold 2: IS [360, 1440) bars (180d) -> OOS [1440, 1800) bars (60d)
   - Fold 3: IS [720, 1800) bars (180d) -> OOS [1800, 2160) bars (60d)

C. 180-Day In-Sample / 45-Day OOS Topology (4 Non-Overlapping 45-Day Folds):
   - Fold 1: IS [0, 1080) bars (180d)  -> OOS [1080, 1350) bars (45d)
   - Fold 2: IS [270, 1350) bars (180d) -> OOS [1350, 1620) bars (45d)
   - Fold 3: IS [540, 1620) bars (180d) -> OOS [1620, 1890) bars (45d)
   - Fold 4: IS [810, 1890) bars (180d) -> OOS [1890, 2160) bars (45d)
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from backtest_10x_convex_compounding import InstitutionalCompoundingEngine, TOTAL_EVAL_BARS


def evaluate_window_metrics(
    equity_slice: np.ndarray,
    turnover_slice: np.ndarray,
    n_bars: int,
    label: str = "Window"
) -> Dict[str, Any]:
    """Compute annualized performance and risk metrics on a specific slice of equity curve."""
    assert len(equity_slice) >= 2, "Window must have at least 2 points"
    
    start_eq = float(equity_slice[0])
    end_eq = float(equity_slice[-1])
    multiple = end_eq / start_eq if start_eq > 0 else 0.0
    net_return = multiple - 1.0
    
    # Bar returns
    bar_rets = np.diff(equity_slice) / (equity_slice[:-1] + 1e-12)
    mean_ret = float(np.mean(bar_rets))
    std_ret = float(np.std(bar_rets))
    
    ann_factor = math.sqrt(2190)
    sharpe = float((mean_ret / (std_ret + 1e-12)) * ann_factor) if std_ret > 1e-8 else 0.0
    
    # Downside deviation for Sortino
    neg_rets = bar_rets[bar_rets < 0]
    downside_std = float(np.std(neg_rets)) if len(neg_rets) > 0 else 1e-8
    sortino = float((mean_ret / (downside_std + 1e-12)) * ann_factor) if downside_std > 1e-8 else 0.0
    
    # Max Drawdown strictly within this window
    peaks = np.maximum.accumulate(equity_slice)
    dd_arr = (peaks - equity_slice) / (peaks + 1e-12)
    max_dd_pct = float(np.max(dd_arr)) * 100.0
    
    # Annualized CAGR
    years = n_bars / 2190.0
    if multiple > 0 and years > 0:
        cagr_pct = float((multiple ** (1.0 / years) - 1.0) * 100.0)
    else:
        cagr_pct = -100.0
        
    calmar = cagr_pct / max_dd_pct if max_dd_pct > 0 else 0.0
    
    # Annualized turnover
    window_turnover = float(np.sum(turnover_slice))
    ann_turnover = float(window_turnover * (2190.0 / n_bars))
    
    return {
        "n_bars": n_bars,
        "days": n_bars / 6.0,
        "start_equity": start_eq,
        "end_equity": end_eq,
        "equity_multiple": multiple,
        "net_return_pct": net_return * 100.0,
        "annualized_cagr_pct": cagr_pct,
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "max_drawdown_pct": max_dd_pct,
        "calmar_ratio": calmar,
        "window_turnover_nav": window_turnover,
        "annualized_turnover_nav": ann_turnover,
    }


def audit_wfo_topology(
    name: str,
    folds_def: List[Dict[str, Any]],
    full_equity_curve: np.ndarray,
    full_turnover_history: np.ndarray,
) -> Dict[str, Any]:
    print("\n" + "=" * 115)
    print(f"   WALK-FORWARD TOPOLOGY: {name.upper()}")
    print("=" * 115)
    print(f"{'FOLD':<10} {'TYPE':<6} {'BARS':<14} {'DATES/DAYS':<12} {'CAGR':<10} {'SHARPE':<8} {'MDD':<8} {'ANN TURNOVER':<14} {'STATUS':<15}")
    print("-" * 115)

    fold_results = []
    all_oos_passed = True
    any_catastrophic_fail = False

    for fold in folds_def:
        f_idx = fold["fold_idx"]
        is_start, is_end = fold["is_start"], fold["is_end"]
        oos_start, oos_end = fold["oos_start"], fold["oos_end"]

        # In-Sample Metrics (Continuous Path Audit)
        is_eq = full_equity_curve[is_start : is_end + 1]
        is_to = full_turnover_history[is_start : is_end]
        is_metrics = evaluate_window_metrics(is_eq, is_to, is_end - is_start, label=f"Fold {f_idx} IS")

        # Out-of-Sample Metrics (Continuous Path Audit)
        oos_eq = full_equity_curve[oos_start : oos_end + 1]
        oos_to = full_turnover_history[oos_start : oos_end]
        oos_metrics = evaluate_window_metrics(oos_eq, oos_to, oos_end - oos_start, label=f"Fold {f_idx} OOS")

        # Evaluate Gating Criteria strictly on OOS:
        # 1. Sharpe >= 1.50
        # 2. Turnover in [250, 550]
        # 3. MDD <= 65.0%
        # Catastrophic failure if Sharpe < 0.0 or MDD > 65.0%
        c1 = oos_metrics["sharpe_ratio"] >= 1.50
        c2 = 250.0 <= oos_metrics["annualized_turnover_nav"] <= 550.0
        c3 = oos_metrics["max_drawdown_pct"] <= 65.0
        
        is_catastrophic = (oos_metrics["sharpe_ratio"] < 0.0) or (oos_metrics["max_drawdown_pct"] > 65.0)
        if is_catastrophic:
            any_catastrophic_fail = True
            all_oos_passed = False
            status = "CATASTROPHIC FAIL"
        elif c1 and c2 and c3:
            status = "PASS"
        else:
            all_oos_passed = False
            reasons = []
            if not c1: reasons.append(f"Sharpe {oos_metrics['sharpe_ratio']:.2f}<1.50")
            if not c2: reasons.append(f"Turnover {oos_metrics['annualized_turnover_nav']:.0f}")
            if not c3: reasons.append(f"MDD {oos_metrics['max_drawdown_pct']:.1f}%>65%")
            status = f"FAIL ({', '.join(reasons)})"

        print(f"Fold {f_idx:<5} {'IS':<6} [{is_start:>4}:{is_end:>4}]  {is_metrics['days']:>5.0f} days  {is_metrics['annualized_cagr_pct']:>8.1f}%  {is_metrics['sharpe_ratio']:>6.2f}  {is_metrics['max_drawdown_pct']:>6.2f}%  {is_metrics['annualized_turnover_nav']:>10.1f}x     IS BASELINE")
        print(f"Fold {f_idx:<5} {'OOS':<6} [{oos_start:>4}:{oos_end:>4}]  {oos_metrics['days']:>5.0f} days  {oos_metrics['annualized_cagr_pct']:>8.1f}%  {oos_metrics['sharpe_ratio']:>6.2f}  {oos_metrics['max_drawdown_pct']:>6.2f}%  {oos_metrics['annualized_turnover_nav']:>10.1f}x     {status}")
        print("." * 115)

        fold_results.append({
            "fold_idx": f_idx,
            "in_sample": {
                "start_bar": is_start,
                "end_bar": is_end,
                "metrics": is_metrics,
            },
            "out_of_sample": {
                "start_bar": oos_start,
                "end_bar": oos_end,
                "metrics": oos_metrics,
                "passed_gate": c1 and c2 and c3,
                "reasons": status,
            }
        })

    topology_verdict = "PASSED CERTIFICATION" if all_oos_passed else ("FAILED (CATASTROPHIC BREACH)" if any_catastrophic_fail else "FAILED PRE-DECLARED GATES")
    print(f"\n--> TOPOLOGY VERDICT: {topology_verdict}\n")

    return {
        "topology_name": name,
        "all_passed": all_oos_passed,
        "any_catastrophic_fail": any_catastrophic_fail,
        "verdict": topology_verdict,
        "folds": fold_results,
    }


def main():
    print("=" * 115)
    print("      FORMAL PRE-REGISTERED WALK-FORWARD OPTIMIZATION (WFO) CERTIFICATION AUDIT      ")
    print("=" * 115)

    print("--> Loading canonical dataset and executing immutable A0 baseline...")
    engine = InstitutionalCompoundingEngine(
        fixed_leverage=3.0,
        turnover_lambda=0.85,
        two_tranche_enabled=False,
        pyramid_ratio=0.0
    )
    _, _, cached_data = engine.load_and_preprocess_data()
    res = engine.run(cached_data)

    full_eq = np.array(res["equity_curve"]) # 2191 items
    
    # Extract bar-level turnover
    full_to = np.array(res["turnover_history"]) # 2190 items
    
    # --------------------------------------------------------------------------
    # TOPOLOGY A: Primary 4 Non-Overlapping 60-Day OOS Folds (125d IS / 60d OOS)
    # Total bars = 2,190. IS = 750 bars (125d). OOS = 360 bars (60d). Step = 360 bars.
    # --------------------------------------------------------------------------
    top_a_folds = [
        {"fold_idx": 1, "is_start": 0,    "is_end": 750,  "oos_start": 750,  "oos_end": 1110},
        {"fold_idx": 2, "is_start": 360,  "is_end": 1110, "oos_start": 1110, "oos_end": 1470},
        {"fold_idx": 3, "is_start": 720,  "is_end": 1470, "oos_start": 1470, "oos_end": 1830},
        {"fold_idx": 4, "is_start": 1080, "is_end": 1830, "oos_start": 1830, "oos_end": 2190},
    ]
    res_a = audit_wfo_topology("Topology A (Primary: 4 Non-Overlapping 60d OOS Folds)", top_a_folds, full_eq, full_to)

    # --------------------------------------------------------------------------
    # TOPOLOGY B: 180-Day In-Sample / 60-Day OOS Folds
    # IS = 1080 bars (180d). OOS = 360 bars (60d). Step = 360 bars.
    # --------------------------------------------------------------------------
    top_b_folds = [
        {"fold_idx": 1, "is_start": 0,   "is_end": 1080, "oos_start": 1080, "oos_end": 1440},
        {"fold_idx": 2, "is_start": 360, "is_end": 1440, "oos_start": 1440, "oos_end": 1800},
        {"fold_idx": 3, "is_start": 720, "is_end": 1800, "oos_start": 1800, "oos_end": 2160},
    ]
    res_b = audit_wfo_topology("Topology B (180-Day IS / 3 Full 60d OOS Folds)", top_b_folds, full_eq, full_to)

    # --------------------------------------------------------------------------
    # TOPOLOGY C: 180-Day In-Sample / 45-Day OOS Folds (4 Folds)
    # IS = 1080 bars (180d). OOS = 270 bars (45d). Step = 270 bars.
    # --------------------------------------------------------------------------
    top_c_folds = [
        {"fold_idx": 1, "is_start": 0,   "is_end": 1080, "oos_start": 1080, "oos_end": 1350},
        {"fold_idx": 2, "is_start": 270, "is_end": 1350, "oos_start": 1350, "oos_end": 1620},
        {"fold_idx": 3, "is_start": 540, "is_end": 1620, "oos_start": 1620, "oos_end": 1890},
        {"fold_idx": 4, "is_start": 810, "is_end": 1890, "oos_start": 1890, "oos_end": 2160},
    ]
    res_c = audit_wfo_topology("Topology C (180-Day IS / 4 Non-Overlapping 45d OOS Folds)", top_c_folds, full_eq, full_to)

    # Save to JSON
    summary_payload = {
        "timestamp_utc": "2026-09-24T04:30:00Z",
        "predeclared_gates": {
            "min_oos_sharpe": 1.50,
            "turnover_range_nav": [250.0, 550.0],
            "max_oos_drawdown_pct": 65.0,
            "decision_rule": "Reject if ANY single OOS fold has Sharpe < 0.0 or MDD > 65.0%"
        },
        "topologies": {
            "topology_a_primary_60d": res_a,
            "topology_b_180d_is_60d_oos": res_b,
            "topology_c_180d_is_45d_oos": res_c,
        }
    }

    out_path = PIPELINE_ROOT / "data" / "wfo_certification_audit_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(summary_payload, f, indent=2)
    print(f"\n[REPORT] Saved full WFO certification report to {out_path}\n")


if __name__ == "__main__":
    main()
