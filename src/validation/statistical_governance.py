#!/usr/bin/env python3
"""
INSTITUTIONAL STATISTICAL GOVERNANCE & MULTIPLE-TESTING DEFLATION ENGINE
========================================================================
Implements Bailey & López de Prado (2014) Deflated Sharpe Ratio (DSR),
Probability of Backtest Overfitting (PBO) via Combinatorial Purged Cross-Validation,
Cross-Sectional Correlation Shock Simulator, and Centralized Experiment Registry.
"""

import json
import math
import subprocess
import hashlib
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
import scipy.stats as stats
import polars as pl

PIPELINE_ROOT = Path(__file__).resolve().parent.parent.parent
REGISTRY_PATH = PIPELINE_ROOT / "artifacts" / "experiment_registry.jsonl"


def get_git_commit_hash() -> str:
    """Retrieves current Git commit hash for provenance auditing."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(PIPELINE_ROOT),
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip()
    except Exception:
        return "unversioned"


def compute_dataset_hash(data_path: Path) -> str:
    """Computes SHA-256 fingerprint of dataset file."""
    if not data_path.exists():
        return "not_found"
    hasher = hashlib.sha256()
    with open(data_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()[:16]


def compute_config_hash(config_dict: Dict[str, Any]) -> str:
    """Computes SHA-256 hash of configuration hyperparameters."""
    s = json.dumps(config_dict, sort_keys=True)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


# ------------------------------------------------------------------------------
# 1. DEFLATED SHARPE RATIO (DSR - Bailey & López de Prado, 2014)
# ------------------------------------------------------------------------------
def compute_deflated_sharpe_ratio(
    observed_sr: float,
    returns: np.ndarray,
    n_trials: int,
    var_sharpe_null: Optional[float] = None,
    annualization_factor: float = math.sqrt(2190),  # 4H bars per year
) -> Dict[str, float]:
    """
    Computes the Deflated Sharpe Ratio (DSR), correcting the observed Sharpe ratio
    for multiple-testing selection bias across N historical tournament trials,
    sample length, skewness, and kurtosis.

    Reference:
      Bailey, D. H., & López de Prado, M. (2014).
      The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting,
      and Non-Normality. Journal of Portfolio Management, 40(5), 94-107.
    """
    T = len(returns)
    if T < 30:
        return {"dsr": 0.0, "sr_star": 0.0, "p_value": 1.0, "is_statistically_significant": False}

    # De-annualize observed SR to match bar frequency
    sr_bar = observed_sr / annualization_factor

    # Higher moments of bar returns
    skew = float(stats.skew(returns))
    kurt = float(stats.kurtosis(returns, fisher=False))  # Pearson kurtosis (normal = 3)

    # Standard error of Sharpe ratio under non-normality
    var_sr = (1.0 - skew * sr_bar + ((kurt - 1.0) / 4.0) * (sr_bar ** 2)) / (T - 1.0)
    se_sr = math.sqrt(max(1e-8, var_sr))

    # Variance of Sharpe ratios across trials under the null hypothesis of no alpha
    # If not provided empirically across past trials, use theoretical benchmark:
    if var_sharpe_null is None or var_sharpe_null <= 0.0:
        # Standard conservative assumption under i.i.d. random walk
        var_sharpe_null = 1.0 / (T - 1.0)

    # Expected maximum Sharpe ratio under the null hypothesis (N trials)
    # E[max_N {z_n}] ≈ (1 - euler_gamma / (2 * ln N)) * sqrt(2 * ln N)
    if n_trials > 1:
        euler_mascheroni = 0.5772156649
        log_n = math.log(n_trials)
        z_expected = (math.sqrt(2.0 * log_n) + euler_mascheroni / math.sqrt(2.0 * log_n))
        sr_star_bar = math.sqrt(var_sharpe_null) * z_expected
    else:
        sr_star_bar = 0.0

    sr_star_annual = sr_star_bar * annualization_factor

    # Test statistic for DSR
    test_stat = (sr_bar - sr_star_bar) / se_sr
    dsr_prob = float(stats.norm.cdf(test_stat))
    p_val = float(1.0 - dsr_prob)

    status_str = "PASS" if p_val < 0.05 else "FAIL / WEAK EVIDENCE"

    return {
        "observed_annual_sharpe": observed_sr,
        "expected_max_null_sharpe": sr_star_annual,
        "n_trials_penalized": n_trials,
        "skewness": skew,
        "kurtosis": kurt,
        "test_statistic": float(test_stat),
        "deflated_sharpe_probability": float(dsr_prob),
        "p_value": p_val,
        "pass_criterion": "p_value < 0.05 (confidence >= 95%)",
        "status": status_str,
        "deflated_sharpe_ratio": float(dsr_prob),  # legacy compatibility
        "is_statistically_significant": bool(p_val < 0.05),
    }


# ------------------------------------------------------------------------------
# 2. PROBABILITY OF BACKTEST OVERFITTING (PBO - Combinatorial Purged CV)
# ------------------------------------------------------------------------------
def compute_probability_of_backtest_overfitting(
    matrix_returns: np.ndarray,  # Shape: (T_bars, N_candidates)
    n_splits: int = 8,
    label_horizon_bars: int = 18, # 72 hours forward label
    embargo_bars: int = 9,         # Post-test embargo buffer
) -> Dict[str, float]:
    """
    Estimates the Probability of Backtest Overfitting (PBO) via true Purged and Embargoed
    Combinatorial Cross-Validation (CPCV) across competing strategy candidates.

    Enforces De Prado's dual integrity bounds:
    1. Label Purging: Purges all training observations whose label intervals [t, t+h]
       overlap with any OOS test interval.
    2. Embargo Buffer: Removes e bars immediately following OOS test blocks to prevent
       post-test auto-correlation leakage.
    """
    T, N = matrix_returns.shape
    if N < 2:
        return {"pbo": 0.0, "is_overfitted": False}

    import itertools
    split_size = T // n_splits
    half = n_splits // 2
    combinations = list(itertools.combinations(range(n_splits), half))

    logits = []

    for is_indices in combinations:
        oos_indices = [i for i in range(n_splits) if i not in is_indices]

        # Identify all OOS test time intervals [start, end]
        oos_intervals = []
        for idx in oos_indices:
            start_t = idx * split_size
            end_t = (idx + 1) * split_size if idx < n_splits - 1 else T
            oos_intervals.append((start_t, end_t))

        # Build purged and embargoed IS sample indices
        is_valid_indices = []
        for idx in is_indices:
            start_t = idx * split_size
            end_t = (idx + 1) * split_size if idx < n_splits - 1 else T

            for t in range(start_t, end_t):
                # Check overlap with any OOS test block (label interval: [t, t + label_horizon_bars])
                overlaps_oos = False
                for (oos_start, oos_end) in oos_intervals:
                    # Purging condition: label [t, t + h] overlaps [oos_start, oos_end]
                    if not (t + label_horizon_bars < oos_start or t > oos_end):
                        overlaps_oos = True
                        break
                    # Embargo condition: t falls within [oos_end, oos_end + embargo_bars]
                    if oos_end <= t <= oos_end + embargo_bars:
                        overlaps_oos = True
                        break

                if not overlaps_oos:
                    is_valid_indices.append(t)

        # Build OOS indices
        oos_valid_indices = []
        for (oos_start, oos_end) in oos_intervals:
            oos_valid_indices.extend(range(oos_start, oos_end))

        if len(is_valid_indices) < 50 or len(oos_valid_indices) < 50:
            continue

        is_data = matrix_returns[is_valid_indices]
        oos_data = matrix_returns[oos_valid_indices]

        # In-sample Sharpe for all candidates
        is_sr = np.mean(is_data, axis=0) / (np.std(is_data, axis=0) + 1e-8)
        best_is_idx = int(np.argmax(is_sr))

        # Out-of-sample rank of the IS best candidate
        oos_sr = np.mean(oos_data, axis=0) / (np.std(oos_data, axis=0) + 1e-8)
        oos_rank = stats.rankdata(oos_sr)[best_is_idx]  # 1 to N
        rel_rank = oos_rank / (N + 1.0)  # 0 to 1

        # Logit of relative rank
        rel_rank_clipped = np.clip(rel_rank, 1e-4, 1.0 - 1e-4)
        logit = math.log(rel_rank_clipped / (1.0 - rel_rank_clipped))
        logits.append(logit)

    # PBO is probability that relative rank is below median (logit < 0)
    pbo = float(np.mean([1.0 if lg < 0.0 else 0.0 for lg in logits])) if len(logits) > 0 else 0.0

    # Institutional classification scale
    if pbo < 0.10:
        pbo_rating = "Excellent (<10%)"
    elif pbo < 0.20:
        pbo_rating = "Strong (10-20%)"
    elif pbo < 0.35:
        pbo_rating = "Moderate (20-35%)"
    elif pbo <= 0.50:
        pbo_rating = "Weak / Caution (35-50%)"
    else:
        pbo_rating = "Fail (>50%)"

    return {
        "pbo": pbo,
        "pbo_pct": pbo * 100.0,
        "pbo_rating": pbo_rating,
        "n_combinations_evaluated": len(logits),
        "label_horizon_bars": label_horizon_bars,
        "embargo_bars": embargo_bars,
        "is_overfitted": bool(pbo > 0.35),
    }


# ------------------------------------------------------------------------------
# 3. CROSS-SECTIONAL CORRELATION SHOCK STRESS TEST
# ------------------------------------------------------------------------------
def simulate_correlation_shock(
    cov_matrix: np.ndarray,
    target_correlation: float = 0.85,
) -> np.ndarray:
    """
    Stress-tests the covariance matrix by synthetically compressing cross-asset
    correlations towards `target_correlation` while preserving individual asset volatilities.

    Answers: What happens to risk-parity allocation and gross risk when all crypto
             assets collapse into a single monolithic factor (rho -> 0.85)?
    """
    n = cov_matrix.shape[0]
    std_devs = np.sqrt(np.maximum(1e-8, np.diag(cov_matrix)))
    D = np.diag(std_devs)
    D_inv = np.diag(1.0 / std_devs)

    # Extract correlation matrix
    R = D_inv @ cov_matrix @ D_inv
    np.fill_diagonal(R, 1.0)

    # Blend correlation matrix with equicorrelation shock matrix J
    # R_shock = (1 - alpha) * R + alpha * (target_corr * 1 + (1 - target_corr) * I)
    J = np.full((n, n), target_correlation)
    np.fill_diagonal(J, 1.0)

    R_shock = J
    cov_shock = D @ R_shock @ D
    return cov_shock


# ------------------------------------------------------------------------------
# 4. CENTRALIZED EXPERIMENT REGISTRY
# ------------------------------------------------------------------------------
def register_experiment(
    experiment_id: str,
    architecture_name: str,
    config: Dict[str, Any],
    cagr_pct: float,
    sharpe_ratio: float,
    max_dd_pct: float,
    turnover_nav: float,
    accounting_discrepancy: float,
    sample_returns: Optional[np.ndarray] = None,
    dataset_name: str = "raw_candles_4h.parquet",
) -> Dict[str, Any]:
    """
    Logs an immutable experiment record to artifacts/experiment_registry.jsonl,
    computing cumulative trials count and evaluating Deflated Sharpe Ratio (DSR).
    """
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Count historical experiments to penalize trial count
    past_trials = 0
    past_sharpes = []
    if REGISTRY_PATH.exists():
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    past_trials += 1
                    try:
                        record = json.loads(line)
                        if "sharpe_ratio" in record:
                            past_sharpes.append(record["sharpe_ratio"])
                    except Exception:
                        pass

    n_trials = past_trials + 1
    var_sharpe = float(np.var(past_sharpes)) if len(past_sharpes) >= 5 else 0.05

    # Compute DSR if returns provided
    if sample_returns is not None and len(sample_returns) > 30:
        dsr_metrics = compute_deflated_sharpe_ratio(
            observed_sr=sharpe_ratio,
            returns=sample_returns,
            n_trials=n_trials,
            var_sharpe_null=var_sharpe,
        )
    else:
        dsr_metrics = {
            "deflated_sharpe_ratio": 0.0,
            "expected_max_null_sharpe": 0.0,
            "is_statistically_significant": False,
        }

    git_hash = get_git_commit_hash()
    data_hash = compute_dataset_hash(PIPELINE_ROOT / "data" / "lake" / dataset_name)
    config_hash = compute_config_hash(config)

    entry = {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "experiment_id": experiment_id,
        "trial_number": n_trials,
        "architecture": architecture_name,
        "git_commit": git_hash,
        "dataset_hash": data_hash,
        "config_hash": config_hash,
        "cagr_pct": cagr_pct,
        "sharpe_ratio": sharpe_ratio,
        "max_dd_pct": max_dd_pct,
        "turnover_nav": turnover_nav,
        "accounting_discrepancy_usd": accounting_discrepancy,
        "deflated_sharpe_ratio": dsr_metrics.get("deflated_sharpe_ratio", 0.0),
        "expected_null_sharpe": dsr_metrics.get("expected_max_null_sharpe", 0.0),
        "dsr_significant": dsr_metrics.get("is_statistically_significant", False),
        "config_params": config,
    }

    with open(REGISTRY_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    return entry


# ------------------------------------------------------------------------------
# 5. NESTED WALK-FORWARD OPTIMIZATION (NESTED WFO / NESTED CPCV)
# ------------------------------------------------------------------------------
@dataclass
class NestedWFOResult:
    n_outer_folds: int
    outer_fold_sharpes: List[float]
    outer_fold_hit_rate: float
    mean_outer_sharpe: float
    median_outer_sharpe: float
    worst_outer_sharpe: float
    outer_sharpe_dispersion: float
    outer_fold_cagrs: List[float]
    outer_fold_max_dds: List[float]
    outer_fold_sortinos: List[float]
    outer_fold_details: List[Dict[str, Any]]
    inner_selected_models: List[Dict[str, Any]]
    is_statistically_robust: bool


class NestedWFOEngine:
    """
    Nested Walk-Forward Optimization & Nested Cross-Validation Engine.
    Ensures complete operational separation between inner optimization and outer evaluation:
    - Inner Loop (In-Sample / Validation Folds):
      Performs all factor selection, parameter lookback tuning, horizon selection,
      and shrinkage/weight estimation.
    - Outer Loop (Untouched Out-of-Sample Evaluation Fold):
      Evaluates the frozen model selected by the inner loop strictly on untouched data,
      enforcing label interval purging and post-test embargo buffers.
    """
    def __init__(
        self,
        matrix_returns: np.ndarray,  # (T_bars, N_candidates)
        n_outer_folds: int = 5,
        n_inner_splits: int = 4,
        label_horizon_bars: int = 18,
        embargo_bars: int = 9,
    ):
        self.returns = matrix_returns
        self.T, self.N = matrix_returns.shape
        self.n_outer_folds = n_outer_folds
        self.n_inner_splits = n_inner_splits
        self.label_horizon = label_horizon_bars
        self.embargo = embargo_bars

    def run_nested_wfo(self) -> NestedWFOResult:
        """
        Executes Nested Walk-Forward Optimization.
        """
        outer_fold_size = self.T // (self.n_outer_folds + 1)
        outer_sharpes = []
        outer_cagrs = []
        outer_max_dds = []
        outer_sortinos = []
        outer_details = []
        selected_models = []

        for f in range(1, self.n_outer_folds + 1):
            train_end = f * outer_fold_size
            test_start = train_end + self.embargo
            test_end = min((f + 1) * outer_fold_size, self.T)

            if test_end <= test_start or train_end < 100:
                continue

            inner_data = self.returns[:train_end - self.label_horizon]
            outer_data = self.returns[test_start:test_end]

            # Inner Loop: Cross-validate candidate models/parameters
            inner_T = len(inner_data)
            inner_split_sz = inner_T // self.n_inner_splits
            inner_perf = np.zeros(self.N)

            for s in range(self.n_inner_splits - 1):
                in_train = inner_data[: (s + 1) * inner_split_sz - self.label_horizon]
                in_val = inner_data[(s + 1) * inner_split_sz + self.embargo : (s + 2) * inner_split_sz]
                if len(in_train) >= 30 and len(in_val) >= 20:
                    sr_val = np.mean(in_val, axis=0) / (np.std(in_val, axis=0) + 1e-8)
                    inner_perf += sr_val

            best_model_idx = int(np.argmax(inner_perf))
            selected_models.append({
                "outer_fold": f,
                "best_candidate_idx": best_model_idx,
                "inner_val_score": float(inner_perf[best_model_idx]),
            })

            # Outer Loop: Untouched Evaluation
            if len(outer_data) >= 20:
                outer_ret = outer_data[:, best_model_idx]
                outer_sr = float((np.mean(outer_ret) / (np.std(outer_ret) + 1e-8)) * math.sqrt(2190))
                
                # Compound equity curve & Max Drawdown for this fold
                eq_curve = np.cumprod(1.0 + outer_ret)
                running_max = np.maximum.accumulate(eq_curve)
                dd_series = (running_max - eq_curve) / (running_max + 1e-8)
                fold_max_dd = float(np.max(dd_series)) * 100.0
                
                # Annualized CAGR for fold
                fold_bars = len(outer_ret)
                fold_cagr = float(((eq_curve[-1]) ** (2190.0 / fold_bars) - 1.0) * 100.0) if fold_bars > 0 else 0.0
                
                # Downside deviation & Sortino
                downside_ret = outer_ret[outer_ret < 0.0]
                downside_std = float(np.std(downside_ret)) if len(downside_ret) > 1 else (np.std(outer_ret) + 1e-8)
                fold_sortino = float((np.mean(outer_ret) / (downside_std + 1e-8)) * math.sqrt(2190))

                outer_sharpes.append(outer_sr)
                outer_cagrs.append(fold_cagr)
                outer_max_dds.append(fold_max_dd)
                outer_sortinos.append(fold_sortino)
                
                outer_details.append({
                    "fold": f,
                    "bars": fold_bars,
                    "best_model_idx": best_model_idx,
                    "sharpe": outer_sr,
                    "cagr_pct": fold_cagr,
                    "max_dd_pct": fold_max_dd,
                    "sortino": fold_sortino,
                })

        mean_outer_sr = float(np.mean(outer_sharpes)) if len(outer_sharpes) > 0 else 0.0
        median_outer_sr = float(np.median(outer_sharpes)) if len(outer_sharpes) > 0 else 0.0
        worst_outer_sr = float(np.min(outer_sharpes)) if len(outer_sharpes) > 0 else 0.0
        outer_sr_dispersion = float(np.std(outer_sharpes)) if len(outer_sharpes) > 0 else 0.0
        hit_rate = float(np.mean([1.0 if s > 0.0 else 0.0 for s in outer_sharpes])) if len(outer_sharpes) > 0 else 0.0
        is_robust = bool((mean_outer_sr >= 1.0) and (hit_rate >= 0.70))

        return NestedWFOResult(
            n_outer_folds=len(outer_sharpes),
            outer_fold_sharpes=outer_sharpes,
            outer_fold_hit_rate=hit_rate,
            mean_outer_sharpe=mean_outer_sr,
            median_outer_sharpe=median_outer_sr,
            worst_outer_sharpe=worst_outer_sr,
            outer_sharpe_dispersion=outer_sr_dispersion,
            outer_fold_cagrs=outer_cagrs,
            outer_fold_max_dds=outer_max_dds,
            outer_fold_sortinos=outer_sortinos,
            outer_fold_details=outer_details,
            inner_selected_models=selected_models,
            is_statistically_robust=is_robust,
        )


# ------------------------------------------------------------------------------
# 6. INSTITUTIONAL RESULT CLASSIFICATION HIERARCHY & OPERATIONAL RULE 1 GATES
# ------------------------------------------------------------------------------

class DryWellException(Exception):
    """
    Raised when complex portfolio machinery (QP solvers, Two-Tranche allocation,
    Merton jump leverage sizing, profit sweeps) is attempted on a signal or composite
    exhibiting negative gross drift in Stage A.
    """
    pass


def verify_stage_a_hurdle(stage_a_sharpe: float, stage_a_cagr: float, raise_exception: bool = False) -> bool:
    """
    Operational Rule 1 Gate:
    Halts all complex architecture until Stage A (Unlevered, zero-cost rank factor)
    is strongly positive: Sharpe >= 1.20 and CAGR > 0.0%.
    
    If the raw mathematical signal does not make money in a frictionless world,
    it is dead on arrival in the real world.
    """
    passed = bool(stage_a_sharpe >= 1.20 and stage_a_cagr > 0.0)
    if not passed and raise_exception:
        raise DryWellException(
            f"DRY WELL VIOLATION: Stage A (unlevered, zero-cost rank factor) failed hurdle "
            f"(Sharpe={stage_a_sharpe:.2f} < 1.20, CAGR={stage_a_cagr:+.2f}%). "
            f"Complex portfolio architecture, two-tranche sweeping, and leverage optimization "
            f"are strictly prohibited on signals with negative gross drift."
        )
    return passed


def evaluate_institutional_tier_status(
    accounting_discrepancy: float,
    invariants_audited: int,
    invariants_passed: bool,
    finite_trade_eligible_features: bool,
    raw_ic: float,
    hac_t_stat: float,
    placebo_rejected: bool,
    stage_a_sharpe: float = 0.0,
    stage_a_cagr: float = 0.0,
    composite_oos_drift_passed: bool = False,
    wfo_res: Optional[NestedWFOResult] = None,
    execution_fill_rate_stress_passed: bool = False,
    forward_telemetry_active: bool = False,
    production_signoff: bool = False,
) -> Dict[str, Any]:
    """
    Evaluates strategy readiness across the 7-stage Institutional Progression:
    - Tier 1: Engineering Validated
    - Tier 2A: Factor Research Supported (Individual Factor Level)
    - Tier 2B: Composite Research Supported (Portfolio Multi-Factor Composite Level)
    - Tier 3A: Economic OOS Supported (Nested WFO / CPCV Outer Folds)
    - Tier 3B: Execution Supported (Fill Quality Stress Matrix & Friction Monotonicity)
    - Tier 3C: Forward-Test Supported (Live Telemetry & Paper-Trading Reconciliation)
    - Tier 3D: Production Approved (Full Multi-Signature Capital Allocation)
    """
    tier_1_pass = bool(
        accounting_discrepancy == 0.0
        and invariants_passed
        and invariants_audited >= 2190
        and finite_trade_eligible_features
    )
    
    # Tier 2A: Individual Factor Level
    tier_2a_pass = bool(
        tier_1_pass
        and raw_ic > 0.010
        and hac_t_stat > 2.0
        and placebo_rejected
    )

    # Operational Rule 1: Stage A Hurdle Gate
    stage_a_hurdle_passed = verify_stage_a_hurdle(stage_a_sharpe, stage_a_cagr, raise_exception=False)

    # Tier 2B: Composite Level (Guards against overfitted combinations that fail out-of-sample)
    tier_2b_pass = bool(
        tier_2a_pass
        and stage_a_hurdle_passed
        and composite_oos_drift_passed
    )

    # Tier 3A: Economic OOS Supported via Predetermined Outer-Fold Gates:
    # 1. Mean outer Sharpe >= 0.50
    # 2. Median outer Sharpe > 0.00
    # 3. Outer fold win rate >= 60.0% (>= 3 of 5 folds positive)
    # 4. Worst outer fold Sharpe > -1.50 (bounded left tail)
    tier_3a_pass = bool(
        tier_2b_pass
        and wfo_res is not None
        and wfo_res.mean_outer_sharpe >= 0.50
        and wfo_res.median_outer_sharpe > 0.00
        and wfo_res.outer_fold_hit_rate >= 0.60
        and wfo_res.worst_outer_sharpe > -1.50
    )
    tier_3b_pass = bool(tier_3a_pass and execution_fill_rate_stress_passed)
    tier_3c_pass = bool(tier_3b_pass and forward_telemetry_active)
    tier_3d_pass = bool(tier_3c_pass and production_signoff)

    if tier_3d_pass:
        active_tier = "Tier 3D: Production Approved"
    elif tier_3c_pass:
        active_tier = "Tier 3C: Forward-Test Supported"
    elif tier_3b_pass:
        active_tier = "Tier 3B: Execution Supported"
    elif tier_3a_pass:
        active_tier = "Tier 3A: Economic OOS Supported"
    elif tier_2b_pass:
        active_tier = "Tier 2B: Composite Research Supported"
    elif tier_2a_pass:
        active_tier = "Tier 2A: Factor Research Supported"
    elif tier_1_pass:
        active_tier = "Tier 1: Engineering Validated"
    else:
        active_tier = "Preliminary / Unvalidated"

    return {
        "active_tier": active_tier,
        "tier_1_engineering_validated": tier_1_pass,
        "tier_2a_factor_research_supported": tier_2a_pass,
        "tier_2b_composite_research_supported": tier_2b_pass,
        "tier_3a_economic_oos_supported": tier_3a_pass,
        "tier_3b_execution_supported": tier_3b_pass,
        "tier_3c_forward_test_supported": tier_3c_pass,
        "tier_3d_production_approved": tier_3d_pass,
        "tier_1_rationale": "Exact mark-to-market accounting ($0.000000), causal timestamps, pre-existing stops, and finite features on trade-eligible points." if tier_1_pass else "Invariant or accounting discrepancies detected.",
        "tier_2a_rationale": "Individual factor demonstrates statistically supported predictive information (Raw IC > 0.010, HAC t > 2.0, placebo rejected)." if tier_2a_pass else "Factor predictive significance or placebo rejection failed.",
        "tier_2b_rationale": (
            "Composite factor demonstrates positive Stage A gross drift (Sharpe >= 1.20, CAGR > 0%) and positive OOS drift."
            if tier_2b_pass else
            (
                f"Stage A Dry Well failure (Sharpe={stage_a_sharpe:.2f} < 1.20, CAGR={stage_a_cagr:+.2f}%); complex portfolio machinery blocked."
                if not stage_a_hurdle_passed else
                "Composite multi-factor assembly unproven or exhibits negative OOS drift."
            )
        ),
        "tier_3a_rationale": f"Untouched outer holdout Sharpe {wfo_res.mean_outer_sharpe:.2f} (Median: {wfo_res.median_outer_sharpe:.2f}, Worst: {wfo_res.worst_outer_sharpe:.2f}) with {wfo_res.outer_fold_hit_rate*100:.1f}% hit rate across {wfo_res.n_outer_folds} folds." if wfo_res else "WFO evaluation pending.",
    }
