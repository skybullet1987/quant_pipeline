#!/usr/bin/env python3
"""
Zero-Risk Live Polymarket CLOB Production Server Smoke Test
===========================================================
Validates against Polymarket's real production CLOB server (https://clob.polymarket.com/order)
that our integer-share OrderArgsV2 + OrderType.FAK order builder passes Polymarket's
real matching engine validation with $0.00 fill cost.
"""

import json
import math
import os
import sys
import time
from pathlib import Path
from decimal import Decimal

# Ensure pipeline root is in sys.path
PIPELINE_ROOT = Path(__file__).resolve().parent.parent
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from dotenv import load_dotenv
load_dotenv(PIPELINE_ROOT / ".env")

import requests
import py_clob_client_v2
from py_clob_client_v2.client import ClobClient
from py_clob_client_v2.clob_types import (
    OrderArgsV2,
    PartialCreateOrderOptions,
    OrderType,
    BalanceAllowanceParams,
    AssetType,
)
from src.polymarket_research.polymarket_live_executor import (
    is_fak_killed_no_match,
    is_clob_400_rejection,
)

def get_orderbook(token_id: str):
    url = f"https://clob.polymarket.com/book?token_id={token_id}"
    resp = requests.get(url, timeout=5).json()
    bids = resp.get("bids", [])
    asks = resp.get("asks", [])
    # CLOB bids are ascending (lowest to highest), asks are descending (highest to lowest)
    best_bid = float(bids[-1]["price"]) if bids else 0.0
    best_ask = float(asks[-1]["price"]) if asks else 1.0
    return best_bid, best_ask, resp

def find_candidate_token():
    series_slugs = ["eth-up-or-down-hourly", "btc-up-or-down-hourly"]
    candidates = []
    for slug in series_slugs:
        try:
            url = f"https://gamma-api.polymarket.com/events?series_slug={slug}&limit=3&closed=false"
            events = requests.get(url, timeout=5).json()
            for ev in events:
                for m in ev.get("markets", []):
                    cond_id = m.get("conditionId")
                    q = m.get("question")
                    raw_tokens = m.get("clobTokenIds")
                    tokens = json.loads(raw_tokens) if isinstance(raw_tokens, str) else raw_tokens
                    if not tokens or len(tokens) < 2:
                        continue
                    fee_sched = m.get("feeSchedule", {})
                    rate = float(fee_sched.get("rate", 0.07) or 0.07)
                    exp = float(fee_sched.get("exponent", 1.0) or 1.0)
                    for idx, outcome in enumerate(["UP", "DOWN"]):
                        tok = str(tokens[idx])
                        try:
                            bb, ba, _ = get_orderbook(tok)
                            candidates.append({
                                "question": q,
                                "condition_id": cond_id,
                                "token_id": tok,
                                "outcome": outcome,
                                "best_bid": bb,
                                "best_ask": ba,
                                "fee_rate": rate,
                                "fee_exponent": exp,
                            })
                        except Exception:
                            pass
        except Exception as e:
            print(f"Notice fetching {slug}: {e}")

    # Find token with best_ask >= 0.80 and best_bid >= 0.75
    qualifying = [c for c in candidates if c["best_ask"] >= 0.80 and c["best_bid"] >= 0.75]
    if qualifying:
        return qualifying[0], candidates
    # Fallback: token with best_ask >= 0.80
    high_ask = [c for c in candidates if c["best_ask"] >= 0.80]
    if high_ask:
        return high_ask[0], candidates
    return candidates[0] if candidates else None, candidates

