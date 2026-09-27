"""
Research Package — Preregistration, Trial Registry, and Null Benchmark Suite.
"""

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
    NullCalibrationResult,
    generate_permuted_weights,
)

__all__ = [
    "PnLDecomposition",
    "ThreeStreamAttribution",
    "PreregisteredPromotionGate",
    "ExperimentRecord",
    "TrialRegistry",
    "NullBenchmarkEvaluator",
    "NullCalibrationResult",
    "generate_permuted_weights",
]
