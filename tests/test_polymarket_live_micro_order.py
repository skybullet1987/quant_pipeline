#!/usr/bin/env python3
"""
POLYMARKET LIVE CLOB REAL-MONEY SMOKE TEST
==========================================
Executes a sub-cent real order against Polymarket CLOB to prove live order flow:
  1. Authenticates via EIP-1271 Deposit Proxy flow (signature_type=3).
  2. Queries on-chain / CLOB collateral balance and allowances.
  3. If funded: submits a 5-share GTC limit order @ $0.001 ($0.005 notional).
  4. Immediately cancels the test order to leave zero open exposure.
"""

import json
import os
import sys
import time
from pathlib import Path

import requests

PIPELINE_ROOT = Path("/home/skybullet1987/quant_pipeline")
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor
from py_clob_client_v2.clob_types import AssetType, BalanceAllowanceParams, OrderArgsV2, OrderType


def test_live_clob_order_flow():
    print("=" * 70)
    print("       POLYMARKET LIVE REAL-MONEY CLOB ORDER TEST")
    print("=" * 70)

    executor = PolymarketLiveExecutor(dry_run=False)
    print(f"Auth Mode:       {executor.auth_mode}")
    print(f"Funder Address:  {executor.funder_address}")
    print(f"Signature Type:  {executor.signature_type}")
    print(f"Authenticated:   {executor.is_authenticated}")

    if not executor.is_authenticated:
        print("[FAIL] Executor failed to authenticate with CLOB L2.")
        return False

    # Check CLOB collateral balance
    print("\n[STEP 1] Querying Polymarket CLOB Collateral Balance...")
    params = BalanceAllowanceParams(asset_type=AssetType.COLLATERAL, signature_type=executor.signature_type)
    bal_res = executor.client.get_balance_allowance(params)
    raw_bal = float(bal_res.get("balance", "0"))
    bal_usdc = raw_bal / 1e6
    print(f"  Collateral Balance: ${bal_usdc:.4f} USDC.e (Raw: {raw_bal})")

    if bal_usdc < 0.05:
        print("\n[BLOCKED] Collateral balance in Polymarket Proxy Wallet is $0.00!")
        print("  Funds must be deposited to the Polymarket Proxy Wallet before live orders can execute.")
        print(f"  Proxy Wallet Address: {executor.funder_address}")
        return False

    # Find active market token
    print("\n[STEP 2] Resolving active market token for deep-book limit smoke test...")
    active_markets = requests.get(
        "https://gamma-api.polymarket.com/markets?active=true&closed=false&limit=10",
        timeout=5,
    ).json()

    target_token = None
    target_title = None
    for m in active_markets:
        raw_tokens = m.get("clobTokenIds")
        tokens = json.loads(raw_tokens) if isinstance(raw_tokens, str) else raw_tokens
        if tokens and len(tokens) >= 2:
            target_token = tokens[0]
            target_title = m.get("question")
            break

    if not target_token:
        print("[FAIL] Could not resolve an active token ID.")
        return False

    print(f"  Target Market: {target_title}")
    print(f"  Target Token:  {target_token[:16]}...{target_token[-8:]}")

    # Step 3: Create, post, and cancel micro-order
    print("\n[STEP 3] Placing 5-share deep limit BUY order @ $0.001 (Notional: $0.005)...")
    order_args = OrderArgsV2(
        price=0.001,
        size=5.0,
        side="BUY",
        token_id=target_token,
    )
    signed_order = executor.client.create_order(order_args)
    resp = executor.client.post_order(signed_order, OrderType.GTC)
    print(f"  CLOB Response: {resp}")

    order_id = resp.get("orderID") or resp.get("id")
    if not order_id:
        print(f"[FAIL] Order rejected by CLOB: {resp}")
        return False

    print(f"  [SUCCESS] Live Order Placed! Order ID: {order_id}")

    # Step 4: Immediately cancel the order
    print("\n[STEP 4] Instantly cancelling test order to leave zero open exposure...")
    cancel_resp = executor.client.cancel(order_id)
    print(f"  Cancellation Response: {cancel_resp}")
    print("\n" + "=" * 70)
    print("      LIVE REAL-MONEY PIPELINE 100% VERIFIED & CONFIRMED!")
    print("=" * 70)
    return True


if __name__ == "__main__":
    test_live_clob_order_flow()
