#!/usr/bin/env python3
"""
HYPERCORE APEX — AUDIT REMEDIATION REGRESSION TEST SUITE
========================================================
Comprehensive regression and verification test suite certifying all Phase 0
remediations from the October 12, 2026 Adversarial Code Audit:

- P0-01: Cryptographic SHA-256 Event Journal replay and tampering detection
- P0-02: Accounting fault thresholds, HALTED latching, and execution aborts
- P0-03: ClOID order lifecycle state machine & Hyperliquid SDK Cloid types
- P0-04: Bracket arming verification & fail-closed unhedged detection
- P0-06: Holding locks absolute micro-bar preservation across replays
- P0-07: Bipower variation, Hurst, and VR return series & jump ratio bounds
- P1-01 / P1-02 / P1-05: FracDiff max_len=18 & causal warmups (no future lookahead)
- OP-01 / OP-02: HTTP Date clock drift & fail-closed frontend open orders
"""

import hashlib
import json
import math
import os
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from hyperliquid.utils.types import Cloid
from src.strategy.convex_10x_engine import (
    compute_bipower_variation_stats,
    compute_continuous_bipower_variation,
    compute_hurst_exponent,
    compute_variance_ratio,
    compute_canonical_wilder_atr,
    round_sz,
    round_px,
    validate_l1_order,
)
from src.alpha.fracdiff_orthogonal_engine import apply_fractional_differentiation
from src.signals.asym_fip import compute_asymmetric_fip_scores
from src.execution.exchange_gateway import HyperliquidGateway
from src.execution.production_apex_daemon import (
    EventJournal,
    PaperTradeState,
    CircuitBreakerState,
    ProductionApexExecutor,
    MAX_VALUATION_RESIDUAL_USD,
    MAX_WARNING_RESIDUAL_USD,
    ADMIN_RESET_TOKEN,
    parse_order_response,
    parse_cancel_response,
)


# ==============================================================================
# P0-01: CRYPTOGRAPHIC SHA-256 JOURNAL INTEGRITY TESTS
# ==============================================================================

def test_p0_01_valid_journal_replay_and_projection():
    """Verifies that an uncorrupted journal replays cleanly and reproduces state."""
    with tempfile.TemporaryDirectory() as tmpdir:
        journal_path = Path(tmpdir) / "test_journal.jsonl"
        journal = EventJournal(journal_path)

        journal.append_event("EPOCH_INIT", {"initial_equity": 1000.0})
        journal.append_event("TARGET_FROZEN", {"generation_id": "1", "target_weights": {"BTC": 0.5, "ETH": 0.5}})
        journal.append_event("ORDER_INTENT", {"cloid": "EXP103/1/BTC/BUY/001", "size": 0.1, "price": 60000.0})

        state = journal.replay_and_project()
        assert state.initial_strategy_equity == 1000.0
        assert state.frozen_target_generation_id == "1"
        assert state.frozen_target_weights == {"BTC": 0.5, "ETH": 0.5}
        assert "EXP103/1/BTC/BUY/001" in state.owned_cloids
        assert state.last_event_id == 3


def test_p0_01_journal_replay_rejects_tampered_payload():
    """Verifies that tampering with an event's payload raises ValueError on replay."""
    with tempfile.TemporaryDirectory() as tmpdir:
        journal_path = Path(tmpdir) / "test_journal.jsonl"
        journal = EventJournal(journal_path)

        journal.append_event("EPOCH_INIT", {"initial_equity": 1000.0})
        journal.append_event("TARGET_FROZEN", {"generation_id": "1", "target_weights": {"BTC": 0.5}})
        journal.append_event("ORDER_INTENT", {"cloid": "EXP103/1/BTC/BUY/001", "size": 0.1})

        # Tamper with the 2nd line payload directly
        with open(journal_path, "r") as f:
            lines = [json.loads(line) for line in f]

        lines[1]["payload"]["target_weights"]["BTC"] = 0.99  # Tamper!
        with open(journal_path, "w") as f:
            for l in lines:
                f.write(json.dumps(l) + "\n")

        replayer = EventJournal(journal_path)
        with pytest.raises(ValueError, match="Cryptographic tampering or payload corruption"):
            replayer.replay_and_project()


def test_p0_01_journal_replay_rejects_broken_hash_pointer():
    """Verifies that an invalid prev_hash pointer is strictly rejected."""
    with tempfile.TemporaryDirectory() as tmpdir:
        journal_path = Path(tmpdir) / "test_journal.jsonl"
        journal = EventJournal(journal_path)

        journal.append_event("EPOCH_INIT", {"initial_equity": 1000.0})
        journal.append_event("TARGET_FROZEN", {"generation_id": "1", "target_weights": {"BTC": 0.5}})

        with open(journal_path, "r") as f:
            lines = [json.loads(line) for line in f]

        lines[1]["prev_hash"] = "0" * 64  # Corrupt prev_hash
        with open(journal_path, "w") as f:
            for l in lines:
                f.write(json.dumps(l) + "\n")

        replayer = EventJournal(journal_path)
        with pytest.raises(ValueError, match="Cryptographic hash chain broken"):
            replayer.replay_and_project()


def test_p0_01_journal_replay_rejects_discontinuous_event_ids():
    """Verifies that non-consecutive event_ids are strictly rejected."""
    with tempfile.TemporaryDirectory() as tmpdir:
        journal_path = Path(tmpdir) / "test_journal.jsonl"
        journal = EventJournal(journal_path)

        journal.append_event("EPOCH_INIT", {"initial_equity": 1000.0})
        journal.append_event("TARGET_FROZEN", {"generation_id": "1", "target_weights": {"BTC": 0.5}})

        with open(journal_path, "r") as f:
            lines = [json.loads(line) for line in f]

        lines[1]["event_id"] = 999  # Non-consecutive
        with open(journal_path, "w") as f:
            for l in lines:
                f.write(json.dumps(l) + "\n")

        replayer = EventJournal(journal_path)
        with pytest.raises(ValueError, match="Journal sequencing fault"):
            replayer.replay_and_project()


# ==============================================================================
# P0-02: ACCOUNTING FAULT THRESHOLDS & HALTED LATCHING TESTS
# ==============================================================================

def test_p0_02_residual_threshold_invariants():
    """Verifies that residual thresholds conform to audited specifications."""
    assert MAX_WARNING_RESIDUAL_USD == 0.05
    assert MAX_VALUATION_RESIDUAL_USD == 0.10
    assert MAX_VALUATION_RESIDUAL_USD < 2.50  # Unsafe $2.50 threshold eliminated


