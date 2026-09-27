import os, warnings, itertools
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
FEE_BPS = 0.0005  # 5 bps taker fee per side

LONG_TP_MULT, LONG_SL_MULT = 2.2, 1.1
SHORT_TP_MULT, SHORT_SL_MULT = 1.4, 0.9

# Empirical thresholds derived from Step 2 Calibration
P_THRESH_LONG = 0.212
P_THRESH_SHORT = 0.242

print("--> [1/3] Extracting OOS universe and features from BigQuery...")
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
df["atr_pct"] = df["atr"] / (df["close"] + 1e-8)
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

# Causal Online HMM
df["ret_4h"] = df.groupby("asset")["close"].pct_change().fillna(0.0)
mbi_ts = df.groupby("timestamp").apply(lambda x: (x["close"] > x["ema_20"]).mean(), include_groups=False).rename("mbi")
csd_ts = df.groupby("timestamp")["ret_4h"].std().fillna(0.01).rename("csd")
macro_df = pd.concat([mbi_ts, csd_ts], axis=1).fillna(0.5)

macro_tr = macro_df[macro_df.index < cutoff_date][["mbi", "csd"]]
hmm_scaler = RobustScaler().fit(macro_tr)
X_tr_scaled = hmm_scaler.transform(macro_tr)

hmm = GaussianHMM(n_components=3, covariance_type="full", random_state=42, n_iter=100).fit(X_tr_scaled)
canonical_order = np.argsort(-hmm.means_[:, 0])

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

feature_cols = [
    "p_bull", "p_chop", "p_bear", "hmm_entropy", "dp_bull", "dp_bear",
    "dist_ema20_atr", "bbw_pct_40", "mom_24h"
]
for c in feature_cols:
    df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

print("--> [2/3] Loading Tuned Models & Generating OOS Predictions...")
cb_long = CatBoostClassifier().load_model(f"{MODELS_DIR}/catboost_long_production.cbm")
cb_short = CatBoostClassifier().load_model(f"{MODELS_DIR}/catboost_short_production.cbm")

df_oos = df[df["timestamp"] >= cutoff_date].copy()
df_oos["p_model_long"] = cb_long.predict_proba(df_oos[feature_cols])[:, 1]
df_oos["p_model_short"] = cb_short.predict_proba(df_oos[feature_cols])[:, 1]

oos_bars = sorted(df_oos["timestamp"].unique())
bar_data = {ts: df_oos[df_oos["timestamp"] == ts].set_index("asset").to_dict("index") for ts in oos_bars}

print(f"--> [3/3] Simulating Portfolio Grid across {len(oos_bars)} 4H Bars...")

