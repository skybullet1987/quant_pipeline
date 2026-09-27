import os
import time
import logging
import datetime
import subprocess

PIPELINE_DIR = "/home/skybullet1987/quant_pipeline"
VENV_BIN = os.path.join(PIPELINE_DIR, "venv/bin")
LOG_FILE = os.path.join(PIPELINE_DIR, "orchestrator.log")

logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def run_command(command, cwd=PIPELINE_DIR):
    env = os.environ.copy()
    env["PATH"] = f"{VENV_BIN}:" + env.get("PATH", "")
    logging.info(f"Executing: {command}")
    
    try:
        result = subprocess.run(command, shell=True, cwd=cwd, env=env, check=True, capture_output=True, text=True)
        logging.info(f"Success. Output snippet:\n{result.stdout[-300:]}")
    except subprocess.CalledProcessError as e:
        # Patch: Capturing stdout because dbt logs its errors there, not just stderr
        error_msg = e.stdout if e.stdout else e.stderr
        logging.error(f"Failed. Error Output:\n{error_msg}")

def get_seconds_until_next_interval(interval_minutes=15):
    now = datetime.datetime.now(datetime.timezone.utc)
    minutes = now.minute
    remainder = minutes % interval_minutes
    minutes_to_wait = interval_minutes - remainder
    
    next_time = now + datetime.timedelta(minutes=minutes_to_wait)
    next_time = next_time.replace(second=5, microsecond=0) # 5-second buffer past the minute
    return (next_time - now).total_seconds()

def main():
    logging.info("Starting 15-Minute Quant Pipeline Orchestrator...")
    print("Orchestrator online. Checking terminal log output for details.")
    
    while True:
        wait_seconds = get_seconds_until_next_interval(15)
        logging.info(f"Sleeping for {wait_seconds:.1f} seconds until next execution block...")
        time.sleep(wait_seconds)
        
        logging.info("=== BEGINNING 15-MINUTE EXECUTION CYCLE ===")
        
        # 1. Ingest Market Data
        run_command("python3 sync_latest_ohlcv.py")
        run_command("python3 sync_latest_derivatives.py")
        run_command("python3 forecast_timesfm.py")
        
        # 2. Rebuild Incremental Feature Matrix (EXCLUDING the massive backtest target table)
        run_command("dbt run --exclude fct_exact_path_resolution", cwd=os.path.join(PIPELINE_DIR, "crypto_features"))
        
        # 3. Trigger Live Execution Daemon
        run_command("python3 execute_hyperliquid_testnet.py")
        
        logging.info("=== CYCLE COMPLETE ===")

if __name__ == "__main__":
    main()
