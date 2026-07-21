import pandas as pd
import numpy as np
from catboost import CatBoostClassifier
from google.cloud import bigquery
import warnings
warnings.filterwarnings('ignore')

PROJECT_ID = "parnasa-498503"
MODEL_PATH = "/home/skybullet1987/quant_pipeline/live_model.cbm"
PURGE_BARS = 240
TARGET_PERCENTILE = 98.0  
MAX_CONCURRENT_TRADES = 3 
MAX_DAILY_TRADES_PER_COIN = 2 

STARTING_CAPITAL = 1000.0
ALLOCATION_PCT = 0.10  # 10% Risk

print("1. Fetching Phase 2 Feature Matrix...")
client = bigquery.Client(project=PROJECT_ID)

query = f"""
    SELECT 
        timestamp, ticker, close, min_240m, max_240m,
        candle_body_pct, candle_upper_wick_pct, candle_lower_wick_pct,
        rank_nofi, rank_volume_zscore, rank_gk_vol,
        rank_vol_term_structure, rank_vwap_dev_60m, rank_alpha_mom_15m,
        rank_alpha_mom_60m, rank_btc_beta_60m,
        btc_ret_24h, 
        target_hard_4_2, ret_240m
    FROM `{PROJECT_ID}.market_data.features_matrix`
    WHERE target_hard_4_2 IS NOT NULL
    ORDER BY timestamp ASC
"""
df = client.query(query).to_dataframe(create_bqstorage_client=True)
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.dropna()

timestamps = df['timestamp'].sort_values().unique()
n = len(timestamps)
eval_end_idx = int(n * 0.85)

test_ts = timestamps[eval_end_idx + PURGE_BARS :]
test_df = df[df['timestamp'].isin(test_ts)].copy()

print("2. Generating Microstructure Predictions...")
model = CatBoostClassifier()
model.load_model(MODEL_PATH)
feature_cols = [
    'candle_body_pct', 'candle_upper_wick_pct', 'candle_lower_wick_pct',
    'rank_nofi', 'rank_volume_zscore', 'rank_gk_vol',
    'rank_vol_term_structure', 'rank_vwap_dev_60m', 'rank_alpha_mom_15m',
    'rank_alpha_mom_60m', 'rank_btc_beta_60m'
]
test_df['prob'] = model.predict_proba(test_df[feature_cols])[:, 1]
dynamic_threshold = np.percentile(test_df['prob'], TARGET_PERCENTILE)

print(f"3. Simulating SPOT MAKER Execution (Threshold: {dynamic_threshold:.4f} | Macro Filter ON)...")

signals = test_df[(test_df['prob'] >= dynamic_threshold) & (test_df['btc_ret_24h'] > 0.005)].copy()
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
        
    if ticker in active_cooldowns or len(active_cooldowns) >= MAX_CONCURRENT_TRADES or daily_coin_counts[date_str].get(ticker, 0) >= MAX_DAILY_TRADES_PER_COIN:
        continue
        
    valid_trades.append(row)
    active_cooldowns[ticker] = tstamp
    daily_coin_counts[date_str][ticker] = daily_coin_counts[date_str].get(ticker, 0) + 1

trades = pd.DataFrame(valid_trades)

if trades.empty:
    print("No valid trades executed.")
    exit()

def calculate_spot_maker_pnl(row):
    MAKER_ENTRY = 0.0030 # Kraken Tier 2 Limit Buy
    MAKER_EXIT  = 0.0030 # Kraken Tier 2 Limit Sell (Take Profit)
    TAKER_EXIT  = 0.0080 # Market Stop Loss (Fee + Slippage)

    if row['target_hard_4_2'] == 1.0:
        # Limit entry filled, Limit TP hit
        return 0.040 - (MAKER_ENTRY + MAKER_EXIT)  
    else:
        # Check if it triggered the Stop Loss before the 4h window ended
        if row['min_240m'] <= row['close'] * 0.980:
            return -0.020 - (MAKER_ENTRY + TAKER_EXIT) 
        else:
            return row['ret_240m'] - (MAKER_ENTRY + TAKER_EXIT) 

trades['pnl_pct'] = trades.apply(calculate_spot_maker_pnl, axis=1)

equity = STARTING_CAPITAL
equity_curve = []
peak_equity = STARTING_CAPITAL
max_dd_usd = 0
max_dd_pct = 0

for idx, row in trades.iterrows():
    trade_size_usd = equity * ALLOCATION_PCT
    dollar_pnl = trade_size_usd * row['pnl_pct']
    equity += dollar_pnl
    
    if equity > peak_equity:
        peak_equity = equity
        
    current_dd_usd = equity - peak_equity
    current_dd_pct = current_dd_usd / peak_equity
    
    if current_dd_pct < max_dd_pct:
        max_dd_pct = current_dd_pct
        max_dd_usd = current_dd_usd
        
    equity_curve.append(equity)

trades['account_equity'] = equity_curve

total_trades = len(trades)
winners = len(trades[trades['pnl_pct'] > 0])
win_rate = winners / total_trades
final_equity = trades['account_equity'].iloc[-1]
net_profit_usd = final_equity - STARTING_CAPITAL

print("\n==================================================")
print("  SPOT MAKER COMPOUNDED EQUITY REPORT ($1,000 START)")
print("==================================================")
print(f"Position Sizing:       {ALLOCATION_PCT*100:.0f}% of Account Balance")
print(f"Total Trades Executed: {total_trades:,}")
print(f"Win Rate:              {win_rate*100:.2f}%")
print(f"Average PnL per Trade: {trades['pnl_pct'].mean()*100:.3f}% (After Fees)")
print("-" * 50)
print(f"Starting Balance:      ${STARTING_CAPITAL:,.2f}")
print(f"Final Balance:         ${final_equity:,.2f}")
print(f"Net Dollar Profit:     ${net_profit_usd:,.2f} ({(net_profit_usd/STARTING_CAPITAL)*100:.2f}%)")
print(f"Maximum Drawdown:      {max_dd_pct*100:.2f}% (${abs(max_dd_usd):.2f})")
print("==================================================")
