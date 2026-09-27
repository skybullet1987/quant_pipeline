"""
Tactical Regime & Dynamic Prior Engine
Replaces hard binary locks with dynamic Bayesian priors and fast tactical hurdle shifts.
"""
import numpy as np

class TacticalRegimeEngine:
    def __init__(
        self,
        bull_breadth_threshold: float = 0.65,
        bear_breadth_threshold: float = 0.30
    ):
        self.bull_thresh = bull_breadth_threshold
        self.bear_thresh = bear_breadth_threshold

    def evaluate_state(
        self,
        slow_regime: int,
        btc_ret_1h: float = 0.0,
        btc_ret_4h: float = 0.0,
        market_breadth_sma20: float = 0.50,
        vol_expansion_ratio: float = 1.0
    ) -> dict:
        """
        Calculates directional prior multipliers and probability thresholds.
        Shifts the required hurdle rate and sizing rather than hard-banning directions.
        """
        # Fast tactical breakout / squeeze detection
        is_fast_squeeze = (btc_ret_1h > 0.02 or btc_ret_4h > 0.04) and (market_breadth_sma20 > 0.55)
        is_fast_flush = (btc_ret_1h < -0.02 or btc_ret_4h < -0.04) and (market_breadth_sma20 < 0.40)

        # Baseline thresholds
        long_hurdle = 0.53
        short_hurdle = 0.53
        long_size_mult = 1.0
        short_size_mult = 1.0

        # Structural State Logic
        if slow_regime == 1 or market_breadth_sma20 >= self.bull_thresh:
            # Bullish Structural Regime
            long_hurdle = 0.51
            short_hurdle = 0.58
            long_size_mult = 1.15
            short_size_mult = 0.50

            if is_fast_squeeze:
                short_hurdle = 0.68  # Heavy hurdle during vertical impulse
                short_size_mult = 0.15
                long_size_mult = 1.30

        elif slow_regime == 2 or market_breadth_sma20 <= self.bear_thresh:
            # Bearish Structural Regime
            long_hurdle = 0.58
            short_hurdle = 0.51
            long_size_mult = 0.50
            short_size_mult = 1.15

            if is_fast_flush:
                long_hurdle = 0.68
                long_size_mult = 0.15
                short_size_mult = 1.30

        else:
            # Regime 0: Chop / Range Compression
            long_hurdle = 0.55
            short_hurdle = 0.55
            long_size_mult = 0.70
            short_size_mult = 0.70

        return {
            "long_hurdle": long_hurdle,
            "short_hurdle": short_hurdle,
            "long_size_mult": long_size_mult,
            "short_size_mult": short_size_mult,
            "is_fast_squeeze": is_fast_squeeze,
            "is_fast_flush": is_fast_flush
        }
