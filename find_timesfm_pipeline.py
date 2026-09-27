#!/usr/bin/env python3
"""
Locates and displays scripts responsible for TimesFM inference
and writing forecasts to BigQuery.
"""

import os
import glob
import re

SEARCH_DIRS = [
    os.path.expanduser("~/quant_pipeline"),
    os.path.expanduser("~/quant_pipeline/crypto_features"),
    os.path.expanduser("~/quant_pipeline/orchestration"),
    os.path.expanduser("~/quant_pipeline/pipelines")
]

KEYWORDS = ["timesfm", "TimesFm", "tfm_ret", "tfm_slope", "tfm_uncertainty", "tfm_conviction_delta"]
BQ_KEYWORDS = ["bigquery", "to_gbq", "load_table_from_dataframe", "insert_rows_json"]

print("\n" + "=" * 90)
print("             SEARCHING FOR TIMESFM INFERENCE & BIGQUERY WRITER SCRIPTS")
print("=" * 90)

matched_files = []

for s_dir in SEARCH_DIRS:
    if not os.path.exists(s_dir):
        continue
    for root, _, files in os.walk(s_dir):
        # Ignore virtualenv and git directories
        if "venv" in root or ".git" in root or "__pycache__" in root or "target" in root:
            continue
        for f in files:
            if f.endswith(".py") or f.endswith(".sh"):
                fpath = os.path.join(root, f)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as file:
                        content = file.read()
                    
                    has_tfm = any(k.lower() in content.lower() for k in KEYWORDS)
                    has_bq = any(k.lower() in content.lower() for k in BQ_KEYWORDS)

                    if has_tfm:
                        score = 2 if has_bq else 1
                        matched_files.append((fpath, score, has_bq, content))
                except Exception:
                    continue

# Sort by match score (both TimesFM + BigQuery first)
matched_files = sorted(matched_files, key=lambda x: x[1], reverse=True)

if not matched_files:
    print("No matching Python or Shell scripts containing TimesFM logic found.")
else:
    for fpath, score, has_bq, content in matched_files:
        print(f"\n[FILE FOUND] {fpath}")
        print(f"  • BigQuery Integration: {'YES' if has_bq else 'NO'}")
        print("-" * 80)
        
        # Display key segments (imports, inference loop, bigquery write)
        lines = content.splitlines()
        key_lines = []
        for i, l in enumerate(lines):
            if any(k.lower() in l.lower() for k in KEYWORDS + ["bigquery", "forecast", "load_table", "to_gbq", "client.query"]):
                # Grab a small window around match
                start = max(0, i - 2)
                end = min(len(lines), i + 3)
                for w in range(start, end):
                    key_lines.append(w)
        
        # Print concise preview of the file
        last = -2
        for idx in sorted(set(key_lines))[:40]:
            if idx > last + 1:
                print("      ...")
            print(f"  {idx+1:4d}: {lines[idx]}")
            last = idx
        print("-" * 80)

print("\n" + "=" * 90 + "\n")
