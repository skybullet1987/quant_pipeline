#!/usr/bin/env python3
import shutil
from datetime import datetime

TARGET_FILE = "execute_hyperliquid_testnet.py"
BACKUP_FILE = f"execute_hyperliquid_testnet.py.bak_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

shutil.copyfile(TARGET_FILE, BACKUP_FILE)
print(f"[BACKUP] Created backup at: {BACKUP_FILE}")

with open(TARGET_FILE, "r") as f:
    content = f.read()

sizing_function = '''
def compute_position_size(
    entry_px: float,
    sl_px: float,
    unified_equity: float,
    total_margin_used: float,
    sz_decimals: int,
    risk_target_pct: float = 0.010,       # 1.0% equity risk budget
    min_sl_distance_pct: float = 0.020,   # 2.0% floor to prevent oversized leverage
    max_position_equity_pct: float = 0.35,# 35% max single-asset allocation
    max_account_leverage: float = 3.0,    # 3x maximum nominal account leverage
    margin_cap_pct: float = 0.85,         # 85% unified margin ceiling
    min_notional_usd: float = 15.0        # Hyperliquid exchange min order size
) -> tuple[float, float, float]:
    """
    Risk-budget position sizing with strict hierarchical constraint waterfall:
    Risk Budget -> Effective SL -> Notional -> Hard Position/Margin/Leverage Caps.
    Returns: (size_tokens, final_notional, modeled_dollar_risk)
    """
    if unified_equity <= 0 or entry_px <= 0 or sl_px <= 0:
        return 0.0, 0.0, 0.0

    # 1. Calculate actual distance to stop trigger with safety floor
    raw_sl_distance = abs(entry_px - sl_px) / entry_px
    effective_sl_distance = max(raw_sl_distance, min_sl_distance_pct)

    # 2. Unconstrained dollar risk budget & notional
    risk_budget_usd = unified_equity * risk_target_pct
    risk_based_notional = risk_budget_usd / effective_sl_distance

    # 3. Hard Safety Ceilings
    max_notional_by_position = unified_equity * max_position_equity_pct
    max_notional_by_leverage = unified_equity * max_account_leverage
    available_margin = max(0.0, (unified_equity * margin_cap_pct) - total_margin_used)

    # 4. Hierarchical min() clamping
    final_notional = min(
        risk_based_notional,
        max_notional_by_position,
        max_notional_by_leverage,
        available_margin
    )

    # 5. Min Notional Gate
    if final_notional < min_notional_usd:
        return 0.0, 0.0, 0.0

    # 6. Apply Lot Precision
    raw_tokens = final_notional / entry_px
    size_tokens = round(raw_tokens, sz_decimals) if sz_decimals > 0 else float(int(raw_tokens))
    realized_notional = size_tokens * entry_px
    modeled_risk = realized_notional * raw_sl_distance

    return size_tokens, realized_notional, modeled_risk
'''

if "def compute_position_size" not in content:
    # Insert function after imports
    import_marker = "import "
    last_import_idx = content.rfind("\nimport ")
    if last_import_idx == -1:
        last_import_idx = content.rfind("\nfrom ")
    end_of_line = content.find("\n", last_import_idx + 1)
    
    patched_content = content[:end_of_line + 1] + sizing_function + content[end_of_line + 1:]
    
    with open(TARGET_FILE, "w") as f:
        f.write(patched_content)
    print("[SUCCESS] Injected compute_position_size into execute_hyperliquid_testnet.py")
else:
    print("[INFO] compute_position_size already present in file.")
