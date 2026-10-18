#!/usr/bin/env python3
"""
Experiment S7: Whales Market 4-Hour TGE Escrow Squeeze Tracker (exp_s7_whales_tge_squeeze.py)
===========================================================================================
Cross-Venue Quantitative Alpha Experiment S7:
Exploits physical delivery constraints and rational default boundaries in pre-market OTC escrows
(Whales Market) during the 4-hour post-TGE Settle Phase (T_settle_start to T_settle_start + 240m).

Game-Theoretic Payoff & Default Mechanics:
  1. OTC Buyer Payoff (Capped Forward):
       Payoff_OTC(S_T) = min(S_T - K, K)
     Why?
       - If seller delivers: Net profit/loss = K - S_T.
       - If seller defaults: Forfeits 100% collateral = -K.
       - Rational Default Condition: -K > K - S_T  =>  S_T > 2K.
       - Sellers will rationally default above S_T > 2K rather than market-buy tokens.

  2. Forced Delivery Zone (0.3K < S_t < 1.85K):
       - Inside this zone, defaulting is strictly worse than delivering (or sellers face reputational loss).
       - Undelivered sellers MUST scramble to market-buy spot tokens on DEXs/Hyperliquid before the 240m timer expires.
       - At S_t > 1.85K, sellers approach the 2K default tipping point, so buying dries up.

  3. Minute 150 Squeeze Trigger:
       At T_settle_start + 150m (90 minutes before deadline):
       - Trigger shadow long Spot/Perp trade if:
           a) >40% of matched escrow volume remains undelivered, AND
           b) Live spot S_t sits inside the Forced Delivery Zone (0.3K < S_t < 1.85K).

  4. Exits & Hard Safety Kill-Switch:
       - Hard Flat Exit: Minute 238 (T_settle_start + 238m, 2 minutes before cutoff).
       - Kill-Switch: Immediate abort if S_t > 1.85K (rational default wave).
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

logger = logging.getLogger("ExpS7WhalesSqueeze")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("[%(asctime)s UTC] [%(levelname)s] [S7-WHALES-SQUEEZE] %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


# ==============================================================================
# 1. WHALES MARKET ESCROW CONTRACT & PAYOFF MODEL
# ==============================================================================

@dataclass
class WhalesMarketEscrowContract:
    symbol: str
    strike_k: float  # Pre-market matched strike price ($)
    total_volume_matched: float  # Total tokens matched in escrow
    delivered_volume: float  # Tokens physically delivered so far
    t_settle_start: float  # Timestamp when TGE settlement phase began
    settle_duration_min: float = 240.0  # 4-hour settlement window

    @property
    def undelivered_volume(self) -> float:
        return max(0.0, self.total_volume_matched - self.delivered_volume)

    @property
    def undelivered_ratio(self) -> float:
        return self.undelivered_volume / self.total_volume_matched if self.total_volume_matched > 0 else 0.0

    def elapsed_minutes(self, current_ts: float) -> float:
        return max(0.0, (current_ts - self.t_settle_start) / 60.0)

    def buyer_payoff(self, s_t: float) -> float:
        """
        Buyer payoff = min(S_T - K, K).
        Sellers rationally default when S_T > 2K.
        """
        return min(s_t - self.strike_k, self.strike_k)

    def is_forced_delivery_zone(self, s_t: float) -> bool:
        """Forced Delivery Zone: 0.3K < S_t < 1.85K."""
        return (0.30 * self.strike_k) < s_t < (1.85 * self.strike_k)

    def is_default_zone(self, s_t: float) -> bool:
        """Default Zone: S_t >= 1.85K (approaching 2K tipping point)."""
        return s_t >= (1.85 * self.strike_k)


# ==============================================================================
# 2. SQUEEZE POSITION DATA STRUCTURE
# ==============================================================================

class SqueezeState(str, Enum):
    IDLE = "IDLE"
    LONG_ACTIVE = "LONG_ACTIVE"
    EXITED_M238 = "EXITED_M238"
    KILLED_DEFAULT_SPIKE = "KILLED_DEFAULT_SPIKE"
    KILLED_OUT_OF_BOUNDS = "KILLED_OUT_OF_BOUNDS"


@dataclass
class S7SqueezePosition:
    position_id: str
    symbol: str
    entry_ts: float
    entry_minute: float
    entry_price: float
    size: float
    state: SqueezeState = SqueezeState.LONG_ACTIVE
    exit_ts: Optional[float] = None
    exit_minute: Optional[float] = None
    exit_price: Optional[float] = None
    realized_pnl_usd: float = 0.0
    exit_reason: Optional[str] = None
    order_id: Optional[str] = None


# ==============================================================================
# 3. EXP-S7 SQUEEZE ENGINE
# ==============================================================================

class ExpS7WhalesTGESqueezeEngine:
    """
    Engine implementing Experiment S7:
      - Tracks Whales Market 4-hour settlement window.
      - At Minute 150, triggers long squeeze trade if undelivered > 40% and 0.3K < S_t < 1.85K.
      - Executes hard flat exit at Minute 238.
      - Enforces immediate kill-switch if S_t > 1.85K (rational default).
    """

    def __init__(self, shadow_broker: Optional[RealisticShadowBroker] = None):
        self.shadow_broker = shadow_broker or RealisticShadowBroker(default_latency_ms=50.0)
        self.escrows: Dict[str, WhalesMarketEscrowContract] = {}
        self.active_positions: Dict[str, S7SqueezePosition] = {}
        self.completed_positions: List[S7SqueezePosition] = []

    def register_escrow(self, escrow: WhalesMarketEscrowContract) -> None:
        self.escrows[escrow.symbol.upper()] = escrow

    def record_delivery(self, symbol: str, delivered_tokens: float) -> None:
        sym = symbol.upper()
        if sym in self.escrows:
            self.escrows[sym].delivered_volume += delivered_tokens

    def evaluate_minute_150_trigger(
        self,
        symbol: str,
        spot_price: float,
        current_ts: float,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Evaluates Minute 150 squeeze entry criteria:
          1. Elapsed time is between 150m and 160m (Minute 150 check).
          2. Undelivered ratio > 40% (high delivery debt).
          3. Spot price inside Forced Delivery Zone (0.3K < S_t < 1.85K).
        """
        sym = symbol.upper()
        escrow = self.escrows.get(sym)
        if not escrow:
            return False, "ESCROW_NOT_REGISTERED", {}

        minute = escrow.elapsed_minutes(current_ts)
        undelivered_ratio = escrow.undelivered_ratio
        in_forced_zone = escrow.is_forced_delivery_zone(spot_price)
        is_default_zone = escrow.is_default_zone(spot_price)

        telemetry = {
            "symbol": sym,
            "strike_k": escrow.strike_k,
            "spot_price": spot_price,
            "elapsed_minutes": round(minute, 1),
            "undelivered_ratio": round(undelivered_ratio, 3),
            "in_forced_delivery_zone": in_forced_zone,
            "is_default_zone": is_default_zone,
            "forced_zone_range": f"[{0.30*escrow.strike_k:.3f}, {1.85*escrow.strike_k:.3f}]",
        }

        # Check Kill-Switch: Above 1.85K
        if is_default_zone:
            return False, "KILLED_DEFAULT_ZONE", telemetry

        # Condition 1: Around Minute 150 (150m to 160m)
        cond_timing = 150.0 <= minute <= 165.0
        # Condition 2: Undelivered > 40%
        cond_undelivered = undelivered_ratio >= 0.40

        if cond_timing and cond_undelivered and in_forced_zone:
            return True, "ARM_MINUTE_150_SQUEEZE", telemetry

        return False, "CRITERIA_NOT_MET", telemetry

    def execute_squeeze_entry(
        self,
        symbol: str,
        spot_price: float,
        trade_size: float,
        current_ts: float,
    ) -> Optional[S7SqueezePosition]:
        """
        Executes long squeeze entry at Minute 150.
        """
        is_trigger, reason, telem = self.evaluate_minute_150_trigger(symbol, spot_price, current_ts)
        if not is_trigger:
            return None

        sym = symbol.upper()
        escrow = self.escrows[sym]
        pos_id = f"s7_{sym}_{int(current_ts)}"

        pos = S7SqueezePosition(
            position_id=pos_id,
            symbol=sym,
            entry_ts=current_ts,
            entry_minute=escrow.elapsed_minutes(current_ts),
            entry_price=spot_price,
            size=trade_size,
            state=SqueezeState.LONG_ACTIVE,
        )

        # Place shadow long order on Spot / Perp DEX
        order = self.shadow_broker.submit_order(
            symbol=sym,
            side=Side.BUY,
            order_type=OrderType.TAKER_IOC,
            price=spot_price * 1.005,  # 0.5% tolerance
            size=trade_size,
            venue="hyperliquid",
            current_ts=current_ts,
        )
        pos.order_id = order.order_id

        self.active_positions[pos_id] = pos
        logger.info(
            f"[+] S7 SQUEEZE ENTRY: Pos={pos_id} Symbol={sym} Minute={pos.entry_minute:.1f}m "
            f"EntryPx=${spot_price:.4f} Undelivered={escrow.undelivered_ratio*100:.1f}% "
            f"Zone=[{0.30*escrow.strike_k:.3f}, {1.85*escrow.strike_k:.3f}]"
        )
        return pos

    def update_position_and_check_exits(
        self,
        position_id: str,
        spot_price: float,
        current_ts: float,
    ) -> bool:
        """
        Evaluates exit conditions during the squeeze:
          1. Minute 238 Hard Flat Exit: Cut-off before Minute 240 settlement close.
          2. Kill-Switch Exit: S_t > 1.85K (sellers switch to default).
        """
        pos = self.active_positions.get(position_id)
        if not pos or pos.state != SqueezeState.LONG_ACTIVE:
            return False

        escrow = self.escrows.get(pos.symbol)
        if not escrow:
            return False

        minute = escrow.elapsed_minutes(current_ts)

        # Exit Rule 1: Kill-Switch on S_t > 1.85K (Rational default)
        if escrow.is_default_zone(spot_price):
            pos.exit_ts = current_ts
            pos.exit_minute = minute
            pos.exit_price = spot_price
            pos.realized_pnl_usd = (spot_price - pos.entry_price) * pos.size
            pos.state = SqueezeState.KILLED_DEFAULT_SPIKE
            pos.exit_reason = f"Kill-switch triggered: Spot ${spot_price:.4f} >= 1.85K (${1.85*escrow.strike_k:.4f})."
            logger.warning(f"[!] S7 POSITION KILLED: Pos={position_id} {pos.exit_reason}")
            self.completed_positions.append(pos)
            del self.active_positions[position_id]
            return True

        # Exit Rule 2: Hard Flat Exit at Minute 238
        if minute >= 238.0:
            pos.exit_ts = current_ts
            pos.exit_minute = minute
            pos.exit_price = spot_price
            pos.realized_pnl_usd = (spot_price - pos.entry_price) * pos.size
            pos.state = SqueezeState.EXITED_M238
            pos.exit_reason = f"Hard Flat Exit reached at Minute {minute:.1f}m (cutoff 238m)."
            logger.info(
                f"[+] S7 FLAT EXIT M238: Pos={position_id} Symbol={pos.symbol} "
                f"ExitPx=${spot_price:.4f} RealizedPnL=${pos.realized_pnl_usd:.2f} PnL%={((spot_price/pos.entry_price)-1)*100:.2f}%"
            )
            self.completed_positions.append(pos)
            del self.active_positions[position_id]
            return True

        return False

    def simulate_tge_settlement_scenario(
        self,
        symbol: str,
        strike_k: float,
        total_tokens: float,
        delivered_tokens_at_m150: float,
        price_trajectory: List[Tuple[float, float]],  # List of (minute, price)
    ) -> S7SqueezePosition:
        """
        Simulates end-to-end 4-hour settlement trajectory.
        """
        t0 = 1_000_000.0
        escrow = WhalesMarketEscrowContract(
            symbol=symbol.upper(),
            strike_k=strike_k,
            total_volume_matched=total_tokens,
            delivered_volume=delivered_tokens_at_m150,
            t_settle_start=t0,
        )
        self.register_escrow(escrow)

        pos: Optional[S7SqueezePosition] = None

        for m, px in price_trajectory:
            t = t0 + (m * 60.0)
            if pos is None and 150.0 <= m <= 160.0:
                pos = self.execute_squeeze_entry(symbol, px, trade_size=10_000.0, current_ts=t)
            elif pos is not None and pos.state == SqueezeState.LONG_ACTIVE:
                closed = self.update_position_and_check_exits(pos.position_id, px, current_ts=t)
                if closed:
                    break

        return pos or S7SqueezePosition("none", symbol, 0, 0, 0, 0, SqueezeState.IDLE)


