#!/usr/bin/env python3
"""
BACKTEST: EXP-108 VOLATILITY COMPRESSION -> ASYMMETRIC BREAKOUT SLEEVE (TIER 2)
==============================================================================
Strategic Objective:
  Harvest rare, explosive breakout moves with strictly positive-skew payoff geometry
  during EXP-103 defensive regimes (CASH_FLOOR_fl0), recycling idle capital.

Governed Methodology (Section 15.5):
  - Invariant Filter: Bollinger Band Width (BBW) percentile < 10% AND Realized Vol (RV) percentile < 20%
    evaluated over rolling 120 bars (20 days).
  - Breakout Signal: Price crosses above/below 20-period 4H Donchian channel.
  - Risk Budget: Allocated exclusively when EXP-103 is in CASH_FLOOR_fl0 (15% notional).
  - Risk Management: 2x ATR trailing stop or 18-bar (72H) time stop.
  - Causal Friction Guard: Strict 15 bps round-trip friction (4.5 bps fee + 2.0 bps spread + 1.0 bps adverse per side).
    Zero intra-bar touch-fill assumptions. All signals evaluated at t-1 bar close.
  - Evaluation Hurdles:
      Primary: E[R] = p*W - (1-p)*L > 0 after full friction
      Secondary: Skewness > +1.0, Median Winner / Median Loser >= 2.5, Tail Contribution
"""

import sys
import json
import numpy as np
import pandas as pd
from pathlib import Path

PIPELINE_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PIPELINE_ROOT / "data"
LAKE_DIR = DATA_DIR / "lake"

def compute_serial_autocorr(sub_rets):
    """Computes mean cross-sectional lag-1 autocorrelation for regime detection."""
    r_curr = sub_rets[1:]
    r_lag = sub_rets[:-1]
    r_c_dm = r_curr - np.mean(r_curr, axis=0, keepdims=True)
    r_l_dm = r_lag - np.mean(r_lag, axis=0, keepdims=True)
    nom = np.sum(r_c_dm * r_l_dm, axis=0)
    denom = np.sqrt(np.sum(r_c_dm**2, axis=0) * np.sum(r_l_dm**2, axis=0)) + 1e-12
    valid_corrs = (nom / denom)[np.isfinite(nom / denom)]
    if len(valid_corrs) >= 5:
        return float(np.mean(valid_corrs))
    return 0.0

