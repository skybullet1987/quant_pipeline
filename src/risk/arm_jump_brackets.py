import os
import math
from pathlib import Path
from dotenv import load_dotenv
import polars as pl
import numpy as np
from eth_account import Account
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

load_dotenv(Path.home() / "quant_pipeline" / ".env")

WALLET = os.getenv("HYPERLIQUID_ACCOUNT_ADDRESS", "0x9703b71686219d34869e8fb89a93263f9e0d50a5").lower().strip()
PRIV_KEY = os.getenv("HYPERLIQUID_PRIVATE_KEY", "").strip()
LAKE_FILE = Path.home() / "quant_pipeline" / "data" / "lake" / "features" / "pit_panel_4h.parquet"

info = Info(constants.TESTNET_API_URL, skip_ws=True)
account = Account.from_key(PRIV_KEY)
exchange = Exchange(
    account,
    constants.TESTNET_API_URL,
    account_address=WALLET if WALLET != account.address.lower() else None
)

def round_sig_figs(val: float, sig_figs: int = 5) -> float:
    if val == 0: return 0.0
    return round(val, sig_figs - int(math.floor(math.log10(abs(val)))) - 1)

def arm_brackets():
    user_state = info.user_state(WALLET)
    open_orders = info.open_orders(WALLET)
    positions = [p["position"] for p in user_state.get("assetPositions", []) if float(p["position"]["szi"]) != 0]

    if not positions:
        print("[BRACKETS] No open positions detected.")
        return

    # Track coins that already have resting trigger stops
    existing_triggers = set()
    for o in open_orders:
        if o.get("orderType", "") == "Trigger" or "trigger" in str(o).lower():
            existing_triggers.add(o.get("coin"))

    df = pl.read_parquet(LAKE_FILE) if LAKE_FILE.exists() else None

    print(f"\n[BRACKETS] Scanning {len(positions)} active positions...")
    for p in positions:
        coin = p["coin"]
        szi = float(p["szi"])
        entry_px = float(p["entryPx"])
        sz = abs(szi)
        is_long = szi > 0

        if coin in existing_triggers:
            print(f" • {coin:<10}: Triggers already active. Skipping.")
            continue

        # Compute Jump-Diffusion Stop Buffer using 14-period normalized ATR
        atr_pct = 0.035
        if df is not None:
            sub = df.filter(pl.col("symbol") == coin)
            if sub.height > 0:
                if "atr_14" in sub.columns and "close" in sub.columns:
                    atr_pct = float(sub.select((pl.col("atr_14") / (pl.col("close") + 1e-8)).last()).to_series()[0])
                elif "vol_yang_zhang" in sub.columns:
                    atr_pct = float(sub.select(pl.col("vol_yang_zhang").last()).to_series()[0])

        stop_dist = entry_px * max(atr_pct * 1.5, 0.02)
        tp_dist = entry_px * max(atr_pct * 2.5, 0.04)

        sl_px = round_sig_figs(entry_px - stop_dist if is_long else entry_px + stop_dist)
        tp_px = round_sig_figs(entry_px + tp_dist if is_long else entry_px - tp_dist)

        print(f" • {coin:<10}: Arming Native Brackets | Entry: ${entry_px:.4f} -> SL: ${sl_px:.4f} | TP: ${tp_px:.4f}")

        # Native Stop Loss (Market Trigger)
        try:
            sl_res = exchange.order(
                name=coin,
                is_buy=not is_long,
                sz=sz,
                limit_px=sl_px,
                order_type={"trigger": {"isMarket": True, "triggerPx": sl_px, "tpsl": "sl"}},
                reduce_only=True
            )
            print(f"   -> SL Placed: {sl_res.get('status')}")
        except Exception as e:
            print(f"   -> SL Error: {e}")

        # Native Take Profit (Market Trigger)
        try:
            tp_res = exchange.order(
                name=coin,
                is_buy=not is_long,
                sz=sz,
                limit_px=tp_px,
                order_type={"trigger": {"isMarket": True, "triggerPx": tp_px, "tpsl": "tp"}},
                reduce_only=True
            )
            print(f"   -> TP Placed: {tp_res.get('status')}")
        except Exception as e:
            print(f"   -> TP Error: {e}")

if __name__ == "__main__":
    arm_brackets()
