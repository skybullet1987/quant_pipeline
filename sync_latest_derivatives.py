import time
import requests
import datetime
import pandas as pd
from google.cloud import bigquery
from concurrent.futures import ThreadPoolExecutor, as_completed

PROJECT_ID = "parnasa-498503"
DATASET_ID = "market_data"

FUNDING_URL = "https://fapi.binance.com/fapi/v1/premiumIndex"
OI_HIST_URL = "https://fapi.binance.com/futures/data/openInterestHist"
TAKER_VOL_URL = "https://fapi.binance.com/futures/data/takerlongshortRatio"

def get_bq_universe(client):
    query = f"SELECT DISTINCT ticker FROM `{PROJECT_ID}.{DATASET_ID}.raw_1m_ohlcv`"
    df = client.query(query).to_dataframe()
    return [t.replace('USD', 'USDT') for t in df['ticker'].tolist()]

def fetch_funding_rates():
    try:
        res = requests.get(FUNDING_URL, timeout=5)
        if res.status_code == 200:
            df = pd.DataFrame(res.json())
            df = df[['symbol', 'lastFundingRate', 'time']]
            df.columns = ['symbol', 'funding_rate', 'timestamp']
            df['funding_rate'] = df['funding_rate'].astype(float)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
            return df
    except Exception as e:
        print(f"Funding rate fetch failed: {e}")
    return pd.DataFrame()

def fetch_asset_metrics(symbol, now_ms):
    params = {"symbol": symbol, "period": "5m", "limit": 1}
    try:
        oi_res = requests.get(OI_HIST_URL, params=params, timeout=5)
        oi_data = oi_res.json() if oi_res.status_code == 200 else []
        
        taker_res = requests.get(TAKER_VOL_URL, params=params, timeout=5)
        taker_data = taker_res.json() if taker_res.status_code == 200 else []
        
        if not oi_data or not taker_data:
            return None
            
        return {
            "timestamp": pd.to_datetime(now_ms, unit='ms', utc=True),
            "ticker": symbol.replace("USDT", "USD"),
            "sum_open_interest": float(oi_data[-1].get("sumOpenInterest", 0)),
            "sum_open_interest_value": float(oi_data[-1].get("sumOpenInterestValue", 0)),
            "sum_taker_long_short_vol_ratio": float(taker_data[-1].get("buySellRatio", 0)),
            "count_long_short_ratio": 1.0, 
            "sum_toptrader_long_short_ratio": 1.0 
        }
    except Exception:
        return None

def main():
    start_time = time.time()
    client = bigquery.Client(project=PROJECT_ID)
    
    universe = get_bq_universe(client)
    now_ms = int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000)
    
    print(f"Fetching Live Derivatives & Funding for {len(universe)} assets...")
    
    df_funding = fetch_funding_rates()
    if not df_funding.empty:
        df_funding = df_funding[df_funding['symbol'].isin(universe)].copy()
        df_funding['ticker'] = df_funding['symbol'].str.replace('USDT', 'USD')
        df_funding = df_funding[['timestamp', 'ticker', 'funding_rate']]
        job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
        client.load_table_from_dataframe(df_funding, f"{PROJECT_ID}.{DATASET_ID}.raw_funding_rate", job_config=job_config).result()

    metrics_rows = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_asset_metrics, sym, now_ms) for sym in universe]
        for future in as_completed(futures):
            res = future.result()
            if res:
                metrics_rows.append(res)
                
    if metrics_rows:
        df_metrics = pd.DataFrame(metrics_rows)
        job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
        client.load_table_from_dataframe(df_metrics, f"{PROJECT_ID}.{DATASET_ID}.raw_open_interest", job_config=job_config).result()
        
    print(f"[SUCCESS] Live derivatives synced in {time.time() - start_time:.2f}s!")

if __name__ == "__main__":
    main()
