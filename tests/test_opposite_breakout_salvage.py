import pytest
import asyncio
import time
from unittest.mock import MagicMock, AsyncMock, patch

from src.polymarket_research.polymarket_live_harvester import (
    PolymarketLiveHarvester,
    ExecutionStatus,
)
from src.polymarket_research.polymarket_paper_trader import (
    PolymarketForwardPaperTrader,
)


@pytest.fixture
def mock_executor():
    executor = MagicMock()
    executor.dry_run = True
    executor.cancel_order = MagicMock(return_value={"canceled": ["order_tp_123"]})
    executor.get_order_fill_summary = MagicMock(return_value={"terminal": False, "matched": 0.0, "order_id": "order_tp_123"})
    executor.post_maker_exit_order = MagicMock(return_value={"success": True, "orderID": "order_tp_123"})
    executor.calculate_balance_epsilon = MagicMock(return_value=0.001)
    executor.execute_unwind_order = MagicMock(return_value={
        "success": True,
        "matched_size": 40.0,
        "taking_amount": 10.0,
        "fee_usd": 0.05,
        "orderID": "unwind_salvage_001",
    })
    executor.release_inventory = MagicMock()
    executor.invalidate_collateral_cache = MagicMock()
    return executor


@pytest.fixture
def harvester(mock_executor, tmp_path):
    h = PolymarketLiveHarvester(
        dry_run=True,
        max_concurrent=3,
        ticket_notional=22.0,
    )
    h.executor = mock_executor
    h.state_file = tmp_path / "live_state.json"
    h._strict_open_orders = MagicMock(return_value=[])
    return h


@pytest.mark.anyio
async def test_rule1_zero_false_positives_on_winners(harvester):
    """
    Rule 1 (Zero False Positives): NEVER trigger a salvage stop while spot_disp >= 0 (wrong_side_pct <= 0.0).
    Whenever spot is on the winning side of open_spot, reset timer.
    """
    now_ts = 1700000000.0
    harvester.active_positions = {
        "POS_TEST_1": {
            "trade_id": "POS_TEST_1",
            "market_id": "MKT_1",
            "token_id": "TOK_DOWN",
            "target_token": "DOWN",
            "asset": "ETH",
            "entry_price": 0.75,
            "entry_shares": 40.0,
            "remaining_shares": 40.0,
            "candle_open_spot": 2400.0,
            "candle_expiry_ts": now_ts + 1800.0,
            "exit_order_id": "order_tp_123",
            "target_exit_price": 0.98,
            "status": "EXIT_RESTING",
        }
    }
    # Spot touches 2400.0 (dist = 0.00%, winning side / breakeven)
    harvester.get_reference_spot_price = MagicMock(return_value=2400.0)
    harvester.executor.get_market_book_async = AsyncMock(return_value={"bids": [{"price": "0.30", "size": "100"}]})

    with patch("time.time", return_value=now_ts):
        await harvester.check_resolutions_and_manage_positions()

    pos = harvester.active_positions.get("POS_TEST_1")
    assert pos is not None
    assert pos.get("status") == "EXIT_RESTING"
    assert pos.get("opposite_breakout_start_ts") is None
    harvester.executor.cancel_order.assert_not_called()


@pytest.mark.anyio
async def test_rule1_resets_timer_when_spot_bounces_to_favorable(harvester):
    """
    If spot was adverse and started timer, but recovers to winning side (wrong_side_pct <= 0.0),
    the salvage timer must be reset immediately.
    """
    now_ts = 1700000000.0
    harvester.active_positions = {
        "POS_TEST_RESET": {
            "trade_id": "POS_TEST_RESET",
            "market_id": "MKT_RESET",
            "token_id": "TOK_DOWN",
            "target_token": "DOWN",
            "asset": "ETH",
            "entry_price": 0.75,
            "entry_shares": 40.0,
            "remaining_shares": 40.0,
            "candle_open_spot": 2400.0,
            "candle_expiry_ts": now_ts + 1800.0,
            "exit_order_id": "order_tp_123",
            "target_exit_price": 0.98,
            "status": "EXIT_RESTING",
        }
    }
    # Cycle 1: Spot crosses to 2405.0 (+0.208% adverse > 0.18% Zone 1 start) -> starts timer
    harvester.get_reference_spot_price = MagicMock(return_value=2405.0)
    harvester.executor.get_market_book_async = AsyncMock(return_value={"bids": [{"price": "0.30", "size": "100"}]})

    with patch("time.time", return_value=now_ts):
        await harvester.check_resolutions_and_manage_positions()

    pos = harvester.active_positions.get("POS_TEST_RESET")
    assert pos is not None
    assert pos.get("opposite_breakout_start_ts") == now_ts

    # Cycle 2: 30s later, spot bounces to 2397.0 (favorable cushion for DOWN, wrong_side_pct < 0) -> timer resets
    harvester.get_reference_spot_price = MagicMock(return_value=2397.0)
    with patch("time.time", return_value=now_ts + 30.0):
        await harvester.check_resolutions_and_manage_positions()

    pos = harvester.active_positions.get("POS_TEST_RESET")
    assert pos is not None
    assert pos.get("opposite_breakout_start_ts") is None
    harvester.executor.cancel_order.assert_not_called()


