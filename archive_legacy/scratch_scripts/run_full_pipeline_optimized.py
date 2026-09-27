import os, json, warnings
import pandas as pd
import numpy as np
import optuna
from scipy.stats import multivariate_normal
from hmmlearn.hmm import GaussianHMM
from sklearn.preprocessing import RobustScaler
from catboost import CatBoostClassifier
from google.cloud import bigquery
from dotenv import load_dotenv

optuna.logging.set_verbosity(optuna.logging.WARNING)
warnings.filterwarnings("ignore")
load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "parnasa-498503")
MODELS_DIR = "models/prod"
TOTAL_DAYS, OOS_DAYS, MAX_HOLD = 365, 30, 18
N_TRIALS = 20
os.makedirs(MODELS_DIR, exist_ok=True)

LONG_TP, LONG_SL, LONG_MAE = 2.2, 1.1, 0.65
SHORT_TP, SHORT_SL, SHORT_MAE = 1.4, 0.9, 0.55

print("=" * 115)
print("--> [1/5] Extracting resampled 4H production features from BigQuery...")
print("=" * 115)

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

# 1. Online Causal HMM Forward Recursion
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

# 2. Vectorized Target Generation on 4H Candles
print("--> [2/5] Generating Target Barrier labels across clean 4H candles...")
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
df["fwd_ret_8b"] = df.groupby("asset")["close"].shift(-8) / df["close"] - 1.0

feature_cols = [
    "p_bull", "p_chop", "p_bear", "hmm_entropy", "dp_bull", "dp_bear",
    "dist_ema20_atr", "bbw_pct_40", "mom_24h"
]
for c in feature_cols:
    df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

df_train = df[df["timestamp"] < cutoff_date].dropna(subset=["fwd_ret_8b"]).copy()

# 3. Fast In-Sample Optuna HPO
print(f"--> [3/5] Running Fast Optuna ({N_TRIALS} trials per side on 105k 4H dataset)...")
is_bars = sorted(df_train["timestamp"].unique())
n_bars = len(is_bars)
fold_splits = [
    (is_bars[:int(n_bars * 0.60)], is_bars[int(n_bars * 0.65):int(n_bars * 0.80)]),
    (is_bars[:int(n_bars * 0.75)], is_bars[int(n_bars * 0.80):])
]

def objective_long(trial):
    params = {
        "iterations": trial.suggest_int("iterations", 250, 450, step=50),
        "depth": trial.suggest_int("depth", 4, 6),
        "learning_rate": trial.suggest_float("learning_rate", 0.02, 0.06, log=True),
        "l2_leaf_reg": trial.suggest_float("l2_leaf_reg", 2.0, 8.0),
        "subsample": 0.85, "thread_count": -1, "verbose": False, "random_seed": 42
    }
    scores = []
    for tr_bars, val_bars in fold_splits:
        tr_df = df_train[df_train["timestamp"].isin(tr_bars)]
        val_df = df_train[df_train["timestamp"].isin(val_bars)].copy()
        cb = CatBoostClassifier(**params).fit(tr_df[feature_cols], tr_df["target_long"])
        val_df["p"] = cb.predict_proba(val_df[feature_cols])[:, 1]
        top_slice = val_df[val_df["p"] >= val_df["p"].quantile(0.90)]
        scores.append(top_slice["fwd_ret_8b"].mean() * 10000.0 * top_slice["target_long"].mean())
    return float(np.mean(scores))

def objective_short(trial):
    params = {
        "iterations": trial.suggest_int("iterations", 250, 450, step=50),
        "depth": trial.suggest_int("depth", 4, 6),
        "learning_rate": trial.suggest_float("learning_rate", 0.02, 0.06, log=True),
        "l2_leaf_reg": trial.suggest_float("l2_leaf_reg", 2.0, 8.0),
        "subsample": 0.85, "thread_count": -1, "verbose": False, "random_seed": 42
    }
    scores = []
    for tr_bars, val_bars in fold_splits:
        tr_df = df_train[df_train["timestamp"].isin(tr_bars)]
        val_df = df_train[df_train["timestamp"].isin(val_bars)].copy()
        cb = CatBoostClassifier(**params).fit(tr_df[feature_cols], tr_df["target_short"])
        val_df["p"] = cb.predict_proba(val_df[feature_cols])[:, 1]
        top_slice = val_df[val_df["p"] >= val_df["p"].quantile(0.90)]
        scores.append(-top_slice["fwd_ret_8b"].mean() * 10000.0 * top_slice["target_short"].mean())
    return float(np.mean(scores))

