import os
import pandas as pd
import numpy as np
from catboost import CatBoostClassifier
from google.cloud import bigquery

PROJECT_ID = "parnasa-498503"
MODEL_PATH = os.path.expanduser("~/quant_pipeline/models/artifacts/catboost_macro_interaction_v1.cbm")
client = bigquery.Client(project=PROJECT_ID)

FEATURE_COLS = [
    "candle_body_pct", "candle_upper_wick_pct", "candle_lower_wick_pct",
    "rank_mom_24h", "rank_mom_7d", "rank_mom_accel_24h",
    "rank_dist_to_120p_high", "rank_gk_vol_20p", "rank_vol_compression_ratio",
    "rank_relative_vol_120p", "expected_sharpe_proxy", "forecast_momentum",
    "macro_expansion_score", "expansion_quintile", "is_q1_coiling", "is_q5_laggard"
]

QUERY = """
WITH bar_macro_aggregates AS (
  SELECT 
    timestamp,
    AVG(market_breadth_sma20) AS cross_breadth_sma20,
    AVG(top_breakout_breadth)  AS cross_breakout_breadth,
    AVG(rank_mom_24h)          AS cross_mom_avg,
    AVG(rank_vol_compression_ratio) AS cross_vol_comp_avg
  FROM `parnasa-498503.market_data.fct_4h_features_tbm`
  WHERE timestamp >= "2026-05-01 00:00:00"
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
      4
    ) AS macro_expansion_score
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
WHERE f.timestamp BETWEEN "2026-05-18 00:00:00" AND "2026-08-17 20:00:00"
  AND f.target_tbm_upper_hit IS NOT NULL
ORDER BY f.timestamp ASC
"""

print("[1/4] Pulling last 90 days of features and forward target data...")
df = client.query(QUERY).to_dataframe()
df = df.dropna(subset=FEATURE_COLS).copy()
print(f"      Loaded {len(df):,} candidate rows across {df['timestamp'].nunique():,} 4H bars.")

print("[2/4] Scoring with production CatBoost model...")
model = CatBoostClassifier()
model.load_model(MODEL_PATH)
df["p_long"] = model.predict_proba(df[FEATURE_COLS])[:, 1]

# Calibrated production hurdles
df["active_hurdle"] = np.where(df["expansion_quintile"].isin([1, 5]), 0.52, 0.56)
df["is_eligible"] = df["p_long"] >= df["active_hurdle"]

print("[3/4] Running bar-by-bar chronological portfolio simulation (Max 2 Slots)...")
MAX_SLOTS = 2
FEE_SLIPPAGE_R = 0.10  # 0.10R transaction friction
bars = sorted(df["timestamp"].unique())

active_trades = []
completed_trades = []

for current_bar in bars:
    still_active = []
    for trade in active_trades:
        trade["bars_held"] += 1
        if trade["bars_held"] >= 18:
            completed_trades.append(trade)
        else:
            still_active.append(trade)
    active_trades = still_active

    available_slots = MAX_SLOTS - len(active_trades)
    if available_slots <= 0:
        continue

    bar_df = df[(df["timestamp"] == current_bar) & (df["is_eligible"] == True)]
    if bar_df.empty:
        continue

    top_candidates = bar_df.sort_values("p_long", ascending=False).head(available_slots)

    for _, row in top_candidates.iterrows():
        if row["target_tbm_upper_hit"] == 1:
            realized_r = 1.80 - FEE_SLIPPAGE_R
            exit_type = "TP (+1.8R)"
        elif row["ret_72h_vertical"] < -0.05:
            realized_r = -1.00 - FEE_SLIPPAGE_R
            exit_type = "SL (-1.0R)"
        else:
            pnl_pct = row["ret_72h_vertical"]
            atr_pct = max(row["atr_20"] / max(row["close"], 1e-6), 0.005)
            realized_r = (pnl_pct / atr_pct) - FEE_SLIPPAGE_R
            exit_type = "TIME_BARRIER (72h)"

        trade_record = {
            "entry_time": current_bar,
            "ticker": row["ticker"],
            "regime": int(row["expansion_quintile"]),
            "p_long": float(row["p_long"]),
            "hurdle": float(row["active_hurdle"]),
            "exit_type": exit_type,
            "realized_r": realized_r,
            "bars_held": 0
        }
        active_trades.append(trade_record)

completed_trades.extend(active_trades)
trades_df = pd.DataFrame(completed_trades)

print("\n[4/4] ================= 90-DAY OOS PERFORMANCE METRICS =================")
if trades_df.empty:
    print("Zero trades executed (System maintained 100% Cash posture throughout the 90 days).")
else:
    total_bars = len(bars)
    total_trades = len(trades_df)
    win_rate = (trades_df["realized_r"] > 0).mean()
    mean_r = trades_df["realized_r"].mean()
    total_r = trades_df["realized_r"].sum()
    gross_win = trades_df[trades_df["realized_r"] > 0]["realized_r"].sum()
    gross_loss = abs(trades_df[trades_df["realized_r"] < 0]["realized_r"].sum())
    profit_factor = gross_win / max(gross_loss, 1e-6)

    trades_df["cum_r"] = trades_df["realized_r"].cumsum()
    trades_df["peak_r"] = trades_df["cum_r"].cummax()
    trades_df["drawdown_r"] = trades_df["cum_r"] - trades_df["peak_r"]
    max_dd_r = abs(trades_df["drawdown_r"].min())
    trade_sharpe = mean_r / max(trades_df["realized_r"].std(), 1e-6) * np.sqrt(len(trades_df))

    print(f"Evaluation Window     : 2026-05-18 to 2026-08-17 (90 Days / {total_bars} 4H Bars)")
    print(f"Total Trades Taken    : {total_trades}")
    print(f"Cash Posture          : {(1.0 - (total_trades / (total_bars * MAX_SLOTS))) * 100:.1f}%")
    print(f"Win Rate              : {win_rate * 100:.1f}%")
    print(f"Mean Return per Trade : {mean_r:+.3f} R")
    print(f"Total Realized PnL    : {total_r:+.2f} R")
    print(f"Profit Factor         : {profit_factor:.2f}")
    print(f"Max Drawdown          : -{max_dd_r:.2f} R")
    print(f"Trade-Level Sharpe    : {trade_sharpe:.2f}")

    print("\n--- Regime Breakdown ---")
    regime_summary = trades_df.groupby("regime").agg(
        trades=("realized_r", "count"),
        win_rate=("realized_r", lambda x: f"{(x > 0).mean()*100:.1f}%"),
        total_pnl_r=("realized_r", lambda x: f"{x.sum():+.2f} R"),
        mean_pnl_r=("realized_r", lambda x: f"{x.mean():+.3f} R")
    ).reset_index()
    print(regime_summary.to_string(index=False))

    print("\n--- Recent 10 Trades Sample ---")
    cols_to_show = ["entry_time", "ticker", "regime", "p_long", "exit_type", "realized_r"]
    print(trades_df[cols_to_show].tail(10).to_string(index=False))
