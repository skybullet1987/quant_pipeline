import os
import eth_account
from dotenv import load_dotenv
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

load_dotenv()
secret_key = os.getenv("HYPERLIQUID_PRIVATE_KEY")
account = eth_account.Account.from_key(secret_key)
master_addr = os.getenv("HYPERLIQUID_MASTER_ADDRESS", account.address)

info = Info(constants.TESTNET_API_URL, skip_ws=True)
exchange = Exchange(account, constants.TESTNET_API_URL, account_address=master_addr)

meta, asset_ctxs = info.meta_and_asset_ctxs()
sz_decimals_map = {a["name"]: a["szDecimals"] for a in meta["universe"]}
mids = info.all_mids()

user_state = info.user_state(master_addr)
positions = user_state.get("assetPositions", [])

# Hardcoded barriers for the active entries from your run
# BERA Entry: 0.19452 (Short) -> TP: 0.1876, SL: 0.2053
# IMX Entry: 0.12198 (Short)  -> TP: 0.1173, SL: 0.1288
custom_targets = {
    "BERA": {"is_buy_exit": True, "tp": 0.1876, "sl": 0.2053},
    "IMX":  {"is_buy_exit": True, "tp": 0.1173, "sl": 0.1288}
}

for p in positions:
    coin = p["position"]["coin"]
    sz = abs(float(p["position"]["szi"]))
    if sz == 0 or coin not in custom_targets:
        continue

    sz_dec = sz_decimals_map.get(coin, 2)
    entry_px = float(p["position"]["entryPx"])
    cfg = custom_targets[coin]
    tp_px = cfg["tp"]
    sl_px = cfg["sl"]
    is_buy_exit = cfg["is_buy_exit"]

    print(f"\n--- Attaching Brackets for {coin} ({sz} tokens | Entry: ${entry_px}) ---")

    # 1. Take Profit (Reduce-Only Limit Trigger)
    try:
        tp_res = exchange.order(
            name=coin,
            is_buy=is_buy_exit,
            sz=sz,
            limit_px=tp_px,
            order_type={"trigger": {"isMarket": False, "triggerPx": tp_px, "tpsl": "tp"}},
            reduce_only=True
        )
        print(f"• TP @ ${tp_px} Response:", tp_res)
    except Exception as e:
        print(f"• TP Failed: {e}")

    # 2. Stop Loss (Reduce-Only Market Trigger)
    try:
        sl_res = exchange.order(
            name=coin,
            is_buy=is_buy_exit,
            sz=sz,
            limit_px=round(sl_px * 1.05 if is_buy_exit else sl_px * 0.95, 4),
            order_type={"trigger": {"isMarket": True, "triggerPx": sl_px, "tpsl": "sl"}},
            reduce_only=True
        )
        print(f"• SL @ ${sl_px} Response:", sl_res)
    except Exception as e:
        print(f"• SL Failed: {e}")

