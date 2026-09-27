"""
Phase 3: 2D Regime Engine & State Measurements.
Implements Numba-accelerated Adams & MacKay BOCD Hazard Engine and Continuous 3-State HMM.
"""
from __future__ import annotations

import numpy as np
from numba import njit
from hmmlearn.hmm import GaussianHMM
from sklearn.preprocessing import StandardScaler


@njit(fastmath=True)
def compute_bocd_hazard_numba(
    returns: np.ndarray,
    hazard_lambda: float = 240.0,
    alpha_0: float = 1.0,
    beta_0: float = 1.0,
    kappa_0: float = 1.0,
    mu_0: float = 0.0,
) -> np.ndarray:
    """
    Online Bayesian Changepoint Detection (Adams & MacKay) with Student-t conjugate priors.
    Returns P(r_t = 0 | x_{1:t}), the probability of a changepoint occurring at bar t.
    """
    T = len(returns)
    hazard_probs = np.zeros(T, dtype=np.float64)
    
    R = np.zeros(T + 1, dtype=np.float64)
    R[0] = 0.0
    
    mu_params = np.zeros(T + 1, dtype=np.float64)
    kappa_params = np.zeros(T + 1, dtype=np.float64)
    alpha_params = np.zeros(T + 1, dtype=np.float64)
    beta_params = np.zeros(T + 1, dtype=np.float64)
    
    mu_params[0] = mu_0
    kappa_params[0] = kappa_0
    alpha_params[0] = alpha_0
    beta_params[0] = beta_0

    H = 1.0 / hazard_lambda
    log_H = np.log(H)
    log_1_minus_H = np.log(1.0 - H)

    for t in range(T):
        x = returns[t]
        log_pred = np.zeros(t + 1, dtype=np.float64)

        for r in range(t + 1):
            df = 2.0 * alpha_params[r]
            var = (beta_params[r] * (kappa_params[r] + 1.0)) / (alpha_params[r] * kappa_params[r])
            std = np.sqrt(max(1e-12, var))
            diff = x - mu_params[r]
            log_pred[r] = -0.5 * (df + 1.0) * np.log(1.0 + (diff * diff) / (df * var)) - np.log(std)

        log_growth = R[: t + 1] + log_pred + log_1_minus_H
        log_cp = np.log(np.sum(np.exp(R[: t + 1] + log_pred)) + 1e-300) + log_H

        R_next = np.zeros(t + 2, dtype=np.float64)
        R_next[0] = log_cp
        R_next[1 : t + 2] = log_growth

        max_log = np.max(R_next)
        R_next_exp = np.exp(R_next - max_log)
        sum_exp = np.sum(R_next_exp)
        R_normalized = R_next_exp / sum_exp

        hazard_probs[t] = R_normalized[0]
        R[: t + 2] = np.log(np.maximum(R_normalized, 1e-300))

        for r in range(t, -1, -1):
            k_prev = kappa_params[r]
            mu_prev = mu_params[r]
            a_prev = alpha_params[r]
            b_prev = beta_params[r]

            k_new = k_prev + 1.0
            mu_new = (k_prev * mu_prev + x) / k_new
            a_new = a_prev + 0.5
            b_new = b_prev + (k_prev * (x - mu_prev) ** 2) / (2.0 * k_new)

            kappa_params[r + 1] = k_new
            mu_params[r + 1] = mu_new
            alpha_params[r + 1] = a_new
            beta_params[r + 1] = b_new

        kappa_params[0] = kappa_0
        mu_params[0] = mu_0
        alpha_params[0] = alpha_0
        beta_params[0] = beta_0

    return hazard_probs


class ContinuousRegimeClassifier:
    """3-State Gaussian Hidden Markov Model for continuous market state tracking."""

    def __init__(self, n_states: int = 3, random_state: int = 42):
        self.scaler = StandardScaler()
        self.n_states = n_states
        self.hmm = GaussianHMM(
            n_components=n_states,
            covariance_type="diag",
            min_covar=1e-4,
            n_iter=100,
            random_state=random_state,
        )

    def fit_predict_posteriors(self, returns: np.ndarray, volatility: np.ndarray) -> np.ndarray:
        """Fits HMM and returns calibrated (T, 3) state probabilities: [P_chop, P_trend, P_expansion]."""
        ret_clean = np.nan_to_num(returns, nan=0.0, posinf=0.0, neginf=0.0).reshape(-1, 1)
        vol_clean = np.nan_to_num(volatility, nan=0.0, posinf=0.0, neginf=0.0).reshape(-1, 1)

        X = np.hstack([ret_clean, vol_clean])
        X_scaled = self.scaler.fit_transform(X)

        self.hmm.fit(X_scaled)
        posteriors = self.hmm.predict_proba(X_scaled)  # Shape (T, 3)

        # Rank components by trace of diagonal variance (Chop -> Trend -> Expansion)
        cov_traces = [float(np.sum(self.hmm.covars_[i])) for i in range(self.n_states)]
        sorted_indices = [int(idx) for idx in np.argsort(cov_traces)]

        # Extract columns with explicit 1D slices
        calibrated = np.column_stack([
            posteriors[:, sorted_indices[0]],  # P_chop
            posteriors[:, sorted_indices[1]],  # P_trend
            posteriors[:, sorted_indices[2]],  # P_expansion
        ])

        return calibrated
