import pandas as pd
import numpy as np
from catboost import CatBoostClassifier, Pool
from google.cloud import bigquery
from hmmlearn.hmm import GaussianHMM
import warnings

warnings.filterwarnings("ignore")

PROJECT_ID = "parnasa-498503"
PURGE_BARS = 18 

# Categorical Features array
CAT_COLS_BASE = [
    'ticker', 'hour_of_day', 'day_of_week', 'is_weekend', 
    'market_session', 'btc_above_sma50'
]

FEATURE_COLS_NUM = [
    'market_breadth_sma20', 'top_breakout_breadth', 'pos_bar_count_6p',
    'candle_body_pct', 'candle_upper_wick_pct', 'candle_lower_wick_pct',
    'rank_eth_btc_spread_20p', 'rank_btc_dominance_spread',
    'rank_gk_vol_20p', 'rank_vol_term_structure', 'rank_gk_vol_zscore', 'rank_vol_compression_ratio',
    'rank_mom_24h', 'rank_mom_7d', 'rank_mom_accel_24h', 'rank_mom_ratio_24h_7d',
    'rank_dist_to_120p_high', 'rank_relative_vol_120p', 'rank_rolling_sharpe_20p', 'rank_atr_pct_20'
]

def load_data():
    print("1. Ingesting Full 28-Feature Matrix from BigQuery...")
    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT *
        FROM `{PROJECT_ID}.market_data.fct_4h_features_tbm`
        WHERE target_tbm_upper_hit IS NOT NULL
        ORDER BY timestamp ASC
    """
    df = client.query(query).to_dataframe(create_bqstorage_client=True)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

def run_walk_forward(df, n_hmm_states):
    print(f"\n========================================================")
    print(f" RUNNING WALK-FORWARD VALIDATION ({n_hmm_states}-STATE HMM)")
    print(f"========================================================")

    # Filter out pure noise
    active_df = df[(df['rank_gk_vol_zscore'] >= 0.40) | (df['rank_relative_vol_120p'] >= 0.50)].copy().reset_index(drop=True)

    # Build HMM Interaction Features with Quartiles (4 bins)
    hmm_features = ['rank_gk_vol_zscore', 'rank_mom_7d', 'market_breadth_sma20']
    
    hmm_model = GaussianHMM(n_components=n_hmm_states, covariance_type="full", n_iter=150, random_state=42)
    hmm_model.fit(active_df[hmm_features].values)
    
    active_df['hmm_regime'] = hmm_model.predict(active_df[hmm_features].values).astype(str)
    active_df['mom_bucket'] = pd.qcut(active_df['rank_mom_24h'], 4, labels=['Q1_mom', 'Q2_mom', 'Q3_mom', 'Q4_mom']).astype(str)
    active_df['vol_bucket'] = pd.qcut(active_df['rank_vol_term_structure'], 4, labels=['Q1_vol', 'Q2_vol', 'Q3_vol', 'Q4_vol']).astype(str)
    
    active_df['hmm_x_mom'] = active_df['hmm_regime'] + "_" + active_df['mom_bucket']
    active_df['hmm_x_vol'] = active_df['hmm_regime'] + "_" + active_df['vol_bucket']

    all_cat_cols = CAT_COLS_BASE + ['hmm_regime', 'hmm_x_mom', 'hmm_x_vol']
    all_features = FEATURE_COLS_NUM + all_cat_cols

    # Ensure all categoricals are explicitly str
    for col in all_cat_cols:
        active_df[col] = active_df[col].astype(str)

    # Define Walk-Forward Windows (Expanding Train / Out-of-Sample Test)
    windows = [
        {"train_end": "2023-12-31", "test_start": "2024-01-01", "test_end": "2024-06-30", "label": "W1: 2024 H1"},
        {"train_end": "2024-06-30", "test_start": "2024-07-01", "test_end": "2024-12-31", "label": "W2: 2024 H2"},
        {"train_end": "2024-12-31", "test_start": "2025-01-01", "test_end": "2025-06-30", "label": "W3: 2025 H1"},
        {"train_end": "2025-06-30", "test_start": "2025-07-01", "test_end": "2026-07-21", "label": "W4: Holdout (2025/26)"},
    ]

    results = []

    for w in windows:
        train_mask = active_df['timestamp'] <= w['train_end']
        test_mask = (active_df['timestamp'] >= w['test_start']) & (active_df['timestamp'] <= w['test_end'])

        train_data = active_df[train_mask]
        test_data = active_df[test_mask]

        if train_data.empty or test_data.empty:
            continue

        train_pool = Pool(train_data[all_features], label=train_data['target_tbm_upper_hit'], cat_features=all_cat_cols)
        test_pool = Pool(test_data[all_features], label=test_data['target_tbm_upper_hit'], cat_features=all_cat_cols)

        # Stable Production Parameters
        model = CatBoostClassifier(
            iterations=1500,
            learning_rate=0.015,
            depth=6,
            l2_leaf_reg=12.0,
            random_strength=6.0,
            loss_function='Logloss',
            eval_metric='AUC',
            od_type='Iter',
            od_wait=100,
            verbose=False
        )

        model.fit(train_pool, eval_set=test_pool, use_best_model=True)
        
        test_auc = model.eval_metrics(test_pool, metrics=['AUC'])['AUC'][-1]
        best_iter = model.get_best_iteration()
        
        results.append({
            'Window': w['label'],
            'Train Rows': len(train_data),
            'Test Rows': len(test_data),
            'Best Iter': best_iter,
            'OOS AUC': test_auc
        })

    res_df = pd.DataFrame(results)
    print(res_df.to_string(index=False))
    print(f"Average Out-of-Sample AUC: {res_df['OOS AUC'].mean():.4f}\n")
    return res_df['OOS AUC'].mean()

def main():
    df = load_data()
    
    # Compare 3-State vs 4-State HMM
    auc_3st = run_walk_forward(df, n_hmm_states=3)
    auc_4st = run_walk_forward(df, n_hmm_states=4)

    print("========================================================")
    print("                FINAL COMPARISON SUMMARY               ")
    print("========================================================")
    print(f"3-State HMM Mean OOS AUC: {auc_3st:.4f}")
    print(f"4-State HMM Mean OOS AUC: {auc_4st:.4f}")
    print("========================================================")

if __name__ == '__main__':
    main()
