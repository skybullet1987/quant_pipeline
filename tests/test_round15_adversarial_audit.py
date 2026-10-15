"""
Unit and Adversarial Invariant Tests for Round 15 Audit Remediations:
- FINDING-15-01: Cross-venue flow directional aggregation, early break, and unified cooldown
- FINDING-15-02: PASSIVE_STOP_RESTING fill polling, single-pass escalation, and urgent supervision
- FINDING-15-03: HTTP 408 exclusion from deterministic 4xx client errors, retryable flag, and crossed-book repricing
- FINDING-15-04: Pre-expiry fsync deduplication and 60/40 tranche threshold alignment (>= $20)
"""

import asyncio
import time
from datetime import datetime, timezone
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from collections import deque
from decimal import Decimal

from src.polymarket_research.polymarket_terminal_recorder import PolymarketDualFeed1HRecorder
from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor
from src.polymarket_research.polymarket_live_harvester import (
    PolymarketLiveHarvester,
    ExecutionStatus,
)


class TestRound15AuditRemediation:

    def test_finding_15_01_cross_venue_directional_aggregation(self):
        """
        FINDING-15-01: If FUTURES has a massive BUY sweep and SPOT has a small SELL print 5ms later,
        the combined 100ms trigger on SPOT tick must aggregate directionally so shock_dir is 'BUY',
        not inverted to 'SELL'.
        """
        rec = PolymarketDualFeed1HRecorder(
            asset="BTC",
            shock_threshold=100_000.0,
        )
        now_ns = time.monotonic_ns()

        # Populate futures_trades with $2,000,000 BUY 10ms ago
        # Schema: (t_mono, trade_id, px, ntl, buyer, fee)
        rec.futures_trades.append((now_ns - 10_000_000, 1, 65000.0, 2_000_000.0, True, 0.0))

        # Add a small $10,000 SELL print on SPOT at now_ns
        rec.spot_trades.append((now_ns, 2, 65000.0, 10_000.0, False, 0.0))

        # Add a mock market and books so shock handling doesn't return early
        mock_book = MagicMock()
        mock_book.get_metrics.return_value = {
            "best_bid": 0.50,
            "best_ask": 0.52,
            "mid": 0.51,
            "spread_bps": 20.0,
            "depth_10bps": 1000.0,
        }
        rec.books["UP"] = mock_book
        rec.books["DOWN"] = mock_book
        rec.current_market = {
            "market_id": "m123",
            "title": "BTC 1H",
            "end_dt": datetime.now(timezone.utc),
            "tokens": {"UP": "tok_up", "DOWN": "tok_down"},
        }

        burst_calls = []
        rec.capture_shock_burst = MagicMock(side_effect=lambda *args, **kwargs: burst_calls.append(args))

        # Evaluate shock on SPOT trade
        with patch("asyncio.create_task") as mock_create_task:
            rec.evaluate_shock(recv_mono_ns=now_ns, event_ts_ms=int(time.time() * 1000), source="SPOT")

            # Verify capture_shock_burst was called
            assert rec.capture_shock_burst.called
            call_args = rec.capture_shock_burst.call_args[0]
            # Args signature: (t0_sec, t0_mono_ns, source, vol_100ms, shock_dir, ofi, ...)
            vol_100ms = call_args[3]
            shock_dir = call_args[4]
            ofi = call_args[5]

            # Verify directional aggregation:
            assert shock_dir == "BUY"
            assert vol_100ms >= 2_000_000.0
            assert ofi > 0.90  # Positive OFI from BUY dominance

    def test_finding_15_01_early_break_performance(self):
        """
        FINDING-15-01: Ensure other_queue scanning breaks early on t_m < cutoff_ns
        rather than iterating over all 15k items.
        """
        rec = PolymarketDualFeed1HRecorder(
            asset="BTC",
            shock_threshold=100_000.0,
        )
        now_ns = time.monotonic_ns()

        # Add 10,000 old trades (> 1 second old)
        for i in range(10000):
            rec.futures_trades.append((now_ns - 2_000_000_000 - i * 1000, i, 65000.0, 100.0, True, 0.0))

        # Add 1 small spot trade
        rec.spot_trades.append((now_ns, 99999, 65000.0, 650.0, True, 0.0))

        t0 = time.perf_counter()
        rec.evaluate_shock(recv_mono_ns=now_ns, event_ts_ms=int(time.time() * 1000), source="SPOT")
        elapsed_us = (time.perf_counter() - t0) * 1e6
        # Early break ensures this takes < 10ms (10,000us)
        assert elapsed_us < 10000.0

    def test_finding_15_03_http_408_exclusion(self):
        """
        FINDING-15-03: HTTP 408 (Request Timeout) must NOT be classified as is_client_err=True.
        It must remain outcome_unknown=True so that executor reserves inventory and does not
        assume the order never hit the book.
        """
        executor = PolymarketLiveExecutor(
            private_key="0x" + "1" * 64,
            dry_run=False,
        )
        executor.client = MagicMock()
        executor.auth_mode = "LIVE"
        executor.is_authenticated = True

        # Mock an HTTP 408 Request Timeout exception
        class HTTP408Error(Exception):
            status_code = 408
            error_message = "Request Timeout"

        executor.client.post_order.side_effect = HTTP408Error("Request Timeout")
        executor.get_unreserved_conditional_balance = MagicMock(return_value=100.0)

        res = executor.post_maker_exit_order("tok_123", 0.85, 10.0, "SELL")
        assert res["outcome_unknown"] is True
        assert res["success"] is False
        assert "EXCEPTION_POST_" in res.get("reservation_id", "")

    def test_finding_15_03_client_rejection_retryable(self):
        """
        FINDING-15-03: When CLOB rejects with errorMsg (e.g. crossed book or delay),
        outcome_unknown=False and retryable=True must be returned so caller can re-attempt.
        """
        executor = PolymarketLiveExecutor(
            private_key="0x" + "1" * 64,
            dry_run=False,
        )
        executor.client = MagicMock()
        executor.auth_mode = "LIVE"
        executor.is_authenticated = True
        executor.get_unreserved_conditional_balance = MagicMock(return_value=100.0)

        # Exchange returns dict with errorMsg
        executor.client.post_order.return_value = {
            "errorMsg": "Order crosses book",
            "orderID": None,
        }

        res = executor.post_maker_exit_order("tok_123", 0.85, 10.0, "SELL")
        assert res["success"] is False
        assert res["outcome_unknown"] is False
        assert res["retryable"] is True
        assert "crosses book" in res["error"].lower()

    def test_finding_15_02_passive_stop_resting_fill_polling(self):
        """
        FINDING-15-02: While in PASSIVE_STOP_RESTING (elapsed < 5.0s),
        harvester must poll fill summary and close position if filled.
        """
        async def _run():
            harvester = PolymarketLiveHarvester(dry_run=True)
            tid = "LIVE_TEST_PASSIVE_STOP"
            now = time.time()
            pos = {
                "trade_id": tid,
                "token_id": "tok_abc",
                "status": ExecutionStatus.POSITION_CONFIRMED,
                "exit_order_status": "PASSIVE_STOP_RESTING",
                "exit_order_id": "OID_PASSIVE_01",
                "passive_stop_start_ts": now - 1.0,  # 1.0s elapsed (< 5.0s)
                "target_exit_price": 0.65,
                "entry_price": 0.70,
                "entry_shares": 20.0,
                "remaining_shares": 20.0,
                "notional_usd": 14.0,
                "candle_expiry_ts": now + 600.0,
            }
            harvester.active_positions[tid] = pos

            # Mock order fill summary showing full fill
            mock_summary = {
                "order_id": "OID_PASSIVE_01",
                "status": "MATCHED",
                "matched": 20.0,
                "price": 0.65,
                "cash": 13.0,
                "fee_cash": 0.0,
                "terminal": True,
            }
            harvester.executor.get_order_fill_summary = MagicMock(return_value=mock_summary)
            harvester.executor.get_open_orders = MagicMock(return_value=[])
            harvester.executor.get_market_book_async = AsyncMock(return_value={
                "bids": [{"price": 0.64, "size": 100}],
                "asks": [{"price": 0.66, "size": 100}],
            })

            # Run supervision check
            await harvester.check_resolutions_and_manage_positions()

            # Position should be closed as PASSIVE_STOP_MAKER_FILLED
            assert tid not in harvester.active_positions
            closed = next((p for p in harvester.closed_positions if p.get("trade_id") == tid), None)
            assert closed is not None
            assert closed["close_reason"] == "PASSIVE_STOP_MAKER_FILLED"

        asyncio.run(_run())

    def test_finding_15_04_tranche_threshold_alignment(self):
        """
        FINDING-15-04: Tickets with notional >= $20.0 must configure sequential
        iceberg tranches (60% / 40%) with t1_px and t2_px.
        """
        harvester = PolymarketLiveHarvester(dry_run=True)
        tid = "LIVE_TEST_TRANCHE_ALIGN"
        pos = {
            "trade_id": tid,
            "token_id": "tok_xyz",
            "status": ExecutionStatus.POSITION_CONFIRMED,
            "entry_price": 0.75,
            "entry_shares": 30.0,
            "remaining_shares": 30.0,
            "notional_usd": 22.50,  # >= $20.0
            "target_exit_price": 0.83,
            "candle_expiry_ts": time.time() + 600.0,
        }

        posted = harvester._attempt_maker_exit_post(tid, pos)
        assert posted is True
        assert "exit_tranches" in pos
        tranches = pos["exit_tranches"]
        assert len(tranches) == 2
        assert tranches[0]["size"] == 18.0  # 60% of 30
        assert tranches[1]["size"] == 12.0  # 40% of 30
        assert tranches[0]["price"] == 0.83
        assert tranches[1]["price"] == round(0.75 + 0.14, 4)  # 0.89
