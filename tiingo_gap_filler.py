import time
import requests
import pandas as pd
from datetime import datetime, timedelta
from google.cloud import bigquery

PROJECT_ID = "parnasa-498503"
TABLE_ID = f"{PROJECT_ID}.market_data.raw_kraken_history"
TIINGO_API_KEY = "895c0cc1087f3e2d1e60c9f3689903d08981cb26"

bq_client = bigquery.Client(project=PROJECT_ID)

# Complete 50-coin liquid Kraken universe (Tiingo format)
SYMBOLS = [
    "btcusd", "ethusd", "solusd", "xrpusd", "adausd", "dogeusd", "dotusd", "avaxusd", "linkusd", "shibusd",
    "ltcusd", "unicusdt", "bchusd", "hbarusd", "xlmusd", "filusd", "aptusd", "nearusd", "imxusd", "injusd",
    "opusd", "grtusd", "stxusd", "rndrusd", "galausd", "mkrusd", "fetusd", "ltdusd", "wbuusd", "suinusd",
    "arbusd", "ldousd", "atomusd", "tiausd", "algousd", "qntusd", "flowusd", "egldusd", "manausd", "sandusd",
    "axsusd", "chzusd", "minausd", "eosusd", "crvusd", "ftmusd", "aaveusd", "thetausd", "xmrusd", "zecusd"
]

START_DATE = datetime(2020, 1, 1)
END_DATE = datetime(2026, 7, 17)

def fetch_tiingo_history_chunk(symbol, start_str, end_str):
    url = "https://api.tiingo.com/tiingo/crypto/prices"
    headers = {'Content-Type': 'application/json', 'Authorization': f'Token {TIINGO_API_KEY}'}
    params = {
        'tickers': symbol,
        'startDate': start_str,
        'endDate': end_str,
        'resampleFreq': '1min',
        'exchanges': 'kraken'
    }
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        if response.status_code != 200:
            return None
        data = response.json()
        if not data or 'priceData' not in data[0] or not data[0]['priceData']:
            return None
        return pd.DataFrame(data[0]['priceData'])
    except Exception:
        return None

def process_and_load(symbol):
    print(f"--- Starting backfill for {symbol} ---")
    current_start = START_DATE
    while current_start < END_DATE:
        current_end = min(current_start + timedelta(days=5), END_DATE)
        start_str = current_start.strftime('%Y-%m-%d')
        end_str = current_end.strftime('%Y-%m-%d')
        
        df = fetch_tiingo_history_chunk(symbol, start_str, end_str)
        
        if df is not None and not df.empty:
            df['timestamp'] = pd.to_datetime(df['date'], utc=True)
            
            # Normalizing asset naming conventions to match Kraken system targets
            db_symbol_map = {"btcusd": "XXBTZUSD", "ethusd": "XETHZUSD"}
            df['symbol'] = db_symbol_map.get(symbol, symbol.upper())
            
            df['trades'] = df['tradesCount'].fillna(0).astype(int)
            df['volume'] = df['volume'].astype(float)
            df = df[['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume', 'trades']]
            
            job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
            job = bq_client.load_table_from_dataframe(df, TABLE_ID, job_config=job_config)
            job.result()
            print(f"[{symbol.upper()}] Loaded rows for segment {start_str} to {end_str}")
            
        current_start = current_end + timedelta(days=1)
        time.sleep(0.1)

if __name__ == "__main__":
    for ticker in SYMBOLS:
        process_and_load(ticker)
