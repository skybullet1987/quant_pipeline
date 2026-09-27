import os
import time
import requests
from pathlib import Path
from dotenv import load_dotenv
from eth_account import Account
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

load_dotenv(Path.home() / "quant_pipeline" / ".env")

WALLET = os.getenv("HYPERLIQUID_ACCOUNT_ADDRESS", "0x9703b71686219d34869e8fb89a93263f9e0d50a5").lower().strip()
PRIV_KEY = os.getenv("HYPERLIQUID_PRIVATE_KEY", "").strip()

if not PRIV_KEY:
    raise ValueError("HYPERLIQUID_PRIVATE_KEY must be set in .env")

account = Account.from_key(PRIV_KEY)
exchange = Exchange(
    account,
    constants.TESTNET_API_URL,
    account_address=WALLET if WALLET != account.address.lower() else None
)

def run_heartbeat():
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting Dead Man's Switch (30s timeout)...")
    while True:
        try:
            # Refresh 30-second countdown exchange-side
            timeout_ms = int(time.time() * 1000) + 30000
            res = exchange.cancel_all_after(timeout_ms)
            if res.get("status") == "ok":
                print(f"[{time.strftime('%H:%M:%S')}] Heartbeat renewed (+30s window).")
            else:
                print(f"[{time.strftime('%H:%M:%S')}] Heartbeat warning: {res}")
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] Heartbeat error: {e}")
        
        time.sleep(10)

if __name__ == "__main__":
    run_heartbeat()
