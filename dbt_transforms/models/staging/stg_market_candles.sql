{{ config(
    materialized='incremental',
    unique_key=['symbol', 'bucket_timestamp_utc'],
    partition_by={
      "field": "bucket_timestamp_utc",
      "data_type": "timestamp",
      "granularity": "day"
    },
    cluster_by=["symbol"]
) }}

WITH raw_trades AS (
    SELECT
        TIMESTAMP_MILLIS(timestamp_ms) AS trade_time,
        symbol,
        side,
        CAST(price AS FLOAT64) AS price,
        CAST(size AS FLOAT64) AS size,
        CAST(price * size AS FLOAT64) AS notional
    FROM {{ source('hyperliquid_raw', 'trades') }}
    WHERE dqg_state = 'VALID'
    {% if is_incremental() %}
      AND timestamp_ms > (
          SELECT COALESCE(MAX(UNIX_MILLIS(bucket_timestamp_utc)), 0) 
          FROM {{ this }}
      )
    {% endif %}
),

bucketed_raw AS (
    SELECT
        symbol,
        TIMESTAMP_TRUNC(trade_time, MINUTE) AS bucket_timestamp_utc,
        trade_time,
        side,
        price,
        size,
        notional
    FROM raw_trades
),

bucketed_1m AS (
    SELECT
        symbol,
        bucket_timestamp_utc,
        ARRAY_AGG(price ORDER BY trade_time ASC LIMIT 1)[OFFSET(0)] AS open_price,
        MAX(price) AS high_price,
        MIN(price) AS low_price,
        ARRAY_AGG(price ORDER BY trade_time DESC LIMIT 1)[OFFSET(0)] AS close_price,
        SUM(size) AS volume,
        SUM(notional) AS quote_volume,
        SUM(CASE WHEN side = 'BUY' THEN size ELSE 0 END) AS buy_volume,
        SUM(CASE WHEN side = 'SELL' THEN size ELSE 0 END) AS sell_volume,
        COUNT(1) AS trade_count
    FROM bucketed_raw
    GROUP BY symbol, bucket_timestamp_utc
)

SELECT
    symbol,
    bucket_timestamp_utc,
    TIMESTAMP_ADD(bucket_timestamp_utc, INTERVAL 1 MINUTE) AS t_available,
    CAST(open_price AS FLOAT64) AS open,
    CAST(high_price AS FLOAT64) AS high,
    CAST(low_price AS FLOAT64) AS low,
    CAST(close_price AS FLOAT64) AS close,
    CAST(volume AS FLOAT64) AS volume,
    CAST(quote_volume AS FLOAT64) AS quote_volume,
    CAST(buy_volume AS FLOAT64) AS buy_volume,
    CAST(sell_volume AS FLOAT64) AS sell_volume,
    CAST(trade_count AS INT64) AS trade_count,
    SAFE_DIVIDE(quote_volume, volume) AS vwap
FROM bucketed_1m
