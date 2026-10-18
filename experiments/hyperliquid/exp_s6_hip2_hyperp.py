#!/usr/bin/env python3
"""
Experiment S6: HIP-2 Geometric Grid Exhaustion & Hyperp 8h EMA Squeeze (exp_s6_hip2_hyperp.py)
============================================================================================
Hyperliquid L1 Microstructure Experiment S6:
Exploits two structural mechanisms unique to Hyperliquid:

1. HIP-2 Geometric Grid Exhaustion (Spot AMM):
   - HIP-1 spot pairs launch with a deterministic 0.3% geometric ask grid:
       P_k = P_0 * (1.003)^(k - 1)   for k = 1 ... N_total
   - Cumulative USDC cost to buy through level K:
       Cost(K) = S_level * P_0 * ((1.003^K - 1) / 0.003)
   - Trigger Breakout:
       Trigger shadow breakout buy when >80% of N_seeded levels are absorbed within 15 minutes
       AND external ask depth above N_seeded is < 0.2 x baseline.
   - Trailing Stop:
       Trails 0.9% (3 HIP-2 ticks: 1.003^3 ~ 1.009027) below the 3-second auto-stepping HIP-2 bid.

2. Hyperp 8h EMA Squeeze (Pre-Launch Perps):
   - Pre-launch Hyperps (pre-TGE tokens) price against an 8-hour exponential decay oracle:
       P_oracle^hyperp(t) = min[ sum_{i=0}^{1439} P_mark^padded(t - i) * e^{-i/480} * ((1 - e^{-1/480}) / (1 - e^{-3})), 4 * P_mark^init ]
   - Pre-TGE Squeeze Traps:
       Unbacked pre-launch perps trade at extreme speculative premiums (>1.8x oracle).
       NEVER short naked prior to TGE spot opening (arbitrage is mechanically impossible).
   - Trigger Short Entry:
       When Hyperp price > 1.8x P_oracle^hyperp AND a CEX spot listing (Binance/OKX/Bybit) opens,
       initiating the post-TGE basis collapse.
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
    OrderType,
    RealisticShadowBroker,
    ShadowOrder,
    Side,
)

logger = logging.getLogger("ExpS6Hip2Hyperp")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("[%(asctime)s UTC] [%(levelname)s] [S6-HIP2-HYPERP] %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


# ==============================================================================
# 1. HIP-2 GEOMETRIC GRID MATHEMATICS
# ==============================================================================

@dataclass
class HIP2GenesisParams:
    """
    HIP-2 Spot Genesis Parameters:
      - p0: Genesis base price ($)
      - n_total: Total grid levels (e.g. 300)
      - s_level: Fixed token size per level (base units)
      - n_seeded: Number of initial seeded ask levels (e.g. 50 or 100)
      - baseline_external_depth: Expected resting depth above n_seeded ($)
      - tick_ratio: Multiplier per rung, exactly 1.003 (0.3% geometric step)
    """
    symbol: str
    p0: float
    n_total: int = 300
    s_level: float = 100_000.0
    n_seeded: int = 50
    baseline_external_depth: float = 50_000.0
    tick_ratio: float = 1.003  # 0.3%

    def price_at_level(self, k: int) -> float:
        """P_k = P_0 * (1.003)^(k - 1) for k >= 1."""
        if k < 1:
            return self.p0
        return self.p0 * (self.tick_ratio ** (k - 1))

    def cumulative_cost(self, k: int) -> float:
        """
        Exact closed-form cumulative USDC cost to absorb levels 1 through K:
          Cost(K) = S_level * P_0 * ((1.003^K - 1) / 0.003)
        """
        if k <= 0:
            return 0.0
        geom_sum = (self.tick_ratio ** k - 1.0) / (self.tick_ratio - 1.0)
        return self.s_level * self.p0 * geom_sum

    def level_for_price(self, price: float) -> int:
        """Returns the grid level index k for a given market price."""
        if price <= self.p0:
            return 1
        # P = P0 * (1.003)^(k - 1) => k = 1 + ln(P / P0) / ln(1.003)
        k = 1.0 + (math.log(price / self.p0) / math.log(self.tick_ratio))
        # Add epsilon to guard against IEEE 754 log precision loss (e.g. 49.99999999999999 -> 50)
        return max(1, min(self.n_total, int(math.floor(k + 1e-9))))

    def level_for_cumulative_usd(self, usd_spent: float) -> int:
        """Returns highest grid level absorbed by a given cumulative USDC spend."""
        if usd_spent <= 0:
            return 0
        # usd = S_level * P0 * ((1.003^K - 1) / 0.003)
        # 1.003^K = 1 + (usd * 0.003) / (S_level * P0)
        numerator = usd_spent * (self.tick_ratio - 1.0)
        denominator = self.s_level * self.p0
        term = 1.0 + (numerator / denominator)
        if term <= 0:
            return 0
        k = math.log(term) / math.log(self.tick_ratio)
        return max(0, min(self.n_total, int(math.floor(k + 1e-9))))


class HIP2SpotTracker:
    """
    Monitors HIP-2 spot trading, grid exhaustion, external orderbook resistance,
    and 3-second auto-stepping bid trailing stop.
    """

    def __init__(self, params: HIP2GenesisParams):
        self.params = params
        self.current_level: int = 1
        self.cumulative_usdc_bought: float = 0.0
        self.first_buy_ts: Optional[float] = None
        self.last_buy_ts: Optional[float] = None

        # 3-second auto-stepping bid tracking
        self.auto_stepping_bid: float = params.p0
        self.last_bid_step_ts: float = 0.0

        # Breakout state
        self.breakout_triggered: bool = False
        self.breakout_entry_price: float = 0.0
        self.breakout_entry_ts: float = 0.0
        self.trailing_stop_price: float = 0.0

    def on_buy_trade(self, trade_price: float, trade_size: float, current_ts: float) -> None:
        """Processes a buy trade consuming the ask grid."""
        if self.first_buy_ts is None:
            self.first_buy_ts = current_ts
        self.last_buy_ts = current_ts

        usdc_value = trade_price * trade_size
        self.cumulative_usdc_bought += usdc_value

        # Calculate new absorbed level from price or cumulative spend
        level_by_px = self.params.level_for_price(trade_price)
        level_by_cost = self.params.level_for_cumulative_usd(self.cumulative_usdc_bought)
        self.current_level = max(self.current_level, level_by_px, level_by_cost)

        # Update auto-stepping bid if 3.0s elapsed
        if current_ts - self.last_bid_step_ts >= 3.0:
            # HIP-2 AMM auto-steps bid 1 level behind current market price
            target_bid_level = max(1, self.current_level - 1)
            self.auto_stepping_bid = self.params.price_at_level(target_bid_level)
            self.last_bid_step_ts = current_ts

            # Trailing stop is 0.9% (3 HIP-2 ticks: 1.003^3) below the auto-stepping bid
            # 1.003^3 = 1.009027027 => Stop = Bid / (1.003^3) ~ Bid * 0.99105
            stop_ratio = self.params.tick_ratio ** 3
            self.trailing_stop_price = self.auto_stepping_bid / stop_ratio

    def evaluate_breakout_signal(
        self,
        external_ask_depth_above_seeded: float,
        current_ts: float,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Evaluates HIP-2 Breakout Entry Invariants:
          1. >80% of N_seeded levels absorbed within 15 minutes (900s).
          2. External ask depth above N_seeded is < 0.2 x baseline (thin orderbook).
        """
        elapsed_sec = (current_ts - self.first_buy_ts) if self.first_buy_ts else 0.0
        seeded_absorption_pct = self.current_level / self.params.n_seeded

        # Invariant 1: >80% absorbed within 15 mins
        cond_absorption = seeded_absorption_pct >= 0.80 and elapsed_sec <= 900.0

        # Invariant 2: External ask depth < 0.2 x baseline
        depth_ratio = (
            external_ask_depth_above_seeded / self.params.baseline_external_depth
            if self.params.baseline_external_depth > 0
            else 1.0
        )
        cond_thin_book = depth_ratio < 0.20

        is_breakout = cond_absorption and cond_thin_book and not self.breakout_triggered

        telemetry = {
            "symbol": self.params.symbol,
            "current_level": self.current_level,
            "n_seeded": self.params.n_seeded,
            "seeded_absorption_pct": round(seeded_absorption_pct * 100.0, 2),
            "elapsed_sec": round(elapsed_sec, 1),
            "cond_absorption_pass": cond_absorption,
            "external_depth_above_seeded": external_ask_depth_above_seeded,
            "baseline_depth": self.params.baseline_external_depth,
            "depth_ratio": round(depth_ratio, 3),
            "cond_thin_book_pass": cond_thin_book,
            "auto_stepping_bid": round(self.auto_stepping_bid, 4),
            "trailing_stop_price": round(self.trailing_stop_price, 4),
            "is_breakout": is_breakout,
        }

        if is_breakout:
            self.breakout_triggered = True
            self.breakout_entry_price = self.params.price_at_level(self.current_level)
            self.breakout_entry_ts = current_ts
            logger.info(
                f"[+] HIP-2 BREAKOUT TRIGGERED: Symbol={self.params.symbol} Level={self.current_level}/{self.params.n_seeded} "
                f"({seeded_absorption_pct*100:.1f}%) Elapsed={elapsed_sec:.1f}s DepthRatio={depth_ratio:.2f} "
                f"EntryPx={self.breakout_entry_price:.4f} TrailingStop={self.trailing_stop_price:.4f}"
            )

        return is_breakout, telemetry


