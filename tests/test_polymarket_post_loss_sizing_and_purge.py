#!/usr/bin/env python3
"""
Unit and regression tests for Post-Loss Sizing, Concurrency Exclusion, and Auto-Purge Fixes:
1. get_position_market_value(pos, now_ts): Values expired/unresolved losses strictly at $0.00.
2. _risk_bearing_positions(): Excludes UNRESOLVED_SETTLEMENT and expired candles from MAX_CONCURRENT_POSITIONS.
3. _close_position(): Unblocks MARKET_RESOLVED_LOSS so expired losses immediately pop from active_positions.
4. Dynamic Sizing Verification: Confirms 25% sizing on $169.05 cash yields $42.26 without ghost equity.
"""

import time
import pytest
from unittest.mock import MagicMock, patch

from src.polymarket_research.polymarket_live_harvester import (
    PolymarketLiveHarvester,
    ExecutionStatus,
)


def test_get_position_market_value_active_vs_loss():
    """Verify get_position_market_value handles active vs expired/loss positions."""
    now_ts = 1792369000.0

    # Case 1: Active position before expiry
    active_pos = {
        "trade_id": "ACTIVE_1",
        "status": "EXIT_RESTING",
        "candle_expiry_ts": now_ts + 1800.0,
        "notional_usd": 50.0,
        "remaining_cost_basis": 50.0,
        "target_token": "DOWN",
    }
    val = PolymarketLiveHarvester.get_position_market_value(active_pos, now_ts)
    assert val == 50.0

    # Case 2: Unresolved settlement with confirmed loss
    loss_unresolved = {
        "trade_id": "LOSS_1",
        "status": "UNRESOLVED_SETTLEMENT",
        "candle_expiry_ts": now_ts - 600.0,
        "notional_usd": 57.28,
        "remaining_cost_basis": 57.28,
        "pending_settlement_close_reason": "MARKET_RESOLVED_LOSS",
        "resolved_winning_outcome": "UP",
        "target_token": "DOWN",
    }
    val = PolymarketLiveHarvester.get_position_market_value(loss_unresolved, now_ts)
    assert val == 0.0

    # Case 3: Expired candle (TTE <= 0) where outcome is against target
    expired_loss = {
        "trade_id": "EXPIRED_1",
        "status": "EXIT_RESTING",
        "candle_expiry_ts": now_ts - 60.0,
        "notional_usd": 56.44,
        "target_token": "DOWN",
        "resolved_winning_outcome": "UP",
    }
    val = PolymarketLiveHarvester.get_position_market_value(expired_loss, now_ts)
    assert val == 0.0

    # Case 4: Expired candle with winning resolution awaiting redemption
    expired_win = {
        "trade_id": "WIN_1",
        "status": "UNRESOLVED_SETTLEMENT",
        "candle_expiry_ts": now_ts - 60.0,
        "notional_usd": 50.0,
        "target_token": "UP",
        "resolved_winning_outcome": "UP",
        "expected_terminal_payout_usd": 65.0,
    }
    val = PolymarketLiveHarvester.get_position_market_value(expired_win, now_ts)
    assert val == 65.0


def test_risk_bearing_positions_excludes_expired_and_unresolved():
    """Verify _risk_bearing_positions excludes expired and resolving positions."""
    harvester = PolymarketLiveHarvester.__new__(PolymarketLiveHarvester)
    harvester.active_positions = {}
    now_ts = time.time()

    # Position 1: Active in-flight
    harvester.active_positions["P1_ACTIVE"] = {
        "trade_id": "P1_ACTIVE",
        "status": "EXIT_RESTING",
        "candle_expiry_ts": now_ts + 1200.0,
        "notional_usd": 40.0,
    }
    # Position 2: Expired candle
    harvester.active_positions["P2_EXPIRED"] = {
        "trade_id": "P2_EXPIRED",
        "status": "EXIT_RESTING",
        "candle_expiry_ts": now_ts - 300.0,
        "notional_usd": 50.0,
    }
    # Position 3: UNRESOLVED_SETTLEMENT
    harvester.active_positions["P3_UNRESOLVED"] = {
        "trade_id": "P3_UNRESOLVED",
        "status": "UNRESOLVED_SETTLEMENT",
        "candle_expiry_ts": now_ts - 600.0,
        "notional_usd": 56.44,
    }

    risk_pos = harvester._risk_bearing_positions()
    assert "P1_ACTIVE" in risk_pos
    assert "P2_EXPIRED" not in risk_pos
    assert "P3_UNRESOLVED" not in risk_pos
    assert len(risk_pos) == 1


