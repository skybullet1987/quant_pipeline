import os, json, warnings
import pandas as pd
import numpy as np
from scipy.stats import multivariate_normal
from hmmlearn.hmm import GaussianHMM
from sklearn.preprocessing import RobustScaler
from catboost import CatBoostClassifier
from google.cloud import bigquery
from dotenv import load_dotenv

warnings.filterwarnings("ignore")
load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "parnasa-498503")
MODELS_DIR = "models/prod"
TOTAL_DAYS, OOS_DAYS, MAX_HOLD = 365, 30, 18
os.makedirs(MODELS_DIR, exist_ok=True)

LONG_TP, LONG_SL, LONG_MAE = 2.2, 1.1, 0.65
SHORT_TP, SHORT_SL, SHORT_MAE = 1.4, 0.9, 0.55

print("--> [1/4] Extracting resampled 4H table from BigQuery...")
client = bigquery.Client(project=PROJECT_ID)
query = f"""
    SELECT timestamp, ticker AS asset, open, high, low, close, volume, atr_20 AS atr, mom_24h, dist_ema20_atr, bbw_pct_40
    FROM `{PROJECT_ID}.market_data.fct_4h_features_production`
    ORDER BY timestamp ASC, ticker ASC
"""
df = client.query(query).to_dataframe()
df["timestamp"] = pd.to_datetime(df["timestamp"])
df["atr_pct"] = df["atr"] / (df["close"] + 1e-8)

unique_bars = sorted(df["timestamp"].unique())
cutoff_date = unique_bars[-1] - pd.Timedelta(days=OOS_DAYS)

# Online Causal HMM
df["ret_4h"] = df.groupby("asset")["close"].pct_change().fillna(0.0)
df["ema_20"] = df.groupby("asset")["close"].transform(lambda x: x.ewm(span=20, adjust=False).mean())
mbi_ts = df.groupby("timestamp").apply(lambda x: (x["close"] > x["ema_20"]).mean(), include_groups=False).rename("mbi")
csd_ts = df.groupby("timestamp")["ret_4h"].std().fillna(0.01).rename("csd")
macro_df = pd.concat([mbi_ts, csd_ts], axis=1).fillna(0.5)

macro_tr = macro_df[macro_df.index < cutoff_date][["mbi", "csd"]]
hmm_scaler = RobustScaler().fit(macro_tr)
hmm = GaussianHMM(n_components=3, covariance_type="full", random_state=42, n_iter=100).fit(hmm_scaler.transform(macro_tr))
canonical_order = np.argsort(-hmm.means_[:, 0])

X_all = hmm_scaler.transform(macro_df[["mbi", "csd"]])
T_len = len(X_all)
alpha = np.zeros((T_len, 3))
B = np.zeros((T_len, 3))
for j in range(3):
    B[:, j] = multivariate_normal.pdf(X_all, mean=hmm.means_[j], cov=hmm.covars_[j] + np.eye(2) * 1e-4)

alpha[0] = hmm.startprob_ * B[0]
alpha[0] /= np.sum(alpha[0]) + 1e-8
for t in range(1, T_len):
    alpha[t] = np.dot(alpha[t-1], hmm.transmat_) * B[t]
    alpha[t] /= np.sum(alpha[t]) + 1e-8

causal_posteriors = alpha[:, canonical_order]
macro_df["p_bull"] = causal_posteriors[:, 0]
macro_df["p_chop"] = causal_posteriors[:, 1]
macro_df["p_bear"] = causal_posteriors[:, 2]
macro_df["hmm_entropy"] = -np.sum(causal_posteriors * np.log(causal_posteriors + 1e-8), axis=1)
macro_df["dp_bull"] = macro_df["p_bull"].diff().fillna(0.0)
macro_df["dp_bear"] = macro_df["p_bear"].diff().fillna(0.0)

df = df.merge(macro_df[["p_bull", "p_chop", "p_bear", "hmm_entropy", "dp_bull", "dp_bear"]].reset_index(), on="timestamp", how="left")

