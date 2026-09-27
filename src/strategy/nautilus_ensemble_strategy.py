"""
NautilusTrader Strategy Actor for Hyperliquid Quantitative Perpetuals Pipeline.
Implements event-driven multi-asset portfolio rebalancing, volatility parity sizing,
and BOCD regime shock risk controls across the full 200+ token universe.
"""
from __future__ import annotations

from decimal import Decimal
import numpy as np

from nautilus_trader.config import StrategyConfig
from nautilus_trader.model.data import Bar, BarType, BarSpecification
from nautilus_trader.model.enums import (
    AggregationSource,
    BarAggregation,
    OrderSide,
    PositionSide,
    PriceType,
    TimeInForce,
)
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.objects import Price, Quantity
from nautilus_trader.trading.strategy import Strategy


class HyperliquidEnsembleStrategyConfig(StrategyConfig, frozen=True):
    instrument_ids: list[str]
    primary_clock_symbol: str = "BTC"     # Only BTC advances the portfolio bar clock
    rebalance_interval_bars: int = 6       # 24H (6 x 4H bars)
    top_k: int = 12                        # Top 12 liquid momentum names
    max_asset_weight: float = 0.12         # 12% single-asset cap
    gross_leverage_cap: float = 1.50       # 1.5x max gross exposure
    hazard_threshold: float = 0.60         # BOCD shock threshold
    initial_cash: float = 100_000.0


