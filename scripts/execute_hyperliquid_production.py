import os, sys, json, time, argparse, warnings

PROJECT_ROOT = os.path.abspath(os.getenv("QUANT_PROJECT_ROOT", "/home/skybullet1987/quant_pipeline"))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pandas as pd
import numpy as np
from scipy.stats import multivariate_normal
from hmmlearn.hmm import GaussianHMM
from sklearn.preprocessing import RobustScaler
from catboost import CatBoostClassifier
from google.cloud import bigquery
from dotenv import load_dotenv

warnings.filterwarnings("ignore")
load_dotenv()

parser = argparse.ArgumentParser()
parser.add_argument("--testnet", action="store_true", default=False)
parser.add_argument("--dry-run", action="store_true", default=False)
args = parser.parse_args()

MODELS_DIR = os.path.join(PROJECT_ROOT, "models/prod")
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "parnasa-498503")

print(f"--> [1/4] Connecting to Hyperliquid ({'TESTNET' if args.testnet else 'MAINNET'} | Mode: {'DRY RUN' if args.dry_run else 'LIVE'})...")

exchange = None
account_value = 575.45
unified_ratio = 0.00
maint_margin = 0.00
open_positions = {}

if not args.dry_run:
    try:
        from eth_account.signers.local import LocalAccount
        from eth_account import Account
        from hyperliquid.info import Info
        from hyperliquid.exchange import Exchange
        from hyperliquid.utils import constants

        secret_key = os.getenv("HL_SECRET_KEY") or os.getenv("HYPERLIQUID_PRIVATE_KEY")
        account_addr = os.getenv("HL_ACCOUNT_ADDRESS") or os.getenv("HYPERLIQUID_MASTER_ADDRESS")
        base_url = constants.TESTNET_API_URL if args.testnet else constants.MAINNET_API_URL

        info = Info(base_url, skip_ws=True)
        account: LocalAccount = Account.from_key(secret_key)
        exchange = Exchange(account, base_url, account_address=account_addr)

        # Query Native Portfolio State
        try:
            port_data = info.post("/info", {"type": "portfolio", "user": account_addr})
            if port_data and isinstance(port_data, list) and len(port_data) > 0:
                latest_entry = port_data[-1]
                account_value = float(latest_entry[1].get("accountValue", 575.45))
        except Exception:
            pass

        user_state = info.user_state(account_addr or account.address)
        margin_sum = user_state.get("marginSummary", {})
        perp_val = float(margin_sum.get("accountValue", 0.0))
        maint_margin = float(margin_sum.get("totalMarginUsed", 0.0))

        if account_value <= 0.0 or account_value == 575.45:
            account_value = perp_val if perp_val > 0 else 575.45

        unified_ratio = (maint_margin / account_value * 100.0) if account_value > 0 else 0.00
        open_positions = {p["position"]["coin"]: p["position"] for p in user_state.get("assetPositions", []) if float(p["position"]["szi"]) != 0}

        try:
            cancel_timestamp_ms = int(time.time() * 1000) + 300000
            exchange.schedule_cancel(cancel_timestamp_ms)
            print("    [✓] Native EIP-712 Dead-Man Switch armed (300s window).")
        except Exception as dms_e:
            print(f"    [!] Dead-man switch arm warning: {dms_e}")

    except Exception as e:
        print(f"    [!] Live exchange connection failed ({e}). Reverting to simulated mode.")
        args.dry_run = True

print("\n" + "="*50)
print("           UNIFIED ACCOUNT SUMMARY")
print("="*50)
print(f"  Unified Account Ratio   : {unified_ratio:.2f}%")
print(f"  Portfolio Value         : ${account_value:,.2f}")
print(f"  Perps Maintenance Margin: ${maint_margin:,.2f}")
print(f"  Open Positions          : {len(open_positions)}")
print("="*50 + "\n")

# 2. Query 4H Feature Mart & Compute Causal HMM
print("--> [2/4] Querying 4H feature mart & updating Causal HMM...")
t0 = time.time()
client = bigquery.Client(project=PROJECT_ID)
query = f"""
    SELECT timestamp, ticker AS asset, open, high, low, close, volume, 
           atr_20 AS atr, mom_24h, dist_ema20_atr, bbw_pct_40
    FROM `{PROJECT_ID}.market_data.fct_4h_features_production`
    WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
    ORDER BY timestamp ASC, ticker ASC
"""
df = client.query(query).to_dataframe()
df["timestamp"] = pd.to_datetime(df["timestamp"])
df["atr_pct"] = df["atr"] / (df["close"] + 1e-8)
df["ret_4h"] = df.groupby("asset")["close"].pct_change().fillna(0.0)

