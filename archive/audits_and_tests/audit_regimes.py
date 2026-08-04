import pandas as pd
from google.cloud import bigquery
import warnings

warnings.filterwarnings("ignore")
PROJECT_ID = "parnasa-498503"

def audit_hmm():
    client = bigquery.Client(project=PROJECT_ID)
    # Pulling the OOS block specifically
    query = f"""
        SELECT f.hmm_state, p.exit_reason, p.exact_gross_return
        FROM `{PROJECT_ID}.market_data.fct_4h_features_tbm` f
        INNER JOIN `{PROJECT_ID}.market_data.fct_exact_path_resolution` p
            ON f.timestamp = p.signal_time AND f.ticker = p.ticker
        WHERE f.target_tbm_upper_hit IS NOT NULL
        AND f.timestamp >= '2025-10-01'  -- OOS Block Approximation
    """
    try:
        df = client.query(query).to_dataframe(create_bqstorage_client=True)
        
        # Apply the friction and payout math to see EV per state
        WIN_FRICTION = 0.0047
        LOSS_FRICTION = 0.0062
        
        df['net_ret'] = df.apply(lambda row: row['exact_gross_return'] - WIN_FRICTION if row['exit_reason'] == 'TP_HIT' else row['exact_gross_return'] - LOSS_FRICTION, axis=1)
        df['is_win'] = (df['exit_reason'] == 'TP_HIT').astype(int)
        
        summary = df.groupby('hmm_state').agg(
            total_setups=('is_win', 'count'),
            win_rate=('is_win', 'mean'),
            avg_net_return=('net_ret', 'mean')
        )
        
        print("\n=== HMM REGIME OOS PERFORMANCE ===")
        print(summary)
    except Exception as e:
        print(f"Could not group by hmm_state: {e}")

if __name__ == "__main__":
    audit_hmm()
