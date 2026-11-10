#!/usr/bin/env python3
"""
Production Stage G Cross-Venue Shadow Deployment, Rollback & Non-Echoing Secret Provisioner
(`scripts/deploy_cross_venue_shadow.py`).

Manages ONLY Stage G (`Action #4`) files and `polymarket-cross-venue-shadow*` user units on
`quant-pipeline-finland` (SSH alias `kraken-finland`) — NEVER modifies or restarts live
trading daemons (`polymarket-live-harvester.service`, `polymarket-alpha124-shadow.service`,
`polymarket-recorder.service`).

Capabilities:
  1. `--check`: Verifies SSH host identity, kernel/RAM/disk headroom, Python venv packages,
     `/etc/polymarket-shadow.env` permissions (`0600`), and live daemon isolation.
  2. `--apply`: Stages LF-normalized bundle, runs remote `pytest` gate BEFORE touching repo,
     snapshots rollback archive, installs `/etc/polymarket-shadow.env` (`0600`, `offline` default)
     + `/etc/logrotate.d/polymarket-cross-venue-shadow` + `systemctl --user` units, starts
     service + 60s watchdog timer in `DOMINUS_NETWORK_MODE=offline` (`0` outbound calls), and
     writes SHA-256 `deployment_version.json`.
  3. `--rollback`: Atomically restores the previous Stage G backup archive (supports `--dry-run`).
  4. `--provision-secret KEY`: Interactive TTY-only (`getpass`) non-echoing credential provisioner
     with pre-write `validate_shadow_env_dict()` enforcement (`0` private keys / `0` echo).
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import getpass
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tarfile
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.polymarket_research.cross_venue_shadow_deployment_gates import (
    EX_CONFIG,
    parse_dotenv_lines,
    validate_shadow_env_dict,
    validate_shadow_env_file,
    validate_systemd_unit_text,
)

REMOTE_REPO_DIR = "/home/skybullet1987/quant_pipeline"
REMOTE_VENV_PY = f"{REMOTE_REPO_DIR}/venv/bin/python"
REMOTE_VENV_PYTEST = f"{REMOTE_REPO_DIR}/venv/bin/pytest"
REMOTE_DATA_DIR = f"{REMOTE_REPO_DIR}/data/cross_venue_shadow"
REMOTE_BACKUP_DIR = f"{REMOTE_REPO_DIR}/backups"
REMOTE_ENV_PATH = "/etc/polymarket-shadow.env"
REMOTE_LOGROTATE_PATH = "/etc/logrotate.d/polymarket-cross-venue-shadow"

PROVISIONABLE_READONLY_KEYS = frozenset({
    "PREDICT_FUN_API_KEY",
    "PREDICT_FUN_ENV",
    "PREDICT_FUN_BUILDER_APP_ID",
    "PREDICT_FUN_DATA_LICENSE_ID",
    "SX_BET_API_KEY",
    "SX_BET_DATA_APPROVAL_ID",
    "SX_BET_WRITTEN_DATA_LICENSE_ID",
    "SX_BET_DATA_INQUIRY_ID",
    "POLYMARKET_INSTITUTIONAL_APP_ID",
    "LIMITLESS_INSTITUTIONAL_APP_ID",
    "STX_API_KEY_ID",
    "STX_ED25519_KEY_FILE",
    "STX_APPS_DATA_TOKEN",
    "STX_APPS_APPLICATION_ID",
    "IBKR_GATEWAY_URL",
})

STAGE_G_MANAGED_FILES: Tuple[str, ...] = (
    "src/polymarket_research/cross_venue_riskless_shadow.py",
    "src/polymarket_research/cross_venue_shadow_deployment_gates.py",
    "src/polymarket_research/cross_venue_connectors.py",
    "src/polymarket_research/cross_venue_l2_and_baskets.py",
    "src/polymarket_research/cross_venue_telemetry_and_watchdog.py",
    "src/polymarket_research/cross_venue_unblock_and_certification.py",
    "src/polymarket_research/cross_venue_dry_run_protocol.py",
    "src/polymarket_research/economic_attribution_ledger.py",
    "docs/KYB_AND_API_ONBOARDING_DOSSIERS.md",
    "scripts/shadow_cross_venue_riskless_probe.py",
    "scripts/deploy_cross_venue_shadow.py",
    "systemd/polymarket-cross-venue-shadow.service",
    "systemd/polymarket-cross-venue-shadow-watchdog.service",
    "systemd/polymarket-cross-venue-shadow-watchdog.timer",
    "systemd/polymarket-cross-venue-shadow.logrotate",
    "systemd/polymarket-shadow.env.template",
    "tests/test_action4_shadow_service_and_gates.py",
    "tests/test_action4_production_connectors_and_adversarial.py",
    "tests/test_cross_venue_riskless_shadow.py",
)


def compute_manifest_sha256(root: Path = REPO_ROOT, rel_paths: Sequence[str] = STAGE_G_MANAGED_FILES) -> Dict[str, str]:
    """Computes LF-normalized SHA-256 digests for all Stage G managed files."""
    manifest: Dict[str, str] = {}
    for rel in rel_paths:
        p = root / rel
        if p.exists():
            norm = p.read_bytes().replace(b"\r\n", b"\n")
            manifest[rel] = hashlib.sha256(norm).hexdigest()
    return manifest


def build_lf_tar_gz_bytes(root: Path = REPO_ROOT, rel_paths: Sequence[str] = STAGE_G_MANAGED_FILES) -> bytes:
    """Packages Stage G managed files into an in-memory `.tar.gz` with clean POSIX LF line endings."""
    buf = io.BytesIO()
    now = int(time.time())
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for rel in rel_paths:
            src = root / rel
            if not src.exists():
                continue
            data = src.read_bytes().replace(b"\r\n", b"\n")
            info = tarfile.TarInfo(name=rel)
            info.size = len(data)
            info.mtime = now
            info.mode = 0o755 if rel.startswith("scripts/") else 0o644
            tf.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def get_local_git_rev(root: Path = REPO_ROOT) -> str:
    try:
        r = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--short=12", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return r.stdout.strip() if r.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def ssh_exec(
    host: str,
    remote_script: str,
    *,
    stdin_bytes: Optional[bytes] = None,
    timeout_sec: int = 120,
) -> Tuple[int, str, str]:
    proc = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", host, remote_script],
        input=stdin_bytes,
        capture_output=True,
        timeout=timeout_sec,
    )
    return (
        int(proc.returncode),
        proc.stdout.decode("utf-8", "replace"),
        proc.stderr.decode("utf-8", "replace"),
    )


def render_env_file_text(env_map: Mapping[str, str]) -> str:
    lines = [
        "# Managed by Dominus Stage G deploy_cross_venue_shadow.py (chmod 0600, zero signing keys)",
    ]
    for k in sorted(env_map.keys()):
        lines.append(f"{k}={env_map[k]}")
    return "\n".join(lines) + "\n"


def update_env_map_with_validated_secret(
    existing_env: Mapping[str, str],
    key_name: str,
    secret_value: str,
) -> Tuple[Dict[str, str], Any]:
    """Pure helper (unit-testable offline): merges & validates a read-only key without echoing it."""
    k = key_name.strip().upper()
    if k not in PROVISIONABLE_READONLY_KEYS:
        raise ValueError(f"KEY_NOT_ALLOWED_FOR_SHADOW_PROVISIONING:{k}")
    merged = dict(existing_env)
    merged[k] = secret_value.strip()
    rep = validate_shadow_env_dict(merged, permissions_ok=True, observed_mode_octal="0o600")
    return merged, rep


def run_check(host: str) -> Dict[str, Any]:
    probe_py = f"""
