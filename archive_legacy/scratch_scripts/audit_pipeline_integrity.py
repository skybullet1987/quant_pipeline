#!/usr/bin/env python3
"""
Pure Python Pipeline Integrity & Causality Audit
Inspects:
  1. TBM Barrier Geometry & Bar Resolution
  2. TimesFM Feature Construction & Alignment
  3. Meta-Labeler OOF Cross-Validation Purity
  4. HMM State Canonicalization & Serialization
"""

import os
import re
import pickle

print("\n" + "=" * 85)
print("             QUANTITATIVE PIPELINE INTEGRITY & CAUSALITY AUDIT")
print("=" * 85)

# --- 1. TBM BARRIER & RESOLUTION AUDIT ---
print("\n[1] TBM BARRIER DEFINITION & TIMEFRAME RESOLUTION:")
if os.path.exists("build_feature_matrix.py"):
    with open("build_feature_matrix.py") as f:
        bfm_content = f.read()
    
    # Locate TBM function definition and call sites
    tbm_matches = re.findall(r"(def compute_tbm.*?)(?=\ndef |\Z)", bfm_content, re.DOTALL)
    if tbm_matches:
        print("  • compute_tbm definition:")
        for line in tbm_matches[0].splitlines()[:15]:
            print(f"      {line}")
            
    # Check where compute_tbm is called
    print("  • compute_tbm invocation sites:")
    for i, line in enumerate(bfm_content.splitlines()):
        if "compute_tbm" in line and not line.strip().startswith("def "):
            print(f"      Line {i+1:4d}: {line.strip()}")
else:
    print("  • build_feature_matrix.py not found.")

# --- 2. TIMESFM CAUSALITY & FEATURE DEFINITION ---
print("\n[2] TIMESFM FEATURE SOURCE & LAG CHECKS:")
if os.path.exists("build_feature_matrix.py"):
    tfm_lines = [f"Line {i+1:4d}: {l.strip()}" for i, l in enumerate(bfm_content.splitlines()) if "tfm_" in l]
    if tfm_lines:
        for tl in tfm_lines[:8]:
            print(f"    {tl}")
    else:
        print("  • No inline tfm_ calculations found (ingested from upstream BigQuery feature table).")

# Check SQL definition if exists
sql_path = "models/fct_4h_features_tbm.sql"
if os.path.exists(sql_path):
    print(f"  • Inspecting SQL logic in {sql_path}:")
    with open(sql_path) as f:
        sql_lines = f.readlines()
    for i, l in enumerate(sql_lines):
        if any(k in l.lower() for k in ["tfm", "timesfm", "lead(", "lag(", "barrier", "target"]):
            print(f"      Line {i+1:4d}: {l.strip()}")

# --- 3. META-LABELER OOF CROSS-VALIDATION PURITY ---
print("\n[3] META-LABELER OOF GENERATION IN TRAIN SCRIPT:")
if os.path.exists("train_production_models.py"):
    with open("train_production_models.py") as f:
        train_lines = f.readlines()
    
    in_meta_block = False
    meta_snippet = []
    for i, l in enumerate(train_lines):
        if "meta" in l.lower() or "oof" in l.lower():
            meta_snippet.append(f"Line {i+1:4d}: {l.strip()}")
    
    for ms in meta_snippet[:15]:
        print(f"    {ms}")

# --- 4. HMM CANONICAL SERIALIZATION & CODE AUDIT ---
print("\n[4] HMM STATE CANONICALIZATION CODE & FILE HEADER:")
if os.path.exists("train_production_models.py"):
    print("  • HMM saving/loading logic in train_production_models.py:")
    for i, l in enumerate(train_lines):
        if any(k in l for k in ["hmm_canonical_order", "hmm_macro", "hmm_scaler"]):
            print(f"      Line {i+1:4d}: {l.strip()}")

hmm_file = "production_models/hmm_canonical_order.pkl"
if os.path.exists(hmm_file):
    with open(hmm_file, "rb") as f:
        raw_bytes = f.read()
    print(f"  • File size: {len(raw_bytes)} bytes")
    print(f"  • Raw bytes repr: {raw_bytes!r}")
    
    # Attempt alternate unpicklers
    try:
        import joblib
        obj = joblib.load(hmm_file)
        print(f"  • Loaded with joblib: {obj}")
    except Exception as e:
        print(f"  • joblib.load error: {e}")

print("=" * 85 + "\n")
