import os
import pandas as pd
import numpy as np
from catboost import CatBoostClassifier
from google.cloud import bigquery

PROJECT_ID = "parnasa-498503"
MODEL_PATH = os.path.expanduser("~/quant_pipeline/models/artifacts/catboost_macro_interaction_v2.cbm")
client = bigquery.Client(project=PROJECT_ID)

FEATURE_COLS = [
    "candle_body_pct", "candle_upper_wick_pct", "candle_lower_wick_pct",
    "rank_mom_24h", "rank_mom_7d", "rank_mom_accel_24h",
    "rank_dist_to_120p_high", "rank_gk_vol_20p", "rank_vol_compression_ratio",
    "rank_relative_vol_120p", "macro_expansion_score", "expansion_quintile"
]
EXCLUDE_TICKERS = ["PAXGUSD", "USDCUSD", "USDTUSD", "FDUSDUSD", "EURUSD", "TUSDUSD"]

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
WHERE f.timestamp BETWEEN "2026-05-18 00:00:00" AND "2026-08-17 20:00:00"
  AND f.target_tbm_upper_hit IS NOT NULL
ORDER BY f.timestamp ASC
"""

print("[1/2] Loading 90-day out-of-sample feature set...")
df = client.query(QUERY).to_dataframe()
df = df[~df["ticker"].isin(EXCLUDE_TICKERS)].dropna(subset=FEATURE_COLS).copy()

model = CatBoostClassifier()
model.load_model(MODEL_PATH)
df["p_long"] = model.predict_proba(df[FEATURE_COLS])[:, 1]

# Empirical quantile thresholds per regime
quantiles = [0.85, 0.90, 0.95, 0.98]
results = []

print("\n[2/2] Running portfolio simulation across quantile hurdle frontier...")
for q_pct in quantiles:
    h_q1 = df[df["expansion_quintile"] == 1]["p_long"].quantile(q_pct)
    h_q5 = df[df["expansion_quintile"] == 5]["p_long"].quantile(q_pct)

    df_test = df.copy()
    df_test["active_hurdle"] = np.where(
        df_test["expansion_quintile"] == 1, h_q1,
        np.where(df_test["expansion_quintile"] == 5, h_q5, 0.999) # Cash for Q2-Q4
    )
    df_test["is_eligible"] = df_test["p_long"] >= df_test["active_hurdle"]

    MAX_SLOTS = 2
    FEE_SLIPPAGE_R = 0.10
    bars = sorted(df_test["timestamp"].unique())
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

        bar_df = df_test[(df_test["timestamp"] == current_bar) & (df_test["is_eligible"] == True)]
        if bar_df.empty:
            continue

        top_candidates = bar_df.sort_values("p_long", ascending=False).head(available_slots)

        for _, row in top_candidates.iterrows():
            if row["target_tbm_upper_hit"] == 1:
                realized_r = 1.80 - FEE_SLIPPAGE_R
                exit_type = "TP (+1.8R)"
            else:
                pnl_pct = row["ret_72h_vertical"]
                atr_pct = max(row["atr_20"] / max(row["close"], 1e-6), 0.005)
                raw_r = pnl_pct / atr_pct
                bounded_r = max(-1.0, min(1.80, raw_r))
                realized_r = bounded_r - FEE_SLIPPAGE_R
                exit_type = "SL (-1.0R)" if bounded_r <= -1.0 else "TIME_BARRIER (72h)"

            active_trades.append({"realized_r": realized_r, "bars_held": 0})

    completed_trades.extend(active_trades)
    t_df = pd.DataFrame(completed_trades)

    if not t_df.empty:
        total_trades = len(t_df)
        win_rate = (t_df["realized_r"] > 0).mean()
        mean_r = t_df["realized_r"].mean()
        total_r = t_df["realized_r"].sum()
        gross_win = t_df[t_df["realized_r"] > 0]["realized_r"].sum()
        gross_loss = abs(t_df[t_df["realized_r"] < 0]["realized_r"].sum())
        profit_factor = gross_win / max(gross_loss, 1e-6)

        t_df["cum_r"] = t_df["realized_r"].cumsum()
        t_df["peak_r"] = t_df["cum_r"].cummax()
        max_dd_r = abs((t_df["cum_r"] - t_df["peak_r"]).min())
        sharpe = (mean_r / max(t_df["realized_r"].std(), 1e-6)) * np.sqrt(total_trades)

        results.append({
            "Quantile": f"P_{int(q_pct*100)}",
            "Hurdle_Q1": round(h_q1, 4),
            "Hurdle_Q5": round(h_q5, 4),
            "Trades": total_trades,
            "Win_Rate": f"{win_rate*100:.1f}%",
            "Total_PnL_R": f"{total_r:+.2f} R",
            "Mean_R": f"{mean_r:+.3f} R",
            "Profit_Factor": round(profit_factor, 2),
            "Max_DD_R": f"-{max_dd_r:.2f} R",
            "Sharpe": round(sharpe, 2)
        })

print("\n================= 90-DAY OOS CALIBRATION FRONTIER =================")
print(pd.DataFrame(results).to_string(index=False))
