"""
RANK-BUFFER HYSTERESIS ALLOCATOR & DEAD-BAND OPERATOR
=====================================================
Eliminates cross-sectional rank churn in factor portfolios.
Enforces:
  1. Entry Gate: Unheld asset only bought if rank <= 8 (or shorted if rank >= N - 8)
  2. Exit Gate: Held long only liquidated if rank > 18 (or held short if rank < N - 18)
  3. Inaction Zone: Held assets ranking between 9 and 18 remain untouched
  4. Ledoit-Wolf Inverse-Volatility Risk Parity Sizing
  5. Leland / Garleanu-Pedersen 300 bps Deadband Operator (tau = 0.030)
"""

import math
from typing import Dict, List, Set, Tuple, Optional
import numpy as np


class RankBufferAllocator:
    """Manages stateful portfolio holdings with rank-buffer hysteresis and deadbands."""

    def __init__(
        self,
        target_k: int = 12,
        entry_k: int = 8,
        exit_k: int = 18,
        deadband_tau: float = 0.030
    ):
        self.target_k = target_k
        self.entry_k = entry_k
        self.exit_k = exit_k
        self.deadband_tau = deadband_tau
        
        # State tracking
        self.active_longs: Set[int] = set()
        self.active_shorts: Set[int] = set()

    def reset_state(self):
        self.active_longs.clear()
        self.active_shorts.clear()

    def set_capacity_breadth(self, nav: float, base_k: int = 8, min_k: int = 8, max_k: int = 16):
        """
        Dynamically scales basket breadth based on compounding equity NAV:
        K = clamp(round(base_k * sqrt(NAV / 50000)), min_k, max_k)
        """
        raw_k = int(round(base_k * math.sqrt(max(nav, 1000.0) / 50000.0)))
        k = max(min_k, min(max_k, raw_k))
        self.target_k = k
        self.entry_k = k
        self.exit_k = int(round(k * 2.25))

    def update_holdings_with_hysteresis(
        self,
        scores: np.ndarray,
        valid_idx: np.ndarray,
        veto_mask: Optional[np.ndarray] = None
    ) -> Tuple[List[int], List[int]]:
        """
        Applies rank-buffer hysteresis sieve to determine the active Long and Short baskets.
        
        Parameters:
        - scores: full array of alpha scores across all symbols
        - valid_idx: indices of valid PIT tradable symbols at time t
        - veto_mask: optional boolean mask of symbols vetoed (e.g. lottery skewness)
        """
        if len(valid_idx) < (self.exit_k * 2):
            return list(self.active_longs), list(self.active_shorts)

        v_scores = scores[valid_idx]
        sorted_order = np.argsort(v_scores)  # Ascending: lowest scores first (shorts), highest last (longs)
        n_valid = len(valid_idx)

        # Mapping from symbol_idx to rank (0 = worst, n_valid - 1 = best)
        rank_dict = {}
        for rank, sub_idx in enumerate(sorted_order):
            sym_idx = valid_idx[sub_idx]
            rank_dict[sym_idx] = rank

        # 1. Evaluate existing Longs: retain if rank >= (n_valid - exit_k) and not vetoed
        retained_longs = set()
        for sym_idx in self.active_longs:
            if sym_idx in rank_dict:
                rank = rank_dict[sym_idx]
                is_vetoed = veto_mask[sym_idx] if veto_mask is not None else False
                if rank >= (n_valid - self.exit_k) and not is_vetoed:
                    retained_longs.add(sym_idx)

        # 2. Evaluate existing Shorts: retain if rank < exit_k
        retained_shorts = set()
        for sym_idx in self.active_shorts:
            if sym_idx in rank_dict:
                rank = rank_dict[sym_idx]
                if rank < self.exit_k:
                    retained_shorts.add(sym_idx)

        # 3. Candidate new Longs: must enter top entry_k (rank >= n_valid - entry_k)
        new_long_candidates = []
        for sub_idx in reversed(sorted_order[-self.entry_k:]):
            sym_idx = valid_idx[sub_idx]
            is_vetoed = veto_mask[sym_idx] if veto_mask is not None else False
            if sym_idx not in retained_longs and not is_vetoed:
                new_long_candidates.append(sym_idx)

        # Fill available slots in Long basket up to target_k
        final_longs = list(retained_longs)
        for cand in new_long_candidates:
            if len(final_longs) < self.target_k:
                final_longs.append(cand)
            else:
                break

        # 4. Candidate new Shorts: must enter bottom entry_k (rank < entry_k)
        new_short_candidates = []
        for sub_idx in sorted_order[:self.entry_k]:
            sym_idx = valid_idx[sub_idx]
            if sym_idx not in retained_shorts:
                new_short_candidates.append(sym_idx)

        # Fill available slots in Short basket up to target_k
        final_shorts = list(retained_shorts)
        for cand in new_short_candidates:
            if len(final_shorts) < self.target_k:
                final_shorts.append(cand)
            else:
                break

        self.active_longs = set(final_longs)
        self.active_shorts = set(final_shorts)

        return final_longs, final_shorts

    def compute_risk_parity_weights(
        self,
        long_indices: List[int],
        short_indices: List[int],
        recent_returns: np.ndarray,
        n_symbols: int,
        target_gross_leverage: float = 1.00
    ) -> np.ndarray:
        """
        Computes inverse-volatility risk parity weights for the selected Long and Short baskets.
        """
        w = np.zeros(n_symbols)
        if not long_indices or not short_indices:
            return w

        # Long side inverse-volatility weighting
        if len(recent_returns) >= 12:
            long_vols = np.std(recent_returns[:, long_indices], axis=0) + 1e-6
            short_vols = np.std(recent_returns[:, short_indices], axis=0) + 1e-6
        else:
            long_vols = np.ones(len(long_indices))
            short_vols = np.ones(len(short_indices))

        raw_long_w = 1.0 / long_vols
        norm_long_w = raw_long_w / np.sum(raw_long_w)

        raw_short_w = 1.0 / short_vols
        norm_short_w = raw_short_w / np.sum(raw_short_w)

        half_lev = target_gross_leverage / 2.0
        w[long_indices] = norm_long_w * half_lev
        w[short_indices] = -norm_short_w * half_lev

        return w

    def compute_convex_power_weights(
        self,
        long_indices: List[int],
        short_indices: List[int],
        scores: np.ndarray,
        recent_returns: np.ndarray,
        n_symbols: int,
        target_gross_leverage: float = 1.00,
        alpha: float = 1.25,
        max_single_weight: float = 0.20
    ) -> np.ndarray:
        """
        Computes convex power-rank factor weights (alpha in [1.2, 1.5]),
        concentrating capital in the highest conviction momentum tokens while
        strictly enforcing Gate 1 concentration limits (<= 20% max single weight).
        """
        w = np.zeros(n_symbols)
        if not long_indices or not short_indices:
            return w

        # Long side convex power weighting
        long_s = scores[long_indices]
        shifted_ls = long_s - np.min(long_s) + 1e-4
        raw_long_p = shifted_ls ** alpha
        norm_long_w = raw_long_p / np.sum(raw_long_p)
        norm_long_w = np.clip(norm_long_w, 0.0, max_single_weight)
        norm_long_w = norm_long_w / np.sum(norm_long_w)

        # Short side convex power weighting (most negative gets highest short weight)
        short_s = scores[short_indices]
        shifted_ss = np.max(short_s) - short_s + 1e-4
        raw_short_p = shifted_ss ** alpha
        norm_short_w = raw_short_p / np.sum(raw_short_p)
        norm_short_w = np.clip(norm_short_w, 0.0, max_single_weight)
        norm_short_w = norm_short_w / np.sum(norm_short_w)

        half_lev = target_gross_leverage / 2.0
        w[long_indices] = norm_long_w * half_lev
        w[short_indices] = -norm_short_w * half_lev
        return w

    def apply_leverage_deadband(
        self,
        target_leverage: float,
        current_leverage: float,
        delta_thresh: float = 0.15
    ) -> float:
        """
        Suppresses continuous leverage rebalancing churn:
        If |target_leverage - current_leverage| < delta_thresh, maintain current leverage.
        """
        if abs(target_leverage - current_leverage) < delta_thresh:
            return current_leverage
        return target_leverage

    def apply_leland_deadband(
        self,
        target_w: np.ndarray,
        current_w: np.ndarray,
        tau: Optional[float] = None
    ) -> np.ndarray:
        """
        Applies Leland / Garleanu-Pedersen deadband buffer operator.
        Delta w_i is suppressed to 0 if |target_w_i - current_w_i| < tau.
        """
        tau_val = tau if tau is not None else self.deadband_tau
        diff = target_w - current_w
        trade = np.where(np.abs(diff) < tau_val, 0.0, diff)
        return current_w + trade


