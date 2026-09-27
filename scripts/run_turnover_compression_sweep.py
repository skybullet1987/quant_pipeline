#!/usr/bin/env python3
"""
PHASE 3: TURNOVER & FRICTION COMPRESSION SWEEP
==============================================
Attacks the turnover bottleneck systematically without freezing the portfolio:
Pre-registered Factorial Grid:
  1. Rebalance Cadence: 4H vs 8H vs 12H
  2. Rank Hysteresis: Off (Top 10) vs On (K_entry=10, K_exit=15)
  3. Portfolio-Level Deadband: Off (0%) vs 5% vs 8% vs 12%
  4. EWMA Weight Smoothing: Raw (1.0) vs 0.35 vs 0.20

Evaluates out-of-sample under the Unified Canonical Execution Engine:
Objective: Maximize Net Realizable OOS PnL under the turnover constraint.
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
    print("   PHASE 3: PRE-REGISTERED TURNOVER & FRICTION COMPRESSION SWEEP")
    print("   Cadence (4H/8H/12H) | Rank Hysteresis | Portfolio Deadband (tau_port) | EWMA Smoothing")
    print("=" * 135, flush=True)

    # 1. Load Data Lake
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

    # 2. WFO Model
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

    def predict_alpha_scores(model: Dict[str, Any], test_features: Dict[str, np.ndarray]) -> np.ndarray:
        c_mat = test_features["close"]
        v_mask = test_features["valid"]
        n_te = len(c_mat)
        scores_out = np.zeros((n_te, n_symbols))
        if not model.get("fitted", False) or n_te == 0:
            return scores_out

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
        return f_asym_te

    feature_panel = {"close": close_mat, "valid": valid_mask, "volume": volume_mat}

    config = IronCoreConfig_v1(
        maker_fee=0.00015,
        taker_fee=0.00045,
        base_maker_ratio=0.985,
        base_adverse_bps=0.00010,
        impact_coefficient=0.03,
        deadband=0.0,  # Zero per-asset deadband to avoid freezing
        wfo_train_bars=540,
        wfo_test_bars=180,
        initial_capital=10000.0,
    )
    engine = IronCoreEngine(config=config)

    ra = MultiSplitRegimeAnalyzer(btc_prices, config.wfo_train_bars, config.wfo_test_bars)
    folds = ra.generate_wfo_folds()
    oos_start = folds[0][2]
    oos_end = folds[-1][3]

    # Pre-generate OOS alpha scores across all folds
    print(f"Generating OOS Alpha Score Panel across {len(folds)} WFO Folds...", flush=True)
    all_oos_scores = []
    for f_idx, (tr_s, tr_e, te_s, te_e) in enumerate(folds):
        tr_feats = {k: v[tr_s:tr_e - 1] for k, v in feature_panel.items()}
        tr_targets = returns_mat[tr_s + 1:tr_e]
        model = fit_alpha_model(tr_feats, tr_targets)

        te_feats = {k: v[te_s:te_e] for k, v in feature_panel.items()}
        scores_te = predict_alpha_scores(model, te_feats)
        all_oos_scores.append(scores_te)

    oos_scores = np.concatenate(all_oos_scores, axis=0)
    oos_returns = returns_mat[oos_start:oos_end]
    oos_funding = predicted_funding[oos_start:oos_end]
    oos_volume = volume_mat[oos_start:oos_end]
    oos_close = close_mat[oos_start:oos_end]
    n_oos = len(oos_scores)

    # Define Factorial Parameter Grid
    cadence_grid = [1, 2, 3]  # 1 = 4H, 2 = 8H, 3 = 12H
    hysteresis_grid = [False, True]  # False = Standard Top 10; True = Hysteresis (K_in=10, K_out=15)
    port_deadband_grid = [0.0, 0.05, 0.08, 0.12]
    ewma_grid = [1.0, 0.35]

    total_runs = len(cadence_grid) * len(hysteresis_grid) * len(port_deadband_grid) * len(ewma_grid)
    print(f"\nEvaluating {total_runs} Pre-Registered Factorial Configurations...\n", flush=True)

    results = []

    for cadence in cadence_grid:
        cadence_label = f"{cadence * 4}H"
        for use_hyst in hysteresis_grid:
            hyst_label = "RankHyst(10/15)" if use_hyst else "Top10(Raw)"
            for p_db in port_deadband_grid:
                db_label = f"DB_{int(p_db*100)}%" if p_db > 0 else "NoDB"
                for ewma_lambda in ewma_grid:
                    ewma_label = f"EWMA_{ewma_lambda:.2f}" if ewma_lambda < 1.0 else "NoSmooth"

                    # 1. Build Target Weights Matrix
                    w_mat = np.zeros((n_oos, n_symbols))
                    w_curr = np.zeros(n_symbols)
                    w_ewma = np.zeros(n_symbols)

                    for t in range(n_oos):
                        # Rebalance only on cadence boundaries
                        if t % cadence == 0:
                            scores_t = oos_scores[t]
                            val_m = valid_mask[oos_start + t]

                            if use_hyst:
                                target_w = engine.compute_rank_hysteresis_weights(
                                    signal_scores=scores_t,
                                    valid_mask_t=val_m,
                                    weights_prev=w_curr,
                                    entry_k=10,
                                    exit_k=15,
                                    target_gross_leverage=1.0,
                                )
                            else:
                                val_idx = np.where(val_m)[0]
                                target_w = np.zeros(n_symbols)
                                if len(val_idx) >= 20:
                                    s_t = scores_t[val_idx]
                                    order = np.argsort(s_t)
                                    long_idx = val_idx[order[-10:]]
                                    short_idx = val_idx[order[:10]]
                                    target_w[long_idx] = 0.50 / 10.0
                                    target_w[short_idx] = -0.50 / 10.0

                            # Apply EWMA Smoothing if active
                            if ewma_lambda < 1.0:
                                w_ewma = ewma_lambda * target_w + (1.0 - ewma_lambda) * w_ewma
                                w_curr = w_ewma.copy()
                            else:
                                w_curr = target_w.copy()

                        w_mat[t] = w_curr.copy()

                    # 2. Simulate on Canonical Execution Engine
                    sim_res = engine.simulate_canonical_execution(
                        weights_matrix=w_mat,
                        returns_mat=oos_returns,
                        predicted_funding=oos_funding,
                        volume_mat=oos_volume,
                        close_mat=oos_close,
                        subbar_data=None,
                        portfolio_deadband=p_db,
                        deadband=0.0,
                        initial_capital=10000.0,
                    )

                    config_name = f"{cadence_label} | {hyst_label:<14} | {db_label:<6} | {ewma_label:<8}"
                    results.append({
                        "name": config_name,
                        "cadence": cadence_label,
                        "hysteresis": use_hyst,
                        "deadband": p_db,
                        "ewma": ewma_lambda,
                        "turnover_mult": sim_res["turnover_multiple"],
                        "turnover_usd": sim_res["turnover_usd"],
                        "gross_pnl": sim_res["gross_price_pnl"],
                        "fees": sim_res["fees"],
                        "impact": sim_res["market_impact"],
                        "net_pnl": sim_res["net_pnl"],
                        "cagr": sim_res["cagr"],
                        "sharpe": sim_res["sharpe"],
                        "max_dd": sim_res["max_dd"],
                        "ending_equity": sim_res["ending_equity"],
                    })

    # Sort results by Net Realizable PnL descending
    results.sort(key=lambda x: x["net_pnl"], reverse=True)

    print("=" * 145)
    print(f"{'Rank':<4} | {'Configuration':<45} | {'Turnover (x)':<12} | {'Gross PnL':<11} | {'Fees ($)':<9} | {'Impact ($)':<10} | {'Net PnL ($)':<11} | {'CAGR':<8} | {'Sharpe':<7} | {'Max DD':<7}")
    print("-" * 145)
    for rank, r in enumerate(results[:15], 1):
        print(
            f"{rank:<4} | "
            f"{r['name']:<45} | "
            f"{r['turnover_mult']:>10.1f}x | "
            f"${r['gross_pnl']:>9.2f} | "
            f"${r['fees']:>7.2f} | "
            f"${r['impact']:>8.2f} | "
            f"${r['net_pnl']:>9.2f} | "
            f"{r['cagr']:>+6.1f}% | "
            f"{r['sharpe']:>6.2f} | "
            f"{r['max_dd']:>5.1f}%"
        )
    print("=" * 145)

    winner = results[0]
    baseline = next(r for r in results if r["cadence"] == "4H" and not r["hysteresis"] and r["deadband"] == 0.0 and r["ewma"] == 1.0)

    print("\n--- BASELINE VS BEST COMPRESSION WINNER ---")
    print(f"Unmanaged Baseline (4H Raw):")
    print(f"  Turnover: {baseline['turnover_mult']:.1f}x | Fees: ${baseline['fees']:,.2f} | Impact: ${baseline['impact']:,.2f} | Net PnL: ${baseline['net_pnl']:,.2f} | Sharpe: {baseline['sharpe']:.2f}")
    print(f"Optimized Winner ({winner['name']}):")
    print(f"  Turnover: {winner['turnover_mult']:.1f}x | Fees: ${winner['fees']:,.2f} | Impact: ${winner['impact']:,.2f} | Net PnL: ${winner['net_pnl']:,.2f} | Sharpe: {winner['sharpe']:.2f} | CAGR: {winner['cagr']:+.1f}%")
    turnover_reduction = (1.0 - winner['turnover_mult'] / baseline['turnover_mult']) * 100.0
    print(f"  Turnover Reduction: {turnover_reduction:.1f}%")
    print(f"  Net Economic Improvement: +${winner['net_pnl'] - baseline['net_pnl']:,.2f}")


if __name__ == "__main__":
    main()
