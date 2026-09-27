import numpy as np
import polars as pl
from pathlib import Path

print("=" * 96)
print("   FORENSIC AUDIT: DECONSTRUCTING FOLD 1 (DAYS 0 TO 51.1)")
print("=" * 96)

LAKE_PATH = Path.home() / "quant_pipeline" / "data" / "lake" / "features" / "pit_panel_1h_with_funding.parquet"
df = pl.read_parquet(LAKE_PATH)

if "group_id" not in df.columns:
    unique_ts = df.select("timestamp_ms").unique().sort("timestamp_ms").with_columns(
        pl.int_range(0, pl.len()).alias("group_id")
    )
    df = df.join(unique_ts, on="timestamp_ms", how="left")

# Check active token counts per day across the first 50 days
daily_stats = (
    df.filter((pl.col("dollar_volume_1h") > 25_000) & pl.col("vol_yang_zhang").is_not_null())
    .with_columns([(pl.col("group_id") // 24).alias("day")])
    .group_by("day")
    .agg([
        pl.col("symbol").n_unique().alias("unique_tokens"),
        pl.col("dollar_volume_1h").mean().alias("avg_hourly_vol")
    ])
    .sort("day")
    .head(52)
)

print(f"{'Day Range':<16} | {'Avg Tradeable Tokens':<22} | {'Avg Hourly Volume':<20} | {'Breadth Status'}")
print("-" * 80)
for w in range(0, 52, 7):
    chunk = daily_stats.filter((pl.col("day") >= w) & (pl.col("day") < w + 7))
    avg_tokens = chunk["unique_tokens"].mean()
    avg_vol = chunk["avg_hourly_vol"].mean()
    status = "GATE CLOSED (Cash)" if avg_tokens < 35 else "GATE OPEN (Trading)"
    print(f"Days {w:>2} to {min(w+6, 51):>2}   | {avg_tokens:>18.1f}   | ${avg_vol:>17,.0f} | {status}")

print("=" * 96)