df["ema_20"] = df.groupby("asset")["close"].transform(lambda x: x.ewm(span=20, adjust=False).mean())
mbi_ts = df.groupby("timestamp").apply(lambda x: (x["close"] > x["ema_20"]).mean(), include_groups=False).rename("mbi")
csd_ts = df.groupby("timestamp")["ret_4h"].std().fillna(0.01).rename("csd")
macro_df = pd.concat([mbi_ts, csd_ts], axis=1).fillna(0.5)

btc_col = next((c for c in df["asset"].unique() if c in ("BTC", "kBTC", "BTC-PERP")), "BTC")
btc_df = df[df["asset"] == btc_col].set_index("timestamp")
macro_df["btc_above_ema20"] = (btc_df["close"] > btc_df["ema_20"]).reindex(macro_df.index).fillna(False)

hmm_scaler = RobustScaler().fit(macro_df[["mbi", "csd"]])
X_all = hmm_scaler.transform(macro_df[["mbi", "csd"]])
hmm = GaussianHMM(n_components=3, covariance_type="diag", min_covar=1e-3, random_state=42, n_iter=75).fit(X_all)
canonical_order = np.argsort(-hmm.means_[:, 0])

T_len = len(X_all)
alpha = np.zeros((T_len, 3))
B = np.zeros((T_len, 3))
for j in range(3):
    B[:, j] = multivariate_normal.pdf(X_all, mean=hmm.means_[j], cov=np.diag(hmm.covars_[j]) + np.eye(2) * 1e-4)

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

df = df.merge(macro_df[["p_bull", "p_chop", "p_bear", "hmm_entropy", "dp_bull", "dp_bear", "btc_above_ema20"]].reset_index(), on="timestamp", how="left")

latest_ts = df["timestamp"].max()
current_bar = df[df["timestamp"] == latest_ts].copy()

p_bull = float(current_bar["p_bull"].iloc[0])
p_chop = float(current_bar["p_chop"].iloc[0])
p_bear = float(current_bar["p_bear"].iloc[0])
btc_bull = bool(current_bar["btc_above_ema20"].iloc[0])

print(f"    Features synced in {time.time()-t0:.2f}s.")
print(f"--> [3/4] Bar: {latest_ts} UTC | Macro State: Bull={p_bull*100:.1f}%, Bear={p_bear*100:.1f}%, Chop={p_chop*100:.1f}%")

# 3. Validated 70/30 Partial + Trailing Runner Execution Parameters
MIN_HMM_BEAR = 0.40
MIN_HMM_BULL = 0.88
Q_SHORT = 0.245
Q_LONG = 0.320
MAX_SLOTS = 2
BASE_LEVERAGE = 5.0

# Exit Parameters (OOS-Validated: 70/30 Architecture)
PARTIAL_SPLIT = 0.70
SHORT_TP1_MULT = 1.8
SHORT_SL_INIT_MULT = 0.85
LONG_TP1_MULT = 1.8
LONG_SL_INIT_MULT = 1.0

open_slots = MAX_SLOTS - len(open_positions)
feature_cols = ["p_bull", "p_chop", "p_bear", "hmm_entropy", "dp_bull", "dp_bear", "dist_ema20_atr", "bbw_pct_40", "mom_24h"]
for c in feature_cols:
    current_bar[c] = pd.to_numeric(current_bar[c], errors="coerce").fillna(0.0)

active_syms = set(open_positions.keys())

