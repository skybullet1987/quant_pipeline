import numpy as np
import polars as pl
from pathlib import Path

print("=" * 96)
print("   EXPERIMENT 5: DYNAMIC LEVERAGE SURFACE & BLOCK 3 RESCUE BENCHMARK")
print("=" * 96)

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
K_CARRY = 6

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

# Vectorized Dispersion & Velocity
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

MODES = [
    "1. Static 2.2x Gross",
    "2. Static 4.6x Gross",
    "3. Step-Gated (3.5x if Δσ>0, else 0x)",
    "4. Proportional Scaling (0x-4.2x)",
    "5. Gated A0 + Carry Ballast"
]

navs = [10_000.0] * 5
turnovers = [0.0] * 5
prev_w = [{}, {}, {}, {}, {}]
active_longs = [set() for _ in range(5)]
active_shorts = [set() for _ in range(5)]
returns_hist = [[] for _ in range(5)]

def safe_val(d, k, default=0.0):
    v = d.get(k)
    if v is None: return default
    try:
        f = float(v)
        return default if np.isnan(f) else f
    except:
        return default

for idx, grp in enumerate(active_grps[:-1]):
    cur_panel = df.filter(pl.col("group_id") == grp)
    valid_panel = cur_panel.filter(
        (pl.col("dollar_volume_1h") > 25_000) &
        pl.col("vol_yang_zhang").is_not_null() &
        pl.col("a0_smoothed").is_not_null() &
        pl.col("funding_rate").is_not_null()
    )
    if valid_panel.height < 35:
        continue

    returns_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["next_ret_1h"].to_list()))
    funding_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["funding_rate"].to_list()))
    vols_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["vol_yang_zhang"].to_list()))

    delta_disp = float(valid_panel["delta_disp_24h"][0])
    cs_disp = float(valid_panel["cs_disp_72h"][0])

    # Rank A0 Alpha
    sorted_a0 = valid_panel.sort("a0_smoothed", descending=True)
    all_ranked = sorted_a0["symbol"].to_list()
    rank_map = {s: i for i, s in enumerate(all_ranked)}

    # Rank Carry
    sorted_funding = valid_panel.sort("funding_rate", descending=True)
    c_shorts = sorted_funding.head(K_CARRY)["symbol"].to_list()
    c_longs = sorted_funding.tail(K_CARRY)["symbol"].to_list()

    is_rebal = (idx % 4 == 0)

    for m in range(5):
        if is_rebal:
            # Sizing rules
            if m == 0:
                gross_target = 2.20
            elif m == 1:
                gross_target = 4.60
            elif m == 2:
                gross_target = 3.50 if delta_disp > 0.0 else 0.0
            elif m == 3:
                gross_target = float(np.clip(1.5 + 400.0 * delta_disp, 0.0, 4.2))
            elif m == 4:
                # Hybrid: A0 gets up to 3.5x if delta_disp > 0; if delta_disp <= 0, A0 = 0x and Carry = 1.5x
                a0_active = (delta_disp > 0.0)
                gross_target = 3.50 if a0_active else 0.0

            if m == 4 and delta_disp <= 0.0:
                # Mode 5 fallback to pure Carry sleeve
                raw_target = {}
                for s in c_longs: raw_target[s] = 0.75 / len(c_longs)
                for s in c_shorts: raw_target[s] = -0.75 / len(c_shorts)
            elif gross_target > 0.0:
                for s in all_ranked[:K_ENTRY]: active_longs[m].add(s)
                for s in all_ranked[-K_ENTRY:]: active_shorts[m].add(s)
                active_longs[m] = {s for s in active_longs[m] if rank_map.get(s, 999) < K_EXIT}
                active_shorts[m] = {s for s in active_shorts[m] if rank_map.get(s, -1) >= (len(all_ranked) - K_EXIT)}
                active_longs[m] -= active_shorts[m]
                active_syms = active_longs[m].union(active_shorts[m])

                if len(active_syms) < 16:
                    raw_target = prev_w[m]
                else:
                    inv_v = {s: 1.0 / max(0.015, safe_val(vols_map, s, 0.025)) for s in active_syms}
                    raw_w = {s: inv_v[s] if s in active_longs[m] else -inv_v[s] for s in active_syms}
                    l_sum = sum(w for w in raw_w.values() if w > 0)
                    s_sum = sum(abs(w) for w in raw_w.values() if w < 0)

                    target_leg = gross_target / 2.0
                    raw_target = {}
                    for s in raw_w:
                        if raw_w[s] > 0 and l_sum > 0: raw_target[s] = (raw_w[s] / l_sum) * target_leg
                        elif raw_w[s] < 0 and s_sum > 0: raw_target[s] = (raw_w[s] / s_sum) * target_leg
            else:
                raw_target = {}
        else:
            raw_target = prev_w[m]

        # Leland Deadband
        dispatched = {}
        all_syms = set(prev_w[m].keys()).union(raw_target.keys())
        for s in all_syms:
            w_t = raw_target.get(s, 0.0)
            w_prev_s = prev_w[m].get(s, 0.0)
            sigma = max(0.015, safe_val(vols_map, s, 0.025))

            if abs(w_t) < 1e-4 or abs(w_prev_s) < 1e-4 or (w_t * w_prev_s < 0):
                dispatched[s] = w_t
                continue

            h_star = np.clip(((4.0 / 3.0) * (FEE_RATE * (sigma ** 2.0)) / GAMMA_MVO) ** (1.0 / 3.0) * 1.5, 0.020, 0.055)
            delta = w_t - w_prev_s
            if abs(delta) > h_star:
                dispatched[s] = w_t - np.sign(delta) * h_star
            else:
                dispatched[s] = w_prev_s

        dispatched = {s: w for s, w in dispatched.items() if abs(w) > 0.002}

        to = sum(abs(dispatched.get(s, 0.0) - prev_w[m].get(s, 0.0)) for s in all_syms)
        turnovers[m] += to
        cost = to * FEE_RATE

        # Hourly funding settlement
        fund_pnl = sum(-dispatched.get(s, 0.0) * safe_val(funding_map, s, 0.0) for s in dispatched)
        p_pnl = sum(dispatched.get(s, 0.0) * safe_val(returns_map, s, 0.0) for s in dispatched)

        net_pnl = p_pnl + fund_pnl - cost
        navs[m] *= (1.0 + net_pnl)
        returns_hist[m].append(net_pnl)
        prev_w[m] = dispatched

