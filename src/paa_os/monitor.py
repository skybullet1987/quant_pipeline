"""
Independent Operations Monitor & Two-Tier Supervisor (`src/paa_os/monitor.py`).

Implements PAA Section 4.A.7 (Independent Monitoring), Section 4.D (Anti-Stall Mechanism),
and Acceptance Test #6 (Monitoring Failure Test):
  - Operates 100% independently of the AI Director (zero AI dependency).
  - Detects all 12 failure modes: crashes, stalled processes, missing `/dev/shm` market data,
    unresolved orders, accounting discrepancies, risk breaches, failed scheduled jobs,
    research pipeline failures, deployment failures, loss of connectivity, missing Director
    heartbeats, and excessive API/infrastructure costs.
  - Emits event-driven wakeup (`director_wakeup.trigger`) to wake `polymarket-paa-director-event.path`.
  - Includes `PAAIndependentSupervisor` (invoked by both PID-1 `/etc/systemd/system/paa-system-supervisor.timer`
    and user `polymarket-paa-supervisor.timer`) to detect and repair failures of the monitor itself!
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from scripts.paa_autonomous_controller import check_operational_status
from src.paa_os.accountant import PAAAccountant
from src.paa_os.budget import BudgetManager
from src.paa_os.permissions import PermissionClass, load_autonomy_config
from src.paa_os.task_db import PAATaskDB, parse_iso, utc_now, utc_now_iso

PIPELINE_ROOT = Path(__file__).resolve().parents[2]
DATA_PM = PIPELINE_ROOT / "data" / "polymarket"
PAA_DIR = DATA_PM / "paa"


def _sh(cmd: List[str], timeout: float = 10.0) -> Tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, ((p.stdout or "") + "\n" + (p.stderr or "")).strip()
    except Exception as exc:
        return 1, str(exc)


def _atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    tmp.replace(path)


class PAAMonitor:
    """Tier-1 Independent 1-Minute Operations, Accounting & Director-Heartbeat Monitor."""

    def __init__(
        self,
        db: PAATaskDB,
        accountant: PAAAccountant,
        budget: BudgetManager,
        data_dir: Optional[Path] = None,
        autonomy_cfg: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.db = db
        self.accountant = accountant
        self.budget = budget
        self.data_dir = Path(data_dir) if data_dir is not None else DATA_PM
        self.paa_dir = self.data_dir / "paa"
        self.triggers_dir = self.paa_dir / "triggers"
        self.triggers_dir.mkdir(parents=True, exist_ok=True)
        self.cfg = autonomy_cfg or load_autonomy_config()
        self.mon_cfg = self.cfg.get("monitoring") or {}

    @property
    def master_stop_file(self) -> Path:
        return self.paa_dir / "PAA_MASTER_STOP"

    @property
    def monitor_heartbeat_file(self) -> Path:
        return self.paa_dir / "monitor_heartbeat.json"

    @property
    def wakeup_trigger_file(self) -> Path:
        return self.triggers_dir / "director_wakeup.trigger"

    def trigger_director_event_wakeup(self, reason: str) -> None:
        payload = {"triggered_at_utc": utc_now_iso(), "reason": reason}
        _atomic_write_json(self.wakeup_trigger_file, payload)

    def _check_connectivity(self) -> Tuple[bool, Optional[float], str]:
        t0 = time.perf_counter()
        try:
            req = urllib.request.Request(
                "https://clob.polymarket.com/time",
                headers={"User-Agent": "DominusPAAMonitor/1.0"},
            )
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                _ = resp.read()
            return True, round((time.perf_counter() - t0) * 1000.0, 2), "OK"
        except Exception as exc:
            return False, None, f"CLOB_CONNECTIVITY_LOST:{exc}"

    def _check_vm_resources(self) -> List[str]:
        alerts: List[str] = []
        min_disk_gb = float(self.mon_cfg.get("min_free_disk_gb", 5.0))
        try:
            du = shutil.disk_usage(str(self.data_dir))
            free_gb = du.free / (1024 ** 3)
            if free_gb < min_disk_gb:
                alerts.append(f"LOW_DISK_SPACE:{free_gb:.2f}GB<{min_disk_gb:.1f}GB")
        except Exception:
            pass
        if sys.platform.startswith("linux") and Path("/proc/meminfo").exists():
            min_mem_mb = float(self.mon_cfg.get("min_available_mem_mb", 512.0))
            try:
                for ln in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
                    if ln.startswith("MemAvailable:"):
                        avail_mb = int(ln.split()[1]) / 1024.0
                        if avail_mb < min_mem_mb:
                            alerts.append(f"LOW_MEMORY_AVAILABLE:{avail_mb:.0f}MB<{min_mem_mb:.0f}MB")
                        break
            except Exception:
                pass
        return alerts

    def _check_failed_systemd_jobs(self) -> List[str]:
        if not sys.platform.startswith("linux"):
            return []
        rc, out = _sh(["systemctl", "--user", "list-units", "--state=failed", "--no-legend", "--plain"])
        failed_paa = []
        for ln in out.splitlines():
            parts = ln.split()
            if parts and ("polymarket-" in parts[0] or "apex-" in parts[0]):
                failed_paa.append(parts[0])
        return failed_paa

    def run_monitor_cycle(
        self,
        live_rpc_check: bool = True,
        auto_recover_safe: bool = True,
        check_network: bool = True,
    ) -> Dict[str, Any]:
        """Executes a complete 1-minute independent watchdog & reconciliation cycle."""
        if self.master_stop_file.exists():
            hb = {"checked_at_utc": utc_now_iso(), "status": "PAUSED_BY_MASTER_STOP"}
            _atomic_write_json(self.monitor_heartbeat_file, hb)
            return hb

        anomalies: List[str] = []
        event_wakeup_reasons: List[str] = []

        # 1. SQLite task state integrity check + Anti-Stall worker/dependency recovery
        db_ok, db_msg = self.db.check_integrity()
        if not db_ok:
            anomalies.append(f"TASK_DB_INTEGRITY_ERROR:{db_msg}")
        recovery = self.db.recover_interrupted_tasks(
            backoff_base_sec=float((self.cfg.get("budget") or {}).get("retry_backoff_base_sec", 30.0)),
            kill_hung_local_worker=auto_recover_safe,
        )
        dep_res = self.db.resolve_dependencies_and_detect_cycles()
        if recovery["reclaimed_crashed"] or recovery["reclaimed_hung"]:
            event_wakeup_reasons.append(f"RECLAIMED_INTERRUPTED_TASKS:{recovery['reclaimed_crashed'] + recovery['reclaimed_hung']}")

        # 2. Core trading, shadow & SHM telemetry operational check (+ bounded safe auto-restart)
        op_status, new_incidents = check_operational_status(auto_recover_safe=auto_recover_safe)
        if not op_status.get("all_core_units_active", True):
            inactive = [k for k, v in (op_status.get("systemd_units") or {}).items() if v != "active"]
            anomalies.append(f"INACTIVE_UNITS:{inactive}")
            for u in inactive:
                if u == "polymarket-live-harvester.service":
                    self.db.enqueue_task(
                        category="SERVICE_RECOVERY",
                        priority_label="P0",
                        expected_net_ev_usd_per_day=20.0,
                        dedupe_key="SERVICE_RECOVERY:LIVE_HARVESTER_DOWN",
                        title="Investigate & Safely Recover polymarket-live-harvester.service",
                        financial_impact_hypothesis="Restore live order management & opportunity capture safely when flat.",
                        evidence={"systemd_units": op_status.get("systemd_units")},
                        required_permission_class=PermissionClass.AUTOMATICALLY_PERMITTED.value,
                        next_action="VERIFY_OPEN_POSITIONS_AND_RESTART_IF_SAFE",
                    )
                    event_wakeup_reasons.append("LIVE_HARVESTER_INACTIVE")

        # 3. Connectivity check
        conn_ok, rtt_ms, conn_msg = self._check_connectivity() if check_network else (True, 0.0, "SKIPPED_OFFLINE")
        if not conn_ok:
            anomalies.append(conn_msg)

        # 4. Authoritative Financial Reconciliation & Unresolved Order / Risk Breach Detection
        fin_snap = self.accountant.measure_and_record(live_rpc_check=live_rpc_check)
        if not fin_snap["accounting_ok"]:
            anomalies.extend(fin_snap["details"]["anomalies"])
            event_wakeup_reasons.append("ACCOUNTING_DISCREPANCY")

        st_path = self.data_dir / "live_harvester_state.json"
        if st_path.exists():
            try:
                st = json.loads(st_path.read_text(encoding="utf-8"))
                now_u = time.time()
                # Detect stuck pending entry intents (> 60s)
                stuck_intents = [
                    oid
                    for oid, it in (st.get("pending_entry_intents") or {}).items()
                    if isinstance(it, dict) and (now_u - float(it.get("created_ts", now_u) or now_u)) > 60.0
                ]
                if stuck_intents:
                    anomalies.append(f"UNRESOLVED_ENTRY_INTENTS:{stuck_intents}")
                    self.db.enqueue_task(
                        category="TRADE_FORENSICS",
                        priority_label="P1",
                        expected_net_ev_usd_per_day=5.0,
                        dedupe_key="UNRESOLVED_ORDERS:PENDING_INTENTS",
                        title="Reconcile Stale Pending Entry Intents on CLOB",
                        financial_impact_hypothesis="Unlock reserved cash from stale >60s pending entry intents.",
                        evidence={"stuck_intent_oids": stuck_intents},
                        required_permission_class=PermissionClass.AUTOMATICALLY_PERMITTED.value,
                        next_action="RECONCILE_CLOB_OPEN_ORDERS",
                    )
                    event_wakeup_reasons.append("STUCK_PENDING_INTENTS")

                if bool(st.get("risk_halt")) or bool((st.get("risk_state") or {}).get("halted")):
                    halt_r = str((st.get("risk_state") or {}).get("halt_reason") or "RISK_HALT_ACTIVE")
                    anomalies.append(f"RISK_BREACH_HALT:{halt_r}")

                # RISKLESS PAA Sentinel 1: Post-lock Zero-Loss Live Invariant Check
                rl_mandate = self.cfg.get("riskless_mandate") or {}
                rl_cut = str(rl_mandate.get("riskless_epoch_start_utc") or "2026-11-04T02:05:00Z")
                loss_alert_usd = float(rl_mandate.get("live_loss_alert_threshold_usd", -0.05))
                if bool(rl_mandate.get("enforce_riskless_only_live", True)):
                    from src.paa_os.optimizer import group_closed_positions_by_box
                    _grouped_c = group_closed_positions_by_box(st.get("closed_positions") or [], st.get("active_positions") or {})
                    for c_rec in _grouped_c[-30:]:
                        if not isinstance(c_rec, dict):
                            continue
                        ts_e = str(c_rec.get("entry_time_utc") or c_rec.get("settled_at_utc") or "")
                        if ts_e < rl_cut:
                            continue
                        if (
                            c_rec.get("close_reason") == "MARKET_RESOLVED_NO_INVENTORY"
                            and not bool(c_rec.get("inventory_reconciled", True))
                            and str(c_rec.get("exit_order_status") or "") == "ENTRY_OUTCOME_UNKNOWN"
                        ):
                            continue
                        pnl_c = float(c_rec.get("net_pnl_usd", c_rec.get("realized_pnl_usd", 0.0)) or 0.0)
                        tid_c = str(c_rec.get("trade_id") or "")
                        if tid_c and pnl_c < loss_alert_usd:
                            anomalies.append(f"RISKLESS_ZERO_LOSS_BREACH:{tid_c}:${pnl_c:.2f}")
                            _, created_b = self.db.enqueue_task(
                                category="TRADE_FORENSICS",
                                priority_label="P0",
                                expected_net_ev_usd_per_day=25.0,
                                dedupe_key=f"RISKLESS_BREACH_FORENSICS:{tid_c}",
                                title=f"URGENT P0: Riskless Zero-Loss Invariant Breach on {tid_c} (${pnl_c:.2f})",
                                financial_impact_hypothesis="Immediately root-cause any real-money loss occurring under 100% Riskless-Only Mode.",
                                evidence={"trade": c_rec, "riskless_epoch_start_utc": rl_cut},
                                required_permission_class=PermissionClass.AUTOMATICALLY_PERMITTED.value,
                                payload={"trade_id": tid_c, "trade": c_rec},
                                next_action="CLASSIFY_LOSS_AND_QUEUE_ACTION",
                            )
                            if created_b:
                                event_wakeup_reasons.append(f"RISKLESS_ZERO_LOSS_BREACH:{tid_c}")

                # RISKLESS PAA Sentinel 2: Stale Unredeemed Post-Expiry CTF Position Watchdog
                max_unred_s = float(rl_mandate.get("max_unredeemed_post_expiry_sec", 2700.0))
                stale_unredeemed = []
                for tid_a, p_act in (st.get("active_positions") or {}).items():
                    if not isinstance(p_act, dict):
                        continue
                    exp_u = float(p_act.get("candle_expiry_ts", 0.0) or 0.0)
                    st_a = str(p_act.get("status") or "").upper()
                    if exp_u > 0.0 and (now_u - exp_u) > max_unred_s and "DISPUTE" not in st_a:
                        stale_unredeemed.append(tid_a)
                if stale_unredeemed:
                    anomalies.append(f"UNREDEEMED_POST_EXPIRY_POSITIONS:{stale_unredeemed}")
                    _, created_r = self.db.enqueue_task(
                        category="SERVICE_RECOVERY",
                        priority_label="P1",
                        expected_net_ev_usd_per_day=6.0,
                        dedupe_key=f"REDEMPTION_RECYCLE:{','.join(sorted(stale_unredeemed)[:3])}",
                        title="Audit & Recycle Unredeemed Post-Expiry CTF Positions for Capital Velocity",
                        financial_impact_hypothesis="Unlock settled CTF collateral back into free pUSD for next riskless cycle.",
                        evidence={"stale_unredeemed_trade_ids": stale_unredeemed},
                        required_permission_class=PermissionClass.AUTOMATICALLY_PERMITTED.value,
                        next_action="AUDIT_ONCHAIN_CTF_REDEMPTION_READY",
                    )
                    if created_r:
                        event_wakeup_reasons.append("STALE_UNREDEEMED_CTF")
            except Exception:
                pass

        # 5. Failed scheduled jobs & deployment rollback follow-ups
        failed_units = self._check_failed_systemd_jobs()
        if failed_units:
            anomalies.append(f"FAILED_SYSTEMD_JOBS:{failed_units}")

        recent_deploys = self.db.list_deployments(limit=5)
        for dep in recent_deploys:
            if dep.get("rolled_back") and dep.get("state") == "ROLLED_BACK":
                t, created = self.db.enqueue_task(
                    category="ENGINEERING_REPAIR",
                    priority_label="P1",
                    expected_net_ev_usd_per_day=3.0,
                    dedupe_key=f"POST_ROLLBACK_RCA:{dep['release_id']}",
                    title=f"Root-Cause Rolled-Back Release {dep['release_id']}",
                    financial_impact_hypothesis="Diagnose failed canary release in isolated worktree without risking production.",
                    evidence=dep,
                    required_permission_class=PermissionClass.AUTOMATICALLY_PERMITTED.value,
                    next_action="INSPECT_ROLLBACK_REASON_AND_TEST",
                )
                if created:
                    event_wakeup_reasons.append(f"ROLLED_BACK_DEPLOY:{dep['release_id']}")

        # 6. Independent Check of PAA Director Heartbeat!
        hbs = self.db.get_heartbeats()
        dir_hb = hbs.get("paa_director")
        max_dir_age = float(self.mon_cfg.get("director_heartbeat_max_age_sec", 1200.0))
        director_stale = (dir_hb is None) or (dir_hb.get("age_sec") is not None and float(dir_hb["age_sec"]) > max_dir_age)
        if director_stale:
            dir_age = dir_hb.get("age_sec") if dir_hb else None
            anomalies.append(f"DIRECTOR_HEARTBEAT_MISSING_OR_STALE(age={dir_age}s>{max_dir_age}s)")
            self.db.log_event(
                "monitor",
                "DIRECTOR_HEARTBEAT_STALE_DETECTED",
                {"age_sec": dir_age, "max_allowed_sec": max_dir_age},
            )
            if auto_recover_safe and sys.platform.startswith("linux"):
                _sh(["systemctl", "--user", "enable", "--now", "polymarket-paa-director.timer"])
            event_wakeup_reasons.append("DIRECTOR_HEARTBEAT_STALE")

        # 7. Excessive API / Infrastructure Cost & Disk/Memory Check
        res_alerts = self._check_vm_resources()
        anomalies.extend(res_alerts)
        budget_sum = self.budget.get_usage_summary()
        if not budget_sum["budget_healthy"]:
            anomalies.append(
                f"BUDGET_CAP_TRIGGERED:calls={budget_sum['daily_ai_calls']}/{budget_sum['max_daily_ai_calls']},usd=${budget_sum['daily_ai_cost_usd']:.4f}"
            )

        if event_wakeup_reasons:
            self.trigger_director_event_wakeup(";".join(event_wakeup_reasons))

        summary = {
            "checked_at_utc": utc_now_iso(),
            "status": "OK" if not anomalies else "ANOMALIES_DETECTED",
            "anomalies": anomalies,
            "clob_rtt_ms": rtt_ms,
            "accounting_ok": fin_snap["accounting_ok"],
            "free_cash_pusd": fin_snap["free_cash_pusd"],
            "nav_mark_to_bid_usd": fin_snap["nav_mark_to_bid_usd"],
            "recovered_tasks": recovery,
            "dependency_checks": dep_res,
            "new_service_incidents": new_incidents,
            "director_heartbeat_stale": director_stale,
            "event_wakeups_emitted": event_wakeup_reasons,
        }
        _atomic_write_json(self.monitor_heartbeat_file, summary)
        _atomic_write_json(self.paa_dir / "operational_status.json", {**op_status, "monitor_summary": summary})
        svc_ttl = float((self.cfg.get("zero_trust") or {}).get("service_fact_ttl_sec", 120.0))
        self.db.upsert_verified_fact(
            fact_key="services.all_core_units_active",
            category="OPERATIONAL_HEALTH",
            value=bool(op_status.get("all_core_units_active", True)),
            epistemic_status="VERIFIED_FACT",
            source_type="SYSTEMCTL_PROBE",
            source_ref="operational_status.json:systemd_units",
            verified_by="PAAMonitor",
            ttl_sec=svc_ttl,
            revalidation_rule="RECHECK_SYSTEMD_EVERY_60S",
        )
        if check_network and rtt_ms > 0:
            self.db.upsert_verified_fact(
                fact_key="clob.rest_time_rtt_ms",
                category="EXCHANGE_OBSERVATION",
                value=round(float(rtt_ms), 2),
                epistemic_status="OBSERVATION",
                source_type="HTTPS_CLOB_TIME_PING",
                source_ref="https://clob.polymarket.com/time",
                verified_by="PAAMonitor",
                ttl_sec=float((self.cfg.get("zero_trust") or {}).get("latency_fact_ttl_sec", 180.0)),
                revalidation_rule="TRANSIENT_NETWORK_MEASUREMENT_EXPIRES_IN_180S",
            )
        self.db.record_heartbeat("paa_monitor", status=summary["status"], details={"anomalies_count": len(anomalies)})
        return summary


class PAAIndependentSupervisor:
    """
    Tier-2 Independent Supervisor (`Acceptance Test #6`).
    Runs via BOTH `/etc/systemd/system/paa-system-supervisor.timer` (PID-1 root/system timer)
    AND `~/.config/systemd/user/polymarket-paa-supervisor.timer`.
    Detects when `polymarket-paa-monitor` itself stops, crashes, or goes stale, records forensic
    evidence, and automatically restores `polymarket-paa-monitor.timer` + runs an immediate check.
    """

    def __init__(
        self,
        db: PAATaskDB,
        data_dir: Optional[Path] = None,
        autonomy_cfg: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.db = db
        self.data_dir = Path(data_dir) if data_dir is not None else DATA_PM
        self.paa_dir = self.data_dir / "paa"
        self.paa_dir.mkdir(parents=True, exist_ok=True)
        self.cfg = autonomy_cfg or load_autonomy_config()
        self.mon_cfg = self.cfg.get("monitoring") or {}

    def run_supervision_check(
        self,
        auto_repair: bool = True,
        repair_callback: Optional[Any] = None,
    ) -> Dict[str, Any]:
        master_stop = self.paa_dir / "PAA_MASTER_STOP"
        if master_stop.exists():
            res = {"checked_at_utc": utc_now_iso(), "status": "PAUSED_BY_MASTER_STOP", "monitor_failed": False}
            _atomic_write_json(self.paa_dir / "supervisor_heartbeat.json", res)
            return res

        max_age = float(self.mon_cfg.get("monitor_heartbeat_max_age_sec", 180.0))
        hb_file = self.paa_dir / "monitor_heartbeat.json"
        now = utc_now()

        hb_age: Optional[float] = None
        if hb_file.exists():
            try:
                hb_data = json.loads(hb_file.read_text(encoding="utf-8"))
                dt = parse_iso(hb_data.get("checked_at_utc"))
                if dt is not None:
                    hb_age = round((now - dt).total_seconds(), 2)
            except Exception:
                hb_age = 999999.0

        timer_active = True
        if sys.platform.startswith("linux"):
            rc_t, out_t = _sh(["systemctl", "--user", "is-active", "polymarket-paa-monitor.timer"])
            timer_active = (rc_t == 0 and out_t.strip() == "active")

        monitor_failed = (hb_age is None) or (hb_age > max_age) or (not timer_active)
        repaired = False
        repair_details = ""

        if monitor_failed:
            failure_reason = (
                f"MONITOR_FAILURE_DETECTED(timer_active={timer_active}, heartbeat_age_sec={hb_age}, max_allowed_sec={max_age})"
            )
            self.db.log_event(
                "independent_supervisor",
                "MONITORING_FAILURE_DETECTED",
                {"timer_active": timer_active, "heartbeat_age_sec": hb_age, "max_allowed_sec": max_age},
            )
            if auto_repair:
                if repair_callback is not None:
                    repair_callback()
                    repaired = True
                    repair_details = "EXECUTED_IN_PROCESS_MONITOR_REPAIR_CALLBACK"
                elif sys.platform.startswith("linux"):
                    _sh(["systemctl", "--user", "daemon-reload"])
                    _sh(["systemctl", "--user", "enable", "--now", "polymarket-paa-monitor.timer"])
                    rc_run, out_run = _sh(["systemctl", "--user", "start", "polymarket-paa-monitor.service"], timeout=45.0)
                    rc_chk, out_chk = _sh(["systemctl", "--user", "is-active", "polymarket-paa-monitor.timer"])
                    repaired = (rc_run == 0 and rc_chk == 0 and out_chk.strip() == "active")
                    repair_details = f"Re-enabled polymarket-paa-monitor.timer ({out_chk.strip()}) & ran immediate monitor service (rc={rc_run})"

                inc_path = self.paa_dir / "incident_and_repair_log.json"
                inc_doc = json.loads(inc_path.read_text(encoding="utf-8")) if inc_path.exists() else {"incidents": []}
                inc_list = list(inc_doc.get("incidents") or [])
                inc_list.append(
                    {
                        "timestamp_utc": utc_now_iso(),
                        "incident_id": f"SUPERVISOR_MONITOR_RECOVERY_{int(time.time())}",
                        "severity": "HIGH",
                        "component": "polymarket-paa-monitor.timer",
                        "root_cause": failure_reason,
                        "action_taken": repair_details,
                        "status": "VERIFIED COMPLETE" if repaired else "FAILED",
                    }
                )
                _atomic_write_json(inc_path, {"updated_at_utc": utc_now_iso(), "incidents": inc_list[-100:]})
                self.db.log_event(
                    "independent_supervisor",
                    "MONITORING_FAILURE_REPAIRED" if repaired else "MONITORING_REPAIR_FAILED",
                    {"repaired": repaired, "details": repair_details},
                )

        result = {
            "checked_at_utc": utc_now_iso(),
            "status": "RECOVERED" if (monitor_failed and repaired) else ("MONITOR_FAILED" if monitor_failed else "OK"),
            "monitor_failed": monitor_failed,
            "monitor_failed_detected": monitor_failed,
            "monitor_timer_was_active": timer_active,
            "monitor_heartbeat_age_sec": hb_age,
            "repaired": repaired,
            "auto_repaired": repaired,
            "repair_details": repair_details,
        }
        _atomic_write_json(self.paa_dir / "supervisor_heartbeat.json", result)
        self.db.record_heartbeat("paa_supervisor", status=result["status"], details=result)
        return result
