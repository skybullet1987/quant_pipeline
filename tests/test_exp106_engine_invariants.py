#!/usr/bin/env python3
"""
Unit & Invariant Test Suite for EXP-106 Sovereign Unconstrained Compounding Engine.
Verifies directional momentum, unconstrained QP portfolio optimization,
Arm B5 acute macro beta overlay, milestone vaulting, and exact 6-bucket mark-to-market ledger balance.
"""

import math
import numpy as np
import pytest

from src.strategy.convex_106_unconstrained_engine import (
    Exp106UnconstrainedEngine,
    BalanceSheet6Bucket,
    Position,
    RegimePhase,
    UnconstrainedQPSolver,
    round_px,
    round_sz,
    validate_l1_order,
)


def test_l1_consensus_quantization():
    """Verify Hyperliquid Layer 1 consensus quantization rules."""
    px = 123.456789
    q_px = round_px(px, sz_decimals=2)
    assert q_px == 123.46

    btc_px = 62345.67
    q_btc = round_px(btc_px, sz_decimals=4)
    assert q_btc == 62346.0

    pepe_px = 0.0000123456
    q_pepe = round_px(pepe_px, sz_decimals=0)
    assert q_pepe == 0.000012

    sz = 1.2399
    q_sz = round_sz(sz, sz_decimals=2)
    assert q_sz == 1.23

    valid = validate_l1_order(px=150.0, sz=0.05, sz_decimals=2)
    assert not valid

    valid = validate_l1_order(px=150.0, sz=0.10, sz_decimals=2)
    assert valid


def test_6bucket_balance_sheet_identity():
    """Verify exact 6-bucket mark-to-market ledger identity."""
    ledger = BalanceSheet6Bucket(initial_capital=10000.0, nav_usd=10000.0)

    ledger.gross_trading_pnl_usd = 4500.0
    ledger.funding_pnl_usd = 120.0
    ledger.maker_fees_usd = 45.0
    ledger.taker_fees_usd = 30.0
    ledger.base_slippage_usd = 25.0
    ledger.market_impact_usd = 15.0

    expected_nav = 10000.0 + 4500.0 + 120.0 - 45.0 - 30.0 - 25.0 - 15.0
    ledger.nav_usd = expected_nav

    discrepancy = ledger.reconcile_ledger()
    assert discrepancy < 1e-10


def test_fractional_diff_alpha_and_fip():
    """Step 1: Verify fractional differentiation alpha computation and FIP filtering."""
    symbols = ["BTC", "ETH", "SOL", "AVAX"]
    engine = Exp106UnconstrainedEngine(symbols=symbols, initial_capital=10000.0)

    # 18-bar synthetic price window
    np.random.seed(42)
    close_window = np.ones((18, 4)) * 100.0
    # SOL has strong upward trend
    close_window[:, 2] = np.linspace(80.0, 140.0, 18)
    returns_window = np.diff(close_window, axis=0, prepend=close_window[0:1]) / close_window

    tradable_mask = np.array([True, True, True, True])
    alpha_vec = engine.compute_fractional_diff_alpha(
        close_window=close_window,
        returns_window=returns_window,
        tradable_mask=tradable_mask
    )

    assert len(alpha_vec) == 4
    # SOL has the highest momentum, so its alpha must be strongly positive
    assert alpha_vec[2] > 0
    assert alpha_vec[2] == np.max(alpha_vec)


