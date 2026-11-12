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
    sync_machine_gun_telemetry_snapshot,
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

PAA_TRADING_AND_SHADOW_UNITS = [
    "polymarket-live-harvester.service",
    "polymarket-alpha124-shadow.service",
    "polymarket-cross-venue-shadow.service",
    "polymarket-cross-venue-shadow-watchdog.timer",
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
    sync_machine_gun_telemetry_snapshot(PIPELINE_ROOT / "data" / "polymarket")
    researcher = PAAResearcher(db, budget, autonomy_cfg=cfg)
    res = researcher.run_research_cycle(max_events=args.max_events)
    fin = reconcile_authoritative_ledger(live_rpc_check=not getattr(args, "offline", False))
    _atomic_write_json(PIPELINE_ROOT / "data" / "polymarket" / "paa" / "authoritative_financial_ledger.json", fin)
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
    lat_candidates = [
        (director.data_dir / "latency_trace.jsonl", ("total_loop_ms", "total_ms", "latency_ms", "rtt_ms", "http_post_ms"), 250.0),
        (director.data_dir / "live_latency_traces.jsonl", ("total_loop_ms", "latency_ms", "rtt_ms"), 250.0),
        (director.data_dir / "live_orders.jsonl", ("clob_http_post_ms", "http_ms", "latency_ms"), 350.0),
    ]
    p50_ms = 0.0
    p95_ms = 0.0
    sample_n = 0
    lat_source = "NONE"
    for lat_path, lat_keys, p95_thresh_ms in lat_candidates:
        if not lat_path.exists():
            continue
        vals: List[float] = []
        for ln in lat_path.read_text(encoding="utf-8", errors="ignore").splitlines()[-500:]:
            ln = ln.strip()
            if not ln:
                continue
            try:
                rec = json.loads(ln)
                ms = 0.0
                for lk in lat_keys:
                    v_ms = rec.get(lk)
                    if v_ms is not None and float(v_ms or 0.0) > 0.0:
                        ms = float(v_ms)
                        break
                if ms > 0.0:
                    vals.append(ms)
            except Exception:
                continue
        if vals:
            vals.sort()
            sample_n = len(vals)
            lat_source = lat_path.name
            p50_ms = round(vals[int(0.50 * (sample_n - 1))], 2)
            p95_ms = round(vals[int(0.95 * (sample_n - 1))], 2)
            if p95_ms > p95_thresh_ms:
                director.db.enqueue_task(
                    category="ENGINEERING_OPTIMIZATION",
                    priority_label="P2",
                    expected_net_ev_usd_per_day=1.50,
                    dedupe_key="HOURLY_OPT:HIGH_LOOP_LATENCY",
                    title=f"Investigate Elevated Live Latency ({lat_source} p95={p95_ms}ms)",
                    financial_impact_hypothesis=f"Keep p95 latency <{p95_thresh_ms:.0f}ms to preserve Maker queue priority.",
                    evidence={"source": lat_source, "p50_ms": p50_ms, "p95_ms": p95_ms, "samples": sample_n},
                    required_permission_class=PermissionClass.AUTOMATICALLY_PERMITTED.value,
                    next_action="PROFILE_HOT_LOOP_LATENCY",
                )
            break

    forensic_ids = director._check_strategy_degradation_and_losses()
    conv = director._audit_profit_conversion_and_velocity()
    from src.paa_os.optimizer import PAAOptimizer
    opt_report = PAAOptimizer(PIPELINE_ROOT, director.data_dir).run_hourly_optimization()
    scorecard = build_strategy_scorecard(reconcile_authoritative_ledger(live_rpc_check=False))
    _atomic_write_json(director.paa_dir / "strategy_inventory_and_scorecard.json", scorecard)
    summary = {
        "evaluated_at_utc": utc_now_iso(),
        "operating_mode": str(director.cfg.get("operating_mode") or "RISKLESS_PAA"),
        "free_cash_pusd": fin["free_cash_pusd"],
        "realized_net_pnl_usd": fin["verified_realized_net_pnl_usd"],
        "simulated_shadow_t1000_pnl_usd": fin["simulated_shadow_t1000_pnl_usd"],
        "zero_loss_shadow_t1000_pnl_usd": fin.get("zero_loss_shadow_t1000_pnl_usd", 0.0),
        "zero_loss_shadow_wins": fin.get("zero_loss_shadow_wins", 0),
        "riskless_metrics": fin.get("riskless_metrics") or {},
        "conversion_and_velocity": conv,
        "riskless_optimizer": opt_report,
        "latency_source": lat_source,
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
        "tests/test_paa_zero_trust_and_dashboard.py",
        "tests/test_paa_profit_and_accounting_upgrades.py",
        "tests/test_riskless_machine_gun.py",
        "tests/test_riskless_protocol_v2_and_paa.py",
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
    if qa_ok:
        baseline_ptr = director.deployer.ensure_baseline_staging_release(refresh_if_baseline=True)
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
    rl_kpis = dash.get("riskless_paa_kpis") or {}
    report_payload = {
        "report_date_utc": day_str,
        "generated_at_utc": utc_now_iso(),
        "operating_mode": dash.get("operating_mode", "RISKLESS_PAA"),
        "riskless_paa_kpis": rl_kpis,
        "verified_financial_performance": vf,
        "budget_and_resources": dash["budget_and_resources"],
        "strategy_deployment_states": dash["strategy_deployment_states"],
        "task_counts_by_state": dash["task_counts_by_state"],
    }
    _atomic_write_json(rep_dir / f"daily_profit_report_{day_str}.json", report_payload)
    md = [
        f"# RISKLESS PAA Daily Verified Profitability & Portfolio Review ({day_str})",
        "",
        f"- **Generated At**: `{report_payload['generated_at_utc']}` | **Operating Mode**: `{report_payload['operating_mode']}`",
        f"- **Pure Riskless Live Record**: `{rl_kpis.get('pure_riskless_live_wins', 0)}W / {rl_kpis.get('pure_riskless_live_losses', 0)}L` (`{rl_kpis.get('pure_riskless_live_wr_pct', 100.0):.1f}%` WR, `${rl_kpis.get('pure_riskless_realized_pnl_usd', 0.0):+.2f}`)",
        f"- **Free Wallet Cash (`pUSD + USDC.e`)**: `${vf['free_cash_pusd']:.4f}`",
        f"- **Portfolio NAV (Mark-to-Bid / Resting Maker)**: `${vf['nav_mark_to_bid_usd']:.2f}` / `${vf['nav_resting_maker_usd']:.2f}`",
        f"- **Verified On-Chain Realized Net PnL**: `${vf['realized_onchain_net_pnl_usd']:+.2f}`",
        f"- **Raw Ledger PnL vs Non-Cash Artifact Adj**: `${vf['raw_state_ledger_pnl_usd']:+.2f}` + `${vf['non_cash_unfilled_artifact_adj_usd']:+.2f}`",
        f"- **Fees & Slippage**: Fees `${vf['realized_fees_usd']:.2f}`, Est. Slippage `${vf['estimated_slippage_usd']:.2f}`",
        f"- **Autonomous Operations Cost (24h)**: AI `${vf['research_ai_cost_usd']:.4f}` + VM Infra `${vf['daily_infra_vm_cost_usd']:.4f}`",
        f"- **Net Economic Result After Ops**: `${vf['net_economic_profit_after_ops_usd']:+.2f}`",
        f"- **Simulated Non-Cash Benchmarks**: Zero-Loss Shadow T1000 `${vf['simulated_non_cash_benchmarks'].get('zero_loss_shadow_t1000_pnl_usd', 0.0):+.2f}` (`{vf['simulated_non_cash_benchmarks'].get('zero_loss_shadow_wins', 0)}W / 0L`, Legacy All-Sleeves `${vf['simulated_non_cash_benchmarks']['alpha124_shadow_t1000_pnl_usd']:+.2f}`), Paper OOS `${vf['simulated_non_cash_benchmarks']['paper_oos_validation_pnl_usd']:+.2f}` (`is_real_money=False`)",
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
    scorecard = build_strategy_scorecard(reconcile_authoritative_ledger(live_rpc_check=False))
    raw_prom = [e["ledger"] for e in evals if e.get("verdict") == "PROMOTE"]
    rl_locked = bool(scorecard.get("riskless_only_mode", True))
    wfo_out = {
        "operating_mode": scorecard.get("operating_mode", "RISKLESS_PAA"),
        "riskless_only_mode": rl_locked,
        "shadow_evaluations": evals,
        "promoted_candidates": [] if rl_locked else raw_prom,
        "held_shadow_only_directional_candidates": raw_prom if rl_locked else [],
        "grad8_zero_loss_live_sleeves": scorecard.get("grad8_live_authorized_sleeves", []),
        "machine_gun_sleeves_detected": scorecard.get("machine_gun_sleeves_detected", []),
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


def _query_systemd_user_unit_statuses(units: List[str]) -> Dict[str, str]:
    statuses: Dict[str, str] = {}
    if not sys.platform.startswith("linux"):
        return {u: "not_applicable_non_linux" for u in units}
    for u in units:
        res = subprocess.run(["systemctl", "--user", "is-active", u], capture_output=True, text=True)
        statuses[u] = (res.stdout or res.stderr or "unknown").strip().splitlines()[0] if (res.stdout or res.stderr) else "unknown"
    return statuses


def _cancel_open_clob_orders_out_of_band(
    data_dir: Path,
    *,
    force_cancel_exits: bool = False,
    executor_factory: Any = None,
) -> Dict[str, Any]:
    """
    Out-of-band CLOB order cancellation safety net for `emergency-stop --include-trading`.
    Guarantees resting Maker entry bids (`BOND1`, `MKR_LOCK1`) are cancelled even if
    `polymarket-live-harvester.service` was hung or dead before receiving `SIGTERM`,
    while never selling/modifying held CTF tokens (`KMIA` disputed locks remain 100% untouched)
    and preserving active position `exit_order_id` / `unwind_order_id` orders unless `force_cancel_exits=True`.
    v6.0 (`R-08`): When active positions carry protective `exit_order_id`/`unwind_order_id` AND the
    executor exposes `get_open_orders` + `cancel_order`, selectively cancels all non-exit open CLOB
    orders (such as resting `BUY` entry anchors) while leaving protective exit orders intact.
    """
    resting_exit_pos_ids: List[str] = []
    protected_exit_oids: set[str] = set()
    state_path = data_dir / "live_harvester_state.json"
    if state_path.exists() and not force_cancel_exits:
        try:
            st = json.loads(state_path.read_text(encoding="utf-8"))
            act = st.get("active_positions") or {}
            for k, p in (act.items() if isinstance(act, dict) else []):
                if not isinstance(p, dict):
                    continue
                ex_id = str(p.get("exit_order_id") or "").strip()
                uw_id = str(p.get("unwind_order_id") or "").strip()
                if ex_id or uw_id:
                    resting_exit_pos_ids.append(str(k))
                    if ex_id:
                        protected_exit_oids.add(ex_id)
                    if uw_id:
                        protected_exit_oids.add(uw_id)
        except Exception as exc:
            return {"attempted": False, "ok": False, "error": f"STATE_READ_ERROR:{exc}"}

    try:
        if executor_factory is None:
            if resting_exit_pos_ids and not force_cancel_exits:
                try:
                    from dotenv import load_dotenv
                    env_file = PIPELINE_ROOT / ".env"
                    if env_file.exists():
                        load_dotenv(env_file, override=False)
                except Exception:
                    pass
                from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor
                executor = PolymarketLiveExecutor(dry_run=False)
            else:
                try:
                    from dotenv import load_dotenv
                    env_file = PIPELINE_ROOT / ".env"
                    if env_file.exists():
                        load_dotenv(env_file, override=False)
                except Exception:
                    pass
                from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor
                executor = PolymarketLiveExecutor(dry_run=False)
        else:
            executor = executor_factory()

        if resting_exit_pos_ids and not force_cancel_exits:
            get_open_fn = getattr(executor, "get_open_orders", None)
            cancel_one_fn = getattr(executor, "cancel_order", None)
            if callable(get_open_fn) and callable(cancel_one_fn):
                open_orders = get_open_fn() or []
                canceled_ids: List[str] = []
                preserved_ids: List[str] = []
                errors: List[str] = []
                for ord_rec in open_orders:
                    oid = str(
                        (ord_rec.get("id") or ord_rec.get("orderID") or ord_rec.get("order_id") or "")
                        if isinstance(ord_rec, dict)
                        else ord_rec
                    ).strip()
                    if not oid:
                        continue
                    if oid in protected_exit_oids:
                        preserved_ids.append(oid)
                        continue
                    try:
                        cancel_one_fn(oid)
                        canceled_ids.append(oid)
                    except Exception as c_err:
                        errors.append(f"{oid}:{c_err}")
                return {
                    "attempted": True,
                    "ok": len(errors) == 0,
                    "mode": "SELECTIVE_ENTRY_CANCEL_PRESERVING_EXITS",
                    "canceled_order_ids": canceled_ids,
                    "preserved_exit_order_ids": preserved_ids,
                    "protected_position_ids": resting_exit_pos_ids,
                    "errors": errors,
                }
            return {
                "attempted": False,
                "ok": True,
                "skipped_reason": "ACTIVE_POSITION_EXIT_ORDER_PRESENT",
                "protected_position_ids": resting_exit_pos_ids,
            }

        res = executor.cancel_all_orders()
        ok = isinstance(res, dict) and ("error" not in res)
        return {"attempted": True, "ok": ok, "result": res}
    except Exception as exc:
        return {"attempted": True, "ok": False, "error": str(exc)}


def cmd_emergency_stop(args: argparse.Namespace) -> int:
    _ensure_systemd_user_env()
    data_dir = PIPELINE_ROOT / "data" / "polymarket"
    paa_dir = data_dir / "paa"
    paa_dir.mkdir(parents=True, exist_ok=True)
    stopped_at = utc_now_iso()
    include_trading = bool(getattr(args, "include_trading", False))
    cancel_orders_arg = getattr(args, "cancel_orders", None)
    should_cancel_orders = bool(include_trading if cancel_orders_arg is None else cancel_orders_arg)
    force_cancel_exits = bool(getattr(args, "force_cancel_exits", False))

    stop_file = paa_dir / "PAA_MASTER_STOP"
    payload: Dict[str, Any] = {
        "stopped_at_utc": stopped_at,
        "reason": args.reason,
        "include_trading": include_trading,
    }
    _atomic_write_json(stop_file, payload)

    kill_switch_file: str | None = None
    if include_trading:
        ks_path = data_dir / "KILL_SWITCH"
        _atomic_write_json(
            ks_path,
            {
                "engaged_at_utc": stopped_at,
                "reason": args.reason,
                "source": "paa_cli.emergency-stop",
            },
        )
        kill_switch_file = str(ks_path)

    stopped_units: List[str] = []
    if sys.platform.startswith("linux"):
        for u in PAA_USER_TIMERS:
            subprocess.run(["systemctl", "--user", "stop", u], capture_output=True, text=True)
            stopped_units.append(u)
        subprocess.run(["systemctl", "--user", "stop", "polymarket-paa-director.service"], capture_output=True, text=True)
        if include_trading:
            for tu in PAA_TRADING_AND_SHADOW_UNITS:
                subprocess.run(["systemctl", "--user", "stop", tu], capture_output=True, text=True)
                stopped_units.append(tu)

    clob_cancel_report: Dict[str, Any] = {"attempted": False, "skipped_reason": "NOT_REQUESTED"}
    if should_cancel_orders:
        clob_cancel_report = _cancel_open_clob_orders_out_of_band(
            data_dir,
            force_cancel_exits=force_cancel_exits,
            executor_factory=getattr(args, "_executor_factory", None),
        )

    db = PAATaskDB(db_path=paa_dir / "paa_tasks.db")
    event_details = {
        **payload,
        "kill_switch_file": kill_switch_file,
        "stopped_units": stopped_units,
        "clob_order_cancel": clob_cancel_report,
    }
    db.log_event("owner_control", "EMERGENCY_STOP_ENGAGED", event_details)
    out = {
        "status": "EMERGENCY_STOP_ENGAGED",
        "stop_file": str(stop_file),
        "kill_switch_file": kill_switch_file,
        "stopped_units": stopped_units,
        "clob_order_cancel": clob_cancel_report,
    }
    print(json.dumps(out, indent=2))
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
    data_dir = PIPELINE_ROOT / "data" / "polymarket"
    paa_dir = data_dir / "paa"
    paa_dir.mkdir(parents=True, exist_ok=True)
    include_trading = bool(getattr(args, "include_trading", False))
    force_override_safeguard = bool(getattr(args, "force_override_safeguard", False))

    # v6.0 (`R-08`): Refuse to clear KILL_SWITCH or resume live trading if ACCOUNTING_SAFEGUARD_ACTIVE.json
    # is currently latched, unless explicit `--force-override-safeguard` is passed by the human owner.
    sg_file = paa_dir / "ACCOUNTING_SAFEGUARD_ACTIVE.json"
    if include_trading and sg_file.exists() and not force_override_safeguard:
        try:
            sg_obj = json.loads(sg_file.read_text(encoding="utf-8"))
            sg_active = not isinstance(sg_obj, dict) or sg_obj.get("active", True) is not False
        except Exception:
            sg_active = True
        if sg_active:
            err_out = {
                "status": "BLOCKED_ACCOUNTING_SAFEGUARD_ACTIVE",
                "safeguard_file": str(sg_file),
                "error": "Reconcile wallet vs state discrepancy first or pass --force-override-safeguard.",
            }
            print(json.dumps(err_out, indent=2))
            return 2

    stop_file = paa_dir / "PAA_MASTER_STOP"
    if stop_file.exists():
        stop_file.unlink()

    ks_path = data_dir / "KILL_SWITCH"
    kill_switch_cleared = False
    if include_trading and ks_path.exists():
        ks_path.unlink()
        kill_switch_cleared = True

    started_units: List[str] = []
    started_trading_units: List[str] = []
    if sys.platform.startswith("linux"):
        for u in PAA_USER_TIMERS:
            rc = subprocess.run(["systemctl", "--user", "enable", "--now", u], capture_output=True, text=True).returncode
            if rc == 0:
                started_units.append(u)
        if include_trading:
            for tu in PAA_TRADING_AND_SHADOW_UNITS:
                cmd = ["systemctl", "--user", "enable", "--now", tu] if tu.endswith(".timer") else ["systemctl", "--user", "start", tu]
                rc = subprocess.run(cmd, capture_output=True, text=True).returncode
                if rc == 0:
                    started_trading_units.append(tu)

    trading_services_status = _query_systemd_user_unit_statuses(PAA_TRADING_AND_SHADOW_UNITS)
    kill_switch_active = ks_path.exists()
    inactive_trading = [
        u for u, st in trading_services_status.items() if st not in ("active", "not_applicable_non_linux")
    ]
    warning: str | None = None
    if kill_switch_active or (not include_trading and inactive_trading):
        warning = (
            "KILL_SWITCH remains active and/or trading/shadow units are not active; "
            "pass --include-trading to clear KILL_SWITCH and restart trading & shadow services."
        )

    db = PAATaskDB(db_path=paa_dir / "paa_tasks.db")
    out: Dict[str, Any] = {
        "status": "AUTONOMY_AND_TRADING_RESUMED" if include_trading else "AUTONOMY_RESUMED",
        "started_units": started_units,
        "started_trading_units": started_trading_units,
        "kill_switch_active": kill_switch_active,
        "kill_switch_cleared": kill_switch_cleared,
        "trading_services_status": trading_services_status,
    }
    if warning:
        out["warning"] = warning
    db.log_event("owner_control", "AUTONOMY_RESUMED", {"resumed_at_utc": utc_now_iso(), **out})
    print(json.dumps(out, indent=2))
    return 0


def _verify_human_owner_cli_session(args: argparse.Namespace) -> Tuple[bool, str]:
    """
    v6.0 (`R-05` Anti-Self-Approval Invariant):
    Hard-blocks autonomous worker subprocesses (`PAA_SIGNING_DISABLED == '1'`, `PAA_WORKER_ROLE` set,
    or non-interactive stdin) from granting, revoking, consuming, or promoting owner approvals.
    """
    if os.environ.get("PAA_SIGNING_DISABLED", "").strip() == "1":
        return False, "FORBIDDEN_ISOLATED_WORKER_SUBPROCESS"
    if os.environ.get("PAA_WORKER_ROLE", "").strip():
        return False, "FORBIDDEN_AUTONOMOUS_WORKER_ROLE"
    is_tty = bool(getattr(sys.stdin, "isatty", lambda: False)()) or bool(
        getattr(args, "_interactive_tty_verified", False)
    )
    if not is_tty:
        return False, "FORBIDDEN_NON_INTERACTIVE_SESSION_REQUIRES_HUMAN_TTY"
    return True, "OK"


def cmd_approvals(args: argparse.Namespace) -> int:
    """Human-owner approval lifecycle CLI (`list`, `grant`, `revoke`, `consume`)."""
    from datetime import datetime, timedelta, timezone

    approvals_dir = PIPELINE_ROOT / "data" / "polymarket" / "paa" / "approvals"
    approvals_dir.mkdir(parents=True, exist_ok=True)
    action = str(getattr(args, "approval_action", "list") or "list").strip().lower()

    if action == "list":
        gate = PermissionGate()
        records: List[Dict[str, Any]] = []
        for fp in sorted(approvals_dir.glob("*.json")):
            scope = fp.stem
            try:
                raw = json.loads(fp.read_text(encoding="utf-8"))
            except Exception as exc:
                records.append({"scope": scope, "valid": False, "error": f"MALFORMED_JSON:{exc}"})
                continue
            valid = gate.has_owner_approval(scope)
            records.append({"scope": scope, "valid_now": valid, "record": raw})
        print(json.dumps({"checked_at_utc": utc_now_iso(), "approvals": records}, indent=2))
        return 0

    human_ok, human_rsn = _verify_human_owner_cli_session(args)
    if not human_ok:
        print(json.dumps({"status": "DENIED", "reason": human_rsn}, indent=2))
        return 3

    all_owner_scopes = bool(getattr(args, "all_owner_scopes", False))
    scope_raw = str(getattr(args, "scope", "") or "").strip()
    if action == "grant" and all_owner_scopes:
        scopes_to_grant = [
            "INCREASE_CAPITAL_EXPOSURE",
            "NEW_LIVE_TRADING_ACTIVATION",
            "CREDENTIAL_OR_PERMISSION_EXPANSION",
            "LIVE_PRODUCTION_PROMOTION",
        ]
    else:
        if not scope_raw:
            print(json.dumps({"status": "ERROR", "reason": "MISSING_APPROVAL_SCOPE"}, indent=2))
            return 2
        scopes_to_grant = [scope_raw]

    safe_scope = "".join(c for c in scopes_to_grant[0] if c.isalnum() or c in ("_", "-"))
    target_fp = approvals_dir / f"{safe_scope}.json"
    now_dt = datetime.now(timezone.utc)
    now_iso = now_dt.isoformat()
    db = PAATaskDB(db_path=PIPELINE_ROOT / "data" / "polymarket" / "paa" / "paa_tasks.db")

    if action == "grant":
        ttl_hours = min(168.0, max(0.25, float(getattr(args, "ttl_hours", 24.0) or 24.0)))
        exp_iso = (now_dt + timedelta(hours=ttl_hours)).isoformat()
        granted_files: List[str] = []
        granted_records: List[Dict[str, Any]] = []
        for raw_sc in scopes_to_grant:
            sc_clean = "".join(c for c in raw_sc if c.isalnum() or c in ("_", "-"))
            sc_fp = approvals_dir / f"{sc_clean}.json"
            rec: Dict[str, Any] = {
                "scope": sc_clean,
                "approved": True,
                "approved_by": str(getattr(args, "approved_by", "human_owner") or "human_owner"),
                "approved_at_utc": now_iso,
                "expires_at_utc": exp_iso,
                "reason": str(getattr(args, "reason", "Explicit owner CLI grant") or "Explicit owner CLI grant"),
                "revoked": False,
                "consumed_at_utc": None,
                "consumed_by_release_id": None,
            }
            rel_id = getattr(args, "release_id", None)
            sha_v = getattr(args, "git_sha", None)
            if rel_id:
                rec["release_id"] = str(rel_id)
            if sha_v:
                rec["git_sha"] = str(sha_v)
            _atomic_write_json(sc_fp, rec)
            db.log_event("owner_control", "OWNER_APPROVAL_GRANTED", rec)
            granted_files.append(str(sc_fp))
            granted_records.append(rec)
        if len(granted_records) == 1:
            print(json.dumps({"status": "GRANTED", "approval_file": granted_files[0], "record": granted_records[0]}, indent=2))
        else:
            print(json.dumps({"status": "GRANTED_SINGLE_PASS_BUNDLE", "approval_files": granted_files, "records": granted_records}, indent=2))
        return 0

    if not target_fp.exists():
        print(json.dumps({"status": "NOT_FOUND", "scope": safe_scope}, indent=2))
        return 1

    existing = json.loads(target_fp.read_text(encoding="utf-8"))
    if action == "revoke":
        existing["revoked"] = True
        existing["approved"] = False
        existing["revoked_at_utc"] = now_iso
        existing["revoke_reason"] = str(getattr(args, "reason", "Owner CLI revocation") or "Owner CLI revocation")
        _atomic_write_json(target_fp, existing)
        db.log_event("owner_control", "OWNER_APPROVAL_REVOKED", existing)
        print(json.dumps({"status": "REVOKED", "approval_file": str(target_fp), "record": existing}, indent=2))
        return 0

    if action == "consume":
        rel_req = str(getattr(args, "release_id", "") or "").strip()
        if not rel_req:
            print(json.dumps({"status": "ERROR", "reason": "CONSUME_REQUIRES_RELEASE_ID"}, indent=2))
            return 2
        existing["consumed_at_utc"] = now_iso
        existing["consumed_by_release_id"] = rel_req
        _atomic_write_json(target_fp, existing)
        db.log_event("owner_control", "OWNER_APPROVAL_CONSUMED", existing)
        print(json.dumps({"status": "CONSUMED", "approval_file": str(target_fp), "record": existing}, indent=2))
        return 0

    print(json.dumps({"status": "ERROR", "reason": f"UNKNOWN_ACTION:{action}"}, indent=2))
    return 2


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
    p_stop.add_argument("--include-trading", action="store_true", help="Also write KILL_SWITCH, stop live & shadow trading services, and cancel open CLOB entry orders")
    p_stop.add_argument(
        "--cancel-orders",
        dest="cancel_orders",
        action="store_true",
        default=None,
        help="Explicitly run out-of-band CLOB cancel_all_orders() (enabled automatically with --include-trading unless --no-cancel-orders is set)",
    )
    p_stop.add_argument(
        "--no-cancel-orders",
        dest="cancel_orders",
        action="store_false",
        help="Skip out-of-band CLOB cancel_all_orders() during --include-trading",
    )
    p_stop.add_argument(
        "--force-cancel-exits",
        action="store_true",
        help="Cancel open CLOB orders even if an active position carries a resting exit_order_id/unwind_order_id",
    )
    p_stop.set_defaults(func=cmd_emergency_stop)

    p_res = sub.add_parser("resume", help="Clear master stop & re-enable PAA autonomous timers (and trading with --include-trading)")
    p_res.add_argument("--include-trading", action="store_true", help="Also clear KILL_SWITCH and restart live & shadow trading services")
    p_res.add_argument(
        "--force-override-safeguard",
        action="store_true",
        help="Explicitly override an active ACCOUNTING_SAFEGUARD_ACTIVE.json lock during --include-trading resume",
    )
    p_res.set_defaults(func=cmd_resume)

    p_app = sub.add_parser("approvals", help="Inspect or manage human-owner approval records (R-05 / D-011)")
    p_app.add_argument("approval_action", choices=["list", "grant", "revoke", "consume"], nargs="?", default="list")
    p_app.add_argument("--scope", default="", help="Approval scope name (e.g. LIVE_PRODUCTION_PROMOTION)")
    p_app.add_argument(
        "--all-owner-scopes",
        action="store_true",
        help="Single-pass Owner authorization granting all 4 governance scopes without repeated approval prompts",
    )
    p_app.add_argument("--ttl-hours", type=float, default=24.0, help="Expiration TTL in hours (0.25..168.0)")
    p_app.add_argument("--release-id", default=None, help="Bind or consume approval for a specific release_id")
    p_app.add_argument("--git-sha", default=None, help="Bind approval to a specific git SHA")
    p_app.add_argument("--approved-by", default="human_owner", help="Human owner identifier")
    p_app.add_argument("--reason", default="Explicit owner CLI action", help="Audit log reason")
    p_app.set_defaults(func=cmd_approvals)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
