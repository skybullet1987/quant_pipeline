{{ config(
    materialized='table',
    partition_by={
      "field": "timestamp",
      "data_type": "timestamp",
      "granularity": "day"
    },
    cluster_by=["ticker"]
) }}

-- ============================================================================
-- STEP 1: Aggregate Native 1-Hour Bars into 4-Hour OHLCV Bars
-- ============================================================================
WITH raw_4h AS (
  SELECT
    TIMESTAMP_SECONDS(DIV(UNIX_SECONDS(timestamp), 14400) * 14400) AS timestamp,
    UPPER(ticker) AS ticker,
    ARRAY_AGG(open ORDER BY timestamp ASC LIMIT 1)[OFFSET(0)] AS open,
    MAX(high) AS high,
    MIN(low) AS low,
    ARRAY_AGG(close ORDER BY timestamp DESC LIMIT 1)[OFFSET(0)] AS close,
    SUM(volume) AS volume
  FROM {{ source('market_data', 'raw_1h_ohlcv') }}
  WHERE timestamp IS NOT NULL
  GROUP BY 1, 2
),

-- ============================================================================
-- STEP 2: Base Metrics, Returns & True Range
-- ============================================================================
bar_metrics AS (
  SELECT
    timestamp, ticker, open, high, low, close, volume,
    LOG(SAFE_DIVIDE(close, LAG(close, 1) OVER w_asset)) AS ret_4h,
    IF(close > LAG(close, 1) OVER w_asset, 1, 0) AS is_pos_bar,
    
    AVG(close) OVER (PARTITION BY ticker ORDER BY timestamp ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS sma_20,
    AVG(close) OVER (PARTITION BY ticker ORDER BY timestamp ROWS BETWEEN 49 PRECEDING AND CURRENT ROW) AS sma_50,

    GREATEST(high - low, ABS(high - LAG(close, 1) OVER w_asset), ABS(low - LAG(close, 1) OVER w_asset)) AS true_range,
    SQRT(0.5 * POW(LOG(SAFE_DIVIDE(high, low)), 2) - (2 * LOG(2) - 1) * POW(LOG(SAFE_DIVIDE(close, open)), 2)) AS gk_vol_bar
  FROM raw_4h 
  WINDOW w_asset AS (PARTITION BY ticker ORDER BY timestamp)
),

-- ============================================================================
-- STEP 3: 20-Period Rolling Windows (Short-Term Base)
-- ============================================================================
rolling_20p AS (
  SELECT
    b.*,
    AVG(b.true_range) OVER w_20 AS atr_20,
    SQRT(AVG(POW(b.gk_vol_bar, 2)) OVER w_20) AS gk_vol_20p,
    SUM(b.ret_4h) OVER w_20 AS mom_20p,
    SAFE_DIVIDE(AVG(b.ret_4h) OVER w_20, NULLIF(STDDEV(b.ret_4h) OVER w_20, 0)) AS rolling_sharpe_20p
  FROM bar_metrics b
  WINDOW w_20 AS (PARTITION BY b.ticker ORDER BY b.timestamp ROWS BETWEEN 19 PRECEDING AND CURRENT ROW)
),

-- ============================================================================
-- STEP 4: 120-Period Rolling Windows (Fixes Nested Analytic Error)
-- ============================================================================
rolling_120p AS (
  SELECT
    r20.*,
    SAFE_DIVIDE(r20.atr_20, r20.close) AS atr_pct_20,
    SQRT(AVG(POW(r20.gk_vol_bar, 2)) OVER w_120) AS gk_vol_120p,
    
    -- Volatility Compression: Minimum of the already calculated 20p GK Vol over 120 periods
    MIN(r20.gk_vol_20p) OVER w_120 AS min_gk_vol_20p_120p,

    -- Rolling Highs & Structure
    MAX(r20.high) OVER w_120 AS max_high_120p,
    IF(r20.close >= MAX(r20.high) OVER w_120, 1.0, 0.0) AS is_at_120p_high,
    
    SAFE_DIVIDE(r20.volume, NULLIF(AVG(r20.volume) OVER w_120, 0)) AS relative_vol_120p,
    SUM(r20.is_pos_bar) OVER w_6 AS pos_bar_count_6p,
    
    -- Momentum Baselines
    SUM(r20.ret_4h) OVER w_6 AS mom_24h,
    SUM(r20.ret_4h) OVER w_42 AS mom_7d
  FROM rolling_20p r20
  WINDOW 
    w_6 AS (PARTITION BY r20.ticker ORDER BY r20.timestamp ROWS BETWEEN 5 PRECEDING AND CURRENT ROW),
    w_42 AS (PARTITION BY r20.ticker ORDER BY r20.timestamp ROWS BETWEEN 41 PRECEDING AND CURRENT ROW),
    w_120 AS (PARTITION BY r20.ticker ORDER BY r20.timestamp ROWS BETWEEN 119 PRECEDING AND CURRENT ROW)
),

-- ============================================================================
-- STEP 5: Market Leadership & Cross-Sectional Macro Features
-- ============================================================================
macro_leadership AS (
  SELECT
    r.*,
    
    -- BTC Structural Trend State
    MAX(IF(r.ticker = 'BTCUSD', r.close, NULL)) OVER (PARTITION BY r.timestamp) AS btc_close,
    MAX(IF(r.ticker = 'BTCUSD', r.sma_50, NULL)) OVER (PARTITION BY r.timestamp) AS btc_sma50,
    
    -- Returns for Dominance & ETH/BTC Spreads
    MAX(IF(r.ticker = 'BTCUSD', r.mom_20p, NULL)) OVER (PARTITION BY r.timestamp) AS btc_ret_20p,
    MAX(IF(r.ticker = 'ETHUSD', r.mom_20p, NULL)) OVER (PARTITION BY r.timestamp) AS eth_ret_20p,
    AVG(r.mom_20p) OVER (PARTITION BY r.timestamp) AS market_avg_ret_20p,

    -- Breadth Metrics
    AVG(IF(r.close > r.sma_20, 1.0, 0.0)) OVER (PARTITION BY r.timestamp) AS market_breadth_sma20,
    AVG(r.is_at_120p_high) OVER (PARTITION BY r.timestamp) AS top_breakout_breadth
  FROM rolling_120p r
),

-- ============================================================================
-- STEP 6: Derived Features, Z-Scores, Geometry & Temporal Context
-- ============================================================================
derived_features AS (
  SELECT
    m.*,
    
    -- TEMPORAL & SESSION FEATURES
    CAST(EXTRACT(HOUR FROM m.timestamp) AS STRING) AS hour_of_day,
    CAST(EXTRACT(DAYOFWEEK FROM m.timestamp) AS STRING) AS day_of_week,
    IF(EXTRACT(DAYOFWEEK FROM m.timestamp) IN (1, 7), "1", "0") AS is_weekend,
    CASE 
      WHEN EXTRACT(HOUR FROM m.timestamp) BETWEEN 0 AND 7 THEN 'ASIA'
      WHEN EXTRACT(HOUR FROM m.timestamp) BETWEEN 8 AND 12 THEN 'EUROPE'
      WHEN EXTRACT(HOUR FROM m.timestamp) BETWEEN 13 AND 21 THEN 'US'
      ELSE 'US_ASIA_TRANSITION'
    END AS market_session,

    -- Explicit Leadership Indicators
    IF(m.btc_close > m.btc_sma50, "1", "0") AS btc_above_sma50,
    (m.eth_ret_20p - m.btc_ret_20p) AS eth_btc_spread_20p,
    (m.btc_ret_20p - m.market_avg_ret_20p) AS btc_dominance_spread,
    
    -- Volatility Term Structure & Compression
    SAFE_DIVIDE(m.gk_vol_20p, NULLIF(m.gk_vol_120p, 0)) AS vol_term_structure,
    SAFE_DIVIDE(m.gk_vol_20p - AVG(m.gk_vol_20p) OVER w_120, NULLIF(STDDEV(m.gk_vol_20p) OVER w_120, 0)) AS gk_vol_zscore_120,
    SAFE_DIVIDE(m.gk_vol_20p, NULLIF(m.min_gk_vol_20p_120p, 0)) AS vol_compression_ratio,

    -- Distance to Rolling High
    SAFE_DIVIDE(m.close - m.max_high_120p, NULLIF(m.max_high_120p, 0)) AS dist_to_120p_high,

    -- Momentum Acceleration (2nd Derivative & Ratio)
    m.mom_24h - LAG(m.mom_24h, 6) OVER (PARTITION BY m.ticker ORDER BY m.timestamp) AS mom_accel_24h,
    SAFE_DIVIDE(m.mom_24h, NULLIF(ABS(m.mom_7d), 0)) AS mom_ratio_24h_7d,

    -- Candle Geometry
    SAFE_DIVIDE(ABS(m.close - m.open), NULLIF(m.high - m.low, 0)) AS candle_body_pct,
    SAFE_DIVIDE(m.high - GREATEST(m.open, m.close), NULLIF(m.high - m.low, 0)) AS candle_upper_wick_pct,
    SAFE_DIVIDE(LEAST(m.open, m.close) - m.low, NULLIF(m.high - m.low, 0)) AS candle_lower_wick_pct
  FROM macro_leadership m
  WINDOW w_120 AS (PARTITION BY m.ticker ORDER BY m.timestamp ROWS BETWEEN 119 PRECEDING AND CURRENT ROW)
),

-- ============================================================================
-- STEP 7: Triple Barrier Method (1.5x ATR Symmetric Target)
-- ============================================================================
tbm_forward_window AS (
  SELECT
    d.*,
    d.close + (1.50 * d.atr_20) AS upper_barrier_price,
    d.close - (1.50 * d.atr_20) AS lower_barrier_price,
    ARRAY_AGG(STRUCT(high AS fwd_high, low AS fwd_low, close AS fwd_close)) OVER (
      PARTITION BY d.ticker ORDER BY d.timestamp ROWS BETWEEN 1 FOLLOWING AND 18 FOLLOWING
    ) AS fwd_bars
  FROM derived_features d
),

tbm_path_resolution AS (
  SELECT
    f.*,
    (
      SELECT AS STRUCT
        MIN(IF(fwd.fwd_high >= f.upper_barrier_price, idx, NULL)) AS upper_hit_idx,
        MIN(IF(fwd.fwd_low <= f.lower_barrier_price, idx, NULL)) AS lower_hit_idx,
        ARRAY_AGG(fwd.fwd_close ORDER BY idx DESC LIMIT 1)[OFFSET(0)] AS vertical_exit_close,
        COUNT(1) AS fwd_bar_count
      FROM UNNEST(f.fwd_bars) AS fwd WITH OFFSET idx
    ) AS barrier_res
  FROM tbm_forward_window f
),

tbm_labels AS (
  SELECT
    p.*,
    CASE
      WHEN p.barrier_res.fwd_bar_count < 18 THEN NULL 
      WHEN p.barrier_res.upper_hit_idx IS NOT NULL 
           AND (p.barrier_res.lower_hit_idx IS NULL OR p.barrier_res.upper_hit_idx < p.barrier_res.lower_hit_idx) THEN 1
      ELSE 0
    END AS target_tbm_upper_hit,
    SAFE_DIVIDE(p.barrier_res.vertical_exit_close - p.close, p.close) AS ret_72h_vertical
  FROM tbm_path_resolution p
),

-- ============================================================================
-- STEP 8: Cross-Sectional Ranking Engine
-- ============================================================================
ranked_features AS (
  SELECT
    timestamp, ticker, open, high, low, close, volume, atr_20, target_tbm_upper_hit, ret_72h_vertical,
    
    -- Absolute Temporal & Macro Categoricals
    hour_of_day,
    day_of_week,
    is_weekend,
    market_session,
    btc_above_sma50,
    
    -- Market Breadth & Structure
    market_breadth_sma20,
    top_breakout_breadth,
    pos_bar_count_6p,
    candle_body_pct, candle_upper_wick_pct, candle_lower_wick_pct,

    -- Cross-Sectional Percentile Ranks
    PERCENT_RANK() OVER (PARTITION BY timestamp ORDER BY eth_btc_spread_20p ASC) AS rank_eth_btc_spread_20p,
    PERCENT_RANK() OVER (PARTITION BY timestamp ORDER BY btc_dominance_spread ASC) AS rank_btc_dominance_spread,
    PERCENT_RANK() OVER (PARTITION BY timestamp ORDER BY gk_vol_20p ASC) AS rank_gk_vol_20p,
    PERCENT_RANK() OVER (PARTITION BY timestamp ORDER BY vol_term_structure ASC) AS rank_vol_term_structure,
    PERCENT_RANK() OVER (PARTITION BY timestamp ORDER BY gk_vol_zscore_120 ASC) AS rank_gk_vol_zscore,
    PERCENT_RANK() OVER (PARTITION BY timestamp ORDER BY vol_compression_ratio ASC) AS rank_vol_compression_ratio,
    PERCENT_RANK() OVER (PARTITION BY timestamp ORDER BY mom_24h ASC) AS rank_mom_24h,
    PERCENT_RANK() OVER (PARTITION BY timestamp ORDER BY mom_7d ASC) AS rank_mom_7d,
    PERCENT_RANK() OVER (PARTITION BY timestamp ORDER BY mom_accel_24h ASC) AS rank_mom_accel_24h,
    PERCENT_RANK() OVER (PARTITION BY timestamp ORDER BY mom_ratio_24h_7d ASC) AS rank_mom_ratio_24h_7d,
    PERCENT_RANK() OVER (PARTITION BY timestamp ORDER BY dist_to_120p_high ASC) AS rank_dist_to_120p_high,
    PERCENT_RANK() OVER (PARTITION BY timestamp ORDER BY relative_vol_120p ASC) AS rank_relative_vol_120p,
    PERCENT_RANK() OVER (PARTITION BY timestamp ORDER BY rolling_sharpe_20p ASC) AS rank_rolling_sharpe_20p,
    PERCENT_RANK() OVER (PARTITION BY timestamp ORDER BY atr_pct_20 ASC) AS rank_atr_pct_20
  FROM tbm_labels
)

SELECT * FROM ranked_features WHERE timestamp IS NOT NULL AND atr_20 IS NOT NULL
