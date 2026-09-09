import os
import numpy as np
import polars as pl
import pytest
from dagster import build_asset_context

from pipeline.assets.research_assets import market_regime_features, trained_meta_learner


def test_research_assets_end_to_end_mock():
    # 1. Create mock clean trades file
    mock_trades_path = "/tmp/lake/clean/mock_trades.parquet"
    os.makedirs(os.path.dirname(mock_trades_path), exist_ok=True)
    import numpy as np
    n = 60
    pl.DataFrame({
        "symbol": ["BTC"] * n,
        "price": [100.0 + np.sin(i / 3.0) * 2.0 + float(i) * 0.1 for i in range(n)],
        "size": [1.0 + (i % 3) * 0.5 for i in range(n)],
        "timestamp_ms": [1700000000000 + i * 60_000 for i in range(n)],
    }).write_parquet(mock_trades_path)
    # 2. Execute market_regime_features asset
    context = build_asset_context()
    regime_output = market_regime_features(context, [mock_trades_path])
    assert os.path.exists(regime_output.value)

    # 3. Execute trained_meta_learner asset
    model_output = trained_meta_learner(context, regime_output.value)
    assert os.path.exists(model_output.value)
    assert "val_brier_score" in model_output.metadata
