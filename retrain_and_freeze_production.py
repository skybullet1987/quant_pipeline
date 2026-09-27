import os, joblib, warnings
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
TOTAL_DAYS, OOS_DAYS, MAX_HOLD_BARS = 365, 90, 18
os.makedirs(MODELS_DIR, exist_ok=True)

LONG_TP, LONG_SL, LONG_MAE = 2.2, 1.1, 0.65
SHORT_TP, SHORT_SL, SHORT_MAE = 1.4, 0.9, 0.55

print("--> [1/4] Extracting raw data from BigQuery...")
client = bigquery.Client(project=PROJECT_ID)
query = f"""
    SELECT f.*, COALESCE(l.rank_liq_intensity, 0) AS rank_liq_intensity
    FROM `{PROJECT_ID}.market_data.fct_4h_features_tbm` f
    LEFT JOIN `{PROJECT_ID}.market_data.fct_liquidation_features` l 
        ON f.timestamp = l.timestamp AND f.ticker = l.ticker
    WHERE f.timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {TOTAL_DAYS} DAY)
    ORDER BY f.timestamp ASC, f.ticker ASC
"""
df = client.query(query).to_dataframe()
df["timestamp"] = pd.to_datetime(df["timestamp"])
if "asset" not in df.columns and "ticker" in df.columns: df["asset"] = df["ticker"]
df = df.sort_values(["asset", "timestamp"]).reset_index(drop=True)

if "open" not in df.columns or df["open"].isnull().all():
    df["open"] = df.groupby("asset")["close"].shift(1).fillna(df["close"])

df["atr"] = df["atr_20"].fillna(df["close"] * 0.02) if "atr_20" in df.columns else df["close"] * 0.02
df["ema_20"] = df.groupby("asset")["close"].transform(lambda x: x.ewm(span=20, adjust=False).mean())
df["dist_ema20_atr"] = (df["close"] - df["ema_20"]) / (df["atr"] + 1e-8)

sma_20 = df.groupby("asset")["close"].transform(lambda x: x.rolling(20, min_periods=5).mean())
std_20 = df.groupby("asset")["close"].transform(lambda x: x.rolling(20, min_periods=5).std().fillna(0.0))
df["bbw"] = (4.0 * std_20) / (sma_20 + 1e-8)
roll_min = df.groupby("asset")["bbw"].transform(lambda x: x.rolling(40, min_periods=10).min())
roll_max = df.groupby("asset")["bbw"].transform(lambda x: x.rolling(40, min_periods=10).max())
df["bbw_pct_40"] = ((df["bbw"] - roll_min) / (roll_max - roll_min + 1e-8)).fillna(0.50).clip(0.0, 1.0)
df["mom_24h"] = df.groupby("asset")["close"].transform(lambda x: x.pct_change(6).fillna(0.0))

unique_bars = sorted(df["timestamp"].unique())
cutoff_date = unique_bars[-1] - pd.Timedelta(days=OOS_DAYS)

print("--> [2/4] Fitting Causal HMM & Generating Causal Online Posteriors...")
df["ret_4h"] = df.groupby("asset")["close"].pct_change().fillna(0.0)
mbi_ts = df.groupby("timestamp").apply(lambda x: (x["close"] > x["ema_20"]).mean(), include_groups=False).rename("mbi")
csd_ts = df.groupby("timestamp")["ret_4h"].std().fillna(0.01).rename("csd")
macro_df = pd.concat([mbi_ts, csd_ts], axis=1).fillna(0.5)

macro_tr = macro_df[macro_df.index < cutoff_date][["mbi", "csd"]]
hmm_scaler = RobustScaler().fit(macro_tr)
X_tr_scaled = hmm_scaler.transform(macro_tr)

hmm = GaussianHMM(n_components=3, covariance_type="full", random_state=42, n_iter=100).fit(X_tr_scaled)
canonical_order = np.argsort(-hmm.means_[:, 0])

# Save production HMM artifacts
joblib.dump(hmm, f"{MODELS_DIR}/hmm_macro.pkl")
joblib.dump(hmm_scaler, f"{MODELS_DIR}/hmm_scaler.pkl")
joblib.dump(canonical_order, f"{MODELS_DIR}/hmm_canonical_order.pkl")

