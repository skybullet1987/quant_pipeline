#!/usr/bin/env python3
"""
AVELLANEDA-STOIKOV INVENTORY-SKEWED QUOTING
===========================================
Calculates asymmetric maker bid/ask quote offsets based on inventory imbalance
to maximize fill completion and eliminate adverse selection.
"""

from __future__ import annotations

import math
from typing import Optional, Tuple
import numpy as np


def compute_as_quote_offsets(
    mid_price: float,
    current_inventory_ratio: float,
    target_inventory_ratio: float,
    asset_vol_24h: float,
    gamma_inv: float = 0.15,
    best_bid: Optional[float] = None,
    best_ask: Optional[float] = None,
    sz_decimals: Optional[int] = None,
) -> Tuple[float, float]:
    """
    Calculates asymmetric maker bid/ask quote offsets based on inventory
    imbalance to maximize fill completion and eliminate adverse selection.
    Enforces directional tick rounding and BBO non-crossing guards so
    Add-Liquidity-Only (ALO) orders are never rejected for crossing the book.

    Parameters:
    -----------
    mid_price: reference mid price
    current_inventory_ratio: active position notional / total NAV
    target_inventory_ratio: desired target position notional / total NAV
    asset_vol_24h: annualized or daily asset volatility
    gamma_inv: risk aversion parameter
    best_bid: optional live L2 best bid price for non-crossing guard
    best_ask: optional live L2 best ask price for non-crossing guard
    sz_decimals: optional Hyperliquid szDecimals for directional tick quantization

    Returns:
    --------
    tuple[float, float]: (bid_quote, ask_quote)
    """
    if mid_price <= 0.0 or math.isnan(mid_price):
        return 0.0, 0.0

    # Inventory imbalance: negative means we need to buy, positive means we need to sell
    inventory_delta = current_inventory_ratio - target_inventory_ratio

    # Normalize volatility to 4H execution horizon if annualized vol (> 0.15) is passed
    eff_vol = asset_vol_24h / math.sqrt(365.25 * 6.0) if asset_vol_24h > 0.15 else asset_vol_24h
    eff_vol = float(np.clip(eff_vol, 0.005, 0.15))

    # Reservation price shift
    reservation_spread_shift = inventory_delta * gamma_inv * (eff_vol ** 2) * 10.0

    # Base half-spread (in bps, e.g., 2.0 bps for inside quote)
    base_half_spread = 0.0002

    # Adjust bid and ask offsets relative to mid price
    bid_offset = base_half_spread + reservation_spread_shift
    ask_offset = base_half_spread - reservation_spread_shift

    # Bounds to ensure orders remain passive (inside the book)
    bid_offset = float(np.clip(bid_offset, 0.00005, 0.0010))
    ask_offset = float(np.clip(ask_offset, 0.00005, 0.0010))

    bid_quote = mid_price * (1.0 - bid_offset)
    ask_quote = mid_price * (1.0 + ask_offset)

    # Directional tick quantization & BBO non-crossing guard for ALO safety
    if sz_decimals is not None and mid_price > 0:
        max_decimals = max(0, 6 - sz_decimals)
        sig_fig_decimals = 5 - int(math.floor(math.log10(abs(mid_price)))) - 1
        target_decimals = min(max_decimals, sig_fig_decimals) if sig_fig_decimals >= 0 else sig_fig_decimals
        tick_size = 10.0 ** (-target_decimals)

        # Floor bid and ceil ask so rounding never pushes quotes across mid/BBO
        bid_quote = math.floor(bid_quote / tick_size + 1e-9) * tick_size
        ask_quote = math.ceil(ask_quote / tick_size - 1e-9) * tick_size

        if best_ask is not None and best_ask > 0:
            bid_quote = min(bid_quote, best_ask - tick_size)
        if best_bid is not None and best_bid > 0:
            ask_quote = max(ask_quote, best_bid + tick_size)

        bid_quote = float(round(bid_quote, max(0, target_decimals)))
        ask_quote = float(round(ask_quote, max(0, target_decimals)))

    return bid_quote, ask_quote
