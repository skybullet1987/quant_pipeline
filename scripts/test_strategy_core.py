from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import polars as pl
from pipeline.research.regime_policy import evaluate_regime_policy
from pipeline.research.portfolio_allocator import ShrunkAlphaAllocator
from pipeline.research.expectancy_engine import RawMarketState, build_trade_intent

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def test_core_flow():
    df = (
        pl.read_parquet("/tmp/lake/features/pit_panel_4h.parquet")
        .unique(subset=["symbol", "bucket_timestamp_utc"])
        .sort("bucket_timestamp_utc")
    )

    # Pick top liquid basket from universe
    symbols = ["BTC", "ETH", "SOL", "AVAX", "LINK", "DOGE", "SUI", "NEAR"]
    sub_df = df.filter(pl.col("symbol").is_in(symbols))
    
    # Pivot returns matrix for Ledoit-Wolf Covariance
    pivoted = sub_df.pivot(index="bucket_timestamp_utc", on="symbol", values="log_ret").fill_null(0.0)
    returns_matrix = pivoted.select(symbols).to_numpy()[-360:] # Last 60 days (360 bars)

    logger.info("Fitted return matrix shape: %s", returns_matrix.shape)

    # Mock ensemble alpha signals (raw basis point predictions)
    raw_alphas = np.array([0.0035, 0.0028, 0.0062, -0.0041, 0.0015, -0.0055, 0.0078, 0.0010])

    # 1. Evaluate Portfolio Regime State (from BTC)
    policy = evaluate_regime_policy(
        p_hazard=0.004,
        p_chop=0.0001,
        p_trend=0.998,
        p_expansion=0.0019,
        directional_impulse=1.2,
    )
    logger.info("Active Regime: %s | Multiplier: %.2fx", policy.regime_label, policy.sizing_multiplier)

    # 2. Allocate with Ledoit-Wolf Covariance Shrinkage
    allocator = ShrunkAlphaAllocator(base_kelly=0.25, gross_exposure_cap=1.50)
    allocation = allocator.allocate(
        symbols=symbols,
        raw_alphas=raw_alphas,
        asset_returns_matrix=returns_matrix,
        m_regime=policy.sizing_multiplier,
    )

    logger.info("Gross Portfolio Leverage: %.2fx | Shrinkage Intensity: %.3f", allocation.gross_leverage, allocation.shrinkage_intensity)

    # 3. Build Immutable TradeIntents
    total_equity = 100_000.0 # $100k account equity
    intents = []

    for sym in symbols:
        weight = allocation.weights[sym]
        mock_market = RawMarketState(
            symbol=sym,
            t_event_ns=0,
            t_recv_ns=0,
            bid_price=100.0,
            ask_price=100.05,
            mid_price=100.025,
            oracle_price=100.025,
            funding_rate_1h=0.000012, # 1.2 bps hourly funding
            funding_missing=False,
        )
        intent = build_trade_intent(mock_market, target_weight=weight, total_portfolio_equity=total_equity)
        intents.append(intent)

    print("\n" + "=" * 80)
    print(f"{'SYMBOL':<8} | {'ACTION':<6} | {'WEIGHT':<8} | {'TARGET':<8} | {'STOP':<8} | {'EV RETURN':<10} | {'EV DOLLAR':<10}")
    print("-" * 80)
    for intent in intents:
        print(f"{intent.symbol:<8} | {intent.action:<6} | {intent.target_weight:7.2%} | ${intent.target_price:<7.2f} | ${intent.stop_price:<7.2f} | {intent.ev_return:+8.3%} | ${intent.ev_dollar:+8.2f}")
    print("=" * 80)


if __name__ == "__main__":
    test_core_flow()
