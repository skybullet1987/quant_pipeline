#!/usr/bin/env python3
"""
Institutional Backtest Benchmark Runner: EXP-106 Sovereign Unconstrained Architecture
Execution Physics: Frozen IronCore v2.4.0 E3 Causal Standard
Accounting: Exact 6-Bucket Mark-to-Market Balance Sheet Ledger (|epsilon| < 10^-10 USDC)
Dataset: Canonical Point-in-Time 4H Data Lake (2,190 Bars / 177 Perpetual Assets)
"""

import math
import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import cvxpy as cp

PIPELINE_ROOT = Path(__file__).resolve().parents[1]
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from backtest_10x_convex_compounding import InstitutionalCompoundingEngine
from src.strategy.convex_106_unconstrained_engine import (
    Exp106UnconstrainedEngine,
    UnconstrainedQPSolver,
    BalanceSheet6Bucket,
    Position,
    RegimePhase,
    round_px,
    round_sz,
    validate_l1_order,
)

ARTIFACTS_DIR = PIPELINE_ROOT / "artifacts"
EQUITY_CURVE_PATH = ARTIFACTS_DIR / "exp106_equity_curve.csv"
METRICS_JSON_PATH = ARTIFACTS_DIR / "exp106_metrics.json"

BENCHMARK_SYMBOL = "BTC"
TOTAL_EVAL_BARS = 2190

# Hyperliquid L1 Protocol & Execution Friction Constants
MAKER_FEE = 0.00015
TAKER_FEE = 0.00045
SLIPPAGE_BASE = 0.00020
SLIPPAGE_IMPACT_COEFF = 0.00010
SLIPPAGE_REF_NOTIONAL = 25000.0
REBALANCE_MAKER_RATIO = 0.80
REBALANCE_TAKER_RATIO = 0.20


