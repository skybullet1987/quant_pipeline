#!/usr/bin/env python3
import os
import joblib
import pandas as pd
from hyperliquid.info import Info
from google.cloud import bigquery
from catboost import CatBoostClassifier, Pool
from dotenv import load_dotenv

load_dotenv()

MASTER_ADDR = os.getenv("HYPERLIQUID_MASTER_ADDRESS", "0x9703B71686219D34869e8FB89a93263f9e0d50A5")
API_URL = "https://api.hyperliquid-testnet.xyz"
PROJECT_ID = "parnasa-498503"
PROD_MODELS_DIR = "production_models" if os.path.exists("production_models") else "."

print("\n" + "=" * 80)
print("             HYPERLIQUID PRE-FLIGHT AUDIT & SYSTEM VERIFICATION")
print("=" * 80)

# 1. Hyperliquid Balance Check
info = Info(API_URL, skip_ws=True)
user_state = info.user_state(MASTER_ADDR)
spot_state = info.spot_user_state(MASTER_ADDR)

perp_equity = float(user_state.get("marginSummary", {}).get("accountValue", 0.0))
margin_used = float(user_state.get("marginSummary", {}).get("totalMarginUsed", 0.0))

spot_usdc = 0.0
for b in spot_state.get("balances", []):
    if b.get("coin") == "USDC":
        spot_usdc = float(b.get("total", 0.0))

total_equity = perp_equity if perp_equity > 0 else spot_usdc
positions = [p["position"] for p in user_state.get("assetPositions", []) if float(p["position"]["szi"]) != 0]

print(f"\n[CHECK 1/3] Hyperliquid Wallet State ({MASTER_ADDR[:8]}...{MASTER_ADDR[-4:]}):")
print(f"  -> Perp Account Value : ${perp_equity:,.2f}")
print(f"  -> Spot USDC Balance  : ${spot_usdc:,.2f}")
print(f"  -> Total Usable Equity: ${total_equity:,.2f}")
print(f"  -> Active Positions   : {len(positions)}")

with open(".peak_equity.txt", "w") as f:
    f.write(str(total_equity))

# 2. BigQuery Scoring Pipeline
print("\n[CHECK 2/3] Querying BigQuery Feature Store & ML Pipeline...")
client = bigquery.Client(project=PROJECT_ID)
query = f"""
    SELECT 
        f.*, 
        t.tfm_ret_24h, t.tfm_ret_72h, t.tfm_slope, t.tfm_uncertainty, t.tfm_residual_24h, t.tfm_conviction_delta,
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
    WHERE f.timestamp = (SELECT MAX(timestamp) FROM `{PROJECT_ID}.market_data.fct_4h_features_tbm`)
"""
df = client.query(query).to_dataframe()

hmm_model = joblib.load(f"{PROD_MODELS_DIR}/hmm_macro.pkl")
hmm_scaler = joblib.load(f"{PROD_MODELS_DIR}/hmm_scaler.pkl")
hmm_feats = joblib.load(f"{PROD_MODELS_DIR}/hmm_feature_names.pkl")
canonical_order = joblib.load(f"{PROD_MODELS_DIR}/hmm_canonical_order.pkl")
cb_long = CatBoostClassifier().load_model(f"{PROD_MODELS_DIR}/regime_1_long_expert.cbm")
cb_short = CatBoostClassifier().load_model(f"{PROD_MODELS_DIR}/regime_2_short_expert.cbm")
cal_l = joblib.load(f"{PROD_MODELS_DIR}/meta_calibrator_long.pkl")
cal_s = joblib.load(f"{PROD_MODELS_DIR}/meta_calibrator_short.pkl")
all_cat_cols = joblib.load(f"{PROD_MODELS_DIR}/cat_cols.pkl")
cat_set = set(all_cat_cols)

for c in hmm_feats:
    df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

scaled_x = hmm_scaler.transform(df[hmm_feats])
probs = hmm_model.predict_proba(scaled_x)[:, canonical_order]
df["p_chop"] = probs[:, 0]
df["regime"] = probs.argmax(axis=1).astype(str)

feats_l = cb_long.feature_names_
feats_s = cb_short.feature_names_

for c in set(feats_l + feats_s):
    if c not in df.columns:
        df[c] = "missing" if c in cat_set else 0.0
    elif c in cat_set:
        df[c] = df[c].astype(str).fillna("missing")
    else:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

pool_l = Pool(df[feats_l], cat_features=[c for c in feats_l if c in cat_set])
pool_s = Pool(df[feats_s], cat_features=[c for c in feats_s if c in cat_set])

raw_pl = cb_long.predict_proba(pool_l)[:, 1]
raw_ps = cb_short.predict_proba(pool_s)[:, 1]

df["p_long"] = cal_l.predict(raw_pl) if hasattr(cal_l, "predict") else raw_pl
df["p_short"] = cal_s.predict(raw_ps) if hasattr(cal_s, "predict") else raw_ps
print(f"  [PASS] Scored {len(df)} assets successfully.")

# 3. Position Sizing & ATR Bracket Payloads
print(f"\n[CHECK 3/3] Sizing & Bracket Triggers on Live ${total_equity:,.2f} Capital:")
meta = info.meta()
sz_decimals_map = {asset["name"]: asset["szDecimals"] for asset in meta.get("universe", [])}
max_lev_map = {asset["name"]: asset["maxLeverage"] for asset in meta.get("universe", [])}

slot_cap = total_equity / 5.0
print(f"  -> Max 5 Slots        : ${slot_cap:,.2f} per slot")
print(f"  -> 60% Margin Cap Pool: ${total_equity * 0.60:,.2f}")

print("\n--- APPROVED CANDIDATES BRACKET PAYLOAD ---")
count = 0
for _, row in df.iterrows():
    coin = str(row["ticker"]).replace("USDT", "").replace("USD", "").upper()
    pl, ps, pc, reg = float(row["p_long"]), float(row["p_short"]), float(row["p_chop"]), str(row["regime"])
    px = float(row.get("close", row.get("close_price", 1.0)))
    atr = float(row.get("atr_14", row.get("atr_20", px * 0.02)))
    if atr <= 0: atr = px * 0.02

    l_pass = (pl >= 0.58 and reg != "2")
    s_pass = (ps >= 0.52 and reg != "1")
    chop_pass = (pc < 0.50)

    if not chop_pass or (not l_pass and not s_pass):
        continue

    is_buy = l_pass and (not s_pass or pl >= ps)
    side = "BUY" if is_buy else "SELL"
    k_frac = 0.35 if is_buy else 0.75
    lev = min(max_lev_map.get(coin, 10.0), 6.0 if is_buy else 10.0)
    
    target_margin = slot_cap * k_frac
    notional = target_margin * lev
    sz_dec = sz_decimals_map.get(coin, 2)
    raw_sz = notional / px
    sz = int(round(raw_sz)) if sz_dec == 0 else round(raw_sz, sz_dec)

    tp_px = round(px + (1.5 * atr) if is_buy else px - (1.5 * atr), 4)
    sl_px = round(px - (1.5 * atr) if is_buy else px + (1.5 * atr), 4)

    count += 1
    print(f"  • {coin:<8} | {side:<4} | Lev: {lev:>2.0f}x | Size: {sz} | Entry: ${px:.4f} | TP: ${tp_px:.4f} | SL: ${sl_px:.4f} | Margin: ${target_margin:.2f}")

if count == 0:
    print("  [INFO] No candidates passed strict alpha & chop hurdles this cycle.")

print("\n" + "=" * 80)
print("     [SUCCESS] PRE-FLIGHT AUDIT PASSED")
print("=" * 80 + "\n")
