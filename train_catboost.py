import pandas as pd
from catboost import CatBoostClassifier, Pool
from google.cloud import bigquery
import os

PROJECT_ID = "parnasa-498503"
MODEL_PATH = "/home/skybullet1987/quant_pipeline/live_model.cbm"
PURGE_BARS = 240 

def train_production_model():
    print("1. Ingesting Phase 2 Matrix with Hard Percentage Targets (+4% / -2%)...")
    client = bigquery.Client(project=PROJECT_ID)
    
    query = f"""
        SELECT 
            timestamp,
            candle_body_pct, candle_upper_wick_pct, candle_lower_wick_pct,
            rank_nofi, rank_volume_zscore, rank_gk_vol,
            rank_vol_term_structure, rank_vwap_dev_60m, rank_alpha_mom_15m,
            rank_alpha_mom_60m, rank_btc_beta_60m,
            target_hard_4_2
        FROM `{PROJECT_ID}.market_data.features_matrix`
        WHERE target_hard_4_2 IS NOT NULL
        ORDER BY timestamp ASC
    """
    
    df = client.query(query).to_dataframe(create_bqstorage_client=True)
    df = df.dropna()

    timestamps = df['timestamp'].sort_values().unique()
    n = len(timestamps)
    
    train_end_idx = int(n * 0.70)
    eval_end_idx = int(n * 0.85)

    train_ts = timestamps[:train_end_idx]
    eval_ts = timestamps[train_end_idx + PURGE_BARS : eval_end_idx]
    test_ts = timestamps[eval_end_idx + PURGE_BARS :]

    train_df = df[df['timestamp'].isin(train_ts)]
    eval_df = df[df['timestamp'].isin(eval_ts)]
    test_df = df[df['timestamp'].isin(test_ts)]

    hit_rate = train_df['target_hard_4_2'].mean()
    print(f"   Target Hit Rate (+4% TP / -2% SL): {hit_rate:.2%}")

    feature_cols = [
        'candle_body_pct', 'candle_upper_wick_pct', 'candle_lower_wick_pct',
        'rank_nofi', 'rank_volume_zscore', 'rank_gk_vol',
        'rank_vol_term_structure', 'rank_vwap_dev_60m', 'rank_alpha_mom_15m',
        'rank_alpha_mom_60m', 'rank_btc_beta_60m'
    ]

    train_pool = Pool(train_df[feature_cols], label=train_df['target_hard_4_2'])
    eval_pool = Pool(eval_df[feature_cols], label=eval_df['target_hard_4_2'])
    test_pool = Pool(test_df[feature_cols], label=test_df['target_hard_4_2'])

    print("\n2. Training CatBoost...")
    model = CatBoostClassifier(
        iterations=1200,
        learning_rate=0.015,
        depth=6,
        l2_leaf_reg=12.0,
        loss_function='Logloss',
        eval_metric='AUC',
        auto_class_weights='Balanced', 
        od_type='Iter',
        od_wait=100,
        verbose=100
    )

    model.fit(train_pool, eval_set=eval_pool, use_best_model=True)

    print("\n3. Evaluating on Purged Out-of-Sample Test Set...")
    test_auc = model.eval_metrics(test_pool, metrics=['AUC'])['AUC'][-1]
    print(f"   >>> Out-of-Sample Test AUC: {test_auc:.4f}")

    model.save_model(MODEL_PATH)
    print(f"\n   Model successfully exported to {MODEL_PATH}")

if __name__ == "__main__":
    train_production_model()
