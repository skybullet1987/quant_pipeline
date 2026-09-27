import numpy as np
import polars as pl
from pathlib import Path

print("=" * 96)
print("   AUDIT: CARRY LEG DECOMPOSITION & CORRELATION WITH A0 ACROSS REGIMES")
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
REBAL_CLOCK = 8
K_ASSETS = 6

# Forward returns
df = df.sort(["symbol", "group_id"]).with_columns([
    (pl.col("close").shift(-1).over("symbol") / pl.col("close") - 1.0).fill_null(0.0).alias("next_ret_1h")
])

# Align BTC for A0 Alpha
btc = df.filter(pl.col("symbol") == "BTC").select([
    "group_id", pl.col("ret_4h").alias("btc_ret_4h"), pl.col("ret_12h").alias("btc_ret_12h"), pl.col("ret_72h").alias("btc_ret_72h")
]).unique(subset=["group_id"])
df = df.join(btc, on="group_id", how="left")

# A0 Alpha Signal
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

valid_counts = df.filter(pl.col("dollar_volume_1h") > 25_000).group_by("group_id").len()
active_grps = sorted(valid_counts.filter(pl.col("len") >= 35)["group_id"].to_list())

def safe_val(d, k, default=0.0):
    v = d.get(k)
    if v is None: return default
    try:
        f = float(v)
        return default if np.isnan(f) else f
    except:
        return default

carry_returns = []
carry_long_pnls = []
carry_short_pnls = []
carry_funds = []
carry_fees = []
a0_returns = []

prev_w_carry = {}
prev_w_a0 = {}
active_longs_a0 = set()
active_shorts_a0 = set()

for idx, grp in enumerate(active_grps[:-1]):
    cur_panel = df.filter(pl.col("group_id") == grp)
    valid_panel = cur_panel.filter(
        (pl.col("dollar_volume_1h") > 25_000) &
        pl.col("funding_rate").is_not_null() &
        pl.col("vol_yang_zhang").is_not_null() &
        pl.col("a0_smoothed").is_not_null()
    )
    if valid_panel.height < 35:
        continue

    returns_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["next_ret_1h"].to_list()))
    funding_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["funding_rate"].to_list()))
    vols_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["vol_yang_zhang"].to_list()))

    # --- 1. SIMULATE CARRY ENGINE (1.5x Gross) ---
    is_carry_rebal = (idx % REBAL_CLOCK == 0)
    if is_carry_rebal:
        sorted_funding = valid_panel.sort("funding_rate", descending=True)
        c_shorts = sorted_funding.head(K_ASSETS)["symbol"].to_list()
        c_longs = sorted_funding.tail(K_ASSETS)["symbol"].to_list()
        w_c = {}
        for s in c_longs: w_c[s] = 0.75 / len(c_longs)
        for s in c_shorts: w_c[s] = -0.75 / len(c_shorts)
    else:
        w_c = prev_w_carry

    all_c_syms = set(prev_w_carry.keys()).union(w_c.keys())
    to_c = sum(abs(w_c.get(s, 0.0) - prev_w_carry.get(s, 0.0)) for s in all_c_syms)
    fee_c = to_c * FEE_RATE

    pnl_l = sum(w_c.get(s, 0.0) * safe_val(returns_map, s, 0.0) for s in w_c if w_c.get(s, 0.0) > 0)
    pnl_s = sum(w_c.get(s, 0.0) * safe_val(returns_map, s, 0.0) for s in w_c if w_c.get(s, 0.0) < 0)
    fund_c = sum(-w_c.get(s, 0.0) * safe_val(funding_map, s, 0.0) for s in w_c)
    net_c = pnl_l + pnl_s + fund_c - fee_c

    carry_returns.append(net_c)
    carry_long_pnls.append(pnl_l)
    carry_short_pnls.append(pnl_s)
    carry_funds.append(fund_c)
    carry_fees.append(fee_c)
    prev_w_carry = w_c

    # --- 2. SIMULATE A0 ALPHA ENGINE (2.2x Gross Baseline) ---
    is_a0_rebal = (idx % 4 == 0)
    sorted_a0 = valid_panel.sort("a0_smoothed", descending=True)
    all_ranked = sorted_a0["symbol"].to_list()
    rank_map = {s: i for i, s in enumerate(all_ranked)}

    if is_a0_rebal:
        for s in all_ranked[:12]: active_longs_a0.add(s)
        for s in all_ranked[-12:]: active_shorts_a0.add(s)
        active_longs_a0 = {s for s in active_longs_a0 if rank_map.get(s, 999) < 28}
        active_shorts_a0 = {s for s in active_shorts_a0 if rank_map.get(s, -1) >= (len(all_ranked) - 28)}
        active_longs_a0 -= active_shorts_a0
        active_syms = active_longs_a0.union(active_shorts_a0)

        if len(active_syms) < 16:
            raw_w_a0 = prev_w_a0
        else:
            inv_v = {s: 1.0 / max(0.015, safe_val(vols_map, s, 0.025)) for s in active_syms}
            raw_w_a0 = {s: inv_v[s] if s in active_longs_a0 else -inv_v[s] for s in active_syms}
            l_sum = sum(w for w in raw_w_a0.values() if w > 0)
            s_sum = sum(abs(w) for w in raw_w_a0.values() if w < 0)
            target_leg = 1.10
            for s in raw_w_a0:
                if raw_w_a0[s] > 0 and l_sum > 0: raw_w_a0[s] = (raw_w_a0[s] / l_sum) * target_leg
                elif raw_w_a0[s] < 0 and s_sum > 0: raw_w_a0[s] = (raw_w_a0[s] / s_sum) * target_leg
    else:
        raw_w_a0 = prev_w_a0

    all_a0_syms = set(prev_w_a0.keys()).union(raw_w_a0.keys())
    to_a0 = sum(abs(raw_w_a0.get(s, 0.0) - prev_w_a0.get(s, 0.0)) for s in all_a0_syms)
    fee_a0 = to_a0 * FEE_RATE
    pnl_a0 = sum(raw_w_a0.get(s, 0.0) * safe_val(returns_map, s, 0.0) for s in raw_w_a0) - fee_a0
    a0_returns.append(pnl_a0)
    prev_w_a0 = raw_w_a0

