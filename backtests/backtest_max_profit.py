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

print("--> [1/4] Extracting 90D dataset from BigQuery...")
client = bigquery.Client(project=PROJECT_ID)
query = f"""
    SELECT timestamp, ticker AS asset, open, high, low, close, volume,
           atr_20 AS atr, mom_24h, dist_ema20_atr, bbw_pct_40
    FROM `{PROJECT_ID}.market_data.fct_4h_features_production`
    ORDER BY timestamp ASC, ticker ASC
"""
df = client.query(query).to_dataframe()
df["timestamp"] = pd.to_datetime(df["timestamp"])
df["atr_pct"] = df["atr"] / (df["close"] + 1e-8)
df["ret_4h"] = df.groupby("asset")["close"].pct_change().fillna(0.0)

print("--> [2/4] Computing Causal HMM & scoring CatBoost...")
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
macro_df["p_bull"] = causal_posteriors[:, 0]
macro_df["p_chop"] = causal_posteriors[:, 1]
macro_df["p_bear"] = causal_posteriors[:, 2]
macro_df["hmm_entropy"] = -np.sum(causal_posteriors * np.log(causal_posteriors + 1e-8), axis=1)
macro_df["dp_bull"] = macro_df["p_bull"].diff().fillna(0.0)
macro_df["dp_bear"] = macro_df["p_bear"].diff().fillna(0.0)

df = df.merge(macro_df[["p_bull", "p_chop", "p_bear", "hmm_entropy", "dp_bull", "dp_bear"]].reset_index(), on="timestamp", how="left")

cb_long = CatBoostClassifier().load_model(f"{MODELS_DIR}/catboost_long_production.cbm")
cb_short = CatBoostClassifier().load_model(f"{MODELS_DIR}/catboost_short_production.cbm")
feature_cols = ["p_bull", "p_chop", "p_bear", "hmm_entropy", "dp_bull", "dp_bear", "dist_ema20_atr", "bbw_pct_40", "mom_24h"]

for c in feature_cols:
    df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

df["p_model_long"] = cb_long.predict_proba(df[feature_cols])[:, 1]
df["p_model_short"] = cb_short.predict_proba(df[feature_cols])[:, 1]

# 3. High-Compounding Max Profit Simulation
print("--> [3/4] Running Max-Profit Simulation with Volatility Targeting & Breakeven Ratchet...")
timestamps = sorted(df["timestamp"].unique())

initial_capital = 500.00
equity = initial_capital
equity_curve = [equity]
trades = []
active_positions = {}
cooldown_tracker = {}

taker_fee = 0.00035
slippage = 0.00020
friction_rate = (taker_fee + slippage) * 2

# Aggressive Profit Maximization Parameters
MIN_HMM_BULL = 0.70
MIN_HMM_BEAR = 0.45
Q_LONG = 0.280          # Filter low-conviction long noise
Q_SHORT = 0.250         # Exploit high-performing short edge
RISK_PER_TRADE = 0.045  # 4.5% equity risk per trade setup
MAX_SINGLE_LEV = 4.5    # Up to 4.5x leverage on compressed setups
MAX_PORTFOLIO_LEV = 9.0 # Aggregate portfolio leverage ceiling
MAX_HOLD_BARS = 18
COOLDOWN_BARS = 3

