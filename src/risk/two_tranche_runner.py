"""
Two-Tranche "Free-Runner" State Machine Architecture & Volumetric Trailing Exit
=============================================================================
Implements the convex payoff architecture:
- Tranche A (50% notional): Fixed profit barrier at +2.0x ATR, initial SL at -1.4x ATR.
- Tranche B (50% notional): Upon Tranche A completion, protective SL ratchets to Entry + 0.2x ATR
  (locking in guaranteed +1.1x ATR worst-case net profit), then transitions into an open-ended
  volumetric trailing runner (Volumetric Chandelier Exit + Kase Dev-Stop 3).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import numpy as np


@dataclass
class TwoTrancheSlot:
    symbol: str
    direction: int                  # +1: Long, -1: Short
    total_size: float
    entry_price: float
    atr_at_entry: float
    entry_bar_idx: int = 0
    tranche_a_closed: bool = False
    tranche_b_trailing_stop: float = 0.0
    highest_mark_price: float = 0.0
    lowest_mark_price: float = 1e9
    bars_held: int = 0
    tranche_a_pnl: float = 0.0
    tranche_b_pnl: float = 0.0
    is_closed: bool = False
    exit_reason: str = ""
    exit_price: float = 0.0


class TwoTrancheRunnerEngine:
    def __init__(
        self,
        tp_a_mult: float = 2.0,
        sl_init_mult: float = 1.4,
        ratchet_mult: float = 0.2,
        volumetric_base_mult: float = 3.0,
        skew_coef: float = 0.35,
        tvs_coef: float = 0.25,
        max_holding_bars: int = 18,  # 72 hours on 4H bars
    ):
        self.tp_a_mult = tp_a_mult
        self.sl_init_mult = sl_init_mult
        self.ratchet_mult = ratchet_mult
        self.volumetric_base_mult = volumetric_base_mult
        self.skew_coef = skew_coef
        self.tvs_coef = tvs_coef
        self.max_holding_bars = max_holding_bars
        self.active_slots: Dict[str, TwoTrancheSlot] = {}
        self.cooldown_tracker: Dict[str, int] = {}

    def open_slot(
        self,
        symbol: str,
        direction: int,
        total_size: float,
        entry_price: float,
        atr: float,
        bar_idx: int = 0,
    ) -> TwoTrancheSlot:
        """Opens a new two-tranche slot."""
        slot = TwoTrancheSlot(
            symbol=symbol,
            direction=direction,
            total_size=total_size,
            entry_price=entry_price,
            atr_at_entry=atr,
            entry_bar_idx=bar_idx,
            highest_mark_price=entry_price,
            lowest_mark_price=entry_price,
        )
        if direction == 1:
            slot.tranche_b_trailing_stop = entry_price - (self.sl_init_mult * atr)
        else:
            slot.tranche_b_trailing_stop = entry_price + (self.sl_init_mult * atr)

        self.active_slots[symbol] = slot
        return slot

    def compute_volumetric_chandelier_stop(
        self,
        slot: TwoTrancheSlot,
        current_price: float,
        current_atr: float,
        tvs: float = 0.0,
        return_skew_24h: float = 0.0,
        tr_skew: float = 0.0,
        tr_std: float = 0.0,
        tr_mean: float = 0.0,
    ) -> float:
        """
        Computes the adaptive trailing stop taking the tighter of Volumetric Chandelier
        and Cynthia Kase DevStop3.
        """
        if slot.direction == 1:  # Long
            dyn_mult = self.volumetric_base_mult * (
                1.0 + self.skew_coef * np.tanh(return_skew_24h)
            ) * (1.0 - self.tvs_coef * np.clip(tvs, -0.5, 0.5))
            
            p_chandelier = slot.highest_mark_price - (dyn_mult * current_atr)
            
            # Cynthia Kase DevStop 3 (skew-adjusted true range stop)
            if tr_std > 0 and tr_mean > 0:
                kase_dev = tr_mean + 3.0 * tr_std * (1.0 + (1.0 / 6.0) * tr_skew)
                p_kase = slot.highest_mark_price - kase_dev
                combined_stop = max(p_chandelier, p_kase)
            else:
                combined_stop = p_chandelier

            # Monotonic ratchet: stop can only move up
            return max(slot.tranche_b_trailing_stop, combined_stop)

        else:  # Short
            dyn_mult = self.volumetric_base_mult * (
                1.0 - self.skew_coef * np.tanh(return_skew_24h)
            ) * (1.0 + self.tvs_coef * np.clip(tvs, -0.5, 0.5))
            
            p_chandelier = slot.lowest_mark_price + (dyn_mult * current_atr)
            
            if tr_std > 0 and tr_mean > 0:
                kase_dev = tr_mean + 3.0 * tr_std * (1.0 + (1.0 / 6.0) * tr_skew)
                p_kase = slot.lowest_mark_price + kase_dev
                combined_stop = min(p_chandelier, p_kase)
            else:
                combined_stop = p_chandelier

            # Monotonic ratchet: stop can only move down
            return min(slot.tranche_b_trailing_stop, combined_stop)

    def evaluate_barriers(
        self,
        mark_prices: Dict[str, float],
        high_prices: Dict[str, float],
        low_prices: Dict[str, float],
        atrs: Dict[str, float],
        tvs_dict: Optional[Dict[str, float]] = None,
        return_skew_dict: Optional[Dict[str, float]] = None,
    ) -> List[dict]:
        """
        Evaluates dynamic barriers across all active slots.
        Returns executable order intents.
        """
        if tvs_dict is None:
            tvs_dict = {}
        if return_skew_dict is None:
            return_skew_dict = {}

        order_intents = []

        for symbol, slot in list(self.active_slots.items()):
            if symbol not in mark_prices:
                continue

            current_price = mark_prices[symbol]
            high_p = high_prices.get(symbol, current_price)
            low_p = low_prices.get(symbol, current_price)
            current_atr = atrs.get(symbol, slot.atr_at_entry)
            tvs = tvs_dict.get(symbol, 0.0)
            ret_skew = return_skew_dict.get(symbol, 0.0)

            slot.bars_held += 1
            slot.highest_mark_price = max(slot.highest_mark_price, high_p)
            slot.lowest_mark_price = min(slot.lowest_mark_price, low_p)

            # ==========================================
            # 1. LONG POSITION LOGIC
            # ==========================================
            if slot.direction == 1:
                # Tranche A Target Price (+2.0x ATR)
                tp_a_price = slot.entry_price + (self.tp_a_mult * slot.atr_at_entry)
                # Catastrophic Stop (-1.4x ATR)
                initial_sl_price = slot.entry_price - (self.sl_init_mult * slot.atr_at_entry)

                # Check Catastrophic Stop First (if Tranche A not yet closed)
                if not slot.tranche_a_closed and low_p <= initial_sl_price:
                    order_intents.append({
                        "symbol": symbol,
                        "action": "CLOSE_FULL_STOP",
                        "size": slot.total_size,
                        "price": initial_sl_price,
                        "order_type": "MARKET",
                        "reason": f"Hit initial stop loss at {initial_sl_price:.4f} (-{self.sl_init_mult}x ATR)",
                    })
                    slot.is_closed = True
                    slot.exit_reason = "INITIAL_STOP_LOSS"
                    slot.exit_price = initial_sl_price
                    self.cooldown_tracker[symbol] = 2
                    del self.active_slots[symbol]
                    continue

                # Check Tranche A Take-Profit (+2.0x ATR)
                if not slot.tranche_a_closed and high_p >= tp_a_price:
                    order_intents.append({
                        "symbol": symbol,
                        "action": "CLOSE_TRANCHE_A",
                        "size": slot.total_size * 0.5,
                        "price": tp_a_price,
                        "order_type": "ALO_LIMIT",
                        "reason": f"Harvested Tranche A (+{self.tp_a_mult}x ATR) at {tp_a_price:.4f}",
                    })
                    slot.tranche_a_closed = True
                    slot.tranche_a_pnl = 0.5 * slot.total_size * (tp_a_price - slot.entry_price)
                    # Ratchet Tranche B stop to Entry + 0.2x ATR (locks in guaranteed profit)
                    slot.tranche_b_trailing_stop = slot.entry_price + (self.ratchet_mult * slot.atr_at_entry)

                # Check Tranche B Volumetric Trailing Exit
                if slot.tranche_a_closed:
                    new_trail = self.compute_volumetric_chandelier_stop(
                        slot=slot,
                        current_price=current_price,
                        current_atr=current_atr,
                        tvs=tvs,
                        return_skew_24h=ret_skew,
                    )
                    slot.tranche_b_trailing_stop = new_trail

                    if low_p <= slot.tranche_b_trailing_stop:
                        exec_p = slot.tranche_b_trailing_stop
                        order_intents.append({
                            "symbol": symbol,
                            "action": "CLOSE_TRANCHE_B_TRAIL",
                            "size": slot.total_size * 0.5,
                            "price": exec_p,
                            "order_type": "MARKET",
                            "reason": f"Tranche B volumetric trailing stop triggered at {exec_p:.4f}",
                        })
                        slot.is_closed = True
                        slot.exit_reason = "TRANCHE_B_TRAIL"
                        slot.exit_price = exec_p
                        self.cooldown_tracker[symbol] = 2
                        del self.active_slots[symbol]
                        continue

            # ==========================================
            # 2. SHORT POSITION LOGIC
            # ==========================================
            elif slot.direction == -1:
                tp_a_price = slot.entry_price - (self.tp_a_mult * slot.atr_at_entry)
                initial_sl_price = slot.entry_price + (self.sl_init_mult * slot.atr_at_entry)

                if not slot.tranche_a_closed and high_p >= initial_sl_price:
                    order_intents.append({
                        "symbol": symbol,
                        "action": "CLOSE_FULL_STOP",
                        "size": slot.total_size,
                        "price": initial_sl_price,
                        "order_type": "MARKET",
                        "reason": f"Hit initial stop loss at {initial_sl_price:.4f} (-{self.sl_init_mult}x ATR)",
                    })
                    slot.is_closed = True
                    slot.exit_reason = "INITIAL_STOP_LOSS"
                    slot.exit_price = initial_sl_price
                    self.cooldown_tracker[symbol] = 2
                    del self.active_slots[symbol]
                    continue

                if not slot.tranche_a_closed and low_p <= tp_a_price:
                    order_intents.append({
                        "symbol": symbol,
                        "action": "CLOSE_TRANCHE_A",
                        "size": slot.total_size * 0.5,
                        "price": tp_a_price,
                        "order_type": "ALO_LIMIT",
                        "reason": f"Harvested Tranche A (+{self.tp_a_mult}x ATR) at {tp_a_price:.4f}",
                    })
                    slot.tranche_a_closed = True
                    slot.tranche_a_pnl = 0.5 * slot.total_size * (slot.entry_price - tp_a_price)
                    slot.tranche_b_trailing_stop = slot.entry_price - (self.ratchet_mult * slot.atr_at_entry)

                if slot.tranche_a_closed:
                    new_trail = self.compute_volumetric_chandelier_stop(
                        slot=slot,
                        current_price=current_price,
                        current_atr=current_atr,
                        tvs=tvs,
                        return_skew_24h=ret_skew,
                    )
                    slot.tranche_b_trailing_stop = new_trail

                    if high_p >= slot.tranche_b_trailing_stop:
                        exec_p = slot.tranche_b_trailing_stop
                        order_intents.append({
                            "symbol": symbol,
                            "action": "CLOSE_TRANCHE_B_TRAIL",
                            "size": slot.total_size * 0.5,
                            "price": exec_p,
                            "order_type": "MARKET",
                            "reason": f"Tranche B volumetric trailing stop triggered at {exec_p:.4f}",
                        })
                        slot.is_closed = True
                        slot.exit_reason = "TRANCHE_B_TRAIL"
                        slot.exit_price = exec_p
                        self.cooldown_tracker[symbol] = 2
                        del self.active_slots[symbol]
                        continue

            # ==========================================
            # 3. HORIZON EXPIRATION (72h MAX HOLDING)
            # ==========================================
            if slot.bars_held >= self.max_holding_bars:
                rem_size = slot.total_size * (0.5 if slot.tranche_a_closed else 1.0)
                order_intents.append({
                    "symbol": symbol,
                    "action": "HORIZON_EXPIRATION",
                    "size": rem_size,
                    "price": current_price,
                    "order_type": "ALO_LIMIT",
                    "reason": f"Horizon timeout reached ({self.max_holding_bars} bars / 72 hours)",
                })
                slot.is_closed = True
                slot.exit_reason = "HORIZON_EXPIRATION"
                slot.exit_price = current_price
                self.cooldown_tracker[symbol] = 2
                del self.active_slots[symbol]

        return order_intents

    def decay_cooldowns(self):
        """Decrements cooldown timer for recently closed slots."""
        for symbol in list(self.cooldown_tracker.keys()):
            self.cooldown_tracker[symbol] -= 1
            if self.cooldown_tracker[symbol] <= 0:
                del self.cooldown_tracker[symbol]
