import os
import json
import time
from pathlib import Path
import numpy as np
import polars as pl
from catboost import CatBoost, Pool
from dagster import (
    AssetExecutionContext,
    Definitions,
    asset,
    define_asset_job,
    ScheduleDefinition
)
from hyperliquid.info import Info
from hyperliquid.utils import constants

LAKE_DIR = Path.home() / "quant_pipeline" / "data" / "lake"
MODEL_DIR = Path.home() / "quant_pipeline" / "data" / "models"
LAKE_DIR.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)
(LAKE_DIR / "features").mkdir(parents=True, exist_ok=True)
(LAKE_DIR / "telemetry").mkdir(parents=True, exist_ok=True)

def compute_yang_zhang_volatility(df: pl.DataFrame, window: int = 42) -> pl.DataFrame:
    """Computes unbiased multi-period Yang-Zhang realized volatility."""
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

@asset
def raw_top50_4h_candles(context: AssetExecutionContext) -> str:
    info = Info(constants.MAINNET_API_URL, skip_ws=True)
    end_ms = int(time.time() * 1000)
    start_ms = end_ms - (365 * 24 * 3600 * 1000)
    
    meta, asset_ctxs = info.meta_and_asset_ctxs()
    universe = meta["universe"]
    
    liquid_candidates = []
    for i, asset_info in enumerate(universe):
        if asset_info.get("isDelisted", False):
            continue
        sym = asset_info["name"]
        ctx = asset_ctxs[i]
        day_volume_usd = float(ctx.get("dayNtlVlm", 0.0))
        open_interest_usd = float(ctx.get("openInterest", 0.0)) * float(ctx.get("oraclePx", 0.0))
        
        liquid_candidates.append({
            "symbol": sym,
            "day_volume_usd": day_volume_usd,
            "open_interest_usd": open_interest_usd
        })
        
    liquid_candidates.sort(key=lambda x: x["day_volume_usd"], reverse=True)
    target_symbols = [c["symbol"] for c in liquid_candidates[:50]]
    if "BTC" not in target_symbols:
        target_symbols[-1] = "BTC"
        
    records = []
    for sym in target_symbols:
        try:
            raw = info.candles_snapshot(sym, "4h", start_ms, end_ms)
            if raw:
                for c in raw:
                    records.append({
                        "symbol": sym,
                        "timestamp_ms": int(c["t"]),
                        "open": float(c["o"]),
                        "high": float(c["h"]),
                        "low": float(c["l"]),
                        "close": float(c["c"]),
                        "volume": float(c["v"]),
                        "oracle_px": float(c.get("oraclePx", c["c"]))
                    })
        except Exception as e:
            context.log.warning(f"Error fetching candles for {sym}: {e}")
            
    df = pl.from_dicts(records).unique(subset=["symbol", "timestamp_ms"]).sort(["symbol", "timestamp_ms"])
    out_path = LAKE_DIR / "raw_candles_4h.parquet"
    df.write_parquet(out_path)
    context.log.info(f"Materialized {len(df)} candles across {len(target_symbols)} assets.")
    return str(out_path)

