import numpy as np
from dataclasses import dataclass
from typing import Tuple, Dict

@dataclass
class ConvexPosition:
    symbol: str
    is_long: bool
    weight: float
    entry_px: float
    atr_yz: float
    sigma_yz: float
    peak_px: float
    trough_px: float
    parabolic_sl_px: float
    catastrophe_collar_px: float
    entry_grp: int

def calculate_dynamic_parabolic_multiplier(
    entry_px: float,
    mfe_px: float,
    alpha_base: float = 4.00,
    alpha_floor: float = 1.65,
    lambda_profit: float = 2.10
) -> float:
    """Tightens trailing volatility multiplier exponentially as unrealized profit expands."""
    unrealized_gain = max(0.0, (mfe_px - entry_px) / (entry_px + 1e-8))
    return alpha_floor + (alpha_base - alpha_floor) * np.exp(-lambda_profit * unrealized_gain)

def evaluate_convex_position_exits(
    pos: ConvexPosition,
    bar_high: float,
    bar_low: float,
    bar_close: float,
    sigma_yz_cur: float,
    alpha_rank_percentile: float
) -> Tuple[bool, float, str]:
    """
    Evaluates position exits across 3 tiers:
    1. Catastrophe Volatility Collar (Hard Exchange Backstop)
    2. Dynamic Parabolic Yang-Zhang Trailing Stop
    3. Cross-Sectional Alpha Rank Demotion (< 0.60)
    """
    sqrt_dt = np.sqrt(4.0 / 24.0)

    if pos.is_long:
        # 1. Catastrophe Collar Check
        if bar_low <= pos.catastrophe_collar_px:
            return True, pos.catastrophe_collar_px, "CATASTROPHE_COLLAR"

        # Update MFE
        pos.peak_px = max(pos.peak_px, bar_high)
        alpha_dyn = calculate_dynamic_parabolic_multiplier(pos.entry_px, pos.peak_px)
        trailing_buffer = pos.peak_px * (1.0 - alpha_dyn * sigma_yz_cur * sqrt_dt)
        pos.parabolic_sl_px = max(pos.parabolic_sl_px, trailing_buffer)

        # 2. Dynamic Parabolic Trailing Stop Breach
        if bar_low <= pos.parabolic_sl_px:
            return True, pos.parabolic_sl_px, "PARABOLIC_YZ_STOP"

        # 3. YetiRank Demotion Rebalance Exit
        if alpha_rank_percentile < 0.60:
            return True, bar_close, "RANK_DEMOTION"

    else: # Short Tail Hedge
        if bar_high >= pos.catastrophe_collar_px:
            return True, pos.catastrophe_collar_px, "CATASTROPHE_COLLAR"

        pos.trough_px = min(pos.trough_px, bar_low)
        unrealized_gain = max(0.0, (pos.entry_px - pos.trough_px) / (pos.entry_px + 1e-8))
        alpha_dyn = 1.65 + (4.00 - 1.65) * np.exp(-2.10 * unrealized_gain)
        trailing_buffer = pos.trough_px * (1.0 + alpha_dyn * sigma_yz_cur * sqrt_dt)
        pos.parabolic_sl_px = min(pos.parabolic_sl_px, trailing_buffer)

        if bar_high >= pos.parabolic_sl_px:
            return True, pos.parabolic_sl_px, "PARABOLIC_YZ_STOP"

        if alpha_rank_percentile > 0.40:
            return True, bar_close, "RANK_DEMOTION"

    return False, 0.0, "ACTIVE"
