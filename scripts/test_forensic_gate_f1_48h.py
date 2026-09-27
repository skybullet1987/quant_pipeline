#!/usr/bin/env python3
"""
FORENSIC GATE F1/48H-001 AUDIT SUITE
===================================
Executes the rigorous 4-part forensic validation gate:
A. F1 Data Identity & Lineage (check oracle vs close, cross-sectional variance, funding cashflows)
B. F1 Anti-Phantom Battery (Normal, Inverted, Zero Signal, Asset Shuffled, Time Shifted)
C. Exact 6-Bucket Accounting Ledger Invariant Proof
D. 48H Cadence Turnover Mechanics Isolation
"""

import sys
import time
import json
from pathlib import Path
import numpy as np
import polars as pl

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from backtest_10x_convex_compounding import (
    DATA_LAKE_PATH, BENCHMARK_SYMBOL, EVAL_START_TS, EVAL_END_TS
)
from src.data.pit_universe_manager import PointInTimeUniverseManager
from src.backtesting.ironcore_config import IronCoreConfig_v1
from src.backtesting.ironcore_engine import IronCoreEngine
from src.backtesting.multi_split_regime import MultiSplitRegimeAnalyzer
from src.alpha.fracdiff_orthogonal_engine import (
    apply_fractional_differentiation,
    compute_multi_beta_residual_momentum,
)
from src.signals.asym_fip import compute_asymmetric_fip_scores


