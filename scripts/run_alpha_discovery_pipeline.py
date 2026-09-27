#!/usr/bin/env python3
"""
INSTITUTIONAL ALPHA DISCOVERY PIPELINE RUNNER (v9.7)
====================================================
Runs the standalone Alpha Research Engine across the curated canonical starter alphas:
1. Validates Rule 13 Information Availability Contract strictly:
   feature_window_start < feature_window_end <= feature_available_at <= decision_timestamp < execution_timestamp
2. Tracks formal FactorMetadata lineage (id, version, formula, lag, hypothesis).
3. Evaluates canonical 4H horizons: h in [1, 2, 4, 8, 18, 36] (4h, 8h, 16h, 32h, 72h, 144h).
4. Computes cross-sectional Rank IC, ICIR, HAC Newey-West t-stat, Block Bootstrap 95% CI, and Decile Sorts.
5. Performs Factor Neutralization against BTC beta, volatility, and liquidity.
6. Evaluates Nested Incremental Alpha with Primary (Delta OOS RankIC, Delta Spread, Delta R^2)
   and Secondary (Delta ICIR, Delta Sharpe) metrics.
7. Produces institutional Standardized Factor Scorecards.
"""

import sys
import math
from pathlib import Path
import numpy as np
import polars as pl

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PIPELINE_ROOT))

from src.data.pit_universe_manager import PointInTimeUniverseManager
from src.alpha.research_engine import AlphaResearchEngine, CANONICAL_4H_HORIZONS, InformationAvailabilityContract
from src.alpha.neutralization import FactorNeutralizer
from src.alpha.orthogonality import OrthogonalityEngine
from src.alpha.factor_library import FactorLibrary, FactorMetadata

DATA_LAKE_PATH = PIPELINE_ROOT / "data" / "lake" / "raw_candles_4h.parquet"
EVAL_START_TS = 1757016000000  # 2025-09-04 20:00:00 UTC
EVAL_END_TS = 1788552000000    # 2026-09-04 20:00:00 UTC


