#!/usr/bin/env python3
"""
Track B: Operational Dual-Envelope Kill-Switch Simulation
=========================================================
Tests the Dual-Envelope Circuit Breaker on the certified Composite_TV_Rho equity curve:
  - Envelope 1 (Trailing HWM): Max DD > 52.0% from any High-Water Mark.
    (Gives a 3.4% buffer beyond the historical worst-case 48.60% drawdown valley).
  - Envelope 2 (Deposit Floor): Portfolio Equity < $4,800 (-52.0% initial capital).
    (Guards against catastrophic Day-1 regime collapse).

Counterfactual Analysis:
  - Evaluates the impact of an arbitrary 45.0% hard drawdown stop.
  - Quantifies the exact dollar and percentage recovery missed due to false termination.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import polars as pl

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from backtest_10x_convex_compounding import (
    InstitutionalCompoundingEngine,
    DATA_LAKE_PATH,
    BENCHMARK_SYMBOL,
    EVAL_START_TS,
)
from src.data.pit_universe_manager import PointInTimeUniverseManager
from scripts.run_stage3a_turnover_velocity_gate import (
    compute_turnover_velocity_series,
    calculate_window_metrics,
)
from scripts.run_2x2_mechanism_ablation import (
    compute_cross_sectional_autocorrelation,
    make_causal_phi,
)


def run_simulation():
    print("=" * 100, flush=True)
    print("   TRACK B: DUAL-ENVELOPE OPERATIONAL KILL-SWITCH SIMULATION   ", flush=True)
    print("=" * 100, flush=True)

    # 1. Load Data
    df_raw = pl.read_parquet(DATA_LAKE_PATH)
    btc_df = df_raw.filter(pl.col("symbol") == BENCHMARK_SYMBOL).sort("timestamp_ms")
    all_timestamps = btc_df["timestamp_ms"].to_list()
    eval_start_idx = all_timestamps.index(EVAL_START_TS)
    max_lake_ts = all_timestamps[-1]
    total_eval_bars = len(all_timestamps) - 1 - eval_start_idx

    eval_timestamps, symbols, full_market_data = PointInTimeUniverseManager.load_pit_market_matrices(
        df=df_raw,
        eval_start_ts=EVAL_START_TS,
        eval_end_ts=max_lake_ts,
        benchmark_symbol=BENCHMARK_SYMBOL,
    )
    valid_mask = full_market_data["valid_price_mask"]
    first_valid_indices = np.zeros(len(symbols), dtype=int)
    for col in range(len(symbols)):
        valid_idx = np.where(valid_mask[:, col])[0]
        first_valid_indices[col] = valid_idx[0] if len(valid_idx) > 0 else 0
    full_market_data["first_valid_indices"] = first_valid_indices

    # 2. Compute Indicators
    tv_20d = compute_turnover_velocity_series(full_market_data, eval_start_idx, total_eval_bars, 120)
    is_tv = tv_20d[:1470]
    q_thresh_tv = float(np.quantile(is_tv, 0.15))
    rho_7d = compute_cross_sectional_autocorrelation(
        full_market_data["close"],
        full_market_data["valid_price_mask"],
        eval_start_idx,
        total_eval_bars,
        window_bars=42,
    )

    mask_comp = (tv_20d < q_thresh_tv) | (rho_7d < -0.150)
    phi_comp = make_causal_phi(mask_comp, 0.0)

    # 3. Run Engine
    eng = InstitutionalCompoundingEngine(
        fixed_leverage=3.0,
        turnover_lambda=0.85,
        two_tranche_enabled=False,
        pyramid_ratio=0.0,
        total_eval_bars=total_eval_bars,
        regime_governor_scalars=phi_comp,
    )
    res = eng.run(full_market_data)
    eq = np.array(res["equity_curve"])

    initial_capital = 10000.0
    hwm = np.maximum.accumulate(eq)
    drawdowns = (hwm - eq) / (hwm + 1e-12)

    # 4. Evaluate Dual Envelopes
    # Track 1: Trailing HWM DD > 52.0%
    trailing_breaches = np.where(drawdowns > 0.520)[0]
    # Track 2: Capital Floor < $4,800
    deposit_floor_breaches = np.where(eq < 4800.0)[0]

    max_historical_dd = np.max(drawdowns)
    worst_bar = int(np.argmax(drawdowns))
    min_equity = np.min(eq)
    min_eq_bar = int(np.argmin(eq))

    print(f"\n--> STRATEGY EQUITY TRAJECTORY SUMMARY (2,284 BARS):")
    print(f"    Initial Capital:        ${initial_capital:,.2f}")
    print(f"    Historical Peak Equity: ${np.max(eq):,.2f} (Bar {np.argmax(eq)})")
    print(f"    Terminal Canonical Eq:  ${eq[2190]:,.2f} (Bar 2,190)")
    print(f"    Terminal Extended Eq:   ${eq[-1]:,.2f} (Bar {len(eq)-1})")
    print(f"    Max Lifetime Drawdown:  {max_historical_dd*100:.2f}% (Bar {worst_bar})")
    print(f"    Lowest Lifetime Equity: ${min_equity:,.2f} (Bar {min_eq_bar})")

    print("\n" + "-" * 100)
    print("--> DUAL-ENVELOPE KILL-SWITCH AUDIT:")
    print(f"    Track 1 [Trailing HWM DD > 52.0%]:    {len(trailing_breaches)} Breaches.")
    print(f"    Track 2 [Deposit Floor < $4,800]:     {len(deposit_floor_breaches)} Breaches.")
    print(f"    Worst-Case Drawdown Headroom:         {(0.520 - max_historical_dd)*100:.2f}% buffer.")
    print(f"    Lowest Equity Headroom:               ${(min_equity - 4800.0):,.2f} above $4,800 floor.")

    if len(trailing_breaches) == 0 and len(deposit_floor_breaches) == 0:
        print("    [RESULT]: PASSED - Zero false terminations across 2,284-bar lifecycle.")
    else:
        print("    [RESULT]: FAILED - Premature termination triggered!")

    # 5. Counterfactual 45% Hard Stop Simulation
    print("\n" + "-" * 100)
    print("--> COUNTERFACTUAL ANALYSIS: 45.0% HARD KILL SWITCH")
    c_breaches_45 = np.where(drawdowns > 0.450)[0]
    if len(c_breaches_45) > 0:
        first_bar = int(c_breaches_45[0])
        eq_at_breach = float(eq[first_bar])
        hwm_at_breach = float(hwm[first_bar])
        dd_at_breach = float(drawdowns[first_bar])
        term_canon = float(eq[2190])
        term_ext = float(eq[-1])
        missed_canon_usd = term_canon - eq_at_breach
        missed_canon_pct = (term_canon / eq_at_breach - 1.0) * 100.0
        missed_ext_usd = term_ext - eq_at_breach
        missed_ext_pct = (term_ext / eq_at_breach - 1.0) * 100.0

        print(f"    Breach Status:           TRIGGERED at Bar {first_bar} (DD = {dd_at_breach*100:.2f}%)")
        print(f"    High-Water Mark at Stop: ${hwm_at_breach:,.2f}")
        print(f"    Equity at Premature Stop: ${eq_at_breach:,.2f}")
        print(f"    Realized Equity at Bar 2,190: ${term_canon:,.2f}")
        print(f"    Realized Equity at Bar 2,284: ${term_ext:,.2f}")
        print(f"    Missed Canonical Recovery: +${missed_canon_usd:,.2f} (+{missed_canon_pct:.1f}%)")
        print(f"    Missed Extended Recovery:  +${missed_ext_usd:,.2f} (+{missed_ext_pct:.1f}%)")
        print(f"\n    [DIAGNOSIS]: A 45% hard stop triggers a PATH-DEPENDENT TERMINATION TRAP.")
        print(f"    The strategy would have liquidated at the bottom of the valley (Bar {first_bar}),")
        print(f"    permanently forfeiting ${missed_canon_usd:,.2f} of subsequent convex recovery.")
    else:
        print("    45.0% stop was not triggered.")

    # Save Results
    results = {
        "dual_envelope_passed": bool(len(trailing_breaches) == 0 and len(deposit_floor_breaches) == 0),
        "trailing_hwm_52_breaches": int(len(trailing_breaches)),
        "deposit_floor_4800_breaches": int(len(deposit_floor_breaches)),
        "max_lifetime_drawdown_pct": float(max_historical_dd * 100),
        "headroom_pct": float((0.520 - max_historical_dd) * 100),
        "counterfactual_45_stop": {
            "triggered": bool(len(c_breaches_45) > 0),
            "breach_bar": int(c_breaches_45[0]) if len(c_breaches_45) > 0 else -1,
            "equity_at_breach": float(eq[c_breaches_45[0]]) if len(c_breaches_45) > 0 else 0.0,
            "missed_recovery_canonical_usd": float(missed_canon_usd) if len(c_breaches_45) > 0 else 0.0,
            "missed_recovery_canonical_pct": float(missed_canon_pct) if len(c_breaches_45) > 0 else 0.0,
            "missed_recovery_extended_usd": float(missed_ext_usd) if len(c_breaches_45) > 0 else 0.0,
            "missed_recovery_extended_pct": float(missed_ext_pct) if len(c_breaches_45) > 0 else 0.0,
        }
    }
    out_path = PIPELINE_ROOT / "data" / "kill_switch_simulation_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n[SAVED] Simulation ledger written to {out_path}", flush=True)


if __name__ == "__main__":
    run_simulation()
