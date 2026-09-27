import os
import joblib
import pandas as pd
import numpy as np
from catboost import CatBoostClassifier, Pool
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "parnasa-498503")
PROD_MODELS_DIR = "models/prod"

def load_and_cache_dataset(total_days=270, oos_days=90):
    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT 
            f.*,
            COALESCE(t.tfm_ret_24h, 0.0) AS tfm_ret_24h, 
            COALESCE(t.tfm_ret_72h, 0.0) AS tfm_ret_72h, 
            COALESCE(t.tfm_slope, 0.0) AS tfm_slope, 
            COALESCE(t.tfm_uncertainty, 0.0) AS tfm_uncertainty, 
            COALESCE(t.tfm_residual_24h, 0.0) AS tfm_residual_24h, 
            COALESCE(t.tfm_conviction_delta, 0.0) AS tfm_conviction_delta,
            COALESCE(l.total_liq_usd, 0) AS total_liq_usd,
            COALESCE(l.liq_imbalance_ratio, 0) AS liq_imbalance_ratio,
            COALESCE(l.long_liq_accel, 0) AS long_liq_accel,
            COALESCE(l.short_liq_accel, 0) AS short_liq_accel,
            COALESCE(l.rank_liq_intensity, 0) AS rank_liq_intensity
        FROM `{PROJECT_ID}.market_data.fct_4h_features_tbm` f
        LEFT JOIN `{PROJECT_ID}.market_data.fct_timesfm_features` t 
            ON f.timestamp = t.timestamp AND f.ticker = t.ticker
        LEFT JOIN `{PROJECT_ID}.market_data.fct_liquidation_features` l 
            ON f.timestamp = l.timestamp AND f.ticker = l.ticker
        WHERE f.timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {total_days} DAY)
        ORDER BY f.timestamp ASC, f.ticker ASC
    """
    df = client.query(query).to_dataframe()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    
    if "atr" not in df.columns:
        df["atr"] = df["atr_20"].fillna(df["close"] * 0.02) if "atr_20" in df.columns else df["close"] * 0.02
    if "market_breadth" not in df.columns:
        df["market_breadth"] = df["market_breadth_sma20"] if "market_breadth_sma20" in df.columns else 0.50
    if "vol_expansion_ratio" not in df.columns: df["vol_expansion_ratio"] = 1.0
    if "btc_ret_1h" not in df.columns: df["btc_ret_1h"] = 0.0
    if "btc_ret_4h" not in df.columns: df["btc_ret_4h"] = 0.0

    hmm_model = joblib.load(f"{PROD_MODELS_DIR}/hmm_macro.pkl")
    hmm_scaler = joblib.load(f"{PROD_MODELS_DIR}/hmm_scaler.pkl")
    hmm_feats = joblib.load(f"{PROD_MODELS_DIR}/hmm_feature_names.pkl")
    canonical_order = joblib.load(f"{PROD_MODELS_DIR}/hmm_canonical_order.pkl")
    cat_set = set(joblib.load(f"{PROD_MODELS_DIR}/cat_cols.pkl") if os.path.exists(f"{PROD_MODELS_DIR}/cat_cols.pkl") else [])

    models_l, models_s = {}, {}
    for r in [0, 1, 2]:
        lp, sp = f"{PROD_MODELS_DIR}/regime_{r}_long_expert.cbm", f"{PROD_MODELS_DIR}/regime_{r}_short_expert.cbm"
        if os.path.exists(lp): models_l[str(r)] = CatBoostClassifier().load_model(lp)
        if os.path.exists(sp): models_s[str(r)] = CatBoostClassifier().load_model(sp)

    fb_l = models_l.get("1", next(iter(models_l.values()), None))
    fb_s = models_s.get("2", next(iter(models_s.values()), None))

    for c in hmm_feats: df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0) if c in df.columns else 0.0
    probs = hmm_model.predict_proba(hmm_scaler.transform(df[hmm_feats]))[:, canonical_order]
    df["p_chop"], df["regime"], df["hmm_regime"] = probs[:, 0], probs.argmax(axis=1).astype(str), probs.argmax(axis=1).astype(str)

    df["p_long"], df["p_short"] = 0.50, 0.50
    for reg_val, group_idx in df.groupby("regime").groups.items():
        reg_str = str(reg_val)
        sub = df.loc[group_idx].copy()
        ml, ms = models_l.get(reg_str, fb_l), models_s.get(reg_str, fb_s)

        for c in ml.feature_names_:
            if c in ["hmm_regime", "regime"]: sub[c] = reg_str
            elif c in cat_set: sub[c] = sub[c].fillna("missing").astype(str)
            else: sub[c] = pd.to_numeric(sub[c], errors="coerce").fillna(0.0) if c in sub.columns else 0.0
        df.loc[group_idx, "p_long"] = ml.predict_proba(Pool(sub[ml.feature_names_], cat_features=[c for c in ml.feature_names_ if c in cat_set]))[:, 1]

        for c in ms.feature_names_:
            if c in ["hmm_regime", "regime"]: sub[c] = reg_str
            elif c in cat_set: sub[c] = sub[c].fillna("missing").astype(str)
            else: sub[c] = pd.to_numeric(sub[c], errors="coerce").fillna(0.0) if c in sub.columns else 0.0
        df.loc[group_idx, "p_short"] = ms.predict_proba(Pool(sub[ms.feature_names_], cat_features=[c for c in ms.feature_names_ if c in cat_set]))[:, 1]

    unique_bars = sorted(df["timestamp"].unique())
    cutoff = len(unique_bars) - int((oos_days / total_days) * len(unique_bars))
    train_bars, oos_bars = unique_bars[:cutoff], unique_bars[cutoff:]

    keep = ["ticker", "high", "low", "close", "atr", "p_long", "p_short", "p_chop", "regime", "btc_ret_1h", "btc_ret_4h", "market_breadth", "vol_expansion_ratio", "timestamp"]
    df_m = df[keep]

    train_dict = [{r["ticker"]: r for r in df_m[df_m["timestamp"] == ts].to_dict("records")} for ts in train_bars]
    oos_dict = [{r["ticker"]: r for r in df_m[df_m["timestamp"] == ts].to_dict("records")} for ts in oos_bars]

    return train_bars, train_dict, oos_bars, oos_dict
