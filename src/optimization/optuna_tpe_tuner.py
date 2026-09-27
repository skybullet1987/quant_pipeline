import sys
import json
from pathlib import Path

PIPELINE_ROOT = Path.home() / "quant_pipeline"
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

import numpy as np
import polars as pl
import optuna
from catboost import CatBoost, Pool
from scipy.stats import spearmanr

LAKE_FILE = PIPELINE_ROOT / "data" / "lake" / "features" / "pit_panel_4h.parquet"
MODEL_DIR = PIPELINE_ROOT / "data" / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
MODEL_OUT = MODEL_DIR / "catboost_tail_alpha_v1.cbm"
META_OUT = MODEL_DIR / "model_metadata.json"

FEATURE_COLS = [
    "ret_4h",
    "ret_24h",
    "ret_72h",
    "ret_168h",
    "volume_zscore_72h",
    "basis_spread",
    "vol_yang_zhang",
    "beta_btc"
]
TARGET_COL = "target_residual_drift"

def prepare_data():
    df = pl.read_parquet(LAKE_FILE).drop_nulls(subset=FEATURE_COLS + [TARGET_COL])
    
    # Map timestamps to discrete integer group IDs for pairwise ranking
    unique_ts = sorted(df.select("timestamp_ms").to_series().unique().to_list())
    ts_to_group = {ts: idx for idx, ts in enumerate(unique_ts)}
    
    df = df.with_columns(
        pl.col("timestamp_ms").replace(ts_to_group).alias("group_id")
    ).sort(["group_id", "symbol"])

    n_groups = len(unique_ts)
    train_split = int(n_groups * 0.70)
    embargo_split = train_split + 42  # 7-day embargo (42 4H bars)

    train_df = df.filter(pl.col("group_id") < train_split)
    val_df = df.filter(pl.col("group_id") >= embargo_split)

    return train_df, val_df, df

def objective(trial, train_df, val_df):
    params = {
        "iterations": trial.suggest_int("iterations", 300, 800, step=100),
        "depth": trial.suggest_int("depth", 3, 7),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.08, log=True),
        "l2_leaf_reg": trial.suggest_float("l2_leaf_reg", 1.0, 15.0, log=True),
        "subsample": trial.suggest_float("subsample", 0.65, 0.95),
        "loss_function": "YetiRank",
        "eval_metric": "NDCG:top=5",
        "random_seed": 42,
        "verbose": False
    }

    train_pool = Pool(
        data=train_df.select(FEATURE_COLS).to_pandas(),
        label=train_df.select(TARGET_COL).to_series().to_numpy(),
        group_id=train_df.select("group_id").to_series().to_numpy()
    )

    val_pool = Pool(
        data=val_df.select(FEATURE_COLS).to_pandas(),
        label=val_df.select(TARGET_COL).to_series().to_numpy(),
        group_id=val_df.select("group_id").to_series().to_numpy()
    )

    model = CatBoost(params)
    model.fit(train_pool, eval_set=val_pool, early_stopping_rounds=40, verbose=False)

    val_preds = model.predict(val_df.select(FEATURE_COLS).to_pandas())
    val_eval = val_df.with_columns(pl.Series("pred", val_preds))

    # Compute rolling rank Information Coefficient (IC) per timestamp group
    ic_list = []
    for grp in val_eval.select("group_id").to_series().unique().to_list():
        sub = val_eval.filter(pl.col("group_id") == grp)
        if sub.height >= 5:
            corr, _ = spearmanr(sub["pred"], sub[TARGET_COL])
            if not np.isnan(corr):
                ic_list.append(corr)

    mean_ic = float(np.mean(ic_list)) if ic_list else 0.0
    ic_std = float(np.std(ic_list)) if ic_list else 1.0
    ic_ir = mean_ic / (ic_std + 1e-6)

    # Score: blended objective maximizing rank IC stability
    return ic_ir

def run_tuner(n_trials: int = 25):
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    print(f"[TUNER] Initializing Bayesian Optimization on {len(FEATURE_COLS)} features across 99 assets...")
    
    train_df, val_df, full_df = prepare_data()
    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=42))
    
    study.optimize(lambda trial: objective(trial, train_df, val_df), n_trials=n_trials, show_progress_bar=True)

    best_params = study.best_params
    best_ir = study.best_value
    print(f"\n[TUNER] Bayesian Optimization Complete!")
    print(f"[TUNER] Optimal Information Ratio (IC_IR): {best_ir:.4f}")
    print(f"[TUNER] Best Hyperparameters: {best_params}")

    # Retrain final production model on full dataset with optimal parameters
    print("[TUNER] Retraining production CatBoost YetiRank engine on full panel...")
    final_params = {
        **best_params,
        "loss_function": "YetiRank",
        "eval_metric": "NDCG:top=5",
        "random_seed": 42,
        "verbose": False
    }

    full_pool = Pool(
        data=full_df.select(FEATURE_COLS).to_pandas(),
        label=full_df.select(TARGET_COL).to_series().to_numpy(),
        group_id=full_df.select("group_id").to_series().to_numpy()
    )

    final_model = CatBoost(final_params)
    final_model.fit(full_pool)
    final_model.save_model(str(MODEL_OUT))

    # Compute latest volatility metadata for daemon execution
    latest_ts = full_df.select(pl.max("timestamp_ms")).to_series()[0]
    latest_rows = full_df.filter(pl.col("timestamp_ms") == latest_ts)
    yz_map = {row["symbol"]: float(row["vol_yang_zhang"]) for row in latest_rows.iter_rows(named=True)}

    with open(META_OUT, "w") as f:
        json.dump({
            "features": FEATURE_COLS,
            "target": TARGET_COL,
            "best_params": best_params,
            "best_ic_ir": best_ir,
            "universe_size": full_df.select("symbol").n_unique(),
            "latest_yz_vol": yz_map
        }, f, indent=2)

    print(f"[TUNER] Production Model Serialized -> {MODEL_OUT}")
    print(f"[TUNER] Model Metadata Serialized  -> {META_OUT}")

if __name__ == "__main__":
    run_tuner(n_trials=25)