import json, os, platform, shutil, stat
from pathlib import Path
env_p = Path({REMOTE_ENV_PATH!r})
env_info = {{"exists": env_p.exists(), "mode": oct(stat.S_IMODE(env_p.stat().st_mode)) if env_p.exists() else None}}
du = shutil.disk_usage({REMOTE_REPO_DIR!r})
mods = {{}}
for m in ("aiohttp", "websockets", "pytest", "psutil", "sqlite3", "cryptography"):
    try:
        __import__(m)
        mods[m] = True
    except Exception:
        mods[m] = False
print(json.dumps({{
    "hostname": platform.node(),
    "kernel": platform.release(),
    "python": platform.python_version(),
    "disk_free_mb": round(du.free / (1024*1024), 1),
    "modules": mods,
    "shadow_env": env_info,
}}))
"""
    rc, out, err = ssh_exec(
        host,
        f"{REMOTE_VENV_PY} - <<'PY'\n{probe_py}\nPY\nsystemctl --user is-active polymarket-live-harvester.service || true",
    )
    if rc != 0:
        raise RuntimeError(f"Remote check failed ({rc}): {err}")
    lines = [ln.strip() for ln in out.strip().splitlines() if ln.strip()]
    host_info = json.loads(lines[0])
    harvester_state = lines[-1] if len(lines) >= 2 else "unknown"
    host_info["live_harvester_service_state"] = harvester_state
    return host_info


def run_apply(
    host: str,
    *,
    reset_offline_env: bool = False,
    enable_authorized_live_public: bool = False,
) -> Dict[str, Any]:
    # 1. Local pre-flight validation
    unit_path = REPO_ROOT / "systemd" / "polymarket-cross-venue-shadow.service"
    unit_rep = validate_systemd_unit_text(unit_path.read_text(encoding="utf-8"), str(unit_path))
    if not unit_rep.valid:
        raise RuntimeError(f"Local systemd unit validation failed: {unit_rep.errors}")

    tpl_path = REPO_ROOT / "systemd" / "polymarket-shadow.env.template"
    _, tpl_rep = validate_shadow_env_file(tpl_path, enforce_posix_0600=False)
    if not tpl_rep.valid:
        raise RuntimeError(f"Local env template validation failed: {tpl_rep.errors}")

    manifest = compute_manifest_sha256()
    bundle_bytes = build_lf_tar_gz_bytes()
    bundle_sha256 = hashlib.sha256(bundle_bytes).hexdigest()
    ts_tag = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    git_rev = get_local_git_rev()

    # 2. Upload LF-normalized bundle to isolated staging overlay directory
    stage_dir = f"/tmp/dominus_stage_g_{ts_tag}"
    stage_prep = (
        f"rm -rf {stage_dir} && mkdir -p -m 0700 {stage_dir}/src/polymarket_research {stage_dir}/config && "
        f"if [ -f '{REMOTE_REPO_DIR}/src/__init__.py' ]; then cp '{REMOTE_REPO_DIR}/src/__init__.py' {stage_dir}/src/; fi && "
        f"cp -r '{REMOTE_REPO_DIR}/src/polymarket_research/.' {stage_dir}/src/polymarket_research/ 2>/dev/null || true && "
        f"cp -r '{REMOTE_REPO_DIR}/config/.' {stage_dir}/config/ 2>/dev/null || true && "
        f"mkdir -p -m 0700 {stage_dir}/_overlay && tar xzf - -C {stage_dir}/_overlay && "
        f"cp -r {stage_dir}/_overlay/. {stage_dir}/"
    )
    rc_up, _, err_up = ssh_exec(
        host,
        stage_prep,
        stdin_bytes=bundle_bytes,
    )
    if rc_up != 0:
        raise RuntimeError(f"Staging upload failed: {err_up}")

    # 3. Execute remote pytest gate in isolated staging overlay BEFORE modifying live repository
    test_targets = " ".join(
        t
        for t in (
            "tests/test_action4_shadow_service_and_gates.py",
            "tests/test_action4_production_connectors_and_adversarial.py",
            "tests/test_cross_venue_riskless_shadow.py",
        )
        if (REPO_ROOT / t).exists()
    )
    rc_test, out_test, err_test = ssh_exec(
        host,
        f"cd {stage_dir} && PYTHONPATH={stage_dir} {REMOTE_VENV_PY} -m pytest -q -o addopts='' {test_targets}",
        timeout_sec=180,
    )
    if rc_test != 0:
        ssh_exec(host, f"rm -rf {stage_dir}")
        raise RuntimeError(f"Remote staging pytest gate FAILED (aborted before install):\n{out_test}\n{err_test}")

    # 4. Create atomic rollback backup, install ONLY Stage G managed files, configure 0600 env, logrotate & user systemd units
    backup_archive = f"{REMOTE_BACKUP_DIR}/stage_g_shadow_{ts_tag}.tar.gz"
    managed_existing_expr = " ".join(f'"{f}"' for f in STAGE_G_MANAGED_FILES)
    reset_flag = "1" if (reset_offline_env or enable_authorized_live_public) else "0"
    net_mode_val = "live_public" if enable_authorized_live_public else "offline"
    op_jur_val = "CA-ON" if enable_authorized_live_public else ""
    fex_pub_val = "1" if enable_authorized_live_public else "0"
    pf_env_val = "testnet" if enable_authorized_live_public else "mainnet"

    install_script = f"""
