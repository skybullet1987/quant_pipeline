import time
from pathlib import Path
import numpy as np
import polars as pl
from sklearn.covariance import LedoitWolf

print("=" * 86)
print("   UNCONSTRAINED FULL-UNIVERSE 1H BACKTEST: ALO MAKER VS TAKER EXECUTION")
print("=" * 86)

LAKE_PATH = Path.home() / "quant_pipeline" / "data" / "lake" / "features" / "pit_panel_1h_full.parquet"
if not LAKE_PATH.exists():
    print(f"[!] Target feature lake {LAKE_PATH} does not exist.")
    exit(1)

df = pl.read_parquet(LAKE_PATH)

# Ensure group_id indexing
if "group_id" not in df.columns:
    unique_ts = df.select("timestamp_ms").unique().sort("timestamp_ms").with_columns(
        pl.int_range(0, pl.len()).alias("group_id")
    )
    df = df.join(unique_ts, on="timestamp_ms", how="left")

all_groups = sorted(df.select("group_id").unique().to_series().to_list())
print(f"[+] Loaded {df.height:,} rows across {df['symbol'].n_unique()} symbols and {len(all_groups):,} 1H bars")

# Simulation Parameters
BARS_PER_YEAR = 24 * 365
WARMUP_BARS = 168         # 7 days lookback for rolling covariance
TOP_K = 18                 # Top 18 Longs / Top 18 Shorts across the unconstrained universe
TARGET_ANN_VOL = 0.35      # 35% Target Volatility (Half-Kelly)
TARGET_BAR_VOL = TARGET_ANN_VOL / np.sqrt(BARS_PER_YEAR)
GAMMA_MVO = 0.05

# Execution Cost Models
# Taker: 4.5 bps base fee + 2.0 bps half-spread / impact = 6.5 bps per unit
# Base tier Hyperliquid maker is ~1.5 bps; with passive limit post-only and spread capture, net friction is near 0.0
COST_TAKER = 0.00045
COST_MAKER_CONSERVATIVE = 0.00000 
COST_MAKER_REBATE = -0.00005     # Passive spread capture / maker rebate (-0.5 bps net)

eval_groups = [g for g in all_groups if g >= WARMUP_BARS]

# Precompute forward returns and fill nulls with 0.0
print("[+] Aligning next 1H forward returns...")
df = df.sort(["symbol", "group_id"]).with_columns([
    (pl.col("close").shift(-1).over("symbol") / pl.col("close") - 1.0).fill_null(0.0).alias("next_ret_1h")
])

# Alpha Signal: Multi-Horizon Residual Drift scaled by Inverse Volatility
print("[+] Computing composite residual momentum alpha...")
btc_panel = df.filter(pl.col("symbol") == "BTC").select([
    "group_id",
    pl.col("ret_4h").alias("btc_ret_4h"),
    pl.col("ret_12h").alias("btc_ret_12h"),
    pl.col("ret_24h").alias("btc_ret_24h")
]).unique(subset=["group_id"])

df = df.join(btc_panel, on="group_id", how="left")

df = df.with_columns([
    (
        0.30 * ((pl.col("ret_4h") - pl.col("beta_btc") * pl.col("btc_ret_4h")) / (pl.col("vol_yang_zhang") + 1e-5)) +
        0.45 * ((pl.col("ret_12h") - pl.col("beta_btc") * pl.col("btc_ret_12h")) / (pl.col("vol_yang_zhang") + 1e-5)) +
        0.25 * ((pl.col("ret_24h") - pl.col("beta_btc") * pl.col("btc_ret_24h")) / (pl.col("vol_yang_zhang") + 1e-5))
    ).alias("composite_alpha")
])

# Simulation Tracking
modes = ["Taker (4.5 bps drag)", "ALO Maker (0.0 bps net)", "ALO Maker (-0.5 bps rebate)"]
costs = [COST_TAKER, COST_MAKER_CONSERVATIVE, COST_MAKER_REBATE]

navs = [10_000.0, 10_000.0, 10_000.0]
total_turnovers = [0.0, 0.0, 0.0]
prev_weights = [{}, {}, {}]
returns_hist = [[], [], []]

cached_cov = None
cached_symbols = []
last_cov_grp = -1

def safe_val(d, k, default=0.0):
    v = d.get(k)
    if v is None:
        return default
    try:
        f = float(v)
        return default if np.isnan(f) else f
    except (TypeError, ValueError):
        return default

t0 = time.time()
print(f"[+] Commencing simulation across {len(eval_groups) - 1:,} hourly steps...")

