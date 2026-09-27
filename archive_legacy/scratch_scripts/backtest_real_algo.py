import os
import glob
import numpy as np
import pandas as pd
from google.cloud import bigquery
from catboost import CatBoostClassifier

print("=====================================================================")
print("          STANDALONE ALGORITHM BACKTESTER (REAL CATBOOST MODEL)       ")
print("=====================================================================")

# ---------------------------------------------------------
# 1. FIND & LOAD TRAINED CATBOOST MODEL ARTIFACT
# ---------------------------------------------------------
model_files = glob.glob("/home/skybullet1987/quant_pipeline/**/*.cbm", recursive=True) + \
              glob.glob("/home/skybullet1987/quant_pipeline/**/*.bin", recursive=True)

if model_files:
    model_path = model_files[0]
    print(f"📦 Loading trained CatBoost model from: {model_path}")
    cat_model = CatBoostClassifier()
    cat_model.load_model(model_path)
    
    # Correct CatBoost attribute for feature names
    model_feature_names = getattr(cat_model, 'feature_names_', [])
    if not model_feature_names:
        model_feature_names = getattr(cat_model, 'feature_names', [])
        
    print(f"✅ Model loaded successfully! Requires {len(model_feature_names)} features.")
else:
    print("❌ Could not locate a trained CatBoost model artifact on disk.")
    exit(1)

# ---------------------------------------------------------
# 2. FETCH HISTORICAL FEATURES FROM BIGQUERY
# ---------------------------------------------------------
DAYS_LOOKBACK = 90
client = bigquery.Client(project="parnasa-498503")
print(f"📥 Fetching last {DAYS_LOOKBACK} days of feature matrix from BigQuery...")

query = f"""
SELECT *
FROM `parnasa-498503.market_data.fct_4h_features_tbm`
WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {DAYS_LOOKBACK} DAY)
ORDER BY timestamp ASC
"""

df = client.query(query).to_dataframe()
print(f"✅ Loaded {len(df):,} historical rows across {df['ticker'].nunique()} tickers.")

# Match BigQuery columns to CatBoost model requirements
if model_feature_names:
    missing_cols = [col for col in model_feature_names if col not in df.columns]
    if missing_cols:
        print(f"⚠️ Missing {len(missing_cols)} features in BQ table, filling defaults...")
        for col in missing_cols:
            df[col] = 0.0
    X = df[model_feature_names].fillna(0.0)
else:
    # Fallback if model did not serialize feature names explicitly
    X = df.select_dtypes(include=[np.number]).fillna(0.0)

# ---------------------------------------------------------
# 3. RUN REAL CATBOOST INFERENCE ON HISTORICAL DATA
# ---------------------------------------------------------
print("🧠 Running actual CatBoost model prediction across all historical bars...")

# Get real predicted probabilities from CatBoost
probs = cat_model.predict_proba(X)
df['model_prob'] = probs[:, 1] if probs.shape[1] > 1 else probs[:, 0]

print(f"📊 Probability Distribution -> Min: {df['model_prob'].min():.4f}, Max: {df['model_prob'].max():.4f}, Mean: {df['model_prob'].mean():.4f}")

# Derive HMM Chop Filter (blocks entry when market breadth is flat near 0.50)
df['is_chop_regime'] = (df['market_breadth_sma20'].between(0.42, 0.58)) & (df['rank_vol_compression_ratio'] < 0.25)

# ---------------------------------------------------------
# 4. SIMULATION PARAMETERS & EXECUTION LOOP
# ---------------------------------------------------------
INITIAL_EQUITY = 1000.0
MAX_OPEN_POSITIONS = 5
POSITION_SIZE_PCT = 0.20        # 20% equity / trade
LEVERAGE = 3.0                   # 3x leverage
ROUNDTRIP_COST = 0.0015          # 0.15% fee + spread drag

PROB_LONG_CUTOFF = 0.55          # CatBoost long threshold
PROB_SHORT_CUTOFF = 0.45         # CatBoost short threshold

timestamps = sorted(df['timestamp'].unique())
equity = INITIAL_EQUITY
equity_curve = [equity]
open_positions = []
trade_log = []

