import os
import sqlite3
import subprocess
from dagster import (
    asset,
    define_asset_job,
    AssetSelection,
    ScheduleDefinition,
    DefaultScheduleStatus,
    Definitions,
    op,
    Out,
    Nothing,
    job,
    MaterializeResult,
    MetadataValue,
)

# ------------------------------------------------------------------------------
# ENVIRONMENT & PATHS
# ------------------------------------------------------------------------------
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(os.getcwd(), "bq_key.json")
DBT_PROJECT_DIR = os.path.join(os.getcwd(), "crypto_features")

# ==============================================================================
# 1. CORE 15-MINUTE TRADING PIPELINE
# ==============================================================================

@asset
def market_data_sync():
    """Pulls latest 15m OHLCV and Derivatives directly from Binance."""
    result = subprocess.run(
        ["python3", "sync_latest_ohlcv.py"],
        check=True, capture_output=True, text=True
    )
    subprocess.run(["python3", "sync_latest_derivatives.py"], check=True)
    
    return MaterializeResult(
        metadata={
            "status": MetadataValue.text("Success"),
            "log_snippet": MetadataValue.text(result.stdout[-300:])
        }
    )

@asset(deps=[market_data_sync])
def timesfm_forecast():
    """Generates live ML predictions after market data is updated."""
    result = subprocess.run(
        ["python3", "forecast_timesfm.py"],
        check=True, capture_output=True, text=True
    )
    return MaterializeResult(
        metadata={
            "status": MetadataValue.text("Forecast Appended"),
            "log_snippet": MetadataValue.text(result.stdout[-300:])
        }
    )

@asset(deps=[timesfm_forecast])
def crypto_features_dbt():
    """Rebuilds dbt feature store matrices with freshly joined predictions."""
    result = subprocess.run([
        "dbt", "run",
        "--exclude", "fct_exact_path_resolution",
        "--project-dir", DBT_PROJECT_DIR
    ], check=True, capture_output=True, text=True)
    
    return MaterializeResult(
        metadata={
            "dbt_status": MetadataValue.text("Build Complete"),
            "dbt_output": MetadataValue.text(result.stdout[-600:])
        }
    )

@asset(deps=[crypto_features_dbt])
def hyperliquid_execution():
    """Routes limit orders to exchange and logs rich telemetry metadata into Dagster."""
    result = subprocess.run(
        ["python3", "execute_hyperliquid_testnet.py"],
        check=True, capture_output=True, text=True
    )

    # Read latest snapshot from SQLite execution telemetry
    table_md = "No intents logged in telemetry database."
    intents_count = 0
    db_path = "/home/skybullet1987/quant_pipeline/live_execution_telemetry.db"
    
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT symbol, order_side, status, size_notional, entry_time 
                FROM execution_telemetry 
                ORDER BY entry_time DESC LIMIT 5
            """)
            rows = cursor.fetchall()
            conn.close()
            
            if rows:
                intents_count = len(rows)
                table_md = "| Symbol | Side | Status | Size ($) | Time |\n|---|---|---|---|---|\n"
                for r in rows:
                    size_val = f"${float(r[3]):.2f}" if r[3] is not None else "$0.00"
                    table_md += f"| {r[0]} | {r[1]} | {r[2]} | {size_val} | {r[4]} |\n"
        except Exception:
            pass

    return MaterializeResult(
        metadata={
            "execution_mode": MetadataValue.text("TESTNET"),
            "log_output": MetadataValue.text(result.stdout[-1000:]),
            "recent_intents_count": MetadataValue.int(intents_count),
            "recent_intents_table": MetadataValue.md(table_md)
        }
    )

# ==============================================================================
# 2. DAILY MAINTENANCE & INGESTION TASKS
# ==============================================================================

@asset
def daily_incremental_ingest():
    """Daily incremental ingestion job."""
    subprocess.run(["python3", "daily_incremental_ingest.py"], check=True)
    return True

# ==============================================================================
# 3. JOBS AND SCHEDULE DEFINITIONS
# ==============================================================================

trading_job = define_asset_job(
    name="trading_pipeline_job",
    selection=[market_data_sync, timesfm_forecast, crypto_features_dbt, hyperliquid_execution]
)

trading_schedule = ScheduleDefinition(
    job=trading_job,
    cron_schedule="*/15 * * * *",
    default_status=DefaultScheduleStatus.RUNNING
)

daily_job = define_asset_job(
    name="daily_ingestion_job",
    selection=[daily_incremental_ingest]
)

daily_schedule = ScheduleDefinition(
    job=daily_job,
    cron_schedule="0 1 * * *",
    default_status=DefaultScheduleStatus.RUNNING
)

# ==============================================================================
# 4. DAGSTER DEFINITIONS REGISTRY
# ==============================================================================


# ==============================================================================
# MONTHLY MODEL GOVERNANCE & RETRAINING JOB
# ==============================================================================
@op(out=Out(Nothing))
def model_governance_op():
    import subprocess
    cmd = "/home/skybullet1987/quant_pipeline/venv/bin/python3 evaluate_and_promote_challenger.py"
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        raise Exception(f"Model governance failed: {res.stderr}")
    print(res.stdout)

@job
def monthly_model_governance_job():
    model_governance_op()

monthly_model_governance_schedule = ScheduleDefinition(
    job=monthly_model_governance_job,
    cron_schedule="0 0 1 * *",  # Midnight UTC on the 1st of every month
)

defs = Definitions(
    assets=[
        market_data_sync,
        timesfm_forecast,
        crypto_features_dbt,
        hyperliquid_execution,
        daily_incremental_ingest,
    ],
    schedules=[monthly_model_governance_schedule, 
        trading_schedule,
        daily_schedule,
    ],
)
