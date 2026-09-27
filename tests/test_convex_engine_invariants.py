#!/usr/bin/env python3
"""
Unit and Invariant Tests for the 10x+ Convex Compounding Architecture (EXP-102 Standard)
under IronCore v2.4.0 Execution Physics.
"""

import math
import numpy as np
import pytest

from src.strategy.convex_10x_engine import (
    IronCoreEngine,
    MachineState,
    PositionRecord,
    round_sz,
    round_px,
    validate_l1_order,
    compute_continuous_bipower_variation,
    compute_hurst_exponent,
    compute_variance_ratio,
    determine_holding_lock_duration,
)


def test_hyperliquid_l1_quantization_invariants():
    # 1. Test size rounding: floor strictly to sz_decimals
    assert round_sz(1.23456, 2) == 1.23
    assert round_sz(0.00999, 2) == 0.00
    assert round_sz(125.9, 0) == 125.0
    assert round_sz(0.0004567, 5) == 0.00045

    # 2. Test price rounding: <= 5 sig figs and <= 6 - sz_decimals
    # Example: BTC (sz_dec = 4) -> max_decimals = 6 - 4 = 2
    # Price 64231.456 -> magnitude = 4, sig_figs = 5 -> target_decimals = min(2, 0) = 0 -> 64231.0
    px_btc = round_px(64231.456, 4)
    assert px_btc == 64231.0

    # Example: Altcoin (sz_dec = 0) -> max_decimals = 6
    # Price 0.00123456 -> magnitude = -3, sig_fig_decimals = 5 - (-3) - 1 = 7 -> target_decimals = min(6, 7) = 6
    px_alt = round_px(0.00123456, 0)
    assert px_alt == 0.001235

    # 3. Test L1 order validation
    # Under $10.00 notional: reject
    valid, msg, q_px, q_sz = validate_l1_order("ETH", 3000.0, 0.002, 3) # Notional = $6.00
    assert not valid
    assert "below $10.00" in msg

    # Valid notional ($30.00): accept
    valid, msg, q_px, q_sz = validate_l1_order("ETH", 3000.0, 0.010, 3)
    assert valid
    assert msg == "VALID"
    assert q_px == 3000.0
    assert q_sz == 0.010


def test_bipower_variation_jump_disentanglement():
    np.random.seed(42)
    # Generate 100 continuous returns (std ~ 0.01)
    returns = np.random.normal(0, 0.01, 100)
    # Inject 3 large Poisson jump shocks
    returns[20] = 0.15
    returns[50] = -0.12
    returns[80] = 0.18

    cont_vol, jump_vol = compute_continuous_bipower_variation(returns)
    assert cont_vol > 0.0
    assert jump_vol > 0.0
    # Continuous vol must be significantly smaller than raw realized volatility due to jump filtering
    raw_rv = float(np.sum(returns ** 2))
    raw_vol = math.sqrt(raw_rv) * math.sqrt(2190)
    assert cont_vol < raw_vol


def test_hurst_and_variance_ratio_regime_mapping():
    # Trending series: cumulative sum of positive drift
    trend_returns = np.ones(50) * 0.01 + np.random.normal(0, 0.001, 50)
    h_trend = compute_hurst_exponent(trend_returns)
    assert h_trend > 0.50

    # Test lock duration mapping
    assert determine_holding_lock_duration(0.70, 1.30) == 42 # Super-persistent (168H)
    assert determine_holding_lock_duration(0.60, 1.10) == 18 # Persistent (72H)
    assert determine_holding_lock_duration(0.50, 1.00) == 6  # Diffusive (24H)
    assert determine_holding_lock_duration(0.40, 0.80) == 0  # Mean-reverting (0H)


def test_grossman_zhou_cushion_governor():
    symbols = ["BTC", "ETH"]
    sz_dec = {"BTC": 4, "ETH": 3}
    engine = IronCoreEngine(symbols, sz_dec, initial_nav=10000.0, m_drawdown_floor=0.20, max_leverage=3.50)

    # At peak HWM ($10,000): Cushion ratio = 1.0 -> Gearing = 3.50x
    assert engine.update_grossman_zhou_cushion() == pytest.approx(3.50, abs=1e-3)

    # In 10% drawdown ($9,000): Floor is $8,000, Buffer is $2,000, Cushion is $1,000 -> Cushion ratio = 0.50
    # Gearing = 3.50 * (0.50)^0.75 = 3.50 * 0.5946 = 2.081x
    engine.nav = 9000.0
    gearing_dd = engine.update_grossman_zhou_cushion()
    assert 2.00 <= gearing_dd <= 2.15

    # Near 20% drawdown limit ($8,050): Cushion is $50 / $2,000 = 0.025 -> Gearing throttles near 0
    engine.nav = 8050.0
    gearing_floor = engine.update_grossman_zhou_cushion()
    assert gearing_floor < 0.30

    # At or below floor ($8,000): Gearing = 0.0x cash
    engine.nav = 7990.0
    assert engine.update_grossman_zhou_cushion() == 0.0


def test_6_bucket_ledger_conservation():
    symbols = ["BTC", "ETH"]
    sz_dec = {"BTC": 4, "ETH": 3}
    engine = IronCoreEngine(symbols, sz_dec, initial_nav=10000.0)

    # Simulate some transactions
    engine.ledger["gross_price_pnl"] = 520.50
    engine.ledger["funding_pnl"] = 45.20
    engine.ledger["exchange_fees"] = 12.30
    engine.ledger["market_impact"] = 8.40
    engine.ledger["adverse_selection"] = 0.0
    engine.ledger["realized_stop_slippage"] = 0.0

    net_delta = 520.50 + 45.20 - 12.30 - 8.40
    engine.nav = engine.initial_nav + net_delta

    is_conserved, discrepancy = engine.audit_ledger_identity()
    assert is_conserved
    assert discrepancy < 1e-12
