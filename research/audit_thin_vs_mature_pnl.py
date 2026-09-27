import numpy as np
import polars as pl
from pathlib import Path

LAKE_PATH = Path.home() / "quant_pipeline" / "data" / "lake" / "features" / "pit_panel_1h_with_funding.parquet"
df = pl.read_parquet(LAKE_PATH)

if "group_id" not in df.columns:
    unique_ts = df.select("timestamp_ms").unique().sort("timestamp_ms").with_columns(
        pl.int_range(0, pl.len()).alias("group_id")
    )
    df = df.join(unique_ts, on="timestamp_ms", how="left")

# Identify group counts
counts = (
    df.filter((pl.col("dollar_volume_1h") > 25_000) & pl.col("vol_yang_zhang").is_not_null())
    .group_by("group_id")
    .len()
)
df = df.join(counts.select(["group_id", pl.col("len").alias("active_n")]), on="group_id", how="left")

BARS_PER_YEAR = 24 * 365
FEE_RATE = 0.00015
GAMMA_MVO = 0.05

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

prev_w = {}
active_longs = set()
active_shorts = set()

thin_returns = []
mature_returns = []

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
    k_entry = max(3, min(12, int(n_avail * 0.15)))
    k_exit = max(6, min(28, int(n_avail * 0.35)))

    is_rebal = (idx % 6 == 0)
    if is_rebal:
        if delta_disp <= -0.001:
            gross_target = 0.0
        else:
            gross_target = float(np.clip(1.20 + 450.0 * delta_disp, 0.0, 4.50))

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

    dispatched = {}
    all_syms = set(prev_w.keys()).union(raw_target.keys())
    for s in all_syms:
        w_t = raw_target.get(s, 0.0)
        w_prev = prev_w.get(s, 0.0)
        sigma = max(0.015, safe_val(vols_map, s, 0.025))

        if abs(w_t) < 1e-4 or abs(w_prev) < 1e-4 or (w_t * w_prev < 0):
            dispatched[s] = w_t
            continue

        h_star = np.clip(((4.0 / 3.0) * (FEE_RATE * (sigma ** 2.0)) / GAMMA_MVO) ** (1.0 / 3.0) * 2.0, 0.020, 0.065)
        delta = w_t - w_prev
        dispatched[s] = (w_t - np.sign(delta) * h_star) if abs(delta) > h_star else w_prev

    dispatched = {s: w for s, w in dispatched.items() if abs(w) > 0.002}
    to = sum(abs(dispatched.get(s, 0.0) - prev_w.get(s, 0.0)) for s in all_syms)
    cost = to * FEE_RATE

    fund_pnl = sum(-dispatched.get(s, 0.0) * safe_val(funding_map, s, 0.0) for s in dispatched)
    p_pnl = sum(dispatched.get(s, 0.0) * safe_val(returns_map, s, 0.0) for s in dispatched)
    net_pnl = p_pnl + fund_pnl - cost

    if n_avail < 35:
        thin_returns.append(net_pnl)
    else:
        mature_returns.append(net_pnl)

    prev_w = dispatched

r_thin = np.array(thin_returns)
r_mat = np.array(mature_returns)

mult_thin = np.prod(1.0 + r_thin)
mult_mat = np.prod(1.0 + r_mat)

sharpe_thin = np.mean(r_thin) / (np.std(r_thin) + 1e-6) * np.sqrt(BARS_PER_YEAR)
sharpe_mat = np.mean(r_mat) / (np.std(r_mat) + 1e-6) * np.sqrt(BARS_PER_YEAR)

cum_thin = np.cumprod(1.0 + r_thin)
cum_mat = np.cumprod(1.0 + r_mat)
mdd_thin = np.min((cum_thin - np.maximum.accumulate(cum_thin)) / np.maximum.accumulate(cum_thin))
mdd_mat = np.min((cum_mat - np.maximum.accumulate(cum_mat)) / np.maximum.accumulate(cum_mat))

print("=" * 86)
print("             EMPIRICAL P&L DECOMPOSITION: THIN VS MATURE UNIVERSE")
print("=" * 86)
print(f"{'Regime':<24} | {'Bars':<8} | {'Days':<6} | {'Multiple':<10} | {'Sharpe':<8} | {'Max DD':<8}")
print("-" * 86)
print(f"{'Thin (12 <= N < 35)':<24} | {len(r_thin):<8} | {len(r_thin)/24:>5.1f}d | {mult_thin:>9.2f}x | {sharpe_thin:>8.2f} | {mdd_thin*100:>7.1f}%")
print(f"{'Mature (N >= 35)':<24} | {len(r_mat):<8} | {len(r_mat)/24:>5.1f}d | {mult_mat:>9.2f}x | {sharpe_mat:>8.2f} | {mdd_mat*100:>7.1f}%")
print("=" * 86)
