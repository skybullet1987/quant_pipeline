"""
Exports 4H-sampled Point-in-Time feature matrix from BigQuery for window stability experiments.
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from google.cloud import bigquery
import polars as pl

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "parnasa-498503")
LOCATION = os.environ.get("BQ_LOCATION", "europe-west3")


def export_panel():
    client = bigquery.Client(project=PROJECT_ID, location=LOCATION)
    output_path = "/tmp/lake/features/pit_panel_4h.parquet"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Sample 4H intervals (every 240 minutes) on point-in-time eligible universe
    query = """
    SELECT
        symbol,
        bucket_timestamp_utc,
        open,
        high,
        low,
        close,
        volume,
        quote_volume,
        asset_age_days,
        rolling_24h_volume_usd,
        rolling_24h_volatility,
        cs_liquidity_percentile,
        cs_momentum_4h_percentile,
        log_ret_proxy AS log_ret
    FROM `parnasa-498503.dbt_marts.fct_point_in_time_mart`
    WHERE is_universe_eligible = TRUE
      AND MOD(UNIX_SECONDS(bucket_timestamp_utc), 14400) = 0
    ORDER BY bucket_timestamp_utc ASC, symbol ASC
    """

    logger.info("Executing 4H panel export query in BigQuery...")
    arrow_table = client.query(query).to_arrow()
    df = pl.from_arrow(arrow_table)

    logger.info("Retrieved %d 4H cross-sectional rows. Saving to %s...", df.height, output_path)
    df.write_parquet(output_path, compression="zstd")
    logger.info("Saved (%.2f MB).", os.path.getsize(output_path) / (1024 * 1024))


if __name__ == "__main__":
    export_panel()
