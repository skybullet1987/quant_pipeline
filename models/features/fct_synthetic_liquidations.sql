{{ config(
    materialized='table',
    partition_by={
      "field": "timestamp",
      "data_type": "timestamp",
      "granularity": "month"
    },
    cluster_by=["ticker"]
) }}

WITH ohlcv_base AS (
    SELECT
        timestamp,
        ticker,
        open,
        high,
        low,
        close,
        volume,
        SAFE_DIVIDE(high - low, open) AS wick_spread_pct,
        SAFE_DIVIDE(ABS(close - open), open) AS body_pct
    FROM {{ source('market_data', 'raw_1m_ohlcv_v1') }}
),

oi_base AS (
    SELECT
        timestamp,
        ticker,
        sum_open_interest_value,
        sum_open_interest_value - LAG(sum_open_interest_value, 1) OVER (PARTITION BY ticker ORDER BY timestamp) AS oi_change_value
    FROM {{ source('market_data', 'raw_open_interest') }}
),

joined AS (
    SELECT
        o.timestamp,
        o.ticker,
        o.open,
        o.high,
        o.low,
        o.close,
        o.volume,
        o.wick_spread_pct,
        o.body_pct,
        LAST_VALUE(i.sum_open_interest_value IGNORE NULLS) OVER (
            PARTITION BY o.ticker 
            ORDER BY o.timestamp 
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS oi_value,
        LAST_VALUE(i.oi_change_value IGNORE NULLS) OVER (
            PARTITION BY o.ticker 
            ORDER BY o.timestamp 
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS oi_change_value
    FROM ohlcv_base o
    LEFT JOIN oi_base i ON o.timestamp = i.timestamp AND o.ticker = i.ticker
),

rolling_stats AS (
    SELECT
        *,
        AVG(volume) OVER (
            PARTITION BY ticker 
            ORDER BY timestamp 
            ROWS BETWEEN 60 PRECEDING AND 1 PRECEDING
        ) AS avg_vol_60m,
        STDDEV(volume) OVER (
            PARTITION BY ticker 
            ORDER BY timestamp 
            ROWS BETWEEN 60 PRECEDING AND 1 PRECEDING
        ) AS std_vol_60m
    FROM joined
)

SELECT
    timestamp,
    ticker,
    open,
    high,
    low,
    close,
    volume,
    oi_value,
    oi_change_value,
    
    CASE 
        WHEN volume > (avg_vol_60m + 3 * NULLIF(std_vol_60m, 0)) 
             AND oi_change_value < 0 
             AND wick_spread_pct > 0.015
        THEN 1 
        ELSE 0 
    END AS is_synthetic_liquidation,

    CASE 
        WHEN volume > (avg_vol_60m + 3 * NULLIF(std_vol_60m, 0)) AND oi_change_value < 0 AND wick_spread_pct > 0.015 AND close < open THEN 'LONG_FLUSH'
        WHEN volume > (avg_vol_60m + 3 * NULLIF(std_vol_60m, 0)) AND oi_change_value < 0 AND wick_spread_pct > 0.015 AND close > open THEN 'SHORT_SQUEEZE'
        ELSE 'NONE'
    END AS cascade_type

FROM rolling_stats
