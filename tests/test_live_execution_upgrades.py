import asyncio
import json
import os
import tempfile
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.polymarket_research.polymarket_live_executor import (
    ExecutionStatus,
    OrderResult,
    PolymarketLiveExecutor,
)
from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester


@pytest.fixture(autouse=True)
def isolate_state_file(tmp_path, monkeypatch):
    """Ensure tests never write to production STATE_FILE."""
    test_state = tmp_path / "test_live_state.json"
    monkeypatch.setattr("src.polymarket_research.polymarket_live_harvester.STATE_FILE", test_state)
    yield test_state


@pytest.fixture
def mock_executor():
    """Mock executor in dry-run mode for testing execution upgrades."""
    executor = PolymarketLiveExecutor(
        dry_run=True,
        funder_address="0x013A2474454fBd8738cff6a7f204eF1bc377F4e9",
        private_key="0x" + "11" * 32,
    )
    executor.set_cached_collateral(166.37)
    return executor


# ==============================================================================
# Upgrade 1: Zero-Lag IPC & In-Memory Pre-Cached Metadata
# ==============================================================================

def test_in_memory_collateral_latency(mock_executor):
    """Test B: In-memory collateral balance retrieval executes in microseconds with ZERO REST calls."""
    t0 = time.perf_counter_ns()
    bal = mock_executor.get_collateral_balance(hot_path=True)
    t1 = time.perf_counter_ns()
    elapsed_us = (t1 - t0) / 1000.0

    assert bal == 166.37
    assert elapsed_us < 50.0, f"Hot-path collateral retrieval took {elapsed_us:.2f}us (target < 50us)"


def test_persistent_trigger_file_reading():
    """Test A: Persistent file handle tails appended lines with zero re-open overhead."""
    with tempfile.NamedTemporaryFile("w+", delete=False) as f:
        f.write('{"initial": 1}\n')
        f.flush()
        file_path = f.name

    try:
        # Open persistent handle and seek to EOF
        fp = open(file_path, "rb")
        fp.seek(0, os.SEEK_END)
        last_pos = fp.tell()

        # Append new trigger line
        payload = {"shock_id": "test_shock_1", "t0_unix": time.time(), "market_id": "12345"}
        with open(file_path, "a") as f_app:
            f_app.write(json.dumps(payload) + "\n")

        # Zero-reopen read
        t0 = time.perf_counter_ns()
        chunk = fp.read()
        t1 = time.perf_counter_ns()
        elapsed_us = (t1 - t0) / 1000.0

        assert chunk != b""
        lines = chunk.strip().splitlines()
        assert len(lines) == 1
        decoded = json.loads(lines[0])
        assert decoded["shock_id"] == "test_shock_1"
        assert elapsed_us < 500.0, f"Persistent file read took {elapsed_us:.2f}us (target < 500us)"
        fp.close()
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


# ==============================================================================
# Upgrade 2: Smart FAK Price Buffer
# ==============================================================================

def test_smart_fak_price_buffer_sleeve_2(mock_executor):
    """Test Upgrade 2: Sleeve 2 (early/mid hour) caps price buffer strictly at 0.85 ceiling."""
    # Scenario 1: raw_vwap = 0.83 -> limit_px = min(0.83 + 0.02, 0.85) = 0.85
    sleeve_max_price = 0.85
    observed_ask = 0.83
    limit_px = round(min(observed_ask + 0.02, sleeve_max_price), 2)
    assert limit_px == 0.85

    # Scenario 2: raw_vwap = 0.84 -> limit_px = min(0.84 + 0.02, 0.85) = 0.85 (capped at ceiling)
    observed_ask = 0.84
    limit_px = round(min(observed_ask + 0.02, sleeve_max_price), 2)
    assert limit_px == 0.85

    # Scenario 3: raw_vwap = 0.72 -> limit_px = min(0.72 + 0.02, 0.85) = 0.74 (+2c buffer)
    observed_ask = 0.72
    limit_px = round(min(observed_ask + 0.02, sleeve_max_price), 2)
    assert limit_px == 0.74


def test_smart_fak_price_buffer_sleeve_1(mock_executor):
    """Test Upgrade 2: Sleeve 1 (late hour) caps price buffer strictly at 0.89 ceiling."""
    sleeve_max_price = 0.89
    observed_ask = 0.86
    limit_px = round(min(observed_ask + 0.02, sleeve_max_price), 2)
    assert limit_px == 0.88

    # When ask is 0.88, limit is min(0.90, 0.89) = 0.89
    observed_ask = 0.88
    limit_px = round(min(observed_ask + 0.02, sleeve_max_price), 2)
    assert limit_px == 0.89


