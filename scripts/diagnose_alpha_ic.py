"""
Alpha Signal Diagnostic Tool:
Computes Spearman Rank Information Coefficient (IC) and Quantile Returns
to verify signal efficacy before event-driven backtesting.
"""
import numpy as np
import pandas as pd
import polars as pl
from scipy.stats import spearmanr
from sklearn.linear_model import RidgeCV
import lightgbm as lgb
from catboost import CatBoostRegressor

print("1. Loading and preparing feature dataset...")
df = (
    pl.read_parquet("/tmp/lake/features/pit_panel_4h.parquet")
    .unique(["symbol", "bucket_timestamp_utc"])
    .sort("bucket_timestamp_utc")
)

# 24H Forward demeaned target vs multi-horizon features
enriched = (
    df.sort(["symbol", "bucket_timestamp_utc"])
    .with_columns([
        pl.col("close").pct_change(6).over("symbol").alias("ret_24h"),
        pl.col("close").pct_change(18).over("symbol").alias("ret_72h"),
        pl.col("close").pct_change(42).over("symbol").alias("ret_168h"),
        pl.col("close").pct_change(6).shift(-6).over("symbol").alias("fwd_ret_24h"),
    ])
)

mkt_mean = (
    enriched.group_by("bucket_timestamp_utc")
    .agg(pl.col("fwd_ret_24h").mean().alias("mkt_fwd_24h"))
)

pdf = (
    enriched.join(mkt_mean, on="bucket_timestamp_utc")
    .with_columns([
        (pl.col("fwd_ret_24h") - pl.col("mkt_fwd_24h")).alias("target_excess_24h")
    ])
    .to_pandas()
)

features = ["log_ret", "ret_24h", "ret_72h", "ret_168h", "rolling_24h_volatility", "cs_momentum_4h_percentile", "cs_liquidity_percentile"]
pdf = pdf.dropna(subset=features + ["target_excess_24h"])
timestamps = pd.Series(pdf["bucket_timestamp_utc"].unique()).sort_values().reset_index(drop=True)

print("2. Running Walk-Forward Out-of-Sample Predictions...")
pdf["pred"] = 0.0
for s in range(2160, len(timestamps), 720):
    e = min(s + 720, len(timestamps))
    tr_times = set(timestamps.iloc[:s])
    te_times = set(timestamps.iloc[s:e])

    tr_mask = pdf["bucket_timestamp_utc"].isin(tr_times)
    te_mask = pdf["bucket_timestamp_utc"].isin(te_times)

    X_tr, y_tr = pdf.loc[tr_mask, features].values, pdf.loc[tr_mask, "target_excess_24h"].values
    X_te = pdf.loc[te_mask, features].values

    if len(X_te) == 0:
        continue

    ridge = RidgeCV(alphas=np.logspace(-2, 3, 10)).fit(X_tr, y_tr)
    lgbm = lgb.LGBMRegressor(n_estimators=40, max_depth=4, num_leaves=15, learning_rate=0.03, random_state=42, n_jobs=-1, verbose=-1).fit(X_tr, y_tr)
    cat = CatBoostRegressor(iterations=40, depth=4, learning_rate=0.03, random_seed=42, thread_count=-1, verbose=0).fit(X_tr, y_tr)

    pdf.loc[te_mask, "pred"] = 0.20 * ridge.predict(X_te) + 0.40 * lgbm.predict(X_te) + 0.40 * cat.predict(X_te)

print("3. Evaluating Out-of-Sample Rank IC and Quantile Spreads...")
oof = pdf[pdf["pred"] != 0.0].copy()

# Compute Spearman Rank IC per timestamp
daily_ics = []
for t, group in oof.groupby("bucket_timestamp_utc"):
    if len(group) >= 20:
        corr, _ = spearmanr(group["pred"], group["target_excess_24h"])
        if not np.isnan(corr):
            daily_ics.append(corr)

mean_ic = np.mean(daily_ics)
ic_ir = mean_ic / (np.std(daily_ics) + 1e-6)

print("\n" + "=" * 70)
print("             TRI-MODEL ENSEMBLE ALPHA DIAGNOSTICS")
print("=" * 70)
print(f"Mean Spearman Rank IC:          {mean_ic:8.4f} (Target: > +0.0300)")
print(f"Information Ratio (IC / IC_std):{ic_ir:8.4f} (Target: > +0.5000)")
print(f"Total Out-of-Sample Timestamps: {len(daily_ics):8d}")
print("=" * 70)
