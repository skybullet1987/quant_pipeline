import os
import eth_account
from dotenv import load_dotenv
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

load_dotenv()
secret_key = os.getenv("HYPERLIQUID_PRIVATE_KEY")
account = eth_account.Account.from_key(secret_key)
master_addr = os.getenv("HYPERLIQUID_MASTER_ADDRESS", "0x9703B71686219D34869e8FB89a93263f9e0d50A5")

info = Info(constants.TESTNET_API_URL, skip_ws=True)
exchange = Exchange(account, constants.TESTNET_API_URL, account_address=master_addr)

# Cancel resting trigger orders for ETH
open_orders = info.open_orders(master_addr)
for order in open_orders:
    if order.get("coin") == "ETH":
        try:
            exchange.cancel("ETH", order["oid"])
            print(f"Cancelled resting order oid: {order['oid']}")
        except Exception:
            pass

# Execute native market close
res = exchange.market_close("ETH")
print("Close Response:", res)
