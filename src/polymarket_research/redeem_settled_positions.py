#!/usr/bin/env python3
"""
POLYMARKET CTF SETTLEMENT & REDEMPTION MONITOR (v1.0.0)
======================================================
Audits resolved prediction positions, inspects on-chain CTF Conditional Token
balances for the Polymarket Deposit Proxy wallet, and reports claimable collateral.

Addresses:
  - Conditional Tokens (CTF): 0x4D97DCd97eC945f40cF65F87097ACe5EA0476045
  - USDC.e (Bridged):         0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174
  - Polymarket NegRisk CTF:   0xC5d563A36AE78145C45a50134d48A1215220f80a
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

PIPELINE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

load_dotenv(PIPELINE_ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s UTC] [%(levelname)s] [CTF-REDEMPTION] %(message)s",
)
logger = logging.getLogger("CTFRedemption")

CTF_CONTRACT = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"
USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
POLYGON_RPC = "https://polygon-bor-rpc.publicnode.com"

DATA_DIR = PIPELINE_ROOT / "data/polymarket"
STATE_FILE = DATA_DIR / "live_harvester_state.json"


from typing import Optional

def get_token_balance_onchain(funder_address: str, token_id: str) -> Optional[float]:
    """Queries ERC-1155 balanceOf(account, tokenId) via Polygon RPC."""
    try:
        # ERC1155 balanceOf(address,uint256) selector: 0x00fdd58e
        addr_padded = funder_address.lower().replace("0x", "").zfill(64)
        token_hex = hex(int(token_id))[2:].zfill(64)
        call_data = f"0x00fdd58e{addr_padded}{token_hex}"

        payload = {
            "jsonrpc": "2.0",
            "method": "eth_call",
            "params": [{"to": CTF_CONTRACT, "data": call_data}, "latest"],
            "id": 1,
        }
        response = requests.post(POLYGON_RPC, json=payload, timeout=5)
        response.raise_for_status()
        resp = response.json()
        if resp.get("error") or not isinstance(resp.get("result"), str):
            raise RuntimeError(f"Invalid eth_call response: {resp}")
        result_hex = resp["result"]
        raw_balance = int(result_hex, 16)
        return raw_balance / 1e6
    except Exception as e:
        logger.error(f"Error querying on-chain balance for {token_id}: {e}")
        return None


def audit_positions_and_redemptions():
    funder_address = os.getenv("POLYGON_FUNDER_ADDRESS", "").strip() or os.getenv("POLYGON_PROXY_ADDRESS", "").strip()
    if not funder_address:
        logger.error("No funder/proxy address configured in .env!")
        return

    print("=" * 80)
    print("      POLYMARKET CTF SETTLEMENT & REDEMPTION AUDITOR")
    print("=" * 80)
    print(f"Proxy Wallet: {funder_address}")
    print(f"CTF Contract: {CTF_CONTRACT}")

    if not STATE_FILE.exists():
        print(f"\nNo state file found at {STATE_FILE}. Zero recorded positions.")
        return

    with open(STATE_FILE, "r") as f:
        state = json.load(f)

    active_positions = state.get("active_positions", {})
    closed_positions = state.get("closed_positions", [])

    print(f"\nActive Positions: {len(active_positions)}")
    print(f"Closed Positions: {len(closed_positions)}")

    unredeemed_shares = 0.0
    estimated_claimable_usd = 0.0
    has_unknown = False

    print("\n--- POSITION AUDIT TABLE ---")
    for pos in closed_positions:
        tid = pos.get("trade_id", "N/A")
        token_id = pos.get("token_id")
        won = pos.get("won", False)
        shares = pos.get("entry_shares", 0.0)
        close_reason = pos.get("close_reason", "UNKNOWN")
        net_pnl = pos.get("net_pnl_usd", 0.0)

        # If position won at market resolution, check on-chain token balance
        if won and close_reason == "MARKET_RESOLVED" and token_id:
            onchain_bal = get_token_balance_onchain(funder_address, token_id)
            if onchain_bal is None:
                has_unknown = True
                print(f"  [UNKNOWN / RETRY] {tid}: Polygon balance query failed; cannot classify redemption state")
                continue
            if onchain_bal > 0.01:
                unredeemed_shares += onchain_bal
                estimated_claimable_usd += onchain_bal * 1.0
                print(f"  [CLAIMABLE] {tid}: {onchain_bal:.2f} shares held on-chain -> ${onchain_bal:.2f} USDC.e claimable")
            else:
                print(f"  [REDEEMED/EMPTY] {tid}: 0.00 shares held on-chain (already redeemed)")
        else:
            print(f"  [{close_reason}] {tid}: Won={won} | Net PnL=${net_pnl:+.2f}")

    print("\n" + "=" * 80)
    print(f"Total Claimable Winning Shares: {unredeemed_shares:.2f}")
    print(f"Estimated Claimable Collateral:   ${estimated_claimable_usd:.2f} USDC.e")
    print("=" * 80)

    if estimated_claimable_usd > 0:
        print("\n[ACTION REQUIRED: REDEMPTION GUIDANCE]")
        print("Because the Proxy Wallet holds 0 POL, direct on-chain contract calls require gas.")
        print("To redeem winning shares gaslessly:")
        print("  1. Log into https://polymarket.com using your funder wallet.")
        print("  2. Navigate to Portfolio -> History / Positions.")
        print("  3. Click 'Claim All' / 'Redeem' (Polymarket's relayer pays Polygon gas automatically).")
        print("  4. USDC.e will be instantly credited to your collateral balance.")
    elif has_unknown:
        print("\n[WARNING] One or more positions could not be queried on-chain. Reconciliation incomplete - retry required.")
    else:
        print("\nAll winning positions are reconciled. No unredeemed tokens pending.")


if __name__ == "__main__":
    audit_positions_and_redemptions()
