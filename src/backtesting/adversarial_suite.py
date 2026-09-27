"""
ADVERSARIAL MONTE CARLO PLACEBO SUITE (N=500 DRAWS)
===================================================
Constructs empirical null distributions with explicit random seeds to falsify candidates:
1. Asset-Label Permutation Null Distribution (N=500 draws) -> p_asset
2. Horizon-Matched Random Signal Null Distribution (N=500 draws) -> p_horizon
3. Time-Shifted Signal (+12h)
4. Sign Inversion (-1.0x)
5. Allocation-Matched Idle Cash Control
"""

import math
from typing import Dict, List, Tuple, Any, Callable
import numpy as np


class AdversarialPlaceboSuite:
    """Runs high-sample Monte Carlo falsification tests against candidate alpha signals."""
    
    def __init__(self, n_draws: int = 500, seed: int = 42):
        self.n_draws = n_draws
        self.seed = seed

    def run_asset_permutation_null(
        self,
        candidate_weights: np.ndarray,
        simulator_fn: Callable[[np.ndarray], Dict[str, Any]],
        candidate_net_pnl: float
    ) -> Dict[str, Any]:
        """
        Permutes asset columns across N draws to verify asset-specific alpha.
        Computes empirical p-value = P(Null Net PnL >= Candidate Net PnL).
        """
        n_bars, n_symbols = candidate_weights.shape
        null_pnls = np.zeros(self.n_draws)
        null_sharpes = np.zeros(self.n_draws)
        
        np.random.seed(self.seed)
        for d in range(self.n_draws):
            perm = np.random.permutation(n_symbols)
            w_null = candidate_weights[:, perm]
            res_null = simulator_fn(w_null)
            null_pnls[d] = res_null["net_pnl"]
            null_sharpes[d] = res_null["sharpe"]
            
        # Standard finite-sample permutation p-value: (count(Null >= Real) + 1) / (N + 1)
        p_val = float((np.sum(null_pnls >= candidate_net_pnl) + 1.0) / (self.n_draws + 1.0))
        
        return {
            "test_name": "Asset-Label Permutation Test",
            "n_draws": self.n_draws,
            "candidate_net_pnl": candidate_net_pnl,
            "empirical_p_value": p_val,
            "null_pnl_mean": float(np.mean(null_pnls)),
            "null_pnl_std": float(np.std(null_pnls)),
            "null_pnl_p95": float(np.percentile(null_pnls, 95)),
            "null_sharpe_mean": float(np.mean(null_sharpes)),
            "null_sharpe_p95": float(np.percentile(null_sharpes, 95)),
            "passed": bool(p_val < 0.01)  # Strict alpha gate: p < 0.01
        }

    def run_horizon_matched_random_null(
        self,
        candidate_weights: np.ndarray,
        valid_mask: np.ndarray,
        simulator_fn: Callable[[np.ndarray], Dict[str, Any]],
        candidate_net_pnl: float
    ) -> Dict[str, Any]:
        """
        Generates N random trading streams matching the candidate's exact active
        asset count and holding duration distribution.
        """
        n_bars, n_symbols = candidate_weights.shape
        null_pnls = np.zeros(self.n_draws)
        
        np.random.seed(self.seed + 100)
        
        # Precompute candidate active counts per bar
        active_counts = np.sum(candidate_weights != 0.0, axis=1)
        gross_weights = np.sum(np.abs(candidate_weights), axis=1)
        
        # Identify bars where the candidate actually rebalances
        is_rebal_bar = np.zeros(n_bars, dtype=bool)
        is_rebal_bar[0] = True
        for t in range(1, n_bars):
            if np.any(candidate_weights[t] != candidate_weights[t-1]):
                is_rebal_bar[t] = True
                
        for d in range(self.n_draws):
            w_rand = np.zeros_like(candidate_weights)
            current_w = np.zeros(n_symbols)
            for t in range(n_bars):
                if is_rebal_bar[t]:
                    current_w = np.zeros(n_symbols)
                    k = active_counts[t]
                    if k >= 2 and gross_weights[t] > 0:
                        avail = np.where(valid_mask[t])[0]
                        if len(avail) >= k:
                            chosen = np.random.choice(avail, size=k, replace=False)
                            half = k // 2
                            per_w = (gross_weights[t] / 2.0) / max(half, 1)
                            current_w[chosen[:half]] = per_w
                            current_w[chosen[half:2*half]] = -per_w
                w_rand[t] = current_w
                        
            res = simulator_fn(w_rand)
            null_pnls[d] = res["net_pnl"]
            
        # Standard finite-sample permutation p-value: (count(Null >= Real) + 1) / (N + 1)
        p_val = float((np.sum(null_pnls >= candidate_net_pnl) + 1.0) / (self.n_draws + 1.0))
        
        return {
            "test_name": "Horizon-Matched Random Null Test",
            "n_draws": self.n_draws,
            "candidate_net_pnl": candidate_net_pnl,
            "empirical_p_value": p_val,
            "null_pnl_mean": float(np.mean(null_pnls)),
            "null_pnl_p95": float(np.percentile(null_pnls, 95)),
            "passed": bool(p_val < 0.01)
        }

    def run_deterministic_placebos(
        self,
        candidate_weights: np.ndarray,
        simulator_fn: Callable[[np.ndarray], Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """Evaluates Sign Inversion, Time-Shift (+12h), and Idle Cash."""
        # Sign Inversion
        res_inv = simulator_fn(-1.0 * candidate_weights)
        
        # Time-Shift (+12h / 3 bars)
        w_shifted = np.roll(candidate_weights, 3, axis=0)
        w_shifted[:3] = 0.0
        res_shift = simulator_fn(w_shifted)
        
        # Idle Cash (zeros)
        w_cash = np.zeros_like(candidate_weights)
        res_cash = simulator_fn(w_cash)
        
        return {
            "sign_inversion": res_inv,
            "time_shifted": res_shift,
            "idle_cash": res_cash
        }
