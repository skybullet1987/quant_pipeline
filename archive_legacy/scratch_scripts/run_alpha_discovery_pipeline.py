import os, joblib, pandas as pd, numpy as np
from hmmlearn.hmm import GaussianHMM
from sklearn.preprocessing import RobustScaler
from catboost import CatBoostClassifier
from google.cloud import bigquery
from scipy.stats import spearmanr
from dotenv import load_dotenv

load_dotenv()
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "parnasa-498503")
TOTAL_DAYS, OOS_DAYS, HOLD_BARS = 365, 90, 8

print("--> [1/4] Extracting raw OHLCV & TimesFM data from BigQuery...")
client = bigquery.Client(project=PROJECT_ID)
query = f"""
    SELECT f.*, 
           COALESCE(t.tfm_ret_24h, 0.0) AS tfm_ret_24h, 
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

print("--> [2/4] Phase 1 & 2: Engineering TimesFM Term Structure & Continuous HMM Dynamics...")
# TimesFM Multi-Horizon & Term Structure
df["tfm_ret_4h"] = df["tfm_ret_24h"] * 0.166
df["tfm_ret_12h"] = df["tfm_ret_24h"] * 0.50
df["tfm_accel"] = (df["tfm_ret_12h"] - df["tfm_ret_4h"]) - (df["tfm_ret_24h"] - df["tfm_ret_12h"])
df["tfm_slope_term"] = df["tfm_ret_24h"] - df["tfm_ret_4h"]
df["tfm_dir_persist"] = np.sign(df["tfm_ret_24h"]) * np.sign(df["tfm_slope"])

unique_bars = sorted(df["timestamp"].unique())
cutoff_date = unique_bars[-1] - pd.Timedelta(days=OOS_DAYS)
df_train = df[df["timestamp"] < cutoff_date].copy()

# Continuous HMM Generator
mbi_tr = df_train.groupby("timestamp").apply(lambda x: (x["close"] > x["ema_20"]).mean(), include_groups=False).rename("mbi")
macro_tr = pd.concat([mbi_tr, df_train.groupby("timestamp")["mom_24h"].std().rename("csd")], axis=1).fillna(0.5)
hmm_scaler = RobustScaler().fit(macro_tr)
hmm = GaussianHMM(n_components=3, covariance_type="full", random_state=42, n_iter=100).fit(hmm_scaler.transform(macro_tr))
canonical_order = np.argsort(-hmm.means_[:, 0])

mbi_all = df.groupby("timestamp").apply(lambda x: (x["close"] > x["ema_20"]).mean(), include_groups=False).rename("mbi")
macro_all = pd.concat([mbi_all, df.groupby("timestamp")["mom_24h"].std().rename("csd")], axis=1).fillna(0.5)
posteriors = hmm.predict_proba(hmm_scaler.transform(macro_all))[:, canonical_order]

df_hmm_dyn = pd.DataFrame({
    "timestamp": macro_all.index,
    "p_bull": posteriors[:, 0],
    "p_chop": posteriors[:, 1],
    "p_bear": posteriors[:, 2],
    "hmm_entropy": -np.sum(posteriors * np.log(posteriors + 1e-8), axis=1)
})
df_hmm_dyn["dp_bull"] = df_hmm_dyn["p_bull"].diff().fillna(0.0)
df_hmm_dyn["dp_bear"] = df_hmm_dyn["p_bear"].diff().fillna(0.0)
df = df.merge(df_hmm_dyn, on="timestamp", how="left")

# Clean Out-of-Sample Forward Target (8-bar return)
df["fwd_ret_8b"] = df.groupby("asset")["close"].shift(-HOLD_BARS) / df["close"] - 1.0

print("\n" + "=" * 115)
print("     [3/4] PHASE 1/2 FEATURE ABLATION LADDER (OOS RANK IC & CONDITIONAL EDGE)     ")
print("=" * 115)

ablation_configs = [
    ("Model A: Baseline Features", ["dist_ema20_atr", "bbw_pct_40", "mom_24h"]),
    ("Model B: + TimesFM Point Forecast", ["dist_ema20_atr", "bbw_pct_40", "mom_24h", "tfm_ret_24h", "tfm_slope"]),
    ("Model C: + TimesFM Term Structure", ["dist_ema20_atr", "bbw_pct_40", "mom_24h", "tfm_ret_24h", "tfm_slope", "tfm_accel", "tfm_slope_term", "tfm_dir_persist"]),
    ("Model D: + Continuous HMM Posteriors", ["dist_ema20_atr", "bbw_pct_40", "mom_24h", "p_bull", "p_chop", "p_bear", "hmm_entropy", "dp_bull", "dp_bear"]),
    ("Model E: Full Fusion Universe", ["dist_ema20_atr", "bbw_pct_40", "mom_24h", "tfm_ret_24h", "tfm_slope", "tfm_accel", "tfm_slope_term", "tfm_dir_persist", "p_bull", "p_chop", "p_bear", "hmm_entropy", "dp_bull", "dp_bear", "rank_liq_intensity"])
]

# Simple 2.6x / 1.3x baseline label for ablation check
bar_map = {ts: df[df["timestamp"] == ts].set_index("asset").to_dict("index") for ts in unique_bars}
recs = []
for b_idx in range(len(unique_bars) - HOLD_BARS):
    ts = unique_bars[b_idx]
    for sym, r in bar_map[ts].items():
        px, atr = r["close"], r["atr"]
        if px <= 0 or atr <= 0: continue
        tp_l, sl_l = px + (2.6 * atr), px - (1.3 * atr)
        hit_tp_l, max_mae_l = False, 0.0
        for f_idx in range(b_idx + 1, b_idx + 1 + HOLD_BARS):
            f_r = bar_map[unique_bars[f_idx]].get(sym)
            if not f_r: continue
            max_mae_l = max(max_mae_l, (px - f_r["low"]) / atr)
            if f_r["high"] >= tp_l: hit_tp_l = True
        recs.append({"timestamp": ts, "asset": sym, "target_long": int(hit_tp_l and max_mae_l <= 0.75)})

df = df.merge(pd.DataFrame(recs), on=["timestamp", "asset"], how="inner")
df_train, df_oos = df[df["timestamp"] < cutoff_date].copy(), df[df["timestamp"] >= cutoff_date].dropna(subset=["fwd_ret_8b"]).copy()

ablation_rows = []
for name, feats in ablation_configs:
    for c in feats:
        df_train[c] = pd.to_numeric(df_train[c], errors="coerce").fillna(0.0)
        df_oos[c] = pd.to_numeric(df_oos[c], errors="coerce").fillna(0.0)

    cb = CatBoostClassifier(iterations=400, depth=5, learning_rate=0.03, l2_leaf_reg=4.0, verbose=False, random_seed=42)
    cb.fit(df_train[feats], df_train["target_long"])
    
    preds_oos = cb.predict_proba(df_oos[feats])[:, 1]
    df_oos["pred"] = preds_oos
    
    # Rank IC
    ic_scores = df_oos.groupby("timestamp").apply(lambda g: spearmanr(g["pred"], g["fwd_ret_8b"])[0] if len(g) > 5 else np.nan).dropna()
    mean_ic, std_ic = ic_scores.mean(), ic_scores.std()
    
    # Top Decile vs Bottom Decile Spread
    q90 = df_oos["pred"].quantile(0.90)
    top_decile_ev = df_oos[df_oos["pred"] >= q90]["fwd_ret_8b"].mean() * 10000.0
    bot_decile_ev = df_oos[df_oos["pred"] < df_oos["pred"].quantile(0.10)]["fwd_ret_8b"].mean() * 10000.0

    ablation_rows.append({
        "Feature Set": name,
        "OOS Rank IC": f"{mean_ic:>+6.3f}",
        "IC IR (Mean/Std)": f"{(mean_ic/max(1e-4, std_ic)):>5.2f}",
        "Top 10% EV (bps)": f"{top_decile_ev:>+6.1f} bps",
        "Decile Spread (bps)": f"{(top_decile_ev - bot_decile_ev):>+6.1f} bps"
    })

print(pd.DataFrame(ablation_rows).to_string(index=False))

print("\n" + "=" * 115)
print("     [4/4] PHASE 3: LABEL GEOMETRY GRID SWEEP (OOS MONOTONIC CONDITIONAL EDGE)     ")
print("=" * 115)

geometry_grid = [
    # Long Grids (TP x SL x MAE)
    ("Long 2.2x / 1.1x (Tight)", 2.2, 1.1, 0.65, "LONG"),
    ("Long 2.6x / 1.3x (Baseline)", 2.6, 1.3, 0.75, "LONG"),
    ("Long 3.0x / 1.4x (Convex)", 3.0, 1.4, 0.85, "LONG"),
    # Short Grids
    ("Short 1.4x / 0.9x (Quick)", 1.4, 0.9, 0.55, "SHORT"),
    ("Short 1.8x / 1.1x (Baseline)", 1.8, 1.1, 0.65, "SHORT"),
    ("Short 2.4x / 1.3x (Cascade)", 2.4, 1.3, 0.75, "SHORT")
]

best_feats = ablation_configs[3][1]  # Model D / Continuous HMM baseline
geo_rows = []

for label, tp_mult, sl_mult, mae_cap, direction in geometry_grid:
    recs_g = []
    for b_idx in range(len(unique_bars) - HOLD_BARS):
        ts = unique_bars[b_idx]
        for sym, r in bar_map[ts].items():
            px, atr = r["close"], r["atr"]
            if px <= 0 or atr <= 0: continue
            hit_tp, max_mae = False, 0.0
            if direction == "LONG":
                target_p = px + (tp_mult * atr)
                for f_idx in range(b_idx + 1, b_idx + 1 + HOLD_BARS):
                    f_r = bar_map[unique_bars[f_idx]].get(sym)
                    if not f_r: continue
                    max_mae = max(max_mae, (px - f_r["low"]) / atr)
                    if f_r["high"] >= target_p: hit_tp = True
            else:
                target_p = px - (tp_mult * atr)
                for f_idx in range(b_idx + 1, b_idx + 1 + HOLD_BARS):
                    f_r = bar_map[unique_bars[f_idx]].get(sym)
                    if not f_r: continue
                    max_mae = max(max_mae, (f_r["high"] - px) / atr)
                    if f_r["low"] <= target_p: hit_tp = True
            recs_g.append({"timestamp": ts, "asset": sym, "tgt": int(hit_tp and max_mae <= mae_cap)})

    df_g = df.merge(pd.DataFrame(recs_g), on=["timestamp", "asset"], how="inner")
    tr_g, oos_g = df_g[df_g["timestamp"] < cutoff_date].copy(), df_g[df_g["timestamp"] >= cutoff_date].dropna(subset=["fwd_ret_8b"]).copy()

    cb_g = CatBoostClassifier(iterations=400, depth=5, learning_rate=0.03, l2_leaf_reg=4.0, verbose=False, random_seed=42)
    cb_g.fit(tr_g[best_feats], tr_g["tgt"])
    
    oos_g["p"] = cb_g.predict_proba(oos_g[best_feats])[:, 1]
    fwd = oos_g["fwd_ret_8b"] if direction == "LONG" else -oos_g["fwd_ret_8b"]
    
    q90 = oos_g["p"].quantile(0.90)
    top_ev = fwd[oos_g["p"] >= q90].mean() * 10000.0
    top_wr = oos_g[oos_g["p"] >= q90]["tgt"].mean() * 100.0
    overall_wr = oos_g["tgt"].mean() * 100.0

    geo_rows.append({
        "Geometry Target": label,
        "Base BaseRate": f"{overall_wr:>4.1f}%",
        "Top 10% WinRate": f"{top_wr:>4.1f}%",
        "Precision Lift": f"{(top_wr - overall_wr):>+5.1f}%",
        "Top 10% EV (bps)": f"{top_ev:>+6.1f} bps"
    })

print(pd.DataFrame(geo_rows).to_string(index=False))
print("=" * 115)
