"""
Phase 5: Refined Full-Universe Architecture Backtest.
24H Forward Demeaned Targets, Cross-Sectional Z-Scored Ensemble Alphas, 
Ledoit-Wolf Covariance Inversion, and Rebalance Deadbands.
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
from sklearn.linear_model import RidgeCV
import lightgbm as lgb
from catboost import CatBoostRegressor
from sklearn.covariance import LedoitWolf
import vectorbt as vbt

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def generate_full_universe_alphas(df: pl.DataFrame) -> pd.DataFrame:
    """Trains expanding-window tri-model ensemble on 24H forward market-demeaned targets."""
    logger.info("Engineering multi-horizon features and 24H forward excess return targets...")
    
    # 1. Feature & Target Formulation (24H forward = 6 bars)
    enriched_df = (
        df.sort(["symbol", "bucket_timestamp_utc"])
        .with_columns([
            pl.col("close").pct_change(6).over("symbol").alias("ret_24h"),
            pl.col("close").pct_change(18).over("symbol").alias("ret_72h"),
            pl.col("close").pct_change(42).over("symbol").alias("ret_168h"),
            (pl.col("close").shift(-6).over("symbol") / pl.col("close") - 1.0).alias("fwd_ret_24h"),
        ])
    )

    # Cross-Sectional Market Demeaning
    market_mean_fwd = (
        enriched_df.group_by("bucket_timestamp_utc")
        .agg(pl.col("fwd_ret_24h").mean().alias("mkt_mean_fwd_24h"))
    )

    pdf = (
        enriched_df.join(market_mean_fwd, on="bucket_timestamp_utc")
        .with_columns([
            (pl.col("fwd_ret_24h") - pl.col("mkt_mean_fwd_24h")).alias("target_excess_24h")
        ])
        .to_pandas()
    )

    feature_cols = [
        "log_ret",
        "ret_24h",
        "ret_72h",
        "ret_168h",
        "rolling_24h_volatility",
        "cs_momentum_4h_percentile",
        "cs_liquidity_percentile",
    ]

    pdf = pdf.dropna(subset=feature_cols + ["target_excess_24h"])
    unique_times = pd.Series(pdf["bucket_timestamp_utc"].unique()).sort_values().reset_index(drop=True)

    n_train_bars = 2160   # 1 year warm-up (2160 x 4H bars)
    retrain_step = 720   # Retrain every 120 days

    pdf["alpha_pred"] = 0.0
    logger.info("Training Expanding-Window Ensemble across %d timestamps...", len(unique_times))

    fold = 0
    for start_idx in range(n_train_bars, len(unique_times), retrain_step):
        fold += 1
        end_idx = min(start_idx + retrain_step, len(unique_times))
        
        train_t_set = set(unique_times.iloc[:start_idx])
        test_t_set = set(unique_times.iloc[start_idx:end_idx])

        train_mask = pdf["bucket_timestamp_utc"].isin(train_t_set)
        test_mask = pdf["bucket_timestamp_utc"].isin(test_t_set)

        X_tr = pdf.loc[train_mask, feature_cols].values
        y_tr = pdf.loc[train_mask, "target_excess_24h"].values
        X_te = pdf.loc[test_mask, feature_cols].values

        if len(X_te) == 0 or len(X_tr) == 0:
            continue

        ridge = RidgeCV(alphas=np.logspace(-2, 3, 10))
        lgbm = lgb.LGBMRegressor(n_estimators=75, max_depth=4, num_leaves=15, learning_rate=0.03, random_state=42, n_jobs=-1, verbose=-1)
        cat = CatBoostRegressor(iterations=75, depth=4, learning_rate=0.03, random_seed=42, thread_count=-1, verbose=0)

        ridge.fit(X_tr, y_tr)
        lgbm.fit(X_tr, y_tr)
        cat.fit(X_tr, y_tr)

        pred_ridge = ridge.predict(X_te)
        pred_lgbm = lgbm.predict(X_te)
        pred_cat = cat.predict(X_te)

        ensemble_pred = (0.20 * pred_ridge) + (0.40 * pred_lgbm) + (0.40 * pred_cat)
        pdf.loc[test_mask, "alpha_pred"] = ensemble_pred
        
        actual_test = pdf.loc[test_mask, "target_excess_24h"].values
        ic = float(np.corrcoef(ensemble_pred, actual_test)[0, 1]) if len(ensemble_pred) > 1 else 0.0
        logger.info("Fold %02d | Samples: Tr=%d, Te=%d | 24H Target IC: %.4f", fold, len(X_tr), len(X_te), ic)

    alpha_pivot = (
        pdf.pivot(index="bucket_timestamp_utc", columns="symbol", values="alpha_pred")
        .fillna(0.0)
    )
    return alpha_pivot


def run_architecture_backtest():
    feature_path = "/tmp/lake/features/pit_panel_4h.parquet"
    regime_path = "/tmp/lake/features/btc_regime_state_4h.parquet"

    df = (
        pl.read_parquet(feature_path)
        .unique(subset=["symbol", "bucket_timestamp_utc"])
        .sort("bucket_timestamp_utc")
    )
    regime_df = (
        pl.read_parquet(regime_path)
        .unique(subset=["bucket_timestamp_utc"])
        .sort("bucket_timestamp_utc")
        .to_pandas()
        .set_index("bucket_timestamp_utc")
    )

    close_df = (
        df.pivot(index="bucket_timestamp_utc", on="symbol", values="close")
        .sort("bucket_timestamp_utc")
        .to_pandas()
        .set_index("bucket_timestamp_utc")
        .ffill()
    )

    # 1. Generate 24H Ensemble Alphas
    alpha_df = generate_full_universe_alphas(df)
    
    # Synchronize timestamps
    common_idx = close_df.index.intersection(alpha_df.index).intersection(regime_df.index)
    close_df = close_df.loc[common_idx]
    alpha_df = alpha_df.loc[common_idx]
    regime_df = regime_df.loc[common_idx]

    returns_df = close_df.pct_change().fillna(0.0)

    T, N = close_df.shape
    weights_matrix = np.zeros((T, N), dtype=np.float64)

    logger.info("Simulating Point-in-Time Dynamic Covariance Allocations across %d assets and %d bars...", N, T)

    gamma = 2.5
    max_asset_wt = 0.10          # 10% maximum single-asset concentration cap
    gross_exposure_cap = 1.50    # 1.5x Gross Leverage Cap
    base_kelly = 0.25
    lookback_cov = 180           # 30-day covariance lookback
    rebalance_freq_bars = 6      # Rebalance every 24H
    top_k_eligible = 30          # Allocate across top 30 liquid assets per timestamp
    weight_deadband = 0.020      # 2.0% minimum weight change buffer

    prev_weights = np.zeros(N, dtype=np.float64)

    for t in range(lookback_cov, T):
        p_hazard = regime_df["p_hazard"].iloc[t]
        p_chop = regime_df["p_chop"].iloc[t]
        p_trend = regime_df["p_trend"].iloc[t]
        p_expansion = regime_df["p_expansion"].iloc[t]

        # BOCD Shock Lockout
        if p_hazard > 0.60:
            weights_matrix[t, :] = 0.0
            prev_weights = np.zeros(N, dtype=np.float64)
            continue

        # Rebalance check
        if t % rebalance_freq_bars != 0:
            weights_matrix[t, :] = prev_weights
            continue

        raw_alphas = alpha_df.iloc[t].values

        # Filter active assets with price history
        ret_window_full = returns_df.iloc[t - lookback_cov : t]
        valid_cols_mask = (ret_window_full != 0.0).sum(axis=0) >= (lookback_cov * 0.70)
        valid_indices = np.where(valid_cols_mask.values)[0]

        if len(valid_indices) < top_k_eligible:
            weights_matrix[t, :] = prev_weights
            continue

        # Select top active tokens by predicted alpha
        sub_alphas = raw_alphas[valid_indices]
        top_sub_idx = np.argsort(np.abs(sub_alphas))[-top_k_eligible:]
        selected_indices = valid_indices[top_sub_idx]

        # Cross-Sectional Z-Score Scaling of Alphas
        selected_alphas = raw_alphas[selected_indices]
        alpha_std = float(np.std(selected_alphas))
        if alpha_std > 1e-8:
            z_alphas = (selected_alphas - np.mean(selected_alphas)) / alpha_std
            # Scale to realistic 24H expected excess basis points (e.g. 50 bps max expected alpha)
            scaled_alphas = z_alphas * 0.0050
        else:
            scaled_alphas = np.zeros_like(selected_alphas)

        # Ledoit-Wolf Covariance Inversion
        ret_window_sub = ret_window_full.iloc[:, selected_indices].values
        lw = LedoitWolf(assume_centered=False)
        lw.fit(ret_window_sub)
        sigma_inv = np.linalg.pinv(lw.covariance_ + 1e-6 * np.eye(len(selected_indices)))

        m_regime = np.clip(0.50 * p_chop + 1.00 * p_trend + 1.20 * p_expansion, 0.25, 1.25)
        f_kelly = base_kelly * m_regime

        raw_w = (1.0 / gamma) * np.dot(sigma_inv, scaled_alphas) * f_kelly
        clipped_w = np.clip(raw_w, -max_asset_wt, max_asset_wt)
        
        # Enforce 1.5x Gross Leverage Cap
        gross_lev = np.sum(np.abs(clipped_w))
        if gross_lev > gross_exposure_cap:
            clipped_w = clipped_w * (gross_exposure_cap / gross_lev)

        current_w = np.zeros(N, dtype=np.float64)
        current_w[selected_indices] = clipped_w

        # Apply Rebalance Deadband
        w_diff = np.abs(current_w - prev_weights)
        target_w = np.where(w_diff >= weight_deadband, current_w, prev_weights)
        
        weights_matrix[t, :] = target_w
        prev_weights = target_w

    target_weights = pd.DataFrame(weights_matrix, index=common_idx, columns=close_df.columns)
    exec_weights = target_weights.shift(1).fillna(0.0)

    fees_taker = 0.00035  # 3.5 bps taker buffer
    fees_maker = 0.00000  # 0.0 bps passive maker route

    pf_taker = vbt.Portfolio.from_orders(
        close=close_df,
        size=exec_weights,
        size_type="targetpercent",
        freq="4h",
        fees=fees_taker,
        init_cash=100_000.0,
        cash_sharing=True,
        group_by=True,
        call_seq="auto",
    )

    pf_maker = vbt.Portfolio.from_orders(
        close=close_df,
        size=exec_weights,
        size_type="targetpercent",
        freq="4h",
        fees=fees_maker,
        init_cash=100_000.0,
        cash_sharing=True,
        group_by=True,
        call_seq="auto",
    )

    print("\n" + "=" * 80)
    print("      REFINED FULL UNIVERSE ARCHITECTURE BACKTEST (24H Target + Z-Score)")
    print("=" * 80)
    print(f"{'METRIC':<28} | {'PASSIVE MAKER (0 bps)':<22} | {'TAKER ROUTE (3.5 bps)':<20}")
    print("-" * 80)
    print(f"{'Sharpe Ratio':<28} | {float(np.squeeze(pf_maker.sharpe_ratio())):22.2f} | {float(np.squeeze(pf_taker.sharpe_ratio())):20.2f}")
    print(f"{'Sortino Ratio':<28} | {float(np.squeeze(pf_maker.sortino_ratio())):22.2f} | {float(np.squeeze(pf_taker.sortino_ratio())):20.2f}")
    print(f"{'Calmar Ratio':<28} | {float(np.squeeze(pf_maker.calmar_ratio())):22.2f} | {float(np.squeeze(pf_taker.calmar_ratio())):20.2f}")
    print(f"{'Max Drawdown':<28} | {float(np.squeeze(pf_maker.max_drawdown())):21.2%} | {float(np.squeeze(pf_taker.max_drawdown())):19.2%}")
    print(f"{'Total Net Return':<28} | {float(np.squeeze(pf_maker.total_return())):21.2%} | {float(np.squeeze(pf_taker.total_return())):19.2%}")
    print(f"{'Total Fees Paid':<28} | ${0.0:21,.2f} | ${float(np.squeeze(pf_maker.total_profit() - pf_taker.total_profit())):19,.2f}")
    print("=" * 80)


if __name__ == "__main__":
    run_architecture_backtest()
