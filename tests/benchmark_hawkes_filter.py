"""
Hawkes Point Process Online Filter Benchmark & Performance Certification Gate (v3.2.1)
File: tests/benchmark_hawkes_filter.py

Validates the performance certification hurdle:
    P50 latency < 5.0 us, P90 latency < 10.0 us
under pinned core, M=5 dense event kernels, preallocated memory, and zero GC allocation.

Also validates that branching matrix spectral radius rho(Gamma) is a fixed offline
structural persistence diagnostic, while lambda(t) tracks real-time dynamic excitation.
"""

import sys
import time
import math
import unittest
import numpy as np

try:
    import numba
    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False


if HAS_NUMBA:
    @numba.njit(fastmath=True)
    def _update_hawkes_kernel_full(
        lambda_components: np.ndarray,
        alpha_base: np.ndarray,
        beta: np.ndarray,
        delta_t: float,
        event_type_j: int,
        mark_scale: float,
        mu: np.ndarray,
        intensities_out: np.ndarray
    ) -> None:
        decay = np.exp(-beta * delta_t)
        lambda_components *= decay
        for i in range(lambda_components.shape[0]):
            lambda_components[i, event_type_j] += alpha_base[i, event_type_j] * mark_scale
            s = 0.0
            for j in range(lambda_components.shape[1]):
                s += lambda_components[i, j]
            intensities_out[i] = mu[i] + s


class MultivariateHawkesFilter:
    """
    Marked Multivariate Hawkes Point Process Online Filter.
    Computes recursive conditional intensity updates in O(nnz(Gamma)) / O(M^2) time.
    """
    def __init__(self, M: int = 5):
        self.M = M
        self.mu = np.array([0.5, 0.5, 0.05, 0.05, 0.02], dtype=np.float64)
        self.beta = np.full((M, M), 5.0, dtype=np.float64)
        self.alpha_base = np.array([
            [0.10, 0.05, 0.02, 0.01, 0.01],
            [0.05, 0.10, 0.01, 0.02, 0.01],
            [0.15, 0.02, 0.30, 0.05, 0.05],
            [0.02, 0.15, 0.05, 0.30, 0.05],
            [0.01, 0.01, 0.05, 0.05, 0.10],
        ], dtype=np.float64)

        self.last_ts_ns = 0
        self.lambda_components = np.zeros((M, M), dtype=np.float64)
        self.current_intensities = self.mu.copy()

        # Offline structural persistence: fixed spectral radius
        self.Gamma = self.alpha_base / self.beta
        eigenvalues = np.linalg.eigvals(self.Gamma)
        self.spectral_radius_rho = float(np.max(np.abs(eigenvalues)))

    def update_tick(self, event_type_j: int, mark_notional_usd: float, current_ts_ns: int) -> np.ndarray:
        if self.last_ts_ns == 0:
            delta_t = 0.001
        else:
            delta_t = (current_ts_ns - self.last_ts_ns) * 1e-9

        self.last_ts_ns = current_ts_ns
        mark_scale = 1.0 + 0.1 * math.log1p(max(0.0, mark_notional_usd / 100_000.0))

        if HAS_NUMBA:
            _update_hawkes_kernel_full(
                self.lambda_components,
                self.alpha_base,
                self.beta,
                delta_t,
                event_type_j,
                mark_scale,
                self.mu,
                self.current_intensities
            )
        else:
            decay_factor = np.exp(-self.beta * delta_t)
            self.lambda_components *= decay_factor
            self.lambda_components[:, event_type_j] += self.alpha_base[:, event_type_j] * mark_scale
            self.current_intensities = self.mu + np.sum(self.lambda_components, axis=1)

        return self.current_intensities


class TestHawkesBenchmark(unittest.TestCase):
    def test_spectral_radius_stability_diagnostic(self):
        """Validates that rho(Gamma) < 1.0 establishes subcritical structural persistence."""
        model = MultivariateHawkesFilter(M=5)
        logger_rho = model.spectral_radius_rho
        self.assertLess(logger_rho, 1.0, f"Branching spectral radius {logger_rho} must be subcritical (< 1.0)")
        self.assertGreater(logger_rho, 0.0)

    def test_performance_certification_gate(self):
        """
        Performance Certification Gate:
        Evaluates 50,000 synthetic arrival events.
        Certifies P50 < 5.0 us and P90 < 10.0 us on Tokyo container.
        """
        model = MultivariateHawkesFilter(M=5)
        n_warmup = 5_000
        n_trials = 50_000

        np.random.seed(42)
        event_types = np.random.randint(0, 5, size=n_warmup + n_trials)
        notionals = np.random.exponential(scale=50_000.0, size=n_warmup + n_trials)
        inter_arrival_ns = np.random.exponential(scale=1_000_000.0, size=n_warmup + n_trials).astype(np.int64)

        current_ts = 1_000_000_000_000

        # Warmup JIT compile
        for k in range(n_warmup):
            current_ts += int(inter_arrival_ns[k])
            model.update_tick(int(event_types[k]), float(notionals[k]), current_ts)

        latencies_ns = np.empty(n_trials, dtype=np.int64)

        # Benchmark run
        for k in range(n_trials):
            idx = n_warmup + k
            current_ts += int(inter_arrival_ns[idx])
            ev = int(event_types[idx])
            notional = float(notionals[idx])

            t0 = time.perf_counter_ns()
            model.update_tick(ev, notional, current_ts)
            t1 = time.perf_counter_ns()

            latencies_ns[k] = t1 - t0

        latencies_us = latencies_ns / 1_000.0
        p50 = float(np.percentile(latencies_us, 50))
        p90 = float(np.percentile(latencies_us, 90))
        p99 = float(np.percentile(latencies_us, 99))

        print(f"\n================ HAWKES FILTER BENCHMARK (M=5, JIT={HAS_NUMBA}) ================")
        print(f"Trials:      {n_trials:,} events")
        print(f"P50 Latency: {p50:.3f} us  [Target: < 5.0 us]")
        print(f"P90 Latency: {p90:.3f} us  [Target: < 10.0 us]")
        print(f"P99 Latency: {p99:.3f} us")
        print(f"Spectral Rho:{model.spectral_radius_rho:.4f} (Offline Structural Persistence)")
        print(f"==========================================================================")

        self.assertLess(p50, 5.0, f"P50 latency {p50:.3f} us violated target < 5.0 us")
        self.assertLess(p90, 10.0, f"P90 latency {p90:.3f} us violated target < 10.0 us")


if __name__ == "__main__":
    unittest.main()
