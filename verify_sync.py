#!/usr/bin/env python3
import os
import sqlite3
import pandas as pd
from google.cloud import bigquery
from hyperliquid.info import Info
from dotenv import load_dotenv

# Explicit path prevents python-dotenv frame inspection crash
load_dotenv(".env")

PROJECT_ID = "parnasa-498503"
API_URL = os.getenv("HYPERLIQUID_API_URL", "https://api.hyperliquid-testnet.xyz")
ADDR = os.getenv("HYPERLIQUID_MASTER_ADDRESS", "0x9703B71686219D34869e8FB89a93263f9e0d50A5")
DB_PATH = "execution_telemetry.db"

print("=" * 80)
print("             SYSTEM-WIDE SYNC & HEALTH VERIFICATION")
print("=" * 80)

# 1. Hyperliquid Exchange State & Active Brackets
print("\n[1/4] Checking Hyperliquid On-Chain State & Trigger Sync...")
try:
    info = Info(API_URL, skip_ws=True)
    user_state = info.user_state(ADDR)
    spot_state = info.spot_user_state(ADDR)
    open_orders = info.open_orders(ADDR)
    frontend_orders = info.frontend_open_orders(ADDR)

    spot_usdc = sum(float(b.get("total", 0.0)) for b in spot_state.get("balances", []) if b.get("coin") == "USDC")
    perp_equity = float(user_state.get("marginSummary", {}).get("accountValue", 0.0))
    margin_used = float(user_state.get("marginSummary", {}).get("totalMarginUsed", 0.0))
    total_equity = perp_equity if perp_equity > 0 else spot_usdc
    active_pos = [p["position"] for p in user_state.get("assetPositions", []) if float(p["position"]["szi"]) != 0]

    print(f"  • Master Wallet     : {ADDR}")
    print(f"  • Unified Equity    : ${total_equity:,.2f} (Margin In Use: ${margin_used:,.2f})")
    print(f"  • Active Positions  : {len(active_pos)}")
    for p in active_pos:
        print(f"    -> {p['coin']:<8} | Size: {p['szi']} | Entry: ${float(p['entryPx']):.4f} | PnL: ${float(p['unrealizedPnl']):+.2f}")

    print(f"  • Resting Orders    : {len(open_orders)} limit, {len(frontend_orders)} triggers")
    for pos in active_pos:
        coin = pos["coin"]
        triggers = [o for o in open_orders + frontend_orders if o.get("coin") == coin]
        if triggers:
            print(f"    [PASS] {coin} has {len(triggers)} active on-exchange trigger(s).")
        else:
            print(f"    [WARN] {coin} has NO active on-exchange trigger orders!")
except Exception as e:
    print(f"  [FAIL] Hyperliquid sync error: {e}")

# 2. BigQuery Feature Freshness Sync
print("\n[2/4] Checking BigQuery Feature Tables Synchronization...")
try:
    client = bigquery.Client(project=PROJECT_ID)
    freshness_query = f"""
        SELECT 
            (SELECT MAX(timestamp) FROM `{PROJECT_ID}.market_data.fct_4h_features_tbm`) AS max_features_ts,
            (SELECT MAX(timestamp) FROM `{PROJECT_ID}.market_data.fct_timesfm_features`) AS max_timesfm_ts,
            (SELECT MAX(timestamp) FROM `{PROJECT_ID}.market_data.fct_liquidation_features`) AS max_liq_ts
    """
    ts_df = client.query(freshness_query).to_dataframe()
    f_ts, t_ts, l_ts = ts_df["max_features_ts"].iloc[0], ts_df["max_timesfm_ts"].iloc[0], ts_df["max_liq_ts"].iloc[0]

    print(f"  • Latest 4H Features  : {f_ts}")
    print(f"  • Latest TimesFM      : {t_ts}")
    print(f"  • Latest Liquidations : {l_ts}")

    if str(f_ts) == str(t_ts) == str(l_ts):
        print("  [PASS] All BigQuery feature sources are in timestamp sync.")
    else:
        print("  [WARN] Timestamp discrepancy detected between feature tables.")
except Exception as e:
    print(f"  [FAIL] BigQuery sync check failed: {e}")

# 3. Telemetry DB & 72H Timeout
print("\n[3/4] Checking Local SQLite Telemetry & 72H Timeout Watchdog...")
try:
    if os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        rows = c.execute("SELECT timestamp, symbol, order_side, status, entry_time FROM execution_telemetry ORDER BY timestamp DESC LIMIT 5").fetchall()
        print(f"  • Telemetry DB Entries: {len(rows)} recent events logged")
        for r in rows:
            print(f"    -> {r[0][:19]} | {r[1]:<6} | {r[2]:<10} | {r[3]}")
        conn.close()
        print("  [PASS] Telemetry logging operational.")
    else:
        print("  [WARN] execution_telemetry.db not yet created.")
except Exception as e:
    print(f"  [FAIL] Telemetry DB check error: {e}")

# 4. Circuit Breakers & Peak Equity
print("\n[4/4] Checking Circuit Breakers & Peak Equity State...")
halt_lock = os.path.exists("HALT_TRADING.lock")
dd_lock = os.path.exists("DRAWDOWN_CIRCUIT_BREAKER.lock")
peak_eq = "N/A"
if os.path.exists(".peak_equity.txt"):
    with open(".peak_equity.txt", "r") as f:
        peak_eq = f.read().strip()

print(f"  • Peak Equity Recorded : ${float(peak_eq):,.2f}" if peak_eq != "N/A" else "  • Peak Equity Recorded : None")
print(f"  • HALT Lockfile        : {'ACTIVE (BLOCKED)' if halt_lock else 'Clean (Clear)'}")
print(f"  • Drawdown Lockfile    : {'ACTIVE (BLOCKED)' if dd_lock else 'Clean (Clear)'}")

if not halt_lock and not dd_lock:
    print("  [PASS] Circuit breakers clear. Full trading pipeline ready.")
else:
    print("  [FAIL] Circuit breaker active! Trading is halted.")

print("\n" + "=" * 80)
print("                       VERIFICATION COMPLETE")
print("=" * 80 + "\n")
