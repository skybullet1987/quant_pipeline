#!/usr/bin/env python3
"""
Decoupled Multi-Speed Clock Architecture Benchmark
===================================================
Compares:
  1. Synchronized 72h Clock: Core, EXP-109, and EXP-104.1 all tied to 72h rebalance timer.
  2. Decoupled Multi-Speed Clock:
     - Core 16-leg momentum on Slow 72h Clock (H=18 bars, deadband-gated)
     - EXP-109 Short-Only on Fast 4H Scanner with dynamic exit (funding < +25% APR or 24h dwell)
     - EXP-104.1 Macro Beta Hedge on Fast 4H Instantaneous De-Escalation Clock
  3. Continuous 4H Smoothing (Config D Master Ablation baseline)
"""

import sys
import os
import math
import time
from pathlib import Path
from typing import Dict, List, Tuple, Any

PIPELINE_ROOT = Path("/home/skybullet1987/quant_pipeline")
sys.path.insert(0, str(PIPELINE_ROOT))

import polars as pl
import numpy as np

from backtest_10x_convex_compounding import (
    PointInTimeUniverseManager,
    BENCHMARK_SYMBOL,
    EVAL_START_TS,
)
from scripts.run_unified_full_stack_ablation import (
    precompute_market_matrices,
    calculate_window_metrics,
    MAKER_FEE_BASE,
    TAKER_FEE_BASE,
    REBALANCE_MAKER_RATIO,
    REBALANCE_TAKER_RATIO,
    SLIPPAGE_BASE,
    SLIPPAGE_IMPACT_COEFF,
    SLIPPAGE_REF_NOTIONAL,
)

DATA_LAKE_PATH = PIPELINE_ROOT / "data" / "lake" / "raw_candles_4h.parquet"


