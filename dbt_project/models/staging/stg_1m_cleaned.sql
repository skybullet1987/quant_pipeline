{{ config(materialized='view') }}

WITH rolling_stats AS (
    SELECT 
        timestamp,
        symbol,
        open,
        high,
        low,
        close,
        volume,
        open_interest,
        PERCENTILE_CONT(close, 0.5) OVER (PARTITION BY symbol ORDER BY timestamp ROWS BETWEEN 59 PRECEDING AND CURRENT ROW) AS rolling_median
    FROM {{ ref('stg_densified_ohlcv') }}
),

mad_calculation AS (
    SELECT 
        *,
        PERCENTILE_CONT(ABS(close - rolling_median), 0.5) OVER (PARTITION BY symbol ORDER BY timestamp ROWS BETWEEN 59 PRECEDING AND CURRENT ROW) AS rolling_mad
    FROM rolling_stats
)

SELECT 
    timestamp,
    symbol,
    open,
    LEAST(high, rolling_median + 4.5 * 1.4826 * NULLIF(rolling_mad, 0)) AS high,
    GREATEST(low, rolling_median - 4.5 * 1.4826 * NULLIF(rolling_mad, 0)) AS low,
    close,
    volume,
    open_interest
FROM mad_calculation;
