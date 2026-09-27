"""
Batch processor for Binance Public Data Archives (Monthly/Daily Klines and AggTrades).
"""
from __future__ import annotations

import io
import logging
import zipfile
import httpx
import polars as pl

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BINANCE_PUBLIC_BASE = "https://data.binance.vision/data/futures/um"


class BinanceArchiveLoader:
    def __init__(self, client: httpx.Client | None = None):
        self.client = client or httpx.Client(timeout=30.0)

    def fetch_daily_agg_trades(self, symbol: str, date_str: str) -> pl.DataFrame:
        url = f"{BINANCE_PUBLIC_BASE}/daily/aggTrades/{symbol}/{symbol}-aggTrades-{date_str}.zip"
        logger.info("Downloading Binance archive: %s", url)
        
        response = self.client.get(url)
        if response.status_code == 404:
            raise FileNotFoundError(f"Archive not found: {url}")
        response.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            csv_name = z.namelist()[0]
            with z.open(csv_name) as f:
                content = f.read()

        # Dynamic header check (Binance futures aggTrades contain CSV headers)
        first_line = content[:300].split(b"\n")[0].decode("utf-8", errors="ignore")
        has_header = not first_line.split(",")[0].strip().isdigit()

        standard_cols = [
            "agg_trade_id", "price", "quantity", 
            "first_trade_id", "last_trade_id", "timestamp_ms", "is_buyer_maker"
        ]

        if has_header:
            df = pl.read_csv(io.BytesIO(content), has_header=True)
            df.columns = standard_cols[:len(df.columns)]
        else:
            df = pl.read_csv(
                io.BytesIO(content),
                has_header=False,
                new_columns=standard_cols,
            )

        # Standardize types and downcast to Float32/Int32 for 16 GB VM memory budget
        df = df.with_columns([
            pl.col("timestamp_ms").cast(pl.Int64),
            pl.col("price").cast(pl.Float32),
            pl.col("quantity").cast(pl.Float32).alias("size"),
            pl.col("agg_trade_id").cast(pl.Utf8).alias("trade_id"),
            pl.col("is_buyer_maker").cast(pl.Boolean),
            pl.lit(symbol).alias("symbol"),
            pl.when(pl.col("is_buyer_maker"))
            .then(pl.lit("SELL"))
            .otherwise(pl.lit("BUY"))
            .alias("side")
        ]).select([
            "timestamp_ms",
            "symbol",
            "side",
            "price",
            "size",
            "trade_id"
        ])
        
        return df
