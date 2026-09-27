#!/usr/bin/env python3
"""
MASTER COMPENDIUM STRATEGY AUDIT & 7-GATE CERTIFICATION TOURNAMENT
==================================================================
Runs the primary strategies from MASTER_RESEARCH_AND_BACKTESTS_COMPENDIUM.md
through the IronCore Institutional Certification Gauntlet.

Evaluated Systems:
1. Gen 10 Unconstrained Two-Tranche (+1,035% CAGR claim)
2. HyperCore Apex Canonical (+92.6% CAGR claim)
3. Tranche A: F1 Remediated Funding Carry (1.5x Gross)
4. Tranche B: F5 Residual Momentum (Standalone Trend)
5. System 0: Baseline RD-ACE-C (1.0x Momentum + Carry)
6. System 12: Target Volatility Gearing (sigma_target = 25%)
7. Alpha-4C: Pairwise Cointegration Stat-Arb
8. Negative Control: Pure Gaussian Noise Baseline
"""

import sys
import os
import math
import time
from pathlib import Path
from typing import Dict, List, Tuple, Any

import numpy as np
import pandas as pd
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


def generate_compendium_strategies(
    close_mat: np.ndarray,
    oracle_mat: np.ndarray,
    volume_mat: np.ndarray,
    valid_mask: np.ndarray,
    returns_mat: np.ndarray,
    predicted_funding: np.ndarray,
    symbols: List[str],
    btc_idx: int,
) -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
    """
    Constructs (weights_matrix, signal_matrix) for each major strategy from the compendium.
    """
    n_bars, n_symbols = close_mat.shape
    btc_rets = returns_mat[:, btc_idx]

    # 144H Macro Trend (36 bars)
    macro_trend_144 = np.zeros_like(close_mat)
    for i in range(36, n_bars):
        macro_trend_144[i] = (close_mat[i] / (close_mat[i-36] + 1e-12)) - 1.0

    # Rolling Open Interest proxy
    oi_mat = np.zeros_like(volume_mat)
    for i in range(12, n_bars):
        oi_mat[i] = np.sum(volume_mat[i-12:i], axis=0)

    # Precompute F5 Residual Momentum
    f5_signal = np.zeros((n_bars, n_symbols))
    lookback = 18
    for t in range(lookback + 2, n_bars):
        mask_t = valid_mask[t]
        if np.sum(mask_t) < 8:
            continue
        r_w = returns_mat[t - lookback:t, :]
        b_w = btc_rets[t - lookback:t]
        b_var = np.var(b_w) + 1e-8
        for i in range(n_symbols):
            if not mask_t[i]:
                continue
            cov_ib = np.cov(r_w[:, i], b_w)[0, 1]
            beta = cov_ib / b_var
            residuals = r_w[:, i] - beta * b_w
            res_vol = np.std(residuals) + 1e-8
            f5_signal[t, i] = np.sum(residuals) / res_vol

    # Precompute F1 Remediated Funding Carry
    f1_signal = np.zeros((n_bars, n_symbols))
    for t in range(n_bars):
        mask_t = valid_mask[t]
        if np.sum(mask_t) < 8:
            continue
        fund_t = predicted_funding[t, mask_t]
        f1_signal[t, mask_t] = - (fund_t - np.mean(fund_t))

    strategies = {}

    # -------------------------------------------------------------
    # 1. Tranche A: F1 Remediated Funding Carry (1.5x Gross Market-Neutral)
    # -------------------------------------------------------------
    w_f1 = np.zeros((n_bars, n_symbols))
    for t in range(0, n_bars, 6):
        mask_t = valid_mask[t]
        if np.sum(mask_t) >= 16:
            v_idx = np.where(mask_t)[0]
            scores = f1_signal[t, v_idx]
            ord_idx = np.argsort(scores)
            top_k = 8
            shorts = v_idx[ord_idx[:top_k]]
            longs = v_idx[ord_idx[-top_k:]]
            w_bar = np.zeros(n_symbols)
            w_bar[longs] = 0.75 / top_k
            w_bar[shorts] = -0.75 / top_k
            for f in range(t, min(t + 6, n_bars)):
                w_f1[f] = w_bar
    strategies["F1 Remediated Carry (1.5x)"] = (w_f1, f1_signal)

    # -------------------------------------------------------------
    # 2. Tranche B: F5 Residual Momentum (Standalone Trend)
    # -------------------------------------------------------------
    w_f5 = np.zeros((n_bars, n_symbols))
    for t in range(0, n_bars, 6):
        mask_t = valid_mask[t]
        if np.sum(mask_t) >= 16:
            v_idx = np.where(mask_t)[0]
            scores = f5_signal[t, v_idx]
            ord_idx = np.argsort(scores)
            top_k = 8
            shorts = v_idx[ord_idx[:top_k]]
            longs = v_idx[ord_idx[-top_k:]]
            w_bar = np.zeros(n_symbols)
            w_bar[longs] = 0.75 / top_k
            w_bar[shorts] = -0.75 / top_k
            for f in range(t, min(t + 6, n_bars)):
                w_f5[f] = w_bar
    strategies["F5 Residual Momentum (1.5x)"] = (w_f5, f5_signal)

    # -------------------------------------------------------------
    # 3. Combined Apex Architecture (60% Carry Core + 40% Macro Breakout)
    # -------------------------------------------------------------
    w_apex = np.zeros((n_bars, n_symbols))
    sig_apex = 0.5 * f1_signal + 0.5 * f5_signal
    for t in range(0, n_bars):
        mask_t = valid_mask[t]
        if np.sum(mask_t) < 16:
            continue
        v_idx = np.where(mask_t)[0]
        # Tranche A rebalanced every 6 bars
        if t % 6 == 0:
            s_blend = sig_apex[t, v_idx]
            ord_a = np.argsort(s_blend)
            k_a = 8
            w_a = np.zeros(n_symbols)
            w_a[v_idx[ord_a[-k_a:]]] = (0.60 * 1.50 * 0.5) / k_a
            w_a[v_idx[ord_a[:k_a]]] = - (0.60 * 1.50 * 0.5) / k_a
        else:
            w_a = w_apex[t-1] * 0.60

        # Tranche B Macro Breakout
        sq_eligible = mask_t & (predicted_funding[t] <= 0.000150)
        w_b = np.zeros(n_symbols)
        if np.sum(sq_eligible) >= 5:
            sq_idx = np.where(sq_eligible)[0]
            macro_s = macro_trend_144[t, sq_idx]
            top_5 = sq_idx[np.argsort(macro_s)[-5:]]
            w_b[top_5] = 0.80 / 5.0

        w_apex[t] = w_a + w_b
    strategies["HyperCore Apex Canonical"] = (w_apex, sig_apex)

    # -------------------------------------------------------------
    # 4. Gen 10 Unconstrained Two-Tranche (High Leverage 3.5x B-Expansion)
    # -------------------------------------------------------------
    w_gen10 = np.zeros((n_bars, n_symbols))
    for t in range(0, n_bars):
        mask_t = valid_mask[t]
        if np.sum(mask_t) < 16:
            continue
        v_idx = np.where(mask_t)[0]
        # 50% Tranche A at 1.5x = 0.75 gross
        s_blend = sig_apex[t, v_idx]
        ord_a = np.argsort(s_blend)
        k_a = 8
        w_a = np.zeros(n_symbols)
        w_a[v_idx[ord_a[-k_a:]]] = 0.375 / k_a
        w_a[v_idx[ord_a[:k_a]]] = -0.375 / k_a

        # 50% Tranche B expanded to 3.5x leverage = 1.75 gross directional
        w_b = np.zeros(n_symbols)
        sq_eligible = mask_t & (predicted_funding[t] <= 0.000150)
        if np.sum(sq_eligible) >= 5:
            sq_idx = np.where(sq_eligible)[0]
            macro_s = macro_trend_144[t, sq_idx]
            top_5 = sq_idx[np.argsort(macro_s)[-5:]]
            w_b[top_5] = 1.75 / 5.0

        w_gen10[t] = w_a + w_b
    strategies["Gen 10 (Unconstrained 10x Claim)"] = (w_gen10, sig_apex)

    # -------------------------------------------------------------
    # 5. System 0: Baseline RD-ACE-C (1.0x Gross Momentum + Carry)
    # -------------------------------------------------------------
    w_sys0 = np.zeros((n_bars, n_symbols))
    for t in range(0, n_bars, 6):
        mask_t = valid_mask[t]
        if np.sum(mask_t) >= 16:
            v_idx = np.where(mask_t)[0]
            s_blend = sig_apex[t, v_idx]
            ord_a = np.argsort(s_blend)
            k = 8
            w_bar = np.zeros(n_symbols)
            w_bar[v_idx[ord_a[-k:]]] = 0.50 / k
            w_bar[v_idx[ord_a[:k]]] = -0.50 / k
            for f in range(t, min(t + 6, n_bars)):
                w_sys0[f] = w_bar
    strategies["System 0: Baseline RD-ACE-C (1.0x)"] = (w_sys0, sig_apex)

    # -------------------------------------------------------------
    # 6. System 12: Target Volatility Gearing (sigma_target = 25%)
    # -------------------------------------------------------------
    w_sys12 = np.zeros((n_bars, n_symbols))
    for t in range(0, n_bars, 6):
        mask_t = valid_mask[t]
        if np.sum(mask_t) >= 16:
            v_idx = np.where(mask_t)[0]
            s_blend = 0.7 * f1_signal[t, v_idx] + 0.3 * f5_signal[t, v_idx]
            ord_a = np.argsort(s_blend)
            k = 8
            hist_rets = returns_mat[max(0, t-36):t, :]
            port_vol = np.std(np.mean(hist_rets, axis=1)) * np.sqrt(365 * 6) + 1e-4
            target_vol = 0.25
            vol_gear = np.clip(target_vol / port_vol, 0.40, 1.60)

            w_bar = np.zeros(n_symbols)
            w_bar[v_idx[ord_a[-k:]]] = (0.50 * vol_gear) / k
            w_bar[v_idx[ord_a[:k]]] = -(0.50 * vol_gear) / k
            for f in range(t, min(t + 6, n_bars)):
                w_sys12[f] = w_bar
    strategies["System 12 (Target Vol 25%)"] = (w_sys12, sig_apex)

    # -------------------------------------------------------------
    # 7. Alpha-4C: Pairwise Cointegration Stat-Arb
    # -------------------------------------------------------------
    w_stat_arb = np.zeros((n_bars, n_symbols))
    # Spread mean reversion between highly correlated assets
    if n_symbols >= 10:
        asset_a = 1  # ETH proxy
        asset_b = 0  # BTC benchmark
        spread = np.zeros(n_bars)
        for t in range(36, n_bars):
            p_a = np.log(np.maximum(close_mat[t-36:t, asset_a], 1e-4))
            p_b = np.log(np.maximum(close_mat[t-36:t, asset_b], 1e-4))
            beta = np.cov(p_a, p_b)[0, 1] / (np.var(p_b) + 1e-8)
            curr_spread = p_a[-1] - beta * p_b[-1]
            spread_mean = np.mean(p_a - beta * p_b)
            spread_std = np.std(p_a - beta * p_b) + 1e-6
            z_score = (curr_spread - spread_mean) / spread_std
            # Mean reversion
            if z_score > 1.5:
                w_stat_arb[t, asset_a] = -0.25
                w_stat_arb[t, asset_b] = 0.25 * beta
            elif z_score < -1.5:
                w_stat_arb[t, asset_a] = 0.25
                w_stat_arb[t, asset_b] = -0.25 * beta
    sig_stat_arb = np.zeros((n_bars, n_symbols))
    sig_stat_arb[:, :2] = 0.1
    strategies["Alpha-4C Pairwise Stat-Arb"] = (w_stat_arb, sig_stat_arb)

    # -------------------------------------------------------------
    # 8. Negative Control: Pure Gaussian Noise Baseline
    # -------------------------------------------------------------
    np.random.seed(1337)
    w_noise = np.zeros((n_bars, n_symbols))
    sig_noise = np.random.randn(n_bars, n_symbols)
    for t in range(0, n_bars, 6):
        mask_t = valid_mask[t]
        if np.sum(mask_t) >= 16:
            v_idx = np.where(mask_t)[0]
            scores = sig_noise[t, v_idx]
            ord_a = np.argsort(scores)
            k = 8
            w_bar = np.zeros(n_symbols)
            w_bar[v_idx[ord_a[-k:]]] = 0.50 / k
            w_bar[v_idx[ord_a[:k]]] = -0.50 / k
            for f in range(t, min(t + 6, n_bars)):
                w_noise[f] = w_bar
    strategies["Negative Control (Pure Noise)"] = (w_noise, sig_noise)

    return strategies


