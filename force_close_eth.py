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

print("1. Cancelling all open & trigger orders...")
# Cancel standard open orders
open_orders = info.open_orders(master_addr)
for o in open_orders:
    if o.get("coin") == "ETH":
        try:
            exchange.cancel("ETH", o["oid"])
            print(f"• Cancelled resting order oid: {o['oid']}")
        except Exception as e:
            print(f"Cancel error: {e}")

# Cancel frontend/trigger orders (TP/SL)
frontend_orders = info.frontend_open_orders(master_addr)
for o in frontend_orders:
    if o.get("coin") == "ETH":
        try:
            exchange.cancel("ETH", o["oid"])
            print(f"• Cancelled trigger order oid: {o['oid']}")
        except Exception as e:
            print(f"Trigger cancel error: {e}")

# 2. Check live ETH position
user_state = info.user_state(master_addr)
eth_pos = next((p for p in user_state.get("assetPositions", []) if p["position"]["coin"] == "ETH"), None)

if not eth_pos or float(eth_pos["position"]["szi"]) == 0:
    print("\n[SUCCESS] ETH position is already flat!")
    exit(0)

sz = abs(float(eth_pos["position"]["szi"]))
print(f"\n2. Active ETH Short Position: {sz} ETH")

# 3. Fetch exact Oracle and L2 Market Data
meta, asset_ctxs = info.meta_and_asset_ctxs()
eth_idx = next(i for i, a in enumerate(meta["universe"]) if a["name"] == "ETH")
oracle_px = float(asset_ctxs[eth_idx]["oraclePx"])
sz_dec = meta["universe"][eth_idx]["szDecimals"]

# 4. Set limit price right at oracle to satisfy Hyperliquid's deviation filter
target_px = round(oracle_px * 1.0005, 1)

print(f"3. Placing GTC Buy (Reduce-Only): {sz} ETH @ ${target_px} (Oracle: ${oracle_px})...")
order_res = exchange.order(
    name="ETH",
    is_buy=True,
    sz=round(sz, sz_dec),
    limit_px=target_px,
    order_type={"limit": {"tif": "Gtc"}},
    reduce_only=True
)
print("Order Response:", order_res)
