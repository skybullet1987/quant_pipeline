import gc
import numpy as np
import pandas as pd
from google.cloud import bigquery
from kalman_filter_features import CausalKalmanFilter

PROJECT_ID = "parnasa-498503"
DATASET_ID = "market_data"

def downcast_df(df):
    """Reduces memory footprint by downcasting numeric dtypes."""
    for col in df.select_dtypes(include=['float64']).columns:
        df[col] = df[col].astype('float32')
    for col in df.select_dtypes(include=['int64']).columns:
        c_min, c_max = df[col].min(), df[col].max()
        if c_min >= -128 and c_max <= 127:
            df[col] = df[col].astype('int8')
        elif c_min >= -32768 and c_max <= 32767:
            df[col] = df[col].astype('int16')
        else:
            df[col] = df[col].astype('int32')
    return df

def fetch_base_dataset(client, limit_tickers=None):
    """Pulls staged market data, synthetic liquidations, and systemic stress metrics."""
    ticker_filter = ""
    if limit_tickers:
        formatted_tickers = ", ".join([f"'{t}'" for t in limit_tickers])
        ticker_filter = f"WHERE ticker IN ({formatted_tickers})"

    query = f"""
        WITH ohlcv AS (
            SELECT timestamp, ticker, open, high, low, close, volume
            FROM `{PROJECT_ID}.{DATASET_ID}.stg_ohlcv`
            {ticker_filter}
        ),
        oi AS (
            SELECT timestamp, ticker, sum_open_interest_value, sum_taker_long_short_vol_ratio
            FROM `{PROJECT_ID}.{DATASET_ID}.stg_open_interest`
        ),
        liq AS (
            SELECT timestamp, ticker, oi_change_value, is_synthetic_liquidation, cascade_type
            FROM `{PROJECT_ID}.{DATASET_ID}.fct_synthetic_liquidations`
        ),
        stress AS (
            SELECT timestamp, total_market_oi, oi_acceleration, avg_funding_rate, funding_dispersion
            FROM `{PROJECT_ID}.{DATASET_ID}.fct_systemic_stress`
        )
        SELECT 
            o.timestamp,
            o.ticker,
            o.open,
            o.high,
            o.low,
            o.close,
            o.volume,
            i.sum_open_interest_value AS open_interest,
            i.sum_taker_long_short_vol_ratio AS taker_ls_ratio,
            l.oi_change_value,
            COALESCE(l.is_synthetic_liquidation, 0) AS is_synthetic_liquidation,
            COALESCE(l.cascade_type, 'NONE') AS cascade_type,
            s.total_market_oi,
            s.oi_acceleration,
            s.avg_funding_rate,
            s.funding_dispersion
        FROM ohlcv o
        LEFT JOIN oi i ON o.timestamp = i.timestamp AND o.ticker = i.ticker
        LEFT JOIN liq l ON o.timestamp = l.timestamp AND o.ticker = l.ticker
        LEFT JOIN stress s ON TIMESTAMP_TRUNC(o.timestamp, HOUR) = s.timestamp
        ORDER BY o.ticker ASC, o.timestamp ASC
    """
    df = client.query(query).to_dataframe()
    return downcast_df(df)

def add_kalman_features(df, q=1e-5, r=1e-3):
    """Computes online Causal Kalman filter close prices and residuals per ticker."""
    processed_dfs = []
    for ticker, group in df.groupby('ticker', sort=False):
        group = group.sort_values('timestamp').copy()
        kf = CausalKalmanFilter(process_noise_q=q, measurement_noise_r=r)
        
        kalman_closes = [kf.update(price) for price in group['close'].values]
            
        group['kalman_close'] = np.array(kalman_closes, dtype=np.float32)
        group['kalman_residual'] = group['close'] - group['kalman_close']
        processed_dfs.append(group)
        
    del df
    gc.collect()
    return pd.concat(processed_dfs, ignore_index=True)

def add_derivatives_features(df):
    """Tracks continuous open interest, staleness age, and funding interactions."""
    df = df.sort_values(['ticker', 'timestamp']).copy()
    
    df['open_interest_ffilled'] = df.groupby('ticker')['open_interest'].ffill()
    df['is_oi_null'] = df['open_interest'].isna().astype('int8')
    
    df['minutes_since_oi_update'] = df.groupby('ticker')['is_oi_null'].transform(
        lambda x: x.groupby((x != x.shift()).cumsum()).cumcount()
    ).astype('int16')
    
    df['oi_x_funding'] = df['open_interest_ffilled'] * df['avg_funding_rate']
    return downcast_df(df)

def add_volatility_features(df):
    """Computes true log returns and sum-of-squares realized volatility."""
    df = df.sort_values(['ticker', 'timestamp']).copy()
    
    df['log_ret'] = df.groupby('ticker')['close'].transform(lambda x: np.log(x).diff())
    
    df['realized_vol_30m'] = df.groupby('ticker')['log_ret'].transform(
        lambda x: np.sqrt((x**2).rolling(30, min_periods=5).sum())
    )
    
    df['oi_x_vol'] = df['open_interest_ffilled'] * df['realized_vol_30m']
    return downcast_df(df)

