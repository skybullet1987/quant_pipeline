#!/usr/bin/env python3
"""
Experiment S8: Pyth Lazer / Hermes CI_Ratio & Pull-Oracle Lag Monitor (exp_s8_pyth_ci_arb.py)
===========================================================================================
Cross-Venue Quantitative Alpha Experiment S8:
Exploits Pyth pull-oracle confidence interval (CI) dilation on pull-oracle DEXs
(ApeX Omni, Drift, Vertex) hedged against tight HyperCore L1 order books.

Microstructure Mechanics:
  1. Pyth Confidence Interval Tracking:
     - CI_Ratio = conf / price
     - Baseline regime: CI_Ratio < 0.0005 (5 bps).
  2. Volatility Dislocation Trigger:
     - When a sudden move widens CI_Ratio > 0.0040 (40 bps) on Pyth
       while Hyperliquid L1 top-of-book spread remains tight (< 3 bps):
       - Simulates quoting maker orders on the CI-penalized DEX at P_Pyth +/- (k * CI).
       - Instantly delta-hedges fills on Hyperliquid L1 at tight book mid.
  3. Mean-Reversion Exit:
     - Holds delta-neutral inventory until confidence interval collapses to CI_Ratio < 0.0005 (5 bps),
       locking in the widened oracle spread.
  4. Hard Safety Kill-Switch:
     - Abort and cancel all orders if:
         a) conf / price > 0.03 (3% outlier print / corrupted feed), OR
         b) now - publish_time > 5.0s (stale oracle feed / network disconnect).
"""

from __future__ import annotations

import logging
import math
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from experiments.core.shadow_broker import (
    L2Book,
    OrderType,
    RealisticShadowBroker,
    ShadowOrder,
    Side,
)