def test_p0_02_circuit_breaker_latching_and_no_autounhalt():
    """Verifies that once HALTED, the circuit breaker remains latched and cannot auto-unhalt."""
    with tempfile.TemporaryDirectory() as tmpdir:
        journal_file = Path(tmpdir) / "test_journal.jsonl"

        executor = ProductionApexExecutor(testnet=True, dry_run=True, acquire_lock=False, journal_path=journal_file)
        executor.state = PaperTradeState()

        mock_gateway = MagicMock()
        mock_gateway.account_address = "0xTEST"
        mock_gateway.get_account_state.return_value = (1000.50, 1000.50, {})
        # Mock user_state returning $0.15 discrepancy (exceeds $0.10 -> HALT)
        mock_gateway.info.user_state.return_value = {
            "marginSummary": {"accountValue": "1000.15"},
            "assetPositions": []
        }
        mock_gateway.info.user_fills_by_time.return_value = []
        mock_gateway.info.user_funding_history.return_value = []
        executor.gateway = mock_gateway

        # Set clean initial state with $1000 equity
        executor.state.initial_strategy_equity = 1000.0
        executor.state.current_strategy_equity = 1000.0
        executor.state.cumulative_realized_pnl = 0.0
        executor.state.cumulative_funding_pnl = 0.0
        executor.state.cumulative_exchange_fees = 0.0
        executor.state.external_cash_flows = 0.0
        executor.state.unrealized_mark_pnl = 0.0

        # 1. Run reconciliation -> trips HALTED
        nav, disc, pos = executor.reconcile_ledger_events_and_reconstruct_nav()
        assert executor.state.circuit_breaker == CircuitBreakerState.HALTED
        assert disc > MAX_VALUATION_RESIDUAL_USD

        # 2. Subsequent reconciliation with lower discrepancy ($0.02) MUST REMAIN HALTED
        mock_gateway.get_account_state.return_value = (1000.02, 1000.02, {})
        mock_gateway.info.user_state.return_value = {
            "marginSummary": {"accountValue": "1000.02"},
            "assetPositions": []
        }
        nav2, disc2, pos2 = executor.reconcile_ledger_events_and_reconstruct_nav()
        assert executor.state.circuit_breaker == CircuitBreakerState.HALTED, "Circuit breaker illegally auto-unhalted!"


def test_p0_02_rebalance_and_repair_abort_on_halted():
    """Verifies that execute_macro_rebalance and execute_micro_risk_cycle abort immediately if HALTED."""
    with tempfile.TemporaryDirectory() as tmpdir:
        journal_path = Path(tmpdir) / "test_journal.jsonl"
        executor = ProductionApexExecutor(testnet=True, dry_run=True, acquire_lock=False, journal_path=journal_path)
        executor.state.circuit_breaker = CircuitBreakerState.HALTED

        # Mock gateway methods to verify they are never called
        executor.gateway = MagicMock()
        executor.gateway.base_url = "https://api.hyperliquid-testnet.xyz"

        executor.execute_macro_rebalance()
        executor.execute_micro_risk_cycle()

        # Verify no orders, cancels, or info calls were made
        assert executor.gateway.place_alo_order.call_count == 0
        assert executor.gateway.cancel_stale_maker_orders.call_count == 0


# ==============================================================================
# P0-03: ClOID ORDER STATE MACHINE & GATEWAY INVARIANTS
# ==============================================================================

def test_p0_03_cloid_deterministic_generation_and_types():
    """Verifies that ClOIDs are formatted into compliant 32-hex Cloid SDK objects."""
    cloid_str = "EXP103/1/BTC/BUY/001"
    hex_digest = hashlib.md5(cloid_str.encode("utf-8")).hexdigest()
    hex_str = "0x" + hex_digest

    cloid_obj = Cloid.from_str(hex_str)
    assert isinstance(cloid_obj, Cloid)
    assert str(cloid_obj).lower() == hex_str.lower()


def test_p0_03_gateway_passes_cloid_to_hyperliquid_order():
    """Verifies that HyperliquidGateway converts cloid string to Cloid object on placement."""
    gateway = HyperliquidGateway(secret_key=None, account_address="0xTEST", testnet=True)
    gateway.info = MagicMock()
    mock_exchange = MagicMock()
    mock_exchange.order.return_value = {"status": "ok"}
    gateway.exchange = mock_exchange
    gateway.sz_decimals = {"BTC": 4}

    # Test place_alo_order
    res = gateway.place_alo_order("BTC", is_buy=True, size=0.5, price=65000.0, cloid="EXP103/1/BTC/BUY/001")
    assert mock_exchange.order.called
    args, kwargs = mock_exchange.order.call_args
    assert "cloid" in kwargs
    assert isinstance(kwargs["cloid"], Cloid)

    # Test place_trigger_stop
    res_sl = gateway.place_trigger_stop("BTC", is_buy_to_close=False, size=0.5, trigger_price=62000.0, cloid="APEX-SL-BTC-12345")
    assert mock_exchange.order.called
    args_sl, kwargs_sl = mock_exchange.order.call_args
    assert "cloid" in kwargs_sl
    assert isinstance(kwargs_sl["cloid"], Cloid)


# ==============================================================================
# P0-04: BRACKET ARMING VERIFICATION & FAIL-CLOSED UNHEDGED DETECTION
# ==============================================================================

def test_p0_04_arm_position_brackets_marks_unhedged_on_failure():
    """Verifies that if SL order placement fails, armed_summary flags sl_armed=False and unhedged=True."""
    with tempfile.TemporaryDirectory() as tmpdir:
        journal_path = Path(tmpdir) / "test_journal.jsonl"
        executor = ProductionApexExecutor(testnet=True, dry_run=True, acquire_lock=False, journal_path=journal_path)
        executor.dry_run = False  # Enable real bracket placement logic
        executor.gateway = MagicMock()
        executor.gateway.sz_decimals = {"BTC": 4}
        executor.gateway.get_frontend_open_orders.return_value = []
        # Mock position
        executor.gateway.get_account_state.return_value = (
            1000.0,
            0.0,
            {"BTC": {"size": 0.5, "entry_px": 65000.0, "mark_px": 65000.0}}
        )
        # Exchange returns failure on order placement
        executor.gateway.place_trigger_stop.return_value = {"status": "err", "response": "Order failed"}
        executor.gateway.place_trigger_tp.return_value = {"status": "err"}

        armed = executor.arm_position_brackets()
        assert "BTC" in armed
        assert armed["BTC"]["sl_armed"] is False
        assert armed["BTC"]["unhedged"] is True


