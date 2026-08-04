import pandas as pd
import numpy as np
from catboost import CatBoostClassifier, Pool
from google.cloud import bigquery
from hmmlearn.hmm import GaussianHMM
from sklearn.model_selection import StratifiedKFold
import optuna
import joblib
import warnings
import os

warnings.filterwarnings("ignore")

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
    'rank_dist_to_120p_high', 'rank_relative_vol_120p', 'rank_rolling_sharpe_20p', 'rank_atr_pct_20'
]

def load_data():
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
    return df.dropna(subset=['exit_reason', 'exit_time']).reset_index(drop=True)

def main():
    print("1. Ingesting Matrix and Calculating Absolute Macro Features...")
    df = load_data()
    
    # Calculate absolute metrics for the HMM
    df['raw_atr_pct'] = df['atr_20'] / df['close']
    df = df.sort_values(['ticker', 'timestamp'])
    df['return_7d'] = df.groupby('ticker')['close'].pct_change(42)  # 6 bars/day * 7 days
    
    df = df.dropna(subset=['return_7d']).copy()
    df = df[(df['rank_gk_vol_zscore'] >= 0.40) | (df['rank_relative_vol_120p'] >= 0.50)].reset_index(drop=True)
    df['target'] = (df['exit_reason'] == 'TP_HIT').astype(int)

    timestamps = df['timestamp'].sort_values().unique()
    split_idx = int(len(timestamps) * 0.85)
    train_ts = timestamps[:split_idx]
    df_train = df[df['timestamp'].isin(train_ts)].copy().reset_index(drop=True)

    print("2. Aggregating 1D Temporal Market States for HMM...")
    # Condense into ONE row per timestamp for pure time-series modeling
    macro_train = df_train.groupby('timestamp').agg(
        macro_breadth=('market_breadth_sma20', 'first'),
        macro_volatility=('raw_atr_pct', 'median'),
        macro_momentum=('return_7d', 'median')
    ).sort_index()

    hmm_features = ['macro_breadth', 'macro_volatility', 'macro_momentum']
    hmm_model = GaussianHMM(n_components=3, covariance_type="full", n_iter=500, random_state=42)
    hmm_model.fit(macro_train[hmm_features].values)
    joblib.dump(hmm_model, f"{MODEL_DIR}/hmm_macro.pkl")
    
    # Map the identified pure macro states back to the individual coins
    macro_train['hmm_regime'] = hmm_model.predict(macro_train[hmm_features].values).astype(str)
    df_train = pd.merge(df_train, macro_train[['hmm_regime']], left_on='timestamp', right_index=True, how='left')

    all_cat_cols = CAT_COLS_BASE + ['hmm_regime']
    all_features = FEATURE_COLS_NUM + all_cat_cols
    
    for col in all_cat_cols:
        df_train[col] = df_train[col].astype(str)

    print(f"3. Launching Optuna HPO ({OPTUNA_TRIALS} Trials)...")
    
    opt_train = df_train.sample(frac=0.8, random_state=42)
    opt_eval = df_train.drop(opt_train.index)
    
    train_pool = Pool(opt_train[all_features], label=opt_train['target'], cat_features=all_cat_cols)
    eval_pool = Pool(opt_eval[all_features], label=opt_eval['target'], cat_features=all_cat_cols)

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
            'verbose': False
        }
        
        model = CatBoostClassifier(**params)
        model.fit(train_pool, eval_set=eval_pool, use_best_model=True)
        return model.best_score_['validation']['AUC']

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=OPTUNA_TRIALS)
    best_params = study.best_params
    print(f"   -> Best Params Found: {best_params}")

    print("4. Deep-Training 3 Regime Experts using Optimal Parameters...")
    df_train['primary_prob'] = 0.0
    kf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    for regime in ['0', '1', '2']:
        regime_idx = df_train[df_train['hmm_regime'] == regime].index
        
        if len(regime_idx) > 100 and df_train.loc[regime_idx, 'target'].nunique() > 1:
            print(f"   -> Cross-Validating Regime {regime}...")
            
            for train_i, val_i in kf.split(regime_idx, df_train.loc[regime_idx, 'target']):
                tr_idx = regime_idx[train_i]
                val_idx = regime_idx[val_i]
                
                model_params = best_params.copy()
                model_params.update({'auto_class_weights': 'Balanced', 'early_stopping_rounds': 50, 'verbose': 0, 'random_seed': 42})
                model = CatBoostClassifier(**model_params)
                
                model.fit(df_train.loc[tr_idx, all_features], df_train.loc[tr_idx, 'target'], 
                          cat_features=all_cat_cols, 
                          eval_set=(df_train.loc[val_idx, all_features], df_train.loc[val_idx, 'target']))
                df_train.loc[val_idx, 'primary_prob'] = model.predict_proba(df_train.loc[val_idx, all_features])[:, 1]
                
            final_params_regime = best_params.copy()
            final_params_regime.update({'auto_class_weights': 'Balanced', 'verbose': 0, 'random_seed': 42})
            final_model = CatBoostClassifier(**final_params_regime)
            final_model.fit(df_train.loc[regime_idx, all_features], df_train.loc[regime_idx, 'target'], cat_features=all_cat_cols)
            final_model.save_model(f"{MODEL_DIR}/regime_{regime}_expert.cbm")

    print("5. Engineering Orthogonal Meta-Features & Training Meta-Labeler...")
    
    df_train['prob_conviction'] = abs(df_train['primary_prob'] - 0.50)
    df_train['prob_x_vol'] = df_train['primary_prob'] * df_train['rank_gk_vol_zscore']
    df_train['prob_x_mom'] = df_train['primary_prob'] * df_train['rank_mom_24h']
    
    meta_train = df_train[df_train['primary_prob'] > 0.50].copy()
    
    if len(meta_train) > 50 and meta_train['target'].nunique() > 1:
        meta_features = [
            'primary_prob', 'prob_conviction', 'prob_x_vol', 'prob_x_mom',
            'rank_gk_vol_zscore', 'rank_relative_vol_120p', 'rank_atr_pct_20', 'market_breadth_sma20'
        ]
        meta_model = CatBoostClassifier(iterations=500, depth=4, learning_rate=0.03, verbose=0, random_seed=42)
        meta_model.fit(meta_train[meta_features], meta_train['target'])
        meta_model.save_model(f"{MODEL_DIR}/meta_labeler.cbm")
    
    print("\n[SUCCESS] Optuna-Optimized Models Compiled.")

if __name__ == "__main__":
    main()