for idx in range(len(eval_groups) - 1):
    grp = eval_groups[idx]
    next_grp = eval_groups[idx + 1]

    cur_panel = df.filter(pl.col("group_id") == grp)
    if cur_panel.height < 30:
        continue

    # Liquidity filter: minimum $20k hourly volume to eliminate illiquid tails
    valid_panel = cur_panel.filter(
        (pl.col("dollar_volume_1h") > 20_000) &
        pl.col("composite_alpha").is_not_null() &
        pl.col("vol_yang_zhang").is_not_null()
    )

    if valid_panel.height < (TOP_K * 2):
        continue

    # Cross-sectional selection: Top K Longs and Bottom K Shorts
    sorted_alpha = valid_panel.sort("composite_alpha", descending=True)
    long_basket = sorted_alpha.head(TOP_K)["symbol"].to_list()
    short_basket = sorted_alpha.tail(TOP_K)["symbol"].to_list()
    active_symbols = set(long_basket + short_basket)

    returns_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["next_ret_1h"].to_list()))
    vols_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["vol_yang_zhang"].to_list()))

    # Update Ledoit-Wolf covariance every 24 bars (daily) across active assets
    if cached_cov is None or (grp - last_cov_grp) >= 24 or not active_symbols.issubset(set(cached_symbols)):
        hist = df.filter((pl.col("group_id") <= grp) & (pl.col("group_id") > grp - 72) & (pl.col("symbol").is_in(list(active_symbols))))
        piv = hist.pivot(values="ret_1h", index="group_id", on="symbol").sort("group_id")
        v_cols = [c for c in active_symbols if c in piv.columns and piv[c].null_count() == 0]
        
        if len(v_cols) < (TOP_K * 2):
            v_cols = list(active_symbols)
            cov_mat = np.diag([max(0.015, safe_val(vols_map, s, 0.025))**2 for s in v_cols])
        else:
            cov_mat = LedoitWolf().fit(piv.select(v_cols).to_numpy()).covariance_
        
        cached_cov = cov_mat
        cached_symbols = v_cols
        last_cov_grp = grp

    v_cols = cached_symbols
    inv_vols = np.array([1.0 / max(0.015, safe_val(vols_map, s, 0.025)) for s in v_cols])
    
    # Dollar-neutral allocation: +weight on longs, -weight on shorts
    raw_w = np.zeros(len(v_cols))
    for i, s in enumerate(v_cols):
        if s in long_basket:
            raw_w[i] = inv_vols[i]
        elif s in short_basket:
            raw_w[i] = -inv_vols[i]

    # Normalize long and short legs to 1.0 unit gross
    l_sum = np.sum(raw_w[raw_w > 0])
    s_sum = np.sum(np.abs(raw_w[raw_w < 0]))
    if l_sum > 0: raw_w[raw_w > 0] /= l_sum
    if s_sum > 0: raw_w[raw_w < 0] /= s_sum
    w_unit = raw_w / 2.0  # Sum of abs weights = 1.0

    # Ex-Ante Volatility Targeting
    port_var = float(w_unit.T @ cached_cov @ w_unit)
    port_vol = np.sqrt(max(port_var, 1e-8))
    lev_target = float(np.clip(TARGET_BAR_VOL / port_vol, 0.50, 4.00))
    w_scaled = w_unit * lev_target
    raw_target = {v_cols[i]: float(w_scaled[i]) for i in range(len(v_cols)) if abs(w_scaled[i]) > 0.002}

    # Evaluate across the 3 execution variants
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

            # Leland Deadband
            h_star = np.clip(((4.0 / 3.0) * (fee_rate * (sigma ** 2.0)) / GAMMA_MVO) ** (1.0 / 3.0), 0.008, 0.030)
            delta = w_t - w_prev
            if abs(delta) > h_star:
                dispatched[s] = w_t - np.sign(delta) * h_star
            else:
                dispatched[s] = w_prev

        dispatched = {s: w for s, w in dispatched.items() if abs(w) > 0.002}

        # Safe PnL calculation: guaranteed numeric values
        to = sum(abs(dispatched.get(s, 0.0) - prev_weights[m].get(s, 0.0)) for s in all_syms)
        total_turnovers[m] += to
        trade_cost = to * costs[m]
        pnl = sum(dispatched.get(s, 0.0) * safe_val(returns_map, s, 0.0) for s in dispatched) - trade_cost
        navs[m] *= (1.0 + pnl)
        returns_hist[m].append(pnl)
        prev_weights[m] = dispatched

    if (idx + 1) % 2000 == 0:
        print(f"  • Progress: {idx + 1:,}/{len(eval_groups) - 1:,} bars ({time.time() - t0:.1f}s elapsed)...")

# Summary Results
print("\n" + "=" * 86)
print("             1-YEAR 1H UNCONSTRAINED UNIVERSE BENCHMARK RESULTS")
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
