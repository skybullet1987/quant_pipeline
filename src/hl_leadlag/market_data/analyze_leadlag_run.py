"""Institutional Lead-Lag & Staleness Horizon Analysis Protocol (Frozen Gate 1).

Evaluates empirical market microstructure captures produced by dual_recorder.py.
Enforces the Frozen Evaluation Protocol:
1. Binance Shock Sweeps (N): Rolling volume sweeps >= $1.5M within <= 100ms.
2. Multi-Horizon Markout: M_100ms, M_250ms, M_500ms, M_1s, M_2s, M_3s, M_5s.
3. Razor-Thin Fee Model: 9.0 bps round-trip taker fees (Hyperliquid Tier 0: 4.5 bps entry + 4.5 bps exit).
4. Friction Hurdle: Half-spread (0.5 to 1.0 bps) + slippage buffer (1.0 bps) -> 11.5 bps total hurdle.
5. Stationary Block Bootstrap: Lower Confidence Bound (LCB_95%) under serial dependence.
6. Scratch-Loss Distribution: PnL distribution for trades exited at the 3-second horizon.
7. Tail Risk: 99th percentile Maximum Adverse Excursion (MAE).
8. Counterfactual Latency Decay: Degradation across +5ms, +10ms, +25ms, +50ms, +100ms artificial delay.

ISOLATION INVARIANT:
Strictly contained under src/hl_leadlag/market_data/.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
import pyarrow.parquet as pq


def stationary_bootstrap_lcb(data: np.ndarray, block_len: int = 10, n_boot: int = 2000, alpha: float = 0.05) -> float:
    """Calculate 95% Lower Confidence Bound using stationary block bootstrap."""
    n = len(data)
    if n < 5:
        return float(np.mean(data)) if n > 0 else 0.0

    p = 1.0 / max(1.0, float(block_len))
    boot_means = np.empty(n_boot)

    for b in range(n_boot):
        indices = np.empty(n, dtype=int)
        idx = np.random.randint(0, n)
        for i in range(n):
            if np.random.rand() < p:
                idx = np.random.randint(0, n)
            else:
                idx = (idx + 1) % n
            indices[i] = idx
        boot_means[b] = np.mean(data[indices])

    return float(np.percentile(boot_means, alpha * 100))


def analyze_leadlag_capture(
    parquet_path: str,
    sweep_threshold_usd: float = 1_500_000.0,
    sweep_window_ms: float = 100.0,
    taker_fee_rt_bps: float = 9.0,      # 4.5 bps entry + 4.5 bps exit
    half_spread_bps: float = 1.0,       # 1.0 bp half-spread
    slippage_buffer_bps: float = 1.5,   # 1.5 bps execution/queue buffer
) -> Dict[str, Any]:
    path = Path(parquet_path)
    if not path.exists():
        print(f"Error: Parquet file {parquet_path} not found.")
        return {}

    table = pq.read_table(str(path))
    df = table.to_pandas()
    print(f"================================================================================")
    print(f"=== TOKYO LEAD-LAG CAUSAL REPLAY AUDIT: {path.name} ===")
    print(f"================================================================================")
    print(f"Total Microsecond Tick Records Loaded: {len(df):,}")

    df = df.sort_values("local_mono_ns").reset_index(drop=True)

    counts = df.groupby(["venue", "event_type"]).size()
    print("\n--- Event Distribution ---")
    for (venue, ev_type), count in counts.items():
        print(f"  {venue.upper():12s} | {ev_type:10s} : {count:10,d} events")

    trades = df[(df["venue"] == "binance") & (df["event_type"] == "trade")].copy()
    hl_books = df[(df["venue"] == "hyperliquid") & (df["event_type"] == "book")].copy()

    if len(trades) == 0 or len(hl_books) == 0:
        print("\n[!] Error: Insufficient multi-venue events to compute causal lead-lag replay.")
        return {"n_events": len(df), "sweeps": 0}

    hl_books["hl_mid"] = (hl_books["best_bid"] + hl_books["best_ask"]) / 2.0
    hl_times = hl_books["local_mono_ns"].values
    hl_bids = hl_books["best_bid"].values
    hl_asks = hl_books["best_ask"].values
    hl_mids = hl_books["hl_mid"].values

    trades["notional"] = trades["price"] * trades["size"]
    window_ns = int(sweep_window_ms * 1_000_000)

    trade_times = trades["local_mono_ns"].values
    trade_notionals = trades["notional"].values
    trade_sides = trades["side"].values
    trade_prices = trades["price"].values

    horizons_ms = [100, 250, 500, 1000, 2000, 3000, 5000]
    total_friction_bps = taker_fee_rt_bps + half_spread_bps + slippage_buffer_bps

    sweeps: List[Dict[str, Any]] = []

    # Sweep detection loop with 5-second refractory lockout
    last_trigger_ns = -5_000_000_000
    for i in range(len(trades)):
        t_start = trade_times[i]
        if (t_start - last_trigger_ns) < 5_000_000_000:
            continue

        t_cutoff = t_start + window_ns
        idx_end = np.searchsorted(trade_times, t_cutoff, side="right")

        window_notionals = trade_notionals[i:idx_end]
        window_sides = trade_sides[i:idx_end]

        buy_vol = window_notionals[window_sides == "buy"].sum()
        sell_vol = window_notionals[window_sides == "sell"].sum()

        is_buy_sweep = buy_vol >= sweep_threshold_usd
        is_sell_sweep = sell_vol >= sweep_threshold_usd

        if not (is_buy_sweep or is_sell_sweep):
            continue

        side = "BUY" if is_buy_sweep else "SELL"
        sweep_vol = buy_vol if is_buy_sweep else sell_vol
        last_trigger_ns = t_start

        # Baseline execution arrival at Hyperliquid (+4.5 ms Tokyo metro latency + signing)
        t_arrive = t_start + int(4.5 * 1_000_000)
        hl_idx_arrive = np.searchsorted(hl_times, t_arrive, side="right") - 1

        if hl_idx_arrive < 0 or hl_idx_arrive >= len(hl_times):
            continue

        fill_px = hl_asks[hl_idx_arrive] if side == "BUY" else hl_bids[hl_idx_arrive]
        pre_mid = hl_mids[hl_idx_arrive]

        # Multi-horizon markout calculation
        markouts_bps = {}
        for h_ms in horizons_ms:
            t_h = t_arrive + int(h_ms * 1_000_000)
            idx_h = np.searchsorted(hl_times, t_h, side="right") - 1
            if idx_h >= 0 and idx_h < len(hl_times):
                mid_h = hl_mids[idx_h]
                if side == "BUY":
                    m_bps = ((mid_h - fill_px) / fill_px) * 10000.0
                else:
                    m_bps = ((fill_px - mid_h) / fill_px) * 10000.0
                markouts_bps[f"M_{h_ms}ms"] = m_bps
            else:
                markouts_bps[f"M_{h_ms}ms"] = np.nan

        # Measure Maximum Adverse Excursion (MAE) over 3 seconds
        t_3s = t_arrive + 3_000_000_000
        idx_3s = np.searchsorted(hl_times, t_3s, side="right")
        window_hl_mids = hl_mids[hl_idx_arrive:idx_3s]

        if len(window_hl_mids) > 0:
            if side == "BUY":
                min_mid = np.min(window_hl_mids)
                mae_bps = ((fill_px - min_mid) / fill_px) * 10000.0
            else:
                max_mid = np.max(window_hl_mids)
                mae_bps = ((max_mid - fill_px) / fill_px) * 10000.0
        else:
            mae_bps = 0.0

        # Counterfactual Latency Delays (+5ms, +10ms, +25ms, +50ms, +100ms)
        counterfactuals = {}
        for delay_ms in [5, 10, 25, 50, 100]:
            t_delayed = t_arrive + int(delay_ms * 1_000_000)
            idx_del = np.searchsorted(hl_times, t_delayed, side="right") - 1
            if idx_del >= 0 and idx_del < len(hl_times):
                delayed_fill = hl_asks[idx_del] if side == "BUY" else hl_bids[idx_del]
                # Compare 1s markout from delayed fill
                t_1s = t_delayed + 1_000_000_000
                idx_1s = np.searchsorted(hl_times, t_1s, side="right") - 1
                if idx_1s >= 0 and idx_1s < len(hl_times):
                    mid_1s = hl_mids[idx_1s]
                    if side == "BUY":
                        cf_edge = ((mid_1s - delayed_fill) / delayed_fill) * 10000.0
                    else:
                        cf_edge = ((delayed_fill - mid_1s) / delayed_fill) * 10000.0
                    counterfactuals[f"CF_+{delay_ms}ms"] = cf_edge

        record = {
            "time_ns": t_start,
            "side": side,
            "volume_usd": sweep_vol,
            "binance_px": trade_prices[i],
            "hl_fill_px": fill_px,
            "mae_bps": mae_bps,
            **markouts_bps,
            **counterfactuals,
        }
        sweeps.append(record)

    sweep_df = pd.DataFrame(sweeps)
    n_sweeps = len(sweep_df)

    print(f"\n================================================================================")
    print(f"=== FROZEN DIAGNOSTIC EVALUATION TABLE (N = {n_sweeps}) ===")
    print(f"================================================================================")
    print(f"Volume Sweep Hurdle     : >= ${sweep_threshold_usd:,.0f} in <= {sweep_window_ms:.0f} ms")
    print(f"Taker Round-Trip Fees   : -{taker_fee_rt_bps:.1f} bps (4.5 bps entry + 4.5 bps exit)")
    print(f"Spread & Slippage Hurdle: -{half_spread_bps + slippage_buffer_bps:.1f} bps (0.5-1.0 bp half-spread + buffer)")
    print(f"Total Execution Hurdle  : -{total_friction_bps:.1f} bps")

    if n_sweeps == 0:
        print(f"\n[!] ZERO sweeps met the >= ${sweep_threshold_usd:,.0f} threshold during this 1-hour window.")
        print("    Regime Assessment: Quiet early Asian session (volatility clustering absent).")
        print("    Protocol Rule: Extend capture into London/NY overlap (12:00-16:00 UTC).")
        return {"n_sweeps": 0, "verdict": "INSUFFICIENT_VOLATILITY"}

    # 1. Multi-Horizon Gross Markout Table
    print("\n--- Multi-Horizon Markout Profile (Gross bps) ---")
    print(f"{'Horizon':10s} | {'Mean':8s} | {'Median':8s} | {'P25':8s} | {'P75':8s} | {'P90':8s}")
    print("-" * 60)
    for h in horizons_ms:
        col = f"M_{h}ms"
        vals = sweep_df[col].dropna()
        print(
            f"{col:10s} | {vals.mean():+7.2f} | {vals.median():+7.2f} | "
            f"{vals.quantile(0.25):+7.2f} | {vals.quantile(0.75):+7.2f} | {vals.quantile(0.90):+7.2f}"
        )

    # 2. Net Markout & LCB95 Calculation at 1s and 3s Horizons
    m1s_gross = sweep_df["M_1000ms"].dropna().values
    m3s_gross = sweep_df["M_3000ms"].dropna().values

    m1s_net = m1s_gross - total_friction_bps
    m3s_net = m3s_gross - total_friction_bps

    lcb_1s = stationary_bootstrap_lcb(m1s_net)
    lcb_3s = stationary_bootstrap_lcb(m3s_net)

    print("\n--- Net Expectancy vs. 11.5 bps Execution Hurdle ---")
    print(f"1-Second Horizon (M_1s) : Gross Mean={np.mean(m1s_gross):+.2f} bps | Net Mean={np.mean(m1s_net):+.2f} bps | LCB_95%={lcb_1s:+.2f} bps")
    print(f"3-Second Horizon (M_3s) : Gross Mean={np.mean(m3s_gross):+.2f} bps | Net Mean={np.mean(m3s_net):+.2f} bps | LCB_95%={lcb_3s:+.2f} bps")

    # 3. Scratch Loss Distribution (3-Second Horizon)
    scratch_losses = sweep_df[sweep_df["M_3000ms"] <= 0]["M_3000ms"] - total_friction_bps
    print("\n--- 3-Second Scratch-Loss Profile ---")
    if len(scratch_losses) > 0:
        print(f"  Scratch Frequency : {len(scratch_losses)} / {n_sweeps} ({len(scratch_losses)/n_sweeps * 100:.1f}%)")
        print(f"  Scratch Mean Loss : {scratch_losses.mean():.2f} bps")
        print(f"  Scratch Median    : {scratch_losses.median():.2f} bps")
        print(f"  Scratch P90 Loss  : {scratch_losses.quantile(0.10):.2f} bps")
    else:
        print("  Zero scratch exits observed.")

    # 4. Tail Loss (99th Percentile Maximum Adverse Excursion)
    mae_99 = sweep_df["mae_bps"].quantile(0.99)
    print(f"\n--- Tail Risk (Maximum Adverse Excursion) ---")
    print(f"  MAE P50 (Median Adverse Excursion) : {sweep_df['mae_bps'].median():.2f} bps")
    print(f"  MAE P95                            : {sweep_df['mae_bps'].quantile(0.95):.2f} bps")
    print(f"  MAE P99 (Worst 1% Gap Risk)       : {mae_99:.2f} bps")

    # 5. Counterfactual Latency Decay
    print("\n--- Counterfactual Latency Decay Test (1-Second Net Edge) ---")
    print(f"{'Arrival Delay':15s} | {'Gross Edge':12s} | {'Net Edge (Post 11.5bps)':24s}")
    print("-" * 55)
    for delay_ms in [0, 5, 10, 25, 50, 100]:
        if delay_ms == 0:
            cf_vals = m1s_gross
        else:
            cf_vals = sweep_df[f"CF_+{delay_ms}ms"].dropna().values

        gross_cf = np.mean(cf_vals) if len(cf_vals) > 0 else 0.0
        net_cf = gross_cf - total_friction_bps
        print(f"+{delay_ms:3d} ms delay    | {gross_cf:+9.2f} bps | {net_cf:+12.2f} bps")

    # 6. Hard Falsification Verdict
    print("\n================================================================================")
    print("=== FALSIFICATION GATE VERDICT ===")
    print("================================================================================")
    passed_lcb = lcb_1s > 0 or lcb_3s > 0
    passed_sample = n_sweeps >= 15

    if not passed_sample:
        verdict = "INSUFFICIENT_SAMPLE_SIZE"
        print(f"VERDICT: {verdict} (N = {n_sweeps} < 15 required). Extend recording window.")
    elif passed_lcb:
        verdict = "PASS_EDGE_CONFIRMED"
        print(f"VERDICT: {verdict} (LCB_95% = {max(lcb_1s, lcb_3s):+.2f} bps > 0). Proceed to Shadow Daemon.")
    else:
        verdict = "FAIL_NEGATIVE_EXPECTANCY"
        print(f"VERDICT: {verdict} (LCB_95% = {max(lcb_1s, lcb_3s):+.2f} bps <= 0). Terminate Option D.")

    return {
        "n_sweeps": n_sweeps,
        "lcb_1s": lcb_1s,
        "lcb_3s": lcb_3s,
        "mae_99": mae_99,
        "verdict": verdict,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Institutional Lead-Lag Parquet Audit")
    parser.add_argument("parquet_file", help="Path to Parquet file")
    parser.add_argument("--threshold", type=float, default=1_500_000.0, help="Volume threshold in USD")
    args = parser.parse_args()

    analyze_leadlag_capture(args.parquet_file, sweep_threshold_usd=args.threshold)
