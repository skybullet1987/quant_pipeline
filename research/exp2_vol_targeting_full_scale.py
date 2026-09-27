import sys
import time
from pathlib import Path
import numpy as np
import polars as pl
from sklearn.covariance import LedoitWolf

sys.path.insert(0, str(Path.home() / "quant_pipeline"))
from src.signals.multiscale_alpha_engine import ProductionMultiScaleEngine, compute_ensemble_alpha, compute_hrp_from_cov
from src.config import STRATEGY_CONFIG

print("=" * 78)
print("   FULL-SCALE WALK-FORWARD BENCHMARK (ALL AVAILABLE REGIMES)")
print("=" * 78)

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
# Need at least 168 bars of history for Ledoit-Wolf covariance warmup
valid_groups = [g for g in all_groups if g >= 168]

print(f"[+] Total available historical groups with full warmup : {len(valid_groups)} (groups {valid_groups[0]} to {valid_groups[-1]})")
print(f"[+] Out-of-Sample Holdout boundary                     : group 1315 (~{len([g for g in valid_groups if g >= 1315])} bars)")

fee_rate = 0.00015  # 1.5 bps maker fee + slippage
TARGET_ANN_VOL = 0.22
BARS_PER_YEAR = 6 * 365
TARGET_BAR_VOL = TARGET_ANN_VOL / np.sqrt(BARS_PER_YEAR)

