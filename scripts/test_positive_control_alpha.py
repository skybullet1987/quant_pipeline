"""
IRONCORE POSITIVE CONTROL: GROUND-TRUTH SYNTHETIC ALPHA STREAM
==============================================================
Demonstrates how IronCore validates a genuine positive-EV predictive alpha stream.

Mechanics:
1. Calculates forward 6-bar (24H) returns across continuously listed assets.
2. Injects Gaussian noise to tune predictive Information Coefficient (IC).
3. Allocates dollar-neutral long/short weights (Top 8 longs, Top 8 shorts).
4. Evaluates against all 7 IronCore adversarial gates:
   - Gate 1: Pre-flight Invariants & Zero-Variance checks
   - Gate 2: Monte Carlo Placebo battery (Asset Permutation & Noise, p < 0.01)
   - Gate 3: Friction & Turnover efficiency (Friction <= 25% of gross)
   - Gate 4: Net Executable EV vs Idle Cash
   - Gate 5: Cross-Regime Survivability (Bull, Chop, Bear Sharpe > -1.0)
   - Gate 6: Non-Parametric Stationary Block-Bootstrap Ruin Probability (<= 5%)
   - Gate 7: Deflated Sharpe Ratio (Bailey & Lopez de Prado, DSR >= 95%)

Run via:
    python3 scripts/test_positive_control_alpha.py
"""

import sys
import math
from pathlib import Path

import numpy as np
import polars as pl

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from backtest_10x_convex_compounding import (
    DATA_LAKE_PATH, BENCHMARK_SYMBOL, EVAL_START_TS, EVAL_END_TS
)
from src.data.pit_universe_manager import PointInTimeUniverseManager
from src.backtesting.ironcore_config import IronCoreConfig_v1
from src.backtesting.ironcore_engine import IronCoreEngine


def generate_positive_control_stream(
    close_mat: np.ndarray,
    valid_mask: np.ndarray,
    returns_mat: np.ndarray,
    holding_bars: int = 6,
    noise_sigma: float = 0.14,
    random_seed: int = 42
) -> np.ndarray:
    """
    Constructs a synthetic predictive alpha signal with known positive forward EV.
    
    CRITICAL REALISM CHECKS:
    - Enforces continuous PIT validity between bar t and bar t + holding_bars.
    - Masks out any unlisted, delisted, or zero-variance assets.
    - Injects controlled noise (noise_sigma) so the signal possesses realistic
      predictive rank correlation (IC ~ 0.15 - 0.25) rather than clairvoyant 100% foresight.
    """
    n_bars, n_symbols = close_mat.shape
    
    # 1. Point-In-Time Continuity Mask: asset must be continuously tradable across the holding horizon
    valid_future = valid_mask & np.roll(valid_mask, -holding_bars, axis=0)
    valid_future[-holding_bars:] = False  # Zero out edge at dataset end

    # 2. Forward Return Calculation: R_{t, t+k} = P_{t+k} / P_t - 1
    fwd_returns = np.zeros_like(returns_mat)
    for t in range(n_bars - holding_bars):
        fwd_returns[t] = np.where(
            valid_future[t],
            (close_mat[t + holding_bars] / (close_mat[t] + 1e-12)) - 1.0,
            0.0
        )

    # 3. Add Gaussian Noise to emulate realistic estimation uncertainty
    np.random.seed(random_seed)
    noise = np.random.normal(0.0, noise_sigma, size=returns_mat.shape)
    
    # Unlisted or invalid assets are set to -999.0 so rank sorting places them out of reach
    synth_signal = np.where(valid_future, fwd_returns + noise, -999.0)
    
    return synth_signal, valid_future


