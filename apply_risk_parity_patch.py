#!/usr/bin/env python3
import re
import shutil
import py_compile
from datetime import datetime, timezone

TARGET_FILE = "execute_hyperliquid_testnet.py"
BACKUP_FILE = f"execute_hyperliquid_testnet.py.bak_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

shutil.copyfile(TARGET_FILE, BACKUP_FILE)
print(f"[BACKUP] Saved clean backup at: {BACKUP_FILE}")

with open(TARGET_FILE, "r") as f:
    code = f.read()

# Target the legacy Kelly sizing block (from kelly_f calculation to approved_orders append)
legacy_sizing_regex = re.compile(
    r"[ \t]*kelly_f = p_win - \(\(1\.0 - p_win\) / 1\.0\).*?"
    r"available_margin_pool -= required_margin",
    re.DOTALL
)

replacement_block = '''        coin_max_lev = float(max_lev_map.get(coin, cand["base_lev"]))
        applied_lev = min(coin_max_lev, cand["base_lev"])
        sz_dec = sz_decimals_map.get(coin, 2)

        # 1. Compute TP/SL barriers first based on volatility
        tp_px = format_hl_price(live_px + (1.50 * cand["atr"]) if is_buy else live_px - (1.50 * cand["atr"]), sz_dec)
        sl_px = format_hl_price(live_px - (1.50 * cand["atr"]) if is_buy else live_px + (1.50 * cand["atr"]), sz_dec)

        # 2. Risk-Budget Sizing (1.0% Equity Risk Target, 2.0% Min SL Floor, Margin/Leverage Caps)
        current_margin_used = max(0.0, (equity * 0.85) - available_margin_pool)
        sz, target_notional, modeled_risk = compute_position_size(
            entry_px=float(live_px),
            sl_px=float(sl_px),
            unified_equity=float(equity),
            total_margin_used=float(current_margin_used),
            sz_decimals=int(sz_dec),
            risk_target_pct=0.010,       # 1.0% modeled risk ($13.40 on $1,340)
            min_sl_distance_pct=0.020,   # 2.0% safety floor against micro-stops
            max_position_equity_pct=0.35,# 35% max equity per position
            max_account_leverage=applied_lev,
            margin_cap_pct=0.85,
            min_notional_usd=15.0        # Hyperliquid min order size
        )

        required_margin = target_notional / applied_lev if applied_lev > 0 else target_notional

        # 3. Validation & Rejection Logging
        if sz <= 0 or required_margin > available_margin_pool:
            logging.info(f"[SIZING REJECT] {coin} (Size: {sz}, Notional: ${target_notional:.2f}, Req Margin: ${required_margin:.2f}, Avail Margin: ${available_margin_pool:.2f})")
            continue

        logging.info(f"[RISK PARITY] {coin} -> Sized: {sz} tokens | Notional: ${target_notional:.2f} | Modeled Risk: ${modeled_risk:.2f} (SL: ${sl_px})")

        approved_orders.append({
            "coin": coin, "is_buy": is_buy, "side": cand["side"], "ev_bps": cand["ev_bps"],
            "notional": target_notional, "margin": required_margin, "sz": sz, "sz_dec": sz_dec,
            "lev": applied_lev, "signal_px": cand["signal_px"], "ref_px": live_px,
            "tp_px": tp_px, "sl_px": sl_px, "modeled_risk": modeled_risk
        })
        available_margin_pool -= required_margin'''

if not legacy_sizing_regex.search(code):
    print("[ERROR] Could not match legacy sizing regex. Inspecting structure...")
else:
    patched_code = legacy_sizing_regex.sub(replacement_block, code, count=1)
    with open(TARGET_FILE, "w") as f:
        f.write(patched_code)
    
    # Syntax compile check
    py_compile.compile(TARGET_FILE, doraise=True)
    print("[SUCCESS] Successfully patched execute_hyperliquid_testnet.py with Risk-Budget sizing!")
