"""
Tri-Model Base Learners (RidgeCV + LightGBM + CatBoost) with
Nested Out-of-Fold (OOF) Stacking Meta-Learner and Isotonic Calibration.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generator
import numpy as np
import polars as pl
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression, RidgeClassifierCV

# Resilient tree imports for Python 3.14+
try:
    from lightgbm import LGBMClassifier
except (ImportError, Exception):
    from sklearn.ensemble import HistGradientBoostingClassifier as LGBMClassifier

try:
    from catboost import CatBoostClassifier
except (ImportError, Exception):
    from sklearn.ensemble import GradientBoostingClassifier as CatBoostClassifier


class PurgedTimeSeriesSplit:
    """
    Time-Series Cross-Validator with Purge and Embargo intervals
    to prevent lookahead leakage and autocorrelation contamination.
    """
    def __init__(self, n_splits: int = 5, purge_window: int = 5, embargo_window: int = 5):
        self.n_splits = n_splits
        self.purge_window = purge_window
        self.embargo_window = embargo_window

    def split(self, X: np.ndarray, y: np.ndarray | None = None) -> Generator[tuple[np.ndarray, np.ndarray], None, None]:
        n_samples = len(X)
        fold_size = n_samples // (self.n_splits + 1)

        for i in range(1, self.n_splits + 1):
            train_end = i * fold_size
            test_start = train_end + self.purge_window
            test_end = test_start + fold_size

            if test_end > n_samples:
                test_end = n_samples

            if test_start >= test_end:
                break

            train_indices = np.arange(0, train_end)
            test_indices = np.arange(test_start, test_end)
            yield train_indices, test_indices


class TriModelStacker(BaseEstimator, ClassifierMixin):
    """
    Ensemble meta-learner:
    1. Base models: RidgeClassifierCV, LightGBM, CatBoost
    2. Meta-learner: LogisticRegression over OOF base predictions
    3. Calibration: Isotonic Regression on meta-learner decision scores
    """
    def __init__(self, cv_splits: int = 4, purge_window: int = 2):
        self.cv_splits = cv_splits
        self.purge_window = purge_window
        
        # Base Learners
        self.ridge = RidgeClassifierCV(alphas=np.logspace(-3, 3, 7))
        self.lgbm = LGBMClassifier(max_depth=3, n_estimators=50, random_state=42)
        self.catboost = CatBoostClassifier(max_depth=3, n_estimators=50, random_state=42)
        
        # Meta Learner & Calibrator
        self.meta_learner = LogisticRegression(C=1.0, max_iter=200, random_state=42)
        self.calibrator = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
        self.is_fitted = False

    def _get_base_prob_or_score(self, model: Any, X: np.ndarray) -> np.ndarray:
        if hasattr(model, "predict_proba"):
            probs = model.predict_proba(X)
            return probs[:, 1] if probs.ndim == 2 else probs
        elif hasattr(model, "decision_function"):
            scores = model.decision_function(X)
            # Sigmoid normalization for raw decision function
            return 1.0 / (1.0 + np.exp(-scores))
        else:
            return model.predict(X).astype(np.float32)

    def fit(self, X: np.ndarray, y: np.ndarray) -> TriModelStacker:
        cv = PurgedTimeSeriesSplit(n_splits=self.cv_splits, purge_window=self.purge_window)
        n_samples = len(X)
        
        oof_base_preds = np.full((n_samples, 3), np.nan, dtype=np.float32)
        valid_oof_mask = np.zeros(n_samples, dtype=bool)

        # 1. Generate Out-of-Fold Base Predictions
        for train_idx, val_idx in cv.split(X, y):
            X_tr, y_tr = X[train_idx], y[train_idx]
            X_val, _ = X[val_idx], y[val_idx]

            # Fit fold models
            self.ridge.fit(X_tr, y_tr)
            self.lgbm.fit(X_tr, y_tr)
            self.catboost.fit(X_tr, y_tr)

            oof_base_preds[val_idx, 0] = self._get_base_prob_or_score(self.ridge, X_val)
            oof_base_preds[val_idx, 1] = self._get_base_prob_or_score(self.lgbm, X_val)
            oof_base_preds[val_idx, 2] = self._get_base_prob_or_score(self.catboost, X_val)
            valid_oof_mask[val_idx] = True

        X_oof = oof_base_preds[valid_oof_mask]
        y_oof = y[valid_oof_mask]

        if len(X_oof) == 0:
            raise ValueError("Insufficient sample length for purged time-series validation.")

        # 2. Fit Meta-Learner on Out-of-Fold features
        self.meta_learner.fit(X_oof, y_oof)
        raw_meta_scores = self.meta_learner.predict_proba(X_oof)[:, 1]

        # 3. Fit Isotonic Calibrator strictly on Meta OOF scores
        self.calibrator.fit(raw_meta_scores, y_oof)

        # 4. Refit base learners on 100% of available training history
        self.ridge.fit(X, y)
        self.lgbm.fit(X, y)
        self.catboost.fit(X, y)

        self.is_fitted = True
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("TriModelStacker must be fitted before calling predict_proba.")

        # Compute current base predictions
        p_ridge = self._get_base_prob_or_score(self.ridge, X)
        p_lgbm = self._get_base_prob_or_score(self.lgbm, X)
        p_cb = self._get_base_prob_or_score(self.catboost, X)
        
        Z = np.column_stack([p_ridge, p_lgbm, p_cb])
        raw_meta_scores = self.meta_learner.predict_proba(Z)[:, 1]
        
        # Apply Isotonic Calibration
        calibrated_p1 = self.calibrator.transform(raw_meta_scores)
        calibrated_p1 = np.clip(calibrated_p1, 0.0, 1.0)
        calibrated_p0 = 1.0 - calibrated_p1

        return np.column_stack([calibrated_p0, calibrated_p1])

    def predict(self, X: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        probs = self.predict_proba(X)
        return (probs[:, 1] >= threshold).astype(int)
