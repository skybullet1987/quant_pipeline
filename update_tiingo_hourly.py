import time
import requests
import pandas as pd
from google.cloud import bigquery
from datetime import datetime, timedelta, timezone

TIINGO_API_KEY = "895c0cc1087f3e2d1e60c9f3689903d08981cb26"
GCP_PROJECT = "parnasa-498503"
BQ_TABLE = f"{GCP_PROJECT}.market_data.raw_ohlcv"

COIN_UNIVERSE = [
    "btcusd", "ethusd", "solusd", "adausd", "xrpusd", "dotusd", "dogeusd", 
    "avaxusd", "linkusd", "maticusd", "ltcusd", "bchusd", "algousd", "xlmusd", 
    "atomusd", "uniusd", "filusd", "trxusd", "xtzusd", "eosusd", "aaveusd",
    "mkrusd", "snxusd", "compusd", "grtusd", "batusd", "enjusd", "manausd",
    "chzusd", "zrxusd", "crvusd", "sushiusd", "yfiusd", "1inchusd", "omgusd",
    "icxusd", "kavausd", "balusd", "bntusd", "renusd", "kncusd", "bandusd",
    "scusd", "storjusd", "oceanusd", "lrcusd", "keepusd", "oxtusd", "nmrusd",
    "dashusd", "zecusd", "xmrusd"
]

END_DATE = datetime.now(timezone.utc)
START_DATE = END_DATE - timedelta(hours=2)

def fetch_incremental():
    client = bigquery.Client(project=GCP_PROJECT)
    headers = {'Content-Type': 'application/json', 'Authorization': f'Token {TIINGO_API_KEY}'}

    for coin in COIN_UNIVERSE:
        url = "https://api.tiingo.com/tiingo/crypto/prices"
        params = {
            'tickers': coin,
            'startDate': START_DATE.strftime('%Y-%m-%d'),
            'endDate': END_DATE.strftime('%Y-%m-%d'),
            'resampleFreq': '1min',
            'exchanges': 'kraken'
        }
        try:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json()
                if data and 'priceData' in data[0]:
                    df = pd.DataFrame(data[0]['priceData']).rename(columns={'date': 'timestamp', 'tradesDone': 'trades'})
                    if not df.empty:
                        df['ticker'] = coin.upper()
                        df = df[['timestamp', 'ticker', 'open', 'high', 'low', 'close', 'volume']]
                        df['timestamp'] = pd.to_datetime(df['timestamp'])
                        job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
                        client.load_table_from_dataframe(df, BQ_TABLE, job_config=job_config).result()
        except Exception:
            pass
        time.sleep(1)

if __name__ == "__main__":
    fetch_incremental()
