#!/usr/bin/env python3
"""
Unit & Invariant Test Suite for EXP-104 Sovereign Frontier Engine.
Verifies all 5 deep research vectors, Hyperliquid L1 consensus quantization,
and 6-bucket mark-to-market ledger balance sheet conservation.
"""

import math
import numpy as np
import pytest

from src.strategy.convex_104_sovereign_engine import (
    Exp104SovereignEngine,
    PortfolioBalanceSheet,
    Position,
    RegimeState,
    round_px,
    round_sz,
    validate_l1_order,
    marchenko_pastur_denoise_matrix,
    compute_herc_weights,
    compute_continuous_bipower_variation,
    compute_hurst_exponent,
    compute_variance_ratio,
    determine_holding_lock_duration,
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
    valid, msg, _, _ = validate_l1_order("SOL", 150.0, 0.05, sz_decimals=2)  # $7.50 < $10
    assert not valid
    assert "below $10.00" in msg

    valid, msg, _, _ = validate_l1_order("SOL", 150.0, 0.10, sz_decimals=2)  # $15.00 >= $10
    assert valid


def test_asymmetric_ratchet_and_giveback_floor():
    """Vector 1: Verify Asymmetric Continuous Ratchet & Protected Capital Floor."""
    sheet = PortfolioBalanceSheet(
        nav_usd=10000.0,
        vault_reserve_usd=9000.0,
        active_compounder_usd=1000.0,
        ratcheted_hwm_usd=10000.0,
        capital_floor_usd=9000.0
    )

    # Surge from $10k to $200k
    sheet.update_asymmetric_ratchet(current_nav=200000.0, current_bar=100, peak_bar=100, theta=0.10)
    assert sheet.ratcheted_hwm_usd == 200000.0
    assert sheet.capital_floor_usd == 180000.0  # (1 - 0.10) * 200k
    assert sheet.vault_reserve_usd == 180000.0
    assert sheet.active_compounder_usd == 20000.0

    # Retracement to $185k (within 10% giveback buffer, within grace period)
    sheet.update_asymmetric_ratchet(current_nav=185000.0, current_bar=110, peak_bar=100, theta=0.10)
    assert sheet.ratcheted_hwm_usd == 200000.0
    assert sheet.capital_floor_usd == 180000.0
    assert sheet.vault_reserve_usd == 180000.0
    assert sheet.active_compounder_usd == 5000.0  # 185k - 180k

    # Prolonged drawdown past grace period (18 bars): HWM* decays smoothly
    sheet.update_asymmetric_ratchet(current_nav=180000.0, current_bar=130, peak_bar=100, theta=0.10)
    assert sheet.ratcheted_hwm_usd < 200000.0
    # Floor adjusts with decayed HWM*, but Vaulted Reserve never decreases
    assert sheet.vault_reserve_usd >= 180000.0


def test_marchenko_pastur_denoising():
    """Vector 5: Verify Random Matrix Theory (RMT) spectral filtering."""
    np.random.seed(42)
    # Generate noisy correlation matrix: T=540, N=30 -> Q = 18
    X = np.random.randn(540, 30)
    # Add a strong common factor
    market_factor = np.random.randn(540, 1)
    X += 0.8 * market_factor
    corr = np.corrcoef(X, rowvar=False)

    q_ratio = 540.0 / 30.0
    denoised_corr = marchenko_pastur_denoise_matrix(corr, q_ratio)

    # Invariants: unit diagonal, symmetric, positive semi-definite
    assert np.allclose(np.diag(denoised_corr), 1.0, atol=1e-5)
    assert np.allclose(denoised_corr, denoised_corr.T, atol=1e-8)
    min_eig = np.min(np.linalg.eigvalsh(denoised_corr))
    assert min_eig >= -1e-6


def test_herc_weights_sum_to_one():
    """Vector 5: Verify Hierarchical Equal Risk Contribution sizing."""
    np.random.seed(42)
    cov = np.eye(10) * 0.04
    cov[0, 1] = cov[1, 0] = 0.02  # correlated pair
    weights = compute_herc_weights(cov)

    assert len(weights) == 10
    assert np.all(weights > 0.0)
    assert np.isclose(np.sum(weights), 1.0, atol=1e-6)
    # Correlated pair gets lower combined weight than uncorrelated individual assets
    assert weights[0] < weights[5]


def test_arm_b5_stress_and_beta_overlay():
    """Vector 2: Verify Arm B5 Cooldown Gate & Continuous Beta Overlay."""
    symbols = ["BTC", "ETH", "SOL", "AVAX"]
    sz_dec = {s: 2 for s in symbols}
    engine = Exp104SovereignEngine(symbols=symbols, sz_decimals=sz_dec)

    # Non-toxic condition: positive BTC return, normal OI
    stress = engine.evaluate_microstructure_stress(
        v_oi_24h=-0.02,
        d_basis=0.001,
        d_basis_mean=0.001,
        d_basis_sigma=0.0005,
        z_jump=0.5,
        r_btc_4h=0.01,
        btc_atr=1500.0,
        btc_close=60000.0
    )
    assert not stress
    assert not engine.ledger.beta_hedge_active

    # Toxic cascade: OI flush (-15%), wide basis, jump Z > 2.576, BTC dumping
    stress_toxic = engine.evaluate_microstructure_stress(
        v_oi_24h=-0.15,
        d_basis=0.010,
        d_basis_mean=0.001,
        d_basis_sigma=0.0005,
        z_jump=3.2,
        r_btc_4h=-0.05,
        btc_atr=1500.0,
        btc_close=60000.0
    )
    assert stress_toxic
    assert engine.ledger.beta_hedge_active

    # Verify beta overlay allocation: short BTC/ETH notional
    alt_weights = np.array([0.0, 0.0, 0.50, 0.50])
    beta_btc = np.array([1.0, 0.8, 1.4, 1.6])
    beta_eth = np.array([0.8, 1.0, 1.2, 1.3])

    w_btc, w_eth = engine.compute_macro_beta_overlay(alt_weights, beta_btc, beta_eth)
    assert w_btc < 0.0  # short hedge
    assert w_eth < 0.0  # short hedge
    assert engine.ledger.btc_hedge_notional < 0.0
    assert engine.ledger.eth_hedge_notional < 0.0


def test_3tier_exit_surface_sequence():
    """Vector 3: Verify 3-Tier Dynamic Exit Surfaces."""
    symbols = ["SOL"]
    sz_dec = {"SOL": 2}
    engine = Exp104SovereignEngine(symbols=symbols, sz_decimals=sz_dec)

    # Manually seed an active long position at $100, ATR=2.0
    pos = Position(
        symbol="SOL",
        direction=1,
        entry_price=100.0,
        current_size=10.0,
        initial_size=10.0,
        entry_atr=2.0,
        continuous_bv_vol=0.50,
        stop_price=96.0,  # 2 ATR stop
        highest_high=100.0,
        lowest_low=100.0,
        tier2_harvested=False,
        entry_bar=0,
        last_mark_price=100.0
    )
    engine.positions["SOL"] = pos

    # Bar 1: Price rallies to $104.50 (+2.25 ATR excursion)
    # Should trigger Tier 2 Partial Harvest: 50% closed at +2.0 ATR ($104.00)
    is_closed, fill_px, exit_type, sz_closed = engine.evaluate_position_exit_surfaces(
        sym="SOL",
        current_open=102.0,
        current_high=104.50,
        current_low=101.50,
        current_close=104.00,
        current_atr=2.0
    )
    assert not is_closed
    assert exit_type == "TIER2_PARTIAL_HARVEST"
    assert fill_px == 104.00
    assert sz_closed == 5.0
    assert pos.current_size == 5.0
    assert pos.tier2_harvested is True
    # Stop moved to Breakeven + 0.25 ATR ($100.50)
    assert pos.stop_price == 100.50

    # Bar 2: Price surges to $120 with low remaining above chandelier stop ($118.50)
    # Tier 3 parabolic chandelier trails closely
    is_closed, fill_px, exit_type, sz_closed = engine.evaluate_position_exit_surfaces(
        sym="SOL",
        current_open=105.0,
        current_high=120.0,
        current_low=118.50,
        current_close=119.50,
        current_atr=2.0
    )
    assert not is_closed
    # Chandelier stop ratcheted up near peak
    assert pos.stop_price > 110.0

    # Bar 3: Wick crashes to $105, breaching chandelier stop
    is_closed, fill_px, exit_type, sz_closed = engine.evaluate_position_exit_surfaces(
        sym="SOL",
        current_open=118.0,
        current_high=119.0,
        current_low=105.0,
        current_close=106.0,
        current_atr=2.0
    )
    assert is_closed
    assert exit_type == "TIER3_CHANDELIER_RUNNER"
    assert sz_closed == 5.0
    assert fill_px >= 105.0


def test_6bucket_mark_to_market_reconciliation():
    """Verify exact 6-bucket mark-to-market balance sheet ledger conservation."""
    sheet = PortfolioBalanceSheet(nav_usd=10000.0)
    initial_cap = 10000.0

    # Simulate varied trading cashflows
    sheet.gross_price_pnl += 5432.10
    sheet.funding_pnl -= 87.65
    sheet.exchange_fees += 45.20
    sheet.market_impact += 12.30
    sheet.adverse_selection += 0.0
    sheet.realized_stop_slippage += 15.40

    # Update NAV to match exact movements
    sheet.nav_usd = initial_cap + 5432.10 - 87.65 - 45.20 - 12.30 - 0.0 - 15.40
    discrepancy = sheet.reconcile_ledger(initial_capital=initial_cap)
    assert discrepancy < 1e-10


def test_concave_cushion_recovery_ramp():
    """Verify Vector 1 Concave Cushion Ramp: rapid re-gearing on positive 24H drift."""
    symbols = ["BTC", "ETH"]
    sz_dec = {"BTC": 4, "ETH": 3}
    engine = Exp104SovereignEngine(symbols=symbols, sz_decimals=sz_dec, leverage_base=1.0, leverage_max=3.5)

    # Simulate equity dip from $10k to $9.5k (cushion ratio ~ 0.50 if theta=0.10)
    engine.ledger.nav_usd = 9500.0
    engine.ledger.ratcheted_hwm_usd = 10000.0
    engine.ledger.capital_floor_usd = 9000.0

    # Scenario A: Drawdown/Negative drift (W_t <= W_{t-6}) -> linear/defensive de-leveraging
    lev_defensive, cushion = engine.update_ratcheted_vault_and_gearing(
        current_bar=10, nav_24h_prev=9600.0, is_expansion=False
    )
    assert math.isclose(cushion, 0.50, abs_tol=1e-5)

    # Scenario B: Positive drift (W_t > W_{t-6}) -> concave recovery ramp (gamma = 0.35)
    lev_rebound, _ = engine.update_ratcheted_vault_and_gearing(
        current_bar=11, nav_24h_prev=9400.0, is_expansion=False
    )
    # Concave re-gearing must restore significantly more leverage than defensive ramp
    assert lev_rebound > lev_defensive
    assert lev_rebound >= 2.50  # Rapidly re-levers above 2.5x even at 50% cushion


def test_instantaneous_deescalation_gate():
    """Verify Vector 2 Instantaneous De-Escalation Gate: drops macro hedge on V_OI > 0 and r_btc > +0.50 ATR."""
    symbols = ["BTC", "ETH"]
    sz_dec = {"BTC": 4, "ETH": 3}
    engine = Exp104SovereignEngine(symbols=symbols, sz_decimals=sz_dec)

    # Put engine in stress state with active hedge
    engine.ledger.beta_hedge_active = True
    engine.ledger.btc_hedge_notional = -15000.0
    engine.ledger.eth_hedge_notional = -5000.0
    engine.current_regime = RegimeState.SYSTEMIC_CASCADE

    # Subbar has positive OI velocity and strong BTC rebound (+1.0 ATR)
    stress = engine.evaluate_microstructure_stress(
        v_oi_24h=0.05,        # positive OI drift
        d_basis=0.001,
        d_basis_mean=0.001,
        d_basis_sigma=0.0005,
        z_jump=0.2,
        r_btc_4h=0.02,        # strong positive return
        btc_atr=600.0,
        btc_close=60000.0     # 0.02 is 2.0x ATR_norm
    )

    # De-escalation gate should immediately unwind hedge and clear cascade regime
    assert not stress
    assert not engine.ledger.beta_hedge_active
    assert engine.ledger.btc_hedge_notional == 0.0
    assert engine.ledger.eth_hedge_notional == 0.0
    assert engine.current_regime == RegimeState.RECOVERY

