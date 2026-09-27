import numpy as np
import polars as pl
from pathlib import Path

print("=" * 96)
print("   EXPERIMENT 4: CROSS-SECTIONAL DISPERSION SURFACE & A0 EDGE MAPPING")
print("=" * 96)

LAKE_PATH = Path.home() / "quant_pipeline" / "data" / "lake" / "features" / "pit_panel_1h_with_funding.parquet"
df = pl.read_parquet(LAKE_PATH)

if "group_id" not in df.columns:
    unique_ts = df.select("timestamp_ms").unique().sort("timestamp_ms").with_columns(
        pl.int_range(0, pl.len()).alias("group_id")
    )
    df = df.join(unique_ts, on="timestamp_ms", how="left")

BARS_PER_YEAR = 24 * 365
K_ENTRY = 12
K_EXIT = 28

# 1. Forward returns
df = df.sort(["symbol", "group_id"]).with_columns([
    (pl.col("close").shift(-1).over("symbol") / pl.col("close") - 1.0).fill_null(0.0).alias("next_ret_1h"),
    (pl.col("close").shift(-4).over("symbol") / pl.col("close") - 1.0).fill_null(0.0).alias("fwd_ret_4h")
])

# 2. Align BTC
btc = df.filter(pl.col("symbol") == "BTC").select([
    "group_id", pl.col("ret_4h").alias("btc_ret_4h"), pl.col("ret_12h").alias("btc_ret_12h"), pl.col("ret_72h").alias("btc_ret_72h")
]).unique(subset=["group_id"])
df = df.join(btc, on="group_id", how="left")

# 3. Composite A0 Alpha
df = df.with_columns([
    (
        -0.35 * ((pl.col("ret_4h") - pl.col("beta_btc") * pl.col("btc_ret_4h")) / (pl.col("vol_yang_zhang") + 1e-5))
        -0.25 * ((pl.col("ret_12h") - pl.col("beta_btc") * pl.col("btc_ret_12h")) / (pl.col("vol_yang_zhang") + 1e-5))
        +0.40 * ((pl.col("ret_72h") - pl.col("beta_btc") * pl.col("btc_ret_72h")) / (pl.col("vol_yang_zhang") + 1e-5))
    ).alias("raw_a0")
])
df = df.sort(["symbol", "group_id"]).with_columns([
    pl.col("raw_a0").ewm_mean(span=6).over("symbol").alias("a0_smoothed")
])

# 4. Vectorized Cross-Sectional Dispersion Calculation
print("[+] Computing vectorized cross-sectional dispersion...")
df_disp = (
    df.filter((pl.col("dollar_volume_1h") > 25_000) & pl.col("ret_72h").is_not_null())
    .group_by("group_id")
    .agg([
        pl.col("ret_72h").std().alias("cs_disp_72h"),
        pl.len().alias("count")
    ])
    .filter(pl.col("count") >= 35)
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
active_grps = sorted(df["group_id"].unique().to_list())

def safe_val(d, k, default=0.0):
    v = d.get(k)
    if v is None: return default
    try:
        f = float(v)
        return default if np.isnan(f) else f
    except:
        return default

bar_results = []
active_longs = set()
active_shorts = set()

print(f"[+] Mapping A0 alpha forward performance across {len(active_grps) // 4:,} 4H decision steps...")
for idx in range(0, len(active_grps) - 4, 4):
    grp = active_grps[idx]
    cur_panel = df.filter(pl.col("group_id") == grp)
    valid_panel = cur_panel.filter(
        (pl.col("dollar_volume_1h") > 25_000) &
        pl.col("vol_yang_zhang").is_not_null() &
        pl.col("a0_smoothed").is_not_null()
    )
    if valid_panel.height < 35:
        continue

    cs_disp = float(valid_panel["cs_disp_72h"][0])
    delta_disp = float(valid_panel["delta_disp_24h"][0])

    vols_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["vol_yang_zhang"].to_list()))
    sorted_a0 = valid_panel.sort("a0_smoothed", descending=True)
    all_ranked = sorted_a0["symbol"].to_list()
    rank_map = {s: i for i, s in enumerate(all_ranked)}

    for s in all_ranked[:K_ENTRY]: active_longs.add(s)
    for s in all_ranked[-K_ENTRY:]: active_shorts.add(s)
    active_longs = {s for s in active_longs if rank_map.get(s, 999) < K_EXIT}
    active_shorts = {s for s in active_shorts if rank_map.get(s, -1) >= (len(all_ranked) - K_EXIT)}
    active_longs -= active_shorts
    active_syms = active_longs.union(active_shorts)

    if len(active_syms) < 16:
        continue

    inv_v = {s: 1.0 / max(0.015, safe_val(vols_map, s, 0.025)) for s in active_syms}
    raw_w = {s: inv_v[s] if s in active_longs else -inv_v[s] for s in active_syms}
    l_sum = sum(w for w in raw_w.values() if w > 0)
    s_sum = sum(abs(w) for w in raw_w.values() if w < 0)

    # 1.0x baseline reference sizing
    w_norm = {}
    for s in raw_w:
        if raw_w[s] > 0 and l_sum > 0: w_norm[s] = (raw_w[s] / l_sum) * 0.50
        elif raw_w[s] < 0 and s_sum > 0: w_norm[s] = (raw_w[s] / s_sum) * 0.50

    fwd_ret_map = dict(zip(valid_panel["symbol"].to_list(), valid_panel["fwd_ret_4h"].to_list()))
    gross_4h = sum(w_norm.get(s, 0.0) * safe_val(fwd_ret_map, s, 0.0) for s in w_norm)

    bar_results.append({
        "group_id": grp,
        "cs_disp": cs_disp,
        "delta_disp": delta_disp,
        "gross_4h": gross_4h
    })