@asset(deps=[raw_top50_4h_candles])
def pit_feature_panel(context: AssetExecutionContext) -> str:
    df = pl.read_parquet(LAKE_DIR / "raw_candles_4h.parquet").sort(["symbol", "timestamp_ms"])
    
    # 1. Base return features & ATR
    df = df.with_columns([
        (pl.col("close") / pl.col("close").shift(1)).log().over("symbol").alias("ret_4h"),
        (pl.col("close") / pl.col("close").shift(6)).log().over("symbol").alias("ret_24h"),
        (pl.col("close") / pl.col("close").shift(18)).log().over("symbol").alias("ret_72h"),
        (pl.col("close") / pl.col("close").shift(42)).log().over("symbol").alias("ret_168h"),
        (pl.max_horizontal(
            pl.col("high") - pl.col("low"),
            (pl.col("high") - pl.col("close").shift(1).over("symbol")).abs(),
            (pl.col("low") - pl.col("close").shift(1).over("symbol")).abs()
        )).rolling_mean(14).over("symbol").alias("atr_14")
    ])
    
    # 2. Yang-Zhang Realized Volatility
    df = compute_yang_zhang_volatility(df, window=42)
    
    # 3. Microstructure Ratios & Spreads
    df = df.with_columns([
        (pl.col("ret_4h").rolling_std(6).over("symbol") / (pl.col("ret_4h").rolling_std(42).over("symbol") + 1e-8)).alias("vol_ratio_24_168"),
        ((pl.col("volume") - pl.col("volume").rolling_mean(18).over("symbol")) / (pl.col("volume").rolling_std(18).over("symbol") + 1e-8)).alias("volume_zscore_72h"),
        (pl.col("close") / (pl.col("oracle_px") + 1e-8)).log().alias("basis_spread")
    ])
    
    # 4. BTC Spillover & Rolling Beta
    btc_shocks = (
        df.filter(pl.col("symbol") == "BTC")
        .select([
            pl.col("timestamp_ms"),
            (pl.col("close") / pl.col("close").shift(1)).log().alias("btc_ret_4h"),
            (pl.col("close") / pl.col("close").shift(6)).log().alias("btc_ret_24h"),
            (pl.col("close").shift(-18) / pl.col("close")).log().alias("btc_fwd_ret_72h")
        ])
        .with_columns([
            (pl.col("btc_ret_4h") * 0.60 + pl.col("btc_ret_24h").shift(1) * 0.40).alias("btc_spillover_signal")
        ])
    )
    df = df.join(btc_shocks, on="timestamp_ms", how="left")
    
    w = 42
    cov_btc_expr = (
        (
            (pl.col("ret_4h") * pl.col("btc_ret_4h")).rolling_mean(w).over("symbol")
            - (pl.col("ret_4h").rolling_mean(w).over("symbol") * pl.col("btc_ret_4h").rolling_mean(w).over("symbol"))
        ) * (w / (w - 1.0))
    )
    var_btc_expr = pl.col("btc_ret_4h").rolling_var(window_size=w).over("symbol")
    
    df = df.with_columns([
        (cov_btc_expr / (var_btc_expr + 1e-8)).alias("beta_btc")
    ])
    df = df.with_columns([
        (pl.col("btc_spillover_signal") * pl.col("beta_btc")).alias("spillover_alpha"),
        (pl.col("ret_72h").rank().over("timestamp_ms") / pl.col("symbol").count().over("timestamp_ms")).alias("cs_rank_72h")
    ])
    
    # 5. Clean Beta-Residualized Continuous Target Label
    df = df.with_columns([
        (pl.col("close").shift(-18).over("symbol") / pl.col("close")).log().alias("fwd_ret_72h")
    ]).with_columns([
        (
            (pl.col("fwd_ret_72h") - pl.col("beta_btc") * pl.col("btc_fwd_ret_72h"))
            / (pl.col("vol_yang_zhang") * np.sqrt(18) + 1e-8)
        ).alias("target_residual_alpha_72h"),
        pl.col("timestamp_ms").rank("dense").cast(pl.UInt32).alias("group_id")
    ]).drop_nulls()
    
    out_path = LAKE_DIR / "features" / "pit_panel_4h.parquet"
    df.write_parquet(out_path)
    context.log.info(f"Materialized Clean Continuous Feature Panel: {out_path}")
    return str(out_path)

