import numpy as np
import polars as pl
from pathlib import Path

LAKE_PATH = Path.home() / "quant_pipeline" / "data" / "lake" / "features" / "pit_panel_1h_with_funding.parquet"

if not LAKE_PATH.exists():
    print(f"[!] Target parquet not found: {LAKE_PATH}")
    exit(1)

df = pl.read_parquet(LAKE_PATH)

# Compute forward price returns for adverse selection correlation check
df = df.sort(["symbol", "timestamp_ms"]).with_columns([
    (pl.col("close").shift(-1).over("symbol") / pl.col("close") - 1.0).alias("fwd_ret_1h"),
    (pl.col("close").shift(-4).over("symbol") / pl.col("close") - 1.0).alias("fwd_ret_4h"),
    (pl.col("close").shift(-24).over("symbol") / pl.col("close") - 1.0).alias("fwd_ret_24h"),
])

# Active records with non-zero volume
valid = df.filter((pl.col("dollar_volume_1h") > 25_000) & pl.col("funding_rate").is_not_null())

apr_vals = valid["funding_apr"].to_numpy()
rate_vals = valid["funding_rate"].to_numpy()

pcts = [0.1, 1, 5, 10, 25, 50, 75, 90, 95, 99, 99.9]
apr_quantiles = np.percentile(apr_vals, pcts)

print("=" * 86)
print("       HYPERLIQUID FUNDING RATE & APR GLOBAL DISTRIBUTION")
print("=" * 86)
print(f"Total Evaluated Bars   : {len(valid):,} across {valid['symbol'].n_unique()} symbols")
print(f"Mean Hourly Funding    : {np.mean(rate_vals)*100:>+.4f}% (APR: {np.mean(apr_vals)*100:>+.2f}%)")
print(f"Median Hourly Funding  : {np.median(rate_vals)*100:>+.4f}% (APR: {np.median(apr_vals)*100:>+.2f}%)")
print(f"Std Dev (Hourly)       : {np.std(rate_vals)*100:>.4f}% (APR: {np.std(apr_vals)*100:>.2f}%)")
print(f"Positive Funding Rate  : {(np.mean(rate_vals > 0)*100):.2f}% of observations")
print(f"Negative Funding Rate  : {(np.mean(rate_vals < 0)*100):.2f}% of observations")
print(f"Flat/Zero Funding Rate : {(np.mean(rate_vals == 0)*100):.2f}% of observations")
print("-" * 86)
print(f"{'Percentile':<15} | {'Hourly Funding Rate':<22} | {'Annualized Funding APR':<24}")
print("-" * 86)
for p, q in zip(pcts, apr_quantiles):
    hourly_equiv = q / (24 * 365)
    print(f"{p:>5.1f}%          | {hourly_equiv*100:>+18.4f}% | {q*100:>+20.2f}%")

# Symbol-Level Persistence and Extreme Carry Spread
sym_stats = valid.group_by("symbol").agg([
    pl.col("funding_apr").mean().alias("mean_apr"),
    pl.col("funding_apr").median().alias("median_apr"),
    pl.col("funding_persistence_7d").mean().alias("mean_pers"),
    (pl.col("funding_rate") > 0).mean().alias("pct_pos"),
    pl.len().alias("count")
]).filter(pl.col("count") > 500)

top_borrow = sym_stats.sort("mean_apr", descending=True).head(10)
top_discount = sym_stats.sort("mean_apr", descending=False).head(10)

print("\n" + "=" * 86)
print("       TOP 10 POSITIVE CARRY TOKENS (LONGS PAY SHORTS)")
print("=" * 86)
print(f"{'Symbol':<12} | {'Mean APR':<14} | {'Median APR':<14} | {'% Positive Hours':<18} | {'Observations':<12}")
print("-" * 86)
for row in top_borrow.iter_rows(named=True):
    print(f"{row['symbol']:<12} | {row['mean_apr']*100:>+11.2f}% | {row['median_apr']*100:>+11.2f}% | {row['pct_pos']*100:>15.1f}% | {row['count']:>12,}")

print("\n" + "=" * 86)
print("       TOP 10 NEGATIVE CARRY TOKENS (SHORTS PAY LONGS)")
print("=" * 86)
print(f"{'Symbol':<12} | {'Mean APR':<14} | {'Median APR':<14} | {'% Positive Hours':<18} | {'Observations':<12}")
print("-" * 86)
for row in top_discount.iter_rows(named=True):
    print(f"{row['symbol']:<12} | {row['mean_apr']*100:>+11.2f}% | {row['median_apr']*100:>+11.2f}% | {row['pct_pos']*100:>15.1f}% | {row['count']:>12,}")

# Adverse Price Selection Check
# Does high positive funding predict immediate price pump (squeeze) or immediate price dump?
corr_1h = valid.select(pl.corr("funding_apr", "fwd_ret_1h")).to_numpy()[0, 0]
corr_4h = valid.select(pl.corr("funding_apr", "fwd_ret_4h")).to_numpy()[0, 0]
corr_24h = valid.select(pl.corr("funding_apr", "fwd_ret_24h")).to_numpy()[0, 0]

print("\n" + "=" * 86)
print("       ADVERSE PRICE SELECTION (CORRELATION: FUNDING APR vs FORWARD RETURN)")
print("=" * 86)
print(f"Correlation with Next 1H Return  : {corr_1h:>+.4f}")
print(f"Correlation with Next 4H Return  : {corr_4h:>+.4f}")
print(f"Correlation with Next 24H Return : {corr_24h:>+.4f}")

if corr_24h > 0.02:
    print("[!] WARNING: Positive correlation exists. Tokens with high funding tend to keep rising.")
    print("    Naive shorting of top-funding tokens carries severe adverse momentum risk.")
elif corr_24h < -0.02:
    print("[✓] INVERSION DETECTED: Tokens with high funding tend to mean-revert downward over 24H.")
else:
    print("[i] NEUTRAL: Funding rate shows minimal linear correlation with price direction.")
print("=" * 86)
