{{ config(
    materialized='table',
    partition_by={
      "field": "timestamp",
      "data_type": "timestamp",
      "granularity": "day"
    },
    cluster_by=["ticker"]
) }}

WITH raw_data AS (
  SELECT 
    timestamp,
    UPPER(ticker) AS ticker,
    open, high, low, close, volume
  FROM {{ source('market_data', 'raw_1m_ohlcv') }}
  WHERE timestamp IS NOT NULL
),

ticker_stats AS (
  SELECT 
    ticker,
    COUNT(DISTINCT timestamp) AS actual_bars,
    TIMESTAMP_DIFF(MAX(timestamp), MIN(timestamp), MINUTE) AS total_expected_minutes
  FROM raw_data
  GROUP BY ticker
),

liquid_tickers AS (
  SELECT ticker
  FROM ticker_stats
  WHERE SAFE_DIVIDE(actual_bars, total_expected_minutes) >= 0.80
),

bounds AS (
  SELECT 
    MIN(timestamp) AS min_ts, 
    MAX(timestamp) AS max_ts 
  FROM raw_data
),

-- Bypassing BigQuery Array Limits via Cross-Joined Generators
date_spine AS (
  SELECT day
  FROM bounds,
  UNNEST(GENERATE_DATE_ARRAY(DATE(min_ts), DATE(max_ts), INTERVAL 1 DAY)) AS day
),

minute_spine AS (
  SELECT minute_offset
  FROM UNNEST(GENERATE_ARRAY(0, 1439)) AS minute_offset
),

time_spine AS (
  SELECT TIMESTAMP_ADD(CAST(d.day AS TIMESTAMP), INTERVAL m.minute_offset MINUTE) AS timestamp
  FROM date_spine d
  CROSS JOIN minute_spine m
  CROSS JOIN bounds b
  WHERE TIMESTAMP_ADD(CAST(d.day AS TIMESTAMP), INTERVAL m.minute_offset MINUTE) >= b.min_ts
    AND TIMESTAMP_ADD(CAST(d.day AS TIMESTAMP), INTERVAL m.minute_offset MINUTE) <= b.max_ts
),

full_grid AS (
  SELECT 
    s.timestamp,
    t.ticker
  FROM time_spine s
  CROSS JOIN liquid_tickers t
),

joined_bars AS (
  SELECT 
    g.timestamp,
    g.ticker,
    r.open,
    r.high,
    r.low,
    r.close,
    COALESCE(r.volume, 0.0) AS volume
  FROM full_grid g
  LEFT JOIN raw_data r
    ON g.timestamp = r.timestamp AND g.ticker = r.ticker
),

densified AS (
  SELECT 
    timestamp,
    ticker,
    volume,
    LAST_VALUE(close IGNORE NULLS) OVER w_locf AS close,
    COALESCE(open, LAST_VALUE(close IGNORE NULLS) OVER w_locf) AS open,
    COALESCE(high, LAST_VALUE(close IGNORE NULLS) OVER w_locf) AS high,
    COALESCE(low, LAST_VALUE(close IGNORE NULLS) OVER w_locf) AS low
  FROM joined_bars
  WINDOW w_locf AS (
    PARTITION BY ticker 
    ORDER BY timestamp 
    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
  )
)

SELECT * FROM densified WHERE close IS NOT NULL
