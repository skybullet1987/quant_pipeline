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
user_state = info.user_state(master_addr)
spot_state = info.spot_user_state(master_addr)

usdc = next((b["total"] for b in spot_state.get("balances", []) if b["coin"] == "USDC"), "0.0")
active_positions = [p for p in user_state.get("assetPositions", []) if float(p["position"]["szi"]) != 0]
open_orders = info.open_orders(master_addr)

print("=" * 60)
print(f"USDC Collateral : ${float(usdc):.2f}")
print(f"Open Positions  : {len(active_positions)}")
for p in active_positions:
    print(f"  • {p['position']['coin']}: {p['position']['szi']} @ ${p['position']['entryPx']}")
print(f"Resting Orders  : {len(open_orders)}")
print("=" * 60)
