import numpy as np
import polars as pl
from pathlib import Path

print("=" * 104)
print("   COMBINED AUDIT: FULL 351-DAY ADAPTIVE BACKTEST & MARGIN LIQUIDATION STRESS TEST")
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
MMR_RATE = 0.040  # 4.0% Hyperliquid blended maintenance margin requirement

# 1. Forward Returns
df = df.sort(["symbol", "group_id"]).with_columns([
    (pl.col("close").shift(-1).over("symbol") / pl.col("close") - 1.0).fill_null(0.0).alias("next_ret_1h")
])

# 2. Align BTC
btc = df.filter(pl.col("symbol") == "BTC").select([
    "group_id", pl.col("ret_4h").alias("btc_ret_4h"), pl.col("ret_12h").alias("btc_ret_12h"), pl.col("ret_72h").alias("btc_ret_72h")
]).unique(subset=["group_id"])
df = df.join(btc, on="group_id", how="left")

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

# 4. Vectorized Cross-Sectional Dispersion with Adaptive Threshold (min 12 tokens)
print("[+] Calculating adaptive cross-sectional dispersion across full history...")
df_disp = (
    df.filter((pl.col("dollar_volume_1h") > 25_000) & pl.col("ret_72h").is_not_null())
    .group_by("group_id")
    .agg([
        pl.col("ret_72h").std().alias("cs_disp_72h"),
        pl.len().alias("count")
    ])
    .filter(pl.col("count") >= 12)  # Lowers threshold to capture full 351 days
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
days_total = len(all_active_grps) / 24.0

print(f"[+] Total Active History Unlocked: {len(all_active_grps):,} hourly bars ({days_total:.1f} days)")

def safe_val(d, k, default=0.0):
    v = d.get(k)
    if v is None: return default
    try:
        f = float(v)
        return default if np.isnan(f) else f
    except:
        return default

# Compare:
# Config 2: Friction Slash (6H Clock, Cap 4.5x, DB 2.0x, Slope 450)
# Config 4: Ultra-Convex Kelly (6H Clock, Cap 6.5x, DB 2.2x, Slope 700)
CONFIGS = [
    ("Config 2 (Prudent: Cap 4.5x, 6H)", 4.50, 2.0, 450.0),
    ("Config 4 (Kelly: Cap 6.5x, 6H)",   6.50, 2.2, 700.0)
]

def run_simulation(max_lev, db_mult, slope, inject_shock=False):
    nav = 10_000.0
    turnover = 0.0
    prev_w = {}
    active_longs = set()
    active_shorts = set()
    returns = []
    min_margin_cushion = 1.0  # Track distance to maintenance margin liquidation
    liquidated = False
    liquidation_bar = None

    for idx, grp in enumerate(all_active_grps[:-1]):
        cur_panel = df.filter(pl.col("group_id") == grp)
        valid_panel = cur_panel.filter(
            (pl.col("dollar_volume_1h") > 25_000) &
            pl.col("vol_yang_zhang").is_not_null() &
            pl.col("a0_smoothed").is_not_null() &
            pl.col("funding_rate").is_not_null()
        )
        n_avail = valid_panel.height
        if n_avail < 12:
            continue

        returns_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["next_ret_1h"].to_list()))
        funding_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["funding_rate"].to_list()))
        vols_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["vol_yang_zhang"].to_list()))

        delta_disp = float(valid_panel["delta_disp_24h"][0])

        # Dynamic Basket Sizing
        k_entry = max(3, min(12, int(n_avail * 0.15)))
        k_exit = max(6, min(28, int(n_avail * 0.35)))

        is_rebal = (idx % 6 == 0)
        if is_rebal:
            if delta_disp <= -0.001:
                gross_target = 0.0
            else:
                base_lev = 1.20
                gross_target = float(np.clip(base_lev + slope * delta_disp, 0.0, max_lev))

            if gross_target > 0.05:
                sorted_a0 = valid_panel.sort("a0_smoothed", descending=True)
                all_ranked = sorted_a0["symbol"].to_list()
                rank_map = {s: i for i, s in enumerate(all_ranked)}

                for s in all_ranked[:k_entry]: active_longs.add(s)
                for s in all_ranked[-k_entry:]: active_shorts.add(s)
                active_longs = {s for s in active_longs if rank_map.get(s, 999) < k_exit}
                active_shorts = {s for s in active_shorts if rank_map.get(s, -1) >= (len(all_ranked) - k_exit)}
                active_longs -= active_shorts
                active_syms = active_longs.union(active_shorts)

                if len(active_syms) >= max(6, k_entry * 2):
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

        # Deadband execution
        dispatched = {}
        all_syms = set(prev_w.keys()).union(raw_target.keys())
        for s in all_syms:
            w_t = raw_target.get(s, 0.0)
            w_prev = prev_w.get(s, 0.0)
            sigma = max(0.015, safe_val(vols_map, s, 0.025))

            if abs(w_t) < 1e-4 or abs(w_prev) < 1e-4 or (w_t * w_prev < 0):
                dispatched[s] = w_t
                continue

            h_star = np.clip(((4.0 / 3.0) * (FEE_RATE * (sigma ** 2.0)) / GAMMA_MVO) ** (1.0 / 3.0) * db_mult, 0.020, 0.065)
            delta = w_t - w_prev
            dispatched[s] = (w_t - np.sign(delta) * h_star) if abs(delta) > h_star else w_prev

        dispatched = {s: w for s, w in dispatched.items() if abs(w) > 0.002}
        to = sum(abs(dispatched.get(s, 0.0) - prev_w.get(s, 0.0)) for s in all_syms)
        turnover += to
        cost = to * FEE_RATE

        # Synthetic Shock Injection at mid-point (simulating Aug 5 / FTX style -16% spread dislocation)
        if inject_shock and idx == len(all_active_grps) // 2:
            p_pnl = sum(-0.12 * w for s, w in dispatched.items() if w > 0) + \
                    sum(-0.04 * abs(w) for s, w in dispatched.items() if w < 0)
        else:
            p_pnl = sum(dispatched.get(s, 0.0) * safe_val(returns_map, s, 0.0) for s in dispatched)

        fund_pnl = sum(-dispatched.get(s, 0.0) * safe_val(funding_map, s, 0.0) for s in dispatched)
        net_pnl = p_pnl + fund_pnl - cost

        # Cross-Margin Liquidation Check:
        # Gross Exposure = sum(|w|), Required Maintenance Margin = Gross * MMR_RATE * NAV
        # If (NAV + PnL) <= Gross * MMR_RATE * NAV -> Liquidation
        gross_notional_ratio = sum(abs(w) for w in dispatched.values())
        if gross_notional_ratio > 0.1:
            # Margin cushion: (Equity - Required Margin) / Equity
            cushion = (1.0 + net_pnl) - (gross_notional_ratio * MMR_RATE)
            min_margin_cushion = min(min_margin_cushion, cushion)
            if cushion <= 0.0:
                liquidated = True
                liquidation_bar = idx
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
        "to_ann": turnover * ann_mult,
        "min_cushion": min_margin_cushion * 100,
        "liquidated": liquidated,
        "liq_bar": liquidation_bar
    }

