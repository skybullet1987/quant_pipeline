import re

path = 'execution/hyperliquid_executor.py'
with open(path, 'r') as f:
    code = f.read()

# 1. Clean out any malformed/nested getattr calls
code = re.sub(r'getattr\(order,\s*getattr\(order,\s*["\'](\w+)["\'],\s*[\d\.]+\)\)', r'getattr(order, "\1", 0.0)', code)

# 2. Normalize to standard attribute access on order
code = code.replace('getattr(order, "signal_price_binance", 0.0)', 'getattr(order, "signal_price_binance", 0.0)')
code = code.replace('getattr(order, "live_price_hl", 0.0)', 'getattr(order, "live_price_hl", 0.0)')

# If getattr wraps a float directly, replace with direct order attribute access:
code = re.sub(r'getattr\(order,\s*order\.(\w+)\)', r'getattr(order, "\1", 0.0)', code)

with open(path, 'w') as f:
    f.write(code)

print("[SUCCESS] Cleared nested getattr lookups in execution/hyperliquid_executor.py.")
