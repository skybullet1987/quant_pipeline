{{ config(materialized='view') }}

SELECT
    ticker,
    timestamp,
    open,
    high,
    low,
    close,
    volume
FROM {{ source('market_data', 'raw_1m_ohlcv') }}
WHERE timestamp IS NOT NULL
