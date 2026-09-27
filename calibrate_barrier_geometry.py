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
  m.macro_expansion_score, q.expansion_quintile
FROM `parnasa-498503.market_data.fct_4h_features_tbm` f
JOIN macro_expansion_scoring m ON f.timestamp = m.timestamp
JOIN macro_quintiles q ON f.timestamp = q.timestamp
WHERE f.timestamp BETWEEN "2026-05-18 00:00:00" AND "2026-08-17 20:00:00"
ORDER BY f.timestamp ASC
"""

print("[1/2] Loading 90-day dataset...")
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

SL_GRID = [2.0, 2.5, 3.0, 3.5]
TP_GRID = [2.0, 2.5, 3.0, 3.5, 4.5]
FEE_SLIPPAGE_R = 0.10
START_EQUITY = 500.0
RISK_PCT = 0.015
MAX_SLOTS = 2

results = []
print("[2/2] Testing multi-ATR barrier surface with breakeven protection...")

for k_sl in SL_GRID:
    for k_tp in TP_GRID:
        for use_be in [False, True]:
            current_equity = START_EQUITY
            equity_curve = [START_EQUITY]
            active_trades = []
            trade_logs = []

            for current_bar in all_timestamps:
                still_active = []
                for trade in active_trades:
                    trade["bars_held"] += 1
                    ticker = trade["ticker"]
                    candle = price_dict.get((ticker, current_bar))
                    if candle is None:
                        still_active.append(trade)
                        continue

                    _, bar_high, bar_low, bar_close = candle

                    # Breakeven ratchet: move stop to entry if high crossed +1.5R
                    if use_be and not trade["be_active"]:
                        if bar_high >= trade["entry_price"] + (1.5 * trade["atr"]):
                            trade["sl_price"] = trade["entry_price"] + (0.10 * trade["atr"])  # Entry + friction buffer
                            trade["be_active"] = True

                    hit_tp = bar_high >= trade["tp_price"]
                    hit_sl = bar_low <= trade["sl_price"]

                    if hit_tp and not hit_sl:
                        realized_r = k_tp - FEE_SLIPPAGE_R
                        current_equity += trade["dollar_risk"] * (realized_r / k_sl)
                        trade["realized_r"] = realized_r
                        trade_logs.append(trade)
                    elif hit_sl and not hit_tp:
                        if trade.get("be_active", False):
                            realized_r = 0.0  # Stopped at breakeven
                        else:
                            realized_r = -k_sl - FEE_SLIPPAGE_R
                        current_equity += trade["dollar_risk"] * (realized_r / k_sl)
                        trade["realized_r"] = realized_r
                        trade_logs.append(trade)
                    elif hit_tp and hit_sl:
                        # Conservative tie-break: SL hit first
                        realized_r = 0.0 if trade.get("be_active", False) else -k_sl - FEE_SLIPPAGE_R
                        current_equity += trade["dollar_risk"] * (realized_r / k_sl)
                        trade["realized_r"] = realized_r
                        trade_logs.append(trade)
                    elif trade["bars_held"] >= 18:
                        # 72h Time barrier exit
                        raw_r = (bar_close - trade["entry_price"]) / max(trade["atr"], 1e-6)
                        bounded_r = max(-k_sl, min(k_tp, raw_r))
                        realized_r = bounded_r - FEE_SLIPPAGE_R
                        current_equity += trade["dollar_risk"] * (realized_r / k_sl)
                        trade["realized_r"] = realized_r
                        trade_logs.append(trade)
                    else:
                        still_active.append(trade)

                active_trades = still_active

                # Screen entries
                available_slots = MAX_SLOTS - len(active_trades)
                if available_slots <= 0:
                    equity_curve.append(current_equity)
                    continue

                bar_df = df_scored[(df_scored["timestamp"] == current_bar) & (df_scored["is_eligible"] == True)]
                if bar_df.empty:
                    equity_curve.append(current_equity)
                    continue

                top_candidates = bar_df.sort_values("p_long", ascending=False).head(available_slots)

                for _, row in top_candidates.iterrows():
                    entry_price = float(row["close"])
                    atr = float(row["atr_20"])
                    tp_price = entry_price + (k_tp * atr)
                    sl_price = entry_price - (k_sl * atr)
                    dollar_risk = current_equity * RISK_PCT

                    active_trades.append({
                        "ticker": row["ticker"],
                        "entry_price": entry_price,
                        "atr": atr,
                        "tp_price": tp_price,
                        "sl_price": sl_price,
                        "dollar_risk": dollar_risk,
                        "be_active": False,
                        "bars_held": 0
                    })

                equity_curve.append(current_equity)

            t_df = pd.DataFrame(trade_logs)
            if t_df.empty:
                continue

            win_rate = (t_df["realized_r"] > 0).mean()
            mean_r = t_df["realized_r"].mean()
            gross_win = t_df[t_df["realized_r"] > 0]["realized_r"].sum()
            gross_loss = abs(t_df[t_df["realized_r"] < 0]["realized_r"].sum())
            profit_factor = gross_win / max(gross_loss, 1e-6)

            eq_series = pd.Series(equity_curve)
            peak = eq_series.cummax()
            drawdown_pct = (eq_series - peak) / peak
            total_return_pct = ((current_equity - START_EQUITY) / START_EQUITY) * 100
            max_dd_pct = abs(drawdown_pct.min()) * 100
            calmar = (total_return_pct * 4) / max(max_dd_pct, 1e-4)

            results.append({
                "SL (ATR)": f"-{k_sl:.1f}",
                "TP (ATR)": f"+{k_tp:.1f}",
                "Breakeven": "YES" if use_be else "NO",
                "Trades": len(t_df),
                "Win Rate": f"{win_rate*100:.1f}%",
                "Profit Factor": round(profit_factor, 2),
                "$500 Final": f"${current_equity:,.2f}",
                "Return (%)": f"{total_return_pct:+.1f}%",
                "Max DD (%)": f"-{max_dd_pct:.2f}%",
                "Calmar": round(calmar, 2)
            })

res_df = pd.DataFrame(results).sort_values("Profit Factor", ascending=False)
print("\n================= CALIBRATED MULTI-ATR GEOMETRY SURFACE =================")
print(res_df.head(15).to_string(index=False))
