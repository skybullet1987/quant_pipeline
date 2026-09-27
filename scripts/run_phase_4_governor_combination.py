#!/usr/bin/env python3
"""
PHASE 4: INTEGRATING PORTFOLIO DRAWDOWN GOVERNANCE WITH THE COMPRESSION WINNER
=============================================================================
Combines:
  1. Phase 3 Winner: 4H Cadence | Rank Hysteresis (K_entry=10, K_exit=15) | Portfolio Deadband 12% | EWMA 0.35
  2. Phase 2 Winner: Discrete Tiered Portfolio Drawdown Governor:
     - < 5% DD: 1.0x leverage
     - 5% - 10% DD: 0.75x leverage
     - 10% - 15% DD: 0.35x aggressive de-risking
     - >= 15% DD: 0.0x capital preservation halt
"""

import math
import sys
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
    print("   PHASE 4: COMPRESSION WINNER + TIERED PORTFOLIO DRAWDOWN GOVERNOR")
    print("   Rank Hysteresis (10/15) | DB 12% | EWMA 0.35 | Dynamic Portfolio Gearing")
    print("=" * 135, flush=True)

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
        if not model.get("fitted", False) or n_te == 0:
            return np.zeros((n_te, n_symbols))

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
        deadband=0.0,
        wfo_train_bars=540,
        wfo_test_bars=180,
        initial_capital=10000.0,
    )
    engine = IronCoreEngine(config=config)

    ra = MultiSplitRegimeAnalyzer(btc_prices, config.wfo_train_bars, config.wfo_test_bars)
    folds = ra.generate_wfo_folds()
    oos_start = folds[0][2]
    oos_end = folds[-1][3]

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

    # Build target weights using Rank Hysteresis (10/15) + EWMA 0.35
    w_mat = np.zeros((n_oos, n_symbols))
    w_curr = np.zeros(n_symbols)
    w_ewma = np.zeros(n_symbols)

    for t in range(n_oos):
        scores_t = oos_scores[t]
        val_m = valid_mask[oos_start + t]
        target_w = engine.compute_rank_hysteresis_weights(
            signal_scores=scores_t,
            valid_mask_t=val_m,
            weights_prev=w_curr,
            entry_k=10,
            exit_k=15,
            target_gross_leverage=1.0,
        )
        w_ewma = 0.35 * target_w + 0.65 * w_ewma
        w_curr = w_ewma.copy()
        w_mat[t] = w_curr.copy()

    # Evaluation 1: No Governor
    res_no_gov = engine.simulate_canonical_execution(
        weights_matrix=w_mat,
        returns_mat=oos_returns,
        predicted_funding=oos_funding,
        volume_mat=oos_volume,
        close_mat=oos_close,
        portfolio_deadband=0.12,
        initial_capital=10000.0,
    )

    # Evaluation 2: With Discrete Tiered Governor
    res_gov = engine.simulate_canonical_execution(
        weights_matrix=w_mat,
        returns_mat=oos_returns,
        predicted_funding=oos_funding,
        volume_mat=oos_volume,
        close_mat=oos_close,
        portfolio_deadband=0.12,
        governor_tiers=config.drawdown_tiers,
        initial_capital=10000.0,
    )

    # Ruin Exceedance Analysis
    from src.backtesting.ruin_and_leverage_frontier import RuinAndLeverageFrontier
    ruin_no_gov = RuinAndLeverageFrontier.stationary_block_bootstrap_ruin(res_no_gov["bar_returns"], ruin_threshold=0.15)
    ruin_gov = RuinAndLeverageFrontier.stationary_block_bootstrap_ruin(res_gov["bar_returns"], ruin_threshold=0.15)

    print("\n" + "=" * 135)
    print(f"{'Strategy Variant':<40} | {'CAGR':<9} | {'Sharpe':<8} | {'Max DD':<8} | {'Gross PnL':<12} | {'Fees':<9} | {'Impact':<9} | {'Net PnL':<12} | {'Turnover':<10}")
    print("-" * 135)
    print(
        f"{'Phase 3 Winner (Ungoverned)':<40} | "
        f"{res_no_gov['cagr']:>+7.2f}% | "
        f"{res_no_gov['sharpe']:>7.2f} | "
        f"{res_no_gov['max_dd']:>6.2f}% | "
        f"${res_no_gov['gross_price_pnl']:>10.2f} | "
        f"${res_no_gov['fees']:>7.2f} | "
        f"${res_no_gov['market_impact']:>7.2f} | "
        f"${res_no_gov['net_pnl']:>10.2f} | "
        f"{res_no_gov['turnover_multiple']:>8.1f}x"
    )
    print(
        f"{'Phase 4 Winner (+ Tiered DD Governor)':<40} | "
        f"{res_gov['cagr']:>+7.2f}% | "
        f"{res_gov['sharpe']:>7.2f} | "
        f"{res_gov['max_dd']:>6.2f}% | "
        f"${res_gov['gross_price_pnl']:>10.2f} | "
        f"${res_gov['fees']:>7.2f} | "
        f"${res_gov['market_impact']:>7.2f} | "
        f"${res_gov['net_pnl']:>10.2f} | "
        f"{res_gov['turnover_multiple']:>8.1f}x"
    )
    print("=" * 135)

    print("\n--- RUIN EXCEEDANCE COMPARISON (P(MDD >= Threshold)) ---")
    print(f"{'Drawdown Threshold':<25} | {'Ungoverned':<15} | {'With Tiered Governor':<20}")
    print("-" * 65)
    for th_label in ["P(MDD >= 10%)", "P(MDD >= 15%)", "P(MDD >= 20%)", "P(MDD >= 25%)", "P(MDD >= 30%)", "P(MDD >= 50%)"]:
        p_ungov = ruin_no_gov["exceedance_curve"].get(th_label, 0.0) * 100.0
        p_gov = ruin_gov["exceedance_curve"].get(th_label, 0.0) * 100.0
        print(f"{th_label:<25} | {p_ungov:>13.2f}% | {p_gov:>18.2f}%")


if __name__ == "__main__":
    main()
