import polars as pl
import pytest
from pipeline.dqg.validator import DataQualityGate, DQGState


def test_dqg_crossed_book_detection():
    gate = DataQualityGate(max_crossed_ratio_tol=0.0)
    
    data = {
        "timestamp_ms": [1000, 1100, 1200, 1300],
        "symbol": ["BTC", "BTC", "BTC", "BTC"],
        "best_bid": [100.0, 101.0, 105.0, 102.0],
        "best_ask": [102.0, 103.0, 104.0, 104.0],
        "bid_size_l1": [1.0, 1.0, 1.0, 1.0],
        "ask_size_l1": [1.0, 1.0, 1.0, 1.0],
        "bid_depth_l5": [5.0, 5.0, 5.0, 5.0],
        "ask_depth_l5": [5.0, 5.0, 5.0, 5.0],
    }
    df = pl.DataFrame(data, schema_overrides={"best_bid": pl.Float32, "best_ask": pl.Float32})
    evaluated_df, report = gate.validate_l2_snapshots(df)
    
    states = evaluated_df["dqg_state"].to_list()
    assert states[0] == DQGState.VALID.value
    assert states[2] == DQGState.CROSSED_INVALID.value
    assert not report.is_partition_accepted


def test_dqg_trade_monotonicity():
    gate = DataQualityGate()
    
    data = {
        "timestamp_ms": [1000, 1050, 1020, 1100],
        "symbol": ["ETH", "ETH", "ETH", "ETH"],
        "side": ["BUY", "BUY", "SELL", "BUY"],
        "price": [2000.0, 2001.0, 2000.5, 2002.0],
        "size": [0.5, 0.5, 0.5, 0.5],
        "trade_id": ["1", "2", "3", "4"]
    }
    df = pl.DataFrame(data)
    evaluated_df, report = gate.validate_trades(df)
    
    states = evaluated_df["dqg_state"].to_list()
    assert states[2] == DQGState.CROSSED_INVALID.value
