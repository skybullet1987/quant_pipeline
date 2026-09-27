import sys
import json
import time
from pathlib import Path

PIPELINE_ROOT = Path.home() / "quant_pipeline"
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from dagster import asset, Definitions, ScheduleDefinition
from hyperliquid.info import Info
from hyperliquid.utils import constants
import polars as pl

from src.data.universe_manager import HyperliquidUniverseManager

UNIVERSE_FILE = PIPELINE_ROOT / "data" / "lake" / "universe" / "active_universe.json"
LAKE_FILE = PIPELINE_ROOT / "data" / "lake" / "features" / "pit_panel_4h.parquet"

@asset(description="Screens Top-100 liquid perpetuals from Hyperliquid Mainnet.")
def hyperliquid_active_universe():
    screener = HyperliquidUniverseManager(target_universe_size=100)
    symbols = screener.screen_universe()
    return symbols

@asset(deps=[hyperliquid_active_universe], description="Appends latest 4H closed bars and updates PIT feature panel.")
def continuous_pit_feature_panel():
    with open(UNIVERSE_FILE, "r") as f:
        symbols = json.load(f)["symbols"]

    info = Info(constants.MAINNET_API_URL, skip_ws=True)
    now_ms = int(time.time() * 1000)
    lookback_ms = now_ms - (48 * 3600 * 1000)

    existing_df = pl.read_parquet(LAKE_FILE)
    max_existing_ts = existing_df.select(pl.max("timestamp_ms")).to_series()[0]

    new_records = []
    for sym in symbols:
        try:
            candles = info.candles_snapshot(sym, "4h", lookback_ms, now_ms)
            if not candles:
                continue
            for c in candles:
                ts = int(c["t"])
                if ts > max_existing_ts:
                    new_records.append({
                        "timestamp_ms": ts,
                        "symbol": sym,
                        "open": float(c["o"]),
                        "high": float(c["h"]),
                        "low": float(c["l"]),
                        "close": float(c["c"]),
                        "volume": float(c["v"]),
                        "num_trades": float(c["n"])
                    })
        except Exception:
            continue

    if new_records:
        new_df = pl.DataFrame(new_records)
        combined = pl.concat([existing_df.select(new_df.columns), new_df]).unique(subset=["timestamp_ms", "symbol"]).sort(["timestamp_ms", "symbol"])
        combined.write_parquet(LAKE_FILE)
        print(f"[DAGSTER] Appended {len(new_records)} new 4H bar records to feature lake.")
    else:
        print("[DAGSTER] Feature lake is up to date.")

defs = Definitions(
    assets=[hyperliquid_active_universe, continuous_pit_feature_panel],
    schedules=[
        ScheduleDefinition(
            name="four_hourly_lake_sync",
            target=[hyperliquid_active_universe, continuous_pit_feature_panel],
            cron_schedule="0 */4 * * *"
        )
    ]
)
