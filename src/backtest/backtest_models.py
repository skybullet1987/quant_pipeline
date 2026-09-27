from dataclasses import dataclass
from typing import Tuple
import numpy as np

@dataclass
class Position:
    symbol: str
    is_long: bool
    weight: float
    entry_px: float
    atr: float
    current_sl_px: float
    peak_px: float
    trough_px: float
    stage: str
    entry_grp: int

class OnlineMicrostructureHMM:
    """Empirically fitted 3-State Gaussian HMM with causal forward filtering."""
    def __init__(self):
        self.means = np.array([[0.015, 0.5, 0.001], [0.035, 0.0, 0.003], [0.070, -1.0, 0.008]])
        self.cov_diags = np.array([[0.005**2, 0.5**2, 0.001**2], [0.015**2, 0.8**2, 0.002**2], [0.030**2, 1.2**2, 0.004**2]])
        self.A = np.array([[0.85, 0.12, 0.03], [0.10, 0.80, 0.10], [0.05, 0.20, 0.75]])
        self.gamma = np.array([0.70, 0.20, 0.10])

    def fit_from_training_observations(self, obs_matrix: np.ndarray):
        """Fits Gaussian HMM parameters from training window observations."""
        if obs_matrix.shape[0] < 60: return
        # Sort states by realized volatility (1st feature: BTC vol)
        vols = obs_matrix[:, 0]
        q33, q66 = np.quantile(vols, 0.33), np.quantile(vols, 0.66)
        mask0 = vols <= q33
        mask1 = (vols > q33) & (vols <= q66)
        mask2 = vols > q66
        
        for idx, m in enumerate([mask0, mask1, mask2]):
            if np.sum(m) > 5:
                self.means[idx] = np.mean(obs_matrix[m], axis=0)
                self.cov_diags[idx] = np.var(obs_matrix[m], axis=0) + 1e-6
        self.gamma = np.array([0.60, 0.30, 0.10])

    def filter_step(self, obs: np.ndarray) -> Tuple[np.ndarray, float, int]:
        prior = self.A.T @ self.gamma
        likelihoods = np.zeros(3)
        for j in range(3):
            diff = obs - self.means[j]
            var = self.cov_diags[j]
            log_prob = -0.5 * np.sum(np.log(2.0 * np.pi * var) + (diff ** 2) / var)
            likelihoods[j] = np.exp(np.clip(log_prob, -50.0, 50.0))
            
        unnorm = prior * likelihoods
        c_t = np.sum(unnorm)
        self.gamma = unnorm / c_t if c_t > 0 else prior
        
        leverage_tiers = np.array([1.75, 1.10, 0.50])
        dyn_leverage = float(np.dot(self.gamma, leverage_tiers))
        dominant_state = int(np.argmax(self.gamma))
        return self.gamma.copy(), dyn_leverage, dominant_state
