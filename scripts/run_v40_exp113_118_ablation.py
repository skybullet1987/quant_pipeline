#!/usr/bin/env python3
"""
APEX v4.0 Deep Research Ablation & Stress Test (EXP-113 through EXP-118)
========================================================================
Tests the exact progression from v3.8.2 (72H frozen cadence + asymmetric sieve)
through Certified Config D and each of the 6 Gemini Deep Research v4.0 upgrades:
  0. v3.8.2 Daemon Baseline (72H Freeze [18 bars], Asymmetric Long Starvation, Flat Brackets)
  1. + EXP-114 (Fast 4H Rolling Garleanu-Pedersen Cadence — Certified Config D Baseline)
  2. + EXP-113 (Symmetric Hurst/VR/FIP Persistence Sieve & Conviction Tilt)
  3. + EXP-115 (ATR-Scaled Volatility Brackets + 4-Stage Multi-ATR Runner Ratchet)
  4. + EXP-116 (Regime-Conditional Volatility-Targeted Convex Gearing under GZ Cushion)
  5. + EXP-117 & EXP-118 (Beta-Neutralized 4H Negative-Funding Squeeze Longs + Bipower Cascade Sleeves)
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import polars as pl

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from backtest_10x_convex_compounding import (
    BENCHMARK_SYMBOL,
    EVAL_START_TS,
    MAKER_FEE_BASE,
    REBALANCE_MAKER_RATIO,
    REBALANCE_TAKER_RATIO,
    SLIPPAGE_BASE,
    SLIPPAGE_IMPACT_COEFF,
    SLIPPAGE_REF_NOTIONAL,
    TAKER_FEE_BASE,
    PointInTimeUniverseManager,
)
from scripts.run_unified_full_stack_ablation import (
    calculate_window_metrics,
    precompute_market_matrices,
)

DATA_DIR = PIPELINE_ROOT / "data"
DATA_LAKE_PATH = PIPELINE_ROOT / "data" / "lake" / "raw_candles_4h.parquet"
OUT_JSON = DATA_DIR / "v40_exp113_118_ablation_results.json"


def precompute_v40_microstructure_matrices(
    full_market_data: Dict[str, Any], pdata: Dict[str, Any]
) -> Dict[str, Any]:
    """Precomputes rolling Hurst/VR/FIP persistence quality, Bipower jump ratios, and CLV for v4.0 ablation."""
    close_mat = pdata["close_mat"]
    high_mat = full_market_data["high"]
    low_mat = full_market_data["low"]
    volume_mat = full_market_data["volume"]
    returns_mat = pdata["returns_mat"]
    n_bars, n_symbols = close_mat.shape

    bar_range = np.maximum(high_mat - low_mat, 1e-8)
    clv_mat = np.where(
        (high_mat - low_mat) > 1e-8,
        ((close_mat - low_mat) - (high_mat - close_mat)) / bar_range,
        0.0,
    )

    pos_rets = (returns_mat > 0).astype(float)
    neg_rets = (returns_mat < 0).astype(float)
    fip_quality = np.zeros_like(close_mat)
    vr_mat = np.ones_like(close_mat)
    jump_ratio_mat = np.zeros_like(close_mat)
    sv_imb_mat = np.zeros_like(close_mat)
    vol_ratio_mat = np.ones_like(close_mat)
    high_6b_mat = np.zeros_like(close_mat)

    dollar_vol = close_mat * np.nan_to_num(volume_mat, nan=0.0)

    for i in range(n_symbols):
        r_col = np.nan_to_num(returns_mat[:, i], nan=0.0)
        s_pos = pd.Series(pos_rets[:, i]).rolling(18, min_periods=6).mean().to_numpy()
        s_neg = pd.Series(neg_rets[:, i]).rolling(18, min_periods=6).mean().to_numpy()
        fip_quality[:, i] = np.abs(s_pos - s_neg)

        r4 = pd.Series(r_col).rolling(4).sum().to_numpy()
        v1 = pd.Series(r_col).rolling(24, min_periods=8).var().to_numpy() + 1e-10
        v4 = pd.Series(r4).rolling(24, min_periods=8).var().to_numpy()
        vr_mat[:, i] = np.nan_to_num(v4 / (4.0 * v1), nan=1.0)

        r_abs = np.abs(r_col)
        rv_12 = pd.Series(r_col ** 2).rolling(12, min_periods=6).sum().to_numpy() + 1e-12
        bv_pair = r_abs * np.roll(r_abs, 1)
        bv_pair[0] = 0.0
        bv_12 = (math.pi / 2.0) * (12.0 / 11.0) * pd.Series(bv_pair).rolling(11, min_periods=5).sum().to_numpy()
        jump_ratio_mat[:, i] = np.clip((rv_12 - bv_12) / rv_12, 0.0, 1.0)

        rv_pos = pd.Series(np.where(r_col > 0, r_col ** 2, 0.0)).rolling(6, min_periods=3).sum().to_numpy()
        rv_neg = pd.Series(np.where(r_col < 0, r_col ** 2, 0.0)).rolling(6, min_periods=3).sum().to_numpy()
        sv_imb_mat[:, i] = (rv_pos - rv_neg) / (rv_pos + rv_neg + 1e-12)

        dv_col = dollar_vol[:, i]
        dv_ma18 = pd.Series(np.roll(dv_col, 1)).rolling(18, min_periods=6).mean().to_numpy() + 1e-8
        vol_ratio_mat[:, i] = np.nan_to_num(dv_col / dv_ma18, nan=1.0)

        high_6b_mat[:, i] = pd.Series(np.roll(close_mat[:, i], 1)).rolling(6, min_periods=3).max().to_numpy()

    pdata["high_mat"] = high_mat
    pdata["low_mat"] = low_mat
    pdata["clv_mat"] = clv_mat
    pdata["fip_quality"] = fip_quality
    pdata["vr_mat"] = vr_mat
    pdata["jump_ratio_mat"] = jump_ratio_mat
    pdata["sv_imb_mat"] = sv_imb_mat
    pdata["vol_ratio_mat"] = vol_ratio_mat
    pdata["high_6b_mat"] = high_6b_mat
    return pdata


def simulate_v40_ablation(
    pdata: Dict[str, Any],
    total_eval_bars: int,
    macro_cadence_bars: int = 1,
    enable_exp113_symmetric_sieve: bool = False,
    enable_exp115_atr_ratchet: bool = False,
    enable_exp116_convex_gearing: bool = False,
    enable_exp117_118_satellites: bool = False,
) -> Dict[str, Any]:
    """
    Exact Config D simulation from run_unified_full_stack_ablation.py with modular v4.0 Deep Research upgrades.
    """
    returns_mat = pdata["returns_mat"]
    close_mat = pdata["close_mat"]
    high_mat = pdata["high_mat"]
    low_mat = pdata["low_mat"]
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

    fip_quality = pdata["fip_quality"]
    vr_mat = pdata["vr_mat"]
    jump_ratio_mat = pdata["jump_ratio_mat"]
    sv_imb_mat = pdata["sv_imb_mat"]
    vol_ratio_mat = pdata["vol_ratio_mat"]
    high_6b_mat = pdata["high_6b_mat"]
    clv_mat = pdata["clv_mat"]

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
    bars_since_macro = macro_cadence_bars

    beta_hedge_active = False
    btc_hedge_notional = 0.0
    eth_hedge_notional = 0.0

    for bar_count in range(total_eval_bars):
        t_idx = eval_start_idx + bar_count
        next_t_idx = min(t_idx + 1, len(returns_mat) - 1)

        # 1. Macro Beta Hedge MTM (EXP-104.1)
        if beta_hedge_active:
            r_b = btc_returns[next_t_idx]
            r_e = eth_returns[next_t_idx]
            h_pnl = (btc_hedge_notional * r_b) + (eth_hedge_notional * r_e)
            equity += h_pnl

        # 2. Continuous Ratchet & Concave Cushion (EXP-104.1)
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

        # 3. Macro Stress & De-Escalation Gate (EXP-104.1)
        is_oi_flush = v_oi_24h[t_idx] < -0.10
        is_basis_disloc = basis_disp[t_idx] > (basis_disp_mean[t_idx] + 2.50 * max(basis_disp_sigma[t_idx], 1e-6))
        atr_norm = btc_atr[t_idx] / max(btc_close[t_idx], 1e-4)
        is_toxic = (z_jump_series[t_idx] > 2.576) and (btc_returns[t_idx] < -1.50 * atr_norm)
        stress_active = (is_oi_flush or is_basis_disloc) and is_toxic
        is_expansion = (
            btc_close[t_idx] > btc_ema50[t_idx]
            and btc_ema20[t_idx] > btc_ema50[t_idx]
            and btc_adx14[t_idx] > 22.0
        )

        # Operating Leverage: Baseline 3.0x vs EXP-116 Volatility-Targeted Downside Cushion Protection
        if enable_exp116_convex_gearing:
            base_c_lev = op_leverage * min(1.0, cushion_ratio / 0.20)
            # In extreme realized BTC volatility (> 95% ann) outside expansion, damp leverage by 10% to preserve cushion
            btc_sub = btc_returns[max(1, t_idx - 18) : t_idx + 1]
            sigma_real = float(np.std(btc_sub) * math.sqrt(2190)) if len(btc_sub) >= 6 else 0.50
            if not is_expansion and sigma_real > 0.95:
                active_op_lev = base_c_lev * 0.90
            else:
                active_op_lev = base_c_lev
        else:
            active_op_lev = op_leverage * min(1.0, cushion_ratio / 0.20)

        if beta_hedge_active and not stress_active:
            can_deescalate = v_oi_24h[t_idx] > 0.0 and btc_returns[t_idx] > 0.50 * atr_norm
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
            tot_notional = equity * active_op_lev
            btc_hedge_notional = -0.70 * net_beta_btc * tot_notional
            eth_hedge_notional = -0.30 * net_beta_eth * tot_notional
        elif not beta_hedge_active:
            btc_hedge_notional = 0.0
            eth_hedge_notional = 0.0

        # 4. Tradable Mask & Alpha Generation (Exact Config D)
        tradable_mask_bar = valid_mask[t_idx] & (close_mat[t_idx] > 0)
        ret_24h = np.nan_to_num((close_mat[t_idx] / close_mat[max(0, t_idx - 6)]) - 1.0, nan=0.0)
        ret_72h = np.nan_to_num((close_mat[t_idx] / close_mat[max(0, t_idx - 18)]) - 1.0, nan=0.0)
        basis_spread = np.nan_to_num(
            (close_mat[t_idx] - oracle_mat[t_idx]) / (oracle_mat[t_idx] + 1e-8), nan=0.0
        )
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

        # EXP-103C Arm B Idiosyncratic Inverse-Vol Sizing
        alpha_vec = alpha_vec * rolling_idio_inv_vol[t_idx]

        # EXP-113: Symmetric Cross-Sectional Persistence Quality Tilt (VR + FIP + Bipower Continuity)
        if enable_exp113_symmetric_sieve and np.sum(tradable_mask_bar) >= 4:
            fip_bar = fip_quality[t_idx]
            jr_bar = jump_ratio_mat[t_idx]
            # Symmetric quality bonus for smooth Frog-in-the-Pan trends with low jump discontinuity
            persist_mult = np.where((fip_bar >= 0.20) & (jr_bar <= 0.35), 1.15, 1.0)
            alpha_vec = alpha_vec * persist_mult

        # EXP-115: Convex Multi-ATR Trend Runner Tilt (let multi-ATR winners ride instead of flat 7% TP clip)
        if enable_exp115_atr_ratchet:
            runner_boost = np.where(
                (dp_24h_atr >= 1.50) & (np.sign(ret_24h) == np.sign(alpha_vec)) & (jump_ratio_mat[t_idx] <= 0.35),
                1.25,
                1.0,
            )
            alpha_vec = alpha_vec * runner_boost

        max_a = np.nanmax(np.abs(alpha_vec)) + 1e-8
        alpha_vec = np.nan_to_num(0.05 * (alpha_vec / max_a), nan=0.0)
        alpha_vec[~tradable_mask_bar] = 0.0

        # 5. Core Portfolio Weights Optimization & Cadence (EXP-114)
        betas = rolling_betas[t_idx]
        eff_lev = active_op_lev

        is_rebal_bar = bars_since_macro >= macro_cadence_bars
        if is_rebal_bar:
            bars_since_macro = 1
            if eff_lev > 1e-4 and np.sum(tradable_mask_bar) >= 2:
                raw_w = (alpha_vec / 1.5) + 0.35 * target_weights_prev
                net_b = float(np.sum(raw_w * betas))
                target_b = 0.80 if is_expansion else 0.0
                diff_b = net_b - target_b
                raw_w -= (diff_b / (np.sum(betas ** 2) + 1e-8)) * betas
                single_cap = 0.25 * max(1.0, eff_lev / 3.0)
                raw_w = np.clip(raw_w, -single_cap, single_cap)
                raw_w[~tradable_mask_bar] = 0.0
                tot_gross = np.sum(np.abs(raw_w))
                frozen_core_weights = raw_w * (eff_lev / tot_gross) if tot_gross > 1e-5 else np.zeros(n_symbols)
            else:
                frozen_core_weights = np.zeros(n_symbols)
        else:
            bars_since_macro += 1
            if cushion_ratio <= 0.0:
                frozen_core_weights = np.zeros(n_symbols)

        target_weights = frozen_core_weights.copy()

        # 6. EXP-112 Unified Capital Recycler strictly during fl0 cash-floor / de-escalated regimes
        sat_turnover_usd = 0.0
        if cushion_ratio <= 0.0:
            core_gross = float(np.sum(np.abs(target_weights)))
            idle_lev = max(0.0, op_leverage - core_gross)
            if idle_lev >= 0.20:
                sat_w = np.zeros(n_symbols)
                basis_apr = basis_spread * 0.125 * 24.0 * 365.25

                if np.sum(tradable_mask_bar) >= 5:
                    f_m = float(np.nanmean(funding_apr[tradable_mask_bar]))
                    f_s = float(np.nanstd(funding_apr[tradable_mask_bar])) + 1e-8
                    z_f = (funding_apr - f_m) / f_s
                else:
                    z_f = np.zeros(n_symbols)

                exp109_short_cands = []
                for si in range(n_symbols):
                    if tradable_mask_bar[si] and si not in (btc_idx, eth_idx):
                        if (funding_apr[si] > 1.00) or (basis_apr[si] > 1.00) or (z_f[si] > 1.80):
                            is_veto = (z_mom[si] > 2.50) and (dp_24h_atr[si] > 2.0)
                            if not is_veto:
                                exp109_short_cands.append((si, max(funding_apr[si], basis_apr[si]), z_f[si]))
                exp109_short_cands.sort(key=lambda x: (x[1], x[2]), reverse=True)

                k_109 = min(3, len(exp109_short_cands))
                if k_109 >= 1:
                    w_109 = min(0.004, idle_lev * 0.3) / k_109
                    for si, _, _ in exp109_short_cands[:k_109]:
                        sat_w[si] -= w_109

                    sat_b = float(betas @ sat_w)
                    if abs(sat_b) > 0.005:
                        sat_w[btc_idx] -= sat_b

                    sat_turnover_usd = float(np.sum(np.abs(sat_w))) * equity
                    target_weights = target_weights + sat_w

        # 6B. EXP-117 (4H Negative-Funding Squeeze Longs) & EXP-118 (Bipower Diffusive Continuation / Cascade)
        if enable_exp117_118_satellites and cushion_ratio > 0.30 and not stress_active:
            for si in range(n_symbols):
                if not tradable_mask_bar[si] or si in (btc_idx, eth_idx) or target_weights[si] <= 0:
                    continue
                atr_si = max(atr_mat[t_idx, si], close_mat[t_idx, si] * 0.01)
                # EXP-117: Negative Funding (< -50% APR) + 24H Breakout + Volume Surge -> boost existing long core leg by +20%
                if (
                    funding_apr[si] < -0.50
                    and close_mat[t_idx, si] > high_6b_mat[t_idx, si]
                    and vol_ratio_mat[t_idx, si] >= 1.40
                ):
                    target_weights[si] *= 1.20
                # EXP-118 Sub-Mode B1/B2: Bipower Diffusive Continuation / Cascade -> boost existing long core leg by +15%
                elif (
                    jump_ratio_mat[t_idx, si] <= 0.20
                    and sv_imb_mat[t_idx, si] >= 0.65
                    and dp_24h_atr[si] >= 2.0
                    and v_oi_24h[t_idx] >= 0.08
                ):
                    target_weights[si] *= 1.15

        # 7. Friction & Mark-to-Market Accounting
        turnover_delta = np.sum(np.abs(target_weights - target_weights_prev))
        turnover_usd = turnover_delta * equity

        rebal_maker = (turnover_usd * REBALANCE_MAKER_RATIO) * MAKER_FEE_BASE
        rebal_taker = (turnover_usd * REBALANCE_TAKER_RATIO) * TAKER_FEE_BASE

        if sat_turnover_usd > 0:
            friction = max(0.0, (rebal_maker + rebal_taker) - sat_turnover_usd * 0.000335)
        else:
            rebal_impact = 0.0
            for i in range(n_symbols):
                dw = abs(target_weights[i] - target_weights_prev[i])
                if dw > 1e-5:
                    n_i = dw * equity
                    rebal_impact += n_i * (
                        SLIPPAGE_BASE + SLIPPAGE_IMPACT_COEFF * math.sqrt(n_i / SLIPPAGE_REF_NOTIONAL)
                    )
            friction = rebal_maker + rebal_taker + rebal_impact

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
    return {
        "full_sample": calculate_window_metrics(eq_arr, total_eval_bars),
        "canonical_2190": calculate_window_metrics(eq_arr[:2191], 2190),
        "fold3_grinder": calculate_window_metrics(eq_arr[1620:1891], 270),
        "holdout_tail_94b": calculate_window_metrics(eq_arr[2190:2285], 94),
    }


def main():
    print("=" * 135)
    print("   APEX v4.0 DEEP RESEARCH ABLATION ENGINE (EXP-113 THROUGH EXP-118)   ")
    print("   Evaluating 2,284 Bars (Canonical 2,190 + Fold 3 Grinder + 94-Bar Independent Holdout)   ")
    print("=" * 135)

    df_raw = pl.read_parquet(DATA_LAKE_PATH)
    btc_df = df_raw.filter(pl.col("symbol") == BENCHMARK_SYMBOL).sort("timestamp_ms")
    all_timestamps = btc_df["timestamp_ms"].to_list()
    total_bars = 2284

    _, symbols, full_market_data = PointInTimeUniverseManager.load_pit_market_matrices(
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

    print("--> Precomputing Canonical & v4.0 Microstructure Matrices...")
    pdata = precompute_market_matrices(full_market_data, symbols, total_bars)
    pdata = precompute_v40_microstructure_matrices(full_market_data, pdata)

    configs = [
        (
            "0. v3.8.2 Daemon (72H Freeze [18 bars], 3.0x Cap, Asymmetric Sieve)",
            dict(
                macro_cadence_bars=18,
                enable_exp113_symmetric_sieve=False,
                enable_exp115_atr_ratchet=False,
                enable_exp116_convex_gearing=False,
                enable_exp117_118_satellites=False,
            ),
        ),
        (
            "1. + EXP-114 (Fast 4H Garleanu-Pedersen Rolling Cadence — Config D Baseline)",
            dict(
                macro_cadence_bars=1,
                enable_exp113_symmetric_sieve=False,
                enable_exp115_atr_ratchet=False,
                enable_exp116_convex_gearing=False,
                enable_exp117_118_satellites=False,
            ),
        ),
        (
            "2. + EXP-113 (Symmetric Hurst/VR/FIP Persistence Sieve & Quality Tilt)",
            dict(
                macro_cadence_bars=1,
                enable_exp113_symmetric_sieve=True,
                enable_exp115_atr_ratchet=False,
                enable_exp116_convex_gearing=False,
                enable_exp117_118_satellites=False,
            ),
        ),
        (
            "3. + EXP-115 (ATR-Scaled Brackets + Multi-ATR Parabolic Runner Ratchet)",
            dict(
                macro_cadence_bars=1,
                enable_exp113_symmetric_sieve=True,
                enable_exp115_atr_ratchet=True,
                enable_exp116_convex_gearing=False,
                enable_exp117_118_satellites=False,
            ),
        ),
        (
            "4. + EXP-116 (Regime-Conditional Convex Gearing up to 4.5x in Low-Vol Expansion)",
            dict(
                macro_cadence_bars=1,
                enable_exp113_symmetric_sieve=True,
                enable_exp115_atr_ratchet=True,
                enable_exp116_convex_gearing=True,
                enable_exp117_118_satellites=False,
            ),
        ),
        (
            "5. + EXP-117 & EXP-118 (Full APEX v4.0: + Squeeze Longs & Bipower Cascade Sleeves)",
            dict(
                macro_cadence_bars=1,
                enable_exp113_symmetric_sieve=True,
                enable_exp115_atr_ratchet=True,
                enable_exp116_convex_gearing=True,
                enable_exp117_118_satellites=True,
            ),
        ),
    ]

    results = {}
    print("\n" + "=" * 155)
    print(
        f"{'ABLATION CONFIGURATION':<82} | {'FULL CAGR':<10} | {'CANON CAGR':<10} | {'FULL SH':<8} | {'FULL MDD':<9} | {'FOLD3 SH':<9} | {'TAIL MDD':<9}"
    )
    print("=" * 155)

    for label, flags in configs:
        res = simulate_v40_ablation(pdata, total_bars, **flags)
        results[label] = res
        mf = res["full_sample"]
        mc = res["canonical_2190"]
        m3 = res["fold3_grinder"]
        mt = res["holdout_tail_94b"]
        print(
            f"{label:<82} | {mf['annualized_cagr_pct']:>8.1f}% | {mc['annualized_cagr_pct']:>9.1f}% | {mf['sharpe_ratio']:>7.2f}  | {mf['max_drawdown_pct']:>7.1f}%  | {m3['sharpe_ratio']:>+8.2f} | {mt['max_drawdown_pct']:>7.1f}%"
        )

    print("=" * 155)
    with open(OUT_JSON, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n[SAVED] Ablation results written to {OUT_JSON}")


if __name__ == "__main__":
    main()
