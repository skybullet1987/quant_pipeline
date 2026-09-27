from google.cloud import bigquery

client = bigquery.Client(project='parnasa-498503')
tables = ['raw_1h_ohlcv', 'stg_densified_ohlcv', 'stg_ohlcv']

print("="*65)
print("📊 STAGING TABLE MAXIMUM TIMESTAMPS")
print("="*65)

for table in tables:
    try:
        query = f"SELECT MAX(timestamp) as m FROM `parnasa-498503.market_data.{table}`"
        res = list(client.query(query).result())
        print(f"{table:<25} | Max TS: {res[0].m}")
    except Exception as e:
        print(f"{table:<25} | Error: {e}")

print("="*65)
