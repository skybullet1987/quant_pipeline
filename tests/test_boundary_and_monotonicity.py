#!/usr/bin/env python3
"""
Unit Test Suite: Boundary Convergence, Dynamic Volatility, CTF Merge & Monotonicity
===================================================================================
Rigorous verification of the mathematical formulations and execution invariants
from the Quantitative Alpha Architecture and Executive Audit:
  1. BoundaryConvergenceEngine: TWAP bounds with 4-sigma dynamic volatility.
  2. Discrete Close Barrier: Black-Scholes jump barrier Z >= 3.5.
  3. Closed-Form Dynamic Taker Fee: f_poly(P) = r * (1 - P).
  4. Instantaneous CTF Split/Merge Arbitrage detection.
  5. AtomicHedgingStateMachine: Happy path and slippage emergency unwind.
  6. Capital Carry Cost discounting for macro horizon chains.
  7. QueuePersistenceProfiler: Event decay tracking and Gate 2 evaluation.
"""

import math
import time
import pytest

from src.polymarket_research.exp306_expiry_boundary_engine import (
    BoundaryConvergenceEngine,
    evaluate_instantaneous_merge_arbitrage,
)
from src.polymarket_research.exp307_monotonicity_copula_scanner import (
    AtomicHedgingStateMachine,
    HedgeState,
    compute_capital_carry_cost,
    compute_polymarket_dynamic_taker_fee,
)
from src.polymarket_research.exp308_queue_persistence_profiler import (
    PersistenceEvent,
    QueuePersistenceProfiler,
)


# ==============================================================================
# TEST 1: BOUNDARY CONVERGENCE ENGINE & DYNAMIC VOLATILITY
# ==============================================================================

def test_dynamic_volatility_twap_bounds():
    strike = 80000.0
    expiry = 1000.0
    twap_window = 30.0

    engine = BoundaryConvergenceEngine(
        strike_price=strike,
        expiry_timestamp=expiry,
        resolution_type="TWAP",
        twap_window_seconds=twap_window,
        min_hurdle_profit=0.02,
        z_score_envelope=4.0,
    )

    # Simulate ticks starting at t = 970 (start of 30s TWAP window)
    # Price is trending strongly above strike at $80,500
    for i in range(25):
        t = 970.0 + i
        px = 80500.0 + (i % 3) * 5.0  # Minor tick noise
        engine.record_composite_tick(px, t)

    # Current time: 5 seconds before expiry (t = 995)
    current_time = 995.0
    bounds = engine.compute_twap_bounds(current_time)

    assert bounds["twap_min"] > 0.0
    assert bounds["twap_max"] > bounds["twap_min"]
    # With 25s already locked at ~80,500, twap_min should comfortably exceed strike $80,000
    assert bounds["twap_min"] > strike

    # Test entry evaluation for winning UP contract
    # Resting ask is discounted at $0.92
    entry = engine.evaluate_execution_entry("UP", clob_best_ask=0.92, ask_liquidity=100.0, current_time=current_time)
    assert entry is not None
    assert entry["action"] == "BUY_FOK"
    assert entry["side"] == "UP"
    assert entry["net_edge"] >= 0.02
    assert entry["fee"] > 0.0


def test_boundary_convergence_rejection_when_unlocked():
    strike = 80000.0
    expiry = 1000.0
    twap_window = 30.0

    engine = BoundaryConvergenceEngine(
        strike_price=strike,
        expiry_timestamp=expiry,
        resolution_type="TWAP",
        twap_window_seconds=twap_window,
    )

    # Spot is hovering right around strike ($80,005)
    for i in range(10):
        t = 970.0 + i
        engine.record_composite_tick(80005.0, t)

    # At t = 980 (20s remaining), volatility envelope allows price to drop below strike
    bounds = engine.compute_twap_bounds(current_time=980.0)
    assert bounds["twap_min"] < strike  # NOT locked!

    # Should reject entry because outcome is not deterministic
    entry = engine.evaluate_execution_entry("UP", clob_best_ask=0.75, ask_liquidity=50.0, current_time=980.0)
    assert entry is None


