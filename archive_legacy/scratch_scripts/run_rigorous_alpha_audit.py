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

TP_MULT = 2.6
SL_MULT = 1.4
HOLD_BARS = 8
FEE_BPS = 12.0
TOTAL_DAYS = 270
OOS_DAYS = 90

print("--> Pulling 270 days of features from BigQuery...")
client = bigquery.Client(project=PROJECT_ID)
query = f"""
    SELECT 
        f.*,
        COALESCE(t.tfm_ret_24h, 0.0) AS tfm_ret_24h, 
        COALESCE(t.tfm_slope, 0.0) AS tfm_slope,
        COALESCE(l.rank_liq_intensity, 0) AS rank_liq_intensity
    FROM `{PROJECT_ID}.market_data.fct_4h_features_tbm` f
    LEFT JOIN `{PROJECT_ID}.market_data.fct_timesfm_features` t 
        ON f.timestamp = t.timestamp AND f.ticker = t.ticker
    LEFT JOIN `{PROJECT_ID}.market_data.fct_liquidation_features` l 
        ON f.timestamp = l.timestamp AND f.ticker = l.ticker
    WHERE f.timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {TOTAL_DAYS} DAY)
    ORDER BY f.timestamp ASC, f.ticker ASC
"""
df = client.query(query).to_dataframe()
df["timestamp"] = pd.to_datetime(df["timestamp"])

if "open" not in df.columns: df["open"] = df["close"].shift(1).fillna(df["close"])
if "atr" not in df.columns:
    df["atr"] = df["atr_20"].fillna(df["close"] * 0.02) if "atr_20" in df.columns else df["close"] * 0.02

print("--> Generating model predictions...")
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
df["p_chop"] = probs[:, 0]
df["regime"] = probs.argmax(axis=1).astype(str)

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
cutoff_idx = len(unique_bars) - int((OOS_DAYS / TOTAL_DAYS) * len(unique_bars))
train_bars = set(unique_bars[:cutoff_idx])
oos_bars = set(unique_bars[cutoff_idx:])

keep = ["ticker", "open", "high", "low", "close", "atr", "p_long", "p_short", "p_chop", "regime", "timestamp"]
dict_bars = {ts: {r["ticker"]: r for r in df[df["timestamp"] == ts][keep].to_dict("records")} for ts in unique_bars}

records = []
print("--> Executing exact-path barrier resolution with dual-touch path detection & MAE/MFE profiling...")

for b_idx in range(len(unique_bars) - HOLD_BARS):
    ts = unique_bars[b_idx]
    is_oos = ts in oos_bars
    b_dict = dict_bars[ts]

    for sym, r in b_dict.items():
        px, atr = r["close"], r["atr"]
        pl, ps = r["p_long"], r["p_short"]
        if px <= 0 or atr <= 0: continue

        tp_l, sl_l = px + (TP_MULT * atr), px - (SL_MULT * atr)
        tp_s, sl_s = px - (TP_MULT * atr), px + (SL_MULT * atr)

        # Forward tracking variables
        exit_px_l, exit_type_l = px, "TIME"
        exit_px_s, exit_type_s = px, "TIME"
        max_fav_l, max_adv_l = 0.0, 0.0
        max_fav_s, max_adv_s = 0.0, 0.0

        # Exact Path Simulation across 8-bar horizon
        resolved_l, resolved_s = False, False

        for f_idx in range(b_idx + 1, b_idx + 1 + HOLD_BARS):
            f_ts = unique_bars[f_idx]
            f_r = dict_bars[f_ts].get(sym)
            if not f_r: continue
            
            f_o, f_h, f_l, f_c = f_r["open"], f_r["high"], f_r["low"], f_r["close"]

            # Track MFE / MAE in units of ATR
            fav_l = (f_h - px) / atr
            adv_l = (px - f_l) / atr
            max_fav_l = max(max_fav_l, fav_l)
            max_adv_l = max(max_adv_l, adv_l)

            fav_s = (px - f_l) / atr
            adv_s = (f_h - px) / atr
            max_fav_s = max(max_fav_s, fav_s)
            max_adv_s = max(max_adv_s, adv_s)

            # Long Barrier Resolution
            if not resolved_l:
                hit_tp = (f_h >= tp_l)
                hit_sl = (f_l <= sl_l)

                if hit_tp and hit_sl:
                    # Intrabar proximity resolution: was Open closer to TP or SL?
                    if abs(f_o - tp_l) <= abs(f_o - sl_l):
                        exit_px_l, exit_type_l, resolved_l = tp_l, "TP", True
                    else:
                        exit_px_l, exit_type_l, resolved_l = sl_l, "SL", True
                elif hit_tp:
                    exit_px_l, exit_type_l, resolved_l = tp_l, "TP", True
                elif hit_sl:
                    exit_px_l, exit_type_l, resolved_l = sl_l, "SL", True
                else:
                    exit_px_l = f_c

            # Short Barrier Resolution
            if not resolved_s:
                hit_tp = (f_l <= tp_s)
                hit_sl = (f_h >= sl_s)

                if hit_tp and hit_sl:
                    if abs(f_o - tp_s) <= abs(f_o - sl_s):
                        exit_px_s, exit_type_s, resolved_s = tp_s, "TP", True
                    else:
                        exit_px_s, exit_type_s, resolved_s = sl_s, "SL", True
                elif hit_tp:
                    exit_px_s, exit_type_s, resolved_s = tp_s, "TP", True
                elif hit_sl:
                    exit_px_s, exit_type_s, resolved_s = sl_s, "SL", True
                else:
                    exit_px_s = f_c

        ret_l = ((exit_px_l - px) / px) - (FEE_BPS / 10000.0)
        ret_s = ((px - exit_px_s) / px) - (FEE_BPS / 10000.0)

        records.append({
            "ticker": sym, "timestamp": ts, "is_oos": is_oos,
            "regime": r["regime"], "p_long": pl, "p_short": ps,
            "ret_l": ret_l, "type_l": exit_type_l, "mfe_l": max_fav_l, "mae_l": max_adv_l,
            "ret_s": ret_s, "type_s": exit_type_s, "mfe_s": max_fav_s, "mae_s": max_adv_s
        })

