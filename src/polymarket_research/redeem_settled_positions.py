#!/usr/bin/env python3
"""
POLYMARKET CTF SETTLEMENT & REDEMPTION MONITOR (v1.0.0)
======================================================
Audits resolved prediction positions, inspects on-chain CTF Conditional Token
balances for the Polymarket Deposit Proxy wallet, and reports claimable collateral.

Addresses:
  - Conditional Tokens (CTF): 0x4D97DCd97eC945f40cF65F87097ACe5EA0476045
  - USDC.e (Bridged):         0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174
  - Polymarket NegRiskAdapter: 0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296
  - Polymarket NegRisk CTF Ex: 0xC5d563A36AE78145C45a50134d48A1215220f80a
"""

import json
import logging
import math
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
NEG_RISK_ADAPTER = "0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296"
PUSD_ADDRESS = "0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB"
USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
POLYGON_RPCS = [
    os.getenv("POLYGON_RPC_URL", "https://polygon-bor-rpc.publicnode.com"),
    "https://polygon-rpc.com",
    "https://1rpc.io/matic",
]

DATA_DIR = PIPELINE_ROOT / "data/polymarket"
STATE_FILE = DATA_DIR / "live_harvester_state.json"


from typing import Optional

def get_token_balance_onchain(funder_address: str, token_id: str) -> Optional[float]:
    """Queries ERC-1155 balanceOf(account, tokenId) via Polygon RPC."""
    try:
        # ERC1155 balanceOf(address,uint256) selector: 0x00fdd58e
        addr_padded = funder_address.lower().replace("0x", "").zfill(64)
        token_int = int(token_id, 16) if str(token_id).startswith("0x") else int(token_id)
        token_hex = hex(token_int)[2:].zfill(64)
        call_data = f"0x00fdd58e{addr_padded}{token_hex}"

        payload = {
            "jsonrpc": "2.0",
            "method": "eth_call",
            "params": [{"to": CTF_CONTRACT, "data": call_data}, "latest"],
            "id": 1,
        }
        last_err = None
        for rpc_url in POLYGON_RPCS:
            try:
                response = requests.post(rpc_url, json=payload, timeout=5)
                response.raise_for_status()
                resp = response.json()
                if resp.get("error") or not isinstance(resp.get("result"), str):
                    raise RuntimeError(f"Invalid eth_call response: {resp}")
                result_hex = resp["result"]
                raw_balance = int(result_hex, 16)
                return raw_balance / 1e6
            except Exception as rpc_e:
                last_err = rpc_e
        raise RuntimeError(f"All Polygon RPCs failed: {last_err}")
    except Exception as e:
        logger.error(f"Error querying on-chain balance for {token_id}: {e}")
        return None


def encode_ctf_merge_or_split_calldata(
    condition_id: str,
    amount_shares: float,
    collateral: str = USDC_ADDRESS,
    is_split: bool = False,
    neg_risk: bool = False,
    is_merge: Optional[bool] = None,
) -> tuple[str, str]:
    """
    ABI-encodes Polygon instant pre-expiry `mergePositions` (burns `1 YES + 1 NO -> $1.00 USDC.e` in ~3s)
    or `splitPosition` (mints `$1.00 USDC.e -> 1 YES + 1 NO` for `CTF_OVERROUND_MINT_SELL`).
    Returns `(target_contract_address, 0x_calldata)`.
    """
    eff_split = (not bool(is_merge)) if is_merge is not None else bool(is_split)
    raw_amt = int(math.floor(max(0.0, float(amount_shares)) * 1_000_000 + 1e-6))
    if raw_amt <= 0:
        raise ValueError("amount_shares must be > 0")
    cond_hex = condition_id.lower().replace("0x", "").rjust(64, "0")
    amt_hex = hex(raw_amt)[2:].rjust(64, "0")
    if neg_risk:
        sel = "0xa3d7da1d" if eff_split else "0xb10c5c17"
        return NEG_RISK_ADAPTER, f"{sel}{cond_hex}{amt_hex}"
    sel = "0x72ce4275" if eff_split else "0x9e7212ad"
    col_hex = collateral.lower().replace("0x", "").rjust(64, "0")
    zero_b32 = "0" * 64
    arr_offset = hex(5 * 32)[2:].rjust(64, "0")
    arr_len = hex(2)[2:].rjust(64, "0")
    idx_1 = hex(1)[2:].rjust(64, "0")
    idx_2 = hex(2)[2:].rjust(64, "0")
    return CTF_CONTRACT, f"{sel}{col_hex}{zero_b32}{cond_hex}{arr_offset}{amt_hex}{arr_len}{idx_1}{idx_2}"


