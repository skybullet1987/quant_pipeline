"""
Tail-Alpha Validation Engine:
Validates the true un-inverted Top-2 Long / Bottom-2 Short spread 
over 72H and 168H holding horizons.
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
import lightgbm as lgb
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

df = (
    raw_df.filter(pl.col("symbol").is_in(top_50))
    .unique(["symbol", "bucket_timestamp_utc"])
    .sort("bucket_timestamp_utc")
)

feat_df = compute_orthogonal_features(df)

# Target: 72H Forward Return (18 bars)
h_bars = 18
h_df = feat_df.with_columns([
    pl.col("close").pct_change(h_bars).shift(-h_bars).over("symbol").alias("fwd_ret")
])
mkt = h_df.group_by("bucket_timestamp_utc").agg(pl.col("fwd_ret").mean().alias("mkt_fwd"))

pdf = (
    h_df.join(mkt, on="bucket_timestamp_utc")
    .with_columns([(pl.col("fwd_ret") - pl.col("mkt_fwd")).alias("target_excess")])
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

pdf = pdf.dropna(subset=feature_cols + ["target_excess"])
timestamps = pd.Series(pdf["bucket_timestamp_utc"].unique()).sort_values().reset_index(drop=True)
pdf["pred"] = 0.0

print("2. Running Walk-Forward Tail-Alpha Validation...")
for s in range(2160, len(timestamps), 720):
    e = min(s + 720, len(timestamps))
    tr_mask = pdf["bucket_timestamp_utc"].isin(set(timestamps.iloc[:s]))
    te_mask = pdf["bucket_timestamp_utc"].isin(set(timestamps.iloc[s:e]))

    X_tr, y_tr = pdf.loc[tr_mask, feature_cols].values, pdf.loc[tr_mask, "target_excess"].values
    X_te = pdf.loc[te_mask, feature_cols].values
    if len(X_te) == 0 or len(X_tr) == 0:
        continue

    cat = CatBoostRegressor(iterations=50, depth=4, learning_rate=0.03, random_seed=42, thread_count=-1, verbose=0).fit(X_tr, y_tr)
    pdf.loc[te_mask, "pred"] = cat.predict(X_te)

oof = pdf[pdf["pred"] != 0.0].copy()

# Sample strictly every 72H (18 bars) to simulate non-overlapping rebalancing
sample_times = timestamps.iloc[2160::18]
rebal_oof = oof[oof["bucket_timestamp_utc"].isin(set(sample_times))]

q_longs, q_shorts = [], []
for t, grp in rebal_oof.groupby("bucket_timestamp_utc"):
    if len(grp) >= 20:
        sorted_grp = grp.sort_values("pred", ascending=False)
        # Top 2 Longs / Bottom 2 Shorts
        q_longs.append(sorted_grp.head(2)["target_excess"].mean())
        q_shorts.append(sorted_grp.tail(2)["target_excess"].mean())

q_longs = np.array(q_longs)
q_shorts = np.array(q_shorts)

# Long Q_top minus Short Q_bottom spread
trade_spreads = q_longs - q_shorts
taker_fee = 0.0007  # 7.0 bps round-trip taker fee[cite: 1]
net_trade_spreads = trade_spreads - taker_fee

cum_gross = np.cumprod(1 + trade_spreads * 1.5)  # 1.5x Long / 1.5x Short (3.0x Gross)
cum_net = np.cumprod(1 + net_trade_spreads * 1.5)

print("\n" + "=" * 70)
print("     UN-INVERTED TAIL ALPHA (72H HORIZON / TOP 2 L/S)")
print("=" * 70)
print(f"Total Discrete Rebalance Trades: {len(trade_spreads):8d}")
print(f"Mean Gross Alpha per Trade:      {np.mean(trade_spreads) * 10000:+8.1f} bps")
print(f"Mean Net Alpha per Trade:        {np.mean(net_trade_spreads) * 10000:+8.1f} bps (After 7 bps Fee)[cite: 1]")
print(f"Trade Win Rate:                  {(trade_spreads > 0).mean() * 100:7.2f}%")
print(f"Sharpe Ratio (Annualized):       {(np.mean(net_trade_spreads) / (np.std(net_trade_spreads) + 1e-6)) * np.sqrt(365 * 24 / 72):8.2f}")
print("-" * 70)
print(f"Gross Capital Growth on $500:    ${500 * cum_gross[-1]:10,.2f}")
print(f"Net Capital Growth on $500:      ${500 * cum_net[-1]:10,.2f}")
print("=" * 70)
