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

# Active dispersion filter (N >= 12)
df_disp = (
    df.filter((pl.col("dollar_volume_1h") > 25_000) & pl.col("ret_72h").is_not_null())
    .group_by("group_id")
    .agg([pl.col("ret_72h").std().alias("cs_disp"), pl.len().alias("count")])
    .filter(pl.col("count") >= 12)
    .sort("group_id")
)
all_active_grps = df_disp["group_id"].to_list()
fold1_grps = all_active_grps[: len(all_active_grps) // 4]

fold1_stats = (
    df.filter(pl.col("group_id").is_in(fold1_grps))
    .filter((pl.col("dollar_volume_1h") > 25_000) & pl.col("vol_yang_zhang").is_not_null())
    .with_columns([((pl.col("group_id") - fold1_grps[0]) // (24 * 7)).alias("fold1_week")])
    .group_by("fold1_week")
    .agg([
        pl.col("symbol").n_unique().alias("unique_tokens"),
        pl.col("dollar_volume_1h").mean().alias("avg_hourly_vol")
    ])
    .sort("fold1_week")
)

print("=" * 86)
print("       CORRECTED FOLD 1 FORENSICS (ACTIVE WINDOW: DAYS 0.0 TO 51.1)")
print("=" * 86)
print(f"{'Week of Fold 1':<18} | {'Avg Active Tokens':<20} | {'Avg Hourly Vol':<18} | {'Breadth Gate'}")
print("-" * 86)
for row in fold1_stats.iter_rows(named=True):
    wk = row["fold1_week"]
    tok = row["unique_tokens"]
    vol = row["avg_hourly_vol"]
    status = "GATE CLOSED (Cash)" if tok < 35 else "GATE OPEN (Active Trading)"
    print(f"Week {wk+1:<13} | {tok:>18.1f} | ${vol:>16,.0f} | {status}")
print("=" * 86)
