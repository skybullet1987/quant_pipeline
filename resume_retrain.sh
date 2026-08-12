#!/bin/bash
exec > /home/skybullet1987/quant_pipeline/resume_retrain.log 2>&1
set -e

echo "====================================================================="
echo "  RESUMING PIPELINE SEQUENCE"
echo "====================================================================="

echo "Patching dbt profiles.yml timeout limit to 3600 seconds..."
python3 -c "
import os, re
p = os.path.expanduser('~/.dbt/profiles.yml')
if os.path.exists(p):
    with open(p, 'r') as f: c = f.read()
    if 'timeout_seconds' in c:
        c = re.sub(r'timeout_seconds:\s*\d+', 'timeout_seconds: 3600', c)
    else:
        c = c.replace('type: bigquery', 'type: bigquery\n      timeout_seconds: 3600')
    with open(p, 'w') as f: f.write(c)
    print('Successfully patched ~/.dbt/profiles.yml')
"

source /home/skybullet1987/quant_pipeline/venv/bin/activate

echo -e "\n---> [1/3] Finishing dbt build (fct_exact_path_resolution)..."
cd /home/skybullet1987/quant_pipeline/crypto_features
dbt run --select fct_exact_path_resolution
cd /home/skybullet1987/quant_pipeline

echo -e "\n---> [2/3] Retraining ML Models on 207-Coin Matrix..."
python3 hmm_regime_detector.py
python3 train_production_models.py

echo -e "\n---> [3/3] Running Phase 2 Asymmetric Backtest..."
python3 simulate_production_engine.py

echo -e "\n====================================================================="
echo "  SEQUENCE COMPLETE. READY FOR TRADING."
echo "====================================================================="
