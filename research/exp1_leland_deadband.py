import sys
from pathlib import Path
import numpy as np
import polars as pl

sys.path.insert(0, str(Path.home() / "quant_pipeline"))
from src.signals.multiscale_alpha_engine import ProductionMultiScaleEngine
from src.config import STRATEGY_CONFIG

print("=" * 65)
print("   EXPERIMENT 1: BASELINE vs. LELAND DEADBAND (A/B TEST)")
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
print(f"[+] Replaying {len(test_groups)} historical bars (identical inputs)...")

fee_rate = 0.00035  # 3.5 bps maker fee + half-spread slippage
gamma_mvo = 0.05    # Risk aversion parameter

# Trackers
nav_base, nav_leland = 10_000.0, 10_000.0
turnover_base, turnover_leland = 0.0, 0.0
prev_w_base, prev_w_leland = {}, {}
returns_base, returns_leland = [], []

for i, grp in enumerate(test_groups[:-1]):
    next_grp = test_groups[i + 1]

    # Generate identical unconstrained target weights from production engine
    target_w, _ = engine.generate_target_portfolio(
        df=df,
        target_grp=grp,
        max_bull_lev=STRATEGY_CONFIG.portfolio.max_bull_leverage,
        s0_short_mult=STRATEGY_CONFIG.portfolio.s0_short_multiplier,
        carry_lev=STRATEGY_CONFIG.portfolio.target_carry_leverage,
        top_k=STRATEGY_CONFIG.portfolio.top_k_conviction,
        retrain_step=STRATEGY_CONFIG.regime_model.retrain_step_bars
    )
    if not target_w:
        continue

    cur_panel = df.filter(pl.col("group_id") == grp)
    next_panel = df.filter(pl.col("group_id") == next_grp)

    returns_map = dict(zip(next_panel["symbol"].to_list(), next_panel["ret_4h"].to_list()))
    vols_map = dict(zip(cur_panel["symbol"].to_list(), cur_panel["vol_yang_zhang"].to_list()))

    # --- Variant A: Baseline Direct Execution ---
    all_syms_base = set(prev_w_base.keys()).union(target_w.keys())
    to_base = sum(abs(target_w.get(s, 0.0) - prev_w_base.get(s, 0.0)) for s in all_syms_base)
    turnover_base += to_base
    pnl_base = sum(target_w.get(s, 0.0) * returns_map.get(s, 0.0) for s in target_w) - (to_base * fee_rate)
    nav_base *= (1.0 + pnl_base)
    returns_base.append(pnl_base)
    prev_w_base = target_w

    # --- Variant B: Baseline + Leland Cubic-Root Deadband ---
    all_syms_leland = set(prev_w_leland.keys()).union(target_w.keys())
    dispatched_leland = {}

    for s in all_syms_leland:
        w_t = target_w.get(s, 0.0)
        w_prev = prev_w_leland.get(s, 0.0)
        sigma = max(0.015, vols_map.get(s, 0.025))

        # Leland cubic-root deadband half-width
        h_star = np.clip(((4.0 / 3.0) * (fee_rate * (sigma ** 2.0)) / gamma_mvo) ** (1.0 / 3.0), 0.015, 0.050)

        delta = w_t - w_prev
        if abs(delta) > h_star:
            # Partial adjustment to outer band boundary
            dispatched_leland[s] = w_t - np.sign(delta) * h_star
        else:
            dispatched_leland[s] = w_prev

    # Clean zero dust
    dispatched_leland = {s: w for s, w in dispatched_leland.items() if abs(w) > 0.005}

    to_leland = sum(abs(dispatched_leland.get(s, 0.0) - prev_w_leland.get(s, 0.0)) for s in all_syms_leland)
    turnover_leland += to_leland
    pnl_leland = sum(dispatched_leland.get(s, 0.0) * returns_map.get(s, 0.0) for s in dispatched_leland) - (to_leland * fee_rate)
    nav_leland *= (1.0 + pnl_leland)
    returns_leland.append(pnl_leland)
    prev_w_leland = dispatched_leland

# Performance Metrics
bars_per_year = 6 * 365
rets_a = np.array(returns_base)
rets_b = np.array(returns_leland)

cagr_a = (nav_base / 10_000.0) ** (bars_per_year / len(rets_a)) - 1.0
cagr_b = (nav_leland / 10_000.0) ** (bars_per_year / len(rets_b)) - 1.0

sharpe_a = np.mean(rets_a) / (np.std(rets_a) + 1e-6) * np.sqrt(bars_per_year)
sharpe_b = np.mean(rets_b) / (np.std(rets_b) + 1e-6) * np.sqrt(bars_per_year)

def max_dd(r):
    cum = np.cumprod(1.0 + r)
    return np.min((cum - np.maximum.accumulate(cum)) / np.maximum.accumulate(cum))

print("\n" + "=" * 65)
print("                   A/B BENCHMARK RESULTS")
print("=" * 65)
print(f"{'Metric':<26} | {'Baseline (A)':<16} | {'Leland (B)':<16}")
print("-" * 65)
print(f"{'Net CAGR':<26} | {cagr_a * 100:>+15.2f}% | {cagr_b * 100:>+15.2f}%")
print(f"{'Net Sharpe Ratio':<26} | {sharpe_a:>16.2f} | {sharpe_b:>16.2f}")
print(f"{'Max Drawdown':<26} | {max_dd(rets_a) * 100:>15.2f}% | {max_dd(rets_b) * 100:>15.2f}%")
print(f"{'Total Turnover':<26} | {turnover_base:>15.1f}x | {turnover_leland:>15.1f}x")
print(f"{'Turnover per 4H Bar':<26} | {turnover_base / len(rets_a):>15.2f}x | {turnover_leland / len(rets_b):>15.2f}x")
turnover_reduc = (1.0 - turnover_leland / turnover_base) * 100
fee_saved = (turnover_base - turnover_leland) * fee_rate * 100
print("-" * 65)
print(f"• Turnover Reduction Achieved : {turnover_reduc:.1f}%  (Target: >= 35%)")
print(f"• Equity Saved from Fee Drag  : {fee_saved:+.2f}% of NAV")
print("=" * 65)
