{{ config(
    materialized='table',
    partition_by={
      "field": "timestamp",
      "data_type": "timestamp",
      "granularity": "month"
    }
) }}

WITH hourly_spine AS (
    SELECT timestamp 
    FROM UNNEST(GENERATE_TIMESTAMP_ARRAY('2021-07-01 00:00:00', CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)) AS timestamp
),

market_oi AS (
    SELECT 
        TIMESTAMP_TRUNC(timestamp, HOUR) AS hr,
        SUM(sum_open_interest_value) AS total_market_oi,
        AVG(sum_taker_long_short_vol_ratio) AS avg_taker_imbalance
    FROM {{ source('market_data', 'raw_open_interest') }}
    GROUP BY 1
),

market_funding AS (
    SELECT 
        TIMESTAMP_TRUNC(timestamp, HOUR) AS hr,
        AVG(funding_rate) AS avg_funding_rate,
        STDDEV(funding_rate) AS funding_dispersion
    FROM {{ source('market_data', 'raw_funding_rate') }}
    GROUP BY 1
),

stress_calculations AS (
    SELECT 
        s.timestamp,
        o.total_market_oi,
        o.avg_taker_imbalance,
        LAST_VALUE(f.avg_funding_rate IGNORE NULLS) OVER (ORDER BY s.timestamp) AS avg_funding_rate,
        LAST_VALUE(f.funding_dispersion IGNORE NULLS) OVER (ORDER BY s.timestamp) AS funding_dispersion
    FROM hourly_spine s
    LEFT JOIN market_oi o ON s.timestamp = o.hr
    LEFT JOIN market_funding f ON s.timestamp = f.hr
)

SELECT
    timestamp,
    total_market_oi,
    (total_market_oi - LAG(total_market_oi, 1) OVER (ORDER BY timestamp)) - 
    (LAG(total_market_oi, 1) OVER (ORDER BY timestamp) - LAG(total_market_oi, 2) OVER (ORDER BY timestamp)) AS oi_acceleration,
    avg_taker_imbalance,
    avg_funding_rate,
    funding_dispersion
FROM stress_calculations
