import requests
import pandas as pd
from google.cloud import bigquery

PROJECT_ID = "parnasa-498503"

def main():
    print("Fetching live Max Leverage parameters from Hyperliquid API...")
    try:
        response = requests.post('https://api.hyperliquid.xyz/info', json={"type": "meta"})
        meta = response.json()
        hl_max_leverage = {asset['name']: asset['maxLeverage'] for asset in meta['universe']}
    except Exception as e:
        print(f"[ERROR] Failed to fetch Hyperliquid meta: {e}")
        return

    print("Fetching latest volatility metrics from BigQuery...")
    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        WITH latest_ts AS (SELECT MAX(timestamp) as max_ts FROM `{PROJECT_ID}.market_data.fct_4h_features_tbm`)
        SELECT ticker, close, atr_20
        FROM `{PROJECT_ID}.market_data.fct_4h_features_tbm`
        WHERE timestamp = (SELECT max_ts FROM latest_ts)
    """
    df = client.query(query).to_dataframe()
    df['ticker'] = df['ticker'].str.replace('USDT', '').str.replace('USD', '')
    
    results = []
    MAINTENANCE_MARGIN_BUFFER = 0.05 # Keep liquidation price 5% further away than the Stop Loss

    for _, row in df.iterrows():
        coin = row['ticker']
        close = row['close']
        atr = row['atr_20']
        
        if coin not in hl_max_leverage or close == 0:
            continue
            
        exchange_max_lev = hl_max_leverage[coin]
        
        # Calculate how far away the 1.5 ATR Stop Loss is in percentage terms
        sl_pct_distance = (1.5 * atr) / close
        
        # Calculate the mathematical maximum leverage before structural liquidation
        if sl_pct_distance > 0:
            math_max_lev = int((1.0 - MAINTENANCE_MARGIN_BUFFER) / sl_pct_distance)
        else:
            math_max_lev = exchange_max_lev
            
        # The applied leverage is the highest possible allowed by either the exchange or the math
        applied_leverage = min(exchange_max_lev, math_max_lev)
        # Ensure we don't drop below 1x
        applied_leverage = max(applied_leverage, 1)
        
        results.append({
            'Coin': coin,
            'SL Distance': f"{sl_pct_distance*100:.2f}%",
            'Exchange Max': f"{exchange_max_lev}x",
            'Strategy Max': f"{math_max_lev}x",
            'Applied Leverage': f"{applied_leverage}x"
        })

    results_df = pd.DataFrame(results).sort_values(by='Applied Leverage', ascending=False)
    
    print("\n--- DYNAMIC LEVERAGE TIERS ---")
    print(results_df.head(10).to_string(index=False))
    print("...")
    print(results_df.tail(10).to_string(index=False))
    print("\n==================================================")
    print("Notice how low-volatility coins get high leverage,")
    print("and high-volatility meme coins get safely capped.")

if __name__ == "__main__":
    main()