def test_discrete_close_barrier_z_score():
    strike = 80000.0
    expiry = 1000.0

    engine = BoundaryConvergenceEngine(
        strike_price=strike,
        expiry_timestamp=expiry,
        resolution_type="DISCRETE_CLOSE",
        discrete_jump_threshold=3.5,
    )

    # Spot is $81,200 (well above strike) with 5 seconds to go
    for i in range(10):
        engine.record_composite_tick(81200.0, 990.0 + i)

    barrier = engine.evaluate_discrete_close_barrier(current_time=995.0)
    assert barrier["deterministic"] is True
    assert barrier["winning_side"] == "UP"
    assert barrier["z_score"] >= 3.5

    entry = engine.evaluate_execution_entry("UP", clob_best_ask=0.91, ask_liquidity=50.0, current_time=995.0)
    assert entry is not None
    assert "DISCRETE_BARRIER" in entry["reason"]


def test_polymarket_closed_form_taker_fee():
    engine = BoundaryConvergenceEngine(strike_price=100.0, expiry_timestamp=100.0, taker_fee_coefficient=0.07)

    # At P = 0.50: fee = 0.07 * (1 - 0.50) = 0.035 (3.50%)
    fee_50 = engine.calculate_polymarket_taker_fee(0.50)
    assert math.isclose(fee_50, 0.035, abs_tol=1e-5)

    # At P = 0.90: fee = 0.07 * (1 - 0.90) = 0.007 (0.70%)
    fee_90 = engine.calculate_polymarket_taker_fee(0.90)
    assert math.isclose(fee_90, 0.007, abs_tol=1e-5)

    # At P = 0.95: fee = 0.07 * (1 - 0.95) = 0.0035 (0.35%)
    fee_95 = engine.calculate_polymarket_taker_fee(0.95)
    assert math.isclose(fee_95, 0.0035, abs_tol=1e-5)


# ==============================================================================
# TEST 2: INSTANTANEOUS CTF COMPLEMENTARY TOKEN SPLIT/MERGE ARBITRAGE
# ==============================================================================

def test_instantaneous_merge_arbitrage_detection():
    # Retail panic: UP ask is $0.45, DOWN ask is $0.48 (Sum = $0.93)
    opp = evaluate_instantaneous_merge_arbitrage(
        market_id="MKT_1001",
        token_up="TOK_UP_1",
        token_down="TOK_DOWN_1",
        best_ask_up=0.45,
        best_ask_down=0.48,
        depth_up_shares=100.0,
        depth_down_shares=80.0,
        fee_coefficient=0.07,
        estimated_gas_usd=0.015,
    )
    assert opp is not None
    assert opp.max_executable_shares == 80.0
    assert opp.gross_cost == pytest.approx(0.93, abs=1e-5)
    assert opp.net_profit_per_share > 0.02  # Solid net profit


def test_merge_arbitrage_rejection_when_fair_or_overpriced():
    # Normal market: UP ask $0.52, DOWN ask $0.51 (Sum = $1.03)
    opp = evaluate_instantaneous_merge_arbitrage(
        market_id="MKT_1002",
        token_up="TOK_UP_2",
        token_down="TOK_DOWN_2",
        best_ask_up=0.52,
        best_ask_down=0.51,
        depth_up_shares=100.0,
        depth_down_shares=100.0,
    )
    assert opp is None


# ==============================================================================
# TEST 3: ATOMIC HEDGING STATE MACHINE & EMERGENCY UNWIND
# ==============================================================================

