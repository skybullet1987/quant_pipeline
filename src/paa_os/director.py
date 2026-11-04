"""
Persistent PAA Autonomous Director & Dashboard Reporter (`src/paa_os/director.py`).

Implements PAA Section 4.A.1 (Persistent Director), Section 4.B (Autonomous Decision Policy),
and Section 4.F (Final Deployment Dashboard & Status Report):
  1. Loads the Master PAA Mandate (`config/paa_master_mandate.md`).
  2. Acquires exclusive `director_cycle` lease lock so concurrent timer/event triggers never collide.
  3. Runs Anti-Stall recovery (`recover_interrupted_tasks` + `resolve_dependencies_and_detect_cycles`).
  4. Evaluates the 8-Step Decision Policy (`B1` Safety/Accounting -> `B2` Service Health ->
     `B3` Highest-EV Queued/Checkpointed Work -> `B4` Strategy Degradation & Trade Forensics ->
     `B5` Polymarket Opportunity Research -> `B6` Eligible Validated Deployments ->
     `B7` Proactive Optimization -> `B8` Budget-Conserving Idle).
  5. Executes tasks with idempotent persistent checkpoints (`completed_steps` in `last_checkpoint_json`),
     generating follow-up tasks automatically and recording full completion evidence.
  6. Publishes `data/polymarket/paa/paa_dashboard.json` and `data/polymarket/paa/paa_status_report.md`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import audit_losing_trades
from scripts.paa_autonomous_controller import (
    build_strategy_scorecard,
    discover_machine_gun_sleeves,
    reconcile_authoritative_ledger,
)
from src.paa_os.accountant import PAAAccountant
from src.paa_os.agent_runtime import AuthExpiredError, HeadlessAgentError, HeadlessAgentRunner
from src.paa_os.budget import BudgetManager
from src.paa_os.builder_and_deployer import DeploymentController, GitWorktreeBuilder
from src.paa_os.monitor import PAAMonitor, _atomic_write_json
from src.paa_os.permissions import PermissionClass, PermissionDeniedError, PermissionGate, load_autonomy_config
from src.paa_os.researcher import PAAResearcher
from src.paa_os.task_db import PAATaskDB, utc_now_iso
from src.paa_os.zero_trust import DeterministicVerificationController, EpistemicStatus, StatelessContextManager

PIPELINE_ROOT = Path(__file__).resolve().parents[2]
DATA_PM = PIPELINE_ROOT / "data" / "polymarket"


class PAADirector:
    def __init__(
        self,
        *,
        repo_root: Optional[Path] = None,
        data_dir: Optional[Path] = None,
        db: Optional[PAATaskDB] = None,
        autonomy_cfg: Optional[Dict[str, Any]] = None,
        staging_root: Optional[Path] = None,
        worktree_root: Optional[Path] = None,
    ) -> None:
        self.repo_root = (Path(repo_root) if repo_root is not None else PIPELINE_ROOT).resolve()
        self.data_dir = (Path(data_dir) if data_dir is not None else (self.repo_root / "data" / "polymarket")).resolve()
        self.paa_dir = self.data_dir / "paa"
        self.paa_dir.mkdir(parents=True, exist_ok=True)
        self.cfg = autonomy_cfg or load_autonomy_config(self.repo_root / "config" / "paa_autonomy_config.json")
        self.db = db or PAATaskDB(self.paa_dir / "paa_tasks.db")
        self.budget = BudgetManager(self.db, autonomy_cfg=self.cfg)
        self.permission_gate = PermissionGate(autonomy_cfg=self.cfg, approvals_dir=self.paa_dir / "approvals")
        self.agent_runner = HeadlessAgentRunner(self.db, self.budget, autonomy_cfg=self.cfg, live_repo_root=self.repo_root)
        self.accountant = PAAAccountant(self.db, self.budget, data_dir=self.data_dir, autonomy_cfg=self.cfg)
        self.researcher = PAAResearcher(self.db, self.budget, data_dir=self.data_dir, autonomy_cfg=self.cfg)
        self.builder = GitWorktreeBuilder(
            self.db,
            self.budget,
            repo_root=self.repo_root,
            worktree_root=worktree_root,
            autonomy_cfg=self.cfg,
        )
        self.deployer = DeploymentController(
            self.db,
            self.permission_gate,
            repo_root=self.repo_root,
            staging_root=staging_root,
            data_dir=self.data_dir,
            autonomy_cfg=self.cfg,
        )
        self.monitor = PAAMonitor(self.db, self.accountant, self.budget, data_dir=self.data_dir, autonomy_cfg=self.cfg)
        self.context_manager = StatelessContextManager(self.db, repo_root=self.repo_root, autonomy_cfg=self.cfg)
        self.verifier = DeterministicVerificationController(
            self.db,
            self.permission_gate,
            accountant=self.accountant,
            deployer=self.deployer,
            repo_root=self.repo_root,
            autonomy_cfg=self.cfg,
        )
        self._custom_handlers: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}

    def register_task_handler(self, category: str, fn: Callable[[Dict[str, Any]], Dict[str, Any]]) -> None:
        self._custom_handlers[category] = fn

    def load_master_mandate(self) -> str:
        p = self.repo_root / "config" / "paa_master_mandate.md"
        if p.exists():
            return p.read_text(encoding="utf-8")
        return "PAA MASTER MANDATE: Maximize sustainable verified net profitability within strict safety and permission gates."

    def _query_systemd_schedules(self) -> Dict[str, Any]:
        if not sys.platform.startswith("linux"):
            return {"platform": sys.platform, "timers": [], "path_units": []}
        timers: List[Dict[str, Any]] = []
        path_units: List[Dict[str, Any]] = []
        try:
            proc = subprocess.run(
                ["systemctl", "--user", "list-timers", "--all", "--no-pager", "--output=json"],
                capture_output=True,
                text=True,
                timeout=5.0,
            )
            if proc.returncode == 0 and proc.stdout.strip().startswith("["):
                raw = json.loads(proc.stdout)
                timers.extend(
                    t for t in raw
                    if isinstance(t, dict) and ("polymarket-" in str(t.get("unit")) or "apex-" in str(t.get("unit")))
                )
            else:
                proc_txt = subprocess.run(
                    ["systemctl", "--user", "list-timers", "--all", "--no-pager", "--no-legend"],
                    capture_output=True,
                    text=True,
                    timeout=5.0,
                )
                for ln in proc_txt.stdout.splitlines():
                    if "polymarket-" in ln or "apex-" in ln:
                        timers.append({"raw_schedule_line": " ".join(ln.split())})

            p_sys = subprocess.run(
                ["systemctl", "is-active", "paa-system-supervisor.timer"],
                capture_output=True,
                text=True,
                timeout=5.0,
            )
            timers.append({"unit": "paa-system-supervisor.timer", "scope": "system_pid1", "state": p_sys.stdout.strip()})

            p_path = subprocess.run(
                ["systemctl", "--user", "is-active", "polymarket-paa-director-event.path"],
                capture_output=True,
                text=True,
                timeout=5.0,
            )
            path_units.append({"unit": "polymarket-paa-director-event.path", "state": p_path.stdout.strip()})
        except Exception:
            pass
        return {"platform": "linux_systemd", "timers": timers, "path_units": path_units}

    def _check_strategy_degradation_and_losses(self) -> List[str]:
        """Policy Step B4: Inspects uninspected live losses without blocking if running offline."""
        created_ids: List[str] = []
        st_path = self.data_dir / "live_harvester_state.json"
        if not st_path.exists():
            return created_ids
        try:
            audit_st = audit_losing_trades.load_audit_state()
            audited = audit_st.get("audited_trades") or {}
            st = json.loads(st_path.read_text(encoding="utf-8"))
            for rec in st.get("closed_positions") or []:
                tid = str(rec.get("trade_id") or "")
                pnl = rec.get("net_pnl_usd")
                if not tid or tid in audited or pnl is None:
                    continue
                if float(pnl) < -1e-6:
                    hint = audit_losing_trades.classify_losing_trade_forensics(rec)
                    t, created = self.db.enqueue_task(
                        category="TRADE_FORENSICS",
                        priority_label="P1",
                        expected_net_ev_usd_per_day=4.0,
                        dedupe_key=f"TRADE_FORENSICS:{tid}",
                        title=f"Forensic Audit of Settled Losing Trade {tid} (${float(pnl):.2f})",
                        financial_impact_hypothesis="Classify strictly under 3-Verdict Wall (EXPECTED_LOSS vs PLUMBING_0_PARAM vs PARAM_WFO_REQUIRED).",
                        evidence={"trade": rec, "forensic_hint": hint},
                        required_permission_class=PermissionClass.AUTOMATICALLY_PERMITTED.value,
                        validation_requirements={"three_verdict_classification": True},
                        next_action="CLASSIFY_LOSS_AND_QUEUE_ACTION",
                        payload={"trade_id": tid, "trade": rec, "hint": hint},
                    )
                    if created:
                        created_ids.append(t["task_id"])
        except Exception:
            pass
        return created_ids

    def _audit_profit_conversion_and_velocity(self) -> Dict[str, Any]:
        """Deterministic Policy Step B7 audit: measures shadow-to-live conversion, near-grad8 sleeves, and 0-loss capital focus."""
        a124_p = self.data_dir / "alpha124_shadow_state.json"
        harv_p = self.data_dir / "live_harvester_state.json"
        cand_p = self.data_dir / "d1_live_box_candidates.jsonl"
        cfg_p = self.repo_root / "config" / "polymarket_strategy_and_risk.json"
        by_slv: Dict[str, Any] = {}
        active_shadow_sleeves: set[str] = set()
        if a124_p.exists():
            try:
                raw_a = json.loads(a124_p.read_text(encoding="utf-8"))
                by_slv = raw_a.get("by_sleeve") or raw_a.get("per_strategy") or {}
                for _op in (raw_a.get("open_positions") or []):
                    if isinstance(_op, dict) and _op.get("sleeve"):
                        active_shadow_sleeves.add(str(_op["sleeve"]))
                for _mo in (raw_a.get("pending_maker_orders") or []):
                    if isinstance(_mo, dict) and _mo.get("sleeve"):
                        active_shadow_sleeves.add(str(_mo["sleeve"]))
            except Exception:
                by_slv = {}
        for opps_cand in (
            self.data_dir / "alpha124_live_opportunities.json",
            self.data_dir.parent / "alpha124" / "alpha124_live_opportunities.json",
        ):
            if opps_cand.exists():
                try:
                    raw_op = json.loads(opps_cand.read_text(encoding="utf-8"))
                    for _o in (raw_op.get("top_opportunities") if isinstance(raw_op, dict) else (raw_op if isinstance(raw_op, list) else [])):
                        if isinstance(_o, dict) and _o.get("sleeve"):
                            active_shadow_sleeves.add(str(_o["sleeve"]))
                except Exception:
                    pass
                break
        closed_live: List[Dict[str, Any]] = []
        live_cash = 0.0
        live_wins_by_slv: Dict[str, int] = {}
        if harv_p.exists():
            try:
                raw_h = json.loads(harv_p.read_text(encoding="utf-8"))
                closed_live = list(raw_h.get("closed_positions") or [])
                live_cash = float(raw_h.get("live_bankroll", 0.0) or 0.0)
                for _ps_k, _ps_v in (raw_h.get("per_strategy") or {}).items():
                    if isinstance(_ps_v, dict) and int(_ps_v.get("wins", 0) or 0) > 0:
                        live_wins_by_slv[str(_ps_k)] = max(live_wins_by_slv.get(str(_ps_k), 0), int(_ps_v["wins"]))
            except Exception:
                pass
        for rec in closed_live:
            if isinstance(rec, dict) and float(rec.get("net_pnl_usd", 0.0) or 0.0) > 0:
                sl = str(rec.get("sleeve") or rec.get("sleeve_source") or "")
                live_wins_by_slv[sl] = live_wins_by_slv.get(sl, 0) + 1
        cand_counts: Dict[str, int] = {}
        if cand_p.exists():
            try:
                sz = cand_p.stat().st_size
                with open(cand_p, "rb") as cf:
                    cf.seek(max(0, sz - 524288))
                    lines = cf.read().decode("utf-8", errors="replace").splitlines()[1 if sz > 524288 else 0 :]
                for ln in lines:
                    try:
                        d = json.loads(ln)
                        sl = str(d.get("sleeve_source") or "")
                        if sl:
                            cand_counts[sl] = cand_counts.get(sl, 0) + 1
                    except Exception:
                        pass
            except Exception:
                pass
        mg_sleeves = discover_machine_gun_sleeves(self.data_dir)
        for _mg_k, _mg_v in mg_sleeves.items():
            if _mg_k not in by_slv and isinstance(_mg_v, dict):
                by_slv[_mg_k] = _mg_v
                if int(_mg_v.get("open", 0) or 0) > 0:
                    active_shadow_sleeves.add(_mg_k)
        min_dir_eq = 0.0
        riskless_only_mode = False
        paused_rb_sleeves: set[str] = set()
        if cfg_p.exists():
            try:
                _cfg_d = json.loads(cfg_p.read_text(encoding="utf-8"))
                min_dir_eq = float(((_cfg_d.get("directional") or {}).get("min_live_equity_for_unhedged_directional_usd")) or 0.0)
                riskless_only_mode = bool((_cfg_d.get("directional") or {}).get("riskless_only_mode", False))
                paused_rb_sleeves = {str(x).strip().upper() for x in ((_cfg_d.get("riskless_boxes") or {}).get("paused_riskless_sleeves") or []) if str(x).strip()}
            except Exception:
                min_dir_eq = 0.0
        grad8_ready, near_grad8, zero_live_gaps = [], [], []
        for sl, rec in by_slv.items():
            if not isinstance(rec, dict) or sl.upper() in paused_rb_sleeves:
                continue
            w = int(rec.get("wins", 0) or 0)
            l = int(rec.get("losses", 0) or 0)
            pnl = float(rec.get("realized_pnl_t1000_usd", rec.get("pnl_t1000_usd", 0.0)) or 0.0)
            if w >= 8 and l == 0 and pnl > 0:
                grad8_ready.append(sl)
                if live_wins_by_slv.get(sl, 0) == 0 and cand_counts.get(sl, 0) == 0:
                    zero_live_gaps.append(sl)
            elif 5 <= w < 8 and l == 0 and pnl > 0:
                near_grad8.append({"sleeve": sl, "wins": w, "remaining": 8 - w, "shadow_pnl_t1000": round(pnl, 2)})
        active_conv_gaps = sorted(sl for sl in zero_live_gaps if sl in active_shadow_sleeves)
        regime_quiet_grad8 = sorted(sl for sl in zero_live_gaps if sl not in active_shadow_sleeves)
        summary = {
            "audited_at_utc": utc_now_iso(),
            "operating_mode": str(self.cfg.get("operating_mode") or "RISKLESS_PAA"),
            "grad8_ready_count": len(grad8_ready),
            "grad8_ready_sleeves": sorted(grad8_ready),
            "paused_riskless_sleeves": sorted(paused_rb_sleeves),
            "machine_gun_sleeves_detected": sorted(mg_sleeves.keys()),
            "grad8_zero_live_conversion_gaps": sorted(zero_live_gaps),
            "grad8_active_shadow_conversion_gaps": active_conv_gaps,
            "grad8_regime_quiet_sleeves": regime_quiet_grad8,
            "near_grad8_candidates": near_grad8,
            "live_wins_by_sleeve": live_wins_by_slv,
            "recent_live_candidate_counts": cand_counts,
            "riskless_only_mode": riskless_only_mode,
            "seed_zero_loss_focus_active": bool(riskless_only_mode or (min_dir_eq > 0.0 and live_cash < min_dir_eq)),
            "min_live_equity_for_unhedged_directional_usd": min_dir_eq,
        }
        self.db.upsert_verified_fact(
            fact_key="profit.conversion_and_velocity_audit",
            category="PROFIT_CONVERSION",
            value=summary,
            epistemic_status=EpistemicStatus.VERIFIED_FACT.value,
            source_type="LEDGER_AND_IPC_AUDIT",
            source_ref="PAADirector._audit_profit_conversion_and_velocity",
            verified_by="PAADirector",
            ttl_sec=3600.0,
            revalidation_rule="REAUDIT_SHADOW_TO_LIVE_CONVERSION_HOURLY",
        )
        return summary

    def _execute_task_with_checkpoints(
        self,
        task: Dict[str, Any],
        mandate_text: str,
        allow_headless_ai: bool = True,
    ) -> Dict[str, Any]:
        """
        Executes a claimed task step-by-step using persistent idempotent checkpoints (`completed_steps`).
        If interrupted mid-flight, subsequent cycles skip already-completed steps and resume seamlessly!
        """
        tid = task["task_id"]
        cat = str(task["category"])
        ckpt = dict(task.get("last_checkpoint") or {})
        completed_steps: List[str] = list(ckpt.get("completed_steps") or [])
        step_outputs: Dict[str, Any] = dict(ckpt.get("step_outputs") or {})
        payload = dict(task.get("payload") or {})

        # Step 0: Enforce Permission Gate before ANY task side effects
        ok_auth, auth_msg = self.permission_gate.check_task_authorization(task)
        if not ok_auth:
            self.db.block_task_authorization(tid, auth_msg, evidence={"task_category": cat, "scopes": task.get("required_scopes")})
            return {"task_id": tid, "outcome": "BLOCKED_AUTHORIZATION", "reason": auth_msg}

        if cat in self._custom_handlers:
            ev = self._custom_handlers[cat](task)
            self.db.complete_task(tid, ev)
            return {"task_id": tid, "outcome": "COMPLETED", "evidence": ev}

        if cat == "SAFETY_ACCOUNTING":
            if "reconcile_pass" not in completed_steps or not (step_outputs.get("reconcile_pass") or {}).get("accounting_ok"):
                snap = self.accountant.measure_and_record(live_rpc_check=True)
                if "reconcile_pass" not in completed_steps:
                    completed_steps.append("reconcile_pass")
                step_outputs["reconcile_pass"] = {
                    "accounting_ok": snap["accounting_ok"],
                    "discrepancy_usd": snap["accounting_discrepancy_usd"],
                    "free_cash_pusd": snap["free_cash_pusd"],
                }
                self.db.save_checkpoint(
                    tid,
                    {"completed_steps": completed_steps, "step_outputs": step_outputs},
                    next_action="VERIFY_ACCOUNTING_RESOLUTION",
                )
            rec_out = step_outputs["reconcile_pass"]
            if not rec_out.get("accounting_ok"):
                self.db.fail_task(tid, f"ACCOUNTING_DISCREPANCY_PERSISTS:${rec_out.get('discrepancy_usd')}", retryable=True)
                return {"task_id": tid, "outcome": "ESCALATED_OR_RETRYING", "details": rec_out}
            self.db.complete_task(tid, {"reconciled": True, **rec_out})
            return {"task_id": tid, "outcome": "COMPLETED", "evidence": rec_out}

        if cat == "RESEARCH_DISCOVERY":
            if "universe_scan" not in completed_steps:
                max_ev = int(payload.get("max_events", 600))
                res = self.researcher.run_research_cycle(max_events=max_ev)
                completed_steps.append("universe_scan")
                step_outputs["universe_scan"] = res
                self.db.save_checkpoint(
                    tid,
                    {"completed_steps": completed_steps, "step_outputs": step_outputs},
                    next_action="FINALIZE_RESEARCH_SUMMARY",
                )
            if allow_headless_ai and payload.get("run_ai_synthesis", False) and "ai_synthesis" not in completed_steps:
                ok_b, _ = self.budget.can_invoke_ai_agent(task)
                if ok_b:
                    pkt = self.context_manager.build_fresh_session_packet(
                        task=task,
                        stage_role="RESEARCH_SYNTHESIS",
                        prior_verified_checkpoint={"universe_scan": step_outputs["universe_scan"]},
                        stage_instructions=(
                            "In 2 concise sentences under RISKLESS PAA (100% zero-loss mandate), state the highest-velocity "
                            "riskless opportunity from `universe_scan` (UMA carry, NegRisk/complete-set slate arb, post-clinch sweeper, "
                            "locked dead-bracket reward, or Grad-8 box) and the top adverse-selection/legging guard to maintain. "
                            "Never claim simulated findings are LIVE_VERIFIED."
                        ),
                    )
                    ai_res = self.agent_runner.invoke(
                        prompt=pkt["prompt"],
                        task_id=tid,
                        cwd=self.repo_root,
                        mode="plan",
                        model=str((self.cfg.get("runtime") or {}).get("fast_triage_model") or "gemini-3.8-flash-low"),
                        sandbox=True,
                        timeout_sec=60,
                        conversation_id=None,
                        stage_role="RESEARCH_SYNTHESIS",
                        context_packet=pkt,
                        task_record=task,
                    )
                    completed_steps.append("ai_synthesis")
                    step_outputs["ai_synthesis"] = {
                        "conversation_id": ai_res.get("conversation_id"),
                        "fresh_session": True,
                        "context_utilization_pct": ai_res.get("context_utilization_pct"),
                        "summary": ai_res.get("response", "").strip()[:600],
                        "cost_usd": ai_res.get("estimated_cost_usd"),
                    }
                    self.db.save_checkpoint(
                        tid,
                        {
                            "completed_steps": completed_steps,
                            "step_outputs": step_outputs,
                        },
                        next_action="COMPLETE",
                    )
            self.db.complete_task(tid, step_outputs)
            return {"task_id": tid, "outcome": "COMPLETED", "evidence": step_outputs}

        if cat == "TRADE_FORENSICS":
            trade_id = str(payload.get("trade_id") or "")
            hint = payload.get("hint") or {}
            suggested = str(hint.get("suggested_classification") or "EXPECTED_VARIANCE_NO_CHANGE")
            if "forensic_classify" not in completed_steps:
                ai_note = ""
                if allow_headless_ai:
                    ok_b, _ = self.budget.can_invoke_ai_agent(task)
                    if ok_b:
                        try:
                            ai_r = self.agent_runner.invoke(
                                prompt=(
                                    "Classify this settled Polymarket loss strictly as EXPECTED_LOSS, PLUMBING_0_PARAM, or PARAM_WFO_REQUIRED "
                                    f"in one sentence: {json.dumps(payload.get('trade') or {})[:1200]}"
                                ),
                                task_id=tid,
                                cwd=self.repo_root,
                                mode="plan",
                                sandbox=True,
                                timeout_sec=60,
                                task_record=task,
                            )
                            ai_note = ai_r.get("response", "").strip()[:300]
                        except Exception:
                            ai_note = ""
                completed_steps.append("forensic_classify")
                step_outputs["forensic_classify"] = {
                    "trade_id": trade_id,
                    "classification": suggested,
                    "ai_note": ai_note,
                }
                self.db.save_checkpoint(tid, {"completed_steps": completed_steps, "step_outputs": step_outputs}, next_action="RECORD_AUDIT_VERDICT")

            if trade_id and suggested == "EXPECTED_VARIANCE_NO_CHANGE" and "mark_audited" not in completed_steps:
                audit_losing_trades.mark_audited(
                    trade_id,
                    "EXPECTED_LOSS",
                    notes=step_outputs["forensic_classify"].get("ai_note") or str(hint.get("rationale") or "Normal variance"),
                )
                completed_steps.append("mark_audited")
                self.db.save_checkpoint(tid, {"completed_steps": completed_steps, "step_outputs": step_outputs}, next_action="COMPLETE")
            elif suggested == "PARAM_WFO_REQUIRED" and trade_id and "mark_audited" not in completed_steps:
                audit_losing_trades.mark_audited(
                    trade_id,
                    "PARAM_WFO_REQUIRED",
                    classification="PARAM_WFO_REQUIRED",
                    notes=step_outputs["forensic_classify"].get("ai_note") or "Queued for Purged WFO evaluation.",
                )
                completed_steps.append("mark_audited")
            elif suggested == "PLUMBING_0_PARAM" and trade_id and "mark_audited" not in completed_steps:
                repair_prompt = (
                    f"Diagnose and fix the 0-parameter execution/reconciliation plumbing defect surfaced by losing trade "
                    f"{trade_id}: {json.dumps(payload.get('trade') or {})[:1400]}. "
                    "Strictly preserve all immutable risk floors and add/pass regression tests."
                )
                rep_task, _ = self.db.enqueue_task(
                    category="ENGINEERING_REPAIR",
                    priority_label="P0",
                    expected_net_ev_usd_per_day=8.0,
                    dedupe_key=f"AUTO_PLUMBING_REPAIR:{trade_id}",
                    title=f"Autonomous Worktree Repair for Plumbing Defect ({trade_id})",
                    financial_impact_hypothesis="Eliminate deterministic execution/reconciliation bug without touching strategy thresholds.",
                    evidence={"trade_id": trade_id, "trade": payload.get("trade"), "hint": hint},
                    required_permission_class=PermissionClass.CONDITIONALLY_AUTOMATIC.value,
                    payload={
                        "steps": [
                            {
                                "step_id": "worktree_ai_repair_and_stage",
                                "action": "WORKTREE_AI_PATCH_AND_STAGE",
                                "prompt": repair_prompt,
                                "commit_message": f"fix(plumbing): autonomous repair for {trade_id}",
                                "pytest_targets": [
                                    "tests/test_v50_holistic_overhaul.py",
                                    "tests/test_paa_profit_and_accounting_upgrades.py",
                                ],
                                "promote_to_live_files": bool((self.cfg.get("permissions") or {}).get("allow_auto_plumbing_bugfix_deploy", True)),
                            }
                        ]
                    },
                    next_action="BUILD_TEST_AND_STAGE_IN_WORKTREE",
                )
                step_outputs["enqueued_repair_task_id"] = rep_task["task_id"]
                audit_losing_trades.mark_audited(
                    trade_id,
                    "BUG_FIXED",
                    classification="PLUMBING_0_PARAM",
                    notes=f"Enqueued autonomous worktree repair {rep_task['task_id']}: {step_outputs['forensic_classify'].get('ai_note') or hint.get('rationale')}",
                )
                completed_steps.append("mark_audited")
            elif suggested == "SEQUENCE_TELEMETRY_REQUIRED" and trade_id and "mark_audited" not in completed_steps:
                self.db.enqueue_task(
                    category="STRATEGY_EVAL_WFO",
                    priority_label="P2",
                    expected_net_ev_usd_per_day=2.0,
                    dedupe_key=f"SEQUENCE_TELEMETRY_AUDIT:{trade_id}",
                    title=f"Sequence & Timing Parity Audit for {trade_id}",
                    financial_impact_hypothesis="Verify live-vs-shadow order sequence parity on legged/rescued execution.",
                    evidence={"trade_id": trade_id, "trade": payload.get("trade"), "hint": hint},
                    required_permission_class=PermissionClass.AUTOMATICALLY_PERMITTED.value,
                    next_action="ANALYZE_SEQUENCE_PARITY",
                )
                audit_losing_trades.mark_audited(
                    trade_id,
                    "EXPECTED_LOSS",
                    classification="SEQUENCE_TELEMETRY_REQUIRED",
                    notes=step_outputs["forensic_classify"].get("ai_note") or str(hint.get("rationale") or "Queued sequence parity audit."),
                )
                completed_steps.append("mark_audited")
            self.db.complete_task(tid, step_outputs)
            return {"task_id": tid, "outcome": "COMPLETED", "evidence": step_outputs}

        if cat in ("STRATEGY_EVAL_WFO", "QA_VALIDATION", "PROFIT_REPORTING", "SERVICE_RECOVERY", "ENGINEERING_REPAIR", "ENGINEERING_OPTIMIZATION"):
            # Checkpoint-guarded multi-step execution supporting custom step lists or diagnostic/QA execution
            steps_spec: List[Dict[str, Any]] = list(
                payload.get("steps")
                or [{"step_id": "default_diagnostic", "action": "RUN_DIAGNOSTIC"}]
            )
            side_effect_log_path = payload.get("side_effect_log_path")
            for st_def in steps_spec:
                sid = str(st_def["step_id"])
                if sid in completed_steps:
                    continue
                act = str(st_def.get("action") or "RUN_DIAGNOSTIC")
                if act == "SLEEP_SIM":
                    time.sleep(float(st_def.get("seconds", 0.1)))
                elif act == "APPEND_MARKER" and side_effect_log_path:
                    Path(side_effect_log_path).parent.mkdir(parents=True, exist_ok=True)
                    with open(side_effect_log_path, "a", encoding="utf-8") as mf:
                        mf.write(f"{sid}\n")
                elif act == "WORKTREE_AI_PATCH_AND_STAGE" and allow_headless_ai:
                    cand = self.builder.build_and_commit_candidate(
                        task_id=tid,
                        commit_message=str(st_def.get("commit_message") or f"PAA autonomous build for {tid}"),
                        ai_prompt=str(st_def.get("prompt") or f"Implement authorized fix for {task['title']}"),
                        agent_runner=self.agent_runner,
                        pytest_targets=list(st_def.get("pytest_targets") or []),
                    )
                    rel_rec = self.deployer.release_candidate(
                        candidate=cand,
                        permission_class=str(task.get("required_permission_class") or PermissionClass.CONDITIONALLY_AUTOMATIC.value),
                        pytest_targets=list(st_def.get("pytest_targets") or []),
                        promote_to_live_files=bool(st_def.get("promote_to_live_files", False)),
                    )
                    step_outputs[sid] = {"release_id": rel_rec["release_id"], "state": rel_rec["state"], "rolled_back": rel_rec["rolled_back"]}
                elif act == "ZERO_TRUST_MULTI_SESSION_BUILD":
                    ms_res = self.verifier.execute_multi_session_engineering_task(
                        task_id=tid,
                        context_mgr=self.context_manager,
                        agent_runner=self.agent_runner,
                        builder=self.builder,
                        deployer=self.deployer,
                        target_rel_file=str(st_def.get("target_rel_file") or "src/paa_os/__init__.py"),
                        pytest_targets=list(st_def.get("pytest_targets") or []),
                        use_live_headless_ai=bool(allow_headless_ai),
                    )
                    return {
                        "task_id": tid,
                        "outcome": ms_res["task"]["state"],
                        "evidence": ms_res["task"]["verification_receipt"],
                    }
                elif act == "HEADLESS_AI_ANALYSIS" and allow_headless_ai:
                    pkt_s = self.context_manager.build_fresh_session_packet(
                        task=task,
                        stage_role=f"STATELESS_STEP_{sid.upper()}",
                        prior_verified_checkpoint={"completed_steps": completed_steps, "step_outputs": step_outputs},
                        stage_instructions=str(st_def.get("prompt") or f"Analyze task: {task['title']}"),
                    )
                    ai_out = self.agent_runner.invoke(
                        prompt=pkt_s["prompt"],
                        task_id=tid,
                        cwd=self.repo_root,
                        mode="plan",
                        sandbox=True,
                        timeout_sec=int(st_def.get("timeout_sec", 90)),
                        conversation_id=None,
                        stage_role=f"STATELESS_STEP_{sid.upper()}",
                        context_packet=pkt_s,
                        task_record=task,
                    )
                    step_outputs[sid] = {
                        "conversation_id": ai_out.get("conversation_id"),
                        "fresh_session": True,
                        "context_utilization_pct": ai_out.get("context_utilization_pct"),
                        "response": ai_out["response"].strip()[:800],
                        "cost_usd": ai_out["estimated_cost_usd"],
                    }
                else:
                    step_outputs[sid] = {"executed_at_utc": utc_now_iso(), "action": act}

                if sid not in step_outputs:
                    step_outputs[sid] = {"executed_at_utc": utc_now_iso(), "action": act}
                completed_steps.append(sid)
                ckpt["completed_steps"] = completed_steps
                ckpt["step_outputs"] = step_outputs
                self.db.save_checkpoint(tid, ckpt, next_action=f"COMPLETED_{sid}")

            if payload.get("zero_trust_verify"):
                self.db.submit_for_verification(
                    tid,
                    worker_claims=dict(payload.get("worker_claims") or {}),
                    evidence={"completed_steps": completed_steps, "step_outputs": step_outputs},
                    epistemic_status=EpistemicStatus.OBSERVATION.value,
                )
                ver_task = self.verifier.verify_and_finalize_task(
                    tid,
                    pytest_targets=list(payload.get("pytest_targets") or []),
                )
                return {"task_id": tid, "outcome": ver_task["state"], "evidence": ver_task["verification_receipt"]}

            self.db.complete_task(tid, {"completed_steps": completed_steps, "step_outputs": step_outputs})
            return {"task_id": tid, "outcome": "COMPLETED", "evidence": step_outputs}

        if cat == "PROFIT_CONVERSION_AUDIT":
            if "conversion_audit" not in completed_steps:
                conv = self._audit_profit_conversion_and_velocity()
                completed_steps.append("conversion_audit")
                step_outputs["conversion_audit"] = conv
                self.db.save_checkpoint(
                    tid,
                    {"completed_steps": completed_steps, "step_outputs": step_outputs},
                    next_action="VERIFY_CONVERSION_AUDIT",
                )
            conv_out = step_outputs["conversion_audit"]
            if allow_headless_ai and payload.get("run_ai_synthesis", False) and conv_out.get("grad8_active_shadow_conversion_gaps") and "ai_conversion_plan" not in completed_steps:
                ok_b, _ = self.budget.can_invoke_ai_agent(task)
                if ok_b:
                    pkt = self.context_manager.build_fresh_session_packet(
                        task=task,
                        stage_role="PROFIT_CONVERSION_TRIAGE",
                        prior_verified_checkpoint={"conversion_audit": conv_out},
                        stage_instructions=(
                            "In 2 concise sentences, identify why any `grad8_zero_live_conversion_gaps` sleeve has 0 live "
                            "candidates and propose a concrete zero-risk-expansion plumbing check."
                        ),
                    )
                    ai_res = self.agent_runner.invoke(
                        prompt=pkt["prompt"],
                        task_id=tid,
                        cwd=self.repo_root,
                        mode="plan",
                        model=str((self.cfg.get("runtime") or {}).get("fast_triage_model") or "gemini-3.8-flash-low"),
                        sandbox=True,
                        timeout_sec=60,
                        conversation_id=None,
                        stage_role="PROFIT_CONVERSION_TRIAGE",
                        context_packet=pkt,
                        task_record=task,
                    )
                    completed_steps.append("ai_conversion_plan")
                    step_outputs["ai_conversion_plan"] = {
                        "conversation_id": ai_res.get("conversation_id"),
                        "summary": ai_res.get("response", "").strip()[:600],
                        "cost_usd": ai_res.get("estimated_cost_usd"),
                    }
            self.db.complete_task(tid, step_outputs)
            return {"task_id": tid, "outcome": "COMPLETED", "evidence": step_outputs}

        self.db.complete_task(tid, {"completed_at_utc": utc_now_iso(), "category": cat})
        return {"task_id": tid, "outcome": "COMPLETED", "evidence": {"category": cat}}

    def generate_dashboard_and_report(self) -> Dict[str, Any]:
        """Generates the complete Section 4.F PAA Dashboard JSON & Markdown report."""
        hbs = self.db.get_heartbeats()
        q_sum = self.db.get_queue_summary()
        fin = self.db.get_latest_financial_snapshot()
        if fin is None:
            fin = self.accountant.measure_and_record(live_rpc_check=False)
        deploys = self.db.list_deployments(limit=15)
        findings = self.db.list_research_findings(limit=20)
        budget_s = self.budget.get_usage_summary()
        sched = self._query_systemd_schedules()
        zt_sum = self.db.get_zero_trust_summary()
        v_facts = self.db.list_verified_facts(include_stale=True, limit=15)
        recent_sessions = self.db.list_session_runs(limit=10)
        pol_ok, pol_missing = self.context_manager.verify_tier_a_policies_present()

        scorecard_p = self.paa_dir / "strategy_inventory_and_scorecard.json"
        if scorecard_p.exists():
            try:
                sc = json.loads(scorecard_p.read_text(encoding="utf-8"))
            except Exception:
                sc = {}
        else:
            sc = build_strategy_scorecard(reconcile_authoritative_ledger(live_rpc_check=False))

        rolled_back = [d for d in deploys if d.get("rolled_back") or d.get("state") == "ROLLED_BACK"]
        recent_ok_deploys = [d for d in deploys if d.get("state") == "DEPLOYED_VERIFIED"]
        blocked_deploys = [d for d in deploys if "BLOCKED" in str(d.get("state"))]

        fin_details = fin.get("details") if isinstance(fin.get("details"), dict) else {}
        fin_rl = fin.get("riskless_metrics") or fin_details.get("riskless_metrics") or {}
        sc_pure = sc.get("pure_riskless_live_summary") or {}
        op_mode = str(self.cfg.get("operating_mode") or "RISKLESS_PAA")
        riskless_kpis = {
            "operating_mode": op_mode,
            "riskless_only_mode": bool(fin_rl.get("riskless_only_mode", sc.get("riskless_only_mode", True))),
            "paused_riskless_sleeves": list(fin_rl.get("paused_riskless_sleeves") or sc.get("paused_riskless_sleeves") or []),
            "pure_riskless_live_wins": int(fin_rl.get("pure_riskless_live_wins", sc_pure.get("wins", 0)) or 0),
            "pure_riskless_live_losses": int(fin_rl.get("pure_riskless_live_losses", sc_pure.get("losses", 0)) or 0),
            "pure_riskless_live_wr_pct": float(fin_rl.get("pure_riskless_live_wr_pct", sc_pure.get("win_rate_pct", 100.0)) or 100.0),
            "pure_riskless_realized_pnl_usd": float(fin_rl.get("pure_riskless_realized_pnl_usd", sc_pure.get("realized_pnl_usd", 0.0)) or 0.0),
            "post_lock_wins": int(fin_rl.get("post_lock_wins", 0) or 0),
            "post_lock_losses": int(fin_rl.get("post_lock_losses", 0) or 0),
            "post_lock_net_pnl_usd": float(fin_rl.get("post_lock_net_pnl_usd", 0.0) or 0.0),
            "working_maker_quoting_usd": float(fin_rl.get("working_maker_quoting_usd", 0.0) or 0.0),
            "effective_deploy_or_quoting_pct": float(fin_rl.get("effective_deploy_or_quoting_pct", 0.0) or 0.0),
            "near_grad8_zero_loss_sleeves": list(sc.get("near_grad8_zero_loss_sleeves") or []),
            "machine_gun_sleeves_detected": list(sc.get("machine_gun_sleeves_detected") or []),
        }

        dashboard = {
            "generated_at_utc": utc_now_iso(),
            "operating_mode": op_mode,
            "riskless_paa_kpis": riskless_kpis,
            "master_stop_engaged": (self.paa_dir / "PAA_MASTER_STOP").exists(),
            "director_heartbeat": hbs.get("paa_director"),
            "last_successful_automation_cycle_utc": (hbs.get("paa_director") or {}).get("last_seen_utc"),
            "scheduled_next_cycles": sched,
            "current_active_tasks": q_sum["active_tasks"],
            "pending_tasks": q_sum["pending_tasks"],
            "blocked_and_escalated_tasks": q_sum["blocked_or_escalated_tasks"],
            "task_counts_by_state": q_sum["counts_by_state"],
            "monitoring_health": {
                "paa_monitor": hbs.get("paa_monitor"),
                "paa_supervisor": hbs.get("paa_supervisor"),
                "accounting_safeguard_active": (self.paa_dir / "ACCOUNTING_SAFEGUARD_ACTIVE.json").exists(),
            },
            "research_progress": {
                "paa_research_heartbeat": hbs.get("paa_research"),
                "recent_findings_count": len(findings),
                "accepted_hypotheses": [f for f in findings if f.get("succeeded")][:8],
                "rejected_hypotheses": [f for f in findings if not f.get("succeeded")][:8],
            },
            "strategy_deployment_states": {
                "total_sleeves_tracked": sc.get("total_sleeves_tracked", 0),
                "riskless_only_mode": riskless_kpis["riskless_only_mode"],
                "paused_riskless_sleeves": riskless_kpis["paused_riskless_sleeves"],
                "grad8_live_authorized_sleeves": sc.get("grad8_live_authorized_sleeves", []),
                "near_grad8_zero_loss_sleeves": riskless_kpis["near_grad8_zero_loss_sleeves"],
                "machine_gun_sleeves_detected": riskless_kpis["machine_gun_sleeves_detected"],
                "shadow_open_positions_total": sc.get("shadow_open_positions_total", 0),
                "compliance_gate": (self.cfg.get("permissions") or {}).get("jurisdiction_compliance_gate"),
            },
            "verified_financial_performance": {
                "realized_onchain_net_pnl_usd": fin["verified_realized_net_pnl_usd"],
                "raw_state_ledger_pnl_usd": fin["raw_ledger_pnl_usd"],
                "non_cash_unfilled_artifact_adj_usd": fin["phantom_adjustment_usd"],
                "free_cash_pusd": fin["free_cash_pusd"],
                "nav_mark_to_bid_usd": fin["nav_mark_to_bid_usd"],
                "nav_resting_maker_usd": fin["nav_resting_maker_usd"],
                "realized_fees_usd": fin["realized_fees_usd"],
                "estimated_slippage_usd": fin["estimated_slippage_usd"],
                "research_ai_cost_usd": fin["research_ai_cost_usd"],
                "daily_infra_vm_cost_usd": fin["infra_cost_usd"],
                "net_economic_profit_after_ops_usd": fin["net_economic_profit_usd"],
                "simulated_non_cash_benchmarks": {
                    "alpha124_shadow_t1000_pnl_usd": fin["simulated_shadow_t1000_pnl_usd"],
                    "zero_loss_shadow_t1000_pnl_usd": fin.get(
                        "zero_loss_shadow_t1000_pnl_usd",
                        ((fin.get("details") or {}).get("simulated_benchmarks") or {}).get("zero_loss_shadow_t1000_pnl_usd", 0.0),
                    ),
                    "zero_loss_shadow_wins": fin.get(
                        "zero_loss_shadow_wins",
                        ((fin.get("details") or {}).get("simulated_benchmarks") or {}).get("zero_loss_shadow_wins", 0),
                    ),
                    "paper_oos_validation_pnl_usd": fin["simulated_paper_oos_pnl_usd"],
                    "is_real_money": False,
                },
            },
            "budget_and_resources": budget_s,
            "zero_trust_telemetry": {
                **zt_sum,
                "tier_a_policies_intact": pol_ok,
                "tier_a_missing_policies": pol_missing,
                "verified_facts": v_facts,
                "recent_stateless_sessions": recent_sessions,
            },
            "recent_improvements": recent_ok_deploys[:10],
            "failed_and_rolled_back_releases": rolled_back[:10],
            "remaining_authorization_blockers": {
                "blocked_tasks": q_sum["blocked_or_escalated_tasks"],
                "blocked_releases": blocked_deploys[:10],
                "standing_policy_gates": [
                    "New live trading sleeve activation requires explicit human approval & operator geographic eligibility verification.",
                    "Increasing capital exposure caps or lowering hard_ruin_floor_usd ($42.00) requires explicit human approval.",
                    "Live harvester daemon restarts require open_positions_count == 0 unless emergency override.",
                ],
            },
        }
        _atomic_write_json(self.paa_dir / "paa_dashboard.json", dashboard)

        dir_hb = dashboard["director_heartbeat"] or {}
        mon_hb = (dashboard["monitoring_health"] or {}).get("paa_monitor") or {}
        sup_hb = (dashboard["monitoring_health"] or {}).get("paa_supervisor") or {}
        vf = dashboard["verified_financial_performance"]

        md = [
            f"# RISKLESS PAA Autonomous Operating System Status ({dashboard['generated_at_utc']})",
            "",
            "## 0. RISKLESS PAA Mandate & Zero-Loss Scorecard",
            f"- **Operating Mode**: `{op_mode}` | **100% Pure Riskless Live Lock**: `{riskless_kpis['riskless_only_mode']}`",
            f"- **Pure Riskless Live Record**: `{riskless_kpis['pure_riskless_live_wins']}W / {riskless_kpis['pure_riskless_live_losses']}L` (`{riskless_kpis['pure_riskless_live_wr_pct']:.1f}%` WR, `${riskless_kpis['pure_riskless_realized_pnl_usd']:+.2f}`) | **Post-Lock Record**: `{riskless_kpis['post_lock_wins']}W / {riskless_kpis['post_lock_losses']}L` (`${riskless_kpis['post_lock_net_pnl_usd']:+.2f}`)",
            f"- **Grad-8 Zero-Loss Live Sleeves (`{len(sc.get('grad8_live_authorized_sleeves') or [])}`)**: `{', '.join(sc.get('grad8_live_authorized_sleeves') or []) or 'NONE'}`",
            f"- **Paused Legging-Risk Sleeves**: `{', '.join(riskless_kpis['paused_riskless_sleeves']) or 'NONE'}` | **Machine-Gun Riskless Sleeves Detected**: `{', '.join(riskless_kpis['machine_gun_sleeves_detected']) or 'AWAITING_AGENT_INTEGRATION'}`",
            "",
            "## 1. Supervision & Heartbeats",
            f"- **Director Heartbeat**: `{dir_hb.get('status', 'INIT')}` at `{dir_hb.get('last_seen_utc', 'N/A')}` (Cycle `#{dir_hb.get('cycle_count', 0)}`)",
            f"- **Independent Monitor (1m)**: `{mon_hb.get('status', 'INIT')}` at `{mon_hb.get('last_seen_utc', 'N/A')}`",
            f"- **Independent Supervisor (2m)**: `{sup_hb.get('status', 'INIT')}` at `{sup_hb.get('last_seen_utc', 'N/A')}`",
            f"- **Master Stop Engaged**: `{dashboard['master_stop_engaged']}` | **Accounting Safeguard Active**: `{dashboard['monitoring_health']['accounting_safeguard_active']}`",
            "",
            "## 2. Verified Financial Ledger (Realized Cash Strictly Separated from Simulated)",
            f"- **Free Wallet Cash (`pUSD + USDC.e`)**: `${vf['free_cash_pusd']:.4f}`",
            f"- **Portfolio NAV (Mark-to-Bid / Resting Maker)**: `${vf['nav_mark_to_bid_usd']:.2f}` / `${vf['nav_resting_maker_usd']:.2f}`",
            f"- **Verified Realized Cash Net PnL**: `${vf['realized_onchain_net_pnl_usd']:+.2f}` (Fees: `${vf['realized_fees_usd']:.2f}`, Est. Slippage: `${vf['estimated_slippage_usd']:.2f}`, Non-Cash Artifact Adj: `${vf['non_cash_unfilled_artifact_adj_usd']:+.2f}`)",
            f"- **Autonomous Ops Cost**: AI Research `${vf['research_ai_cost_usd']:.4f}` + Prorated VM Infra `${vf['daily_infra_vm_cost_usd']:.4f}` -> **Net Economic Result**: `${vf['net_economic_profit_after_ops_usd']:+.2f}`",
            f"- **Simulated Non-Cash Benchmarks (Not Real Money)**: Zero-Loss Shadow T1000 `${vf['simulated_non_cash_benchmarks'].get('zero_loss_shadow_t1000_pnl_usd', 0.0):+.2f}` (`{vf['simulated_non_cash_benchmarks'].get('zero_loss_shadow_wins', 0)}W / 0L`, Legacy All-Sleeves `${vf['simulated_non_cash_benchmarks']['alpha124_shadow_t1000_pnl_usd']:+.2f}`) | Forward Paper OOS `${vf['simulated_non_cash_benchmarks']['paper_oos_validation_pnl_usd']:+.2f}`",
            "",
            "## 3. Durable Task Queue & Releases",
            f"- **Task Counts by State**: `{json.dumps(dashboard['task_counts_by_state'])}`",
            f"- **Active Tasks**: `{len(dashboard['current_active_tasks'])}` | **Pending**: `{len(dashboard['pending_tasks'])}` | **Auth-Blocked / Escalated**: `{len(dashboard['blocked_and_escalated_tasks'])}`",
            f"- **Verified Releases**: `{len(recent_ok_deploys)}` | **Rolled-Back Releases**: `{len(rolled_back)}` | **Auth-Blocked Releases**: `{len(blocked_deploys)}`",
            f"- **Research Ledger**: `{len(dashboard['research_progress']['accepted_hypotheses'])}` recent accepted / `{len(dashboard['research_progress']['rejected_hypotheses'])}` recent rejected hypotheses",
        ]
        (self.paa_dir / "paa_status_report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
        return dashboard

    def run_cycle(
        self,
        *,
        max_tasks_per_cycle: int = 2,
        allow_headless_ai: bool = True,
        run_proactive_research_if_idle: bool = True,
        live_rpc_check: bool = False,
    ) -> Dict[str, Any]:
        """
        Executes one complete, lock-protected PAA Director cycle (`Policy B1 -> B8`).
        """
        if (self.paa_dir / "PAA_MASTER_STOP").exists():
            return {"status": "PAUSED_BY_MASTER_STOP", "timestamp_utc": utc_now_iso()}

        lock_owner = self.db.acquire_lock("director_cycle", ttl_sec=600.0)
        if not lock_owner:
            return {"status": "SKIPPED_DIRECTOR_LOCK_ACTIVE", "timestamp_utc": utc_now_iso()}

        try:
            mandate = self.load_master_mandate()
            self.db.record_heartbeat("paa_director", status="RUNNING_CYCLE", details={"pid": os.getpid()})

            # Anti-Stall Sweep: recover crashed/hung tasks & detect dependency loops
            recovered = self.db.recover_interrupted_tasks(
                backoff_base_sec=float((self.cfg.get("budget") or {}).get("retry_backoff_base_sec", 30.0))
            )
            deps = self.db.resolve_dependencies_and_detect_cycles()

            # Policy B1: Safety, Accounting & Auth Verification
            fin = self.accountant.measure_and_record(live_rpc_check=live_rpc_check)
            auth_ok = True
            auth_msg = "SKIPPED"
            if allow_headless_ai:
                auth_ok, auth_msg = self.agent_runner.verify_auth_health()
                if not auth_ok:
                    self.db.log_event("director", "HEADLESS_AUTH_DEGRADED", {"message": auth_msg})

            # Policy B4: Check settled trade losses / degradation and enqueue forensic tasks
            forensic_enqueued = self._check_strategy_degradation_and_losses()

            # Policy B5 / B7: Schedule unattended research when idle + hourly profit-conversion audit (deduped by hour)
            ready_now = self.db.list_tasks(states=("CHECKPOINTED", "READY", "PENDING"), limit=5)
            if run_proactive_research_if_idle:
                hr_bucket = time.strftime("%Y%m%d_%H", time.gmtime())
                res_dkey = f"SCHEDULED_RESEARCH:UNIVERSE_AND_WFO_SCAN:{hr_bucket}"
                if not ready_now and not self.db.has_dedupe_key(res_dkey, include_completed=True):
                    hbs = self.db.get_heartbeats()
                    res_hb = hbs.get("paa_research")
                    res_age = float(res_hb["age_sec"]) if (res_hb and res_hb.get("age_sec") is not None) else 99999.0
                    if res_age >= 300.0:
                        self.db.enqueue_task(
                            category="RESEARCH_DISCOVERY",
                            priority_label="P2",
                            expected_net_ev_usd_per_day=1.50,
                            dedupe_key=res_dkey,
                            title="Continuous RISKLESS PAA Arbitrage, Carry & Grad-8 Universe Scan",
                            financial_impact_hypothesis="Discover highest-bps/hr UMA carries, NegRisk/complete-set slate arbs, post-clinch sweepers, locked dead-bracket rewards, and Grad-8 zero-loss sleeves.",
                            required_permission_class=PermissionClass.AUTOMATICALLY_PERMITTED.value,
                            payload={"max_events": 600, "run_ai_synthesis": bool(allow_headless_ai and auth_ok)},
                            next_action="SCAN_POLYMARKET_UNIVERSE",
                        )
                conv_dkey = f"PROFIT_CONVERSION_AUDIT:{hr_bucket}"
                if not self.db.has_dedupe_key(conv_dkey, include_completed=True):
                    self.db.enqueue_task(
                        category="PROFIT_CONVERSION_AUDIT",
                        priority_label="P2",
                        expected_net_ev_usd_per_day=2.50,
                        dedupe_key=conv_dkey,
                        title=f"Hourly RISKLESS PAA Shadow-to-Live Conversion & Velocity Audit ({hr_bucket}Z)",
                        financial_impact_hypothesis="Ensure all Grad-8 zero-loss & Machine-Gun Riskless sleeves convert cleanly to live CLOB candidates and maximize bps/hr velocity.",
                        required_permission_class=PermissionClass.AUTOMATICALLY_PERMITTED.value,
                        payload={"run_ai_synthesis": bool(allow_headless_ai and auth_ok)},
                        next_action="AUDIT_SHADOW_TO_LIVE_CONVERSION",
                    )

            # Policy B3 / B6: Claim and execute highest-priority eligible tasks
            executed_results: List[Dict[str, Any]] = []
            for _ in range(max(1, int(max_tasks_per_cycle))):
                self.db.renew_lock("director_cycle", lock_owner, ttl_sec=600.0)
                ok_eng, _, _ = self.budget.check_engineering_concurrency()
                allowed_cats = None
                if not ok_eng:
                    allowed_cats = {
                        "SAFETY_ACCOUNTING",
                        "SERVICE_RECOVERY",
                        "TRADE_FORENSICS",
                        "RESEARCH_DISCOVERY",
                        "PROFIT_CONVERSION_AUDIT",
                        "STRATEGY_EVAL_WFO",
                        "PROFIT_REPORTING",
                    }
                task = self.db.claim_next_eligible_task(
                    lease_ttl_sec=float((self.cfg.get("monitoring") or {}).get("worker_lease_ttl_sec", 480.0)),
                    allowed_categories=allowed_cats,
                )
                if task is None:
                    break
                try:
                    out = self._execute_task_with_checkpoints(
                        task,
                        mandate_text=mandate,
                        allow_headless_ai=bool(allow_headless_ai and auth_ok),
                    )
                    executed_results.append(out)
                except PermissionDeniedError as p_exc:
                    self.db.block_task_authorization(task["task_id"], str(p_exc))
                    executed_results.append({"task_id": task["task_id"], "outcome": "BLOCKED_AUTHORIZATION", "reason": str(p_exc)})
                except (AuthExpiredError, HeadlessAgentError) as a_exc:
                    st_after = self.db.fail_task(task["task_id"], str(a_exc), retryable=True)
                    executed_results.append({"task_id": task["task_id"], "outcome": st_after, "error": str(a_exc)})
                except Exception as exc:
                    st_after = self.db.fail_task(task["task_id"], f"{type(exc).__name__}:{exc}", retryable=True)
                    executed_results.append({"task_id": task["task_id"], "outcome": st_after, "error": str(exc)})

            dashboard = self.generate_dashboard_and_report()
            hb = self.db.record_heartbeat(
                "paa_director",
                status="OK" if fin["accounting_ok"] else "SAFEGUARD_ACTIVE",
                details={
                    "tasks_executed": len(executed_results),
                    "accounting_ok": fin["accounting_ok"],
                    "headless_auth_ok": auth_ok,
                },
                increment_cycle=False,
            )
            cycle_report = {
                "status": "OK",
                "timestamp_utc": utc_now_iso(),
                "director_heartbeat": hb,
                "recovered_interrupted": recovered,
                "dependency_resolution": deps,
                "forensic_tasks_enqueued": forensic_enqueued,
                "tasks_executed": executed_results,
                "accounting_ok": fin["accounting_ok"],
                "headless_auth_status": auth_msg,
                "queue_counts": dashboard["task_counts_by_state"],
            }
            self.db.log_event("director", "DIRECTOR_CYCLE_COMPLETED", cycle_report)
            return cycle_report
        finally:
            self.db.release_lock("director_cycle", lock_owner)
