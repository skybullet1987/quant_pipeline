import numpy as np
import polars as pl
from pathlib import Path

print("=" * 104)
print("   EXPERIMENT 15: TRI-ALPHA OPTIMAL WEIGHTING & 10x KELLY CALIBRATION")
print("=" * 104)

LAKE_PATH = Path.home() / "quant_pipeline" / "data" / "lake" / "features" / "pit_panel_1h_with_funding.parquet"
df = pl.read_parquet(LAKE_PATH)

if "group_id" not in df.columns:
    unique_ts = df.select("timestamp_ms").unique().sort("timestamp_ms").with_columns(
        pl.int_range(0, pl.len()).alias("group_id")
    )
    df = df.join(unique_ts, on="timestamp_ms", how="left")

BARS_PER_YEAR = 24 * 365
FEE_RATE = 0.00015
GAMMA_MVO = 0.05
K_ENTRY = 12
K_EXIT = 28
REBAL_CLOCK = 6
MMR_RATE = 0.040  # Hyperliquid 4.0% blended maintenance margin

# 1. Forward Returns
df = df.sort(["symbol", "group_id"]).with_columns([
    (pl.col("close").shift(-1).over("symbol") / pl.col("close") - 1.0).fill_null(0.0).alias("next_ret_1h")
])

# 2. Align BTC
btc = df.filter(pl.col("symbol") == "BTC").select([
    "group_id",
    pl.col("ret_4h").alias("btc_ret_4h"),
    pl.col("ret_12h").alias("btc_ret_12h"),
    pl.col("ret_72h").alias("btc_ret_72h")
]).unique(subset=["group_id"])
df = df.join(btc, on="group_id", how="left")

# 3. Construct the 3 Proven Alphas
# A0: Multi-Horizon Residual Momentum
df = df.with_columns([
    (
        -0.35 * ((pl.col("ret_4h") - pl.col("beta_btc") * pl.col("btc_ret_4h")) / (pl.col("vol_yang_zhang") + 1e-5))
        -0.25 * ((pl.col("ret_12h") - pl.col("beta_btc") * pl.col("btc_ret_12h")) / (pl.col("vol_yang_zhang") + 1e-5))
        +0.40 * ((pl.col("ret_72h") - pl.col("beta_btc") * pl.col("btc_ret_72h")) / (pl.col("vol_yang_zhang") + 1e-5))
    ).alias("raw_a0")
])

# A1: 1H Short-Term Liquidity Exhaustion
df = df.with_columns([
    (
        -1.0 * ((pl.col("ret_1h") - pl.col("beta_btc") * (pl.col("btc_ret_4h") / 4.0)) / (pl.col("vol_yang_zhang") + 1e-5))
        * (pl.col("volume_zscore_72h").clip(-1.0, 4.0) + 1.0)
    ).alias("raw_a1")
])

# A2: Funding Rate Velocity Divergence
df = df.with_columns([
    (
        -1.0 * (
            ((pl.col("funding_rate") - pl.col("funding_rate").rolling_mean(24).over("symbol")) /
             (pl.col("funding_rate").rolling_std(24).over("symbol") + 1e-6)).clip(-3.0, 3.0)
            - (pl.col("ret_24h") / (pl.col("vol_yang_zhang") * np.sqrt(24) + 1e-5)).clip(-3.0, 3.0)
        )
    ).alias("raw_a2")
])

# EWMA Smoothing
df = df.sort(["symbol", "group_id"]).with_columns([
    pl.col("raw_a0").ewm_mean(span=6).over("symbol").alias("a0_smooth"),
    pl.col("raw_a1").ewm_mean(span=2).over("symbol").alias("a1_smooth"),
    pl.col("raw_a2").ewm_mean(span=4).over("symbol").alias("a2_smooth")
])

# Standardize cross-sectionally per group
for col, zcol in [("a0_smooth", "z_a0"), ("a1_smooth", "z_a1"), ("a2_smooth", "z_a2")]:
    df = df.with_columns([
        ((pl.col(col) - pl.col(col).mean().over("group_id")) / (pl.col(col).std().over("group_id") + 1e-5)).alias(zcol)
    ])

