import os, joblib, warnings
import pandas as pd
import numpy as np
from google.cloud import bigquery
from catboost import CatBoostClassifier

warnings.filterwarnings("ignore")
PROJECT_ID = "parnasa-498503"
MODEL_DIR = "/home/skybullet1987/quant_pipeline/production_models"

ENTRY_THRESHOLD_SHORT = 0.52
KELLY_FRACTION_SHORT = 0.50
HARD_LIQUIDITY_CAP = 150000.0
PORTFOLIO_RISK_CAP = 0.05  # 5.0% Cap

MAJORS = {'BTCUSD', 'ETHUSD', 'SOLUSD', 'BTC', 'ETH', 'SOL'}
LIQUID_ALTS = {'AVAXUSD', 'NEARUSD', 'LINKUSD', 'SUIUSD', 'AAVEUSD', 'BNBUSD', 'XRPUSD', 'DOGEUSD', 'ADAUSD', 'TRXUSD', 'AVAX', 'NEAR', 'LINK', 'SUI', 'AAVE', 'BNB', 'XRP', 'DOGE', 'ADA', 'TRX'}
MID_CAPS = {'ICPUSD', 'DOTUSD', 'UNIUSD', 'LTCUSD', 'APTUSD', 'INJUSD', 'STXUSD', 'RNDRUSD', 'ICP', 'DOT', 'UNI', 'LTC', 'APT', 'INJ', 'STX', 'RNDR'}

def get_tier_frictions(ticker):
    t = str(ticker).upper()
    if t in MAJORS:
        return 0.0007, 0.0005, 0.0010
    elif t in LIQUID_ALTS:
        return 0.0010, 0.0008, 0.0015
    elif t in MID_CAPS:
        return 0.0016, 0.0012, 0.0022
    else:
        return 0.0030, 0.0025, 0.0045

print("[INFO] Fetching 90-day dataset from BigQuery for Drawdown Autopsy...")
client = bigquery.Client(project=PROJECT_ID)
query = f"""
    SELECT 
        f.*, 
        p.target_short, p.minutes_in_trade
    FROM `{PROJECT_ID}.market_data.fct_4h_features_tbm` f
    INNER JOIN `{PROJECT_ID}.market_data.fct_exact_path_resolution` p
        ON f.ticker = p.ticker AND f.timestamp = p.signal_time
    ORDER BY f.timestamp ASC
"""
df = client.query(query).to_dataframe(create_bqstorage_client=True)
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Load models and score
hmm_model, hmm_scaler = joblib.load(f"{MODEL_DIR}/hmm_macro.pkl"), joblib.load(f"{MODEL_DIR}/hmm_scaler.pkl")
hmm_features, canonical_order = joblib.load(f"{MODEL_DIR}/hmm_feature_names.pkl"), joblib.load(f"{MODEL_DIR}/hmm_canonical_order.pkl")
meta_short, cal_short = CatBoostClassifier().load_model(f"{MODEL_DIR}/meta_labeler_short.cbm"), joblib.load(f"{MODEL_DIR}/meta_calibrator_short.pkl")
all_cat_cols, all_features = joblib.load(f"{MODEL_DIR}/cat_cols.pkl"), joblib.load(f"{MODEL_DIR}/feature_names.pkl")

for col in all_features:
    if col not in df.columns: df[col] = 0.0
for col in hmm_features:
    if col not in df.columns: df[col] = 0.0
df = df.fillna(0)

scaled_x = hmm_scaler.transform(df[hmm_features].fillna(0))
can_probs = hmm_model.predict_proba(scaled_x)[:, canonical_order]
df['hmm_p_chop'], df['hmm_regime'] = can_probs[:, 0], can_probs.argmax(axis=1).astype(str)
for col in all_cat_cols: df[col] = df[col].astype(str)

df['primary_prob_short'] = 0.0
for regime in ['0', '1', '2']:
    m_s_path = f"{MODEL_DIR}/regime_{regime}_short_expert.cbm"
    idx = df[df['hmm_regime'] == regime].index
    if len(idx) > 0 and os.path.exists(m_s_path):
        df.loc[idx, 'primary_prob_short'] = CatBoostClassifier().load_model(m_s_path).predict_proba(df.loc[idx, all_features])[:, 1]

df['calibrated_prob_short'] = cal_short.predict(meta_short.predict_proba(df[meta_short.feature_names_])[:, 1])

df_triggers = df[(df['hmm_p_chop'] < 0.50) & (df['hmm_regime'] != '0') & (df['calibrated_prob_short'] >= ENTRY_THRESHOLD_SHORT)].copy()