@pytest.mark.anyio
async def test_zone1_mid_hour_salvage(harvester):
    """
    Zone 1 — Mid-Hour (TTE > 900.0s):
    - Starts when wrong_side_pct >= 0.18%
    - Sustains when wrong_side_pct >= 0.15% for 45.0s
    - Requires best_b >= 0.08
    """
    now_ts = 1700000000.0
    harvester.active_positions = {
        "POS_Z1": {
            "trade_id": "POS_Z1",
            "market_id": "MKT_Z1",
            "token_id": "TOK_DOWN",
            "target_token": "DOWN",
            "asset": "ETH",
            "entry_price": 0.65,
            "entry_shares": 40.0,
            "remaining_shares": 40.0,
            "candle_open_spot": 2400.0,
            "candle_expiry_ts": now_ts + 1800.0,  # TTE = 1800s > 900s
            "exit_order_id": "order_tp_123",
            "target_exit_price": 0.98,
            "status": "EXIT_RESTING",
        }
    }
    # Adverse move: Spot at 2405.0 (+0.208% adverse > 0.18%)
    harvester.get_reference_spot_price = MagicMock(return_value=2405.0)
    harvester.executor.get_market_book_async = AsyncMock(return_value={"bids": [{"price": "0.50", "size": "100"}]})

    # Step 1: at t = 0 -> timer armed
    with patch("time.time", return_value=now_ts):
        await harvester.check_resolutions_and_manage_positions()

    pos = harvester.active_positions.get("POS_Z1")
    assert pos.get("opposite_breakout_start_ts") == now_ts
    harvester.executor.cancel_order.assert_not_called()

    # Step 2: at t = 30.0s (< 40s) -> still holding
    with patch("time.time", return_value=now_ts + 30.0):
        await harvester.check_resolutions_and_manage_positions()
    harvester.executor.cancel_order.assert_not_called()

    # Step 3: at t = 46.0s (>= 45s), spot at 2404.0 (+0.167% adverse >= 0.15%), best_bid = 0.50 >= 0.08 -> TRIGGERS
    harvester.get_reference_spot_price = MagicMock(return_value=2404.0)
    with patch("time.time", return_value=now_ts + 46.0):
        await harvester.check_resolutions_and_manage_positions()

    harvester.executor.cancel_order.assert_called_once_with("order_tp_123")
    harvester.executor.execute_unwind_order.assert_called_once()
    call_kwargs = harvester.executor.execute_unwind_order.call_args.kwargs
    assert call_kwargs["min_price"] == 0.48  # 0.50 - 0.02


