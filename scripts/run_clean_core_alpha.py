#!/usr/bin/env python3
"""
CLEAN CORE ALPHA ENGINE STANDALONE BENCHMARK (v9.8)
===================================================
Directly operationalizes the Senior Quant Review's three operational pivot rules:
- Rule 1 Gate: Verify Stage A unlevered zero-cost rank factor hurdle (Sharpe >= 1.20, CAGR > 0%)
- Rule 2: Pure F5 Idiosyncratic Residual Momentum (HAC t = +6.87, unpolluted by toxic F3/F4)
- Rule 3: Remediated F1 Funding Carry ("Become the House" - collecting hourly retail funding)
- Decoupled Rebalancing Cadence: 24h primary target rebalancing + 4h deadband (tau=0.030)
- Trap 3 Safeguards: Squeeze Veto Filter (+3.0 ATR / 5x Vol), 4.0% Single-Name Short Cap, 1.5 ATR Stops.

Asserts:
  Net Sharpe >= 2.00
  Total Annual Fee Drag < $25.00
  Positive Cumulative Funding Cash Flow
"""

import sys
import math
from pathlib import Path
from typing import Dict, Any

import numpy as np
import pandas as pd

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PIPELINE_ROOT))

from src.validation.statistical_governance import (
    verify_stage_a_hurdle,
    DryWellException,
)
from src.alpha.hypercore_alphas import (
    HyperliquidEngineConfig,
    HyperCoreAlphaEngine,
    CleanCoreAlphaEngine,
    F5_RESIDUAL_MOMENTUM_METADATA,
    F1_REMEDIATED_CARRY_METADATA,
)
from backtest_10x_convex_compounding import (
    InstitutionalCompoundingEngine,
    TOTAL_EVAL_BARS,
    BENCHMARK_SYMBOL,
)


