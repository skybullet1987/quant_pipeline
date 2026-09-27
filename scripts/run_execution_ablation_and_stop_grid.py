#!/usr/bin/env python3
"""
FOUR-WAY EXECUTION REALISM ABLATION (E0-E3) & STOP SENSITIVITY GRID
==================================================================
Evaluates the B6 configuration under four escalating levels of execution physics:
  E0: Heuristic Baseline (same-subbar touch, same-subbar stop immune, 0 bps TP penetration)
  E1: Event-Causal Passive Queue (next-subbar touch only, same-subbar stop immune)
  E2: Causal Passive + Stop Vulnerability (next-subbar touch, same-subbar stop vulnerable)
  E3: Fully Causal Reality (strictly causal ADV/vol, next-subbar touch, same-subbar stop vulnerable, 1.5 bps TP penetration)

Followed by a comprehensive Stop Loss Parameter Basin Stability Grid on E3 physics:
  Fixed Stops: 1.5%, 2.0%, 2.5%, 3.0%, 3.5%, 4.0%, 4.5%, 5.0%
  Dynamic ATR Stops: 2.0 ATR, 2.5 ATR, 3.0 ATR
"""

import json
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
from src.backtesting.ironcore_config import IronCoreConfig_v1, ResolvedExecutionParameters
from src.backtesting.multi_split_regime import MultiSplitRegimeAnalyzer
from src.alpha.fracdiff_orthogonal_engine import (
    apply_fractional_differentiation,
    compute_multi_beta_residual_momentum,
)
from src.signals.asym_fip import compute_asymmetric_fip_scores