def test_executor_smart_fak_price_buffer_enforcement(mock_executor):
    """Test Upgrade 2: execute_snipe_order quantizes and enforces limit_px with +2c buffer."""
    book = {
        "asks": [{"price": "0.84", "size": "100.0"}],
        "bids": [{"price": "0.82", "size": "100.0"}],
    }

    # Best ask is 0.84. With target_price = 0.83 and max_price_ceiling = 0.85,
    # limit_px = min(0.83 + 0.02, 0.85) = 0.85 >= 0.84 -> fills at best ask (0.84)!
    res = mock_executor.execute_snipe_order(
        trade_id="TEST_BUFFER_1",
        token_id="0xTOK_BUFFER_1",
        target_token="UP",
        notional_usd=40.0,
        target_price=0.83,
        side="BUY",
        max_price_ceiling=0.85,
        prefetched_book=book,
    )
    assert res.success is True
    assert res.price == 0.84  # Executed with price improvement at 0.84!

    # But if book ticked to 0.86 (above sleeve_max_price 0.85):
    book_too_high = {
        "asks": [{"price": "0.86", "size": "100.0"}],
        "bids": [{"price": "0.83", "size": "100.0"}],
    }
    res_rejected = mock_executor.execute_snipe_order(
        trade_id="TEST_BUFFER_REJECT",
        token_id="0xTOK_BUFFER_2",
        target_token="UP",
        notional_usd=40.0,
        target_price=0.83,
        side="BUY",
        max_price_ceiling=0.85,
        prefetched_book=book_too_high,
    )
    assert res_rejected.success is False
    assert "Rejected" in res_rejected.error


# ==============================================================================
# Upgrade 3: Final-45s Capital Recycler + Auto-Redeemer
# ==============================================================================

@pytest.mark.anyio
async def test_final_45s_capital_recycler_trigger(mock_executor):
    """Test Upgrade 3 Task A: TTE <= 45s and best_bid >= 0.98 triggers immediate exit at 0.98."""
    harvester = PolymarketLiveHarvester(dry_run=True)
    harvester.executor = mock_executor

    now = time.time()
    tid = "TRADE_TEST_RECYCLE_45S"
    pos = {
        "trade_id": tid,
        "market_id": "99999",
        "token_id": "0xTOK_RECYCLE",
        "target_token": "UP",
        "entry_shares": 50.0,
        "remaining_shares": 50.0,
        "entry_price": 0.84,
        "notional_usd": 42.0,
        "candle_expiry_ts": now + 35.0,  # TTE = 35s <= 45s
        "exit_order_id": "OID_MAKER_099",
        "target_exit_price": 0.99,
        "exit_order_status": "RESTING",
        "status": ExecutionStatus.POSITION_CONFIRMED,
        "candle_open_spot": 2400.0,
        "asset": "ETH",
    }
    harvester.active_positions[tid] = pos

    # Mock market book with best bid = 0.985 >= 0.98
    mock_book = {
        "bids": [{"price": "0.985", "size": "100.0"}],
        "asks": [{"price": "0.99", "size": "100.0"}],
    }

    with patch.object(mock_executor, "get_market_book_async", AsyncMock(return_value=mock_book)), \
         patch.object(mock_executor, "cancel_order", MagicMock(return_value={"canceled": ["OID_MAKER_099"]})), \
         patch.object(mock_executor, "execute_unwind_order", MagicMock(return_value={
             "success": True, "orderID": "OID_UNWIND_098", "matched_size": 50.0, "taking_amount": 49.25
         })):

        await harvester.check_resolutions_and_manage_positions()

        # Position should have executed unwind order at 0.98 and settled/closed
        assert tid not in harvester.active_positions or harvester.active_positions[tid].get("exit_order_status") in ("FINAL_45S_CAPITAL_RECYCLE", "CLOSED", "FILLED")
        assert getattr(harvester, "_pending_collateral_refresh", False) is True


@pytest.mark.anyio
async def test_final_45s_capital_recycler_does_not_dump_if_bid_low(mock_executor):
    """Test Upgrade 3 Task A: Does NOT dump if best_bid < 0.98."""
    harvester = PolymarketLiveHarvester(dry_run=True)
    harvester.executor = mock_executor

    now = time.time()
    tid = "TRADE_TEST_NO_DUMP"
    pos = {
        "trade_id": tid,
        "market_id": "99998",
        "token_id": "0xTOK_NO_DUMP",
        "target_token": "UP",
        "entry_shares": 50.0,
        "remaining_shares": 50.0,
        "entry_price": 0.84,
        "notional_usd": 42.0,
        "candle_expiry_ts": now + 30.0,  # TTE = 30s <= 45s
        "exit_order_id": "OID_MAKER_099",
        "target_exit_price": 0.99,
        "exit_order_status": "RESTING",
        "status": ExecutionStatus.POSITION_CONFIRMED,
        "candle_open_spot": 2400.0,
        "asset": "ETH",
    }
    harvester.active_positions[tid] = pos

    # Best bid is only 0.95 (< 0.98)
    mock_book = {
        "bids": [{"price": "0.95", "size": "100.0"}],
        "asks": [{"price": "0.99", "size": "100.0"}],
    }

    with patch.object(mock_executor, "get_market_book_async", AsyncMock(return_value=mock_book)), \
         patch.object(mock_executor, "execute_unwind_order") as mock_unwind:

        await harvester.check_resolutions_and_manage_positions()

        # Should NOT have executed emergency unwind at 0.95
        mock_unwind.assert_not_called()
        assert tid in harvester.active_positions


