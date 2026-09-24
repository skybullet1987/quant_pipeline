#!/usr/bin/env python3
"""
Gate 2: Empirical Telemetry Batch Auditor
=========================================
Audits execution receipts in data/papertrade_journal.jsonl against Gate 2 standards:
  - Sample target: N >= 500 fills across all liquidity tiers and sides
  - Gate 1: Median Implementation Shortfall (P50) <= 6.0 bps
  - Gate 2: 90th Percentile Shortfall (P90) <= 18.0 bps
  - Gate 3: 95th Percentile Shortfall (P95) <= 25.0 bps
  - Gate 4: Maker Fill Ratio (Resting AS-ALO) >= 65.0%
  - Gate 5: Side Balance (Long >= 35%, Short >= 35%)
  - Gate 6: Unfilled Breakout Abandonment Ratio <= 15.0%
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
JOURNAL_PATH = PIPELINE_ROOT / "data" / "papertrade_journal.jsonl"
STATE_PATH = PIPELINE_ROOT / "data" / "papertrade_state.json"


def audit_telemetry():
    print("=" * 105)
    print("   GATE 2: EMPIRICAL EXECUTION TELEMETRY BATCH AUDITOR   ")
    print("   Environment: europe-west3 hyperliquid-paper daemon | Target: N >= 500 Fills")
    print("=" * 105)

    if not JOURNAL_PATH.exists():
        print(f"[ERROR] Journal file not found at {JOURNAL_PATH}")
        sys.exit(1)

    audit_records = []
    total_signals = 0
    unfilled_breakouts = 0

    with open(JOURNAL_PATH, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
                ev_type = ev.get("event_type")
                if ev_type == "IMPLEMENTATION_AUDIT_RECORD":
                    audit_records.append(ev.get("payload", {}))
                elif ev_type == "TARGET_FROZEN":
                    weights = ev.get("payload", {}).get("target_weights", {})
                    total_signals += len([w for w in weights.values() if abs(w) > 0.001])
                elif ev_type == "UNFILLED_BREAKOUT_ABANDONED":
                    unfilled_breakouts += 1
            except Exception:
                continue

    n_total = len(audit_records)
    print(f"\n--> DATA LAKE RECEIPT SUMMARY:")
    print(f"    Total Recorded Implementation Audit Fills: {n_total} / 500 ({n_total / 500.0 * 100:.1f}% Attainment)")
    print(f"    Total Frozen Target Signals:               {total_signals}")
    print(f"    Total Unfilled Breakout Abandonments:      {unfilled_breakouts}")

    # Inspect current state cache
    if STATE_PATH.exists():
        try:
            with open(STATE_PATH, "r") as f:
                state = json.load(f)
            eq = state.get("equity", {})
            cad = state.get("cadence", {})
            print(f"    Current Daemon Strategy NAV:               ${eq.get('current_strategy_equity', 0.0):,.2f} USDC")
            print(f"    Historical High-Water Mark:                ${eq.get('historical_hwm', 0.0):,.2f} USDC")
            print(f"    Current Drawdown from HWM:                 {eq.get('drawdown_pct', 0.0):.2f}% (Limit: 52.0%)")
            print(f"    Cadence Progress:                          Bar {cad.get('bars_since_macro', 0)}/18 toward Macro Rebalance")
        except Exception:
            pass

    if n_total == 0:
        print("\n[STATUS]: INSUFFICIENT DATA - Waiting for active execution fills to accumulate.")
        print("          Daemon is running in the background and logging receipts on each 4H cadence.\n")
        return

    # Evaluate Rolling Window (last 100 fills or all if < 100)
    window = audit_records[-100:]
    n_win = len(window)

    shortfalls = np.array([float(r.get("total_shortfall_bps", 0.0)) for r in window])
    p50 = float(np.percentile(shortfalls, 50))
    p90 = float(np.percentile(shortfalls, 90))
    p95 = float(np.percentile(shortfalls, 95))

    n_maker = sum(1 for r in window if "RESTING_ALO" in str(r.get("order_type", "")).upper())
    maker_ratio = (n_maker / n_win) * 100.0

    n_buy = sum(1 for r in window if str(r.get("side", "")).upper() in ["BUY", "LONG"])
    n_sell = n_win - n_buy
    buy_ratio = (n_buy / n_win) * 100.0
    sell_ratio = (n_sell / n_win) * 100.0

    denom_sig = max(total_signals, n_win)
    unfilled_ratio = (unfilled_breakouts / denom_sig) * 100.0 if denom_sig > 0 else 0.0

    # Gate verification
    gates = [
        ("Median Shortfall (P50)", f"{p50:.2f} bps", "<= 6.0 bps", p50 <= 6.0, "Review Quote Sizing"),
        ("90th Percentile Shortfall (P90)", f"{p90:.2f} bps", "<= 18.0 bps", p90 <= 18.0, "Spread Widening Alert"),
        ("95th Percentile Shortfall (P95)", f"{p95:.2f} bps", "<= 25.0 bps", p95 <= 25.0, "Execution Throttle"),
        ("Maker Fill Ratio (Resting ALO)", f"{maker_ratio:.1f}%", ">= 65.0%", maker_ratio >= 65.0, "Algorithmic Reroute"),
        ("Side Balance (Long Ratio)", f"{buy_ratio:.1f}%", ">= 35.0%", buy_ratio >= 35.0, "Universe Bias Audit"),
        ("Side Balance (Short Ratio)", f"{sell_ratio:.1f}%", ">= 35.0%", sell_ratio >= 35.0, "Universe Bias Audit"),
        ("Unfilled Breakout Abandonment", f"{unfilled_ratio:.1f}%", "<= 15.0%", unfilled_ratio <= 15.0, "Adverse Selection Flag"),
    ]

    print("\n" + "-" * 105)
    print(f"{'DISTRIBUTIONAL METRIC':<35} {'OBSERVED (N=' + str(n_win) + ')':<20} {'GATE THRESHOLD':<18} {'STATUS':<10} {'VIOLATION ACTION'}")
    print("-" * 105)
    all_passed = True
    for name, obs, thresh, passed, action in gates:
        status_str = "PASS" if passed else "ALERT"
        if not passed:
            all_passed = False
        print(f"{name:<35} {obs:<20} {thresh:<18} {status_str:<10} {action if not passed else '-'}")
    print("-" * 105)

    if n_total < 500:
        print(f"\n--> GATE 2 STATUS: IN PROGRESS ({n_total}/500 Fills Accumulated - {500 - n_total} remaining).")
    elif all_passed:
        print(f"\n--> GATE 2 STATUS: CERTIFIED PASSED (N={n_total} >= 500 Fills; All Distributional Gates Met)!")
    else:
        print(f"\n--> GATE 2 STATUS: GATES BREACHED - Review actions before Gate 3 transition.")
    print("=" * 105 + "\n")


if __name__ == "__main__":
    audit_telemetry()