for current_ts in timestamps:
    bar_df = df[df['timestamp'] == current_ts]
    
    # --- A. UPDATE OPEN POSITIONS USING REAL PRICE ACTION ---
    active_positions = []
    for pos in open_positions:
        ticker = pos['ticker']
        ticker_row = bar_df[bar_df['ticker'] == ticker]
        
        pos['bars_held'] += 1
        exit_triggered = False
        pnl_pct = 0.0
        exit_reason = ""
        
        if not ticker_row.empty:
            row = ticker_row.iloc[0]
            curr_high = row['high']
            curr_low = row['low']
            curr_close = row['close']
            
            if pos['direction'] == 'LONG':
                if curr_high >= pos['tp_price']:
                    pnl_pct = (pos['tp_price'] - pos['entry_price']) / pos['entry_price']
                    exit_triggered = True
                    exit_reason = "TAKE_PROFIT_HIT"
                elif curr_low <= pos['sl_price']:
                    pnl_pct = (pos['sl_price'] - pos['entry_price']) / pos['entry_price']
                    exit_triggered = True
                    exit_reason = "STOP_LOSS_HIT"
                elif pos['bars_held'] >= 18:
                    pnl_pct = (curr_close - pos['entry_price']) / pos['entry_price']
                    exit_triggered = True
                    exit_reason = "72H_VERTICAL_TIMEOUT"
                    
            elif pos['direction'] == 'SHORT':
                if curr_low <= pos['tp_price']:
                    pnl_pct = (pos['entry_price'] - pos['tp_price']) / pos['entry_price']
                    exit_triggered = True
                    exit_reason = "TAKE_PROFIT_HIT"
                elif curr_high >= pos['sl_price']:
                    pnl_pct = (pos['entry_price'] - curr_close) / pos['entry_price']
                    exit_triggered = True
                    exit_reason = "STOP_LOSS_HIT"
                elif pos['bars_held'] >= 18:
                    pnl_pct = (pos['entry_price'] - curr_close) / pos['entry_price']
                    exit_triggered = True
                    exit_reason = "72H_VERTICAL_TIMEOUT"
        
        if exit_triggered:
            position_size = pos['position_equity'] * LEVERAGE
            gross_pnl = position_size * pnl_pct
            fee_cost = position_size * ROUNDTRIP_COST
            net_pnl = gross_pnl - fee_cost
            
            equity += net_pnl
            trade_log.append({
                'entry_ts': pos['entry_ts'],
                'exit_ts': current_ts,
                'ticker': ticker,
                'direction': pos['direction'],
                'net_pnl': net_pnl,
                'pnl_pct': pnl_pct - ROUNDTRIP_COST,
                'exit_reason': exit_reason
            })
        else:
            active_positions.append(pos)
            
    open_positions = active_positions

    # --- B. EVALUATE NEW ENTRIES USING REAL CATBOOST PROBABILITIES ---
    avg_chop = bar_df['is_chop_regime'].mean()
    is_high_chop = avg_chop > 0.65
    
    if not is_high_chop and len(open_positions) < MAX_OPEN_POSITIONS:
        open_tickers = {p['ticker'] for p in open_positions}
        available_slots = MAX_OPEN_POSITIONS - len(open_positions)
        
        candidates = bar_df[~bar_df['ticker'].isin(open_tickers)].copy()
        
        long_candidates = candidates[candidates['model_prob'] >= PROB_LONG_CUTOFF].sort_values('model_prob', ascending=False)
        short_candidates = candidates[candidates['model_prob'] <= PROB_SHORT_CUTOFF].sort_values('model_prob', ascending=True)
        
        # Enter Longs
        for _, row in long_candidates.head(available_slots).iterrows():
            if row['close'] <= 0 or row['atr_20'] <= 0:
                continue
            pos_equity = equity * POSITION_SIZE_PCT
            open_positions.append({
                'ticker': row['ticker'],
                'direction': 'LONG',
                'entry_price': row['close'],
                'tp_price': row['close'] + (1.50 * row['atr_20']),
                'sl_price': row['close'] - (1.50 * row['atr_20']),
                'entry_ts': current_ts,
                'bars_held': 0,
                'position_equity': pos_equity
            })
            available_slots -= 1
            if available_slots <= 0:
                break
                
    equity_curve.append(equity)

# ---------------------------------------------------------
# 5. PRINT PERFORMANCE AUDIT
# ---------------------------------------------------------
trade_df = pd.DataFrame(trade_log)

print("\n=====================================================================")
print("             REAL CATBOOST ALGORITHM BACKTEST AUDIT                  ")
print("=====================================================================")
print(f" Period Scanned          : Last {DAYS_LOOKBACK} Days")
print(f" Starting Equity         : ${INITIAL_EQUITY:,.2f}")
print(f" Ending Equity           : ${equity:,.2f}")
print(f" Total Net PnL           : ${equity - INITIAL_EQUITY:,.2f} ({(equity/INITIAL_EQUITY - 1)*100:.2f}%)")
print(f" Total Trades Executed   : {len(trade_df)}")

if not trade_df.empty:
    wins = trade_df[trade_df['net_pnl'] > 0]
    win_rate = (len(wins) / len(trade_df)) * 100
    avg_trade_pnl = trade_df['net_pnl'].mean()
    
    eq_series = pd.Series(equity_curve)
    peak = eq_series.cummax()
    drawdown = (eq_series - peak) / peak
    max_dd = drawdown.min() * 100
    
    print(f" Win Rate                : {win_rate:.2f}% ({len(wins)} / {len(trade_df)})")
    print(f" Average PnL per Trade   : ${avg_trade_pnl:.2f}")
    print(f" Max Drawdown            : {max_dd:.2f}%")
    print(f" Exits Breakdown         : {trade_df['exit_reason'].value_counts().to_dict()}")
else:
    print(" ℹ️ Zero trades taken. (CatBoost probabilities stayed below confidence threshold / HMM Chop blocked entries!)")

print("=====================================================================\n")
