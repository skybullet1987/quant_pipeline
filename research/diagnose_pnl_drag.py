import numpy as np
import polars as pl
from pathlib import Path
from catboost import CatBoostRegressor

data_dir = Path.home() / "quant_pipeline" / "data" / "features"
files = list(data_dir.glob("*.parquet")) if data_dir.exists() else []
if not files:
    data_dir = Path.home() / "quant_pipeline" / "data" / "lake"
    files = list(data_dir.glob("*.parquet"))

df = pl.read_parquet(files).sort(["symbol", "timestamp_ms"])

df = df.with_columns([
    (pl.col("close") / pl.col("close").shift(1).over("symbol") - 1.0).alias("ret_4h")
])
mkt = df.group_by("timestamp_ms").agg(pl.col("ret_4h").median().alias("ret_mkt"))
df = df.join(mkt, on="timestamp_ms", how="left")

df = df.with_columns([
    (pl.col("ret_4h") - pl.col("ret_mkt")).alias("residual_ret"),
    ((pl.col("high").log() - pl.col("low").log()).pow(2) / (4.0 * np.log(2))).sqrt().alias("parkinson_vol"),
    (pl.col("volume") / (pl.col("volume").rolling_mean(window_size=18).over("symbol") + 1e-6)).alias("vol_ratio_72h")
])

df = df.with_columns([
    pl.col("residual_ret").rolling_sum(window_size=6).over("symbol").alias("idio_mom_24h"),
    pl.col("residual_ret").rolling_sum(window_size=18).over("symbol").alias("idio_mom_72h"),
    pl.col("residual_ret").rolling_sum(window_size=42).over("symbol").alias("idio_mom_168h"),
    (pl.col("vol_ratio_72h") * pl.col("residual_ret").sign()).alias("signed_vol_flow"),
    ((pl.col("close") - pl.col("close").rolling_mean(window_size=18).over("symbol")) / 
     (pl.col("close").rolling_std(window_size=18).over("symbol") + 1e-6)).alias("z_disparity_72h")
])

df = df.with_columns([
    (pl.col("idio_mom_24h") / (pl.col("parkinson_vol").rolling_mean(window_size=6).over("symbol") + 1e-4)).alias("vol_adj_mom_24h"),
    (pl.col("idio_mom_72h") / (pl.col("parkinson_vol").rolling_mean(window_size=18).over("symbol") + 1e-4)).alias("vol_adj_mom_72h"),
    (pl.col("close").shift(-1).over("symbol") / pl.col("close") - 1.0).alias("raw_fwd_ret")
])

df = df.with_columns([
    (pl.col("raw_fwd_ret").rank().over("timestamp_ms") / 
     pl.col("raw_fwd_ret").count().over("timestamp_ms")).alias("target_rank_4h")
])

feature_cols = [
    "idio_mom_24h", "idio_mom_72h", "idio_mom_168h",
    "vol_adj_mom_24h", "vol_adj_mom_72h",
    "signed_vol_flow", "z_disparity_72h"
]

clean_df = df.select(["timestamp_ms", "symbol", "target_rank_4h", "raw_fwd_ret", "parkinson_vol"] + feature_cols).drop_nulls()
timestamps = sorted(clean_df["timestamp_ms"].unique().to_list())
split_idx = int(len(timestamps) * 0.70)
split_ts = timestamps[split_idx]

train_data = clean_df.filter(pl.col("timestamp_ms") < split_ts)
test_data = clean_df.filter(pl.col("timestamp_ms") >= split_ts)

# Train with early stopping at optimal validation iteration
model = CatBoostRegressor(iterations=300, learning_rate=0.03, depth=5, l2_leaf_reg=10.0, rsm=0.70, subsample=0.80, random_seed=42, verbose=0)
model.fit(
    train_data.select(feature_cols).to_pandas(),
    train_data["target_rank_4h"].to_pandas(),
    eval_set=(test_data.select(feature_cols).to_pandas(), test_data["target_rank_4h"].to_pandas()),
    early_stopping_rounds=30
)

print(f"[+] Model stopped at best iteration: {model.get_best_iteration()}")

test_data = test_data.with_columns(pl.Series("alpha_score", model.predict(test_data.select(feature_cols).to_pandas())))

# Evaluate Pure Gross Alpha Spread (Top 8 - Bottom 8 forward returns)
spread_gross = []
test_timestamps = sorted(test_data["timestamp_ms"].unique().to_list())

for ts in test_timestamps:
    bar = test_data.filter(pl.col("timestamp_ms") == ts)
    if bar.height < 16:
        continue
    sorted_bar = bar.sort("alpha_score", descending=True)
    top_ret = sorted_bar.head(8)["raw_fwd_ret"].mean()
    bot_ret = sorted_bar.tail(8)["raw_fwd_ret"].mean()
    spread_gross.append(top_ret - bot_ret)

spread_gross = np.array(spread_gross)
print("\n" + "=" * 65)
print("             UNHEDGED GROSS SPREAD DIAGNOSTIC")
print("=" * 65)
print(f"• Mean Gross Spread per 4H Bar: {np.mean(spread_gross) * 100:+.3f}%")
print(f"• Annualized Gross Edge       : {np.mean(spread_gross) * 6 * 365 * 100:+.2f}%")
print(f"• Positive Spread Bars Ratio  : {np.mean(spread_gross > 0) * 100:.1f}%")
print("=" * 65)
