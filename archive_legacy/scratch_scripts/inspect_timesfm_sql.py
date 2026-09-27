#!/usr/bin/env python3
"""
Inspects TimesFM SQL Logic and Window Specifications across:
  1. Local dbt models and SQL staging files
  2. BigQuery INFORMATION_SCHEMA.VIEWS definitions
"""

import os
import glob
import re
from google.cloud import bigquery

PROJECT_ID = "parnasa-498503"
DATASET_ID = "market_data"

print("\n" + "=" * 90)
print("             TIMESFM SQL LOGIC & WINDOW SPECIFICATION AUDIT")
print("=" * 90)

# --- 1. LOCAL SQL & DBT MODELS AUDIT ---
print("\n[1] SEARCHING LOCAL DBT & SQL FILES FOR TIMESFM DEFINITIONS...")
sql_files = glob.glob("**/*.sql", recursive=True) + glob.glob("../**/*.sql", recursive=True)

found_local = False
for fpath in set(sql_files):
    try:
        with open(fpath, "r") as f:
            content = f.read()
        
        if any(k in content.lower() for k in ["tfm_", "timesfm", "conviction_delta", "tfm_uncertainty"]):
            found_local = True
            print(f"\n--- MATCH FOUND: {fpath} ---")
            lines = content.splitlines()
            # Print matching lines with 3 lines of surrounding context
            matching_indices = set()
            for idx, line in enumerate(lines):
                if any(k in line.lower() for k in ["tfm_", "timesfm", "conviction_delta", "tfm_uncertainty", "partition by", "rows between"]):
                    for offset in range(max(0, idx - 2), min(len(lines), idx + 3)):
                        matching_indices.add(offset)
            
            last_idx = -2
            for idx in sorted(matching_indices):
                if idx > last_idx + 1:
                    print("    ...")
                print(f"    {idx+1:4d}: {lines[idx]}")
                last_idx = idx
    except Exception as e:
        continue

if not found_local:
    print("    No local SQL files containing explicit tfm_ window definitions found.")

# --- 2. BIGQUERY INFORMATION_SCHEMA VIEW AUDIT ---
print("\n" + "=" * 90)
print(f"[2] QUERYING BIGQUERY VIEW DEFINITIONS ({PROJECT_ID}.{DATASET_ID})...")
print("=" * 90)

try:
    client = bigquery.Client(project=PROJECT_ID)
    view_query = f"""
    SELECT 
        table_name,
        view_definition
    FROM `{PROJECT_ID}.{DATASET_ID}.INFORMATION_SCHEMA.VIEWS`
    WHERE LOWER(view_definition) LIKE '%tfm_%' 
       OR LOWER(view_definition) LIKE '%timesfm%'
       OR LOWER(view_definition) LIKE '%conviction_delta%';
    """
    df_views = client.query(view_query).to_dataframe()
    
    if df_views.empty:
        print("    No BigQuery views found containing TimesFM transformation logic.")
    else:
        for _, row in df_views.iterrows():
            print(f"\nVIEW: {row['table_name']}")
            print("-" * 80)
            print(row["view_definition"])

except Exception as e:
    print(f"    [BIGQUERY VIEW ERROR] {e}")

print("\n" + "=" * 90 + "\n")
