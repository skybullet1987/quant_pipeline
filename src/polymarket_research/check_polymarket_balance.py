#!/usr/bin/env python3
"""
POLYMARKET LIVE BALANCE & PERFORMANCE INSPECTOR
==============================================
Quick CLI tool to monitor live wallet balance, open outcome tokens, and realized PnL.
"""

import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import requests

PIPELINE_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PIPELINE_ROOT / ".env")

WALLET_ADDR = os.getenv("POLYGON_FUNDER_ADDRESS", "").strip()
if not WALLET_ADDR:
    print("[ERROR] POLYGON_FUNDER_ADDRESS is not set in .env")
    sys.exit(1)

USDC_E = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
PUSD = "0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB"


def check_balance():
    print("=" * 65)
    print("        POLYMARKET LIVE BALANCE & STATUS INSPECTOR")
    print("=" * 65)
    print(f"Funder Wallet:   {WALLET_ADDR}")

    # 1. Authoritative CLOB L2 Collateral Balance
    clob_bal = None
    try:
        from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor
        ex = PolymarketLiveExecutor(dry_run=False)
        if ex.is_authenticated:
            clob_bal = ex.get_collateral_balance()
            print(f"CLOB L2 Balance: ${clob_bal:,.2f} USD")
    except Exception as e:
        pass

    # 2. On-chain balances with multi-RPC fallback
    rpcs = [
        "https://polygon-bor-rpc.publicnode.com",
        "https://polygon-rpc.com",
        "https://polygon.gateway.tenderly.co",
        "https://1rpc.io/matic",
    ]
    pol_bal = 0.0
    pusd_bal = 0.0
    usdc_bal = 0.0

    for rpc in rpcs:
        try:
            # Native POL
            r_pol = requests.post(rpc, json={
                "jsonrpc": "2.0", "method": "eth_getBalance", "params": [WALLET_ADDR, "latest"], "id": 1
            }, timeout=2.5).json()
            if "result" in r_pol:
                pol_bal = int(r_pol["result"], 16) / 1e18

            call_data = "0x70a08231" + WALLET_ADDR[2:].lower().rjust(64, "0")
            # V2 pUSD primary collateral
            r_pusd = requests.post(rpc, json={
                "jsonrpc": "2.0", "method": "eth_call", "params": [{"to": PUSD, "data": call_data}, "latest"], "id": 2
            }, timeout=2.5).json()
            if "result" in r_pusd:
                pusd_bal = int(r_pusd["result"], 16) / 1e6

            # Legacy USDC.e
            r_usdc = requests.post(rpc, json={
                "jsonrpc": "2.0", "method": "eth_call", "params": [{"to": USDC_E, "data": call_data}, "latest"], "id": 3
            }, timeout=2.5).json()
            if "result" in r_usdc:
                usdc_bal = int(r_usdc["result"], 16) / 1e6
            if pusd_bal > 0 or usdc_bal > 0 or pol_bal > 0:
                break
        except Exception:
            continue

    print(f"POL Gas Balance: {pol_bal:.4f} POL")
    print(f"pUSD On-chain:   ${pusd_bal:,.2f} pUSD (V2 Primary Collateral)")
    print(f"USDC.e On-chain: ${usdc_bal:,.2f} USDC.e (Legacy Bridge)")

    # 2. Check live execution ledger if active
    ledger_path = PIPELINE_ROOT / "data/polymarket/live_orders.jsonl"
    if ledger_path.exists():
        orders = []
        with open(ledger_path, "r") as f:
            for line in f:
                if line.strip():
                    orders.append(json.loads(line))
        print(f"\nLive Orders Dispatched: {len(orders)}")
        if orders:
            print("Recent Orders:")
            for o in orders[-5:]:
                print(f"  • [{o.get('timestamp_utc')[:19]}] {o.get('trade_id')} | {o.get('target_token')} | ${o.get('notional_usd')} @ ${o.get('price')} (Mode: {o.get('mode')})")
    else:
        print("\nLive Orders Ledger: No live orders placed yet.")

    print("=" * 65)


if __name__ == "__main__":
    check_balance()
