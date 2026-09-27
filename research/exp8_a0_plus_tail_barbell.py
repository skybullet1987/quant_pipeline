import numpy as np
import polars as pl
from pathlib import Path

print("=" * 96)
print("   EXPERIMENT 8: A0 PROPORTIONAL + CONDITIONED TAIL BARBELL (ZERO CARRY)")
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
K_ENTRY_A0 = 12
K_EXIT_A0 = 28

# Forward returns
df = df.sort(["symbol", "group_id"]).with_columns([
    (pl.col("close").shift(-1).over("symbol") / pl.col("close") - 1.0).fill_null(0.0).alias("next_ret_1h")
])

# Align BTC for A0
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

# Dispersion & Velocity
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

# Tail Runner Trigger
df = df.with_columns([
    (
        (pl.col("volume_zscore_72h") > 2.5) &
        ((pl.col("vol_yang_zhang") / (pl.col("vol_yang_zhang").rolling_mean(72).over("symbol") + 1e-5)) > 1.7) &
        (pl.col("ret_24h") > 0.08)
    ).alias("is_tail_trigger")
])

active_grps = sorted(df["group_id"].unique().to_list())

def safe_val(d, k, default=0.0):
    v = d.get(k)
    if v is None: return default
    try:
        f = float(v)
        return default if np.isnan(f) else f
    except:
        return default

CONFIGS = [
    ("1. Pure A0 Proportional (100% / 0% Tail)", 1.00, 0.00),
    ("2. Barbell: A0 85% + Tail 15%", 0.85, 0.15),
    ("3. Barbell: A0 80% + Tail 20%", 0.80, 0.20),
    ("4. Aggressive: A0 75% + Tail 25%", 0.75, 0.25)
]

results = []

