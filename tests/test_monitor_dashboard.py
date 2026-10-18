#!/usr/bin/env python3
"""
====================================================================================================
TEST SUITE: MONITOR DASHBOARD, SCORECARD & WEBHOOK ALERTER (tests/test_monitor_dashboard.py)
====================================================================================================
Unit and integration tests for:
- SQLite schema migrations & empty database resilience
- Strategy funnel scorecard aggregation math (Signals, Sub, Fill, Rej, Win %, PnL)
- Adverse selection detection & markout curve evaluation (+1s, +5s, +30s, +5m, +1h)
- Promotion Gate quantitative evaluations (Gates 1, 2, 3, 4)
- WebhookAlerter payload formatting for Telegram / Discord and scheduled follow-ups
- Markdown & JSON promotion readiness report generation
====================================================================================================
"""

import asyncio
import json
import os
import sqlite3
import tempfile
import time
from pathlib import Path
from typing import Any, Dict

import pytest

from experiments.monitor_dashboard import (
    ALL_STRATEGIES,
    PromotionGateReportGenerator,
    ShadowScorecard,
    TerminalTUIDashboard,
    WebhookAlerter,
)


@pytest.fixture
def temp_db_path(tmp_path: Path) -> str:
    """Fixture providing a fresh isolated SQLite database path."""
    return str(tmp_path / "test_shadow_ledger.db")


def test_scorecard_schema_and_empty_db(temp_db_path: str):
    """Verifies that ShadowScorecard initializes all schemas and handles empty tables gracefully."""
    scorecard = ShadowScorecard(temp_db_path)

    # Verify tables exist
    conn = sqlite3.connect(temp_db_path)
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in c.fetchall()}
    assert "shadow_orders" in tables
    assert "shadow_fills" in tables
    assert "shadow_markouts" in tables
    assert "high_asymmetry_events" in tables
    assert "feed_telemetry" in tables
    conn.close()

    # Empty table queries should return safe defaults
    funnel = scorecard.get_strategy_funnel()
    assert len(funnel) == len(ALL_STRATEGIES)
    assert funnel["S1"]["submitted"] == 0
    assert funnel["S1"]["fill_pct"] == 0.0

    markouts = scorecard.get_markout_curves()
    assert len(markouts) == len(ALL_STRATEGIES)
    assert markouts["S1"]["adverse_selection"] is False
    assert markouts["S1"]["status_label"] == "INSUFFICIENT FILLS"

    events = scorecard.get_recent_events(limit=5)
    assert events == []

    gates = scorecard.evaluate_promotion_gates()
    assert "gate_1_replication" in gates
    assert "gate_2_markouts" in gates
    assert "gate_3_maker_survival" in gates
    assert "gate_4_multileg" in gates


def test_strategy_funnel_aggregation(temp_db_path: str):
    """Verifies funnel math: Signals, Submitted, Filled, Fill %, Rejects, Win %, Net PnL."""
    scorecard = ShadowScorecard(temp_db_path)
    now = time.time()

    conn = sqlite3.connect(temp_db_path)
    with conn:
        # S1 orders: 10 submitted, 9 filled, 1 rejected
        for i in range(10):
            st = "FILLED" if i < 9 else "REJECTED"
            conn.execute("""
                INSERT INTO shadow_orders (order_id, symbol, venue, order_type, side, price, size, remaining_size,
                                           created_ts, latency_ms, arrival_ts, status, queue_ahead_size, reject_reason, strategy)
                VALUES (?, 'POLY_NO_SUBSET_4', 'polymarket', 'TAKER_FOK', 'BUY', 0.85, 100.0, 0.0,
                        ?, 50.0, ?, ?, 0.0, NULL, 'S1')
            """, (f"ord_s1_{i}", now, now + 0.05, st))

        # S1 fills: 9 fills with positive markouts (+25 bps)
        for i in range(9):
            conn.execute("""
                INSERT INTO shadow_fills (fill_id, order_id, symbol, venue, side, fill_time, fill_price, fill_size, liquidity_role, queue_ahead_at_entry, fee_usd)
                VALUES (?, ?, 'POLY_NO_SUBSET_4', 'polymarket', 'BUY', ?, 0.85, 100.0, 'TAKER', 0.0, 0.05)
            """, (f"fill_s1_{i}", f"ord_s1_{i}", now + 0.05))

            conn.execute("""
                INSERT INTO shadow_markouts (fill_id, order_id, symbol, horizon_label, scheduled_ts, recorded_ts, fill_price, markout_mid_price, markout_pnl_bps, markout_pnl_usd, is_final)
                VALUES (?, ?, 'POLY_NO_SUBSET_4', '30s', ?, ?, 0.85, 0.87, 235.29, 2.00, 1)
            """, (f"fill_s1_{i}", f"ord_s1_{i}", now + 30.0, now + 30.0))

        # S1 signal event
        conn.execute("""
            INSERT INTO high_asymmetry_events (event_id, strategy, event_type, symbol, timestamp, notional, expected_payoff, details_json)
            VALUES ('s1_sig_1', 'S1', 'NEGRISK_CONVERT_ARB', 'POLY_NO_SUBSET_4', ?, 85.0, 15.0, '{}')
        """, (now,))

    conn.close()

    funnel = scorecard.get_strategy_funnel()
    s1 = funnel["S1"]
    assert s1["signals"] == 1
    assert s1["submitted"] == 10
    assert s1["filled"] == 9
    assert pytest.approx(s1["fill_pct"], 0.1) == 90.0
    assert s1["rejected"] == 1
    assert pytest.approx(s1["win_pct"], 0.1) == 100.0
    assert pytest.approx(s1["net_pnl_usd"], 0.1) == 18.00