# ==============================================================================
# 4. DEMO & SELF-TEST EXECUTION
# ==============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=== Cross-Venue Experiment S7: Whales Market TGE Squeeze Tracker ===")

    engine = ExpS7WhalesTGESqueezeEngine()

    # Model Pre-market contract: Strike K = $1.00, 1M tokens matched
    # At Minute 150, only 300k delivered (70% undelivered > 40%)
    # Trajectory:
    #   Minute 150: Price = $1.20 (inside [0.30, 1.85]) -> Long entry
    #   Minute 180: Delivery panic pushes price to $1.45
    #   Minute 220: Price reaches $1.65
    #   Minute 238: Hard flat exit at $1.72
    trajectory = [
        (100.0, 1.05),
        (150.0, 1.20),
        (180.0, 1.45),
        (220.0, 1.65),
        (238.0, 1.72),
        (240.0, 1.70),
    ]

    pos = engine.simulate_tge_settlement_scenario(
        symbol="ZRO",
        strike_k=1.00,
        total_tokens=1_000_000.0,
        delivered_tokens_at_m150=300_000.0,  # 70% undelivered
        price_trajectory=trajectory,
    )

    print(f"[S7 Result] Status: {pos.state.value} | Entry: ${pos.entry_price:.2f} @ M{pos.entry_minute:.0f}")
    print(f"[S7 Result] Exit: ${pos.exit_price:.2f} @ M{pos.exit_minute:.0f} | Realized PnL: ${pos.realized_pnl_usd:.2f}")
