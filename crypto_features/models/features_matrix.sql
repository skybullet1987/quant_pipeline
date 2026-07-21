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
    timestamp, ticker, open, high, low, close, volume,
    LOG(SAFE_DIVIDE(close, LAG(close, 1) OVER w_asset)) AS ret_1m,
    close * volume AS dollar_volume,
    GREATEST(
        high - low,
        ABS(high - LAG(close, 1) OVER w_asset),
        ABS(low - LAG(close, 1) OVER w_asset)
    ) AS true_range
  FROM {{ ref('stg_densified_ohlcv') }}
  WINDOW w_asset AS (PARTITION BY ticker ORDER BY timestamp)
),

market_and_btc AS (
  SELECT *, 
    AVG(ret_1m) OVER (PARTITION BY timestamp) AS market_ret_1m,
    SUM(IF(ticker = 'BTCUSD', ret_1m, 0)) OVER (PARTITION BY timestamp) AS btc_ret_1m,
    
    SAFE_DIVIDE(ABS(close - open), NULLIF(high - low, 0)) AS candle_body_pct,
    SAFE_DIVIDE(high - GREATEST(open, close), NULLIF(high - low, 0)) AS candle_upper_wick_pct,
    SAFE_DIVIDE(LEAST(open, close) - low, NULLIF(high - low, 0)) AS candle_lower_wick_pct
  FROM raw_bars
),

microstructure_and_vol AS (
  SELECT *,
    (ret_1m - market_ret_1m) AS alpha_ret_1m,
    AVG(true_range) OVER w_rolling_60 AS atr_60m,

    SAFE_DIVIDE(
      SAFE_DIVIDE((close - low) - (high - close), NULLIF(high - low, 0)) * volume,
      NULLIF(AVG(volume) OVER w_rolling_60, 0)
    ) AS nofi_proxy,

    SAFE_DIVIDE(
      volume - AVG(volume) OVER w_rolling_60,
      NULLIF(STDDEV(volume) OVER w_rolling_60, 0)
    ) AS volume_zscore_60m,

    SAFE_DIVIDE(
      close - (SUM(dollar_volume) OVER w_rolling_60 / NULLIF(SUM(volume) OVER w_rolling_60, 0)),
      NULLIF(SUM(dollar_volume) OVER w_rolling_60 / NULLIF(SUM(volume) OVER w_rolling_60, 0), 0)
    ) AS vwap_dev_60m,

    SQRT(AVG(0.5 * POW(LOG(SAFE_DIVIDE(high, low)), 2) - (2 * LOG(2) - 1) * POW(LOG(SAFE_DIVIDE(close, open)), 2)) OVER w_rolling_60) AS garman_klass_vol_60m,

    SAFE_DIVIDE(
      SQRT(AVG(0.5 * POW(LOG(SAFE_DIVIDE(high, low)), 2) - (2 * LOG(2) - 1) * POW(LOG(SAFE_DIVIDE(close, open)), 2)) OVER w_rolling_15),
      NULLIF(SQRT(AVG(0.5 * POW(LOG(SAFE_DIVIDE(high, low)), 2) - (2 * LOG(2) - 1) * POW(LOG(SAFE_DIVIDE(close, open)), 2)) OVER w_rolling_240), 0)
    ) AS vol_term_structure,

    SUM(ret_1m - market_ret_1m) OVER w_rolling_15 AS alpha_mom_15m,
    SUM(ret_1m - market_ret_1m) OVER w_rolling_60 AS alpha_mom_60m,
    SUM(ret_1m) OVER w_rolling_60 - SUM(btc_ret_1m) OVER w_rolling_60 AS btc_beta_60m,

    SUM(btc_ret_1m) OVER w_rolling_1440 AS btc_ret_24h,
    SQRT(AVG(0.5 * POW(LOG(SAFE_DIVIDE(high, low)), 2) - (2 * LOG(2) - 1) * POW(LOG(SAFE_DIVIDE(close, open)), 2)) OVER w_rolling_1440) AS btc_vol_24h,

    MAX(high) OVER w_forward_240 AS max_240m,
    MIN(low) OVER w_forward_240 AS min_240m,
    LEAD(close, 240) OVER (PARTITION BY ticker ORDER BY timestamp) AS close_240m

  FROM market_and_btc
  WINDOW 
    w_rolling_15 AS (PARTITION BY ticker ORDER BY timestamp ROWS BETWEEN 14 PRECEDING AND CURRENT ROW),
    w_rolling_60 AS (PARTITION BY ticker ORDER BY timestamp ROWS BETWEEN 59 PRECEDING AND CURRENT ROW),
    w_rolling_240 AS (PARTITION BY ticker ORDER BY timestamp ROWS BETWEEN 239 PRECEDING AND CURRENT ROW),
    w_rolling_1440 AS (PARTITION BY ticker ORDER BY timestamp ROWS BETWEEN 1439 PRECEDING AND CURRENT ROW),
    w_forward_240 AS (PARTITION BY ticker ORDER BY timestamp ROWS BETWEEN 1 FOLLOWING AND 240 FOLLOWING)
),

ranked_features AS (
  SELECT
    timestamp, ticker, close, garman_klass_vol_60m, btc_ret_24h, btc_vol_24h,
    max_240m, min_240m,
    EXTRACT(HOUR FROM timestamp) AS hour_of_day,
    EXTRACT(DAYOFWEEK FROM timestamp) AS day_of_week,
    IF(EXTRACT(DAYOFWEEK FROM timestamp) IN (1, 7), 1, 0) AS is_weekend,
    
    candle_body_pct, candle_upper_wick_pct, candle_lower_wick_pct,

    PERCENT_RANK() OVER (PARTITION BY timestamp ORDER BY nofi_proxy ASC) AS rank_nofi,
    PERCENT_RANK() OVER (PARTITION BY timestamp ORDER BY volume_zscore_60m ASC) AS rank_volume_zscore,
    PERCENT_RANK() OVER (PARTITION BY timestamp ORDER BY garman_klass_vol_60m ASC) AS rank_gk_vol,
    PERCENT_RANK() OVER (PARTITION BY timestamp ORDER BY vol_term_structure ASC) AS rank_vol_term_structure,
    PERCENT_RANK() OVER (PARTITION BY timestamp ORDER BY vwap_dev_60m ASC) AS rank_vwap_dev_60m,
    PERCENT_RANK() OVER (PARTITION BY timestamp ORDER BY alpha_mom_15m ASC) AS rank_alpha_mom_15m,
    PERCENT_RANK() OVER (PARTITION BY timestamp ORDER BY alpha_mom_60m ASC) AS rank_alpha_mom_60m,
    PERCENT_RANK() OVER (PARTITION BY timestamp ORDER BY btc_beta_60m ASC) AS rank_btc_beta_60m,

    -- THE NEW HARD PERCENTAGE TARGET: +4.0% TP / -2.0% SL
    CASE 
      WHEN max_240m >= close * 1.040 AND min_240m > close * 0.980 THEN 1 
      ELSE 0 
    END AS target_hard_4_2,
    
    SAFE_DIVIDE(close_240m - close, close) AS ret_240m

  FROM microstructure_and_vol
)

SELECT * FROM ranked_features WHERE timestamp IS NOT NULL
