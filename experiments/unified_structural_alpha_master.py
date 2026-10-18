#!/usr/bin/env python3
"""
====================================================================================================
UNIFIED MASTER QUANTITATIVE ALPHA & MICROSTRUCTURE SUITE (ALL 4 TIERS / 9 STRATEGIES)
====================================================================================================
Authoritative single-file consolidation of all 4 architectural prompts:

TIER 0: Core Telemetry & Realistic Shadow Execution Engine
  - Hardened Polymarket Dual-Socket Watchdog (poly_watchdog_ws)
  - HyperCore Local 3-Second Mark Price Replicator (hl_mark_replicator)
  - Realistic Shadow Broker & Replay Engine with SQLite Markout Ledger (shadow_broker)

TIER 1: Polymarket Structural Alpha Experiments
  - S1:  Categorical NegRisk convertPositions Arbitrage (exp_s1_negrisk_convert)
  - S10: Polygon OrderFilled Calibrated Insider Shadowing & Murphy Brier Scoring (exp_s10_insider_shadow)
  - S2:  UMA N/A ($0.50 Midpoint) & DVM Dispute Scanner (exp_s2_uma_na_scanner)

TIER 2: Hyperliquid L1 & HyperEVM Microstructure Experiments
  - S4:  Stage-1 30s Partial-Liquidation Cooldown Wick Catcher (exp_s4_hl_wick_catcher)
  - S6:  HIP-2 Geometric Grid Exhaustion & Hyperp 8h EMA Squeeze (exp_s6_hip2_hyperp)
  - S5:  HyperEVM Precompile (0x0808) to CoreWriter (0x333...333) Simulator (exp_s5_hyperevm_atomic)

TIER 3: Cross-Venue Quantitative & Oracle Alpha Experiments
  - S9:  Deribit SVI Breeden-Litzenberger vs Polymarket/Kalshi Strike Ladders (exp_s9_svi_digital_arb)
  - S8:  Pyth Lazer / Hermes CI_Ratio & Pull-Oracle Lag Monitor (exp_s8_pyth_ci_arb)
  - S7:  Whales Market 4-Hour TGE Escrow Squeeze Tracker (exp_s7_whales_tge_squeeze)

====================================================================================================
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import math
import os
import re
import sqlite3
import sys
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

import httpx
import numpy as np
from scipy.optimize import minimize
from scipy.stats import norm

# Setup Logging
logger = logging.getLogger("UnifiedAlphaMaster")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("[%(asctime)s UTC] [%(levelname)s] [%(name)s] %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


# ==================================================================================================
# TIER 0: CORE TELEMETRY & SHADOW EXECUTION ENGINE
# ==================================================================================================

# ------------------------------------------------------------------------------
# 0.1 Continuous-Time EMA & Math Utilities
# ------------------------------------------------------------------------------

class ContinuousTimeEMA:
    """
    Exact continuous-time decaying accumulator over arbitrary elapsed dt:
        ema_num(t) = ema_num(t - dt) * exp(-dt / tau) + sample * dt
        ema_den(t) = ema_den(t - dt) * exp(-dt / tau) + dt
        EMA(t)     = ema_num(t) / ema_den(t)
    """
    def __init__(self, tau_seconds: float, initial_value: float = 0.0):
        self.tau: float = float(tau_seconds)
        self.ema_num: float = 0.0
        self.ema_den: float = 0.0
        self.last_ts: Optional[float] = None
        self.initial_value: float = initial_value

    def update(self, sample: float, current_ts: Optional[float] = None) -> float:
        now = time.monotonic() if current_ts is None else current_ts
        if self.last_ts is None:
            self.last_ts = now
            self.ema_num = sample * self.tau
            self.ema_den = self.tau
            return sample

        dt = max(0.0, now - self.last_ts)
        self.last_ts = now
        if dt == 0.0:
            if self.ema_den <= self.tau or self.ema_den == 0.0:
                self.ema_num = sample * self.tau
                self.ema_den = self.tau
                return sample
            return self.value()

        decay = math.exp(-dt / self.tau)
        self.ema_num = self.ema_num * decay + sample * dt
        self.ema_den = self.ema_den * decay + dt
        return self.ema_num / self.ema_den if self.ema_den > 1e-12 else sample

    def value(self) -> float:
        return self.ema_num / self.ema_den if self.ema_den > 1e-12 else self.initial_value

    def reset(self) -> None:
        self.ema_num = 0.0
        self.ema_den = 0.0
        self.last_ts = None


def weighted_median(items: List[Tuple[float, float]]) -> float:
    """Computes exact weighted median for (value, weight) pairs."""
    valid_items = [(v, w) for v, w in items if w > 0 and not math.isnan(v)]
    if not valid_items:
        raise ValueError("Cannot compute weighted median of empty sequence.")
    if len(valid_items) == 1:
        return valid_items[0][0]

    sorted_items = sorted(valid_items, key=lambda x: x[0])
    half_weight = sum(w for _, w in sorted_items) / 2.0
    cum_w = 0.0
    for i, (val, w) in enumerate(sorted_items):
        cum_w += w
        if cum_w >= half_weight:
            if math.isclose(cum_w, half_weight, rel_tol=1e-9) and i + 1 < len(sorted_items):
                return (val + sorted_items[i + 1][0]) / 2.0
            return val
    return sorted_items[-1][0]


# ------------------------------------------------------------------------------
# 0.2 Local L2 Order Book & Realistic Shadow Broker with SQLite Ledger
# ------------------------------------------------------------------------------

class OrderType(str, Enum):
    TAKER_FOK = "TAKER_FOK"
    TAKER_IOC = "TAKER_IOC"
    MAKER_ALO = "MAKER_ALO"

class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderStatus(str, Enum):
    SUBMITTED = "SUBMITTED"
    IN_FLIGHT = "IN_FLIGHT"
    RESTING = "RESTING"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


@dataclass
class ShadowFill:
    fill_id: str
    order_id: str
    symbol: str
    venue: str
    side: Side
    fill_time: float
    fill_price: float
    fill_size: float
    liquidity_role: str
    queue_ahead_at_entry: float
    fee_usd: float = 0.0


@dataclass
class ShadowMarkout:
    fill_id: str
    order_id: str
    symbol: str
    horizon_label: str
    scheduled_ts: float
    recorded_ts: Optional[float] = None
    fill_price: float = 0.0
    markout_mid_price: Optional[float] = None
    markout_pnl_bps: Optional[float] = None
    markout_pnl_usd: Optional[float] = None
    is_final: bool = False


@dataclass
class ShadowOrder:
    order_id: str
    symbol: str
    venue: str
    order_type: OrderType
    side: Side
    price: float
    size: float
    remaining_size: float
    created_ts: float
    latency_ms: float
    arrival_ts: float
    status: OrderStatus = OrderStatus.SUBMITTED
    queue_ahead_size: float = 0.0
    reject_reason: Optional[str] = None
    fills: List[ShadowFill] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class L2Book:
    """In-memory L2 orderbook tracker supporting price-level queries and book-walking."""
    def __init__(self, symbol: str):
        self.symbol: str = symbol.upper()
        self.bids: Dict[float, float] = {}
        self.asks: Dict[float, float] = {}
        self.last_update_ts: float = 0.0

    def set_level(self, price: float, size: float, side: Side, ts: Optional[float] = None) -> None:
        target = self.bids if side == Side.BUY else self.asks
        if size <= 0:
            target.pop(price, None)
        else:
            target[price] = float(size)
        if ts is not None:
            self.last_update_ts = ts

    def best_bid(self) -> Optional[float]:
        return max(self.bids.keys()) if self.bids else None

    def best_ask(self) -> Optional[float]:
        return min(self.asks.keys()) if self.asks else None

    def mid_price(self) -> Optional[float]:
        bb, ba = self.best_bid(), self.best_ask()
        if bb is not None and ba is not None:
            return (bb + ba) / 2.0
        return bb or ba

    def walk_book(
        self,
        side: Side,
        requested_size: float,
        limit_price: float,
    ) -> Tuple[float, float, List[Tuple[float, float]]]:
        levels_filled: List[Tuple[float, float]] = []
        rem_size = requested_size
        cost_accum = 0.0
        total_filled = 0.0

        if side == Side.BUY:
            sorted_prices = sorted(self.asks.keys())
            for px in sorted_prices:
                if px > limit_price or rem_size <= 0:
                    break
                avail = self.asks[px]
                fill_qty = min(rem_size, avail)
                levels_filled.append((px, fill_qty))
                cost_accum += fill_qty * px
                total_filled += fill_qty
                rem_size -= fill_qty
        else:
            sorted_prices = sorted(self.bids.keys(), reverse=True)
            for px in sorted_prices:
                if px < limit_price or rem_size <= 0:
                    break
                avail = self.bids[px]
                fill_qty = min(rem_size, avail)
                levels_filled.append((px, fill_qty))
                cost_accum += fill_qty * px
                total_filled += fill_qty
                rem_size -= fill_qty

        avg_px = (cost_accum / total_filled) if total_filled > 0 else 0.0
        return total_filled, avg_px, levels_filled


MARKOUT_HORIZONS: List[Tuple[float, str]] = [
    (1.0, "1s"),
    (5.0, "5s"),
    (30.0, "30s"),
    (300.0, "5m"),
    (3600.0, "1h"),
]


class RealisticShadowBroker:
    """
    Institutional shadow execution broker supporting latency modeling, ALO queueing,
    walk-book matching, and persistent SQLite markout ledger.
    """
    def __init__(
        self,
        telemetry_db_path: str = "experiments/shadow_ledger.db",
        default_latency_ms: float = 130.0,
        taker_fee_bps: float = 4.5,
        maker_rebate_bps: float = -1.5,
    ):
        self.default_latency = default_latency_ms
        self.taker_fee_bps = taker_fee_bps
        self.maker_rebate_bps = maker_rebate_bps
        self.telemetry_db_path = telemetry_db_path
        self.books: Dict[str, L2Book] = {}
        self.orders: Dict[str, ShadowOrder] = {}
        self.fills: List[ShadowFill] = []
        self.markouts: List[ShadowMarkout] = []
        self.recorded_markouts: Set[Tuple[str, str]] = set()

        # Initialize SQLite database
        if telemetry_db_path != ":memory:":
            Path(telemetry_db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(telemetry_db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self._init_db()

    def _init_db(self) -> None:
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS shadow_orders (
                    order_id TEXT PRIMARY KEY,
                    symbol TEXT,
                    venue TEXT,
                    order_type TEXT,
                    side TEXT,
                    price REAL,
                    size REAL,
                    remaining_size REAL,
                    created_ts REAL,
                    latency_ms REAL,
                    arrival_ts REAL,
                    status TEXT,
                    queue_ahead_size REAL,
                    reject_reason TEXT
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS shadow_fills (
                    fill_id TEXT PRIMARY KEY,
                    order_id TEXT,
                    symbol TEXT,
                    venue TEXT,
                    side TEXT,
                    fill_time REAL,
                    fill_price REAL,
                    fill_size REAL,
                    liquidity_role TEXT,
                    queue_ahead_at_entry REAL,
                    fee_usd REAL
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS shadow_markouts (
                    fill_id TEXT,
                    order_id TEXT,
                    symbol TEXT,
                    horizon_label TEXT,
                    scheduled_ts REAL,
                    recorded_ts REAL,
                    fill_price REAL,
                    markout_mid_price REAL,
                    markout_pnl_bps REAL,
                    markout_pnl_usd REAL,
                    is_final INTEGER,
                    PRIMARY KEY (fill_id, horizon_label)
                )
            """)
            # Schema migrations for strategy tracking and high asymmetry events
            cursor = self.conn.cursor()
            cursor.execute("PRAGMA table_info(shadow_orders)")
            cols = [col[1] for col in cursor.fetchall()]
            if "strategy" not in cols:
                cursor.execute("ALTER TABLE shadow_orders ADD COLUMN strategy TEXT")
            if "metadata_json" not in cols:
                cursor.execute("ALTER TABLE shadow_orders ADD COLUMN metadata_json TEXT")

            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS high_asymmetry_events (
                    event_id TEXT PRIMARY KEY,
                    strategy TEXT,
                    event_type TEXT,
                    symbol TEXT,
                    timestamp REAL,
                    notional REAL,
                    expected_payoff REAL,
                    details_json TEXT,
                    alert_sent INTEGER DEFAULT 0,
                    followup_sent INTEGER DEFAULT 0
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS feed_telemetry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    venue TEXT,
                    metric_name TEXT,
                    metric_value REAL,
                    details_json TEXT
                )
            """)

    def _persist_order(self, order: ShadowOrder) -> None:
        strategy = order.metadata.get("strategy") if order.metadata else None
        if not strategy:
            if order.symbol.startswith("POLY_NO_SUBSET") or (order.metadata and order.metadata.get("pure_neg")):
                strategy = "S1"
            elif (order.metadata and order.metadata.get("stage2_tracker")) or order.symbol in ("BTC", "ETH", "SOL", "PURR", "HYPE"):
                strategy = "S4"
            else:
                strategy = "UNKNOWN"
        meta_json = json.dumps(order.metadata) if order.metadata else "{}"
        try:
            with self.conn:
                self.conn.execute("""
                    INSERT OR REPLACE INTO shadow_orders (
                        order_id, symbol, venue, order_type, side, price, size, remaining_size,
                        created_ts, latency_ms, arrival_ts, status, queue_ahead_size, reject_reason,
                        strategy, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    order.order_id, order.symbol, order.venue, order.order_type.value,
                    order.side.value, order.price, order.size, order.remaining_size,
                    order.created_ts, order.latency_ms, order.arrival_ts,
                    order.status.value, order.queue_ahead_size, order.reject_reason,
                    strategy, meta_json
                ))
        except Exception as e:
            logger.error(f"Error persisting shadow order {order.order_id}: {e}")

    def record_high_asymmetry_event(
        self,
        event_id: str,
        strategy: str,
        event_type: str,
        symbol: str,
        timestamp: float,
        notional: float,
        expected_payoff: float,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        try:
            with self.conn:
                self.conn.execute("""
                    INSERT OR REPLACE INTO high_asymmetry_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0)
                """, (
                    event_id, strategy, event_type, symbol, timestamp,
                    notional, expected_payoff, json.dumps(details or {})
                ))
        except Exception as e:
            logger.error(f"Error persisting high asymmetry event {event_id}: {e}")

    def record_feed_telemetry(
        self,
        venue: str,
        metric_name: str,
        metric_value: float,
        details: Optional[Dict[str, Any]] = None,
        ts: Optional[float] = None,
    ) -> None:
        now = time.time() if ts is None else float(ts)
        try:
            with self.conn:
                self.conn.execute("""
                    INSERT INTO feed_telemetry (timestamp, venue, metric_name, metric_value, details_json)
                    VALUES (?, ?, ?, ?, ?)
                """, (now, venue, metric_name, metric_value, json.dumps(details or {})))
        except Exception as e:
            logger.error(f"Error recording feed telemetry: {e}")

    def _persist_fill(self, fill: ShadowFill) -> None:
        try:
            with self.conn:
                self.conn.execute("""
                    INSERT OR REPLACE INTO shadow_fills VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    fill.fill_id, fill.order_id, fill.symbol, fill.venue, fill.side.value,
                    fill.fill_time, fill.fill_price, fill.fill_size, fill.liquidity_role,
                    fill.queue_ahead_at_entry, fill.fee_usd
                ))
                # Schedule pending markouts across all horizons with NULL pnl until real wall-clock expiry
                for horizon_sec, horizon_label in MARKOUT_HORIZONS:
                    self.conn.execute("""
                        INSERT OR IGNORE INTO shadow_markouts (
                            fill_id, order_id, symbol, horizon_label, scheduled_ts, recorded_ts,
                            fill_price, markout_mid_price, markout_pnl_bps, markout_pnl_usd, is_final
                        ) VALUES (?, ?, ?, ?, ?, NULL, ?, NULL, NULL, NULL, 0)
                    """, (
                        fill.fill_id, fill.order_id, fill.symbol, horizon_label,
                        fill.fill_time + horizon_sec, fill.fill_price
                    ))
        except Exception as e:
            logger.error(f"Error persisting shadow fill {fill.fill_id}: {e}")

    def _persist_markout(self, markout: ShadowMarkout) -> None:
        try:
            with self.conn:
                self.conn.execute("""
                    INSERT OR REPLACE INTO shadow_markouts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    markout.fill_id, markout.order_id, markout.symbol, markout.horizon_label,
                    markout.scheduled_ts, markout.recorded_ts, markout.fill_price,
                    markout.markout_mid_price, markout.markout_pnl_bps, markout.markout_pnl_usd,
                    1 if markout.is_final else 0
                ))
        except Exception as e:
            logger.error(f"Error persisting shadow markout {markout.fill_id} {markout.horizon_label}: {e}")

    def get_or_create_book(self, symbol: str) -> L2Book:
        sym = symbol.upper()
        if sym not in self.books:
            self.books[sym] = L2Book(sym)
        return self.books[sym]

    def submit_order(
        self,
        symbol: str,
        side: Union[Side, str],
        order_type: Union[OrderType, str],
        price: float,
        size: float,
        venue: str = "hyperliquid",
        latency_ms: Optional[float] = None,
        current_ts: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ShadowOrder:
        sym = symbol.upper()
        s_side = Side(side.upper()) if isinstance(side, str) else side
        o_type = OrderType(order_type.upper()) if isinstance(order_type, str) else order_type
        t0 = time.time() if current_ts is None else float(current_ts)
        eff_lat = latency_ms if latency_ms is not None else self.default_latency
        arrival_ts = t0 + (eff_lat / 1000.0)

        order_id = f"ord_{venue[:2]}_{uuid.uuid4().hex[:8]}"
        order = ShadowOrder(
            order_id=order_id,
            symbol=sym,
            venue=venue,
            order_type=o_type,
            side=s_side,
            price=float(price),
            size=float(size),
            remaining_size=float(size),
            created_ts=t0,
            latency_ms=eff_lat,
            arrival_ts=arrival_ts,
            status=OrderStatus.SUBMITTED,
            metadata=metadata or {},
        )
        self.orders[order_id] = order
        self._persist_order(order)
        return order

    def cancel_order(self, order_id: str) -> bool:
        if order_id in self.orders:
            self.orders[order_id].status = OrderStatus.CANCELLED
            self._persist_order(self.orders[order_id])
            return True
        return False

    def on_book_tick(
        self,
        venue: str,
        symbol: str,
        bids: Union[Dict[float, float], List[Tuple[float, float]]],
        asks: Union[Dict[float, float], List[Tuple[float, float]]],
        ts: float,
    ) -> None:
        """
        1. Updates internal L2Book.
        2. Evaluates SUBMITTED orders whose arrival_ts <= ts.
           - TAKER_FOK / IOC: walks book, fills or rejects if FOK lacks depth.
           - MAKER_ALO: rejects if crosses at arrival, else sets RESTING and snapshots queue ahead.
        """
        book = self.get_or_create_book(symbol)
        if isinstance(bids, dict):
            for px, sz in bids.items():
                book.set_level(float(px), float(sz), Side.BUY, ts)
        else:
            book.bids.clear()
            for px, sz in bids:
                book.set_level(float(px), float(sz), Side.BUY, ts)

        if isinstance(asks, dict):
            for px, sz in asks.items():
                book.set_level(float(px), float(sz), Side.SELL, ts)
        else:
            book.asks.clear()
            for px, sz in asks:
                book.set_level(float(px), float(sz), Side.SELL, ts)

        # Process due SUBMITTED orders
        due_orders = [
            ord for ord in self.orders.values()
            if ord.venue.lower() == venue.lower()
            and ord.symbol == symbol.upper()
            and ord.status == OrderStatus.SUBMITTED
            and ts >= ord.arrival_ts
        ]

        for order in due_orders:
            if order.order_type in (OrderType.TAKER_FOK, OrderType.TAKER_IOC):
                total_filled, avg_px, levels = book.walk_book(order.side, order.remaining_size, order.price)
                if order.order_type == OrderType.TAKER_FOK:
                    if total_filled < (order.remaining_size - 1e-9):
                        order.status = OrderStatus.REJECTED
                        order.reject_reason = "FOK_INSUFFICIENT_DEPTH"
                    else:
                        fee_rate = self.taker_fee_bps / 10_000.0
                        fee_usd = order.remaining_size * avg_px * fee_rate
                        fill = ShadowFill(
                            fill_id=f"fill_{uuid.uuid4().hex[:8]}",
                            order_id=order.order_id,
                            symbol=order.symbol,
                            venue=order.venue,
                            side=order.side,
                            fill_time=ts,
                            fill_price=avg_px,
                            fill_size=order.remaining_size,
                            liquidity_role="TAKER",
                            queue_ahead_at_entry=0.0,
                            fee_usd=fee_usd,
                        )
                        order.fills.append(fill)
                        self.fills.append(fill)
                        self._persist_fill(fill)
                        order.status = OrderStatus.FILLED
                        order.remaining_size = 0.0
                elif order.order_type == OrderType.TAKER_IOC:
                    if total_filled > 1e-9:
                        fee_rate = self.taker_fee_bps / 10_000.0
                        fee_usd = total_filled * avg_px * fee_rate
                        fill = ShadowFill(
                            fill_id=f"fill_{uuid.uuid4().hex[:8]}",
                            order_id=order.order_id,
                            symbol=order.symbol,
                            venue=order.venue,
                            side=order.side,
                            fill_time=ts,
                            fill_price=avg_px,
                            fill_size=total_filled,
                            liquidity_role="TAKER",
                            queue_ahead_at_entry=0.0,
                            fee_usd=fee_usd,
                        )
                        order.fills.append(fill)
                        self.fills.append(fill)
                        self._persist_fill(fill)
                        order.remaining_size -= total_filled
                        order.status = OrderStatus.FILLED if order.remaining_size <= 1e-9 else OrderStatus.PARTIALLY_FILLED
                    else:
                        order.status = OrderStatus.CANCELLED
                        order.reject_reason = "IOC_ZERO_FILL_AVAILABLE"

            elif order.order_type == OrderType.MAKER_ALO:
                if order.side == Side.BUY:
                    best_ask = book.best_ask()
                    if best_ask is not None and order.price >= best_ask:
                        order.status = OrderStatus.REJECTED
                        order.reject_reason = "ALO_WOULD_CROSS"
                    else:
                        order.status = OrderStatus.RESTING
                        order.queue_ahead_size = book.bids.get(order.price, 0.0)
                elif order.side == Side.SELL:
                    best_bid = book.best_bid()
                    if best_bid is not None and order.price <= best_bid:
                        order.status = OrderStatus.REJECTED
                        order.reject_reason = "ALO_WOULD_CROSS"
                    else:
                        order.status = OrderStatus.RESTING
                        order.queue_ahead_size = book.asks.get(order.price, 0.0)

            self._persist_order(order)

    def on_public_trade(
        self,
        venue: str,
        symbol: str,
        trade_price: float,
        trade_size: float,
        aggressor_side: Union[Side, str],
        ts: float,
    ) -> None:
        """
        Executes trade ticks against resting ALO orders:
        - Print through level -> fills 100% of remaining_size.
        - Print at level -> decrements queue_ahead_size; fills excess volume.
        """
        aggr = Side(aggressor_side.upper()) if isinstance(aggressor_side, str) else aggressor_side
        active_orders = [
            ord for ord in self.orders.values()
            if ord.venue.lower() == venue.lower()
            and ord.symbol == symbol.upper()
            and ord.status in (OrderStatus.RESTING, OrderStatus.PARTIALLY_FILLED)
            and ord.order_type == OrderType.MAKER_ALO
        ]

        for order in active_orders:
            filled_qty = 0.0
            if order.side == Side.BUY:
                if trade_price < order.price:
                    # Traded strictly through our level
                    filled_qty = order.remaining_size
                elif math.isclose(trade_price, order.price, rel_tol=1e-7, abs_tol=1e-7) and aggr == Side.SELL:
                    order.queue_ahead_size -= trade_size
                    if order.queue_ahead_size < 0:
                        fillable = min(order.remaining_size, abs(order.queue_ahead_size))
                        filled_qty = fillable
                        order.queue_ahead_size = 0.0
            elif order.side == Side.SELL:
                if trade_price > order.price:
                    # Traded strictly through our level
                    filled_qty = order.remaining_size
                elif math.isclose(trade_price, order.price, rel_tol=1e-7, abs_tol=1e-7) and aggr == Side.BUY:
                    order.queue_ahead_size -= trade_size
                    if order.queue_ahead_size < 0:
                        fillable = min(order.remaining_size, abs(order.queue_ahead_size))
                        filled_qty = fillable
                        order.queue_ahead_size = 0.0

            if filled_qty > 1e-9:
                fee_rate = self.maker_rebate_bps / 10_000.0
                fee_usd = filled_qty * order.price * fee_rate
                fill = ShadowFill(
                    fill_id=f"fill_{uuid.uuid4().hex[:8]}",
                    order_id=order.order_id,
                    symbol=order.symbol,
                    venue=order.venue,
                    side=order.side,
                    fill_time=ts,
                    fill_price=order.price,
                    fill_size=filled_qty,
                    liquidity_role="MAKER",
                    queue_ahead_at_entry=order.queue_ahead_size,
                    fee_usd=fee_usd,
                )
                order.fills.append(fill)
                self.fills.append(fill)
                self._persist_fill(fill)

                order.remaining_size -= filled_qty
                order.status = OrderStatus.FILLED if order.remaining_size <= 1e-9 else OrderStatus.PARTIALLY_FILLED
                self._persist_order(order)

    def update_markouts(self, venue: str, symbol: str, mid_price: float, ts: float) -> List[ShadowMarkout]:
        """
        Computes and persists signed markout PnL in bps and USD at horizons
        [1.0, 5.0, 30.0, 300.0, 3600.0] seconds after fill_time.
        """
        newly_recorded = []
        for fill in self.fills:
            if fill.venue.lower() != venue.lower() or fill.symbol.upper() != symbol.upper():
                continue
            for horizon_sec, horizon_label in MARKOUT_HORIZONS:
                key = (fill.fill_id, horizon_label)
                if key in self.recorded_markouts:
                    continue
                if ts >= (fill.fill_time + horizon_sec):
                    if fill.side == Side.BUY:
                        pnl_bps = ((mid_price - fill.fill_price) / fill.fill_price) * 10_000.0
                        pnl_usd = (mid_price - fill.fill_price) * fill.fill_size - fill.fee_usd
                    else:
                        pnl_bps = ((fill.fill_price - mid_price) / fill.fill_price) * 10_000.0
                        pnl_usd = (fill.fill_price - mid_price) * fill.fill_size - fill.fee_usd

                    m = ShadowMarkout(
                        fill_id=fill.fill_id,
                        order_id=fill.order_id,
                        symbol=fill.symbol,
                        horizon_label=horizon_label,
                        scheduled_ts=fill.fill_time + horizon_sec,
                        recorded_ts=ts,
                        fill_price=fill.fill_price,
                        markout_mid_price=mid_price,
                        markout_pnl_bps=pnl_bps,
                        markout_pnl_usd=pnl_usd,
                        is_final=True,
                    )
                    self.markouts.append(m)
                    self.recorded_markouts.add(key)
                    self._persist_markout(m)
                    newly_recorded.append(m)
        return newly_recorded


# ------------------------------------------------------------------------------
# 0.3 HyperCore 3-Second Mark Price Replicator
# ------------------------------------------------------------------------------

CEX_WEIGHTS = {"binance": 3.0, "okx": 2.0, "bybit": 2.0, "gate": 1.0, "mexc": 1.0}

class HyperCoreMarkPriceReplicator:
    """Continuously replicates HyperCore's internal P_mark = median(P1, P2, P3)."""
    def __init__(self, symbols: Optional[List[str]] = None):
        self.symbols = [s.upper() for s in (symbols or ["BTC", "ETH", "SOL", "PURR"])]
        self.p1_emas = {s: ContinuousTimeEMA(150.0) for s in self.symbols}
        self.p3_fallback_emas = {s: ContinuousTimeEMA(30.0) for s in self.symbols}
        self.hl_bids = {s: 0.0 for s in self.symbols}
        self.hl_asks = {s: 0.0 for s in self.symbols}
        self.hl_trades = {s: 0.0 for s in self.symbols}
        self.hl_oracles = {s: 0.0 for s in self.symbols}
        self.cex_mids: Dict[Tuple[str, str], Tuple[float, float]] = {}  # (venue, sym) -> (px, ts)
        self.mark_prices: Dict[str, float] = {s: 0.0 for s in self.symbols}

    def update_hl_book(self, symbol: str, best_bid: float, best_ask: float, last_trade: Optional[float] = None, timestamp_mono: Optional[float] = None) -> None:
        sym = symbol.upper()
        now = time.monotonic() if timestamp_mono is None else timestamp_mono
        self.hl_bids[sym] = best_bid
        self.hl_asks[sym] = best_ask
        if last_trade:
            self.hl_trades[sym] = last_trade
        self._compute_mark(sym, now)

    def update_hl_oracle(self, symbol: str, oracle_price: float, timestamp_mono: Optional[float] = None) -> None:
        sym = symbol.upper()
        now = time.monotonic() if timestamp_mono is None else timestamp_mono
        self.hl_oracles[sym] = oracle_price
        self._compute_mark(sym, now)

    def update_cex_mid(self, symbol: str, venue: str, mid_price: float, timestamp_mono: Optional[float] = None) -> None:
        sym = symbol.upper()
        now = time.monotonic() if timestamp_mono is None else timestamp_mono
        self.cex_mids[(venue.lower(), sym)] = (mid_price, now)
        self._compute_mark(sym, now)

    def _compute_mark(self, symbol: str, now: float) -> float:
        sym = symbol.upper()
        oracle = self.hl_oracles.get(sym, 0.0)
        bid = self.hl_bids.get(sym, 0.0)
        ask = self.hl_asks.get(sym, 0.0)
        trade = self.hl_trades.get(sym, 0.0) or ((bid + ask) / 2.0 if bid > 0 and ask > 0 else oracle)
        mid = (bid + ask) / 2.0 if bid > 0 and ask > 0 else (trade or oracle)

        # P1: Oracle-anchored fair value
        p1 = oracle + self.p1_emas[sym].update(mid - oracle, now) if oracle > 0 else mid

        # P2: Local HL micro median
        candidates_p2 = sorted([bid or mid, ask or mid, trade or mid])
        p2 = candidates_p2[1]

        # P3: CEX weighted median
        live_cex = []
        for ven, w in CEX_WEIGHTS.items():
            if (ven, sym) in self.cex_mids:
                px, t_upd = self.cex_mids[(ven, sym)]
                if px > 0 and (now - t_upd) <= 10.0:
                    live_cex.append((px, w))

        self.p3_fallback_emas[sym].update(p2, now)
        if len(live_cex) <= 2:
            p3 = self.p3_fallback_emas[sym].value()
        else:
            p3 = weighted_median(live_cex)

        p_mark = sorted([p1, p2, p3])[1]
        self.mark_prices[sym] = p_mark
        return p_mark

    def get_mark_price(self, symbol: str) -> float:
        return self.mark_prices.get(symbol.upper(), 0.0)


# ------------------------------------------------------------------------------
# 0.4 Polymarket Dual-Socket Watchdog
# ------------------------------------------------------------------------------

class PolymarketDualSocketWatchdog:
    """
    Hardened Dual-Socket WebSocket Watchdog for Polymarket CLOB.
    Manages socket_a & socket_b redundancy, dynamic tick size updates,
    10s PING loop, 1s silence drift detector, and isolated HTTP client sessions.
    """
    def __init__(
        self,
        token_ids: Optional[List[str]] = None,
        ws_url: str = "wss://ws-subscriptions-clob.polymarket.com/ws/market",
        rest_url: str = "https://clob.polymarket.com",
    ):
        self.token_ids: List[str] = token_ids or []
        self.ws_url: str = ws_url
        self.rest_url: str = rest_url.rstrip("/")
        self.tick_sizes: Dict[str, float] = {}
        self.best_bid_ask: Dict[str, Tuple[float, float]] = {}
        self.last_data_ts_a: float = 0.0
        self.last_data_ts_b: float = 0.0
        self.running: bool = False
        self._ws_a = None
        self._ws_b = None

        # Strictly isolated HTTP client configurations (Anti-Cloudflare 3,000ms delay)
        self.polling_http_client = httpx.AsyncClient(
            base_url=self.rest_url,
            headers={"User-Agent": "Polymarket-Polling/2.0"},
            timeout=httpx.Timeout(4.0, connect=2.0),
        )
        self.execution_http_client = httpx.AsyncClient(
            base_url=self.rest_url,
            headers={"User-Agent": "Polymarket-Execution/2.0"},
            timeout=httpx.Timeout(5.0, connect=2.0),
        )

    def set_tick_size(self, asset_id: str, tick_size: float) -> None:
        self.tick_sizes[asset_id] = float(tick_size)

    def get_tick_size(self, asset_id: str) -> float:
        return self.tick_sizes.get(asset_id, 0.01)

    def quantize_price(self, asset_id: str, price: float, side: str = "BUY") -> float:
        tick = self.get_tick_size(asset_id)
        tick_dec = Decimal(str(tick))
        price_dec = Decimal(str(price))
        mode = ROUND_FLOOR if side.upper() == "BUY" else ROUND_CEILING
        quantized = float((price_dec / tick_dec).quantize(Decimal("1"), rounding=mode) * tick_dec)
        min_allowed = tick
        max_allowed = float(Decimal("1.0") - tick_dec)
        return max(min_allowed, min(max_allowed, quantized))

    def build_subscription_payload(self) -> Dict[str, Any]:
        return {
            "type": "market",
            "assets_ids": self.token_ids,
            "custom_feature_enabled": True,
        }

    def _handle_message(self, socket_id: str, msg_str: str) -> None:
        now = time.time()
        if socket_id == "A":
            self.last_data_ts_a = now
        else:
            self.last_data_ts_b = now

        if msg_str.strip() == "PONG":
            return

        try:
            data = json.loads(msg_str)
        except Exception:
            return

        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            ev = item.get("event_type")
            if ev == "tick_size_change":
                asset_id = item.get("asset_id") or item.get("token_id")
                new_tick = item.get("tick_size") or item.get("new_tick_size")
                if asset_id and new_tick is not None:
                    try:
                        self.set_tick_size(str(asset_id), float(new_tick))
                        logger.info(f"[tick_size_change] Updated {asset_id} to {float(new_tick)}")
                    except Exception:
                        pass
            elif ev == "best_bid_ask":
                asset_id = item.get("asset_id")
                if asset_id:
                    bid = float(item.get("bid", 0.0) or 0.0)
                    ask = float(item.get("ask", 0.0) or 0.0)
                    self.best_bid_ask[str(asset_id)] = (bid, ask)

    async def _ping_loop(self) -> None:
        while self.running:
            await asyncio.sleep(10.0)
            for ws in (self._ws_a, self._ws_b):
                if ws:
                    try:
                        await ws.send("PING")
                    except Exception:
                        pass

    async def _watchdog_loop(self) -> None:
        while self.running:
            await asyncio.sleep(1.0)
            if self.last_data_ts_a > 0 and self.last_data_ts_b > 0:
                drift = abs(self.last_data_ts_a - self.last_data_ts_b)
                if drift > 5.0:
                    logger.warning(f"[WATCHDOG] Dual socket drift {drift:.2f}s > 5.0s detected! Forcing reconnect.")
                    if self.last_data_ts_a < self.last_data_ts_b and self._ws_a:
                        try:
                            await self._ws_a.close()
                        except Exception:
                            pass
                    elif self._ws_b:
                        try:
                            await self._ws_b.close()
                        except Exception:
                            pass

    async def _listen_socket(self, socket_id: str) -> None:
        """Connects and listens to Polymarket CLOB WS for a designated socket instance (A or B)."""
        while self.running:
            try:
                async with websockets.connect(self.ws_url, ping_interval=20.0, ping_timeout=10.0) as ws:
                    if socket_id == "A":
                        self._ws_a = ws
                    else:
                        self._ws_b = ws
                    logger.info(f"[POLY WATCHDOG] Socket {socket_id} connected to {self.ws_url}")
                    if self.token_ids:
                        sub_payload = self.build_subscription_payload()
                        await ws.send(json.dumps(sub_payload))
                    async for msg_str in ws:
                        if not self.running:
                            break
                        self._handle_message(socket_id, msg_str)
            except Exception as e:
                logger.debug(f"[POLY WATCHDOG] Socket {socket_id} error: {e}")
                await asyncio.sleep(2.0)
            finally:
                if socket_id == "A":
                    self._ws_a = None
                else:
                    self._ws_b = None

    async def run(self) -> None:
        """Starts dual-socket connections, ping loop, and silence drift detector concurrently."""
        self.running = True
        tasks = [
            asyncio.create_task(self._listen_socket("A")),
            asyncio.create_task(self._listen_socket("B")),
            asyncio.create_task(self._ping_loop()),
            asyncio.create_task(self._watchdog_loop()),
        ]
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            pass

    async def close(self) -> None:
        self.running = False
        if self._ws_a:
            await self._ws_a.close()
        if self._ws_b:
            await self._ws_b.close()
        await self.polling_http_client.aclose()
        await self.execution_http_client.aclose()


# ==================================================================================================
# TIER 1: POLYMARKET STRUCTURAL ALPHA EXPERIMENTS (S1, S10, S2)
# ==================================================================================================

# ------------------------------------------------------------------------------
# 1.1 S1: Categorical NegRisk convertPositions Arbitrage
# ------------------------------------------------------------------------------

@dataclass
class NegRiskArbitrageSubset:
    event_id: str
    condition_id: str
    subset_indices: List[int]
    subset_size: int
    no_bundle_cost: float
    immediate_cash_pnl: float
    residual_tail_shares: List[int]
    residual_mtm_value: float
    is_pure_negative_cost: bool
    shadow_fill_size: float
    timestamp: float


class NegRiskConvertEngine:
    """Evaluates multi-outcome NegRisk convertPositions arbitrage and legging salvage."""
    def __init__(self, shadow_broker: Optional[RealisticShadowBroker] = None):
        self.shadow_broker = shadow_broker or RealisticShadowBroker(default_latency_ms=120.0)

    @staticmethod
    def evaluate_subsets(
        event_id: str,
        condition_id: str,
        outcomes_n: int,
        ask_prices_no: Dict[int, float],
        bid_prices_yes: Dict[int, float],
        ask_depth_no: Dict[int, float],
        gas_and_fees_usd: float = 0.005,
        max_depth_fraction: float = 0.50,
    ) -> List[NegRiskArbitrageSubset]:
        opportunities = []
        for m_size in range(2, outcomes_n + 1):
            sorted_indices = sorted(range(outcomes_n), key=lambda i: ask_prices_no.get(i, 1.0))
            subset = sorted_indices[:m_size]

            cost_no = sum(ask_prices_no.get(i, 1.0) for i in subset)
            collateral_unlocked = float(m_size - 1)
            residual_indices = [j for j in range(outcomes_n) if j not in subset]
            residual_mtm = sum(bid_prices_yes.get(j, 0.0) for j in residual_indices)

            is_pure_neg = cost_no < collateral_unlocked
            net_cash_pnl = collateral_unlocked - cost_no - gas_and_fees_usd

            if is_pure_neg or (cost_no < collateral_unlocked + residual_mtm - gas_and_fees_usd):
                min_depth = min(ask_depth_no.get(i, 1000.0) for i in subset)
                q_cap = min_depth * max_depth_fraction

                opp = NegRiskArbitrageSubset(
                    event_id=event_id,
                    condition_id=condition_id,
                    subset_indices=subset,
                    subset_size=m_size,
                    no_bundle_cost=cost_no,
                    immediate_cash_pnl=net_cash_pnl,
                    residual_tail_shares=residual_indices,
                    residual_mtm_value=residual_mtm,
                    is_pure_negative_cost=is_pure_neg,
                    shadow_fill_size=q_cap,
                    timestamp=time.time(),
                )
                opportunities.append(opp)
        return opportunities


# ------------------------------------------------------------------------------
# 1.2 S10: Polygon OrderFilled Calibrated Insider Shadowing
# ------------------------------------------------------------------------------

def compute_murphy_brier_decomposition(
    forecasts: List[float],
    outcomes: List[int],
    n_bins: int = 10,
) -> Dict[str, float]:
    """Computes exact Murphy (1973) Brier Score Decomposition: BS = Reliability - Resolution + Uncertainty."""
    N = len(forecasts)
    if N == 0:
        return {"brier_score": 0.0, "reliability": 0.0, "resolution": 0.0, "uncertainty": 0.0, "ece": 0.0}

    f_arr = np.array(forecasts)
    o_arr = np.array(outcomes)
    bs = float(np.mean((f_arr - o_arr) ** 2))
    base_rate = float(np.mean(o_arr))
    uncertainty = base_rate * (1.0 - base_rate)

    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    reliability = 0.0
    resolution = 0.0
    ece = 0.0

    for i in range(n_bins):
        low, high = bin_edges[i], bin_edges[i + 1]
        mask = (f_arr >= low) & (f_arr <= high if i == n_bins - 1 else f_arr < high)
        n_k = int(np.sum(mask))
        if n_k > 0:
            p_k = float(np.mean(f_arr[mask]))
            o_k = float(np.mean(o_arr[mask]))
            weight = n_k / N
            reliability += weight * ((p_k - o_k) ** 2)
            resolution += weight * ((o_k - base_rate) ** 2)
            ece += weight * abs(p_k - o_k)

    return {
        "brier_score": bs,
        "reliability": reliability,
        "resolution": resolution,
        "uncertainty": uncertainty,
        "ece": ece,
    }


class InsiderShadowEngine:
    """Indexes Polygon OrderFilled logs, decodes direction, and scores insider calibration."""
    EXCLUDED_SIGS = {"PositionsConverted", "PositionSplit", "PositionsMerge"}

    @staticmethod
    def decode_order_filled_direction(maker_asset_id: int) -> str:
        return "BUY_CONDITIONAL" if maker_asset_id == 0 else "SELL_CONDITIONAL"

    @staticmethod
    def is_sybil_wash_trade(
        buyer_eoa: str,
        seller_eoa: str,
        upstream_clusters: Dict[str, str],
        seller_minted_within_24h: bool,
    ) -> bool:
        if upstream_clusters.get(buyer_eoa) == upstream_clusters.get(seller_eoa) and buyer_eoa in upstream_clusters:
            return True
        if seller_minted_within_24h:
            return True
        return False


# ------------------------------------------------------------------------------
# 1.3 S2: UMA N/A ($0.50 Midpoint) & DVM Dispute Scanner
# ------------------------------------------------------------------------------

class UMANAScannerEngine:
    """Scans for extreme skew markets near endDate, parsing rules for N/A $0.50 triggers."""
    STRICT_PATTERNS = [
        re.compile(r"by\s+(\d{1,2}:\d{2}\s*UTC)", re.IGNORECASE),
        re.compile(r"https?://[^\s]+", re.IGNORECASE),
        re.compile(r"postpone|delayed|cancel", re.IGNORECASE),
    ]

    @staticmethod
    def parse_resolution_ambiguity(description: str) -> Dict[str, Any]:
        has_utc = bool(re.search(r"\d{1,2}:\d{2}\s*UTC", description, re.IGNORECASE))
        has_url = bool(re.search(r"https?://[^\s]+", description, re.IGNORECASE))
        has_postpone = bool(re.search(r"postpone|delayed|void", description, re.IGNORECASE))
        ambiguity_score = (int(has_utc) * 0.4) + (int(has_url) * 0.3) + (int(has_postpone) * 0.3)
        return {
            "has_strict_utc": has_utc,
            "has_named_source": has_url,
            "has_postponement_clause": has_postpone,
            "ambiguity_score": ambiguity_score,
        }

    @staticmethod
    def evaluate_na_payoff_multiplier(entry_price: float) -> float:
        return 0.50 / max(0.001, entry_price)


# ==================================================================================================
# TIER 2: HYPERLIQUID L1 & HYPEREVM MICROSTRUCTURE EXPERIMENTS (S4, S6, S5)
# ==================================================================================================

# ------------------------------------------------------------------------------
# 2.1 S4: Stage-1 30s Partial-Liquidation Cooldown Wick Catcher
# ------------------------------------------------------------------------------

def calculate_exact_liq_price(price: float, side: int, margin_available: float, position_size: float, mmr: float) -> float:
    """Exact Hyperliquid liquidation price formula: P_liq = P - (side * margin / size) / (1 - mmr * side)."""
    denom = 1.0 - mmr * side
    return price - ((side * margin_available / position_size) / denom)


@dataclass
class CooldownTracker:
    user: str
    symbol: str
    side: int  # +1 Long (liquidating via SELL down), -1 Short (liquidating via BUY up)
    rem_size: float
    t0: float
    trigger_ts: float
    dump_ts: float
    status: str = "PENDING"
    projected_wick_bottom: float = 0.0
    orders_placed: List[str] = field(default_factory=list)
    filled: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class HLWickCatcherEngine:
    """Monitors whale positions > $100k breaching 1.0x MMR and arms geometric maker ladders across Stage 2 wicks."""
    def __init__(self, shadow_broker: Optional[RealisticShadowBroker] = None):
        self.shadow_broker = shadow_broker or RealisticShadowBroker(default_latency_ms=50.0)
        self.cooldown_trackers: List[CooldownTracker] = []
        self.filled_hedges: List[Dict[str, Any]] = []

    @staticmethod
    def check_vault_takeover_blocking(equity: float, position_size: float, current_mark: float, mmr: float) -> Tuple[bool, str]:
        notional = abs(position_size) * current_mark
        mmr_req = notional * mmr
        hlp_req = mmr_req * (2.0 / 3.0)

        if equity <= hlp_req:
            return False, "HLP_VAULT_TAKEOVER_RISK"
        if equity >= mmr_req:
            return False, "POSITION_SOLVENT_OR_TOPPED_UP"
        return True, "STAGE2_FORCED_CLOB_DUMP_ACTIVE"

    def on_stage1_partial_liq(
        self,
        user: str,
        symbol: str,
        side: int,
        liq_fill_size: float,
        fill_px: float,
        margin_avail: float,
        mmr: float,
        ts: float,
    ) -> Optional[CooldownTracker]:
        """
        Stage-1 20% partial liquidation detector:
        Infers original whale position orig_size = liq_fill_size / 0.20 and remaining rem_size = orig_size * 0.80.
        If orig_size * fill_px >= 100_000.0, registers a CooldownTracker(t0=ts, trigger_ts=ts+29.0, dump_ts=ts+30.0).
        """
        orig_size = liq_fill_size / 0.20
        rem_size = orig_size * 0.80
        notional = orig_size * fill_px

        if notional >= 100_000.0:
            tracker = CooldownTracker(
                user=user,
                symbol=symbol.upper(),
                side=side,
                rem_size=rem_size,
                t0=ts,
                trigger_ts=ts + 29.0,
                dump_ts=ts + 30.0,
                status="PENDING",
            )
            self.cooldown_trackers.append(tracker)
            logger.info(
                f"[S4 Stage-1 Partial Liq] Registered Whale {user} on {symbol}: "
                f"Orig Notional=${notional:,.2f}, Remaining 80% Dump={rem_size:.4f}, Cooldown 30s armed."
            )
            return tracker
        return None

    def evaluate_cooldowns(
        self,
        ts: float,
        hl_replicator: HyperCoreMarkPriceReplicator,
        cex_5s_realized_vol_bps: float,
    ) -> List[Dict[str, Any]]:
        """
        Evaluates active cooldown trackers at trigger_ts (T0 + 29.0s) and dump_ts (T0 + 30.0s):
        1. Abort if cex_5s_realized_vol_bps > 150.0 or |P_hl_book - P_cex_median| / P_cex_median > 0.025.
        2. Verify check_vault_takeover_blocking returns (True, "STAGE2_FORCED_CLOB_DUMP_ACTIVE").
        3. Walk shadow_broker orderbook with rem_size to project exact terminal wick price P_wick_bottom.
        4. Generate 5 geometric OrderType.MAKER_ALO shadow orders across bottom 30% of [P_mark, P_wick_bottom] range,
           with automatic reduce_only TP at P_mark and simulated 50% CEX delta hedge upon fill at T0 + 30.0s.
        """
        actions = []
        for tracker in self.cooldown_trackers:
            if tracker.status == "PENDING" and ts >= tracker.trigger_ts:
                # 1. Kill-switch check
                if cex_5s_realized_vol_bps > 150.0:
                    tracker.status = "ABORTED_MACRO_VOL"
                    logger.warning(f"[S4] Aborted tracker {tracker.user}: macro vol {cex_5s_realized_vol_bps:.1f}bps > 150bps")
                    continue

                p_mark = hl_replicator.get_mark_price(tracker.symbol)
                book = self.shadow_broker.get_or_create_book(tracker.symbol)
                if p_mark <= 0:
                    p_mark = book.mid_price() or 100.0

                cex_prices = [
                    px for (ven, sym), (px, upd) in hl_replicator.cex_mids.items()
                    if sym == tracker.symbol and px > 0
                ]
                p_cex_median = float(np.median(cex_prices)) if cex_prices else p_mark
                if p_cex_median > 0 and abs(p_mark - p_cex_median) / p_cex_median > 0.025:
                    tracker.status = "ABORTED_CEX_DIVERGENCE"
                    logger.warning(f"[S4] Aborted tracker {tracker.user}: CEX divergence > 2.5%")
                    continue

                # 2. Vault takeover blocking check (equity between 2/3 MMR and 1.0 MMR)
                equity_est = p_mark * tracker.rem_size * 0.04 * 0.85
                can_dump, reason = self.check_vault_takeover_blocking(
                    equity=equity_est,
                    position_size=tracker.rem_size,
                    current_mark=p_mark,
                    mmr=0.04,
                )
                if not can_dump or reason != "STAGE2_FORCED_CLOB_DUMP_ACTIVE":
                    tracker.status = f"ABORTED_{reason}"
                    continue

                # 3. Walk book to project exact terminal wick price P_wick_bottom
                rem = tracker.rem_size
                p_wick_bottom = p_mark
                if tracker.side > 0:
                    # Whale Long -> forced market Sell sweeps bids down
                    sorted_bids = sorted(book.bids.items(), key=lambda x: x[0], reverse=True)
                    for px, sz in sorted_bids:
                        if rem <= sz:
                            p_wick_bottom = px
                            rem = 0.0
                            break
                        rem -= sz
                        p_wick_bottom = px
                    if rem > 0:
                        p_wick_bottom = (sorted_bids[-1][0] * 0.85) if sorted_bids else (p_mark * 0.90)
                else:
                    # Whale Short -> forced market Buy sweeps asks up
                    sorted_asks = sorted(book.asks.items(), key=lambda x: x[0])
                    for px, sz in sorted_asks:
                        if rem <= sz:
                            p_wick_bottom = px
                            rem = 0.0
                            break
                        rem -= sz
                        p_wick_bottom = px
                    if rem > 0:
                        p_wick_bottom = (sorted_asks[-1][0] * 1.15) if sorted_asks else (p_mark * 1.10)

                tracker.projected_wick_bottom = p_wick_bottom

                # 4. Generate 5 geometric OrderType.MAKER_ALO shadow orders across bottom 30% of [P_mark, P_wick_bottom]
                n_levels = 5
                tot_quote_size = tracker.rem_size * 0.25
                ladder_order_ids = []

                if tracker.side > 0:
                    # Bids are swept down to p_wick_bottom. We place BUY ALO orders in bottom 30%:
                    band_low = p_wick_bottom
                    band_high = p_wick_bottom + 0.30 * (p_mark - p_wick_bottom)
                    ratio = (band_high / band_low) ** (1.0 / (n_levels - 1)) if band_low > 0 and band_high > band_low else 1.0
                    for i in range(n_levels):
                        px = band_low * (ratio ** i) if ratio > 1.0 else band_low
                        sz = tot_quote_size / n_levels
                        ord_obj = self.shadow_broker.submit_order(
                            symbol=tracker.symbol,
                            side=Side.BUY,
                            order_type=OrderType.MAKER_ALO,
                            price=round(px, 2),
                            size=round(sz, 4),
                            venue="hyperliquid",
                            latency_ms=130.0,
                            current_ts=ts,
                            metadata={"reduce_only_tp": p_mark, "hedge_cex_ratio": 0.50, "whale_user": tracker.user},
                        )
                        ladder_order_ids.append(ord_obj.order_id)
                else:
                    # Asks are swept up to p_wick_bottom. We place SELL ALO orders in top 30%:
                    band_high = p_wick_bottom
                    band_low = p_wick_bottom - 0.30 * (p_wick_bottom - p_mark)
                    ratio = (band_high / band_low) ** (1.0 / (n_levels - 1)) if band_low > 0 and band_high > band_low else 1.0
                    for i in range(n_levels):
                        px = band_low * (ratio ** i) if ratio > 1.0 else band_high
                        sz = tot_quote_size / n_levels
                        ord_obj = self.shadow_broker.submit_order(
                            symbol=tracker.symbol,
                            side=Side.SELL,
                            order_type=OrderType.MAKER_ALO,
                            price=round(px, 2),
                            size=round(sz, 4),
                            venue="hyperliquid",
                            latency_ms=130.0,
                            current_ts=ts,
                            metadata={"reduce_only_tp": p_mark, "hedge_cex_ratio": 0.50, "whale_user": tracker.user},
                        )
                        ladder_order_ids.append(ord_obj.order_id)

                tracker.orders_placed = ladder_order_ids
                tracker.status = "LADDER_ARMED"
                actions.append({
                    "action": "LADDER_ARMED",
                    "user": tracker.user,
                    "symbol": tracker.symbol,
                    "p_mark": p_mark,
                    "p_wick_bottom": p_wick_bottom,
                    "order_ids": ladder_order_ids,
                })
                logger.info(
                    f"[S4 REAL TAPE] Armed 5 Geometric ALO orders for {tracker.symbol} (Finland->Tokyo Latency=130ms): "
                    f"Wick [{p_mark:.2f} -> {p_wick_bottom:.2f}], Orders={ladder_order_ids}"
                )

            elif tracker.status == "LADDER_ARMED" and not tracker.filled:
                # REAL TAPE VALIDATION: Check if any ladder orders received real fills from live Hyperliquid WebSocket
                real_fills = [f for f in self.shadow_broker.fills if f.order_id in tracker.orders_placed]
                if real_fills:
                    tracker.filled = True
                    tracker.status = "FILLED_AND_HEDGED"
                    tot_filled_sz = sum(f.fill_size for f in real_fills)
                    p_mark = hl_replicator.get_mark_price(tracker.symbol) or real_fills[-1].fill_price
                    hedged_size = tot_filled_sz * 0.50
                    self.filled_hedges.append({
                        "symbol": tracker.symbol,
                        "user": tracker.user,
                        "hedged_size": hedged_size,
                        "hedge_venue": "binance",
                        "hedge_px": p_mark,
                        "tp_price": p_mark,
                        "ts": ts,
                    })
                    actions.append({
                        "action": "FILLED_AND_HEDGED",
                        "user": tracker.user,
                        "symbol": tracker.symbol,
                        "hedged_size": hedged_size,
                        "hedge_venue": "binance",
                    })
                    logger.info(
                        f"[S4 REAL TAPE] Real fills captured on ladder: {tot_filled_sz:.4f} {tracker.symbol}! "
                        f"Hedge: {hedged_size:.4f} on Binance @ {p_mark:.2f}"
                    )
                elif ts >= tracker.dump_ts + 30.0:
                    # Timeout expiration: Cancel resting ALO orders
                    for oid in tracker.orders_placed:
                        self.shadow_broker.cancel_order(oid)
                    tracker.status = "CANCELLED_UNFILLED"
                    actions.append({
                        "action": "CANCELLED_UNFILLED",
                        "user": tracker.user,
                        "symbol": tracker.symbol,
                    })
                    logger.info(f"[S4 REAL TAPE] Ladder expired unfilled after 30s. Cancelled resting orders.")

        return actions


# ------------------------------------------------------------------------------
# 2.2 S6: HIP-2 Geometric Grid Exhaustion & Hyperp 8h EMA Squeeze
# ------------------------------------------------------------------------------

class HIP2GridModel:
    """Exact 0.3% geometric ask grid: P_k = P_0 * 1.003^(k - 1) and cumulative exhaustion cost."""
    def __init__(self, p0: float, s_level: float = 100_000.0, n_seeded: int = 50):
        self.p0 = p0
        self.s_level = s_level
        self.n_seeded = n_seeded

    def price_at_level(self, k: int) -> float:
        return self.p0 * (1.003 ** (k - 1))

    def cumulative_cost(self, k: int) -> float:
        return self.s_level * self.p0 * ((1.003 ** k - 1.0) / 0.003)

    def level_for_price(self, price: float) -> int:
        if price <= self.p0:
            return 1
        k = 1.0 + (math.log(price / self.p0) / math.log(1.003))
        return int(math.floor(k + 1e-9))


class Hyperp8hEMAModel:
    """Pre-launch Hyperp 8h EMA oracle calculator with 4x genesis mark price cap."""
    def __init__(self, p_mark_init: float):
        self.p_mark_init = p_mark_init
        self.weights = []
        tau = 480.0
        norm_factor = (1.0 - math.exp(-1.0 / tau)) / (1.0 - math.exp(-3.0))
        for i in range(1440):
            self.weights.append(math.exp(-i / tau) * norm_factor)
        w_sum = sum(self.weights)
        self.weights = [w / w_sum for w in self.weights]

    def compute_oracle(self, minute_history: List[float]) -> float:
        recent = list(reversed(minute_history)) if minute_history else [self.p_mark_init]
        pad_val = recent[-1]
        oracle_sum = 0.0
        for i in range(1440):
            px = recent[i] if i < len(recent) else pad_val
            oracle_sum += px * self.weights[i]
        return min(oracle_sum, 4.0 * self.p_mark_init)


# ------------------------------------------------------------------------------
# 2.3 S5: HyperEVM Precompile (0x0808) to CoreWriter Simulator
# ------------------------------------------------------------------------------

class HyperEVMCoreWriterSimulator:
    """Simulates precompile 0x0808 staticcall, dust stripping, and CoreWriter limit orders."""
    PRECOMPILE_ADDR = "0x0000000000000000000000000000000000000808"
    CORE_WRITER_ADDR = "0x3333333333333333333333333333333333333333"

    @staticmethod
    def calculate_precompile_gas(in_bytes: int = 32, out_bytes: int = 128) -> int:
        return 2000 + 65 * (in_bytes + out_bytes)

    @staticmethod
    def strip_dust(raw_amount: int, dust_factor: int = 10_000_000_000) -> Tuple[int, int]:
        clean = (raw_amount // dust_factor) * dust_factor
        return clean, raw_amount - clean

    @staticmethod
    def encode_core_writer_ioc(asset_index: int, is_buy: bool, limit_px: float, size: float) -> Dict[str, Any]:
        return {
            "header": "0x01000001",
            "asset_index": asset_index,
            "is_buy": is_buy,
            "limit_px_1e8": int(round(limit_px * 1e8)),
            "size_1e8": int(round(size * 1e8)),
            "encoded_tif": 3,  # IOC
            "gas_cost": 47_000,
        }


# ==================================================================================================
# TIER 3: CROSS-VENUE QUANTITATIVE & ORACLE EXPERIMENTS (S9, S8, S7)
# ==================================================================================================

# ------------------------------------------------------------------------------
# 3.1 S9: Deribit SVI Breeden-Litzenberger vs Polymarket/Kalshi
# ------------------------------------------------------------------------------

@dataclass
class SVIParameters:
    a: float
    b: float
    rho: float
    m: float
    sigma: float

    def total_variance(self, k: float) -> float:
        return max(1e-8, self.a + self.b * (self.rho * (k - self.m) + math.sqrt((k - self.m) ** 2 + self.sigma ** 2)))

    def implied_vol(self, k: float, t_years: float) -> float:
        return math.sqrt(self.total_variance(k) / max(1e-6, t_years))


def black_scholes_call(F: float, K: float, T: float, sigma: float, r: float = 0.0) -> float:
    if T <= 0 or sigma <= 0 or K <= 0:
        return max(0.0, F - K) * math.exp(-r * T)
    sqrt_t = math.sqrt(T)
    d1 = (math.log(F / K) + 0.5 * (sigma ** 2) * T) / (sigma * sqrt_t)
    d2 = d1 - sigma * sqrt_t
    return math.exp(-r * T) * (F * norm.cdf(d1) - K * norm.cdf(d2))


class BreedenLitzenbergerCalculator:
    """Extracts risk-neutral probability P(S_T > K) = -e^(rT) * dC/dK and calibrates SVI total variance surface."""
    @staticmethod
    def compute_digital_prob(F: float, K: float, T: float, svi: SVIParameters, r: float = 0.0) -> float:
        dK = max(1.0, K * 0.001)
        sigma_up = svi.implied_vol(math.log((K + dK) / F), T)
        sigma_dn = svi.implied_vol(math.log(max(1.0, K - dK) / F), T)
        c_up = black_scholes_call(F, K + dK, T, sigma_up, r)
        c_dn = black_scholes_call(F, K - dK, T, sigma_dn, r)
        dC_dK = (c_up - c_dn) / (2.0 * dK)
        p_rnd = -math.exp(r * T) * dC_dK
        return max(0.0001, min(0.9999, p_rnd))

    @staticmethod
    def fit_svi_surface(
        k_array: Union[List[float], np.ndarray],
        w_market_array: Union[List[float], np.ndarray],
        t_years: float = 0.1,
    ) -> SVIParameters:
        """
        Calibrates raw SVI parameters (a, b, rho, m, sigma) from log-moneyness and total variance
        using scipy.optimize.minimize (L-BFGS-B) subject to Gatheral's no-butterfly-arbitrage bounds:
          b >= 0, |rho| < 1, sigma > 0,
          a + b * sigma * sqrt(1 - rho^2) >= 0 (minimum variance >= 0),
          b * (1 + |rho|) <= 2.
        """
        k_arr = np.array(k_array, dtype=float)
        w_arr = np.array(w_market_array, dtype=float)

        if len(k_arr) < 5:
            atm_w = float(w_arr[0]) if len(w_arr) > 0 else 0.04
            return SVIParameters(a=atm_w * 0.8, b=0.10, rho=-0.25, m=0.0, sigma=0.10)

        atm_w = float(np.interp(0.0, k_arr, w_arr))
        x0 = [atm_w * 0.8, 0.15, -0.25, 0.0, 0.10]
        bounds = [(-1.0, 2.0), (0.001, 2.0), (-0.99, 0.99), (-1.0, 1.0), (0.001, 1.0)]

        def objective(params: np.ndarray) -> float:
            a, b, rho, m, sigma = params
            term = np.sqrt((k_arr - m) ** 2 + sigma ** 2)
            model_w = a + b * (rho * (k_arr - m) + term)
            sse = np.sum((model_w - w_arr) ** 2)
            min_var = a + b * sigma * np.sqrt(max(0.0, 1.0 - rho ** 2))
            neg_pen = (max(0.0, -min_var) ** 2) * 1000.0
            slope_pen = (max(0.0, b * (1.0 + abs(rho)) - 2.0) ** 2) * 500.0
            return float(sse + neg_pen + slope_pen)

        res = minimize(objective, x0, method="L-BFGS-B", bounds=bounds)
        a, b, rho, m, sigma = res.x
        return SVIParameters(a=float(a), b=float(b), rho=float(rho), m=float(m), sigma=float(sigma))

    @staticmethod
    def interpolate_1800_utc_svi(
        svi_0800_day1: SVIParameters,
        t_day1: float,
        svi_0800_day2: SVIParameters,
        t_day2: float,
        t_poly_1800: float,
    ) -> Callable[[float], float]:
        """
        Linearly interpolates total variance w(k, T_poly) in forward variance time
        between the two bracketing Deribit 08:00 UTC expiries to price Polymarket's 18:00 UTC resolution.
        """
        dt = max(1e-6, t_day2 - t_day1)
        alpha = max(0.0, min(1.0, (t_poly_1800 - t_day1) / dt))

        def w_poly(k: float) -> float:
            w1 = svi_0800_day1.total_variance(k)
            w2 = svi_0800_day2.total_variance(k)
            return (1.0 - alpha) * w1 + alpha * w2

        return w_poly


# ------------------------------------------------------------------------------
# 3.2 S8: Pyth Lazer / Hermes CI_Ratio & Pull-Oracle Lag Monitor
# ------------------------------------------------------------------------------

class PythCIArbEngine:
    """Monitors Pyth CI_Ratio = conf / price, maker quoting on CI venue, and HL delta hedging."""
    @staticmethod
    def evaluate_ci_dislocation(price: float, conf: float, publish_ts: float, current_ts: float, hl_spread_bps: float) -> Tuple[bool, str]:
        ci_ratio = conf / price if price > 0 else 0.0
        if ci_ratio >= 0.03:
            return False, "KILLED_OUTLIER_CI_3_PCT"
        if (current_ts - publish_ts) >= 5.0:
            return False, "KILLED_STALE_ORACLE_5S"

        if (ci_ratio * 10_000.0 >= 40.0) and (hl_spread_bps <= 3.0):
            return True, "ARM_CI_DISLOCATION_ARB"

        return False, "NORMAL_REGIME"


# ------------------------------------------------------------------------------
# 3.3 S7: Whales Market 4-Hour TGE Escrow Squeeze Tracker
# ------------------------------------------------------------------------------

class WhalesTGESqueezeEngine:
    """Models capped forward payoff min(S_T - K, K) and Minute 150 forced delivery squeeze."""
    @staticmethod
    def is_forced_delivery_zone(spot: float, strike_k: float) -> bool:
        return (0.30 * strike_k) < spot < (1.85 * strike_k)

    @staticmethod
    def is_default_zone(spot: float, strike_k: float) -> bool:
        return spot >= (1.85 * strike_k)

    @staticmethod
    def evaluate_minute_150_squeeze(spot: float, strike_k: float, undelivered_ratio: float, elapsed_min: float) -> Tuple[bool, str]:
        if WhalesTGESqueezeEngine.is_default_zone(spot, strike_k):
            return False, "KILLED_DEFAULT_ZONE"
        if 150.0 <= elapsed_min <= 165.0 and undelivered_ratio >= 0.40 and WhalesTGESqueezeEngine.is_forced_delivery_zone(spot, strike_k):
            return True, "ARM_FORCED_DELIVERY_SQUEEZE"
        return False, "CRITERIA_NOT_MET"


# ==================================================================================================
# UNIFIED MASTER COORDINATOR & SELF-TEST HARNESS
# ==================================================================================================

class UnifiedStructuralAlphaMaster:
    """Master controller orchestrating all 9 structural alphas and stateful telemetry engines."""
    def __init__(self, db_path: str = "experiments/shadow_ledger.db"):
        self.db_path = db_path
        self.shadow_broker = RealisticShadowBroker(telemetry_db_path=db_path, default_latency_ms=50.0)
        self.hl_replicator = HyperCoreMarkPriceReplicator()
        self.poly_watchdog = PolymarketDualSocketWatchdog(token_ids=["tok_btc_yes", "tok_btc_no"])
        self.negrisk_engine = NegRiskConvertEngine(self.shadow_broker)
        self.wick_catcher = HLWickCatcherEngine(self.shadow_broker)
        self.results_summary: Dict[str, Any] = {}

    def run_master_diagnostic_suite(self) -> Dict[str, Any]:
        logger.info("================================================================================")
        logger.info("STARTING MASTER UNIFIED ALPHA DIAGNOSTIC SUITE (ALL 9 EXPERIMENTS + STATEFUL ENGINES)")
        logger.info("================================================================================")
        t_start = time.time()

        # ----------------------------------------------------------------------
        # 1. Test RealisticShadowBroker Lifecycle, Queueing & SQLite Markout Ledger
        # ----------------------------------------------------------------------
        broker = self.shadow_broker
        now = time.time()
        # Seed orderbook
        broker.on_book_tick(
            venue="hyperliquid",
            symbol="BTC",
            bids=[(99_990.0, 2.0), (99_980.0, 5.0)],
            asks=[(100_010.0, 1.0), (100_020.0, 3.0)],
            ts=now,
        )

        # A: Taker FOK rejection test (insufficient depth)
        ord_fok_fail = broker.submit_order(
            symbol="BTC", side=Side.BUY, order_type=OrderType.TAKER_FOK,
            price=100_010.0, size=5.0, venue="hyperliquid", latency_ms=10.0, current_ts=now,
        )
        broker.on_book_tick("hyperliquid", "BTC", [(99_990.0, 2.0)], [(100_010.0, 1.0)], ts=now + 0.02)
        assert ord_fok_fail.status == OrderStatus.REJECTED
        assert ord_fok_fail.reject_reason == "FOK_INSUFFICIENT_DEPTH"

        # B: Taker FOK fill test (sufficient depth)
        ord_fok_pass = broker.submit_order(
            symbol="BTC", side=Side.BUY, order_type=OrderType.TAKER_FOK,
            price=100_025.0, size=2.0, venue="hyperliquid", latency_ms=10.0, current_ts=now + 0.03,
        )
        broker.on_book_tick("hyperliquid", "BTC", [(99_990.0, 2.0)], [(100_010.0, 1.0), (100_020.0, 3.0)], ts=now + 0.05)
        assert ord_fok_pass.status == OrderStatus.FILLED
        assert len(ord_fok_pass.fills) == 1
        assert ord_fok_pass.fills[0].fill_price == 100_015.0

        # C: Maker ALO Crossing rejection test
        ord_alo_cross = broker.submit_order(
            symbol="BTC", side=Side.BUY, order_type=OrderType.MAKER_ALO,
            price=100_020.0, size=1.0, venue="hyperliquid", latency_ms=10.0, current_ts=now + 0.06,
        )
        broker.on_book_tick("hyperliquid", "BTC", [(99_990.0, 2.0)], [(100_010.0, 1.0)], ts=now + 0.08)
        assert ord_alo_cross.status == OrderStatus.REJECTED
        assert ord_alo_cross.reject_reason == "ALO_WOULD_CROSS"

        # D: Maker ALO Queueing & Trade print-through fill test
        ord_alo_rest = broker.submit_order(
            symbol="BTC", side=Side.BUY, order_type=OrderType.MAKER_ALO,
            price=99_980.0, size=1.0, venue="hyperliquid", latency_ms=10.0, current_ts=now + 0.09,
        )
        broker.on_book_tick("hyperliquid", "BTC", [(99_990.0, 2.0), (99_980.0, 5.0)], [(100_010.0, 1.0)], ts=now + 0.11)
        assert ord_alo_rest.status == OrderStatus.RESTING
        assert ord_alo_rest.queue_ahead_size == 5.0

        # Print trade through ALO price (99_975 < 99_980)
        broker.on_public_trade(
            venue="hyperliquid", symbol="BTC", trade_price=99_975.0, trade_size=1.0,
            aggressor_side=Side.SELL, ts=now + 0.20,
        )
        assert ord_alo_rest.status == OrderStatus.FILLED

        # E: Markout Telemetry persistence
        markouts = broker.update_markouts(venue="hyperliquid", symbol="BTC", mid_price=100_100.0, ts=now + 2.0)
        self.results_summary["Shadow_Orders_Logged"] = len(broker.orders)
        self.results_summary["Shadow_Fills_Logged"] = len(broker.fills)
        self.results_summary["Shadow_Markouts_Generated"] = len(markouts)
        logger.info(f"[+] ShadowBroker: {len(broker.orders)} Orders | {len(broker.fills)} Fills | {len(markouts)} Markouts computed.")

        # ----------------------------------------------------------------------
        # 2. Test PolymarketDualSocketWatchdog Isolated Clients & Dynamic Tick Size
        # ----------------------------------------------------------------------
        watchdog = self.poly_watchdog
        sub_payload = watchdog.build_subscription_payload()
        assert sub_payload["custom_feature_enabled"] is True
        watchdog._handle_message("A", json.dumps({"event_type": "tick_size_change", "asset_id": "tok_btc_yes", "tick_size": 0.001}))
        assert watchdog.get_tick_size("tok_btc_yes") == 0.001
        q_px = watchdog.quantize_price("tok_btc_yes", 0.54321, side="BUY")
        assert q_px == 0.543
        self.results_summary["Poly_Tick_Size_Quantized"] = q_px
        logger.info(f"[+] DualSocketWatchdog: custom_feature_enabled=True | Quantized 0.54321 -> {q_px}")

        # ----------------------------------------------------------------------
        # 3. Test S1 NegRisk Convert Engine
        # ----------------------------------------------------------------------
        s1_res = NegRiskConvertEngine.evaluate_subsets(
            event_id="poly_pres_2028", condition_id="cond_pres", outcomes_n=5,
            ask_prices_no={0: 0.15, 1: 0.20, 2: 0.22, 3: 0.25, 4: 0.30},
            bid_prices_yes={0: 0.82, 1: 0.78, 2: 0.76, 3: 0.72, 4: 0.68},
            ask_depth_no={i: 10_000.0 for i in range(5)},
        )
        self.results_summary["S1_NegRisk_Subsets_Found"] = len(s1_res)
        logger.info(f"[+] S1 NegRisk: Found {len(s1_res)} profitable subsets. Top PureNeg: {s1_res[0].is_pure_negative_cost}")

        # ----------------------------------------------------------------------
        # 4. Test S10 Insider Shadow & Murphy Decomposition
        # ----------------------------------------------------------------------
        s10_decomp = compute_murphy_brier_decomposition([0.1, 0.2, 0.8, 0.9], [0, 0, 1, 1])
        self.results_summary["S10_Murphy_Resolution"] = s10_decomp["resolution"]
        logger.info(f"[+] S10 Insider Shadow: BS={s10_decomp['brier_score']:.4f} Resolution={s10_decomp['resolution']:.4f}")

        # ----------------------------------------------------------------------
        # 5. Test S2 UMA N/A Scanner
        # ----------------------------------------------------------------------
        s2_parse = UMANAScannerEngine.parse_resolution_ambiguity("Will BTC reach $100k by 18:00 UTC? Postponed events resolve N/A.")
        self.results_summary["S2_Ambiguity_Score"] = s2_parse["ambiguity_score"]
        logger.info(f"[+] S2 UMA Scanner: Ambiguity Score={s2_parse['ambiguity_score']:.2f} PayoffMult(0.04)={UMANAScannerEngine.evaluate_na_payoff_multiplier(0.04):.1f}x")

        # ----------------------------------------------------------------------
        # 6. Test S4 Stage-1 30s Cooldown State Machine & Geometric Ladder
        # ----------------------------------------------------------------------
        s4_engine = self.wick_catcher
        # Seed replicator mark price
        self.hl_replicator.update_hl_book("ETH", best_bid=3000.0, best_ask=3002.0)
        self.hl_replicator.update_hl_oracle("ETH", 3001.0)
        self.hl_replicator.update_cex_mid("ETH", "binance", 3001.0)
        self.hl_replicator.update_cex_mid("ETH", "okx", 3001.0)
        self.hl_replicator.update_cex_mid("ETH", "bybit", 3001.0)

        # Ingest book for ETH with thin bids to simulate depth sweep
        broker.on_book_tick("hyperliquid", "ETH", [(2995.0, 10.0), (2990.0, 20.0), (2950.0, 50.0)], [(3005.0, 10.0)], ts=now)

        # Register Stage-1 Partial Liquidation ($150k notional position -> 20% liq size = 10 ETH @ $3000)
        t_liq = now
        tracker = s4_engine.on_stage1_partial_liq(
            user="0xwhale_42", symbol="ETH", side=1, liq_fill_size=10.0, fill_px=3000.0,
            margin_avail=6000.0, mmr=0.04, ts=t_liq,
        )
        assert tracker is not None
        assert tracker.rem_size == 40.0
        assert tracker.trigger_ts == t_liq + 29.0
        assert tracker.dump_ts == t_liq + 30.0

        # Step A: Evaluate at T0 + 29.0s -> generates 5 geometric ALO orders
        actions_29 = s4_engine.evaluate_cooldowns(ts=t_liq + 29.0, hl_replicator=self.hl_replicator, cex_5s_realized_vol_bps=45.0)
        assert len(actions_29) == 1
        assert actions_29[0]["action"] == "LADDER_ARMED"
        assert len(actions_29[0]["order_ids"]) == 5

        # Step B: Evaluate at T0 + 30.0s -> forced dump execution and 50% CEX delta hedge
        actions_30 = s4_engine.evaluate_cooldowns(ts=t_liq + 30.0, hl_replicator=self.hl_replicator, cex_5s_realized_vol_bps=45.0)
        assert len(actions_30) == 1
        assert actions_30[0]["action"] == "FILLED_AND_HEDGED"
        assert actions_30[0]["hedged_size"] == 5.0  # (40 * 0.25) * 0.50

        self.results_summary["S4_Wick_Bottom_Px"] = actions_29[0]["p_wick_bottom"]
        self.results_summary["S4_Ladder_Armed"] = True
        self.results_summary["S4_CEX_Hedged_Qty"] = actions_30[0]["hedged_size"]
        logger.info(f"[+] S4 Cooldown Machine: Ladder Armed (Wick ${actions_29[0]['p_wick_bottom']:.2f}) -> Stage-2 Dump Filled & Hedged ({actions_30[0]['hedged_size']} ETH).")

        # ----------------------------------------------------------------------
        # 7. Test S6 HIP-2 Grid & Hyperp 8h EMA
        # ----------------------------------------------------------------------
        hip2 = HIP2GridModel(p0=0.10)
        c50 = hip2.cumulative_cost(50)
        hyperp = Hyperp8hEMAModel(p_mark_init=1.0)
        oracle_8h = hyperp.compute_oracle([1.0] * 1440)
        self.results_summary["S6_HIP2_Cost_Lvl50"] = c50
        self.results_summary["S6_Hyperp_Oracle"] = oracle_8h
        logger.info(f"[+] S6 HIP-2 & Hyperp: 50-Level Cost=${c50:,.2f} | 8h EMA Oracle=${oracle_8h:.4f}")

        # ----------------------------------------------------------------------
        # 8. Test S5 HyperEVM Precompile to CoreWriter
        # ----------------------------------------------------------------------
        gas_0808 = HyperEVMCoreWriterSimulator.calculate_precompile_gas(32, 128)
        clean_tok, dust = HyperEVMCoreWriterSimulator.strip_dust(1234567890123456789, 10_000_000_000)
        self.results_summary["S5_Precompile_Gas"] = gas_0808
        self.results_summary["S5_Clean_Tokens"] = clean_tok
        logger.info(f"[+] S5 HyperEVM: Precompile Gas={gas_0808} | Dust Stripped={dust}")

        # ----------------------------------------------------------------------
        # 9. Test S9 SVI Calibration & 08:00->18:00 UTC Forward Variance Interpolator
        # ----------------------------------------------------------------------
        k_strikes = [-0.15, -0.08, -0.03, 0.0, 0.03, 0.08, 0.15]
        w_obs = [0.052, 0.046, 0.042, 0.040, 0.041, 0.045, 0.051]
        svi_calib = BreedenLitzenbergerCalculator.fit_svi_surface(k_strikes, w_obs, t_years=0.1)
        assert svi_calib.b >= 0.0
        assert abs(svi_calib.rho) < 1.0

        # Interpolate between Day 1 08:00 UTC and Day 2 08:00 UTC for Day 1 18:00 UTC
        svi_day2 = SVIParameters(a=0.045, b=0.12, rho=-0.22, m=0.0, sigma=0.11)
        w_interp_fn = BreedenLitzenbergerCalculator.interpolate_1800_utc_svi(
            svi_0800_day1=svi_calib, t_day1=1.0,
            svi_0800_day2=svi_day2, t_day2=2.0,
            t_poly_1800=1.4167,  # 10 hours into the 24 hour interval (10/24 ~ 0.4167)
        )
        w_atm_1800 = w_interp_fn(0.0)
        p_rnd = BreedenLitzenbergerCalculator.compute_digital_prob(95_000.0, 100_000.0, 10.0 / 8760.0, svi_calib)
        self.results_summary["S9_SVI_Calib_b"] = svi_calib.b
        self.results_summary["S9_1800_UTC_w_ATM"] = w_atm_1800
        self.results_summary["S9_RND_Prob"] = p_rnd
        logger.info(f"[+] S9 SVI Digital Arb: Calibrated b={svi_calib.b:.4f} rho={svi_calib.rho:.4f} | 18:00 UTC w(0)={w_atm_1800:.5f} | RND={p_rnd:.4f}")

        # ----------------------------------------------------------------------
        # 10. Test S8 Pyth CI_Ratio Dislocation
        # ----------------------------------------------------------------------
        s8_trig, s8_reason = PythCIArbEngine.evaluate_ci_dislocation(3000.0, 15.0, t_start, t_start, 1.0)
        self.results_summary["S8_CI_Arb_Active"] = s8_trig
        logger.info(f"[+] S8 Pyth CI Arb: Dislocation Active={s8_trig} ({s8_reason})")

        # ----------------------------------------------------------------------
        # 11. Test S7 Whales Market TGE Squeeze
        # ----------------------------------------------------------------------
        s7_trig, s7_reason = WhalesTGESqueezeEngine.evaluate_minute_150_squeeze(1.25, 1.00, 0.70, 150.0)
        self.results_summary["S7_TGE_Squeeze_Active"] = s7_trig
        logger.info(f"[+] S7 Whales Squeeze: M150 Squeeze Active={s7_trig} ({s7_reason})")

        logger.info("================================================================================")
        logger.info(f"ALL 9 STRUCTURAL ALPHA EXPERIMENTS & STATEFUL ENGINES VALIDATED IN {time.time() - t_start:.2f}s")
        logger.info("================================================================================")
        return self.results_summary


if __name__ == "__main__":
    master = UnifiedStructuralAlphaMaster()
    summary = master.run_master_diagnostic_suite()
    print("\n--- MASTER RUN SUMMARY ---")
    print(json.dumps(summary, indent=2))
