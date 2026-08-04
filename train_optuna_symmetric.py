import os
import json
import gc
import warnings
import numpy as np
import pandas as pd
import optuna
from catboost import CatBoostClassifier, Pool
from sklearn.metrics import roc_auc_score

warnings.filterwarnings('ignore')
optuna.logging.set_verbosity(optuna.logging.WARNING)

PARQUET_FILE = "feature_matrix_symmetric.parquet"
MODEL_DIR = "production_models"
os.makedirs(MODEL_DIR, exist_ok=True)

N_TRIALS = 30
PURGE_MINUTES = 30

def load_and_preprocess():
    print(f"Loading {PARQUET_FILE}...")
    df = pd.read_parquet(PARQUET_FILE)
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    # --- MEMORY OPTIMIZATION 1: HPO Truncation ---
    # We only need a representative sample to find parameters. 
    # Using the most recent 2.5M rows prevents OOM crashes.
    if len(df) > 2500000:
        print(f"Truncating from {len(df):,} to 2,500,000 rows for memory-safe HPO...")
        df = df.tail(2500000).reset_index(drop=True)

    # --- MEMORY OPTIMIZATION 2: Downcasting ---
    for col in df.select_dtypes(include=['float64']).columns:
        df[col] = df[col].astype('float32')
    for col in df.select_dtypes(include=['int64']).columns:
        df[col] = pd.to_numeric(df[col], downcast='integer')
    
    # Deduplicate suffixes if present
    for col in [c for c in df.columns if c.endswith('_y')]:
        base_col = col[:-2]
        df[base_col] = df[col]
        df = df.drop(columns=[f"{base_col}_x", col], errors='ignore')

    df['ticker'] = df['ticker'].astype(str)
    df['hour_of_day'] = df['timestamp'].dt.hour.astype(str)
    df['day_of_week'] = df['timestamp'].dt.dayofweek.astype(str)
    
    exclude_cols = ['timestamp', 'ticker', 'hour_of_day', 'day_of_week', 'target_tbm', 'tbm_realized_return', 'log_ret_1m']
    base_features = [c for c in df.columns if c not in exclude_cols and pd.api.types.is_numeric_dtype(df[c])]
    cat_features = ['ticker', 'hour_of_day', 'day_of_week']
    
    return df, base_features + cat_features, cat_features

def evaluate_walk_forward_fold(df, all_features, cat_features, params, direction='long'):
    """Performs 3-fold temporal walk-forward cross-validation with a 30m purge embargo."""
    timestamps = df['timestamp'].sort_values().unique()
    n_splits = 3
    split_size = len(timestamps) // (n_splits + 1)
    
    auc_scores = []
    
    target_col = (df['target_tbm'] == (1 if direction == 'long' else -1)).astype(np.int8)
    
    for i in range(1, n_splits + 1):
        train_end_idx = i * split_size
        test_end_idx = (i + 1) * split_size
        
        train_ts = timestamps[:train_end_idx]
        test_ts = timestamps[train_end_idx + PURGE_MINUTES : test_end_idx]
        
        train_mask = df['timestamp'].isin(train_ts)
        test_mask = df['timestamp'].isin(test_ts)
        
        y_tr = target_col[train_mask]
        y_te = target_col[test_mask]
        
        if y_tr.nunique() < 2 or y_te.nunique() < 2:
            continue
            
        pool_tr = Pool(df.loc[train_mask, all_features], label=y_tr, cat_features=cat_features)
        pool_te = Pool(df.loc[test_mask, all_features], label=y_te, cat_features=cat_features)
        
        scale_pos = (len(y_tr) - y_tr.sum()) / (y_tr.sum() + 1e-8)
        
        model_params = params.copy()
        model_params['scale_pos_weight'] = scale_pos
        
        # --- MEMORY OPTIMIZATION 3: Thread limits ---
        model_params['thread_count'] = 8 
        
        model = CatBoostClassifier(**model_params)
        model.fit(pool_tr, eval_set=pool_te, early_stopping_rounds=30, verbose=0, use_best_model=True)
        
        preds = model.predict_proba(pool_te)[:, 1]
        auc = roc_auc_score(y_te, preds)
        auc_scores.append(auc)
        
        # --- MEMORY OPTIMIZATION 4: Aggressive GC ---
        del pool_tr, pool_te, model, train_mask, test_mask, y_tr, y_te, preds
        gc.collect()
        
    return np.mean(auc_scores) if auc_scores else 0.50

def main():
    df, all_features, cat_features = load_and_preprocess()
    print(f"Data ingested. Features: {len(all_features)} | Total Rows: {len(df):,}")
    
    # ---------------------------------------------------------
    # OPTUNA STUDY FOR LONG DIRECTION (+1.5σ)
    # ---------------------------------------------------------
    print("\n--- Phase 1A: Optimizing CatBoost for LONG Setups (+1.5σ) ---")
    
    def objective_long(trial):
        params = {
            'iterations': trial.suggest_int('iterations', 200, 600, step=100),
            'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.10, log=True),
            'depth': trial.suggest_int('depth', 4, 8),
            'l2_leaf_reg': trial.suggest_float('l2_leaf_reg', 2.0, 15.0),
            'random_strength': trial.suggest_float('random_strength', 1.0, 10.0),
            'subsample': trial.suggest_float('subsample', 0.6, 1.0),
            'random_seed': 42
        }
        return evaluate_walk_forward_fold(df, all_features, cat_features, params, direction='long')

    study_long = optuna.create_study(direction="maximize")
    study_long.optimize(objective_long, n_trials=N_TRIALS)
    print(f"[LONG] Best Trial OOS AUC: {study_long.best_value:.4f}")
    print(f"[LONG] Best Params: {study_long.best_params}")

    # ---------------------------------------------------------
    # OPTUNA STUDY FOR SHORT DIRECTION (-1.5σ)
    # ---------------------------------------------------------
    print("\n--- Phase 1B: Optimizing CatBoost for SHORT Setups (-1.5σ) ---")
    
    def objective_short(trial):
        params = {
            'iterations': trial.suggest_int('iterations', 200, 600, step=100),
            'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.10, log=True),
            'depth': trial.suggest_int('depth', 4, 8),
            'l2_leaf_reg': trial.suggest_float('l2_leaf_reg', 2.0, 15.0),
            'random_strength': trial.suggest_float('random_strength', 1.0, 10.0),
            'subsample': trial.suggest_float('subsample', 0.6, 1.0),
            'random_seed': 42
        }
        return evaluate_walk_forward_fold(df, all_features, cat_features, params, direction='short')

    study_short = optuna.create_study(direction="maximize")
    study_short.optimize(objective_short, n_trials=N_TRIALS)
    print(f"[SHORT] Best Trial OOS AUC: {study_short.best_value:.4f}")
    print(f"[SHORT] Best Params: {study_short.best_params}")

    # ---------------------------------------------------------
    # EXPORT OPTIMAL PARAMETERS
    # ---------------------------------------------------------
    optimal_params = {
        'long_model': study_long.best_params,
        'short_model': study_short.best_params,
        'long_best_auc': study_long.best_value,
        'short_best_auc': study_short.best_value
    }
    
    out_file = os.path.join(MODEL_DIR, "optimal_params_symmetric.json")
    with open(out_file, "w") as f:
        json.dump(optimal_params, f, indent=4)
        
    print(f"\n[SUCCESS] Symmetric hyperparameter optimization complete.")
    print(f"Optimal parameters saved to {out_file}")

if __name__ == "__main__":
    main()
