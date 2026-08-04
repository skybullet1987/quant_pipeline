import os
import time
import requests
import pandas as pd
from google.cloud import bigquery
from google.api_core.exceptions import GoogleAPIError
from datetime import datetime, timedelta, timezone

# --- CONFIGURATION ---
PROJECT_ID = "parnasa-498503"
DATASET_ID = "market_data"
TABLE_ID = "raw_1m_ohlcv_staging" # NEW TARGET: Staging Table
TABLE_REF = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

TIINGO_API_KEY = os.getenv("TIINGO_API_KEY", "895c0cc1087f3e2d1e60c9f3689903d08981cb26")

# STRICTLY THE 33 MISSING COINS
COIN_UNIVERSE = [
    "enjusd", "zrxusd", "lrcusd", "mkrusd", "bandusd", "kavausd", "omgusd", 
    "renusd", "sushiusd", "grtusd", "yfiusd", "manausd", "crvusd", "storjusd", 
    "chzusd", "balusd", "snxusd", "batusd", "scusd", "icxusd", "kncusd", 
    "1inchusd", "bntusd", "keepusd", "oxtusd", "nmrusd", "ldousd", "rndrusd", 
    "arbusd", "opusd", "injusd", "tiausd", "fetusd"
]

START_DATE = datetime(2021, 7, 21, tzinfo=timezone.utc)
END_DATE = datetime.now(timezone.utc)
CHUNK_DAYS = 3  
MAX_RETRIES = 3

def setup_staging_table(client):
    """Creates the table WITHOUT partitioning to bypass BQ quotas."""
    schema = [
        bigquery.SchemaField("timestamp", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("ticker", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("open", "FLOAT64"),
        bigquery.SchemaField("high", "FLOAT64"),
        bigquery.SchemaField("low", "FLOAT64"),
        bigquery.SchemaField("close", "FLOAT64"),
        bigquery.SchemaField("volume", "FLOAT64")
    ]
    table = bigquery.Table(TABLE_REF, schema=schema)
    
    try:
        client.get_table(TABLE_REF)
        print(f"Staging table {TABLE_REF} already exists.")
    except Exception:
        client.create_table(table)
        print(f"Created unpartitioned staging table {TABLE_REF}.")

def fetch_with_retry(url, headers, params, retries=MAX_RETRIES):
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=15)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"      [!] API Error: {e}. Retrying ({attempt + 1}/{retries})...")
            time.sleep(2 ** attempt)
    return None

def main():
    client = bigquery.Client(project=PROJECT_ID)
    setup_staging_table(client)
    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Token {TIINGO_API_KEY}'
    }

    print(f"\nInitiating V3 Staging Ingestion for {len(COIN_UNIVERSE)} remaining assets...")
    
    for idx, coin in enumerate(COIN_UNIVERSE, 1):
        print(f"\n[{idx}/{len(COIN_UNIVERSE)}] Fetching 5-year history for {coin.upper()} into memory...")
        
        current_start = START_DATE
        coin_master_list = []
        
        while current_start < END_DATE:
            current_end = min(current_start + timedelta(days=CHUNK_DAYS), END_DATE)
            
            url = "https://api.tiingo.com/tiingo/crypto/prices"
            params = {
                'tickers': coin,
                'startDate': current_start.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'endDate': current_end.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'resampleFreq': '1min'
            }
            
            data = fetch_with_retry(url, headers, params)
            
            if data and isinstance(data, list) and len(data) > 0 and 'priceData' in data[0]:
                price_data = data[0]['priceData']
                if price_data:
                    coin_master_list.extend(price_data)
            
            current_start = current_end
            time.sleep(1.0) 
            
        if coin_master_list:
            print(f"  -> Compilation complete. Converting {len(coin_master_list):,} rows to DataFrame...")
            df = pd.DataFrame(coin_master_list)
            df = df.rename(columns={'date': 'timestamp'})
            df['ticker'] = coin.upper()
            
            if 'volumeNotional' in df.columns:
                df['volume'] = df['volumeNotional']
            elif 'volume' not in df.columns:
                df['volume'] = 0.0
                
            df = df[['timestamp', 'ticker', 'open', 'high', 'low', 'close', 'volume']]
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            print(f"  -> Blasting {coin.upper()} to Staging Table...")
            try:
                job = client.load_table_from_dataframe(df, TABLE_REF, job_config=job_config)
                job.result() 
                print(f"  [SUCCESS] {coin.upper()} safely staged.")
            except GoogleAPIError as e:
                print(f"  [!] BigQuery Upload Failed for {coin.upper()}: {e}")
        else:
            print(f"  [WARNING] No data found for {coin.upper()}.")

if __name__ == "__main__":
    main()