def test_atomic_hedging_happy_path():
    sm = AtomicHedgingStateMachine(max_allowed_slippage=0.02, max_hedging_delay_sec=0.5)
    assert sm.state == HedgeState.IDLE

    # Leg 1 posted
    sm.on_leg1_posted("ORDER_LEG1_123", price=0.65, shares=50.0)
    assert sm.state == HedgeState.LEG1_POSTED

    # Leg 1 filled
    sm.on_leg1_filled(price=0.65, shares=50.0)
    assert sm.state == HedgeState.LEG1_FILLED

    # Leg 2 triggered with acceptable ask price
    decision = sm.trigger_leg2(expected_price=0.58, current_best_ask=0.585)
    assert decision["action"] == "EXECUTE_LEG2_FOK"
    assert sm.state == HedgeState.LEG2_TRIGGERED

    # Leg 2 confirmed
    sm.on_leg2_success("ORDER_LEG2_456", fill_price=0.585)
    assert sm.state == HedgeState.HEDGED_COMPLETE


def test_atomic_hedging_emergency_unwind_on_slippage():
    sm = AtomicHedgingStateMachine(max_allowed_slippage=0.02, max_hedging_delay_sec=0.5)

    sm.on_leg1_posted("ORDER_LEG1_789", price=0.65, shares=50.0)
    sm.on_leg1_filled(price=0.65, shares=50.0)

    # Leg 2 ask jumped by $0.05 (from 0.58 to 0.63, exceeding 0.02 max slippage)
    decision = sm.trigger_leg2(expected_price=0.58, current_best_ask=0.63)
    assert decision["action"] == "EMERGENCY_UNWIND"
    assert sm.state == HedgeState.EMERGENCY_UNWIND_TRIGGERED

    # Unwind executed
    sm.on_unwind_success("ORDER_UNWIND_999", exit_price=0.64)
    assert sm.state == HedgeState.UNWOUND_CLOSED


# ==============================================================================
# TEST 4: CAPITAL CARRY COST INTEGRATION
# ==============================================================================

def test_capital_carry_cost_deduction():
    # 45 days at SOFR (4.8%) on $1.20 notional (e.g. 2 legs of macro contract)
    notional = 1.20
    tau_days = 45.0
    carry = compute_capital_carry_cost(notional, tau_days, r_f=0.048)

    # 45 / 365.25 * 0.048 ~ 0.59% -> 1.20 * 0.0059 ~ $0.0071
    assert 0.005 < carry < 0.009

    # Zero days has zero carry cost
    zero_carry = compute_capital_carry_cost(notional, tau_days=0.0)
    assert zero_carry == pytest.approx(0.0, abs=1e-5)


# ==============================================================================
# TEST 5: QUEUE PERSISTENCE PROFILER METRICS & GATES
# ==============================================================================

def test_queue_persistence_metrics_calculation(tmp_path, monkeypatch):
    test_events_file = tmp_path / "test_persistence_events.jsonl"
    test_metrics_file = tmp_path / "test_persistence_metrics.json"

    import src.polymarket_research.exp308_queue_persistence_profiler as prof_mod
    monkeypatch.setattr(prof_mod, "EVENTS_FILE", test_events_file)
    monkeypatch.setattr(prof_mod, "METRICS_FILE", test_metrics_file)

    profiler = QueuePersistenceProfiler()

    # Add 10 mock events: 8 survive > 150ms, 2 evaporate under 85ms (20% decay < 85ms)
    for i in range(10):
        evaporated = i < 2
        ev = PersistenceEvent(
            event_id=f"EV_{i}",
            token_id=f"TOK_{i}",
            t0_timestamp=time.time(),
            initial_best_ask=0.92,
            initial_depth=50.0,
            persistence_matrix={"50ms": True, "85ms": not evaporated, "150ms": not evaporated},
            evaporated_under_85ms=evaporated,
            final_survival_seconds=0.05 if evaporated else 0.5,
        )
        profiler.events.append(ev)

    profiler._recalculate_metrics()
    assert profiler.stats["total_events"] == 10
    assert profiler.stats["evaporated_under_85ms_pct"] == 20.0
    assert profiler.stats["survived_over_150ms_pct"] == 80.0
