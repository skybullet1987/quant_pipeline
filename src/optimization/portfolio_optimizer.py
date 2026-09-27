import numpy as np
import cvxpy as cp
from sklearn.covariance import LedoitWolf
import logging

logger = logging.getLogger("PortfolioOptimizer")

def optimize_portfolio_weights(
    symbols: list[str],
    alpha_scores: dict[str, float],
    returns_matrix: np.ndarray,
    betas_btc: dict[str, float],
    target_gross_leverage: float = 1.5,
    max_single_weight: float = 0.35,
    risk_aversion: float = 1.0
) -> dict[str, float]:
    """
    Computes optimal portfolio weights using Ledoit-Wolf shrinkage covariance,
    strictly enforcing dollar-neutrality and BTC beta-neutrality.
    """
    n = len(symbols)
    if n == 0 or returns_matrix.shape[1] != n:
        raise ValueError("Mismatch between symbol count and returns matrix dimensions.")

    # 1. Estimate Shrinkage Covariance Matrix
    lw = LedoitWolf()
    sigma = lw.fit(returns_matrix).covariance_
    
    # 2. Build parameter vectors
    alpha_vec = np.array([alpha_scores.get(s, 0.0) for s in symbols])
    beta_vec = np.array([betas_btc.get(s, 1.0) for s in symbols])
    
    # 3. Formulate Optimization Variables
    w = cp.Variable(n)
    portfolio_var = cp.quad_form(w, sigma)
    expected_alpha = alpha_vec @ w
    
    objective = cp.Minimize(0.5 * risk_aversion * portfolio_var - expected_alpha)
    
    constraints = [
        cp.sum(w) == 0.0,                                    # Strict Dollar Neutrality
        beta_vec @ w == 0.0,                                 # Strict BTC Beta Neutrality
        cp.norm(w, 1) <= target_gross_leverage,              # Gross Leverage Cap (1.5x)
        w <= max_single_weight,                              # Long Cap
        w >= -max_single_weight                              # Short Cap
    ]
    
    prob = cp.Problem(objective, constraints)
    try:
        prob.solve(solver=cp.OSQP, eps_abs=1e-6, eps_rel=1e-6, warm_start=True)
    except Exception as e:
        logger.warning(f"OSQP solver error: {e}. Falling back to ECOS.")
        prob.solve(solver=cp.ECOS)
        
    if prob.status not in ["optimal", "optimal_inaccurate"]:
        logger.error(f"Solver failed with status: {prob.status}. Falling back to rank-based allocation.")
        # Fallback allocation
        sorted_symbols = sorted(symbols, key=lambda s: alpha_scores.get(s, 0.0), reverse=True)
        fallback = {}
        for s in sorted_symbols[:3]:
            fallback[s] = target_gross_leverage / 6.0
        for s in sorted_symbols[-3:]:
            fallback[s] = -target_gross_leverage / 6.0
        return fallback

    weights = w.value
    return {symbols[i]: float(weights[i]) for i in range(n) if abs(weights[i]) > 0.005}
