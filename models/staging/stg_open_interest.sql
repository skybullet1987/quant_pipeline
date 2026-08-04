{{ config(materialized='view') }}

SELECT
    CAST(timestamp AS TIMESTAMP) AS timestamp,
    UPPER(TRIM(ticker)) AS ticker,
    CAST(sum_open_interest AS FLOAT64) AS sum_open_interest,
    CAST(sum_open_interest_value AS FLOAT64) AS sum_open_interest_value,
    CAST(count_long_short_ratio AS FLOAT64) AS count_long_short_ratio,
    CAST(sum_toptrader_long_short_ratio AS FLOAT64) AS sum_toptrader_long_short_ratio,
    CAST(sum_taker_long_short_vol_ratio AS FLOAT64) AS sum_taker_long_short_vol_ratio
FROM {{ source('market_data', 'raw_open_interest') }}
WHERE timestamp IS NOT NULL 
  AND ticker IS NOT NULL
