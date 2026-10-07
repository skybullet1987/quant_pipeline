#!/usr/bin/env python3
"""
POLYMARKET LIVE HARVESTER DAEMON (v1.0.0 Production)
===================================================
Real-time execution daemon implementing Policy B2 (Maker-First Fast Unwind):
  1. Tails real-time shock responses from Binance/Polymarket streaming pipeline.
  2. Enforces strict fail-closed depth guard (DepthRatio >= 1.50) and sweet-spot gating.
  3. Executes atomic FOK entry via EIP-712 L2 CLOB API.
  4. Posts resting maker scalp ask (+10¢ target) to capture fast unwind repricing.
  5. Manages positions, logs fills to live immutable audit ledger.
"""

import asyncio
import json
import logging
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from dotenv import load_dotenv
import requests

PIPELINE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

load_dotenv(PIPELINE_ROOT / ".env")

from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor, OrderResult

logger = logging.getLogger("LiveHarvester")
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s UTC] [%(levelname)s] [HARVESTER] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(PIPELINE_ROOT / "data/polymarket/live_harvester.log"),
    ],
)

DATA_DIR = PIPELINE_ROOT / "data/polymarket"
TRIGGER_FILE = DATA_DIR / "live_shock_triggers.jsonl"
SHOCK_FILE = DATA_DIR / "shock_responses.jsonl"
RESOLUTIONS_FILE = DATA_DIR / "finalized_market_resolutions.jsonl"
STATE_FILE = DATA_DIR / "live_harvester_state.json"
PID_FILE = DATA_DIR / "live_harvester.pid"

DEFAULT_TICKET_NOTIONAL = 20.0       # $20 per trade (Kelly-optimal on $301 bankroll)
MAX_TRADES_PER_HOUR = 1             # Max 1 trade per 1-hour market candle
MAX_PORTFOLIO_EXPOSURE_USD = 60.0   # Hard ceiling: max $60 total concurrent exposure
PROFIT_THETA = 0.10                 # +10¢ target exit scalp
MIN_DISTANCE_PCT = 0.05             # At least 0.05% lead-lag distance shock


