import numpy as np
import polars as pl
from pathlib import Path

print("=" * 96)
print("   EXPERIMENT 7: THREE-SLEEVE PORTFOLIO ENGINE & GEOMETRIC CONTRIBUTION")
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
K_CARRY = 6

# Forward returns
df = df.sort(["symbol", "group_id"]).with_columns([
    (pl.col("close").shift(-1).over("symbol") / pl.col("close") - 1.0).fill_null(0.0).alias("next_ret_1h"),
    (pl.col("close").shift(-4).over("symbol") / pl.col("close") - 1.0).fill_null(0.0).alias("fwd_ret_4h")
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

# Convex Tail Triggers
df = df.with_columns([
    (
        (pl.col("volume_zscore_72h") > 2.2) &
        ((pl.col("vol_yang_zhang") / (pl.col("vol_yang_zhang").rolling_mean(72).over("symbol") + 1e-5)) > 1.6) &
        (pl.col("ret_24h") > 0.08)
    ).alias("is_convex_trigger")
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

# Portfolio allocation weights: (w_a0, w_carry, w_tail)
CONFIGS = [
    ("1. A0 Proportional Only (100% / 0% / 0%)", 1.00, 0.00, 0.00),
    ("2. Carry Ballast Only (0% / 100% / 0%)", 0.00, 1.00, 0.00),
    ("3. Barbell: A0 + Carry (70% / 30% / 0%)", 0.70, 0.30, 0.00),
    ("4. Full Tri-Sleeve (60% / 25% / 15%)", 0.60, 0.25, 0.15),
    ("5. High-Octane Tri-Sleeve (50% / 30% / 20%)", 0.50, 0.30, 0.20)
]

all_returns = []
all_navs = []
all_drawdowns = []

for label, w_a0, w_carry, w_tail in CONFIGS:
    nav = 10_000.0
    turnover = 0.0
    prev_w_a0 = {}
    prev_w_carry = {}
    active_longs_a0 = set()
    active_shorts_a0 = set()
    tail_positions = {}  # symbol -> {"entry_price", "stop_loss", "bars_held", "weight"}

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

        # --- SLEEVE 1: DYNAMIC GATED A0 ---
        is_a0_rebal = (idx % 4 == 0)
        pnl_a0 = 0.0
        if w_a0 > 0:
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

        # --- SLEEVE 2: CARRY BALLAST ---
        pnl_carry = 0.0
        if w_carry > 0:
            is_carry_rebal = (idx % 8 == 0)
            if is_carry_rebal:
                sorted_f = valid_panel.sort("funding_rate", descending=True)
                c_shorts = sorted_f.head(K_CARRY)["symbol"].to_list()
                c_longs = sorted_f.tail(K_CARRY)["symbol"].to_list()
                target_carry = {}
                leg_alloc = (1.50 * w_carry) / 2.0
                for s in c_longs: target_carry[s] = leg_alloc / len(c_longs)
                for s in c_shorts: target_carry[s] = -leg_alloc / len(c_shorts)
            else:
                target_carry = prev_w_carry

            all_c_syms = set(prev_w_carry.keys()).union(target_carry.keys())
            to_c = sum(abs(target_carry.get(s, 0.0) - prev_w_carry.get(s, 0.0)) for s in all_c_syms)
            pnl_carry = sum(target_carry.get(s, 0.0) * safe_val(returns_map, s, 0.0) for s in target_carry) - (to_c * FEE_RATE)
            pnl_carry += sum(-target_carry.get(s, 0.0) * safe_val(funding_map, s, 0.0) for s in target_carry)
            prev_w_carry = target_carry
            turnover += to_c

        # --- SLEEVE 3: CONVEX TAIL RUNNER ---
        pnl_tail = 0.0
        if w_tail > 0:
            # Check existing tail positions
            closed_tail_syms = []
            for s, pos in tail_positions.items():
                cur_price = safe_val(prices_map, s, pos["entry_price"])
                pnl_pct = (cur_price / pos["entry_price"]) - 1.0
                pos["bars_held"] += 1

                # Stop-Loss: 2 * ATR (~8%) or Time-Stop (48H)
                if cur_price <= pos["stop_loss"] or pos["bars_held"] >= 48:
                    exit_pnl = pos["weight"] * pnl_pct - (pos["weight"] * FEE_RATE)
                    pnl_tail += exit_pnl
                    turnover += pos["weight"]
                    closed_tail_syms.append(s)
                else:
                    # Ratchet trailing stop
                    if pnl_pct > 0.10:
                        pos["stop_loss"] = max(pos["stop_loss"], pos["entry_price"] * (1.0 + pnl_pct - 0.06))
                    pnl_tail += pos["weight"] * safe_val(returns_map, s, 0.0)

            for s in closed_tail_syms:
                del tail_positions[s]

            # Trigger new candidates if capacity available (max 4 concurrent tail runners)
            if len(tail_positions) < 4:
                triggers = valid_panel.filter(pl.col("is_convex_trigger"))["symbol"].to_list()
                for s in triggers:
                    if s not in tail_positions and len(tail_positions) < 4:
                        px = safe_val(prices_map, s, 1.0)
                        sigma = max(0.02, safe_val(vols_map, s, 0.03))
                        stop_dist = max(0.06, 2.0 * sigma)
                        pos_w = (w_tail * 1.50) / 4.0  # Distributed across slots
                        tail_positions[s] = {
                            "entry_price": px,
                            "stop_loss": px * (1.0 - stop_dist),
                            "bars_held": 0,
                            "weight": pos_w
                        }
                        turnover += pos_w
                        pnl_tail -= pos_w * FEE_RATE

        # Combined Net Portfolio Return
        net_bar_pnl = pnl_a0 + pnl_carry + pnl_tail
        nav *= (1.0 + net_bar_pnl)
        returns.append(net_bar_pnl)

    all_returns.append(returns)
    all_navs.append(nav)

print("\n" + "=" * 96)
print("             EXPERIMENT 7: FULL 191-DAY PORTFOLIO ALLOCATION RESULTS")
print("=" * 96)
print(f"{'Sleeve Allocation Strategy':<42} | {'CAGR':<10} | {'Sharpe':<8} | {'MDD':<8} | {'Multiple':<10} | {'Geo g':<8}")
print("-" * 96)

for i, (label, _, _, _) in enumerate(CONFIGS):
    r = np.array(all_returns[i])
    ann_mult = BARS_PER_YEAR / len(r)
    cagr = (all_navs[i] / 10_000.0) ** ann_mult - 1.0
    sharpe = np.mean(r) / (np.std(r) + 1e-6) * np.sqrt(BARS_PER_YEAR)
    cum = np.cumprod(1.0 + r)
    mdd = np.min((cum - np.maximum.accumulate(cum)) / np.maximum.accumulate(cum))
    geo_g = np.mean(np.log(1.0 + r)) * BARS_PER_YEAR
    print(f"{label:<42} | {cagr*100:>+8.1f}% | {sharpe:>8.2f} | {mdd*100:>7.1f}% | {all_navs[i]/10_000.0:>8.2f}x | {geo_g:>8.2f}")

# Block 3 (OOS) Rescue Breakdown
b_size = len(all_returns[0]) // 3
oos_slice = slice(2 * b_size, len(all_returns[0]))

print("\n" + "=" * 96)
print("             UNTOUCHED OUT-OF-SAMPLE (DAYS 129 TO 193) BREAKDOWN")
print("=" * 96)
print(f"{'Sleeve Allocation Strategy':<42} | {'OOS CAGR':<10} | {'OOS Sharpe':<10} | {'OOS MDD':<10} | {'OOS Mult':<10}")
print("-" * 96)
for i, (label, _, _, _) in enumerate(CONFIGS):
    r_oos = np.array(all_returns[i][oos_slice])
    ann_b = BARS_PER_YEAR / len(r_oos)
    cagr_oos = (np.prod(1.0 + r_oos)) ** ann_b - 1.0
    sharpe_oos = np.mean(r_oos) / (np.std(r_oos) + 1e-6) * np.sqrt(BARS_PER_YEAR)
    cum_oos = np.cumprod(1.0 + r_oos)
    mdd_oos = np.min((cum_oos - np.maximum.accumulate(cum_oos)) / np.maximum.accumulate(cum_oos))
    mult_oos = np.prod(1.0 + r_oos)
    print(f"{label:<42} | {cagr_oos*100:>+8.1f}% | {sharpe_oos:>10.2f} | {mdd_oos*100:>9.1f}% | {mult_oos:>9.2f}x")
print("=" * 96)
