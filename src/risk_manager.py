from __future__ import annotations
import numpy as np
from dataclasses import dataclass
from typing import List

@dataclass
class AllocationResult:
    coin: str
    target_leverage: float
    position_notional_usd: float
    kelly_fraction: float
    entropy_scalar: float
    allocated_margin_usd: float

class ContinuousKellyPositionSizer:
    def __init__(
        self,
        target_risk_per_bar: float = 0.035,
        half_kelly_dampener: float = 0.5,
        min_leverage: float = 1.0,
        max_leverage: float = 4.0,
        max_single_position_pct: float = 0.33,
        max_portfolio_margin_utilization: float = 0.75
    ) -> None:
        self.target_risk = target_risk_per_bar
        self.dampener = half_kelly_dampener
        self.min_leverage = min_leverage
        self.max_leverage = max_leverage
        self.max_single_weight = max_single_position_pct
        self.max_margin_util = max_portfolio_margin_utilization
        self.h_max = np.log(3.0)

    def compute_hmm_certainty_scalar(self, hmm_state_probs: List[float]) -> float:
        probs = np.array(hmm_state_probs, dtype=np.float64)
        probs = np.clip(probs, 1e-12, 1.0)
        probs = probs / np.sum(probs)
        entropy = -np.sum(probs * np.log(probs))
        certainty = 1.0 - (entropy / self.h_max)
        return float(np.clip(certainty, 0.0, 1.0))

    def compute_continuous_sizing(
        self,
        coin: str,
        prob_catboost: float,
        odds_ratio_b: float,
        atr_pct_20: float,
        hmm_state_probs: List[float],
        equity_usd: float,
        max_exchange_leverage: float = 20.0
    ) -> AllocationResult:
        breakeven_p = 1.0 / (odds_ratio_b + 1.0)
        if prob_catboost <= (breakeven_p + 0.015):
            return AllocationResult(coin, 0.0, 0.0, 0.0, 0.0, 0.0)

        unconstrained_kelly = prob_catboost - ((1.0 - prob_catboost) / odds_ratio_b)
        omega_h = self.compute_hmm_certainty_scalar(hmm_state_probs)
        kappa = self.dampener * unconstrained_kelly * omega_h

        if kappa <= 0.0:
            return AllocationResult(coin, 0.0, 0.0, 0.0, omega_h, 0.0)

        vol_adjusted_leverage = kappa * (self.target_risk / max(atr_pct_20, 1e-4))
        clamped_leverage = float(np.clip(vol_adjusted_leverage, self.min_leverage, self.max_leverage))
        max_notional_single = equity_usd * self.max_single_weight * clamped_leverage
        target_notional = equity_usd * kappa * clamped_leverage
        final_notional = min(target_notional, max_notional_single)
        margin_demanded = final_notional / max_exchange_leverage

        return AllocationResult(
            coin=coin,
            target_leverage=clamped_leverage,
            position_notional_usd=final_notional,
            kelly_fraction=kappa,
            entropy_scalar=omega_h,
            allocated_margin_usd=margin_demanded
        )
