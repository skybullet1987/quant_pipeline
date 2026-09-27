import numpy as np
import polars as pl
from pathlib import Path

print("=" * 96)
print("   EXPERIMENT 11: EXECUTION FRICTION & ADVERSE SELECTION SENSITIVITY")
print("=" * 96)

LAKE_PATH = Path.home() / "quant_pipeline" / "data" / "lake" / "features" / "pit_panel_1h_with_funding.parquet"
df = pl.read_parquet(LAKE_PATH)

if "group_id" not in df.columns:
    unique_ts = df.select("timestamp_ms").unique().sort("timestamp_ms").with_columns(
        pl.int_range(0, pl.len()).alias("group_id")
    )
    df = df.join(unique_ts, on="timestamp_ms", how="left")

BARS_PER_YEAR = 24 * 365
GAMMA_MVO = 0.05
K_ENTRY = 12
K_EXIT = 28

# Forward returns
df = df.sort(["symbol", "group_id"]).with_columns([
    (pl.col("close").shift(-1).over("symbol") / pl.col("close") - 1.0).fill_null(0.0).alias("next_ret_1h")
])

# Align BTC
btc = df.filter(pl.col("symbol") == "BTC").select([
    "group_id", pl.col("ret_4h").alias("btc_ret_4h"), pl.col("ret_12h").alias("btc_ret_12h"), pl.col("ret_72h").alias("btc_ret_72h")
]).unique(subset=["group_id"])
df = df.join(btc, on="group_id", how="left")

# A0 Alpha
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

# Dispersion
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

FRICTION_SCENARIOS = [
    ("1. Pure ALO Maker (1.5 bps)", 0.00015, 0.0),
    ("2. Conservative Maker + Fill Slippage (2.5 bps)", 0.00025, 0.0),
    ("3. Blended 50% Maker / 50% Taker (3.0 bps)", 0.00030, 0.0),
    ("4. Aggressive Taker / Toxic Flow (4.5 bps)", 0.00045, 0.0),
    ("5. Adverse Fill Shock (2.5 bps + 1.0 bp adverse drag)", 0.00025, 0.00010)
]

results = []

for label, fee_rate, adverse_drag in FRICTION_SCENARIOS:
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
            pl.col("a0_smoothed").is_not_null() &
            pl.col("funding_rate").is_not_null()
        )
        n_avail = valid_panel.height

        returns_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["next_ret_1h"].to_list()))
        funding_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["funding_rate"].to_list()))
        vols_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["vol_yang_zhang"].to_list()))

        delta_disp = float(valid_panel["delta_disp_24h"][0]) if n_avail >= 12 else -1.0
        is_active = (n_avail >= 35) and (delta_disp > -0.001)

        is_rebal = (idx % 6 == 0)
        if is_rebal:
            if is_active:
                gross_target = float(np.clip(1.20 + 450.0 * delta_disp, 0.0, 4.50))
                sorted_a0 = valid_panel.sort("a0_smoothed", descending=True)
                all_ranked = sorted_a0["symbol"].to_list()
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

            h_star = np.clip(((4.0 / 3.0) * (fee_rate * (sigma ** 2.0)) / GAMMA_MVO) ** (1.0 / 3.0) * 2.0, 0.020, 0.065)
            delta = w_t - w_prev
            dispatched[s] = (w_t - np.sign(delta) * h_star) if abs(delta) > h_star else w_prev

        dispatched = {s: w for s, w in dispatched.items() if abs(w) > 0.002}
        to = sum(abs(dispatched.get(s, 0.0) - prev_w.get(s, 0.0)) for s in all_syms)
        turnover += to
        cost = to * (fee_rate + adverse_drag)

        fund_pnl = sum(-dispatched.get(s, 0.0) * safe_val(funding_map, s, 0.0) for s in dispatched)
        p_pnl = sum(dispatched.get(s, 0.0) * safe_val(returns_map, s, 0.0) for s in dispatched)
        net_pnl = p_pnl + fund_pnl - cost

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

    results.append({
        "scenario": label,
        "cagr": cagr,
        "sharpe": sharpe,
        "mdd": mdd,
        "mult": nav / 10_000.0,
        "geo_g": geo_g,
        "to_ann": turnover * ann_mult
    })

print("\n" + "=" * 96)
print("             EXECUTION FRICTION STRESS TEST RESULTS (204.5 DAYS)")
print("=" * 96)
print(f"{'Friction Scenario':<48} | {'CAGR':<10} | {'Sharpe':<8} | {'MDD':<8} | {'Multiple':<8} | {'Geo g':<8}")
print("-" * 96)
for res in results:
    print(f"{res['scenario']:<48} | {res['cagr']*100:>+8.1f}% | {res['sharpe']:>8.2f} | {res['mdd']*100:>7.1f}% | {res['mult']:>6.2f}x | {res['geo_g']:>8.2f}")
print("=" * 96)