set -euo pipefail
mkdir -p -m 0700 "{REMOTE_BACKUP_DIR}" "{REMOTE_DATA_DIR}" "$HOME/.config/systemd/user" "$HOME/.config/dominus"

cd "{REMOTE_REPO_DIR}"
EXISTING=()
for f in {managed_existing_expr}; do
    if [ -f "$f" ]; then EXISTING+=("$f"); fi
done
if [ ${{#EXISTING[@]}} -gt 0 ]; then
    tar czf "{backup_archive}" "${{EXISTING[@]}}"
else
    tar czf "{backup_archive}" --files-from /dev/null
fi

cp -r "{stage_dir}/_overlay/." "{REMOTE_REPO_DIR}/"
rm -rf "{stage_dir}"

# Provision /etc/polymarket-shadow.env (0600 owned by service user, 0 secrets)
if [ ! -f "{REMOTE_ENV_PATH}" ] || [ "{reset_flag}" = "1" ]; then
    TMP_ENV=$(mktemp)
    cat > "$TMP_ENV" <<'EOF'
PYTHONUNBUFFERED=1
DOMINUS_NETWORK_MODE={net_mode_val}
DOMINUS_OPERATOR_JURISDICTION={op_jur_val}
DOMINUS_SERVER_REGION=FI
DOMINUS_WORKSTATION_GEOBLOCKED=1
DOMINUS_ENABLED_VENUES=polymarket,predict_fun,sx_bet,limitless,forecastex,stx_ontario
DOMINUS_KYB_AUTHORIZED_VENUES=
DOMINUS_KYB_REFERENCE_ID=
DOMINUS_REVOKED_KEY_SHA256_LIST=
POLYMARKET_INSTITUTIONAL_APP_ID=
LIMITLESS_INSTITUTIONAL_APP_ID=
PREDICT_FUN_ENV={pf_env_val}
PREDICT_FUN_API_KEY=
PREDICT_FUN_BUILDER_APP_ID=
PREDICT_FUN_DATA_LICENSE_ID=
SX_BET_API_KEY=
SX_BET_DATA_APPROVAL_ID=
SX_BET_WRITTEN_DATA_LICENSE_ID=
SX_BET_DATA_INQUIRY_ID=
IBKR_GATEWAY_URL=
IBKR_ALLOW_LOCALHOST_SELF_SIGNED=0
FORECASTEX_PUBLIC_PORTAL_AUTHORIZED={fex_pub_val}
FORECASTEX_MAX_PUBLIC_CONTRACTS=600
STX_API_KEY_ID=
STX_ED25519_KEY_FILE=
STX_APPS_DATA_TOKEN=
STX_APPS_APPLICATION_ID=
STX_ENV=prod
STX_BASE_URL=
EOF
    sudo install -o "$(id -un)" -g "$(id -gn)" -m 0600 "$TMP_ENV" "{REMOTE_ENV_PATH}"
    rm -f "$TMP_ENV"
else
    sudo chown "$(id -un):$(id -gn)" "{REMOTE_ENV_PATH}"
    sudo chmod 0600 "{REMOTE_ENV_PATH}"
fi

# Install logrotate policy
sudo install -o root -g root -m 0644 "{REMOTE_REPO_DIR}/systemd/polymarket-cross-venue-shadow.logrotate" "{REMOTE_LOGROTATE_PATH}"

# Install systemd user units (isolated strictly to Stage G shadow units)
install -m 0644 "{REMOTE_REPO_DIR}/systemd/polymarket-cross-venue-shadow.service" "$HOME/.config/systemd/user/polymarket-cross-venue-shadow.service"
install -m 0644 "{REMOTE_REPO_DIR}/systemd/polymarket-cross-venue-shadow-watchdog.service" "$HOME/.config/systemd/user/polymarket-cross-venue-shadow-watchdog.service"
install -m 0644 "{REMOTE_REPO_DIR}/systemd/polymarket-cross-venue-shadow-watchdog.timer" "$HOME/.config/systemd/user/polymarket-cross-venue-shadow-watchdog.timer"

# Validate installed configuration fail-closed before starting units
"{REMOTE_VENV_PY}" "{REMOTE_REPO_DIR}/scripts/shadow_cross_venue_riskless_probe.py" --validate-config-only --env-file "{REMOTE_ENV_PATH}" >/dev/null

systemctl --user daemon-reload
systemctl --user enable polymarket-cross-venue-shadow.service polymarket-cross-venue-shadow-watchdog.timer >/dev/null 2>&1 || true
rm -f "{REMOTE_DATA_DIR}/shadow_service_health.json"
systemctl --user restart polymarket-cross-venue-shadow.service
systemctl --user restart polymarket-cross-venue-shadow-watchdog.timer
for _ in $(seq 1 45); do
    if [ -f "{REMOTE_DATA_DIR}/shadow_service_health.json" ]; then
        break
    fi
    sleep 1
done
"{REMOTE_VENV_PY}" "{REMOTE_REPO_DIR}/scripts/shadow_cross_venue_riskless_probe.py" --watchdog-check --env-file "{REMOTE_ENV_PATH}" >/dev/null
"""
    rc_inst, out_inst, err_inst = ssh_exec(host, install_script, timeout_sec=180)
    if rc_inst != 0:
        raise RuntimeError(f"Remote installation failed ({rc_inst}):\n{out_inst}\n{err_inst}")

    version_record = {
        "schema_version": "2.0.0",
        "deployed_at_utc": ts_tag,
        "git_revision": git_rev,
        "bundle_sha256": bundle_sha256,
        "rollback_archive": backup_archive,
        "staging_pytest_output": out_test.strip(),
        "managed_file_sha256": manifest,
    }
    ver_bytes = json.dumps(version_record, indent=2).encode("utf-8")
    ssh_exec(
        host,
        f"cat > {REMOTE_DATA_DIR}/deployment_version.json",
        stdin_bytes=ver_bytes,
    )

    # 5. Collect post-deploy verification proof
    verify_cmd = f"""
systemctl --user is-active polymarket-cross-venue-shadow.service
systemctl --user is-active polymarket-cross-venue-shadow-watchdog.timer
systemctl --user is-active polymarket-live-harvester.service
stat -c '%a %U:%G' "{REMOTE_ENV_PATH}"
cat "{REMOTE_DATA_DIR}/shadow_service_health.json"
"""
    rc_v, out_v, err_v = ssh_exec(host, verify_cmd)
    if rc_v != 0:
        raise RuntimeError(f"Post-deploy verification failed: {err_v}")
    v_lines = out_v.splitlines()
    health_json = json.loads("\n".join(v_lines[4:]))
    return {
        "deployed": True,
        "deployed_at_utc": ts_tag,
        "git_revision": git_rev,
        "bundle_sha256": bundle_sha256,
        "rollback_archive": backup_archive,
        "staging_pytest_summary": out_test.strip().splitlines()[-1] if out_test.strip() else "passed",
        "shadow_service_state": v_lines[0].strip(),
        "watchdog_timer_state": v_lines[1].strip(),
        "live_harvester_service_state": v_lines[2].strip(),
        "shadow_env_stat": v_lines[3].strip(),
        "health_snapshot": {
            "service_healthy": health_json.get("service_healthy"),
            "network_mode": health_json.get("network_mode"),
            "data_origin": health_json.get("data_origin"),
            "cycles_completed": health_json.get("cycles_completed"),
            "graduation_report_sha256": health_json.get("graduation_report_sha256"),
        },
    }


def run_rollback(host: str, *, archive_path: str = "", dry_run: bool = False) -> Dict[str, Any]:
    find_cmd = (
        f"ls -1t {REMOTE_BACKUP_DIR}/stage_g_shadow_*.tar.gz 2>/dev/null | head -n 1"
        if not archive_path
        else f"ls -1 {archive_path}"
    )
    rc, out, err = ssh_exec(host, find_cmd)
    target = out.strip()
    if rc != 0 or not target:
        raise RuntimeError(f"No rollback archive found ({err.strip()})")

    rc_list, list_out, _ = ssh_exec(host, f"tar tzf '{target}'")
    archived_files = [ln.strip() for ln in list_out.splitlines() if ln.strip()]
    if dry_run:
        return {
            "rolled_back": False,
            "dry_run": True,
            "target_archive": target,
            "archive_readable": rc_list == 0,
            "files_in_archive": len(archived_files),
        }

    rb_cmd = f"""
set -euo pipefail
cd "{REMOTE_REPO_DIR}"
tar xzf "{target}" -C "{REMOTE_REPO_DIR}"
if [ -f "{REMOTE_REPO_DIR}/systemd/polymarket-cross-venue-shadow.service" ]; then
    install -m 0644 "{REMOTE_REPO_DIR}/systemd/polymarket-cross-venue-shadow.service" "$HOME/.config/systemd/user/polymarket-cross-venue-shadow.service"
fi
systemctl --user daemon-reload
systemctl --user restart polymarket-cross-venue-shadow.service
systemctl --user is-active polymarket-cross-venue-shadow.service
"""
    rc_rb, out_rb, err_rb = ssh_exec(host, rb_cmd)
    if rc_rb != 0:
        raise RuntimeError(f"Rollback execution failed: {err_rb}")
    return {
        "rolled_back": True,
        "dry_run": False,
        "restored_archive": target,
        "restored_file_count": len(archived_files),
        "shadow_service_state": out_rb.strip().splitlines()[-1],
    }


def run_provision_secret(key_name: str, *, host: str = "", local_env_path: str = "") -> int:
    if not sys.stdin.isatty():
        print("ERROR: --provision-secret requires an interactive TTY (never pass secrets via CLI args or pipes).", file=sys.stderr)
        return EX_CONFIG
    keys = [item.strip().upper() for item in key_name.split(",") if item.strip()]
    if not keys:
        print("ERROR: No key specified for --provision-secret.", file=sys.stderr)
        return EX_CONFIG
    for k in keys:
        if k not in PROVISIONABLE_READONLY_KEYS:
            print(f"ERROR: Key {k} is not an allowed Stage G read-only variable ({sorted(PROVISIONABLE_READONLY_KEYS)}).", file=sys.stderr)
            return EX_CONFIG

    secret_updates: Dict[str, str] = {}
    for k in keys:
        val = getpass.getpass(f"Enter read-only value for {k} (input hidden, never logged): ").strip().strip('"').strip("'")
        secret_updates[k] = val

    is_self_host = host.strip().lower() in {"self", "local"}
    if local_env_path:
        p = Path(local_env_path)
        existing, _ = parse_dotenv_lines(p.read_text(encoding="utf-8")) if p.exists() else ({}, [])
    elif is_self_host:
        env_p = Path(REMOTE_ENV_PATH)
        existing, _ = parse_dotenv_lines(env_p.read_text(encoding="utf-8")) if env_p.exists() else ({}, [])
    else:
        rc_rd, raw_env, _ = ssh_exec(host, f"cat {REMOTE_ENV_PATH} 2>/dev/null || true")
        existing, _ = parse_dotenv_lines(raw_env) if rc_rd == 0 else ({}, [])

    merged = dict(existing)
    for k, secret_val in secret_updates.items():
        merged, rep = update_env_map_with_validated_secret(merged, k, secret_val)
        if not rep.valid:
            print(f"ERROR: Validation rejected {k}: {rep.errors}", file=sys.stderr)
            return EX_CONFIG

    if local_env_path:
        p = Path(local_env_path)
        tmp = p.parent / f".{p.name}.tmp.{os.getpid()}"
        tmp.write_text(render_env_file_text(merged), encoding="utf-8")
        if os.name != "nt":
            os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(str(tmp), str(p))
        print(
            json.dumps(
                {
                    "provisioned_keys": keys,
                    "target": str(p),
                    "valid": True,
                    "key_lengths": {k: len(secret_updates[k]) for k in keys},
                }
            )
        )
        return 0

    rendered = render_env_file_text(merged).encode("utf-8")
    install_cmd = f'TMP=$(mktemp) && cat > "$TMP" && sudo install -o "$(id -un)" -g "$(id -gn)" -m 0600 "$TMP" {REMOTE_ENV_PATH} && rm -f "$TMP"'
    if is_self_host:
        proc = subprocess.run(
            ["bash", "-c", install_cmd],
            input=rendered,
            capture_output=True,
            timeout=30,
        )
        rc_wr = int(proc.returncode)
        err_wr = proc.stderr.decode("utf-8", "replace")
    else:
        rc_wr, _, err_wr = ssh_exec(host, install_cmd, stdin_bytes=rendered)

    if rc_wr != 0:
        print(f"ERROR: Write to {REMOTE_ENV_PATH} failed: {err_wr}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "provisioned_keys": keys,
                "host": host,
                "target": REMOTE_ENV_PATH,
                "valid": True,
                "key_lengths": {k: len(secret_updates[k]) for k in keys},
            }
        )
    )
    return 0


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Dominus Stage G Cross-Venue Shadow Deployment & Rollback Tool")
    ap.add_argument("--host", default="kraken-finland", help="SSH host alias (default: kraken-finland).")
    ap.add_argument("--check", action="store_true", help="Run remote host, dependency, and isolation pre-flight check.")
    ap.add_argument("--apply", action="store_true", help="Stage, pytest-gate, backup, and deploy Stage G shadow units.")
    ap.add_argument("--reset-offline-env", action="store_true", help="Reset /etc/polymarket-shadow.env to clean offline template.")
    ap.add_argument(
        "--enable-authorized-live-public",
        action="store_true",
        help="Configure /etc/polymarket-shadow.env in live_public mode for permitted public CFTC feeds while fencing restricted venues.",
    )
    ap.add_argument("--rollback", action="store_true", help="Restore previous Stage G backup archive.")
    ap.add_argument("--archive", default="", help="Specific backup archive path for --rollback.")
    ap.add_argument("--dry-run", action="store_true", help="Verify rollback archive without modifying remote files.")
    ap.add_argument("--provision-secret", default="", help="Interactively provision a read-only API key via hidden TTY prompt.")
    ap.add_argument("--local-env-path", default="", help="Optional local .env path for --provision-secret testing.")
    ap.add_argument(
        "--generate-stx-ed25519-keypair",
        action="store_true",
        help="Generate a local 0600 Ed25519 signing keypair for STX Ontario BYOK and print ONLY the public PEM.",
    )
    ap.add_argument(
        "--stx-key-file",
        default=str(Path.home() / ".config" / "dominus" / "stx_ed25519.pem"),
        help="Target 0600 path for --generate-stx-ed25519-keypair (default: ~/.config/dominus/stx_ed25519.pem).",
    )
    return ap.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    if args.generate_stx_ed25519_keypair:
        from src.polymarket_research.cross_venue_connectors import generate_stx_ed25519_keypair

        key_path = Path(args.stx_key_file).expanduser().resolve()
        pub_pem = generate_stx_ed25519_keypair(key_path)
        print(
            json.dumps(
                {
                    "generated": True,
                    "private_key_file": str(key_path),
                    "private_key_echoed": False,
                    "public_key_pem": pub_pem,
                    "next_step": (
                        "Paste public_key_pem into https://on.stxapp.ca -> Settings -> API Management (Read-Only scope), "
                        "then set STX_API_KEY_ID and STX_ED25519_KEY_FILE."
                    ),
                },
                indent=2,
            )
        )
        return 0
    if args.provision_secret:
        return run_provision_secret(args.provision_secret, host=args.host, local_env_path=args.local_env_path)
    if args.check:
        print(json.dumps(run_check(args.host), indent=2))
        return 0
    if args.apply:
        print(
            json.dumps(
                run_apply(
                    args.host,
                    reset_offline_env=bool(args.reset_offline_env),
                    enable_authorized_live_public=bool(args.enable_authorized_live_public),
                ),
                indent=2,
            )
        )
        return 0
    if args.rollback:
        print(json.dumps(run_rollback(args.host, archive_path=args.archive, dry_run=bool(args.dry_run)), indent=2))
        return 0
    print("Specify one of: --check, --apply, --rollback, or --provision-secret KEY", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
