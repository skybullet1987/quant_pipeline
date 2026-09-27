"""
DYNAMIC GEARING & CUSHION GOVERNOR
===================================
Implements:
  1. Target Volatility Gearing:
     Scale_t = clamp(sigma_target / (sigma_port,t * sqrt(2190)), L_min, L_max)
  2. Continuous Grossman-Zhou (1993) Cushion Governance:
     C(t) = max(0, (NAV(t) - (1 - M) * HWM(t)) / (M * HWM(t)))
     L_eff(t) = L_min + (L_max - L_min) * C(t)^gamma
  3. Combined Vol-Target + GZ Cushion Risk Shield
"""

import math
from typing import Dict, Any, Optional
import numpy as np


class DynamicGearingGovernor:
    """Modulates portfolio leverage dynamically based on realized volatility and drawdown cushions."""

    def __init__(
        self,
        lookback_bars: int = 20,
        annualization_factor: float = math.sqrt(2190.0),  # 6 bars/day * 365 days
        m_drawdown_floor: float = 0.25,                  # 25% max target drawdown
        gamma_cushion: float = 0.75,
        default_l_min: float = 0.50,
        default_l_max: float = 1.80
    ):
        self.lookback_bars = lookback_bars
        self.ann_factor = annualization_factor
        self.m = m_drawdown_floor
        self.gamma = gamma_cushion
        self.l_min = default_l_min
        self.l_max = default_l_max

        # State tracking for continuous cushion
        self.hwm: float = 1.0
        self.nav: float = 1.0

    def reset_state(self, initial_nav: float = 1.0):
        self.hwm = initial_nav
        self.nav = initial_nav

    def update_nav(self, current_nav: float):
        self.nav = max(current_nav, 1e-6)
        if self.nav > self.hwm:
            self.hwm = self.nav

    def compute_vol_target_scale(
        self,
        recent_port_returns: np.ndarray,
        sigma_target: float,
        l_min: Optional[float] = None,
        l_max: Optional[float] = None
    ) -> float:
        """
        Computes the target volatility leverage multiplier.
        """
        min_l = l_min if l_min is not None else self.l_min
        max_l = l_max if l_max is not None else self.l_max

        if len(recent_port_returns) < 6:
            return 1.0

        # Exponentially weighted or sample volatility
        r = recent_port_returns[-self.lookback_bars:]
        sample_std = float(np.std(r, ddof=1)) if len(r) > 1 else 0.01
        realized_ann_vol = max(sample_std * self.ann_factor, 0.05)

        raw_scale = sigma_target / realized_ann_vol
        return float(np.clip(raw_scale, min_l, max_l))

    def compute_grossman_zhou_cushion(
        self,
        current_nav: Optional[float] = None,
        l_min: Optional[float] = None,
        l_max: Optional[float] = None,
        m_floor: Optional[float] = None,
        gamma_val: Optional[float] = None,
        accelerated_reentry: bool = False
    ) -> float:
        """
        Computes continuous Grossman-Zhou drawdown cushion leverage multiplier.
        """
        if current_nav is not None:
            self.update_nav(current_nav)

        min_l = l_min if l_min is not None else self.l_min
        max_l = l_max if l_max is not None else self.l_max
        m_eff = m_floor if m_floor is not None else self.m
        gamma_eff = gamma_val if gamma_val is not None else self.gamma

        # Floor boundary: (1 - M) * HWM
        floor_level = (1.0 - m_eff) * self.hwm
        cushion = max(0.0, (self.nav - floor_level) / (m_eff * self.hwm + 1e-8))
        cushion = min(1.0, cushion)

        if accelerated_reentry:
            # Accelerated curvature out of troughs: uses concave ramp sqrt(cushion)
            cushion = math.sqrt(cushion)

        # L_eff = L_min + (L_max - L_min) * C(t)^gamma
        l_eff = min_l + (max_l - min_l) * (cushion ** gamma_eff)
        return float(np.clip(l_eff, min_l, max_l))

    def compute_composite_risk_shield_leverage(
        self,
        recent_port_returns: np.ndarray,
        current_nav: float,
        sigma_target: float = 0.30,
        l_min: float = 0.50,
        l_max: float = 1.80,
        m_floor: Optional[float] = None,
        gamma_val: Optional[float] = None,
        accelerated_reentry: bool = False
    ) -> float:
        """
        Synthesizes Target Volatility Gearing and Grossman-Zhou Cushion Governance.
        """
        vol_scale = self.compute_vol_target_scale(recent_port_returns, sigma_target, l_min, l_max)
        gz_scale = self.compute_grossman_zhou_cushion(
            current_nav, l_min, l_max, m_floor=m_floor, gamma_val=gamma_val, accelerated_reentry=accelerated_reentry
        )

        # The composite leverage is constrained by the tighter of vol-scale and GZ cushion
        composite_lev = min(vol_scale, gz_scale)
        return float(np.clip(composite_lev, l_min, l_max))

