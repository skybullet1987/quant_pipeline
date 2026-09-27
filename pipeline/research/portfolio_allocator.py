"""
Section 3.3: Shrunk Alpha Portfolio Allocator & Risk-Constrained Sizing.
Implements Ledoit-Wolf Covariance Inversion, Alpha Shrinkage, and Fractional Kelly Allocations.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np
from sklearn.covariance import LedoitWolf


@dataclass(frozen=True)
class PortfolioAllocationResult:
    weights: dict[str, float]       # Fractional weight per symbol (sum <= gross_exposure_cap)
    gross_leverage: float
    effective_alphas: dict[str, float]
    shrinkage_intensity: float


class ShrunkAlphaAllocator:
    def __init__(
        self,
        base_kelly: float = 0.25,        # Quarter-Kelly base conservative multiplier
        gamma_risk_aversion: float = 2.5,
        max_asset_weight: float = 0.15,   # Maximum single-asset concentration (15%)
        gross_exposure_cap: float = 1.50, # Section 5: Maximum gross portfolio leverage (1.5x)
    ):
        self.base_kelly = base_kelly
        self.gamma = gamma_risk_aversion
        self.max_asset_weight = max_asset_weight
        self.gross_exposure_cap = gross_exposure_cap

    def calculate_alpha_shrinkage(
        self,
        raw_alphas: np.ndarray,
        prior_variance: float = 0.0025,   # Estimated historical cross-sectional variance
    ) -> tuple[np.ndarray, float]:
        """Calculates Bayesian variance shrinkage factor lambda_mu."""
        sample_var = float(np.var(raw_alphas))
        if sample_var <= 1e-12:
            return np.zeros_like(raw_alphas), 0.0

        # lambda_mu = max(0.0, 1.0 - Var(mu_hat) / Var(mu_prior))
        # When sample noise dominates prior variance, alphas shrink to zero
        shrinkage_lambda = float(np.clip(1.0 - (sample_var / max(prior_variance, 1e-8)), 0.05, 1.0))
        mu_effective = shrinkage_lambda * raw_alphas
        return mu_effective, shrinkage_lambda

    def allocate(
        self,
        symbols: list[str],
        raw_alphas: np.ndarray,           # (N,) Expected returns from ML ensemble
        asset_returns_matrix: np.ndarray, # (T, N) Historical return window for covariance estimation
        m_regime: float = 1.0,            # Sizing multiplier from Regime Engine
        m_confidence: float = 1.0,        # Model confidence multiplier
    ) -> PortfolioAllocationResult:
        """
        Computes optimal risk-adjusted weights using Ledoit-Wolf shrunk covariance matrix.
        """
        n_assets = len(symbols)
        if n_assets == 0:
            return PortfolioAllocationResult({}, 0.0, {}, 0.0)

        # 1. Calculate Alpha Shrinkage
        mu_eff, shrink_lambda = self.calculate_alpha_shrinkage(raw_alphas)

        # 2. Fit Ledoit-Wolf Shrunk Covariance
        lw = LedoitWolf(assume_centered=False)
        lw.fit(asset_returns_matrix)
        sigma_lw = lw.covariance_

        # Add minor Tikhonov regularization on diagonal for numerical inversion stability
        reg_sigma = sigma_lw + 1e-6 * np.eye(n_assets)
        inv_sigma = np.linalg.pinv(reg_sigma)

        # 3. Dynamic Kelly Multiplier
        f_kelly = self.base_kelly * m_regime * m_confidence

        # 4. Unconstrained Mean-Variance Weights: w* = (1/gamma) * Sigma^(-1) * mu_eff * f_Kelly
        raw_weights = (1.0 / self.gamma) * np.dot(inv_sigma, mu_eff) * f_kelly

        # 5. Asset-Level Concentration Caps & Bounds
        clipped_weights = np.clip(raw_weights, -self.max_asset_weight, self.max_asset_weight)

        # 6. Portfolio-Level Gross Exposure Scaling
        gross_leverage = float(np.sum(np.abs(clipped_weights)))
        if gross_leverage > self.gross_exposure_cap:
            scale_factor = self.gross_exposure_cap / gross_leverage
            clipped_weights = clipped_weights * scale_factor
            gross_leverage = self.gross_exposure_cap

        weights_dict = {sym: float(w) for sym, w in zip(symbols, clipped_weights)}
        eff_alphas_dict = {sym: float(a) for sym, a in zip(symbols, mu_eff)}

        return PortfolioAllocationResult(
            weights=weights_dict,
            gross_leverage=gross_leverage,
            effective_alphas=eff_alphas_dict,
            shrinkage_intensity=shrink_lambda,
        )