def simulate_portfolio(slots, weighting, leverage_cap):
    equity = 1000.0
    equity_curve = [equity]
    active_positions = []
    trade_returns = []
    simul_stopouts = 0

    for b_idx, ts in enumerate(oos_bars):
        current_bar_assets = bar_data[ts]
        first_asset = next(iter(current_bar_assets.values()))
        p_bull, p_bear = first_asset["p_bull"], first_asset["p_bear"]

        # 1. Update Active Positions & Check Barrier Triggers
        surviving_positions = []
        stopped_out_bar = 0

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

            hit_tp, hit_sl, exit_p = False, False, None

            if direction == "LONG":
                tp_price = entry_p + (LONG_TP_MULT * pos["entry_atr"])
                sl_price = entry_p - (LONG_SL_MULT * pos["entry_atr"])
                if hi >= tp_price: hit_tp, exit_p = True, tp_price
                elif lo <= sl_price: hit_sl, exit_p = True, sl_price
            else:
                tp_price = entry_p - (SHORT_TP_MULT * pos["entry_atr"])
                sl_price = entry_p + (SHORT_SL_MULT * pos["entry_atr"])
                if lo <= tp_price: hit_tp, exit_p = True, tp_price
                elif hi >= sl_price: hit_sl, exit_p = True, sl_price

            if not hit_tp and not hit_sl and pos["bars_held"] >= MAX_HOLD_BARS:
                exit_p = cl

            if hit_tp or hit_sl or (pos["bars_held"] >= MAX_HOLD_BARS):
                pnl_pct = ((exit_p - entry_p) / entry_p) if direction == "LONG" else ((entry_p - exit_p) / entry_p)
                net_pnl = (size_usd * pnl_pct) - (size_usd * 2 * FEE_BPS)
                equity += net_pnl
                trade_returns.append(pnl_pct)
                if hit_sl: stopped_out_bar += 1
            else:
                surviving_positions.append(pos)

        if stopped_out_bar >= 2: simul_stopouts += 1
        active_positions = surviving_positions

        # 2. Strict Calibrated Entry Gating
        open_slots = slots - len(active_positions)
        if open_slots > 0 and equity > 50.0:
            active_syms = {p["asset"] for p in active_positions}
            
            # Qualified Longs: P >= 0.212 AND HMM Bull >= 0.60
            long_cands = [
                (sym, r["p_model_long"], r["atr_pct"], r["close"], r["atr"], "LONG")
                for sym, r in current_bar_assets.items()
                if sym not in active_syms and r["p_model_long"] >= P_THRESH_LONG and p_bull >= 0.60 and r["close"] > 0
            ]
            # Qualified Shorts: P >= 0.242 AND HMM Bear >= 0.50
            short_cands = [
                (sym, r["p_model_short"], r["atr_pct"], r["close"], r["atr"], "SHORT")
                for sym, r in current_bar_assets.items()
                if sym not in active_syms and r["p_model_short"] >= P_THRESH_SHORT and p_bear >= 0.50 and r["close"] > 0
            ]

            long_cands.sort(key=lambda x: -x[1])
            short_cands.sort(key=lambda x: -x[1])

            # Select dominant direction
            selected = short_cands[:open_slots] if len(short_cands) >= len(long_cands) and short_cands else long_cands[:open_slots]

            if selected:
                total_gross_cap = equity * leverage_cap
                slot_cap = total_gross_cap / slots

                if weighting == "EQUAL":
                    weights = [1.0 / len(selected)] * len(selected)
                elif weighting == "INV_ATR":
                    inv_atrs = [1.0 / max(c[2], 0.005) for c in selected]
                    weights = [w / sum(inv_atrs) for w in inv_atrs]

                for idx, (sym, p_val, atr_p, px, atr, dir_str) in enumerate(selected):
                    alloc_usd = min(slot_cap, total_gross_cap * weights[idx] * (len(selected) / slots))
                    active_positions.append({
                        "asset": sym, "direction": dir_str, "entry_price": px,
                        "entry_atr": atr, "size_usd": alloc_usd, "bars_held": 0
                    })

        equity_curve.append(max(equity, 1.0))

    eq_series = pd.Series(equity_curve)
    ret_series = eq_series.pct_change().dropna()
    
    term_equity = float(eq_series.iloc[-1])
    tot_return = float((term_equity - 1000.0) / 1000.0)
    dd = (eq_series / eq_series.cummax()) - 1.0
    max_dd = float(abs(dd.min()))
    
    mean_r, std_r = float(ret_series.mean()), float(ret_series.std())
    sharpe = float((mean_r / (std_r + 1e-6)) * np.sqrt(2190)) if std_r > 0 else 0.0
    
    neg_std = float(ret_series[ret_series < 0].std())
    sortino = float((mean_r / (neg_std + 1e-6)) * np.sqrt(2190)) if neg_std > 0 else 0.0
    
    win_rate = float((np.array(trade_returns) > 0).mean() * 100.0) if trade_returns else 0.0

    return {
        "Slots (N)": slots, "Weighting": weighting, "Lev Cap": leverage_cap,
        "Terminal Eq Num": term_equity, "Return Num": tot_return,
        "Sharpe Num": sharpe, "Sortino Num": sortino, "MaxDD Num": max_dd,
        "WinRate Num": win_rate, "Trades": len(trade_returns), "Simul SL": simul_stopouts
    }

results = []
for n, w, lev in itertools.product([1, 2, 3, 4, 5], ["EQUAL", "INV_ATR"], [1.0, 1.5, 2.0, 2.5, 3.0]):
    results.append(simulate_portfolio(n, w, lev))

res_df = pd.DataFrame(results)

print("\n" + "=" * 115)
print("     TOP 15 PORTFOLIO CONFIGURATIONS (SORTED BY NUMERIC SORTINO RATIO)     ")
print("=" * 115)

res_sorted = res_df.sort_values(by="Sortino Num", ascending=False).head(15).copy()
res_sorted["Lev Cap"] = res_sorted["Lev Cap"].map(lambda x: f"{x:.1f}x")
res_sorted["Terminal Eq"] = res_sorted["Terminal Eq Num"].map(lambda x: f"${x:,.1f}")
res_sorted["Return"] = res_sorted["Return Num"].map(lambda x: f"{x*100:>+6.1f}%")
res_sorted["Sharpe"] = res_sorted["Sharpe Num"].map(lambda x: f"{x:>5.2f}")
res_sorted["Sortino"] = res_sorted["Sortino Num"].map(lambda x: f"{x:>5.2f}")
res_sorted["MaxDD"] = res_sorted["MaxDD Num"].map(lambda x: f"{x*100:>4.1f}%")
res_sorted["WinRate"] = res_sorted["WinRate Num"].map(lambda x: f"{x:>4.1f}%")

display_cols = ["Slots (N)", "Weighting", "Lev Cap", "Terminal Eq", "Return", "Sharpe", "Sortino", "MaxDD", "WinRate", "Trades", "Simul SL"]
print(res_sorted[display_cols].to_string(index=False))
print("=" * 115)
