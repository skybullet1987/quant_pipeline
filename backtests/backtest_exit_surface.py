import os, sys, warnings
PROJECT_ROOT = os.path.abspath(os.getenv("QUANT_PROJECT_ROOT", "/home/skybullet1987/quant_pipeline"))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import itertools
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

print("--> [1/4] Extracting feature dataset from BigQuery...")
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

# 2. Causal Macro Regime Posteriors
print("--> [2/4] Estimating causal HMM posteriors & scoring CatBoost...")
df["ema_20"] = df.groupby("asset")["close"].transform(lambda x: x.ewm(span=20, adjust=False).mean())
mbi_ts = df.groupby("timestamp").apply(lambda x: (x["close"] > x["ema_20"]).mean(), include_groups=False).rename("mbi")
csd_ts = df.groupby("timestamp")["ret_4h"].std().fillna(0.01).rename("csd")
macro_df = pd.concat([mbi_ts, csd_ts], axis=1).fillna(0.5)

btc_col = next((c for c in df["asset"].unique() if c in ("BTC", "kBTC", "BTC-PERP")), "BTC")
btc_df = df[df["asset"] == btc_col].set_index("timestamp")
macro_df["btc_above_ema20"] = (btc_df["close"] > btc_df["ema_20"]).reindex(macro_df.index).fillna(False)

hmm_scaler = RobustScaler().fit(macro_df[["mbi", "csd"]])
X_all = hmm_scaler.transform(macro_df[["mbi", "csd"]])
hmm = GaussianHMM(n_components=3, covariance_type="diag", min_covar=1e-3, random_state=42, n_iter=75).fit(X_all)
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

df = df.merge(macro_df[["p_bull", "p_chop", "p_bear", "hmm_entropy", "dp_bull", "dp_bear", "btc_above_ema20"]].reset_index(), on="timestamp", how="left")

cb_long = CatBoostClassifier().load_model(f"{MODELS_DIR}/catboost_long_production.cbm")
cb_short = CatBoostClassifier().load_model(f"{MODELS_DIR}/catboost_short_production.cbm")
feature_cols = ["p_bull", "p_chop", "p_bear", "hmm_entropy", "dp_bull", "dp_bear", "dist_ema20_atr", "bbw_pct_40", "mom_24h"]

for c in feature_cols:
    df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

df["p_model_long"] = cb_long.predict_proba(df[feature_cols])[:, 1]
df["p_model_short"] = cb_short.predict_proba(df[feature_cols])[:, 1]

# 3. MFE / MAE Path Analytics (Frozen Baseline Entries)
print("--> [3/4] Computing MFE / MAE excursion metrics across candidate entries...")
timestamps = sorted(df["timestamp"].unique())
ts_to_idx = {ts: i for i, ts in enumerate(timestamps)}
df_indexed = df.set_index(["timestamp", "asset"]).sort_index()

entry_signals = []
cooldown = {}
MAX_SLOTS = 2
MIN_HMM_BEAR = 0.40
MIN_HMM_BULL = 0.88
Q_SHORT = 0.245
Q_LONG = 0.320

for t_idx, ts in enumerate(timestamps):
    bar_df = df[df["timestamp"] == ts].set_index("asset")
    if bar_df.empty:
        continue
    p_bull = float(bar_df["p_bull"].iloc[0])
    p_bear = float(bar_df["p_bear"].iloc[0])
    btc_bull = bool(bar_df["btc_above_ema20"].iloc[0])

    if p_bear >= MIN_HMM_BEAR:
        cands = bar_df[(bar_df["p_model_short"] >= Q_SHORT) & (bar_df["mom_24h"] < 0.0)].sort_values(by="p_model_short", ascending=False)
        for sym, row in cands.iterrows():
            if t_idx - cooldown.get(sym, -99) >= 3:
                entry_signals.append({
                    "entry_idx": t_idx, "timestamp": ts, "asset": sym, "side": "SHORT",
                    "entry_px": float(row["close"]), "atr": float(row["atr"]),
                    "p_score": float(row["p_model_short"]), "initial_sl": 0.85
                })
                cooldown[sym] = t_idx

    elif p_bull >= MIN_HMM_BULL and btc_bull:
        cands = bar_df[(bar_df["p_model_long"] >= Q_LONG) & (bar_df["mom_24h"] > 0.02)].sort_values(by="p_model_long", ascending=False)
        for sym, row in cands.iterrows():
            if t_idx - cooldown.get(sym, -99) >= 3:
                entry_signals.append({
                    "entry_idx": t_idx, "timestamp": ts, "asset": sym, "side": "LONG",
                    "entry_px": float(row["close"]), "atr": float(row["atr"]),
                    "p_score": float(row["p_model_long"]), "initial_sl": 1.0
                })
                cooldown[sym] = t_idx

