"""
Indexes canonical Parquet tick streams into the NautilusTrader DataCatalog
for tick-level replay and microstructural backtesting.
Supports native NautilusTrader and high-performance Parquet catalog fallback.
"""
from __future__ import annotations

import logging
from pathlib import Path
import polars as pl

logger = logging.getLogger(__name__)

try:
    from nautilus_trader.model.data import TradeTick
    from nautilus_trader.model.enums import AggressorSide
    from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
    from nautilus_trader.model.objects import Price, Quantity
    from nautilus_trader.persistence.catalog import DataCatalog
    HAS_NAUTILUS = True
except (ImportError, ModuleNotFoundError):
    HAS_NAUTILUS = False


class NautilusCatalogIndexer:
    def __init__(self, catalog_path: str = "/tmp/nautilus_catalog"):
        self.catalog_path = Path(catalog_path)
        self.catalog_path.mkdir(parents=True, exist_ok=True)
        if HAS_NAUTILUS:
            self.catalog = DataCatalog(str(self.catalog_path))
        else:
            self.catalog = None

    def index_trade_parquet(
        self, parquet_path: str | Path, venue_name: str = "HYPERLIQUID"
    ) -> int:
        path = Path(parquet_path)
        if not path.exists():
            raise FileNotFoundError(f"Parquet file not found: {path}")

        df = pl.scan_parquet(path).select([
            pl.col("timestamp_ms"),
            pl.col("symbol"),
            pl.col("side"),
            pl.col("price").cast(pl.Float32),
            pl.col("size").cast(pl.Float32),
            pl.col("trade_id").cast(pl.Utf8)
        ]).collect(engine="streaming")

        if df.is_empty():
            return 0

        first_symbol = df["symbol"][0]

        # 1. Native NautilusTrader DataCatalog Indexing
        if HAS_NAUTILUS and self.catalog is not None:
            instrument_id = InstrumentId(
                symbol=Symbol(first_symbol),
                venue=Venue(venue_name)
            )

            ticks: list[TradeTick] = []
            for row in df.iter_rows(named=True):
                aggressor = (
                    AggressorSide.BUYER if row["side"] == "BUY" 
                    else AggressorSide.SELLER if row["side"] == "SELL" 
                    else AggressorSide.NO_AGGRESSOR
                )
                ts_ns = int(row["timestamp_ms"]) * 1_000_000
                
                tick = TradeTick(
                    instrument_id=instrument_id,
                    price=Price.from_str(f"{row['price']:.6f}"),
                    size=Quantity.from_str(f"{row['size']:.6f}"),
                    aggressor_side=aggressor,
                    trade_id=row["trade_id"],
                    ts_event=ts_ns,
                    ts_init=ts_ns
                )
                ticks.append(tick)

            self.catalog.write_data(ticks)
            return len(ticks)

        # 2. Resilient Nautilus-Schema Parquet Catalog Fallback
        instrument_str = f"{first_symbol}.{venue_name}"
        catalog_target_dir = self.catalog_path / "data" / "trade_tick" / instrument_str
        catalog_target_dir.mkdir(parents=True, exist_ok=True)

        standardized_ticks = df.with_columns([
            (pl.col("timestamp_ms") * 1_000_000).alias("ts_event"),
            (pl.col("timestamp_ms") * 1_000_000).alias("ts_init"),
            pl.lit(instrument_str).alias("instrument_id"),
            pl.when(pl.col("side") == "BUY")
            .then(pl.lit("BUYER"))
            .when(pl.col("side") == "SELL")
            .then(pl.lit("SELLER"))
            .otherwise(pl.lit("NO_AGGRESSOR"))
            .alias("aggressor_side")
        ]).select([
            "ts_event",
            "ts_init",
            "instrument_id",
            "price",
            "size",
            "aggressor_side",
            "trade_id"
        ])

        target_file = catalog_target_dir / f"{path.stem}_indexed.parquet"
        standardized_ticks.write_parquet(target_file, compression="zstd")
        logger.info("Indexed %d ticks to catalog file: %s", standardized_ticks.height, target_file)

        return standardized_ticks.height
