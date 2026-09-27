import os, sys, subprocess
from dagster import asset, Output, OpExecutionContext

PROJECT_ROOT = os.getenv("QUANT_PROJECT_ROOT", "/home/skybullet1987/quant_pipeline")
PYTHON_EXEC = sys.executable

def run_command(cmd, context: OpExecutionContext):
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    for line in iter(proc.stdout.readline, ""):
        if line:
            context.log.info(line.strip())
    proc.stdout.close()
    return_code = proc.wait()
    if return_code != 0:
        raise subprocess.CalledProcessError(return_code, cmd)

@asset(group_name="market_data", compute_kind="python")
def ingest_hyperliquid_candles_4h(context: OpExecutionContext):
    """Fetches latest 1M candles from Hyperliquid and merges into BigQuery."""
    script = os.path.join(PROJECT_ROOT, "scripts/ingest_hyperliquid_candles.py")
    run_command([PYTHON_EXEC, "-u", script], context)
    return Output(value="ingested", metadata={"status": "success"})

@asset(group_name="features", deps=[ingest_hyperliquid_candles_4h], compute_kind="dbt")
def dbt_fct_4h_features_production(context: OpExecutionContext):
    """Materializes clean resampled 4H feature matrix in BigQuery."""
    run_command(["dbt", "run", "--select", "fct_4h_features_production", "--project-dir", PROJECT_ROOT], context)
    return Output(value="dbt_complete")

@asset(group_name="execution", deps=[dbt_fct_4h_features_production], compute_kind="hyperliquid")
def execute_trading_decisions(context: OpExecutionContext):
    """Runs online Causal HMM, CatBoost inference, and manages Hyperliquid bracket orders."""
    script = os.path.join(PROJECT_ROOT, "scripts/execute_hyperliquid_production.py")
    run_command([PYTHON_EXEC, "-u", script, "--testnet"], context)
    return Output(value="executed")
