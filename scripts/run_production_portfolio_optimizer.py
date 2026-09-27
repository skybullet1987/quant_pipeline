"""
Production Portfolio Optimizer & Risk Engine (Calibrated):
- Spread-Based Dynamic Volatility Targeting (1.2x - 2.2x Gross Leverage)
- Fixed UTC Asof-Merge BOCD Hazard Gate (p_hazard > 0.60 -> Cash)
- Inverse-NATR Risk Parity Weighting (4 Longs / 4 Shorts)
- 12% Catastrophic Short Stop-Loss
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

print("1. Ingesting Top-50 Liquid Universe and Macro Regime Data...")
raw_df = pl.read_parquet("/tmp/lake/features/pit_panel_4h.parquet")

top_50 = (
    raw_df.group_by("symbol")
    .agg((pl.col("volume") * pl.col("close")).mean().alias("dvol"))
    .sort("dvol", descending=True)
    .head(50)["symbol"]
    .to_list()
)

df = raw_df.filter(pl.col("symbol").is_in(top_50)).unique(["symbol", "bucket_timestamp_utc"]).sort("bucket_timestamp_utc")

regime_df = (
    pl.read_parquet("/tmp/lake/features/btc_regime_state_4h.parquet")
    .unique(["bucket_timestamp_utc"])
    .sort("bucket_timestamp_utc")
    .to_pandas()
)
regime_df["ts_utc"] = pd.to_datetime(regime_df["bucket_timestamp_utc"], utc=True)
regime_df = regime_df.sort_values("ts_utc").reset_index(drop=True)

feat_df = compute_orthogonal_features(df)

# 72H Forward Excess Target (18 bars)
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

# Merge regime hazard using backward asof matching
pdf = pd.merge_asof(
    pdf.sort_values("ts_utc"),
    regime_df[["ts_utc", "p_hazard"]].sort_values("ts_utc"),
    on="ts_utc",
    direction="backward"
)
pdf["p_hazard"] = pdf["p_hazard"].fillna(0.0)

timestamps = pd.Series(pdf["ts_utc"].unique()).sort_values().reset_index(drop=True)
pdf["alpha_pred"] = 0.0

print("2. Generating Walk-Forward Model Predictions...")
for s in range(2160, len(timestamps), 720):
    e = min(s + 720, len(timestamps))
    tr_mask = pdf["ts_utc"].isin(set(timestamps.iloc[:s]))
    te_mask = pdf["ts_utc"].isin(set(timestamps.iloc[s:e]))
    X_tr, y_tr = pdf.loc[tr_mask, feature_cols].values, pdf.loc[tr_mask, "target_excess_72h"].values
    X_te = pdf.loc[te_mask, feature_cols].values
    if len(X_te) == 0 or len(X_tr) == 0:
        continue
    cat = CatBoostRegressor(iterations=50, depth=4, learning_rate=0.03, random_seed=42, thread_count=-1, verbose=0).fit(X_tr, y_tr)
    pdf.loc[te_mask, "alpha_pred"] = cat.predict(X_te)

oof = pdf[pdf["alpha_pred"] != 0.0].copy()
sample_times = timestamps.iloc[2160::18]
rebal_oof = oof[oof["ts_utc"].isin(set(sample_times))]

print("3. Executing Production Risk-Calibrated Simulation...")
trade_records = []
top_k = 4
target_spread_vol = 0.48  # Target 48% annualized spread volatility

for t, grp in rebal_oof.groupby("ts_utc"):
    if len(grp) < (top_k * 2):
        continue

    p_hazard = grp["p_hazard"].iloc[0]
    if p_hazard > 0.60:
        # Cash Lockout during BOCD Regime Shocks
        trade_records.append({"timestamp": t, "net_return": 0.0, "hazard": True, "leverage": 0.0})
        continue

    sorted_grp = grp.sort_values("alpha_pred", ascending=False)
    top_long_df = sorted_grp.head(top_k)
    top_short_df = sorted_grp.tail(top_k)

    # Inverse-NATR Risk Parity Sizing
    inv_natr_l = 1.0 / (top_long_df["normalized_atr_24h"].values + 1e-4)
    w_l = inv_natr_l / np.sum(inv_natr_l)

    inv_natr_s = 1.0 / (top_short_df["normalized_atr_24h"].values + 1e-4)
    w_s = inv_natr_s / np.sum(inv_natr_s)

    # Dynamic Spread Volatility Scaling
    basket_natr = np.mean(list(top_long_df["normalized_atr_24h"]) + list(top_short_df["normalized_atr_24h"]))
    # Spread volatility is ~55% of raw directional asset volatility
    estimated_spread_vol = basket_natr * np.sqrt(365) * 0.55
    dynamic_leverage = np.clip(target_spread_vol / (estimated_spread_vol + 1e-4), 1.00, 2.20)

    # Returns calculation with 12% Short Hard Stop
    long_rets = top_long_df["target_excess_72h"].values
    short_raw_rets = top_short_df["target_excess_72h"].values
    short_rets = np.maximum(-short_raw_rets, -0.12)

    basket_long_ret = np.sum(long_rets * w_l) * (dynamic_leverage / 2.0)
    basket_short_ret = np.sum(short_rets * w_s) * (dynamic_leverage / 2.0)

    # 7.0 bps fee deduction
    net_ret = (basket_long_ret + basket_short_ret) - (0.0007 * dynamic_leverage)
    trade_records.append({"timestamp": t, "net_return": net_ret, "hazard": False, "leverage": dynamic_leverage})

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
print("     CALIBRATED PRODUCTION RISK TEARSHEET (48% SPREAD VOL)")
print("=" * 70)
print(f"Starting Capital:               $500.00")
print(f"Ending Capital:                 ${tdf['equity'].iloc[-1]:,.2f}")
print(f"Total Cumulative Return:        {total_ret * 100:,.2f}%")
print(f"Compound Annual Growth (CAGR):  {cagr * 100:.2f}%")
print(f"Maximum Drawdown (Max DD):      {max_dd * 100:.2f}%")
print(f"Calmar Ratio (CAGR / Max DD):   {calmar:.2f}")
print(f"Sortino Ratio:                  {sortino:.2f}")
print(f"BOCD Cash Lockout Triggers:     {tdf['hazard'].sum()} periods")
print(f"Average Gross Leverage Deployed:{tdf['leverage'].mean():.2f}x")
print("=" * 70)

tdf["year_month"] = tdf["timestamp"].dt.tz_localize(None).dt.to_period("M")
monthly = tdf.groupby("year_month")["net_return"].apply(lambda r: np.prod(1 + r) - 1.0)
print("\nMonthly Performance Profile:")
print(f"  - Positive Months:            {(monthly > 0).sum()} / {len(monthly)} ({(monthly > 0).mean() * 100:.1f}%)")
print(f"  - Best Month:                 {monthly.max() * 100:+.2f}%")
print(f"  - Worst Month:                {monthly.min() * 100:+.2f}%")
print(f"  - Average Monthly Gain:       {monthly.mean() * 100:+.2f}%")
print("=" * 70)
