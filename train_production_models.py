import pandas as pd
import numpy as np
from catboost import CatBoostClassifier
from google.cloud import bigquery
from hmmlearn.hmm import GaussianHMM
from sklearn.isotonic import IsotonicRegression
import joblib
import json
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
    print("1. Ingesting 5-Year Feature Matrix...")
    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT 
            f.*, p.exit_time, p.exit_reason, p.minutes_in_trade
        FROM `{PROJECT_ID}.market_data.fct_4h_features_tbm` f
        INNER JOIN `{PROJECT_ID}.market_data.fct_exact_path_resolution` p
            ON f.timestamp = p.signal_time AND f.ticker = p.ticker
        WHERE f.target_tbm_upper_hit IS NOT NULL
        ORDER BY f.timestamp ASC
    """
    df = client.query(query).to_dataframe(create_bqstorage_client=True)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df.dropna(subset=['exit_reason', 'exit_time', 'minutes_in_trade']).copy()

def main():
    param_path = f"{MODEL_DIR}/optimal_params.json"
    if not os.path.exists(param_path):
        print("ERROR: optimal_params.json not found.")
        return
        
    with open(param_path, "r") as f:
        optimal_params = json.load(f)
        
    df = load_data()
    df = df[(df['rank_gk_vol_zscore'] >= 0.40) | (df['rank_relative_vol_120p'] >= 0.50)].copy().reset_index(drop=True)
    df['target'] = (df['exit_reason'] == 'TP_HIT').astype(int)

    # Dynamic Purge Calculation (Assuming 4H/240m bars)
    max_minutes = df['minutes_in_trade'].max()
    purge_bars = int(np.ceil(max_minutes / 240.0))
    print(f"-> Dynamic Purge Set: {purge_bars} Bars (Max Hold: {max_minutes/60:.1f} Hours)")

    timestamps = df['timestamp'].sort_values().unique()
    split_idx = int(len(timestamps) * 0.85)
    train_ts = timestamps[:split_idx]
    df_train = df[df['timestamp'].isin(train_ts)].copy().reset_index(drop=True)

    print("\n2. Training & Exporting HMM Macro Filter...")
    hmm_features = ['rank_gk_vol_zscore', 'rank_mom_7d', 'market_breadth_sma20']
    hmm_params = optimal_params.get("hmm_macro", {'n_components': 4, 'covariance_type': 'full'})
    hmm_model = GaussianHMM(n_components=3, covariance_type="full", n_iter=500, random_state=42)
    hmm_model.fit(df_train[hmm_features].values)
    joblib.dump(hmm_model, f"{MODEL_DIR}/hmm_macro.pkl")
    df_train['hmm_regime'] = hmm_model.predict(df_train[hmm_features].values).astype(str)

    all_cat_cols = CAT_COLS_BASE + ['hmm_regime']
    all_features = FEATURE_COLS_NUM + all_cat_cols
    for col in all_cat_cols: df_train[col] = df_train[col].astype(str)

    print("\n3. Deep-Training Regime Experts (Purged Walk-Forward)...")
    df_train['primary_prob'] = 0.0
    
    unique_regimes = df_train['hmm_regime'].unique()
    for regime in unique_regimes:
        regime_idx = df_train[df_train['hmm_regime'] == regime].index
        expert_params = optimal_params.get(f"regime_{regime}")
        
        if expert_params and len(regime_idx) > 200:
            print(f"   -> Processing Regime {regime}...")
            expert_params.update({'auto_class_weights': 'Balanced', 'verbose': 0, 'random_seed': 42})
            
            # Simple chronological split to generate out-of-sample probabilities for the Meta-Labeler
            r_timestamps = df_train.loc[regime_idx, 'timestamp'].sort_values().unique()
            for i in range(1, 4):
                split_point = int(len(r_timestamps) * (i / 4.0))
                train_t = r_timestamps[:split_point]
                test_t = r_timestamps[split_point + purge_bars : int(len(r_timestamps) * ((i+1) / 4.0))]
                
                tr_mask = df_train['timestamp'].isin(train_t) & (df_train['hmm_regime'] == regime)
                te_mask = df_train['timestamp'].isin(test_t) & (df_train['hmm_regime'] == regime)
                
                if tr_mask.sum() > 50 and te_mask.sum() > 10:
                    model = CatBoostClassifier(**expert_params)
                    model.fit(df_train.loc[tr_mask, all_features], df_train.loc[tr_mask, 'target'], cat_features=all_cat_cols)
                    df_train.loc[te_mask, 'primary_prob'] = model.predict_proba(df_train.loc[te_mask, all_features])[:, 1]
            
            # Train final production model on 100% of the training block
            final_model = CatBoostClassifier(**expert_params)
            final_model.fit(df_train.loc[regime_idx, all_features], df_train.loc[regime_idx, 'target'], cat_features=all_cat_cols)
            final_model.save_model(f"{MODEL_DIR}/regime_{regime}_expert.cbm")
            
    print("\n4. Training Meta-Labeler & Probability Calibration...")
    meta_train = df_train[df_train['primary_prob'] > 0.50].copy().dropna(subset=['primary_prob'])
    meta_params = optimal_params.get("meta_labeler")
    
    if meta_params and len(meta_train) > 100:
        meta_features = FEATURE_COLS_NUM + ['primary_prob']
        meta_params.update({'verbose': 0, 'random_seed': 42})
        
        meta_model = CatBoostClassifier(**meta_params)
        meta_model.fit(meta_train[meta_features], meta_train['target'])
        meta_model.save_model(f"{MODEL_DIR}/meta_labeler.cbm")
        
        # Fit Isotonic Regression to map raw scores to true probabilities
        raw_preds = meta_model.predict_proba(meta_train[meta_features])[:, 1]
        calibrator = IsotonicRegression(out_of_bounds='clip')
        calibrator.fit(raw_preds, meta_train['target'])
        joblib.dump(calibrator, f"{MODEL_DIR}/meta_calibrator.pkl")
        print(f"   -> Calibrator saved to {MODEL_DIR}/meta_calibrator.pkl")
    
    print("\n[SUCCESS] Fully Calibrated Production Models Exported.")

if __name__ == "__main__":
    main()
