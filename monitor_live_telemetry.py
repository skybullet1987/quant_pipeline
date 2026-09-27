#!/usr/bin/env python3
"""
True Round-Trip Forward Validation Telemetry
- Aggregates multi-slice fills into single trade events.
- Filters fills strictly to the current validation epoch.
"""

import os
import sqlite3
import pandas as pd
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from eth_account import Account
from hyperliquid.info import Info
from hyperliquid.utils import constants

load_dotenv()

BASE_URL = constants.TESTNET_API_URL
SECRET_KEY = (
    os.getenv("HYPERLIQUID_TESTNET_PRIVATE_KEY")
    or os.getenv("HL_TESTNET_PRIVATE_KEY")
    or os.getenv("HYPERLIQUID_PRIVATE_KEY")
)
account = Account.from_key(SECRET_KEY)
info = Info(BASE_URL, skip_ws=True)

MASTER_ADDRESS = (
    os.getenv("HYPERLIQUID_MASTER_ADDRESS")
    or os.getenv("HYPERLIQUID_USER_ADDRESS")
    or os.getenv("MASTER_ADDRESS")
    or account.address
)

# Set the start of the hardened forward validation epoch (e.g. last 48 hours)
EPOCH_START = datetime.now(timezone.utc) - timedelta(days=2)

def inspect_live_telemetry():
    user_state = info.user_state(MASTER_ADDRESS)
    spot_state = info.spot_user_state(MASTER_ADDRESS)
    
    margin_summary = user_state.get("marginSummary", {})
    account_value = float(margin_summary.get("accountValue", 0.0))
    total_margin_used = float(margin_summary.get("totalMarginUsed", 0.0))
    
    spot_usdc = sum(float(b["total"]) for b in spot_state.get("balances", []) if b["coin"] == "USDC")
    unified_equity = account_value + spot_usdc
    utilization_pct = (total_margin_used / unified_equity * 100.0) if unified_equity > 0 else 0.0

    print("\n" + "=" * 90)
    print(f"   LIVE TELEMETRY DASHBOARD | UNIFIED EQUITY: ${unified_equity:>+9,.2f}")
    print("=" * 90)
    print(f"Master Account:      {MASTER_ADDRESS}")
    print(f"Perps Margin Used:   ${total_margin_used:>+9,.2f} ({utilization_pct:.1f}% / 85.0% Cap)")
    print(f"Available Capital:   ${max(0.0, (unified_equity * 0.85 - total_margin_used)):>+9,.2f}")

    # Active Positions
    active_positions = [
        p["position"] for p in user_state.get("assetPositions", [])
        if float(p["position"]["szi"]) != 0.0
    ]
    open_orders = info.open_orders(MASTER_ADDRESS)
    
    print("\n--- ACTIVE PORTFOLIO POSITIONS ---")
    if not active_positions:
        print("  [IDLE] No active positions open.")
    else:
        print(f"{'Coin':<10}{'Side':<8}{'Size':<16}{'Entry Price':<14}{'Unrealized PnL':<18}{'Triggers'}")
        print("-" * 90)
        for pos in active_positions:
            coin = pos["coin"]
            size = float(pos["szi"])
            side = "LONG" if size > 0 else "SHORT"
            entry_px = float(pos["entryPx"])
            upnl = float(pos["unrealizedPnl"])
            triggers = sum(1 for o in open_orders if o["coin"] == coin)
            trigger_status = f"{triggers}/2 Orders" if triggers == 2 else f"⚠️ {triggers}/2 Orders"
            print(f"{coin:<10}{side:<8}{abs(size):<16.4f}${entry_px:<13.4f}${upnl:>+9.2f}          {trigger_status}")

    # Fetch and aggregate on-chain fills
    raw_fills = info.user_fills(MASTER_ADDRESS)
    fill_rows = []
    for f in raw_fills:
        fill_time = datetime.fromtimestamp(f["time"] / 1000.0, timezone.utc)
        closed_pnl = float(f.get("closedPnl", 0.0))
        if fill_time >= EPOCH_START and closed_pnl != 0.0:
            fill_rows.append({
                "time": fill_time,
                "coin": f["coin"],
                "dir": f.get("dir", ""),
                "sz": float(f["sz"]),
                "px": float(f["px"]),
                "pnl": closed_pnl,
                "fee": float(f.get("fee", 0.0)),
                "minute_bucket": fill_time.strftime("%Y-%m-%d %H:%M")
            })

    print(f"\n--- FORWARD VALIDATION SCORECARD (Epoch: Since {EPOCH_START.strftime('%Y-%m-%d %H:%M')} UTC) ---")
    if not fill_rows:
        print("  No closed positions within the current hardened validation epoch.")
    else:
        df = pd.DataFrame(fill_rows)
        # Group partial fill fragments occurring within the same minute on the same coin
        trades = df.groupby(["coin", "minute_bucket", "dir"]).agg({
            "pnl": "sum",
            "fee": "sum",
            "sz": "sum",
            "time": "max"
        }).reset_index().sort_values("time", ascending=False)

        total_trades = len(trades)
        wins = (trades["pnl"] > 0).sum()
        losses = (trades["pnl"] <= 0).sum()
        wr = (wins / total_trades) * 100.0 if total_trades > 0 else 0.0
        
        gross_profit = trades.loc[trades["pnl"] > 0, "pnl"].sum()
        gross_loss = abs(trades.loc[trades["pnl"] < 0, "pnl"].sum())
        pf = (gross_profit / gross_loss) if gross_loss > 0 else (99.9 if gross_profit > 0 else 0.0)
        net_pnl = trades["pnl"].sum() - trades["fee"].sum()

        wr_gate = "PASS" if wr >= 55.0 else "FAIL"
        pf_gate = "PASS" if pf >= 1.60 else "FAIL"

        print(f"Aggregated Trades:   {total_trades} true round-trips ({wins}W / {losses}L)")
        print(f"Realized Net PnL:    ${net_pnl:>+9,.2f} (Fees: ${trades['fee'].sum():.2f})")
        print(f"Realized Win Rate:   {wr:>5.1f}%     (Gate: >= 55.0%) -> [{wr_gate}]")
        print(f"Profit Factor:       {pf:>5.2f}      (Gate: >= 1.60)  -> [{pf_gate}]")
        
        print("\nRecent Round-Trip Exits:")
        for _, t in trades.head(5).iterrows():
            print(f"  • {t['time'].strftime('%Y-%m-%d %H:%M')} UTC | {t['coin']:<8} | {t['dir']:<12} | Net PnL: ${t['pnl'] - t['fee']:>+7.2f}")

    print("=" * 90 + "\n")

if __name__ == "__main__":
    inspect_live_telemetry()