for t_idx, ts in enumerate(timestamps):
    bar_df = df[df["timestamp"] == ts].set_index("asset")
    if bar_df.empty:
        continue

    p_bull = float(bar_df["p_bull"].iloc[0])
    p_chop = float(bar_df["p_chop"].iloc[0])
    p_bear = float(bar_df["p_bear"].iloc[0])

    # 1. Manage Active Positions with Breakeven Ratchets
    closed_syms = []
    for sym, pos in active_positions.items():
        if sym not in bar_df.index:
            continue
        c_row = bar_df.loc[sym]
        c_high, c_low, c_close, c_atr = float(c_row["high"]), float(c_row["low"]), float(c_row["close"]), float(c_row["atr"])
        bars_held = t_idx - pos["entry_bar"]

        # Stage 1: Breakeven Ratchet at +1.0x ATR
        if not pos["is_be_locked"]:
            if pos["side"] == "LONG" and c_high >= (pos["entry_price"] + 1.0 * c_atr):
                pos["sl_px"] = pos["entry_price"] * (1.0 + friction_rate)
                pos["is_be_locked"] = True
            elif pos["side"] == "SHORT" and c_low <= (pos["entry_price"] - 1.0 * c_atr):
                pos["sl_px"] = pos["entry_price"] * (1.0 - friction_rate)
                pos["is_be_locked"] = True

        hit_tp, hit_sl, time_exit = False, False, False
        exit_px = c_close

        if pos["side"] == "LONG":
            if c_high >= pos["tp_px"]:
                hit_tp = True
                exit_px = pos["tp_px"]
            elif c_low <= pos["sl_px"]:
                hit_sl = True
                exit_px = pos["sl_px"]
            elif bars_held >= MAX_HOLD_BARS:
                time_exit = True
                exit_px = c_close
        else:
            if c_low <= pos["tp_px"]:
                hit_tp = True
                exit_px = pos["tp_px"]
            elif c_high >= pos["sl_px"]:
                hit_sl = True
                exit_px = pos["sl_px"]
            elif bars_held >= MAX_HOLD_BARS:
                time_exit = True
                exit_px = c_close

        if hit_tp or hit_sl or time_exit:
            pnl_mult = (exit_px - pos["entry_price"]) / pos["entry_price"] if pos["side"] == "LONG" else (pos["entry_price"] - exit_px) / pos["entry_price"]
            pnl = (pos["notional"] * pnl_mult) - (pos["notional"] * friction_rate)
            equity += pnl
            tag = "TP" if hit_tp else ("BE_SCRATCH" if pos["is_be_locked"] and hit_sl else ("SL" if hit_sl else "TIME"))
            trades.append({
                "asset": sym,
                "side": pos["side"],
                "pnl": pnl,
                "ret_pct": pnl_mult,
                "exit_reason": tag,
                "notional": pos["notional"],
                "equity_after": equity
            })
            closed_syms.append(sym)
            cooldown_tracker[sym] = t_idx

    for s in closed_syms:
        del active_positions[s]

    # 2. Open High-Leverage Setups with Volatility Risk Parity
    current_portfolio_notional = sum(p["notional"] for p in active_positions.values())
    max_additional_notional = max(0.0, (equity * MAX_PORTFOLIO_LEV) - current_portfolio_notional)
    open_slots = 3 - len(active_positions)

    if open_slots > 0 and max_additional_notional > (equity * 0.5):
        eligible_cands = [s for s in bar_df.index if s not in active_positions and (t_idx - cooldown_tracker.get(s, -99)) >= COOLDOWN_BARS]

        if p_bull >= MIN_HMM_BULL:
            cands = bar_df.loc[eligible_cands]
            cands = cands[(cands["p_model_long"] >= Q_LONG) & (cands["mom_24h"] > 0.0)].sort_values(by="p_model_long", ascending=False).head(open_slots)
            for sym, row in cands.iterrows():
                px = float(row["close"])
                atr = float(row["atr"])
                stop_dist_pct = (1.1 * atr) / px
                
                # Sizing based on risk budget
                target_notional = min((equity * RISK_PER_TRADE) / stop_dist_pct, equity * MAX_SINGLE_LEV, max_additional_notional)
                if target_notional >= (equity * 0.5):
                    active_positions[sym] = {
                        "side": "LONG",
                        "entry_price": px,
                        "notional": target_notional,
                        "tp_px": px + (2.5 * atr),
                        "sl_px": px - (1.1 * atr),
                        "is_be_locked": False,
                        "entry_bar": t_idx
                    }
                    max_additional_notional -= target_notional

        elif p_bear >= MIN_HMM_BEAR:
            cands = bar_df.loc[eligible_cands]
            cands = cands[(cands["p_model_short"] >= Q_SHORT) & (cands["mom_24h"] < 0.0)].sort_values(by="p_model_short", ascending=False).head(open_slots)
            for sym, row in cands.iterrows():
                px = float(row["close"])
                atr = float(row["atr"])
                stop_dist_pct = (0.9 * atr) / px
                
                target_notional = min((equity * RISK_PER_TRADE) / stop_dist_pct, equity * MAX_SINGLE_LEV, max_additional_notional)
                if target_notional >= (equity * 0.5):
                    active_positions[sym] = {
                        "side": "SHORT",
                        "entry_price": px,
                        "notional": target_notional,
                        "tp_px": px - (1.6 * atr),
                        "sl_px": px + (0.9 * atr),
                        "is_be_locked": False,
                        "entry_bar": t_idx
                    }
                    max_additional_notional -= target_notional

    equity_curve.append(equity)

# 4. Analytics
print("--> [4/4] Performance Summary...")
trades_df = pd.DataFrame(trades)
eq_series = pd.Series(equity_curve)
peak = eq_series.cummax()
dd = (eq_series - peak) / peak

total_trades = len(trades_df)
wins = len(trades_df[trades_df["pnl"] > 0])
losses = len(trades_df[trades_df["pnl"] <= 0])
win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0
total_pnl = equity - initial_capital
total_ret = (total_pnl / initial_capital) * 100
max_dd = abs(dd.min()) * 100
profit_factor = (trades_df[trades_df["pnl"] > 0]["pnl"].sum() / abs(trades_df[trades_df["pnl"] < 0]["pnl"].sum())) if losses > 0 else np.nan

print("\n" + "="*55)
print("     MAX-PROFIT VOLATILITY-SCALED BACKTEST (90D)")
print("="*55)
print(f"Starting Capital       : ${initial_capital:,.2f}")
print(f"Ending Equity          : ${equity:,.2f}")
print(f"Net Profit             : ${total_pnl:+,.2f} ({total_ret:+.2f}%)")
print(f"Total Completed Trades : {total_trades}")
print(f"Win Rate               : {win_rate:.1f}% ({wins}W / {losses}L)")
print(f"Profit Factor          : {profit_factor:.2f}")
print(f"Maximum Drawdown (MDD) : {max_dd:.2f}%")
print("="*55)

if total_trades > 0:
    print("\n--- Exit Reason Breakdown ---")
    print(trades_df.groupby("exit_reason").agg(
        Trades=("pnl", "count"),
        Win_Rate=("pnl", lambda x: f"{(x > 0).mean()*100:.1f}%"),
        Avg_PnL=("pnl", "mean"),
        Total_PnL=("pnl", "sum")
    ).to_string())

    print("\n--- Long vs Short Performance ---")
    print(trades_df.groupby("side").agg(
        Trades=("pnl", "count"),
        Win_Rate=("pnl", lambda x: f"{(x > 0).mean()*100:.1f}%"),
        Total_PnL=("pnl", "sum")
    ).to_string())
