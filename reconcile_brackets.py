#!/usr/bin/env python3
"""
Automated Bracket Reconciler & Orphan Garbage Collector
- Detects and cancels orphaned TP/SL trigger orders on closed positions.
- Verifies that every active position has exactly two protective resting triggers.
- Automatically arms missing TP (+7.0%) and SL (-3.5%) brackets on unprotected positions.
"""

import os
import json
import logging
from typing import Dict, Any
from dotenv import load_dotenv
from eth_account.signers.local import LocalAccount
from eth_account import Account
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

from src.strategy.convex_10x_engine import round_sz, round_px, validate_l1_order

# Load environment variables from .env
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

BASE_URL = constants.TESTNET_API_URL
SECRET_KEY = (
    os.getenv("HYPERLIQUID_TESTNET_PRIVATE_KEY")
    or os.getenv("HL_TESTNET_PRIVATE_KEY")
    or os.getenv("HYPERLIQUID_PRIVATE_KEY")
    or os.getenv("TESTNET_PRIVATE_KEY")
)
MASTER_WALLET = os.getenv("HYPERLIQUID_ACCOUNT_ADDRESS")

if not SECRET_KEY:
    raise ValueError("Hyperliquid private key not found in environment or .env file.")

account: LocalAccount = Account.from_key(SECRET_KEY)
target_account = MASTER_WALLET if MASTER_WALLET else account.address

info = Info(BASE_URL, skip_ws=True)
exchange = Exchange(account, BASE_URL, account_address=target_account)

meta = info.meta()
sz_decimals: Dict[str, int] = {
    token["name"]: token["szDecimals"] for token in meta.get("universe", [])
}

DEFAULT_SL_PCT = 0.035
DEFAULT_TP_PCT = 0.070


def get_frontend_open_orders() -> list:
    try:
        res = info.post("/info", {"type": "frontendOpenOrders", "user": target_account})
        return res if isinstance(res, list) else []
    except Exception as e:
        logging.warning(f"Error fetching frontend open orders: {e}")
        return []


def run_reconciliation(auto_arm: bool = True):
    logging.info(f"Starting on-chain bracket reconciliation for account: {target_account}...")

    user_state = info.user_state(target_account)
    open_positions = {
        pos["position"]["coin"]: {
            "size": float(pos["position"]["szi"]),
            "entry_px": float(pos["position"]["entryPx"]),
        }
        for pos in user_state.get("assetPositions", [])
        if float(pos["position"]["szi"]) != 0.0
    }

    fe_orders = get_frontend_open_orders()
    triggers_by_coin: Dict[str, list] = {}
    for o in fe_orders:
        if o.get("isTrigger") or "trigger" in str(o.get("orderType", "")).lower():
            coin = o["coin"]
            triggers_by_coin.setdefault(coin, []).append(o)

    # 1. Garbage Collect Orphaned Orders
    orphans_purged = 0
    for coin, orders in triggers_by_coin.items():
        if coin not in open_positions:
            logging.warning(f"Found {len(orders)} orphaned order(s) for closed coin: {coin}. Purging...")
            for o in orders:
                try:
                    exchange.cancel(coin, o["oid"])
                    orphans_purged += 1
                    logging.info(f"  -> Canceled orphaned order OID: {o['oid']} ({o.get('orderType')})")
                except Exception as e:
                    logging.warning(f"  -> Error cancelling orphan OID {o.get('oid')}: {e}")

    # 2. Audit & Auto-Arm Protective Coverage for Open Positions
    armed_count = 0
    for coin, pos in open_positions.items():
        size = pos["size"]
        entry = pos["entry_px"]
        is_long = size > 0
        sz_abs = abs(size)
        sz_dec = sz_decimals.get(coin, 2)
        rounded_sz = abs(round_sz(sz_abs, sz_dec))
        if rounded_sz <= 0:
            continue

        raw_sl = entry * (1.0 - DEFAULT_SL_PCT) if is_long else entry * (1.0 + DEFAULT_SL_PCT)
        raw_tp = entry * (1.0 + DEFAULT_TP_PCT) if is_long else entry * (1.0 - DEFAULT_TP_PCT)
        is_buy_exit = not is_long

        sl_px = round_px(raw_sl, sz_dec)
        tp_px = round_px(raw_tp, sz_dec)

        pos_triggers = triggers_by_coin.get(coin, [])
        has_sl = False
        has_tp = False

        for o in pos_triggers:
            otype = str(o.get("orderType", "")).lower()
            t_sz = float(o.get("sz", 0))
            t_px = float(o.get("triggerPx") or o.get("origPx") or 0)
            sz_match = abs(t_sz - rounded_sz) < 1e-5

            if "stop" in otype or o.get("tpsl") == "sl":
                if sz_match and abs(t_px - sl_px) / (sl_px + 1e-8) < 0.005:
                    has_sl = True
            elif "profit" in otype or o.get("tpsl") == "tp":
                if sz_match and abs(t_px - tp_px) / (tp_px + 1e-8) < 0.005:
                    has_tp = True

        status_str = f"SL: {'OK' if has_sl else 'MISSING'} | TP: {'OK' if has_tp else 'MISSING'}"
        if has_sl and has_tp:
            logging.info(f"[HEALTHY] {coin} ({size} contracts): Full bracket protection active.")
        else:
            logging.warning(f"[UNPROTECTED] {coin} ({size} contracts): {status_str}")

            if auto_arm:
                if not has_sl:
                    val_ok, err, _, _ = validate_l1_order(symbol=coin, price=sl_px, size=rounded_sz, sz_decimals=sz_dec, is_reduce_only=True)
                    if val_ok or "notional" in err.lower():
                        try:
                            res_sl = exchange.order(
                                coin, is_buy_exit, rounded_sz, sl_px,
                                order_type={"trigger": {"isMarket": True, "triggerPx": float(sl_px), "tpsl": "sl"}},
                                reduce_only=True
                            )
                            logging.info(f"  -> Auto-armed SL for {coin}: sz={rounded_sz} @ {sl_px} | res={res_sl.get('status')}")
                            armed_count += 1
                        except Exception as e:
                            logging.error(f"  -> Failed to arm SL for {coin}: {e}")

                if not has_tp:
                    val_ok, err, _, _ = validate_l1_order(symbol=coin, price=tp_px, size=rounded_sz, sz_decimals=sz_dec, is_reduce_only=True)
                    if val_ok or "notional" in err.lower():
                        try:
                            res_tp = exchange.order(
                                coin, is_buy_exit, rounded_sz, tp_px,
                                order_type={"trigger": {"isMarket": True, "triggerPx": float(tp_px), "tpsl": "tp"}},
                                reduce_only=True
                            )
                            logging.info(f"  -> Auto-armed TP for {coin}: sz={rounded_sz} @ {tp_px} | res={res_tp.get('status')}")
                            armed_count += 1
                        except Exception as e:
                            logging.error(f"  -> Failed to arm TP for {coin}: {e}")

    logging.info(f"Reconciliation complete. Orphaned purged: {orphans_purged} | Brackets auto-armed: {armed_count}\n")


if __name__ == "__main__":
    run_reconciliation(auto_arm=True)