def main():
    print("=" * 120)
    print("   IRONCORE MASTER BACKTESTER: COMPENDIUM STRATEGIES TOURNAMENT")
    print("   Evaluating Master Compendium Algos Across the 7-Gate Institutional Gauntlet")
    print("=" * 120)

    # 1. Load Point-in-Time Market Matrices
    df = pl.read_parquet(DATA_LAKE_PATH)
    _, symbols, market_data = PointInTimeUniverseManager.load_pit_market_matrices(
        df=df, eval_start_ts=EVAL_START_TS, eval_end_ts=EVAL_END_TS, benchmark_symbol=BENCHMARK_SYMBOL
    )

    close_mat = market_data["close"].copy()
    oracle_mat = market_data["oracle"].copy()
    volume_mat = market_data["volume"].copy()
    valid_mask = market_data["valid_price_mask"].copy()
    timestamps = market_data["timestamps"]
    
    btc_idx = symbols.index(BENCHMARK_SYMBOL) if BENCHMARK_SYMBOL in symbols else 0
    btc_prices = close_mat[:, btc_idx]

    prev_close = np.roll(close_mat, 1, axis=0)
    returns_mat = np.nan_to_num(np.where(prev_close > 0, (close_mat / prev_close) - 1.0, 0.0))
    returns_mat[0] = 0.0
    predicted_funding = (close_mat - oracle_mat) / (oracle_mat + 1e-8) + 0.000125

    print(f"\n[DATASET READY] Loaded {len(timestamps)} bars across {len(symbols)} symbols.")
    
    # 2. Build candidate strategy weights
    print("[BUILDING CANDIDATE STRATEGY WEIGHTS...]")
    strategies = generate_compendium_strategies(
        close_mat, oracle_mat, volume_mat, valid_mask, returns_mat, predicted_funding, symbols, btc_idx
    )
    print(f"Generated weight matrices for {len(strategies)} candidate strategies.")

    # 3. Configure IronCore Engine
    # Set mc_placebo_draws=150 (Resolution floor = 1/151 = 0.0066 < 0.0100)
    # Set bootstrap_paths=1000 for rapid tournament execution
    config = IronCoreConfig_v1(
        mc_placebo_draws=150,
        bootstrap_paths=1000,
        initial_capital=10000.0,
    )
    engine = IronCoreEngine(config=config)

    results = []

    print("\n" + "=" * 125)
    print(f"{'STRATEGY NAME':<34} | {'CAGR':<8} | {'SHARPE':<6} | {'MAX DD':<7} | {'FRIC RATIO':<10} | {'P(PERM)':<7} | {'DSR':<6} | {'VERDICT':<7}")
    print("-" * 125)

    for strat_name, (w_mat, sig_mat) in strategies.items():
        t0 = time.time()
        cert = engine.run_full_certification_gauntlet(
            candidate_name=strat_name,
            weights_matrix=w_mat,
            signal_matrix=sig_mat,
            returns_mat=returns_mat,
            predicted_funding=predicted_funding,
            volume_mat=volume_mat,
            close_mat=close_mat,
            oracle_mat=oracle_mat,
            valid_mask=valid_mask,
            btc_prices=btc_prices,
        )
        elapsed = time.time() - t0

        p = cert["performance"]
        gates = cert["gates"]
        v_str = cert["overall_verdict"]

        p_perm = cert["placebos"]["asset_permutation"]["empirical_p_value"]
        p_noise = cert["placebos"]["horizon_matched_random"]["empirical_p_value"]
        dsr = cert["dsr_metrics"]["deflated_sharpe_ratio"]
        ruin = cert["ruin_analysis"]["ruin_probability"]

        failed = [g.split("(")[1].split(")")[0] for g, passed in gates.items() if not passed]
        failed_str = ", ".join(failed) if failed else "None"

        print(f"{strat_name:<34} | {p['cagr']:>7.2f}% | {p['sharpe']:>6.2f} | {p['max_dd']:>6.2f}% | {p['fric_ratio']:>8.2f}% | {p_perm:>7.4f} | {dsr:>6.4f} | {v_str:<7}")

        results.append({
            "name": strat_name,
            "verdict": v_str,
            "cagr": p["cagr"],
            "sharpe": p["sharpe"],
            "max_dd": p["max_dd"],
            "turnover": p["turnover"],
            "friction_ratio": p["fric_ratio"],
            "p_perm": p_perm,
            "p_noise": p_noise,
            "ruin_prob": ruin,
            "dsr": dsr,
            "failed_gates": failed_str,
            "gates_dict": gates,
            "elapsed": elapsed
        })

    print("=" * 125)

    # 4. Print Detailed Forensic Breakdown
    print("\n\n" + "=" * 125)
    print("                         FORENSIC GATE-BY-GATE TOURNAMENT AUDIT")
    print("=" * 125)
    for r in results:
        status_icon = "[PASSED]" if r["verdict"] == "PASSED" else "[KILLED]"
        print(f"\n>>> {r['name']}: {status_icon}")
        print(f"    CAGR: {r['cagr']:.2f}% | Sharpe: {r['sharpe']:.2f} | Max DD: {r['max_dd']:.2f}% | Turnover: {r['turnover']:.1f}x")
        print(f"    Friction Ratio: {r['friction_ratio']:.2f}% of Gross (Gate 3 Max <= 25.0%)")
        print(f"    Asset Permutation p-val: {r['p_perm']:.4f} | Random Noise p-val: {r['p_noise']:.4f} (Gate 2 Req < 0.0100)")
        print(f"    Ruin Probability: {r['ruin_prob']*100:.2f}% (Gate 6 Max <= 5.0%) | DSR: {r['dsr']:.4f} (Gate 7 Req >= 0.9500)")
        print(f"    Failed Gates: {r['failed_gates']}")

    print("\n" + "=" * 125)


if __name__ == "__main__":
    main()
