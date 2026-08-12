import os
import joblib
import warnings
import numpy as np
import pandas as pd
from google.cloud import bigquery
from hmmlearn.hmm import GaussianHMM
from catboost import CatBoostClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import KFold

warnings.filterwarnings("ignore")

PROJECT_ID = "parnasa-498503"
MODEL_DIR = "/home/skybullet1987/quant_pipeline/production_models"
os.makedirs(MODEL_DIR, exist_ok=True)
PURGE_BARS = 18  # 72H horizon target overlap purge

CAT_COLS_BASE = ['ticker', 'hour_of_day', 'day_of_week', 'is_weekend', 'market_session', 'btc_above_sma50']
FEATURE_COLS_NUM = [
    'market_breadth_sma20', 'top_breakout_breadth', 'pos_bar_count_6p',
    'candle_body_pct', 'candle_upper_wick_pct', 'candle_lower_wick_pct',
    'rank_eth_btc_spread_20p', 'rank_btc_dominance_spread',
    'rank_gk_vol_20p', 'rank_vol_term_structure', 'rank_gk_vol_zscore', 'rank_vol_compression_ratio',
    'rank_mom_24h', 'rank_mom_7d', 'rank_mom_accel_24h', 'rank_mom_ratio_24h_7d',
    'rank_dist_to_120p_high', 'rank_relative_vol_120p', 'rank_rolling_sharpe_20p', 'rank_atr_pct_20',
    'tfm_ret_24h', 'tfm_ret_72h', 'tfm_slope', 'tfm_uncertainty', 'tfm_residual_24h', 'tfm_conviction_delta',
    'total_liq_usd', 'liq_imbalance_ratio', 'long_liq_accel', 'short_liq_accel', 'rank_liq_intensity'
]

