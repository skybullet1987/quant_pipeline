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


class ProductionEnsembleStrategyConfig(StrategyConfig, frozen=True):
    instrument_ids: list[str]
    primary_clock_symbol: str = "BTC"
    rebalance_interval_bars: int = 6       # 24H
    top_k: int = 8                         # 8 Longs / 8 Shorts = 16 positions
    target_long_leverage: float = 1.50     # 1.5x Long
    target_short_leverage: float = 1.50    # 1.5x Short -> 3.0x Gross Leverage
    max_asset_weight: float = 0.25         # 25% single-token cap
    short_stop_loss_pct: float = 0.12      # 12% short squeeze hard stop
    initial_cash: float = 500.0


class ProductionEnsembleStrategy(Strategy):
    def __init__(self, config: ProductionEnsembleStrategyConfig, alpha_df: pd.DataFrame, regime_df: pd.DataFrame) -> None:
        super().__init__(config)
        self.alpha_df = alpha_df
        self.regime_df = regime_df
        self.instruments_map = {}
        self.primary_inst_id: InstrumentId | None = None
        self.bar_counts = 0
        self.last_rebalance_bar = 0
        self.latest_prices: dict[InstrumentId, float] = {}
        self.price_histories: dict[InstrumentId, list[float]] = {}
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
                self.price_histories[inst_id] = []
                self.subscribe_bars(BarType(inst_id, bar_spec, AggregationSource.EXTERNAL))
        if self.primary_inst_id is None and self.instruments_map:
            self.primary_inst_id = next(iter(self.instruments_map.keys()))

    def on_stop(self) -> None:
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

        # 1. Intra-bar Short Squeeze Stop-Loss Check (+12%)
        open_pos = self.cache.positions_open(instrument_id=inst_id)
        if open_pos and open_pos[0].side == PositionSide.SHORT:
            entry_px = self.short_entry_prices.get(inst_id, close_price)
            if (close_price / entry_px - 1.0) >= self.config.short_stop_loss_pct:
                self.cancel_all_orders(inst_id)
                self.close_all_positions(inst_id)
                if inst_id in self.short_entry_prices:
                    del self.short_entry_prices[inst_id]

        # 2. Portfolio 24H Rebalance Step
        if inst_id == self.primary_inst_id:
            self.current_timestamp = pd.Timestamp(bar.ts_event, unit="ns", tz="UTC")
            self.bar_counts += 1
            if self.bar_counts - self.last_rebalance_bar >= self.config.rebalance_interval_bars:
                self.last_rebalance_bar = self.bar_counts
                self._rebalance_portfolio()

    def _rebalance_portfolio(self) -> None:
        if self.current_timestamp is None or self.current_timestamp not in self.regime_df.index:
            return

        regime_row = self.regime_df.loc[self.current_timestamp]
        p_hazard = float(regime_row["p_hazard"])

        # BOCD Shock Lockout -> 100% Cash
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
        valid_ids, vols = [], {}
        for inst_id, hist in self.price_histories.items():
            sym = inst_id.symbol.value.split("-")[0]
            if len(hist) >= 30 and sym in alphas.index:
                std = float(np.std(np.diff(hist) / hist[:-1]))
                if std > 0.001:
                    valid_ids.append((inst_id, sym))
                    vols[inst_id] = std

        if len(valid_ids) < (self.config.top_k * 2):
            return

        # Symmetrical Selection: Top-K Longs & Bottom-K Shorts
        valid_ids.sort(key=lambda x: alphas[x[1]], reverse=True)
        top_long = valid_ids[: self.config.top_k]
        bottom_short = valid_ids[-self.config.top_k:]

        # Volatility-Parity Weights within Long and Short Baskets
        inv_vols_l = np.array([1.0 / vols[inst_id] for inst_id, _ in top_long])
        weights_l = (inv_vols_l / np.sum(inv_vols_l)) * self.config.target_long_leverage

        inv_vols_s = np.array([1.0 / vols[inst_id] for inst_id, _ in bottom_short])
        weights_s = -(inv_vols_s / np.sum(inv_vols_s)) * self.config.target_short_leverage

        venue = self.instruments_map[top_long[0][0]].id.venue
        account = self.portfolio.account(venue)
        if not account or (equity := float(account.balance_total().as_double())) <= 0:
            return

        target_alloc: dict[InstrumentId, float] = {}
        for (inst_id, _), w in zip(top_long, weights_l):
            target_alloc[inst_id] = min(w, self.config.max_asset_weight)

        for (inst_id, _), w in zip(bottom_short, weights_s):
            target_alloc[inst_id] = max(w, -self.config.max_asset_weight)

        active_candidates = set(target_alloc.keys())
        for pos in self.cache.positions_open():
            active_candidates.add(pos.instrument_id)

        for inst_id in active_candidates:
            instrument = self.instruments_map.get(inst_id)
            if not instrument or (px := self.latest_prices.get(inst_id, 0.0)) <= 0:
                continue

            open_pos = self.cache.positions_open(instrument_id=inst_id)
            current_qty = 0.0
            if open_pos:
                current_qty = float(open_pos[0].quantity.as_double()) if open_pos[0].side == PositionSide.LONG else -float(open_pos[0].quantity.as_double())

            target_wt = target_alloc.get(inst_id, 0.0)
            target_qty = (equity * target_wt) / px
            diff_qty = target_qty - current_qty

            if target_wt == 0.0 and current_qty != 0.0:
                self.cancel_all_orders(inst_id)
                self.close_all_positions(inst_id)
                if inst_id in self.short_entry_prices:
                    del self.short_entry_prices[inst_id]
                continue

            if abs(diff_qty * px) < max(5.0, equity * 0.01):
                continue

            self.cancel_all_orders(inst_id)
            tick = float(instrument.price_increment.as_double())
            limit_px = max(px - tick, tick) if diff_qty > 0 else (px + tick)
            order_qty = round(abs(diff_qty), instrument.size_precision)

            if order_qty > 0 and limit_px > 0:
                if diff_qty < 0:
                    self.short_entry_prices[inst_id] = px
                self.submit_order(self.order_factory.limit(
                    instrument_id=inst_id,
                    order_side=OrderSide.BUY if diff_qty > 0 else OrderSide.SELL,
                    quantity=Quantity.from_str(f"{order_qty:.{instrument.size_precision}f}"),
                    price=Price.from_str(f"{limit_px:.{instrument.price_precision}f}"),
                    time_in_force=TimeInForce.GTC,
                    post_only=True,
                ))
