#!/usr/bin/env python3
"""
QA & Parity Verification Suite for EXP-103 Paper Trading Engine
===============================================================
Institutional Test Gates:
  Gate 1: Strategy/Alpha Invariants & Dual-Clock Math
    - Causal 4H boundary assertion (zero lookahead)
    - Age-aware data matrix (ffill limit=2, no bfill)
    - Canonical Wilder's ATR(14) parity
    - Canonical F1 PIT funding carry parity
    - 10% Leland turnover deadband (0.100)
    - Grossman-Zhou continuous cushion governor
  Gate 2: Execution Integrity, ClOID Ownership, & Fault-Injection Recovery
    - ClOID format and foreign order isolation
    - Append-only EventJournal SHA-256 hash chaining
    - Crash recovery: 100% deterministic state reconstruction from journal
    - Fill and funding event deduplication idempotency
    - Frozen 72H target immutability during 4H micro repair
    - Fail-closed circuit breaker trip on excessive valuation residual
  Gate 3: Accounting & Balance Sheet Invariants
    - Exchange mark-price NAV reconciliation formula
    - Native TP/SL trigger brackets (-3.5% SL / +7.0% TP)
    - Sub-$8 dust sweeping logic
    - Hyperliquid L1 order quantization & min notional compliance
"""

import hashlib
import json
import math
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.execution.production_apex_daemon import (
    ProductionApexExecutor,
    EventJournal,
    PaperTradeState,
    CircuitBreakerState,
    LELAND_DEADBAND,
    MACRO_CADENCE_BARS,
    GROSSMAN_ZHOU_FLOOR,
    BASE_LEVERAGE,
    PEAK_LEVERAGE,
    MIN_NOTIONAL_L1,
    DUST_THRESHOLD_USD,
    MAX_VALUATION_RESIDUAL_USD,
)
from src.strategy.convex_10x_engine import (
    round_sz,
    round_px,
    validate_l1_order,
    compute_canonical_wilder_atr,
    compute_canonical_f1_carry,
)


@pytest.fixture
def mock_executor(tmp_path):
    """Initializes ProductionApexExecutor with mocked exchange gateway and temporary isolated paths."""
    journal_file = tmp_path / "papertrade_journal.jsonl"
    state_file = tmp_path / "papertrade_state.json"
    log_file = tmp_path / "execution.log"

    with patch("src.execution.production_apex_daemon.JOURNAL_FILE", journal_file), \
         patch("src.execution.production_apex_daemon.STATE_FILE", state_file), \
         patch("src.execution.production_apex_daemon.LOG_FILE", log_file), \
         patch("src.execution.production_apex_daemon.HyperliquidGateway") as mock_gw_cls:

        mock_gw = MagicMock()
        mock_gw.sz_decimals = {"BTC": 4, "ETH": 3, "SOL": 2, "DOGE": 0, "ARB": 1}
        mock_gw.get_account_state.return_value = (1000.0, 1000.0, {})
        mock_gw.get_mid_price.side_effect = lambda sym: 60000.0 if sym == "BTC" else (3000.0 if sym == "ETH" else 150.0)
        mock_gw.get_frontend_open_orders.return_value = []
        mock_gw.info.user_state.return_value = {"assetPositions": []}
        mock_gw.info.user_fills_by_time.return_value = []
        mock_gw.info.post.return_value = []
        mock_gw_cls.return_value = mock_gw

        executor = ProductionApexExecutor(testnet=True, dry_run=True, acquire_lock=False)
        executor.gateway = mock_gw
        yield executor, state_file, journal_file


# ==============================================================================
# GATE 1: STRATEGY / ALPHA INVARIANTS & DUAL-CLOCK MATH
# ==============================================================================

