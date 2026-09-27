#!/usr/bin/env python3
"""
Decoupled 72H Sovereign Finality Benchmark Test
Tests multi-cadence decoupling under canonical IronCore execution physics.
"""

import math
import sys
from pathlib import Path
import numpy as np
import polars as pl

PIPELINE_ROOT = Path(__file__).resolve().parents[1]
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from src.data.pit_universe_manager import PointInTimeUniverseManager
from src.backtesting.ironcore_engine import IronCoreEngine
from src.backtesting.ironcore_config import IronCoreConfig_v1
from src.alpha.fracdiff_orthogonal_engine import apply_fractional_differentiation, compute_multi_beta_residual_momentum
from src.signals.asym_fip import compute_asymmetric_fip_scores

DATA_LAKE_PATH = PIPELINE_ROOT / "data" / "lake" / "raw_candles_4h.parquet"
df = pl.read_parquet(DATA_LAKE_PATH)
_, symbols, market_data = PointInTimeUniverseManager.load_pit_market_matrices(
    df=df, eval_start_ts=1757016000000, eval_end_ts=1788552000000, benchmark_symbol="BTC"
)

close_mat = np.nan_to_num(market_data["close"].copy(), nan=0.0)
oracle_mat = np.nan_to_num(market_data["oracle"].copy(), nan=0.0)
volume_mat = np.nan_to_num(market_data["volume"].copy(), nan=0.0)
valid_mask = market_data["valid_price_mask"].copy() & (close_mat > 0.0)
n_bars, n_symbols = close_mat.shape
eval_start_idx = market_data["eval_start_idx"]

btc_idx = symbols.index("BTC")
eth_idx = symbols.index("ETH")

prev_close = np.roll(close_mat, 1, axis=0)
returns_mat = np.zeros_like(close_mat)
valid_step = (prev_close > 0.0) & (close_mat > 0.0)
returns_mat[valid_step] = (close_mat[valid_step] / prev_close[valid_step]) - 1.0
returns_mat = np.nan_to_num(returns_mat, nan=0.0)
returns_mat[0] = 0.0
predicted_funding = np.nan_to_num((close_mat - oracle_mat) / np.maximum(oracle_mat, 1e-6) + 0.000125, nan=0.0)

# Subbars
subbars = 4
sub_opens = np.zeros((n_bars, subbars, n_symbols))
sub_highs = np.zeros((n_bars, subbars, n_symbols))
sub_lows = np.zeros((n_bars, subbars, n_symbols))
sub_closes = np.zeros((n_bars, subbars, n_symbols))
sub_vols = np.zeros((n_bars, subbars, n_symbols))

rng = np.random.RandomState(42)
for t in range(n_bars):
    p_c = close_mat[t]
    p_prev = prev_close[t]
    bar_vol = volume_mat[t]
    sigma = np.clip(np.abs(returns_mat[t]) + 0.015, 0.005, 0.20)

    step_open = np.where(p_prev > 0, p_prev, p_c)
    step_open = np.where(step_open > 0, step_open, 100.0)
    target_close = np.where(p_c > 0, p_c, step_open)

    for s in range(subbars):
        sub_opens[t, s] = step_open
        drift = (target_close - step_open) / max(subbars - s, 1)
        noise = rng.randn(n_symbols) * (step_open * sigma * 0.15)
        step_close = np.maximum(step_open + drift + noise, 1e-4)
        sub_closes[t, s] = step_close

        sub_hi = np.maximum(step_open, step_close) + np.abs(rng.randn(n_symbols)) * (step_open * sigma * 0.10)
        sub_lo = np.maximum(np.minimum(step_open, step_close) - np.abs(rng.randn(n_symbols)) * (step_open * sigma * 0.10), 1e-4)
        sub_highs[t, s] = sub_hi
        sub_lows[t, s] = sub_lo
        sub_vols[t, s] = bar_vol / subbars
        step_open = step_close

