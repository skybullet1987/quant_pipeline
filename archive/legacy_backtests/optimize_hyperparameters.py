import pandas as pd
import numpy as np
from catboost import CatBoostClassifier, Pool
from google.cloud import bigquery
from hmmlearn.hmm import GaussianHMM
import optuna
import json
import warnings
import os

warnings.filterwarnings("ignore")

PROJECT_ID = "parnasa-498503"
MODEL_DIR = "/home/skybullet1987/quant_pipeline/production_models"
os.makedirs(MODEL_DIR, exist_ok=True)

OPTUNA_TRIALS_HMM = 10
OPTUNA_TRIALS_CAT = 25
PURGE_BARS = 18 # Strict 72-hour embargo to prevent label overlap

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
    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT f.*, p.exit_time, p.exit_reason
        FROM `{PROJECT_ID}.market_data.fct_4h_features_tbm` f
        INNER JOIN `{PROJECT_ID}.market_data.fct_exact_path_resolution` p
            ON f.timestamp = p.signal_time AND f.ticker = p.ticker
        WHERE f.target_tbm_upper_hit IS NOT NULL
        ORDER BY f.timestamp ASC
    """
    df = client.query(query).to_dataframe(create_bqstorage_client=True)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df.dropna(subset=['exit_reason', 'exit_time']).copy()

def purged_walk_forward_cv(df, params, all_features, cat_cols, n_splits=3):
    """
    Simulates real-world deployment by continuously advancing the training window, 
    leaving a 72-hour purge gap, and evaluating on strictly unseen future data.
    """
    timestamps = df['timestamp'].sort_values().unique()
    split_size = len(timestamps) // (n_splits + 1)
    aucs = []
    
    for i in range(1, n_splits + 1):
        train_end_idx = i * split_size
        test_end_idx = (i + 1) * split_size
        
        train_ts = timestamps[:train_end_idx]
        # The Purge: Start the test set strictly after the 72-hour path resolution timeout
        test_ts = timestamps[train_end_idx + PURGE_BARS : test_end_idx]
        
        train_data = df[df['timestamp'].isin(train_ts)]
        test_data = df[df['timestamp'].isin(test_ts)]
        
        if len(train_data) < 200 or len(test_data) < 50 or test_data['target'].nunique() < 2:
            continue
            
        t_pool = Pool(train_data[all_features], label=train_data['target'], cat_features=cat_cols)
        e_pool = Pool(test_data[all_features], label=test_data['target'], cat_features=cat_cols)
        
        model = CatBoostClassifier(**params)
        model.fit(t_pool, eval_set=e_pool, use_best_model=True)
        
        aucs.append(model.best_score_['validation']['AUC'])
        
    return np.mean(aucs) if aucs else 0.50

def main():
    print("1. Ingesting Data for Purged Walk-Forward Optimization...")
    df = load_data()
    df = df[(df['rank_gk_vol_zscore'] >= 0.40) | (df['rank_relative_vol_120p'] >= 0.50)].copy().reset_index(drop=True)
    df['target'] = (df['exit_reason'] == 'TP_HIT').astype(int)

    timestamps = df['timestamp'].sort_values().unique()
    train_ts = timestamps[:int(len(timestamps) * 0.85)]
    df_train = df[df['timestamp'].isin(train_ts)].copy().reset_index(drop=True)

    optimal_params = {}
    hmm_features = ['rank_gk_vol_zscore', 'rank_mom_7d', 'market_breadth_sma20']
    X_train_hmm = df_train[hmm_features].values

    print("\n2. Launching HMM Regime Optimization (Minimizing BIC)...")
    def hmm_objective(trial):
        n_components = trial.suggest_int('n_components', 2, 6)
        covariance_type = trial.suggest_categorical('covariance_type', ['diag', 'full'])
        try:
            model = GaussianHMM(n_components=n_components, covariance_type=covariance_type, n_iter=150, random_state=42)
            model.fit(X_train_hmm)
            log_likelihood = model.score(X_train_hmm)
            d = X_train_hmm.shape[1]
            c = n_components
            n_params = c * d * 2 + c * (c - 1) + c - 1 if covariance_type == 'diag' else c * d + c * d * (d + 1) / 2 + c * (c - 1) + c - 1
            return -2 * log_likelihood + n_params * np.log(X_train_hmm.shape[0])
        except Exception:
            return float('inf')

    hmm_study = optuna.create_study(direction="minimize")
    hmm_study.optimize(hmm_objective, n_trials=OPTUNA_TRIALS_HMM)
    best_hmm_params = hmm_study.best_params
    optimal_params["hmm_macro"] = best_hmm_params
    print(f"   -> Best HMM Parameters: {best_hmm_params}")

    print("\n3. Tagging Regimes with Optimal HMM...")
    best_hmm = GaussianHMM(n_components=best_hmm_params['n_components'], covariance_type=best_hmm_params['covariance_type'], n_iter=500, random_state=42)
    best_hmm.fit(X_train_hmm)
    df_train['hmm_regime'] = best_hmm.predict(X_train_hmm).astype(str)

    all_cat_cols = CAT_COLS_BASE + ['hmm_regime']
    all_features = FEATURE_COLS_NUM + all_cat_cols
    for col in all_cat_cols: df_train[col] = df_train[col].astype(str)

    print("\n4. Launching Purged Walk-Forward CV for Regime Experts...")
    unique_regimes = df_train['hmm_regime'].unique()
    for regime in unique_regimes:
        regime_data = df_train[df_train['hmm_regime'] == regime].copy()
        if len(regime_data) > 800:
            print(f"   -> Optimizing Regime {regime} ({len(regime_data)} setups)...")
            
            def cat_objective(trial):
                params = {
                    'iterations': trial.suggest_int('iterations', 500, 1500),
                    'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.08, log=True),
                    'depth': trial.suggest_int('depth', 4, 7),
                    'l2_leaf_reg': trial.suggest_float('l2_leaf_reg', 3.0, 20.0),
                    'random_strength': trial.suggest_float('random_strength', 1.0, 10.0),
                    'auto_class_weights': 'Balanced',
                    'loss_function': 'Logloss',
                    'eval_metric': 'AUC',
                    'od_type': 'Iter',
                    'od_wait': 50,
                    'verbose': False
                }
                return purged_walk_forward_cv(regime_data, params, all_features, all_cat_cols, n_splits=3)

            study = optuna.create_study(direction="maximize")
            study.optimize(cat_objective, n_trials=OPTUNA_TRIALS_CAT)
            optimal_params[f"regime_{regime}"] = study.best_params
            print(f"      Best Purged AUC: {study.best_value:.4f}")
        else:
            optimal_params[f"regime_{regime}"] = None
            print(f"   -> Skipping Regime {regime} (Insufficient data for Walk-Forward CV)")

    print("\n5. Launching Purged Walk-Forward CV for Meta-Labeler...")
    df_train['primary_prob'] = 0.0
    for regime in unique_regimes:
        r_idx = df_train[df_train['hmm_regime'] == regime].index
        if optimal_params.get(f"regime_{regime}") is not None:
            temp_params = optimal_params[f"regime_{regime}"].copy()
            temp_params.update({'auto_class_weights': 'Balanced', 'verbose': False})
            temp_model = CatBoostClassifier(**temp_params)
            temp_model.fit(df_train.loc[r_idx, all_features], df_train.loc[r_idx, 'target'], cat_features=all_cat_cols)
            df_train.loc[r_idx, 'primary_prob'] = temp_model.predict_proba(df_train.loc[r_idx, all_features])[:, 1]

    meta_train = df_train[df_train['primary_prob'] > 0.50].copy()
    if len(meta_train) > 800:
        meta_features = FEATURE_COLS_NUM + ['primary_prob']
        
        def meta_objective(trial):
            params = {
                'iterations': trial.suggest_int('iterations', 500, 1500),
                'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.06, log=True),
                'depth': trial.suggest_int('depth', 3, 6),
                'l2_leaf_reg': trial.suggest_float('l2_leaf_reg', 3.0, 15.0),
                'loss_function': 'Logloss',
                'eval_metric': 'AUC',
                'od_type': 'Iter',
                'od_wait': 50,
                'verbose': False
            }
            return purged_walk_forward_cv(meta_train, params, meta_features, [], n_splits=3)

        meta_study = optuna.create_study(direction="maximize")
        meta_study.optimize(meta_objective, n_trials=OPTUNA_TRIALS_CAT)
        optimal_params["meta_labeler"] = meta_study.best_params
        print(f"      Best Meta Purged AUC: {meta_study.best_value:.4f}")
    else:
        optimal_params["meta_labeler"] = None
        print("      Skipping Meta-Labeler (Insufficient high-probability setups)")

    with open(f"{MODEL_DIR}/optimal_params.json", "w") as f:
        json.dump(optimal_params, f, indent=4)
    print(f"\n[SUCCESS] Hyperparameters optimized via Purged Walk-Forward CV and saved to {MODEL_DIR}/optimal_params.json")

if __name__ == "__main__":
    main()
