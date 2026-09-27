import os, joblib, optuna, pandas as pd, numpy as np
from catboost import CatBoostClassifier
from google.cloud import bigquery
from dotenv import load_dotenv

optuna.logging.set_verbosity(optuna.logging.WARNING)
load_dotenv()
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "parnasa-498503")
MODELS_DIR = "models/prod"
INITIAL_CAPITAL = 1000.0
TOTAL_DAYS, OOS_DAYS, HOLD_BARS = 365, 90, 8

print("--> [1/5] Extracting 365-day dataset from BigQuery...")
client = bigquery.Client(project=PROJECT_ID)
query = f"""
    SELECT f.*, COALESCE(t.tfm_ret_24h, 0.0) AS tfm_ret_24h, 
           COALESCE(t.tfm_slope, 0.0) AS tfm_slope,
           COALESCE(l.rank_liq_intensity, 0) AS rank_liq_intensity
    FROM `{PROJECT_ID}.market_data.fct_4h_features_tbm` f
    LEFT JOIN `{PROJECT_ID}.market_data.fct_timesfm_features` t ON f.timestamp = t.timestamp AND f.ticker = t.ticker
    LEFT JOIN `{PROJECT_ID}.market_data.fct_liquidation_features` l ON f.timestamp = l.timestamp AND f.ticker = l.ticker
    WHERE f.timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {TOTAL_DAYS} DAY)
    ORDER BY f.timestamp ASC, f.ticker ASC
"""
df = client.query(query).to_dataframe()
df["timestamp"] = pd.to_datetime(df["timestamp"])
if "asset" not in df.columns and "ticker" in df.columns: df["asset"] = df["ticker"]
if "open" not in df.columns or df["open"].isnull().all(): df["open"] = df.groupby("asset")["close"].shift(1).fillna(df["close"])

df["atr"] = df["atr_20"].fillna(df["close"]*0.02) if "atr_20" in df.columns else (df["atr"].fillna(df["close"]*0.02) if "atr" in df.columns else df["close"]*0.02)
df["ema_20"] = df.groupby("asset")["close"].transform(lambda x: x.ewm(span=20, adjust=False).mean())
df["dist_ema20_atr"] = (df["close"] - df["ema_20"]) / (df["atr"] + 1e-8)

sma_20 = df.groupby("asset")["close"].transform(lambda x: x.rolling(20, min_periods=5).mean())
std_20 = df.groupby("asset")["close"].transform(lambda x: x.rolling(20, min_periods=5).std().fillna(0.0))
df["bbw"] = (4.0 * std_20) / (sma_20 + 1e-8)
roll_min = df.groupby("asset")["bbw"].transform(lambda x: x.rolling(40, min_periods=10).min())
roll_max = df.groupby("asset")["bbw"].transform(lambda x: x.rolling(40, min_periods=10).max())
df["bbw_pct_40"] = ((df["bbw"] - roll_min) / (roll_max - roll_min + 1e-8)).fillna(0.50).clip(0.0, 1.0)
df["mom_24h"] = df.groupby("asset")["close"].transform(lambda x: x.pct_change(6).fillna(0.0))
df["funding_annual"] = df["funding_rate"].fillna(0.0) * 24.0 * 365.0 if "funding_rate" in df.columns else 0.0

print("--> [2/5] Generating Drawdown-Penalized exact-path labels...")
unique_bars = sorted(df["timestamp"].unique())
bar_map = {ts: df[df["timestamp"] == ts].set_index("asset").to_dict("index") for ts in unique_bars}
recs = []
for b_idx in range(len(unique_bars) - HOLD_BARS):
    ts = unique_bars[b_idx]
    for sym, r in bar_map[ts].items():
        px, atr = r["close"], r["atr"]
        if px <= 0 or atr <= 0: continue
        tp_l, sl_l = px + (2.6 * atr), px - (1.3 * atr)
        tp_s, sl_s = px - (1.8 * atr), px + (1.1 * atr)
        hit_tp_l, hit_sl_l, hit_tp_s, hit_sl_s = False, False, False, False
        max_mae_l, max_mae_s = 0.0, 0.0
        for f_idx in range(b_idx + 1, b_idx + 1 + HOLD_BARS):
            f_r = bar_map[unique_bars[f_idx]].get(sym)
            if not f_r: continue
            max_mae_l = max(max_mae_l, (px - f_r["low"]) / atr)
            max_mae_s = max(max_mae_s, (f_r["high"] - px) / atr)
            if not hit_tp_l and not hit_sl_l:
                if f_r["low"] <= sl_l: hit_sl_l = True
                elif f_r["high"] >= tp_l: hit_tp_l = True
            if not hit_tp_s and not hit_sl_s:
                if f_r["high"] >= sl_s: hit_sl_s = True
                elif f_r["low"] <= tp_s: hit_tp_s = True
        recs.append({"timestamp": ts, "asset": sym, "target_long": int(hit_tp_l and max_mae_l <= 0.75), "target_short": int(hit_tp_s and max_mae_s <= 0.65)})

