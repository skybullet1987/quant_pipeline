#!/usr/bin/env python3
"""
TP PENETRATION SENSITIVITY GRID
===============================
Evaluates E3 performance under varying degrees of Take Profit penetration depth:
  Penetration depths (bps): 0.0, 0.5, 1.0, 1.5, 2.5, 5.0, 10.0
"""

import json
import math
import sys
from pathlib import Path
from typing import Dict, List, Any

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
    print("=" * 120)
    print("   IRONCORE v2.4: TAKE PROFIT PENETRATION SENSITIVITY GRID (0 to 10 bps)")
    print("=" * 120, flush=True)

    df = pl.read_parquet(DATA_LAKE_PATH)
    _, symbols, market_data = PointInTimeUniverseManager.load_pit_market_matrices(
        df=df, eval_start_ts=EVAL_START_TS, eval_end_ts=EVAL_END_TS, benchmark_symbol=BENCHMARK_SYMBOL
    )

    close_mat = np.nan_to_num(market_data["close"].copy(), nan=0.0)
    oracle_mat = np.nan_to_num(market_data["oracle"].copy(), nan=0.0)
    volume_mat = np.nan_to_num(market_data["volume"].copy(), nan=0.0)
    valid_mask = market_data["valid_price_mask"].copy() & (close_mat > 0.0)

    n_bars, n_symbols = close_mat.shape
    btc_idx = symbols.index(BENCHMARK_SYMBOL) if BENCHMARK_SYMBOL in symbols else 0
    eth_idx = symbols.index("ETH") if "ETH" in symbols else 1
    btc_prices = close_mat[:, btc_idx]

    prev_close = np.roll(close_mat, 1, axis=0)
    returns_mat = np.zeros_like(close_mat)
    valid_step = (prev_close > 0.0) & (close_mat > 0.0)
    returns_mat[valid_step] = (close_mat[valid_step] / prev_close[valid_step]) - 1.0
    returns_mat = np.nan_to_num(returns_mat, nan=0.0)
    returns_mat[0] = 0.0
    predicted_funding = np.nan_to_num((close_mat - oracle_mat) / np.maximum(oracle_mat, 1e-6) + 0.000125, nan=0.0)

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
        sigma = np.clip(np.abs(returns_mat[t]) + 0.015, 0.005, 0.20)

        step_open = np.where(p_prev > 0, p_prev, p_c)
        step_open = np.where(step_open > 0, step_open, 100.0)
        target_close = np.where(p_c > 0, p_c, step_open)

        for s in range(subbars):
            sub_opens[t, s] = step_open
            drift = (target_close - step_open) / max(subbars - s, 1)
            noise = rng.randn(n_symbols) * (step_open * sigma * 0.15)
            step_close = np.maximum(step_open + drift + noise, 1e-4)
            sub_closes[t, s] = step_close

            sub_hi = np.maximum(step_open, step_close) + np.abs(rng.randn(n_symbols)) * (step_open * sigma * 0.10)
            sub_lo = np.maximum(np.minimum(step_open, step_close) - np.abs(rng.randn(n_symbols)) * (step_open * sigma * 0.10), 1e-4)
            sub_highs[t, s] = sub_hi
            sub_lows[t, s] = sub_lo
            sub_vols[t, s] = bar_vol / subbars
            step_open = step_close

    subbar_dict = {
        "opens": sub_opens,
        "highs": sub_highs,
        "lows": sub_lows,
        "closes": sub_closes,
        "volumes": sub_vols,
    }

    config = IronCoreConfig_v1(
        maker_fee=0.00015,
        taker_fee=0.00045,
        base_maker_ratio=0.985,
        base_adverse_bps=0.00010,
        impact_coefficient=0.03,
        portfolio_deadband=0.08,
        rerisk_buffer_pct=0.02,
        fixed_slot_sizing=True,
        wfo_train_bars=540,
        wfo_test_bars=180,
        initial_capital=10000.0,
    )
    engine = IronCoreEngine(config=config)

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
        f5_std, res_std = compute_multi_beta_residual_momentum(fd_diff, btc_d, eth_d, v_mask, lookback_h=min(18, n_tr - 1))
        f_asym = compute_asymmetric_fip_scores(residuals=res_std, raw_f5_scores=f5_std, valid_mask=v_mask, lookback=min(18, n_tr - 1))
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
        f5_te, res_te = compute_multi_beta_residual_momentum(fd_diff, btc_d, eth_d, v_mask, lookback_h=min(18, n_te))
        f_asym_te = compute_asymmetric_fip_scores(residuals=res_te, raw_f5_scores=f5_te, valid_mask=v_mask, lookback=min(18, n_te))
        return f_asym_te

    feature_panel = {"close": close_mat, "valid": valid_mask, "volume": volume_mat}
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
    oos_subbars = {k: v[oos_start:oos_end] for k, v in subbar_dict.items()}
    n_oos = len(oos_scores)

    w_hyst = np.zeros((n_oos, n_symbols))
    w_prev = np.zeros(n_symbols)
    for t in range(n_oos):
        s_t = oos_scores[t]
        v_m = valid_mask[oos_start + t]
        target_w = engine.compute_rank_hysteresis_weights(
            signal_scores=s_t,
            valid_mask_t=v_m,
            weights_prev=w_prev,
            entry_k=10,
            exit_k=15,
            target_gross_leverage=1.0,
            fixed_slot_sizing=True,
        )
        w_hyst[t] = target_w
        w_prev = target_w.copy()

    adv_24h = np.zeros((len(oos_returns), n_symbols))
    vol_24h = np.zeros((len(oos_returns), n_symbols))
    for t_idx in range(len(oos_returns)):
        start_k = max(0, t_idx - 5)
        v_slice = np.nan_to_num(oos_volume[start_k:t_idx + 1], nan=0.0)
        c_slice = np.nan_to_num(oos_close[start_k:t_idx + 1], nan=0.0)
        n_pts = (t_idx + 1) - start_k
        scale = 6.0 / max(n_pts, 1)
        adv_24h[t_idx] = np.sum(v_slice * c_slice, axis=0) * scale
        if n_pts > 1:
            denom = np.maximum(c_slice[:-1], 1e-6)
            rets_slice = np.nan_to_num(np.diff(c_slice, axis=0) / denom, nan=0.0)
            vol_24h[t_idx] = np.std(rets_slice, axis=0) * np.sqrt(6 * 365)
        else:
            vol_24h[t_idx] = 0.02
    adv_24h = np.maximum(np.nan_to_num(adv_24h, nan=1000.0), 1000.0)
    vol_24h = np.clip(np.nan_to_num(vol_24h, nan=0.02), 0.001, 0.50)

    # TP Sensitivity Grid
    tp_pen_bps_list = [0.0, 0.5, 1.0, 1.5, 2.5, 5.0, 10.0]
    results = []

    print("\nRunning TP Penetration Sensitivity Surface...", flush=True)
    for pen_bps in tp_pen_bps_list:
        pen_decimal = pen_bps / 10_000.0
        p = config.resolve_runtime_parameters(
            causal_passive_mode=True,
            same_subbar_stop_vulnerable=True,
            tp_penetration_bps=pen_decimal,
            fixed_stop_loss_pct=0.035,
            fixed_take_profit_pct=0.070,
            enable_cooldown=True,
            cooldown_bars=1,
            portfolio_deadband=0.08,
            governor_tiers=config.drawdown_tiers,
        )
        res = engine.simulate_canonical_execution(
            weights_matrix=w_hyst,
            returns_mat=oos_returns,
            predicted_funding=oos_funding,
            volume_mat=oos_volume,
            close_mat=oos_close,
            subbar_data=oos_subbars,
            params=p,
            adv_24h=adv_24h,
            vol_24h=vol_24h,
        )
        results.append({
            "pen_bps": pen_bps,
            "cagr": res["cagr"],
            "sharpe": res["sharpe"],
            "max_dd": res["max_dd"],
            "ending_equity": res["ending_equity"],
            "tp_count": res["tp_count"],
            "sl_count": res["sl_count"],
            "turnover_usd": res["turnover_usd"],
            "friction_usd": res["total_friction"],
        })

    print("\n" + "=" * 110)
    print("   TABLE: TAKE PROFIT DEPTH PENETRATION SENSITIVITY SURFACE")
    print("=" * 110)
    hdr = f"{'TP Penetration (bps)':<22} | {'CAGR (%)':<10} | {'Sharpe':<8} | {'Max DD (%)':<12} | {'Ending Equity ($)':<18} | {'TP Hits':<8} | {'SL Hits':<8}"
    print(hdr)
    print("-" * 110)
    for r in results:
        print(f"{r['pen_bps']:>18.1f} bps | {r['cagr']:>+9.1f}% | {r['sharpe']:>8.2f} | {r['max_dd']:>11.1f}% | ${r['ending_equity']:>16,.0f} | {r['tp_count']:>8d} | {r['sl_count']:>8d}")
    print("=" * 110)

    with open(PIPELINE_ROOT / "reports" / "tp_penetration_sensitivity_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n[Saved] TP Sensitivity results saved to reports/tp_penetration_sensitivity_results.json")


if __name__ == "__main__":
    main()
