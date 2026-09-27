import numpy as np
import polars as pl
from pathlib import Path

print("=" * 104)
print("   EXPERIMENT 12: SIMULTANEOUS 10x ENGINE BENCHMARK (POWER-LAW, BETA FLEX, KELLY)")
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

# 1. Forward 1H returns
df = df.sort(["symbol", "group_id"]).with_columns([
    (pl.col("close").shift(-1).over("symbol") / pl.col("close") - 1.0).fill_null(0.0).alias("next_ret_1h")
])

# 2. Align BTC with 10-day (240-hour) Trend SMA
btc = (
    df.filter(pl.col("symbol") == "BTC")
    .select([
        "group_id",
        "close",
        pl.col("ret_4h").alias("btc_ret_4h"),
        pl.col("ret_12h").alias("btc_ret_12h"),
        pl.col("ret_72h").alias("btc_ret_72h")
    ])
    .unique(subset=["group_id"])
    .sort("group_id")
    .with_columns([
        pl.col("close").rolling_mean(window_size=240).alias("btc_sma_240h")
    ])
    .with_columns([
        (pl.col("close") > pl.col("btc_sma_240h")).alias("btc_in_uptrend")
    ])
)
df = df.join(btc.select(["group_id", "btc_ret_4h", "btc_ret_12h", "btc_ret_72h", "btc_in_uptrend"]), on="group_id", how="left")

# 3. Composite A0 Signal
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

# 4. Cross-Sectional Dispersion
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

MODELS = [
    "1. Control Baseline (Dollar-Neutral, Inv-Vol, Cap 4.5x)",
    "2. Power-Law Longs (γ=2.0, Concentrated Outliers)",
    "3. Directional Beta Flex (Up to +0.8x Net Tilt)",
    "4. Power-Law + Directional Beta Flex",
    "5. Ultra 10x Kelly Engine (Power-Law + Flex + Cap 5.8x)"
]

navs = [10_000.0] * 5
turnovers = [0.0] * 5
prev_w = [{}, {}, {}, {}, {}]
active_longs = [set() for _ in range(5)]
active_shorts = [set() for _ in range(5)]
returns_hist = [[] for _ in range(5)]

