#!/usr/bin/env python3
"""
Unified Command-Line Entrypoint for PROFIT ABOVE ALL (PAA) Autonomous Operating System (`scripts/paa_cli.py`).

Supports all scheduled systemd cadences, event-driven wakeups, status dashboards, and owner emergency controls:
  - `director-cycle`   (Every 15m + immediate `.path` event trigger)
  - `monitor-cycle`    (Every 1m independent health & accounting reconciliation)
  - `supervisor-cycle` (Every 2m independent Tier-2 monitor supervisor)
  - `scan-cycle`       (Every 5m full-ecosystem Polymarket opportunity & problem detector)
  - `hourly-opt`       (Every 1h strategy performance, latency & live-vs-sim parity analyzer)
  - `six-hour-eval`    (Every 6h research candidate evaluation, automated QA & staging checks)
  - `daily-report`     (Daily full profitability, ops-cost & portfolio report)
  - `weekly-review`    (Weekly Purged WFO/CPCV governance & architecture review)
  - `status`           (Generate & print live `paa_dashboard.json` status)
  - `enqueue`          (Enqueue a durable task into `paa_tasks.db`)
  - `emergency-stop`   (Engage `PAA_MASTER_STOP` and halt autonomy timers safely)
  - `resume`           (Clear `PAA_MASTER_STOP` and re-enable autonomy timers)
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

PIPELINE_ROOT = Path(__file__).resolve().parents[1]
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from scripts.paa_autonomous_controller import (
    build_strategy_scorecard,
    reconcile_authoritative_ledger,
)
from scripts.weekly_wfo_governance import evaluate_ledger_file
from src.paa_os.accountant import PAAAccountant
from src.paa_os.budget import BudgetManager
from src.paa_os.director import PAADirector
from src.paa_os.monitor import PAAIndependentSupervisor, PAAMonitor, _atomic_write_json
from src.paa_os.permissions import PermissionClass, build_isolated_worker_env, load_autonomy_config
from src.paa_os.researcher import PAAResearcher
from src.paa_os.task_db import PAATaskDB, utc_now_iso

PAA_USER_TIMERS = [
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


def _ensure_systemd_user_env() -> None:
    if sys.platform.startswith("linux"):
        uid = os.getuid()
        os.environ.setdefault("XDG_RUNTIME_DIR", f"/run/user/{uid}")
        os.environ.setdefault("DBUS_SESSION_BUS_ADDRESS", f"unix:path=/run/user/{uid}/bus")


def cmd_director_cycle(args: argparse.Namespace) -> int:
    _ensure_systemd_user_env()
    director = PAADirector()
    out = director.run_cycle(
        max_tasks_per_cycle=args.max_tasks,
        allow_headless_ai=not args.no_ai,
        run_proactive_research_if_idle=not args.no_proactive_research,
        live_rpc_check=args.live_rpc,
    )
    print(json.dumps(out, indent=2, default=str))
    return 0


def cmd_monitor_cycle(args: argparse.Namespace) -> int:
    _ensure_systemd_user_env()
    cfg = load_autonomy_config()
    db = PAATaskDB()
    budget = BudgetManager(db, autonomy_cfg=cfg)
    accountant = PAAAccountant(db, budget, autonomy_cfg=cfg)
    monitor = PAAMonitor(db, accountant, budget, autonomy_cfg=cfg)
    out = monitor.run_monitor_cycle(
        live_rpc_check=not args.offline,
        auto_recover_safe=not args.no_recover,
        check_network=not args.offline,
    )
    # Refresh dashboard snapshot lightly so external observers always see fresh 1m telemetry
    PAADirector(db=db, autonomy_cfg=cfg).generate_dashboard_and_report()
    print(json.dumps(out, indent=2, default=str))
    return 0


def cmd_supervisor_cycle(args: argparse.Namespace) -> int:
    _ensure_systemd_user_env()
    cfg = load_autonomy_config()
    db = PAATaskDB()
    sup = PAAIndependentSupervisor(db, autonomy_cfg=cfg)
    out = sup.run_supervision_check(auto_repair=not args.no_repair)
    print(json.dumps(out, indent=2, default=str))
    return 0


def cmd_scan_cycle(args: argparse.Namespace) -> int:
    _ensure_systemd_user_env()
    cfg = load_autonomy_config()
    db = PAATaskDB()
    if (PIPELINE_ROOT / "data" / "polymarket" / "paa" / "PAA_MASTER_STOP").exists():
        print(json.dumps({"status": "PAUSED_BY_MASTER_STOP"}, indent=2))
        return 0
    budget = BudgetManager(db, autonomy_cfg=cfg)
    researcher = PAAResearcher(db, budget, autonomy_cfg=cfg)
    res = researcher.run_research_cycle(max_events=args.max_events)
    fin = reconcile_authoritative_ledger(live_rpc_check=False)
    scorecard = build_strategy_scorecard(fin)
    _atomic_write_json(PIPELINE_ROOT / "data" / "polymarket" / "paa" / "strategy_inventory_and_scorecard.json", scorecard)
    print(json.dumps({"status": "OK", "research": res, "sleeves_tracked": scorecard["total_sleeves_tracked"]}, indent=2, default=str))
    return 0


def cmd_hourly_opt(args: argparse.Namespace) -> int:
    """Every 1 hour: deeper strategy performance, latency trace & live-vs-simulated parity analysis."""
    _ensure_systemd_user_env()
    director = PAADirector()
    if (director.paa_dir / "PAA_MASTER_STOP").exists():
        print(json.dumps({"status": "PAUSED_BY_MASTER_STOP"}, indent=2))
        return 0

    fin = director.accountant.measure_and_record(live_rpc_check=True)
    lat_path = director.data_dir / "live_latency_traces.jsonl"
    p50_ms = 0.0
    p95_ms = 0.0
    sample_n = 0
    if lat_path.exists():
        vals: List[float] = []
        for ln in lat_path.read_text(encoding="utf-8", errors="ignore").splitlines()[-500:]:
            ln = ln.strip()
            if not ln:
                continue
            try:
                rec = json.loads(ln)
                ms = float(rec.get("total_loop_ms") or rec.get("latency_ms") or rec.get("rtt_ms") or 0.0)
                if ms > 0:
                    vals.append(ms)
            except Exception:
                continue
        if vals:
            vals.sort()
            sample_n = len(vals)
            p50_ms = round(vals[int(0.50 * (sample_n - 1))], 2)
            p95_ms = round(vals[int(0.95 * (sample_n - 1))], 2)
            if p95_ms > 250.0:
                director.db.enqueue_task(
                    category="ENGINEERING_OPTIMIZATION",
                    priority_label="P2",
                    expected_net_ev_usd_per_day=1.50,
                    dedupe_key="HOURLY_OPT:HIGH_LOOP_LATENCY",
                    title=f"Investigate Elevated Live Loop Latency (p95={p95_ms}ms)",
                    financial_impact_hypothesis="Keep p95 execution loop <250ms to preserve Maker queue priority.",
                    evidence={"p50_ms": p50_ms, "p95_ms": p95_ms, "samples": sample_n},
                    required_permission_class=PermissionClass.AUTOMATICALLY_PERMITTED.value,
                    next_action="PROFILE_HOT_LOOP_LATENCY",
                )

    forensic_ids = director._check_strategy_degradation_and_losses()
    summary = {
        "evaluated_at_utc": utc_now_iso(),
        "free_cash_pusd": fin["free_cash_pusd"],
        "realized_net_pnl_usd": fin["verified_realized_net_pnl_usd"],
        "simulated_shadow_t1000_pnl_usd": fin["simulated_shadow_t1000_pnl_usd"],
        "latency_samples": sample_n,
        "latency_p50_ms": p50_ms,
        "latency_p95_ms": p95_ms,
        "forensic_tasks_enqueued": forensic_ids,
    }
    _atomic_write_json(director.paa_dir / "hourly_optimization_summary.json", summary)
    director.db.record_heartbeat("paa_hourly_opt", status="OK", details=summary)
    director.generate_dashboard_and_report()
    print(json.dumps(summary, indent=2, default=str))
    return 0


def cmd_six_hour_eval(args: argparse.Namespace) -> int:
    """Every 6 hours: evaluate research candidates, run automated QA suite, and verify staging baseline."""
    _ensure_systemd_user_env()
    director = PAADirector()
    if (director.paa_dir / "PAA_MASTER_STOP").exists():
        print(json.dumps({"status": "PAUSED_BY_MASTER_STOP"}, indent=2))
        return 0

    res = director.researcher.run_research_cycle(max_events=800)
    baseline_ptr = director.deployer.ensure_baseline_staging_release()

    py_exe = str(PIPELINE_ROOT / "venv" / "bin" / "python") if (PIPELINE_ROOT / "venv" / "bin" / "python").exists() else sys.executable
    env_qa = build_isolated_worker_env(role="SIX_HOUR_QA_AUDIT", autonomy_cfg=director.cfg)
    env_qa["PYTHONPATH"] = str(PIPELINE_ROOT)
    targets = [
        "tests/test_v50_holistic_overhaul.py",
        "tests/test_zero_trust_forensic_audit.py",
        "tests/test_paa_autonomy_os.py",
    ]
    existing_targets = [t for t in targets if (PIPELINE_ROOT / t).exists()]
    t0 = time.perf_counter()
    pt = subprocess.run(
        [py_exe, "-m", "pytest", *existing_targets, "-q"],
        cwd=str(PIPELINE_ROOT),
        env=env_qa,
        capture_output=True,
        text=True,
        timeout=240.0,
    )
    qa_ms = round((time.perf_counter() - t0) * 1000.0, 1)
    qa_ok = pt.returncode == 0
    if not qa_ok:
        director.db.enqueue_task(
            category="ENGINEERING_REPAIR",
            priority_label="P0",
            expected_net_ev_usd_per_day=10.0,
            dedupe_key="SIX_HOUR_QA:REGRESSION_DETECTED",
            title="Repair Automated QA Regression Detected by 6-Hour Audit",
            financial_impact_hypothesis="Maintain 100% invariant & regression test pass rate.",
            evidence={"stdout_tail": (pt.stdout + "\n" + pt.stderr)[-1200:]},
            required_permission_class=PermissionClass.AUTOMATICALLY_PERMITTED.value,
            next_action="REPRODUCE_AND_FIX_IN_WORKTREE",
        )
        director.monitor.trigger_director_event_wakeup("SIX_HOUR_QA_REGRESSION")

    summary = {
        "evaluated_at_utc": utc_now_iso(),
        "research": res,
        "qa_passed": qa_ok,
        "qa_duration_ms": qa_ms,
        "qa_output_tail": (pt.stdout + "\n" + pt.stderr).strip()[-500:],
        "active_staging_pointer": baseline_ptr,
    }
    _atomic_write_json(director.paa_dir / "six_hour_evaluation_summary.json", summary)
    director.db.record_heartbeat("paa_6h_eval", status="OK" if qa_ok else "QA_FAILED", details={"qa_passed": qa_ok, "qa_ms": qa_ms})
    director.generate_dashboard_and_report()
    print(json.dumps(summary, indent=2, default=str))
    return 0 if qa_ok else 1


def cmd_daily_report(args: argparse.Namespace) -> int:
    """Daily full profitability analysis, cost accounting & portfolio review."""
    _ensure_systemd_user_env()
    director = PAADirector()
    fin = director.accountant.measure_and_record(live_rpc_check=True)
    dash = director.generate_dashboard_and_report()
    day_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rep_dir = director.paa_dir / "reports"
    rep_dir.mkdir(parents=True, exist_ok=True)

    vf = dash["verified_financial_performance"]
    report_payload = {
        "report_date_utc": day_str,
        "generated_at_utc": utc_now_iso(),
        "verified_financial_performance": vf,
        "budget_and_resources": dash["budget_and_resources"],
        "strategy_deployment_states": dash["strategy_deployment_states"],
        "task_counts_by_state": dash["task_counts_by_state"],
    }
    _atomic_write_json(rep_dir / f"daily_profit_report_{day_str}.json", report_payload)
    md = [
        f"# PAA Daily Verified Profitability & Portfolio Review ({day_str})",
        "",
        f"- **Generated At**: `{report_payload['generated_at_utc']}`",
        f"- **Free Wallet Cash (`pUSD + USDC.e`)**: `${vf['free_cash_pusd']:.4f}`",
        f"- **Portfolio NAV (Mark-to-Bid / Resting Maker)**: `${vf['nav_mark_to_bid_usd']:.2f}` / `${vf['nav_resting_maker_usd']:.2f}`",
        f"- **Verified On-Chain Realized Net PnL**: `${vf['realized_onchain_net_pnl_usd']:+.2f}`",
        f"- **Raw Ledger PnL vs Non-Cash Artifact Adj**: `${vf['raw_state_ledger_pnl_usd']:+.2f}` + `${vf['non_cash_unfilled_artifact_adj_usd']:+.2f}`",
        f"- **Fees & Slippage**: Fees `${vf['realized_fees_usd']:.2f}`, Est. Slippage `${vf['estimated_slippage_usd']:.2f}`",
        f"- **Autonomous Operations Cost (24h)**: AI `${vf['research_ai_cost_usd']:.4f}` + VM Infra `${vf['daily_infra_vm_cost_usd']:.4f}`",
        f"- **Net Economic Result After Ops**: `${vf['net_economic_profit_after_ops_usd']:+.2f}`",
        f"- **Simulated Non-Cash Benchmarks**: Shadow T1000 `${vf['simulated_non_cash_benchmarks']['alpha124_shadow_t1000_pnl_usd']:+.2f}`, Paper OOS `${vf['simulated_non_cash_benchmarks']['paper_oos_validation_pnl_usd']:+.2f}` (`is_real_money=False`)",
    ]
    (rep_dir / f"daily_profit_report_{day_str}.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    director.db.record_heartbeat("paa_daily_report", status="OK", details={"report_date_utc": day_str})
    print(json.dumps(report_payload, indent=2, default=str))
    return 0


def cmd_weekly_review(args: argparse.Namespace) -> int:
    """Weekly broader research, Purged WFO/CPCV governance & architecture review."""
    _ensure_systemd_user_env()
    director = PAADirector()
    ledgers = [
        director.data_dir / "ledger_shadow_sol_v392.jsonl",
        director.data_dir / "ledger_shadow_hybrid_zsplit.jsonl",
        director.data_dir / "ledger_shadow_xau_15m.jsonl",
        director.data_dir / "ledger_shadow_btc_5m.jsonl",
        director.data_dir / "ledger_shadow_sol_5m.jsonl",
    ]
    evals = [evaluate_ledger_file(p) for p in ledgers]
    wfo_out = {
        "shadow_evaluations": evals,
        "promoted_candidates": [e["ledger"] for e in evals if e.get("verdict") == "PROMOTE"],
    }
    dash = director.generate_dashboard_and_report()
    day_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rep_dir = director.paa_dir / "reports"
    rep_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "review_date_utc": day_str,
        "generated_at_utc": utc_now_iso(),
        "weekly_wfo_governance": wfo_out,
        "dashboard_snapshot": dash,
    }
    _atomic_write_json(rep_dir / f"weekly_architecture_review_{day_str}.json", payload)
    director.db.record_heartbeat("paa_weekly_review", status="OK", details={"promoted": wfo_out.get("promoted_candidates", [])})
    print(json.dumps({"status": "OK", "review_date_utc": day_str, "wfo": wfo_out}, indent=2, default=str))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    _ensure_systemd_user_env()
    dash = PAADirector().generate_dashboard_and_report()
    print(json.dumps(dash, indent=2, default=str))
    return 0


def cmd_enqueue(args: argparse.Namespace) -> int:
    db = PAATaskDB()
    t, created = db.enqueue_task(
        category=args.category,
        priority_label=args.priority,
        expected_net_ev_usd_per_day=args.ev,
        title=args.title,
        financial_impact_hypothesis=args.hypothesis,
        dedupe_key=args.dedupe_key,
        required_permission_class=args.permission_class,
        next_action="EXECUTE_QUEUED_TASK",
    )
    print(json.dumps({"created": created, "task": t}, indent=2, default=str))
    return 0


def cmd_emergency_stop(args: argparse.Namespace) -> int:
    _ensure_systemd_user_env()
    paa_dir = PIPELINE_ROOT / "data" / "polymarket" / "paa"
    paa_dir.mkdir(parents=True, exist_ok=True)
    stop_file = paa_dir / "PAA_MASTER_STOP"
    payload = {
        "stopped_at_utc": utc_now_iso(),
        "reason": args.reason,
        "include_trading": bool(args.include_trading),
    }
    _atomic_write_json(stop_file, payload)

    stopped_units: List[str] = []
    if sys.platform.startswith("linux"):
        for u in PAA_USER_TIMERS:
            subprocess.run(["systemctl", "--user", "stop", u], capture_output=True, text=True)
            stopped_units.append(u)
        subprocess.run(["systemctl", "--user", "stop", "polymarket-paa-director.service"], capture_output=True, text=True)
        if args.include_trading:
            for tu in ("polymarket-live-harvester.service", "polymarket-alpha124-shadow.service"):
                subprocess.run(["systemctl", "--user", "stop", tu], capture_output=True, text=True)
                stopped_units.append(tu)

    db = PAATaskDB()
    db.log_event("owner_control", "EMERGENCY_STOP_ENGAGED", {**payload, "stopped_units": stopped_units})
    print(json.dumps({"status": "EMERGENCY_STOP_ENGAGED", "stop_file": str(stop_file), "stopped_units": stopped_units}, indent=2))
    return 0


def cmd_zero_trust_status(args: argparse.Namespace) -> int:
    _ensure_systemd_user_env()
    director = PAADirector()
    pol_ok, pol_missing = director.context_manager.verify_tier_a_policies_present()
    out = {
        "checked_at_utc": utc_now_iso(),
        "tier_a_policies_intact": pol_ok,
        "tier_a_missing_policies": pol_missing,
        "zero_trust_summary": director.db.get_zero_trust_summary(),
        "verified_facts": director.db.list_verified_facts(include_stale=True, limit=25),
        "recent_stateless_sessions": director.db.list_session_runs(limit=12),
    }
    print(json.dumps(out, indent=2, default=str))
    return 0


def cmd_resume(args: argparse.Namespace) -> int:
    _ensure_systemd_user_env()
    stop_file = PIPELINE_ROOT / "data" / "polymarket" / "paa" / "PAA_MASTER_STOP"
    if stop_file.exists():
        stop_file.unlink()
    started_units: List[str] = []
    if sys.platform.startswith("linux"):
        for u in PAA_USER_TIMERS:
            rc = subprocess.run(["systemctl", "--user", "enable", "--now", u], capture_output=True, text=True).returncode
            if rc == 0:
                started_units.append(u)
    db = PAATaskDB()
    db.log_event("owner_control", "AUTONOMY_RESUMED", {"resumed_at_utc": utc_now_iso(), "started_units": started_units})
    print(json.dumps({"status": "AUTONOMY_RESUMED", "started_units": started_units}, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="PROFIT ABOVE ALL (PAA) Autonomous Operating System CLI")
    sub = p.add_subparsers(dest="command", required=True)

    p_dir = sub.add_parser("director-cycle", help="Run one lock-protected PAA Director cycle")
    p_dir.add_argument("--max-tasks", type=int, default=2)
    p_dir.add_argument("--no-ai", action="store_true")
    p_dir.add_argument("--no-proactive-research", action="store_true")
    p_dir.add_argument("--live-rpc", action="store_true")
    p_dir.set_defaults(func=cmd_director_cycle)

    p_mon = sub.add_parser("monitor-cycle", help="Run 1-minute independent watchdog & reconciliation")
    p_mon.add_argument("--offline", action="store_true")
    p_mon.add_argument("--no-recover", action="store_true")
    p_mon.set_defaults(func=cmd_monitor_cycle)

    p_sup = sub.add_parser("supervisor-cycle", help="Run 2-minute Tier-2 independent supervisor check")
    p_sup.add_argument("--no-repair", action="store_true")
    p_sup.set_defaults(func=cmd_supervisor_cycle)

    p_scan = sub.add_parser("scan-cycle", help="Run 5-minute Polymarket ecosystem scan & scorecard")
    p_scan.add_argument("--max-events", type=int, default=800)
    p_scan.set_defaults(func=cmd_scan_cycle)

    p_h = sub.add_parser("hourly-opt", help="Run 1-hour strategy, parity & latency optimization audit")
    p_h.set_defaults(func=cmd_hourly_opt)

    p_6h = sub.add_parser("six-hour-eval", help="Run 6-hour candidate evaluation & automated QA regression suite")
    p_6h.set_defaults(func=cmd_six_hour_eval)

    p_day = sub.add_parser("daily-report", help="Generate daily verified profitability & cost report")
    p_day.set_defaults(func=cmd_daily_report)

    p_wk = sub.add_parser("weekly-review", help="Run weekly WFO/CPCV governance & architecture review")
    p_wk.set_defaults(func=cmd_weekly_review)

    p_st = sub.add_parser("status", help="Generate and print live PAA dashboard JSON")
    p_st.set_defaults(func=cmd_status)

    p_zt = sub.add_parser("zero-trust-status", help="Inspect Tier-A/B/C Zero-Trust memory, TTLs & stateless sessions")
    p_zt.set_defaults(func=cmd_zero_trust_status)

    p_enq = sub.add_parser("enqueue", help="Enqueue a durable task into paa_tasks.db")
    p_enq.add_argument("--category", default="RESEARCH_DISCOVERY")
    p_enq.add_argument("--priority", default="P2")
    p_enq.add_argument("--ev", type=float, default=1.0)
    p_enq.add_argument("--title", required=True)
    p_enq.add_argument("--hypothesis", default="Operator-queued PAA task")
    p_enq.add_argument("--dedupe-key", default=None)
    p_enq.add_argument("--permission-class", default=PermissionClass.AUTOMATICALLY_PERMITTED.value)
    p_enq.set_defaults(func=cmd_enqueue)

    p_stop = sub.add_parser("emergency-stop", help="Safely halt PAA autonomous infrastructure")
    p_stop.add_argument("--reason", default="Manual owner emergency stop")
    p_stop.add_argument("--include-trading", action="store_true", help="Also stop live & shadow trading services")
    p_stop.set_defaults(func=cmd_emergency_stop)

    p_res = sub.add_parser("resume", help="Clear master stop & re-enable PAA autonomous timers")
    p_res.set_defaults(func=cmd_resume)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
