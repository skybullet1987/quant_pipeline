import math
import time
from pathlib import Path
from datetime import datetime, timezone
import polars as pl
import pandas as pd
import numpy as np
from dagster import asset, AssetExecutionContext, Output, MetadataValue

from hyperliquid.info import Info
from hyperliquid.utils import constants

LAKE_DIR = Path.home() / "quant_pipeline" / "data" / "lake"
LAKE_DIR.mkdir(parents=True, exist_ok=True)
FEATURE_DIR = LAKE_DIR / "features"
FEATURE_DIR.mkdir(parents=True, exist_ok=True)
RAW_DIR = Path.home() / "quant_pipeline" / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)


@asset(group_name="raw_ingestion", compute_kind="hyperliquid_api")
def raw_top100_1h_candles(context: AssetExecutionContext) -> Output[str]:
    """EL Layer: Ingests 1H OHLCV candles & funding rates from Hyperliquid API."""
    info = Info(constants.MAINNET_API_URL, skip_ws=True)
    meta = info.meta()
    
    # Expand breadth to all active, non-delisted universe tokens
    active_tokens = [c["name"] for c in meta["universe"] if not c.get("isDelisted", False)]
    end_ms = int(time.time() * 1000)
    start_ms = end_ms - (120 * 3600 * 1000)  # 120-hour rolling buffer for multi-horizon features

    all_bars = []
    for sym in active_tokens:
        candles = []
        for attempt in range(3):
            try:
                candles = info.candles_snapshot(sym, "1h", start_ms, end_ms)
                time.sleep(0.3)
                break
            except Exception as e:
                if '429' in str(e):
                    time.sleep(1.5 * (attempt + 1))
                else:
                    time.sleep(0.5)
        try:
            for c in candles:
                all_bars.append({
                    "symbol": sym,
                    "timestamp_ms": int(c["t"]),
                    "bucket_timestamp_utc": pd.to_datetime(c["t"], unit="ms", utc=True),
                    "open": float(c["o"]),
                    "high": float(c["h"]),
                    "low": float(c["l"]),
                    "close": float(c["c"]),
                    "volume": float(c["v"]),
                    "dollar_volume_1h": float(c["v"]) * float(c["c"]),
                })
        except Exception as e:
            context.log.warning(f"Error ingesting 1H candles for {sym}: {e}")

    if not all_bars:
        raise ValueError("No 1H candle records retrieved from Hyperliquid.")

    df_raw = pl.from_dicts(all_bars).unique(["symbol", "timestamp_ms"]).sort("timestamp_ms")

    # Ingest hourly funding rates
    meta_ctxs = info.meta_and_asset_ctxs()
    funding_map = {
        ctx["name"]: float(ctx["funding"])
        for ctx in meta_ctxs[1]
        if "name" in ctx and "funding" in ctx
    }
    df_raw = df_raw.with_columns([
        pl.col("symbol").replace(funding_map, default=0.0).alias("funding_rate")
    ])

    out_path = RAW_DIR / "raw_candles_1h.parquet"
    df_raw.write_parquet(out_path)

    return Output(
        str(out_path),
        metadata={
            "total_rows": df_raw.height,
            "unique_symbols": len(active_tokens),
            "latest_candle": str(df_raw["bucket_timestamp_utc"].max()),
        }
    )


