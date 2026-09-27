"""
NautilusTrader Event-Driven Full Universe Backtest Runner.
High-throughput execution with tuned risk engine throttlers and comprehensive metrics reporting.
"""
from __future__ import annotations

import logging
import os
import sys
from decimal import Decimal
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import polars as pl

from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
from nautilus_trader.config import LoggingConfig, RiskEngineConfig
from nautilus_trader.model.currencies import Currency, USD
from nautilus_trader.model.data import Bar, BarType, BarSpecification
from nautilus_trader.model.enums import (
    AccountType,
    AggregationSource,
    BarAggregation,
    OmsType,
    OrderStatus,
    PriceType,
)
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.instruments import CryptoPerpetual
from nautilus_trader.model.objects import Money, Price, Quantity

from src.strategy.nautilus_ensemble_strategy import (
    HyperliquidEnsembleStrategy,
    HyperliquidEnsembleStrategyConfig,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def create_hyperliquid_perp_instrument(symbol_str: str, venue: Venue) -> CryptoPerpetual:
    inst_id = InstrumentId(Symbol(f"{symbol_str}-USD-PERP"), venue)
    base_curr = Currency.from_str(symbol_str) if symbol_str != "USD" else USD
    
    return CryptoPerpetual(
        instrument_id=inst_id,
        raw_symbol=Symbol(symbol_str),
        base_currency=base_curr,
        quote_currency=USD,
        settlement_currency=USD,
        is_inverse=False,
        price_precision=6,
        size_precision=4,
        price_increment=Price.from_str("0.000001"),
        size_increment=Quantity.from_str("0.0001"),
        lot_size=Quantity.from_str("0.0001"),
        max_quantity=Quantity.from_str("10000000.0"),
        min_quantity=Quantity.from_str("0.0001"),
        max_price=Price.from_str("1000000.0"),
        min_price=Price.from_str("0.000001"),
        margin_init=Decimal("0.05"),
        margin_maint=Decimal("0.025"),
        maker_fee=Decimal("0.0000"),
        taker_fee=Decimal("0.00035"),
        ts_event=0,
        ts_init=0,
    )


def run_nautilus_pipeline():
    feature_path = "/tmp/lake/features/pit_panel_4h.parquet"

    logger.info("Loading Full Universe 4H Point-in-Time feature dataset...")
    df = (
        pl.read_parquet(feature_path)
        .unique(subset=["symbol", "bucket_timestamp_utc"])
        .sort("bucket_timestamp_utc")
    )

    all_symbols = df["symbol"].unique().to_list()
    logger.info("Configuring NautilusTrader across full universe of %d assets...", len(all_symbols))

    venue = Venue("HYPERLIQUID")
    bar_spec = BarSpecification(4, BarAggregation.HOUR, PriceType.LAST)

    risk_config = RiskEngineConfig(
        max_order_submit_rate="50000/1s",
        max_order_modify_rate="50000/1s",
    )
    engine_config = BacktestEngineConfig(
        trader_id="HYPERLIQUID-QUANT-01",
        logging=LoggingConfig(log_level="WARNING"),
        risk_engine=risk_config,
    )
    engine = BacktestEngine(config=engine_config)

    initial_capital = 100_000.0
    engine.add_venue(
        venue=venue,
        oms_type=OmsType.NETTING,
        account_type=AccountType.MARGIN,
        base_currency=USD,
        starting_balances=[Money(initial_capital, USD)],
    )

    instruments = {}
    instrument_ids_str = []
    for sym in all_symbols:
        inst = create_hyperliquid_perp_instrument(sym, venue)
        instruments[sym] = inst
        instrument_ids_str.append(str(inst.id))
        engine.add_instrument(inst)

    logger.info("Constructing and ordering %d bar events...", df.height)
    pdf = df.sort("bucket_timestamp_utc").to_pandas()
    bar_objects = []

    for row in pdf.itertuples():
        inst = instruments[row.symbol]
        bar_type = BarType(inst.id, bar_spec, AggregationSource.EXTERNAL)
        ts_ns = int(pd.Timestamp(row.bucket_timestamp_utc).value)

        bar = Bar(
            bar_type=bar_type,
            open=Price.from_str(f"{row.open:.6f}"),
            high=Price.from_str(f"{row.high:.6f}"),
            low=Price.from_str(f"{row.low:.6f}"),
            close=Price.from_str(f"{row.close:.6f}"),
            volume=Quantity.from_str(f"{max(row.volume, 0.0001):.4f}"),
            ts_event=ts_ns,
            ts_init=ts_ns,
        )
        bar_objects.append(bar)

    engine.add_data(bar_objects)

    strat_config = HyperliquidEnsembleStrategyConfig(
        instrument_ids=instrument_ids_str,
        primary_clock_symbol="BTC",
        rebalance_interval_bars=6,
        top_k=12,
        max_asset_weight=0.12,
        gross_leverage_cap=1.50,
        hazard_threshold=0.60,
        initial_cash=initial_capital,
    )
    strategy = HyperliquidEnsembleStrategy(strat_config)
    engine.add_strategy(strategy)

    logger.info("Running event-driven simulation (2021-2026)...")
    engine.run()

    logger.info("Compiling performance results...")
    account = engine.portfolio.account(venue)
    positions = engine.cache.positions()
    orders = engine.cache.orders()

    filled_orders = [o for o in orders if o.status in (OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED)]
    canceled_orders = [o for o in orders if o.status == OrderStatus.CANCELED]
    rejected_orders = [o for o in orders if o.status in (OrderStatus.REJECTED, OrderStatus.DENIED)]

    final_balance = account.balance_total().as_double()
    total_net_pnl = final_balance - initial_capital
    net_return_pct = (total_net_pnl / initial_capital) * 100.0

    print("\n" + "=" * 80)
    print("      NAUTILUS TRADER FULL UNIVERSE (212 ASSETS) EVENT-DRIVEN RESULTS")
    print("=" * 80)
    print(f"Total Universe Symbols:            {len(all_symbols):8d}")
    print(f"Total Discrete Orders Submitted:   {len(orders):8d}")
    print(f"Total Orders Filled:               {len(filled_orders):8d}")
    print(f"Total Orders Canceled (Replaced):  {len(canceled_orders):8d}")
    print(f"Total Orders Rejected:             {len(rejected_orders):8d}")
    print(f"Total Positions Processed:         {len(positions):8d}")
    print("-" * 80)
    print(f"Initial Starting Capital:          ${initial_capital:12,.2f}")
    print(f"Final Account Balance:             ${final_balance:12,.2f}")
    print(f"Total Net PnL:                     ${total_net_pnl:12,.2f}")
    print(f"Total Net Return:                  {net_return_pct:11.2f}%")
    print(f"Free Margin Available:             ${account.balance_free().as_double():12,.2f}")
    print("=" * 80)


if __name__ == "__main__":
    run_nautilus_pipeline()