# Causal online forward pass
X_all_scaled = hmm_scaler.transform(macro_df[["mbi", "csd"]])
T_len = len(X_all_scaled)
alpha = np.zeros((T_len, 3))
B = np.zeros((T_len, 3))
for j in range(3):
    B[:, j] = multivariate_normal.pdf(X_all_scaled, mean=hmm.means_[j], cov=hmm.covars_[j] + np.eye(2) * 1e-4)

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

print("--> [3/4] Label Generation & Training Production CatBoost Models...")
bar_map = {ts: df[df["timestamp"] == ts].set_index("asset").to_dict("index") for ts in unique_bars}
recs = []
for b_idx in range(len(unique_bars) - MAX_HOLD_BARS):
    ts = unique_bars[b_idx]
    for sym, r in bar_map[ts].items():
        px, atr = r["close"], r["atr"]
        if px <= 0 or atr <= 0: continue
        tp_l, sl_l = px + (LONG_TP * atr), px - (LONG_SL * atr)
        tp_s, sl_s = px - (SHORT_TP * atr), px + (SHORT_SL * atr)
        hit_tp_l, hit_sl_l, hit_tp_s, hit_sl_s = False, False, False, False
        max_mae_l, max_mae_s = 0.0, 0.0
        for f_idx in range(b_idx + 1, b_idx + 1 + MAX_HOLD_BARS):
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

final_feature_set = [
    "p_bull", "p_chop", "p_bear", "hmm_entropy", "dp_bull", "dp_bear",
    "dist_ema20_atr", "bbw_pct_40", "mom_24h"
]
joblib.dump(final_feature_set, f"{MODELS_DIR}/production_feature_names.pkl")

for c in final_feature_set:
    df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

df_train = df[df["timestamp"] < cutoff_date].copy()
df_oos = df[df["timestamp"] >= cutoff_date].copy()

# Fit Production Models on In-Sample
cb_long = CatBoostClassifier(iterations=550, depth=5, learning_rate=0.03, l2_leaf_reg=4.0, subsample=0.85, verbose=False, random_seed=42)
cb_short = CatBoostClassifier(iterations=550, depth=5, learning_rate=0.03, l2_leaf_reg=4.0, subsample=0.85, verbose=False, random_seed=42)

cb_long.fit(df_train[final_feature_set], df_train["target_long"])
cb_short.fit(df_train[final_feature_set], df_train["target_short"])

cb_long.save_model(f"{MODELS_DIR}/catboost_long_production.cbm")
cb_short.save_model(f"{MODELS_DIR}/catboost_short_production.cbm")
print("--> [✓] Production models saved to models/prod/")

print("\n" + "=" * 115)
print("     [4/4] OUT-OF-SAMPLE DECILE CALIBRATION & EXPECTANCY AUDIT     ")
print("=" * 115)

df_oos["p_model_long"] = cb_long.predict_proba(df_oos[final_feature_set])[:, 1]
df_oos["p_model_short"] = cb_short.predict_proba(df_oos[final_feature_set])[:, 1]
df_oos["fwd_ret_8b"] = df_oos.groupby("asset")["close"].shift(-8) / df_oos["close"] - 1.0
df_oos_clean = df_oos.dropna(subset=["fwd_ret_8b"]).copy()

df_oos_clean["decile_long"] = pd.qcut(df_oos_clean["p_model_long"], q=10, labels=False, duplicates="drop")
df_oos_clean["decile_short"] = pd.qcut(df_oos_clean["p_model_short"], q=10, labels=False, duplicates="drop")

long_calib = df_oos_clean.groupby("decile_long").agg(
    P_Min=("p_model_long", "min"),
    P_Max=("p_model_long", "max"),
    WinRate=("target_long", lambda x: f"{x.mean()*100:.1f}%"),
    EV_bps=("fwd_ret_8b", lambda x: f"{x.mean()*10000:>+6.1f} bps"),
    Count=("fwd_ret_8b", "count")
)

short_calib = df_oos_clean.groupby("decile_short").agg(
    P_Min=("p_model_short", "min"),
    P_Max=("p_model_short", "max"),
    WinRate=("target_short", lambda x: f"{x.mean()*100:.1f}%"),
    EV_bps=("fwd_ret_8b", lambda x: f"{-x.mean()*10000:>+6.1f} bps"),
    Count=("fwd_ret_8b", "count")
)

print("\n[LONG PRODUCTION MODEL: OOS CALIBRATION BY PREDICTED DECILE]")
print(long_calib.to_string())

print("\n[SHORT PRODUCTION MODEL: OOS CALIBRATION BY PREDICTED DECILE]")
print(short_calib.to_string())
print("=" * 115)