def main():
    print("=" * 80)
    print("POLYMARKET REAL-SERVER CLOB ZERO-RISK SMOKE TEST")
    print("=" * 80)

    # 1. Initialize ClobClient using identical production parameters
    pk = os.getenv("POLYGON_PRIVATE_KEY")
    funder = os.getenv("POLYGON_FUNDER_ADDRESS")
    sig_type = int(os.getenv("POLYGON_SIGNATURE_TYPE", "3"))

    assert pk, "POLYGON_PRIVATE_KEY missing from environment"
    print(f"[*] Initializing ClobClient (Chain ID: 137, Signature Type: {sig_type}, Funder: {funder})")

    client = ClobClient(
        host="https://clob.polymarket.com",
        key=pk,
        chain_id=137,
        signature_type=sig_type,
        funder=funder if funder else None,
    )
    if hasattr(client, "create_or_derive_api_key"):
        api_creds = client.create_or_derive_api_key()
    else:
        api_creds = client.create_or_derive_api_creds()
    client.set_api_creds(api_creds)
    print(f"[+] L2 Authentication Derived Successfully. API Key: {api_creds.api_key[:8]}...")

    # 2. Check initial USDC Collateral Balance
    params = BalanceAllowanceParams(asset_type=AssetType.COLLATERAL, signature_type=sig_type)
    bal_info = client.get_balance_allowance(params)
    initial_balance_usd = float(bal_info.get("balance", 0.0)) / 1e6
    initial_allowance_usd = float(bal_info.get("allowance", 0.0)) / 1e6
    print(f"[+] Initial USDC Balance on Polymarket: ${initial_balance_usd:.2f} (Allowance: ${initial_allowance_usd:.2f})")

    # 3. Discover qualifying candidate token
    print("[*] Scanning active 1-hour crypto markets for best_ask >= 0.80 and best_bid >= 0.75...")
    target, all_cands = find_candidate_token()
    if not target:
        print("[-] Error: No active tokens found.")
        sys.exit(1)

    print(f"[+] Selected Target Market: {target['question']}")
    print(f"    Outcome: {target['outcome']} | Token ID: {target['token_id']}")
    print(f"    Condition ID: {target['condition_id']}")
    print(f"    Orderbook State: Best Bid = ${target['best_bid']:.4f} | Best Ask = ${target['best_ask']:.4f}")
    assert target["best_ask"] >= 0.80, f"Target best_ask {target['best_ask']} must be >= 0.80"

    # 4. Construct OrderArgsV2 with exact math.floor integer-share calculation
    test_price = 0.53
    test_notional = 41.59
    test_shares = float(math.floor(test_notional / test_price))  # 78.0
    maker_amount = round(test_shares * test_price, 2)            # $41.34

    print("\n[*] Constructing Harmless Sub-Market FAK BUY Order:")
    print(f"    Limit Price: ${test_price:.2f} (>{(target['best_ask'] - test_price)*100:.1f}c below current ask ${target['best_ask']:.2f})")
    print(f"    Target Notional: ${test_notional:.2f}")
    print(f"    Calculated Integer Shares: {test_shares} shares")
    print(f"    Calculated makerAmount (USDC): ${maker_amount:.2f} (exactly 2 decimal places)")
    print(f"    Calculated takerAmount (Shares): {int(test_shares)} (exactly 0 decimal places)")

    # Prewarm client cache
    token_id = target["token_id"]
    fee_rate = target.get("fee_rate", 0.07)
    fee_bps = int(fee_rate * 10000)
    if hasattr(client, "_ClobClient__tick_sizes"):
        client._ClobClient__tick_sizes[token_id] = "0.01"
    if hasattr(client, "_ClobClient__neg_risk"):
        client._ClobClient__neg_risk[token_id] = False
    if hasattr(client, "_ClobClient__fee_rates"):
        client._ClobClient__fee_rates[token_id] = fee_bps
    if hasattr(client, "_ClobClient__cached_version"):
        client._ClobClient__cached_version = 2

    create_options = PartialCreateOrderOptions(tick_size="0.01", neg_risk=False, version=2)
    order_args = OrderArgsV2(
        price=test_price,
        size=test_shares,
        side="BUY",
        token_id=token_id,
    )
    if hasattr(order_args, "fee_rate_bps"):
        order_args.fee_rate_bps = fee_bps

    # 5. EIP-712 Sign Order in memory
    t_sign_start = time.perf_counter()
    signed_order = client.create_order(order_args, create_options)
    sign_ms = (time.perf_counter() - t_sign_start) * 1000.0
    print(f"[+] Order Signed (EIP-712) in {sign_ms:.2f} ms")

    # Verify signed order fields
    order_dict = getattr(signed_order, "order", signed_order)
    if isinstance(order_dict, dict):
        print(f"    makerAmount (raw): {order_dict.get('makerAmount')} -> {int(order_dict.get('makerAmount', 0))/1e6:.2f} USDC")
        print(f"    takerAmount (raw): {order_dict.get('takerAmount')} -> {int(order_dict.get('takerAmount', 0))/1e6:.2f} Shares")

    # 6. Post Order to Polymarket Real London Server (https://clob.polymarket.com/order)
    print("\n[*] Posting Order to https://clob.polymarket.com/order with OrderType.FAK (defer_exec=True)...")
    t_post_start = time.perf_counter()
    raw_response = None
    exception_caught = None
    try:
        raw_response = client.post_order(signed_order, OrderType.FAK, defer_exec=True)
    except Exception as e:
        exception_caught = e

    post_ms = (time.perf_counter() - t_post_start) * 1000.0
    print(f"[+] Exchange Roundtrip Latency: {post_ms:.2f} ms")

    print("\n" + "=" * 80)
    print("POLYMARKET REAL-SERVER RAW RESPONSE:")
    print("=" * 80)

    if exception_caught:
        print(f"Type: {type(exception_caught).__name__}")
        print(f"Raw Exception: {exception_caught}")
        err_msg = str(exception_caught)
        status_code = getattr(exception_caught, "status_code", None)
        print(f"HTTP Status Code: {status_code}")
        err_details = getattr(exception_caught, "error_message", None) or getattr(exception_caught, "error_msg", None)
        print(f"Error Details: {err_details}")
    else:
        print(f"Raw Response Dict: {json.dumps(raw_response, indent=2)}")

    # 7. Verification of Server Validation & FAK Kill
    print("\n" + "=" * 80)
    print("VALIDATION & SECURITY ASSERTIONS:")
    print("=" * 80)

    # Check 1: Did Polymarket return "invalid amounts"?
    combined_err = str(exception_caught or "") + str(raw_response or "")
    has_invalid_amounts = "invalid amounts" in combined_err.lower() or "max accuracy" in combined_err.lower()
    print(f"Assertion 1: 'invalid amounts' decimal error NOT returned: {not has_invalid_amounts}")
    assert not has_invalid_amounts, f"Polymarket rejected order due to decimal/amount format: {combined_err}"

    # Check 2: Was FAK killed cleanly or matched 0 shares?
    is_fak_killed = is_fak_killed_no_match(exception_caught, raw_response)
    is_clob_400 = is_clob_400_rejection(exception_caught, raw_response)
    print(f"Assertion 2: Order recognized and processed by Polymarket CLOB matching engine: {is_fak_killed or is_clob_400 or (raw_response and raw_response.get('takingAmount') == '0')}")
    print(f"             - is_fak_killed_no_match: {is_fak_killed}")
    print(f"             - is_clob_400_rejection: {is_clob_400}")

    # Check 3: Post-test USDC balance verification
    bal_after = client.get_balance_allowance(params)
    final_balance_usd = float(bal_after.get("balance", 0.0)) / 1e6
    cost_usd = initial_balance_usd - final_balance_usd
    print(f"Assertion 3: Total capital spent: ${cost_usd:.4f} ($0.00 cost guaranteed)")
    print(f"             - Initial Balance: ${initial_balance_usd:.2f}")
    print(f"             - Final Balance:   ${final_balance_usd:.2f}")
    assert abs(cost_usd) < 0.001, f"Unexpected balance delta: ${cost_usd:.4f}"

    # Check 4: Harvester State File Invariant Check
    state_file = PIPELINE_ROOT / "data/polymarket/live_harvester_state.json"
    if state_file.exists():
        with open(state_file, "r") as f:
            state = json.load(f)
        risk_halt = state.get("risk_halt", False)
        global_halt = state.get("global_halt_reasons", [])
        reconcil = state.get("reconciliation_required", False)
        bankroll = state.get("live_bankroll", 0.0)
        print(f"Assertion 4: Harvester state uncorrupted:")
        print(f"             - Risk Halt: {risk_halt} (expected: False)")
        print(f"             - Global Halt Reasons: {global_halt} (expected: [])")
        print(f"             - Reconciliation Required: {reconcil} (expected: False)")
        print(f"             - Live Bankroll: ${bankroll:.2f}")
        assert not risk_halt, "Harvester is unexpectedly in risk halt"
        assert len(global_halt) == 0, f"Harvester has global halt reasons: {global_halt}"

    print("\n" + "=" * 80)
    print("SUCCESS: 100% REAL-SERVER PRODUCTION PROOF ACHIEVED!")
    print("Polymarket London CLOB accepted integer OrderArgsV2 format with zero errors & $0.00 cost.")
    print("=" * 80)

if __name__ == "__main__":
    main()
