import pandas as pd
import numpy as np
from catboost import CatBoostClassifier
from google.cloud import bigquery

PROJECT_ID = "parnasa-498503"
client = bigquery.Client(project=PROJECT_ID)

QUERY = """
WITH base_candles AS (
  SELECT 
    timestamp,
    ticker,
    open,
    high,
    low,
    close,
    volume,
    atr_20,
    mom_24h,
    dist_ema20_atr,
    bbw_pct_40,
    PERCENT_RANK() OVER(PARTITION BY timestamp ORDER BY mom_24h DESC) AS mom_rank_pct
  FROM `parnasa-498503.market_data.fct_4h_features_production`
),

bar_macro_stats AS (
  SELECT 
    timestamp,
    COUNT(DISTINCT ticker) AS total_universe,
    COUNTIF(dist_ema20_atr >= 1.8 AND mom_24h > 0.03) AS exp_count,
    ROUND(COUNTIF(dist_ema20_atr >= 1.8 AND mom_24h > 0.03) / NULLIF(COUNT(DISTINCT ticker), 0), 4) AS exp_breadth,
    ROUND(AVG(mom_24h), 4) AS cross_mom_avg,
    ROUND(AVG(bbw_pct_40), 4) AS cross_bbw_avg
  FROM base_candles
  GROUP BY timestamp
),

time_series_deltas AS (
  SELECT 
    timestamp,
    exp_breadth,
    cross_mom_avg,
    exp_breadth - LAG(exp_breadth, 1) OVER(ORDER BY timestamp) AS breadth_delta_1,
    cross_mom_avg - LAG(cross_mom_avg, 1) OVER(ORDER BY timestamp) AS mom_delta_1,
    AVG(cross_bbw_avg) OVER(ORDER BY timestamp ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING) AS prior_bbw_3b
  FROM bar_macro_stats
),

macro_expansion_scoring AS (
  SELECT 
    timestamp,
    exp_breadth,
    breadth_delta_1,
    ROUND(
      (0.35 * exp_breadth) + 
      (0.35 * COALESCE(breadth_delta_1, 0)) + 
      (0.15 * GREATEST(0.0, COALESCE(mom_delta_1, 0))) + 
      (0.15 * (1.0 - LEAST(1.0, COALESCE(prior_bbw_3b, 0.05) / 0.10))), 
    4) AS macro_expansion_score
  FROM time_series_deltas
),

macro_quintiles AS (
  SELECT 
    timestamp,
    macro_expansion_score,
    NTILE(5) OVER(ORDER BY macro_expansion_score) AS expansion_quintile
  FROM macro_expansion_scoring
)

SELECT 
  t.timestamp,
  t.ticker,
  t.close,
  t.atr_20,
  t.mom_24h,
  t.dist_ema20_atr,
  t.bbw_pct_40,
  t.mom_rank_pct,
  m.macro_expansion_score,
  q.expansion_quintile,
  CASE 
    WHEN q.expansion_quintile = 1 AND t.dist_ema20_atr BETWEEN 0.0 AND 1.0 AND t.bbw_pct_40 < 0.35 
    THEN 1 ELSE 0 
  END AS is_q1_coiling,
  CASE 
    WHEN q.expansion_quintile = 5 AND t.mom_rank_pct > 0.50 AND t.dist_ema20_atr < 1.0 
    THEN 1 ELSE 0 
  END AS is_q5_laggard,
  (LEAD(t.close, 3) OVER(PARTITION BY t.ticker ORDER BY t.timestamp) - t.close) / NULLIF(t.atr_20, 0) AS target_12h_r
FROM base_candles t
JOIN macro_expansion_scoring m ON t.timestamp = m.timestamp
JOIN macro_quintiles q ON t.timestamp = q.timestamp
WHERE t.timestamp IS NOT NULL
ORDER BY t.timestamp ASC
"""

print("[1/4] Pulling data from BigQuery...")
df = client.query(QUERY).to_dataframe()
df = df.dropna(subset=["target_12h_r", "atr_20", "mom_24h", "dist_ema20_atr", "bbw_pct_40"]).copy()

# Binary classification target: 1 if forward return >= 1.0 ATR
df["target_bin"] = (df["target_12h_r"] >= 1.0).astype(int)

# 80% Train / 20% Chronological Frozen OOS Split
unique_ts = sorted(df["timestamp"].unique())
split_ts = unique_ts[int(len(unique_ts) * 0.80)]

train_df = df[df["timestamp"] < split_ts].copy()
test_df = df[df["timestamp"] >= split_ts].copy()

print(f"[2/4] Train set: {len(train_df):,} rows | OOS Test set: {len(test_df):,} rows (Split timestamp: {split_ts})")

BASE_FEATURES = ["mom_24h", "dist_ema20_atr", "bbw_pct_40"]
INTERACTION_FEATURES = BASE_FEATURES + [
    "mom_rank_pct", 
    "macro_expansion_score", 
    "expansion_quintile", 
    "is_q1_coiling", 
    "is_q5_laggard"
]

def train_and_eval(features, name):
    model = CatBoostClassifier(
        iterations=500,
        learning_rate=0.03,
        depth=5,
        loss_function="Logloss",
        verbose=False,
        random_seed=42
    )
    model.fit(train_df[features], train_df["target_bin"])
    
    test_df[f"prob_{name}"] = model.predict_proba(test_df[features])[:, 1]
    
    FEE_R_PENALTY = 0.10  # ~0.10R round-trip fee + slippage buffer
    
    results = []
    for q in [1, 2, 3, 4, 5]:
        sub = test_df[(test_df["expansion_quintile"] == q) & (test_df[f"prob_{name}"] >= 0.58)]
        if len(sub) > 0:
            net_r = sub["target_12h_r"] - FEE_R_PENALTY
            results.append({
                "model": name,
                "quintile": f"Q{q}",
                "trades": len(sub),
                "win_rate": round((net_r > 0).mean(), 3),
                "mean_net_r": round(net_r.mean(), 3),
                "total_net_r": round(net_r.sum(), 2)
            })
    return pd.DataFrame(results)

print("[3/4] Training Baseline Model A vs Interaction Model B...")
res_a = train_and_eval(BASE_FEATURES, "Baseline_A")
res_b = train_and_eval(INTERACTION_FEATURES, "Interaction_B")

print("\n[4/4] ================= FROZEN OOS EVALUATION =================")
summary = pd.concat([res_a, res_b], ignore_index=True)
print(summary.to_string(index=False))
