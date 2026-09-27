import os
import pandas as pd
import numpy as np
from catboost import CatBoostClassifier, Pool
from google.cloud import bigquery

PROJECT_ID = "parnasa-498503"
MODEL_OUTPUT_PATH = os.path.expanduser("~/quant_pipeline/models/artifacts/catboost_macro_interaction_v2.cbm")
client = bigquery.Client(project=PROJECT_ID)

QUERY = """
WITH bar_macro_aggregates AS (
  SELECT 
    timestamp,
    AVG(market_breadth_sma20) AS cross_breadth_sma20,
    AVG(top_breakout_breadth)  AS cross_breakout_breadth,
    AVG(rank_mom_24h)          AS cross_mom_avg,
    AVG(rank_vol_compression_ratio) AS cross_vol_comp_avg
  FROM `parnasa-498503.market_data.fct_4h_features_tbm`
  WHERE timestamp BETWEEN "2020-01-01 00:00:00" AND "2026-05-01 00:00:00"
  GROUP BY timestamp
),
macro_time_series AS (
  SELECT 
    timestamp,
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
    ROUND((0.35 * COALESCE(cross_breakout_breadth, 0)) + 
          (0.35 * GREATEST(0.0, COALESCE(breakout_delta_1, 0))) + 
          (0.15 * COALESCE(cross_breadth_sma20, 0)) + 
          (0.15 * COALESCE(prior_comp_3b, 0.5)), 4) AS macro_expansion_score
  FROM macro_time_series
),
macro_quintiles AS (
  SELECT timestamp, macro_expansion_score, NTILE(5) OVER(ORDER BY macro_expansion_score) AS expansion_quintile
  FROM macro_expansion_scoring
)
SELECT 
  f.timestamp, f.ticker, f.close, f.atr_20,
  f.candle_body_pct, f.candle_upper_wick_pct, f.candle_lower_wick_pct,
  f.rank_mom_24h, f.rank_mom_7d, f.rank_mom_accel_24h,
  f.rank_dist_to_120p_high, f.rank_gk_vol_20p, f.rank_vol_compression_ratio,
  f.rank_relative_vol_120p,
  m.macro_expansion_score, q.expansion_quintile,
  f.target_tbm_upper_hit, f.ret_72h_vertical
FROM `parnasa-498503.market_data.fct_4h_features_tbm` f
JOIN macro_expansion_scoring m ON f.timestamp = m.timestamp
JOIN macro_quintiles q ON f.timestamp = q.timestamp
WHERE f.target_tbm_upper_hit IS NOT NULL
ORDER BY f.timestamp ASC
"""

print("[1/3] Fetching multi-year feature mart from BigQuery...")
df = client.query(QUERY).to_dataframe()

FEATURES = [
    "candle_body_pct", "candle_upper_wick_pct", "candle_lower_wick_pct",
    "rank_mom_24h", "rank_mom_7d", "rank_mom_accel_24h",
    "rank_dist_to_120p_high", "rank_gk_vol_20p", "rank_vol_compression_ratio",
    "rank_relative_vol_120p", "macro_expansion_score", "expansion_quintile"
]
df = df.dropna(subset=FEATURES + ["target_tbm_upper_hit"]).copy()

# Purged split: Train through end of 2024, validation on 2025
train_df = df[df["timestamp"] <= "2024-12-28 16:00:00+00:00"].copy()
val_df = df[df["timestamp"] >= "2025-01-01 00:00:00+00:00"].copy()

print(f"      Train rows: {len(train_df):,} | Val rows: {len(val_df):,}")

# Exact Optuna Hyperparameters
params = {
    "iterations": 1000,
    "learning_rate": 0.055076,
    "depth": 6,
    "l2_leaf_reg": 14.4822,
    "random_strength": 1.0166,
    "loss_function": "Logloss",
    "eval_metric": "AUC",
    "random_seed": 42,
    "verbose": 100
}

print("\n[2/3] Training optimized CatBoost interaction model...")
train_pool = Pool(train_df[FEATURES], train_df["target_tbm_upper_hit"])
val_pool = Pool(val_df[FEATURES], val_df["target_tbm_upper_hit"])

model = CatBoostClassifier(**params)
model.fit(train_pool, eval_set=val_pool, early_stopping_rounds=50)

print(f"\n[3/3] Saving production artifact to {MODEL_OUTPUT_PATH}...")
os.makedirs(os.path.dirname(MODEL_OUTPUT_PATH), exist_ok=True)
model.save_model(MODEL_OUTPUT_PATH)
print("      Model successfully saved.")
