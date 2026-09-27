#!/usr/bin/env python3
"""
AUTOMATED 4H DATA LAKE SYNCHRONIZATION & REFRESH UTILITY
======================================================
Backfills 4H OHLCV candles directly from Hyperliquid API from the last recorded
timestamp up to the present hour across all active perps.
Synchronizes:
  1. data/lake/raw_candles_4h.parquet
  2. data/pit_panel_4h.parquet
"""

import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any

import numpy as np
import polars as pl
import requests

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

RAW_4H_LAKE = PIPELINE_ROOT / "data" / "lake" / "raw_candles_4h.parquet"
PIT_4H_LAKE = PIPELINE_ROOT / "data" / "pit_panel_4h.parquet"
HL_INFO_URL = "https://api.hyperliquid.xyz/info"
HEADERS = {"Content-Type": "application/json"}


def log(msg: str):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{ts}] {msg}", flush=True)


def get_active_symbols() -> List[str]:
    """Fetch active perpetual symbols from Hyperliquid meta."""
    try:
        resp = requests.post(HL_INFO_URL, json={"type": "metaAndAssetCtxs"}, headers=HEADERS, timeout=15).json()
        universe = resp[0]["universe"]
        symbols = [u["name"] for u in universe if not u.get("isDelisted", False)]
        return symbols
    except Exception as e:
        log(f"Error fetching active symbols: {e}")
        return []


def sync_4h_candles():
    log("=== STARTING 4H DATA LAKE SYNCHRONIZATION ===")
    if not RAW_4H_LAKE.exists():
        log(f"Primary lake not found at {RAW_4H_LAKE}. Aborting.")
        return

    df_existing = pl.read_parquet(RAW_4H_LAKE)
    last_ms = int(df_existing["timestamp_ms"].max())
    last_date = datetime.fromtimestamp(last_ms / 1000, timezone.utc)
    log(f"Existing Lake Rows: {df_existing.height:,} | Last Timestamp: {last_date.strftime('%Y-%m-%d %H:%M:%S UTC')}")

    now_ms = int(time.time() * 1000)
    # Start 1 bar earlier to ensure continuity
    start_ms = last_ms - (4 * 3600 * 1000)

    symbols = get_active_symbols()
    log(f"Targeting {len(symbols)} active symbols from Hyperliquid API...")

    records = []
    fetched_count = 0
    for sym in symbols:
        payload = {
            "type": "candleSnapshot",
            "req": {
                "coin": sym,
                "interval": "4h",
                "startTime": start_ms,
                "endTime": now_ms,
            }
        }
        try:
            r = requests.post(HL_INFO_URL, json=payload, headers=HEADERS, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if data:
                    fetched_count += 1
                    for c in data:
                        records.append({
                            "symbol": sym,
                            "timestamp_ms": int(c["t"]),
                            "open": float(c["o"]),
                            "high": float(c["h"]),
                            "low": float(c["l"]),
                            "close": float(c["c"]),
                            "volume": float(c["v"]),
                            "oracle_px": float(c.get("oracle", c["c"])),
                        })
            time.sleep(0.04)  # Rate throttle
        except Exception as e:
            continue

    if not records:
        log("No new candles returned. Lake is already up to date.")
        return

    df_new = pl.from_dicts(records)
    log(f"Fetched {len(records):,} new candle observations across {fetched_count} symbols.")

    # Merge and deduplicate
    df_combined = (
        pl.concat([df_existing, df_new], how="diagonal")
        .unique(subset=["symbol", "timestamp_ms"])
        .sort(["timestamp_ms", "symbol"])
    )

    new_last_ms = int(df_combined["timestamp_ms"].max())
    new_last_date = datetime.fromtimestamp(new_last_ms / 1000, timezone.utc)
    log(f"Merged Total Rows: {df_combined.height:,} (+{df_combined.height - df_existing.height:,}) | New Horizon: {new_last_date.strftime('%Y-%m-%d %H:%M:%S UTC')}")

    # Atomic write to RAW_4H_LAKE
    temp_raw = RAW_4H_LAKE.with_suffix(".tmp")
    df_combined.write_parquet(temp_raw)
    temp_raw.replace(RAW_4H_LAKE)
    log(f"Updated primary lake at: {RAW_4H_LAKE}")

    # Synchronize to pit_panel_4h.parquet
    temp_pit = PIT_4H_LAKE.with_suffix(".tmp")
    df_combined.write_parquet(temp_pit)
    temp_pit.replace(PIT_4H_LAKE)
    log(f"Synchronized root feature lake at: {PIT_4H_LAKE}")

    log("=== 4H DATA LAKE SYNCHRONIZATION COMPLETE ===")


if __name__ == "__main__":
    sync_4h_candles()
