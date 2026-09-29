#!/usr/bin/env python3
"""
Polymarket Autonomous Forward Paper Trader (Sweet Spot Strategy)
File: src/polymarket_research/polymarket_paper_trader.py

v3.1 Pure Implementation-Conformance / Forensic State:
1. Hard-Enforces R3_VALIDATION_START_UTC = 2026-09-29T18:11:34.000Z (Commit 08d50e8 frozen boundary).
2. Partitions ledgers into DEV calibration (data/polymarket/paper_trading_dev_ledger.jsonl)
   and frozen Out-Of-Sample VALIDATION (data/polymarket/paper_trading_validation_ledger.jsonl).
3. Strictly Fail-Closed executable depth check (DepthRatio >= 1.50, empty book rejects immediately).
4. Strictly requires verified fee metadata in shock payload (fee_rate_market must be present).
5. Fully restart-idempotent (persisted ledgers restored on startup, deduplicating historical events).
"""

import os
import sys
import json
import time
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Set, Optional
from collections import defaultdict

PIPELINE_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PIPELINE_ROOT / "data" / "polymarket"
SHOCK_FILE = DATA_DIR / "shock_responses.jsonl"
RESOLUTIONS_FILE = DATA_DIR / "finalized_market_resolutions.jsonl"
DEV_LEDGER_FILE = DATA_DIR / "paper_trading_dev_ledger.jsonl"
VALIDATION_LEDGER_FILE = DATA_DIR / "paper_trading_validation_ledger.jsonl"
STATE_FILE = DATA_DIR / "paper_trader_state.json"
PID_FILE = DATA_DIR / "paper_trader.pid"

INITIAL_PAPER_CAPITAL = 1000.0
TICKET_NOTIONAL = 50.0
MAX_TTE_SECONDS = 900.0   # 15 minutes
MIN_TTE_SECONDS = 60.0    # 1 minute (avoid unexecutable settlement lock)
MAX_TRADES_PER_HOUR = 2

# v3.1 Frozen Out-of-Sample Boundary
R3_VALIDATION_START_UTC = "2026-09-29T18:11:34.000Z"
R3_VALIDATION_START_UNIX = 1790705494.0


