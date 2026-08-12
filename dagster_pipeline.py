import os
import subprocess
from dagster import (
    asset,
    ScheduleDefinition,
    DefaultScheduleStatus,
    define_asset_job,
    Definitions,
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
    subprocess.run(["python3", "sync_latest_ohlcv.py"], check=True)
    subprocess.run(["python3", "sync_latest_derivatives.py"], check=True)
    return True

@asset(deps=[market_data_sync])
def timesfm_forecast():
    """Generates live ML predictions after market data is updated."""
    subprocess.run(["python3", "forecast_timesfm.py"], check=True)
    return True

@asset(deps=[timesfm_forecast])
def crypto_features_dbt():
    """Rebuilds dbt feature store matrices with freshly joined predictions."""
    subprocess.run([
        "dbt", "run",
        "--exclude", "fct_exact_path_resolution",
        "--project-dir", DBT_PROJECT_DIR
    ], check=True)
    return True

@asset(deps=[crypto_features_dbt])
def hyperliquid_execution():
    """Routes limit orders to exchange ONLY if feature build succeeds."""
    subprocess.run(["python3", "execute_hyperliquid_testnet.py"], check=True)
    return True

# ==============================================================================
# 2. DAILY MAINTENANCE & INGESTION TASKS
# ==============================================================================

@asset
def daily_incremental_ingest():
    """Daily incremental ingestion job."""
    subprocess.run(["python3", "daily_incremental_ingest.py"], check=True)
    return True

# ==============================================================================
# 3. WEEKLY OPTUNA MODEL RETRAINING
# ==============================================================================

@asset
def optuna_model_retraining():
    """Weekly hyperparameter & model sweep."""
    subprocess.run(["python3", "run_optuna_sweep.py"], check=True)
    return True

# ==============================================================================
# 4. JOBS AND SCHEDULE DEFINITIONS
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

optuna_job = define_asset_job(
    name="weekly_optuna_job",
    selection=[optuna_model_retraining]
)

optuna_schedule = ScheduleDefinition(
    job=optuna_job,
    cron_schedule="30 2 * * 0",
    default_status=DefaultScheduleStatus.RUNNING
)

# ==============================================================================
# 5. DAGSTER DEFINITIONS REGISTRY
# ==============================================================================

defs = Definitions(
    assets=[
        market_data_sync,
        timesfm_forecast,
        crypto_features_dbt,
        hyperliquid_execution,
        daily_incremental_ingest,
        optuna_model_retraining,
    ],
    schedules=[
        trading_schedule,
        daily_schedule,
        optuna_schedule,
    ],
)
