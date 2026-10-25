#!/usr/bin/env python3
"""
POLYMARKET ACCOUNT ONBOARDING & VERIFICATION UTILITY
===================================================
Automates on-chain token allowances and L2 API credential derivation
for Rabby / EOA wallets on Polygon PoS (Chain ID 137).
"""

import json
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

PIPELINE_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PIPELINE_ROOT / ".env")

try:
    from web3 import Web3
    from web3.middleware import ExtraDataToPOAMiddleware
except ImportError as e:
    print(f"[ERROR] Required library missing: {e}")
    sys.exit(1)

try:
    from py_clob_client_v2.client import ClobClient  # CLOB V2 (primary)
except ImportError:
    try:
        from py_clob_client.client import ClobClient  # legacy fallback
    except ImportError as e:
        print(f"[ERROR] No CLOB client library installed (py_clob_client_v2 / py_clob_client): {e}")
        sys.exit(1)

# Contract Addresses on Polygon (Chain ID 137)
POLYGON_RPC = "https://polygon-bor-rpc.publicnode.com"
USDC_E_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"  # Legacy bridged USDC.e
PUSD_ADDRESS = "0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB"      # CLOB V2 primary collateral (pUSD)
CTF_EXCHANGE = "0xE111180000d2663C0091e4f400237545B87B996B"     # CTF Exchange V2
NEGRISK_EXCHANGE = "0xe2222d279d744050d28e00520010520000310F59"  # NegRisk Exchange V2
NEGRISK_ADAPTER = "0xe3333700cA9d93003F00f0F71f8515005F6c00Aa"   # Exchange V3
CTF_ADDRESS = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"     # Conditional Tokens Framework (ERC1155)

ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}, {"name": "_spender", "type": "address"}],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
]

ERC1155_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "account", "type": "address"}, {"name": "operator", "type": "address"}],
        "name": "isApprovedForAll",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [{"name": "operator", "type": "address"}, {"name": "approved", "type": "bool"}],
        "name": "setApprovalForAll",
        "outputs": [],
        "type": "function",
    },
]


