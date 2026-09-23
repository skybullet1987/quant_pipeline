#!/usr/bin/env python3
"""
Branch A1: Causal Pyramiding Ablation Sweep
==========================================
Isolates whether adding exposure to winning positions adds genuine predictive alpha
when execution artifacts are strictly eliminated.

Physics Standard:
- Breakout condition evaluated at bar t close (close_t >= entry + 2.0 * atr_0).
- Execution strictly at bar t+1 open with base slippage, square-root impact, and exchange fees.
- Risk caps enforced against portfolio equity at fill time.
- Sweep: pyramid_ratio in [0.00, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30].

Evaluation Metrics (No double-counting):
1. Primary: Delta CAGR_net = CAGR_A1 - CAGR_A0
2. Cost Decomposition: Delta Cost = Delta Fees + Delta Impact + Delta Funding
3. Incremental Pyramid Trade Expectancy: E[R_pyr,net] = sum(PnL_pyr,net) / sum(Capital_pyr)
4. Log Wealth Delta: Delta LogWealth = ln(W_A1 / W_A0)
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

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


def run_causal_pyramid_backtest(
    cached_data: Dict[str, Any],
    pyramid_ratio: float = 0.0,
    fixed_leverage: float = 3.0,
    turnover_lambda: float = 0.85,
    enforce_pyramid_risk_caps: bool = True,
) -> Dict[str, Any]:
    """
    Executes a causal backtest where pyramiding triggers are evaluated at close of bar t,
    and executed at open of bar t+1 with slippage and market impact.
    Tracks exact incremental pyramid capital and PnL.
    """
    symbols = cached_data["symbols"]
    n_symbols = len(symbols)
    btc_idx = symbols.index(BENCHMARK_SYMBOL)

    close_mat = cached_data["close"]
    open_mat = cached_data["open"]
    high_mat = cached_data["high"]
    low_mat = cached_data["low"]
    volume_mat = cached_data["volume"]
    oracle_mat = cached_data["oracle"]
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

    # Active positions dict: sym -> state dict
    active_positions: Dict[str, Dict[str, Any]] = {}
    pending_pyramids: set = set()

    cost_breakdown = {
        "maker_fees_usd": 0.0,
        "taker_fees_usd": 0.0,
        "base_slippage_usd": 0.0,
        "market_impact_usd": 0.0,
        "stop_gap_cost_usd": 0.0,
        "funding_pnl_usd": 0.0,
        "gross_trading_pnl_usd": 0.0,
        "total_traded_volume_usd": 0.0,
        "pyramid_allocated_capital_usd": 0.0,
        "pyramid_net_pnl_usd": 0.0,
        "pyramid_count": 0,
    }

    pyramid_pnl_list: List[float] = []
    trade_count = 0

    # Macro 72H Cadence (every 18 bars)
    target_weights = np.zeros(n_symbols)
    bars_since_macro = 18

    for t_idx in range(TOTAL_EVAL_BARS - 1):
        next_t_idx = t_idx + 1

        # ----------------------------------------------------------------------
        # 1. Regime Detection (Strictly from close of t_idx)
        # ----------------------------------------------------------------------
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

        # ----------------------------------------------------------------------
        # 2. Macro 72H Signal Calculation (every 18 bars)
        # ----------------------------------------------------------------------
        bars_since_macro += 1
        if bars_since_macro >= 18:
            bars_since_macro = 0
            # Alpha calculation strictly using information available at t_idx
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

            # Apply turnover dampening
            target_weights = (1.0 - turnover_lambda) * target_weights + turnover_lambda * new_target_w

        # ----------------------------------------------------------------------
        # 3. Bar t+1 Open Execution: Rebalance & Fills
        # ----------------------------------------------------------------------
        prev_equity = equity
        bar_rebal_volume = 0.0

        # A. Execute Macro Target Adjustments at Open of next_t_idx
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

            if abs(delta_notional) > 10.0:  # $10 minimum notional threshold
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
                    atr_0 = atr_mat[t_idx, s_i] if not np.isnan(atr_mat[t_idx, s_i]) else (cur_px * 0.02)
                    if sym not in active_positions:
                        active_positions[sym] = {
                            "direction": direction,
                            "entry_price": cur_px,
                            "current_size": delta_sz,
                            "base_size": delta_sz,
                            "atr_0": atr_0,
                            "pyramided": False,
                            "pyramid_size": 0.0,
                            "pyramid_entry_px": 0.0,
                            "pyramid_fric": 0.0,
                            "bars_held": 0,
                        }
                        trade_count += 1
                    else:
                        active_positions[sym]["current_size"] += delta_sz
                        active_positions[sym]["base_size"] = active_positions[sym]["current_size"]

        # ----------------------------------------------------------------------
        # B. Causal Pyramiding Execution at Open of next_t_idx
        # ----------------------------------------------------------------------
        if pyramid_ratio > 0.0 and len(pending_pyramids) > 0:
            for sym in list(pending_pyramids):
                pos = active_positions.get(sym)
                if pos is not None and not pos["pyramided"]:
                    s_i = symbols.index(sym)
                    open_p = open_mat[next_t_idx, s_i]
                    if np.isnan(open_p) or open_p <= 0:
                        open_p = close_mat[t_idx, s_i]

                    pyr_fill_px = open_p * (1.0 + SLIPPAGE_BASE) if pos["direction"] == 1 else open_p * (1.0 - SLIPPAGE_BASE)
                    add_size = pyramid_ratio * abs(pos["base_size"])

                    # Risk cap: max 25% of equity per position
                    if enforce_pyramid_risk_caps:
                        max_sz = (0.25 * equity) / pyr_fill_px
                        if abs(pos["current_size"]) + add_size > max_sz:
                            add_size = max(0.0, max_sz - abs(pos["current_size"]))

                    if add_size > 1e-6:
                        add_notional = add_size * pyr_fill_px
                        p_fee = add_notional * (REBALANCE_MAKER_RATIO * MAKER_FEE + REBALANCE_TAKER_RATIO * TAKER_FEE)
                        p_slip = add_notional * SLIPPAGE_BASE
                        p_imp = add_notional * (SLIPPAGE_IMPACT_COEFF * math.sqrt(add_notional / SLIPPAGE_REF_NOTIONAL))
                        p_fric = p_fee + p_slip + p_imp

                        cost_breakdown["maker_fees_usd"] += add_notional * REBALANCE_MAKER_RATIO * MAKER_FEE
                        cost_breakdown["taker_fees_usd"] += add_notional * REBALANCE_TAKER_RATIO * TAKER_FEE
                        cost_breakdown["base_slippage_usd"] += p_slip
                        cost_breakdown["market_impact_usd"] += p_imp
                        cost_breakdown["total_traded_volume_usd"] += add_notional
                        cost_breakdown["pyramid_allocated_capital_usd"] += add_notional
                        cost_breakdown["pyramid_count"] += 1

                        equity -= p_fric

                        # Expand position
                        signed_add = add_size * pos["direction"]
                        pos["current_size"] += signed_add
                        pos["pyramided"] = True
                        pos["pyramid_size"] = add_size
                        pos["pyramid_entry_px"] = pyr_fill_px
                        pos["pyramid_fric"] = p_fric

            pending_pyramids.clear()

        # ----------------------------------------------------------------------
        # 4. Bar PnL & Funding Simulation through next_t_idx Close
        # ----------------------------------------------------------------------
        bar_funding = 0.0
        bar_trading_pnl = 0.0

        for sym, pos in list(active_positions.items()):
            s_i = symbols.index(sym)
            c_prev = close_mat[t_idx, s_i]
            c_curr = close_mat[next_t_idx, s_i]
            pos_sz = pos["current_size"]

            # Bar trading PnL
            pos_pnl = pos_sz * (c_curr - c_prev)
            bar_trading_pnl += pos_pnl

            # Funding (every bar represents 4H, Hyperliquid funding is 8H)
            f_rate = funding_mat[next_t_idx, s_i] if not np.isnan(funding_mat[next_t_idx, s_i]) else 0.0
            pos_notional = pos_sz * c_curr
            fund_pnl = -pos_notional * (f_rate * 0.5)
            bar_funding += fund_pnl

            pos["bars_held"] += 1

            # Check if position has an active pyramid tranche; track its cumulative PnL
            if pos["pyramided"] and pos["pyramid_size"] > 0:
                pyr_sz = pos["pyramid_size"]
                pyr_pnl_incremental = pyr_sz * (c_curr - c_prev) * pos["direction"]
                cost_breakdown["pyramid_net_pnl_usd"] += pyr_pnl_incremental

        cost_breakdown["gross_trading_pnl_usd"] += bar_trading_pnl
        cost_breakdown["funding_pnl_usd"] += bar_funding
        equity += (bar_trading_pnl + bar_funding)

        equity_curve.append(equity)
        bar_ret = (equity - prev_equity) / (prev_equity + 1e-8)
        portfolio_returns.append(bar_ret)
        turnover_history.append(bar_rebal_volume / (prev_equity + 1e-8))

        # ----------------------------------------------------------------------
        # 5. Check Breakout Condition at Close of next_t_idx for Bar t+2 Queue
        # ----------------------------------------------------------------------
        if pyramid_ratio > 0.0:
            for sym, pos in active_positions.items():
                if not pos["pyramided"]:
                    s_i = symbols.index(sym)
                    c_close = close_mat[next_t_idx, s_i]
                    atr_0 = pos["atr_0"]
                    entry_px = pos["entry_price"]
                    direction = pos["direction"]

                    if direction == 1 and c_close >= (entry_px + 2.0 * atr_0):
                        pending_pyramids.add(sym)
                    elif direction == -1 and c_close <= (entry_px - 2.0 * atr_0):
                        pending_pyramids.add(sym)

    # --------------------------------------------------------------------------
    # Compute Final Economics
    # --------------------------------------------------------------------------
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
    avg_turnover = (total_turnover / TOTAL_EVAL_BARS) * 100.0

    tot_fees = cost_breakdown["maker_fees_usd"] + cost_breakdown["taker_fees_usd"]
    tot_impact = cost_breakdown["market_impact_usd"]
    tot_base_slip = cost_breakdown["base_slippage_usd"]
    tot_funding = cost_breakdown["funding_pnl_usd"]

    pyr_allocated = cost_breakdown["pyramid_allocated_capital_usd"]
    pyr_net_pnl = cost_breakdown["pyramid_net_pnl_usd"]
    pyr_expectancy = (pyr_net_pnl / (pyr_allocated + 1e-8)) * 100.0 if pyr_allocated > 0 else 0.0

    return {
        "pyramid_ratio": pyramid_ratio,
        "ending_equity": final_equity,
        "equity_multiple": final_equity / initial_capital,
        "net_cagr": net_cagr,
        "sharpe": sharpe,
        "sortino": sortino,
        "calmar": calmar,
        "max_drawdown": max_drawdown_pct,
        "total_trades": trade_count,
        "total_turnover": total_turnover,
        "avg_turnover_bar": avg_turnover,
        "total_fees": tot_fees,
        "base_slippage": tot_base_slip,
        "market_impact": tot_impact,
        "funding_pnl": tot_funding,
        "total_traded_volume": cost_breakdown["total_traded_volume_usd"],
        "pyramid_count": cost_breakdown["pyramid_count"],
        "pyramid_allocated_capital": pyr_allocated,
        "pyramid_net_pnl": pyr_net_pnl,
        "pyramid_expectancy_pct": pyr_expectancy,
        "equity_curve": eq_arr,
    }


def main():
    print("=" * 100)
    print("      BRANCH A1: CAUSAL PYRAMIDING ABLATION SWEEP (Next-Bar Open Standard)      ")
    print("=" * 100)

    loader = InstitutionalCompoundingEngine()
    print("--> Loading canonical data lake...")
    _, _, cached_data = loader.load_and_preprocess_data()

    sweep_ratios = [0.00, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30]
    results = []

    print(f"\nEvaluating {len(sweep_ratios)} configurations under strict t+1 causal execution...\n")

    t_start = time.time()
    for ratio in sweep_ratios:
        t0 = time.time()
        print(f"--> [A1 Sweep] Running pyramid_ratio = {ratio:.2f} ...", end=" ", flush=True)
        res = run_causal_pyramid_backtest(cached_data, pyramid_ratio=ratio, fixed_leverage=3.0)
        elapsed = time.time() - t0
        print(f"Done in {elapsed:.1f}s | Equity: ${res['ending_equity']:,.2f} ({res['equity_multiple']:.2f}x) | Sharpe: {res['sharpe']:.2f} | MDD: {res['max_drawdown']:.2f}%")
        results.append(res)

    print(f"\nAll sweep runs completed in {time.time() - t_start:.1f}s.")

    # Base reference A0 (pyramid_ratio=0.00)
    a0 = results[0]
    a0_equity = a0["ending_equity"]
    a0_cagr = a0["net_cagr"]
    a0_sharpe = a0["sharpe"]
    a0_mdd = a0["max_drawdown"]
    a0_cost = a0["total_fees"] + a0["market_impact"] + a0["funding_pnl"]

    print("\n" + "=" * 115)
    print(f"{'RATIO':<8} {'ENDING EQ':<12} {'MULT':<8} {'CAGR':<10} {'SHARPE':<8} {'MDD':<8} {'CALMAR':<8} {'ΔCAGR_net':<11} {'ΔLogWealth':<12} {'E[R_pyr]%':<10} {'PYR COUNT':<10}")
    print("=" * 115)

    summary_rows = []
    for r in results:
        ratio = r["pyramid_ratio"]
        eq = r["ending_equity"]
        mult = r["equity_multiple"]
        cagr = r["net_cagr"]
        sharpe = r["sharpe"]
        mdd = r["max_drawdown"]
        calmar = r["calmar"]

        delta_cagr = cagr - a0_cagr
        delta_log_w = math.log(eq / a0_equity)
        e_pyr = r["pyramid_expectancy_pct"]
        pyr_count = r["pyramid_count"]

        print(f"{ratio:<8.2f} ${eq:<11,.2f} {mult:<7.2f}x {cagr:<9.2f}% {sharpe:<7.2f} {mdd:<7.2f}% {calmar:<7.2f} {delta_cagr:<+10.2f}% {delta_log_w:<+11.4f} {e_pyr:<9.2f}% {pyr_count:<10}")

        summary_rows.append({
            "pyramid_ratio": ratio,
            "ending_equity": eq,
            "equity_multiple": mult,
            "cagr_pct": cagr,
            "sharpe": sharpe,
            "sortino": r["sortino"],
            "calmar": calmar,
            "max_drawdown_pct": mdd,
            "total_turnover": r["total_turnover"],
            "total_fees": r["total_fees"],
            "market_impact": r["market_impact"],
            "funding_pnl": r["funding_pnl"],
            "delta_cagr_net": delta_cagr,
            "delta_log_wealth": delta_log_w,
            "pyramid_count": pyr_count,
            "pyramid_expectancy_pct": e_pyr,
            "pyramid_allocated_capital": r["pyramid_allocated_capital"],
            "pyramid_net_pnl": r["pyramid_net_pnl"],
        })

    print("=" * 115)

    # Save summary artifact
    out_path = PIPELINE_ROOT / "data" / "branch_a1_pyramiding_sweep_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(summary_rows, f, indent=2)
    print(f"\nWrote full A1 sweep ledger to {out_path}")


if __name__ == "__main__":
    main()
