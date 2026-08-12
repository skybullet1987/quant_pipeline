SELECT * FROM (
{{ config(
    materialized='table',
    partition_by={
      "field": "signal_time",
      "data_type": "timestamp",
      "granularity": "day"
    },
    cluster_by=["ticker", "exit_reason"]
) }}

WITH signals AS (
    SELECT 
        ticker,
        timestamp AS signal_time,
        close AS entry_price,
        atr_20,
        close + (1.5 * atr_20) AS target_price_1_5_atr,
        close - (1.5 * atr_20) AS stop_loss_1_5_atr,
        TIMESTAMP_ADD(timestamp, INTERVAL 72 HOUR) AS timeout_limit
    FROM {{ ref('fct_4h_features_tbm') }}
    WHERE atr_20 IS NOT NULL
),

path_mapping AS (
    SELECT 
        s.ticker,
        s.signal_time,
        s.entry_price,
        s.target_price_1_5_atr,
        s.stop_loss_1_5_atr,
        MIN(CASE WHEN m.high >= s.target_price_1_5_atr THEN m.timestamp END) AS tp_hit_time,
        MIN(CASE WHEN m.low <= s.stop_loss_1_5_atr THEN m.timestamp END) AS sl_hit_time,
        LOGICAL_OR(CASE WHEN m.high >= s.target_price_1_5_atr AND m.low <= s.stop_loss_1_5_atr AND m.is_price_anomaly THEN TRUE ELSE FALSE END) AS has_data_error,
        ARRAY_AGG(m.close ORDER BY m.timestamp DESC LIMIT 1)[OFFSET(0)] AS timeout_close_price
    FROM signals s
    INNER JOIN {{ ref('stg_1m_cleaned') }} m
        ON s.ticker = m.ticker
        AND m.timestamp > s.signal_time
        AND m.timestamp <= s.timeout_limit
    GROUP BY 1, 2, 3, 4, 5
),

final_resolution AS (
    SELECT
        ticker,
        signal_time,
        entry_price,
        target_price_1_5_atr,
        stop_loss_1_5_atr,
        tp_hit_time,
        sl_hit_time,
        timeout_close_price,
        CASE 
            WHEN has_data_error THEN 'DATA_ERROR'
            WHEN tp_hit_time IS NOT NULL AND (sl_hit_time IS NULL OR tp_hit_time < sl_hit_time) THEN 'TP_HIT'
            WHEN sl_hit_time IS NOT NULL AND (tp_hit_time IS NULL OR sl_hit_time < tp_hit_time) THEN 'SL_HIT'
            WHEN tp_hit_time IS NOT NULL AND sl_hit_time IS NOT NULL AND tp_hit_time = sl_hit_time THEN 'SL_HIT'
            ELSE 'TIMEOUT'
        END AS exit_reason,
        CASE 
            WHEN has_data_error THEN COALESCE(tp_hit_time, sl_hit_time)
            WHEN tp_hit_time IS NOT NULL AND (sl_hit_time IS NULL OR tp_hit_time < sl_hit_time) THEN tp_hit_time
            WHEN sl_hit_time IS NOT NULL AND (tp_hit_time IS NULL OR sl_hit_time < tp_hit_time) THEN sl_hit_time
            WHEN tp_hit_time IS NOT NULL AND sl_hit_time IS NOT NULL AND tp_hit_time = sl_hit_time THEN sl_hit_time
            ELSE TIMESTAMP_ADD(signal_time, INTERVAL 72 HOUR)
        END AS exit_time
    FROM path_mapping
)

SELECT 
    *,
    CASE 
        WHEN exit_reason = 'DATA_ERROR' THEN 0.0
        WHEN exit_reason = 'TP_HIT' THEN (target_price_1_5_atr - entry_price) / entry_price
        WHEN exit_reason = 'SL_HIT' THEN (stop_loss_1_5_atr - entry_price) / entry_price
        WHEN exit_reason = 'TIMEOUT' THEN (timeout_close_price - entry_price) / entry_price
        ELSE 0.0 
    END AS exact_gross_return,
    CASE WHEN exit_reason = 'TP_HIT' THEN 1 ELSE 0 END AS target_long,
    CASE WHEN exit_reason = 'SL_HIT' THEN 1 ELSE 0 END AS target_short,
    TIMESTAMP_DIFF(exit_time, signal_time, MINUTE) AS minutes_in_trade
FROM final_resolution

) AS base_query
WHERE entry_price > 0.000001
  AND stop_loss_1_5_atr > 0
  AND exact_gross_return BETWEEN -0.99 AND 2.0
  AND exit_reason != 'DATA_ERROR'
