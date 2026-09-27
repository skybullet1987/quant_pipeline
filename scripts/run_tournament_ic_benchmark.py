"""
Stage 1 & 2 Tournament Evaluation:
Assesses Walk-Forward Out-of-Sample Rank Information Coefficients (IC)
and Feature Importance across the Orthogonal Quantitative Library.
"""
import numpy as np
import pandas as pd
import polars as pl
from scipy.stats import spearmanr
from sklearn.linear_model import RidgeCV
import lightgbm as lgb
from catboost import CatBoostRegressor

from src.features.orthogonal_library import compute_orthogonal_features

print("1. Loading raw panel dataset...")
raw_df = (
    pl.read_parquet("/tmp/lake/features/pit_panel_4h.parquet")
    .unique(["symbol", "bucket_timestamp_utc"])
    .sort("bucket_timestamp_utc")
)

print("2. Generating Orthogonal Quantitative Feature Library...")
df = compute_orthogonal_features(raw_df)

# Demean forward target against cross-sectional market mean
market_mean = (
    df.group_by("bucket_timestamp_utc")
    .agg(pl.col("fwd_ret_24h").mean().alias("mkt_fwd_24h"))
)

pdf = (
    df.join(market_mean, on="bucket_timestamp_utc")
    .with_columns([
        (pl.col("fwd_ret_24h") - pl.col("mkt_fwd_24h")).alias("target_excess_24h")
    ])
    .to_pandas()
)

# Orthogonal Feature Set across Families 1, 2, 5, 6, 7, 8
feature_cols = [
    "cs_rank_ret_24h",
    "cs_rank_ret_72h",
    "cs_mom_acceleration_24_72",
    "cs_dist_to_universe_median_24h",
    "beta_btc_7d",
    "idio_residual_ret_btc_24h",
    "garman_klass_vol_ratio_24h",
    "normalized_atr_24h",
    "bollinger_keltner_squeeze_ratio_20",
    "clv_4h",
    "lower_wick_absorption_ratio_4h",
    "upper_wick_ratio_4h",
    "intrabar_wick_imbalance_4h",
    "cs_rank_volume_pct_24h",
    "interaction_mom_squeeze_24h",
    "interaction_breakout_thrust",
    "interaction_tbm_score",
]

pdf = pdf.dropna(subset=feature_cols + ["target_excess_24h"])
timestamps = pd.Series(pdf["bucket_timestamp_utc"].unique()).sort_values().reset_index(drop=True)

print(f"3. Running Walk-Forward Tournament Validation across {len(timestamps)} timestamps...")
pdf["pred"] = 0.0

n_train = 2160    # 1 year warm-up
step = 720        # 4 month retraining interval

for s in range(n_train, len(timestamps), step):
    e = min(s + step, len(timestamps))
    tr_times = set(timestamps.iloc[:s])
    te_times = set(timestamps.iloc[s:e])

    tr_mask = pdf["bucket_timestamp_utc"].isin(tr_times)
    te_mask = pdf["bucket_timestamp_utc"].isin(te_times)

    X_tr = pdf.loc[tr_mask, feature_cols].values
    y_tr = pdf.loc[tr_mask, "target_excess_24h"].values
    X_te = pdf.loc[te_mask, feature_cols].values

    if len(X_te) == 0 or len(X_tr) == 0:
        continue

    # Asymmetric regularized CatBoost + LightGBM + Ridge Ensemble
    ridge = RidgeCV(alphas=np.logspace(-2, 3, 10)).fit(X_tr, y_tr)
    lgbm = lgb.LGBMRegressor(n_estimators=40, max_depth=4, num_leaves=15, learning_rate=0.03, random_state=42, n_jobs=-1, verbose=-1).fit(X_tr, y_tr)
    cat = CatBoostRegressor(iterations=40, depth=4, learning_rate=0.03, random_seed=42, thread_count=-1, verbose=0).fit(X_tr, y_tr)

    pdf.loc[te_mask, "pred"] = (
        0.20 * ridge.predict(X_te) +
        0.40 * lgbm.predict(X_te) +
        0.40 * cat.predict(X_te)
    )

print("4. Compiling Tournament Rank IC Metrics...")
oof = pdf[pdf["pred"] != 0.0].copy()

daily_ics = []
for t, group in oof.groupby("bucket_timestamp_utc"):
    if len(group) >= 20:
        corr, _ = spearmanr(group["pred"], group["target_excess_24h"])
        if not np.isnan(corr):
            daily_ics.append(corr)

mean_ic = np.mean(daily_ics)
std_ic = np.std(daily_ics) + 1e-6
ic_ir = mean_ic / std_ic
pct_positive = (np.array(daily_ics) > 0).mean() * 100

print("\n" + "=" * 70)
print("     STAGE 2 TOURNAMENT RESULTS: ORTHOGONAL FEATURE LIBRARY")
print("=" * 70)
print(f"Features Evaluated:             {len(feature_cols):8d}")
print(f"Mean Spearman Rank IC:          {mean_ic:8.4f} (Benchmark: > +0.0200)")
print(f"Information Ratio (IC / IC_std):{ic_ir:8.4f} (Benchmark: > +0.3000)")
print(f"Positive IC Period Win Rate:    {pct_positive:7.2f}%")
print(f"Total Out-of-Sample Timestamps: {len(daily_ics):8d}")
print("=" * 70)

# Extract top CatBoost feature importances
importances = cat.get_feature_importance()
top_feats = sorted(zip(feature_cols, importances), key=lambda x: x[1], reverse=True)
print("\nTop Predictive Features by CatBoost Split Gain:")
for feat, imp in top_feats[:8]:
    print(f"  - {feat:<35}: {imp:6.2f}%")
print("=" * 70)
