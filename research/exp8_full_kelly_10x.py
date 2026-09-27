import time
from pathlib import Path
import numpy as np
import polars as pl

print("=" * 86)
print("   EXPERIMENT 8: TRUE FULL-KELLY DOLLAR-NEUTRAL 10x FRONTIER")
print("=" * 86)

LAKE_PATH = Path.home() / "quant_pipeline" / "data" / "lake" / "features" / "pit_panel_1h_full.parquet"
df = pl.read_parquet(LAKE_PATH)

if "group_id" not in df.columns:
    unique_ts = df.select("timestamp_ms").unique().sort("timestamp_ms").with_columns(
        pl.int_range(0, pl.len()).alias("group_id")
    )
    df = df.join(unique_ts, on="timestamp_ms", how="left")

all_groups = sorted(df.select("group_id").unique().to_series().to_list())
BARS_PER_YEAR = 24 * 365
WARMUP_BARS = 168
K_ENTRY = 12
K_EXIT = 28
FEE_RATE = 0.00015  # 1.5 bps maker fee
GAMMA_MVO = 0.05

# 1. Forward returns
df = df.sort(["symbol", "group_id"]).with_columns([
    (pl.col("close").shift(-1).over("symbol") / pl.col("close") - 1.0).fill_null(0.0).alias("next_ret_1h")
])

# 2. Align BTC reference returns
btc_panel = df.filter(pl.col("symbol") == "BTC").select([
    "group_id",
    pl.col("ret_4h").alias("btc_ret_4h"),
    pl.col("ret_12h").alias("btc_ret_12h"),
    pl.col("ret_72h").alias("btc_ret_72h")
]).unique(subset=["group_id"])

df = df.join(btc_panel, on="group_id", how="left")

# 3. Composite Alpha
df = df.with_columns([
    (
        -0.35 * ((pl.col("ret_4h") - pl.col("beta_btc") * pl.col("btc_ret_4h")) / (pl.col("vol_yang_zhang") + 1e-5))
        -0.25 * ((pl.col("ret_12h") - pl.col("beta_btc") * pl.col("btc_ret_12h")) / (pl.col("vol_yang_zhang") + 1e-5))
        +0.40 * ((pl.col("ret_72h") - pl.col("beta_btc") * pl.col("btc_ret_72h")) / (pl.col("vol_yang_zhang") + 1e-5))
    ).alias("raw_alpha")
])

df = df.sort(["symbol", "group_id"]).with_columns([
    pl.col("raw_alpha").ewm_mean(span=6).over("symbol").alias("smoothed_alpha")
])

eval_groups = [g for g in all_groups if g >= WARMUP_BARS]

# Target Volatility Frontier:
# Mode 0: Exp 7 Benchmark (33% realized vol)
# Mode 1: 50% Target Vol (Gross Leverage ~5.5x)
# Mode 2: 65% Target Vol (Gross Leverage ~7.5x)
# Mode 3: 65% Target Vol + Hourly Funding Yield Capture (40% APR basis)
MODES = ["33% Vol (Exp 7)", "50% Target Vol", "65% Target Vol", "65% Vol + Funding Yield"]
TARGET_VOLS = [0.33, 0.50, 0.65, 0.65]

navs = [10_000.0] * 4
total_turnovers = [0.0] * 4
prev_weights = [{}, {}, {}, {}]
active_longs = [set(), set(), set(), set()]
active_shorts = [set(), set(), set(), set()]
returns_hist = [[], [], [] ,[]]

def safe_val(d, k, default=0.0):
    v = d.get(k)
    if v is None: return default
    try:
        f = float(v)
        return default if np.isnan(f) else f
    except:
        return default

# Hyperliquid average hourly funding yield on short overbought alts (~0.005% per hour = ~43% APR)
HOURLY_FUNDING_YIELD = 0.00005

t0 = time.time()
print(f"[+] Running Full-Kelly simulation across {len(eval_groups) - 1:,} hourly bars...")