@pytest.mark.anyio
async def test_zone2_late_hour_salvage(harvester):
    """
    Zone 2 — Late-Hour (180.0s < TTE <= 900.0s):
    - Starts when wrong_side_pct >= 0.12%
    - Sustains when wrong_side_pct >= 0.10% for 20.0s
    - Requires best_b >= 0.08
    """
    now_ts = 1700000000.0
    harvester.active_positions = {
        "POS_Z2": {
            "trade_id": "POS_Z2",
            "market_id": "MKT_Z2",
            "token_id": "TOK_DOWN",
            "target_token": "DOWN",
            "asset": "ETH",
            "entry_price": 0.75,
            "entry_shares": 40.0,
            "remaining_shares": 40.0,
            "candle_open_spot": 2400.0,
            "candle_expiry_ts": now_ts + 600.0,  # TTE = 600s (Zone 2)
            "exit_order_id": "order_tp_123",
            "target_exit_price": 0.98,
            "status": "EXIT_RESTING",
        }
    }
    # Adverse move: Spot at 2403.5 (+0.146% adverse > 0.12%)
    harvester.get_reference_spot_price = MagicMock(return_value=2403.5)
    harvester.executor.get_market_book_async = AsyncMock(return_value={"bids": [{"price": "0.25", "size": "100"}]})

    with patch("time.time", return_value=now_ts):
        await harvester.check_resolutions_and_manage_positions()

    pos = harvester.active_positions.get("POS_Z2")
    assert pos.get("opposite_breakout_start_ts") == now_ts

    # 21 seconds later, spot at 2402.8 (+0.117% >= 0.10%), duration 21s >= 20s -> TRIGGERS
    harvester.get_reference_spot_price = MagicMock(return_value=2402.8)
    with patch("time.time", return_value=now_ts + 21.0):
        await harvester.check_resolutions_and_manage_positions()

    harvester.executor.cancel_order.assert_called_once_with("order_tp_123")
    harvester.executor.execute_unwind_order.assert_called_once()


@pytest.mark.anyio
async def test_zone3_final_minutes_salvage(harvester):
    """
    Zone 3 — Final 3 Minutes (25.0s <= TTE <= 180.0s):
    - Starts when wrong_side_pct >= 0.07%
    - Sustains when wrong_side_pct >= 0.05% for 10.0s
    - Requires best_b >= 0.06
    """
    now_ts = 1700000000.0
    harvester.active_positions = {
        "POS_Z3": {
            "trade_id": "POS_Z3",
            "market_id": "MKT_Z3",
            "token_id": "TOK_UP",
            "target_token": "UP",
            "asset": "BTC",
            "entry_price": 0.70,
            "entry_shares": 30.0,
            "remaining_shares": 30.0,
            "candle_open_spot": 60000.0,
            "candle_expiry_ts": now_ts + 120.0,  # TTE = 120s (Zone 3)
            "exit_order_id": "order_tp_123",
            "target_exit_price": 0.98,
            "status": "EXIT_RESTING",
        }
    }
    # For UP, adverse is spot < open. Spot at 59950.0 is -0.083% adverse (> 0.07%)
    harvester.get_reference_spot_price = MagicMock(return_value=59950.0)
    harvester.executor.get_market_book_async = AsyncMock(return_value={"bids": [{"price": "0.15", "size": "100"}]})

    with patch("time.time", return_value=now_ts):
        await harvester.check_resolutions_and_manage_positions()

    pos = harvester.active_positions.get("POS_Z3")
    assert pos.get("opposite_breakout_start_ts") == now_ts

    # 11 seconds later, spot at 59960.0 (-0.067% >= 0.05%), duration 11s >= 10s, bid 0.15 >= 0.06 -> TRIGGERS
    harvester.get_reference_spot_price = MagicMock(return_value=59960.0)
    with patch("time.time", return_value=now_ts + 11.0):
        await harvester.check_resolutions_and_manage_positions()

    harvester.executor.cancel_order.assert_called_once_with("order_tp_123")
    harvester.executor.execute_unwind_order.assert_called_once()


@pytest.mark.anyio
async def test_peak_bid_trailing_profit_ratchet(harvester):
    """
    Peak-Bid Trailing Profit Ratchet:
    - Arm condition: max_seen_bid >= max(0.84, entry_px + 0.14)
    - Trailing floor: max_seen_bid - 0.08
    - Trigger condition: best_b <= trail_floor for >= 6.0s, TTE >= 30s, best_b >= entry_px + 0.05
    """
    now_ts = 1700000000.0
    harvester.active_positions = {
        "POS_RATCHET": {
            "trade_id": "POS_RATCHET",
            "market_id": "MKT_RATCHET",
            "token_id": "TOK_UP",
            "target_token": "UP",
            "asset": "BTC",
            "entry_price": 0.65,
            "entry_shares": 30.0,
            "remaining_shares": 30.0,
            "candle_open_spot": 60000.0,
            "candle_expiry_ts": now_ts + 300.0,  # TTE = 300s
            "exit_order_id": "order_tp_123",
            "target_exit_price": 0.98,
            "status": "EXIT_RESTING",
            "max_seen_bid": 0.86,  # 0.86 >= max(0.84, 0.65 + 0.14) -> armed! trail_floor = 0.86 - 0.08 = 0.78
            "trailing_ratchet_detected_ts": now_ts - 6.5,  # 6.5s elapsed
        }
    }
    # Reference spot is favorable
    harvester.get_reference_spot_price = MagicMock(return_value=60300.0)
    # Book bid dropped to 0.77 (<= 0.78 trail floor, and 0.77 >= 0.65 + 0.05 = 0.70)
    harvester.executor.get_market_book_async = AsyncMock(return_value={"bids": [{"price": "0.77", "size": "100"}]})

    with patch("time.time", return_value=now_ts):
        await harvester.check_resolutions_and_manage_positions()

    harvester.executor.cancel_order.assert_called_once_with("order_tp_123")
    harvester.executor.execute_unwind_order.assert_called_once()
    call_kwargs = harvester.executor.execute_unwind_order.call_args.kwargs
    assert call_kwargs["min_price"] == 0.75  # max(0.01, 0.77 - 0.02)