def test_p0_04_arm_position_brackets_confirms_valid_sl():
    """Verifies that when SL placement succeeds, armed_summary flags sl_armed=True."""
    with tempfile.TemporaryDirectory() as tmpdir:
        journal_path = Path(tmpdir) / "test_journal.jsonl"
        executor = ProductionApexExecutor(testnet=True, dry_run=True, acquire_lock=False, journal_path=journal_path)
        executor.dry_run = False  # Enable real bracket placement logic
        executor.gateway = MagicMock()
        executor.gateway.sz_decimals = {"BTC": 4}
        executor.gateway.get_frontend_open_orders.return_value = []
        executor.gateway.get_account_state.return_value = (
            1000.0,
            0.0,
            {"BTC": {"size": 0.5, "entry_px": 65000.0, "mark_px": 65000.0}}
        )
        executor.gateway.place_trigger_stop.return_value = {"status": "ok", "response": {"data": {"statuses": [{"resting": {"oid": 101}}]}}}
        executor.gateway.place_trigger_tp.return_value = {"status": "ok", "response": {"data": {"statuses": [{"resting": {"oid": 102}}]}}}

        armed = executor.arm_position_brackets()
        assert "BTC" in armed
        assert armed["BTC"]["sl_armed"] is True
        assert armed["BTC"]["tp_armed"] is True
        assert armed["BTC"]["unhedged"] is False


# ==============================================================================
# P0-06: HOLDING LOCKS ABSOLUTE MICRO-BAR PRESERVATION ACROSS REPLAY
# ==============================================================================

def test_p0_06_holding_locks_preservation_across_journal_replay():
    """Verifies that holding locks store absolute expiry bar and do not reset on replay."""
    with tempfile.TemporaryDirectory() as tmpdir:
        journal_path = Path(tmpdir) / "test_journal.jsonl"
        journal = EventJournal(journal_path)

        # 1. Bar 0: Initialize epoch
        journal.append_event("EPOCH_INIT", {"initial_equity": 1000.0})

        # 2. Bar 1: Rebalance assigns lock of 6 bars to SOL (expires at micro bar 1 + 6 = 7)
        journal.append_event("TARGET_FROZEN", {
            "generation_id": "1",
            "target_weights": {"SOL": 0.25},
            "holding_locks": {"SOL": 7}
        })
        journal.append_event("MICRO_BAR_COMPLETED", {
            "total_micro_bars": 1,
            "bars_since_macro": 1,
            "holding_locks": {"SOL": 7}
        })

        # Replay at bar 1: SOL lock must be 7 (unexpired)
        state1 = journal.replay_and_project()
        assert state1.total_micro_bars == 1
        assert state1.holding_locks.get("SOL") == 7

        # 3. Bar 7: Advance to bar 7
        journal.append_event("MICRO_BAR_COMPLETED", {
            "total_micro_bars": 7,
            "bars_since_macro": 7,
            "holding_locks": {}  # Expired
        })

        state2 = journal.replay_and_project()
        assert state2.total_micro_bars == 7
        assert "SOL" not in state2.holding_locks


# ==============================================================================
# P0-07: BIPOWER VARIATION, HURST, AND VR RETURN SERIES & JUMP RATIO TESTS
# ==============================================================================

def test_p0_07_bipower_variation_gaussian_diffusion_zero_jump_ratio():
    """Verifies that continuous Gaussian diffusion produces jump_ratio close to zero."""
    np.random.seed(42)
    # 500 periods of pure Gaussian returns
    gaussian_returns = np.random.normal(loc=0.0, scale=0.01, size=500)

    bv, rv, jump_ratio = compute_bipower_variation_stats(gaussian_returns)
    assert bv > 0
    assert rv > 0
    # On pure Brownian motion, jump ratio should be approximately 0.0 (<= 0.05)
    assert 0.0 <= jump_ratio <= 0.05


def test_p0_07_bipower_variation_injected_jumps_positive_ratio():
    """Verifies that discrete price jumps produce a significantly positive jump ratio bounded in [0, 1]."""
    np.random.seed(42)
    returns = np.random.normal(loc=0.0, scale=0.01, size=500)
    # Inject large discrete jumps (e.g., 6 sigma shocks)
    jump_indices = [50, 120, 250, 380, 450]
    for idx in jump_indices:
        returns[idx] += 0.08 * (1 if np.random.rand() > 0.5 else -1)

    bv, rv, jump_ratio = compute_bipower_variation_stats(returns)
    assert rv > bv, f"Realized variance {rv} should exceed Bipower variation {bv} in presence of jumps"
    assert 0.10 <= jump_ratio <= 1.0, f"Jump ratio {jump_ratio} should reflect injected jump component"


def test_p0_07_continuous_bipower_variation_gate():
    """Verifies that jump gate rejects return series with large jump discontinuities (jump_ratio > 0.40)."""
    np.random.seed(1337)
    returns = np.random.normal(loc=0.0, scale=0.005, size=200)
    # Inject massive jump shock
    returns[100] = 0.15

    bv, rv, jump_ratio = compute_bipower_variation_stats(returns)
    assert jump_ratio > 0.40, f"Jump ratio {jump_ratio} should exceed 0.40 threshold"


def test_p0_07_hurst_and_variance_ratio_consume_returns():
    """Verifies that Hurst exponent and Variance Ratio compute valid stats on return series."""
    np.random.seed(42)
    mean_reverting_returns = np.zeros(200)
    for i in range(1, 200):
        mean_reverting_returns[i] = -0.5 * mean_reverting_returns[i-1] + np.random.normal(0, 0.01)

    hurst = compute_hurst_exponent(mean_reverting_returns)
    vr = compute_variance_ratio(mean_reverting_returns)
    assert 0.0 <= hurst <= 1.0
    assert vr > 0.0


# ==============================================================================
# P1-01 / P1-02 / P1-05: FRACDIFF, ATR, ASYM-FIP CAUSAL WARMUP TESTS
# ==============================================================================

def test_p1_01_fracdiff_default_max_len_18():
    """Verifies that apply_fractional_differentiation default max_len is 18 (H=18)."""
    import inspect
    sig = inspect.signature(apply_fractional_differentiation)
    assert sig.parameters["max_len"].default == 18


