#!/usr/bin/env python3
"""
LELAND OPTIMAL DEADBAND & MULTI-HORIZON EXECUTION ALLOCATOR
===========================================================
Implements the friction mitigation mechanisms from the Institutional Compounding Blueprint:
1. Leland Optimal No-Trade Buffer Zone (Rebalancing Deadband tau = 0.030 / 300 bps).
2. Multi-Horizon Exponential Moving Average Alpha Smoothing (12h, 36h, 72h).
3. Ledoit-Wolf Non-Linear Shrinkage & Inverse Volatility Risk Parity Weighting.
"""

import math
from typing import Dict, List, Tuple, Optional
import numpy as np
from sklearn.covariance import ledoit_wolf


class DeadbandExecutionAllocator:
    """Manages optimal trade buffer zones and multi-horizon portfolio allocation."""

    def __init__(
        self,
        deadband_base: float = 0.030,     # 300 bps baseline deadband
        smoothing_lambdas: Tuple[float, float, float] = (0.80, 0.92, 0.96), # 12h, 36h, 72h
        smoothing_weights: Tuple[float, float, float] = (0.50, 0.30, 0.20),
    ):
        self.deadband_base = deadband_base
        self.lambdas = smoothing_lambdas
        self.weights = smoothing_weights

    def apply_leland_deadband(
        self,
        target_weights: np.ndarray,
        current_weights: np.ndarray,
        tau: Optional[float] = None
    ) -> np.ndarray:
        """
        Applies the Leland / Garleanu-Pedersen optimal no-trade buffer operator:
            dw_exec = 0                                       if |w* - w_{t-1}| < tau
            dw_exec = w* - w_{t-1} - sign(w* - w_{t-1}) * tau if |w* - w_{t-1}| >= tau
        """
        tau_val = self.deadband_base if tau is None else tau
        delta_w = target_weights - current_weights
        abs_delta = np.abs(delta_w)
        
        # Execute only the portion that exceeds the deadband buffer
        dw_exec = np.where(
            abs_delta >= tau_val,
            delta_w - np.sign(delta_w) * tau_val,
            0.0
        )
        return current_weights + dw_exec

    def smooth_multi_horizon_alpha(
        self,
        raw_alpha_matrix: np.ndarray
    ) -> np.ndarray:
        """
        Applies multi-horizon exponential smoothing to filter discrete rebalancing noise:
            alpha_bar_t = sum_k w_k * alpha_tilde_t^{(k)}
        """
        n_bars, n_symbols = raw_alpha_matrix.shape
        smoothed_matrix = np.zeros_like(raw_alpha_matrix)
        
        # Track state for each decay horizon
        state_k = [np.zeros(n_symbols) for _ in self.lambdas]
        
        for t in range(n_bars):
            bar_raw = np.nan_to_num(raw_alpha_matrix[t], nan=0.0)
            combined_bar = np.zeros(n_symbols)
            
            for k, (lam, w_k) in enumerate(zip(self.lambdas, self.weights)):
                state_k[k] = lam * state_k[k] + (1.0 - lam) * bar_raw
                combined_bar += w_k * state_k[k]
                
            smoothed_matrix[t] = combined_bar
            
        return smoothed_matrix

    @staticmethod
    def compute_risk_parity_weights(
        scores: np.ndarray,
        valid_idx: np.ndarray,
        recent_returns: np.ndarray,
        top_k: int = 15,
        target_gross_leverage: float = 1.50
    ) -> np.ndarray:
        """
        Selects top_k longs and top_k shorts, weighted via Ledoit-Wolf shrunk inverse volatility:
        w_i proportional to 1 / sigma_i, normalized to sum(w_long) = L/2, sum(w_short) = -L/2.
        """
        n_symbols = len(scores)
        weights = np.zeros(n_symbols, dtype=np.float64)
        
        if len(valid_idx) < (top_k * 2):
            return weights
            
        valid_scores = scores[valid_idx]
        sorted_order = np.argsort(valid_scores)
        
        short_picks = valid_idx[sorted_order[:top_k]]
        long_picks = valid_idx[sorted_order[-top_k:]]
        
        # Calculate asset realized volatilities from recent returns (e.g. last 36 bars)
        if recent_returns.shape[0] >= 12:
            try:
                # Ledoit-Wolf shrinkage on selected assets
                selected = np.concatenate([long_picks, short_picks])
                lw_cov, _ = ledoit_wolf(recent_returns[:, selected])
                vols = np.sqrt(np.diag(lw_cov)) + 1e-6
                inv_vols_long = 1.0 / vols[:top_k]
                inv_vols_short = 1.0 / vols[top_k:]
            except Exception:
                inv_vols_long = np.ones(top_k)
                inv_vols_short = np.ones(top_k)
        else:
            inv_vols_long = np.ones(top_k)
            inv_vols_short = np.ones(top_k)
            
        # Normalize to target gross leverage
        half_lev = target_gross_leverage / 2.0
        w_long = (inv_vols_long / np.sum(inv_vols_long)) * half_lev
        w_short = (inv_vols_short / np.sum(inv_vols_short)) * half_lev
        
        weights[long_picks] = w_long
        weights[short_picks] = -w_short
        return weights
