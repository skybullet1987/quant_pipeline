"""
EFFECTIVE TRIAL COUNT (N_eff) AUDITOR & DEFLATED SHARPE RATIO
=============================================================
Implements Bailey & López de Prado (2014) spectral eigenvalue correction for
correlated multiple testing in quantitative alpha research.

When strategies are correlated (e.g. variants of the same momentum factor, rho >= 0.85),
using literal trial count N in the Deflated Sharpe Ratio creates excessive conservative bias.
The effective number of independent trials N_eff is derived from the eigenvalues of the
empirical correlation matrix:

    N_eff = (sum_k lambda_k)^2 / sum_k (lambda_k^2) = N^2 / tr(Sigma_trials^2)
"""

import math
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from scipy import stats


def compute_effective_trials_spectral(corr_matrix: np.ndarray) -> Tuple[float, np.ndarray]:
    """
    Computes effective number of independent trials (N_eff) via eigenvalue decomposition.
    
    corr_matrix: (N, N) correlation matrix of strategy returns
    Returns: (N_eff, eigenvalues)
    """
    # Clean correlation matrix
    c = np.nan_to_num(corr_matrix, nan=0.0)
    np.fill_diagonal(c, 1.0)
    c = 0.5 * (c + c.T)  # Enforce exact symmetry

    eigenvalues = np.linalg.eigvalsh(c)
    eigenvalues = np.maximum(eigenvalues, 1e-8)  # Positive semi-definite

    sum_eig = np.sum(eigenvalues)
    sum_eig_sq = np.sum(eigenvalues ** 2)

    n_eff = float((sum_eig ** 2) / max(sum_eig_sq, 1e-8))
    return n_eff, eigenvalues


def compute_spectral_dsr(
    candidate_sharpe: float,
    bar_returns: np.ndarray,
    n_eff: float,
    var_sharpes: float,
    annualization_factor: float = math.sqrt(2190.0),
) -> Dict[str, Any]:
    """
    Computes Deflated Sharpe Ratio using N_eff effective independent trials.
    """
    r = np.asarray(bar_returns, dtype=np.float64)
    r = r[~np.isnan(r)]
    t_samples = len(r)

    if t_samples < 10:
        return {"dsr": 0.0, "sr_star": 0.0, "n_eff": n_eff}

    std_sharpes = math.sqrt(max(var_sharpes, 1e-6))
    skew = float(stats.skew(r))
    kurt = float(stats.kurtosis(r, fisher=False))

    euler_mascheroni = 0.57721566490153286
    if n_eff > 1.0:
        z1 = float(stats.norm.ppf(1.0 - 1.0 / n_eff))
        z2 = float(stats.norm.ppf(1.0 - 1.0 / (n_eff * math.e)))
        sr_star = std_sharpes * ((1.0 - euler_mascheroni) * z1 + euler_mascheroni * z2)
    else:
        sr_star = 0.0

    sr_period = candidate_sharpe / annualization_factor
    sr_star_period = sr_star / annualization_factor

    denom_var = 1.0 - skew * sr_period + ((kurt - 1.0) / 4.0) * (sr_period ** 2)
    denom_std = math.sqrt(max(denom_var / max(t_samples - 1, 1), 1e-8))

    dsr_stat = (sr_period - sr_star_period) / denom_std
    dsr_p_value = float(stats.norm.cdf(dsr_stat))

    return {
        "candidate_sharpe": candidate_sharpe,
        "expected_max_null_sharpe": float(sr_star),
        "deflated_sharpe_ratio": float(dsr_p_value),
        "dsr_statistic": float(dsr_stat),
        "n_eff": float(n_eff),
        "skewness": skew,
        "kurtosis": kurt,
    }
