import sys
import json
import warnings
from pathlib import Path
from datetime import datetime, timezone

PIPELINE_ROOT = Path.home() / "quant_pipeline"
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

warnings.filterwarnings("ignore")

import optuna
import numpy as np
import polars as pl
from scipy.stats import spearmanr
from catboost import CatBoost, Pool

optuna.logging.set_verbosity(optuna.logging.WARNING)

LAKE_FILE = PIPELINE_ROOT / "data" / "lake" / "features" / "pit_panel_4h.parquet"
MODEL_DIR = PIPELINE_ROOT / "data" / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

FEATURE_COLS = [
    "ret_4h", "ret_24h", "ret_72h", "ret_168h",
    "volume_zscore_72h", "basis_spread", "vol_yang_zhang", "beta_btc"
]

def optimize_horizon_model(train_df: pl.DataFrame, val_df: pl.DataFrame, target_col: str, n_trials: int = 12) -> dict:
    """Finds optimal tree depth, learning rate, and L2 regularization via Bayesian TPE."""
    X_tr = train_df.select(FEATURE_COLS).to_pandas()
    y_tr = train_df.select(target_col).to_series().to_numpy()
    grp_tr = train_df.select("group_id").to_series().to_numpy()

    X_val = val_df.select(FEATURE_COLS).to_pandas()
    y_val = val_df.select(target_col).to_series().to_numpy()
    grp_val = val_df.select("group_id").to_series().to_numpy()

    train_pool = Pool(X_tr, y_tr, group_id=grp_tr)
    val_pool = Pool(X_val, y_val, group_id=grp_val)

    def objective(trial):
        params = {
            "iterations": trial.suggest_int("iterations", 100, 300, step=50),
            "depth": trial.suggest_int("depth", 3, 6),
            "learning_rate": trial.suggest_float("learning_rate", 0.02, 0.07, log=True),
            "l2_leaf_reg": trial.suggest_float("l2_leaf_reg", 1.5, 10.0, log=True),
            "subsample": trial.suggest_float("subsample", 0.70, 0.90),
            "loss_function": "YetiRank",
            "eval_metric": "NDCG:top=5",
            "random_seed": 42,
            "thread_count": -1,
            "verbose": False
        }
        model = CatBoost(params).fit(train_pool, eval_set=val_pool, early_stopping_rounds=25, verbose=False)
        preds = model.predict(X_val)
        val_eval = val_df.with_columns(pl.Series("pred", preds))

        ics = []
        for grp in val_eval.select("group_id").to_series().unique().to_list():
            sub = val_eval.filter(pl.col("group_id") == grp)
            if sub.height >= 5:
                corr, _ = spearmanr(sub["pred"], sub[target_col])
                if not np.isnan(corr):
                    ics.append(corr)

        mean_ic = float(np.mean(ics)) if ics else 0.0
        ic_std = float(np.std(ics)) if ics else 1.0
        return mean_ic / (ic_std + 1e-6)

    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=42))
    study.optimize(objective, n_trials=n_trials)
    return study.best_params

