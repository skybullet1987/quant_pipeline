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

WITH candle_base AS (
    SELECT
        symbol,
        bucket_timestamp_utc,
        t_available,
        close,
        vwap,
        volume,
        buy_volume,
        sell_volume,
        (buy_volume - sell_volume) AS bar_delta
    FROM {{ ref('stg_market_candles') }}
    {% if is_incremental() %}
      WHERE bucket_timestamp_utc > (
          SELECT COALESCE(MAX(bucket_timestamp_utc), TIMESTAMP('1970-01-01')) 
          FROM {{ this }}
      )
    {% endif %}
)

SELECT
    symbol,
    bucket_timestamp_utc,
    t_available,
    close,
    vwap,
    bar_delta,
    SAFE_DIVIDE(bar_delta, volume) AS order_flow_imbalance,
    SAFE_DIVIDE((close - vwap), vwap) AS vwap_basis_bps,
    SUM(bar_delta) OVER(
        PARTITION BY symbol 
        ORDER BY bucket_timestamp_utc 
        ROWS BETWEEN 14 PRECEDING AND CURRENT ROW
    ) AS cvd_15m,
    SUM(bar_delta) OVER(
        PARTITION BY symbol 
        ORDER BY bucket_timestamp_utc 
        ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
    ) AS cvd_60m
FROM candle_base
