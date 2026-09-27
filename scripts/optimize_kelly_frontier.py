"""
Kelly Leverage & Basket Breadth Frontier Optimizer:
Maps out CAGR, Max Drawdown, Sharpe, and Calmar ratios
across different leverage multiples (1.0x to 3.0x) and basket sizes (3L/3S vs 4L/4S vs 5L/5S).
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

print("1. Ingesting Top-50 Liquid Universe and Running Alpha Engine...")
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

# 72H Target
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

oof = pdf[pdf["alpha_pred"] != 0.0].copy()
sample_times = timestamps.iloc[2160::18]
rebal_oof = oof[oof["ts_utc"].isin(set(sample_times))]

print("\n" + "=" * 86)
print("             KELLY LEVERAGE & BASKET BREADTH PARETO FRONTIER")
print("=" * 86)
print(f"{'Basket':<10} | {'Gross Lev':<10} | {'Ending ($500)':<14} | {'CAGR (%)':<10} | {'Max DD (%)':<12} | {'Calmar':<8} | {'Sortino':<8}")
print("-" * 86)

configs = [
    (3, 1.2), (3, 1.5), (3, 1.8), (3, 2.2), (3, 3.0),
    (4, 1.2), (4, 1.5), (4, 1.8), (4, 2.2), (4, 3.0),
    (5, 1.2), (5, 1.5), (5, 1.8), (5, 2.2), (5, 3.0),
]

for top_k, gross_lev in configs:
    trade_rets = []
    for t, grp in rebal_oof.groupby("ts_utc"):
        if len(grp) < (top_k * 2):
            continue
        sorted_grp = grp.sort_values("alpha_pred", ascending=False)
        top_l = sorted_grp.head(top_k)
        top_s = sorted_grp.tail(top_k)

        w_l_raw = np.maximum(top_l["alpha_pred"].values, 0.001) / (top_l["normalized_atr_24h"].values + 1e-4)
        w_l = w_l_raw / np.sum(w_l_raw)

        w_s_raw = np.maximum(-top_s["alpha_pred"].values, 0.001) / (top_s["normalized_atr_24h"].values + 1e-4)
        w_s = w_s_raw / np.sum(w_s_raw)

        long_rets = top_l["target_excess_72h"].values
        short_raw_rets = top_s["target_excess_72h"].values
        short_rets = np.maximum(-short_raw_rets, -0.12)

        half_lev = gross_lev / 2.0
        b_l = np.sum(long_rets * w_l) * half_lev
        b_s = np.sum(short_rets * w_s) * half_lev
        net_ret = (b_l + b_s) - (0.0007 * gross_lev)
        trade_rets.append(net_ret)

    trade_rets = np.array(trade_rets)
    equity = 500.0 * np.cumprod(1.0 + trade_rets)
    peak = np.maximum.accumulate(equity)
    drawdowns = (equity - peak) / peak

    max_dd = drawdowns.min()
    end_eq = equity[-1]
    cagr = ((end_eq / 500.0) ** (1.0 / 4.64)) - 1.0
    calmar = cagr / abs(max_dd)
    ann_factor = np.sqrt(365 * 24 / 72)
    downside_std = trade_rets[trade_rets < 0].std() * ann_factor
    sortino = (trade_rets.mean() * (365 * 24 / 72)) / (downside_std + 1e-6)

    basket_name = f"{top_k}L / {top_k}S"
    print(f"{basket_name:<10} | {gross_lev:<10.1f} | ${end_eq:>12,.2f} | {cagr * 100:>8.2f}% | {max_dd * 100:>10.2f}% | {calmar:>8.2f} | {sortino:>8.2f}")

print("=" * 86)
