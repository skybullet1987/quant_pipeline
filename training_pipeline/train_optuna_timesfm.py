import os
import warnings
import joblib
import numpy as np
import pandas as pd
import optuna
from google.cloud import bigquery
from hmmlearn.hmm import GaussianHMM
from catboost import CatBoostClassifier, Pool
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import roc_auc_score, brier_score_loss

warnings.filterwarnings("ignore")
optuna.logging.set_verbosity(optuna.logging.WARNING)

PROJECT_ID = "parnasa-498503"
MODEL_DIR = "/home/skybullet1987/quant_pipeline/production_models"
os.makedirs(MODEL_DIR, exist_ok=True)
OPTUNA_TRIALS = 25

CAT_COLS_BASE = ['ticker', 'hour_of_day', 'day_of_week', 'is_weekend', 'market_session', 'btc_above_sma50']
FEATURE_COLS_NUM = [
    'market_breadth_sma20', 'top_breakout_breadth', 'pos_bar_count_6p',
    'candle_body_pct', 'candle_upper_wick_pct', 'candle_lower_wick_pct',
    'rank_eth_btc_spread_20p', 'rank_btc_dominance_spread',
    'rank_gk_vol_20p', 'rank_vol_term_structure', 'rank_gk_vol_zscore', 'rank_vol_compression_ratio',
    'rank_mom_24h', 'rank_mom_7d', 'rank_mom_accel_24h', 'rank_mom_ratio_24h_7d',
    'rank_dist_to_120p_high', 'rank_relative_vol_120p', 'rank_rolling_sharpe_20p', 'rank_atr_pct_20',
    # --- TIMESFM 2.5 FOUNDATION FEATURES ---
    'tfm_ret_24h', 'tfm_ret_72h', 'tfm_slope', 'tfm_uncertainty', 'tfm_residual_24h', 'tfm_conviction_delta'
]