# Calculate 18-bar forward MFE/MAE excursions in ATR units
mfe_records = []
for sig in entry_signals:
    sym = sig["asset"]
    e_idx = sig["entry_idx"]
    px0 = sig["entry_px"]
    atr = sig["atr"]
    side = sig["side"]
    
    forward_bars = [timestamps[i] for i in range(e_idx + 1, min(e_idx + 19, len(timestamps)))]
    highs, lows, closes = [], [], []
    for f_ts in forward_bars:
        if (f_ts, sym) in df_indexed.index:
            row = df_indexed.loc[(f_ts, sym)]
            highs.append(float(row["high"]))
            lows.append(float(row["low"]))
            closes.append(float(row["close"]))

    if not highs:
        continue

    if side == "LONG":
        mfe_atr = (max(highs) - px0) / atr
        mae_atr = (px0 - min(lows)) / atr
    else:
        mfe_atr = (px0 - min(lows)) / atr
        mae_atr = (max(highs) - px0) / atr

    mfe_records.append({
        "asset": sym, "side": side, "mfe_atr": mfe_atr, "mae_atr": mae_atr,
        "hit_2_atr": mfe_atr >= 2.0, "hit_3_2_atr": mfe_atr >= 3.2,
        "hit_5_atr": mfe_atr >= 5.0, "hit_8_atr": mfe_atr >= 8.0
    })

mfe_df = pd.DataFrame(mfe_records)

print("\n" + "="*55)
print("       EMPIRICAL EXCURSION PROFILE (MFE / MAE)")
print("="*55)
print(f"Total Evaluated Setups     : {len(mfe_df)}")
print(f"Median MFE (Favorable)     : {mfe_df['mfe_atr'].median():.2f}x ATR")
print(f"75th Percentile MFE        : {mfe_df['mfe_atr'].quantile(0.75):.2f}x ATR")
print(f"90th Percentile MFE        : {mfe_df['mfe_atr'].quantile(0.90):.2f}x ATR")
print(f"Max MFE Reached            : {mfe_df['mfe_atr'].max():.2f}x ATR")
print(f"Median MAE (Adverse)       : {mfe_df['mae_atr'].median():.2f}x ATR")
print("-" * 55)
print(f"Continuation Rate >= 2.0x ATR : {mfe_df['hit_2_atr'].mean()*100:.1f}%")
print(f"Continuation Rate >= 3.2x ATR : {mfe_df['hit_3_2_atr'].mean()*100:.1f}%")
print(f"Extension Rate    >= 5.0x ATR : {mfe_df['hit_5_atr'].mean()*100:.1f}%")
print(f"Extension Rate    >= 8.0x ATR : {mfe_df['hit_8_atr'].mean()*100:.1f}%")
print("="*55 + "\n")

# 4. Exit-Surface Grid Search
print("--> [4/4] Simulating Exit Parameter Surface...")

taker_fee = 0.00035
slippage = 0.00020
friction_rate = (taker_fee + slippage) * 2

