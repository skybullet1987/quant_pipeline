#!/usr/bin/env python3
"""
PM-HWR-001B: Adversarial Simulation Audit of EXP-303 Policy B2
=============================================================
Forensic audit of the reported 100% win rate in EXP-303 Policy B2 (shadow_fast_unwind_ledger.jsonl).
Exposes the counterfactual assumptions and simulates realistic adverse scenarios:
  1. Original Simulator: Unconditional fill assumption at entry + theta.
  2. Adverse Scenario A: Loss resolution (won=False) forfeits principal at 0.00 without stop.
  3. Adverse Scenario B: Loss resolution caught by spot-delta stop-loss (~0.58 exit).
  4. Adverse Scenario C: Partial queue fill / missed maker execution.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

DATA_DIR = Path("data/polymarket")
OUTPUT_DIR = Path("data/pm_hwr_001")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SHADOW_LEDGER = DATA_DIR / "shadow_fast_unwind_ledger.jsonl"
VALIDATION_LEDGER = DATA_DIR / "paper_trading_validation_ledger.jsonl"


def run_exp303_adversarial_audit() -> Dict[str, Any]:
    with open(SHADOW_LEDGER, "r") as f:
        shadow_records = [json.loads(line) for line in f if line.strip()]

    with open(VALIDATION_LEDGER, "r") as f:
        val_records = {json.loads(line)["trade_id"]: json.loads(line) for line in f if line.strip()}

    n_total = len(shadow_records)
    print(f"Loaded {n_total} records from shadow_fast_unwind_ledger.jsonl.")

    # 1. Inspect Original Policy B2
    orig_b2_wins = sum(1 for r in shadow_records if r["policy_b2"]["net_pnl_usd"] > 0)
    orig_b2_pnl = sum(r["policy_b2"]["net_pnl_usd"] for r in shadow_records)
    orig_b2_losses = sum(1 for r in shadow_records if r["policy_b2"]["net_pnl_usd"] <= 0)

    # 2. Check resolution labels from validation ledger
    won_count = 0
    lost_count = 0
    for r in shadow_records:
        tid = r["trade_id"]
        v = val_records.get(tid, {})
        if v.get("won") is True:
            won_count += 1
        elif v.get("won") is False:
            lost_count += 1

    # 3. Model 1: Adversarial Reality without Stop-Loss (Hold to 0.00 on losing candles)
    # If the contract lost at expiry (won == False), assume it suffered a full wipeout (-notional - entry_fee)
    m1_pnls = []
    m1_wins = 0
    m1_losses = 0
    for r in shadow_records:
        tid = r["trade_id"]
        v = val_records.get(tid, {})
        won = v.get("won", False)
        if won:
            pnl = r["policy_b2"]["net_pnl_usd"]
            m1_pnls.append(pnl)
            m1_wins += 1
        else:
            notional = r["notional_usd"]
            entry_fee = r["entry_fee_usd"]
            loss_pnl = -(notional + entry_fee)
            m1_pnls.append(loss_pnl)
            m1_losses += 1

    # 4. Model 2: Adversarial Reality WITH Spot-Delta Stop-Loss Unwind (~0.58 CLOB exit)
    m2_pnls = []
    m2_wins = 0
    m2_losses = 0
    for r in shadow_records:
        tid = r["trade_id"]
        v = val_records.get(tid, {})
        won = v.get("won", False)
        if won:
            pnl = r["policy_b2"]["net_pnl_usd"]
            m2_pnls.append(pnl)
            m2_wins += 1
        else:
            # Stopped out at 0.58 CLOB bid (salvages ~72% of capital)
            shares = r["shares"]
            notional = r["notional_usd"]
            entry_fee = r["entry_fee_usd"]
            salvage_cash = shares * 0.58
            stop_pnl = round(salvage_cash - notional - entry_fee, 2)
            m2_pnls.append(stop_pnl)
            m2_losses += 1

    # 5. Model 3: Adverse Selection + Queue Miss (15% of winning maker asks fail to fill before price turns)
    m3_pnls = []
    m3_wins = 0
    m3_losses = 0
    for i, r in enumerate(shadow_records):
        tid = r["trade_id"]
        v = val_records.get(tid, {})
        won = v.get("won", False)
        if won:
            # 85% maker fill, 15% missed maker order that falls back to taker or expiry
            if i % 7 == 0:  # ~14.3% missed maker
                # Falls back to taker exit with fee
                pnl = r["policy_b1"]["net_pnl_usd"]
            else:
                pnl = r["policy_b2"]["net_pnl_usd"]
            m3_pnls.append(pnl)
            m3_wins += 1
        else:
            shares = r["shares"]
            notional = r["notional_usd"]
            entry_fee = r["entry_fee_usd"]
            salvage_cash = shares * 0.58
            stop_pnl = round(salvage_cash - notional - entry_fee, 2)
            m3_pnls.append(stop_pnl)
            m3_losses += 1

    audit_summary = {
        "audit_name": "EXP-303_ADVERSARIAL_SIMULATION_AUDIT",
        "sample_size": n_total,
        "underlying_ground_truth": {
            "settled_winning_events": won_count,
            "settled_losing_events": lost_count,
            "actual_settlement_accuracy_pct": round(won_count / n_total * 100, 2),
        },
        "simulation_models": {
            "original_exp303_policy_b2": {
                "description": "Original counterfactual simulation in shadow_fast_unwind_ledger.jsonl",
                "flaw_identified": "Unconditionally assigned exit_price = entry_px + 0.10 regardless of market outcome (won=True or False)",
                "wins": orig_b2_wins,
                "losses": orig_b2_losses,
                "win_rate_pct": round(orig_b2_wins / n_total * 100, 2),
                "total_net_pnl": round(orig_b2_pnl, 2),
                "ev_per_trade": round(orig_b2_pnl / n_total, 2),
                "max_drawdown": 0.0,
            },
            "adversarial_model_1_unconditional_loss": {
                "description": "Losing candles (won=False) held to expiry wipeout ($0.00) without stop-loss",
                "wins": m1_wins,
                "losses": m1_losses,
                "win_rate_pct": round(m1_wins / n_total * 100, 2),
                "total_net_pnl": round(sum(m1_pnls), 2),
                "ev_per_trade": round(sum(m1_pnls) / n_total, 2),
                "avg_win": round(sum(p for p in m1_pnls if p > 0) / m1_wins, 2),
                "avg_loss": round(sum(p for p in m1_pnls if p < 0) / m1_losses, 2),
            },
            "adversarial_model_2_with_spot_delta_stop": {
                "description": "Losing candles caught by Policy B2 Spot-Delta Stop-Loss (unwind @ 0.58)",
                "wins": m2_wins,
                "losses": m2_losses,
                "win_rate_pct": round(m2_wins / n_total * 100, 2),
                "total_net_pnl": round(sum(m2_pnls), 2),
                "ev_per_trade": round(sum(m2_pnls) / n_total, 2),
                "avg_win": round(sum(p for p in m2_pnls if p > 0) / m2_wins, 2),
                "avg_loss": round(sum(p for p in m2_pnls if p < 0) / m2_losses, 2),
            },
            "adversarial_model_3_queue_friction_and_stop": {
                "description": "Realistic queue friction (14% missed maker scalp fallback to taker) + spot-delta stop",
                "wins": m3_wins,
                "losses": m3_losses,
                "win_rate_pct": round(m3_wins / n_total * 100, 2),
                "total_net_pnl": round(sum(m3_pnls), 2),
                "ev_per_trade": round(sum(m3_pnls) / n_total, 2),
                "avg_win": round(sum(p for p in m3_pnls if p > 0) / m3_wins, 2),
                "avg_loss": round(sum(p for p in m3_pnls if p < 0) / m3_losses, 2),
            },
        },
    }

    out_file = OUTPUT_DIR / "exp303_adversarial_audit_report.json"
    with open(out_file, "w") as f:
        json.dump(audit_summary, f, indent=2)

    print(f"✓ Saved Adversarial Audit Report to: {out_file}\n")
    print(f"{'Simulation Model':<35} | {'Win Rate':<10} | {'Wins':<6} | {'Losses':<8} | {'Net PnL':<12} | {'EV / Trade':<10}")
    print("-" * 92)
    for k, v in audit_summary["simulation_models"].items():
        print(f"{k:<35} | {v['win_rate_pct']:<9.1f}% | {v['wins']:<6} | {v['losses']:<8} | ${v['total_net_pnl']:<11.2f} | ${v['ev_per_trade']:<10.2f}")

    return audit_summary


if __name__ == "__main__":
    run_exp303_adversarial_audit()
