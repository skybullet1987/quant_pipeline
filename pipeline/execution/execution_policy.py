"""
Section 3.4: Execution Policy Layer & Microstructure Routing.
Implements Execution-Adjusted EV, Passive Fill Probability, and Directional Adverse Selection.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
import numpy as np
from pipeline.research.expectancy_engine import TradeIntent


@dataclass(frozen=True)
class OrderRoutePlan:
    symbol: str
    action: Literal["LONG", "SHORT", "FLAT"]
    order_type: Literal["LIMIT_MAKER", "MARKET_TAKER", "DO_NOT_ROUTE"]
    limit_price: float
    target_notional: float
    ev_trade: float
    p_fill: float
    adverse_selection_buffer_bps: float


class ExecutionRouter:
    def __init__(
        self,
        maker_fee_bps: float = -0.5,    # Hyperliquid passive rebate / fee (-0.5 bps)
        taker_fee_bps: float = 3.5,     # Taker execution fee (3.5 bps)
        min_ev_hurdle_bps: float = 2.0, # Minimum edge required to route order
    ):
        self.maker_fee = maker_fee_bps * 1e-4
        self.taker_fee = taker_fee_bps * 1e-4
        self.min_ev_hurdle = min_ev_hurdle_bps * 1e-4

    def estimate_passive_fill_probability(
        self,
        spread_bps: float,
        rolling_volatility_4h: float,
        queue_ahead_notional: float,
        recent_trade_flow_usd: float,
    ) -> float:
        """
        Estimates conditional fill probability P_fill given local queue depth and flow rate.
        """
        # Base fill probability inversely proportional to queue depth ahead
        liquidity_ratio = recent_trade_flow_usd / max(queue_ahead_notional, 10_000.0)
        vol_factor = np.clip(rolling_volatility_4h * 100.0, 0.5, 2.5)
        
        raw_prob = 1.0 - np.exp(-0.35 * liquidity_ratio * vol_factor)
        return float(np.clip(raw_prob, 0.05, 0.95))

    def evaluate_route(
        self,
        intent: TradeIntent,
        best_bid: float,
        best_ask: float,
        rolling_vol_4h: float,
        queue_ahead_notional: float = 25_000.0,
        recent_trade_flow_usd: float = 75_000.0,
    ) -> OrderRoutePlan:
        """
        Selects optimal execution route (Maker vs. Taker) by maximizing Execution-Adjusted EV.
        """
        if intent.action == "FLAT" or intent.ev_return <= self.min_ev_hurdle:
            return OrderRoutePlan(
                symbol=intent.symbol,
                action="FLAT",
                order_type="DO_NOT_ROUTE",
                limit_price=best_bid,
                target_notional=0.0,
                ev_trade=0.0,
                p_fill=0.0,
                adverse_selection_buffer_bps=0.0,
            )

        mid_price = 0.5 * (best_bid + best_ask)
        spread_bps = ((best_ask - best_bid) / mid_price) * 1e4

        p_fill = self.estimate_passive_fill_probability(
            spread_bps=spread_bps,
            rolling_volatility_4h=rolling_vol_4h,
            queue_ahead_notional=queue_ahead_notional,
            recent_trade_flow_usd=recent_trade_flow_usd,
        )

        # Maker: Post at top of book (Best Bid for Long, Best Ask for Short)
        # Taker: Cross spread immediately (Best Ask for Long, Best Bid for Short)
        if intent.action == "LONG":
            limit_price = best_bid
            ev_maker = intent.ev_return - self.maker_fee + (0.5 * spread_bps * 1e-4)
            ev_taker = intent.ev_return - self.taker_fee - (0.5 * spread_bps * 1e-4)
        else:
            limit_price = best_ask
            ev_maker = intent.ev_return - self.maker_fee + (0.5 * spread_bps * 1e-4)
            ev_taker = intent.ev_return - self.taker_fee - (0.5 * spread_bps * 1e-4)

        # Expected value under hybrid maker-taker policy
        ev_trade = (p_fill * ev_maker) + ((1.0 - p_fill) * ev_taker)

        # If passive fill likelihood is high and maker EV exceeds taker EV by hurdle, route LIMIT_MAKER
        if p_fill >= 0.40 and ev_maker > ev_taker:
            order_type = "LIMIT_MAKER"
        else:
            order_type = "MARKET_TAKER"

        return OrderRoutePlan(
            symbol=intent.symbol,
            action=intent.action,
            order_type=order_type,
            limit_price=limit_price,
            target_notional=intent.ev_dollar / max(intent.ev_return, 1e-6),
            ev_trade=float(ev_trade),
            p_fill=p_fill,
            adverse_selection_buffer_bps=float((ev_maker - ev_taker) * 1e4),
        )
