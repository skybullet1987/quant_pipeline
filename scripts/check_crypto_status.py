import os
import sys
import glob
import json
import datetime
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from eth_account import Account
from hyperliquid.info import Info
from hyperliquid.utils import constants

load_dotenv(os.path.expanduser('~/quant_pipeline/.env'))

private_key = os.getenv("HL_PRIVATE_KEY") or os.getenv("AGENT_PRIVATE_KEY")
if not private_key:
    print("[ERROR] No private key found in ~/quant_pipeline/.env")
    sys.exit(1)

account = Account.from_key(private_key)
wallet_address = os.getenv("HL_WALLET_ADDRESS", account.address)

info = Info(constants.MAINNET_API_URL, skip_ws=True)

print("=" * 80)
print(f"=== HL-3A APEX CRYPTO STATUS AUDIT | WALLET: {wallet_address[:8]}...{wallet_address[-6:]} ===")
print("=" * 80)

# 1. Check Feature Lake & Parquet Recency
parquet_path = os.path.expanduser("~/quant_pipeline/data/lake/features/pit_panel_1h_with_funding.parquet")
if not os.path.exists(parquet_path):
    # Fallback to general parquet store
    alt_files = glob.glob(os.path.expanduser("~/quant_pipeline/**/*.parquet"), recursive=True)
    parquet_path = alt_files[0] if alt_files else None

if parquet_path and os.path.exists(parquet_path):
    mtime = datetime.datetime.fromtimestamp(os.path.getmtime(parquet_path), tz=datetime.timezone.utc)
    print(f"\n[DATA LAKE] Feature store found: {parquet_path}")
    print(f"[DATA LAKE] Last modified: {mtime.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    try:
        df = pd.read_parquet(parquet_path)
        last_epoch = df["timestamp"].max() if "timestamp" in df.columns else "N/A"
        unique_tokens = df["coin"].nunique() if "coin" in df.columns else len(df)
        print(f"[DATA LAKE] Max Timestamp: {last_epoch} | Available Universe Breadth: {unique_tokens} tokens")
    except Exception as e:
        print(f"[WARN] Error parsing parquet metrics: {e}")
else:
    print("\n[DATA LAKE] No active Parquet feature store identified.")

# 2. Check Local Rebalance / Selection Artifacts
state_files = glob.glob(os.path.expanduser("~/quant_pipeline/**/portfolio_state.json"), recursive=True)
rebalance_files = glob.glob(os.path.expanduser("~/quant_pipeline/**/latest_selection.json"), recursive=True)

target_state = rebalance_files[0] if rebalance_files else (state_files[0] if state_files else None)

if target_state and os.path.exists(target_state):
    print(f"\n[SELECTION STATE] Ingesting: {target_state}")
    try:
        with open(target_state, "r") as f:
            state_data = json.load(f)
        
        timestamp = state_data.get("timestamp") or state_data.get("epoch_time", "N/A")
        gated = state_data.get("risk_gated", False)
        gating_reason = state_data.get("gating_reason", "None")
        weights = state_data.get("target_weights", {})
        
        print(f"[SELECTION STATE] Epoch Timestamp : {timestamp}")
        print(f"[SELECTION STATE] Risk Gated       : {gated} (Reason: {gating_reason})")
        print(f"[SELECTION STATE] Active Allocations: {len(weights)} assets")
        
        if weights:
            df_w = pd.DataFrame(list(weights.items()), columns=["Coin", "Weight"]).sort_values("Weight", ascending=False)
            print("\nTop Target Allocations (HRP + Carry Overlay):")
            print(df_w.head(10).to_string(index=False))
    except Exception as e:
        print(f"[WARN] Error parsing selection JSON: {e}")

# 3. Query Live Hyperliquid Clearinghouse Positions
try:
    user_state = info.user_state(wallet_address)
    margin_summary = user_state.get("marginSummary", {})
    account_value = float(margin_summary.get("accountValue", 0))
    total_ntl = float(margin_summary.get("totalNtlPos", 0))
    raw_positions = user_state.get("assetPositions", [])
    
    current_leverage = (total_ntl / account_value) if account_value > 0 else 0.0
    
    print("\n" + "-" * 80)
    print(f"CLEARINGHOUSE SUMMARY: Account Equity: ${account_value:,.2f} | Gross Notional: ${total_ntl:,.2f} | Leverage: {current_leverage:.2f}x")
    print("-" * 80)
    
    active_positions = []
    for pos in raw_positions:
        p = pos.get("position", {})
        szi = float(p.get("szi", 0))
        if szi != 0:
            coin = p.get("coin")
            entry_px = float(p.get("entryPx", 0))
            unrealized_pnl = float(p.get("unrealizedPnl", 0))
            active_positions.append({
                "Coin": coin,
                "Side": "LONG" if szi > 0 else "SHORT",
                "Size": abs(szi),
                "Entry Px": entry_px,
                "Unrealized PnL ($)": unrealized_pnl
            })
            
    if active_positions:
        df_pos = pd.DataFrame(active_positions)
        print(f"Active Live Positions ({len(df_pos)} open):")
        print(df_pos.to_string(index=False))
    else:
        print("Zero open positions on HyperCore. Engine is either in cash preservation mode (risk gated) or awaiting next epoch.")

except Exception as err:
    print(f"[ERROR] Clearinghouse query failed: {err}")

print("=" * 80)