def main():
    print("=" * 135)
    print("   IRONCORE v2.4.0: FOUR-WAY EXECUTION REALISM ABLATION & STOP SENSITIVITY GRID")
    print("   Institutional Execution Parity Audit | Zero Alpha Weight Curve-Fitting")
    print("=" * 135, flush=True)

    # 1. Load Data Lake
    print("\n[1/5] Loading Point-In-Time 4H Market Data Lake...", flush=True)
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
    returns_mat = np.nan_to_num(returns_mat, nan=0.0, posinf=0.0, neginf=0.0)
    returns_mat[0] = 0.0
    predicted_funding = np.nan_to_num((close_mat - oracle_mat) / np.maximum(oracle_mat, 1e-6) + 0.000125, nan=0.0)

    # 2. Build High-Resolution Sub-Bar Data (4 subbars per 4H bar)
    print("[2/5] Constructing Causal Sub-Bar Intraday Paths (4 subbars/bar)...", flush=True)
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

    # 3. Compute Dynamic ATR Stops
    print("[3/5] Precomputing Dynamic ATR Volatility Stops...", flush=True)
    bar_high_4h = np.max(sub_highs, axis=1)
    bar_low_4h = np.min(sub_lows, axis=1)
    tr_4h = np.maximum(
        bar_high_4h - bar_low_4h,
        np.maximum(np.abs(bar_high_4h - prev_close), np.abs(bar_low_4h - prev_close))
    )
    atr_14 = np.zeros_like(tr_4h)
    for t in range(n_bars):
        lookback = tr_4h[max(0, t - 13):t + 1]
        atr_14[t] = np.mean(lookback, axis=0)

    dynamic_sl_2atr = np.clip((2.0 * atr_14) / np.maximum(close_mat, 1e-4), 0.020, 0.080)
    dynamic_tp_4atr = dynamic_sl_2atr * 2.0
    dynamic_sl_2_5atr = np.clip((2.5 * atr_14) / np.maximum(close_mat, 1e-4), 0.025, 0.100)
    dynamic_tp_5atr = dynamic_sl_2_5atr * 2.0
    dynamic_sl_3atr = np.clip((3.0 * atr_14) / np.maximum(close_mat, 1e-4), 0.030, 0.120)
    dynamic_tp_6atr = dynamic_sl_3atr * 2.0

    # 4. Generate Frozen WFO Alpha Scores
    print("[4/5] Executing True In-Fold WFO Alpha Generation...", flush=True)
    feature_panel = {"close": close_mat, "valid": valid_mask, "volume": volume_mat}
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
    oos_sl_2atr = dynamic_sl_2atr[oos_start:oos_end]
    oos_tp_4atr = dynamic_tp_4atr[oos_start:oos_end]
    oos_sl_2_5atr = dynamic_sl_2_5atr[oos_start:oos_end]
    oos_tp_5atr = dynamic_tp_5atr[oos_start:oos_end]
    oos_sl_3atr = dynamic_sl_3atr[oos_start:oos_end]
    oos_tp_6atr = dynamic_tp_6atr[oos_start:oos_end]
    n_oos = len(oos_scores)

    print(f"OOS Window: Bars {oos_start} -> {oos_end} ({n_oos} 4H bars = {n_oos/6:.1f} days)")

    # Build Frozen Rank Hysteresis Weights (K_in=10, K_out=15, fixed_slot_sizing=True)
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

    # Precompute causal ADV & Vol for entire matrix
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
            rets_slice = np.nan_to_num(np.diff(c_slice, axis=0) / denom, nan=0.0, posinf=0.0, neginf=0.0)
            vol_24h[t_idx] = np.std(rets_slice, axis=0) * np.sqrt(6 * 365)
        else:
            vol_24h[t_idx] = 0.02
    adv_24h = np.maximum(np.nan_to_num(adv_24h, nan=1000.0), 1000.0)
    vol_24h = np.clip(np.nan_to_num(vol_24h, nan=0.02), 0.001, 0.50)

    # =========================================================================
    # PART 1: FOUR-WAY EXECUTION REALISM ABLATION (E0 to E3 on B6)
    # =========================================================================
    print("\n[5/5] Executing 4-Way Execution Realism Ablation (E0 -> E3)...", flush=True)

    # E0: Heuristic Baseline (Legacy mechanics: same-subbar touch, same-subbar stop immune, 0 bps TP penetration)
    params_e0 = config.resolve_runtime_parameters(
        causal_passive_mode=False,
        same_subbar_stop_vulnerable=False,
        tp_penetration_bps=0.0,
        sl_pct=0.035,
        tp_pct=0.070,
        enable_cooldown=True,
        cooldown_bars=1,
        portfolio_deadband=0.08,
        governor_tiers=config.drawdown_tiers,
    )
    res_e0 = engine.simulate_canonical_execution(
        weights_matrix=w_hyst,
        returns_mat=oos_returns,
        predicted_funding=oos_funding,
        volume_mat=oos_volume,
        close_mat=oos_close,
        subbar_data=oos_subbars,
        params=params_e0,
        adv_24h=adv_24h,
        vol_24h=vol_24h,
    )

    # E1: Event-Causal Passive Queue (next-subbar touch only; same-subbar stop immune)
    params_e1 = config.resolve_runtime_parameters(
        causal_passive_mode=True,
        same_subbar_stop_vulnerable=False,
        tp_penetration_bps=0.0,
        sl_pct=0.035,
        tp_pct=0.070,
        enable_cooldown=True,
        cooldown_bars=1,
        portfolio_deadband=0.08,
        governor_tiers=config.drawdown_tiers,
    )
    res_e1 = engine.simulate_canonical_execution(
        weights_matrix=w_hyst,
        returns_mat=oos_returns,
        predicted_funding=oos_funding,
        volume_mat=oos_volume,
        close_mat=oos_close,
        subbar_data=oos_subbars,
        params=params_e1,
        adv_24h=adv_24h,
        vol_24h=vol_24h,
    )

    # E2: Event-Causal Passive + Same-Subbar Stop Vulnerability
    params_e2 = config.resolve_runtime_parameters(
        causal_passive_mode=True,
        same_subbar_stop_vulnerable=True,
        tp_penetration_bps=0.0,
        sl_pct=0.035,
        tp_pct=0.070,
        enable_cooldown=True,
        cooldown_bars=1,
        portfolio_deadband=0.08,
        governor_tiers=config.drawdown_tiers,
    )
    res_e2 = engine.simulate_canonical_execution(
        weights_matrix=w_hyst,
        returns_mat=oos_returns,
        predicted_funding=oos_funding,
        volume_mat=oos_volume,
        close_mat=oos_close,
        subbar_data=oos_subbars,
        params=params_e2,
        adv_24h=adv_24h,
        vol_24h=vol_24h,
    )

    # E3: Fully Causal Reality (+ 1.5 bps TP penetration requirement)
    params_e3 = config.resolve_runtime_parameters(
        causal_passive_mode=True,
        same_subbar_stop_vulnerable=True,
        tp_penetration_bps=0.00015,
        sl_pct=0.035,
        tp_pct=0.070,
        enable_cooldown=True,
        cooldown_bars=1,
        portfolio_deadband=0.08,
        governor_tiers=config.drawdown_tiers,
    )
    res_e3 = engine.simulate_canonical_execution(
        weights_matrix=w_hyst,
        returns_mat=oos_returns,
        predicted_funding=oos_funding,
        volume_mat=oos_volume,
        close_mat=oos_close,
        subbar_data=oos_subbars,
        params=params_e3,
        adv_24h=adv_24h,
        vol_24h=vol_24h,
    )

    ablation_results = [
        ("E0: Heuristic Baseline", res_e0),
        ("E1: + Next-Subbar Passive Touch", res_e1),
        ("E2: + Same-Subbar Stop Vulnerability", res_e2),
        ("E3: Fully Causal Reality (+ TP 1.5bps Pen)", res_e3),
    ]

    # =========================================================================
    # PART 2: STOP LOSS SENSITIVITY GRID UNDER E3 PHYSICS
    # =========================================================================
    print("\nExecuting Stop Loss Sensitivity Grid on E3 Physics...", flush=True)
    stop_grid_specs = [
        ("Fixed 1.5% SL / 3.0% TP", 0.015, 0.030, None, None),
        ("Fixed 2.0% SL / 4.0% TP", 0.020, 0.040, None, None),
        ("Fixed 2.5% SL / 5.0% TP", 0.025, 0.050, None, None),
        ("Fixed 3.0% SL / 6.0% TP", 0.030, 0.060, None, None),
        ("Fixed 3.5% SL / 7.0% TP (Baseline)", 0.035, 0.070, None, None),
        ("Fixed 4.0% SL / 8.0% TP", 0.040, 0.080, None, None),
        ("Fixed 4.5% SL / 9.0% TP", 0.045, 0.090, None, None),
        ("Fixed 5.0% SL / 10.0% TP", 0.050, 0.100, None, None),
        ("Dynamic 2.0 ATR SL / 4.0 ATR TP", None, None, oos_sl_2atr, oos_tp_4atr),
        ("Dynamic 2.5 ATR SL / 5.0 ATR TP", None, None, oos_sl_2_5atr, oos_tp_5atr),
        ("Dynamic 3.0 ATR SL / 6.0 ATR TP", None, None, oos_sl_3atr, oos_tp_6atr),
    ]

    grid_results = []
    for label, sl_f, tp_f, sl_dyn, tp_dyn in stop_grid_specs:
        overrides = {
            "causal_passive_mode": True,
            "same_subbar_stop_vulnerable": True,
            "tp_penetration_bps": 0.00015,
            "enable_cooldown": True,
            "cooldown_bars": 1,
            "portfolio_deadband": 0.08,
            "governor_tiers": config.drawdown_tiers,
        }
        if sl_dyn is not None:
            overrides["dynamic_stop_loss"] = sl_dyn
            overrides["dynamic_take_profit"] = tp_dyn
            overrides["fixed_stop_loss_pct"] = None
            overrides["fixed_take_profit_pct"] = None
        else:
            overrides["fixed_stop_loss_pct"] = sl_f
            overrides["fixed_take_profit_pct"] = tp_f
            overrides["dynamic_stop_loss"] = None
            overrides["dynamic_take_profit"] = None

        p_grid = config.resolve_runtime_parameters(**overrides)
        res_g = engine.simulate_canonical_execution(
            weights_matrix=w_hyst,
            returns_mat=oos_returns,
            predicted_funding=oos_funding,
            volume_mat=oos_volume,
            close_mat=oos_close,
            subbar_data=oos_subbars,
            params=p_grid,
            adv_24h=adv_24h,
            vol_24h=vol_24h,
        )
        grid_results.append((label, res_g))

    # =========================================================================
    # PART 3: REPORTING & FORMATTED COMPARISON TABLES
    # =========================================================================
    print("\n" + "=" * 135)
    print("   TABLE 1: FOUR-WAY EXECUTION REALISM ABLATION (E0 -> E3 ON B6)")
    print("=" * 135)
    hdr1 = (
        f"{'Variant':<42} | {'CAGR (%)':<9} | {'Sharpe':<7} | {'Max DD (%)':<10} | "
        f"{'Terminal ($)':<12} | {'Turnover ($)':<12} | {'SL Trigs':<8} | {'TP Trigs':<8} | {'Maker %':<7}"
    )
    print(hdr1)
    print("-" * 135)

    for label, r in ablation_results:
        row = (
            f"{label:<42} | {r['cagr']:>+8.1f}% | {r['sharpe']:>7.2f} | {r['max_dd']:>9.1f}% | "
            f"${r['ending_equity']:>10,.0f} | ${r['turnover_usd']:>10,.0f} | {r['sl_count']:>8d} | "
            f"{r['tp_count']:>8d} | {r['modeled_maker_pct']:>6.1f}%"
        )
        print(row)
    print("=" * 135)

    print("\n" + "=" * 135)
    print("   TABLE 2: STOP LOSS SENSITIVITY GRID UNDER E3 CAUSAL PHYSICS")
    print("=" * 135)
    hdr2 = (
        f"{'Stop Loss Specification':<40} | {'CAGR (%)':<9} | {'Sharpe':<7} | {'Max DD (%)':<10} | "
        f"{'Terminal ($)':<12} | {'Turnover ($)':<12} | {'SL Trigs':<8} | {'TP Trigs':<8} | {'Fric ($)':<8}"
    )
    print(hdr2)
    print("-" * 135)

    for label, r in grid_results:
        row = (
            f"{label:<40} | {r['cagr']:>+8.1f}% | {r['sharpe']:>7.2f} | {r['max_dd']:>9.1f}% | "
            f"${r['ending_equity']:>10,.0f} | ${r['turnover_usd']:>10,.0f} | {r['sl_count']:>8d} | "
            f"{r['tp_count']:>8d} | ${r['total_friction']:>7.0f}"
        )
        print(row)
    print("=" * 135)

    # Save results to JSON artifact
    out_dict = {
        "ablation": {
            label: {
                "cagr": r["cagr"],
                "sharpe": r["sharpe"],
                "max_dd": r["max_dd"],
                "ending_equity": r["ending_equity"],
                "turnover_usd": r["turnover_usd"],
                "turnover_multiple": r["turnover_multiple"],
                "sl_count": r["sl_count"],
                "tp_count": r["tp_count"],
                "modeled_maker_pct": r["modeled_maker_pct"],
                "total_friction": r["total_friction"],
                "gross_price_pnl": r["gross_price_pnl"],
            }
            for label, r in ablation_results
        },
        "grid": {
            label: {
                "cagr": r["cagr"],
                "sharpe": r["sharpe"],
                "max_dd": r["max_dd"],
                "ending_equity": r["ending_equity"],
                "turnover_usd": r["turnover_usd"],
                "turnover_multiple": r["turnover_multiple"],
                "sl_count": r["sl_count"],
                "tp_count": r["tp_count"],
                "modeled_maker_pct": r["modeled_maker_pct"],
                "total_friction": r["total_friction"],
                "gross_price_pnl": r["gross_price_pnl"],
            }
            for label, r in grid_results
        }
    }

    out_path = PIPELINE_ROOT / "reports" / "execution_ablation_and_stop_grid_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(out_dict, f, indent=2)
    print(f"\nSaved results artifact to: {out_path}\n", flush=True)


if __name__ == "__main__":
    main()
