#!/usr/bin/env python3
"""
Backtest & Verification of Confirmed Opposite-Side Structural Breakout Salvage:
Replays second-by-second spot price and orderbook bids across today's 11 live production trades:
  - 9 Winning Trades (12PM, 1PM, 3PM, 4PM, 5PM, 6PM, 9PM, 10PM, 11PM ET)
  - 2 Losing Trades (7PM, 8PM ET)

Rule Definition:
  1. Holding UP:
     - Strike = candle open.
     - Wrong-side distance: spot < open -> wrong_side_pct = (open - spot) / open * 100%
  2. Holding DOWN:
     - Strike = candle open.
     - Wrong-side distance: spot > open -> wrong_side_pct = (spot - open) / open * 100%
  3. Condition:
     - Initial trigger when wrong_side_pct >= 0.20%.
     - Must sustain wrong_side_pct >= 0.18% for >= 90 continuous seconds.
     - TTE >= 90s.
     - best_bid >= 0.12 (has viable salvage liquidity).
  4. Action:
     - Salvage shares at best_bid.
"""

import os
import sys
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = PIPELINE_ROOT / "data/polymarket/live_harvester_state.json"
TRIGGERS_FILE = PIPELINE_ROOT / "data/polymarket/live_shock_triggers.jsonl"
RECORDER_ETH = PIPELINE_ROOT / "data/polymarket/recorder_eth.log"
RECORDER_BTC = PIPELINE_ROOT / "data/polymarket/recorder.log"

def load_trades():
    with open(STATE_FILE) as f:
        st = json.load(f)
    closed = st.get("closed_positions", [])
    # Filter for the 11 production trades from 16:00 UTC (12PM ET) onward
    prod_trades = [p for p in closed if p.get("entry_ts", 0) >= 1792339200]
    return prod_trades

def replay_trade(trade):
    t_id = trade["trade_id"]
    asset = trade["asset"]
    token = trade["target_token"]
    entry_ts = float(trade["entry_ts"])
    candle_expiry_ts = float(trade.get("candle_expiry_ts") or (entry_ts + trade.get("seconds_to_expiry", 3600)))
    open_spot = float(trade["candle_open_spot"])
    shares = float(trade.get("gross_entry_shares") or trade.get("entry_shares") or 0.0)
    notional = float(trade.get("notional_usd") or 0.0)
    entry_px = float(trade.get("entry_price") or 0.0)
    won = trade.get("won", False)
    actual_pnl = float(trade.get("net_pnl_usd", 0.0))

    # Read relevant triggers during this trade window
    # We want timestamp, spot, TTE, best_bid for target_token
    snapshots = []
    
    with open(TRIGGERS_FILE, "r") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            
            if d.get("market_id") != trade["market_id"]:
                continue
            
            t_u = float(d.get("t0_unix", 0.0))
            if t_u < entry_ts:
                continue
            if t_u > candle_expiry_ts + 60:
                continue

            spot = float(d.get("spot_at_t0") or d.get("trigger_price") or 0.0)
            tte = float(d.get("seconds_to_expiry", 0.0))
            
            # Extract bid for target token
            tok_feats = d.get("pre_shock_features_t0", {}).get(token, {})
            best_bid = float(tok_feats.get("best_bid") or 0.0)
            if best_bid == 0.0 and tok_feats.get("raw_top_bids"):
                best_bid = float(tok_feats["raw_top_bids"][0][0])
            
            if spot > 0:
                snapshots.append({
                    "timestamp": t_u,
                    "spot": spot,
                    "tte": tte,
                    "best_bid": best_bid,
                })

    # Sort snapshots by timestamp
    snapshots.sort(key=lambda s: s["timestamp"])

    # Track opposite-side duration
    consecutive_wrong_side_start = None
    last_wrong_side_ts = None
    salvaged = False
    salvage_info = None

    for snap in snapshots:
        ts = snap["timestamp"]
        spot = snap["spot"]
        tte = snap["tte"]
        bid = snap["best_bid"]

        if token == "UP":
            # Wrong side is spot < open_spot
            wrong_pct = ((open_spot - spot) / open_spot) * 100.0
        else:
            # Wrong side is spot > open_spot
            wrong_pct = ((spot - open_spot) / open_spot) * 100.0

        # Check if wrong side holds
        if wrong_pct >= 0.18:
            if consecutive_wrong_side_start is None:
                if wrong_pct >= 0.20:
                    consecutive_wrong_side_start = ts
                    last_wrong_side_ts = ts
            else:
                last_wrong_side_ts = ts
                duration = last_wrong_side_ts - consecutive_wrong_side_start
                if duration >= 90.0:
                    # Check salvage criteria
                    if tte >= 90.0 and bid >= 0.12:
                        salvaged = True
                        salvage_cash = round(shares * bid, 2)
                        salvage_pnl = round(salvage_cash - notional, 2)
                        salvage_info = {
                            "trigger_ts": ts,
                            "delay_after_entry_sec": round(ts - entry_ts, 1),
                            "tte": tte,
                            "wrong_pct": round(wrong_pct, 4),
                            "bid": bid,
                            "shares": shares,
                            "salvage_cash": salvage_cash,
                            "salvage_pnl": salvage_pnl,
                            "duration_held": round(duration, 1)
                        }
                        break
        else:
            consecutive_wrong_side_start = None
            last_wrong_side_ts = None

    return {
        "trade_id": t_id,
        "asset": asset,
        "token": token,
        "won": won,
        "actual_pnl": actual_pnl,
        "entry_px": entry_px,
        "notional": notional,
        "shares": shares,
        "snapshots_count": len(snapshots),
        "salvaged": salvaged,
        "salvage_info": salvage_info,
    }

