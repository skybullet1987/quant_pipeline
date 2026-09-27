import pandas as pd
import numpy as np
from catboost import CatBoostClassifier, Pool
from google.cloud import bigquery
import time

PROJECT_ID = "parnasa-498503"
client = bigquery.Client(project=PROJECT_ID)

QUERY = """
WITH bar_macro_aggregates AS (
  SELECT 
    timestamp,
    COUNT(DISTINCT ticker) AS active_universe,
    AVG(market_breadth_sma20) AS cross_breadth_sma20,
    AVG(top_breakout_breadth)  AS cross_breakout_breadth,
    AVG(rank_mom_24h)          AS cross_mom_avg,
    AVG(rank_vol_compression_ratio) AS cross_vol_comp_avg
  FROM `parnasa-498503.market_data.fct_4h_features_tbm`
  WHERE timestamp BETWEEN "2020-01-01 00:00:00" AND "2026-08-17 20:00:00"
  GROUP BY timestamp
),

macro_time_series AS (
  SELECT 
    timestamp,
    active_universe,
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
    active_universe,
    ROUND(
      (0.35 * COALESCE(cross_breakout_breadth, 0)) + 
      (0.35 * GREATEST(0.0, COALESCE(breakout_delta_1, 0))) + 
      (0.15 * COALESCE(cross_breadth_sma20, 0)) + 
      (0.15 * COALESCE(prior_comp_3b, 0.5)), 
    4) AS macro_expansion_score
  FROM macro_time_series
),

macro_quintiles AS (
  SELECT 
    timestamp,
    macro_expansion_score,
    NTILE(5) OVER(ORDER BY macro_expansion_score) AS expansion_quintile
  FROM macro_expansion_scoring
)

SELECT 
  f.timestamp,
  f.ticker,
  f.close,
  f.atr_20,
  f.candle_body_pct,
  f.candle_upper_wick_pct,
  f.candle_lower_wick_pct,
  f.rank_mom_24h,
  f.rank_mom_7d,
  f.rank_mom_accel_24h,
  f.rank_dist_to_120p_high,
  f.rank_gk_vol_20p,
  f.rank_vol_compression_ratio,
  f.rank_relative_vol_120p,
  f.expected_sharpe_proxy,
  f.forecast_momentum,
  m.macro_expansion_score,
  q.expansion_quintile,
  CASE 
    WHEN q.expansion_quintile = 1 AND f.rank_dist_to_120p_high BETWEEN 0.40 AND 0.80 AND f.rank_vol_compression_ratio > 0.60 
    THEN 1 ELSE 0 
  END AS is_q1_coiling,
  CASE 
    WHEN q.expansion_quintile = 5 AND f.rank_mom_24h <= 0.50 AND f.rank_dist_to_120p_high < 0.70 
    THEN 1 ELSE 0 
  END AS is_q5_laggard,
  f.target_tbm_upper_hit,
  f.ret_72h_vertical
FROM `parnasa-498503.market_data.fct_4h_features_tbm` f
JOIN macro_expansion_scoring m ON f.timestamp = m.timestamp
JOIN macro_quintiles q ON f.timestamp = q.timestamp
WHERE f.timestamp BETWEEN "2020-01-01 00:00:00" AND "2026-08-17 20:00:00"
  AND f.target_tbm_upper_hit IS NOT NULL
ORDER BY f.timestamp ASC
"""

print("[1/5] Extracting clean historical dataset (2020-01-01 to 2026-08-17)...")
start_t = time.time()
df = client.query(QUERY).to_dataframe()
print(f"      Loaded {len(df):,} rows across {df['timestamp'].nunique():,} 4H bars in {time.time()-start_t:.1f}s")

FEATURE_COLS = [
    "candle_body_pct", "candle_upper_wick_pct", "candle_lower_wick_pct",
    "rank_mom_24h", "rank_mom_7d", "rank_mom_accel_24h",
    "rank_dist_to_120p_high", "rank_gk_vol_20p", "rank_vol_compression_ratio",
    "rank_relative_vol_120p", "expected_sharpe_proxy", "forecast_momentum",
    "macro_expansion_score", "expansion_quintile", "is_q1_coiling", "is_q5_laggard"
]
df = df.dropna(subset=FEATURE_COLS + ["target_tbm_upper_hit", "ret_72h_vertical"]).copy()

# Enforce leak-free 72h purge window
train_mask = df["timestamp"] <= "2024-12-28 16:00:00+00:00"
test_mask = df["timestamp"] >= "2025-01-01 00:00:00+00:00"

train_df = df[train_mask].copy()
test_df = df[test_mask].copy()

print(f"[2/5] Train Set (2020 to 2024-12-28): {len(train_df):,} rows")
print(f"      Purge Embargo Window: 2024-12-28 16:00 to 2025-01-01 00:00 (Dropped)")
print(f"      Frozen OOS Test Set (2025-01-01 to 2026-08-17): {len(test_df):,} rows")

print("\n[3/5] Training CatBoost with Purged Multi-Year Validation...")
train_pool = Pool(train_df[FEATURE_COLS], train_df["target_tbm_upper_hit"])
test_pool = Pool(test_df[FEATURE_COLS], test_df["target_tbm_upper_hit"])

model = CatBoostClassifier(
    iterations=800,
    learning_rate=0.04,
    depth=6,
    loss_function="Logloss",
    eval_metric="AUC",
    random_seed=42,
    verbose=100
)

model.fit(train_pool, eval_set=test_pool, early_stopping_rounds=50, use_best_model=True)

print("\n[4/5] ================= FEATURE IMPORTANCE =================")
fi = pd.DataFrame({"feature": FEATURE_COLS, "importance": model.get_feature_importance()})
print(fi.sort_values("importance", ascending=False).to_string(index=False))

test_df["pred_prob"] = model.predict_proba(test_df[FEATURE_COLS])[:, 1]

print("\n[5/5] ================= FROZEN OOS (2025-2026) REGIME BREAKDOWN =================")
FEE_SLIPPAGE_PCT = 0.0012  # 0.12% round trip taker fee + slippage buffer

results = []
for q in [1, 2, 3, 4, 5]:
    q_df = test_df[test_df["expansion_quintile"] == q].copy()
    
    # Meta-router selection: Top 2 candidates per bar with P >= 0.35
    top_candidates = q_df.sort_values(["timestamp", "pred_prob"], ascending=[True, False]).groupby("timestamp").head(2)
    selected = top_candidates[top_candidates["pred_prob"] >= 0.35]
    
    if len(selected) > 0:
        net_ret = selected["ret_72h_vertical"] - FEE_SLIPPAGE_PCT
        win_rate = (net_ret > 0).mean()
        tbm_hit_rate = selected["target_tbm_upper_hit"].mean()
        mean_ret = net_ret.mean()
        total_ret = net_ret.sum()
        
        results.append({
            "Regime": f"Q{q}",
            "Evaluated_Bars": q_df["timestamp"].nunique(),
            "Trades_Taken": len(selected),
            "TBM_Hit_Rate": round(tbm_hit_rate, 3),
            "Win_Rate": round(win_rate, 3),
            "Mean_Net_Ret": f"{mean_ret * 100:.2f}%",
            "Total_Net_Return": f"{total_ret * 100:.1f}%"
        })

summary_df = pd.DataFrame(results)
print(summary_df.to_string(index=False))

# Save the trained model artifact
model.save_model("catboost_macro_interaction_v1.cbm")
print("\n[Artifact Saved] Successfully exported model to catboost_macro_interaction_v1.cbm")
