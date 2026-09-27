{{ config(
    materialized='table',
    partition_by={
      "field": "bucket_timestamp_utc",
      "data_type": "timestamp",
      "granularity": "month"
    },
    cluster_by=["symbol", "is_universe_eligible"]
) }}

WITH base_candles AS (
    SELECT
        symbol,
        TIMESTAMP_MILLIS(timestamp_ms) AS bucket_timestamp_utc,
        open,
        high,
        low,
        close,
        volume,
        quote_volume,
        trade_count,
        taker_buy_volume,
        SAFE_DIVIDE(taker_buy_volume, volume) AS taker_buy_ratio,
        SAFE_DIVIDE(close - open, open) AS log_ret_proxy
    FROM {{ source('warehouse_historical', 'stg_market_candles_1m_historical') }}
),

asset_listing_meta AS (
    SELECT
        symbol,
        MIN(bucket_timestamp_utc) AS first_listed_utc
    FROM base_candles
    GROUP BY symbol
),

enriched_universe AS (
    SELECT
        b.*,
        m.first_listed_utc,
        DATE_DIFF(DATE(b.bucket_timestamp_utc), DATE(m.first_listed_utc), DAY) AS asset_age_days,
        
        -- Lagged 4H Close (240 bars) for momentum
        LAG(b.close, 240) OVER (
            PARTITION BY b.symbol 
            ORDER BY b.bucket_timestamp_utc
        ) AS close_lag_240,

        -- Rolling 24h (1440-minute) Notional Volume
        SUM(b.quote_volume) OVER (
            PARTITION BY b.symbol 
            ORDER BY b.bucket_timestamp_utc 
            ROWS BETWEEN 1439 PRECEDING AND CURRENT ROW
        ) AS rolling_24h_volume_usd,
        
        -- Rolling 24h Realized Volatility
        STDDEV(b.log_ret_proxy) OVER (
            PARTITION BY b.symbol 
            ORDER BY b.bucket_timestamp_utc 
            ROWS BETWEEN 1439 PRECEDING AND CURRENT ROW
        ) AS rolling_24h_volatility
    FROM base_candles b
    JOIN asset_listing_meta m USING (symbol)
),

intermediate_metrics AS (
    SELECT
        *,
        SAFE_DIVIDE(close - close_lag_240, close_lag_240) AS return_4h,
        CASE 
            WHEN asset_age_days >= 3 AND rolling_24h_volume_usd >= 1000000.0 THEN TRUE 
            ELSE FALSE 
        END AS is_universe_eligible
    FROM enriched_universe
),

ranked_panel AS (
    SELECT
        *,
        -- Point-in-time Cross-Sectional Liquidity Rank
        PERCENT_RANK() OVER (
            PARTITION BY bucket_timestamp_utc 
            ORDER BY rolling_24h_volume_usd ASC
        ) AS cs_liquidity_percentile,
        
        -- Point-in-time Cross-Sectional Momentum Rank
        PERCENT_RANK() OVER (
            PARTITION BY bucket_timestamp_utc 
            ORDER BY return_4h ASC
        ) AS cs_momentum_4h_percentile
    FROM intermediate_metrics
)

SELECT * FROM ranked_panel
