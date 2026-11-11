#!/usr/bin/env python3
"""
Human-Owner Dry-Run Verifier, Atomic Applier & Rollback Utility for
`paa_staging/proposals/v50_owner_control_package/`.

Why staged:
  `src/paa_os/permissions.py`, `src/paa_os/builder_and_deployer.py`, and
  `config/paa_autonomy_config.json` are `protected_files` in `PermissionGate`.
  Autonomous workers are hard-blocked (`SystemExit(77)`) from executing `--apply`
  or `--rollback`; only the human owner in an un-isolated shell may apply or roll back.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import py_compile
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List

PACKAGE_DIR = Path(__file__).resolve().parent
DEFAULT_REPO_ROOT = PACKAGE_DIR.parents[2]
HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def _sha256_lf(text: str) -> str:
    return hashlib.sha256(text.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def _assert_human_owner_session() -> None:
    if os.environ.get("PAA_SIGNING_DISABLED") == "1" or bool(os.environ.get("PAA_WORKER_ROLE")):
        raise SystemExit(77)


def apply_unified_patch_for_file(orig_text: str, patch_text: str, repo_path: str) -> str:
    """Applies unified diff hunks targeting `b/<repo_path>` to `orig_text` (LF-normalized)."""
    norm_orig = orig_text.replace("\r\n", "\n")
    src_lines = norm_orig.splitlines(keepends=True)
    patch_lines = patch_text.replace("\r\n", "\n").splitlines(keepends=True)

    target_header = f"+++ b/{repo_path}"
    in_target = False
    idx = 0
    hunks: List[tuple[int, List[str]]] = []

    while idx < len(patch_lines):
        ln = patch_lines[idx]
        if ln.startswith("--- a/"):
            in_target = False
            idx += 1
            continue
        if ln.startswith("+++ b/"):
            in_target = ln.strip() == target_header
            idx += 1
            continue
        if in_target and ln.startswith("@@ "):
            m = HUNK_RE.match(ln)
            if not m:
                raise ValueError(f"Malformed hunk header in patch for {repo_path}: {ln!r}")
            old_start = int(m.group(1))
            idx += 1
            hunk_body: List[str] = []
            while idx < len(patch_lines) and not patch_lines[idx].startswith(("--- a/", "@@ ")):
                hunk_body.append(patch_lines[idx])
                idx += 1
            hunks.append((old_start, hunk_body))
            continue
        idx += 1

    if not hunks:
        raise ValueError(f"No hunks found for {repo_path}")

    out: List[str] = []
    src_pos = 0  # 0-based index into src_lines
    for old_start, body in hunks:
        hunk_idx = old_start - 1
        if hunk_idx < src_pos or hunk_idx > len(src_lines):
            raise ValueError(f"Out-of-order or out-of-bounds hunk at line {old_start} for {repo_path}")
        out.extend(src_lines[src_pos:hunk_idx])
        cur = hunk_idx
        for bln in body:
            if bln.startswith("\\"):
                continue
            prefix = bln[0]
            content = bln[1:]
            if prefix == " ":
                if cur >= len(src_lines) or src_lines[cur] != content:
                    raise ValueError(
                        f"Context mismatch in {repo_path} at line {cur + 1}: "
                        f"expected {content!r}, got {src_lines[cur] if cur < len(src_lines) else 'EOF'!r}"
                    )
                out.append(src_lines[cur])
                cur += 1
            elif prefix == "-":
                if cur >= len(src_lines) or src_lines[cur] != content:
                    raise ValueError(
                        f"Removal mismatch in {repo_path} at line {cur + 1}: "
                        f"expected {content!r}, got {src_lines[cur] if cur < len(src_lines) else 'EOF'!r}"
                    )
                cur += 1
            elif prefix == "+":
                out.append(content)
            else:
                raise ValueError(f"Unexpected diff prefix {prefix!r} in {repo_path}")
        src_pos = cur

    out.extend(src_lines[src_pos:])
    return "".join(out)


def verify_package_in_memory(repo_root: Path = DEFAULT_REPO_ROOT, pkg_dir: Path = PACKAGE_DIR) -> Dict[str, Any]:
    manifest = json.loads((pkg_dir / "proposal_manifest.json").read_text(encoding="utf-8"))
    rendered: Dict[str, str] = {}
    report_files: List[Dict[str, Any]] = []
    already_applied_count = 0

    for entry in manifest["files"]:
        rel = entry["repo_path"]
        src_p = repo_root / rel
        orig_text = src_p.read_bytes().decode("utf-8").replace("\r\n", "\n")
        actual_sha = _sha256_lf(orig_text)
        if actual_sha == entry["target_lf_sha256"]:
            if rel.endswith(".py"):
                compile(orig_text, rel, "exec")
            elif rel.endswith(".json"):
                json.loads(orig_text)
            rendered[rel] = orig_text
            already_applied_count += 1
            report_files.append(
                {
                    "repo_path": rel,
                    "baseline_lf_sha256": entry["baseline_lf_sha256"],
                    "target_lf_sha256": actual_sha,
                    "already_applied": True,
                    "verified": True,
                }
            )
            continue
        if actual_sha != entry["baseline_lf_sha256"]:
            raise ValueError(
                f"Baseline SHA-256 mismatch for {rel}: expected {entry['baseline_lf_sha256']}, got {actual_sha}"
            )
        patch_text = (pkg_dir / entry["patch_file"]).read_text(encoding="utf-8")
        new_text = apply_unified_patch_for_file(orig_text, patch_text, rel)
        actual_target_sha = _sha256_lf(new_text)
        if actual_target_sha != entry["target_lf_sha256"]:
            raise ValueError(
                f"Target SHA-256 mismatch for {rel}: expected {entry['target_lf_sha256']}, got {actual_target_sha}"
            )
        if rel.endswith(".py"):
            compile(new_text, rel, "exec")
        elif rel.endswith(".json"):
            json.loads(new_text)
        rendered[rel] = new_text
        report_files.append(
            {
                "repo_path": rel,
                "baseline_lf_sha256": actual_sha,
                "target_lf_sha256": actual_target_sha,
                "already_applied": False,
                "verified": True,
            }
        )

    if 0 < already_applied_count < len(manifest["files"]):
        raise ValueError(
            f"Partially applied state detected ({already_applied_count}/{len(manifest['files'])} files at target SHA-256)"
        )

    return {
        "package_id": manifest["package_id"],
        "verified": True,
        "already_applied": already_applied_count == len(manifest["files"]),
        "files": report_files,
        "_rendered": rendered,
    }


def apply_package(repo_root: Path = DEFAULT_REPO_ROOT, pkg_dir: Path = PACKAGE_DIR) -> Dict[str, Any]:
    _assert_human_owner_session()
    ver = verify_package_in_memory(repo_root=repo_root, pkg_dir=pkg_dir)
    rendered: Dict[str, str] = ver.pop("_rendered")
    backup_root = repo_root / "data" / "polymarket" / "paa" / "live_backups" / "v50_owner_control_package"
    if ver.get("already_applied"):
        return {
            "status": "ALREADY_APPLIED",
            "applied_files": list(rendered.keys()),
            "backup_dir": str(backup_root),
        }
    backup_root.mkdir(parents=True, exist_ok=True)

    applied: List[str] = []
    try:
        for rel, new_text in rendered.items():
            dst = repo_root / rel
            bkp = backup_root / rel
            bkp.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dst, bkp)
            tmp = dst.with_suffix(dst.suffix + ".owner_tmp")
            tmp.write_bytes(new_text.encode("utf-8"))
            if rel.endswith(".py"):
                py_compile.compile(str(tmp), doraise=True)
            os.replace(tmp, dst)
            applied.append(rel)
    except Exception:
        rollback_package(repo_root=repo_root)
        raise

    return {"status": "APPLIED", "applied_files": applied, "backup_dir": str(backup_root)}


def rollback_package(repo_root: Path = DEFAULT_REPO_ROOT, pkg_dir: Path = PACKAGE_DIR) -> Dict[str, Any]:
    _assert_human_owner_session()
    manifest = json.loads((pkg_dir / "proposal_manifest.json").read_text(encoding="utf-8"))
    backup_root = repo_root / "data" / "polymarket" / "paa" / "live_backups" / "v50_owner_control_package"
    if not backup_root.exists():
        raise FileNotFoundError(f"Backup directory not found: {backup_root}")

    restored: List[str] = []
    for entry in manifest["files"]:
        rel = entry["repo_path"]
        bkp = backup_root / rel
        dst = repo_root / rel
        if bkp.exists():
            tmp = dst.with_suffix(dst.suffix + ".rollback_tmp")
            shutil.copy2(bkp, tmp)
            os.replace(tmp, dst)
            restored.append(rel)
    return {"status": "ROLLED_BACK", "restored_files": restored, "backup_dir": str(backup_root)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify, apply, or roll back v50_owner_control_package")
    grp = parser.add_mutually_exclusive_group(required=True)
    grp.add_argument("--verify-dry-run", action="store_true", help="Verify baseline SHA-256, patch hunks, and syntax in memory")
    grp.add_argument("--apply", action="store_true", help="Human owner only: back up and atomically apply package")
    grp.add_argument("--rollback", action="store_true", help="Human owner only: restore backups atomically")
    parser.add_argument("--repo-root", type=Path, default=DEFAULT_REPO_ROOT)
    args = parser.parse_args()

    if args.verify_dry_run:
        res = verify_package_in_memory(repo_root=args.repo_root)
        res.pop("_rendered", None)
        print(json.dumps(res, indent=2))
        return 0
    if args.apply:
        print(json.dumps(apply_package(repo_root=args.repo_root), indent=2))
        return 0
    if args.rollback:
        print(json.dumps(rollback_package(repo_root=args.repo_root), indent=2))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
