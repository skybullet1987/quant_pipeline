import numpy as np
import pytest
from pipeline.strategy.allocator import PureStrategyCore
from pipeline.strategy.expectancy import ExpectancyEngine
from pipeline.strategy.state import FeatureState, IntentSide, RawMarketState, RegimeState


def test_expectancy_engine_funding_and_fee_deduction():
    engine = ExpectancyEngine(maker_fee_pct=-0.00005, default_slippage_pct=0.0001)
    
    # 60% win rate, 1% gain vs 1% loss
    metrics = engine.evaluate_expectancy(
        win_prob=0.60,
        expected_gain_pct=0.01,
        expected_loss_pct=0.01,
        current_funding_rate=0.0005,       # High positive funding rate (long pays)
        predicted_funding_rate=0.0005,
        is_long=True,
        notional_usd=10000.0,
        holding_horizon_hours=1.0,
        is_maker=True
    )

    # Raw return: 0.6*0.01 - 0.4*0.01 = 0.0020 (20 bps)
    # Funding drag: ~0.0005 (5 bps)
    # Maker rebate: +0.00005 (+0.5 bps)
    # Expected net return: ~0.00155 (15.5 bps)
    assert metrics.is_positive_ev
    assert 0.0014 < metrics.ev_return_pct < 0.0017
    assert metrics.ev_dollar > 14.0


def test_pure_strategy_core_zero_io_execution():
    core = PureStrategyCore(min_ev_bps_threshold=2.0)

    market = RawMarketState(
        timestamp_ns=1700000000000000000,
        symbol="BTC",
        best_bid=50000.0,
        best_ask=50000.5,
        mid_price=50000.25,
        last_trade_price=50000.25,
        bid_depth_l5=20.0,
        ask_depth_l5=20.0,
        funding_rate_hourly=0.00001,
        predicted_funding_next=0.00001,
    )

    features = FeatureState(
        timestamp_ns=1700000000000000000,
        symbol="BTC",
        log_ret_1m=0.0005,
        rvol_15m=0.15,
        rvol_1h=0.18,
        natr_14m=0.002,
        order_flow_imbalance=0.25,
        vwap_basis_bps=1.5,
        cvd_15m=150.0,
        volume_zscore_60m=1.2,
    )

    regime = RegimeState(
        timestamp_ns=1700000000000000000,
        symbol="BTC",
        p_trend=0.75,
        p_chop=0.20,
        p_expansion=0.05,
        p_hazard=0.02,
        long_permission=0.98,
        short_permission=0.98,
        regime_multiplier=1.10,
    )

    intent = core.process(
        market=market,
        features=features,
        regime=regime,
        raw_win_prob=0.62,
        expected_gain_pct=0.008,
        expected_loss_pct=0.006,
        total_equity_usd=10000.0
    )

    assert intent.target_side == IntentSide.LONG
    assert intent.target_weight > 0.0
    assert intent.target_notional_usd > 0.0
    assert intent.limit_price_ref == 50000.0
    assert intent.metadata["net_edge_bps"] > 2.0
