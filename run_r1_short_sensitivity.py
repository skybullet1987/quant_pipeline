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
GLOBAL_RISK_CAP = 0.05  # Fixed 5.0% Global Open Risk Cap

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

print("[INFO] Fetching 90-day dataset from BigQuery for R1 Short Sensitivity Sweep...")
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

def run_r1_sensitivity_sim(r1_short_cap=0.05):
    capital = 1000.0
    peak_capital = capital
    max_dd = 0.0
    trades_executed = 0
    wins = 0
    r1_short_trades = 0
    r1_short_pnl = 0.0
    
    grouped = df_triggers.groupby('timestamp')
    
    for ts, group in grouped:
        current_timestamp_open_risk = 0.0
        current_r1_short_risk = 0.0
        
        for _, row in group.iterrows():
            coin = str(row['ticker']).replace("USDT", "").replace("USD", "").upper()
            entry_price, atr = float(row['close']), float(row['atr_20'])
            p_s = float(row['calibrated_prob_short'])
            regime = str(row['hmm_regime'])
            
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
            
            # Apply R1 Short Specific Risk Cap
            if regime == '1':
                if current_r1_short_risk + trade_risk_pct > r1_short_cap:
                    rem_r1 = max(0.0, r1_short_cap - current_r1_short_risk)
                    if rem_r1 <= 0.0005: continue
                    scale = rem_r1 / trade_risk_pct
                    trade_notional_pct *= scale
                    trade_risk_pct = rem_r1
            
            # Apply Global Risk Cap
            if current_timestamp_open_risk + trade_risk_pct > GLOBAL_RISK_CAP:
                rem_global = max(0.0, GLOBAL_RISK_CAP - current_timestamp_open_risk)
                if rem_global <= 0.0005: continue
                scale = rem_global / trade_risk_pct
                trade_notional_pct *= scale
                trade_risk_pct = rem_global

            current_timestamp_open_risk += trade_risk_pct
            if regime == '1': current_r1_short_risk += trade_risk_pct
            
            notional_size = min(capital * trade_notional_pct, HARD_LIQUIDITY_CAP)
            
            hit_target = bool(row['target_short'])
            pnl = notional_size * net_win if hit_target else -notional_size * net_loss
            
            capital += pnl
            trades_executed += 1
            if hit_target: wins += 1
            
            if regime == '1':
                r1_short_trades += 1
                r1_short_pnl += pnl

            if capital > peak_capital: peak_capital = capital
            dd = (peak_capital - capital) / peak_capital if peak_capital > 0 else 0
            if dd > max_dd: max_dd = dd

            if capital <= 10.0:
                capital = 0.0
                break
                
        if capital <= 0.0: break

    win_rate = (wins / trades_executed * 100.0) if trades_executed > 0 else 0.0
    cagr_proxy = (capital / 1000.0) ** (365.0 / 90.0) - 1.0 if capital > 0 else 0.0
    calmar = (cagr_proxy / max_dd) if max_dd > 0 else 0.0
    
    return capital, max_dd * 100.0, calmar, win_rate, trades_executed, r1_short_trades, r1_short_pnl

r1_caps = [0.05, 0.03, 0.02, 0.015, 0.01, 0.00]

print("\n" + "="*95)
print("🧪 R1 SHORT RISK SENSITIVITY SWEEP (GLOBAL CAP = 5.0%)")
print("="*95)
h1, h2, h3, h4, h5, h6, h7, h8 = "R1 Short Cap", "Final Equity ($1k)", "Max DD (%)", "Calmar", "Win Rate (%)", "Total Trades", "R1 Trades", "R1 Short P&L ($)"
print(f"{h1:<13} | {h2:<18} | {h3:<10} | {h4:<8} | {h5:<12} | {h6:<12} | {h7:<9} | {h8:<15}")
print("-" * 95)

for r1_cap in r1_caps:
    cap_label = f"{r1_cap*100:.1f}%" if r1_cap > 0 else "0.0% (Disabled)"
    eq, dd, calmar, wr, n_tot, n_r1, pnl_r1 = run_r1_sensitivity_sim(r1_cap)
    print(f"{cap_label:<13} | ${eq:>16,.2f} | {-dd:>9.2f}% | {calmar:>8.2f} | {wr:>11.2f}% | {n_tot:>12} | {n_r1:>9} | ${pnl_r1:>14,.2f}")

print("="*95 + "\n")
