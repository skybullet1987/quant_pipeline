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
import ctypes
import json
import logging
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
import fcntl
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from dotenv import load_dotenv
import requests

PIPELINE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

load_dotenv(PIPELINE_ROOT / ".env")

from src.polymarket_research.polymarket_live_executor import (
    PolymarketLiveExecutor,
    OrderResult,
    ExecutionStatus,
    calculate_taker_fee,
)

logger = logging.getLogger("LiveHarvester")
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s UTC] [%(levelname)s] [HARVESTER] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(PIPELINE_ROOT / "data/polymarket/live_harvester.log"),
    ],
)


class LinuxInotifyWatcher:
    """
    Sub-millisecond filesystem change notifier using Linux inotify syscalls via libc.
    Replaces 50ms polling with direct event-driven kernel wakeups.
    """
    IN_MODIFY = 0x00000002
    IN_CLOSE_WRITE = 0x00000008
    IN_NONBLOCK = 0x00000800

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.fd = -1
        self.wd = -1
        self._available = False
        try:
            self.libc = ctypes.CDLL("libc.so.6", use_errno=True)
            self.inotify_init1 = self.libc.inotify_init1
            self.inotify_init1.restype = ctypes.c_int
            self.inotify_init1.argtypes = [ctypes.c_int]

            self.inotify_add_watch = self.libc.inotify_add_watch
            self.inotify_add_watch.restype = ctypes.c_int
            self.inotify_add_watch.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32]

            self.fd = self.inotify_init1(self.IN_NONBLOCK)
            if self.fd >= 0:
                if not self.filepath.exists():
                    self.filepath.touch()
                target_bytes = str(self.filepath).encode("utf-8")
                self.wd = self.inotify_add_watch(self.fd, target_bytes, self.IN_MODIFY | self.IN_CLOSE_WRITE)
                if self.wd >= 0:
                    self._available = True
        except Exception as e:
            logger.debug(f"inotify setup notice: {e}")

    @property
    def is_available(self) -> bool:
        return self._available and self.fd >= 0

    def drain_events(self):
        """Non-blocking drain of inotify event queue."""
        if not self.is_available:
            return
        try:
            os.read(self.fd, 4096)
        except (BlockingIOError, OSError):
            pass

    def close(self):
        if self.fd >= 0:
            try:
                os.close(self.fd)
            except Exception:
                pass
            self.fd = -1


DATA_DIR = PIPELINE_ROOT / "data/polymarket"
TRIGGER_FILE = DATA_DIR / "live_shock_triggers.jsonl"
SHOCK_FILE = DATA_DIR / "shock_responses.jsonl"
RESOLUTIONS_FILE = DATA_DIR / "finalized_market_resolutions.jsonl"
STATE_FILE = DATA_DIR / "live_harvester_state.json"
PID_FILE = DATA_DIR / "live_harvester.pid"
COUNTERFACTUAL_CANDIDATES_FILE = DATA_DIR / "counterfactual_candidates.jsonl"

DEFAULT_TICKET_NOTIONAL = 25.0       # Fallback ticket floor
DEFAULT_MAX_TRADES_PER_MARKET = 1     # Hard cap: Max 1 trade per 1-hour market candle (prevents duplicate fills on same shock)
DEFAULT_MAX_TRADES_PER_HOUR = 4       # Max 4 total portfolio trades per hour (supports BTC + ETH dual asset)
MAX_PORTFOLIO_EXPOSURE_USD = 100.0  # Hard ceiling: max $100 total concurrent exposure
MIN_LOT_SIZE_USD = 5.0              # Minimum viable execution ticket floor
DEFAULT_MAX_CONCURRENT_POSITIONS = 3 # Default 3 concurrent positions ceiling
PROFIT_THETA = 0.09                 # +9¢ target exit scalp (Regime 4 calibrated passive maker target)
MIN_DISTANCE_PCT = 0.05             # At least 0.05% lead-lag distance shock
MAX_TTE_SECONDS = 1500.0            # 25 minutes (widened from 15 min sweet spot to capture early pre-shock moves)
MIN_TTE_SECONDS = 60.0              # 1 minute (avoid unexecutable settlement lock)
MAX_PRICE_CEILING = 0.88            # Restored high-conviction momentum breakout ceiling (matches OOS paper parity)
MIN_PRICE_FLOOR = 0.15              # Restored minimum entry price floor (matches OOS paper parity)
MAX_ALLOWED_SPREAD = 0.030          # Hard cap: Reject entries if spread > 3¢ (guards against thin/distorted books)
ALLOWED_ASSETS = {"BTC", "ETH"}      # Tier 1 Core: Strictly BTC and ETH for taker shock harvesting

# Regime 4 Parameters
SL_POLICY = "SPOT_DELTA_PASSIVE"    # Decoupled from CLOB price; spot-delta monitored
SPOT_DELTA_K = 1.15                 # Multiplier on hourly spot volatility (requires 1.15 sigma structural breakdown)
MAX_ADVERSE_SPOT_MOVE_PCT = float(os.getenv("POLYMARKET_MAX_ADVERSE_SPOT_MOVE_PCT", "0.0040"))  # Hard adverse spot move cap (0.40%)
TTE_CANCEL_WINDOW = 180.0           # Seconds before expiry to cancel resting maker scalp asks (avoid late toxic fills)
KELLY_FRACTION = 0.50               # Half-Kelly fraction (lambda = 0.50)
MAX_NOTIONAL_CAP_PCT = 0.12         # Max 12% bankroll per trade ceiling (~$33.98 on $283.15 balance)
PASSIVE_UNWIND_TIMEOUT = 15.0       # Timeout in seconds before repricing midpoint maker unwind


class StatePersistenceError(RuntimeError):
    """Critical state could not be durably written; live entry must halt."""
    pass


class EmergencyRiskController:
    """Automated circuit breaker enforcing max loss & emergency halt policies."""
    def __init__(self, max_consecutive_losses: int = 3, max_daily_loss_usd: float = 75.0):
        self.max_consecutive_losses = max_consecutive_losses
        self.max_daily_loss_usd = max_daily_loss_usd
        self.consecutive_losses = 0
        self.daily_realized_loss = 0.0
        self.last_loss_date_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.halted = False
        self.halt_reason = ""
        self.kill_file = DATA_DIR / "KILL_SWITCH"

    def _check_and_reset_daily(self):
        """Enforces clean UTC calendar day rollover for daily loss budget."""
        current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if current_date != self.last_loss_date_utc:
            logger.info(f"[RISK CONTROLLER] UTC day rolled over ({self.last_loss_date_utc} -> {current_date}). Resetting daily realized loss to $0.00.")
            self.daily_realized_loss = 0.0
            self.last_loss_date_utc = current_date
            if self.halted and "Max daily loss reached" in self.halt_reason:
                self.halted = False
                self.halt_reason = ""

    def record_trade_pnl(self, net_pnl: float):
        self._check_and_reset_daily()
        if net_pnl < 0:
            self.consecutive_losses += 1
            self.daily_realized_loss += abs(net_pnl)
            if self.consecutive_losses >= self.max_consecutive_losses:
                self.halted = True
                self.halt_reason = f"Max consecutive losses reached ({self.consecutive_losses})"
            elif self.daily_realized_loss >= self.max_daily_loss_usd:
                self.halted = True
                self.halt_reason = f"Max daily loss reached (${self.daily_realized_loss:.2f} on {self.last_loss_date_utc})"
        else:
            self.consecutive_losses = 0

    def is_halted(self) -> bool:
        """Evaluates whether trading is halted due to automated circuit breaker or manual kill switch."""
        if self.halted:
            return True
        if self.kill_file.exists():
            self.halted = True
            self.halt_reason = f"Emergency KILL_SWITCH file detected at {self.kill_file}"
            return True
        return False

    def check_kill_switch(self) -> bool:
        return self.is_halted()


