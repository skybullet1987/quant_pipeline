"""
HUBER ROBUST MULTI-BETA RESIDUAL MOMENTUM ENGINE
================================================
Implements Huber M-estimator regression to eliminate beta distortion caused by
fat-tailed benchmark flash crashes (BTC, ETH). 

Mathematical Formulation:
  r_{i, t} = \alpha_i + \beta_{i, BTC} r_{BTC, t} + \beta_{i, ETH} r_{ETH, t} + \epsilon_{i, t}

Huber Loss Function:
  \rho_\delta(e) = 0.5 * e^2                 for |e| <= \delta
                 = \delta * (|e| - 0.5 * \delta) for |e| > \delta
  where \delta = 1.345 * MAD(e) (yielding 95% efficiency under normal distribution).

Uses batched Iteratively Reweighted Least Squares (IRLS) with vectorized linear solves
for sub-millisecond execution across the entire universe.
"""

import math
import numpy as np
from typing import Tuple


def compute_huber_residuals_bar(
    returns_window: np.ndarray,      # (T, N)
    benchmark_window: np.ndarray,    # (T, K)
    valid_mask_t: np.ndarray,        # (N,)
    epsilon: float = 1.345,
    max_iter: int = 3,
) -> np.ndarray:
    """
    Solves Huber robust regressions simultaneously for all valid assets at time t
    using batched IRLS with normal equations: (X^T W_i X) \beta_i = X^T W_i y_i.
    """
    T, N = returns_window.shape
    X = np.column_stack([np.ones(T), benchmark_window])  # (T, K+1)
    K1 = X.shape[1]

    residuals = np.zeros(N)
    v_idx = np.where(valid_mask_t)[0]
    V = len(v_idx)
    if V < 5:
        return residuals

    Y = returns_window[:, v_idx]  # (T, V)

    # 1. Initial OLS Estimate
    XtX = X.T @ X + np.eye(K1) * 1e-6
    XtX_inv_Xt = np.linalg.inv(XtX) @ X.T  # (K1, T)
    betas = XtX_inv_Xt @ Y                 # (K1, V)
    res = Y - X @ betas                    # (T, V)

    # 2. Batched IRLS Iterations
    reg_eye = np.eye(K1)[None, :, :] * 1e-6
    for _ in range(max_iter):
        med = np.median(res, axis=0, keepdims=True)
        mad = np.median(np.abs(res - med), axis=0, keepdims=True)
        scale = 1.4826 * mad + 1e-6
        u = np.abs(res) / (epsilon * scale)
        w = np.where(u <= 1.0, 1.0, 1.0 / np.maximum(u, 1e-6))  # (T, V)

        # Batched normal equations:
        # XtWX: (V, K1, K1)
        XtWX = np.einsum('tv,tk,tl->vkl', w, X, X) + reg_eye
        # XtWy: (V, K1)
        XtWy = np.einsum('tv,tk,tv->vk', w, X, Y)

        # Batched solve: (V, K1, 1) -> (K1, V)
        sol = np.linalg.solve(XtWX, XtWy[:, :, None])[:, :, 0]
        betas = sol.T
        res = Y - X @ betas

    residuals[v_idx] = res[-1]
    return residuals


def compute_multi_beta_huber_residual_momentum(
    returns_mat: np.ndarray,
    btc_rets: np.ndarray,
    eth_rets: np.ndarray,
    valid_mask: np.ndarray,
    lookback_h: int = 18,
    epsilon: float = 1.345,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Computes rolling Huber robust multi-beta residual momentum signals and residuals.
    
    Returns:
        f5_huber: (n_bars x n_symbols) standardized cumulative residual score.
        residuals: (n_bars x n_symbols) bar-by-bar idiosyncratic innovations.
    """
    n_bars, n_symbols = returns_mat.shape
    residuals = np.zeros_like(returns_mat)
    f5_huber = np.zeros_like(returns_mat)

    for t in range(lookback_h + 2, n_bars):
        mask_t = valid_mask[t]
        if np.sum(mask_t) < 5:
            continue

        ret_w = returns_mat[t - lookback_h : t]
        b_w = btc_rets[t - lookback_h : t]
        e_w = eth_rets[t - lookback_h : t]
        bench_w = np.column_stack([b_w, e_w])

        res_t = compute_huber_residuals_bar(
            returns_window=ret_w,
            benchmark_window=bench_w,
            valid_mask_t=mask_t,
            epsilon=epsilon,
            max_iter=3,
        )
        residuals[t] = res_t

        # Compute standardized score over lookback window
        # Use recent residuals to construct standardized Information Ratio
        v_idx = np.where(mask_t)[0]
        if len(v_idx) > 0 and t >= lookback_h * 2:
            recent_res = residuals[t - lookback_h : t, v_idx]
            res_vol = np.std(recent_res, axis=0) + 1e-8
            res_sum = np.sum(recent_res, axis=0)
            f5_huber[t, v_idx] = res_sum / (math.sqrt(lookback_h) * res_vol)

    return f5_huber, residuals
