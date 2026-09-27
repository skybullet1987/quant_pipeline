import time
from pathlib import Path
import numpy as np
import polars as pl
from sklearn.covariance import LedoitWolf

print("=" * 86)
print("   STABILIZED FULL-UNIVERSE 1H BENCHMARK: HYSTERESIS + ALPHA SMOOTHING")
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
TARGET_ANN_VOL = 0.35
TARGET_BAR_VOL = TARGET_ANN_VOL / np.sqrt(BARS_PER_YEAR)
GAMMA_MVO = 0.05

# Hysteresis Limits
K_ENTRY = 12   # Stricter entry threshold
K_EXIT = 24    # Relaxed exit buffer

# Realistic Hyperliquid fee structure: 0.015% maker, 0.045% taker
COST_TAKER = 0.00045
COST_MAKER = 0.00015
COST_MAKER_PASSIVE = 0.00000  # Capturing spread at BBO

# Forward returns
df = df.sort(["symbol", "group_id"]).with_columns([
    (pl.col("close").shift(-1).over("symbol") / pl.col("close") - 1.0).fill_null(0.0).alias("next_ret_1h")
])

# Align BTC benchmarks
btc_panel = df.filter(pl.col("symbol") == "BTC").select([
    "group_id",
    pl.col("ret_4h").alias("btc_ret_4h"),
    pl.col("ret_12h").alias("btc_ret_12h"),
    pl.col("ret_72h").alias("btc_ret_72h")
]).unique(subset=["group_id"])

df = df.join(btc_panel, on="group_id", how="left")

# Corrected Alpha: Fade short-term noise (4h/12h reversion), ride medium-term drift (72h trend)
df = df.with_columns([
    (
        -0.35 * ((pl.col("ret_4h") - pl.col("beta_btc") * pl.col("btc_ret_4h")) / (pl.col("vol_yang_zhang") + 1e-5))
        -0.25 * ((pl.col("ret_12h") - pl.col("beta_btc") * pl.col("btc_ret_12h")) / (pl.col("vol_yang_zhang") + 1e-5))
        +0.40 * ((pl.col("ret_72h") - pl.col("beta_btc") * pl.col("btc_ret_72h")) / (pl.col("vol_yang_zhang") + 1e-5))
    ).alias("raw_alpha")
])

# Alpha Smoothing (6-period rolling EMA over symbol)
print("[+] Smoothing alpha signals via 6-hour exponential filter...")
df = df.sort(["symbol", "group_id"]).with_columns([
    pl.col("raw_alpha").ewm_mean(span=6).over("symbol").alias("smoothed_alpha")
])

eval_groups = [g for g in all_groups if g >= WARMUP_BARS]

modes = ["Taker (4.5 bps)", "ALO Maker (1.5 bps)", "ALO Passive (0.0 bps)"]
costs = [COST_TAKER, COST_MAKER, COST_MAKER_PASSIVE]

navs = [10_000.0, 10_000.0, 10_000.0]
total_turnovers = [0.0, 0.0, 0.0]
prev_weights = [{}, {}, {}]
active_longs = set()
active_shorts = set()
returns_hist = [[], [], []]

def safe_val(d, k, default=0.0):
    v = d.get(k)
    if v is None: return default
    try:
        f = float(v)
        return default if np.isnan(f) else f
    except:
        return default

cached_cov = None
cached_symbols = []
last_cov_grp = -1

