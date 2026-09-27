import os
import joblib
import pandas as pd
import numpy as np
from google.cloud import bigquery
from catboost import CatBoostClassifier, Pool
from dotenv import load_dotenv

load_dotenv()
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "parnasa-498503")

client = bigquery.Client(project=PROJECT_ID)
query = f"""
    SELECT f.*, 
        COALESCE(t.tfm_ret_24h, 0.0) AS tfm_ret_24h, 
        COALESCE(t.tfm_ret_72h, 0.0) AS tfm_ret_72h, 
        COALESCE(t.tfm_slope, 0.0) AS tfm_slope, 
        COALESCE(t.tfm_uncertainty, 0.0) AS tfm_uncertainty, 
        COALESCE(t.tfm_residual_24h, 0.0) AS tfm_residual_24h, 
        COALESCE(t.tfm_conviction_delta, 0.0) AS tfm_conviction_delta,
        COALESCE(l.total_liq_usd, 0) AS total_liq_usd,
        COALESCE(l.liq_imbalance_ratio, 0) AS liq_imbalance_ratio,
        COALESCE(l.long_liq_accel, 0) AS long_liq_accel,
        COALESCE(l.short_liq_accel, 0) AS short_liq_accel,
        COALESCE(l.rank_liq_intensity, 0) AS rank_liq_intensity
    FROM `{PROJECT_ID}.market_data.fct_4h_features_tbm` f
    LEFT JOIN `{PROJECT_ID}.market_data.fct_timesfm_features` t ON f.timestamp = t.timestamp AND f.ticker = t.ticker
    LEFT JOIN `{PROJECT_ID}.market_data.fct_liquidation_features` l ON f.timestamp = l.timestamp AND f.ticker = l.ticker
    WHERE f.timestamp = (SELECT MAX(timestamp) FROM `{PROJECT_ID}.market_data.fct_4h_features_tbm`)
"""
df = client.query(query).to_dataframe()
print(f"Fetched {len(df)} candidate rows for bar {df['timestamp'].iloc[0] if not df.empty else 'N/A'}")

cb_l1 = CatBoostClassifier().load_model("models/prod/regime_1_long_expert.cbm")
cb_s2 = CatBoostClassifier().load_model("models/prod/regime_2_short_expert.cbm")

feats_l = cb_l1.feature_names_
feats_s = cb_s2.feature_names_

all_cat_cols = joblib.load("models/prod/cat_cols.pkl") if os.path.exists("models/prod/cat_cols.pkl") else []
cat_set = set(all_cat_cols)

for c in set(feats_l + feats_s):
    if c not in df.columns:
        df[c] = "missing" if c in cat_set else 0.0
    elif c in cat_set:
        df[c] = df[c].astype(str).fillna("missing")
    else:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

pool_l = Pool(df[feats_l], cat_features=[c for c in feats_l if c in cat_set])
pool_s = Pool(df[feats_s], cat_features=[c for c in feats_s if c in cat_set])

raw_pl = cb_l1.predict_proba(pool_l)[:, 1]
raw_ps = cb_s2.predict_proba(pool_s)[:, 1]

print("\n--- RAW CATBOOST PREDICTIONS ---")
print(f"Long  (R1 Expert) - Min: {raw_pl.min():.4f}, Mean: {raw_pl.mean():.4f}, Max: {raw_pl.max():.4f}")
print(f"Short (R2 Expert) - Min: {raw_ps.min():.4f}, Mean: {raw_ps.mean():.4f}, Max: {raw_ps.max():.4f}")

if os.path.exists("models/prod/meta_calibrator_short.pkl"):
    cal_s = joblib.load("models/prod/meta_calibrator_short.pkl")
    cal_ps = cal_s.predict(raw_ps)
    print(f"Calibrated Short  - Min: {cal_ps.min():.4f}, Mean: {cal_ps.mean():.4f}, Max: {cal_ps.max():.4f}")

sample = df[['ticker']].copy()
sample['raw_pl'] = np.round(raw_pl, 4)
sample['raw_ps'] = np.round(raw_ps, 4)
print("\nSample Predictions (Top 8):")
print(sample.head(8).to_string(index=False))
