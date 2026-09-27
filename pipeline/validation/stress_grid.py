"""
Layer 4 Validation Engine:
Multi-Variable Adversarial Stress Grid & Parameter Basin Evaluator.
Simulates execution performance under degraded microstructure and hostile regime shocks.
"""
from __future__ import annotations

from dataclasses import dataclass
import itertools
import numpy as np
import polars as pl


@dataclass(frozen=True)
class StressScenario:
    fill_rate_multiplier: float        # [0.10, 1.00]
    slippage_shock_bps: float          # [0.0, 15.0]
    latency_penalty_ms: float          # [0.0, 500.0]
    adverse_selection_mult: float      # [1.0, 3.0]
    funding_shock_multiplier: float    # [1.0, 4.0]


@dataclass(frozen=True)
class StressTestResult:
    scenario: StressScenario
    sharpe_ratio: float
    max_drawdown_pct: float
    win_rate: float
    total_net_pnl_bps: float
    is_profitable: bool
    is_basin_stable: bool


class AdversarialStressGrid:
    """
    Stress-tests pure strategy alpha signals against hostile microstructure grids.
    """
    def __init__(
        self,
        fill_rates: list[float] | None = None,
        slippage_bps_levels: list[float] | None = None,
        adverse_selection_levels: list[float] | None = None,
        funding_shock_levels: list[float] | None = None,
    ):
        self.fill_rates = fill_rates or [1.0, 0.70, 0.40, 0.20]
        self.slippage_bps_levels = slippage_bps_levels or [0.5, 2.0, 5.0, 10.0]
        self.adverse_selection_levels = adverse_selection_levels or [1.0, 1.5, 2.5]
        self.funding_shock_levels = funding_shock_levels or [1.0, 2.0]

    def evaluate_scenario(
        self,
        base_returns_bps: np.ndarray,
        base_funding_drag_bps: np.ndarray,
        is_maker_mask: np.ndarray,
        scenario: StressScenario
    ) -> StressTestResult:
        n = len(base_returns_bps)
        if n == 0:
            raise ValueError("Empty return series provided for stress testing.")

        # 1. Simulate Stochastic Fill Dropouts
        fill_rand = np.random.uniform(0.0, 1.0, size=n)
        filled_mask = fill_rand <= scenario.fill_rate_multiplier

        # 2. Apply Slippage and Adverse Selection Penalties
        execution_drag = np.zeros(n, dtype=np.float64)
        
        # Maker orders suffer elevated adverse selection
        execution_drag[is_maker_mask] = 1.0 * scenario.adverse_selection_mult
        
        # Taker / unfulfilled orders suffer slippage shock
        execution_drag[~is_maker_mask] = scenario.slippage_shock_bps

        # Latency drag penalty (0.01 bps per 10ms of latency)
        latency_drag = (scenario.latency_penalty_ms / 10.0) * 0.01
        execution_drag += latency_drag

        # 3. Apply Funding Carry Shocks
        shocked_funding = base_funding_drag_bps * scenario.funding_shock_multiplier

        # 4. Net Return Realization
        net_returns_bps = np.where(
            filled_mask,
            base_returns_bps - execution_drag - shocked_funding,
            0.0  # Zero return if unfilled
        )

        total_net_bps = float(np.sum(net_returns_bps))
        active_returns = net_returns_bps[filled_mask]

        if len(active_returns) > 1 and np.std(active_returns) > 1e-6:
            # Annualized Sharpe (assuming 1-minute sampling interval)
            sharpe = float(np.mean(active_returns) / np.std(active_returns) * np.sqrt(525600.0))
        else:
            sharpe = 0.0

        # Cumulative drawdown computation
        cum_returns = np.cumsum(net_returns_bps)
        peak = np.maximum.accumulate(cum_returns)
        drawdowns = peak - cum_returns
        max_dd_bps = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0.0
        max_dd_pct = max_dd_bps / 10000.0

        win_rate = float(np.mean(active_returns > 0.0)) if len(active_returns) > 0 else 0.0
        is_profitable = total_net_bps > 0.0
        is_basin_stable = (sharpe > 1.2) and (max_dd_pct < 0.15) and is_profitable

        return StressTestResult(
            scenario=scenario,
            sharpe_ratio=sharpe,
            max_drawdown_pct=max_dd_pct,
            win_rate=win_rate,
            total_net_pnl_bps=total_net_bps,
            is_profitable=is_profitable,
            is_basin_stable=is_basin_stable,
        )

    def run_grid(
        self,
        base_returns_bps: np.ndarray,
        base_funding_drag_bps: np.ndarray,
        is_maker_mask: np.ndarray,
    ) -> pl.DataFrame:
        results = []
        combos = itertools.product(
            self.fill_rates,
            self.slippage_bps_levels,
            self.adverse_selection_levels,
            self.funding_shock_levels,
        )

        for fill_rate, slippage_bps, as_mult, funding_mult in combos:
            scenario = StressScenario(
                fill_rate_multiplier=fill_rate,
                slippage_shock_bps=slippage_bps,
                latency_penalty_ms=15.0,
                adverse_selection_mult=as_mult,
                funding_shock_multiplier=funding_mult,
            )
            res = self.evaluate_scenario(base_returns_bps, base_funding_drag_bps, is_maker_mask, scenario)
            results.append({
                "fill_rate": fill_rate,
                "slippage_bps": slippage_bps,
                "adverse_selection_mult": as_mult,
                "funding_shock_mult": funding_mult,
                "sharpe_ratio": res.sharpe_ratio,
                "max_drawdown_pct": res.max_drawdown_pct,
                "win_rate": res.win_rate,
                "total_net_pnl_bps": res.total_net_pnl_bps,
                "is_profitable": res.is_profitable,
                "is_basin_stable": res.is_basin_stable,
            })

        return pl.DataFrame(results)