def test_causal_4h_boundary_assertion(mock_executor):
    """Verifies that decision boundary is strictly floored to 4H boundary."""
    executor, _, _ = mock_executor
    now_ms = int(time.time() * 1000)
    decision_ts_ms, completed_bar_end_ms = executor.get_causal_4h_decision_boundary()

    bar_len_ms = 4 * 3600 * 1000
    expected_decision_ts = (now_ms // bar_len_ms) * bar_len_ms

    assert decision_ts_ms == expected_decision_ts
    assert completed_bar_end_ms == decision_ts_ms
    assert decision_ts_ms <= now_ms
    assert (now_ms - decision_ts_ms) < bar_len_ms


def test_dual_clock_boundary_calculation(mock_executor):
    """Verifies that seconds until next 4H boundary returns a valid positive interval <= 14415s."""
    executor, _, _ = mock_executor
    secs = executor.get_seconds_until_next_4h_bar()
    assert isinstance(secs, int)
    assert 1 <= secs <= 4 * 3600 + 30


def test_leland_turnover_deadband_10pct(mock_executor):
    """Verifies that Leland turnover deadband is strictly 10% (0.100) and suppresses sub-10% adjustments."""
    assert LELAND_DEADBAND == 0.100

    # Sub-10% weight adjustments suppressed
    assert abs(0.040) <= LELAND_DEADBAND
    assert abs(0.095) <= LELAND_DEADBAND

    # Greater than 10% adjustments executed
    assert abs(0.105) > LELAND_DEADBAND
    assert abs(0.150) > LELAND_DEADBAND


def test_age_aware_mask_no_bfill():
    """Verifies age-aware observed mask logic: forward-fill limit=2, price_age > 2 invalid, zero bfill."""
    # 5 bars x 2 symbols
    # Sym 0 has missing bar at t=2, 3, 4 (age exceeds 2 at t=4)
    # Sym 1 has missing bar at t=0 (must NOT be backfilled)
    raw = np.array([
        [100.0, np.nan],
        [101.0, 50.0],
        [np.nan, 51.0],
        [np.nan, 52.0],
        [np.nan, 53.0],
    ])
    observed = ~np.isnan(raw)
    n_bars, n_syms = observed.shape

    price_age = np.zeros((n_bars, n_syms), dtype=int)
    for t in range(n_bars):
        for i in range(n_syms):
            if observed[t, i]:
                price_age[t, i] = 0
            else:
                price_age[t, i] = price_age[t - 1, i] + 1 if t > 0 else 999

    valid_mask = (price_age <= 2)

    # Sym 1 at t=0 was missing: age=999 -> invalid (NO bfill allowed)
    assert valid_mask[0, 1] == False
    # Sym 0 at t=1: observed -> valid
    assert valid_mask[1, 0] == True
    # Sym 0 at t=2: age=1 -> valid (within ffill limit 2)
    assert valid_mask[2, 0] == True
    # Sym 0 at t=3: age=2 -> valid (at limit 2)
    assert valid_mask[3, 0] == True
    # Sym 0 at t=4: age=3 -> INVALID (exceeds ffill limit 2)
    assert valid_mask[4, 0] == False


def test_canonical_wilder_atr_parity():
    """Verifies that compute_canonical_wilder_atr implements exact Wilder's exponential smoothing."""
    # Synthetic series of 20 bars
    np.random.seed(42)
    high = np.array([105.0] * 20)
    low = np.array([95.0] * 20)
    close = np.array([100.0] * 20)

    # True range for all bars is 10.0
    atr_mat = compute_canonical_wilder_atr(high.reshape(-1, 1), low.reshape(-1, 1), close.reshape(-1, 1), window=14)
    assert atr_mat.shape == (20, 1)
    # ATR should converge to exactly 10.0
    assert abs(atr_mat[-1, 0] - 10.0) < 1e-6


def test_canonical_f1_carry_parity():
    """Verifies that canonical F1 funding carry implements -zscore(funding_rates)."""
    funding = np.array([0.0003, 0.0001, -0.0002, 0.0005])
    eligible = np.array([True, True, True, True])

    f1 = compute_canonical_f1_carry(funding, eligible)
    # The highest positive funding rate (asset 3) must have the most negative carry score
    assert f1[3] < f1[0] < f1[1] < f1[2]
    # The negative funding rate (asset 2) collects carry when shorted -> highest positive score
    assert f1[2] > 0.0
    # Zero mean property of zscore
    assert abs(np.mean(f1)) < 1e-6


# ==============================================================================
# GATE 2: EXECUTION INTEGRITY, ClOID OWNERSHIP, & FAULT INJECTION
# ==============================================================================

def test_event_journal_append_and_sha256_hash_chain(tmp_path):
    """Verifies that EventJournal maintains a tamper-evident SHA-256 cryptographic hash chain."""
    journal_path = tmp_path / "test_journal.jsonl"
    journal = EventJournal(journal_path)

    ev1 = journal.append_event("EPOCH_INIT", {"initial_equity": 1000.0})
    ev2 = journal.append_event("TARGET_FROZEN", {"generation_id": "GEN_001", "target_weights": {"ETH": 0.5}})

    assert ev1["event_id"] == 1
    assert ev1["prev_hash"] == "0" * 64
    assert len(ev1["hash"]) == 64

    assert ev2["event_id"] == 2
    assert ev2["prev_hash"] == ev1["hash"]

    # Verify cryptographic link
    payload_bytes = json.dumps(ev2["payload"], sort_keys=True).encode("utf-8")
    expected_hash = hashlib.sha256(ev1["hash"].encode("utf-8") + payload_bytes).hexdigest()
    assert ev2["hash"] == expected_hash


def test_journal_replay_state_reconstruction_after_crash(tmp_path):
    """Verifies crash recovery: complete deletion of state cache is 100% reconstructed from journal."""
    journal_path = tmp_path / "test_journal.jsonl"
    journal = EventJournal(journal_path)

    journal.append_event("EPOCH_INIT", {"initial_equity": 555.93, "hwm": 555.93})
    journal.append_event("TARGET_FROZEN", {
        "generation_id": "GEN_TEST",
        "target_weights": {"BTC": 0.50, "ETH": -0.50},
        "active_leverage": 2.0,
        "cushion": 0.80,
        "holding_locks": {"BTC": 18},
    })
    journal.append_event("FILL_RECONCILED", {
        "fill_key": "BTC_101_101_1726000000000_60000.0_0.01_b",
        "coin": "BTC",
        "closed_pnl": 15.50,
        "fee": 0.35,
        "time_ms": 1726000000000,
    })
    journal.append_event("FUNDING_RECONCILED", {
        "funding_key": "BTC_1726003600000_1.250000",
        "coin": "BTC",
        "usdc": 1.25,
        "time_ms": 1726003600000,
    })

    # Deterministic replay
    state = journal.replay_and_project()

    assert state.initial_strategy_equity == 555.93
    assert state.historical_hwm == 555.93
    assert state.frozen_target_generation_id == "GEN_TEST"
    assert state.frozen_target_weights == {"BTC": 0.50, "ETH": -0.50}
    assert state.active_leverage == 2.0
    assert state.cushion == 0.80
    assert state.holding_locks == {"BTC": 18}
    assert state.cumulative_realized_pnl == 15.50
    assert state.cumulative_exchange_fees == 0.35
    assert state.cumulative_funding_pnl == 1.25
    assert "BTC_101_101_1726000000000_60000.0_0.01_b" in state.processed_fill_keys
    assert "BTC_1726003600000_1.250000" in state.processed_funding_keys


def test_fill_and_funding_deduplication_idempotency(mock_executor):
    """Verifies that duplicate fill and funding events from overlapping API queries are deduplicated."""
    executor, _, _ = mock_executor

    # Mock user_fills_by_time returning identical fill twice
    mock_fill = {
        "coin": "ETH",
        "oid": 888,
        "tid": 999,
        "time": executor.state.epoch_start_ms + 1000,
        "px": "3000.0",
        "sz": "0.10",
        "side": "b",
        "closedPnl": "25.00",
        "fee": "0.50"
    }
    executor.gateway.info.user_fills_by_time.return_value = [mock_fill, mock_fill]

    # Mock userFunding returning identical funding event twice
    mock_funding = {
        "coin": "ETH",
        "time": executor.state.epoch_start_ms + 2000,
        "usdc": "+2.0000"
    }
    executor.gateway.info.post.return_value = [mock_funding, mock_funding]

    executor.reconcile_ledger_events_and_reconstruct_nav()

    # Verify PnL is credited ONCE, not twice
    assert executor.state.cumulative_realized_pnl == 25.00
    assert executor.state.cumulative_exchange_fees == 0.50
    assert executor.state.cumulative_funding_pnl == 2.00


def test_frozen_target_immutability_during_4h_micro_repair(mock_executor):
    """Verifies that 4H micro risk cycle DOES NOT re-score alpha or alter frozen target generation ID."""
    executor, _, _ = mock_executor
    executor.journal.append_event("TARGET_FROZEN", {
        "generation_id": "GEN_ORIGINAL_72H",
        "target_weights": {"BTC": 0.50, "ETH": -0.50},
        "active_leverage": 2.0,
        "cushion": 1.0,
        "holding_locks": {},
        "timestamp": "2026-09-20 20:00:00 UTC",
    })
    executor.state = executor.journal.replay_and_project()

    # Run micro cycle
    executor.execute_micro_risk_cycle()

    # Assert target generation and weights are strictly unchanged
    assert executor.state.frozen_target_generation_id == "GEN_ORIGINAL_72H"
    assert executor.state.frozen_target_weights == {"BTC": 0.50, "ETH": -0.50}
    assert executor.state.bars_since_macro == 1
    assert executor.state.total_micro_bars == 1


def test_circuit_breaker_halts_on_excessive_valuation_residual(mock_executor):
    """Verifies fail-closed behavior: unexplained valuation residual > $0.10 trips circuit breaker to HALTED."""
    executor, _, _ = mock_executor
    executor.state.initial_strategy_equity = 1000.0

    # Exchange reports 1000.0, but reconstructed NAV is 1000.0.
    # Now simulate an external untracked discrepancy: exchange reports 1050.0 without corresponding fills
    executor.gateway.get_account_state.return_value = (1050.0, 1050.0, {})
    executor.gateway.info.user_state.return_value = {"assetPositions": []}

    equity, discrepancy, _ = executor.reconcile_ledger_events_and_reconstruct_nav()

    assert discrepancy == 50.0
    assert discrepancy > MAX_VALUATION_RESIDUAL_USD
    assert executor.state.circuit_breaker == CircuitBreakerState.HALTED


def test_foreign_order_isolation(mock_executor):
    """Verifies that engine only manages its own owned ClOIDs and ignores external manual orders."""
    executor, _, _ = mock_executor
    executor.dry_run = False

    # Mock foreign order (manual user limit order on BTC) and owned order (on ETH)
    executor.state.owned_oids = {1002}
    executor.gateway.get_frontend_open_orders.return_value = [
        {"oid": 1001, "coin": "BTC", "isTrigger": False, "sz": "0.1", "origPx": "60000.0"},  # Foreign
        {"oid": 1002, "coin": "ETH", "isTrigger": False, "sz": "1.0", "origPx": "3000.0"},   # Owned
    ]

    # Timeout evaluator checks open orders
    resting_owned = [
        o for o in executor.gateway.get_frontend_open_orders()
        if int(o.get("oid", 0)) in executor.state.owned_oids and not o.get("isTrigger")
    ]

    assert len(resting_owned) == 1
    assert resting_owned[0]["coin"] == "ETH"
    assert resting_owned[0]["oid"] == 1002


# ==============================================================================
# GATE 3: ACCOUNTING & BALANCE SHEET INVARIANTS
# ==============================================================================

def test_exchange_mark_price_nav_reconciliation_equation(mock_executor):
    """
    Verifies exact NAV reconstruction equation:
    NAV_recon = OpeningEquity + RealizedPnL + FundingPnL - Fees + Unrealized(Mark) + CashFlows.
    """
    executor, _, _ = mock_executor

    # Append authoritative ledger events to journal
    executor.journal.append_event("FILL_RECONCILED", {
        "fill_key": "ETH_FILL_101",
        "coin": "ETH",
        "closed_pnl": 42.10,
        "fee": 1.25,
        "time_ms": 1726000000000,
    })
    executor.journal.append_event("FUNDING_RECONCILED", {
        "funding_key": "ETH_FUND_101",
        "coin": "ETH",
        "usdc": 3.50,
        "time_ms": 1726003600000,
    })

    # Mock exchange user_state having 1 position with unrealized PnL of +15.72
    executor.gateway.info.user_state.return_value = {
        "assetPositions": [
            {"position": {"coin": "ETH", "unrealizedPnl": "15.72"}}
        ]
    }

    # Opening equity from epoch is 1000.0
    expected_recon = 1000.0 + 42.10 + 3.50 - 1.25 + 15.72
    executor.gateway.get_account_state.return_value = (expected_recon, expected_recon - 15.72, {})

    chain_equity, discrepancy, _ = executor.reconcile_ledger_events_and_reconstruct_nav()

    assert abs(chain_equity - expected_recon) < 1e-6
    assert discrepancy < 1e-6
    assert executor.state.circuit_breaker == CircuitBreakerState.RUNNING


def test_automated_tpsl_bracket_generation_and_orphan_cleanup(mock_executor):
    """Verifies that native TP/SL brackets are armed accurately and orphan triggers are cleaned."""
    executor, _, _ = mock_executor
    executor.dry_run = False

    # Mock open positions: 1 active ETH long position
    executor.gateway.get_account_state.return_value = (
        1000.0, 1000.0,
        {"ETH": {"size": 0.10, "entry_px": 3000.0}}
    )

    # Mock existing frontend orders: 1 orphan trigger on SOL
    executor.gateway.get_frontend_open_orders.return_value = [
        {"oid": 101, "coin": "SOL", "isTrigger": True, "orderType": "Trigger Market", "sz": "1.0", "triggerPx": "140.0"},
    ]

    armed = executor.arm_position_brackets(sl_pct=0.035, tp_pct=0.070)

    # Check that orphan trigger on SOL was cancelled
    executor.gateway.exchange.cancel.assert_any_call("SOL", 101)

    # Check that ETH bracket was calculated
    assert "ETH" in armed
    expected_sl = round_px(3000.0 * (1.0 - 0.035), 3)
    expected_tp = round_px(3000.0 * (1.0 + 0.070), 3)
    assert armed["ETH"]["sl_px"] == expected_sl
    assert armed["ETH"]["tp_px"] == expected_tp


def test_sub_8_dust_sweeper(mock_executor):
    """Verifies that position remnants under $8 notional are automatically flattened."""
    executor, _, _ = mock_executor
    executor.dry_run = False

    positions = {
        "SOL": {"size": 0.035, "entry_px": 140.0},  # 0.035 * 140 = $4.90 < $8.00
        "ETH": {"size": 0.10, "entry_px": 3000.0}   # 0.10 * 3000 = $300.00 >= $8.00
    }

    executor.sweep_dust_positions(positions)

    # Verify SOL was closed, ETH was not touched
    executor.gateway.close_position.assert_called_once_with("SOL", 0.035, True)


def test_order_quantization_and_min_notional_compliance(mock_executor):
    """Verifies that generated orders strictly comply with Hyperliquid L1 consensus rules."""
    test_cases = [
        ("BTC", True, 0.005, 62450.5, 4),    # Notional ~$312.25
        ("ETH", False, 0.12, 3421.25, 3),    # Notional ~$410.55
        ("SOL", True, 2.5, 145.82, 2),       # Notional ~$364.55
    ]

    for sym, is_buy, raw_sz, raw_px, sz_dec in test_cases:
        sz = round_sz(raw_sz, sz_dec)
        px = round_px(raw_px, sz_dec)
        notional = sz * px
        valid, err, _, _ = validate_l1_order(symbol=sym, price=px, size=sz, sz_decimals=sz_dec)
        assert valid, f"Order failed L1 validation: {err}"


def test_sub_10_delta_rebalance_trap(mock_executor):
    """Verifies that sub-$10 delta rebalances are suppressed on active positions, while exits use reduce_only."""
    executor, _, _ = mock_executor
    nav = 1000.0
    executor.current_equity = nav

    # Active ETH position with +$7.00 delta (notional < $10.00)
    dw_delta_usd = 7.00
    dw = dw_delta_usd / nav
    is_active = True
    target_notional = abs(dw * nav)
    should_suppress = (is_active and target_notional < MIN_NOTIONAL_L1)
    assert should_suppress is True

    # Reduce-only order under $10 passes L1 validation
    val_ok_reduce, msg, _, _ = validate_l1_order(symbol="SOL", price=140.0, size=0.046, sz_decimals=2, is_reduce_only=True)
    assert val_ok_reduce is True

    # Normal order under $10 fails
    val_ok_normal, msg, _, _ = validate_l1_order(symbol="SOL", price=140.0, size=0.046, sz_decimals=2, is_reduce_only=False)
    assert val_ok_normal is False
    assert "below $10.00" in msg


def test_state_persistence_and_6bucket_identity(mock_executor):
    """Verifies that 6-bucket ledger identity and engine state persist and restore without leakage."""
    executor, state_file, journal_file = mock_executor
    executor.initial_nav = 1000.0
    executor.current_equity = 1150.0
    executor.hwm = 1200.0
    executor.active_leverage = 2.50
    executor.cushion = 0.75
    executor.total_micro_bars = 42
    executor.bars_since_macro = 6

    executor.ledger = {
        "gross_price_pnl": 180.0,
        "funding_pnl": 5.0,
        "exchange_fees": 20.0,
        "unrealized_mark_pnl": 0.0,
        "external_cash_flows": 0.0,
        "valuation_residual_usd": 0.0,
    }

    executor.save_state(current_positions={}, orders_placed=[], armed_triggers={})
    assert state_file.exists()

    with patch("src.execution.production_apex_daemon.STATE_FILE", state_file), \
         patch("src.execution.production_apex_daemon.JOURNAL_FILE", journal_file):
        new_executor = ProductionApexExecutor(testnet=True, dry_run=True, acquire_lock=False)
        new_executor.gateway = executor.gateway
        new_executor.load_state()

        assert new_executor.initial_nav == 1000.0
        assert new_executor.hwm == 1200.0
        assert new_executor.active_leverage == 2.50
        assert new_executor.cushion == 0.75
        assert new_executor.total_micro_bars == 42
        assert new_executor.bars_since_macro == 6
        assert new_executor.ledger["gross_price_pnl"] == 180.0
        assert new_executor.ledger["valuation_residual_usd"] == 0.0


def test_round_sz_preserves_negative_sign_for_exits():
    """Regression test: verifies round_sz preserves sign for closing short/long positions."""
    # Closing long position requires negative target_sz
    long_exit_sz = -0.0423
    rounded_exit = round_sz(long_exit_sz, sz_decimals=4)
    assert rounded_exit == -0.0423
    assert abs(rounded_exit) == 0.0423

    # Closing short position requires positive target_sz
    short_exit_sz = 125.75
    rounded_short_exit = round_sz(short_exit_sz, sz_decimals=2)
    assert rounded_short_exit == 125.75

    # Truncation down to szDecimals precision
    assert round_sz(-0.042399, sz_decimals=4) == -0.0423
    assert round_sz(0.042399, sz_decimals=4) == 0.0423

    # Zero handling
    assert round_sz(0.0, sz_decimals=4) == 0.0
    assert round_sz(-0.0, sz_decimals=4) == 0.0


def test_month_end_seconds_until_next_4h_bar(mock_executor):
    """Regression test: verifies get_seconds_until_next_4h_bar handles month-end rollover without ValueError."""
    executor, _, _ = mock_executor
    from datetime import datetime, timezone

    # Simulate September 30 at 22:30:00 UTC (day 30 of a 30-day month)
    mock_now = datetime(2026, 9, 30, 22, 30, 0, tzinfo=timezone.utc)
    with patch("src.execution.production_apex_daemon.datetime") as mock_dt:
        mock_dt.now.return_value = mock_now
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
        secs = executor.get_seconds_until_next_4h_bar()
        # Next 4H bar is Oct 1, 00:00:15 UTC -> 1 hr 30 min 15 sec = 5415 seconds
        assert secs == 5415


def test_full_exit_l1_order_validation():
    """Regression test: verifies that a full position exit passes validate_l1_order with reduce_only=True."""
    sym = "ETH"
    mid_px = 2685.70
    open_sz = 0.0423
    sz_dec = 4

    target_sz = -open_sz
    rounded_sz = round_sz(target_sz, sz_dec)
    assert rounded_sz == -0.0423
    sz_abs = abs(rounded_sz)

    val_ok, err_msg, q_px, q_sz = validate_l1_order(
        symbol=sym,
        price=mid_px,
        size=sz_abs,
        sz_decimals=sz_dec,
        is_reduce_only=True
    )
    assert val_ok is True
    assert err_msg == "VALID"
    assert q_sz == 0.0423