for idx in range(len(eval_groups) - 1):
    grp = eval_groups[idx]
    next_grp = eval_groups[idx + 1]

    cur_panel = df.filter(pl.col("group_id") == grp)
    valid_panel = cur_panel.filter(
        (pl.col("dollar_volume_1h") > 25_000) &
        pl.col("smoothed_alpha").is_not_null() &
        pl.col("vol_yang_zhang").is_not_null()
    )

    if valid_panel.height < 35:
        continue

    returns_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["next_ret_1h"].to_list()))
    vols_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["vol_yang_zhang"].to_list()))

    sorted_alpha = valid_panel.sort("smoothed_alpha", descending=True)
    all_ranked = sorted_alpha["symbol"].to_list()
    rank_map = {s: i for i, s in enumerate(all_ranked)}

    is_rebal = (idx % 4 == 0)

    for m in range(4):
        if is_rebal:
            for s in all_ranked[:K_ENTRY]: active_longs[m].add(s)
            for s in all_ranked[-K_ENTRY:]: active_shorts[m].add(s)

            active_longs[m] = {s for s in active_longs[m] if rank_map.get(s, 999) < K_EXIT}
            active_shorts[m] = {s for s in active_shorts[m] if rank_map.get(s, -1) >= (len(all_ranked) - K_EXIT)}
            active_longs[m] -= active_shorts[m]

            active_syms = active_longs[m].union(active_shorts[m])
            if len(active_syms) < 16:
                raw_target = prev_weights[m]
            else:
                inv_vols = {s: 1.0 / max(0.015, safe_val(vols_map, s, 0.025)) for s in active_syms}
                raw_w = {}
                for s in active_syms:
                    raw_w[s] = inv_vols[s] if s in active_longs[m] else -inv_vols[s]

                l_sum = sum(w for w in raw_w.values() if w > 0)
                s_sum = sum(abs(w) for w in raw_w.values() if w < 0)
                for s in raw_w:
                    if raw_w[s] > 0 and l_sum > 0: raw_w[s] /= (2.0 * l_sum)
                    elif raw_w[s] < 0 and s_sum > 0: raw_w[s] /= (2.0 * s_sum)

                mean_asset_vol = np.mean([safe_val(vols_map, s, 0.025) for s in active_syms])
                port_bar_vol = max(0.005, mean_asset_vol * 0.35)

                target_bar_vol = TARGET_VOLS[m] / np.sqrt(BARS_PER_YEAR)
                # Uncap leverage bounds to allow higher target volatility
                max_lev = 5.00 if m == 0 else (7.00 if m == 1 else 9.00)
                lev = float(np.clip(target_bar_vol / port_bar_vol, 1.00, max_lev))
                raw_target = {s: raw_w[s] * lev for s in raw_w if abs(raw_w[s] * lev) > 0.002}
        else:
            raw_target = prev_weights[m]

        # Leland Deadband
        dispatched = {}
        all_syms = set(prev_weights[m].keys()).union(raw_target.keys())

        for s in all_syms:
            w_t = raw_target.get(s, 0.0)
            w_prev = prev_weights[m].get(s, 0.0)
            sigma = max(0.015, safe_val(vols_map, s, 0.025))

            if abs(w_t) < 1e-4 or abs(w_prev) < 1e-4 or (w_t * w_prev < 0):
                dispatched[s] = w_t
                continue

            h_star = np.clip(((4.0 / 3.0) * (FEE_RATE * (sigma ** 2.0)) / GAMMA_MVO) ** (1.0 / 3.0) * 1.5, 0.020, 0.050)
            delta = w_t - w_prev
            if abs(delta) > h_star:
                dispatched[s] = w_t - np.sign(delta) * h_star
            else:
                dispatched[s] = w_prev

        dispatched = {s: w for s, w in dispatched.items() if abs(w) > 0.002}

        to = sum(abs(dispatched.get(s, 0.0) - prev_weights[m].get(s, 0.0)) for s in all_syms)
        total_turnovers[m] += to
        cost = to * FEE_RATE

        # Mode 3 captures hourly funding on the short leg
        funding_pnl = 0.0
        if m == 3:
            short_exposure = sum(abs(w) for w in dispatched.values() if w < 0)
            funding_pnl = short_exposure * HOURLY_FUNDING_YIELD

        pnl = sum(dispatched.get(s, 0.0) * safe_val(returns_map, s, 0.0) for s in dispatched) - cost + funding_pnl
        navs[m] *= (1.0 + pnl)
        returns_hist[m].append(pnl)
        prev_weights[m] = dispatched

    if (idx + 1) % 2000 == 0:
        print(f"  • Processed {idx + 1:,}/{len(eval_groups) - 1:,} bars ({time.time() - t0:.1f}s)...")

