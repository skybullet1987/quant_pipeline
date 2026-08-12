import os
import json
import joblib
import warnings
import numpy as np
import pandas as pd
import optuna
from google.cloud import bigquery
from hmmlearn.hmm import GaussianHMM
from catboost import CatBoostClassifier, Pool
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import KFold

warnings.filterwarnings("ignore")
optuna.logging.set_verbosity(optuna.logging.WARNING)

PROJECT_ID = "parnasa-498503"
MODEL_DIR = "/home/skybullet1987/quant_pipeline/production_models"
os.makedirs(MODEL_DIR, exist_ok=True)
OPTUNA_TRIALS = 20
PURGE_BARS = 18

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
        WHERE f.target_tbm_upper_hit IS NOT NULL AND p.exit_reason != 'DATA_ERROR'
        ORDER BY f.timestamp ASC
    """
    df = client.query(query).to_dataframe(create_bqstorage_client=True)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    # Replaced strict dropna with the safe fillna(0) to prevent 0-row matrix collapse
    return df.dropna(subset=['exit_reason', 'exit_time', 'minutes_in_trade']).fillna(0).copy()

def main():
    print("1. Ingesting Data for Dual Optuna Sweep...")
    df = load_data()
    df = df[(df['rank_gk_vol_zscore'] >= 0.40) | (df['rank_relative_vol_120p'] >= 0.50)].copy().reset_index(drop=True)

    # Purged Time-Series Train Split
    timestamps = df['timestamp'].sort_values().unique()
    split_idx = int(len(timestamps) * 0.85)
    train_ts = timestamps[:split_idx - PURGE_BARS]
    df_train = df[df['timestamp'].isin(train_ts)].copy().reset_index(drop=True)

    print(f"-> Verified {len(df_train)} training rows loaded successfully.")

    # Anchor HMM Regimes
    hmm_features = ["rank_gk_vol_zscore", "rank_mom_7d", "market_breadth_sma20"]
    hmm_scaler = StandardScaler()
    scaled_hmm_X = hmm_scaler.fit_transform(df_train[hmm_features].fillna(0))
    hmm_model = GaussianHMM(n_components=3, covariance_type="full", n_iter=500, random_state=42).fit(scaled_hmm_X)
    
    state_vol = [df_train.loc[hmm_model.predict(scaled_hmm_X) == i, "rank_gk_vol_zscore"].median() for i in range(3)]
    canonical_order = np.argsort(state_vol)
    df_train['hmm_regime'] = hmm_model.predict_proba(scaled_hmm_X)[:, canonical_order].argmax(axis=1).astype(str)
    
    all_cat_cols = CAT_COLS_BASE + ['hmm_regime']
    all_features = FEATURE_COLS_NUM + all_cat_cols
    for col in all_cat_cols: df_train[col] = df_train[col].astype(str)

    optimal_params = {}
    print(f"\n2. Running Dual Optuna Sweep ({OPTUNA_TRIALS} Trials) using Sequential Time-Series CV...")
    
    for regime in ['0', '1', '2']:
        regime_data = df_train[df_train['hmm_regime'] == regime].copy().reset_index(drop=True)
        if len(regime_data) < 200: continue
        
        for direction, target_col in [('long', 'target_long'), ('short', 'target_short')]:
            print(f" -> Tuning Regime {regime} [{direction.upper()}]...")
            
            def objective(trial):
                params = {
                    'iterations': trial.suggest_int('iterations', 400, 1200),
                    'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.08, log=True),
                    'depth': trial.suggest_int('depth', 4, 7),
                    'l2_leaf_reg': trial.suggest_float('l2_leaf_reg', 3.0, 20.0),
                    'random_strength': trial.suggest_float('random_strength', 1.0, 10.0),
                    'auto_class_weights': 'Balanced', 'loss_function': 'Logloss', 'eval_metric': 'AUC',
                    'od_type': 'Iter', 'od_wait': 50, 'verbose': False, 'random_seed': 42
                }
                
                # Replaced shuffled StratifiedKFold with strict time-series sequential KFold
                kf = KFold(n_splits=3, shuffle=False)
                aucs = []
                for tr_idx, val_idx in kf.split(regime_data):
                    tr_pool = Pool(regime_data.iloc[tr_idx][all_features], label=regime_data.iloc[tr_idx][target_col], cat_features=all_cat_cols)
                    val_pool = Pool(regime_data.iloc[val_idx][all_features], label=regime_data.iloc[val_idx][target_col], cat_features=all_cat_cols)
                    model = CatBoostClassifier(**params).fit(tr_pool, eval_set=val_pool, use_best_model=True)
                    aucs.append(model.best_score_['validation']['AUC'])
                return np.mean(aucs)

            study = optuna.create_study(direction="maximize")
            study.optimize(objective, n_trials=OPTUNA_TRIALS)
            optimal_params[f"regime_{regime}_{direction}"] = study.best_params
        
    with open(f"{MODEL_DIR}/optimal_params.json", "w") as f:
        json.dump(optimal_params, f, indent=4)
    print(f"\n[SUCCESS] Dual parameters saved to {MODEL_DIR}/optimal_params.json")

if __name__ == "__main__":
    main()
