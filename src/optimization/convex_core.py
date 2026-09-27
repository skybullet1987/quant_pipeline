import numpy as np
import cvxpy as cp
from typing import Tuple, List, Dict

def compute_bull_conviction_score(
    alpha_skew: float,
    btc_trend_intensity: float,
    oi_velocity: float,
    basis_expansion: float
) -> float:
    w = np.array([0.30, 0.35, 0.20, 0.15])
    z = np.array([alpha_skew, btc_trend_intensity, oi_velocity, basis_expansion])
    return float(np.dot(w, z))

def compute_clean_dynamic_beta(
    s_t: float,
    hmm_probs: np.ndarray,
    beta_min: float = 0.0,
    beta_max: float = 2.00,
    beta_chop: float = 0.0,
    beta_crisis: float = -0.35,
    kappa_beta: float = 1.85,
    s0_star: float = 0.75
) -> float:
    logistic_s0 = beta_min + (beta_max - beta_min) / (1.0 + np.exp(-kappa_beta * (s_t - s0_star)))
    target_b = (hmm_probs[0] * logistic_s0) + (hmm_probs[1] * beta_chop) + (hmm_probs[2] * beta_crisis)
    return float(np.clip(target_b, -0.50, 2.00))

def compute_risk_scaled_leverage(
    ic_oof: float,
    alpha_dispersion: float,
    sigma_port_yz: float,
    current_drawdown: float,
    portfolio_funding_rate: float,
    base_leverage: float = 1.75,
    d_max: float = 0.28,
    gamma_dd: float = 1.60,
    sigma_target: float = 0.40
) -> Tuple[float, dict]:
    """Relative Multiplicative Scaler normalized around historical medians."""
    # Normalized conviction multipliers
    ic_mult = np.clip(max(0.01, ic_oof) / 0.05, 0.70, 1.40)
    disp_mult = np.clip(max(0.05, alpha_dispersion) / 0.30, 0.75, 1.35)

    # Volatility drag throttle (monotonically decreasing)
    vol_c = max(0.10, sigma_port_yz)
    omega_drag = float(min(1.0, (sigma_target / vol_c) ** 1.5))

    # Endogenous Drawdown Brake
    d_clamped = min(d_max, max(0.0, current_drawdown))
    phi_dd = float(max(0.0, 1.0 - (d_clamped / d_max) ** gamma_dd))

    # Funding drag
    psi_funding = float(np.exp(-1.15 * max(0.0, portfolio_funding_rate - 0.40)))

    # Scaled execution leverage
    scaled_lev = base_leverage * ic_mult * disp_mult * omega_drag * phi_dd * psi_funding
    l_exec = float(np.clip(scaled_lev, 0.50, 3.50))

    return l_exec, {
        "ic_mult": ic_mult,
        "disp_mult": disp_mult,
        "omega_drag": omega_drag,
        "phi_dd": phi_dd,
        "l_exec": l_exec
    }

def compute_softmax_weights_with_caps(
    alpha_scores: np.ndarray,
    top_k_long: int = 5,
    top_k_short: int = 4,
    tau_temp: float = 0.85
) -> Tuple[np.ndarray, List[int], List[int]]:
    n = len(alpha_scores)
    order = np.argsort(-alpha_scores)
    long_idx = list(order[:top_k_long])
    short_idx = list(order[-top_k_short:])

    z_alpha = (alpha_scores - np.mean(alpha_scores)) / (np.std(alpha_scores) + 1e-8)

    # Long Softmax
    exp_l = np.exp(z_alpha[long_idx] / tau_temp)
    w_long = exp_l / np.sum(exp_l)

    # Short Softmax (inverted z-score)
    exp_s = np.exp(-z_alpha[short_idx] / tau_temp)
    w_short = exp_s / np.sum(exp_s)

    conviction = np.zeros(n)
    conviction[long_idx] = w_long
    conviction[short_idx] = -w_short
    return conviction, long_idx, short_idx

def solve_clarabel_socp(
    cov_shrunk: np.ndarray,
    alpha_conviction: np.ndarray,
    betas_btc: np.ndarray,
    carry_yields: np.ndarray,
    w_prev: np.ndarray,
    target_net_beta: float,
    target_gross_leverage: float,
    long_idx: List[int],
    short_idx: List[int],
    max_single_name_frac: float = 0.25
) -> np.ndarray:
    n = len(alpha_conviction)
    w = cp.Variable(n)

    var = cp.quad_form(w, cp.psd_wrap(cov_shrunk))
    alpha_term = alpha_conviction @ w
    tc = cp.norm1(w - w_prev)
    carry = carry_yields @ w

    obj = cp.Minimize(0.5 * var - 1.2 * alpha_term + 0.0015 * tc - 0.35 * carry)

    w_max = max_single_name_frac * target_gross_leverage
    active_set = set(long_idx + short_idx)
    inactive_set = [i for i in range(n) if i not in active_set]

    constraints = [
        cp.norm1(w) <= target_gross_leverage,
        betas_btc @ w == target_net_beta,
        w[long_idx] >= 0.0,
        w[short_idx] <= 0.0,
        w <= w_max,
        w >= -w_max
    ]
    if len(inactive_set) > 0:
        constraints.append(w[inactive_set] == 0.0)

    prob = cp.Problem(obj, constraints)
    try:
        prob.solve(solver=cp.CLARABEL, tol_gap_abs=1e-5, max_iter=100)
        if prob.status in ["optimal", "optimal_inaccurate"] and w.value is not None:
            return np.array(w.value)
    except Exception:
        pass

    # Heuristic Fallback
    fallback = np.zeros(n)
    fallback[long_idx] = (alpha_conviction[long_idx] / np.sum(alpha_conviction[long_idx])) * (0.80 * target_gross_leverage)
    fallback[short_idx] = (alpha_conviction[short_idx] / np.sum(np.abs(alpha_conviction[short_idx]))) * (0.20 * target_gross_leverage)
    return fallback
