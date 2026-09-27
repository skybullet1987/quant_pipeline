"""
Layer 3: Empirical Fill Model & Execution-Adjusted EV Policy.
"""
from __future__ import annotations

import numpy as np
from pipeline.execution.models import (
    ExecutionEVBreakdown,
    ExecutionOrderType,
    ExecutionSide,
    MicrostructureContext,
    OrderAction,
    OrderPlan,
)
from pipeline.strategy.state import IntentSide, TradeIntent


class EmpiricalFillModel:
    """
    Microstructural Empirical Fill & Adverse Selection Model:
    P(fill | queue, flow, cancels, spread, vol, latency, dt)
    """
    def __init__(
        self,
        base_fill_rate: float = 0.70,
        flow_sensitivity: float = 1.80,
        queue_decay_coef: float = 0.40,
        time_constant_ms: float = 300.0,
    ):
        self.base_fill_rate = base_fill_rate
        self.flow_sensitivity = flow_sensitivity
        self.queue_decay_coef = queue_decay_coef
        self.time_constant_ms = time_constant_ms

    def estimate_fill_probability(
        self,
        context: MicrostructureContext,
        order_size: float,
        is_buy: bool,
        horizon_ms: float = 1000.0
    ) -> float:
        total_ahead = max(context.queue_ahead_size + order_size * 0.5, 1e-4)
        total_depth = total_ahead + max(context.queue_behind_size, 1e-4)
        queue_ratio = total_ahead / total_depth

        # Flow alignment: positive if market aggressor flows in our direction
        flow_direction = context.trade_flow_imbalance if is_buy else -context.trade_flow_imbalance
        
        # Logistic intensity formulation
        latency_penalty = max(0.0, (context.estimated_latency_ms - 10.0) / 100.0)
        logit = (
            self.flow_sensitivity * flow_direction
            - self.queue_decay_coef * np.log1p(queue_ratio * 10.0)
            + (context.spread_bps / 10.0)
            - (context.rolling_cancel_ratio * 0.5)
            - latency_penalty
        )
        prob = 1.0 / (1.0 + np.exp(-logit))
        time_scaling = 1.0 - np.exp(-horizon_ms / self.time_constant_ms)
        
        return float(np.clip(prob * time_scaling, 0.01, 0.99))

    def estimate_adverse_selection_bps(
        self,
        context: MicrostructureContext,
        fill_prob: float,
        is_buy: bool
    ) -> float:
        toxic_flow = max(0.0, -context.trade_flow_imbalance if is_buy else context.trade_flow_imbalance)
        as_bps = (context.realized_vol_1m_bps * 0.35) * (1.0 + toxic_flow) * fill_prob
        return float(max(0.1, as_bps))


class ExecutionPolicyEngine:
    """
    Execution-Adjusted Expected Value Policy Engine:
    EV_trade = P_fill * EV_maker + (1 - P_fill) * EV_taker - OpportunityCost
    """
    def __init__(
        self,
        maker_rebate_bps: float = 0.5,   # Hyperliquid maker rebate ~0.005%
        taker_fee_bps: float = 3.5,      # Hyperliquid taker fee ~0.035%
        opportunity_cost_scalar: float = 0.50
    ):
        self.maker_rebate_bps = maker_rebate_bps
        self.taker_fee_bps = taker_fee_bps
        self.opportunity_cost_scalar = opportunity_cost_scalar
        self.fill_model = EmpiricalFillModel()

    def evaluate_execution(
        self,
        intent: TradeIntent,
        context: MicrostructureContext
    ) -> ExecutionEVBreakdown:
        is_buy = intent.target_side == IntentSide.LONG
        alpha_ev_bps = intent.ev_return_pct * 10000.0

        fill_prob = self.fill_model.estimate_fill_probability(
            context=context,
            order_size=intent.target_notional_usd / max(context.best_bid, 1e-4),
            is_buy=is_buy
        )

        as_bps = self.fill_model.estimate_adverse_selection_bps(
            context=context,
            fill_prob=fill_prob,
            is_buy=is_buy
        )

        ev_maker = alpha_ev_bps + self.maker_rebate_bps - as_bps
        half_spread_bps = context.spread_bps / 2.0
        ev_taker = alpha_ev_bps - self.taker_fee_bps - half_spread_bps
        opp_cost = max(0.0, alpha_ev_bps * self.opportunity_cost_scalar)

        ev_trade = fill_prob * ev_maker + (1.0 - fill_prob) * (ev_taker - opp_cost)

        route = (
            ExecutionOrderType.IOC
            if (ev_taker > ev_maker or intent.urgency_bps > 5.0 or fill_prob < 0.20)
            else ExecutionOrderType.LIMIT_MAKER
        )

        return ExecutionEVBreakdown(
            ev_maker_bps=float(ev_maker),
            ev_taker_bps=float(ev_taker),
            ev_trade_bps=float(ev_trade),
            fill_probability=float(fill_prob),
            adverse_selection_bps=float(as_bps),
            opportunity_cost_bps=float(opp_cost),
            selected_routing=route,
        )

    def formulate_order_plan(
        self,
        intent: TradeIntent,
        context: MicrostructureContext,
        order_seq: int = 1
    ) -> OrderPlan:
        if intent.target_side == IntentSide.FLAT or intent.target_weight <= 0.0:
            return OrderPlan(
                action=OrderAction.HOLD,
                symbol=intent.symbol,
                side=ExecutionSide.BUY,
                order_type=ExecutionOrderType.GTC,
                target_price=0.0,
                target_size=0.0,
                target_notional_usd=0.0,
                expected_fill_prob=0.0,
                expected_adverse_selection_bps=0.0,
                ev_trade_bps=0.0,
                cl_ord_id=f"hold_{intent.symbol}_{order_seq}",
            )

        side = ExecutionSide.BUY if intent.target_side == IntentSide.LONG else ExecutionSide.SELL
        ev_breakdown = self.evaluate_execution(intent, context)

        if ev_breakdown.selected_routing == ExecutionOrderType.LIMIT_MAKER:
            target_px = context.best_bid if side == ExecutionSide.BUY else context.best_ask
        else:
            target_px = context.best_ask if side == ExecutionSide.BUY else context.best_bid

        target_size = intent.target_notional_usd / max(target_px, 1e-4)
        cl_ord_id = f"hl_{intent.symbol}_{side.value.lower()}_{order_seq}"

        return OrderPlan(
            action=OrderAction.PLACE,
            symbol=intent.symbol,
            side=side,
            order_type=ev_breakdown.selected_routing,
            target_price=float(target_px),
            target_size=float(target_size),
            target_notional_usd=float(intent.target_notional_usd),
            expected_fill_prob=ev_breakdown.fill_probability,
            expected_adverse_selection_bps=ev_breakdown.adverse_selection_bps,
            ev_trade_bps=ev_breakdown.ev_trade_bps,
            cl_ord_id=cl_ord_id,
            urgency_bps=intent.urgency_bps,
            metadata={
                "ev_maker_bps": ev_breakdown.ev_maker_bps,
                "ev_taker_bps": ev_breakdown.ev_taker_bps,
                "opp_cost_bps": ev_breakdown.opportunity_cost_bps,
            }
        )
