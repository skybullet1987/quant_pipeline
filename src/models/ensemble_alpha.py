import numpy as np
import pandas as pd
import polars as pl
from sklearn.linear_model import RidgeCV
import lightgbm as lgb
from catboost import CatBoostRegressor


def generate_ensemble_alphas(df: pl.DataFrame) -> pd.DataFrame:
    """Trains expanding-window tri-model ensemble on 24H forward demeaned returns."""
    # 1. Compute rolling predictors & 24H forward excess target
    enriched_df = (
        df.sort(["symbol", "bucket_timestamp_utc"])
        .with_columns([
            pl.col("close").pct_change(6).over("symbol").alias("ret_24h"),
            pl.col("close").pct_change(18).over("symbol").alias("ret_72h"),
            pl.col("close").pct_change(42).over("symbol").alias("ret_168h"),
            pl.col("close").pct_change(6).shift(-6).over("symbol").alias("fwd_ret_24h"),
        ])
    )

    market_mean_fwd = (
        enriched_df.group_by("bucket_timestamp_utc")
        .agg(pl.col("fwd_ret_24h").mean().alias("mkt_mean_fwd_24h"))
    )

    pdf = (
        enriched_df.join(market_mean_fwd, on="bucket_timestamp_utc")
        .with_columns([
            (pl.col("fwd_ret_24h") - pl.col("mkt_mean_fwd_24h")).alias("target_excess_24h")
        ])
        .to_pandas()
    )

    feature_cols = [
        "log_ret", "ret_24h", "ret_72h", "ret_168h",
        "rolling_24h_volatility", "cs_momentum_4h_percentile", "cs_liquidity_percentile"
    ]

    pdf = pdf.dropna(subset=feature_cols + ["target_excess_24h"])
    unique_times = pd.Series(pdf["bucket_timestamp_utc"].unique()).sort_values().reset_index(drop=True)

    n_train_bars = 2160    # 1 year warm-up
    retrain_step = 720     # 4 month retraining
    pdf["alpha_pred"] = 0.0

    for start_idx in range(n_train_bars, len(unique_times), retrain_step):
        end_idx = min(start_idx + retrain_step, len(unique_times))
        train_times = set(unique_times.iloc[:start_idx])
        test_times = set(unique_times.iloc[start_idx:end_idx])

        train_mask = pdf["bucket_timestamp_utc"].isin(train_times)
        test_mask = pdf["bucket_timestamp_utc"].isin(test_times)

        X_tr = pdf.loc[train_mask, feature_cols].values
        y_tr = pdf.loc[train_mask, "target_excess_24h"].values
        X_te = pdf.loc[test_mask, feature_cols].values

        if len(X_te) == 0 or len(X_tr) == 0:
            continue

        ridge = RidgeCV(alphas=np.logspace(-2, 3, 10))
        lgbm = lgb.LGBMRegressor(n_estimators=40, max_depth=4, num_leaves=15, learning_rate=0.03, random_state=42, n_jobs=-1, verbose=-1)
        cat = CatBoostRegressor(iterations=40, depth=4, learning_rate=0.03, random_seed=42, thread_count=-1, verbose=0)

        ridge.fit(X_tr, y_tr)
        lgbm.fit(X_tr, y_tr)
        cat.fit(X_tr, y_tr)

        pdf.loc[test_mask, "alpha_pred"] = (
            (0.20 * ridge.predict(X_te)) +
            (0.40 * lgbm.predict(X_te)) +
            (0.40 * cat.predict(X_te))
        )

    return pdf.pivot(index="bucket_timestamp_utc", columns="symbol", values="alpha_pred").fillna(0.0)
