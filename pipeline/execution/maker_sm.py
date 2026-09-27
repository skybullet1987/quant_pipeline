"""
Layer 3: Maker State Machine with Hysteresis & Lifecycle Management.
Prevents quote-flicker and rate limit penalties via threshold hysteresis.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any
from pipeline.execution.models import (
    ExecutionOrderType,
    ExecutionSide,
    OrderAction,
    OrderPlan,
)


class OrderState(str, Enum):
    IDLE = "IDLE"
    PENDING_SUBMIT = "PENDING_SUBMIT"
    RESTING = "RESTING"
    PENDING_MODIFY = "PENDING_MODIFY"
    PENDING_CANCEL = "PENDING_CANCEL"
    FILLED = "FILLED"
    CANCELED = "CANCELED"


@dataclass
class ActiveQuote:
    cl_ord_id: str
    symbol: str
    side: ExecutionSide
    price: float
    size: float
    state: OrderState
    last_update_ts: int


class MakerStateMachine:
    """
    Finite State Machine with Hysteresis for Maker Quoting:
    Only amends resting limit orders if price shift > price_hysteresis_bps
    or size change > size_hysteresis_pct.
    """
    def __init__(
        self,
        price_hysteresis_bps: float = 1.0,
        size_hysteresis_pct: float = 0.10,
        min_relist_interval_ms: int = 250
    ):
        self.price_hysteresis_bps = price_hysteresis_bps
        self.size_hysteresis_pct = size_hysteresis_pct
        self.min_relist_interval_ms = min_relist_interval_ms
        self.active_quotes: dict[str, ActiveQuote] = {}

    def reconcile_intent(self, plan: OrderPlan, current_time_ns: int) -> tuple[OrderAction, OrderPlan]:
        key = f"{plan.symbol}_{plan.side.value}"
        current_time_ms = current_time_ns // 1_000_000
        quote = self.active_quotes.get(key)

        # 1. No active quote exists -> PLACE
        if quote is None or quote.state in (OrderState.IDLE, OrderState.CANCELED, OrderState.FILLED):
            if plan.action == OrderAction.PLACE and plan.target_size > 0.0:
                self.active_quotes[key] = ActiveQuote(
                    cl_ord_id=plan.cl_ord_id,
                    symbol=plan.symbol,
                    side=plan.side,
                    price=plan.target_price,
                    size=plan.target_size,
                    state=OrderState.PENDING_SUBMIT,
                    last_update_ts=current_time_ms
                )
                return OrderAction.PLACE, plan
            return OrderAction.HOLD, plan

        # 2. Plan requests flat / cancellation -> CANCEL
        if plan.action == OrderAction.HOLD or plan.target_size <= 0.0:
            quote.state = OrderState.PENDING_CANCEL
            cancel_plan = OrderPlan(
                action=OrderAction.CANCEL,
                symbol=plan.symbol,
                side=plan.side,
                order_type=ExecutionOrderType.GTC,
                target_price=quote.price,
                target_size=quote.size,
                target_notional_usd=quote.price * quote.size,
                expected_fill_prob=0.0,
                expected_adverse_selection_bps=0.0,
                ev_trade_bps=0.0,
                cl_ord_id=quote.cl_ord_id,
            )
            return OrderAction.CANCEL, cancel_plan

        # 3. Rate limiting check
        elapsed_ms = current_time_ms - quote.last_update_ts
        if elapsed_ms < self.min_relist_interval_ms:
            return OrderAction.HOLD, plan

        # 4. Hysteresis Threshold Evaluation
        price_diff_bps = abs(plan.target_price - quote.price) / max(quote.price, 1e-4) * 10000.0
        size_diff_pct = abs(plan.target_size - quote.size) / max(quote.size, 1e-4)

        if price_diff_bps > self.price_hysteresis_bps or size_diff_pct > self.size_hysteresis_pct:
            quote.price = plan.target_price
            quote.size = plan.target_size
            quote.state = OrderState.PENDING_MODIFY
            quote.last_update_ts = current_time_ms

            modify_plan = OrderPlan(
                action=OrderAction.MODIFY,
                symbol=plan.symbol,
                side=plan.side,
                order_type=plan.order_type,
                target_price=plan.target_price,
                target_size=plan.target_size,
                target_notional_usd=plan.target_notional_usd,
                expected_fill_prob=plan.expected_fill_prob,
                expected_adverse_selection_bps=plan.expected_adverse_selection_bps,
                ev_trade_bps=plan.ev_trade_bps,
                cl_ord_id=quote.cl_ord_id,
            )
            return OrderAction.MODIFY, modify_plan

        return OrderAction.HOLD, plan

    def on_fill(self, symbol: str, side: ExecutionSide) -> None:
        key = f"{symbol}_{side.value}"
        if key in self.active_quotes:
            self.active_quotes[key].state = OrderState.FILLED
