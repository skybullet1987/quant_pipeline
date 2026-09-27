{{ config(
    materialized='table',
    partition_by={"field": "timestamp", "data_type": "timestamp", "granularity": "day"},
    cluster_by=["ticker"]
) }}

WITH base_candles AS (
    SELECT 
        timestamp,
        ticker,
        open,
        high,
        low,
        close,
        volume,
        atr_20,
        mom_24h,
        mom_7d,
        mom_accel_24h,
        dist_ema20_atr,
        bbw_pct_40,
        dist_to_120p_high,
        gk_vol_20p,
        vol_compression_ratio,
        relative_vol_120p,
        candle_body_pct,
        candle_upper_wick_pct,
        candle_lower_wick_pct,
        COALESCE(expected_sharpe_proxy, 0.0) AS expected_sharpe_proxy,
        COALESCE(forecast_momentum, 0.0) AS forecast_momentum
    FROM {{ ref('stg_hyperliquid_candles_4h') }}
),

cross_sectional_ranks AS (
    SELECT
        *,
        PERCENT_RANK() OVER(PARTITION BY timestamp ORDER BY mom_24h DESC) AS rank_mom_24h,
        PERCENT_RANK() OVER(PARTITION BY timestamp ORDER BY mom_7d DESC) AS rank_mom_7d,
        PERCENT_RANK() OVER(PARTITION BY timestamp ORDER BY mom_accel_24h DESC) AS rank_mom_accel_24h,
        PERCENT_RANK() OVER(PARTITION BY timestamp ORDER BY dist_to_120p_high DESC) AS rank_dist_to_120p_high,
        PERCENT_RANK() OVER(PARTITION BY timestamp ORDER BY gk_vol_20p DESC) AS rank_gk_vol_20p,
        PERCENT_RANK() OVER(PARTITION BY timestamp ORDER BY vol_compression_ratio DESC) AS rank_vol_compression_ratio,
        PERCENT_RANK() OVER(PARTITION BY timestamp ORDER BY relative_vol_120p DESC) AS rank_relative_vol_120p,
        CASE WHEN dist_ema20_atr >= 1.8 AND mom_24h > 0.03 THEN 1.0 ELSE 0.0 END AS is_expanding
    FROM base_candles
),

bar_macro_aggregates AS (
    SELECT
        timestamp,
        COUNT(DISTINCT ticker) AS active_universe,
        AVG(CASE WHEN dist_ema20_atr > 0.0 THEN 1.0 ELSE 0.0 END) AS cross_breadth_sma20,
        AVG(is_expanding) AS cross_breakout_breadth,
        AVG(rank_mom_24h) AS cross_mom_avg,
        AVG(rank_vol_compression_ratio) AS cross_vol_comp_avg
    FROM cross_sectional_ranks
    GROUP BY timestamp
),

macro_time_series AS (
    SELECT
        timestamp,
        active_universe,
        cross_breadth_sma20,
        cross_breakout_breadth,
        cross_breakout_breadth - LAG(cross_breakout_breadth, 1) OVER(ORDER BY timestamp) AS breakout_delta_1,
        cross_breadth_sma20 - LAG(cross_breadth_sma20, 1) OVER(ORDER BY timestamp) AS breadth_delta_1,
        AVG(cross_vol_comp_avg) OVER(ORDER BY timestamp ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING) AS prior_comp_3b
    FROM bar_macro_aggregates
),

macro_expansion_scoring AS (
    SELECT
        timestamp,
        active_universe,
        ROUND(
            (0.35 * COALESCE(cross_breakout_breadth, 0)) + 
            (0.35 * GREATEST(0.0, COALESCE(breakout_delta_1, 0))) + 
            (0.15 * COALESCE(cross_breadth_sma20, 0)) + 
            (0.15 * COALESCE(prior_comp_3b, 0.5)),
            4
        ) AS macro_expansion_score
    FROM macro_time_series
),

macro_quintiles AS (
    SELECT
        timestamp,
        macro_expansion_score,
        NTILE(5) OVER(ORDER BY macro_expansion_score) AS expansion_quintile
    FROM macro_expansion_scoring
)

SELECT
    c.*,
    m.macro_expansion_score,
    q.expansion_quintile,
    CASE 
        WHEN q.expansion_quintile = 1 AND c.rank_dist_to_120p_high BETWEEN 0.40 AND 0.80 AND c.rank_vol_compression_ratio > 0.60 
        THEN 1 ELSE 0 
    END AS is_q1_coiling,
    CASE 
        WHEN q.expansion_quintile = 5 AND c.rank_mom_24h <= 0.50 AND c.rank_dist_to_120p_high < 0.70 
        THEN 1 ELSE 0 
    END AS is_q5_laggard
FROM cross_sectional_ranks c
JOIN macro_expansion_scoring m ON c.timestamp = m.timestamp
JOIN macro_quintiles q ON c.timestamp = q.timestamp
