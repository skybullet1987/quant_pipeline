import os
import json
import time
import math
import pickle
from pathlib import Path
from datetime import datetime, timezone
import polars as pl
import pandas as pd
import numpy as np
from dagster import (
    asset,
    define_asset_job,
    ScheduleDefinition,
    Definitions,
    AssetExecutionContext,
    Output
)
from hyperliquid.info import Info
from hyperliquid.utils import constants

LAKE_DIR = Path.home() / "quant_pipeline" / "data" / "lake"
RAW_LAKE_PATH = LAKE_DIR / "raw_candles_1h.parquet"
FEATURE_LAKE_PATH = LAKE_DIR / "features" / "pit_panel_1h_with_funding.parquet"
STORAGE_DIR = Path.home() / "dagster_home" / "storage"

LAKE_DIR.mkdir(parents=True, exist_ok=True)
FEATURE_LAKE_PATH.parent.mkdir(parents=True, exist_ok=True)
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def compute_yang_zhang_volatility(df: pl.DataFrame, window: int = 72) -> pl.DataFrame:
    """Computes unbiased multi-period Yang-Zhang realized volatility over 72 1H bars."""
    k_yz = 0.34 / (1.34 + (window + 1.0) / (window - 1.0))
    return (
        df.sort(["symbol", "timestamp_ms"])
        .with_columns([
            (pl.col("high") / pl.col("open")).log().over("symbol").alias("u"),
            (pl.col("low") / pl.col("open")).log().over("symbol").alias("d"),
            (pl.col("close") / pl.col("open")).log().over("symbol").alias("c"),
            (pl.col("open") / pl.col("close").shift(1)).log().over("symbol").alias("o")
        ])
        .with_columns([
            (pl.col("u") * (pl.col("u") - pl.col("c")) + pl.col("d") * (pl.col("d") - pl.col("c"))).alias("rs_var_inst"),
            pl.col("o").rolling_var(window).over("symbol").alias("sigma_oj_sq"),
            pl.col("c").rolling_var(window).over("symbol").alias("sigma_cc_sq")
        ])
        .with_columns([
            pl.col("rs_var_inst").rolling_mean(window).over("symbol").alias("sigma_rs_sq")
        ])
        .with_columns([
            (
                pl.col("sigma_oj_sq") +
                k_yz * pl.col("sigma_cc_sq") +
                (1.0 - k_yz) * pl.col("sigma_rs_sq")
            ).clip(lower_bound=1e-8).sqrt().alias("vol_yang_zhang")
        ])
        .drop(["u", "d", "c", "o", "rs_var_inst", "sigma_oj_sq", "sigma_cc_sq", "sigma_rs_sq"])
    )


