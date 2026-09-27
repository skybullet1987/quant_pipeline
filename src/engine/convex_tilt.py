"""
CONVEX TOP-DECILE TILTING OPERATOR
==================================
Applies an asymmetric conviction boost to Top 2 Longs and Bottom 2 Shorts
exhibiting low jump ratios (pristine accumulation), without violating Gate 1
single-asset concentration limits (max weight <= 20%).

Mathematical Formulation:
  w_i^* = 1.25 * w_base   if Rank_i <= 2 and JumpRatio_i <= 0.20
  w_i^* = 0.75 * w_base   for Ranks 7 and 8
  w_i^* = w_base          otherwise
"""

import numpy as np


def apply_convex_top_decile_tilt(
    base_weights: np.ndarray,
    factor_scores: np.ndarray,
    jump_ratios: np.ndarray,
    top_tilt: float = 0.25,
) -> np.ndarray:
    """
    Applies asymmetric conviction boost to clean non-jump runners in top/bottom ranks.
    """
    tilted_weights = base_weights.copy()
    active_longs = np.where(base_weights > 0)[0]
    active_shorts = np.where(base_weights < 0)[0]

    # Tilting for Long basket
    if len(active_longs) >= 4:
        sorted_longs = active_longs[np.argsort(-factor_scores[active_longs])]
        # Boost top 2 longs if non-jump
        for idx in sorted_longs[:2]:
            if jump_ratios[idx] <= 0.20:
                tilted_weights[idx] *= 1.0 + top_tilt
        # Downweight tail longs (ranks 7 & 8 if available)
        for idx in sorted_longs[-2:]:
            tilted_weights[idx] *= 1.0 - top_tilt

    # Tilting for Short basket
    if len(active_shorts) >= 4:
        sorted_shorts = active_shorts[np.argsort(factor_scores[active_shorts])]
        # Boost top 2 shorts if non-jump
        for idx in sorted_shorts[:2]:
            if jump_ratios[idx] <= 0.20:
                tilted_weights[idx] *= 1.0 + top_tilt
        # Downweight tail shorts
        for idx in sorted_shorts[-2:]:
            tilted_weights[idx] *= 1.0 - top_tilt

    # Enforce dollar neutrality (sum longs = 0.50, sum shorts = -0.50)
    long_sum = np.sum(tilted_weights[tilted_weights > 0])
    short_sum = np.sum(np.abs(tilted_weights[tilted_weights < 0]))

    if long_sum > 1e-6:
        tilted_weights[tilted_weights > 0] = (
            tilted_weights[tilted_weights > 0] / long_sum
        ) * 0.50
    if short_sum > 1e-6:
        tilted_weights[tilted_weights < 0] = -(
            np.abs(tilted_weights[tilted_weights < 0]) / short_sum
        ) * 0.50

    return np.clip(tilted_weights, -0.20, 0.20)
