{{ config(materialized='view') }}

WITH time_grid AS (
    SELECT 
        ts AS timestamp
    FROM 
        UNNEST(GENERATE_TIMESTAMP_ARRAY(
            (SELECT MIN(timestamp) FROM {{ source('raw_crypto', 'raw_1m_ohlcv') }}),
            (SELECT MAX(timestamp) FROM {{ source('raw_crypto', 'raw_1m_ohlcv') }}),
            INTERVAL 1 MINUTE
        )) AS ts
),

assets AS (
    SELECT DISTINCT symbol FROM {{ source('raw_crypto', 'raw_1m_ohlcv') }}
),

cartesian_grid AS (
    SELECT 
        g.timestamp,
        a.symbol
    FROM time_grid g
    CROSS JOIN assets a
),

merged_ohlcv AS (
    SELECT 
        cg.timestamp,
        cg.symbol,
        r.open,
        r.high,
        r.low,
        r.close,
        COALESCE(r.volume, 0.0) AS volume,
        r.open_interest
    FROM cartesian_grid cg
    LEFT JOIN {{ source('raw_crypto', 'raw_1m_ohlcv') }} r
        ON cg.timestamp = r.timestamp AND cg.symbol = r.symbol
)

SELECT 
    timestamp,
    symbol,
    LAST_VALUE(open IGNORE NULLS) OVER (PARTITION BY symbol ORDER BY timestamp ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS open,
    LAST_VALUE(high IGNORE NULLS) OVER (PARTITION BY symbol ORDER BY timestamp ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS high,
    LAST_VALUE(low IGNORE NULLS) OVER (PARTITION BY symbol ORDER BY timestamp ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS low,
    LAST_VALUE(close IGNORE NULLS) OVER (PARTITION BY symbol ORDER BY timestamp ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS close,
    volume,
    LAST_VALUE(open_interest IGNORE NULLS) OVER (PARTITION BY symbol ORDER BY timestamp ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS open_interest
FROM merged_ohlcv;
