import re

file_path = "execute_hyperliquid_testnet.py"
with open(file_path, "r") as f:
    code = f.read()

# Replace entry thresholds and leverage parameters
code = re.sub(r"ENTRY_THRESHOLD_SHORT\s*,\s*ENTRY_THRESHOLD_LONG\s*=\s*[\d\.\s,]+", "ENTRY_THRESHOLD_SHORT, ENTRY_THRESHOLD_LONG = 0.56, 0.60", code)
code = re.sub(r"KELLY_FRACTION_SHORT\s*,\s*KELLY_FRACTION_LONG\s*=\s*[\d\.\s,]+", "KELLY_FRACTION_SHORT, KELLY_FRACTION_LONG = 0.50, 0.20", code)

with open(file_path, "w") as f:
    f.write(code)

print("[SUCCESS] Live Execution Daemon updated to Master Conditional Allocator parameters!")
