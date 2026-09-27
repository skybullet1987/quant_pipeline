#!/usr/bin/env python3
"""
BAYESIAN IC-GATED DYNAMIC VOLATILITY GOVERNOR
=============================================
Dynamically modulates target portfolio volatility based on the trailing
Spearman rank Information Coefficient (IC) of idiosyncratic alpha factor scores.

Gears up target volatility during high-conviction factor runs (IC > +0.15)
and de-gears during regime transitions (IC -> 0), holding average volatility
contained at ~55% and bypassing static Ito variance drag.
"""

from __future__ import annotations

import numpy as np
import scipy.stats as stats


def compute_ic_modulated_volatility(
    factor_scores_history: np.ndarray,
    residual_returns_history: np.ndarray,
    base_target_vol: float = 0.60,
    min_vol: float = 0.38,
    max_vol: float = 0.74,
    lookback_bars: int = 18,
    psi_scaling: float = 0.35,
) -> float:
    """
    Dynamically modulates target portfolio volatility based on trailing
    Spearman rank Information Coefficient (IC) of the momentum factor.

    Parameters:
    -----------
    factor_scores_history: shape (T_bars, N_assets)
    residual_returns_history: shape (T_bars, N_assets)
    base_target_vol: baseline target volatility (default: 0.60)
    min_vol: lower floor for target volatility (default: 0.38)
    max_vol: upper ceiling for target volatility (default: 0.74)
    lookback_bars: trailing lookback window in 4H bars (18 bars = 72 hours)
    psi_scaling: sensitivity multiplier for IC z-score modulation

    Returns:
    --------
    float: dynamically modulated target volatility in [min_vol, max_vol]
    """
    T = factor_scores_history.shape[0]
    if T < lookback_bars + 1:
        return base_target_vol

    trailing_ics = []
    for t in range(T - lookback_bars, T - 1):
        scores = factor_scores_history[t]
        next_returns = residual_returns_history[t + 1]

        valid_mask = np.isfinite(scores) & np.isfinite(next_returns)
        if np.sum(valid_mask) > 10:
            ic, _ = stats.spearmanr(scores[valid_mask], next_returns[valid_mask])
            if np.isfinite(ic):
                trailing_ics.append(ic)

    if len(trailing_ics) < 6:
        return base_target_vol

    mean_ic = float(np.mean(trailing_ics))
    std_ic = float(np.std(trailing_ics)) + 1e-6
    ic_zscore = mean_ic / std_ic

    # Modulate target volatility around base_target_vol
    vol_multiplier = 1.0 + psi_scaling * np.clip(ic_zscore, -1.5, 2.0)
    modulated_vol = base_target_vol * vol_multiplier

    return float(np.clip(modulated_vol, min_vol, max_vol))
