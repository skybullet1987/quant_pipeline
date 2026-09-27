import optuna
import pandas as pd
import numpy as np
from catboost import CatBoostClassifier, Pool
from google.cloud import bigquery
import warnings
warnings.filterwarnings("ignore")

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

print("[1/3] Loading multi-year dataset for Optuna optimization...")
df = client.query(QUERY).to_dataframe()

FEATURES = [
    "candle_body_pct", "candle_upper_wick_pct", "candle_lower_wick_pct",
    "rank_mom_24h", "rank_mom_7d", "rank_mom_accel_24h",
    "rank_dist_to_120p_high", "rank_gk_vol_20p", "rank_vol_compression_ratio",
    "rank_relative_vol_120p", "macro_expansion_score", "expansion_quintile"
]
df = df.dropna(subset=FEATURES + ["target_tbm_upper_hit", "ret_72h_vertical"]).copy()

# Purged split: Train <= 2024-12-28, Val: 2025-01-01 to 2026-05-01
train_df = df[df["timestamp"] <= "2024-12-28 16:00:00+00:00"].copy()
val_df = df[df["timestamp"] >= "2025-01-01 00:00:00+00:00"].copy()

train_pool = Pool(train_df[FEATURES], train_df["target_tbm_upper_hit"])
val_pool = Pool(val_df[FEATURES], val_df["target_tbm_upper_hit"])
print(f"      Train: {len(train_df):,} rows | Validation: {len(val_df):,} rows")

def objective(trial):
    params = {
        "iterations": 500,
        "learning_rate": trial.suggest_float("learning_rate", 0.015, 0.07, log=True),
        "depth": trial.suggest_int("depth", 4, 7),
        "l2_leaf_reg": trial.suggest_float("l2_leaf_reg", 1.0, 25.0, log=True),
        "random_strength": trial.suggest_float("random_strength", 0.1, 5.0),
        "loss_function": "Logloss",
        "eval_metric": "AUC",
        "random_seed": 42,
        "verbose": False
    }

    model = CatBoostClassifier(**params)
    model.fit(train_pool, eval_set=val_pool, early_stopping_rounds=35, verbose=False)

    val_preds = model.predict_proba(val_df[FEATURES])[:, 1]
    val_temp = val_df.copy()
    val_temp["pred_p"] = val_preds

    # Parameterize regime hurdles
    h_q1 = trial.suggest_float("hurdle_q1", 0.50, 0.55)
    h_q_chop = trial.suggest_float("hurdle_q_chop", 0.54, 0.60)
    h_q5 = trial.suggest_float("hurdle_q5", 0.50, 0.55)

    val_temp["active_h"] = np.where(
        val_temp["expansion_quintile"] == 1, h_q1,
        np.where(val_temp["expansion_quintile"] == 5, h_q5, h_q_chop)
    )

    selected = val_temp[val_temp["pred_p"] >= val_temp["active_h"]].sort_values(
        ["timestamp", "pred_p"], ascending=[True, False]
    ).groupby("timestamp").first().reset_index()

    if len(selected) < 25:
        return -100.0

    # Realized R calculation with hard -1.0R stop loss
    pnl_raw = np.where(
        selected["target_tbm_upper_hit"] == 1, 1.80,
        np.maximum(-1.0, selected["ret_72h_vertical"] * selected["close"] / np.maximum(selected["atr_20"], 1e-6))
    )
    selected["pnl_r"] = pnl_raw - 0.10

    downside = selected[selected["pnl_r"] < 0]["pnl_r"].std()
    sortino = (selected["pnl_r"].mean() / max(downside, 1e-4)) * np.sqrt(len(selected))
    return sortino

print("\n[2/3] Running Optuna Bayesian Search (35 trials)...")
optuna.logging.set_verbosity(optuna.logging.WARNING)
study = optuna.create_study(direction="maximize")
study.optimize(objective, n_trials=35)

print("\n[3/3] ================= BEST OPTUNA PARAMETERS =================")
print(f"Best Validation Sortino: {study.best_value:.3f}")
for k, v in study.best_params.items():
    print(f"  {k:20s}: {v}")
