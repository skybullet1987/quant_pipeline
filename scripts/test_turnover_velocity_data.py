#!/usr/bin/env python3
"""
Inspect Aggregate Market Volume and Systemic Indicators Across Folds
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

    # Dollar volume: close * vol on valid pairs
    dollar_vol = np.where(valid, close * vol, 0.0)
    agg_vol = np.sum(dollar_vol, axis=1) # shape (T,)

    eval_start = data['eval_start_idx']
    agg_vol_eval = agg_vol[eval_start : eval_start + 2190]
    close_eval = close[eval_start : eval_start + 2190]
    btc_idx = symbols.index("BTC")
    btc_close = close_eval[:, btc_idx]

    # Active universe count at each bar
    active_count = np.sum(valid[eval_start : eval_start + 2190], axis=1)

    print(f"Total eval bars: {len(agg_vol_eval)}")
    print(f"Mean aggregate 4H dollar volume: ${np.mean(agg_vol_eval):,.0f}")
    print(f"Active universe range: [{np.min(active_count)} to {np.max(active_count)}] assets")

    folds = [
        ("Fold 1 (Bars 750-1110: OOS 1)", 750, 1110),
        ("Fold 2 (Bars 1110-1470: OOS 2)", 1110, 1470),
        ("Fold 3 (Bars 1470-1830: OOS 3)", 1470, 1830),
        ("Fold 4 (Bars 1830-2190: OOS 4)", 1830, 2190),
    ]

    print("\n" + "=" * 90)
    print(f"{'WINDOW':<32} {'MEAN 4H VOL':<15} {'MEDIAN 4H VOL':<15} {'ACTIVE ASSETS':<15} {'BTC RETURN':<12}")
    print("=" * 90)

    for name, s, e in folds:
        sub_vol = agg_vol_eval[s:e]
        sub_assets = active_count[s:e]
        btc_ret = (btc_close[e-1] / btc_close[s] - 1.0) * 100.0
        print(f"{name:<32} ${np.mean(sub_vol):>12,.0f}  ${np.median(sub_vol):>12,.0f}  {np.mean(sub_assets):>12.1f}   {btc_ret:>+9.2f}%")

if __name__ == "__main__":
    main()
