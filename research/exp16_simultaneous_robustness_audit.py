import numpy as np
import polars as pl
from pathlib import Path

print("=" * 104)
print("   EXPERIMENT 16: SIMULTANEOUS TRI-ALPHA STRESS AUDIT (WALK-FORWARD, CRASH, EXECUTION)")
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
MMR_RATE = 0.040

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

# 3. Compute 3 Orthogonal Alphas
df = df.with_columns([
    # A0: Multi-Horizon Residual Momentum
    (
        -0.35 * ((pl.col("ret_4h") - pl.col("beta_btc") * pl.col("btc_ret_4h")) / (pl.col("vol_yang_zhang") + 1e-5))
        -0.25 * ((pl.col("ret_12h") - pl.col("beta_btc") * pl.col("btc_ret_12h")) / (pl.col("vol_yang_zhang") + 1e-5))
        +0.40 * ((pl.col("ret_72h") - pl.col("beta_btc") * pl.col("btc_ret_72h")) / (pl.col("vol_yang_zhang") + 1e-5))
    ).alias("raw_a0"),
    # A1: Short-term Liquidity Exhaustion
    (
        -1.0 * ((pl.col("ret_1h") - pl.col("beta_btc") * (pl.col("btc_ret_4h") / 4.0)) / (pl.col("vol_yang_zhang") + 1e-5))
        * (pl.col("volume_zscore_72h").clip(-1.0, 4.0) + 1.0)
    ).alias("raw_a1"),
    # A2: Funding Divergence
    (
        -1.0 * (
            ((pl.col("funding_rate") - pl.col("funding_rate").rolling_mean(24).over("symbol")) /
             (pl.col("funding_rate").rolling_std(24).over("symbol") + 1e-6)).clip(-3.0, 3.0)
            - (pl.col("ret_24h") / (pl.col("vol_yang_zhang") * np.sqrt(24) + 1e-5)).clip(-3.0, 3.0)
        )
    ).alias("raw_a2")
])

# Smooth & Cross-Sectionally Standardize
df = df.sort(["symbol", "group_id"]).with_columns([
    pl.col("raw_a0").ewm_mean(span=6).over("symbol").alias("a0_smooth"),
    pl.col("raw_a1").ewm_mean(span=2).over("symbol").alias("a1_smooth"),
    pl.col("raw_a2").ewm_mean(span=4).over("symbol").alias("a2_smooth")
])

for col, zcol in [("a0_smooth", "z_a0"), ("a1_smooth", "z_a1"), ("a2_smooth", "z_a2")]:
    df = df.with_columns([
        ((pl.col(col) - pl.col(col).mean().over("group_id")) / (pl.col(col).std().over("group_id") + 1e-5)).alias(zcol)
    ])

# Master Tri-Alpha Score (40% A0, 30% A1, 30% A2)
df = df.with_columns([
    (0.40 * pl.col("z_a0") + 0.30 * pl.col("z_a1") + 0.30 * pl.col("z_a2")).alias("tri_alpha")
])

# Dispersion & Breadth
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

# Generic Simulation Core
def run_backtest(grps, max_lev=6.2, fee_rate=0.00015, fill_rate=1.0, inject_crash=False, crash_idx=None):
    nav = 10_000.0
    turnover = 0.0
    prev_w = {}
    active_longs = set()
    active_shorts = set()
    returns = []
    min_cushion = 1.0
    liquidated = False

    for idx, grp in enumerate(grps[:-1]):
        cur_panel = df.filter(pl.col("group_id") == grp)
        valid_panel = cur_panel.filter(
            (pl.col("dollar_volume_1h") > 25_000) &
            pl.col("vol_yang_zhang").is_not_null() &
            pl.col("tri_alpha").is_not_null() &
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
                gross_target = float(np.clip(1.20 + 700.0 * delta_disp, 0.0, max_lev))
                sorted_alpha = valid_panel.sort("tri_alpha", descending=True)
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

        # Leland deadband + partial fill modeling
        dispatched = {}
        all_syms = set(prev_w.keys()).union(raw_target.keys())
        for s in all_syms:
            w_t = raw_target.get(s, 0.0)
            w_prev = prev_w.get(s, 0.0)
            sigma = max(0.015, safe_val(vols_map, s, 0.025))

            if abs(w_t) < 1e-4 or abs(w_prev) < 1e-4 or (w_t * w_prev < 0):
                target_delta = w_t - w_prev
                dispatched[s] = w_prev + target_delta * fill_rate
                continue

            h_star = np.clip(((4.0 / 3.0) * (fee_rate * (sigma ** 2.0)) / GAMMA_MVO) ** (1.0 / 3.0) * 2.0, 0.020, 0.065)
            delta = w_t - w_prev
            if abs(delta) > h_star:
                dispatched[s] = w_prev + (w_t - np.sign(delta) * h_star - w_prev) * fill_rate
            else:
                dispatched[s] = w_prev

        dispatched = {s: w for s, w in dispatched.items() if abs(w) > 0.002}
        to = sum(abs(dispatched.get(s, 0.0) - prev_w.get(s, 0.0)) for s in all_syms)
        turnover += to
        cost = to * fee_rate

        # Adversarial Flash Crash Injection: -20% BTC crash + shorts squeeze +12%
        if inject_crash and idx == crash_idx:
            p_pnl = sum(-0.20 * w for s, w in dispatched.items() if w > 0) + \
                    sum(-0.12 * abs(w) for s, w in dispatched.items() if w < 0)
        else:
            p_pnl = sum(dispatched.get(s, 0.0) * safe_val(returns_map, s, 0.0) for s in dispatched)

        fund_pnl = sum(-dispatched.get(s, 0.0) * safe_val(funding_map, s, 0.0) for s in dispatched)
        net_pnl = p_pnl + fund_pnl - cost

        gross_exp = sum(abs(w) for w in dispatched.values())
        if gross_exp > 0.1:
            cushion = (1.0 + net_pnl) - (gross_exp * MMR_RATE)
            min_cushion = min(min_cushion, cushion)
            if cushion <= 0.0:
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
        "nav": nav,
        "mult": nav / 10_000.0,
        "cagr": cagr,
        "sharpe": sharpe,
        "mdd": mdd,
        "geo_g": geo_g,
        "cushion": min_cushion * 100,
        "liquidated": liquidated
    }

