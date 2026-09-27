import numpy as np
import polars as pl
from pathlib import Path

print("=" * 104)
print("   EXPERIMENT 18: ARCHITECTURE ADJUSTMENTS & CRITIQUE VALIDATION")
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
MMR_TIER1 = 0.040   # 4.0% MMR for standard altcoins on Hyperliquid
LIQ_PENALTY = 0.010 # 1.0% Hyperliquid liquidation fee penalty
MAX_PARTICIPATION = 0.02 # Max 2% of 1h volume allowed per rebalance

# 1. Forward returns
df = df.sort(["symbol", "group_id"]).with_columns([
    (pl.col("close").shift(-1).over("symbol") / pl.col("close") - 1.0).fill_null(0.0).alias("next_ret_1h"),
    (pl.col("close") / pl.col("close").shift(1).over("symbol") - 1.0).fill_null(0.0).alias("ret_1h_clean")
])

# 2. Align BTC 1h, 4h, 12h, 72h
btc = df.filter(pl.col("symbol") == "BTC").select([
    "group_id",
    pl.col("ret_1h_clean").alias("btc_ret_1h"),
    pl.col("ret_4h").alias("btc_ret_4h"),
    pl.col("ret_12h").alias("btc_ret_12h"),
    pl.col("ret_72h").alias("btc_ret_72h")
]).unique(subset=["group_id"])
df = df.join(btc, on="group_id", how="left")

# 3. FIX: Horizon-Consistent A0 & Matched 1H A1
# Compute residuals per horizon using horizon-specific vol scaling
df = df.with_columns([
    ((pl.col("ret_4h") - pl.col("beta_btc") * pl.col("btc_ret_4h")) / (pl.col("vol_yang_zhang") * np.sqrt(4/72) + 1e-5)).alias("res_4h"),
    ((pl.col("ret_12h") - pl.col("beta_btc") * pl.col("btc_ret_12h")) / (pl.col("vol_yang_zhang") * np.sqrt(12/72) + 1e-5)).alias("res_12h"),
    ((pl.col("ret_72h") - pl.col("beta_btc") * pl.col("btc_ret_72h")) / (pl.col("vol_yang_zhang") + 1e-5)).alias("res_72h"),
    # A1 fix: Matched 1H BTC return
    (-1.0 * ((pl.col("ret_1h_clean") - pl.col("beta_btc") * pl.col("btc_ret_1h")) / (pl.col("vol_yang_zhang") * np.sqrt(1/72) + 1e-5)) *
     (pl.col("volume_zscore_72h").clip(-1.0, 4.0) + 1.0)).alias("raw_a1_fixed")
])

# Standardize each horizon cross-sectionally to ensure correct weights
for r_col, z_r in [("res_4h", "z_res_4h"), ("res_12h", "z_res_12h"), ("res_72h", "z_res_72h")]:
    df = df.with_columns([
        ((pl.col(r_col) - pl.col(r_col).mean().over("group_id")) / (pl.col(r_col).std().over("group_id") + 1e-5)).alias(z_r)
    ])

# A0 Horizon-Consistent Composite
df = df.with_columns([
    (-0.35 * pl.col("z_res_4h") - 0.25 * pl.col("z_res_12h") + 0.40 * pl.col("z_res_72h")).alias("raw_a0_fixed"),
    # A2 Asymmetric: Positive funding surprise only, conditioned on absolute funding > 0
    (-1.0 * (
        ((pl.col("funding_rate") - pl.col("funding_rate").rolling_mean(24).over("symbol")) /
         (pl.col("funding_rate").rolling_std(24).over("symbol") + 1e-6)).clip(0.0, 3.0)
        - (pl.col("ret_24h") / (pl.col("vol_yang_zhang") * np.sqrt(24/72) + 1e-5)).clip(-3.0, 3.0)
    )).alias("raw_a2_fixed")
])

# Smooth & Standardize final alphas
df = df.sort(["symbol", "group_id"]).with_columns([
    pl.col("raw_a0_fixed").ewm_mean(span=6).over("symbol").alias("a0_smooth"),
    pl.col("raw_a1_fixed").ewm_mean(span=2).over("symbol").alias("a1_smooth"),
    pl.col("raw_a2_fixed").ewm_mean(span=4).over("symbol").alias("a2_smooth")
])

for col, zcol in [("a0_smooth", "z_a0"), ("a1_smooth", "z_a1"), ("a2_smooth", "z_a2")]:
    df = df.with_columns([
        ((pl.col(col) - pl.col(col).mean().over("group_id")) / (pl.col(col).std().over("group_id") + 1e-5)).alias(zcol)
    ])

# Adjusted Master Score: 45% A0 + 35% A1 + 20% A2
df = df.with_columns([
    (0.45 * pl.col("z_a0") + 0.35 * pl.col("z_a1") + 0.20 * pl.col("z_a2")).alias("adjusted_tri_alpha")
])

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

