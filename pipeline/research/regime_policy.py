"""
Section 3.2: 2D Regime Engine & Directional Permission.
Translates HMM posteriors and BOCD hazard into continuous risk multipliers.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class RegimePolicyOutput:
    long_permission: float       # Continuous gate: 0.0 to 1.0
    short_permission: float      # Continuous gate: 0.0 to 1.0
    sizing_multiplier: float     # Kelly scale: 0.0 to 1.25
    regime_label: str


def evaluate_regime_policy(
    p_hazard: float,
    p_chop: float,
    p_trend: float,
    p_expansion: float,
    directional_impulse: float,
) -> RegimePolicyOutput:
    """
    Evaluates market state using BOCD change-point hazard and HMM state posteriors.
    """
    # 1. Structural Shock Check
    if p_hazard > 0.60:
        if abs(directional_impulse) > 1.8:
            # Confirmed Breakout: Permit trend direction, choke counter-trend
            if directional_impulse > 0:
                return RegimePolicyOutput(
                    long_permission=1.0,
                    short_permission=0.05,
                    sizing_multiplier=0.75,
                    regime_label="BREAKOUT_BULL",
                )
            else:
                return RegimePolicyOutput(
                    long_permission=0.05,
                    short_permission=1.0,
                    sizing_multiplier=0.75,
                    regime_label="BREAKOUT_BEAR",
                )
        else:
            # Chaotic Shock: Full defensive lockout
            return RegimePolicyOutput(
                long_permission=0.0,
                short_permission=0.0,
                sizing_multiplier=0.0,
                regime_label="CHAOTIC_SHOCK_LOCKOUT",
            )

    # 2. Standard Continuous Regime Sizing Multiplier
    m_regime = float(np.clip(0.50 * p_chop + 1.00 * p_trend + 1.20 * p_expansion, 0.25, 1.25))

    # Identify dominant state
    states = [("CHOP", p_chop), ("TREND", p_trend), ("EXPANSION", p_expansion)]
    dominant_state = max(states, key=lambda x: x[1])[0]

    return RegimePolicyOutput(
        long_permission=1.0,
        short_permission=1.0,
        sizing_multiplier=m_regime,
        regime_label=dominant_state,
    )