study_l = optuna.create_study(direction="maximize")
study_l.optimize(objective_long, n_trials=N_TRIALS)

study_s = optuna.create_study(direction="maximize")
study_s.optimize(objective_short, n_trials=N_TRIALS)

# 4. Retrain & Freeze Production Models
print("--> [4/5] Retraining production CatBoost models on full In-Sample...")
p_l = study_l.best_params.copy()
p_l.update({"thread_count": -1, "verbose": False, "random_seed": 42})
p_s = study_s.best_params.copy()
p_s.update({"thread_count": -1, "verbose": False, "random_seed": 42})

cb_final_l = CatBoostClassifier(**p_l).fit(df_train[feature_cols], df_train["target_long"])
cb_final_s = CatBoostClassifier(**p_s).fit(df_train[feature_cols], df_train["target_short"])

cb_final_l.save_model(f"{MODELS_DIR}/catboost_long_production.cbm")
cb_final_s.save_model(f"{MODELS_DIR}/catboost_short_production.cbm")

df["p_model_long"] = cb_final_l.predict_proba(df[feature_cols])[:, 1]
df["p_model_short"] = cb_final_s.predict_proba(df[feature_cols])[:, 1]

q90_long = float(df[df["timestamp"] < cutoff_date]["p_model_long"].quantile(0.90))
q85_short = float(df[df["timestamp"] < cutoff_date]["p_model_short"].quantile(0.85))

# Save execution params
config_data = {
  "pipeline_version": "2.2.0-clean-hpo",
  "feature_set": feature_cols,
  "portfolio_sizing": {"max_slots": 5, "weighting_method": "INV_ATR", "gross_leverage_cap": 1.5, "fee_bps_roundtrip": 10.0},
  "calibrated_thresholds": {"p_long_cutoff": round(q90_long, 3), "p_short_cutoff": round(q85_short, 3), "min_hmm_bull_prob": 0.60, "min_hmm_bear_prob": 0.45},
  "barrier_geometry": {"long_tp_mult": LONG_TP, "long_sl_mult": LONG_SL, "short_tp_mult": SHORT_TP, "short_sl_mult": SHORT_SL, "max_holding_bars": MAX_HOLD}
}
with open("config/execution_params.json", "w") as f:
    json.dump(config_data, f, indent=2)

# 5. Execute Portfolio Backtest
print(f"--> [5/5] Simulating Portfolio Backtest across {len(unique_bars)} 4H bars...")
FEE_BPS = 0.0005
bar_data = {ts: df[df["timestamp"] == ts].set_index("asset").to_dict("index") for ts in unique_bars}

equity = 1000.0
equity_curve = [equity]
active_positions = []
completed_trades = []

