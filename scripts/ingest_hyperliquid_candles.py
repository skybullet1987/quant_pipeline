import os, sys, time, warnings
import pandas as pd
import requests
from google.cloud import bigquery
from dotenv import load_dotenv

warnings.filterwarnings("ignore")
load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "parnasa-498503")
HL_INFO_URL = "https://api.hyperliquid.xyz/info"
headers = {"Content-Type": "application/json"}

print("--> [Ingest] Fetching active coin universe from Hyperliquid...")
try:
    meta_resp = requests.post(HL_INFO_URL, json={"type": "metaAndAssetCtxs"}, headers=headers, timeout=15).json()
    universe = meta_resp[0]["universe"]
    symbols = [u["name"] for u in universe if not u.get("isDelisted", False)]
except Exception as e:
    print(f"--> [Ingest Error] Failed fetching universe: {e}")
    sys.exit(1)

print(f"--> [Ingest] Polling latest 1M candles for {len(symbols)} active perpetuals...")
now_ms = int(time.time() * 1000)
start_ms = now_ms - (3 * 24 * 3600 * 1000)  # Catch up 3 days

records = []
for sym in symbols:
    payload = {
        "type": "candleSnapshot",
        "req": {"coin": sym, "interval": "1m", "startTime": start_ms, "endTime": now_ms}
    }
    try:
        r = requests.post(HL_INFO_URL, json=payload, headers=headers, timeout=10)
        if r.status_code == 200:
            for c in r.json():
                records.append({
                    "timestamp": pd.to_datetime(c["t"], unit="ms", utc=True),
                    "ticker": sym,
                    "open": float(c["o"]),
                    "high": float(c["h"]),
                    "low": float(c["l"]),
                    "close": float(c["c"]),
                    "volume": float(c["v"])
                })
    except Exception:
        continue

if not records:
    print("--> [Ingest] No candle data retrieved.")
    sys.exit(0)

df_new = pd.DataFrame(records).drop_duplicates(subset=["timestamp", "ticker"])
print(f"--> [Ingest] Parsed {len(df_new):,} rows. Loading into raw table...")

client = bigquery.Client(project=PROJECT_ID)
raw_table_id = f"{PROJECT_ID}.market_data.raw_ohlcv"
temp_table_id = f"{PROJECT_ID}.market_data.temp_raw_ohlcv_staging"

# Ensure raw table schema exists
ddl_create = f"""
    CREATE TABLE IF NOT EXISTS `{raw_table_id}` (
        timestamp TIMESTAMP,
        ticker STRING,
        open FLOAT64,
        high FLOAT64,
        low FLOAT64,
        close FLOAT64,
        volume FLOAT64
    )
    PARTITION BY DATE(timestamp)
    CLUSTER BY ticker;
"""
client.query(ddl_create).result()

schema = [
    bigquery.SchemaField("timestamp", "TIMESTAMP"),
    bigquery.SchemaField("ticker", "STRING"),
    bigquery.SchemaField("open", "FLOAT64"),
    bigquery.SchemaField("high", "FLOAT64"),
    bigquery.SchemaField("low", "FLOAT64"),
    bigquery.SchemaField("close", "FLOAT64"),
    bigquery.SchemaField("volume", "FLOAT64"),
]

# Load into staging table with explicit schema
client.load_table_from_dataframe(
    df_new, 
    temp_table_id, 
    job_config=bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE", schema=schema)
).result()

# Merge with explicit type casting
merge_query = f"""
    MERGE `{raw_table_id}` T
    USING `{temp_table_id}` S
    ON CAST(T.timestamp AS TIMESTAMP) = CAST(S.timestamp AS TIMESTAMP) 
       AND T.ticker = S.ticker
    WHEN NOT MATCHED THEN
      INSERT (timestamp, ticker, open, high, low, close, volume)
      VALUES (S.timestamp, S.ticker, S.open, S.high, S.low, S.close, S.volume)
"""
client.query(merge_query).result()
client.delete_table(temp_table_id, not_found_ok=True)

print(f"--> [Ingest] [✓] Successfully merged latest candles into {raw_table_id}.")
