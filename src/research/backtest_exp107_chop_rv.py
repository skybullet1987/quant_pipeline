#!/usr/bin/env python3
"""
BACKTEST: EXP-107 CHOP RELATIVE-VALUE SLEEVE (FAST VECTORIZED)
=============================================================
Evaluates beta-neutral relative-value pair trading exclusively when EXP-103
is in CASH_FLOOR_fl0 (rho_7d <= -0.10).
"""

import sys
import json
import numpy as np
import pandas as pd
from pathlib import Path

PIPELINE_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PIPELINE_ROOT / "data"
LAKE_DIR = DATA_DIR / "lake"

def run_backtest():
    print("=" * 80)
    print("  EXP-107: CHOP RV SLEEVE (BETA-NEUTRAL TIME-SERIES SPREADS) BACKTEST")
    print("=" * 80)

    # 1. Load Data Lake
    df_c = pd.read_parquet(LAKE_DIR / "raw_candles_4h.parquet")
    df_c['dt'] = pd.to_datetime(df_c['timestamp_ms'], unit='ms')
    df_close = df_c.pivot(index='dt', columns='symbol', values='close').sort_index()

    pairs = [
        ('SOL', 'ETH'),
        ('SUI', 'SOL'),
        ('AVAX', 'SOL'),
        ('LINK', 'ETH'),
        ('DOGE', 'SOL')
    ]

    all_symbols = ['BTC'] + list(set([s for p in pairs for s in p]))
    available = [s for s in all_symbols if s in df_close.columns]
    
    df_close_sub = df_close[available].dropna(subset=['BTC'])
    df_rets = df_close_sub.pct_change().fillna(0.0)

    n_bars = len(df_rets)
    btc_rets = df_rets['BTC'].values

    w_rho = 42 # 7 days
    w_beta = 180 # 30 days

    # 2. Precompute rho_t across all bars
    print("Precomputing rho_7d series...")
    alt_symbols = [s for s in available if s != 'BTC']
    alt_mat = df_rets[alt_symbols].values
    
    rho_arr = np.zeros(n_bars)
    for t in range(w_rho + 1, n_bars):
        sub = alt_mat[t - w_rho : t]
        r_curr = sub[1:]
        r_lag = sub[:-1]
        r_c_dm = r_curr - np.mean(r_curr, axis=0, keepdims=True)
        r_l_dm = r_lag - np.mean(r_lag, axis=0, keepdims=True)
        nom = np.sum(r_c_dm * r_l_dm, axis=0)
        denom = np.sqrt(np.sum(r_c_dm**2, axis=0) * np.sum(r_l_dm**2, axis=0)) + 1e-12
        corrs = nom / denom
        valid = corrs[np.isfinite(corrs)]
        if len(valid) >= 3:
            rho_arr[t] = float(np.mean(valid))

    print(f"Precomputed {n_bars} bars of rho. Running pair simulation...")

    rv_pnl = np.zeros(n_bars)
    trades_count = 0
    wins_count = 0
    losses_count = 0
    fl0_bars_count = 0

    open_positions = {}

    for t in range(w_beta + 10, n_bars - 1):
        is_fl0 = (rho_arr[t] <= -0.1000)

        if not is_fl0:
            open_positions.clear()
            continue

        fl0_bars_count += 1
        r_btc_w = btc_rets[t - w_beta : t]
        var_btc = np.var(r_btc_w) + 1e-12

        for sym_a, sym_b in pairs:
            if sym_a not in df_rets.columns or sym_b not in df_rets.columns:
                continue

            pair_id = f"{sym_a}_{sym_b}"

            r_a_w = df_rets[sym_a].values[t - w_beta : t]
            r_b_w = df_rets[sym_b].values[t - w_beta : t]

            beta_a = np.cov(r_a_w, r_btc_w)[0, 1] / var_btc
            beta_b = np.cov(r_b_w, r_btc_w)[0, 1] / var_btc

            spread_w = (r_a_w - beta_a * r_btc_w) - (r_b_w - beta_b * r_btc_w)
            spread_mean = np.mean(spread_w)
            spread_std = np.std(spread_w) + 1e-12

            current_spread = spread_w[-1]
            z_t = (current_spread - spread_mean) / spread_std

            # Exit condition
            if pair_id in open_positions:
                pos = open_positions[pair_id]
                bars_held = t - pos['entry_t']
                if abs(z_t) < 0.50 or bars_held >= 6:
                    r_a_fwd = df_rets[sym_a].values[t]
                    r_b_fwd = df_rets[sym_b].values[t]
                    gross = pos['direction'] * (pos['w_a'] * r_a_fwd - pos['w_b'] * r_b_fwd)
                    friction = (pos['w_a'] + pos['w_b']) * 0.00045 # exit fee
                    net = gross - friction
                    rv_pnl[t] += net
                    trades_count += 1
                    if net > 0:
                        wins_count += 1
                    else:
                        losses_count += 1
                    del open_positions[pair_id]
                else:
                    r_a_fwd = df_rets[sym_a].values[t]
                    r_b_fwd = df_rets[sym_b].values[t]
                    gross = pos['direction'] * (pos['w_a'] * r_a_fwd - pos['w_b'] * r_b_fwd)
                    rv_pnl[t] += gross

            # Entry condition: |z_t| > 1.8
            elif len(open_positions) < 3 and abs(z_t) > 1.8:
                direction = -1.0 if z_t > 0 else +1.0
                w_a = 0.05 * (beta_b / (beta_a + beta_b + 1e-6))
                w_b = 0.05 * (beta_a / (beta_a + beta_b + 1e-6))
                entry_friction = (w_a + w_b) * 0.00045
                rv_pnl[t] -= entry_friction
                open_positions[pair_id] = {
                    'entry_t': t,
                    'direction': direction,
                    'w_a': w_a,
                    'w_b': w_b,
                    'entry_spread': current_spread
                }

    # Summary Metrics
    active_rv_pnl = rv_pnl[w_beta + 10 :]
    cum_equity = np.cumprod(1 + active_rv_pnl) * 1000.0
    net_dollar_gain = cum_equity[-1] - 1000.0
    win_rate = (wins_count / max(1, trades_count)) * 100.0

    years = len(active_rv_pnl) / (365.25 * 6)
    cagr = ((cum_equity[-1] / 1000.0) ** (1.0 / years) - 1.0) * 100.0
    sharpe = np.mean(active_rv_pnl) / (np.std(active_rv_pnl) + 1e-12) * np.sqrt(365.25 * 6)

    hwm = np.maximum.accumulate(cum_equity)
    max_dd = np.max((hwm - cum_equity) / hwm * 100.0)

    print("\n" + "=" * 80)
    print("                    EXP-107 CHOP RV BACKTEST RESULTS")
    print("=" * 80)
    print(f"Total EXP-103 Cash Floor Bars Evaluated: {fl0_bars_count} bars (~{fl0_bars_count/6:.1f} days)")
    print(f"Total Completed Dislocated RV Trades:    {trades_count} trades")
    print(f"Winning Trades / Losing Trades:          {wins_count} / {losses_count}")
    print(f"Win Rate:                                {win_rate:.1f}%")
    print(f"Net Standalone Dollar Gain ($1k base):   ${net_dollar_gain:>+.2f} USDC")
    print(f"Standalone Net CAGR:                     {cagr:>+.2f}%")
    print(f"Standalone Annualized Sharpe Ratio:      {sharpe:.2f}")
    print(f"Maximum Pair Drawdown:                   {max_dd:.2f}%")
    print("=" * 80)

    results = {
        "experiment": "EXP-107",
        "timestamp_utc": pd.Timestamp.utcnow().isoformat(),
        "fl0_bars_active": fl0_bars_count,
        "total_trades": trades_count,
        "win_rate_pct": round(win_rate, 2),
        "net_dollar_gain": round(float(net_dollar_gain), 2),
        "net_cagr_pct": round(float(cagr), 2),
        "sharpe_ratio": round(float(sharpe), 2),
        "max_drawdown_pct": round(float(max_dd), 2)
    }

    out_file = DATA_DIR / "exp107_backtest_results.json"
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Artifact saved to {out_file}")

if __name__ == "__main__":
    run_backtest()
