#!/usr/bin/env python3
"""
Realistic Shadow Execution & Replay Engine (shadow_broker.py)
============================================================
Institutional-grade execution simulator for Polymarket and Hyperliquid / APEX.

Key Capabilities:
  1. Dual Execution Modes:
     - Live Shadow Mode (real-time async event loop)
     - Historical Parquet / DuckDB Replay Mode (microsecond-accurate backtesting)

  2. Taker FOK / IOC Orders:
     - Applies configurable latency dt_latency (e.g. 120ms Polymarket pre-signed FOK, 50ms HyperCore)
     - Walks the full L2 book at t0 + dt_latency (NOT at submission time t0).
     - FOK: Fills completely at weighted average price if depth >= requested, else cancels immediately.
     - IOC: Fills available depth up to requested size & limit price, cancels remainder.

  3. Maker ALO (Add-Liquidity-Only / Post-Only) Orders:
     - Rejects at t0 + dt_latency if book has crossed during transit (limit >= ask for BUY or <= bid for SELL).
     - Tracks exact `queue_ahead_size` at limit price.
     - Fills when:
       a) Trades print *through* our price level (immediate fill).
       b) Cumulative trade volume at our price exceeds `queue_ahead_size`.

  4. Markout Telemetry Engine:
     - Automatically logs PnL markouts at +1s, +5s, +30s, +5m, +1h, and resolution into DuckDB/SQLite.
     - Computes signed basis-point markouts and realized dollar PnL.
"""

from __future__ import annotations