logger = logging.getLogger("ExpS8PythArb")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("[%(asctime)s UTC] [%(levelname)s] [S8-PYTH-ARB] %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


# ==============================================================================
# 1. PYTH ORACLE & DEX BOOK DATA CONTRACTS
# ==============================================================================

@dataclass
class PythPriceUpdate:
    symbol: str
    price: float
    conf: float
    publish_time: float  # Unix timestamp in seconds
    feed_id: str = "pyth_feed"

    @property
    def ci_ratio(self) -> float:
        """CI_Ratio = conf / price."""
        return self.conf / self.price if self.price > 0 else 0.0

    @property
    def ci_bps(self) -> float:
        return self.ci_ratio * 10_000.0

    def age_seconds(self, current_ts: float) -> float:
        return max(0.0, current_ts - self.publish_time)

    def is_outlier(self, max_ci_ratio: float = 0.03) -> bool:
        """Kill-switch check 1: >3% outlier print."""
        return self.ci_ratio >= max_ci_ratio

    def is_stale(self, current_ts: float, max_age_sec: float = 5.0) -> bool:
        """Kill-switch check 2: >5s age."""
        return self.age_seconds(current_ts) >= max_age_sec


@dataclass
class DEXBookSummary:
    venue: str
    symbol: str
    best_bid: float
    best_ask: float
    timestamp: float

    @property
    def mid(self) -> float:
        return (self.best_bid + self.best_ask) / 2.0 if self.best_bid > 0 and self.best_ask > 0 else 0.0

    @property
    def spread_bps(self) -> float:
        if self.mid <= 0:
            return 999.0
        return ((self.best_ask - self.best_bid) / self.mid) * 10_000.0


@dataclass
class S8Config:
    ci_trigger_bps: float = 40.0         # 40 bps (0.0040)
    ci_exit_bps: float = 5.0             # 5 bps (0.0005)
    hl_max_spread_bps: float = 3.0       # < 3 bps on Hyperliquid
    k_ci_band: float = 1.0               # P_pyth +/- k * CI
    max_ci_ratio_kill_switch: float = 0.03  # 3% outlier print
    max_oracle_age_sec: float = 5.0      # 5.0 seconds staleness


# Backward-compatible alias
PythCIArbConfig = S8Config


# ==============================================================================
# 2. POSITION & ARBITRAGE LIFECYCLE
# ==============================================================================

class PositionState(str, Enum):
    ARMED = "ARMED"
    HEDGED = "HEDGED"
    CLOSED_PROFIT = "CLOSED_PROFIT"
    KILLED_SAFETY = "KILLED_SAFETY"


@dataclass
class PythCIArbPosition:
    position_id: str
    symbol: str
    dex_venue: str
    entry_ts: float
    dex_side: Side
    dex_price: float
    dex_size: float
    hl_hedge_side: Side
    hl_hedge_price: float
    hl_hedge_size: float
    entry_ci_bps: float
    exit_ts: Optional[float] = None
    exit_dex_price: Optional[float] = None
    exit_hl_price: Optional[float] = None
    realized_pnl_usd: float = 0.0
    state: PositionState = PositionState.ARMED
    kill_reason: Optional[str] = None


# ==============================================================================
# 3. EXP-S8 ARBITRAGE ENGINE
# ==============================================================================

class ExpS8PythCIArbEngine:
    """
    Engine implementing Experiment S8:
      - Tracks Pyth Hermes/Lazer feeds and multi-venue L1 books.
      - Monitors CI_Ratio and HL spread.
      - Enforces 3% outlier and 5s staleness safety kill-switches.
      - Simulates CI-penalized maker quote and instant HL delta hedge.
      - Unwinds position when CI_Ratio collapses < 5 bps.
    """

    def __init__(
        self,
        config: Optional[S8Config] = None,
        shadow_broker: Optional[RealisticShadowBroker] = None,
    ):
        self.config = config or S8Config()
        self.shadow_broker = shadow_broker or RealisticShadowBroker(default_latency_ms=50.0)

        # Active state: symbol -> PythPriceUpdate
        self.pyth_feeds: Dict[str, PythPriceUpdate] = {}
        # Multi-venue books: (venue, symbol) -> DEXBookSummary
        self.dex_books: Dict[Tuple[str, str], DEXBookSummary] = {}

        # Active hedged positions
        self.active_positions: Dict[str, PythCIArbPosition] = {}
        self.completed_positions: List[PythCIArbPosition] = []

    def update_pyth_feed(self, update: PythPriceUpdate) -> None:
        self.pyth_feeds[update.symbol.upper()] = update

    def update_dex_book(
        self,
        venue: str,
        symbol: str,
        best_bid: float,
        best_ask: float,
        timestamp: float,
    ) -> DEXBookSummary:
        sym = symbol.upper()
        ven = venue.lower()
        summary = DEXBookSummary(
            venue=ven,
            symbol=sym,
            best_bid=best_bid,
            best_ask=best_ask,
            timestamp=timestamp,
        )
        self.dex_books[(ven, sym)] = summary
        return summary

    def evaluate_opportunity(
        self,
        symbol: str,
        dex_venue: str,
        current_ts: float,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Evaluates whether Pyth CI_Ratio and Hyperliquid book spread qualify for arbitrage.
        """
        sym = symbol.upper()
        dex_ven = dex_venue.lower()

        pyth = self.pyth_feeds.get(sym)
        if not pyth:
            return False, "NO_PYTH_FEED", {}

        # Check Kill-Switch 1: Outlier print (>3% CI ratio)
        if pyth.is_outlier(self.config.max_ci_ratio_kill_switch):
            logger.warning(
                f"[!] S8 KILL-SWITCH: {sym} Pyth CI_Ratio={pyth.ci_bps:.1f} bps > 300 bps (Outlier print). Aborting."
            )
            self._abort_symbol_positions(sym, "OUTLIER_CI_RATIO_ABORT")
            return False, "KILLED_OUTLIER_CI", {"ci_ratio": pyth.ci_ratio}

        # Check Kill-Switch 2: Stale feed (>5s age)
        age = pyth.age_seconds(current_ts)
        if pyth.is_stale(current_ts, self.config.max_oracle_age_sec):
            logger.warning(
                f"[!] S8 KILL-SWITCH: {sym} Pyth Feed is stale (Age={age:.2f}s > 5.0s). Aborting."
            )
            self._abort_symbol_positions(sym, "STALE_ORACLE_ABORT")
            return False, "KILLED_STALE_ORACLE", {"age_sec": age}

        hl_book = self.dex_books.get(("hyperliquid", sym))
        if not hl_book:
            return False, "NO_HYPERLIQUID_BOOK", {}

        # Check Condition 1: CI_Ratio > 40 bps
        cond_ci_spike = pyth.ci_bps >= self.config.ci_trigger_bps
        # Check Condition 2: Hyperliquid spread < 3 bps
        cond_hl_tight = hl_book.spread_bps <= self.config.hl_max_spread_bps

        telemetry = {
            "symbol": sym,
            "dex_venue": dex_ven,
            "pyth_price": pyth.price,
            "pyth_conf": pyth.conf,
            "ci_bps": round(pyth.ci_bps, 2),
            "ci_spike_pass": cond_ci_spike,
            "hl_spread_bps": round(hl_book.spread_bps, 2),
            "hl_tight_pass": cond_hl_tight,
            "oracle_age_sec": round(age, 3),
        }

        if cond_ci_spike and cond_hl_tight:
            return True, "ARM_CI_ARB", telemetry

        return False, "CRITERIA_NOT_MET", telemetry

    def execute_ci_dislocation_arb(
        self,
        symbol: str,
        dex_venue: str,
        trade_size: float,
        current_ts: float,
    ) -> Optional[PythCIArbPosition]:
        """
        Executes maker order on CI-penalized DEX and instant delta-hedge on Hyperliquid.
        """
        is_opp, reason, telem = self.evaluate_opportunity(symbol, dex_venue, current_ts)
        if not is_opp:
            return None

        sym = symbol.upper()
        pyth = self.pyth_feeds[sym]
        hl_book = self.dex_books[("hyperliquid", sym)]

        # CI Maker quote prices on target DEX: P_pyth +/- k * CI
        band = self.config.k_ci_band * pyth.conf
        bid_quote = pyth.price - band
        ask_quote = pyth.price + band

        # Assume bid maker order fills (buying cheap on CI DEX)
        dex_fill_px = bid_quote
        dex_side = Side.BUY

        # Instant delta hedge on Hyperliquid: SELL at HL best bid
        hl_hedge_side = Side.SELL
        hl_fill_px = hl_book.best_bid

        pos_id = f"s8_{sym}_{int(current_ts)}"
        pos = PythCIArbPosition(
            position_id=pos_id,
            symbol=sym,
            dex_venue=dex_venue.lower(),
            entry_ts=current_ts,
            dex_side=dex_side,
            dex_price=dex_fill_px,
            dex_size=trade_size,
            hl_hedge_side=hl_hedge_side,
            hl_hedge_price=hl_fill_px,
            hl_hedge_size=trade_size,
            entry_ci_bps=pyth.ci_bps,
            state=PositionState.HEDGED,
        )

        # Place shadow hedge order on Hyperliquid
        self.shadow_broker.submit_order(
            symbol=sym,
            side=hl_hedge_side,
            order_type=OrderType.TAKER_IOC,
            price=hl_fill_px,
            size=trade_size,
            venue="hyperliquid",
            current_ts=current_ts,
        )

        self.active_positions[pos_id] = pos
        logger.info(
            f"[+] S8 HEDGED ENTRY: Pos={pos_id} Symbol={sym} DEX={dex_venue} "
            f"DEX_Buy={dex_fill_px:.2f} HL_HedgeSell={hl_fill_px:.2f} "
            f"EntryCI={pyth.ci_bps:.1f}bps SpreadCaptured=${(hl_fill_px - dex_fill_px):.2f}"
        )
        return pos

    def check_position_exit(
        self,
        position_id: str,
        current_ts: float,
    ) -> bool:
        """
        Unwinds position when Pyth CI_Ratio collapses < 5 bps (mean-reversion complete).
        """
        pos = self.active_positions.get(position_id)
        if not pos or pos.state != PositionState.HEDGED:
            return False

        pyth = self.pyth_feeds.get(pos.symbol)
        hl_book = self.dex_books.get(("hyperliquid", pos.symbol))
        if not pyth or not hl_book:
            return False

        # Check safety kill-switch during holding period
        if pyth.is_outlier() or pyth.is_stale(current_ts):
            pos.state = PositionState.KILLED_SAFETY
            pos.kill_reason = "Safety kill-switch tripped during position hold."
            self.completed_positions.append(pos)
            del self.active_positions[position_id]
            logger.warning(f"[!] S8 Position {position_id} killed: {pos.kill_reason}")
            return False

        # Exit condition: CI_Ratio collapses < 5 bps
        if pyth.ci_bps <= self.config.ci_exit_bps:
            # Unwind DEX position at current Pyth mid and HL hedge at current HL mid
            pos.exit_ts = current_ts
            pos.exit_dex_price = pyth.price
            pos.exit_hl_price = hl_book.mid

            # Realized PnL:
            # DEX PnL: (exit_dex - entry_dex) * size (since we bought DEX)
            # HL PnL:  (entry_hl - exit_hl) * size  (since we sold HL hedge)
            dex_pnl = (pos.exit_dex_price - pos.dex_price) * pos.dex_size
            hl_pnl = (pos.hl_hedge_price - pos.exit_hl_price) * pos.hl_hedge_size
            pos.realized_pnl_usd = dex_pnl + hl_pnl
            pos.state = PositionState.CLOSED_PROFIT

            logger.info(
                f"[+] S8 POSITION CLOSED: Pos={pos.position_id} Symbol={pos.symbol} "
                f"ExitCI={pyth.ci_bps:.1f}bps RealizedPnL=${pos.realized_pnl_usd:.2f} "
                f"(DEX=${dex_pnl:.2f}, HL=${hl_pnl:.2f})"
            )
            self.completed_positions.append(pos)
            del self.active_positions[position_id]
            return True

        return False

    def _abort_symbol_positions(self, symbol: str, reason: str) -> None:
        """Kills any open positions for symbol when safety trip occurs."""
        for pid in list(self.active_positions.keys()):
            pos = self.active_positions[pid]
            if pos.symbol == symbol:
                pos.state = PositionState.KILLED_SAFETY
                pos.kill_reason = reason
                self.completed_positions.append(pos)
                del self.active_positions[pid]


# ==============================================================================
# 4. DEMO & SELF-TEST EXECUTION
# ==============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=== Cross-Venue Experiment S8: Pyth CI_Ratio & Pull-Oracle Lag Monitor ===")

    engine = ExpS8PythCIArbEngine()
    t0 = time.time()

    # 1. Setup Pyth Feed with 50 bps CI spike (conf = 50 on price = 10,000)
    update = PythPriceUpdate(
        symbol="ETH",
        price=3000.0,
        conf=15.0,  # 15 / 3000 = 0.0050 = 50 bps > 40 bps
        publish_time=t0,
    )
    engine.update_pyth_feed(update)

    # 2. Hyperliquid book remains ultra-tight (1.0 bps spread)
    engine.update_dex_book(
        venue="hyperliquid",
        symbol="ETH",
        best_bid=3000.0,
        best_ask=3000.30,  # 0.30 / 3000 = 1.0 bps < 3.0 bps
        timestamp=t0,
    )

    # 3. Evaluate & execute dislocation arb
    pos = engine.execute_ci_dislocation_arb(
        symbol="ETH",
        dex_venue="apex_omni",
        trade_size=10.0,
        current_ts=t0,
    )
    print(f"[S8 Entry] Position: {pos.position_id if pos else None} | State: {pos.state.value if pos else None}")

    # 4. CI collapses back to 4 bps (conf = 1.2 on price = 3000.0)
    collapsed_update = PythPriceUpdate(
        symbol="ETH",
        price=3000.0,
        conf=1.2,  # 1.2 / 3000 = 0.0004 = 4 bps < 5 bps exit
        publish_time=t0 + 2.0,
    )
    engine.update_pyth_feed(collapsed_update)
    closed = engine.check_position_exit(pos.position_id, current_ts=t0 + 2.0)
    print(f"[S8 Exit] Position Closed: {closed} | Realized PnL: ${pos.realized_pnl_usd:.2f}")
