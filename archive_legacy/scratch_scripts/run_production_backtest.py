import os, sys, json, warnings
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
CONFIG_PATH = "config/execution_params.json"
MODELS_DIR = "models/prod"

with open(CONFIG_PATH, "r") as f:
    config = json.load(f)

FEE_BPS = config["portfolio_sizing"].get("fee_bps_roundtrip", 10.0) / 10000.0 / 2.0  # Per side
MAX_SLOTS = config["portfolio_sizing"]["max_slots"]
LEV_CAP = config["portfolio_sizing"]["gross_leverage_cap"]
P_LONG_CUT = config["calibrated_thresholds"]["p_long_cutoff"]
P_SHORT_CUT = config["calibrated_thresholds"]["p_short_cutoff"]
MIN_BULL = config["calibrated_thresholds"]["min_hmm_bull_prob"]
MIN_BEAR = config["calibrated_thresholds"]["min_hmm_bear_prob"]

LONG_TP = config["barrier_geometry"]["long_tp_mult"]
LONG_SL = config["barrier_geometry"]["long_sl_mult"]
SHORT_TP = config["barrier_geometry"]["short_tp_mult"]
SHORT_SL = config["barrier_geometry"]["short_sl_mult"]
MAX_HOLD = config["barrier_geometry"]["max_holding_bars"]

print("=" * 115)
print("--> [1/4] Extracting resampled 4H production dataset from BigQuery...")
print("=" * 115)

client = bigquery.Client(project=PROJECT_ID)
query = f"""
    SELECT 
        timestamp, 
        ticker AS asset, 
        open, high, low, close, volume, 
        atr_20 AS atr, 
        mom_24h, 
        dist_ema20_atr, 
        bbw_pct_40
    FROM `{PROJECT_ID}.market_data.fct_4h_features_production`
    ORDER BY timestamp ASC, ticker ASC
"""
df = client.query(query).to_dataframe()
df["timestamp"] = pd.to_datetime(df["timestamp"])
df["atr_pct"] = df["atr"] / (df["close"] + 1e-8)

# Online Causal HMM Forward Recursion
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

print("--> [2/4] Scoring historical bars using frozen production CatBoost models...")
feature_cols = config["feature_set"]
for c in feature_cols:
    df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

cb_long = CatBoostClassifier().load_model(f"{MODELS_DIR}/catboost_long_production.cbm")
cb_short = CatBoostClassifier().load_model(f"{MODELS_DIR}/catboost_short_production.cbm")

df["p_model_long"] = cb_long.predict_proba(df[feature_cols])[:, 1]
df["p_model_short"] = cb_short.predict_proba(df[feature_cols])[:, 1]

unique_bars = sorted(df["timestamp"].unique())
bar_data = {ts: df[df["timestamp"] == ts].set_index("asset").to_dict("index") for ts in unique_bars}

print(f"--> [3/4] Running portfolio simulation across {len(unique_bars)} historical 4H bars...")

equity = 1000.0
equity_curve = [{"timestamp": unique_bars[0], "equity": equity}]
active_positions = []
completed_trades = []

