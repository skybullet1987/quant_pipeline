"""
Portfolio Tearsheet & Risk Profile Analyzer:
Calculates Max Drawdown, Calmar Ratio, Monthly Returns,
and Risk-Adjusted Metrics for the 72H Tail-Alpha Strategy.
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

print("1. Re-evaluating 72H equity curve time series...")
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
timestamps = pd.Series(pdf["bucket_timestamp_utc"].unique()).sort_values().reset_index(drop=True)
pdf["alpha_pred"] = 0.0

for s in range(2160, len(timestamps), 720):
    e = min(s + 720, len(timestamps))
    tr_mask = pdf["bucket_timestamp_utc"].isin(set(timestamps.iloc[:s]))
    te_mask = pdf["bucket_timestamp_utc"].isin(set(timestamps.iloc[s:e]))
    X_tr, y_tr = pdf.loc[tr_mask, feature_cols].values, pdf.loc[tr_mask, "target_excess_72h"].values
    X_te = pdf.loc[te_mask, feature_cols].values
    if len(X_te) == 0 or len(X_tr) == 0:
        continue
    cat = CatBoostRegressor(iterations=50, depth=4, learning_rate=0.03, random_seed=42, thread_count=-1, verbose=0).fit(X_tr, y_tr)
    pdf.loc[te_mask, "alpha_pred"] = cat.predict(X_te)

oof = pdf[pdf["alpha_pred"] != 0.0].copy()
sample_times = timestamps.iloc[2160::18]
rebal_oof = oof[oof["bucket_timestamp_utc"].isin(set(sample_times))]

trade_records = []
for t, grp in rebal_oof.groupby("bucket_timestamp_utc"):
    if len(grp) >= 20:
        sorted_grp = grp.sort_values("alpha_pred", ascending=False)
        long_ret = sorted_grp.head(2)["target_excess_72h"].mean()
        short_ret = sorted_grp.tail(2)["target_excess_72h"].mean()
        # 1.5x Long, 1.5x Short minus 7 bps taker fee
        net_ret = (long_ret - short_ret) * 1.5 - 0.0007
        trade_records.append({"timestamp": t, "net_return": net_ret})

tdf = pd.DataFrame(trade_records).sort_values("timestamp").reset_index(drop=True)
tdf["equity"] = 500.0 * np.cumprod(1.0 + tdf["net_return"])
tdf["peak"] = tdf["equity"].cummax()
tdf["drawdown"] = (tdf["equity"] - tdf["peak"]) / tdf["peak"]

max_dd = tdf["drawdown"].min()
total_ret = (tdf["equity"].iloc[-1] - 500.0) / 500.0
cagr = ((tdf["equity"].iloc[-1] / 500.0) ** (1.0 / 4.64)) - 1.0
calmar = cagr / abs(max_dd)

downside_std = tdf.loc[tdf["net_return"] < 0, "net_return"].std() * np.sqrt(365 * 24 / 72)
sortino = (tdf["net_return"].mean() * (365 * 24 / 72)) / (downside_std + 1e-6)

print("\n" + "=" * 70)
print("             72H TAIL-ALPHA RISK & TEARSHEET METRICS")
print("=" * 70)
print(f"Starting Capital:               $500.00")
print(f"Ending Capital:                 ${tdf['equity'].iloc[-1]:,.2f}")
print(f"Total Cumulative Return:        {total_ret * 100:,.2f}%")
print(f"Compound Annual Growth (CAGR):  {cagr * 100:.2f}%")
print(f"Maximum Drawdown (Max DD):      {max_dd * 100:.2f}%")
print(f"Calmar Ratio (CAGR / Max DD):   {calmar:.2f}")
print(f"Sortino Ratio:                  {sortino:.2f}")
print("=" * 70)

# Monthly returns breakdown
tdf["year_month"] = pd.to_datetime(tdf["timestamp"]).dt.to_period("M")
monthly = tdf.groupby("year_month")["net_return"].apply(lambda r: np.prod(1 + r) - 1.0)
print("\nMonthly Performance Highlights:")
print(f"  - Positive Months:            {(monthly > 0).sum()} / {len(monthly)} ({(monthly > 0).mean() * 100:.1f}%)")
print(f"  - Best Month:                 {monthly.max() * 100:+.2f}%")
print(f"  - Worst Month:                {monthly.min() * 100:+.2f}%")
print(f"  - Average Monthly Gain:       {monthly.mean() * 100:+.2f}%")
print("=" * 70)
