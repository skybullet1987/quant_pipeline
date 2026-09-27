import pytest
from pipeline.execution.maker_sm import MakerStateMachine, OrderState
from pipeline.execution.models import (
    ExecutionOrderType,
    ExecutionSide,
    MicrostructureContext,
    OrderAction,
    OrderPlan,
)
from pipeline.execution.policy import EmpiricalFillModel, ExecutionPolicyEngine
from pipeline.strategy.state import IntentSide, TradeIntent


def test_empirical_fill_model_probabilities():
    model = EmpiricalFillModel()
    
    # Favorable queue & aligned positive flow
    ctx_favorable = MicrostructureContext(
        timestamp_ns=1700000000000000000,
        symbol="BTC",
        best_bid=50000.0,
        best_ask=50000.5,
        spread_bps=1.0,
        queue_ahead_size=1.0,
        queue_behind_size=20.0,
        trade_flow_imbalance=0.80,   # Strong buy flow
        rolling_cancel_ratio=0.10,
        realized_vol_1m_bps=5.0,
        estimated_latency_ms=10.0
    )

    p_favorable = model.estimate_fill_probability(ctx_favorable, order_size=0.5, is_buy=True)
    
    # Toxic unfavorable flow & large queue ahead
    ctx_unfavorable = MicrostructureContext(
        timestamp_ns=1700000000000000000,
        symbol="BTC",
        best_bid=50000.0,
        best_ask=50000.5,
        spread_bps=1.0,
        queue_ahead_size=50.0,
        queue_behind_size=2.0,
        trade_flow_imbalance=-0.90,  # Hostile sell flow
        rolling_cancel_ratio=0.60,
        realized_vol_1m_bps=20.0,
        estimated_latency_ms=80.0
    )

    p_unfavorable = model.estimate_fill_probability(ctx_unfavorable, order_size=0.5, is_buy=True)

    assert p_favorable > p_unfavorable
    assert p_favorable > 0.50
    assert p_unfavorable < 0.30


def test_execution_policy_engine_routing():
    engine = ExecutionPolicyEngine()

    intent_low_urgency = TradeIntent(
        timestamp_ns=1700000000000000000,
        symbol="BTC",
        target_side=IntentSide.LONG,
        target_weight=0.10,
        target_notional_usd=5000.0,
        limit_price_ref=50000.0,
        urgency_bps=0.5,
        ev_return_pct=0.0015,
        regime_multiplier=1.0,
    )

    ctx = MicrostructureContext(
        timestamp_ns=1700000000000000000,
        symbol="BTC",
        best_bid=50000.0,
        best_ask=50000.5,
        spread_bps=1.0,
        queue_ahead_size=2.0,
        queue_behind_size=10.0,
        trade_flow_imbalance=0.50,
        rolling_cancel_ratio=0.10,
        realized_vol_1m_bps=4.0,
    )

    plan_maker = engine.formulate_order_plan(intent_low_urgency, ctx)
    assert plan_maker.action == OrderAction.PLACE
    assert plan_maker.order_type == ExecutionOrderType.LIMIT_MAKER
    assert plan_maker.target_price == 50000.0

    # High urgency intent forces aggressive taker routing (IOC)
    intent_urgent = TradeIntent(
        timestamp_ns=1700000000000000000,
        symbol="BTC",
        target_side=IntentSide.LONG,
        target_weight=0.10,
        target_notional_usd=5000.0,
        limit_price_ref=50000.5,
        urgency_bps=8.0,
        ev_return_pct=0.0040,
        regime_multiplier=1.0,
    )

    plan_taker = engine.formulate_order_plan(intent_urgent, ctx)
    assert plan_taker.order_type == ExecutionOrderType.IOC
    assert plan_taker.target_price == 50000.5


def test_maker_state_machine_hysteresis():
    sm = MakerStateMachine(price_hysteresis_bps=2.0, size_hysteresis_pct=0.15)
    t0_ns = 1700000000_000_000_000

    plan_init = OrderPlan(
        action=OrderAction.PLACE,
        symbol="BTC",
        side=ExecutionSide.BUY,
        order_type=ExecutionOrderType.LIMIT_MAKER,
        target_price=50000.0,
        target_size=1.0,
        target_notional_usd=50000.0,
        expected_fill_prob=0.8,
        expected_adverse_selection_bps=0.5,
        ev_trade_bps=5.0,
        cl_ord_id="ord_1",
    )

    act, p = sm.reconcile_intent(plan_init, current_time_ns=t0_ns)
    assert act == OrderAction.PLACE

    # Minor price change within threshold -> HOLD
    t1_ns = t0_ns + 500_000_000
    plan_minor = OrderPlan(
        action=OrderAction.PLACE,
        symbol="BTC",
        side=ExecutionSide.BUY,
        order_type=ExecutionOrderType.LIMIT_MAKER,
        target_price=50001.0,
        target_size=1.0,
        target_notional_usd=50001.0,
        expected_fill_prob=0.8,
        expected_adverse_selection_bps=0.5,
        ev_trade_bps=5.0,
        cl_ord_id="ord_2",
    )
    act_minor, _ = sm.reconcile_intent(plan_minor, current_time_ns=t1_ns)
    assert act_minor == OrderAction.HOLD

    # Significant price change above threshold -> MODIFY
    t2_ns = t1_ns + 500_000_000
    plan_major = OrderPlan(
        action=OrderAction.PLACE,
        symbol="BTC",
        side=ExecutionSide.BUY,
        order_type=ExecutionOrderType.LIMIT_MAKER,
        target_price=50050.0,
        target_size=1.0,
        target_notional_usd=50050.0,
        expected_fill_prob=0.8,
        expected_adverse_selection_bps=0.5,
        ev_trade_bps=5.0,
        cl_ord_id="ord_3",
    )
    act_major, p_mod = sm.reconcile_intent(plan_major, current_time_ns=t2_ns)
    assert act_major == OrderAction.MODIFY
    assert p_mod.target_price == 50050.0