df = df.merge(pd.DataFrame(recs), on=["timestamp", "asset"], how="inner")

hmm_model = joblib.load(f"{MODELS_DIR}/hmm_macro.pkl")
hmm_scaler = joblib.load(f"{MODELS_DIR}/hmm_scaler.pkl")
hmm_feats = joblib.load(f"{MODELS_DIR}/hmm_feature_names.pkl")
canonical_order = joblib.load(f"{MODELS_DIR}/hmm_canonical_order.pkl")
for c in hmm_feats: df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0) if c in df.columns else 0.0
df["regime"] = hmm_model.predict_proba(hmm_scaler.transform(df[hmm_feats]))[:, canonical_order].argmax(axis=1).astype(str)

feat_cols = ["dist_ema20_atr", "bbw_pct_40", "mom_24h", "funding_annual", "tfm_ret_24h", "tfm_slope", "rank_liq_intensity"]
for c in ["market_breadth_sma20", "vol_expansion_ratio", "rsi_14"]:
    if c in df.columns: feat_cols.append(c)
for c in feat_cols: df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

cutoff = unique_bars[-1] - pd.Timedelta(days=OOS_DAYS)
df_train, df_oos = df[df["timestamp"] < cutoff].copy(), df[df["timestamp"] >= cutoff].copy()

print("--> [3/5] Running Optuna HPO for CatBoost Regime Experts (25 Trials/Regime)...")
best_l, best_s = {}, {}
for r in ["0", "1", "2"]:
    sub_tr = df_train[df_train["regime"] == r]
    if len(sub_tr) < 500: sub_tr = df_train
    t_cut = sub_tr["timestamp"].quantile(0.80)
    tr, val = sub_tr[sub_tr["timestamp"] < t_cut], sub_tr[sub_tr["timestamp"] >= t_cut]
    
    def obj(trial, tgt):
        m = CatBoostClassifier(iterations=400, depth=trial.suggest_int("d", 4, 7), learning_rate=trial.suggest_float("lr", 0.02, 0.08, log=True),
                               l2_leaf_reg=trial.suggest_float("l2", 1.0, 8.0), subsample=trial.suggest_float("sub", 0.7, 1.0),
                               scale_pos_weight=trial.suggest_float("spw", 1.5, 4.0), verbose=False, random_seed=42)
        m.fit(tr[feat_cols], tr[tgt], eval_set=(val[feat_cols], val[tgt]), early_stopping_rounds=30, verbose=False)
        preds = m.predict_proba(val[feat_cols])[:, 1]
        top = preds >= np.quantile(preds, 0.90)
        return val.loc[top, tgt].mean() if top.sum() > 0 else -1.0

    st_l = optuna.create_study(direction="maximize"); st_l.optimize(lambda t: obj(t, "target_long"), n_trials=25, timeout=90)
    st_s = optuna.create_study(direction="maximize"); st_s.optimize(lambda t: obj(t, "target_short"), n_trials=25, timeout=90)
    
    pl, ps = st_l.best_params, st_s.best_params
    cb_l = CatBoostClassifier(iterations=600, depth=pl["d"], learning_rate=pl["lr"], l2_leaf_reg=pl["l2"], subsample=pl["sub"], scale_pos_weight=pl["spw"], verbose=False, random_seed=42)
    cb_s = CatBoostClassifier(iterations=600, depth=ps["d"], learning_rate=ps["lr"], l2_leaf_reg=ps["l2"], subsample=ps["sub"], scale_pos_weight=ps["spw"], verbose=False, random_seed=42)
    cb_l.fit(sub_tr[feat_cols], sub_tr["target_long"]); cb_s.fit(sub_tr[feat_cols], sub_tr["target_short"])
    cb_l.save_model(f"{MODELS_DIR}/regime_{r}_long_expert.cbm"); cb_s.save_model(f"{MODELS_DIR}/regime_{r}_short_expert.cbm")
    best_l[r], best_s[r] = cb_l, cb_s