def load_data():
    print("1. Ingesting Full Feature Matrix from BigQuery...")
    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT 
            f.*, p.exit_time, p.exit_reason, p.minutes_in_trade, p.target_long, p.target_short,
            t.tfm_ret_24h, t.tfm_ret_72h, t.tfm_slope, t.tfm_uncertainty, t.tfm_residual_24h, t.tfm_conviction_delta,
            COALESCE(l.total_liq_usd, 0) AS total_liq_usd,
            COALESCE(l.liq_imbalance_ratio, 0) AS liq_imbalance_ratio,
            COALESCE(l.long_liq_accel, 0) AS long_liq_accel,
            COALESCE(l.short_liq_accel, 0) AS short_liq_accel,
            COALESCE(l.rank_liq_intensity, 0) AS rank_liq_intensity
        FROM `{PROJECT_ID}.market_data.fct_4h_features_tbm` f
        INNER JOIN `{PROJECT_ID}.market_data.fct_exact_path_resolution` p
            ON f.timestamp = p.signal_time AND f.ticker = p.ticker
        LEFT JOIN `{PROJECT_ID}.market_data.fct_timesfm_features` t
            ON f.timestamp = t.timestamp AND f.ticker = t.ticker
        LEFT JOIN `{PROJECT_ID}.market_data.fct_liquidation_features` l
            ON f.timestamp = l.timestamp AND f.ticker = l.ticker
        WHERE f.target_tbm_upper_hit IS NOT NULL
          AND p.exit_reason != 'DATA_ERROR'
        ORDER BY f.timestamp ASC
    """
    df = client.query(query).to_dataframe(create_bqstorage_client=True)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df.dropna(subset=['exit_reason', 'exit_time', 'minutes_in_trade']).fillna(0).copy()

def main():
    df = load_data()
    df = df[(df['rank_gk_vol_zscore'] >= 0.40) | (df['rank_relative_vol_120p'] >= 0.50)].copy().reset_index(drop=True)

    # 1. Purged Time-Series Train/Val Split (dropping 18 target-overlap bars at boundary)
    timestamps = df['timestamp'].sort_values().unique()
    split_idx = int(len(timestamps) * 0.85)
    train_ts = timestamps[:split_idx - PURGE_BARS]
    df_train = df[df['timestamp'].isin(train_ts)].copy().reset_index(drop=True)

    print(f"\n2. Training Macro HMM Filter on {len(df_train):,} Purged Training Rows...")
    hmm_features = ["rank_gk_vol_zscore", "rank_mom_7d", "market_breadth_sma20"]
    hmm_scaler = StandardScaler()
    scaled_hmm_X = hmm_scaler.fit_transform(df_train[hmm_features].fillna(0))
    joblib.dump(hmm_scaler, f"{MODEL_DIR}/hmm_scaler.pkl")
    joblib.dump(hmm_features, f"{MODEL_DIR}/hmm_feature_names.pkl")

    hmm_model = GaussianHMM(n_components=3, covariance_type="full", n_iter=500, random_state=42)
    hmm_model.fit(scaled_hmm_X)
    joblib.dump(hmm_model, f"{MODEL_DIR}/hmm_macro.pkl")

    raw_states = hmm_model.predict(scaled_hmm_X)
    state_vol = [df_train.loc[raw_states == i, "rank_gk_vol_zscore"].median() for i in range(3)]
    canonical_order = np.argsort(state_vol)
    joblib.dump(canonical_order, f"{MODEL_DIR}/hmm_canonical_order.pkl")

    raw_probs = hmm_model.predict_proba(scaled_hmm_X)
    can_probs = raw_probs[:, canonical_order]
    df_train["hmm_regime"] = can_probs.argmax(axis=1).astype(str)

    all_cat_cols = CAT_COLS_BASE + ['hmm_regime']
    all_features = FEATURE_COLS_NUM + all_cat_cols
    for col in all_cat_cols: 
        df_train[col] = df_train[col].astype(str)

    joblib.dump(all_cat_cols, f"{MODEL_DIR}/cat_cols.pkl")
    joblib.dump(all_features, f"{MODEL_DIR}/feature_names.pkl")

    print("\n3. Training Asymmetric Dual Experts with Sequential Non-Overlapping CV...")
    df_train['primary_prob_long'] = 0.0
    df_train['primary_prob_short'] = 0.0
    
    # Sequential Time-Series K-Fold (shuffle=False to prevent forward leakage across folds)
    kf = KFold(n_splits=5, shuffle=False)

    for regime in ['0', '1', '2']:
        regime_idx = df_train[df_train['hmm_regime'] == regime].index
        if len(regime_idx) > 100:
            print(f"   -> Out-of-Fold Cross-Validation: Regime {regime} Experts...")
            for train_i, val_i in kf.split(regime_idx):
                tr_idx, val_idx = regime_idx[train_i], regime_idx[val_i]
                
                # Long Expert
                m_long = CatBoostClassifier(iterations=800, depth=5, auto_class_weights='Balanced', early_stopping_rounds=50, learning_rate=0.03, verbose=0, random_seed=42)
                m_long.fit(df_train.loc[tr_idx, all_features], df_train.loc[tr_idx, 'target_long'], cat_features=all_cat_cols, eval_set=(df_train.loc[val_idx, all_features], df_train.loc[val_idx, 'target_long']))
                df_train.loc[val_idx, 'primary_prob_long'] = m_long.predict_proba(df_train.loc[val_idx, all_features])[:, 1]

                # Short Expert
                m_short = CatBoostClassifier(iterations=800, depth=5, auto_class_weights='Balanced', early_stopping_rounds=50, learning_rate=0.03, verbose=0, random_seed=42)
                m_short.fit(df_train.loc[tr_idx, all_features], df_train.loc[tr_idx, 'target_short'], cat_features=all_cat_cols, eval_set=(df_train.loc[val_idx, all_features], df_train.loc[val_idx, 'target_short']))
                df_train.loc[val_idx, 'primary_prob_short'] = m_short.predict_proba(df_train.loc[val_idx, all_features])[:, 1]

            # Fit Final Production Experts on full regime data
            f_long = CatBoostClassifier(iterations=800, depth=5, auto_class_weights='Balanced', learning_rate=0.03, verbose=0, random_seed=42)
            f_long.fit(df_train.loc[regime_idx, all_features], df_train.loc[regime_idx, 'target_long'], cat_features=all_cat_cols)
            f_long.save_model(f"{MODEL_DIR}/regime_{regime}_long_expert.cbm")

            f_short = CatBoostClassifier(iterations=800, depth=5, auto_class_weights='Balanced', learning_rate=0.03, verbose=0, random_seed=42)
            f_short.fit(df_train.loc[regime_idx, all_features], df_train.loc[regime_idx, 'target_short'], cat_features=all_cat_cols)
            f_short.save_model(f"{MODEL_DIR}/regime_{regime}_short_expert.cbm")

    print("\n4. Training Meta-Labelers & Isotonic Calibrators on Out-of-Fold Predictions...")
    # Long Meta & Calibrator
    meta_tr_long = df_train[df_train['primary_prob_long'] > 0.50].copy().reset_index(drop=True)
    meta_feats_long = FEATURE_COLS_NUM + ['primary_prob_long']
    if len(meta_tr_long) > 50:
        meta_tr_long['oof_meta_prob'] = 0.0
        kf_meta = KFold(n_splits=5, shuffle=False)
        
        for tr_i, val_i in kf_meta.split(meta_tr_long):
            m_cv = CatBoostClassifier(iterations=500, depth=4, auto_class_weights='Balanced', early_stopping_rounds=50, learning_rate=0.03, verbose=0, random_seed=42)
            m_cv.fit(meta_tr_long.loc[tr_i, meta_feats_long], meta_tr_long.loc[tr_i, 'target_long'], eval_set=(meta_tr_long.loc[val_i, meta_feats_long], meta_tr_long.loc[val_i, 'target_long']))
            meta_tr_long.loc[val_i, 'oof_meta_prob'] = m_cv.predict_proba(meta_tr_long.loc[val_i, meta_feats_long])[:, 1]

        # Fit Final Production Meta Model
        m_model_long = CatBoostClassifier(iterations=500, depth=4, auto_class_weights='Balanced', learning_rate=0.03, verbose=0, random_seed=42)
        m_model_long.fit(meta_tr_long[meta_feats_long], meta_tr_long['target_long'])
        m_model_long.save_model(f"{MODEL_DIR}/meta_labeler_long.cbm")
        
        # Fit Isotonic Calibrator strictly on OUT-OF-FOLD Meta Probabilities
        cal_long = IsotonicRegression(out_of_bounds='clip')
        cal_long.fit(meta_tr_long['oof_meta_prob'], meta_tr_long['target_long'])
        joblib.dump(cal_long, f"{MODEL_DIR}/meta_calibrator_long.pkl")

    # Short Meta & Calibrator
    meta_tr_short = df_train[df_train['primary_prob_short'] > 0.50].copy().reset_index(drop=True)
    meta_feats_short = FEATURE_COLS_NUM + ['primary_prob_short']
    if len(meta_tr_short) > 50:
        meta_tr_short['oof_meta_prob'] = 0.0
        kf_meta = KFold(n_splits=5, shuffle=False)
        
        for tr_i, val_i in kf_meta.split(meta_tr_short):
            m_cv = CatBoostClassifier(iterations=500, depth=4, auto_class_weights='Balanced', early_stopping_rounds=50, learning_rate=0.03, verbose=0, random_seed=42)
            m_cv.fit(meta_tr_short.loc[tr_i, meta_feats_short], meta_tr_short.loc[tr_i, 'target_short'], eval_set=(meta_tr_short.loc[val_i, meta_feats_short], meta_tr_short.loc[val_i, 'target_short']))
            meta_tr_short.loc[val_i, 'oof_meta_prob'] = m_cv.predict_proba(meta_tr_short.loc[val_i, meta_feats_short])[:, 1]

        # Fit Final Production Meta Model
        m_model_short = CatBoostClassifier(iterations=500, depth=4, auto_class_weights='Balanced', learning_rate=0.03, verbose=0, random_seed=42)
        m_model_short.fit(meta_tr_short[meta_feats_short], meta_tr_short['target_short'])
        m_model_short.save_model(f"{MODEL_DIR}/meta_labeler_short.cbm")
        
        # Fit Isotonic Calibrator strictly on OUT-OF-FOLD Meta Probabilities
        cal_short = IsotonicRegression(out_of_bounds='clip')
        cal_short.fit(meta_tr_short['oof_meta_prob'], meta_tr_short['target_short'])
        joblib.dump(cal_short, f"{MODEL_DIR}/meta_calibrator_short.pkl")

    print("\n[SUCCESS] Leak-Free Asymmetric Dual Pipeline Compiled & Saved to Disk.")

if __name__ == "__main__":
    main()
