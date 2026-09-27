import os
from pathlib import Path
from datetime import datetime, timezone
import polars as pl
from dagster import asset, AssetExecutionContext, Output
from hyperliquid.info import Info
from hyperliquid.utils import constants

LAKE_DIR = Path("/tmp/lake")


@asset(group_name="monitoring", compute_kind="hyperliquid_api")
def live_portfolio_telemetry(context: AssetExecutionContext) -> Output[dict]:
    """Syncs live margin state, positions, and unrealized PnL into the telemetry lake."""
    addr = os.getenv("HYPERLIQUID_ACCOUNT_ADDRESS", "0x9703B71686219D34869e8FB89a93263f9e0d50A5")
    use_testnet = os.getenv("HYPERLIQUID_TESTNET", "true").lower() == "true"
    base_url = constants.TESTNET_API_URL if use_testnet else constants.MAINNET_API_URL

    info = Info(base_url, skip_ws=True)
    user_state = info.user_state(addr)
    spot_state = info.spot_user_state(addr)

    perp_val = float(user_state.get("marginSummary", {}).get("accountValue", 0.0))
    spot_usdc = sum(float(b["total"]) for b in spot_state.get("balances", []) if b["coin"] == "USDC")
    total_val = perp_val + spot_usdc

    positions = []
    for p in user_state.get("assetPositions", []):
        pos = p.get("position", {})
        if float(pos.get("szi", 0.0)) != 0.0:
            positions.append({
                "timestamp_utc": datetime.now(timezone.utc),
                "coin": pos["coin"],
                "size": float(pos["szi"]),
                "entry_px": float(pos["entryPx"]),
                "unrealized_pnl": float(pos.get("unrealizedPnl", 0.0)),
                "leverage": float(pos.get("leverage", {}).get("value", 1.0))
            })

    telemetry_summary = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "account_address": addr,
        "total_equity_usd": total_val,
        "open_positions_count": len(positions),
    }

    if positions:
        pos_df = pl.from_dicts(positions)
        pos_path = LAKE_DIR / "live_positions_telemetry.parquet"
        pos_df.write_parquet(pos_path)

    return Output(telemetry_summary, metadata=telemetry_summary)