def safe_val(d, k, default=0.0):
    v = d.get(k)
    if v is None: return default
    try:
        f = float(v)
        return default if np.isnan(f) else f
    except:
        return default

# ==============================================================================
# 1. REVIEWER AUDIT: CONDITIONAL LOSS SURFACE ON DELTA DISPERSION
# ==============================================================================
print("\n" + "=" * 96)
print("1. CONDITIONAL RETURN & RISK SURFACE ON DISPERSION ACCELERATION (Δσ_CS)")
print("=" * 96)

# Group delta_disp into 5 quantiles to test reviewer's "tail risk" concern
disp_quantiles = df.select(["group_id", "delta_disp_24h"]).unique(subset=["group_id"]).sort("group_id")
q_cuts = disp_quantiles["delta_disp_24h"].qcut(5, labels=["Q1 (Extreme Contraction)", "Q2 (Mild Contraction)", "Q3 (Neutral)", "Q4 (Expansion)", "Q5 (Extreme Expansion)"])
disp_quantiles = disp_quantiles.with_columns(q_cuts.alias("disp_regime"))
df = df.join(disp_quantiles.select(["group_id", "disp_regime"]), on="group_id", how="left")

regime_stats = (
    df.filter(pl.col("dollar_volume_1h") > 25_000)
    .group_by("disp_regime")
    .agg([
        pl.col("delta_disp_24h").mean().alias("avg_delta_disp"),
        pl.col("ret_1h_clean").std().alias("token_vol"),
        pl.len().alias("sample_count")
    ])
    .sort("disp_regime")
)

print(f"{'Dispersion Regime':<26} | {'Avg Δσ_CS':<12} | {'Token 1H Vol':<14} | {'Sample Bars'}")
print("-" * 76)
for row in regime_stats.iter_rows(named=True):
    print(f"{row['disp_regime']:<26} | {row['avg_delta_disp']:>+10.4f} | {row['token_vol']*100:>12.2f}% | {row['sample_count']:,}")

