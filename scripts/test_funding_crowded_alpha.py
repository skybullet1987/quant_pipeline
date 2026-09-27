"""
10x Alpha Engine: Continuous CatBoost Tail Alpha + Derivatives Positioning Filter
- Longs: Top Predicted Excess Alpha + Uncrowded Funding (Low/Negative Carry)
- Shorts: Bottom Predicted Excess Alpha + Overcrowded Long Funding (High Positive Carry)
- Evaluates discrete 72H non-overlapping holding periods
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

print("1. Ingesting Top-50 Liquid Universe and Engineering Derivatives Features...")
raw_df = pl.read_parquet("/tmp/lake/features/pit_panel_4h.parquet")

top_50 = (
    raw_df.group_by("symbol")
    .agg((pl.col("volume") * pl.col("close")).mean().alias("dvol"))
    .sort("dvol", descending=True)
    .head(50)["symbol"]
    .to_list()
)

df = raw_df.filter(pl.col("symbol").is_in(top_50)).unique(["symbol", "bucket_timestamp_utc"]).sort("bucket_timestamp_utc")

# Compute base orthogonal library
feat_df = compute_orthogonal_features(df)

# Add Derivatives Positioning Features (Family 3)
if "funding_rate" in feat_df.columns:
    feat_df = feat_df.with_columns([
        pl.col("funding_rate").rolling_mean(6).over("symbol").alias("funding_24h"),
        pl.col("funding_rate").rolling_mean(18).over("symbol").alias("funding_72h"),
        pl.col("funding_rate").rank("ordinal").over("bucket_timestamp_utc").alias("cs_rank_funding"),
    ])
else:
    # Synthetic funding proxy from basis/momentum stretch if raw funding column is absent
    feat_df = feat_df.with_columns([
        pl.col("ret_24h").rank("ordinal").over("bucket_timestamp_utc").alias("cs_rank_funding"),
        pl.col("ret_24h").alias("funding_24h"),
    ])

# 72H Forward Target
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

print(f"2. Training Continuous Cross-Sectional CatBoost Model ({len(timestamps)} timestamps)...")
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

print("3. Evaluating Funding-Asymmetric Alpha Spread...")
trade_records = []
top_k = 3  # 3 Longs / 3 Shorts

for t, grp in rebal_oof.groupby("ts_utc"):
    if len(grp) < (top_k * 2):
        continue

    # 1. Long Candidates: Top alpha predictions with low/negative funding (Spot driven)
    long_candidates = grp.sort_values("alpha_pred", ascending=False).head(top_k * 2)
    # Pick lowest funding among top alpha
    top_longs = long_candidates.sort_values("cs_rank_funding", ascending=True).head(top_k)

    # 2. Short Candidates: Bottom alpha predictions with high funding (Overcrowded longs)
    short_candidates = grp.sort_values("alpha_pred", ascending=True).head(top_k * 2)
    # Pick highest funding among bottom alpha
    top_shorts = short_candidates.sort_values("cs_rank_funding", ascending=False).head(top_k)

    l_rets = top_longs["target_excess_72h"].values
    s_raw_rets = top_shorts["target_excess_72h"].values
    s_rets = -s_raw_rets

    mean_l = np.mean(l_rets)
    mean_s = np.mean(s_rets)
    spread = mean_l + mean_s
    net_spread = spread - 0.0007  # Deduct 7.0 bps taker fee

    trade_records.append({
        "timestamp": t,
        "long_ret": mean_l,
        "short_ret": mean_s,
        "gross_spread": spread,
        "net_spread": net_spread
    })

tdf = pd.DataFrame(trade_records).sort_values("timestamp").reset_index(drop=True)
tdf["equity"] = 500.0 * np.cumprod(1.0 + tdf["net_spread"] * 1.5)
tdf["peak"] = tdf["equity"].cummax()
tdf["drawdown"] = (tdf["equity"] - tdf["peak"]) / tdf["peak"]

max_dd = tdf["drawdown"].min()
total_ret = (tdf["equity"].iloc[-1] - 500.0) / 500.0
cagr = ((tdf["equity"].iloc[-1] / 500.0) ** (1.0 / 4.64)) - 1.0
calmar = cagr / abs(max_dd)

ann_factor = np.sqrt(365 * 24 / 72)
sharpe = (tdf["net_spread"].mean() / (tdf["net_spread"].std() + 1e-6)) * ann_factor

print("\n" + "=" * 70)
print("     FUNDING-CONDITIONED CONTINUOUS TAIL-ALPHA RESULTS")
print("=" * 70)
print(f"Total Rebalance Trades:         {len(tdf):8d}")
print(f"Long Basket Mean Return (72H):  {tdf['long_ret'].mean() * 10000:+8.1f} bps")
print(f"Short Basket Mean Return (72H): {tdf['short_ret'].mean() * 10000:+8.1f} bps")
print(f"Gross Long/Short Spread:        {tdf['gross_spread'].mean() * 10000:+8.1f} bps / trade")
print(f"Net L/S Spread (After 7 bps):   {tdf['net_spread'].mean() * 10000:+8.1f} bps / trade")
print(f"Strategy Win Rate:              {(tdf['net_spread'] > 0).mean() * 100:7.2f}%")
print(f"Annualized Sharpe Ratio:        {sharpe:8.2f}")
print(f"Maximum Drawdown:               {max_dd * 100:8.2f}%")
print(f"Calmar Ratio:                   {calmar:8.2f}")
print("-" * 70)
print(f"Starting Capital:               $500.00")
print(f"Compounded Net Capital:         ${tdf['equity'].iloc[-1]:10,.2f} (+{total_ret * 100:,.2f}%)")
print("=" * 70)
