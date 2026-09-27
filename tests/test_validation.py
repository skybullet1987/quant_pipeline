import numpy as np
import polars as pl
import pytest
from pipeline.validation.stress_grid import AdversarialStressGrid, StressScenario


def test_adversarial_stress_grid_execution():
    np.random.seed(42)
    n = 500
    
    # 500 trades with positive expected edge (mean +5 bps, std 10 bps)
    base_returns = np.random.normal(loc=5.0, scale=10.0, size=n).astype(np.float64)
    base_funding = np.full(n, 0.5, dtype=np.float64)  # 0.5 bps funding drag
    is_maker = np.ones(n, dtype=bool)

    grid = AdversarialStressGrid(
        fill_rates=[1.0, 0.50],
        slippage_bps_levels=[1.0, 5.0],
        adverse_selection_levels=[1.0, 2.0],
        funding_shock_levels=[1.0]
    )

    df_results = grid.run_grid(base_returns, base_funding, is_maker)

    assert df_results.height == 2 * 2 * 2 * 1  # 8 scenarios
    assert "sharpe_ratio" in df_results.columns
    assert "is_basin_stable" in df_results.columns

    # Pristine scenario (fill=1.0, slippage=1.0, AS=1.0) must be profitable
    pristine = df_results.filter(
        (pl.col("fill_rate") == 1.0) &
        (pl.col("slippage_bps") == 1.0) &
        (pl.col("adverse_selection_mult") == 1.0)
    )
    assert pristine["is_profitable"][0] is True
    assert pristine["sharpe_ratio"][0] > 0.0
