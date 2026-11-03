"""
Durable SQLite WAL Task Queue, Checkpoints, Execution Locks & Persistent Registries (`src/paa_os/task_db.py`).

Implements PAA Section 4.A.2 (Durable Task Management) & Section 4.D (Anti-Stall Mechanism):
  - ACID SQLite WAL storage surviving process crashes and VM reboots.
  - All 12 mandatory task fields:
      1. `task_id` (unique identifier + `dedupe_key` active uniqueness)
      2. `category` & `priority_label` / `priority_rank` / `ev_priority_score`
      3. `financial_impact_hypothesis` (+ `expected_net_ev_usd_per_day`)
      4. `evidence_json`
      5. `required_permission_class` & `required_scopes_json`
      6. `execution_state`
      7. `attempts` & `max_retries` (+ `next_eligible_at_utc` exponential backoff)
      8. `dependencies_json` (+ DFS dependency-loop detector)
      9. `last_checkpoint_json` (+ `completed_steps` idempotency guard)
     10. `validation_requirements_json`
     11. `completion_evidence_json`
     12. `next_action`
  - Safe interrupted-task recovery (`recover_interrupted_tasks`) & stalled-worker detection.
  - Atomic execution locks (`director_cycle`, `production_deploy`, `engineering_slot_0`) with dead-PID reclamation.
"""

from __future__ import annotations

import json
import os
import signal
import socket
import sqlite3
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple

PIPELINE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PAA_DIR = PIPELINE_ROOT / "data" / "polymarket" / "paa"
DEFAULT_DB_PATH = DEFAULT_PAA_DIR / "paa_tasks.db"