def compute_realized_rank_ic(
    signal_matrix: np.ndarray,
    forward_returns: np.ndarray,
    valid_mask: np.ndarray,
    holding_bars: int = 6
) -> dict:
    """Computes empirical Spearman rank Information Coefficient across rebalance bars."""
    from scipy import stats
    n_bars = signal_matrix.shape[0]
    rank_ics = []
    
    for t in range(0, n_bars - holding_bars, holding_bars):
        avail = np.where(valid_mask[t])[0]
        if len(avail) >= 16:
            sig_t = signal_matrix[t, avail]
            ret_t = forward_returns[t, avail]
            if not np.all(np.isnan(sig_t)) and not np.all(np.isnan(ret_t)):
                ic = stats.spearmanr(sig_t, ret_t, nan_policy="omit").statistic
                if not np.isnan(ic):
                    rank_ics.append(ic)
                    
    ics_arr = np.array(rank_ics)
    mean_ic = float(np.mean(ics_arr)) if len(ics_arr) > 0 else 0.0
    std_ic = float(np.std(ics_arr)) if len(ics_arr) > 0 else 1.0
    icir = float((mean_ic / max(std_ic, 1e-6)) * math.sqrt(365.25 * 6 / holding_bars))
    
    return {
        "mean_rank_ic": mean_ic,
        "std_rank_ic": std_ic,
        "annualized_icir": icir,
        "eval_rebalances": len(ics_arr)
    }


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
    print("   IRONCORE MASTER BACKTESTER: POSITIVE CONTROL SYNTHETIC ALPHA EVALUATION")
    print(f"   Hyperliquid L1 4H Lake | {n_bars} Total Bars ({n_bars - eval_start_idx} Post-Warmup Eval Bars) | {n_symbols} Assets | MTM Drift < 1e-8")
    print("=" * 130)

    # Forward fill prices for inactive assets to prevent zero-division in returns
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
            close_mat[:, col] = 1.0
            oracle_mat[:, col] = 1.0
            volume_mat[:, col] = 0.0

    btc_idx = symbols.index(BENCHMARK_SYMBOL) if BENCHMARK_SYMBOL in symbols else 0
    btc_prices = close_mat[:, btc_idx]
    prev_close = np.roll(close_mat, 1, axis=0)
    returns_mat = np.nan_to_num(np.where(prev_close > 0, (close_mat / prev_close) - 1.0, 0.0))
    predicted_funding = (close_mat - oracle_mat) / (oracle_mat + 1e-8) + 0.000125

    # 2. Generate Synthetic Alpha Stream (Realistic production IC ~ 0.037 vs Strong IC ~ 0.21)
    holding_bars = 6
    # Calculate pure forward returns
    valid_future = valid_mask & np.roll(valid_mask, -holding_bars, axis=0)
    valid_future[-holding_bars:] = False

    fwd_returns = np.zeros_like(returns_mat)
    for t in range(n_bars - holding_bars):
        fwd_returns[t] = np.where(
            valid_future[t],
            (close_mat[t + holding_bars] / (close_mat[t] + 1e-12)) - 1.0,
            0.0
        )

    # Strong positive control (noise sigma = 0.14)
    np.random.seed(42)
    noise = np.random.normal(0.0, 0.14, size=returns_mat.shape)
    synth_signal = np.where(valid_future, fwd_returns + noise, np.nan)

    # Compute realized Rank IC
    ic_stats = compute_realized_rank_ic(synth_signal, fwd_returns, valid_future, holding_bars)
    print(f"\n[REALIZED SIGNAL STATS] Mean Rank IC: {ic_stats['mean_rank_ic']:.4f} | Std IC: {ic_stats['std_rank_ic']:.4f} | Annualized ICIR: {ic_stats['annualized_icir']:.2f}")

    # 3. Construct Dollar-Neutral Target Portfolio Weights
    print("\n[2/3] Constructing Dollar-Neutral Weights (Top 8 Long / Top 8 Short)...")
    cfg = IronCoreConfig_v1(mc_placebo_draws=250, bootstrap_paths=1_000)
    engine = IronCoreEngine(config=cfg)

    weights_positive = np.zeros((n_bars, n_symbols))
    for t in range(0, n_bars, holding_bars):
        w_t = engine.seeded_rank_weights(
            signal_scores=np.nan_to_num(synth_signal[t], nan=0.0),
            valid_mask_t=valid_future[t],
            top_k=8,
            target_gross_leverage=1.0,
            seed=t
        )
        for s in range(holding_bars):
            if t + s < n_bars:
                weights_positive[t + s] = w_t

    # 4. Run Complete 7-Gate IronCore Certification Gauntlet
    print(f"[3/3] Executing 7-Gate IronCore Certification Gauntlet ({cfg.mc_placebo_draws} MC Draws)...")
    results = engine.run_full_certification_gauntlet(
        candidate_name="Positive_Control_Synthetic_Alpha",
        weights_matrix=weights_positive,
        signal_matrix=synth_signal,
        returns_mat=returns_mat,
        predicted_funding=predicted_funding,
        volume_mat=volume_mat,
        close_mat=close_mat,
        oracle_mat=oracle_mat,
        valid_mask=valid_mask,
        btc_prices=btc_prices
    )

    # 5. Display Comprehensive Audit Report
    perf = results["performance"]
    dsr = results["dsr_metrics"]
    ruin = results["ruin_analysis"]
    perm = results["placebos"]["asset_permutation"]
    horizon = results["placebos"]["horizon_matched_random"]

    print("\n" + "=" * 130)
    print("                      IRONCORE AUDIT REPORT: POSITIVE CONTROL")
    print("=" * 130)
    print(f"Overall Gauntlet Verdict   : {results['overall_verdict']}")
    print(f"Annualized Net CAGR        : {perf['cagr']:+.2f}%")
    print(f"Realized Sharpe Ratio      : {perf['sharpe']:.2f}")
    print(f"Maximum Peak-to-Trough DD  : {perf['max_dd']:.2f}%")
    print(f"Win Rate (Per Bar)         : {perf['win_rate']:.2f}%")
    print(f"Annual Portfolio Turnover  : {perf['turnover']:.1f}x")
    print(f"Total Fees Paid (60/40)    : ${perf['fees']:,.2f}")
    print(f"Square-Root Market Impact  : ${perf['market_impact']:,.2f}")
    print(f"Friction / Gross PnL Ratio : {perf['fric_ratio']:.2f}% (Threshold <= 25.0%)")
    print(f"Max MTM Drift Observed     : ${perf['max_mtm_drift']:.10f} (Tolerance < 1e-8)")
    print("-" * 130)
    print(f"Realized Mean Rank IC      : {ic_stats['mean_rank_ic']:.4f} (Annualized ICIR = {ic_stats['annualized_icir']:.2f})")
    print(f"Asset Permutation p-value  : {perm['empirical_p_value']:.4f} (Required < 0.0100, N={cfg.mc_placebo_draws})")
    print(f"Random Noise p-value       : {horizon['empirical_p_value']:.4f} (Required < 0.0100, N={cfg.mc_placebo_draws})")
    print(f"Deflated Sharpe Ratio (DSR): {dsr['deflated_sharpe_ratio']:.4f} (Required >= 0.9500)")
    print(f"Stationary Ruin Prob P(50%): {ruin['ruin_probability']:.4f} (Required <= 0.0500)")
    print(f"Extreme P99 Drawdown       : {ruin['p99_max_dd']:.2f}%")
    print("-" * 130)
    print("Macro Regime Breakdown:")
    for reg_name, reg_stat in results["regimes"].items():
        print(f"  - {reg_name:<12}: Sharpe = {reg_stat['sharpe']:>6.2f} | Net CAGR = {reg_stat['cagr']:>+8.1f}% | Win Rate = {reg_stat['win_rate']:>5.1f}% | Bars = {reg_stat['n_bars']}")
    print("-" * 130)
    print("Gate-by-Gate Verification Status:")
    for gate_name, passed in results["gates"].items():
        status = "PASSED [OK]" if passed else "FAILED [X]"
        print(f"  {gate_name:<50} : {status}")
    print("=" * 130)

    assert results["overall_verdict"] == "PASSED", "Positive control must pass all IronCore gates!"
    print("\n>>> Positive Control verification successfully completed. All gates certified.")

    # Sanity check assertion
    assert results["overall_verdict"] == "PASSED", "Positive control must pass all IronCore gates!"
    print("\n>>> Positive Control verification successfully completed. All gates certified.")


if __name__ == "__main__":
    main()
