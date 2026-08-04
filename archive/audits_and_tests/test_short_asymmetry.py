import pandas as pd
import numpy as np
from catboost import CatBoostClassifier
from google.cloud import bigquery
from hmmlearn.hmm import GaussianHMM
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import brier_score_loss, log_loss
import warnings

warnings.filterwarnings("ignore")

PROJECT_ID = "parnasa-498503"
PURGE_BARS = 18 

WIN_FRICTION = 0.00035 + 0.0002
LOSS_FRICTION = 0.00035 + 0.0002

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

print("1. Ingesting Matrix and Calculating Targets...")
df = load_data()
df = df.sort_values(['ticker', 'timestamp']).reset_index(drop=True)
df['raw_atr_pct'] = df['atr_20'] / df['close']
df['return_7d'] = df.groupby('ticker')['close'].pct_change(42)
df = df.dropna(subset=['return_7d']).sort_values('timestamp').reset_index(drop=True)

df = df[(df['rank_gk_vol_zscore'] >= 0.40) | (df['rank_relative_vol_120p'] >= 0.50)].reset_index(drop=True)

# Dual Targets
df['target_long'] = (df['exit_reason'] == 'TP_HIT').astype(int)
df['target_short'] = (df['exit_reason'] == 'SL_HIT').astype(int)

# 80/20 Time-Series Train/Val Split
timestamps = df['timestamp'].sort_values().unique()
split_idx = int(len(timestamps) * 0.80)
train_ts = timestamps[:split_idx]
val_ts = timestamps[split_idx + PURGE_BARS :]

train_df = df[df['timestamp'].isin(train_ts)].copy().reset_index(drop=True)
val_df = df[df['timestamp'].isin(val_ts)].copy().reset_index(drop=True)

print("2. Assigning HMM Regimes...")
hmm_features = ['macro_breadth', 'macro_volatility', 'macro_momentum']

macro_train = train_df.groupby('timestamp').agg(
    macro_breadth=('market_breadth_sma20', 'first'),
    macro_volatility=('raw_atr_pct', 'median'),
    macro_momentum=('return_7d', 'median')
).sort_index().ffill().bfill()

hmm = GaussianHMM(n_components=3, covariance_type="full", n_iter=150, random_state=42)
hmm.fit(macro_train[hmm_features].values)

# Merging regime safely back to the training matrix
macro_train['hmm_regime'] = hmm.predict(macro_train[hmm_features].values).astype(str)
train_df = pd.merge(train_df, macro_train[['hmm_regime']], left_on='timestamp', right_index=True, how='left')

macro_val = val_df.groupby('timestamp').agg(
    macro_breadth=('market_breadth_sma20', 'first'),
    macro_volatility=('raw_atr_pct', 'median'),
    macro_momentum=('return_7d', 'median')
).sort_index().ffill().bfill()

# Merging regime safely back to the validation matrix
macro_val['hmm_regime'] = hmm.predict(macro_val[hmm_features].values).astype(str)
val_df = pd.merge(val_df, macro_val[['hmm_regime']], left_on='timestamp', right_index=True, how='left')

all_cat_cols = CAT_COLS_BASE + ['hmm_regime']
all_features = FEATURE_COLS_NUM + all_cat_cols
for col in all_cat_cols:
    train_df[col] = train_df[col].astype(str)
    val_df[col] = val_df[col].astype(str)

print("3. Training Dual-Directional Global CatBoost Models...")
model_long = CatBoostClassifier(iterations=800, learning_rate=0.05, depth=5, auto_class_weights='Balanced', verbose=0, random_seed=42)
model_long.fit(train_df[all_features], train_df['target_long'], cat_features=all_cat_cols)

model_short = CatBoostClassifier(iterations=800, learning_rate=0.05, depth=5, auto_class_weights='Balanced', verbose=0, random_seed=42)
model_short.fit(train_df[all_features], train_df['target_short'], cat_features=all_cat_cols)

val_df['raw_prob_long'] = model_long.predict_proba(val_df[all_features])[:, 1]
val_df['raw_prob_short'] = model_short.predict_proba(val_df[all_features])[:, 1]

print("4. Fitting Isotonic Calibrators...")
calib_long = IsotonicRegression(out_of_bounds='clip')
calib_long.fit(model_long.predict_proba(train_df[all_features])[:, 1], train_df['target_long'])

calib_short = IsotonicRegression(out_of_bounds='clip')
calib_short.fit(model_short.predict_proba(train_df[all_features])[:, 1], train_df['target_short'])

val_df['calib_prob_long'] = calib_long.predict(val_df['raw_prob_long'])
val_df['calib_prob_short'] = calib_short.predict(val_df['raw_prob_short'])

print("\n========================================================")
print("     SHORT-SIDE ASYMMETRY & CALIBRATION VERIFICATION    ")
print("========================================================")

for direction, prob_col, target_col in [('LONG', 'calib_prob_long', 'target_long'), ('SHORT', 'calib_prob_short', 'target_short')]:
    print(f"\n--- Direction: {direction} ---")
    signals = val_df[val_df[prob_col] >= 0.55].copy()
    if len(signals) == 0:
        print("No signals above 0.55 calibrated probability threshold.")
        continue
        
    win_rate = (signals[target_col] == 1).mean()
    net_returns = np.where(signals[target_col] == 1, (1.50 * signals['raw_atr_pct']) - WIN_FRICTION, (-1.50 * signals['raw_atr_pct']) - LOSS_FRICTION)
    avg_net_ret = net_returns.mean()
    std_net_ret = net_returns.std() + 1e-6
    sharpe = (avg_net_ret / std_net_ret) * np.sqrt(len(signals))
    
    print(f"  Signal Count: {len(signals):,}")
    print(f"  Realized Win Rate: {win_rate:.2%}")
    print(f"  Avg Net Return per Trade: {avg_net_ret:.4%}")
    print(f"  Sharpe Ratio: {sharpe:.2f}")

