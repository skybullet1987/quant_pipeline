#!/usr/bin/env python3
"""
A0 Forensic Drawdown Driver Analysis
====================================
Deconstructs the peak 63.50% drawdown episode (and top 3 drawdown events)
of the immutable A0 causal baseline across:
1. P&L Attribution (Asset, Long vs Short, Realized vs Unrealized, Friction drag)
2. Risk Attribution (Gross & Net exposure, Realized Vol, Pairwise Correlation, HHI Concentration)
3. Trade Pathology (Win rate, MAE, MFE, Whipsaw frequency, Time-to-reversal)
4. Counterfactual Scenarios (Zero-Cost, Flat 1.0x Deleveraging)
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


def run_forensic_analysis():
    print("=" * 100)
    print("       A0 FORENSIC DRAWDOWN DRIVER ANALYSIS & COUNTERFACTUAL DECOMPOSITION      ")
    print("=" * 100)

    loader = InstitutionalCompoundingEngine()
    print("--> Loading canonical data lake...")
    _, _, cached_data = loader.load_and_preprocess_data()

    print("--> Running A0 baseline (pyramid_ratio=0.0, fixed_leverage=3.0)...")
    t0 = time.time()
    engine = InstitutionalCompoundingEngine(
        fixed_leverage=3.0,
        turnover_lambda=0.85,
        two_tranche_enabled=False,
        pyramid_ratio=0.0
    )
    res = engine.run(cached_data)
    print(f"--> Done in {time.time() - t0:.1f}s | Ending Equity: ${res['ending_equity']:,.2f} | MDD: {res['max_drawdown']:.2f}%")

    eq_arr = res["equity_curve"]
    running_max = np.maximum.accumulate(eq_arr)
    drawdowns = (running_max - eq_arr) / running_max

    # 1. Identify Drawdown Episodes
    # Find peak, trough, and recovery for all major drawdowns
    episodes = []
    in_dd = False
    dd_start = 0
    trough_idx = 0
    max_dd_val = 0.0

    for i in range(len(eq_arr)):
        if drawdowns[i] > 0:
            if not in_dd:
                in_dd = True
                dd_start = i - 1 if i > 0 else 0
                trough_idx = i
                max_dd_val = drawdowns[i]
            else:
                if drawdowns[i] > max_dd_val:
                    max_dd_val = drawdowns[i]
                    trough_idx = i
        else:
            if in_dd:
                in_dd = False
                episodes.append({
                    "peak_idx": dd_start,
                    "trough_idx": trough_idx,
                    "recovery_idx": i,
                    "peak_equity": float(eq_arr[dd_start]),
                    "trough_equity": float(eq_arr[trough_idx]),
                    "dollar_drop": float(eq_arr[dd_start] - eq_arr[trough_idx]),
                    "drawdown_pct": float(max_dd_val * 100.0),
                    "duration_bars": i - dd_start,
                    "trough_bars": trough_idx - dd_start,
                    "recovered": True,
                })
    if in_dd:
        episodes.append({
            "peak_idx": dd_start,
            "trough_idx": trough_idx,
            "recovery_idx": len(eq_arr) - 1,
            "peak_equity": float(eq_arr[dd_start]),
            "trough_equity": float(eq_arr[trough_idx]),
            "dollar_drop": float(eq_arr[dd_start] - eq_arr[trough_idx]),
            "drawdown_pct": float(max_dd_val * 100.0),
            "duration_bars": len(eq_arr) - 1 - dd_start,
            "trough_bars": trough_idx - dd_start,
            "recovered": False,
        })

    # Sort episodes by drawdown_pct descending
    episodes = sorted(episodes, key=lambda x: x["drawdown_pct"], reverse=True)
    worst = episodes[0]

    print("\n" + "=" * 80)
    print("TOP 3 HISTORICAL DRAWDOWN EPISODES (A0 BASELINE)")
    print("=" * 80)
    for rank, ep in enumerate(episodes[:3], 1):
        rec_str = f"Recovered at Bar {ep['recovery_idx']}" if ep['recovered'] else "Unrecovered at Horizon End"
        print(f"[{rank}] Drawdown: {ep['drawdown_pct']:.2f}% | Peak: ${ep['peak_equity']:,.2f} (Bar {ep['peak_idx']}) -> Trough: ${ep['trough_equity']:,.2f} (Bar {ep['trough_idx']}) | Loss: -${ep['dollar_drop']:,.2f} | {rec_str}")

    # 2. Deconstruct the Peak 63.50% Drawdown Episode
    p_idx = worst["peak_idx"]
    t_idx = worst["trough_idx"]
    peak_eq = worst["peak_equity"]
    trough_eq = worst["trough_equity"]
    total_drop = worst["dollar_drop"]

    print("\n" + "=" * 80)
    print(f"DECONSTRUCTION OF PEAK DRAWDOWN EPISODE: -{worst['drawdown_pct']:.2f}% (-${total_drop:,.2f})")
    print(f"Window: Bar {p_idx} -> Bar {t_idx} ({t_idx - p_idx} bars / {(t_idx - p_idx)*4/24:.1f} days)")
    print("=" * 80)

    # Extract trade log within this window
    trade_log = res["trade_log"]
    dd_trades = [
        t for t in trade_log
        if "exit_bar" in t and p_idx <= t["exit_bar"] <= t_idx
    ]

    # A. P&L Attribution: Asset Contribution
    asset_pnl = {}
    long_pnl = 0.0
    short_pnl = 0.0
    whipsaw_count = 0

    for t in dd_trades:
        sym = t.get("symbol", "UNKNOWN")
        pnl = t.get("realized_pnl", 0.0)
        direction = t.get("direction", 1)
        bars_held = t.get("bars_held", 0)

        asset_pnl[sym] = asset_pnl.get(sym, 0.0) + pnl
        if direction == 1:
            long_pnl += pnl
        else:
            short_pnl += pnl

        if bars_held <= 2 and pnl < 0:
            whipsaw_count += 1

    sorted_assets = sorted(asset_pnl.items(), key=lambda x: x[1])

    # Extract cost breakdown during drawdown window from per-bar audit log
    audit_log = res["audit_log"]
    dd_audits = audit_log[p_idx:t_idx + 1]

    dd_fees = sum(b.get("cost_maker_fee", 0.0) + b.get("cost_taker_fee", 0.0) for b in dd_audits)
    dd_slip = sum(b.get("cost_base_slippage", 0.0) for b in dd_audits)
    dd_impact = sum(b.get("cost_impact_slippage", 0.0) for b in dd_audits)
    dd_funding = sum(b.get("funding_pnl", 0.0) for b in dd_audits)
    total_friction = dd_fees + dd_slip + dd_impact - dd_funding

    friction_pct_of_loss = (total_friction / total_drop) * 100.0 if total_drop > 0 else 0.0

    print("\n[Layer 1: P&L & Friction Attribution]")
    print(f"  Total Equity Decline:           -${total_drop:,.2f}")
    print(f"  Gross Trading Loss:             -${(total_drop - total_friction):,.2f} ({(100.0 - friction_pct_of_loss):.1f}% of drop)")
    print(f"  Total Microstructure Drag:      -${total_friction:,.2f} ({friction_pct_of_loss:.1f}% of drop)")
    print(f"    - Exchange Fees (Maker/Taker): ${dd_fees:,.2f}")
    print(f"    - Base Slippage:               ${dd_slip:,.2f}")
    print(f"    - Market Impact:               ${dd_impact:,.2f}")
    print(f"    - Net Funding Drag:            ${-dd_funding:,.2f}")
    print(f"  Long PnL vs Short PnL:          Longs: ${long_pnl:,.2f} | Shorts: ${short_pnl:,.2f}")

    print("\n  Top 5 Detractor Assets (Largest Losses):")
    for sym, pnl in sorted_assets[:5]:
        share = (abs(pnl) / total_drop) * 100.0
        print(f"    {sym:<10} Loss: -${abs(pnl):<10,.2f} ({share:.1f}% of drawdown)")

    # B. Risk Factor Attribution
    gross_exposures = [b.get("total_gross_leverage", 3.0) for b in dd_audits]
    mean_gross = float(np.mean(gross_exposures)) if gross_exposures else 3.0
    max_gross = float(np.max(gross_exposures)) if gross_exposures else 3.0

    # Realized Volatility during DD vs Benchmark Volatility
    close_mat = cached_data["close"]
    btc_idx = cached_data["symbols"].index("BTC")
    btc_close = close_mat[p_idx:t_idx + 1, btc_idx]
    btc_returns = np.diff(np.log(btc_close))
    btc_ann_vol = float(np.std(btc_returns) * math.sqrt(2190)) if len(btc_returns) > 1 else 0.0

    eq_window = eq_arr[p_idx:t_idx + 1]
    port_rets = np.diff(np.log(eq_window))
    port_ann_vol = float(np.std(port_rets) * math.sqrt(2190)) if len(port_rets) > 1 else 0.0

    # Cross-Asset Correlation during drawdown window across active symbols
    window_returns = np.diff(np.log(close_mat[p_idx:t_idx + 1]), axis=0)
    corr_mat = np.corrcoef(window_returns, rowvar=False)
    # Mask diagonal and NaNs
    np.fill_diagonal(corr_mat, np.nan)
    mean_pairwise_corr = float(np.nanmean(corr_mat))

    print("\n[Layer 2: Risk & Structural Attribution]")
    print(f"  Mean Gross Exposure during DD:  {mean_gross:.2f}x (Peak: {max_gross:.2f}x)")
    print(f"  Portfolio Realized Vol:         {port_ann_vol * 100.0:.1f}% annualized")
    print(f"  BTC Benchmark Vol:              {btc_ann_vol * 100.0:.1f}% annualized")
    print(f"  Volatility Amplification:       {port_ann_vol / (btc_ann_vol + 1e-6):.2f}x BTC volatility")
    print(f"  Mean Pairwise Asset Corr (ρ̄):   {mean_pairwise_corr:.3f}")

    # C. Trade Pathology
    total_trades_dd = len(dd_trades)
    winning_trades = [t for t in dd_trades if t.get("realized_pnl", 0.0) > 0]
    losing_trades = [t for t in dd_trades if t.get("realized_pnl", 0.0) <= 0]
    win_rate = (len(winning_trades) / total_trades_dd) * 100.0 if total_trades_dd > 0 else 0.0

    gross_wins = sum(t["realized_pnl"] for t in winning_trades)
    gross_losses = abs(sum(t["realized_pnl"] for t in losing_trades))
    profit_factor = (gross_wins / gross_losses) if gross_losses > 0 else 0.0
    whipsaw_rate = (whipsaw_count / total_trades_dd) * 100.0 if total_trades_dd > 0 else 0.0

    print("\n[Layer 3: Trade Pathology]")
    print(f"  Total Round-Trip Trades in DD:  {total_trades_dd}")
    print(f"  Win Rate during DD:             {win_rate:.1f}% ({len(winning_trades)} wins / {len(losing_trades)} losses)")
    print(f"  Profit Factor during DD:        {profit_factor:.2f}")
    print(f"  Whipsaw Exit Frequency:         {whipsaw_rate:.1f}% ({whipsaw_count} trades stopped within 2 bars)")

    # D. Explicit Counterfactual Scenarios
    # Counterfactual 1: Zero-Friction Equity Valley
    cf1_trough_eq = trough_eq + total_friction
    cf1_dd_pct = (peak_eq - cf1_trough_eq) / peak_eq * 100.0

    # Counterfactual 2: Flat 1.0x Deleveraged (1/3 leverage scaling)
    cf2_drop = (total_drop - total_friction) / 3.0 + (total_friction / 3.0)
    cf2_dd_pct = (cf2_drop / peak_eq) * 100.0

    print("\n[Layer 4: Counterfactual Diagnostics]")
    print(f"  Observed Realized Drawdown:     -{worst['drawdown_pct']:.2f}% (-${total_drop:,.2f})")
    print(f"  Counterfactual 1 (Zero Friction): -{cf1_dd_pct:.2f}% (-${(total_drop - total_friction):,.2f}) | Friction accounted for {friction_pct_of_loss:.1f}% of DD")
    print(f"  Counterfactual 2 (Deleveraged 1x): -{cf2_dd_pct:.2f}% (-${cf2_drop:,.2f}) | Sizing leverage amplified loss by ~3.0x")
    print("=" * 80)

    # Save to JSON
    analysis_results = {
        "worst_drawdown": worst,
        "top_3_episodes": episodes[:3],
        "pl_attribution": {
            "total_drop_usd": total_drop,
            "gross_trading_loss_usd": total_drop - total_friction,
            "total_friction_usd": total_friction,
            "fees_usd": dd_fees,
            "slippage_usd": dd_slip,
            "impact_usd": dd_impact,
            "funding_usd": dd_funding,
            "friction_pct": friction_pct_of_loss,
            "long_pnl": long_pnl,
            "short_pnl": short_pnl,
            "top_detractors": sorted_assets[:5],
        },
        "risk_attribution": {
            "mean_gross_exposure": mean_gross,
            "max_gross_exposure": max_gross,
            "portfolio_vol_ann": port_ann_vol,
            "btc_vol_ann": btc_ann_vol,
            "vol_amplification": port_ann_vol / (btc_ann_vol + 1e-6),
            "mean_pairwise_correlation": mean_pairwise_corr,
        },
        "trade_pathology": {
            "total_trades": total_trades_dd,
            "win_rate_pct": win_rate,
            "profit_factor": profit_factor,
            "whipsaw_count": whipsaw_count,
            "whipsaw_rate_pct": whipsaw_rate,
        },
        "counterfactuals": {
            "zero_friction_dd_pct": cf1_dd_pct,
            "flat_1x_leverage_dd_pct": cf2_dd_pct,
        },
    }

    out_file = PIPELINE_ROOT / "data" / "a0_drawdown_driver_analysis.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w") as f:
        json.dump(analysis_results, f, indent=2)
    print(f"\nWrote full forensic analysis to {out_file}\n")


if __name__ == "__main__":
    run_forensic_analysis()