# ==============================================================================
# 2. FULL ENGINE BACKTEST WITH DUAL DOLLAR + BETA NEUTRALITY & PARTICIPATION CAPS
# ==============================================================================
def simulate_adjusted(beta_neutral=True, participation_cap=True):
    nav = 10_000.0
    turnover = 0.0
    prev_w = {}
    active_longs = set()
    active_shorts = set()
    returns = []
    min_cushion = 1.0
    liquidated = False
    shortfall_accum = 0.0
    total_rebal_events = 0

    for idx, grp in enumerate(all_active_grps[:-1]):
        cur_panel = df.filter(pl.col("group_id") == grp)
        valid_panel = cur_panel.filter(
            (pl.col("dollar_volume_1h") > 25_000) &
            pl.col("vol_yang_zhang").is_not_null() &
            pl.col("adjusted_tri_alpha").is_not_null() &
            pl.col("funding_rate").is_not_null() &
            pl.col("beta_btc").is_not_null()
        )
        n_avail = valid_panel.height

        returns_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["next_ret_1h"].to_list()))
        funding_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["funding_rate"].to_list()))
        vols_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["vol_yang_zhang"].to_list()))
        betas_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["beta_btc"].to_list()))
        volume_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["dollar_volume_1h"].to_list()))

        delta_disp = float(valid_panel["delta_disp_24h"][0]) if n_avail >= 12 else -1.0
        breadth_active = (n_avail >= 35) and (delta_disp > -0.001)

        is_rebal = (idx % REBAL_CLOCK == 0)
        if is_rebal:
            total_rebal_events += 1
            if breadth_active:
                gross_target = float(np.clip(1.20 + 550.0 * delta_disp, 0.0, MAX_LEV))
                sorted_alpha = valid_panel.sort("adjusted_tri_alpha", descending=True)
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
                    
                    target_pre = {}
                    for s in raw_w:
                        if raw_w[s] > 0 and l_sum > 0: target_pre[s] = (raw_w[s] / l_sum) * target_leg
                        elif raw_w[s] < 0 and s_sum > 0: target_pre[s] = (raw_w[s] / s_sum) * target_leg

                    # FIX: Dual Dollar & Beta Neutralization
                    if beta_neutral:
                        net_beta = sum(w * safe_val(betas_map, s, 1.0) for s, w in target_pre.items())
                        # Adjust legs slightly to neutralize net portfolio beta
                        beta_l = sum(w * safe_val(betas_map, s, 1.0) for s, w in target_pre.items() if w > 0) / target_leg
                        beta_s = sum(abs(w) * safe_val(betas_map, s, 1.0) for s, w in target_pre.items() if w < 0) / target_leg
                        if beta_l > 0 and beta_s > 0:
                            ratio = beta_s / beta_l
                            # Bound ratio within [0.75, 1.25] to prevent unbalancing dollar legs
                            ratio = np.clip(ratio, 0.80, 1.25)
                            raw_target = {s: (w * ratio if w > 0 else w) for s, w in target_pre.items()}
                        else:
                            raw_target = target_pre
                    else:
                        raw_target = target_pre
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

        # FIX: Market Participation Constraint (Cap order size to 2% of 1h volume)
        if participation_cap:
            for s in all_syms:
                w_disp = dispatched.get(s, 0.0)
                w_prev = prev_w.get(s, 0.0)
                order_notional = abs(w_disp - w_prev) * nav
                avail_vol = safe_val(volume_map, s, 25_000.0)
                max_order = avail_vol * MAX_PARTICIPATION
                if order_notional > max_order:
                    # Clip order delta to max participation rate
                    allowed_delta = (max_order / nav) * np.sign(w_disp - w_prev)
                    dispatched[s] = w_prev + allowed_delta
                    shortfall_accum += abs(order_notional - max_order)

        dispatched = {s: w for s, w in dispatched.items() if abs(w) > 0.002}
        to = sum(abs(dispatched.get(s, 0.0) - prev_w.get(s, 0.0)) for s in all_syms)
        turnover += to
        cost = to * FEE_RATE

        fund_pnl = sum(-dispatched.get(s, 0.0) * safe_val(funding_map, s, 0.0) for s in dispatched)
        p_pnl = sum(dispatched.get(s, 0.0) * safe_val(returns_map, s, 0.0) for s in dispatched)
        net_pnl = p_pnl + fund_pnl - cost

        # FIX: Realistic Exchange Cross-Margin Liquidation Engine
        gross_notional = sum(abs(w) for w in dispatched.values()) * nav
        if gross_notional > 0.1:
            req_mmr = gross_notional * MMR_TIER1
            equity_post = nav * (1.0 + net_pnl)
            # Cushion relative to required margin + liquidation penalty buffer
            cushion = (equity_post - (req_mmr * (1.0 + LIQ_PENALTY))) / equity_post if equity_post > 0 else 0.0
            min_cushion = min(min_cushion, cushion)
            if equity_post <= req_mmr * (1.0 + LIQ_PENALTY):
                liquidated = True
                nav = 0.0
                break

        nav *= (1.0 + net_pnl)
        returns.append(net_pnl)
        prev_w = dispatched

    r = np.array(returns)
    ann_mult = BARS_PER_YEAR / len(r) if len(r) > 0 else 1.0
    cagr = (nav / 10_000.0) ** ann_mult - 1.0 if nav > 0 else -1.0
    sharpe = np.mean(r) / (np.std(r) + 1e-6) * np.sqrt(BARS_PER_YEAR) if len(r) > 0 else 0.0
    cum = np.cumprod(1.0 + r) if len(r) > 0 else np.array([0.0])
    mdd = np.min((cum - np.maximum.accumulate(cum)) / np.maximum.accumulate(cum)) if len(r) > 0 else -1.0
    geo_g = np.mean(np.log(1.0 + r)) * BARS_PER_YEAR if len(r) > 0 and not liquidated else -999.0

    return {
        "cagr": cagr, "sharpe": sharpe, "mdd": mdd, "mult": nav / 10_000.0, "geo_g": geo_g,
        "min_cushion": min_cushion * 100, "liquidated": liquidated, "shortfall": shortfall_accum
    }

print("\n" + "=" * 104)
print("2. PERFORMANCE IMPACT OF REVIEWER ADJUSTMENTS (FULL 204.5 DAYS)")
print("=" * 104)
print(f"{'Configuration':<44} | {'CAGR':<10} | {'Sharpe':<8} | {'MDD':<8} | {'Multiple':<8} | {'Min Cush':<9}")
print("-" * 104)

res_orig = simulate_adjusted(beta_neutral=False, participation_cap=False)
res_adj = simulate_adjusted(beta_neutral=True, participation_cap=True)

print(f"{'1. Unadjusted Baseline (Exp 17 Spec)':<44} | {res_orig['cagr']*100:>+8.1f}% | {res_orig['sharpe']:>8.2f} | {res_orig['mdd']*100:>7.1f}% | {res_orig['mult']:>6.2f}x | {res_orig['min_cushion']:>7.1f}%")
print(f"{'2. Fully Adjusted (Beta-Neutral + Part Capped)':<44} | {res_adj['cagr']*100:>+8.1f}% | {res_adj['sharpe']:>8.2f} | {res_adj['mdd']*100:>7.1f}% | {res_adj['mult']:>6.2f}x | {res_adj['min_cushion']:>7.1f}%")
print("=" * 104)
