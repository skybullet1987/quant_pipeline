import os
import sys
import logging
import datetime
import subprocess

PIPELINE_DIR = "/home/skybullet1987/quant_pipeline"
VENV_BIN = os.path.join(PIPELINE_DIR, "venv/bin")
LOG_FILE = os.path.join(PIPELINE_DIR, "daily_ingest.log")

PYTHON_EXEC = os.path.join(VENV_BIN, "python3")
DBT_EXEC = os.path.join(VENV_BIN, "dbt")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def run_command_live(command, step_name, cwd=PIPELINE_DIR):
    logging.info(f"Starting: {step_name}...")
    print(f"\n==================================================")
    print(f"  [RUNNING]: {step_name}")
    print(f"==================================================")
    
    env = os.environ.copy()
    env["PATH"] = f"{VENV_BIN}:" + env.get("PATH", "")

    # Stream output live to terminal while recording to log
    process = subprocess.Popen(
        command, 
        shell=True, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.STDOUT, 
        text=True, 
        cwd=cwd, 
        env=env
    )

    full_output = []
    for line in process.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()
        full_output.append(line)

    process.wait()
    
    output_str = "".join(full_output)
    if process.returncode == 0:
        logging.info(f"Completed successfully: {step_name}")
        logging.info(f"Output:\n{output_str.strip()}")
    else:
        logging.error(f"Failed: {step_name}")
        logging.error(f"Error:\n{output_str.strip()}")
        raise RuntimeError(f"Step '{step_name}' failed.")

def main():
    logging.info("="*60)
    logging.info("STARTING AUTOMATED PIPELINE EXECUTION SEQUENCE")
    logging.info("="*60)

    try:
        # STEP 1: Sync latest market data from Binance API
        run_command_live(f"{PYTHON_EXEC} sync_latest_ohlcv.py"
        run_command_live(f"{PYTHON_EXEC} sync_1h_ohlcv.py", "1H Market Data Sync")", "Incremental Market Data Sync")

        # STEP 2: Execute dbt transformation models (Includes BQML TimesFM 2.5)
        crypto_features_dir = os.path.join(PIPELINE_DIR, "crypto_features")
        run_command_live(f"{DBT_EXEC} run", "dbt Transformation Suite", cwd=crypto_features_dir)

        # STEP 3: Run dbt data quality tests
        run_command_live(f"{DBT_EXEC} test", "dbt Data Integrity Tests", cwd=crypto_features_dir)

        # STEP 4: Relabel TBM and regenerate feature_matrix_symmetric.parquet
        run_command_live(f"{PYTHON_EXEC} relabel_tbm.py", "Relabel TBM & Parquet Update")

        # STEP 5: Monthly Retraining Check (Runs on 1st of every month)
        today = datetime.datetime.now(datetime.timezone.utc)
        if today.day == 1:
            logging.info("--- 1ST OF THE MONTH DETECTED: TRIGGERING MODEL RETRAINING ---")
            run_command_live(f"{PYTHON_EXEC} build_model_bundle.py", "Monthly Production Model Retraining")

        print("\n[SUCCESS] Entire Pipeline Executed and Auto-Healed Cleanly!")

    except Exception as e:
        print(f"\n[CRITICAL ERROR] Pipeline failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