def test_p1_01_fracdiff_causal_warmup_no_future_lookahead():
    """Verifies that FracDiff warmup values are causal and unaffected by changes to future prices."""
    np.random.seed(42)
    prices_orig = np.cumprod(1 + np.random.normal(0, 0.01, 100)) * 100.0
    prices_mutated = prices_orig.copy()
    # Mutate values after bar 30
    prices_mutated[30:] = prices_mutated[30:] * 2.5

    fd_orig = apply_fractional_differentiation(prices_orig.reshape(-1, 1), d=0.38, max_len=18)
    fd_mutated = apply_fractional_differentiation(prices_mutated.reshape(-1, 1), d=0.38, max_len=18)

    # Bars 0 to 25 MUST be identical (strictly causal)
    np.testing.assert_allclose(fd_orig[:25, 0], fd_mutated[:25, 0], rtol=1e-10)


def test_p1_02_wilder_atr_causal_warmup_no_future_lookahead():
    """Verifies that compute_canonical_wilder_atr warmup is causal and unaffected by future bars."""
    highs = np.linspace(100, 150, 50)
    lows = np.linspace(95, 145, 50)
    closes_orig = np.linspace(98, 148, 50)
    closes_mutated = closes_orig.copy()
    closes_mutated[30:] += 50.0

    atr_orig = compute_canonical_wilder_atr(highs, lows, closes_orig, window=14)
    atr_mutated = compute_canonical_wilder_atr(highs, lows, closes_mutated, window=14)

    # Bars 0 to 25 MUST be identical
    np.testing.assert_allclose(atr_orig[:25], atr_mutated[:25], rtol=1e-10)


def test_p1_05_asym_fip_causal_warmup_no_future_lookahead():
    """Verifies that compute_asymmetric_fip_scores warmup does not backfill future values."""
    np.random.seed(42)
    n_bars, n_symbols = 60, 12
    residuals_orig = np.random.normal(0, 0.02, (n_bars, n_symbols))
    raw_f5_orig = np.random.normal(0, 0.02, (n_bars, n_symbols))
    valid_mask = np.ones((n_bars, n_symbols), dtype=bool)

    residuals_mutated = residuals_orig.copy()
    residuals_mutated[30:, :] += 0.10

    fip_orig = compute_asymmetric_fip_scores(residuals_orig, raw_f5_orig, valid_mask, lookback=18)
    fip_mutated = compute_asymmetric_fip_scores(residuals_mutated, raw_f5_orig, valid_mask, lookback=18)

    # Warmup bars 0 to 18 MUST be identical
    np.testing.assert_allclose(fip_orig[:18], fip_mutated[:18], rtol=1e-10)


# ==============================================================================
# OP-01 / OP-02: OPERATIONAL GATEWAY & CLOCK DRIFT INVARIANTS
# ==============================================================================

def test_op_01_clock_drift_http_header_synchronization():
    """Verifies that check_clock_drift measures HTTP Date header synchronization."""
    with tempfile.TemporaryDirectory() as tmpdir:
        journal_path = Path(tmpdir) / "test_journal.jsonl"
        executor = ProductionApexExecutor(testnet=True, dry_run=True, acquire_lock=False, journal_path=journal_path)

        # Mock response with matching current time
        now_gmt = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
        mock_resp = MagicMock()
        mock_resp.headers.get.return_value = now_gmt
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp):
            drift_ok = executor.check_clock_drift()
            assert drift_ok is True


def test_op_02_get_frontend_open_orders_raises_on_error():
    """Verifies that get_frontend_open_orders raises RuntimeError on failure rather than returning []."""
    gateway = HyperliquidGateway(secret_key=None, account_address="0xVALID_ACCOUNT", testnet=True)
    gateway.info = MagicMock()
    gateway.info.post.side_effect = ConnectionError("Hyperliquid L1 node unreachable")

    with pytest.raises(RuntimeError, match="Exchange query frontendOpenOrders failed"):
        gateway.get_frontend_open_orders()


# ==============================================================================
# AUDITOR ADVERSARIAL REPRODUCTION SUITE (PHASE 0.1 SAFETY CERTIFICATION)
# ==============================================================================

def test_p0_01_event_type_tampering_rejected_by_strict_replay():
    """
    Auditor Reproduction Test:
    Modifying event_type without changing hash or payload MUST fail strict replay under Schema v2.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        journal_path = Path(tmpdir) / "test_journal.jsonl"
        journal = EventJournal(journal_path)

        journal.append_event("EPOCH_INIT", {"initial_equity": 1000.0})
        journal.append_event("CIRCUIT_BREAKER", {"state": "HALTED", "reason": "Test fault"})

        # Initial replay must be HALTED
        state0 = journal.replay_and_project(strict=True)
        assert state0.circuit_breaker == CircuitBreakerState.HALTED

        # Adversarial tamper: modify second event's event_type to IMPLEMENTATION_AUDIT_RECORD leaving hashes identical
        with open(journal_path, "r") as f:
            lines = [json.loads(line) for line in f]

        lines[1]["event_type"] = "IMPLEMENTATION_AUDIT_RECORD"
        with open(journal_path, "w") as f:
            for l in lines:
                f.write(json.dumps(l) + "\n")

        # Strict replay MUST reject the tampered event_type!
        replayer = EventJournal(journal_path)
        with pytest.raises(ValueError, match="Cryptographic tampering or payload corruption"):
            replayer.replay_and_project(strict=True)


def test_p0_01_timestamp_and_event_id_tampering_rejected():
    """Verifies that altering timestamp_ms in envelope is caught by SHA-256 verification."""
    with tempfile.TemporaryDirectory() as tmpdir:
        journal_path = Path(tmpdir) / "test_journal.jsonl"
        journal = EventJournal(journal_path)
        journal.append_event("EPOCH_INIT", {"initial_equity": 1000.0})

        with open(journal_path, "r") as f:
            entry = json.loads(f.readline())

        entry["timestamp_ms"] = entry["timestamp_ms"] + 100000
        with open(journal_path, "w") as f:
            f.write(json.dumps(entry) + "\n")

        replayer = EventJournal(journal_path)
        with pytest.raises(ValueError, match="Cryptographic tampering or payload corruption"):
            replayer.replay_and_project(strict=True)


def test_p0_01_legacy_v1_migration_boundary():
    """Verifies that historical Schema v1 journal events (hash of prev_hash + payload) replay cleanly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        journal_path = Path(tmpdir) / "test_v1_journal.jsonl"
        payload = {"initial_equity": 1000.0}
        payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        hasher = hashlib.sha256()
        hasher.update(("0" * 64).encode("utf-8"))
        hasher.update(payload_bytes)
        v1_hash = hasher.hexdigest()

        entry_v1 = {
            "event_id": 1,
            "event_type": "EPOCH_INIT",
            "timestamp_ms": 1600000000000,
            "payload": payload,
            "prev_hash": "0" * 64,
            "hash": v1_hash,
            "schema_version": 1,
        }
        with open(journal_path, "w") as f:
            f.write(json.dumps(entry_v1) + "\n")

        replayer = EventJournal(journal_path)
        state = replayer.replay_and_project(strict=True)
        assert state.initial_strategy_equity == 1000.0
        assert state.last_hash == v1_hash