df["p_long"], df["p_short"] = 0.50, 0.50
for r_val, g_idx in df.groupby("regime").groups.items():
    df.loc[g_idx, "p_long"] = best_l.get(str(r_val), best_l["1"]).predict_proba(df.loc[g_idx, feat_cols])[:, 1]
    df.loc[g_idx, "p_short"] = best_s.get(str(r_val), best_s["1"]).predict_proba(df.loc[g_idx, feat_cols])[:, 1]

bar_snaps = {ts: df[df["timestamp"] == ts].copy() for ts in unique_bars}

def sim_portfolio(p, bar_list, fee_bps=12.0):
    eq, pos, trades, curve = INITIAL_CAPITAL, {}, [], []
    fee = fee_bps / 10000.0
    for b_idx, ts in enumerate(bar_list):
        b_df = bar_snaps[ts]
        px_map, h_map, l_map, atr_map = b_df.set_index("asset")["close"].to_dict(), b_df.set_index("asset")["high"].to_dict(), b_df.set_index("asset")["low"].to_dict(), b_df.set_index("asset")["atr"].to_dict()
        closed = []
        for sym, cp in list(pos.items()):
            if sym not in px_map: continue
            h, l, c, atr = h_map[sym], l_map[sym], px_map[sym], atr_map.get(sym, (h_map[sym]-l_map[sym]))
            cp["h"], cp["l"] = max(cp["h"], h), min(cp["l"], l)
            b_held = b_idx - cp["b"]
            if cp["dir"] == 1:
                if (cp["h"] - cp["entry"]) / atr >= p["ratchet"] and not cp["pt"]:
                    cp["pt"] = True
                    p_sz = cp["sz"] * 0.40; p_ex = cp["entry"] + p["ratchet"] * atr
                    eq += (p_sz * (p_ex/cp["entry"] - 1.0)) - (p_sz * fee); cp["sz"] *= 0.60
                    cp["sl"] = max(cp["sl"], cp["entry"] + 0.20 * atr)
                cp["sl"] = max(cp["sl"], cp["h"] - (p["sl_m"] * 1.5 * atr))
                hit_sl, hit_tp, hit_tm = (l <= cp["sl"]), (h >= cp["entry"] + p["tp_m"] * atr), (b_held >= p["hold"])
                if hit_sl or hit_tp or hit_tm:
                    ep = cp["sl"] if hit_sl else (cp["entry"] + p["tp_m"] * atr if hit_tp else c)
                    net = (cp["sz"] * (ep/cp["entry"] - 1.0)) - (cp["sz"] * fee); eq += net
                    trades.append({"pnl": net, "win": net > 0}); closed.append(sym)
            else:
                tp_px = cp["entry"] - (p["tp_m"] * 0.75 * atr); sl_px = cp["entry"] + (p["sl_m"] * atr)
                hit_tp, hit_sl, hit_tm = (l <= tp_px), (h >= sl_px), (b_held >= int(p["hold"]*0.6))
                if hit_tp or hit_sl or hit_tm:
                    ep = tp_px if hit_tp else (sl_px if hit_sl else c)
                    net = (cp["sz"] * (1.0 - ep/cp["entry"])) - (cp["sz"] * fee); eq += net
                    trades.append({"pnl": net, "win": net > 0}); closed.append(sym)
        for s in closed: del pos[s]
        
        mbi = (b_df["close"] > b_df["ema_20"]).mean()
        reg = 0 if mbi >= 0.60 else (2 if mbi < 0.35 else 1)
        b_df = b_df.copy()
        b_df["l_score"] = b_df["p_long"] + (0.3 * b_df["mom_24h"]) - (0.2 * b_df["bbw_pct_40"])
        b_df["s_score"] = b_df["p_short"] - (0.4 * b_df["mom_24h"])
        v_l = b_df[(b_df["p_long"] >= p["l_p"]) & (b_df["dist_ema20_atr"].between(0.1, 1.3)) & (b_df["bbw_pct_40"] <= 0.50)].sort_values(by="l_score", ascending=False).head(2)
        v_s = b_df[(b_df["p_short"] >= p["s_p"]) & (b_df["dist_ema20_atr"] < 0.0)].sort_values(by="s_score", ascending=False).head(2)
        
        slots = 2 - len(pos)
        if slots > 0 and eq > 50.0:
            pending = []
            if reg in [0, 1]:
                for _, rw in v_l.iterrows():
                    if rw["asset"] not in pos and len(pending) < slots:
                        sd = p["sl_m"] * rw["atr"]; sz = (eq * p["risk"]) / max(1e-6, sd / rw["close"])
                        pending.append({"asset": rw["asset"], "dir": 1, "entry": rw["close"], "sz": sz, "sl": rw["close"] - sd, "atr": rw["atr"]})
            if reg in [1, 2]:
                for _, rw in v_s.iterrows():
                    if rw["asset"] not in pos and (slots - len(pending)) > 0:
                        sd = p["sl_m"] * rw["atr"]; sz = (eq * p["risk"]) / max(1e-6, sd / rw["close"])
                        pending.append({"asset": rw["asset"], "dir": -1, "entry": rw["close"], "sz": sz, "sl": rw["close"] + sd, "atr": rw["atr"]})
            if pending:
                tot = sum(x["sz"] for x in pending)
                if tot / eq > p["max_lev"]:
                    for x in pending: x["sz"] *= (p["max_lev"] / (tot / eq))
                for x in pending:
                    pos[x["asset"]] = {"dir": x["dir"], "entry": x["entry"], "b": b_idx, "sz": x["sz"], "sl": x["sl"], "pt": False, "h": x["entry"], "l": x["entry"]}
        curve.append(eq)

    t_df = pd.DataFrame(trades)
    wins = t_df[t_df["pnl"] > 0]["pnl"].sum() if not t_df.empty else 0.0
    loss = abs(t_df[t_df["pnl"] <= 0]["pnl"].sum()) if not t_df.empty else 1.0
    dd = ((pd.Series(curve) - pd.Series(curve).cummax()) / pd.Series(curve).cummax()).min() * 100.0
    return curve[-1]/INITIAL_CAPITAL, dd, wins/loss, (t_df["win"].mean()*100 if not t_df.empty else 0.0), len(t_df), curve[-1]