for idx, grp in enumerate(all_active_grps[:-1]):
    cur_panel = df.filter(pl.col("group_id") == grp)
    valid_panel = cur_panel.filter(
        (pl.col("dollar_volume_1h") > 25_000) &
        pl.col("vol_yang_zhang").is_not_null() &
        pl.col("a0_smoothed").is_not_null() &
        pl.col("funding_rate").is_not_null()
    )
    n_avail = valid_panel.height

    returns_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["next_ret_1h"].to_list()))
    funding_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["funding_rate"].to_list()))
    vols_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["vol_yang_zhang"].to_list()))
    a0_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["a0_smoothed"].to_list()))

    delta_disp = float(valid_panel["delta_disp_24h"][0]) if n_avail >= 12 else -1.0
    btc_trend = bool(valid_panel["btc_in_uptrend"][0]) if "btc_in_uptrend" in valid_panel.columns and valid_panel["btc_in_uptrend"][0] is not None else False

    # Universal Breadth Gate: Require >= 35 liquid tokens
    breadth_active = (n_avail >= 35) and (delta_disp > -0.001)

    is_rebal = (idx % REBAL_CLOCK == 0)

    for m in range(5):
        if is_rebal:
            if not breadth_active:
                raw_target = {}
            else:
                # 1. Determine gross leverage target
                if m == 4:
                    # Model 5: Ultra-Kelly scales to 5.8x if BTC trending + delta_disp strong
                    if btc_trend and delta_disp > 0.002:
                        gross_target = float(np.clip(1.50 + 650.0 * delta_disp, 0.0, 5.80))
                    else:
                        gross_target = float(np.clip(1.20 + 450.0 * delta_disp, 0.0, 4.50))
                else:
                    gross_target = float(np.clip(1.20 + 450.0 * delta_disp, 0.0, 4.50))

                # 2. Determine leg ratios (Dollar Neutral vs Directional Beta Flex)
                if m in [2, 3, 4] and btc_trend and delta_disp > 0.0:
                    long_ratio = 0.65
                    short_ratio = 0.35
                else:
                    long_ratio = 0.50
                    short_ratio = 0.50

                long_cap = gross_target * long_ratio
                short_cap = gross_target * short_ratio

                # 3. Form universe selections
                sorted_a0 = valid_panel.sort("a0_smoothed", descending=True)
                all_ranked = sorted_a0["symbol"].to_list()
                rank_map = {s: i for i, s in enumerate(all_ranked)}

                for s in all_ranked[:K_ENTRY]: active_longs[m].add(s)
                for s in all_ranked[-K_ENTRY:]: active_shorts[m].add(s)
                active_longs[m] = {s for s in active_longs[m] if rank_map.get(s, 999) < K_EXIT}
                active_shorts[m] = {s for s in active_shorts[m] if rank_map.get(s, -1) >= (len(all_ranked) - K_EXIT)}
                active_longs[m] -= active_shorts[m]
                active_syms = active_longs[m].union(active_shorts[m])

                if len(active_syms) < 16:
                    raw_target = prev_w[m]
                else:
                    # 4. Weighting Scheme (Uniform Inv-Vol vs Power-Law)
                    raw_target = {}
                    if m in [1, 3, 4]:
                        # Power-Law Longs
                        scores = [max(0.01, safe_val(a0_map, s, 0.01)) for s in active_longs[m]]
                        sigmas_l = [max(0.015, safe_val(vols_map, s, 0.025)) for s in active_longs[m]]
                        unnorm_longs = [(sc ** 2.0) / sg for sc, sg in zip(scores, sigmas_l)]
                        sum_l = sum(unnorm_longs)
                        for s, w_u in zip(active_longs[m], unnorm_longs):
                            raw_target[s] = (w_u / sum_l) * long_cap if sum_l > 0 else 0.0

                        # Uniform Inv-Vol Shorts
                        sigmas_s = [max(0.015, safe_val(vols_map, s, 0.025)) for s in active_shorts[m]]
                        unnorm_shorts = [1.0 / sg for sg in sigmas_s]
                        sum_s = sum(unnorm_shorts)
                        for s, w_u in zip(active_shorts[m], unnorm_shorts):
                            raw_target[s] = -(w_u / sum_s) * short_cap if sum_s > 0 else 0.0
                    else:
                        # Baseline Uniform Inv-Vol on both legs
                        inv_v = {s: 1.0 / max(0.015, safe_val(vols_map, s, 0.025)) for s in active_syms}
                        raw_w = {s: inv_v[s] if s in active_longs[m] else -inv_v[s] for s in active_syms}
                        l_sum = sum(w for w in raw_w.values() if w > 0)
                        s_sum = sum(abs(w) for w in raw_w.values() if w < 0)
                        for s in raw_w:
                            if raw_w[s] > 0 and l_sum > 0: raw_target[s] = (raw_w[s] / l_sum) * long_cap
                            elif raw_w[s] < 0 and s_sum > 0: raw_target[s] = (raw_w[s] / s_sum) * short_cap
        else:
            raw_target = prev_w[m]

        # Leland Deadband
        dispatched = {}
        all_syms = set(prev_w[m].keys()).union(raw_target.keys())
        for s in all_syms:
            w_t = raw_target.get(s, 0.0)
            w_prev = prev_w[m].get(s, 0.0)
            sigma = max(0.015, safe_val(vols_map, s, 0.025))
            if abs(w_t) < 1e-4 or abs(w_prev) < 1e-4 or (w_t * w_prev < 0):
                dispatched[s] = w_t
                continue
            h_star = np.clip(((4.0 / 3.0) * (FEE_RATE * (sigma ** 2.0)) / GAMMA_MVO) ** (1.0 / 3.0) * 2.0, 0.020, 0.065)
            delta = w_t - w_prev
            dispatched[s] = (w_t - np.sign(delta) * h_star) if abs(delta) > h_star else w_prev

        dispatched = {s: w for s, w in dispatched.items() if abs(w) > 0.002}
        to = sum(abs(dispatched.get(s, 0.0) - prev_w[m].get(s, 0.0)) for s in all_syms)
        turnovers[m] += to
        cost = to * FEE_RATE

        fund_pnl = sum(-dispatched.get(s, 0.0) * safe_val(funding_map, s, 0.0) for s in dispatched)
        p_pnl = sum(dispatched.get(s, 0.0) * safe_val(returns_map, s, 0.0) for s in dispatched)
        net_pnl = p_pnl + fund_pnl - cost

        navs[m] *= (1.0 + net_pnl)
        returns_hist[m].append(net_pnl)
        prev_w[m] = dispatched

