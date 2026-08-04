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
TABLE_ID = "raw_1m_ohlcv" 
TABLE_REF = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

TIINGO_API_KEY = os.getenv("TIINGO_API_KEY", "895c0cc1087f3e2d1e60c9f3689903d08981cb26")

START_DATE = datetime(2021, 7, 21, tzinfo=timezone.utc)
END_DATE = datetime.now(timezone.utc)
CHUNK_DAYS = 3  
MAX_RETRIES = 3

def get_full_universe(client):
    # Querying the downstream feature table because raw_1m_ohlcv was wiped!
    safe_table = f"{PROJECT_ID}.{DATASET_ID}.fct_4h_features_tbm"
    print(f"Fetching full coin universe from downstream table: {safe_table}...")
    query = f"SELECT DISTINCT ticker FROM `{safe_table}`"
    try:
        df = client.query(query).to_dataframe()
        universe = df['ticker'].str.lower().tolist()
        print(f"-> Found {len(universe)} unique coins in the database.")
        return universe
    except Exception as e:
        print(f"Error fetching universe: {e}")
        return []

def setup_clean_table(client):
    client.delete_table(TABLE_REF, not_found_ok=True)
    print(f"Purged old aggregated table: {TABLE_REF}")
    
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
    table.time_partitioning = bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY,
        field="timestamp"
    )
    table.clustering_fields = ["ticker"]
    
    client.create_table(table)
    print(f"Created fresh partitioned Binance table: {TABLE_REF}")

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
    
    # Get universe before dropping table
    coin_universe = get_full_universe(client)
    if not coin_universe:
        print("Aborting: Could not retrieve coin universe.")
        return
        
    setup_clean_table(client)
    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Token {TIINGO_API_KEY}'
    }

    print(f"\nInitiating PURE BINANCE Ingestion for {len(coin_universe)} assets...")
    
    for idx, coin in enumerate(coin_universe, 1):
        # Force the global Binance USDT market pair
        base_coin = coin.replace('usdt', '').replace('usd', '')
        tiingo_ticker = f"{base_coin}usdt"
        
        print(f"\n[{idx}/{len(coin_universe)}] Fetching 5-year Binance history for {tiingo_ticker.upper()}...")
        
        current_start = START_DATE
        coin_master_list = []
        
        while current_start < END_DATE:
            current_end = min(current_start + timedelta(days=CHUNK_DAYS), END_DATE)
            
            url = "https://api.tiingo.com/tiingo/crypto/prices"
            params = {
                'tickers': tiingo_ticker,
                'startDate': current_start.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'endDate': current_end.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'resampleFreq': '1min',
                'exchanges': 'binance' 
            }
            
            data = fetch_with_retry(url, headers, params)
            
            if data and isinstance(data, list) and len(data) > 0 and 'priceData' in data[0]:
                price_data = data[0]['priceData']
                if price_data:
                    coin_master_list.extend(price_data)
            
            current_start = current_end
            time.sleep(1.0) 
            
        if coin_master_list:
            df = pd.DataFrame(coin_master_list)
            df = df.rename(columns={'date': 'timestamp'})
            
            # Map back to standard database ticker format
            df['ticker'] = coin.upper() 
            
            if 'volumeNotional' in df.columns:
                df['volume'] = df['volumeNotional']
            elif 'volume' not in df.columns:
                df['volume'] = 0.0
                
            df = df[['timestamp', 'ticker', 'open', 'high', 'low', 'close', 'volume']]
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            try:
                job = client.load_table_from_dataframe(df, TABLE_REF, job_config=job_config)
                job.result() 
                print(f"  [SUCCESS] {coin.upper()} safely staged ({len(df):,} rows).")
            except GoogleAPIError as e:
                print(f"  [!] BigQuery Upload Failed for {coin.upper()}: {e}")
        else:
            print(f"  [WARNING] No Binance data found for {tiingo_ticker.upper()}.")

if __name__ == "__main__":
    main()