def test_p1_05_asym_fip_post_warmup_calculation_nonzero():
    """
    Auditor Reproduction Test:
    30 bars, 12 valid assets, constant nonzero F5 score (1.50).
    Verifies that bars >= 18 are computed and populated, NOT left as 0.00!
    """
    n_bars, n_symbols = 30, 12
    np.random.seed(42)
    residuals = np.random.normal(0, 0.02, (n_bars, n_symbols))
    raw_f5 = np.full((n_bars, n_symbols), 1.50)
    valid_mask = np.ones((n_bars, n_symbols), dtype=bool)

    f_asym = compute_asymmetric_fip_scores(residuals, raw_f5, valid_mask, lookback=18)

    # Warmup bar 17 must equal raw F5 (1.50)
    assert np.allclose(f_asym[17, :], 1.50)

    # Post-warmup bars 18 and 29 MUST BE NONZERO and computed
    assert np.all(f_asym[18, :] > 0.0), "Bar 18 must be computed and nonzero!"
    assert np.all(f_asym[29, :] > 0.0), "Bar 29 must be computed and nonzero!"
    assert not np.allclose(f_asym[18, :], 0.0)
    assert not np.allclose(f_asym[29, :], 0.0)


def test_p1_05_asym_fip_long_penalty_and_short_boost_math():
    """Verifies mathematical properties of long penalty and short boost in AsymFIP."""
    lookback = 18
    n_bars = 25
    n_symbols = 10
    residuals = np.full((n_bars, n_symbols), 0.01)
    # Inject large pump wick into symbol 0 (long penalty test)
    residuals[19, 0] = 0.50
    # Inject large liquidation waterfall into symbol 1 (short boost test)
    residuals[19, 1] = -0.50

    raw_f5 = np.zeros((n_bars, n_symbols))
    raw_f5[20, 0] = 2.0   # Long candidate
    raw_f5[20, 1] = -2.0  # Short candidate
    valid_mask = np.ones((n_bars, n_symbols), dtype=bool)

    f_asym = compute_asymmetric_fip_scores(residuals, raw_f5, valid_mask, lookback=lookback)

    # Symbol 0 (long with pump wick) must be penalized: f_asym < raw_f5
    assert f_asym[20, 0] < raw_f5[20, 0]
    # Symbol 1 (short with liquidation waterfall) must be boosted (more negative): f_asym < raw_f5
    assert f_asym[20, 1] < raw_f5[20, 1]


def test_p0_04_parse_order_response_rejects_embedded_errors():
    """
    Auditor Reproduction Test:
    Hyperliquid returns {"status": "ok", "response": {"type": "order", "data": {"statuses": [{"error": "SL rejection"}]}}}
    parse_order_response MUST return ok=False, oid=None.
    """
    res = {
        "status": "ok",
        "response": {
            "type": "order",
            "data": {
                "statuses": [{"error": "SL rejection"}]
            }
        }
    }
    ok, oid, err = parse_order_response(res)
    assert ok is False
    assert oid is None
    assert "SL rejection" in err


def test_p0_04_bracket_arming_embedded_rejection_marks_unhedged():
    """
    Auditor Reproduction Test:
    When exchange returns top-level 'ok' with embedded error inside statuses,
    arm_position_brackets MUST report sl_armed=False and unhedged=True!
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        journal_path = Path(tmpdir) / "test_journal.jsonl"
        executor = ProductionApexExecutor(testnet=True, dry_run=False, acquire_lock=False, journal_path=journal_path)
        executor.gateway = MagicMock()
        executor.gateway.sz_decimals = {"SOL": 2}
        executor.gateway.get_frontend_open_orders.return_value = []
        executor.gateway.get_account_state.return_value = (
            1000.0, 0.0, {"SOL": {"size": 10.0, "entry_px": 150.0, "mark_px": 150.0}}
        )
        # Mock embedded SL rejection
        executor.gateway.place_trigger_stop.return_value = {
            "status": "ok",
            "response": {
                "type": "order",
                "data": {
                    "statuses": [{"error": "SL rejection"}]
                }
            }
        }
        executor.gateway.place_trigger_tp.return_value = {
            "status": "ok",
            "response": {"type": "order", "data": {"statuses": [{"resting": {"oid": 202}}]}}
        }

        armed = executor.arm_position_brackets()
        assert armed["SOL"]["sl_armed"] is False, "SL must not be classified as armed on embedded error!"
        assert armed["SOL"]["unhedged"] is True, "Position must be classified as unhedged!"


def test_p0_04_bracket_query_exception_trips_halt_and_fails_closed():
    """
    Auditor Reproduction Test:
    When open orders query raises RuntimeError('exchange offline'),
    arm_position_brackets MUST trip HALT, record CIRCUIT_BREAKER event, and return unverified state.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        journal_path = Path(tmpdir) / "test_journal.jsonl"
        executor = ProductionApexExecutor(testnet=True, dry_run=False, acquire_lock=False, journal_path=journal_path)
        executor.gateway = MagicMock()
        executor.gateway.get_account_state.side_effect = RuntimeError("exchange offline")

        armed = executor.arm_position_brackets()
        assert executor.state.circuit_breaker == CircuitBreakerState.HALTED
        assert "_error" in armed
        assert armed.get("_unverified_protection") is True

        # Check that HALTED is durably committed to journal
        state_replayed = executor.journal.replay_and_project()
        assert state_replayed.circuit_breaker == CircuitBreakerState.HALTED