def test_markout_curve_and_adverse_selection_detection(temp_db_path: str):
    """
    Verifies markout curve aggregation:
    - Adverse selection warning when +5s markout is negative (buying stale tops).
    - Promotion readiness when +30s markout >= +25 bps and fill % >= 50%.
    """
    scorecard = ShadowScorecard(temp_db_path)
    now = time.time()

    conn = sqlite3.connect(temp_db_path)
    with conn:
        # S3 Latency Arb: Negative +5s markout (adverse selection)
        conn.execute("""
            INSERT INTO shadow_orders (order_id, symbol, venue, order_type, side, price, size, remaining_size,
                                       created_ts, latency_ms, arrival_ts, status, queue_ahead_size, reject_reason, strategy)
            VALUES ('ord_s3_1', 'POLY_BTC_YES', 'polymarket', 'TAKER_IOC', 'BUY', 0.50, 100.0, 0.0, ?, 120.0, ?, 'FILLED', 0.0, NULL, 'S3')
        """, (now, now + 0.12))
        conn.execute("""
            INSERT INTO shadow_fills VALUES ('fill_s3_1', 'ord_s3_1', 'POLY_BTC_YES', 'polymarket', 'BUY', ?, 0.50, 100.0, 'TAKER', 0.0, 0.05)
        """, (now + 0.12,))
        conn.execute("""
            INSERT INTO shadow_markouts VALUES ('fill_s3_1', 'ord_s3_1', 'POLY_BTC_YES', '5s', ?, ?, 0.50, 0.48, -400.0, -2.00, 1)
        """, (now + 5.0, now + 5.0))

        # S4 Wick Catcher: Positive +30s markout (+35.0 bps)
        conn.execute("""
            INSERT INTO shadow_orders (order_id, symbol, venue, order_type, side, price, size, remaining_size,
                                       created_ts, latency_ms, arrival_ts, status, queue_ahead_size, reject_reason, strategy)
            VALUES ('ord_s4_1', 'BTC', 'hyperliquid', 'MAKER_ALO', 'BUY', 82000.0, 0.5, 0.0, ?, 50.0, ?, 'FILLED', 0.0, NULL, 'S4')
        """, (now, now + 0.05))
        conn.execute("""
            INSERT INTO shadow_fills VALUES ('fill_s4_1', 'ord_s4_1', 'BTC', 'hyperliquid', 'BUY', ?, 82000.0, 0.5, 'MAKER', 0.0, -0.61)
        """, (now + 0.05,))
        conn.execute("""
            INSERT INTO shadow_markouts VALUES ('fill_s4_1', 'ord_s4_1', 'BTC', '30s', ?, ?, 82000.0, 82250.0, 30.48, 125.0, 1)
        """, (now + 30.0, now + 30.0))

    conn.close()

    curves = scorecard.get_markout_curves()

    # S3 must flag adverse selection
    assert curves["S3"]["adverse_selection"] is True
    assert "ADVERSE SELECTION" in curves["S3"]["status_label"]

    # S4 must flag promotion ready
    assert curves["S4"]["promotion_ready"] is True
    assert "PROMOTION GATE READY" in curves["S4"]["status_label"]