for label, w_a0, w_tail in CONFIGS:
    nav = 10_000.0
    turnover = 0.0
    prev_w_a0 = {}
    active_longs_a0 = set()
    active_shorts_a0 = set()
    tail_positions = {}
    returns = []

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
        prices_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["close"].to_list()))

        delta_disp = float(valid_panel["delta_disp_24h"][0])

        # --- SLEEVE 1: A0 PROPORTIONAL ---
        is_a0_rebal = (idx % 4 == 0)
        pnl_a0 = 0.0
        if is_a0_rebal:
            gross_a0 = float(np.clip(1.5 + 400.0 * delta_disp, 0.0, 4.2)) * w_a0
            if gross_a0 > 0.05:
                sorted_a0 = valid_panel.sort("a0_smoothed", descending=True)
                all_ranked = sorted_a0["symbol"].to_list()
                rank_map = {s: i for i, s in enumerate(all_ranked)}

                for s in all_ranked[:K_ENTRY_A0]: active_longs_a0.add(s)
                for s in all_ranked[-K_ENTRY_A0:]: active_shorts_a0.add(s)
                active_longs_a0 = {s for s in active_longs_a0 if rank_map.get(s, 999) < K_EXIT_A0}
                active_shorts_a0 = {s for s in active_shorts_a0 if rank_map.get(s, -1) >= (len(all_ranked) - K_EXIT_A0)}
                active_longs_a0 -= active_shorts_a0
                active_syms = active_longs_a0.union(active_shorts_a0)

                if len(active_syms) >= 16:
                    inv_v = {s: 1.0 / max(0.015, safe_val(vols_map, s, 0.025)) for s in active_syms}
                    raw_w = {s: inv_v[s] if s in active_longs_a0 else -inv_v[s] for s in active_syms}
                    l_sum = sum(w for w in raw_w.values() if w > 0)
                    s_sum = sum(abs(w) for w in raw_w.values() if w < 0)
                    target_leg = gross_a0 / 2.0
                    raw_target_a0 = {}
                    for s in raw_w:
                        if raw_w[s] > 0 and l_sum > 0: raw_target_a0[s] = (raw_w[s] / l_sum) * target_leg
                        elif raw_w[s] < 0 and s_sum > 0: raw_target_a0[s] = (raw_w[s] / s_sum) * target_leg
                else:
                    raw_target_a0 = prev_w_a0
            else:
                raw_target_a0 = {}
        else:
            raw_target_a0 = prev_w_a0

        # Deadband
        dispatched_a0 = {}
        all_a0_syms = set(prev_w_a0.keys()).union(raw_target_a0.keys())
        for s in all_a0_syms:
            w_t = raw_target_a0.get(s, 0.0)
            w_prev = prev_w_a0.get(s, 0.0)
            sigma = max(0.015, safe_val(vols_map, s, 0.025))
            if abs(w_t) < 1e-4 or abs(w_prev) < 1e-4 or (w_t * w_prev < 0):
                dispatched_a0[s] = w_t
                continue
            h_star = np.clip(((4.0 / 3.0) * (FEE_RATE * (sigma ** 2.0)) / GAMMA_MVO) ** (1.0 / 3.0) * 1.5, 0.020, 0.055)
            delta = w_t - w_prev
            dispatched_a0[s] = (w_t - np.sign(delta) * h_star) if abs(delta) > h_star else w_prev

        dispatched_a0 = {s: w for s, w in dispatched_a0.items() if abs(w) > 0.002}
        to_a0 = sum(abs(dispatched_a0.get(s, 0.0) - prev_w_a0.get(s, 0.0)) for s in all_a0_syms)
        pnl_a0 = sum(dispatched_a0.get(s, 0.0) * safe_val(returns_map, s, 0.0) for s in dispatched_a0) - (to_a0 * FEE_RATE)
        pnl_a0 += sum(-dispatched_a0.get(s, 0.0) * safe_val(funding_map, s, 0.0) for s in dispatched_a0)
        prev_w_a0 = dispatched_a0
        turnover += to_a0

        # --- SLEEVE 2: CONVEX TAIL RUNNER (WITH 2.0x ATR STOP & TRAIL) ---
        pnl_tail = 0.0
        if w_tail > 0:
            closed_tail_syms = []
            for s, pos in tail_positions.items():
                cur_price = safe_val(prices_map, s, pos["entry_price"])
                pnl_pct = (cur_price / pos["entry_price"]) - 1.0
                pos["bars_held"] += 1

                if cur_price <= pos["stop_loss"] or pos["bars_held"] >= 72:
                    exit_pnl = pos["weight"] * pnl_pct - (pos["weight"] * FEE_RATE)
                    pnl_tail += exit_pnl
                    turnover += pos["weight"]
                    closed_tail_syms.append(s)
                else:
                    if pnl_pct > 0.12:
                        pos["stop_loss"] = max(pos["stop_loss"], pos["entry_price"] * (1.0 + pnl_pct - 0.05))
                    pnl_tail += pos["weight"] * safe_val(returns_map, s, 0.0)

            for s in closed_tail_syms:
                del tail_positions[s]

            if len(tail_positions) < 3:
                triggers = valid_panel.filter(pl.col("is_tail_trigger"))["symbol"].to_list()
                for s in triggers:
                    if s not in tail_positions and len(tail_positions) < 3:
                        px = safe_val(prices_map, s, 1.0)
                        sigma = max(0.02, safe_val(vols_map, s, 0.03))
                        stop_dist = max(0.07, 2.0 * sigma)
                        pos_w = (w_tail * 1.50) / 3.0
                        tail_positions[s] = {
                            "entry_price": px,
                            "stop_loss": px * (1.0 - stop_dist),
                            "bars_held": 0,
                            "weight": pos_w
                        }
                        turnover += pos_w
                        pnl_tail -= pos_w * FEE_RATE

        net_pnl = pnl_a0 + pnl_tail
        nav *= (1.0 + net_pnl)
        returns.append(net_pnl)

    r = np.array(returns)
    ann_mult = BARS_PER_YEAR / len(r)
    cagr = (nav / 10_000.0) ** ann_mult - 1.0
    sharpe = np.mean(r) / (np.std(r) + 1e-6) * np.sqrt(BARS_PER_YEAR)
    cum = np.cumprod(1.0 + r)
    mdd = np.min((cum - np.maximum.accumulate(cum)) / np.maximum.accumulate(cum))
    geo_g = np.mean(np.log(1.0 + r)) * BARS_PER_YEAR

    # Block Breakdown
    b_size = len(returns) // 3
    r_b1 = np.array(returns[:b_size])
    r_b2 = np.array(returns[b_size:2*b_size])
    r_b3 = np.array(returns[2*b_size:])
    mult_b3 = np.prod(1.0 + r_b3)
    cagr_b3 = mult_b3 ** (BARS_PER_YEAR / len(r_b3)) - 1.0

    results.append({
        "name": label,
        "multiple": nav / 10_000.0,
        "cagr": cagr,
        "sharpe": sharpe,
        "mdd": mdd,
        "geo_g": geo_g,
        "b3_cagr": cagr_b3,
        "b3_mult": mult_b3
    })

print("\n" + "=" * 96)
print("             EXPERIMENT 8 RESULTS: A0 + TAIL BARBELL BENCHMARK")
print("=" * 96)
print(f"{'Strategy Architecture':<38} | {'CAGR':<10} | {'Sharpe':<8} | {'MDD':<8} | {'Mult':<8} | {'Geo g':<8} | {'OOS Mult':<8}")
print("-" * 96)
for res in results:
    print(f"{res['name']:<38} | {res['cagr']*100:>+8.1f}% | {res['sharpe']:>8.2f} | {res['mdd']*100:>7.1f}% | {res['multiple']:>6.2f}x | {res['geo_g']:>6.2f} | {res['b3_mult']:>6.2f}x")
print("=" * 96)