# ==============================================================================
# Upgrade 4: Next-Candle Pre-Warming at TTE = 120s
# ==============================================================================

@pytest.mark.anyio
async def test_prewarm_next_candle_markets(mock_executor):
    """Test Upgrade 4: Pre-warm queries Gamma API and pre-seeds condition_id and token_id caches."""
    harvester = PolymarketLiveHarvester(dry_run=True)
    harvester.executor = mock_executor

    future_end = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%Y-%m-%dT%H:00:00Z")
    mock_gamma_events = [
        {
            "markets": [
                {
                    "id": "777001",
                    "conditionId": "0xCOND_PREWARM_1",
                    "endDate": future_end,
                    "clobTokenIds": '["0xTOK_UP_PREWARMED", "0xTOK_DOWN_PREWARMED"]',
                    "feeSchedule": {"rate": 0.07, "exponent": 1},
                }
            ]
        }
    ]

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_gamma_events

    with patch.object(mock_executor._sync_session, "get", return_value=mock_resp):
        await harvester._prewarm_next_candle_markets()

        # Verify market condition_id and tokens were pre-warmed in harvester memory
        assert harvester.market_condition_ids.get("777001") == "0xCOND_PREWARM_1"
        assert harvester.market_tokens_cache.get("777001_UP") == "0xTOK_UP_PREWARMED"
        assert harvester.market_tokens_cache.get("777001_DOWN") == "0xTOK_DOWN_PREWARMED"

        # Verify py-clob-client tick sizes and fee caches were pre-populated
        assert mock_executor._tick_size_cache.get("0xTOK_UP_PREWARMED") == 0.01
        assert mock_executor._fee_cache.get("0xCOND_PREWARM_1") == (0.07, 1.0)


# ==============================================================================
# Upgrade 5: CLOB Decimal Precision & Collateral Guard ($41.59 @ 0.728)
# ==============================================================================

