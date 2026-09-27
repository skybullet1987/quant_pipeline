#!/usr/bin/env python3
"""
Branch A5: Regime-Conditional Exposure Governor Sweep
=====================================================
Modulates portfolio gross leverage cap L_max(t+1) in [0.5x, 3.0x] strictly at the portfolio boundary:
    w_i*(t+1) = w_i(t+1) * Phi_t
    sum |w_i*(t+1)| <= L_max(t+1) = 3.0x * Phi_t
where Phi_t in [Phi_min, 1.0] is computed strictly at the close of bar t.

Three Candidate Indicators:
1. Signal 1: Cross-Sectional Trend Breadth (% Assets > EMA50)
   - Equilibrium chop zone: Breadth in [0.40, 0.60] (or [0.35, 0.65])
   - Tapers/steps down gross leverage to Phi_min in [0.33, 0.50]

2. Signal 2: Aggregate Directional Efficiency (Mean Kaufman ER)
   - Lookback k in [120, 240] bars (20d, 40d)
   - Phi_t = clip(ER_bar_t / ER_threshold, Phi_min, 1.00)

3. Signal 3: Cross-Sectional Momentum Dispersion
   - Dispersion = std(R_{i, t-k -> t}) across tradable universe
   - Phi_t = clip(Dispersion_t / Disp_threshold, Phi_min, 1.00)

4. Signal 4: Dual Composite (Breadth + ER)
   - Phi_t = min(Phi_breadth, Phi_ER)
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

from backtest_10x_convex_compounding import InstitutionalCompoundingEngine, TOTAL_EVAL_BARS


def compute_breadth_series(close_mat: np.ndarray, valid_mask: np.ndarray) -> np.ndarray:
    """Compute cross-sectional breadth: % of valid assets with Close > EMA50."""
    n_bars, n_syms = close_mat.shape
    alpha = 2.0 / (50.0 + 1.0)
    
    # Vectorized EMA50
    ema50 = np.zeros_like(close_mat)
    ema50[0] = close_mat[0]
    for t in range(1, n_bars):
        # Only update where valid
        c_t = close_mat[t]
        v_t = valid_mask[t]
        prev_ema = ema50[t - 1]
        ema50[t] = np.where(v_t, alpha * c_t + (1.0 - alpha) * prev_ema, prev_ema)
        # Handle newly listing assets
        new_listings = v_t & ~valid_mask[t - 1]
        if np.any(new_listings):
            ema50[t, new_listings] = c_t[new_listings]

    # Breadth at each bar
    above_ema = (close_mat > ema50) & valid_mask
    valid_counts = np.maximum(1, np.sum(valid_mask, axis=1))
    breadth = np.sum(above_ema, axis=1) / valid_counts
    return breadth


def compute_kaufman_er_series(close_mat: np.ndarray, valid_mask: np.ndarray, lookback: int) -> np.ndarray:
    """Compute aggregate Kaufman Efficiency Ratio across valid assets."""
    n_bars, n_syms = close_mat.shape
    er_mean_ts = np.zeros(n_bars)

    abs_diffs = np.abs(np.diff(close_mat, axis=0)) # (n_bars-1, n_syms)

    for t in range(lookback, n_bars):
        t_start = t - lookback
        v_t = valid_mask[t] & valid_mask[t_start]
        if not np.any(v_t):
            er_mean_ts[t] = 0.5
            continue
        
        displacement = np.abs(close_mat[t, v_t] - close_mat[t_start, v_t])
        path = np.sum(abs_diffs[t_start:t, v_t], axis=0)
        
        with np.errstate(invalid="ignore", divide="ignore"):
            er = np.where(path > 1e-8, displacement / path, 0.0)
        
        er_mean_ts[t] = float(np.mean(er))
    
    er_mean_ts[:lookback] = er_mean_ts[lookback] if lookback < n_bars else 0.5
    return er_mean_ts


def compute_dispersion_series(close_mat: np.ndarray, valid_mask: np.ndarray, lookback: int) -> np.ndarray:
    """Compute cross-sectional return dispersion."""
    n_bars, n_syms = close_mat.shape
    disp_ts = np.zeros(n_bars)

    for t in range(lookback, n_bars):
        t_start = t - lookback
        v_t = valid_mask[t] & valid_mask[t_start]
        if np.sum(v_t) < 3:
            disp_ts[t] = 0.10
            continue
        
        rets = (close_mat[t, v_t] / (close_mat[t_start, v_t] + 1e-12)) - 1.0
        disp_ts[t] = float(np.std(rets))

    disp_ts[:lookback] = disp_ts[lookback] if lookback < n_bars else 0.10
    return disp_ts


def main():
    print("=" * 105)
    print("      BRANCH A5: REGIME-CONDITIONAL EXPOSURE GOVERNOR ABLATION & PARETO TOURNAMENT      ")
    print("=" * 105)

    print("--> Loading canonical dataset...")
    engine_loader = InstitutionalCompoundingEngine()
    _, _, cached_data = engine_loader.load_and_preprocess_data()

    close_mat = cached_data["close"]
    valid_mask = cached_data.get("valid_price_mask", ~np.isnan(close_mat))
    eval_start_idx = cached_data["eval_start_idx"]
    n_bars = len(cached_data["timestamps"])

    print("--> Precomputing causal market indicators...")
    t0 = time.time()
    breadth_ts = compute_breadth_series(close_mat, valid_mask)
    er_20d_ts = compute_kaufman_er_series(close_mat, valid_mask, lookback=120)
    er_40d_ts = compute_kaufman_er_series(close_mat, valid_mask, lookback=240)
    disp_20d_ts = compute_dispersion_series(close_mat, valid_mask, lookback=120)
    disp_40d_ts = compute_dispersion_series(close_mat, valid_mask, lookback=240)
    print(f"--> Precomputed 5 indicator series across {n_bars} bars in {time.time()-t0:.2f}s.\n")

    # Indicator distributions
    eval_breadth = breadth_ts[eval_start_idx:]
    eval_er20 = er_20d_ts[eval_start_idx:]
    eval_er40 = er_40d_ts[eval_start_idx:]
    eval_disp20 = disp_20d_ts[eval_start_idx:]

    print(f"Indicator Summary (Evaluation Window):")
    print(f"  Breadth:    mean={np.mean(eval_breadth):.3f}, 10%={np.percentile(eval_breadth, 10):.3f}, 50%={np.median(eval_breadth):.3f}, 90%={np.percentile(eval_breadth, 90):.3f}")
    print(f"  ER (20d):   mean={np.mean(eval_er20):.3f}, 10%={np.percentile(eval_er20, 10):.3f}, 50%={np.median(eval_er20):.3f}, 90%={np.percentile(eval_er20, 90):.3f}")
    print(f"  ER (40d):   mean={np.mean(eval_er40):.3f}, 10%={np.percentile(eval_er40, 10):.3f}, 50%={np.median(eval_er40):.3f}, 90%={np.percentile(eval_er40, 90):.3f}")
    print(f"  Disp (20d): mean={np.mean(eval_disp20):.3f}, 10%={np.percentile(eval_disp20, 10):.3f}, 50%={np.median(eval_disp20):.3f}, 90%={np.percentile(eval_disp20, 90):.3f}\n")

    configurations = []

    # 1. Baseline A0
    configurations.append({
        "name": "A0_Golden_Control",
        "type": "none",
        "phi_series": np.ones(n_bars),
        "desc": "Fixed 3.0x Baseline (No Governor)"
    })

    # 2. Breadth Governor Candidates
    for phi_min in [0.33, 0.50]:
        for half_w in [0.10, 0.15]:
            # Continuous taper around 0.50
            phi_taper = np.ones(n_bars)
            for t in range(n_bars):
                dist = abs(breadth_ts[t] - 0.50)
                if dist < half_w:
                    # In chop zone
                    intensity = 1.0 - (dist / half_w)
                    phi_taper[t] = 1.0 - (1.0 - phi_min) * intensity
                else:
                    phi_taper[t] = 1.0
            
            configurations.append({
                "name": f"Breadth_Taper_W{int(half_w*100)}_Min{int(phi_min*100)}",
                "type": "breadth_taper",
                "phi_series": phi_taper,
                "desc": f"Breadth Continuous Taper (HalfWidth={half_w}, PhiMin={phi_min})"
            })

            # Step down
            phi_step = np.ones(n_bars)
            for t in range(n_bars):
                dist = abs(breadth_ts[t] - 0.50)
                if dist < half_w:
                    phi_step[t] = phi_min
                else:
                    phi_step[t] = 1.0
            
            configurations.append({
                "name": f"Breadth_Step_W{int(half_w*100)}_Min{int(phi_min*100)}",
                "type": "breadth_step",
                "phi_series": phi_step,
                "desc": f"Breadth Step Function (HalfWidth={half_w}, PhiMin={phi_min})"
            })

    # 3. Aggregate Directional Efficiency (ER) Candidates
    for er_ts, lb_label in [(er_20d_ts, "20d"), (er_40d_ts, "40d")]:
        for er_thresh in [0.25, 0.35, 0.45]:
            for phi_min in [0.33, 0.50]:
                phi_er = np.clip(er_ts / er_thresh, phi_min, 1.0)
                configurations.append({
                    "name": f"ER_{lb_label}_Thresh{int(er_thresh*100)}_Min{int(phi_min*100)}",
                    "type": "efficiency",
                    "phi_series": phi_er,
                    "desc": f"Kaufman ER ({lb_label}, Thresh={er_thresh}, PhiMin={phi_min})"
                })

    # 4. Dispersion Governor Candidates
    for disp_ts, lb_label in [(disp_20d_ts, "20d"), (disp_40d_ts, "40d")]:
        for disp_thresh in [0.15, 0.25]:
            for phi_min in [0.33, 0.50]:
                phi_disp = np.clip(disp_ts / disp_thresh, phi_min, 1.0)
                configurations.append({
                    "name": f"Disp_{lb_label}_Thresh{int(disp_thresh*100)}_Min{int(phi_min*100)}",
                    "type": "dispersion",
                    "phi_series": phi_disp,
                    "desc": f"Cross-Sectional Dispersion ({lb_label}, Thresh={disp_thresh}, PhiMin={phi_min})"
                })

    # 5. Dual Composite Candidates (Breadth + ER)
    for phi_min in [0.33, 0.50]:
        # Breadth Step W10 + ER 20d Thresh35
        p_b = np.where(np.abs(breadth_ts - 0.50) < 0.10, phi_min, 1.0)
        p_er = np.clip(er_20d_ts / 0.35, phi_min, 1.0)
        phi_comp = np.minimum(p_b, p_er)
        configurations.append({
            "name": f"Composite_BreadthW10_ER20d_Min{int(phi_min*100)}",
            "type": "composite",
            "phi_series": phi_comp,
            "desc": f"Dual Composite Breadth+ER (PhiMin={phi_min})"
        })

    print(f"Total Candidate Governor Configurations to Evaluate: {len(configurations)}\n")
    print(f"{'CONFIGURATION':<38} {'ENDING EQ':<13} {'MULT':<7} {'CAGR':<9} {'SHARPE':<7} {'MDD':<7} {'CALMAR':<7} {'STATUS':<15}")
    print("-" * 108)

    results = []
    base_res = None

    for i, cfg in enumerate(configurations):
        engine = InstitutionalCompoundingEngine(
            fixed_leverage=3.0,
            turnover_lambda=0.85,
            two_tranche_enabled=False,
            pyramid_ratio=0.0,
            regime_governor_scalars=cfg["phi_series"]
        )
        res = engine.run(cached_data)

        eq = res["ending_equity"]
        mult = eq / 10000.0
        cagr = res["net_cagr"]
        sharpe = res["sharpe"]
        mdd = res["max_drawdown"]
        calmar = res["calmar"]

        if i == 0:
            base_res = res
            status = "GOLDEN CONTROL"
        else:
            # Gating Rule:
            # MDD < 42.0%, Sharpe >= 2.35, Calmar >= 9.50
            if mdd < 42.0 and sharpe >= 2.35 and calmar >= 9.50:
                status = "PASSES ALL GATES"
            elif mdd < 48.0 and sharpe >= 2.20 and calmar >= 8.53:
                status = "MARGINAL PASS"
            elif mdd < 55.0 and sharpe >= 2.20:
                status = "MODERATE DD RED"
            else:
                status = "FAILS GATES"

        print(f"{cfg['name']:<38} ${eq:<12,.2f} {mult:<6.2f}x {cagr:<8.2f}% {sharpe:<6.2f} {mdd:<6.2f}% {calmar:<6.2f} {status:<15}", flush=True)

        results.append({
            "name": cfg["name"],
            "type": cfg["type"],
            "desc": cfg["desc"],
            "ending_equity": eq,
            "equity_multiple": mult,
            "cagr_pct": cagr,
            "sharpe": sharpe,
            "sortino": res["sortino"],
            "calmar": calmar,
            "max_drawdown_pct": mdd,
            "turnover_nav": res.get("total_turnover_nav", 0.0),
            "total_friction_usd": res["cost_breakdown"]["total_execution_friction_usd"],
            "status": status,
        })

    print("-" * 108)

    # Save to JSON
    out_path = PIPELINE_ROOT / "data" / "branch_a5_regime_governor_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nWrote {len(results)} configuration records to {out_path}\n")


if __name__ == "__main__":
    main()
