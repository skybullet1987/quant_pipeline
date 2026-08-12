import argparse
import json
import logging
import time
from datetime import datetime, timezone
import pandas as pd
import requests
from google.cloud import bigquery

# Force immediate unbuffered logging output
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", force=True)

PROJECT_ID = "parnasa-498503"
DATASET_ID = "market_data"

def fetch_binance_klines_page(symbol: str, end_time: int = None, limit: int = 1000):
    url = "https://fapi.binance.com/fapi/v1/klines"
    params = {"symbol": f"{symbol}USDT", "interval": "1m", "limit": limit}
    if end_time:
        params["endTime"] = end_time
        
    retries = 0
    while retries < 5:
        try:
            res = requests.get(url, params=params, timeout=10)
            used_weight = int(res.headers.get("x-mbx-used-weight-1m", 0))
            
            if res.status_code == 200:
                if used_weight > 1900:
                    logging.info(f"[{symbol}] Weight capacity high ({used_weight}/2400). Pausing 8s...")
                    time.sleep(8)
                else:
                    time.sleep(0.03)
                return res.json()
                
            elif res.status_code in [429, 418]:
                wait_time = int(res.headers.get("Retry-After", 30))
                logging.warning(f"[{symbol}] RATE LIMIT HIT! Sleeping for {wait_time}s...")
                time.sleep(wait_time)
                retries += 1
            else:
                logging.error(f"[{symbol}] HTTP {res.status_code} - {res.text}")
                return []
        except requests.exceptions.RequestException as e:
            logging.error(f"[{symbol}] Network error: {e}")
            time.sleep(5)
            retries += 1
            
    return []

def backfill_coin(symbol: str, max_pages: int = 3500):
    all_klines = []
    end_time = None
    
    for page in range(1, max_pages + 1):
        klines = fetch_binance_klines_page(symbol, end_time=end_time)
        if not klines:
            break
            
        all_klines.extend(klines)
        end_time = klines[0][0] - 1 
        
        # Log progress every 50 pages (50,000 candles)
        if page % 50 == 0:
            dt = datetime.fromtimestamp(klines[0][0] / 1000.0, tz=timezone.utc)
            logging.info(f"[{symbol}] Downloaded {len(all_klines):,} candles (Reached {dt.strftime('%Y-%m-%d')})...")
        
        if len(klines) < 1000:
            dt = datetime.fromtimestamp(klines[0][0] / 1000.0, tz=timezone.utc)
            logging.info(f"[{symbol}] Reached earliest listing date: {dt.strftime('%Y-%m-%d')}")
            break
            
    return all_klines

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--coins", type=str, required=True)
    parser.add_argument("--dest", type=str, default="raw_1m_ohlcv")
    args = parser.parse_args()

    with open(args.coins, "r") as f:
        coins = json.load(f)

    bq_client = bigquery.Client(project=PROJECT_ID)
    target_table = f"{PROJECT_ID}.{DATASET_ID}.{args.dest}"
    staging_table = f"{PROJECT_ID}.{DATASET_ID}.temp_staging_backfill"

    for coin in coins:
        logging.info(f"Starting deep historical backfill for {coin}...")
        klines = backfill_coin(coin)
        
        if not klines:
            logging.warning(f"Skipping {coin} - no data returned.")
            continue

        rows = []
        for k in klines:
            ts = datetime.fromtimestamp(k[0] / 1000.0, tz=timezone.utc)
            rows.append({
                "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "ticker": f"{coin}USD",
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5])
            })

        df = pd.DataFrame(rows)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        logging.info(f"[{coin}] Extracted {len(df):,} total rows. Running BigQuery MERGE...")
        
        job_config = bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE")
        bq_client.load_table_from_dataframe(df, staging_table, job_config=job_config).result()
        
        merge_sql = f"""
        MERGE `{target_table}` T
        USING `{staging_table}` S
        ON T.ticker = S.ticker AND T.timestamp = S.timestamp
        WHEN NOT MATCHED THEN
          INSERT (timestamp, ticker, open, high, low, close, volume)
          VALUES (S.timestamp, S.ticker, S.open, S.high, S.low, S.close, S.volume)
        """
        bq_client.query(merge_sql).result()
        logging.info(f"[{coin}] BigQuery MERGE complete!")

    logging.info("Full deep backfill completed successfully across all coins!")

if __name__ == "__main__":
    main()
