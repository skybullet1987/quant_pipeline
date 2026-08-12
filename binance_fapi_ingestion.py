import argparse
import json
import logging
import time
from datetime import datetime, timezone
import pandas as pd
import requests
from google.cloud import bigquery

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

PROJECT_ID = "parnasa-498503"
DATASET_ID = "market_data"

def fetch_binance_klines(symbol: str, interval: str = "1m", limit: int = 1000):
    url = "https://fapi.binance.com/fapi/v1/klines"
    params = {
        "symbol": f"{symbol}USDT",
        "interval": interval,
        "limit": limit
    }
    try:
        res = requests.get(url, params=params, timeout=10)
        if res.status_code == 200:
            return res.json()
        else:
            logging.warning(f"Could not fetch {symbol}USDT (Status {res.status_code})")
            return []
    except Exception as e:
        logging.error(f"Failed request for {symbol}: {e}")
        return []

def main():
    parser = argparse.ArgumentParser(description="Idempotent Binance Futures Ingestion to BigQuery")
    parser.add_argument("--coins", type=str, required=True, help="Path to JSON file containing target coin list")
    parser.add_argument("--dest", type=str, default="raw_1m_ohlcv", help="Destination BigQuery table name")
    args = parser.parse_args()

    with open(args.coins, "r") as f:
        coins = json.load(f)

    logging.info(f"Loaded {len(coins)} target assets from {args.coins}")

    bq_client = bigquery.Client(project=PROJECT_ID)
    target_table = f"{PROJECT_ID}.{DATASET_ID}.{args.dest}"
    staging_table = f"{PROJECT_ID}.{DATASET_ID}.temp_staging_1m_ohlcv"

    all_rows = []
    for coin in coins:
        logging.info(f"Fetching 1m candles for {coin}...")
        klines = fetch_binance_klines(coin, interval="1m", limit=1000)
        
        for k in klines:
            ts = datetime.fromtimestamp(k[0] / 1000.0, tz=timezone.utc)
            all_rows.append({
                "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "ticker": f"{coin}USD",
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5])
            })
        
        time.sleep(0.05)

    if all_rows:
        df = pd.DataFrame(all_rows)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Step 1: Write raw batch to temporary staging table
        logging.info(f"Uploading batch to staging table {staging_table}...")
        job_config = bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE")
        bq_client.load_table_from_dataframe(df, staging_table, job_config=job_config).result()
        
        # Step 2: Atomic MERGE to prevent duplicate timestamps per ticker
        merge_sql = f"""
        MERGE `{target_table}` T
        USING `{staging_table}` S
        ON T.ticker = S.ticker AND T.timestamp = S.timestamp
        WHEN NOT MATCHED THEN
          INSERT (timestamp, ticker, open, high, low, close, volume)
          VALUES (S.timestamp, S.ticker, S.open, S.high, S.low, S.close, S.volume)
        """
        logging.info("Executing atomic MERGE to deduplicate incoming data...")
        bq_client.query(merge_sql).result()
        logging.info("Ingestion and deduplication completed successfully.")
    else:
        logging.warning("No data returned for ingestion.")

if __name__ == "__main__":
    main()
