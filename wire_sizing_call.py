#!/usr/bin/env python3
import re
import shutil
from datetime import datetime, timezone

TARGET_FILE = "execute_hyperliquid_testnet.py"
BACKUP_FILE = f"execute_hyperliquid_testnet.py.bak_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

shutil.copyfile(TARGET_FILE, BACKUP_FILE)
print(f"[BACKUP] Saved: {BACKUP_FILE}")

with open(TARGET_FILE, "r") as f:
    code = f.read()

# Replace legacy sizing calculations (slot_notional / entry_px patterns)
# Pattern matching common slot sizing assignments
legacy_pattern = r"([ \t]*)(?:slot_notional\s*=\s*[^\n]+|raw_size\s*=\s*[^\n]+|size_tokens\s*=\s*round[^\n]+)+"

replacement_block = r'''\1# --- RISK-PARITY VOLATILITY SIZING ---
\1size_tokens, final_notional, modeled_risk = compute_position_size(
\1    entry_px=float(entry_px),
\1    sl_px=float(sl_px),
\1    unified_equity=float(unified_equity),
\1    total_margin_used=float(total_margin_used),
\1    sz_decimals=int(sz_decimals),
\1    risk_target_pct=0.010,
\1    min_sl_distance_pct=0.020,
\1    max_position_equity_pct=0.35,
\1    margin_cap_pct=0.85
\1)
\1if size_tokens <= 0:
\1    logger.warning(f"[{symbol}] Sizing constraint rejected (Notional: ${final_notional:.2f}). Skipping.")
\1    continue
\1logger.info(f"[{symbol}] Risk-Parity Sizing: {size_tokens} tokens | Notional: ${final_notional:.2f} | Modeled Risk: ${modeled_risk:.2f}")'''

# If slot_notional exists, substitute it; otherwise replace direct size calculations
if "slot_notional" in code:
    code = re.sub(r"[ \t]*slot_notional\s*=\s*[^\n]+(?:\n[ \t]*raw_size\s*=\s*[^\n]+)?(?:\n[ \t]*size_tokens\s*=\s*[^\n]+)?", replacement_block, code, count=1)
elif "raw_size" in code and "compute_position_size(" not in code.split("def compute_position_size")[1]:
    code = re.sub(r"[ \t]*raw_size\s*=\s*[^\n]+(?:\n[ \t]*size_tokens\s*=\s*[^\n]+)?", replacement_block, code, count=1)

with open(TARGET_FILE, "w") as f:
    f.write(code)

print("[SUCCESS] Patched call site in execute_hyperliquid_testnet.py")
