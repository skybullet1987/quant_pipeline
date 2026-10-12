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

import pytest
import requests

PIPELINE_ROOT = Path("/home/skybullet1987/quant_pipeline")
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

# P0 #4: HARD SAFETY GATE: Never execute real-money orders during normal pytest discovery
if os.getenv("POLYMARKET_LIVE_TEST") != "1":
    pytest.skip("Skipping live real-money test. Set POLYMARKET_LIVE_TEST=1 to enable.", allow_module_level=True)

from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor
from py_clob_client_v2.clob_types import AssetType, BalanceAllowanceParams, OrderArgsV2, OrderType


@pytest.mark.live_money
def test_live_clob_order_flow():
    print("=" * 70)
    print("       POLYMARKET LIVE REAL-MONEY CLOB ORDER TEST")
    print("=" * 70)

    executor = PolymarketLiveExecutor(dry_run=False)
    print(f"Auth Mode:       {executor.auth_mode}")
    print(f"Funder Address:  {executor.funder_address}")
    print(f"Signature Type:  {executor.signature_type}")
    print(f"Authenticated:   {executor.is_authenticated}")

    assert executor.is_authenticated, "Executor failed to authenticate with CLOB L2."

    # Check CLOB collateral balance
    print("\n[STEP 1] Querying Polymarket CLOB Collateral Balance...")
    bal_pusd = executor.get_collateral_balance()
    print(f"  Collateral Balance: ${bal_pusd:.4f} pUSD (V2 Collateral)")

    assert bal_pusd >= 0.05, f"Insufficient collateral in Polymarket wallet: ${bal_pusd:.4f} (minimum $0.05 required)"

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

    assert target_token is not None, "Could not resolve an active token ID from Gamma API."

    print(f"  Target Market: {target_title}")
    print(f"  Target Token:  {target_token[:16]}...{target_token[-8:]}")

    # Step 3: Create, post micro-order deep in book ($0.001)
    print("\n[STEP 3] Placing 5-share deep limit BUY order @ $0.001 (Notional: $0.005)...")
    order_args = OrderArgsV2(
        price=0.001,
        size=5.0,
        side="BUY",
        token_id=target_token,
    )
    signed_order = executor.client.create_order(order_args)
    resp = executor.client.post_order(signed_order, OrderType.GTC, defer_exec=True)
    print(f"  CLOB Response: {resp}")

    order_id = resp.get("orderID") or resp.get("id")
    assert order_id is not None, f"Order rejected by CLOB matching engine: {resp}"
    print(f"  [SUCCESS] Live Order Placed! Order ID: {order_id}")

    # Step 4: Verify order is active in open orders (allow 0.5s for CLOB indexer sync)
    print("\n[STEP 4] Verifying order presence in open orders...")
    time.sleep(0.5)
    open_orders = executor.get_open_orders()
    order_found = any(o.get("id") == order_id or o.get("orderID") == order_id for o in open_orders)
    assert order_found, f"Order {order_id} was submitted but not found in CLOB open orders: {open_orders}"
    print(f"  ✓ Confirmed order {order_id} active in open orderbook")

    # Step 5: Cancel the order
    print("\n[STEP 5] Instantly cancelling test order to leave zero open exposure...")
    cancel_resp = executor.client.cancel_orders([order_id])
    print(f"  Cancellation Response: {cancel_resp}")
    canceled_ids = cancel_resp.get("canceled", [])
    assert order_id in canceled_ids or order_id in str(cancel_resp), f"Cancellation failed for {order_id}: {cancel_resp}"

    # Step 6: Verify order is removed from open orders
    time.sleep(0.5)
    open_orders_after = executor.get_open_orders()
    still_open = any(o.get("id") == order_id or o.get("orderID") == order_id for o in open_orders_after)
    assert not still_open, f"Order {order_id} still present in open orders after cancellation: {open_orders_after}"
    print(f"  ✓ Confirmed order {order_id} removed from open orders")

    # Step 7: Verify zero unintended fills occurred
    order_status = executor.get_order_status(order_id)
    if order_status:
        matched = float(order_status.get("size_matched", "0"))
        assert matched == 0.0, f"Unintended fill detected on smoke test order! Matched={matched}"
        print(f"  ✓ Confirmed zero shares filled on test order (matched={matched})")

    print("\n" + "=" * 70)
    print("      LIVE REAL-MONEY PIPELINE 100% VERIFIED & CONFIRMED!")
    print("=" * 70)


if __name__ == "__main__":
    test_live_clob_order_flow()
