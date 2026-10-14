"""Phase 0.2 adversarial fault-injection tests for the production Apex daemon.

These exercise real state transitions and persistence (restart replay), not substituted flags.
"""
import json
import tempfile
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.execution.production_apex_daemon import (
    CircuitBreakerState,
    EventJournal,
    ProductionApexExecutor,
    parse_cancel_response,
    parse_order_response,
)


def _executor(tmpdir, dry_run=False):
    return ProductionApexExecutor(
        testnet=True, dry_run=dry_run, acquire_lock=False,
        journal_path=Path(tmpdir) / "j.jsonl",
    )


def _restart(tmpdir):
    return _executor(tmpdir)


def _seed(ex):
    # Non-empty journal so boot does not try to init an epoch from the exchange
    ex.journal.append_event("EPOCH_INIT", {"initial_equity": 1000.0, "hwm": 1000.0, "epoch_start_ms": 1})


def test_clock_http_exception_durably_halts_and_survives_restart():
    with tempfile.TemporaryDirectory() as d:
        ex = _executor(d)
        _seed(ex)
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("503")):
            assert ex.check_clock_drift() is False
        assert ex.state.circuit_breaker == CircuitBreakerState.HALTED
        assert ex.journal.replay_and_project().circuit_breaker == CircuitBreakerState.HALTED
        assert _restart(d).state.circuit_breaker == CircuitBreakerState.HALTED


def test_clock_missing_date_header_durably_halts():
    with tempfile.TemporaryDirectory() as d:
        ex = _executor(d)
        _seed(ex)
        resp = MagicMock()
        resp.headers.get.return_value = None
        resp.__enter__.return_value = resp
        with patch("urllib.request.urlopen", return_value=resp):
            assert ex.check_clock_drift() is False
        assert ex.journal.replay_and_project().circuit_breaker == CircuitBreakerState.HALTED


def test_halt_survives_journal_append_failure_via_latch():
    with tempfile.TemporaryDirectory() as d:
        ex = _executor(d)
        _seed(ex)
        with patch.object(ex.journal, "append_event", side_effect=OSError("disk full")):
            with pytest.raises(RuntimeError):
                ex.trip_halt("test")
        assert ex.state.circuit_breaker == CircuitBreakerState.HALTED
        # Journal has no HALT, but restart must still be blocked by the out-of-band latch
        assert ex.journal.replay_and_project().circuit_breaker != CircuitBreakerState.HALTED
        assert _restart(d).state.circuit_breaker == CircuitBreakerState.HALTED


def test_post_v2_legacy_record_rejected():
    with tempfile.TemporaryDirectory() as d:
        j = EventJournal(Path(d) / "j.jsonl")
        j.append_event("EPOCH_INIT", {"initial_equity": 1000.0})
        line = json.dumps({
            "event_id": 2, "event_type": "CIRCUIT_BREAKER",
            "payload": {"state": "RUNNING", "manual_override_reset": True},
            "prev_hash": j.last_hash, "hash": "0" * 64,
        })
        with open(j.path, "a") as f:
            f.write(line + "\n")
        with pytest.raises(ValueError):
            EventJournal(j.path).replay_and_project()


def test_embedded_cancel_rejection_not_confirmed():
    res = {"status": "ok", "response": {"type": "cancel", "data": {"statuses": [{"error": "Cancellation rejected"}]}}}
    assert parse_cancel_response(res)[0] is False
    assert parse_cancel_response({"status": "ok", "response": {"type": "cancel", "data": {"statuses": ["success"]}}})[0] is True


def test_filled_without_oid_not_accepted():
    res = {"status": "ok", "response": {"type": "order", "data": {"statuses": [{"filled": {"totalSz": "2"}}]}}}
    assert parse_order_response(res)[0] is False


def test_reconcile_fails_closed_when_fill_query_errors():
    with tempfile.TemporaryDirectory() as d:
        ex = _executor(d)
        _seed(ex)
        ex.gateway = MagicMock()
        ex.gateway.get_account_state.return_value = (1000.0, 1000.0, {})
        ex.gateway.info.user_state.return_value = {"assetPositions": []}
        ex.gateway.info.user_fills_by_time.side_effect = RuntimeError("api down")
        ex.gateway.info.post.return_value = []
        with pytest.raises(RuntimeError, match="incomplete"):
            ex.reconcile_ledger_events_and_reconstruct_nav()
        # Cycle entry points must abort with no order placed
        ex.check_clock_drift = lambda: True
        ex.execute_micro_risk_cycle()
        assert ex.gateway.place_alo_order.call_count == 0


def test_latch_preserved_across_reconcile_replay():
    with tempfile.TemporaryDirectory() as d:
        ex = _executor(d)
        _seed(ex)
        with patch.object(ex.journal, "append_event", side_effect=OSError("disk full")):
            with pytest.raises(RuntimeError):
                ex.trip_halt("test")
        ex.gateway = MagicMock()
        ex.gateway.get_account_state.return_value = (1000.0, 1000.0, {})
        ex.gateway.info.user_state.return_value = {"assetPositions": []}
        ex.gateway.info.user_fills_by_time.return_value = []
        ex.gateway.info.post.return_value = []
        ex.reconcile_ledger_events_and_reconstruct_nav()
        assert ex.state.circuit_breaker == CircuitBreakerState.HALTED
