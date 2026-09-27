"""
Tests for Research Protocol v1.0, Trial Registry, and Null Benchmark Suite.
"""

import pytest
import numpy as np
import tempfile
import os

from src.research.protocol_spec import (
    PnLDecomposition,
    ThreeStreamAttribution,
    PreregisteredPromotionGate,
)
from src.research.trial_registry import (
    ExperimentRecord,
    TrialRegistry,
)
from src.research.null_benchmark import (
    NullBenchmarkEvaluator,
    generate_permuted_weights,
)


def test_pnl_decomposition_exact_conservation():
    """
    Verifies that the 6-bucket PnL decomposition conserves exactly within 1e-6 tolerance.
    """
    # Exact ledger reconciliation:
    # Gross Price: 1500.0, Funding: -50.0, Fees: 120.0, Impact: 45.0, Adverse: 25.0, Slippage: 60.0
    # Net PnL = 1500 - 50 - 120 - 45 - 25 - 60 = 1200.0
    decomp = PnLDecomposition(
        delta_gross_price_pnl=1500.0,
        delta_funding_pnl=-50.0,
        delta_exchange_fees=120.0,
        delta_market_impact=45.0,
        delta_adverse_selection=25.0,
        delta_explicit_slippage=60.0,
        delta_net_pnl=1200.0,
    )

    assert decomp.is_conserved(1e-6)
    assert decomp.residual == pytest.approx(0.0, abs=1e-9)

    # Discrepancy test
    broken_decomp = PnLDecomposition(
        delta_gross_price_pnl=1500.0,
        delta_funding_pnl=-50.0,
        delta_exchange_fees=120.0,
        delta_market_impact=45.0,
        delta_adverse_selection=25.0,
        delta_explicit_slippage=60.0,
        delta_net_pnl=1300.0,  # 100.0 unaccounted drift
    )
    assert not broken_decomp.is_conserved(1e-6)
    assert broken_decomp.residual == pytest.approx(100.0, abs=1e-9)


def test_three_stream_newey_west_hac_t_stat():
    """
    Verifies 3-stream delta HAC paired t-statistic computation.
    """
    n = 200
    rng = np.random.RandomState(42)
    # Autocorrelated positive delta stream
    innovations = rng.normal(0.001, 0.01, size=n)
    delta = np.zeros(n)
    for t in range(1, n):
        delta[t] = 0.3 * delta[t-1] + innovations[t]

    exp_r = np.full(n, 0.002) + delta
    ctrl_r = np.full(n, 0.002)

    stream = ThreeStreamAttribution(
        exp_returns=exp_r,
        ctrl_returns=ctrl_r,
        delta_returns=delta,
    )

    t_stat = stream.compute_newey_west_t_stat(max_lag=5)
    assert t_stat > 0.0
    assert np.isfinite(t_stat)


def test_preregistered_promotion_gate():
    """
    Verifies predefined 10-point promotion criteria evaluation.
    """
    gate = PreregisteredPromotionGate()

    valid_decomp = PnLDecomposition(
        delta_gross_price_pnl=500.0,
        delta_funding_pnl=0.0,
        delta_exchange_fees=50.0,
        delta_market_impact=10.0,
        delta_adverse_selection=10.0,
        delta_explicit_slippage=10.0,
        delta_net_pnl=420.0,
    )

    res = gate.evaluate(
        provenance_passed=True,
        accounting_conserved=True,
        pit_clean=True,
        pnl_decomp=valid_decomp,
        hac_t_stat=2.45,
        dsr_p_val=0.02,
        max_dd=14.5,
        n_bars=150,
        null_calibration_passed=True,
        parameter_stability_passed=True,
    )

    assert res["promoted"]
    assert len(res["failed_checks"]) == 0

    # Test rejection on failing HAC t-stat (t = 1.45 < 2.00)
    res_fail = gate.evaluate(
        provenance_passed=True,
        accounting_conserved=True,
        pit_clean=True,
        pnl_decomp=valid_decomp,
        hac_t_stat=1.45,
        dsr_p_val=0.02,
        max_dd=14.5,
        n_bars=150,
        null_calibration_passed=True,
        parameter_stability_passed=True,
    )
    assert not res_fail["promoted"]
    assert "5_hac_paired_t_stat_pass" in res_fail["failed_checks"]


