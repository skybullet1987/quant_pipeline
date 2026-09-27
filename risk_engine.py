"""
Decoupled Volatility Risk Engine
Sizes positions strictly by equity dollar risk budget and ATR stop distance.
"""
import numpy as np

class PortfolioRiskEngine:
    def __init__(
        self,
        risk_budget_pct: float = 0.015,       # 1.5% equity risked per SL hit
        max_slot_equity_pct: float = 0.35,    # Max 35% equity notional per slot ($215 on $615)
        max_gross_leverage: float = 2.00,     # Max 2.0x gross leverage across portfolio
        atr_stop_multiplier: float = 1.50
    ):
        self.risk_budget_pct = risk_budget_pct
        self.max_slot_equity_pct = max_slot_equity_pct
        self.max_gross_leverage = max_gross_leverage
        self.atr_stop_mult = atr_stop_multiplier

    def compute_order_size(
        self,
        account_equity: float,
        current_price: float,
        atr_20: float,
        regime_size_mult: float = 1.0,
        model_conviction: float = 0.55,
        min_notional_usd: float = 15.0
    ) -> tuple[float, float, float]:
        """
        Returns: (target_tokens, target_notional, modeled_dollar_risk)
        """
        if account_equity <= 0 or current_price <= 0 or atr_20 <= 0:
            return 0.0, 0.0, 0.0

        # 1. Calculate stop distance
        stop_dist = max(self.atr_stop_mult * atr_20, current_price * 0.015)
        
        # 2. Risk budget scaled by conviction and regime multiplier
        conviction_scalar = float(np.clip((model_conviction - 0.50) / 0.20, 0.5, 1.5))
        dollar_risk = account_equity * self.risk_budget_pct * regime_size_mult * conviction_scalar

        # 3. Base token units
        target_tokens = dollar_risk / stop_dist
        target_notional = target_tokens * current_price

        # 4. Enforce single-position notional cap
        slot_cap_notional = account_equity * self.max_slot_equity_pct
        if target_notional > slot_cap_notional:
            target_notional = slot_cap_notional
            target_tokens = target_notional / current_price

        # 5. Enforce minimum notional threshold
        if target_notional < min_notional_usd:
            return 0.0, 0.0, 0.0

        modeled_risk = target_tokens * stop_dist
        return float(target_tokens), float(target_notional), float(modeled_risk)
