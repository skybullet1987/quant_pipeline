#!/usr/bin/env python3
"""
EXPERIMENT 22: GOLDEN STACKED CHALLENGER (FULL 365-DAY LAKE BENCHMARK)
Integrates:
  1. Tri-Alpha Factor Suite (z_a0, z_a1, z_a2)
  2. Mode 4 Beta-Neutral Trend-Filtered Funding Carry Overlay
  3. Dynamic Volatility-Targeted Leverage Scaling
  4. Production Delta-Dispersion Gate (-0.0035 threshold)
  5. Leland Deadband Rebalancing (6-Hour Clock)
"""

import numpy as np
import polars as pl
from pathlib import Path

print("=" * 104)
print("   EXPERIMENT 22: GOLDEN STACKED CHALLENGER (FULL 365-DAY HISTORICAL RUN)")
print("=" * 104)

LAKE_DIR = Path.home() / "quant_pipeline" / "data" / "lake" / "features"
FULL_LAKE_PATH = LAKE_DIR / "pit_panel_1h_full.parquet"
FUNDING_LAKE_PATH = LAKE_DIR / "pit_panel_1h_with_funding.parquet"

df = pl.read_parquet(FULL_LAKE_PATH)

# Merge available real funding data; default missing historical funding to 0.0
if "funding_rate" not in df.columns:
    if FUNDING_LAKE_PATH.exists():
        df_fund = pl.read_parquet(FUNDING_LAKE_PATH).select(["symbol", "timestamp_ms", "funding_rate"]).unique(subset=["symbol", "timestamp_ms"])
        df = df.join(df_fund, on=["symbol", "timestamp_ms"], how="left")
    df = df.with_columns(pl.col("funding_rate").fill_null(0.0) if "funding_rate" in df.columns else pl.lit(0.0).alias("funding_rate"))

# Ensure group_id is mapped monotonically to timestamp_ms
unique_ts = df.select("timestamp_ms").unique().sort("timestamp_ms").with_columns(
    pl.int_range(0, pl.len()).alias("group_id")
)
if "group_id" in df.columns:
    df = df.drop("group_id")
df = df.join(unique_ts, on="timestamp_ms", how="left")

BARS_PER_YEAR = 24 * 365
FEE_RATE = 0.00015
GAMMA_MVO = 0.05
K_ENTRY = 10
K_EXIT = 24
REBAL_CLOCK = 6

# Forward 1H returns
df = df.sort(["symbol", "group_id"]).with_columns([
    (pl.col("close").shift(-1).over("symbol") / pl.col("close") - 1.0).fill_null(0.0).alias("next_ret_1h")
])

# Align BTC
btc = df.filter(pl.col("symbol") == "BTC").select([
    "group_id",
    pl.col("ret_4h").alias("btc_ret_4h"),
    pl.col("ret_12h").alias("btc_ret_12h"),
    pl.col("ret_72h").alias("btc_ret_72h")
]).unique(subset=["group_id"])
df = df.join(btc, on="group_id", how="left")

# Construct Correctly-Signed Alphas
df = df.with_columns([
    # A0: Multi-Horizon Residual Trend
    (
        0.20 * ((pl.col("ret_4h") - pl.col("beta_btc") * pl.col("btc_ret_4h")) / (pl.col("vol_yang_zhang") + 1e-5))
        + 0.30 * ((pl.col("ret_12h") - pl.col("beta_btc") * pl.col("btc_ret_12h")) / (pl.col("vol_yang_zhang") + 1e-5))
        + 0.50 * ((pl.col("ret_72h") - pl.col("beta_btc") * pl.col("btc_ret_72h")) / (pl.col("vol_yang_zhang") + 1e-5))
    ).alias("raw_a0"),
    
    # A1: Volume Divergence / Exhaustion
    (
        -1.0 * ((pl.col("ret_1h") - pl.col("beta_btc") * (pl.col("btc_ret_4h") / 4.0)) / (pl.col("vol_yang_zhang") + 1e-5))
        * (pl.col("volume_zscore_72h").clip(-1.0, 4.0) + 1.0)
    ).alias("raw_a1"),
    
    # A2: Funding Rate Velocity Divergence
    (
        -1.0 * (
            ((pl.col("funding_rate") - pl.col("funding_rate").rolling_mean(24).over("symbol")) /
             (pl.col("funding_rate").rolling_std(24).over("symbol") + 1e-6)).clip(-3.0, 3.0)
            - (pl.col("ret_24h") / (pl.col("vol_yang_zhang") * np.sqrt(24) + 1e-5)).clip(-3.0, 3.0)
        )
    ).alias("raw_a2")
])