def test_close_position_unblocks_market_resolved_loss():
    """Verify _close_position immediately purges MARKET_RESOLVED_LOSS even if exit_cash_estimated is True."""
    harvester = PolymarketLiveHarvester.__new__(PolymarketLiveHarvester)
    harvester.active_positions = {}
    harvester.closed_positions = []
    harvester.risk_controller = MagicMock()
    harvester.executor = MagicMock()
    harvester.save_state = MagicMock()
    harvester.calculate_realized_cash_pnl = MagicMock(return_value=-57.28)
    harvester._release_position_reservations = MagicMock()

    dead_pos = {
        "trade_id": "DEAD_7PM",
        "status": "UNRESOLVED_SETTLEMENT",
        "exit_cash_estimated": True,  # Would have blocked settlement prior to fix
        "estimated_exit_cash": 0.0,
        "notional_usd": 57.28,
        "target_token": "DOWN",
        "pending_settlement_close_reason": "MARKET_RESOLVED_LOSS",
    }
    harvester.active_positions["DEAD_7PM"] = dead_pos

    res = harvester._close_position(
        "DEAD_7PM", dead_pos,
        ExecutionStatus.SETTLED, "MARKET_RESOLVED_LOSS",
        won=False, record_pnl=True
    )

    # Position must be removed from active_positions and appended to closed_positions
    assert "DEAD_7PM" not in harvester.active_positions
    assert len(harvester.closed_positions) == 1
    assert harvester.closed_positions[0]["trade_id"] == "DEAD_7PM"
    assert harvester.closed_positions[0]["won"] is False
    assert harvester.closed_positions[0]["close_reason"] == "MARKET_RESOLVED_LOSS"


def test_dynamic_sizing_no_ghost_equity():
    """Verify dynamic ticket sizing strictly uses true marked equity without ghost additions."""
    harvester = PolymarketLiveHarvester.__new__(PolymarketLiveHarvester)
    now_ts = 1792369000.0

    # Dead position in active_positions
    harvester.active_positions = {
        "DEAD_7PM": {
            "trade_id": "DEAD_7PM",
            "status": "UNRESOLVED_SETTLEMENT",
            "candle_expiry_ts": now_ts - 600.0,
            "notional_usd": 57.28,
            "pending_settlement_close_reason": "MARKET_RESOLVED_LOSS",
            "resolved_winning_outcome": "UP",
            "target_token": "DOWN",
        }
    }

    # Calculate marked equity for dynamic sizing
    live_bankroll = 169.05
    deployed_market_value = sum(
        harvester.get_position_market_value(pos, now_ts)
        for pos in harvester.active_positions.values()
    )
    # The dead position must contribute exactly $0.00
    assert deployed_market_value == 0.0

    total_account_value = live_bankroll + deployed_market_value
    assert total_account_value == 169.05  # NOT $226.33

    dynamic_bankroll_pct = 0.25
    dynamic_ticket_cap = round(min(250.0, max(25.0, total_account_value * dynamic_bankroll_pct)), 2)

    # 25% of 169.05 is exactly 42.26
    assert dynamic_ticket_cap == 42.26  # NOT $56.37 or $57.12
