import numpy as np
import polars as pl
from pathlib import Path

print("=" * 104)
print("   EXPERIMENT 19: CASCADE GOVERNOR & MICROSTRUCTURE TOXICITY GATING (HL-3A)")
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
MAX_LEV = 5.20

# 1. Clean forward and 1H returns
df = df.sort(["symbol", "group_id"]).with_columns([
    (pl.col("close").shift(-1).over("symbol") / pl.col("close") - 1.0).fill_null(0.0).alias("next_ret_1h"),
    (pl.col("close") / pl.col("close").shift(1).over("symbol") - 1.0).fill_null(0.0).alias("ret_1h_clean")
])

# 2. Align BTC
btc = df.filter(pl.col("symbol") == "BTC").select([
    "group_id",
    pl.col("ret_1h_clean").alias("btc_ret_1h"),
    pl.col("ret_4h").alias("btc_ret_4h"),
    pl.col("ret_12h").alias("btc_ret_12h"),
    pl.col("ret_72h").alias("btc_ret_72h")
]).unique(subset=["group_id"])
df = df.join(btc, on="group_id", how="left")

# 3. Alphas with Directional Flow Gating
# Residual 1h return
df = df.with_columns([
    ((pl.col("ret_1h_clean") - pl.col("beta_btc") * pl.col("btc_ret_1h")) / (pl.col("vol_yang_zhang") + 1e-5)).alias("res_ret_1h")
])

# G_micro proxy: When volume surge is extreme (>2.0 z-score) and return is large, do not fade
df = df.with_columns([
    # Standard A0 (Multi-Horizon Residual Momentum)
    (
        -0.35 * ((pl.col("ret_4h") - pl.col("beta_btc") * pl.col("btc_ret_4h")) / (pl.col("vol_yang_zhang") + 1e-5))
        -0.25 * ((pl.col("ret_12h") - pl.col("beta_btc") * pl.col("btc_ret_12h")) / (pl.col("vol_yang_zhang") + 1e-5))
        +0.40 * ((pl.col("ret_72h") - pl.col("beta_btc") * pl.col("btc_ret_72h")) / (pl.col("vol_yang_zhang") + 1e-5))
    ).alias("raw_a0"),
    # A1 Gated: Suppress reversal when volume z-score > 2.0 (toxic directional sweep)
    pl.when(pl.col("volume_zscore_72h") > 2.0)
    .then(0.0) # Suppress fade during volume blowouts
    .otherwise(
        -1.0 * pl.col("res_ret_1h") * (pl.col("volume_zscore_72h").clip(-1.0, 2.0) + 1.0)
    ).alias("raw_a1_gated"),
    # A2 Asymmetric Funding
    (
        -1.0 * (
            ((pl.col("funding_rate") - pl.col("funding_rate").rolling_mean(24).over("symbol")) /
             (pl.col("funding_rate").rolling_std(24).over("symbol") + 1e-6)).clip(0.0, 3.0)
            - (pl.col("ret_24h") / (pl.col("vol_yang_zhang") * np.sqrt(24) + 1e-5)).clip(-3.0, 3.0)
        )
    ).alias("raw_a2")
])

# Smooth & Standardize
df = df.sort(["symbol", "group_id"]).with_columns([
    pl.col("raw_a0").ewm_mean(span=6).over("symbol").alias("a0_smooth"),
    pl.col("raw_a1_gated").ewm_mean(span=2).over("symbol").alias("a1_smooth"),
    pl.col("raw_a2").ewm_mean(span=4).over("symbol").alias("a2_smooth")
])

for col, zcol in [("a0_smooth", "z_a0"), ("a1_smooth", "z_a1"), ("a2_smooth", "z_a2")]:
    df = df.with_columns([
        ((pl.col(col) - pl.col(col).mean().over("group_id")) / (pl.col(col).std().over("group_id") + 1e-5)).alias(zcol)
    ])

df = df.with_columns([
    (0.45 * pl.col("z_a0") + 0.35 * pl.col("z_a1") + 0.20 * pl.col("z_a2")).alias("gated_tri_alpha")
])

