import time
from pathlib import Path
import numpy as np
import polars as pl

print("=" * 96)
print("   EXPERIMENT 10: ADVERSARIAL STRESS TESTING & PURE CHRONOLOGICAL HOLDOUT")
print("=" * 96)

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
GAMMA_MVO = 0.05
BASE_FUNDING = 0.00005  # ~43% APR on short basket

# Forward returns
df = df.sort(["symbol", "group_id"]).with_columns([
    (pl.col("close").shift(-1).over("symbol") / pl.col("close") - 1.0).fill_null(0.0).alias("next_ret_1h")
])

# BTC Benchmark & EMA200
btc_panel = df.filter(pl.col("symbol") == "BTC").select([
    "group_id", "close",
    pl.col("ret_4h").alias("btc_ret_4h"),
    pl.col("ret_12h").alias("btc_ret_12h"),
    pl.col("ret_72h").alias("btc_ret_72h")
]).unique(subset=["group_id"]).sort("group_id")

btc_close = btc_panel["close"].to_numpy()
btc_ema200 = pl.Series(btc_close).ewm_mean(span=200).to_numpy()
btc_bull_map = {grp: (btc_close[i] > btc_ema200[i]) for i, grp in enumerate(btc_panel["group_id"].to_list())}

df = df.join(btc_panel.select(["group_id", "btc_ret_4h", "btc_ret_12h", "btc_ret_72h"]), on="group_id", how="left")

# Composite Alpha Signal
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

def safe_val(d, k, default=0.0):
    v = d.get(k)
    if v is None: return default
    try:
        f = float(v)
        return default if np.isnan(f) else f
    except:
        return default

# Pre-run core target generation to keep exact parity across all stress tests
print("[+] Generating frozen Mode 2 target weights across all bars...")
target_weights_history = []
active_bars_info = []

active_longs = set()
active_shorts = set()
prev_w = {}

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
        target_weights_history.append({})
        active_bars_info.append(None)
        continue

    returns_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["next_ret_1h"].to_list()))
    vols_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["vol_yang_zhang"].to_list()))
    is_bull = btc_bull_map.get(grp, False)
    median_vol = float(valid_panel["vol_yang_zhang"].median())

    sorted_alpha = valid_panel.sort("smoothed_alpha", descending=True)
    all_ranked = sorted_alpha["symbol"].to_list()
    rank_map = {s: i for i, s in enumerate(all_ranked)}

    is_rebal = (idx % 4 == 0)
    if is_rebal:
        for s in all_ranked[:K_ENTRY]: active_longs.add(s)
        for s in all_ranked[-K_ENTRY:]: active_shorts.add(s)

        active_longs = {s for s in active_longs if rank_map.get(s, 999) < K_EXIT}
        active_shorts = {s for s in active_shorts if rank_map.get(s, -1) >= (len(all_ranked) - K_EXIT)}
        active_longs -= active_shorts

        active_syms = active_longs.union(active_shorts)
        if len(active_syms) < 16:
            raw_target = prev_w
        else:
            inv_vols = {s: 1.0 / max(0.015, safe_val(vols_map, s, 0.025)) for s in active_syms}
            raw_w = {}
            for s in active_syms:
                raw_w[s] = inv_vols[s] if s in active_longs else -inv_vols[s]

            l_sum = sum(w for w in raw_w.values() if w > 0)
            s_sum = sum(abs(w) for w in raw_w.values() if w < 0)

            # Target 4.60x gross (2.30x long, 2.30x short)
            target_leg = 2.30
            raw_target = {}
            for s in raw_w:
                if raw_w[s] > 0 and l_sum > 0: raw_target[s] = (raw_w[s] / l_sum) * target_leg
                elif raw_w[s] < 0 and s_sum > 0: raw_target[s] = (raw_w[s] / s_sum) * target_leg
    else:
        raw_target = prev_w

    # Leland Deadband
    dispatched = {}
    all_syms = set(prev_w.keys()).union(raw_target.keys())
    for s in all_syms:
        w_t = raw_target.get(s, 0.0)
        w_prev_s = prev_w.get(s, 0.0)
        sigma = max(0.015, safe_val(vols_map, s, 0.025))

        if abs(w_t) < 1e-4 or abs(w_prev_s) < 1e-4 or (w_t * w_prev_s < 0):
            dispatched[s] = w_t
            continue

        h_star = np.clip(((4.0 / 3.0) * (0.00015 * (sigma ** 2.0)) / GAMMA_MVO) ** (1.0 / 3.0) * 1.5, 0.020, 0.055)
        delta = w_t - w_prev_s
        if abs(delta) > h_star:
            dispatched[s] = w_t - np.sign(delta) * h_star
        else:
            dispatched[s] = w_prev_s

    dispatched = {s: w for s, w in dispatched.items() if abs(w) > 0.002}
    prev_w = dispatched
    target_weights_history.append(dispatched)
    active_bars_info.append({
        "grp": grp,
        "returns_map": returns_map,
        "vols_map": vols_map,
        "is_bull": is_bull,
        "median_vol": median_vol
    })

