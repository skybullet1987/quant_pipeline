#!/usr/bin/env python3
import json

CLEAN_FEATURES = [
    # 1. Macro & Breadth
    "market_breadth_sma20",
    "top_breakout_breadth",
    "btc_above_sma50",
    
    # 2. TimesFM Foundation
    "tfm_ret_24h",
    "tfm_ret_72h",
    "tfm_conviction_delta",
    "tfm_slope",
    "tfm_residual_24h",
    
    # 3. Volatility Compression & Structure
    "rank_vol_compression_ratio",
    "rank_vol_term_structure",
    "rank_dist_to_120p_high",
    "rank_atr_pct_20",
    "rank_gk_vol_20p",
    "rank_gk_vol_zscore",
    "rank_relative_vol_120p",
    
    # 4. Cross-Sectional Momentum
    "rank_mom_7d",
    "rank_mom_24h",
    "rank_mom_accel_24h",
    "rank_rolling_sharpe_20p",
    
    # 5. Price Microstructure & Session
    "candle_body_pct",
    "candle_upper_wick_pct",
    "candle_lower_wick_pct",
    "day_of_week",
    "hour_of_day",
    "ticker"
]

CATEGORICAL_FEATURES = [
    "ticker",
    "hour_of_day",
    "day_of_week",
    "btc_above_sma50"
]

schema = {
    "feature_names": CLEAN_FEATURES,
    "categorical_features": CATEGORICAL_FEATURES,
    "feature_count": len(CLEAN_FEATURES)
}

with open("production_models/feature_schema_clean.json", "w") as f:
    json.dump(schema, f, indent=2)

print(f"[SUCCESS] Saved clean schema with {len(CLEAN_FEATURES)} features to production_models/feature_schema_clean.json")
