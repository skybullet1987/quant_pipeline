import os
import gc
import json
import joblib
import datetime
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier, Pool
from sklearn.linear_model import LogisticRegression
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import brier_score_loss

PARQUET_FILE = "feature_matrix_symmetric.parquet"
PARAMS_FILE = "production_models/optimal_params_symmetric.json"
BUNDLE_DIR = "model_bundle_v1.0.0"

def select_best_calibrator(raw_probs, y_true):
    if len(np.unique(y_true)) < 2:
        return LogisticRegression().fit(np.zeros((len(y_true),1)), y_true), "Platt"
    y_bin = (y_true == 1).astype(int)
    
    platt = LogisticRegression(C=1.0, solver='lbfgs')
    platt.fit(raw_probs.reshape(-1, 1), y_bin)
    platt_probs = platt.predict_proba(raw_probs.reshape(-1, 1))[:, 1]
    platt_brier = brier_score_loss(y_bin, platt_probs)
    
    iso = IsotonicRegression(out_of_bounds='clip')
    iso.fit(raw_probs, y_bin)
    iso_probs = iso.predict(raw_probs)
    iso_brier = brier_score_loss(y_bin, iso_probs)
    
    return (iso, "Isotonic") if iso_brier < platt_brier else (platt, "Platt")

def build_production_bundle():
    print(f"Creating Bundle Directory: {BUNDLE_DIR}...")
    os.makedirs(BUNDLE_DIR, exist_ok=True)
    
    print(f"Loading Hyperparameters ({PARAMS_FILE})...")
    with open(PARAMS_FILE, "r") as f:
        opt_params = json.load(f)
        
    long_params = opt_params['long_model']
    short_params = opt_params['short_model']
    long_params.update({'verbose': 100, 'random_seed': 42})
    short_params.update({'verbose': 100, 'random_seed': 42})

    print(f"Loading Full Dataset ({PARQUET_FILE})...")
    df = pd.read_parquet(PARQUET_FILE)
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    
    # MEMORY OPTIMIZATION 1: Truncate to Rolling Window (Post Jan 1, 2024)
    cutoff_date = pd.to_datetime('2024-01-01', utc=True)
    df = df[df['timestamp'] >= cutoff_date]
    df = df.sort_values('timestamp').reset_index(drop=True)
    print(f"Dataset truncated to post-2024. Remaining rows: {len(df):,}")

    # Clean up duplicate columns
    drop_cols = []
    for col in [c for c in df.columns if c.endswith('_y')]:
        base_col = col[:-2]
        df[base_col] = df[col]
        drop_cols.extend([f"{base_col}_x", col])
    
    df.drop(columns=[c for c in drop_cols if c in df.columns], inplace=True, errors='ignore')
    gc.collect()

    # MEMORY OPTIMIZATION 2: Downcast float64 to float32
    print("Downcasting float64 to float32...")
    float_cols = df.select_dtypes(include=['float64']).columns
    df[float_cols] = df[float_cols].astype('float32')
    gc.collect()

    df['ticker'] = df['ticker'].astype(str)
    df['hour_of_day'] = df['timestamp'].dt.hour.astype(str)
    df['day_of_week'] = df['timestamp'].dt.dayofweek.astype(str)
    
    exclude_cols = ['timestamp', 'ticker', 'hour_of_day', 'day_of_week', 'target_tbm', 'tbm_realized_return']
    base_features = [c for c in df.columns if c not in exclude_cols and pd.api.types.is_numeric_dtype(df[c])]
    cat_features = ['ticker', 'hour_of_day', 'day_of_week']
    all_features = base_features + cat_features

    # 1. Export Feature Schema
    feature_schema = {
        'all_features': all_features,
        'base_features': base_features,
        'cat_features': cat_features,
        'feature_count': len(all_features)
    }
    with open(f"{BUNDLE_DIR}/feature_schema.json", "w") as f:
        json.dump(feature_schema, f, indent=4)

    # 2. Train Full-Data LONG Model
    print("\n--- Training Production LONG Expert ---")
    y_long = (df['target_tbm'] == 1).astype(int)
    pool_long = Pool(df[all_features], label=y_long, cat_features=cat_features)
    long_params['scale_pos_weight'] = (len(y_long) - sum(y_long)) / (sum(y_long) + 1e-8)
    
    model_long = CatBoostClassifier(**long_params)
    model_long.fit(pool_long)
    model_long.save_model(f"{BUNDLE_DIR}/long_expert.cbm")
    
    raw_probs_long = model_long.predict_proba(pool_long)[:, 1]
    calibrator_long, cal_type_l = select_best_calibrator(raw_probs_long, y_long)
    joblib.dump(calibrator_long, f"{BUNDLE_DIR}/calibrator_long.pkl")

    # MEMORY OPTIMIZATION 3: Free RAM before Short Training
    del pool_long
    del y_long
    del raw_probs_long
    gc.collect()

    # 3. Train Full-Data SHORT Model
    print("\n--- Training Production SHORT Expert ---")
    y_short = (df['target_tbm'] == -1).astype(int)
    pool_short = Pool(df[all_features], label=y_short, cat_features=cat_features)
    short_params['scale_pos_weight'] = (len(y_short) - sum(y_short)) / (sum(y_short) + 1e-8)
    
    model_short = CatBoostClassifier(**short_params)
    model_short.fit(pool_short)
    model_short.save_model(f"{BUNDLE_DIR}/short_expert.cbm")
    
    raw_probs_short = model_short.predict_proba(pool_short)[:, 1]
    calibrator_short, cal_type_s = select_best_calibrator(raw_probs_short, y_short)
    joblib.dump(calibrator_short, f"{BUNDLE_DIR}/calibrator_short.pkl")

    del pool_short
    del y_short
    del raw_probs_short
    gc.collect()

    # 4. Export Thresholds
    thresholds = {
        'long_calibrator_type': cal_type_l,
        'short_calibrator_type': cal_type_s,
        'min_probability_long': 0.51,
        'min_probability_short': 0.51,
        'volatility_percentile_gate': 0.75,
        'hmm_state_ban': [0],
        'exchange_max_leverage': 10.0,
        'dex_roundtrip_fee_bps': 0.0004
    }
    with open(f"{BUNDLE_DIR}/thresholds.json", "w") as f:
        json.dump(thresholds, f, indent=4)

    # 5. Export Manifest
    manifest = {
        'bundle_version': '1.0.0',
        'build_timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'dataset_row_count': len(df),
        'start_date': str(df['timestamp'].min()),
        'end_date': str(df['timestamp'].max()),
        'target_definition': 'Symmetric Triple Barrier (+1.5 ATR / -1.5 ATR, 30m horizon)',
        'optuna_params': opt_params
    }
    with open(f"{BUNDLE_DIR}/manifest.json", "w") as f:
        json.dump(manifest, f, indent=4)

    print("\n" + "="*60)
    print(f"[SUCCESS] Production Bundle frozen at: {BUNDLE_DIR}/")
    print("="*60)

if __name__ == "__main__":
    build_production_bundle()