# Filter to only the active window where portfolio trades
active_indices = [i for i, info in enumerate(active_bars_info) if info is not None]
n_active = len(active_indices)
print(f"[+] Total Active Trading Bars: {n_active:,} (~{n_active/24:.1f} days)")

def run_simulation(fee_rate, funding_mult, gross_scale=1.0, subset_indices=None):
    if subset_indices is None:
        subset_indices = active_indices
    nav = 10_000.0
    turnover = 0.0
    prev_dispatched = {}
    returns = []
    gross_pnls = []
    fees_paid = []
    funding_collected = []
    daily_returns = []
    cur_day_rets = []

    for idx in subset_indices:
        info = active_bars_info[idx]
        weights = target_weights_history[idx]
        if not weights:
            continue

        scaled_w = {s: w * gross_scale for s, w in weights.items()}
        all_syms = set(prev_dispatched.keys()).union(scaled_w.keys())
        to = sum(abs(scaled_w.get(s, 0.0) - prev_dispatched.get(s, 0.0)) for s in all_syms)
        turnover += to
        trade_cost = to * fee_rate

        short_exp = sum(abs(w) for w in scaled_w.values() if w < 0)
        fund_pnl = short_exp * (BASE_FUNDING * funding_mult)

        gross_pnl = sum(scaled_w.get(s, 0.0) * safe_val(info["returns_map"], s, 0.0) for s in scaled_w)
        net_pnl = gross_pnl - trade_cost + fund_pnl

        nav *= (1.0 + net_pnl)
        returns.append(net_pnl)
        gross_pnls.append(gross_pnl)
        fees_paid.append(trade_cost)
        funding_collected.append(fund_pnl)
        prev_dispatched = scaled_w

        cur_day_rets.append(net_pnl)
        if len(cur_day_rets) == 24:
            day_ret = np.prod([1.0 + r for r in cur_day_rets]) - 1.0
            daily_returns.append(day_ret)
            cur_day_rets = []

    if not returns:
        return {}

    r = np.array(returns)
    cum = np.cumprod(1.0 + r)
    mdd = np.min((cum - np.maximum.accumulate(cum)) / np.maximum.accumulate(cum))
    vol = np.std(r) * np.sqrt(BARS_PER_YEAR)
    cagr = (nav / 10_000.0) ** (BARS_PER_YEAR / len(r)) - 1.0
    sharpe = np.mean(r) / (np.std(r) + 1e-6) * np.sqrt(BARS_PER_YEAR)
    downside_r = r[r < 0]
    sortino = np.mean(r) / (np.std(downside_r) + 1e-6) * np.sqrt(BARS_PER_YEAR) if len(downside_r) > 0 else 0.0
    calmar = cagr / abs(mdd) if abs(mdd) > 1e-4 else 0.0

    worst_1h = np.min(r)
    worst_24h = min(daily_returns) if daily_returns else worst_1h

    # Pathwise worst-case position margin headroom estimate
    # Position liquidation occurs on 2.3x isolated leg if single token drops > ~40% against position
    return {
        "nav": nav,
        "multiple": nav / 10_000.0,
        "cagr": cagr,
        "sharpe": sharpe,
        "sortino": sortino,
        "calmar": calmar,
        "mdd": mdd,
        "vol": vol,
        "turnover_ann": turnover * (BARS_PER_YEAR / len(r)),
        "worst_1h": worst_1h,
        "worst_24h": worst_24h,
        "gross_alpha_ann": sum(gross_pnls) * (BARS_PER_YEAR / len(r)),
        "fee_drag_ann": sum(fees_paid) * (BARS_PER_YEAR / len(r)),
        "funding_yield_ann": sum(funding_collected) * (BARS_PER_YEAR / len(r))
    }

