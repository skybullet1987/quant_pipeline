#!/usr/bin/env python3
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

PIPELINE_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PIPELINE_ROOT / ".env")

RPC = "https://polygon-bor-rpc.publicnode.com"
w3 = Web3(Web3.HTTPProvider(RPC))
try:
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
except Exception:
    pass

pk = os.getenv("POLYGON_PRIVATE_KEY", "").strip()
assert pk, "POLYGON_PRIVATE_KEY is empty!"
account = w3.eth.account.from_key(pk)
wallet_addr = account.address

USDC_E = Web3.to_checksum_address("0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174")
CTF_EXCHANGE = Web3.to_checksum_address("0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E")
NEGRISK_EXCHANGE = Web3.to_checksum_address("0xC5d563A36AE78145C45a50134d48A1215220f80a")
NEGRISK_ADAPTER = Web3.to_checksum_address("0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296")

ERC20_ABI = [
    {"constant": False, "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}, {"name": "_spender", "type": "address"}], "name": "allowance", "outputs": [{"name": "", "type": "uint256"}], "type": "function"}
]

usdc = w3.eth.contract(address=USDC_E, abi=ERC20_ABI)
max_uint256 = 2**256 - 1

spenders = [
    ("CTF Exchange", CTF_EXCHANGE),
    ("NegRisk Exchange", NEGRISK_EXCHANGE),
    ("NegRisk Adapter", NEGRISK_ADAPTER),
]

print(f"Executing approvals for wallet: {wallet_addr}")
for name, spender in spenders:
    cur = usdc.functions.allowance(wallet_addr, spender).call()
    if cur > 1e30:
        print(f"  ✓ {name}: Already has Max Allowance!")
        continue
    
    nonce = w3.eth.get_transaction_count(wallet_addr, "pending")
    gas_price = max(int(w3.eth.gas_price * 1.5), 60 * 10**9) # At least 60 Gwei
    print(f"  Broadcasting approve for {name} with nonce {nonce} @ {gas_price/1e9:.1f} Gwei...")
    tx = usdc.functions.approve(spender, max_uint256).build_transaction({
        "from": wallet_addr,
        "nonce": nonce,
        "gas": 120000,
        "gasPrice": gas_price,
        "chainId": 137
    })
    signed = w3.eth.account.sign_transaction(tx, private_key=pk)
    h = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"    Tx hash: {h.hex()}")
    rcpt = w3.eth.wait_for_transaction_receipt(h, timeout=60)
    print(f"    Receipt Status: {rcpt.status} (Block: {rcpt.blockNumber})")
    time.sleep(2)

print("\nALL APPROVALS COMPLETED SUCCESSFULLY!")