def simulate_surface(split_ratio, tp1_mult, trail_mult, sl_active_mult):
    equity = 500.00
    equity_curve = [equity]
    trades = []
    active_positions = {}
    cooldown_tracker = {}
    base_lev = 5.0

    for t_idx, ts in enumerate(timestamps):
        bar_df = df[df["timestamp"] == ts].set_index("asset")
        if bar_df.empty:
            continue

        p_bull = float(bar_df["p_bull"].iloc[0])
        p_bear = float(bar_df["p_bear"].iloc[0])
        btc_bull = bool(bar_df["btc_above_ema20"].iloc[0])

        closed_syms = []
        for sym, pos in active_positions.items():
            if sym not in bar_df.index:
                continue
            c_row = bar_df.loc[sym]
            c_high, c_low, c_close = float(c_row["high"]), float(c_row["low"]), float(c_row["close"])
            bars_held = t_idx - pos["entry_bar"]

            # 1. Tranche A (Partial TP)
            if not pos["tranche_a_closed"]:
                if pos["side"] == "LONG" and c_high >= pos["tp1_px"]:
                    pnl_a = (pos["notional_a"] * ((pos["tp1_px"] - pos["entry_price"]) / pos["entry_price"])) - (pos["notional_a"] * friction_rate)
                    equity += pnl_a
                    pos["tranche_a_closed"] = True
                    # Activate runner trailing stop
                    pos["sl_px"] = pos["entry_price"] + (sl_active_mult * pos["atr"])
                    pos["runner_best_px"] = pos["tp1_px"]
                elif pos["side"] == "SHORT" and c_low <= pos["tp1_px"]:
                    pnl_a = (pos["notional_a"] * ((pos["entry_price"] - pos["tp1_px"]) / pos["entry_price"])) - (pos["notional_a"] * friction_rate)
                    equity += pnl_a
                    pos["tranche_a_closed"] = True
                    # Activate runner trailing stop
                    pos["sl_px"] = pos["entry_price"] - (sl_active_mult * pos["atr"])
                    pos["runner_best_px"] = pos["tp1_px"]

            # Update Chandelier trailing stop for Tranche B
            if pos["tranche_a_closed"] and pos["notional_b"] > 0:
                if pos["side"] == "LONG":
                    if c_high > pos["runner_best_px"]:
                        pos["runner_best_px"] = c_high
                        pos["sl_px"] = max(pos["sl_px"], pos["runner_best_px"] - (trail_mult * pos["atr"]))
                else:
                    if c_low < pos["runner_best_px"]:
                        pos["runner_best_px"] = c_low
                        pos["sl_px"] = min(pos["sl_px"], pos["runner_best_px"] + (trail_mult * pos["atr"]))

            # Evaluate Exits
            hit_sl = False
            time_exit = False
            exit_px = c_close

            if pos["side"] == "LONG":
                if c_low <= pos["sl_px"]:
                    hit_sl = True
                    exit_px = pos["sl_px"]
                elif bars_held >= 18:
                    time_exit = True
                    exit_px = c_close
            else:
                if c_high >= pos["sl_px"]:
                    hit_sl = True
                    exit_px = pos["sl_px"]
                elif bars_held >= 18:
                    time_exit = True
                    exit_px = c_close

            if hit_sl or time_exit:
                remaining_notional = (pos["notional_a"] if not pos["tranche_a_closed"] else 0.0) + pos["notional_b"]
                if remaining_notional > 0:
                    ret_mult = (exit_px - pos["entry_price"]) / pos["entry_price"] if pos["side"] == "LONG" else (pos["entry_price"] - exit_px) / pos["entry_price"]
                    pnl_b = (remaining_notional * ret_mult) - (remaining_notional * friction_rate)
                    equity += pnl_b
                    trades.append({"pnl": pnl_b})
                closed_syms.append(sym)
                cooldown_tracker[sym] = t_idx

        for s in closed_syms:
            del active_positions[s]

        # Sizing & Position Allocation
        open_slots = MAX_SLOTS - len(active_positions)
        if open_slots > 0:
            eligible = [s for s in bar_df.index if s not in active_positions and (t_idx - cooldown_tracker.get(s, -99)) >= 3]

            if p_bear >= MIN_HMM_BEAR:
                cands = bar_df.loc[eligible]
                cands = cands[(cands["p_model_short"] >= Q_SHORT) & (cands["mom_24h"] < 0.0)].sort_values(by="p_model_short", ascending=False).head(open_slots)
                for sym, row in cands.iterrows():
                    px = float(row["close"])
                    atr = float(row["atr"])
                    p_score = float(row["p_model_short"])
                    slot_lev = float(np.clip((base_lev / MAX_SLOTS) + (max(0.0, p_score - 0.28) / 0.15 * 0.5), 2.5, 3.0))
                    total_ntl = equity * slot_lev

                    active_positions[sym] = {
                        "side": "SHORT", "entry_price": px, "atr": atr, "entry_bar": t_idx,
                        "notional_a": total_ntl * split_ratio, "notional_b": total_ntl * (1.0 - split_ratio),
                        "tp1_px": px - (tp1_mult * atr), "sl_px": px + (0.85 * atr),
                        "tranche_a_closed": False, "runner_best_px": px
                    }

            elif p_bull >= MIN_HMM_BULL and btc_bull:
                cands = bar_df.loc[eligible]
                cands = cands[(cands["p_model_long"] >= Q_LONG) & (cands["mom_24h"] > 0.02)].sort_values(by="p_model_long", ascending=False).head(open_slots)
                for sym, row in cands.iterrows():
                    px = float(row["close"])
                    atr = float(row["atr"])
                    total_ntl = equity * (base_lev / MAX_SLOTS)

                    active_positions[sym] = {
                        "side": "LONG", "entry_price": px, "atr": atr, "entry_bar": t_idx,
                        "notional_a": total_ntl * split_ratio, "notional_b": total_ntl * (1.0 - split_ratio),
                        "tp1_px": px + (tp1_mult * atr), "sl_px": px - (1.0 * atr),
                        "tranche_a_closed": False, "runner_best_px": px
                    }

        equity_curve.append(equity)

    eq_series = pd.Series(equity_curve)
    peak = eq_series.cummax()
    dd = (eq_series - peak) / peak
    max_dd = abs(dd.min()) * 100
    net_pnl = equity - 500.00
    total_ret = (net_pnl / 500.00) * 100
    calmar_proxy = total_ret / (max_dd + 1e-8)

    return {
        "split": f"{int(split_ratio*100)}/{int((1-split_ratio)*100)}",
        "tp1": tp1_mult,
        "trail": trail_mult,
        "sl_act": sl_active_mult,
        "ending_eq": equity,
        "net_pnl": net_pnl,
        "ret_pct": total_ret,
        "mdd": max_dd,
        "calmar": calmar_proxy
    }