# Summary Results
print("\n" + "=" * 96)
print("             EXPERIMENT 8: TRUE FULL-KELLY 10x COMPOUNDING FRONTIER")
print("=" * 96)
headers = ["Metric", MODES[0], MODES[1], MODES[2], MODES[3]]
print(f"{headers[0]:<28} | {headers[1]:<14} | {headers[2]:<14} | {headers[3]:<14} | {headers[4]:<16}")
print("-" * 96)

def calc_metrics(nav, rets, to):
    r = np.array(rets)
    total_ret = (nav / 10_000.0) - 1.0
    cagr = (nav / 10_000.0) ** (BARS_PER_YEAR / len(r)) - 1.0
    sharpe = np.mean(r) / (np.std(r) + 1e-6) * np.sqrt(BARS_PER_YEAR)
    vol = np.std(r) * np.sqrt(BARS_PER_YEAR)
    cum = np.cumprod(1.0 + r)
    mdd = np.min((cum - np.maximum.accumulate(cum)) / np.maximum.accumulate(cum))
    mult = nav / 10_000.0
    return mult, total_ret, cagr, sharpe, vol, mdd, to / len(r), to

res = [calc_metrics(navs[i], returns_hist[i], total_turnovers[i]) for i in range(4)]

print(f"{'Terminal Equity Multiple':<28} | {res[0][0]:>13.2f}x | {res[1][0]:>13.2f}x | {res[2][0]:>13.2f}x | {res[3][0]:>15.2f}x")
print(f"{'Cumulative Net Return':<28} | {res[0][1]*100:>+12.1f}% | {res[1][1]*100:>+12.1f}% | {res[2][1]*100:>+12.1f}% | {res[3][1]*100:>+14.1f}%")
print(f"{'Annualized CAGR':<28} | {res[0][2]*100:>+12.1f}% | {res[1][2]*100:>+12.1f}% | {res[2][2]*100:>+12.1f}% | {res[3][2]*100:>+14.1f}%")
print(f"{'Net Sharpe Ratio':<28} | {res[0][3]:>14.2f} | {res[1][3]:>14.2f} | {res[2][3]:>14.2f} | {res[3][3]:>16.2f}")
print(f"{'Realized Annual Volatility':<28} | {res[0][4]*100:>13.1f}% | {res[1][4]*100:>13.1f}% | {res[2][4]*100:>13.1f}% | {res[3][4]*100:>15.1f}%")
print(f"{'Max Drawdown':<28} | {res[0][5]*100:>13.1f}% | {res[1][5]*100:>13.1f}% | {res[2][5]*100:>13.1f}% | {res[3][5]*100:>15.1f}%")
print(f"{'Total Annualized Volume':<28} | {res[0][7]*(BARS_PER_YEAR/len(returns_hist[0])):>13.0f}x | {res[1][7]*(BARS_PER_YEAR/len(returns_hist[1])):>13.0f}x | {res[2][7]*(BARS_PER_YEAR/len(returns_hist[2])):>13.0f}x | {res[3][7]*(BARS_PER_YEAR/len(returns_hist[3])):>15.0f}x")
print("=" * 96)
