import pandas as pd
import numpy as np
from catboost import CatBoostRanker, Pool
from google.cloud import bigquery
import warnings

# Suppress pandas fragmentation warnings from extensive rolling metrics
warnings.filterwarnings('ignore')

def fetch_data():
    print("1. Fetching Wide Universe Matrix from BigQuery...")
    client = bigquery.Client()
    
    # Pulling 50+ coins from your historical data warehouse
    query = """
        SELECT timestamp, symbol, open, high, low, close, volume 
        FROM `your_gcp_project.your_dataset.kraken_ohlcv`
        ORDER BY symbol, timestamp
    """
    
    # create_bqstorage_client=True leverages the gRPC protocol for massive speed
    df = client.query(query).to_dataframe(create_bqstorage_client=True)
    print(f"Successfully loaded {len(df)} rows.")
    return df

def engineer_advanced_features(df, window=60):
    print(f"2. Engineering Full Advanced Feature Matrix (Window: {window} periods)...")
    df = df.sort_values(['symbol', 'timestamp']).copy()
    
    # --- TARGET VARIABLE ---
    df['target_forward_ret'] = df.groupby('symbol')['close'].shift(-1) / df['close'] - 1
    
    # Log transforms for range volatility math
    log_o = np.log(df['open'])
    log_h = np.log(df['high'])
    log_l = np.log(df['low'])
    log_c = np.log(df['close'])
    
    # --- 1. ADVANCED VOLATILITY REGIMES ---
    # Yang-Zhang Volatility (Captures overnight gap risk and intraday drift)
    df['log_oc_prev'] = log_o - df.groupby('symbol')['close'].shift(1).apply(np.log)
    df['log_co'] = log_c - log_o
    df['rs'] = (log_h - log_o) * (log_h - log_c) + (log_l - log_o) * (log_l - log_c)
    
    var_o = df.groupby('symbol')['log_oc_prev'].transform(lambda x: x.rolling(window).var())
    var_c = df.groupby('symbol')['log_co'].transform(lambda x: x.rolling(window).var())
    var_rs = df.groupby('symbol')['rs'].transform(lambda x: x.rolling(window).mean())
    
    k = 0.34 / (1.34 + (window + 1) / (window - 1))
    df['yang_zhang_vol'] = np.sqrt(var_o + k * var_c + (1 - k) * var_rs)
    
    # Garman-Klass Volatility (7.4x more efficient than close-to-close metrics)
    df['gk_element'] = 0.5 * (log_h - log_l)**2 - (2 * np.log(2) - 1) * (log_co)**2
    df['garman_klass_vol'] = np.sqrt(df.groupby('symbol')['gk_element'].transform(lambda x: x.rolling(window).mean()))
    
    # --- 2. MULTI-HORIZON MOMENTUM & MARKET BETA ---
    df['ret_1m'] = df.groupby('symbol')['close'].pct_change(1)
    df['ret_5m'] = df.groupby('symbol')['close'].pct_change(5)
    df['ret_15m'] = df.groupby('symbol')['close'].pct_change(15)
    df['ret_60m'] = df.groupby('symbol')['close'].pct_change(60)
    
    # Rolling Market Beta against cross-sectional baseline index
    df['market_ret'] = df.groupby('timestamp')['ret_1m'].transform('mean')
    def calc_beta(group):
        cov = group['ret_1m'].rolling(window).cov(group['market_ret'])
        var = group['market_ret'].rolling(window).var()
        return cov / var
    df['market_beta'] = df.groupby('symbol', group_keys=False).apply(calc_beta)
    
    # --- 3. CLASSIC STRUCTURAL MOMENTUM & OSCILLATORS ---
    # Vectorized Relative Strength Index (RSI-14)
    delta = df.groupby('symbol')['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    ema_gain = df.groupby('symbol', group_keys=False).apply(lambda x: x['close'].diff().clip(lower=0).ewm(com=13, adjust=False).mean())
    ema_loss = df.groupby('symbol', group_keys=False).apply(lambda x: (-x['close'].diff().clip(upper=0)).ewm(com=13, adjust=False).mean())
    rs = ema_gain / (ema_loss + 1e-8)
    df['rsi_14'] = 100 - (100 / (1 + rs))
    
    # Moving Average Convergence Divergence (MACD 12, 26, 9)
    ema_12 = df.groupby('symbol')['close'].transform(lambda x: x.ewm(span=12, adjust=False).mean())
    ema_26 = df.groupby('symbol')['close'].transform(lambda x: x.ewm(span=26, adjust=False).mean())
    df['macd_line'] = ema_12 - ema_26
    df['macd_signal'] = df.groupby('symbol')['macd_line'].transform(lambda x: x.ewm(span=9, adjust=False).mean())
    df['macd_hist'] = df['macd_line'] - df['macd_signal']
    
    # --- 4. VOLUME FACTOR SIZES (24-Hour Horizon) ---
    vol_24h_mean = df.groupby('symbol')['volume'].transform(lambda x: x.rolling(1440).mean())
    df['volume_multiple'] = df['volume'] / (vol_24h_mean + 1e-8)
    
    # --- 5. CRYPTO-VALUE CENTERS (Distance from VWAP) ---
    df['typ_price'] = (df['high'] + df['low'] + df['close']) / 3
    df['pv'] = df['typ_price'] * df['volume']
    rolling_pv = df.groupby('symbol')['pv'].transform(lambda x: x.rolling(window).sum())
    rolling_vol = df.groupby('symbol')['volume'].transform(lambda x: x.rolling(window).sum())
    df['vwap'] = rolling_pv / (rolling_vol + 1e-8)
    df['dist_from_vwap'] = (df['close'] - df['vwap']) / df['vwap']
    
    # --- 6. CYCLICAL CATEGORICAL REGIMES ---
    dt_series = pd.to_datetime(df['timestamp'])
    df['hour_of_day'] = dt_series.dt.hour.astype(str)
    df['day_of_week'] = dt_series.dt.dayofweek.astype(str)
    df['is_weekend'] = dt_series.dt.dayofweek.isin([5, 6]).astype(int).astype(str)
    
    # Drop intermediate processing filters and clear all rolling NaNs
    clean_cols = [
        'log_oc_prev', 'log_co', 'rs', 'gk_element', 
        'market_ret', 'typ_price', 'pv', 'vwap'
    ]
    df = df.drop(columns=clean_cols).dropna().copy()
    return df

def prepare_pools(df):
    print("3. Preparing Cross-Sectional Groups & Splitting Dataset...")
    df = df.sort_values(['timestamp', 'symbol'])
    df['group_id'] = df.groupby('timestamp').ngroup()
    
    timestamps = df['timestamp'].unique()
    n = len(timestamps)
    
    # Chronological out-of-sample data split (70/15/15)
    train_ts = timestamps[:int(n * 0.70)]
    eval_ts = timestamps[int(n * 0.70):int(n * 0.85)]
    test_ts = timestamps[int(n * 0.85):]
    
    train_df = df[df['timestamp'].isin(train_ts)]
    eval_df = df[df['timestamp'].isin(eval_ts)]
    test_df = df[df['timestamp'].isin(test_ts)]
    
    drop_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'target_forward_ret', 'group_id']
    features = [col for col in df.columns if col not in drop_cols]
    cat_features = ['symbol', 'hour_of_day', 'day_of_week', 'is_weekend']
    
    print(f"Training blocks: {len(train_ts)} | Validation blocks: {len(eval_ts)} | Test blocks: {len(test_ts)}")
    
    train_pool = Pool(data=train_df[features], label=train_df['target_forward_ret'], 
                      group_id=train_df['group_id'], cat_features=cat_features)
    
    eval_pool = Pool(data=eval_df[features], label=eval_df['target_forward_ret'], 
                     group_id=eval_df['group_id'], cat_features=cat_features)
    
    test_pool = Pool(data=test_df[features], label=test_df['target_forward_ret'], 
                     group_id=test_df['group_id'], cat_features=cat_features)
                     
    return train_pool, eval_pool, test_pool

def train_and_test():
    df = fetch_data()
    df = engineer_advanced_features(df)
    train_pool, eval_pool, test_pool = prepare_pools(df)
    
    print("4. Initializing CatBoostRanker Decisions Engine...")
    model = CatBoostRanker(
        iterations=1500,
        loss_function='YetiRank',
        eval_metric='NDCG',
        learning_rate=0.03,
        depth=6,
        od_type='Iter',
        od_wait=50,
        verbose=50
    )
    
    print("5. Launching Optimization Engine (In-Sample Training)...")
    model.fit(train_pool, eval_set=eval_pool, use_best_model=True)
    
    print("\n6. Executing Unseen Out-of-Sample Test Evaluation...")
    test_metrics = model.eval_metrics(test_pool, metrics=['NDCG'])
    final_ndcg = test_metrics['NDCG'][-1]
    print(f"\n>>> Out-of-Sample Final Model NDCG Score: {final_ndcg:.4f}")
    
    model.save_model('kraken_ranker_v1.cbm')
    print("Production matrix saved successfully to kraken_ranker_v1.cbm. Engine active.")

if __name__ == "__main__":
    train_and_test()
