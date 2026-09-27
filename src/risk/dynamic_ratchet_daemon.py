import os
import time
import math
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
import polars as pl
from eth_account import Account
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

load_dotenv(Path.home() / "quant_pipeline" / ".env")

WALLET = os.getenv("HYPERLIQUID_ACCOUNT_ADDRESS", "0x9703b71686219d34869e8fb89a93263f9e0d50a5").lower().strip()
PRIV_KEY = os.getenv("HYPERLIQUID_PRIVATE_KEY", "").strip()
LAKE_FILE = Path.home() / "quant_pipeline" / "data" / "lake" / "features" / "pit_panel_4h.parquet"
STATE_FILE = Path.home() / "quant_pipeline" / "data" / "lake" / "telemetry" / "ratchet_state.json"
LOG_FILE = Path.home() / "quant_pipeline" / "data" / "lake" / "telemetry" / "ratchet_daemon.log"

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger().addHandler(console)

info = Info(constants.TESTNET_API_URL, skip_ws=True)
account = Account.from_key(PRIV_KEY)
exchange = Exchange(account, constants.TESTNET_API_URL, account_address=WALLET if WALLET != account.address.lower() else None)

def round_sig_figs(val: float, sig_figs: int = 5) -> float:
    if val == 0: return 0.0
    return round(val, sig_figs - int(math.floor(math.log10(abs(val)))) - 1)

def run_ratchet_monitor():
    logging.info("Dynamic Ratchet & Chandelier Stop Monitor initialized.")
    tracking_state = {}
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r") as f:
                tracking_state = json.load(f)
        except Exception as e:
            logging.error(f"Failed loading tracking state: {e}")

    while True:
        try:
            user_state = info.user_state(WALLET)
            open_orders = info.open_orders(WALLET)
            all_mids = info.all_mids()
            positions = [p["position"] for p in user_state.get("assetPositions", []) if float(p["position"]["szi"]) != 0]

            active_coins = {p["coin"] for p in positions}
            tracking_state = {k: v for k, v in tracking_state.items() if k in active_coins}

            df = pl.read_parquet(LAKE_FILE) if LAKE_FILE.exists() else None

            for p in positions:
                coin = p["coin"]
                szi = float(p["szi"])
                entry_px = float(p["entryPx"])
                sz = abs(szi)
                is_long = szi > 0
                current_px = float(all_mids.get(coin, entry_px))

                # Safe State Initialization
                if coin not in tracking_state:
                    tracking_state[coin] = {
                        "peak_px": max(entry_px, current_px) if is_long else min(entry_px, current_px),
                        "trough_px": min(entry_px, current_px) if is_long else max(entry_px, current_px),
                        "stage": "STAGE_1_INITIAL",
                        "active_sl_oid": None,
                        "current_sl_px": 0.0
                    }

                pos_track = tracking_state[coin]
                pos_track["peak_px"] = max(pos_track["peak_px"], current_px)
                pos_track["trough_px"] = min(pos_track["trough_px"], current_px)

                # Fail-Closed ATR Lookup
                atr = None
                if df is not None:
                    sub = df.filter(pl.col("symbol") == coin)
                    if sub.height > 0 and "atr_14" in sub.columns:
                        val = float(sub.select(pl.col("atr_14").last()).to_series()[0])
                        if val > 0: atr = val

                if atr is None:
                    logging.warning(f"{coin}: ATR unavailable in lake. Retaining emergency initial stop.")
                    continue

                mfe_atr = (pos_track["peak_px"] - entry_px) / atr if is_long else (entry_px - pos_track["trough_px"]) / atr

                target_sl = None
                new_stage = pos_track["stage"]

                # Stage 2: Chandelier Trailing Stop (+2.0x ATR MFE)
                if mfe_atr >= 2.0:
                    chandelier_sl = pos_track["peak_px"] - (2.0 * atr) if is_long else pos_track["trough_px"] + (2.0 * atr)
                    if is_long and chandelier_sl > pos_track.get("current_sl_px", 0.0):
                        target_sl = chandelier_sl
                        new_stage = "STAGE_3_CHANDELIER"
                    elif not is_long and (pos_track.get("current_sl_px", 0.0) == 0.0 or chandelier_sl < pos_track["current_sl_px"]):
                        target_sl = chandelier_sl
                        new_stage = "STAGE_3_CHANDELIER"

                # Stage 1: Breakeven Ratchet (+1.5x ATR MFE)
                elif mfe_atr >= 1.5 and pos_track["stage"] == "STAGE_1_INITIAL":
                    be_sl = entry_px + (0.10 * atr) if is_long else entry_px - (0.10 * atr)
                    target_sl = be_sl
                    new_stage = "STAGE_2_BREAKEVEN"

                # Atomic Protection Update: Place New Trigger BEFORE Canceling Old Trigger
                if target_sl is not None:
                    target_sl = round_sig_figs(target_sl)
                    old_sl_orders = [o for o in open_orders if o.get("coin") == coin and "sl" in str(o).lower()]
                    
                    logging.info(f"Advancing Stop for {coin}: {pos_track['stage']} -> {new_stage} | Target SL: ${target_sl:.4f} (MFE: {mfe_atr:.2f} ATR)")

                    try:
                        res = exchange.order(
                            name=coin,
                            is_buy=not is_long,
                            sz=sz,
                            limit_px=target_sl,
                            order_type={"trigger": {"isMarket": True, "triggerPx": target_sl, "tpsl": "sl"}},
                            reduce_only=True
                        )
                        
                        if res.get("status") == "ok":
                            pos_track["current_sl_px"] = target_sl
                            pos_track["stage"] = new_stage

                            # Verification Succeeded: Cancel Old Stop Triggers
                            for o in old_sl_orders:
                                try:
                                    c_res = exchange.cancel(coin, o["oid"])
                                    if c_res.get("status") != "ok":
                                        logging.critical(f"CRITICAL: Failed to cancel superseded SL oid {o['oid']} for {coin}: {c_res}")
                                except Exception as c_err:
                                    logging.critical(f"CRITICAL: SL cancel exception for {coin} oid {o['oid']}: {c_err}")
                        else:
                            logging.error(f"SL placement rejected by exchange for {coin}: {res}")

                    except Exception as order_err:
                        logging.error(f"SL replacement network exception for {coin}: {order_err}")

            with open(STATE_FILE, "w") as f:
                json.dump(tracking_state, f, indent=2)

        except Exception as loop_err:
            logging.error(f"Unexpected exception in ratchet loop: {loop_err}")

        time.sleep(15)

if __name__ == "__main__":
    run_ratchet_monitor()
