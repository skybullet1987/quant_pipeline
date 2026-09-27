import numpy as np
import polars as pl
from pathlib import Path

print("=" * 104)
print("   EXPERIMENT 17: ELIMINATING A2 KNIFE-CATCHING (DUAL VS ASYMMETRIC VS GATED)")
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
MAX_LEV = 5.2

# 1. Forward Returns
df = df.sort(["symbol", "group_id"]).with_columns([
    (pl.col("close").shift(-1).over("symbol") / pl.col("close") - 1.0).fill_null(0.0).alias("next_ret_1h")
])

# 2. Align BTC
btc = (
    df.filter(pl.col("symbol") == "BTC")
    .select([
        "group_id", "close",
        pl.col("ret_4h").alias("btc_ret_4h"),
        pl.col("ret_12h").alias("btc_ret_12h"),
        pl.col("ret_72h").alias("btc_ret_72h")
    ])
    .unique(subset=["group_id"])
    .sort("group_id")
    .with_columns([
        pl.col("close").rolling_mean(240).alias("btc_sma_240h")
    ])
    .with_columns([
        (pl.col("close") > pl.col("btc_sma_240h")).alias("btc_uptrend")
    ])
)
df = df.join(btc.select(["group_id", "btc_ret_4h", "btc_ret_12h", "btc_ret_72h", "btc_uptrend"]), on="group_id", how="left")

# 3. Market-wide funding regime
mkt_funding = (
    df.filter(pl.col("funding_rate").is_not_null())
    .group_by("group_id")
    .agg(pl.col("funding_rate").median().alias("mkt_median_funding"))
)
df = df.join(mkt_funding, on="group_id", how="left")

# 4. Alpha Construction
df = df.with_columns([
    # A0: Multi-Horizon Residual Momentum
    (
        -0.35 * ((pl.col("ret_4h") - pl.col("beta_btc") * pl.col("btc_ret_4h")) / (pl.col("vol_yang_zhang") + 1e-5))
        -0.25 * ((pl.col("ret_12h") - pl.col("beta_btc") * pl.col("btc_ret_12h")) / (pl.col("vol_yang_zhang") + 1e-5))
        +0.40 * ((pl.col("ret_72h") - pl.col("beta_btc") * pl.col("btc_ret_72h")) / (pl.col("vol_yang_zhang") + 1e-5))
    ).alias("raw_a0"),
    # A1: Short-Term Liquidity Exhaustion
    (
        -1.0 * ((pl.col("ret_1h") - pl.col("beta_btc") * (pl.col("btc_ret_4h") / 4.0)) / (pl.col("vol_yang_zhang") + 1e-5))
        * (pl.col("volume_zscore_72h").clip(-1.0, 4.0) + 1.0)
    ).alias("raw_a1"),
    # A2 Unconditioned
    (
        -1.0 * (
            ((pl.col("funding_rate") - pl.col("funding_rate").rolling_mean(24).over("symbol")) /
             (pl.col("funding_rate").rolling_std(24).over("symbol") + 1e-6)).clip(-3.0, 3.0)
            - (pl.col("ret_24h") / (pl.col("vol_yang_zhang") * np.sqrt(24) + 1e-5)).clip(-3.0, 3.0)
        )
    ).alias("raw_a2_uncond"),
    # A2 Asymmetric: Only fade crowded longs (clip funding z to >= 0)
    (
        -1.0 * (
            ((pl.col("funding_rate") - pl.col("funding_rate").rolling_mean(24).over("symbol")) /
             (pl.col("funding_rate").rolling_std(24).over("symbol") + 1e-6)).clip(0.0, 3.0)
            - (pl.col("ret_24h") / (pl.col("vol_yang_zhang") * np.sqrt(24) + 1e-5)).clip(-3.0, 3.0)
        )
    ).alias("raw_a2_asym")
])

# Smooth & Standardize
df = df.sort(["symbol", "group_id"]).with_columns([
    pl.col("raw_a0").ewm_mean(span=6).over("symbol").alias("a0_smooth"),
    pl.col("raw_a1").ewm_mean(span=2).over("symbol").alias("a1_smooth"),
    pl.col("raw_a2_uncond").ewm_mean(span=4).over("symbol").alias("a2_uncond_smooth"),
    pl.col("raw_a2_asym").ewm_mean(span=4).over("symbol").alias("a2_asym_smooth")
])

for col, zcol in [
    ("a0_smooth", "z_a0"),
    ("a1_smooth", "z_a1"),
    ("a2_uncond_smooth", "z_a2_uncond"),
    ("a2_asym_smooth", "z_a2_asym")
]:
    df = df.with_columns([
        ((pl.col(col) - pl.col(col).mean().over("group_id")) / (pl.col(col).std().over("group_id") + 1e-5)).alias(zcol)
    ])

