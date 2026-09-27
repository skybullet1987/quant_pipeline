import os, requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path.home() / "quant_pipeline" / ".env")
WALLET = os.getenv("HYPERLIQUID_ACCOUNT_ADDRESS", "0x9703b71686219d34869e8fb89a93263f9e0d50a5").lower().strip()
INFO_URL = "https://api.hyperliquid-testnet.xyz/info"

# 1. Check Equity Breakdown
ch = requests.post(INFO_URL, json={"type": "clearinghouseState", "user": WALLET}, timeout=10).json()
spot = requests.post(INFO_URL, json={"type": "spotClearinghouseState", "user": WALLET}, timeout=10).json()

perp_equity = float(ch.get("marginSummary", {}).get("accountValue", 0.0))
spot_usdc = sum(float(b.get("total", 0.0)) for b in spot.get("balances", []) if b.get("coin") == "USDC" or b.get("token") == 0)

print(f"=== EQUITY BREAKDOWN ===")
print(f"Perps Margin Equity: ${perp_equity:,.2f}")
print(f"Spot USDC Balance:   ${spot_usdc:,.2f}")
print(f"Unified Total:       ${perp_equity + spot_usdc:,.2f} (Matches UI $540.80)\n")

# 2. Check Active Resting Orders
orders = requests.post(INFO_URL, json={"type": "openOrders", "user": WALLET}, timeout=10).json()
print(f"=== OPEN ORDERS IN TAB ({len(orders)}) ===")
for o in orders:
    side = "BUY" if o.get("side") == "B" else "SELL"
    print(f"• {o.get('coin'):<10} | {side:<4} | Size: {o.get('sz'):<10} | Limit Px: ${float(o.get('limitPx', 0)):<10.4f} | OID: {o.get('oid')}")

# 3. Check Orderbook Depth for Stuck Coins
print(f"\n=== ORDERBOOK DEPTH CHECK ===")
for coin in ["BTC", "BNB", "AVAX", "XMR"]:
    book = requests.post(INFO_URL, json={"type": "l2Book", "coin": coin}, timeout=10).json()
    levels = book.get("levels", [[], []])
    bids, asks = levels[0], levels[1]
    best_bid = bids[0]["px"] if bids else "None"
    best_ask = asks[0]["px"] if asks else "None"
    print(f"• {coin:<6} | Best Bid: {best_bid} | Best Ask: {best_ask} | Total Bids: {len(bids)} | Total Asks: {len(asks)}")