# Smooth factors
df = df.sort(["symbol", "group_id"]).with_columns([
    pl.col("raw_a0").ewm_mean(span=6).over("symbol").alias("a0_smooth"),
    pl.col("raw_a1").ewm_mean(span=2).over("symbol").alias("a1_smooth"),
    pl.col("raw_a2").ewm_mean(span=4).over("symbol").alias("a2_smooth")
])

# Cross-sectional standardization per bar
for col, zcol in [("a0_smooth", "z_a0"), ("a1_smooth", "z_a1"), ("a2_smooth", "z_a2")]:
    df = df.with_columns([
        ((pl.col(col) - pl.col(col).mean().over("group_id")) / (pl.col(col).std().over("group_id") + 1e-5)).alias(zcol)
    ])

# Composite Tri-Alpha
df = df.with_columns([
    (0.50 * pl.col("z_a0") + 0.25 * pl.col("z_a1") + 0.25 * pl.col("z_a2")).alias("tri_alpha_score")
])

# Cross-Sectional Dispersion
df_disp = (
    df.filter((pl.col("dollar_volume_1h") > 25_000) & pl.col("ret_72h").is_not_null())
    .group_by("group_id")
    .agg([
        pl.col("ret_72h").std().alias("cs_disp_72h"),
        pl.len().alias("count")
    ])
    .filter(pl.col("count") >= 12)
    .sort("group_id")
    .with_columns([
        pl.col("cs_disp_72h").rolling_mean(window_size=24).alias("cs_disp_ma24")
    ])
    .with_columns([
        (pl.col("cs_disp_72h") - pl.col("cs_disp_ma24")).alias("delta_disp_24h")
    ])
    .drop_nulls(subset=["cs_disp_72h", "delta_disp_24h"])
)
df = df.join(df_disp.select(["group_id", "cs_disp_72h", "delta_disp_24h"]), on="group_id", how="inner")
all_active_grps = sorted(df["group_id"].unique().to_list())

def safe_val(d, k, default=0.0):
    v = d.get(k)
    if v is None: return default
    try:
        f = float(v)
        return default if np.isnan(f) else f
    except:
        return default

CONFIGS = [
    ("1. Baseline Tri-Alpha (Fixed 2.0x)", False, False, 2.0),
    ("2. Tri-Alpha + Trend Carry Overlay", False, True, 2.0),
    ("3. Tri-Alpha + Vol-Target (35% Ann Vol)", True, False, 0.35),
    ("4. Stacked Engine (Tri-Alpha + Trend Carry + Vol-Target 40%)", True, True, 0.40)
]

