"""
GAUSSIAN INVERSE-NORMAL RANK TRANSFORMATION
===========================================
Eliminates fat-tail outlier sizing distortions in cross-sectional factor models.
Maps ordinal factor ranks uniformly onto a standard Gaussian bell curve N(0, 1)
via the inverse Gaussian cumulative distribution function (Probit transform).

Mathematical Formulation:
  u_i = (Rank(F_i) - 0.5) / N_valid
  \tilde{F}_i = \Phi^{-1}(u_i)
"""

import numpy as np
import scipy.stats as stats


def gaussian_rank_transform_1d(factor_scores: np.ndarray, mask: np.ndarray = None) -> np.ndarray:
    """
    Maps a 1D vector of cross-sectional factor scores to N(0, 1) via inverse CDF.
    """
    if mask is not None:
        valid_mask = np.isfinite(factor_scores) & mask
    else:
        valid_mask = np.isfinite(factor_scores)

    n_valid = int(np.sum(valid_mask))
    if n_valid <= 1:
        return np.zeros_like(factor_scores)

    # Compute fractional ranks in (0, 1)
    ranks = stats.rankdata(factor_scores[valid_mask], method="average")
    uniform_ranks = (ranks - 0.5) / n_valid

    # Map uniform distribution to standard normal N(0, 1)
    gaussian_scores = stats.norm.ppf(uniform_ranks)

    output = np.zeros_like(factor_scores)
    output[valid_mask] = gaussian_scores
    return output


def gaussian_rank_transform_2d(factor_matrix: np.ndarray, valid_mask: np.ndarray = None) -> np.ndarray:
    """
    Applies Gaussian rank transformation across each row (bar) of a 2D factor matrix.
    """
    n_bars, n_symbols = factor_matrix.shape
    transformed = np.zeros_like(factor_matrix)

    for t in range(n_bars):
        m_t = valid_mask[t] if valid_mask is not None else None
        transformed[t] = gaussian_rank_transform_1d(factor_matrix[t], m_t)

    return transformed
