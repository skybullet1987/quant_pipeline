import numpy as np
import pandas as pd
import joblib
from hmmlearn.hmm import GaussianHMM

class CanonicalGaussianHMM:
    """
    3-State Gaussian HMM wrapper that guarantees deterministic state ordering 
    by sorting component states by Volatility Emission Means post-training.
    
    Ensures:
      - State 0: Low Volatility / Chop
      - State 1: Normal Volatility / Trend
      - State 2: High Volatility / Expansion
    """
    def __init__(self, n_components=3, covariance_type="full", n_iter=500, random_state=42):
        self.n_components = n_components
        self.covariance_type = covariance_type
        self.n_iter = n_iter
        self.random_state = random_state
        self.model = None
        self.state_map = None # Mapping from raw EM index to sorted canonical index

    def fit(self, X_values, vol_feature_idx=0):
        """
        Fits HMM and computes canonical sorting based on vol_feature_idx.
        """
        raw_hmm = GaussianHMM(
            n_components=self.n_components,
            covariance_type=self.covariance_type,
            n_iter=self.n_iter,
            random_state=self.random_state
        )
        raw_hmm.fit(X_values)

        # Extract Volatility Emission Means for each raw component
        vol_means = raw_hmm.means_[:, vol_feature_idx]
        
        # Sort raw component indices by ascending volatility
        canonical_order = np.argsort(vol_means)
        
        # Build mapping: raw_index -> canonical_index
        self.state_map = {raw_idx: canonical_idx for canonical_idx, raw_idx in enumerate(canonical_order)}
        
        # Re-order HMM internal matrices to freeze canonical state definitions permanently
        sorted_hmm = GaussianHMM(
            n_components=self.n_components,
            covariance_type=self.covariance_type,
            n_iter=self.n_iter,
            random_state=self.random_state
        )
        sorted_hmm.means_ = raw_hmm.means_[canonical_order]
        sorted_hmm.covars_ = raw_hmm.covars_[canonical_order]
        sorted_hmm.startprob_ = raw_hmm.startprob_[canonical_order]
        sorted_hmm.transmat_ = raw_hmm.transmat_[canonical_order][:, canonical_order]

        self.model = sorted_hmm
        return self

    def predict_features(self, X_values):
        """
        Returns a DataFrame containing:
          - p_state_0 (Low Vol Prob)
          - p_state_1 (Normal Vol Prob)
          - p_state_2 (High Vol Prob)
          - canonical_state (Hard integer)
        """
        probs = self.model.predict_proba(X_values)
        states = np.argmax(probs, axis=1)

        df_out = pd.DataFrame(probs, columns=['hmm_p_low_vol', 'hmm_p_norm_vol', 'hmm_p_high_vol'])
        df_out['hmm_canonical_state'] = states.astype(str)
        return df_out

if __name__ == "__main__":
    print("Testing Canonical HMM Sorting Engine...")
    # Mock X matrix: [vol_zscore, mom_7d, breadth]
    X_mock = np.random.randn(1000, 3)
    
    chmm = CanonicalGaussianHMM()
    chmm.fit(X_mock, vol_feature_idx=0)
    
    features = chmm.predict_features(X_mock[:5])
    print("\n--- Canonical Probability Vector Output Sample ---")
    print(features)
