import polars as pl
from datetime import datetime, timedelta
from src.features.engine import FeatureEngineeringEngine

def test_feature_pipeline():
    dates = [datetime(2026, 1, 1) + timedelta(hours=h) for h in range(0, 400, 4)]
    tickers = ["BTCUSD", "ETHUSD", "SOLUSD", "AVAXUSD"]
    
    records = []
    for t in tickers:
        for i, d in enumerate(dates):
            records.append({
                "timestamp": d,
                "ticker": t,
                "open": 100.0 + i,
                "high": 105.0 + i,
                "low": 95.0 + i,
                "close": 102.0 + i,
                "volume": 1000.0
            })
            
    df = pl.DataFrame(records)
    engine = FeatureEngineeringEngine(forward_horizon_bars=6, lookback_bars=20)
    
    df_feat = engine.compute_ohlcv_features(df)
    assert "gk_vol_20p" in df_feat.columns
    assert "vol_compression_ratio" in df_feat.columns
    
    df_res = engine.residualize_against_market(df_feat)
    assert "beta_btc" in df_res.columns
    assert "residual_momentum_zscore" in df_res.columns
    
    df_target = engine.construct_ranking_targets(df_res)
    assert "ranking_target" in df_target.columns
