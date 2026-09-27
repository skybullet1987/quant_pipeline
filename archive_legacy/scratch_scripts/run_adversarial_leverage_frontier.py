import os, joblib, pandas as pd, numpy as np
from hmmlearn.hmm import GaussianHMM
from sklearn.preprocessing import RobustScaler
from catboost import CatBoostClassifier
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "parnasa-498503")
INITIAL_CAPITAL, TOTAL_DAYS, OOS_DAYS, HOLD_BARS = 1000.0, 365, 90, 8
LONG_TP_MULT, LONG_SL_MULT, SHORT_TP_MULT, SHORT_SL_MULT = 2.6, 1.3, 1.8, 1.1

print("--> [1/3] Fetching BigQuery universe & computing features...")
client = bigquery.Client(project=PROJECT_ID)
query = f"""
    SELECT f.*, COALESCE(t.tfm_ret_24h, 0.0) AS tfm_ret_24h, COALESCE(t.tfm_slope, 0.0) AS tfm_slope,
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

df["atr"] = df["atr_20"].fillna(df["close"]*0.02) if "atr_20" in df.columns else df["close"]*0.02
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
df_train = df[df["timestamp"] < cutoff_date].copy()

mbi_tr = df_train.groupby("timestamp").apply(lambda x: (x["close"] > x["ema_20"]).mean(), include_groups=False).rename("mbi")
macro_tr = pd.concat([mbi_tr, df_train.groupby("timestamp")["mom_24h"].std().rename("csd")], axis=1).fillna(0.5)
hmm_scaler = RobustScaler().fit(macro_tr)
hmm = GaussianHMM(n_components=3, covariance_type="full", random_state=42, n_iter=100).fit(hmm_scaler.transform(macro_tr))
canonical_order = np.argsort(-hmm.means_[:, 0])

mbi_all = df.groupby("timestamp").apply(lambda x: (x["close"] > x["ema_20"]).mean(), include_groups=False).rename("mbi")
macro_all = pd.concat([mbi_all, df.groupby("timestamp")["mom_24h"].std().rename("csd")], axis=1).fillna(0.5)
df = df.merge(pd.DataFrame({"timestamp": macro_all.index, "regime": hmm.predict_proba(hmm_scaler.transform(macro_all))[:, canonical_order].argmax(axis=1).astype(str), "mbi": macro_all["mbi"].values}), on="timestamp", how="left")

models_l, models_s = {}, {}
for r in ["0", "1", "2"]:
    lp, sp = f"models/prod/regime_{r}_long_expert.cbm", f"models/prod/regime_{r}_short_expert.cbm"
    if os.path.exists(lp): models_l[r] = CatBoostClassifier().load_model(lp)
    if os.path.exists(sp): models_s[r] = CatBoostClassifier().load_model(sp)

df["p_long"], df["p_short"] = 0.50, 0.50
for r_val, g_idx in df.groupby("regime").groups.items():
    r_str = str(r_val)
    if r_str in models_l:
        ml = models_l[r_str]
        for f in ml.feature_names_:
            if f not in df.columns: df[f] = 0.0
            else: df[f] = pd.to_numeric(df[f], errors="coerce").fillna(0.0)
        df.loc[g_idx, "p_long"] = ml.predict_proba(df.loc[g_idx, ml.feature_names_])[:, 1]
    if r_str in models_s:
        ms = models_s[r_str]
        for f in ms.feature_names_:
            if f not in df.columns: df[f] = 0.0
            else: df[f] = pd.to_numeric(df[f], errors="coerce").fillna(0.0)
        df.loc[g_idx, "p_short"] = ms.predict_proba(df.loc[g_idx, ms.feature_names_])[:, 1]

bar_snaps = {ts: df[df["timestamp"] == ts].copy() for ts in unique_bars}

def simulate_exact_causal(bar_list, max_lev, risk_frac, friction_bps=12.0):
    equity = INITIAL_CAPITAL
    open_pos, closed_trades, curve = {}, [], []
    fee_rate = friction_bps / 10000.0

    for b_idx, ts in enumerate(bar_list):
        b_df = bar_snaps[ts]
        if b_df.empty:
            curve.append(equity)
            continue
        px_map, op_map, hi_map, lo_map = b_df.set_index("asset")["close"].to_dict(), b_df.set_index("asset")["open"].to_dict(), b_df.set_index("asset")["high"].to_dict(), b_df.set_index("asset")["low"].to_dict()
        closed = []
        for sym, pos in list(open_pos.items()):
            if sym not in px_map: continue
            o, h, l, c, atr = op_map[sym], hi_map[sym], lo_map[sym], px_map[sym], pos["entry_atr"]
            b_held, high_first = b_idx - pos["entry_bar"], abs(o - h) <= abs(o - l)
            exit_p = None

            if pos["dir"] == -1:
                if high_first:
                    if h >= pos["current_sl"]: exit_p = pos["current_sl"]
                    else:
                        if (pos["entry_px"] - l) >= (1.8 * atr) and not pos["ratchet_hit"]:
                            pos["ratchet_hit"] = True; p_sz = pos["size_usd"] * 0.50
                            equity += (p_sz * (1.0 - (pos["entry_px"] - 1.8 * atr) / pos["entry_px"])) - (p_sz * fee_rate)
                            pos["size_usd"] *= 0.50; pos["current_sl"] = min(pos["current_sl"], pos["entry_px"] - 0.20 * atr)
                        pos["lowest"] = min(pos["lowest"], l)
                        if pos["ratchet_hit"]: pos["current_sl"] = min(pos["current_sl"], pos["lowest"] + 1.6 * atr)
                        if l <= pos["entry_px"] - (3.4 * atr): exit_p = pos["entry_px"] - (3.4 * atr)
                        elif b_held >= 10: exit_p = c
                else:
                    if (pos["entry_px"] - l) >= (1.8 * atr) and not pos["ratchet_hit"]:
                        pos["ratchet_hit"] = True; p_sz = pos["size_usd"] * 0.50
                        equity += (p_sz * (1.0 - (pos["entry_px"] - 1.8 * atr) / pos["entry_px"])) - (p_sz * fee_rate)
                        pos["size_usd"] *= 0.50; pos["current_sl"] = min(pos["current_sl"], pos["entry_px"] - 0.20 * atr)
                    pos["lowest"] = min(pos["lowest"], l)
                    if pos["ratchet_hit"]: pos["current_sl"] = min(pos["current_sl"], pos["lowest"] + 1.6 * atr)
                    if l <= pos["entry_px"] - (3.4 * atr): exit_p = pos["entry_px"] - (3.4 * atr)
                    elif h >= pos["current_sl"]: exit_p = pos["current_sl"]
                    elif b_held >= 10: exit_p = c
                if exit_p is not None:
                    net = (pos["size_usd"] * (1.0 - (exit_p / pos["entry_px"]))) - (pos["size_usd"] * fee_rate)
                    equity += net; closed_trades.append({"ret_pct": (1.0 - exit_p/pos["entry_px"])}); closed.append(sym)
            else:
                pos["highest"] = max(pos["highest"], h)
                if (pos["highest"] - pos["entry_px"]) >= (1.8 * atr) and not pos["ratchet_hit"]:
                    pos["ratchet_hit"] = True; pos["current_sl"] = max(pos["current_sl"], pos["entry_px"] + 0.20 * atr)
                pos["current_sl"] = max(pos["current_sl"], pos["highest"] - 2.0 * atr)
                hit_tp, hit_sl, hit_tm = (h >= pos["tp_px"]), (l <= pos["current_sl"]), (b_held >= HOLD_BARS)
                if hit_tp and hit_sl: exit_p = pos["tp_px"] if abs(o - pos["tp_px"]) <= abs(o - pos["current_sl"]) else pos["current_sl"]
                elif hit_tp: exit_p = pos["tp_px"]
                elif hit_sl: exit_p = pos["current_sl"]
                elif hit_tm: exit_p = c
                if exit_p is not None:
                    net = (pos["size_usd"] * ((exit_p / pos["entry_px"]) - 1.0)) - (pos["size_usd"] * fee_rate)
                    equity += net; closed_trades.append({"ret_pct": (exit_p/pos["entry_px"] - 1.0)}); closed.append(sym)
        for s in closed: del open_pos[s]

        reg, mbi = str(b_df["regime"].iloc[0]), b_df["mbi"].iloc[0]
        v_l = b_df[(b_df["p_long"] >= 0.54) & (b_df["dist_ema20_atr"].between(0.10, 1.35)) & (b_df["bbw_pct_40"] <= 0.60)].sort_values("p_long", ascending=False).head(2)
        v_s = b_df[(b_df["p_short"] >= 0.56) & (b_df["dist_ema20_atr"] < 0.0)].sort_values("p_short", ascending=False).head(2)
        slots = 2 - len(open_pos)
        if slots > 0 and equity > 50.0:
            pnd = []
            if (reg in ["0", "1"] or mbi >= 0.55) and reg != "2":
                for _, r in v_l.iterrows():
                    if r["asset"] not in open_pos and len(pnd) < slots:
                        sd = LONG_SL_MULT * r["atr"]; sz = (equity * risk_frac) / max(1e-6, sd / r["close"])
                        pnd.append({"a": r["asset"], "d": 1, "p": r["close"], "sz": sz, "atr": r["atr"], "tp": r["close"] + LONG_TP_MULT * r["atr"], "sl": r["close"] - sd})
            if (reg in ["1", "2"] or mbi <= 0.45) and reg != "0":
                for _, r in v_s.iterrows():
                    if r["asset"] not in open_pos and (slots - len(pnd)) > 0:
                        sd = SHORT_SL_MULT * r["atr"]; sz = (equity * risk_frac) / max(1e-6, sd / r["close"])
                        pnd.append({"a": r["asset"], "d": -1, "p": r["close"], "sz": sz, "atr": r["atr"], "tp": r["close"] - SHORT_TP_MULT * r["atr"], "sl": r["close"] + sd})
            if pnd:
                tot = sum(x["sz"] for x in pnd)
                if tot / equity > max_lev:
                    for x in pnd: x["sz"] *= (max_lev / (tot / equity))
                for x in pnd:
                    open_pos[x["a"]] = {"dir": x["d"], "entry_px": x["p"], "entry_bar": b_idx, "entry_atr": x["atr"], "size_usd": x["sz"], "tp_px": x["tp"], "sl_px": x["sl"], "current_sl": x["sl"], "highest": x["p"], "lowest": x["p"], "ratchet_hit": False}
        curve.append(equity)
    df_t = pd.DataFrame(closed_trades)
    peak = pd.Series(curve).cummax()
    return curve[-1] / INITIAL_CAPITAL, ((pd.Series(curve) - peak) / peak).min() * 100.0, len(df_t), df_t

print("\n" + "=" * 115)
print("     [2/3] DETERMINISTIC PARTITION EVALUATION ACROSS LEVERAGE TIERS     ")
print("=" * 115)

is_bars, oos_bars = [ts for ts in unique_bars if ts < cutoff_date], [ts for ts in unique_bars if ts >= cutoff_date]
leverage_grid = [
    ("1.5x Leverage", 1.5, 0.025), ("2.0x Leverage", 2.0, 0.035), ("2.5x Leverage", 2.5, 0.042),
    ("3.0x Leverage", 3.0, 0.050), ("3.5x Leverage", 3.5, 0.058), ("4.0x Leverage", 4.0, 0.065), ("5.0x Leverage", 5.0, 0.080)
]

p_rows = []
for lbl, lev, rf in leverage_grid:
    is_m, is_dd, _, _ = simulate_exact_causal(is_bars, lev, rf, 12.0)
    oos_m, oos_dd, _, _ = simulate_exact_causal(oos_bars, lev, rf, 12.0)
    fl_m, fl_dd, fl_n, _ = simulate_exact_causal(unique_bars, lev, rf, 12.0)
    p_rows.append({"Leverage Tier": lbl, "IS (275d)": f"{is_m:>5.2f}x ({is_dd:>5.1f}%)", "OOS (90d)": f"{oos_m:>5.2f}x ({oos_dd:>5.1f}%)", "Full 365d": f"{fl_m:>6.2f}x", "MaxDD": f"{fl_dd:>6.1f}%", "Trades": fl_n})

print(pd.DataFrame(p_rows).to_string(index=False))

print("\n" + "=" * 115)
print("     [3/3] ADVERSARIAL MONTE CARLO STRESS TEST & RUIN PROBABILITY (500 SIMS)     ")
print("=" * 115)

_, _, _, base_trades = simulate_exact_causal(unique_bars, 2.5, 0.042, 12.0)
r_pool = base_trades["ret_pct"].values

stress_rows = []
for lbl, lev, _ in leverage_grid:
    terms, dds, ruins = [], [], 0
    for _ in range(500):
        s_rets = (np.random.choice(r_pool, size=len(r_pool), replace=True) * 0.90) - (25.0 / 10000.0)
        s_idx = np.random.randint(0, max(1, len(s_rets) - 3))
        s_rets[s_idx:s_idx + 3] = -0.065
        eq, c = INITIAL_CAPITAL, [INITIAL_CAPITAL]
        for r in s_rets:
            eq += eq * (lev * 0.40) * r
            if eq <= 100.0: eq = 0.0; break
            c.append(eq)
        terms.append(eq / INITIAL_CAPITAL)
        if eq == 0.0: ruins += 1; dds.append(-100.0)
        else: pk = pd.Series(c).cummax(); dds.append(((pd.Series(c) - pk) / pk).min() * 100.0)
    stress_rows.append({
        "Leverage": f"{lev:.1f}x Gross", "Median Mult": f"{np.median(terms):>5.2f}x", "5th %ile Mult": f"{np.percentile(terms, 5):>5.2f}x",
        "95% MaxDD": f"{np.percentile(dds, 5):>6.1f}%", "P(DD > 30%)": f"{(np.array(dds) <= -30.0).mean()*100:>5.1f}%",
        "P(DD > 50%)": f"{(np.array(dds) <= -50.0).mean()*100:>5.1f}%", "P(Ruin)": f"{(ruins/500)*100:>4.1f}%"
    })

print(pd.DataFrame(stress_rows).to_string(index=False))
print("=" * 115)
