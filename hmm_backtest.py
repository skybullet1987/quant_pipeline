import pandas as pd
import numpy as np
from catboost import CatBoostClassifier
from google.cloud import bigquery
from hmmlearn.hmm import GaussianHMM
import warnings
warnings.filterwarnings('ignore')

PROJECT_ID = "parnasa-498503"
MODEL_PATH = "/home/skybullet1987/quant_pipeline/live_model.cbm"
PURGE_BARS = 60
TARGET_PERCENTILE = 99.0  # Optimal Plateau Threshold (Top 1.0% signals)
MAX_CONCURRENT_TRADES = 3 
MAX_DAILY_TRADES_PER_COIN = 2 # Optimal Falling-Knife Breaker

print("1. Fetching Full Dataset & Macro Features...")
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

print("2. Training Convergence-Optimized Macro HMM on BTCUSD...")
btc_df = df[df['ticker'] == 'BTCUSD'].sort_values('timestamp').copy()
btc_df['btc_ret_24h'] = btc_df['close'].pct_change(1440).fillna(0)
btc_df['btc_vol_24h_avg'] = btc_df['garman_klass_vol_60m'].rolling(1440).mean().fillna(0)

btc_train = btc_df[btc_df['timestamp'].isin(train_ts)].copy()
btc_test = btc_df[btc_df['timestamp'].isin(test_ts)].copy()

# Add tol=1e-2 and n_iter=500 for clean convergence
hmm_model = GaussianHMM(n_components=2, covariance_type="diag", n_iter=500, tol=1e-2, random_state=42)
hmm_features = ['btc_ret_24h', 'btc_vol_24h_avg']
hmm_model.fit(btc_train[hmm_features])

regime_stats = btc_train.groupby(hmm_model.predict(btc_train[hmm_features]))['btc_ret_24h'].mean()
SAFE_REGIME = regime_stats.idxmax()
DANGER_REGIME = regime_stats.idxmin()

btc_test['regime'] = hmm_model.predict(btc_test[hmm_features])
regime_map = btc_test[['timestamp', 'regime']].set_index('timestamp')
test_df = test_df.join(regime_map, on='timestamp')
test_df['regime'] = test_df['regime'].ffill().fillna(DANGER_REGIME) 

print("3. Generating CatBoost Predictions...")
model = CatBoostClassifier()
model.load_model(MODEL_PATH)

feature_cols = [
    'rank_nofi', 'rank_gk_vol', 'rank_vol_term_structure',
    'rank_vwap_dev_60m', 'rank_alpha_mom_15m', 'rank_alpha_mom_60m'
]
cat_cols = ['ticker', 'hour_of_day', 'day_of_week', 'is_weekend']

test_df['prob'] = model.predict_proba(test_df[feature_cols + cat_cols])[:, 1]
dynamic_threshold = np.percentile(test_df['prob'], TARGET_PERCENTILE)
print(f"4. Simulating Execution (Threshold >= {dynamic_threshold:.4f} | Top 1.0%)...")

signals = test_df[(test_df['prob'] >= dynamic_threshold) & (test_df['regime'] == SAFE_REGIME)].copy()
signals = signals.sort_values(by=['timestamp', 'prob'], ascending=[True, False])

valid_trades = []
active_cooldowns = {} 
daily_coin_counts = {}

for idx, row in signals.iterrows():
    tstamp = row['timestamp']
    ticker = row['ticker']
    date_str = tstamp.date()
    
    if date_str not in daily_coin_counts:
        daily_coin_counts[date_str] = {}
    
    expired = [t for t, entry_time in active_cooldowns.items() if (tstamp - entry_time).total_seconds() >= (PURGE_BARS * 60)]
    for t in expired:
        del active_cooldowns[t]
        
    if ticker in active_cooldowns:
        continue
    if len(active_cooldowns) >= MAX_CONCURRENT_TRADES:
        continue
    if daily_coin_counts[date_str].get(ticker, 0) >= MAX_DAILY_TRADES_PER_COIN:
        continue
        
    valid_trades.append(row)
    active_cooldowns[ticker] = tstamp
    daily_coin_counts[date_str][ticker] = daily_coin_counts[date_str].get(ticker, 0) + 1

trades = pd.DataFrame(valid_trades)

def calculate_triple_barrier_pnl(row):
    if row['target_tp_hit'] == 1.0:
        return 0.012  # +1.2% Net Gain (after fees/slippage)
    else:
        raw_return = row['target_ret_60m']
        if raw_return <= -0.018:
            return -0.018 # Hard Stop Loss
        else:
            return raw_return - 0.0016 # Time exit minus fee hurdle

trades['pnl_pct'] = trades.apply(calculate_triple_barrier_pnl, axis=1)
trades['cumulative_pnl'] = trades['pnl_pct'].cumsum()

total_trades = len(trades)
winners = len(trades[trades['pnl_pct'] > 0])
win_rate = winners / total_trades
max_drawdown = (trades['cumulative_pnl'] - trades['cumulative_pnl'].cummax()).min()

trades['date'] = trades['timestamp'].dt.date
daily_pnl = trades.groupby('date')['pnl_pct'].sum()
daily_sharpe = (daily_pnl.mean() / daily_pnl.std()) * np.sqrt(365) if daily_pnl.std() > 0 else 0

print("\n==================================================")
print("     FINAL PRODUCTION BACKTEST REPORT (OPTIMIZED)")
print("==================================================")
print(f"Total Trades Executed: {total_trades:,}")
print(f"Win Rate (> 0% PnL):   {win_rate*100:.2f}%")
print(f"Expected Value (EV):   {trades['pnl_pct'].mean()*100:.3f}% per trade")
print(f"Total Net Return:      {trades['cumulative_pnl'].iloc[-1]*100:.2f}%")
print(f"Max Drawdown:          {max_drawdown*100:.2f}%")
print(f"Daily Sharpe Ratio:    {daily_sharpe:.2f}")

print("\n--- Top 5 Most Profitable Coins ---")
coin_pnl = trades.groupby('ticker')['pnl_pct'].sum().sort_values(ascending=False)
for coin, pnl in coin_pnl.head(5).items():
    count = len(trades[trades['ticker'] == coin])
    print(f" {coin:<8}: +{pnl*100:>5.2f}% ({count} trades)")

print("\n--- Top 5 Worst Performing Coins ---")
for coin, pnl in coin_pnl.tail(5).sort_values().items():
    count = len(trades[trades['ticker'] == coin])
    print(f" {coin:<8}: {pnl*100:>6.2f}% ({count} trades)")
print("==================================================")