def run_alpha_discovery():
    print("=" * 105)
    print("        INSTITUTIONAL ALPHA DISCOVERY ENGINE & STANDARDIZED SCORECARD PIPELINE (v9.7)       ")
    print("=" * 105)

    print("--> Loading PIT market matrices from raw data lake...")
    df = pl.read_parquet(DATA_LAKE_PATH)
    eval_timestamps, symbols, market_data = PointInTimeUniverseManager.load_pit_market_matrices(
        df=df,
        eval_start_ts=EVAL_START_TS,
        eval_end_ts=EVAL_END_TS,
        benchmark_symbol="BTC",
    )
    print(f"    Loaded {len(eval_timestamps)} evaluation bars across {len(symbols)} PIT assets.")

    close_mat = market_data["close"]
    open_mat = market_data["open"]
    high_mat = market_data["high"]
    low_mat = market_data["low"]
    volume_mat = market_data["volume"]
    oracle_mat = market_data["oracle"]
    valid_mask = market_data["valid_price_mask"]

    # 1. Initialize Alpha Research Engine with canonical 4H horizons
    canonical_h = list(CANONICAL_4H_HORIZONS.keys())
    print(f"\n--> Initializing Standalone Alpha Research Engine with Canonical 4H Horizons:")
    print(f"    Horizons: {', '.join([f'h={k} ({v})' for k, v in CANONICAL_4H_HORIZONS.items()])}")
    
    engine = AlphaResearchEngine(
        close_mat=close_mat,
        valid_mask=valid_mask,
        symbols=symbols,
        timestamps=eval_timestamps,
        default_horizons=canonical_h,
    )

    # 2. Factor Library & Lineage Metadata (Initial 4 Canonical Starter Alphas)
    print("\n--> Initializing Curated Factor Library & Lineage Metadata (4 Starter Alphas)...")
    factor_lib = FactorLibrary(
        close_mat=close_mat,
        open_mat=open_mat,
        high_mat=high_mat,
        low_mat=low_mat,
        volume_mat=volume_mat,
        oracle_mat=oracle_mat,
        valid_mask=valid_mask,
        symbols=symbols,
        benchmark_symbol="BTC",
    )
    starter_factors = factor_lib.get_starter_factors()

    # Verify Rule 13 Information Availability Contract
    print("\n--> Auditing Rule 13 Information Availability Contract across Starter Alphas...")
    for f_name in starter_factors.keys():
        meta = factor_lib.get_metadata(f_name)
        assert meta is not None, f"Missing metadata for {f_name}"
        # Sample timestamp check at bar index 100
        sample_bar_close = eval_timestamps[100]
        window_start = eval_timestamps[100 - meta.lookback_bars]
        available_at = sample_bar_close + meta.availability_lag_ms
        decision_ts = sample_bar_close + 1_000  # 1s after close
        exec_ts = eval_timestamps[101]          # next bar open execution

        contract = InformationAvailabilityContract(
            factor_timestamp=sample_bar_close,
            feature_window_start=window_start,
            feature_window_end=sample_bar_close,
            feature_available_at=available_at,
            decision_timestamp=decision_ts,
            execution_timestamp=exec_ts,
        )
        assert contract.validate(), f"Contract violation for {f_name}"
        print(f"    [PASSED] {meta.factor_id} (v{meta.version}): lag={meta.availability_lag_ms}ms, lookback={meta.lookback_bars} bars.")

    # 3. Factor Neutralization Engine
    print("\n--> Initializing Cross-Sectional Factor Neutralizer (Nuisance: BTC Beta, Volatility, Liquidity)...")
    neutralizer = FactorNeutralizer(
        close_mat=close_mat,
        volume_mat=volume_mat,
        oracle_mat=oracle_mat,
        valid_mask=valid_mask,
        symbols=symbols,
        benchmark_symbol="BTC",
    )

    # 4. Orthogonality & Scorecard Engine
    print("--> Initializing Orthogonality & Incremental Alpha Engine...")
    ortho_engine = OrthogonalityEngine(
        close_mat=close_mat,
        valid_mask=valid_mask,
        symbols=symbols,
    )

    scorecards = []
    evaluated_diagnostics = {}
    neutralized_factors = {}

    fwd_ret_4 = engine.compute_forward_returns(4) # 16h benchmark

    print("\n" + "=" * 115)
    print(f"{'Factor Name':<22} | {'Raw IC':<7} | {'ICIR':<5} | {'HAC t':<6} | {'P(IC>0)':<7} | {'Δ OOS IC':<8} | {'Δ Spread':<8} | {'Δ R²':<6} | {'Stat':<4} | {'Econ':<4} | {'Verdict'}")
    print("-" * 115)

    for factor_name, f_mat in starter_factors.items():
        # Evaluate raw diagnostics at 16h benchmark (4 bars)
        diag = engine.evaluate_factor(
            factor_name=factor_name,
            factor_mat=f_mat,
            target_horizon=4, # 16H benchmark
            run_placebo=True,
        )
        evaluated_diagnostics[factor_name] = diag

        # Neutralize factor against BTC beta, volatility, and liquidity
        f_neut = neutralizer.neutralize_factor(
            raw_factor_mat=f_mat,
            nuisance_list=["btc_beta", "volatility", "liquidity"],
        )
        neutralized_factors[factor_name] = f_neut

        # Evaluate neutralized Rank IC
        diag_neut = engine.evaluate_factor(
            factor_name=f"{factor_name}_neut",
            factor_mat=f_neut,
            target_horizon=4,
            run_placebo=False,
        )
        neutralized_ic = diag_neut.mean_ic

        # Incremental alpha test (Primary: Delta OOS Rank IC, Delta Spread, Delta R^2)
        existing_sub = {k: neutralized_factors[k] for k in list(neutralized_factors.keys())[:-1]}
        inc_res = ortho_engine.evaluate_incremental_alpha(
            existing_factor_dict=existing_sub,
            candidate_name=factor_name,
            candidate_mat=f_neut,
            forward_returns=fwd_ret_4,
        )

        capacity = ortho_engine.estimate_capacity(diag.mean_ic)
        card = ortho_engine.generate_scorecard(
            factor_name=factor_name,
            raw_diagnostics=diag,
            neutralized_ic=neutralized_ic,
            incremental_res=inc_res,
            capacity_dict=capacity,
        )
        scorecards.append(card)

        print(
            f"{factor_name:<22} | {diag.mean_ic:+7.4f} | {diag.icir:5.2f} | {diag.hac_t_stat:6.2f} | "
            f"{diag.pct_positive_ic*100:5.1f}%  | {inc_res.delta_oos_rank_ic:+8.4f} | {inc_res.delta_oos_spread*10000:+6.1f}bp | "
            f"{inc_res.delta_oos_r2*1000:5.2f}‰ | {card.statistical_grade:<4} | {card.economic_grade:<4} | {card.final_verdict}"
        )

    print("=" * 115)

    # Display Canonical 4H Decay Profiles
    print("\n--> Canonical 4H Horizon Decay Profiles (Spearman Rank IC):")
    horiz_labels = [CANONICAL_4H_HORIZONS[h] for h in canonical_h]
    decay_hdr = f"{'Factor Name':<24} " + " ".join([f"{lbl:>8}" for lbl in horiz_labels])
    print(decay_hdr)
    print("-" * len(decay_hdr))
    for factor_name, diag in evaluated_diagnostics.items():
        decay_vals = [f"{diag.decay_profile.get(h, 0.0):+8.4f}" for h in canonical_h]
        print(f"{factor_name:<24} " + " ".join(decay_vals))

    # Compute Cross-Factor Pairwise Correlation Matrix
    print("\n--> Cross-Factor Pairwise Spearman Rank Correlation Matrix:")
    corr_res = ortho_engine.compute_cross_factor_correlation(starter_factors)
    names = corr_res["factor_names"]
    mat = corr_res["correlation_matrix"]
    
    header = f"{'':<24} " + " ".join([f"{n[:6]:>8}" for n in names])
    print(header)
    for i, n in enumerate(names):
        row_str = f"{n:<24} " + " ".join([f"{mat[i, j]:+8.2f}" for j in range(len(names))])
        print(row_str)

    print("\n[SUCCESS] Alpha Discovery Pipeline (v9.7) completed cleanly.")


if __name__ == "__main__":
    run_alpha_discovery()