def load_data():
    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT 
            f.*,
            p.exit_time,
            p.exit_reason,
            t.tfm_ret_24h, t.tfm_ret_72h, t.tfm_slope, t.tfm_uncertainty, t.tfm_residual_24h, t.tfm_conviction_delta
        FROM `{PROJECT_ID}.market_data.fct_4h_features_tbm` f
        INNER JOIN `{PROJECT_ID}.market_data.fct_exact_path_resolution` p
            ON f.timestamp = p.signal_time AND f.ticker = p.ticker
        LEFT JOIN `{PROJECT_ID}.market_data.fct_timesfm_features` t
            ON f.timestamp = t.timestamp AND f.ticker = t.ticker
        WHERE f.target_tbm_upper_hit IS NOT NULL
        ORDER BY f.timestamp ASC
    """
    df = client.query(query).to_dataframe(create_bqstorage_client=True)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df.dropna(subset=['exit_reason', 'exit_time', 'tfm_residual_24h']).reset_index(drop=True)

def calculate_entropy(probs):
    """Calculates Shannon Entropy across state probability distribution."""
    probs = np.clip(probs, 1e-12, 1.0)
    return -np.sum(probs * np.log(probs), axis=1)

def main():
    print("=================================================================")
    print("   1. INGESTING FEATURE MATRIX & TIMESFM FOUNDATION FEATURES     ")
    print("=================================================================")
    df = load_data()
    
    df['raw_atr_pct'] = df['atr_20'] / df['close']
    df = df.sort_values(['ticker', 'timestamp'])
    df['return_7d'] = df.groupby('ticker')['close'].pct_change(42)  
    
    df = df.dropna(subset=['return_7d']).copy()
    # Volatility/Volume regime filter
    df = df[(df['rank_gk_vol_zscore'] >= 0.40) | (df['rank_relative_vol_120p'] >= 0.50)].reset_index(drop=True)
    df['target'] = (df['exit_reason'] == 'TP_HIT').astype(int)

    # Walk-forward temporal split (85% Train, 15% Validation)
    timestamps = df['timestamp'].sort_values().unique()
    split_idx = int(len(timestamps) * 0.85)
    train_ts = timestamps[:split_idx]
    
    df_train = df[df['timestamp'].isin(train_ts)].copy().reset_index(drop=True)
    df_val = df[~df['timestamp'].isin(train_ts)].copy().reset_index(drop=True)

    print("\n=================================================================")
    print("   2. TRAINING CANONICAL 4-VECTOR HMM (WITH SURPRISE INDEX)      ")
    print("=================================================================")
    macro_train = df_train.groupby('timestamp').agg(
        macro_breadth=('market_breadth_sma20', 'first'),
        macro_volatility=('raw_atr_pct', 'median'),
        macro_momentum=('return_7d', 'median'),
        macro_surprise=('tfm_residual_24h', 'median')
    ).sort_index()

    hmm_features = ['macro_breadth', 'macro_volatility', 'macro_momentum', 'macro_surprise']
    
    hmm_raw = GaussianHMM(n_components=3, covariance_type="full", n_iter=500, random_state=42)
    hmm_raw.fit(macro_train[hmm_features].values)
    
    # Sort canonical state order by volatility emission mean (State 0 = Chop, State 1 = Trend, State 2 = High Vol)
    vol_means = hmm_raw.means_[:, 1]
    canonical_order = np.argsort(vol_means)
    state_map = {raw: can for can, raw in enumerate(canonical_order)}
    
    # Generate continuous state posterior probabilities
    raw_probs_train = hmm_raw.predict_proba(macro_train[hmm_features].values)
    canonical_probs_train = raw_probs_train[:, canonical_order]
    
    macro_train['hmm_p_chop'] = canonical_probs_train[:, 0]
    macro_train['hmm_p_trend'] = canonical_probs_train[:, 1]
    macro_train['hmm_p_cascade'] = canonical_probs_train[:, 2]
    macro_train['hmm_entropy'] = calculate_entropy(canonical_probs_train)
    macro_train['hmm_regime'] = np.argmax(canonical_probs_train, axis=1).astype(str)

    # Save HMM artifacts
    joblib.dump(hmm_raw, f"{MODEL_DIR}/hmm_macro.pkl")
    joblib.dump(canonical_order, f"{MODEL_DIR}/hmm_canonical_order.pkl")

    # Merge continuous HMM probabilities into training set
    df_train = pd.merge(
        df_train, 
        macro_train[['hmm_p_chop', 'hmm_p_trend', 'hmm_p_cascade', 'hmm_entropy', 'hmm_regime']], 
        left_on='timestamp', 
        right_index=True, 
        how='left'
    )

    # Process validation macro HMM vectors
    macro_val = df_val.groupby('timestamp').agg(
        macro_breadth=('market_breadth_sma20', 'first'),
        macro_volatility=('raw_atr_pct', 'median'),
        macro_momentum=('return_7d', 'median'),
        macro_surprise=('tfm_residual_24h', 'median')
    ).sort_index()

    raw_probs_val = hmm_raw.predict_proba(macro_val[hmm_features].values)
    canonical_probs_val = raw_probs_val[:, canonical_order]
    
    macro_val['hmm_p_chop'] = canonical_probs_val[:, 0]
    macro_val['hmm_p_trend'] = canonical_probs_val[:, 1]
    macro_val['hmm_p_cascade'] = canonical_probs_val[:, 2]
    macro_val['hmm_entropy'] = calculate_entropy(canonical_probs_val)
    macro_val['hmm_regime'] = np.argmax(canonical_probs_val, axis=1).astype(str)

    df_val = pd.merge(
        df_val, 
        macro_val[['hmm_p_chop', 'hmm_p_trend', 'hmm_p_cascade', 'hmm_entropy', 'hmm_regime']], 
        left_on='timestamp', 
        right_index=True, 
        how='left'
    )

    all_cat_cols = CAT_COLS_BASE + ['hmm_regime']
    all_features = FEATURE_COLS_NUM + ['hmm_p_chop', 'hmm_p_trend', 'hmm_p_cascade', 'hmm_entropy'] + all_cat_cols
    
    for col in all_cat_cols:
        df_train[col] = df_train[col].astype(str)
        df_val[col] = df_val[col].astype(str)

    print("\n=================================================================")
    print(f"   3. RUNNING OPTUNA HYPERPARAMETER TUNING ({OPTUNA_TRIALS} TRIALS)     ")
    print("=================================================================")
    
    train_pool = Pool(df_train[all_features], label=df_train['target'], cat_features=all_cat_cols)
    val_pool = Pool(df_val[all_features], label=df_val['target'], cat_features=all_cat_cols)

    def objective(trial):
        params = {
            'iterations': trial.suggest_int('iterations', 500, 1500),
            'learning_rate': trial.suggest_float('learning_rate', 0.005, 0.08, log=True),
            'depth': trial.suggest_int('depth', 3, 7),
            'l2_leaf_reg': trial.suggest_float('l2_leaf_reg', 3.0, 25.0),
            'random_strength': trial.suggest_float('random_strength', 1.0, 10.0),
            'loss_function': 'Logloss',
            'eval_metric': 'AUC',
            'od_type': 'Iter',
            'od_wait': 75,
            'verbose': False,
            'random_seed': 42
        }
        
        model = CatBoostClassifier(**params)
        model.fit(train_pool, eval_set=val_pool, use_best_model=True)
        return model.best_score_['validation']['AUC']

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=OPTUNA_TRIALS)
    
    print(f"\n   -> Best Optuna Validation AUC: {study.best_value:.4f}")
    print(f"   -> Best Parameters: {study.best_params}")

    print("\n=================================================================")
    print("   4. TRAINING ISOTONIC PROBABILITY CALIBRATED MODEL             ")
    print("=================================================================")
    
    # Re-instantiate best CatBoost configuration
    best_params = study.best_params
    best_params.update({'loss_function': 'Logloss', 'eval_metric': 'AUC', 'verbose': False, 'random_seed': 42})
    base_catboost = CatBoostClassifier(**best_params)

    # Wrap in Isotonic Calibrator using 5-Fold Cross Validation
    calibrated_model = CalibratedClassifierCV(
        estimator=base_catboost,
        method='isotonic',
        cv=5
    )

    # Convert string categorical columns to category codes for sklearn compatibility
    X_train_encoded = df_train[all_features].copy()
    X_val_encoded = df_val[all_features].copy()
    
    for col in all_cat_cols:
        X_train_encoded[col] = X_train_encoded[col].astype('category').cat.codes
        X_val_encoded[col] = X_val_encoded[col].astype('category').cat.codes

    print("Fitting Isotonic Calibrated Classifier across training set...")
    calibrated_model.fit(X_train_encoded, df_train['target'])

    # Evaluate raw vs calibrated probability performance
    raw_val_probs = study.best_trial.user_attrs.get('val_probs', None)
    calibrated_val_probs = calibrated_model.predict_proba(X_val_encoded)[:, 1]
    
    cal_auc = roc_auc_score(df_val['target'], calibrated_val_probs)
    brier_score = brier_score_loss(df_val['target'], calibrated_val_probs)

    print(f"   -> Calibrated Validation AUC:   {cal_auc:.4f}")
    print(f"   -> Calibrated Brier Score Loss: {brier_score:.4f} (Lower is better)")

    print("\n=================================================================")
    print("   5. SAVING PRODUCTION MODEL BUNDLE & METADATA                  ")
    print("=================================================================")
    
    joblib.dump(calibrated_model, f"{MODEL_DIR}/catboost_calibrated_production.pkl")
    joblib.dump(all_features, f"{MODEL_DIR}/feature_names.pkl")
    joblib.dump(all_cat_cols, f"{MODEL_DIR}/cat_cols.pkl")
    joblib.dump(study.best_params, f"{MODEL_DIR}/best_params.pkl")

    print(f"[SUCCESS] All model artifacts saved cleanly to: {MODEL_DIR}")
    print("=================================================================")

if __name__ == "__main__":
    main()
