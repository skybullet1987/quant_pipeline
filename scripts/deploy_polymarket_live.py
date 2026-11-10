#!/usr/bin/env python3
"""
deploy_polymarket_live.py
=========================
Safe, atomic, flat-inventory-aware production deployment CLI for Dominus Polymarket
(`kraken-finland:/home/skybullet1987/quant_pipeline`).

Modes:
  1. `--check` (default, 100% read-only):
     - Compiles all local production & test Python modules and validates JSON configs.
     - Computes SHA-256 digests of the deployment manifest and compares against
       `kraken-finland:/home/skybullet1987/quant_pipeline` (read-only SSH inspection).
     - Reports live service status, open position count, pending Maker intents, and
       exactly which files differ.
  2. `--apply` (explicit operator opt-in):
     - Uploads the deployment manifest to an isolated staging directory on `kraken-finland`
       and runs the remote `pytest` gate BEFORE touching `/home/skybullet1987/quant_pipeline`.
     - Creates a timestamped backup tarball of all target files on `kraken-finland`.
     - Atomically installs updated `config/`, `src/polymarket_research/`, `tests/`, and `scripts/`
       files (`config/polymarket_strategy_and_risk.json` hot-reloads immediately in <2s).
     - Restarts `polymarket-alpha124-shadow.service` (`systemctl --user`) immediately, and
       restarts `polymarket-live-harvester.service` immediately if inventory is flat (`0` open
       positions and `0` non-maker inflight orders) — or arms `paa_flat_harvester_redeploy_once.py`
       automatically if a live box/carry position is currently open (unless `--force-restart` is set).
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import py_compile
import subprocess
import sys
import tarfile
import time
from pathlib import Path
from typing import Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REMOTE_HOST = "kraken-finland"
DEFAULT_REMOTE_ROOT = "/home/skybullet1987/quant_pipeline"

DEPLOY_MANIFEST: Tuple[str, ...] = (
    "audit_losing_trades.py",
    "polymarket_live_executor.py",
    "polymarket_all_in_one.py",
    "polymarket_all_in_one.txt",
    "polymarket_alpha124_all_in_one.py",
    "polymarket_alpha124_all_in_one.txt",
    "docs/DOMINUS_MASTER_ROADMAP.md",
    "systemd/polymarket-live-harvester.service",
    "systemd/polymarket-recorder.service",
    "systemd/polymarket-alpha124-shadow.service",
    "systemd/polymarket-exp316-shadow.service",
    "systemd/polymarket-trader.service",
    "systemd/polymarket-paa-6h-eval.service",
    "systemd/polymarket-paa-6h-eval.timer",
    "systemd/polymarket-paa-daily-report.service",
    "systemd/polymarket-paa-daily-report.timer",
    "systemd/polymarket-paa-director-event.path",
    "systemd/polymarket-paa-director.service",
    "systemd/polymarket-paa-director.timer",
    "systemd/polymarket-paa-hourly-opt.service",
    "systemd/polymarket-paa-hourly-opt.timer",
    "systemd/polymarket-paa-monitor.service",
    "systemd/polymarket-paa-monitor.timer",
    "systemd/polymarket-paa-supervisor.service",
    "systemd/polymarket-paa-supervisor.timer",
    "systemd/polymarket-paa-watchdog.service",
    "systemd/polymarket-paa-watchdog.timer",
    "systemd/polymarket-paa-weekly-review.service",
    "systemd/polymarket-paa-weekly-review.timer",
    "systemd/polymarket-telemetry-compactor.service",
    "systemd/polymarket-telemetry-compactor.timer",
    "systemd/polymarket-cross-venue-shadow.service",
    "systemd/polymarket-cross-venue-shadow-watchdog.service",
    "systemd/polymarket-cross-venue-shadow-watchdog.timer",
    "config/polymarket_risk_config.json",
    "config/polymarket_strategy_and_risk.json",
    "config/polymarket_external_cashflows.json",
    "config/paa_autonomy_config.json",
    "config/paa_master_mandate.md",
    "config/policies/PAA_AUTONOMY_POLICY.md",
    "config/policies/PAA_DEPLOYMENT_POLICY.md",
    "config/policies/PAA_MISSION.md",
    "config/policies/PAA_RISK_POLICY.md",
    "config/policies/PAA_VERIFICATION_POLICY.md",
    "src/paa_os/__init__.py",
    "src/paa_os/accountant.py",
    "src/paa_os/agent_runtime.py",
    "src/paa_os/budget.py",
    "src/paa_os/builder_and_deployer.py",
    "src/paa_os/director.py",
    "src/paa_os/monitor.py",
    "src/paa_os/optimizer.py",
    "src/paa_os/permissions.py",
    "src/paa_os/researcher.py",
    "src/paa_os/task_db.py",
    "src/paa_os/zero_trust.py",
    "src/polymarket_research/holistic_strategy_governance.py",
    "src/polymarket_research/latency_trace.py",
    "src/polymarket_research/economic_attribution_ledger.py",
    "src/polymarket_research/stage_c_zero_loss_velocity.py",
    "src/polymarket_research/synthetic_maker_quoter.py",
    "src/polymarket_research/polymarket_ws_streams.py",
    "src/polymarket_research/polymarket_direct_feeds.py",
    "src/polymarket_research/polymarket_terminal_recorder.py",
    "src/polymarket_research/exact_twap_lock_engine.py",
    "src/polymarket_research/orderflow_wfo_simulators.py",
    "src/polymarket_research/polymarket_live_executor.py",
    "src/polymarket_research/polymarket_live_harvester.py",
    "src/polymarket_research/riskless_machine_gun_engine.py",
    "src/polymarket_research/riskless_protocol_v2_expansion.py",
    "src/polymarket_research/same_oracle_dominance_box.py",
    "src/polymarket_research/macro_counting_ctf_engine.py",
    "src/polymarket_research/tradfi_sports_zero_fee_engine.py",
    "src/polymarket_research/weather_metar_engine.py",
    "src/polymarket_research/uma_nba_endgame_engine.py",
    "src/polymarket_research/riskless_frontier_v2_engine.py",
    "src/polymarket_research/riskless_frontier_v3_engine.py",
    "src/polymarket_research/riskless_frontier_v4_engine.py",
    "src/polymarket_research/alpha_124_shadow_daemon.py",
    "src/polymarket_research/barrier_onetouch_svi_engine.py",
    "src/polymarket_research/cross_venue_connectors.py",
    "src/polymarket_research/cross_venue_dry_run_protocol.py",
    "src/polymarket_research/cross_venue_l2_and_baskets.py",
    "src/polymarket_research/cross_venue_riskless_shadow.py",
    "src/polymarket_research/cross_venue_shadow_deployment_gates.py",
    "src/polymarket_research/cross_venue_telemetry_and_watchdog.py",
    "src/polymarket_research/cross_venue_unblock_and_certification.py",
    "src/polymarket_research/deribit_svi_surface.py",
    "src/polymarket_research/directional_wfo_shadow_sleeves.py",
    "src/polymarket_research/exp316_macro_strike_shadow.py",
    "src/polymarket_research/multistrike_svi_scalper.py",
    "src/polymarket_research/net_alpha_opportunity_engine.py",
    "src/polymarket_research/polymarket_paper_trader.py",
    "src/polymarket_research/check_polymarket_balance.py",
    "src/polymarket_research/redeem_settled_positions.py",
    "scripts/bundle_polymarket_all_in_one.py",
    "scripts/bundle_polymarket_full_codebase.py",
    "scripts/paa_autonomous_controller.py",
    "scripts/paa_cli.py",
    "scripts/paa_flat_harvester_redeploy_once.py",
    "scripts/polymarket_daily_projections.py",
    "scripts/check_polymarket_region_latency.py",
    "scripts/dominus_command_center.py",
    "scripts/weekly_wfo_governance.py",
    "scripts/shadow_cross_venue_riskless_probe.py",
    "scripts/launch_finland_browser.ps1",
    "scripts/gcp_nl_cost_and_latency_cutover.sh",
    "scripts/deploy_polymarket_live.py",
    "tests/conftest.py",
    "tests/test_action4_production_connectors_and_adversarial.py",
    "tests/test_action4_shadow_service_and_gates.py",
    "tests/test_alpha_124_oracles.py",
    "tests/test_apex_v51_adversarial_and_wfo.py",
    "tests/test_apex_v52_ws_microstructure_and_canary.py",
    "tests/test_apex_v5_fixes_and_parity.py",
    "tests/test_cloud_spend_egress_and_probe_hardening.py",
    "tests/test_cross_venue_riskless_shadow.py",
    "tests/test_directional_wfo_shadow_sleeves.py",
    "tests/test_experiments_polymarket.py",
    "tests/test_forensic_audit_v6_fixes.py",
    "tests/test_latency_trace.py",
    "tests/test_maker_queue_and_uma_fixes.py",
    "tests/test_orderflow_hardening.py",
    "tests/test_paa_autonomy_os.py",
    "tests/test_paa_profit_and_accounting_upgrades.py",
    "tests/test_paa_zero_trust_and_dashboard.py",
    "tests/test_phase1_and_dry_run_protocol.py",
    "tests/test_polymarket_execution_parity.py",
    "tests/test_polymarket_executor.py",
    "tests/test_polymarket_live_e2e_diagnostic.py",
    "tests/test_polymarket_live_micro_order.py",
    "tests/test_polymarket_live_qa.py",
    "tests/test_polymarket_post_loss_sizing_and_purge.py",
    "tests/test_polymarket_refinements_production.py",
    "tests/test_polymarket_sleeve2_mutual_exclusion.py",
    "tests/test_polymarket_wfo_5fixes.py",
    "tests/test_priority0_live_leak_fixes.py",
    "tests/test_qa_audit_remediation_invariants.py",
    "tests/test_qa_flawless_riskless_hardening.py",
    "tests/test_riskless_cleanup_optimizations.py",
    "tests/test_riskless_frontier_v3.py",
    "tests/test_riskless_frontier_v4.py",
    "tests/test_riskless_machine_gun.py",
    "tests/test_riskless_paa_fill_rate_uplift.py",
    "tests/test_riskless_protocol_v2_and_paa.py",
    "tests/test_round3_adversarial_invariants.py",
    "tests/test_stage_b_economic_attribution.py",
    "tests/test_stage_c_zero_loss_velocity.py",
    "tests/test_v33_microstructure.py",
    "tests/test_v36_forensic_remediation.py",
    "tests/test_v395_sleeve1_all_tracks.py",
    "tests/test_v50_holistic_overhaul.py",
    "tests/test_v530_forensic_plumbing_fixes.py",
    "tests/test_v531_qa_audit_fixes.py",
    "tests/test_v550_zero_loss_frontier_and_velocity.py",
    "tests/test_v560_fill_rate_and_profit_growth.py",
    "tests/test_v570_ms_velocity_and_ws_sniper.py",
    "tests/test_v580_sharded_ws_d1fast_pusd_and_direct_feeds.py",
    "tests/test_v590_fast_cancel_ws_hedge_and_synthetic_maker.py",
    "tests/test_zero_trust_forensic_audit.py",
)

REMOTE_PYTEST_GATE: Tuple[str, ...] = tuple(
    rel for rel in DEPLOY_MANIFEST
    if rel.startswith("tests/test_") and rel not in ("tests/test_polymarket_live_e2e_diagnostic.py", "tests/test_polymarket_live_qa.py")
)

TEXT_NORM_SUFFIXES: Tuple[str, ...] = (".py", ".json", ".sh", ".ps1", ".service", ".timer", ".path", ".txt", ".md")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_local_manifest(manifest: Tuple[str, ...] = DEPLOY_MANIFEST) -> Dict[str, str]:
    """Validates syntax/JSON of every file in `manifest` and returns `{rel_path: sha256}`."""
    digests: Dict[str, str] = {}
    for rel in manifest:
        fp = PROJECT_ROOT / rel
        if not fp.exists():
            raise FileNotFoundError(f"Missing local manifest file: {fp}")
        raw = fp.read_bytes()
        if rel.endswith(".json"):
            parsed = json.loads(raw.decode("utf-8"))
            if rel.endswith("polymarket_strategy_and_risk.json"):
                if not parsed.get("directional", {}).get("riskless_only_mode", False):
                    raise ValueError("Refusing deploy: directional.riskless_only_mode MUST be True in polymarket_strategy_and_risk.json")
        elif rel.endswith(".py"):
            py_compile.compile(str(fp), doraise=True)
        digests[rel] = _sha256_bytes(raw)
    return digests


def build_manifest_tar_gz(manifest: Tuple[str, ...] = DEPLOY_MANIFEST) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for rel in manifest:
            fp = PROJECT_ROOT / rel
            data = fp.read_bytes().replace(b"\r\n", b"\n") if rel.endswith(TEXT_NORM_SUFFIXES) else fp.read_bytes()
            info = tarfile.TarInfo(name=rel)
            info.size = len(data)
            info.mtime = int(fp.stat().st_mtime)
            info.mode = 0o755 if rel.startswith("scripts/") and rel.endswith(".py") else 0o644
            tf.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def inspect_remote_state(host: str, remote_root: str, manifest: Tuple[str, ...]) -> Dict[str, object]:
    probe_py = (
        "import hashlib, json, os, pathlib, subprocess\n"
        f"root = pathlib.Path({remote_root!r})\n"
        f"manifest = {list(manifest)!r}\n"
        f"norm_sfx = {TEXT_NORM_SUFFIXES!r}\n"
        "hashes = {}\n"
        "for rel in manifest:\n"
        "    p = root / rel\n"
        "    if p.exists():\n"
        "        b = p.read_bytes().replace(b'\\r\\n', b'\\n') if rel.endswith(norm_sfx) else p.read_bytes()\n"
        "        hashes[rel] = hashlib.sha256(b).hexdigest()\n"
        "    else:\n"
        "        hashes[rel] = None\n"
        "env = {**os.environ, 'XDG_RUNTIME_DIR': f'/run/user/{os.getuid()}'}\n"
        "svcs = {}\n"
        "for s in ('polymarket-live-harvester.service', 'polymarket-alpha124-shadow.service', 'polymarket-recorder.service', 'polymarket-cross-venue-shadow.service'):\n"
        "    r = subprocess.run(['systemctl', '--user', 'is-active', s], env=env, capture_output=True, text=True)\n"
        "    svcs[s] = r.stdout.strip() or r.stderr.strip()\n"
        "st_p = root / 'data/polymarket/live_harvester_state.json'\n"
        "st = json.loads(st_p.read_text(encoding='utf-8')) if st_p.exists() else {}\n"
        "act = st.get('active_positions') or {}\n"
        "pend = st.get('pending_entry_intents') or {}\n"
        "print(json.dumps({'hashes': hashes, 'services': svcs, 'active_positions': len(act), "
        "'pending_maker_intents': sum(1 for v in pend.values() if isinstance(v, dict) and v.get('live_maker_anchor_inflight')), "
        "'pending_other_intents': sum(1 for v in pend.values() if isinstance(v, dict) and not v.get('live_maker_anchor_inflight')), "
        "'live_bankroll': st.get('live_bankroll'), 'risk_halt': st.get('risk_halt')}))\n"
    )
    proc = subprocess.run(
        ["ssh", host, f"{remote_root}/venv/bin/python -"],
        input=probe_py,
        capture_output=True,
        text=True,
        timeout=25,
        check=True,
    )
    return json.loads(proc.stdout.strip().splitlines()[-1])


def run_check(host: str, remote_root: str) -> int:
    print("[1/2] Validating local syntax, JSON governance, and zero-loss guardrails...")
    verify_local_manifest(DEPLOY_MANIFEST)
    norm_local: Dict[str, str] = {}
    for rel in DEPLOY_MANIFEST:
        fp = PROJECT_ROOT / rel
        b = fp.read_bytes().replace(b"\r\n", b"\n") if rel.endswith(TEXT_NORM_SUFFIXES) else fp.read_bytes()
        norm_local[rel] = _sha256_bytes(b)
    print(f"      OK ({len(DEPLOY_MANIFEST)} manifest files validated).")

    print(f"[2/2] Inspecting remote state on {host}:{remote_root} (read-only)...")
    rem = inspect_remote_state(host, remote_root, DEPLOY_MANIFEST)
    rem_hashes = rem.get("hashes") or {}
    changed: List[str] = [rel for rel in DEPLOY_MANIFEST if rem_hashes.get(rel) != norm_local[rel]]

    print(f"      Services: {rem.get('services')}")
    print(
        f"      Harvester: bankroll=${rem.get('live_bankroll')} | risk_halt={rem.get('risk_halt')} | "
        f"active_positions={rem.get('active_positions')} | maker_intents={rem.get('pending_maker_intents')}"
    )
    print(f"      Changed/new files to deploy ({len(changed)}/{len(DEPLOY_MANIFEST)}):")
    for rel in changed:
        tag = "NEW" if rem_hashes.get(rel) is None else "MODIFIED"
        print(f"        - [{tag}] {rel}")
    if not changed:
        print("        (Remote production tree already matches local manifest 100%.)")
    return 0


def run_apply(host: str, remote_root: str, *, force_restart: bool = False) -> int:
    verify_local_manifest(DEPLOY_MANIFEST)
    tar_bytes = build_manifest_tar_gz(DEPLOY_MANIFEST)
    ts_tag = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    # Disk-backed staging directory (never /tmp tmpfs RAM on the 3.8 GiB VM!)
    stage_dir = f"{remote_root}/.deploy_stage_{ts_tag}"
    backup_tar = f"{remote_root}/backups/polymarket_predeploy_{ts_tag}.tar.gz"

    print(f"[1/4] Uploading {len(tar_bytes):,} B staged bundle to {host}:{stage_dir} (disk-backed) and running pytest gate...")
    stage_cmd = (
        f"set -e; trap 'rm -rf {stage_dir}' EXIT; mkdir -p {stage_dir}/systemd {stage_dir}/docs; "
        f"cp -r {remote_root}/src {remote_root}/config {remote_root}/tests {remote_root}/scripts {stage_dir}/; "
        f"if [ -d {remote_root}/docs ]; then cp -r {remote_root}/docs/* {stage_dir}/docs/ 2>/dev/null || true; fi; "
        f"if [ -d {remote_root}/systemd ]; then cp -r {remote_root}/systemd/* {stage_dir}/systemd/ 2>/dev/null || true; fi; "
        f"find {stage_dir} -name '__pycache__' -exec rm -rf {{}} + 2>/dev/null || true; "
        f"tar -xzf - -C {stage_dir}; "
        f"cd {stage_dir} && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH={stage_dir} {remote_root}/venv/bin/python -c "
        + json.dumps(
            "import os, sys; "
            "sys.meta_path[:] = [f for f in sys.meta_path if 'editable' not in type(f).__name__.lower()]; "
            f"sys.path[:] = [p for p in sys.path if os.path.normpath(p) != os.path.normpath({remote_root!r})]; "
            f"sys.path.insert(0, {stage_dir!r}); "
            "import pytest; "
            f"raise SystemExit(pytest.main(['-q', '--import-mode=importlib', f'--rootdir={stage_dir}', '-o', f'cache_dir={stage_dir}/.pytest_cache', {', '.join(repr(t) for t in REMOTE_PYTEST_GATE)}]))"
        )
    )
    subprocess.run(["ssh", host, stage_cmd], input=tar_bytes, timeout=600, check=True)

    print(f"[2/4] Creating atomic rollback backup at {host}:{backup_tar}...")
    existing_files = " ".join(DEPLOY_MANIFEST)
    install_cmd = (
        f"set -e; mkdir -p {remote_root}/backups; "
        f"cd {remote_root} && tar -czf {backup_tar} --ignore-failed-read {existing_files}; "
        f"tar -xzf - -C {remote_root}"
    )
    subprocess.run(["ssh", host, install_cmd], input=tar_bytes, timeout=60, check=True)

    print("[3/4] Syncing systemd user units/timers, restarting recorder/shadow, & checking Harvester restart safety...")
    restart_py = (
        "import json, os, pathlib, shutil, subprocess, sys, time\n"
        f"root = pathlib.Path({remote_root!r})\n"
        "sys.path.insert(0, str(root))\n"
        f"force = {bool(force_restart)!r}\n"
        "env = {**os.environ, 'XDG_RUNTIME_DIR': f'/run/user/{os.getuid()}'}\n"
        "user_sysd = pathlib.Path.home() / '.config/systemd/user'\n"
        "changed_units = set()\n"
        "always_sync = {\n"
        "    'polymarket-recorder.service', 'polymarket-alpha124-shadow.service',\n"
        "    'polymarket-live-harvester.service', 'polymarket-exp316-shadow.service',\n"
        "    'polymarket-paa-6h-eval.service', 'polymarket-paa-6h-eval.timer',\n"
        "    'polymarket-paa-daily-report.service', 'polymarket-paa-daily-report.timer',\n"
        "    'polymarket-paa-director-event.path', 'polymarket-paa-director.service', 'polymarket-paa-director.timer',\n"
        "    'polymarket-paa-hourly-opt.service', 'polymarket-paa-hourly-opt.timer',\n"
        "    'polymarket-paa-monitor.service', 'polymarket-paa-monitor.timer',\n"
        "    'polymarket-paa-supervisor.service', 'polymarket-paa-supervisor.timer',\n"
        "    'polymarket-paa-watchdog.service', 'polymarket-paa-watchdog.timer',\n"
        "    'polymarket-paa-weekly-review.service', 'polymarket-paa-weekly-review.timer',\n"
        "    'polymarket-telemetry-compactor.service', 'polymarket-telemetry-compactor.timer',\n"
        "    'polymarket-cross-venue-shadow.service',\n"
        "    'polymarket-cross-venue-shadow-watchdog.service', 'polymarket-cross-venue-shadow-watchdog.timer',\n"
        "}\n"
        "if user_sysd.exists():\n"
        "    for u_src in sorted((root / 'systemd').iterdir()):\n"
        "        u_name = u_src.name\n"
        "        if not u_name.endswith(('.service', '.timer', '.path')):\n"
        "            continue\n"
        "        u_dst = user_sysd / u_name\n"
        "        if u_dst.is_symlink() and str(u_dst.resolve()) == '/dev/null':\n"
        "            continue\n"
        "        if u_name in always_sync or u_dst.exists():\n"
        "            if u_dst.is_symlink() and u_dst.resolve() == u_src.resolve():\n"
        "                continue\n"
        "            r_nd = subprocess.run(['systemctl', '--user', 'show', '-p', 'NeedDaemonReload', '--value', u_name], env=env, capture_output=True, text=True)\n"
        "            if r_nd.stdout.strip() == 'yes':\n"
        "                changed_units.add(u_name)\n"
        "            if (not u_dst.exists()) or u_src.read_bytes() != u_dst.read_bytes():\n"
        "                shutil.copy2(u_src, u_dst)\n"
        "                changed_units.add(u_name)\n"
        "    subprocess.run(['systemctl', '--user', 'daemon-reload'], env=env, check=True)\n"
        "    for t_name in sorted(x for x in always_sync if x.endswith(('.timer', '.path'))):\n"
        "        if not (user_sysd / t_name).exists():\n"
        "            continue\n"
        "        r_sh = subprocess.run(['systemctl', '--user', 'show', '-p', 'ActiveState,SubState', '--value', t_name], env=env, capture_output=True, text=True)\n"
        "        pts = [x.strip() for x in r_sh.stdout.splitlines() if x.strip()]\n"
        "        a_st = pts[0] if len(pts) >= 1 else ''\n"
        "        s_st = pts[1] if len(pts) >= 2 else ''\n"
        "        if a_st != 'active':\n"
        "            subprocess.run(['systemctl', '--user', 'enable', '--now', t_name], env=env, check=False)\n"
        "        elif t_name in changed_units or (t_name.endswith('.timer') and s_st == 'elapsed'):\n"
        "            subprocess.run(['systemctl', '--user', 'restart', t_name], env=env, check=False)\n"
        "    if 'polymarket-recorder.service' in changed_units:\n"
        "        subprocess.run(['systemctl', '--user', 'restart', 'polymarket-recorder.service'], env=env, check=True)\n"
        "    if 'polymarket-exp316-shadow.service' in changed_units:\n"
        "        r_exp = subprocess.run(['systemctl', '--user', 'is-active', 'polymarket-exp316-shadow.service'], env=env, capture_output=True, text=True)\n"
        "        if r_exp.stdout.strip() == 'active':\n"
        "            subprocess.run(['systemctl', '--user', 'restart', 'polymarket-exp316-shadow.service'], env=env, check=True)\n"
        "r_cv = subprocess.run(['systemctl', '--user', 'is-active', 'polymarket-cross-venue-shadow.service'], env=env, capture_output=True, text=True)\n"
        "if r_cv.stdout.strip() == 'active' or 'polymarket-cross-venue-shadow.service' in changed_units:\n"
        "    if (user_sysd / 'polymarket-cross-venue-shadow.service').exists():\n"
        "        subprocess.run(['systemctl', '--user', 'restart', 'polymarket-cross-venue-shadow.service'], env=env, check=True)\n"
        "subprocess.run(['systemctl', '--user', 'restart', 'polymarket-alpha124-shadow.service'], env=env, check=True)\n"
        "st_p = root / 'data/polymarket/live_harvester_state.json'\n"
        "st = json.loads(st_p.read_text(encoding='utf-8')) if st_p.exists() else {}\n"
        "act = st.get('active_positions') or {}\n"
        "from scripts.paa_flat_harvester_redeploy_once import _safe_to_restart\n"
        "if force or _safe_to_restart(st):\n"
        "    subprocess.run(['systemctl', '--user', 'restart', 'polymarket-live-harvester.service'], env=env, check=True)\n"
        "    time.sleep(3.0)\n"
        "    mode = 'RESTARTED_IMMEDIATELY'\n"
        "else:\n"
        "    subprocess.Popen([str(root / 'venv/bin/python'), str(root / 'scripts/paa_flat_harvester_redeploy_once.py'), 'v5.9.1'], "
        "env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)\n"
        "    mode = f'ARMED_FLAT_BOOK_WATCHER(active_positions={len(act)})'\n"
        "s1 = subprocess.run(['systemctl', '--user', 'is-active', 'polymarket-alpha124-shadow.service'], env=env, capture_output=True, text=True).stdout.strip()\n"
        "s2 = subprocess.run(['systemctl', '--user', 'is-active', 'polymarket-live-harvester.service'], env=env, capture_output=True, text=True).stdout.strip()\n"
        "s3 = subprocess.run(['systemctl', '--user', 'is-active', 'polymarket-recorder.service'], env=env, capture_output=True, text=True).stdout.strip()\n"
        "s4 = subprocess.run(['systemctl', '--user', 'is-active', 'polymarket-cross-venue-shadow.service'], env=env, capture_output=True, text=True).stdout.strip()\n"
        "print(json.dumps({'harvester_deploy_mode': mode, 'alpha124_shadow': s1, 'live_harvester': s2, 'recorder': s3, 'cross_venue_shadow': s4, 'changed_units': sorted(changed_units), 'backup': "
        f"{backup_tar!r}"
        "}))\n"
    )
    res = subprocess.run(
        ["ssh", host, f"{remote_root}/venv/bin/python -"],
        input=restart_py,
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    print(f"[4/4] Deploy complete: {res.stdout.strip()}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Safe atomic deployer for Dominus Polymarket production services.")
    grp = ap.add_mutually_exclusive_group()
    grp.add_argument("--check", action="store_true", help="Read-only preflight validation and remote SHA-256 diff (default).")
    grp.add_argument("--apply", action="store_true", help="Stage, pytest-gate, backup, install, and gracefully reload services.")
    ap.add_argument("--host", default=DEFAULT_REMOTE_HOST, help="SSH host alias (default: kraken-finland).")
    ap.add_argument("--remote-root", default=DEFAULT_REMOTE_ROOT, help="Remote pipeline directory.")
    ap.add_argument("--force-restart", action="store_true", help="Restart live harvester immediately even if positions are open.")
    args = ap.parse_args()

    if args.apply:
        return run_apply(args.host, args.remote_root, force_restart=args.force_restart)
    return run_check(args.host, args.remote_root)


if __name__ == "__main__":
    raise SystemExit(main())
