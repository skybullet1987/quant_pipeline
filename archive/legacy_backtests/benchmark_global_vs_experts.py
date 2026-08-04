import pandas as pd
import numpy as np
from catboost import CatBoostClassifier
from google.cloud import bigquery
from hmmlearn.hmm import GaussianHMM
from sklearn.metrics import brier_score_loss, log_loss
import warnings

warnings.filterwarnings("ignore")

PROJECT_ID = "parnasa-498503"
PURGE_BARS = 18 

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

print("1. Ingesting Matrix and Calculating Absolute Macro Features...")
df = load_data()

# Defensive Sort per Asset prior to calculating rolling returns
df = df.sort_values(['ticker', 'timestamp']).reset_index(drop=True)
df['raw_atr_pct'] = df['atr_20'] / df['close']
df['return_7d'] = df.groupby('ticker')['close'].pct_change(42)
df = df.dropna(subset=['return_7d']).reset_index(drop=True)

# Re-sort chronologically for time-series splitting
df = df.sort_values('timestamp').reset_index(drop=True)

df = df[(df['rank_gk_vol_zscore'] >= 0.40) | (df['rank_relative_vol_120p'] >= 0.50)].reset_index(drop=True)
df['target'] = (df['exit_reason'] == 'TP_HIT').astype(int)

# 80/20 Time-Series Train/Val Split with Purge
timestamps = df['timestamp'].sort_values().unique()
split_idx = int(len(timestamps) * 0.80)
train_ts = timestamps[:split_idx]
val_ts = timestamps[split_idx + PURGE_BARS :]

train_df = df[df['timestamp'].isin(train_ts)].copy().reset_index(drop=True)
val_df = df[df['timestamp'].isin(val_ts)].copy().reset_index(drop=True)

print("2. Fitting 3-State Macro HMM...")
macro_train = train_df.groupby('timestamp').agg(
    macro_breadth=('market_breadth_sma20', 'first'),
    macro_volatility=('raw_atr_pct', 'median'),
    macro_momentum=('return_7d', 'median')
).sort_index().ffill().bfill()

hmm_features = ['macro_breadth', 'macro_volatility', 'macro_momentum']
hmm = GaussianHMM(n_components=3, covariance_type="full", n_iter=150, random_state=42)
hmm.fit(macro_train[hmm_features].values)

# Tag Regimes safely
macro_train['hmm_regime'] = hmm.predict(macro_train[hmm_features].values).astype(str)
train_df = pd.merge(train_df, macro_train[['hmm_regime']], left_on='timestamp', right_index=True, how='left')

macro_val = val_df.groupby('timestamp').agg(
    macro_breadth=('market_breadth_sma20', 'first'),
    macro_volatility=('raw_atr_pct', 'median'),
    macro_momentum=('return_7d', 'median')
).sort_index().ffill().bfill()

macro_val['hmm_regime'] = hmm.predict(macro_val[hmm_features].values).astype(str)
val_df = pd.merge(val_df, macro_val[['hmm_regime']], left_on='timestamp', right_index=True, how='left')

all_cat_cols = CAT_COLS_BASE + ['hmm_regime']
all_features = FEATURE_COLS_NUM + all_cat_cols
for col in all_cat_cols:
    train_df[col] = train_df[col].astype(str)
    val_df[col] = val_df[col].astype(str)

val_df['prob_experts'] = 0.0
val_df['prob_global'] = 0.0

print("3. Training 3-Expert Stack...")
for regime in ['0', '1', '2']:
    tr_sub = train_df[train_df['hmm_regime'] == regime]
    val_sub = val_df[val_df['hmm_regime'] == regime]
    
    if len(tr_sub) > 100 and len(val_sub) > 0:
        exp_model = CatBoostClassifier(iterations=800, learning_rate=0.05, depth=5, auto_class_weights='Balanced', verbose=0, random_seed=42)
        exp_model.fit(tr_sub[all_features], tr_sub['target'], cat_features=all_cat_cols)
        val_df.loc[val_sub.index, 'prob_experts'] = exp_model.predict_proba(val_sub[all_features])[:, 1]

print("4. Training Single Global Model...")
global_model = CatBoostClassifier(iterations=800, learning_rate=0.05, depth=5, auto_class_weights='Balanced', verbose=0, random_seed=42)
global_model.fit(train_df[all_features], train_df['target'], cat_features=all_cat_cols)
val_df['prob_global'] = global_model.predict_proba(val_df[all_features])[:, 1]

print("\n========================================================")
print("             CALIBRATION BENCHMARK RESULTS              ")
print("========================================================")

# Calculate Error Metrics (Lower is better)
brier_exp = brier_score_loss(val_df['target'], val_df['prob_experts'])
logloss_exp = log_loss(val_df['target'], val_df['prob_experts'])

brier_glob = brier_score_loss(val_df['target'], val_df['prob_global'])
logloss_glob = log_loss(val_df['target'], val_df['prob_global'])

print(f"3-EXPERT STACK  -> Brier Score: {brier_exp:.5f} | Log Loss: {logloss_exp:.5f}")
print(f"GLOBAL MODEL    -> Brier Score: {brier_glob:.5f} | Log Loss: {logloss_glob:.5f}")
print("--------------------------------------------------------")

if brier_glob < brier_exp:
    print(">>> VERDICT: GLOBAL MODEL is more strictly calibrated.")
else:
    print(">>> VERDICT: 3-EXPERT STACK is more strictly calibrated.")

print("\n--- Empirical Calibration Curve (Global Model) ---")
bins = [0.0, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.80, 1.0]
val_df['prob_bucket'] = pd.cut(val_df['prob_global'], bins=bins)
calib = val_df.groupby('prob_bucket', observed=False).agg(
    Trades=('target', 'count'),
    Avg_Predicted_Prob=('prob_global', lambda x: f"{x.mean():.2%}" if pd.notnull(x.mean()) else "N/A"),
    Actual_Win_Rate=('target', lambda x: f"{x.mean():.2%}" if pd.notnull(x.mean()) else "N/A")
).reset_index()

print(calib.to_string(index=False))
