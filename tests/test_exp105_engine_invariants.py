#!/usr/bin/env python3
"""
Unit & Invariant Test Suite for EXP-105 Sovereign Compounding Engine.
Verifies all 3 deep research vectors, Hyperliquid L1 consensus quantization,
and 6-bucket mark-to-market ledger balance sheet conservation identity (|eps| < 10^-10).
"""

import math
import numpy as np
import pytest

from src.strategy.convex_105_sovereign_engine import (
    Exp105SovereignEngine,
    BalanceSheet6Bucket,
    Position,
    RegimePhase,
    round_px,
    round_sz,
    validate_l1_order,
)


def test_l1_consensus_quantization():
    """Verify Hyperliquid Layer 1 consensus quantization rules."""
    # szDecimals = 2 -> max decimals = 4, sig figs <= 5
    px = 123.456789
    q_px = round_px(px, sz_decimals=2)
    assert q_px == 123.46  # 5 sig figs: 1,2,3,4,6

    # High price asset: BTC ($62,345.67) -> 5 sig figs means 62346
    btc_px = 62345.67
    q_btc = round_px(btc_px, sz_decimals=4)
    assert q_btc == 62346.0

    # Low price asset: PEPE ($0.0000123456) -> max decimals = 6 - 0 = 6
    pepe_px = 0.0000123456
    q_pepe = round_px(pepe_px, sz_decimals=0)
    assert q_pepe == 0.000012

    # Size quantization: floor
    sz = 1.2399
    q_sz = round_sz(sz, sz_decimals=2)
    assert q_sz == 1.23

    # Min notional validation
    valid = validate_l1_order(px=150.0, sz=0.05, sz_decimals=2)  # $7.50 < $10
    assert not valid

    valid = validate_l1_order(px=150.0, sz=0.10, sz_decimals=2)  # $15.00 >= $10
    assert valid


def test_continuous_cushion_governor_and_asymmetric_regearing():
    """Vector A: Verify continuous power-law cushion scaling with decoupled exponents."""
    engine = Exp105SovereignEngine(
        symbols=["BTC", "ETH", "SOL"],
        initial_capital=10000.0,
        theta_giveback=0.18,
        leverage_base=1.0,
        leverage_max=3.25
    )

    # Initial state: NAV = $10,000, Floor = $8,200, Cushion = $1,800, c_ratio = 1.0
    assert engine.ledger.nav_usd == 10000.0
    assert engine.ledger.capital_floor == 8200.0

    # Case 1: Rebound scenario (W_t > W_{t-6}) with confirmed trend
    # NAV surges to $50,000 from $40,000 6 bars ago
    engine.ledger.nav_usd = 50000.0
    engine.ledger.ratcheted_hwm = 50000.0
    lev = engine.update_continuous_cushion_governor(
        current_bar=50,
        peak_bar=50,
        nav_6bars_ago=40000.0,
        btc_adx=28.0,
        btc_price=65000.0,
        btc_ema50=60000.0
    )
    assert engine.regime == RegimePhase.FAST_REBOUND
    # c_ratio = 1.0, Q_trend ~ 0.88-1.0 -> leverage should approach max (3.25x)
    assert 2.90 <= lev <= 3.25

    # Case 2: Drawdown scenario (W_t <= W_{t-6})
    # NAV drops to $42,000 from $48,000 6 bars ago (Floor is 0.82 * 50k = $41,000)
    engine.ledger.nav_usd = 42000.0
    lev_dd = engine.update_continuous_cushion_governor(
        current_bar=56,
        peak_bar=50,
        nav_6bars_ago=48000.0,
        btc_adx=20.0,
        btc_price=58000.0,
        btc_ema50=60000.0
    )
    # Cushion is very thin ($42k - $41k = $1k), leverage must be throttled close to 1.0x
    assert lev_dd < 1.50
    assert lev_dd >= 1.0


