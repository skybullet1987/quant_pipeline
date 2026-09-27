import numpy as np
import pytest
from pipeline.research.regime import BOCDConfig, BOCDDetector, GaussianHMMRegime


def test_bocd_hazard_detection_on_regime_shift():
    detector = BOCDDetector(BOCDConfig(hazard_lambda=50.0))
    
    np.random.seed(42)
    # Regime 1: zero mean, low variance (100 steps)
    r1 = np.random.normal(loc=0.0, scale=0.1, size=100)
    # Regime 2: shifted mean, high variance (50 steps)
    r2 = np.random.normal(loc=2.0, scale=0.8, size=50)
    
    hazards = []
    for val in np.concatenate([r1, r2]):
        hazards.append(detector.update(float(val)))

    # Steady state in regime 1 should have low hazard
    assert np.mean(hazards[20:90]) < 0.20
    # Immediate post-shift should show elevated hazard probability
    assert max(hazards[99:110]) > 0.40


def test_hmm_forward_filter_probability_simplex():
    hmm = GaussianHMMRegime()
    np.random.seed(42)
    sample_returns = np.random.normal(loc=0.0005, scale=0.02, size=100).astype(np.float32)

    probs = hmm.process_series(sample_returns)

    assert probs.shape == (100, 3)
    # Check all rows lie on the probability simplex (sum to 1.0)
    np.testing.assert_allclose(probs.sum(axis=1), np.ones(100, dtype=np.float32), atol=1e-5)
    # Check bounds [0, 1]
    assert np.all(probs >= 0.0) and np.all(probs <= 1.0)
