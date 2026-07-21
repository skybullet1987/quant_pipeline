import pandas as pd
import numpy as np
from google.cloud import bigquery
import itertools

PROJECT_ID = "parnasa-498503"

print("1. Fetching Price Action Data for HPO...")
client = bigquery.Client(project=PROJECT_ID)

query = f"""
    SELECT 
        close, atr_60m, max_240m, min_240m, ret_240m
    FROM `{PROJECT_ID}.market_data.features_matrix`
    WHERE max_240m IS NOT NULL
    AND RAND() < 0.3
"""
df = client.query(query).to_dataframe(create_bqstorage_client=True)

# THE FIX: Drop incomplete look-ahead rows to prevent NaN math
df = df.dropna().reset_index(drop=True)
print(f"   Loaded {len(df):,} clean sample rows for optimization.")

tp_multipliers = np.arange(0.5, 3.25, 0.25)
sl_multipliers = np.arange(0.5, 3.25, 0.25)

results = []

print("2. Running Grid Search (Label Optimization)...")
for tp, sl in itertools.product(tp_multipliers, sl_multipliers):
    tp_price = df['close'] + (tp * df['atr_60m'])
    sl_price = df['close'] - (sl * df['atr_60m'])
    
    win = (df['max_240m'] >= tp_price) & (df['min_240m'] > sl_price)
    loss = (df['min_240m'] <= sl_price)
    timeout = (df['max_240m'] < tp_price) & (df['min_240m'] > sl_price)
    
    tp_pct = (tp * df['atr_60m']) / df['close']
    sl_pct = -(sl * df['atr_60m']) / df['close']
    
    TAKER_ENTRY = 0.0070 
    MAKER_EXIT  = 0.0030 
    TAKER_EXIT  = 0.0080 
    
    pnl = np.zeros(len(df))
    pnl[win] = tp_pct[win] - (TAKER_ENTRY + MAKER_EXIT)
    pnl[loss] = sl_pct[loss] - (TAKER_ENTRY + TAKER_EXIT)
    pnl[timeout] = df['ret_240m'][timeout] - (TAKER_ENTRY + TAKER_EXIT)
    
    win_rate = win.mean()
    avg_pnl = pnl.mean() * 100 
    
    if win_rate > 0.10:
        results.append({
            'TP_Multiplier': tp,
            'SL_Multiplier': sl,
            'Base_Win_Rate': win_rate * 100,
            'Expected_Value_Pct': avg_pnl
        })

res_df = pd.DataFrame(results).sort_values(by='Expected_Value_Pct', ascending=False)

print("\n==================================================")
print("   TOP 10 TAKE PROFIT / STOP LOSS COMBINATIONS")
print("==================================================")
print(res_df.head(10).to_string(index=False))
