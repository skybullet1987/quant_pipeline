#!/usr/bin/env python3
"""
Unit tests for Polymarket Live Execution Client and Pre-Trade Risk Filters.
"""

import pytest
from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor


def test_dynamic_fee_calculation():
    executor = PolymarketLiveExecutor(dry_run=True)
    
    # Contract at $0.77: fee_rate = 0.07 * (1 - 0.77) = 0.0161 (1.61%)
    rate, fee_usd = executor.calculate_dynamic_crypto_fee(0.77, 50.0)
    assert abs(rate - 0.0161) < 1e-4
    assert abs(fee_usd - 0.805) < 1e-4

    # Contract at $0.50: fee_rate = 0.07 * 0.50 = 0.035 (3.5%)
    rate, fee_usd = executor.calculate_dynamic_crypto_fee(0.50, 100.0)
    assert abs(rate - 0.035) < 1e-4
    assert abs(fee_usd - 3.50) < 1e-4

    # Contract at $0.90: fee_rate = 0.07 * 0.10 = 0.007 (0.7%)
    rate, fee_usd = executor.calculate_dynamic_crypto_fee(0.90, 50.0)
    assert abs(rate - 0.007) < 1e-4
    assert abs(fee_usd - 0.35) < 1e-4


def test_depth_guard_validation():
    executor = PolymarketLiveExecutor(dry_run=True)

    # Mock orderbook with sufficient depth ($100 available vs $50 target -> 2.0x >= 1.50x)
    good_book = {
        "asks": [
            {"price": "0.75", "size": "80"},
            {"price": "0.76", "size": "60"},
        ]
    }
    passed, ratio, best_px = executor.verify_pre_trade_depth(good_book, target_notional_usd=50.0, side="BUY")
    assert passed is True
    assert ratio > 1.50
    assert best_px == 0.75

    # Mock orderbook with thin depth ($20 available vs $50 target -> 0.4x < 1.50x)
    thin_book = {
        "asks": [
            {"price": "0.75", "size": "10"},
            {"price": "0.76", "size": "15"},
        ]
    }
    passed, ratio, best_px = executor.verify_pre_trade_depth(thin_book, target_notional_usd=50.0, side="BUY")
    assert passed is False
    assert ratio < 1.50


def test_dry_run_snipe_execution(tmp_path):
    ledger = tmp_path / "test_orders.jsonl"
    executor = PolymarketLiveExecutor(dry_run=True, ledger_path=str(ledger))

    # Mock get_market_book
    executor.get_market_book = lambda tid: {
        "asks": [
            {"price": "0.80", "size": "150"},
            {"price": "0.81", "size": "100"},
        ]
    }

    res = executor.execute_snipe_order(
        trade_id="TEST_TRADE_001",
        token_id="12345",
        target_token="UP",
        notional_usd=50.0,
        target_price=0.80,
    )

    assert res.success is True
    assert res.mode == "DRY_RUN_SIMULATION"
    assert res.size == 62.5
    assert res.fee_usd > 0
    assert ledger.exists()