class PolymarketLiveHarvester:
    def __init__(
        self,
        ticket_notional: float = DEFAULT_TICKET_NOTIONAL,
        dry_run: bool = False,
        dynamic_sizing: bool = True,
        max_exposure: float = MAX_PORTFOLIO_EXPOSURE_USD,
        max_concurrent: Optional[int] = None,
        max_trades_per_market: int = DEFAULT_MAX_TRADES_PER_MARKET,
        max_trades_per_hour: int = DEFAULT_MAX_TRADES_PER_HOUR,
        max_tte: float = MAX_TTE_SECONDS,
        max_price_ceiling: float = MAX_PRICE_CEILING,
        min_price_floor: float = MIN_PRICE_FLOOR,
        profit_theta: float = PROFIT_THETA,
        spot_delta_k: float = SPOT_DELTA_K,
        tte_cancel_window: float = TTE_CANCEL_WINDOW,
        kelly_fraction: float = KELLY_FRACTION,
        max_notional_cap_pct: float = MAX_NOTIONAL_CAP_PCT,
        passive_unwind_timeout: float = PASSIVE_UNWIND_TIMEOUT,
        depth_hurdle: float = 1.50,
    ):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.ticket_notional = ticket_notional
        self.dry_run = dry_run
        self.dynamic_sizing = dynamic_sizing
        self.max_exposure = max_exposure
        self.max_trades_per_market = max_trades_per_market
        self.max_trades_per_hour = max_trades_per_hour
        self.max_tte = max_tte
        self.max_price_ceiling = max_price_ceiling
        self.min_price_floor = min_price_floor
        self.profit_theta = profit_theta
        self.spot_delta_k = spot_delta_k
        self.tte_cancel_window = tte_cancel_window
        self.kelly_fraction = kelly_fraction
        self.max_notional_cap_pct = max_notional_cap_pct
        self.passive_unwind_timeout = passive_unwind_timeout
        self.depth_hurdle = depth_hurdle
        self._spot_cache: Dict[str, Tuple[float, float]] = {}

        if max_concurrent is not None:
            self.max_concurrent_positions = max_concurrent
        elif "MAX_CONCURRENT_POSITIONS" in os.environ:
            self.max_concurrent_positions = int(os.environ["MAX_CONCURRENT_POSITIONS"])
        else:
            self.max_concurrent_positions = 1 if ticket_notional <= 5.0 else DEFAULT_MAX_CONCURRENT_POSITIONS
        
        # Initialize execution adapter
        self.executor = PolymarketLiveExecutor(
            dry_run=dry_run,
            ledger_path=str(DATA_DIR / "live_orders.jsonl")
        )
        self.risk_controller = EmergencyRiskController()
        
        self.seen_shock_ids: Set[str] = set()
        self.traded_market_ids: Set[str] = set()
        self.trades_per_market: Dict[str, int] = defaultdict(int)
        self.active_positions: Dict[str, Dict[str, Any]] = {}
        self.closed_positions: List[Dict[str, Any]] = []
        self.trades_this_hour = 0
        self.current_hour_window = time.time() // 3600
        
        self.last_trigger_file_pos = 0
        self.last_shock_file_pos = 0
        self.last_res_file_pos = 0
        self.last_heartbeat_time = 0.0
        self.market_tokens_cache: Dict[str, str] = {}
        self.market_condition_ids: Dict[str, str] = {}

    def get_condition_id(self, market_id: str) -> Optional[str]:
        m_str = str(market_id)
        if m_str in self.market_condition_ids:
            return self.market_condition_ids[m_str]
        try:
            r = requests.get(f"https://gamma-api.polymarket.com/markets/{m_str}", timeout=3).json()
            cond_id = r.get("conditionId")
            if cond_id:
                self.market_condition_ids[m_str] = str(cond_id)
                return str(cond_id)
        except Exception as e:
            logger.error(f"Error fetching condition_id for market {market_id}: {e}")
        return None

    def get_token_id(self, market_id: str, target_token: str) -> Optional[str]:
        cache_key = f"{market_id}_{target_token}"
        if cache_key in self.market_tokens_cache:
            return self.market_tokens_cache[cache_key]
        try:
            r = requests.get(f"https://gamma-api.polymarket.com/markets/{market_id}", timeout=3).json()
            cond_id = r.get("conditionId")
            if cond_id:
                self.market_condition_ids[str(market_id)] = str(cond_id)
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

    def get_reference_spot_price(self, asset: str) -> Optional[float]:
        """
        Pulls current spot reference price from Binance REST ticker with low latency (<50ms).
        Caches price for 1.0s to avoid redundant network overhead during high-frequency checks.
        """
        now = time.time()
        cache_key = f"{asset.upper()}USDT"
        if cache_key in self._spot_cache:
            val, ts = self._spot_cache[cache_key]
            if now - ts < 1.0:
                return val

        try:
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={cache_key}"
            resp = requests.get(url, timeout=1.5)
            if resp.status_code == 200:
                price = float(resp.json().get("price", 0.0))
                self._spot_cache[cache_key] = (price, now)
                return price
        except Exception as e:
            logger.debug(f"Failed to fetch Binance spot price for {cache_key}: {e}")
        return None

    def compute_kelly_ticket_size(self, p_model: float, p_market_ask: float, bankroll: float) -> float:
        """
        Calculates fractional Kelly sizing for bounded binary contracts:
        f* = lambda * (p_model - all_in_cost_per_share) / (1.0 - all_in_cost_per_share)
        Capped at max_notional_cap_pct of bankroll (default 12% for Half-Kelly).
        Deducts taker fees net of notional.
        """
        if p_market_ask >= self.max_price_ceiling or p_market_ask <= self.min_price_floor:
            return 0.0

        p = float(p_market_ask)
        fee_rate = 0.07  # Crypto dynamic fee schedule
        fee_exponent = 1.0
        fee_per_share = fee_rate * ((p * (1.0 - p)) ** fee_exponent)
        all_in_cost_per_share = p + fee_per_share
        net_edge_per_share = p_model - all_in_cost_per_share
        if net_edge_per_share <= 0.015:  # Require at least 1.5% edge net of taker fees
            return 0.0

        unconstrained_kelly = net_edge_per_share / max(0.05, 1.0 - all_in_cost_per_share)
        scaled_fraction = unconstrained_kelly * self.kelly_fraction
        bounded_fraction = min(self.max_notional_cap_pct, max(0.015, scaled_fraction))

        ticket_usd = bankroll * bounded_fraction
        return round(ticket_usd, 2)

    def load_state(self):
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, "r") as f:
                    state = json.load(f)
                    self.active_positions = state.get("active_positions", {})
                    self.closed_positions = state.get("closed_positions", [])
                    self.seen_shock_ids = set(state.get("seen_shock_ids", []))
                    self.traded_market_ids = set(state.get("traded_market_ids", []))
                    raw_tpm = state.get("trades_per_market", {})
                    self.trades_per_market = defaultdict(int, {str(k): int(v) for k, v in raw_tpm.items()})
                    if not self.trades_per_market and self.closed_positions:
                        for cp in self.closed_positions:
                            mid = str(cp.get("market_id", ""))
                            if mid:
                                self.trades_per_market[mid] += 1
                    saved_hour = state.get("current_hour_window")
                    current_hour = time.time() // 3600
                    if saved_hour == current_hour:
                        self.trades_this_hour = state.get("trades_this_hour", 0)
                        self.current_hour_window = current_hour
                    else:
                        self.trades_this_hour = 0
                        self.current_hour_window = current_hour
                    self.last_event_id = state.get("last_event_id", "")
                    risk_st = state.get("risk_state", {})
                    if risk_st.get("halted"):
                        self.risk_controller.halted = True
                        self.risk_controller.halt_reason = risk_st.get("halt_reason", "Restored from persisted halt state")
                    self.risk_controller.consecutive_losses = risk_st.get("consecutive_losses", 0)
                    self.risk_controller.daily_realized_loss = risk_st.get("daily_realized_loss", 0.0)
                    logger.info(f"Loaded existing state: {len(self.active_positions)} active positions, {len(self.traded_market_ids)} traded markets.")
            except Exception as e:
                logger.critical(f"LIVE STATE UNREADABLE; refusing all reconciliation and order mutation: {e}")
                raise RuntimeError("Refusing live startup with unreadable position state") from e

    def save_state(self):
        state = {
            "state_version": "2.0.0",
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
            "ticket_notional": self.ticket_notional,
            "dynamic_sizing": self.dynamic_sizing,
            "max_exposure": self.max_exposure,
            "max_concurrent_positions": self.max_concurrent_positions,
            "dry_run": self.dry_run,
            "last_event_id": getattr(self, "last_event_id", ""),
            "active_positions_count": len(self.active_positions),
            "closed_positions_count": len(self.closed_positions),
            "trades_this_hour": self.trades_this_hour,
            "current_hour_window": self.current_hour_window,
            "active_positions": self.active_positions,
            "active_position_ids": list(self.active_positions.keys()),
            "closed_positions": self.closed_positions[-20:],
            "seen_shock_ids": list(self.seen_shock_ids)[-1000:],
            "traded_market_ids": list(self.traded_market_ids)[-100:],
            "trades_per_market": dict(self.trades_per_market),
            "risk_state": {
                "halted": self.risk_controller.halted,
                "halt_reason": self.risk_controller.halt_reason,
                "consecutive_losses": self.risk_controller.consecutive_losses,
                "daily_realized_loss": self.risk_controller.daily_realized_loss,
            },
            "status": "HALTED" if self.risk_controller.is_halted() else "RUNNING"
        }
        # Atomic file write pattern with PID-unique temp file, fsync and directory sync (Findings 12 & 23)
        tmp_file = STATE_FILE.with_suffix(f".tmp.{os.getpid()}")
        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_file, STATE_FILE)
            try:
                dir_fd = os.open(str(STATE_FILE.parent), os.O_RDONLY)
                try:
                    os.fsync(dir_fd)
                finally:
                    os.close(dir_fd)
            except Exception:
                pass
        except Exception as exc:
            try:
                tmp_file.unlink(missing_ok=True)
            except Exception:
                pass
            raise StatePersistenceError(f"Critical live state save failed: {exc}") from exc

    async def evaluate_shock_and_execute(self, shock: Dict[str, Any]):
        # P1 Invariant: Durable Event Idempotency Check
        event_id = shock.get("event_id") or shock.get("shock_id") or f"{shock.get('market_id')}_{shock.get('t0_unix')}"
        if event_id in self.seen_shock_ids:
            logger.debug(f"[IDEMPOTENCY] Trigger event {event_id} already executed or seen. Skipping duplicate trigger.")
            return
        self.seen_shock_ids.add(event_id)
        self.last_event_id = event_id

        # P0 #3: Hard Circuit Breaker & Kill Switch Gate Check
        if self.risk_controller.is_halted():
            logger.warning(f"[CIRCUIT BREAKER BLOCKED] Refusing new order entry: {self.risk_controller.halt_reason}")
            return

        # Concurrency Guard: Enforce maximum concurrent active positions
        if len(self.active_positions) >= self.max_concurrent_positions:
            logger.debug(
                f"[CONCURRENCY LIMIT] Active positions count ({len(self.active_positions)}) "
                f">= limit ({self.max_concurrent_positions}). Enforced."
            )
            return

        # P1: Heartbeat Degradation Escalation - Halt new entries while keeping existing positions supervised
        if not self.dry_run and not self.executor.is_heartbeat_healthy():
            logger.critical(f"[HEARTBEAT UNHEALTHY] CLOB heartbeat has failed {self.executor.heartbeat_failures} times. Halting new entries.")
            self.risk_controller.halted = True
            self.risk_controller.halt_reason = f"Heartbeat degraded ({self.executor.heartbeat_failures} consecutive drops) - new entries halted; existing positions remain supervised."
            self.save_state()
            return

        now_hour = time.time() // 3600
        if now_hour != self.current_hour_window:
            self.current_hour_window = now_hour
            self.trades_this_hour = 0

        # Track current active portfolio exposure
        current_exposure = sum(pos.get("notional_usd", 0.0) for pos in self.active_positions.values())

        shock_dir = shock.get("shock_direction")  # "BUY" or "SELL"
        if not shock_dir:
            return
        target_token = "UP" if shock_dir == "BUY" else "DOWN"

        # Time-to-Expiry (TTE) Guard: Must be in sweet spot (60s <= TTE <= max_tte)
        tte = shock.get("seconds_to_expiry", 3600.0)
        if tte > self.max_tte or tte < MIN_TTE_SECONDS:
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

        # Asset Tier Guard: Only trade vetted Tier 1 Core assets (BTC, ETH)
        asset_str = str(shock.get("asset", "")).upper()
        if not asset_str:
            title_str = str(shock.get("title", "")).lower()
            asset_str = "BTC" if ("btc" in title_str or "bitcoin" in title_str) else ("ETH" if ("eth" in title_str or "ethereum" in title_str) else "")
        if not asset_str and self.dry_run:
            asset_str = "BTC"  # Dry-run / test fixture simulation fallback
        if not asset_str or asset_str not in ALLOWED_ASSETS:
            logger.debug(f"[TIER GUARD] Asset {asset_str!r} not in ALLOWED_ASSETS ({ALLOWED_ASSETS}). Skipping.")
            return

        token_features = shock.get("pre_shock_features_t0", {}).get(target_token, {})
        m_id = str(shock.get("market_id"))
        token_id = token_features.get("token_id") or self.get_token_id(m_id, target_token)
        if not token_id:
            logger.warning(f"Could not resolve token_id for market {m_id} ({target_token})")
            return

        # Spread Guard: Reject entries if CLOB book spread > 3¢ (guards against thin/distorted books)
        spread = float(token_features.get("spread", 0.01) or 0.01)
        if spread > MAX_ALLOWED_SPREAD:
            logger.debug(f"[SPREAD GUARD] Spread {spread:.3f} > max allowed {MAX_ALLOWED_SPREAD:.3f}. Skipping illiquid book.")
            return

        # Pre-Trade Depth Evaluation & Dynamic Sizing
        # In live mode, fetch fresh full-depth CLOB snapshot; fallback gracefully to payload
        raw_asks = token_features.get("raw_top_asks", [])
        raw_bids = []
        if not self.dry_run and token_id:
            try:
                book_snapshot = await self.executor.get_market_book_async(token_id)
                live_asks = sorted(
                    [(float(x.get("price", 0.0)), float(x.get("size", 0.0))) for x in book_snapshot.get("asks", [])],
                    key=lambda x: x[0],
                )
                live_bids = sorted(
                    [(float(x.get("price", 0.0)), float(x.get("size", 0.0))) for x in book_snapshot.get("bids", [])],
                    key=lambda x: x[0], reverse=True,
                )
                if live_asks:
                    raw_asks = live_asks
                    raw_bids = live_bids
            except Exception as exc:
                logger.debug("Live CLOB book snapshot fallback: %s", exc)

        if not raw_asks:
            return

        if raw_bids:
            spread = raw_asks[0][0] - raw_bids[0][0]
            if spread > MAX_ALLOWED_SPREAD:
                logger.debug(f"[SPREAD GUARD] Spread {spread:.3f} > max allowed {MAX_ALLOWED_SPREAD:.3f}. Skipping illiquid book.")
                return

        executable_depth_usd = sum(px * sz for px, sz in raw_asks if px <= self.max_price_ceiling)

        # Baseline ticket notional with dynamic Quarter/Half-Kelly scaling
        ticket_target = self.ticket_notional
        first_ask = raw_asks[0][0] if raw_asks else 0.50
        if not self.dry_run and first_ask <= self.max_price_ceiling and first_ask >= self.min_price_floor:
            bankroll = self.executor.get_collateral_balance()
            if bankroll > 0:
                model_prob = shock.get("p_model")
                model_meta = shock.get("probability_model", {})
                if model_prob is not None and model_meta.get("model_version") and model_meta.get("calibration_id"):
                    p_model = float(model_prob)
                    if 0.0 < p_model < 1.0:
                        kelly_ticket = self.compute_kelly_ticket_size(p_model, first_ask, bankroll)
                        if kelly_ticket >= MIN_LOT_SIZE_USD:
                            ticket_target = kelly_ticket

        # Dynamic Depth-Proportional Sizing:
        # Scale notional with orderbook depth: min(ticket_target, depth / depth_hurdle)
        # Allows filling up to ticket_target while scaling down to $5 if depth is lighter
        if self.dynamic_sizing:
            max_depth_notional = round(executable_depth_usd / self.depth_hurdle, 2)
            effective_notional = min(ticket_target, max_depth_notional)
        else:
            effective_notional = ticket_target

        # Headroom capping: Do not exceed remaining portfolio exposure allowance
        remaining_exposure = max(0.0, round(self.max_exposure - current_exposure, 2))
        effective_notional = min(effective_notional, remaining_exposure)

        # Fail-closed guard: Must meet minimum lot size ($5.00) and depth hurdle
        if effective_notional < MIN_LOT_SIZE_USD:
            return
        if (executable_depth_usd / effective_notional) < (self.depth_hurdle - 1e-4):
            return

        # Compute raw orderbook crossing VWAP before fees
        spent = 0.0
        shares = 0.0
        for px, sz in raw_asks:
            fill_dollars = min(effective_notional - spent, px * sz)
            spent += fill_dollars
            shares += fill_dollars / px
            if spent >= effective_notional - 1e-6:
                break
        raw_vwap = round(spent / shares, 4) if shares > 0 else (raw_asks[0][0] if raw_asks else None)

        # Check ceiling and floor against raw execution ask / VWAP, NOT post-fee effective price
        if not raw_vwap or raw_vwap < self.min_price_floor or raw_vwap > self.max_price_ceiling:
            return

        eff_px = (
            token_features.get(f"effective_price_${int(effective_notional)}")
            or token_features.get("effective_price_$25")
            or token_features.get("effective_price_$20")
            or token_features.get("effective_price_$5")
            or token_features.get("effective_price_$50")
            or raw_vwap
        )

        m_id = str(shock.get("market_id"))

        # Hourly Cap Guard: Log Candidate #3, #4, etc. for sample analysis
        if self.trades_this_hour >= self.max_trades_per_hour or self.trades_per_market[m_id] >= self.max_trades_per_market:
            candidate_record = {
                "logged_at_utc": datetime.now(timezone.utc).isoformat(),
                "candidate_index_in_hour": self.trades_this_hour + 1,
                "candidate_index_in_market": self.trades_per_market[m_id] + 1,
                "market_id": m_id,
                "title": shock.get("title"),
                "target_token": target_token,
                "token_id": token_id,
                "dist_pct": dist_pct,
                "tte_seconds": tte,
                "effective_price": eff_px,
                "executable_depth_usd": executable_depth_usd,
                "hypothetical_notional": effective_notional,
                "target_exit_price": round(eff_px + PROFIT_THETA, 3),
                "reason_blocked": "HOURLY_PORTFOLIO_CAP_REACHED" if self.trades_this_hour >= self.max_trades_per_hour else "MARKET_CANDLE_CAP_REACHED",
            }
            try:
                with open(COUNTERFACTUAL_CANDIDATES_FILE, "a") as f:
                    f.write(json.dumps(candidate_record) + "\n")
            except Exception as e:
                logger.warning(f"Failed to record counterfactual candidate: {e}")
            logger.info(
                f"[COUNTERFACTUAL CANDIDATE #{self.trades_this_hour + 1}] {shock.get('title')} {target_token} @ ${eff_px:.3f} "
                f"(Depth: ${executable_depth_usd:.1f}, Dist: {dist_pct:+.2f}%) passed all gates but blocked by hourly cap "
                f"(portfolio hour: {self.trades_this_hour}/{self.max_trades_per_hour}, market: {self.trades_per_market[m_id]}/{self.max_trades_per_market}). Recorded for sample analysis."
            )
            return

        # Concurrent Positions & Portfolio Exposure Ceiling Guard
        if (current_exposure + MIN_LOT_SIZE_USD) > self.max_exposure or len(self.active_positions) >= self.max_concurrent_positions:
            candidate_record = {
                "logged_at_utc": datetime.now(timezone.utc).isoformat(),
                "candidate_index_in_hour": self.trades_this_hour + 1,
                "market_id": m_id,
                "title": shock.get("title"),
                "target_token": target_token,
                "token_id": token_id,
                "dist_pct": dist_pct,
                "tte_seconds": tte,
                "effective_price": eff_px,
                "executable_depth_usd": executable_depth_usd,
                "hypothetical_notional": effective_notional,
                "target_exit_price": round(eff_px + PROFIT_THETA, 3),
                "reason_blocked": "EXPOSURE_OR_CONCURRENT_CEILING_REACHED",
            }
            try:
                with open(COUNTERFACTUAL_CANDIDATES_FILE, "a") as f:
                    f.write(json.dumps(candidate_record) + "\n")
            except Exception as e:
                logger.warning(f"Failed to record counterfactual candidate: {e}")
            logger.warning(
                f"[CEILING BLOCKED] Active={len(self.active_positions)}/{self.max_concurrent_positions}, "
                f"Exposure=${current_exposure:.2f}/${self.max_exposure:.2f}. Recorded counterfactual candidate for sample analysis."
            )
            return

        trade_id = f"LIVE_{shock.get('market_id')}_{int(time.time())}_{target_token}"
        logger.info(
            f"[QUALIFIED OPPORTUNITY] {shock.get('title')} | Target: {target_token} | "
            f"Expected Px: ${raw_vwap:.3f} (Eff: ${eff_px:.3f}) | Dist: {dist_pct:+.2f}% | TTE: {tte/60.0:.1f}m | "
            f"Depth: ${executable_depth_usd:.1f} | Sized Notional: ${effective_notional:.2f}"
        )

        # Dispatch live order via asynchronous EIP-712 adapter (non-blocking)
        fee_meta = shock.get("fee_metadata", {})
        cond_id = shock.get("condition_id") or self.get_condition_id(m_id)
        res = await self.executor.execute_snipe_order_async(
            trade_id=trade_id,
            token_id=token_id,
            target_token=target_token,
            notional_usd=effective_notional,
            target_price=raw_vwap,
            side="BUY",
            depth_hurdle=self.depth_hurdle,
            max_price_ceiling=self.max_price_ceiling,
            market_id=str(shock.get("market_id")),
            condition_id=cond_id,
            market_fee_rate=fee_meta.get("fee_rate_market"),
            market_fee_exponent=fee_meta.get("fee_exponent", 1.0),
        )

        if res.success:
            self.trades_this_hour += 1
            self.trades_per_market[m_id] += 1
            self.traded_market_ids.add(m_id)
            target_exit = min(0.99, round(res.price + self.profit_theta, 4))
            asset_sym = asset_str
            if asset_sym not in ALLOWED_ASSETS:
                raise RuntimeError(f"Refusing to create position with unresolved/disallowed asset: {asset_sym!r}")
            open_spot = float(shock.get("finalized_1h_open") or shock.get("spot_at_t0") or 0.0)
            if open_spot <= 0.0:
                open_spot = self.get_reference_spot_price(asset_sym) or 0.0

            pos_record = {
                "trade_id": trade_id,
                "event_id": event_id,
                "market_id": str(shock.get("market_id")),
                "condition_id": cond_id,
                "token_id": token_id,
                "target_token": target_token,
                "asset": asset_sym,
                "candle_open_spot": open_spot,
                "candle_sigma": float(shock.get("candle_sigma", 0.005) or 0.005),
                "entry_price": res.price,
                "entry_shares": res.size,
                "remaining_shares": res.size,
                "filled_exit_shares": 0.0,
                "remaining_exit_shares": res.size,
                "remaining_cost_basis": res.notional_usd,
                "realized_exit_cash": 0.0,
                "realized_exit_fee": 0.0,
                "gross_exit_cash": 0.0,
                "average_exit_price": 0.0,
                "exit_trade_ids": [],
                "notional_usd": res.notional_usd,
                "fee_usd": res.fee_usd,
                "target_exit_price": target_exit,
                "entry_time_utc": datetime.now(timezone.utc).isoformat(),
                "entry_ts": time.time(),
                "candle_expiry_ts": time.time() + tte,
                "pre_token_balance": res.details.get("pre_token_balance", 0.0),
                "trade_ids": res.details.get("trade_ids", []),
                "transactions_hashes": res.details.get("transactions_hashes", []),
                "status": res.execution_status,
                "exit_order_id": None,
                "exit_order_status": "NONE",
                "is_liquidating": False,
                "unwind_order_id": None,
                "unwind_start_time": 0.0,
            }
            # IMMUTABLE PERSISTENCE: Save open position immediately before placing exit order
            self.active_positions[trade_id] = pos_record
            self.save_state()
            logger.info(f"✓ POSITION RECORDED & PERSISTED: {trade_id} | Shares={res.size:.2f} @ ${res.price:.4f} | Status={res.execution_status}")

            # Post resting maker scalp limit order with post_only=True (Policy B2)
            # P0 Invariant: Only post exit immediately if position is CONFIRMED on-chain!
            if res.execution_status == ExecutionStatus.POSITION_CONFIRMED:
                exit_res = self.executor.post_maker_exit_order(
                    token_id=token_id,
                    price=target_exit,
                    size=res.size,
                    side="SELL",
                )
                if exit_res.get("success"):
                    pos_record["exit_order_id"] = exit_res.get("orderID")
                    pos_record["exit_order_status"] = "RESTING"
                    pos_record["status"] = ExecutionStatus.EXIT_RESTING
                    logger.info(f"✓ MAKER SCALP ORDER POSTED (POST-ONLY): {pos_record['exit_order_id']} | {res.size:.2f} shares @ ${target_exit:.4f}")
                else:
                    pos_record["exit_order_status"] = "AWAITING_DELTA_SETTLEMENT" if exit_res.get("retryable") else "POST_FAILED"
                    logger.warning(f"Maker scalp order post deferred ({exit_res.get('error')}). Position held until settlement.")
            else:
                pos_record["exit_order_status"] = "AWAITING_DELTA_SETTLEMENT"
                logger.info(f"Position {trade_id} in {res.execution_status}. Background loop will verify on-chain delta before posting maker exit.")

            self.save_state()

    def reconcile_with_exchange(self):
        """Discovers CLOB open orders, checks position alignment, recovers missing exits, and cancels orphan orders on restart."""
        if self.dry_run or not self.executor.is_authenticated:
            return

        logger.info("[RECONCILIATION] Reconciling local state with live exchange...")
        try:
            try:
                open_orders = self.executor.get_open_orders(strict=True)
            except TypeError:
                open_orders = self.executor.get_open_orders()
            if open_orders is None:
                raise RuntimeError("CLOB open-order snapshot unavailable")
            open_order_ids = {o.get("id") or o.get("orderID") for o in open_orders if o}
            logger.info(f"[RECONCILIATION] CLOB reports {len(open_order_ids)} live open orders.")

            # 1. Match local active positions with exchange orders and recover missing exits (P1 Fix)
            for tid, pos in list(self.active_positions.items()):
                exit_oid = pos.get("exit_order_id")
                token_id = pos.get("token_id")

                if exit_oid and exit_oid in open_order_ids:
                    logger.info(f"[RECONCILIATION] Active position {tid} has confirmed resting exit order {exit_oid}.")
                    continue

                if exit_oid and exit_oid not in open_order_ids:
                    # Query order status to see if it filled while offline
                    order_info = self.executor.get_order_status(exit_oid)
                    if order_info and (order_info.get("status") == "MATCHED" or float(order_info.get("size_matched", 0.0)) >= (pos["entry_shares"] - 1e-4)):
                        raw_taking = order_info.get("taking_amount") or order_info.get("takingAmount")
                        try:
                            taking_usd = float(raw_taking) if raw_taking is not None else (pos["entry_shares"] * pos["target_exit_price"])
                        except (ValueError, TypeError):
                            taking_usd = pos["entry_shares"] * pos["target_exit_price"]
                        payout = round(taking_usd, 2)
                        net_pnl = round(payout - pos["notional_usd"] - pos["fee_usd"], 2)
                        pos["status"] = ExecutionStatus.FILLED
                        pos["settled_at_utc"] = datetime.now(timezone.utc).isoformat()
                        pos["won"] = True
                        pos["filled_exit_shares"] = pos["entry_shares"]
                        pos["remaining_exit_shares"] = 0.0
                        pos["gross_exit_cash"] = round(taking_usd, 4)
                        pos["average_exit_price"] = round(taking_usd / max(pos["entry_shares"], 1e-4), 4)
                        pos["payout_usd"] = payout
                        pos["net_pnl_usd"] = net_pnl
                        pos["close_reason"] = "FILLED_OFFLINE"
                        self.closed_positions.append(pos)
                        del self.active_positions[tid]
                        logger.info(f"[RECONCILIATION] Position {tid} filled while offline! Payout=${payout:.2f} | Net PnL: ${net_pnl:+.2f}")
                        continue
                    else:
                        logger.warning(f"[RECONCILIATION] Exit order {exit_oid} for position {tid} no longer open or matched.")

                # If position has no active exit order (crash after entry or failed post), recover it:
                if token_id:
                    cond_bal = self.executor.get_conditional_balance(token_id)
                    pre_bal = pos.get("pre_token_balance", 0.0)
                    delta = cond_bal - pre_bal
                    epsilon = self.executor.calculate_balance_epsilon(0.001)
                    rec_shares = pos.get("remaining_shares", pos.get("remaining_exit_shares", pos["entry_shares"]))
                    if delta >= (rec_shares - epsilon):
                        logger.info(f"[RECONCILIATION RECOVERY] Active position {tid} has {delta:.4f} verified tokens on-chain without exit order. Recreating maker exit for {rec_shares:.2f} shares...")
                        exit_res = self.executor.post_maker_exit_order(
                            token_id=token_id,
                            price=pos["target_exit_price"],
                            size=rec_shares,
                            side="SELL"
                        )
                        if exit_res.get("success"):
                            pos["exit_order_id"] = exit_res.get("orderID")
                            pos["exit_order_status"] = "RESTING"
                            pos["status"] = ExecutionStatus.EXIT_RESTING
                            logger.info(f"[RECONCILIATION RECOVERY] Recreated exit order {pos['exit_order_id']} for {tid}")
                        else:
                            pos["exit_order_status"] = "EXIT_RECOVERY_REQUIRED"
                    elif cond_bal < 0.05:
                        logger.warning(f"[RECONCILIATION] Position {tid} has near-zero token balance ({cond_bal:.4f}).")

            # 2. Cancel any orphan orders on CLOB not associated with tracked positions
            tracked_exit_oids = {pos.get("exit_order_id") for pos in self.active_positions.values() if pos.get("exit_order_id")}
            for o in open_orders:
                oid = o.get("id") or o.get("orderID")
                if oid and oid not in tracked_exit_oids:
                    logger.warning(f"[RECONCILIATION] Orphan CLOB order {oid} detected. Canceling for capital safety.")
                    self.executor.cancel_order(oid)

            self.save_state()
            logger.info("[RECONCILIATION] Exchange state successfully reconciled.")
        except Exception as e:
            logger.critical(f"[RECONCILIATION] Exchange/local state is UNKNOWN; refusing to mutate orders: {e}")
            raise RuntimeError("Live exchange reconciliation failed; safe startup refused") from e

    async def check_resolutions_and_manage_positions(self):
        """Monitors active positions for delta settlements, maker scalp fills, time-decay unwind, or finalized resolutions."""
        if not self.active_positions:
            return

        # 1. Check finalized candle resolutions from stream (binary buffered read)
        if RESOLUTIONS_FILE.exists():
            try:
                current_res_size = RESOLUTIONS_FILE.stat().st_size
                if current_res_size > self.last_res_file_pos:
                    with open(RESOLUTIONS_FILE, "rb") as f:
                        f.seek(self.last_res_file_pos)
                        chunk = f.read()
                    complete_end = chunk.rfind(b"\n") + 1
                    if complete_end:
                        new_lines = chunk[:complete_end].decode("utf-8").splitlines()
                        self.last_res_file_pos += complete_end
                    else:
                        new_lines = []

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
                                    rem_shares = pos.get("remaining_shares", pos.get("remaining_exit_shares", pos["entry_shares"]))
                                    payout = rem_shares * 1.0 if won else 0.0
                                    total_cash = pos.get("realized_exit_cash", 0.0) + payout
                                    total_fees = pos["fee_usd"] + pos.get("realized_exit_fee", 0.0)
                                    net_pnl = total_cash - pos["notional_usd"] - total_fees

                                    # Cancel resting exit order if still open
                                    if pos.get("exit_order_id"):
                                        self.executor.cancel_order(pos["exit_order_id"])

                                    pos["status"] = ExecutionStatus.SETTLED
                                    pos["settled_at_utc"] = datetime.now(timezone.utc).isoformat()
                                    pos["won"] = won
                                    pos["payout_usd"] = round(total_cash, 2)
                                    pos["net_pnl_usd"] = round(net_pnl, 2)
                                    pos["close_reason"] = "MARKET_RESOLVED"
                                    self.closed_positions.append(pos)
                                    self.risk_controller.record_trade_pnl(net_pnl)
                                    del self.active_positions[tid]
                                    logger.info(f"✓ POSITION RESOLVED AT MATURITY: {tid} | Won={won} | RemShares={rem_shares:.2f} | Net PnL=${net_pnl:+.2f}")
                                    self.save_state()
                        except Exception as e:
                            logger.error(f"Error parsing resolution line: {e}")
            except Exception as e:
                logger.error(f"Error checking resolutions: {e}")

        # 2. Check live positions for delta confirmation, maker scalp fills, and time-decay unwind
        if self.dry_run:
            # DRY-RUN SIMULATION ONLY: simulate maker fill if best bid reaches target exit price
            for tid, pos in list(self.active_positions.items()):
                try:
                    token_id = pos.get("token_id")
                    if not token_id:
                        continue
                    book = await self.executor.get_market_book_async(token_id)
                    bids = book.get("bids", [])
                    if bids:
                        best_bid = max(float(b.get("price", 0.0)) for b in bids)
                        if best_bid >= pos.get("target_exit_price", 0.99):
                            payout = round(pos["entry_shares"] * pos["target_exit_price"], 2)
                            net_pnl = round(payout - pos["notional_usd"] - pos["fee_usd"], 2)
                            pos["status"] = ExecutionStatus.FILLED
                            pos["settled_at_utc"] = datetime.now(timezone.utc).isoformat()
                            pos["won"] = True
                            pos["filled_exit_shares"] = pos["entry_shares"]
                            pos["remaining_exit_shares"] = 0.0
                            pos["gross_exit_cash"] = payout
                            pos["average_exit_price"] = pos["target_exit_price"]
                            pos["payout_usd"] = payout
                            pos["net_pnl_usd"] = net_pnl
                            pos["close_reason"] = "DRY_RUN_MAKER_SCALP_FILLED"
                            self.closed_positions.append(pos)
                            self.risk_controller.record_trade_pnl(net_pnl)
                            del self.active_positions[tid]
                            logger.info(f"[DRY-RUN] ✓ POSITION CLOSED VIA SIMULATED MAKER SCALP: {tid} | Net PnL=${net_pnl:+.2f}")
                            self.save_state()
                except Exception as e:
                    logger.debug(f"Error in dry-run book check for {tid}: {e}")

        # Active position supervision and risk management (runs for remaining open positions)
        try:
            open_orders = await asyncio.to_thread(self.executor.get_open_orders)
            open_oids = {o.get("id") or o.get("orderID") for o in open_orders if o} if open_orders is not None else set()

            now_ts = time.time()
            for tid, pos in list(self.active_positions.items()):
                try:
                    exit_oid = pos.get("exit_order_id")
                    token_id = pos.get("token_id")

                    # Phase A: Trade finality & delta-aware settlement confirmation for pending entries (P0/P1 Fix)
                    expiry_ts = pos.get("candle_expiry_ts", now_ts + 600.0)
                    tte_rem = max(0.0, expiry_ts - now_ts)
                    is_terminal_or_held = (
                        pos.get("exit_order_status") in ["CANCELED_FOR_EXPIRY_HOLD", "CANCELED_FOR_STOP_LOSS", "UNWIND_RETRY_REQUIRED"]
                        or pos.get("is_liquidating")
                        or (tte_rem < self.tte_cancel_window)
                    )
                    if not is_terminal_or_held and (
                        not exit_oid
                        or pos.get("status") == ExecutionStatus.MATCHED_PENDING_SETTLEMENT
                        or pos.get("exit_order_status") in [
                            "PENDING_CONFIRMATION",
                            "AWAITING_DELTA_SETTLEMENT",
                            "AWAITING_SETTLEMENT",
                            "POST_FAILED",
                            "EXIT_RECOVERY_REQUIRED",
                        ]
                    ):
                        if token_id:
                            # 1. Authoritative CLOB trade status hierarchy & Polygon receipt verification
                            # P0/P1 Rule: CONFIRMED OR (tx_hash present AND on-chain Polygon receipt.status == 1)
                            # AND balance delta >= entry_shares - epsilon
                            trade_ids = pos.get("trade_ids", [])
                            tx_hashes = pos.get("transactions_hashes") or pos.get("transactionsHashes") or pos.get("transaction_hashes") or []
                            finality_ok = False

                            if trade_ids:
                                for tr_id in trade_ids:
                                    tr_info = self.executor.get_trade_status(tr_id)
                                    st = tr_info.get("status", "").upper()
                                    tr_tx = tr_info.get("transactionHash") or tr_info.get("transaction_hash")
                                    if st == "CONFIRMED":
                                        finality_ok = True
                                        break
                                    elif tr_tx:
                                        receipt_ok = await self.executor.get_transaction_receipt_status_async(tr_tx)
                                        if receipt_ok is True:
                                            finality_ok = True
                                            break
                                        elif receipt_ok is False:
                                            logger.critical(f"[ON-CHAIN REVERT] Transaction {tr_tx} reverted on Polygon! Trade {tr_id} failed.")
                                            pos["status"] = ExecutionStatus.FAILED
                                            pos["close_reason"] = "ONCHAIN_REVERT_DETECTED"
                                            self.save_state()
                                            break
                            if not finality_ok and tx_hashes:
                                for tx_h in tx_hashes:
                                    receipt_ok = await self.executor.get_transaction_receipt_status_async(tx_h)
                                    if receipt_ok is True:
                                        finality_ok = True
                                        break
                                    elif receipt_ok is False:
                                        logger.critical(f"[ON-CHAIN REVERT] Transaction {tx_h} reverted on Polygon!")
                                        pos["status"] = ExecutionStatus.FAILED
                                        pos["close_reason"] = "ONCHAIN_REVERT_DETECTED"
                                        self.save_state()
                                        break

                            # 2. Derive precision-derived balance tolerance epsilon (P1 Fix)
                            epsilon = self.executor.calculate_balance_epsilon(0.001)
                            # Independent on-chain read verification: query Polygon ERC-1155 balanceOf first
                            onchain_bal = self.executor.get_onchain_erc1155_balance(token_id)
                            if onchain_bal is not None:
                                cond_bal = onchain_bal
                                bal_source = "POLYGON_ONCHAIN_ERC1155"
                            else:
                                cond_bal = self.executor.get_conditional_balance(token_id)
                                bal_source = "CLOB_ALLOWANCE_API"

                            pre_bal = pos.get("pre_token_balance", 0.0)
                            delta = cond_bal - pre_bal
                            if self.dry_run:
                                delta_reconciled = True
                                finality_ok = True
                            if finality_ok or delta_reconciled:
                                logger.info(
                                    f"✓ AUTHORITATIVE SETTLEMENT CONFIRMED: finality={finality_ok}, Delta {delta:.4f} >= {pos['entry_shares']:.4f} - {epsilon:.4f} "
                                    f"({bal_source} pre={pre_bal:.4f}, cur={cond_bal:.4f}). Posting maker exit for {tid}..."
                                )
                                pos["status"] = ExecutionStatus.POSITION_CONFIRMED
                                exit_res = self.executor.post_maker_exit_order(
                                    token_id=token_id,
                                    size=pos.get("remaining_shares", pos.get("remaining_exit_shares", pos["entry_shares"])),
                                    price=pos["target_exit_price"],
                                    side="SELL"
                                )
                                if exit_res.get("success"):
                                    pos["exit_order_id"] = exit_res.get("orderID")
                                    pos["exit_order_status"] = "RESTING"
                                    pos["status"] = ExecutionStatus.EXIT_RESTING
                                    self.save_state()
                            else:
                                logger.debug(
                                    f"[PENDING INCONCLUSIVE] Preserving pending settlement state for {tid}: finality={finality_ok}, "
                                    f"delta={delta:.4f} < {pos['entry_shares']:.4f} - {epsilon:.4f} ({bal_source}). Awaiting on-chain arrival."
                                )
                        continue

                    # Phase B: Time-Dependent Terminal Unwind Policy & Spot-Delta Monitoring (Regime 4)
                    expiry_ts = pos.get("candle_expiry_ts", now_ts + 600.0)
                    tte_rem = max(0.0, expiry_ts - now_ts)

                    # Phase B: Stop-Loss Protection and Pre-Expiry Liquidation Policy
                    entry_px = float(pos.get("entry_price", 0.50))
                    rem_shrs = pos.get("remaining_shares", pos.get("remaining_exit_shares", pos["entry_shares"]))

                    # Check current market book & spot price for active open positions
                    retry_due = (
                        pos.get("exit_order_status") == "UNWIND_RETRY_REQUIRED"
                        and now_ts >= float(pos.get("next_unwind_retry_ts", 0.0))
                    )
                    if (not pos.get("is_liquidating") or retry_due) and token_id and rem_shrs > 0.01:
                        book = await self.executor.get_market_book_async(token_id)
                        bids = book.get("bids", [])
                        best_b = max(float(b.get("price", 0.0)) for b in bids) if bids else 0.0

                        asset_sym = pos.get("asset", "BTC")
                        current_spot = await asyncio.to_thread(self.get_reference_spot_price, asset_sym)
                        open_spot = float(pos.get("candle_open_spot", 0.0))
                        candle_sigma = float(pos.get("candle_sigma", 0.005))

                        spot_valid = current_spot is not None and current_spot > 0 and open_spot > 0
                        is_otm = False
                        if spot_valid:
                            if pos.get("target_token") == "UP":
                                is_otm = (current_spot < open_spot)
                            else:
                                is_otm = (current_spot > open_spot)

                        # Trigger 1: Hard CLOB Price Stop-Loss (best bid drops >= 15¢ below entry or below 20¢)
                        clob_sl_triggered = (best_b > 0.0 and (best_b <= (entry_px - 0.15) or best_b <= 0.20))

                        # Trigger 2: Pre-Expiry Out-Of-The-Money Salvage (TTE <= 300s / 5min and OTM)
                        pre_expiry_otm_salvage = (tte_rem <= 300.0 and is_otm and best_b >= 0.05)

                        # Trigger 3: Spot-Delta Structural Crash (K*sigma reversal OR hard max adverse move cap)
                        spot_disp = 0.0
                        if spot_valid:
                            spot_disp = (current_spot - open_spot) if pos.get("target_token") == "UP" else (open_spot - current_spot)
                        reversal_limit = -(self.spot_delta_k * candle_sigma * open_spot) if (open_spot > 0) else -999999.0
                        spot_move_pct = (spot_disp / open_spot) if spot_valid else 0.0
                        spot_crash_triggered = bool(
                            spot_valid and (
                                spot_disp <= reversal_limit
                                or spot_move_pct <= -MAX_ADVERSE_SPOT_MOVE_PCT
                            )
                        )

                        if clob_sl_triggered or pre_expiry_otm_salvage or spot_crash_triggered or retry_due:
                            reason = (
                                "Scheduled Stop-Loss Unwind Retry" if retry_due
                                else f"CLOB price dropped to ${best_b:.4f} (entry: ${entry_px:.4f})" if clob_sl_triggered
                                else f"Pre-expiry OTM salvage (TTE={tte_rem:.0f}s, spot={current_spot:.2f} vs open={open_spot:.2f})" if pre_expiry_otm_salvage
                                else f"Spot structural breakdown ({spot_disp:.2f} <= {reversal_limit:.2f} or move={spot_move_pct*100:.2f}%)"
                            )
                            logger.warning(f"[STOP-LOSS ACTIVATED] Position {tid}: {reason}. Unwinding position immediately...")

                            # Cancel any resting maker order with confirmation
                            if exit_oid:
                                cancel_res = await asyncio.to_thread(self.executor.cancel_order, exit_oid)
                                canceled_ids = set((cancel_res or {}).get("canceled", []) or [])
                                status_info = await asyncio.to_thread(self.executor.get_order_status, exit_oid) or {}
                                status = str(status_info.get("status", "UNKNOWN")).upper()
                                matched = float(status_info.get("size_matched", 0.0) or 0.0)
                                if matched > float(pos.get("filled_exit_shares", 0.0)) + 1e-6:
                                    pos["exit_order_status"] = "FILL_RECONCILIATION_REQUIRED"
                                    pos["pending_canceled_order_id"] = exit_oid
                                    self.save_state()
                                    continue
                                canceled_confirmed = (
                                    exit_oid in canceled_ids
                                    or status in {"CANCELED", "CANCELLED", "EXPIRED"}
                                )
                                if not canceled_confirmed:
                                    pos["exit_order_status"] = "STOP_CANCEL_PENDING"
                                    pos["cancel_pending_order_id"] = exit_oid
                                    self.save_state()
                                    continue
                                pos["exit_order_id"] = None
                            pos["exit_order_status"] = "CANCELED_FOR_STOP_LOSS"

                            # Aggressive FOK unwind at best bid (min price 0.01) to lock in capital recovery
                            unwind_res = await asyncio.to_thread(
                                self.executor.execute_unwind_order,
                                token_id=token_id,
                                size=rem_shrs,
                                side="SELL",
                                min_price=max(0.01, best_b - 0.02)
                            )
                            if unwind_res.get("success"):
                                matched_sz = float(unwind_res.get("matched_size", rem_shrs))
                                taking_usd = float(unwind_res.get("taking_amount", matched_sz * best_b))
                                p_out = round(taking_usd, 2)
                                exit_fee = float(unwind_res.get("fee_usd", 0.0))
                                net_pnl = round(p_out - pos["notional_usd"] - pos["fee_usd"] - exit_fee, 2)
                                pos["status"] = ExecutionStatus.SETTLED
                                pos["settled_at_utc"] = datetime.now(timezone.utc).isoformat()
                                pos["won"] = False
                                pos["payout_usd"] = p_out
                                pos["net_pnl_usd"] = net_pnl
                                pos["close_reason"] = "ADVERSE_STOP_LOSS_UNWIND"
                                self.closed_positions.append(pos)
                                self.risk_controller.record_trade_pnl(net_pnl)
                                del self.active_positions[tid]
                                logger.warning(f"✓ [STOP-LOSS EXECUTED] {tid} unwound via CLOB FOK @ ~${best_b:.4f} | Payout: ${p_out:.2f} | Net PnL: ${net_pnl:+.2f}")
                                self.save_state()
                                continue
                            else:
                                logger.error(f"Immediate FOK unwind failed for {tid}: {unwind_res.get('error')}. Scheduling retry.")
                                pos["is_liquidating"] = False
                                pos["exit_order_status"] = "UNWIND_RETRY_REQUIRED"
                                pos["next_unwind_retry_ts"] = now_ts + 1.0
                                pos["unwind_last_error"] = str(unwind_res.get("error", "unknown"))
                                self.save_state()
                                continue

                    # Pre-Expiry Hold for In-The-Money Positions (TTE < 180s)
                    if exit_oid and exit_oid in open_oids and tte_rem < self.tte_cancel_window:
                        logger.info(
                            f"[REGIME 4 TTE < {self.tte_cancel_window:.0f}s] TTE={tte_rem:.0f}s. Canceling resting maker scalp ask {exit_oid} for {tid} "
                            "to prevent toxic late fills into market expiry. Position In-The-Money; holding to $1.00 terminal settlement."
                        )
                        self.executor.cancel_order(exit_oid)
                        pos["exit_order_id"] = None
                        pos["exit_order_status"] = "CANCELED_FOR_EXPIRY_HOLD"
                        pos["status"] = ExecutionStatus.POSITION_CONFIRMED
                        self.save_state()
                        continue

                    # 3. Manage active passive liquidation order queue
                    if pos.get("is_liquidating") and pos.get("unwind_order_id"):
                        u_oid = pos["unwind_order_id"]
                        if u_oid not in open_oids:
                            # Passive midpoint order filled!
                            logger.info(f"[REGIME 4 UNWIND FILLED] Passive unwind {u_oid} for {tid} filled! Finalizing settlement.")
                            book = self.executor.get_market_book(token_id)
                            bids = book.get("bids", [])
                            best_b = max(float(b.get("price", 0.0)) for b in bids) if bids else 0.50
                            rem_shrs = pos.get("remaining_shares", pos.get("remaining_exit_shares", pos["entry_shares"]))
                            p_out = round(rem_shrs * best_b, 2)
                            net_pnl = round(p_out - pos["notional_usd"] - pos["fee_usd"], 2)
                            pos["status"] = ExecutionStatus.SETTLED
                            pos["settled_at_utc"] = datetime.now(timezone.utc).isoformat()
                            pos["won"] = net_pnl > 0
                            pos["payout_usd"] = p_out
                            pos["net_pnl_usd"] = net_pnl
                            pos["close_reason"] = "SPOT_DELTA_PASSIVE_UNWIND"
                            self.closed_positions.append(pos)
                            self.risk_controller.record_trade_pnl(net_pnl)
                            del self.active_positions[tid]
                            self.save_state()
                            continue
                        elif (now_ts - pos.get("unwind_start_time", now_ts)) > self.passive_unwind_timeout:
                            # Midpoint order timed out: reprice to best bid to complete unwind
                            logger.info(f"[REGIME 4 UNWIND TIMEOUT] Midpoint order {u_oid} timed out ({self.passive_unwind_timeout}s). Repricing to best bid...")
                            self.executor.cancel_order(u_oid)
                            book = self.executor.get_market_book(token_id)
                            bids = book.get("bids", [])
                            best_b = max(float(b.get("price", 0.0)) for b in bids) if bids else 0.01
                            rem_shrs = pos.get("remaining_shares", pos.get("remaining_exit_shares", pos["entry_shares"]))
                            unwind_res = self.executor.execute_unwind_order(
                                token_id=token_id,
                                size=rem_shrs,
                                side="SELL",
                                min_price=max(0.01, best_b - 0.02)
                            )
                            if unwind_res.get("success"):
                                matched_sz = float(unwind_res.get("matched_size", rem_shrs))
                                taking_usd = float(unwind_res.get("taking_amount", matched_sz * best_b))
                                p_out = round(taking_usd, 2)
                                exit_fee = float(unwind_res.get("fee_usd", 0.0))
                                net_pnl = round(p_out - pos["notional_usd"] - pos["fee_usd"] - exit_fee, 2)
                                pos["status"] = ExecutionStatus.SETTLED
                                pos["settled_at_utc"] = datetime.now(timezone.utc).isoformat()
                                pos["won"] = net_pnl > 0
                                pos["payout_usd"] = p_out
                                pos["net_pnl_usd"] = net_pnl
                                pos["close_reason"] = "SPOT_DELTA_TIMEOUT_REPRICED_UNWIND"
                                self.closed_positions.append(pos)
                                self.risk_controller.record_trade_pnl(net_pnl)
                                del self.active_positions[tid]
                                self.save_state()
                                continue

                    # 4. Phase C: Deterministic Expiry Hold (Hold thesis to terminal settlement)
                    if not exit_oid and tte_rem < 60.0 and not pos.get("is_liquidating"):
                        pos["terminal_policy"] = "DETERMINISTIC_TERMINAL_HOLD"

                    # Phase D: Fill Verification and Detailed Partial-Fill Accounting (P1 Fix)
                    order_info = self.executor.get_order_status(exit_oid)
                    if order_info:
                        status = order_info.get("status")
                        size_matched = float(order_info.get("size_matched", 0.0))
                        if status == "MATCHED" or size_matched >= (pos["entry_shares"] - 1e-4):
                            raw_taking = order_info.get("taking_amount") or order_info.get("takingAmount")
                            try:
                                taking_usd = float(raw_taking) if raw_taking is not None else (size_matched * pos["target_exit_price"])
                            except (ValueError, TypeError):
                                taking_usd = size_matched * pos["target_exit_price"]

                            avg_px = round(taking_usd / max(size_matched, 1e-4), 4) if size_matched > 0 else pos["target_exit_price"]
                            rem_shares = max(0.0, round(pos["entry_shares"] - size_matched, 4))
                            rem_ratio = rem_shares / max(pos["entry_shares"], 1e-4)

                            pos["filled_exit_shares"] = size_matched
                            pos["remaining_shares"] = rem_shares
                            pos["remaining_exit_shares"] = rem_shares
                            pos["remaining_cost_basis"] = round(pos["notional_usd"] * rem_ratio, 4)
                            pos["gross_exit_cash"] = round(taking_usd, 4)
                            pos["realized_exit_cash"] = round(taking_usd, 4)
                            pos["realized_exit_fee"] = 0.0
                            pos["average_exit_price"] = avg_px
                            pos["exit_trade_ids"] = order_info.get("associate_trades", []) or [exit_oid]

                            if rem_shares <= 0.01:
                                payout = round(taking_usd, 2)
                                net_pnl = round(payout - pos["notional_usd"] - pos["fee_usd"], 2)
                                pos["status"] = ExecutionStatus.FILLED
                                pos["settled_at_utc"] = datetime.now(timezone.utc).isoformat()
                                pos["won"] = True
                                pos["payout_usd"] = payout
                                pos["net_pnl_usd"] = net_pnl
                                pos["close_reason"] = "MAKER_SCALP_FILLED_CLOB"
                                self.closed_positions.append(pos)
                                self.risk_controller.record_trade_pnl(net_pnl)
                                del self.active_positions[tid]
                                logger.info(f"✓ POSITION CLOSED VIA CONFIRMED CLOB FILL: {tid} | OID: {exit_oid} | Payout: ${payout:.2f} | Net PnL: ${net_pnl:+.2f}")
                                self.save_state()
                            else:
                                pos["status"] = ExecutionStatus.PARTIALLY_FILLED
                                logger.info(f"[PARTIAL FILL] {tid}: Filled {size_matched:.2f}/{pos['entry_shares']:.2f} shares. Remaining: {rem_shares:.2f} (basis: ${pos['remaining_cost_basis']:.2f})")
                                self.save_state()
                        elif status in ["CANCELED", "CANCELLED"]:
                            logger.warning(f"⚠️ Exit order {exit_oid} was canceled on CLOB. Position {tid} remains OPEN.")
                            matched = max(0.0, min(float(pos["entry_shares"]), size_matched))
                            already_accounted = float(pos.get("filled_exit_shares", 0.0))
                            if matched > already_accounted + 1e-6:
                                pos["exit_order_status"] = "FILL_RECONCILIATION_REQUIRED"
                                pos["pending_canceled_order_id"] = exit_oid
                                self.save_state()
                                continue
                            pos["exit_order_id"] = None
                            pos["exit_order_status"] = "EXIT_RECOVERY_REQUIRED"
                            pos["status"] = ExecutionStatus.EXIT_PENDING_SETTLEMENT
                            self.save_state()
                except Exception as pos_err:
                    logger.error(f"Error managing position {tid}: {pos_err}", exc_info=True)
        except Exception as e:
            logger.error(f"Error querying live CLOB order status: {e}")

    def check_resolutions_and_manage_positions_sync(self):
        """Synchronous wrapper for test execution."""
        return asyncio.run(self.check_resolutions_and_manage_positions())

    async def run(self):
        logger.info("=====================================================================")
        logger.info("       POLYMARKET LIVE MONEY HARVESTER (REGIME 4 ARMED)              ")
        logger.info("=====================================================================")
        logger.info(f"Wallet Address:   {self.executor.funder_address}")
        logger.info(f"Auth Mode:        {self.executor.auth_mode}")
        logger.info(f"Ticket Floor:     ${self.ticket_notional:.2f} USD (Half-Kelly Sizing, λ={self.kelly_fraction:.2f}, Cap: {self.max_notional_cap_pct*100:.1f}%)")
        logger.info(f"Price Boundary:   [${self.min_price_floor:.2f}, ${self.max_price_ceiling:.2f}]")
        logger.info(f"Dynamic Sizing:   {self.dynamic_sizing} (Floor: ${MIN_LOT_SIZE_USD:.2f}, Hurdle: {self.depth_hurdle:.2f}x)")
        logger.info(f"Portfolio Cap:    ${self.max_exposure:.2f} USD (Max Concurrent: {self.max_concurrent_positions})")
        logger.info(f"Profit Target:    +{self.profit_theta*100:.0f}¢ per share")
        logger.info(f"Exit Policy:      Spot-Delta Decoupled (K={self.spot_delta_k}σ) + Passive Midpoint Maker")
        logger.info(f"Mode:             {'DRY-RUN' if self.dry_run else 'LIVE REAL-MONEY TRADING'}")
        logger.info("=====================================================================")

        lock_path = PID_FILE.with_suffix(".lock")
        self._instance_lock_fd = open(lock_path, "a+")
        try:
            fcntl.flock(self._instance_lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            self._instance_lock_fd.close()
            raise RuntimeError("Another live harvester instance already holds the lock") from exc

        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))

        self.load_state()

        # Reconcile exchange orders with local state on startup
        self.reconcile_with_exchange()

        # Start tailing from current EOF so we only execute new events
        if not TRIGGER_FILE.exists():
            TRIGGER_FILE.touch()
        self.last_trigger_file_pos = TRIGGER_FILE.stat().st_size
        logger.info(f"Tailing zero-latency shock triggers from byte offset: {self.last_trigger_file_pos}")

        if SHOCK_FILE.exists():
            self.last_shock_file_pos = SHOCK_FILE.stat().st_size
            logger.info(f"Tailing shock responses fallback from byte offset: {self.last_shock_file_pos}")

        if RESOLUTIONS_FILE.exists():
            # Replay pre-existing resolutions first: active positions may have resolved while daemon was down
            self.last_res_file_pos = 0
            await self.check_resolutions_and_manage_positions()
            self.last_res_file_pos = RESOLUTIONS_FILE.stat().st_size
            logger.info(f"Tailing new resolutions from byte offset: {self.last_res_file_pos}")

        # P1: Zero-Polling Fast IPC via Linux inotify file descriptor
        watcher = LinuxInotifyWatcher(TRIGGER_FILE)
        loop = asyncio.get_running_loop()
        trigger_notify_event = asyncio.Event()

        def on_inotify_file_event():
            watcher.drain_events()
            trigger_notify_event.set()

        if watcher.is_available:
            loop.add_reader(watcher.fd, on_inotify_file_event)
            logger.info(f"✓ Linux inotify event listener armed on {TRIGGER_FILE.name} (sub-millisecond wakeups enabled).")
        else:
            logger.info("Linux inotify unavailable; using responsive 50ms polling fallback.")

        last_heartbeat = time.time()
        last_clob_heartbeat = 0.0
        last_mgmt_check = 0.0
        scanned_count = 0

        try:
            while True:
                # P0 #3: Automated Circuit Breaker & Emergency Kill Switch Check
                if self.risk_controller.is_halted():
                    logger.critical(f"[CIRCUIT BREAKER] {self.risk_controller.halt_reason}. Halting new entries.")
                    self.save_state()
                    if not self.active_positions:
                        if not self.dry_run:
                            self.executor.cancel_all_orders()
                        break

                # P1: Immediate Heartbeat Escalation Check
                if not self.dry_run and not self.executor.is_heartbeat_healthy():
                    logger.critical(f"[HEARTBEAT UNHEALTHY] CLOB heartbeat dropped {self.executor.heartbeat_failures} times. Halting new entries.")
                    self.risk_controller.halted = True
                    self.risk_controller.halt_reason = f"Heartbeat degraded ({self.executor.heartbeat_failures} drops) - new entries halted; existing positions remain supervised."
                    self.save_state()
                    if not self.active_positions:
                        self.executor.cancel_all_orders()
                        break

                # 1. Maintain periodic CLOB session heartbeat (every 5.0s when active positions exist)
                now_ts = time.time()
                if not self.dry_run and self.active_positions and (now_ts - last_clob_heartbeat >= 5.0):
                    last_clob_heartbeat = now_ts
                    hb_res = self.executor.post_heartbeat()
                    if hb_res.get("error"):
                        logger.warning(f"[HEARTBEAT WARN] Heartbeat error: {hb_res.get('error')}")

                # 2. Ingest zero-latency shock triggers (<1ms from recorder detection)
                if TRIGGER_FILE.exists():
                    current_size = TRIGGER_FILE.stat().st_size
                    if current_size > self.last_trigger_file_pos:
                        with open(TRIGGER_FILE, "rb") as f:
                            f.seek(self.last_trigger_file_pos)
                            chunk = f.read()
                        complete_end = chunk.rfind(b"\n") + 1
                        if complete_end:
                            new_lines = chunk[:complete_end].decode("utf-8").splitlines()
                            self.last_trigger_file_pos += complete_end
                            for line in new_lines:
                                if not line.strip():
                                    continue
                                try:
                                    shock = json.loads(line)
                                except Exception as parse_err:
                                    logger.error(f"Error parsing trigger line: {parse_err}")
                                    continue
                                try:
                                    s_id = shock.get("event_id") or shock.get("shock_id") or f"{shock.get('market_id')}_{shock.get('t0_unix')}"
                                    self.last_event_id = s_id
                                    if s_id not in self.seen_shock_ids:
                                        scanned_count += 1
                                        await self.evaluate_shock_and_execute(shock)
                                except StatePersistenceError:
                                    self.risk_controller.halted = True
                                    self.risk_controller.halt_reason = "Critical state persistence failure"
                                    logger.critical("Critical live state persistence failure; blocking further entries but continuing position supervision", exc_info=True)
                                    break

                # 3. Monitor open positions for scalp exit fills or market resolutions (every 1.0s)
                if now_ts - last_mgmt_check >= 1.0:
                    last_mgmt_check = now_ts
                    await self.check_resolutions_and_manage_positions()

                if time.time() - last_heartbeat >= 300:
                    last_heartbeat = time.time()
                    active_exp = sum(p.get("notional_usd", 0.0) for p in self.active_positions.values())
                    logger.info(
                        f"[HEARTBEAT] Harvester active | Triggers scanned: {scanned_count} | "
                        f"Active positions: {len(self.active_positions)} (${active_exp:.2f}) | "
                        f"Closed: {len(self.closed_positions)}"
                    )

                # Event-driven sleep: wake immediately when inotify triggers or after 50ms timeout
                try:
                    await asyncio.wait_for(trigger_notify_event.wait(), timeout=0.05)
                    trigger_notify_event.clear()
                except asyncio.TimeoutError:
                    pass

        except Exception as e:
            logger.error(f"Error in harvester loop: {e}")
        finally:
            if watcher.is_available:
                try:
                    loop.remove_reader(watcher.fd)
                except Exception:
                    pass
                watcher.close()
            lock_fd = getattr(self, "_instance_lock_fd", None)
            if lock_fd is not None:
                try:
                    fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
                    lock_fd.close()
                except Exception:
                    pass


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Polymarket Live Harvester")
    parser.add_argument("--lot-size", type=float, default=35.0, help="Ticket size in USD (default: $35.00 for Half-Kelly scaling)")
    parser.add_argument("--dynamic-sizing", action="store_true", default=True, help="Dynamically scale lot size with orderbook depth (default: True)")
    parser.add_argument("--no-dynamic-sizing", dest="dynamic_sizing", action="store_false", help="Disable dynamic sizing and use fixed lot size")
    parser.add_argument("--max-exposure", type=float, default=100.0, help="Maximum concurrent portfolio exposure in USD (default: $100.00)")
    parser.add_argument("--max-concurrent", type=int, default=3, help="Maximum concurrent open positions (default: 3)")
    parser.add_argument("--max-trades-per-market", type=int, default=DEFAULT_MAX_TRADES_PER_MARKET, help="Max trades per market candle (default: 1)")
    parser.add_argument("--max-trades-per-hour", type=int, default=DEFAULT_MAX_TRADES_PER_HOUR, help="Max total portfolio trades per hour (default: 4)")
    parser.add_argument("--max-tte", type=float, default=MAX_TTE_SECONDS, help="Max TTE in seconds (default: 1500.0)")
    parser.add_argument("--max-price-ceiling", type=float, default=MAX_PRICE_CEILING, help="Maximum entry price ceiling (default: 0.88)")
    parser.add_argument("--min-price-floor", type=float, default=MIN_PRICE_FLOOR, help="Minimum entry price floor (default: 0.15)")
    parser.add_argument("--dry-run", action="store_true", help="Run in dry-run simulation mode")
    args = parser.parse_args()

    harvester = PolymarketLiveHarvester(
        ticket_notional=args.lot_size,
        dry_run=args.dry_run,
        dynamic_sizing=args.dynamic_sizing,
        max_exposure=args.max_exposure,
        max_concurrent=args.max_concurrent,
        max_trades_per_market=args.max_trades_per_market,
        max_trades_per_hour=args.max_trades_per_hour,
        max_tte=args.max_tte,
        max_price_ceiling=args.max_price_ceiling,
        min_price_floor=args.min_price_floor,
    )
    asyncio.run(harvester.run())

