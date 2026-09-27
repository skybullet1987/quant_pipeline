"""
DISPERSION-GATED DYNAMIC BREADTH ALLOCATOR
==========================================
Dynamically adjusts long/short portfolio breadth based on cross-sectional factor
dispersion significance (|z| >= z_threshold).

During high-dispersion trending regimes, expands basket to K=10 to capture breadth.
During low-dispersion chop regimes, contracts basket to K=4 high-conviction assets,
leaving idle capital in cash/USDC to prevent churn and compress drawdowns.
"""

import numpy as np
from typing import Tuple, List


def compute_dispersion_gated_selection(
    gaussian_scores: np.ndarray,
    valid_idx: np.ndarray,
    z_threshold: float = 1.0,
    min_k: int = 4,
    max_k: int = 10,
) -> Tuple[np.ndarray, np.ndarray, int, int]:
    """
    Identifies active long and short baskets based on cross-sectional factor significance.
    
    Returns:
        target_longs: Array of selected asset indices for longs
        target_shorts: Array of selected asset indices for shorts
        k_long: Number of selected longs
        k_short: Number of selected shorts
    """
    scores_valid = gaussian_scores[valid_idx]
    
    # Identify statistically significant longs (z >= +1.0) and shorts (z <= -1.0)
    sig_long_sub = np.where(scores_valid >= z_threshold)[0]
    sig_short_sub = np.where(scores_valid <= -z_threshold)[0]

    k_long = int(np.clip(len(sig_long_sub), min_k, max_k))
    k_short = int(np.clip(len(sig_short_sub), min_k, max_k))

    sorted_sub = np.argsort(scores_valid)
    target_shorts = valid_idx[sorted_sub[:k_short]].tolist()
    target_longs = valid_idx[sorted_sub[-k_long:]].tolist()

    return target_longs, target_shorts, k_long, k_short


def compute_dispersion_gated_weights(
    gaussian_scores: np.ndarray,
    current_weights: np.ndarray,
    valid_mask_t: np.ndarray,
    z_threshold: float = 1.0,
    min_k: int = 4,
    max_k: int = 10,
    deadband: float = 0.030,
) -> np.ndarray:
    """
    Dynamically adjusts long/short portfolio weights based on cross-sectional
    factor dispersion significance and applies Leland deadband operator.
    """
    num_assets = len(gaussian_scores)
    v_idx = np.where(valid_mask_t)[0]
    if len(v_idx) < (min_k * 2):
        return current_weights.copy()

    target_longs, target_shorts, k_long, k_short = compute_dispersion_gated_selection(
        gaussian_scores, v_idx, z_threshold=z_threshold, min_k=min_k, max_k=max_k
    )

    target_weights = np.zeros(num_assets)
    target_weights[target_longs] = 0.50 / k_long
    target_weights[target_shorts] = -0.50 / k_short

    # Apply Leland deadband operator
    executed_weights = np.where(
        np.abs(target_weights - current_weights) >= deadband,
        target_weights,
        current_weights,
    )

    return executed_weights