def test_unconstrained_qp_solver():
    """Step 2: Verify unconstrained QP solver allows natural beta and no alt penalties."""
    symbols = ["BTC", "ETH", "SOL", "AVAX", "LINK"]
    solver = UnconstrainedQPSolver(n_symbols=5, gamma=1.0, lambda_turnover=0.85)

    alpha_vec = np.array([0.01, 0.02, 0.05, 0.04, -0.01])
    cov_matrix = np.eye(5) * 0.04
    w_prev = np.zeros(5)
    tradable_mask = np.ones(5, dtype=bool)

    w_opt = solver.solve(
        alpha_vec=alpha_vec,
        cov_matrix=cov_matrix,
        w_prev=w_prev,
        gross_target=3.0,
        tradable_mask=tradable_mask,
        single_name_cap=0.25
    )

    gross_exposure = np.sum(np.abs(w_opt))
    assert gross_exposure > 0.0
    # Top alphas (SOL=index 2, AVAX=index 3) should have positive allocations
    assert w_opt[2] > 0.0
    assert w_opt[3] > 0.0
    # Non-tradable check
    tradable_mask[4] = False
    w_masked = solver.solve(
        alpha_vec=alpha_vec,
        cov_matrix=cov_matrix,
        w_prev=w_prev,
        gross_target=3.0,
        tradable_mask=tradable_mask,
        single_name_cap=0.25
    )
    assert w_masked[4] == 0.0


def test_arm_b5_acute_macro_hedge():
    """Step 4: Verify Arm B5 acute hedge triggers on cascade and instantly unwinds."""
    symbols = ["BTC", "ETH", "SOL"]
    engine = Exp106UnconstrainedEngine(symbols=symbols, initial_capital=10000.0)

    rolling_betas = np.array([1.0, 1.2, 1.8])
    active_weights = np.array([0.5, 0.5, 1.0]) # Total 2.0x weight

    # Case 1: Normal conditions -> Hedge stays dormant
    is_hedged, btc_notional, eth_notional = engine.evaluate_acute_macro_hedge(
        z_jump=0.5,
        v_oi=0.05,
        btc_ret_4h=0.01,
        btc_close=60000.0,
        btc_ema20=59000.0,
        btc_atr=1200.0,
        rolling_betas=rolling_betas,
        active_weights=active_weights,
        equity=10000.0
    )
    assert not is_hedged
    assert btc_notional == 0.0
    assert eth_notional == 0.0

    # Case 2: Acute cascade (Z_jump = 2.1 > 1.645 and btc_ret < -1.5 ATR)
    is_hedged, btc_notional, eth_notional = engine.evaluate_acute_macro_hedge(
        z_jump=2.1,
        v_oi=-0.12,
        btc_ret_4h=-0.04,
        btc_close=57000.0,
        btc_ema20=60000.0,
        btc_atr=1200.0,
        rolling_betas=rolling_betas,
        active_weights=active_weights,
        equity=10000.0
    )
    assert is_hedged
    assert btc_notional < 0.0 # Short BTC
    assert eth_notional < 0.0 # Short ETH
    assert engine.regime_phase == RegimePhase.ACUTE_TAIL_SHIELD

    # Case 3: Instantaneous de-escalation on rebound (r_btc > +0.5 ATR)
    is_hedged, btc_notional, eth_notional = engine.evaluate_acute_macro_hedge(
        z_jump=0.2,
        v_oi=0.02,
        btc_ret_4h=+0.025, # > 0.5 ATR
        btc_close=58500.0,
        btc_ema20=59000.0,
        btc_atr=1200.0,
        rolling_betas=rolling_betas,
        active_weights=active_weights,
        equity=10000.0
    )
    assert not is_hedged
    assert btc_notional == 0.0
    assert eth_notional == 0.0
    assert engine.regime_phase == RegimePhase.DEESCALATION_RECOVERY


def test_milestone_vaulting():
    """Step 5: Verify milestone reserve sweeping at doubling thresholds."""
    symbols = ["BTC", "ETH"]
    engine = Exp106UnconstrainedEngine(
        symbols=symbols,
        initial_capital=10000.0,
        vault_milestones_enabled=True,
        vault_sweep_pct=0.25
    )

    # Below 2x milestone ($20,000)
    sweep_1 = engine.check_milestone_vault(15000.0)
    assert sweep_1 == 0.0
    assert engine.ledger.vault_reserve_usd == 0.0

    # Cross 2x milestone ($20,000)
    sweep_2 = engine.check_milestone_vault(20500.0)
    # Profit above base is $10,500 -> 25% is $2,625
    assert sweep_2 == 2625.0
    assert engine.ledger.vault_reserve_usd == 2625.0
    assert engine.next_vault_milestone == 40000.0
