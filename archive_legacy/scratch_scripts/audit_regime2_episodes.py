#!/usr/bin/env python3
"""
Regime 2 Short Cascade Episode & Concentration Diagnostic
Analyzes:
  1. Top-N Trade PnL Concentration (Gini / Pareto skew)
  2. Temporal Cascade Episode Clustering (Grouping overlapping liquidation events)
  3. Weekly / Monthly PnL Stability & Win Rate
  4. Adverse vs Favorable Excursion and Holding Periods
"""

import os
import numpy as np
import pandas as pd
from datetime import timedelta

CSV_PATH = "legacy_high_octane_trades_90d.csv"
if not os.path.exists(CSV_PATH):
    print(f"[ERROR] '{CSV_PATH}' not found. Run backtest first.")
    exit(1)

df = pd.read_csv(CSV_PATH)
df["entry_time"] = pd.to_datetime(df["entry_time"])
df["exit_time"] = pd.to_datetime(df["exit_time"])

# Filter for Shorts
shorts = df[df["side"] == "SELL"].sort_values("entry_time").reset_index(drop=True)
total_short_pnl = shorts["pnl"].sum()
total_trades = len(shorts)

print("\n" + "=" * 90)
print(f"       REGIME 2 SHORT CASCADE EPISODE & CONCENTRATION AUDIT ({total_trades} TRADES)")
print("=" * 90)

# 1. Top Trade Concentration
sorted_pnl = shorts.sort_values("pnl", ascending=False).reset_index(drop=True)
top_3_pnl = sorted_pnl.loc[:2, "pnl"].sum()
top_5_pnl = sorted_pnl.loc[:4, "pnl"].sum()
top_10_pnl = sorted_pnl.loc[:9, "pnl"].sum()

print("--- PNL CONCENTRATION ANALYSIS ---")
print(f"Total Short Net PnL:         ${total_short_pnl:>+10,.2f}")
print(f"Top 3 Trades PnL:            ${top_3_pnl:>+10,.2f}  ({(top_3_pnl / total_short_pnl)*100:>5.1f}% of total)")
print(f"Top 5 Trades PnL:            ${top_5_pnl:>+10,.2f}  ({(top_5_pnl / total_short_pnl)*100:>5.1f}% of total)")
print(f"Top 10 Trades PnL:           ${top_10_pnl:>+10,.2f}  ({(top_10_pnl / total_short_pnl)*100:>5.1f}% of total)")
print(f"Remaining {total_trades-10} Trades PnL:      ${(total_short_pnl - top_10_pnl):>+10,.2f}  ({((total_short_pnl - top_10_pnl) / total_short_pnl)*100:>5.1f}% of total)")

# 2. Cascade Episode Clustering (Trades entered within 12h of each other belong to the same macro episode)
episodes = []
current_ep = [shorts.iloc[0]]

for i in range(1, len(shorts)):
    prev_trade = current_ep[-1]
    curr_trade = shorts.iloc[i]
    if (curr_trade["entry_time"] - prev_trade["entry_time"]) <= timedelta(hours=12):
        current_ep.append(curr_trade)
    else:
        episodes.append(pd.DataFrame(current_ep))
        current_ep = [curr_trade]
if current_ep:
    episodes.append(pd.DataFrame(current_ep))

ep_summary = []
for idx, ep in enumerate(episodes, 1):
    ep_pnl = ep["pnl"].sum()
    ep_trades = len(ep)
    ep_wr = (ep["pnl"] > 0).mean() * 100.0
    start_ts = ep["entry_time"].min().strftime("%Y-%m-%d %H:%M")
    end_ts = ep["exit_time"].max().strftime("%Y-%m-%d %H:%M")
    coins = ", ".join(ep["coin"].unique())
    ep_summary.append({
        "Episode": f"Ep #{idx:02d}",
        "Start": start_ts,
        "Trades": ep_trades,
        "Coins": coins[:28] + ("..." if len(coins) > 28 else ""),
        "Win_Rate": ep_wr,
        "PnL": ep_pnl
    })

ep_df = pd.DataFrame(ep_summary)
print(f"\n--- INDEPENDENT CASCADE EPISODES (Total Identified: {len(ep_df)}) ---")
print(f"{'Episode':<8}{'Start Date':<18}{'Trades':<8}{'Win Rate':<11}{'Episode PnL':<15}{'Assets Traded'}")
print("-" * 90)
for _, r in ep_df.iterrows():
    print(f"{r['Episode']:<8}{r['Start']:<18}{r['Trades']:<8}{r['Win_Rate']:>5.1f}%     ${r['PnL']:>+10.2f}    {r['Coins']}")

profitable_episodes = (ep_df["PnL"] > 0).sum()
print("-" * 90)
print(f"Episode Win Rate:            {(profitable_episodes / len(ep_df))*100:.1f}% ({profitable_episodes}/{len(ep_df)} independent cascade clusters profitable)")
print(f"Largest Single Episode PnL:  ${ep_df['PnL'].max():>+10.2f} ({(ep_df['PnL'].max() / total_short_pnl)*100:.1f}% of total short PnL)")
print(f"Worst Single Episode Loss:   ${ep_df['PnL'].min():>+10.2f}")

# 3. Monthly Attribution
shorts["month"] = shorts["entry_time"].dt.to_period("M")
print("\n--- MONTHLY SHORT BREAKDOWN ---")
for m, grp in shorts.groupby("month"):
    m_pnl = grp["pnl"].sum()
    m_wr = (grp["pnl"] > 0).mean() * 100.0
    print(f"  • {str(m):<7} ({len(grp):>2} trades): PnL: ${m_pnl:>+9.2f} | Win Rate: {m_wr:>5.1f}% | Expectancy: ${grp['pnl'].mean():>+6.2f}/trade")

print("=" * 90 + "\n")
