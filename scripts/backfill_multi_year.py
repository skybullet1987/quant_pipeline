"""
Multi-Year (2021-2026) Point-in-Time 1-Minute Kline Ingestion Engine.
Streams monthly archives directly into BigQuery with dynamic listing date detection.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse
import concurrent.futures
import datetime
import io
import logging
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


def generate_year_months(start_year: int = 2021) -> list[str]:
    today = datetime.datetime.now(datetime.timezone.utc).date()
    months = []
    curr = today.replace(day=1)
    limit = datetime.date(start_year, 1, 1)
    
    while curr >= limit:
        months.append(curr.strftime("%Y-%m"))
        curr = (curr - datetime.timedelta(days=1)).replace(day=1)
    return sorted(months)


def fetch_month_archive(loader: BinanceUniverseLoader, sym: str, ym: str) -> pl.DataFrame | None:
    binance_sym = loader.resolve_binance_symbol(sym)
    if not binance_sym:
        return None
        
    url = f"{BINANCE_PUBLIC_BASE}/monthly/klines/{binance_sym}/1m/{binance_sym}-1m-{ym}.zip"
    kline_cols = [
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trade_count", "taker_buy_volume",
        "taker_buy_quote_volume", "ignore"
    ]

    try:
        with httpx.Client(timeout=20.0, follow_redirects=True) as client:
            resp = client.get(url)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()

            with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
                content = z.read(z.namelist()[0])

        first_line = content[:300].split(b"\n")[0].decode("utf-8", errors="ignore")
        has_header = not first_line.split(",")[0].strip().isdigit()

        df = pl.read_csv(io.BytesIO(content), has_header=has_header)
        df.columns = kline_cols[:len(df.columns)]

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


def run_multi_year_backfill(start_year: int = 2021, max_workers: int = 12):
    client = bigquery.Client(project=PROJECT_ID, location=LOCATION)
    loader = BinanceUniverseLoader()
    symbols = loader.hl_universe.get_symbols()
    year_months = generate_year_months(start_year=start_year)

    logger.info("Starting Multi-Year Backfill (%d to 2026) across %d symbols (%d months)...", start_year, len(symbols), len(year_months))

    for ym in year_months:
        logger.info("--- Processing Year-Month Batch: %s ---", ym)
        month_dfs: list[pl.DataFrame] = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_sym = {executor.submit(fetch_month_archive, loader, sym, ym): sym for sym in symbols}
            for future in concurrent.futures.as_completed(future_to_sym):
                res = future.result()
                if res is not None and not res.is_empty():
                    month_dfs.append(res)

        if not month_dfs:
            logger.warning("No archives found for %s across any symbol.", ym)
            continue

        consolidated = pl.concat(month_dfs)
        out_parquet = f"/tmp/lake/klines_1m_{ym}.parquet"
        os.makedirs(os.path.dirname(out_parquet), exist_ok=True)
        consolidated.write_parquet(out_parquet, compression="zstd")

        table_id = f"{PROJECT_ID}.{MART_DATASET}.stg_market_candles_1m_historical"
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.PARQUET,
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            schema=[
                bigquery.SchemaField("symbol", "STRING"),
                bigquery.SchemaField("timestamp_ms", "INT64"),
                bigquery.SchemaField("open", "FLOAT64"),
                bigquery.SchemaField("high", "FLOAT64"),
                bigquery.SchemaField("low", "FLOAT64"),
                bigquery.SchemaField("close", "FLOAT64"),
                bigquery.SchemaField("volume", "FLOAT64"),
                bigquery.SchemaField("quote_volume", "FLOAT64"),
                bigquery.SchemaField("trade_count", "INT64"),
                bigquery.SchemaField("taker_buy_volume", "FLOAT64"),
            ]
        )

        with open(out_parquet, "rb") as f:
            job = client.load_table_from_file(f, table_id, job_config=job_config)
        job.result()
        logger.info("Loaded %d rows for %s into %s (Active assets: %d)", job.output_rows, ym, table_id, len(month_dfs))

        if os.path.exists(out_parquet):
            os.remove(out_parquet)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-year", type=int, default=2021)
    parser.add_argument("--workers", type=int, default=12)
    args = parser.parse_args()

    run_multi_year_backfill(start_year=args.start_year, max_workers=args.workers)