print("--> [4/5] Running Optuna on Compounding Policy (80 Trials)...")
in_bars = [ts for ts in unique_bars if ts < cutoff]
oos_bars = [ts for ts in unique_bars if ts >= cutoff]

def obj_port(trial):
    p = {"risk": trial.suggest_float("risk", 0.03, 0.055), "max_lev": trial.suggest_float("max_lev", 2.0, 2.8),
         "l_p": trial.suggest_float("l_p", 0.55, 0.68), "s_p": trial.suggest_float("s_p", 0.35, 0.52),
         "tp_m": trial.suggest_float("tp_m", 2.4, 3.4), "sl_m": trial.suggest_float("sl_m", 1.1, 1.4),
         "ratchet": trial.suggest_float("ratchet", 1.6, 2.2), "hold": trial.suggest_int("hold", 8, 14)}
    m, dd, pf, wr, n, _ = sim_portfolio(p, in_bars, 12.0)
    return -1.0 if (n < 30 or dd < -25.0) else m * (1.0 - abs(dd)/100.0)

st_p = optuna.create_study(direction="maximize"); st_p.optimize(obj_port, n_trials=80, timeout=120)
best_p = st_p.best_params

print("\n" + "=" * 100)
print("--> [5/5] FULL LIFECYCLE MULTI-TIER EVALUATION")
print("=" * 100)
for label, b_list, bps in [("In-Sample (275d)", in_bars, 12.0), ("Out-of-Sample (90d)", oos_bars, 12.0),
                           ("Full 365d (12 bps)", unique_bars, 12.0), ("Stress 365d (25 bps)", unique_bars, 25.0)]:
    m, dd, pf, wr, n, end_eq = sim_portfolio(best_p, b_list, bps)
    print(f"[{label:<22}] Multiple: {m:>5.2f}x | Equity: ${end_eq:>8.2f} | MaxDD: {dd:>6.1f}% | PF: {pf:.2f} | WR: {wr:.1f}% | Trades: {n}")
print("=" * 100)
