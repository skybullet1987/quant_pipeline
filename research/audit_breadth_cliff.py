import numpy as np
import polars as pl
from pathlib import Path

LAKE_PATH = Path.home() / "quant_pipeline" / "data" / "lake" / "features" / "pit_panel_1h_with_funding.parquet"
df = pl.read_parquet(LAKE_PATH)

if "group_id" not in df.columns:
    unique_ts = df.select("timestamp_ms").unique().sort("timestamp_ms").with_columns(
        pl.int_range(0, pl.len()).alias("group_id")
    )
    df = df.join(unique_ts, on="timestamp_ms", how="left")

# Count active symbols per group
counts = (
    df.filter((pl.col("dollar_volume_1h") > 25_000) & pl.col("vol_yang_zhang").is_not_null())
    .group_by("group_id")
    .len()
    .sort("group_id")
)

grps_thin = counts.filter((pl.col("len") >= 12) & (pl.col("len") < 35))["group_id"].to_list()
grps_liquid = counts.filter(pl.col("len") >= 35)["group_id"].to_list()

print("=" * 86)
print("             UNIVERSE BREADTH DISTRIBUTION IN LAKE")
print("=" * 86)
print(f"Total Available Bars with >=12 assets : {counts.filter(pl.col('len') >= 12).height:,} ({counts.filter(pl.col('len') >= 12).height/24:.1f} days)")
print(f"Bars with Thin Universe (12 <= N < 35) : {len(grps_thin):,} ({len(grps_thin)/24:.1f} days)")
print(f"Bars with Mature Universe (N >= 35)    : {len(grps_liquid):,} ({len(grps_liquid)/24:.1f} days)")
print(f"Average Assets in Thin Regime          : {counts.filter((pl.col('len') >= 12) & (pl.col('len') < 35))['len'].mean():.1f} symbols")
print(f"Average Assets in Mature Regime        : {counts.filter(pl.col('len') >= 35)['len'].mean():.1f} symbols")
print("=" * 86)
