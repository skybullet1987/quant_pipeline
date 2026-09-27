#!/usr/bin/env python3
"""
OBSERVABLE MICROSTRUCTURE REGIME DETECTOR & LIQUIDATION CIRCUIT BREAKER
========================================================================
Deterministic regime gating driven by observable, physical microstructure variables.
Replaces latent Hidden Markov Models (HMM) to eliminate transition lag, lookahead
smoothing traps, and state-flip turnover churn.

Monitored Physical Microstructure Variables:
1. Aggregate Open Interest Velocity (24h / 6-bar contraction):
   V_OI,t = (sum_i OI_i,t - sum_i OI_i,t-6) / (sum_i OI_i,t-6)
   - When V_OI < -10%, forced exchange liquidations are cascading through margin engines.
   - Triggers instantaneous circuit breaker: gross exposure on Tranche B cuts to 0.0x (cash),
     Tranche A cuts exposure by 50%.
2. Cross-Sectional Basis Dispersion:
   D_basis,t = std(Basis_1,t, ..., Basis_N,t)
   - When basis dispersion widens > 2.5 sigma, market-maker arbitrage has broken down.
3. Volatility-Scalable Exposure:
   - Inverse Parkinson/ATR scaling capping tail-risk exposure during panic regimes.
"""

from dataclasses import dataclass
from typing import Optional, Union, Dict, Any
import numpy as np
import pandas as pd


# Canonical Regime Identifiers
REGIME_LIQUIDATION_CASCADE = 0  # Circuit Breaker Active: Tranche B 0.0x, Tranche A 50%
REGIME_NORMAL_DISPERSION = 1     # Quiet / Mean-Reversion: Tranche A 1.0x, Tranche B 2.0x
REGIME_STRUCTURAL_MOMENTUM = 2   # Alt-Season / Runaway: Tranche B scales to 3.0x - 3.5x


@dataclass
class RegimeState:
    regime_id: int
    regime_name: str
    oi_velocity_24h: float
    basis_dispersion: float
    leverage_mult_tranche_a: float
    leverage_mult_tranche_b: float
    circuit_breaker_active: bool


class ObservableRegimeCircuitBreaker:
    """
    Deterministic regime gating driven by physical microstructure variables.
    Replaces latent HMM state filters to eliminate transition lag and state estimation inertia.
    """
    def __init__(
        self,
        oi_velocity_threshold: float = -0.10,  # -10% OI contraction in 24h
        basis_disp_zscore: float = 2.5,
        momentum_oi_threshold: float = 0.05,   # +5% OI expansion in 24h
    ):
        self.oi_velocity_threshold = oi_velocity_threshold
        self.basis_disp_zscore = basis_disp_zscore
        self.momentum_oi_threshold = momentum_oi_threshold
        self.rolling_disp_history: list = []

    def evaluate_regime(
        self,
        current_oi_series: Union[pd.Series, np.ndarray],
        historical_oi_6bars_ago: Union[pd.Series, np.ndarray],
        basis_cross_section: Union[pd.Series, np.ndarray],
    ) -> RegimeState:
        """
        Evaluates observable market regime at bar close t strictly causally.
        Returns complete RegimeState including leverage multipliers.
        """
        # Convert to numpy arrays if necessary
        oi_now = np.asarray(current_oi_series, dtype=float)
        oi_past = np.asarray(historical_oi_6bars_ago, dtype=float)
        basis = np.asarray(basis_cross_section, dtype=float)

        # 1. Physical Open Interest Velocity over 24h (6 x 4H bars)
        valid_now = ~np.isnan(oi_now)
        valid_past = ~np.isnan(oi_past)
        sum_now = np.sum(oi_now[valid_now]) if np.any(valid_now) else 0.0
        sum_past = np.sum(oi_past[valid_past]) if np.any(valid_past) else 0.0

        if sum_past > 1e-4:
            oi_velocity = float((sum_now - sum_past) / sum_past)
        else:
            oi_velocity = 0.0

        # 2. Cross-Sectional Basis Dispersion
        valid_basis = basis[~np.isnan(basis)]
        if len(valid_basis) >= 10:
            dispersion = float(np.std(valid_basis))
        else:
            dispersion = 0.0

        self.rolling_disp_history.append(dispersion)
        if len(self.rolling_disp_history) > 180:
            self.rolling_disp_history.pop(0)

        mean_disp = float(np.mean(self.rolling_disp_history)) if len(self.rolling_disp_history) > 0 else 0.0
        std_disp = float(np.std(self.rolling_disp_history)) + 1e-8 if len(self.rolling_disp_history) > 5 else 1.0

        # 3. Deterministic Microstructure Logic:
        # Case A: Liquidation Cascade (Circuit Breaker Active)
        # Immediate de-risking on aggressive forced liquidations or arbitrage collapse
        is_cascade = (oi_velocity < self.oi_velocity_threshold) or (
            len(self.rolling_disp_history) >= 30 and (dispersion - mean_disp) / std_disp > self.basis_disp_zscore
        )

        if is_cascade:
            return RegimeState(
                regime_id=REGIME_LIQUIDATION_CASCADE,
                regime_name="LIQUIDATION_CASCADE_CIRCUIT_BREAKER",
                oi_velocity_24h=oi_velocity,
                basis_dispersion=dispersion,
                leverage_mult_tranche_a=0.50,  # Cut Tranche A gross exposure by 50%
                leverage_mult_tranche_b=0.00,  # Tranche B completely exited to cash/stables
                circuit_breaker_active=True,
            )

        # Case B: Structural Momentum / Alt-Season (Healthy expansion)
        if oi_velocity > self.momentum_oi_threshold:
            return RegimeState(
                regime_id=REGIME_STRUCTURAL_MOMENTUM,
                regime_name="STRUCTURAL_MOMENTUM_EXPANSION",
                oi_velocity_24h=oi_velocity,
                basis_dispersion=dispersion,
                leverage_mult_tranche_a=1.00,
                leverage_mult_tranche_b=3.00,  # Scaled leverage for runaway compounding
                circuit_breaker_active=False,
            )

        # Case C: Normal / Tranquil Dispersion
        return RegimeState(
            regime_id=REGIME_NORMAL_DISPERSION,
            regime_name="NORMAL_DISPERSION",
            oi_velocity_24h=oi_velocity,
            basis_dispersion=dispersion,
            leverage_mult_tranche_a=1.00,
            leverage_mult_tranche_b=2.00,
            circuit_breaker_active=False,
        )