@pytest.mark.anyio
async def test_final_45s_capital_recycler(harvester):
    """
    Final-45s Capital Recycler:
    - At tte_rem <= 45.0s, if best_b >= 0.88 and best_b > entry_px + 0.03,
      cancel Maker TP and exit at best_b - 0.01 to recycle USDC before rollover.
    """
    now_ts = 1700000000.0
    harvester.active_positions = {
        "POS_RECYCLE": {
            "trade_id": "POS_RECYCLE",
            "market_id": "MKT_RECYCLE",
            "token_id": "TOK_UP",
            "target_token": "UP",
            "asset": "BTC",
            "entry_price": 0.70,
            "entry_shares": 30.0,
            "remaining_shares": 30.0,
            "candle_open_spot": 60000.0,
            "candle_expiry_ts": now_ts + 40.0,  # TTE = 40s <= 45s
            "exit_order_id": "order_tp_123",
            "target_exit_price": 0.98,
            "status": "EXIT_RESTING",
        }
    }
    harvester.get_reference_spot_price = MagicMock(return_value=60200.0)
    # Book bid is 0.92 >= 0.88 and > 0.70 + 0.03
    harvester.executor.get_market_book_async = AsyncMock(return_value={"bids": [{"price": "0.92", "size": "100"}]})

    with patch("time.time", return_value=now_ts):
        await harvester.check_resolutions_and_manage_positions()

    harvester.executor.cancel_order.assert_called_once_with("order_tp_123")
    harvester.executor.execute_unwind_order.assert_called_once()
    call_kwargs = harvester.executor.execute_unwind_order.call_args.kwargs
    assert call_kwargs["min_price"] == 0.91  # max(0.01, 0.92 - 0.01)


def test_paper_trader_3zone_salvage(tmp_path, monkeypatch):
    """
    Verifies PolymarketForwardPaperTrader executes CONFIRMED_OPPOSITE_BREAKOUT_SALVAGE
    adhering strictly to Zone 2 (20s) requirements.
    """
    monkeypatch.setattr("src.polymarket_research.polymarket_paper_trader.DEV_LEDGER_FILE", tmp_path / "dev.jsonl")
    monkeypatch.setattr("src.polymarket_research.polymarket_paper_trader.VALIDATION_LEDGER_FILE", tmp_path / "val.jsonl")
    monkeypatch.setattr("src.polymarket_research.polymarket_paper_trader.STATE_FILE", tmp_path / "state.json")

    paper = PolymarketForwardPaperTrader(paper_latency_ms=0)
    m_id = "MKT_PAPER_SALVAGE"
    t_start = 1700000000.0

    trade = {
        "trade_id": "TRADE_SALVAGE_Z2",
        "market_id": m_id,
        "title": "ETH 1H Down",
        "target_token": "DOWN",
        "entry_unix": t_start - 300.0,
        "candle_open_spot": 2400.0,
        "strike_price": 2400.0,
        "shares_bought": 50.0,
        "notional_usd": 37.50,
        "taker_fee_usd": 0.40,
        "status": "OPEN",
    }
    paper.open_trades[m_id] = [trade]

    # Event 1 at t_start: Spot rallies to 2404.0 (+0.167% adverse > 0.12% Zone 2 start), TTE = 600s
    telem_1 = {
        "timestamp_unix": t_start,
        "spot_at_t0": 2404.0,
        "seconds_to_expiry": 600.0,
        "DOWN": {"best_bid": 0.25, "best_ask": 0.28},
    }
    closed = paper.check_maker_tp_fills(m_id, telem_1)
    assert len(closed) == 0
    assert trade["status"] == "OPEN"
    assert trade.get("opposite_breakout_start_ts") == t_start

    # Event 2 at t_start + 21.0s: Spot at 2403.0 (+0.125% adverse >= 0.10%), duration 21s >= 20s
    telem_2 = {
        "timestamp_unix": t_start + 21.0,
        "spot_at_t0": 2403.0,
        "seconds_to_expiry": 579.0,
        "DOWN": {"best_bid": 0.22, "best_ask": 0.25},
    }
    closed = paper.check_maker_tp_fills(m_id, telem_2)
    assert len(closed) == 1
    closed_trade = closed[0]
    assert closed_trade["status"] == "CLOSED"
    assert closed_trade["exit_reason"] == "CONFIRMED_OPPOSITE_BREAKOUT_SALVAGE"
    assert closed_trade["won"] is False
    assert closed_trade["exit_price"] == 0.22
    assert closed_trade["payout_usd"] == 11.00  # 50 shares * 0.22