print("--> [2/4] Generating exact Target Barrier labels on resampled 4H data...")
bar_map = {ts: df[df["timestamp"] == ts].set_index("asset").to_dict("index") for ts in unique_bars}
recs = []
for b_idx in range(len(unique_bars) - MAX_HOLD):
    ts = unique_bars[b_idx]
    for sym, r in bar_map[ts].items():
        px, atr = r["close"], r["atr"]
        if px <= 0 or atr <= 0: continue
        tp_l, sl_l = px + (LONG_TP * atr), px - (LONG_SL * atr)
        tp_s, sl_s = px - (SHORT_TP * atr), px + (SHORT_SL * atr)
        hit_tp_l, hit_sl_l, hit_tp_s, hit_sl_s = False, False, False, False
        max_mae_l, max_mae_s = 0.0, 0.0
        for f_idx in range(b_idx + 1, b_idx + 1 + MAX_HOLD):
            f_r = bar_map[unique_bars[f_idx]].get(sym)
            if not f_r: continue
            f_o, f_h, f_l = f_r["open"], f_r["high"], f_r["low"]
            max_mae_l = max(max_mae_l, (px - f_l) / atr)
            max_mae_s = max(max_mae_s, (f_h - px) / atr)
            if not hit_tp_l and not hit_sl_l:
                if f_h >= tp_l and f_l <= sl_l:
                    if abs(f_o - tp_l) <= abs(f_o - sl_l): hit_tp_l = True
                    else: hit_sl_l = True
                elif f_h >= tp_l: hit_tp_l = True
                elif f_l <= sl_l: hit_sl_l = True
            if not hit_tp_s and not hit_sl_s:
                if f_l <= tp_s and f_h >= sl_s:
                    if abs(f_o - tp_s) <= abs(f_o - sl_s): hit_tp_s = True
                    else: hit_sl_s = True
                elif f_l <= tp_s: hit_tp_s = True
                elif f_h >= sl_s: hit_sl_s = True
        recs.append({
            "timestamp": ts, "asset": sym,
            "target_long": int(hit_tp_l and max_mae_l <= LONG_MAE),
            "target_short": int(hit_tp_s and max_mae_s <= SHORT_MAE)
        })

df = df.merge(pd.DataFrame(recs), on=["timestamp", "asset"], how="inner")

feature_cols = [
    "p_bull", "p_chop", "p_bear", "hmm_entropy", "dp_bull", "dp_bear",
    "dist_ema20_atr", "bbw_pct_40", "mom_24h"
]
for c in feature_cols:
    df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

df_train = df[df["timestamp"] < cutoff_date].copy()
df_oos = df[df["timestamp"] >= cutoff_date].copy()

print(f"--> [3/4] Training CatBoost on {len(df_train):,} clean 4H bars...")
cb_long = CatBoostClassifier(iterations=400, depth=4, learning_rate=0.03, l2_leaf_reg=5.0, thread_count=-1, verbose=False, random_seed=42)
cb_short = CatBoostClassifier(iterations=400, depth=4, learning_rate=0.035, l2_leaf_reg=6.0, thread_count=-1, verbose=False, random_seed=42)

cb_long.fit(df_train[feature_cols], df_train["target_long"])
cb_short.fit(df_train[feature_cols], df_train["target_short"])

cb_long.save_model(f"{MODELS_DIR}/catboost_long_production.cbm")
cb_short.save_model(f"{MODELS_DIR}/catboost_short_production.cbm")

# Compute Decile 9 thresholds
df_train["p_l"] = cb_long.predict_proba(df_train[feature_cols])[:, 1]
df_train["p_s"] = cb_short.predict_proba(df_train[feature_cols])[:, 1]

q90_l = float(df_train["p_l"].quantile(0.90))
q85_s = float(df_train["p_s"].quantile(0.85))

print(f"--> [4/4] [✓] Retrained models locked. Calibrated Thresholds: Long Q90 = {q90_l:.3f} | Short Q85 = {q85_s:.3f}")

# Update config with retrained parameters
config_data = {
  "pipeline_version": "2.1.0-resampled",
  "feature_set": feature_cols,
  "portfolio_sizing": {
    "max_slots": 5,
    "weighting_method": "INV_ATR",
    "gross_leverage_cap": 1.5,
    "fee_bps_roundtrip": 10.0
  },
  "calibrated_thresholds": {
    "p_long_cutoff": round(q90_l, 3),
    "p_short_cutoff": round(q85_s, 3),
    "min_hmm_bull_prob": 0.70,
    "min_hmm_bear_prob": 0.45,
    "allow_longs": False  # Toggle asymmetric regime gating
  },
  "barrier_geometry": {
    "long_tp_mult": 2.2, "long_sl_mult": 1.1,
    "short_tp_mult": 1.4, "short_sl_mult": 0.9,
    "max_holding_bars": 18
  }
}

with open("config/execution_params.json", "w") as f:
    json.dump(config_data, f, indent=2)
print("--> Updated config/execution_params.json")