@asset(deps=[pit_feature_panel])
def catboost_production_model(context: AssetExecutionContext) -> str:
    df = pl.read_parquet(LAKE_DIR / "features" / "pit_panel_4h.parquet").sort(["group_id", "symbol"])
    
    features = [
        "ret_4h", "ret_24h", "ret_72h", "ret_168h",
        "vol_yang_zhang", "vol_ratio_24_168", "volume_zscore_72h",
        "basis_spread", "spillover_alpha", "cs_rank_72h"
    ]
    
    unique_groups = df.select("group_id").unique().to_series().to_list()
    split_idx = int(len(unique_groups) * 0.85)
    train_groups = set(unique_groups[:split_idx])
    
    train_df = df.filter(pl.col("group_id").is_in(train_groups))
    val_df = df.filter(~pl.col("group_id").is_in(train_groups))
    
    train_pool = Pool(
        data=train_df.select(features).to_pandas(),
        label=train_df.select("target_residual_alpha_72h").to_pandas().values.ravel(),
        group_id=train_df.select("group_id").to_pandas().values.ravel()
    )
    
    val_pool = Pool(
        data=val_df.select(features).to_pandas(),
        label=val_df.select("target_residual_alpha_72h").to_pandas().values.ravel(),
        group_id=val_df.select("group_id").to_pandas().values.ravel()
    )
    
    model = CatBoost({
        "loss_function": "YetiRank",
        "eval_metric": "NDCG:top=3",
        "iterations": 600,
        "learning_rate": 0.04,
        "depth": 5,
        "l2_leaf_reg": 3.0,
        "thread_count": -1,
        "verbose": 100
    })
    
    model.fit(train_pool, eval_set=val_pool, use_best_model=True)
    
    latest_bar = df.filter(pl.col("timestamp_ms") == df.select(pl.max("timestamp_ms")).to_series()[0])
    atr_dict = {row["symbol"]: float(row["atr_14"]) for row in latest_bar.iter_rows(named=True)}
    yz_dict = {row["symbol"]: float(row["vol_yang_zhang"]) for row in latest_bar.iter_rows(named=True)}
    
    model_path = MODEL_DIR / "catboost_tail_alpha_v1.cbm"
    meta_path = MODEL_DIR / "model_metadata.json"
    
    model.save_model(str(model_path))
    with open(meta_path, "w") as f:
        json.dump({
            "features": features,
            "trained_at_ms": int(time.time() * 1000),
            "best_iteration": model.get_best_iteration(),
            "best_score": model.get_best_score().get("validation", {}).get("NDCG:top=3", 0.0),
            "latest_atr": atr_dict,
            "latest_yz_vol": yz_dict
        }, f, indent=2)
        
    context.log.info(f"Saved YetiRank Model -> {model_path}")
    return str(model_path)

@asset
def live_portfolio_telemetry(context: AssetExecutionContext) -> str:
    info = Info(constants.TESTNET_API_URL, skip_ws=True)
    addr = os.getenv("HYPERLIQUID_ACCOUNT_ADDRESS", "0x9703B71686219D34869e8FB89a93263f9e0d50A5")
    user_state = info.user_state(addr)
    
    records = []
    ts = int(time.time() * 1000)
    for p in user_state.get("assetPositions", []):
        pos = p["position"]
        records.append({
            "timestamp_ms": ts,
            "symbol": pos["coin"],
            "size": float(pos["szi"]),
            "entry_px": float(pos["entryPx"]) if pos["entryPx"] else 0.0,
            "unrealized_pnl": float(pos["unrealizedPnl"]),
            "margin_used": float(pos["marginUsed"]),
            "leverage": float(pos["leverage"]["value"]) if "value" in pos["leverage"] else 1.0
        })
        
    df = pl.from_dicts(records) if records else pl.DataFrame()
    out_path = LAKE_DIR / "telemetry" / "live_telemetry.parquet"
    df.write_parquet(out_path)
    return str(out_path)

defs = Definitions(
    assets=[raw_top50_4h_candles, pit_feature_panel, catboost_production_model, live_portfolio_telemetry],
    jobs=[
        define_asset_job("pipeline_retrain_job", selection=["raw_top50_4h_candles", "pit_feature_panel", "catboost_production_model"]),
        define_asset_job("hourly_telemetry_job", selection=["live_portfolio_telemetry"])
    ],
    schedules=[
        ScheduleDefinition(name="daily_retrain_schedule", job_name="pipeline_retrain_job", cron_schedule="0 0 * * *"),
        ScheduleDefinition(name="hourly_telemetry_schedule", job_name="hourly_telemetry_job", cron_schedule="0 * * * *")
    ]
)