# ==============================================================================
# AUDIT 1: WALK-FORWARD OUT-OF-SAMPLE STABILITY (4 EQUAL CHRONOLOGICAL FOLDS)
# ==============================================================================
print("\n" + "=" * 104)
print("AUDIT 1: WALK-FORWARD OUT-OF-SAMPLE FOLD AUDIT (STATIONARITY CHECK)")
print("=" * 104)
print(f"{'Fold Period':<26} | {'Days':<6} | {'CAGR':<10} | {'Sharpe':<8} | {'MDD':<8} | {'Multiple':<8} | {'Geo g':<8}")
print("-" * 104)

n_bars = len(all_active_grps)
fold_size = n_bars // 4
for f in range(4):
    f_grps = all_active_grps[f * fold_size : (f + 1) * fold_size]
    res_f = run_backtest(f_grps, max_lev=4.5)
    f_days = len(f_grps) / 24.0
    print(f"Fold {f+1}: Days {f*f_days:>4.1f} - {(f+1)*f_days:>4.1f}   | {f_days:>4.1f}d | {res_f['cagr']*100:>+8.1f}% | {res_f['sharpe']:>8.2f} | {res_f['mdd']*100:>7.1f}% | {res_f['mult']:>6.2f}x | {res_f['geo_g']:>8.2f}")

# ==============================================================================
# AUDIT 2: SYSTEMIC FLASH CRASH & MARGIN LIQUIDATION AT PEAK LEVERAGE
# ==============================================================================
print("\n" + "=" * 104)
print("AUDIT 2: ADVERSARIAL FLASH CRASH STRESS TEST (-20% BTC CRASH + SHORT SQUEEZE)")
print("=" * 104)
print(f"{'Leverage Setting':<30} | {'Status':<16} | {'Min Margin Cushion':<22} | {'Terminal Mult':<14}")
print("-" * 104)

crash_point = len(all_active_grps) // 2
for lev in [4.5, 5.5, 6.2]:
    res_crash = run_backtest(all_active_grps, max_lev=lev, inject_crash=True, crash_idx=crash_point)
    status = "LIQUIDATED" if res_crash["liquidated"] else "SURVIVED"
    print(f"Gross Cap {lev:.1f}x                 | {status:<16} | {res_crash['cushion']:>18.1f}%   | {res_crash['mult']:>10.2f}x")

# ==============================================================================
# AUDIT 3: PARTIAL FILL & EXECUTION SLIPPAGE DEGRADATION SWEEP
# ==============================================================================
print("\n" + "=" * 104)
print("AUDIT 3: PARTIAL FILL & EXECUTION SLIPPAGE DEGRADATION SWEEP (CAP 5.2x)")
print("=" * 104)
print(f"{'Execution Realism Scenario':<44} | {'CAGR':<10} | {'Sharpe':<8} | {'MDD':<8} | {'Multiple':<8}")
print("-" * 104)

scenarios = [
    ("1. Ideal ALO: 100% Fill @ 1.5 bps", 1.00, 0.00015),
    ("2. Realist ALO: 80% Fill @ 2.0 bps", 0.80, 0.00020),
    ("3. Degraded: 65% Fill @ 3.0 bps (Taker Leak)", 0.65, 0.00030),
    ("4. Hostile: 50% Fill @ 4.5 bps (Toxic Sweeps)", 0.50, 0.00045)
]

for label, fill, fee in scenarios:
    res_exec = run_backtest(all_active_grps, max_lev=5.2, fee_rate=fee, fill_rate=fill)
    print(f"{label:<44} | {res_exec['cagr']*100:>+8.1f}% | {res_exec['sharpe']:>8.2f} | {res_exec['mdd']*100:>7.1f}% | {res_exec['mult']:>6.2f}x")

print("=" * 104)