def compute_tbm_vectorized(closes, vols, pt_mult=2.0, sl_mult=1.0, max_holding=30):
    """Fast vectorized NumPy implementation of path-dependent Triple-Barrier Labels."""
    n = len(closes)
    labels = np.zeros(n, dtype=np.int8)
    
    if n <= max_holding:
        return labels
        
    future_closes = np.lib.stride_tricks.sliding_window_view(closes[1:], window_shape=max_holding)[:n - max_holding]
    entries = closes[:n - max_holding, None]
    v = vols[:n - max_holding, None]
    
    valid_mask = ~np.isnan(v.squeeze()) & (v.squeeze() > 0)
    
    pt_thresh = entries * (1 + pt_mult * v)
    sl_thresh = entries * (1 - sl_mult * v)
    
    pt_hits = future_closes >= pt_thresh
    sl_hits = future_closes <= sl_thresh
    
    pt_idx = np.where(pt_hits, np.arange(max_holding), max_holding + 1)
    sl_idx = np.where(sl_hits, np.arange(max_holding), max_holding + 1)
    
    min_pt_idx = np.min(pt_idx, axis=1)
    min_sl_idx = np.min(sl_idx, axis=1)
    
    hit_labels = np.zeros(n - max_holding, dtype=np.int8)
    
    pt_first = (min_pt_idx < min_sl_idx) & (min_pt_idx < max_holding + 1)
    sl_first = (min_sl_idx < min_pt_idx) & (min_sl_idx < max_holding + 1)
    
    hit_labels[pt_first] = 1
    hit_labels[sl_first] = -1
    hit_labels[~valid_mask] = 0
    
    labels[:n - max_holding] = hit_labels
    return labels

def add_triple_barrier_targets(df, pt_multiplier=2.0, sl_multiplier=1.0, max_holding=30):
    """Computes path-dependent Triple-Barrier Labels across all tickers."""
    processed_dfs = []
    
    for ticker, group in df.groupby('ticker', sort=False):
        group = group.sort_values('timestamp').reset_index(drop=True)
        closes = group['close'].values
        vols = group['realized_vol_30m'].values
        
        group['target_tbm'] = compute_tbm_vectorized(closes, vols, pt_multiplier, sl_multiplier, max_holding)
        processed_dfs.append(group)
        
    del df
    gc.collect()
    return pd.concat(processed_dfs, ignore_index=True)

def add_macro_regimes_asof(df, macro_df):
    """Memory-efficient backward merge_asof for hourly macro metrics."""
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    macro_df['timestamp'] = pd.to_datetime(macro_df['timestamp'], utc=True)
    
    macro_df = macro_df.sort_values('timestamp').reset_index(drop=True)
    
    merged_dfs = []
    for ticker, group in df.groupby('ticker', sort=False):
        group_sorted = group.sort_values('timestamp').reset_index(drop=True)
        merged = pd.merge_asof(
            group_sorted,
            macro_df,
            on='timestamp',
            direction='backward'
        )
        merged_dfs.append(merged)
        
    del df, macro_df
    gc.collect()
    return pd.concat(merged_dfs, ignore_index=True)

def run_quality_controls(df):
    """Executes strict pre-parquet assertions and prints data diagnostics."""
    print("\nRunning Quality Control Assertions...")
    assert df['ticker'].notna().all(), "Found null tickers!"
    assert df['target_tbm'].notna().all(), "Found null target labels!"
    assert not df.duplicated(['ticker', 'timestamp']).any(), "Found duplicate ticker-timestamp rows!"
    print("[SUCCESS] All pre-parquet assertions passed!")

    print("\n--- Pipeline Diagnostics ---")
    print(f"Total Rows: {len(df):,}")
    print(f"Memory Usage: {df.memory_usage(deep=True).sum() / 1e6:.2f} MB")
    print("\nTarget TBM Class Balance:")
    print(df['target_tbm'].value_counts(normalize=True))
    print("\nRows per Ticker:")
    print(df['ticker'].value_counts())
    print(f"\nMean OI Staleness (Minutes): {df['minutes_since_oi_update'].mean():.2f}")

def main():
    client = bigquery.Client(project=PROJECT_ID)
    
    print("Step 1/6: Fetching Base Dataset (BTCUSD & ETHUSD Sample)...")
    df_base = fetch_base_dataset(client, limit_tickers=['BTCUSD', 'ETHUSD'])
    
    print("Step 2/6: Applying Causal Kalman Filter...")
    df_kalman = add_kalman_features(df_base, q=1e-5, r=1e-3)
    
    print("Step 3/6: Engineering Derivatives & Volatility Features...")
    df_deriv = add_derivatives_features(df_kalman)
    df_vol = add_volatility_features(df_deriv)
    
    print("Step 4/6: Computing Vectorized Triple-Barrier Labels...")
    df_labeled = add_triple_barrier_targets(df_vol)
    
    print("Step 5/6: Fetching Macro Data & Applying backward merge_asof...")
    macro_query = f"""
        SELECT timestamp, total_market_oi, oi_acceleration, avg_funding_rate, funding_dispersion
        FROM `{PROJECT_ID}.{DATASET_ID}.fct_systemic_stress`
        ORDER BY timestamp ASC
    """
    macro_df = client.query(macro_query).to_dataframe()
    macro_df = downcast_df(macro_df)
    
    df_merged = add_macro_regimes_asof(df_labeled, macro_df)
    
    # Drop warm-up NaN rows
    df_final = df_merged.dropna(subset=['target_tbm', 'realized_vol_30m']).reset_index(drop=True)
    df_final = downcast_df(df_final)
    
    print("Step 6/6: Running Quality Controls & Exporting...")
    run_quality_controls(df_final)
    
    output_file = "feature_matrix_production.parquet"
    df_final.to_parquet(output_file, index=False)
    print(f"\n[SUCCESS] Production Feature Matrix saved to {output_file}!")

if __name__ == "__main__":
    main()
