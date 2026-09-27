"""
Diagnostic Harness for Decoupled Asymmetric TBM Classifiers.
Evaluates Top-Decile Long Expectancy and Short Breakdown Expectancy.
"""
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd
import polars as pl

from src.models.asymmetric_tbm_engine import generate_asymmetric_tbm_alphas

print("1. Ingesting Top-50 Liquid Universe...")
raw_df = pl.read_parquet("/tmp/lake/features/pit_panel_4h.parquet")

top_50 = (
    raw_df.group_by("symbol")
    .agg((pl.col("volume") * pl.col("close")).mean().alias("dvol"))
    .sort("dvol", descending=True)
    .head(50)["symbol"]
    .to_list()
)

df = raw_df.filter(pl.col("symbol").is_in(top_50)).unique(["symbol", "bucket_timestamp_utc"]).sort("bucket_timestamp_utc")

print("2. Generating Decoupled Asymmetric TBM Probabilities...")
alpha_matrix = generate_asymmetric_tbm_alphas(df)

# Forward 72H return check
pdf_eval = (
    df.sort(["symbol", "bucket_timestamp_utc"])
    .with_columns([
        pl.col("close").pct_change(18).shift(-18).over("symbol").alias("fwd_ret_72h")
    ])
    .to_pandas()
)
pdf_eval["ts_utc"] = pd.to_datetime(pdf_eval["bucket_timestamp_utc"], utc=True)
fwd_piv = pdf_eval.pivot(index="ts_utc", columns="symbol", values="fwd_ret_72h").fillna(0.0)

timestamps = alpha_matrix.index.intersection(fwd_piv.index)
sample_times = timestamps[2160::18]

long_expectancies = []
short_expectancies = []
spreads = []

for t in sample_times:
    alphas = alpha_matrix.loc[t]
    fwds = fwd_piv.loc[t]
    
    valid_syms = alphas[alphas != 0.0].index.intersection(fwds[fwds != 0.0].index)
    if len(valid_syms) < 10:
        continue
        
    sorted_syms = alphas[valid_syms].sort_values(ascending=False)
    
    top_longs = sorted_syms.head(4).index
    top_shorts = sorted_syms.tail(4).index
    
    l_ret = fwds[top_longs].mean()
    s_ret = -fwds[top_shorts].mean()
    
    long_expectancies.append(l_ret)
    short_expectancies.append(s_ret)
    spreads.append(l_ret + s_ret)

spreads = np.array(spreads)
l_exp = np.array(long_expectancies)
s_exp = np.array(short_expectancies)

net_spreads = spreads - 0.0007  # Deduct 7.0 bps taker fee
cum_pnl = np.cumprod(1.0 + net_spreads * 1.5)

print("\n" + "=" * 70)
print("     ASYMMETRIC TARGET BARRIER (TBM) EXPECTANCY RESULTS")
print("=" * 70)
print(f"Total Rebalance Trades Evaluated: {len(spreads):8d}")
print(f"Long Basket Mean Return (72H):   {np.mean(l_exp) * 10000:+8.1f} bps")
print(f"Short Basket Mean Return (72H):  {np.mean(s_exp) * 10000:+8.1f} bps")
print(f"Gross Long/Short Spread per Trade:{np.mean(spreads) * 10000:+8.1f} bps")
print(f"Net L/S Spread (After 7 bps Fee): {np.mean(net_spreads) * 10000:+8.1f} bps")
print(f"Strategy Win Rate:                {(net_spreads > 0).mean() * 100:7.2f}%")
print(f"Annualized Sharpe Ratio:          {(np.mean(net_spreads) / (np.std(net_spreads) + 1e-6)) * np.sqrt(365 * 24 / 72):8.2f}")
print("-" * 70)
print(f"Compounded Net Capital on $500:   ${500 * cum_pnl[-1]:10,.2f} (+{(cum_pnl[-1] - 1.0) * 100:,.1f}%)")
print("=" * 70)
