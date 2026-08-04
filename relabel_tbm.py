import pandas as pd
import numpy as np
from numba import njit
import time

INPUT_FILE = "feature_matrix_production.parquet"
OUTPUT_FILE = "feature_matrix_symmetric.parquet"

PT_MULT = 1.5
SL_MULT = 1.5
HORIZON = 30

@njit
def compute_symmetric_tbm(prices, vols, horizon, pt_mult, sl_mult):
    n = len(prices)
    targets = np.zeros(n, dtype=np.int8)
    realized_returns = np.zeros(n, dtype=np.float32)
    
    for i in range(n):
        if i + horizon >= n:
            targets[i] = 0
            realized_returns[i] = 0.0
            continue
            
        p0 = prices[i]
        vol = vols[i]
        
        if vol <= 1e-8 or np.isnan(vol) or np.isnan(p0):
            targets[i] = 0
            realized_returns[i] = 0.0
            continue
            
        upper_barrier = p0 * (1.0 + (pt_mult * vol))
        lower_barrier = p0 * (1.0 - (sl_mult * vol))
        
        hit = 0
        ret = 0.0
        
        for j in range(1, horizon + 1):
            p_cur = prices[i + j]
            if p_cur >= upper_barrier:
                hit = 1
                ret = (p_cur - p0) / p0
                break
            elif p_cur <= lower_barrier:
                hit = -1
                ret = (p_cur - p0) / p0
                break
                
        if hit == 0:
            ret = (prices[i + horizon] - p0) / p0
            
        targets[i] = hit
        realized_returns[i] = ret
        
    return targets, realized_returns

def main():
    print(f"Loading {INPUT_FILE}...")
    df = pd.read_parquet(INPUT_FILE)
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    print("Reconstructing price paths and generating symmetric labels...")
    df['log_ret_1m'] = df.get('log_ret_1m', df.get('log_ret', pd.Series(np.zeros(len(df))))).fillna(0)
    prices = np.exp(df['log_ret_1m'].cumsum()).values
    vols = df['realized_vol_30m'].fillna(0).values
    
    start_time = time.time()
    targets, returns = compute_symmetric_tbm(prices, vols, HORIZON, PT_MULT, SL_MULT)
    print(f"Relabeling completed in {time.time() - start_time:.2f} seconds.")
    
    df['target_tbm'] = targets
    df['tbm_realized_return'] = returns
    
    print("\n[VERIFICATION] New Symmetric Base Rates:")
    print(df['target_tbm'].value_counts(normalize=True) * 100)
    
    print(f"\nSaving to {OUTPUT_FILE}...")
    df.to_parquet(OUTPUT_FILE, index=False)
    print("Done!")

if __name__ == "__main__":
    main()