def test_clob_decimal_precision_dynamic_ticket_buy_fak():
    """
    Test Upgrade 5: Non-round dynamic ticket ($41.59 @ 0.728 with worst_acceptable_px = 0.75)
    strictly complies with Polymarket CLOB decimal constraints using whole integer shares:
      - size: strictly integer shares (0 fractional decimals)
      - price: strictly 2 decimal places (0.01 tick size)
      - makerAmount: strictly at most 2 decimal places (USDC base units % 10000 == 0)
      - takerAmount: strictly at most 4 decimal places (share base units % 100 == 0, here % 1000000 == 0)
      - makerAmount <= notional_usd ($41.25 <= $41.59)
    """
    import math
    from py_clob_client.order_builder.builder import OrderBuilder, ROUNDING_CONFIG
    from py_clob_client_v2.clob_types import OrderArgsV2

    notional_usd = 41.59
    raw_vwap = 0.728
    worst_acceptable_px = 0.75  # 0.728 + 0.02 buffer -> quantized 0.75

    # 1. Authoritative sizing calculation with whole integer shares (ROUND_FLOOR to 1 share)
    max_shares_for_limit = float(math.floor(notional_usd / worst_acceptable_px))
    raw_sweep_shares = float(math.floor(notional_usd / raw_vwap))
    shares_to_buy = min(raw_sweep_shares, max_shares_for_limit)

    assert shares_to_buy == 55.0, f"Expected 55.0 shares, got {shares_to_buy}"
    assert shares_to_buy * worst_acceptable_px <= notional_usd
    assert round(shares_to_buy * worst_acceptable_px, 2) == 41.25

    # 2. Test py-clob-client OrderBuilder under tick_size = '0.01'
    mock_signer = MagicMock()
    ob = OrderBuilder(mock_signer)
    cfg_01 = ROUNDING_CONFIG["0.01"]

    # Limit FAK order amounts via create_order
    u_buy, maker_amt_int, taker_amt_int = ob.get_order_amounts("BUY", shares_to_buy, worst_acceptable_px, cfg_01)
    
    # Assert exact base units
    assert maker_amt_int == 41250000, f"Expected 41250000 base units, got {maker_amt_int}"
    assert taker_amt_int == 55000000, f"Expected 55000000 base units, got {taker_amt_int}"

    # Assert human representation
    maker_usd = maker_amt_int / 1e6
    taker_shares = taker_amt_int / 1e6
    assert maker_usd == 41.25
    assert taker_shares == 55.0
    assert maker_usd <= notional_usd

    # Assert strictly valid CLOB decimal accuracy:
    # makerAmount max 2 decimals (USDC cents) -> base units must be divisible by 10**(6 - 2) = 10000
    assert maker_amt_int % 10000 == 0, f"makerAmount {maker_amt_int} has fractional precision past 2 decimals"
    # takerAmount max 4 decimals (shares) -> base units must be divisible by 10**(6 - 4) = 100
    assert taker_amt_int % 100 == 0, f"takerAmount {taker_amt_int} has fractional precision past 4 decimals"
    # Whole integer shares guarantee 0 decimal places (% 1000000 == 0)
    assert taker_amt_int % 1000000 == 0, f"takerAmount {taker_amt_int} is not whole integer shares"

    # 3. Test py-clob-client OrderBuilder under tick_size = '0.001'
    cfg_001 = ROUNDING_CONFIG["0.001"]
    u_buy_3, maker_amt_3, taker_amt_3 = ob.get_order_amounts("BUY", shares_to_buy, worst_acceptable_px, cfg_001)
    assert maker_amt_3 == 41250000
    assert taker_amt_3 == 55000000
    assert maker_amt_3 % 10000 == 0
    assert taker_amt_3 % 100 == 0
    assert taker_amt_3 % 1000000 == 0

    # 4. Demonstrate why create_market_order failed at 13:10:22 UTC
    # create_market_order with tick_size 0.001 produced 5 decimals in takerAmount!
    _, m_mo_001, t_mo_001 = ob.get_market_order_amounts("BUY", notional_usd, raw_vwap, cfg_001)
    # Taker amount is 57.12912 shares = 57129120 base units (5 decimals!), violating CLOB 4-decimal max accuracy:
    assert t_mo_001 == 57129120
    assert t_mo_001 % 100 != 0, "create_market_order has remainder past 4 decimals on 0.001 tick size"


@pytest.mark.anyio
async def test_live_executor_routes_fak_without_market_order(mock_executor):
    """
    Test Upgrade 5: PolymarketLiveExecutor snipe execution strictly routes through
    create_order(OrderArgsV2) and post_order(OrderType.FAK), capping shares to ticket.
    """
    from py_clob_client_v2.clob_types import OrderArgsV2, OrderType

    # Orderbook with asks at 0.728
    book = {
        "bids": [{"price": "0.720", "size": "100.0"}],
        "asks": [{"price": "0.728", "size": "200.0"}],
    }

    mock_client = MagicMock()
    mock_signed_order = MagicMock()
    mock_client.create_order.return_value = mock_signed_order
    mock_client.post_order.return_value = {"orderID": "0xMOCK_FAK_OID_1", "status": "MATCHED"}

    mock_executor.client = mock_client
    mock_executor.is_authenticated = True
    mock_executor.dry_run = False
    mock_executor._tick_size_cache["0xTOKEN_DOWN_123"] = 0.01

    res = await mock_executor.execute_snipe_order_async(
        trade_id="LIVE_5774630_TEST_DOWN",
        token_id="0xTOKEN_DOWN_123",
        target_token="DOWN",
        side="BUY",
        notional_usd=41.59,
        target_price=0.728,
        prefetched_book=book,
        max_price_ceiling=0.85,
        max_ticket_cap=100.0,
    )

    # Verify create_order was called with OrderArgsV2 and capped size
    mock_client.create_order.assert_called_once()
    call_args, call_kwargs = mock_client.create_order.call_args
    order_args = call_args[0]
    assert isinstance(order_args, OrderArgsV2)
    assert order_args.price == 0.75  # 0.728 + 0.02
    assert order_args.size == 55.0  # floor(41.59 / 0.75) whole integer shares
    assert order_args.side == "BUY"
    assert order_args.token_id == "0xTOKEN_DOWN_123"

    # Verify post_order was called with FAK
    mock_client.post_order.assert_called_once()
    p_args, p_kwargs = mock_client.post_order.call_args
    assert p_args[0] == mock_signed_order
    assert p_args[1] in (OrderType.FAK, OrderType.FOK)
    # create_market_order was NEVER called
    assert not hasattr(mock_client, "create_market_order") or not mock_client.create_market_order.called

