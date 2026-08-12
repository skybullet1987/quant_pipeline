import os, joblib, warnings
import pandas as pd
import numpy as np
from google.cloud import bigquery
from catboost import CatBoostClassifier

warnings.filterwarnings("ignore")
PROJECT_ID = "parnasa-498503"
MODEL_DIR = "/home/skybullet1987/quant_pipeline/production_models"

ENTRY_THRESHOLD_SHORT = 0.52
ENTRY_THRESHOLD_LONG = 0.58

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

print("[INFO] Fetching 90-day dataset from BigQuery for Regime Expectancy Matrix...")
client = bigquery.Client(project=PROJECT_ID)
query = f"""
    SELECT 
        f.*, 
        p.target_short, p.target_long, p.minutes_in_trade
    FROM `{PROJECT_ID}.market_data.fct_4h_features_tbm` f
    INNER JOIN `{PROJECT_ID}.market_data.fct_exact_path_resolution` p
        ON f.ticker = p.ticker AND f.timestamp = p.signal_time
    ORDER BY f.timestamp ASC
"""
df = client.query(query).to_dataframe(create_bqstorage_client=True)
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Load models
hmm_model, hmm_scaler = joblib.load(f"{MODEL_DIR}/hmm_macro.pkl"), joblib.load(f"{MODEL_DIR}/hmm_scaler.pkl")
hmm_features, canonical_order = joblib.load(f"{MODEL_DIR}/hmm_feature_names.pkl"), joblib.load(f"{MODEL_DIR}/hmm_canonical_order.pkl")
meta_short, cal_short = CatBoostClassifier().load_model(f"{MODEL_DIR}/meta_labeler_short.cbm"), joblib.load(f"{MODEL_DIR}/meta_calibrator_short.pkl")
meta_long, cal_long = CatBoostClassifier().load_model(f"{MODEL_DIR}/meta_labeler_long.cbm"), joblib.load(f"{MODEL_DIR}/meta_calibrator_long.pkl")
all_cat_cols, all_features = joblib.load(f"{MODEL_DIR}/cat_cols.pkl"), joblib.load(f"{MODEL_DIR}/feature_names.pkl")

for col in all_features:
    if col not in df.columns: df[col] = 0.0
for col in hmm_features:
    if col not in df.columns: df[col] = 0.0
df = df.fillna(0)

# Score HMM
scaled_x = hmm_scaler.transform(df[hmm_features].fillna(0))
can_probs = hmm_model.predict_proba(scaled_x)[:, canonical_order]
df['hmm_p_chop'], df['hmm_regime'] = can_probs[:, 0], can_probs.argmax(axis=1).astype(str)
for col in all_cat_cols: df[col] = df[col].astype(str)

# Score Short & Long Experts
df['primary_prob_short'] = 0.0
df['primary_prob_long'] = 0.0

for regime in ['0', '1', '2']:
    m_s_path = f"{MODEL_DIR}/regime_{regime}_short_expert.cbm"
    m_l_path = f"{MODEL_DIR}/regime_{regime}_long_expert.cbm"
    idx = df[df['hmm_regime'] == regime].index
    if len(idx) > 0:
        if os.path.exists(m_s_path):
            df.loc[idx, 'primary_prob_short'] = CatBoostClassifier().load_model(m_s_path).predict_proba(df.loc[idx, all_features])[:, 1]
        if os.path.exists(m_l_path):
            df.loc[idx, 'primary_prob_long'] = CatBoostClassifier().load_model(m_l_path).predict_proba(df.loc[idx, all_features])[:, 1]

df['calibrated_prob_short'] = cal_short.predict(meta_short.predict_proba(df[meta_short.feature_names_])[:, 1])
df['calibrated_prob_long'] = cal_long.predict(meta_long.predict_proba(df[meta_long.feature_names_])[:, 1])

# Evaluate expectations for both directions
matrix_records = []

for _, row in df.iterrows():
    coin = str(row['ticker']).replace("USDT", "").replace("USD", "").upper()
    entry_price, atr = float(row['close']), float(row['atr_20'])
    if entry_price <= 0 or atr <= 0: continue
    
    c_entry, c_tp, c_sl = get_tier_frictions(coin)
    r_dist = (1.50 * atr) / entry_price
    net_win = r_dist - c_entry - c_tp
    net_loss = r_dist + c_entry + c_sl
    
    # Check Short Trigger
    p_s = float(row['calibrated_prob_short'])
    ev_s = (p_s * net_win) - ((1.0 - p_s) * net_loss)
    if row['hmm_p_chop'] < 0.50 and row['hmm_regime'] != '0' and p_s >= ENTRY_THRESHOLD_SHORT and ev_s > 0:
        hit_s = bool(row['target_short'])
        r_pnl = (net_win / net_loss) if hit_s else -1.0
        matrix_records.append({
            'direction': 'SHORT', 'regime': str(row['hmm_regime']),
            'win': hit_s, 'r_pnl': r_pnl, 'prob': p_s
        })

    # Check Long Trigger
    p_l = float(row['calibrated_prob_long'])
    ev_l = (p_l * net_win) - ((1.0 - p_l) * net_loss)
    if row['hmm_p_chop'] < 0.50 and row['hmm_regime'] != '2' and p_l >= ENTRY_THRESHOLD_LONG and ev_l > 0:
        hit_l = bool(row['target_long'])
        r_pnl = (net_win / net_loss) if hit_l else -1.0
        matrix_records.append({
            'direction': 'LONG', 'regime': str(row['hmm_regime']),
            'win': hit_l, 'r_pnl': r_pnl, 'prob': p_l
        })

res_df = pd.DataFrame(matrix_records)

print("\n" + "="*80)
print("📊 DIRECTIONAL EXPECTANCY MATRIX BY HMM REGIME (LONG vs SHORT)")
print("="*80)
h1, h2, h3, h4, h5 = "Direction / Regime", "Total Signals", "Win Rate (%)", "Avg Expectancy (R)", "Sum R-PnL"
print(f"{h1:<22} | {h2:<15} | {h3:<14} | {h4:<20} | {h5:<10}")
print("-" * 80)

for reg in ['0', '1', '2']:
    for dir_label in ['LONG', 'SHORT']:
        sub = res_df[(res_df['direction'] == dir_label) & (res_df['regime'] == reg)]
        if not sub.empty:
            count = len(sub)
            wr = sub['win'].mean() * 100.0
            avg_r = sub['r_pnl'].mean()
            sum_r = sub['r_pnl'].sum()
            label = f"{dir_label} (Regime {reg})"
            print(f"{label:<22} | {count:>15} | {wr:>13.2f}% | {avg_r:>19.4f}R | {sum_r:>9.2f}R")
        else:
            label = f"{dir_label} (Regime {reg})"
            print(f"{label:<22} | {'0':>15} | {'N/A':>14} | {'N/A':>20} | {'0.00':>9}R")

print("="*80 + "\n")
