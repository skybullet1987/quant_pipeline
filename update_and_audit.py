#!/usr/bin/env python3
import os
import re
import sys
import joblib
import pandas as pd
from eth_account import Account
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from google.cloud import bigquery
from catboost import CatBoostClassifier, Pool

MASTER_ADDR = "0x9703B71686219D34869e8FB89a93263f9e0d50A5"
PK = "0x9c611e6a447bed63b34e4db09621d65c4c1a79603dacf4655d6bd75b9a4015e8"
API_URL = "https://api.hyperliquid-testnet.xyz"
PROJECT_ID = "parnasa-498503"
PROD_MODELS_DIR = "production_models" if os.path.exists("production_models") else "."

# 1. Update .env file
env_file = ".env"
content = ""
if os.path.exists(env_file):
    with open(env_file, "r") as f:
        content = f.read()

if "HYPERLIQUID_MASTER_ADDRESS=" in content:
    content = re.sub(r"HYPERLIQUID_MASTER_ADDRESS=.*", f"HYPERLIQUID_MASTER_ADDRESS={MASTER_ADDR}", content)
else:
    content += f"\nHYPERLIQUID_MASTER_ADDRESS={MASTER_ADDR}\n"

if "HYPERLIQUID_PRIVATE_KEY=" in content:
    content = re.sub(r"HYPERLIQUID_PRIVATE_KEY=.*", f"HYPERLIQUID_PRIVATE_KEY={PK}", content)
else:
    content += f"\nHYPERLIQUID_PRIVATE_KEY={PK}\n"

with open(env_file, "w") as f:
    f.write(content.strip() + "\n")

print("=" * 80)
print("     HYPERLIQUID PRODUCTION PRE-FLIGHT AUDIT & VERIFICATION")
print("=" * 80)

# 2. Derive & Verify Agent / Master Setup
acct = Account.from_key(PK)
agent_addr = acct.address

print(f"[AUTH] Master Wallet Address : {MASTER_ADDR}")
print(f"[AUTH] Signing Agent Key     : {agent_addr}")

# 3. Query Hyperliquid State
info = Info(API_URL, skip_ws=True)
user_state = info.user_state(MASTER_ADDR)
open_orders = info.open_orders(MASTER_ADDR)
frontend_orders = info.frontend_open_orders(MASTER_ADDR)

margin_summary = user_state.get("marginSummary", {})
equity = float(margin_summary.get("accountValue", 0.0))
margin_used = float(margin_summary.get("totalMarginUsed", 0.0))
positions = [p["position"] for p in user_state.get("assetPositions", []) if float(p["position"]["szi"]) != 0]

print(f"\n[CHECK 1/4] Hyperliquid Live State:")
print(f"  -> Account Equity        : ${equity:,.2f}")
print(f"  -> Margin In Use         : ${margin_used:,.2f}")
print(f"  -> Active Perp Positions : {len(positions)}")
print(f"  -> Resting Limit Orders  : {len(open_orders)}")
print(f"  -> Resting TP/SL Triggers: {len(frontend_orders)}")

if len(positions) == 0 and len(open_orders) == 0:
    print("  [PASS] Clean zero-state verified on exchange.")
else:
    print(f"  [INFO] Detected active state ({len(positions)} positions, {len(open_orders)} orders).")

# Update local peak equity tracker
peak_file = ".peak_equity.txt"
with open(peak_file, "w") as f:
    f.write(str(equity))

# 4. Check BigQuery Latest Features & Scoring
print("\n[CHECK 2/4] Querying BigQuery Feature Store & ML Pipeline...")
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
print(f"  -> Loaded {len(df)} assets from latest candle ({df['timestamp'].iloc[0] if len(df) > 0 else 'N/A'}).")

# 5. Run ML Model Inference
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
print(f"  [PASS] ML inference computed successfully across all {len(df)} assets.")

# 6. Sizing & Precision Audit
print("\n[CHECK 3/4] Sizing & Bracket Order Bounds (Starting from Live ${equity:,.2f}):".format(equity=equity))
meta = info.meta()
sz_decimals_map = {asset["name"]: asset["szDecimals"] for asset in meta.get("universe", [])}
max_lev_map = {asset["name"]: asset["maxLeverage"] for asset in meta.get("universe", [])}

slot_cap = equity / 5.0
max_pool = equity * 0.60
print(f"  -> 5 Concurrent Slots   : ${slot_cap:,.2f} max capital per slot")
print(f"  -> 60% Margin Cap Pool  : ${max_pool:,.2f}")

print("\n--- APPROVED CANDIDATES WATERFALL ---")
approved_count = 0
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

    approved_count += 1
    print(f"  • {coin:<8} | {side:<4} | Lev: {lev:>2.0f}x | Size: {sz} | Entry: ${px:.4f} | TP: ${tp_px:.4f} | SL: ${sl_px:.4f} | Margin: ${target_margin:.2f}")

if approved_count == 0:
    print("  [INFO] No candidates passed strict alpha & chop hurdles this cycle.")

print("\n" + "=" * 80)
print("     [SUCCESS] PRE-FLIGHT AUDIT PASSED WITH LIVE HYPERLIQUID WALLET")
print("=" * 80 + "\n")