subbar_dict = {
    "opens": sub_opens,
    "highs": sub_highs,
    "lows": sub_lows,
    "closes": sub_closes,
    "volumes": sub_vols,
}

# Alpha
print("--> Computing stationary fractional differentiation and asymmetric FIP...")
fd_series = apply_fractional_differentiation(close_mat, d=0.38, max_len=18)
fd_diff = fd_series - np.roll(fd_series, 1, axis=0)
fd_diff[0] = 0.0
btc_d = fd_diff[:, btc_idx]
eth_d = fd_diff[:, eth_idx]

f5_mom, res = compute_multi_beta_residual_momentum(fd_diff, btc_d, eth_d, valid_mask, lookback_h=18)
f_asym = compute_asymmetric_fip_scores(res, f5_mom, valid_mask, lookback=18)

config = IronCoreConfig_v1(
    maker_fee=0.00015,
    taker_fee=0.00045,
    base_maker_ratio=0.985,
    base_adverse_bps=0.00010,
    impact_coefficient=0.03,
    deadband=0.03,
    portfolio_deadband=0.08,
    rerisk_buffer_pct=0.02,
    fixed_slot_sizing=True,
    initial_capital=10000.0,
)
engine = IronCoreEngine(config=config)

# Decoupled 72H Macro Rebalance
print("--> Generating 72H decoupled macro allocation weights...")
w_72h = np.zeros((n_bars, n_symbols))
w_prev = np.zeros(n_symbols)
for t in range(eval_start_idx, n_bars):
    bar_idx = t - eval_start_idx
    if bar_idx % 18 == 0:
        s_t = f_asym[t]
        v_m = valid_mask[t]
        target_w = engine.compute_rank_hysteresis_weights(
            signal_scores=s_t,
            valid_mask_t=v_m,
            weights_prev=w_prev,
            entry_k=8,
            exit_k=14,
            target_gross_leverage=1.80,
            fixed_slot_sizing=True,
        )
        w_prev = target_w.copy()
    w_72h[t] = w_prev.copy()

eval_window = slice(eval_start_idx, n_bars - 1)
print("--> Simulating canonical execution under IronCore v2.4.0 physics...")
res = engine.simulate_canonical_execution(
    weights_matrix=w_72h[eval_window],
    returns_mat=returns_mat[eval_window],
    predicted_funding=predicted_funding[eval_window],
    volume_mat=volume_mat[eval_window],
    close_mat=close_mat[eval_window],
    subbar_data={k: v[eval_window] for k, v in subbar_dict.items()},
    sl_pct=0.035,
    tp_pct=0.070,
    enable_cooldown=True,
    cooldown_bars=1,
    portfolio_deadband=0.03,
    governor_tiers=config.drawdown_tiers,
    initial_capital=10000.0,
)

end_eq = res["ending_equity"]
cagr = res["cagr"]
mdd = res["max_dd"]
sharpe = res["sharpe"]
to_mult = res["turnover_multiple"]
trades = res["trades_count"]
drift = res["max_mtm_drift"]

print("\n" + "=" * 80)
print("             DECOUPLED 72H BENCHMARK AUDIT SCOREBOARD")
print("=" * 80)
print(f"Ending Equity      : ${end_eq:,.2f} ({end_eq/10000.0:.2f}x)")
print(f"Annualized Net CAGR: {cagr:+.2f}%")
print(f"Maximum Drawdown   : {mdd:.2f}% (Ceiling <= 20.0%)")
print(f"Calmar Ratio       : {cagr/max(mdd, 0.01):.2f}")
print(f"Sharpe Ratio       : {sharpe:.2f}")
print(f"Turnover Multiple  : {to_mult:.2f}x (Annual Churn: {to_mult/(len(w_72h[eval_window])/2190.0):.2f}x)")
print(f"Trades Executed    : {trades}")
print(f"Max MTM Drift      : {drift:.14f}")
print("=" * 80)