print("\n" + "=" * 96)
print("             EXPERIMENT 5: DYNAMIC LEVERAGE COMPARISON (FULL 191 DAYS)")
print("=" * 96)
headers = ["Performance Metric", MODES[0], MODES[1], MODES[2], MODES[3], MODES[4]]
print(f"{headers[0]:<28} | {headers[1]:<12} | {headers[2]:<12} | {headers[3]:<12} | {headers[4]:<12} | {headers[5]:<12}")
print("-" * 96)

def calc_stats(rets, to, nav):
    r = np.array(rets)
    ann_mult = BARS_PER_YEAR / len(r)
    cagr = (nav / 10_000.0) ** ann_mult - 1.0
    sharpe = np.mean(r) / (np.std(r) + 1e-6) * np.sqrt(BARS_PER_YEAR)
    cum = np.cumprod(1.0 + r)
    mdd = np.min((cum - np.maximum.accumulate(cum)) / np.maximum.accumulate(cum))
    vol = np.std(r) * np.sqrt(BARS_PER_YEAR)
    down_r = r[r < 0]
    sortino = np.mean(r) / (np.std(down_r) + 1e-6) * np.sqrt(BARS_PER_YEAR) if len(down_r) > 0 else 0.0
    return nav / 10_000.0, cagr, sharpe, sortino, mdd, vol, to * ann_mult

