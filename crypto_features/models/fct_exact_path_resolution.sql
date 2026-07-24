{{ config(
    materialized='table',
    partition_by={
      "field": "signal_time",
      "data_type": "timestamp",
      "granularity": "day"
    },
    cluster_by=["ticker"]
) }}

WITH signals AS (
    SELECT 
        timestamp AS signal_time, 
        ticker, 
        close AS entry_price, 
        atr_20,
        close + (1.50 * atr_20) AS tp_price,
        close - (1.50 * atr_20) AS sl_price,
        TIMESTAMP_ADD(timestamp, INTERVAL 72 HOUR) AS timeout_time
    FROM {{ ref('fct_4h_features_tbm') }}
    WHERE target_tbm_upper_hit IS NOT NULL
),

forward_paths AS (
    SELECT 
        s.signal_time,
        s.ticker,
        s.entry_price,
        s.tp_price,
        s.sl_price,
        s.timeout_time,
        m.timestamp AS minute_time,
        m.high,
        m.low,
        m.close AS minute_close,
        CASE 
            WHEN m.high >= s.tp_price AND m.low <= s.sl_price THEN 'SIMULTANEOUS_BREACH'
            WHEN m.high >= s.tp_price THEN 'TP_HIT'
            WHEN m.low <= s.sl_price THEN 'SL_HIT'
            ELSE NULL 
        END AS breach_type
    FROM signals s
    INNER JOIN {{ ref('stg_densified_ohlcv') }} m
        ON s.ticker = m.ticker
        AND m.timestamp > s.signal_time
        AND m.timestamp <= s.timeout_time
),

first_breaches AS (
    SELECT 
        signal_time,
        ticker,
        MIN(minute_time) AS t1_star
    FROM forward_paths
    WHERE breach_type IS NOT NULL
    GROUP BY 1, 2
),

resolved_exits AS (
    SELECT 
        s.signal_time,
        s.ticker,
        s.entry_price,
        s.tp_price,
        s.sl_price,
        s.timeout_time,
        COALESCE(fb.t1_star, s.timeout_time) AS exit_time,
        
        CASE 
            WHEN fb.t1_star IS NULL THEN 'TIMEOUT'
            WHEN fp.breach_type = 'SIMULTANEOUS_BREACH' THEN 'SL_HIT'
            ELSE fp.breach_type 
        END AS exit_reason,
        
        CASE 
            WHEN fb.t1_star IS NULL THEN fp_timeout.minute_close
            WHEN fp.breach_type = 'TP_HIT' THEN s.tp_price
            WHEN fp.breach_type IN ('SL_HIT', 'SIMULTANEOUS_BREACH') THEN s.sl_price
        END AS exit_price
        
    FROM signals s
    LEFT JOIN first_breaches fb 
        ON s.signal_time = fb.signal_time AND s.ticker = fb.ticker
    LEFT JOIN forward_paths fp 
        ON s.signal_time = fp.signal_time AND s.ticker = fp.ticker AND fb.t1_star = fp.minute_time
    LEFT JOIN forward_paths fp_timeout
        ON s.signal_time = fp_timeout.signal_time AND s.ticker = fp_timeout.ticker AND s.timeout_time = fp_timeout.minute_time
)

SELECT 
    *,
    SAFE_DIVIDE(exit_price - entry_price, entry_price) AS exact_gross_return,
    TIMESTAMP_DIFF(exit_time, signal_time, MINUTE) AS minutes_in_trade
FROM resolved_exits
