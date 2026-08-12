import pandas as pd
from google.cloud import bigquery

PROJECT_ID = "parnasa-498503"

def main():
    client = bigquery.Client(project=PROJECT_ID)
    
    print("Executing BigQuery SQL Freshness Audit across all coins...\n")
    
    query = f"""
        WITH coin_stats AS (
            SELECT 
                ticker,
                MIN(timestamp) as earliest_ts,
                MAX(timestamp) as latest_ts,
                COUNT(*) as total_rows
            FROM `{PROJECT_ID}.market_data.fct_4h_features_tbm`
            GROUP BY ticker
        )
        SELECT 
            ticker,
            earliest_ts,
            latest_ts,
            total_rows,
            TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), latest_ts, HOUR) as lag_hours
        FROM coin_stats
        ORDER BY latest_ts ASC, ticker ASC
    """
    
    df = client.query(query).to_dataframe()
    
    total_coins = len(df)
    stale_coins = df[df['lag_hours'] > 6]
    fresh_coins = df[df['lag_hours'] <= 6]
    
    print("="*75)
    print("            PER-COIN FEATURE MATRIX FRESHNESS REPORT            ")
    print("="*75)
    print(f"Total Tickers in Feature Matrix: {total_coins} / 207")
    print(f"Fresh Coins (Lag <= 6h):         {len(fresh_coins)}")
    print(f"Stale/Lagging Coins (Lag > 6h):   {len(stale_coins)}")
    print("="*75)
    
    if not stale_coins.empty:
        print("\n[WARNING] LAGGING COINS DETECTED:")
        print(stale_coins[['ticker', 'latest_ts', 'lag_hours', 'total_rows']].to_string(index=False))
    else:
        print("\n[SUCCESS] ALL COINS ARE FULLY SYNCHRONIZED AND UP TO DATE!")
        print("\nSample Tickers Output (Top 10):")
        print(fresh_coins[['ticker', 'latest_ts', 'lag_hours', 'total_rows']].head(10).to_string(index=False))

if __name__ == "__main__":
    main()
