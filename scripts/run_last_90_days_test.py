"""
90-Day Recent Performance Stress Test:
Isolates out-of-sample performance to the final 540 bars (90 days).
"""
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd
import polars as pl
from catboost import CatBoostRegressor

from src.features.orthogonal_library import compute_orthogonal_features

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
pdf["ts_utc"] = pd.to_datetime(pdf["bucket_timestamp_utc"], utc=True)
timestamps = pd.Series(pdf["ts_utc"].unique()).sort_values().reset_index(drop=True)
pdf["alpha_pred"] = 0.0

for s in range(2160, len(timestamps), 720):
    e = min(s + 720, len(timestamps))
    tr_mask = pdf["ts_utc"].isin(set(timestamps.iloc[:s]))
    te_mask = pdf["ts_utc"].isin(set(timestamps.iloc[s:e]))
    X_tr, y_tr = pdf.loc[tr_mask, feature_cols].values, pdf.loc[tr_mask, "target_excess_72h"].values
    X_te = pdf.loc[te_mask, feature_cols].values
    if len(X_te) == 0 or len(X_tr) == 0:
        continue
    cat = CatBoostRegressor(iterations=60, depth=4, learning_rate=0.03, random_seed=42, thread_count=-1, verbose=0).fit(X_tr, y_tr)
    pdf.loc[te_mask, "alpha_pred"] = cat.predict(X_te)

# Filter strictly for the last 540 timestamps (~90 days)
last_90_cutoff = timestamps.iloc[-540]
oof = pdf[(pdf["alpha_pred"] != 0.0) & (pdf["ts_utc"] >= last_90_cutoff)].copy()
sample_times = timestamps[timestamps >= last_90_cutoff].iloc[::18]
rebal_oof = oof[oof["ts_utc"].isin(set(sample_times))]

trade_rets = []
for t, grp in rebal_oof.groupby("ts_utc"):
    if len(grp) < 6:
        continue
    sorted_grp = grp.sort_values("alpha_pred", ascending=False)
    top_l = sorted_grp.head(3)
    top_s = sorted_grp.tail(3)

    w_l = (1.0 / (top_l["normalized_atr_24h"].values + 1e-4))
    w_l /= w_l.sum()
    w_s = (1.0 / (top_s["normalized_atr_24h"].values + 1e-4))
    w_s /= w_s.sum()

    long_rets = top_l["target_excess_72h"].values
    short_rets = np.maximum(-top_s["target_excess_72h"].values, -0.12)

    net_ret = (np.sum(long_rets * w_l) * 0.75 + np.sum(short_rets * w_s) * 0.75) - (0.0007 * 1.5)
    trade_rets.append(net_ret)

trade_rets = np.array(trade_rets)
print("\n" + "=" * 50)
print("     LAST 90 DAYS STRESS TEST RESULTS")
print("=" * 50)
print(f"Rebalance Cycles Tested: {len(trade_rets)}")
print(f"Period Net Return:       {((np.prod(1 + trade_rets) - 1.0) * 100):+.2f}%")
print(f"Mean Spread per Trade:   {trade_rets.mean() * 10000:+.1f} bps")
print(f"Period Win Rate:         {(trade_rets > 0).mean() * 100:.1f}%")
print("=" * 50)
