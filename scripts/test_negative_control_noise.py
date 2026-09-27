"""
IRONCORE NEGATIVE CONTROL: PURE NOISE STREAM COMPANION
======================================================
Companion negative control for IronCore verification.
Generates an uninformative pure Gaussian noise signal (Rank IC = 0.000)
and confirms that IronCore decisively REJECTS it across the gates:
- Gate 2 (Placebo Rejection): FAILS (p > 0.01)
- Gate 3 (Friction Efficiency): FAILS (churn eats gross)
- Gate 4 (Net EV vs Cash): FAILS (loses money to fees/impact)
- Gate 7 (Deflated Sharpe Ratio): FAILS (DSR ~ 0.00)

Run via:
    python3 scripts/test_negative_control_noise.py
"""

import sys
import math
from pathlib import Path

import numpy as np
import polars as pl
from scipy import stats

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from backtest_10x_convex_compounding import (
    DATA_LAKE_PATH, BENCHMARK_SYMBOL, EVAL_START_TS, EVAL_END_TS
)
from src.data.pit_universe_manager import PointInTimeUniverseManager
from src.backtesting.ironcore_config import IronCoreConfig_v1
from src.backtesting.ironcore_engine import IronCoreEngine


def main():
    # 1. Load Market Matrices from Point-In-Time Universe Manager
    df = pl.read_parquet(DATA_LAKE_PATH)
    _, symbols, market_data = PointInTimeUniverseManager.load_pit_market_matrices(
        df=df, eval_start_ts=EVAL_START_TS, eval_end_ts=EVAL_END_TS, benchmark_symbol=BENCHMARK_SYMBOL
    )

    close_mat = market_data["close"].copy()
    oracle_mat = market_data["oracle"].copy()
    volume_mat = market_data["volume"].copy()
    valid_mask = market_data["valid_price_mask"]
    eval_start_idx = market_data.get("eval_start_idx", 35)
    n_bars, n_symbols = close_mat.shape

    print("=" * 130)
    print("   IRONCORE MASTER BACKTESTER: NEGATIVE CONTROL PURE NOISE EVALUATION")
    print(f"   Hyperliquid L1 4H Lake | {n_bars} Total Bars ({n_bars - eval_start_idx} Post-Warmup Eval Bars) | {n_symbols} Assets | MTM Drift < 1e-8")
    print("=" * 130)

    # Forward fill prices for inactive assets
    for col in range(n_symbols):
        mask = valid_mask[:, col]
        if np.any(mask):
            first_idx = np.where(mask)[0][0]
            for r in range(first_idx + 1, n_bars):
                if not mask[r]:
                    close_mat[r, col] = close_mat[r-1, col]
                    oracle_mat[r, col] = oracle_mat[r-1, col]
                    volume_mat[r, col] = 0.0
        else:
            close_mat[:, col] = 1.0; oracle_mat[:, col] = 1.0; volume_mat[:, col] = 0.0

    btc_idx = symbols.index(BENCHMARK_SYMBOL) if BENCHMARK_SYMBOL in symbols else 0
    btc_prices = close_mat[:, btc_idx]
    prev_close = np.roll(close_mat, 1, axis=0)
    returns_mat = np.nan_to_num(np.where(prev_close > 0, (close_mat / prev_close) - 1.0, 0.0))
    predicted_funding = (close_mat - oracle_mat) / (oracle_mat + 1e-8) + 0.000125

    holding_bars = 6
    valid_future = valid_mask & np.roll(valid_mask, -holding_bars, axis=0)
    valid_future[-holding_bars:] = False

    # 2. Pure Gaussian Noise (Zero Information Content)
    np.random.seed(999)
    noise_signal = np.where(valid_future, np.random.normal(0.0, 1.0, size=returns_mat.shape), np.nan)

    # Calculate actual realized Rank IC
    fwd_returns = np.zeros_like(returns_mat)
    for t in range(n_bars - holding_bars):
        fwd_returns[t] = np.where(valid_future[t], (close_mat[t + holding_bars] / (close_mat[t] + 1e-12)) - 1.0, 0.0)

    rank_ics = []
    for t in range(0, n_bars - holding_bars, holding_bars):
        avail = np.where(valid_future[t])[0]
        if len(avail) >= 16:
            ic = stats.spearmanr(noise_signal[t, avail], fwd_returns[t, avail], nan_policy="omit").statistic
            if not np.isnan(ic):
                rank_ics.append(ic)
    mean_ic = float(np.mean(rank_ics))
    std_ic = float(np.std(rank_ics))
    print(f"\n[REALIZED SIGNAL STATS] Mean Rank IC: {mean_ic:+.4f} | Std IC: {std_ic:.4f} | Annualized ICIR: {mean_ic/std_ic*math.sqrt(365.25):.2f}")

    # 3. Construct Dollar-Neutral Target Portfolio Weights
    print("\n[2/3] Constructing Dollar-Neutral Weights (Top 8 Long / Top 8 Short)...")
    cfg = IronCoreConfig_v1(mc_placebo_draws=250, bootstrap_paths=1_000)
    engine = IronCoreEngine(config=cfg)

    weights_noise = np.zeros((n_bars, n_symbols))
    for t in range(0, n_bars, holding_bars):
        w_t = engine.seeded_rank_weights(
            signal_scores=np.nan_to_num(noise_signal[t], nan=0.0),
            valid_mask_t=valid_future[t],
            top_k=8,
            target_gross_leverage=1.0,
            seed=t
        )
        for s in range(holding_bars):
            if t + s < n_bars:
                weights_noise[t + s] = w_t

    # 4. Run Complete 7-Gate IronCore Certification Gauntlet
    print(f"[3/3] Executing 7-Gate IronCore Certification Gauntlet ({cfg.mc_placebo_draws} MC Draws)...")
    results = engine.run_full_certification_gauntlet(
        candidate_name="Negative_Control_Pure_Noise",
        weights_matrix=weights_noise,
        signal_matrix=noise_signal,
        returns_mat=returns_mat,
        predicted_funding=predicted_funding,
        volume_mat=volume_mat,
        close_mat=close_mat,
        oracle_mat=oracle_mat,
        valid_mask=valid_mask,
        btc_prices=btc_prices
    )

    perf = results["performance"]
    dsr = results["dsr_metrics"]
    ruin = results["ruin_analysis"]
    perm = results["placebos"]["asset_permutation"]
    horizon = results["placebos"]["horizon_matched_random"]

    print("\n" + "=" * 130)
    print("                      IRONCORE AUDIT REPORT: NEGATIVE CONTROL (PURE NOISE)")
    print("=" * 130)
    print(f"Overall Gauntlet Verdict   : {results['overall_verdict']}")
    print(f"Annualized Net CAGR        : {perf['cagr']:+.2f}%")
    print(f"Realized Sharpe Ratio      : {perf['sharpe']:.2f}")
    print(f"Maximum Peak-to-Trough DD  : {perf['max_dd']:.2f}%")
    print(f"Annual Portfolio Turnover  : {perf['turnover']:.1f}x")
    print(f"Total Friction Paid        : ${perf['total_friction']:,.2f}")
    print(f"Friction / Gross PnL Ratio : {perf['fric_ratio']:.2f}% (Threshold <= 25.0%)")
    print("-" * 130)
    print(f"Realized Mean Rank IC      : {mean_ic:+.4f} (Annualized ICIR = {mean_ic/std_ic*math.sqrt(365.25):.2f})")
    print(f"Asset Permutation p-value  : {perm['empirical_p_value']:.4f} (Required < 0.0100, N={cfg.mc_placebo_draws})")
    print(f"Random Noise p-value       : {horizon['empirical_p_value']:.4f} (Required < 0.0100, N={cfg.mc_placebo_draws})")
    print(f"Deflated Sharpe Ratio (DSR): {dsr['deflated_sharpe_ratio']:.4f} (Required >= 0.9500)")
    print(f"Stationary Ruin Prob P(50%): {ruin['ruin_probability']:.4f} (Required <= 0.0500)")
    print("-" * 130)
    print("Gate-by-Gate Verification Status:")
    for gate_name, passed in results["gates"].items():
        status = "PASSED [OK]" if passed else "FAILED [X]"
        print(f"  {gate_name:<50} : {status}")
    print("=" * 130)

    assert results["overall_verdict"] == "KILLED", "Negative pure noise control must be KILLED by IronCore!"
    print("\n>>> Negative Control companion successfully verified: KILLED as expected.")


if __name__ == "__main__":
    main()
