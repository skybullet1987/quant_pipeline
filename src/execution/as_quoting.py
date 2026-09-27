#!/usr/bin/env python3
"""
AVELLANEDA-STOIKOV INVENTORY-SKEWED QUOTING
===========================================
Calculates asymmetric maker bid/ask quote offsets based on inventory imbalance
to maximize fill completion and eliminate adverse selection.
"""

from __future__ import annotations

import numpy as np


def compute_as_quote_offsets(
    mid_price: float,
    current_inventory_ratio: float,
    target_inventory_ratio: float,
    asset_vol_24h: float,
    gamma_inv: float = 0.15,
) -> tuple[float, float]:
    """
    Calculates asymmetric maker bid/ask quote offsets based on inventory
    imbalance to maximize fill completion and eliminate adverse selection.

    Parameters:
    -----------
    mid_price: reference mid price
    current_inventory_ratio: active position notional / total NAV
    target_inventory_ratio: desired target position notional / total NAV
    asset_vol_24h: annualized asset volatility
    gamma_inv: risk aversion parameter

    Returns:
    --------
    tuple[float, float]: (bid_quote, ask_quote)
    """
    # Inventory imbalance: negative means we need to buy, positive means we need to sell
    inventory_delta = current_inventory_ratio - target_inventory_ratio

    # Reservation price shift
    reservation_spread_shift = inventory_delta * gamma_inv * (asset_vol_24h ** 2)

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

    return bid_quote, ask_quote
