#!/bin/bash
# Redirect all output and errors to a master log file
exec > /home/skybullet1987/quant_pipeline/full_retrain_and_backtest.log 2>&1
set -e # Abort the sequence immediately if any script crashes

echo "====================================================================="
echo "  STARTING FULL 207-COIN PIPELINE RETRAIN & PHASE 2 BACKTEST"
echo "  Timestamp: $(date -u)"
echo "====================================================================="

source /home/skybullet1987/quant_pipeline/venv/bin/activate
cd /home/skybullet1987/quant_pipeline

echo -e "\n---> [1/5] Backfilling TimesFM & Derivatives for 207 Assets..."
python3 backfill_timesfm.py
python3 sync_latest_derivatives.py

echo -e "\n---> [2/5] Rebuilding Full dbt Matrix & Path Resolution Targets..."
cd /home/skybullet1987/quant_pipeline/crypto_features
# We MUST include path resolution here so the new coins have training targets
dbt run --full-refresh
cd /home/skybullet1987/quant_pipeline

echo -e "\n---> [3/5] Retraining HMM Regime Detector on 207-Coin Volatility..."
python3 hmm_regime_detector.py

echo -e "\n---> [4/5] Retraining CatBoost Experts & Meta-Labelers..."
python3 train_production_models.py

echo -e "\n---> [5/5] Running Phase 2 Asymmetric Backtest on New Universe..."
python3 simulate_production_engine.py

echo -e "\n====================================================================="
echo "  SEQUENCE COMPLETE. WAITING FOR MANUAL REVIEW BEFORE TRADING."
echo "  Timestamp: $(date -u)"
echo "====================================================================="