for b_idx, ts in enumerate(unique_bars):
    current_bar_assets = bar_data[ts]
    first_asset = next(iter(current_bar_assets.values()))
    p_bull, p_bear = first_asset["p_bull"], first_asset["p_bear"]

    # 1. Evaluate open positions against candle High/Low barriers
    surviving_positions = []
    for pos in active_positions:
        sym = pos["asset"]
        if sym not in current_bar_assets:
            surviving_positions.append(pos)
            continue

        bar = current_bar_assets[sym]
        hi, lo, cl = bar["high"], bar["low"], bar["close"]
        pos["bars_held"] += 1
        direction = pos["direction"]
        entry_p = pos["entry_price"]
        size_usd = pos["size_usd"]

        hit_tp, hit_sl, exit_p, exit_reason = False, False, None, None

        if direction == "LONG":
            tp_price = entry_p + (LONG_TP * pos["entry_atr"])
            sl_price = entry_p - (LONG_SL * pos["entry_atr"])
            if hi >= tp_price:
                hit_tp, exit_p, exit_reason = True, tp_price, "TP"
            elif lo <= sl_price:
                hit_sl, exit_p, exit_reason = True, sl_price, "SL"
        else:  # SHORT
            tp_price = entry_p - (SHORT_TP * pos["entry_atr"])
            sl_price = entry_p + (SHORT_SL * pos["entry_atr"])
            if lo <= tp_price:
                hit_tp, exit_p, exit_reason = True, tp_price, "TP"
            elif hi >= sl_price:
                hit_sl, exit_p, exit_reason = True, sl_price, "SL"

        if not hit_tp and not hit_sl and pos["bars_held"] >= MAX_HOLD:
            exit_p, exit_reason = cl, "TIME_STOP"

        if exit_p is not None:
            raw_pnl_pct = ((exit_p - entry_p) / entry_p) if direction == "LONG" else ((entry_p - exit_p) / entry_p)
            fee_cost = size_usd * 2 * FEE_BPS
            net_pnl_usd = (size_usd * raw_pnl_pct) - fee_cost
            equity += net_pnl_usd
            completed_trades.append({
                "entry_ts": pos["entry_ts"],
                "exit_ts": ts,
                "asset": sym,
                "direction": direction,
                "size_usd": size_usd,
                "entry_price": entry_p,
                "exit_price": exit_p,
                "pnl_pct": raw_pnl_pct,
                "net_pnl_usd": net_pnl_usd,
                "exit_reason": exit_reason,
                "bars_held": pos["bars_held"]
            })
        else:
            surviving_positions.append(pos)

    active_positions = surviving_positions

    # 2. Allocate capital to new qualified signals
    open_slots = MAX_SLOTS - len(active_positions)
    if open_slots > 0 and equity > 50.0:
        active_syms = {p["asset"] for p in active_positions}

        long_cands = [
            (sym, r["p_model_long"], r["atr_pct"], r["close"], r["atr"], "LONG")
            for sym, r in current_bar_assets.items()
            if sym not in active_syms and r["p_model_long"] >= P_LONG_CUT and p_bull >= MIN_BULL and r["close"] > 0
        ]
        short_cands = [
            (sym, r["p_model_short"], r["atr_pct"], r["close"], r["atr"], "SHORT")
            for sym, r in current_bar_assets.items()
            if sym not in active_syms and r["p_model_short"] >= P_SHORT_CUT and p_bear >= MIN_BEAR and r["close"] > 0
        ]

        long_cands.sort(key=lambda x: -x[1])
        short_cands.sort(key=lambda x: -x[1])

        selected = short_cands[:open_slots] if len(short_cands) >= len(long_cands) and short_cands else long_cands[:open_slots]

        if selected:
            total_gross_cap = equity * LEV_CAP
            slot_cap = total_gross_cap / MAX_SLOTS

            inv_atrs = [1.0 / max(c[2], 0.005) for c in selected]
            sum_inv_atr = sum(inv_atrs)
            weights = [w / sum_inv_atr for w in inv_atrs]

            for idx, (sym, p_val, atr_p, px, atr, dir_str) in enumerate(selected):
                alloc_usd = min(slot_cap, total_gross_cap * weights[idx] * (len(selected) / MAX_SLOTS))
                active_positions.append({
                    "entry_ts": ts,
                    "asset": sym,
                    "direction": dir_str,
                    "entry_price": px,
                    "entry_atr": atr,
                    "size_usd": alloc_usd,
                    "bars_held": 0
                })

    equity_curve.append({"timestamp": ts, "equity": max(equity, 1.0)})

eq_df = pd.DataFrame(equity_curve).set_index("timestamp")
eq_series = eq_df["equity"]
ret_series = eq_series.pct_change().dropna()
trades_df = pd.DataFrame(completed_trades)

# Performance Calculations
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
loss_trades = trades_df[trades_df["net_pnl_usd"] <= 0]

win_rate = (len(win_trades) / total_trades * 100.0) if total_trades > 0 else 0.0
gross_profit = win_trades["net_pnl_usd"].sum() if not win_trades.empty else 0.0
gross_loss = abs(loss_trades["net_pnl_usd"].sum()) if not loss_trades.empty else 1e-6
profit_factor = gross_profit / gross_loss

print("\n" + "=" * 115)
print("                    PRODUCTION PORTFOLIO BACKTEST PERFORMANCE REPORT                    ")
print("=" * 115)

summary_table = pd.DataFrame([{
    "Initial Capital": "$1,000.00",
    "Terminal Equity": f"${term_equity:,.2f}",
    "Total Net PnL": f"{tot_return*100:>+6.2f}%",
    "Annualized Sharpe": f"{sharpe:>5.2f}",
    "Annualized Sortino": f"{sortino:>5.2f}",
    "Max Drawdown": f"{max_dd*100:>4.2f}%",
    "Profit Factor": f"{profit_factor:>4.2f}",
    "Win Rate": f"{win_rate:>4.1f}%",
    "Total Trades": total_trades
}])
print(summary_table.to_string(index=False))

# Long vs Short Breakdown
if not trades_df.empty:
    print("\n" + "-" * 115)
    print("DIRECTIONAL BREAKDOWN")
    print("-" * 115)
    dir_summary = trades_df.groupby("direction").agg(
        Trades=("net_pnl_usd", "count"),
        WinRate=("net_pnl_usd", lambda x: f"{(x > 0).mean()*100:.1f}%"),
        Total_PnL_USD=("net_pnl_usd", lambda x: f"${x.sum():>+8.2f}"),
        Avg_Trade_PnL=("net_pnl_usd", lambda x: f"${x.mean():>+6.2f}"),
        Avg_Bars_Held=("bars_held", lambda x: f"{x.mean():.1f}")
    )
    print(dir_summary.to_string())

    print("\n" + "-" * 115)
    print("EXIT REASON DISTRIBUTION")
    print("-" * 115)
    exit_summary = trades_df.groupby("exit_reason").agg(
        Count=("net_pnl_usd", "count"),
        Pct_Total=("net_pnl_usd", lambda x: f"{len(x)/total_trades*100:.1f}%"),
        Net_PnL_USD=("net_pnl_usd", lambda x: f"${x.sum():>+8.2f}"),
        WinRate=("net_pnl_usd", lambda x: f"{(x > 0).mean()*100:.1f}%")
    )
    print(exit_summary.to_string())

print("=" * 115)
