import os, requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path.home() / "quant_pipeline" / ".env")
WALLET = os.getenv("HYPERLIQUID_ACCOUNT_ADDRESS", "0x9703b71686219d34869e8fb89a93263f9e0d50a5").lower().strip()
INFO_URL = "https://api.hyperliquid-testnet.xyz/info"

ch = requests.post(INFO_URL, json={"type": "clearinghouseState", "user": WALLET}, timeout=10).json()
equity = float(ch.get("marginSummary", {}).get("accountValue", 0.0))
positions = [
    f"{p['position']['coin']}: {float(p['position']['szi']):+g} (Entry: ${float(p['position']['entryPx']):.4f})"
    for p in ch.get("assetPositions", [])
    if float(p.get("position", {}).get("szi", 0.0)) != 0
]

print(f"Live Portfolio Equity: ${equity:,.2f}")
print(f"Active Positions ({len(positions)}):")
for pos in positions:
    print(f"  • {pos}")
