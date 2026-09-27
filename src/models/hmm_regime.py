import numpy as np
from hmmlearn.hmm import GaussianHMM

class HMMRegimeGovernor:
    def __init__(self, n_states: int = 3, random_state: int = 42, min_covar: float = 1e-3):
        self.n_states = n_states
        self.min_covar = min_covar
        self.random_state = random_state
        self.model = GaussianHMM(
            n_components=n_states,
            covariance_type="diag",
            min_covar=min_covar,
            n_iter=200,
            random_state=random_state
        )
        self.is_fitted = False

    def fit(self, X: np.ndarray) -> "HMMRegimeGovernor":
        if X is None or len(X) < 5:
            return self
        try:
            self.model.fit(X)
            # Regularize transition matrix and startprob to prevent zero-division / NaNs
            if hasattr(self.model, "startprob_"):
                sp = np.nan_to_num(self.model.startprob_, nan=1.0 / self.n_states) + 1e-6
                self.model.startprob_ = sp / np.sum(sp)
            if hasattr(self.model, "transmat_"):
                tm = np.nan_to_num(self.model.transmat_, nan=1.0 / self.n_states) + 1e-6
                self.model.transmat_ = tm / np.sum(tm, axis=1, keepdims=True)
            self.is_fitted = True
        except Exception:
            try:
                # Fallback re-init with higher regularization
                self.model = GaussianHMM(
                    n_components=self.n_states,
                    covariance_type="diag",
                    min_covar=self.min_covar * 10,
                    n_iter=100,
                    random_state=self.random_state
                )
                self.model.fit(X)
                if hasattr(self.model, "startprob_"):
                    sp = np.nan_to_num(self.model.startprob_, nan=1.0 / self.n_states) + 1e-6
                    self.model.startprob_ = sp / np.sum(sp)
                if hasattr(self.model, "transmat_"):
                    tm = np.nan_to_num(self.model.transmat_, nan=1.0 / self.n_states) + 1e-6
                    self.model.transmat_ = tm / np.sum(tm, axis=1, keepdims=True)
                self.is_fitted = True
            except Exception:
                self.is_fitted = False
        return self

    def compute_regime_entropy(self, current_features: np.ndarray) -> tuple[int, float]:
        if not self.is_fitted:
            return 1, 0.5  # Neutral default

        if current_features.ndim == 1:
            current_features = current_features.reshape(1, -1)

        try:
            posteriors = self.model.predict_proba(current_features)[-1]
            if np.any(np.isnan(posteriors)) or np.sum(posteriors) == 0:
                posteriors = np.ones(self.n_states) / self.n_states
            active_state = int(np.argmax(posteriors))

            eps = 1e-12
            entropy = -np.sum(posteriors * np.log(posteriors + eps))
            max_entropy = np.log(self.n_states)

            omega_h = float(np.clip(1.0 - (entropy / max_entropy), 0.0, 1.0))
            return active_state, omega_h
        except Exception:
            return 1, 0.5
