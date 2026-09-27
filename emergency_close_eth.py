import os
import eth_account
from dotenv import load_dotenv
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

load_dotenv()
secret_key = os.getenv("HYPERLIQUID_PRIVATE_KEY")
account = eth_account.Account.from_key(secret_key)
base_url = constants.TESTNET_API_URL
master_addr = os.getenv("HYPERLIQUID_MASTER_ADDRESS", "0x9703B71686219D34869e8FB89a93263f9e0d50A5")

info = Info(base_url, skip_ws=True)
exchange = Exchange(account, base_url, account_address=master_addr)

# 1. Cancel all resting orders for ETH
open_orders = info.open_orders(master_addr)
for order in open_orders:
    if order.get("coin") == "ETH":
        try:
            exchange.cancel("ETH", order["oid"])
        except Exception:
            pass

# 2. Get exact live Oracle and Mark price
meta, asset_ctxs = info.meta_and_asset_ctxs()
eth_idx = next(i for i, a in enumerate(meta["universe"]) if a["name"] == "ETH")
eth_ctx = asset_ctxs[eth_idx]

oracle_px = float(eth_ctx["oraclePx"])
mark_px = float(eth_ctx["markPx"])
sz_decimals = meta["universe"][eth_idx]["szDecimals"]

# 3. Position size
user_state = info.user_state(master_addr)
eth_pos = next((p for p in user_state.get("assetPositions", []) if p["position"]["coin"] == "ETH"), None)

if not eth_pos or float(eth_pos["position"]["szi"]) == 0:
    print("[SUCCESS] Position is already flat.")
    exit(0)

pos_sz = round(abs(float(eth_pos["position"]["szi"])), sz_decimals)

# 4. Limit price locked directly to Oracle Price (+0.05% max)
target_px = round(oracle_px * 1.0005, 1)

print(f"Oracle: ${oracle_px} | Mark: ${mark_px} | Target Buy: ${target_px} | Size: {pos_sz} ETH")

result = exchange.order(
    name="ETH",
    is_buy=True,
    sz=pos_sz,
    limit_px=target_px,
    order_type={"limit": {"tif": "Gtc"}},
    reduce_only=True
)
print("Execution Result:", result)
