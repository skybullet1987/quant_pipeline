"""
Production Model Exporter:
Trains the finalized CatBoost model on the full historical dataset 
and exports serialized model artifacts + universe metadata to disk.
"""
import os
import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import polars as pl
import pandas as pd
from catboost import CatBoostRegressor

from src.features.orthogonal_library import compute_orthogonal_features

MODEL_DIR = PROJECT_ROOT / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

print("1. Ingesting Top-50 Liquid Universe...")
raw_df = pl.read_parquet("/tmp/lake/features/pit_panel_4h.parquet")

top_50 = (
    raw_df.group_by("symbol")
    .agg((pl.col("volume") * pl.col("close")).mean().alias("dvol"))
    .sort("dvol", descending=True)
    .head(50)["symbol"]
    .to_list()
)

df = raw_df.filter(pl.col("symbol").is_in(top_50)).unique(["symbol", "bucket_timestamp_utc"]).sort("bucket_timestamp_utc")
feat_df = compute_orthogonal_features(df)

h_bars = 18
h_df = feat_df.with_columns([
    pl.col("close").pct_change(h_bars).shift(-h_bars).over("symbol").alias("fwd_ret_72h")
])
mkt = h_df.group_by("bucket_timestamp_utc").agg(pl.col("fwd_ret_72h").mean().alias("mkt_fwd_72h"))

pdf = (
    h_df.join(mkt, on="bucket_timestamp_utc")
    .with_columns([(pl.col("fwd_ret_72h") - pl.col("mkt_fwd_72h")).alias("target_excess_72h")])
    .to_pandas()
)

feature_cols = [
    "cs_rank_ret_24h", "cs_rank_ret_72h", "cs_mom_acceleration_24_72",
    "cs_dist_to_universe_median_24h", "beta_btc_7d", "idio_residual_ret_btc_24h",
    "garman_klass_vol_ratio_24h", "normalized_atr_24h", "bollinger_keltner_squeeze_ratio_20",
    "clv_4h", "lower_wick_absorption_ratio_4h", "upper_wick_ratio_4h",
    "intrabar_wick_imbalance_4h", "cs_rank_volume_pct_24h",
    "interaction_mom_squeeze_24h", "interaction_breakout_thrust", "interaction_tbm_score",
]

pdf = pdf.dropna(subset=feature_cols + ["target_excess_72h"])
X = pdf[feature_cols].values
y = pdf["target_excess_72h"].values

print(f"2. Training Production Model on full dataset ({len(pdf):,} samples)...")
model = CatBoostRegressor(
    iterations=80,
    depth=4,
    learning_rate=0.03,
    random_seed=42,
    thread_count=-1,
    verbose=0
)
model.fit(X, y)

# Save model artifact
model_path = MODEL_DIR / "catboost_tail_alpha_v1.cbm"
model.save_model(str(model_path))

# Save universe metadata
meta = {
    "feature_names": feature_cols,
    "top_50_symbols": top_50,
    "horizon_bars": 18,
    "top_k": 3,
    "gross_leverage": 1.50,
    "short_stop_pct": 0.12,
}
with open(MODEL_DIR / "model_metadata.json", "w") as f:
    json.dump(meta, f, indent=2)

print(f"\nModel successfully serialized to: {model_path}")
print(f"Metadata exported to:             {MODEL_DIR / 'model_metadata.json'}")
