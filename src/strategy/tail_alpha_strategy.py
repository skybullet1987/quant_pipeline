"""
NautilusTrader 72H Tail-Alpha Strategy Actor.
Longs Top 2 Orthogonal Composite Leaders, Shorts Bottom 2 Breakdown Names.
3.0x Gross Leverage with 72H Non-Overlapping Rebalance Horizons.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from nautilus_trader.config import StrategyConfig
from nautilus_trader.model.data import Bar, BarType, BarSpecification
from nautilus_trader.model.enums import (
    AggregationSource, BarAggregation, OrderSide, PositionSide, PriceType, TimeInForce
)
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.objects import Price, Quantity
from nautilus_trader.trading.strategy import Strategy


class TailAlphaConfig(StrategyConfig, frozen=True):
    instrument_ids: list[str]
    primary_clock_symbol: str = "BTC"
    rebalance_interval_bars: int = 18      # 72H Rebalance Interval
    top_k: int = 2                         # 2 Longs / 2 Shorts (4 positions total)
    target_long_leverage: float = 1.50     # 1.50x Long (0.75x per token)
    target_short_leverage: float = 1.50    # 1.50x Short (-0.75x per token)
    short_stop_loss_pct: float = 0.15      # 15% catastrophic short stop
    initial_cash: float = 500.0


class TailAlphaStrategy(Strategy):
    def __init__(self, config: TailAlphaConfig, alpha_df: pd.DataFrame, regime_df: pd.DataFrame) -> None:
        super().__init__(config)
        self.alpha_df = alpha_df
        self.regime_df = regime_df
        self.instruments_map = {}
        self.primary_inst_id: InstrumentId | None = None
        self.bar_counts = 0
        self.last_rebalance_bar = 0
        
        self.latest_prices: dict[InstrumentId, float] = {}
        self.short_entry_prices: dict[InstrumentId, float] = {}
        self.current_timestamp = None

    def on_start(self) -> None:
        bar_spec = BarSpecification(4, BarAggregation.HOUR, PriceType.LAST)
        for inst_id_str in self.config.instrument_ids:
            inst_id = InstrumentId.from_str(inst_id_str)
            if self.config.primary_clock_symbol in inst_id_str:
                self.primary_inst_id = inst_id
            instrument = self.cache.instrument(inst_id)
            if instrument:
                self.instruments_map[inst_id] = instrument
                self.subscribe_bars(BarType(inst_id, bar_spec, AggregationSource.EXTERNAL))
        if self.primary_inst_id is None and self.instruments_map:
            self.primary_inst_id = next(iter(self.instruments_map.keys()))

    def on_stop(self) -> None:
        for inst_id in self.instruments_map.keys():
            self.cancel_all_orders(inst_id)

    def on_bar(self, bar: Bar) -> None:
        inst_id = bar.bar_type.instrument_id
        close_px = float(bar.close.as_double())
        self.latest_prices[inst_id] = close_px

        # 1. Intra-bar Catastrophic Short Squeeze Stop (+15%)
        open_pos = self.cache.positions_open(instrument_id=inst_id)
        if open_pos and open_pos[0].side == PositionSide.SHORT:
            entry_px = self.short_entry_prices.get(inst_id, close_px)
            if (close_px / entry_px - 1.0) >= self.config.short_stop_loss_pct:
                self.cancel_all_orders(inst_id)
                self.close_all_positions(inst_id)
                if inst_id in self.short_entry_prices:
                    del self.short_entry_prices[inst_id]

        # 2. Rebalance on 72H Primary Clock (18 bars)
        if inst_id == self.primary_inst_id:
            self.current_timestamp = pd.Timestamp(bar.ts_event, unit="ns", tz="UTC")
            self.bar_counts += 1
            if self.bar_counts - self.last_rebalance_bar >= self.config.rebalance_interval_bars:
                self.last_rebalance_bar = self.bar_counts
                self._rebalance_portfolio()

    def _rebalance_portfolio(self) -> None:
        if self.current_timestamp is None or self.current_timestamp not in self.regime_df.index:
            return

        p_hazard = float(self.regime_df.loc[self.current_timestamp]["p_hazard"])
        if p_hazard > 0.60:
            for inst_id in self.instruments_map.keys():
                if self.cache.positions_open(instrument_id=inst_id):
                    self.cancel_all_orders(inst_id)
                    self.close_all_positions(inst_id)
            self.short_entry_prices.clear()
            return

        if self.current_timestamp not in self.alpha_df.index:
            return

        alphas = self.alpha_df.loc[self.current_timestamp]
        valid_candidates = []
        for inst_id in self.instruments_map.keys():
            sym = inst_id.symbol.value.split("-")[0]
            if sym in alphas.index and self.latest_prices.get(inst_id, 0.0) > 0:
                valid_candidates.append((inst_id, sym, alphas[sym]))

        if len(valid_candidates) < (self.config.top_k * 2):
            return

        # Top 2 Longs (Highest predicted alpha) / Bottom 2 Shorts (Lowest predicted alpha)
        valid_candidates.sort(key=lambda x: x[2], reverse=True)
        top_longs = [c[0] for c in valid_candidates[: self.config.top_k]]
        top_shorts = [c[0] for c in valid_candidates[-self.config.top_k:]]

        account = self.portfolio.account(self.instruments_map[top_longs[0]].id.venue)
        if not account or (equity := float(account.balance_total().as_double())) <= 0:
            return

        target_allocations: dict[InstrumentId, float] = {}
        for inst_id in top_longs:
            target_allocations[inst_id] = self.config.target_long_leverage / self.config.top_k   # +0.75x

        for inst_id in top_shorts:
            target_allocations[inst_id] = -self.config.target_short_leverage / self.config.top_k  # -0.75x

        # Close positions falling out of target basket
        for open_pos in self.cache.positions_open():
            if open_pos.instrument_id not in target_allocations:
                self.cancel_all_orders(open_pos.instrument_id)
                self.close_all_positions(open_pos.instrument_id)
                if open_pos.instrument_id in self.short_entry_prices:
                    del self.short_entry_prices[open_pos.instrument_id]

        # Rebalance target basket
        for inst_id, target_weight in target_allocations.items():
            instrument = self.instruments_map.get(inst_id)
            px = self.latest_prices.get(inst_id, 0.0)
            if not instrument or px <= 0:
                continue

            open_pos = self.cache.positions_open(instrument_id=inst_id)
            current_qty = 0.0
            if open_pos:
                pos = open_pos[0]
                current_qty = float(pos.quantity.as_double()) if pos.side == PositionSide.LONG else -float(pos.quantity.as_double())

            target_usd = equity * target_weight
            target_qty = target_usd / px
            diff_qty = target_qty - current_qty

            if abs(diff_qty * px) < max(10.0, equity * 0.02):
                continue

            self.cancel_all_orders(inst_id)
            order_qty = round(abs(diff_qty), instrument.size_precision)

            if order_qty > 0:
                if diff_qty < 0:
                    self.short_entry_prices[inst_id] = px
                self.submit_order(self.order_factory.market(
                    instrument_id=inst_id,
                    order_side=OrderSide.BUY if diff_qty > 0 else OrderSide.SELL,
                    quantity=Quantity.from_str(f"{order_qty:.{instrument.size_precision}f}"),
                ))
