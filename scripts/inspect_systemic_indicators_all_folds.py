#!/usr/bin/env python3
"""
Comprehensive Inspection of Systemic Market-State Candidate Indicators Across Folds
===================================================================================
Compares:
1. Systemic Turnover Velocity (Aggregate and Normalized per Active Asset)
2. BTC Realized Volatility (30-day annualized rolling volatility)
3. Trend Efficiency / Directional Persistence
Across:
- Fold 1 (Bars 750-1110)
- Fold 2 (Bars 1110-1470)
- Fold 3 (Bars 1470-1830)  <-- THE FAILURE WINDOW
- Fold 4 (Bars 1830-2190)
"""

import numpy as np
import pandas as pd
from pathlib import Path
from backtest_10x_convex_compounding import InstitutionalCompoundingEngine

PIPELINE_ROOT = Path(__file__).resolve().parent.parent

def main():
    engine = InstitutionalCompoundingEngine(fixed_leverage=3.0)
    eval_ts, symbols, data = engine.load_and_preprocess_data()

    close = data['close']
    vol = data['volume']
    high = data['high']
    low = data['low']
    valid = data['valid_price_mask']
    eval_start = data['eval_start_idx']

    T_full, N = close.shape
    dollar_vol = np.where(valid, close * vol, 0.0)
    agg_vol = np.sum(dollar_vol, axis=1)

    # Dwell decay for OI
    decay = np.exp(-np.log(2.0) / 48.0)
    oi_mat = np.zeros((T_full, N))
    for col in range(N):
        valid_idx = np.where(valid[:, col])[0]
        if len(valid_idx) > 0:
            first_idx = valid_idx[0]
            oi_mat[first_idx, col] = dollar_vol[first_idx, col] * 5.0
            for t in range(first_idx + 1, T_full):
                if valid[t, col]:
                    oi_mat[t, col] = oi_mat[t-1, col] * decay + 0.20 * dollar_vol[t, col]
                else:
                    oi_mat[t, col] = 0.0

    agg_oi = np.sum(oi_mat, axis=1)

    # Active universe count
    n_active = np.sum(valid, axis=1)

    # Per-active-asset normalized volume and OI (PIT clean)
    norm_vol = agg_vol / np.maximum(n_active, 1)
    norm_oi = agg_oi / np.maximum(n_active, 1)

    # Slices for 2190 eval bars
    sl = slice(eval_start, eval_start + 2190)
    eval_agg_vol = agg_vol[sl]
    eval_agg_oi = agg_oi[sl]
    eval_norm_vol = norm_vol[sl]
    eval_norm_oi = norm_oi[sl]
    eval_close = close[sl]
    
    btc_idx = symbols.index("BTC")
    btc_c = eval_close[:, btc_idx]
    btc_ret = np.diff(btc_c) / btc_c[:-1]
    btc_ret = np.insert(btc_ret, 0, 0.0)

    # 1. Aggregate Turnover Velocity (20d = 120 bars)
    tv_agg_20d = (
        pd.Series(eval_agg_vol).ewm(span=120, adjust=False).mean() /
        (pd.Series(eval_agg_oi).ewm(span=120, adjust=False).mean() + 1e-8)
    ).to_numpy()

    # 2. Normalized Turnover Velocity (20d = 120 bars)
    tv_norm_20d = (
        pd.Series(eval_norm_vol).ewm(span=120, adjust=False).mean() /
        (pd.Series(eval_norm_oi).ewm(span=120, adjust=False).mean() + 1e-8)
    ).to_numpy()

    # 3. 10d Turnover Velocity (60 bars)
    tv_norm_10d = (
        pd.Series(eval_norm_vol).ewm(span=60, adjust=False).mean() /
        (pd.Series(eval_norm_oi).ewm(span=60, adjust=False).mean() + 1e-8)
    ).to_numpy()

    # 4. BTC 30-Day Annualized Realized Volatility (180 bars @ 4H)
    btc_vol_30d = (
        pd.Series(btc_ret).rolling(180, min_periods=30).std() * np.sqrt(2190) * 100.0
    ).to_numpy()

    # 5. Trend Efficiency / Directional Ratio (Net displacement / Total path over 20d)
    net_disp_20d = np.abs(pd.Series(btc_c).diff(120)).to_numpy()
    tot_path_20d = pd.Series(np.abs(np.diff(btc_c, prepend=btc_c[0]))).rolling(120, min_periods=30).sum().to_numpy()
    efficiency_20d = net_disp_20d / (tot_path_20d + 1e-8)

    folds = [
        ("Fold 1 (Bars 750-1110)", 750, 1110),
        ("Fold 2 (Bars 1110-1470)", 1110, 1470),
        ("Fold 3 (Bars 1470-1830) [CHOP]", 1470, 1830),
        ("Fold 4 (Bars 1830-2190)", 1830, 2190),
    ]

    print("=" * 105)
    print(f"{'WINDOW':<30} {'TV_AGG_20D':<14} {'TV_NORM_20D':<14} {'TV_NORM_10D':<14} {'BTC_VOL_30D':<14} {'TREND_EFF_20D':<14}")
    print("=" * 105)

    for name, s, e in folds:
        m_tv_agg = np.nanmean(tv_agg_20d[s:e])
        m_tv_norm = np.nanmean(tv_norm_20d[s:e])
        m_tv_10d = np.nanmean(tv_norm_10d[s:e])
        m_btc_vol = np.nanmean(btc_vol_30d[s:e])
        m_eff = np.nanmean(efficiency_20d[s:e])
        print(f"{name:<30} {m_tv_agg:>12.4f}  {m_tv_norm:>12.4f}  {m_tv_10d:>12.4f}  {m_btc_vol:>11.1f}%  {m_eff:>12.4f}")

if __name__ == "__main__":
    main()
