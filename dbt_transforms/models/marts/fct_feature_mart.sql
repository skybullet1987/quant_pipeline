{{ config(
    materialized='incremental',
    unique_key=['symbol', 'bucket_timestamp_utc'],
    partition_by={
      "field": "bucket_timestamp_utc",
      "data_type": "timestamp",
      "granularity": "day"
    },
    cluster_by=["symbol"]
) }}

WITH base AS (
    SELECT
        c.symbol,
        c.bucket_timestamp_utc,
        c.t_available,
        c.open,
        c.high,
        c.low,
        c.close,
        c.volume,
        f.bar_delta,
        f.order_flow_imbalance,
        f.vwap_basis_bps,
        f.cvd_15m,
        f.cvd_60m,
        LN(c.close / LAG(c.close, 1) OVER (PARTITION BY c.symbol ORDER BY c.bucket_timestamp_utc)) AS log_ret_1m,
        GREATEST(
            c.high - c.low,
            ABS(c.high - LAG(c.close, 1) OVER (PARTITION BY c.symbol ORDER BY c.bucket_timestamp_utc)),
            ABS(c.low - LAG(c.close, 1) OVER (PARTITION BY c.symbol ORDER BY c.bucket_timestamp_utc))
        ) AS true_range
    FROM {{ ref('stg_market_candles') }} c
    JOIN {{ ref('int_order_flow_proxies') }} f
      ON c.symbol = f.symbol 
     AND c.bucket_timestamp_utc = f.bucket_timestamp_utc
    {% if is_incremental() %}
      WHERE c.bucket_timestamp_utc > (
          SELECT COALESCE(MAX(bucket_timestamp_utc), TIMESTAMP('1970-01-01')) 
          FROM {{ this }}
      )
    {% endif %}
),

feature_calcs AS (
    SELECT
        symbol,
        bucket_timestamp_utc,
        t_available,
        close,
        log_ret_1m,
        order_flow_imbalance,
        vwap_basis_bps,
        cvd_15m,
        cvd_60m,
        STDDEV(log_ret_1m) OVER (
            PARTITION BY symbol ORDER BY bucket_timestamp_utc ROWS BETWEEN 14 PRECEDING AND CURRENT ROW
        ) * SQRT(525600.0) AS rvol_15m,
        STDDEV(log_ret_1m) OVER (
            PARTITION BY symbol ORDER BY bucket_timestamp_utc ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
        ) * SQRT(525600.0) AS rvol_1h,
        STDDEV(log_ret_1m) OVER (
            PARTITION BY symbol ORDER BY bucket_timestamp_utc ROWS BETWEEN 239 PRECEDING AND CURRENT ROW
        ) * SQRT(525600.0) AS rvol_4h,
        AVG(true_range) OVER (
            PARTITION BY symbol ORDER BY bucket_timestamp_utc ROWS BETWEEN 13 PRECEDING AND CURRENT ROW
        ) / close AS natr_14m,
        (volume - AVG(volume) OVER (
            PARTITION BY symbol ORDER BY bucket_timestamp_utc ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
        )) / NULLIF(STDDEV(volume) OVER (
            PARTITION BY symbol ORDER BY bucket_timestamp_utc ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
        ), 0.0) AS volume_zscore_60m
    FROM base
)

SELECT
    symbol,
    bucket_timestamp_utc,
    t_available,
    CAST(close AS FLOAT64) AS close,
    CAST(log_ret_1m AS FLOAT64) AS log_ret_1m,
    CAST(order_flow_imbalance AS FLOAT64) AS order_flow_imbalance,
    CAST(vwap_basis_bps AS FLOAT64) AS vwap_basis_bps,
    CAST(cvd_15m AS FLOAT64) AS cvd_15m,
    CAST(cvd_60m AS FLOAT64) AS cvd_60m,
    CAST(rvol_15m AS FLOAT64) AS rvol_15m,
    CAST(rvol_1h AS FLOAT64) AS rvol_1h,
    CAST(rvol_4h AS FLOAT64) AS rvol_4h,
    CAST(natr_14m AS FLOAT64) AS natr_14m,
    CAST(volume_zscore_60m AS FLOAT64) AS volume_zscore_60m
FROM feature_calcs
