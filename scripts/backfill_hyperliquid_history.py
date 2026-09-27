import os, time, argparse, requests
import pandas as pd
from google.cloud import bigquery
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "parnasa-498503")

parser = argparse.ArgumentParser()
parser.add_argument("--days", type=int, default=90)
args = parser.parse_args()

print(f"--> [1/3] Fetching universe metadata and {args.days}D candle history from Hyperliquid...")
info_url = "https://api.hyperliquid.xyz/info"
meta_res = requests.post(info_url, json={"type": "meta"}).json()
universe = [u["name"] for u in meta_res["universe"]]
print(f"    Found {len(universe)} active perpetual assets.")

end_ts = int(time.time() * 1000)
start_ts = end_ts - (args.days * 86400 * 1000)

all_rows = []

def fetch_coin_candles(coin):
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": coin,
            "interval": "4h",
            "startTime": start_ts,
            "endTime": end_ts
        }
    }
    try:
        res = requests.post(info_url, json=payload, timeout=10)
        data = res.json()
        if not data:
            return []
        
        parsed = []
        for c in data:
            parsed.append({
                "timestamp": pd.to_datetime(c["t"], unit="ms", utc=True),
                "ticker": coin,
                "open": float(c["o"]),
                "high": float(c["h"]),
                "low": float(c["l"]),
                "close": float(c["c"]),
                "volume": float(c["v"])
            })
        return parsed
    except Exception as e:
        print(f"    [!] Failed fetching {coin}: {e}")
        return []

with ThreadPoolExecutor(max_workers=12) as executor:
    futures = [executor.submit(fetch_coin_candles, coin) for coin in universe]
    for fut in as_completed(futures):
        all_rows.extend(fut.result())

df = pd.DataFrame(all_rows)
print(f"--> [2/3] Collected {len(df):,} total 4H candle records across {df['ticker'].nunique()} assets.")

# Write to BigQuery raw_ohlcv
print(f"--> [3/3] Overwriting `{PROJECT_ID}.market_data.raw_ohlcv` in BigQuery...")
client = bigquery.Client(project=PROJECT_ID)
table_id = f"{PROJECT_ID}.market_data.raw_ohlcv"

job_config = bigquery.LoadJobConfig(
    write_disposition="WRITE_TRUNCATE",
    time_partitioning=bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY,
        field="timestamp"
    ),
    clustering_fields=["ticker"]
)

job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
job.result()
print(f"    [✓] Successfully ingested {len(df):,} rows into BigQuery.")
