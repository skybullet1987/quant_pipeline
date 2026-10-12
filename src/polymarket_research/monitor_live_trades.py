#!/usr/bin/env python3
"""
Polymarket Live Trade & Signal Monitor
Displays:
1. Currently deployed parameters & wallet cash
2. Active positions in flight
3. Closed real-money trades
4. Recent paper-trading parity trades (last 5 deals)
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
STATE_FILE = BASE_DIR / "data/polymarket/live_harvester_state.json"
LEDGER_FILE = BASE_DIR / "data/polymarket/paper_trading_validation_ledger.jsonl"
LOG_FILE = BASE_DIR / "data/polymarket/live_harvester.log"

def main():
    print("=" * 80)
    print("           POLYMARKET REAL-TIME TRADE & HARVESTER MONITOR")
    print("=" * 80)
    
    # 1. State & Active Configuration
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            state = json.load(f)
            
        print("\n[ACTIVE SYSTEM CONFIGURATION]")
        print(f"  Daemon Status:       {state.get('status', 'UNKNOWN')}")
        print(f"  Mode:                {'DRY_RUN' if state.get('dry_run') else 'LIVE_REAL_MONEY'}")
        print(f"  Base Ticket:         ${state.get('ticket_notional', 35.0):.2f}")
        print(f"  Dynamic Sizing:      {state.get('dynamic_sizing', True)} (Half-Kelly, 12% cap)")
        print(f"  Max Exposure Cap:    ${state.get('max_exposure', 75.0):.2f}")
        print(f"  Max Concurrent:      {state.get('max_concurrent_positions', 2)}")
        print(f"  Active Positions:    {state.get('active_positions_count', 0)}")
        print(f"  Closed Positions:    {state.get('closed_positions_count', 0)}")
        
        # Active positions
        active = state.get("active_positions", {})
        if active:
            print("\n[ACTIVE POSITIONS IN FLIGHT]")
            for pid, pos in active.items():
                print(f"  • {pos.get('trade_id')}: {pos.get('target_token')} | ${pos.get('notional_usd'):.2f} @ ${pos.get('entry_price'):.4f} | Status={pos.get('status')}")
        else:
            print("  Active In Flight:    0 (Standing by for next hourly shock trigger)")
            
        # Closed real-money trades
        closed = state.get("closed_positions", [])
        if closed:
            print("\n[CLOSED REAL-MONEY TRADES]")
            print(f"  {'Trade ID':<30} {'Token':<6} {'Entry':<8} {'Exit/Settle':<12} {'PnL':<10} {'Reason'}")
            print("  " + "-" * 76)
            for cp in closed[-8:]:
                tid = cp.get("trade_id", "")
                tok = cp.get("target_token", "")
                epx = f"${cp.get('entry_price', 0):.3f}"
                exit_px = f"${cp.get('average_exit_price') or (cp.get('payout_usd', 0)/max(0.01, cp.get('entry_shares', 1))):.3f}"
                pnl = f"${cp.get('net_pnl_usd', 0):+.2f}"
                reason = cp.get("close_reason", "")
                print(f"  {tid:<30} {tok:<6} {epx:<8} {exit_px:<12} {pnl:<10} {reason}")
    else:
        print("[!] Live harvester state file not found.")

    # 2. Recent Paper Trades (5-for-5 wins)
    if LEDGER_FILE.exists():
        trades = []
        with open(LEDGER_FILE) as f:
            for line in f:
                if line.strip():
                    trades.append(json.loads(line))
        trades.sort(key=lambda x: x["entry_unix"])
        recent = trades[-5:]
        print("\n[LAST 5 PAPER TRADING DEALS (Recent 24H Validation)]")
        print(f"  {'Time (UTC)':<17} {'Asset / Market':<32} {'Token':<6} {'Fill Px':<9} {'Payout':<8} {'Net PnL':<8}")
        print("  " + "-" * 84)
        for t in recent:
            ts = t["entry_time"][5:16]
            title = t.get("title", "")[:31]
            tok = t.get("target_token", "")
            px = f"${t.get('effective_price', 0):.4f}"
            payout = f"${t.get('payout_usd', 0):.2f}"
            pnl = f"${t.get('net_pnl_usd', 0):+.2f}"
            print(f"  {ts:<17} {title:<32} {tok:<6} {px:<9} {payout:<8} {pnl:<8}")
            
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
