"""
Consolidated BigQuery Lake Loader.
Combines all clean asset partition Parquet files into a single batch
to execute 1 atomic load job, avoiding BigQuery table update rate limits (429).
"""
from __future__ import annotations

import glob
import logging
import os
from google.cloud import bigquery
import polars as pl

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "parnasa-498503")
DATASET_ID = os.environ.get("BQ_RAW_DATASET", "hyperliquid_raw")
LOCATION = os.environ.get("BQ_LOCATION", "europe-west3")


def seed_all_raw_trades():
    client = bigquery.Client(project=PROJECT_ID, location=LOCATION)

    dataset_ref = bigquery.DatasetReference(PROJECT_ID, DATASET_ID)
    dataset = bigquery.Dataset(dataset_ref)
    dataset.location = LOCATION
    client.create_dataset(dataset, exists_ok=True)

    parquet_files = sorted(glob.glob("/tmp/lake/clean/binance/trades/*.parquet"))
    if not parquet_files:
        raise FileNotFoundError("No clean trade files found in /tmp/lake/clean/binance/trades/.")

    logger.info("Consolidating %d asset parquet partitions with Polars...", len(parquet_files))
    consolidated_path = "/tmp/lake/consolidated_clean_trades.parquet"
    
    # Consolidate all 191 files in memory-efficient streaming mode
    pl.scan_parquet(parquet_files).sink_parquet(consolidated_path, compression="zstd")
    
    table_id = f"{PROJECT_ID}.{DATASET_ID}.trades"
    schema = [
        bigquery.SchemaField("timestamp_ms", "INT64"),
        bigquery.SchemaField("symbol", "STRING"),
        bigquery.SchemaField("side", "STRING"),
        bigquery.SchemaField("price", "FLOAT64"),
        bigquery.SchemaField("size", "FLOAT64"),
        bigquery.SchemaField("trade_id", "STRING"),
        bigquery.SchemaField("delta_t_ms", "INT64"),
        bigquery.SchemaField("dqg_state", "STRING"),
    ]

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.PARQUET,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        schema=schema,
    )

    file_size_mb = os.path.getsize(consolidated_path) / (1024 * 1024)
    logger.info("Executing 1 atomic BigQuery load for consolidated file (size: %.2f MB)...", file_size_mb)
    
    with open(consolidated_path, "rb") as f:
        load_job = client.load_table_from_file(f, table_id, job_config=job_config)
    
    load_job.result()
    logger.info("Successfully loaded %d total rows into %s in 1 atomic job.", load_job.output_rows, table_id)
    
    if os.path.exists(consolidated_path):
        os.remove(consolidated_path)


if __name__ == "__main__":
    seed_all_raw_trades()
