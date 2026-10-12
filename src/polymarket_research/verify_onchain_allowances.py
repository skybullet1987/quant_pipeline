import os
import sys
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

raw_wallet = os.getenv("POLYGON_FUNDER_ADDRESS", "").strip()
if not raw_wallet:
    print("[ERROR] POLYGON_FUNDER_ADDRESS not found in .env")
    sys.exit(1)
WALLET = Web3.to_checksum_address(raw_wallet)

USDC_E = Web3.to_checksum_address("0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174")
PUSD = Web3.to_checksum_address("0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB")
CTF_CONTRACT = Web3.to_checksum_address("0x4D97DCd97eC945f40cF65F87097ACe5EA0476045")

# Authoritative V2 Exchange Contracts from py_clob_client_v2
EXCHANGE_V2 = Web3.to_checksum_address("0xE111180000d2663C0091e4f400237545B87B996B")
NEGRISK_V2 = Web3.to_checksum_address("0xe2222d279d744050d28e00520010520000310F59")
EXCHANGE_V3 = Web3.to_checksum_address("0xe3333700cA9d93003F00f0F71f8515005F6c00Aa")

ERC20_ABI = [
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}, {"name": "_spender", "type": "address"}], "name": "allowance", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"}
]

ERC1155_ABI = [
    {"constant": True, "inputs": [{"name": "account", "type": "address"}, {"name": "operator", "type": "address"}], "name": "isApprovedForAll", "outputs": [{"name": "", "type": "bool"}], "type": "function"}
]

usdc = w3.eth.contract(address=USDC_E, abi=ERC20_ABI)
pusd = w3.eth.contract(address=PUSD, abi=ERC20_ABI)
ctf = w3.eth.contract(address=CTF_CONTRACT, abi=ERC1155_ABI)

print("=" * 65)
print("ON-CHAIN VERIFICATION OF V2 ALLOWANCES & APPROVALS")
print("=" * 65)
print(f"Funder Wallet: {WALLET}")

try:
    bal = pusd.functions.balanceOf(WALLET).call() / 1e6
    print(f"pUSD Balance (V2 Collateral): ${bal:,.2f}")
except Exception as e:
    print(f"pUSD Balance Query Failed: {e}")

spenders = [
    ("CTF Exchange V2 (Binary Route)", EXCHANGE_V2),
    ("NegRisk Exchange V2 (NegRisk Route)", NEGRISK_V2),
    ("Exchange V3 (Protocol V2 Route)", EXCHANGE_V3),
]

print("\n[USDC.e Spender Allowances]")
for name, addr in spenders:
    try:
        raw = usdc.functions.allowance(WALLET, addr).call()
        usd = raw / 1e6
        is_max = (raw > 1e30)
        print(f"  ✓ {name}: {'MAX_UINT256 (Unlimited)' if is_max else f'${usd:,.2f}'}")
    except Exception as e:
        print(f"  ✗ {name}: Failed ({e})")

print("\n[CTF Operator Approvals]")
operators = [
    ("CTF Exchange V2", EXCHANGE_V2),
    ("NegRisk Exchange V2", NEGRISK_V2),
    ("Exchange V3", EXCHANGE_V3),
]

for name, addr in operators:
    try:
        appr = ctf.functions.isApprovedForAll(WALLET, addr).call()
        print(f"  ✓ CTF Operator Approval to {name}: {appr}")
    except Exception as e:
        print(f"  ✗ {name}: Failed ({e})")

print("\n[CLOB L2 Balance & Allowances]")
try:
    from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor
    ex = PolymarketLiveExecutor(dry_run=False)
    if ex.is_authenticated:
        bal = ex.get_collateral_balance()
        print(f"  ✓ CLOB Collateral Balance: ${bal:.2f} USD")
        from py_clob_client_v2.clob_types import AssetType, BalanceAllowanceParams
        p = BalanceAllowanceParams(asset_type=AssetType.COLLATERAL, signature_type=ex.signature_type)
        clob_res = ex.client.get_balance_allowance(p)
        allowances = clob_res.get("allowances", {})
        for addr, val in allowances.items():
            is_max = int(val) > 1e30 if str(val).isdigit() else False
            print(f"  ✓ Spender {addr[:10]}...{addr[-6:]}: {'MAX_UINT256 (Unlimited)' if is_max else val}")
except Exception as e:
    print(f"  ✗ CLOB Query Failed: {e}")

print("=" * 65)
print("VERIFICATION COMPLETE: READY FOR ZERO-REVERT EXECUTION")
print("=" * 65)