def simulate_multispeed_clock(
    pdata: Dict[str, Any],
    symbols: List[str],
    total_eval_bars: int = 2284,
    clock_mode: str = "decoupled",  # "synchronized_72h", "decoupled_multispeed", "continuous_4h"
    sat_alloc: float = 0.004,
) -> Dict[str, Any]:
    """
    Simulates portfolio across the 2,284-bar canonical + holdout dataset
    under different clock decoupling regimes.
    """
    returns_mat = pdata["returns_mat"]
    close_mat = pdata["close_mat"]
    oracle_mat = pdata["oracle_mat"]
    atr_mat = pdata["atr_mat"]
    valid_mask = pdata["valid_mask"]
    eval_start_idx = pdata["eval_start_idx"]
    btc_idx = pdata["btc_idx"]
    eth_idx = pdata["eth_idx"]
    n_symbols = pdata["n_symbols"]

    btc_close = pdata["btc_close"]
    btc_returns = pdata["btc_returns"]
    eth_returns = pdata["eth_returns"]
    btc_atr = pdata["btc_atr"]
    btc_ema20 = pdata["btc_ema20"]
    btc_ema50 = pdata["btc_ema50"]
    btc_adx14 = pdata["btc_adx14"]
    v_oi_24h = pdata["v_oi_24h"]
    basis_disp = pdata["basis_disp"]
    basis_disp_mean = pdata["basis_disp_mean"]
    basis_disp_sigma = pdata["basis_disp_sigma"]
    z_jump_series = pdata["z_jump_series"]
    rolling_betas = pdata["rolling_betas"]
    rolling_idio_inv_vol = pdata["rolling_idio_inv_vol"]
    funding_mat = pdata["funding_mat"]

    op_leverage = 3.0
    theta_floor = 0.20
    initial_capital = 10000.0
    equity = initial_capital
    ratcheted_hwm = initial_capital
    peak_equity = initial_capital
    peak_bar = 0

    equity_curve = [equity]
    target_weights_prev = np.zeros(n_symbols)
    frozen_core_weights = np.zeros(n_symbols)
    bars_since_macro = 18  # Trigger macro on first bar

    beta_hedge_active = False
    btc_hedge_notional = 0.0
    eth_hedge_notional = 0.0

    # Satellite active tracking: {symbol: {"entry_bar": int, "weight": float}}
    active_satellites: Dict[int, Dict[str, Any]] = {}

    total_friction_usd = 0.0
    total_trades_count = 0
    total_turnover_usd = 0.0

    MACRO_CADENCE_BARS = 18  # 72 hours (18 x 4H bars)
    LELAND_DEADBAND = 0.05   # 5% rebalancing deadband

    for bar_count in range(total_eval_bars):
        t_idx = eval_start_idx + bar_count
        next_t_idx = min(t_idx + 1, len(returns_mat) - 1)

        # -------------------------------------------------------------
        # 1. Macro Beta Hedge MTM (EXP-104.1)
        # -------------------------------------------------------------
        if beta_hedge_active:
            r_b = btc_returns[next_t_idx]
            r_e = eth_returns[next_t_idx]
            h_pnl = (btc_hedge_notional * r_b) + (eth_hedge_notional * r_e)
            equity += h_pnl

        # -------------------------------------------------------------
        # 2. Continuous Ratchet & Concave Cushion (EXP-104.1)
        # -------------------------------------------------------------
        if equity > peak_equity:
            peak_equity = equity
            peak_bar = bar_count

        if equity >= ratcheted_hwm:
            ratcheted_hwm = equity
        else:
            if (bar_count - peak_bar) > 18:
                decay_rate = 0.05 / 2190.0
                ratcheted_hwm *= math.exp(-decay_rate)

        capital_floor = (1.0 - theta_floor) * ratcheted_hwm
        cushion_dollars = max(0.0, equity - capital_floor)
        max_cushion = theta_floor * ratcheted_hwm + 1e-12
        cushion_ratio = float(np.clip(cushion_dollars / max_cushion, 0.0, 1.0))

        # -------------------------------------------------------------
        # 3. Macro Stress & Hedge Evaluation Clock
        # -------------------------------------------------------------
        # Fast Hedge Clock: In "decoupled_multispeed" and "continuous_4h", evaluate every 4H bar.
        # Synchronized 72h Clock: Only evaluate every 18 bars (72 hours).
        is_macro_bar = (bars_since_macro >= MACRO_CADENCE_BARS)

        is_oi_flush = v_oi_24h[t_idx] < -0.10
        is_basis_disloc = basis_disp[t_idx] > (basis_disp_mean[t_idx] + 2.50 * max(basis_disp_sigma[t_idx], 1e-6))
        atr_norm = btc_atr[t_idx] / max(btc_close[t_idx], 1e-4)
        is_toxic = (z_jump_series[t_idx] > 2.576) and (btc_returns[t_idx] < -1.50 * atr_norm)
        stress_active = (is_oi_flush or is_basis_disloc) and is_toxic
        is_expansion = (btc_close[t_idx] > btc_ema50[t_idx] and btc_ema20[t_idx] > btc_ema50[t_idx] and btc_adx14[t_idx] > 22.0)

        hedge_eval_now = True if clock_mode != "synchronized_72h" else is_macro_bar

        if hedge_eval_now:
            if beta_hedge_active and not stress_active:
                can_deescalate = (v_oi_24h[t_idx] > 0.0 and btc_returns[t_idx] > 0.50 * atr_norm)
                if can_deescalate:
                    beta_hedge_active = False
                    btc_hedge_notional = 0.0
                    eth_hedge_notional = 0.0

            if stress_active:
                beta_hedge_active = True
                b_btc = rolling_betas[t_idx]
                b_eth = np.ones(n_symbols) * 0.8
                net_beta_btc = float(np.sum(target_weights_prev * b_btc))
                net_beta_eth = float(np.sum(target_weights_prev * b_eth))
                tot_notional = equity * op_leverage
                btc_hedge_notional = -0.70 * net_beta_btc * tot_notional
                eth_hedge_notional = -0.30 * net_beta_eth * tot_notional
            elif not beta_hedge_active:
                btc_hedge_notional = 0.0
                eth_hedge_notional = 0.0

        # -------------------------------------------------------------
        # 4. Tradable Mask & Alpha Generation
        # -------------------------------------------------------------
        tradable_mask_bar = valid_mask[t_idx] & (close_mat[t_idx] > 0)
        ret_24h = np.nan_to_num((close_mat[t_idx] / close_mat[max(0, t_idx-6)]) - 1.0, nan=0.0)
        ret_72h = np.nan_to_num((close_mat[t_idx] / close_mat[max(0, t_idx-18)]) - 1.0, nan=0.0)
        basis_spread = np.nan_to_num((close_mat[t_idx] - oracle_mat[t_idx]) / (oracle_mat[t_idx] + 1e-8), nan=0.0)
        vol_compress = np.nan_to_num(atr_mat[t_idx] / (close_mat[t_idx] + 1e-8), nan=0.0)

        funding_apr = funding_mat[t_idx] * 24.0 * 365.25
        dp_24h_atr = np.zeros(n_symbols)
        for si in range(n_symbols):
            if atr_mat[t_idx, si] > 1e-8 and close_mat[t_idx, si] > 0:
                dp_24h_atr[si] = abs(ret_24h[si] * close_mat[t_idx, si]) / atr_mat[t_idx, si]

        crowded_longs = funding_apr > 1.05
        if np.sum(tradable_mask_bar) >= 2:
            mom_raw_pre = ret_24h + ret_72h
            m_mean_pre = np.nanmean(mom_raw_pre[tradable_mask_bar])
            m_std_pre = np.nanstd(mom_raw_pre[tradable_mask_bar]) + 1e-8
            z_mom_pre = np.nan_to_num((mom_raw_pre - m_mean_pre) / m_std_pre)

            carry_exempt = (z_mom_pre > 2.50) & (dp_24h_atr > 2.0) & (funding_apr < 5.0)
            crowded_longs = crowded_longs & (~carry_exempt)

        tradable_mask_bar = tradable_mask_bar & (~crowded_longs)

        # Cross-sectional funding z-score
        if np.sum(tradable_mask_bar) >= 5:
            f_m = float(np.nanmean(funding_apr[tradable_mask_bar]))
            f_s = float(np.nanstd(funding_apr[tradable_mask_bar])) + 1e-8
            z_f = (funding_apr - f_m) / f_s
        else:
            z_f = np.zeros(n_symbols)

        # -------------------------------------------------------------
        # 5. Core Portfolio Optimization Clock
        # -------------------------------------------------------------
        betas = rolling_betas[t_idx]
        eff_lev = op_leverage * min(1.0, cushion_ratio / 0.20)

        if clock_mode == "continuous_4h":
            # Continuous 4H Core Rebalance (as in previous ablation)
            if np.sum(tradable_mask_bar) >= 2:
                mom_raw = ret_24h + ret_72h
                m_mean = np.nanmean(mom_raw[tradable_mask_bar])
                m_std = np.nanstd(mom_raw[tradable_mask_bar]) + 1e-8
                z_mom = np.nan_to_num((mom_raw - m_mean) / m_std)

                b_mean = np.nanmean(basis_spread[tradable_mask_bar])
                b_std = np.nanstd(basis_spread[tradable_mask_bar]) + 1e-8
                z_basis = np.nan_to_num(-(basis_spread - b_mean) / b_std)

                v_mean = np.nanmean(vol_compress[tradable_mask_bar])
                v_std = np.nanstd(vol_compress[tradable_mask_bar]) + 1e-8
                z_vol = np.nan_to_num((vol_compress - v_mean) / v_std)
            else:
                z_mom = np.zeros(n_symbols)
                z_basis = np.zeros(n_symbols)
                z_vol = np.zeros(n_symbols)

            alpha_vec = 0.60 * z_mom + 0.25 * z_basis + 0.15 * z_vol
            squeeze_cands = (funding_apr < -0.70) & (v_oi_24h[t_idx] > 0.15)
            alpha_vec = np.where(squeeze_cands, alpha_vec * 1.50, alpha_vec)
            alpha_vec = alpha_vec * rolling_idio_inv_vol[t_idx]
            max_a = np.nanmax(np.abs(alpha_vec)) + 1e-8
            alpha_vec = np.nan_to_num(0.05 * (alpha_vec / max_a), nan=0.0)
            alpha_vec[~tradable_mask_bar] = 0.0

            if eff_lev > 1e-4 and np.sum(tradable_mask_bar) >= 2:
                raw_w = (alpha_vec / 1.5) + 0.35 * target_weights_prev
                net_b = float(np.sum(raw_w * betas))
                target_b = 0.80 if is_expansion else 0.0
                diff_b = net_b - target_b
                raw_w -= (diff_b / (np.sum(betas**2) + 1e-8)) * betas
                raw_w = np.clip(raw_w, -0.25, 0.25)
                raw_w[~tradable_mask_bar] = 0.0
                tot_gross = np.sum(np.abs(raw_w))
                core_weights = raw_w * (eff_lev / tot_gross) if tot_gross > 1e-5 else np.zeros(n_symbols)
            else:
                core_weights = np.zeros(n_symbols)
        else:
            # Slow 72h Clock: Recompute core targets ONLY when is_macro_bar
            if is_macro_bar:
                bars_since_macro = 0
                if np.sum(tradable_mask_bar) >= 2:
                    mom_raw = ret_24h + ret_72h
                    m_mean = np.nanmean(mom_raw[tradable_mask_bar])
                    m_std = np.nanstd(mom_raw[tradable_mask_bar]) + 1e-8
                    z_mom = np.nan_to_num((mom_raw - m_mean) / m_std)

                    b_mean = np.nanmean(basis_spread[tradable_mask_bar])
                    b_std = np.nanstd(basis_spread[tradable_mask_bar]) + 1e-8
                    z_basis = np.nan_to_num(-(basis_spread - b_mean) / b_std)

                    v_mean = np.nanmean(vol_compress[tradable_mask_bar])
                    v_std = np.nanstd(vol_compress[tradable_mask_bar]) + 1e-8
                    z_vol = np.nan_to_num((vol_compress - v_mean) / v_std)
                else:
                    z_mom = np.zeros(n_symbols)
                    z_basis = np.zeros(n_symbols)
                    z_vol = np.zeros(n_symbols)

                alpha_vec = 0.60 * z_mom + 0.25 * z_basis + 0.15 * z_vol
                squeeze_cands = (funding_apr < -0.70) & (v_oi_24h[t_idx] > 0.15)
                alpha_vec = np.where(squeeze_cands, alpha_vec * 1.50, alpha_vec)
                alpha_vec = alpha_vec * rolling_idio_inv_vol[t_idx]
                max_a = np.nanmax(np.abs(alpha_vec)) + 1e-8
                alpha_vec = np.nan_to_num(0.05 * (alpha_vec / max_a), nan=0.0)
                alpha_vec[~tradable_mask_bar] = 0.0

                if eff_lev > 1e-4 and np.sum(tradable_mask_bar) >= 2:
                    raw_w = (alpha_vec / 1.5) + 0.35 * frozen_core_weights
                    net_b = float(np.sum(raw_w * betas))
                    target_b = 0.80 if is_expansion else 0.0
                    diff_b = net_b - target_b
                    raw_w -= (diff_b / (np.sum(betas**2) + 1e-8)) * betas
                    raw_w = np.clip(raw_w, -0.25, 0.25)
                    raw_w[~tradable_mask_bar] = 0.0
                    tot_gross = np.sum(np.abs(raw_w))
                    frozen_core_weights = raw_w * (eff_lev / tot_gross) if tot_gross > 1e-5 else np.zeros(n_symbols)
                else:
                    frozen_core_weights = np.zeros(n_symbols)
            else:
                bars_since_macro += 1
                # If cushion dropped to zero (cash floor entered between macro bars), de-gear Core
                if cushion_ratio <= 0.0:
                    frozen_core_weights = np.zeros(n_symbols)

            core_weights = frozen_core_weights.copy()

        # -------------------------------------------------------------
        # 6. EXP-112 Unified Recycler (EXP-109 Short-Only)
        # -------------------------------------------------------------
        sat_turnover_usd = 0.0
        target_weights = core_weights.copy()

        if cushion_ratio <= 0.0:
            core_gross = float(np.sum(np.abs(core_weights)))
            idle_lev = max(0.0, op_leverage - core_gross)

            if clock_mode == "synchronized_72h":
                # Synchronized: Only scan and trade on macro bars (every 18 bars = 72h)
                if is_macro_bar and idle_lev >= 0.20:
                    sat_w = np.zeros(n_symbols)
                    basis_apr = basis_spread * 0.125 * 24.0 * 365.25

                    exp109_cands = []
                    for si in range(n_symbols):
                        if tradable_mask_bar[si] and si not in (btc_idx, eth_idx):
                            if (funding_apr[si] > 1.00) or (basis_apr[si] > 1.00) or (z_f[si] > 1.80):
                                is_veto = (z_mom_pre[si] > 2.50) and (dp_24h_atr[si] > 2.0)
                                if not is_veto:
                                    exp109_cands.append((si, max(funding_apr[si], basis_apr[si]), z_f[si]))
                    exp109_cands.sort(key=lambda x: (x[1], x[2]), reverse=True)
                    k = min(3, len(exp109_cands))
                    if k >= 1:
                        w_each = min(sat_alloc, idle_lev * 0.3) / k
                        for si, _, _ in exp109_cands[:k]:
                            sat_w[si] -= w_each
                        sat_b = float(betas @ sat_w)
                        if abs(sat_b) > 0.005:
                            sat_w[btc_idx] -= sat_b
                        sat_turnover_usd = float(np.sum(np.abs(sat_w))) * equity
                        target_weights = target_weights + sat_w

            elif clock_mode == "decoupled_multispeed":
                # Decoupled Multi-Speed Clock:
                # Evaluates on EVERY 4H bar!
                # Dynamic Exit Rule:
                #   1. Funding mean-reverts below +25% APR (z_F < 0.50)
                #   2. Max dwell time of 24h (6 bars) reached
                basis_apr = basis_spread * 0.125 * 24.0 * 365.25

                # A. Evaluate exits for existing active satellites
                expired_sats = []
                for si, info in list(active_satellites.items()):
                    entry_bar = info["entry_bar"]
                    dwell_bars = bar_count - entry_bar
                    is_mean_reverted = (funding_apr[si] < 0.25) or (z_f[si] < 0.50)
                    is_expired = (dwell_bars >= 6)  # 24 hours (6 x 4H bars)
                    if is_mean_reverted or is_expired or (not tradable_mask_bar[si]):
                        expired_sats.append(si)

                for si in expired_sats:
                    del active_satellites[si]

                # B. Scan for new entries on every 4H bar if capacity available
                current_sat_count = len(active_satellites)
                if current_sat_count < 3 and idle_lev >= 0.20:
                    exp109_cands = []
                    for si in range(n_symbols):
                        if tradable_mask_bar[si] and si not in (btc_idx, eth_idx) and si not in active_satellites:
                            if (funding_apr[si] > 1.00) or (basis_apr[si] > 1.00) or (z_f[si] > 1.80):
                                is_veto = (z_mom_pre[si] > 2.50) and (dp_24h_atr[si] > 2.0)
                                if not is_veto:
                                    exp109_cands.append((si, max(funding_apr[si], basis_apr[si]), z_f[si]))
                    exp109_cands.sort(key=lambda x: (x[1], x[2]), reverse=True)

                    slots_available = 3 - current_sat_count
                    for si, _, _ in exp109_cands[:slots_available]:
                        w_slot = min(sat_alloc, idle_lev * 0.3) / 3.0
                        active_satellites[si] = {
                            "entry_bar": bar_count,
                            "weight": -w_slot,
                        }

                # C. Construct satellite weight vector and neutralize beta
                sat_w = np.zeros(n_symbols)
                for si, info in active_satellites.items():
                    sat_w[si] = info["weight"]

                if np.sum(np.abs(sat_w)) > 0:
                    sat_b = float(betas @ sat_w)
                    if abs(sat_b) > 0.005:
                        sat_w[btc_idx] -= sat_b

                sat_turnover_usd = float(np.sum(np.abs(sat_w))) * equity
                target_weights = target_weights + sat_w

            elif clock_mode == "continuous_4h":
                # Continuous 4H (Ablation master style)
                if idle_lev >= 0.20:
                    sat_w = np.zeros(n_symbols)
                    basis_apr = basis_spread * 0.125 * 24.0 * 365.25
                    exp109_cands = []
                    for si in range(n_symbols):
                        if tradable_mask_bar[si] and si not in (btc_idx, eth_idx):
                            if (funding_apr[si] > 1.00) or (basis_apr[si] > 1.00) or (z_f[si] > 1.80):
                                is_veto = (z_mom_pre[si] > 2.50) and (dp_24h_atr[si] > 2.0)
                                if not is_veto:
                                    exp109_cands.append((si, max(funding_apr[si], basis_apr[si]), z_f[si]))
                    exp109_cands.sort(key=lambda x: (x[1], x[2]), reverse=True)
                    k = min(3, len(exp109_cands))
                    if k >= 1:
                        w_each = min(sat_alloc, idle_lev * 0.3) / k
                        for si, _, _ in exp109_cands[:k]:
                            sat_w[si] -= w_each
                        sat_b = float(betas @ sat_w)
                        if abs(sat_b) > 0.005:
                            sat_w[btc_idx] -= sat_b
                        sat_turnover_usd = float(np.sum(np.abs(sat_w))) * equity
                        target_weights = target_weights + sat_w
        else:
            # If not in cash floor, clear any residual satellites
            active_satellites.clear()

        # -------------------------------------------------------------
        # 7. Friction & Mark-to-Market Accounting
        # -------------------------------------------------------------
        turnover_delta = np.sum(np.abs(target_weights - target_weights_prev))
        turnover_usd = turnover_delta * equity
        total_turnover_usd += turnover_usd

        # Count trades
        trade_mask = np.abs(target_weights - target_weights_prev) > 1e-5
        total_trades_count += int(np.sum(trade_mask))

        rebal_maker = (turnover_usd * REBALANCE_MAKER_RATIO) * MAKER_FEE_BASE
        rebal_taker = (turnover_usd * REBALANCE_TAKER_RATIO) * TAKER_FEE_BASE

        if sat_turnover_usd > 0:
            # Model 2A OFI Passive Maker limit execution (+3.35 bps savings, zero taker impact)
            friction = max(0.0, (rebal_maker + rebal_taker) - sat_turnover_usd * 0.000335)
        else:
            rebal_impact = 0.0
            for i in range(n_symbols):
                dw = abs(target_weights[i] - target_weights_prev[i])
                if dw > 1e-5:
                    n_i = dw * equity
                    rebal_impact += n_i * (SLIPPAGE_BASE + SLIPPAGE_IMPACT_COEFF * math.sqrt(n_i / SLIPPAGE_REF_NOTIONAL))
            friction = rebal_maker + rebal_taker + rebal_impact

        total_friction_usd += friction

        # Returns & Funding
        bar_trading = 0.0
        bar_funding = 0.0
        for i in range(n_symbols):
            w_i = target_weights[i]
            if abs(w_i) > 1e-5:
                notional = w_i * equity
                bar_trading += notional * returns_mat[next_t_idx, i]
                h_f = float(np.nan_to_num(np.clip(funding_mat[next_t_idx, i], -0.0005, 0.0005), nan=0.0000125))
                bar_funding -= notional * (h_f * 4.0)

        bar_net = bar_trading + bar_funding - friction
        equity += bar_net
        equity_curve.append(equity)
        target_weights_prev = target_weights

    eq_arr = np.array(equity_curve)
    metrics_full = calculate_window_metrics(eq_arr, total_eval_bars)
    metrics_fold3 = calculate_window_metrics(eq_arr[1620:1891], 270)
    metrics_tail = calculate_window_metrics(eq_arr[2190:2285], 94)

    # Calculate monthly friction in bps/month
    # Total eval bars: 2,284 x 4H = 9,136h = 380.67 days = 12.51 months
    total_months = (total_eval_bars * 4.0) / (24.0 * 30.4375)
    mean_equity = float(np.mean(eq_arr))
    total_friction_bps = (total_friction_usd / mean_equity) * 10000.0
    monthly_friction_bps = total_friction_bps / total_months

    return {
        "clock_mode": clock_mode,
        "full_sample": metrics_full,
        "fold3": metrics_fold3,
        "holdout_tail": metrics_tail,
        "monthly_friction_bps": round(monthly_friction_bps, 2),
        "total_friction_usd": round(total_friction_usd, 2),
        "total_trades_count": total_trades_count,
        "total_turnover_usd": round(total_turnover_usd, 2),
    }