def test_trial_registry_preregistration_and_immutability(tmp_path):
    """
    Verifies trial registry lifecycle, family tracking, duplicate prevention, and JSON persistence.
    """
    reg_path = str(tmp_path / "trial_registry.json")
    registry = TrialRegistry(registry_file=reg_path)

    rec1 = ExperimentRecord(
        experiment_id="EXP-A1-001",
        research_family="A1_FUNDING",
        hypothesis="Funding carry with momentum divergence",
        feature_set=["funding_skew_24h", "oi_delta_zscore"],
        signal_version="v1.0",
        training_spec="WFO_12x28D",
        portfolio_spec="VOL_SCALED",
        execution_config_hash="abc123e3hash",
        dataset_snapshot_hash="data123hash",
        universe_ordering_hash="univ123hash",
        primary_test="HAC_PAIRED_T",
        secondary_metrics=["DSR_P_VAL", "MAX_DD"],
    )

    fp1 = registry.preregister(rec1)
    assert len(fp1) == 64
    assert registry.total_trial_count() == 1
    assert registry.total_trial_count("A1_FUNDING") == 1
    assert registry.total_trial_count("A2_MOMENTUM") == 0

    # Duplicate registration must error
    with pytest.raises(ValueError):
        registry.preregister(rec1)

    # Log completion
    registry.log_completion(
        experiment_id="EXP-A1-001",
        results={"ending_equity": 11500.0, "cagr": 15.0},
        pnl_decomp={"delta_net_pnl": 1500.0},
        hac_paired_t=2.15,
        dsr_p_value=0.03,
        status="PROMOTED",
    )

    # Reload from disk and check consistency
    registry2 = TrialRegistry(registry_file=reg_path)
    assert registry2.total_trial_count() == 1
    assert registry2.records["EXP-A1-001"].status == "PROMOTED"
    assert registry2.records["EXP-A1-001"].hac_paired_t == 2.15


def test_null_benchmark_evaluator():
    """
    Verifies null benchmark calibration checks:
    - Standard normal null passes calibration (mean ~ 0, std ~ 1, FPR ~ 5%)
    - Shifted positive null fails calibration (catches false discovery bias)
    """
    evaluator = NullBenchmarkEvaluator()

    # 1. Unbiased standard normal nulls
    rng = np.random.RandomState(42)
    calibrated_t_stats = list(rng.normal(0.0, 1.0, size=500))
    res_cal = evaluator.evaluate_t_statistics(calibrated_t_stats)

    assert res_cal.passed_calibration
    assert abs(res_cal.mean_t_stat) <= 0.25
    assert len(res_cal.issues) == 0

    # 2. Biased null (systematically shifted positive: mean t = +0.80)
    biased_t_stats = list(rng.normal(0.80, 1.0, size=500))
    res_biased = evaluator.evaluate_t_statistics(biased_t_stats)

    assert not res_biased.passed_calibration
    assert any("NULL_SYSTEMATIC_DRIFT" in issue for issue in res_biased.issues)


def test_generate_permuted_weights():
    """
    Verifies cross-sectional permutation preserves gross leverage while destroying cross-sectional asset identity.
    """
    weights = np.array([
        [0.10, -0.20, 0.30],
        [-0.05, 0.15, -0.10],
    ])
    permuted = generate_permuted_weights(weights, seed=123)

    assert permuted.shape == weights.shape
    # Row-wise gross leverage must be exactly conserved
    assert np.allclose(np.sum(np.abs(permuted), axis=1), np.sum(np.abs(weights), axis=1))
    # Row-wise net exposure must be exactly conserved
    assert np.allclose(np.sum(permuted, axis=1), np.sum(weights, axis=1))
