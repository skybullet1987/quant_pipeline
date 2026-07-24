import pandas as pd
import numpy as np
from catboost import CatBoostClassifier, Pool
from google.cloud import bigquery
from hmmlearn.hmm import GaussianHMM
from sklearn.model_selection import StratifiedKFold
import joblib
import warnings
import os

warnings.filterwarnings("ignore")

PROJECT_ID = "parnasa-498503"
MODEL_DIR = "/home/skybullet1987/quant_pipeline/production_models"
os.makedirs(MODEL_DIR, exist_ok=True)

CAT_COLS_BASE = ['ticker', 'hour_of_day', 'day_of_week', 'is_weekend', 'market_session', 'btc_above_sma50']
FEATURE_COLS_NUM = [
    'market_breadth_sma20', 'top_breakout_breadth', 'pos_bar_count_6p',
    'candle_body_pct', 'candle_upper_wick_pct', 'candle_lower_wick_pct',
    'rank_eth_btc_spread_20p', 'rank_btc_dominance_spread',
    'rank_gk_vol_20p', 'rank_vol_term_structure', 'rank_gk_vol_zscore', 'rank_vol_compression_ratio',
    'rank_mom_24h', 'rank_mom_7d', 'rank_mom_accel_24h', 'rank_mom_ratio_24h_7d',
    'rank_dist_to_120p_high', 'rank_relative_vol_120p', 'rank_rolling_sharpe_20p', 'rank_atr_pct_20'
]

def load_data():
    print("1. Ingesting 5-Year Feature Matrix (620k Rows)...")
    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT 
            f.*,
            p.exit_time,
            p.exit_reason
        FROM `{PROJECT_ID}.market_data.fct_4h_features_tbm` f
        INNER JOIN `{PROJECT_ID}.market_data.fct_exact_path_resolution` p
            ON f.timestamp = p.signal_time AND f.ticker = p.ticker
        WHERE f.target_tbm_upper_hit IS NOT NULL
        ORDER BY f.timestamp ASC
    """
    df = client.query(query).to_dataframe(create_bqstorage_client=True)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.dropna(subset=['exit_reason', 'exit_time']).copy()
    return df

def main():
    df = load_data()
    df = df[(df['rank_gk_vol_zscore'] >= 0.40) | (df['rank_relative_vol_120p'] >= 0.50)].copy().reset_index(drop=True)
    
    df['target'] = (df['exit_reason'] == 'TP_HIT').astype(int)

    timestamps = df['timestamp'].sort_values().unique()
    split_idx = int(len(timestamps) * 0.85)
    train_ts = timestamps[:split_idx]
    df_train = df[df['timestamp'].isin(train_ts)].copy().reset_index(drop=True)

    print("2. Training & Exporting HMM Macro Filter...")
    hmm_features = ['rank_gk_vol_zscore', 'rank_mom_7d', 'market_breadth_sma20']
    hmm_model = GaussianHMM(n_components=4, covariance_type="full", n_iter=500, random_state=42)
    hmm_model.fit(df_train[hmm_features].values)
    joblib.dump(hmm_model, f"{MODEL_DIR}/hmm_macro.pkl")
    
    df_train['hmm_regime'] = hmm_model.predict(df_train[hmm_features].values).astype(str)

    all_cat_cols = CAT_COLS_BASE + ['hmm_regime']
    all_features = FEATURE_COLS_NUM + all_cat_cols
    
    for col in all_cat_cols:
        df_train[col] = df_train[col].astype(str)

    print("3. Deep-Training 4 Regime Experts (1000 Iterations, Balanced Weights)...")
    df_train['primary_prob'] = 0.0
    
    # THE FIX: Stratified K-Fold to maintain exact Win/Loss ratios in every fold
    kf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    for regime in ['0', '1', '2', '3']:
        regime_idx = df_train[df_train['hmm_regime'] == regime].index
        
        # Ensure we have enough data AND more than just 1 class outcome
        if len(regime_idx) > 100 and df_train.loc[regime_idx, 'target'].nunique() > 1:
            print(f"   -> Cross-Validating Regime {regime} ({len(regime_idx)} samples)...")
            
            # Pass the target variable to StratifiedKFold so it can balance the splits
            for train_i, val_i in kf.split(regime_idx, df_train.loc[regime_idx, 'target']):
                tr_idx = regime_idx[train_i]
                val_idx = regime_idx[val_i]
                
                model = CatBoostClassifier(iterations=1000, depth=5, auto_class_weights='Balanced', early_stopping_rounds=50, learning_rate=0.03, verbose=0, random_seed=42)
                model.fit(df_train.loc[tr_idx, all_features], df_train.loc[tr_idx, 'target'], cat_features=all_cat_cols, eval_set=(df_train.loc[val_idx, all_features], df_train.loc[val_idx, 'target']))
                df_train.loc[val_idx, 'primary_prob'] = model.predict_proba(df_train.loc[val_idx, all_features])[:, 1]
                
            final_model = CatBoostClassifier(iterations=1000, depth=5, auto_class_weights='Balanced', learning_rate=0.03, verbose=0, random_seed=42)
            final_model.fit(df_train.loc[regime_idx, all_features], df_train.loc[regime_idx, 'target'], cat_features=all_cat_cols)
            final_model.save_model(f"{MODEL_DIR}/regime_{regime}_expert.cbm")
            print(f"   -> Saved: {MODEL_DIR}/regime_{regime}_expert.cbm")
        else:
            print(f"   -> Skipping Regime {regime} (Insufficient samples or only 1 target class)")

    print("4. Training & Exporting Meta-Labeler...")
    meta_train = df_train[df_train['primary_prob'] > 0.50].copy()
    
    # Final guardrail for the Meta-Labeler
    if len(meta_train) > 50 and meta_train['target'].nunique() > 1:
        meta_features = FEATURE_COLS_NUM + ['primary_prob']
        
        meta_model = CatBoostClassifier(iterations=1000, depth=5, early_stopping_rounds=100, learning_rate=0.02, verbose=0, random_seed=42)
        meta_model.fit(meta_train[meta_features], meta_train['target'], eval_set=(meta_train[meta_features], meta_train['target']))
        meta_model.save_model(f"{MODEL_DIR}/meta_labeler.cbm")
        print(f"   -> Saved: {MODEL_DIR}/meta_labeler.cbm")
    else:
        print("   -> WARNING: Meta-Labeler skipped (Insufficient data or only 1 target class)")
    
    print("\n[SUCCESS] Production Models Compiled and Saved to Disk.")

if __name__ == "__main__":
    main()