# Run Simulation and Log Equity / Trade Details
capital = 1000.0
peak_capital = capital
trade_logs = []
equity_series = [capital]

grouped = df_triggers.groupby('timestamp')

for ts, group in grouped:
    current_timestamp_open_risk = 0.0
    for _, row in group.iterrows():
        coin = str(row['ticker']).replace("USDT", "").replace("USD", "").upper()
        entry_price, atr = float(row['close']), float(row['atr_20'])
        p_s = float(row['calibrated_prob_short'])
        
        if entry_price <= 0 or atr <= 0: continue

        c_entry, c_tp, c_sl = get_tier_frictions(coin)
        r_dist = (1.50 * atr) / entry_price
        
        net_win = r_dist - c_entry - c_tp
        net_loss = r_dist + c_entry + c_sl
        ev = (p_s * net_win) - ((1.0 - p_s) * net_loss)
        
        if ev <= 0 or net_win <= 0: continue
            
        dynamic_payoff = net_win / net_loss if net_loss > 0 else 1.0
        kelly_f = p_s - ((1.0 - p_s) / dynamic_payoff)
        
        trade_notional_pct = min(kelly_f * KELLY_FRACTION_SHORT * 10.0, 2.0)
        trade_risk_pct = trade_notional_pct * net_loss
        
        if current_timestamp_open_risk + trade_risk_pct > PORTFOLIO_RISK_CAP:
            remaining = max(0.0, PORTFOLIO_RISK_CAP - current_timestamp_open_risk)
            if remaining <= 0.001: continue
            scale_factor = remaining / trade_risk_pct
            trade_notional_pct *= scale_factor
            trade_risk_pct = remaining
        
        current_timestamp_open_risk += trade_risk_pct
        notional_size = min(capital * trade_notional_pct, HARD_LIQUIDITY_CAP)
        
        hit_target = bool(row['target_short'])
        pnl = notional_size * net_win if hit_target else -notional_size * net_loss
        
        capital += pnl
        if capital > peak_capital: peak_capital = capital
        
        trade_logs.append({
            'timestamp': ts,
            'ticker': coin,
            'hmm_regime': str(row['hmm_regime']),
            'pnl': pnl,
            'hit_target': hit_target,
            'capital_after': capital,
            'peak_capital': peak_capital,
            'drawdown_pct': (capital - peak_capital) / peak_capital
        })
        equity_series.append(capital)

trades_df = pd.DataFrame(trade_logs)

# Drawdown Episode Decomposition
eq_arr = np.array(equity_series)
peaks = np.maximum.accumulate(eq_arr)
drawdowns = (eq_arr - peaks) / peaks

# Locate top 3 non-overlapping peak-to-trough episodes
worst_indices = np.argsort(drawdowns)
top_episodes = []
used_ranges = set()

for idx in worst_indices:
    if len(top_episodes) >= 3: break
    peak_idx = np.argmax(eq_arr[:idx+1])
    if any(r[0] <= idx <= r[1] or r[0] <= peak_idx <= r[1] for r in used_ranges):
        continue
    top_episodes.append((peak_idx, idx, drawdowns[idx]))
    used_ranges.add((peak_idx, idx))

print("\n" + "="*80)
print("🔍 TOP 3 DRAWDOWN EPISODE AUTOPSY (5.0% OPEN RISK CAP)")
print("="*80)

for rank, (p_idx, t_idx, dd_val) in enumerate(top_episodes, 1):
    sub_df = trades_df.iloc[max(0, p_idx-1):t_idx]
    if sub_df.empty: continue
    
    win_rate = (sub_df['hit_target'].mean()) * 100.0
    regime_counts = sub_df['hmm_regime'].value_counts(normalize=True) * 100.0
    regime_str = ", ".join([f"R{reg}: {pct:.1f}%" for reg, pct in regime_counts.items()])
    
    print(f"\n# {rank} Worst Drawdown: {dd_val*100.0:.2f}% Depth")
    print(f"   Peak Equity:        ${eq_arr[p_idx]:,.2f} (Trade #{p_idx})")
    print(f"   Trough Equity:      ${eq_arr[t_idx]:,.2f} (Trade #{t_idx})")
    print(f"   Trades in Episode:  {len(sub_df)}")
    print(f"   Episode Win Rate:   {win_rate:.2f}%")
    print(f"   HMM Regime Mix:     {regime_str}")
    print(f"   Time Range:         {sub_df['timestamp'].min()}  -->  {sub_df['timestamp'].max()}")

print("\n" + "="*80 + "\n")
