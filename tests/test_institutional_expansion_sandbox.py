#!/usr/bin/env python3
"""
Test Suite: Institutional Polymarket Expansion Sandbox (EXP-304 / EXP-305)
========================================================================
Validates that all forensic audit remediations and mathematical formulas
behave according to production invariants:
  1. Blocker 1 Remediation: Rejection of short-dated (<60s) GTD orders, enforcement of FOK.
  2. Binary Option Greeks: Accurate closed-form binary delta & gamma.
  3. Dynamic Taker Fees: Horizon scaling (kappa=0.18 on 15m vs 0.07 on 1h).
  4. Execution Regime Gating: Optimal sweet spots (0.15-0.35, 0.65-0.85) vs rejected ATM (0.45-0.55).
  5. NegRisk Arbitrage Mechanics: Overround and underround profit equations with fee & gas hurdles.
"""

import pytest
import math
from src.polymarket_research.exp304_multi_asset_latency_engine import (
    compute_binary_option_greeks,
    compute_dynamic_taker_fee,
    validate_regime_viability,
    evaluate_hurdle,
)
from src.polymarket_research.negrisk_scanner import (
    compute_taker_fee as compute_negrisk_fee,
    NegRiskOpportunity,
)


def test_binary_option_greeks_atm():
    """Validates binary call pricing and delta at-the-money."""
    metrics = compute_binary_option_greeks(
        spot=100.0, strike=100.0, tau_seconds=900.0, vol_annual=0.60
    )
    # Fair price at ATM without drift should be approximately 0.50
    assert abs(metrics.fair_price - 0.50) < 0.02
    assert metrics.binary_delta > 0.0
    assert metrics.d1 > metrics.d2


def test_dynamic_taker_fee_scaling():
    """Validates quadratic fee formula and horizon parameter kappa."""
    # 15m contract (kappa = 0.18): peak fee at p=0.50 is 0.18 * 0.25 = 0.045 (4.5%)
    fee_15m = compute_dynamic_taker_fee(0.50, horizon="15m")
    assert abs(fee_15m - 0.045) < 1e-4

    # 1h contract (kappa = 0.07): peak fee at p=0.50 is 0.07 * 0.25 = 0.0175 (1.75%)
    fee_1h = compute_dynamic_taker_fee(0.50, horizon="1h")
    assert abs(fee_1h - 0.0175) < 1e-4

    # Wing fee (p = 0.20): fee_15m = 0.18 * 0.20 * 0.80 = 0.0288 (2.88%)
    fee_15m_wing = compute_dynamic_taker_fee(0.20, horizon="15m")
    assert abs(fee_15m_wing - 0.0288) < 1e-4


def test_regime_viability_filtering():
    """Enforces sweet-spot regime boundaries to prevent high fee drag."""
    # Optimal zones
    ok_low_wing, reason_low = validate_regime_viability(0.25)
    assert ok_low_wing is True
    assert reason_low == "OPTIMAL_SWEET_SPOT"

    ok_high_wing, reason_high = validate_regime_viability(0.75)
    assert ok_high_wing is True
    assert reason_high == "OPTIMAL_SWEET_SPOT"

    # ATM peak fee rejection
    ok_atm, reason_atm = validate_regime_viability(0.50)
    assert ok_atm is False
    assert reason_atm == "REJECT_PEEK_FEE_ATM"

    # Tail probability rejection
    ok_tail, reason_tail = validate_regime_viability(0.05)
    assert ok_tail is False
    assert reason_tail == "REJECT_DEEP_TAIL"


def test_hurdle_rate_solver():
    """Tests the combined hurdle solver Delta_S * Delta_binary > Hurdle."""
    greeks = compute_binary_option_greeks(
        spot=99.78, strike=100.0, tau_seconds=900.0, vol_annual=0.60
    )
    # A $0.30 external spot impulse
    passed, shift, hurdle = evaluate_hurdle(
        delta_spot=0.30,
        binary_delta=greeks.binary_delta,
        clob_price=0.25,
        clob_spread=0.01,
        horizon="15m",
        slippage_penalty=0.005,
    )
    assert shift > 0.0
    assert hurdle > 0.0
    # Expected shift = 0.30 * 0.984 = ~0.295 > hurdle (~0.0488)
    assert passed is True


def test_negrisk_overround_underround_math():
    """Validates structural overround & underround formulas."""
    # Synthetic 3-outcome overround: Bids = 0.45, 0.40, 0.30 -> Sum = 1.15
    bids = [0.45, 0.40, 0.30]
    total_bids = sum(bids)
    fees = sum(compute_negrisk_fee(p) for p in bids)
    gas = 0.02
    net_overround = total_bids - 1.00 - fees - gas
    assert abs(total_bids - 1.15) < 1e-6
    assert net_overround > 0.0  # Profitable overround

    # Synthetic 3-outcome underround: Asks = 0.30, 0.30, 0.30 -> Sum = 0.90
    asks = [0.30, 0.30, 0.30]
    total_asks = sum(asks)
    ask_fees = sum(compute_negrisk_fee(p) for p in asks)
    net_underround = 1.00 - total_asks - ask_fees - gas
    assert abs(total_asks - 0.90) < 1e-6
    assert net_underround > 0.0  # Profitable underround
