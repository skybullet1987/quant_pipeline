import os
import re

# Files to patch that currently rely on the old asymmetric column name
files = [
    'simulate_production_engine.py', 
    'train_production_models.py', 
    'audit_insample_engine.py',
    'run_production_backtest.py',
    'run_ev_backtest.py'
]

for filepath in files:
    if not os.path.exists(filepath):
        continue
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Patch BigQuery SQL SELECT blocks embedded in the Python engines
    content = content.replace('p.target_price_3_atr', 'p.target_price_1_5_atr')
    
    # Patch DataFrame row indexing for EV calculations
    content = content.replace("row['target_price_3_atr']", "row['target_price_1_5_atr']")
    
    with open(filepath, 'w') as f:
        f.write(content)
        
print("Python engines successfully patched to use symmetric target_price_1_5_atr.")
