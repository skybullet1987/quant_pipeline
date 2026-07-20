import pandas as pd
from catboost import CatBoostClassifier, Pool
from google.cloud import bigquery
import os

PROJECT_ID = "parnasa-498503"
MODEL_PATH = "/home/skybullet1987/quant_pipeline/live_model.cbm"
PURGE_BARS = 60 

def train_production_model():
    print("1. Ingesting Cross-Sectionally Rank-Normalized Feature Store...")
    client = bigquery.Client(project=PROJECT_ID)
    
    query = f"""
        SELECT 
            timestamp,
            ticker,
            hour_of_day,
            day_of_week,
            is_weekend,
            rank_nofi,
            rank_gk_vol,
            rank_vol_term_structure,
            rank_vwap_dev_60m,
            rank_alpha_mom_15m,
            rank_alpha_mom_60m,
            target_tp_hit
        FROM `{PROJECT_ID}.market_data.features_matrix`
        WHERE target_tp_hit IS NOT NULL
        ORDER BY timestamp ASC
    """
    
    df = client.query(query).to_dataframe(create_bqstorage_client=True)
    print(f"   Loaded {len(df):,} rows.")

    timestamps = df['timestamp'].unique()
    n = len(timestamps)
    
    train_end_idx = int(n * 0.70)
    eval_end_idx = int(n * 0.85)

    train_ts = timestamps[:train_end_idx]
    eval_ts = timestamps[train_end_idx + PURGE_BARS : eval_end_idx]
    test_ts = timestamps[eval_end_idx + PURGE_BARS :]

    train_df = df[df['timestamp'].isin(train_ts)]
    eval_df = df[df['timestamp'].isin(eval_ts)]
    test_df = df[df['timestamp'].isin(test_ts)]

    feature_cols = [
        'rank_nofi', 'rank_gk_vol', 'rank_vol_term_structure',
        'rank_vwap_dev_60m', 'rank_alpha_mom_15m', 'rank_alpha_mom_60m'
    ]
    cat_cols = ['ticker', 'hour_of_day', 'day_of_week', 'is_weekend']

    print(f"   Train samples: {len(train_df):,} | Eval samples: {len(eval_df):,} | Test samples: {len(test_df):,}")

    train_pool = Pool(train_df[feature_cols + cat_cols], label=train_df['target_tp_hit'], cat_features=cat_cols)
    eval_pool = Pool(eval_df[feature_cols + cat_cols], label=eval_df['target_tp_hit'], cat_features=cat_cols)
    test_pool = Pool(test_df[feature_cols + cat_cols], label=test_df['target_tp_hit'], cat_features=cat_cols)

    print("2. Training Regularized CatBoost Model...")
    model = CatBoostClassifier(
        iterations=1500,
        learning_rate=0.03,
        depth=5,
        l2_leaf_reg=10.0,
        loss_function='Logloss',
        eval_metric='AUC',
        auto_class_weights='Balanced', # Automatically handles the rarity of the +2.0% hits
        od_type='Iter',
        od_wait=50,
        verbose=100
    )

    model.fit(train_pool, eval_set=eval_pool, use_best_model=True)

    print("\n3. Evaluating on Purged Out-of-Sample Test Set...")
    test_auc = model.eval_metrics(test_pool, metrics=['AUC'])['AUC'][-1]
    print(f"   >>> Out-of-Sample Test AUC: {test_auc:.4f}")

    model.save_model(MODEL_PATH)
    print(f"   Model successfully exported to {MODEL_PATH}")

if __name__ == "__main__":
    train_production_model()
