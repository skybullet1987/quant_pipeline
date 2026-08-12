import datetime
import requests
import pandas as pd
from google.cloud import bigquery
from concurrent.futures import ThreadPoolExecutor, as_completed

PROJECT_ID = "parnasa-498503"
DATASET_ID = "market_data"
TABLE_ID = "raw_1h_ohlcv"
TABLE_REF = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
BINANCE_FUTURES_URL = "https://fapi.binance.com/fapi/v1/klines"

client = bigquery.Client(project=PROJECT_ID)

# Pull full universe directly from stg_ohlcv / raw_1m_ohlcv
q = f"SELECT DISTINCT ticker FROM `{PROJECT_ID}.{DATASET_ID}.stg_ohlcv`"
tickers = [row.ticker for row in client.query(q).result()]

print(f"Fetching fresh 1H candles from Binance across ALL {len(tickers)} tickers...")

def fetch_ticker_1h(ticker):
    base = ticker.replace('USD', '').replace('USDT', '')
    symbol = f"{base}USDT"
    params = {'symbol': symbol, 'interval': '1h', 'limit': 1000} # 1000 hours = ~41 days
    try:
        r = requests.get(BINANCE_FUTURES_URL, params=params, timeout=5)
        if r.status_code == 200 and isinstance(r.json(), list):
            rows = []
            for item in r.json():
                rows.append({
                    'timestamp': pd.to_datetime(item[0], unit='ms', utc=True),
                    'ticker': ticker,
                    'open': float(item[1]),
                    'high': float(item[2]),
                    'low': float(item[3]),
                    'close': float(item[4]),
                    'volume': float(item[5])
                })
            return pd.DataFrame(rows)
    except Exception:
        pass
    return None

frames = []
with ThreadPoolExecutor(max_workers=20) as executor:
    futures = {executor.submit(fetch_ticker_1h, t): t for t in tickers}
    for future in as_completed(futures):
        df = future.result()
        if df is not None and not df.empty:
            frames.append(df)

if frames:
    full_df = pd.concat(frames, ignore_index=True)
    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_TRUNCATE", # Clean snapshot of last 41 days of 1H data
        autodetect=True
    )
    job = client.load_table_from_dataframe(full_df, TABLE_REF, job_config=job_config)
    job.result()
    print(f"[SUCCESS] Updated {TABLE_REF} with {len(full_df)} fresh 1H bars up to today!")
else:
    print("[ERROR] Failed to fetch 1H klines.")
