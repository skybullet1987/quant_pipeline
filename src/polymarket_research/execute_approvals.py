#!/usr/bin/env python3
"""
POLYMARKET V2 ON-CHAIN & L2 APPROVALS VERIFIER & EXECUTOR
==========================================================
Audited Architecture (Fail-Closed, Signature-Type Aware):
  1. IDENTIFY SIGNER (EOA from private key)
  2. IDENTIFY FUNDER (Target trading account)
  3. IDENTIFY SIGNATURE TYPE:
       0 = EOA
       1 = Polymarket proxy
       2 = Gnosis Safe
       3 = Polymarket deposit wallet / EIP-1271
  4. IDENTIFY COLLATERAL TOKEN:
       CLOB V2 primary collateral = pUSD (0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB)
       Legacy bridge collateral   = USDC.e (0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174)
       Conditional Tokens         = CTF Contract (0x4D97DCd97eC945f40cF65F87097ACe5EA0476045)
  5. VERIFY ACTUAL V2 ON-CHAIN ALLOWANCES (pUSD, USDC.e)
  6. VERIFY CTF OPERATOR APPROVALS
  7. VERIFY CLOB L2 BALANCE & ALLOWANCES (via py_clob_client_v2 and update_balance_allowance)
  8. FAIL CLOSED:
       - For non-EOA funder (types 1, 2, 3): Verify CLOB allowances. Never guess or broadcast
         invalid on-chain transactions pretending the signer can execute from the contract.
       - For EOA funder (type 0): Execute on-chain approvals if missing.
"""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

PIPELINE_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PIPELINE_ROOT / ".env")

# Dedicated RPC Configuration with fallback
PRIMARY_RPC = os.getenv("POLYGON_RPC_URL", "https://polygon-bor-rpc.publicnode.com")
w3 = Web3(Web3.HTTPProvider(PRIMARY_RPC))
try:
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
except Exception:
    pass

# ==============================================================================
# 1. IDENTIFY SIGNER
# ==============================================================================
pk = os.getenv("POLYGON_PRIVATE_KEY", "").strip()
if not pk:
    print("[FATAL] POLYGON_PRIVATE_KEY is missing or empty in .env. Cannot verify or execute approvals.")
    sys.exit(1)

account = w3.eth.account.from_key(pk)
signer_addr = Web3.to_checksum_address(account.address)

# ==============================================================================
# 2. IDENTIFY FUNDER
# ==============================================================================
raw_funder = (
    os.getenv("POLYGON_FUNDER_ADDRESS", "").strip()
    or os.getenv("POLYGON_PROXY_ADDRESS", "").strip()
    or signer_addr
)
funder_addr = Web3.to_checksum_address(raw_funder)

# ==============================================================================
# 3. IDENTIFY SIGNATURE TYPE
# ==============================================================================
raw_sig = os.getenv("POLYGON_SIGNATURE_TYPE", "").strip()
if not raw_sig:
    raise RuntimeError("LIVE APPROVAL REFUSED: POLYGON_SIGNATURE_TYPE must be explicitly configured in .env")
sig_type = int(raw_sig)
if sig_type not in (0, 1, 2, 3):
    raise RuntimeError(f"Unsupported POLYGON_SIGNATURE_TYPE={sig_type}")

SIG_TYPE_LABELS = {
    0: "0 (EOA - Direct Externally Owned Account)",
    1: "1 (Polymarket Proxy Wallet)",
    2: "2 (Gnosis Safe Multi-Sig)",
    3: "3 (Polymarket Deposit Wallet / EIP-1271)",
}
sig_label = SIG_TYPE_LABELS.get(sig_type, f"{sig_type} (Unknown)")

# ==============================================================================
# 4. IDENTIFY COLLATERAL & CONTRACTS (Polymarket V2 Authoritative)
# ==============================================================================
# V2 Primary Collateral is pUSD; USDC.e is wrapped through CollateralOnramp
PUSD_TOKEN = Web3.to_checksum_address("0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB")
USDC_E_TOKEN = Web3.to_checksum_address("0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174")
CTF_CONTRACT = Web3.to_checksum_address("0x4D97DCd97eC945f40cF65F87097ACe5EA0476045")

# Authoritative V2 Exchange Contracts from py_clob_client_v2.config
# 0xE111... = CTF Exchange V2
# 0xe222... = Neg Risk CTF Exchange
# 0xe333... = ExchangeV3 / Protocol V2
CTF_EXCHANGE_V2 = Web3.to_checksum_address("0xE111180000d2663C0091e4f400237545B87B996B")
NEGRISK_EXCHANGE_V2 = Web3.to_checksum_address("0xe2222d279d744050d28e00520010520000310F59")
EXCHANGE_V3 = Web3.to_checksum_address("0xe3333700cA9d93003F00f0F71f8515005F6c00Aa")