def main():
    print("=" * 75)
    print("      POLYMARKET LIVE ACCOUNT INITIALIZATION & ONBOARDING")
    print("=" * 75)

    pk = os.getenv("POLYGON_PRIVATE_KEY", "").strip()
    funder = os.getenv("POLYGON_FUNDER_ADDRESS", "").strip()

    if not pk:
        print("\n[ERROR] POLYGON_PRIVATE_KEY is missing from .env!")
        print("Please export your private key from Rabby and add it to:")
        print(f"  {PIPELINE_ROOT / '.env'}")
        print("\nFormat:")
        print("  POLYGON_PRIVATE_KEY=0xYourPrivateKeyHere")
        print("  POLYGON_FUNDER_ADDRESS=0x9703b71686219d34869e8fb89a93263f9e0d50a5")
        sys.exit(1)

    # Initialize Web3
    w3 = Web3(Web3.HTTPProvider(POLYGON_RPC))
    try:
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    except Exception:
        pass

    account = w3.eth.account.from_key(pk)
    wallet_addr = account.address
    sig_type = int(os.getenv("POLYGON_SIGNATURE_TYPE", "0") or "0")
    effective_funder = Web3.to_checksum_address(funder) if (sig_type in (1, 2, 3) and funder) else wallet_addr
    print(f"\n[1/5] Signer EOA: {wallet_addr} | Effective Funder (sig_type={sig_type}): {effective_funder}")

    # Check on-chain balances on effective_funder
    print("\n[2/5] Checking On-Chain Balances on Polygon...")
    pol_wei = w3.eth.get_balance(wallet_addr)
    pol_bal = pol_wei / 1e18
    print(f"      Signer POL Gas:   {pol_bal:.4f} POL")

    usdc_contract = w3.eth.contract(address=Web3.to_checksum_address(PUSD_ADDRESS), abi=ERC20_ABI)
    usdc_raw = usdc_contract.functions.balanceOf(effective_funder).call()
    usdc_bal = usdc_raw / 1e6
    print(f"      Funder pUSD Bal:  ${usdc_bal:,.2f} pUSD")

    if usdc_bal < 10.0:
        print("      [WARN] Low pUSD balance on funder wallet.")

    # Check and set on-chain allowances ONLY for direct EOA mode (sig_type == 0)
    print("\n[3/5] Verifying On-Chain Exchange Approvals...")
    spenders = [
        ("CTF Exchange V2", CTF_EXCHANGE),
        ("NegRisk Exchange V2", NEGRISK_EXCHANGE),
        ("Exchange V3", NEGRISK_ADAPTER),
    ]

    max_uint256 = 2**256 - 1

    if sig_type == 0:
        for label, spender_addr in spenders:
            current_allowance = usdc_contract.functions.allowance(wallet_addr, Web3.to_checksum_address(spender_addr)).call()
            allowance_usd = current_allowance / 1e6
            if allowance_usd < 300.0:
                print(f"      Approving {label} ({spender_addr[:10]}...)...")
                time.sleep(2)
                nonce = w3.eth.get_transaction_count(wallet_addr, "pending")
                gas_price = int(w3.eth.gas_price * 1.5)
                tx = usdc_contract.functions.approve(
                    Web3.to_checksum_address(spender_addr),
                    max_uint256
                ).build_transaction({
                    "from": wallet_addr,
                    "nonce": nonce,
                    "gas": 80000,
                    "gasPrice": gas_price,
                    "chainId": 137,
                })
                signed_tx = w3.eth.account.sign_transaction(tx, private_key=pk)
                tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                print(f"      ✓ {label} Approval tx broadcast: {tx_hash.hex()[:18]}... Waiting for receipt...")
                w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
                print(f"      ✓ {label} Approved successfully!")
            else:
                print(f"      ✓ {label}: Already Approved (${allowance_usd:,.0f})")

        print("\n[3b/5] Verifying Conditional Tokens (CTF) Operator Approvals...")
        ctf_contract = w3.eth.contract(address=Web3.to_checksum_address(CTF_ADDRESS), abi=ERC1155_ABI)
        for label, spender_addr in spenders:
            is_approved = ctf_contract.functions.isApprovedForAll(wallet_addr, Web3.to_checksum_address(spender_addr)).call()
            if not is_approved:
                print(f"      Approving CTF for {label} ({spender_addr[:10]}...)...")
                time.sleep(3)
                nonce = w3.eth.get_transaction_count(wallet_addr, "pending")
                gas_price = int(w3.eth.gas_price * 1.5)
                tx = ctf_contract.functions.setApprovalForAll(
                    Web3.to_checksum_address(spender_addr),
                    True
                ).build_transaction({
                    "from": wallet_addr,
                    "nonce": nonce,
                    "gas": 80000,
                    "gasPrice": gas_price,
                    "chainId": 137,
                })
                signed_tx = w3.eth.account.sign_transaction(tx, private_key=pk)
                tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                print(f"      ✓ CTF {label} Approval tx: {tx_hash.hex()[:18]}... Waiting for receipt...")
                w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
                print(f"      ✓ CTF {label} Approved successfully!")
            else:
                print(f"      ✓ CTF {label}: Already Approved (True)")
    else:
        print(f"      [Proxy/Deposit Wallet Mode sig_type={sig_type}] Skipping direct EOA on-chain approve() broadcasts (managed via CLOB L2 relayer).")

    # Connect to Polymarket CLOB
    host = "https://clob.polymarket.com"
    print(f"\n[4/5] Connecting to Polymarket CLOB at {host}...")
    client = ClobClient(
        host=host,
        key=pk,
        chain_id=137,
        signature_type=sig_type,
        funder=effective_funder
    )
    server_time = client.get_server_time()
    print(f"      ✓ Connection established! Server Time: {server_time}")

    # Derive L2 API Credentials
    print("\n[5/5] Deriving & Registering Polymarket L2 API Credentials...")
    try:
        creds = client.create_or_derive_api_creds()
        client.set_api_creds(creds)
        print("      ✓ Successfully derived L2 API Key!")
        print(f"      API Key: {creds.api_key[:16]}...")

        # Cache credentials to disk
        creds_dir = PIPELINE_ROOT / "data/polymarket"
        creds_dir.mkdir(parents=True, exist_ok=True)
        creds_path = creds_dir / "clob_creds.json"
        with open(creds_path, "w") as f:
            json.dump({
                "api_key": creds.api_key,
                "api_secret": creds.api_secret,
                "api_passphrase": creds.api_passphrase,
                "signer_address": wallet_addr,
                "funder_address": effective_funder,
                "signature_type": sig_type,
                "derived_at_utc": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
            }, f, indent=2)
        os.chmod(creds_path, 0o600)
        print(f"      ✓ Credentials cached to: data/polymarket/clob_creds.json")

        # Notify Polymarket relayer of balance & allowance
        print("      Notifying Polymarket CLOB relayer...")
        try:
            relayer_res = client.update_balance_allowance()
            print(f"      ✓ Relayer response: {relayer_res}")
        except Exception as e:
            print(f"      (Relayer note: {e})")

    except Exception as e:
        print(f"[ERROR] Failed to derive L2 API credentials: {e}")
        sys.exit(1)

    print("\n" + "=" * 75)
    print("                 ACCOUNT ONBOARDING 100% COMPLETE")
    print("=" * 75)
    print(f"Signer EOA:         {wallet_addr}")
    print(f"Effective Funder:   {effective_funder} (sig_type={sig_type})")
    print(f"pUSD Available:     ${usdc_bal:,.2f}")
    print(f"L2 Credentials:     ACTIVE & CACHED (0600)")
    print("=" * 75)
    print("\nLaunch the live harvester daemon via systemd:")
    print("  systemctl --user start polymarket-live-harvester.service")
    print("=" * 75)


if __name__ == "__main__":
    main()
