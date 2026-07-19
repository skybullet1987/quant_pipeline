import time
import requests
from datetime import datetime, timedelta
from google.cloud import bigquery

# --- CONFIGURATION ---
TIINGO_API_KEY = "895c0cc1087f3e2d1e60c9f3689903d08981cb26"
PROJECT_ID = "parnasa-498503"
FULL_TABLE_REF = f"{PROJECT_ID}.market_data.raw_ohlcv"
TICKERS = [
    "btcusd", "ethusd", "solusd", "xrpusd", "adausd", 
    "dogeusd", "linkusd", "dotusd", "maticusd", "avaxusd"
]

bq_client = bigquery.Client(project=PROJECT_ID)

# Dynamic 24-hour window
END_DATE = datetime.utcnow()
START_DATE = END_DATE - timedelta(days=1)

def run_daily_increment():
    start_str = START_DATE.strftime("%Y-%m-%d")
    end_str = END_DATE.strftime("%Y-%m-%d")
    
    print(f"\n--- Running Daily Increment: {start_str} to {end_str} ---")
    
    for ticker in TICKERS:
        url = "https://api.tiingo.com/tiingo/crypto/prices"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Token {TIINGO_API_KEY}"
        }
        params = {
            "tickers": ticker,
            "resampleFreq": "1min",
            "startDate": start_str,
            "endDate": end_str
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            if response.status_code == 200 and response.json():
                data = response.json()
                price_data = data[0].get("priceData", [])
                
                rows = [{
                    "timestamp": r["date"],
                    "ticker": ticker,
                    "open": float(r["open"]),
                    "high": float(r["high"]),
                    "low": float(r["low"]),
                    "close": float(r["close"]),
                    "volume": float(r["volume"]),
                    "volume_notional": float(r.get("volumeNotional")) if r.get("volumeNotional") is not None else None
                } for r in price_data]
                
                if rows:
                    bq_client.insert_rows_json(FULL_TABLE_REF, rows)
                    print(f"Inserted {len(rows)} daily rows for {ticker.upper()}.")
            time.sleep(0.5)
        except Exception as e:
            print(f"Error fetching {ticker}: {e}")

if __name__ == "__main__":
    run_daily_increment()