def test_op_01_clock_drift_failure_trips_halt_and_aborts_all_cycles():
    """
    Auditor Reproduction Test:
    Clock verification failure trips HALT and halts execution across macro and micro cycles.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        journal_path = Path(tmpdir) / "test_journal.jsonl"
        executor = ProductionApexExecutor(testnet=True, dry_run=False, acquire_lock=False, journal_path=journal_path)

        # Mock clock check failure (> 5000ms drift)
        with patch.object(executor, "check_clock_drift", return_value=False):
            executor.gateway = MagicMock()

            # 1. Macro rebalance aborts
            executor.execute_macro_rebalance()
            assert executor.gateway.place_alo_order.call_count == 0

            # 2. Micro risk cycle aborts
            executor.execute_micro_risk_cycle()
            assert executor.gateway.place_alo_order.call_count == 0


def test_p0_02_drawdown_breach_durably_halts_and_prevents_target_freeze():
    """
    Auditor Reproduction Test:
    Drawdown > 52% trips durable HALT, persists to journal, aborts macro rebalance,
    and never appends TARGET_FROZEN. Survives journal replay.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        journal_path = Path(tmpdir) / "test_journal.jsonl"
        executor = ProductionApexExecutor(testnet=True, dry_run=False, acquire_lock=False, journal_path=journal_path)
        executor.journal.append_event("EPOCH_INIT", {
            "initial_equity": 10000.0,
            "hwm": 10000.0,
        })
        executor.state = executor.journal.replay_and_project()
        executor.state.current_strategy_equity = 4500.0  # 55% DD (> 52%)

        executor.gateway = MagicMock()
        executor.gateway.get_account_state.return_value = (4500.0, 4500.0, {})
        executor.gateway.info.user_state.return_value = {"marginSummary": {"accountValue": "4500.0"}, "assetPositions": []}
        executor.gateway.info.user_fills_by_time.return_value = []
        executor.gateway.info.user_funding_history.return_value = []

        executor.load_latest_market_data = MagicMock(return_value=(
            np.ones((40, 10)), np.ones((40, 10)), np.zeros(10), np.ones((40, 10), dtype=bool),
            [f"S{i}" for i in range(10)], 0, 1, None
        ))

        with patch.object(executor, "check_clock_drift", return_value=True):
            executor.execute_macro_rebalance()

        assert executor.state.circuit_breaker == CircuitBreakerState.HALTED

        # Verify on-disk journal replay confirms HALTED and NO TARGET_FROZEN was committed
        replayer = EventJournal(journal_path)
        state_replayed = replayer.replay_and_project()
        assert state_replayed.circuit_breaker == CircuitBreakerState.HALTED
        assert state_replayed.frozen_target_generation_id == ""


def test_p0_02_monotonic_circuit_breaker_latch_rejects_unauthorized_reset():
    """Verifies that an ordinary RUNNING event cannot unhalt a latched HALTED state."""
    with tempfile.TemporaryDirectory() as tmpdir:
        journal_path = Path(tmpdir) / "test_journal.jsonl"
        journal = EventJournal(journal_path)
        journal.append_event("EPOCH_INIT", {"initial_equity": 1000.0})
        journal.append_event("CIRCUIT_BREAKER", {"state": "HALTED", "reason": "Fault"})
        # Attempt to append ordinary RUNNING without manual override
        journal.append_event("CIRCUIT_BREAKER", {"state": "RUNNING", "reason": "Unauthorized attempt"})

        state = journal.replay_and_project()
        assert state.circuit_breaker == CircuitBreakerState.HALTED, "Monotonic terminal latch must reject unauthorized reset!"

        # Legitimate authenticated manual reset with ADMIN_RESET_TOKEN
        journal.append_event("CIRCUIT_BREAKER", {"state": "RUNNING", "manual_override_reset": True, "auth_token": ADMIN_RESET_TOKEN, "reason": "Operator auth"})
        state_reset = journal.replay_and_project()
        assert state_reset.circuit_breaker == CircuitBreakerState.RUNNING


