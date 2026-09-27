"""
EXPONENTIAL ASYMMETRIC FROG-IN-THE-PAN (Exp-AsymFIP) OPERATOR
=============================================================
Applies non-linear convex exponential dampening on long candidates to aggressively
suppress pump-and-dump wicks, while applying a convex power boost to short candidates
to maximize alpha extraction during rapid liquidation cascades.

Mathematical Formulation:
1. Long Candidates (F5 > 0):
   Quality_long = exp(-alpha_long * (max(0, max_j eps_j) / sum_j |eps_j|))
   F_ExpAsym = F5 * Quality_long

2. Short Candidates (F5 <= 0):
   Quality_short = 1.0 + clip(beta_short * (max(0, -min_j eps_j) / sum_j |eps_j|)^0.75, 0.0, 0.50)
   F_ExpAsym = F5 * Quality_short
"""

import numpy as np
from typing import Optional


def compute_exponential_asym_fip(
    fracdiff_scores: np.ndarray,
    residual_returns: np.ndarray,
    valid_mask: np.ndarray,
    lookback: int = 18,
    alpha_long: float = 2.50,
    beta_short: float = 1.20,
) -> np.ndarray:
    """
    Applies non-linear exponential jump dampening on long candidates while
    applying a convex power boost to short liquidation cascades.
    """
    n_bars, n_symbols = fracdiff_scores.shape
    adjusted_scores = np.zeros_like(fracdiff_scores)

    for t in range(lookback, n_bars):
        m_t = valid_mask[t]
        v_idx = np.where(m_t)[0]
        if len(v_idx) >= 10:
            res_win = residual_returns[t - lookback : t, v_idx]
            scores_t = fracdiff_scores[t, v_idx]

            total_abs_drift = np.sum(np.abs(res_win), axis=0) + 1e-8
            max_pos_jump = np.maximum(0.0, np.max(res_win, axis=0))
            max_neg_jump = np.maximum(0.0, -np.min(res_win, axis=0))

            pos_jump_ratio = max_pos_jump / total_abs_drift
            neg_jump_ratio = max_neg_jump / total_abs_drift

            # Exponential decay for longs: aggressive non-linear suppression of outlier pumps
            long_quality = np.exp(-alpha_long * pos_jump_ratio)

            # Convex power boost for shorts: amplifies rapid liquidation cascades
            short_quality = 1.0 + np.clip(beta_short * (neg_jump_ratio ** 0.75), 0.0, 0.50)

            adj_t = np.where(scores_t > 0, scores_t * long_quality, scores_t * short_quality)
            adjusted_scores[t, v_idx] = adj_t

    adjusted_scores[:lookback] = adjusted_scores[lookback]
    return adjusted_scores
