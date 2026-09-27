#!/usr/bin/env python3
"""
Test Systemic Market Turnover Velocity Formulation and Calibration
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
    valid = data['valid_price_mask']
    eval_start = data['eval_start_idx']

    # Dollar volume: close * vol on valid pairs
    dollar_vol = np.where(valid, close * vol, 0.0) # (T, N)
    
    # 1. Point-in-Time Universe Mask: Active Tradeable Perpetual Contracts at bar t
    agg_vol = np.sum(dollar_vol, axis=1) # (T,)

    # 2. Open Interest Modeling:
    # Perpetual positions accumulate with volume and decay as positions close.
    # Half-life of perp positions: ~7-10 days (42-60 bars @ 4H).
    # Decay factor per 4H bar: lambda_decay = exp(-ln(2) / 48) ~= 0.9856
    decay = np.exp(-np.log(2.0) / 48.0)
    
    # Model OI per symbol or aggregate OI
    # Let's accumulate OI per symbol using Point-in-Time valid mask
    T, N = dollar_vol.shape
    oi_mat = np.zeros((T, N))
    
    # Initialize first valid OI
    for col in range(N):
        valid_idx = np.where(valid[:, col])[0]
        if len(valid_idx) > 0:
            first_idx = valid_idx[0]
            oi_mat[first_idx, col] = dollar_vol[first_idx, col] * 5.0 # ~5x 4H volume initial stock
            for t in range(first_idx + 1, T):
                if valid[t, col]:
                    # Fraction of volume that creates new open interest (~20%) vs closes existing
                    # In equilibrium: OI_ss = (0.20 * Volume) / (1 - decay) ~= 0.20 / 0.0143 ~= 14x 4H volume (~2.3x 24h volume)
                    oi_mat[t, col] = oi_mat[t-1, col] * decay + 0.20 * dollar_vol[t, col]
                else:
                    oi_mat[t, col] = 0.0
                    
    agg_oi = np.sum(oi_mat, axis=1) # (T,)

    # Slices for evaluation period (2190 bars)
    eval_agg_vol = agg_vol[eval_start : eval_start + 2190]
    eval_agg_oi = agg_oi[eval_start : eval_start + 2190]

    print("Data summary over 2,190 eval bars:")
    print(f"  Mean Agg Volume: ${np.mean(eval_agg_vol):,.0f}")
    print(f"  Mean Agg OI:     ${np.mean(eval_agg_oi):,.0f}")
    print(f"  Ratio Vol/OI:    {np.mean(eval_agg_vol / eval_agg_oi):.4f}")

    # Test smoothing windows: 10 days (60 bars) and 20 days (120 bars)
    for lookback_days in [10, 20]:
        span_bars = lookback_days * 6
        ema_vol = pd.Series(eval_agg_vol).ewm(span=span_bars, adjust=False).mean().to_numpy()
        ema_oi = pd.Series(eval_agg_oi).ewm(span=span_bars, adjust=False).mean().to_numpy()
        
        turnover_velocity = ema_vol / (ema_oi + 1e-8)
        
        # In-Sample period: Fold 1-2 (Bars 0 to 1470)
        is_tv = turnover_velocity[:1470]
        
        for tau in [0.15, 0.20, 0.25]:
            q_thresh = float(np.quantile(is_tv, tau))
            gated = turnover_velocity < q_thresh # True when throttled
            
            downtime_pct = float(np.mean(gated)) * 100.0
            
            # Folds disable distribution:
            # Fold 1: [750, 1110]
            # Fold 2: [1110, 1470]
            # Fold 3: [1470, 1830]
            # Fold 4: [1830, 2190]
            f1_dis = float(np.mean(gated[750:1110])) * 100.0
            f2_dis = float(np.mean(gated[1110:1470])) * 100.0
            f3_dis = float(np.mean(gated[1470:1830])) * 100.0
            f4_dis = float(np.mean(gated[1830:2190])) * 100.0
            
            # Transitions and run length
            transitions = int(np.sum(np.diff(gated.astype(int)) != 0))
            # Run length of throttled periods
            runs = []
            cur_run = 0
            for g in gated:
                if g:
                    cur_run += 1
                elif cur_run > 0:
                    runs.append(cur_run)
                    cur_run = 0
            if cur_run > 0:
                runs.append(cur_run)
            avg_run = float(np.mean(runs)) if runs else 0.0

            print(f"Lookback {lookback_days:2d}d | Tau {tau:.2f} (Q={q_thresh:.4f}) | Duty Downtime: {downtime_pct:5.1f}% | Trans: {transitions:3d} | Avg Run: {avg_run:4.1f}b | F1: {f1_dis:4.1f}% | F2: {f2_dis:4.1f}% | F3: {f3_dis:4.1f}% | F4: {f4_dis:4.1f}%")

if __name__ == "__main__":
    main()
