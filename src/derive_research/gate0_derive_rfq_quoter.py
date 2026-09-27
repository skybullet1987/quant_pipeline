"""
Experiment D: Derive (Lyra v3) Multi-Leg RFQ Quoter & Indicative Pricing Probe
File: src/derive_research/gate0_derive_rfq_quoter.py

Evaluates:
  1. Authenticated session key connection to Derive /private/ endpoints
  2. Multi-leg RFQ submission (/private/send_rfq) for vertical debit spreads
  3. Market-maker quote polling (/private/poll_quotes or /private/get_rfqs)
  4. Response latency and price improvement: D_RFQ vs D_synthetic vs D_mid
  5. Fallback diagnostic reporting if session key is unconfigured
"""

import os
import sys
import time
import json
import asyncio
import aiohttp
from typing import Dict, Any, List, Optional
from eth_account import Account
from eth_account.messages import encode_defunct

DERIVE_BASE_URL = os.getenv("DERIVE_API_URL", "https://api.lyra.finance")

DERIVE_WALLET = os.getenv("DERIVE_WALLET")
DERIVE_PRIVATE_KEY = os.getenv("DERIVE_PRIVATE_KEY")

def generate_auth_headers(wallet_address: str, private_key: str) -> Dict[str, str]:
    """Generates standard Derive EIP-191 wallet signature headers."""
    timestamp = str(int(time.time() * 1000))
    message = encode_defunct(text=timestamp)
    signed = Account.sign_message(message, private_key=private_key)
    sig_hex = "0x" + signed.signature.hex() if not signed.signature.hex().startswith("0x") else signed.signature.hex()
    return {
        "X-LyraWallet": wallet_address,
        "X-LyraTimestamp": timestamp,
        "X-LyraSignature": sig_hex,
        "Content-Type": "application/json",
        "accept": "application/json",
        "User-Agent": "Mozilla/5.0"
    }

async def check_account_and_subaccounts(session: aiohttp.ClientSession, wallet: str, pkey: str):
    """Checks if the wallet has an active account and subaccounts on Derive."""
    headers = generate_auth_headers(wallet, pkey)
    body = {"wallet": wallet}
    
    async with session.post(f"{DERIVE_BASE_URL}/private/get_account", headers=headers, json=body) as resp:
        res = await resp.json()
        
    if "error" in res:
        err = res["error"]
        return None, err
        
    account_data = res.get("result", {})
    subaccounts = account_data.get("subaccount_ids", [])
    return subaccounts, None

async def probe_rfq_spread(session: aiohttp.ClientSession, wallet: str, pkey: str, subaccount_id: int, 
                           leg_long: str, leg_short: str, synth_ask: float):
    """Submits an atomic 2-leg vertical debit spread RFQ and measures market-maker responses."""
    rfq_payload = {
        "subaccount_id": subaccount_id,
        "legs": [
            {"instrument_name": leg_long, "direction": "buy", "amount": "1.0"},
            {"instrument_name": leg_short, "direction": "sell", "amount": "1.0"}
        ],
        "max_total_cost": str(round(synth_ask, 2)),
        "label": "canary_spread_audit"
    }
    
    headers = generate_auth_headers(wallet, pkey)
    t_start = time.perf_counter()
    
    print(f"\n[>] Dispatching RFQ for package: +1 {leg_long} / -1 {leg_short}")
    async with session.post(f"{DERIVE_BASE_URL}/private/send_rfq", headers=headers, json=rfq_payload) as resp:
        rfq_res = await resp.json()
        
    if "error" in rfq_res:
        print(f"[-] RFQ rejection: {rfq_res['error']}")
        return None

    rfq_id = rfq_res.get("result", {}).get("rfq_id")
    print(f"[+] RFQ submitted successfully! ID: {rfq_id}. Polling market-maker quotes...")

    quotes_received = []
    poll_payload = {"rfq_id": rfq_id, "subaccount_id": subaccount_id}
    
    for _ in range(6):  # Poll every 500ms
        await asyncio.sleep(0.5)
        headers = generate_auth_headers(wallet, pkey)
        async with session.post(f"{DERIVE_BASE_URL}/private/poll_quotes", headers=headers, json=poll_payload) as q_resp:
            q_data = await q_resp.json()
            quotes = q_data.get("result", {}).get("quotes", [])
            if quotes:
                quotes_received = quotes
                break

    latency = (time.perf_counter() - t_start) * 1000.0
    
    if not quotes_received:
        print(f"[-] Zero quotes received within 3.0 seconds (Latency: {latency:.1f}ms).")
        return {
            "package": f"{leg_long}/{leg_short}",
            "rfq_quoted": False,
            "best_rfq_debit": None,
            "latency_ms": latency
        }

    best_quote = min(quotes_received, key=lambda x: float(x.get("total_cost", 999999)))
    best_debit = float(best_quote.get("total_cost"))
    print(f"[+] Quote received! Best RFQ Debit: ${best_debit:.2f} (Latency: {latency:.1f}ms across {len(quotes_received)} quotes)")
    
    return {
        "package": f"{leg_long}/{leg_short}",
        "rfq_quoted": True,
        "best_rfq_debit": best_debit,
        "latency_ms": latency
    }