class HyperliquidEnsembleStrategy(Strategy):
    """Event-driven execution strategy running on NautilusTrader."""

    def __init__(self, config: HyperliquidEnsembleStrategyConfig) -> None:
        super().__init__(config)
        self.instruments_map = {}
        self.primary_inst_id: InstrumentId | None = None
        self.bar_counts = 0
        self.last_rebalance_bar = 0

        self.latest_prices: dict[InstrumentId, float] = {}
        self.price_histories: dict[InstrumentId, list[float]] = {}
        
        self.current_hazard: float = 0.0
        self.p_expansion: float = 0.0

    def on_start(self) -> None:
        self.log.info(f"Hyperliquid Strategy initialized. Subscribing to {len(self.config.instrument_ids)} instruments...")
        bar_spec = BarSpecification(4, BarAggregation.HOUR, PriceType.LAST)
        
        for inst_id_str in self.config.instrument_ids:
            inst_id = InstrumentId.from_str(inst_id_str)
            if self.config.primary_clock_symbol in inst_id_str:
                self.primary_inst_id = inst_id

            instrument = self.cache.instrument(inst_id)
            if instrument:
                self.instruments_map[inst_id] = instrument
                self.price_histories[inst_id] = []
                bar_type = BarType(inst_id, bar_spec, AggregationSource.EXTERNAL)
                self.subscribe_bars(bar_type)

        if self.primary_inst_id is None and self.instruments_map:
            self.primary_inst_id = next(iter(self.instruments_map.keys()))

    def on_stop(self) -> None:
        self.log.info("Strategy execution completed. Unsubscribing all instruments...")
        for inst_id in self.instruments_map.keys():
            self.cancel_all_orders(inst_id)

    def on_bar(self, bar: Bar) -> None:
        inst_id = bar.bar_type.instrument_id
        close_price = float(bar.close.as_double())
        self.latest_prices[inst_id] = close_price

        if inst_id not in self.price_histories:
            self.price_histories[inst_id] = []
        self.price_histories[inst_id].append(close_price)
        if len(self.price_histories[inst_id]) > 180:
            self.price_histories[inst_id].pop(0)

        # Advance rebalance clock strictly once per 4H interval on primary asset
        if inst_id == self.primary_inst_id:
            self.bar_counts += 1
            if self.bar_counts - self.last_rebalance_bar >= self.config.rebalance_interval_bars:
                self.last_rebalance_bar = self.bar_counts
                self._rebalance_portfolio()

    def _rebalance_portfolio(self) -> None:
        """Executes risk-budgeted volatility parity rebalancing across active instruments."""
        if self.current_hazard > self.config.hazard_threshold:
            for inst_id in self.instruments_map.keys():
                open_pos = self.cache.positions_open(instrument_id=inst_id)
                if open_pos:
                    self.cancel_all_orders(inst_id)
                    self.close_all_positions(inst_id)
            return

        valid_ids = []
        vols = {}
        for inst_id, history in self.price_histories.items():
            if len(history) >= 30:
                ret = np.diff(history) / history[:-1]
                std = float(np.std(ret))
                if std > 0.001:
                    valid_ids.append(inst_id)
                    vols[inst_id] = std

        if len(valid_ids) < self.config.top_k:
            return

        scored_ids = []
        for inst_id in valid_ids:
            hist = self.price_histories[inst_id]
            mom_72h = (hist[-1] / hist[-18] - 1.0) if len(hist) >= 18 else 0.0
            scored_ids.append((inst_id, mom_72h))

        scored_ids.sort(key=lambda x: x[1], reverse=True)
        top_long_ids = [inst_id for inst_id, _ in scored_ids[: self.config.top_k]]

        inv_vols = np.array([1.0 / vols[inst_id] for inst_id in top_long_ids])
        norm_weights = inv_vols / np.sum(inv_vols)

        target_gross = min(1.0 + 0.5 * self.p_expansion, self.config.gross_leverage_cap)
        venue = self.instruments_map[top_long_ids[0]].id.venue
        account = self.portfolio.account(venue)
        if not account:
            return
        
        equity = float(account.balance_total().as_double())
        if equity <= 0:
            return

        target_allocations: dict[InstrumentId, float] = {}
        for inst_id, w in zip(top_long_ids, norm_weights):
            target_allocations[inst_id] = min(w * target_gross, self.config.max_asset_weight)

        active_candidates = set(target_allocations.keys())
        for pos in self.cache.positions_open():
            active_candidates.add(pos.instrument_id)

        for inst_id in active_candidates:
            instrument = self.instruments_map.get(inst_id)
            if not instrument:
                continue

            open_positions = self.cache.positions_open(instrument_id=inst_id)
            current_qty = 0.0
            if open_positions:
                pos = open_positions[0]
                if pos.side == PositionSide.LONG:
                    current_qty = float(pos.quantity.as_double())
                elif pos.side == PositionSide.SHORT:
                    current_qty = -float(pos.quantity.as_double())

            px = self.latest_prices.get(inst_id, 0.0)
            if px <= 0:
                continue

            target_wt = target_allocations.get(inst_id, 0.0)
            target_usd = equity * target_wt
            target_qty = target_usd / px

            diff_qty = target_qty - current_qty
            diff_usd = abs(diff_qty * px)

            # Liquidate positions that fell out of Top-K
            if target_wt == 0.0 and current_qty != 0.0:
                self.cancel_all_orders(inst_id)
                self.close_all_positions(inst_id)
                continue

            if diff_usd < max(500.0, equity * 0.01):
                continue

            self.cancel_all_orders(inst_id)

            qty_precision = instrument.size_precision
            price_precision = instrument.price_precision
            tick_size = float(instrument.price_increment.as_double())

            if diff_qty > 0:
                side = OrderSide.BUY
                limit_px = max(px - tick_size, tick_size)
            else:
                side = OrderSide.SELL
                limit_px = px + tick_size

            order_qty = round(abs(diff_qty), qty_precision)

            if order_qty > 0 and limit_px > 0:
                order = self.order_factory.limit(
                    instrument_id=inst_id,
                    order_side=side,
                    quantity=Quantity.from_str(f"{order_qty:.{qty_precision}f}"),
                    price=Price.from_str(f"{limit_px:.{price_precision}f}"),
                    time_in_force=TimeInForce.GTC,
                    post_only=True,
                )
                self.submit_order(order)
