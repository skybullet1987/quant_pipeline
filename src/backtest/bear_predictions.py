import pickle
from pathlib import Path
import numpy as np
import polars as pl
from catboost import CatBoostRanker, Pool

CACHE_DIR = Path.home() / "quant_pipeline" / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def precompute_bear_holdout_predictions(
    df: pl.DataFrame, start_eval: int = 2768, end_eval: int = 4083, retrain_step: int = 42
):
    cache_file = CACHE_DIR / f"bear_preds_{start_eval}_{end_eval}_{retrain_step}.pkl"
    if cache_file.exists():
        print(f"\n[CACHE] Found precomputed predictions at {cache_file} -> Loading directly...")
        with open(cache_file, "rb") as f:
            return pickle.load(f)

    print(f"\n[PASS 1] Precomputing Rolling OOS Predictions ({start_eval} -> {end_eval})...")
    drop_cols = {
        "symbol", "timestamp", "timestamp_ms", "group_id", "close", "high", "low", "volume", 
        "open", "num_trades", "target_12h_alpha", "target_48h_drift", "target_168h_trend", 
        "atr_14", "beta_btc", "ret_4h", "basis_spread", "funding_rate", "volume_zscore_72h", 
        "vol_yang_zhang", "fwd_ret_12h", "fwd_ret_48h", "fwd_ret_168h", "btc_fwd_12h", 
        "btc_fwd_48h", "btc_fwd_168h", "btc_ret_4h", "fwd_ret_72h", "btc_fwd_ret_72h", 
        "target_residual_drift"
    }
    feature_cols = [c for c in df.columns if c not in drop_cols]
    preds_12, preds_48, preds_168, hmm_data = {}, {}, {}, {}
    total_steps = ((end_eval - start_eval) // retrain_step) + 1
    step_idx = 0

    for chunk_start in range(start_eval, end_eval, retrain_step):
        step_idx += 1
        chunk_end = min(chunk_start + retrain_step, end_eval)
        print(f" • Training Block {step_idx}/{total_steps} (Groups {chunk_start} -> {chunk_end})...")

        train_df = df.filter(pl.col("group_id") < chunk_start)
        eval_df = df.filter((pl.col("group_id") >= chunk_start) & (pl.col("group_id") < chunk_end))

        # HMM training observations (last 1500 bars)
        btc_tr = train_df.filter(pl.col("symbol") == "BTC").sort("group_id")
        vol_arr = btc_tr.select("vol_yang_zhang").to_numpy().flatten()
        vol_mean = train_df.group_by("group_id").agg(pl.mean("volume_zscore_72h").alias("mvz")).sort("group_id").select("mvz").to_numpy().flatten()
        min_len = min(len(vol_arr), len(vol_mean), 1500)
        hmm_obs = np.column_stack([vol_arr[-min_len:], vol_mean[-min_len:], np.full(min_len, 0.002)])
        for g in range(chunk_start, chunk_end):
            hmm_data[g] = hmm_obs

        # Rolling CatBoost models
        for horizon, target_col, p_dict in [
            ("12h", "target_12h_alpha", preds_12),
            ("48h", "target_48h_drift", preds_48),
            ("168h", "target_168h_trend", preds_168)
        ]:
            clean_tr = train_df.filter(pl.col(target_col).is_not_null())
            tr_pool = Pool(
                data=clean_tr.select(feature_cols).to_pandas(),
                label=clean_tr.select(target_col).to_series().to_numpy(),
                group_id=clean_tr.select("group_id").to_series().to_numpy()
            )
            model = CatBoostRanker(iterations=180, learning_rate=0.06, depth=5, loss_function="YetiRank", verbose=False, random_seed=42)
            model.fit(tr_pool)

            for g in range(chunk_start, chunk_end):
                g_df = eval_df.filter(pl.col("group_id") == g)
                if g_df.height > 0:
                    p = model.predict(g_df.select(feature_cols).to_pandas())
                    p_dict[g] = {s: float(v) for s, v in zip(g_df.select("symbol").to_series(), p)}

    with open(cache_file, "wb") as f:
        pickle.dump((preds_12, preds_48, preds_168, hmm_data), f)
    print(f"[CACHE] Saved precomputed predictions to {cache_file}")

    return preds_12, preds_48, preds_168, hmm_data
