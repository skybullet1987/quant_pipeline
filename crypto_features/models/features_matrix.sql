{{ config(
    materialized='table',
    partition_by={
      "field": "timestamp",
      "data_type": "timestamp",
      "granularity": "day"
    },
    cluster_by=["ticker"]
) }}

WITH raw_bars AS (
  SELECT
    timestamp,
    ticker,
    open,
    high,
    low,
    close,
    volume,
    LOG(SAFE_DIVIDE(close, LAG(close, 1) OVER w_asset)) AS ret_1m,
    close * volume AS dollar_volume
  FROM {{ source('market_data', 'raw_ohlcv') }}
  WINDOW w_asset AS (PARTITION BY ticker ORDER BY timestamp)
),

market_basket AS (
  SELECT
    timestamp,
    ticker,
    open, high, low, close, volume, ret_1m, dollar_volume,
    AVG(ret_1m) OVER (PARTITION BY timestamp) AS market_ret_1m
  FROM raw_bars
),

microstructure_and_vol AS (
  SELECT
    timestamp,
    ticker,
    close,
    volume,
    dollar_volume,
    
    (ret_1m - market_ret_1m) AS alpha_ret_1m,

    -- 1. Normalized Order Flow Imbalance (NOFI) Proxy
    SAFE_DIVIDE(
      SAFE_DIVIDE((close - low) - (high - close), NULLIF(high - low, 0)) * volume,
      NULLIF(AVG(volume) OVER w_rolling_60, 0)
    ) AS nofi_proxy,

    -- 2. Volatility: Garman-Klass (60-minute rolling)
    SQRT(AVG(
      0.5 * POW(LOG(SAFE_DIVIDE(high, low)), 2) - 
      (2 * LOG(2) - 1) * POW(LOG(SAFE_DIVIDE(close, open)), 2)
    ) OVER w_rolling_60) AS garman_klass_vol_60m,

    -- 3. Volatility Term Structure Ratio (15m Vol / 240m Vol)
    SAFE_DIVIDE(
      SQRT(AVG(0.5 * POW(LOG(SAFE_DIVIDE(high, low)), 2) - (2 * LOG(2) - 1) * POW(LOG(SAFE_DIVIDE(close, open)), 2)) OVER w_rolling_15),
      NULLIF(SQRT(AVG(0.5 * POW(LOG(SAFE_DIVIDE(high, low)), 2) - (2 * LOG(2) - 1) * POW(LOG(SAFE_DIVIDE(close, open)), 2)) OVER w_rolling_240), 0)
    ) AS vol_term_structure,

    -- 4. VWAP Deviations (60m)
    SAFE_DIVIDE(
      close - (SUM(dollar_volume) OVER w_rolling_60 / NULLIF(SUM(volume) OVER w_rolling_60, 0)),
      NULLIF(SUM(dollar_volume) OVER w_rolling_60 / NULLIF(SUM(volume) OVER w_rolling_60, 0), 0)
    ) AS vwap_dev_60m,

    -- 5. Multi-Horizon Idiosyncratic Momentum
    SUM(ret_1m - market_ret_1m) OVER w_rolling_15 AS alpha_mom_15m,
    SUM(ret_1m - market_ret_1m) OVER w_rolling_60 AS alpha_mom_60m,

    -- Forward 60m High/Low path for Triple-Barrier Target
    MAX(high) OVER w_forward_60 AS future_max_60m,
    MIN(low) OVER w_forward_60 AS future_min_60m,
    
    -- Continuous 60-minute forward close price for continuous PnL
    LEAD(close, 60) OVER (PARTITION BY ticker ORDER BY timestamp) AS future_close_60m

  FROM market_basket
  WINDOW 
    w_rolling_15 AS (PARTITION BY ticker ORDER BY timestamp ROWS BETWEEN 14 PRECEDING AND CURRENT ROW),
    w_rolling_60 AS (PARTITION BY ticker ORDER BY timestamp ROWS BETWEEN 59 PRECEDING AND CURRENT ROW),
    w_rolling_240 AS (PARTITION BY ticker ORDER BY timestamp ROWS BETWEEN 239 PRECEDING AND CURRENT ROW),
    w_forward_60 AS (PARTITION BY ticker ORDER BY timestamp ROWS BETWEEN 1 FOLLOWING AND 60 FOLLOWING)
),

ranked_features AS (
  SELECT
    timestamp,
    ticker,
    close,
    garman_klass_vol_60m,

    -- Time Categoricals
    EXTRACT(HOUR FROM timestamp) AS hour_of_day,
    EXTRACT(DAYOFWEEK FROM timestamp) AS day_of_week,
    IF(EXTRACT(DAYOFWEEK FROM timestamp) IN (1, 7), 1, 0) AS is_weekend,

    -- Cross-Sectional Rank Normalization (PERCENT_RANK per timestamp)
    PERCENT_RANK() OVER (PARTITION BY timestamp ORDER BY nofi_proxy ASC) AS rank_nofi,
    PERCENT_RANK() OVER (PARTITION BY timestamp ORDER BY garman_klass_vol_60m ASC) AS rank_gk_vol,
    PERCENT_RANK() OVER (PARTITION BY timestamp ORDER BY vol_term_structure ASC) AS rank_vol_term_structure,
    PERCENT_RANK() OVER (PARTITION BY timestamp ORDER BY vwap_dev_60m ASC) AS rank_vwap_dev_60m,
    PERCENT_RANK() OVER (PARTITION BY timestamp ORDER BY alpha_mom_15m ASC) AS rank_alpha_mom_15m,
    PERCENT_RANK() OVER (PARTITION BY timestamp ORDER BY alpha_mom_60m ASC) AS rank_alpha_mom_60m,

    -- Dynamic Triple Barrier Labeling: Upper barrier clamped to minimum +2.0%
    CASE 
      WHEN future_max_60m >= close * (1.0 + GREATEST(0.020, 2.0 * COALESCE(garman_klass_vol_60m, 0.01)))
       AND future_min_60m > close * (1.0 - 1.0 * COALESCE(garman_klass_vol_60m, 0.01)) THEN 1
      ELSE 0
    END AS target_tp_hit,
    
    -- Calculate continuous percentage return
    SAFE_DIVIDE(future_close_60m - close, close) AS target_ret_60m

  FROM microstructure_and_vol
)

SELECT * FROM ranked_features
WHERE timestamp IS NOT NULL
