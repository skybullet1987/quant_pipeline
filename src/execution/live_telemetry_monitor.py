#!/usr/bin/env python3
"""
HYPERCORE LIVE TELEMETRY & REAL-TIME WATCHDOG MONITOR (v9.8)
============================================================
Autonomous telemetry streaming and execution risk guardrail monitor for Phase 4 Canary.

Enforces:
  1. Real-time structured telemetry streaming to artifacts/canary_telemetry.jsonl
  2. Account Margin Ratio Watchdog (> 65% warning, > 80% emergency de-risk)
  3. WebSocket Heartbeat & REST Latency Watchdog (> 15s drop or > 3,000 ms latency freezes orders)
  4. 15.0% Peak-to-Trough Drawdown Kill Switch (flattens Tranche B, cuts Tranche A to 0.5x)
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PIPELINE_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_TELEMETRY_LOG = PIPELINE_ROOT / "artifacts" / "canary_telemetry.jsonl"


@dataclass
class TelemetryRecord:
    timestamp_utc: str
    timestamp_ms: int
    event_type: str
    account_value_usd: float
    margin_used_usd: float
    margin_ratio: float
    drawdown_pct: float
    peak_equity_usd: float
    gross_leverage: float
    open_positions_count: int
    active_orders_count: int
    fee_drag_bps: float
    accounting_discrepancy_usd: float
    guardrail_status: str
    details: Dict[str, Any] = field(default_factory=dict)


class TelemetryMonitor:
    """
    Real-Time Telemetry & Watchdog Monitor for Canary Deployment.
    """
    def __init__(
        self,
        log_path: Optional[Path] = None,
        dry_run: bool = False,
        max_margin_warn: float = 0.65,
        max_margin_kill: float = 0.80,
        max_drawdown_limit: float = 0.15,
        max_heartbeat_drop_sec: float = 15.0,
        max_rest_latency_ms: float = 3000.0,
    ):
        self.log_path = log_path or DEFAULT_TELEMETRY_LOG
        self.dry_run = dry_run
        self.max_margin_warn = max_margin_warn
        self.max_margin_kill = max_margin_kill
        self.max_drawdown_limit = max_drawdown_limit
        self.max_heartbeat_drop_sec = max_heartbeat_drop_sec
        self.max_rest_latency_ms = max_rest_latency_ms

        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.last_heartbeat_time = time.time()
        self.is_frozen = False
        self.kill_switch_triggered = False

    def check_margin_health(self, account_val: float, margin_used: float) -> bool:
        """
        Evaluates Account Margin Ratio = margin_used / account_value.
        Returns True if within safe bounds, False if emergency de-risk is breached (> 80%).
        """
        if account_val <= 0.0:
            if margin_used > 0.0:
                self._record_alert(
                    "EMERGENCY_DERISK",
                    f"CRITICAL: Margin used (${margin_used:,.2f}) with zero/negative equity (${account_val:,.2f})!"
                )
                return False
            return True

        margin_ratio = margin_used / account_val

        if margin_ratio > self.max_margin_kill:
            self._record_alert(
                "EMERGENCY_DERISK",
                f"BREACH: Margin Ratio {margin_ratio * 100.0:.2f}% > {self.max_margin_kill * 100.0:.1f}% threshold! Cancelling orders and derisking to cash."
            )
            return False
        elif margin_ratio > self.max_margin_warn:
            self._record_alert(
                "MARGIN_WARNING",
                f"WARNING: Margin Ratio {margin_ratio * 100.0:.2f}% > {self.max_margin_warn * 100.0:.1f}% threshold. Restricting further leverage expansion."
            )

        return True

    def check_heartbeat_health(self, last_ws_frame_ts: float) -> bool:
        """Asserts WebSocket frame stream is active within 15 seconds."""
        now = time.time()
        elapsed = now - last_ws_frame_ts
        if elapsed > self.max_heartbeat_drop_sec:
            self.is_frozen = True
            self._record_alert(
                "WATCHDOG_FREEZE",
                f"ALERT: WebSocket heartbeat dropped for {elapsed:.1f}s > {self.max_heartbeat_drop_sec:.1f}s limit! Freezing order generation."
            )
            return False
        self.is_frozen = False
        return True

    def check_rest_latency(self, latency_ms: float) -> bool:
        """Asserts REST API responses return within 3,000 ms."""
        if latency_ms > self.max_rest_latency_ms:
            self._record_alert(
                "LATENCY_DEGRADATION",
                f"WARNING: REST API latency {latency_ms:.1f} ms exceeds {self.max_rest_latency_ms:.1f} ms ceiling."
            )
            return False
        return True

    def check_drawdown_kill_switch(self, equity: float, peak_equity: float) -> Tuple[bool, float]:
        """
        Asserts peak-to-trough drawdown <= 15.0%.
        If breached: signals kill switch (flatten Tranche B, reduce Tranche A to 0.5x, halt).
        """
        if peak_equity <= 0.0:
            return True, 0.0

        dd = max(0.0, 1.0 - (equity / peak_equity))
        if dd > self.max_drawdown_limit:
            self.kill_switch_triggered = True
            self._record_alert(
                "DRAWDOWN_KILL_SWITCH",
                f"CRITICAL: Total account drawdown {dd * 100.0:.2f}% breached {self.max_drawdown_limit * 100.0:.1f}% ceiling! Initiating emergency shutdown."
            )
            return False, dd

        return True, dd

    def log_telemetry_event(
        self,
        event_type: str,
        account_val: float,
        margin_used: float,
        equity: float,
        peak_equity: float,
        gross_leverage: float = 0.0,
        open_positions: int = 0,
        active_orders: int = 0,
        fee_drag_bps: float = 0.0,
        accounting_disc: float = 0.0,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Appends structured JSONL telemetry record."""
        now_utc = datetime.now(timezone.utc)
        margin_ratio = margin_used / max(1.0, account_val)
        dd_pct = max(0.0, 1.0 - (equity / max(1.0, peak_equity))) * 100.0

        status = "HEALTHY"
        if self.kill_switch_triggered:
            status = "KILL_SWITCH"
        elif self.is_frozen:
            status = "FROZEN"
        elif margin_ratio > self.max_margin_warn:
            status = "MARGIN_ALERT"

        record = TelemetryRecord(
            timestamp_utc=now_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
            timestamp_ms=int(now_utc.timestamp() * 1000),
            event_type=event_type,
            account_value_usd=round(account_val, 4),
            margin_used_usd=round(margin_used, 4),
            margin_ratio=round(margin_ratio, 4),
            drawdown_pct=round(dd_pct, 4),
            peak_equity_usd=round(peak_equity, 4),
            gross_leverage=round(gross_leverage, 4),
            open_positions_count=open_positions,
            active_orders_count=active_orders,
            fee_drag_bps=round(fee_drag_bps, 2),
            accounting_discrepancy_usd=round(accounting_disc, 6),
            guardrail_status=status,
            details=details or {},
        )

        with open(self.log_path, "a") as f:
            f.write(json.dumps(asdict(record)) + "\n")

    def _record_alert(self, alert_type: str, message: str):
        now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        print(f"[{now_utc}] [{alert_type}] {message}", flush=True)
        alert_record = {
            "timestamp_utc": now_utc,
            "timestamp_ms": int(time.time() * 1000),
            "event_type": alert_type,
            "message": message,
        }
        with open(self.log_path, "a") as f:
            f.write(json.dumps(alert_record) + "\n")


if __name__ == "__main__":
    mon = TelemetryMonitor(dry_run=True)
    is_ok = mon.check_margin_health(account_val=1000.0, margin_used=200.0)
    assert is_ok is True
    mon.log_telemetry_event(
        event_type="PREFLIGHT_INIT",
        account_val=1000.0,
        margin_used=200.0,
        equity=1000.0,
        peak_equity=1000.0,
        gross_leverage=0.20,
        open_positions=0,
        active_orders=0,
        details={"status": "initialization_check"}
    )
    print("TelemetryMonitor self-test passed.")
