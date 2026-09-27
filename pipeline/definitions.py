"""
Daily Automated Ingestion and Mart Materialization Pipeline.
"""
from __future__ import annotations

import concurrent.futures
import datetime
import io
import os
import subprocess
import zipfile
import httpx
import polars as pl
from google.cloud import bigquery
from dagster import (
    Definitions,
    ScheduleDefinition,
    asset,
    define_asset_job,
)

from pipeline.ingestion.binance_universe_loader import BinanceUniverseLoader

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "parnasa-498503")
MART_DATASET = os.environ.get("BQ_MART_DATASET", "dbt_marts")
LOCATION = os.environ.get("BQ_LOCATION", "europe-west3")
BINANCE_PUBLIC_BASE = "https://data.binance.vision/data/futures/um"


def _fetch_daily_kline_archive(loader: BinanceUniverseLoader, sym: str, date_str: str) -> pl.DataFrame | None:
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


@asset(group_name="market_data")
def daily_kline_incremental_ingest() -> str:
    """Ingests yesterday's 1m klines across universe and appends to BigQuery."""
    client = bigquery.Client(project=PROJECT_ID, location=LOCATION)
    loader = BinanceUniverseLoader()
    symbols = loader.hl_universe.get_symbols()

    yesterday = (datetime.datetime.now(datetime.timezone.utc).date() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    table_id = f"{PROJECT_ID}.{MART_DATASET}.stg_market_candles_1m_historical"

    day_dfs = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(_fetch_daily_kline_archive, loader, sym, yesterday): sym for sym in symbols}
        for f in concurrent.futures.as_completed(futures):
            res = f.result()
            if res is not None and not res.is_empty():
                day_dfs.append(res)

    if not day_dfs:
        return f"No records found for {yesterday}"

    consolidated = pl.concat(day_dfs)
    tmp_path = f"/tmp/lake/klines_1m_{yesterday}.parquet"
    os.makedirs(os.path.dirname(tmp_path), exist_ok=True)
    consolidated.write_parquet(tmp_path, compression="zstd")

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.PARQUET,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
    )
    with open(tmp_path, "rb") as f:
        job = client.load_table_from_file(f, table_id, job_config=job_config)
    job.result()

    if os.path.exists(tmp_path):
        os.remove(tmp_path)

    return f"Successfully ingested {job.output_rows} bars for {yesterday}"


@asset(deps=[daily_kline_incremental_ingest], group_name="market_data")
def daily_dbt_point_in_time_mart() -> str:
    """Runs dbt incremental build on fct_point_in_time_mart."""
    dbt_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../dbt_transforms"))
    res = subprocess.run(
        ["dbt", "run", "--select", "fct_point_in_time_mart", "--project-dir", dbt_dir, "--profiles-dir", os.path.expanduser("~/.dbt")],
        capture_output=True,
        text=True
    )
    if res.returncode != 0:
        raise RuntimeError(f"dbt build failed:\n{res.stderr}\n{res.stdout}")
    return "Point-in-Time Mart successfully refreshed."


daily_refresh_job = define_asset_job(name="daily_refresh_job", selection=["daily_kline_incremental_ingest", "daily_dbt_point_in_time_mart"])

# Executes everyday at 01:15 UTC (after Binance Vision publishes daily archives)
daily_refresh_schedule = ScheduleDefinition(
    job=daily_refresh_job,
    cron_schedule="15 1 * * *",
    execution_timezone="UTC",
)

defs = Definitions(
    assets=[daily_kline_incremental_ingest, daily_dbt_point_in_time_mart],
    schedules=[daily_refresh_schedule],
)
