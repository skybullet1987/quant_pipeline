import os, sys, json, argparse, warnings
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

parser = argparse.ArgumentParser()
parser.add_argument("--dry-run", action="store_true", default=True, help="Simulate execution without submitting live orders")
args = parser.parse_args()

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "parnasa-498503")
CONFIG_PATH = "config/execution_params.json"
MODELS_DIR = "models/prod"

with open(CONFIG_PATH, "r") as f:
    config = json.load(f)

print("=" * 110)
print(f"--> [1/4] Loading 4H Features from BigQuery (Mode: {'DRY RUN' if args.dry_run else 'LIVE TRADING'})")
print("=" * 110)

client = bigquery.Client(project=PROJECT_ID)
query = f"""
    SELECT timestamp, ticker AS asset, open, high, low, close, volume, atr_20 AS atr, mom_24h, dist_ema20_atr, bbw_pct_40
    FROM `{PROJECT_ID}.market_data.fct_4h_features_production`
    WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 60 DAY)
    ORDER BY timestamp ASC, ticker ASC
"""
df = client.query(query).to_dataframe()
df["timestamp"] = pd.to_datetime(df["timestamp"])
df["atr_pct"] = df["atr"] / (df["close"] + 1e-8)

# Online Causal HMM Forward Pass
df["ret_4h"] = df.groupby("asset")["close"].pct_change().fillna(0.0)
df["ema_20"] = df.groupby("asset")["close"].transform(lambda x: x.ewm(span=20, adjust=False).mean())
mbi_ts = df.groupby("timestamp").apply(lambda x: (x["close"] > x["ema_20"]).mean(), include_groups=False).rename("mbi")
csd_ts = df.groupby("timestamp")["ret_4h"].std().fillna(0.01).rename("csd")
macro_df = pd.concat([mbi_ts, csd_ts], axis=1).fillna(0.5)

hmm_scaler = RobustScaler().fit(macro_df[["mbi", "csd"]])
hmm = GaussianHMM(n_components=3, covariance_type="full", random_state=42, n_iter=100).fit(hmm_scaler.transform(macro_df[["mbi", "csd"]]))
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

# Score Latest Bar
latest_ts = df["timestamp"].max()
current_bar = df[df["timestamp"] == latest_ts].copy()

feature_cols = config["feature_set"]
cb_long = CatBoostClassifier().load_model(f"{MODELS_DIR}/catboost_long_production.cbm")
cb_short = CatBoostClassifier().load_model(f"{MODELS_DIR}/catboost_short_production.cbm")

current_bar["p_model_long"] = cb_long.predict_proba(current_bar[feature_cols])[:, 1]
current_bar["p_model_short"] = cb_short.predict_proba(current_bar[feature_cols])[:, 1]

p_bull = current_bar["p_bull"].iloc[0]
p_bear = current_bar["p_bear"].iloc[0]
p_chop = current_bar["p_chop"].iloc[0]

print(f"--> [2/4] Scored {len(current_bar)} Assets for Bar: {latest_ts} UTC")
print(f"    Macro Dynamics: Bull = {p_bull*100:.1f}% | Bear = {p_bear*100:.1f}% | Chop = {p_chop*100:.1f}%")

# Filter Qualified Assets
p_long_cut = config["calibrated_thresholds"]["p_long_cutoff"]
p_short_cut = config["calibrated_thresholds"]["p_short_cutoff"]
min_bull = config["calibrated_thresholds"]["min_hmm_bull_prob"]
min_bear = config["calibrated_thresholds"]["min_hmm_bear_prob"]
max_slots = config["portfolio_sizing"]["max_slots"]

long_cands = current_bar[(current_bar["p_model_long"] >= p_long_cut) & (p_bull >= min_bull)].sort_values(by="p_model_long", ascending=False)
short_cands = current_bar[(current_bar["p_model_short"] >= p_short_cut) & (p_bear >= min_bear)].sort_values(by="p_model_short", ascending=False)

print(f"--> [3/4] Signals: {len(long_cands)} Longs (P >= {p_long_cut}) | {len(short_cands)} Shorts (P >= {p_short_cut})")

selected_cands = []
active_direction = "FLAT"

if len(short_cands) >= len(long_cands) and not short_cands.empty:
    active_direction = "SHORT"
    selected_cands = short_cands.head(max_slots)
elif not long_cands.empty:
    active_direction = "LONG"
    selected_cands = long_cands.head(max_slots)

print("\n" + "=" * 110)
print(f"     [4/4] LIVE TARGET BARRIER ORDER ROUTING (DIRECTION: {active_direction})     ")
print("=" * 110)

if selected_cands.empty or active_direction == "FLAT":
    print("--> ZERO ASSETS MET STRICT THRESHOLDS. 100% CAPITAL PRESERVATION / FLAT.")
else:
    inv_atrs = 1.0 / selected_cands["atr_pct"].clip(lower=0.005)
    weights = inv_atrs / inv_atrs.sum()
    
    order_plan = []
    for idx, (_, row) in enumerate(selected_cands.iterrows()):
        sym = row["asset"]
        px = row["close"]
        atr = row["atr"]
        w = weights.iloc[idx]
        
        if active_direction == "LONG":
            tp = px + (config["barrier_geometry"]["long_tp_mult"] * atr)
            sl = px - (config["barrier_geometry"]["long_sl_mult"] * atr)
            p_conv = row["p_model_long"]
        else:
            tp = px - (config["barrier_geometry"]["short_tp_mult"] * atr)
            sl = px + (config["barrier_geometry"]["short_sl_mult"] * atr)
            p_conv = row["p_model_short"]

        order_plan.append({
            "Symbol": sym,
            "Direction": active_direction,
            "Conviction": f"{p_conv*100:.1f}%",
            "Weight": f"{w*100:.1f}%",
            "Current Price": f"${px:,.4f}",
            "Take Profit": f"${tp:,.4f}",
            "Stop Loss": f"${sl:,.4f}"
        })

    print(pd.DataFrame(order_plan).to_string(index=False))

print("=" * 110)
