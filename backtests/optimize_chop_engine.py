import os, sys, warnings
PROJECT_ROOT = os.path.abspath(os.getenv("QUANT_PROJECT_ROOT", "/home/skybullet1987/quant_pipeline"))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import numpy as np
import pandas as pd
import optuna
from scipy.stats import multivariate_normal
from hmmlearn.hmm import GaussianHMM
from sklearn.preprocessing import RobustScaler
from google.cloud import bigquery
from dotenv import load_dotenv

warnings.filterwarnings("ignore")
optuna.logging.set_verbosity(optuna.logging.WARNING)
load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "parnasa-498503")

print("--> [1/2] Loading 90D feature data and estimating HMM...")
client = bigquery.Client(project=PROJECT_ID)
query = f"""
    SELECT timestamp, ticker AS asset, close
    FROM `{PROJECT_ID}.market_data.fct_4h_features_production`
    ORDER BY timestamp ASC, ticker ASC
"""
df = client.query(query).to_dataframe()
df["timestamp"] = pd.to_datetime(df["timestamp"])
df["ret_4h"] = df.groupby("asset")["close"].pct_change().fillna(0.0)

# Estimate HMM posteriors
df["ema_20"] = df.groupby("asset")["close"].transform(lambda x: x.ewm(span=20, adjust=False).mean())
mbi_ts = df.groupby("timestamp").apply(lambda x: (x["close"] > x["ema_20"]).mean(), include_groups=False).rename("mbi")
csd_ts = df.groupby("timestamp")["ret_4h"].std().fillna(0.01).rename("csd")
macro_df = pd.concat([mbi_ts, csd_ts], axis=1).fillna(0.5)

hmm_scaler = RobustScaler().fit(macro_df[["mbi", "csd"]])
X_all = hmm_scaler.transform(macro_df[["mbi", "csd"]])
hmm = GaussianHMM(n_components=3, covariance_type="diag", min_covar=1e-3, random_state=42, n_iter=200).fit(X_all)
canonical_order = np.argsort(-hmm.means_[:, 0])

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
macro_df["p_chop"] = causal_posteriors[:, 1]
df = df.merge(macro_df[["p_chop"]].reset_index(), on="timestamp", how="left")

pivot_rets = df.pivot(index="timestamp", columns="asset", values="ret_4h").fillna(0.0)
timestamps = sorted(df["timestamp"].unique())
btc_col = next((c for c in pivot_rets.columns if c in ("BTC", "kBTC", "BTC-PERP")), pivot_rets.columns[0])
eth_col = next((c for c in pivot_rets.columns if c in ("ETH", "kETH", "ETH-PERP")), pivot_rets.columns[1])
assets = [c for c in pivot_rets.columns if c not in (btc_col, eth_col)]

taker_fee = 0.00035
slippage = 0.00020
friction_per_leg = (taker_fee + slippage) * 2

print("--> [2/2] Running Optuna Bayesian Search (100 Trials)...")

def objective(trial):
    lookback = trial.suggest_int("lookback", 60, 240, step=30)
    horizon = trial.suggest_int("horizon", 3, 15, step=3)
    min_spread = trial.suggest_float("min_spread", 1.5, 3.5, step=0.25)
    hold_bars = trial.suggest_int("hold_bars", 6, 24, step=3)
    gross_lev = trial.suggest_float("gross_leverage", 1.5, 3.5, step=0.5)

    equity = 575.45
    pnl_history = []
    active_basket = None
    entry_bar = 0

    for t_idx, ts in enumerate(timestamps):
        p_chop = float(df[df["timestamp"] == ts]["p_chop"].iloc[0])
        bar_rets = pivot_rets.iloc[t_idx]

        # Exit / Rebalance
        if active_basket is not None:
            if (t_idx - entry_bar) >= hold_bars or p_chop < 0.50:
                basket_ret = 0.0
                for sym, w in active_basket["weights"].items():
                    # Cumulative price change over holding duration
                    entry_px = active_basket["entries"][sym]
                    curr_px = df[(df["timestamp"] == ts) & (df["asset"] == sym)]["close"].iloc[0]
                    r = (curr_px - entry_px) / entry_px
                    basket_ret += (w * r) - (abs(w) * friction_per_leg)

                pnl = equity * basket_ret
                equity += pnl
                pnl_history.append(pnl)
                active_basket = None

        # Entry
        if p_chop >= 0.70 and active_basket is None and t_idx >= lookback:
            sub_rets = pivot_rets.iloc[t_idx - lookback + 1 : t_idx + 1]
            r_market = sub_rets[[btc_col, eth_col]].values
            X = np.column_stack([np.ones(lookback), r_market])
            X_t = X.T

            try:
                beta_hat_inv = np.linalg.pinv(X_t @ X) @ X_t
            except Exception:
                continue

            records = []
            dof = lookback - 3
            for a in assets:
                y = sub_rets[a].values
                params = beta_hat_inv @ y
                res = y - (X @ params)
                sigma_eps = np.sqrt(np.sum(res**2) / dof)
                cum_res = np.sum(res[-horizon:])
                res_mom = cum_res / (sigma_eps * np.sqrt(horizon) + 1e-8)
                records.append((a, res_mom, sigma_eps))

            records.sort(key=lambda x: x[1], reverse=True)
            spread = records[0][1] - records[-1][1]

            if spread >= min_spread:
                top2 = records[:2]
                bot2 = records[-2:]

                long_inv = [1.0 / (x[2] + 1e-8) for x in top2]
                short_inv = [1.0 / (x[2] + 1e-8) for x in bot2]

                weights = {}
                for i, (sym, _, _) in enumerate(top2):
                    weights[sym] = (long_inv[i] / sum(long_inv)) * (gross_lev / 2.0)
                for i, (sym, _, _) in enumerate(bot2):
                    weights[sym] = -(short_inv[i] / sum(short_inv)) * (gross_lev / 2.0)

                current_bar_df = df[df["timestamp"] == ts].set_index("asset")
                entries = {s: float(current_bar_df.loc[s]["close"]) for s in weights.keys() if s in current_bar_df.index}

                if len(entries) == 4:
                    active_basket = {"weights": weights, "entries": entries}
                    entry_bar = t_idx

    if len(pnl_history) < 5:
        return -999.0

    pnl_arr = np.array(pnl_history)
    sharpe = (pnl_arr.mean() / (pnl_arr.std() + 1e-8)) * np.sqrt(len(pnl_arr))
    net_return = (equity - 575.45) / 575.45

    # Penalize negative net returns and reward stability
    return sharpe if net_return > 0 else -10.0 + net_return

study = optuna.create_study(direction="maximize")
study.optimize(objective, n_trials=100)

print("\n" + "="*50)
print("     OPTUNA OPTIMIZATION COMPLETE")
print("="*50)
print(f"Best Objective Score (Sharpe) : {study.best_value:.3f}")
print("Optimal Chop Engine Parameters:")
for k, v in study.best_params.items():
    print(f"  --> {k:<20} : {v}")
print("="*50)
