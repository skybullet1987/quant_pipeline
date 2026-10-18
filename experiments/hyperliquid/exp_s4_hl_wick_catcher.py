#!/usr/bin/env python3
"""
Experiment S4: Stage-1 30s Partial-Liquidation Cooldown Wick Catcher (exp_s4_hl_wick_catcher.py)
=============================================================================================
Hyperliquid L1 Microstructure Experiment S4:
Exploits HyperCore's deterministic two-stage liquidation engine:
  - Stage 1: Position > $100k breaching 1.0 x MMR prints a 20% partial liquidation market order at T0.
  - 30-Second Cooldown: HyperCore pauses for exactly 30.0 seconds before liquidating remaining 80%.
  - Vault Takeover Boundary: If position equity breaches 2/3 x MMR (~0.667 x MMR), the HLP Liquidator Vault
    takes over the position off-book at liquidation price (no public CLOB impact).
  - Cooldown Verification: If P_mark (median of P1, P2, P3) stays between 2/3 x MMR and 1.0 x MMR
    (no whale margin top-up, vault blocked), the remaining 80% forced market dump MUST hit the CLOB at T0 + 30.0s.
  - Execution: At T0 + 29.0s, project L2 book clearing price and place a geometric ALO maker ladder
    across the bottom 30% of the projected wick (5%–18% beyond P_mark).
  - Macro Vol Kill-Switch: Cancel ladder if Binance/OKX 5s realized volatility spikes.
  - Post-Fill: Instant 50% delta-hedge on Binance/Bybit perps and reduce-only take-profit at P_mark.
"""

from __future__ import annotations

import asyncio
import logging
import math
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from experiments.core.hl_mark_replicator import HyperCoreMarkPriceReplicator
from experiments.core.shadow_broker import (
    L2Book,
    OrderType,
    RealisticShadowBroker,
    ShadowOrder,
    Side,
)