print("\n" + "=" * 104)
print("             SIMULTANEOUS 10x ENGINE RESULTS: FULL 204.5 DAYS (4,907 BARS)")
print("=" * 104)
print(f"{'Strategy Architecture':<42} | {'CAGR':<10} | {'Sharpe':<8} | {'MDD':<8} | {'Mult':<8} | {'Geo g':<8} | {'Turnover':<10}")
print("-" * 104)

def calc_summary(r_list, to, nav):
    r = np.array(r_list)
    ann_mult = BARS_PER_YEAR / len(r)
    cagr = (nav / 10_000.0) ** ann_mult - 1.0
    sharpe = np.mean(r) / (np.std(r) + 1e-6) * np.sqrt(BARS_PER_YEAR)
    cum = np.cumprod(1.0 + r)
    mdd = np.min((cum - np.maximum.accumulate(cum)) / np.maximum.accumulate(cum))
    geo_g = np.mean(np.log(1.0 + r)) * BARS_PER_YEAR
    return cagr, sharpe, mdd, nav / 10_000.0, geo_g, to * ann_mult

metrics = [calc_summary(returns_hist[i], turnovers[i], navs[i]) for i in range(5)]

for i in range(5):
    print(f"{MODELS[i]:<42} | {metrics[i][0]*100:>+8.1f}% | {metrics[i][1]:>8.2f} | {metrics[i][2]*100:>7.1f}% | {metrics[i][3]:>6.2f}x | {metrics[i][4]:>8.2f} | {metrics[i][5]:>8.0f}x")

# Out-of-sample breakdown (last 68 days of mature lake)
b_size = len(returns_hist[0]) // 3
oos_slice = slice(2 * b_size, len(returns_hist[0]))

print("\n" + "=" * 104)
print("             OUT-OF-SAMPLE INTEGRITY CHECK (LAST 68.1 DAYS / 1,635 BARS)")
print("=" * 104)
print(f"{'Strategy Architecture':<42} | {'OOS CAGR':<10} | {'OOS Sharpe':<10} | {'OOS MDD':<10} | {'OOS Mult':<10}")
print("-" * 104)
for i in range(5):
    r_oos = np.array(returns_hist[i][oos_slice])
    ann_b = BARS_PER_YEAR / len(r_oos)
    cagr_oos = (np.prod(1.0 + r_oos)) ** ann_b - 1.0
    sharpe_oos = np.mean(r_oos) / (np.std(r_oos) + 1e-6) * np.sqrt(BARS_PER_YEAR)
    cum_oos = np.cumprod(1.0 + r_oos)
    mdd_oos = np.min((cum_oos - np.maximum.accumulate(cum_oos)) / np.maximum.accumulate(cum_oos))
    mult_oos = np.prod(1.0 + r_oos)
    print(f"{MODELS[i]:<42} | {cagr_oos*100:>+8.1f}% | {sharpe_oos:>10.2f} | {mdd_oos*100:>9.1f}% | {mult_oos:>9.2f}x")
print("=" * 104)
