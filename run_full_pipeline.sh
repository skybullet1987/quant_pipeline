#!/bin/bash
# Exit instantly if any step fails
set -e

echo "[1/5] Running dbt: OHLCV Densification..."
dbt run --select stg_densified_ohlcv

echo "[2/5] Running BigQuery ML: TimesFM 2.5 Forecast..."
bq query --use_legacy_sql=false '
CREATE OR REPLACE TABLE `parnasa-498503.market_data.stg_timesfm_raw` AS
SELECT * 
FROM AI.FORECAST(
  (
    SELECT ticker, timestamp, close AS close_price
    FROM `parnasa-498503.market_data.stg_densified_ohlcv`
  ),
  data_col => "close_price",
  timestamp_col => "timestamp",
  id_cols => ["ticker"],
  horizon => 24, 
  model => "TimesFM 2.5"
);
'

echo "[3/5] Running dbt: Feature Compilation & Volume Filtering..."
# Runs the downstream TimesFM delta calcs, then joins into features_matrix
dbt run --select fct_timesfm_features features_matrix

echo "[4/5] Retraining Models: CatBoost & HMM Optuna (This will take hours)..."
python train_optuna_models.py

echo "[5/5] Wiping Telemetry & Launching Live Daemon..."
rm -f live_execution_telemetry.db
python execute_hyperliquid_testnet.py
