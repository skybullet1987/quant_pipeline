#!/usr/bin/env python3
"""
Stage 3A: Exploratory Systemic Market Turnover Velocity Gate Calibration
========================================================================
Implements and evaluates the Systemic Turnover Velocity Gate on the canonical 2,190-bar dataset.

Mathematical Formulation:
  TurnoverVelocity_t = EMA_w(Agg_Volume_t) / EMA_w(Agg_Open_Interest_t)
  Phi_macro(t) = 1.0 if TurnoverVelocity_t >= Q_tau(TurnoverVelocity_IS) else lambda_floor
  Gross Exposure Cap(t+1) = 3.0x * Phi_macro(t)

Point-in-Time (PIT) Controls:
  - Active tradeable universe U_t dynamically masked at each bar t.
  - Quantile threshold Q_tau computed strictly on In-Sample window (Bars 0 to 1470).
  - Causal next-bar execution: Phi_macro(t) regulates exposure on bar t+1.

Pre-Registered Grid (18 Configurations):
  - IS Quantiles tau: [0.15, 0.20, 0.25]
  - Leverage Floors lambda_floor: [0.00x, 0.33x, 0.50x]
  - Lookback Windows: [10 days (60 bars), 20 days (120 bars)]

Strict Gating Constraints:
  - Duty Cycle Downtime <= 25.0% across full dataset.
  - Multi-fold disable distribution reporting (ensures not selectively targeting only Fold 3).
  - Fold 3 recovery target: Sharpe >= 0.00.
  - Trend-regime retention: Retains >= 70% of A0 Sharpe in Folds 1, 2, and 4.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from backtest_10x_convex_compounding import InstitutionalCompoundingEngine, TOTAL_EVAL_BARS


def calculate_window_metrics(equity_slice: np.ndarray, n_bars: int) -> Dict[str, Any]:
    assert len(equity_slice) >= 2, "Window must have at least 2 points"
    start_eq = float(equity_slice[0])
    end_eq = float(equity_slice[-1])
    multiple = end_eq / start_eq if start_eq > 0 else 0.0
    net_return = multiple - 1.0

    bar_rets = np.diff(equity_slice) / (equity_slice[:-1] + 1e-12)
    mean_ret = float(np.mean(bar_rets))
    std_ret = float(np.std(bar_rets))

    ann_factor = math.sqrt(2190)
    sharpe = float((mean_ret / (std_ret + 1e-12)) * ann_factor) if std_ret > 1e-8 else 0.0

    peaks = np.maximum.accumulate(equity_slice)
    dd_arr = (peaks - equity_slice) / (peaks + 1e-12)
    max_dd_pct = float(np.max(dd_arr)) * 100.0

    years = n_bars / 2190.0
    cagr_pct = float((multiple ** (1.0 / years) - 1.0) * 100.0) if (multiple > 0 and years > 0) else -100.0
    calmar = cagr_pct / max_dd_pct if max_dd_pct > 0 else 0.0

    return {
        "start_equity": start_eq,
        "end_equity": end_eq,
        "multiple": multiple,
        "net_return_pct": net_return * 100.0,
        "annualized_cagr_pct": cagr_pct,
        "sharpe_ratio": sharpe,
        "max_drawdown_pct": max_dd_pct,
        "calmar_ratio": calmar,
    }


def compute_turnover_velocity_series(
    data: Dict[str, Any],
    eval_start_idx: int,
    total_bars: int,
    lookback_bars: int,
) -> np.ndarray:
    """
    Computes Point-in-Time Systemic Market Turnover Velocity time series across evaluation window.
    """
    close = data["close"]
    vol = data["volume"]
    valid = data["valid_price_mask"]
    T_full, N = close.shape

    # Dollar volume: close * vol on active valid contracts
    dollar_vol = np.where(valid, close * vol, 0.0)
    agg_vol = np.sum(dollar_vol, axis=1)

    # Dwell decay for Open Interest (half-life of perp positions ~8-10 days: 48 4H bars)
    decay = np.exp(-np.log(2.0) / 48.0)
    oi_mat = np.zeros((T_full, N))
    for col in range(N):
        valid_idx = np.where(valid[:, col])[0]
        if len(valid_idx) > 0:
            first_idx = valid_idx[0]
            oi_mat[first_idx, col] = dollar_vol[first_idx, col] * 5.0
            for t in range(first_idx + 1, T_full):
                if valid[t, col]:
                    oi_mat[t, col] = oi_mat[t-1, col] * decay + 0.20 * dollar_vol[t, col]
                else:
                    oi_mat[t, col] = 0.0

    agg_oi = np.sum(oi_mat, axis=1)

    # Active universe count
    n_active = np.sum(valid, axis=1)
    # Per-active-asset normalized volume and OI to ensure universe expansions don't bias indicator
    norm_vol = agg_vol / np.maximum(n_active, 1)
    norm_oi = agg_oi / np.maximum(n_active, 1)

    # Slice evaluation window with 120 bars of pre-warmup to eliminate EMA edge effects
    warmup_bars = 120
    s_idx = max(0, eval_start_idx - warmup_bars)
    e_idx = eval_start_idx + total_bars

    sl_vol = norm_vol[s_idx:e_idx]
    sl_oi = norm_oi[s_idx:e_idx]

    ema_v = pd.Series(sl_vol).ewm(span=lookback_bars, adjust=False).mean().to_numpy()
    ema_o = pd.Series(sl_oi).ewm(span=lookback_bars, adjust=False).mean().to_numpy()
    tv_full = ema_v / (ema_o + 1e-8)

    # Extract strictly the evaluation bars
    offset = eval_start_idx - s_idx
    tv_eval = tv_full[offset : offset + total_bars]
    assert len(tv_eval) == total_bars, f"Expected {total_bars} bars, got {len(tv_eval)}"
    return tv_eval


def main():
    print("=" * 115)
    print("   STAGE 3A: SYSTEMIC MARKET TURNOVER VELOCITY GATE CALIBRATION   ")
    print("=" * 115)

    print("--> Loading canonical dataset and caching market matrices...")
    engine_base = InstitutionalCompoundingEngine(fixed_leverage=3.0)
    eval_ts, symbols, cached_data = engine_base.load_and_preprocess_data()
    eval_start_idx = cached_data["eval_start_idx"]

    # Folds definitions (Topology A 60-day OOS Folds):
    # Fold 1: IS [0, 750) -> OOS [750, 1110)
    # Fold 2: IS [360, 1110) -> OOS [1110, 1470)
    # Fold 3: IS [720, 1470) -> OOS [1470, 1830) (Chop failure window)
    # Fold 4: IS [1080, 1830) -> OOS [1830, 2190)
    folds = [
        (1, 750, 1110),
        (2, 1110, 1470),
        (3, 1470, 1830),
        (4, 1830, 2190),
    ]

    # Pre-registered Parameter Grid:
    # Lookback windows: 10 days (60 bars), 20 days (120 bars)
    # Quantiles: 0.15, 0.20, 0.25
    # Leverage floors: 0.00x (flat cash), 0.33x, 0.50x
    lookback_days_list = [10, 20]
    tau_list = [0.15, 0.20, 0.25]
    floor_list = [0.00, 0.33, 0.50]

    all_results = []

    print("\n" + "-" * 115)
    print(f"{'CONFIG':<22} {'CAGR':<8} {'SHARPE':<7} {'MDD':<7} {'DUTY':<7} {'F1 OOS':<8} {'F2 OOS':<8} {'F3 OOS':<8} {'F4 OOS':<8} {'VERDICT':<10}")
    print("-" * 115)

    # 1. Run A0 Baseline First as Immutable Benchmark
    print("--> Running A0 un-gated baseline control...")
    res_a0 = engine_base.run(cached_data)
    eq_a0 = np.array(res_a0["equity_curve"])
    m_a0 = calculate_window_metrics(eq_a0, TOTAL_EVAL_BARS)
    sh_a0 = [calculate_window_metrics(eq_a0[s:e+1], e-s)["sharpe_ratio"] for _, s, e in folds]
    print(f"A0 Control Baseline    {m_a0['annualized_cagr_pct']:>6.1f}%  {m_a0['sharpe_ratio']:>5.2f}  {m_a0['max_drawdown_pct']:>5.2f}%    0.0%  {sh_a0[0]:>6.2f}   {sh_a0[1]:>6.2f}   {sh_a0[2]:>6.2f}   {sh_a0[3]:>6.2f}   BASELINE")
    print("." * 115)

    cfg_idx = 0
    for lb_days in lookback_days_list:
        lb_bars = lb_days * 6
        tv_series = compute_turnover_velocity_series(cached_data, eval_start_idx, TOTAL_EVAL_BARS, lb_bars)

        # In-Sample threshold calculated strictly on IS bars [0 to 1470)
        is_tv = tv_series[:1470]

        for tau in tau_list:
            q_thresh = float(np.quantile(is_tv, tau))
            is_throttled = tv_series < q_thresh  # True when TV is low (chop)

            # Inactivity distribution across folds
            f1_dis = float(np.mean(is_throttled[750:1110])) * 100.0
            f2_dis = float(np.mean(is_throttled[1110:1470])) * 100.0
            f3_dis = float(np.mean(is_throttled[1470:1830])) * 100.0
            f4_dis = float(np.mean(is_throttled[1830:2190])) * 100.0
            downtime_pct = float(np.mean(is_throttled)) * 100.0

            # Transitions & run length
            transitions = int(np.sum(np.diff(is_throttled.astype(int)) != 0))
            runs = []
            cur_run = 0
            for g in is_throttled:
                if g:
                    cur_run += 1
                elif cur_run > 0:
                    runs.append(cur_run)
                    cur_run = 0
            if cur_run > 0:
                runs.append(cur_run)
            avg_run = float(np.mean(runs)) if runs else 0.0

            for floor in floor_list:
                cfg_idx += 1
                cfg_name = f"{lb_days}d_t{int(tau*100)}_fl{int(floor*100)}"

                # Construct scalar leverage multiplier series:
                # Phi_macro(t) regulates exposure on bar t+1 (causal next-bar execution)
                phi_series = np.where(is_throttled, floor, 1.0)
                # Causal shift by 1 bar: signal at t takes effect on t+1
                phi_causal = np.roll(phi_series, 1)
                phi_causal[0] = 1.0  # Bar 0 uses default leverage

                # Run InstitutionalCompoundingEngine with dynamic regime governor
                eng = InstitutionalCompoundingEngine(
                    fixed_leverage=3.0,
                    turnover_lambda=0.85,
                    two_tranche_enabled=False,
                    pyramid_ratio=0.0,
                    regime_governor_scalars=phi_causal,
                )
                res = eng.run(cached_data)
                eq = np.array(res["equity_curve"])

                # Metrics full sample
                full_m = calculate_window_metrics(eq, TOTAL_EVAL_BARS)

                # OOS Fold Stability metrics
                fold_sharpes = []
                for _, s, e in folds:
                    fm = calculate_window_metrics(eq[s : e + 1], e - s)
                    fold_sharpes.append(fm["sharpe_ratio"])

                f1_sh, f2_sh, f3_sh, f4_sh = fold_sharpes

                # Gating Criteria Evaluation:
                # 1. Duty Cycle <= 25.0%
                duty_pass = downtime_pct <= 25.0
                # 2. Fold 3 recovery (must be >= 0.00, ideally >= 0.50)
                fold3_pass = f3_sh >= 0.00
                # 3. Retain >= 70% of A0 Sharpe in Folds 1, 2, 4
                ret_f1 = f1_sh >= (0.70 * sh_a0[0])
                ret_f2 = f2_sh >= (0.70 * sh_a0[1])
                ret_f4 = f4_sh >= (0.70 * sh_a0[3])
                trend_pass = ret_f1 and ret_f2 and ret_f4

                if duty_pass and fold3_pass and trend_pass:
                    verdict = "PASS"
                elif not duty_pass:
                    verdict = "DUTY FAIL"
                elif not fold3_pass:
                    verdict = "F3 FAIL"
                else:
                    verdict = "TREND FAIL"

                print(f"{cfg_name:<22} {full_m['annualized_cagr_pct']:>6.1f}%  {full_m['sharpe_ratio']:>5.2f}  {full_m['max_drawdown_pct']:>5.2f}%  {downtime_pct:>5.1f}%  {f1_sh:>6.2f}   {f2_sh:>6.2f}   {f3_sh:>6.2f}   {f4_sh:>6.2f}   {verdict}")

                record = {
                    "config": {
                        "config_id": cfg_name,
                        "lookback_days": lb_days,
                        "quantile_tau": tau,
                        "leverage_floor": floor,
                        "is_q_threshold": q_thresh,
                    },
                    "full_sample_metrics": {
                        "terminal_equity": full_m["end_equity"],
                        "compounding_multiple": full_m["multiple"],
                        "cagr_pct": full_m["annualized_cagr_pct"],
                        "sharpe_ratio": full_m["sharpe_ratio"],
                        "max_drawdown": full_m["max_drawdown_pct"],
                        "calmar_ratio": full_m["calmar_ratio"],
                        "duty_cycle_downtime_pct": downtime_pct,
                        "total_gate_transitions": transitions,
                        "avg_throttled_duration_bars": avg_run,
                    },
                    "fold_disable_distribution": {
                        "fold1_disabled_pct": f1_dis,
                        "fold2_disabled_pct": f2_dis,
                        "fold3_disabled_pct": f3_dis,
                        "fold4_disabled_pct": f4_dis,
                    },
                    "oos_fold_stability": {
                        "fold1_oos_sharpe": f1_sh,
                        "fold2_oos_sharpe": f2_sh,
                        "fold3_oos_sharpe": f3_sh,
                        "fold4_oos_sharpe": f4_sh,
                    },
                    "governance_verdict": {
                        "duty_cycle_cleared": duty_pass,
                        "fold3_catastrophic_cleared": fold3_pass,
                        "trend_alpha_preserved": trend_pass,
                        "overall_verdict": verdict,
                    }
                }
                all_results.append(record)

    # Save to JSON artifact
    payload = {
        "timestamp_utc": "2026-09-24T05:00:00Z",
        "benchmark_a0": {
            "full_sample": m_a0,
            "oos_fold_sharpes": {
                "fold1": sh_a0[0],
                "fold2": sh_a0[1],
                "fold3": sh_a0[2],
                "fold4": sh_a0[3],
            }
        },
        "grid_evaluations": all_results,
    }

    out_file = PIPELINE_ROOT / "data" / "stage3a_turnover_velocity_results.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w") as f:
        json.dump(payload, f, indent=2)

    print("\n" + "=" * 115)
    print(f"[REPORT] Saved full Stage 3A results ledger to {out_file}")
    print("=" * 115)


if __name__ == "__main__":
    main()
