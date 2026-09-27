"""
ORTHOGONAL ALPHA ENSEMBLE & EXHAUSTION FADER
=============================================
Implements:
  1. Multi-Memory FracDiff Ensemble:
     Fast (d=0.45, H=12), Medium (d=0.38, H=18), Slow (d=0.28, H=36)
  2. Lottery Skewness & Memecoin Toxic Flow Veto (S_eps > 1.50)
  3. Exhaustion Wick Fader (Monetizes Failed Breakouts via Maker ALO Orders)
"""

import math
from typing import Dict, Tuple, List, Optional
import numpy as np
from scipy import stats

from src.alpha.fracdiff_orthogonal_engine import (
    compute_fracdiff_weights,
    apply_fractional_differentiation,
    compute_multi_beta_residual_momentum,
)


class OrthogonalAlphaEnsemble:
    """Computes multi-horizon fractional diff composites, lottery vetoes, and wick faders."""

    def __init__(self):
        # Weights for multi-memory composite
        self.w_fast = 0.30
        self.w_med = 0.45
        self.w_slow = 0.25

    def compute_multi_memory_fracdiff_composite(
        self,
        close_mat: np.ndarray,
        valid_mask: np.ndarray,
        btc_idx: int,
        eth_idx: int
    ) -> np.ndarray:
        """
        Computes the multi-horizon fractional differentiation ensemble:
        Fast: d=0.45, H=12
        Med:  d=0.38, H=18
        Slow: d=0.28, H=36
        """
        n_bars, n_symbols = close_mat.shape

        def get_fd_signal(d_val: float, h_val: int) -> np.ndarray:
            fd_series = apply_fractional_differentiation(close_mat, d=d_val, max_len=h_val)
            fd_diff = fd_series - np.roll(fd_series, 1, axis=0)
            fd_diff[0] = 0.0
            sig, _ = compute_multi_beta_residual_momentum(
                fd_diff, fd_diff[:, btc_idx], fd_diff[:, eth_idx], valid_mask, lookback_h=h_val
            )
            return sig

        print("    [Ensemble] Computing Fast Horizon (d=0.45, H=12)...")
        f_fast = get_fd_signal(0.45, 12)

        print("    [Ensemble] Computing Medium Horizon (d=0.38, H=18)...")
        f_med = get_fd_signal(0.38, 18)

        print("    [Ensemble] Computing Slow Horizon (d=0.28, H=36)...")
        f_slow = get_fd_signal(0.28, 36)

        composite = np.zeros((n_bars, n_symbols))
        for t in range(n_bars):
            m_t = valid_mask[t]
            if np.sum(m_t) >= 10:
                v_idx = np.where(m_t)[0]

                # Standardize each horizon cross-sectionally
                def standardize(arr):
                    sub = arr[v_idx]
                    s_std = np.std(sub)
                    return (sub - np.mean(sub)) / (s_std + 1e-8) if s_std > 1e-8 else sub

                z_fast = standardize(f_fast[t])
                z_med = standardize(f_med[t])
                z_slow = standardize(f_slow[t])

                comp_v = self.w_fast * z_fast + self.w_med * z_med + self.w_slow * z_slow
                composite[t, v_idx] = comp_v

        return composite

    def compute_lottery_skewness_veto_mask(
        self,
        residuals: np.ndarray,
        close_mat: np.ndarray,
        valid_mask: np.ndarray,
        lookback_bars: int = 180,  # 30 days
        skew_threshold: float = 1.50
    ) -> np.ndarray:
        """
        Computes a boolean mask (n_bars, n_symbols) where True indicates an asset
        exhibits extreme positive lottery skewness + rapid expansion (toxic flow).
        Such assets are vetoed from the Long portfolio.
        """
        n_bars, n_symbols = residuals.shape
        veto_mask = np.zeros((n_bars, n_symbols), dtype=bool)

        # Precompute ATR-like 14-bar range
        prev_close = np.roll(close_mat, 1, axis=0)
        returns_mat = np.nan_to_num(np.where(prev_close > 0, (close_mat / prev_close) - 1.0, 0.0))
        returns_mat[0] = 0.0

        for t in range(lookback_bars, n_bars):
            m_t = valid_mask[t]
            if not np.any(m_t):
                continue
            sub_res = residuals[t - lookback_bars : t]
            s_vals = stats.skew(sub_res, axis=0)

            # 24-hour return & 14-bar ATR range (vectorized)
            ret_24h = (close_mat[t] - close_mat[max(0, t - 6)]) / (close_mat[max(0, t - 6)] + 1e-8)
            atr_14 = np.mean(np.abs(returns_mat[max(0, t - 14) : t]), axis=0) + 1e-6

            veto_mask[t] = m_t & (s_vals > skew_threshold) & (ret_24h > (3.5 * atr_14))

        return veto_mask

    def compute_exhaustion_wick_fader_weights(
        self,
        residuals: np.ndarray,
        close_mat: np.ndarray,
        volume_mat: np.ndarray,
        valid_mask: np.ndarray,
        fader_allocation: float = 0.15
    ) -> np.ndarray:
        """
        Monetizes breakout failures by shorting tokens with severe 24h residual overextension
        (eps_24h > +3.0 * ATR) on decelerating volume.
        Allocates negative weight (passive short) with quick 2-4 bar holding horizon.
        """
        n_bars, n_symbols = residuals.shape
        fader_weights = np.zeros((n_bars, n_symbols))

        prev_close = np.roll(close_mat, 1, axis=0)
        returns_mat = np.nan_to_num(np.where(prev_close > 0, (close_mat / prev_close) - 1.0, 0.0))
        returns_mat[0] = 0.0

        # Precompute rolling indicator matrices vectorized
        atr_14_mat = np.zeros_like(returns_mat)
        res_24h_mat = np.zeros_like(residuals)
        vol_recent_mat = np.zeros_like(volume_mat)
        vol_baseline_mat = np.zeros_like(volume_mat)

        for t in range(14, n_bars):
            atr_14_mat[t] = np.mean(np.abs(returns_mat[t - 14 : t]), axis=0) + 1e-6
        for t in range(6, n_bars):
            res_24h_mat[t] = np.sum(residuals[t - 6 : t], axis=0)
        for t in range(12, n_bars):
            vol_recent_mat[t] = np.mean(volume_mat[t - 2 : t], axis=0)
            vol_baseline_mat[t] = np.mean(volume_mat[t - 12 : t], axis=0) + 1e-6

        active_fades: Dict[int, int] = {}  # sym_idx -> bars_held

        for t in range(24, n_bars):
            to_remove = [s for s, b in active_fades.items() if b >= 3 or not valid_mask[t, s]]
            for s in to_remove:
                del active_fades[s]
            for s in active_fades:
                active_fades[s] += 1

            # Vectorized candidate selection
            is_exhaustion = (
                valid_mask[t] &
                (res_24h_mat[t] > 3.0 * atr_14_mat[t]) &
                (vol_recent_mat[t] < vol_baseline_mat[t])
            )
            for c in np.where(is_exhaustion)[0]:
                if c not in active_fades:
                    active_fades[c] = 0

            if active_fades:
                fade_syms = list(active_fades.keys())
                fader_weights[t, fade_syms] = -fader_allocation / len(fade_syms)

        return fader_weights