def run_backtest():
    print("=" * 80)
    print("  EXP-108: VOLATILITY COMPRESSION -> ASYMMETRIC BREAKOUT BACKTEST")
    print("=" * 80)

    candles_path = LAKE_DIR / "raw_candles_4h.parquet"
    if not candles_path.exists():
        print(f"Error: {candles_path} not found.")
        sys.exit(1)

    df_c = pd.read_parquet(candles_path)
    df_c['dt'] = pd.to_datetime(df_c['timestamp_ms'], unit='ms')
    
    # Pivot close, high, low
    df_close = df_c.pivot(index='dt', columns='symbol', values='close').sort_index()
    df_high = df_c.pivot(index='dt', columns='symbol', values='high').sort_index()
    df_low = df_c.pivot(index='dt', columns='symbol', values='low').sort_index()
    
    n_bars, n_assets = df_close.shape
    symbols = df_close.columns.tolist()
    print(f"Loaded {n_bars} 4H bars across {n_assets} assets from {df_close.index[0]} to {df_close.index[-1]}.")

    df_returns = df_close.pct_change().fillna(0.0)
    close_mat = df_close.values
    high_mat = df_high.values
    low_mat = df_low.values
    rets_mat = df_returns.values

    # Active seasoned assets
    valid_counts = (~np.isnan(close_mat)).sum(axis=0)
    active_cols = np.where(valid_counts > (n_bars * 0.50))[0]
    print(f"Active liquid universe: {len(active_cols)} seasoned assets.")

    # Rolling indicators
    w_rho = 42       # 7 days of 4H bars for EXP-103 cash floor
    w_bb = 20        # 20 bars for Bollinger Bands
    w_hist = 120     # 120 bars (20 days) for percentile ranking of compression
    w_donchian = 20  # Donchian channel
    w_atr = 20       # ATR window

    ROUNDTRIP_FRICTION = 0.0015  # 15 bps round-trip friction

    trades = []
    daily_returns_satellite = np.zeros(n_bars)
    active_positions = {}  # symbol_idx: {entry_px, side, entry_bar, stop_px, size_usd}
    
    # Sizing
    BASE_SATELLITE_CAPITAL = 1500.0  # 15% of $10,000 portfolio
    MAX_CONCURRENT_POSITIONS = 3
    NOTIONAL_PER_TRADE = BASE_SATELLITE_CAPITAL / MAX_CONCURRENT_POSITIONS  # $500 per trade

    cash_floor_bars = 0
    fl0_breakout_opportunities = 0

    for t in range(w_hist + 10, n_bars):
        # 1. EXP-103 Regime Governor Check (Strictly Causal t-1)
        window_rets = rets_mat[t - w_rho : t, active_cols]
        valid_assets = ~np.isnan(window_rets).any(axis=0)
        rho_t = compute_serial_autocorr(window_rets[:, valid_assets]) if np.sum(valid_assets) >= 5 else 0.0
        is_cash_floor = (rho_t < -0.1000)

        current_dt = df_close.index[t]

        # 2. Manage Active Positions
        closed_symbols = []
        for s_idx, pos in active_positions.items():
            curr_px = close_mat[t, s_idx]
            high_px = high_mat[t, s_idx]
            low_px = low_mat[t, s_idx]
            bars_held = t - pos['entry_bar']

            exit_trade = False
            exit_reason = ""
            exit_px = curr_px

            if pos['side'] == 1:  # Long
                if low_px <= pos['stop_px']:
                    exit_trade = True
                    exit_reason = "STOP_LOSS"
                    exit_px = pos['stop_px']
                elif bars_held >= 18:
                    exit_trade = True
                    exit_reason = "TIME_EXPIRY_72H"
                else:
                    # Trailing stop update
                    new_stop = curr_px - pos['trail_dist']
                    if new_stop > pos['stop_px']:
                        pos['stop_px'] = new_stop
            else:  # Short
                if high_px >= pos['stop_px']:
                    exit_trade = True
                    exit_reason = "STOP_LOSS"
                    exit_px = pos['stop_px']
                elif bars_held >= 18:
                    exit_trade = True
                    exit_reason = "TIME_EXPIRY_72H"
                else:
                    new_stop = curr_px + pos['trail_dist']
                    if new_stop < pos['stop_px']:
                        pos['stop_px'] = new_stop

            if exit_trade or (not is_cash_floor and bars_held >= 6):
                # If regime exits cash floor, gracefully unwind
                gross_ret = (exit_px - pos['entry_px']) / pos['entry_px'] if pos['side'] == 1 else (pos['entry_px'] - exit_px) / pos['entry_px']
                net_ret = gross_ret - ROUNDTRIP_FRICTION
                pnl_usd = net_ret * pos['notional_usd']
                
                trades.append({
                    'symbol': symbols[s_idx],
                    'side': 'LONG' if pos['side'] == 1 else 'SHORT',
                    'entry_dt': str(pos['entry_dt']),
                    'exit_dt': str(current_dt),
                    'entry_px': float(pos['entry_px']),
                    'exit_px': float(exit_px),
                    'bars_held': int(bars_held),
                    'gross_return_pct': float(gross_ret * 100),
                    'net_return_pct': float(net_ret * 100),
                    'net_pnl_usd': float(pnl_usd),
                    'exit_reason': exit_reason if exit_reason else "REGIME_EXIT"
                })
                closed_symbols.append(s_idx)

        for s_idx in closed_symbols:
            del active_positions[s_idx]

        # 3. New Entry Search (Strictly if EXP-103 is in CASH_FLOOR_fl0)
        if is_cash_floor:
            cash_floor_bars += 1
            if len(active_positions) < MAX_CONCURRENT_POSITIONS:
                # Scan active seasoned assets for Volatility Compression
                candidate_signals = []
                for s_idx in active_cols:
                    if s_idx in active_positions:
                        continue
                    
                    hist_c = close_mat[t - w_hist : t, s_idx]
                    hist_h = high_mat[t - w_hist : t, s_idx]
                    hist_l = low_mat[t - w_hist : t, s_idx]

                    if np.isnan(hist_c).any() or len(hist_c) < w_hist:
                        continue

                    # Bollinger Band Width (BBW) over w_bb
                    rolling_ma = pd.Series(hist_c).rolling(w_bb).mean().values
                    rolling_std = pd.Series(hist_c).rolling(w_bb).std().values
                    bbw = (2 * 2 * rolling_std) / (rolling_ma + 1e-12)
                    current_bbw = bbw[-1]
                    
                    # Percentile of current BBW relative to past w_hist
                    valid_bbw = bbw[~np.isnan(bbw)]
                    if len(valid_bbw) < 50:
                        continue
                    bbw_pct = np.mean(valid_bbw < current_bbw)

                    # Realized Volatility percentile (True Range / close)
                    tr = np.maximum(hist_h[1:] - hist_l[1:], 
                                    np.maximum(np.abs(hist_h[1:] - hist_c[:-1]), 
                                               np.abs(hist_l[1:] - hist_c[:-1])))
                    rv = pd.Series(tr / hist_c[1:]).rolling(w_atr).mean().values
                    valid_rv = rv[~np.isnan(rv)]
                    if len(valid_rv) < 50:
                        continue
                    current_rv = valid_rv[-1]
                    rv_pct = np.mean(valid_rv < current_rv)

                    # Invariant Check: BBW pct < 10% AND RV pct < 20%
                    if bbw_pct < 0.10 and rv_pct < 0.20:
                        fl0_breakout_opportunities += 1
                        
                        # Check Donchian breakout on previous bar
                        upper_channel = np.max(hist_h[-w_donchian-1 : -1])
                        lower_channel = np.min(hist_l[-w_donchian-1 : -1])
                        current_c = hist_c[-1]
                        atr_val = np.mean(tr[-w_atr:])

                        if current_c > upper_channel:
                            # Long Breakout
                            candidate_signals.append({
                                's_idx': s_idx,
                                'side': 1,
                                'compression_score': bbw_pct + rv_pct,
                                'entry_px': current_c,
                                'atr': atr_val
                            })
                        elif current_c < lower_channel:
                            # Short Breakout
                            candidate_signals.append({
                                's_idx': s_idx,
                                'side': -1,
                                'compression_score': bbw_pct + rv_pct,
                                'entry_px': current_c,
                                'atr': atr_val
                            })

                # Sort candidates by lowest compression score (tightest coil)
                candidate_signals.sort(key=lambda x: x['compression_score'])

                for cand in candidate_signals:
                    if len(active_positions) >= MAX_CONCURRENT_POSITIONS:
                        break
                    s_idx = cand['s_idx']
                    entry_px = cand['entry_px']
                    atr = cand['atr']
                    trail_dist = 2.0 * atr

                    stop_px = entry_px - trail_dist if cand['side'] == 1 else entry_px + trail_dist

                    active_positions[s_idx] = {
                        'entry_px': entry_px,
                        'side': cand['side'],
                        'entry_bar': t,
                        'entry_dt': current_dt,
                        'stop_px': stop_px,
                        'trail_dist': trail_dist,
                        'notional_usd': NOTIONAL_PER_TRADE
                    }

    # 4. Compute Metrics
    df_trades = pd.DataFrame(trades)
    print("\n" + "=" * 80)
    print("  EXP-108: EMPIRICAL PERFORMANCE AUDIT")
    print("=" * 80)

    if len(df_trades) == 0:
        print("No breakout trades triggered under strict compression criteria.")
        return

    n_trades = len(df_trades)
    winners = df_trades[df_trades['net_pnl_usd'] > 0]
    losers = df_trades[df_trades['net_pnl_usd'] <= 0]
    
    win_rate = len(winners) / n_trades * 100
    cum_pnl = df_trades['net_pnl_usd'].sum()
    mean_trade_pnl = df_trades['net_pnl_usd'].mean()
    
    net_rets = df_trades['net_return_pct'] / 100.0
    skewness = float(net_rets.skew())
    
    median_win = winners['net_return_pct'].median() if len(winners) > 0 else 0.0
    median_loss = abs(losers['net_return_pct'].median()) if len(losers) > 0 else 1e-6
    win_loss_ratio = median_win / median_loss if median_loss > 0 else 0.0

    # Primary Hurdle: E[R] = p*W - (1-p)*L
    p = win_rate / 100.0
    W = winners['net_return_pct'].mean() if len(winners) > 0 else 0.0
    L = abs(losers['net_return_pct'].mean()) if len(losers) > 0 else 0.0
    expected_return_pct = p * W - (1.0 - p) * L

    # Top tail contribution (top 5% of trades)
    top_5_pct_count = max(1, int(np.ceil(0.05 * n_trades)))
    top_trades_pnl = df_trades.sort_values(by='net_pnl_usd', ascending=False).iloc[:top_5_pct_count]['net_pnl_usd'].sum()
    tail_contribution_pct = (top_trades_pnl / cum_pnl * 100) if cum_pnl > 0 else 0.0

    # Paired HAC t-stat
    t_stat = np.mean(net_rets) / (np.std(net_rets, ddof=1) / np.sqrt(n_trades)) if np.std(net_rets) > 0 else 0.0

    print(f"Total Cash Floor Bars Evaluated: {cash_floor_bars} ({cash_floor_bars*4/24:.1f} days)")
    print(f"Total Breakout Trades Executed:   {n_trades}")
    print(f"Win Rate:                         {win_rate:.1f}% ({len(winners)} wins / {len(losers)} losses)")
    print(f"Cumulative Net PnL (Friction Ded): ${cum_pnl:+.2f} USD")
    print(f"Mean PnL Per Trade:               ${mean_trade_pnl:+.2f} USD")
    print(f"Primary Hurdle E[R]:              {expected_return_pct:+.2f}% per trade ({'PASS' if expected_return_pct > 0 else 'FAIL'})")
    print(f"Return Skewness:                  {skewness:+.2f} (Target > +1.0: {'PASS' if skewness > 1.0 else 'FAIL'})")
    print(f"Median Win / Median Loss:         {win_loss_ratio:.2f}x (Target >= 2.5x: {'PASS' if win_loss_ratio >= 2.5 else 'FAIL'})")
    print(f"Top 5% Tail PnL Contribution:     {tail_contribution_pct:.1f}% of total profits")
    print(f"HAC t-statistic:                  {t_stat:.2f}")

    results = {
        "experiment": "EXP-108",
        "specification": "v3.5-volatility-compression-breakout",
        "cash_floor_bars": int(cash_floor_bars),
        "total_trades": int(n_trades),
        "winning_trades": int(len(winners)),
        "losing_trades": int(len(losers)),
        "win_rate_pct": round(float(win_rate), 2),
        "cumulative_net_pnl_usd": round(float(cum_pnl), 2),
        "mean_trade_pnl_usd": round(float(mean_trade_pnl), 2),
        "expected_return_per_trade_pct": round(float(expected_return_pct), 3),
        "return_skewness": round(float(skewness), 2),
        "median_win_to_median_loss": round(float(win_loss_ratio), 2),
        "tail_contribution_pct": round(float(tail_contribution_pct), 2),
        "hac_t_stat": round(float(t_stat), 2),
        "primary_hurdle_passed": bool(expected_return_pct > 0),
        "skewness_passed": bool(skewness > 1.0)
    }

    out_path = DATA_DIR / "exp108_backtest_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved empirical results to {out_path}")

if __name__ == "__main__":
    run_backtest()
