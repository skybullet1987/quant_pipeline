from hyperliquid.info import Info
from hyperliquid.utils import constants

info = Info(constants.MAINNET_API_URL, skip_ws=True)
addresses = [
    "0x9703B71686219D34869e8FB89a93263f9e0d50A5",
    "0xA426209CFb39A3040aE9316d25f5875584236955"
]

for addr in addresses:
    print("\n" + "=" * 65)
    print(f"INSPECTING ADDRESS: {addr}")
    print("=" * 65)

    # 1. Perps User State
    try:
        user_state = info.user_state(addr)
        ms = user_state.get("marginSummary", {})
        cms = user_state.get("crossMarginSummary", {})
        positions = []
        for p in user_state.get("assetPositions", []):
            pos_dict = p.get("position", {})
            coin = pos_dict.get("coin")
            szi = float(pos_dict.get("szi", 0.0))
            if szi != 0:
                positions.append(f"{coin}: {szi} @ {pos_dict.get('entryPx')}")
        print(f"Perps marginSummary accountValue      : ${ms.get('accountValue', '0')} USDC")
        print(f"Perps crossMarginSummary accountValue : ${cms.get('accountValue', '0')} USDC")
        print(f"Perps Active Positions ({len(positions)}): {positions}")
    except Exception as e:
        print(f"Error fetching perps state: {e}")

    # 2. Spot Clearinghouse State
    try:
        spot_state = info.spot_user_state(addr)
        balances = spot_state.get("balances", [])
        print(f"Spot Balances                         : {balances}")
    except Exception as e:
        print(f"Error fetching spot state: {e}")

    # 3. WebData2 Unified Summary
    try:
        web_data = info.post("/info", {"type": "webData2", "user": addr})
        clearing = web_data.get("clearinghouseState", {})
        spot_data = web_data.get("spotState", {})
        ms_web = clearing.get("marginSummary", {})
        print(f"WebData2 Perps Account Value          : ${ms_web.get('accountValue', '0')} USDC")
        print(f"WebData2 Spot Balances Count          : {len(spot_data.get('balances', []))}")
    except Exception as e:
        print(f"Error fetching webData2: {e}")

    # 4. Check Sub-accounts
    try:
        sub_accounts = info.post("/info", {"type": "subAccounts", "user": addr})
        if sub_accounts:
            print(f"Sub-accounts found                    : {sub_accounts}")
    except Exception:
        pass
