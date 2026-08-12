import os
import glob
import requests
import pandas as pd
from io import BytesIO
from zipfile import ZipFile
from google.cloud import bigquery
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
import concurrent.futures

# --- CONFIGURATION ---
PROJECT_ID = "parnasa-498503"
DATASET_ID = "market_data"

START_DATE = datetime(2021, 7, 1)
END_DATE = datetime.now(timezone.utc).replace(tzinfo=None)

SCHEMAS = {
    'fundingRate': {
        'final_table': f"{PROJECT_ID}.{DATASET_ID}.raw_funding_rate",
        'temp_table': f"{PROJECT_ID}.{DATASET_ID}.raw_funding_rate_temp",
        'fields': [
            bigquery.SchemaField("timestamp", "TIMESTAMP", mode="NULLABLE"),
            bigquery.SchemaField("ticker", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("funding_rate", "FLOAT64", mode="NULLABLE")
        ],
        'numeric_cols': ['funding_rate']
    },
    'metrics': {
        'final_table': f"{PROJECT_ID}.{DATASET_ID}.raw_open_interest",
        'temp_table': f"{PROJECT_ID}.{DATASET_ID}.raw_open_interest_temp",
        'fields': [
            bigquery.SchemaField("timestamp", "TIMESTAMP", mode="NULLABLE"),
            bigquery.SchemaField("ticker", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("sum_open_interest", "FLOAT64", mode="NULLABLE"),
            bigquery.SchemaField("sum_open_interest_value", "FLOAT64", mode="NULLABLE"),
            bigquery.SchemaField("count_long_short_ratio", "FLOAT64", mode="NULLABLE"),
            bigquery.SchemaField("sum_toptrader_long_short_ratio", "FLOAT64", mode="NULLABLE"),
            bigquery.SchemaField("sum_taker_long_short_vol_ratio", "FLOAT64", mode="NULLABLE")
        ],
        'numeric_cols': [
            'sum_open_interest', 'sum_open_interest_value',
            'count_long_short_ratio', 'sum_toptrader_long_short_ratio',
            'sum_taker_long_short_vol_ratio'
        ]
    },
    'liquidationSnapshot': {
        'final_table': f"{PROJECT_ID}.{DATASET_ID}.raw_liquidations",
        'temp_table': f"{PROJECT_ID}.{DATASET_ID}.raw_liquidations_temp",
        'fields': [
            bigquery.SchemaField("timestamp", "TIMESTAMP", mode="NULLABLE"),
            bigquery.SchemaField("ticker", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("side", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("price", "FLOAT64", mode="NULLABLE"),
            bigquery.SchemaField("original_quantity", "FLOAT64", mode="NULLABLE")
        ],
        'numeric_cols': ['price', 'original_quantity']
    }
}

def get_full_universe(client):
    safe_table = f"{PROJECT_ID}.{DATASET_ID}.fct_4h_features_tbm"
    try:
        df = client.query(f"SELECT DISTINCT ticker FROM `{safe_table}`").to_dataframe()
        return df['ticker'].str.upper().tolist()
    except Exception as e:
        print(f"Error fetching universe: {e}")
        return []

def generate_urls(ticker, dataset):
    ticker_usdt = ticker.replace('USD', '').replace('USDT', '') + 'USDT'
    urls = []
    current_date = START_DATE
    if dataset == 'fundingRate':
        while current_date <= END_DATE:
            month_str = str(current_date.month).zfill(2)
            filename = f"{ticker_usdt}-fundingRate-{current_date.year}-{month_str}"
            urls.append(f"https://data.binance.vision/data/futures/um/monthly/fundingRate/{ticker_usdt}/{filename}.zip")
            current_date += relativedelta(months=1)
    else:
        while current_date <= END_DATE:
            month_str = str(current_date.month).zfill(2)
            day_str = str(current_date.day).zfill(2)
            filename = f"{ticker_usdt}-{dataset}-{current_date.year}-{month_str}-{day_str}"
            urls.append(f"https://data.binance.vision/data/futures/um/daily/{dataset}/{ticker_usdt}/{filename}.zip")
            current_date += relativedelta(days=1)
    return urls

def fetch_url(url, ticker, dataset):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return None
            
        with ZipFile(BytesIO(response.content)) as z:
            csv_filename = [n for n in z.namelist() if n.endswith('.csv')][0]
            with z.open(csv_filename) as f:
                df = pd.read_csv(f)
                df.columns = [c.lower().strip() for c in df.columns]
                res = pd.DataFrame()
                
                if dataset == 'fundingRate':
                    ts = pd.to_numeric(df['calc_time'], errors='coerce')
                    res['timestamp'] = pd.to_datetime(ts, unit='ms', errors='coerce')
                    res['funding_rate'] = df['last_funding_rate']
                elif dataset == 'metrics':
                    # Parse ISO string timestamp directly
                    res['timestamp'] = pd.to_datetime(df['create_time'], errors='coerce')
                    for col in ['sum_open_interest', 'sum_open_interest_value', 
                                'count_long_short_ratio', 'sum_toptrader_long_short_ratio', 
                                'sum_taker_long_short_vol_ratio']:
                        res[col] = df[col] if col in df.columns else None
                elif dataset == 'liquidationSnapshot':
                    time_col = 'time' if 'time' in df.columns else 'timestamp'
                    ts = pd.to_numeric(df[time_col], errors='coerce')
                    res['timestamp'] = pd.to_datetime(ts, unit='ms', errors='coerce')
                    res['side'] = df['side'].astype(str)
                    res['price'] = df['price']
                    qty_col = 'original_quantity' if 'original_quantity' in df.columns else 'qty'
                    res['original_quantity'] = df[qty_col] if qty_col in df.columns else None
                
                res['ticker'] = ticker
                res = res.dropna(subset=['timestamp'])
                return res
    except Exception:
        return None

def process_dataset(client, universe, dataset):
    cache_dir = f"data_cache_{dataset}"
    os.makedirs(cache_dir, exist_ok=True)
    
    print(f"\n=======================================================")
    print(f"PROCESSING DATASET: {dataset.upper()}")
    print(f"=======================================================")
    
    print(f"\n--- Phase 1: Multithreaded Caching ({dataset}) ---")
    for idx, ticker in enumerate(universe, 1):
        parquet_path = os.path.join(cache_dir, f"{ticker}.parquet")
        if os.path.exists(parquet_path):
            print(f"[{idx}/{len(universe)}] {ticker} already cached.")
            continue
            
        print(f"[{idx}/{len(universe)}] Downloading {ticker}...")
        urls = generate_urls(ticker, dataset)
        dfs = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            future_to_url = {executor.submit(fetch_url, url, ticker, dataset): url for url in urls}
            for future in concurrent.futures.as_completed(future_to_url):
                res_df = future.result()
                if res_df is not None and not res_df.empty:
                    dfs.append(res_df)
                    
        if dfs:
            final_df = pd.concat(dfs, ignore_index=True)
            if 'timestamp' in final_df.columns:
                if dataset in ['fundingRate', 'metrics']:
                    final_df = final_df.drop_duplicates(subset=['timestamp', 'ticker'], keep='last')
                else:
                    final_df = final_df.drop_duplicates()
                    
                final_df = final_df.sort_values('timestamp').reset_index(drop=True)
                
                for col in SCHEMAS[dataset]['numeric_cols']:
                    if col in final_df.columns:
                        final_df[col] = pd.to_numeric(final_df[col], errors='coerce').astype('float64')
                    
                final_df.to_parquet(parquet_path, index=False)
                print(f"  [CACHED] {ticker} saved locally ({len(final_df):,} rows).")
        else:
            print(f"  [WARNING] No data found for {ticker}.")

    print(f"\n--- Phase 2: Streaming to Unpartitioned Temp Table ({dataset}) ---")
    config = SCHEMAS[dataset]
    temp_ref = config['temp_table']
    final_ref = config['final_table']
    
    client.delete_table(temp_ref, not_found_ok=True)
    table = bigquery.Table(temp_ref, schema=config['fields'])
    client.create_table(table)
    
    parquet_files = sorted(glob.glob(os.path.join(cache_dir, "*.parquet")))
    if not parquet_files:
        print(f"No {dataset} parquet files to stream.")
        return
        
    job_config = bigquery.LoadJobConfig(source_format=bigquery.SourceFormat.PARQUET, write_disposition="WRITE_APPEND")
    
    for idx, p_file in enumerate(parquet_files, 1):
        ticker = os.path.basename(p_file).replace(".parquet", "")
        print(f"[{idx}/{len(parquet_files)}] Streaming {ticker} -> {temp_ref}")
        with open(p_file, "rb") as source_file:
            job = client.load_table_from_file(source_file, temp_ref, job_config=job_config)
            job.result()
            
    print(f"\n--- Phase 3: Migrating to MONTH-PARTITIONED Final Table ({dataset}) ---")
    query = f"""
        CREATE OR REPLACE TABLE `{final_ref}`
        PARTITION BY TIMESTAMP_TRUNC(timestamp, MONTH)
        CLUSTER BY ticker
        AS SELECT * FROM `{temp_ref}`
    """
    client.query(query).result()
    client.delete_table(temp_ref, not_found_ok=True)
    print(f"[SUCCESS] {dataset.upper()} completely staged into BigQuery!\n")

def main():
    client = bigquery.Client(project=PROJECT_ID)
    universe = get_full_universe(client)
    if not universe:
        return
        
    for dataset in ['liquidationSnapshot']:
        process_dataset(client, universe, dataset)

if __name__ == "__main__":
    main()
