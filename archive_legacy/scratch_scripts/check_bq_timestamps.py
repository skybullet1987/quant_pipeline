from google.cloud import bigquery

client = bigquery.Client(project='parnasa-498503')
tables = ['stg_ohlcv', 'fct_timesfm_features', 'fct_4h_features_tbm']

print("="*60)
print("📊 BIGQUERY MAXIMUM TIMESTAMPS BY TABLE")
print("="*60)

for table in tables:
    try:
        query = f"SELECT MAX(timestamp) as m FROM `parnasa-498503.market_data.{table}`"
        res = list(client.query(query).result())
        print(f"{table:<25} | Max TS: {res[0].m}")
    except Exception as e:
        print(f"{table:<25} | Error: {e}")

print("="*60)
