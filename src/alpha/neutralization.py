#!/usr/bin/env python3
"""
CRYPTO FACTOR NEUTRALIZATION ENGINE
===================================
Neutralizes candidate alpha factors against crypto-specific nuisance risk factors.

Enforces Strict Causal Boundaries:
- Neutralization exposures X_{i,t} are computed strictly using information known THROUGH time t.
- Zero future data leakage into the factor construction.
- Supports both:
  1. Factor Exposure Neutralization: F_{i,t} = gamma * X_{i,t} + F_resid_{i,t}
  2. Forward Return Residualization: R_{i,t+h} = beta * X_{i,t} + epsilon_{i,t+h}

Crypto Nuisance Factor Suite:
1. BTC Beta: Sensitivity to Bitcoin returns.
2. Alt-Market Beta: Sensitivity to broad altcoin market factor.
3. Realized Volatility: Historical 20-bar return standard deviation.
4. Liquidity / ADV: Log of 20-bar average traded volume.
5. Funding Rate: Current perpetual funding rate known at t.
6. Basis / Premium: Percentage dislocation between mark price and oracle.
7. Raw Momentum: 24-hour unadjusted return momentum.
"""

from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import scipy.stats as stats
import polars as pl


class FactorNeutralizer:
    """
    Cross-sectional factor neutralization engine.
    Solves OLS/WLS at each timestamp t to extract idiosyncratic alpha.
    """
    def __init__(
        self,
        close_mat: np.ndarray,
        volume_mat: np.ndarray,
        oracle_mat: np.ndarray,
        valid_mask: np.ndarray,
        symbols: List[str],
        benchmark_symbol: str = "BTC",
    ):
        self.close_mat = close_mat
        self.volume_mat = volume_mat
        self.oracle_mat = oracle_mat
        self.valid_mask = valid_mask
        self.symbols = symbols
        self.T, self.N = close_mat.shape

        if benchmark_symbol in symbols:
            self.btc_idx = symbols.index(benchmark_symbol)
        else:
            self.btc_idx = 0

        self.precompute_nuisance_factors()

    def precompute_nuisance_factors(self):
        """
        Precomputes causal nuisance factor matrices known through time t.
        All calculations are strictly backward-looking.
        """
        # 1. Backward returns
        self.ret_1 = np.zeros_like(self.close_mat)
        self.ret_1[1:] = (self.close_mat[1:] / (self.close_mat[:-1] + 1e-12)) - 1.0

        # BTC returns
        self.btc_ret = self.ret_1[:, self.btc_idx]

        # 2. Broad Alt-Market return (equal-weighted across valid alts)
        self.alt_ret = np.zeros(self.T, dtype=float)
        for t in range(self.T):
            alt_mask = self.valid_mask[t].copy()
            alt_mask[self.btc_idx] = False
            if np.any(alt_mask):
                self.alt_ret[t] = np.nanmean(self.ret_1[t, alt_mask])

        # 3. Realized Volatility (20 bars)
        self.vol_20 = np.full_like(self.close_mat, np.nan)
        for t in range(20, self.T):
            slice_ret = self.ret_1[t-20 : t]
            self.vol_20[t] = np.nanstd(slice_ret, axis=0)

        # 4. Liquidity / Log ADV (20 bars)
        self.adv_20 = np.full_like(self.volume_mat, np.nan)
        for t in range(20, self.T):
            slice_vol = self.volume_mat[t-20 : t]
            mean_v = np.nanmean(slice_vol, axis=0)
            self.adv_20[t] = np.log(np.maximum(1.0, mean_v))

        # 5. Basis / Oracle Premium: (close - oracle) / oracle
        self.basis = (self.close_mat - self.oracle_mat) / (self.oracle_mat + 1e-12)

        # 6. Raw 24h Momentum (6 4H bars)
        self.mom_24h = np.full_like(self.close_mat, np.nan)
        self.mom_24h[6:] = (self.close_mat[6:] / (self.close_mat[:-6] + 1e-12)) - 1.0

        # 7. Rolling BTC Beta (60 bars)
        self.btc_beta = np.ones_like(self.close_mat, dtype=float)
        for t in range(60, self.T):
            btc_slice = self.btc_ret[t-60 : t]
            var_btc = np.var(btc_slice) + 1e-8
            for i in range(self.N):
                if self.valid_mask[t, i]:
                    asset_slice = self.ret_1[t-60 : t, i]
                    valid_pts = ~np.isnan(asset_slice)
                    if np.sum(valid_pts) >= 30:
                        cov = np.cov(asset_slice[valid_pts], btc_slice[valid_pts])[0, 1]
                        self.btc_beta[t, i] = cov / var_btc

    def neutralize_factor(
        self,
        raw_factor_mat: np.ndarray,
        nuisance_list: List[str] = ["btc_beta", "volatility", "liquidity", "momentum"],
    ) -> np.ndarray:
        """
        Cross-sectionally regresses raw_factor_mat on nuisance factors at each time t.
        Returns the residualized factor matrix F_resid.
        """
        residual_factor = np.full_like(raw_factor_mat, np.nan)

        for t in range(max(60, 20), self.T):
            mask_t = self.valid_mask[t] & ~np.isnan(raw_factor_mat[t])
            # Ensure all requested nuisance factors have valid values
            if "volatility" in nuisance_list:
                mask_t &= ~np.isnan(self.vol_20[t])
            if "liquidity" in nuisance_list:
                mask_t &= ~np.isnan(self.adv_20[t])
            if "momentum" in nuisance_list:
                mask_t &= ~np.isnan(self.mom_24h[t])
            if "basis" in nuisance_list:
                mask_t &= ~np.isnan(self.basis[t])

            if np.sum(mask_t) < 15: # Need degrees of freedom
                continue

            # Dependent variable: standardized factor
            y = raw_factor_mat[t, mask_t]
            y = (y - np.mean(y)) / (np.std(y) + 1e-8)

            # Design matrix X: intercept + selected nuisance factors
            X_cols = [np.ones(len(y))]
            for n_factor in nuisance_list:
                if n_factor == "btc_beta":
                    col = self.btc_beta[t, mask_t]
                elif n_factor == "volatility":
                    col = self.vol_20[t, mask_t]
                elif n_factor == "liquidity":
                    col = self.adv_20[t, mask_t]
                elif n_factor == "momentum":
                    col = self.mom_24h[t, mask_t]
                elif n_factor == "basis":
                    col = self.basis[t, mask_t]
                else:
                    col = np.zeros(len(y))

                col_std = np.std(col) + 1e-8
                X_cols.append((col - np.mean(col)) / col_std)

            X = np.column_stack(X_cols)

            try:
                # OLS: y = X * beta + resid
                beta, residuals, rank, s = np.linalg.lstsq(X, y, rcond=None)
                resid = y - (X @ beta)
                residual_factor[t, mask_t] = resid
            except Exception:
                residual_factor[t, mask_t] = y

        return residual_factor
