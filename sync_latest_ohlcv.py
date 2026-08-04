import time
import requests
import datetime
import pandas as pd
from google.cloud import bigquery
from concurrent.futures import ThreadPoolExecutor, as_completed

PROJECT_ID = "parnasa-498503"
DATASET_ID = "market_data"
TABLE_ID = "raw_1m_ohlcv"
TABLE_REF = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
BINANCE_FUTURES_URL = "https://fapi.binance.com/fapi/v1/klines"

def get_bq_watermarks(client):
    """Finds the maximum timestamp per ticker in BigQuery."""
    query = f"""
        SELECT ticker, MAX(timestamp) AS max_ts 
        FROM `{PROJECT_ID}.{DATASET_ID}.stg_ohlcv` 
        GROUP BY ticker
    """
    try:
        df = client.query(query).to_dataframe()
        df['max_ts'] = pd.to_datetime(df['max_ts'], utc=True)
        return dict(zip(df['ticker'], df['max_ts']))
    except Exception as e:
        print(f"Could not fetch watermarks: {e}")
        return {}

def fetch_single_ticker(ticker, max_ts, now_ms, now_utc):
    """Worker task to fetch missing klines for a single ticker."""
    start_ms = int(max_ts.timestamp() * 1000) + 1000
    lag_minutes = (now_utc - max_ts).total_seconds() / 60.0
    
    if lag_minutes < 2.0:
        return ticker, None

    base = ticker.replace('USD', '').replace('USDT', '')
    symbol = f"{base}USDT"
    
    all_candles = []
    current_start = start_ms
    
    while current_start < now_ms:
        params = {
            'symbol': symbol,
            'interval': '1m',
            'startTime': current_start,
            'endTime': now_ms,
            'limit': 1000
        }
        try:
            r = requests.get(BINANCE_FUTURES_URL, params=params, timeout=5)
            if r.status_code != 200:
                break
            data = r.json()
            if not data or not isinstance(data, list):
                break
            all_candles.extend(data)
            current_start = data[-1][0] + 1
        except Exception:
            break
            
    if not all_candles:
        return ticker, None

    df = pd.DataFrame(all_candles, columns=[
        'open_time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'count', 'taker_buy_volume', 'taker_buy_quote_volume', 'ignore'
    ])
    df['timestamp'] = pd.to_datetime(df['open_time'], unit='ms', utc=True)
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)
        
    df['ticker'] = ticker
    return ticker, df[['timestamp', 'ticker', 'open', 'high', 'low', 'close', 'volume']]

def main():
    start_time = time.time()
    client = bigquery.Client(project=PROJECT_ID)
    watermarks = get_bq_watermarks(client)
    
    if not watermarks:
        print("No watermarks found.")
        return

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_ms = int(now_utc.timestamp() * 1000)
    
    print(f"Parallel Market Sync starting across {len(watermarks)} tickers...")
    
    collected_dfs = []
    
    # Run API fetches in parallel across 10 threads
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(fetch_single_ticker, ticker, max_ts, now_ms, now_utc)
            for ticker, max_ts in watermarks.items()
        ]
        
        for future in as_completed(futures):
            ticker, df_ticker = future.result()
            if df_ticker is not None and not df_ticker.empty:
                collected_dfs.append(df_ticker)
                
    if not collected_dfs:
        print(f"[OK] All tickers up to date. Sync completed in {time.time() - start_time:.2f}s.")
        return

    # Single Bulk Load Job to BigQuery
    full_df = pd.concat(collected_dfs, ignore_index=True)
    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
    
    print(f"Uploading {len(full_df):,} bars to BigQuery in 1 bulk job...")
    job = client.load_table_from_dataframe(full_df, TABLE_REF, job_config=job_config)
    job.result()
    
    print(f"[SUCCESS] Appended {len(full_df):,} total bars in {time.time() - start_time:.2f}s!")

if __name__ == "__main__":
    main()
