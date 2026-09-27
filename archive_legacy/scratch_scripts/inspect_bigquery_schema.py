#!/usr/bin/env python3
"""
Inspects:
  1. Local dbt model SQL and schema definitions for the feature pipeline.
  2. Live BigQuery table schemas and column types via INFORMATION_SCHEMA.
"""

import os
from google.cloud import bigquery

PROJECT_ID = "parnasa-498503"
DATASET_ID = "market_data"

print("\n" + "=" * 90)
print("             UPSTREAM BIGQUERY FEATURE TABLE & DBT DEFINITIONS")
print("=" * 90)

# --- 1. LOCAL DBT MODEL SQL DEFINITION ---
sql_paths = [
    "models/fct_4h_features_tbm.sql",
    "models/schema.yml",
    "crypto_features/models/fct_4h_features_tbm.sql",
    "crypto_features/models/schema.yml"
]

for p in sql_paths:
    if os.path.exists(p):
        print(f"\n--- FILE: {p} ---")
        with open(p, "r") as f:
            content = f.read()
        print(content.strip())

# --- 2. LIVE BIGQUERY SCHEMA & COLUMN METADATA ---
print("\n" + "=" * 90)
print(f"             LIVE BIGQUERY SCHEMA METADATA ({PROJECT_ID}.{DATASET_ID})")
print("=" * 90)

try:
    client = bigquery.Client(project=PROJECT_ID)
    
    # Query INFORMATION_SCHEMA for table columns
    query = f"""
    SELECT 
        table_name,
        column_name,
        data_type,
        is_nullable
    FROM `{PROJECT_ID}.{DATASET_ID}.INFORMATION_SCHEMA.COLUMNS`
    WHERE table_name IN ('fct_4h_features_tbm', 'stg_ohlcv', 'stg_open_interest', 'fct_synthetic_liquidations', 'fct_systemic_stress')
    ORDER BY table_name, ordinal_position;
    """
    df = client.query(query).to_dataframe()
    
    if df.empty:
        print(f"No tables found matching target feature names in {PROJECT_ID}.{DATASET_ID}.")
    else:
        for tbl, group in df.groupby("table_name"):
            print(f"\nTABLE: {tbl} ({len(group)} columns)")
            print(f"{'Column Name':<35} {'Data Type':<20} {'Nullable'}")
            print("-" * 65)
            for _, row in group.iterrows():
                print(f"{row['column_name']:<35} {row['data_type']:<20} {row['is_nullable']}")

except Exception as e:
    print(f"[BIGQUERY ACCESS ERROR] {e}")

print("\n" + "=" * 90 + "\n")
