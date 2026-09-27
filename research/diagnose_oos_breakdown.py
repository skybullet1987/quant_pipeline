import numpy as np
import polars as pl
from pathlib import Path

LAKE_PATH = Path.home() / "quant_pipeline" / "data" / "lake" / "features" / "pit_panel_1h_full.parquet"
df = pl.read_parquet(LAKE_PATH)

if "group_id" not in df.columns:
    unique_ts = df.select("timestamp_ms").unique().sort("timestamp_ms").with_columns(
        pl.int_range(0, pl.len()).alias("group_id")
    )
    df = df.join(unique_ts, on="timestamp_ms", how="left")

all_groups = sorted(df.select("group_id").unique().to_series().to_list())

# Forward 4H return
df = df.sort(["symbol", "group_id"]).with_columns([
    (pl.col("close").shift(-4).over("symbol") / pl.col("close") - 1.0).fill_null(0.0).alias("fwd_ret_4h")
])

# Align BTC
btc = df.filter(pl.col("symbol") == "BTC").select([
    "group_id", pl.col("ret_4h").alias("btc_ret_4h"), pl.col("ret_12h").alias("btc_ret_12h"), pl.col("ret_72h").alias("btc_ret_72h")
]).unique(subset=["group_id"])
df = df.join(btc, on="group_id", how="left")

# Signals
df = df.with_columns([
    (-((pl.col("ret_4h") - pl.col("beta_btc") * pl.col("btc_ret_4h")) / (pl.col("vol_yang_zhang") + 1e-5))).alias("sig_rev_4h"),
    (-((pl.col("ret_12h") - pl.col("beta_btc") * pl.col("btc_ret_12h")) / (pl.col("vol_yang_zhang") + 1e-5))).alias("sig_rev_12h"),
    (((pl.col("ret_72h") - pl.col("beta_btc") * pl.col("btc_ret_72h")) / (pl.col("vol_yang_zhang") + 1e-5))).alias("sig_drift_72h"),
])

# Filter valid trading groups
valid_counts = df.filter(pl.col("dollar_volume_1h") > 25_000).group_by("group_id").count()
active_grps = sorted(valid_counts.filter(pl.col("count") >= 35)["group_id"].to_list())
split_grp = active_grps[int(len(active_grps) * 0.70)]

def calc_period_stats(grps, name):
    sub = df.filter(pl.col("group_id").is_in(grps) & (pl.col("dollar_volume_1h") > 25_000))
    # IC for each signal
    ic_4h = sub.select(pl.corr("sig_rev_4h", "fwd_ret_4h")).to_numpy()[0, 0]
    ic_12h = sub.select(pl.corr("sig_rev_12h", "fwd_ret_4h")).to_numpy()[0, 0]
    ic_72h = sub.select(pl.corr("sig_drift_72h", "fwd_ret_4h")).to_numpy()[0, 0]
    
    # Dispersion (cross-sectional std of 72h return)
    disp = sub.group_by("group_id").agg(pl.col("ret_72h").std().alias("cs_std"))["cs_std"].mean()
    vol = sub["vol_yang_zhang"].median()
    print(f"[{name}]")
    print(f"  • Cross-Sectional Dispersion : {disp*100:.2f}%")
    print(f"  • Median Yang-Zhang Vol     : {vol*100:.2f}%")
    print(f"  • IC (4H Reversion)         : {ic_4h:>+.4f}")
    print(f"  • IC (12H Reversion)        : {ic_12h:>+.4f}")
    print(f"  • IC (72H Drift)            : {ic_72h:>+.4f}")

print("=" * 70)
print("       SIGNAL INFORMATION COEFFICIENT (IC) & DISPERSION AUDIT")
print("=" * 70)
calc_period_stats([g for g in active_grps if g < split_grp], "In-Sample (First 70% / 134 Days)")
print("-" * 70)
calc_period_stats([g for g in active_grps if g >= split_grp], "Untouched OOS (Last 30% / 57 Days)")
print("=" * 70)
