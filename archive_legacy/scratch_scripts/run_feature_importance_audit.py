import os, joblib, pandas as pd, numpy as np
from hmmlearn.hmm import GaussianHMM
from sklearn.preprocessing import RobustScaler
from catboost import CatBoostClassifier, Pool
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "parnasa-498503")
TOTAL_DAYS, OOS_DAYS, HOLD_BARS = 365, 90, 8

print("--> [1/3] Extracting complete feature matrix from BigQuery...")
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

unique_bars = sorted(df["timestamp"].unique())
cutoff_date = unique_bars[-1] - pd.Timedelta(days=OOS_DAYS)
df_train = df[df["timestamp"] < cutoff_date].copy()

# Fit continuous HMM on In-Sample
mbi_tr = df_train.groupby("timestamp").apply(lambda x: (x["close"] > x["ema_20"]).mean(), include_groups=False).rename("mbi")
macro_tr = pd.concat([mbi_tr, df_train.groupby("timestamp")["mom_24h"].std().rename("csd")], axis=1).fillna(0.5)
hmm_scaler = RobustScaler().fit(macro_tr)
hmm = GaussianHMM(n_components=3, covariance_type="full", random_state=42, n_iter=100).fit(hmm_scaler.transform(macro_tr))
canonical_order = np.argsort(-hmm.means_[:, 0])

mbi_all = df.groupby("timestamp").apply(lambda x: (x["close"] > x["ema_20"]).mean(), include_groups=False).rename("mbi")
macro_all = pd.concat([mbi_all, df.groupby("timestamp")["mom_24h"].std().rename("csd")], axis=1).fillna(0.5)
posteriors = hmm.predict_proba(hmm_scaler.transform(macro_all))[:, canonical_order]

df_hmm = pd.DataFrame({
    "timestamp": macro_all.index,
    "p_bull": posteriors[:, 0],
    "p_chop": posteriors[:, 1],
    "p_bear": posteriors[:, 2],
    "hmm_entropy": -np.sum(posteriors * np.log(posteriors + 1e-8), axis=1)
})
df_hmm["dp_bull"] = df_hmm["p_bull"].diff().fillna(0.0)
df_hmm["dp_bear"] = df_hmm["p_bear"].diff().fillna(0.0)
df = df.merge(df_hmm, on="timestamp", how="left")

# Generate Drawdown-Penalized Targets
bar_map = {ts: df[df["timestamp"] == ts].set_index("asset").to_dict("index") for ts in unique_bars}
recs = []
for b_idx in range(len(unique_bars) - HOLD_BARS):
    ts = unique_bars[b_idx]
    for sym, r in bar_map[ts].items():
        px, atr = r["close"], r["atr"]
        if px <= 0 or atr <= 0: continue
        tp_l, sl_l = px + (2.2 * atr), px - (1.1 * atr)
        tp_s, sl_s = px - (1.4 * atr), px + (0.9 * atr)
        hit_tp_l, hit_sl_l, hit_tp_s, hit_sl_s = False, False, False, False
        max_mae_l, max_mae_s = 0.0, 0.0
        for f_idx in range(b_idx + 1, b_idx + 1 + HOLD_BARS):
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
        recs.append({"timestamp": ts, "asset": sym, "target_long": int(hit_tp_l and max_mae_l <= 0.65), "target_short": int(hit_tp_s and max_mae_s <= 0.55)})

df = df.merge(pd.DataFrame(recs), on=["timestamp", "asset"], how="inner")
df_train = df[df["timestamp"] < cutoff_date].copy()
df_oos = df[df["timestamp"] >= cutoff_date].copy()

all_feature_candidates = [
    "tfm_ret_24h", "tfm_slope", "rank_liq_intensity",
    "dist_ema20_atr", "bbw_pct_40", "mom_24h",
    "p_bull", "p_chop", "p_bear", "hmm_entropy", "dp_bull", "dp_bear"
]
for c in all_feature_candidates:
    df_train[c] = pd.to_numeric(df_train[c], errors="coerce").fillna(0.0)
    df_oos[c] = pd.to_numeric(df_oos[c], errors="coerce").fillna(0.0)

print("--> [2/3] Fitting Full CatBoost Classifiers & Computing SHAP Values...")
cb_long = CatBoostClassifier(iterations=500, depth=5, learning_rate=0.03, l2_leaf_reg=4.0, subsample=0.85, verbose=False, random_seed=42)
cb_long.fit(df_train[all_feature_candidates], df_train["target_long"])

cb_short = CatBoostClassifier(iterations=500, depth=5, learning_rate=0.03, l2_leaf_reg=4.0, subsample=0.85, verbose=False, random_seed=42)
cb_short.fit(df_train[all_feature_candidates], df_train["target_short"])

# In-Sample Feature Importance
imp_long = cb_long.get_feature_importance(type="PredictionValuesChange")
imp_short = cb_short.get_feature_importance(type="PredictionValuesChange")

# Out-of-Sample SHAP Values
oos_pool = Pool(df_oos[all_feature_candidates])
shap_long = np.abs(cb_long.get_feature_importance(oos_pool, type="ShapValues")[:, :-1]).mean(axis=0)
shap_short = np.abs(cb_short.get_feature_importance(oos_pool, type="ShapValues")[:, :-1]).mean(axis=0)

print("\n" + "=" * 115)
print("     [3/3] EMPIRICAL FEATURE IMPORTANCE & OOS SHAP IMPACT AUDIT     ")
print("=" * 115)

audit_df = pd.DataFrame({
    "Feature Name": all_feature_candidates,
    "Long Imp (%)": imp_long,
    "Long OOS SHAP": shap_long,
    "Short Imp (%)": imp_short,
    "Short OOS SHAP": shap_short
}).sort_values(by="Short Imp (%)", ascending=False)

audit_df["Long Imp (%)"] = audit_df["Long Imp (%)"].map(lambda x: f"{x:>5.2f}%")
audit_df["Long OOS SHAP"] = audit_df["Long OOS SHAP"].map(lambda x: f"{x:>7.4f}")
audit_df["Short Imp (%)"] = audit_df["Short Imp (%)"].map(lambda x: f"{x:>5.2f}%")
audit_df["Short OOS SHAP"] = audit_df["Short OOS SHAP"].map(lambda x: f"{x:>7.4f}")

print(audit_df.to_string(index=False))
print("=" * 115)
