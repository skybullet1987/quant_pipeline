import pandas as pd
from google.cloud import bigquery
import warnings

warnings.filterwarnings("ignore")
PROJECT_ID = "parnasa-498503"

def hunt_regime_5_bug():
    client = bigquery.Client(project=PROJECT_ID)
    
    query = f"""
        SELECT 
            p.ticker, 
            p.signal_time, 
            p.entry_price, 
            p.target_price_3_atr, 
            p.stop_loss_1_5_atr, 
            p.exit_time, 
            p.exit_reason, 
            p.exact_gross_return, 
            p.minutes_in_trade
        FROM `{PROJECT_ID}.market_data.fct_exact_path_resolution` p
        ORDER BY p.exact_gross_return DESC
        LIMIT 20
    """
    try:
        df = client.query(query).to_dataframe(create_bqstorage_client=True)
        
        print("\n==========================================================================================")
        print("                        TOP 20 HIGHEST RETURN TRADES (ANOMALY HUNT)                       ")
        print("==========================================================================================")
        
        # Format the output so it doesn't wrap terribly in the terminal
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 1000)
        pd.set_option('display.float_format', lambda x: '%.4f' % x)
        
        print(df.to_string(index=False))
    except Exception as e:
        print(f"Error querying BigQuery: {e}")

if __name__ == "__main__":
    hunt_regime_5_bug()