def test_multi_beta_residualization_and_fip_filter():
    """Vector B: Verify multi-beta OLS residualization and FIP jump filtering."""
    np.random.seed(42)
    t_len = 60
    n_assets = 5
    btc_idx = 0
    eth_idx = 1

    engine = Exp105SovereignEngine(
        symbols=["BTC", "ETH", "SOL", "AVAX", "PUMP_TOKEN"],
        initial_capital=10000.0
    )

    # Synthetic returns
    r_btc = np.random.normal(0.001, 0.02, t_len)
    r_eth = 0.8 * r_btc + np.random.normal(0.0, 0.015, t_len)
    r_sol = 1.2 * r_btc + 0.3 * r_eth + np.random.normal(0.002, 0.025, t_len)
    r_avax = 0.9 * r_btc + 0.4 * r_eth + np.random.normal(0.001, 0.02, t_len)

    # Pump token: single massive wick at t=55 (80% of all drift)
    r_pump = 0.5 * r_btc + np.random.normal(0.0, 0.01, t_len)
    r_pump[55] += 0.35  # huge 35% single-candle pump

    rets_mat = np.column_stack([r_btc, r_eth, r_sol, r_avax, r_pump])

    z_alpha = engine.compute_idiosyncratic_residual_momentum(
        returns_window_60=rets_mat,
        btc_idx=btc_idx,
        eth_idx=eth_idx
    )

    # PUMP_TOKEN (index 4) has JumpRatio > 0.40, so its alpha must be zeroed out
    assert z_alpha[4] == 0.0
    # SOL has positive residual drift without outlier jump, so z_alpha should be non-zero
    assert abs(z_alpha[2]) > 0.0


def test_calibrated_4h_bipower_jump_hedging_and_instant_unwind():
    """Vector C: Verify calibrated 4H Bipower Jump Gate (Threshold: 1.645) & Instant Unwinding."""
    engine = Exp105SovereignEngine(symbols=["BTC", "ETH"], initial_capital=10000.0)

    # Normal calm market returns
    calm_rets = np.full(18, 0.002)
    stress = engine.evaluate_4h_bipower_jump_hedging(
        btc_rets_18=calm_rets,
        v_oi_24h=0.05,
        r_btc_4h=0.005,
        btc_atr=1000.0,
        btc_price=60000.0,
        btc_ema20=59000.0
    )
    assert not stress
    assert not engine.ledger.hedge_active

    # Jump cascade: severe negative return exceeding 1 ATR with high jump score
    cascade_rets = np.array([0.001]*15 + [0.08, -0.09, -0.06])
    stress_cascade = engine.evaluate_4h_bipower_jump_hedging(
        btc_rets_18=cascade_rets,
        v_oi_24h=-0.15,
        r_btc_4h=-0.04,  # -4% drop
        btc_atr=1200.0,
        btc_price=60000.0,
        btc_ema20=62000.0
    )
    assert stress_cascade
    assert engine.ledger.hedge_active
    assert engine.regime == RegimePhase.TAIL_CASCADE

    # Immediate rebound bar: r_btc > +0.5 ATR and Price > EMA20 -> instant unwinding!
    unwind_check = engine.evaluate_4h_bipower_jump_hedging(
        btc_rets_18=cascade_rets,
        v_oi_24h=0.02,
        r_btc_4h=0.025,  # +2.5% recovery candle
        btc_atr=1200.0,
        btc_price=63000.0,
        btc_ema20=62000.0
    )
    assert not unwind_check
    assert not engine.ledger.hedge_active
    assert engine.regime == RegimePhase.FAST_REBOUND


def test_dynamic_turnover_regularizer():
    """Vector B: Verify dynamic QP turnover regularization scaling."""
    engine = Exp105SovereignEngine(symbols=["BTC"], initial_capital=10000.0)
    lam_initial = engine.compute_dynamic_turnover_regularizer(btc_vol_current=0.02, btc_vol_baseline=0.02)
    assert 0.85 <= lam_initial <= 2.0

    # When equity compounds to $100k and volatility doubles, lambda must increase
    engine.ledger.nav_usd = 100000.0
    lam_expanded = engine.compute_dynamic_turnover_regularizer(btc_vol_current=0.05, btc_vol_baseline=0.02)
    assert lam_expanded > lam_initial


def test_6bucket_ledger_reconciliation_zero_leakage():
    """Verify 6-bucket mark-to-market balance sheet ledger identity (|eps| < 10^-10 USDC)."""
    ledger = BalanceSheet6Bucket(
        nav_usd=10000.0,
        initial_capital=10000.0
    )

    # Simulate trading events
    ledger.gross_price_pnl = 15234.56789012
    ledger.funding_pnl = 145.23450000
    ledger.exchange_fees = 120.45000000
    ledger.market_impact = 35.12000000
    ledger.adverse_selection = 12.00000000
    ledger.realized_stop_slippage = 45.50000000

    # Expected NAV
    expected_nav = (
        ledger.initial_capital
        + ledger.gross_price_pnl
        + ledger.funding_pnl
        - ledger.exchange_fees
        - ledger.market_impact
        - ledger.adverse_selection
        - ledger.realized_stop_slippage
    )
    ledger.nav_usd = expected_nav

    discrepancy = ledger.verify_ledger_invariants()
    assert discrepancy < 1e-10
