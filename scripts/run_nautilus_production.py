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

from src.models.ensemble_alpha import generate_ensemble_alphas
from src.strategy.production_ensemble_strategy import (
    ProductionEnsembleStrategy,
    ProductionEnsembleStrategyConfig,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def create_instrument(symbol_str: str, venue: Venue) -> CryptoPerpetual:
    return CryptoPerpetual(
        instrument_id=InstrumentId(Symbol(f"{symbol_str}-USD-PERP"), venue),
        raw_symbol=Symbol(symbol_str),
        base_currency=Currency.from_str(symbol_str) if symbol_str != "USD" else USD,
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


def run_pipeline():
    logger.info("Loading feature panel and BTC regime data...")
    df = (
        pl.read_parquet("/tmp/lake/features/pit_panel_4h.parquet")
        .unique(["symbol", "bucket_timestamp_utc"])
        .sort("bucket_timestamp_utc")
    )
    regime_df = (
        pl.read_parquet("/tmp/lake/features/btc_regime_state_4h.parquet")
        .unique(["bucket_timestamp_utc"])
        .sort("bucket_timestamp_utc")
        .to_pandas()
        .set_index("bucket_timestamp_utc")
    )

    alpha_df = generate_ensemble_alphas(df)

    symbols = df["symbol"].unique().to_list()
    venue = Venue("HYPERLIQUID")
    bar_spec = BarSpecification(4, BarAggregation.HOUR, PriceType.LAST)

    engine = BacktestEngine(
        BacktestEngineConfig(
            trader_id="HYPERLIQUID-PROD-01",
            logging=LoggingConfig(log_level="WARNING"),
            risk_engine=RiskEngineConfig(
                max_order_submit_rate="50000/1s",
                max_order_modify_rate="50000/1s",
            ),
        )
    )

    initial_capital = 500.0
    engine.add_venue(
        venue=venue,
        oms_type=OmsType.NETTING,
        account_type=AccountType.MARGIN,
        base_currency=USD,
        starting_balances=[Money(initial_capital, USD)],
    )

    instruments = {}
    ids_str = []
    for s in symbols:
        inst = create_instrument(s, venue)
        instruments[s] = inst
        ids_str.append(str(inst.id))
        engine.add_instrument(inst)

    logger.info("Streaming %d bar events...", df.height)
    pdf = df.sort("bucket_timestamp_utc").to_pandas()
    bars = [
        Bar(
            BarType(instruments[r.symbol].id, bar_spec, AggregationSource.EXTERNAL),
            Price.from_str(f"{r.open:.6f}"),
            Price.from_str(f"{r.high:.6f}"),
            Price.from_str(f"{r.low:.6f}"),
            Price.from_str(f"{r.close:.6f}"),
            Quantity.from_str(f"{max(r.volume, 0.0001):.4f}"),
            int(pd.Timestamp(r.bucket_timestamp_utc).value),
            int(pd.Timestamp(r.bucket_timestamp_utc).value),
        )
        for r in pdf.itertuples()
    ]
    engine.add_data(bars)

    strat_cfg = ProductionEnsembleStrategyConfig(
        instrument_ids=ids_str,
        top_k=8,
        target_long_leverage=1.50,
        target_short_leverage=1.50,
        initial_cash=initial_capital,
    )
    engine.add_strategy(ProductionEnsembleStrategy(strat_cfg, alpha_df, regime_df))

    logger.info("Executing 3.0x Market-Neutral Simulation (2021-2026)...")
    engine.run()

    account = engine.portfolio.account(venue)
    final_bal = account.balance_total().as_double()
    filled = len(
        [
            o
            for o in engine.cache.orders()
            if o.status in (OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED)
        ]
    )

    print("\n" + "=" * 70)
    print("   3.0x MARKET-NEUTRAL NAUTILUS SIMULATION RESULTS ($500 CAPITAL)")
    print("=" * 70)
    print(f"Total Universe Symbols:      {len(symbols):12d}")
    print(f"Total Orders Filled:         {filled:12d}")
    print(f"Starting Capital:            ${initial_capital:12,.2f}")
    print(f"Final Account Balance:       ${final_bal:12,.2f}")
    print(f"Net PnL:                     ${final_bal - initial_capital:12,.2f}")
    print(f"Net Return:                  {((final_bal - initial_capital) / initial_capital) * 100:11.2f}%")
    print("=" * 70)


if __name__ == "__main__":
    run_pipeline()
