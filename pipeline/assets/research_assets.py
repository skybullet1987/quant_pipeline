from __future__ import annotations

import os
from pathlib import Path
import joblib
import numpy as np
import polars as pl
from dagster import Output, asset
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

try:
    import mlflow
except (ImportError, ModuleNotFoundError):
    mlflow = None

from pipeline.research.regime import BOCDConfig, BOCDDetector, GaussianHMMRegime
from pipeline.research.stacking import TriModelStacker


@asset(
    group_name="research",
    description="Extracts 1-minute bar regime probabilities per symbol across all validated DEX assets."
)
def market_regime_features(context, dqg_validated_trades: list[str]) -> Output[str]:
    all_bars: list[pl.DataFrame] = []
    total_processed_ticks = 0

    for idx, clean_path in enumerate(dqg_validated_trades):
        if not os.path.exists(clean_path):
            continue

        try:
            df_asset_bars = (
                pl.scan_parquet(clean_path)
                .with_columns((pl.col("timestamp_ms") // 60_000 * 60_000).alias("bar_time_ms"))
                .group_by(["symbol", "bar_time_ms"])
                .agg([
                    pl.col("price").first().alias("open"),
                    pl.col("price").max().alias("high"),
                    pl.col("price").min().alias("low"),
                    pl.col("price").last().alias("close"),
                    pl.col("size").sum().alias("volume"),
                    (pl.col("price") * pl.col("size")).sum().alias("notional"),
                    pl.len().alias("tick_count"),
                ])
                .sort("bar_time_ms")
                .with_columns((pl.col("notional") / pl.col("volume")).cast(pl.Float32).alias("vwap"))
                .collect(engine="streaming")
            )

            if df_asset_bars.height < 10:
                continue

            prices = df_asset_bars["close"].to_numpy()
            log_rets = np.zeros(len(prices), dtype=np.float32)
            log_rets[1:] = np.diff(np.log(prices))

            hmm = GaussianHMMRegime()
            hmm_probs = hmm.process_series(log_rets)

            bocd = BOCDDetector(BOCDConfig(hazard_lambda=60.0))
            bocd_hazards = np.array([bocd.update(float(r)) for r in log_rets], dtype=np.float32)

            enriched = df_asset_bars.with_columns([
                pl.Series("log_ret", log_rets, dtype=pl.Float32),
                pl.Series("p_trend", hmm_probs[:, 0], dtype=pl.Float32),
                pl.Series("p_chop", hmm_probs[:, 1], dtype=pl.Float32),
                pl.Series("p_expansion", hmm_probs[:, 2], dtype=pl.Float32),
                pl.Series("p_hazard", bocd_hazards, dtype=pl.Float32),
            ])
            all_bars.append(enriched)
            total_processed_ticks += df_asset_bars["tick_count"].sum()

        except Exception as e:
            context.log.warning(f"Error processing bar regimes for {clean_path}: {e}")
            continue

    if not all_bars:
        raise ValueError("No valid bar features extracted from universe partitions.")

    combined_df = pl.concat(all_bars)
    output_path = "/tmp/lake/features/regime_features.parquet"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    combined_df.write_parquet(output_path, compression="zstd")

    context.log.info(
        f"Extracted {combined_df.height:,} 1-min bars across {len(all_bars)} assets "
        f"({total_processed_ticks:,} source ticks) -> {output_path}"
    )
    return Output(
        value=output_path,
        metadata={
            "total_bars": combined_df.height,
            "assets_count": len(all_bars),
            "output_path": output_path,
        }
    )


@asset(
    group_name="research",
    description="Trains cross-sectional TriModelStacker across full multi-asset regime features."
)
def trained_meta_learner(context, market_regime_features: str) -> Output[str]:
    df = pl.read_parquet(market_regime_features)
    
    y_target = (df["log_ret"].shift(-1).fill_null(0.0).to_numpy() > 0.0).astype(int)
    feature_cols = ["p_trend", "p_chop", "p_expansion", "p_hazard", "log_ret"]
    X = df.select(feature_cols).to_numpy()

    split_idx = int(len(X) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y_target[:split_idx], y_target[split_idx:]

    stacker = TriModelStacker(cv_splits=3, purge_window=2)
    stacker.fit(X_train, y_train)

    probs = stacker.predict_proba(X_test)
    brier = float(brier_score_loss(y_test, probs[:, 1]))
    loss = float(log_loss(y_test, probs[:, 1]))
    auc = float(roc_auc_score(y_test, probs[:, 1])) if len(np.unique(y_test)) > 1 else 0.5

    model_artifact_path = "/tmp/models/tri_model_stacker.joblib"
    os.makedirs(os.path.dirname(model_artifact_path), exist_ok=True)
    joblib.dump(stacker, model_artifact_path)

    if mlflow is not None:
        try:
            mlflow_dir = Path("/tmp/mlflow")
            mlflow_dir.mkdir(parents=True, exist_ok=True)
            mlflow.set_tracking_uri("sqlite:////tmp/mlflow/mlflow.db")
            mlflow.set_experiment("layer1_research_fabric")

            with mlflow.start_run(run_name="full_universe_tri_stacker"):
                mlflow.log_params({
                    "n_samples": len(X),
                    "features": feature_cols,
                })
                mlflow.log_metrics({
                    "val_brier_score": brier,
                    "val_log_loss": loss,
                    "val_roc_auc": auc,
                })
                mlflow.log_artifact(model_artifact_path, artifact_path="model")
        except Exception as e:
            context.log.warning(f"MLflow tracking skipped: {e}")

    context.log.info(f"Full-universe meta-learner trained. Brier: {brier:.4f}, AUC: {auc:.4f}")

    return Output(
        value=model_artifact_path,
        metadata={"val_brier_score": brier, "val_log_loss": loss, "val_roc_auc": auc}
    )
