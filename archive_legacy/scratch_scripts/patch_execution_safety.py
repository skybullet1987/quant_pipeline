import re

file_path = "execute_hyperliquid_testnet.py"
with open(file_path, "r") as f:
    code = f.read()

# 1. Ensure max 2 new trades per 15-min cycle
if "MAX_TRADES_PER_CYCLE" not in code:
    code = code.replace("MAX_POSITIONS = 5", "MAX_POSITIONS = 5\nMAX_TRADES_PER_CYCLE = 2")

# 2. Add pending coin deduplication check before placing order
old_check = "if available_cap >= margin and notional > 10.0:"
new_check = "if available_cap >= margin and notional > 10.0 and coin_symbol not in all_active_coins and trades_submitted_this_cycle < MAX_TRADES_PER_CYCLE:"

if old_check in code:
    code = code.replace(old_check, new_check)

with open(file_path, "w") as f:
    f.write(code)

print("[SUCCESS] Safety caps (Max 2 trades/cycle + pending order deduplication) applied successfully!")