metrics = [calc_stats(returns_hist[i], turnovers[i], navs[i]) for i in range(5)]

print(f"{'Terminal Multiple':<28} | {metrics[0][0]:>11.2f}x | {metrics[1][0]:>11.2f}x | {metrics[2][0]:>11.2f}x | {metrics[3][0]:>11.2f}x | {metrics[4][0]:>11.2f}x")
print(f"{'Annualized Net CAGR':<28} | {metrics[0][1]*100:>10.1f}% | {metrics[1][1]*100:>10.1f}% | {metrics[2][1]*100:>10.1f}% | {metrics[3][1]*100:>10.1f}% | {metrics[4][1]*100:>10.1f}%")
print(f"{'Net Sharpe Ratio':<28} | {metrics[0][2]:>12.2f} | {metrics[1][2]:>12.2f} | {metrics[2][2]:>12.2f} | {metrics[3][2]:>12.2f} | {metrics[4][2]:>12.2f}")
print(f"{'Sortino Ratio':<28} | {metrics[0][3]:>12.2f} | {metrics[1][3]:>12.2f} | {metrics[2][3]:>12.2f} | {metrics[3][3]:>12.2f} | {metrics[4][3]:>12.2f}")
print(f"{'Max Drawdown':<28} | {metrics[0][4]*100:>11.1f}% | {metrics[1][4]*100:>11.1f}% | {metrics[2][4]*100:>11.1f}% | {metrics[3][4]*100:>11.1f}% | {metrics[4][4]*100:>11.1f}%")
print(f"{'Realized Volatility':<28} | {metrics[0][5]*100:>11.1f}% | {metrics[1][5]*100:>11.1f}% | {metrics[2][5]*100:>11.1f}% | {metrics[3][5]*100:>11.1f}% | {metrics[4][5]*100:>11.1f}%")
print(f"{'Annualized Turnover':<28} | {metrics[0][6]:>11.0f}x | {metrics[1][6]:>11.0f}x | {metrics[2][6]:>11.0f}x | {metrics[3][6]:>11.0f}x | {metrics[4][6]:>11.0f}x")

# Block 3 (OOS) Performance specifically
b_size = len(returns_hist[0]) // 3
oos_slice = slice(2 * b_size, len(returns_hist[0]))

print("\n" + "=" * 96)
print("             BLOCK 3 (DAYS 129 TO 193 - UNTOUCHED OOS) RESCUE AUDIT")
print("=" * 96)
print(f"{'Performance Metric':<28} | {MODES[0]:<12} | {MODES[1]:<12} | {MODES[2]:<12} | {MODES[3]:<12} | {MODES[4]:<12}")
print("-" * 96)
for metric_name, fn in [
    ("OOS Net CAGR", lambda r: ((np.prod(1.0 + r))**(BARS_PER_YEAR/len(r)) - 1.0)*100),
    ("OOS Net Sharpe", lambda r: np.mean(r)/(np.std(r)+1e-6)*np.sqrt(BARS_PER_YEAR)),
    ("OOS Max Drawdown", lambda r: np.min((np.cumprod(1.0+r)-np.maximum.accumulate(np.cumprod(1.0+r)))/np.maximum.accumulate(np.cumprod(1.0+r)))*100)
]:
    vals = [fn(np.array(returns_hist[i][oos_slice])) for i in range(5)]
    print(f"{metric_name:<28} | {vals[0]:>10.1f}% | {vals[1]:>10.1f}% | {vals[2]:>10.1f}% | {vals[3]:>10.1f}% | {vals[4]:>10.1f}%" if "CAGR" in metric_name or "Drawdown" in metric_name else f"{metric_name:<28} | {vals[0]:>12.2f} | {vals[1]:>12.2f} | {vals[2]:>12.2f} | {vals[3]:>12.2f} | {vals[4]:>12.2f}")
print("=" * 96)