# ==============================================================================
# 2. HYPERP 8H EMA ORACLE & PRE-LAUNCH SQUEEZE MATHEMATICS
# ==============================================================================

class Hyperp8hEMATracker:
    """
    Maintains a rolling 1,440-minute mark-price buffer for pre-launch Hyperps
    and computes the exact 8-hour exponential decay oracle price:

      P_oracle^hyperp(t) = min[ sum_{i=0}^{1439} P_mark^padded(t - i) * e^{-i/480} * ((1 - e^{-1/480}) / (1 - e^{-3})), 4 * P_mark^init ]
    """

    def __init__(self, symbol: str, p_mark_init: float):
        self.symbol = symbol.upper()
        self.p_mark_init = float(p_mark_init)
        self.minute_marks: List[float] = []
        self.max_buffer_len: int = 1440  # 1,440 minutes = 24 hours

        # Precompute discrete exponential weights for i = 0 ... 1439 with tau = 480 min (8 hours)
        self.weights: List[float] = []
        tau = 480.0
        norm_factor = (1.0 - math.exp(-1.0 / tau)) / (1.0 - math.exp(-3.0))  # e^(-1440/480) = e^(-3)
        for i in range(self.max_buffer_len):
            w = math.exp(-i / tau) * norm_factor
            self.weights.append(w)

        # Normalize weights so sum is identically 1.0
        w_sum = sum(self.weights)
        if w_sum > 0:
            self.weights = [w / w_sum for w in self.weights]

    def add_minute_mark(self, mark_price: float) -> None:
        """Appends a new minute mark price to rolling buffer."""
        self.minute_marks.append(float(mark_price))
        if len(self.minute_marks) > self.max_buffer_len:
            self.minute_marks.pop(0)

    def compute_hyperp_oracle(self) -> float:
        """
        Computes exact Hyperp 8-hour exponential decay oracle price.
        If buffer has fewer than 1,440 entries, pads missing historical minutes with the oldest mark.
        """
        if not self.minute_marks:
            return self.p_mark_init

        # Pad buffer to 1,440 entries
        n_avail = len(self.minute_marks)
        # Reversed so index 0 is t (most recent), index 1 is t - 1, etc.
        recent_first = list(reversed(self.minute_marks))
        oldest_price = recent_first[-1]

        oracle_sum = 0.0
        for i in range(self.max_buffer_len):
            px = recent_first[i] if i < n_avail else oldest_price
            oracle_sum += px * self.weights[i]

        # 4x genesis mark cap invariant
        hard_cap = 4.0 * self.p_mark_init
        return min(oracle_sum, hard_cap)

    def evaluate_short_signal(
        self,
        current_hyperp_price: float,
        cex_spot_listing_active: bool,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Evaluates Short Signal Invariants:
          1. Hyperp trades > 1.8x its 8h EMA oracle (speculative overvaluation).
          2. CEX spot listing (Binance/OKX/Bybit) MUST BE OPEN.
          3. Absolute rule: NEVER short naked prior to TGE spot opening.
        """
        oracle_px = self.compute_hyperp_oracle()
        premium_ratio = current_hyperp_price / oracle_px if oracle_px > 0 else 1.0

        is_inflated = premium_ratio >= 1.80

        telemetry = {
            "symbol": self.symbol,
            "current_price": current_hyperp_price,
            "oracle_8h_ema": round(oracle_px, 4),
            "premium_ratio": round(premium_ratio, 3),
            "is_inflated": is_inflated,
            "cex_spot_listing_active": cex_spot_listing_active,
            "p_mark_init": self.p_mark_init,
            "hard_cap_4x": round(4.0 * self.p_mark_init, 4),
        }

        # Rule 1: Not inflated enough
        if not is_inflated:
            return False, "HYPERP_PREMIUM_UNDER_1.8X", telemetry

        # Rule 2: Naked short gate prior to TGE spot opening
        if not cex_spot_listing_active:
            telemetry["gate_blocked"] = "NEVER_SHORT_NAKED_PRIOR_TO_TGE_SPOT"
            logger.warning(
                f"[!] HYPERP SHORT BLOCKED: Symbol={self.symbol} Premium={premium_ratio:.2f}x > 1.8x, "
                f"BUT CEX spot listing is NOT yet open. Shorting naked prior to TGE is prohibited."
            )
            return False, "BLOCKED_NO_CEX_SPOT_OPEN", telemetry

        # Both conditions satisfied: basis collapse short signal armed
        logger.info(
            f"[+] HYPERP POST-TGE SHORT SIGNAL ARMED: Symbol={self.symbol} Price={current_hyperp_price:.4f} "
            f"Oracle={oracle_px:.4f} Premium={premium_ratio:.2f}x CEXSpot=OPEN"
        )
        return True, "ARM_POST_TGE_SHORT", telemetry


# ==============================================================================
# 3. UNIFIED S6 EXPERIMENT RUNNER
# ==============================================================================

class ExpS6Runner:
    """
    Unified controller managing both HIP-2 Spot Grid Exhaustion and Hyperp 8h EMA Squeeze.
    """

    def __init__(self, shadow_broker: Optional[RealisticShadowBroker] = None):
        self.shadow_broker = shadow_broker or RealisticShadowBroker(default_latency_ms=50.0)
        self.hip2_trackers: Dict[str, HIP2SpotTracker] = {}
        self.hyperp_trackers: Dict[str, Hyperp8hEMATracker] = {}

    def register_hip2_pair(self, params: HIP2GenesisParams) -> HIP2SpotTracker:
        tracker = HIP2SpotTracker(params)
        self.hip2_trackers[params.symbol.upper()] = tracker
        return tracker

    def register_hyperp(self, symbol: str, p_mark_init: float) -> Hyperp8hEMATracker:
        tracker = Hyperp8hEMATracker(symbol.upper(), p_mark_init)
        self.hyperp_trackers[symbol.upper()] = tracker
        return tracker

    def simulate_hip2_breakout(
        self,
        symbol: str,
        n_levels_to_absorb: int,
        duration_sec: float,
        external_depth_ratio: float = 0.10,
    ) -> Tuple[bool, Dict[str, Any], Optional[ShadowOrder]]:
        """
        Simulates an aggressive buy wave absorbing n_levels_to_absorb of the HIP-2 grid.
        Submits shadow buy order and arms trailing stop if breakout conditions met.
        """
        sym = symbol.upper()
        tracker = self.hip2_trackers[sym]
        t0 = 1_000_000.0

        # Simulate trades advancing grid levels
        for k in range(1, n_levels_to_absorb + 1):
            px = tracker.params.price_at_level(k)
            t = t0 + (duration_sec * (k / n_levels_to_absorb))
            tracker.on_buy_trade(trade_price=px, trade_size=tracker.params.s_level, current_ts=t)

        ext_depth = tracker.params.baseline_external_depth * external_depth_ratio
        is_breakout, telemetry = tracker.evaluate_breakout_signal(
            external_ask_depth_above_seeded=ext_depth,
            current_ts=t0 + duration_sec,
        )

        shadow_order: Optional[ShadowOrder] = None
        if is_breakout:
            entry_px = tracker.params.price_at_level(tracker.current_level)
            shadow_order = self.shadow_broker.submit_order(
                symbol=sym,
                side=Side.BUY,
                order_type=OrderType.TAKER_IOC,
                price=entry_px * 1.003,  # 1 tick slippage allowance
                size=tracker.params.s_level,
                venue="hyperliquid",
                current_ts=t0 + duration_sec,
            )

        return is_breakout, telemetry, shadow_order

    def simulate_hyperp_squeeze(
        self,
        symbol: str,
        minutes_history: List[float],
        current_hyperp_price: float,
        cex_spot_open: bool,
    ) -> Tuple[bool, str, Dict[str, Any], Optional[ShadowOrder]]:
        """
        Simulates Hyperp 8h EMA oracle computation and short evaluation.
        Submits shadow short order if signal is valid.
        """
        sym = symbol.upper()
        tracker = self.hyperp_trackers[sym]

        for px in minutes_history:
            tracker.add_minute_mark(px)

        is_short, reason, telemetry = tracker.evaluate_short_signal(
            current_hyperp_price=current_hyperp_price,
            cex_spot_listing_active=cex_spot_open,
        )

        shadow_order: Optional[ShadowOrder] = None
        if is_short:
            shadow_order = self.shadow_broker.submit_order(
                symbol=sym,
                side=Side.SELL,
                order_type=OrderType.TAKER_IOC,
                price=current_hyperp_price * 0.995,  # 0.5% crossing tolerance
                size=10_000.0,
                venue="hyperliquid",
                current_ts=time.time(),
            )

        return is_short, reason, telemetry, shadow_order


# ==============================================================================
# 4. DEMO & SELF-TEST EXECUTION
# ==============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=== Hyperliquid Experiment S6: HIP-2 Grid & Hyperp 8h EMA ===")

    runner = ExpS6Runner()

    # 1. Test HIP-2 Spot Grid Exhaustion
    params = HIP2GenesisParams(
        symbol="PURR",
        p0=0.10,
        n_total=300,
        s_level=100_000.0,
        n_seeded=50,
        baseline_external_depth=50_000.0,
    )
    runner.register_hip2_pair(params)

    cost_50 = params.cumulative_cost(50)
    print(f"[HIP-2] Cost to absorb 50 seeded levels: ${cost_50:,.2f} USDC")

    # Simulate absorbing 42 levels (84% of 50 seeded) in 10 minutes (600s)
    is_brk, telem, ord_brk = runner.simulate_hip2_breakout(
        symbol="PURR",
        n_levels_to_absorb=42,
        duration_sec=600.0,
        external_depth_ratio=0.12,  # 12% < 20%
    )
    print(f"[HIP-2 Breakout] Triggered: {is_brk} | Level: {telem['current_level']} | TrailingStop: ${telem['trailing_stop_price']:.4f}")

    # 2. Test Hyperp 8h EMA Squeeze
    runner.register_hyperp(symbol="W", p_mark_init=1.0)

    # 1,440 minutes of baseline around $1.00
    history = [1.0 + 0.05 * math.sin(i / 100.0) for i in range(1440)]

    # Test 1: High premium ($2.10 vs ~$1.00 oracle) BUT CEX spot NOT open => MUST BLOCK
    is_short1, reason1, telem1, _ = runner.simulate_hyperp_squeeze(
        symbol="W",
        minutes_history=history,
        current_hyperp_price=2.10,
        cex_spot_open=False,
    )
    print(f"[Hyperp Test 1 - Pre-TGE] Signal: {is_short1} | Reason: {reason1} | Oracle: ${telem1['oracle_8h_ema']:.4f}")

    # Test 2: High premium ($2.10) AND CEX spot OPENS => MUST ARM SHORT
    is_short2, reason2, telem2, ord_short = runner.simulate_hyperp_squeeze(
        symbol="W",
        minutes_history=[],
        current_hyperp_price=2.10,
        cex_spot_open=True,
    )
    print(f"[Hyperp Test 2 - Post-TGE] Signal: {is_short2} | Reason: {reason2} | ShortOrder: {ord_short.order_id if ord_short else None}")