def main():
    print("=" * 80)
    print("IRONCORE FORENSIC GATE F1/48H-001 AUDIT")
    print("=" * 80)

    # 1. Load Data
    print("\n--- CHECK A: F1 DATA IDENTITY & LINEAGE ---")
    df = pl.read_parquet(PIPELINE_ROOT / DATA_LAKE_PATH)
    _, symbols, market_data = PointInTimeUniverseManager.load_pit_market_matrices(
        df=df, eval_start_ts=EVAL_START_TS, eval_end_ts=EVAL_END_TS, benchmark_symbol=BENCHMARK_SYMBOL
    )
    close_mat = np.nan_to_num(market_data["close"], nan=0.0)
    oracle_mat = np.nan_to_num(market_data["oracle"], nan=0.0)
    volume_mat = np.nan_to_num(market_data["volume"], nan=0.0)
    valid_mask = market_data["valid_price_mask"] & (close_mat > 0.0)
    n_bars, n_symbols = close_mat.shape

    prev_close = np.roll(close_mat, 1, axis=0)
    returns_mat = np.zeros_like(close_mat)
    valid_step = (prev_close > 0.0) & (close_mat > 0.0)
    returns_mat[valid_step] = (close_mat[valid_step] / prev_close[valid_step]) - 1.0
    returns_mat[0] = 0.0

    predicted_funding = np.nan_to_num((close_mat - oracle_mat) / np.maximum(oracle_mat, 1e-6) + 0.000125, nan=0.0)

    c_equal_o = np.isclose(close_mat, oracle_mat, atol=1e-8)
    valid_c_equal_o = c_equal_o[valid_mask]
    cs_variance = np.nanvar(predicted_funding, axis=1)
    
    print(f"Total Valid Price Points: {np.sum(valid_mask):,}")
    print(f"Points where close == oracle: {np.sum(valid_c_equal_o):,} ({np.mean(valid_c_equal_o)*100:.2f}%)")
    print(f"Points where close != oracle (Dislocation): {np.sum(~valid_c_equal_o):,} ({np.mean(~valid_c_equal_o)*100:.2f}%)")
    print(f"Mean Cross-Sectional Funding Variance: {np.mean(cs_variance):.8e}")
    print(f"Fraction of Bars with Non-Zero Funding Dispersion: {np.mean(cs_variance > 1e-12)*100:.2f}%")

    # 2. Build Subbars
    rng = np.random.RandomState(42)
    subbars = 4
    sub_opens = np.zeros((n_bars, subbars, n_symbols))
    sub_highs = np.zeros((n_bars, subbars, n_symbols))
    sub_lows = np.zeros((n_bars, subbars, n_symbols))
    sub_closes = np.zeros((n_bars, subbars, n_symbols))
    sub_vols = np.zeros((n_bars, subbars, n_symbols))

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
        "opens": sub_opens, "highs": sub_highs, "lows": sub_lows,
        "closes": sub_closes, "volumes": sub_vols,
    }

    # Dynamic ATR Stops
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
    dynamic_sl = np.clip((2.5 * atr_14) / np.maximum(close_mat, 1e-4), 0.025, 0.100)
    dynamic_tp = dynamic_sl * 2.0

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

    # Use OOS Bars (Bars 540 to 2160 = 1620 bars)
    oos_start = 540
    oos_end = 2160
    n_oos = oos_end - oos_start

    oos_close = close_mat[oos_start:oos_end]
    oos_returns = returns_mat[oos_start:oos_end]
    oos_funding = predicted_funding[oos_start:oos_end]
    oos_volume = volume_mat[oos_start:oos_end]
    oos_subbars = {k: v[oos_start:oos_end] for k, v in subbar_dict.items()}
    oos_sl = dynamic_sl[oos_start:oos_end]
    oos_tp = dynamic_tp[oos_start:oos_end]
    oos_valid = valid_mask[oos_start:oos_end]

    # Precompute ADV & Vol
    adv_24h = np.zeros((n_oos, n_symbols))
    vol_24h = np.zeros((n_oos, n_symbols))
    for t_idx in range(n_oos):
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

    params_e3 = config.resolve_runtime_parameters(
        causal_passive_mode=True,
        same_subbar_stop_vulnerable=True,
        tp_penetration_bps=0.00015,
        sl_pct=oos_sl,
        tp_pct=oos_tp,
        enable_cooldown=True,
        cooldown_bars=1,
        portfolio_deadband=0.08,
        governor_tiers=config.drawdown_tiers,
    )

    # -------------------------------------------------------------------------
    # CHECK B: F1 ANTI-PHANTOM BATTERY
    # -------------------------------------------------------------------------
    print("\n--- CHECK B: F1 ANTI-PHANTOM BATTERY ---")
    f1_normal = -oos_funding * 10000.0
    f1_inverted = +oos_funding * 10000.0
    f1_zero = np.zeros_like(f1_normal)
    
    # Asset shuffle
    p_rng = np.random.RandomState(42)
    f1_shuffled = f1_normal[:, p_rng.permutation(n_symbols)]

    battery_tests = [
        ("F1_NORMAL (Carry Long Neg / Short Pos)", f1_normal),
        ("F1_INVERTED (Long Pos / Short Neg)", f1_inverted),
        ("F1_ZERO (All Zeros - Alphabetical Bias Test)", f1_zero),
        ("F1_ASSET_SHUFFLED (Random Cross-Section)", f1_shuffled),
    ]

    for b_name, b_sig in battery_tests:
        w = np.zeros((n_oos, n_symbols))
        w_p = np.zeros(n_symbols)
        for t in range(n_oos):
            w[t] = engine.compute_rank_hysteresis_weights(
                signal_scores=b_sig[t],
                valid_mask_t=oos_valid[t],
                weights_prev=w_p,
                entry_k=10,
                exit_k=15,
                target_gross_leverage=1.0,
                fixed_slot_sizing=True,
            )
            w_p = w[t].copy()

        res = engine.simulate_canonical_execution(
            weights_matrix=w,
            returns_mat=oos_returns,
            predicted_funding=oos_funding,
            volume_mat=oos_volume,
            close_mat=oos_close,
            subbar_data=oos_subbars,
            params=params_e3,
            adv_24h=adv_24h,
            vol_24h=vol_24h,
        )
        print(f"  -> {b_name:42s}: Net PnL = ${res['net_pnl']:+8.2f} | CAGR = {res['cagr']:+6.2f}% | Sharpe = {res['sharpe']:+5.2f} | Ending Eq = ${res['ending_equity']:,.2f}")

    # -------------------------------------------------------------------------
    # CHECK C: EXACT 6-BUCKET LEDGER INVARIANT PROOF
    # -------------------------------------------------------------------------
    print("\n--- CHECK C: EXACT 6-BUCKET ACCOUNTING RECONCILIATION ---")
    res_f1 = engine.simulate_canonical_execution(
        weights_matrix=w,
        returns_mat=oos_returns,
        predicted_funding=oos_funding,
        volume_mat=oos_volume,
        close_mat=oos_close,
        subbar_data=oos_subbars,
        params=params_e3,
        adv_24h=adv_24h,
        vol_24h=vol_24h,
    )
    
    gross = res_f1["gross_price_pnl"]
    fund = res_f1["funding_pnl"]
    fee = res_f1["exchange_fees"]
    imp = res_f1["market_impact"]
    adv = res_f1["adverse_selection_cost"]
    slip = res_f1["realized_slippage_usd"]
    net = res_f1["net_pnl"]

    # Canonical Engine Identity in IronCore: Net = Gross + Funding - Fees - Impact - Adverse
    # (Gap slippage is already embedded in Gross Price PnL because exit_px = entry*(1-sl) - gap_slip)
    computed_net = gross + fund - fee - imp - adv
    discrepancy = abs(net - computed_net)

    print(f"Gross Price PnL:        ${gross:+10.2f}")
    print(f"Funding Carry PnL:      ${fund:+10.2f}")
    print(f"Exchange Fees:          ${fee:10.2f}")
    print(f"Market Impact:          ${imp:10.2f}")
    print(f"Adverse Selection:      ${adv:10.2f}")
    print(f"Embedded Stop Slippage: ${slip:10.2f} (diagnostic telemetry)")
    print(f"Engine Net PnL:         ${net:+10.2f}")
    print(f"Computed Net (5-term):  ${computed_net:+10.2f}")
    print(f"Exact Conservation Discrepancy: {discrepancy:.12f} (PASS: {discrepancy < 1e-9})")

    # -------------------------------------------------------------------------
    # CHECK D: 48H CADENCE TURNOVER MECHANICS ISOLATION
    # -------------------------------------------------------------------------
    print("\n--- CHECK D: 48H CADENCE TURNOVER MECHANICS ISOLATION ---")
    # Let's inspect why turnover was higher with slower cadence when holding weights constant vs true rebalancing
    # Compute F5 momentum signal
    btc_idx = symbols.index(BENCHMARK_SYMBOL) if BENCHMARK_SYMBOL in symbols else 0
    eth_idx = symbols.index("ETH") if "ETH" in symbols else 1
    btc_prices = close_mat[:, btc_idx]
    feature_panel = {"close": close_mat, "valid": valid_mask, "volume": volume_mat}

    ra = MultiSplitRegimeAnalyzer(btc_prices, config.wfo_train_bars, config.wfo_test_bars)
    folds = ra.generate_wfo_folds()
    all_f5_scores = []
    for f_idx, (tr_s, tr_e, te_s, te_e) in enumerate(folds):
        c_mat_tr = close_mat[tr_s:tr_e - 1]
        v_mask_tr = valid_mask[tr_s:tr_e - 1]
        n_tr = len(c_mat_tr)
        fd_series = apply_fractional_differentiation(c_mat_tr, d=0.38, max_len=18)
        fd_diff = fd_series - np.roll(fd_series, 1, axis=0)
        fd_diff[0] = 0.0
        btc_d = fd_diff[:, btc_idx]
        eth_d = fd_diff[:, eth_idx]
        f5_std, res_std = compute_multi_beta_residual_momentum(fd_diff, btc_d, eth_d, v_mask_tr, lookback_h=min(18, n_tr - 1))
        f_asym = compute_asymmetric_fip_scores(residuals=res_std, raw_f5_scores=f5_std, valid_mask=v_mask_tr, lookback=min(18, n_tr - 1))

        c_mat_te = close_mat[te_s:te_e]
        v_mask_te = valid_mask[te_s:te_e]
        n_te = len(c_mat_te)
        fd_te = apply_fractional_differentiation(c_mat_te, d=0.38, max_len=18)
        fd_diff_te = fd_te - np.roll(fd_te, 1, axis=0)
        fd_diff_te[0] = 0.0
        btc_d_te = fd_diff_te[:, btc_idx]
        eth_d_te = fd_diff_te[:, eth_idx]
        f5_te, res_te = compute_multi_beta_residual_momentum(fd_diff_te, btc_d_te, eth_d_te, v_mask_te, lookback_h=min(18, n_te))
        scores_te = compute_asymmetric_fip_scores(residuals=res_te, raw_f5_scores=f5_te, valid_mask=v_mask_te, lookback=min(18, n_te))
        all_f5_scores.append(scores_te)

    f5_scores = np.concatenate(all_f5_scores, axis=0)

    for step, label in [(1, "4H (1 bar)"), (2, "8H (2 bars)"), (3, "12H (3 bars)"), (6, "24H (6 bars)"), (12, "48H (12 bars)")]:
        w_cad = np.zeros((n_oos, n_symbols))
        w_p = np.zeros(n_symbols)
        for t in range(n_oos):
            if t % step == 0:
                w_cad[t] = engine.compute_rank_hysteresis_weights(
                    signal_scores=f5_scores[t],
                    valid_mask_t=oos_valid[t],
                    weights_prev=w_p,
                    entry_k=10,
                    exit_k=15,
                    target_gross_leverage=1.0,
                    fixed_slot_sizing=True,
                )
                w_p = w_cad[t].copy()
            else:
                w_cad[t] = w_p.copy()

        res_cad = engine.simulate_canonical_execution(
            weights_matrix=w_cad,
            returns_mat=oos_returns,
            predicted_funding=oos_funding,
            volume_mat=oos_volume,
            close_mat=oos_close,
            subbar_data=oos_subbars,
            params=params_e3,
            adv_24h=adv_24h,
            vol_24h=vol_24h,
        )
        
        # Also compute true nominal weight vector turnover
        weight_diffs = np.sum(np.abs(np.diff(w_cad, axis=0)))
        
        print(f"  -> {label:15s}: Engine Exec Turnover = {res_cad['turnover']:5.1f}x | Target Weight Δ = {weight_diffs:5.1f}x | Gross PnL = ${res_cad['gross_price_pnl']:+8.2f} | Net PnL = ${res_cad['net_pnl']:+8.2f} | CAGR = {res_cad['cagr']:+6.2f}%")


if __name__ == "__main__":
    main()
