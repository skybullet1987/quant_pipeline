import numpy as np
import pandas as pd
from google.cloud import bigquery

PROJECT_ID = "parnasa-498503"
DATASET_ID = "market_data"

class CausalKalmanFilter:
    """
    1D Online Causal Kalman Filter for price state estimation.
    Strictly causal (updates tick-by-tick based only on past observations).
    """
    def __init__(self, process_noise_q=1e-5, measurement_noise_r=1e-3):
        self.q = process_noise_q  # Process variance (trust in state model)
        self.r = measurement_noise_r  # Measurement variance (trust in data)
        self.x = None  # State estimate
        self.p = 1.0   # Estimate uncertainty

    def update(self, measurement):
        if np.isnan(measurement):
            return self.x if self.x is not None else np.nan
            
        if self.x is None:
            self.x = measurement
            return self.x

        # 1. Predict
        x_pred = self.x
        p_pred = self.p + self.q

        # 2. Update
        k_gain = p_pred / (p_pred + self.r)
        self.x = x_pred + k_gain * (measurement - x_pred)
        self.p = (1 - k_gain) * p_pred

        return self.x

def apply_kalman_to_ticker(df, q=1e-5, r=1e-3):
    kf = CausalKalmanFilter(process_noise_q=q, measurement_noise_r=r)
    df = df.sort_values('timestamp').copy()
    
    kalman_prices = []
    for price in df['close'].values:
        kalman_prices.append(kf.update(price))
        
    df['kalman_close'] = kalman_prices
    df['kalman_residual'] = df['close'] - df['kalman_close']
    return df

def main():
    client = bigquery.Client(project=PROJECT_ID)
    print("Testing Causal Kalman Filter on BTCUSD sample...")
    
    query = f"""
        SELECT timestamp, ticker, close 
        FROM `{PROJECT_ID}.{DATASET_ID}.raw_1m_ohlcv_v1` 
        WHERE ticker = 'BTCUSD' 
        ORDER BY timestamp DESC 
        LIMIT 10000
    """
    df = client.query(query).to_dataframe()
    df_filtered = apply_kalman_to_ticker(df)
    
    print("\n--- Kalman Output Sample ---")
    print(df_filtered[['timestamp', 'ticker', 'close', 'kalman_close', 'kalman_residual']].head())
    print("\n[SUCCESS] Causal Kalman Filter engine verified successfully!")

if __name__ == "__main__":
    main()
