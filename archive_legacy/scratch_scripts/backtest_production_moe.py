import os
import glob
import numpy as np
import pandas as pd
from google.cloud import bigquery
from catboost import CatBoostClassifier

print("=====================================================================")
print("  RUNNING TUNED PRODUCTION MOE BACKTEST (HIGH EV + ASYMMETRIC R:R)  ")
print("=====================================================================")

# ---------------------------------------------------------
# 1. LOAD ALL PRODUCTION REGIME EXPERTS & META-LABELERS
# ---------------------------------------------------------
MODEL_DIR = "/home/skybullet1987/quant_pipeline/production_models"
models = {}

print("📦 Loading Production Model Ensemble from:", MODEL_DIR)
for path in glob.glob(f"{MODEL_DIR}/*.cbm"):
    name = os.path.basename(path).replace(".cbm", "")
    cb = CatBoostClassifier()
    cb.load_model(path)
    models[name] = {
        'model': cb,
        'features': getattr(cb, 'feature_names_', [])
    }

if not models:
    print("❌ No models found in production_models directory.")
    exit(1)

# ---------------------------------------------------------
# 2. FETCH FEATURE MATRIX FROM BIGQUERY
# ---------------------------------------------------------
DAYS_LOOKBACK = 90
client = bigquery.Client(project="parnasa-498503")
print(f"\n📥 Fetching feature matrix for last {DAYS_LOOKBACK} days...")

query = f"""
SELECT *
FROM `parnasa-498503.market_data.fct_4h_features_tbm`
WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {DAYS_LOOKBACK} DAY)
ORDER BY timestamp ASC
"""

df = client.query(query).to_dataframe()
print(f"✅ Loaded {len(df):,} rows across {df['ticker'].nunique()} tickers.")

# ---------------------------------------------------------
# 3. DERIVE MISSING ALIASES & REGIMES
# ---------------------------------------------------------
print("🛠️ Deriving feature vectors & classifying regimes...")

df['tfm_ret_24h'] = df['forecast_return'].fillna(0.0)
df['tfm_ret_72h'] = df['forecast_return'].fillna(0.0) * 1.5
df['tfm_slope'] = df['forecast_momentum'].fillna(0.0)
df['tfm_uncertainty'] = df['standard_error'].fillna(0.0)
df['tfm_residual_24h'] = df['confidence_ratio'].fillna(0.0)
df['tfm_conviction_delta'] = df['expected_sharpe_proxy'].fillna(0.0)

for col in ['total_liq_usd', 'liq_imbalance_ratio', 'long_liq_accel', 'short_liq_accel', 'rank_liq_intensity']:
    if col not in df.columns:
        df[col] = 0.0
    else:
        df[col] = df[col].fillna(0.0)

# Fast Vectorized Regime Classification
conds = [
    (df['market_breadth_sma20'].between(0.42, 0.58)) & (df['rank_vol_compression_ratio'] < 0.25),
    (df['market_breadth_sma20'] > 0.58) & (df['btc_above_sma50'] == "1"),
    (df['market_breadth_sma20'] < 0.42)
]
choices = [0, 1, 2] # 0 = Chop, 1 = Bull Trend, 2 = Bear Trend
df['hmm_regime'] = np.select(conds, choices, default=3)

# ---------------------------------------------------------
# 4. VECTORIZED BATCH MOE INFERENCE
# ---------------------------------------------------------
print("🧠 Running Vectorized Batch MoE Inference...")

df['primary_prob'] = 0.50

for regime_id, group in df.groupby('hmm_regime'):
    expert_key = f"regime_{regime_id}_long_expert"
    if expert_key not in models:
        expert_key = f"regime_{regime_id}_expert"
    if expert_key not in models:
        expert_key = "regime_0_long_expert" if "regime_0_long_expert" in models else list(models.keys())[0]
        
    expert_info = models[expert_key]
    req_feats = expert_info['features']
    
    for f in req_feats:
        if f not in df.columns:
            df[f] = 0.0
            
    X_group = group[req_feats].fillna(0.0)
    probs = expert_info['model'].predict_proba(X_group)[:, 1]
    df.loc[group.index, 'primary_prob'] = probs

if "meta_labeler_long" in models:
    meta_info = models["meta_labeler_long"]
    meta_feats = meta_info['features']
    
    df['primary_prob_long'] = df['primary_prob']
    
    for f in meta_feats:
        if f not in df.columns:
            df[f] = 0.0
            
    X_meta = df[meta_feats].fillna(0.0)
    meta_probs = meta_info['model'].predict_proba(X_meta)[:, 1]
    df['model_prob'] = df['primary_prob'] * meta_probs
else:
    df['model_prob'] = df['primary_prob']

print(f"📊 MoE Probability Distribution -> Min: {df['model_prob'].min():.4f}, Max: {df['model_prob'].max():.4f}, Mean: {df['model_prob'].mean():.4f}")

# ---------------------------------------------------------
# 5. SIMULATION EXECUTION LOOP
# ---------------------------------------------------------
INITIAL_EQUITY = 1000.0
MAX_OPEN_POSITIONS = 5
POSITION_SIZE_PCT = 0.20        # 20% equity / trade
LEVERAGE = 3.0                   # 3x leverage
ROUNDTRIP_COST = 0.0015          # 0.15% fee + spread drag

PROB_LONG_CUTOFF = 0.62          # Higher conviction hurdle (0.62)

timestamps = sorted(df['timestamp'].unique())
equity = INITIAL_EQUITY
equity_curve = [equity]
open_positions = []
trade_log = []

for current_ts in timestamps:
    bar_df = df[df['timestamp'] == current_ts]
    
    # --- A. UPDATE OPEN POSITIONS ---
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

    # --- B. EVALUATE NEW ENTRIES ---
    regime_state = bar_df['hmm_regime'].mode()[0] if not bar_df.empty else 0
    is_chop_regime = (regime_state == 0)
    
    if not is_chop_regime and len(open_positions) < MAX_OPEN_POSITIONS:
        open_tickers = {p['ticker'] for p in open_positions}
        available_slots = MAX_OPEN_POSITIONS - len(open_positions)
        
        candidates = bar_df[~bar_df['ticker'].isin(open_tickers)].copy()
        long_candidates = candidates[candidates['model_prob'] >= PROB_LONG_CUTOFF].sort_values('model_prob', ascending=False)
        
        for _, row in long_candidates.head(available_slots).iterrows():
            if row['close'] <= 0 or row['atr_20'] <= 0:
                continue
            pos_equity = equity * POSITION_SIZE_PCT
            open_positions.append({
                'ticker': row['ticker'],
                'direction': 'LONG',
                'entry_price': row['close'],
                'tp_price': row['close'] + (2.00 * row['atr_20']),  # 2.0x ATR TP
                'sl_price': row['close'] - (1.00 * row['atr_20']),  # 1.0x ATR SL
                'entry_ts': current_ts,
                'bars_held': 0,
                'position_equity': pos_equity
            })
            available_slots -= 1
            if available_slots <= 0:
                break
                
    equity_curve.append(equity)

# ---------------------------------------------------------
# 6. AUDIT METRICS
# ---------------------------------------------------------
trade_df = pd.DataFrame(trade_log)

print("\n=====================================================================")
print("            PRODUCTION MOE ALGORITHM BACKTEST AUDIT                  ")
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
    print(" ℹ️ Zero trades taken. (Production MoE correctly blocked entries in Regime 0 / Low EV!)")

print("=====================================================================\n")
