import sys
from pathlib import Path
import numpy as np
import polars as pl
from sklearn.covariance import LedoitWolf

sys.path.insert(0, str(Path.home() / "quant_pipeline"))
from src.signals.multiscale_alpha_engine import ProductionMultiScaleEngine, compute_ensemble_alpha, compute_hrp_from_cov
from src.config import STRATEGY_CONFIG

print("=" * 65)
print("   EXPERIMENT 1.2: MEMBERSHIP HYSTERESIS BENCHMARK")
print("=" * 65)

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
print(f"[+] Replaying {len(test_groups)} historical bars...")

fee_rate = 0.00035

nav_base, nav_hyst = 10_000.0, 10_000.0
turnover_base, turnover_hyst = 0.0, 0.0
prev_w_base, prev_w_hyst = {}, {}
rets_base, rets_hyst = [], []

# Persistent active sets for hysteresis
active_longs = set()
active_shorts = set()

ENTRY_K = 7
EXIT_K = 11

for i, grp in enumerate(test_groups[:-1]):
    next_grp = test_groups[i + 1]

    # --- Variant A: Baseline Production Logic ---
    w_base, _ = engine.generate_target_portfolio(
        df=df, target_grp=grp,
        max_bull_lev=STRATEGY_CONFIG.portfolio.max_bull_leverage,
        s0_short_mult=STRATEGY_CONFIG.portfolio.s0_short_multiplier,
        carry_lev=STRATEGY_CONFIG.portfolio.target_carry_leverage,
        top_k=STRATEGY_CONFIG.portfolio.top_k_conviction,
        retrain_step=STRATEGY_CONFIG.regime_model.retrain_step_bars
    )
    if not w_base:
        continue

    cur_panel = df.filter(pl.col("group_id") == grp)
    next_panel = df.filter(pl.col("group_id") == next_grp)
    returns_map = dict(zip(next_panel["symbol"].to_list(), next_panel["ret_4h"].to_list()))

    all_base = set(prev_w_base.keys()).union(w_base.keys())
    to_a = sum(abs(w_base.get(s, 0.0) - prev_w_base.get(s, 0.0)) for s in all_base)
    turnover_base += to_a
    pnl_a = sum(w_base.get(s, 0.0) * returns_map.get(s, 0.0) for s in w_base) - (to_a * fee_rate)
    nav_base *= (1.0 + pnl_a)
    rets_base.append(pnl_a)
    prev_w_base = w_base

    # --- Variant B: Membership Hysteresis ---
    cur_rows = {r["symbol"]: r for r in cur_panel.iter_rows(named=True)}
    symbols = list(cur_rows.keys())

    X_live = cur_panel.select(engine.m12.feature_names_).to_pandas()
    p12 = engine.m12.predict(X_live)
    p48 = engine.m48.predict(X_live)
    p168 = engine.m168.predict(X_live)
    alpha_vec = compute_ensemble_alpha(p12, p48, p168, {"12h": [], "48h": [], "168h": []}, use_dynamic_ir=True)
    alpha_dict = {s: v for s, v in zip(symbols, alpha_vec)}

    hist = df.filter((pl.col("group_id") <= grp) & (pl.col("group_id") > grp - 168))
    piv = hist.pivot(values="ret_4h", index="group_id", on="symbol").sort("group_id")
    v_cols = [c for c in symbols if c in piv.columns and piv[c].null_count() == 0]

    sorted_alpha = sorted(v_cols, key=lambda s: alpha_dict[s], reverse=True)
    N = len(sorted_alpha)
    rank_map = {s: r for r, s in enumerate(sorted_alpha)}

    # Buffer: Enter if rank <= 7; hold until rank > 11
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

    shrunk_cov = LedoitWolf().fit(piv.select(v_cols).to_numpy()).covariance_
    m_yz = float(cur_panel.select(pl.mean("vol_yang_zhang")).to_series()[0])
    vol_scaler = float(np.clip(0.025 / (m_yz + 1e-8), 0.60, 1.60))
    target_lev = float(np.clip(1.50 * vol_scaler, 0.50, 2.20))

    selected_coins = list(active_longs.union(active_shorts))
    w_hyst = {}
    if selected_coins:
        a_sub = np.array([alpha_dict[s] for s in v_cols])
        w_raw = compute_hrp_from_cov(shrunk_cov, a_sub, target_lev, top_k=len(selected_coins))
        coin_weights = {v_cols[idx]: float(w_raw[idx]) for idx in range(len(v_cols))}
        for s in selected_coins:
            if s in active_longs and coin_weights.get(s, 0.0) > 0:
                w_hyst[s] = coin_weights[s]
            elif s in active_shorts and coin_weights.get(s, 0.0) < 0:
                w_hyst[s] = coin_weights[s]

    all_hyst = set(prev_w_hyst.keys()).union(w_hyst.keys())
    to_b = sum(abs(w_hyst.get(s, 0.0) - prev_w_hyst.get(s, 0.0)) for s in all_hyst)
    turnover_hyst += to_b
    pnl_b = sum(w_hyst.get(s, 0.0) * returns_map.get(s, 0.0) for s in w_hyst) - (to_b * fee_rate)
    nav_hyst *= (1.0 + pnl_b)
    rets_hyst.append(pnl_b)
    prev_w_hyst = w_hyst

bars_per_year = 6 * 365
rets_a = np.array(rets_base)
rets_b = np.array(rets_hyst)

cagr_a = (nav_base / 10_000.0) ** (bars_per_year / len(rets_a)) - 1.0
cagr_b = (nav_hyst / 10_000.0) ** (bars_per_year / len(rets_b)) - 1.0

sharpe_a = np.mean(rets_a) / (np.std(rets_a) + 1e-6) * np.sqrt(bars_per_year)
sharpe_b = np.mean(rets_b) / (np.std(rets_b) + 1e-6) * np.sqrt(bars_per_year)

def max_dd(r):
    cum = np.cumprod(1.0 + r)
    return np.min((cum - np.maximum.accumulate(cum)) / np.maximum.accumulate(cum))

print("\n" + "=" * 65)
print("             RANK HYSTERESIS BENCHMARK RESULTS")
print("=" * 65)
print(f"{'Metric':<26} | {'Baseline (A)':<16} | {'Hysteresis (B)':<16}")
print("-" * 65)
print(f"{'Net CAGR':<26} | {cagr_a * 100:>+15.2f}% | {cagr_b * 100:>+15.2f}%")
print(f"{'Net Sharpe Ratio':<26} | {sharpe_a:>16.2f} | {sharpe_b:>16.2f}")
print(f"{'Max Drawdown':<26} | {max_dd(rets_a) * 100:>15.2f}% | {max_dd(rets_b) * 100:>15.2f}%")
print(f"{'Total Turnover':<26} | {turnover_base:>15.1f}x | {turnover_hyst:>15.1f}x")
print(f"{'Turnover per 4H Bar':<26} | {turnover_base / len(rets_a):>15.2f}x | {turnover_hyst / len(rets_b):>15.2f}x")
turnover_reduc = (1.0 - turnover_hyst / turnover_base) * 100
fee_saved = (turnover_base - turnover_hyst) * fee_rate * 100
print("-" * 65)
print(f"• Turnover Reduction Achieved : {turnover_reduc:.1f}%")
print(f"• Equity Saved from Fee Drag  : {fee_saved:+.2f}% of NAV")
print("=" * 65)
