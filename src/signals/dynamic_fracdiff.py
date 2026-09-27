"""
ASSET-SPECIFIC OPTIMAL FRACTIONAL DIFFERENTIATION (Dynamic d_i*)
===============================================================
Computes the minimum fractional differencing parameter d_i* per asset that achieves
Augmented Dickey-Fuller (ADF) stationarity (p <= 0.010), preserving the maximum amount
of long-memory predictive autocorrelation.

Mathematical Formulation:
  d_i* = argmin_{d in [0.20, 0.60]} { d | ADF_pvalue(P_i^{(d)}) <= 0.010 }
"""

import math
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
import numpy as np
from typing import Tuple, Optional
from statsmodels.tsa.stattools import adfuller

from src.alpha.fracdiff_orthogonal_engine import compute_fracdiff_weights


def fractional_differentiation_1d(
    series: np.ndarray,
    d: float,
    max_len: int = 60,
    threshold: float = 1e-4,
) -> np.ndarray:
    """Applies memory-preserving fractional differentiation to a 1D price series."""
    weights = compute_fracdiff_weights(d=d, max_len=max_len, threshold=threshold)
    k_len = len(weights)
    n_bars = len(series)

    log_px = np.log(np.maximum(series, 1e-8))
    diff_series = np.zeros(n_bars)

    for t in range(k_len - 1, n_bars):
        window = log_px[t - k_len + 1 : t + 1][::-1]
        diff_series[t] = np.sum(window * weights)

    diff_series[:k_len - 1] = diff_series[k_len - 1]
    return diff_series


def compute_optimal_d_per_asset(
    price_matrix: np.ndarray,
    d_range: Tuple[float, float] = (0.20, 0.60),
    step: float = 0.04,
    p_threshold: float = 0.010,
    max_len: int = 60,
) -> np.ndarray:
    """
    Finds the minimum stationarity parameter d_i* for each column (symbol) in price_matrix.
    """
    n_bars, n_symbols = price_matrix.shape
    optimal_d = np.full(n_symbols, 0.38)
    d_candidates = np.arange(d_range[0], d_range[1] + 1e-5, step)

    # Subsample window for fast ADF testing (last 1000 bars if dataset is long)
    test_start = max(0, n_bars - 1200)

    for i in range(n_symbols):
        series = price_matrix[test_start:, i]
        if np.std(series) < 1e-8 or np.isnan(series).any():
            continue

        best_d = 0.38
        min_pval = 1.0

        for d in d_candidates:
            diff_series = fractional_differentiation_1d(series, d, max_len=max_len)
            valid_diff = diff_series[max_len:]
            if len(valid_diff) < 50 or np.std(valid_diff) < 1e-8:
                continue

            try:
                adf_result = adfuller(valid_diff, maxlag=4, autolag=None)
                p_val = float(adf_result[1])
                if p_val < min_pval:
                    min_pval = p_val
                    best_d = d
                if p_val <= p_threshold:
                    best_d = d
                    break
            except Exception:
                continue

        optimal_d[i] = best_d

    return optimal_d


def apply_dynamic_fractional_differentiation(
    price_matrix: np.ndarray,
    optimal_d: np.ndarray,
    max_len: int = 18,
) -> np.ndarray:
    """
    Applies asset-specific fractional differentiation d_i* to each asset in price_matrix.
    """
    n_bars, n_symbols = price_matrix.shape
    fd_matrix = np.zeros_like(price_matrix)

    for i in range(n_symbols):
        d_i = float(optimal_d[i])
        fd_matrix[:, i] = fractional_differentiation_1d(
            price_matrix[:, i], d=d_i, max_len=max_len
        )

    return fd_matrix