# 1. Overall Correlation
corr_bar = np.corrcoef(carry_returns, a0_returns)[0, 1]

# Daily aggregation for macro correlation
n_days = len(carry_returns) // 24
daily_c = [np.prod([1.0 + r for r in carry_returns[i*24:(i+1)*24]]) - 1.0 for i in range(n_days)]
daily_a0 = [np.prod([1.0 + r for r in a0_returns[i*24:(i+1)*24]]) - 1.0 for i in range(n_days)]
corr_daily = np.corrcoef(daily_c, daily_a0)[0, 1]

print("\n" + "=" * 96)
print("1. CROSS-STRATEGY CORRELATION (CARRY vs A0 ALPHA)")
print("=" * 96)
print(f"Hourly Return Correlation : {corr_bar:>+.4f}")
print(f"Daily Return Correlation  : {corr_daily:>+.4f}")

# 2. Leg Decomposition of Carry
ann_mult = BARS_PER_YEAR / len(carry_returns)
print("\n" + "=" * 96)
print("2. CARRY ENGINE LEG P&L DECOMPOSITION (ANNUALIZED BASIS)")
print("=" * 96)
print(f"Long Leg Price P&L       : {sum(carry_long_pnls)*ann_mult*100:>+10.1f}%")
print(f"Short Leg Price P&L      : {sum(carry_short_pnls)*ann_mult*100:>+10.1f}%")
print(f"Net Price Drift P&L      : {(sum(carry_long_pnls) + sum(carry_short_pnls))*ann_mult*100:>+10.1f}%")
print(f"Funding Yield Harvested  : {sum(carry_funds)*ann_mult*100:>+10.1f}%")
print(f"Trading Fees Paid        : {sum(carry_fees)*ann_mult*100:>10.1f}%")
print(f"Net Realized CAGR        : {((np.prod([1.0 + r for r in carry_returns]))**ann_mult - 1.0)*100:>+10.1f}%")

# 3. Block-by-Block Comparison (Regime Breakdown)
b_size = len(carry_returns) // 3
blocks = [
    ("Block 1 (Days 1 to 64)", slice(0, b_size)),
    ("Block 2 (Days 65 to 128)", slice(b_size, 2*b_size)),
    ("Block 3 (Days 129 to 193 - OOS)", slice(2*b_size, len(carry_returns)))
]

print("\n" + "=" * 96)
print("3. REGIME BREAKDOWN: CARRY vs A0 ALPHA ACROSS 64-DAY BLOCKS")
print("=" * 96)
print(f"{'Block Name':<30} | {'Carry CAGR':<12} | {'Carry Sharpe':<14} | {'A0 CAGR':<12} | {'A0 Sharpe':<12}")
print("-" * 96)

for name, s in blocks:
    r_c = np.array(carry_returns[s])
    r_a = np.array(a0_returns[s])
    ann_b = BARS_PER_YEAR / len(r_c)

    cagr_c = (np.prod(1.0 + r_c))**ann_b - 1.0
    sharpe_c = np.mean(r_c) / (np.std(r_c) + 1e-6) * np.sqrt(BARS_PER_YEAR)

    cagr_a = (np.prod(1.0 + r_a))**ann_b - 1.0
    sharpe_a = np.mean(r_a) / (np.std(r_a) + 1e-6) * np.sqrt(BARS_PER_YEAR)

    print(f"{name:<30} | {cagr_c*100:>+10.1f}% | {sharpe_c:>12.2f} | {cagr_a*100:>+10.1f}% | {sharpe_a:>10.2f}")
print("=" * 96)