@asset(deps=[raw_top100_1h_candles], group_name="feature_store", compute_kind="polars")
def pit_panel_1h_with_funding(context: AssetExecutionContext) -> Output[str]:
    """Feature Store: Computes 72H Yang-Zhang volatility, Tri-Alpha signals, and Delta Dispersion."""
    raw_path = RAW_DIR / "raw_candles_1h.parquet"
    df = pl.read_parquet(raw_path)

    # 1. Multi-horizon returns
    df = df.sort(["symbol", "timestamp_ms"]).with_columns([
        (pl.col("close") / pl.col("close").shift(1).over("symbol") - 1.0).alias("ret_1h"),
        (pl.col("close") / pl.col("close").shift(4).over("symbol") - 1.0).alias("ret_4h"),
        (pl.col("close") / pl.col("close").shift(12).over("symbol") - 1.0).alias("ret_12h"),
        (pl.col("close") / pl.col("close").shift(24).over("symbol") - 1.0).alias("ret_24h"),
        (pl.col("close") / pl.col("close").shift(72).over("symbol") - 1.0).alias("ret_72h")
    ])

    # 2. Yang-Zhang 72H Realized Volatility
    df = df.with_columns([
        (
            0.5 * (pl.col("high").log() - pl.col("low").log()) ** 2 -
            (2 * math.log(2) - 1) * (pl.col("close").log() - pl.col("open").log()) ** 2
        ).rolling_mean(72).over("symbol").sqrt().alias("vol_yang_zhang")
    ])

    # 3. BTC Returns & Rolling Beta
    btc = df.filter(pl.col("symbol") == "BTC").select([
        "timestamp_ms",
        pl.col("ret_1h").alias("btc_ret_1h"),
        pl.col("ret_4h").alias("btc_ret_4h"),
        pl.col("ret_12h").alias("btc_ret_12h"),
        pl.col("ret_72h").alias("btc_ret_72h")
    ]).unique(subset=["timestamp_ms"])
    df = df.join(btc, on="timestamp_ms", how="left")

    df = df.with_columns([
        (
            (pl.col("ret_1h") * pl.col("btc_ret_1h")).rolling_mean(72).over("symbol") /
            (pl.col("btc_ret_1h").pow(2).rolling_mean(72).over("symbol") + 1e-6)
        ).clip(0.20, 2.50).alias("beta_btc"),
        (
            (pl.col("dollar_volume_1h") - pl.col("dollar_volume_1h").rolling_mean(72).over("symbol")) /
            (pl.col("dollar_volume_1h").rolling_std(72).over("symbol") + 1e-5)
        ).alias("volume_zscore_72h")
    ])

    # 4. Master Tri-Alpha Signals
    df = df.with_columns([
        (
            0.20 * ((pl.col("ret_4h") - pl.col("beta_btc") * pl.col("btc_ret_4h")) / (pl.col("vol_yang_zhang") + 1e-5))
            + 0.30 * ((pl.col("ret_12h") - pl.col("beta_btc") * pl.col("btc_ret_12h")) / (pl.col("vol_yang_zhang") + 1e-5))
            + 0.50 * ((pl.col("ret_72h") - pl.col("beta_btc") * pl.col("btc_ret_72h")) / (pl.col("vol_yang_zhang") + 1e-5))
        ).alias("raw_a0"),
        (
            -1.0 * ((pl.col("ret_1h") - pl.col("beta_btc") * pl.col("btc_ret_1h")) / (pl.col("vol_yang_zhang") + 1e-5))
            * (pl.col("volume_zscore_72h").clip(-1.0, 4.0) + 1.0)
        ).alias("raw_a1"),
        (
            -1.0 * (
                ((pl.col("funding_rate") - pl.col("funding_rate").rolling_mean(24).over("symbol")) /
                 (pl.col("funding_rate").rolling_std(24).over("symbol") + 1e-6)).clip(0.0, 3.0)
                - (pl.col("ret_24h") / (pl.col("vol_yang_zhang") * math.sqrt(24) + 1e-5)).clip(-3.0, 3.0)
            )
        ).alias("raw_a2")
    ])

    # 5. Temporal EWMA Smoothing
    df = df.sort(["symbol", "timestamp_ms"]).with_columns([
        pl.col("raw_a0").ewm_mean(span=6).over("symbol").alias("a0_smooth"),
        pl.col("raw_a1").ewm_mean(span=2).over("symbol").alias("a1_smooth"),
        pl.col("raw_a2").ewm_mean(span=4).over("symbol").alias("a2_smooth")
    ])

    # 6. Cross-Sectional Standardization & Composite Score
    for col, zcol in [("a0_smooth", "z_a0"), ("a1_smooth", "z_a1"), ("a2_smooth", "z_a2")]:
        df = df.with_columns([
            ((pl.col(col) - pl.col(col).mean().over("timestamp_ms")) /
             (pl.col(col).std().over("timestamp_ms") + 1e-5)).alias(zcol)
        ])

    df = df.with_columns([
        (0.45 * pl.col("z_a0") + 0.35 * pl.col("z_a1") + 0.20 * pl.col("z_a2")).alias("master_tri_alpha")
    ])

    # 7. Cross-Sectional Dispersion Acceleration (Delta Sigma CS)
    df_disp = (
        df.filter((pl.col("dollar_volume_1h") > 25_000) & pl.col("ret_72h").is_not_null())
        .group_by("timestamp_ms")
        .agg([
            pl.col("ret_72h").std().alias("cs_disp_72h"),
            pl.len().alias("count")
        ])
        .filter(pl.col("count") >= 12)
        .sort("timestamp_ms")
        .with_columns([
            pl.col("cs_disp_72h").rolling_mean(24).alias("cs_disp_ma24")
        ])
        .with_columns([
            (pl.col("cs_disp_72h") - pl.col("cs_disp_ma24")).alias("delta_disp_24h")
        ])
    )
    df = df.join(df_disp.select(["timestamp_ms", "cs_disp_72h", "delta_disp_24h"]), on="timestamp_ms", how="left")

    out_file = FEATURE_DIR / "pit_panel_1h_with_funding.parquet"
    df.write_parquet(out_file)

    context.log.info(f"Materialized HL-3A Apex Feature Lake: {df.height:,} rows -> {out_file}")
    return Output(
        str(out_file),
        metadata={
            "total_rows": df.height,
            "columns": len(df.columns),
            "latest_bar": str(df["timestamp_ms"].max()),
        }
    )
