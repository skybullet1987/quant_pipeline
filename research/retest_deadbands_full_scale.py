import sys
import time
from pathlib import Path
import numpy as np
import polars as pl
from sklearn.covariance import LedoitWolf

sys.path.insert(0, str(Path.home() / "quant_pipeline"))
from src.signals.multiscale_alpha_engine import ProductionMultiScaleEngine, compute_ensemble_alpha, compute_hrp_from_cov
from src.config import STRATEGY_CONFIG

print("=" * 82)
print("   UNIFIED FULL-SCALE MACRO RE-TEST: TURNOVER MECHANICS (2,052 BARS)")
print("=" * 82)

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
print(f"[+] Replaying full historical cycle across {len(eval_groups)} 4H bars ({len(eval_groups)/6:.1f} days)...")

fee_rate = 0.00015  # 1.5 bps realistic maker fee
gamma_mvo = 0.05
TARGET_ANN_VOL = 0.22
BARS_PER_YEAR = 6 * 365
TARGET_BAR_VOL = TARGET_ANN_VOL / np.sqrt(BARS_PER_YEAR)

# 1: Baseline (K=7, Raw)
# 2: Vol-Targeted (K=10, sigma*=22%)
# 3: Vol-Targeted + Leland Deadband
# 4: Vol-Targeted + Rank Hysteresis
navs = [10_000.0] * 4
turnovers = [0.0] * 4
prev_weights = [{}, {}, {}, {}]
returns_hist = [[], [], [], []]

# State for hysteresis variant (variant index 3)
active_longs, active_shorts = set(), set()
ENTRY_K = 10
EXIT_K = 14

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

    # Shared Alpha & Covariance State
    X_live = cur_panel.select(engine.m12.feature_names_).to_pandas()
    p12 = engine.m12.predict(X_live)
    p48 = engine.m48.predict(X_live)
    p168 = engine.m168.predict(X_live)
    alpha_vec = compute_ensemble_alpha(p12, p48, p168, {"12h": [], "48h": [], "168h": []}, use_dynamic_ir=True)
    alpha_dict = {s: v for s, v in zip(symbols, alpha_vec)}

    hist = df.filter((pl.col("group_id") <= grp) & (pl.col("group_id") > grp - 168))
    piv = hist.pivot(values="ret_4h", index="group_id", on="symbol").sort("group_id")
    v_cols = [c for c in symbols if c in piv.columns and piv[c].null_count() == 0]
    if len(v_cols) < 20:
        continue

    shrunk_cov = LedoitWolf().fit(piv.select(v_cols).to_numpy()).covariance_
    a_sub = np.array([alpha_dict[s] for s in v_cols])
    m_yz = float(cur_panel.select(pl.mean("vol_yang_zhang")).to_series()[0])
    vol_scaler = float(np.clip(0.025 / (m_yz + 1e-8), 0.60, 1.60))

    # --- Variant 0: Baseline (K=7, Heuristic Lev) ---
    lev_0 = float(np.clip(1.50 * vol_scaler, 0.50, 2.00))
    w_raw_0 = compute_hrp_from_cov(shrunk_cov, a_sub, target_leverage=lev_0, top_k=7)
    target_w0 = {v_cols[i]: float(w_raw_0[i]) for i in range(len(v_cols)) if abs(w_raw_0[i]) > 0.005}

    # --- Variant 1: Vol-Targeted Control (K=10, sigma*=22%) ---
    w_unit = compute_hrp_from_cov(shrunk_cov, a_sub, target_leverage=1.0, top_k=10)
    port_var = float(w_unit.T @ shrunk_cov @ w_unit)
    port_vol = np.sqrt(max(port_var, 1e-8))
    lev_target = float(np.clip(TARGET_BAR_VOL / port_vol, 0.60, 2.50))
    w_scaled = w_unit * lev_target
    target_w1 = {v_cols[i]: float(w_scaled[i]) for i in range(len(v_cols)) if abs(w_scaled[i]) > 0.005}

    # --- Variant 2: Vol-Targeted + Sign-Preserving Leland Deadband ---
    target_w2 = {}
    all_syms_l = set(prev_weights[2].keys()).union(target_w1.keys())
    for s in all_syms_l:
        w_t = target_w1.get(s, 0.0)
        w_prev = prev_weights[2].get(s, 0.0)
        sigma = max(0.015, vols_map.get(s, 0.025))

        if abs(w_t) < 1e-4 or abs(w_prev) < 1e-4 or (w_t * w_prev < 0):
            target_w2[s] = w_t
            continue

        h_star = np.clip(((4.0 / 3.0) * (fee_rate * (sigma ** 2.0)) / gamma_mvo) ** (1.0 / 3.0), 0.010, 0.035)
        delta = w_t - w_prev
        if abs(delta) > h_star:
            target_w2[s] = w_t - np.sign(delta) * h_star
        else:
            target_w2[s] = w_prev
    target_w2 = {s: w for s, w in target_w2.items() if abs(w) > 0.005}

    # --- Variant 3: Vol-Targeted + Rank Hysteresis ---
    sorted_alpha = sorted(v_cols, key=lambda s: alpha_dict[s], reverse=True)
    N = len(sorted_alpha)
    rank_map = {s: r for r, s in enumerate(sorted_alpha)}

    new_longs = set(sorted_alpha[:ENTRY_K])
    for s in active_longs:
        if s in rank_map and rank_map[s] < EXIT_K and s not in sorted_alpha[-EXIT_K:]:
            new_longs.add(s)

    new_shorts = set(sorted_alpha[-ENTRY_K:])
    for s in active_shorts:
        if s in rank_map and rank_map[s] >= (N - EXIT_K) and s not in sorted_alpha[:EXIT_K]:
            new_shorts.add(s)

    new_longs = new_longs - new_shorts
    active_longs, active_shorts = new_longs, new_shorts
    selected_hyst = list(active_longs.union(active_shorts))

    target_w3 = {}
    if selected_hyst:
        w_raw_h = compute_hrp_from_cov(shrunk_cov, a_sub, target_leverage=1.0, top_k=len(selected_hyst))
        port_var_h = float(w_raw_h.T @ shrunk_cov @ w_raw_h)
        port_vol_h = np.sqrt(max(port_var_h, 1e-8))
        lev_h = float(np.clip(TARGET_BAR_VOL / port_vol_h, 0.60, 2.50))
        w_scaled_h = w_raw_h * lev_h
        coin_weights = {v_cols[i]: float(w_scaled_h[i]) for i in range(len(v_cols))}
        for s in selected_hyst:
            if s in active_longs and coin_weights.get(s, 0.0) > 0:
                target_w3[s] = coin_weights[s]
            elif s in active_shorts and coin_weights.get(s, 0.0) < 0:
                target_w3[s] = coin_weights[s]
    target_w3 = {s: w for s, w in target_w3.items() if abs(w) > 0.005}

    # Accounting & Net PnL Execution across all variants
    all_targets = [target_w0, target_w1, target_w2, target_w3]
    for v in range(4):
        tw = all_targets[v]
        pw = prev_weights[v]
        all_syms = set(pw.keys()).union(tw.keys())
        to = sum(abs(tw.get(s, 0.0) - pw.get(s, 0.0)) for s in all_syms)
        turnovers[v] += to
        cost = to * fee_rate
        pnl = sum(tw.get(s, 0.0) * returns_map.get(s, 0.0) for s in tw) - cost
        navs[v] *= (1.0 + pnl)
        returns_hist[v].append(pnl)
        prev_weights[v] = tw

    if (idx + 1) % 500 == 0 or (idx + 1) == len(eval_groups) - 1:
        print(f"  • Progress: {idx + 1}/{len(eval_groups) - 1} bars ({time.time() - t0:.1f}s elapsed)...")

