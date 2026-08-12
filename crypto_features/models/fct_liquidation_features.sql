{{ config(
    materialized='view',
    partition_by={
      "field": "timestamp",
      "data_type": "timestamp",
      "granularity": "day"
    },
    cluster_by=["ticker"]
) }}

WITH spine_4h AS (
    SELECT 
        TIMESTAMP_SECONDS(DIV(UNIX_SECONDS(timestamp), 14400) * 14400) AS timestamp,
        ticker
    FROM {{ ref('stg_densified_ohlcv') }}
    GROUP BY 1, 2
),

synthetic_liq_agg AS (
    SELECT
        TIMESTAMP_SECONDS(DIV(UNIX_SECONDS(timestamp), 14400) * 14400) AS timestamp,
        UPPER(ticker) AS ticker,
        SUM(CASE WHEN cascade_type = 'LONG_FLUSH' THEN volume * close ELSE 0 END) AS long_liq_usd,
        SUM(CASE WHEN cascade_type = 'SHORT_SQUEEZE' THEN volume * close ELSE 0 END) AS short_liq_usd
    FROM `parnasa-498503.market_data.fct_synthetic_liquidations`
    WHERE timestamp IS NOT NULL
    GROUP BY 1, 2
),

joined AS (
    SELECT
        s.timestamp,
        s.ticker,
        COALESCE(l.long_liq_usd, 0.0) AS long_liq_usd,
        COALESCE(l.short_liq_usd, 0.0) AS short_liq_usd
    FROM spine_4h s
    LEFT JOIN synthetic_liq_agg l ON s.timestamp = l.timestamp AND s.ticker = l.ticker
),

rolling_metrics AS (
    SELECT
        timestamp,
        ticker,
        long_liq_usd,
        short_liq_usd,
        
        -- Total Liquidation Volume
        (long_liq_usd + short_liq_usd) AS total_liq_usd,
        
        -- Liquidation Imbalance Ratio [-1.0 = Short Squeeze, +1.0 = Long Flush]
        SAFE_DIVIDE(long_liq_usd - short_liq_usd, NULLIF(long_liq_usd + short_liq_usd, 0)) AS liq_imbalance_ratio,
        
        -- Liquidation Acceleration
        SAFE_DIVIDE(long_liq_usd, NULLIF(AVG(long_liq_usd) OVER (PARTITION BY ticker ORDER BY timestamp ROWS BETWEEN 6 PRECEDING AND 1 PRECEDING), 0)) AS long_liq_accel,
        SAFE_DIVIDE(short_liq_usd, NULLIF(AVG(short_liq_usd) OVER (PARTITION BY ticker ORDER BY timestamp ROWS BETWEEN 6 PRECEDING AND 1 PRECEDING), 0)) AS short_liq_accel,
        
        -- Ecosystem Cascade Rank
        PERCENT_RANK() OVER (PARTITION BY timestamp ORDER BY (long_liq_usd + short_liq_usd) ASC) AS rank_liq_intensity
    FROM joined
)

SELECT * FROM rolling_metrics
