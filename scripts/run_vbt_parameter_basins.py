"""
Phase 5: Production-Aligned VectorBT Parameter Basins.
Implements BTC Regime Directional Gating, 24H Rebalance Cycles, and Top-K Portfolio Concentration.
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd
import polars as pl
from numba import njit
import vectorbt as vbt

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


@njit(fastmath=True)
def generate_regime_gated_weights_numba(
    mom_ranks: np.ndarray,      # (T, N) cross-sectional percentiles (0 to 1)
    valid_mask: np.ndarray,     # (T, N) liquidity and listing validity
    btc_regime: np.ndarray,     # (T,) 1 = Bull, -1 = Bear, 0 = Chop/Defensive
    top_k: int = 10,
    rebalance_freq_bars: int = 6, # 24 hours (6 x 4H bars)
) -> np.ndarray:
    """Generates discrete top-k long/short target weights with periodic rebalancing and regime gates."""
    T, N = mom_ranks.shape
    weights = np.zeros((T, N), dtype=np.float64)
    current_weights = np.zeros(N, dtype=np.float64)

    for t in range(T):
        if t % rebalance_freq_bars == 0:
            current_weights = np.zeros(N, dtype=np.float64)
            regime = btc_regime[t]

            # Collect valid candidates
            valid_indices = []
            for j in range(N):
                if valid_mask[t, j] and not np.isnan(mom_ranks[t, j]):
                    valid_indices.append(j)

            if len(valid_indices) >= top_k * 2:
                # Rank valid universe
                ranks = np.array([mom_ranks[t, j] for j in valid_indices])
                sorted_order = np.argsort(ranks)
                
                top_long_idx = [valid_indices[i] for i in sorted_order[-top_k:]]
                bottom_short_idx = [valid_indices[i] for i in sorted_order[:top_k]]

                w_per_asset = 1.0 / top_k

                if regime == 1:  # Bull Market: Long-Only Top-K (1.0x Gross)
                    for j in top_long_idx:
                        current_weights[j] = w_per_asset
                elif regime == -1:  # Bear Market: Short-Only Bottom-K (0.5x Defensive Gross)
                    for j in bottom_short_idx:
                        current_weights[j] = -0.5 * w_per_asset
                else:  # Chop / Shock: Neutral Market (0.5x Long Top-K, 0.5x Short Bottom-K)
                    for j in top_long_idx:
                        current_weights[j] = 0.5 * w_per_asset
                    for j in bottom_short_idx:
                        current_weights[j] = -0.5 * w_per_asset

        weights[t, :] = current_weights

    return weights


def run_parameter_basins():
    feature_path = "/tmp/lake/features/pit_panel_4h.parquet"
    if not os.path.exists(feature_path):
        raise FileNotFoundError(f"Feature dataset not found: {feature_path}")

    logger.info("Loading 4H Point-in-Time panel...")
    df = (
        pl.read_parquet(feature_path)
        .unique(subset=["symbol", "bucket_timestamp_utc"])
        .sort("bucket_timestamp_utc")
    )

    close_df = (
        df.pivot(index="bucket_timestamp_utc", on="symbol", values="close")
        .sort("bucket_timestamp_utc")
        .to_pandas()
        .set_index("bucket_timestamp_utc")
        .ffill()
    )

    # 1. Multi-Horizon Intermediate Momentum Factor (72H + 168H)
    ret_72h = close_df.pct_change(18)
    ret_168h = close_df.pct_change(42)
    composite_mom = (0.50 * ret_72h + 0.50 * ret_168h).fillna(0.0)
    cs_ranks = composite_mom.rank(axis=1, pct=True)

    # 2. Derive BTC Macro Regime (Trend / Filter)
    btc_close = close_df["BTC"]
    btc_sma_50d = btc_close.rolling(300).mean()   # 50 days (300 x 4H bars)
    btc_sma_200d = btc_close.rolling(1200).mean() # 200 days (1200 x 4H bars)

    btc_regime_arr = np.zeros(len(btc_close), dtype=np.int64)
    bull_mask = (btc_close > btc_sma_50d) & (btc_sma_50d > btc_sma_200d)
    bear_mask = (btc_close < btc_sma_50d) & (btc_sma_50d < btc_sma_200d)

    btc_regime_arr[bull_mask] = 1
    btc_regime_arr[bear_mask] = -1

    # 3. Minimum Liquidity Filter (Assets with >= 30 days history)
    valid_mask = (~close_df.isna() & (close_df.rolling(180).count() >= 180)).to_numpy()
    mom_matrix = cs_ranks.to_numpy()

    # Rebalancing frequency configurations to sweep: 12H, 24H, 48H
    sweep_configs = [
        {"name": "Top-10 Basket (12H Rebalance)", "freq_bars": 3, "k": 10},
        {"name": "Top-10 Basket (24H Rebalance)", "freq_bars": 6, "k": 10},
        {"name": "Top-15 Basket (24H Rebalance)", "freq_bars": 6, "k": 15},
        {"name": "Top-10 Basket (48H Rebalance)", "freq_bars": 12, "k": 10},
    ]

    fees = 0.00035  # 3.5 bps taker buffer

    print("\n" + "=" * 105)
    print(f"{'STRATEGY CONFIGURATION':<35} | {'GROSS SHARPE':<12} | {'NET SHARPE':<10} | {'MAX DD':<10} | {'TOTAL RETURN':<12} | {'FEES PAID':<10}")
    print("-" * 105)

    for cfg in sweep_configs:
        raw_weights_arr = generate_regime_gated_weights_numba(
            mom_ranks=mom_matrix,
            valid_mask=valid_mask,
            btc_regime=btc_regime_arr,
            top_k=cfg["k"],
            rebalance_freq_bars=cfg["freq_bars"],
        )

        raw_weights = pd.DataFrame(raw_weights_arr, index=cs_ranks.index, columns=cs_ranks.columns)
        
        # Enforce strict 1-bar execution lag
        exec_weights = raw_weights.shift(1).fillna(0.0)

        # Net Portfolio Simulation
        pf_net = vbt.Portfolio.from_orders(
            close=close_df,
            size=exec_weights,
            size_type="targetpercent",
            freq="4h",
            fees=fees,
            init_cash=100_000.0,
            cash_sharing=True,
            group_by=True,
            call_seq="auto",
        )

        # Gross Portfolio Simulation
        pf_gross = vbt.Portfolio.from_orders(
            close=close_df,
            size=exec_weights,
            size_type="targetpercent",
            freq="4h",
            fees=0.0,
            init_cash=100_000.0,
            cash_sharing=True,
            group_by=True,
            call_seq="auto",
        )

        gross_sharpe = float(np.squeeze(pf_gross.sharpe_ratio()))
        net_sharpe = float(np.squeeze(pf_net.sharpe_ratio()))
        max_dd = float(np.squeeze(pf_net.max_drawdown()))
        total_ret = float(np.squeeze(pf_net.total_return()))
        total_fees = float(np.squeeze(pf_gross.total_profit() - pf_net.total_profit()))

        print(
            f"{cfg['name']:<35} | "
            f"{gross_sharpe:12.2f} | "
            f"{net_sharpe:10.2f} | "
            f"{max_dd:9.2%} | "
            f"{total_ret:11.2%} | "
            f"${total_fees:9,.0f}"
        )
    print("=" * 105)


if __name__ == "__main__":
    run_parameter_basins()
