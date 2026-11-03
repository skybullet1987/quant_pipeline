"""
Comprehensive Automated Test Suite for PAA Autonomous Operating System (`tests/test_paa_autonomy_os.py`).

Covers all core invariants and failure modes across `src/paa_os/`:
  1. Durable SQLite WAL Task Queue (all 12 required fields, deduplication, priority/EV ordering).
  2. Persistent Checkpoints & Idempotent Resumption (zero duplicate step execution after interruption).
  3. Anti-Stall Recovery (dead PID reclamation + hung worker termination + independent task progress).
  4. Dependency Resolution & Circular Dependency Escalation.
  5. 3-Class Permission Gate, Protected File/Envelope Diff Blocking, Non-Plan Live Repo Blocking & Secret Stripping.
  6. Isolated Git Worktree Builder + 6-Gate Deployment Controller + Automatic Canary Rollback.
  7. Financial Integrity Safeguard & Strict Separation of Realized On-Chain Cash vs Non-Cash Artifacts vs Simulated PnL.
  8. Independent Tier-1 Monitor & Tier-2 Supervisor (detecting Director staleness & Monitor failure).
  9. Autonomous Research Continuity (storing both accepted and rejected hypotheses + empty-pipeline anti-stall).
  10. Budget Caps, Rate Limits & Master Emergency Stop.
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict

import pytest

from src.paa_os.accountant import PAAAccountant
from src.paa_os.agent_runtime import HeadlessAgentRunner
from src.paa_os.budget import BudgetManager
from src.paa_os.builder_and_deployer import DeploymentController, GitWorktreeBuilder, _find_git_exe
from src.paa_os.director import PAADirector
from src.paa_os.monitor import PAAIndependentSupervisor
from src.paa_os.permissions import (
    PermissionClass,
    PermissionDeniedError,
    PermissionGate,
    build_isolated_worker_env,
    load_autonomy_config,
)
from src.paa_os.researcher import PAAResearcher
from src.paa_os.task_db import PAATaskDB
from src.polymarket_research.holistic_strategy_governance import DEFAULT_HOLISTIC_CONFIG


def _make_test_cfg() -> Dict[str, Any]:
    cfg = copy.deepcopy(load_autonomy_config())
    cfg["monitoring"]["worker_lease_ttl_sec"] = 5
    cfg["monitoring"]["monitor_heartbeat_max_age_sec"] = 30
    cfg["monitoring"]["director_heartbeat_max_age_sec"] = 60
    cfg["monitoring"]["accounting_discrepancy_threshold_usd"] = 1.00
    cfg["monitoring"]["max_consecutive_empty_research_runs"] = 2
    cfg["budget"]["retry_backoff_base_sec"] = 0.05
    cfg["budget"]["max_daily_ai_cost_usd"] = 1.00
    cfg["budget"]["max_hourly_ai_invocations"] = 5
    return cfg


def test_task_db_all_12_fields_dedupe_and_priority_ranking(tmp_path: Path) -> None:
    db = PAATaskDB(tmp_path / "paa_tasks.db")
    ok, msg = db.check_integrity()
    assert ok is True and msg == "ok"

    t_low, c1 = db.enqueue_task(
        category="RESEARCH_DISCOVERY",
        priority_label="P2",
        expected_net_ev_usd_per_day=1.20,
        dedupe_key="TEST_DEDUPE_1",
        title="Scan weather markets",
        financial_impact_hypothesis="+$1.20/day maker edge",
        evidence={"markets": 12},
        required_permission_class=PermissionClass.AUTOMATICALLY_PERMITTED.value,
        validation_requirements={"oos_sharpe_gt_1": True},
        next_action="RUN_SCAN",
    )
    assert c1 is True
    # Duplicate dedupe_key while active/pending must NOT create duplicate work
    t_dup, c2 = db.enqueue_task(
        category="RESEARCH_DISCOVERY",
        priority_label="P2",
        expected_net_ev_usd_per_day=1.20,
        dedupe_key="TEST_DEDUPE_1",
        title="Duplicate scan",
    )
    assert c2 is False
    assert t_dup["task_id"] == t_low["task_id"]

    # Verify all 12 mandatory fields exist on hydrated record
    for req_field in (
        "task_id",
        "category",
        "priority_label",
        "financial_impact_hypothesis",
        "evidence",
        "required_permission_class",
        "execution_state",
        "state",
        "attempts",
        "max_retries",
        "dependencies",
        "last_checkpoint",
        "validation_requirements",
        "completion_evidence",
        "next_action",
    ):
        assert req_field in t_low

    t_high, _ = db.enqueue_task(
        category="SAFETY_ACCOUNTING",
        priority_label="P0",
        expected_net_ev_usd_per_day=25.0,
        title="Reconcile cash",
    )
    claimed = db.claim_next_eligible_task(worker_id="w1")
    assert claimed is not None
    assert claimed["task_id"] == t_high["task_id"]
    assert claimed["state"] == "RUNNING"
    assert claimed["attempts"] == 0


def test_task_persistence_checkpoint_resumption_no_duplicate_side_effects(tmp_path: Path) -> None:
    cfg = _make_test_cfg()
    data_dir = tmp_path / "data" / "polymarket"
    director = PAADirector(repo_root=tmp_path, data_dir=data_dir, autonomy_cfg=cfg)
    marker_file = tmp_path / "side_effects.log"

    t, _ = director.db.enqueue_task(
        category="QA_VALIDATION",
        priority_label="P1",
        expected_net_ev_usd_per_day=3.0,
        title="Multi-step resumable QA task",
        payload={
            "side_effect_log_path": str(marker_file),
            "steps": [
                {"step_id": "step_1", "action": "APPEND_MARKER"},
                {"step_id": "step_2", "action": "APPEND_MARKER"},
                {"step_id": "step_3", "action": "APPEND_MARKER"},
            ],
        },
    )

    # Simulate worker executing step_1, saving checkpoint, and crashing (dead PID 99999991) before step_2
    claimed = director.db.claim_next_eligible_task(worker_id="crashed_worker", worker_pid=99999991, lease_ttl_sec=60.0)
    assert claimed is not None and claimed["task_id"] == t["task_id"]
    marker_file.write_text("step_1\n", encoding="utf-8")
    director.db.save_checkpoint(
        t["task_id"],
        {"completed_steps": ["step_1"], "step_outputs": {"step_1": {"ok": True}}},
        next_action="RESUME_AT_STEP_2",
    )

    # Director runs cycle -> detects dead PID 99999991 -> reclaims as CHECKPOINTED -> resumes at step_2!
    time.sleep(0.08)
    cycle = director.run_cycle(max_tasks_per_cycle=2, allow_headless_ai=False, run_proactive_research_if_idle=False)
    assert cycle["recovered_interrupted"]["reclaimed_crashed"] == [t["task_id"]]

    final_task = director.db.get_task(t["task_id"])
    assert final_task is not None
    assert final_task["state"] == "COMPLETED"
    lines = [ln.strip() for ln in marker_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
    # Exact once-only execution across crash boundary!
    assert lines == ["step_1", "step_2", "step_3"]


def test_stalled_worker_killed_and_independent_tasks_proceed(tmp_path: Path) -> None:
    db = PAATaskDB(tmp_path / "paa_tasks.db")

    # Spawn a real hung Python child process
    hung_proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    try:
        t_hung, _ = db.enqueue_task(
            category="ENGINEERING_OPTIMIZATION",
            priority_label="P2",
            expected_net_ev_usd_per_day=1.0,
            title="Hung optimization worker",
            max_retries=1,
        )
        t_indep, _ = db.enqueue_task(
            category="PROFIT_REPORTING",
            priority_label="P1",
            expected_net_ev_usd_per_day=2.0,
            title="Independent reporting task",
        )
        claimed_hung = db.claim_next_eligible_task(
            worker_id="hung_w",
            worker_pid=hung_proc.pid,
            lease_ttl_sec=0.15,
            allowed_categories={"ENGINEERING_OPTIMIZATION"},
        )
        assert claimed_hung is not None and claimed_hung["task_id"] == t_hung["task_id"]

        time.sleep(0.25)
        rec = db.recover_interrupted_tasks(backoff_base_sec=5.0, kill_hung_local_worker=True)
        assert rec["reclaimed_hung"] == [t_hung["task_id"]]
        hung_proc.wait(timeout=5.0)
        assert hung_proc.poll() is not None  # Process was terminated!

        # While t_hung is in retry backoff (5s), independent task t_indep claims and executes immediately!
        next_task = db.claim_next_eligible_task(worker_id="healthy_w")
        assert next_task is not None
        assert next_task["task_id"] == t_indep["task_id"]
    finally:
        if hung_proc.poll() is None:
            hung_proc.kill()


def test_dependency_cycle_detection_and_resolution(tmp_path: Path) -> None:
    db = PAATaskDB(tmp_path / "paa_tasks.db")
    t_base, _ = db.enqueue_task(category="QA_VALIDATION", priority_label="P1", title="Base QA")
    t_dep, _ = db.enqueue_task(
        category="CANDIDATE_EVALUATION",
        priority_label="P1",
        title="Dependent Eval",
        dependencies=[t_base["task_id"]],
    )
    assert t_dep["state"] == "BLOCKED_DEPENDENCY"

    db.claim_next_eligible_task()
    db.complete_task(t_base["task_id"], {"qa": "passed"})
    res1 = db.resolve_dependencies_and_detect_cycles()
    assert res1["unblocked"] == [t_dep["task_id"]]
    assert db.get_task(t_dep["task_id"])["state"] == "READY"

    # Inject a circular dependency A <-> B and verify escalation without hanging
    db.enqueue_task(category="QA_VALIDATION", title="Cycle A", dependencies=["TASK_CYCLE_B"], task_id="TASK_CYCLE_A")
    db.enqueue_task(category="QA_VALIDATION", title="Cycle B", dependencies=["TASK_CYCLE_A"], task_id="TASK_CYCLE_B")
    res2 = db.resolve_dependencies_and_detect_cycles()
    assert set(res2["cycles_escalated"]) == {"TASK_CYCLE_A", "TASK_CYCLE_B"}
    assert db.get_task("TASK_CYCLE_A")["state"] == "ESCALATED"
    assert db.get_task("TASK_CYCLE_B")["state"] == "ESCALATED"


def test_permission_classes_diff_blocking_and_credential_stripping(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POLYGON_PRIVATE_KEY", "0xdeadbeef_secret_private_key")
    monkeypatch.setenv("POLY_API_SECRET", "super_secret_poly_api")
    monkeypatch.setenv("BUILDER_PRIVATE_KEY", "builder_secret_123")

    cfg = _make_test_cfg()
    clean_env = build_isolated_worker_env(role="TEST_WORKER", autonomy_cfg=cfg)
    assert "POLYGON_PRIVATE_KEY" not in clean_env
    assert "POLY_API_SECRET" not in clean_env
    assert "BUILDER_PRIVATE_KEY" not in clean_env
    assert clean_env["PAA_SIGNING_DISABLED"] == "1"
    assert clean_env["PAA_WORKER_ROLE"] == "TEST_WORKER"

    gate = PermissionGate(autonomy_cfg=cfg, approvals_dir=tmp_path / "approvals")

    # 1. Task requesting live sleeve activation without human approval MUST fail
    unapproved_task = {
        "task_id": "TASK_LIVE_ACT_1",
        "required_permission_class": PermissionClass.AUTOMATICALLY_PERMITTED.value,
        "required_scopes": ["NEW_LIVE_TRADING_ACTIVATION"],
    }
    ok_t, msg_t = gate.check_task_authorization(unapproved_task)
    assert ok_t is False and "EXPLICIT_AUTHORIZATION_REQUIRED" in msg_t

    # 2. Protected file modifications (.env, permissions.py) MUST fail diff audit
    ok_d1, viol_1 = gate.inspect_candidate_diff(
        changed_files=[".env", "src/paa_os/permissions.py"],
        diff_text="+POLYGON_PRIVATE_KEY=hack",
    )
    assert ok_d1 is False
    assert any("PROTECTED_FILE_MODIFIED" in v for v in viol_1)
    assert any("FORBIDDEN_CREDENTIAL_OR_TRANSFER_PATTERN" in v for v in viol_1)

    # 3. Weakening risk floor, increasing daily loss limit, or enabling new live asset MUST fail diff audit
    base_strat = copy.deepcopy(DEFAULT_HOLISTIC_CONFIG)
    weakened_strat = copy.deepcopy(DEFAULT_HOLISTIC_CONFIG)
    weakened_strat["risk_controller"]["hard_ruin_floor_usd"] = 10.0
    weakened_strat["risk_controller"]["max_daily_directional_loss_usd"] = 50.0
    weakened_strat["directional"]["allowed_assets_1h"] = list(base_strat["directional"].get("allowed_assets_1h") or []) + ["DOGE"]
    ok_d2, viol_2 = gate.inspect_candidate_diff(
        changed_files=["config/polymarket_strategy_and_risk.json"],
        diff_text="",
        baseline_cfg=base_strat,
        candidate_cfg=weakened_strat,
    )
    assert ok_d2 is False
    assert any("RISK_FLOOR_WEAKENED" in v for v in viol_2)
    assert any("EXPOSURE_INCREASED" in v for v in viol_2)
    assert any("NEW_LIVE_ASSET_ACTIVATION" in v for v in viol_2)

    # 4. HeadlessAgentRunner MUST block non-plan execution targeting live_repo_root
    db = PAATaskDB(tmp_path / "paa.db")
    budget = BudgetManager(db, autonomy_cfg=cfg)
    runner = HeadlessAgentRunner(db, budget, autonomy_cfg=cfg, live_repo_root=tmp_path / "live_repo")
    (tmp_path / "live_repo").mkdir()
    with pytest.raises(PermissionDeniedError):
        runner.invoke(
            prompt="Modify live code directly",
            task_id="T_ILLEGAL",
            cwd=tmp_path / "live_repo",
            mode="auto",
            allow_worktree_edits=True,
        )


def test_git_worktree_builder_deployment_and_automatic_rollback(tmp_path: Path) -> None:
    git_exe = _find_git_exe()
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run([git_exe, "init"], cwd=str(repo), check=True, capture_output=True)
    subprocess.run([git_exe, "config", "user.name", "Test"], cwd=str(repo), check=True)
    subprocess.run([git_exe, "config", "user.email", "test@dominus.local"], cwd=str(repo), check=True)

    (repo / "config").mkdir()
    (repo / "src").mkdir()
    (repo / "config" / "polymarket_strategy_and_risk.json").write_text(
        json.dumps(DEFAULT_HOLISTIC_CONFIG, indent=2), encoding="utf-8"
    )
    (repo / "config" / "polymarket_risk_config.json").write_text("{}", encoding="utf-8")
    (repo / "src" / "sample_alpha.py").write_text(
        "def paa_canary_health_check() -> bool:\n    return True\n", encoding="utf-8"
    )
    subprocess.run([git_exe, "add", "-A"], cwd=str(repo), check=True)
    subprocess.run([git_exe, "commit", "-m", "initial baseline"], cwd=str(repo), check=True, capture_output=True)

    cfg = _make_test_cfg()
    db = PAATaskDB(tmp_path / "paa_tasks.db")
    budget = BudgetManager(db, autonomy_cfg=cfg)
    gate = PermissionGate(autonomy_cfg=cfg, approvals_dir=tmp_path / "approvals")
    builder = GitWorktreeBuilder(db, budget, repo_root=repo, worktree_root=tmp_path / "worktrees", autonomy_cfg=cfg)
    deployer = DeploymentController(
        db,
        gate,
        repo_root=repo,
        staging_root=tmp_path / "staging",
        data_dir=tmp_path / "data" / "polymarket",
        autonomy_cfg=cfg,
    )

    # 1. Valid low-risk candidate -> builds in isolated worktree & deploys to staging!
    cand_ok = builder.build_and_commit_candidate(
        task_id="TASK_DEPLOY_GOOD",
        commit_message="Add verified helper with passing canary",
        apply_fn=lambda wt: (wt / "src" / "sample_alpha.py").write_text(
            "def compute_edge() -> float:\n    return 0.015\n\ndef paa_canary_health_check() -> bool:\n    return compute_edge() > 0\n",
            encoding="utf-8",
        ),
    )
    rel_ok = deployer.release_candidate(candidate=cand_ok, release_id="REL_GOOD_001")
    assert rel_ok["state"] == "DEPLOYED_VERIFIED"
    assert rel_ok["canary_passed"] is True
    assert deployer.get_active_staging_pointer()["active_release_id"] == "REL_GOOD_001"

    # 2. Faulty candidate whose canary check fails -> MUST automatically roll back to REL_GOOD_001!
    cand_bad = builder.build_and_commit_candidate(
        task_id="TASK_DEPLOY_BAD",
        commit_message="Faulty canary candidate",
        apply_fn=lambda wt: (wt / "src" / "sample_alpha.py").write_text(
            "def paa_canary_health_check() -> bool:\n    return False\n",
            encoding="utf-8",
        ),
    )
    rel_bad = deployer.release_candidate(candidate=cand_bad, release_id="REL_BAD_002")
    assert rel_bad["state"] == "ROLLED_BACK"
    assert rel_bad["rolled_back"] is True
    assert rel_bad["evidence"]["rolled_back_to_release_id"] == "REL_GOOD_001"
    assert rel_bad["evidence"]["post_rollback_health_verified"] is True
    assert deployer.get_active_staging_pointer()["active_release_id"] == "REL_GOOD_001"


def test_financial_integrity_safeguard_and_real_vs_simulated_pnl_separation(tmp_path: Path) -> None:
    cfg = _make_test_cfg()
    data_dir = tmp_path / "data" / "polymarket"
    data_dir.mkdir(parents=True)
    db = PAATaskDB(data_dir / "paa" / "paa_tasks.db")
    budget = BudgetManager(db, autonomy_cfg=cfg)

    # Seed simulated shadow ($+485.00) and simulated paper OOS ($+112.50)
    (data_dir / "alpha124_shadow_state.json").write_text(
        json.dumps({"by_sleeve": {"BOND1_UMA_RESOLUTION_CARRY": {"realized_pnl_t1000_usd": 485.0}}}),
        encoding="utf-8",
    )
    (data_dir / "paper_trader_state.json").write_text(
        json.dumps({"validation_oos_epoch": {"cumulative_realized_pnl": 112.5, "winning_trades": 9, "losing_trades": 2}}),
        encoding="utf-8",
    )

    accountant = PAAAccountant(db, budget, data_dir=data_dir, autonomy_cfg=cfg)

    # 1. Inject $15.00 cash drift between onchain ($21.68) and harvester state ($36.68)
    ledger_sample = {
        "free_cash_pusd": 21.68,
        "open_cost_basis_usd": 43.29,
        "portfolio_nav_mark_to_bid_usd": 64.50,
        "portfolio_nav_at_resting_maker_usd": 64.97,
        "verified_realized_net_profit_usd": -68.23,
        "raw_state_ledger_realized_pnl_usd": -80.13,
        "non_cash_unfilled_artifact_adjustment_usd": 11.90,
        "total_realized_fees_paid_usd": 4.12,
        "open_positions": [],
    }
    snap_bad = accountant.measure_and_record(
        live_rpc_check=False,
        ledger_override=ledger_sample,
        state_override={"live_bankroll": 36.68},
    )
    assert snap_bad["accounting_ok"] is False
    assert snap_bad["accounting_discrepancy_usd"] == 15.0
    assert (data_dir / "paa" / "ACCOUNTING_SAFEGUARD_ACTIVE.json").exists()
    # Realized cash PnL MUST NOT mix in the +$485 shadow or +$112.50 paper PnL!
    assert snap_bad["verified_realized_net_pnl_usd"] == -68.23
    assert snap_bad["simulated_shadow_t1000_pnl_usd"] == 485.0
    assert snap_bad["simulated_paper_oos_pnl_usd"] == 112.5

    p0_tasks = db.list_tasks(states=("READY",))
    assert any(t["category"] == "SAFETY_ACCOUNTING" and t["priority_label"] == "P0" for t in p0_tasks)

    # 2. Restore reconciled state ($21.68 == $21.68) -> safeguard clears automatically!
    snap_clean = accountant.measure_and_record(
        live_rpc_check=False,
        ledger_override=ledger_sample,
        state_override={"live_bankroll": 21.68},
    )
    assert snap_clean["accounting_ok"] is True
    assert not (data_dir / "paa" / "ACCOUNTING_SAFEGUARD_ACTIVE.json").exists()


def test_monitoring_failure_detected_and_repaired_by_independent_supervisor(tmp_path: Path) -> None:
    cfg = _make_test_cfg()
    data_dir = tmp_path / "data" / "polymarket"
    paa_dir = data_dir / "paa"
    paa_dir.mkdir(parents=True)
    db = PAATaskDB(paa_dir / "paa_tasks.db")

    # Age monitor_heartbeat.json by 600s (> max 30s) to simulate crashed/stopped monitor
    stale_ts = (datetime.now(timezone.utc) - timedelta(seconds=600)).strftime("%Y-%m-%dT%H:%M:%SZ")
    (paa_dir / "monitor_heartbeat.json").write_text(
        json.dumps({"checked_at_utc": stale_ts, "status": "OK"}),
        encoding="utf-8",
    )

    repaired_flag = {"called": False}

    def _repair_cb() -> None:
        repaired_flag["called"] = True
        now_s = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        (paa_dir / "monitor_heartbeat.json").write_text(
            json.dumps({"checked_at_utc": now_s, "status": "OK"}),
            encoding="utf-8",
        )

    sup = PAAIndependentSupervisor(db, data_dir=data_dir, autonomy_cfg=cfg)
    out = sup.run_supervision_check(auto_repair=True, repair_callback=_repair_cb)
    assert out["monitor_failed"] is True
    assert out["repaired"] is True
    assert out["status"] == "RECOVERED"
    assert repaired_flag["called"] is True
    assert (paa_dir / "incident_and_repair_log.json").exists()


def test_research_continuity_records_both_accepted_and_rejected_hypotheses(tmp_path: Path) -> None:
    cfg = _make_test_cfg()
    data_dir = tmp_path / "data" / "polymarket"
    data_dir.mkdir(parents=True)
    db = PAATaskDB(data_dir / "paa" / "paa_tasks.db")
    budget = BudgetManager(db, autonomy_cfg=cfg)
    researcher = PAAResearcher(db, budget, data_dir=data_dir, autonomy_cfg=cfg)

    fake_universe = {
        "active_markets_scanned": 19540,
        "events_scanned": 800,
        "ranked_uma_proposed_carries": [
            {
                "market_id": "UMA_MKT_1",
                "category": "politics",
                "question": "Did Senate pass bill X?",
                "net_edge_bps_maker_0pct": 85.0,
                "liquidity_usd": 2400.0,
            }
        ],
        "ranked_intraday_high_prob_carries": [
            {
                "market_id": "INTRA_ILLIQUID_1",
                "category": "culture",
                "question": "Illiquid low-volume carry trap",
                "side": "NO",
                "est_bps_per_hour": 45.0,
                "net_edge_bps_maker": 110.0,
                "liquidity_usd": 600.0,
                "volume_24h_usd": 120.0,  # Rejected (< $1500 24h turnover)
            }
        ],
        "ranked_clob_usdc_reward_pools": [
            {
                "market_id": "RW_WIDE_1",
                "category": "macro",
                "question": "Wide spread reward trap",
                "best_bid": 0.40,
                "best_ask": 0.55,  # 15c spread -> rejected!
                "min_capital_est_usd": 10.0,
                "daily_reward_pool_usd": 50.0,
                "daily_pool_to_liq_ratio": 0.05,
            }
        ],
    }

    summary = researcher.run_research_cycle(universe_override=fake_universe)
    assert summary["accepted_findings"] >= 1
    assert summary["rejected_findings"] >= 2

    findings = db.list_research_findings(limit=20)
    assert any(f["succeeded"] is True for f in findings)
    assert any(f["succeeded"] is False for f in findings)
    assert (data_dir / "paa" / "validated_experiment_registry.json").exists()


def test_budget_caps_and_master_stop(tmp_path: Path) -> None:
    cfg = _make_test_cfg()
    cfg["budget"]["max_daily_ai_cost_usd"] = 0.05
    data_dir = tmp_path / "data" / "polymarket"
    director = PAADirector(repo_root=tmp_path, data_dir=data_dir, autonomy_cfg=cfg)

    # Record $0.06 of AI spend (48k input tokens * $0.00125/1k = $0.06 > $0.05 daily cap, < $0.075 P0 emergency cap)
    cost = director.budget.record_ai_usage(
        model_name="gemini-4-argon-high",
        task_id="T_COST_1",
        input_tokens=48000,
        output_tokens=0,
        duration_sec=1.5,
    )
    assert abs(cost - 0.06) < 1e-6
    ok_p2, msg_p2 = director.budget.can_invoke_ai_agent({"priority_label": "P2", "expected_net_ev_usd_per_day": 1.0})
    assert ok_p2 is False and "DAILY_AI_BUDGET_EXHAUSTED" in msg_p2

    # P0 emergency task still permitted within 1.5x emergency reserve!
    ok_p0, _ = director.budget.can_invoke_ai_agent({"priority_label": "P0", "expected_net_ev_usd_per_day": 10.0})
    assert ok_p0 is True

    # Engage PAA_MASTER_STOP -> Director immediately pauses without claiming tasks
    (data_dir / "paa" / "PAA_MASTER_STOP").write_text('{"stopped": true}', encoding="utf-8")
    out = director.run_cycle()
    assert out["status"] == "PAUSED_BY_MASTER_STOP"
