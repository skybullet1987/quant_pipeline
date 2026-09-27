#!/usr/bin/env python3
"""
BigQuery Table Partitioning & Clustering Migration
Migrates existing tables to Date-Partitioned + Ticker-Clustered tables via safe temp-table swap.
"""

import os
from google.cloud import bigquery

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "parnasa-498503")
DATASET_ID = "market_data"

TABLES_TO_OPTIMIZE = [
    ("fct_4h_features_tbm", "timestamp", "ticker"),
    ("fct_exact_path_resolution", "signal_time", "ticker"),
    ("fct_timesfm_features", "timestamp", "ticker"),
    ("fct_liquidation_features", "timestamp", "ticker")
]

client = bigquery.Client(project=PROJECT_ID)

print(f"Starting BigQuery optimization for dataset: {PROJECT_ID}.{DATASET_ID}")

for table_name, ts_col, cluster_col in TABLES_TO_OPTIMIZE:
    full_table = f"{PROJECT_ID}.{DATASET_ID}.{table_name}"
    temp_table = f"{PROJECT_ID}.{DATASET_ID}.{table_name}_partitioned_tmp"
    
    print(f"\n[1/3] Creating partitioned/clustered staging table: {temp_table}...")
    create_query = f"""
    CREATE OR REPLACE TABLE `{temp_table}`
    PARTITION BY DATE({ts_col})
    CLUSTER BY {cluster_col}
    AS SELECT * FROM `{full_table}`;
    """
    client.query(create_query).result()

    print(f"[2/3] Dropping unpartitioned legacy table: {full_table}...")
    drop_query = f"DROP TABLE `{full_table}`;"
    client.query(drop_query).result()

    print(f"[3/3] Renaming {temp_table} -> {table_name}...")
    rename_query = f"ALTER TABLE `{temp_table}` RENAME TO `{table_name}`;"
    client.query(rename_query).result()

    print(f"  -> [SUCCESS] `{table_name}` successfully partitioned by DATE({ts_col}) and clustered by `{cluster_col}`.")

print("\nAll BigQuery tables successfully migrated, partitioned, and clustered.")
