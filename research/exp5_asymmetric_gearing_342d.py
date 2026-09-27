import sys
import time
from pathlib import Path
import numpy as np
import polars as pl
from sklearn.covariance import LedoitWolf

sys.path.insert(0, str(Path.home() / "quant_pipeline"))
from src.signals.multiscale_alpha_engine import ProductionMultiScaleEngine, compute_hrp_from_cov

print("=" * 84)
print("   1-YEAR 10x FEASIBILITY: ASYMMETRIC REGIME GEARING (342 DAYS)")
print("=" * 84)

lake_path = Path.home() / "quant_pipeline" / "data" / "lake" / "features" / "pit_panel_4h.parquet"
df = pl.read_parquet(lake_path)

if "group_id" not in df.columns:
    unique_ts = df.select("timestamp_ms").unique().sort("timestamp_ms").with_columns(
        pl.int_range(0, pl.len()).alias("group_id")
    )
    df = df.join(unique_ts, on="timestamp_ms", how="left")

engine = ProductionMultiScaleEngine()
_, _ = engine.compute_live_targets(lake_file=lake_path)

all_groups = sorted(df.select("group_id").unique().to_series().to_list())
eval_groups = [g for g in all_groups if g >= 168]

fee_rate = 0.00015
gamma_mvo = 0.05
BARS_PER_YEAR = 6 * 365

# BTC Macro Regime Filter (50-bar EMA of BTC close)
btc_df = df.filter(pl.col("symbol") == "BTC").sort("group_id").select(["group_id", "close"])
btc_close = btc_df["close"].to_numpy()
btc_ema50 = pl.Series(btc_close).ewm_mean(span=50).to_numpy()
btc_regime_map = {grp: (btc_close[i] > btc_ema50[i]) for i, grp in enumerate(btc_df["group_id"].to_list())}

def zscore(arr):
    s = np.std(arr)
    return (arr - np.mean(arr)) / (s if s > 1e-6 else 1.0)

# Compare 3 Gearing Modes:
# 1. Market-Neutral Base (0.0x Net Beta, Vol-Target 22%)
# 2. Moderate Gearing (Up to 1.75x Net Long in Bull, 0.0x in Bear)
# 3. Aggressive 10x Gearing (Up to 3.0x Net Long in Bull, 0.0x in Bear, Vol-Target 55%)

navs = [10_000.0] * 3
turnovers = [0.0] * 3
prev_weights = [{}, {}, {}]
returns_hist = [[], [], []]

t0 = time.time()
for idx in range(len(eval_groups) - 1):
    grp = eval_groups[idx]
    next_grp = eval_groups[idx + 1]

    cur_panel = df.filter(pl.col("group_id") == grp)
    next_panel = df.filter(pl.col("group_id") == next_grp)
    returns_map = dict(zip(next_panel["symbol"].to_list(), next_panel["ret_4h"].to_list()))
    vols_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["vol_yang_zhang"].to_list()))
    cur_rows = {r["symbol"]: r for r in cur_panel.iter_rows(named=True)}
    symbols = list(cur_rows.keys())

    X_live = cur_panel.select(engine.m12.feature_names_).to_pandas()
    z12 = zscore(engine.m12.predict(X_live))
    z48 = zscore(engine.m48.predict(X_live))
    z168 = zscore(engine.m168.predict(X_live))

    # Corrected Alpha Ensemble
    alpha_vec = (-0.30 * z12) + (0.45 * z48) + (0.25 * z168)
    alpha_dict = {s: v for s, v in zip(symbols, alpha_vec)}

    hist = df.filter((pl.col("group_id") <= grp) & (pl.col("group_id") > grp - 168))
    piv = hist.pivot(values="ret_4h", index="group_id", on="symbol").sort("group_id")
    v_cols = [c for c in symbols if c in piv.columns and piv[c].null_count() == 0]
    if len(v_cols) < 20:
        continue

    shrunk_cov = LedoitWolf().fit(piv.select(v_cols).to_numpy()).covariance_
    a_sub = np.array([alpha_dict[s] for s in v_cols])

    # Base HRP unit weights
    w_unit = compute_hrp_from_cov(shrunk_cov, a_sub, target_leverage=1.0, top_k=10)
    port_var = float(w_unit.T @ shrunk_cov @ w_unit)
    port_vol = np.sqrt(max(port_var, 1e-8))

    is_bull = btc_regime_map.get(grp, False)

    # --- Mode 0: Market Neutral (22% Target Vol) ---
    lev_0 = float(np.clip((0.22 / np.sqrt(BARS_PER_YEAR)) / port_vol, 0.60, 2.50))
    w_0 = w_unit * lev_0

    # --- Mode 1: Moderate Asymmetric Gearing ---
    lev_1 = float(np.clip((0.35 / np.sqrt(BARS_PER_YEAR)) / port_vol, 0.60, 3.00))
    w_1 = w_unit.copy() * lev_1
    if is_bull:
        w_1[w_1 > 0] *= 1.75  # Boost longs by 1.75x
        w_1[w_1 < 0] *= 0.50  # Damped shorts

    # --- Mode 2: Aggressive 1-Year 10x Gearing ---
    lev_2 = float(np.clip((0.55 / np.sqrt(BARS_PER_YEAR)) / port_vol, 0.80, 4.00))
    w_2 = w_unit.copy() * lev_2
    if is_bull:
        w_2[w_2 > 0] *= 2.50  # 2.5x geared longs in bull expansion
        w_2[w_2 < 0] *= 0.25  # Prune shorts to tail hedges
    else:
        w_2[w_2 > 0] *= 0.70  # Defensive long reduction in bear/chop

    modes = [w_0, w_1, w_2]

    for v in range(3):
        raw_target = {v_cols[i]: float(modes[v][i]) for i in range(len(v_cols)) if abs(modes[v][i]) > 0.005}

        # Sign-Preserving Leland Deadband
        dispatched = {}
        all_syms = set(prev_weights[v].keys()).union(raw_target.keys())
        for s in all_syms:
            w_t = raw_target.get(s, 0.0)
            w_prev = prev_weights[v].get(s, 0.0)
            sigma = max(0.015, vols_map.get(s, 0.025))

            if abs(w_t) < 1e-4 or abs(w_prev) < 1e-4 or (w_t * w_prev < 0):
                dispatched[s] = w_t
                continue

            h_star = np.clip(((4.0 / 3.0) * (fee_rate * (sigma ** 2.0)) / gamma_mvo) ** (1.0 / 3.0), 0.010, 0.040)
            delta = w_t - w_prev
            if abs(delta) > h_star:
                dispatched[s] = w_t - np.sign(delta) * h_star
            else:
                dispatched[s] = w_prev
        dispatched = {s: w for s, w in dispatched.items() if abs(w) > 0.005}

        to = sum(abs(dispatched.get(s, 0.0) - prev_weights[v].get(s, 0.0)) for s in all_syms)
        turnovers[v] += to
        cost = to * fee_rate
        pnl = sum(dispatched.get(s, 0.0) * returns_map.get(s, 0.0) for s in dispatched) - cost
        navs[v] *= (1.0 + pnl)
        returns_hist[v].append(pnl)
        prev_weights[v] = dispatched

    if (idx + 1) % 500 == 0 or (idx + 1) == len(eval_groups) - 1:
        print(f"  • Processed {idx + 1}/{len(eval_groups) - 1} bars ({time.time() - t0:.1f}s elapsed)...")

