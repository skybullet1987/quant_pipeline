"""
Multi-Horizon Alpha & Fee Friction Diagnostic Tool:
Evaluates 24H vs 72H vs 168H Holding Horizons, Rank Hysteresis,
and Net Expectancy after Hyperliquid Taker & Maker Fees.
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
from sklearn.linear_model import RidgeCV
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

# Evaluate across 3 horizons: 24H (6 bars), 72H (18 bars), 168H (42 bars)
horizons = {"24H (6 bars)": 6, "72H (18 bars)": 18, "168H (42 bars)": 42}

feature_cols = [
    "cs_rank_ret_24h", "cs_rank_ret_72h", "cs_mom_acceleration_24_72",
    "cs_dist_to_universe_median_24h", "beta_btc_7d", "idio_residual_ret_btc_24h",
    "garman_klass_vol_ratio_24h", "normalized_atr_24h", "bollinger_keltner_squeeze_ratio_20",
    "clv_4h", "lower_wick_absorption_ratio_4h", "upper_wick_ratio_4h",
    "intrabar_wick_imbalance_4h", "cs_rank_volume_pct_24h",
    "interaction_mom_squeeze_24h", "interaction_breakout_thrust", "interaction_tbm_score",
]

print("\n" + "=" * 78)
print("       MULTI-HORIZON ALPHA & TRANSACTION FEE FRICTION ANALYSIS")
print("=" * 78)

for h_name, h_bars in horizons.items():
    h_df = feat_df.with_columns([
        pl.col("close").pct_change(h_bars).shift(-h_bars).over("symbol").alias("fwd_ret")
    ])
    mkt = h_df.group_by("bucket_timestamp_utc").agg(pl.col("fwd_ret").mean().alias("mkt_fwd"))
    pdf = (
        h_df.join(mkt, on="bucket_timestamp_utc")
        .with_columns([(pl.col("fwd_ret") - pl.col("mkt_fwd")).alias("target_excess")])
        .to_pandas()
        .dropna(subset=feature_cols + ["target_excess"])
    )

    timestamps = pd.Series(pdf["bucket_timestamp_utc"].unique()).sort_values().reset_index(drop=True)
    pdf["pred"] = 0.0

    for s in range(2160, len(timestamps), 1440):
        e = min(s + 1440, len(timestamps))
        tr_mask = pdf["bucket_timestamp_utc"].isin(set(timestamps.iloc[:s]))
        te_mask = pdf["bucket_timestamp_utc"].isin(set(timestamps.iloc[s:e]))

        X_tr, y_tr = pdf.loc[tr_mask, feature_cols].values, pdf.loc[tr_mask, "target_excess"].values
        X_te = pdf.loc[te_mask, feature_cols].values
        if len(X_te) == 0 or len(X_tr) == 0:
            continue

        lgbm = lgb.LGBMRegressor(n_estimators=30, max_depth=3, learning_rate=0.04, random_state=42, n_jobs=-1, verbose=-1).fit(X_tr, y_tr)
        pdf.loc[te_mask, "pred"] = -lgbm.predict(X_te)

    oof = pdf[pdf["pred"] != 0.0].copy()
    
    q1_returns, q5_returns = [], []
    for t, grp in oof.groupby("bucket_timestamp_utc"):
        if len(grp) >= 20:
            sorted_grp = grp.sort_values("pred", ascending=False)
            q1_returns.append(sorted_grp.head(2)["target_excess"].mean())
            q5_returns.append(sorted_grp.tail(2)["target_excess"].mean())

    gross_spread_bps = (np.mean(q1_returns) - np.mean(q5_returns)) * 10000
    taker_fee_bps = 7.0   # 3.5 bps entry + 3.5 bps exit
    maker_fee_bps = 0.0   # 0.0 bps maker
    
    net_taker_bps = gross_spread_bps - taker_fee_bps
    net_maker_bps = gross_spread_bps - maker_fee_bps

    trades_per_year = (365 * 24 / (h_bars * 4)) * 4
    ann_net_maker = ((1 + (net_maker_bps / 10000)) ** (trades_per_year / 4) - 1) * 100

    print(f"Horizon: {h_name:<16}")
    print(f"  - Gross Spread per Trade:  {gross_spread_bps:+7.1f} bps")
    print(f"  - Net Taker Spread (Mkt):  {net_taker_bps:+7.1f} bps  (Taker Fee = 7.0 bps)")
    print(f"  - Net Maker Spread (Limit):{net_maker_bps:+7.1f} bps  (Maker Fee = 0.0 bps)")
    print(f"  - Projected Annualized Net:{ann_net_maker:+7.2f}% (via Maker Execution)")
    print("-" * 78)
print("=" * 78)
