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
  FROM {{ source('market_data', 'raw_ohlcv') }}
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

time_spine AS (
  SELECT timestamp
  FROM bounds,
  UNNEST(GENERATE_TIMESTAMP_ARRAY(min_ts, max_ts, INTERVAL 1 MINUTE)) AS timestamp
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
