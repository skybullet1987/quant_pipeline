#!/usr/bin/env python3
"""
QUANT PIPELINE UNIFIED SHADOW TELEMETRY MONITOR
===============================================
Polls and formats the real-time empirical telemetry across all 6 shadow tracks:
  1. EXP-202: Binance Trade-Tape De-Censoring
  2. EXP-103B: Adaptive Maker Pegging & Queue Economics
  3. EXP-303: Polymarket Fast-Unwind vs Hold-to-Maturity
  4. EXP-201C: Composite Recovery & Toxicity Routing
  5. EXP-401: Cross-Venue Perpetual Basis & Horizon Carry
  6. EXP-103C: Inverse-Volatility Risk Parity Sizing
"""

import os
import sys
import json
import time
from pathlib import Path

PIPELINE_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PIPELINE_ROOT / "data"

def load_json(p: Path):
    if p.exists():
        try:
            with open(p, "r") as f:
                return json.load(f)
        except Exception:
            return None
    return None

def main():
    print("\n" + "=" * 80)
    print("                QUANT PIPELINE SHADOW EXPERIMENT DASHBOARD                ")
    print(f"                     Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}                     ")
    print("=" * 80)

    # 1. EXP-202
    exp202 = load_json(DATA_DIR / "exp202" / "trade_tape_telemetry_state.json")
    print("\n[1] EXP-202: BINANCE TRADE-TAPE DE-CENSORING TELEMETRY")
    if exp202:
        m = exp202.get("metrics", {})
        print(f"  Total Sweeps Detected: {m.get('total_synthetic_sweeps', 0)} | "
              f"Matched Force Orders: {m.get('matched_force_orders', 0)} | "
              f"Precision: {m.get('precision_pct', 0.0)}%")
        print(f"  Lead Time: Mean = {m.get('lead_time_mean_ms', 0.0):.1f} ms | "
              f"P50 = {m.get('lead_time_p50_ms', 0.0):.1f} ms | "
              f"P95 = {m.get('lead_time_p95_ms', 0.0):.1f} ms")
    else:
        print("  State initializing...")

    # 2. EXP-103B
    exp103b = load_json(DATA_DIR / "exp103b_maker_shadow_state.json")
    print("\n[2] EXP-103B: ADAPTIVE MAKER PEGGING & ADVERSE SELECTION (HYPERLIQUID)")
    if exp103b:
        models = exp103b.get("models_comparison", {})
        for m_name, stats in models.items():
            print(f"  {m_name:24} | Fills: {stats.get('fills_count', 0)}/{stats.get('total_orders', 0)} "
                  f"({stats.get('fill_rate_pct', 0.0):.1f}%) | "
                  f"Adv 1s: {stats.get('mean_adverse_selection_1s_bps', 0.0):+.1f} bps | "
                  f"Net PnL: ${stats.get('cumulative_net_pnl_usd', 0.0):+.2f}")
    else:
        print("  State initializing...")

    # 3. EXP-303
    exp303 = load_json(DATA_DIR / "polymarket" / "shadow_fast_unwind_state.json")
    print("\n[3] EXP-303: POLYMARKET EXECUTABLE FAST-UNWIND VS MATURITY")
    if exp303:
        m = exp303.get("metrics", {})
        pa = m.get("policy_a_hold_to_maturity", {})
        pb1 = m.get("policy_b1_taker_unwind", {})
        pb2 = m.get("policy_b2_maker_first_scalp", {})
        print(f"  Sample: {exp303.get('sample_size', 0)} settled forward trades")
        print(f"  Policy A (Maturity):   PnL = ${pa.get('cumulative_net_pnl_usd', 0.0):+.2f} | "
              f"EV/evt = ${pa.get('ev_per_event_usd', 0.0):+.2f} | "
              f"Hold: {pa.get('median_holding_time_sec', 0.0):.0f}s | "
              f"PnL/Cap-Hr: ${pa.get('pnl_per_capital_hour', 0.0):.1f}")
        print(f"  Policy B1 (Taker Cut): PnL = ${pb1.get('cumulative_net_pnl_usd', 0.0):+.2f} | "
              f"EV/evt = ${pb1.get('ev_per_event_usd', 0.0):+.2f} | "
              f"Hold: {pb1.get('median_holding_time_sec', 0.0):.0f}s | "
              f"PnL/Cap-Hr: ${pb1.get('pnl_per_capital_hour', 0.0):.1f}")
        print(f"  Policy B2 (Maker Cut): PnL = ${pb2.get('cumulative_net_pnl_usd', 0.0):+.2f} | "
              f"EV/evt = ${pb2.get('ev_per_event_usd', 0.0):+.2f} | "
              f"Hold: {pb2.get('median_holding_time_sec', 0.0):.0f}s | "
              f"PnL/Cap-Hr: ${pb2.get('pnl_per_capital_hour', 0.0):.1f}")
    else:
        print("  State initializing...")

    # 4. EXP-201C
    ratchet = load_json(DATA_DIR / "ratchet" / "ratchet_shadow_summary.json")
    print("\n[4] EXP-201C: STANDARDIZED RECOVERY & TOXICITY ROUTING (HL RATCHET)")
    if ratchet:
        p = ratchet.get("policy_performance", {})
        total_eps = ratchet.get("sample_size", {}).get("total_independent_episodes", 0)
        print(f"  Total Independent Episodes: {total_eps}")
        for pol, d in p.items():
            print(f"  {pol:25} | Net PnL: ${d.get('cumulative_net_pnl_usd', 0.0):+.2f} | "
                  f"Mean: ${d.get('mean_net_pnl_usd', 0.0):+.4f} | "
                  f"WinRate: {d.get('win_rate_pct', 0.0):.1f}%")
    else:
        print("  State initializing...")

    # 5. EXP-401
    exp401 = load_json(DATA_DIR / "exp401" / "basis_shadow_state.json")
    print("\n[5] EXP-401: CROSS-VENUE PERPETUAL BASIS & HORIZON CARRY (BINANCE / HL)")
    if exp401:
        symbols = exp401.get("symbols", {})
        for sym, d in symbols.items():
            print(f"  {sym:4} | Mid Spread: {d.get('mid_spread_bps', 0.0):+5.1f} bps | "
                  f"8H Carry: {d.get('carry_8h_gross_bps', 0.0):+5.2f} bps | "
                  f"Net Edge (vs 21.5bp hurdle): {d.get('net_8h_edge_bps', 0.0):+5.2f} bps | "
                  f"Exceeded: {d.get('hurdle_exceeded')}")
    else:
        print("  State initializing...")

    # 6. EXP-103C
    exp103c = load_json(DATA_DIR / "exp103c_risk_parity_state.json")
    print("\n[6] EXP-103C: INVERSE-VOLATILITY RISK PARITY & FACTOR EXPOSURE")
    if exp103c:
        arms = exp103c.get("arms_comparison", {})
        findings = exp103c.get("findings", {})
        ea = arms.get("arm_a_equal_notional", {})
        ec = arms.get("arm_c_shrunk_cov_risk_parity", {})
        print(f"  Arm A (Equal Weight): Vol = {ea.get('annualized_vol_pct', 0.0):.1f}% | "
              f"BTC Beta = {ea.get('btc_factor_exposure', 0.0):.2f} | "
              f"10d CVaR_99 = {ea.get('cvar_99_10d_pct', 0.0):.1f}% | "
              f"Funding Yield = {ea.get('annualized_funding_yield_pct', 0.0):.1f}%")
        print(f"  Arm C (Risk Parity):  Vol = {ec.get('annualized_vol_pct', 0.0):.1f}% | "
              f"BTC Beta = {ec.get('btc_factor_exposure', 0.0):.2f} | "
              f"10d CVaR_99 = {ec.get('cvar_99_10d_pct', 0.0):.1f}% | "
              f"Funding Yield = {ec.get('annualized_funding_yield_pct', 0.0):.1f}%")
        print(f"  -> Volatility Reduction: -{findings.get('volatility_reduction_c_vs_a_pct', 0.0):.1f} pp | "
              f"CVaR Reduction: -{findings.get('cvar_reduction_c_vs_a_pct', 0.0):.1f} pp")
    else:
        print("  State initializing...")

    print("\n" + "=" * 80 + "\n")

if __name__ == "__main__":
    main()
