{{ config(
    materialized='table',
    partition_by={
      "field": "timestamp",
      "data_type": "timestamp",
      "granularity": "day"
    },
    cluster_by=["ticker"]
) }}

WITH forecast_curve AS (
    -- Pull strictly from the causally backfilled TimesFM forecasts
    -- This completely eliminates the lookahead bias caused by 'output_historical_time_series => TRUE'
    SELECT 
        ticker,
        forecast_timestamp AS timestamp,
        forecast_value,
        prediction_interval_upper_bound - prediction_interval_lower_bound AS tfm_uncertainty
    FROM `parnasa-498503.market_data.fct_timesfm_forecasts`
),

transformed AS (
    SELECT
        timestamp,
        ticker,
        
        -- Feature 27 & 28: Forecast Returns (Using forecast_value, NOT actual time_series_data)
        SAFE_DIVIDE(LEAD(forecast_value, 6) OVER(PARTITION BY ticker ORDER BY timestamp) - forecast_value, forecast_value) AS tfm_ret_24h,
        SAFE_DIVIDE(LEAD(forecast_value, 18) OVER(PARTITION BY ticker ORDER BY timestamp) - forecast_value, forecast_value) AS tfm_ret_72h,
        
        -- Feature 29: Slope Acceleration
        SAFE_DIVIDE(LEAD(forecast_value, 6) OVER(PARTITION BY ticker ORDER BY timestamp) - LEAD(forecast_value, 1) OVER(PARTITION BY ticker ORDER BY timestamp), 20.0) AS tfm_slope,
        
        -- Feature 30: Uncertainty / Band Width
        tfm_uncertainty,
        
        -- Feature 31: Surprise Index (Forecasted trajectory vs. previous forecast)
        SAFE_DIVIDE(forecast_value - LAG(forecast_value, 6) OVER (PARTITION BY ticker ORDER BY timestamp), 
                    NULLIF(LAG(forecast_value, 6) OVER (PARTITION BY ticker ORDER BY timestamp), 0)) AS tfm_residual_24h,
                    
        -- Feature 32: Conviction Delta
        SAFE_DIVIDE(forecast_value - LAG(forecast_value, 1) OVER (PARTITION BY ticker ORDER BY timestamp), 
                    NULLIF(LAG(forecast_value, 1) OVER (PARTITION BY ticker ORDER BY timestamp), 0)) AS tfm_conviction_delta
                    
    FROM forecast_curve
)

SELECT * FROM transformed 
WHERE timestamp IS NOT NULL

QUALIFY ROW_NUMBER() OVER (PARTITION BY ticker, timestamp ORDER BY timestamp DESC) = 1
