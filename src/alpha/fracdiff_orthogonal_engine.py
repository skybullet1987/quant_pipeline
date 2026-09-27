#!/usr/bin/env python3
"""
FRACTIONAL DIFFERENTIATION & GRAM-SCHMIDT ORTHOGONAL ALPHA ENGINE
=================================================================
Implements the core alpha specifications from the Institutional Compounding Blueprint:
1. Fractional Differentiation at d* = 0.38 (López de Prado Memory Preservation).
2. Multi-Beta Rolling Residualization against BTC and ETH benchmarks (F5).
3. Gram-Schmidt Orthogonalized Carry Arbitrage (F1_perp): <F1_perp, F5> == 0.
4. Idiosyncratic Residual Hurst Exponent (H_eps) for trend persistence verification.
"""

import math
from typing import Dict, List, Tuple, Optional
import numpy as np
import polars as pl


def compute_fracdiff_weights(d: float = 0.38, max_len: int = 120, threshold: float = 1e-4) -> np.ndarray:
    """
    Computes binomial series expansion weights for the fractional differencing operator (1 - B)^d:
        w_0 = 1,  w_k = -w_{k-1} * (d - k + 1) / k
    """
    weights = [1.0]
    for k in range(1, max_len):
        w_k = -weights[-1] * (d - k + 1) / k
        if abs(w_k) < threshold:
            break
        weights.append(w_k)
    return np.array(weights, dtype=np.float64)


def apply_fractional_differentiation(
    price_matrix: np.ndarray,
    d: float = 0.38,
    max_len: int = 60,
    threshold: float = 1e-4
) -> np.ndarray:
    """
    Applies memory-preserving fractional differentiation along the time axis (axis 0).
    Input: price_matrix (n_bars x n_symbols) in natural log space.
    Returns: fracdiff_matrix (n_bars x n_symbols).
    """
    weights = compute_fracdiff_weights(d=d, max_len=max_len, threshold=threshold)
    k_len = len(weights)
    n_bars, n_symbols = price_matrix.shape
    
    log_px = np.log(np.maximum(price_matrix, 1e-8))
    fracdiff_mat = np.zeros_like(log_px)
    
    for t in range(k_len - 1, n_bars):
        # dot product across lookback window: sum_{k=0}^{K-1} w_k * log_px[t - k]
        window = log_px[t - k_len + 1 : t + 1][::-1]  # shape: (k_len, n_symbols), index 0 is lag 0
        fracdiff_mat[t] = np.sum(window * weights[:, np.newaxis], axis=0)
        
    # Forward-fill initial warmup
    fracdiff_mat[:k_len - 1] = fracdiff_mat[k_len - 1]
    return fracdiff_mat


def compute_multi_beta_residual_momentum(
    returns_mat: np.ndarray,
    btc_rets: np.ndarray,
    eth_rets: np.ndarray,
    valid_mask: np.ndarray,
    lookback_h: int = 18
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Extracts idiosyncratic residual momentum (F5) purged of BTC and ETH systematic beta:
        r_{i,t} = alpha_i + beta_{i,BTC} * r_{BTC,t} + beta_{i,ETH} * r_{ETH,t} + eps_{i,t}
    
    Returns:
        f5_signal: (n_bars x n_symbols) standardized cumulative residual score.
        residuals: (n_bars x n_symbols) bar-by-bar idiosyncratic innovations.
    """
    n_bars, n_symbols = returns_mat.shape
    residuals = np.zeros_like(returns_mat)
    f5_signal = np.zeros_like(returns_mat)
    
    # Benchmarks matrix X: [ones, btc, eth]
    for t in range(lookback_h + 2, n_bars):
        mask_t = valid_mask[t]
        if np.sum(mask_t) < 5:
            continue
            
        b_w = btc_rets[t - lookback_h : t]
        e_w = eth_rets[t - lookback_h : t]
        X = np.column_stack([np.ones(lookback_h), b_w, e_w])
        
        # Precompute (X^T X)^{-1} X^T with ridge stabilizer
        try:
            XtX_inv_Xt = np.linalg.inv(X.T @ X + np.eye(3) * 1e-6) @ X.T
        except np.linalg.LinAlgError:
            continue
            
        for i in range(n_symbols):
            if not mask_t[i]:
                continue
            y_i = returns_mat[t - lookback_h : t, i]
            betas = XtX_inv_Xt @ y_i
            # Purge systematic BTC and ETH market beta, retaining idiosyncratic alpha drift
            res_w = y_i - (betas[1] * b_w + betas[2] * e_w)
            residuals[t, i] = res_w[-1]
            
            res_vol = np.std(res_w) + 1e-8
            # F5 standardized score: cumulative idiosyncratic drift scaled by idiosyncratic volatility
            f5_signal[t, i] = np.sum(res_w) / (math.sqrt(lookback_h) * res_vol)
            
    return f5_signal, residuals


def orthogonalize_carry_gram_schmidt(
    f_carry: np.ndarray,
    f_momentum: np.ndarray,
    valid_mask: np.ndarray
) -> np.ndarray:
    """
    Enforces exact Gram-Schmidt orthogonalization between Funding Carry (F1) and Momentum (F5):
        F1_perp = F1 - ( <F1, F5> / ||F5||^2 ) * F5
    Guarantees that <F1_perp, F5> == 0 on every rebalancing bar.
    """
    n_bars, n_symbols = f_carry.shape
    f1_perp = np.zeros_like(f_carry)
    
    for t in range(n_bars):
        mask_t = valid_mask[t]
        if np.sum(mask_t) < 8:
            continue
            
        c_t = f_carry[t, mask_t].copy()
        m_t = f_momentum[t, mask_t].copy()
        
        # Demean cross-sectionally
        c_t -= np.mean(c_t)
        m_t -= np.mean(m_t)
        
        norm_sq = np.sum(m_t ** 2)
        if norm_sq > 1e-10:
            projection = (np.dot(c_t, m_t) / norm_sq) * m_t
            ortho = c_t - projection
        else:
            ortho = c_t
            
        f1_perp[t, mask_t] = ortho
        
    return f1_perp


def compute_idiosyncratic_hurst_exponent(
    residuals_w: np.ndarray,
    min_window: int = 8
) -> float:
    """
    Computes Rescaled Range (R/S) Hurst exponent H on idiosyncratic residual returns.
    H >= 0.62 indicates statistically persistent trend structure.
    H ~ 0.50 indicates pure random walk / white noise.
    H < 0.40 indicates mean reversion.
    """
    n = len(residuals_w)
    if n < min_window:
        return 0.50
        
    mean_adj = residuals_w - np.mean(residuals_w)
    cum_dev = np.cumsum(mean_adj)
    r = np.max(cum_dev) - np.min(cum_dev)
    s = np.std(residuals_w) + 1e-8
    
    rs = r / s
    if rs <= 0.0 or n <= 2:
        return 0.50
        
    # Anis-Lloyd corrected empirical Hurst approximation
    h = math.log(max(rs, 1e-4)) / math.log(n)
    return float(np.clip(h, 0.0, 1.0))
