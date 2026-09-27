import numpy as np
from typing import Tuple

def compute_bull_conviction_score(
    alpha_skew: float,
    btc_trend_intensity: float,
    oi_velocity: float,
    basis_expansion: float
) -> float:
    """Calculates composite Bull Conviction Score S_t from 4 orthogonal indicators."""
    w = np.array([0.30, 0.35, 0.20, 0.15])
    z_scores = np.array([alpha_skew, btc_trend_intensity, oi_velocity, basis_expansion])
    return float(np.dot(w, z_scores))

def compute_dynamic_net_beta(
    s_t: float,
    hmm_probs: np.ndarray,
    beta_min: float = 0.0,
    beta_max: float = 2.50,
    beta_chop: float = 0.0,
    beta_crisis: float = -0.35,
    kappa_beta: float = 1.85,
    s0_star: float = 0.75
) -> float:
    """Computes continuous net market beta target beta_net*."""
    # Logistic transition in Regime S0 (Bull Expansion)
    logistic_s0 = beta_min + (beta_max - beta_min) / (1.0 + np.exp(-kappa_beta * (s_t - s0_star)))
    p_s0, p_s1, p_s2 = hmm_probs[0], hmm_probs[1], hmm_probs[2]
    beta_net = (p_s0 * logistic_s0) + (p_s1 * beta_chop) + (p_s2 * beta_crisis)
    return float(np.clip(beta_net, -0.50, 2.50))

def compute_fractional_kelly_leverage(
    ic_oof: float,
    alpha_dispersion: float,
    sigma_port_yz: float,
    current_drawdown: float,
    portfolio_funding_rate: float,
    n_eff: float = 4.0,
    c_k: float = 0.28,
    d_max: float = 0.28,
    gamma_dd: float = 1.60,
    sigma_target: float = 0.45
) -> Tuple[float, dict]:
    """Calculates continuous Fractional Kelly gross leverage with multi-stage brakes."""
    # 1. Base Fractional Kelly
    ic_clamped = max(0.01, ic_oof)
    disp_clamped = max(0.05, alpha_dispersion)
    vol_clamped = max(0.10, sigma_port_yz)
    raw_kelly = c_k * (ic_clamped * disp_clamped * np.sqrt(n_eff)) / vol_clamped

    # 2. Quadratic Volatility Drag Throttle (Omega_drag)
    omega_drag = min(1.0, (sigma_target / vol_clamped) ** 2)

    # 3. Endogenous Drawdown Brake (Phi_dd)
    d_clamped = min(d_max, max(0.0, current_drawdown))
    phi_dd = max(0.0, 1.0 - (d_clamped / d_max) ** gamma_dd)

    # 4. Funding Drag Attenuator (Psi_funding)
    psi_funding = np.exp(-1.15 * max(0.0, portfolio_funding_rate - 0.40))

    # Composite execution leverage bounded [0.50x, 5.00x]
    l_exec = float(np.clip(raw_kelly * omega_drag * phi_dd * psi_funding, 0.50, 5.00))

    telemetry = {
        "raw_kelly": raw_kelly,
        "omega_drag": omega_drag,
        "phi_dd": phi_dd,
        "psi_funding": psi_funding,
        "l_exec": l_exec
    }
    return l_exec, telemetry
