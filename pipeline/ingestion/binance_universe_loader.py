"""
Unified Universe Ingestion Adapter.
Maps Hyperliquid perp universe to Binance Futures UM Public Data Archives.
"""
from __future__ import annotations

import concurrent.futures
import io
import logging
import os
import zipfile
import httpx
import polars as pl

from pipeline.ingestion.hyperliquid_universe import HyperliquidUniverse

logger = logging.getLogger(__name__)

BINANCE_PUBLIC_BASE = "https://data.binance.vision/data/futures/um"

EXPLICIT_SYMBOL_MAP = {
    "kPEPE": "1000PEPEUSDT",
    "kBONK": "1000BONKUSDT",
    "kSHIB": "1000SHIBUSDT",
    "kFLOKI": "1000FLOKIUSDT",
    "kLUNC": "1000LUNCUSDT",
    "kRATS": "1000RATSUSDT",
    "kBTT": "1000BTTUSDT",
    "kSATS": "1000SATSUSDT",
}


class BinanceUniverseLoader:
    def __init__(self, is_testnet: bool = False):
        self.hl_universe = HyperliquidUniverse(is_testnet=is_testnet)
        self.client = httpx.Client(timeout=20.0, follow_redirects=True)

    def resolve_binance_symbol(self, hl_symbol: str) -> str | None:
        """Translates Hyperliquid ticker to Binance Futures symbol."""
        if hl_symbol in EXPLICIT_SYMBOL_MAP:
            return EXPLICIT_SYMBOL_MAP[hl_symbol]
        
        if hl_symbol.startswith("k") and len(hl_symbol) > 1:
            return f"1000{hl_symbol[1:]}USDT"
        
        return f"{hl_symbol}USDT"

    def fetch_single_day(self, hl_symbol: str, date_str: str) -> pl.DataFrame | None:
        binance_symbol = self.resolve_binance_symbol(hl_symbol)
        if not binance_symbol:
            return None

        url = f"{BINANCE_PUBLIC_BASE}/daily/aggTrades/{binance_symbol}/{binance_symbol}-aggTrades-{date_str}.zip"
        
        try:
            resp = self.client.get(url)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()

            with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
                csv_name = z.namelist()[0]
                with z.open(csv_name) as f:
                    content = f.read()

            first_line = content[:300].split(b"\n")[0].decode("utf-8", errors="ignore")
            has_header = not first_line.split(",")[0].strip().isdigit()
            cols = ["agg_trade_id", "price", "quantity", "first_id", "last_id", "timestamp_ms", "is_buyer_maker"]

            if has_header:
                df = pl.read_csv(io.BytesIO(content), has_header=True)
                df.columns = cols[:len(df.columns)]
            else:
                df = pl.read_csv(io.BytesIO(content), has_header=False, new_columns=cols)

            is_k_scale = hl_symbol.startswith("k") or binance_symbol.startswith("1000")
            price_mult = 1000.0 if is_k_scale else 1.0
            size_mult = 0.001 if is_k_scale else 1.0

            df = df.with_columns([
                pl.col("timestamp_ms").cast(pl.Int64),
                (pl.col("price").cast(pl.Float32) * price_mult).alias("price"),
                (pl.col("quantity").cast(pl.Float32) * size_mult).alias("size"),
                pl.col("agg_trade_id").cast(pl.Utf8).alias("trade_id"),
                pl.lit(hl_symbol).alias("symbol"),
                pl.when(pl.col("is_buyer_maker")).then(pl.lit("SELL")).otherwise(pl.lit("BUY")).alias("side"),
            ]).select(["timestamp_ms", "symbol", "side", "price", "size", "trade_id"])

            return df

        except Exception as e:
            logger.debug("Failed downloading %s from %s: %s", hl_symbol, url, e)
            return None

    def bulk_ingest_universe(
        self,
        date_str: str,
        output_dir: str = "/tmp/lake/raw/binance/trades",
        max_workers: int = 8,
        min_daily_volume_usd: float = 0.0
    ) -> list[str]:
        os.makedirs(output_dir, exist_ok=True)
        symbols = self.hl_universe.get_symbols(min_daily_volume_usd=min_daily_volume_usd)
        saved_files: list[str] = []

        logger.info("Starting bulk ingestion for %d Hyperliquid assets for %s...", len(symbols), date_str)

        def _task(sym: str) -> str | None:
            df = self.fetch_single_day(sym, date_str)
            if df is not None and not df.is_empty():
                target_path = os.path.join(output_dir, f"{sym}_{date_str}.parquet")
                df.write_parquet(target_path, compression="zstd")
                return target_path
            return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_sym = {executor.submit(_task, sym): sym for sym in symbols}
            for future in concurrent.futures.as_completed(future_to_sym):
                sym = future_to_sym[future]
                res = future.result()
                if res:
                    saved_files.append(res)
                    logger.info("Saved %s -> %s", sym, res)
                else:
                    logger.warning("No Binance archive for %s (Hyperliquid-exclusive or unlisted).", sym)

        return saved_files