def run_simulation(start_group: int, end_group: int, run_label: str):
    eval_groups = [g for g in valid_groups if start_group <= g <= end_group]
    print(f"\n[+] Running {run_label}: {len(eval_groups)} 4H bars ({len(eval_groups)/6:.1f} days)...")
    t0 = time.time()

    nav_a, nav_b, nav_c = 10_000.0, 10_000.0, 10_000.0
    to_a, to_b, to_c = 0.0, 0.0, 0.0
    prev_w_a, prev_w_b, prev_w_c = {}, {}, {}
    rets_a, rets_b, rets_c = [], [], []
    levs_a, levs_b, levs_c = [], [], []

    for idx in range(len(eval_groups) - 1):
        grp = eval_groups[idx]
        next_grp = eval_groups[idx + 1]

        cur_panel = df.filter(pl.col("group_id") == grp)
        next_panel = df.filter(pl.col("group_id") == next_grp)
        returns_map = dict(zip(next_panel["symbol"].to_list(), next_panel["ret_4h"].to_list()))
        cur_rows = {r["symbol"]: r for r in cur_panel.iter_rows(named=True)}
        symbols = list(cur_rows.keys())

        # Model Inference
        X_live = cur_panel.select(engine.m12.feature_names_).to_pandas()
        p12 = engine.m12.predict(X_live)
        p48 = engine.m48.predict(X_live)
        p168 = engine.m168.predict(X_live)
        alpha_vec = compute_ensemble_alpha(p12, p48, p168, {"12h": [], "48h": [], "168h": []}, use_dynamic_ir=True)
        alpha_dict = {s: v for s, v in zip(symbols, alpha_vec)}

        # Covariance Matrix Estimation
        hist = df.filter((pl.col("group_id") <= grp) & (pl.col("group_id") > grp - 168))
        piv = hist.pivot(values="ret_4h", index="group_id", on="symbol").sort("group_id")
        v_cols = [c for c in symbols if c in piv.columns and piv[c].null_count() == 0]
        if len(v_cols) < 20:
            continue

        shrunk_cov = LedoitWolf().fit(piv.select(v_cols).to_numpy()).covariance_
        a_sub = np.array([alpha_dict[s] for s in v_cols])
        m_yz = float(cur_panel.select(pl.mean("vol_yang_zhang")).to_series()[0])
        vol_scaler = float(np.clip(0.025 / (m_yz + 1e-8), 0.60, 1.60))

        # --- Variant A: Baseline (K=7, Heuristic Lev) ---
        lev_a = float(np.clip(1.50 * vol_scaler, 0.50, 2.00))
        w_raw_a = compute_hrp_from_cov(shrunk_cov, a_sub, target_leverage=lev_a, top_k=7)
        target_w_a = {v_cols[i]: float(w_raw_a[i]) for i in range(len(v_cols)) if abs(w_raw_a[i]) > 0.005}

        turn_a = sum(abs(target_w_a.get(s, 0.0) - prev_w_a.get(s, 0.0)) for s in set(prev_w_a).union(target_w_a))
        to_a += turn_a
        pnl_a = sum(target_w_a.get(s, 0.0) * returns_map.get(s, 0.0) for s in target_w_a) - (turn_a * fee_rate)
        nav_a *= (1.0 + pnl_a)
        rets_a.append(pnl_a)
        levs_a.append(sum(abs(w) for w in target_w_a.values()))
        prev_w_a = target_w_a

        # --- Variant B: Expanded Breadth (K=10, Heuristic Lev) ---
        lev_b = lev_a
        w_raw_b = compute_hrp_from_cov(shrunk_cov, a_sub, target_leverage=lev_b, top_k=10)
        target_w_b = {v_cols[i]: float(w_raw_b[i]) for i in range(len(v_cols)) if abs(w_raw_b[i]) > 0.005}

        turn_b = sum(abs(target_w_b.get(s, 0.0) - prev_w_b.get(s, 0.0)) for s in set(prev_w_b).union(target_w_b))
        to_b += turn_b
        pnl_b = sum(target_w_b.get(s, 0.0) * returns_map.get(s, 0.0) for s in target_w_b) - (turn_b * fee_rate)
        nav_b *= (1.0 + pnl_b)
        rets_b.append(pnl_b)
        levs_b.append(sum(abs(w) for w in target_w_b.values()))
        prev_w_b = target_w_b

        # --- Variant C: Vol-Target (K=10, Ex-Ante Target sigma* = 22%) ---
        w_unit = compute_hrp_from_cov(shrunk_cov, a_sub, target_leverage=1.0, top_k=10)
        port_var = float(w_unit.T @ shrunk_cov @ w_unit)
        port_vol = np.sqrt(max(port_var, 1e-8))

        lev_c = float(np.clip(TARGET_BAR_VOL / port_vol, 0.60, 2.50))
        w_c_scaled = w_unit * lev_c
        target_w_c = {v_cols[i]: float(w_c_scaled[i]) for i in range(len(v_cols)) if abs(w_c_scaled[i]) > 0.005}

        turn_c = sum(abs(target_w_c.get(s, 0.0) - prev_w_c.get(s, 0.0)) for s in set(prev_w_c).union(target_w_c))
        to_c += turn_c
        pnl_c = sum(target_w_c.get(s, 0.0) * returns_map.get(s, 0.0) for s in target_w_c) - (turn_c * fee_rate)
        nav_c *= (1.0 + pnl_c)
        rets_c.append(pnl_c)
        levs_c.append(sum(abs(w) for w in target_w_c.values()))
        prev_w_c = target_w_c

        if (idx + 1) % 250 == 0 or (idx + 1) == len(eval_groups) - 1:
            elapsed = time.time() - t0
            print(f"  • Processed {idx + 1}/{len(eval_groups) - 1} bars [{elapsed:.1f}s elapsed]...")

    def calc_metrics(nav, rets, levs, to):
        r = np.array(rets)
        n_bars = len(r)
        cagr = (nav / 10_000.0) ** (BARS_PER_YEAR / n_bars) - 1.0
        sharpe = np.mean(r) / (np.std(r) + 1e-6) * np.sqrt(BARS_PER_YEAR)
        ann_vol = np.std(r) * np.sqrt(BARS_PER_YEAR)
        cum = np.cumprod(1.0 + r)
        mdd = np.min((cum - np.maximum.accumulate(cum)) / np.maximum.accumulate(cum))
        calmar = cagr / abs(mdd) if abs(mdd) > 0 else 0.0
        win_rate = np.mean(r > 0) * 100
        return cagr, sharpe, ann_vol, mdd, calmar, np.mean(levs), to, win_rate

    ma = calc_metrics(nav_a, rets_a, levs_a, to_a)
    mb = calc_metrics(nav_b, rets_b, levs_b, to_b)
    mc = calc_metrics(nav_c, rets_c, levs_c, to_c)

    print("\n" + "=" * 78)
    print(f"       BENCHMARK RESULTS: {run_label.upper()}")
    print("=" * 78)
    print(f"{'Metric':<25} | {'Baseline (K=7)':<15} | {'Breadth (K=10)':<15} | {'Vol-Target (C)':<15}")
    print("-" * 78)
    print(f"{'Net CAGR':<25} | {ma[0]*100:>+14.2f}% | {mb[0]*100:>+14.2f}% | {mc[0]*100:>+14.2f}%")
    print(f"{'Net Sharpe Ratio':<25} | {ma[1]:>15.2f} | {mb[1]:>15.2f} | {mc[1]:>15.2f}")
    print(f"{'Calmar Ratio':<25} | {ma[4]:>15.2f} | {mb[4]:>15.2f} | {mc[4]:>15.2f}")
    print(f"{'Realized Volatility':<25} | {ma[2]*100:>14.2f}% | {mb[2]*100:>14.2f}% | {mc[2]*100:>14.2f}%")
    print(f"{'Max Drawdown':<25} | {ma[3]*100:>14.2f}% | {mb[3]*100:>14.2f}% | {mc[3]*100:>14.2f}%")
    print(f"{'Win Rate (% Bars)':<25} | {ma[7]:>14.1f}% | {mb[7]:>14.1f}% | {mc[7]:>14.1f}%")
    print(f"{'Mean Realized Leverage':<25} | {ma[5]:>14.2f}x | {mb[5]:>14.2f}x | {mc[5]:>14.2f}x")
    print(f"{'Total Turnover':<25} | {ma[6]:>14.1f}x | {mb[6]:>14.1f}x | {mc[6]:>14.1f}x")
    print("=" * 78)

# Run 1: Strict Out-of-Sample Holdout (Group 1315 to 2220, ~151 days)
run_simulation(1315, 2220, "Strict Out-of-Sample Holdout (905 Bars)")

# Run 2: Full Macro Cycle (Group 168 to 2220, ~342 days)
run_simulation(168, 2220, "Full Macro Historical Lake (2,052 Bars)")