# ==========================================
# 1. FRICTION STRESS TEST
# ==========================================
print("\n" + "=" * 96)
print("1. EXECUTION FRICTION STRESS TEST (FROZEN 4.6x GROSS, 1.0x FUNDING)")
print("=" * 96)
scenarios = [
    ("Base (1.5 bps)", 0.00015),
    ("Mild (3.0 bps)", 0.00030),
    ("Moderate (5.0 bps)", 0.00050),
    ("Severe (10.0 bps)", 0.00100),
    ("Extreme (15.0 bps)", 0.00150)
]
print(f"{'Scenario':<22} | {'CAGR':<10} | {'Sharpe':<8} | {'Sortino':<8} | {'MDD':<8} | {'Mult (191d)':<12} | {'Ann Fee Drag':<12}")
print("-" * 96)
for name, fee in scenarios:
    res = run_simulation(fee_rate=fee, funding_mult=1.0)
    print(f"{name:<22} | {res['cagr']*100:>+8.1f}% | {res['sharpe']:>8.2f} | {res['sortino']:>8.2f} | {res['mdd']*100:>7.1f}% | {res['multiple']:>10.2f}x | {res['fee_drag_ann']*100:>10.1f}%")

# ==========================================
# 2. FUNDING SENSITIVITY TEST
# ==========================================
print("\n" + "=" * 96)
print("2. FUNDING SENSITIVITY STRESS TEST (FROZEN 4.6x GROSS, 1.5 BPS FEE)")
print("=" * 96)
funding_scenarios = [
    ("Zero Funding (0.0x)", 0.0),
    ("Half Funding (0.5x)", 0.5),
    ("Base Observed (1.0x)", 1.0),
    ("High Funding (2.0x)", 2.0),
    ("Adverse Reversal (-1.0x)", -1.0)
]
print(f"{'Funding Multiplier':<25} | {'CAGR':<10} | {'Sharpe':<8} | {'Sortino':<8} | {'MDD':<8} | {'Multiple':<10}")
print("-" * 96)
for name, fmult in funding_scenarios:
    res = run_simulation(fee_rate=0.00015, funding_mult=fmult)
    print(f"{name:<25} | {res['cagr']*100:>+8.1f}% | {res['sharpe']:>8.2f} | {res['sortino']:>8.2f} | {res['mdd']*100:>7.1f}% | {res['multiple']:>8.2f}x")

# ==========================================
# 3. LEVERAGE & TAIL RISK STRESS TEST
# ==========================================
print("\n" + "=" * 96)
print("3. LEVERAGE SCALING & TAIL RISK (1.5 BPS FEE, 1.0x FUNDING)")
print("=" * 96)
lev_scenarios = [
    ("2.20x Gross", 2.20 / 4.60),
    ("2.75x Gross", 2.75 / 4.60),
    ("3.50x Gross", 3.50 / 4.60),
    ("4.00x Gross", 4.00 / 4.60),
    ("4.60x Gross (Base)", 1.00),
    ("5.00x Gross", 5.00 / 4.60),
    ("5.60x Gross", 5.60 / 4.60)
]
print(f"{'Leverage':<18} | {'CAGR':<10} | {'Sharpe':<7} | {'Calmar':<7} | {'MDD':<8} | {'Worst 1H':<9} | {'Worst 24H':<10}")
print("-" * 96)
for name, lscale in lev_scenarios:
    res = run_simulation(fee_rate=0.00015, funding_mult=1.0, gross_scale=lscale)
    print(f"{name:<18} | {res['cagr']*100:>+8.1f}% | {res['sharpe']:>7.2f} | {res['calmar']:>7.2f} | {res['mdd']*100:>7.1f}% | {res['worst_1h']*100:>8.2f}% | {res['worst_24h']*100:>9.2f}%")

