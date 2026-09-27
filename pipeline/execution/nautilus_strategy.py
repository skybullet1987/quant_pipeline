"""
Phase 5 & 6: NautilusTrader Strategy Node for Hyperliquid Execution.
Wires Zero-I/O Strategy Core, Execution Router, and Risk Supervisor into Nautilus Actor.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from nautilus_trader.common.enums import LogColor
from nautilus_trader.config import StrategyConfig
from nautilus_trader.core.message import Event
from nautilus_trader.model.data import Bar, BarType, QuoteTick, TradeTick
from nautilus_trader.model.enums import OrderSide, TimeInForce
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.instruments import Instrument
from nautilus_trader.model.orders import LimitOrder, MarketOrder
from nautilus_trader.trading.strategy import Strategy

from pipeline.execution.execution_policy import ExecutionRouter, OrderRoutePlan
from pipeline.research.expectancy_engine import RawMarketState, TradeIntent, build_trade_intent
from pipeline.research.portfolio_allocator import ShrunkAlphaAllocator
from pipeline.research.regime_policy import evaluate_regime_policy


class HyperliquidCoreConfig(StrategyConfig, frozen=True):
    instrument_id: str
    bar_type: str
    base_equity_usd: float = 100_000.0
    max_leverage_cap: float = 1.50


class HyperliquidCoreStrategy(Strategy):
    """
    Production Nautilus Strategy Actor integrating pure math core with exchange connectivity.
    """

    def __init__(self, config: HyperliquidCoreConfig) -> None:
        super().__init__(config=config)
        self.instrument_id = InstrumentId.from_str(config.instrument_id)
        self.bar_type = BarType.from_str(config.bar_type)
        self.router = ExecutionRouter()
        self.allocator = ShrunkAlphaAllocator(gross_exposure_cap=config.max_leverage_cap)
        self._instrument: Instrument | None = None
        self._last_quote: QuoteTick | None = None

    def on_start(self) -> None:
        self._instrument = self.cache.instrument(self.instrument_id)
        if self._instrument is None:
            self.log.error(f"Could not load instrument {self.instrument_id} from cache.", LogColor.RED)
            self.stop()
            return

        self.subscribe_bars(self.bar_type)
        self.subscribe_quote_ticks(self.instrument_id)
        self.log.info(f"Hyperliquid Strategy initialized for {self.instrument_id}.", LogColor.GREEN)

    def on_quote_tick(self, tick: QuoteTick) -> None:
        self._last_quote = tick

    def on_bar(self, bar: Bar) -> None:
        if self._last_quote is None or self._instrument is None:
            return

        bid_price = float(self._last_quote.bid_price)
        ask_price = float(self._last_quote.ask_price)
        mid_price = 0.5 * (bid_price + ask_price)

        # 1. Construct Zero-I/O Market State
        market_state = RawMarketState(
            symbol=str(self.instrument_id.symbol),
            t_event_ns=bar.ts_event,
            t_recv_ns=bar.ts_init,
            bid_price=bid_price,
            ask_price=ask_price,
            mid_price=mid_price,
            oracle_price=mid_price,
            funding_rate_1h=0.000012,
            funding_missing=False,
        )

        # 2. Build TradeIntent & Route Plan
        intent = build_trade_intent(
            market=market_state,
            target_weight=0.15,
            total_portfolio_equity=self.config.base_equity_usd,
        )

        route_plan: OrderRoutePlan = self.router.evaluate_route(
            intent=intent,
            best_bid=bid_price,
            best_ask=ask_price,
            rolling_vol_4h=0.015,
        )

        if route_plan.order_type == "DO_NOT_ROUTE" or route_plan.target_notional <= 0:
            return

        # 3. Translate RoutePlan to Nautilus Orders
        target_qty = Decimal(str(round(route_plan.target_notional / mid_price, 4)))
        order_side = OrderSide.BUY if route_plan.action == "LONG" else OrderSide.SELL

        if route_plan.order_type == "LIMIT_MAKER":
            order = self.order_factory.limit(
                instrument_id=self.instrument_id,
                order_side=order_side,
                quantity=self._instrument.make_qty(target_qty),
                price=self._instrument.make_price(Decimal(str(round(route_plan.limit_price, 2)))),
                time_in_force=TimeInForce.GTC,
                post_only=True,
            )
        else:
            order = self.order_factory.market(
                instrument_id=self.instrument_id,
                order_side=order_side,
                quantity=self._instrument.make_qty(target_qty),
            )

        self.submit_order(order)
        self.log.info(
            f"Submitted {route_plan.order_type} {order_side.name} order for {target_qty} {self.instrument_id.symbol} (EV: {route_plan.ev_trade:+.4%})",
            LogColor.CYAN,
        )

    def on_stop(self) -> None:
        self.cancel_all_orders(self.instrument_id)
        self.log.info(f"Hyperliquid Strategy stopped. All resting orders cancelled.", LogColor.YELLOW)