class PolymarketLiveHarvester:
    def __init__(self, ticket_notional: float = DEFAULT_TICKET_NOTIONAL, dry_run: bool = False):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.ticket_notional = ticket_notional
        self.dry_run = dry_run
        
        # Initialize execution adapter
        self.executor = PolymarketLiveExecutor(
            dry_run=dry_run,
            ledger_path=str(DATA_DIR / "live_orders.jsonl")
        )
        
        self.seen_shock_ids: Set[str] = set()
        self.traded_market_ids: Set[str] = set()
        self.active_positions: Dict[str, Dict[str, Any]] = {}
        self.closed_positions: List[Dict[str, Any]] = []
        self.trades_this_hour = 0
        self.current_hour_window = time.time() // 3600
        
        self.last_trigger_file_pos = 0
        self.last_shock_file_pos = 0
        self.last_res_file_pos = 0
        self.market_tokens_cache: Dict[str, str] = {}

    def get_token_id(self, market_id: str, target_token: str) -> Optional[str]:
        cache_key = f"{market_id}_{target_token}"
        if cache_key in self.market_tokens_cache:
            return self.market_tokens_cache[cache_key]
        try:
            r = requests.get(f"https://gamma-api.polymarket.com/markets/{market_id}", timeout=3).json()
            raw = r.get("clobTokenIds")
            tokens = json.loads(raw) if isinstance(raw, str) else raw
            if tokens and len(tokens) >= 2:
                self.market_tokens_cache[f"{market_id}_UP"] = str(tokens[0])
                self.market_tokens_cache[f"{market_id}_DOWN"] = str(tokens[1])
                logger.info(f"Resolved tokens for market {market_id}: UP={tokens[0][:10]}... DOWN={tokens[1][:10]}...")
                return self.market_tokens_cache.get(cache_key)
        except Exception as e:
            logger.error(f"Error fetching tokens for market {market_id}: {e}")
        return None

    def load_state(self):
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, "r") as f:
                    state = json.load(f)
                    self.active_positions = state.get("active_positions", {})
                    self.closed_positions = state.get("closed_positions", [])
                    self.seen_shock_ids = set(state.get("seen_shock_ids", []))
                    self.traded_market_ids = set(state.get("traded_market_ids", []))
                    logger.info(f"Loaded existing state: {len(self.active_positions)} active positions, {len(self.traded_market_ids)} traded markets.")
            except Exception as e:
                logger.error(f"Error loading state: {e}")

    def save_state(self):
        state = {
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
            "ticket_notional": self.ticket_notional,
            "dry_run": self.dry_run,
            "active_positions_count": len(self.active_positions),
            "closed_positions_count": len(self.closed_positions),
            "active_positions": self.active_positions,
            "closed_positions": self.closed_positions[-20:],
            "seen_shock_ids": list(self.seen_shock_ids)[-200:],
            "traded_market_ids": list(self.traded_market_ids)[-100:],
            "status": "RUNNING"
        }
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)

    def evaluate_shock_and_execute(self, shock: Dict[str, Any]):
        now_hour = time.time() // 3600
        if now_hour != self.current_hour_window:
            self.current_hour_window = now_hour
            self.trades_this_hour = 0

        if self.trades_this_hour >= MAX_TRADES_PER_HOUR:
            return

        m_id = str(shock.get("market_id"))
        if m_id in self.traded_market_ids:
            return

        # Portfolio Exposure Guard (hard ceiling: $60 max portfolio exposure)
        current_exposure = sum(pos.get("notional_usd", 0.0) for pos in self.active_positions.values())
        if (current_exposure + self.ticket_notional) > MAX_PORTFOLIO_EXPOSURE_USD:
            logger.warning(
                f"Portfolio exposure ceiling reached: ${current_exposure:.2f} + ${self.ticket_notional:.2f} "
                f"> ${MAX_PORTFOLIO_EXPOSURE_USD:.2f}. Skipping opportunity."
            )
            return

        shock_dir = shock.get("shock_direction")  # "BUY" or "SELL"
        if not shock_dir:
            return
        target_token = "UP" if shock_dir == "BUY" else "DOWN"

        # Time-to-Expiry (TTE) Guard: Must be in sweet spot (60s <= TTE <= 900s / last 15 min of candle)
        tte = shock.get("seconds_to_expiry", 3600.0)
        if tte > 900.0 or tte < 60.0:
            return

        # Trend Congruence Guard (|dist| >= 0.05%)
        dist_pct = shock.get("candle_distance_pct", 0.0)
        min_dist = 0.05
        if abs(dist_pct) < min_dist:
            return
        if target_token == "UP" and dist_pct < min_dist:
            return
        if target_token == "DOWN" and dist_pct > -min_dist:
            return

        token_features = shock.get("pre_shock_features_t0", {}).get(target_token, {})
        m_id = str(shock.get("market_id"))
        token_id = token_features.get("token_id") or self.get_token_id(m_id, target_token)
        if not token_id:
            logger.warning(f"Could not resolve token_id for market {m_id} ({target_token})")
            return

        # Pre-Trade Fail-Closed Depth Check (>= 1.5x of ticket size)
        raw_asks = token_features.get("raw_top_asks", [])
        if not raw_asks:
            return
        executable_depth_usd = sum(px * sz for px, sz in raw_asks if px <= 0.85)
        depth_ratio = executable_depth_usd / self.ticket_notional
        if depth_ratio < 1.50:
            return

        eff_px = (
            token_features.get(f"effective_price_${int(self.ticket_notional)}")
            or token_features.get("effective_price_$20")
            or token_features.get("effective_price_$50")
            or (raw_asks[0][0] if raw_asks else None)
        )
        if not eff_px or eff_px < 0.15 or eff_px > 0.85:
            return

        trade_id = f"LIVE_{shock.get('market_id')}_{int(time.time())}_{target_token}"
        logger.info(
            f"[QUALIFIED OPPORTUNITY] {shock.get('title')} | Target: {target_token} | "
            f"Expected Px: ${eff_px:.3f} | Dist: {dist_pct:+.2f}% | TTE: {tte/60.0:.1f}m | Depth: ${executable_depth_usd:.1f}"
        )

        # Dispatch live order via EIP-712 adapter
        res = self.executor.execute_snipe_order(
            trade_id=trade_id,
            token_id=token_id,
            target_token=target_token,
            notional_usd=self.ticket_notional,
            target_price=eff_px,
            side="BUY",
            depth_hurdle=1.50
        )

        if res.success:
            self.trades_this_hour += 1
            self.traded_market_ids.add(m_id)
            target_exit = min(0.99, round(res.price + PROFIT_THETA, 4))
            pos_record = {
                "trade_id": trade_id,
                "market_id": str(shock.get("market_id")),
                "token_id": token_id,
                "target_token": target_token,
                "entry_price": res.price,
                "entry_shares": res.size,
                "notional_usd": res.notional_usd,
                "fee_usd": res.fee_usd,
                "target_exit_price": target_exit,
                "entry_time_utc": datetime.now(timezone.utc).isoformat(),
                "status": "OPEN",
                "exit_order_id": None,
            }
            # Post resting maker scalp limit order (Policy B2)
            exit_res = self.executor.post_maker_exit_order(
                token_id=token_id,
                price=target_exit,
                size=res.size,
                side="SELL",
            )
            if exit_res.get("success"):
                pos_record["exit_order_id"] = exit_res.get("orderID")
                logger.info(f"✓ MAKER SCALP ORDER POSTED: {pos_record['exit_order_id']} | {res.size:.2f} shares @ ${target_exit:.4f}")

            self.active_positions[trade_id] = pos_record
            logger.info(f"✓ POSITION OPENED: {trade_id} | Shares={res.size:.2f} @ ${res.price:.4f} | Target Exit: ${target_exit:.4f}")
            self.save_state()

    def check_resolutions_and_manage_positions(self):
        """Monitors active positions for maker scalp fills or finalized market resolutions."""
        if not self.active_positions:
            return

        # 1. Check finalized candle resolutions from stream
        if RESOLUTIONS_FILE.exists():
            try:
                current_res_size = RESOLUTIONS_FILE.stat().st_size
                if current_res_size > self.last_res_file_pos:
                    with open(RESOLUTIONS_FILE, "r") as f:
                        f.seek(self.last_res_file_pos)
                        new_lines = f.readlines()
                        self.last_res_file_pos = f.tell()

                    for line in new_lines:
                        if not line.strip():
                            continue
                        try:
                            res = json.loads(line)
                            res_m_id = str(res.get("market_id"))
                            winning_outcome = res.get("winning_outcome")

                            for tid, pos in list(self.active_positions.items()):
                                if str(pos.get("market_id")) == res_m_id:
                                    won = (pos.get("target_token") == winning_outcome)
                                    payout = pos["entry_shares"] * 1.0 if won else 0.0
                                    net_pnl = payout - pos["notional_usd"] - pos["fee_usd"]

                                    # Cancel resting exit order if still open
                                    if pos.get("exit_order_id"):
                                        self.executor.cancel_order(pos["exit_order_id"])

                                    pos["status"] = "CLOSED"
                                    pos["settled_at_utc"] = datetime.now(timezone.utc).isoformat()
                                    pos["won"] = won
                                    pos["payout_usd"] = round(payout, 2)
                                    pos["net_pnl_usd"] = round(net_pnl, 2)
                                    pos["close_reason"] = "MARKET_RESOLVED"
                                    self.closed_positions.append(pos)
                                    del self.active_positions[tid]
                                    logger.info(f"✓ POSITION RESOLVED AT MATURITY: {tid} | Won={won} | Net PnL=${net_pnl:+.2f}")
                                    self.save_state()
                        except Exception as e:
                            logger.error(f"Error parsing resolution line: {e}")
            except Exception as e:
                logger.error(f"Error checking resolutions: {e}")

        # 2. Check live positions for maker scalp fills (verifiable CLOB order query or book inspection)
        for tid, pos in list(self.active_positions.items()):
            try:
                # Primary: query live CLOB order status if order ID exists and in live mode
                if pos.get("exit_order_id") and not self.dry_run:
                    order_info = self.executor.get_order_status(pos["exit_order_id"])
                    if order_info:
                        status = order_info.get("status")
                        size_matched = float(order_info.get("size_matched", 0.0))
                        if status == "MATCHED" or size_matched >= (pos["entry_shares"] - 1e-4):
                            payout = round(pos["entry_shares"] * pos["target_exit_price"], 2)
                            net_pnl = round(payout - pos["notional_usd"] - pos["fee_usd"], 2)
                            pos["status"] = "CLOSED"
                            pos["settled_at_utc"] = datetime.now(timezone.utc).isoformat()
                            pos["won"] = True
                            pos["payout_usd"] = payout
                            pos["net_pnl_usd"] = net_pnl
                            pos["close_reason"] = "MAKER_SCALP_FILLED_CLOB"
                            self.closed_positions.append(pos)
                            del self.active_positions[tid]
                            logger.info(f"✓ POSITION CLOSED VIA VERIFIED CLOB FILL: {tid} | OID: {pos['exit_order_id']} | Net PnL: ${net_pnl:+.2f}")
                            self.save_state()
                            continue

                # Secondary: Check live market orderbook bids (simulation or resting order cross)
                token_id = pos.get("token_id")
                if not token_id:
                    continue
                book = self.executor.get_market_book(token_id)
                bids = book.get("bids", [])
                if bids:
                    best_bid = max(float(b.get("price", 0.0)) for b in bids)
                    if best_bid >= pos["target_exit_price"]:
                        payout = round(pos["entry_shares"] * pos["target_exit_price"], 2)
                        net_pnl = round(payout - pos["notional_usd"] - pos["fee_usd"], 2)
                        pos["status"] = "CLOSED"
                        pos["settled_at_utc"] = datetime.now(timezone.utc).isoformat()
                        pos["won"] = True
                        pos["payout_usd"] = payout
                        pos["net_pnl_usd"] = net_pnl
                        pos["close_reason"] = "MAKER_SCALP_FILLED_BOOK"
                        self.closed_positions.append(pos)
                        del self.active_positions[tid]
                        logger.info(f"✓ POSITION CLOSED VIA MAKER SCALP: {tid} | Net PnL=${net_pnl:+.2f}")
                        self.save_state()
            except Exception as e:
                logger.debug(f"Error checking book for position {tid}: {e}")

    async def run(self):
        logger.info("=====================================================================")
        logger.info("       POLYMARKET LIVE MONEY HARVESTER (POLICY B2 ARMED)             ")
        logger.info("=====================================================================")
        logger.info(f"Wallet Address:   {self.executor.funder_address}")
        logger.info(f"Auth Mode:        {self.executor.auth_mode}")
        logger.info(f"Ticket Size:      ${self.ticket_notional:.2f} USD")
        logger.info(f"Profit Target:    +{PROFIT_THETA*100:.0f}¢ per share")
        logger.info(f"Mode:             {'DRY-RUN' if self.dry_run else 'LIVE REAL-MONEY TRADING'}")
        logger.info("=====================================================================")

        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))

        self.load_state()

        # Start tailing from current EOF so we only execute new events
        if not TRIGGER_FILE.exists():
            TRIGGER_FILE.touch()
        self.last_trigger_file_pos = TRIGGER_FILE.stat().st_size
        logger.info(f"Tailing zero-latency shock triggers from byte offset: {self.last_trigger_file_pos}")

        if SHOCK_FILE.exists():
            self.last_shock_file_pos = SHOCK_FILE.stat().st_size
            logger.info(f"Tailing shock responses fallback from byte offset: {self.last_shock_file_pos}")

        if RESOLUTIONS_FILE.exists():
            self.last_res_file_pos = RESOLUTIONS_FILE.stat().st_size
            logger.info(f"Tailing resolutions from byte offset: {self.last_res_file_pos}")

        last_heartbeat = time.time()
        last_mgmt_check = 0.0
        scanned_count = 0

        while True:
            try:
                # 1. Ingest zero-latency shock triggers (<1ms from recorder detection)
                if TRIGGER_FILE.exists():
                    current_size = TRIGGER_FILE.stat().st_size
                    if current_size > self.last_trigger_file_pos:
                        with open(TRIGGER_FILE, "r") as f:
                            f.seek(self.last_trigger_file_pos)
                            new_lines = f.readlines()
                            self.last_trigger_file_pos = f.tell()

                        for line in new_lines:
                            if not line.strip():
                                continue
                            try:
                                shock = json.loads(line)
                                s_id = f"{shock.get('market_id')}_{shock.get('t0_unix')}"
                                if s_id not in self.seen_shock_ids:
                                    self.seen_shock_ids.add(s_id)
                                    scanned_count += 1
                                    self.evaluate_shock_and_execute(shock)
                            except Exception as parse_err:
                                logger.error(f"Error parsing trigger line: {parse_err}")

                # 2. Monitor open positions for scalp exit fills or market resolutions (every 1.0s)
                now_ts = time.time()
                if now_ts - last_mgmt_check >= 1.0:
                    last_mgmt_check = now_ts
                    self.check_resolutions_and_manage_positions()

                if time.time() - last_heartbeat >= 300:
                    last_heartbeat = time.time()
                    active_exp = sum(p.get("notional_usd", 0.0) for p in self.active_positions.values())
                    logger.info(
                        f"[HEARTBEAT] Harvester active | Triggers scanned: {scanned_count} | "
                        f"Active positions: {len(self.active_positions)} (${active_exp:.2f}) | "
                        f"Closed: {len(self.closed_positions)}"
                    )

                # Microsecond-scale poll interval (50ms)
                await asyncio.sleep(0.05)
            except Exception as e:
                logger.error(f"Error in harvester loop: {e}")
                await asyncio.sleep(1.0)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Polymarket Live Harvester")
    parser.add_argument("--lot-size", type=float, default=20.0, help="Ticket size in USD (default: $20.00)")
    parser.add_argument("--dry-run", action="store_true", help="Run in dry-run simulation mode")
    args = parser.parse_args()

    harvester = PolymarketLiveHarvester(ticket_notional=args.lot_size, dry_run=args.dry_run)
    asyncio.run(harvester.run())
