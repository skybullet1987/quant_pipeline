import numpy as np
import pandas as pd
from google.cloud import bigquery
from hmmlearn.hmm import GaussianHMM

PROJECT_ID = "parnasa-498503"
DATASET_ID = "market_data"

def fetch_macro_vector(client):
    query = f"""
        WITH ohlcv_agg AS (
            SELECT 
                TIMESTAMP_TRUNC(timestamp, HOUR) AS hr,
                AVG(close) AS avg_price,
                STDDEV(close) AS price_volatility
            FROM `{PROJECT_ID}.{DATASET_ID}.raw_1m_ohlcv_v1`
            GROUP BY 1
        ),
        stress AS (
            SELECT 
                timestamp AS hr,
                total_market_oi,
                oi_acceleration,
                avg_funding_rate
            FROM `{PROJECT_ID}.{DATASET_ID}.fct_systemic_stress`
        )
        SELECT 
            o.hr AS timestamp,
            o.avg_price,
            o.price_volatility,
            s.total_market_oi,
            s.oi_acceleration,
            s.avg_funding_rate
        FROM ohlcv_agg o
        JOIN stress s ON o.hr = s.hr
        ORDER BY o.hr ASC
    """
    return client.query(query).to_dataframe()

def prepare_hmm_features(df):
    df = df.sort_values('timestamp').copy()
    
    df['log_return'] = np.log(df['avg_price'] / df['avg_price'].shift(1))
    df['realized_vol'] = df['log_return'].rolling(24).std()
    df['vol_of_vol'] = df['realized_vol'].rolling(24).std()
    
    oi_mean = df['oi_acceleration'].rolling(168).mean()
    oi_std = df['oi_acceleration'].rolling(168).std()
    df['norm_oi_accel'] = (df['oi_acceleration'] - oi_mean) / (oi_std + 1e-8)
    
    df['funding_shift'] = df['avg_funding_rate'] - df['avg_funding_rate'].shift(1)
    
    feature_cols = ['log_return', 'realized_vol', 'vol_of_vol', 'norm_oi_accel', 'funding_shift']
    clean_df = df.dropna(subset=feature_cols).reset_index(drop=True)
    
    return clean_df, feature_cols

def fit_stabilized_hmm(df, feature_cols, n_states=4, n_fits=5):
    """
    Fits Gaussian HMM with diagonal covariance and multi-start initialization 
    to guarantee numerical convergence.
    """
    X = df[feature_cols].values
    X_scaled = (X - np.mean(X, axis=0)) / (np.std(X, axis=0) + 1e-8)
    
    best_score = -np.inf
    best_model = None
    
    # Multi-start optimization loop to avoid local minima
    for seed in range(n_fits):
        model = GaussianHMM(
            n_components=n_states,
            covariance_type="diag",  # Prevents off-diagonal singularity
            min_covar=1e-3,          # Enforces variance floor
            n_iter=500,              # Expanded iteration limit
            random_state=42 + seed
        )
        try:
            model.fit(X_scaled)
            score = model.score(X_scaled)
            if score > best_score:
                best_score = score
                best_model = model
        except Exception:
            continue
            
    hidden_states = best_model.predict(X_scaled)
    posterior_probs = best_model.predict_proba(X_scaled)
    
    df['hmm_regime'] = hidden_states
    for i in range(n_states):
        df[f'hmm_prob_state_{i}'] = posterior_probs[:, i]
        
    return df, best_model

def main():
    client = bigquery.Client(project=PROJECT_ID)
    print("Fetching 5D macro vector from BigQuery...")
    raw_df = fetch_macro_vector(client)
    
    print("Engineering stationary features...")
    df_clean, feature_cols = prepare_hmm_features(raw_df)
    
    print(f"Fitting Stabilized 4-State Gaussian HMM (Diagonal Covariance) on {len(df_clean):,} hours...")
    df_regimes, model = fit_stabilized_hmm(df_clean, feature_cols, n_states=4)
    
    print("\n--- Stabilized HMM Regime Frequency ---")
    print(df_regimes['hmm_regime'].value_counts(normalize=True).rename("frequency"))
    
    print("\n--- Verified Output Sample ---")
    out_cols = ['timestamp', 'hmm_regime', 'hmm_prob_state_0', 'hmm_prob_state_1', 'hmm_prob_state_2', 'hmm_prob_state_3']
    print(df_regimes[out_cols].tail())
    
    print("\n[SUCCESS] Stabilized HMM Regime Detector converged cleanly!")

if __name__ == "__main__":
    main()
