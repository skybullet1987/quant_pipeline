{{ config(
    materialized='table',
    partition_by={
      "field": "timestamp",
      "data_type": "timestamp",
      "granularity": "day"
    },
    cluster_by=["ticker"]
) }}

WITH aggregated_4h AS (
    -- Downsample cleaned 1m bars to 4H for TimesFM context stability
    SELECT 
        TIMESTAMP_SECONDS(DIV(UNIX_SECONDS(timestamp), 14400) * 14400) AS timestamp,
        ticker,
        ARRAY_AGG(close ORDER BY timestamp DESC LIMIT 1)[OFFSET(0)] AS close
    FROM {{ ref('stg_1m_cleaned') }}
    WHERE timestamp IS NOT NULL
    GROUP BY 1, 2
),

timesfm_raw AS (
    -- Execute Zero-Shot TimesFM 2.5 Inference via BQML
    SELECT *
    FROM AI.FORECAST(
        (SELECT timestamp, ticker, close FROM aggregated_4h),
        data_col => 'close',
        timestamp_col => 'timestamp',
        model => 'TimesFM 2.5',
        id_cols => ['ticker'],
        horizon => 18,               -- 72 hours forward on 4H bars
        confidence_level => 0.80,
        output_historical_time_series => TRUE
    )
),

transformed AS (
    SELECT
        time_series_timestamp AS timestamp,
        ticker,
        
        -- Feature 27 & 28: Forecast Returns
        SAFE_DIVIDE(LEAD(time_series_data, 6) OVER(PARTITION BY ticker ORDER BY time_series_timestamp) - time_series_data, time_series_data) AS tfm_ret_24h,
        SAFE_DIVIDE(LEAD(time_series_data, 18) OVER(PARTITION BY ticker ORDER BY time_series_timestamp) - time_series_data, time_series_data) AS tfm_ret_72h,
        
        -- Feature 29: Slope Acceleration
        SAFE_DIVIDE(LEAD(time_series_data, 6) OVER(PARTITION BY ticker ORDER BY time_series_timestamp) - LEAD(time_series_data, 1) OVER(PARTITION BY ticker ORDER BY time_series_timestamp), 20.0) AS tfm_slope,
        
        -- Feature 30: Uncertainty / Band Width (CatBoost will handle NULLs on historical rows)
        prediction_interval_upper_bound - prediction_interval_lower_bound AS tfm_uncertainty,
        
        -- Feature 31: Surprise Index (Actual Price vs. What was forecast 24h ago)
        SAFE_DIVIDE(time_series_data - LAG(time_series_data, 6) OVER (PARTITION BY ticker ORDER BY time_series_timestamp), 
                    LAG(time_series_data, 6) OVER (PARTITION BY ticker ORDER BY time_series_timestamp)) AS tfm_residual_24h,
                    
        -- Feature 32: Conviction Delta
        SAFE_DIVIDE(time_series_data - LAG(time_series_data, 1) OVER (PARTITION BY ticker ORDER BY time_series_timestamp), 
                    LAG(time_series_data, 1) OVER (PARTITION BY ticker ORDER BY time_series_timestamp)) AS tfm_conviction_delta
                    
    FROM timesfm_raw
)

SELECT * FROM transformed 
WHERE timestamp IS NOT NULL
