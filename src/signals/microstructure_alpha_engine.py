"""
High-Information Microstructure Alpha Signals Engine
===================================================
Implements Pillar 3 of the 10x Convex Compounding Architecture:
1. Liquidation Cluster Absorption (LCA) - Detects V-bottom selling exhaustion.
2. Funding Velocity Divergence (FVD) - Disconnects between price momentum and leverage accumulation.
3. Multi-Level Order Flow Imbalance (MLOFI) & Taker Volume Skew (TVS) - Defensive ALO quoting offsets.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


class MicrostructureAlphaEngine:
    def __init__(self, book_depth_levels: int = 5):
        self.levels = book_depth_levels

    def compute_liquidation_cluster_absorption(
        self,
        liq_volume_usd: float,
        depth_0_5_pct_usd: float,
        delta_p_abs: float,
        atr: float,
        delta_oi_ratio: float,
        theta_oi: float = 0.02,
    ) -> float:
        """
        Detects exhaustion of aggressive forced liquidations absorbed by passive liquidity.
        LCA spikes only when large liquidation volume is absorbed with minimal price displacement.
        """
        if depth_0_5_pct_usd <= 0.0 or atr <= 0.0:
            return 0.0

        if delta_oi_ratio >= -theta_oi:
            return 0.0

        volume_ratio = np.log1p(liq_volume_usd / depth_0_5_pct_usd)
        price_displacement_penalty = np.exp(-delta_p_abs / atr)
        lca = volume_ratio * price_displacement_penalty
        return float(lca)

    def compute_funding_velocity_divergence(
        self,
        price_series: pd.Series,
        funding_series: pd.Series,
        lookback_k: int = 24,
    ) -> tuple[pd.Series, pd.Series, pd.Series]:
        """
        Computes Funding Velocity (V_f), Price Velocity (V_p), and FVD = Z(V_p) - Z(V_f).
        FVD > 0: Healthy spot accumulation.
        FVD < 0: Dangerous speculative perpetual leverage build susceptible to cascade.
        """
        f_mean = funding_series.rolling(window=lookback_k, min_periods=4).mean()
        f_std = funding_series.rolling(window=lookback_k, min_periods=4).std().replace(0, 1e-8)
        v_f = (funding_series - f_mean) / f_std

        p_delta = price_series - price_series.shift(lookback_k)
        p_std = price_series.rolling(window=lookback_k, min_periods=4).std().replace(0, 1e-8)
        v_p = p_delta / p_std

        fvd = v_p - v_f
        return v_p, v_f, fvd

    def compute_mlofi_quoting_offset(
        self,
        bid_px: np.ndarray,
        bid_sz: np.ndarray,
        ask_px: np.ndarray,
        ask_sz: np.ndarray,
        prev_bid_px: np.ndarray,
        prev_bid_sz: np.ndarray,
        prev_ask_px: np.ndarray,
        prev_ask_sz: np.ndarray,
        taker_vol_skew: float = 0.0,
        gk_volatility: float = 0.02,
    ) -> float:
        """
        Multi-Level OFI Quoting Defense:
        Calculates optimal limit price offset from mid for Add-Liquidity-Only (ALO) orders.
        Expands away from the market when toxic order flow is detected, tightens during stable books.
        """
        ofi_levels = np.zeros(self.levels)
        for m in range(min(self.levels, len(bid_px))):
            # Bid level flow
            if bid_px[m] > prev_bid_px[m]:
                delta_bid = bid_sz[m]
            elif bid_px[m] == prev_bid_px[m]:
                delta_bid = bid_sz[m] - prev_bid_sz[m]
            else:
                delta_bid = -prev_bid_sz[m]

            # Ask level flow
            if ask_px[m] < prev_ask_px[m]:
                delta_ask = ask_sz[m]
            elif ask_px[m] == prev_ask_px[m]:
                delta_ask = ask_sz[m] - prev_ask_sz[m]
            else:
                delta_ask = -prev_ask_sz[m]

            ofi_levels[m] = delta_bid - delta_ask

        decay_weights = np.exp(-np.arange(self.levels) * 0.5)
        decay_weights /= np.sum(decay_weights)
        mlofi_scalar = np.dot(ofi_levels, decay_weights)

        # Base offset (4 bps baseline)
        delta_base = 0.0004
        k1 = 0.0001
        k2 = 0.0002
        k3 = 0.50

        offset = delta_base - (k1 * np.tanh(mlofi_scalar)) - (k2 * taker_vol_skew) + (k3 * gk_volatility)
        return float(np.clip(offset, 0.0001, 0.0050))
