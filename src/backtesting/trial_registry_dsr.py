"""
TRIAL REGISTRY & DEFLATED SHARPE RATIO (DSR) LAYER
===================================================
Implements Bailey & López de Prado (2014) Deflated Sharpe Ratio (DSR) to strictly
penalize for multiple-testing bias, cross-trial variance, and non-normal return distributions.
Maintains an immutable append-only JSONL trial audit registry.
"""

import json
import math
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np
from scipy import stats


REGISTRY_PATH = Path("/home/skybullet1987/quant_pipeline/artifacts/ironcore_trial_registry.jsonl")


class TrialRegistryDSR:
    """Manages trial logging and calculates Deflated Sharpe Ratio (DSR)."""
    
    def __init__(self, registry_file: Path = REGISTRY_PATH):
        self.registry_file = registry_file
        self.registry_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.registry_file.exists():
            self.registry_file.touch()

    def load_historical_sharpes(self) -> List[float]:
        sharpes = []
        if not self.registry_file.exists():
            return sharpes
        with open(self.registry_file, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        record = json.loads(line)
                        if "sharpe" in record and record["sharpe"] is not None:
                            val = float(record["sharpe"])
                            if not math.isnan(val):
                                sharpes.append(val)
                    except Exception:
                        continue
        return sharpes

    def log_trial(self, trial_name: str, sharpe: float, cagr: float, max_dd: float, metadata: Optional[Dict[str, Any]] = None):
        record = {
            "trial_name": trial_name,
            "sharpe": float(sharpe),
            "cagr": float(cagr),
            "max_dd": float(max_dd),
            "timestamp": np.datetime64("now").astype(str),
            "metadata": metadata or {}
        }
        with open(self.registry_file, "a") as f:
            f.write(json.dumps(record) + "\n")

    def compute_deflated_sharpe_ratio(
        self,
        candidate_sharpe: float,
        bar_returns: np.ndarray,
        annualization_factor: float = math.sqrt(2190),  # 6 bars/day * 365
        effective_n_trials: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Computes the Deflated Sharpe Ratio (DSR) accounting for:
        1. Historical trial count N_trials (or effective independent trial count N_eff)
        2. Cross-trial variance of Sharpes
        3. Skewness and kurtosis of candidate returns (fat tails)
        """
        historical_sharpes = self.load_historical_sharpes()
        if effective_n_trials is not None and effective_n_trials >= 1.0:
            n_trials = float(effective_n_trials)
        else:
            n_trials = max(len(historical_sharpes) + 1, 1)
        
        # Cross-trial variance
        if len(historical_sharpes) >= 2:
            var_sharpes = float(np.var(historical_sharpes, ddof=1))
        else:
            var_sharpes = 0.50  # Conservative institutional prior variance
            
        std_sharpes = math.sqrt(max(var_sharpes, 1e-6))
        
        # Higher moments of candidate returns
        r = np.asarray(bar_returns, dtype=np.float64)
        r = r[~np.isnan(r)]
        t_samples = len(r)
        
        if t_samples < 10:
            return {"dsr": 0.0, "sr_star": 0.0, "n_trials": n_trials, "p_true_sr": 0.0}
            
        skew = float(stats.skew(r))
        kurt = float(stats.kurtosis(r, fisher=False))  # Pearson kurtosis (normal = 3.0)
        
        # Expected maximum Sharpe under null of N trials
        # SR* = sqrt(V) * [ (1 - gamma) * Z^-1(1 - 1/N) + gamma * Z^-1(1 - 1/(N*e)) ]
        euler_mascheroni = 0.57721566490153286
        if n_trials > 1.0:
            z1 = float(stats.norm.ppf(1.0 - 1.0 / n_trials))
            z2 = float(stats.norm.ppf(1.0 - 1.0 / (n_trials * math.e)))
            sr_star = std_sharpes * ((1.0 - euler_mascheroni) * z1 + euler_mascheroni * z2)
        else:
            sr_star = 0.0
            
        # Non-annualized per-period Sharpe
        sr_period = candidate_sharpe / annualization_factor
        sr_star_period = sr_star / annualization_factor
        
        # Variance of Sharpe estimator under non-normality (Mertens, 2002)
        # Var(SR) = (1 - skew * SR + (kurt - 1)/4 * SR^2) / (T - 1)
        denom_var = 1.0 - skew * sr_period + ((kurt - 1.0) / 4.0) * (sr_period ** 2)
        denom_std = math.sqrt(max(denom_var / max(t_samples - 1, 1), 1e-8))
        
        # DSR Statistic
        dsr_stat = (sr_period - sr_star_period) / denom_std
        dsr_p_value = float(stats.norm.cdf(dsr_stat))
        
        # Probabilistic Sharpe Ratio (vs 0 benchmark)
        psr_stat = sr_period / denom_std
        psr_p_value = float(stats.norm.cdf(psr_stat))
        
        return {
            "candidate_sharpe": candidate_sharpe,
            "expected_max_null_sharpe": float(sr_star),
            "deflated_sharpe_ratio": dsr_p_value,
            "probabilistic_sharpe_ratio": psr_p_value,
            "dsr_statistic": float(dsr_stat),
            "n_trials": n_trials,
            "skewness": skew,
            "kurtosis": kurt,
            "var_sharpes": var_sharpes
        }
