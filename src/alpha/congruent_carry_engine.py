"""
MOMENTUM-CONGRUENT CARRY BOOSTER & TOXIC FUNDING VETO
======================================================
Harmonizes directional fractional-differentiation momentum with funding carry:
  1. Toxic Funding Vetoes:
     - Longs vetoed if funding >= +0.010% per 8h (avoiding crowded long funding fee bleed).
     - Shorts vetoed if funding <= -0.005% per 8h (avoiding crowded short funding bleed).
  2. Congruent Carry Boosters:
     - Short side: If F_frac < 0 and funding >= +0.025% per 8h (> +27% APR cashflow),
       boost short score by -0.20 (more negative = higher conviction short).
     - Long side: If F_frac > 0 and funding <= -0.015% per 8h (receiving funding from shorts),
       boost long score by +0.20 (more positive = higher conviction long).
"""

import numpy as np


class CongruentCarryEngine:
    """Enhances directional momentum signals with trend-aligned funding yield."""

    def __init__(
        self,
        long_toxic_thresh: float = 0.00010,    # +10 bps / 8h
        short_toxic_thresh: float = -0.00005,  # -5 bps / 8h
        short_boost_thresh: float = 0.00025,   # +25 bps / 8h
        boost_magnitude: float = 0.20
    ):
        self.long_toxic_thresh = long_toxic_thresh
        self.short_toxic_thresh = short_toxic_thresh
        self.short_boost_thresh = short_boost_thresh
        self.boost_mag = boost_magnitude

    def compute_congruent_carry_scores(
        self,
        fracdiff_scores: np.ndarray,
        predicted_funding: np.ndarray,
        valid_mask: np.ndarray
    ) -> np.ndarray:
        """
        Transforms raw FracDiff momentum scores by applying toxic funding filters
        and adding congruent carry yield bonuses.
        
        Input shapes: (n_bars x n_symbols)
        """
        n_bars, n_symbols = fracdiff_scores.shape
        congruent_scores = fracdiff_scores.copy()

        for t in range(n_bars):
            m_t = valid_mask[t]
            if not np.any(m_t):
                continue

            f_t = predicted_funding[t]
            s_t = congruent_scores[t]

            # 1. Toxic Funding Penalization
            # Crowded Longs paying excessive funding to shorts
            toxic_longs = m_t & (s_t > 0) & (f_t >= self.long_toxic_thresh)
            congruent_scores[t, toxic_longs] = 0.0

            # Crowded Shorts paying excessive funding to longs
            toxic_shorts = m_t & (s_t < 0) & (f_t <= self.short_toxic_thresh)
            congruent_scores[t, toxic_shorts] = 0.0

            # 2. Congruent Carry Yield Bonus
            # Short momentum receiving high positive funding yield
            short_bonus = m_t & (s_t < 0) & (f_t >= self.short_boost_thresh)
            congruent_scores[t, short_bonus] -= self.boost_mag  # More negative

            # Long momentum receiving negative funding yield (shorts paying longs)
            long_bonus = m_t & (s_t > 0) & (f_t <= -0.00015)
            congruent_scores[t, long_bonus] += self.boost_mag   # More positive

        return congruent_scores
