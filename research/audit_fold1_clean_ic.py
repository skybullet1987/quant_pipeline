import numpy as np
import polars as pl
from pathlib import Path

print("=" * 96)
print("   CLEAN FORENSIC AUDIT: FOLD 1 ALPHA RANK IC & P&L DECOMPOSITION")
print("=" * 96)

LAKE_PATH = Path.home() / "quant_pipeline" / "data" / "lake" / "features" / "pit_panel_1h_with_funding.parquet"
df = pl.read_parquet(LAKE_PATH)

if "group_id" not in df.columns:
    unique_ts = df.select("timestamp_ms").unique().sort("timestamp_ms").with_columns(
        pl.int_range(0, pl.len()).alias("group_id")
    )
    df = df.join(unique_ts, on="timestamp_ms", how="left")

# Forward returns
df = df.sort(["symbol", "group_id"]).with_columns([
    (pl.col("close").shift(-1).over("symbol") / pl.col("close") - 1.0).fill_null(0.0).alias("next_ret_1h")
])

# Align BTC
btc = df.filter(pl.col("symbol") == "BTC").select([
    "group_id", pl.col("ret_4h").alias("btc_ret_4h"), pl.col("ret_12h").alias("btc_ret_12h"), pl.col("ret_72h").alias("btc_ret_72h")
]).unique(subset=["group_id"])
df = df.join(btc, on="group_id", how="left")

# Alphas
df = df.with_columns([
    (-0.35 * ((pl.col("ret_4h") - pl.col("beta_btc") * pl.col("btc_ret_4h")) / (pl.col("vol_yang_zhang") + 1e-5))
     -0.25 * ((pl.col("ret_12h") - pl.col("beta_btc") * pl.col("btc_ret_12h")) / (pl.col("vol_yang_zhang") + 1e-5))
     +0.40 * ((pl.col("ret_72h") - pl.col("beta_btc") * pl.col("btc_ret_72h")) / (pl.col("vol_yang_zhang") + 1e-5))).alias("raw_a0"),
    (-1.0 * ((pl.col("ret_1h") - pl.col("beta_btc") * (pl.col("btc_ret_4h") / 4.0)) / (pl.col("vol_yang_zhang") + 1e-5)) * (pl.col("volume_zscore_72h").clip(-1.0, 4.0) + 1.0)).alias("raw_a1"),
    (-1.0 * (((pl.col("funding_rate") - pl.col("funding_rate").rolling_mean(24).over("symbol")) / (pl.col("funding_rate").rolling_std(24).over("symbol") + 1e-6)).clip(-3.0, 3.0)
     - (pl.col("ret_24h") / (pl.col("vol_yang_zhang") * np.sqrt(24) + 1e-5)).clip(-3.0, 3.0))).alias("raw_a2")
])

df = df.sort(["symbol", "group_id"]).with_columns([
    pl.col("raw_a0").ewm_mean(span=6).over("symbol").alias("a0_smooth"),
    pl.col("raw_a1").ewm_mean(span=2).over("symbol").alias("a1_smooth"),
    pl.col("raw_a2").ewm_mean(span=4).over("symbol").alias("a2_smooth")
])

for col, zcol in [("a0_smooth", "z_a0"), ("a1_smooth", "z_a1"), ("a2_smooth", "z_a2")]:
    df = df.with_columns([
        ((pl.col(col) - pl.col(col).mean().over("group_id")) / (pl.col(col).std().over("group_id") + 1e-5)).alias(zcol)
    ])

# Active groups
df_disp = (
    df.filter((pl.col("dollar_volume_1h") > 25_000) & pl.col("ret_72h").is_not_null())
    .group_by("group_id")
    .agg([pl.col("ret_72h").std().alias("cs_disp"), pl.len().alias("count")])
    .filter(pl.col("count") >= 12)
    .sort("group_id")
)
all_active_grps = df_disp["group_id"].to_list()
fold1_grps = all_active_grps[: len(all_active_grps) // 4]

# Drop warm-up nulls to avoid NaN propagation
f1_df = df.filter(
    pl.col("group_id").is_in(fold1_grps) &
    (pl.col("dollar_volume_1h") > 25_000) &
    pl.col("z_a0").is_not_null() &
    pl.col("z_a1").is_not_null() &
    pl.col("z_a2").is_not_null() &
    pl.col("next_ret_1h").is_not_null()
)

def safe_spearman_ic(col_name):
    ics = (
        f1_df.group_by("group_id")
        .agg(pl.corr(col_name, "next_ret_1h", method="spearman").alias("ic"))
        .filter(pl.col("ic").is_not_null() & ~pl.col("ic").is_nan())
    )
    return float(ics["ic"].mean())

ic_a0 = safe_spearman_ic("z_a0")
ic_a1 = safe_spearman_ic("z_a1")
ic_a2 = safe_spearman_ic("z_a2")

print(f"{'Alpha Signal':<32} | {'Fold 1 Rank IC':<16} | {'Regime Status'}")
print("-" * 64)
print(f"{'A0 (Multi-Horizon Momentum)':<32} | {ic_a0:>+14.4f}   | {'Positive / Intact' if ic_a0 > 0 else 'Inverted'}")
print(f"{'A1 (Liquidity Exhaustion)':<32} | {ic_a1:>+14.4f}   | {'Positive / Intact' if ic_a1 > 0 else 'Inverted'}")
print(f"{'A2 (Funding Divergence)':<32} | {ic_a2:>+14.4f}   | {'Inverted (Catching Knives)' if ic_a2 < 0 else 'Intact'}")
print("=" * 96)