res_df = pl.DataFrame(bar_results)

# 5. Partition by Dispersion Quintiles
q_disp = [
    res_df["cs_disp"].quantile(0.20),
    res_df["cs_disp"].quantile(0.40),
    res_df["cs_disp"].quantile(0.60),
    res_df["cs_disp"].quantile(0.80)
]

print("\n" + "=" * 96)
print("1. A0 ALPHA PERFORMANCE BY DISPERSION LEVEL (72H CROSS-SECTIONAL STD)")
print("=" * 96)
print(f"{'Dispersion Bucket':<25} | {'Range':<18} | {'N (4H Bars)':<12} | {'Mean 4H PnL':<14} | {'Sharpe (Ann)':<12} | {'Win Rate':<10}")
print("-" * 96)

ranges = [
    ("Q1: Severe Compression", 0.0, q_disp[0]),
    ("Q2: Low Dispersion", q_disp[0], q_disp[1]),
    ("Q3: Normal Dispersion", q_disp[1], q_disp[2]),
    ("Q4: Elevated Dispersion", q_disp[2], q_disp[3]),
    ("Q5: Extreme Dislocation", q_disp[3], 1.0)
]

for name, low, high in ranges:
    sub = res_df.filter((pl.col("cs_disp") >= low) & (pl.col("cs_disp") < high))
    rets = sub["gross_4h"].to_numpy()
    if len(rets) == 0: continue
    mean_pnl = np.mean(rets)
    std_pnl = np.std(rets) + 1e-6
    sharpe = (mean_pnl / std_pnl) * np.sqrt(BARS_PER_YEAR / 4)
    win_rate = np.mean(rets > 0) * 100
    print(f"{name:<25} | {low*100:>5.1f}% - {high*100:>5.1f}%   | {len(sub):>12} | {mean_pnl*100:>+12.3f}% | {sharpe:>12.2f} | {win_rate:>9.1f}%")

# 6. Partition by 24H Dispersion Acceleration
print("\n" + "=" * 96)
print("2. A0 ALPHA PERFORMANCE BY DISPERSION VELOCITY (EXPANDING vs CONTRACTING)")
print("=" * 96)
expanding = res_df.filter(pl.col("delta_disp") > 0.002)
flat = res_df.filter((pl.col("delta_disp") >= -0.002) & (pl.col("delta_disp") <= 0.002))
contracting = res_df.filter(pl.col("delta_disp") < -0.002)

for name, sub in [("Expanding (+Δσ)", expanding), ("Neutral Chop (Δσ ≈ 0)", flat), ("Contracting (-Δσ)", contracting)]:
    rets = sub["gross_4h"].to_numpy()
    if len(rets) == 0: continue
    mean_pnl = np.mean(rets)
    std_pnl = np.std(rets) + 1e-6
    sharpe = (mean_pnl / std_pnl) * np.sqrt(BARS_PER_YEAR / 4)
    win_rate = np.mean(rets > 0) * 100
    print(f"{name:<25} | N = {len(sub):>4} bars | Mean 4H: {mean_pnl*100:>+6.3f}% | Sharpe: {sharpe:>6.2f} | Win Rate: {win_rate:>5.1f}%")

print("=" * 96)
