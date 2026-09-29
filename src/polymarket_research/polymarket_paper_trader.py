#!/usr/bin/env python3
"""
Polymarket Autonomous Forward Paper Trader
File: src/polymarket_research/polymarket_paper_trader.py

Runs real-time paper trading on Polymarket 1-Hour BTC binary markets:
1. Replays historical shocks from data/polymarket/shock_responses.jsonl to initialize track record.
2. Continuously monitors live incoming shocks for the late-candle alpha sweet spot:
   - Time to Expiry (TTE) <= 15 minutes (900 seconds)
   - Direction congruent with candle distance (Spot vs Open)
   - Effective price between $0.15 and $0.85 (avoiding extreme tail traps)
   - Max 2 concurrent positions per hourly market ($50 notional each)
3. Evaluates full fill-level taker fees (7% crypto fee schedule) and book sweep crossing costs.
4. Automatically settles open paper positions against finalized candle resolutions.
5. Logs real-time performance metrics to data/polymarket/paper_trading_ledger.jsonl.
"""

import os
import sys
import json
import time
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

PIPELINE_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PIPELINE_ROOT / "data" / "polymarket"
SHOCK_FILE = DATA_DIR / "shock_responses.jsonl"
RESOLUTIONS_FILE = DATA_DIR / "finalized_market_resolutions.jsonl"
LEDGER_FILE = DATA_DIR / "paper_trading_ledger.jsonl"
STATE_FILE = DATA_DIR / "paper_trader_state.json"
PID_FILE = DATA_DIR / "paper_trader.pid"

INITIAL_PAPER_CAPITAL = 1000.0
TICKET_NOTIONAL = 50.0
MAX_TTE_SECONDS = 900.0  # 15 minutes
MIN_TTE_SECONDS = 60.0   # 1 minute (avoid unexecutable settlement lock)
MAX_TRADES_PER_HOUR = 2

