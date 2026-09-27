#!/usr/bin/env python3
import glob
import pandas as pd
import numpy as np

files = sorted(glob.glob("oos_decisions_*.parquet"))
if not files:
    print("[ERROR] No oos_decisions_*.parquet found.")
    exit(1)

latest = files[-1]
print(f"\nReading {latest}...")
df = pd.read_parquet(latest)

print(f"Total Evaluated Rows: {len(df):,}")
print("All Parquet Columns:", list(df.columns))

# Filter Executed Trades
executed = df[df['final_decision'] == 'EXECUTED'].copy()
print(f"\nTotal Executed Trades: {len(executed):,}")
print(f"Executed Direction Breakdown:\n{executed['selected_direction'].value_counts()}")
print(f"\nExecuted Regime Breakdown:\n{executed['regime'].value_counts()}")

# Cross-tabulate Regime vs Direction for Executed Trades
print("\n" + "=" * 80)
print("             1. EXECUTED TRADES: REGIME vs SELECTED DIRECTION")
print("=" * 80)
ct = pd.crosstab(executed['regime'], executed['selected_direction'], margins=True)
print(ct)

# Cross-tabulate Rejections by Regime
print("\n" + "=" * 80)
print("             2. CANDIDATE GATING & REJECTIONS BY REGIME")
print("=" * 80)
gating_ct = pd.crosstab(df['regime'], df['rejection_reason'], margins=True)
print(gating_ct.T)

# Confidence & EV by Selected Direction
print("\n" + "=" * 80)
print("             3. AVERAGE PROBABILITIES & EV BY DIRECTION")
print("=" * 80)
stats = executed.groupby('selected_direction').agg(
    count=('p_long', 'count'),
    mean_p_long=('p_long', 'mean'),
    mean_p_short=('p_short', 'mean'),
    mean_p_chop=('p_chop', 'mean'),
    mean_long_ev=('long_ev_bps', 'mean'),
    mean_short_ev=('short_ev_bps', 'mean'),
    mean_kelly=('kelly_fraction', 'mean'),
    mean_position_usd=('position_size_usd', 'mean')
)
print(stats.to_string())
print("=" * 80 + "\n")
