#!/usr/bin/env python3
"""
Branch A3: Close-Triggered Invalidation Exits (A0 + Exits)
=========================================================
Tests explicit adverse-trend invalidation rules evaluated strictly at bar t close,
routing 100% full liquidation orders to execute at bar t+1 open with standard friction.

Pre-registered Rules (No in-flight optimization):
1. ATR Ratchet: K * ATR_20 trailing peak close (K in [2.0, 3.0, 4.0])
2. Structural 18-bar (72H) Extremum Break
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from backtest_10x_convex_compounding import InstitutionalCompoundingEngine

BENCHMARK_SYMBOL = "BTC"
MAKER_FEE = 0.00015
TAKER_FEE = 0.00038
SLIPPAGE_BASE = 0.00025
SLIPPAGE_IMPACT_COEFF = 0.00010
SLIPPAGE_REF_NOTIONAL = 25000.0
REBALANCE_MAKER_RATIO = 0.85
REBALANCE_TAKER_RATIO = 0.15
TOTAL_EVAL_BARS = 2190


def run_invalidation_exit_backtest(
    cached_data: Dict[str, Any],
    exit_rule: str = "none",  # "none", "atr_ratchet_2.0", "atr_ratchet_3.0", "atr_ratchet_4.0", "structural_72h"
    atr_k: float = 3.0,
    fixed_leverage: float = 3.0,
    turnover_lambda: float = 0.85,
) -> Dict[str, Any]:
    symbols = cached_data["symbols"]
    n_symbols = len(symbols)
    btc_idx = symbols.index(BENCHMARK_SYMBOL)

    close_mat = cached_data["close"]
    open_mat = cached_data["open"]
    high_mat = cached_data["high"]
    low_mat = cached_data["low"]
    funding_mat = cached_data["funding"]
    atr_mat = cached_data["atr"]
    btc_returns = cached_data["btc_returns"]
    btc_close = cached_data["btc_close"]
    btc_atr = cached_data["btc_atr"]
    btc_ema20 = cached_data["btc_ema20"]
    btc_ema50 = cached_data["btc_ema50"]
    btc_adx14 = cached_data["btc_adx14"]

    STATE_EXPANSION = 0
    STATE_CHOP = 1
    STATE_FAST_SHOCK = 2
    STATE_RECOVERY = 3

    regime_state = STATE_CHOP
    expansion_streak = 0
    chop_streak = 0
    shock_dwell = 0
    recovery_dwell = 0
    shock_trough = 1e9

    initial_capital = 10000.0
    equity = initial_capital
    equity_curve = [equity]
    portfolio_returns = []
    turnover_history = []

    active_positions: Dict[str, Dict[str, Any]] = {}
    pending_exits: set = set()

    cost_breakdown = {
        "maker_fees_usd": 0.0,
        "taker_fees_usd": 0.0,
        "base_slippage_usd": 0.0,
        "market_impact_usd": 0.0,
        "funding_pnl_usd": 0.0,
        "gross_trading_pnl_usd": 0.0,
        "total_traded_volume_usd": 0.0,
    }

    invalidation_count = 0
    target_weights = np.zeros(n_symbols)
    bars_since_macro = 18

    for t_idx in range(TOTAL_EVAL_BARS - 1):
        next_t_idx = t_idx + 1

        # 1. Macro Regime
        btc_4h_ret = btc_returns[t_idx]
        btc_24h_ret = (btc_close[t_idx] / btc_close[max(0, t_idx - 6)]) - 1.0 if t_idx >= 6 else 0.0
        btc_atr_p = btc_atr[t_idx] / btc_close[t_idx]

        is_shock = (btc_4h_ret < -2.5 * btc_atr_p) or (btc_24h_ret < -0.06)
        if is_shock:
            regime_state = STATE_FAST_SHOCK
            shock_dwell += 1
            recovery_dwell = 0
            shock_trough = min(shock_trough, low_mat[t_idx, btc_idx])
            expansion_streak = 0
            chop_streak = 0
        elif regime_state == STATE_FAST_SHOCK:
            if (shock_dwell >= 6) and (btc_close[t_idx] > shock_trough) and (btc_4h_ret > -1.5 * btc_atr_p):
                regime_state = STATE_RECOVERY
                recovery_dwell = 1
                shock_dwell = 0
                shock_trough = 1e9
            else:
                shock_dwell += 1
        elif regime_state == STATE_RECOVERY:
            recovery_dwell += 1
            if recovery_dwell >= 6:
                is_expansion_tech = (btc_close[t_idx] > btc_ema50[t_idx] and btc_ema20[t_idx] > btc_ema50[t_idx] and btc_adx14[t_idx] > 22.0)
                if is_expansion_tech and expansion_streak >= 3:
                    regime_state = STATE_EXPANSION
                    recovery_dwell = 0
                else:
                    regime_state = STATE_CHOP
                    recovery_dwell = 0
        else:
            is_expansion_tech = (btc_close[t_idx] > btc_ema50[t_idx] and btc_ema20[t_idx] > btc_ema50[t_idx] and btc_adx14[t_idx] > 22.0)
            if is_expansion_tech:
                expansion_streak += 1
                chop_streak = 0
            else:
                chop_streak += 1
                expansion_streak = 0

            if regime_state == STATE_CHOP and expansion_streak >= 3:
                regime_state = STATE_EXPANSION
            elif regime_state == STATE_EXPANSION and chop_streak >= 3:
                regime_state = STATE_CHOP

        # 2. Macro 72H Rebalance Signal
        bars_since_macro += 1
        if bars_since_macro >= 18:
            bars_since_macro = 0
            ret_24h_all = np.nan_to_num((close_mat[t_idx] / close_mat[max(0, t_idx - 6)]) - 1.0, nan=0.0)
            ret_72h_all = np.nan_to_num((close_mat[t_idx] / close_mat[max(0, t_idx - 18)]) - 1.0, nan=0.0)
            mom_raw = ret_24h_all + ret_72h_all

            valid_mask = (close_mat[t_idx] > 0) & (~np.isnan(close_mat[t_idx]))
            valid_indices = np.where(valid_mask)[0]

            new_target_w = np.zeros(n_symbols)
            if len(valid_indices) >= 16:
                sorted_idx = valid_indices[np.argsort(mom_raw[valid_indices])]
                top_8_long = sorted_idx[-8:]
                top_8_short = sorted_idx[:8]

                long_w = (fixed_leverage * 0.5) / 8.0
                short_w = -(fixed_leverage * 0.5) / 8.0

                new_target_w[top_8_long] = long_w
                new_target_w[top_8_short] = short_w

            target_weights = (1.0 - turnover_lambda) * target_weights + turnover_lambda * new_target_w

        # 3. Bar t+1 Open Execution
        prev_equity = equity
        bar_rebal_volume = 0.0

        # A. Priority 1: Execute Pending Invalidation Exits at Open of next_t_idx
        for sym in list(pending_exits):
            if sym in active_positions:
                s_i = symbols.index(sym)
                cur_px = open_mat[next_t_idx, s_i]
                if np.isnan(cur_px) or cur_px <= 0:
                    cur_px = close_mat[t_idx, s_i]

                pos = active_positions[sym]
                sz = abs(pos["current_size"])
                notional = sz * cur_px
                # Taker execution for invalidation exits
                fee = notional * TAKER_FEE
                slip = notional * SLIPPAGE_BASE * 1.5
                imp = notional * (SLIPPAGE_IMPACT_COEFF * math.sqrt(notional / SLIPPAGE_REF_NOTIONAL))
                fric = fee + slip + imp

                cost_breakdown["taker_fees_usd"] += fee
                cost_breakdown["base_slippage_usd"] += slip
                cost_breakdown["market_impact_usd"] += imp
                cost_breakdown["total_traded_volume_usd"] += notional
                bar_rebal_volume += notional

                equity -= fric
                del active_positions[sym]
                target_weights[s_i] = 0.0  # Clear target weight
                invalidation_count += 1
        pending_exits.clear()

        # B. Priority 2: Execute Rebalance
        for s_i, sym in enumerate(symbols):
            tgt_w = target_weights[s_i]
            cur_pos = active_positions.get(sym)
            cur_sz = cur_pos["current_size"] if cur_pos else 0.0
            cur_px = open_mat[next_t_idx, s_i]
            if np.isnan(cur_px) or cur_px <= 0:
                cur_px = close_mat[t_idx, s_i]

            cur_notional = cur_sz * cur_px
            tgt_notional = tgt_w * equity
            delta_notional = tgt_notional - cur_notional

            if abs(delta_notional) > 10.0:
                delta_sz = delta_notional / cur_px
                fee = abs(delta_notional) * (REBALANCE_MAKER_RATIO * MAKER_FEE + REBALANCE_TAKER_RATIO * TAKER_FEE)
                slip = abs(delta_notional) * SLIPPAGE_BASE
                imp = abs(delta_notional) * (SLIPPAGE_IMPACT_COEFF * math.sqrt(abs(delta_notional) / SLIPPAGE_REF_NOTIONAL))
                fric = fee + slip + imp

                cost_breakdown["maker_fees_usd"] += abs(delta_notional) * REBALANCE_MAKER_RATIO * MAKER_FEE
                cost_breakdown["taker_fees_usd"] += abs(delta_notional) * REBALANCE_TAKER_RATIO * TAKER_FEE
                cost_breakdown["base_slippage_usd"] += slip
                cost_breakdown["market_impact_usd"] += imp
                cost_breakdown["total_traded_volume_usd"] += abs(delta_notional)
                bar_rebal_volume += abs(delta_notional)

                equity -= fric

                if abs(tgt_w) < 1e-4:
                    if sym in active_positions:
                        del active_positions[sym]
                else:
                    direction = 1 if tgt_w > 0 else -1
                    if sym not in active_positions:
                        active_positions[sym] = {
                            "direction": direction,
                            "entry_price": cur_px,
                            "current_size": delta_sz,
                            "peak_close": cur_px,
                            "trough_close": cur_px,
                            "bars_held": 0,
                        }
                    else:
                        active_positions[sym]["current_size"] += delta_sz

        # 4. Bar PnL & Funding Simulation
        bar_funding = 0.0
        bar_trading_pnl = 0.0

        for sym, pos in list(active_positions.items()):
            s_i = symbols.index(sym)
            c_prev = close_mat[t_idx, s_i]
            c_curr = close_mat[next_t_idx, s_i]
            pos_sz = pos["current_size"]

            pos_pnl = pos_sz * (c_curr - c_prev)
            bar_trading_pnl += pos_pnl

            f_rate = funding_mat[next_t_idx, s_i] if not np.isnan(funding_mat[next_t_idx, s_i]) else 0.0
            pos_notional = pos_sz * c_curr
            fund_pnl = -pos_notional * (f_rate * 0.5)
            bar_funding += fund_pnl

            pos["bars_held"] += 1
            if c_curr > pos["peak_close"]:
                pos["peak_close"] = c_curr
            if c_curr < pos["trough_close"]:
                pos["trough_close"] = c_curr

        cost_breakdown["gross_trading_pnl_usd"] += bar_trading_pnl
        cost_breakdown["funding_pnl_usd"] += bar_funding
        equity += (bar_trading_pnl + bar_funding)

        equity_curve.append(equity)
        bar_ret = (equity - prev_equity) / (prev_equity + 1e-8)
        portfolio_returns.append(bar_ret)
        turnover_history.append(bar_rebal_volume / (prev_equity + 1e-8))

        # 5. Check Close-Triggered Invalidation Rules at Close of next_t_idx
        if exit_rule != "none":
            for sym, pos in active_positions.items():
                s_i = symbols.index(sym)
                c_close = close_mat[next_t_idx, s_i]
                atr_val = atr_mat[next_t_idx, s_i] if not np.isnan(atr_mat[next_t_idx, s_i]) else (c_close * 0.02)
                direction = pos["direction"]

                if "atr_ratchet" in exit_rule:
                    if direction == 1:
                        # Long exit if close breached trailing threshold
                        ratchet_threshold = pos["peak_close"] - (atr_k * atr_val)
                        if c_close <= ratchet_threshold:
                            pending_exits.add(sym)
                    else:
                        # Short exit if close breached trailing threshold
                        ratchet_threshold = pos["trough_close"] + (atr_k * atr_val)
                        if c_close >= ratchet_threshold:
                            pending_exits.add(sym)

                elif exit_rule == "structural_72h":
                    # Check prior 18 bars (72H)
                    lookback_start = max(0, next_t_idx - 18)
                    if direction == 1:
                        prior_lowest_low = np.nanmin(low_mat[lookback_start:next_t_idx, s_i])
                        if c_close < prior_lowest_low:
                            pending_exits.add(sym)
                    else:
                        prior_highest_high = np.nanmax(high_mat[lookback_start:next_t_idx, s_i])
                        if c_close > prior_highest_high:
                            pending_exits.add(sym)

    # Economics calculation
    eq_arr = np.array(equity_curve)
    final_equity = equity
    net_cagr = ((final_equity / initial_capital) - 1.0) * 100.0

    running_max = np.maximum.accumulate(eq_arr)
    drawdowns = (running_max - eq_arr) / running_max
    max_drawdown_pct = float(np.max(drawdowns) * 100.0)

    port_ret_arr = np.array(portfolio_returns)
    mean_ret = float(np.mean(port_ret_arr))
    std_ret = float(np.std(port_ret_arr)) + 1e-8
    downside_std = float(np.std(port_ret_arr[port_ret_arr < 0])) + 1e-8

    sharpe = (mean_ret / std_ret) * math.sqrt(2190)
    sortino = (mean_ret / downside_std) * math.sqrt(2190)
    calmar = (net_cagr / max_drawdown_pct) if max_drawdown_pct > 0 else 0.0
    total_turnover = float(sum(turnover_history))

    return {
        "exit_rule": exit_rule,
        "atr_k": atr_k,
        "ending_equity": final_equity,
        "equity_multiple": final_equity / initial_capital,
        "net_cagr": net_cagr,
        "sharpe": sharpe,
        "sortino": sortino,
        "calmar": calmar,
        "max_drawdown": max_drawdown_pct,
        "total_turnover": total_turnover,
        "invalidation_count": invalidation_count,
        "total_fees": cost_breakdown["maker_fees_usd"] + cost_breakdown["taker_fees_usd"],
        "market_impact": cost_breakdown["market_impact_usd"],
        "funding_pnl": cost_breakdown["funding_pnl_usd"],
        "equity_curve": eq_arr,
    }


def main():
    print("=" * 100)
    print("      BRANCH A3: CLOSE-TRIGGERED INVALIDATION EXITS (A0 + EXITS)      ")
    print("=" * 100)

    loader = InstitutionalCompoundingEngine()
    print("--> Loading canonical data lake...")
    _, _, cached_data = loader.load_and_preprocess_data()

    experiments = [
        ("A0_Control", "none", 0.0),
        ("ATR_Ratchet_2.0", "atr_ratchet", 2.0),
        ("ATR_Ratchet_3.0", "atr_ratchet", 3.0),
        ("ATR_Ratchet_4.0", "atr_ratchet", 4.0),
        ("Structural_72H", "structural_72h", 0.0),
    ]

    results = []
    print(f"\nEvaluating {len(experiments)} invalidation exit variants...\n")

    t_start = time.time()
    for name, rule, k in experiments:
        t0 = time.time()
        print(f"--> [A3 Sweep] Rule: {name:<18} (k={k}) ...", end=" ", flush=True)
        res = run_invalidation_exit_backtest(cached_data, exit_rule=rule, atr_k=k, fixed_leverage=3.0)
        elapsed = time.time() - t0
        print(f"Done in {elapsed:.1f}s | Equity: ${res['ending_equity']:,.2f} ({res['equity_multiple']:.2f}x) | Sharpe: {res['sharpe']:.2f} | MDD: {res['max_drawdown']:.2f}% | Calmar: {res['calmar']:.2f} | Exits: {res['invalidation_count']}")
        res["name"] = name
        results.append(res)

    print(f"\nAll A3 runs completed in {time.time() - t_start:.1f}s.")

    print("\n" + "=" * 110)
    print(f"{'VARIANT':<18} {'ENDING EQ':<12} {'MULT':<8} {'CAGR':<10} {'SHARPE':<8} {'MDD':<8} {'CALMAR':<8} {'TURNOVER':<10} {'EXITS':<8}")
    print("=" * 110)
    for r in results:
        print(f"{r['name']:<18} ${r['ending_equity']:<11,.2f} {r['equity_multiple']:<7.2f}x {r['net_cagr']:<9.2f}% {r['sharpe']:<7.2f} {r['max_drawdown']:<7.2f}% {r['calmar']:<7.2f} {r['total_turnover']:<10.2f} {r['invalidation_count']:<8}")
    print("=" * 110)

    clean_summary = [{k: v for k, v in r.items() if k != "equity_curve"} for r in results]
    out_path = PIPELINE_ROOT / "data" / "branch_a3_invalidation_exits_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(clean_summary, f, indent=2)
    print(f"\nWrote full A3 results to {out_path}\n")


if __name__ == "__main__":
    main()
