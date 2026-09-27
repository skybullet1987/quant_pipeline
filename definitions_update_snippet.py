"""
Verify your definitions.py includes the new assets.
"""
import os

defs_path = os.path.expanduser("~/quant_pipeline/definitions.py")
print(f"Checking {defs_path}...")

# Example structure inside definitions.py:
# from assets.model_pipeline_assets import fct_4h_model_signals, dispatched_trading_orders
#
# defs = Definitions(
#     assets=[..., fct_4h_model_signals, dispatched_trading_orders],
#     schedules=[...],
# )