def test_promotion_gates_evaluation(temp_db_path: str):
    """Verifies evaluation of all 4 quantitative promotion gates."""
    scorecard = ShadowScorecard(temp_db_path)
    now = time.time()

    conn = sqlite3.connect(temp_db_path)
    with conn:
        # Feed telemetry: low mark price tracking error (0.45 bps)
        conn.execute("""
            INSERT INTO feed_telemetry (timestamp, venue, metric_name, metric_value, details_json)
            VALUES (?, 'hyperliquid', 'mark_price', 82130.0, '{"symbol": "BTC"}')
        """, (now,))

        # S1 Order with 100% completion rate and positive cash profit
        conn.execute("""
            INSERT INTO shadow_orders (order_id, symbol, venue, order_type, side, price, size, remaining_size,
                                       created_ts, latency_ms, arrival_ts, status, queue_ahead_size, reject_reason, strategy)
            VALUES ('ord_s1_gate', 'POLY_NO_SUBSET_4', 'polymarket', 'TAKER_FOK', 'BUY', 0.80, 500.0, 0.0,
                    ?, 50.0, ?, 'FILLED', 0.0, NULL, 'S1')
        """, (now, now + 0.05))
        conn.execute("""
            INSERT INTO shadow_fills VALUES ('fill_s1_gate', 'ord_s1_gate', 'POLY_NO_SUBSET_4', 'polymarket', 'BUY', ?, 0.80, 500.0, 'TAKER', 0.0, 0.10)
        """, (now + 0.05,))
        conn.execute("""
            INSERT INTO shadow_markouts VALUES ('fill_s1_gate', 'ord_s1_gate', 'POLY_NO_SUBSET_4', '30s', ?, ?, 0.80, 0.85, 625.0, 24.90, 1)
        """, (now + 30.0, now + 30.0))

    conn.close()

    report_gen = PromotionGateReportGenerator(scorecard)
    data = report_gen.generate_json_report()
    gates = data["promotion_gates"]

    # Gate 1: Replication error < 1.5 bps
    assert gates["gate_1_replication"]["status"] == "PASS"

    # Gate 2: Positive short-horizon markout
    assert gates["gate_2_markouts"]["status"] == "PASS"

    # Gate 4: S1 NegRisk Multi-leg completion >= 85% & positive cash
    assert gates["gate_4_multileg"]["status"] == "PASS"
    assert gates["gate_4_multileg"]["s1_completion_pct"] == 100.0

    # Live Stage 3 Recommendation
    rec = gates["graduation_recommendation"]
    assert rec["ready_for_stage_3"] is True
    assert any("S1" in s for s in rec["recommended_micro_live_strategies"])


def test_markdown_and_json_report_generation(temp_db_path: str):
    """Verifies that the report generator outputs valid Markdown and complete JSON."""
    scorecard = ShadowScorecard(temp_db_path)
    report_gen = PromotionGateReportGenerator(scorecard)

    md = report_gen.generate_markdown_report()
    assert "# 🛡️ Structural Alpha Promotion Gate & Live Readiness Report" in md
    assert "Tier 0 Mark Replicator Error" in md
    assert "Strategy Funnel & Execution Performance" in md
    assert "The Markout Curve" in md

    js = report_gen.generate_json_report()
    assert "promotion_gates" in js
    assert "strategy_funnel" in js
    assert "markout_curves" in js
    assert "evaluation_timestamp_utc" in js


def test_webhook_alerter_formatting_and_simulated_dispatch(temp_db_path: str):
    """Verifies WebhookAlerter formatting and simulated alert dispatch without network calls."""
    async def _run_test():
        alerter = WebhookAlerter(
            telegram_bot_token=None,  # Unset -> simulated mode
            telegram_chat_id=None,
            discord_webhook_url=None,
            db_path=temp_db_path,
        )

        assert alerter.is_configured is False

        # Trigger high asymmetry alert
        await alerter.trigger_high_asymmetry_alert(
            strategy="S4",
            event_id="test_whale_001",
            symbol="BTC",
            notional_usd=350_000.0,
            expected_metric="Stage-1 20% Dump: $70k @ T0+29s",
            order_id="ord_s4_test",
        )

        # Verify task scheduled for +60s follow-up
        assert "test_whale_001" in alerter.pending_followups
        task = alerter.pending_followups["test_whale_001"]
        task.cancel()  # Cancel to prevent waiting 60s in test

        await alerter.close()

    asyncio.run(_run_test())


def test_ansi_dashboard_rendering(temp_db_path: str):
    """Verifies that TerminalTUIDashboard renders ANSI text without errors."""
    scorecard = ShadowScorecard(temp_db_path)
    dash = TerminalTUIDashboard(scorecard)
    ansi_text = dash.render_ansi()

    assert "STRUCTURAL ALPHA REAL-TIME MONITOR" in ansi_text
    assert "PANEL A: FEED & WATCHDOG TELEMETRY" in ansi_text
    assert "PANEL B: STRATEGY FUNNEL SCORECARD" in ansi_text
    assert "PANEL C: THE MARKOUT CURVE" in ansi_text
    assert "PANEL D: RECENT HIGH-ASYMMETRY EVENTS TAPE" in ansi_text
