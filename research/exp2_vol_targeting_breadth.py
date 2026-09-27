import sys
from pathlib import Path
import numpy as np
import polars as pl
from sklearn.covariance import LedoitWolf

sys.path.insert(0, str(Path.home() / "quant_pipeline"))
from src.signals.multiscale_alpha_engine import ProductionMultiScaleEngine, compute_ensemble_alpha, compute_hrp_from_cov
from src.config import STRATEGY_CONFIG

print("=" * 70)
print("   EXPERIMENT 2.1: DYNAMIC VOL TARGETING (22%) & BREADTH EXPANSION")
print("=" * 70)

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
test_groups = [g for g in all_groups if g >= (all_groups[-1] - 180)]
print(f"[+] Walking forward over {len(test_groups)} bars...")

# Hyperliquid execution parameters
fee_rate = 0.00015  # 1.5 bps realistic ALO maker fee + slippage
TARGET_ANN_VOL = 0.22  # 22% annualized target volatility
BARS_PER_YEAR = 6 * 365
TARGET_BAR_VOL = TARGET_ANN_VOL / np.sqrt(BARS_PER_YEAR)

# Variant A: Baseline (K=7, Heuristic Leverage ~1.21x)
# Variant B: Expanded Breadth (K=10, Heuristic Leverage)
# Variant C: Expanded Breadth (K=10, Ex-Ante Vol Targeting sigma* = 22%, Max Lev = 2.50x)

nav_a, nav_b, nav_c = 10_000.0, 10_000.0, 10_000.0
to_a, to_b, to_c = 0.0, 0.0, 0.0
prev_w_a, prev_w_b, prev_w_c = {}, {}, {}
rets_a, rets_b, rets_c = [], [], []
levs_a, levs_b, levs_c = [], [], []

for i in range(len(test_groups) - 1):
    grp = test_groups[i]
    next_grp = test_groups[i + 1]

    cur_panel = df.filter(pl.col("group_id") == grp)
    next_panel = df.filter(pl.col("group_id") == next_grp)
    returns_map = dict(zip(next_panel["symbol"].to_list(), next_panel["ret_4h"].to_list()))
    cur_rows = {r["symbol"]: r for r in cur_panel.iter_rows(named=True)}
    symbols = list(cur_rows.keys())

    # --- 1. Common Alpha and Covariance State ---
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

    # --- Variant A: Baseline (K=7, Lev capped at 2.0x, mean ~1.21x) ---
    lev_a = float(np.clip(1.50 * vol_scaler, 0.50, 2.00))
    w_raw_a = compute_hrp_from_cov(shrunk_cov, a_sub, lev_a, top_k=7)
    target_w_a = {v_cols[idx]: float(w_raw_a[idx]) for idx in range(len(v_cols)) if abs(w_raw_a[idx]) > 0.005}

    all_a = set(prev_w_a.keys()).union(target_w_a.keys())
    turn_a = sum(abs(target_w_a.get(s, 0.0) - prev_w_a.get(s, 0.0)) for s in all_a)
    to_a += turn_a
    pnl_a = sum(target_w_a.get(s, 0.0) * returns_map.get(s, 0.0) for s in target_w_a) - (turn_a * fee_rate)
    nav_a *= (1.0 + pnl_a)
    rets_a.append(pnl_a)
    levs_a.append(sum(abs(w) for w in target_w_a.values()))
    prev_w_a = target_w_a

    # --- Variant B: Expanded Breadth (K=10, Same Heuristic Sizing) ---
    lev_b = lev_a
    w_raw_b = compute_hrp_from_cov(shrunk_cov, a_sub, lev_b, top_k=10)
    target_w_b = {v_cols[idx]: float(w_raw_b[idx]) for idx in range(len(v_cols)) if abs(w_raw_b[idx]) > 0.005}

    all_b = set(prev_w_b.keys()).union(target_w_b.keys())
    turn_b = sum(abs(target_w_b.get(s, 0.0) - prev_w_b.get(s, 0.0)) for s in all_b)
    to_b += turn_b
    pnl_b = sum(target_w_b.get(s, 0.0) * returns_map.get(s, 0.0) for s in target_w_b) - (turn_b * fee_rate)
    nav_b *= (1.0 + pnl_b)
    rets_b.append(pnl_b)
    levs_b.append(sum(abs(w) for w in target_w_b.values()))
    prev_w_b = target_w_b

    # --- Variant C: K=10 + Ex-Ante Volatility Targeting (sigma* = 22%) ---
    # 1. Compute unit-leveraged HRP basket weights
    w_unit = compute_hrp_from_cov(shrunk_cov, a_sub, target_leverage=1.0, top_k=10)
    
    # 2. Portfolio ex-ante variance: w^T * Sigma * w
    port_var = float(w_unit.T @ shrunk_cov @ w_unit)
    port_vol = np.sqrt(max(port_var, 1e-8))

    # 3. Scale leverage to target exact bar volatility, bounded in [0.60x, 2.50x]
    lev_c = float(np.clip(TARGET_BAR_VOL / port_vol, 0.60, 2.50))
    w_c_scaled = w_unit * lev_c
    target_w_c = {v_cols[idx]: float(w_c_scaled[idx]) for idx in range(len(v_cols)) if abs(w_c_scaled[idx]) > 0.005}

    all_c = set(prev_w_c.keys()).union(target_w_c.keys())
    turn_c = sum(abs(target_w_c.get(s, 0.0) - prev_w_c.get(s, 0.0)) for s in all_c)
    to_c += turn_c
    pnl_c = sum(target_w_c.get(s, 0.0) * returns_map.get(s, 0.0) for s in target_w_c) - (turn_c * fee_rate)
    nav_c *= (1.0 + pnl_c)
    rets_c.append(pnl_c)
    levs_c.append(sum(abs(w) for w in target_w_c.values()))
    prev_w_c = target_w_c

