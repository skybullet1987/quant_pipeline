"""
High-Conviction Alpha Engine:
- Pure Continuous CatBoost Tail Alpha (Top 3 Longs / Bottom 3 Shorts)
- Conviction & Inverse-NATR Risk Parity Weighting
- 12% Catastrophic Short Squeeze Stop
- 72H Multi-Day Holding Horizon
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

# 72H Forward Target (18 bars)
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

print(f"2. Training Continuous CatBoost Model ({len(timestamps)} timestamps)...")
for s in range(2160, len(timestamps), 720):
    e = min(s + 720, len(timestamps))
    tr_mask = pdf["ts_utc"].isin(set(timestamps.iloc[:s]))
    te_mask = pdf["ts_utc"].isin(set(timestamps.iloc[s:e]))
    
    X_tr, y_tr = pdf.loc[tr_mask, feature_cols].values, pdf.loc[tr_mask, "target_excess_72h"].values
    X_te = pdf.loc[te_mask, feature_cols].values
    if len(X_te) == 0 or len(X_tr) == 0:
        continue
        
    cat = CatBoostRegressor(iterations=60, depth=4, learning_rate=0.03, random_seed=42, thread_count=-1, verbose=0)
    cat.fit(X_tr, y_tr)
    pdf.loc[te_mask, "alpha_pred"] = cat.predict(X_te)

oof = pdf[pdf["alpha_pred"] != 0.0].copy()
sample_times = timestamps.iloc[2160::18]
rebal_oof = oof[oof["ts_utc"].isin(set(sample_times))]

print("3. Simulating Conviction-Weighted Execution...")
trade_records = []
top_k = 3

for t, grp in rebal_oof.groupby("ts_utc"):
    if len(grp) < (top_k * 2):
        continue

    sorted_grp = grp.sort_values("alpha_pred", ascending=False)
    top_long_df = sorted_grp.head(top_k)
    top_short_df = sorted_grp.tail(top_k)

    # Conviction * Inverse NATR Weights
    w_l_raw = np.maximum(top_long_df["alpha_pred"].values, 0.001) / (top_long_df["normalized_atr_24h"].values + 1e-4)
    w_l = w_l_raw / np.sum(w_l_raw)

    w_s_raw = np.maximum(-top_short_df["alpha_pred"].values, 0.001) / (top_short_df["normalized_atr_24h"].values + 1e-4)
    w_s = w_s_raw / np.sum(w_s_raw)

    # Target 1.5x Long / 1.5x Short (3.0x Gross Leverage)
    long_rets = top_long_df["target_excess_72h"].values
    short_raw_rets = top_short_df["target_excess_72h"].values
    short_rets = np.maximum(-short_raw_rets, -0.12)  # 12% Short Squeeze Hard Stop[cite: 1]

    b_long_ret = np.sum(long_rets * w_l) * 1.5
    b_short_ret = np.sum(short_rets * w_s) * 1.5

    gross_spread = (np.sum(long_rets * w_l) + np.sum(short_rets * w_s))
    net_ret = (b_long_ret + b_short_ret) - (0.0007 * 3.0)  # 7 bps taker fee scaled by 3.0x leverage[cite: 1]

    trade_records.append({
        "timestamp": t,
        "gross_spread": gross_spread,
        "net_return": net_ret
    })

tdf = pd.DataFrame(trade_records).sort_values("timestamp").reset_index(drop=True)
tdf["equity"] = 500.0 * np.cumprod(1.0 + tdf["net_return"])
tdf["peak"] = tdf["equity"].cummax()
tdf["drawdown"] = (tdf["equity"] - tdf["peak"]) / tdf["peak"]

max_dd = tdf["drawdown"].min()
total_ret = (tdf["equity"].iloc[-1] - 500.0) / 500.0
cagr = ((tdf["equity"].iloc[-1] / 500.0) ** (1.0 / 4.64)) - 1.0
calmar = cagr / abs(max_dd)

ann_factor = np.sqrt(365 * 24 / 72)
downside_std = tdf.loc[tdf["net_return"] < 0, "net_return"].std() * ann_factor
sortino = (tdf["net_return"].mean() * (365 * 24 / 72)) / (downside_std + 1e-6)

print("\n" + "=" * 70)
print("     PURE CONVICTION-WEIGHTED TAIL ALPHA RESULTS ($500)")
print("=" * 70)
print(f"Total Discrete Rebalances:      {len(tdf):8d}")
print(f"Gross Spread per Trade:         {tdf['gross_spread'].mean() * 10000:+8.1f} bps")
print(f"Starting Capital:               $500.00")
print(f"Ending Capital:                 ${tdf['equity'].iloc[-1]:10,.2f}")
print(f"Total Cumulative Return:        {total_ret * 100:10.2f}%")
print(f"Compound Annual Growth (CAGR):  {cagr * 100:8.2f}%")
print(f"Maximum Drawdown (Max DD):      {max_dd * 100:8.2f}%")
print(f"Calmar Ratio (CAGR / Max DD):   {calmar:8.2f}")
print(f"Sortino Ratio:                  {sortino:8.2f}")
print("=" * 70)
