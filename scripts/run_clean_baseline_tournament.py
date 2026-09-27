#!/usr/bin/env python3
"""
PHASE 2: CLEAN ECONOMIC BASELINE TOURNAMENT
===========================================
Executes the clean economic baseline using the unified canonical execution engine:
  B0: 4H Discrete, No Stops, Zero Lookahead
  B1: Sub-Bar High-Resolution (4 subbars/bar), No Stops, ALO Queue & Timeout Crossings
  B2: Sub-Bar High-Resolution, Sequence-Correct 3.5% Bracket Stops (Conservative Adverse Stop First)
  B3: 4H Discrete with Discrete Tiered Portfolio Drawdown Governor (<5% 1.0x, 5-10% 0.75x, 10-15% 0.35x, >=15% Halt)

Decomposes the exact economic waterfall:
  Gross Price P&L
  - Exchange Fees
  - Footprint Market Impact
  + Funding Cashflow
  - Stop Losses
  = Realizable Net P&L
"""

import math
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple, Any

import numpy as np
import polars as pl

PIPELINE_ROOT = Path("/home/skybullet1987/quant_pipeline")
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from backtest_10x_convex_compounding import (
    DATA_LAKE_PATH, BENCHMARK_SYMBOL, EVAL_START_TS, EVAL_END_TS
)
from src.data.pit_universe_manager import PointInTimeUniverseManager
from src.backtesting.ironcore_engine import IronCoreEngine
from src.backtesting.ironcore_config import IronCoreConfig_v1
from src.backtesting.multi_split_regime import MultiSplitRegimeAnalyzer
from src.alpha.fracdiff_orthogonal_engine import (
    apply_fractional_differentiation,
    compute_multi_beta_residual_momentum,
)
from src.signals.asym_fip import compute_asymmetric_fip_scores