def inspect_mergeable_complete_set(
    funder_or_condition_id: str,
    yes_token_or_shares: Any,
    no_token_or_shares: Any,
    neg_risk: Optional[bool] = None,
) -> Any:
    """
    Dual-mode complete-set inspector:
      - Pure balance mode (`yes_token_or_shares` / `no_token_or_shares` numeric or `neg_risk is not None`):
        returns `{"mergeable": bool, "mergeable_sets": float, "target_contract": str, "calldata": str}`.
      - Live RPC mode (`(funder_address, yes_token_id, no_token_id)` strings):
        queries Polygon ERC-1155 balances and returns mergeable complete-set shares (`float`).
    """
    if neg_risk is not None or isinstance(yes_token_or_shares, (int, float)):
        sets = round(max(0.0, min(float(yes_token_or_shares or 0.0), float(no_token_or_shares or 0.0))), 6)
        if sets <= 0.0:
            return {"mergeable": False, "mergeable_sets": 0.0, "target_contract": "", "calldata": ""}
        tgt, cd = encode_ctf_merge_or_split_calldata(
            funder_or_condition_id, sets, neg_risk=bool(neg_risk), is_merge=True
        )
        return {"mergeable": True, "mergeable_sets": sets, "target_contract": tgt, "calldata": cd}

    b_y = get_token_balance_onchain(funder_or_condition_id, str(yes_token_or_shares))
    b_n = get_token_balance_onchain(funder_or_condition_id, str(no_token_or_shares))
    if b_y is None or b_n is None:
        return 0.0
    return round(max(0.0, min(b_y, b_n)), 6)


def _is_harvester_lock_active(lock_path: Path) -> bool:
    """Checks whether live_harvester.pid.lock belongs to a currently running process."""
    if not lock_path.exists():
        return False
    try:
        raw_pid = lock_path.read_text(encoding="utf-8").strip()
        if not raw_pid.isdigit():
            return False
        pid = int(raw_pid)
        if pid <= 0:
            return False
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True
    except OSError:
        return False


def _is_flock_held(lock_path: Path) -> bool:
    """Returns True when another process (the Live Harvester) currently holds an exclusive flock on `lock_path`."""
    if not lock_path.exists():
        return False
    try:
        import fcntl
    except ImportError:
        return False
    try:
        with open(lock_path, "a+") as fh:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        return False
    except BlockingIOError:
        return True
    except OSError:
        return False


