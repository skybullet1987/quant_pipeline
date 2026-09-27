#!/usr/bin/env python3
"""
DOWNSIDE MARKET COSKEWNESS SIEVE
================================
Calculates cross-sectional coskewness with negative market innovations
to filter out tokens prone to liquidation waterfalls during BTC/ETH flash crashes.
"""

from __future__ import annotations

import numpy as np


def compute_downside_coskewness(
    residual_returns: np.ndarray,
    market_returns: np.ndarray,
    lookback_bars: int = 72,  # 12 days
) -> np.ndarray:
    """
    Calculates cross-sectional coskewness with negative market innovations
    to filter out tokens prone to liquidation waterfalls during BTC/ETH flash crashes.

    Parameters:
    -----------
    residual_returns: shape (T_bars, N_assets)
    market_returns: shape (T_bars,) - benchmark market returns (e.g. BTC)
    lookback_bars: trailing lookback window (default 72 bars = 12 days)

    Returns:
    --------
    np.ndarray: shape (N_assets,) array of downside coskewness scores
    """
    T, N = residual_returns.shape
    coskew_scores = np.zeros(N)

    eff_lookback = min(lookback_bars, T)
    if eff_lookback < 12:
        return coskew_scores

    # Extract downside market innovations
    mkt = market_returns[-eff_lookback:]
    downside_mkt = np.minimum(0.0, mkt - np.mean(mkt))
    downside_mkt_var = np.mean(downside_mkt ** 2) + 1e-8

    if downside_mkt_var < 1e-10:
        return coskew_scores

    for i in range(N):
        res = residual_returns[-eff_lookback:, i]
        res_centered = res - np.mean(res)
        res_std = np.std(res) + 1e-8

        # E[res * (downside_mkt)^2] / (std(res) * var(downside_mkt))
        co_moment = np.mean(res_centered * (downside_mkt ** 2))
        coskew_scores[i] = co_moment / (res_std * downside_mkt_var)

    return coskew_scores
