import pandas as pd
from google.cloud import bigquery
import datetime

PROJECT_ID = "parnasa-498503"
DATASET_ID = "market_data"

def check_freshness():
    client = bigquery.Client(project=PROJECT_ID)
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    
    tables_to_check = [
        "stg_ohlcv",
        "stg_1m_cleaned",
        "fct_4h_features_tbm"
    ]
    
    print("=" * 70)
    print(f"      BIGQUERY DATA FRESHNESS AUDIT (Current UTC: {now_utc.strftime('%Y-%m-%d %H:%M:%S')})")
    print("=" * 70)
    
    for table_name in tables_to_check:
        full_table = f"{PROJECT_ID}.{DATASET_ID}.{table_name}"
        query = f"SELECT MAX(timestamp) AS max_ts, COUNT(DISTINCT ticker) as num_tickers FROM `{full_table}`"
        try:
            df = client.query(query).to_dataframe()
            max_ts = pd.to_datetime(df['max_ts'].iloc[0], utc=True)
            num_tickers = df['num_tickers'].iloc[0]
            
            lag = now_utc - max_ts
            lag_hours = lag.total_seconds() / 3600.0
            
            print(f"Table: {table_name:<22} | Max TS: {max_ts.strftime('%Y-%m-%d %H:%M')} UTC | Lag: {lag_hours:6.1f} hrs | Tickers: {num_tickers}")
        except Exception as e:
            print(f"Table: {table_name:<22} | ERROR: {e}")
            
    print("=" * 70)

if __name__ == "__main__":
    check_freshness()
