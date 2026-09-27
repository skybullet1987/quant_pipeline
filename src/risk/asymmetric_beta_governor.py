"""
Asymmetric Long/Short Gearing & Random Matrix Theory (RMT) Beta Governor
========================================================================
Implements:
1. Pillar 1: Asymmetric directional decoupling based on HMM regime clarity (w_long = 0 in Chop/Bear).
2. Benchmark beta hedging: Neutralizes altcoin short portfolio beta via long BTC perps.
3. Pillar 4: Marchenko-Pastur RMT covariance denoising with market-mode detoning.
"""

from __future__ import annotations

import numpy as np
import scipy.linalg as la
import polars as pl


class RMTBetaGovernor:
    def __init__(self, n_assets: int = 50, lookback_t: int = 180):
        self.n_assets = n_assets
        self.lookback_t = lookback_t
        self.q_ratio = float(lookback_t) / max(float(n_assets), 1.0)

    def denoise_and_detone_covariance(self, return_matrix: np.ndarray) -> np.ndarray:
        """
        Cleans empirical covariance matrix:
        1. Decomposes correlation matrix and strips dominant market mode (lambda_1).
        2. Applies Marchenko-Pastur constant residual clipping to filter noise.
        3. Reconstructs positive semi-definite clean covariance matrix.
        """
        t_samples, n_dim = return_matrix.shape
        if t_samples <= n_dim:
            cov_sample = np.cov(return_matrix, rowvar=False)
            return cov_sample + 0.05 * np.eye(n_dim)

        q = float(t_samples) / float(n_dim)
        sample_cov = np.cov(return_matrix, rowvar=False)
        std_diag = np.sqrt(np.maximum(np.diag(sample_cov), 1e-8))
        inv_std = np.diag(1.0 / std_diag)
        corr = inv_std @ sample_cov @ inv_std

        # Spectral decomposition
        evals, evecs = la.eigh(corr)
        sort_indices = np.argsort(evals)[::-1]
        evals = np.maximum(evals[sort_indices], 1e-8)
        evecs = evecs[:, sort_indices]

        # 1. Market-Mode Detoning
        lambda_mkt = evals[0]
        v_mkt = evecs[:, 0:1]
        corr_detoned = corr - lambda_mkt * (v_mkt @ v_mkt.T)
        d_diag = np.sqrt(np.maximum(np.diag(corr_detoned), 1e-8))
        corr_detoned = corr_detoned / np.outer(d_diag, d_diag)
        np.fill_diagonal(corr_detoned, 1.0)

        # 2. Re-decompose detoned matrix for Marchenko-Pastur filtering
        evals_det, evecs_det = la.eigh(corr_detoned)
        sort_det = np.argsort(evals_det)[::-1]
        evals_det = np.maximum(evals_det[sort_det], 1e-8)
        evecs_det = evecs_det[:, sort_det]

        # Theoretical MP bounds
        sigma_sq = 1.0 - (lambda_mkt / float(n_dim))
        lambda_plus = sigma_sq * (1.0 + np.sqrt(1.0 / q)) ** 2

        # Targeted eigenvalue clipping
        clean_evals = evals_det.copy()
        noise_mask = clean_evals <= lambda_plus
        if np.any(noise_mask):
            mean_noise = np.mean(clean_evals[noise_mask])
            clean_evals[noise_mask] = mean_noise

        clean_corr_detoned = evecs_det @ np.diag(clean_evals) @ evecs_det.T
        np.fill_diagonal(clean_corr_detoned, 1.0)

        # 3. Re-inject market mode and scale back to covariance
        clean_corr = clean_corr_detoned + lambda_mkt * (v_mkt @ v_mkt.T)
        diag_inv = 1.0 / np.sqrt(np.maximum(np.diag(clean_corr), 1e-8))
        clean_corr = clean_corr * np.outer(diag_inv, diag_inv)
        np.fill_diagonal(clean_corr, 1.0)

        clean_cov = np.diag(std_diag) @ clean_corr @ np.diag(std_diag)
        return clean_cov

    def compute_asymmetric_hedge(
        self,
        short_weights: dict[str, float],
        alt_betas: dict[str, float],
        btc_beta: float = 1.0,
        regime_state: int = 1,
    ) -> float:
        """
        Calculates required BTC long hedge weight to neutralize short altcoin beta.
        - State 0 (Bull): eta = 1.00 (Complete market-squeeze protection)
        - State 1 (Chop): eta = 0.50 (Partial hedge preserving idiosyncratic short alpha)
        - State 2 (Bear): eta = 0.00 (Unhedged directional short)
        """
        eta_map = {0: 1.00, 1: 0.50, 2: 0.00}
        eta_hedge = eta_map.get(regime_state, 0.50)

        # Clip altcoin betas to prevent extreme tail outlier explosions (e.g. betas of 55x)
        total_short_notional = sum(abs(w) for w in short_weights.values())
        total_short_beta = sum(abs(w) * float(np.clip(alt_betas.get(s, 1.2), 0.50, 2.00)) for s, w in short_weights.items())
        required_btc_hedge = (total_short_beta / max(btc_beta, 0.80)) * eta_hedge
        # Immunization bound: hedge cannot exceed 1.25x short notional
        required_btc_hedge = min(required_btc_hedge, total_short_notional * 1.25)
        return float(required_btc_hedge)

    def allocate_asymmetric_portfolio(
        self,
        ranked_df: pl.DataFrame,
        regime_state: int,
        clarity_omega: float,
        target_gross_leverage: float,
        alt_betas: dict[str, float] | None = None,
    ) -> dict[str, float]:
        """
        Implements Pillar 1 Asymmetric Gearing:
        - Decouples long/short allocations.
        - In State 1 (Chop) & State 2 (Bear): ZERO altcoin longs to avoid -2.8 bps EV bleed.
        - In State 1: Active short book + 50% BTC hedge.
        - In State 2: Full active short book + 0% BTC hedge (unhedged bear ride).
        - In State 0 (Bull): Only take longs if clarity_omega > 0.65.
        """
        if alt_betas is None:
            alt_betas = {}

        weights: dict[str, float] = {}
        sym_col = "symbol" if "symbol" in ranked_df.columns else "ticker"
        score_col = "predicted_rank_score" if "predicted_rank_score" in ranked_df.columns else "score"

        # Sorted from highest alpha to lowest, excluding benchmark BTC
        sorted_df = ranked_df.sort(score_col, descending=True)
        raw_symbols = sorted_df[sym_col].to_list()
        symbols = [s for s in raw_symbols if s != "BTC"]
        if not symbols:
            return {}

        top_shorts = symbols[-4:]  # 4 highest-conviction short candidates

        if regime_state == 0 and clarity_omega > 0.65:
            # Bull Expansion with high clarity: take selective longs, modest shorts
            top_longs = symbols[:4]
            w_long = (target_gross_leverage * 0.70) / max(len(top_longs), 1)
            w_short = (target_gross_leverage * 0.30) / max(len(top_shorts), 1)
            for s in top_longs:
                weights[s] = round(w_long, 4)
            for s in top_shorts:
                weights[s] = round(-w_short, 4)

            # In State 0, 100% hedge short exposure with BTC
            short_sub = {s: weights[s] for s in top_shorts}
            btc_hedge = self.compute_asymmetric_hedge(short_sub, alt_betas, regime_state=0)
            if btc_hedge > 0.01:
                weights["BTC"] = round(weights.get("BTC", 0.0) + btc_hedge, 4)

        elif regime_state == 2:
            # Bear Breakdown: 100% directional short book, 0% altcoin longs, 0% BTC hedge
            w_short = target_gross_leverage / max(len(top_shorts), 1)
            for s in top_shorts:
                weights[s] = round(-w_short, 4)

        else:
            # State 1 (Sideways Chop / Transition):
            # NO altcoin longs. Capitalize on +102 bps short EV, hedged 50% with BTC
            short_scale = target_gross_leverage * max(0.50, (1.0 - clarity_omega * 0.5))
            w_short = short_scale / max(len(top_shorts), 1)
            for s in top_shorts:
                weights[s] = round(-w_short, 4)

            short_sub = {s: weights[s] for s in top_shorts}
            btc_hedge = self.compute_asymmetric_hedge(short_sub, alt_betas, regime_state=1)
            if btc_hedge > 0.01:
                weights["BTC"] = round(btc_hedge, 4)

        # Strictly enforce target gross leverage ceiling
        current_gross = sum(abs(w) for w in weights.values())
        if current_gross > target_gross_leverage and target_gross_leverage > 0:
            scale = target_gross_leverage / current_gross
            weights = {s: round(w * scale, 4) for s, w in weights.items()}

        return weights
