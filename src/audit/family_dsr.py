"""
HYPOTHESIS FAMILY-PARTITIONED DEFLATED SHARPE RATIO (Family DSR)
================================================================
Isolates candidate trial distribution strictly to its own structural hypothesis
class (Fractional Differentiation & Staggered Momentum Family), eliminating spurious
variance inflation caused by unrelated failed breakout or cointegration experiments.

Mathematical Formulation:
  DSR = \Phi( (\hat{SR} - SR_0) / SE(\hat{SR}) )
  SR_0 = \sigma_{SR} * [ (1 - \gamma) \Phi^{-1}(1 - 1/N_eff) + \gamma \Phi^{-1}(1 - 1/(N_eff * e)) ]
  N_eff = ( \sum \lambda_i )^2 / \sum \lambda_i^2  (Spectral eigenvalue decomposition)
"""

import math
import numpy as np
from scipy import stats
from typing import Dict, List, Any, Optional


def compute_spectral_neff(returns_matrix: np.ndarray) -> float:
    """
    Computes effective number of independent trials via eigenvalue decomposition
    of the cross-trial correlation matrix (Bailey & Lopez de Prado, 2014).
    """
    corr_mat = np.corrcoef(returns_matrix, rowvar=False)
    corr_mat = np.nan_to_num(corr_mat, nan=0.0)
    np.fill_diagonal(corr_mat, 1.0)

    eigenvalues = np.linalg.eigvalsh(corr_mat)
    eigenvalues = np.maximum(eigenvalues, 0.0)

    sum_eigen = np.sum(eigenvalues)
    sum_sq_eigen = np.sum(eigenvalues ** 2)

    if sum_sq_eigen < 1e-8:
        return 1.0

    n_eff = (sum_eigen ** 2) / sum_sq_eigen
    return float(np.clip(n_eff, 1.0, returns_matrix.shape[1]))


def compute_family_dsr(
    candidate_sharpe: float,
    candidate_returns: np.ndarray,
    family_sharpes: List[float],
    n_eff_family: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Computes Deflated Sharpe Ratio conditioned on the family trial distribution.
    """
    T = len(candidate_returns)
    mean_r = np.mean(candidate_returns)
    std_r = np.std(candidate_returns) + 1e-8

    skew = float(stats.skew(candidate_returns))
    kurt = float(stats.kurtosis(candidate_returns, fisher=False))  # Pearson kurtosis

    # Standard error of Sharpe ratio
    sr_annual = candidate_sharpe
    sr_bar = sr_annual / math.sqrt(2190)

    # Mertens (2002) SE formulation
    var_sr = (1.0 + 0.5 * (sr_bar ** 2) - skew * sr_bar + ((kurt - 3.0) / 4.0) * (sr_bar ** 2)) / T
    se_sr = math.sqrt(max(var_sr, 1e-10)) * math.sqrt(2190)

    # Family parameters
    sigma_sr = float(np.std(family_sharpes)) if len(family_sharpes) > 1 else 0.40
    n_eff = n_eff_family or max(1.0, float(len(family_sharpes)))

    # Expected maximum Sharpe under the null hypothesis (Euler-Mascheroni approximation)
    euler_gamma = 0.5772156649
    p1 = 1.0 - (1.0 / n_eff)
    p2 = 1.0 - (1.0 / (n_eff * math.e))

    z1 = stats.norm.ppf(max(0.0001, min(0.9999, p1)))
    z2 = stats.norm.ppf(max(0.0001, min(0.9999, p2)))

    sr_0 = sigma_sr * ((1.0 - euler_gamma) * z1 + euler_gamma * z2)

    # Deflated Sharpe Ratio
    dsr_z = (sr_annual - sr_0) / se_sr
    dsr_p_value = float(stats.norm.cdf(dsr_z))

    return {
        "candidate_sharpe": sr_annual,
        "sr_0_hurdle": float(sr_0),
        "family_sigma_sr": sigma_sr,
        "n_eff_family": float(n_eff),
        "se_sharpe": float(se_sr),
        "dsr_z_score": float(dsr_z),
        "family_dsr": float(dsr_p_value),
        "gate_7_passed": dsr_p_value >= 0.950,
    }
