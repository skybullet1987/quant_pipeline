import os, requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path.home() / "quant_pipeline" / ".env")
WALLET = os.getenv("HYPERLIQUID_ACCOUNT_ADDRESS", "0x9703b71686219d34869e8fb89a93263f9e0d50a5").lower().strip()
INFO_URL = "https://api.hyperliquid-testnet.xyz/info"

fills = requests.post(INFO_URL, json={"type": "userFills", "user": WALLET}, timeout=10).json()

print(f"=== RECENT TESTNET FILLS ({len(fills)}) ===")
for f in fills[:10]:
    side = "BUY" if f.get("side") == "B" else "SELL"
    print(f"• {f.get('coin'):<10} | {side:<4} | Sz: {f.get('sz'):<10} | Px: ${float(f.get('px', 0)):<10.4f} | Fee: ${float(f.get('fee', 0)):.4f} | Time: {f.get('time')}")
