import os
import pandas as pd
import numpy as np
from catboost import CatBoostClassifier, Pool
from google.cloud import bigquery

PROJECT_ID = "parnasa-498503"
client = bigquery.Client(project=PROJECT_ID)

FEATURE_COLS = [
    "candle_body_pct", "candle_upper_wick_pct", "candle_lower_wick_pct",
    "rank_mom_24h", "rank_mom_7d", "rank_mom_accel_24h",
    "rank_dist_to_120p_high", "rank_gk_vol_20p", "rank_vol_compression_ratio",
    "rank_relative_vol_120p"
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
  WHERE timestamp >= "2020-01-01 00:00:00"
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
  f.target_tbm_upper_hit, f.ret_72h_vertical
FROM `parnasa-498503.market_data.fct_4h_features_tbm` f
JOIN macro_expansion_scoring m ON f.timestamp = m.timestamp
JOIN macro_quintiles q ON f.timestamp = q.timestamp
ORDER BY f.timestamp ASC
"""

print("[1/4] Pulling full multi-year market history (2020-2026)...")
df = client.query(QUERY).to_dataframe()
df = df[~df["ticker"].isin(EXCLUDE_TICKERS)].dropna(subset=FEATURE_COLS + ["ret_72h_vertical"]).copy()
df["timestamp"] = pd.to_datetime(df["timestamp"])

# 1. Purged Training Set: 2020-01-01 to 2021-12-31
train_df = df[df["timestamp"] <= "2021-12-28 16:00:00+00:00"].copy()
test_df = df[df["timestamp"] >= "2022-01-01 00:00:00+00:00"].copy()

print(f"      Train Samples (2020-2021): {len(train_df):,} rows")
print(f"      Test Samples  (2022-2026): {len(test_df):,} rows across {test_df['timestamp'].nunique():,} 4H bars")

print("\n[2/4] Fitting baseline CatBoost ranker (No Optuna hacking)...")
model = CatBoostClassifier(
    iterations=600,
    learning_rate=0.04,
    depth=5,
    l2_leaf_reg=5.0,
    loss_function="Logloss",
    random_seed=42,
    verbose=False
)
model.fit(train_df[FEATURE_COLS], train_df["target_tbm_upper_hit"])

test_df["p_rank"] = model.predict_proba(test_df[FEATURE_COLS])[:, 1]

print("\n[3/4] Running zero-hurdle portfolio simulation (Binary Q5 Gate -> Top 2 Assets)...")
MAX_SLOTS = 2
K_SL = 3.0  # Wide disaster stop (3x ATR)
K_TP = 2.5  # Take profit target (2.5x ATR)
FEE_SLIPPAGE_R = 0.10
START_EQUITY = 500.0
RISK_PCT = 0.015

# Price dictionary for fast lookup
price_dict = {}
for (ticker, ts), row in test_df.set_index(["ticker", "timestamp"]).iterrows():
    price_dict[(ticker, ts)] = (row["open"], row["high"], row["low"], row["close"])

all_timestamps = sorted(test_df["timestamp"].unique())
current_equity = START_EQUITY
equity_curve = []
active_trades = []
completed_trades = []

for current_bar in all_timestamps:
    # 1. Update active trades
    still_active = []
    for trade in active_trades:
        trade["bars_held"] += 1
        candle = price_dict.get((trade["ticker"], current_bar))
        if candle is None:
            still_active.append(trade)
            continue

        _, b_high, b_low, b_close = candle
        hit_tp = b_high >= trade["tp_price"]
        hit_sl = b_low <= trade["sl_price"]

        if hit_tp and not hit_sl:
            realized_r = K_TP - FEE_SLIPPAGE_R
            dollar_pnl = trade["dollar_risk"] * (realized_r / K_SL)
            current_equity += dollar_pnl
            trade["realized_r"] = realized_r
            trade["exit_bar"] = current_bar
            trade["exit_type"] = "TP (+2.5R)"
            completed_trades.append(trade)
        elif hit_sl:
            realized_r = -K_SL - FEE_SLIPPAGE_R
            dollar_pnl = trade["dollar_risk"] * (realized_r / K_SL)
            current_equity += dollar_pnl
            trade["realized_r"] = realized_r
            trade["exit_bar"] = current_bar
            trade["exit_type"] = "SL (-3.0R)"
            completed_trades.append(trade)
        elif trade["bars_held"] >= 18:
            raw_r = (b_close - trade["entry_price"]) / max(trade["atr"], 1e-6)
            bounded_r = max(-K_SL, min(K_TP, raw_r))
            realized_r = bounded_r - FEE_SLIPPAGE_R
            dollar_pnl = trade["dollar_risk"] * (realized_r / K_SL)
            current_equity += dollar_pnl
            trade["realized_r"] = realized_r
            trade["exit_bar"] = current_bar
            trade["exit_type"] = "TIME_72H"
            completed_trades.append(trade)
        else:
            still_active.append(trade)

    active_trades = still_active
    equity_curve.append({"timestamp": current_bar, "equity": current_equity})

    # 2. Check available slot capacity
    available_slots = MAX_SLOTS - len(active_trades)
    if available_slots <= 0:
        continue

    # 3. Layer 1: Macro Gate (Only trade when Q5 expansion is active)
    bar_df = test_df[test_df["timestamp"] == current_bar]
    if bar_df.empty or bar_df["expansion_quintile"].iloc[0] < 5:
        continue

    # 4. Layer 2: Cross-Sectional Ranking (Pick Top N candidates directly)
    top_candidates = bar_df.sort_values("p_rank", ascending=False).head(available_slots)

    for _, row in top_candidates.iterrows():
        entry_price = float(row["close"])
        atr = float(row["atr_20"])
        active_trades.append({
            "ticker": row["ticker"],
            "entry_bar": current_bar,
            "year": current_bar.year,
            "entry_price": entry_price,
            "atr": atr,
            "tp_price": entry_price + (K_TP * atr),
            "sl_price": entry_price - (K_SL * atr),
            "dollar_risk": current_equity * RISK_PCT,
            "bars_held": 0
        })

trades_df = pd.DataFrame(completed_trades)
eq_df = pd.DataFrame(equity_curve)

print("\n[4/4] ================= MULTI-YEAR CYCLE BREAKDOWN =================")
years = sorted(trades_df["year"].unique())
summary_rows = []

for yr in years:
    yr_trades = trades_df[trades_df["year"] == yr]
    w_rate = (yr_trades["realized_r"] > 0).mean() * 100
    pnl_r = yr_trades["realized_r"].sum()
    mean_r = yr_trades["realized_r"].mean()
    g_win = yr_trades[yr_trades["realized_r"] > 0]["realized_r"].sum()
    g_loss = abs(yr_trades[yr_trades["realized_r"] < 0]["realized_r"].sum())
    pf = g_win / max(g_loss, 1e-6)

    # Year start / end equity
    yr_eq = eq_df[eq_df["timestamp"].dt.year == yr]["equity"]
    start_e = yr_eq.iloc[0]
    end_e = yr_eq.iloc[-1]
    ret_pct = ((end_e - start_e) / start_e) * 100
    peak = yr_eq.cummax()
    max_dd = abs(((yr_eq - peak) / peak).min()) * 100

    summary_rows.append({
        "Cycle / Year": f"{yr}",
        "Market Phase": "Bear Market" if yr == 2022 else ("Chop / Recovery" if yr == 2023 else ("Bull Market" if yr == 2024 else "Live OOS (2025-26)")),
        "Trades": len(yr_trades),
        "Win Rate": f"{w_rate:.1f}%",
        "Total PnL (R)": f"{pnl_r:+.2f} R",
        "Mean R": f"{mean_r:+.3f} R",
        "Profit Factor": round(pf, 2),
        "Return (%)": f"{ret_pct:+.1f}%",
        "Max DD (%)": f"-{max_dd:.2f}%"
    })

print(pd.DataFrame(summary_rows).to_string(index=False))

total_ret = ((current_equity - START_EQUITY) / START_EQUITY) * 100
total_peak = eq_df["equity"].cummax()
total_dd = abs(((eq_df["equity"] - total_peak) / total_peak).min()) * 100
print(f"\nOverall Compounding (2022-2026): $500.00 -> ${current_equity:,.2f} ({total_ret:+.1f}%) | Max DD: -{total_dd:.2f}%")
