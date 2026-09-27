import os
import eth_account
from dotenv import load_dotenv
from hyperliquid.info import Info
from hyperliquid.utils import constants

load_dotenv()
info = Info(constants.TESTNET_API_URL, skip_ws=True)
master_addr = os.getenv("HYPERLIQUID_MASTER_ADDRESS")

user_state = info.user_state(master_addr)
spot_state = info.spot_user_state(master_addr)
orders = info.frontend_open_orders(master_addr)

usdc = next((b["total"] for b in spot_state.get("balances", []) if b["coin"] == "USDC"), "0.0")
active = [p for p in user_state.get("assetPositions", []) if float(p["position"]["szi"]) != 0]

print("=" * 60)
print(f"USDC Collateral : ${float(usdc):.2f}")
print(f"Open Positions  : {len(active)}/5")
for p in active:
    pos = p["position"]
    print(f"  • {pos['coin']:<6} | Size: {pos['szi']:>8} | Entry: ${float(pos['entryPx']):.4f} | PnL: ${float(pos['unrealizedPnl']):>+6.2f}")

print(f"Resting Triggers: {len(orders)}")
for o in orders:
    print(f"  • {o.get('coin'):<6} | {o.get('orderType'):<18} | TriggerPx: ${o.get('triggerPx')}")
print("=" * 60)
