import pandas as pd
from google.cloud import bigquery
from hmmlearn.hmm import GaussianHMM
import warnings

warnings.filterwarnings("ignore")
PROJECT_ID = "parnasa-498503"

def run_temporal_stability():
    client = bigquery.Client(project=PROJECT_ID)
    
    print("1. Pulling full sanitized dataset from BigQuery...")
    query = f"""
        SELECT timestamp, rank_gk_vol_zscore, rank_mom_7d, market_breadth_sma20, atr_20
        FROM `{PROJECT_ID}.market_data.fct_4h_features_tbm`
        ORDER BY timestamp ASC
    """
    df = client.query(query).to_dataframe(create_bqstorage_client=True)
    df['year'] = df['timestamp'].dt.year
    
    print("2. Isolating 2021-2023 Training Block and Fitting 3-State HMM...")
    train_df = df[df['year'].isin([2021, 2022, 2023])].copy()
    
    hmm_features = ['rank_gk_vol_zscore', 'rank_mom_7d', 'market_breadth_sma20']
    hmm = GaussianHMM(n_components=3, covariance_type="full", n_iter=500, random_state=42)
    hmm.fit(train_df[hmm_features].values)
    
    print("3. Predicting regimes across ALL years (2021-2026)...")
    df['hmm_regime'] = hmm.predict(df[hmm_features].values).astype(str)
    
    print("\n==========================================================================")
    print("               HMM TEMPORAL STABILITY TEST (3-STATE)                      ")
    print("==========================================================================")
    
    for regime in sorted(df['hmm_regime'].unique()):
        print(f"\n--- REGIME {regime} STABILITY ACROSS YEARS ---")
        reg_df = df[df['hmm_regime'] == regime]
        
        summary = reg_df.groupby('year').agg(
            Bar_Count=('atr_20', 'count'),
            Breadth_SMA20=('market_breadth_sma20', 'median'),
            Vol_ZScore=('rank_gk_vol_zscore', 'median'),
            Mom_7d=('rank_mom_7d', 'median'),
            Raw_ATR=('atr_20', 'median')
        ).round(4)
        
        print(summary.to_string())
    print("\n==========================================================================\n")

if __name__ == "__main__":
    run_temporal_stability()