# ==========================================
# 4. REGIME SEGMENTATION
# ==========================================
print("\n" + "=" * 96)
print("4. REGIME SEGMENTATION BREAKDOWN (FROZEN 4.6x GROSS, 1.5 BPS FEE)")
print("=" * 96)
bull_indices = [i for i in active_indices if active_bars_info[i]["is_bull"]]
bear_indices = [i for i in active_indices if not active_bars_info[i]["is_bull"]]

all_vols = [active_bars_info[i]["median_vol"] for i in active_indices]
vol_median = np.median(all_vols)
high_vol_indices = [i for i in active_indices if active_bars_info[i]["median_vol"] >= vol_median]
low_vol_indices = [i for i in active_indices if active_bars_info[i]["median_vol"] < vol_median]

regimes = [
    ("BTC Bull (Price > EMA200)", bull_indices),
    ("BTC Bear (Price < EMA200)", bear_indices),
    ("High Volatility Regime", high_vol_indices),
    ("Low Volatility Regime", low_vol_indices)
]
print(f"{'Regime':<28} | {'Bars':<7} | {'CAGR':<10} | {'Sharpe':<8} | {'Sortino':<8} | {'MDD':<8}")
print("-" * 96)
for name, idxs in regimes:
    res = run_simulation(fee_rate=0.00015, funding_mult=1.0, subset_indices=idxs)
    print(f"{name:<28} | {len(idxs):<7} | {res['cagr']*100:>+8.1f}% | {res['sharpe']:>8.2f} | {res['sortino']:>8.2f} | {res['mdd']*100:>7.1f}%")

# ==========================================
# 5. CHRONOLOGICAL HOLDOUT TEST (70% IS / 30% PURE OOS)
# ==========================================
print("\n" + "=" * 96)
print("5. PURE CHRONOLOGICAL HOLDOUT (70% IN-SAMPLE / 30% UNTOUCHED OOS)")
print("=" * 96)
split_idx = int(n_active * 0.70)
is_indices = active_indices[:split_idx]
oos_indices = active_indices[split_idx:]

res_is = run_simulation(fee_rate=0.00015, funding_mult=1.0, subset_indices=is_indices)
res_oos = run_simulation(fee_rate=0.00015, funding_mult=1.0, subset_indices=oos_indices)

print(f"{'Partition':<24} | {'Bars (Days)':<14} | {'CAGR':<10} | {'Sharpe':<8} | {'Sortino':<8} | {'MDD':<8} | {'Multiple':<10}")
print("-" * 96)
print(f"{'In-Sample (First 70%)':<24} | {len(is_indices):<5} ({len(is_indices)/24:.1f}d) | {res_is['cagr']*100:>+8.1f}% | {res_is['sharpe']:>8.2f} | {res_is['sortino']:>8.2f} | {res_is['mdd']*100:>7.1f}% | {res_is['multiple']:>8.2f}x")
print(f"{'Untouched OOS (Last 30%)':<24} | {len(oos_indices):<5} ({len(oos_indices)/24:.1f}d) | {res_oos['cagr']*100:>+8.1f}% | {res_oos['sharpe']:>8.2f} | {res_oos['sortino']:>8.2f} | {res_oos['mdd']*100:>7.1f}% | {res_oos['multiple']:>8.2f}x")
print("=" * 96)
