"""
Layer 2 Shrunk Alpha Allocator & Pure Strategy Engine.
Translates AlphaState & RegimeState into immutable TradeIntent objects.
"""
from __future__ import annotations

import numpy as np
from pipeline.strategy.expectancy import ExpectancyEngine
from pipeline.strategy.state import (
    AlphaState,
    FeatureState,
    IntentSide,
    RawMarketState,
    RegimeState,
    TradeIntent,
)


class EmpiricalRegimePolicy:
    """
    Applies continuous permission multipliers to raw alphas based on regime posteriors.
    """
    @staticmethod
    def modulate_regime(regime: RegimeState, raw_alpha: float) -> tuple[float, float, float]:
        # Dampen long alpha if trend is down or hazard is surging
        long_perm = max(0.0, 1.0 - regime.p_hazard) * (1.0 - regime.p_chop * 0.5)
        short_perm = max(0.0, 1.0 - regime.p_hazard) * (1.0 - regime.p_chop * 0.5)
        
        multiplier = regime.p_trend * 1.2 + regime.p_expansion * 0.8 + regime.p_chop * 0.4
        multiplier *= max(0.05, 1.0 - regime.p_hazard)

        return float(long_perm), float(short_perm), float(multiplier)


class PureStrategyCore:
    """
    Zero-I/O Strategy Pipeline:
    Evaluates EV -> Shrinks Alpha -> Modulates by Regime -> Sizes with Kelly -> Emits TradeIntent.
    """
    def __init__(
        self,
        shrinkage_factor: float = 0.75,
        half_kelly_fraction: float = 0.50,
        max_position_weight: float = 0.25,
        min_ev_bps_threshold: float = 3.0
    ):
        self.shrinkage_factor = shrinkage_factor
        self.half_kelly_fraction = half_kelly_fraction
        self.max_position_weight = max_position_weight
        self.min_ev_bps_threshold = min_ev_bps_threshold
        self.expectancy_engine = ExpectancyEngine()

    def process(
        self,
        market: RawMarketState,
        features: FeatureState,
        regime: RegimeState,
        raw_win_prob: float,
        expected_gain_pct: float,
        expected_loss_pct: float,
        total_equity_usd: float = 10000.0
    ) -> TradeIntent:
        is_bullish = raw_win_prob > 0.50
        target_side = IntentSide.LONG if is_bullish else IntentSide.SHORT

        # 1. Evaluate Multi-Outcome Expectancy
        ev = self.expectancy_engine.evaluate_expectancy(
            win_prob=raw_win_prob if is_bullish else (1.0 - raw_win_prob),
            expected_gain_pct=expected_gain_pct,
            expected_loss_pct=expected_loss_pct,
            current_funding_rate=market.funding_rate_hourly,
            predicted_funding_rate=market.predicted_funding_next,
            is_long=is_bullish,
            notional_usd=total_equity_usd * self.max_position_weight
        )

        # 2. Regime Policy Modulations
        long_perm, short_perm, regime_mult = EmpiricalRegimePolicy.modulate_regime(
            regime=regime,
            raw_alpha=(raw_win_prob - 0.50) * 2.0
        )
        permission = long_perm if is_bullish else short_perm

        # 3. Shrunk Alpha Estimation
        mu_raw = ev.ev_return_pct
        mu_effective = self.shrinkage_factor * mu_raw * regime_mult * permission

        # 4. Fractional Kelly Sizing
        variance = max((features.rvol_15m / np.sqrt(525600.0)) ** 2, 1e-6)
        kelly_weight = (mu_effective / variance) * self.half_kelly_fraction
        target_weight = float(np.clip(kelly_weight, 0.0, self.max_position_weight))

        # Check minimum EV hurdle
        if ev.net_edge_bps < self.min_ev_bps_threshold or permission < 0.10:
            target_side = IntentSide.FLAT
            target_weight = 0.0

        target_notional = target_weight * total_equity_usd
        limit_price = market.best_bid if target_side == IntentSide.LONG else market.best_ask

        return TradeIntent(
            timestamp_ns=market.timestamp_ns,
            symbol=market.symbol,
            target_side=target_side,
            target_weight=target_weight,
            target_notional_usd=target_notional,
            limit_price_ref=limit_price,
            urgency_bps=features.vwap_basis_bps,
            ev_return_pct=ev.ev_return_pct,
            regime_multiplier=regime_mult,
            metadata={
                "ev_dollar": ev.ev_dollar,
                "funding_drag_pct": ev.funding_drag_pct,
                "net_edge_bps": ev.net_edge_bps,
                "mu_effective": mu_effective,
            }
        )
