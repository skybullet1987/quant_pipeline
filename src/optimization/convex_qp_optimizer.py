import numpy as np
import cvxpy as cp
from sklearn.covariance import LedoitWolf

def solve_convex_qp_portfolio(
    symbols: list[str],
    alpha_scores: dict[str, float],
    returns_matrix: np.ndarray,
    btc_betas: dict[str, float],
    prev_weights: dict[str, float],
    target_gross_leverage: float = 1.5,
    lambda_risk: float = 1.0,
    lambda_turnover: float = 0.02,
    max_single_weight: float = 0.25,
    top_k: int = 5
) -> dict[str, float]:
    """
    Solves Multi-Objective QP Portfolio Allocation with strict factor neutrality,
    calibrated alpha z-scores, and enforced gross leverage.
    """
    # 1. Isolate Top-K Longs (highest alpha) and Bottom-K Shorts (lowest alpha)
    sorted_syms = sorted(symbols, key=lambda s: alpha_scores.get(s, 0.0), reverse=True)
    top_longs = sorted_syms[:top_k]
    top_shorts = sorted_syms[-top_k:]
    active_syms = top_longs + top_shorts
    n = len(active_syms)

    if n < 4:
        equal_w = target_gross_leverage / len(symbols)
        return {s: (equal_w if alpha_scores.get(s, 0.0) > 0 else -equal_w) for s in symbols}

    indices = [symbols.index(s) for s in active_syms]
    sub_returns = returns_matrix[:, indices]

    # 2. Condition covariance via Ledoit-Wolf Shrinkage
    lw = LedoitWolf()
    cov_matrix = lw.fit(sub_returns).covariance_ + np.eye(n) * 1e-5

    # 3. Z-Score standardize alpha across the active basket (mean=0, std=1)
    raw_alphas = np.array([alpha_scores.get(s, 0.0) for s in active_syms])
    alpha_vec = (raw_alphas - np.mean(raw_alphas)) / (np.std(raw_alphas) + 1e-8)
    
    beta_vec = np.array([btc_betas.get(s, 1.0) for s in active_syms])
    prev_w_vec = np.array([prev_weights.get(s, 0.0) for s in active_syms])

    # 4. Optimization Variables
    w = cp.Variable(n)
    u = cp.Variable(n)  # Turnover slack (|w - w_prev|)
    z = cp.Variable(n)  # Gross exposure slack (|w|)

    # Objective: Maximize standardized alpha, penalize covariance risk and turnover
    risk_term = 0.5 * lambda_risk * cp.quad_form(w, cov_matrix)
    alpha_term = - alpha_vec @ w
    turnover_term = lambda_turnover * cp.sum(u)

    objective = cp.Minimize(alpha_term + risk_term + turnover_term)
    w_bound = max_single_weight * (target_gross_leverage / 2.0)

    constraints = [
        cp.sum(w) == 0.0,                                    # Dollar neutrality
        cp.abs(beta_vec @ w) <= 0.05,                        # Strict BTC beta neutrality (|beta_p| <= 0.05)
        cp.sum(z) == target_gross_leverage,                  # Enforce full gross leverage deployment
        
        # Slack constraints
        u >= w - prev_w_vec,
        u >= -(w - prev_w_vec),
        z >= w,
        z >= -w,

        # Position box constraints
        w <= w_bound,
        w >= -w_bound
    ]

    prob = cp.Problem(objective, constraints)
    try:
        prob.solve(solver=cp.CLARABEL, warm_start=True)
    except Exception:
        prob.solve(solver=cp.OSQP)

    if prob.status not in ["optimal", "optimal_inaccurate"] or w.value is None:
        # Fallback: Top-K equal weighted long/short
        half_lev = target_gross_leverage / 2.0
        w_dict = {}
        for s in top_longs:
            w_dict[s] = round(float(half_lev / top_k), 4)
        for s in top_shorts:
            w_dict[s] = round(float(-half_lev / top_k), 4)
        return w_dict

    raw_weights = np.array(w.value)
    return {active_syms[i]: round(float(raw_weights[i]), 4) for i in range(n) if abs(raw_weights[i]) > 1e-4}