def main():
    print("=" * 110)
    print("   APEX CLOCK ARCHITECTURE BENCHMARK: SYNCHRONIZED 72H VS DECOUPLED MULTI-SPEED   ")
    print("   Dataset: 2,284 Bars (Canonical 2,190 + Independent 94-Bar Holdout Tail)   ")
    print("=" * 110)

    # 1. Load Data Lake
    df_raw = pl.read_parquet(DATA_LAKE_PATH)
    btc_df = df_raw.filter(pl.col("symbol") == BENCHMARK_SYMBOL).sort("timestamp_ms")
    all_timestamps = btc_df["timestamp_ms"].to_list()
    total_bars = 2284

    eval_timestamps, symbols, full_market_data = PointInTimeUniverseManager.load_pit_market_matrices(
        df=df_raw,
        eval_start_ts=EVAL_START_TS,
        eval_end_ts=all_timestamps[-1],
        benchmark_symbol=BENCHMARK_SYMBOL,
    )
    valid_mask = full_market_data["valid_price_mask"]
    first_valid_indices = np.zeros(len(symbols), dtype=int)
    for col in range(len(symbols)):
        valid_idx = np.where(valid_mask[:, col])[0]
        first_valid_indices[col] = valid_idx[0] if len(valid_idx) > 0 else 0
    full_market_data["first_valid_indices"] = first_valid_indices

    print("--> Precomputing Market Matrices...")
    pdata = precompute_market_matrices(full_market_data, symbols, total_bars)

    # 2. Run Clock Architectures
    regimes = [
        ("Synchronized 72h Clock (Core + EXP-109 + 104.1 on 72h)", "synchronized_72h"),
        ("Decoupled Multi-Speed Clock (72h Core / 4H EXP-109 & 104.1)", "decoupled_multispeed"),
        ("Continuous 4H Baseline (Ablation Reference)", "continuous_4h"),
    ]

    results = {}
    for label, mode in regimes:
        print(f"\n[RUNNING CLOCK REGIME] {label} ...")
        t0 = time.time()
        res = simulate_multispeed_clock(pdata, symbols, total_bars, clock_mode=mode)
        elapsed = time.time() - t0
        res["elapsed_sec"] = round(elapsed, 2)
        results[mode] = res

        mf = res["full_sample"]
        m3 = res["fold3"]
        mt = res["holdout_tail"]
        print(f"  --> Full Sample: CAGR {mf['annualized_cagr_pct']:>+6.1f}%, Sharpe {mf['sharpe_ratio']:>5.2f}, MDD {mf['max_drawdown_pct']:>5.1f}%")
        print(f"  --> Fold 3:      Sharpe {m3['sharpe_ratio']:>+5.2f}, Return {m3['net_return_pct']:>+6.1f}%, MDD {m3['max_drawdown_pct']:>5.1f}%")
        print(f"  --> Holdout (94b): Return {mt['net_return_pct']:>+6.1f}%, Sharpe {mt['sharpe_ratio']:>+6.2f}, MDD {mt['max_drawdown_pct']:>5.1f}%")
        print(f"  --> Monthly Friction: {res['monthly_friction_bps']:>5.1f} bps/mo | Trades: {res['total_trades_count']} | Elapsed: {elapsed:.2f}s")

    # 3. Print Comprehensive Comparison Table
    print("\n" + "=" * 135)
    print(f"{'CLOCK ARCHITECTURE REGIME':<50} | {'CAGR':<8} | {'SHARPE':<7} | {'MDD':<7} | {'FOLD3 RET':<10} | {'TAIL RET':<9} | {'FRICTION':<11} | {'TRADES':<7}")
    print("=" * 135)
    for label, mode in regimes:
        r = results[mode]
        mf = r["full_sample"]
        m3 = r["fold3"]
        mt = r["holdout_tail"]
        print(f"{label:<50} | {mf['annualized_cagr_pct']:>6.1f}% | {mf['sharpe_ratio']:>6.2f}  | {mf['max_drawdown_pct']:>5.1f}% | {m3['net_return_pct']:>8.1f}%  | {mt['net_return_pct']:>7.1f}% | {r['monthly_friction_bps']:>7.1f} bps | {r['total_trades_count']:>6}")
    print("=" * 135)


if __name__ == "__main__":
    main()