print("\n" + "=" * 104)
print("1. FULL 351-DAY ADAPTIVE UNIVERSE BACKTEST RESULTS (UNCONSTRAINED HISTORY)")
print("=" * 104)
print(f"{'Configuration':<36} | {'CAGR':<10} | {'Sharpe':<8} | {'MDD':<8} | {'Multiple':<10} | {'Geo g':<8} | {'Turnover':<10}")
print("-" * 104)

res_c2 = run_simulation(CONFIGS[0][1], CONFIGS[0][2], CONFIGS[0][3], inject_shock=False)
res_c4 = run_simulation(CONFIGS[1][1], CONFIGS[1][2], CONFIGS[1][3], inject_shock=False)

print(f"{CONFIGS[0][0]:<36} | {res_c2['cagr']*100:>+8.1f}% | {res_c2['sharpe']:>8.2f} | {res_c2['mdd']*100:>7.1f}% | {res_c2['mult']:>8.2f}x | {res_c2['geo_g']:>8.2f} | {res_c2['to_ann']:>8.0f}x")
print(f"{CONFIGS[1][0]:<36} | {res_c4['cagr']*100:>+8.1f}% | {res_c4['sharpe']:>8.2f} | {res_c4['mdd']*100:>7.1f}% | {res_c4['mult']:>8.2f}x | {res_c4['geo_g']:>8.2f} | {res_c4['to_ann']:>8.0f}x")

print("\n" + "=" * 104)
print("2. REALIZED MARGIN CUSHION & FLASH-CRASH STRESS TEST (-16% SPREAD BLOWOUT)")
print("=" * 104)
print(f"{'Configuration':<36} | {'Hist Min Cushion':<18} | {'Synthetic Shock Result':<25} | {'Liquidation Risk':<18}")
print("-" * 104)

shock_c2 = run_simulation(CONFIGS[0][1], CONFIGS[0][2], CONFIGS[0][3], inject_shock=True)
shock_c4 = run_simulation(CONFIGS[1][1], CONFIGS[1][2], CONFIGS[1][3], inject_shock=True)

status_c2 = f"SURVIVED (NAV: {shock_c2['mult']:.2f}x)" if not shock_c2["liquidated"] else "LIQUIDATED (-100%)"
status_c4 = f"SURVIVED (NAV: {shock_c4['mult']:.2f}x)" if not shock_c4["liquidated"] else "LIQUIDATED (-100%)"

risk_c2 = "PASS (Safe Buffer)" if not shock_c2["liquidated"] and res_c2["min_cushion"] > 40.0 else "ELEVATED"
risk_c4 = "FAIL (ADL / Margin Call)" if shock_c4["liquidated"] else "BORDERLINE"

print(f"{CONFIGS[0][0]:<36} | {res_c2['min_cushion']:>15.1f}% | {status_c2:<25} | {risk_c2:<18}")
print(f"{CONFIGS[1][0]:<36} | {res_c4['min_cushion']:>15.1f}% | {status_c4:<25} | {risk_c4:<18}")
print("=" * 104)
