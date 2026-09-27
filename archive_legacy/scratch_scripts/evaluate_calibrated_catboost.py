import pandas as pd
import numpy as np
from catboost import CatBoostClassifier
from google.cloud import bigquery

# Load trained model
model = CatBoostClassifier()
model.load_model("catboost_macro_interaction_v1.cbm")

PROJECT_ID = "parnasa-498503"
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
  WHERE timestamp BETWEEN "2025-01-01 00:00:00" AND "2026-08-17 20:00:00"
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
WHERE f.timestamp BETWEEN "2025-01-01 00:00:00" AND "2026-08-17 20:00:00"
  AND f.target_tbm_upper_hit IS NOT NULL
ORDER BY f.timestamp ASC
"""

print("[1/3] Pulling frozen OOS dataset (2025-2026)...")
df_oos = client.query(QUERY).to_dataframe()

FEATURE_COLS = [
    "candle_body_pct", "candle_upper_wick_pct", "candle_lower_wick_pct",
    "rank_mom_24h", "rank_mom_7d", "rank_mom_accel_24h",
    "rank_dist_to_120p_high", "rank_gk_vol_20p", "rank_vol_compression_ratio",
    "rank_relative_vol_120p", "expected_sharpe_proxy", "forecast_momentum",
    "macro_expansion_score", "expansion_quintile", "is_q1_coiling", "is_q5_laggard"
]
df_oos = df_oos.dropna(subset=FEATURE_COLS).copy()

# Score probabilities
df_oos["pred_prob"] = model.predict_proba(df_oos[FEATURE_COLS])[:, 1]

# Distribution Audit
print("\n[2/3] --- Model OOS Probability Distribution ---")
for p in [50, 75, 90, 95, 98, 99]:
    val = np.percentile(df_oos["pred_prob"], p)
    print(f"P{p:02d}: {val:.4f}")

# Calibrated Hurdle Sweeps (Evaluating TBM Payoff: TP = +1.8R, SL = -1.0R, Vertical = ret_72h_vertical / ATR)
print("\n[3/3] ================= CALIBRATED HURDLE SWEEP (OOS 2025-2026) =================")
FEE_SLIPPAGE_R = 0.10  # 0.10R fee drag per trade

# Triple Barrier Payoff Modeling
df_oos["tbm_pnl_r"] = np.where(
    df_oos["target_tbm_upper_hit"] == 1,
    1.80 - FEE_SLIPPAGE_R,  # Hit TP1
    np.where(
        df_oos["ret_72h_vertical"] < -0.05, 
        -1.00 - FEE_SLIPPAGE_R, # Hit SL
        (df_oos["ret_72h_vertical"] * df_oos["close"] / np.maximum(df_oos["atr_20"], 1e-6)) - FEE_SLIPPAGE_R
    )
)

results = []
for hurdle in [0.55, 0.60, 0.65, 0.70, 0.75]:
    # Select max 1 candidate per bar matching hurdle
    top_per_bar = df_oos[df_oos["pred_prob"] >= hurdle].sort_values(["timestamp", "pred_prob"], ascending=[True, False]).groupby("timestamp").first().reset_index()
    
    total_bars = df_oos["timestamp"].nunique()
    trades_taken = len(top_per_bar)
    cash_pct = (1.0 - (trades_taken / total_bars)) * 100
    
    if trades_taken > 0:
        win_rate = (top_per_bar["tbm_pnl_r"] > 0).mean()
        mean_pnl_r = top_per_bar["tbm_pnl_r"].mean()
        total_pnl_r = top_per_bar["tbm_pnl_r"].sum()
        
        # Profit Factor
        gross_profit = top_per_bar[top_per_bar["tbm_pnl_r"] > 0]["tbm_pnl_r"].sum()
        gross_loss = abs(top_per_bar[top_per_bar["tbm_pnl_r"] < 0]["tbm_pnl_r"].sum())
        profit_factor = gross_profit / max(gross_loss, 1e-6)
        
        results.append({
            "Hurdle_P": hurdle,
            "Trades": trades_taken,
            "Cash_Posture": f"{cash_pct:.1f}%",
            "TBM_Win_Rate": f"{win_rate*100:.1f}%",
            "Mean_R": round(mean_pnl_r, 3),
            "Profit_Factor": round(profit_factor, 2),
            "Total_PnL_R": round(total_pnl_r, 1)
        })

summary = pd.DataFrame(results)
print(summary.to_string(index=False))
