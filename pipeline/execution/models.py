"""
Layer 3: Execution Policy Layer Models & Contracts.
Emits concrete, deterministic OrderPlan specifications for live trading engines.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class OrderAction(str, Enum):
    PLACE = "PLACE"
    MODIFY = "MODIFY"
    CANCEL = "CANCEL"
    HOLD = "HOLD"


class ExecutionOrderType(str, Enum):
    LIMIT_MAKER = "LIMIT_MAKER"  # Post-Only maker limit
    IOC = "IOC"                  # Immediate-or-Cancel aggressive taker
    GTC = "GTC"                  # Good-Til-Cancelled limit


class ExecutionSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True)
class MicrostructureContext:
    timestamp_ns: int
    symbol: str
    best_bid: float
    best_ask: float
    spread_bps: float
    queue_ahead_size: float
    queue_behind_size: float
    trade_flow_imbalance: float   # [-1.0, 1.0] aggressor bias
    rolling_cancel_ratio: float   # [0.0, 1.0]
    realized_vol_1m_bps: float
    estimated_latency_ms: float = 15.0


@dataclass(frozen=True)
class ExecutionEVBreakdown:
    ev_maker_bps: float
    ev_taker_bps: float
    ev_trade_bps: float
    fill_probability: float
    adverse_selection_bps: float
    opportunity_cost_bps: float
    selected_routing: ExecutionOrderType


@dataclass(frozen=True)
class OrderPlan:
    action: OrderAction
    symbol: str
    side: ExecutionSide
    order_type: ExecutionOrderType
    target_price: float
    target_size: float
    target_notional_usd: float
    expected_fill_prob: float
    expected_adverse_selection_bps: float
    ev_trade_bps: float
    cl_ord_id: str
    urgency_bps: float = 0.0
    metadata: dict[str, float] = field(default_factory=dict)
