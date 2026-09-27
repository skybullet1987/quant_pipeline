import os
import sys
import ast
import glob
import subprocess
import pandas as pd
from datetime import datetime, timezone
from google.cloud import bigquery

PIPELINE_DIR = "/home/skybullet1987/quant_pipeline"
MODEL_DIR = os.path.join(PIPELINE_DIR, "production_models")
PROJECT_ID = "parnasa-498503"

class Color:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'

def log_pass(msg): print(f"  [{Color.GREEN}PASS{Color.END}] {msg}")
def log_warn(msg): print(f"  [{Color.YELLOW}WARN{Color.END}] {msg}")
def log_fail(msg): print(f"  [{Color.RED}FAIL{Color.END}] {msg}")

def header(title):
    print("\n" + "="*70)
    print(f"{Color.BOLD}{title}{Color.END}")
    print("="*70)

# ============================================================================
# 1. PROCESS & CRON CONFLICT AUDIT
# ============================================================================
def audit_crons_and_processes():
    header("1. AUDITING BACKGROUND PROCESSES & CRONTAB")
    
    # Check Crontab
    try:
        res = subprocess.run("crontab -l", shell=True, capture_output=True, text=True)
        lines = res.stdout.split('\n')
        active_crons = [l for l in lines if l.strip() and not l.strip().startswith('#')]
        
        if active_crons:
            log_warn(f"Found {len(active_crons)} ACTIVE un-commented cron job(s)!")
            for c in active_crons:
                print(f"       -> {c}")
            log_warn("Action Needed: Comment out legacy crons so they don't collide with tmux orchestrator.")
        else:
            log_pass("Crontab is clean. All legacy cron jobs are disabled.")
    except Exception as e:
        log_fail(f"Could not read crontab: {e}")

    # Check Tmux Session
    try:
        res = subprocess.run("tmux ls", shell=True, capture_output=True, text=True)
        if "quant_orchestrator" in res.stdout:
            log_pass("tmux session 'quant_orchestrator' is ACTIVE.")
        else:
            log_fail("tmux session 'quant_orchestrator' NOT FOUND.")
    except Exception as e:
        log_fail(f"Could not verify tmux: {e}")

