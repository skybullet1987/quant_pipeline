import os
import time
import requests
import pandas as pd
from google.cloud import bigquery
from datetime import datetime, timedelta, timezone

# --- CONFIGURATION ---
TIINGO_API_KEY = "895c0cc1087f3e2d1e60c9f3689903d08981cb26"
GCP_PROJECT = "parnasa-498503"
BQ_TABLE = f"{GCP_PROJECT}.market_data.raw_ohlcv"

COIN_UNIVERSE = [
    "btcusd", "ethusd", "solusd", "adausd", "xrpusd", "dotusd", "dogeusd", 
    "avaxusd", "linkusd", "maticusd", "ltcusd", "bchusd", "algousd", "xlmusd", 
    "atomusd", "uniusd", "filusd", "trxusd", "xtzusd", "eosusd", "aaveusd",
    "mkrusd", "snxusd", "compusd", "grtusd", "batusd", "enjusd", "manausd",
    "chzusd", "zrxusd", "crvusd", "sushiusd", "yfiusd", "1inchusd", "omgusd",
    "icxusd", "kavausd", "balusd", "bntusd", "renusd", "kncusd", "bandusd",
    "scusd", "storjusd", "oceanusd", "lrcusd", "keepusd", "oxtusd", "nmrusd",
    "dashusd", "zecusd", "xmrusd"
]

# Modern timezone-aware dates
END_DATE = datetime.now(timezone.utc)
START_DATE = END_DATE - timedelta(days=180)
CHUNK_DAYS = 5  # Pulling 5 days at a time bypasses Tiingo's row limits

def fetch_and_load():
    client = bigquery.Client(project=GCP_PROJECT)
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Token {TIINGO_API_KEY}'
    }

    print(f"Initiating chunked Tiingo ingestion for {len(COIN_UNIVERSE)} assets...")
    
    for coin in COIN_UNIVERSE:
        print(f"\nFetching 1-min data for {coin}...")
        
        current_start = START_DATE
        total_rows_for_coin = 0
        
        # Paginate through time in 5-day chunks
        while current_start < END_DATE:
            current_end = min(current_start + timedelta(days=CHUNK_DAYS), END_DATE)
            
            url = "https://api.tiingo.com/tiingo/crypto/prices"
            params = {
                'tickers': coin,
                'startDate': current_start.strftime('%Y-%m-%d'),
                'endDate': current_end.strftime('%Y-%m-%d'),
                'resampleFreq': '1min',
                'exchanges': 'kraken' # Lowercase is safer for Tiingo's backend
            }
            
            try:
                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()
                
                # Check if API returned an error dictionary instead of a list
                if isinstance(data, dict) and 'detail' in data:
                    print(f"  -> API Error: {data['detail']}")
                    break
                
                # If no data in this chunk, move to the next window
                if not data or len(data) == 0 or 'priceData' not in data[0]:
                    current_start = current_end
                    time.sleep(1)
                    continue
                    
                price_data = data[0]['priceData']
                df = pd.DataFrame(price_data)
                
                if df.empty:
                    current_start = current_end
                    time.sleep(1)
                    continue
                
                df = df.rename(columns={
                    'date': 'timestamp',
                    'tradesDone': 'trades'
                })
                df['ticker'] = coin.upper()
                
                # Ensure structure matches BigQuery perfectly
                df = df[['timestamp', 'ticker', 'open', 'high', 'low', 'close', 'volume']]
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                
                # Stream directly to BigQuery
                job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
                job = client.load_table_from_dataframe(df, BQ_TABLE, job_config=job_config)
                job.result()
                
                total_rows_for_coin += len(df)
                
            except Exception as e:
                print(f"  -> Chunk failed ({current_start.date()}): {str(e)}")
            
            # Step the window forward and respect rate limits
            current_start = current_end
            time.sleep(1.5)
            
        print(f"*** Successfully loaded {total_rows_for_coin} total rows for {coin} ***")

if __name__ == "__main__":
    fetch_and_load()