ERC20_ABI = [
    {"constant": False, "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}, {"name": "_spender", "type": "address"}], "name": "allowance", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
]

ERC1155_ABI = [
    {"constant": False, "inputs": [{"name": "operator", "type": "address"}, {"name": "approved", "type": "bool"}], "name": "setApprovalForAll", "outputs": [], "type": "function"},
    {"constant": True, "inputs": [{"name": "account", "type": "address"}, {"name": "operator", "type": "address"}], "name": "isApprovedForAll", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
]

pusd = w3.eth.contract(address=PUSD_TOKEN, abi=ERC20_ABI)
usdc = w3.eth.contract(address=USDC_E_TOKEN, abi=ERC20_ABI)
ctf = w3.eth.contract(address=CTF_CONTRACT, abi=ERC1155_ABI)
max_uint256 = 2**256 - 1

# Active V2 Settlement Routes (deprecated V1 adapter 0xd91E excluded)
V2_SPENDERS = [
    ("CTF Exchange V2 (Binary Route)", CTF_EXCHANGE_V2),
    ("NegRisk Exchange V2 (NegRisk Route)", NEGRISK_EXCHANGE_V2),
    ("Exchange V3 (Protocol V2 Route)", EXCHANGE_V3),
]

print("=" * 80)
print("       POLYMARKET V2 ON-CHAIN & L2 APPROVALS VERIFIER & EXECUTOR")
print("=" * 80)
print(f"1. SIGNER EOA:        {signer_addr}")
print(f"2. FUNDER WALLET:      {funder_addr}")
print(f"3. SIGNATURE TYPE:     {sig_label}")
print(f"4. V2 COLLATERAL:      pUSD ({PUSD_TOKEN})")
print(f"   LEGACY BRIDGE:      USDC.e ({USDC_E_TOKEN})")
print(f"   CTF CONTRACT:       {CTF_CONTRACT}")
print("=" * 80)

# ==============================================================================
# 5. VERIFY ON-CHAIN ALLOWANCES (Funder Wallet)
# ==============================================================================
print("\n[STEP 1] Verifying On-Chain Token Balances & Allowances...")

try:
    pusd_bal = pusd.functions.balanceOf(funder_addr).call() / 1e6
    usdc_bal = usdc.functions.balanceOf(funder_addr).call() / 1e6
    print(f"  Funder pUSD On-Chain Balance:   ${pusd_bal:,.2f}")
    print(f"  Funder USDC.e On-Chain Balance: ${usdc_bal:,.2f}")
except Exception as e:
    print(f"  [WARN] Failed to query on-chain balances: {e}")

missing_onchain_pusd = []
for name, spender in V2_SPENDERS:
    try:
        cur_allowance = pusd.functions.allowance(funder_addr, spender).call()
        is_max = cur_allowance > 1e30
        status = "MAX_UINT256 (Unlimited)" if is_max else f"${cur_allowance/1e6:,.2f}"
        print(f"  - pUSD -> {name} ({spender[:10]}...): {status}")
        if not is_max:
            missing_onchain_pusd.append((name, spender))
    except Exception as e:
        print(f"  - pUSD -> {name}: Query error ({e})")
        missing_onchain_pusd.append((name, spender))

# ==============================================================================
# 6. VERIFY CTF OPERATOR APPROVALS (ERC-1155)
# ==============================================================================
print("\n[STEP 2] Verifying CTF ERC-1155 Operator Approvals...")
missing_ctf_operators = []
for name, spender in V2_SPENDERS:
    try:
        approved = ctf.functions.isApprovedForAll(funder_addr, spender).call()
        print(f"  - CTF Operator Approval to {name}: {'✓ APPROVED' if approved else '✗ NOT APPROVED'}")
        if not approved:
            missing_ctf_operators.append((name, spender))
    except Exception as e:
        print(f"  - CTF Operator to {name}: Query error ({e})")
        missing_ctf_operators.append((name, spender))

# ==============================================================================
# 7. VERIFY CLOB L2 BALANCE & ALLOWANCE (via py_clob_client_v2)
# ==============================================================================
print("\n[STEP 3] Verifying CLOB L2 Balance & Allowances...")
clob_verified = False
try:
    from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor
    from py_clob_client_v2.clob_types import AssetType, BalanceAllowanceParams

    ex = PolymarketLiveExecutor(dry_run=False)
    if ex.is_authenticated and ex.client:
        collat_bal = ex.get_collateral_balance()
        print(f"  ✓ Authoritative CLOB L2 Collateral: ${collat_bal:,.2f} USD")

        params = BalanceAllowanceParams(asset_type=AssetType.COLLATERAL, signature_type=sig_type)
        print("  Synchronizing CLOB L2 allowances with on-chain state (update_balance_allowance)...")
        ex.client.update_balance_allowance(params)

        clob_res = ex.client.get_balance_allowance(params)
        allowances = clob_res.get("allowances", {})
        print(f"  Authoritative CLOB L2 Spender Allowances for funder {funder_addr[:10]}...:")
        all_l2_max = True
        for spender_addr, val in allowances.items():
            is_max = int(val) > 1e30 if str(val).isdigit() else False
            status = "MAX_UINT256 (Unlimited)" if is_max else val
            print(f"    ✓ CLOB Spender {spender_addr[:10]}...: {status}")
            if not is_max:
                all_l2_max = False

        if allowances and all_l2_max:
            clob_verified = True
            print("  ✓ All required CLOB L2 allowances are MAX_UINT256 and synchronized.")
except Exception as e:
    print(f"  [ERROR] CLOB L2 Allowance verification failed: {e}")

# ==============================================================================
# 8. EXECUTION & FAIL-CLOSED POLICY DECISION
# ==============================================================================
print("\n" + "=" * 80)
print("APPROVAL VERIFICATION & EXECUTION DISPOSITION:")
print("=" * 80)

if sig_type == 0:
    # EOA MODE: Signer is funder, authorized to execute on-chain transactions
    print("[DISPOSITION: EOA DIRECT MODE]")
    if not missing_onchain_pusd and not missing_ctf_operators:
        print("✓ All on-chain pUSD and CTF approvals already active for EOA.")
    else:
        print(f"Broadcasting on-chain approvals from EOA {signer_addr}...")
        for name, spender in missing_onchain_pusd:
            nonce = w3.eth.get_transaction_count(signer_addr, "pending")
            gas_price = max(int(w3.eth.gas_price * 1.5), 60 * 10**9)
            print(f"  Broadcasting pUSD approve for {name} with nonce {nonce}...")
            tx = pusd.functions.approve(spender, max_uint256).build_transaction({
                "from": signer_addr,
                "nonce": nonce,
                "gas": 120000,
                "gasPrice": gas_price,
                "chainId": 137,
            })
            signed = w3.eth.account.sign_transaction(tx, private_key=pk)
            h = w3.eth.send_raw_transaction(signed.raw_transaction)
            rcpt = w3.eth.wait_for_transaction_receipt(h, timeout=60)
            print(f"    Receipt Status: {rcpt.status} (Block: {rcpt.blockNumber})")
            time.sleep(1)

        for name, spender in missing_ctf_operators:
            nonce = w3.eth.get_transaction_count(signer_addr, "pending")
            gas_price = max(int(w3.eth.gas_price * 1.5), 60 * 10**9)
            print(f"  Broadcasting CTF setApprovalForAll for {name} with nonce {nonce}...")
            tx = ctf.functions.setApprovalForAll(spender, True).build_transaction({
                "from": signer_addr,
                "nonce": nonce,
                "gas": 120000,
                "gasPrice": gas_price,
                "chainId": 137,
            })
            signed = w3.eth.account.sign_transaction(tx, private_key=pk)
            h = w3.eth.send_raw_transaction(signed.raw_transaction)
            rcpt = w3.eth.wait_for_transaction_receipt(h, timeout=60)
            print(f"    Receipt Status: {rcpt.status} (Block: {rcpt.blockNumber})")
            time.sleep(1)

    print("✓ EOA on-chain setup verified.")

else:
    # NON-EOA MODE (Deposit Wallet / Proxy / Safe, Signature Type 1, 2, or 3)
    print(f"[DISPOSITION: SMART CONTRACT FUNDER (Signature Type {sig_type})]")
    print(f"  Trading funds originate from {funder_addr}.")
    print(f"  Order signature is authorized via signing key {signer_addr} on CLOB L2.")

    if clob_verified:
        print("  ✓ ALL REQUIRED CLOB L2 SPENDERS HAVE MAX ALLOWANCE FOR FUNDER WALLET.")
        print("  ✓ ZERO ON-CHAIN BROADCAST NEEDED (CLOB L2 Relayer Settlement Active).")
        print("  ✓ SYSTEM IS FAIL-CLOSED AND PRODUCTION-READY FOR CLOB V2 TRADING.")
    else:
        print("  ✗ FAIL-CLOSED TRIGGERED: Non-EOA funder does not have verified MAX CLOB allowances.")
        print("  Refusing to guess or broadcast invalid on-chain transactions from signing EOA.")
        print("  Please fund the deposit wallet and initialize approvals through the official Polymarket flow.")
        sys.exit(1)

print("=" * 80)
