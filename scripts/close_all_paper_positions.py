#!/usr/bin/env python3
"""
EMERGENCY FLATTEN & PAUSE SCRIPT
=================================
1. Cancels all open orders (maker limit, stop-loss, take-profit triggers) on Hyperliquid Testnet.
2. Flattens all active positions to zero USDC notional via reduce-only orders.
3. Updates papertrade state to PAUSED.
"""

import os
import sys
import time
import json
from pathlib import Path
from dotenv import load_dotenv

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PIPELINE_ROOT))

load_dotenv(PIPELINE_ROOT / ".env")

from eth_account import Account
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants


def main():
    print("=" * 80)
    print("      HYPERLIQUID TESTNET: CANCEL ALL ORDERS & FLATTEN ALL POSITIONS")
    print("=" * 80)

    network_url = constants.TESTNET_API_URL
    priv_key = os.getenv("HYPERLIQUID_PRIVATE_KEY") or os.getenv("HYPERLIQUID_API_KEY")
    if not priv_key:
        print("[ERROR] HYPERLIQUID_PRIVATE_KEY is not configured in .env.")
        return

    account = Account.from_key(priv_key)
    wallet = os.getenv("HYPERLIQUID_ACCOUNT_ADDRESS", account.address).lower().strip()
    is_agent = (wallet != account.address.lower())

    print(f"Connecting to Testnet API: {network_url}")
    print(f"Signer Address: {account.address}")
    print(f"Account Wallet: {wallet}")

    info = Info(network_url, skip_ws=True)
    exchange = Exchange(account, network_url, account_address=wallet if is_agent else None)

    # 1. Cancel All Open Orders
    print("\n[1/3] Fetching and Cancelling Active Open Orders...")
    try:
        open_orders = info.frontend_open_orders(wallet)
        print(f"Found {len(open_orders)} open orders.")
        for o in open_orders:
            coin = o["coin"]
            oid = o["oid"]
            try:
                res = exchange.cancel(coin, oid)
                print(f"  Cancelled order for {coin} (OID: {oid}): {res.get('status')}")
            except Exception as e:
                print(f"  Failed to cancel order {oid} on {coin}: {e}")
    except Exception as e:
        print(f"Error fetching open orders: {e}")

    # 2. Query and Flatten Active Positions
    print("\n[2/3] Fetching Active Open Positions...")
    try:
        user_state = info.user_state(wallet)
        margin_summary = user_state.get("marginSummary", {})
        account_value = float(margin_summary.get("accountValue", 0.0))
        print(f"Account Value: ${account_value:.2f} USDC")

        asset_positions = user_state.get("assetPositions", [])
        active_positions = []
        for p in asset_positions:
            pos = p.get("position", {})
            coin = pos.get("coin")
            szi = float(pos.get("szi", 0.0))
            if abs(szi) > 1e-5:
                active_positions.append({
                    "coin": coin,
                    "szi": szi,
                    "entry_px": float(pos.get("entryPx", 0.0)),
                    "unrealized_pnl": float(pos.get("unrealizedPnl", 0.0))
                })

        print(f"Found {len(active_positions)} active positions to flatten:")
        for ap in active_positions:
            coin = ap["coin"]
            szi = ap["szi"]
            print(f"  * {coin:<10}: Size = {szi:+.4f} (uPnL: ${ap['unrealized_pnl']:+.2f})")
            try:
                print(f"    Executing market_close for {coin}...")
                res = exchange.market_close(coin)
                print(f"    Result: {res}")
            except Exception as e:
                print(f"    Failed to market_close {coin}: {e}")

        # Cancel any trigger orders that remained attached
        print("\nCancelling any lingering trigger orders...")
        for o in info.frontend_open_orders(wallet):
            try:
                exchange.cancel(o["coin"], o["oid"])
            except Exception:
                pass

    except Exception as e:
        print(f"Error querying/closing positions: {e}")

    # 3. Verify Final State
    time.sleep(2)
    print("\n[3/3] Verifying Final Account State...")
    try:
        final_orders = info.frontend_open_orders(wallet)
        final_state = info.user_state(wallet)
        remaining_positions = [
            p["position"] for p in final_state.get("assetPositions", [])
            if abs(float(p["position"].get("szi", 0.0))) > 1e-5
        ]

        print(f"Remaining Open Orders: {len(final_orders)}")
        print(f"Remaining Open Positions: {len(remaining_positions)}")
        for rp in remaining_positions:
            print(f"  * {rp.get('coin')}: Size = {rp.get('szi')}")

        # Update papertrade_state.json
        state_file = PIPELINE_ROOT / "data" / "papertrade_state.json"
        state_data = {
            "status": "PAUSED",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "account_value": float(final_state.get("marginSummary", {}).get("accountValue", 0.0)),
            "open_orders_count": len(final_orders),
            "open_positions_count": len(remaining_positions),
            "notes": "Paper trading daemon stopped and all positions closed per user request."
        }
        with open(state_file, "w") as f:
            json.dump(state_data, f, indent=2)

        print(f"\nState saved to {state_file}")
        print("Paper trading is now PAUSED.")

    except Exception as e:
        print(f"Error verifying final state: {e}")

    print("=" * 80)


if __name__ == "__main__":
    main()