@asset(group_name="data_fabric", compute_kind="hyperliquid_api")
def dynamic_universe_lake(context: AssetExecutionContext) -> Output[str]:
    """Ingests 1H OHLCV candles and live funding rates for all active perpetuals."""
    info = Info(constants.MAINNET_API_URL, skip_ws=True)
    meta, asset_ctxs = info.meta_and_asset_ctxs()

    funding_map = {}
    candidates = []
    for idx, u in enumerate(meta["universe"]):
        if u.get("isDelisted", False):
            continue
        ctx = asset_ctxs[idx]
        name = u["name"]
        funding_rate = float(ctx.get("funding", 0.0))
        funding_map[name] = funding_rate
        candidates.append({
            "name": name,
            "dayNtlVlm": float(ctx.get("dayNtlVlm", 0.0)),
            "markPx": float(ctx.get("markPx") or ctx.get("midPx") or 0.0),
            "funding": funding_rate,
        })

    candidates.sort(key=lambda x: x["dayNtlVlm"], reverse=True)
    target_symbols = [c["name"] for c in candidates[:100]]
    if "BTC" not in target_symbols:
        target_symbols.append("BTC")

    end_ms = int(time.time() * 1000)
    # Rolling 120-hour buffer provides sufficient lookback for 72H rolling features
    lookback_ms = end_ms - (120 * 3600 * 1000)

    records = []
    for sym in target_symbols:
        try:
            raw = info.candles_snapshot(sym, "1h", lookback_ms, end_ms)
            if raw:
                f_rate = funding_map.get(sym, 0.0)
                current_hour_ms = (int(time.time()) // 3600) * 3600 * 1000
                for c in raw:
                    if int(c["t"]) >= current_hour_ms:
                        continue
                    records.append({
                        "symbol": sym,
                        "timestamp_ms": int(c["t"]),
                        "open": float(c["o"]),
                        "high": float(c["h"]),
                        "low": float(c["l"]),
                        "close": float(c["c"]),
                        "volume": float(c["v"]),
                        "dollar_volume_1h": float(c["v"]) * float(c["c"]),
                        "funding_rate": f_rate
                    })
            time.sleep(0.02)  # Rate pacing
        except Exception as e:
            context.log.warning(f"1H candle fetch skipped for {sym}: {e}")

    df_new = pl.from_dicts(records).unique(subset=["symbol", "timestamp_ms"]).sort(["symbol", "timestamp_ms"])
    df_new.write_parquet(RAW_LAKE_PATH)

    return Output(
        str(RAW_LAKE_PATH),
        metadata={
            "total_bars": df_new.height,
            "active_symbols": len(target_symbols),
            "latest_bar_ms": int(df_new["timestamp_ms"].max())
        }
    )


@asset(deps=[dynamic_universe_lake], group_name="feature_fabric", compute_kind="polars")
def pit_feature_panel(context: AssetExecutionContext) -> Output[str]:
    """Computes HL-3A Apex features: 72H Yang-Zhang vol, Tri-Alpha, and Delta Dispersion."""
    df = pl.read_parquet(RAW_LAKE_PATH).sort(["symbol", "timestamp_ms"])

    # 1. Multi-horizon returns
    df = df.with_columns([
        (pl.col("close") / pl.col("close").shift(1).over("symbol") - 1.0).alias("ret_1h"),
        (pl.col("close") / pl.col("close").shift(4).over("symbol") - 1.0).alias("ret_4h"),
        (pl.col("close") / pl.col("close").shift(12).over("symbol") - 1.0).alias("ret_12h"),
        (pl.col("close") / pl.col("close").shift(24).over("symbol") - 1.0).alias("ret_24h"),
        (pl.col("close") / pl.col("close").shift(72).over("symbol") - 1.0).alias("ret_72h")
    ])

    # 2. 72H Yang-Zhang Volatility
    df = compute_yang_zhang_volatility(df, window=72)

    # 3. BTC Rolling Beta & Spillover
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

    # 4. Tri-Alpha Formulations
    df = df.with_columns([
        (
            -0.35 * ((pl.col("ret_4h") - pl.col("beta_btc") * pl.col("btc_ret_4h")) / (pl.col("vol_yang_zhang") + 1e-5))
            -0.25 * ((pl.col("ret_12h") - pl.col("beta_btc") * pl.col("btc_ret_12h")) / (pl.col("vol_yang_zhang") + 1e-5))
            +0.40 * ((pl.col("ret_72h") - pl.col("beta_btc") * pl.col("btc_ret_72h")) / (pl.col("vol_yang_zhang") + 1e-5))
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

    # 5. EWMA Temporal Smoothing
    df = df.sort(["symbol", "timestamp_ms"]).with_columns([
        pl.col("raw_a0").ewm_mean(span=6).over("symbol").alias("a0_smooth"),
        pl.col("raw_a1").ewm_mean(span=2).over("symbol").alias("a1_smooth"),
        pl.col("raw_a2").ewm_mean(span=4).over("symbol").alias("a2_smooth")
    ])

    # 6. Cross-Sectional Standardization & Master Tri-Alpha
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

    df.write_parquet(FEATURE_LAKE_PATH)
    context.log.info(f"HL-3A Apex Feature Lake materialized: {df.height:,} rows -> {FEATURE_LAKE_PATH}")

    return Output(
        str(FEATURE_LAKE_PATH),
        metadata={
            "feature_matrix_rows": df.height,
            "latest_candle_ms": int(df["timestamp_ms"].max())
        }
    )


@asset(deps=[pit_feature_panel], group_name="cloud_warehouse", compute_kind="bigquery")
def cloud_warehouse_sync(context: AssetExecutionContext) -> Output[dict]:
    """Asynchronously archives feature updates to BigQuery (graceful fallback)."""
    try:
        from src.data.bq_exporter import BigQueryWarehouseSync
        syncer = BigQueryWarehouseSync(dataset_id="market_data")
        feat_rows = syncer.sync_feature_panel()
        result = {"status": "synced", "features_uploaded": feat_rows}
    except Exception as e:
        context.log.info(f"BigQuery export bypassed or deferred: {e}")
        result = {"status": "deferred", "reason": str(e)}

    return Output(result, metadata=result)


@asset(group_name="macro_feature_fabric", compute_kind="hyperliquid_polars")
def continuous_4h_pit_feature_panel(context: AssetExecutionContext) -> Output[str]:
    """Ingests 4H OHLCV candles and materializes the 4H production PIT feature panel."""
    from scripts.sync_4h_data_lake import sync_4h_candles, RAW_4H_LAKE, PIT_4H_LAKE
    sync_4h_candles()
    context.log.info(f"4H data lake and feature panel synchronized to {RAW_4H_LAKE} and {PIT_4H_LAKE}")

    return Output(
        str(RAW_4H_LAKE),
        metadata={"raw_path": str(RAW_4H_LAKE), "pit_path": str(PIT_4H_LAKE), "synced_at": datetime.now(timezone.utc).isoformat()}
    )


quant_1h_pipeline_job = define_asset_job(
    name="quant_1h_pipeline_job",
    selection=["dynamic_universe_lake", "pit_feature_panel", "cloud_warehouse_sync"]
)

quant_4h_pipeline_job = define_asset_job(
    name="quant_4h_pipeline_job",
    selection=["continuous_4h_pit_feature_panel"]
)

defs = Definitions(
    assets=[dynamic_universe_lake, pit_feature_panel, cloud_warehouse_sync, continuous_4h_pit_feature_panel],
    jobs=[quant_1h_pipeline_job, quant_4h_pipeline_job],
    schedules=[
        ScheduleDefinition(
            name="hyperliquid_1h_cron_schedule",
            job=quant_1h_pipeline_job,
            cron_schedule="2 * * * *"
        ),
        ScheduleDefinition(
            name="hyperliquid_4h_cron_schedule",
            job=quant_4h_pipeline_job,
            cron_schedule="5 */4 * * *"
        )
    ]
)