# Summary Metrics Calculation
print("\n" + "=" * 82)
print("             FULL-SCALE MACRO RE-TEST: BENCHMARK SUMMARY")
print("=" * 82)
headers = ["Metric", "Baseline (K=7)", "Vol-Target (K=10)", "VT + Leland", "VT + Hysteresis"]
print(f"{headers[0]:<23} | {headers[1]:<13} | {headers[2]:<13} | {headers[3]:<13} | {headers[4]:<13}")
print("-" * 82)

def calc_all(nav, rets, to):
    r = np.array(rets)
    cagr = (nav / 10_000.0) ** (BARS_PER_YEAR / len(r)) - 1.0
    sharpe = np.mean(r) / (np.std(r) + 1e-6) * np.sqrt(BARS_PER_YEAR)
    vol = np.std(r) * np.sqrt(BARS_PER_YEAR)
    cum = np.cumprod(1.0 + r)
    mdd = np.min((cum - np.maximum.accumulate(cum)) / np.maximum.accumulate(cum))
    return cagr, sharpe, vol, mdd, to

results = [calc_all(navs[i], returns_hist[i], turnovers[i]) for i in range(4)]

print(f"{'Net CAGR':<23} | {results[0][0]*100:>+12.2f}% | {results[1][0]*100:>+12.2f}% | {results[2][0]*100:>+12.2f}% | {results[3][0]*100:>+12.2f}%")
print(f"{'Net Sharpe Ratio':<23} | {results[0][1]:>13.2f} | {results[1][1]:>13.2f} | {results[2][1]:>13.2f} | {results[3][1]:>13.2f}")
print(f"{'Realized Volatility':<23} | {results[0][2]*100:>12.2f}% | {results[1][2]*100:>12.2f}% | {results[2][2]*100:>12.2f}% | {results[3][2]*100:>12.2f}%")
print(f"{'Max Drawdown':<23} | {results[0][3]*100:>12.2f}% | {results[1][3]*100:>12.2f}% | {results[2][3]*100:>12.2f}% | {results[3][3]*100:>12.2f}%")
print(f"{'Total Turnover':<23} | {results[0][4]:>12.1f}x | {results[1][4]:>12.1f}x | {results[2][4]:>12.1f}x | {results[3][4]:>12.1f}x")
print(f"{'Turnover / 4H Bar':<23} | {results[0][4]/len(returns_hist[0]):>12.2f}x | {results[1][4]/len(returns_hist[1]):>12.2f}x | {results[2][4]/len(returns_hist[2]):>12.2f}x | {results[3][4]/len(returns_hist[3]):>12.2f}x")
print("=" * 82)
