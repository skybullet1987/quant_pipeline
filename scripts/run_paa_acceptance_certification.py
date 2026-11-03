#!/usr/bin/env python3
"""
Live VM Acceptance Certification Suite for PROFIT ABOVE ALL (PAA) Autonomous OS
(`scripts/run_paa_acceptance_certification.py`).

Executes and records verifiable, timestamped, reproducible evidence on `kraken-finland`
for all 12 Mandatory Acceptance Tests (`Section 4.E`):
  --record-reboot-pre   : Snapshots boot_id, uptime, systemd units & live CLOB orders BEFORE `sudo reboot`
  --record-reboot-post  : Verifies new boot_id, automatic systemd recovery & untouched CLOB orders AFTER `sudo reboot`
  --run-tests-2-to-12   : Executes live OS/process/systemd/AI/Git/Financial/Permission/Research certification tests 2..12
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

PIPELINE_ROOT = Path(__file__).resolve().parents[1]
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from scripts.paa_autonomous_controller import reconcile_authoritative_ledger
from src.paa_os.accountant import PAAAccountant
from src.paa_os.agent_runtime import HeadlessAgentRunner
from src.paa_os.budget import BudgetManager
from src.paa_os.builder_and_deployer import DeploymentController, GitWorktreeBuilder, _find_git_exe
from src.paa_os.director import PAADirector
from src.paa_os.monitor import PAAIndependentSupervisor, PAAMonitor, _atomic_write_json
from src.paa_os.permissions import (
    PermissionClass,
    PermissionDeniedError,
    PermissionGate,
    build_isolated_worker_env,
    load_autonomy_config,
)
from src.paa_os.researcher import PAAResearcher
from src.paa_os.task_db import PAATaskDB, utc_now_iso
from src.polymarket_research.holistic_strategy_governance import DEFAULT_HOLISTIC_CONFIG

PAA_DIR = PIPELINE_ROOT / "data" / "polymarket" / "paa"
EVIDENCE_PATH = PAA_DIR / "acceptance_certification_evidence.json"

CORE_AND_PAA_USER_UNITS = [
    "polymarket-live-harvester.service",
    "polymarket-alpha124-shadow.service",
    "polymarket-recorder.service",
    "polymarket-paa-monitor.timer",
    "polymarket-paa-supervisor.timer",
    "polymarket-paa-watchdog.timer",
    "polymarket-paa-director.timer",
    "polymarket-paa-director-event.path",
    "polymarket-paa-hourly-opt.timer",
    "polymarket-paa-6h-eval.timer",
    "polymarket-paa-daily-report.timer",
    "polymarket-paa-weekly-review.timer",
]


def _sh(cmd: List[str], timeout: float = 30.0) -> Dict[str, Any]:
    env = dict(os.environ)
    if sys.platform.startswith("linux"):
        uid = os.getuid()
        env.setdefault("XDG_RUNTIME_DIR", f"/run/user/{uid}")
        env.setdefault("DBUS_SESSION_BUS_ADDRESS", f"unix:path=/run/user/{uid}/bus")
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
    return {
        "cmd": " ".join(cmd),
        "returncode": p.returncode,
        "stdout": (p.stdout or "").strip(),
        "stderr": (p.stderr or "").strip(),
    }


def _load_evidence() -> Dict[str, Any]:
    if EVIDENCE_PATH.exists():
        try:
            return json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"suite": "PAA_MANDATORY_ACCEPTANCE_TESTS_V1", "tests": {}}


def _save_evidence(doc: Dict[str, Any]) -> None:
    doc["updated_at_utc"] = utc_now_iso()
    _atomic_write_json(EVIDENCE_PATH, doc)


def _snapshot_vm_and_trading_state() -> Dict[str, Any]:
    boot_id = Path("/proc/sys/kernel/random/boot_id").read_text(encoding="utf-8").strip() if Path("/proc/sys/kernel/random/boot_id").exists() else "UNKNOWN"
    uptime_s = float(Path("/proc/uptime").read_text(encoding="utf-8").split()[0]) if Path("/proc/uptime").exists() else 0.0
    user_units = {}
    for u in CORE_AND_PAA_USER_UNITS:
        r = _sh(["systemctl", "--user", "is-active", u])
        user_units[u] = r["stdout"]
    sys_sup = _sh(["systemctl", "is-active", "paa-system-supervisor.timer"])["stdout"]

    st_path = PIPELINE_ROOT / "data" / "polymarket" / "live_harvester_state.json"
    active_orders = {}
    if st_path.exists():
        st = json.loads(st_path.read_text(encoding="utf-8"))
        for k, v in (st.get("active_positions") or {}).items():
            if isinstance(v, dict):
                active_orders[k] = {
                    "resting_exit_oid": v.get("resting_exit_oid"),
                    "shares": v.get("shares"),
                    "resting_exit_px": v.get("resting_exit_px"),
                }
    return {
        "captured_at_utc": utc_now_iso(),
        "boot_id": boot_id,
        "uptime_sec": round(uptime_s, 2),
        "paa_system_supervisor_timer": sys_sup,
        "user_units": user_units,
        "active_positions_resting_orders": active_orders,
    }


def record_reboot_pre() -> None:
    doc = _load_evidence()
    snap = _snapshot_vm_and_trading_state()
    doc["reboot_pre_snapshot"] = snap
    _save_evidence(doc)
    print(json.dumps(snap, indent=2))


def record_reboot_post() -> None:
    doc = _load_evidence()
    pre = doc.get("reboot_pre_snapshot") or {}
    # Allow up to 45s after early SSH reconnect for OnBootSec timers/services to settle
    deadline = time.time() + 45.0
    post = _snapshot_vm_and_trading_state()
    while time.time() < deadline:
        all_up = (
            post["paa_system_supervisor_timer"] == "active"
            and all(v == "active" for v in post["user_units"].values())
        )
        if all_up:
            break
        time.sleep(3.0)
        post = _snapshot_vm_and_trading_state()

    boot_changed = bool(pre.get("boot_id")) and (pre.get("boot_id") != post["boot_id"])
    all_units_active = (
        post["paa_system_supervisor_timer"] == "active"
        and all(v == "active" for v in post["user_units"].values())
    )
    pre_oids = {k: v.get("resting_exit_oid") for k, v in (pre.get("active_positions_resting_orders") or {}).items()}
    post_oids = {k: v.get("resting_exit_oid") for k, v in (post.get("active_positions_resting_orders") or {}).items()}
    orders_preserved = (pre_oids == post_oids)

    passed = boot_changed and all_units_active and orders_preserved
    res = {
        "test_number": 1,
        "name": "Reboot Test",
        "passed": passed,
        "verified_at_utc": utc_now_iso(),
        "pre_reboot": pre,
        "post_reboot": post,
        "assertions": {
            "kernel_boot_id_changed": boot_changed,
            "all_13_paa_and_trading_units_auto_resumed": all_units_active,
            "resting_clob_orders_preserved": orders_preserved,
        },
    }
    doc["tests"]["01_reboot_test"] = res
    _save_evidence(doc)
    print(json.dumps(res, indent=2))
    if not passed:
        raise SystemExit(1)


def run_tests_2_to_12() -> None:
    doc = _load_evidence()
    cfg = copy.deepcopy(load_autonomy_config())

    # -------------------------------------------------------------------------
    # TEST 2 & TEST 4: Agent Crash Test (`SIGKILL`) + Task Persistence Test
    # -------------------------------------------------------------------------
    with tempfile.TemporaryDirectory(prefix="paa_cert_crash_") as td:
        tdir = Path(td)
        test_cfg = copy.deepcopy(cfg)
        test_cfg["budget"]["retry_backoff_base_sec"] = 0.05
        director = PAADirector(repo_root=PIPELINE_ROOT, data_dir=tdir / "data", autonomy_cfg=test_cfg)
        side_log = tdir / "resumable_steps.log"
        task_rec, _ = director.db.enqueue_task(
            category="QA_VALIDATION",
            priority_label="P1",
            expected_net_ev_usd_per_day=5.0,
            title="Multi-step Crash & Checkpoint Persistence Verification",
            payload={
                "side_effect_log_path": str(side_log),
                "steps": [
                    {"step_id": "step_1", "action": "APPEND_MARKER"},
                    {"step_id": "step_2", "action": "APPEND_MARKER"},
                    {"step_id": "step_3", "action": "APPEND_MARKER"},
                ],
            },
        )
        tid = task_rec["task_id"]

        # Spawn a real child worker process that claims the task, executes step_1, checkpoints, and hangs in step_2
        worker_code = (
            "import sys, time; "
            f"sys.path.insert(0, {str(PIPELINE_ROOT)!r}); "
            "from src.paa_os.task_db import PAATaskDB; "
            f"db = PAATaskDB({str(director.db.db_path)!r}); "
            "t = db.claim_next_eligible_task(worker_id='real_child_worker', lease_ttl_sec=120.0); "
            f"open({str(side_log)!r}, 'a').write('step_1\\n'); "
            "db.save_checkpoint(t['task_id'], {'completed_steps': ['step_1'], 'step_outputs': {'step_1': {'ok': True}}}, 'RUNNING_STEP_2'); "
            f"open({str(tdir / 'ready.flag')!r}, 'w').write(str(t['task_id'])); "
            "time.sleep(60)"
        )
        child = subprocess.Popen([sys.executable, "-c", worker_code])
        deadline = time.time() + 10.0
        while not (tdir / "ready.flag").exists() and time.time() < deadline:
            time.sleep(0.05)
        killed_pid = child.pid
        # Force-kill the active worker mid-task with SIGKILL (-9)!
        os.kill(killed_pid, signal.SIGKILL)
        child.wait(timeout=5.0)
        time.sleep(0.10)

        # Run recovery + Director resumption
        cycle_out = director.run_cycle(max_tasks_per_cycle=2, allow_headless_ai=False, run_proactive_research_if_idle=False)
        final_t = director.db.get_task(tid)
        executed_lines = [ln.strip() for ln in side_log.read_text(encoding="utf-8").splitlines() if ln.strip()]

        crash_passed = (
            len(cycle_out["recovered_interrupted"]["reclaimed_crashed"]) == 1
            and final_t is not None
            and final_t["state"] == "COMPLETED"
        )
        persistence_passed = (executed_lines == ["step_1", "step_2", "step_3"])

        doc["tests"]["02_agent_crash_test"] = {
            "test_number": 2,
            "name": "Agent Crash Test",
            "passed": crash_passed,
            "verified_at_utc": utc_now_iso(),
            "killed_worker_pid": killed_pid,
            "signal": "SIGKILL (-9)",
            "recovered_interrupted": cycle_out["recovered_interrupted"],
            "final_task_state": final_t["state"] if final_t else None,
            "last_error_recorded_on_crash": final_t["last_error"] if final_t else None,
        }
        doc["tests"]["04_task_persistence_test"] = {
            "test_number": 4,
            "name": "Task Persistence Test",
            "passed": persistence_passed,
            "verified_at_utc": utc_now_iso(),
            "task_id": tid,
            "side_effect_execution_order": executed_lines,
            "duplicate_steps_executed": 0 if persistence_passed else -1,
            "final_checkpoint": final_t["last_checkpoint"] if final_t else None,
        }

    # -------------------------------------------------------------------------
    # TEST 3: Session Independence Test (Systemd `.path` event trigger + Headless `agy` CLI with zero TTY)
    # -------------------------------------------------------------------------
    prod_db = PAATaskDB()
    headless_task, _ = prod_db.enqueue_task(
        category="QA_VALIDATION",
        priority_label="P0",
        expected_net_ev_usd_per_day=9.0,
        dedupe_key=f"CERT_SESSION_INDEP_{int(time.time())}",
        title="Headless Systemd Session-Independence Verification via agy CLI",
        financial_impact_hypothesis="Prove unattended systemd execution of agy CLI without any open interactive session.",
        required_permission_class=PermissionClass.AUTOMATICALLY_PERMITTED.value,
        payload={
            "steps": [
                {
                    "step_id": "headless_agy_check",
                    "action": "HEADLESS_AI_ANALYSIS",
                    "prompt": "Reply with the single exact token: HEADLESS_PAA_AUTONOMY_VERIFIED",
                    "timeout_sec": 60,
                }
            ]
        },
    )
    hl_tid = headless_task["task_id"]
    # Trigger event-driven `.path` wakeup (`polymarket-paa-director-event.path` -> `polymarket-paa-director.service` under systemd user manager PID, zero TTY!)
    trig_file = PAA_DIR / "triggers" / "director_wakeup.trigger"
    _atomic_write_json(trig_file, {"triggered_at_utc": utc_now_iso(), "reason": f"CERT_TEST_3:{hl_tid}"})

    deadline = time.time() + 75.0
    hl_final = prod_db.get_task(hl_tid)
    while time.time() < deadline:
        hl_final = prod_db.get_task(hl_tid)
        if hl_final and hl_final["state"] in ("COMPLETED", "FAILED", "ESCALATED"):
            break
        time.sleep(1.5)

    journal_out = _sh(["journalctl", "--user", "-u", "polymarket-paa-director.service", "-n", "25", "--no-pager"])["stdout"]
    session_indep_passed = (
        hl_final is not None
        and hl_final["state"] == "COMPLETED"
        and "HEADLESS_PAA_AUTONOMY_VERIFIED" in json.dumps(hl_final.get("completion_evidence") or {})
    )
    doc["tests"]["03_session_independence_test"] = {
        "test_number": 3,
        "name": "Session Independence Test",
        "passed": session_indep_passed,
        "verified_at_utc": utc_now_iso(),
        "trigger_mechanism": "polymarket-paa-director-event.path -> polymarket-paa-director.service (systemd user manager, TTY=none)",
        "task_id": hl_tid,
        "task_state": hl_final["state"] if hl_final else None,
        "completion_evidence": hl_final.get("completion_evidence") if hl_final else None,
        "systemd_journal_tail": journal_out[-1200:],
    }

    # -------------------------------------------------------------------------
    # TEST 5: Stalled Worker Test (Hung Process Killed + Independent Work Continues)
    # -------------------------------------------------------------------------
    with tempfile.TemporaryDirectory(prefix="paa_cert_stall_") as td:
        s_db = PAATaskDB(Path(td) / "stall.db")
        hung_proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(180)"])
        hung_pid = hung_proc.pid
        t_stall, _ = s_db.enqueue_task(category="ENGINEERING_OPTIMIZATION", priority_label="P2", title="Hung Worker Simulation")
        t_other, _ = s_db.enqueue_task(category="PROFIT_REPORTING", priority_label="P1", title="Independent Unblocked Task")
        s_db.claim_next_eligible_task(
            worker_id="hung_worker_sim",
            worker_pid=hung_pid,
            lease_ttl_sec=1.0,
            allowed_categories={"ENGINEERING_OPTIMIZATION"},
        )
        time.sleep(1.3)
        stall_rec = s_db.recover_interrupted_tasks(backoff_base_sec=30.0, kill_hung_local_worker=True)
        hung_proc.wait(timeout=5.0)
        claimed_other = s_db.claim_next_eligible_task(worker_id="healthy_worker")
        if claimed_other:
            s_db.complete_task(claimed_other["task_id"], {"independent_progress": True})

        stall_passed = (
            len(stall_rec["reclaimed_hung"]) == 1
            and hung_proc.poll() is not None
            and claimed_other is not None
            and claimed_other["task_id"] == t_other["task_id"]
        )
        doc["tests"]["05_stalled_worker_test"] = {
            "test_number": 5,
            "name": "Stalled Worker Test",
            "passed": stall_passed,
            "verified_at_utc": utc_now_iso(),
            "hung_worker_pid": hung_pid,
            "hung_worker_exit_code": hung_proc.returncode,
            "recovery_summary": stall_rec,
            "independent_task_completed_while_stalled_in_backoff": claimed_other["task_id"] if claimed_other else None,
        }

    # -------------------------------------------------------------------------
    # TEST 6: Monitoring Failure Test (Stop Monitor Timer -> PID-1 System Supervisor Detects & Repairs!)
    # -------------------------------------------------------------------------
    _sh(["systemctl", "--user", "stop", "polymarket-paa-monitor.timer"])
    stopped_state = _sh(["systemctl", "--user", "is-active", "polymarket-paa-monitor.timer"])["stdout"]
    stale_hb_ts = (datetime.now(timezone.utc) - timedelta(seconds=600)).strftime("%Y-%m-%dT%H:%M:%SZ")
    _atomic_write_json(PAA_DIR / "monitor_heartbeat.json", {"checked_at_utc": stale_hb_ts, "status": "FORCED_STALE_FOR_TEST_6"})

    # Trigger the independent PID-1 system supervisor service (`sudo systemctl start paa-system-supervisor.service`)
    sup_exec = _sh(["sudo", "systemctl", "start", "paa-system-supervisor.service"], timeout=60.0)
    restored_timer_state = _sh(["systemctl", "--user", "is-active", "polymarket-paa-monitor.timer"])["stdout"]
    sup_hb = json.loads((PAA_DIR / "supervisor_heartbeat.json").read_text(encoding="utf-8"))
    fresh_mon_hb = json.loads((PAA_DIR / "monitor_heartbeat.json").read_text(encoding="utf-8"))
    mon_fail_passed = (
        stopped_state != "active"
        and restored_timer_state == "active"
        and sup_hb.get("monitor_failed") is True
        and sup_hb.get("repaired") is True
        and fresh_mon_hb.get("checked_at_utc") != stale_hb_ts
    )
    doc["tests"]["06_monitoring_failure_test"] = {
        "test_number": 6,
        "name": "Monitoring Failure Test",
        "passed": mon_fail_passed,
        "verified_at_utc": utc_now_iso(),
        "monitor_timer_state_after_fault_injection": stopped_state,
        "supervisor_command": sup_exec,
        "supervisor_heartbeat": sup_hb,
        "monitor_timer_state_after_supervisor_repair": restored_timer_state,
        "refreshed_monitor_heartbeat_utc": fresh_mon_hb.get("checked_at_utc"),
    }

    # -------------------------------------------------------------------------
    # TEST 7 & TEST 8: Deployment Test & Automatic Rollback Test (Real Git Worktree + Staging)
    # -------------------------------------------------------------------------
    with tempfile.TemporaryDirectory(prefix="paa_cert_deploy_") as td:
        d_root = Path(td)
        d_db = PAATaskDB(d_root / "deploy.db")
        d_budget = BudgetManager(d_db, autonomy_cfg=cfg)
        d_gate = PermissionGate(autonomy_cfg=cfg, approvals_dir=d_root / "approvals")
        builder = GitWorktreeBuilder(d_db, d_budget, repo_root=PIPELINE_ROOT, worktree_root=d_root / "worktrees", autonomy_cfg=cfg)
        deployer = DeploymentController(
            d_db,
            d_gate,
            repo_root=PIPELINE_ROOT,
            staging_root=d_root / "staging",
            data_dir=d_root / "data",
            autonomy_cfg=cfg,
        )
        try:
            cand_good = builder.build_and_commit_candidate(
                task_id="CERT_DEPLOY_OK",
                commit_message="Cert Test 7: Authorized low-risk canary diagnostic module",
                apply_fn=lambda wt: (wt / "src" / "paa_os" / "cert_canary_probe.py").write_text(
                    '"""Low-risk PAA canary verification probe."""\n\ndef paa_canary_health_check() -> bool:\n    return True\n',
                    encoding="utf-8",
                ),
                pytest_targets=["tests/test_paa_autonomy_os.py"],
            )
            rel_good = deployer.release_candidate(
                candidate=cand_good,
                release_id="REL_CERT_GOOD_07",
                pytest_targets=["tests/test_paa_autonomy_os.py"],
            )
            ptr_after_good = deployer.get_active_staging_pointer()

            cand_faulty = builder.build_and_commit_candidate(
                task_id="CERT_ROLLBACK_BAD",
                commit_message="Cert Test 8: Faulty candidate triggering automatic canary rollback",
                apply_fn=lambda wt: (wt / "src" / "paa_os" / "cert_canary_probe.py").write_text(
                    '"""Faulty canary probe simulating post-release health failure."""\n\ndef paa_canary_health_check() -> bool:\n    return False\n',
                    encoding="utf-8",
                ),
            )
            rel_bad = deployer.release_candidate(
                candidate=cand_faulty,
                release_id="REL_CERT_FAULTY_08",
            )
            ptr_after_rollback = deployer.get_active_staging_pointer()
        finally:
            git_exe = _find_git_exe()
            subprocess.run([git_exe, "branch", "-D", "paa/CERT_DEPLOY_OK"], cwd=str(PIPELINE_ROOT), capture_output=True)
            subprocess.run([git_exe, "branch", "-D", "paa/CERT_ROLLBACK_BAD"], cwd=str(PIPELINE_ROOT), capture_output=True)

        deploy_passed = (
            rel_good["state"] == "DEPLOYED_VERIFIED"
            and rel_good["qa_passed"] is True
            and ptr_after_good is not None
            and ptr_after_good["active_release_id"] == "REL_CERT_GOOD_07"
        )
        rollback_passed = (
            rel_bad["state"] == "ROLLED_BACK"
            and rel_bad["rolled_back"] is True
            and ptr_after_rollback is not None
            and ptr_after_rollback["active_release_id"] == "REL_CERT_GOOD_07"
            and rel_bad["evidence"]["post_rollback_health_verified"] is True
        )
        doc["tests"]["07_deployment_test"] = {
            "test_number": 7,
            "name": "Deployment Test",
            "passed": deploy_passed,
            "verified_at_utc": utc_now_iso(),
            "release_record": rel_good,
            "active_staging_pointer": ptr_after_good,
        }
        doc["tests"]["08_rollback_test"] = {
            "test_number": 8,
            "name": "Rollback Test",
            "passed": rollback_passed,
            "verified_at_utc": utc_now_iso(),
            "failed_release_record": rel_bad,
            "restored_staging_pointer": ptr_after_rollback,
        }

    # -------------------------------------------------------------------------
    # TEST 9: Financial Integrity Test (Controlled Accounting Discrepancy Safeguard + Live Reconciliation)
    # -------------------------------------------------------------------------
    with tempfile.TemporaryDirectory(prefix="paa_cert_fin_") as td:
        f_data = Path(td) / "data"
        f_data.mkdir(parents=True)
        f_db = PAATaskDB(f_data / "paa" / "fin.db")
        f_budget = BudgetManager(f_db, autonomy_cfg=cfg)
        f_acc = PAAAccountant(f_db, f_budget, data_dir=f_data, autonomy_cfg=cfg)
        injected_snap = f_acc.measure_and_record(
            live_rpc_check=False,
            ledger_override={
                "free_cash_pusd": 21.68,
                "open_cost_basis_usd": 43.29,
                "portfolio_nav_mark_to_bid_usd": 64.97,
                "portfolio_nav_at_resting_maker_usd": 64.97,
                "verified_realized_net_profit_usd": -68.23,
                "raw_state_ledger_realized_pnl_usd": -80.13,
                "non_cash_unfilled_artifact_adjustment_usd": 11.90,
                "total_realized_fees_paid_usd": 4.12,
                "open_positions": [
                    {"trade_id": "SIM_DISCREPANCY_POS", "shares_ledger": 28.0, "shares_onchain": 0.0, "best_bid": 0.75}
                ],
            },
            state_override={"live_bankroll": 36.18},
        )
        safeguard_engaged = (f_data / "paa" / "ACCOUNTING_SAFEGUARD_ACTIVE.json").exists()
        queued_p0 = f_db.list_tasks(states=("READY",))

        live_auth_ledger = reconcile_authoritative_ledger(live_rpc_check=True)
        live_snap = PAAAccountant(
            f_db,
            f_budget,
            data_dir=PIPELINE_ROOT / "data" / "polymarket",
            autonomy_cfg=cfg,
        ).verify_accounting_integrity(live_auth_ledger)
        fin_integrity_passed = (
            injected_snap["accounting_ok"] is False
            and safeguard_engaged is True
            and any(t["category"] == "SAFETY_ACCOUNTING" and t["priority_label"] == "P0" for t in queued_p0)
            and live_snap[0] is True
        )
        doc["tests"]["09_financial_integrity_test"] = {
            "test_number": 9,
            "name": "Financial Integrity Test",
            "passed": fin_integrity_passed,
            "verified_at_utc": utc_now_iso(),
            "injected_discrepancy_usd": injected_snap["accounting_discrepancy_usd"],
            "injected_anomalies": injected_snap["details"]["anomalies"],
            "safeguard_file_created": safeguard_engaged,
            "p0_safety_task_enqueued": queued_p0[0]["task_id"] if queued_p0 else None,
            "live_production_reconciliation_ok": live_snap[0],
            "live_free_cash_pusd": live_auth_ledger.get("free_cash_pusd"),
        }

    # -------------------------------------------------------------------------
    # TEST 10: Permission Test (Out-of-Scope File, Risk Floor, Live Activation & Secret Stripping)
    # -------------------------------------------------------------------------
    with tempfile.TemporaryDirectory(prefix="paa_cert_perm_") as td:
        p_root = Path(td)
        p_db = PAATaskDB(p_root / "perm.db")
        p_budget = BudgetManager(p_db, autonomy_cfg=cfg)
        p_gate = PermissionGate(autonomy_cfg=cfg, approvals_dir=p_root / "approvals")

        ok_f, v_f = p_gate.inspect_candidate_diff([".env", "src/paa_os/permissions.py"], "+POLYGON_PRIVATE_KEY=leak")
        weak_cfg = copy.deepcopy(DEFAULT_HOLISTIC_CONFIG)
        weak_cfg["risk_controller"]["hard_ruin_floor_usd"] = 20.0
        weak_cfg["risk_controller"]["max_daily_directional_loss_usd"] = 100.0
        ok_r, v_r = p_gate.inspect_candidate_diff(
            ["config/polymarket_strategy_and_risk.json"],
            "",
            baseline_cfg=DEFAULT_HOLISTIC_CONFIG,
            candidate_cfg=weak_cfg,
        )
        ok_live, msg_live = p_gate.check_task_authorization(
            {
                "task_id": "T_UNAUTH_LIVE",
                "required_permission_class": PermissionClass.AUTOMATICALLY_PERMITTED.value,
                "required_scopes": ["NEW_LIVE_TRADING_ACTIVATION"],
            }
        )
        runner = HeadlessAgentRunner(p_db, p_budget, autonomy_cfg=cfg, live_repo_root=PIPELINE_ROOT)
        direct_live_blocked = False
        try:
            runner.invoke(prompt="Edit live repo", task_id="T_DIRECT", cwd=PIPELINE_ROOT, mode="auto", allow_worktree_edits=True)
        except PermissionDeniedError:
            direct_live_blocked = True

        os.environ["TEMP_TEST_PRIVATE_KEY_CHECK"] = "should_not_matter"
        stripped_env = build_isolated_worker_env(role="CERT_CHECK", autonomy_cfg=cfg)
        secrets_absent = all(k not in stripped_env for k in ("POLYGON_PRIVATE_KEY", "POLY_API_SECRET", "BUILDER_PRIVATE_KEY"))

        perm_passed = (not ok_f) and (not ok_r) and (not ok_live) and direct_live_blocked and secrets_absent
        doc["tests"]["10_permission_test"] = {
            "test_number": 10,
            "name": "Permission Test",
            "passed": perm_passed,
            "verified_at_utc": utc_now_iso(),
            "protected_file_violations": v_f,
            "risk_envelope_violations": v_r,
            "unapproved_live_activation_block": msg_live,
            "direct_live_repo_agent_write_blocked": direct_live_blocked,
            "wallet_secrets_stripped_from_worker_env": secrets_absent,
        }

    # -------------------------------------------------------------------------
    # TEST 11: Research Continuity Test (Live ~19,000+ Polymarket Scan + Accepted & Rejected Hypotheses)
    # -------------------------------------------------------------------------
    prod_budget = BudgetManager(prod_db, autonomy_cfg=cfg)
    prod_researcher = PAAResearcher(prod_db, prod_budget, autonomy_cfg=cfg)
    res_summary = prod_researcher.run_research_cycle(max_events=800)
    stored_findings = prod_db.list_research_findings(limit=30)
    has_accepted_or_eval = len(stored_findings) >= 4
    has_rejected = any(not f["succeeded"] for f in stored_findings)
    res_cont_passed = (
        res_summary["active_markets_scanned"] >= 5000
        and has_accepted_or_eval
        and has_rejected
    )
    doc["tests"]["11_research_continuity_test"] = {
        "test_number": 11,
        "name": "Research Continuity Test",
        "passed": res_cont_passed,
        "verified_at_utc": utc_now_iso(),
        "live_scan_summary": res_summary,
        "stored_findings_count": len(stored_findings),
        "sample_accepted_findings": [f["finding_id"] for f in stored_findings if f["succeeded"]][:5],
        "sample_rejected_findings": [f["finding_id"] for f in stored_findings if not f["succeeded"]][:5],
    }

    # -------------------------------------------------------------------------
    # TEST 12: Profitability Test (Strict Separation of Realized Wallet Cash vs Artifacts vs Simulated)
    # -------------------------------------------------------------------------
    prod_director = PAADirector()
    live_fin_snap = prod_director.accountant.measure_and_record(live_rpc_check=True)
    dash = prod_director.generate_dashboard_and_report()
    vf = dash["verified_financial_performance"]
    prof_passed = (
        vf["simulated_non_cash_benchmarks"]["is_real_money"] is False
        and vf["free_cash_pusd"] > 0
        and abs(
            (vf["raw_state_ledger_pnl_usd"] + vf["non_cash_unfilled_artifact_adj_usd"])
            - vf["realized_onchain_net_pnl_usd"]
        ) < 0.05
        and "research_ai_cost_usd" in vf
        and "daily_infra_vm_cost_usd" in vf
    )
    doc["tests"]["12_profitability_test"] = {
        "test_number": 12,
        "name": "Profitability Test",
        "passed": prof_passed,
        "verified_at_utc": utc_now_iso(),
        "verified_financial_performance": vf,
        "live_accounting_ok": live_fin_snap["accounting_ok"],
    }

    _save_evidence(doc)
    summary_flags = {k: v["passed"] for k, v in sorted(doc["tests"].items())}
    print(json.dumps({"summary": summary_flags}, indent=2))
    if not all(v for k, v in summary_flags.items() if k != "01_reboot_test"):
        raise SystemExit(1)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--record-reboot-pre", action="store_true")
    p.add_argument("--record-reboot-post", action="store_true")
    p.add_argument("--run-tests-2-to-12", action="store_true")
    args = p.parse_args()
    if args.record_reboot_pre:
        record_reboot_pre()
    elif args.record_reboot_post:
        record_reboot_post()
    elif args.run_tests_2_to_12:
        run_tests_2_to_12()
    else:
        p.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
