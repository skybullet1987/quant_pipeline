import numpy as np
import polars as pl
from pathlib import Path

print("=" * 96)
print("   EXPERIMENT 12: ORTHOGONAL MULTI-FACTOR ENGINE ON THE 58.2-DAY OOS")
print("=" * 96)

LAKE_PATH = Path.home() / "quant_pipeline" / "data" / "lake" / "features" / "pit_panel_1h_full.parquet"
df = pl.read_parquet(LAKE_PATH)

if "group_id" not in df.columns:
    unique_ts = df.select("timestamp_ms").unique().sort("timestamp_ms").with_columns(
        pl.int_range(0, pl.len()).alias("group_id")
    )
    df = df.join(unique_ts, on="timestamp_ms", how="left")

BARS_PER_YEAR = 24 * 365
FEE_RATE = 0.00015
GAMMA_MVO = 0.05
K_ENTRY = 10
K_EXIT = 30
REBAL_CLOCK = 6  # 6-hour execution clock

# 1. Forward Returns
df = df.sort(["symbol", "group_id"]).with_columns([
    (pl.col("close").shift(-1).over("symbol") / pl.col("close") - 1.0).fill_null(0.0).alias("next_ret_1h")
])

# 2. Align BTC
btc = df.filter(pl.col("symbol") == "BTC").select([
    "group_id",
    pl.col("ret_72h").alias("btc_ret_72h")
]).unique(subset=["group_id"])
df = df.join(btc, on="group_id", how="left")

# 3. Construct Orthogonal Signals
# S1: Clean 72H Residual Momentum (pure drift)
# S2: Volume-Volatility Exhaustion (fading volume spikes on extended assets)
# S3: Funding Carry Proxy (assets with low basis / low volatility trend)
df = df.with_columns([
    ((pl.col("ret_72h") - pl.col("beta_btc") * pl.col("btc_ret_72h")) / (pl.col("vol_yang_zhang") + 1e-5)).fill_null(0.0).alias("sig_drift_72h"),
    (-pl.col("ret_24h").sign() * pl.col("volume_zscore_72h").clip(0.0, 3.0)).fill_null(0.0).alias("sig_volume_exhaustion"),
    (-pl.col("ret_12h") / (pl.col("vol_yang_zhang") + 1e-5)).fill_null(0.0).alias("sig_mean_reversion_12h")
])

# Normalize cross-sectionally to z-scores per group
df = df.with_columns([
    ((pl.col("sig_drift_72h") - pl.col("sig_drift_72h").mean().over("group_id")) / (pl.col("sig_drift_72h").std().over("group_id") + 1e-6)).alias("z_drift"),
    ((pl.col("sig_volume_exhaustion") - pl.col("sig_volume_exhaustion").mean().over("group_id")) / (pl.col("sig_volume_exhaustion").std().over("group_id") + 1e-6)).alias("z_exhaustion"),
    ((pl.col("sig_mean_reversion_12h") - pl.col("sig_mean_reversion_12h").mean().over("group_id")) / (pl.col("sig_mean_reversion_12h").std().over("group_id") + 1e-6)).alias("z_reversion")
])

# Composite Balanced Multi-Factor
df = df.with_columns([
    (0.40 * pl.col("z_drift") + 0.35 * pl.col("z_exhaustion") + 0.25 * pl.col("z_reversion")).alias("composite_multifactor")
])

# Smooth composite factor via 6-bar EMA
df = df.sort(["symbol", "group_id"]).with_columns([
    pl.col("composite_multifactor").ewm_mean(span=6).over("symbol").alias("smoothed_multifactor")
])

# Isolate OOS
valid_counts = df.filter(pl.col("dollar_volume_1h") > 25_000).group_by("group_id").len()
active_grps = sorted(valid_counts.filter(pl.col("len") >= 35)["group_id"].to_list())
split_idx = int(len(active_grps) * 0.70)
oos_grps = active_grps[split_idx:]

print(f"[+] Evaluating on the identical 58.2-day OOS period ({len(oos_grps)} bars)...")

def safe_val(d, k, default=0.0):
    v = d.get(k)
    if v is None: return default
    try:
        f = float(v)
        return default if np.isnan(f) else f
    except:
        return default

# Compare 3 variants on OOS:
# 1. Fixed 4.6x Multi-Factor (No leverage gating)
# 2. Dynamic Gated Multi-Factor (1.5x in low dispersion, 4.2x in high dispersion)
# 3. Dynamic Gated Multi-Factor + Funding Carry Overlay (50% APR basis on short basket)
MODES = ["Fixed 4.6x Multi-Factor", "Dynamic Gated (1.5x-4.2x)", "Dynamic Gated + Funding Carry"]

navs = [10_000.0] * 3
turnovers = [0.0] * 3
prev_dispatched = [{}, {}, {}]
active_longs = [set(), set(), set()]
active_shorts = [set(), set(), set()]
returns_hist = [[], [], []]

BASE_FUNDING = 0.00005

