import os, json, warnings
import pandas as pd, numpy as np
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
os.makedirs(MODELS_DIR, exist_ok=True)

LONG_TP, LONG_SL, LONG_MAE = 2.2, 1.1, 0.65
SHORT_TP, SHORT_SL, SHORT_MAE = 1.4, 0.9, 0.55
FEE_BPS = 0.0005

print("--> [1/3] Loading 4H production features from BigQuery...")
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

all_bars = sorted(df["timestamp"].unique())
cutoff_date = all_bars[-1] - pd.Timedelta(days=30)

# Causal Online HMM
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

# Target Generation
bar_map = {ts: df[df["timestamp"] == ts].set_index("asset").to_dict("index") for ts in all_bars}
recs = []
for b_idx in range(len(all_bars) - 18):
    ts = all_bars[b_idx]
    for sym, r in bar_map[ts].items():
        px, atr = r["close"], r["atr"]
        if px <= 0 or atr <= 0: continue
        tp_l, sl_l = px + (LONG_TP * atr), px - (LONG_SL * atr)
        tp_s, sl_s = px - (SHORT_TP * atr), px + (SHORT_SL * atr)
        hit_tp_l, hit_sl_l, hit_tp_s, hit_sl_s = False, False, False, False
        max_mae_l, max_mae_s = 0.0, 0.0
        for f_idx in range(b_idx + 1, b_idx + 19):
            f_r = bar_map[all_bars[f_idx]].get(sym)
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
feature_cols = ["p_bull", "p_chop", "p_bear", "hmm_entropy", "dp_bull", "dp_bear", "dist_ema20_atr", "bbw_pct_40", "mom_24h"]
for c in feature_cols: df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

print("--> [2/3] Training Production CatBoost Models...")
is_mask = df["timestamp"] < cutoff_date
cb_s = CatBoostClassifier(iterations=350, depth=4, learning_rate=0.04, l2_leaf_reg=5.0, thread_count=-1, verbose=False, random_seed=42).fit(df.loc[is_mask, feature_cols], df.loc[is_mask, "target_short"])
cb_l = CatBoostClassifier(iterations=350, depth=4, learning_rate=0.03, l2_leaf_reg=5.0, thread_count=-1, verbose=False, random_seed=42).fit(df.loc[is_mask, feature_cols], df.loc[is_mask, "target_long"])

cb_s.save_model(f"{MODELS_DIR}/catboost_short_production.cbm")
cb_l.save_model(f"{MODELS_DIR}/catboost_long_production.cbm")

df["p_model_short"] = cb_s.predict_proba(df[feature_cols])[:, 1]
df["p_model_long"] = cb_l.predict_proba(df[feature_cols])[:, 1]

q85_s = float(df.loc[is_mask, "p_model_short"].quantile(0.85))
q92_l = float(df.loc[is_mask, "p_model_long"].quantile(0.92))

print(f"--> Thresholds Locked: Short Q85 = {q85_s:.3f} | Long Q92 = {q92_l:.3f}")

# Simulation
print("--> [3/3] Running Concentrated Compounding Growth Backtests...")
valid_bars = sorted(df["timestamp"].unique())
bar_data = {ts: df[df["timestamp"] == ts].set_index("asset").to_dict("index") for ts in valid_bars}

