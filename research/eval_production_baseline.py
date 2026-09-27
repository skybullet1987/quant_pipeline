import sys
from pathlib import Path
import numpy as np
import polars as pl

sys.path.insert(0, str(Path.home() / "quant_pipeline"))
from src.signals.multiscale_alpha_engine import ProductionMultiScaleEngine
from src.config import STRATEGY_CONFIG

print("=" * 65)
print("   OFFLINE LAB: TRUE PRODUCTION BASELINE WALK-FORWARD")
print("=" * 65)

lake_path = Path.home() / "quant_pipeline" / "data" / "lake" / "features" / "pit_panel_4h.parquet"
df = pl.read_parquet(lake_path)

if "group_id" not in df.columns:
    unique_ts = df.select("timestamp_ms").unique().sort("timestamp_ms").with_columns(
        pl.int_range(0, pl.len()).alias("group_id")
    )
    df = df.join(unique_ts, on="timestamp_ms", how="left")

# Instantiate and let it auto-bind the production models
engine = ProductionMultiScaleEngine()
_, _ = engine.compute_live_targets(lake_file=lake_path)
print(f"[+] Successfully loaded production Tri-Horizon models:")
print(f"    • m12  : {engine.m12.tree_count_} trees")
print(f"    • m48  : {engine.m48.tree_count_} trees")
print(f"    • m168 : {engine.m168.tree_count_} trees")

all_groups = sorted(df.select("group_id").unique().to_series().to_list())
# Benchmark over the trailing 180 bars (~30 days) of out-of-sample data
test_groups = [g for g in all_groups if g >= (all_groups[-1] - 180)]
print(f"[+] Benchmarking across {len(test_groups)} 4H bars (groups {test_groups[0]} to {test_groups[-1]})...")

fee_rate = 0.00035  # 3.5 bps maker fee + half-spread slippage
nav = 10_000.0
turnover_total = 0.0
prev_weights = {}
period_returns = []
active_counts = []
leverage_series = []

for i, grp in enumerate(test_groups[:-1]):
    next_grp = test_groups[i + 1]
    
    # 1. Evaluate baseline production target portfolio
    weights, diag = engine.generate_target_portfolio(
        df=df,
        target_grp=grp,
        max_bull_lev=STRATEGY_CONFIG.portfolio.max_bull_leverage,
        s0_short_mult=STRATEGY_CONFIG.portfolio.s0_short_multiplier,
        carry_lev=STRATEGY_CONFIG.portfolio.target_carry_leverage,
        top_k=STRATEGY_CONFIG.portfolio.top_k_conviction,
        retrain_step=STRATEGY_CONFIG.regime_model.retrain_step_bars
    )
    if not weights:
        continue

    # 2. Extract realized returns over [t, t+1]
    next_panel = df.filter(pl.col("group_id") == next_grp)
    returns_map = dict(zip(next_panel["symbol"].to_list(), next_panel["ret_4h"].to_list()))

    # 3. Compute turnover and fee drag
    all_syms = set(prev_weights.keys()).union(weights.keys())
    turnover = sum(abs(weights.get(s, 0.0) - prev_weights.get(s, 0.0)) for s in all_syms)
    turnover_total += turnover
    cost = turnover * fee_rate

    # 4. Period net PnL
    gross_pnl = sum(weights.get(s, 0.0) * returns_map.get(s, 0.0) for s in weights)
    net_pnl = gross_pnl - cost
    nav *= (1.0 + net_pnl)
    period_returns.append(net_pnl)
    active_counts.append(len(weights))
    leverage_series.append(sum(abs(w) for w in weights.values()))
    prev_weights = weights

# Performance Summary
bars_per_year = 6 * 365
rets = np.array(period_returns)
cagr = (nav / 10_000.0) ** (bars_per_year / max(1, len(rets))) - 1.0
sharpe = np.mean(rets) / (np.std(rets) + 1e-6) * np.sqrt(bars_per_year)

cum = np.cumprod(1.0 + rets)
peak = np.maximum.accumulate(cum)
mdd = np.min((cum - peak) / peak)

print("\n" + "=" * 65)
print("             TRUE PRODUCTION BASELINE BENCHMARK")
print("=" * 65)
print(f"• Evaluated 4H Periods        : {len(rets)}")
print(f"• Baseline Net CAGR           : {cagr * 100:+.2f}%")
print(f"• Baseline Net Sharpe Ratio   : {sharpe:.2f}")
print(f"• Baseline Max Drawdown       : {mdd * 100:.2f}%")
print(f"• Mean Realized Leverage      : {np.mean(leverage_series):.2f}x")
print(f"• Mean Active Basket Breadth  : {np.mean(active_counts):.1f} coins")
print(f"• Cumulative Turnover         : {turnover_total:,.1f}x NAV")
print(f"• Mean Turnover per 4H Bar    : {turnover_total / max(1, len(rets)):.2f}x NAV")
print("=" * 65)
