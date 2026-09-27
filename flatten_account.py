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

print("1. Cancelling all resting & trigger orders...")
# Standard open orders
for o in info.open_orders(master_addr):
    try:
        exchange.cancel(o["coin"], o["oid"])
        print(f"  • Cancelled resting order {o['coin']} ({o['oid']})")
    except Exception as e:
        print(f"  • Cancel failed: {e}")

# Frontend/trigger orders
for o in info.frontend_open_orders(master_addr):
    try:
        exchange.cancel(o["coin"], o["oid"])
        print(f"  • Cancelled trigger {o['coin']} ({o['oid']})")
    except Exception as e:
        print(f"  • Trigger cancel failed: {e}")

print("\n2. Closing all open positions...")
user_state = info.user_state(master_addr)
for p in user_state.get("assetPositions", []):
    coin = p["position"]["coin"]
    sz = float(p["position"]["szi"])
    if sz != 0:
        res = exchange.market_close(coin)
        print(f"  • Market Closed {coin} (Size: {sz}) -> {res.get('status')}")

print("\n[SUCCESS] Account is completely flat.")
