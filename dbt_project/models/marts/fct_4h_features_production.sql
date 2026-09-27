{{ config(
    materialized='table', 
    partition_by={"field": "timestamp_4h", "data_type": "timestamp"}
) }}

WITH aggregated_4h AS (
    SELECT 
        TIMESTAMP_TRUNC(timestamp, HOUR) - INTERVAL MOD(EXTRACT(HOUR FROM timestamp), 4) HOUR AS timestamp_4h,
        symbol,
        ARRAY_AGG(open ORDER BY timestamp ASC LIMIT 1)[OFFSET(0)] AS open_4h,
        MAX(high) AS high_4h,
        MIN(low) AS low_4h,
        ARRAY_AGG(close ORDER BY timestamp DESC LIMIT 1)[OFFSET(0)] AS close_4h,
        SUM(volume) AS volume_4h,
        ARRAY_AGG(open_interest ORDER BY timestamp DESC LIMIT 1)[OFFSET(0)] AS oi_4h
    FROM {{ ref('stg_1m_cleaned') }}
    GROUP BY 1, 2
),

log_returns AS (
    SELECT 
        *,
        LN(close_4h / NULLIF(LAG(close_4h, 1) OVER (PARTITION BY symbol ORDER BY timestamp_4h), 0)) AS ret_4h,
        0.5 * POW(LN(high_4h / NULLIF(low_4h, 0)), 2) - (2 * LN(2) - 1) * POW(LN(close_4h / NULLIF(open_4h, 0)), 2) AS gk_component
    FROM aggregated_4h
),

gk_vol_calc AS (
    SELECT 
        *,
        SQRT(NULLIF(AVG(gk_component) OVER (PARTITION BY symbol ORDER BY timestamp_4h ROWS BETWEEN 19 PRECEDING AND CURRENT ROW), 0)) AS sigma_gk_20p,
        LN(close_4h / NULLIF(LAG(close_4h, 6) OVER (PARTITION BY symbol ORDER BY timestamp_4h), 0)) AS mom_24h,
        LN(close_4h / NULLIF(LAG(close_4h, 12) OVER (PARTITION BY symbol ORDER BY timestamp_4h), 0)) AS mom_48h
    FROM log_returns
),

benchmarks AS (
    SELECT 
        timestamp_4h,
        MAX(CASE WHEN symbol = 'BTC' THEN ret_4h END) AS btc_ret,
        MAX(CASE WHEN symbol = 'ETH' THEN ret_4h END) AS eth_ret
    FROM log_returns
    GROUP BY timestamp_4h
),

joined_features AS (
    SELECT 
        g.*,
        b.btc_ret,
        b.eth_ret,
        g.mom_24h - LAG(g.mom_24h, 6) OVER (PARTITION BY g.symbol ORDER BY g.timestamp_4h) AS mom_acc,
        g.sigma_gk_20p / NULLIF(MIN(g.sigma_gk_20p) OVER (PARTITION BY g.symbol ORDER BY g.timestamp_4h ROWS BETWEEN 119 PRECEDING AND CURRENT ROW) + 1e-6, 0) AS vcr_20_120
    FROM gk_vol_calc g
    INNER JOIN benchmarks b ON g.timestamp_4h = b.timestamp_4h
)

SELECT 
    timestamp_4h,
    symbol,
    open_4h,
    high_4h,
    low_4h,
    close_4h,
    volume_4h,
    oi_4h,
    ret_4h,
    btc_ret,
    eth_ret,
    sigma_gk_20p,
    vcr_20_120,
    mom_24h,
    mom_48h,
    mom_acc
FROM joined_features;