for b_idx, ts in enumerate(unique_bars):
    current_bar_assets = bar_data[ts]
    first_asset = next(iter(current_bar_assets.values()))
    p_bull, p_bear = first_asset["p_bull"], first_asset["p_bear"]

    # Barrier Exits
    surviving_positions = []
    for pos in active_positions:
        sym = pos["asset"]
        if sym not in current_bar_assets:
            surviving_positions.append(pos)
            continue

        bar = current_bar_assets[sym]
        hi, lo, cl = bar["high"], bar["low"], bar["close"]
        pos["bars_held"] += 1
        direction, entry_p, size_usd = pos["direction"], pos["entry_price"], pos["size_usd"]

        hit_tp, hit_sl, exit_p, exit_reason = False, False, None, None
        if direction == "LONG":
            tp_price, sl_price = entry_p + (LONG_TP * pos["entry_atr"]), entry_p - (LONG_SL * pos["entry_atr"])
            if hi >= tp_price: hit_tp, exit_p, exit_reason = True, tp_price, "TP"
            elif lo <= sl_price: hit_sl, exit_p, exit_reason = True, sl_price, "SL"
        else:
            tp_price, sl_price = entry_p - (SHORT_TP * pos["entry_atr"]), entry_p + (SHORT_SL * pos["entry_atr"])
            if lo <= tp_price: hit_tp, exit_p, exit_reason = True, tp_price, "TP"
            elif hi >= sl_price: hit_sl, exit_p, exit_reason = True, sl_price, "SL"

        if not hit_tp and not hit_sl and pos["bars_held"] >= MAX_HOLD:
            exit_p, exit_reason = cl, "TIME_STOP"

        if exit_p is not None:
            raw_pnl_pct = ((exit_p - entry_p) / entry_p) if direction == "LONG" else ((entry_p - exit_p) / entry_p)
            net_pnl_usd = (size_usd * raw_pnl_pct) - (size_usd * 2 * FEE_BPS)
            equity += net_pnl_usd
            completed_trades.append({"direction": direction, "net_pnl_usd": net_pnl_usd, "exit_reason": exit_reason, "bars_held": pos["bars_held"]})
        else:
            surviving_positions.append(pos)

    active_positions = surviving_positions

    # Capital Allocation
    open_slots = 5 - len(active_positions)
    if open_slots > 0 and equity > 50.0:
        active_syms = {p["asset"] for p in active_positions}
        long_cands = [
            (sym, r["p_model_long"], r["atr_pct"], r["close"], r["atr"], "LONG")
            for sym, r in current_bar_assets.items()
            if sym not in active_syms and r["p_model_long"] >= q90_long and p_bull >= 0.60 and r["close"] > 0
        ]
        short_cands = [
            (sym, r["p_model_short"], r["atr_pct"], r["close"], r["atr"], "SHORT")
            for sym, r in current_bar_assets.items()
            if sym not in active_syms and r["p_model_short"] >= q85_short and p_bear >= 0.45 and r["close"] > 0
        ]
        long_cands.sort(key=lambda x: -x[1])
        short_cands.sort(key=lambda x: -x[1])
        selected = short_cands[:open_slots] if len(short_cands) >= len(long_cands) and short_cands else long_cands[:open_slots]

        if selected:
            total_gross_cap = equity * 1.5
            slot_cap = total_gross_cap / 5
            inv_atrs = [1.0 / max(c[2], 0.005) for c in selected]
            weights = [w / sum(inv_atrs) for w in inv_atrs]

            for idx, (sym, p_val, atr_p, px, atr, dir_str) in enumerate(selected):
                alloc_usd = min(slot_cap, total_gross_cap * weights[idx] * (len(selected) / 5))
                active_positions.append({"asset": sym, "direction": dir_str, "entry_price": px, "entry_atr": atr, "size_usd": alloc_usd, "bars_held": 0})

    equity_curve.append(max(equity, 1.0))

eq_series = pd.Series(equity_curve)
ret_series = eq_series.pct_change().dropna()
trades_df = pd.DataFrame(completed_trades)

term_equity = float(eq_series.iloc[-1])
tot_return = float((term_equity - 1000.0) / 1000.0)
dd = (eq_series / eq_series.cummax()) - 1.0
max_dd = float(abs(dd.min()))

mean_r, std_r = float(ret_series.mean()), float(ret_series.std())
sharpe = float((mean_r / (std_r + 1e-6)) * np.sqrt(2190)) if std_r > 0 else 0.0
neg_std = float(ret_series[ret_series < 0].std())
sortino = float((mean_r / (neg_std + 1e-6)) * np.sqrt(2190)) if neg_std > 0 else 0.0

total_trades = len(trades_df)
win_trades = trades_df[trades_df["net_pnl_usd"] > 0]
win_rate = (len(win_trades) / total_trades * 100.0) if total_trades > 0 else 0.0

print("\n" + "=" * 115)
print("             CLEAN 4H PRODUCTION PIPELINE: OPTUNA + RETRAIN + BACKTEST REPORT             ")
print("=" * 115)
print(pd.DataFrame([{
    "Initial Capital": "$1,000.00",
    "Terminal Equity": f"${term_equity:,.2f}",
    "Total Net PnL": f"{tot_return*100:>+6.2f}%",
    "Annualized Sharpe": f"{sharpe:>5.2f}",
    "Annualized Sortino": f"{sortino:>5.2f}",
    "Max Drawdown": f"{max_dd*100:>4.2f}%",
    "Win Rate": f"{win_rate:>4.1f}%",
    "Total Trades": total_trades
}]).to_string(index=False))

if not trades_df.empty:
    print("\n" + "-" * 115)
    print("DIRECTIONAL PERFORMANCE")
    print("-" * 115)
    print(trades_df.groupby("direction").agg(
        Trades=("net_pnl_usd", "count"),
        WinRate=("net_pnl_usd", lambda x: f"{(x > 0).mean()*100:.1f}%"),
        Total_PnL_USD=("net_pnl_usd", lambda x: f"${x.sum():>+8.2f}"),
        Avg_Trade_PnL=("net_pnl_usd", lambda x: f"${x.mean():>+6.2f}"),
        Avg_Bars_Held=("bars_held", lambda x: f"{x.mean():.1f}")
    ).to_string())
print("=" * 115)
