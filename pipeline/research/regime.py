"""
Layer 1 State Measurement Engines:
- Gaussian HMM for P(Trend), P(Chop), P(Vol Expansion)
- Bayesian Online Changepoint Detection (BOCD) for P(Hazard)
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import polars as pl
from scipy.special import gammaln


@dataclass(frozen=True)
class BOCDConfig:
    hazard_lambda: float = 100.0  # Expected run-length parameter
    mu0: float = 0.0
    kappa0: float = 1.0
    alpha0: float = 1.0
    beta0: float = 1.0
    max_run_length: int = 500


class BOCDDetector:
    """
    Online Bayesian Changepoint Detection (Adams & MacKay 2007).
    Recursively tracks run-length posteriors and structural break hazard.
    """
    def __init__(self, config: BOCDConfig | None = None):
        self.cfg = config or BOCDConfig()
        self.reset()

    def reset(self) -> None:
        self.t = 0
        self.R = np.array([1.0], dtype=np.float32)  # P(r_0 = 0) = 1
        self.mu = np.array([self.cfg.mu0], dtype=np.float32)
        self.kappa = np.array([self.cfg.kappa0], dtype=np.float32)
        self.alpha = np.array([self.cfg.alpha0], dtype=np.float32)
        self.beta = np.array([self.cfg.beta0], dtype=np.float32)

    def _student_t_pdf(self, x: float, df: np.ndarray, loc: np.ndarray, scale: np.ndarray) -> np.ndarray:
        var = scale ** 2
        c = np.exp(gammaln((df + 1.0) / 2.0) - gammaln(df / 2.0)) / np.sqrt(np.pi * df * var)
        return c * (1.0 + (x - loc) ** 2 / (df * var)) ** (-(df + 1.0) / 2.0)

    def update(self, x: float) -> float:
        """
        Updates posterior with observation x_t.
        Returns P(r_t = 0 | x_{1:t}), the structural break hazard probability.
        """
        self.t += 1
        H = 1.0 / self.cfg.hazard_lambda

        # 1. Predictive probability under existing run lengths
        df = 2.0 * self.alpha
        scale = np.sqrt(self.beta * (self.kappa + 1.0) / (self.alpha * self.kappa))
        pred_probs = self._student_t_pdf(x, df, self.mu, scale) + 1e-12

        # 2. Predictive probability under base prior (changepoint hypothesis r_t = 0)
        df0 = np.array([2.0 * self.cfg.alpha0], dtype=np.float32)
        loc0 = np.array([self.cfg.mu0], dtype=np.float32)
        scale0 = np.array([np.sqrt(self.cfg.beta0 * (self.cfg.kappa0 + 1.0) / (self.cfg.alpha0 * self.cfg.kappa0))], dtype=np.float32)
        pred_prob_0 = float(self._student_t_pdf(x, df0, loc0, scale0)[0]) + 1e-12

        # 3. Growth and changepoint probabilities
        growth_probs = self.R * pred_probs * (1.0 - H)
        cp_prob = float(np.sum(self.R * H) * pred_prob_0)

        # 4. Form joint distribution and normalize
        joint = np.empty(len(growth_probs) + 1, dtype=np.float32)
        joint[0] = cp_prob
        joint[1:] = growth_probs
        evidence = float(np.sum(joint)) + 1e-12
        self.R = joint / evidence

        # 5. Update sufficient statistics across all hypotheses
        mu_all = np.concatenate([[self.cfg.mu0], self.mu])
        kappa_all = np.concatenate([[self.cfg.kappa0], self.kappa])
        alpha_all = np.concatenate([[self.cfg.alpha0], self.alpha])
        beta_all = np.concatenate([[self.cfg.beta0], self.beta])

        kappa_new = kappa_all + 1.0
        mu_new = (kappa_all * mu_all + x) / kappa_new
        alpha_new = alpha_all + 0.5
        beta_new = beta_all + (kappa_all * (x - mu_all) ** 2) / (2.0 * kappa_new)

        self.mu = mu_new.astype(np.float32)
        self.kappa = kappa_new.astype(np.float32)
        self.alpha = alpha_new.astype(np.float32)
        self.beta = beta_new.astype(np.float32)

        # 6. Memory-safe pruning
        if len(self.R) > self.cfg.max_run_length:
            self.R = self.R[:self.cfg.max_run_length]
            self.mu = self.mu[:self.cfg.max_run_length]
            self.kappa = self.kappa[:self.cfg.max_run_length]
            self.alpha = self.alpha[:self.cfg.max_run_length]
            self.beta = self.beta[:self.cfg.max_run_length]
            self.R /= np.sum(self.R)

        return float(self.R[0])


class GaussianHMMRegime:
    """
    3-State Continuous Gaussian HMM:
    State 0: Trend (high directional drift)
    State 1: Chop / Mean-Reverting (low drift, low volatility)
    State 2: Volatility Expansion (elevated variance)
    """
    def __init__(
        self,
        transition_matrix: np.ndarray | None = None,
        means: np.ndarray | None = None,
        variances: np.ndarray | None = None
    ):
        self.n_states = 3
        self.A = transition_matrix if transition_matrix is not None else np.array([
            [0.90, 0.08, 0.02],  # From Trend
            [0.05, 0.92, 0.03],  # From Chop
            [0.10, 0.15, 0.75],  # From Expansion
        ], dtype=np.float32)

        self.means = means if means is not None else np.array([0.001, 0.000, 0.000], dtype=np.float32)
        self.vars = variances if variances is not None else np.array([0.0004, 0.0001, 0.0016], dtype=np.float32)
        self.filter_state = np.array([0.333, 0.334, 0.333], dtype=np.float32)

    def _gaussian_emission(self, x: float) -> np.ndarray:
        stds = np.sqrt(self.vars)
        return (1.0 / (np.sqrt(2 * np.pi) * stds)) * np.exp(-0.5 * ((x - self.means) / stds) ** 2)

    def filter_step(self, observation: float) -> np.ndarray:
        """
        Online non-anticipative forward filter step.
        Returns P(S_t = k | x_{1:t}) for k in {Trend, Chop, Expansion}.
        """
        prior = np.dot(self.filter_state, self.A)
        emission = self._gaussian_emission(observation)
        posterior = prior * emission
        norm = np.sum(posterior) + 1e-12
        self.filter_state = (posterior / norm).astype(np.float32)
        return self.filter_state.copy()

    def process_series(self, returns: np.ndarray) -> np.ndarray:
        """Processes 1D returns array and returns (N, 3) matrix of state probabilities."""
        n = len(returns)
        probs = np.zeros((n, 3), dtype=np.float32)
        for i in range(n):
            probs[i] = self.filter_step(float(returns[i]))
        return probs