# Statistics
def calc_stats(nav, rets, levs, to):
    rets_arr = np.array(rets)
    cagr = (nav / 10_000.0) ** (BARS_PER_YEAR / len(rets_arr)) - 1.0
    sharpe = np.mean(rets_arr) / (np.std(rets_arr) + 1e-6) * np.sqrt(BARS_PER_YEAR)
    ann_vol = np.std(rets_arr) * np.sqrt(BARS_PER_YEAR)
    cum = np.cumprod(1.0 + rets_arr)
    mdd = np.min((cum - np.maximum.accumulate(cum)) / np.maximum.accumulate(cum))
    return cagr, sharpe, ann_vol, mdd, np.mean(levs), to

stats_a = calc_stats(nav_a, rets_a, levs_a, to_a)
stats_b = calc_stats(nav_b, rets_b, levs_b, to_b)
stats_c = calc_stats(nav_c, rets_c, levs_c, to_c)

print("\n" + "=" * 75)
print("             EXPERIMENT 2.1: COMPARATIVE BENCHMARK")
print("=" * 75)
print(f"{'Metric':<25} | {'Baseline (A: K=7)':<15} | {'Breadth (B: K=10)':<15} | {'Vol-Target (C)':<15}")
print("-" * 75)
print(f"{'Net CAGR':<25} | {stats_a[0]*100:>+14.2f}% | {stats_b[0]*100:>+14.2f}% | {stats_c[0]*100:>+14.2f}%")
print(f"{'Net Sharpe Ratio':<25} | {stats_a[1]:>15.2f} | {stats_b[1]:>15.2f} | {stats_c[1]:>15.2f}")
print(f"{'Realized Ann Volatility':<25} | {stats_a[2]*100:>14.2f}% | {stats_b[2]*100:>14.2f}% | {stats_c[2]*100:>14.2f}%")
print(f"{'Max Drawdown':<25} | {stats_a[3]*100:>14.2f}% | {stats_b[3]*100:>14.2f}% | {stats_c[3]*100:>14.2f}%")
print(f"{'Mean Realized Leverage':<25} | {stats_a[4]:>14.2f}x | {stats_b[4]:>14.2f}x | {stats_c[4]:>14.2f}x")
print(f"{'Total Cumulative Turnover':<25} | {stats_a[5]:>14.1f}x | {stats_b[5]:>14.1f}x | {stats_c[5]:>14.1f}x")
print("=" * 75)
