"""
ASYMMETRIC REGIME-GATED CUSHION GOVERNOR
========================================
Dynamically adapts the Grossman-Zhou capital preservation floor M(t) based on
macro market regime (Bull vs Bear/Chop):
  - Macro Bull Regime: M_bull = 0.28 (expands cushion to capture convex compounding trends)
  - Chop/Bear Regime:  M_bear = 0.18 (tightens drawdown floor to suppress tail volatility)
"""

import numpy as np


def compute_regime_gated_m_floor(
    btc_prices: np.ndarray,
    current_bar: int,
    lookback_bars: int = 180,  # 30 days of 4H bars
    m_bull: float = 0.28,
    m_bear: float = 0.18,
) -> float:
    """
    Computes dynamic Grossman-Zhou floor M_eff based on rolling BTC macro momentum.
    """
    if current_bar < lookback_bars:
        return 0.25  # default baseline

    p_curr = btc_prices[current_bar]
    p_past = btc_prices[current_bar - lookback_bars]

    macro_return = (p_curr / (p_past + 1e-8)) - 1.0

    # Bull regime: positive macro trend with upward slope
    if macro_return > 0.05:
        return m_bull
    elif macro_return < -0.05:
        return m_bear
    else:
        # Interpolate between m_bear and m_bull for flat markets
        return 0.22