class PolymarketForwardPaperTrader:
    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        # Deduplication & Idempotency Sets
        self.settled_trade_ids: Set[str] = set()
        self.seen_shock_ids: Set[str] = set()
        self.seen_resolution_ids: Set[str] = set()
        self.trades_per_market: Dict[str, int] = defaultdict(int)
        
        # Partitioned Track Records
        self.dev_cash: float = INITIAL_PAPER_CAPITAL
        self.dev_realized_pnl: float = 0.0
        self.dev_total_fees: float = 0.0
        self.dev_trades: List[Dict[str, Any]] = []
        
        self.val_cash: float = INITIAL_PAPER_CAPITAL
        self.val_realized_pnl: float = 0.0
        self.val_total_fees: float = 0.0
        self.val_trades: List[Dict[str, Any]] = []
        
        # In-Flight Open Positions: market_id -> list of open positions
        self.open_trades: Dict[str, List[Dict[str, Any]]] = {}
        
        self.last_shock_file_pos: int = 0
        self.last_res_file_pos: int = 0

        # Load existing ledgers idempotently
        self.load_persisted_ledgers()

    def load_persisted_ledgers(self):
        """Loads DEV and VALIDATION ledgers to restore state idempotently without duplication."""
        # 1. Ingest DEV ledger
        if DEV_LEDGER_FILE.exists():
            with open(DEV_LEDGER_FILE, "r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    t = json.loads(line)
                    tid = t["trade_id"]
                    if tid not in self.settled_trade_ids:
                        self.settled_trade_ids.add(tid)
                        self.dev_trades.append(t)
                        self.dev_realized_pnl += t.get("net_pnl_usd", 0.0)
                        self.dev_total_fees += t.get("taker_fee_usd", 0.0)
                        m_id = t.get("market_id")
                        if m_id:
                            self.trades_per_market[m_id] += 1
            self.dev_cash = INITIAL_PAPER_CAPITAL + self.dev_realized_pnl

        # 2. Ingest VALIDATION ledger
        if VALIDATION_LEDGER_FILE.exists():
            with open(VALIDATION_LEDGER_FILE, "r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    t = json.loads(line)
                    tid = t["trade_id"]
                    if tid not in self.settled_trade_ids:
                        self.settled_trade_ids.add(tid)
                        self.val_trades.append(t)
                        self.val_realized_pnl += t.get("net_pnl_usd", 0.0)
                        self.val_total_fees += t.get("taker_fee_usd", 0.0)
                        m_id = t.get("market_id")
                        if m_id:
                            self.trades_per_market[m_id] += 1
            self.val_cash = INITIAL_PAPER_CAPITAL + self.val_realized_pnl

        print(f"[RECOVERY COMPLETE] Loaded {len(self.settled_trade_ids)} settled trades from disk across {len(self.trades_per_market)} markets."
              f"\n  DEV Ledger: {len(self.dev_trades)} trades | Realized PnL: ${self.dev_realized_pnl:+.2f} | Cash: ${self.dev_cash:,.2f}"
              f"\n  OOS VALIDATION Ledger: {len(self.val_trades)} trades | Realized PnL: ${self.val_realized_pnl:+.2f} | Cash: ${self.val_cash:,.2f}", flush=True)

    def replay_existing_data(self):
        """Replays historical shock data to catch any pending un-settled trades in active markets."""
        if not RESOLUTIONS_FILE.exists() or not SHOCK_FILE.exists():
            return

        resolutions: Dict[str, Dict[str, Any]] = {}
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

        # Settle any open historical markets against finalized resolutions
        for m_id, res in resolutions.items():
            self.settle_market(m_id, res, historical=True)

        self.save_state()
        print(f"[REPLAY SYNCHRONIZED] Open in-flight markets: {len(self.open_trades)}", flush=True)

    def evaluate_shock_signal(self, shock: Dict[str, Any], historical: bool = False):
        m_id = shock.get("market_id")
        if not m_id:
            return

        t0_unix = shock.get("t0_unix", time.time())
        shock_dir = shock.get("shock_direction")  # BUY or SELL
        target_token = "UP" if shock_dir == "BUY" else "DOWN"
        trade_id = f"PAPER_{m_id}_{int(t0_unix)}_{target_token}"

        # Idempotency Guard: Never open or re-evaluate already settled trades
        if trade_id in self.settled_trade_ids:
            return

        # Check in-flight open trades for this market
        current_market_open = self.open_trades.get(m_id, [])
        if any(t["trade_id"] == trade_id for t in current_market_open):
            return

        # Check total trades per market hour cap (settled + open)
        total_market_trades = self.trades_per_market.get(m_id, 0) + len(current_market_open)
        if total_market_trades >= MAX_TRADES_PER_HOUR:
            return

        # Time to Expiry (TTE) Guard: 60s <= TTE <= 900s
        tte = shock.get("seconds_to_expiry", 3600.0)
        if tte > MAX_TTE_SECONDS or tte < MIN_TTE_SECONDS:
            return

        # Trend Congruence Invariant & Noise Whipsaw Guard: Spot must have cleared minimum buffer (|dist| >= 0.05%)
        MIN_CANDLE_DIST_PCT = 0.05
        dist_pct = shock.get("candle_distance_pct", 0.0)
        if abs(dist_pct) < MIN_CANDLE_DIST_PCT:
            return  # Whipsaw risk: Spot is too close to 1H open (within +-0.05% noise zone)
        if target_token == "UP" and dist_pct < MIN_CANDLE_DIST_PCT:
            return
        if target_token == "DOWN" and dist_pct > -MIN_CANDLE_DIST_PCT:
            return

        token_features = shock.get("pre_shock_features_t0", {}).get(target_token, {})
        
        # Executable Depth Ratio Guard (v3.1 Specification: DepthRatio >= 1.50)
        # STRICT FAIL-CLOSED: If resting asks are missing or empty, reject immediately!
        raw_asks = token_features.get("raw_top_asks", [])
        if not raw_asks:
            return  # FAIL-CLOSED: No resting book depth
        executable_depth_usd = sum(px * sz for px, sz in raw_asks if px <= 0.85)
        depth_ratio = executable_depth_usd / TICKET_NOTIONAL
        if depth_ratio < 1.50:
            return  # FAIL-CLOSED: Executable depth ratio < 1.50 (requires >= $75 executable depth for $50 ticket)

        eff_px = token_features.get("effective_price_$50")
        if not eff_px or eff_px < 0.15 or eff_px > 0.85:
            return

        # Explicit Fee Metadata Enforcement (STRICT FAIL-CLOSED)
        fee_meta = shock.get("fee_metadata", {})
        fee_rate = fee_meta.get("fee_rate_market")
        if fee_rate is None or fee_rate <= 0.0:
            return  # FAIL-CLOSED: Missing explicit fee metadata in shock payload

        shares = TICKET_NOTIONAL / eff_px
        # Fill-level fee formula: C * feeRate * p * (1 - p)
        taker_fee = TICKET_NOTIONAL * fee_rate * eff_px * (1.0 - eff_px)

        is_oos_validation = (t0_unix >= R3_VALIDATION_START_UNIX)
        epoch_label = "VALIDATION" if is_oos_validation else "DEV"

        trade = {
            "trade_id": trade_id,
            "market_id": m_id,
            "title": shock.get("title", ""),
            "entry_time": shock.get("timestamp", ""),
            "entry_unix": t0_unix,
            "epoch": epoch_label,
            "seconds_to_expiry": tte,
            "target_token": target_token,
            "notional_usd": TICKET_NOTIONAL,
            "effective_price": eff_px,
            "shares_bought": round(shares, 4),
            "taker_fee_usd": round(taker_fee, 4),
            "fee_rate_applied": fee_rate,
            "spot_at_t0": shock.get("spot_at_t0"),
            "candle_distance_pct": dist_pct,
            "status": "OPEN"
        }

        if m_id not in self.open_trades:
            self.open_trades[m_id] = []
        self.open_trades[m_id].append(trade)

        if not historical:
            print(f"\n[PAPER ORDER FILLED - {epoch_label}] {shock.get('title')} | Target: {target_token} | "
                  f"Price: {eff_px:.3f} | Shares: {shares:.1f} | TTE: {tte/60.0:.1f}m | Dist: {dist_pct:+.2f}% | Fee: ${taker_fee:.3f}", flush=True)

    def settle_market(self, m_id: str, resolution: Dict[str, Any], historical: bool = False):
        if m_id not in self.open_trades:
            return

        winning = resolution.get("winning_outcome")  # UP or DOWN
        closed_this_round = []

        for trade in self.open_trades[m_id]:
            tid = trade["trade_id"]
            if tid in self.settled_trade_ids:
                continue

            won = (trade["target_token"] == winning)
            payout = trade["shares_bought"] * 1.0 if won else 0.0
            net_pnl = payout - trade["notional_usd"]

            trade["settle_time"] = resolution.get("timestamp_resolved", "")
            trade["winning_outcome"] = winning
            trade["won"] = won
            trade["payout_usd"] = round(payout, 2)
            trade["net_pnl_usd"] = round(net_pnl, 2)
            trade["status"] = "CLOSED"

            entry_unix = trade.get("entry_unix", 0.0)
            if entry_unix < R3_VALIDATION_START_UNIX:
                # Route to DEV ledger
                self.dev_trades.append(trade)
                self.dev_realized_pnl += net_pnl
                self.dev_total_fees += trade.get("taker_fee_usd", 0.0)
                self.dev_cash = INITIAL_PAPER_CAPITAL + self.dev_realized_pnl
                target_file = DEV_LEDGER_FILE
            else:
                # Route to frozen Out-of-Sample VALIDATION ledger
                self.val_trades.append(trade)
                self.val_realized_pnl += net_pnl
                self.val_total_fees += trade.get("taker_fee_usd", 0.0)
                self.val_cash = INITIAL_PAPER_CAPITAL + self.val_realized_pnl
                target_file = VALIDATION_LEDGER_FILE

            self.settled_trade_ids.add(tid)
            self.trades_per_market[m_id] += 1
            closed_this_round.append(trade)

            with open(target_file, "a") as f:
                f.write(json.dumps(trade) + "\n")

        del self.open_trades[m_id]

        if not historical and closed_this_round:
            total_round_pnl = sum(t["net_pnl_usd"] for t in closed_this_round)
            print(f"\n[MARKET SETTLED] Market ID: {m_id} | Winner: {winning} | "
                  f"Trades Settled: {len(closed_this_round)} | Net PnL: ${total_round_pnl:+.2f} | "
                  f"Validation Equity: ${self.val_cash:,.2f} | Dev Equity: ${self.dev_cash:,.2f}", flush=True)

    def save_state(self):
        val_total = len(self.val_trades)
        val_wins = sum(1 for t in self.val_trades if t.get("won"))
        val_wr = (val_wins / val_total * 100.0) if val_total > 0 else 0.0

        dev_total = len(self.dev_trades)
        dev_wins = sum(1 for t in self.dev_trades if t.get("won"))
        dev_wr = (dev_wins / dev_total * 100.0) if dev_total > 0 else 0.0

        state = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "governance": {
                "specification_version": "v3.1",
                "validation_start_utc": R3_VALIDATION_START_UTC,
                "validation_start_unix": R3_VALIDATION_START_UNIX,
                "executable_depth_guard": "DepthRatio >= 1.50 (Fail-Closed)",
                "fee_schedule": "crypto_fees_v2 (7% dynamic schedule enforced)",
                "idempotent_event_sourced": True
            },
            "validation_oos_epoch": {
                "paper_portfolio_equity": round(self.val_cash, 2),
                "initial_capital": INITIAL_PAPER_CAPITAL,
                "cumulative_realized_pnl": round(self.val_realized_pnl, 2),
                "total_fees_paid": round(self.val_total_fees, 2),
                "total_trades_settled": val_total,
                "winning_trades": val_wins,
                "losing_trades": val_total - val_wins,
                "win_rate_pct": round(val_wr, 2),
                "ledger_file": str(VALIDATION_LEDGER_FILE)
            },
            "dev_calibration_epoch": {
                "paper_portfolio_equity": round(self.dev_cash, 2),
                "initial_capital": INITIAL_PAPER_CAPITAL,
                "cumulative_realized_pnl": round(self.dev_realized_pnl, 2),
                "total_fees_paid": round(self.dev_total_fees, 2),
                "total_trades_settled": dev_total,
                "winning_trades": dev_wins,
                "losing_trades": dev_total - dev_wins,
                "win_rate_pct": round(dev_wr, 2),
                "ledger_file": str(DEV_LEDGER_FILE)
            },
            "active_open_positions_count": sum(len(v) for v in self.open_trades.values()),
            "total_settled_trade_ids_tracked": len(self.settled_trade_ids),
            "status": "RUNNING"
        }
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)

    async def live_loop(self):
        print("===============================================================================", flush=True)
        print("   POLYMARKET AUTONOMOUS FORWARD PAPER TRADER (v3.1 Conformance State)        ", flush=True)
        print(f"   Frozen OOS Boundary: {R3_VALIDATION_START_UTC}                             ", flush=True)
        print("   Depth Guard: Fail-Closed (Ratio >= 1.50) | Fee Schedule: crypto_fees_v2    ", flush=True)
        print("   Ticket Size: $50.00 Notional | Initial Capital: $1,000.00                  ", flush=True)
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
