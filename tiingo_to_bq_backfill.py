import os
import time
import requests
from datetime import datetime, timedelta
from google.cloud import bigquery
from google.api_core.exceptions import GoogleAPIError

# --- CONFIGURATION ---
TIINGO_API_KEY = "895c0cc1087f3e2d1e60c9f3689903d08981cb26"
PROJECT_ID = "parnasa-498503"
DATASET_ID = "market_data"
TABLE_ID = "raw_ohlcv"
FULL_TABLE_REF = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

# 9-month rolling window (October 19, 2025 to July 19, 2026)
START_DATE = datetime(2025, 10, 19)
END_DATE = datetime(2026, 7, 19)

# Initial Kraken target universe mapped to Tiingo
TICKERS = [
    "btcusd", "ethusd", "solusd", "xrpusd", "adausd", 
    "dogeusd", "linkusd", "dotusd", "maticusd", "avaxusd"
]

bq_client = bigquery.Client(project=PROJECT_ID)

def initialize_table():
    """Creates the BigQuery table with time partitioning and ticker clustering."""
    schema = [
        bigquery.SchemaField("timestamp", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("ticker", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("open", "FLOAT64", mode="REQUIRED"),
        bigquery.SchemaField("high", "FLOAT64", mode="REQUIRED"),
        bigquery.SchemaField("low", "FLOAT64", mode="REQUIRED"),
        bigquery.SchemaField("close", "FLOAT64", mode="REQUIRED"),
        bigquery.SchemaField("volume", "FLOAT64", mode="REQUIRED"),
        bigquery.SchemaField("volume_notional", "FLOAT64", mode="NULLABLE"),
    ]
    
    table = bigquery.Table(FULL_TABLE_REF, schema=schema)
    table.time_partitioning = bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY,
        field="timestamp"
    )
    table.clustering_fields = ["ticker"]
    
    try:
        bq_client.get_table(FULL_TABLE_REF)
        print(f"Table {FULL_TABLE_REF} exists. Starting backfill.")
    except Exception:
        print(f"Creating optimized table: {FULL_TABLE_REF}")
        bq_client.create_table(table)

def fetch_tiingo_chunk(ticker, start_str, end_str):
    """Fetches a 7-day 1-minute OHLCV slice to respect API payload limits."""
    url = f"https://api.tiingo.com/tiingo/crypto/prices"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Token {TIINGO_API_KEY}"
    }
    params = {
        "tickers": ticker,
        "resampleFreq": "1min",
        "startDate": start_str,
        "endDate": end_str
    }
    
    for attempt in range(3):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                print(" Rate limit hit. Sleeping 10s...")
                time.sleep(10)
            else:
                print(f" HTTP {response.status_code} for {ticker}: {response.text}")
                time.sleep(2)
        except requests.exceptions.RequestException as e:
            print(f" Connection error: {e}. Retrying...")
            time.sleep(5)
    return None

def process_and_upload(data):
    """Transforms the payload and streams directly into BigQuery."""
    if not data or not isinstance(data, list) or len(data) == 0:
        return
    
    ticker_entry = data[0]
    ticker = ticker_entry.get("ticker").lower()
    price_data = ticker_entry.get("priceData", [])
    
    rows = [{
        "timestamp": r["date"],
        "ticker": ticker,
        "open": float(r["open"]),
        "high": float(r["high"]),
        "low": float(r["low"]),
        "close": float(r["close"]),
        "volume": float(r["volume"]),
        "volume_notional": float(r.get("volumeNotional")) if r.get("volumeNotional") is not None else None
    } for r in price_data]
        
    if not rows:
        return

    errors = bq_client.insert_rows_json(FULL_TABLE_REF, rows)
    if errors:
        raise GoogleAPIError(f"BQ insertion errors: {errors}")
    else:
        print(f"   Inserted {len(rows)} rows into {TABLE_ID}.")

def run_backfill():
    initialize_table()
    
    for ticker in TICKERS:
        print(f"\n--- Backfilling: {ticker.upper()} ---")
        current_start = START_DATE
        
        while current_start < END_DATE:
            current_end = min(current_start + timedelta(days=7), END_DATE)
            start_str = current_start.strftime("%Y-%m-%d")
            end_str = current_end.strftime("%Y-%m-%d")
            
            print(f" Fetching {start_str} to {end_str}...")
            payload = fetch_tiingo_chunk(ticker, start_str, end_str)
            
            if payload:
                process_and_upload(payload)
            
            current_start = current_end
            time.sleep(0.5)

if __name__ == "__main__":
    run_backfill()
