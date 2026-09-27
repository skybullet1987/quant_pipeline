"""
Layer 1: Full-Universe Dynamic Ingestion and DQG Validation Assets.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta
import polars as pl
from dagster import Output, asset

from pipeline.catalog.indexer import NautilusCatalogIndexer
from pipeline.ingestion.binance_universe_loader import BinanceUniverseLoader
from pipeline.validation.dqg import DataQualityGate


@asset(
    group_name="data_fabric",
    description="Dynamically pulls all available Hyperliquid coins from Binance archives concurrently."
)
def raw_binance_trades(context) -> Output[list[str]]:
    loader = BinanceUniverseLoader()
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    date_str = yesterday.strftime("%Y-%m-%d")
    
    saved_paths = loader.bulk_ingest_universe(
        date_str=date_str,
        output_dir="/tmp/lake/raw/binance/trades",
        max_workers=8,
        min_daily_volume_usd=0.0
    )

    if not saved_paths:
        fallback_date = (yesterday - timedelta(days=1)).strftime("%Y-%m-%d")
        context.log.warning(f"Archive not ready for {date_str}, falling back to {fallback_date}")
        saved_paths = loader.bulk_ingest_universe(
            date_str=fallback_date,
            output_dir="/tmp/lake/raw/binance/trades",
            max_workers=8
        )

    return Output(
        value=saved_paths,
        metadata={"total_ingested_symbols": len(saved_paths)}
    )


@asset(
    group_name="data_fabric",
    description="Runs Data Quality Gate (DQG) validation across all full-universe trade streams."
)
def dqg_validated_trades(context, raw_binance_trades: list[str]) -> Output[list[str]]:
    dqg = DataQualityGate()
    clean_paths: list[str] = []
    total_valid_ticks = 0

    for raw_path in raw_binance_trades:
        df_raw = pl.read_parquet(raw_path)
        if df_raw.is_empty():
            continue
            
        df_clean, audit = dqg.audit_and_clean_trade_stream(df_raw)
        
        clean_path = f"/tmp/lake/clean/binance/trades/{os.path.basename(raw_path)}"
        os.makedirs(os.path.dirname(clean_path), exist_ok=True)
        df_clean.write_parquet(clean_path, compression="zstd")
        clean_paths.append(clean_path)
        total_valid_ticks += df_clean.height

    context.log.info(f"DQG complete across {len(clean_paths)} assets ({total_valid_ticks:,} valid ticks).")

    return Output(
        value=clean_paths,
        metadata={"assets_validated": len(clean_paths), "total_valid_ticks": total_valid_ticks}
    )


@asset(
    group_name="data_fabric",
    description="Indexes multi-asset clean trade streams into NautilusTrader DataCatalog."
)
def nautilus_catalog_index(context, dqg_validated_trades: list[str]) -> Output[int]:
    indexer = NautilusCatalogIndexer()
    total_indexed = 0
    
    for clean_path in dqg_validated_trades:
        count = indexer.index_trade_parquet(clean_path, venue_name="BINANCE")
        total_indexed += count

    return Output(value=total_indexed, metadata={"total_indexed_ticks": total_indexed})
