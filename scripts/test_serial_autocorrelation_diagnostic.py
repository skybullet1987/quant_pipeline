#!/usr/bin/env python3
"""
Test Return Serial Autocorrelation Across Folds
==============================================
Empirically tests the hypothesis:
Does cross-sectional return serial autocorrelation rho_1(t) cleanly distinguish
the high-volume liquidation grinder of Fold 3 from the directional trending regimes of Folds 1, 2, and 4?
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
    valid = data['valid_price_mask']
    eval_start = data['eval_start_idx']

    # Returns matrix
    returns_mat = np.zeros_like(close)
    prev_close = np.roll(close, 1, axis=0)
    valid_pair = valid & np.roll(valid, 1, axis=0)
    valid_pair[0] = False
    with np.errstate(invalid="ignore", divide="ignore"):
        returns_mat[1:] = np.where(valid_pair[1:], (close[1:] / (prev_close[1:] + 1e-12)) - 1.0, 0.0)

    # Slice evaluation window with 60 bars warmup
    total_eval_bars = 2190
    warmup = 120
    s_idx = max(0, eval_start - warmup)
    e_idx = eval_start + total_eval_bars
    
    rets_eval = returns_mat[s_idx:e_idx] # (T_slice, N)
    valid_eval = valid[s_idx:e_idx]
    
    # Compute rolling lag-1 autocorrelation for each asset across different window lengths:
    # 7 days (42 bars), 10 days (60 bars), 14 days (84 bars), 20 days (120 bars)
    for window_bars in [30, 42, 60, 84]:
        w_days = window_bars / 6.0
        T_slice, N = rets_eval.shape
        rho_series = np.zeros(T_slice)
        
        for t in range(window_bars, T_slice):
            sub_rets = rets_eval[t - window_bars : t] # (W, N)
            sub_valid = valid_eval[t - window_bars : t] # (W, N)
            
            # Asset is valid if it has valid data throughout the window
            asset_mask = np.all(sub_valid, axis=0)
            if np.sum(asset_mask) < 10:
                continue
                
            r_curr = sub_rets[1:, asset_mask] # (W-1, K)
            r_lag = sub_rets[:-1, asset_mask]  # (W-1, K)
            
            # Compute pearson correlation per asset
            r_curr_demean = r_curr - np.mean(r_curr, axis=0, keepdims=True)
            r_lag_demean = r_lag - np.mean(r_lag, axis=0, keepdims=True)
            
            nom = np.sum(r_curr_demean * r_lag_demean, axis=0)
            denom = np.sqrt(np.sum(r_curr_demean**2, axis=0) * np.sum(r_lag_demean**2, axis=0)) + 1e-12
            
            corrs = nom / denom
            # Filter out degenerate NaN or Inf
            valid_corrs = corrs[np.isfinite(corrs)]
            if len(valid_corrs) > 0:
                rho_series[t] = np.mean(valid_corrs)
                
        # Offset to eval bars
        offset = eval_start - s_idx
        eval_rho = rho_series[offset : offset + total_eval_bars]
        
        folds = [
            ("Fold 1 (Bars 750-1110) [TREND]", 750, 1110),
            ("Fold 2 (Bars 1110-1470) [TREND]", 1110, 1470),
            ("Fold 3 (Bars 1470-1830) [GRINDER]", 1470, 1830),
            ("Fold 4 (Bars 1830-2190) [RECOVERY]", 1830, 2190),
        ]
        
        print(f"\n--- WINDOW: {w_days:.1f} DAYS ({window_bars} BARS) ---")
        for name, s, e in folds:
            sub_r = eval_rho[s:e]
            print(f"  {name:<36} Mean Rho = {np.mean(sub_r):>+7.4f} | Min = {np.min(sub_r):>+7.4f} | % Negative = {np.mean(sub_r < -0.10)*100:>5.1f}%")

if __name__ == "__main__":
    main()