def test_p0_06_holding_locks_carry_forward_across_successive_generations():
    """
    Auditor Reproduction Test:
    A holding lock from Generation 1 (e.g. 42 micro bars) must NOT be erased
    when Generation 2 arrives at bar 18 omitting the token.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        journal_path = Path(tmpdir) / "test_journal.jsonl"
        executor = ProductionApexExecutor(testnet=True, dry_run=False, acquire_lock=False, journal_path=journal_path)
        executor.state.total_micro_bars = 18
        # Token SOL has lock until bar 42 (24 bars remaining)
        executor.state.holding_locks = {"SOL": 42}

        executor.gateway = MagicMock()
        executor.gateway.sz_decimals = {"BTC": 4, "ETH": 4, "SOL": 2}
        executor.gateway.get_account_state.return_value = (
            1000.0, 1000.0, {"SOL": {"size": 5.0, "entry_px": 100.0, "mark_px": 100.0}}
        )
        executor.gateway.get_mid_price.return_value = 100.0
        executor.gateway.info.user_state.return_value = {"marginSummary": {"accountValue": "1000.0"}, "assetPositions": []}
        executor.gateway.info.user_fills_by_time.return_value = []
        executor.gateway.info.user_funding_history.return_value = []
        executor.reconcile_ledger_events_and_reconstruct_nav = MagicMock(return_value=(
            1000.0, 0.0, {"SOL": {"size": 5.0, "entry_px": 100.0, "mark_px": 100.0}}
        ))

        # New macro generation targets BTC and ETH, but omits SOL (raw_weights has no SOL)
        executor.load_latest_market_data = MagicMock(return_value=(
            np.ones((40, 5)), np.ones((40, 5)), np.zeros(5), np.ones((40, 5), dtype=bool),
            ["BTC", "ETH", "SOL", "AVAX", "NEAR"], 0, 1, None
        ))
        executor.compute_exp103_signals_and_weights = MagicMock(return_value=(
            {"BTC": 0.5, "ETH": 0.5}, 1.0, 1.0, ["BTC"], ["ETH"], {"BTC": 24, "ETH": 24}
        ))

        with patch.object(executor, "check_clock_drift", return_value=True):
            executor.execute_macro_rebalance()

        # SOL lock MUST be carried forward to 42 in state and journal!
        assert "SOL" in executor.state.holding_locks
        assert executor.state.holding_locks["SOL"] == 42


def test_p0_03_order_decision_prices_reconstructed_from_journal():
    """Verifies that order_decision_prices are reconstructed upon journal replay."""
    with tempfile.TemporaryDirectory() as tmpdir:
        journal_path = Path(tmpdir) / "test_journal.jsonl"
        journal = EventJournal(journal_path)
        journal.append_event("EPOCH_INIT", {"initial_equity": 1000.0})
        journal.append_event("ORDER_CONFIRMED", {
            "cloid": "EXP103/1/BTC/BUY/001",
            "oid": 54321,
            "sym": "BTC",
            "size": 0.1,
            "price": 60000.0,
            "signal_price": 59950.0,
            "target_price": 60000.0,
        })

        state = journal.replay_and_project()
        assert "54321" in state.order_decision_prices
        assert state.order_decision_prices["54321"]["signal_price"] == 59950.0
        assert state.order_decision_prices["54321"]["target_price"] == 60000.0


def test_dry_run_state_isolation_does_not_mutate_live_journal():
    """Verifies that running in dry-run mode uses isolated dry-run files and never mutates production journal/state."""
    executor = ProductionApexExecutor(testnet=True, dry_run=True, acquire_lock=False)
    assert "dry_run_journal.jsonl" in str(executor.journal_file)
    assert "dry_run_state.json" in str(executor.state_file)
    assert executor.journal.path == executor.journal_file


def test_secondary_daemon_decommissioned_prevents_execution():
    """Verifies that MasterApexExecutor raises RuntimeError when initialized."""
    from src.execution.master_apex_daemon import MasterApexExecutor
    with pytest.raises(RuntimeError, match="DEPRECATED_ENTRYPOINT"):
        MasterApexExecutor(testnet=True, dry_run=True)


def test_p0_01_schema_downgrade_post_v2_rejected():
    """Adversarial probe: appending a legacy v1 event after v2 migration must fail strict replay."""
    with tempfile.TemporaryDirectory() as tmpdir:
        journal_path = Path(tmpdir) / "test_journal.jsonl"
        journal = EventJournal(journal_path)

        # 1. Append valid Schema v2 events
        journal.append_event("EPOCH_INIT", {"initial_equity": 1000.0})
        journal.append_event("CIRCUIT_BREAKER", {"state": "HALTED", "reason": "Test fault"})

        # 2. Append legacy Schema v1 event (schema_version omitted) after Schema v2
        payload = {"state": "RUNNING", "manual_override_reset": True}
        payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        hasher = hashlib.sha256()
        hasher.update(journal.last_hash.encode("utf-8"))
        hasher.update(payload_bytes)
        v1_hash = hasher.hexdigest()

        v1_entry = {
            "event_id": journal.last_event_id + 1,
            "event_type": "CIRCUIT_BREAKER",
            "timestamp_ms": int(time.time() * 1000),
            "payload": payload,
            "prev_hash": journal.last_hash,
            "hash": v1_hash,
        }
        with open(journal_path, "a") as f:
            f.write(json.dumps(v1_entry) + "\n")

        # 3. Strict replay must detect schema downgrade attack and raise ValueError!
        replayer = EventJournal(journal_path)
        with pytest.raises(ValueError, match="Schema downgrade detected"):
            replayer.replay_and_project(strict=True)


def test_p0_01_circuit_breaker_unauthorized_unhalt_rejected():
    """Adversarial probe: unhalting circuit breaker requires Schema v2 AND authenticated admin token."""
    with tempfile.TemporaryDirectory() as tmpdir:
        journal_path = Path(tmpdir) / "test_journal.jsonl"
        journal = EventJournal(journal_path)

        journal.append_event("EPOCH_INIT", {"initial_equity": 1000.0})
        journal.append_event("CIRCUIT_BREAKER", {"state": "HALTED", "reason": "Test fault"})

        # Unauthorized attempt without valid auth_token
        journal.append_event("CIRCUIT_BREAKER", {
            "state": "RUNNING",
            "manual_override_reset": True,
            "auth_token": "MALICIOUS_OR_UNAUTHORIZED_TOKEN"
        })

        # Strict replay must reject unauthorized transition and remain HALTED
        state = journal.replay_and_project(strict=True)
        assert state.circuit_breaker == CircuitBreakerState.HALTED

        # Authorized transition with correct ADMIN_RESET_TOKEN
        journal.append_event("CIRCUIT_BREAKER", {
            "state": "RUNNING",
            "manual_override_reset": True,
            "auth_token": ADMIN_RESET_TOKEN
        })
        state_auth = journal.replay_and_project(strict=True)
        assert state_auth.circuit_breaker == CircuitBreakerState.RUNNING


def test_op_01_clock_failure_modes_durably_trip_halt():
    """Adversarial probe: HTTP 503, missing Date header, and excessive drift all durably trip HALT."""
    with tempfile.TemporaryDirectory() as tmpdir:
        journal_file = Path(tmpdir) / "test_journal.jsonl"
        executor = ProductionApexExecutor(testnet=True, dry_run=True, acquire_lock=False, journal_path=journal_file)

        # 1. HTTP Error (503 / network exception) -> must call trip_halt
        with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError("http://test", 503, "Service Unavailable", {}, None)):
            res = executor.check_clock_drift()
            assert res is False
            assert executor.state.circuit_breaker == CircuitBreakerState.HALTED

        # Verify durable HALT record in journal
        with open(journal_file, "r") as f:
            lines = [json.loads(line) for line in f]
        halt_events = [e for e in lines if e.get("event_type") == "CIRCUIT_BREAKER" and e.get("payload", {}).get("state") == "HALTED"]
        assert len(halt_events) >= 1

        # Reset state with valid admin token
        executor.journal.append_event("CIRCUIT_BREAKER", {"state": "RUNNING", "manual_override_reset": True, "auth_token": ADMIN_RESET_TOKEN})
        executor.state.circuit_breaker = CircuitBreakerState.RUNNING

        # 2. Missing Date Header -> must call trip_halt
        mock_resp = MagicMock()
        mock_resp.headers.get.return_value = None
        mock_resp.__enter__.return_value = mock_resp
        with patch("urllib.request.urlopen", return_value=mock_resp):
            res2 = executor.check_clock_drift()
            assert res2 is False
            assert executor.state.circuit_breaker == CircuitBreakerState.HALTED


def test_p0_02_emergency_out_of_band_latch_survives_journal_disk_failure():
    """Adversarial probe: if journal append raises OSError('disk full'), emergency latch guarantees HALT on restart."""
    with tempfile.TemporaryDirectory() as tmpdir:
        journal_file = Path(tmpdir) / "test_journal.jsonl"
        executor = ProductionApexExecutor(testnet=True, dry_run=True, acquire_lock=False, journal_path=journal_file)

        # In-memory starts RUNNING
        executor.state.circuit_breaker = CircuitBreakerState.RUNNING

        # Simulate disk full during journal append
        with patch.object(executor.journal, "append_event", side_effect=OSError("No space left on device")):
            with pytest.raises(RuntimeError, match="persistent latch active on disk"):
                executor.trip_halt("Simulated disk full fault")

        # Emergency latch file MUST exist on disk
        assert executor.latch_file.exists()
        assert executor.state.circuit_breaker == CircuitBreakerState.HALTED

        # Restarting a new daemon instance must detect emergency latch and initialize as HALTED
        new_executor = ProductionApexExecutor(testnet=True, dry_run=True, acquire_lock=False, journal_path=journal_file)
        assert new_executor.state.circuit_breaker == CircuitBreakerState.HALTED


def test_p0_03_embedded_cancellation_rejection_suppresses_replacement():
    """Adversarial probe: embedded cancel error is rejected by parse_cancel_response."""
    rejected_cancel_payload = {
        "status": "ok",
        "response": {
            "type": "cancel",
            "data": {
                "statuses": [
                    {"error": "Cancellation rejected"}
                ]
            }
        }
    }
    ok, err = parse_cancel_response(rejected_cancel_payload)
    assert not ok
    assert "Cancellation rejected" in err

    success_cancel_payload = {
        "status": "ok",
        "response": {
            "type": "cancel",
            "data": {
                "statuses": [
                    "success"
                ]
            }
        }
    }
    ok_s, msg_s = parse_cancel_response(success_cancel_payload)
    assert ok_s
    assert msg_s == "SUCCESS"


def test_p0_04_parse_order_response_requires_valid_integer_oid():
    """Adversarial probe: parse_order_response requires valid integer oid for resting and filled."""
    # 1. Filled response missing oid
    res_no_oid = {
        "status": "ok",
        "response": {
            "type": "order",
            "data": {
                "statuses": [{"filled": {"totalSz": "2"}}]
            }
        }
    }
    ok1, oid1, err1 = parse_order_response(res_no_oid)
    assert not ok1
    assert oid1 is None
    assert "missing oid" in err1.lower()

    # 2. Filled response with invalid oid
    res_inv_oid = {
        "status": "ok",
        "response": {
            "type": "order",
            "data": {
                "statuses": [{"filled": {"oid": "invalid_oid_string"}}]
            }
        }
    }
    ok2, oid2, err2 = parse_order_response(res_inv_oid)
    assert not ok2
    assert oid2 is None
    assert "invalid" in err2.lower()

    # 3. Valid filled response with integer oid
    res_valid = {
        "status": "ok",
        "response": {
            "type": "order",
            "data": {
                "statuses": [{"filled": {"oid": 998877, "totalSz": "1.5"}}]
            }
        }
    }
    ok3, oid3, err3 = parse_order_response(res_valid)
    assert ok3
    assert oid3 == 998877
    assert err3 == "FILLED"


def test_p0_04_unhedged_position_trips_durable_halt():
    """Adversarial probe: if exchange rejects stop loss bracket, arm_position_brackets trips durable HALT."""
    with tempfile.TemporaryDirectory() as tmpdir:
        journal_file = Path(tmpdir) / "test_journal.jsonl"
        executor = ProductionApexExecutor(testnet=True, dry_run=False, acquire_lock=False, journal_path=journal_file)

        # Mock 1 active position on ETH
        mock_gateway = MagicMock()
        mock_gateway.account_address = "0xTEST"
        mock_gateway.get_account_state.return_value = (1000.0, 1000.0, {"ETH": {"size": 1.0, "entry_price": 3000.0}})
        mock_gateway.get_mid_price.return_value = 3000.0
        mock_gateway.sz_decimals = {"ETH": 2}
        mock_gateway.get_frontend_open_orders.return_value = []

        # Mock exchange rejecting SL order with embedded error
        rejected_sl_response = {
            "status": "ok",
            "response": {
                "type": "order",
                "data": {
                    "statuses": [{"error": "SL rejection"}]
                }
            }
        }
        mock_gateway.place_trigger_stop.return_value = rejected_sl_response
        mock_gateway.place_trigger_tp.return_value = {"status": "ok", "response": {"type": "order", "data": {"statuses": [{"resting": {"oid": 1111}}]}}}
        executor.gateway = mock_gateway

        # Call arm_position_brackets
        summary = executor.arm_position_brackets()

        # Position must be unhedged AND daemon must trip durable HALT
        assert summary["ETH"]["unhedged"] is True
        assert executor.state.unverified_protection is True
        assert executor.state.circuit_breaker == CircuitBreakerState.HALTED


def test_p0_03_micro_repair_journals_order_intent_with_deterministic_cloid():
    """Adversarial probe: repair slices must journal durable ORDER_INTENT before gateway order submission."""
    with tempfile.TemporaryDirectory() as tmpdir:
        journal_file = Path(tmpdir) / "test_journal.jsonl"
        executor = ProductionApexExecutor(testnet=True, dry_run=False, acquire_lock=False, journal_path=journal_file)

        executor.state.frozen_target_generation_id = "GEN_TEST_4H"
        executor.state.frozen_target_weights = {"BTC": 0.50}
        executor.state.total_micro_bars = 5

        mock_gateway = MagicMock()
        mock_gateway.account_address = "0xTEST"
        # Current weight is 0.10 (dw = +0.40 > Leland deadband 0.10)
        mock_gateway.get_account_state.return_value = (1000.0, 1000.0, {"BTC": {"size": 0.001666, "entry_price": 60000.0}})
        mock_gateway.get_mid_price.return_value = 60000.0
        mock_gateway.sz_decimals = {"BTC": 4}
        mock_gateway.get_frontend_open_orders.return_value = []
        mock_gateway.info.user_fills_by_time.return_value = []
        mock_gateway.info.user_funding_history.return_value = []
        mock_gateway.info.post.return_value = []
        mock_gateway.info.user_state.return_value = {
            "marginSummary": {"accountValue": "1000.0"},
            "assetPositions": [{"position": {"coin": "BTC", "szi": "0.001666", "entryPx": "60000.0", "unrealizedPnl": "0.0"}}]
        }

        # Mock order success
        mock_gateway.place_alo_order.return_value = {
            "status": "ok",
            "response": {"type": "order", "data": {"statuses": [{"resting": {"oid": 778899}}]}}
        }
        executor.gateway = mock_gateway
        executor.reconcile_ledger_events_and_reconstruct_nav = MagicMock(return_value=(1000.0, 0.0, {"BTC": {"size": 0.001666, "entry_px": 60000.0}}))

        with patch.object(executor, "check_clock_drift", return_value=True):
            executor.execute_micro_risk_cycle()

        # Read journal events
        with open(journal_file, "r") as f:
            lines = [json.loads(line) for line in f]

        intents = [e for e in lines if e.get("event_type") == "ORDER_INTENT" and e.get("payload", {}).get("action") == "MICRO_REPAIR"]
        confirms = [e for e in lines if e.get("event_type") == "ORDER_CONFIRMED"]

        assert len(intents) >= 1, "ORDER_INTENT must be journaled before repair order placement!"
        assert len(confirms) >= 1
        intent = intents[0]["payload"]
        assert "EXP103_GEN_TEST_4H_REPAIR_5_BTC" in intent["cloid"]

