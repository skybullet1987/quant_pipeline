#!/usr/bin/env python3
import os
import math
from eth_account import Account
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from dotenv import load_dotenv

load_dotenv(".env")

API_URL = os.getenv("HYPERLIQUID_API_URL", "https://api.hyperliquid-testnet.xyz")
PK = os.getenv("HYPERLIQUID_PRIVATE_KEY")
ADDR = os.getenv("HYPERLIQUID_MASTER_ADDRESS")

def round_sig_figs(val, sig_figs=5):
    """Rounds to max significant figures matching Hyperliquid exchange precision rules."""
    if val == 0: return 0
    return round(val, sig_figs - int(math.floor(math.log10(abs(val)))) - 1)

info = Info(API_URL, skip_ws=True)
exchange = Exchange(Account.from_key(PK), API_URL, account_address=ADDR)

user_state = info.user_state(ADDR)
positions = [p["position"] for p in user_state.get("assetPositions", []) if float(p["position"]["szi"]) != 0]

print("=== ARMING MISSING BRACKET TRIGGERS ===")
for p in positions:
    coin = p["coin"]
    szi = float(p["szi"])
    entry_px = float(p["entryPx"])
    sz = abs(szi)
    is_long = szi > 0

    # Approximate 1.5x ATR at ~3.5% default if feature table not joined
    target_dist = entry_px * 0.035
    tp_px = round_sig_figs(entry_px + target_dist if is_long else entry_px - target_dist)
    sl_px = round_sig_figs(entry_px - target_dist if is_long else entry_px + target_dist)

    print(f"\nPosition: {coin} | {'LONG' if is_long else 'SHORT'} {sz} @ ${entry_px}")
    print(f" -> Submitting TP: ${tp_px} | SL: ${sl_px}")

    # TP Trigger
    tp_res = exchange.order(
        coin, not is_long, sz, tp_px,
        {"trigger": {"isMarket": True, "triggerPx": tp_px, "tpsl": "tp"}},
        reduce_only=True
    )
    print(f" -> TP Response: {tp_res}")

    # SL Trigger
    sl_res = exchange.order(
        coin, not is_long, sz, sl_px,
        {"trigger": {"isMarket": True, "triggerPx": sl_px, "tpsl": "sl"}},
        reduce_only=True
    )
    print(f" -> SL Response: {sl_res}")

