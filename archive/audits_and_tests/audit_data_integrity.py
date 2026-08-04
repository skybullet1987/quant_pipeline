import pandas as pd
from google.cloud import bigquery
import warnings

warnings.filterwarnings("ignore")
PROJECT_ID = "parnasa-498503"

def run_data_audit():
    client = bigquery.Client(project=PROJECT_ID)
    print("========================================================")
    print("        DATA INTEGRITY & ANOMALY DIAGNOSTIC AUDIT       ")
    print("========================================================\n")

    # 1. Staging Anomaly Rate Check
    query_anomalies = f"""
        SELECT 
            COUNT(1) AS total_bars,
            COUNTIF(is_price_anomaly) AS anomaly_bars,
            SAFE_DIVIDE(COUNTIF(is_price_anomaly), COUNT(1)) * 100 AS anomaly_pct
        FROM `{PROJECT_ID}.market_data.stg_1m_cleaned`
    """
    try:
        df_anom = client.query(query_anomalies).to_dataframe()
        tot = df_anom['total_bars'].iloc[0]
        anom = df_anom['anomaly_bars'].iloc[0]
        pct = df_anom['anomaly_pct'].iloc[0]
        print(f"[TEST 1] Adaptive Anomaly Detection (stg_1m_cleaned):")
        print(f"  - Total 1-Min Bars: {tot:,}")
        print(f"  - Flagged Anomalies: {anom:,} ({pct:.4f}%)\n")
    except Exception as e:
        print(f"[TEST 1 FAILED] Could not query stg_1m_cleaned: {e}\n")

    # 2. Path Resolution Integrity & Exit Reason Distribution
    query_path = f"""
        SELECT 
            exit_reason,
            COUNT(1) AS trade_count,
            AVG(exact_gross_return) AS avg_gross_return,
            COUNTIF(exit_time = signal_time) AS same_bar_collisions,
            COUNTIF(entry_price IS NULL OR exact_gross_return IS NULL) AS null_counts
        FROM `{PROJECT_ID}.market_data.fct_exact_path_resolution`
        GROUP BY exit_reason
    """
    try:
        df_path = client.query(query_path).to_dataframe()
        print(f"[TEST 2] Path Resolution Distribution (fct_exact_path_resolution):")
        print(df_path.to_string(index=False))
        print("")

        # Integrity Assertions
        tp_ret = df_path[df_path['exit_reason'] == 'TP_HIT']['avg_gross_return'].values
        sl_ret = df_path[df_path['exit_reason'] == 'SL_HIT']['avg_gross_return'].values

        if len(tp_ret) > 0 and len(sl_ret) > 0:
            diff = abs(abs(tp_ret[0]) - abs(sl_ret[0]))
            print(f"[TEST 3] Barrier Symmetry Check:")
            print(f"  - Avg TP Gross Return: {tp_ret[0]:.4%}")
            print(f"  - Avg SL Gross Return: {sl_ret[0]:.4%}")
            print(f"  - Absolute Delta: {diff:.4%}")
            if diff <= 0.0005:
                print("  -> PASSED: Barriers are strictly symmetric within 0.05% margin.\n")
            else:
                print("  -> WARNING: Barrier asymmetry detected!\n")

        total_trades = df_path['trade_count'].sum()
        collisions = df_path['same_bar_collisions'].sum()
        collision_pct = (collisions / total_trades) * 100 if total_trades > 0 else 0
        
        print(f"[TEST 4] Same-Bar Collision Check:")
        print(f"  - Collisions (exit_time == signal_time): {collisions:,} ({collision_pct:.2f}%)")
        if collision_pct < 1.0:
            print("  -> PASSED: Same-bar collisions are well under 1.0%.\n")
        else:
            print("  -> WARNING: High same-bar collision rate!\n")

    except Exception as e:
        print(f"[TEST 2-4 FAILED] Could not query fct_exact_path_resolution: {e}\n")

if __name__ == "__main__":
    run_data_audit()
