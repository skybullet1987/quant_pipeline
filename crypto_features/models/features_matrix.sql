WITH step_1_minute_returns AS (
  SELECT
    timestamp,
    ticker,
    close,
    -- Calculate the 1-minute backward log return for the volatility calculation
    LOG(close / LAG(close, 1) OVER (PARTITION BY ticker ORDER BY timestamp)) as backward_return_1m,
    
    -- Calculate 15-minute backward return for the momentum alpha
    LOG(close / LAG(close, 15) OVER (PARTITION BY ticker ORDER BY timestamp)) as backward_return_15m,
    
    -- Target Variable: Forward 15-minute return (strictly shifted to T-15)
    LOG(LEAD(close, 15) OVER (PARTITION BY ticker ORDER BY timestamp) / close) as target_forward_return_15m
  FROM {{ source('market_data', 'raw_ohlcv') }}
),

step_2_rolling_vol AS (
  SELECT
    timestamp,
    ticker,
    target_forward_return_15m,
    backward_return_15m,
    -- Now calculate the 60-minute rolling volatility on the pre-calculated 1m return
    STDDEV(backward_return_1m) OVER (PARTITION BY ticker ORDER BY timestamp ROWS BETWEEN 60 PRECEDING AND CURRENT ROW) as realized_vol_60m
  FROM step_1_minute_returns
),

normalized_features AS (
  SELECT
    timestamp,
    ticker,
    target_forward_return_15m,
    -- Volatility Normalization: Strip out absolute variance bias
    SAFE_DIVIDE(backward_return_15m, realized_vol_60m) as vol_norm_momentum_15m
  FROM step_2_rolling_vol
  WHERE realized_vol_60m IS NOT NULL 
    AND realized_vol_60m > 0
)

SELECT
  timestamp,
  ticker,
  vol_norm_momentum_15m,
  target_forward_return_15m,
  -- Cross-Sectional Ranking: Rank tokens against each other per individual minute bar
  PERCENT_RANK() OVER (PARTITION BY timestamp ORDER BY vol_norm_momentum_15m DESC) as cross_sectional_momentum_rank
FROM normalized_features