# Summary Results
print("\n" + "=" * 84)
print("          342-DAY COMPOUNDING & 1-YEAR 10x TRAJECTORY")
print("=" * 84)
headers = ["Metric", "Market-Neutral (22%)", "Moderate Gearing", "Aggressive Gearing (55%)"]
print(f"{headers[0]:<25} | {headers[1]:<20} | {headers[2]:<18} | {headers[3]:<18}")
print("-" * 84)

def calc_stats(nav, rets, to):
    r = np.array(rets)
    total_ret = (nav / 10_000.0) - 1.0
    cagr = (nav / 10_000.0) ** (BARS_PER_YEAR / len(r)) - 1.0
    sharpe = np.mean(r) / (np.std(r) + 1e-6) * np.sqrt(BARS_PER_YEAR)
    vol = np.std(r) * np.sqrt(BARS_PER_YEAR)
    cum = np.cumprod(1.0 + r)
    mdd = np.min((cum - np.maximum.accumulate(cum)) / np.maximum.accumulate(cum))
    mult = nav / 10_000.0
    return mult, total_ret, cagr, sharpe, vol, mdd, to

res = [calc_stats(navs[i], returns_hist[i], turnovers[i]) for i in range(3)]

print(f"{'Account Multiple (342d)':<25} | {res[0][0]:>19.2f}x | {res[1][0]:>17.2f}x | {res[2][0]:>17.2f}x")
print(f"{'Cumulative Net Return':<25} | {res[0][1]*100:>+19.2f}% | {res[1][1]*100:>+17.2f}% | {res[2][1]*100:>+17.2f}%")
print(f"{'Annualized CAGR':<25} | {res[0][2]*100:>+19.2f}% | {res[1][2]*100:>+17.2f}% | {res[2][2]*100:>+17.2f}%")
print(f"{'Net Sharpe Ratio':<25} | {res[0][3]:>20.2f} | {res[1][3]:>18.2f} | {res[2][3]:>18.2f}")
print(f"{'Realized Volatility':<25} | {res[0][4]*100:>19.2f}% | {res[1][4]*100:>17.2f}% | {res[2][4]*100:>17.2f}%")
print(f"{'Max Drawdown':<25} | {res[0][5]*100:>19.2f}% | {res[1][5]*100:>17.2f}% | {res[2][5]*100:>17.2f}%")
print(f"{'Turnover / 4H Bar':<25} | {res[0][6]/len(returns_hist[0]):>19.2f}x | {res[1][6]/len(returns_hist[1]):>17.2f}x | {res[2][6]/len(returns_hist[2]):>17.2f}x")
print("=" * 84)
