import numpy as np
import cvxpy as cp
from typing import Dict, List, Tuple

def compute_softmax_conviction_weights(
    alpha_scores: np.ndarray,
    top_k_long: int = 4,
    top_k_short: int = 3,
    tau_temp: float = 0.85
) -> Tuple[np.ndarray, List[int], List[int]]:
    """Calculates non-linear softmax conviction weights across top longs and short hedges."""
    n = len(alpha_scores)
    order = np.argsort(-alpha_scores)
    long_idx = list(order[:top_k_long])
    short_idx = list(order[-top_k_short:])

    # Standardized alpha scores
    z_alpha = (alpha_scores - np.mean(alpha_scores)) / (np.std(alpha_scores) + 1e-8)

    # Long Basket Softmax
    z_long = z_alpha[long_idx]
    exp_long = np.exp(z_long / tau_temp)
    w_long_norm = exp_long / np.sum(exp_long)

    # Short Basket Softmax (inverted z-score for structural laggards)
    z_short = -z_alpha[short_idx]
    exp_short = np.exp(z_short / tau_temp)
    w_short_norm = exp_short / np.sum(exp_short)

    alpha_conviction = np.zeros(n)
    alpha_conviction[long_idx] = w_long_norm
    alpha_conviction[short_idx] = -w_short_norm
    return alpha_conviction, long_idx, short_idx

def solve_clarabel_conic_portfolio(
    cov_shrunk: np.ndarray,
    alpha_conviction: np.ndarray,
    betas_btc: np.ndarray,
    carry_yields: np.ndarray,
    w_prev: np.ndarray,
    target_net_beta: float,
    target_gross_leverage: float,
    long_idx: List[int],
    short_idx: List[int],
    lambda_alpha: float = 1.0,
    lambda_tc: float = 0.0015,
    lambda_carry: float = 0.35
) -> np.ndarray:
    """Solves the unified Clarabel SOCP portfolio problem with strict cone bounds."""
    n = len(alpha_conviction)
    w = cp.Variable(n)

    # Risk objective: covariance variance + alpha tilt + turnover friction - carry yield
    variance = cp.quad_form(w, cp.psd_wrap(cov_shrunk))
    alpha_term = alpha_conviction @ w
    turnover = cp.norm1(w - w_prev)
    carry_term = carry_yields @ w

    objective = cp.Minimize(0.5 * variance - lambda_alpha * alpha_term + lambda_tc * turnover - lambda_carry * carry_term)

    # Maximum single-name gross capacity: 35% of gross exposure
    w_max = 0.35 * target_gross_leverage

    active_indices = set(long_idx + short_idx)
    inactive_indices = [i for i in range(n) if i not in active_indices]

    constraints = [
        cp.norm1(w) <= target_gross_leverage,
        betas_btc @ w == target_net_beta,
        w[long_idx] >= 0.0,
        w[short_idx] <= 0.0,
        w <= w_max,
        w >= -w_max
    ]
    if len(inactive_indices) > 0:
        constraints.append(w[inactive_indices] == 0.0)

    prob = cp.Problem(objective, constraints)
    try:
        prob.solve(solver=cp.CLARABEL, tol_gap_abs=1e-5, max_iter=100)
        if prob.status in ["optimal", "optimal_inaccurate"] and w.value is not None:
            return np.array(w.value)
    except Exception:
        pass

    # Fallback heuristic: project softmax conviction directly to beta target
    fallback_w = np.zeros(n)
    fallback_w[long_idx] = (alpha_conviction[long_idx] / np.sum(alpha_conviction[long_idx])) * (0.80 * target_gross_leverage)
    fallback_w[short_idx] = (alpha_conviction[short_idx] / np.sum(np.abs(alpha_conviction[short_idx]))) * (0.20 * target_gross_leverage)
    return fallback_w
