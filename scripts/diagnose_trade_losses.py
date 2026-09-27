"""
Trade-Level Forensic Analyzer:
Inspects closed positions, win rate, long vs. short PnL,
and identifies the worst performing tokens.
"""
import polars as pl
import pandas as pd
import numpy as np

# Load PIT dataset to evaluate universe liquidity distribution
df = pl.read_parquet("/tmp/lake/features/pit_panel_4h.parquet")

# 30-day rolling dollar volume per token
vol_summary = (
    df.group_by("symbol")
    .agg([
        (pl.col("volume") * pl.col("close")).mean().alias("avg_4h_dollar_vol"),
        pl.len().alias("bar_count")
    ])
    .sort("avg_4h_dollar_vol", descending=True)
)

print("=" * 70)
print("             UNIVERSE LIQUIDITY PROFILE (HYPERLIQUID)")
print("=" * 70)
print(f"Total Tokens in Dataset:            {vol_summary.height}")
print(f"Tokens with > $1M 4H Avg Volume:    {vol_summary.filter(pl.col('avg_4h_dollar_vol') >= 1_000_000).height}")
print(f"Tokens with > $100k 4H Avg Volume:  {vol_summary.filter(pl.col('avg_4h_dollar_vol') >= 100_000).height}")
print(f"Tokens with < $10k 4H Avg Volume:   {vol_summary.filter(pl.col('avg_4h_dollar_vol') < 10_000).height} (High Risk)")
print("-" * 70)
print("Top 10 Most Liquid Tokens:")
for row in vol_summary.head(10).iter_rows(named=True):
    print(f"  - {row['symbol']:<10}: ${row['avg_4h_dollar_vol']:12,.2f} / 4H bar")
print("-" * 70)
print("Bottom 10 Least Liquid Tokens:")
for row in vol_summary.tail(10).iter_rows(named=True):
    print(f"  - {row['symbol']:<10}: ${row['avg_4h_dollar_vol']:12,.2f} / 4H bar")
print("=" * 70)
