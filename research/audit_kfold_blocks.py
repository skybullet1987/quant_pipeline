import numpy as np
import polars as pl
from pathlib import Path

LAKE_PATH = Path.home() / "quant_pipeline" / "data" / "lake" / "features" / "pit_panel_1h_full.parquet"
df = pl.read_parquet(LAKE_PATH)

if "group_id" not in df.columns:
    unique_ts = df.select("timestamp_ms").unique().sort("timestamp_ms").with_columns(
        pl.int_range(0, pl.len()).alias("group_id")
    )
    df = df.join(unique_ts, on="timestamp_ms", how="left")

BARS_PER_YEAR = 24 * 365
FEE_RATE = 0.00015
GROSS_LEVERAGE = 4.60
BASE_FUNDING = 0.00005
GAMMA_MVO = 0.05
K_ENTRY = 12
K_EXIT = 28

df = df.sort(["symbol", "group_id"]).with_columns([
    (pl.col("close").shift(-1).over("symbol") / pl.col("close") - 1.0).fill_null(0.0).alias("next_ret_1h")
])

btc = df.filter(pl.col("symbol") == "BTC").select([
    "group_id", pl.col("ret_4h").alias("btc_ret_4h"), pl.col("ret_12h").alias("btc_ret_12h"), pl.col("ret_72h").alias("btc_ret_72h")
]).unique(subset=["group_id"])
df = df.join(btc, on="group_id", how="left")

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

valid_counts = df.filter(pl.col("dollar_volume_1h") > 25_000).group_by("group_id").len()
active_grps = sorted(valid_counts.filter(pl.col("len") >= 35)["group_id"].to_list())

# Split into 3 equal consecutive blocks (~64 days each)
n_total = len(active_grps)
b_size = n_total // 3
blocks = [
    ("Block 1 (Days 1 to 64)", active_grps[:b_size]),
    ("Block 2 (Days 65 to 128)", active_grps[b_size:2*b_size]),
    ("Block 3 (Days 129 to 193 - OOS)", active_grps[2*b_size:])
]

def safe_val(d, k, default=0.0):
    v = d.get(k)
    if v is None: return default
    try:
        f = float(v)
        return default if np.isnan(f) else f
    except:
        return default

def eval_block(grps):
    nav = 10_000.0
    turnover = 0.0
    prev_w = {}
    active_longs = set()
    active_shorts = set()
    returns = []
    gross_pnls = []
    fee_pnls = []

    for idx, grp in enumerate(grps[:-1]):
        cur_panel = df.filter(pl.col("group_id") == grp)
        valid_panel = cur_panel.filter(
            (pl.col("dollar_volume_1h") > 25_000) &
            pl.col("vol_yang_zhang").is_not_null() &
            pl.col("smoothed_alpha").is_not_null()
        )
        if valid_panel.height < 35:
            continue

        returns_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["next_ret_1h"].to_list()))
        vols_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["vol_yang_zhang"].to_list()))

        sorted_alpha = valid_panel.sort("smoothed_alpha", descending=True)
        all_ranked = sorted_alpha["symbol"].to_list()
        rank_map = {s: i for i, s in enumerate(all_ranked)}

        if (idx % 4 == 0):
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

                target_leg = GROSS_LEVERAGE / 2.0
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

            h_star = np.clip(((4.0 / 3.0) * (FEE_RATE * (sigma ** 2.0)) / GAMMA_MVO) ** (1.0 / 3.0) * 1.5, 0.020, 0.055)
            delta = w_t - w_prev_s
            if abs(delta) > h_star:
                dispatched[s] = w_t - np.sign(delta) * h_star
            else:
                dispatched[s] = w_prev_s

        dispatched = {s: w for s, w in dispatched.items() if abs(w) > 0.002}

        to = sum(abs(dispatched.get(s, 0.0) - prev_w.get(s, 0.0)) for s in all_syms)
        turnover += to
        cost = to * FEE_RATE

        short_exp = sum(abs(w) for w in dispatched.values() if w < 0)
        fund_pnl = short_exp * BASE_FUNDING
        gross_pnl = sum(dispatched.get(s, 0.0) * safe_val(returns_map, s, 0.0) for s in dispatched)
        net_pnl = gross_pnl - cost + fund_pnl

        nav *= (1.0 + net_pnl)
        returns.append(net_pnl)
        gross_pnls.append(gross_pnl)
        fee_pnls.append(cost)
        prev_w = dispatched

    r = np.array(returns)
    cum = np.cumprod(1.0 + r)
    mdd = np.min((cum - np.maximum.accumulate(cum)) / np.maximum.accumulate(cum))
    vol = np.std(r) * np.sqrt(BARS_PER_YEAR)
    cagr = (nav / 10_000.0) ** (BARS_PER_YEAR / len(r)) - 1.0
    sharpe = np.mean(r) / (np.std(r) + 1e-6) * np.sqrt(BARS_PER_YEAR)

    return {
        "multiple": nav / 10_000.0,
        "cagr": cagr,
        "sharpe": sharpe,
        "mdd": mdd,
        "vol": vol,
        "gross_alpha": sum(gross_pnls),
        "fees_paid": sum(fee_pnls),
        "turnover_ann": turnover * (BARS_PER_YEAR / len(r))
    }

print("=" * 96)
print("       BLOCKED 3-STAGE CHRONOLOGICAL AUDIT (64 DAYS PER BLOCK)")
print("=" * 96)
print(f"{'Block Name':<30} | {'Mult':<8} | {'CAGR':<10} | {'Sharpe':<8} | {'MDD':<8} | {'Gross PnL':<10} | {'Fees Paid':<10}")
print("-" * 96)

for name, grps in blocks:
    res = eval_block(grps)
    print(f"{name:<30} | {res['multiple']:>6.2f}x | {res['cagr']*100:>+8.1f}% | {res['sharpe']:>8.2f} | {res['mdd']*100:>7.1f}% | {res['gross_alpha']*100:>+8.1f}% | {res['fees_paid']*100:>8.1f}%")
print("=" * 96)
