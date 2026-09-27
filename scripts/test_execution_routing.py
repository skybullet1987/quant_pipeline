from __future__ import annotations

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.research.expectancy_engine import RawMarketState, build_trade_intent
from pipeline.execution.execution_policy import ExecutionRouter
from pipeline.execution.deadman_switch import DeadManSwitchDaemon

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def run_execution_test():
    router = ExecutionRouter()
    
    # Mock Market Feed & TradeIntent
    market = RawMarketState(
        symbol="BTC",
        t_event_ns=0,
        t_recv_ns=0,
        bid_price=78700.0,
        ask_price=78705.0,
        mid_price=78702.5,
        oracle_price=78702.5,
        funding_rate_1h=0.000012,
        funding_missing=False,
    )
    
    intent = build_trade_intent(market, target_weight=0.15, total_portfolio_equity=100_000.0)
    
    # Evaluate Execution Route
    plan = router.evaluate_route(
        intent=intent,
        best_bid=market.bid_price,
        best_ask=market.ask_price,
        rolling_vol_4h=0.015,
        queue_ahead_notional=15_000.0,
        recent_trade_flow_usd=60_000.0,
    )

    print("\n" + "=" * 70)
    print("                EXECUTION ROUTE SPECIFICATION")
    print("=" * 70)
    print(f"Symbol:               {plan.symbol}")
    print(f"Action:               {plan.action}")
    print(f"Order Route Type:     {plan.order_type}")
    print(f"Limit / Post Price:   ${plan.limit_price:,.2f}")
    print(f"Target Notional:      ${plan.target_notional:,.2f}")
    print(f"Estimated P(Fill):    {plan.p_fill:.2%}")
    print(f"Execution EV:         {plan.ev_trade:+.4%}")
    print(f"AS Hurdle Buffer:     {plan.adverse_selection_buffer_bps:+.2f} bps")
    print("=" * 70)

    # Test Dead Man Switch Heartbeat
    dms = DeadManSwitchDaemon()
    dms.heartbeat_once()


if __name__ == "__main__":
    run_execution_test()
