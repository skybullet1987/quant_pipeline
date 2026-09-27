"""
Walk-Forward Window Stability Experiment Harness (4H Horizon).
Compares 6M, 12M, 18M, 24M, 36M, and Expanding training windows.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import logging
import numpy as np
import polars as pl
from sklearn.metrics import brier_score_loss, roc_auc_score
from catboost import CatBoostClassifier
import mlflow

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def run_window_stability_grid():
    feature_path = "/tmp/lake/features/pit_panel_4h.parquet"
    if not os.path.exists(feature_path):
        raise FileNotFoundError(f"Feature dataset not found: {feature_path}")

    df = pl.read_parquet(feature_path).sort("bucket_timestamp_utc")
    logger.info("Loaded panel with %d observations across universe.", df.height)

    feature_cols = [
        "asset_age_days",
        "rolling_24h_volume_usd",
        "rolling_24h_volatility",
        "cs_liquidity_percentile",
        "cs_momentum_4h_percentile",
        "log_ret"
    ]

    unique_times = df["bucket_timestamp_utc"].unique().sort().to_list()
    total_periods = len(unique_times)
    logger.info("Total unique 4H timestamps: %d (%s to %s)", total_periods, unique_times[0], unique_times[-1])

    window_configs = {
        "6_Months": 180 * 6,
        "12_Months": 365 * 6,
        "18_Months": 540 * 6,
        "24_Months": 730 * 6,
        "36_Months": 1095 * 6,
        "Expanding": None,
    }

    test_period_bars = 90 * 6   # 90-day walk-forward test slices
    min_warmup_bars = 365 * 6   # 1-year initial warmup

    mlflow.set_tracking_uri("sqlite:////tmp/mlflow/mlflow.db")
    mlflow.set_experiment("window_stability_experiments")

    for w_name, w_size in window_configs.items():
        logger.info("==================== Evaluating Window: %s ====================", w_name)
        oos_aucs, oos_briers, oos_sharpes = [], [], []

        for test_start_idx in range(min_warmup_bars, total_periods - test_period_bars, test_period_bars):
            test_end_idx = test_start_idx + test_period_bars
            train_start_idx = 0 if w_size is None else max(0, test_start_idx - w_size)

            t_train_start = unique_times[train_start_idx]
            t_test_start = unique_times[test_start_idx]
            t_test_end = unique_times[test_end_idx - 1]

            df_train = df.filter((pl.col("bucket_timestamp_utc") >= t_train_start) & (pl.col("bucket_timestamp_utc") < t_test_start))
            df_test = df.filter((pl.col("bucket_timestamp_utc") >= t_test_start) & (pl.col("bucket_timestamp_utc") <= t_test_end))

            X_train = df_train.select(feature_cols).to_numpy()
            y_train = (df_train.select(pl.col("log_ret").shift(-1).fill_null(0.0)).to_numpy().flatten() > 0.0).astype(int)

            X_test = df_test.select(feature_cols).to_numpy()
            y_test = (df_test.select(pl.col("log_ret").shift(-1).fill_null(0.0)).to_numpy().flatten() > 0.0).astype(int)
            ret_test = df_test["log_ret"].to_numpy()

            if len(X_train) == 0 or len(X_test) == 0:
                continue

            cb = CatBoostClassifier(iterations=120, depth=4, learning_rate=0.05, verbose=0, random_seed=42)
            cb.fit(X_train, y_train)
            probs = cb.predict_proba(X_test)[:, 1]

            auc = float(roc_auc_score(y_test, probs)) if len(np.unique(y_test)) > 1 else 0.5
            brier = float(brier_score_loss(y_test, probs))

            # Long top quintile (p > 0.53), Short bottom quintile (p < 0.47)
            pos = np.where(probs > 0.53, 1.0, np.where(probs < 0.47, -1.0, 0.0))
            strategy_rets = pos * ret_test
            mean_r = np.mean(strategy_rets)
            std_r = np.std(strategy_rets)
            sharpe = float((mean_r / std_r) * np.sqrt(2190)) if std_r > 0 else 0.0

            oos_aucs.append(auc)
            oos_briers.append(brier)
            oos_sharpes.append(sharpe)

        mean_auc = float(np.mean(oos_aucs)) if oos_aucs else 0.5
        mean_brier = float(np.mean(oos_briers)) if oos_briers else 0.25
        mean_sharpe = float(np.mean(oos_sharpes)) if oos_sharpes else 0.0

        with mlflow.start_run(run_name=f"window_{w_name}"):
            mlflow.log_param("window_name", w_name)
            mlflow.log_param("window_bars", w_size if w_size else "Expanding")
            mlflow.log_metrics({
                "mean_oos_auc": mean_auc,
                "mean_oos_brier": mean_brier,
                "mean_oos_sharpe": mean_sharpe,
            })

        logger.info(
            "[%s Complete] Mean OOS AUC: %.4f | Mean Brier: %.4f | Mean OOS Sharpe: %.2f",
            w_name, mean_auc, mean_brier, mean_sharpe
        )


if __name__ == "__main__":
    run_window_stability_grid()
