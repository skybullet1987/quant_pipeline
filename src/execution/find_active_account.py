import requests
import json
from pathlib import Path

MASTER_ADDR = "0x9703b71686219d34869e8fb89a93263f9e0d50a5"
URL = "https://api.hyperliquid.xyz/info"
HEADERS = {"Content-Type": "application/json"}
CONFIG_PATH = Path.home() / "quant_pipeline" / "config" / "secrets.json"

print("=" * 65)
print(f"Scanning linked accounts for Master: {MASTER_ADDR}")
print("=" * 65)

# 1. Query linked Subaccounts
try:
    subaccounts = requests.post(URL, headers=HEADERS, json={"type": "subAccounts", "user": MASTER_ADDR}, timeout=10).json()
except Exception as e:
    subaccounts = []

# 2. Query linked Vaults
try:
    vaults = requests.post(URL, headers=HEADERS, json={"type": "userVaultEquities", "user": MASTER_ADDR}, timeout=10).json()
except Exception as e:
    vaults = []

candidate_addresses = [{"name": "Master Wallet", "address": MASTER_ADDR}]

if isinstance(subaccounts, list):
    for sub in subaccounts:
        sub_addr = sub.get("subAccountUser", sub.get("user", ""))
        name = sub.get("name", "SubAccount")
        if sub_addr:
            candidate_addresses.append({"name": f"SubAccount ({name})", "address": sub_addr.lower()})

if isinstance(vaults, list):
    for v in vaults:
        v_addr = v.get("vaultAddress", "")
        if v_addr:
            candidate_addresses.append({"name": "Vault", "address": v_addr.lower()})

target_address = None
max_equity = 0.0

for cand in candidate_addresses:
    addr = cand["address"]
    label = cand["name"]
    
    # Query perps clearinghouse
    perp_res = requests.post(URL, headers=HEADERS, json={"type": "clearinghouseState", "user": addr}).json()
    account_val = float(perp_res.get("marginSummary", {}).get("accountValue", 0.0))
    pos_count = len(perp_res.get("assetPositions", []))
    
    # Query spot clearinghouse
    spot_res = requests.post(URL, headers=HEADERS, json={"type": "spotClearinghouseState", "user": addr}).json()
    spot_usdc = sum(float(b["total"]) for b in spot_res.get("balances", []) if b.get("coin") == "USDC")
    
    print(f"\n[{label}] {addr}")
    print(f"  * Perp Account Equity : ${account_val:,.2f}")
    print(f"  * Open Perp Positions : {pos_count}")
    print(f"  * Spot USDC Collateral: ${spot_usdc:,.2f}")
    
    if account_val > max_equity or pos_count > 0:
        max_equity = max(account_val, spot_usdc)
        target_address = addr

print("\n" + "=" * 65)
if target_address and target_address != MASTER_ADDR:
    print(f"[FOUND] Active trading account identified: {target_address} (Equity: ${max_equity:,.2f})")
    
    # Update secrets.json
    with open(CONFIG_PATH, "r") as f:
        cfg = json.load(f)
    cfg["account_address"] = target_address
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)
    print(f"[UPDATED] secrets.json successfully mapped to active trading address: {target_address}")
elif target_address == MASTER_ADDR and max_equity <= 10.0:
    print("[NOTE] No automated subaccounts detected via API query.")
    print("Please check your Hyperliquid UI profile dropdown for the exact subaccount address.")
else:
    print(f"[READY] Active account set to {MASTER_ADDR}")
print("=" * 65 + "\n")
