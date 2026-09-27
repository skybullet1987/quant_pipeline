{{ config(materialized='view') }}

SELECT
    timestamp,
    ticker,
    open,
    high,
    low,
    close,
    volume
FROM `{{ target.project }}.market_data.raw_ohlcv`
