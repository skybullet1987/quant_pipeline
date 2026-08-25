import polars as pl
from src.portfolio.allocator import DollarNeutralPortfolioAllocator
from src.portfolio.risk_governor import ContinuousRiskGovernor

def test_allocation_dollar_neutrality():
    mock_data = pl.DataFrame({
        "ticker": ["SOLUSD", "AVAXUSD", "LINKUSD", "NEARUSD", "DOTUSD", "ADAUSD"],
        "close": [150.0, 30.0, 15.0, 5.0, 7.0, 0.40],
        "gk_vol_20p": [0.03, 0.04, 0.02, 0.05, 0.03, 0.04],
        "mom_24h": [0.05, 0.02, -0.01, -0.04, 0.01, -0.02],
        "predicted_rank_score": [2.5, 1.8, 0.5, -0.2, -1.2, -2.1]
    })
    
    omega = ContinuousRiskGovernor.compute_exposure_scalar(mock_data)
    assert 0.20 <= omega <= 1.00
    
    allocator = DollarNeutralPortfolioAllocator(top_quantile=0.33, max_gross_leverage=2.0)
    orders = allocator.generate_orders(mock_data, equity_usd=1000.0, macro_omega=omega)
    
    assert abs(orders["net_dollar_exposure"]) < 1e-4
    assert len(orders["long_basket"]) >= 2
    assert len(orders["short_basket"]) >= 2
