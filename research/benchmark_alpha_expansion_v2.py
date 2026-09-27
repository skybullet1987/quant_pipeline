import os
from pathlib import Path
import numpy as np
import polars as pl
from scipy.stats import spearmanr
from catboost import CatBoostRegressor

print("=" * 65)
print("   OFFLINE ALPHA EXPERIMENTAL LAB: BENCHMARK V2 (RANK-ALIGNED)")
print("=" * 65)

data_dir = Path.home() / "quant_pipeline" / "data" / "features"
parquet_files = list(data_dir.glob("*.parquet")) if data_dir.exists() else []
if not parquet_files:
    data_dir = Path.home() / "quant_pipeline" / "data" / "lake"
    parquet_files = list(data_dir.glob("*.parquet"))

print(f"[+] Loading {len(parquet_files)} parquet file(s)...")
df = pl.read_parquet(parquet_files).sort(["symbol", "timestamp_ms"])

# 1. 4H Returns & Market Benchmark (Cross-Sectional Median Market Return)
df = df.with_columns([
    (pl.col("close") / pl.col("close").shift(1).over("symbol") - 1.0).alias("ret_4h")
])

mkt = df.group_by("timestamp_ms").agg(pl.col("ret_4h").median().alias("ret_mkt"))
df = df.join(mkt, on="timestamp_ms", how="left")

# 2. Residual Returns (R_i - R_mkt)
df = df.with_columns([
    (pl.col("ret_4h") - pl.col("ret_mkt")).alias("residual_ret")
])

# 3. Multi-Horizon Residual Momentum: 24h (6 bars), 72h (18 bars), 168h (42 bars)
df = df.with_columns([
    pl.col("residual_ret").rolling_sum(window_size=6).over("symbol").alias("idio_mom_24h"),
    pl.col("residual_ret").rolling_sum(window_size=18).over("symbol").alias("idio_mom_72h"),
    pl.col("residual_ret").rolling_sum(window_size=42).over("symbol").alias("idio_mom_168h")
])

# 4. Parkinson Volatility
df = df.with_columns([
    ((pl.col("high").log() - pl.col("low").log()).pow(2) / (4.0 * np.log(2))).sqrt().alias("parkinson_vol")
])

# 5. Volatility-Adjusted Residual Trend (Directional Sharpes)
df = df.with_columns([
    (pl.col("idio_mom_24h") / (pl.col("parkinson_vol").rolling_mean(window_size=6).over("symbol") + 1e-4)).alias("vol_adj_mom_24h"),
    (pl.col("idio_mom_72h") / (pl.col("parkinson_vol").rolling_mean(window_size=18).over("symbol") + 1e-4)).alias("vol_adj_mom_72h"),
])

# 6. Signed Volume Flow Interaction
df = df.with_columns([
    (pl.col("volume") / (pl.col("volume").rolling_mean(window_size=18).over("symbol") + 1e-6)).alias("vol_ratio_72h")
])
df = df.with_columns([
    (pl.col("vol_ratio_72h") * pl.col("residual_ret").sign()).alias("signed_vol_flow")
])

# 7. Mean-Reversion Disparity Feature
df = df.with_columns([
    ((pl.col("close") - pl.col("close").rolling_mean(window_size=18).over("symbol")) / 
     (pl.col("close").rolling_std(window_size=18).over("symbol") + 1e-6)).alias("z_disparity_72h")
])

# 8. Target Transformation: 4H Forward Cross-Sectional Percentile Rank
df = df.with_columns([
    (pl.col("close").shift(-1).over("symbol") / pl.col("close") - 1.0).alias("raw_fwd_ret")
])

# Compute intra-bar cross-sectional percentile rank [0, 1]
df = df.with_columns([
    (pl.col("raw_fwd_ret").rank().over("timestamp_ms") / 
     pl.col("raw_fwd_ret").count().over("timestamp_ms")).alias("target_rank_4h")
])

feature_cols = [
    "idio_mom_24h",
    "idio_mom_72h",
    "idio_mom_168h",
    "vol_adj_mom_24h",
    "vol_adj_mom_72h",
    "signed_vol_flow",
    "z_disparity_72h"
]

clean_df = df.select(["timestamp_ms", "symbol", "target_rank_4h", "raw_fwd_ret"] + feature_cols).drop_nulls()
print(f"[+] Dataset prepped with rank-aligned targets: {clean_df.height:,} samples")

# Walk-Forward Split (70% Train, 30% Test)
timestamps = sorted(clean_df["timestamp_ms"].unique().to_list())
split_idx = int(len(timestamps) * 0.70)
split_ts = timestamps[split_idx]

train_data = clean_df.filter(pl.col("timestamp_ms") < split_ts)
test_data = clean_df.filter(pl.col("timestamp_ms") >= split_ts)

X_train = train_data.select(feature_cols).to_pandas()
y_train = train_data["target_rank_4h"].to_pandas()
X_test = test_data.select(feature_cols).to_pandas()
y_test = test_data["target_rank_4h"].to_pandas()

# Regularized CatBoost setup per research paper
print("\n[+] Training regularized CatBoost on cross-sectional rank target...")
model = CatBoostRegressor(
    iterations=500,
    learning_rate=0.03,
    depth=5,
    l2_leaf_reg=10.0,
    rsm=0.70,
    subsample=0.80,
    random_seed=42,
    verbose=100
)
model.fit(X_train, y_train, eval_set=(X_test, y_test), early_stopping_rounds=40)

# Out-of-Sample Rank IC Evaluation against real forward returns
test_df = test_data.with_columns(
    pl.Series("pred_rank", model.predict(X_test))
)

rank_ics = []
for ts, group in test_df.group_by("timestamp_ms"):
    if group.height >= 8:
        corr, _ = spearmanr(group["pred_rank"].to_numpy(), group["raw_fwd_ret"].to_numpy())
        if not np.isnan(corr):
            rank_ics.append(corr)

mean_ic = np.mean(rank_ics) if rank_ics else 0.0
std_ic = np.std(rank_ics) if rank_ics else 1.0
ir = mean_ic / (std_ic + 1e-6)

print("\n" + "=" * 65)
print("             OUT-OF-SAMPLE BENCHMARK V2 RESULTS")
print("=" * 65)
print(f"• Evaluated 4H Test Bars       : {len(rank_ics)}")
print(f"• Mean Cross-Sectional Rank IC   : {mean_ic:+.4f}  (Target Hurdle: > +0.030 to +0.055)")
print(f"• Information Ratio (IC / σ)   : {ir:+.4f}")
print("=" * 65)

importances = model.get_feature_importance()
print("\n=== FEATURE IMPORTANCE RANKING ===")
for feat, imp in sorted(zip(feature_cols, importances), key=lambda x: x[1], reverse=True):
    print(f"• {feat:<22}: {imp:.2f}%")
print("=" * 65)
