"""
Production Asymmetric Target Barrier Method (TBM) Execution Strategy.
- True Range ATR (6-bar / 24H)
- Long: +2.2x ATR TP / -1.1x ATR SL (Max 18 bars)
- Short: -1.4x ATR TP / +0.9x ATR SL (Max 18 bars)
- Conservative Intrabar Execution
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


class TBMBracketConfig(StrategyConfig, frozen=True):
    instrument_ids: list[str]
    primary_clock_symbol: str = "BTC"
    rebalance_interval_bars: int = 6       # 24H scan
    top_k: int = 4                         # 4 Longs / 4 Shorts
    long_tp_atr: float = 2.2               # 2.2x ATR TP for Longs[cite: 1]
    long_sl_atr: float = 1.1               # 1.1x ATR SL for Longs[cite: 1]
    short_tp_atr: float = 1.4              # 1.4x ATR TP for Shorts[cite: 1]
    short_sl_atr: float = 0.9              # 0.9x ATR SL for Shorts[cite: 1]
    max_holding_bars: int = 18             # 72H Max Holding Window[cite: 1]
    max_position_weight: float = 0.25      # $125 max per position on $500
    initial_cash: float = 500.0


class TBMBracketStrategy(Strategy):
    def __init__(self, config: TBMBracketConfig, alpha_df: pd.DataFrame, regime_df: pd.DataFrame) -> None:
        super().__init__(config)
        self.alpha_df = alpha_df
        self.regime_df = regime_df
        self.instruments_map = {}
        self.primary_inst_id: InstrumentId | None = None
        self.bar_counts = 0
        self.last_rebalance_bar = 0
        
        self.latest_prices: dict[InstrumentId, float] = {}
        self.prev_closes: dict[InstrumentId, float] = {}
        self.tr_histories: dict[InstrumentId, list[float]] = {}
        
        # Position Barriers: {inst_id: (entry_px, tp_px, sl_px, side, bars_held)}
        self.position_barriers: dict[InstrumentId, list] = {}
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
                self.tr_histories[inst_id] = []
                self.subscribe_bars(BarType(inst_id, bar_spec, AggregationSource.EXTERNAL))
        if self.primary_inst_id is None and self.instruments_map:
            self.primary_inst_id = next(iter(self.instruments_map.keys()))

    def on_stop(self) -> None:
        for inst_id in self.instruments_map.keys():
            self.cancel_all_orders(inst_id)

    def on_bar(self, bar: Bar) -> None:
        inst_id = bar.bar_type.instrument_id
        close_px = float(bar.close.as_double())
        high_px = float(bar.high.as_double())
        low_px = float(bar.low.as_double())
        self.latest_prices[inst_id] = close_px

        # Calculate True Range (TR)
        prev_c = self.prev_closes.get(inst_id, close_px)
        tr = max(high_px - low_px, abs(high_px - prev_c), abs(low_px - prev_c))
        self.prev_closes[inst_id] = close_px

        if inst_id not in self.tr_histories:
            self.tr_histories[inst_id] = []
        self.tr_histories[inst_id].append(tr)
        if len(self.tr_histories[inst_id]) > 30:
            self.tr_histories[inst_id].pop(0)

        # 1. Target Barrier Method (TBM) Monitoring
        open_pos = self.cache.positions_open(instrument_id=inst_id)
        if open_pos and inst_id in self.position_barriers:
            entry_px, tp_px, sl_px, side, bars_held = self.position_barriers[inst_id]
            bars_held += 1
            self.position_barriers[inst_id][4] = bars_held

            should_close = False

            if side == PositionSide.LONG:
                # Conservative intra-bar execution: SL evaluated before TP
                if low_px <= sl_px:
                    should_close = True
                elif high_px >= tp_px:
                    should_close = True
                elif bars_held >= self.config.max_holding_bars:
                    should_close = True
            elif side == PositionSide.SHORT:
                if high_px >= sl_px:
                    should_close = True
                elif low_px <= tp_px:
                    should_close = True
                elif bars_held >= self.config.max_holding_bars:
                    should_close = True

            if should_close:
                self.cancel_all_orders(inst_id)
                self.close_all_positions(inst_id)
                del self.position_barriers[inst_id]

        # 2. Portfolio Rebalance Trigger
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
            self.position_barriers.clear()
            return

        if self.current_timestamp not in self.alpha_df.index:
            return

        alphas = self.alpha_df.loc[self.current_timestamp]
        valid_ids = []
        for inst_id, tr_list in self.tr_histories.items():
            sym = inst_id.symbol.value.split("-")[0]
            if len(tr_list) >= 6 and sym in alphas.index:
                atr_24h = float(np.mean(tr_list[-6:]))
                if atr_24h > 0:
                    valid_ids.append((inst_id, sym, atr_24h))

        if len(valid_ids) < (self.config.top_k * 2):
            return

        # Sort: Q1 (Longs - High Inverted Alpha) vs Q5 (Shorts - Low Inverted Alpha)
        valid_ids.sort(key=lambda x: alphas[x[1]], reverse=True)
        top_longs = valid_ids[: self.config.top_k]
        top_shorts = valid_ids[-self.config.top_k:]

        account = self.portfolio.account(self.instruments_map[top_longs[0][0]].id.venue)
        if not account or (equity := float(account.balance_total().as_double())) <= 0:
            return

        target_usd_per_pos = equity * self.config.max_position_weight

        # Open Long Entries & Set ATR Barriers
        for inst_id, _, atr_24h in top_longs:
            if not self.cache.positions_open(instrument_id=inst_id):
                px = self.latest_prices.get(inst_id, 0.0)
                if px > 0 and atr_24h > 0:
                    inst = self.instruments_map[inst_id]
                    qty = round(target_usd_per_pos / px, inst.size_precision)
                    if qty > 0:
                        tp_px = px + (self.config.long_tp_atr * atr_24h)
                        sl_px = px - (self.config.long_sl_atr * atr_24h)
                        self.position_barriers[inst_id] = [px, tp_px, sl_px, PositionSide.LONG, 0]
                        self.submit_order(self.order_factory.market(
                            instrument_id=inst_id,
                            order_side=OrderSide.BUY,
                            quantity=Quantity.from_str(f"{qty:.{inst.size_precision}f}"),
                        ))

        # Open Short Entries & Set ATR Barriers
        for inst_id, _, atr_24h in top_shorts:
            if not self.cache.positions_open(instrument_id=inst_id):
                px = self.latest_prices.get(inst_id, 0.0)
                if px > 0 and atr_24h > 0:
                    inst = self.instruments_map[inst_id]
                    qty = round(target_usd_per_pos / px, inst.size_precision)
                    if qty > 0:
                        tp_px = px - (self.config.short_tp_atr * atr_24h)
                        sl_px = px + (self.config.short_sl_atr * atr_24h)
                        self.position_barriers[inst_id] = [px, tp_px, sl_px, PositionSide.SHORT, 0]
                        self.submit_order(self.order_factory.market(
                            instrument_id=inst_id,
                            order_side=OrderSide.SELL,
                            quantity=Quantity.from_str(f"{qty:.{inst.size_precision}f}"),
                        ))