def test_paper_trader_trailing_ratchet(tmp_path, monkeypatch):
    """
    Verifies PolymarketForwardPaperTrader executes TRAILING_PROFIT_RATCHET_UNWIND
    when peak bid hits arm threshold and drops <= trail floor for >= 6.0s.
    """
    monkeypatch.setattr("src.polymarket_research.polymarket_paper_trader.DEV_LEDGER_FILE", tmp_path / "dev.jsonl")
    monkeypatch.setattr("src.polymarket_research.polymarket_paper_trader.VALIDATION_LEDGER_FILE", tmp_path / "val.jsonl")
    monkeypatch.setattr("src.polymarket_research.polymarket_paper_trader.STATE_FILE", tmp_path / "state.json")

    paper = PolymarketForwardPaperTrader(paper_latency_ms=0)
    m_id = "MKT_PAPER_RATCHET"
    t_start = 1700000000.0

    trade = {
        "trade_id": "TRADE_RATCHET_1",
        "market_id": m_id,
        "title": "BTC 1H Up",
        "target_token": "UP",
        "entry_unix": t_start - 300.0,
        "entry_price": 0.65,
        "candle_open_spot": 60000.0,
        "strike_price": 60000.0,
        "shares_bought": 40.0,
        "notional_usd": 26.00,
        "taker_fee_usd": 0.30,
        "status": "OPEN",
    }
    paper.open_trades[m_id] = [trade]

    # Event 1: Bid rallies to 0.86 (arms ratchet: 0.86 >= max(0.84, 0.65+0.14), trail floor = 0.78)
    telem_1 = {
        "timestamp_unix": t_start,
        "spot_at_t0": 60300.0,
        "seconds_to_expiry": 500.0,
        "UP": {"best_bid": 0.86, "best_ask": 0.87},
    }
    closed = paper.check_maker_tp_fills(m_id, telem_1)
    assert len(closed) == 0
    assert trade["max_seen_bid"] == 0.86

    # Event 2: Bid drops to 0.77 (<= 0.78 trail floor), timer starts
    telem_2 = {
        "timestamp_unix": t_start + 10.0,
        "spot_at_t0": 60250.0,
        "seconds_to_expiry": 490.0,
        "UP": {"best_bid": 0.77, "best_ask": 0.78},
    }
    closed = paper.check_maker_tp_fills(m_id, telem_2)
    assert len(closed) == 0
    assert trade.get("trailing_ratchet_start_ts") == t_start + 10.0

    # Event 3: 6.5s later, bid still at 0.77 -> triggers ratchet unwind!
    telem_3 = {
        "timestamp_unix": t_start + 16.5,
        "spot_at_t0": 60240.0,
        "seconds_to_expiry": 483.5,
        "UP": {"best_bid": 0.77, "best_ask": 0.78},
    }
    closed = paper.check_maker_tp_fills(m_id, telem_3)
    assert len(closed) == 1
    assert closed[0]["exit_reason"] == "TRAILING_PROFIT_RATCHET_UNWIND"
    assert closed[0]["won"] is True
    assert closed[0]["exit_price"] == 0.77
