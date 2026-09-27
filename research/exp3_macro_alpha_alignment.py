import sys
import time
from pathlib import Path
import numpy as np
import polars as pl
from sklearn.covariance import LedoitWolf

sys.path.insert(0, str(Path.home() / "quant_pipeline"))
from src.signals.multiscale_alpha_engine import ProductionMultiScaleEngine, compute_hrp_from_cov

print("=" * 84)
print("   EXPERIMENT 3: ALPHA SIGN ALIGNMENT & HORIZON TUNING (2,052 BARS)")
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
print(f"[+] Replaying full 342-day historical cycle ({len(eval_groups)} 4H bars)...")

fee_rate = 0.00015  # 1.5 bps ALO maker fee
gamma_mvo = 0.05
TARGET_ANN_VOL = 0.22
BARS_PER_YEAR = 6 * 365
TARGET_BAR_VOL = TARGET_ANN_VOL / np.sqrt(BARS_PER_YEAR)

# 0: Uncorrected Production (+0.30*p12 + 0.45*p48 + 0.25*p168)
# 1: Sign-Corrected (-0.30*p12 + 0.45*p48 + 0.25*p168)
# 2: Pruned 12H (0.40*p48 + 0.60*p168)
# 3: Heavy Trend (0.20*p48 + 0.80*p168)

navs = [10_000.0] * 4
turnovers = [0.0] * 4
prev_weights = [{}, {}, {}, {}]
returns_hist = [[], [], [], []]

def zscore(arr):
    s = np.std(arr)
    return (arr - np.mean(arr)) / (s if s > 1e-6 else 1.0)

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
    p12 = engine.m12.predict(X_live)
    p48 = engine.m48.predict(X_live)
    p168 = engine.m168.predict(X_live)

    z12, z48, z168 = zscore(p12), zscore(p48), zscore(p168)

    alphas = [
        (0.30 * z12) + (0.45 * z48) + (0.25 * z168),     # Uncorrected
        (-0.30 * z12) + (0.45 * z48) + (0.25 * z168),    # Sign-Corrected
        (0.40 * z48) + (0.60 * z168),                     # Pruned 12H
        (0.20 * z48) + (0.80 * z168)                      # Heavy Trend
    ]

    hist = df.filter((pl.col("group_id") <= grp) & (pl.col("group_id") > grp - 168))
    piv = hist.pivot(values="ret_4h", index="group_id", on="symbol").sort("group_id")
    v_cols = [c for c in symbols if c in piv.columns and piv[c].null_count() == 0]
    if len(v_cols) < 20:
        continue

    shrunk_cov = LedoitWolf().fit(piv.select(v_cols).to_numpy()).covariance_

    for v in range(4):
        a_dict = {s: val for s, val in zip(symbols, alphas[v])}
        a_sub = np.array([a_dict[s] for s in v_cols])

        # Unit HRP weights with K=10
        w_unit = compute_hrp_from_cov(shrunk_cov, a_sub, target_leverage=1.0, top_k=10)
        port_var = float(w_unit.T @ shrunk_cov @ w_unit)
        port_vol = np.sqrt(max(port_var, 1e-8))
        lev_target = float(np.clip(TARGET_BAR_VOL / port_vol, 0.60, 2.50))
        w_scaled = w_unit * lev_target
        raw_target = {v_cols[i]: float(w_scaled[i]) for i in range(len(v_cols)) if abs(w_scaled[i]) > 0.005}

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

            h_star = np.clip(((4.0 / 3.0) * (fee_rate * (sigma ** 2.0)) / gamma_mvo) ** (1.0 / 3.0), 0.010, 0.035)
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

# Performance Summary
print("\n" + "=" * 84)
print("             ALPHA ALIGNMENT & HORIZON BENCHMARK RESULTS")
print("=" * 84)
headers = ["Metric", "Uncorrected (Prod)", "Sign-Corrected 12H", "Pruned 12H (48/168)", "Heavy Trend (20/80)"]
print(f"{headers[0]:<23} | {headers[1]:<18} | {headers[2]:<18} | {headers[3]:<18} | {headers[4]:<18}")
print("-" * 84)

def calc_stats(nav, rets, to):
    r = np.array(rets)
    cagr = (nav / 10_000.0) ** (BARS_PER_YEAR / len(r)) - 1.0
    sharpe = np.mean(r) / (np.std(r) + 1e-6) * np.sqrt(BARS_PER_YEAR)
    vol = np.std(r) * np.sqrt(BARS_PER_YEAR)
    cum = np.cumprod(1.0 + r)
    mdd = np.min((cum - np.maximum.accumulate(cum)) / np.maximum.accumulate(cum))
    calmar = cagr / abs(mdd) if abs(mdd) > 0 else 0.0
    win_rate = np.mean(r > 0) * 100
    return cagr, sharpe, vol, mdd, calmar, win_rate, to

res = [calc_stats(navs[i], returns_hist[i], turnovers[i]) for i in range(4)]

print(f"{'Net CAGR':<23} | {res[0][0]*100:>+17.2f}% | {res[1][0]*100:>+17.2f}% | {res[2][0]*100:>+17.2f}% | {res[3][0]*100:>+17.2f}%")
print(f"{'Net Sharpe Ratio':<23} | {res[0][1]:>18.2f} | {res[1][1]:>18.2f} | {res[2][1]:>18.2f} | {res[3][1]:>18.2f}")
print(f"{'Calmar Ratio':<23} | {res[0][4]:>18.2f} | {res[1][4]:>18.2f} | {res[2][4]:>18.2f} | {res[3][4]:>18.2f}")
print(f"{'Realized Volatility':<23} | {res[0][2]*100:>17.2f}% | {res[1][2]*100:>17.2f}% | {res[2][2]*100:>17.2f}% | {res[3][2]*100:>17.2f}%")
print(f"{'Max Drawdown':<23} | {res[0][3]*100:>17.2f}% | {res[1][3]*100:>17.2f}% | {res[2][3]*100:>17.2f}% | {res[3][3]*100:>17.2f}%")
print(f"{'Bar Win Rate':<23} | {res[0][5]:>17.1f}% | {res[1][5]:>17.1f}% | {res[2][5]:>17.1f}% | {res[3][5]:>17.1f}%")
print(f"{'Total Turnover':<23} | {res[0][6]:>17.1f}x | {res[1][6]:>17.1f}x | {res[2][6]:>17.1f}x | {res[3][6]:>17.1f}x")
print("=" * 84)
