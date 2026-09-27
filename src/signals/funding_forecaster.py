import numpy as np
import cvxpy as cp

def forecast_hourly_funding(
    instant_basis: float,
    volume_zscore: float,
    ret_4h: float,
    realized_twap_basis: float,
    theta: float = 0.15
) -> tuple[float, float]:
    """
    Ornstein-Uhlenbeck basis mean-reversion funding yield forecaster.
    Returns (hourly_funding_rate, annualized_carry_yield).
    """
    # OU drift update: dBasis = theta * (0 - instant_basis) + noise
    expected_basis_drift = -theta * instant_basis
    flow_premium = 0.00005 * np.tanh(volume_zscore) * np.sign(ret_4h)
    
    forecasted_hourly_rate = float(np.clip(instant_basis * 0.125 + expected_basis_drift + flow_premium, -0.005, 0.005))
    annualized_yield = forecasted_hourly_rate * 24 * 365
    return forecasted_hourly_rate, annualized_yield

def solve_alpha_orthogonal_carry(
    symbols: list[str],
    carry_yields: dict[str, float],
    alpha_scores: dict[str, float],
    btc_betas: dict[str, float],
    returns_matrix: np.ndarray,
    target_carry_leverage: float = 0.60
) -> dict[str, float]:
    """
    Solves Quadratic Program for basis carry allocations projected onto
    the null space of alpha scores and BTC market beta.
    Uses Tikhonov spectral shrinkage and cp.psd_wrap to guarantee numerical PSD convergence.
    """
    n = len(symbols)
    if n == 0:
        return {}

    # 1. Empirical Covariance with Spectral Shrinkage & Jitter
    if returns_matrix.shape[0] < 2 or returns_matrix.shape[1] != n:
        cov = np.eye(n) * 0.001
    else:
        raw_cov = np.cov(returns_matrix, rowvar=False)
        raw_cov = 0.5 * (raw_cov + raw_cov.T)  # Enforce exact symmetry
        
        # High-dimensional rank-deficiency regularization (Tikhonov + Ledoit-Wolf shrinkage)
        trace_mean = np.trace(raw_cov) / n if n > 0 else 0.001
        shrinkage_alpha = 0.20 if returns_matrix.shape[0] < n else 0.05
        cov = (1 - shrinkage_alpha) * raw_cov + shrinkage_alpha * trace_mean * np.eye(n)
        
        # Guarantee strictly positive eigenvalues
        min_eig = np.min(np.real(np.linalg.eigvals(cov)))
        if min_eig < 1e-4:
            cov += (abs(min_eig) + 1e-4) * np.eye(n)

    # 2. Linear Feature Constraints (Beta neutrality & Alpha null-space projection)
    b_carry = np.array([carry_yields.get(s, 0.0) for s in symbols])
    alpha_vec = np.array([alpha_scores.get(s, 0.0) for s in symbols])
    beta_vec = np.array([btc_betas.get(s, 1.0) for s in symbols])

    # Filter negligible yields
    if np.all(np.abs(b_carry) < 1e-6):
        return {s: 0.0 for s in symbols}

    # 3. Formulate Convex QP
    w = cp.Variable(n)
    
    # Wrap covariance with cp.psd_wrap to bypass fragile ARPACK validation
    risk_term = cp.quad_form(w, cp.psd_wrap(cov))
    return_term = b_carry @ w
    
    gamma = 2.0  # Risk aversion scalar
    objective = cp.Maximize(return_term - gamma * risk_term)
    
    constraints = [
        cp.sum(w) == 0.0,                              # Dollar-neutral cash balance
        alpha_vec @ w == 0.0,                          # Alpha orthogonal
        beta_vec @ w == 0.0,                           # Market beta neutral
        cp.norm(w, 1) <= target_carry_leverage,        # Carry gross leverage ceiling
        w <= 0.15,                                     # Position limits
        w >= -0.15
    ]
    
    prob = cp.Problem(objective, constraints)
    
    # Solve with CLARABEL / OSQP fallback
    try:
        prob.solve(solver=cp.CLARABEL, tol_gap_abs=1e-5, tol_gap_rel=1e-5)
    except Exception:
        try:
            prob.solve(solver=cp.OSQP, eps_abs=1e-4, eps_rel=1e-4)
        except Exception:
            prob.solve(solver=cp.SCS, eps=1e-3)

    if w.value is None or prob.status not in ["optimal", "optimal_inaccurate"]:
        # Soft fallback: zero carry if constrained QP fails
        return {s: 0.0 for s in symbols}

    raw_weights = w.value
    return {symbols[i]: float(np.round(raw_weights[i], 4)) for i in range(n) if abs(raw_weights[i]) > 0.001}
