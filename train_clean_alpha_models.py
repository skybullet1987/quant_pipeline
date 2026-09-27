import os
import shutil
import joblib
import pandas as pd
import numpy as np
from catboost import CatBoostClassifier, Pool
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "parnasa-498503")
MODELS_DIR = "models/prod"
TOTAL_DAYS = 365
OOS_DAYS = 90
HOLD_BARS = 8

os.makedirs(MODELS_DIR, exist_ok=True)

print("=" * 90)
print("       PHASE 1: EXTRACTING COMPLETE HISTORICAL UNIVERSE FROM BIGQUERY       ")
print("=" * 90)

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
if "asset" not in df.columns and "ticker" in df.columns: df["asset"] = df["ticker"]
if "open" not in df.columns or df["open"].isnull().all(): df["open"] = df.groupby("asset")["close"].shift(1).fillna(df["close"])

# Volatility & Benchmark alignment
if "atr_20" in df.columns: df["atr"] = df["atr_20"].fillna(df["close"] * 0.02)
elif "atr" in df.columns: df["atr"] = df["atr"].fillna(df["close"] * 0.02)
else: df["atr"] = df["close"] * 0.02

print(f"--> Extracted {len(df):,} total 4H bar records across {df['asset'].nunique()} assets.")

print("\n" + "=" * 90)
print("       PHASE 2: COMPUTING STRUCTURAL SQUEEZE & ABSORPTION FEATURES         ")
print("=" * 90)

df["ema_20"] = df.groupby("asset")["close"].transform(lambda x: x.ewm(span=20, adjust=False).mean())
df["dist_ema20_atr"] = (df["close"] - df["ema_20"]) / (df["atr"] + 1e-8)

# Bollinger Band Squeeze (40-period lookback percentile)
sma_20 = df.groupby("asset")["close"].transform(lambda x: x.rolling(20, min_periods=5).mean())
std_20 = df.groupby("asset")["close"].transform(lambda x: x.rolling(20, min_periods=5).std().fillna(0.0))
bb_upper = sma_20 + 2.0 * std_20
bb_lower = sma_20 - 2.0 * std_20
df["bbw"] = (bb_upper - bb_lower) / (sma_20 + 1e-8)

roll_min = df.groupby("asset")["bbw"].transform(lambda x: x.rolling(40, min_periods=10).min())
roll_max = df.groupby("asset")["bbw"].transform(lambda x: x.rolling(40, min_periods=10).max())
df["bbw_pct_40"] = ((df["bbw"] - roll_min) / (roll_max - roll_min + 1e-8)).fillna(0.50).clip(0.0, 1.0)

df["mom_24h"] = df.groupby("asset")["close"].transform(lambda x: x.pct_change(6).fillna(0.0))
if "funding_rate" in df.columns: df["funding_annual"] = df["funding_rate"].fillna(0.0) * 24.0 * 365.0
else: df["funding_annual"] = 0.0

print("\n" + "=" * 90)
print("       PHASE 3: GENERATING DRAWDOWN-PENALIZED TRIPLE BARRIER LABELS       ")
print("=" * 90)

# Pre-index bars for lookahead simulation
unique_bars = sorted(df["timestamp"].unique())
bar_map = {ts: df[df["timestamp"] == ts].set_index("asset").to_dict("index") for ts in unique_bars}

# Target barrier parameters
LONG_TP, LONG_SL, LONG_MAX_MAE = 2.6, 1.3, 0.75     # Target +2.6x ATR, no retracement > 0.75x ATR
SHORT_TP, SHORT_SL, SHORT_MAX_MAE = 1.8, 1.1, 0.65  # Target -1.8x ATR, no bounce > 0.65x ATR

records = []
print("--> Generating exact-path labels with MAE penalty filtering...")