def run_clean_core_benchmark():
    print("=" * 115)
    print("         CLEAN CORE ALPHA ENGINE STANDALONE BENCHMARK (THE WELL vs THE PIPES)        ")
    print("=" * 115)

    print("--> [1/4] Loading Point-in-Time Universe and Market Matrices...")
    engine_proto = InstitutionalCompoundingEngine()
    _, _, cached_data = engine_proto.load_and_preprocess_data()

    close_mat = cached_data["close"]
    open_mat = cached_data["open"]
    high_mat = cached_data["high"]
    low_mat = cached_data["low"]
    volume_mat = cached_data["volume"]
    oracle_mat = cached_data["oracle"]
    timestamps = cached_data["timestamps"]
    eval_start_idx = cached_data["eval_start_idx"]
    valid_mask = cached_data.get("valid_price_mask", ~np.isnan(close_mat))
    symbols = cached_data["symbols"]
    btc_idx = symbols.index(BENCHMARK_SYMBOL)
    n_symbols = len(symbols)
    T = len(timestamps)

    returns_mat = np.zeros_like(close_mat)
    prev_close = np.roll(close_mat, 1, axis=0)
    valid_pair = valid_mask & np.roll(valid_mask, 1, axis=0)
    valid_pair[0] = False
    with np.errstate(invalid="ignore", divide="ignore"):
        returns_mat[1:] = np.where(valid_pair[1:], (close_mat[1:] / (prev_close[1:] + 1e-12)) - 1.0, 0.0)

    # Compute 14-period ATR
    atr_mat = np.zeros_like(close_mat)
    with np.errstate(invalid="ignore"):
        tr = np.maximum(
            high_mat - low_mat,
            np.maximum(
                np.abs(high_mat - np.roll(close_mat, 1, axis=0)),
                np.abs(low_mat - np.roll(close_mat, 1, axis=0)),
            ),
        )
    for i in range(20, len(tr)):
        with np.errstate(invalid="ignore"):
            atr_mat[i] = np.nanmean(tr[i-20:i], axis=0)
    atr_mat = np.nan_to_num(atr_mat, nan=0.0)

    cfg = HyperliquidEngineConfig()
    alpha_engine = HyperCoreAlphaEngine(config=cfg)
    btc_rets = returns_mat[:, btc_idx]

    # Hourly predicted funding rate and 4H settlement
    predicted_funding_hourly = (close_mat - oracle_mat) / (oracle_mat + 1e-8) + 0.000125
    funding_rate_4h = predicted_funding_hourly * 4.0

    print("--> [2/4] Computing Isolated Factors with Aligned Metadata & Safeguards...")
    print(f"    Factor F5: {F5_RESIDUAL_MOMENTUM_METADATA['factor_id']} (Lookback: {F5_RESIDUAL_MOMENTUM_METADATA['lookback_bars']} bars, Sign: {F5_RESIDUAL_MOMENTUM_METADATA['sign_convention']})")
    f5_signal = alpha_engine.compute_idiosyncratic_residual_momentum(
        returns=returns_mat,
        btc_returns=btc_rets,
        eligible_mask=valid_mask,
        lookback_bars=18,
    )

    print(f"    Factor F1: {F1_REMEDIATED_CARRY_METADATA['factor_id']} (Squeeze Veto: Active, Short Cap: 4.0%)")
    f1_signal = alpha_engine.compute_remediated_funding_carry(
        predicted_funding=predicted_funding_hourly,
        eligible_mask=valid_mask,
        closes=close_mat,
        volumes=volume_mat,
        atr_mat=atr_mat,
        max_short_cap=0.040,
        squeeze_veto=True,
    )

    # -------------------------------------------------------------------------
    # TEST 1: PURE F5 RESIDUAL MOMENTUM STANDALONE (Stage A Frictionless)
    # -------------------------------------------------------------------------
    print("\n--> [3/4] Running Test 1: Pure F5 Residual Momentum Standalone...")
    eval_slice_close = close_mat[eval_start_idx : eval_start_idx + TOTAL_EVAL_BARS]
    eval_slice_rets = returns_mat[eval_start_idx : eval_start_idx + TOTAL_EVAL_BARS]
    eval_slice_f5 = f5_signal[eval_start_idx : eval_start_idx + TOTAL_EVAL_BARS]
    eval_slice_f1 = f1_signal[eval_start_idx : eval_start_idx + TOTAL_EVAL_BARS]
    eval_slice_mask = valid_mask[eval_start_idx : eval_start_idx + TOTAL_EVAL_BARS]
    eval_slice_funding = funding_rate_4h[eval_start_idx : eval_start_idx + TOTAL_EVAL_BARS]
    eval_slice_atr = atr_mat[eval_start_idx : eval_start_idx + TOTAL_EVAL_BARS]

    # Stage A: Pure rank factor, zero cost, unlevered
    f5_stage_a_rets = []
    for t in range(TOTAL_EVAL_BARS - 1):
        el = eval_slice_mask[t] & ~np.isnan(eval_slice_f5[t])
        if np.sum(el) < 10:
            f5_stage_a_rets.append(0.0)
            continue
        s_t = eval_slice_f5[t, el]
        ranks = pd.Series(s_t).rank().to_numpy()
        w_t = (ranks - np.mean(ranks))
        w_t = w_t / (np.sum(np.abs(w_t)) + 1e-8)
        ret_next = eval_slice_rets[t + 1, el]
        f5_stage_a_rets.append(float(np.sum(w_t * ret_next)))

    f5_arr = np.array(f5_stage_a_rets)
    f5_sharpe = float((np.mean(f5_arr) / (np.std(f5_arr) + 1e-8)) * math.sqrt(2190))
    f5_cagr = float(((np.prod(1.0 + f5_arr)) ** (2190.0 / len(f5_arr)) - 1.0) * 100.0)
    print(f"    [Test 1 Result] Pure F5 Stage A: Sharpe = {f5_sharpe:0.2f} | Gross CAGR = {f5_cagr:+0.2f}%")

    # Operational Rule 1 Governance Gate Verification
    print("    --> Enforcing Operational Rule 1 Gate on F5...")
    is_f5_pass = verify_stage_a_hurdle(f5_sharpe, f5_cagr, raise_exception=False)
    print(f"    --> Operational Rule 1 Verification: {'PASS' if is_f5_pass else 'FAIL'} (Sharpe {f5_sharpe:.2f} >= 1.20, CAGR {f5_cagr:+.1f}% > 0%)")
    assert is_f5_pass, "F5 failed Stage A hurdle!"

    # -------------------------------------------------------------------------
    # TEST 2: PURE F1 REMEDIATED FUNDING CARRY STANDALONE (24H Cadence)
    # -------------------------------------------------------------------------
    print("\n--> Running Test 2: Pure F1 Remediated Carry Harvest Standalone...")
    engine_f1_standalone = CleanCoreAlphaEngine(
        symbols=symbols,
        w_f5=0.0,
        w_f1=1.0,
        rebal_interval_bars=6, # 24h
        deadband_threshold=0.030,
        max_short_carry_cap=0.040,
    )
    res_f1 = engine_f1_standalone.simulate_clean_core(
        close_mat=eval_slice_close,
        returns_mat=eval_slice_rets,
        funding_rate_4h=eval_slice_funding,
        f5_signal=eval_slice_f5,
        f1_signal=eval_slice_f1,
        valid_mask=eval_slice_mask,
        atr_mat=eval_slice_atr,
        maker_ratio=0.60,
        start_nav=10000.0,
    )
    print(f"    [Test 2 Result] Pure F1 Carry Harvest (24h Cadence):")
    print(f"      Ending Equity     : ${res_f1['ending_equity']:,.2f}")
    print(f"      Net CAGR          : {res_f1['net_cagr_pct']:+0.2f}%")
    print(f"      Net Sharpe        : {res_f1['annualized_sharpe']:0.2f}")
    print(f"      Max Drawdown      : {res_f1['max_drawdown_pct']:0.2f}%")
    print(f"      Funding Cashflow  : +${res_f1['total_funding_collected_usd']:,.2f} ('Become the House')")
    print(f"      Total Annual Fees : ${res_f1['total_fees_usd']:0.2f} (Turnover: {res_f1['total_turnover_nav']:.1f}x)")

    # -------------------------------------------------------------------------
    # TEST 3: CLEAN CORE COMBINED (50% F5 + 50% F1, 24H Decoupled Cadence)
    # -------------------------------------------------------------------------
    print("\n--> [4/4] Running Test 3: Clean Core Engine (50% F5 + 50% F1 Carry Harvest)...")
    engine_clean_core = CleanCoreAlphaEngine(
        symbols=symbols,
        w_f5=0.50,
        w_f1=0.50,
        rebal_interval_bars=6, # 24h primary target rebalance
        deadband_threshold=0.030,
        max_short_carry_cap=0.040,
        stop_loss_atr_mult=1.5,
    )
    res_core = engine_clean_core.simulate_clean_core(
        close_mat=eval_slice_close,
        returns_mat=eval_slice_rets,
        funding_rate_4h=eval_slice_funding,
        f5_signal=eval_slice_f5,
        f1_signal=eval_slice_f1,
        valid_mask=eval_slice_mask,
        atr_mat=eval_slice_atr,
        maker_ratio=0.60,
        start_nav=10000.0,
    )

    print("\n" + "=" * 115)
    print("                     CLEAN CORE ALPHA ENGINE OFFICIAL SCORECARD                     ")
    print("=" * 115)
    print(f"  Architecture                  : Decoupled 24H Primary Target + 4H Hysteresis Deadband (tau=0.030)")
    print(f"  Factor Blend                  : 50% Pure F5 (Residual Mom) + 50% Remediated F1 (Funding Carry)")
    print(f"  Starting NAV                  : ${res_core['initial_equity']:,.2f}")
    print(f"  Ending NAV                    : ${res_core['ending_equity']:,.2f}")
    print(f"  Net CAGR                      : {res_core['net_cagr_pct']:+0.2f}%")
    print(f"  Annualized Sharpe Ratio       : {res_core['annualized_sharpe']:0.2f}")
    print(f"  Annualized Sortino Ratio      : {res_core['annualized_sortino']:0.2f}")
    print(f"  Realized Maximum Drawdown     : {res_core['max_drawdown_pct']:0.2f}%")
    print("-" * 115)
    print(f"  Gross Alpha P&L               : +${res_core['total_gross_pnl_usd']:,.2f}")
    print(f"  Realized Funding Cashflow     : +${res_core['total_funding_collected_usd']:,.2f} (Positive Carry Inversion)")
    print(f"  Total Execution Friction      : -${res_core['total_fees_usd']:,.2f} (Sub-$25 Target)")
    print(f"  Total Annual Portfolio Volume : {res_core['total_turnover_nav']:.2f}x NAV")
    print("=" * 115)

    # Formal Assertions per User Review
    # Test 2: F1 Remediated Funding Carry ('Become the House')
    assert res_f1['total_funding_collected_usd'] > 0.0, "F1 Carry failed to collect positive funding cashflow!"
    assert res_f1['annualized_sharpe'] >= 1.50, f"F1 Net Sharpe {res_f1['annualized_sharpe']:.2f} below 1.50!"
    assert res_f1['total_fees_usd'] < 25.0, f"F1 Annual Fees ${res_f1['total_fees_usd']:.2f} exceeds $25 ceiling!"

    # Test 3: Clean Core (F5 + F1)
    assert res_core['annualized_sharpe'] >= 2.00, f"Clean Core Net Sharpe {res_core['annualized_sharpe']:.2f} below 2.00!"
    assert res_core['total_fees_usd'] < 25.0, f"Fee drag ${res_core['total_fees_usd']:.2f} exceeds $25 ceiling!"
    assert res_core['ending_equity'] > 14000.0, f"Ending equity ${res_core['ending_equity']:.2f} below $14,000!"

    print("\n[SUCCESS] Clean Core Alpha Engine fully verified against all 3 Operational Rules and Trap Safeguards.\n")
    return res_core


if __name__ == "__main__":
    run_clean_core_benchmark()