t0 = time.time()
print(f"[+] Simulating across {len(eval_groups) - 1:,} hourly steps with hysteresis...")

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

    sorted_alpha = valid_panel.sort("smoothed_alpha", descending=True)
    all_ranked = sorted_alpha["symbol"].to_list()
    rank_map = {s: i for i, s in enumerate(all_ranked)}

    # Apply Hysteresis Buffer
    # Add new entries if in top/bottom K_ENTRY
    for s in all_ranked[:K_ENTRY]:
        active_longs.add(s)
    for s in all_ranked[-K_ENTRY:]:
        active_shorts.add(s)

    # Evict positions only if they degrade past K_EXIT
    active_longs = {s for s in active_longs if rank_map.get(s, 999) < K_EXIT}
    active_shorts = {s for s in active_shorts if rank_map.get(s, -1) >= (len(all_ranked) - K_EXIT)}

    # Remove overlaps
    active_longs -= active_shorts

    active_symbols = active_longs.union(active_shorts)
    if len(active_symbols) < 16:
        continue

    returns_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["next_ret_1h"].to_list()))
    vols_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["vol_yang_zhang"].to_list()))

    # Update covariance every 24 bars
    if cached_cov is None or (grp - last_cov_grp) >= 24 or not active_symbols.issubset(set(cached_symbols)):
        hist = df.filter((pl.col("group_id") <= grp) & (pl.col("group_id") > grp - 72) & (pl.col("symbol").is_in(list(active_symbols))))
        piv = hist.pivot(values="ret_1h", index="group_id", on="symbol").sort("group_id")
        v_cols = [c for c in active_symbols if c in piv.columns and piv[c].null_count() == 0]
        
        if len(v_cols) < 16:
            v_cols = list(active_symbols)
            cov_mat = np.diag([max(0.015, safe_val(vols_map, s, 0.025))**2 for s in v_cols])
        else:
            cov_mat = LedoitWolf().fit(piv.select(v_cols).to_numpy()).covariance_
        
        cached_cov = cov_mat
        cached_symbols = v_cols
        last_cov_grp = grp

    v_cols = cached_symbols
    inv_vols = np.array([1.0 / max(0.015, safe_val(vols_map, s, 0.025)) for s in v_cols])

    raw_w = np.zeros(len(v_cols))
    for i, s in enumerate(v_cols):
        if s in active_longs:
            raw_w[i] = inv_vols[i]
        elif s in active_shorts:
            raw_w[i] = -inv_vols[i]

    l_sum = np.sum(raw_w[raw_w > 0])
    s_sum = np.sum(np.abs(raw_w[raw_w < 0]))
    if l_sum > 0: raw_w[raw_w > 0] /= l_sum
    if s_sum > 0: raw_w[raw_w < 0] /= s_sum
    w_unit = raw_w / 2.0

    port_var = float(w_unit.T @ cached_cov @ w_unit)
    port_vol = np.sqrt(max(port_var, 1e-8))
    lev_target = float(np.clip(TARGET_BAR_VOL / port_vol, 0.50, 3.50))
    w_scaled = w_unit * lev_target
    raw_target = {v_cols[i]: float(w_scaled[i]) for i in range(len(v_cols)) if abs(w_scaled[i]) > 0.002}

    for m in range(3):
        dispatched = {}
        all_syms = set(prev_weights[m].keys()).union(raw_target.keys())
        fee_rate = max(0.00010, abs(costs[m]))

        for s in all_syms:
            w_t = raw_target.get(s, 0.0)
            w_prev = prev_weights[m].get(s, 0.0)
            sigma = max(0.015, safe_val(vols_map, s, 0.025))

            if abs(w_t) < 1e-4 or abs(w_prev) < 1e-4 or (w_t * w_prev < 0):
                dispatched[s] = w_t
                continue

            h_star = np.clip(((4.0 / 3.0) * (fee_rate * (sigma ** 2.0)) / GAMMA_MVO) ** (1.0 / 3.0), 0.008, 0.035)
            delta = w_t - w_prev
            if abs(delta) > h_star:
                dispatched[s] = w_t - np.sign(delta) * h_star
            else:
                dispatched[s] = w_prev

        dispatched = {s: w for s, w in dispatched.items() if abs(w) > 0.002}

        to = sum(abs(dispatched.get(s, 0.0) - prev_weights[m].get(s, 0.0)) for s in all_syms)
        total_turnovers[m] += to
        trade_cost = to * costs[m]
        pnl = sum(dispatched.get(s, 0.0) * safe_val(returns_map, s, 0.0) for s in dispatched) - trade_cost
        navs[m] *= (1.0 + pnl)
        returns_hist[m].append(pnl)
        prev_weights[m] = dispatched

    if (idx + 1) % 2000 == 0:
        print(f"  • Processed {idx + 1:,}/{len(eval_groups) - 1:,} bars ({time.time() - t0:.1f}s)...")

# Summary
print("\n" + "=" * 86)
print("       STABILIZED FULL-UNIVERSE 1H BENCHMARK RESULTS")
print("=" * 86)
headers = ["Metric", modes[0], modes[1], modes[2]]
print(f"{headers[0]:<28} | {headers[1]:<17} | {headers[2]:<17} | {headers[3]:<17}")
print("-" * 86)

def calc_metrics(nav, rets, to):
    r = np.array(rets)
    total_ret = (nav / 10_000.0) - 1.0
    cagr = (nav / 10_000.0) ** (BARS_PER_YEAR / len(r)) - 1.0
    sharpe = np.mean(r) / (np.std(r) + 1e-6) * np.sqrt(BARS_PER_YEAR)
    vol = np.std(r) * np.sqrt(BARS_PER_YEAR)
    cum = np.cumprod(1.0 + r)
    mdd = np.min((cum - np.maximum.accumulate(cum)) / np.maximum.accumulate(cum))
    mult = nav / 10_000.0
    return mult, total_ret, cagr, sharpe, vol, mdd, to / len(r)

res = [calc_metrics(navs[i], returns_hist[i], total_turnovers[i]) for i in range(3)]

print(f"{'Terminal Equity Multiple':<28} | {res[0][0]:>16.2f}x | {res[1][0]:>16.2f}x | {res[2][0]:>16.2f}x")
print(f"{'Cumulative Net Return':<28} | {res[0][1]*100:>+15.2f}% | {res[1][1]*100:>+15.2f}% | {res[2][1]*100:>+15.2f}%")
print(f"{'Annualized CAGR':<28} | {res[0][2]*100:>+15.2f}% | {res[1][2]*100:>+15.2f}% | {res[2][2]*100:>+15.2f}%")
print(f"{'Net Sharpe Ratio':<28} | {res[0][3]:>17.2f} | {res[1][3]:>17.2f} | {res[2][3]:>17.2f}")
print(f"{'Realized Annual Volatility':<28} | {res[0][4]*100:>16.2f}% | {res[1][4]*100:>16.2f}% | {res[2][4]*100:>16.2f}%")
print(f"{'Max Drawdown':<28} | {res[0][5]*100:>16.2f}% | {res[1][5]*100:>16.2f}% | {res[2][5]*100:>16.2f}%")
print(f"{'Mean Turnover per 1H Bar':<28} | {res[0][6]:>16.2f}x | {res[1][6]:>16.2f}x | {res[2][6]:>16.2f}x")
print(f"{'Annualized Volume Traded':<28} | {res[0][6]*BARS_PER_YEAR:>15.0f}x | {res[1][6]*BARS_PER_YEAR:>15.0f}x | {res[2][6]*BARS_PER_YEAR:>15.0f}x")
print("=" * 86)
