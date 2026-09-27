"""
Research Protocol v1.0 — Immutable Specification for Alpha Hypothesis Testing
Provides canonical accounting decomposition, 10-point promotion criteria, and 3-stream evaluation.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List
import numpy as np


@dataclass(frozen=True)
class PnLDecomposition:
    """
    Auditable 6-bucket deterministic PnL decomposition.
    Derived directly from the simulation accounting ledger.
    """
    delta_gross_price_pnl: float
    delta_funding_pnl: float
    delta_exchange_fees: float
    delta_market_impact: float
    delta_adverse_selection: float
    delta_explicit_slippage: float
    delta_net_pnl: float

    @property
    def sum_of_components(self) -> float:
        """
        Net = Gross Price + Funding - Exchange Fees - Market Impact - Adverse Selection - Slippage
        """
        return (
            self.delta_gross_price_pnl
            + self.delta_funding_pnl
            - self.delta_exchange_fees
            - self.delta_market_impact
            - self.delta_adverse_selection
            - self.delta_explicit_slippage
        )

    @property
    def residual(self) -> float:
        """Discrepancy between reported Net PnL and ledger components."""
        return abs(self.delta_net_pnl - self.sum_of_components)

    def is_conserved(self, tolerance: float = 1e-6) -> bool:
        """Exact conservation test for auditable ledger reporting."""
        return self.residual <= tolerance

    def to_dict(self) -> Dict[str, float]:
        d = asdict(self)
        d["residual"] = self.residual
        d["is_conserved"] = self.is_conserved()
        return d


@dataclass(frozen=True)
class ThreeStreamAttribution:
    """
    Synchronized 3-stream time series comparison:
    R_exp(t), R_ctrl(t), Delta_R(t) = R_exp(t) - R_ctrl(t).
    """
    exp_returns: np.ndarray
    ctrl_returns: np.ndarray
    delta_returns: np.ndarray
    timestamps: Optional[np.ndarray] = None
    
    @property
    def mean_delta(self) -> float:
        return float(np.mean(self.delta_returns)) if len(self.delta_returns) > 0 else 0.0

    @property
    def std_delta(self) -> float:
        return float(np.std(self.delta_returns)) + 1e-12 if len(self.delta_returns) > 0 else 1.0

    def compute_newey_west_t_stat(self, max_lag: int = 5) -> float:
        """
        Computes heteroskedasticity and autocorrelation consistent (HAC) paired t-statistic.
        """
        d = self.delta_returns
        n = len(d)
        if n < 10:
            return 0.0
        
        mean_d = np.mean(d)
        gamma_0 = np.var(d, ddof=0)
        
        gamma_sum = 0.0
        for lag in range(1, min(max_lag + 1, n)):
            weight = 1.0 - (lag / (max_lag + 1))
            cov = float(np.mean((d[lag:] - mean_d) * (d[:-lag] - mean_d)))
            gamma_sum += 2.0 * weight * cov
            
        hac_var = (gamma_0 + gamma_sum) / max(n, 1)
        if hac_var <= 0:
            hac_var = 1e-12
            
        hac_se = np.sqrt(hac_var)
        return float(mean_d / hac_se) if hac_se > 0 else 0.0


@dataclass(frozen=True)
class PreregisteredPromotionGate:
    """
    Standard 10-point promotion criteria predefined BEFORE seeing experimental results.
    """
    min_hac_paired_t: float = 2.00
    max_dsr_p_value: float = 0.05
    max_drawdown_pct: float = 25.0
    min_active_bars: int = 100
    accounting_tolerance: float = 1e-6

    def evaluate(
        self,
        provenance_passed: bool,
        accounting_conserved: bool,
        pit_clean: bool,
        pnl_decomp: PnLDecomposition,
        hac_t_stat: float,
        dsr_p_val: float,
        max_dd: float,
        n_bars: int,
        null_calibration_passed: bool,
        parameter_stability_passed: bool,
    ) -> Dict[str, Any]:
        """Evaluates candidate against the immutable 10-point promotion gate."""
        checks = {
            "1_provenance_pass": bool(provenance_passed),
            "2_accounting_pass": bool(accounting_conserved and pnl_decomp.is_conserved(self.accounting_tolerance)),
            "3_pit_cleanliness_pass": bool(pit_clean),
            "4_positive_delta_net_pnl": bool(pnl_decomp.delta_net_pnl > 0.0),
            "5_hac_paired_t_stat_pass": bool(hac_t_stat >= self.min_hac_paired_t),
            "6_dsr_p_value_pass": bool(dsr_p_val <= self.max_dsr_p_value),
            "7_max_drawdown_pass": bool(max_dd <= self.max_drawdown_pct),
            "8_min_observations_pass": bool(n_bars >= self.min_active_bars),
            "9_null_calibration_pass": bool(null_calibration_passed),
            "10_parameter_stability_pass": bool(parameter_stability_passed),
        }
        
        all_passed = all(checks.values())
        return {
            "promoted": all_passed,
            "checklist": checks,
            "failed_checks": [k for k, v in checks.items() if not v],
        }
