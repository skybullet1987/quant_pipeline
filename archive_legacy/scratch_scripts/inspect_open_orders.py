import os, requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path.home() / "quant_pipeline" / ".env")
WALLET = os.getenv("HYPERLIQUID_ACCOUNT_ADDRESS", "0x9703b71686219d34869e8fb89a93263f9e0d50a5").lower().strip()
INFO_URL = "https://api.hyperliquid-testnet.xyz/info"

orders = requests.post(INFO_URL, json={"type": "openOrders", "user": WALLET}, timeout=10).json()

print(f"=== LIVE OPEN ORDERS ON TESTNET ({len(orders)}) ===")
for o in orders:
    side = "BUY" if o.get("side") == "B" else "SELL"
    print(f"• {o.get('coin'):<10} | {side:<4} | Size: {o.get('sz'):<10} | Limit Px: ${float(o.get('limitPx', 0)):<10.4f} | OID: {o.get('oid')}")
