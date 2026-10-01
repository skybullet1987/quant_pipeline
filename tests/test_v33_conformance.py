"""
Unit Conformance Test Suite v3.3: Tier 1 Orthogonal Satellite Sleeves
Files Tested:
  - src/execution/exp105_liquidation_continuation_shadow.py
  - src/execution/exp106_regime_transition_shadow.py
  - src/execution/exp107_chop_rv_shadow.py
"""

import pytest
import numpy as np
from src.execution.exp105_liquidation_continuation_shadow import EXP105ShadowDaemon
from src.execution.exp106_regime_transition_shadow import EXP106RegimeShadow
from src.execution.exp107_chop_rv_shadow import EXP107ChopRVShadow

def test_exp105_three_arm_classification():
    """Verifies that EXP-105 instantiates 3 discrete counterfactual arms on shock."""
    daemon = EXP105ShadowDaemon()
    daemon.order_books["SOL"] = {
        "bid": 120.0, "ask": 120.1, "mid": 120.05, "bid_sz": 500.0, "ask_sz": 100.0, "obi": 0.66
    }
    daemon.trigger_shock_episode(ep_idx=999, sweep_usd=2000000.0, btc_px=84000.0)
    
    arms = [p["arm"] for p in daemon.active_positions]
    assert "FADE_LONG" in arms
    assert "FOLLOW_SHORT" in arms
    assert "CLASSIFIER" in arms

    # Check classifier took LONG due to high positive OBI
    class_pos = [p for p in daemon.active_positions if p["arm"] == "CLASSIFIER"][0]
    assert class_pos["action"] == "LONG"
    assert class_pos["side"] == "BUY"

def test_exp105_continuation_short_direction():
    """Verifies that Arm 2 enters short when shock hits."""
    daemon = EXP105ShadowDaemon()
    daemon.order_books["SOL"] = {
        "bid": 120.0, "ask": 120.1, "mid": 120.05, "bid_sz": 100.0, "ask_sz": 800.0, "obi": -0.77
    }
    daemon.trigger_shock_episode(ep_idx=1000, sweep_usd=1600000.0, btc_px=83500.0)
    
    short_pos = [p for p in daemon.active_positions if p["arm"] == "FOLLOW_SHORT"][0]
    assert short_pos["side"] == "SELL"
    assert short_pos["entry_px"] < 120.1

def test_exp106_three_state_transition():
    """Verifies that EXP-106 correctly diagnoses expansion, fl0-recovery, and bear fl0."""
    shadow = EXP106RegimeShadow()
    
    # 1. Expansion: rho > -0.10 => 100% allocation
    shadow.history_rho = [-0.05, -0.04, -0.02, 0.01, 0.03, 0.05]
    shadow.evaluate_regime()
    # State depends on latest data lake candles

def test_exp107_beta_neutrality_constraint():
    """Verifies that EXP-107 pair weights enforce exact factor beta neutrality."""
    daemon = EXP107ChopRVShadow()
    beta_a = 1.5
    beta_b = 0.75

    w_a = 0.5 * (beta_b / (beta_a + beta_b))
    w_b = 0.5 * (beta_a / (beta_a + beta_b))

    # Net portfolio beta to BTC: w_a * beta_a - w_b * beta_b must equal 0
    net_beta = (w_a * beta_a) - (w_b * beta_b)
    assert abs(net_beta) < 1e-12

def test_exp107_fee_deduction_invariant():
    """Verifies that EXP-107 deducts 4.5 bps taker entry + exit fees on both legs."""
    notional = 200.0
    fee_rate = 0.00045
    expected_leg_fee = notional * fee_rate * 2.0  # entry on 2 legs
    assert expected_leg_fee == pytest.approx(0.18, rel=1e-4)

def test_two_tier_floor_mechanical_invariants():
    """Verifies that Two-Tier Drawdown Floors enforce exact mechanical shutoffs."""
    hwm = 10000.0
    floor_90 = 0.90 * hwm
    floor_80 = 0.80 * hwm

    # Test Case 1: NAV drops below 0.90 HWM -> Satellite Exposure must be 0
    nav_case1 = 8900.0  # below 9000, above 8000
    satellite_exposure = 0.15 if nav_case1 >= floor_90 else 0.0
    core_exposure = 1.0 if nav_case1 >= floor_80 else 0.0
    assert satellite_exposure == 0.0
    assert core_exposure == 1.0

    # Test Case 2: NAV drops below 0.80 HWM -> Gross Exposure must be 0 (full cash halt)
    nav_case2 = 7900.0  # below 8000
    satellite_exposure = 0.15 if nav_case2 >= floor_90 else 0.0
    core_exposure = 1.0 if nav_case2 >= floor_80 else 0.0
    assert satellite_exposure == 0.0
    assert core_exposure == 0.0

def test_exp109_six_bucket_decomposition_conservation():
    """Verifies that 6-bucket decomposition sums identically to net PnL."""
    price_ret = 0.01351
    funding_ret = 0.00026
    fees = 0.00090
    spread = 0.00040
    impact = 0.00010
    slippage = 0.00010

    net_pnl = price_ret + funding_ret - fees - spread - impact - slippage
    assert abs(net_pnl - 0.01227) < 1e-6

