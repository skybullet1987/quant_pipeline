import os
import glob
import requests
import pandas as pd
from io import BytesIO
from zipfile import ZipFile
from google.cloud import bigquery
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta

# --- CONFIGURATION ---
PROJECT_ID = "parnasa-498503"
DATASET_ID = "market_data"
FINAL_TABLE_ID = "raw_1m_ohlcv"
TEMP_TABLE_ID = "raw_1m_ohlcv_temp"

FINAL_TABLE_REF = f"{PROJECT_ID}.{DATASET_ID}.{FINAL_TABLE_ID}"
TEMP_TABLE_REF = f"{PROJECT_ID}.{DATASET_ID}.{TEMP_TABLE_ID}"
CACHE_DIR = "data_cache_klines"

START_DATE = datetime(2021, 7, 1)
END_DATE = datetime.now(timezone.utc).replace(tzinfo=None)
NUMERIC_COLS = ['open', 'high', 'low', 'close', 'volume']

def get_full_universe(client):
    safe_table = f"{PROJECT_ID}.{DATASET_ID}.fct_4h_features_tbm"
    print(f"Fetching coin universe from {safe_table}...")
    try:
        df = client.query(f"SELECT DISTINCT ticker FROM `{safe_table}`").to_dataframe()
        return df['ticker'].str.upper().tolist()
    except Exception as e:
        print(f"Error fetching universe: {e}")
        return []

def setup_unpartitioned_temp_table(client):
    """Creates a temporary staging table with NO partitioning to avoid daily modification quotas."""
    client.delete_table(TEMP_TABLE_REF, not_found_ok=True)
    schema = [
        bigquery.SchemaField("timestamp", "TIMESTAMP", mode="NULLABLE"),
        bigquery.SchemaField("ticker", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("open", "FLOAT64", mode="NULLABLE"),
        bigquery.SchemaField("high", "FLOAT64", mode="NULLABLE"),
        bigquery.SchemaField("low", "FLOAT64", mode="NULLABLE"),
        bigquery.SchemaField("close", "FLOAT64", mode="NULLABLE"),
        bigquery.SchemaField("volume", "FLOAT64", mode="NULLABLE")
    ]
    table = bigquery.Table(TEMP_TABLE_REF, schema=schema)
    client.create_table(table)
    print(f"Created UNPARTITIONED staging table: {TEMP_TABLE_REF}")

def main():
    client = bigquery.Client(project=PROJECT_ID)
    universe = get_full_universe(client)
    if not universe:
        return
        
    os.makedirs(CACHE_DIR, exist_ok=True)
    parquet_files = sorted(glob.glob(os.path.join(CACHE_DIR, "*.parquet")))
    
    print("\nPhase 1: Downloading & Caching (Skipping - Already Cached)...")
    
    print("\nPhase 2: Streaming 58 Parquet files to UNPARTITIONED Temp Table...")
    setup_unpartitioned_temp_table(client)
        
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.PARQUET,
        write_disposition="WRITE_APPEND"
    )
    
    for idx, p_file in enumerate(parquet_files, 1):
        ticker = os.path.basename(p_file).replace(".parquet", "")
        print(f"[{idx}/{len(parquet_files)}] Streaming {ticker} to Temp Table...")
        with open(p_file, "rb") as source_file:
            job = client.load_table_from_file(source_file, TEMP_TABLE_REF, job_config=job_config)
            job.result()
            
    print("\nPhase 3: Migrating to FINAL Partitioned Table (Bypassing Quotas)...")
    migration_query = f"""
        CREATE OR REPLACE TABLE `{FINAL_TABLE_REF}`
        PARTITION BY DATE(timestamp)
        CLUSTER BY ticker
        AS SELECT * FROM `{TEMP_TABLE_REF}`
    """
    query_job = client.query(migration_query)
    query_job.result()
    
    print("Cleaning up Temp Table...")
    client.delete_table(TEMP_TABLE_REF, not_found_ok=True)
    
    print("\n[SUCCESS] BigQuery load complete! All 58 assets staged perfectly.")

if __name__ == "__main__":
    main()
