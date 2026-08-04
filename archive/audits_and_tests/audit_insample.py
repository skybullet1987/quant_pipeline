import pandas as pd
from google.cloud import bigquery
import warnings

warnings.filterwarnings("ignore")
PROJECT_ID = "parnasa-498503"

def audit_in_sample():
    client = bigquery.Client(project=PROJECT_ID)
    
    # Notice the date: We are pulling the TRAINING data only
    query = f"""
        SELECT f.hmm_state, p.exit_reason, p.exact_gross_return
        FROM `{PROJECT_ID}.market_data.fct_4h_features_tbm` f
        INNER JOIN `{PROJECT_ID}.market_data.fct_exact_path_resolution` p
            ON f.timestamp = p.signal_time AND f.ticker = p.ticker
        WHERE f.target_tbm_upper_hit IS NOT NULL
        AND f.timestamp < '2025-10-01'  
    """
    try:
        df = client.query(query).to_dataframe(create_bqstorage_client=True)
        
        WIN_FRICTION = 0.0047
        LOSS_FRICTION = 0.0062
        
        df['net_ret'] = df.apply(lambda row: row['exact_gross_return'] - WIN_FRICTION if row['exit_reason'] == 'TP_HIT' else row['exact_gross_return'] - LOSS_FRICTION, axis=1)
        df['is_win'] = (df['exit_reason'] == 'TP_HIT').astype(int)
        
        summary = df.groupby('hmm_state').agg(
            Trades=('is_win', 'count'),
            Win_Rate=('is_win', lambda x: f"{x.mean():.2%}"),
            Avg_Net_Return=('net_ret', lambda x: f"{x.mean():.2%}")
        )
        
        print("\n=== IN-SAMPLE (2021-2025) REGIME PERFORMANCE ===")
        print(summary)
    except Exception as e:
        print(f"Could not group by hmm_state: {e}")

if __name__ == "__main__":
    audit_in_sample()