async def run_rfq_audit():
    print(f"===============================================================================")
    print(f"   EXPERIMENT D: DERIVE (LYRA v3) MULTI-LEG RFQ PROBE")
    print(f"   API Base URL: {DERIVE_BASE_URL}")
    print(f"===============================================================================\n")

    wallet = DERIVE_WALLET
    pkey = DERIVE_PRIVATE_KEY
    
    is_ephemeral = False
    if not pkey or not wallet:
        # Generate ephemeral key for probe testing
        temp_acc = Account.create()
        wallet = temp_acc.address
        pkey = temp_acc.key.hex()
        is_ephemeral = True
        print(f"[*] No DERIVE_PRIVATE_KEY found in .env. Using ephemeral probe wallet: {wallet}")
    else:
        print(f"[*] Loaded configured Derive wallet: {wallet}")

    async with aiohttp.ClientSession() as session:
        # 1. Test Authentication & Account Status
        subaccounts, error = await check_account_and_subaccounts(session, wallet, pkey)
        
        if error:
            code = error.get("code")
            msg = error.get("message")
            print(f"\n[-] Authentication Checked: Derive returned Code {code} ({msg})")
            
            if code == 14000:
                print("\n[DIAGNOSTIC] Account Not Registered on Derive App-Chain:")
                print("  • Derive is a non-custodial EVM roll-up (zero KYC required).")
                print("  • To access the private RFQ engine, a wallet must first connect once to Derive")
                print("    (https://derive.xyz or https://testnet.derive.xyz) or register a session key.")
                print("  • Settings -> Developers -> Session Keys -> Export/Generate Key.")
                print("  • Add to .env:")
                print("      DERIVE_WALLET=0x...")
                print("      DERIVE_PRIVATE_KEY=0x...")
                print("\n[*] Public Orderbook / Synthetic Crossing Benchmark remains 100% active and unblocked.")
                return
            else:
                print(f"[-] Authentication failed with unexpected error: {error}")
                return

        print(f"[+] Wallet authenticated successfully! Subaccounts: {subaccounts}")
        if not subaccounts:
            print("[-] No subaccount found for this wallet. Create a subaccount in the Derive UI.")
            return

        sub_id = subaccounts[0]
        print(f"[+] Using Subaccount ID: {sub_id}")

        # Candidate Packages
        test_packages = [
            ("ETH-20260928-2800-C", "ETH-20260928-2850-C", 2.60),
            ("ETH-20260928-2775-C", "ETH-20260928-2825-C", 3.70),
            ("BTC-20260928-86000-C", "BTC-20260928-88000-C", 143.00)
        ]

        results = []
        for leg_long, leg_short, synth_ask in test_packages:
            res = await probe_rfq_spread(session, wallet, pkey, sub_id, leg_long, leg_short, synth_ask)
            if res:
                results.append(res)
            await asyncio.sleep(1.0)

        print("\n=== DERIVE RFQ QUOTING PERFORMANCE SUMMARY ===")
        print(f"{'Package':<42} | {'Quoted':<8} | {'Best RFQ Debit':<16} | {'Response Time':<12}")
        print("-" * 84)
        for r in results:
            debit_str = f"${r['best_rfq_debit']:.2f}" if r["best_rfq_debit"] else "NO_QUOTES"
            print(f"{r['package']:<42} | {str(r['rfq_quoted']):<8} | {debit_str:<16} | {r['latency_ms']:.1f}ms")

if __name__ == "__main__":
    asyncio.run(run_rfq_audit())
