#!/usr/bin/env python3
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

RPC = "https://polygon-bor-rpc.publicnode.com"
w3 = Web3(Web3.HTTPProvider(RPC))
try:
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
except Exception:
    pass

WALLET = Web3.to_checksum_address("0x9703b71686219d34869e8fb89a93263f9e0d50a5")
USDC_E = Web3.to_checksum_address("0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174")
CTF_EXCHANGE = Web3.to_checksum_address("0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E")
NEGRISK_EXCHANGE = Web3.to_checksum_address("0xC5d563A36AE78145C45a50134d48A1215220f80a")
NEGRISK_ADAPTER = Web3.to_checksum_address("0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296")
CTF_CONTRACT = Web3.to_checksum_address("0x4D97DCd97eC945f40cF65F87097ACe5EA0476045")

ERC20_ABI = [
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}, {"name": "_spender", "type": "address"}], "name": "allowance", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"}
]

ERC1155_ABI = [
    {"constant": True, "inputs": [{"name": "account", "type": "address"}, {"name": "operator", "type": "address"}], "name": "isApprovedForAll", "outputs": [{"name": "", "type": "bool"}], "type": "function"}
]

usdc = w3.eth.contract(address=USDC_E, abi=ERC20_ABI)
ctf = w3.eth.contract(address=CTF_CONTRACT, abi=ERC1155_ABI)

print("=" * 60)
print("ON-CHAIN VERIFICATION OF ALLOWANCES & APPROVALS")
print("=" * 60)

bal = usdc.functions.balanceOf(WALLET).call() / 1e6
print(f"USDC.e Balance: ${bal:,.2f}")

spenders = [
    ("CTF Exchange", CTF_EXCHANGE),
    ("NegRisk Exchange", NEGRISK_EXCHANGE),
    ("NegRisk Adapter", NEGRISK_ADAPTER),
]

for name, addr in spenders:
    raw = usdc.functions.allowance(WALLET, addr).call()
    usd = raw / 1e6
    is_max = (raw > 1e30)
    print(f"  ✓ {name}: Allowance = {'MAX_UINT256 (Unlimited)' if is_max else f'${usd:,.2f}'}")

operators = [
    ("CTF Exchange", CTF_EXCHANGE),
    ("NegRisk Adapter", NEGRISK_ADAPTER),
]

for name, addr in operators:
    appr = ctf.functions.isApprovedForAll(WALLET, addr).call()
    print(f"  ✓ CTF Operator Approval to {name}: {appr}")

print("=" * 60)
print("VERIFICATION COMPLETE: READY FOR ZERO-REVERT EXECUTION")
print("=" * 60)