def train_production_artifacts(rolling_train_bars: int = 1080, embargo_bars: int = 42) -> dict:
    print(f"[RETRAIN] Loading PIT Lake from {LAKE_FILE}...")
    raw_df = pl.read_parquet(LAKE_FILE)

    # 1. Target Construction
    df = raw_df.with_columns([
        (pl.col("close").shift(-3).over("symbol") / pl.col("close")).log().alias("fwd_ret_12h"),
        (pl.col("close").shift(-12).over("symbol") / pl.col("close")).log().alias("fwd_ret_48h"),
        (pl.col("close").shift(-42).over("symbol") / pl.col("close")).log().alias("fwd_ret_168h"),
    ])

    btc_targets = df.filter(pl.col("symbol") == "BTC").select([
        "timestamp_ms",
        pl.col("fwd_ret_12h").alias("btc_fwd_12h"),
        pl.col("fwd_ret_48h").alias("btc_fwd_48h"),
        pl.col("fwd_ret_168h").alias("btc_fwd_168h"),
    ])
    df = df.join(btc_targets, on="timestamp_ms", how="left")

    df = df.with_columns([
        (-1.0 * (pl.col("fwd_ret_12h") - (pl.col("beta_btc") * pl.col("btc_fwd_12h"))) / (pl.col("vol_yang_zhang") + 1e-6)).alias("target_12h_reversion"),
        ((pl.col("fwd_ret_48h") - (pl.col("beta_btc") * pl.col("btc_fwd_48h"))) / (pl.col("vol_yang_zhang") + 1e-6)).alias("target_48h_drift"),
        ((pl.col("fwd_ret_168h") - (pl.col("beta_btc") * pl.col("btc_fwd_168h"))) / (pl.col("vol_yang_zhang") + 1e-6)).alias("target_168h_trend")
    ]).drop_nulls(subset=FEATURE_COLS + ["target_12h_reversion", "target_48h_drift", "target_168h_trend"])

    unique_ts = sorted(df.select("timestamp_ms").to_series().unique().to_list())
    ts_to_grp = {ts: idx for idx, ts in enumerate(unique_ts)}
    df = df.with_columns(pl.col("timestamp_ms").replace(ts_to_grp).alias("group_id")).sort(["group_id", "symbol"])

    max_grp = max(ts_to_grp.values())
    train_end = max_grp - embargo_bars
    train_start = max(0, train_end - rolling_train_bars)
    val_start = max(0, train_end - 180)  # 30-day internal validation fold

    train_fold = df.filter((pl.col("group_id") >= train_start) & (pl.col("group_id") < val_start))
    val_fold = df.filter((pl.col("group_id") >= val_start) & (pl.col("group_id") < train_end))
    full_train = df.filter((pl.col("group_id") >= train_start) & (pl.col("group_id") < train_end))

    print(f"[RETRAIN] Training Window: Groups {train_start} to {train_end} ({full_train.height:,} samples across {full_train.select('symbol').n_unique()} tokens)")

    X_full = full_train.select(FEATURE_COLS).to_pandas()
    grp_full = full_train.select("group_id").to_series().to_numpy()

    # 2. Bayesian Tuning & Fitting for 12H, 48H, 168H
    print("[RETRAIN] Tuning 12H Reversion Model...")
    p12 = optimize_horizon_model(train_fold, val_fold, "target_12h_reversion")
    m12 = CatBoost({**p12, "loss_function": "YetiRank", "thread_count": -1, "verbose": False}).fit(
        Pool(X_full, full_train.select("target_12h_reversion").to_series().to_numpy(), group_id=grp_full)
    )
    m12.save_model(str(MODEL_DIR / "catboost_12h_reversion.cbm"))

    print("[RETRAIN] Tuning 48H Drift Model...")
    p48 = optimize_horizon_model(train_fold, val_fold, "target_48h_drift")
    m48 = CatBoost({**p48, "loss_function": "YetiRank", "thread_count": -1, "verbose": False}).fit(
        Pool(X_full, full_train.select("target_48h_drift").to_series().to_numpy(), group_id=grp_full)
    )
    m48.save_model(str(MODEL_DIR / "catboost_48h_drift.cbm"))

    print("[RETRAIN] Tuning 168H Trend Model...")
    p168 = optimize_horizon_model(train_fold, val_fold, "target_168h_trend")
    m168 = CatBoost({**p168, "loss_function": "YetiRank", "thread_count": -1, "verbose": False}).fit(
        Pool(X_full, full_train.select("target_168h_trend").to_series().to_numpy(), group_id=grp_full)
    )
    m168.save_model(str(MODEL_DIR / "catboost_168h_trend.cbm"))

    # 3. Register Production Metadata
    meta = {
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "training_bars": train_end - train_start,
        "embargo_bars": embargo_bars,
        "feature_cols": FEATURE_COLS,
        "best_params": {"m12": p12, "m48": p48, "m168": p168},
        "ensemble_weights": {"reversion_12h": 0.30, "drift_48h": 0.45, "trend_168h": 0.25},
        "portfolio_params": {
            "top_k": 8,
            "max_gross_leverage": 1.75,
            "crisis_vol_threshold": 0.045,
            "crisis_gross_leverage": 0.50,
            "target_carry_leverage": 0.50
        }
    }
    
    meta_path = MODEL_DIR / "multiscale_meta.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    print(f"[RETRAIN] All artifacts materialized successfully -> {meta_path}")
    return meta

if __name__ == "__main__":
    train_production_artifacts()
