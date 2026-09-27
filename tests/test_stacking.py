import numpy as np
import pytest
from pipeline.research.stacking import PurgedTimeSeriesSplit, TriModelStacker


def test_purged_time_series_split_leakage():
    n_samples = 100
    purge_window = 5
    splitter = PurgedTimeSeriesSplit(n_splits=3, purge_window=purge_window)
    X = np.arange(n_samples).reshape(-1, 1)

    for train_idx, test_idx in splitter.split(X):
        # Strict temporal non-anticipative invariant: max(train) + purge <= min(test)
        assert train_idx[-1] + purge_window <= test_idx[0]
        # No index intersection between train and test
        assert len(set(train_idx).intersection(set(test_idx))) == 0


def test_tri_model_stacker_fit_and_calibration():
    np.random.seed(42)
    n_samples = 300
    n_features = 8

    # Generate synthetic feature matrix and linear-logistic signal
    X = np.random.normal(loc=0.0, scale=1.0, size=(n_samples, n_features)).astype(np.float32)
    signal = X[:, 0] * 1.5 - X[:, 1] * 0.8 + np.random.normal(0, 0.5, size=n_samples)
    y = (signal > 0.0).astype(int)

    stacker = TriModelStacker(cv_splits=3, purge_window=3)
    stacker.fit(X, y)

    # Inference check
    X_test = np.random.normal(loc=0.0, scale=1.0, size=(30, n_features)).astype(np.float32)
    probs = stacker.predict_proba(X_test)
    preds = stacker.predict(X_test, threshold=0.5)

    assert probs.shape == (30, 2)
    assert len(preds) == 30
    # Simplex constraint check: P(0) + P(1) == 1.0
    np.testing.assert_allclose(probs.sum(axis=1), np.ones(30), atol=1e-5)
    # Range check [0, 1]
    assert np.all(probs >= 0.0) and np.all(probs <= 1.0)