# Multi-Alpha Signal Candidates:
df = df.with_columns([
    # 1. Unconditioned Tri-Alpha Baseline
    (0.40 * pl.col("z_a0") + 0.30 * pl.col("z_a1") + 0.30 * pl.col("z_a2_uncond")).alias("ens_tri_uncond"),
    # 2. Dual Alpha (Pure Momentum + Exhaustion, Zero A2)
    (0.55 * pl.col("z_a0") + 0.45 * pl.col("z_a1")).alias("ens_dual_pure"),
    # 3. Asymmetric Tri-Alpha (A2 never catches negative funding knives)
    (0.45 * pl.col("z_a0") + 0.35 * pl.col("z_a1") + 0.20 * pl.col("z_a2_asym")).alias("ens_tri_asym"),
    # 4. Regime-Gated Tri-Alpha (A2 muted when market median funding < 0 or BTC in downtrend)
    pl.when((pl.col("mkt_median_funding") > 0) & (pl.col("btc_uptrend") == True))
    .then(0.40 * pl.col("z_a0") + 0.30 * pl.col("z_a1") + 0.30 * pl.col("z_a2_uncond"))
    .otherwise(0.55 * pl.col("z_a0") + 0.45 * pl.col("z_a1"))
    .alias("ens_tri_gated")
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
fold1_cutoff = len(all_active_grps) // 4

def safe_val(d, k, default=0.0):
    v = d.get(k)
    if v is None: return default
    try:
        f = float(v)
        return default if np.isnan(f) else f
    except:
        return default

MODELS = [
    ("1. Baseline Tri-Alpha (Unconditioned)", "ens_tri_uncond"),
    ("2. Dual Alpha Pure (55% A0 + 45% A1)", "ens_dual_pure"),
    ("3. Asymmetric Tri-Alpha (Fade Crowded Longs Only)", "ens_tri_asym"),
    ("4. Regime-Gated Tri-Alpha (A2 Muted in Downtrend)", "ens_tri_gated")
]

def simulate_engine(col_name):
    nav = 10_000.0
    turnover = 0.0
    prev_w = {}
    active_longs = set()
    active_shorts = set()
    returns = []

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
                gross_target = float(np.clip(1.20 + 550.0 * delta_disp, 0.0, MAX_LEV))
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

        nav *= (1.0 + net_pnl)
        returns.append(net_pnl)
        prev_w = dispatched

    # Full stats
    r = np.array(returns)
    ann_mult = BARS_PER_YEAR / len(r)
    cagr = (nav / 10_000.0) ** ann_mult - 1.0
    sharpe = np.mean(r) / (np.std(r) + 1e-6) * np.sqrt(BARS_PER_YEAR)
    cum = np.cumprod(1.0 + r)
    mdd = np.min((cum - np.maximum.accumulate(cum)) / np.maximum.accumulate(cum))
    geo_g = np.mean(np.log(1.0 + r)) * BARS_PER_YEAR

    # Fold 1 stats
    r_f1 = r[:fold1_cutoff]
    ann_f1 = BARS_PER_YEAR / len(r_f1)
    cagr_f1 = (np.prod(1.0 + r_f1)) ** ann_f1 - 1.0
    sharpe_f1 = np.mean(r_f1) / (np.std(r_f1) + 1e-6) * np.sqrt(BARS_PER_YEAR)
    cum_f1 = np.cumprod(1.0 + r_f1)
    mdd_f1 = np.min((cum_f1 - np.maximum.accumulate(cum_f1)) / np.maximum.accumulate(cum_f1))
    mult_f1 = np.prod(1.0 + r_f1)

    return {
        "full_cagr": cagr, "full_sharpe": sharpe, "full_mdd": mdd, "full_mult": nav / 10_000.0, "full_g": geo_g,
        "f1_cagr": cagr_f1, "f1_sharpe": sharpe_f1, "f1_mdd": mdd_f1, "f1_mult": mult_f1
    }

print("\n" + "=" * 104)
print("             1. FULL 204.5-DAY PORTFOLIO COMPOUNDING (THE 10x MANDATE)")
print("=" * 104)
print(f"{'Strategy Configuration':<44} | {'CAGR':<10} | {'Sharpe':<8} | {'MDD':<8} | {'Mult':<8} | {'Geo g':<8}")
print("-" * 104)
results = {}
for label, col in MODELS:
    res = simulate_engine(col)
    results[label] = res
    print(f"{label:<44} | {res['full_cagr']*100:>+8.1f}% | {res['full_sharpe']:>8.2f} | {res['full_mdd']*100:>7.1f}% | {res['full_mult']:>6.2f}x | {res['full_g']:>8.2f}")

print("\n" + "=" * 104)
print("             2. FOLD 1 RESILIENCE AUDIT (DAYS 0 TO 51.1 - ADVERSE DELEVERAGING)")
print("=" * 104)
print(f"{'Strategy Configuration':<44} | {'F1 CAGR':<10} | {'F1 Sharpe':<10} | {'F1 MDD':<10} | {'F1 Mult':<10}")
print("-" * 104)
for label, _ in MODELS:
    res = results[label]
    print(f"{label:<44} | {res['f1_cagr']*100:>+8.1f}% | {res['f1_sharpe']:>10.2f} | {res['f1_mdd']*100:>9.1f}% | {res['f1_mult']:>9.2f}x")
print("=" * 104)