class PolymarketForwardPaperTrader:
    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.cash = INITIAL_PAPER_CAPITAL
        self.realized_pnl = 0.0
        self.total_fees_paid = 0.0
        self.open_trades: Dict[str, List[Dict[str, Any]]] = {}  # market_id -> list of open positions
        self.closed_trades: List[Dict[str, Any]] = []
        self.seen_shock_ids = set()
        self.seen_resolution_ids = set()
        self.last_shock_file_pos = 0
        self.last_res_file_pos = 0

    def replay_existing_data(self):
        """Replays all completed markets to establish the baseline paper ledger."""
        if not RESOLUTIONS_FILE.exists() or not SHOCK_FILE.exists():
            return

        resolutions = {}
        with open(RESOLUTIONS_FILE, "r") as f:
            for line in f:
                if line.strip():
                    r = json.loads(line)
                    resolutions[r["market_id"]] = r
                    self.seen_resolution_ids.add(r["market_id"])

        with open(SHOCK_FILE, "r") as f:
            for line in f:
                if not line.strip():
                    continue
                s = json.loads(line)
                shock_id = f"{s.get('market_id')}_{s.get('t0_unix')}"
                self.seen_shock_ids.add(shock_id)
                self.evaluate_shock_signal(s, historical=True)

        # Settle any completed historical markets
        for m_id, res in resolutions.items():
            self.settle_market(m_id, res, historical=True)

        self.save_state()
        print(f"[REPLAY COMPLETE] Processed {len(self.closed_trades)} historical paper trades. "
              f"Realized PnL: ${self.realized_pnl:+.2f} | Current Equity: ${self.cash:,.2f}")

    def evaluate_shock_signal(self, shock: Dict[str, Any], historical: bool = False):
        m_id = shock.get("market_id")
        if not m_id:
            return

        # Check trades per hour cap
        current_market_trades = self.open_trades.get(m_id, [])
        if len(current_market_trades) >= MAX_TRADES_PER_HOUR:
            return

        tte = shock.get("seconds_to_expiry", 3600.0)
        if tte > MAX_TTE_SECONDS or tte < MIN_TTE_SECONDS:
            return

        shock_dir = shock.get("shock_direction")  # BUY or SELL
        target_token = "UP" if shock_dir == "BUY" else "DOWN"

        # Trend Congruence Invariant: Shock must align with current distance from 1H candle open
        dist_pct = shock.get("candle_distance_pct", 0.0)
        if target_token == "UP" and dist_pct < 0.0:
            return
        if target_token == "DOWN" and dist_pct > 0.0:
            return

        token_features = shock.get("pre_shock_features_t0", {}).get(target_token, {})
        eff_px = token_features.get("effective_price_$50")
        if not eff_px or eff_px < 0.15 or eff_px > 0.85:
            return

        shares = TICKET_NOTIONAL / eff_px
        fee_rate = shock.get("fee_metadata", {}).get("fee_rate_market", 0.07)
        # Fill-level fee: C * feeRate * p * (1 - p)
        taker_fee = TICKET_NOTIONAL * fee_rate * eff_px * (1.0 - eff_px)

        trade = {
            "trade_id": f"PAPER_{m_id}_{int(shock.get('t0_unix', time.time()))}_{target_token}",
            "market_id": m_id,
            "title": shock.get("title", ""),
            "entry_time": shock.get("timestamp", ""),
            "entry_unix": shock.get("t0_unix", time.time()),
            "seconds_to_expiry": tte,
            "target_token": target_token,
            "notional_usd": TICKET_NOTIONAL,
            "effective_price": eff_px,
            "shares_bought": round(shares, 4),
            "taker_fee_usd": round(taker_fee, 4),
            "spot_at_t0": shock.get("spot_at_t0"),
            "candle_distance_pct": dist_pct,
            "status": "OPEN"
        }

        if m_id not in self.open_trades:
            self.open_trades[m_id] = []
        self.open_trades[m_id].append(trade)
        self.cash -= TICKET_NOTIONAL
        self.total_fees_paid += taker_fee

        if not historical:
            print(f"\n[PAPER ORDER FILLED] {shock.get('title')} | Target: {target_token} | "
                  f"Price: {eff_px:.3f} | Shares: {shares:.1f} | TTE: {tte/60.0:.1f}m | Dist: {dist_pct:+.2f}%", flush=True)

    def settle_market(self, m_id: str, resolution: Dict[str, Any], historical: bool = False):
        if m_id not in self.open_trades:
            return

        winning = resolution.get("winning_outcome")  # UP or DOWN
        closed_this_round = []

        for trade in self.open_trades[m_id]:
            won = (trade["target_token"] == winning)
            payout = trade["shares_bought"] * 1.0 if won else 0.0
            net_pnl = payout - trade["notional_usd"]

            trade["settle_time"] = resolution.get("timestamp_resolved", "")
            trade["winning_outcome"] = winning
            trade["won"] = won
            trade["payout_usd"] = round(payout, 2)
            trade["net_pnl_usd"] = round(net_pnl, 2)
            trade["status"] = "CLOSED"

            self.cash += payout
            self.realized_pnl += net_pnl
            self.closed_trades.append(trade)
            closed_this_round.append(trade)

            with open(LEDGER_FILE, "a") as f:
                f.write(json.dumps(trade) + "\n")

        del self.open_trades[m_id]

        if not historical and closed_this_round:
            total_round_pnl = sum(t["net_pnl_usd"] for t in closed_this_round)
            print(f"\n[MARKET SETTLED] Market ID: {m_id} | Winner: {winning} | "
                  f"Trades Settled: {len(closed_this_round)} | Net PnL: ${total_round_pnl:+.2f} | "
                  f"Total Portfolio: ${self.cash:,.2f}", flush=True)

    def save_state(self):
        total_trades = len(self.closed_trades)
        wins = sum(1 for t in self.closed_trades if t.get("won"))
        win_rate = (wins / total_trades * 100.0) if total_trades > 0 else 0.0

        state = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "paper_portfolio_equity": round(self.cash, 2),
            "initial_capital": INITIAL_PAPER_CAPITAL,
            "cumulative_realized_pnl": round(self.realized_pnl, 2),
            "total_fees_paid": round(self.total_fees_paid, 2),
            "total_trades_settled": total_trades,
            "winning_trades": wins,
            "losing_trades": total_trades - wins,
            "win_rate_pct": round(win_rate, 2),
            "active_open_positions_count": sum(len(v) for v in self.open_trades.values()),
            "status": "RUNNING"
        }
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)

    async def live_loop(self):
        print("===============================================================================", flush=True)
        print("   POLYMARKET AUTONOMOUS FORWARD PAPER TRADING ENGINE (Sweet Spot Strategy)   ", flush=True)
        print("   Filter: TTE <= 15m | Congruent Candle Distance | Exact Fill-Level Fees     ", flush=True)
        print("   Ticket Size: $50.00 Notional | Initial Capital: $1,000.00                   ", flush=True)
        print("===============================================================================", flush=True)

        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))

        self.replay_existing_data()

        while True:
            try:
                # 1. Ingest new shock events
                if SHOCK_FILE.exists():
                    with open(SHOCK_FILE, "r") as f:
                        f.seek(self.last_shock_file_pos)
                        new_lines = f.readlines()
                        self.last_shock_file_pos = f.tell()

                    for line in new_lines:
                        if not line.strip():
                            continue
                        s = json.loads(line)
                        shock_id = f"{s.get('market_id')}_{s.get('t0_unix')}"
                        if shock_id not in self.seen_shock_ids:
                            self.seen_shock_ids.add(shock_id)
                            self.evaluate_shock_signal(s, historical=False)

                # 2. Check for newly finalized market resolutions
                if RESOLUTIONS_FILE.exists():
                    with open(RESOLUTIONS_FILE, "r") as f:
                        f.seek(self.last_res_file_pos)
                        new_res_lines = f.readlines()
                        self.last_res_file_pos = f.tell()

                    for line in new_res_lines:
                        if not line.strip():
                            continue
                        res = json.loads(line)
                        m_id = res.get("market_id")
                        if m_id not in self.seen_resolution_ids:
                            self.seen_resolution_ids.add(m_id)
                            self.settle_market(m_id, res, historical=False)

                self.save_state()
                await asyncio.sleep(5)
            except Exception as e:
                print(f"[-] Error in paper trader loop: {e}", flush=True)
                await asyncio.sleep(5)

if __name__ == "__main__":
    trader = PolymarketForwardPaperTrader()
    asyncio.run(trader.live_loop())