# 4. SYSTEMIC CASCADE GOVERNOR: Cross-Sectional Funding Skewness & Dispersion
mkt_state = (
    df.filter(pl.col("funding_rate").is_not_null())
    .group_by("group_id")
    .agg([
        pl.col("funding_rate").mean().alias("m_f"),
        pl.col("funding_rate").std().alias("s_f"),
        pl.col("funding_rate").quantile(0.90).alias("q90_f"),
        pl.col("funding_rate").quantile(0.10).alias("q10_f"),
        # Higher moment: Skewness
        (((pl.col("funding_rate") - pl.col("funding_rate").mean()) / (pl.col("funding_rate").std() + 1e-7)) ** 3).mean().alias("fund_skew")
    ])
    .with_columns([
        (pl.col("q90_f") - pl.col("q10_f")).alias("fund_dispersion")
    ])
    .sort("group_id")
    .with_columns([
        ((pl.col("fund_dispersion") - pl.col("fund_dispersion").rolling_mean(72)) /
         (pl.col("fund_dispersion").rolling_std(72) + 1e-6)).alias("z_fund_disp"),
        pl.col("fund_skew").rolling_mean(12).alias("smooth_fund_skew")
    ])
)
df = df.join(mkt_state.select(["group_id", "z_fund_disp", "smooth_fund_skew"]), on="group_id", how="left")

# Dispersion Metrics
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

def simulate_engine(use_cascade_governor=True):
    nav = 10_000.0
    turnover = 0.0
    prev_w = {}
    active_longs = set()
    active_shorts = set()
    returns = []
    min_cushion = 1.0

    for idx, grp in enumerate(all_active_grps[:-1]):
        cur_panel = df.filter(pl.col("group_id") == grp)
        valid_panel = cur_panel.filter(
            (pl.col("dollar_volume_1h") > 25_000) &
            pl.col("vol_yang_zhang").is_not_null() &
            pl.col("gated_tri_alpha").is_not_null() &
            pl.col("funding_rate").is_not_null()
        )
        n_avail = valid_panel.height

        returns_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["next_ret_1h"].to_list()))
        funding_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["funding_rate"].to_list()))
        vols_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["vol_yang_zhang"].to_list()))

        delta_disp = float(valid_panel["delta_disp_24h"][0]) if n_avail >= 12 else -1.0
        z_disp_f = float(valid_panel["z_fund_disp"][0]) if "z_fund_disp" in valid_panel.columns else 0.0
        skew_f = float(valid_panel["smooth_fund_skew"][0]) if "smooth_fund_skew" in valid_panel.columns else 0.0

        # Systemic Cascade Governor: If funding dispersion explodes (z > 2.5) or funding skewness inverts sharply (<-2.0), shut down leverage
        is_cascade_risk = use_cascade_governor and ((z_disp_f > 2.5) or (skew_f < -2.2))
        
        breadth_active = (n_avail >= 35) and (delta_disp > -0.001) and (not is_cascade_risk)

        is_rebal = (idx % REBAL_CLOCK == 0)
        if is_rebal:
            if breadth_active:
                gross_target = float(np.clip(1.20 + 550.0 * delta_disp, 0.0, MAX_LEV))
                sorted_alpha = valid_panel.sort("gated_tri_alpha", descending=True)
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

        # Leland deadband
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

        gross_exp = sum(abs(w) for w in dispatched.values())
        if gross_exp > 0.1:
            req_margin = gross_exp * 0.040 * 1.01
            cushion = (1.0 + net_pnl) - req_margin
            min_cushion = min(min_cushion, cushion)

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
        "min_cushion": min_cushion * 100, "f1_mult": mult_f1, "f1_mdd": mdd_f1, "f1_sharpe": sharpe_f1
    }

print("\n" + "=" * 104)
print("COMPARING ENGINE PERFORMANCE: UNCONDITIONED VS. CASCADE-GOVERNED (EXP 19)")
print("=" * 104)
print(f"{'Configuration':<38} | {'Full CAGR':<10} | {'Sharpe':<8} | {'Full MDD':<9} | {'Fold 1 Mult':<12} | {'Full Mult'}")
print("-" * 104)

r_base = simulate_engine(use_cascade_governor=False)
r_gov = simulate_engine(use_cascade_governor=True)

print(f"{'1. HL-3A Baseline (Exp 17 Spec)':<38} | {r_base['full_cagr']*100:>+8.1f}% | {r_base['full_sharpe']:>8.2f} | {r_base['full_mdd']*100:>8.1f}% | {r_base['f1_mult']:>10.2f}x | {r_base['full_mult']:>8.2f}x")
print(f"{'2. Cascade Governor + Toxicity Gate':<38} | {r_gov['full_cagr']*100:>+8.1f}% | {r_gov['full_sharpe']:>8.2f} | {r_gov['full_mdd']*100:>8.1f}% | {r_gov['f1_mult']:>10.2f}x | {r_gov['full_mult']:>8.2f}x")
print("=" * 104)
