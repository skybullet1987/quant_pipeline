"""
Layer 4: Live Execution Node with Full Dynamic Universe Support.
"""
from __future__ import annotations

import logging
from pipeline.execution.maker_sm import MakerStateMachine
from pipeline.execution.models import MicrostructureContext, OrderAction, OrderPlan
from pipeline.execution.policy import ExecutionPolicyEngine
from pipeline.ingestion.hyperliquid_universe import HyperliquidUniverse
from pipeline.live.reconciliation import PositionReconciler
from pipeline.live.signer import HyperliquidSigner, SignedExchangePayload
from pipeline.strategy.allocator import PureStrategyCore
from pipeline.strategy.state import FeatureState, RawMarketState, RegimeState, TradeIntent

logger = logging.getLogger(__name__)


class LiveExecutionNode:
    def __init__(
        self,
        signer: HyperliquidSigner,
        universe: HyperliquidUniverse | None = None,
        total_equity_usd: float = 10000.0,
    ):
        self.signer = signer
        self.universe = universe or HyperliquidUniverse(is_testnet=signer.is_testnet)
        self.total_equity_usd = total_equity_usd
        
        self.strategy_core = PureStrategyCore()
        self.policy_engine = ExecutionPolicyEngine()
        self.maker_sm = MakerStateMachine()
        self.reconciler = PositionReconciler()
        self._order_seq = 0

    def process_tick(
        self,
        market: RawMarketState,
        features: FeatureState,
        regime: RegimeState,
        microstructure: MicrostructureContext,
        raw_win_prob: float,
        expected_gain_pct: float,
        expected_loss_pct: float,
    ) -> SignedExchangePayload | None:
        if self.reconciler.is_circuit_broken:
            logger.error("Execution halted by circuit breaker: %s", self.reconciler.circuit_break_reason)
            return None

        self._order_seq += 1

        # 1. Zero-I/O Strategy Core -> TradeIntent
        intent: TradeIntent = self.strategy_core.process(
            market=market,
            features=features,
            regime=regime,
            raw_win_prob=raw_win_prob,
            expected_gain_pct=expected_gain_pct,
            expected_loss_pct=expected_loss_pct,
            total_equity_usd=self.total_equity_usd,
        )

        # 2. Execution Policy Layer -> OrderPlan
        raw_plan: OrderPlan = self.policy_engine.formulate_order_plan(
            intent=intent,
            context=microstructure,
            order_seq=self._order_seq,
        )

        # 3. Apply szDecimals precision rounding for the specific contract
        adjusted_size = self.universe.round_size(market.symbol, raw_plan.target_size)
        precision_plan = OrderPlan(
            action=raw_plan.action,
            symbol=raw_plan.symbol,
            side=raw_plan.side,
            order_type=raw_plan.order_type,
            target_price=raw_plan.target_price,
            target_size=adjusted_size,
            target_notional_usd=raw_plan.target_notional_usd,
            expected_fill_prob=raw_plan.expected_fill_prob,
            expected_adverse_selection_bps=raw_plan.expected_adverse_selection_bps,
            ev_trade_bps=raw_plan.ev_trade_bps,
            cl_ord_id=raw_plan.cl_ord_id,
            urgency_bps=raw_plan.urgency_bps,
            metadata=raw_plan.metadata,
        )

        # 4. Maker State Machine Hysteresis Check
        action, finalized_plan = self.maker_sm.reconcile_intent(
            plan=precision_plan,
            current_time_ns=market.timestamp_ns,
        )

        if action == OrderAction.HOLD:
            return None

        # 5. Dynamic Asset Index Lookup & EIP-712 Signing
        self.reconciler.record_signal(finalized_plan.cl_ord_id, market.timestamp_ns)
        asset_index = self.universe.asset_map.get(market.symbol, 0)

        if action in (OrderAction.PLACE, OrderAction.MODIFY):
            payload = self.signer.build_order_action(finalized_plan, asset_index=asset_index)
            self.reconciler.record_submit(finalized_plan.cl_ord_id)
            return payload

        elif action == OrderAction.CANCEL:
            payload = self.signer.build_cancel_by_cloid(asset_index=asset_index, cl_ord_id=finalized_plan.cl_ord_id)
            self.reconciler.record_submit(finalized_plan.cl_ord_id)
            return payload

        return None
