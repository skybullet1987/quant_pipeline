import os
import sqlite3
from datetime import datetime, timezone
from dotenv import load_dotenv
from google.cloud import bigquery
from hyperliquid.info import Info

load_dotenv('.env')
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "parnasa-498503")
DATASET_NAME = os.getenv("BQ_DATASET", "market_data")
API_URL = os.getenv("HYPERLIQUID_API_URL", "https://api.hyperliquid-testnet.xyz")

def run_audit():
    print("=" * 60)
    print(" 🛡️  QUANT PIPELINE PRE-FLIGHT AUDIT REPORT")
    print("=" * 60)

    checks_passed = 0
    total_checks = 5

    try:
        bq_client = bigquery.Client(project=PROJECT_ID)
    except Exception as e:
        print(f"[❌ FAIL] BigQuery Client Init Error: {e}")
        bq_client = None

    # --- CHECK 1: Raw Data Freshness (stg_ohlcv) ---
    if bq_client:
        try:
            q_raw = f"SELECT MAX(timestamp) as max_ts FROM `{PROJECT_ID}.{DATASET_NAME}.stg_ohlcv`"
            res_raw = list(bq_client.query(q_raw).result())[0]
            raw_ts = res_raw.max_ts
            diff_hours = (datetime.now(timezone.utc) - raw_ts).total_seconds() / 3600.0

            if diff_hours <= 3.0:
                print(f"[✅ PASS] 1. Raw Data Freshness: Latest bar at {raw_ts} ({diff_hours:.1f}h ago)")
                checks_passed += 1
            else:
                print(f"[❌ FAIL] 1. Raw Data Stale: Latest bar is {diff_hours:.1f}h old ({raw_ts})")
        except Exception as e:
            print(f"[❌ FAIL] 1. Raw Data Freshness Error: {e}")
    else:
        print("[❌ FAIL] 1. Raw Data Freshness: BigQuery client unavailable")

    # --- CHECK 2: Feature Matrix Integrity (fct_4h_features_tbm) ---
    if bq_client:
        try:
            q_feat = f"""
                SELECT MAX(timestamp) as max_ts, COUNT(*) as cnt 
                FROM `{PROJECT_ID}.{DATASET_NAME}.fct_4h_features_tbm`
                WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
            """
            res_feat = list(bq_client.query(q_feat).result())[0]
            feat_ts = res_feat.max_ts
            cnt = res_feat.cnt
            if cnt and cnt > 0:
                print(f"[✅ PASS] 2. Feature Matrix: {cnt} valid rows in last 24h (Max TS: {feat_ts})")
                checks_passed += 1
            else:
                print("[❌ FAIL] 2. Feature Matrix: No rows found in last 24h")
        except Exception as e:
            print(f"[❌ FAIL] 2. Feature Matrix Error: {e}")
    else:
        print("[❌ FAIL] 2. Feature Matrix: BigQuery client unavailable")

    # --- CHECK 3: ML Predictions / TimesFM Coverage ---
    if bq_client:
        try:
            q_pred = f"""
                SELECT COUNT(DISTINCT ticker) as cnt 
                FROM `{PROJECT_ID}.{DATASET_NAME}.fct_4h_features_tbm`
                WHERE timestamp = (SELECT MAX(timestamp) FROM `{PROJECT_ID}.{DATASET_NAME}.fct_4h_features_tbm`)
            """
            res_pred = list(bq_client.query(q_pred).result())[0]
            cnt = res_pred.cnt
            if cnt and cnt > 0:
                print(f"[✅ PASS] 3. ML Feature Coverage: {cnt} tickers active in latest feature slice")
                checks_passed += 1
            else:
                print("[❌ FAIL] 3. ML Feature Coverage: No active tickers in latest feature slice")
        except Exception as e:
            print(f"[❌ FAIL] 3. ML Predictions Error: {e}")
    else:
        print("[❌ FAIL] 3. ML Predictions: BigQuery client unavailable")

    # --- CHECK 4: Hyperliquid API Connectivity ---
    try:
        info = Info(API_URL, skip_ws=True)
        meta = info.meta()
        universe = meta.get("universe", [])
        env_label = "TESTNET" if "testnet" in API_URL else "MAINNET"
        if universe:
            print(f"[✅ PASS] 4. Hyperliquid API: Connected to {env_label} ({len(universe)} assets loaded)")
            checks_passed += 1
        else:
            print("[❌ FAIL] 4. Hyperliquid API: Empty universe returned")
    except Exception as e:
        print(f"[❌ FAIL] 4. Hyperliquid API Error: {e}")

    # --- CHECK 5: Local Telemetry Store ---
    try:
        db_file = "execution_telemetry.db" if os.path.exists("execution_telemetry.db") else "live_execution_telemetry.db"
        conn = sqlite3.connect(db_file)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM execution_telemetry")
        rec_cnt = cur.fetchone()[0]
        conn.close()
        print(f"[✅ PASS] 5. Local Telemetry Store: {db_file} is accessible ({rec_cnt} records logged)")
        checks_passed += 1
    except Exception as e:
        print(f"[❌ FAIL] 5. Local Telemetry Store Error: {e}")

    print("=" * 60)
    if checks_passed == total_checks:
        print(f"🚀 AUDIT SUCCESS ({checks_passed}/{total_checks}): All pre-flight checks passed.")
    else:
        print(f"⚠️ AUDIT WARNING ({checks_passed}/{total_checks}): Address failed items before launching.")
    print("=" * 60)

if __name__ == "__main__":
    run_audit()