# Ensembles:
df = df.with_columns([
    # Heuristic Tri-Alpha
    (0.55 * pl.col("z_a0") + 0.25 * pl.col("z_a1") + 0.20 * pl.col("z_a2")).alias("ens_tri_heuristic"),
    # Equal-Risk Contribution (Balanced 40 / 30 / 30)
    (0.40 * pl.col("z_a0") + 0.30 * pl.col("z_a1") + 0.30 * pl.col("z_a2")).alias("ens_tri_balanced"),
    # Momentum-Tilted (60 / 20 / 20)
    (0.60 * pl.col("z_a0") + 0.20 * pl.col("z_a1") + 0.20 * pl.col("z_a2")).alias("ens_tri_mom_tilt")
])

# Cross-Sectional Dispersion & Breadth
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
    ("1. Tri-Alpha Baseline (Heuristic, Cap 4.5x)", "ens_tri_heuristic", 4.50, 450.0),
    ("2. Tri-Alpha Balanced (40/30/30, Cap 4.5x)",   "ens_tri_balanced",  4.50, 450.0),
    ("3. Tri-Alpha Convex Sizing (Cap 5.2x)",        "ens_tri_heuristic", 5.20, 550.0),
    ("4. Tri-Alpha 10x Kelly Target (Cap 5.8x)",     "ens_tri_heuristic", 5.80, 650.0),
    ("5. Tri-Alpha Max Capacity (Cap 6.2x)",         "ens_tri_heuristic", 6.20, 700.0)
]

results = []

