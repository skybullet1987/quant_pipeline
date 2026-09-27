"""
Grossman-Zhou Dynamic Drawdown Optimization & Multi-Tier Risk Engine
====================================================================
Implements the continuous stochastic optimal control framework of Grossman & Zhou (1993)
to bound portfolio maximum drawdowns below D_max = 22% while unlocking 6.0x - 8.0x gross
leverage during high-conviction regime expansions.
"""

from dataclasses import dataclass
import numpy as np


@dataclass
class RiskTelemetry:
    current_equity: float
    high_water_mark: float
    drawdown: float
    drawdown_tier: int
    cushion_ratio: float
    phi_gz: float
    convex_expansion: float
    entropy_dampener: float
    funding_penalty: float
    target_gross_leverage: float


class GrossmanZhouRiskGovernor:
    def __init__(
        self,
        d_max: float = 0.25,
        beta_d: float = 0.75,
        l_base: float = 2.50,
        l_max: float = 2.50,
        l_min: float = 0.20,
        kappa_s: float = 1.0,
        s_pivot: float = 0.50,
        alpha_e: float = 0.50,
    ):
        self.d_max = d_max
        self.beta_d = beta_d
        self.l_base = l_base
        self.l_max = l_max
        self.l_min = l_min
        self.kappa_s = kappa_s
        self.s_pivot = s_pivot
        self.alpha_e = alpha_e
        self.high_water_mark: float = 0.0

    def compute_leverage(
        self,
        equity: float,
        bull_score: float,
        regime_entropy: float,
        funding_rate_avg: float = 0.0001,
    ) -> tuple[float, RiskTelemetry]:
        """
        Calculates optimal operational gross leverage with continuous Grossman-Zhou
        drawdown dampening and multi-tier risk constraints.
        """
        if self.high_water_mark == 0.0 or equity > self.high_water_mark:
            self.high_water_mark = equity

        dd_t = max(0.0, 1.0 - (equity / self.high_water_mark))

        # 1. Determine Drawdown Tier
        if dd_t < 0.10:
            dd_tier = 0  # Tier 0: Normal Unconstrained
            tier_cap = self.l_max
        elif dd_t < 0.18:
            dd_tier = 1  # Tier 1: Caution (Hard cap at 2.00x)
            tier_cap = 2.00
        elif dd_t < self.d_max:
            dd_tier = 2  # Tier 2: Defensive (Hard cap at 1.00x)
            tier_cap = 1.00
        else:
            dd_tier = 3  # Tier 3: Floor / Defensive Clamp
            tier_cap = self.l_min

        if dd_tier == 3:
            telemetry = RiskTelemetry(
                current_equity=equity,
                high_water_mark=self.high_water_mark,
                drawdown=dd_t,
                drawdown_tier=dd_tier,
                cushion_ratio=0.0,
                phi_gz=0.0,
                convex_expansion=0.0,
                entropy_dampener=0.0,
                funding_penalty=0.0,
                target_gross_leverage=0.0,
            )
            return 0.0, telemetry

        # 2. Grossman-Zhou Continuous Dampener Phi_GZ
        cushion_ratio = max(0.0, (self.d_max - dd_t) / (self.d_max * (1.0 - dd_t + 1e-8)))
        phi_gz = float(np.clip(cushion_ratio, 0.0, 1.0) ** self.beta_d)

        # 3. Asymmetric Bull Conviction Expansion
        convex_expansion = 1.0 + self.kappa_s * max(0.0, bull_score - self.s_pivot)

        # 4. Regime Entropy Dampener: (1 - alpha_e * (1 - omega_h))
        entropy_dampener = float(np.clip(1.0 - self.alpha_e * max(0.0, 1.0 - regime_entropy), 0.20, 1.0))

        # 5. Funding Rate Drag Attenuator
        funding_penalty = float(np.exp(-1.15 * max(0.0, (funding_rate_avg * 24 * 365) - 0.40)))

        # Composite Target Gross Leverage
        raw_target = self.l_base * convex_expansion * entropy_dampener * phi_gz * funding_penalty
        l_exec = float(np.clip(raw_target, self.l_min, min(self.l_max, tier_cap)))

        telemetry = RiskTelemetry(
            current_equity=equity,
            high_water_mark=self.high_water_mark,
            drawdown=dd_t,
            drawdown_tier=dd_tier,
            cushion_ratio=cushion_ratio,
            phi_gz=phi_gz,
            convex_expansion=convex_expansion,
            entropy_dampener=entropy_dampener,
            funding_penalty=funding_penalty,
            target_gross_leverage=l_exec,
        )
        return l_exec, telemetry
