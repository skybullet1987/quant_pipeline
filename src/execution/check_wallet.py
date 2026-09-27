import sys
from hyperliquid.info import Info
from hyperliquid.utils import constants

if len(sys.argv) < 2:
    print("Usage: python src/execution/check_wallet.py <WALLET_ADDRESS>")
    sys.exit(1)

wallet = sys.argv[1].strip()
info = Info(constants.MAINNET_API_URL, skip_ws=True)

try:
    user_state = info.user_state(wallet)
    ms = user_state.get("marginSummary", {})
    cms = user_state.get("crossMarginSummary", {})
    
    positions = []
    for p in user_state.get("assetPositions", []):
        pos = p.get("position", {})
        coin = pos.get("coin")
        szi = float(pos.get("szi", 0.0))
        if szi != 0:
            positions.append(f"{coin}: {szi} (entry: {pos.get('entryPx')})")
            
    print("\n" + "=" * 65)
    print(f"Target Wallet : {wallet}")
    print(f"Account Value : ${ms.get('accountValue', cms.get('accountValue', '0.00'))} USDC")
    print(f"Active Positions ({len(positions)}): {positions}")
    print("=" * 65 + "\n")
except Exception as e:
    print(f"Error checking wallet {wallet}: {e}")
