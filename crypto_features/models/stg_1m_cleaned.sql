{{ config(
    materialized='view',
    partition_by={
      "field": "timestamp",
      "data_type": "timestamp",
      "granularity": "day"
    },
    cluster_by=["ticker", "is_price_anomaly"]
) }}

WITH base_data AS (
    SELECT 
        timestamp,
        ticker,
        open, high, low, close, volume
    FROM {{ ref('stg_densified_ohlcv') }}
    WHERE timestamp IS NOT NULL
),

-- STEP 1: Generate rolling 60-bar window array for close prices
windowed_close AS (
    SELECT
        *,
        ARRAY_AGG(close) OVER (
            PARTITION BY ticker
            ORDER BY timestamp
            ROWS BETWEEN 60 PRECEDING AND 1 PRECEDING
        ) AS close_arr
    FROM base_data
),

-- STEP 2: Compute rolling median from the close array
rolling_stats AS (
    SELECT
        timestamp, ticker, open, high, low, close, volume,
        (
            SELECT APPROX_QUANTILES(val, 2)[OFFSET(1)]
            FROM UNNEST(close_arr) AS val
        ) AS rolling_median
    FROM windowed_close
),

-- STEP 3: Generate rolling 60-bar window array for absolute deviations
windowed_dev AS (
    SELECT
        *,
        ABS(close - rolling_median) AS absolute_deviation,
        ARRAY_AGG(ABS(close - rolling_median)) OVER (
            PARTITION BY ticker
            ORDER BY timestamp
            ROWS BETWEEN 60 PRECEDING AND 1 PRECEDING
        ) AS dev_arr
    FROM rolling_stats
),

-- STEP 4: Compute rolling MAD from the deviation array
mad_calc AS (
    SELECT
        timestamp, ticker, open, high, low, close, volume,
        rolling_median,
        absolute_deviation,
        (
            SELECT APPROX_QUANTILES(val, 2)[OFFSET(1)]
            FROM UNNEST(dev_arr) AS val
        ) AS rolling_mad
    FROM windowed_dev
),

-- STEP 5: Flag anomalies using adaptive bounds
anomaly_flagging AS (
    SELECT
        *,
        rolling_median + (15.0 * rolling_mad) AS upper_bound,
        rolling_median - (15.0 * rolling_mad) AS lower_bound,
        CASE
            WHEN rolling_mad = 0 THEN FALSE 
            WHEN close > (rolling_median + (15.0 * rolling_mad)) THEN TRUE
            WHEN close < (rolling_median - (15.0 * rolling_mad)) THEN TRUE
            ELSE FALSE
        END AS is_price_anomaly
    FROM mad_calc
),

-- STEP 6: Collapse anomalous bars to rolling median
repaired_data AS (
    SELECT
        timestamp,
        ticker,
        CASE WHEN is_price_anomaly THEN rolling_median ELSE open END AS open,
        CASE WHEN is_price_anomaly THEN rolling_median ELSE high END AS high,
        CASE WHEN is_price_anomaly THEN rolling_median ELSE low END AS low,
        CASE WHEN is_price_anomaly THEN rolling_median ELSE close END AS close,
        volume,
        is_price_anomaly,
        rolling_median,
        rolling_mad
    FROM anomaly_flagging
)

SELECT * FROM repaired_data