for b_idx in range(len(unique_bars) - HOLD_BARS):
    ts = unique_bars[b_idx]
    b_dict = bar_map[ts]

    for sym, r in b_dict.items():
        px, atr = r["close"], r["atr"]
        if px <= 0 or atr <= 0: continue

        tp_l, sl_l = px + (LONG_TP * atr), px - (LONG_SL * atr)
        tp_s, sl_s = px - (SHORT_TP * atr), px + (SHORT_SL * atr)

        hit_tp_l, hit_sl_l = False, False
        hit_tp_s, hit_sl_s = False, False
        max_mae_l, max_mae_s = 0.0, 0.0

        for f_idx in range(b_idx + 1, b_idx + 1 + HOLD_BARS):
            f_ts = unique_bars[f_idx]
            f_r = bar_map[f_ts].get(sym)
            if not f_r: continue
            
            f_h, f_l = f_r["high"], f_r["low"]

            # Track adverse excursion in ATR units
            max_mae_l = max(max_mae_l, (px - f_l) / atr)
            max_mae_s = max(max_mae_s, (f_h - px) / atr)

            # Long barrier path
            if not hit_tp_l and not hit_sl_l:
                if f_l <= sl_l: hit_sl_l = True
                elif f_h >= tp_l: hit_tp_l = True

            # Short barrier path
            if not hit_tp_s and not hit_sl_s:
                if f_h >= sl_s: hit_sl_s = True
                elif f_l <= tp_s: hit_tp_s = True

        # STRICT DRAWDOWN PENALIZATION: Label = 1 ONLY if TP was hit and MAE stayed within bounds
        label_long = 1 if (hit_tp_l and max_mae_l <= LONG_MAX_MAE) else 0
        label_short = 1 if (hit_tp_s and max_mae_s <= SHORT_MAX_MAE) else 0

        records.append({
            "timestamp": ts, "asset": sym,
            "target_long": label_long,
            "target_short": label_short
        })

df_targets = pd.DataFrame(records)
df = df.merge(df_targets, on=["timestamp", "asset"], how="inner")

print(f"--> Label Distribution (Clean Dataset):")
print(f"    Positive Longs : {df['target_long'].mean()*100:.2f}% (N = {df['target_long'].sum():,})")
print(f"    Positive Shorts: {df['target_short'].mean()*100:.2f}% (N = {df['target_short'].sum():,})")

print("\n" + "=" * 90)
print("       PHASE 4: TRAINING REGIME-PARTITIONED CATBOOST ALPHA EXPERTS       ")
print("=" * 90)

# Load macro HMM
hmm_model = joblib.load(f"{MODELS_DIR}/hmm_macro.pkl")
hmm_scaler = joblib.load(f"{MODELS_DIR}/hmm_scaler.pkl")
hmm_feats = joblib.load(f"{MODELS_DIR}/hmm_feature_names.pkl")
canonical_order = joblib.load(f"{MODELS_DIR}/hmm_canonical_order.pkl")

for c in hmm_feats: df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0) if c in df.columns else 0.0
probs = hmm_model.predict_proba(hmm_scaler.transform(df[hmm_feats]))[:, canonical_order]
df["regime"] = probs.argmax(axis=1).astype(str)

# Time-Purged Split (Last 90 days strictly held out for OOS validation)
cutoff_date = unique_bars[-1] - pd.Timedelta(days=OOS_DAYS)
df_train = df[df["timestamp"] < cutoff_date].copy()
df_oos = df[df["timestamp"] >= cutoff_date].copy()

print(f"--> Split Breakdown:")
print(f"    In-Sample Training : {len(df_train):,} rows ({df_train['timestamp'].min().strftime('%Y-%m-%d')} to {df_train['timestamp'].max().strftime('%Y-%m-%d')})")
print(f"    Out-of-Sample Hold : {len(df_oos):,} rows ({df_oos['timestamp'].min().strftime('%Y-%m-%d')} to {df_oos['timestamp'].max().strftime('%Y-%m-%d')})")

# Feature specification (purged of raw price chasing)
feature_cols = [
    "dist_ema20_atr", "bbw_pct_40", "mom_24h", "funding_annual",
    "tfm_ret_24h", "tfm_slope", "rank_liq_intensity"
]
# Include any existing engineered indicators if available
for col in ["rsi_14", "vol_expansion_ratio", "market_breadth_sma20", "adx_14"]:
    if col in df.columns: feature_cols.append(col)

for c in feature_cols:
    df_train[c] = pd.to_numeric(df_train[c], errors="coerce").fillna(0.0)
    df_oos[c] = pd.to_numeric(df_oos[c], errors="coerce").fillna(0.0)

print(f"--> Features Selected for Training ({len(feature_cols)} total): {feature_cols}")

