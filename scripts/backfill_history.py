"""
Multi-Day Full-Universe Backfill Orchestrator.
Automates historical ingestion -> DQG validation -> BigQuery load -> dbt marts.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import glob
import logging
import os
import subprocess
from google.cloud import bigquery
import polars as pl

from pipeline.ingestion.binance_universe_loader import BinanceUniverseLoader
from pipeline.validation.dqg import DataQualityGate

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "parnasa-498503")
DATASET_ID = os.environ.get("BQ_RAW_DATASET", "hyperliquid_raw")
LOCATION = os.environ.get("BQ_LOCATION", "europe-west3")


def run_day_backfill(date_str: str, client: bigquery.Client, dqg: DataQualityGate, loader: BinanceUniverseLoader):
    logger.info("==================== STARTING BACKFILL FOR %s ====================", date_str)
    
    raw_dir = f"/tmp/lake/raw/binance/trades/{date_str}"
    clean_dir = f"/tmp/lake/clean/binance/trades/{date_str}"
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(clean_dir, exist_ok=True)

    # 1. Parallel Ingestion from Binance Vision
    saved_files = loader.bulk_ingest_universe(
        date_str=date_str,
        output_dir=raw_dir,
        max_workers=8,
        min_daily_volume_usd=0.0
    )
    logger.info("[%s] Downloaded %d assets.", date_str, len(saved_files))
    if not saved_files:
        logger.warning("[%s] No archives available. Skipping day.", date_str)
        return

    # 2. DQG Audit and Parquet Cleaning
    clean_files = []
    total_valid = 0
    for raw_file in saved_files:
        df_raw = pl.read_parquet(raw_file)
        if df_raw.is_empty():
            continue
        df_clean, audit = dqg.audit_and_clean_trade_stream(df_raw)
        out_clean = os.path.join(clean_dir, os.path.basename(raw_file))
        df_clean.write_parquet(out_clean, compression="zstd")
        clean_files.append(out_clean)
        total_valid += df_clean.height

    logger.info("[%s] DQG Validated: %d assets (%d valid ticks).", date_str, len(clean_files), total_valid)

    # 3. Consolidate & Load Atomic Batch to BigQuery
    consolidated_path = f"/tmp/lake/consolidated_{date_str}.parquet"
    pl.scan_parquet(clean_files).sink_parquet(consolidated_path, compression="zstd")

    table_id = f"{PROJECT_ID}.{DATASET_ID}.trades"
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.PARQUET,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        schema=[
            bigquery.SchemaField("timestamp_ms", "INT64"),
            bigquery.SchemaField("symbol", "STRING"),
            bigquery.SchemaField("side", "STRING"),
            bigquery.SchemaField("price", "FLOAT64"),
            bigquery.SchemaField("size", "FLOAT64"),
            bigquery.SchemaField("trade_id", "STRING"),
            bigquery.SchemaField("delta_t_ms", "INT64"),
            bigquery.SchemaField("dqg_state", "STRING"),
        ],
    )

    with open(consolidated_path, "rb") as f:
        load_job = client.load_table_from_file(f, table_id, job_config=job_config)
    load_job.result()
    logger.info("[%s] Appended %d rows into BigQuery %s", date_str, load_job.output_rows, table_id)

    if os.path.exists(consolidated_path):
        os.remove(consolidated_path)

    # 4. Trigger dbt Incremental Run
    dbt_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../dbt_transforms"))
    res = subprocess.run(
        ["dbt", "run", "--project-dir", dbt_dir, "--profiles-dir", os.path.expanduser("~/.dbt")],
        capture_output=True,
        text=True
    )
    if res.returncode != 0:
        logger.error("dbt incremental build failed for %s:\n%s", date_str, res.stderr)
    else:
        logger.info("[%s] dbt incremental feature mart materialized successfully.", date_str)


def main():
    parser = argparse.ArgumentParser(description="Backfill crypto universe data.")
    parser.add_argument("--days", type=int, default=14, help="Number of historical days to backfill (default: 14)")
    args = parser.parse_args()

    client = bigquery.Client(project=PROJECT_ID, location=LOCATION)
    dqg = DataQualityGate()
    loader = BinanceUniverseLoader()

    today = datetime.now(timezone.utc).date()
    for d in range(2, args.days + 2):
        target_date = (today - timedelta(days=d)).strftime("%Y-%m-%d")
        run_day_backfill(target_date, client, dqg, loader)


if __name__ == "__main__":
    main()