def main():
    trades = load_trades()
    print("=" * 85)
    print(f"   BACKTEST: CONFIRMED OPPOSITE-SIDE BREAKOUT SALVAGE ({len(trades)} PRODUCTION TRADES)")
    print("=" * 85)
    print(f"{'Trade / Candle':<32} {'Type':<10} {'Result':<8} {'Actual PnL':<12} {'Salvaged?':<12} {'Salvage PnL / Notes'}")
    print("-" * 85)

    winners_touched = 0
    losers_salvaged = 0
    total_salvage_recovered = 0.0

    for tr in trades:
        res = replay_trade(tr)
        t_title = f"{res['asset']} {res['token']} ({res['trade_id'][-20:]})"
        res_str = "WIN" if res["won"] else "LOSS"
        actual_pnl_str = f"${res['actual_pnl']:+.2f}"
        salvaged_str = "YES (BAIL)" if res["salvaged"] else "NO"
        
        note = ""
        if res["won"]:
            if res["salvaged"]:
                winners_touched += 1
                note = f"[FALSE POSITIVE] Wrongly exited winner at {res['salvage_info']['bid']:.2f}!"
            else:
                note = "Held to target/payout (0 false triggers)"
        else:
            if res["salvaged"]:
                losers_salvaged += 1
                s = res["salvage_info"]
                cash_back = s['salvage_cash']
                total_salvage_recovered += cash_back
                note = f"Salvaged +${cash_back:.2f} cash @ {s['bid']:.2f} bid (Loss cut to {s['salvage_pnl']:+.2f})"
            else:
                note = "[UNSAVED] Full loss to 0.00"

        print(f"{t_title:<32} {res['token']:<10} {res_str:<8} {actual_pnl_str:<12} {salvaged_str:<12} {note}")

    print("=" * 85)
    print(f"VERIFICATION SUMMARY:")
    print(f"  - Winners Touched: {winners_touched} / 9 (Target: 0)")
    print(f"  - Losers Salvaged: {losers_salvaged} / 2 (Target: 2)")
    print(f"  - Total Capital Salvaged: +${total_salvage_recovered:.2f} USDC")
    print("=" * 85)

if __name__ == "__main__":
    main()