# ============================================================================
# 2. PYTHON SYNTAX & IMPORT AUDIT (AST PARSER)
# ============================================================================
def audit_python_files():
    header("2. AUDITING PYTHON SCRIPTS FOR SYNTAX & UNDEFINED NAMES")
    py_files = glob.glob(f"{PIPELINE_DIR}/*.py")
    
    failed = False
    for filepath in py_files:
        filename = os.path.basename(filepath)
        try:
            with open(filepath, "r") as f:
                code = f.read()
            tree = ast.parse(code, filename=filename)
            
            # Simple check for imported modules
            imported = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names: imported.add(alias.name.split('.')[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module: imported.add(node.module.split('.')[0])
            
            # Check for common missing standard modules (e.g., 'os' or 'sys' used without import)
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    if node.id in ['os', 'sys', 're', 'time', 'json'] and node.id not in imported:
                        log_fail(f"{filename}: Uses '{node.id}' but missing 'import {node.id}'")
                        failed = True
                        break
            else:
                log_pass(f"{filename:<35} | AST Syntax Valid")
        except SyntaxError as se:
            log_fail(f"{filename}: Syntax Error at line {se.lineno}: {se.msg}")
            failed = True
        except Exception as e:
            log_fail(f"{filename}: AST Parsing Failed: {e}")
            failed = True

# ============================================================================
# 3. BIGQUERY UNIVERSE & DATA FRESHNESS AUDIT
# ============================================================================
def audit_bigquery_tables():
    header("3. AUDITING BIGQUERY DATA FRESHNESS & UNIVERSE CONSISTENCY")
    try:
        client = bigquery.Client(project=PROJECT_ID)
        tables = ['raw_1m_ohlcv', 'stg_ohlcv', 'fct_4h_features_tbm']
        metrics = {}

        for table in tables:
            query = f"""
                SELECT 
                    COUNT(DISTINCT ticker) as total_tickers,
                    MAX(timestamp) as max_ts,
                    MIN(timestamp) as min_ts
                FROM `{PROJECT_ID}.market_data.{table}`
            """
            df = client.query(query).to_dataframe()
            metrics[table] = {
                'tickers': df['total_tickers'].iloc[0],
                'max_ts': pd.to_datetime(df['max_ts'].iloc[0]),
                'min_ts': pd.to_datetime(df['min_ts'].iloc[0])
            }
            log_pass(f"Table '{table:<20}': {metrics[table]['tickers']:>3} Tickers | Latest TS: {metrics[table]['max_ts']}")

        # Validate Universe Synchronization
        raw_t = metrics['raw_1m_ohlcv']['tickers']
        stg_t = metrics['stg_ohlcv']['tickers']
        fct_t = metrics['fct_4h_features_tbm']['tickers']

        if stg_t < raw_t or fct_t < raw_t:
            log_fail(f"UNIVERSE DESYNC DETECTED! raw_1m_ohlcv has {raw_t} assets, but stg_ohlcv has {stg_t} and fct_4h_features_tbm has {fct_t}.")
            log_fail("Action Needed: Run manual catch-up sync scripts.")
        else:
            log_pass(f"UNIVERSE SYNCHRONIZED across all tables ({raw_t} assets).")

        # Check Data Freshness (Lag vs UTC Now)
        now_utc = pd.Timestamp.now(tz='UTC')
        fct_lag_hours = (now_utc - metrics['fct_4h_features_tbm']['max_ts']).total_seconds() / 3600.0
        
        if fct_lag_hours > 4.5:
            log_warn(f"Feature matrix `fct_4h_features_tbm` is lagging by {fct_lag_hours:.2f} hours!")
        else:
            log_pass(f"Feature matrix freshness is optimal (Lag: {fct_lag_hours:.2f} hours).")

    except Exception as e:
        log_fail(f"BigQuery Audit Failed: {e}")

# ============================================================================
# 4. PRODUCTION MODEL ARTIFACT AUDIT
# ============================================================================
def audit_model_artifacts():
    header("4. AUDITING PRODUCTION ML MODEL ARTIFACTS")
    required_artifacts = [
        "hmm_macro.pkl", "hmm_scaler.pkl", "hmm_feature_names.pkl", "hmm_canonical_order.pkl",
        "meta_labeler_long.cbm", "meta_calibrator_long.pkl",
        "meta_labeler_short.cbm", "meta_calibrator_short.pkl",
        "regime_0_long_expert.cbm", "regime_0_short_expert.cbm",
        "regime_1_long_expert.cbm", "regime_1_short_expert.cbm",
        "regime_2_long_expert.cbm", "regime_2_short_expert.cbm",
        "cat_cols.pkl", "feature_names.pkl"
    ]
    
    missing = []
    for artifact in required_artifacts:
        path = os.path.join(MODEL_DIR, artifact)
        if os.path.exists(path):
            size_kb = os.path.getsize(path) / 1024.0
            log_pass(f"Artifact '{artifact:<28}' | Size: {size_kb:>7.1f} KB")
        else:
            log_fail(f"Artifact '{artifact:<28}' | MISSING!")
            missing.append(artifact)
            
    if missing:
        log_fail(f"CRITICAL: {len(missing)} model file(s) missing from {MODEL_DIR}")

# ============================================================================
# 5. DBT PROJECT BUILD AUDIT
# ============================================================================
def audit_dbt_project():
    header("5. AUDITING DBT PROJECT CONFIGURATION & COMPILATION")
    dbt_dir = os.path.join(PIPELINE_DIR, "crypto_features")
    sql_path = os.path.join(dbt_dir, "models/fct_4h_features_tbm.sql")
    
    if os.path.exists(sql_path):
        with open(sql_path, "r") as f:
            sql_content = f.read()
        
        if "materialized='incremental'" in sql_content:
            log_pass("fct_4h_features_tbm.sql is correctly configured as INCREMENTAL.")
        else:
            log_fail("fct_4h_features_tbm.sql is STILL configured as TABLE (Slow Full Rebuilds).")

        if "is_incremental()" in sql_content:
            log_pass("Incremental lookback logic `is_incremental()` detected.")
        else:
            log_fail("Missing `is_incremental()` lookback block in SQL.")
    else:
        log_fail(f"dbt model file not found at: {sql_path}")

# ============================================================================
# MAIN AUDIT EXECUTION
# ============================================================================
def main():
    print(f"\n{Color.BOLD}{'='*70}{Color.END}")
    print(f"{Color.BOLD}   QUANT PIPELINE END-TO-END SYSTEM AUDIT SUITE   {Color.END}")
    print(f"{Color.BOLD}   Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}{Color.END}")
    print(f"{Color.BOLD}{'='*70}{Color.END}")

    audit_crons_and_processes()
    audit_python_files()
    audit_bigquery_tables()
    audit_model_artifacts()
    audit_dbt_project()
    
    header("AUDIT COMPLETE")
    print("Review any red [FAIL] or yellow [WARN] outputs above.\n")

if __name__ == "__main__":
    main()