ACTIVE_TASK_STATES = (
    "PENDING",
    "READY",
    "CLAIMED",
    "RUNNING",
    "PENDING_VERIFICATION",
    "CHECKPOINTED",
    "BLOCKED_DEPENDENCY",
    "VALIDATING",
)
TERMINAL_TASK_STATES = (
    "VERIFIED_COMPLETE",
    "COMPLETED",
    "FAILED",
    "FAILED_PERMANENT",
    "BLOCKED",
    "BLOCKED_AUTHORIZATION",
    "REJECTED",
    "CANCELLED",
)
VERIFICATION_CONTROLLER_SEAL = "PAA_DETERMINISTIC_VERIFICATION_CONTROLLER_V2"
PRIORITY_MAP = {
    "P0": 100,
    "P1": 80,
    "P2": 60,
    "P3": 40,
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    return utc_now().isoformat()


def utc_offset_iso(seconds: float) -> str:
    return (utc_now() + timedelta(seconds=float(seconds))).isoformat()


def parse_iso(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def is_pid_alive(pid: Optional[int], expected_host: Optional[str] = None) -> bool:
    """Checks whether a local worker PID is alive (and not a zombie)."""
    if not pid or int(pid) <= 0:
        return False
    if expected_host and expected_host != socket.gethostname():
        # Cross-host leases rely on lease_expires_utc
        return True
    p = int(pid)
    if os.name == "nt":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            SYNCHRONIZE = 0x00100000
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = kernel32.OpenProcess(SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION, False, p)
            if not handle:
                return False
            exit_code = ctypes.c_ulong()
            ok = kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
            kernel32.CloseHandle(handle)
            return bool(ok and exit_code.value == 259)  # STILL_ACTIVE == 259
        except Exception:
            return False
    try:
        os.kill(p, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    stat_path = Path(f"/proc/{p}/stat")
    if stat_path.exists():
        try:
            st_char = stat_path.read_text(encoding="utf-8", errors="ignore").rsplit(")", 1)[1].split()[0]
            if st_char == "Z":
                return False
        except Exception:
            pass
    return True


class PAATaskDB:
    """Thread-safe, multi-process-safe SQLite WAL database for PAA Autonomous OS."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.hostname = socket.gethostname()
        self._init_schema()

    @contextmanager
    def _connect(self, immediate: bool = False) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(str(self.db_path), timeout=15.0, isolation_level=None)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA busy_timeout=10000;")
            conn.execute("PRAGMA foreign_keys=ON;")
            if immediate:
                conn.execute("BEGIN IMMEDIATE;")
            else:
                conn.execute("BEGIN;")
            try:
                yield conn
                if conn.in_transaction:
                    conn.execute("COMMIT;")
            except Exception:
                if conn.in_transaction:
                    conn.execute("ROLLBACK;")
                raise
        finally:
            conn.close()

    def check_integrity(self) -> Tuple[bool, str]:
        """Anti-stall database corruption detector (`PRAGMA integrity_check`)."""
        if not self.db_path.exists():
            return False, "DB_FILE_MISSING"
        try:
            conn = sqlite3.connect(str(self.db_path), timeout=5.0)
            try:
                row = conn.execute("PRAGMA integrity_check;").fetchone()
                msg = str(row[0]) if row else "EMPTY"
                return (msg.lower() == "ok"), msg
            finally:
                conn.close()
        except Exception as exc:
            return False, f"SQLITE_ERROR:{exc}"

    def _init_schema(self) -> None:
        with self._connect(immediate=True) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS paa_tasks (
                    task_id TEXT PRIMARY KEY,
                    dedupe_key TEXT NOT NULL,
                    category TEXT NOT NULL,
                    priority_label TEXT NOT NULL DEFAULT 'P2',
                    priority_rank INTEGER NOT NULL DEFAULT 60,
                    ev_priority_score REAL NOT NULL DEFAULT 0.0,
                    expected_net_ev_usd_per_day REAL NOT NULL DEFAULT 0.0,
                    title TEXT NOT NULL,
                    financial_impact_hypothesis TEXT NOT NULL,
                    evidence_json TEXT NOT NULL DEFAULT '{}',
                    required_permission_class TEXT NOT NULL DEFAULT 'AUTOMATICALLY_PERMITTED',
                    required_scopes_json TEXT NOT NULL DEFAULT '[]',
                    execution_state TEXT NOT NULL DEFAULT 'READY',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    max_retries INTEGER NOT NULL DEFAULT 3,
                    next_eligible_at_utc TEXT,
                    dependencies_json TEXT NOT NULL DEFAULT '[]',
                    last_checkpoint_json TEXT NOT NULL DEFAULT '{}',
                    validation_requirements_json TEXT NOT NULL DEFAULT '{}',
                    completion_evidence_json TEXT NOT NULL DEFAULT '{}',
                    next_action TEXT NOT NULL DEFAULT '',
                    payload_json TEXT NOT NULL DEFAULT '{}',
                    worker_pid INTEGER,
                    worker_host TEXT,
                    lease_expires_utc TEXT,
                    last_heartbeat_utc TEXT,
                    last_progress_utc TEXT,
                    last_error TEXT DEFAULT '',
                    created_at_utc TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL,
                    completed_at_utc TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_paa_tasks_state_prio
                    ON paa_tasks(execution_state, priority_rank DESC, ev_priority_score DESC, created_at_utc ASC);

                CREATE INDEX IF NOT EXISTS idx_paa_tasks_dedupe
                    ON paa_tasks(dedupe_key, execution_state);

                CREATE TABLE IF NOT EXISTS execution_locks (
                    lock_name TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL,
                    owner_pid INTEGER NOT NULL,
                    owner_host TEXT NOT NULL,
                    acquired_at_utc TEXT NOT NULL,
                    heartbeat_utc TEXT NOT NULL,
                    expires_at_utc TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS task_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp_utc TEXT NOT NULL,
                    task_id TEXT,
                    component TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    details_json TEXT NOT NULL DEFAULT '{}'
                );

                CREATE INDEX IF NOT EXISTS idx_task_events_ts ON task_events(timestamp_utc DESC);
                CREATE INDEX IF NOT EXISTS idx_task_events_task ON task_events(task_id, event_id ASC);

                CREATE TABLE IF NOT EXISTS research_findings (
                    finding_id TEXT PRIMARY KEY,
                    created_at_utc TEXT NOT NULL,
                    category TEXT NOT NULL,
                    hypothesis TEXT NOT NULL,
                    validation_method TEXT NOT NULL,
                    sample_size INTEGER NOT NULL DEFAULT 0,
                    expected_net_ev_usd_per_day REAL NOT NULL DEFAULT 0.0,
                    metrics_json TEXT NOT NULL DEFAULT '{}',
                    succeeded INTEGER NOT NULL DEFAULT 0,
                    verdict TEXT NOT NULL,
                    notes TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS deployments (
                    release_id TEXT PRIMARY KEY,
                    created_at_utc TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL,
                    task_id TEXT,
                    git_branch TEXT NOT NULL,
                    candidate_sha TEXT NOT NULL,
                    baseline_sha TEXT NOT NULL,
                    permission_class TEXT NOT NULL,
                    target_env TEXT NOT NULL DEFAULT 'staging',
                    state TEXT NOT NULL,
                    qa_passed INTEGER NOT NULL DEFAULT 0,
                    invariants_passed INTEGER NOT NULL DEFAULT 0,
                    perf_passed INTEGER NOT NULL DEFAULT 0,
                    canary_passed INTEGER NOT NULL DEFAULT 0,
                    rolled_back INTEGER NOT NULL DEFAULT 0,
                    rollback_reason TEXT DEFAULT '',
                    evidence_json TEXT NOT NULL DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS financial_snapshots (
                    snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recorded_at_utc TEXT NOT NULL,
                    free_cash_pusd REAL NOT NULL,
                    open_cost_basis_usd REAL NOT NULL,
                    nav_mark_to_bid_usd REAL NOT NULL,
                    nav_resting_maker_usd REAL NOT NULL,
                    verified_realized_net_pnl_usd REAL NOT NULL,
                    raw_ledger_pnl_usd REAL NOT NULL,
                    phantom_adjustment_usd REAL NOT NULL,
                    unrealized_pnl_bid_usd REAL NOT NULL,
                    unrealized_pnl_maker_usd REAL NOT NULL,
                    realized_fees_usd REAL NOT NULL,
                    estimated_slippage_usd REAL NOT NULL,
                    drawdown_from_hwm_usd REAL NOT NULL,
                    capital_utilization_pct REAL NOT NULL,
                    execution_reliability_pct REAL NOT NULL,
                    opportunity_capture_pct REAL NOT NULL,
                    research_ai_cost_usd REAL NOT NULL,
                    infra_cost_usd REAL NOT NULL,
                    net_economic_profit_usd REAL NOT NULL,
                    accounting_discrepancy_usd REAL NOT NULL,
                    accounting_ok INTEGER NOT NULL DEFAULT 1,
                    simulated_shadow_t1000_pnl_usd REAL NOT NULL DEFAULT 0.0,
                    simulated_paper_oos_pnl_usd REAL NOT NULL DEFAULT 0.0,
                    details_json TEXT NOT NULL DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS budget_ledger (
                    entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recorded_at_utc TEXT NOT NULL,
                    date_utc TEXT NOT NULL,
                    hour_utc TEXT NOT NULL,
                    cost_type TEXT NOT NULL,
                    model_name TEXT DEFAULT '',
                    task_id TEXT DEFAULT '',
                    input_tokens INTEGER NOT NULL DEFAULT 0,
                    output_tokens INTEGER NOT NULL DEFAULT 0,
                    duration_sec REAL NOT NULL DEFAULT 0.0,
                    estimated_cost_usd REAL NOT NULL DEFAULT 0.0,
                    details_json TEXT NOT NULL DEFAULT '{}'
                );

                CREATE INDEX IF NOT EXISTS idx_budget_date ON budget_ledger(date_utc, cost_type);

                CREATE TABLE IF NOT EXISTS heartbeats (
                    component TEXT PRIMARY KEY,
                    last_seen_utc TEXT NOT NULL,
                    pid INTEGER,
                    host TEXT,
                    status TEXT NOT NULL,
                    cycle_count INTEGER NOT NULL DEFAULT 0,
                    details_json TEXT NOT NULL DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS verified_facts (
                    fact_key TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    value_json TEXT NOT NULL,
                    epistemic_status TEXT NOT NULL DEFAULT 'VERIFIED_FACT',
                    source_type TEXT NOT NULL,
                    source_ref TEXT NOT NULL,
                    observed_at_utc TEXT NOT NULL,
                    verified_by TEXT NOT NULL,
                    ttl_sec REAL NOT NULL DEFAULT 300.0,
                    expires_at_utc TEXT NOT NULL,
                    revalidation_rule TEXT NOT NULL DEFAULT 'REQUERY_AUTHORITATIVE_SOURCE',
                    contradicted_reason TEXT NOT NULL DEFAULT ''
                );

                CREATE INDEX IF NOT EXISTS idx_verified_facts_cat
                    ON verified_facts(category, epistemic_status);

                CREATE TABLE IF NOT EXISTS session_runs (
                    session_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    stage_role TEXT NOT NULL,
                    conversation_id TEXT,
                    fresh_session INTEGER NOT NULL DEFAULT 1,
                    model_name TEXT NOT NULL DEFAULT '',
                    prompt_chars INTEGER NOT NULL DEFAULT 0,
                    est_prompt_tokens INTEGER NOT NULL DEFAULT 0,
                    actual_input_tokens INTEGER NOT NULL DEFAULT 0,
                    output_tokens INTEGER NOT NULL DEFAULT 0,
                    context_budget_tokens INTEGER NOT NULL DEFAULT 16000,
                    context_utilization_pct REAL NOT NULL DEFAULT 0.0,
                    checkpoint_triggered INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL,
                    details_json TEXT NOT NULL DEFAULT '{}'
                );

                CREATE INDEX IF NOT EXISTS idx_session_runs_task
                    ON session_runs(task_id, created_at_utc DESC);
                """
            )
            # Safe idempotent schema migrations for existing SQLite databases
            existing_task_cols = {
                r["name"] for r in conn.execute("PRAGMA table_info(paa_tasks)").fetchall()
            }
            for col_name, col_ddl in (
                ("worker_submission_json", "TEXT NOT NULL DEFAULT '{}'"),
                ("verification_receipt_json", "TEXT NOT NULL DEFAULT '{}'"),
                ("epistemic_status", "TEXT NOT NULL DEFAULT 'UNKNOWN'"),
                ("session_count", "INTEGER NOT NULL DEFAULT 0"),
            ):
                if col_name not in existing_task_cols:
                    conn.execute(f"ALTER TABLE paa_tasks ADD COLUMN {col_name} {col_ddl}")

            existing_rf_cols = {
                r["name"] for r in conn.execute("PRAGMA table_info(research_findings)").fetchall()
            }
            for col_name, col_ddl in (
                ("evidence_stage", "TEXT NOT NULL DEFAULT 'HYPOTHESIS'"),
                ("epistemic_status", "TEXT NOT NULL DEFAULT 'HYPOTHESIS'"),
            ):
                if col_name not in existing_rf_cols:
                    conn.execute(f"ALTER TABLE research_findings ADD COLUMN {col_name} {col_ddl}")

    def _row_to_task(self, row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        for jkey, out_key in (
            ("evidence_json", "evidence"),
            ("required_scopes_json", "required_scopes"),
            ("dependencies_json", "dependencies"),
            ("last_checkpoint_json", "last_checkpoint"),
            ("validation_requirements_json", "validation_requirements"),
            ("completion_evidence_json", "completion_evidence"),
            ("worker_submission_json", "worker_submission"),
            ("verification_receipt_json", "verification_receipt"),
            ("payload_json", "payload"),
        ):
            raw = d.get(jkey)
            try:
                d[out_key] = json.loads(raw) if raw else ({} if "scopes" not in jkey and "dependencies" not in jkey else [])
            except Exception:
                d[out_key] = {} if "scopes" not in jkey and "dependencies" not in jkey else []
        d["state"] = d.get("execution_state")
        return d

    def log_event(
        self,
        component: str,
        event_type: str,
        details: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
    ) -> None:
        with self._connect(immediate=True) as conn:
            conn.execute(
                "INSERT INTO task_events(timestamp_utc, task_id, component, event_type, details_json) VALUES (?, ?, ?, ?, ?)",
                (utc_now_iso(), task_id, component, event_type, json.dumps(details or {}, default=str)),
            )

    def record_heartbeat(
        self,
        component: str,
        status: str = "OK",
        details: Optional[Dict[str, Any]] = None,
        increment_cycle: bool = True,
    ) -> Dict[str, Any]:
        now_s = utc_now_iso()
        pid = os.getpid()
        with self._connect(immediate=True) as conn:
            cur = conn.execute("SELECT cycle_count FROM heartbeats WHERE component = ?", (component,)).fetchone()
            cyc = (int(cur["cycle_count"]) + (1 if increment_cycle else 0)) if cur else (1 if increment_cycle else 0)
            conn.execute(
                """
                INSERT INTO heartbeats(component, last_seen_utc, pid, host, status, cycle_count, details_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(component) DO UPDATE SET
                    last_seen_utc = excluded.last_seen_utc,
                    pid = excluded.pid,
                    host = excluded.host,
                    status = excluded.status,
                    cycle_count = excluded.cycle_count,
                    details_json = excluded.details_json
                """,
                (component, now_s, pid, self.hostname, status, cyc, json.dumps(details or {}, default=str)),
            )
        return {"component": component, "last_seen_utc": now_s, "pid": pid, "status": status, "cycle_count": cyc}

    def get_heartbeats(self) -> Dict[str, Dict[str, Any]]:
        now = utc_now()
        out: Dict[str, Dict[str, Any]] = {}
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM heartbeats").fetchall()
        for r in rows:
            d = dict(r)
            dt = parse_iso(d.get("last_seen_utc"))
            d["age_sec"] = round((now - dt).total_seconds(), 2) if dt else None
            try:
                d["details"] = json.loads(d.get("details_json") or "{}")
            except Exception:
                d["details"] = {}
            out[d["component"]] = d
        return out

    def acquire_lock(self, lock_name: str, ttl_sec: float = 300.0, owner_id: Optional[str] = None) -> Optional[str]:
        """
        Acquires a named execution lock atomically.
        Automatically reclaims locks whose TTL expired OR whose local owner PID exited.
        """
        oid = owner_id or f"{self.hostname}:{os.getpid()}:{uuid.uuid4().hex[:8]}"
        now = utc_now()
        now_s = now.isoformat()
        exp_s = (now + timedelta(seconds=max(5.0, float(ttl_sec)))).isoformat()
        with self._connect(immediate=True) as conn:
            existing = conn.execute("SELECT * FROM execution_locks WHERE lock_name = ?", (lock_name,)).fetchone()
            if existing is not None:
                exp_dt = parse_iso(existing["expires_at_utc"])
                expired = exp_dt is not None and exp_dt <= now
                dead_local_pid = (
                    existing["owner_host"] == self.hostname
                    and existing["owner_pid"] != os.getpid()
                    and not is_pid_alive(existing["owner_pid"], existing["owner_host"])
                )
                if not expired and not dead_local_pid and existing["owner_id"] != oid:
                    return None
                conn.execute("DELETE FROM execution_locks WHERE lock_name = ?", (lock_name,))
                if expired or dead_local_pid:
                    conn.execute(
                        "INSERT INTO task_events(timestamp_utc, task_id, component, event_type, details_json) VALUES (?, NULL, ?, ?, ?)",
                        (
                            now_s,
                            "lock_manager",
                            "RECLAIMED_STALE_LOCK",
                            json.dumps(
                                {
                                    "lock_name": lock_name,
                                    "prev_owner": existing["owner_id"],
                                    "prev_pid": existing["owner_pid"],
                                    "expired": expired,
                                    "dead_local_pid": dead_local_pid,
                                }
                            ),
                        ),
                    )
            conn.execute(
                """
                INSERT INTO execution_locks(lock_name, owner_id, owner_pid, owner_host, acquired_at_utc, heartbeat_utc, expires_at_utc)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (lock_name, oid, os.getpid(), self.hostname, now_s, now_s, exp_s),
            )
        return oid

    def renew_lock(self, lock_name: str, owner_id: str, ttl_sec: float = 300.0) -> bool:
        now = utc_now()
        exp_s = (now + timedelta(seconds=max(5.0, float(ttl_sec)))).isoformat()
        with self._connect(immediate=True) as conn:
            cur = conn.execute(
                "UPDATE execution_locks SET heartbeat_utc = ?, expires_at_utc = ? WHERE lock_name = ? AND owner_id = ?",
                (now.isoformat(), exp_s, lock_name, owner_id),
            )
            return cur.rowcount > 0

    def release_lock(self, lock_name: str, owner_id: str) -> bool:
        with self._connect(immediate=True) as conn:
            cur = conn.execute(
                "DELETE FROM execution_locks WHERE lock_name = ? AND owner_id = ?",
                (lock_name, owner_id),
            )
            return cur.rowcount > 0

    def has_dedupe_key(self, dedupe_key: str, *, include_completed: bool = True) -> bool:
        """Checks whether a task with `dedupe_key` already exists (including completed same-hour buckets when `include_completed=True`)."""
        dkey = str(dedupe_key or "").strip()[:180]
        if not dkey:
            return False
        with self._connect(immediate=False) as conn:
            if include_completed:
                row = conn.execute(
                    "SELECT 1 FROM paa_tasks WHERE dedupe_key = ? LIMIT 1",
                    (dkey,),
                ).fetchone()
            else:
                placeholders = ",".join("?" for _ in ACTIVE_TASK_STATES + ("BLOCKED_AUTHORIZATION",))
                row = conn.execute(
                    f"SELECT 1 FROM paa_tasks WHERE dedupe_key = ? AND execution_state IN ({placeholders}) LIMIT 1",
                    (dkey, *ACTIVE_TASK_STATES, "BLOCKED_AUTHORIZATION"),
                ).fetchone()
            return row is not None

    def enqueue_task(
        self,
        *,
        category: str,
        title: str,
        financial_impact_hypothesis: str = "Autonomous PAA optimization task",
        priority_label: str = "P2",
        expected_net_ev_usd_per_day: float = 0.0,
        dedupe_key: Optional[str] = None,
        task_id: Optional[str] = None,
        evidence: Optional[Dict[str, Any]] = None,
        required_permission_class: str = "AUTOMATICALLY_PERMITTED",
        required_scopes: Optional[List[str]] = None,
        dependencies: Optional[List[str]] = None,
        validation_requirements: Optional[Dict[str, Any]] = None,
        next_action: str = "EXECUTE_INITIAL_STEP",
        payload: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
        initial_state_override: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], bool]:
        """
        Inserts a durable task or deduplicates against an existing active task with the same `dedupe_key`.
        Returns `(task_dict, created_new)`.
        """
        prio_lbl = priority_label.upper() if priority_label.upper() in PRIORITY_MAP else "P2"
        prio_rank = PRIORITY_MAP[prio_lbl]
        ev_val = float(expected_net_ev_usd_per_day or 0.0)
        ev_score = round(prio_rank * 10.0 + max(-50.0, min(500.0, ev_val * 25.0)), 4)
        dkey = (dedupe_key or f"{category}:{title}").strip()[:180]
        deps = list(dependencies or [])
        now_s = utc_now_iso()

        with self._connect(immediate=True) as conn:
            placeholders = ",".join("?" for _ in ACTIVE_TASK_STATES + ("BLOCKED_AUTHORIZATION",))
            existing = conn.execute(
                f"SELECT * FROM paa_tasks WHERE dedupe_key = ? AND execution_state IN ({placeholders}) ORDER BY created_at_utc DESC LIMIT 1",
                (dkey, *ACTIVE_TASK_STATES, "BLOCKED_AUTHORIZATION"),
            ).fetchone()
            if existing is not None:
                # Upgrade priority/EV if higher, without creating duplicate work
                if prio_rank > int(existing["priority_rank"]) or ev_score > float(existing["ev_priority_score"]):
                    conn.execute(
                        """
                        UPDATE paa_tasks
                        SET priority_label = ?, priority_rank = ?, ev_priority_score = ?, expected_net_ev_usd_per_day = ?,
                            evidence_json = ?, updated_at_utc = ?
                        WHERE task_id = ?
                        """,
                        (
                            prio_lbl,
                            max(prio_rank, int(existing["priority_rank"])),
                            max(ev_score, float(existing["ev_priority_score"])),
                            max(ev_val, float(existing["expected_net_ev_usd_per_day"])),
                            json.dumps(evidence or {}, default=str),
                            now_s,
                            existing["task_id"],
                        ),
                    )
                    existing = conn.execute("SELECT * FROM paa_tasks WHERE task_id = ?", (existing["task_id"],)).fetchone()
                return self._row_to_task(existing), False

            # Check if dependencies are already completed / verified
            initial_state = initial_state_override if initial_state_override in ("PENDING", "READY") else "READY"
            if deps:
                dep_ph = ",".join("?" for _ in deps)
                done_cnt = conn.execute(
                    f"SELECT COUNT(*) AS c FROM paa_tasks WHERE task_id IN ({dep_ph}) AND execution_state IN ('COMPLETED', 'VERIFIED_COMPLETE')",
                    tuple(deps),
                ).fetchone()["c"]
                if int(done_cnt) < len(set(deps)):
                    initial_state = "BLOCKED_DEPENDENCY"

            tid = task_id or f"PAA_{category[:10]}_{int(time.time())}_{uuid.uuid4().hex[:6].upper()}"
            conn.execute(
                """
                INSERT INTO paa_tasks(
                    task_id, dedupe_key, category, priority_label, priority_rank, ev_priority_score,
                    expected_net_ev_usd_per_day, title, financial_impact_hypothesis, evidence_json,
                    required_permission_class, required_scopes_json, execution_state, attempts, max_retries,
                    next_eligible_at_utc, dependencies_json, last_checkpoint_json, validation_requirements_json,
                    completion_evidence_json, next_action, payload_json, created_at_utc, updated_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, '{}', ?, '{}', ?, ?, ?, ?)
                """,
                (
                    tid,
                    dkey,
                    category,
                    prio_lbl,
                    prio_rank,
                    ev_score,
                    ev_val,
                    title,
                    financial_impact_hypothesis,
                    json.dumps(evidence or {}, default=str),
                    required_permission_class,
                    json.dumps(required_scopes or []),
                    initial_state,
                    int(max_retries),
                    now_s,
                    json.dumps(deps),
                    json.dumps(validation_requirements or {}, default=str),
                    next_action,
                    json.dumps(payload or {}, default=str),
                    now_s,
                    now_s,
                ),
            )
            conn.execute(
                "INSERT INTO task_events(timestamp_utc, task_id, component, event_type, details_json) VALUES (?, ?, ?, ?, ?)",
                (
                    now_s,
                    tid,
                    "task_db",
                    "TASK_ENQUEUED",
                    json.dumps({"category": category, "priority": prio_lbl, "state": initial_state, "dedupe_key": dkey}),
                ),
            )
            created = conn.execute("SELECT * FROM paa_tasks WHERE task_id = ?", (tid,)).fetchone()
            return self._row_to_task(created), True

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM paa_tasks WHERE task_id = ?", (task_id,)).fetchone()
            return self._row_to_task(row) if row else None

    def list_tasks(
        self,
        states: Optional[Tuple[str, ...]] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            if states:
                ph = ",".join("?" for _ in states)
                rows = conn.execute(
                    f"""
                    SELECT * FROM paa_tasks
                    WHERE execution_state IN ({ph})
                    ORDER BY priority_rank DESC, ev_priority_score DESC, created_at_utc ASC
                    LIMIT ?
                    """,
                    (*states, int(limit)),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM paa_tasks ORDER BY updated_at_utc DESC LIMIT ?",
                    (int(limit),),
                ).fetchall()
        return [self._row_to_task(r) for r in rows]

    def resolve_dependencies_and_detect_cycles(self) -> Dict[str, List[str]]:
        """
        1. Detects dependency loops among non-terminal tasks (DFS cycle check) and transitions loops to `ESCALATED`.
        2. Promotes `BLOCKED_DEPENDENCY` tasks to `READY` once all dependencies are `COMPLETED`.
        3. Escalates `BLOCKED_DEPENDENCY` tasks if any upstream dependency failed permanently or escalated.
        """
        unblocked: List[str] = []
        cycles: List[str] = []
        upstream_failed: List[str] = []
        now_s = utc_now_iso()

        with self._connect(immediate=True) as conn:
            all_rows = conn.execute("SELECT task_id, execution_state, dependencies_json FROM paa_tasks").fetchall()
            state_map: Dict[str, str] = {}
            dep_map: Dict[str, List[str]] = {}
            for r in all_rows:
                tid = r["task_id"]
                state_map[tid] = r["execution_state"]
                try:
                    dep_map[tid] = list(json.loads(r["dependencies_json"] or "[]"))
                except Exception:
                    dep_map[tid] = []

            # 1. Cycle detection via 3-color DFS (0=unvisited, 1=visiting, 2=done)
            color: Dict[str, int] = {}
            in_cycle: Set[str] = set()

            def _dfs(node: str, stack: List[str]) -> None:
                color[node] = 1
                stack.append(node)
                for nxt in dep_map.get(node, []):
                    if nxt == node or color.get(nxt) == 1:
                        if nxt in stack:
                            idx = stack.index(nxt)
                            in_cycle.update(stack[idx:])
                        else:
                            in_cycle.add(node)
                    elif nxt in dep_map and color.get(nxt, 0) == 0:
                        _dfs(nxt, stack)
                stack.pop()
                color[node] = 2

            for tid, st in state_map.items():
                if st == "BLOCKED_DEPENDENCY" and color.get(tid, 0) == 0:
                    _dfs(tid, [])

            for tid in sorted(in_cycle):
                if state_map.get(tid) == "BLOCKED_DEPENDENCY":
                    conn.execute(
                        """
                        UPDATE paa_tasks
                        SET execution_state = 'ESCALATED',
                            last_error = 'ANTI_STALL_DEPENDENCY_LOOP_DETECTED',
                            next_action = 'OPERATOR_BREAK_DEPENDENCY_CYCLE',
                            updated_at_utc = ?
                        WHERE task_id = ?
                        """,
                        (now_s, tid),
                    )
                    conn.execute(
                        "INSERT INTO task_events(timestamp_utc, task_id, component, event_type, details_json) VALUES (?, ?, ?, ?, ?)",
                        (now_s, tid, "anti_stall", "DEPENDENCY_LOOP_ESCALATED", json.dumps({"dependencies": dep_map.get(tid, [])})),
                    )
                    cycles.append(tid)
                    state_map[tid] = "ESCALATED"

            # 2. Unblock satisfied dependencies or escalate broken dependencies
            for tid, st in list(state_map.items()):
                if st != "BLOCKED_DEPENDENCY":
                    continue
                deps = dep_map.get(tid, [])
                if not deps:
                    conn.execute(
                        "UPDATE paa_tasks SET execution_state = 'READY', updated_at_utc = ? WHERE task_id = ?",
                        (now_s, tid),
                    )
                    unblocked.append(tid)
                    continue
                missing_or_broken = [
                    d
                    for d in deps
                    if state_map.get(d)
                    in (
                        "FAILED",
                        "FAILED_PERMANENT",
                        "REJECTED",
                        "BLOCKED",
                        "ESCALATED",
                        "CANCELLED",
                        "BLOCKED_AUTHORIZATION",
                        None,
                    )
                ]
                if missing_or_broken:
                    conn.execute(
                        """
                        UPDATE paa_tasks
                        SET execution_state = 'ESCALATED',
                            last_error = ?,
                            next_action = 'RESOLVE_UPSTREAM_DEPENDENCY_BLOCKER',
                            updated_at_utc = ?
                        WHERE task_id = ?
                        """,
                        (f"UPSTREAM_DEPENDENCY_BLOCKED:{missing_or_broken}", now_s, tid),
                    )
                    upstream_failed.append(tid)
                elif all(state_map.get(d) in ("COMPLETED", "VERIFIED_COMPLETE") for d in deps):
                    conn.execute(
                        "UPDATE paa_tasks SET execution_state = 'READY', updated_at_utc = ? WHERE task_id = ?",
                        (now_s, tid),
                    )
                    unblocked.append(tid)

        return {"unblocked": unblocked, "cycles_escalated": cycles, "upstream_escalated": upstream_failed}

    def recover_interrupted_tasks(
        self,
        backoff_base_sec: float = 30.0,
        kill_hung_local_worker: bool = True,
    ) -> Dict[str, List[str]]:
        """
        Detects crashed or hung `RUNNING` workers:
          - If `worker_pid` exited unexpectedly -> transitions to `CHECKPOINTED` (preserving `last_checkpoint_json`!)
            so the next Director cycle resumes cleanly from the last completed step without duplicate side effects.
          - If `lease_expires_utc` passed while `worker_pid` is hung -> sends bounded `SIGTERM` to hung worker PID
            (never touching production trading PIDs!), records stall evidence, and re-queues as `CHECKPOINTED` or `ESCALATED`.
          - Also promotes `FAILED_RETRYABLE` tasks whose `next_eligible_at_utc <= now` back to `READY`/`CHECKPOINTED`.
        """
        reclaimed_crashed: List[str] = []
        reclaimed_hung: List[str] = []
        escalated: List[str] = []
        promoted_retries: List[str] = []
        now = utc_now()
        now_s = now.isoformat()

        with self._connect(immediate=True) as conn:
            running = conn.execute("SELECT * FROM paa_tasks WHERE execution_state = 'RUNNING'").fetchall()
            for r in running:
                tid = r["task_id"]
                wpid = r["worker_pid"]
                whost = r["worker_host"]
                lease_dt = parse_iso(r["lease_expires_utc"])
                lease_expired = lease_dt is not None and lease_dt <= now
                pid_alive = is_pid_alive(wpid, whost)

                if pid_alive and not lease_expired:
                    continue

                reason = "WORKER_CRASHED_PID_DEAD" if not pid_alive else "STALLED_WORKER_LEASE_EXPIRED"
                if pid_alive and lease_expired and kill_hung_local_worker and whost == self.hostname and wpid and int(wpid) != os.getpid():
                    try:
                        os.kill(int(wpid), signal.SIGTERM)
                    except Exception:
                        pass

                new_attempts = int(r["attempts"]) + 1
                max_ret = int(r["max_retries"])
                has_ckpt = bool(r["last_checkpoint_json"] and r["last_checkpoint_json"] != "{}")
                if new_attempts > max_ret:
                    conn.execute(
                        """
                        UPDATE paa_tasks
                        SET execution_state = 'ESCALATED',
                            attempts = ?,
                            worker_pid = NULL,
                            lease_expires_utc = NULL,
                            last_error = ?,
                            next_action = 'OPERATOR_REVIEW_REPEATED_FAILURES',
                            updated_at_utc = ?
                        WHERE task_id = ?
                        """,
                        (new_attempts, f"{reason}_MAX_RETRIES_EXCEEDED({new_attempts}/{max_ret})", now_s, tid),
                    )
                    escalated.append(tid)
                else:
                    # Crash recovery with a saved checkpoint is immediately resumable (0s wait if crashed once,
                    # bounded exponential backoff on repeated failures)
                    delay_s = 0.0 if (has_ckpt and new_attempts == 1 and not lease_expired) else min(1800.0, float(backoff_base_sec) * (2 ** max(0, new_attempts - 1)))
                    elig_s = (now + timedelta(seconds=delay_s)).isoformat()
                    target_state = "CHECKPOINTED" if has_ckpt else "READY"
                    conn.execute(
                        """
                        UPDATE paa_tasks
                        SET execution_state = ?,
                            attempts = ?,
                            next_eligible_at_utc = ?,
                            worker_pid = NULL,
                            lease_expires_utc = NULL,
                            last_error = ?,
                            next_action = 'RESUME_FROM_CHECKPOINT',
                            updated_at_utc = ?
                        WHERE task_id = ?
                        """,
                        (target_state, new_attempts, elig_s, reason, now_s, tid),
                    )
                    if not pid_alive:
                        reclaimed_crashed.append(tid)
                    else:
                        reclaimed_hung.append(tid)

                conn.execute(
                    "INSERT INTO task_events(timestamp_utc, task_id, component, event_type, details_json) VALUES (?, ?, ?, ?, ?)",
                    (
                        now_s,
                        tid,
                        "anti_stall",
                        reason,
                        json.dumps(
                            {
                                "worker_pid": wpid,
                                "attempts": new_attempts,
                                "max_retries": max_ret,
                                "has_checkpoint": has_ckpt,
                                "escalated": new_attempts > max_ret,
                            }
                        ),
                    ),
                )

            retry_rows = conn.execute("SELECT * FROM paa_tasks WHERE execution_state = 'FAILED_RETRYABLE'").fetchall()
            for rr in retry_rows:
                elig_dt = parse_iso(rr["next_eligible_at_utc"])
                if elig_dt is None or elig_dt <= now:
                    has_ckpt = bool(rr["last_checkpoint_json"] and rr["last_checkpoint_json"] != "{}")
                    st_next = "CHECKPOINTED" if has_ckpt else "READY"
                    conn.execute(
                        "UPDATE paa_tasks SET execution_state = ?, updated_at_utc = ? WHERE task_id = ?",
                        (st_next, now_s, rr["task_id"]),
                    )
                    promoted_retries.append(rr["task_id"])

        return {
            "reclaimed_crashed": reclaimed_crashed,
            "reclaimed_hung": reclaimed_hung,
            "escalated": escalated,
            "promoted_retries": promoted_retries,
        }

    def claim_next_eligible_task(
        self,
        lease_ttl_sec: float = 480.0,
        worker_pid: Optional[int] = None,
        worker_id: Optional[str] = None,
        allowed_categories: Optional[Set[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Atomically selects and leases the highest-priority eligible task (`CHECKPOINTED` resumed first within same priority tier!).
        """
        now = utc_now()
        now_s = now.isoformat()
        exp_s = (now + timedelta(seconds=max(0.05, float(lease_ttl_sec)))).isoformat()
        wpid = int(worker_pid if worker_pid is not None else os.getpid())

        with self._connect(immediate=True) as conn:
            rows = conn.execute(
                """
                SELECT * FROM paa_tasks
                WHERE execution_state IN ('CHECKPOINTED', 'READY', 'PENDING')
                ORDER BY
                    priority_rank DESC,
                    CASE WHEN execution_state = 'CHECKPOINTED' THEN 1 ELSE 0 END DESC,
                    ev_priority_score DESC,
                    created_at_utc ASC
                """
            ).fetchall()
            chosen: Optional[sqlite3.Row] = None
            for r in rows:
                if allowed_categories and r["category"] not in allowed_categories:
                    continue
                elig_dt = parse_iso(r["next_eligible_at_utc"])
                if elig_dt is not None and elig_dt > now:
                    continue
                chosen = r
                break

            if chosen is None:
                return None

            tid = chosen["task_id"]
            conn.execute(
                """
                UPDATE paa_tasks
                SET execution_state = 'RUNNING',
                    worker_pid = ?,
                    worker_host = ?,
                    lease_expires_utc = ?,
                    last_heartbeat_utc = ?,
                    updated_at_utc = ?
                WHERE task_id = ?
                """,
                (wpid, self.hostname, exp_s, now_s, now_s, tid),
            )
            conn.execute(
                "INSERT INTO task_events(timestamp_utc, task_id, component, event_type, details_json) VALUES (?, ?, ?, ?, ?)",
                (now_s, tid, "director", "TASK_CLAIMED", json.dumps({"worker_pid": wpid, "lease_expires_utc": exp_s})),
            )
            updated = conn.execute("SELECT * FROM paa_tasks WHERE task_id = ?", (tid,)).fetchone()
            return self._row_to_task(updated)

    def save_checkpoint(
        self,
        task_id: str,
        checkpoint: Dict[str, Any],
        next_action: Optional[str] = None,
        lease_ttl_sec: float = 480.0,
    ) -> None:
        """Persists an atomic step checkpoint and extends the worker lease."""
        now = utc_now()
        now_s = now.isoformat()
        exp_s = (now + timedelta(seconds=max(0.05, float(lease_ttl_sec)))).isoformat()
        with self._connect(immediate=True) as conn:
            if next_action is not None:
                conn.execute(
                    """
                    UPDATE paa_tasks
                    SET last_checkpoint_json = ?, next_action = ?, last_heartbeat_utc = ?,
                        last_progress_utc = ?, lease_expires_utc = ?, updated_at_utc = ?
                    WHERE task_id = ?
                    """,
                    (json.dumps(checkpoint, default=str), next_action, now_s, now_s, exp_s, now_s, task_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE paa_tasks
                    SET last_checkpoint_json = ?, last_heartbeat_utc = ?,
                        last_progress_utc = ?, lease_expires_utc = ?, updated_at_utc = ?
                    WHERE task_id = ?
                    """,
                    (json.dumps(checkpoint, default=str), now_s, now_s, exp_s, now_s, task_id),
                )
            conn.execute(
                "INSERT INTO task_events(timestamp_utc, task_id, component, event_type, details_json) VALUES (?, ?, ?, ?, ?)",
                (now_s, task_id, "worker", "CHECKPOINT_SAVED", json.dumps({"checkpoint": checkpoint, "next_action": next_action}, default=str)),
            )

    def complete_task(
        self,
        task_id: str,
        completion_evidence: Dict[str, Any],
        next_action: str = "NONE_TASK_COMPLETE",
        caller_is_ai_worker: bool = False,
    ) -> None:
        if caller_is_ai_worker:
            raise PermissionError(
                "ZERO_TRUST_VIOLATION: AI worker cannot mark a task COMPLETED or VERIFIED_COMPLETE; use submit_for_verification()."
            )
        now_s = utc_now_iso()
        with self._connect(immediate=True) as conn:
            conn.execute(
                """
                UPDATE paa_tasks
                SET execution_state = 'COMPLETED',
                    completion_evidence_json = ?,
                    epistemic_status = 'VERIFIED_FACT',
                    next_action = ?,
                    worker_pid = NULL,
                    lease_expires_utc = NULL,
                    last_error = '',
                    updated_at_utc = ?,
                    completed_at_utc = ?
                WHERE task_id = ?
                """,
                (json.dumps(completion_evidence, default=str), next_action, now_s, now_s, task_id),
            )
            conn.execute(
                "INSERT INTO task_events(timestamp_utc, task_id, component, event_type, details_json) VALUES (?, ?, ?, ?, ?)",
                (now_s, task_id, "worker", "TASK_COMPLETED", json.dumps(completion_evidence, default=str)),
            )

    def claim_task_transaction(
        self,
        task_id: str,
        worker_pid: Optional[int] = None,
        lease_ttl_sec: float = 480.0,
    ) -> Optional[Dict[str, Any]]:
        """Explicit Zero-Trust transition `PENDING`/`READY`/`CHECKPOINTED` -> `CLAIMED`."""
        now = utc_now()
        now_s = now.isoformat()
        exp_s = (now + timedelta(seconds=max(0.05, float(lease_ttl_sec)))).isoformat()
        wpid = int(worker_pid if worker_pid is not None else os.getpid())
        with self._connect(immediate=True) as conn:
            cur = conn.execute(
                """
                UPDATE paa_tasks
                SET execution_state = 'CLAIMED',
                    worker_pid = ?,
                    worker_host = ?,
                    lease_expires_utc = ?,
                    last_heartbeat_utc = ?,
                    updated_at_utc = ?
                WHERE task_id = ? AND execution_state IN ('PENDING', 'READY', 'CHECKPOINTED')
                """,
                (wpid, self.hostname, exp_s, now_s, now_s, task_id),
            )
            if cur.rowcount == 0:
                return None
            conn.execute(
                "INSERT INTO task_events(timestamp_utc, task_id, component, event_type, details_json) VALUES (?, ?, ?, ?, ?)",
                (now_s, task_id, "zero_trust", "STATE_CLAIMED", json.dumps({"worker_pid": wpid})),
            )
            row = conn.execute("SELECT * FROM paa_tasks WHERE task_id = ?", (task_id,)).fetchone()
            return self._row_to_task(row) if row else None

    def start_claimed_task(self, task_id: str, lease_ttl_sec: float = 480.0) -> Optional[Dict[str, Any]]:
        """Explicit Zero-Trust transition `CLAIMED` -> `RUNNING`."""
        now = utc_now()
        now_s = now.isoformat()
        exp_s = (now + timedelta(seconds=max(0.05, float(lease_ttl_sec)))).isoformat()
        with self._connect(immediate=True) as conn:
            cur = conn.execute(
                """
                UPDATE paa_tasks
                SET execution_state = 'RUNNING',
                    lease_expires_utc = ?,
                    last_heartbeat_utc = ?,
                    updated_at_utc = ?
                WHERE task_id = ? AND execution_state IN ('CLAIMED', 'READY', 'PENDING', 'CHECKPOINTED')
                """,
                (exp_s, now_s, now_s, task_id),
            )
            if cur.rowcount == 0:
                return None
            conn.execute(
                "INSERT INTO task_events(timestamp_utc, task_id, component, event_type, details_json) VALUES (?, ?, ?, ?, ?)",
                (now_s, task_id, "zero_trust", "STATE_RUNNING", json.dumps({"lease_expires_utc": exp_s})),
            )
            row = conn.execute("SELECT * FROM paa_tasks WHERE task_id = ?", (task_id,)).fetchone()
            return self._row_to_task(row) if row else None

    def submit_for_verification(
        self,
        task_id: str,
        worker_claims: Dict[str, Any],
        evidence: Optional[Dict[str, Any]] = None,
        epistemic_status: str = "OBSERVATION",
    ) -> Dict[str, Any]:
        """
        Zero-Trust worker submission boundary:
        An AI worker may ONLY submit claims/evidence and request verification (`PENDING_VERIFICATION`).
        It CANNOT set `VERIFIED_COMPLETE`.
        """
        now_s = utc_now_iso()
        submission = {
            "submitted_at_utc": now_s,
            "worker_claims": worker_claims,
            "proposed_evidence": evidence or {},
            "worker_epistemic_status": epistemic_status,
        }
        with self._connect(immediate=True) as conn:
            conn.execute(
                """
                UPDATE paa_tasks
                SET execution_state = 'PENDING_VERIFICATION',
                    worker_submission_json = ?,
                    epistemic_status = ?,
                    worker_pid = NULL,
                    lease_expires_utc = NULL,
                    next_action = 'AWAITING_DETERMINISTIC_VERIFICATION_CONTROLLER',
                    updated_at_utc = ?
                WHERE task_id = ?
                """,
                (json.dumps(submission, default=str), epistemic_status, now_s, task_id),
            )
            conn.execute(
                "INSERT INTO task_events(timestamp_utc, task_id, component, event_type, details_json) VALUES (?, ?, ?, ?, ?)",
                (now_s, task_id, "ai_worker", "SUBMITTED_FOR_VERIFICATION", json.dumps(submission, default=str)),
            )
            row = conn.execute("SELECT * FROM paa_tasks WHERE task_id = ?", (task_id,)).fetchone()
            if not row:
                raise KeyError(f"Task {task_id} not found")
            return self._row_to_task(row)

    def record_verification_verdict(
        self,
        task_id: str,
        *,
        passed: bool,
        verifier_receipt: Dict[str, Any],
        controller_seal: str,
        terminal_state: Optional[str] = None,
        epistemic_status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Authoritative non-AI verification verdict gate:
        ONLY `DeterministicVerificationController` (holding `VERIFICATION_CONTROLLER_SEAL`) may transition
        a task to `VERIFIED_COMPLETE` (or terminal `REJECTED` / `BLOCKED` / `FAILED`).
        """
        if controller_seal != VERIFICATION_CONTROLLER_SEAL:
            raise PermissionError(
                "ZERO_TRUST_VIOLATION: Only DeterministicVerificationController may finalize task verification!"
            )
        now_s = utc_now_iso()
        if passed:
            t_state = "VERIFIED_COMPLETE"
            epi = epistemic_status or "VERIFIED_FACT"
            nxt = "NONE_VERIFIED_COMPLETE"
            err = ""
            comp_ts: Optional[str] = now_s
        else:
            t_state = terminal_state if terminal_state in ("REJECTED", "BLOCKED", "FAILED", "BLOCKED_AUTHORIZATION") else "REJECTED"
            epi = epistemic_status or ("CONTRADICTED" if t_state == "REJECTED" else "UNKNOWN")
            nxt = f"REMEDIATION_OR_REVIEW_{t_state}"
            err = str(verifier_receipt.get("summary_reason") or "VERIFICATION_GATES_FAILED")[:2000]
            comp_ts = None

        with self._connect(immediate=True) as conn:
            conn.execute(
                """
                UPDATE paa_tasks
                SET execution_state = ?,
                    verification_receipt_json = ?,
                    completion_evidence_json = ?,
                    epistemic_status = ?,
                    worker_pid = NULL,
                    lease_expires_utc = NULL,
                    last_error = ?,
                    next_action = ?,
                    updated_at_utc = ?,
                    completed_at_utc = COALESCE(?, completed_at_utc)
                WHERE task_id = ?
                """,
                (
                    t_state,
                    json.dumps(verifier_receipt, default=str),
                    json.dumps(verifier_receipt, default=str),
                    epi,
                    err,
                    nxt,
                    now_s,
                    comp_ts,
                    task_id,
                ),
            )
            conn.execute(
                "INSERT INTO task_events(timestamp_utc, task_id, component, event_type, details_json) VALUES (?, ?, ?, ?, ?)",
                (
                    now_s,
                    task_id,
                    "verification_controller",
                    f"VERIFICATION_{t_state}",
                    json.dumps({"epistemic_status": epi, **verifier_receipt}, default=str),
                ),
            )
            row = conn.execute("SELECT * FROM paa_tasks WHERE task_id = ?", (task_id,)).fetchone()
            if not row:
                raise KeyError(f"Task {task_id} not found")
            return self._row_to_task(row)

    def block_task_authorization(
        self,
        task_id: str,
        reason: str,
        evidence: Optional[Dict[str, Any]] = None,
    ) -> None:
        now_s = utc_now_iso()
        with self._connect(immediate=True) as conn:
            conn.execute(
                """
                UPDATE paa_tasks
                SET execution_state = 'BLOCKED_AUTHORIZATION',
                    worker_pid = NULL,
                    lease_expires_utc = NULL,
                    last_error = ?,
                    completion_evidence_json = ?,
                    next_action = 'AWAITING_EXPLICIT_OPERATOR_APPROVAL',
                    updated_at_utc = ?
                WHERE task_id = ?
                """,
                (reason, json.dumps(evidence or {"blocked_reason": reason}, default=str), now_s, task_id),
            )
            conn.execute(
                "INSERT INTO task_events(timestamp_utc, task_id, component, event_type, details_json) VALUES (?, ?, ?, ?, ?)",
                (now_s, task_id, "permissions", "TASK_BLOCKED_AUTHORIZATION", json.dumps({"reason": reason, **(evidence or {})}, default=str)),
            )

    def fail_task(
        self,
        task_id: str,
        error_msg: str,
        retryable: bool = True,
        backoff_base_sec: float = 30.0,
    ) -> str:
        now = utc_now()
        now_s = now.isoformat()
        with self._connect(immediate=True) as conn:
            row = conn.execute("SELECT attempts, max_retries FROM paa_tasks WHERE task_id = ?", (task_id,)).fetchone()
            if row is None:
                return "MISSING"
            attempts = int(row["attempts"]) + 1
            max_ret = int(row["max_retries"])
            if retryable and attempts <= max_ret:
                delay = min(1800.0, float(backoff_base_sec) * (2 ** max(0, attempts - 1)))
                elig = (now + timedelta(seconds=delay)).isoformat()
                new_state = "FAILED_RETRYABLE"
                nxt = f"AUTO_RETRY_AT_{elig}"
            else:
                elig = now_s
                new_state = "ESCALATED" if attempts > max_ret else "FAILED_PERMANENT"
                nxt = "OPERATOR_INVESTIGATE_FAILURE"
            conn.execute(
                """
                UPDATE paa_tasks
                SET execution_state = ?,
                    attempts = ?,
                    next_eligible_at_utc = ?,
                    worker_pid = NULL,
                    lease_expires_utc = NULL,
                    last_error = ?,
                    next_action = ?,
                    updated_at_utc = ?
                WHERE task_id = ?
                """,
                (new_state, attempts, elig, str(error_msg)[:2000], nxt, now_s, task_id),
            )
            conn.execute(
                "INSERT INTO task_events(timestamp_utc, task_id, component, event_type, details_json) VALUES (?, ?, ?, ?, ?)",
                (now_s, task_id, "worker", "TASK_FAILED", json.dumps({"state": new_state, "attempts": attempts, "error": str(error_msg)[:800]})),
            )
            return new_state

    def record_research_finding(
        self,
        *,
        finding_id: str,
        category: str,
        hypothesis: str,
        validation_method: str,
        sample_size: int,
        expected_net_ev_usd_per_day: float,
        metrics: Dict[str, Any],
        succeeded: bool,
        verdict: str,
        notes: str = "",
        evidence_stage: str = "HYPOTHESIS",
        epistemic_status: str = "HYPOTHESIS",
    ) -> None:
        now_s = utc_now_iso()
        valid_stages = ("HYPOTHESIS", "BACKTESTED", "OOS_TESTED", "SHADOW_VALIDATED", "LIVE_VERIFIED")
        st_norm = evidence_stage.upper() if evidence_stage.upper() in valid_stages else "HYPOTHESIS"
        with self._connect(immediate=True) as conn:
            conn.execute(
                """
                INSERT INTO research_findings(
                    finding_id, created_at_utc, category, hypothesis, validation_method,
                    sample_size, expected_net_ev_usd_per_day, metrics_json, succeeded, verdict, notes,
                    evidence_stage, epistemic_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(finding_id) DO UPDATE SET
                    created_at_utc = excluded.created_at_utc,
                    sample_size = excluded.sample_size,
                    expected_net_ev_usd_per_day = excluded.expected_net_ev_usd_per_day,
                    metrics_json = excluded.metrics_json,
                    succeeded = excluded.succeeded,
                    verdict = excluded.verdict,
                    notes = excluded.notes,
                    evidence_stage = excluded.evidence_stage,
                    epistemic_status = excluded.epistemic_status
                """,
                (
                    finding_id,
                    now_s,
                    category,
                    hypothesis,
                    validation_method,
                    int(sample_size),
                    float(expected_net_ev_usd_per_day),
                    json.dumps(metrics, default=str),
                    1 if succeeded else 0,
                    verdict,
                    notes,
                    st_norm,
                    epistemic_status,
                ),
            )

    def list_research_findings(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM research_findings ORDER BY created_at_utc DESC LIMIT ?", (int(limit),)).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            try:
                d["metrics"] = json.loads(d.get("metrics_json") or "{}")
            except Exception:
                d["metrics"] = {}
            d["succeeded"] = bool(d.get("succeeded"))
            out.append(d)
        return out

    def upsert_deployment(self, rec: Dict[str, Any]) -> None:
        now_s = utc_now_iso()
        with self._connect(immediate=True) as conn:
            conn.execute(
                """
                INSERT INTO deployments(
                    release_id, created_at_utc, updated_at_utc, task_id, git_branch, candidate_sha, baseline_sha,
                    permission_class, target_env, state, qa_passed, invariants_passed, perf_passed, canary_passed,
                    rolled_back, rollback_reason, evidence_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(release_id) DO UPDATE SET
                    updated_at_utc = excluded.updated_at_utc,
                    target_env = excluded.target_env,
                    state = excluded.state,
                    qa_passed = excluded.qa_passed,
                    invariants_passed = excluded.invariants_passed,
                    perf_passed = excluded.perf_passed,
                    canary_passed = excluded.canary_passed,
                    rolled_back = excluded.rolled_back,
                    rollback_reason = excluded.rollback_reason,
                    evidence_json = excluded.evidence_json
                """,
                (
                    rec["release_id"],
                    rec.get("created_at_utc") or now_s,
                    now_s,
                    rec.get("task_id"),
                    rec.get("git_branch", "HEAD"),
                    rec.get("candidate_sha", ""),
                    rec.get("baseline_sha", ""),
                    rec.get("permission_class", "CONDITIONALLY_AUTOMATIC"),
                    rec.get("target_env", "staging"),
                    rec["state"],
                    1 if rec.get("qa_passed") else 0,
                    1 if rec.get("invariants_passed") else 0,
                    1 if rec.get("perf_passed") else 0,
                    1 if rec.get("canary_passed") else 0,
                    1 if rec.get("rolled_back") else 0,
                    rec.get("rollback_reason", ""),
                    json.dumps(rec.get("evidence", {}), default=str),
                ),
            )

    def list_deployments(self, limit: int = 30) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM deployments ORDER BY updated_at_utc DESC LIMIT ?", (int(limit),)).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            for b in ("qa_passed", "invariants_passed", "perf_passed", "canary_passed", "rolled_back"):
                d[b] = bool(d.get(b))
            try:
                d["evidence"] = json.loads(d.get("evidence_json") or "{}")
            except Exception:
                d["evidence"] = {}
            out.append(d)
        return out

    def record_financial_snapshot(self, snap: Dict[str, Any]) -> None:
        now_s = snap.get("recorded_at_utc") or utc_now_iso()
        with self._connect(immediate=True) as conn:
            conn.execute(
                """
                INSERT INTO financial_snapshots(
                    recorded_at_utc, free_cash_pusd, open_cost_basis_usd, nav_mark_to_bid_usd, nav_resting_maker_usd,
                    verified_realized_net_pnl_usd, raw_ledger_pnl_usd, phantom_adjustment_usd, unrealized_pnl_bid_usd,
                    unrealized_pnl_maker_usd, realized_fees_usd, estimated_slippage_usd, drawdown_from_hwm_usd,
                    capital_utilization_pct, execution_reliability_pct, opportunity_capture_pct, research_ai_cost_usd,
                    infra_cost_usd, net_economic_profit_usd, accounting_discrepancy_usd, accounting_ok,
                    simulated_shadow_t1000_pnl_usd, simulated_paper_oos_pnl_usd, details_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    now_s,
                    float(snap.get("free_cash_pusd", 0.0)),
                    float(snap.get("open_cost_basis_usd", 0.0)),
                    float(snap.get("nav_mark_to_bid_usd", 0.0)),
                    float(snap.get("nav_resting_maker_usd", 0.0)),
                    float(snap.get("verified_realized_net_pnl_usd", 0.0)),
                    float(snap.get("raw_ledger_pnl_usd", 0.0)),
                    float(snap.get("phantom_adjustment_usd", 0.0)),
                    float(snap.get("unrealized_pnl_bid_usd", 0.0)),
                    float(snap.get("unrealized_pnl_maker_usd", 0.0)),
                    float(snap.get("realized_fees_usd", 0.0)),
                    float(snap.get("estimated_slippage_usd", 0.0)),
                    float(snap.get("drawdown_from_hwm_usd", 0.0)),
                    float(snap.get("capital_utilization_pct", 0.0)),
                    float(snap.get("execution_reliability_pct", 100.0)),
                    float(snap.get("opportunity_capture_pct", 0.0)),
                    float(snap.get("research_ai_cost_usd", 0.0)),
                    float(snap.get("infra_cost_usd", 0.0)),
                    float(snap.get("net_economic_profit_usd", 0.0)),
                    float(snap.get("accounting_discrepancy_usd", 0.0)),
                    1 if snap.get("accounting_ok", True) else 0,
                    float(snap.get("simulated_shadow_t1000_pnl_usd", 0.0)),
                    float(snap.get("simulated_paper_oos_pnl_usd", 0.0)),
                    json.dumps(snap.get("details", {}), default=str),
                ),
            )

    def get_latest_financial_snapshot(self) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM financial_snapshots ORDER BY snapshot_id DESC LIMIT 1").fetchone()
        if not row:
            return None
        d = dict(row)
        d["accounting_ok"] = bool(d.get("accounting_ok"))
        try:
            d["details"] = json.loads(d.get("details_json") or "{}")
        except Exception:
            d["details"] = {}
        return d

    def get_queue_summary(self) -> Dict[str, Any]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT execution_state, COUNT(*) AS cnt FROM paa_tasks GROUP BY execution_state"
            ).fetchall()
            counts = {r["execution_state"]: int(r["cnt"]) for r in rows}
            active = conn.execute(
                "SELECT task_id, category, priority_label, title, worker_pid, execution_state, session_count, epistemic_status, updated_at_utc, next_action FROM paa_tasks WHERE execution_state IN ('RUNNING', 'CLAIMED', 'PENDING_VERIFICATION') ORDER BY updated_at_utc DESC"
            ).fetchall()
            pending = conn.execute(
                "SELECT task_id, category, priority_label, ev_priority_score, title, execution_state, session_count, epistemic_status, next_action FROM paa_tasks WHERE execution_state IN ('CHECKPOINTED', 'READY', 'PENDING', 'BLOCKED_DEPENDENCY') ORDER BY priority_rank DESC, ev_priority_score DESC LIMIT 15"
            ).fetchall()
            blocked_auth = conn.execute(
                "SELECT task_id, category, priority_label, title, execution_state, epistemic_status, last_error, updated_at_utc FROM paa_tasks WHERE execution_state IN ('BLOCKED_AUTHORIZATION', 'BLOCKED', 'REJECTED', 'ESCALATED', 'FAILED') ORDER BY updated_at_utc DESC LIMIT 15"
            ).fetchall()
        return {
            "counts_by_state": counts,
            "active_tasks": [dict(x) for x in active],
            "pending_tasks": [dict(x) for x in pending],
            "blocked_or_escalated_tasks": [dict(x) for x in blocked_auth],
        }

    # ------------------------------------------------------------------
    # Tier-B Verified Operational Memory & Stateless Session Telemetry
    # ------------------------------------------------------------------
    def upsert_verified_fact(
        self,
        *,
        fact_key: str,
        category: str,
        value: Any,
        epistemic_status: str = "VERIFIED_FACT",
        source_type: str,
        source_ref: str,
        verified_by: str,
        ttl_sec: float = 300.0,
        revalidation_rule: str = "REQUERY_AUTHORITATIVE_SOURCE",
        observed_at_utc: Optional[str] = None,
        contradicted_reason: str = "",
    ) -> Dict[str, Any]:
        """
        Records a Tier-B operational fact with explicit source, timestamp, epistemic class, and TTL expiry.
        Point-in-time measurements (e.g. CLOB HTTP latency) automatically degrade to
        `STALE_REVALIDATION_REQUIRED` once `expires_at_utc` passes.
        """
        obs_dt = parse_iso(observed_at_utc) if observed_at_utc else utc_now()
        if obs_dt is None:
            obs_dt = utc_now()
        obs_s = obs_dt.isoformat()
        exp_s = (obs_dt + timedelta(seconds=max(1.0, float(ttl_sec)))).isoformat()
        with self._connect(immediate=True) as conn:
            conn.execute(
                """
                INSERT INTO verified_facts(
                    fact_key, category, value_json, epistemic_status, source_type, source_ref,
                    observed_at_utc, verified_by, ttl_sec, expires_at_utc, revalidation_rule, contradicted_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(fact_key) DO UPDATE SET
                    category = excluded.category,
                    value_json = excluded.value_json,
                    epistemic_status = excluded.epistemic_status,
                    source_type = excluded.source_type,
                    source_ref = excluded.source_ref,
                    observed_at_utc = excluded.observed_at_utc,
                    verified_by = excluded.verified_by,
                    ttl_sec = excluded.ttl_sec,
                    expires_at_utc = excluded.expires_at_utc,
                    revalidation_rule = excluded.revalidation_rule,
                    contradicted_reason = excluded.contradicted_reason
                """,
                (
                    fact_key,
                    category,
                    json.dumps(value, default=str),
                    epistemic_status,
                    source_type,
                    source_ref,
                    obs_s,
                    verified_by,
                    float(ttl_sec),
                    exp_s,
                    revalidation_rule,
                    contradicted_reason,
                ),
            )
        return self.get_verified_fact(fact_key, allow_stale=True) or {}

    def _hydrate_fact_row(self, row: sqlite3.Row, now: Optional[datetime] = None) -> Dict[str, Any]:
        now_dt = now or utc_now()
        d = dict(row)
        try:
            d["value"] = json.loads(d.get("value_json") or "null")
        except Exception:
            d["value"] = d.get("value_json")
        obs_dt = parse_iso(d.get("observed_at_utc"))
        exp_dt = parse_iso(d.get("expires_at_utc"))
        d["age_sec"] = round((now_dt - obs_dt).total_seconds(), 2) if obs_dt else None
        rem = round((exp_dt - now_dt).total_seconds(), 2) if exp_dt else -1.0
        d["ttl_remaining_sec"] = rem
        is_stale = rem <= 0.0
        d["is_stale"] = is_stale
        if d.get("epistemic_status") == "CONTRADICTED":
            d["effective_status"] = "CONTRADICTED"
        elif is_stale:
            d["effective_status"] = "STALE_REVALIDATION_REQUIRED"
        else:
            d["effective_status"] = str(d.get("epistemic_status") or "UNKNOWN")
        return d

    def get_verified_fact(self, fact_key: str, allow_stale: bool = False) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM verified_facts WHERE fact_key = ?", (fact_key,)).fetchone()
        if not row:
            return None
        hyd = self._hydrate_fact_row(row)
        if not allow_stale and (hyd["is_stale"] or hyd["effective_status"] == "CONTRADICTED"):
            return None
        return hyd

    def list_verified_facts(
        self,
        *,
        include_stale: bool = True,
        category: Optional[str] = None,
        limit: int = 60,
    ) -> List[Dict[str, Any]]:
        now_dt = utc_now()
        with self._connect() as conn:
            if category:
                rows = conn.execute(
                    "SELECT * FROM verified_facts WHERE category = ? ORDER BY observed_at_utc DESC LIMIT ?",
                    (category, int(limit)),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM verified_facts ORDER BY observed_at_utc DESC LIMIT ?",
                    (int(limit),),
                ).fetchall()
        out: List[Dict[str, Any]] = []
        for r in rows:
            h = self._hydrate_fact_row(r, now=now_dt)
            if not include_stale and h["is_stale"]:
                continue
            out.append(h)
        return out

    def mark_fact_contradicted(
        self,
        fact_key: str,
        *,
        reason: str,
        claimed_value: Any = None,
        authoritative_source_ref: str = "",
        category: str = "CONTRADICTION_AUDIT",
    ) -> Dict[str, Any]:
        rec = self.upsert_verified_fact(
            fact_key=fact_key,
            category=category,
            value={"claimed": claimed_value, "contradicted_reason": reason},
            epistemic_status="CONTRADICTED",
            source_type="CONTRADICTION_DETECTOR",
            source_ref=authoritative_source_ref or "DeterministicVerificationController",
            verified_by="DeterministicVerificationController",
            ttl_sec=86400.0,
            revalidation_rule="DO_NOT_TRUST_CONTRADICTED_CLAIM",
            contradicted_reason=reason,
        )
        self.log_event(
            "verification_controller",
            "CLAIM_CONTRADICTED",
            {"fact_key": fact_key, "reason": reason, "claimed_value": claimed_value, "source_ref": authoritative_source_ref},
        )
        return rec

    def record_session_run(
        self,
        *,
        task_id: str,
        stage_role: str,
        conversation_id: Optional[str],
        fresh_session: bool,
        model_name: str,
        prompt_chars: int,
        est_prompt_tokens: int,
        actual_input_tokens: int,
        output_tokens: int,
        context_budget_tokens: int,
        context_utilization_pct: float,
        checkpoint_triggered: bool,
        status: str,
        details: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        sid = session_id or f"SES_{int(time.time()*1000)}_{uuid.uuid4().hex[:6].upper()}"
        now_s = utc_now_iso()
        with self._connect(immediate=True) as conn:
            conn.execute(
                """
                INSERT INTO session_runs(
                    session_id, task_id, stage_role, conversation_id, fresh_session, model_name,
                    prompt_chars, est_prompt_tokens, actual_input_tokens, output_tokens,
                    context_budget_tokens, context_utilization_pct, checkpoint_triggered,
                    status, created_at_utc, details_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sid,
                    task_id,
                    stage_role,
                    conversation_id,
                    1 if fresh_session else 0,
                    model_name,
                    int(prompt_chars),
                    int(est_prompt_tokens),
                    int(actual_input_tokens),
                    int(output_tokens),
                    int(context_budget_tokens),
                    round(float(context_utilization_pct), 2),
                    1 if checkpoint_triggered else 0,
                    status,
                    now_s,
                    json.dumps(details or {}, default=str),
                ),
            )
            conn.execute(
                "UPDATE paa_tasks SET session_count = COALESCE(session_count, 0) + 1, updated_at_utc = ? WHERE task_id = ?",
                (now_s, task_id),
            )
        return {
            "session_id": sid,
            "task_id": task_id,
            "stage_role": stage_role,
            "conversation_id": conversation_id,
            "fresh_session": fresh_session,
            "context_utilization_pct": round(float(context_utilization_pct), 2),
            "checkpoint_triggered": checkpoint_triggered,
            "status": status,
            "created_at_utc": now_s,
        }

    def list_session_runs(self, task_id: Optional[str] = None, limit: int = 30) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            if task_id:
                rows = conn.execute(
                    "SELECT * FROM session_runs WHERE task_id = ? ORDER BY created_at_utc ASC LIMIT ?",
                    (task_id, int(limit)),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM session_runs ORDER BY created_at_utc DESC LIMIT ?",
                    (int(limit),),
                ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["fresh_session"] = bool(d.get("fresh_session"))
            d["checkpoint_triggered"] = bool(d.get("checkpoint_triggered"))
            try:
                d["details"] = json.loads(d.get("details_json") or "{}")
            except Exception:
                d["details"] = {}
            out.append(d)
        return out

    def get_zero_trust_summary(self) -> Dict[str, Any]:
        facts = self.list_verified_facts(include_stale=True, limit=200)
        fresh_cnt = sum(1 for f in facts if f["effective_status"] in ("VERIFIED_FACT", "OBSERVATION") and not f["is_stale"])
        stale_cnt = sum(1 for f in facts if f["effective_status"] == "STALE_REVALIDATION_REQUIRED")
        contra_cnt = sum(1 for f in facts if f["effective_status"] == "CONTRADICTED")

        with self._connect() as conn:
            sr_row = conn.execute(
                """
                SELECT COUNT(*) AS total_sessions,
                       SUM(CASE WHEN fresh_session = 1 THEN 1 ELSE 0 END) AS fresh_sessions,
                       MAX(context_utilization_pct) AS max_ctx_pct,
                       AVG(context_utilization_pct) AS avg_ctx_pct,
                       SUM(CASE WHEN checkpoint_triggered = 1 THEN 1 ELSE 0 END) AS ctx_rotations
                FROM session_runs
                """
            ).fetchone()
            rf_rows = conn.execute(
                "SELECT COALESCE(evidence_stage, 'HYPOTHESIS') AS stg, COUNT(*) AS cnt FROM research_findings GROUP BY COALESCE(evidence_stage, 'HYPOTHESIS')"
            ).fetchall()
            tk_rows = conn.execute(
                "SELECT execution_state, COUNT(*) AS cnt FROM paa_tasks GROUP BY execution_state"
            ).fetchall()

        total_s = int((sr_row["total_sessions"] if sr_row else 0) or 0)
        fresh_s = int((sr_row["fresh_sessions"] if sr_row else 0) or 0)
        ladder = {r["stg"]: int(r["cnt"]) for r in rf_rows}
        t_counts = {r["execution_state"]: int(r["cnt"]) for r in tk_rows}
        return {
            "verified_facts_fresh": fresh_cnt,
            "verified_facts_stale": stale_cnt,
            "verified_facts_contradicted": contra_cnt,
            "stateless_sessions_total": total_s,
            "fresh_session_ratio_pct": round(100.0 * fresh_s / max(1, total_s), 1) if total_s > 0 else 100.0,
            "max_context_utilization_pct": round(float((sr_row["max_ctx_pct"] if sr_row else 0.0) or 0.0), 2),
            "avg_context_utilization_pct": round(float((sr_row["avg_ctx_pct"] if sr_row else 0.0) or 0.0), 2),
            "context_checkpoint_rotations": int((sr_row["ctx_rotations"] if sr_row else 0) or 0),
            "research_evidence_ladder": {
                "HYPOTHESIS": ladder.get("HYPOTHESIS", 0),
                "BACKTESTED": ladder.get("BACKTESTED", 0),
                "OOS_TESTED": ladder.get("OOS_TESTED", 0),
                "SHADOW_VALIDATED": ladder.get("SHADOW_VALIDATED", 0),
                "LIVE_VERIFIED": ladder.get("LIVE_VERIFIED", 0),
            },
            "task_states": t_counts,
        }
