import pandas as pd
from google.cloud import bigquery
import joblib
import warnings

warnings.filterwarnings("ignore")
PROJECT_ID = "parnasa-498503"
MODEL_DIR = "/home/skybullet1987/quant_pipeline/production_models"

def profile_hmm_physics():
    client = bigquery.Client(project=PROJECT_ID)
    
    print("\n==========================================================")
    print("1. Pulling clean in-sample data from BigQuery...")
    query = f"""
        SELECT rank_gk_vol_zscore, rank_mom_7d, market_breadth_sma20, atr_20
        FROM `{PROJECT_ID}.market_data.fct_4h_features_tbm`
        WHERE timestamp < '2025-10-01'
    """
    df = client.query(query).to_dataframe(create_bqstorage_client=True)
    
    print("2. Loading newly trained clean HMM...")
    try:
        hmm_model = joblib.load(f"{MODEL_DIR}/hmm_macro.pkl")
    except FileNotFoundError:
        print(f"Error: Could not find hmm_macro.pkl in {MODEL_DIR}. Check your model directory.")
        return

    hmm_features = ['rank_gk_vol_zscore', 'rank_mom_7d', 'market_breadth_sma20']
    
    print("3. Assigning market regimes...")
    df['hmm_regime'] = hmm_model.predict(df[hmm_features].values).astype(str)
    
    print("\n==========================================================")
    print("           HMM REGIME PHYSICS (IN-SAMPLE MEDIANS)         ")
    print("==========================================================")
    
    summary = df.groupby('hmm_regime').agg(
        Bar_Count=('atr_20', 'count'),
        Breadth_SMA20=('market_breadth_sma20', 'median'),
        Vol_ZScore=('rank_gk_vol_zscore', 'median'),
        Mom_7d=('rank_mom_7d', 'median'),
        Raw_ATR=('atr_20', 'median')
    ).round(4)
    
    print(summary.to_string())
    print("==========================================================\n")

if __name__ == "__main__":
    profile_hmm_physics()
