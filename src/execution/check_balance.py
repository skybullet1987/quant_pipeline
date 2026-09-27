import requests
import json

addr = "0x9703b71686219d34869e8fb89a93263f9e0d50a5"
url = "https://api.hyperliquid.xyz/info"
headers = {"Content-Type": "application/json"}

# 1. Fetch Spot Tokens & Spot Contexts
spot_meta = requests.post(url, headers=headers, json={"type": "spotMetaAndAssetCtxs"}).json()
tokens = {t["index"]: t["name"] for t in spot_meta[0]["tokens"]}
spot_ctxs = {ctx["coin"]: float(ctx["markPx"]) for ctx in spot_meta[1]}

spot_state = requests.post(url, headers=headers, json={"type": "spotClearinghouseState", "user": addr}).json()

print("\n--- SPOT HOLDINGS ---")
total_spot_usd = 0.0
for b in spot_state.get("balances", []):
    token_idx = b.get("token")
    token_name = tokens.get(token_idx, b.get("coin", "UNKNOWN"))
    total_qty = float(b.get("total", 0.0))
    if total_qty > 0:
        price = 1.0 if token_name == "USDC" else spot_ctxs.get(f"@{token_idx}", spot_ctxs.get(token_name, 0.0))
        token_usd = total_qty * price
        total_spot_usd += token_usd
        print(f"Token: {token_name:<10} Qty: {total_qty:<15.4f} Price: ${price:<10.4f} USD Value: ${token_usd:,.2f}")

print(f"Total Spot Collateral: ${total_spot_usd:,.2f}")

# 2. Fetch Perp State
perp_state = requests.post(url, headers=headers, json={"type": "clearinghouseState", "user": addr}).json()
perp_val = float(perp_state.get("marginSummary", {}).get("accountValue", 0.0))
perp_pnl = sum(float(p["position"]["unrealizedPnl"]) for p in perp_state.get("assetPositions", []))

print("\n--- PERP STATE ---")
print(f"Perp Account Value : ${perp_val:,.2f}")
print(f"Unrealized Perp PnL: ${perp_pnl:,.2f}")

unified_total = total_spot_usd + perp_pnl if perp_val == 0 else perp_val + total_spot_usd
print(f"\n>>> UNIFIED PORTFOLIO VALUE: ${unified_total:,.2f} <<<\n")