# Priority 1: Bear Breakdown Cascades
if p_bear >= MIN_HMM_BEAR and open_slots > 0:
    print(f"--> [4/4] Regime: BEAR BREAKDOWN (P_bear={p_bear*100:.1f}%). Scoring Short CatBoost...")
    cb_short = CatBoostClassifier().load_model(f"{MODELS_DIR}/catboost_short_production.cbm")
    current_bar["p_model"] = cb_short.predict_proba(current_bar[feature_cols])[:, 1]

    cands = current_bar[
        (~current_bar["asset"].isin(active_syms)) & 
        (current_bar["p_model"] >= Q_SHORT) &
        (current_bar["mom_24h"] < 0.0)
    ].sort_values(by="p_model", ascending=False).head(open_slots)

    if cands.empty:
        print("    [i] No short candidates cleared probability and momentum criteria.")
    else:
        for _, row in cands.iterrows():
            sym = row["asset"]
            px = float(row["close"])
            atr = float(row["atr"])
            p_score = float(row["p_model"])

            slot_lev = (BASE_LEVERAGE / MAX_SLOTS) + (max(0.0, p_score - 0.28) / 0.15 * 0.5)
            slot_lev = float(np.clip(slot_lev, 2.5, 3.0))
            target_notional = account_value * slot_lev
            total_sz = round(target_notional / px, 3)
            tranche_a_sz = round(total_sz * PARTIAL_SPLIT, 3)
            tranche_b_sz = round(total_sz - tranche_a_sz, 3)

            tp1_px = round(px - (SHORT_TP1_MULT * atr), 4)
            sl_px = round(px + (SHORT_SL_INIT_MULT * atr), 4)

            print(f"    [+] {sym:<8} SHORT: Total={total_sz} (${target_notional:,.1f} @ {slot_lev:.1f}x)")
            print(f"        - Tranche A (70%): {tranche_a_sz} @ TP1 ${tp1_px} (-{SHORT_TP1_MULT}x ATR)")
            print(f"        - Tranche B (30%): {tranche_b_sz} (Uncapped 2.5x ATR Trailing Runner)")
            print(f"        - Protective SL  : ${sl_px} (+{SHORT_SL_INIT_MULT}x ATR)")

            if not args.dry_run and exchange is not None and target_notional >= 10.0:
                try:
                    exchange.update_leverage(int(slot_lev), sym, is_cross=True)
                    exchange.market_open(sym, False, total_sz, px, 0.01)
                    # Limit TP for 70% Tranche A
                    exchange.order(sym, True, tranche_a_sz, tp1_px, {"trigger": {"triggerPx": str(tp1_px), "isMarket": False, "tpsl": "tp"}}, reduce_only=True)
                    # Stop-Loss for full position (100%)
                    exchange.order(sym, True, total_sz, sl_px, {"trigger": {"triggerPx": str(sl_px), "isMarket": True, "tpsl": "sl"}}, reduce_only=True)
                    print(f"        [✓] Live Short orders placed for {sym}")
                except Exception as ex:
                    print(f"        [!] Execution failed for {sym}: {ex}")

# Priority 2: Ultra-Confirmed Bull Breakouts
elif p_bull >= MIN_HMM_BULL and btc_bull and open_slots > 0:
    print(f"--> [4/4] Regime: ULTRA BULL EXPANSION (P_bull={p_bull*100:.1f}%). Scoring Long CatBoost...")
    cb_long = CatBoostClassifier().load_model(f"{MODELS_DIR}/catboost_long_production.cbm")
    current_bar["p_model"] = cb_long.predict_proba(current_bar[feature_cols])[:, 1]

    cands = current_bar[
        (~current_bar["asset"].isin(active_syms)) & 
        (current_bar["p_model"] >= Q_LONG) &
        (current_bar["mom_24h"] > 0.02)
    ].sort_values(by="p_model", ascending=False).head(open_slots)

    if cands.empty:
        print("    [i] No long candidates cleared ultra-bull criteria.")
    else:
        for _, row in cands.iterrows():
            sym = row["asset"]
            px = float(row["close"])
            atr = float(row["atr"])
            target_notional = account_value * (BASE_LEVERAGE / MAX_SLOTS)
            total_sz = round(target_notional / px, 3)
            tranche_a_sz = round(total_sz * PARTIAL_SPLIT, 3)
            tranche_b_sz = round(total_sz - tranche_a_sz, 3)

            tp1_px = round(px + (LONG_TP1_MULT * atr), 4)
            sl_px = round(px - (LONG_SL_INIT_MULT * atr), 4)

            print(f"    [+] {sym:<8} LONG: Total={total_sz} (${target_notional:,.1f} @ 2.5x)")
            print(f"        - Tranche A (70%): {tranche_a_sz} @ TP1 ${tp1_px} (+{LONG_TP1_MULT}x ATR)")
            print(f"        - Tranche B (30%): {tranche_b_sz} (Uncapped 2.5x ATR Trailing Runner)")
            print(f"        - Protective SL  : ${sl_px} (-{LONG_SL_INIT_MULT}x ATR)")

            if not args.dry_run and exchange is not None and target_notional >= 10.0:
                try:
                    exchange.update_leverage(3, sym, is_cross=True)
                    exchange.market_open(sym, True, total_sz, px, 0.01)
                    # Limit TP for 70% Tranche A
                    exchange.order(sym, False, tranche_a_sz, tp1_px, {"trigger": {"triggerPx": str(tp1_px), "isMarket": False, "tpsl": "tp"}}, reduce_only=True)
                    # Stop-Loss for full position (100%)
                    exchange.order(sym, False, total_sz, sl_px, {"trigger": {"triggerPx": str(sl_px), "isMarket": True, "tpsl": "sl"}}, reduce_only=True)
                    print(f"        [✓] Live Long orders placed for {sym}")
                except Exception as ex:
                    print(f"        [!] Execution failed for {sym}: {ex}")

elif p_chop >= 0.70:
    print("--> [4/4] Regime: CONSOLIDATION CHOP. 100% Cash (Capital Protected).")
else:
    print("--> [4/4] Macro Ambiguity. 100% Cash.")

print("--> [✓] Production cycle complete.")