# Run Grid
splits = [1.0, 0.70, 0.60, 0.50]  # 1.0 is 100% hard TP baseline
tp1_vals = [1.8, 2.0, 2.2, 2.5]
trails = [1.5, 2.0, 2.5]
sl_activations = [0.0, 0.25, 0.50]

results = []
# Baseline (100% hard TP at 3.2x ATR)
res_base = simulate_surface(1.0, 3.2, 2.5, 0.0)
res_base["config"] = "BASELINE (100% @ 3.2 ATR)"
results.append(res_base)

for sp, tp1, tr, act in itertools.product(splits[1:], tp1_vals, trails, sl_activations):
    r = simulate_surface(sp, tp1, tr, act)
    r["config"] = f"Split {r['split']} | TP1={tp1}x | Trail={tr}x | SL_Act={act}x"
    results.append(r)

res_df = pd.DataFrame(results).sort_values(by="calmar", ascending=False)

print("="*85)
print("                 TOP 10 EXIT CONFIGURATIONS (BY RETURN / MAX DD)")
print("="*85)
print(res_df[["config", "ending_eq", "ret_pct", "mdd", "calmar"]].head(10).to_string(index=False))

print("\n" + "="*85)
print("                 BASELINE vs BEST RUNNER COMPARISON")
print("="*85)
best_runner = res_df[res_df["config"] != "BASELINE (100% @ 3.2 ATR)"].iloc[0]
baseline_row = res_df[res_df["config"] == "BASELINE (100% @ 3.2 ATR)"].iloc[0]

comp_df = pd.DataFrame([baseline_row, best_runner])
print(comp_df[["config", "ending_eq", "ret_pct", "mdd", "calmar"]].to_string(index=False))