def simulate(slots, lev_cap):
    equity = 1000.0
    equity_curve = [equity]
    active_positions = []
    trades = []

    for ts in valid_bars:
        current_assets = bar_data.get(ts, {})
        if not current_assets: continue
        
        first = next(iter(current_assets.values()))
        p_bull, p_bear = first["p_bull"], first["p_bear"]

        surviving = []
        for pos in active_positions:
            sym = pos["asset"]
            if sym not in current_assets:
                surviving.append(pos)
                continue
            
            b = current_assets[sym]
            hi, lo, cl = b["high"], b["low"], b["close"]
            pos["bars"] += 1
            direction, entry_p, size_usd = pos["dir"], pos["entry_p"], pos["size"]
            tp_p = entry_p + (LONG_TP if direction == "LONG" else -SHORT_TP) * pos["atr"]
            sl_p = entry_p - (LONG_SL if direction == "LONG" else -SHORT_SL) * pos["atr"]

            hit_tp = (hi >= tp_p) if direction == "LONG" else (lo <= tp_p)
            hit_sl = (lo <= sl_p) if direction == "LONG" else (hi >= sl_p)
            exit_p = None

            if hit_tp: exit_p = tp_p
            elif hit_sl: exit_p = sl_p
            elif pos["bars"] >= 18: exit_p = cl

            if exit_p is not None:
                pnl_pct = ((exit_p - entry_p) / entry_p) if direction == "LONG" else ((entry_p - exit_p) / entry_p)
                net_usd = (size_usd * pnl_pct) - (size_usd * 2 * FEE_BPS)
                equity += net_usd
                trades.append({"dir": direction, "net_usd": net_usd})
            else:
                surviving.append(pos)
        
        active_positions = surviving
        open_slots = slots - len(active_positions)
        
        if open_slots > 0 and equity > 25.0:
            active_syms = {p["asset"] for p in active_positions}
            short_cands = [
                (s, r["p_model_short"], r["atr_pct"], r["close"], r["atr"], "SHORT")
                for s, r in current_assets.items()
                if s not in active_syms and r["p_model_short"] >= q85_s and p_bear >= 0.45 and r["close"] > 0
            ]
            long_cands = [
                (s, r["p_model_long"], r["atr_pct"], r["close"], r["atr"], "LONG")
                for s, r in current_assets.items()
                if s not in active_syms and r["p_model_long"] >= q92_l and p_bull >= 0.70 and r["close"] > 0
            ]
            short_cands.sort(key=lambda x: -x[1])
            long_cands.sort(key=lambda x: -x[1])

            selected = short_cands[:open_slots] if len(short_cands) >= len(long_cands) and short_cands else long_cands[:open_slots]

            if selected:
                inv_atrs = [1.0 / max(c[2], 0.005) for c in selected]
                weights = [w / sum(inv_atrs) for w in inv_atrs]
                for idx, (sym, p_val, atr_p, px, atr, dir_str) in enumerate(selected):
                    slot_alloc = (equity * lev_cap * weights[idx]) * (len(selected) / slots)
                    active_positions.append({"asset": sym, "dir": dir_str, "entry_p": px, "atr": atr, "size": slot_alloc, "bars": 0})

        equity_curve.append(max(equity, 1.0))

    eq = pd.Series(equity_curve)
    ret = eq.pct_change().dropna()
    tot_ret = (eq.iloc[-1] - 1000.0) / 1000.0
    max_dd = abs(((eq / eq.cummax()) - 1.0).min())
    sortino = (ret.mean() / (ret[ret < 0].std() + 1e-6)) * np.sqrt(2190) if len(ret[ret < 0]) > 0 else 0.0
    wr = (pd.DataFrame(trades)["net_usd"] > 0).mean() * 100 if trades else 0.0

    return {
        "Slots": slots, "Leverage": f"{lev_cap:.1f}x", "Terminal Eq": f"${eq.iloc[-1]:,.2f}",
        "Return": f"{tot_ret*100:>+7.1f}%", "Sortino": f"{sortino:>5.2f}",
        "MaxDD": f"{max_dd*100:>5.1f}%", "WinRate": f"{wr:>4.1f}%", "Trades": len(trades)
    }

print("\n" + "=" * 105)
print("              CONCENTRATED COMPOUNDING GROWTH SIMULATION MATRIX              ")
print("=" * 105)
results = []
for slots in [2, 3]:
    for lev in [2.5, 3.0, 3.5, 4.0]:
        results.append(simulate(slots, lev))

print(pd.DataFrame(results).to_string(index=False))
print("=" * 105)
