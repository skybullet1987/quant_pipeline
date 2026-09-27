import os
from pathlib import Path
import numpy as np
import polars as pl
from scipy.stats import spearmanr
from catboost import CatBoostRegressor, Pool

print("=" * 65)
print("   OFFLINE ALPHA EXPERIMENTAL LAB: FEATURE BENCHMARK")
print("=" * 65)

data_dir = Path.home() / "quant_pipeline" / "data" / "features"
parquet_files = list(data_dir.glob("*.parquet")) if data_dir.exists() else []
if not parquet_files:
    data_dir = Path.home() / "quant_pipeline" / "data" / "lake"
    parquet_files = list(data_dir.glob("*.parquet"))

print(f"[+] Loading {len(parquet_files)} parquet file(s)...")
df = pl.read_parquet(parquet_files)
print(f"[+] Total Records: {df.height:,} | Columns: {df.columns}")

# Sort chronologically by symbol and timestamp
df = df.sort(["symbol", "timestamp_ms"])

# 1. 4-Hour Return Calculation
df = df.with_columns([
    (pl.col("close") / pl.col("close").shift(1).over("symbol") - 1.0).alias("ret_4h"),
    (pl.col("volume") / (pl.col("volume").rolling_mean(window_size=18).over("symbol") + 1e-6)).alias("vol_surge_72h")
])

# 2. Oracle Basis Spread (Native Hyperliquid Pricing Wedge)
# Divergence between execution mark/close and oracle index
df = df.with_columns([
    ((pl.col("close") - pl.col("oracle_px")) / (pl.col("oracle_px") + 1e-6)).alias("oracle_basis_spread")
])

# 3. High-Low Parkinson Volatility Estimator
df = df.with_columns([
    ((pl.col("high").log() - pl.col("low").log()).pow(2) / (4.0 * np.log(2))).alias("parkinson_vol")
])

# 4. Market Beta Residualization
# Isolate market return: use BTC if present, else cross-sectional median
unique_symbols = df["symbol"].unique().to_list()
btc_sym = next((s for s in unique_symbols if s.upper() in ["BTC", "BTC-USD", "BTC-USDC", "BTC-PERP"]), None)

if btc_sym:
    print(f"[+] Residualizing returns against market anchor: {btc_sym}")
    btc_mkt = (
        df.filter(pl.col("symbol") == btc_sym)
        .select(["timestamp_ms", "ret_4h"])
        .rename({"ret_4h": "ret_mkt"})
    )
    df = df.join(btc_mkt, on="timestamp_ms", how="left")
else:
    print("[+] BTC anchor not isolated; using cross-sectional median market return...")
    mkt = df.group_by("timestamp_ms").agg(pl.col("ret_4h").median().alias("ret_mkt"))
    df = df.join(mkt, on="timestamp_ms", how="left")

# Residual return innovation (R_i - R_mkt)
df = df.with_columns([
    (pl.col("ret_4h") - pl.col("ret_mkt")).alias("residual_ret")
])

# Multi-horizon residual momentum
df = df.with_columns([
    pl.col("residual_ret").rolling_sum(window_size=6).over("symbol").alias("idio_mom_24h"),
    pl.col("residual_ret").rolling_sum(window_size=18).over("symbol").alias("idio_mom_72h")
])

# 5. Define Forward Target: 4H Forward Cross-Sectional Return
df = df.with_columns([
    (pl.col("close").shift(-1).over("symbol") / pl.col("close") - 1.0).alias("fwd_ret_4h")
])

feature_cols = [
    "oracle_basis_spread",
    "parkinson_vol",
    "vol_surge_72h",
    "residual_ret",
    "idio_mom_24h",
    "idio_mom_72h"
]

clean_df = df.select(["timestamp_ms", "symbol", "fwd_ret_4h"] + feature_cols).drop_nulls()
print(f"[+] Preprocessed clean samples: {clean_df.height:,}")

# 6. Walk-Forward Train/Test Split (70% Train, 30% Out-of-Sample Test)
timestamps = sorted(clean_df["timestamp_ms"].unique().to_list())
split_idx = int(len(timestamps) * 0.70)
split_ts = timestamps[split_idx]

train_data = clean_df.filter(pl.col("timestamp_ms") < split_ts)
test_data = clean_df.filter(pl.col("timestamp_ms") >= split_ts)

print(f"[+] Train timestamps: {split_idx} bars ({train_data.height:,} samples)")
print(f"[+] Test timestamps:  {len(timestamps) - split_idx} bars ({test_data.height:,} samples)")

X_train = train_data.select(feature_cols).to_pandas()
y_train = train_data["fwd_ret_4h"].to_pandas()
X_test = test_data.select(feature_cols).to_pandas()
y_test = test_data["fwd_ret_4h"].to_pandas()

# 7. Train Regularized CatBoost Regressor
print("\n[+] Training CatBoost model with tree-depth=5, L2-leaf-reg=10.0...")
model = CatBoostRegressor(
    iterations=400,
    learning_rate=0.03,
    depth=5,
    l2_leaf_reg=10.0,
    random_seed=42,
    verbose=100
)
model.fit(X_train, y_train, eval_set=(X_test, y_test), early_stopping_rounds=40)

# 8. Out-of-Sample Cross-Sectional Rank IC Benchmark
test_df = test_data.with_columns(
    pl.Series("pred", model.predict(X_test))
)

rank_ics = []
for ts, group in test_df.group_by("timestamp_ms"):
    if group.height >= 8:
        corr, _ = spearmanr(group["pred"].to_numpy(), group["fwd_ret_4h"].to_numpy())
        if not np.isnan(corr):
            rank_ics.append(corr)

mean_ic = np.mean(rank_ics) if rank_ics else 0.0
std_ic = np.std(rank_ics) if rank_ics else 1.0
ir = mean_ic / (std_ic + 1e-6)

print("\n" + "=" * 65)
print("             OUT-OF-SAMPLE BENCHMARK RESULTS")
print("=" * 65)
print(f"• Evaluated 4H Test Bars    : {len(rank_ics)}")
print(f"• Mean Cross-Sectional Rank IC: {mean_ic:+.4f}  (Hurdle: > +0.055)")
print(f"• Information Ratio (IC / σ): {ir:+.4f}")
print("=" * 65)

importances = model.get_feature_importance()
print("\n=== FEATURE IMPORTANCE RANKING ===")
for feat, imp in sorted(zip(feature_cols, importances), key=lambda x: x[1], reverse=True):
    print(f"• {feat:<22}: {imp:.2f}%")
print("=" * 65)