def main():
    print("=" * 135)
    print("   PHASE 2: CLEAN ECONOMIC BASELINE TOURNAMENT (UNIFIED CANONICAL ENGINE)")
    print("   Zero Lookahead (t -> t+1) | Dual Turnover Tracking | Unclipped Impact | Drawdown Governor")
    print("=" * 135, flush=True)

    # 1. Load Data Lake
    print("\n[1/4] Loading Point-In-Time 4H Market Data Lake...", flush=True)
    df = pl.read_parquet(DATA_LAKE_PATH)
    _, symbols, market_data = PointInTimeUniverseManager.load_pit_market_matrices(
        df=df, eval_start_ts=EVAL_START_TS, eval_end_ts=EVAL_END_TS, benchmark_symbol=BENCHMARK_SYMBOL
    )

    close_mat = market_data["close"].copy()
    oracle_mat = market_data["oracle"].copy()
    volume_mat = market_data["volume"].copy()
    valid_mask = market_data["valid_price_mask"].copy()

    n_bars, n_symbols = close_mat.shape
    btc_idx = symbols.index(BENCHMARK_SYMBOL) if BENCHMARK_SYMBOL in symbols else 0
    eth_idx = symbols.index("ETH") if "ETH" in symbols else 1
    btc_prices = close_mat[:, btc_idx]

    prev_close = np.roll(close_mat, 1, axis=0)
    returns_mat = np.nan_to_num(np.where(prev_close > 0, (close_mat / prev_close) - 1.0, 0.0))
    returns_mat[0] = 0.0
    predicted_funding = (close_mat - oracle_mat) / (oracle_mat + 1e-8) + 0.000125

    # 2. Build Sub-Bar Data (4 subbars per 4H bar)
    print("[2/4] Constructing Causal Sub-Bar Intraday Paths (4 subbars/bar)...", flush=True)
    subbars = 4
    sub_opens = np.zeros((n_bars, subbars, n_symbols))
    sub_highs = np.zeros((n_bars, subbars, n_symbols))
    sub_lows = np.zeros((n_bars, subbars, n_symbols))
    sub_closes = np.zeros((n_bars, subbars, n_symbols))
    sub_vols = np.zeros((n_bars, subbars, n_symbols))

    rng = np.random.RandomState(42)
    for t in range(n_bars):
        p_c = close_mat[t]
        p_prev = prev_close[t]
        bar_vol = volume_mat[t]
        sigma = np.abs(returns_mat[t]) + 0.015

        step_open = p_prev.copy()
        for s in range(subbars):
            sub_opens[t, s] = step_open
            drift = (p_c - step_open) / max(subbars - s, 1)
            noise = rng.randn(n_symbols) * sigma * 0.35
            step_close = step_open + drift + noise
            sub_closes[t, s] = np.maximum(step_close, 1e-4)

            sub_hi = np.maximum(step_open, step_close) + np.abs(rng.randn(n_symbols)) * sigma * 0.25
            sub_lo = np.minimum(step_open, step_close) - np.abs(rng.randn(n_symbols)) * sigma * 0.25
            sub_highs[t, s] = sub_hi
            sub_lows[t, s] = np.maximum(sub_lo, 1e-4)
            sub_vols[t, s] = bar_vol / subbars
            step_open = step_close

    subbar_dict = {
        "opens": sub_opens,
        "highs": sub_highs,
        "lows": sub_lows,
        "closes": sub_closes,
        "volumes": sub_vols,
    }

    # 3. Setup WFO Strategy Model
    print("[3/4] Configuring True In-Fold WFO Strategy Model...", flush=True)
    def fit_alpha_model(train_features: Dict[str, np.ndarray], train_targets: np.ndarray) -> Dict[str, Any]:
        c_mat = train_features["close"]
        v_mask = train_features["valid"]
        n_tr = len(c_mat)
        if n_tr < 30:
            return {"fitted": False}

        fd_series = apply_fractional_differentiation(c_mat, d=0.38, max_len=18)
        fd_diff = fd_series - np.roll(fd_series, 1, axis=0)
        fd_diff[0] = 0.0
        btc_d = fd_diff[:, btc_idx]
        eth_d = fd_diff[:, eth_idx]

        f5_std, res_std = compute_multi_beta_residual_momentum(
            fd_diff, btc_d, eth_d, v_mask, lookback_h=min(18, n_tr - 1)
        )
        f_asym = compute_asymmetric_fip_scores(
            residuals=res_std, raw_f5_scores=f5_std, valid_mask=v_mask, lookback=min(18, n_tr - 1)
        )
        return {"fitted": True}

    def predict_alpha_weights(model: Dict[str, Any], test_features: Dict[str, np.ndarray]) -> np.ndarray:
        c_mat = test_features["close"]
        v_mask = test_features["valid"]
        n_te = len(c_mat)
        w_out = np.zeros((n_te, n_symbols))
        if not model.get("fitted", False) or n_te == 0:
            return w_out

        fd_series = apply_fractional_differentiation(c_mat, d=0.38, max_len=18)
        fd_diff = fd_series - np.roll(fd_series, 1, axis=0)
        fd_diff[0] = 0.0
        btc_d = fd_diff[:, btc_idx]
        eth_d = fd_diff[:, eth_idx]

        f5_te, res_te = compute_multi_beta_residual_momentum(
            fd_diff, btc_d, eth_d, v_mask, lookback_h=min(18, n_te)
        )
        f_asym_te = compute_asymmetric_fip_scores(
            residuals=res_te, raw_f5_scores=f5_te, valid_mask=v_mask, lookback=min(18, n_te)
        )

        for t in range(n_te):
            sig_t = f_asym_te[t]
            val_idx = np.where(v_mask[t])[0]
            if len(val_idx) >= 20:
                scores = sig_t[val_idx]
                sorted_i = np.argsort(scores)
                long_idx = val_idx[sorted_i[-10:]]
                short_idx = val_idx[sorted_i[:10]]
                w_out[t, long_idx] = 0.50 / 10.0
                w_out[t, short_idx] = -0.50 / 10.0
        return w_out

    feature_panel = {"close": close_mat, "valid": valid_mask, "volume": volume_mat}

    config = IronCoreConfig_v1(
        maker_fee=0.00015,
        taker_fee=0.00045,
        base_maker_ratio=0.985,
        base_adverse_bps=0.00010,
        impact_coefficient=0.03,
        deadband=0.030,
        wfo_train_bars=540,
        wfo_test_bars=180,
        initial_capital=10000.0,
    )
    engine = IronCoreEngine(config=config)

    print("[4/4] Generating True In-Fold Out-Of-Sample Weights (Zero-Leakage API)...", flush=True)
    wfo_base = engine.run_true_wfo(
        fit_fn=fit_alpha_model,
        predict_fn=predict_alpha_weights,
        feature_panel=feature_panel,
        returns_mat=returns_mat,
        predicted_funding=predicted_funding,
        volume_mat=volume_mat,
        close_mat=close_mat,
        btc_prices=btc_prices,
        continuous_portfolio=True,
    )

    ra = MultiSplitRegimeAnalyzer(btc_prices, config.wfo_train_bars, config.wfo_test_bars)
    folds = ra.generate_wfo_folds()
    oos_start = folds[0][2]
    oos_end = folds[-1][3]
    oos_weights = wfo_base["oos_weights_matrix"]
    n_oos = len(oos_weights)

    oos_returns = returns_mat[oos_start:oos_end]
    oos_funding = predicted_funding[oos_start:oos_end]
    oos_volume = volume_mat[oos_start:oos_end]
    oos_close = close_mat[oos_start:oos_end]
    oos_subbars = {k: v[oos_start:oos_end] for k, v in subbar_dict.items()}

    print(f"OOS Evaluation Window: Bars {oos_start} -> {oos_end} ({n_oos} 4H bars = {n_oos/6:.1f} calendar days)")

    # Execute B0, B1, B2, B3 on Canonical Engine
    print("\nExecuting Factorial Variations on Unified Canonical Engine...\n")

    # B0: 4H Discrete, No Stops
    res_b0 = engine.simulate_canonical_execution(
        weights_matrix=oos_weights,
        returns_mat=oos_returns,
        predicted_funding=oos_funding,
        volume_mat=oos_volume,
        close_mat=oos_close,
        subbar_data=None,
        sl_pct=None,
        tp_pct=None,
        initial_capital=10000.0,
    )

    # B1: Sub-Bar High-Resolution, No Stops
    res_b1 = engine.simulate_canonical_execution(
        weights_matrix=oos_weights,
        returns_mat=oos_returns,
        predicted_funding=oos_funding,
        volume_mat=oos_volume,
        close_mat=oos_close,
        subbar_data=oos_subbars,
        sl_pct=None,
        tp_pct=None,
        initial_capital=10000.0,
    )

    # B2: Sub-Bar High-Resolution, Sequence-Correct 3.5% Bracket Stops
    res_b2 = engine.simulate_canonical_execution(
        weights_matrix=oos_weights,
        returns_mat=oos_returns,
        predicted_funding=oos_funding,
        volume_mat=oos_volume,
        close_mat=oos_close,
        subbar_data=oos_subbars,
        sl_pct=0.035,
        tp_pct=0.070,
        enable_cooldown=True,
        cooldown_bars=1,
        initial_capital=10000.0,
    )

    # B3: 4H Discrete with Tiered Drawdown Governor
    res_b3 = engine.simulate_canonical_execution(
        weights_matrix=oos_weights,
        returns_mat=oos_returns,
        predicted_funding=oos_funding,
        volume_mat=oos_volume,
        close_mat=oos_close,
        subbar_data=None,
        sl_pct=None,
        tp_pct=None,
        governor_tiers=config.drawdown_tiers,
        initial_capital=10000.0,
    )

    variants = [
        ("B0: 4H Discrete (No Stops)", res_b0),
        ("B1: Sub-Bar (No Stops)", res_b1),
        ("B2: Sub-Bar (3.5% SL / 7% TP)", res_b2),
        ("B3: 4H + Tiered DD Governor", res_b3),
    ]

    print("=" * 135)
    print(f"{'Variant':<35} | {'CAGR':<9} | {'Sharpe':<8} | {'Max DD':<8} | {'Gross PnL':<12} | {'Fees Paid':<11} | {'Impact':<10} | {'Net PnL':<12} | {'Turnover ($)':<14} | {'Stops':<6}")
    print("-" * 135)
    for name, r in variants:
        print(
            f"{name:<35} | "
            f"{r['cagr']:>+7.2f}% | "
            f"{r['sharpe']:>7.2f} | "
            f"{r['max_dd']:>6.2f}% | "
            f"${r['gross_price_pnl']:>10.2f} | "
            f"${r['fees']:>9.2f} | "
            f"${r['market_impact']:>8.2f} | "
            f"${r['net_pnl']:>10.2f} | "
            f"${r['turnover_usd']:>12,.0f} | "
            f"{r['sl_count']:>5}"
        )
    print("=" * 135)

    print("\n--- ECONOMIC WATERFALL ATTRIBUTION ---")
    for name, r in variants:
        print(f"\n{name}:")
        print(f"  + Gross Price PnL:     ${r['gross_price_pnl']:>10.2f}")
        print(f"  - Exchange Fees:       ${r['fees']:>10.2f}")
        print(f"  - Footprint Impact:    ${r['market_impact']:>10.2f}")
        print(f"  + Funding Cashflow:    ${r['funding_pnl']:>10.2f}")
        print(f"  = Net Realizable PnL:  ${r['net_pnl']:>10.2f} (Final Equity: ${r['ending_equity']:,.2f})")
        print(f"  Turnover: {r['turnover_multiple']:.1f}x NAV (${r['turnover_usd']:,.0f} USD traded)")
        if r['sl_count'] > 0:
            print(f"  Intrabar Stops Hit: {r['sl_count']} stop-outs, {r['tp_count']} take-profits")


if __name__ == "__main__":
    main()
