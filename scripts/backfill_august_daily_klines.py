"""
Backfills daily 1-minute Kline archives for the current month (August 2026) into BigQuery.
"""
from __future__ import annotations

import concurrent.futures
import datetime
import io
import logging
import os
import zipfile
import httpx
import polars as pl
from google.cloud import bigquery

from pipeline.ingestion.binance_universe_loader import BinanceUniverseLoader

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "parnasa-498503")
MART_DATASET = os.environ.get("BQ_MART_DATASET", "dbt_marts")
LOCATION = os.environ.get("BQ_LOCATION", "europe-west3")
BINANCE_PUBLIC_BASE = "https://data.binance.vision/data/futures/um"


def fetch_daily_kline(loader: BinanceUniverseLoader, sym: str, date_str: str) -> pl.DataFrame | None:
    binance_sym = loader.resolve_binance_symbol(sym)
    if not binance_sym:
        return None

    url = f"{BINANCE_PUBLIC_BASE}/daily/klines/{binance_sym}/1m/{binance_sym}-1m-{date_str}.zip"
    cols = [
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trade_count", "taker_buy_volume",
        "taker_buy_quote_volume", "ignore"
    ]

    try:
        with httpx.Client(timeout=15.0, follow_redirects=True) as client:
            resp = client.get(url)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()

            with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
                content = z.read(z.namelist()[0])

        first_line = content[:300].split(b"\n")[0].decode("utf-8", errors="ignore")
        has_header = not first_line.split(",")[0].strip().isdigit()

        df = pl.read_csv(io.BytesIO(content), has_header=has_header)
        df.columns = cols[:len(df.columns)]

        is_k = sym.startswith("k") or binance_sym.startswith("1000")
        p_mult = 1000.0 if is_k else 1.0
        s_mult = 0.001 if is_k else 1.0

        return df.select([
            pl.lit(sym).alias("symbol"),
            pl.col("open_time").cast(pl.Int64).alias("timestamp_ms"),
            (pl.col("open").cast(pl.Float32) * p_mult).alias("open"),
            (pl.col("high").cast(pl.Float32) * p_mult).alias("high"),
            (pl.col("low").cast(pl.Float32) * p_mult).alias("low"),
            (pl.col("close").cast(pl.Float32) * p_mult).alias("close"),
            (pl.col("volume").cast(pl.Float32) * s_mult).alias("volume"),
            pl.col("quote_volume").cast(pl.Float32).alias("quote_volume"),
            pl.col("trade_count").cast(pl.Int32).alias("trade_count"),
            (pl.col("taker_buy_volume").cast(pl.Float32) * s_mult).alias("taker_buy_volume"),
        ])
    except Exception:
        return None


def backfill_august(start_day: int = 1, end_day: int = 24):
    client = bigquery.Client(project=PROJECT_ID, location=LOCATION)
    loader = BinanceUniverseLoader()
    symbols = loader.hl_universe.get_symbols()
    table_id = f"{PROJECT_ID}.{MART_DATASET}.stg_market_candles_1m_historical"

    logger.info("Ingesting August daily klines (2026-08-%02d to 2026-08-%02d) across %d symbols...", start_day, end_day, len(symbols))

    for day in range(start_day, end_day + 1):
        date_str = f"2026-08-{day:02d}"
        logger.info("--- Ingesting %s ---", date_str)
        day_dfs = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_sym = {executor.submit(fetch_daily_kline, loader, sym, date_str): sym for sym in symbols}
            for future in concurrent.futures.as_completed(future_to_sym):
                res = future.result()
                if res is not None and not res.is_empty():
                    day_dfs.append(res)

        if not day_dfs:
            logger.warning("No klines found for %s", date_str)
            continue

        consolidated = pl.concat(day_dfs)
        out_path = f"/tmp/lake/klines_1m_{date_str}.parquet"
        consolidated.write_parquet(out_path, compression="zstd")

        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.PARQUET,
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        )
        with open(out_path, "rb") as f:
            job = client.load_table_from_file(f, table_id, job_config=job_config)
        job.result()

        logger.info("Appended %d rows for %s into %s", job.output_rows, date_str, table_id)
        if os.path.exists(out_path):
            os.remove(out_path)


if __name__ == "__main__":
    backfill_august(start_day=1, end_day=24)