for label, use_vol_target, use_trend_carry, target_param in CONFIGS:
    nav = 10_000.0
    turnover = 0.0
    prev_w = {}
    active_longs = set()
    active_shorts = set()
    returns = []
    trailing_returns = []

    for idx, grp in enumerate(all_active_grps[:-1]):
        cur_panel = df.filter(pl.col("group_id") == grp)
        valid_panel = cur_panel.filter(
            (pl.col("dollar_volume_1h") > 25_000) &
            pl.col("vol_yang_zhang").is_not_null() &
            pl.col("tri_alpha_score").is_not_null()
        )
        n_avail = valid_panel.height

        returns_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["next_ret_1h"].to_list()))
        funding_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["funding_rate"].to_list()))
        vols_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["vol_yang_zhang"].to_list()))
        beta_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["beta_btc"].to_list()))

        delta_disp = float(valid_panel["delta_disp_24h"][0]) if n_avail >= 12 else -1.0
        
        # Production Dispersion Gate: -0.0035
        breadth_active = (n_avail >= 35) and (delta_disp >= -0.0035)

        is_rebal = (idx % REBAL_CLOCK == 0)

        if is_rebal:
            if breadth_active:
                if use_vol_target:
                    if len(trailing_returns) >= 72:
                        realized_vol = np.std(trailing_returns[-168:]) * np.sqrt(BARS_PER_YEAR) + 1e-4
                        gross_target = float(np.clip(target_param / realized_vol, 0.75, 3.50))
                    else:
                        gross_target = 1.50
                else:
                    gross_target = target_param

                if use_trend_carry:
                    short_pool = valid_panel.filter(pl.col("ret_24h") <= 0.01).sort("tri_alpha_score", descending=False)
                    long_pool = valid_panel.filter(pl.col("ret_24h") >= -0.01).sort("tri_alpha_score", descending=True)
                    longs = long_pool.head(K_ENTRY)["symbol"].to_list()
                    shorts = short_pool.head(K_ENTRY)["symbol"].to_list()
                else:
                    sorted_alpha = valid_panel.sort("tri_alpha_score", descending=True)
                    all_ranked = sorted_alpha["symbol"].to_list()
                    rank_map = {s: i for i, s in enumerate(all_ranked)}
                    for s in all_ranked[:K_ENTRY]: active_longs.add(s)
                    for s in all_ranked[-K_ENTRY:]: active_shorts.add(s)
                    active_longs = {s for s in active_longs if rank_map.get(s, 999) < K_EXIT}
                    active_shorts = {s for s in active_shorts if rank_map.get(s, -1) >= (len(all_ranked) - K_EXIT)}
                    active_longs -= active_shorts
                    longs = list(active_longs)
                    shorts = list(active_shorts)

                active_syms = set(longs).union(shorts)

                if len(longs) >= 4 and len(shorts) >= 4:
                    inv_v = {s: 1.0 / max(0.015, safe_val(vols_map, s, 0.025)) for s in active_syms}
                    raw_w = {s: inv_v[s] if s in longs else -inv_v[s] for s in active_syms}
                    
                    l_beta = np.mean([safe_val(beta_map, s, 1.0) for s in longs])
                    s_beta = np.mean([safe_val(beta_map, s, 1.0) for s in shorts])
                    if s_beta > 0.1:
                        for s in shorts:
                            raw_w[s] *= (l_beta / s_beta)
                            
                    total_abs_w = sum(abs(w) for w in raw_w.values())
                    raw_target = {s: (w / total_abs_w) * gross_target for s, w in raw_w.items()}
                else:
                    raw_target = prev_w
            else:
                raw_target = {}
        else:
            raw_target = prev_w

        # Leland Deadband Execution
        dispatched = {}
        all_syms = set(prev_w.keys()).union(raw_target.keys())
        for s in all_syms:
            w_t = raw_target.get(s, 0.0)
            w_prev = prev_w.get(s, 0.0)
            sigma = max(0.015, safe_val(vols_map, s, 0.025))
            if abs(w_t) < 1e-4 or abs(w_prev) < 1e-4 or (w_t * w_prev < 0):
                dispatched[s] = w_t
                continue
            h_star = np.clip(((4.0 / 3.0) * (FEE_RATE * (sigma ** 2.0)) / GAMMA_MVO) ** (1.0 / 3.0) * 2.0, 0.015, 0.050)
            delta = w_t - w_prev
            dispatched[s] = (w_t - np.sign(delta) * h_star) if abs(delta) > h_star else w_prev

        dispatched = {s: w for s, w in dispatched.items() if abs(w) > 0.002}
        to = sum(abs(dispatched.get(s, 0.0) - prev_w.get(s, 0.0)) for s in all_syms)
        turnover += to
        cost = to * FEE_RATE

        fund_pnl = sum(-dispatched.get(s, 0.0) * safe_val(funding_map, s, 0.0) for s in dispatched)
        p_pnl = sum(dispatched.get(s, 0.0) * safe_val(returns_map, s, 0.0) for s in dispatched)
        net_pnl = p_pnl + fund_pnl - cost

        nav *= (1.0 + net_pnl)
        returns.append(net_pnl)
        trailing_returns.append(net_pnl)
        prev_w = dispatched

    # Metrics
    r = np.array(returns)
    n_bars = len(r)
    n_days = n_bars / 24.0
    mult = nav / 10_000.0
    cagr = (mult ** (365.25 / n_days) - 1.0) * 100.0 if mult > 0 else -100.0
    sharpe = np.mean(r) / (np.std(r) + 1e-6) * np.sqrt(BARS_PER_YEAR)
    cum = np.cumprod(1.0 + r)
    mdd = np.min((cum - np.maximum.accumulate(cum)) / np.maximum.accumulate(cum)) * 100.0
    geo_g = np.mean(np.log(np.maximum(1e-6, 1.0 + r))) * BARS_PER_YEAR
    ann_to = turnover * (365.25 / n_days)

    print(f"\n--- {label} ---")
    print(f"  Multiple: {mult:.2f}x  |  CAGR: {cagr:+,.1f}%  |  Sharpe: {sharpe:.2f}  |  MDD: {mdd:.1f}%")
    print(f"  Geo g: {geo_g:.2f}  |  Ann Turnover: {ann_to:,.0f}x  |  Bars: {n_bars:,} ({n_days:.1f} days)")