def audit_positions_and_redemptions(execute: bool = False, force: bool = False):
    funder_address = os.getenv("POLYGON_FUNDER_ADDRESS", "").strip() or os.getenv("POLYGON_PROXY_ADDRESS", "").strip()
    if not funder_address:
        logger.error("No funder/proxy address configured in .env!")
        return

    print("=" * 80)
    print("      POLYMARKET CTF SETTLEMENT & REDEMPTION AUDITOR")
    print("=" * 80)
    print(f"Proxy Wallet: {funder_address}")
    print(f"CTF Contract: {CTF_CONTRACT}")
    print(f"Collateral:   pUSD ({PUSD_ADDRESS}) / USDC.e ({USDC_ADDRESS})")

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
    claimable_conditions: List[str] = []
    claimable_meta: Dict[str, Dict[str, Any]] = {}

    print("\n--- POSITION AUDIT TABLE ---")
    for pos in list(active_positions.values()) + list(closed_positions):
        tid = pos.get("trade_id", "N/A")
        token_id = pos.get("token_id")
        won = pos.get("won", False)
        close_reason = pos.get("close_reason", "UNKNOWN")
        net_pnl = pos.get("net_pnl_usd", 0.0)

        # Candidate if awaiting on-chain settlement, holding winning shares, or a confirmed winning resolution.
        is_candidate = (
            pos.get("status") == "AWAITING_ONCHAIN_SETTLEMENT"
            or float(pos.get("winning_shares_held", 0.0) or 0.0) > 0.0
            or (bool(won) and close_reason in {"MARKET_RESOLVED", "ONCHAIN_REDEMPTION_CONFIRMED"})
        )
        # If position won at market resolution, check on-chain token balance
        if is_candidate and token_id:
            onchain_bal = get_token_balance_onchain(funder_address, token_id)
            if onchain_bal is None:
                has_unknown = True
                print(f"  [UNKNOWN / RETRY] {tid}: Polygon balance query failed; cannot classify redemption state")
                continue
            if onchain_bal > 0.01:
                unredeemed_shares += onchain_bal
                estimated_claimable_usd += onchain_bal * 1.0
                cid = str(pos.get("condition_id") or "").strip()
                if cid and cid not in claimable_conditions:
                    claimable_conditions.append(cid)
                    claimable_meta[cid] = {
                        "neg_risk": pos.get("neg_risk"),
                        "winning_token_id": str(token_id),
                    }
                print(f"  [CLAIMABLE] {tid}: {onchain_bal:.2f} shares held on-chain -> ${onchain_bal:.2f} pUSD/USDC.e claimable")
            else:
                print(f"  [REDEEMED/EMPTY] {tid}: 0.00 shares held on-chain (already redeemed)")
        else:
            print(f"  [{close_reason}] {tid}: Won={won} | Net PnL=${net_pnl:+.2f}")

    print("\n" + "=" * 80)
    print(f"Total Claimable Winning Shares: {unredeemed_shares:.2f}")
    print(f"Estimated Claimable Collateral:   ${estimated_claimable_usd:.2f} pUSD/USDC.e")
    print("=" * 80)

    if execute and claimable_conditions:
        # Harvester writes its PID to `live_harvester.pid` and holds an flock on `live_harvester.lock`.
        pid_lock = DATA_DIR / "live_harvester.pid"
        if not force and (_is_harvester_lock_active(pid_lock) or _is_flock_held(DATA_DIR / "live_harvester.lock")):
            logger.error(
                f"Refusing --execute while Live Harvester holds {pid_lock} (prevents EOA nonce collision with "
                "60s poll_onchain_redemptions). Stop harvester first or pass --force."
            )
            return
        from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor
        executor = PolymarketLiveExecutor(dry_run=False)
        for cid in claimable_conditions:
            meta = claimable_meta.get(cid, {})
            tx_h = executor.attempt_onchain_redemption(
                cid,
                neg_risk=meta.get("neg_risk"),
            )
            print(f"  [EXECUTE REDEMPTION] condition={cid} -> tx_hash={tx_h or 'SKIPPED (insufficient EOA POL gas or non-1of1 proxy)'}")

    if estimated_claimable_usd > 0:
        print("\n[ACTION REQUIRED: REDEMPTION GUIDANCE]")
        print("If EOA holds >= 0.05 POL, run with --execute for Safe/EOA on-chain redemption, or redeem gaslessly:")
        print("  1. Log into https://polymarket.com using your funder wallet.")
        print("  2. Navigate to Portfolio -> History / Positions.")
        print("  3. Click 'Claim All' / 'Redeem' (Polymarket's relayer pays Polygon gas automatically).")
        print("  4. Collateral (pUSD / USDC.e) will be credited to your trading balance.")
    elif has_unknown:
        print("\n[WARNING] One or more positions could not be queried on-chain. Reconciliation incomplete - retry required.")
    else:
        print("\nAll winning positions are reconciled. No unredeemed tokens pending.")


if __name__ == "__main__":
    audit_positions_and_redemptions(execute="--execute" in sys.argv, force="--force" in sys.argv)