# Train models for Regimes 0 (Bull), 1 (Chop), 2 (Bear)
for r in [0, 1, 2]:
    r_str = str(r)
    train_sub = df_train[df_train["regime"] == r_str]
    if len(train_sub) < 500:
        print(f"--> Insufficient samples for Regime {r_str}, using pooled fallback.")
        train_sub = df_train

    # Calculate class weights to balance rare positive breakout events
    w_long_pos = (len(train_sub) - train_sub["target_long"].sum()) / max(1, train_sub["target_long"].sum())
    w_short_pos = (len(train_sub) - train_sub["target_short"].sum()) / max(1, train_sub["target_short"].sum())

    # Long Expert
    cb_long = CatBoostClassifier(
        iterations=600, learning_rate=0.03, depth=5,
        scale_pos_weight=min(4.0, max(1.0, w_long_pos * 0.4)),
        eval_metric="Logloss", random_seed=42, verbose=False
    )
    cb_long.fit(train_sub[feature_cols], train_sub["target_long"])
    cb_long.save_model(f"{MODELS_DIR}/regime_{r}_long_expert.cbm")

    # Short Expert
    cb_short = CatBoostClassifier(
        iterations=600, learning_rate=0.03, depth=5,
        scale_pos_weight=min(4.0, max(1.0, w_short_pos * 0.4)),
        eval_metric="Logloss", random_seed=42, verbose=False
    )
    cb_short.fit(train_sub[feature_cols], train_sub["target_short"])
    cb_short.save_model(f"{MODELS_DIR}/regime_{r}_short_expert.cbm")

    print(f"--> Successfully trained & saved Regime {r_str} Long and Short Experts.")

print("\n" + "=" * 90)
print("       PHASE 5: OUT-OF-SAMPLE (OOS) MONOTONICITY & EXPECTANCY AUDIT        ")
print("=" * 90)

# Score OOS dataset
df_oos["p_long"], df_oos["p_short"] = 0.50, 0.50
for r in [0, 1, 2]:
    r_str = str(r)
    sub_idx = df_oos[df_oos["regime"] == r_str].index
    if len(sub_idx) == 0: continue
    
    ml = CatBoostClassifier().load_model(f"{MODELS_DIR}/regime_{r}_long_expert.cbm")
    ms = CatBoostClassifier().load_model(f"{MODELS_DIR}/regime_{r}_short_expert.cbm")
    
    df_oos.loc[sub_idx, "p_long"] = ml.predict_proba(df_oos.loc[sub_idx, feature_cols])[:, 1]
    df_oos.loc[sub_idx, "p_short"] = ms.predict_proba(df_oos.loc[sub_idx, feature_cols])[:, 1]

# Realized 8-bar forward return audit
df_oos["fwd_ret_long"] = (df_oos.groupby("asset")["close"].shift(-HOLD_BARS) - df_oos["close"]) / df_oos["close"]
df_oos["fwd_ret_short"] = -df_oos["fwd_ret_long"]
df_oos = df_oos.dropna(subset=["fwd_ret_long"])

bins = [0.0, 0.35, 0.45, 0.55, 0.65, 1.00]
df_oos["p_long_bin"] = pd.cut(df_oos["p_long"], bins=bins)
df_oos["p_short_bin"] = pd.cut(df_oos["p_short"], bins=bins)

print("\n[RETRAINED LONG EXPERT: OOS REALIZED EXPECTANCY BY DECILE]")
l_summary = df_oos.groupby("p_long_bin", observed=False).agg(
    N=("fwd_ret_long", "count"),
    Win_Rate=("target_long", lambda x: f"{x.mean()*100:.1f}%"),
    Avg_EV_bps=("fwd_ret_long", lambda x: f"{x.mean()*10000:>+6.1f} bps"),
    Profit_Factor=("fwd_ret_long", lambda x: round(x[x > 0].sum() / max(1e-4, abs(x[x <= 0].sum())), 2))
)
print(l_summary)

print("\n[RETRAINED SHORT EXPERT: OOS REALIZED EXPECTANCY BY DECILE]")
s_summary = df_oos.groupby("p_short_bin", observed=False).agg(
    N=("fwd_ret_short", "count"),
    Win_Rate=("target_short", lambda x: f"{x.mean()*100:.1f}%"),
    Avg_EV_bps=("fwd_ret_short", lambda x: f"{x.mean()*10000:>+6.1f} bps"),
    Profit_Factor=("fwd_ret_short", lambda x: round(x[x > 0].sum() / max(1e-4, abs(x[x <= 0].sum())), 2))
)
print(s_summary)
print("=" * 90)
