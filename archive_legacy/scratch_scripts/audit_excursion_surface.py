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
  f.timestamp, f.ticker, f.open, f.high, f.low, f.close, f.atr_20,
  f.candle_body_pct, f.candle_upper_wick_pct, f.candle_lower_wick_pct,
  f.rank_mom_24h, f.rank_mom_7d, f.rank_mom_accel_24h,
  f.rank_dist_to_120p_high, f.rank_gk_vol_20p, f.rank_vol_compression_ratio,
  f.rank_relative_vol_120p,
  m.macro_expansion_score, q.expansion_quintile,
  f.ret_72h_vertical
FROM `parnasa-498503.market_data.fct_4h_features_tbm` f
JOIN macro_expansion_scoring m ON f.timestamp = m.timestamp
JOIN macro_quintiles q ON f.timestamp = q.timestamp
WHERE f.timestamp BETWEEN "2026-05-18 00:00:00" AND "2026-08-17 20:00:00"
ORDER BY f.timestamp ASC
"""

print("[1/2] Loading raw 4H trajectories...")
df = client.query(QUERY).to_dataframe()
df = df[~df["ticker"].isin(EXCLUDE_TICKERS)].copy()

model = CatBoostClassifier()
model.load_model(MODEL_PATH)
df_scored = df.dropna(subset=FEATURE_COLS).copy()
df_scored["p_long"] = model.predict_proba(df_scored[FEATURE_COLS])[:, 1]

# Calibrated production hurdles
df_scored["active_hurdle"] = np.where(
    df_scored["expansion_quintile"] == 1, 0.4493,
    np.where(df_scored["expansion_quintile"] == 5, 0.4893, 0.5500)
)
df_scored["is_eligible"] = df_scored["p_long"] >= df_scored["active_hurdle"]

price_dict = {}
for (ticker, ts), row in df.set_index(["ticker", "timestamp"]).iterrows():
    price_dict[(ticker, ts)] = (row["open"], row["high"], row["low"], row["close"])

all_timestamps = sorted(df["timestamp"].unique())
ts_to_idx = {ts: idx for idx, ts in enumerate(all_timestamps)}

MAX_SLOTS = 2
active_trades = []
analyzed_trades = []

for current_bar in all_timestamps:
    # Mature trades on 18-bar (72h) clock
    still_active = []
    for trade in active_trades:
        trade["bars_held"] += 1
        t_idx = ts_to_idx[current_bar]
        ticker = trade["ticker"]
        candle = price_dict.get((ticker, current_bar))
        if candle is not None:
            _, b_high, b_low, b_close = candle
            # Track peak excursion during hold
            mfe_atr = (b_high - trade["entry_price"]) / trade["atr"]
            mae_atr = (trade["entry_price"] - b_low) / trade["atr"]
            trade["max_mfe_r"] = max(trade["max_mfe_r"], mfe_atr)
            trade["max_mae_r"] = max(trade["max_mae_r"], mae_atr)

        if trade["bars_held"] >= 18:
            if candle is not None:
                trade["final_return_r"] = (b_close - trade["entry_price"]) / trade["atr"]
            analyzed_trades.append(trade)
        else:
            still_active.append(trade)
    active_trades = still_active

    available_slots = MAX_SLOTS - len(active_trades)
    if available_slots <= 0:
        continue

    bar_df = df_scored[(df_scored["timestamp"] == current_bar) & (df_scored["is_eligible"] == True)]
    if bar_df.empty:
        continue

    top_candidates = bar_df.sort_values("p_long", ascending=False).head(available_slots)
    for _, row in top_candidates.iterrows():
        entry_price = float(row["close"])
        atr = float(row["atr_20"])
        active_trades.append({
            "entry_time": current_bar,
            "ticker": row["ticker"],
            "regime": int(row["expansion_quintile"]),
            "p_long": float(row["p_long"]),
            "entry_price": entry_price,
            "atr": atr,
            "max_mfe_r": 0.0,
            "max_mae_r": 0.0,
            "final_return_r": 0.0,
            "bars_held": 0
        })

res_df = pd.DataFrame(analyzed_trades)

print("\n[2/2] ================= FORWARD 72-HOUR EXCURSION DISTRIBUTION =================")
print(f"Total Qualified Production Trades: {len(res_df)}")
print("\n--- Max Favorable Excursion (Upside Reach in ATR R-units) ---")
print(res_df["max_mfe_r"].describe(percentiles=[0.25, 0.50, 0.75, 0.90]))

print("\n--- Max Adverse Excursion (Downside Drawdown in ATR R-units) ---")
print(res_df["max_mae_r"].describe(percentiles=[0.25, 0.50, 0.75, 0.90]))

print("\n--- Realized 72h Final Vertical Returns (in ATR R-units) ---")
print(res_df["final_return_r"].describe(percentiles=[0.25, 0.50, 0.75, 0.90]))
