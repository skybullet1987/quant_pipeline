import sys
import os
import pandas as pd
import numpy as np
from google.cloud import bigquery

# Import functions/constants from audit_3month_backtest
import audit_3month_backtest as base

print("="*80)
print("📊 RUNNING REAL EMPIRICAL RISK CAP GRID ON BIGQUERY 90-DAY DATA")
print("="*80)

# We will run audit_3month_backtest with dynamic risk limits
# Let's inspect baseline execution
base.main()