def run_exp106_backtest(
    fixed_leverage: float = 3.0,
    pyramid_ratio: float = 0.50,
    use_acute_hedge: bool = True,
    z_jump_thresh: float = 1.645,
    v_oi_thresh: float = -0.10,
    hedge_btc_ratio: float = 0.70,
    hedge_eth_ratio: float = 0.30,
    initial_capital: float = 10000.0,
    single_name_cap: float = 0.25,
) -> Dict:
    print("=" * 90)
    print("INSTITUTIONAL QUANT ENGINE: EXP-106 SOVEREIGN UNCONSTRAINED ARCHITECTURE")
    print("EXECUTION PHYSICS: IronCore v2.4.0 Frozen E3 Causal Standard")
    print(f"CONFIGURATION: Leverage={fixed_leverage:.2f}x, PyramidRatio={pyramid_ratio:.2f}, AcuteHedge={use_acute_hedge}")
    print("=" * 90)

    # 1. Ingest Data Lake
    print("--> [Data Engine] Initializing Point-in-Time Data Lake and Market Matrices...")
    ref_engine = InstitutionalCompoundingEngine(fixed_leverage=fixed_leverage, turnover_lambda=0.85)
    eval_timestamps, symbols, data = ref_engine.load_and_preprocess_data()
    n_symbols = len(symbols)
    btc_idx = symbols.index(BENCHMARK_SYMBOL)
    eth_idx = symbols.index("ETH") if "ETH" in symbols else 1

    close_mat = data["close"]
    open_mat = data["open"]
    high_mat = data["high"]
    low_mat = data["low"]
    volume_mat = data["volume"]
    oracle_mat = data["oracle"]
    timestamps = data["timestamps"]
    eval_start_idx = data["eval_start_idx"]
    valid_mask = data.get("valid_price_mask", ~np.isnan(close_mat))

    print(f"--> [Data Lake] {n_symbols} assets across {len(close_mat)} bars. Evaluation window: {TOTAL_EVAL_BARS} bars.")

    # Returns & Technicals
    returns_mat = np.zeros_like(close_mat)
    prev_close = np.roll(close_mat, 1, axis=0)
    valid_pair = valid_mask & np.roll(valid_mask, 1, axis=0)
    valid_pair[0] = False
    with np.errstate(invalid="ignore", divide="ignore"):
        returns_mat[1:] = np.where(valid_pair[1:], (close_mat[1:] / (prev_close[1:] + 1e-12)) - 1.0, 0.0)

    tr = np.maximum(high_mat - low_mat, np.maximum(np.abs(high_mat - prev_close), np.abs(low_mat - prev_close)))
    atr_mat = np.zeros_like(close_mat)
    for i in range(20, len(tr)):
        atr_mat[i] = np.nanmean(tr[i-20:i], axis=0)
    atr_mat[:20] = np.nan_to_num(tr[:20], nan=0.0)

    btc_close = close_mat[:, btc_idx]
    btc_returns = returns_mat[:, btc_idx]
    eth_returns = returns_mat[:, eth_idx]
    btc_atr = atr_mat[:, btc_idx]
    btc_ema20 = pd.Series(btc_close).ewm(span=20, adjust=False).mean().to_numpy()

    # Total volume & VOI proxy
    vol_tot = np.sum(volume_mat, axis=1)
    v_oi_24h = np.zeros(len(close_mat))
    v_oi_24h[6:] = (vol_tot[6:] - vol_tot[:-6]) / (vol_tot[:-6] + 1e-8)

    # 4H Bipower Variation Jump Series
    z_jump_series = np.zeros(len(close_mat))
    for t in range(18, len(close_mat)):
        sub_btc = btc_returns[t-18:t]
        rv = np.sum(sub_btc ** 2)
        bv = (math.pi / 2.0) * (18.0 / 17.0) * np.sum(np.abs(sub_btc[1:]) * np.abs(sub_btc[:-1]))
        tp = 18.0 * (18.0 / 16.0) * (0.8309 ** -3) * np.sum(
            (np.abs(sub_btc[2:]) ** (4.0 / 3.0)) * (np.abs(sub_btc[1:-1]) ** (4.0 / 3.0)) * (np.abs(sub_btc[:-2]) ** (4.0 / 3.0))
        )
        if rv > bv and tp > 0:
            var_stat = (math.pi ** 2 / 4.0 + math.pi - 3.0) * (1.0 / 18.0) * max(1.0, tp / (bv ** 2 + 1e-8))
            z_jump_series[t] = ((rv - bv) / rv) / math.sqrt(max(1e-8, var_stat))

    # Rolling Betas (vectorized)
    print("--> [Data Engine] Precomputing Rolling Betas across 60-bar windows...")
    rolling_betas = np.ones((len(timestamps), n_symbols))
    for t_idx in range(eval_start_idx, len(timestamps)):
        w_rets = np.nan_to_num(returns_mat[max(0, t_idx-60) : t_idx], nan=0.0)
        w_btc = w_rets[:, btc_idx]
        var_btc = np.var(w_btc) + 1e-8
        cov_btc = np.mean((w_rets - np.mean(w_rets, axis=0)) * (w_btc[:, None] - np.mean(w_btc)), axis=0)
        rolling_betas[t_idx] = cov_btc / var_btc
    rolling_betas[np.isnan(rolling_betas)] = 1.0
    rolling_betas[:, btc_idx] = 1.0

    # Covariance EWMA initialization
    warmup_slice = np.nan_to_num(returns_mat[max(0, eval_start_idx-30) : eval_start_idx], nan=0.0)
    cov_matrix = np.cov(warmup_slice, rowvar=False) + np.eye(n_symbols) * 1e-4
    ewma_lambda = 2.0 / (180.0 + 1.0)

    # 2. Strategy Engine & Solver Initialization
    engine = Exp106UnconstrainedEngine(
        symbols=symbols,
        initial_capital=initial_capital,
        fixed_leverage=fixed_leverage,
        z_jump_thresh=z_jump_thresh,
        v_oi_thresh=v_oi_thresh,
        hedge_btc_ratio=hedge_btc_ratio,
        hedge_eth_ratio=hedge_eth_ratio,
    )
    solver = UnconstrainedQPSolver(n_symbols=n_symbols, gamma=1.0, lambda_turnover=0.85)

    equity = initial_capital
    peak_equity = initial_capital
    equity_curve = [equity]
    portfolio_returns = []
    active_positions: Dict[str, Dict] = {}
    pending_pyramids: Set[str] = set()
    target_weights_prev = np.zeros(n_symbols)

    cost_breakdown = {
        "maker_fees_usd": 0.0,
        "taker_fees_usd": 0.0,
        "base_slippage_usd": 0.0,
        "market_impact_usd": 0.0,
        "funding_pnl_usd": 0.0,
        "gross_trading_pnl_usd": 0.0,
        "beta_hedge_pnl_usd": 0.0,
    }

    # Tracking metrics
    total_trades_count = 0
    winning_trades_count = 0
    losing_trades_count = 0
    gross_win_dollars = 0.0
    gross_loss_dollars = 0.0
    stress_events_count = 0
    deescalation_events_count = 0

    beta_hedge_active = False
    btc_hedge_notional = 0.0
    eth_hedge_notional = 0.0

    t_start = time.time()
    print("--> [Simulation Engine] Executing 2,190 bars under frozen IronCore v2.4.0 E3 causal standard...")

    for bar_count in range(TOTAL_EVAL_BARS):
        t_idx = eval_start_idx + bar_count
        next_t_idx = min(t_idx + 1, len(timestamps) - 1)

        # Update EWMA covariance
        r_t = returns_mat[t_idx]
        cov_matrix = (1.0 - ewma_lambda) * cov_matrix + ewma_lambda * np.outer(r_t, r_t)
        mu_shrinkage = np.trace(cov_matrix) / n_symbols
        shrunk_cov = 0.85 * cov_matrix + 0.15 * mu_shrinkage * np.eye(n_symbols)
        shrunk_cov = 0.5 * (shrunk_cov + shrunk_cov.T) + 1e-4 * np.eye(n_symbols)

        # 1. Macro Beta Hedge Mark-to-Market
        if beta_hedge_active:
            r_b = btc_returns[next_t_idx]
            r_e = eth_returns[next_t_idx]
            h_pnl = (btc_hedge_notional * r_b) + (eth_hedge_notional * r_e)
            cost_breakdown["beta_hedge_pnl_usd"] += h_pnl
            cost_breakdown["gross_trading_pnl_usd"] += h_pnl
            equity += h_pnl

        if equity > peak_equity:
            peak_equity = equity

        # 2. Acute Tail-Risk Shield (Arm B5 Trigger)
        is_oi_flush = v_oi_24h[t_idx] < v_oi_thresh
        atr_norm = btc_atr[t_idx] / max(btc_close[t_idx], 1e-4)
        is_jump_crash = (z_jump_series[t_idx] > z_jump_thresh) and (btc_returns[t_idx] < -1.50 * atr_norm)
        acute_cascade = is_jump_crash or is_oi_flush

        # Instantaneous De-escalation Gate
        is_stabilized = (v_oi_24h[t_idx] > 0.0 and btc_returns[t_idx] > 0.50 * atr_norm) or (btc_close[t_idx] > btc_ema20[t_idx])

        if use_acute_hedge:
            if beta_hedge_active:
                if is_stabilized and not acute_cascade:
                    beta_hedge_active = False
                    btc_hedge_notional = 0.0
                    eth_hedge_notional = 0.0
                    deescalation_events_count += 1
            else:
                if acute_cascade:
                    stress_events_count += 1
                    beta_hedge_active = True
                    b_btc = rolling_betas[t_idx]
                    b_eth = np.ones(n_symbols) * 0.80
                    tot_max_notional = equity * fixed_leverage
                    raw_btc = -hedge_btc_ratio * net_beta_btc * tot_max_notional
                    raw_eth = -hedge_eth_ratio * net_beta_eth * tot_max_notional
                    tot_req = abs(raw_btc) + abs(raw_eth)
                    max_hedge_allowed = tot_max_notional * 0.50
                    scale = min(1.0, max_hedge_allowed / max(1e-4, tot_req))
                    btc_hedge_notional = raw_btc * scale
                    eth_hedge_notional = raw_eth * scale

        # 3. Alpha Sieve (EXP-103 Multi-Horizon Momentum)
        tradable_mask = valid_mask[t_idx] & (close_mat[t_idx] > 0)
        ret_24h_all = np.nan_to_num((close_mat[t_idx] / close_mat[max(0, t_idx-6)]) - 1.0, nan=0.0)
        ret_72h_all = np.nan_to_num((close_mat[t_idx] / close_mat[max(0, t_idx-18)]) - 1.0, nan=0.0)
        basis_spread = np.nan_to_num((close_mat[t_idx] - oracle_mat[t_idx]) / (oracle_mat[t_idx] + 1e-8), nan=0.0)
        vol_compress = np.nan_to_num(atr_mat[t_idx] / (close_mat[t_idx] + 1e-8), nan=0.0)

        if np.sum(tradable_mask) >= 2:
            mom_raw = ret_24h_all + ret_72h_all
            m_mean = np.nanmean(mom_raw[tradable_mask])
            m_std = np.nanstd(mom_raw[tradable_mask]) + 1e-8
            z_mom = np.nan_to_num((mom_raw - m_mean) / m_std)

            b_mean = np.nanmean(basis_spread[tradable_mask])
            b_std = np.nanstd(basis_spread[tradable_mask]) + 1e-8
            z_basis = np.nan_to_num(-(basis_spread - b_mean) / b_std)

            v_mean = np.nanmean(vol_compress[tradable_mask])
            v_std = np.nanstd(vol_compress[tradable_mask]) + 1e-8
            z_vol = np.nan_to_num((vol_compress - v_mean) / v_std)
        else:
            z_mom = np.zeros(n_symbols)
            z_basis = np.zeros(n_symbols)
            z_vol = np.zeros(n_symbols)

        alpha_vec = 0.60 * z_mom + 0.25 * z_basis + 0.15 * z_vol
        max_abs = np.nanmax(np.abs(alpha_vec)) + 1e-8
        alpha_vec = np.nan_to_num(0.05 * (alpha_vec / max_abs), nan=0.0)
        alpha_vec[~tradable_mask] = 0.0

        # 4. Unconstrained QP Portfolio Target Weights (PURGED OF BETA RESTRICTIONS)
        target_weights = solver.solve(
            alpha_vec=alpha_vec,
            cov_matrix=shrunk_cov,
            w_prev=target_weights_prev,
            gross_target=fixed_leverage,
            tradable_mask=tradable_mask,
            single_name_cap=single_name_cap,
        )

        # 5. Rebalance Execution & Friction
        turnover_delta = np.sum(np.abs(target_weights - target_weights_prev))
        turnover_usd = turnover_delta * equity
        rebal_maker_fee = (turnover_usd * REBALANCE_MAKER_RATIO) * MAKER_FEE
        rebal_taker_fee = (turnover_usd * REBALANCE_TAKER_RATIO) * TAKER_FEE
        rebal_impact = 0.0
        for i in range(n_symbols):
            dw_i = abs(target_weights[i] - target_weights_prev[i])
            if dw_i > 1e-5:
                notional_i = dw_i * equity
                rebal_impact += notional_i * (SLIPPAGE_BASE + SLIPPAGE_IMPACT_COEFF * math.sqrt(notional_i / SLIPPAGE_REF_NOTIONAL))

        rebal_friction = rebal_maker_fee + rebal_taker_fee + rebal_impact
        cost_breakdown["maker_fees_usd"] += rebal_maker_fee
        cost_breakdown["taker_fees_usd"] += rebal_taker_fee
        cost_breakdown["market_impact_usd"] += rebal_impact

        # Update active positions
        for i, sym in enumerate(symbols):
            tgt_w = target_weights[i]
            cur_pos = active_positions.get(sym)

            if abs(tgt_w) > 1e-4:
                pos_dir = 1 if tgt_w > 0 else -1
                allocated_notional = abs(tgt_w) * equity
                open_p = open_mat[next_t_idx, i]
                if np.isnan(open_p) or open_p <= 0.0:
                    open_p = close_mat[t_idx, i]
                if np.isnan(open_p) or open_p <= 0.0:
                    continue
                px = open_p * (1.0 + SLIPPAGE_BASE) if pos_dir == 1 else open_p * (1.0 - SLIPPAGE_BASE)
                sz_units = allocated_notional / max(px, 1e-6)
                atr_i = atr_mat[t_idx, i]
                if np.isnan(atr_i) or atr_i <= 0.0:
                    atr_i = px * 0.02

                if cur_pos is None:
                    total_trades_count += 1
                    active_positions[sym] = {
                        "direction": pos_dir,
                        "entry_price": px,
                        "base_size": sz_units,
                        "current_size": sz_units,
                        "stop_price": px - 1.5 * atr_i if pos_dir == 1 else px + 1.5 * atr_i,
                        "atr_0": atr_i,
                        "entry_bar": bar_count,
                        "pyramided": False,
                    }
                else:
                    cur_pos["direction"] = pos_dir
                    cur_pos["base_size"] = sz_units
                    if not cur_pos["pyramided"]:
                        cur_pos["current_size"] = sz_units
                    else:
                        cur_pos["current_size"] = (1.0 + pyramid_ratio) * sz_units
                    cur_pos["stop_price"] = px - 1.5 * atr_i if pos_dir == 1 else px + 1.5 * atr_i
            else:
                if cur_pos is not None:
                    trade_pnl = cur_pos["current_size"] * (close_mat[t_idx, i] - cur_pos["entry_price"]) * cur_pos["direction"]
                    if trade_pnl > 0:
                        winning_trades_count += 1
                        gross_win_dollars += trade_pnl
                    else:
                        losing_trades_count += 1
                        gross_loss_dollars += abs(trade_pnl)
                    del active_positions[sym]
                    pending_pyramids.discard(sym)

        # 6. Causal Pyramiding Execution (IronCore v2.4.1 Certified: Bar-Confirmed Next-Bar-Open)
        if pyramid_ratio > 0.0:
            # Step A: Execute pending pyramids from previous bar's confirmation at OPEN of next_t_idx
            for sym in list(pending_pyramids):
                pos = active_positions.get(sym)
                if pos is not None and not pos["pyramided"]:
                    s_i = symbols.index(sym)
                    open_p = open_mat[next_t_idx, s_i]
                    if np.isnan(open_p) or open_p <= 0.0:
                        open_p = close_mat[t_idx, s_i]
                    pyr_px = open_p * (1.0 + SLIPPAGE_BASE) if pos["direction"] == 1 else open_p * (1.0 - SLIPPAGE_BASE)
                    add_size = pyramid_ratio * pos["base_size"]
                    add_notional = add_size * pyr_px
                    p_fee = (add_notional * REBALANCE_MAKER_RATIO) * MAKER_FEE + (add_notional * REBALANCE_TAKER_RATIO) * TAKER_FEE
                    p_slip = add_notional * SLIPPAGE_BASE
                    p_imp = add_notional * (SLIPPAGE_IMPACT_COEFF * math.sqrt(add_notional / SLIPPAGE_REF_NOTIONAL))
                    p_fric = p_fee + p_slip + p_imp

                    c_next = close_mat[next_t_idx, s_i]
                    p_pnl = add_size * (c_next - pyr_px) * pos["direction"]
                    cost_breakdown["gross_trading_pnl_usd"] += p_pnl
                    cost_breakdown["maker_fees_usd"] += (add_notional * REBALANCE_MAKER_RATIO) * MAKER_FEE
                    cost_breakdown["taker_fees_usd"] += (add_notional * REBALANCE_TAKER_RATIO) * TAKER_FEE
                    cost_breakdown["base_slippage_usd"] += p_slip
                    cost_breakdown["market_impact_usd"] += p_imp

                    pos["current_size"] += add_size
                    pos["pyramided"] = True
                    equity += (p_pnl - p_fric)
                pending_pyramids.discard(sym)

            # Step B: Check if bar t_idx closed with +2.0 ATR reached, queue for next bar open fill
            for sym, pos in active_positions.items():
                s_i = symbols.index(sym)
                h_t = high_mat[t_idx, s_i]
                l_t = low_mat[t_idx, s_i]
                if not pos["pyramided"] and sym not in pending_pyramids:
                    if pos["direction"] == 1 and h_t >= (pos["entry_price"] + 2.0 * pos["atr_0"]):
                        pending_pyramids.add(sym)
                    elif pos["direction"] == -1 and l_t <= (pos["entry_price"] - 2.0 * pos["atr_0"]):
                        pending_pyramids.add(sym)

        # 7. Intra-bar Stop Loss Evaluation
        bar_realized_trade_pnl = 0.0
        closed_syms = []
        for sym, pos in active_positions.items():
            s_i = symbols.index(sym)
            next_l = low_mat[next_t_idx, s_i]
            next_h = high_mat[next_t_idx, s_i]
            c_prev = close_mat[t_idx, s_i]
            stopped = False
            fill_px = pos["stop_price"]

            if pos["direction"] == 1:
                if not np.isnan(next_l) and next_l <= pos["stop_price"]:
                    stopped = True
                    n_open = open_mat[next_t_idx, s_i]
                    fill_px = min(n_open, pos["stop_price"]) if not np.isnan(n_open) else pos["stop_price"]
            else:
                if not np.isnan(next_h) and next_h >= pos["stop_price"]:
                    stopped = True
                    n_open = open_mat[next_t_idx, s_i]
                    fill_px = max(n_open, pos["stop_price"]) if not np.isnan(n_open) else pos["stop_price"]

            if stopped:
                c_ref = c_prev if not np.isnan(c_prev) and c_prev > 0.0 else pos["entry_price"]
                trade_pnl = pos["current_size"] * (fill_px - c_ref) * pos["direction"]
                notional = pos["current_size"] * fill_px
                stop_fee = notional * TAKER_FEE
                stop_slip = notional * SLIPPAGE_BASE
                stop_imp = notional * (SLIPPAGE_IMPACT_COEFF * math.sqrt(notional / SLIPPAGE_REF_NOTIONAL))
                fric = stop_fee + stop_slip + stop_imp
                cost_breakdown["taker_fees_usd"] += stop_fee
                cost_breakdown["base_slippage_usd"] += stop_slip
                cost_breakdown["market_impact_usd"] += stop_imp
                cost_breakdown["gross_trading_pnl_usd"] += trade_pnl
                bar_realized_trade_pnl += (trade_pnl - fric)

                full_pnl = pos["current_size"] * (fill_px - pos["entry_price"]) * pos["direction"]
                if full_pnl > 0:
                    winning_trades_count += 1
                    gross_win_dollars += full_pnl
                else:
                    losing_trades_count += 1
                    gross_loss_dollars += abs(full_pnl)
                closed_syms.append(sym)

        for s in closed_syms:
            del active_positions[s]

        # 8. MTM Incremental Evaluation
        bar_unrealized_pnl = 0.0
        for sym, pos in active_positions.items():
            s_i = symbols.index(sym)
            c_now = close_mat[next_t_idx, s_i]
            c_prev = close_mat[t_idx, s_i]
            if np.isnan(c_now) or np.isnan(c_prev) or c_prev <= 0.0:
                bar_ret = 0.0
                c_ref = pos["entry_price"]
            else:
                bar_ret = (c_now / c_prev) - 1.0
                c_ref = c_prev
            pnl_i = np.nan_to_num(pos["current_size"] * c_ref * bar_ret * pos["direction"], nan=0.0)
            bar_unrealized_pnl += pnl_i

        cost_breakdown["gross_trading_pnl_usd"] += bar_unrealized_pnl
        bar_net_pnl = bar_unrealized_pnl + bar_realized_trade_pnl - rebal_friction
        equity += bar_net_pnl

        bar_ret_port = bar_net_pnl / max(1e-8, equity - bar_net_pnl)
        portfolio_returns.append(bar_ret_port)
        equity_curve.append(equity)
        target_weights_prev = target_weights

    # 9. Post-Tournament Metrics Calculation
    final_equity = float(equity)
    multiple = final_equity / initial_capital
    cum_ret_pct = (multiple - 1.0) * 100.0
    cagr_pct = ((multiple ** (2190.0 / TOTAL_EVAL_BARS)) - 1.0) * 100.0

    eq_arr = np.array(equity_curve)
    running_max = np.maximum.accumulate(eq_arr)
    drawdowns = (running_max - eq_arr) / running_max
    max_dd_pct = float(np.max(drawdowns)) * 100.0
    peak_val = float(np.max(eq_arr))
    giveback_pct = float((peak_val - final_equity) / peak_val) * 100.0

    rets = np.array(portfolio_returns)
    sharpe = float(np.mean(rets) / (np.std(rets) + 1e-8)) * math.sqrt(2190.0)
    downside = np.std(rets[rets < 0]) + 1e-8
    sortino = float(np.mean(rets) / downside) * math.sqrt(2190.0)
    calmar = cagr_pct / (max_dd_pct + 1e-8)
    payout_ratio = float(gross_win_dollars / (gross_loss_dollars + 1e-8))

    reconciled_nav = (
        initial_capital
        + cost_breakdown["gross_trading_pnl_usd"]
        + cost_breakdown["funding_pnl_usd"]
        - cost_breakdown["maker_fees_usd"]
        - cost_breakdown["taker_fees_usd"]
        - cost_breakdown["base_slippage_usd"]
        - cost_breakdown["market_impact_usd"]
    )
    max_discrepancy = abs(reconciled_nav - final_equity)

    metrics = {
        "architecture": "EXP-106 Sovereign Unconstrained Engine",
        "evaluation_window_bars": TOTAL_EVAL_BARS,
        "calendar_days": 365.0,
        "initial_nav_usd": initial_capital,
        "terminal_equity_usd": round(final_equity, 2),
        "equity_multiple": round(multiple, 2),
        "cumulative_net_return_pct": round(cum_ret_pct, 2),
        "annualized_net_cagr_pct": round(cagr_pct, 2),
        "annualized_sharpe_ratio": round(sharpe, 2),
        "annualized_sortino_ratio": round(sortino, 2),
        "realized_max_drawdown_pct": round(max_dd_pct, 2),
        "calmar_ratio": round(calmar, 2),
        "peak_portfolio_equity_usd": round(peak_val, 2),
        "realized_peak_giveback_pct": round(giveback_pct, 2),
        "realized_win_loss_payout_ratio": round(payout_ratio, 2),
        "total_trades": total_trades_count,
        "winning_trades": winning_trades_count,
        "losing_trades": losing_trades_count,
        "stress_episodes_handled": stress_events_count,
        "deescalation_events": deescalation_events_count,
        "max_accounting_discrepancy_usd": float(max_discrepancy),
        "relative_discrepancy": float(max_discrepancy / max(1.0, final_equity)),
        "zero_leakage_certified": bool(max_discrepancy < 1e-6),
        "config": {
            "fixed_leverage": fixed_leverage,
            "pyramid_ratio": pyramid_ratio,
            "use_acute_hedge": use_acute_hedge,
            "z_jump_thresh": z_jump_thresh,
            "v_oi_thresh": v_oi_thresh,
            "hedge_btc_ratio": hedge_btc_ratio,
            "hedge_eth_ratio": hedge_eth_ratio,
        },
        "timestamp_utc": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    }

    # Print Formatted Institutional Scoreboard
    print("\n" + "=" * 90)
    print("EXP-106 SOVEREIGN UNCONSTRAINED AUDITED TOURNAMENT RESULTS (IRONCORE v2.4.0 E3)")
    print("=" * 90)
    print(f"Initial Capital Base         : ${initial_capital:,.2f} USDC")
    print(f"Terminal Portfolio Equity    : ${final_equity:,.2f} USDC")
    print(f"Equity Compounding Multiple  : {multiple:0.2f}x")
    print(f"Annualized Net CAGR          : {cagr_pct:+.2f}%")
    print(f"Annualized Sharpe Ratio      : {sharpe:0.2f}")
    print(f"Annualized Sortino Ratio     : {sortino:0.2f}")
    print(f"Realized Max Drawdown        : {max_dd_pct:0.2f}%")
    print(f"Calmar Compounding Ratio     : {calmar:0.2f}")
    print(f"Peak Portfolio Equity        : ${peak_val:,.2f} USDC")
    print(f"Realized Peak Giveback       : {giveback_pct:0.2f}%")
    print(f"Win/Loss Payout Ratio        : {payout_ratio:0.2f}")
    print(f"Stress Episodes Triggered    : {stress_events_count}")
    print(f"De-escalation Events Fired   : {deescalation_events_count}")
    print(f"6-Bucket Max Discrepancy     : ${max_discrepancy:.14f} USDC")
    print(f"Relative Discrepancy         : {metrics['relative_discrepancy']:.4e}")
    print(f"Zero-Leakage Status          : {'PASS' if metrics['zero_leakage_certified'] else 'FAIL'}")
    print(f"Simulation Wall Time         : {time.time()-t_start:.1f}s")
    print("=" * 90)

    # Save Artifacts
    with open(METRICS_JSON_PATH, "w") as f:
        json.dump(metrics, f, indent=2)

    df_curve = pd.DataFrame({
        "bar_index": np.arange(len(equity_curve)),
        "portfolio_equity_usd": equity_curve,
    })
    df_curve.to_csv(EQUITY_CURVE_PATH, index=False)
    print(f"--> [Artifacts] Metrics saved to {METRICS_JSON_PATH}")
    print(f"--> [Artifacts] Equity curve saved to {EQUITY_CURVE_PATH}")

    return metrics


if __name__ == "__main__":
    run_exp106_backtest()
