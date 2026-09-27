import sys
import json
from pathlib import Path

PIPELINE_ROOT = Path.home() / "quant_pipeline"
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

import eth_account
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

CONFIG_FILE = PIPELINE_ROOT / "config" / "secrets.json"

def cancel_all():
    with open(CONFIG_FILE, "r") as f:
        secrets = json.load(f)

    account_address = secrets["account_address"]
    secret_key = secrets["secret_key"]

    info = Info(constants.MAINNET_API_URL, skip_ws=True)
    account = eth_account.Account.from_key(secret_key)
    exchange = Exchange(account, constants.MAINNET_API_URL, account_address=account_address)

    open_orders = info.open_orders(account_address)
    print(f"[PURGE] Found {len(open_orders)} open orders for {account_address}")

    if not open_orders:
        print("[PURGE] No open orders to cancel.")
        return

    for order in open_orders:
        sym = order["coin"]
        oid = order["oid"]
        try:
            res = exchange.cancel(sym, oid)
            print(f"[CANCELED] {sym:<10} Order ID: {oid} -> {res['status']}")
        except Exception as e:
            print(f"[ERROR] Failed to cancel {sym} {oid}: {e}")

    print("\n[PURGE] All open orders cleared successfully.")

if __name__ == "__main__":
    cancel_all()