for idx, grp in enumerate(oos_grps[:-1]):
    cur_panel = df.filter(pl.col("group_id") == grp)
    valid_panel = cur_panel.filter(
        (pl.col("dollar_volume_1h") > 25_000) &
        pl.col("vol_yang_zhang").is_not_null()
    )
    if valid_panel.height < 35:
        continue

    returns_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["next_ret_1h"].to_list()))
    vols_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["vol_yang_zhang"].to_list()))

    alpha_map = dict(zip(valid_panel["symbol"].to_list(), valid_panel["smoothed_multifactor"].to_list()))
    sorted_pairs = sorted(alpha_map.items(), key=lambda x: x[1], reverse=True)
    all_ranked = [p[0] for p in sorted_pairs]
    rank_map = {s: i for i, s in enumerate(all_ranked)}

    # Dispersion metric: standard deviation of composite alpha
    alpha_dispersion = float(valid_panel["smoothed_multifactor"].std())

    is_rebal = (idx % REBAL_CLOCK == 0)

    for m in range(3):
        if is_rebal:
            for s in all_ranked[:K_ENTRY]: active_longs[m].add(s)
            for s in all_ranked[-K_ENTRY:]: active_shorts[m].add(s)

            active_longs[m] = {s for s in active_longs[m] if rank_map.get(s, 999) < K_EXIT}
            active_shorts[m] = {s for s in active_shorts[m] if rank_map.get(s, -1) >= (len(all_ranked) - K_EXIT)}
            active_longs[m] -= active_shorts[m]

            active_syms = active_longs[m].union(active_shorts[m])
            if len(active_syms) < 16:
                raw_target = prev_dispatched[m]
            else:
                inv_vols = {s: 1.0 / max(0.015, safe_val(vols_map, s, 0.025)) for s in active_syms}
                raw_w = {}
                for s in active_syms:
                    raw_w[s] = inv_vols[s] if s in active_longs[m] else -inv_vols[s]

                l_sum = sum(w for w in raw_w.values() if w > 0)
                s_sum = sum(abs(w) for w in raw_w.values() if w < 0)

                # Leverage sizing
                if m == 0:
                    gross_lev = 4.60
                else:
                    # Gating: scale between 1.5x and 4.2x based on dispersion
                    disp_factor = np.clip((alpha_dispersion - 0.50) / 0.50, 0.0, 1.0)
                    gross_lev = 1.50 + (4.20 - 1.50) * disp_factor

                target_leg = gross_lev / 2.0
                raw_target = {}
                for s in raw_w:
                    if raw_w[s] > 0 and l_sum > 0: raw_target[s] = (raw_w[s] / l_sum) * target_leg
                    elif raw_w[s] < 0 and s_sum > 0: raw_target[s] = (raw_w[s] / s_sum) * target_leg
        else:
            raw_target = prev_dispatched[m]

        # Leland Deadband
        dispatched = {}
        all_syms = set(prev_dispatched[m].keys()).union(raw_target.keys())
        for s in all_syms:
            w_t = raw_target.get(s, 0.0)
            w_prev_s = prev_dispatched[m].get(s, 0.0)
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

        to = sum(abs(dispatched.get(s, 0.0) - prev_dispatched[m].get(s, 0.0)) for s in all_syms)
        turnovers[m] += to
        cost = to * FEE_RATE

        fund_pnl = 0.0
        if m == 2:
            short_exp = sum(abs(w) for w in dispatched.values() if w < 0)
            fund_pnl = short_exp * BASE_FUNDING

        net_pnl = sum(dispatched.get(s, 0.0) * safe_val(returns_map, s, 0.0) for s in dispatched) - cost + fund_pnl

        navs[m] *= (1.0 + net_pnl)
        returns_hist[m].append(net_pnl)
        prev_dispatched[m] = dispatched

print("\n" + "=" * 96)
print("             EXPERIMENT 12: OUT-OF-SAMPLE RESULTS (58.2 DAYS)")
print("=" * 96)
headers = ["Performance Metric", MODES[0], MODES[1], MODES[2]]
print(f"{headers[0]:<30} | {headers[1]:<20} | {headers[2]:<20} | {headers[3]:<20}")
print("-" * 96)

def calc_metrics(nav, rets, to):
    r = np.array(rets)
    total_ret = (nav / 10_000.0) - 1.0
    cagr = (nav / 10_000.0) ** (BARS_PER_YEAR / len(r)) - 1.0
    sharpe = np.mean(r) / (np.std(r) + 1e-6) * np.sqrt(BARS_PER_YEAR)
    vol = np.std(r) * np.sqrt(BARS_PER_YEAR)
    cum = np.cumprod(1.0 + r)
    mdd = np.min((cum - np.maximum.accumulate(cum)) / np.maximum.accumulate(cum))
    downside_r = r[r < 0]
    sortino = np.mean(r) / (np.std(downside_r) + 1e-6) * np.sqrt(BARS_PER_YEAR) if len(downside_r) > 0 else 0.0
    return nav / 10_000.0, cagr, sharpe, sortino, mdd, vol, to * (BARS_PER_YEAR / len(r))

res = [calc_metrics(navs[i], returns_hist[i], turnovers[i]) for i in range(3)]

print(f"{'Terminal Multiple (58.2d)':<30} | {res[0][0]:>18.2f}x | {res[1][0]:>18.2f}x | {res[2][0]:>18.2f}x")
print(f"{'Annualized CAGR':<30} | {res[0][1]*100:>17.1f}% | {res[1][1]*100:>17.1f}% | {res[2][1]*100:>17.1f}%")
print(f"{'Net Sharpe Ratio (After Fees)':<30} | {res[0][2]:>20.2f} | {res[1][2]:>20.2f} | {res[2][2]:>20.2f}")
print(f"{'Sortino Ratio':<30} | {res[0][3]:>20.2f} | {res[1][3]:>20.2f} | {res[2][3]:>20.2f}")
print(f"{'Max Drawdown':<30} | {res[0][4]*100:>19.1f}% | {res[1][4]*100:>19.1f}% | {res[2][4]*100:>19.1f}%")
print(f"{'Realized Annual Volatility':<30} | {res[0][5]*100:>19.1f}% | {res[1][5]*100:>19.1f}% | {res[2][5]*100:>19.1f}%")
print(f"{'Annualized Turnover Volume':<30} | {res[0][6]:>17.0f}x | {res[1][6]:>17.0f}x | {res[2][6]:>17.0f}x")
print("=" * 96)
