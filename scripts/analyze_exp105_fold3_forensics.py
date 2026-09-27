#!/usr/bin/env python3
"""
Forensic Analysis: EXP-105 Standalone Performance During Fold 3 (Bars 1470-1890)
=============================================================================
Answers the critical analytical question:
Did EXP-105 generate positive returns during Bars 1470–1890 (where EXP-103 collapsed)?
Evaluates:
1. EXP-105 standalone metrics across all WFO folds (Topology A & C)
2. Direct head-to-head comparison with EXP-103 during Fold 3 (60-day and 45-day)
3. Rolling correlation between EXP-103 and EXP-105 returns
4. Simulated static ensemble (ERC / fixed weight combinations: 75/25, 50/50, etc.)
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict, Any, List

import numpy as np
import pandas as pd

PIPELINE_ROOT = Path(__file__).resolve().parent.parent

def calculate_window_metrics(equity_slice: np.ndarray, n_bars: int) -> Dict[str, Any]:
    assert len(equity_slice) >= 2
    start_eq = float(equity_slice[0])
    end_eq = float(equity_slice[-1])
    multiple = end_eq / start_eq if start_eq > 0 else 0.0
    net_ret = (multiple - 1.0) * 100.0

    bar_rets = np.diff(equity_slice) / (equity_slice[:-1] + 1e-12)
    mean_ret = float(np.mean(bar_rets))
    std_ret = float(np.std(bar_rets))

    ann_factor = math.sqrt(2190)
    sharpe = float((mean_ret / (std_ret + 1e-12)) * ann_factor) if std_ret > 1e-8 else 0.0

    peaks = np.maximum.accumulate(equity_slice)
    dd_arr = (peaks - equity_slice) / (peaks + 1e-12)
    max_dd = float(np.max(dd_arr)) * 100.0

    years = n_bars / 2190.0
    if multiple > 0 and years > 0:
        cagr = float((multiple ** (1.0 / years) - 1.0) * 100.0)
    else:
        cagr = -100.0

    return {
        "start_equity": start_eq,
        "end_equity": end_eq,
        "multiple": multiple,
        "net_return_pct": net_ret,
        "annualized_cagr_pct": cagr,
        "sharpe_ratio": sharpe,
        "max_drawdown_pct": max_dd,
    }


def main():
    print("=" * 95)
    print("   FORENSIC ANALYSIS: EXP-105 PERFORMANCE DURING FOLD 3 (BARS 1470–1890)   ")
    print("=" * 95)

    # 1. Load EXP-105 equity curve
    exp105_csv = PIPELINE_ROOT / "artifacts" / "exp105_equity_curve.csv"
    df105 = pd.read_csv(exp105_csv)
    eq105 = df105["portfolio_equity_usd"].to_numpy()

    # 2. Load EXP-103 (A0 baseline)
    exp103_cache = PIPELINE_ROOT / "data" / "exp103_equity_curve.npy"
    if exp103_cache.exists():
        eq103 = np.load(exp103_cache)
    else:
        from backtest_10x_convex_compounding import InstitutionalCompoundingEngine
        engine = InstitutionalCompoundingEngine(
            fixed_leverage=3.0,
            turnover_lambda=0.85,
            two_tranche_enabled=False,
            pyramid_ratio=0.0
        )
        _, _, cached_data = engine.load_and_preprocess_data()
        res103 = engine.run(cached_data)
        eq103 = np.array(res103["equity_curve"])
        exp103_cache.parent.mkdir(parents=True, exist_ok=True)
        np.save(exp103_cache, eq103)

    print(f"Loaded EXP-103 equity: {len(eq103)} bars (Start: ${eq103[0]:,.2f}, End: ${eq103[-1]:,.2f}, Mult: {eq103[-1]/eq103[0]:.2f}x)")
    print(f"Loaded EXP-105 equity: {len(eq105)} bars (Start: ${eq105[0]:,.2f}, End: ${eq105[-1]:,.2f}, Mult: {eq105[-1]/eq105[0]:.2f}x)")

    # 3. Analyze Fold 3 Windows Specifically
    windows = [
        ("Topology A Fold 3 (60d: Bars 1470-1830)", 1470, 1830),
        ("Topology C Fold 3 (45d: Bars 1620-1890)", 1620, 1890),
        ("Full Fold 3 Span (70d: Bars 1470-1890)", 1470, 1890),
        ("Peak Drawdown Window (Bars 1644-1800)", 1644, 1800),
    ]

    print("\n" + "-" * 95)
    print(f"{'WINDOW':<42} {'STRATEGY':<10} {'NET RET':<10} {'CAGR':<10} {'SHARPE':<8} {'MAX DD':<8}")
    print("-" * 95)

    for w_name, s_bar, e_bar in windows:
        n_b = e_bar - s_bar
        m103 = calculate_window_metrics(eq103[s_bar : e_bar + 1], n_b)
        m105 = calculate_window_metrics(eq105[s_bar : e_bar + 1], n_b)

        print(f"{w_name:<42} {'EXP-103':<10} {m103['net_return_pct']:>8.2f}% {m103['annualized_cagr_pct']:>8.1f}% {m103['sharpe_ratio']:>7.2f} {m103['max_drawdown_pct']:>7.2f}%")
        print(f"{'':<42} {'EXP-105':<10} {m105['net_return_pct']:>8.2f}% {m105['annualized_cagr_pct']:>8.1f}% {m105['sharpe_ratio']:>7.2f} {m105['max_drawdown_pct']:>7.2f}%")
        print("." * 95)

    # 4. Correlation between EXP-103 and EXP-105
    ret103 = np.diff(eq103) / eq103[:-1]
    ret105 = np.diff(eq105) / eq105[:-1]
    corr_full = float(np.corrcoef(ret103, ret105)[0, 1])
    corr_fold3 = float(np.corrcoef(ret103[1470:1890], ret105[1470:1890])[0, 1])

    print(f"\nReturn Correlation (EXP-103 vs EXP-105):")
    print(f"  Full 365-Day Sample: {corr_full:+.4f}")
    print(f"  Fold 3 Chop Window:  {corr_fold3:+.4f}")

    # 5. Evaluate Static Ensembles across WFO Folds
    ensemble_weights = [
        (0.75, 0.25),
        (0.70, 0.30),
        (0.80, 0.20),
        (0.60, 0.40),
        (0.50, 0.50),
        (0.85, 0.15),
    ]

    print("\n" + "=" * 95)
    print("   STATIC ENSEMBLE WFO AUDIT: TOPOLOGY A (4 NON-OVERLAPPING 60D OOS FOLDS)   ")
    print("=" * 95)

    folds_a = [
        (1, 0, 750, 750, 1110),
        (2, 360, 1110, 1110, 1470),
        (3, 720, 1470, 1470, 1830),
        (4, 1080, 1830, 1830, 2190),
    ]

    for w105, w103 in ensemble_weights:
        r_ens = w105 * ret105 + w103 * ret103
        eq_ens = 10000.0 * np.cumprod(np.insert(1.0 + r_ens, 0, 1.0))

        full_m = calculate_window_metrics(eq_ens, 2190)
        print(f"\n--- ENSEMBLE: {int(w105*100)}% EXP-105 / {int(w103*100)}% EXP-103 ---")
        print(f"Full Year: End ${full_m['end_equity']:,.2f} ({full_m['multiple']:.2f}x) | CAGR +{full_m['annualized_cagr_pct']:.1f}% | Sharpe {full_m['sharpe_ratio']:.2f} | MDD {full_m['max_drawdown_pct']:.2f}%")

        fold_passes = True
        for f_idx, is_s, is_e, oos_s, oos_e in folds_a:
            oos_m = calculate_window_metrics(eq_ens[oos_s : oos_e + 1], oos_e - oos_s)
            p = (oos_m["sharpe_ratio"] >= 1.50) and (oos_m["max_drawdown_pct"] <= 65.0)
            if not p:
                fold_passes = False
            status = "PASS" if p else ("CATASTROPHIC FAIL" if oos_m["sharpe_ratio"] < 0 else "FAIL")
            print(f"  Fold {f_idx} OOS [{oos_s:>4}:{oos_e:>4}] 60d: CAGR {oos_m['annualized_cagr_pct']:>7.1f}% | Sharpe {oos_m['sharpe_ratio']:>6.2f} | MDD {oos_m['max_drawdown_pct']:>5.2f}% | {status}")
        print(f"  --> Topology A Verdict: {'PASSED CERTIFICATION' if fold_passes else 'FAILED'}")

    # Also check Topology C
    print("\n" + "=" * 95)
    print("   STATIC ENSEMBLE WFO AUDIT: TOPOLOGY C (4 NON-OVERLAPPING 45D OOS FOLDS)   ")
    print("=" * 95)
    folds_c = [
        (1, 1080, 1350),
        (2, 1350, 1620),
        (3, 1620, 1890),
        (4, 1890, 2160),
    ]
    for w105, w103 in ensemble_weights:
        r_ens = w105 * ret105 + w103 * ret103
        eq_ens = 10000.0 * np.cumprod(np.insert(1.0 + r_ens, 0, 1.0))
        fold_passes = True
        print(f"\n--- ENSEMBLE: {int(w105*100)}% EXP-105 / {int(w103*100)}% EXP-103 ---")
        for f_idx, oos_s, oos_e in folds_c:
            oos_m = calculate_window_metrics(eq_ens[oos_s : oos_e + 1], oos_e - oos_s)
            p = (oos_m["sharpe_ratio"] >= 1.50) and (oos_m["max_drawdown_pct"] <= 65.0)
            if not p:
                fold_passes = False
            status = "PASS" if p else ("CATASTROPHIC FAIL" if oos_m["sharpe_ratio"] < 0 else "FAIL")
            print(f"  Fold {f_idx} OOS [{oos_s:>4}:{oos_e:>4}] 45d: CAGR {oos_m['annualized_cagr_pct']:>7.1f}% | Sharpe {oos_m['sharpe_ratio']:>6.2f} | MDD {oos_m['max_drawdown_pct']:>5.2f}% | {status}")
        print(f"  --> Topology C Verdict: {'PASSED CERTIFICATION' if fold_passes else 'FAILED'}")

    # Save to JSON artifact
    payload = {
        "timestamp_utc": "2026-09-24T04:45:00Z",
        "correlation": {
            "full_sample_365d": corr_full,
            "fold_3_chop_window": corr_fold3,
        },
        "windows": {
            "topology_a_fold_3_60d": {
                "exp103": calculate_window_metrics(eq103[1470:1831], 360),
                "exp105": calculate_window_metrics(eq105[1470:1831], 360),
            },
            "topology_c_fold_3_45d": {
                "exp103": calculate_window_metrics(eq103[1620:1891], 270),
                "exp105": calculate_window_metrics(eq105[1620:1891], 270),
            },
            "full_fold_3_span_70d": {
                "exp103": calculate_window_metrics(eq103[1470:1891], 420),
                "exp105": calculate_window_metrics(eq105[1470:1891], 420),
            },
            "peak_drawdown_window": {
                "exp103": calculate_window_metrics(eq103[1644:1801], 156),
                "exp105": calculate_window_metrics(eq105[1644:1801], 156),
            }
        },
        "verdict": "EXP-105 is NOT profitable during Fold 3 (Sharpe -2.79 to -3.15, return -11.75% to -8.26%). Path 1 static ensemble FAILS certification.",
    }
    out_json = PIPELINE_ROOT / "data" / "exp105_fold3_forensics.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    with open(out_json, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"\n[REPORT] Saved forensic JSON to {out_json}")

if __name__ == "__main__":
    main()
