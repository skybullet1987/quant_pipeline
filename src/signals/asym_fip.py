"""
ASYMMETRIC FROG-IN-THE-PAN (AsymFIP) OPERATOR
=============================================
Distinguishes between gradual accumulation on the Long side and sudden liquidation
waterfalls on the Short side in crypto perpetual futures.

Mathematical Formulation:
1. Long Candidates (F5 > 0):
   Penalizes tokens whose upward drift was driven by single-candle pump wicks.
   F_AsymFIP = F5 * (1.0 - clip(1.50 * (max(0, max_j eps_j) / sum_j |eps_j|), 0.0, 0.60))

2. Short Candidates (F5 <= 0):
   Boosts tokens experiencing rapid liquidation waterfalls.
   F_AsymFIP = F5 * (1.0 + clip(0.50 * (max(0, -min_j eps_j) / sum_j |eps_j|), 0.0, 0.40))
"""

import numpy as np
from typing import Optional


def compute_asymmetric_fip_scores(
    residuals: np.ndarray,
    raw_f5_scores: np.ndarray,
    valid_mask: np.ndarray,
    lookback: int = 18,
    lambda_long: float = 1.50,
    lambda_short: float = 0.50,
    max_long_penalty: float = 0.60,
    max_short_boost: float = 0.40,
) -> np.ndarray:
    """
    Computes Asymmetric FIP scores across the cross-section over an 18-bar (72H) lookback.
    
    residuals: np.ndarray of shape (n_bars, n_symbols)
    raw_f5_scores: np.ndarray of shape (n_bars, n_symbols)
    valid_mask: np.ndarray of shape (n_bars, n_symbols)
    """
    n_bars, n_symbols = raw_f5_scores.shape
    f_asym = np.zeros_like(raw_f5_scores)

    for t in range(lookback, n_bars):
        m_t = valid_mask[t]
        v_idx = np.where(m_t)[0]
        if len(v_idx) >= 10:
            res_win = residuals[t - lookback : t, v_idx]  # shape (lookback, len(v_idx))
            scores_t = raw_f5_scores[t, v_idx]

            total_abs_drift = np.sum(np.abs(res_win), axis=0) + 1e-8
            max_pos = np.maximum(0.0, np.max(res_win, axis=0))
            max_neg = np.maximum(0.0, -np.min(res_win, axis=0))

            jump_ratio_long = max_pos / total_abs_drift
            jump_ratio_short = max_neg / total_abs_drift

            long_mult = 1.0 - np.clip(jump_ratio_long * lambda_long, 0.0, max_long_penalty)
            short_mult = 1.0 + np.clip(jump_ratio_short * lambda_short, 0.0, max_short_boost)

            asym_scores = np.where(scores_t > 0, scores_t * long_mult, scores_t * short_mult)
            f_asym[t, v_idx] = asym_scores

    f_asym[:lookback] = f_asym[lookback]
    return f_asym
