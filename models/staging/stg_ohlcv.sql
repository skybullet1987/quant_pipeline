{{ config(materialized='view') }}

SELECT
    CAST(timestamp AS TIMESTAMP) AS timestamp,
    UPPER(TRIM(ticker)) AS ticker,
    CAST(open AS FLOAT64) AS open,
    CAST(high AS FLOAT64) AS high,
    CAST(low AS FLOAT64) AS low,
    CAST(close AS FLOAT64) AS close,
    CAST(volume AS FLOAT64) AS volume
FROM {{ source('market_data', 'raw_1m_ohlcv_v1') }}
WHERE timestamp IS NOT NULL 
  AND ticker IS NOT NULL
  AND volume >= 0