import asyncio
import logging
import math
import os
import sqlite3
import sys
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("ShadowBroker")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("[%(asctime)s UTC] [%(levelname)s] [SHADOW-BROKER] %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Standard Markout Horizons in seconds (None represents terminal resolution)
MARKOUT_HORIZONS: Dict[str, Optional[float]] = {
    "1s": 1.0,
    "5s": 5.0,
    "30s": 30.0,
    "5m": 300.0,
    "1h": 3600.0,
    "resolution": None,
}

# Standard Default Execution Latencies
DEFAULT_LATENCIES_MS = {
    "polymarket": 120.0,   # 120ms pre-signed FOK / CLOB transit
    "hyperliquid": 50.0,   # 50ms HyperCore transit
    "default": 75.0,
}


# ==============================================================================
# 1. ENUMS AND DATA CONTRACTS
# ==============================================================================

class OrderType(str, Enum):
    TAKER_FOK = "TAKER_FOK"  # Fill-Or-Kill Taker
    TAKER_IOC = "TAKER_IOC"  # Immediate-Or-Cancel Taker
    MAKER_ALO = "MAKER_ALO"  # Add-Liquidity-Only (Post-Only Maker)


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
class ShadowOrder:
    order_id: str
    symbol: str
    venue: str
    order_type: OrderType
    side: Side
    price: float
    size: float
    remaining_size: float
    created_ts: float  # Submission timestamp t0
    latency_ms: float  # Configurable transit latency
    arrival_ts: float  # t0 + (latency_ms / 1000.0)
    status: OrderStatus = OrderStatus.SUBMITTED
    queue_ahead_size: float = 0.0
    reject_reason: Optional[str] = None
    fills: List[ShadowFill] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


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
    liquidity_role: str  # "TAKER" or "MAKER"
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


# ==============================================================================
# 2. LOCAL L2 ORDER BOOK MODEL
# ==============================================================================

class L2Book:
    """
    Price-level order book tracker. Supports depth aggregation, walking the book,
    and calculating weighted execution prices.
    """

    def __init__(self, symbol: str):
        self.symbol: str = symbol
        self.bids: Dict[float, float] = {}  # price -> size
        self.asks: Dict[float, float] = {}  # price -> size
        self.last_update_ts: float = 0.0

    def apply_snapshot(
        self,
        bids: List[Union[Dict[str, Any], Tuple[float, float], List[float]]],
        asks: List[Union[Dict[str, Any], Tuple[float, float], List[float]]],
        ts: Optional[float] = None,
    ) -> None:
        """Applies full book snapshot."""
        self.bids.clear()
        self.asks.clear()

        for b in bids:
            px, sz = self._parse_level(b)
            if sz > 0:
                self.bids[px] = sz

        for a in asks:
            px, sz = self._parse_level(a)
            if sz > 0:
                self.asks[px] = sz

        if ts is not None:
            self.last_update_ts = ts

    def set_level(self, price: float, size: float, side: Side, ts: Optional[float] = None) -> None:
        """Sets or deletes a specific price level."""
        target_dict = self.bids if side == Side.BUY else self.asks
        if size <= 0:
            target_dict.pop(price, None)
        else:
            target_dict[price] = float(size)
        if ts is not None:
            self.last_update_ts = ts

    @staticmethod
    def _parse_level(item: Any) -> Tuple[float, float]:
        if isinstance(item, dict):
            return float(item.get("px", item.get("price", 0.0))), float(item.get("sz", item.get("size", 0.0)))
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            return float(item[0]), float(item[1])
        return 0.0, 0.0

    def best_bid(self) -> Optional[float]:
        return max(self.bids.keys()) if self.bids else None

    def best_ask(self) -> Optional[float]:
        return min(self.asks.keys()) if self.asks else None

    def mid_price(self) -> Optional[float]:
        bb = self.best_bid()
        ba = self.best_ask()
        if bb is not None and ba is not None:
            return (bb + ba) / 2.0
        return bb or ba

    def get_depth_at_price(self, price: float, side: Side) -> float:
        """Returns existing quantity at exact price level."""
        d = self.bids if side == Side.BUY else self.asks
        return d.get(price, 0.0)

    def walk_book(
        self,
        side: Side,
        requested_size: float,
        limit_price: float,
    ) -> Tuple[float, float, List[Tuple[float, float]]]:
        """
        Simulates taker walking the book up to requested_size and limit_price.
        Returns: (filled_size, weighted_avg_price, list_of_level_executions)
        """
        levels_filled: List[Tuple[float, float]] = []
        rem_size = requested_size
        cost_accum = 0.0
        total_filled = 0.0

        if side == Side.BUY:
            # Walk asks ascending
            sorted_prices = sorted(self.asks.keys())
            for px in sorted_prices:
                if px > limit_price or rem_size <= 1e-9:
                    break
                available = self.asks[px]
                fill_qty = min(rem_size, available)
                levels_filled.append((px, fill_qty))
                cost_accum += fill_qty * px
                total_filled += fill_qty
                rem_size -= fill_qty
        else:
            # Walk bids descending
            sorted_prices = sorted(self.bids.keys(), reverse=True)
            for px in sorted_prices:
                if px < limit_price or rem_size <= 1e-9:
                    break
                available = self.bids[px]
                fill_qty = min(rem_size, available)
                levels_filled.append((px, fill_qty))
                cost_accum += fill_qty * px
                total_filled += fill_qty
                rem_size -= fill_qty

        avg_price = (cost_accum / total_filled) if total_filled > 0 else 0.0
        return total_filled, avg_price, levels_filled


# ==============================================================================
# 3. DUCKDB / SQLITE MARKOUT TELEMETRY STORE
# ==============================================================================

class ShadowTelemetryDB:
    """
    High-performance telemetry store for orders, fills, and markout horizons.
    Supports DuckDB natively when available, with automatic SQLite fallback.
    """

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self.is_duckdb: bool = False
        self._conn = None
        self._init_backend()

    def _init_backend(self) -> None:
        try:
            import duckdb
            self._conn = duckdb.connect(self.db_path)
            self.is_duckdb = True
            logger.info(f"[DB] Initialized DuckDB telemetry store at {self.db_path}")
        except Exception:
            self._conn = sqlite3.connect(self.db_path)
            self.is_duckdb = False
            logger.info(f"[DB] Fallback: Initialized SQLite telemetry store at {self.db_path}")

        self._create_schema()

    def _create_schema(self) -> None:
        c = self._conn.cursor()
        c.execute("""
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
        c.execute("""
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
        c.execute("""
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
        if not self.is_duckdb:
            self._conn.commit()

    def insert_order(self, order: ShadowOrder) -> None:
        c = self._conn.cursor()
        if self.is_duckdb:
            c.execute("""
                INSERT OR REPLACE INTO shadow_orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order.order_id, order.symbol, order.venue, order.order_type.value,
                order.side.value, order.price, order.size, order.remaining_size,
                order.created_ts, order.latency_ms, order.arrival_ts,
                order.status.value, order.queue_ahead_size, order.reject_reason
            ))
        else:
            c.execute("""
                INSERT OR REPLACE INTO shadow_orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order.order_id, order.symbol, order.venue, order.order_type.value,
                order.side.value, order.price, order.size, order.remaining_size,
                order.created_ts, order.latency_ms, order.arrival_ts,
                order.status.value, order.queue_ahead_size, order.reject_reason
            ))
            self._conn.commit()

    def insert_fill(self, fill: ShadowFill) -> None:
        c = self._conn.cursor()
        c.execute("""
            INSERT OR REPLACE INTO shadow_fills VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            fill.fill_id, fill.order_id, fill.symbol, fill.venue, fill.side.value,
            fill.fill_time, fill.fill_price, fill.fill_size, fill.liquidity_role,
            fill.queue_ahead_at_entry, fill.fee_usd
        ))
        if not self.is_duckdb:
            self._conn.commit()

    def record_markout(self, markout: ShadowMarkout) -> None:
        c = self._conn.cursor()
        c.execute("""
            INSERT OR REPLACE INTO shadow_markouts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            markout.fill_id, markout.order_id, markout.symbol, markout.horizon_label,
            markout.scheduled_ts, markout.recorded_ts, markout.fill_price,
            markout.markout_mid_price, markout.markout_pnl_bps, markout.markout_pnl_usd,
            1 if markout.is_final else 0
        ))
        if not self.is_duckdb:
            self._conn.commit()

    def query_markouts(self) -> List[Dict[str, Any]]:
        c = self._conn.cursor()
        c.execute("SELECT * FROM shadow_markouts ORDER BY scheduled_ts ASC")
        cols = [desc[0] for desc in c.description]
        return [dict(zip(cols, row)) for row in c.fetchall()]

    def close(self) -> None:
        if self._conn:
            self._conn.close()


# ==============================================================================
# 4. REALISTIC SHADOW BROKER ENGINE
# ==============================================================================

class RealisticShadowBroker:
    """
    Realistic Shadow Execution & Replay Engine.

    Manages order states, placement transit delays, orderbook crossing validation,
    resting maker queue depth, trade tape matching, and markout telemetry.
    """

    def __init__(
        self,
        telemetry_db_path: str = ":memory:",
        default_latency_ms: Optional[float] = None,
        taker_fee_bps: float = 4.5,
        maker_rebate_bps: float = -1.5,
    ):
        self.default_latency = default_latency_ms
        self.taker_fee_bps = taker_fee_bps
        self.maker_rebate_bps = maker_rebate_bps

        # Internal state
        self.books: Dict[str, L2Book] = {}
        self.orders: Dict[str, ShadowOrder] = {}
        self.pending_in_flight: List[ShadowOrder] = []
        self.resting_alo_orders: List[ShadowOrder] = []
        self.fills: List[ShadowFill] = []
        self.pending_markouts: List[ShadowMarkout] = []

        # Database telemetry backend
        self.db = ShadowTelemetryDB(telemetry_db_path)

        # Mode controls
        self.is_live: bool = False
        self._live_worker_task: Optional[asyncio.Task] = None

    def get_or_create_book(self, symbol: str) -> L2Book:
        if symbol not in self.books:
            self.books[symbol] = L2Book(symbol)
        return self.books[symbol]

    # --------------------------------------------------------------------------
    # ORDER SUBMISSION INTERFACE
    # --------------------------------------------------------------------------

    def submit_order(
        self,
        symbol: str,
        side: Union[Side, str],
        order_type: Union[OrderType, str],
        price: float,
        size: float,
        venue: str = "polymarket",
        latency_ms: Optional[float] = None,
        current_ts: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ShadowOrder:
        """
        Submits an order at t0. It will NOT match at t0.
        It enters IN_FLIGHT state and executes at arrival_ts = t0 + latency.
        """
        sym = symbol.upper()
        s_side = Side(side.upper()) if isinstance(side, str) else side
        o_type = OrderType(order_type.upper()) if isinstance(order_type, str) else order_type

        t0 = time.time() if current_ts is None else float(current_ts)
        effective_latency = (
            latency_ms
            if latency_ms is not None
            else (self.default_latency or DEFAULT_LATENCIES_MS.get(venue.lower(), DEFAULT_LATENCIES_MS["default"]))
        )
        t_arrival = t0 + (effective_latency / 1000.0)

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
            latency_ms=effective_latency,
            arrival_ts=t_arrival,
            status=OrderStatus.IN_FLIGHT,
            metadata=metadata or {},
        )

        self.orders[order_id] = order
        self.pending_in_flight.append(order)
        self.db.insert_order(order)

        logger.debug(
            f"[SUBMIT] {order_id} ({order.order_type.value} {order.side.value} {order.size} @ {order.price}) "
            f"in flight to {venue}. Transit latency: {effective_latency}ms"
        )
        return order

    # --------------------------------------------------------------------------
    # ORDER ARRIVAL & MATCHING ENGINE (AT t_arrival = t0 + dt_latency)
    # --------------------------------------------------------------------------

    def evaluate_order_arrival(self, order: ShadowOrder, current_ts: float) -> None:
        """
        Evaluates order matching strictly against the book at arrival_ts.
        """
        book = self.get_or_create_book(order.symbol)

        # ----------------------------------------------------------------------
        # TAKER ORDERS: FOK & IOC
        # ----------------------------------------------------------------------
        if order.order_type in (OrderType.TAKER_FOK, OrderType.TAKER_IOC):
            filled_qty, avg_px, level_fills = book.walk_book(
                side=order.side,
                requested_size=order.remaining_size,
                limit_price=order.price,
            )

            # Case A: TAKER FOK
            if order.order_type == OrderType.TAKER_FOK:
                if filled_qty >= (order.remaining_size - 1e-9):
                    # FOK Success: Full fill
                    self._register_fill(
                        order=order,
                        fill_qty=order.remaining_size,
                        fill_price=avg_px,
                        current_ts=current_ts,
                        role="TAKER",
                    )
                    order.status = OrderStatus.FILLED
                    order.remaining_size = 0.0
                    for px, sz in level_fills:
                        target_dict = book.asks if order.side == Side.BUY else book.bids
                        if px in target_dict:
                            target_dict[px] -= sz
                            if target_dict[px] <= 1e-9:
                                target_dict.pop(px, None)
                    logger.info(f"[FILL FOK] {order.order_id} filled {order.size} @ {avg_px:.4f}")
                else:
                    # FOK Failure: Reject immediately
                    order.status = OrderStatus.REJECTED
                    order.reject_reason = (
                        f"FOK_INSUFFICIENT_LIQUIDITY (Avail: {filled_qty:.2f} < Req: {order.remaining_size:.2f})"
                    )
                    logger.info(f"[REJECT FOK] {order.order_id}: {order.reject_reason}")

            # Case B: TAKER IOC
            elif order.order_type == OrderType.TAKER_IOC:
                if filled_qty > 1e-9:
                    self._register_fill(
                        order=order,
                        fill_qty=filled_qty,
                        fill_price=avg_px,
                        current_ts=current_ts,
                        role="TAKER",
                    )
                    order.remaining_size -= filled_qty
                    if order.remaining_size <= 1e-9:
                        order.status = OrderStatus.FILLED
                    else:
                        order.status = OrderStatus.PARTIALLY_FILLED
                    for px, sz in level_fills:
                        target_dict = book.asks if order.side == Side.BUY else book.bids
                        if px in target_dict:
                            target_dict[px] -= sz
                            if target_dict[px] <= 1e-9:
                                target_dict.pop(px, None)
                    logger.info(f"[FILL IOC] {order.order_id} filled {filled_qty:.2f} @ {avg_px:.4f}")
                else:
                    order.status = OrderStatus.CANCELLED
                    order.reject_reason = "IOC_ZERO_FILL_AVAILABLE"
                    logger.info(f"[CANCEL IOC] {order.order_id}: {order.reject_reason}")

        # ----------------------------------------------------------------------
        # MAKER ORDER: ALO (Add-Liquidity-Only / Post-Only)
        # ----------------------------------------------------------------------
        elif order.order_type == OrderType.MAKER_ALO:
            bb = book.best_bid()
            ba = book.best_ask()

            # Invariant: Reject if book crossed during transit
            if order.side == Side.BUY and ba is not None and order.price >= ba:
                order.status = OrderStatus.REJECTED
                order.reject_reason = f"POST_ONLY_WOULD_CROSS_ASK (Price: {order.price} >= BestAsk: {ba})"
                logger.info(f"[REJECT ALO] {order.order_id}: {order.reject_reason}")
            elif order.side == Side.SELL and bb is not None and order.price <= bb:
                order.status = OrderStatus.REJECTED
                order.reject_reason = f"POST_ONLY_WOULD_CROSS_BID (Price: {order.price} <= BestBid: {bb})"
                logger.info(f"[REJECT ALO] {order.order_id}: {order.reject_reason}")
            else:
                # Order Accepted: Enters resting book queue
                # Track queue ahead at arrival
                q_ahead = book.get_depth_at_price(order.price, order.side)
                order.queue_ahead_size = q_ahead
                order.status = OrderStatus.RESTING
                self.resting_alo_orders.append(order)
                logger.info(
                    f"[RESTING ALO] {order.order_id} posted {order.side.value} @ {order.price:.4f}. "
                    f"Queue ahead: {q_ahead:.2f}"
                )

        self.db.insert_order(order)

    # --------------------------------------------------------------------------
    # TRADE TAPE INGESTION & QUEUE DYNAMICS FOR RESTING ALO ORDERS
    # --------------------------------------------------------------------------

    def on_trade_tick(
        self,
        symbol: str,
        trade_price: float,
        trade_size: float,
        taker_side: Union[Side, str],
        trade_ts: float,
    ) -> None:
        """
        Processes trade tick against resting ALO orders:
          1. Prints through our price -> Immediate full fill.
          2. Prints at our price -> Depletes queue ahead; fills excess volume.
        """
        sym = symbol.upper()
        t_side = Side(taker_side.upper()) if isinstance(taker_side, str) else taker_side

        active_resting: List[ShadowOrder] = []
        for order in self.resting_alo_orders:
            if order.symbol != sym or order.status not in (OrderStatus.RESTING, OrderStatus.PARTIALLY_FILLED):
                if order.status in (OrderStatus.RESTING, OrderStatus.PARTIALLY_FILLED):
                    active_resting.append(order)
                continue

            filled_this_trade = 0.0

            # Condition 1: BUY Resting ALO Order
            if order.side == Side.BUY:
                if trade_price < order.price:
                    # Trade printed THROUGH our BUY price -> Immediate full fill!
                    filled_this_trade = order.remaining_size
                    logger.info(
                        f"[ALO FILL THROUGH] {order.order_id}: Trade {trade_price} printed through BUY {order.price}"
                    )
                elif math.isclose(trade_price, order.price, rel_tol=1e-7) and t_side == Side.SELL:
                    # Trade printed AT our price with matching counter-side taker
                    if trade_size <= order.queue_ahead_size:
                        order.queue_ahead_size -= trade_size
                    else:
                        fillable_vol = trade_size - order.queue_ahead_size
                        order.queue_ahead_size = 0.0
                        filled_this_trade = min(order.remaining_size, fillable_vol)
                        logger.info(
                            f"[ALO FILL QUEUE] {order.order_id}: Queue depleted, filled {filled_this_trade:.2f} @ {order.price}"
                        )

            # Condition 2: SELL Resting ALO Order
            elif order.side == Side.SELL:
                if trade_price > order.price:
                    # Trade printed THROUGH our SELL price -> Immediate full fill!
                    filled_this_trade = order.remaining_size
                    logger.info(
                        f"[ALO FILL THROUGH] {order.order_id}: Trade {trade_price} printed through SELL {order.price}"
                    )
                elif math.isclose(trade_price, order.price, rel_tol=1e-7) and t_side == Side.BUY:
                    # Trade printed AT our price with matching counter-side taker
                    if trade_size <= order.queue_ahead_size:
                        order.queue_ahead_size -= trade_size
                    else:
                        fillable_vol = trade_size - order.queue_ahead_size
                        order.queue_ahead_size = 0.0
                        filled_this_trade = min(order.remaining_size, fillable_vol)
                        logger.info(
                            f"[ALO FILL QUEUE] {order.order_id}: Queue depleted, filled {filled_this_trade:.2f} @ {order.price}"
                        )

            if filled_this_trade > 1e-9:
                self._register_fill(
                    order=order,
                    fill_qty=filled_this_trade,
                    fill_price=order.price,
                    current_ts=trade_ts,
                    role="MAKER",
                )
                order.remaining_size -= filled_this_trade
                if order.remaining_size <= 1e-9:
                    order.status = OrderStatus.FILLED
                else:
                    order.status = OrderStatus.PARTIALLY_FILLED
                    active_resting.append(order)
            else:
                active_resting.append(order)

            self.db.insert_order(order)

        self.resting_alo_orders = active_resting

    # --------------------------------------------------------------------------
    # FILL REGISTRATION & MARKOUT SCHEDULING
    # --------------------------------------------------------------------------

    def _register_fill(
        self,
        order: ShadowOrder,
        fill_qty: float,
        fill_price: float,
        current_ts: float,
        role: str,
    ) -> ShadowFill:
        """Records fill, calculates fee, and schedules markout telemetry."""
        fill_id = f"fill_{uuid.uuid4().hex[:8]}"

        fee_rate = (self.taker_fee_bps if role == "TAKER" else self.maker_rebate_bps) / 10_000.0
        fee_usd = fill_qty * fill_price * fee_rate

        fill = ShadowFill(
            fill_id=fill_id,
            order_id=order.order_id,
            symbol=order.symbol,
            venue=order.venue,
            side=order.side,
            fill_time=current_ts,
            fill_price=fill_price,
            fill_size=fill_qty,
            liquidity_role=role,
            queue_ahead_at_entry=order.queue_ahead_size,
            fee_usd=fee_usd,
        )

        order.fills.append(fill)
        self.fills.append(fill)
        self.db.insert_fill(fill)

        # Schedule Markouts (+1s, +5s, +30s, +5m, +1h, and resolution)
        for label, offset in MARKOUT_HORIZONS.items():
            sched_ts = (current_ts + offset) if offset is not None else float("inf")
            m = ShadowMarkout(
                fill_id=fill_id,
                order_id=order.order_id,
                symbol=order.symbol,
                horizon_label=label,
                scheduled_ts=sched_ts,
                fill_price=fill_price,
                is_final=(label == "resolution"),
            )
            self.pending_markouts.append(m)

        return fill

    # --------------------------------------------------------------------------
    # MARKOUT TELEMETRY EVALUATOR
    # --------------------------------------------------------------------------

    def check_and_record_markouts(self, current_ts: float, terminal_resolution: bool = False) -> None:
        """
        Evaluates pending markout targets against current orderbook mid-price.
        """
        remaining_markouts: List[ShadowMarkout] = []
        for m in self.pending_markouts:
            book = self.get_or_create_book(m.symbol)
            mid = book.mid_price() or m.fill_price

            is_due = (current_ts >= m.scheduled_ts) or (terminal_resolution and m.is_final)
            if is_due:
                order = self.orders.get(m.order_id)
                side = order.side if order else Side.BUY

                # Basis point markout formula:
                # BUY:  (Mid - Fill) / Fill * 10,000 bps
                # SELL: (Fill - Mid) / Fill * 10,000 bps
                if m.fill_price > 0:
                    if side == Side.BUY:
                        pnl_bps = ((mid - m.fill_price) / m.fill_price) * 10_000.0
                        pnl_usd = (mid - m.fill_price) * (order.size if order else 1.0)
                    else:
                        pnl_bps = ((m.fill_price - mid) / m.fill_price) * 10_000.0
                        pnl_usd = (m.fill_price - mid) * (order.size if order else 1.0)
                else:
                    pnl_bps = 0.0
                    pnl_usd = 0.0

                m.recorded_ts = current_ts
                m.markout_mid_price = mid
                m.markout_pnl_bps = round(pnl_bps, 2)
                m.markout_pnl_usd = round(pnl_usd, 4)
                self.db.record_markout(m)
                logger.debug(
                    f"[MARKOUT {m.horizon_label}] Fill {m.fill_id} ({m.symbol}): {pnl_bps:+.1f} bps (Mid: {mid:.4f})"
                )
            else:
                remaining_markouts.append(m)

        self.pending_markouts = remaining_markouts

    # --------------------------------------------------------------------------
    # ADVANCING TIME TICK (HISTORICAL REPLAY OR SIMULATION STEP)
    # --------------------------------------------------------------------------

    def advance_time(self, current_ts: float) -> None:
        """
        Steps virtual or live clock forward to current_ts.
        Evaluates orders arriving at t0 + dt_latency and checks markouts.
        """
        # 1. Process in-flight orders that have arrived
        still_in_flight: List[ShadowOrder] = []
        for order in self.pending_in_flight:
            if current_ts >= order.arrival_ts:
                self.evaluate_order_arrival(order, current_ts)
            else:
                still_in_flight.append(order)
        self.pending_in_flight = still_in_flight

        # 2. Check and record markouts
        self.check_and_record_markouts(current_ts)

    # --------------------------------------------------------------------------
    # HISTORICAL PARQUET / DUCKDB REPLAY RUNNER
    # --------------------------------------------------------------------------

    def replay_parquet(
        self,
        parquet_path: str,
        orders_schedule: Optional[List[Dict[str, Any]]] = None,
        max_records: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Replays recorded market data from a Parquet file through the shadow broker.
        Supports standard schema:
          (venue, event_type, local_mono_ns, exchange_ts, price, size, side, best_bid, best_ask)
        """
        import pyarrow.parquet as pq

        path = Path(parquet_path)
        if not path.exists():
            raise FileNotFoundError(f"Replay file not found: {parquet_path}")

        logger.info(f"[REPLAY] Beginning replay of {path.name}...")
        table = pq.read_table(str(path))
        num_rows = table.num_rows if max_records is None else min(max_records, table.num_rows)

        venues = table.column("venue").to_pylist()[:num_rows]
        event_types = table.column("event_type").to_pylist()[:num_rows]
        exchange_ts = table.column("exchange_ts").to_pylist()[:num_rows]
        prices = table.column("price").to_pylist()[:num_rows]
        sizes = table.column("size").to_pylist()[:num_rows]
        sides = table.column("side").to_pylist()[:num_rows]
        best_bids = table.column("best_bid").to_pylist()[:num_rows]
        best_asks = table.column("best_ask").to_pylist()[:num_rows]

        # Scheduled orders sorted by trigger timestamp
        scheduled_orders = list(orders_schedule or [])
        scheduled_orders.sort(key=lambda x: x.get("submit_ts", 0))
        next_ord_idx = 0

        start_time_sec = exchange_ts[0] / 1000.0 if exchange_ts[0] > 1e11 else exchange_ts[0]

        for i in range(num_rows):
            raw_ts = exchange_ts[i]
            cur_sec = (raw_ts / 1000.0) if raw_ts > 1e11 else float(raw_ts)
            ev_type = event_types[i]
            ven = venues[i]

            # 1. Update book state
            book = self.get_or_create_book("BTC")
            bb = best_bids[i]
            ba = best_asks[i]
            if bb > 0 and ba > 0:
                book.set_level(bb, 10.0, Side.BUY, ts=cur_sec)
                book.set_level(ba, 10.0, Side.SELL, ts=cur_sec)

            # 2. Check scheduled order submissions
            while next_ord_idx < len(scheduled_orders):
                ord_spec = scheduled_orders[next_ord_idx]
                if cur_sec >= ord_spec.get("submit_ts", 0):
                    self.submit_order(
                        symbol=ord_spec.get("symbol", "BTC"),
                        side=ord_spec["side"],
                        order_type=ord_spec["order_type"],
                        price=ord_spec["price"],
                        size=ord_spec["size"],
                        venue=ord_spec.get("venue", ven),
                        latency_ms=ord_spec.get("latency_ms"),
                        current_ts=cur_sec,
                    )
                    next_ord_idx += 1
                else:
                    break

            # 3. Advance clock & evaluate in-flight arrivals
            self.advance_time(cur_sec)

            # 4. If trade event, trigger trade tape matching for resting orders
            if ev_type in ("trade", "trades") and prices[i] > 0 and sizes[i] > 0:
                t_side = Side.BUY if sides[i] in ("buy", "BUY") else Side.SELL
                self.on_trade_tick(
                    symbol="BTC",
                    trade_price=prices[i],
                    trade_size=sizes[i],
                    taker_side=t_side,
                    trade_ts=cur_sec,
                )

        # Finalize replay: resolve terminal markouts
        end_time_sec = exchange_ts[-1] / 1000.0 if exchange_ts[-1] > 1e11 else exchange_ts[-1]
        self.check_and_record_markouts(end_time_sec, terminal_resolution=True)

        logger.info(
            f"[REPLAY COMPLETE] Processed {num_rows} records over {(end_time_sec - start_time_sec):.1f}s. "
            f"Orders: {len(self.orders)}, Fills: {len(self.fills)}"
        )

        return {
            "records_processed": num_rows,
            "total_orders": len(self.orders),
            "total_fills": len(self.fills),
            "markouts": self.db.query_markouts(),
        }

    # --------------------------------------------------------------------------
    # LIVE SHADOW BROKER WORKER
    # --------------------------------------------------------------------------

    async def _live_worker_loop(self) -> None:
        """Continuous background tick advancement for live shadow mode."""
        while self.is_live:
            try:
                now = time.time()
                self.advance_time(now)
                await asyncio.sleep(0.010)  # 10ms evaluation tick
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[LIVE SHADOW WORKER ERROR] {e}", exc_info=True)
                await asyncio.sleep(0.050)

    async def start_live_mode(self) -> None:
        """Starts live execution clock worker."""
        if self.is_live:
            return
        self.is_live = True
        logger.info("[+] Starting Realistic Shadow Broker (Live Mode)...")
        self._live_worker_task = asyncio.create_task(self._live_worker_loop())

    async def stop_live_mode(self) -> None:
        """Stops live execution clock worker."""
        if not self.is_live:
            return
        self.is_live = False
        logger.info("[-] Stopping Realistic Shadow Broker (Live Mode)...")
        if self._live_worker_task and not self._live_worker_task.done():
            self._live_worker_task.cancel()
        self.check_and_record_markouts(time.time(), terminal_resolution=True)
