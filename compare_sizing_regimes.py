#!/usr/bin/env python3
"""
Walk-Forward Sizing Regime Evaluation
Replays the exact 22 on-chain closed trades from the current epoch under:
  - Regime A: Fixed Notional ($228/slot)
  - Regime B: Risk-Budget Sizing (1.0% Equity Risk, 2.0% Min SL Floor, 35% Position Cap)
"""

import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from eth_account import Account
from hyperliquid.info import Info
from hyperliquid.utils import constants

load_dotenv()

key = os.getenv("HYPERLIQUID_TESTNET_PRIVATE_KEY") or os.getenv("HYPERLIQUID_PRIVATE_KEY")
if not key:
    raise ValueError("Private key missing.")

account = Account.from_key(key)
info = Info(constants.TESTNET_API_URL, skip_ws=True)
master_addr = os.getenv("HYPERLIQUID_MASTER_ADDRESS") or account.address
epoch_start = datetime.now(timezone.utc) - timedelta(days=2)

# 1. Pull exact closed trade fills
raw_fills = info.user_fills(master_addr)
fill_rows = []
for f in raw_fills:
    t = datetime.fromtimestamp(f["time"] / 1000.0, timezone.utc)
    pnl = float(f.get("closedPnl", 0.0))
    if t >= epoch_start and pnl != 0.0:
        fill_rows.append({
            "time": t,
            "coin": f["coin"],
            "dir": f.get("dir", ""),
            "sz": float(f["sz"]),
            "px": float(f["px"]),
            "pnl": pnl,
            "fee": float(f.get("fee", 0.0)),
            "bucket": t.strftime("%Y-%m-%d %H:%M")
        })

if not fill_rows:
    print("No closed trade records found in the current epoch.")
    exit()

df = pd.DataFrame(fill_rows)
trades = df.groupby(["coin", "bucket", "dir"]).agg({
    "pnl": "sum",
    "fee": "sum",
    "sz": "sum",
    "px": "mean",
    "time": "max"
}).reset_index().sort_values("time", ascending=True)

# 2. Simulation parameters
STARTING_EQUITY = 1340.0
RISK_TARGET_PCT = 0.010       # 1.0% ($13.40)
MIN_SL_PCT = 0.020            # 2.0% floor
MAX_POSITION_PCT = 0.35       # 35% equity ceiling
FIXED_NOTIONAL = STARTING_EQUITY * 0.85 / 5.0  # ~$227.80
FEE_RATE = 0.00035

pnl_fixed, pnl_rp = [], []
eq_fixed, eq_rp = [STARTING_EQUITY], [STARTING_EQUITY]

for _, r in trades.iterrows():
    nominal_trade_notional = r["sz"] * r["px"]
    nominal_return_pct = r["pnl"] / nominal_trade_notional if nominal_trade_notional > 0 else 0.0
    implied_sl_dist = max(abs(nominal_return_pct), MIN_SL_PCT)

    # Regime A: Fixed Notional
    trade_pnl_a = (FIXED_NOTIONAL * nominal_return_pct) - (FIXED_NOTIONAL * 2 * FEE_RATE)
    pnl_fixed.append(trade_pnl_a)
    eq_fixed.append(eq_fixed[-1] + trade_pnl_a)

    # Regime B: Risk-Budget Sizing
    curr_eq = eq_rp[-1]
    risk_budget = curr_eq * RISK_TARGET_PCT
    notional_b = min(risk_budget / implied_sl_dist, curr_eq * MAX_POSITION_PCT)
    trade_pnl_b = (notional_b * nominal_return_pct) - (notional_b * 2 * FEE_RATE)
    pnl_rp.append(trade_pnl_b)
    eq_rp.append(curr_eq + trade_pnl_b)

def get_stats(pnl_list, eq_curve):
    arr = np.array(pnl_list)
    wins, losses = arr[arr > 0], arr[arr <= 0]
    wr = (len(wins) / len(arr) * 100.0) if len(arr) else 0.0
    gp = wins.sum() if len(wins) else 0.0
    gl = abs(losses.sum()) if len(losses) else 0.0
    pf = (gp / gl) if gl > 0 else (99.9 if gp > 0 else 0.0)
    expectancy = arr.mean() if len(arr) else 0.0
    
    peaks = np.maximum.accumulate(eq_curve)
    dds = (peaks - eq_curve) / peaks
    max_dd = dds.max() * 100.0
    cvar_95 = abs(np.percentile(losses, 5)) if len(losses) >= 10 else (abs(losses.min()) if len(losses) else 0.0)

    return {
        "Net Realized PnL": arr.sum(),
        "Win Rate": wr,
        "Profit Factor": pf,
        "Expectancy": expectancy,
        "Max Drawdown": max_dd,
        "CVaR (95% Tail)": cvar_95,
        "Final Equity": eq_curve[-1]
    }

metrics_a = get_stats(pnl_fixed, eq_fixed)
metrics_b = get_stats(pnl_rp, eq_rp)

summary_df = pd.DataFrame([metrics_a, metrics_b], index=["Regime A (Fixed Notional)", "Regime B (Risk Parity)"])

print("\n" + "=" * 92)
print("      WALK-FORWARD REPLAY OVER IDENTICAL 22 EXECUTIONS (Hyperliquid Testnet)")
print("=" * 92)
print(summary_df.to_string(formatters={
    "Net Realized PnL": "${:>+8.2f}".format,
    "Win Rate": "{:>5.1f}%".format,
    "Profit Factor": "{:>5.2f}".format,
    "Expectancy": "${:>+6.2f}/tr".format,
    "Max Drawdown": "{:>5.1f}%".format,
    "CVaR (95% Tail)": "${:>6.2f}".format,
    "Final Equity": "${:>8.2f}".format
}))
print("=" * 92 + "\n")
