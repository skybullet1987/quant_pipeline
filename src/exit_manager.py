from __future__ import annotations
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class PositionSide(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"

class ExitStage(str, Enum):
    INITIAL = "INITIAL"
    BREAKEVEN = "BREAKEVEN"
    CHANDELIER = "CHANDELIER"
    CLOSED = "CLOSED"

@dataclass
class TradeLifecycleState:
    coin: str
    side: PositionSide
    entry_price: float
    size: float
    current_stage: ExitStage
    stop_loss_px: float

class HyperliquidExitManager:
    def __init__(
        self,
        fee_rate_bps: float = 3.5,
        slippage_buffer_bps: float = 2.0,
        chandelier_mult: float = 2.5
    ) -> None:
        self.chandelier_mult = chandelier_mult
        self.friction_factor = ((fee_rate_bps * 2.0) + slippage_buffer_bps) / 10000.0

    def evaluate_exit_logic(
        self,
        state: TradeLifecycleState,
        c_high: float,
        c_low: float,
        historical_highs_6b: List[float],
        historical_lows_6b: List[float],
        current_atr_20: float
    ) -> TradeLifecycleState:
        # Breakeven Check (+1.0x ATR)
        if state.current_stage == ExitStage.INITIAL:
            if state.side == PositionSide.LONG and c_high >= (state.entry_price + 1.0 * current_atr_20):
                new_sl = state.entry_price * (1.0 + self.friction_factor)
                state.stop_loss_px = max(state.stop_loss_px, new_sl)
                state.current_stage = ExitStage.BREAKEVEN
            elif state.side == PositionSide.SHORT and c_low <= (state.entry_price - 1.0 * current_atr_20):
                new_sl = state.entry_price * (1.0 - self.friction_factor)
                state.stop_loss_px = min(state.stop_loss_px, new_sl)
                state.current_stage = ExitStage.BREAKEVEN

        # Chandelier Activation Check (+1.8x ATR)
        if state.current_stage in (ExitStage.INITIAL, ExitStage.BREAKEVEN):
            if state.side == PositionSide.LONG and c_high >= (state.entry_price + 1.8 * current_atr_20):
                highest_high = max(historical_highs_6b + [c_high])
                chandelier_sl = highest_high - (self.chandelier_mult * current_atr_20)
                state.stop_loss_px = max(state.stop_loss_px, chandelier_sl)
                state.current_stage = ExitStage.CHANDELIER
            elif state.side == PositionSide.SHORT and c_low <= (state.entry_price - 1.8 * current_atr_20):
                lowest_low = min(historical_lows_6b + [c_low])
                chandelier_sl = lowest_low + (self.chandelier_mult * current_atr_20)
                state.stop_loss_px = min(state.stop_loss_px, chandelier_sl)
                state.current_stage = ExitStage.CHANDELIER

        # Advancing Chandelier Stops
        elif state.current_stage == ExitStage.CHANDELIER:
            if state.side == PositionSide.LONG:
                highest_high = max(historical_highs_6b + [c_high])
                candidate_sl = highest_high - (self.chandelier_mult * current_atr_20)
                if candidate_sl > state.stop_loss_px:
                    state.stop_loss_px = candidate_sl
            elif state.side == PositionSide.SHORT:
                lowest_low = min(historical_lows_6b + [c_low])
                candidate_sl = lowest_low + (self.chandelier_mult * current_atr_20)
                if candidate_sl < state.stop_loss_px:
                    state.stop_loss_px = candidate_sl

        return state