df_res = pd.DataFrame(records)
bins = [0.0, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 1.00]
df_res["p_long_bin"] = pd.cut(df_res["p_long"], bins=bins)
df_res["p_short_bin"] = pd.cut(df_res["p_short"], bins=bins)

def summarize_expectancy(df_sub, side="l"):
    p_col = f"p_{'long' if side=='l' else 'short'}_bin"
    ret_col = f"ret_{side}"
    type_col = f"type_{side}"
    mfe_col = f"mfe_{side}"
    mae_col = f"mae_{side}"

    summary = df_sub.groupby(p_col, observed=False).agg(
        N=(ret_col, "count"),
        EV_bps=(ret_col, lambda x: f"{x.mean()*10000:>+6.1f} bps"),
        PF=(ret_col, lambda x: round(x[x > 0].sum() / max(1e-4, abs(x[x <= 0].sum())), 2)),
        TP_rate=(type_col, lambda x: f"{(x=='TP').mean()*100:4.1f}%"),
        SL_rate=(type_col, lambda x: f"{(x=='SL').mean()*100:4.1f}%"),
        Time_rate=(type_col, lambda x: f"{(x=='TIME').mean()*100:4.1f}%"),
        Mean_MFE=(mfe_col, lambda x: f"{x.mean():.2f}"),
        Mean_MAE=(mae_col, lambda x: f"{x.mean():.2f}")
    )
    return summary

print("\n" + "=" * 105)
print("             1. OUT-OF-SAMPLE (OOS ONLY) UNLEVERED EXPECTANCY & MONOTONICITY             ")
print("=" * 105)
oos_df = df_res[df_res["is_oos"]]
print("\n[LONG EXPERT - OOS ONLY]:")
print(summarize_expectancy(oos_df, "l"))

print("\n[SHORT EXPERT - OOS ONLY]:")
print(summarize_expectancy(oos_df, "s"))

print("\n" + "=" * 105)
print("             2. REGIME-CONDITIONED EXPECTANCY (OOS ONLY: BULL vs CHOP vs BEAR)             ")
print("=" * 105)
for reg, reg_name in [("0", "BULL (0)"), ("1", "CHOP (1)"), ("2", "BEAR (2)")]:
    sub = oos_df[oos_df["regime"] == reg]
    print(f"\n--- REGIME {reg_name} (N={len(sub):,}) ---")
    ev_l = sub["ret_l"].mean() * 10000
    ev_s = sub["ret_s"].mean() * 10000
    pf_l = sub["ret_l"][sub["ret_l"] > 0].sum() / max(1e-4, abs(sub["ret_l"][sub["ret_l"] <= 0].sum()))
    pf_s = sub["ret_s"][sub["ret_s"] > 0].sum() / max(1e-4, abs(sub["ret_s"][sub["ret_s"] <= 0].sum()))
    print(f"  Unconditional Long EV : {ev_l:>+6.1f} bps | PF: {pf_l:.2f} | MFE: {sub['mfe_l'].mean():.2f} ATR | MAE: {sub['mae_l'].mean():.2f} ATR")
    print(f"  Unconditional Short EV: {ev_s:>+6.1f} bps | PF: {pf_s:.2f} | MFE: {sub['mfe_s'].mean():.2f} ATR | MAE: {sub['mae_s'].mean():.2f} ATR")
    
    # Conditional high conviction
    l_high = sub[sub["p_long"] >= 0.58]
    s_high = sub[sub["p_short"] >= 0.50]
    if len(l_high) > 0:
        print(f"  High-Conviction Long (p>=0.58, N={len(l_high)}): EV = {l_high['ret_l'].mean()*10000:>+6.1f} bps | PF = {l_high['ret_l'][l_high['ret_l']>0].sum()/max(1e-4, abs(l_high['ret_l'][l_high['ret_l']<=0].sum())):.2f}")
    if len(s_high) > 0:
        print(f"  High-Conviction Short (p>=0.50, N={len(s_high)}): EV = {s_high['ret_s'].mean()*10000:>+6.1f} bps | PF = {s_high['ret_s'][s_high['ret_s']>0].sum()/max(1e-4, abs(s_high['ret_s'][s_high['ret_s']<=0].sum())):.2f}")

print("=" * 105)
