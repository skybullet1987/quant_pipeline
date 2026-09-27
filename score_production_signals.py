import os
import pandas as pd
import numpy as np
from catboost import CatBoostClassifier
from google.cloud import bigquery

PROJECT_ID = "parnasa-498503"
MODEL_PATH = os.path.expanduser("~/quant_pipeline/models/artifacts/catboost_macro_interaction_v2.cbm")
EXCLUDE_TICKERS = ["PAXGUSD", "USDCUSD", "USDTUSD", "FDUSDUSD", "EURUSD", "TUSDUSD"]

FEATURE_COLS = [
    "candle_body_pct", "candle_upper_wick_pct", "candle_lower_wick_pct",
    "rank_mom_24h", "rank_mom_7d", "rank_mom_accel_24h",
    "rank_dist_to_120p_high", "rank_gk_vol_20p", "rank_vol_compression_ratio",
    "rank_relative_vol_120p", "macro_expansion_score", "expansion_quintile"
]

AUDIT_COLS = [
    "timestamp", "ticker", "close", "atr_20", "mom_24h", "dist_ema20_atr",
    "macro_expansion_score", "expansion_quintile", "p_long", "active_hurdle",
    "is_eligible", "execution_action"
]

def run_scoring():
    client = bigquery.Client(project=PROJECT_ID)
    
    print("[1/3] Fetching latest bar from fct_4h_features_production...")
    query = f"""
    SELECT *
    FROM `{PROJECT_ID}.market_data.fct_4h_features_production`
    WHERE timestamp = (
        SELECT MAX(timestamp) 
        FROM `{PROJECT_ID}.market_data.fct_4h_features_production`
    )
    """
    df_live = client.query(query).to_dataframe()
    if df_live.empty:
        print("ERROR: No data found.")
        return

    latest_ts = df_live["timestamp"].iloc[0]
    print(f"      Scoring {len(df_live)} assets for timestamp: {latest_ts}")

    df_live = df_live[~df_live["ticker"].isin(EXCLUDE_TICKERS)].copy()
    model = CatBoostClassifier()
    model.load_model(MODEL_PATH)

    df_features = df_live.dropna(subset=FEATURE_COLS).copy()
    df_features["p_long"] = model.predict_proba(df_features[FEATURE_COLS])[:, 1]

    # P95 Calibrated Dynamic Hurdles
    df_features["active_hurdle"] = np.where(
        df_features["expansion_quintile"] == 1, 0.4493,
        np.where(df_features["expansion_quintile"] == 5, 0.4893, 0.5500)
    )
    df_features["is_eligible"] = df_features["p_long"] >= df_features["active_hurdle"]
    df_features["execution_action"] = np.where(df_features["is_eligible"], "DISPATCH_TRADE", "PRESERVE_CASH")

    scored_df = df_features.sort_values("p_long", ascending=False).reset_index(drop=True)
    top_candidate = scored_df.iloc[0]

    print("\n[2/3] ================= TOP CROSS-SECTIONAL SETUP =================")
    print(f"Timestamp        : {top_candidate['timestamp']}")
    print(f"Regime Quintile  : Q{top_candidate['expansion_quintile']} (Macro Score: {top_candidate['macro_expansion_score']:.4f})")
    print(f"Top Asset        : {top_candidate['ticker']}")
    print(f"Predicted P(Long): {top_candidate['p_long']:.4f}")
    print(f"Active Hurdle    : {top_candidate['active_hurdle']:.4f}")
    print(f"Action Verdict   : {top_candidate['execution_action']}")

    print("\nTop 5 Candidates Ranking:")
    print(scored_df[["ticker", "expansion_quintile", "macro_expansion_score", "p_long", "active_hurdle", "is_eligible"]].head(5).to_string(index=False))

    print("\n[3/3] Writing audit records to fct_4h_model_signals...")
    dest_table = f"{PROJECT_ID}.market_data.fct_4h_model_signals"
    audit_df = scored_df[AUDIT_COLS].copy()
    
    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_APPEND",
        schema_update_options=[bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION],
        time_partitioning=bigquery.TimePartitioning(type_=bigquery.TimePartitioningType.DAY, field="timestamp")
    )
    client.load_table_from_dataframe(audit_df, dest_table, job_config=job_config).result()
    print("      Audit records successfully written.")

if __name__ == "__main__":
    run_scoring()
