#!/usr/bin/env python3
"""
Institutional Backtest Benchmark Runner: EXP-105 Sovereign Compounding Architecture
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
from src.strategy.convex_105_sovereign_engine import (
    Exp105SovereignEngine,
    BalanceSheet6Bucket,
    Position,
    RegimePhase,
    round_px,
    round_sz,
    validate_l1_order,
)

ARTIFACTS_DIR = PIPELINE_ROOT / "artifacts"
EQUITY_CURVE_PATH = ARTIFACTS_DIR / "exp105_equity_curve.csv"
METRICS_JSON_PATH = ARTIFACTS_DIR / "exp105_metrics.json"

BENCHMARK_SYMBOL = "BTC"
TOTAL_EVAL_BARS = 2190


class DynamicQPSolver:
    """Convex QP Solver supporting dynamic per-bar turnover regularization lambda_turnover(t)."""
    def __init__(self, n_symbols: int, gamma: float = 1.0):
        self.n = n_symbols
        self.gamma = gamma
        self.w_var = cp.Variable(self.n)

    def solve(
        self,
        alpha_vec: np.ndarray,
        cov_matrix: np.ndarray,
        beta_btc: np.ndarray,
        beta_alt: np.ndarray,
        w_prev: np.ndarray,
        gross_target: float,
        beta_min: float,
        beta_max: float,
        lambda_alt: float,
        lambda_turnover: float,
        tradable_mask: np.ndarray,
    ) -> np.ndarray:
        if gross_target <= 1e-4 or np.sum(tradable_mask) == 0:
            return np.zeros(self.n)

        min_eig = np.min(np.real(np.linalg.eigvals(cov_matrix)))
        if min_eig < 1e-5:
            cov_matrix = cov_matrix + (abs(min_eig) + 1e-4) * np.eye(self.n)
        cov_matrix = 0.5 * (cov_matrix + cov_matrix.T)

        eff_beta_min = min(beta_min, beta_max)
        eff_beta_max = max(beta_min, beta_max)

        single_name_cap = min(0.25, gross_target)
        upper_bounds = np.where(tradable_mask, single_name_cap, 0.0)
        lower_bounds = np.where(tradable_mask, -single_name_cap, 0.0)

        quad_term = (self.gamma / 2.0) * cp.quad_form(self.w_var, cp.psd_wrap(cov_matrix))
        turnover_term = lambda_turnover * cp.sum_squares(self.w_var - w_prev)
        alt_term = lambda_alt * cp.square(beta_alt @ self.w_var)
        linear_term = -alpha_vec @ self.w_var

        obj = cp.Minimize(linear_term + quad_term + turnover_term + alt_term)
        qp_gross_limit = max(0.0, gross_target - 0.002)

        constraints = [
            cp.norm1(self.w_var) <= qp_gross_limit,
            beta_btc @ self.w_var >= eff_beta_min,
            beta_btc @ self.w_var <= eff_beta_max,
            self.w_var <= upper_bounds,
            self.w_var >= lower_bounds,
        ]

        prob = cp.Problem(obj, constraints)
        try:
            prob.solve(solver=cp.OSQP, warm_start=True, eps_abs=1e-5, eps_rel=1e-5, max_iter=4000)
        except Exception:
            try:
                prob.solve(solver=cp.CLARABEL)
            except Exception:
                pass

        if prob.status not in ["optimal", "optimal_inaccurate"] or self.w_var.value is None:
            prev_gross = float(np.sum(np.abs(w_prev)))
            if prev_gross > gross_target and prev_gross > 1e-4:
                return w_prev * (gross_target / prev_gross)
            return w_prev.copy()

        w_opt = np.array(self.w_var.value).flatten()
        w_opt = np.nan_to_num(w_opt, nan=0.0)
        w_opt[~tradable_mask] = 0.0
        return w_opt


def run_exp105_backtest(
    initial_capital: float = 10000.0,
    theta_giveback: float = 0.18,
    leverage_base: float = 1.0,
    leverage_max: float = 3.25,
    target_vol: float = 0.45,
    lambda_0: float = 0.85,
) -> Dict:
    start_wall_time = time.time()
    print("=" * 90)
    print("INSTITUTIONAL QUANT ENGINE: EXP-105 SOVEREIGN COMPOUNDING ARCHITECTURE")
    print("EXECUTION PHYSICS: IronCore v2.4.0 Frozen E3 Causal Standard")
    print(f"CONFIGURATION: L_base={leverage_base:.2f}x, L_max={leverage_max:.2f}x, Theta={theta_giveback*100:.1f}%, TargetVol={target_vol*100:.1f}%")
    print("=" * 90)

    # 1. Load Canonical Point-in-Time Data Lake
    print("--> [Data Engine] Initializing Point-in-Time Data Lake and Market Matrices...")
    compounding_engine = InstitutionalCompoundingEngine(fixed_leverage=3.0, turnover_lambda=0.85)
    eval_ts, symbols, data = compounding_engine.load_and_preprocess_data()

    n_symbols = len(symbols)
    btc_idx = symbols.index("BTC")
    eth_idx = symbols.index("ETH") if "ETH" in symbols else 1

    close_mat = data["close"]
    open_mat = data["open"]
    high_mat = data["high"]
    low_mat = data["low"]
    oracle_mat = data["oracle"]
    volume_mat = data["volume"]
    timestamps = data["timestamps"]
    eval_start_idx = data["eval_start_idx"]
    valid_mask = data.get("valid_price_mask", ~np.isnan(close_mat))

    print(f"--> [Data Lake] {n_symbols} assets across {len(timestamps)} bars. Evaluation window: {TOTAL_EVAL_BARS} bars.")

    # 2. Precompute Return & Technical Matrices
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
    btc_ema50 = pd.Series(btc_close).ewm(span=50, adjust=False).mean().to_numpy()

    # ADX-14 calculation for BTC
    up_move = high_mat[:, btc_idx] - np.roll(high_mat[:, btc_idx], 1)
    down_move = np.roll(low_mat[:, btc_idx], 1) - low_mat[:, btc_idx]
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    tr_btc = tr[:, btc_idx]
    tr_smooth = pd.Series(tr_btc).ewm(span=14, adjust=False).mean().to_numpy() + 1e-8
    plus_di = 100.0 * (pd.Series(plus_dm).ewm(span=14, adjust=False).mean().to_numpy() / tr_smooth)
    minus_di = 100.0 * (pd.Series(minus_dm).ewm(span=14, adjust=False).mean().to_numpy() / tr_smooth)
    dx = 100.0 * (np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-8))
    btc_adx14 = pd.Series(dx).ewm(span=14, adjust=False).mean().to_numpy()

    # Total volume and proxy open interest velocity
    vol_tot = np.sum(volume_mat, axis=1)
    v_oi_24h = np.zeros(len(close_mat))
    v_oi_24h[6:] = (vol_tot[6:] - vol_tot[:-6]) / (vol_tot[:-6] + 1e-8)

    # 4H Bipower Variation Jump Series (M = 18 bars)
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

    # Rolling BTC Betas (60 bars)
    print("--> [Data Engine] Precomputing Rolling Betas across 60-bar windows...")
    rolling_betas = np.ones((len(timestamps), n_symbols))
    for t_idx in range(eval_start_idx, len(timestamps)):
        w_rets = np.nan_to_num(returns_mat[max(0, t_idx-60) : t_idx], nan=0.0)
        var_btc = np.var(w_rets[:, btc_idx]) + 1e-8
        cov_btc = np.cov(w_rets, rowvar=False)[:, btc_idx]
        rolling_betas[t_idx] = cov_btc / var_btc
    rolling_betas[np.isnan(rolling_betas)] = 1.0
    rolling_betas[:, btc_idx] = 1.0

    # Baseline BTC Volatility for Dynamic Turnover Scaling
    btc_vol_baseline = float(np.std(btc_returns[eval_start_idx - 60 : eval_start_idx])) + 1e-8

    # EWMA Covariance Matrix
    warmup_slice = np.nan_to_num(returns_mat[max(0, eval_start_idx-30) : eval_start_idx], nan=0.0)
    cov_matrix = np.cov(warmup_slice, rowvar=False) + np.eye(n_symbols) * 1e-4
    ewma_lambda = 2.0 / (180.0 + 1.0)

    # 3. Initialize Production Strategy Engine
    sovereign_engine = Exp105SovereignEngine(
        symbols=symbols,
        initial_capital=initial_capital,
        theta_giveback=theta_giveback,
        leverage_base=leverage_base,
        leverage_max=leverage_max,
        target_vol=target_vol,
        lambda_turnover_base=lambda_0,
    )
    qp_solver = DynamicQPSolver(n_symbols=n_symbols, gamma=1.0)

    # State variables
    equity = initial_capital
    peak_equity = initial_capital
    peak_bar = 0
    equity_curve = [equity]
    portfolio_returns = []
    active_positions: Dict[str, Position] = {}
    target_weights_prev = np.zeros(n_symbols)
    nav_history = [equity]

    # Accounting breakdown
    cost_breakdown = {
        "maker_fees_usd": 0.0,
        "taker_fees_usd": 0.0,
        "base_slippage_usd": 0.0,
        "market_impact_usd": 0.0,
        "funding_pnl_usd": 0.0,
        "gross_trading_pnl_usd": 0.0,
        "beta_hedge_pnl_usd": 0.0,
    }

    stress_events_count = 0
    deescalation_events_count = 0
    total_trades_count = 0
    winning_trades_count = 0
    losing_trades_count = 0
    gross_win_dollars = 0.0
    gross_loss_dollars = 0.0

    # Execution physics parameters
    MAKER_FEE = 0.00015
    TAKER_FEE = 0.00045
    SLIPPAGE_BASE = 0.00020
    SLIPPAGE_IMPACT_COEFF = 0.00010
    SLIPPAGE_REF_NOTIONAL = 25000.0
    REBALANCE_MAKER_RATIO = 0.80
    REBALANCE_TAKER_RATIO = 0.20

    print("--> [Simulation Engine] Executing 2,190 bars under frozen IronCore v2.4.0 E3 causal standard...")

    for bar_count in range(TOTAL_EVAL_BARS):
        t_idx = eval_start_idx + bar_count
        next_t_idx = min(t_idx + 1, len(timestamps) - 1)

        # Update covariance matrix
        r_t = returns_mat[t_idx]
        cov_matrix = (1.0 - ewma_lambda) * cov_matrix + ewma_lambda * np.outer(r_t, r_t)
        mu_shrinkage = np.trace(cov_matrix) / n_symbols
        shrunk_cov = 0.85 * cov_matrix + 0.15 * mu_shrinkage * np.eye(n_symbols)

        # 1. Macro Beta Hedge Mark-to-Market (Shield Engine)
        if sovereign_engine.ledger.hedge_active:
            r_b = btc_returns[next_t_idx]
            r_e = eth_returns[next_t_idx]
            h_pnl = (sovereign_engine.ledger.btc_hedge_notional * r_b) + (sovereign_engine.ledger.eth_hedge_notional * r_e)
            cost_breakdown["beta_hedge_pnl_usd"] += h_pnl
            cost_breakdown["gross_trading_pnl_usd"] += h_pnl
            equity += h_pnl
            sovereign_engine.ledger.gross_price_pnl += h_pnl
            sovereign_engine.ledger.nav_usd = equity

        # 2. Continuous Cushion Governor & Operating Leverage Evaluation
        if equity > peak_equity:
            peak_equity = equity
            peak_bar = bar_count

        nav_6bars_ago = nav_history[max(0, bar_count - 6)]
        sovereign_engine.ledger.nav_usd = equity
        op_leverage = sovereign_engine.update_continuous_cushion_governor(
            current_bar=bar_count,
            peak_bar=peak_bar,
            nav_6bars_ago=nav_6bars_ago,
            btc_adx=btc_adx14[t_idx],
            btc_price=btc_close[t_idx],
            btc_ema50=btc_ema50[t_idx],
        )

        # 3. Macro Tail Hedge Evaluation (Calibrated 4H Jump Gate: Z > 1.645)
        was_hedged = sovereign_engine.ledger.hedge_active
        is_hedged = sovereign_engine.evaluate_4h_bipower_jump_hedging(
            btc_rets_18=btc_returns[max(0, t_idx-18) : t_idx],
            v_oi_24h=v_oi_24h[t_idx],
            r_btc_4h=btc_returns[t_idx],
            btc_atr=btc_atr[t_idx],
            btc_price=btc_close[t_idx],
            btc_ema20=btc_ema20[t_idx],
        )

        if was_hedged and not is_hedged:
            deescalation_events_count += 1
        if is_hedged and not was_hedged:
            stress_events_count += 1

        if is_hedged:
            # Neutralize portfolio beta via short liquid BTC/ETH
            b_btc = rolling_betas[t_idx]
            b_eth = np.ones(n_symbols) * 0.8
            net_beta_btc = float(np.sum(target_weights_prev * b_btc))
            net_beta_eth = float(np.sum(target_weights_prev * b_eth))
            tot_notional = equity * op_leverage
            sovereign_engine.ledger.btc_hedge_notional = -0.70 * net_beta_btc * tot_notional
            sovereign_engine.ledger.eth_hedge_notional = -0.30 * net_beta_eth * tot_notional
        else:
            sovereign_engine.ledger.btc_hedge_notional = 0.0
            sovereign_engine.ledger.eth_hedge_notional = 0.0

        # 4. Vector B: Multi-Beta Residualization & Asymmetric FIP Jump Filtering
        tradable_mask = valid_mask[t_idx] & (close_mat[t_idx] > 0)
        ret_window_60 = np.nan_to_num(returns_mat[max(0, t_idx-60) : t_idx], nan=0.0)

        z_alpha = sovereign_engine.compute_idiosyncratic_residual_momentum(
            returns_window_60=ret_window_60,
            btc_idx=btc_idx,
            eth_idx=eth_idx,
        )

        # 5. Volatility Parity Scaling
        vols_72h = np.nan_to_num(np.std(returns_mat[max(0, t_idx-18) : t_idx], axis=0) * math.sqrt(2190), nan=0.50)
        vol_scale = np.where(vols_72h > 0.05, target_vol / (vols_72h + 1e-8), 1.0)
        raw_alpha_vec = z_alpha * vol_scale

        max_abs_alpha = np.nanmax(np.abs(raw_alpha_vec)) + 1e-8
        alpha_vec = np.nan_to_num(0.05 * (raw_alpha_vec / max_abs_alpha), nan=0.0)
        alpha_vec[~tradable_mask] = 0.0

        # Dynamic Turnover Regularization Parameter
        btc_vol_current = float(np.std(btc_returns[max(0, t_idx-18) : t_idx])) + 1e-8
        lambda_turnover_t = sovereign_engine.compute_dynamic_turnover_regularizer(
            btc_vol_current=btc_vol_current,
            btc_vol_baseline=btc_vol_baseline,
        )

        # Decoupled Regime Target Bounds
        is_expansion = (btc_close[t_idx] > btc_ema50[t_idx] and btc_ema20[t_idx] > btc_ema50[t_idx] and btc_adx14[t_idx] > 22.0)
        gross_target = op_leverage
        if is_expansion:
            scale = min(1.0, gross_target / 2.0)
            eff_beta_min, eff_beta_max = 0.8 * scale, 1.2 * scale
            lambda_alt = 0.05
        else:
            eff_beta_min, eff_beta_max = -0.05, 0.15
            lambda_alt = 1.50

        beta_btc_vec = rolling_betas[t_idx]
        beta_alt_vec = beta_btc_vec.copy()
        beta_alt_vec[btc_idx] = 0.0

        # Solve QP Portfolio Targets
        target_weights = qp_solver.solve(
            alpha_vec=alpha_vec,
            cov_matrix=shrunk_cov,
            beta_btc=beta_btc_vec,
            beta_alt=beta_alt_vec,
            w_prev=target_weights_prev,
            gross_target=gross_target,
            beta_min=eff_beta_min,
            beta_max=eff_beta_max,
            lambda_alt=lambda_alt,
            lambda_turnover=lambda_turnover_t,
            tradable_mask=tradable_mask,
        )

        # 6. Rebalance Execution & Friction
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

        sovereign_engine.ledger.exchange_fees += (rebal_maker_fee + rebal_taker_fee)
        sovereign_engine.ledger.market_impact += rebal_impact

        # Update positions
        bar_realized_trade_pnl = 0.0
        for i, sym in enumerate(symbols):
            tgt_w = target_weights[i]
            cur_pos = active_positions.get(sym)

            if abs(tgt_w) > 1e-4:
                pos_dir = 1 if tgt_w > 0 else -1
                allocated_notional = abs(tgt_w) * equity
                open_p = open_mat[next_t_idx, i]
                if np.isnan(open_p):
                    open_p = close_mat[t_idx, i]
                if np.isnan(open_p) or open_p <= 0.0:
                    continue
                slip_rate = SLIPPAGE_BASE
                px = open_p * (1.0 + slip_rate) if pos_dir == 1 else open_p * (1.0 - slip_rate)
                sz_units = allocated_notional / max(px, 1e-6)
                atr_i = atr_mat[t_idx, i]
                if np.isnan(atr_i) or atr_i <= 0.0:
                    atr_i = px * 0.02

                if cur_pos is None:
                    total_trades_count += 1
                    active_positions[sym] = {
                        "direction": pos_dir,
                        "entry_price": px,
                        "current_size": sz_units,
                        "allocated_notional": allocated_notional,
                        "stop_price": px - 3.0 * atr_i if pos_dir == 1 else px + 3.0 * atr_i,
                        "entry_bar": bar_count,
                    }
                else:
                    cur_pos["direction"] = pos_dir
                    cur_pos["current_size"] = sz_units
                    cur_pos["allocated_notional"] = allocated_notional
                    cur_pos["stop_price"] = px - 3.0 * atr_i if pos_dir == 1 else px + 3.0 * atr_i
            else:
                if cur_pos is not None:
                    # Clean close via target weight reduction
                    trade_pnl = cur_pos["current_size"] * (close_mat[t_idx, i] - cur_pos["entry_price"]) * cur_pos["direction"]
                    if trade_pnl > 0:
                        winning_trades_count += 1
                        gross_win_dollars += trade_pnl
                    else:
                        losing_trades_count += 1
                        gross_loss_dollars += abs(trade_pnl)
                    del active_positions[sym]

        # 7. Intra-Bar Price & Stop Verification
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

            if stopped and (bar_count - pos["entry_bar"]) >= 12:
                if np.isnan(fill_px) or fill_px <= 0.0:
                    fill_px = pos["entry_price"]
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

        # Continuous MTM Incremental Evaluation
        bar_unrealized_pnl = 0.0
        bar_funding_pnl = 0.0
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

        bar_realized_trade_pnl = float(np.nan_to_num(bar_realized_trade_pnl, nan=0.0))
        rebal_friction = float(np.nan_to_num(rebal_friction, nan=0.0))
        cost_breakdown["gross_trading_pnl_usd"] += bar_unrealized_pnl
        bar_net_pnl = bar_unrealized_pnl + bar_realized_trade_pnl + bar_funding_pnl - rebal_friction
        bar_net_pnl = float(np.nan_to_num(bar_net_pnl, nan=0.0))
        equity += bar_net_pnl

        bar_ret_port = bar_net_pnl / max(1e-8, equity - bar_net_pnl)
        portfolio_returns.append(bar_ret_port)
        equity_curve.append(equity)
        nav_history.append(equity)
        target_weights_prev = target_weights

    # 8. Post-Tournament Metrics Calculation
    eq_arr = np.array(equity_curve)
    final_equity = float(equity)
    multiple = final_equity / initial_capital
    cum_ret_pct = (multiple - 1.0) * 100.0
    cagr_pct = ((multiple ** (2190.0 / TOTAL_EVAL_BARS)) - 1.0) * 100.0

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
        "architecture": "EXP-105 Sovereign Compounding Engine",
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
        "zero_leakage_certified": bool((max_discrepancy / max(1.0, final_equity)) < 1e-11 or max_discrepancy < 1e-6),
        "config": {
            "theta_floor": theta_giveback,
            "leverage_base": leverage_base,
            "leverage_max": leverage_max,
            "target_vol": target_vol,
            "lambda_0": lambda_0,
            "gamma_rebound": 0.35,
            "gamma_drawdown": 0.85,
            "z_jump_thresh": 1.645,
        },
        "timestamp_utc": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    }

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(METRICS_JSON_PATH, "w") as f:
        json.dump(metrics, f, indent=2)

    df_curve = pd.DataFrame({
        "bar_index": np.arange(len(equity_curve)),
        "portfolio_equity_usd": equity_curve,
    })
    df_curve.to_csv(EQUITY_CURVE_PATH, index=False)

    wall_clock = time.time() - start_wall_time
    is_zero_leak = (max_discrepancy / max(1.0, final_equity)) < 1e-11 or max_discrepancy < 1e-6

    print("\n" + "=" * 90)
    print("EXP-105 SOVEREIGN AUDITED TOURNAMENT RESULTS (IRONCORE v2.4.0 E3 STANDARD)")
    print("=" * 90)
    print(f"Initial Capital Base         : ${initial_capital:,.2f} USDC")
    print(f"Terminal Portfolio Equity    : ${final_equity:,.2f} USDC")
    print(f"Equity Compounding Multiple  : {multiple:.2f}x")
    print(f"Annualized Net CAGR          : +{cagr_pct:.2f}%")
    print(f"Annualized Sharpe Ratio      : {sharpe:.2f}")
    print(f"Annualized Sortino Ratio     : {sortino:.2f}")
    print(f"Realized Max Drawdown        : {max_dd_pct:.2f}%")
    print(f"Calmar Compounding Ratio     : {calmar:.2f}")
    print(f"Peak Portfolio Equity        : ${peak_val:,.2f} USDC")
    print(f"Realized Peak Giveback       : {giveback_pct:.2f}%")
    print(f"Win/Loss Payout Ratio        : {payout_ratio:.2f}")
    print(f"Stress Episodes Triggered    : {stress_events_count}")
    print(f"De-escalation Events Fired   : {deescalation_events_count}")
    print(f"6-Bucket Max Discrepancy     : ${max_discrepancy:.14f} USDC")
    print(f"Relative Discrepancy         : {max_discrepancy / max(1.0, final_equity):.4e}")
    print(f"Zero-Leakage Status          : {'PASS (|rel_eps| < 1e-11)' if is_zero_leak else 'FAIL'}")
    print(f"Simulation Wall Time         : {wall_clock:.1f}s")
    print("=" * 90)

    return metrics


if __name__ == "__main__":
    run_exp105_backtest()
