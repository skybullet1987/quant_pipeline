import pandas as pd
import numpy as np
from catboost import CatBoostClassifier
from google.cloud import bigquery
from hmmlearn.hmm import GaussianHMM
import itertools
import warnings
warnings.filterwarnings('ignore')

PROJECT_ID = "parnasa-498503"
MODEL_PATH = "/home/skybullet1987/quant_pipeline/live_model.cbm"
PURGE_BARS = 60
MAX_CONCURRENT_TRADES = 3

print("1. Fetching Full Dataset & Generating HMM Regimes...")
client = bigquery.Client(project=PROJECT_ID)

query = f"""
    SELECT 
        timestamp, ticker, hour_of_day, day_of_week, is_weekend,
        rank_nofi, rank_gk_vol, rank_vol_term_structure,
        rank_vwap_dev_60m, rank_alpha_mom_15m, rank_alpha_mom_60m,
        target_tp_hit, target_ret_60m, close, garman_klass_vol_60m
    FROM `{PROJECT_ID}.market_data.features_matrix`
    WHERE target_tp_hit IS NOT NULL 
      AND target_ret_60m IS NOT NULL
    ORDER BY timestamp ASC
"""
df = client.query(query).to_dataframe(create_bqstorage_client=True)
df['timestamp'] = pd.to_datetime(df['timestamp'])

timestamps = df['timestamp'].sort_values().unique()
n = len(timestamps)
train_end_idx = int(n * 0.70)
eval_end_idx = int(n * 0.85)

train_ts = timestamps[:train_end_idx]
test_ts = timestamps[eval_end_idx + PURGE_BARS :]
test_df = df[df['timestamp'].isin(test_ts)].copy()

# HMM Macro Filter
btc_df = df[df['ticker'] == 'BTCUSD'].sort_values('timestamp').copy()
btc_df['btc_ret_24h'] = btc_df['close'].pct_change(1440).fillna(0)
btc_df['btc_vol_24h_avg'] = btc_df['garman_klass_vol_60m'].rolling(1440).mean().fillna(0)

btc_train = btc_df[btc_df['timestamp'].isin(train_ts)].copy()
btc_test = btc_df[btc_df['timestamp'].isin(test_ts)].copy()

hmm_model = GaussianHMM(n_components=2, covariance_type="diag", n_iter=200, random_state=42)
hmm_features = ['btc_ret_24h', 'btc_vol_24h_avg']
hmm_model.fit(btc_train[hmm_features])

regime_stats = btc_train.groupby(hmm_model.predict(btc_train[hmm_features]))['btc_ret_24h'].mean()
SAFE_REGIME = regime_stats.idxmax()
DANGER_REGIME = regime_stats.idxmin()

btc_test['regime'] = hmm_model.predict(btc_test[hmm_features])
regime_map = btc_test[['timestamp', 'regime']].set_index('timestamp')
test_df = test_df.join(regime_map, on='timestamp')
test_df['regime'] = test_df['regime'].ffill().fillna(DANGER_REGIME) 

print("2. Generating CatBoost Predictions...")
model = CatBoostClassifier()
model.load_model(MODEL_PATH)
feature_cols = ['rank_nofi', 'rank_gk_vol', 'rank_vol_term_structure', 'rank_vwap_dev_60m', 'rank_alpha_mom_15m', 'rank_alpha_mom_60m']
cat_cols = ['ticker', 'hour_of_day', 'day_of_week', 'is_weekend']
test_df['prob'] = model.predict_proba(test_df[feature_cols + cat_cols])[:, 1]

print("\n3. Executing Parameter Sweep Matrix...")
print("=" * 80)
print(f"{'Percentile':<12} | {'Daily Cap':<9} | {'Trades':<6} | {'Win Rate':<8} | {'EV / Trade':<10} | {'Sharpe':<6} | {'Max DD':<8}")
print("-" * 80)

percentiles_to_test = [98.0, 98.5, 99.0, 99.5, 99.9]
caps_to_test = [1, 2, 3]

def calculate_triple_barrier_pnl(row):
    if row['target_tp_hit'] == 1.0: return 0.012 
    raw_return = row['target_ret_60m']
    return -0.018 if raw_return <= -0.018 else raw_return - 0.0016 

for pct, cap in itertools.product(percentiles_to_test, caps_to_test):
    dynamic_threshold = np.percentile(test_df['prob'], pct)
    
    signals = test_df[(test_df['prob'] >= dynamic_threshold) & (test_df['regime'] == SAFE_REGIME)].copy()
    signals = signals.sort_values(by=['timestamp', 'prob'], ascending=[True, False])

    valid_trades = []
    active_cooldowns = {} 
    daily_coin_counts = {}

    for idx, row in signals.iterrows():
        tstamp = row['timestamp']
        ticker = row['ticker']
        date_str = tstamp.date()
        
        if date_str not in daily_coin_counts: daily_coin_counts[date_str] = {}
        
        expired = [t for t, entry_time in active_cooldowns.items() if (tstamp - entry_time).total_seconds() >= (PURGE_BARS * 60)]
        for t in expired: del active_cooldowns[t]
            
        if ticker in active_cooldowns or len(active_cooldowns) >= MAX_CONCURRENT_TRADES or daily_coin_counts[date_str].get(ticker, 0) >= cap:
            continue
            
        valid_trades.append(row)
        active_cooldowns[ticker] = tstamp
        daily_coin_counts[date_str][ticker] = daily_coin_counts[date_str].get(ticker, 0) + 1

    if not valid_trades:
        print(f"{pct:<12.1f} | {cap:<9} | {'0':<6} | {'N/A':<8} | {'N/A':<10} | {'N/A':<6} | {'N/A':<8}")
        continue

    trades = pd.DataFrame(valid_trades)
    trades['pnl_pct'] = trades.apply(calculate_triple_barrier_pnl, axis=1)
    trades['cumulative_pnl'] = trades['pnl_pct'].cumsum()
    
    total_trades = len(trades)
    win_rate = len(trades[trades['pnl_pct'] > 0]) / total_trades
    ev = trades['pnl_pct'].mean()
    max_drawdown = (trades['cumulative_pnl'] - trades['cumulative_pnl'].cummax()).min()
    
    trades['date'] = trades['timestamp'].dt.date
    daily_pnl = trades.groupby('date')['pnl_pct'].sum()
    sharpe = (daily_pnl.mean() / daily_pnl.std()) * np.sqrt(365) if daily_pnl.std() > 0 else 0
    
    print(f"{pct:<12.1f} | {cap:<9} | {total_trades:<6} | {win_rate*100:>7.2f}% | {ev*100:>9.3f}% | {sharpe:>6.2f} | {max_drawdown*100:>7.2f}%")

print("=" * 80)
