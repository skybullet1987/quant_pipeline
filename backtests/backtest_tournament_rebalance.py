import os, sys, warnings
PROJECT_ROOT = os.path.abspath(os.getenv("QUANT_PROJECT_ROOT", "/home/skybullet1987/quant_pipeline"))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import numpy as np
import pandas as pd
from scipy.stats import multivariate_normal
from hmmlearn.hmm import GaussianHMM
from sklearn.preprocessing import RobustScaler
from catboost import CatBoostClassifier
from google.cloud import bigquery
from dotenv import load_dotenv

warnings.filterwarnings("ignore")
load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "parnasa-498503")
MODELS_DIR = os.path.join(PROJECT_ROOT, "models/prod")

print("--> [1/3] Extracting feature dataset from BigQuery...")
client = bigquery.Client(project=PROJECT_ID)
query = f"""
    SELECT timestamp, ticker AS asset, open, high, low, close, volume,
           atr_20 AS atr, mom_24h, dist_ema20_atr, bbw_pct_40
    FROM `{PROJECT_ID}.market_data.fct_4h_features_production`
    ORDER BY timestamp ASC, ticker ASC
"""
df = client.query(query).to_dataframe()
df["timestamp"] = pd.to_datetime(df["timestamp"])
df["ret_4h"] = df.groupby("asset")["close"].pct_change().fillna(0.0)

# Causal Macro Features
df["ema_20"] = df.groupby("asset")["close"].transform(lambda x: x.ewm(span=20, adjust=False).mean())
mbi_ts = df.groupby("timestamp").apply(lambda x: (x["close"] > x["ema_20"]).mean(), include_groups=False).rename("mbi")
csd_ts = df.groupby("timestamp")["ret_4h"].std().fillna(0.01).rename("csd")
macro_df = pd.concat([mbi_ts, csd_ts], axis=1).fillna(0.5)

hmm_scaler = RobustScaler().fit(macro_df[["mbi", "csd"]])
X_all = hmm_scaler.transform(macro_df[["mbi", "csd"]])
hmm = GaussianHMM(n_components=3, covariance_type="diag", min_covar=1e-3, random_state=42, n_iter=200).fit(X_all)

mbi_means = hmm.means_[:, 0]
bull_idx = int(np.argmax(mbi_means))
bear_idx = int(np.argmin(mbi_means))
chop_idx = int([i for i in range(3) if i not in (bull_idx, bear_idx)][0])
canonical_order = [bull_idx, chop_idx, bear_idx]

T_len = len(X_all)
alpha = np.zeros((T_len, 3))
B = np.zeros((T_len, 3))
for j in range(3):
    B[:, j] = multivariate_normal.pdf(X_all, mean=hmm.means_[j], cov=np.diag(hmm.covars_[j]) + np.eye(2) * 1e-4)

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

# CatBoost Alpha Scoring
print("--> [2/3] Scoring CatBoost models...")
cb_long = CatBoostClassifier().load_model(f"{MODELS_DIR}/catboost_long_production.cbm")
cb_short = CatBoostClassifier().load_model(f"{MODELS_DIR}/catboost_short_production.cbm")
feature_cols = ["p_bull", "p_chop", "p_bear", "hmm_entropy", "dp_bull", "dp_bear", "dist_ema20_atr", "bbw_pct_40", "mom_24h"]

for c in feature_cols:
    df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

df["p_long"] = cb_long.predict_proba(df[feature_cols])[:, 1]
df["p_short"] = cb_short.predict_proba(df[feature_cols])[:, 1]

# 3. Dynamic Alpha Rebalancing Simulation
print("--> [3/3] Simulating Tournament Cross-Sectional Alpha Compounding...")
timestamps = sorted(df["timestamp"].unique())
pivot_rets = df.pivot(index="timestamp", columns="asset", values="ret_4h").fillna(0.0)

initial_capital = 500.00
equity = initial_capital
equity_curve = [equity]
trades = []

taker_fee = 0.00035
slippage = 0.00020
friction_rate = (taker_fee + slippage) * 2

GROSS_LEVERAGE = 4.0
TOP_K = 2  # Top 2 alpha assets per bar

current_weights = {}

for t_idx, ts in enumerate(timestamps[:-1]):
    next_ts = timestamps[t_idx + 1]
    bar_df = df[df["timestamp"] == ts].set_index("asset")
    next_bar_rets = pivot_rets.loc[next_ts]

    p_bull = float(bar_df["p_bull"].iloc[0])
    p_bear = float(bar_df["p_bear"].iloc[0])

    target_weights = {}

    # BULL EXPANSION -> Allocate to Top K Longs
    if p_bull >= 0.60:
        top_longs = bar_df.sort_values(by="p_long", ascending=False).head(TOP_K)
        for sym in top_longs.index:
            target_weights[sym] = (GROSS_LEVERAGE / TOP_K)

    # BEAR BREAKDOWN -> Allocate to Top K Shorts
    elif p_bear >= 0.45:
        top_shorts = bar_df.sort_values(by="p_short", ascending=False).head(TOP_K)
        for sym in top_shorts.index:
            target_weights[sym] = -(GROSS_LEVERAGE / TOP_K)

    # Calculate Turnover & Fee Friction
    all_syms = set(current_weights.keys()).union(target_weights.keys())
    turnover = sum(abs(target_weights.get(s, 0.0) - current_weights.get(s, 0.0)) for s in all_syms)
    fee_cost = equity * turnover * (taker_fee + slippage)

    # Compute Period PnL
    bar_pnl = 0.0
    for sym, weight in target_weights.items():
        if sym in next_bar_rets:
            r = next_bar_rets[sym]
            bar_pnl += equity * weight * r

    net_bar_pnl = bar_pnl - fee_cost
    equity += net_bar_pnl
    equity_curve.append(equity)
    current_weights = target_weights

# Performance Summary
eq_series = pd.Series(equity_curve)
peak = eq_series.cummax()
dd = (eq_series - peak) / peak

total_pnl = equity - initial_capital
total_ret = (total_pnl / initial_capital) * 100
max_dd = abs(dd.min()) * 100
sharpe = (eq_series.pct_change().mean() / (eq_series.pct_change().std() + 1e-8)) * np.sqrt(365 * 6)

print("\n" + "="*55)
print("     TOURNAMENT DYNAMIC-ALPHA PERFORMANCE (90D)")
print("="*55)
print(f"Starting Capital       : ${initial_capital:,.2f}")
print(f"Ending Equity          : ${equity:,.2f}")
print(f"Net Profit             : ${total_pnl:+,.2f} ({total_ret:+.2f}%)")
print(f"Sharpe Ratio (4H Ann.) : {sharpe:.2f}")
print(f"Maximum Drawdown (MDD) : {max_dd:.2f}%")
print("="*55)
