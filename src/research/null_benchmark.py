"""
Null Benchmark Calibration Suite (NULL-000)
Evaluates pipeline empirical false positive rates and distribution calibration
under cross-sectional rank permutations atop frozen IronCore v2.4.0 (E3 config).
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional
import numpy as np
import math
from src.research.protocol_spec import ThreeStreamAttribution


@dataclass(frozen=True)
class NullCalibrationResult:
    """Statistical summary of null benchmark calibration."""
    n_permutations: int
    mean_t_stat: float
    std_t_stat: float
    median_t_stat: float
    p5_t_stat: float
    p95_t_stat: float
    max_t_stat: float
    min_t_stat: float
    empirical_fpr_alpha_05: float  # Frequency of |t| >= 1.96
    empirical_fpr_alpha_01: float  # Frequency of |t| >= 2.58
    passed_calibration: bool
    issues: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class NullBenchmarkEvaluator:
    """
    Evaluates a collection of null test statistics against theoretical and empirical expectations.
    """
    def __init__(
        self,
        mean_tolerance: float = 0.25,
        std_min: float = 0.70,
        std_max: float = 1.30,
        expected_alpha_05_range: tuple = (0.015, 0.085),
    ):
        self.mean_tolerance = mean_tolerance
        self.std_min = std_min
        self.std_max = std_max
        self.expected_alpha_05_range = expected_alpha_05_range

    def evaluate_t_statistics(self, t_stats: List[float]) -> NullCalibrationResult:
        """Evaluates empirical null t-statistics distribution."""
        arr = np.array(t_stats, dtype=float)
        n = len(arr)
        if n == 0:
            return NullCalibrationResult(
                n_permutations=0, mean_t_stat=0.0, std_t_stat=0.0, median_t_stat=0.0,
                p5_t_stat=0.0, p95_t_stat=0.0, max_t_stat=0.0, min_t_stat=0.0,
                empirical_fpr_alpha_05=0.0, empirical_fpr_alpha_01=0.0,
                passed_calibration=False, issues=["EMPTY_T_STATS_SAMPLE"]
            )

        mean_t = float(np.mean(arr))
        std_t = float(np.std(arr, ddof=1)) if n > 1 else 1.0
        med_t = float(np.median(arr))
        p5 = float(np.percentile(arr, 5))
        p95 = float(np.percentile(arr, 95))
        max_t = float(np.max(arr))
        min_t = float(np.min(arr))

        fpr_05 = float(np.mean(np.abs(arr) >= 1.96))
        fpr_01 = float(np.mean(np.abs(arr) >= 2.58))

        issues = []
        if abs(mean_t) > self.mean_tolerance:
            issues.append(f"NULL_SYSTEMATIC_DRIFT: mean t = {mean_t:.3f} (tol: ±{self.mean_tolerance})")
        if std_t < self.std_min or std_t > self.std_max:
            issues.append(f"NULL_VARIANCE_DISTORTED: std t = {std_t:.3f} (expected: [{self.std_min}, {self.std_max}])")
        if not (self.expected_alpha_05_range[0] <= fpr_05 <= self.expected_alpha_05_range[1]):
            issues.append(f"NULL_FPR_BREACH: empirical alpha(0.05) = {fpr_05:.3f} (expected: {self.expected_alpha_05_range})")

        passed = len(issues) == 0
        return NullCalibrationResult(
            n_permutations=n,
            mean_t_stat=mean_t,
            std_t_stat=std_t,
            median_t_stat=med_t,
            p5_t_stat=p5,
            p95_t_stat=p95,
            max_t_stat=max_t,
            min_t_stat=min_t,
            empirical_fpr_alpha_05=fpr_05,
            empirical_fpr_alpha_01=fpr_01,
            passed_calibration=passed,
            issues=issues,
        )


def generate_permuted_weights(
    weights_matrix: np.ndarray,
    seed: int,
) -> np.ndarray:
    """
    Permutes cross-sectional asset identities consistently across the entire time series.
    Preserves exact holding periods, autocorrelation, turnover, gross exposure, and fee physics
    while destroying asset-specific alpha coupling.
    """
    rng = np.random.RandomState(seed)
    n_bars, n_symbols = weights_matrix.shape
    perm = rng.permutation(n_symbols)
    return weights_matrix[:, perm].copy()


def generate_permuted_scores(
    scores_matrix: np.ndarray,
    seed: int,
) -> np.ndarray:
    """
    Permutes raw alpha scores cross-sectionally per bar before passing through portfolio hysteresis.
    """
    rng = np.random.RandomState(seed)
    n_bars, n_symbols = scores_matrix.shape
    permuted = np.zeros_like(scores_matrix)
    for t in range(n_bars):
        permuted[t] = rng.permutation(scores_matrix[t])
    return permuted