for label, col_name, max_lev, slope in CONFIGS:
    nav = 10_000.0
    turnover = 0.0
    prev_w = {}
    active_longs = set()
    active_shorts = set()
    returns = []
    min_margin_cushion = 1.0

    for idx, grp in enumerate(all_active_grps[:-1]):
        cur_panel = df.filter(pl.col("group_id") == grp)
        valid_panel = cur_panel.filter(
            (pl.col("dollar_volume_1h") > 25_000) &
            pl.col("vol_yang_zhang").is_not_null() &
            pl.col(col_name).is_not_null() &
            pl.col("funding_rate").is_not_null()
        )
        n_avail = valid_panel.height

        returns_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["next_ret_1h"].to_list()))
        funding_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["funding_rate"].to_list()))
        vols_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["vol_yang_zhang"].to_list()))

        delta_disp = float(valid_panel["delta_disp_24h"][0]) if n_avail >= 12 else -1.0
        breadth_active = (n_avail >= 35) and (delta_disp > -0.001)

        is_rebal = (idx % REBAL_CLOCK == 0)
        if is_rebal:
            if breadth_active:
                gross_target = float(np.clip(1.20 + slope * delta_disp, 0.0, max_lev))
                sorted_alpha = valid_panel.sort(col_name, descending=True)
                all_ranked = sorted_alpha["symbol"].to_list()
                rank_map = {s: i for i, s in enumerate(all_ranked)}

                for s in all_ranked[:K_ENTRY]: active_longs.add(s)
                for s in all_ranked[-K_ENTRY:]: active_shorts.add(s)
                active_longs = {s for s in active_longs if rank_map.get(s, 999) < K_EXIT}
                active_shorts = {s for s in active_shorts if rank_map.get(s, -1) >= (len(all_ranked) - K_EXIT)}
                active_longs -= active_shorts
                active_syms = active_longs.union(active_shorts)

                if len(active_syms) >= 16:
                    inv_v = {s: 1.0 / max(0.015, safe_val(vols_map, s, 0.025)) for s in active_syms}
                    raw_w = {s: inv_v[s] if s in active_longs else -inv_v[s] for s in active_syms}
                    l_sum = sum(w for w in raw_w.values() if w > 0)
                    s_sum = sum(abs(w) for w in raw_w.values() if w < 0)
                    target_leg = gross_target / 2.0
                    raw_target = {}
                    for s in raw_w:
                        if raw_w[s] > 0 and l_sum > 0: raw_target[s] = (raw_w[s] / l_sum) * target_leg
                        elif raw_w[s] < 0 and s_sum > 0: raw_target[s] = (raw_w[s] / s_sum) * target_leg
                else:
                    raw_target = prev_w
            else:
                raw_target = {}
        else:
            raw_target = prev_w

        dispatched = {}
        all_syms = set(prev_w.keys()).union(raw_target.keys())
        for s in all_syms:
            w_t = raw_target.get(s, 0.0)
            w_prev = prev_w.get(s, 0.0)
            sigma = max(0.015, safe_val(vols_map, s, 0.025))
            if abs(w_t) < 1e-4 or abs(w_prev) < 1e-4 or (w_t * w_prev < 0):
                dispatched[s] = w_t
                continue
            h_star = np.clip(((4.0 / 3.0) * (FEE_RATE * (sigma ** 2.0)) / GAMMA_MVO) ** (1.0 / 3.0) * 2.0, 0.020, 0.065)
            delta = w_t - w_prev
            dispatched[s] = (w_t - np.sign(delta) * h_star) if abs(delta) > h_star else w_prev

        dispatched = {s: w for s, w in dispatched.items() if abs(w) > 0.002}
        to = sum(abs(dispatched.get(s, 0.0) - prev_w.get(s, 0.0)) for s in all_syms)
        turnover += to
        cost = to * FEE_RATE

        fund_pnl = sum(-dispatched.get(s, 0.0) * safe_val(funding_map, s, 0.0) for s in dispatched)
        p_pnl = sum(dispatched.get(s, 0.0) * safe_val(returns_map, s, 0.0) for s in dispatched)
        net_pnl = p_pnl + fund_pnl - cost

        gross_exposure = sum(abs(w) for w in dispatched.values())
        if gross_exposure > 0.1:
            cushion = (1.0 + net_pnl) - (gross_exposure * MMR_RATE)
            min_margin_cushion = min(min_margin_cushion, cushion)

        nav *= (1.0 + net_pnl)
        returns.append(net_pnl)
        prev_w = dispatched

    r = np.array(returns)
    ann_mult = BARS_PER_YEAR / len(r)
    cagr = (nav / 10_000.0) ** ann_mult - 1.0
    sharpe = np.mean(r) / (np.std(r) + 1e-6) * np.sqrt(BARS_PER_YEAR)
    cum = np.cumprod(1.0 + r)
    mdd = np.min((cum - np.maximum.accumulate(cum)) / np.maximum.accumulate(cum))
    geo_g = np.mean(np.log(1.0 + r)) * BARS_PER_YEAR
    vol = np.std(r) * np.sqrt(BARS_PER_YEAR)

    # Last 68.1 days (OOS)
    b_size = len(returns) // 3
    r_oos = np.array(returns[2*b_size:])
    ann_b = BARS_PER_YEAR / len(r_oos)
    cagr_oos = (np.prod(1.0 + r_oos)) ** ann_b - 1.0
    mult_oos = np.prod(1.0 + r_oos)

    results.append({
        "name": label,
        "cagr": cagr,
        "sharpe": sharpe,
        "vol": vol,
        "mdd": mdd,
        "mult": nav / 10_000.0,
        "geo_g": geo_g,
        "cushion": min_margin_cushion * 100,
        "oos_mult": mult_oos,
        "oos_cagr": cagr_oos
    })

print("=" * 104)
print("             EXPERIMENT 15 RESULTS: TRI-ALPHA 10x KELLY CALIBRATION")
print("=" * 104)
print(f"{'Configuration':<42} | {'CAGR':<10} | {'Sharpe':<8} | {'Vol':<8} | {'MDD':<8} | {'Mult':<8} | {'Geo g':<8} | {'Min Cush':<9}")
print("-" * 104)
for res in results:
    print(f"{res['name']:<42} | {res['cagr']*100:>+8.1f}% | {res['sharpe']:>8.2f} | {res['vol']*100:>7.1f}% | {res['mdd']*100:>7.1f}% | {res['mult']:>6.2f}x | {res['geo_g']:>8.2f} | {res['cushion']:>7.1f}%")

print("\n" + "=" * 104)
print("             OUT-OF-SAMPLE (LAST 68.1 DAYS) VERIFICATION")
print("=" * 104)
print(f"{'Configuration':<42} | {'OOS Multiple':<14} | {'OOS CAGR':<12}")
print("-" * 104)
for res in results:
    print(f"{res['name']:<42} | {res['oos_mult']:>12.2f}x | {res['oos_cagr']*100:>+10.1f}%")
print("=" * 104)
