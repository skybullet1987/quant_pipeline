"""
Google Cloud BigQuery Batch Loader.
Loads validated Parquet partition files directly into partitioned BigQuery tables.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

try:
    from google.cloud import bigquery
    HAS_BIGQUERY = True
except (ImportError, ModuleNotFoundError):
    HAS_BIGQUERY = False


class BigQueryLakeLoader:
    def __init__(self, project_id: str | None = None, dataset_id: str = "market_data"):
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.client = bigquery.Client(project=project_id) if HAS_BIGQUERY else None

    def load_parquet_to_bq(
        self,
        parquet_path: str | Path,
        table_name: str = "raw_trades",
        write_disposition: str = "WRITE_APPEND"
    ) -> int:
        if not HAS_BIGQUERY or self.client is None:
            logger.info("google-cloud-bigquery client not configured. Local mock run.")
            return 0

        path = Path(parquet_path)
        if not path.exists():
            raise FileNotFoundError(f"Parquet file not found: {path}")

        table_id = f"{self.client.project}.{self.dataset_id}.{table_name}"
        
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.PARQUET,
            write_disposition=write_disposition,
        )

        with open(path, "rb") as source_file:
            load_job = self.client.load_table_from_file(
                source_file, table_id, job_config=job_config
            )

        load_job.result()  # Wait for table load completion
        logger.info("Loaded %d rows into BigQuery table %s", load_job.output_rows, table_id)
        return int(load_job.output_rows or 0)