logger = logging.getLogger("ExpS4WickCatcher")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("[%(asctime)s UTC] [%(levelname)s] [S4-WICK-CATCHER] %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


# ==============================================================================
# 1. MATHEMATICAL FORMULAS & INVARIANTS
# ==============================================================================

def calculate_exact_liq_price(
    price: float,
    side: int,
    margin_available: float,
    position_size: float,
    mmr: float,
) -> float:
    """
    Computes exact liquidation price on Hyperliquid L1:
        liq_price = price - (side * margin_available / position_size) / (1 - mmr * side)

    Parameters:
        price: Current mark price or entry price ($)
        side: +1 for Long, -1 for Short
        margin_available: Account equity or allocated margin for position ($)
        position_size: Absolute size in base units (|S| > 0)
        mmr: Maintenance Margin Requirement fraction (e.g. 0.04 for 4%)
    """
    if position_size <= 0:
        raise ValueError(f"position_size must be positive, got {position_size}")
    if math.isclose(1.0 - mmr * side, 0.0):
        return 0.0

    denom = 1.0 - mmr * side
    numerator = side * margin_available / position_size
    return price - (numerator / denom)


def calculate_equity_cushion_to_mmr(
    position_size: float,
    current_mark: float,
    account_equity: float,
    mmr: float,
) -> Tuple[float, float, float]:
    """
    Computes:
      1. Maintenance margin requirement (1.0 x MMR)
      2. HLP Vault takeover threshold (2/3 x MMR)
      3. Ratio of account equity to 1.0 x MMR requirement (equity / mmr_req)
    """
    notional = abs(position_size) * current_mark
    mmr_req = notional * mmr
    hlp_vault_req = mmr_req * (2.0 / 3.0)

    equity_ratio = account_equity / mmr_req if mmr_req > 0 else 1.0
    return mmr_req, hlp_vault_req, equity_ratio


# ==============================================================================
# 2. DATA STRUCTURES & CONFIGURATION
# ==============================================================================

class CooldownState(str, Enum):
    MONITORING = "MONITORING"
    VERIFIED_ACTIVE = "VERIFIED_ACTIVE"
    LADDER_ARMED = "LADDER_ARMED"
    FILLED_AND_HEDGED = "FILLED_AND_HEDGED"
    INVALIDATED_HLP_TAKEOVER = "INVALIDATED_HLP_TAKEOVER"
    INVALIDATED_TOP_UP = "INVALIDATED_TOP_UP"
    INVALIDATED_MACRO_VOL = "INVALIDATED_MACRO_VOL"
    INVALIDATED_INSUFFICIENT_WICK = "INVALIDATED_INSUFFICIENT_WICK"
    EXPIRED = "EXPIRED"


@dataclass
class WhalePosition:
    symbol: str
    wallet_address: str
    position_size: float  # Positive for Long, negative for Short
    entry_price: float
    margin_available: float
    mmr: float = 0.04  # Default 4% MMR
    last_update_ts: float = field(default_factory=time.monotonic)

    @property
    def side(self) -> int:
        return 1 if self.position_size >= 0 else -1

    @property
    def abs_size(self) -> float:
        return abs(self.position_size)

    @property
    def notional(self) -> float:
        return self.abs_size * self.entry_price

    def get_liq_price(self, current_price: Optional[float] = None) -> float:
        ref_px = current_price if current_price is not None else self.entry_price
        return calculate_exact_liq_price(
            price=ref_px,
            side=self.side,
            margin_available=self.margin_available,
            position_size=self.abs_size,
            mmr=self.mmr,
        )


@dataclass
class Stage1LiquidationEvent:
    event_id: str
    symbol: str
    wallet_address: str
    t0_timestamp: float
    whale_side: int  # +1 Long (liquidating via SELL), -1 Short (liquidating via BUY)
    initial_position_size: float
    partial_liq_size: float  # Exactly 20%
    remaining_dump_size: float  # Exactly 80%
    t0_price: float
    state: CooldownState = CooldownState.MONITORING
    invalidation_reason: Optional[str] = None

    # Ladder and fill telemetry
    projected_clearing_px: float = 0.0
    projected_wick_pct: float = 0.0
    ladder_order_ids: List[str] = field(default_factory=list)
    filled_size: float = 0.0
    avg_fill_px: float = 0.0
    hedged_size: float = 0.0
    hedge_px: float = 0.0
    take_profit_order_id: Optional[str] = None
    realized_pnl: float = 0.0


@dataclass
class S4Config:
    min_whale_notional: float = 100_000.0  # $100k minimum notional
    cooldown_seconds: float = 30.0  # HyperCore 30.0s cooldown
    verification_cutoff_sec: float = 28.5  # Monitor until T0 + 28.5s
    ladder_place_sec: float = 29.0  # Arm ladder at T0 + 29.0s
    execution_sec: float = 30.0  # Stage 2 dump at T0 + 30.0s

    min_wick_pct: float = 0.05  # At least 5% projected wick
    max_wick_pct: float = 0.18  # At most 18% projected wick
    wick_bottom_fraction: float = 0.30  # Bottom 30% of wick
    ladder_levels: int = 4  # Number of geometric ladder rungs

    delta_hedge_ratio: float = 0.50  # 50% instant delta hedge on CEX
    vol_spike_threshold_pct: float = 0.015  # 1.5% 5s return move on Binance/OKX kills setup
    vol_spike_annualized: float = 1.20  # 120% annualized 5s vol kills setup


# ==============================================================================
# 3. EXP-S4 WICK CATCHER ENGINE
# ==============================================================================

class ExpS4WickCatcher:
    """
    Autonomous engine implementing Experiment S4: Stage-1 30s Partial-Liquidation Cooldown.
    """

    def __init__(
        self,
        config: Optional[S4Config] = None,
        mark_replicator: Optional[HyperCoreMarkPriceReplicator] = None,
        shadow_broker: Optional[RealisticShadowBroker] = None,
    ):
        self.config = config or S4Config()
        self.mark_replicator = mark_replicator or HyperCoreMarkPriceReplicator(
            symbols=["BTC", "ETH", "SOL", "PURR", "AVAX"]
        )
        self.shadow_broker = shadow_broker or RealisticShadowBroker(default_latency_ms=50.0)

        # In-memory tracking
        self.whale_positions: Dict[str, WhalePosition] = {}  # wallet -> WhalePosition
        self.active_events: Dict[str, Stage1LiquidationEvent] = {}  # event_id -> Stage1LiquidationEvent
        self.completed_events: List[Stage1LiquidationEvent] = []

        # Local L2 order books: symbol -> L2Book
        self.order_books: Dict[str, L2Book] = {}

        # Recent CEX price buffer for 5-second realized vol calculation: symbol -> list of (ts, px)
        self.cex_price_history: Dict[str, List[Tuple[float, float]]] = {}

    # --------------------------------------------------------------------------
    # 1. WHALE TRACKING & STAGE-1 TRIGGER DETECTION
    # --------------------------------------------------------------------------

    def register_whale_position(
        self,
        symbol: str,
        wallet: str,
        size: float,
        entry_price: float,
        margin_available: float,
        mmr: float = 0.04,
    ) -> Optional[WhalePosition]:
        """Registers or updates a whale position. Returns position if notional >= $100k."""
        notional = abs(size) * entry_price
        if notional < self.config.min_whale_notional:
            return None

        pos = WhalePosition(
            symbol=symbol.upper(),
            wallet_address=wallet,
            position_size=size,
            entry_price=entry_price,
            margin_available=margin_available,
            mmr=mmr,
            last_update_ts=time.monotonic(),
        )
        self.whale_positions[wallet] = pos
        return pos

    def on_stage1_partial_liquidation(
        self,
        symbol: str,
        wallet: str,
        partial_size: float,
        price: float,
        timestamp: Optional[float] = None,
    ) -> Optional[Stage1LiquidationEvent]:
        """
        Invoked when HyperCore prints a Stage-1 20% partial liquidation market order on tape at T0.
        """
        t0 = timestamp if timestamp is not None else time.monotonic()
        pos = self.whale_positions.get(wallet)

        # Infer position context if not previously pre-registered
        if pos is None:
            # Stage 1 is exactly 20%, so initial total was 5.0 * partial_size
            total_size = partial_size * 5.0
            pos = WhalePosition(
                symbol=symbol.upper(),
                wallet_address=wallet,
                position_size=total_size,
                entry_price=price,
                margin_available=abs(total_size) * price * 0.038,  # Just below 4% MMR
                mmr=0.04,
                last_update_ts=t0,
            )
            self.whale_positions[wallet] = pos

        whale_notional = pos.abs_size * price
        if whale_notional < self.config.min_whale_notional:
            logger.debug(f"Stage 1 ignored for {wallet}: notional ${whale_notional:.2f} < ${self.config.min_whale_notional:.2f}")
            return None

        # Remaining dump size is strictly 80% of initial position
        remaining_size = pos.abs_size * 0.80

        event_id = f"s4_{symbol}_{wallet[:8]}_{int(t0)}"
        event = Stage1LiquidationEvent(
            event_id=event_id,
            symbol=symbol.upper(),
            wallet_address=wallet,
            t0_timestamp=t0,
            whale_side=pos.side,
            initial_position_size=pos.abs_size,
            partial_liq_size=pos.abs_size * 0.20,
            remaining_dump_size=remaining_size,
            t0_price=price,
            state=CooldownState.MONITORING,
        )

        self.active_events[event_id] = event
        logger.info(
            f"[+] STAGE-1 PARTIAL LIQUIDATION TRIGGERED: Event={event_id} Symbol={symbol} "
            f"WhaleSide={'LONG' if pos.side > 0 else 'SHORT'} RemainingDump={remaining_size:.4f} "
            f"T0={t0:.3f} RefPx={price:.4f}"
        )
        return event

    # --------------------------------------------------------------------------
    # 2. COOLDOWN VERIFICATION [T0, T0 + 28.5s]
    # --------------------------------------------------------------------------

    def verify_cooldown_invariants(
        self,
        event: Stage1LiquidationEvent,
        current_ts: Optional[float] = None,
    ) -> bool:
        """
        Verifies mathematical invariants during t in [T0, T0 + 28.5s]:
          1. Mark Price P_mark keeps position equity ABOVE 2/3 x MMR (~0.667 x MMR)
             => HLP Vault is blocked from off-book takeover.
          2. Position equity stays BELOW 1.0 x MMR (no whale margin top-up)
             => Liquidation condition remains active.
        """
        now = current_ts if current_ts is not None else time.monotonic()
        elapsed = now - event.t0_timestamp

        if event.state not in (CooldownState.MONITORING, CooldownState.VERIFIED_ACTIVE):
            return False

        # Get local replicated P_mark = median(P1, P2, P3)
        p_mark = self.mark_replicator.get_mark_price(event.symbol)
        if p_mark <= 0:
            p_mark = event.t0_price

        pos = self.whale_positions.get(event.wallet_address)
        if not pos:
            return False

        # Compute synthetic position equity under current P_mark
        # PnL = side * size * (P_mark - entry_px)
        pnl = pos.side * pos.abs_size * (p_mark - pos.entry_price)
        current_equity = pos.margin_available + pnl

        mmr_req, hlp_vault_req, equity_ratio = calculate_equity_cushion_to_mmr(
            position_size=pos.abs_size,
            current_mark=p_mark,
            account_equity=current_equity,
            mmr=pos.mmr,
        )

        # Check Invariant 1: Vault takeover boundary
        if current_equity <= hlp_vault_req:
            event.state = CooldownState.INVALIDATED_HLP_TAKEOVER
            event.invalidation_reason = (
                f"Equity ${current_equity:.2f} breached 2/3 x MMR threshold ${hlp_vault_req:.2f}. "
                f"HLP vault will absorb remaining position off-book."
            )
            logger.warning(f"[!] S4 INVALIDATED: {event.invalidation_reason}")
            return False

        # Check Invariant 2: Whale solvent or margin top-up
        if current_equity >= mmr_req:
            event.state = CooldownState.INVALIDATED_TOP_UP
            event.invalidation_reason = (
                f"Equity ${current_equity:.2f} recovered above 1.0 x MMR requirement ${mmr_req:.2f}. "
                f"Position is solvent; Stage 2 cancelled."
            )
            logger.warning(f"[!] S4 INVALIDATED: {event.invalidation_reason}")
            return False

        if elapsed >= self.config.verification_cutoff_sec:
            event.state = CooldownState.VERIFIED_ACTIVE

        return True

    # --------------------------------------------------------------------------
    # 3. L2 BOOK DEPTH WALK & GEOMETRIC LADDER PLACEMENT AT T0 + 29.0s
    # --------------------------------------------------------------------------

    def simulate_book_depth_impact(
        self,
        symbol: str,
        dump_size: float,
        whale_side: int,
    ) -> Tuple[float, float]:
        """
        Simulates HyperCore CLOB walk for remaining 80% forced market order:
          - If whale was Long, market SELL sweeps bids down.
          - If whale was Short, market BUY sweeps asks up.
        Returns:
          (clearing_price, projected_wick_percentage)
        """
        book = self.order_books.get(symbol.upper())
        p_mark = self.mark_replicator.get_mark_price(symbol)
        if p_mark <= 0 and book:
            p_mark = book.mid_price() or 1.0

        if not book or not book.bids or not book.asks:
            # Fallback synthetic depth estimation if book empty
            synthetic_wick = 0.08  # 8% baseline wick
            clearing_px = p_mark * (1.0 - synthetic_wick) if whale_side > 0 else p_mark * (1.0 + synthetic_wick)
            return clearing_px, synthetic_wick

        # Handle Dict[float, float] or List[Tuple[float, float]]
        if isinstance(book.bids, dict):
            sorted_bids = sorted(book.bids.items(), key=lambda x: x[0], reverse=True)
        else:
            sorted_bids = list(book.bids)

        if isinstance(book.asks, dict):
            sorted_asks = sorted(book.asks.items(), key=lambda x: x[0], reverse=False)
        else:
            sorted_asks = list(book.asks)

        remaining = dump_size
        clearing_px = p_mark

        if whale_side > 0:
            # Whale Long -> Market Sell dumps into Bids
            for px, sz in sorted_bids:
                if remaining <= sz:
                    clearing_px = px
                    remaining = 0.0
                    break
                remaining -= sz
                clearing_px = px

            # If entire book swept, extrapolate beyond lowest bid
            if remaining > 0 and sorted_bids:
                clearing_px = sorted_bids[-1][0] * 0.85

            wick_pct = max(0.0, (p_mark - clearing_px) / p_mark)
        else:
            # Whale Short -> Market Buy sweeps into Asks
            for px, sz in sorted_asks:
                if remaining <= sz:
                    clearing_px = px
                    remaining = 0.0
                    break
                remaining -= sz
                clearing_px = px

            if remaining > 0 and sorted_asks:
                clearing_px = sorted_asks[-1][0] * 1.15

            wick_pct = max(0.0, (clearing_px - p_mark) / p_mark)

        return clearing_px, wick_pct

    def generate_geometric_ladder(
        self,
        symbol: str,
        whale_side: int,
        p_mark: float,
        clearing_px: float,
        total_ladder_size: float,
    ) -> List[Tuple[float, float]]:
        """
        Generates a geometric shadow ladder of post-only maker (ALO) orders across
        the bottom 30% of the projected wick (clamped between 5% and 18% beyond P_mark).

        Returns list of (limit_price, order_size) tuples.
        """
        levels = self.config.ladder_levels
        wick_fraction = self.config.wick_bottom_fraction

        ladder: List[Tuple[float, float]] = []

        if whale_side > 0:
            # Downward wick: we want to BUY maker orders at the bottom of the dump
            # Wick span: from clearing_px to p_mark
            # Bottom 30% is [clearing_px, clearing_px + 0.30 * (p_mark - clearing_px)]
            band_low = clearing_px
            band_high = clearing_px + wick_fraction * (p_mark - clearing_px)

            # Clamp between 5% and 18% below p_mark
            hard_max_px = p_mark * (1.0 - self.config.min_wick_pct)
            hard_min_px = p_mark * (1.0 - self.config.max_wick_pct)

            band_low = max(hard_min_px, min(band_low, hard_max_px))
            band_high = max(band_low, min(band_high, hard_max_px))

            # Geometric spacing across band
            if levels <= 1 or math.isclose(band_low, band_high):
                return [(band_low, total_ladder_size)]

            ratio = (band_high / band_low) ** (1.0 / (levels - 1))
            size_per_level = total_ladder_size / levels

            for k in range(levels):
                px = band_low * (ratio ** k)
                ladder.append((round(px, 4), round(size_per_level, 4)))

        else:
            # Upward wick: we want to SELL maker orders at the top of the dump
            band_high = clearing_px
            band_low = clearing_px - wick_fraction * (clearing_px - p_mark)

            hard_min_px = p_mark * (1.0 + self.config.min_wick_pct)
            hard_max_px = p_mark * (1.0 + self.config.max_wick_pct)

            band_low = max(hard_min_px, min(band_low, hard_max_px))
            band_high = max(band_low, min(band_high, hard_max_px))

            if levels <= 1 or math.isclose(band_low, band_high):
                return [(band_high, total_ladder_size)]

            ratio = (band_high / band_low) ** (1.0 / (levels - 1))
            size_per_level = total_ladder_size / levels

            for k in range(levels):
                px = band_low * (ratio ** k)
                ladder.append((round(px, 4), round(size_per_level, 4)))

        return ladder

    def arm_shadow_ladder_at_t29(
        self,
        event: Stage1LiquidationEvent,
        current_ts: Optional[float] = None,
    ) -> bool:
        """
        At T0 + 29.0s, computes clearing depth and places geometric maker ALO orders.
        """
        now = current_ts if current_ts is not None else time.monotonic()
        if not self.verify_cooldown_invariants(event, now):
            return False

        p_mark = self.mark_replicator.get_mark_price(event.symbol)
        clearing_px, wick_pct = self.simulate_book_depth_impact(
            symbol=event.symbol,
            dump_size=event.remaining_dump_size,
            whale_side=event.whale_side,
        )

        event.projected_clearing_px = clearing_px
        event.projected_wick_pct = wick_pct

        if wick_pct < self.config.min_wick_pct:
            event.state = CooldownState.INVALIDATED_INSUFFICIENT_WICK
            event.invalidation_reason = (
                f"Projected wick {wick_pct*100:.2f}% is below minimum {self.config.min_wick_pct*100:.1f}% threshold."
            )
            logger.info(f"[i] S4 Setup skipped: {event.invalidation_reason}")
            return False

        # Check macro volatility kill switch before submission
        if self.check_macro_vol_kill_switch(event.symbol, now):
            event.state = CooldownState.INVALIDATED_MACRO_VOL
            event.invalidation_reason = "External Binance/OKX 5s realized volatility spiked."
            logger.warning(f"[!] S4 KILL-SWITCH ACTIVATED: {event.invalidation_reason}")
            return False

        # Place geometric ALO ladder orders
        # Whale Long liquidation => we BUY maker ALO
        # Whale Short liquidation => we SELL maker ALO
        ladder_side = Side.BUY if event.whale_side > 0 else Side.SELL
        ladder = self.generate_geometric_ladder(
            symbol=event.symbol,
            whale_side=event.whale_side,
            p_mark=p_mark,
            clearing_px=clearing_px,
            total_ladder_size=event.remaining_dump_size * 0.40,  # Catch up to 40% of the dump
        )

        event.ladder_order_ids.clear()
        for px, sz in ladder:
            order = self.shadow_broker.submit_order(
                symbol=event.symbol,
                side=ladder_side,
                order_type=OrderType.MAKER_ALO,
                price=px,
                size=sz,
                venue="hyperliquid",
                current_ts=now,
            )
            event.ladder_order_ids.append(order.order_id)

        event.state = CooldownState.LADDER_ARMED
        logger.info(
            f"[+] S4 LADDER ARMED: Event={event.event_id} Symbol={event.symbol} Side={ladder_side.value} "
            f"ProjectedWick={wick_pct*100:.2f}% Rungs={len(ladder)} Orders={event.ladder_order_ids}"
        )
        return True

    # --------------------------------------------------------------------------
    # 4. KILL-SWITCH & REALIZED VOLATILITY CHECK
    # --------------------------------------------------------------------------

    def record_cex_price(self, symbol: str, price: float, timestamp: float) -> None:
        """Records external Binance/OKX tick for rolling 5s volatility tracking."""
        sym = symbol.upper()
        if sym not in self.cex_price_history:
            self.cex_price_history[sym] = []
        buf = self.cex_price_history[sym]
        buf.append((timestamp, price))

        # Retain only trailing 15 seconds
        cutoff = timestamp - 15.0
        while buf and buf[0][0] < cutoff:
            buf.pop(0)

    def check_macro_vol_kill_switch(self, symbol: str, current_ts: float) -> bool:
        """
        Computes 5-second realized return variance on Binance/OKX.
        Returns True if realized volatility or price deviation exceeds threshold.
        """
        buf = self.cex_price_history.get(symbol.upper(), [])
        if len(buf) < 3:
            return False

        # Filter points within trailing 5.0 seconds
        window = [p for ts, p in buf if current_ts - 5.0 <= ts <= current_ts]
        if len(window) < 2:
            return False

        # 1. Total 5-second percentage excursion
        p_start, p_end = window[0], window[-1]
        pct_change = abs(p_end - p_start) / p_start if p_start > 0 else 0.0
        if pct_change >= self.config.vol_spike_threshold_pct:
            return True

        # 2. Log-return realized volatility
        log_rets = [math.log(window[i] / window[i - 1]) for i in range(1, len(window)) if window[i - 1] > 0]
        if not log_rets:
            return False

        mean_ret = sum(log_rets) / len(log_rets)
        var = sum((r - mean_ret) ** 2 for r in log_rets) / len(log_rets)
        # Annualized vol assuming ~0.5s ticks
        annualized_vol = math.sqrt(var * 2.0 * 365 * 24 * 3600)
        return annualized_vol >= self.config.vol_spike_annualized

    # --------------------------------------------------------------------------
    # 5. EXECUTION AT T0 + 30.0s & INSTANT DELTA HEDGING
    # --------------------------------------------------------------------------

    def execute_stage2_fill_and_hedge(
        self,
        event: Stage1LiquidationEvent,
        execution_price: Optional[float] = None,
        current_ts: Optional[float] = None,
    ) -> bool:
        """
        Executes Stage-2 forced liquidation dump at T0 + 30.0s:
          1. Fills armed ladder orders.
          2. Simulates 50% instant delta-hedge on Binance/Bybit perps.
          3. Places reduce-only take-profit order at P_mark.
        """
        now = current_ts if current_ts is not None else time.monotonic()
        if event.state != CooldownState.LADDER_ARMED:
            return False

        # Final kill switch check
        if self.check_macro_vol_kill_switch(event.symbol, now):
            event.state = CooldownState.INVALIDATED_MACRO_VOL
            event.invalidation_reason = "Macro vol spike tripped kill switch at execution second."
            for oid in event.ladder_order_ids:
                self.shadow_broker.cancel_order(oid)
            return False

        fill_px = execution_price or event.projected_clearing_px
        total_filled = 0.0
        cost_sum = 0.0

        for oid in event.ladder_order_ids:
            order = self.shadow_broker.orders.get(oid)
            if order:
                from experiments.core.shadow_broker import OrderStatus
                # Force fill at limit or print-through execution price
                order.status = OrderStatus.FILLED
                order.remaining_size = 0.0
                exec_px = min(order.price, fill_px) if order.side == Side.BUY else max(order.price, fill_px)
                total_filled += order.size
                cost_sum += order.size * exec_px

        if total_filled <= 0:
            event.state = CooldownState.EXPIRED
            return False

        avg_fill = cost_sum / total_filled
        event.filled_size = total_filled
        event.avg_fill_px = avg_fill

        # 50% instant delta-hedge on Binance/Bybit
        # If we bought (ladder_side=BUY), hedge by SELLING on CEX
        hedge_side = Side.SELL if event.whale_side > 0 else Side.BUY
        hedge_size = total_filled * self.config.delta_hedge_ratio
        event.hedged_size = hedge_size
        event.hedge_px = fill_px  # CEX perp market price

        # Reduce-only take-profit order on HyperCore at P_mark
        p_mark = self.mark_replicator.get_mark_price(event.symbol) or event.t0_price
        tp_side = Side.SELL if event.whale_side > 0 else Side.BUY
        tp_order = self.shadow_broker.submit_order(
            symbol=event.symbol,
            side=tp_side,
            order_type=OrderType.MAKER_ALO,
            price=p_mark,
            size=total_filled,
            venue="hyperliquid",
            current_ts=now,
        )
        event.take_profit_order_id = tp_order.order_id

        # Theoretical mean reversion profit
        gross_reversion_spread = abs(p_mark - avg_fill)
        event.realized_pnl = total_filled * gross_reversion_spread

        event.state = CooldownState.FILLED_AND_HEDGED
        logger.info(
            f"[+] S4 FILLED & HEDGED: Event={event.event_id} Symbol={event.symbol} "
            f"FilledSize={total_filled:.4f} AvgFillPx={avg_fill:.4f} "
            f"Hedged={hedge_size:.4f} @ {event.hedge_px:.4f} TP_Target={p_mark:.4f} "
            f"ProjectedProfit=${event.realized_pnl:.2f}"
        )
        self.completed_events.append(event)
        return True

    # --------------------------------------------------------------------------
    # 6. STEP-BY-STEP SIMULATION RUNNER (FOR BACKTESTS & VALIDATION)
    # --------------------------------------------------------------------------

    def simulate_lifecycle_event(
        self,
        symbol: str,
        wallet: str,
        position_size: float,
        entry_price: float,
        margin_available: float,
        book: L2Book,
        cex_vol_spike: bool = False,
    ) -> Stage1LiquidationEvent:
        """
        Runs a complete synchronous simulation of the 30.0s lifecycle:
          T0: Stage 1 20% partial liquidation
          T0 + 20s: Invariant verification check
          T0 + 29s: Book depth walk & ladder arming
          T0 + 30s: Stage 2 dump execution, CEX delta-hedge, reduce-only TP
        """
        t0 = 1_000_000.0  # Normalized virtual epoch
        self.order_books[symbol.upper()] = book

        # 1. Register whale & trigger Stage 1
        self.register_whale_position(
            symbol=symbol,
            wallet=wallet,
            size=position_size,
            entry_price=entry_price,
            margin_available=margin_available,
        )
        # Update mark replicator anchor
        self.mark_replicator.update_hl_book(symbol, book.best_bid() or entry_price, book.best_ask() or entry_price, timestamp_mono=t0)
        self.mark_replicator.update_hl_oracle(symbol, entry_price, timestamp_mono=t0)
        for ven in ("binance", "okx", "bybit"):
            self.mark_replicator.update_cex_mid(symbol, ven, entry_price, timestamp_mono=t0)

        # Record CEX price history
        self.record_cex_price(symbol, entry_price, t0 - 4.0)
        self.record_cex_price(symbol, entry_price, t0 - 2.0)
        if cex_vol_spike:
            # Simulate a 3.0% sudden crash on Binance/OKX
            self.record_cex_price(symbol, entry_price * 0.97, t0 + 28.8)
        else:
            self.record_cex_price(symbol, entry_price * 0.999, t0 + 28.8)

        event = self.on_stage1_partial_liquidation(
            symbol=symbol,
            wallet=wallet,
            partial_size=abs(position_size) * 0.20,
            price=entry_price,
            timestamp=t0,
        )
        assert event is not None, "Failed to initialize Stage 1 event"

        # 2. Advance to T0 + 20.0s: check verification
        self.verify_cooldown_invariants(event, current_ts=t0 + 20.0)

        # 3. Advance to T0 + 29.0s: arm ladder
        self.arm_shadow_ladder_at_t29(event, current_ts=t0 + 29.0)

        # 4. Advance to T0 + 30.0s: execute dump & delta-hedge
        if event.state == CooldownState.LADDER_ARMED:
            clearing_px, _ = self.simulate_book_depth_impact(symbol, event.remaining_dump_size, event.whale_side)
            self.execute_stage2_fill_and_hedge(event, execution_price=clearing_px, current_ts=t0 + 30.0)

        return event


# ==============================================================================
# 4. CLI / DEMO ENTRYPOINT
# ==============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=== Hyperliquid Experiment S4: Stage-1 Cooldown Wick Catcher ===")

    # Initialize synthetic book
    book = L2Book(symbol="SOL")
    mid = 100.0
    for i in range(1, 30):
        # Thin bid book to create deep wick
        book.set_level(mid - i * 0.5, 20.0, Side.BUY)
        book.set_level(mid + i * 0.5, 200.0, Side.SELL)

    catcher = ExpS4WickCatcher()
    event = catcher.simulate_lifecycle_event(
        symbol="SOL",
        wallet="0xWhale111111111111111111111111111111111111",
        position_size=2000.0,  # $200,000 notional long
        entry_price=100.0,
        margin_available=7900.0,  # ~3.95% MMR
        book=book,
        cex_vol_spike=False,
    )

    print(f"Simulation Status: {event.state.value}")
    print(f"Wick %: {event.projected_wick_pct*100:.2f}% | Clearing: ${event.projected_clearing_px:.2f}")
    print(f"Filled: {event.filled_size:.2f} @ ${event.avg_fill_px:.2f} | Realized PnL: ${event.realized_pnl:.2f}")
