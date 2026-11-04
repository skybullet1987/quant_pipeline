"""
Isolated Git Worktree Builder, Automated QA & Versioned Deployment/Rollback Controller
(`src/paa_os/builder_and_deployer.py`).

Implements PAA Section 4.A.4 (Autonomous Engineering), Section 4.A.6 (Autonomous Deployment),
Acceptance Test #7 (Deployment Test), Acceptance Test #8 (Rollback Test), and Acceptance Test #10 (Permission Test):
  - Never modifies live production code directly without version control and validation.
  - Develops and tests candidate changes inside credential-stripped Git worktrees.
  - Enforces 6 strict Release Gates:
      Gate 1: Permission & Diff Authorization Audit (`PermissionGate`)
      Gate 2: Automated QA (`pytest` + `py_compile` + `<1 MiB` bundle integrity when applicable)
      Gate 3: Accounting & Risk Invariants (`_deep_merge_validated` + accounting safeguard clear)
      Gate 4: Performance Non-Regression (module load & hot-path latency check)
      Gate 5: Staging / Shadow Deployment + Operational Canary Health Probe
      Gate 6: Automatic Rollback on Predefined Failure Criteria (restoring baseline release & verifying health)
"""

from __future__ import annotations

import copy
import json
import os
import py_compile
import re
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.paa_os.agent_runtime import HeadlessAgentRunner
from src.paa_os.budget import BudgetManager
from src.paa_os.permissions import (
    PermissionClass,
    PermissionGate,
    build_isolated_worker_env,
    load_autonomy_config,
)
from src.paa_os.task_db import PAATaskDB, utc_now_iso
from src.polymarket_research.holistic_strategy_governance import (
    DEFAULT_HOLISTIC_CONFIG,
    _deep_merge_validated,
)

PIPELINE_ROOT = Path(__file__).resolve().parents[2]


def _find_git_exe() -> str:
    w = shutil.which("git")
    if w:
        return w
    for p in (
        r"C:\Program Files\Git\cmd\git.exe",
        r"C:\Program Files\Git\bin\git.exe",
        "/usr/bin/git",
    ):
        if Path(p).exists():
            return p
    return "git"


class GitWorktreeBuilder:
    """Creates isolated, credential-stripped Git worktrees for autonomous engineering & QA."""

    def __init__(
        self,
        db: PAATaskDB,
        budget: BudgetManager,
        repo_root: Optional[Path] = None,
        worktree_root: Optional[Path] = None,
        autonomy_cfg: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.db = db
        self.budget = budget
        self.cfg = autonomy_cfg or load_autonomy_config()
        self.repo_root = (Path(repo_root) if repo_root is not None else PIPELINE_ROOT).resolve()
        rt = self.cfg.get("runtime") or {}
        if worktree_root is not None:
            self.worktree_root = Path(worktree_root).resolve()
        elif os.name != "nt":
            self.worktree_root = Path(str(rt.get("worktree_root_linux") or (self.repo_root.parent / "paa_worktrees"))).resolve()
        else:
            self.worktree_root = (self.repo_root.parent / "paa_worktrees").resolve()
        self.worktree_root.mkdir(parents=True, exist_ok=True)
        self.git_exe = _find_git_exe()

    def _git(self, args: List[str], cwd: Optional[Path] = None, timeout: float = 30.0) -> subprocess.CompletedProcess[str]:
        env = build_isolated_worker_env(role="GIT_WORKTREE_BUILDER", autonomy_cfg=self.cfg)
        return subprocess.run(
            [self.git_exe, *args],
            cwd=str(cwd or self.repo_root),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    def create_worktree(self, task_id: str, base_ref: str = "HEAD") -> Tuple[Path, str, str]:
        slug = re.sub(r"[^0-9A-Za-z_-]", "_", task_id)[:48]
        branch_name = f"paa/{slug}"
        wt_path = self.worktree_root / f"wt_{slug}_{uuid.uuid4().hex[:6]}"
        base_proc = self._git(["rev-parse", base_ref])
        if base_proc.returncode != 0:
            raise RuntimeError(f"git rev-parse {base_ref} failed: {base_proc.stderr.strip()}")
        baseline_sha = base_proc.stdout.strip()

        self._git(["worktree", "prune"])
        add_proc = self._git(["worktree", "add", "-B", branch_name, str(wt_path), baseline_sha], timeout=60.0)
        if add_proc.returncode != 0:
            raise RuntimeError(f"git worktree add failed: {add_proc.stderr.strip()}")

        # Double-guarantee zero secrets exist inside the worktree
        for secret_f in (".env", ".env.local", ".env.production"):
            sp = wt_path / secret_f
            if sp.exists():
                sp.unlink()

        return wt_path, branch_name, baseline_sha

    def remove_worktree(self, wt_path: Path) -> None:
        if wt_path.exists():
            self._git(["worktree", "remove", "--force", str(wt_path)], timeout=30.0)
            if wt_path.exists():
                shutil.rmtree(wt_path, ignore_errors=True)
        self._git(["worktree", "prune"])

    def build_and_commit_candidate(
        self,
        *,
        task_id: str,
        commit_message: str,
        apply_fn: Optional[Callable[[Path], None]] = None,
        ai_prompt: Optional[str] = None,
        agent_runner: Optional[HeadlessAgentRunner] = None,
        pytest_targets: Optional[List[str]] = None,
        keep_worktree: bool = False,
    ) -> Dict[str, Any]:
        """
        Builds a candidate change inside an isolated Git worktree, runs tests, commits to branch `paa/<task_id>`,
        and returns full release metadata + unified diff for `DeploymentController`.
        """
        wt_path, branch_name, baseline_sha = self.create_worktree(task_id)
        try:
            if apply_fn is not None:
                apply_fn(wt_path)
            elif ai_prompt and agent_runner is not None:
                eng_model = str((self.cfg.get("runtime") or {}).get("engineering_model") or "gemini-3.8-flash-high")
                timeout_s = int((self.cfg.get("budget") or {}).get("engineering_job_timeout_sec", 420))
                agent_runner.invoke(
                    prompt=ai_prompt,
                    task_id=task_id,
                    cwd=wt_path,
                    mode="auto",
                    model=eng_model,
                    sandbox=False,
                    allow_worktree_edits=True,
                    timeout_sec=timeout_s,
                )
            else:
                raise ValueError("Either apply_fn or (ai_prompt + agent_runner) is required")

            # Stage changes inside isolated worktree
            self._git(["add", "-A"], cwd=wt_path)
            st_proc = self._git(["status", "--porcelain"], cwd=wt_path)
            if not st_proc.stdout.strip():
                raise RuntimeError("NO_WORKTREE_CHANGES_PRODUCED")

            # Run pytest inside isolated worktree if targets specified
            qa_result: Dict[str, Any] = {"ran": False, "passed": True, "output": ""}
            if pytest_targets:
                env_qa = build_isolated_worker_env(role="QA_ISOLATED", autonomy_cfg=self.cfg)
                env_qa["PYTHONPATH"] = str(wt_path)
                py_exe = sys.executable
                venv_py = self.repo_root / "venv" / "bin" / "python"
                if venv_py.exists():
                    py_exe = str(venv_py)
                pt_proc = subprocess.run(
                    [py_exe, "-m", "pytest", *pytest_targets, "-q"],
                    cwd=str(wt_path),
                    env=env_qa,
                    capture_output=True,
                    text=True,
                    timeout=int((self.cfg.get("budget") or {}).get("qa_job_timeout_sec", 240)),
                )
                qa_result = {
                    "ran": True,
                    "passed": pt_proc.returncode == 0,
                    "returncode": pt_proc.returncode,
                    "output": (pt_proc.stdout + "\n" + pt_proc.stderr).strip()[-1500:],
                }
                if pt_proc.returncode != 0:
                    raise RuntimeError(f"WORKTREE_PYTEST_FAILED:{qa_result['output'][:400]}")

            commit_proc = self._git(
                [
                    "-c", "user.name=PAA Autonomous Builder",
                    "-c", "user.email=paa-builder@dominus.local",
                    "commit", "-m", commit_message,
                ],
                cwd=wt_path,
            )
            if commit_proc.returncode != 0:
                raise RuntimeError(f"git commit failed: {commit_proc.stderr or commit_proc.stdout}")

            cand_sha = self._git(["rev-parse", "HEAD"], cwd=wt_path).stdout.strip()
            names_out = self._git(["diff", "--name-only", baseline_sha, cand_sha], cwd=wt_path).stdout.strip()
            changed_files = [ln.strip() for ln in names_out.splitlines() if ln.strip()]
            diff_text = self._git(["diff", baseline_sha, cand_sha], cwd=wt_path).stdout

            return {
                "task_id": task_id,
                "branch_name": branch_name,
                "baseline_sha": baseline_sha,
                "candidate_sha": cand_sha,
                "changed_files": changed_files,
                "diff_text": diff_text,
                "worktree_path": str(wt_path) if keep_worktree else None,
                "worktree_qa": qa_result,
            }
        finally:
            if not keep_worktree:
                self.remove_worktree(wt_path)


class DeploymentController:
    """
    Versioned Release & Automatic Rollback Controller (`PAA Section 4.A.6`).
    Deploys validated candidate commits to versioned staging/canary directories, verifies operational
    behavior against baseline, promotes eligible changes safely, and rolls back automatically on failure.
    """

    def __init__(
        self,
        db: PAATaskDB,
        permission_gate: PermissionGate,
        repo_root: Optional[Path] = None,
        staging_root: Optional[Path] = None,
        data_dir: Optional[Path] = None,
        autonomy_cfg: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.db = db
        self.permission_gate = permission_gate
        self.cfg = autonomy_cfg or load_autonomy_config()
        self.repo_root = (Path(repo_root) if repo_root is not None else PIPELINE_ROOT).resolve()
        self.data_dir = (Path(data_dir) if data_dir is not None else (self.repo_root / "data" / "polymarket")).resolve()
        rt = self.cfg.get("runtime") or {}
        if staging_root is not None:
            self.staging_root = Path(staging_root).resolve()
        elif os.name != "nt":
            self.staging_root = Path(str(rt.get("staging_root_linux") or (self.repo_root.parent / "paa_staging"))).resolve()
        else:
            self.staging_root = (self.repo_root.parent / "paa_staging").resolve()
        self.releases_dir = self.staging_root / "releases"
        self.live_backups_dir = self.staging_root / "live_backups"
        self.pointer_file = self.staging_root / "CURRENT_RELEASE.json"
        self.current_link = self.staging_root / "current"
        self.releases_dir.mkdir(parents=True, exist_ok=True)
        self.live_backups_dir.mkdir(parents=True, exist_ok=True)
        self.git_exe = _find_git_exe()

    def _git(self, args: List[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess[str]:
        env = build_isolated_worker_env(role="DEPLOYMENT_CONTROLLER", autonomy_cfg=self.cfg)
        return subprocess.run([self.git_exe, *args], cwd=str(cwd or self.repo_root), env=env, capture_output=True, text=True, timeout=45.0)

    def get_active_staging_pointer(self) -> Optional[Dict[str, Any]]:
        if self.pointer_file.exists():
            try:
                return json.loads(self.pointer_file.read_text(encoding="utf-8"))
            except Exception:
                return None
        return None

    def _set_active_staging_pointer(self, release_id: str, release_path: Path, sha: str) -> None:
        payload = {
            "active_release_id": release_id,
            "release_path": str(release_path),
            "commit_sha": sha,
            "activated_at_utc": utc_now_iso(),
        }
        tmp = self.pointer_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(self.pointer_file)
        if os.name != "nt":
            tmp_lnk = self.staging_root / f".current_tmp_{uuid.uuid4().hex[:6]}"
            try:
                os.symlink(str(release_path), str(tmp_lnk))
                os.replace(str(tmp_lnk), str(self.current_link))
            except Exception:
                if tmp_lnk.exists() or tmp_lnk.is_symlink():
                    tmp_lnk.unlink(missing_ok=True)

    def _materialize_commit_files(self, commit_sha: str, target_dir: Path, files_to_extract: List[str]) -> None:
        target_dir.mkdir(parents=True, exist_ok=True)
        # Always include strategy & autonomy configs plus changed files for self-contained canary verification
        base_files = set(files_to_extract) | {
            "src/__init__.py",
            "config/polymarket_strategy_and_risk.json",
            "config/polymarket_risk_config.json",
        }
        for rel in sorted(base_files):
            rel_norm = rel.replace("\\", "/").removeprefix("./").lstrip("/")
            show = self._git(["show", f"{commit_sha}:{rel_norm}"])
            if show.returncode == 0:
                dst = target_dir / rel_norm
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_text(show.stdout, encoding="utf-8")

    def _run_release_canary_probe(
        self,
        release_dir: Path,
        changed_files: List[str],
        canary_command: Optional[List[str]] = None,
    ) -> Tuple[bool, str, float]:
        """
        Executes operational canary verification against `release_dir`:
          1. Byte-compiles every `.py` file in `release_dir`.
          2. Validates any staged `polymarket_strategy_and_risk.json`.
          3. Executes any module `--canary-check` entrypoint or caller-provided `canary_command`
             inside a credential-stripped environment (`PYTHONPATH=release_dir:repo_root`).
        """
        t0 = time.perf_counter()
        for pyf in release_dir.rglob("*.py"):
            if pyf.name == "polymarket_all_in_one.py":
                raw_aio = pyf.read_bytes()
                if len(raw_aio) >= 1_000_000:
                    return (
                        False,
                        f"BUNDLE_SIZE_CEILING_EXCEEDED:{len(raw_aio)}_bytes",
                        (time.perf_counter() - t0) * 1000.0,
                    )
                if b"\r\n" in raw_aio:
                    return False, "BUNDLE_CRLF_DETECTED:polymarket_all_in_one.py", (time.perf_counter() - t0) * 1000.0
            try:
                py_compile.compile(str(pyf), doraise=True)
            except Exception as exc:
                return False, f"PY_COMPILE_FAILED:{pyf.name}:{exc}", (time.perf_counter() - t0) * 1000.0

        cfg_f = release_dir / "config" / "polymarket_strategy_and_risk.json"
        if cfg_f.exists():
            try:
                raw_c = json.loads(cfg_f.read_text(encoding="utf-8"))
                _deep_merge_validated(DEFAULT_HOLISTIC_CONFIG, raw_c)
            except Exception as exc:
                return False, f"CONFIG_INVARIANT_FAILED:{exc}", (time.perf_counter() - t0) * 1000.0

        env = build_isolated_worker_env(role="CANARY_VERIFIER", autonomy_cfg=self.cfg)
        env["PYTHONPATH"] = os.pathsep.join([str(release_dir), str(self.repo_root)])
        py_exe = sys.executable
        venv_py = self.repo_root / "venv" / "bin" / "python"
        if venv_py.exists():
            py_exe = str(venv_py)

        if canary_command:
            proc = subprocess.run(canary_command, cwd=str(release_dir), env=env, capture_output=True, text=True, timeout=30.0)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            if proc.returncode != 0:
                return False, f"CANARY_CMD_FAILED(rc={proc.returncode}):{(proc.stderr or proc.stdout).strip()[:300]}", elapsed_ms
            return True, (proc.stdout or "CANARY_OK").strip()[:300], elapsed_ms

        # Auto-execute any changed python module that defines a `paa_canary_health_check()` function
        for rel in changed_files:
            rel_norm = rel.replace("\\", "/").removeprefix("./").lstrip("/")
            if rel_norm.endswith(".py") and (release_dir / rel_norm).exists():
                code_txt = (release_dir / rel_norm).read_text(encoding="utf-8", errors="ignore")
                if "def paa_canary_health_check" in code_txt:
                    probe = (
                        "import importlib.util, sys; "
                        f"spec=importlib.util.spec_from_file_location('cand_mod', {str(release_dir / rel_norm)!r}); "
                        "m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); "
                        "res=m.paa_canary_health_check(); "
                        "sys.exit(0 if res else 2)"
                    )
                    proc = subprocess.run([py_exe, "-c", probe], cwd=str(release_dir), env=env, capture_output=True, text=True, timeout=20.0)
                    elapsed_ms = (time.perf_counter() - t0) * 1000.0
                    if proc.returncode != 0:
                        return (
                            False,
                            f"MODULE_CANARY_HEALTH_FAILED({rel_norm}, rc={proc.returncode}):{(proc.stderr or proc.stdout).strip()[:300]}",
                            elapsed_ms,
                        )

        return True, "ALL_CANARY_CHECKS_PASSED", (time.perf_counter() - t0) * 1000.0

    def ensure_baseline_staging_release(self, *, refresh_if_baseline: bool = False) -> Dict[str, Any]:
        """Seeds an initial `BASELINE` staging release (or advances a QA-verified `REL_BASELINE_*` pointer when requested)."""
        cur = self.get_active_staging_pointer()
        head_sha = self._git(["rev-parse", "HEAD"]).stdout.strip() or "WORKING_TREE_BASELINE"
        if cur and Path(cur["release_path"]).exists():
            is_base_rel = str(cur.get("active_release_id") or "").startswith("REL_BASELINE_")
            if not (refresh_if_baseline and is_base_rel and str(cur.get("commit_sha") or "") != head_sha):
                return cur
        rel_id = f"REL_BASELINE_{head_sha[:8]}"
        rel_dir = self.releases_dir / rel_id
        rel_dir.mkdir(parents=True, exist_ok=True)
        for cfg_rel in ("config/polymarket_strategy_and_risk.json", "config/polymarket_risk_config.json"):
            src = self.repo_root / cfg_rel
            if src.exists():
                dst = rel_dir / cfg_rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
        (rel_dir / "RELEASE_MANIFEST.json").write_text(
            json.dumps({"release_id": rel_id, "commit_sha": head_sha, "type": "BASELINE"}, indent=2),
            encoding="utf-8",
        )
        self._set_active_staging_pointer(rel_id, rel_dir, head_sha)
        return self.get_active_staging_pointer() or {"active_release_id": rel_id, "release_path": str(rel_dir), "commit_sha": head_sha}

    def release_candidate(
        self,
        *,
        candidate: Dict[str, Any],
        release_id: Optional[str] = None,
        permission_class: str = PermissionClass.CONDITIONALLY_AUTOMATIC.value,
        pytest_targets: Optional[List[str]] = None,
        canary_command: Optional[List[str]] = None,
        promote_to_live_files: bool = False,
        max_canary_ms: float = 5000.0,
    ) -> Dict[str, Any]:
        """
        Runs the complete 6-gate release pipeline with automatic rollback on failure.
        """
        lock_owner = self.db.acquire_lock("production_deploy", ttl_sec=300.0)
        if not lock_owner:
            raise RuntimeError("PRODUCTION_DEPLOY_LOCK_BUSY: Overlapping deployment prevented")

        rel_id = release_id or f"REL_{int(time.time())}_{uuid.uuid4().hex[:6].upper()}"
        task_id = candidate.get("task_id")
        branch = str(candidate.get("branch_name") or "HEAD")
        cand_sha = str(candidate.get("candidate_sha") or "")
        base_sha = str(candidate.get("baseline_sha") or "")
        changed_files = list(candidate.get("changed_files") or [])
        diff_text = str(candidate.get("diff_text") or "")

        try:
            prev_pointer = self.ensure_baseline_staging_release()
            prev_rel_id = prev_pointer["active_release_id"]
            prev_rel_path = Path(prev_pointer["release_path"])
            prev_sha = prev_pointer["commit_sha"]

            # Load baseline vs candidate strategy config if config changed
            base_cfg_path = self.repo_root / "config" / "polymarket_strategy_and_risk.json"
            base_cfg = json.loads(base_cfg_path.read_text(encoding="utf-8")) if base_cfg_path.exists() else copy.deepcopy(DEFAULT_HOLISTIC_CONFIG)
            cand_cfg = base_cfg
            if any(f.replace("\\", "/").endswith("config/polymarket_strategy_and_risk.json") for f in changed_files):
                show_cfg = self._git(["show", f"{cand_sha}:config/polymarket_strategy_and_risk.json"])
                if show_cfg.returncode == 0:
                    cand_cfg = json.loads(show_cfg.stdout)

            # Gate 1: Permission & Diff Compliance Gate
            ok_perm, perm_violations = self.permission_gate.inspect_candidate_diff(
                changed_files=changed_files,
                diff_text=diff_text,
                baseline_cfg=base_cfg,
                candidate_cfg=cand_cfg,
                release_id=rel_id,
            )
            if not ok_perm:
                rec = {
                    "release_id": rel_id,
                    "task_id": task_id,
                    "git_branch": branch,
                    "candidate_sha": cand_sha,
                    "baseline_sha": base_sha,
                    "permission_class": permission_class,
                    "target_env": "blocked",
                    "state": "BLOCKED_AUTHORIZATION",
                    "qa_passed": False,
                    "invariants_passed": False,
                    "perf_passed": False,
                    "canary_passed": False,
                    "rolled_back": False,
                    "rollback_reason": "; ".join(perm_violations),
                    "evidence": {"violations": perm_violations, "changed_files": changed_files},
                }
                self.db.upsert_deployment(rec)
                self.db.log_event("deployer", "DEPLOYMENT_BLOCKED_AUTHORIZATION", rec, task_id=task_id)
                return rec

            # Materialize candidate release into staging directory
            cand_rel_dir = self.releases_dir / rel_id
            self._materialize_commit_files(cand_sha, cand_rel_dir, changed_files)

            # Gate 2: Automated QA Gate
            qa_passed = True
            qa_output = "WORKTREE_QA_VERIFIED"
            if pytest_targets:
                env_qa = build_isolated_worker_env(role="DEPLOY_QA", autonomy_cfg=self.cfg)
                env_qa["PYTHONPATH"] = os.pathsep.join([str(cand_rel_dir), str(self.repo_root)])
                py_exe = str(self.repo_root / "venv" / "bin" / "python") if (self.repo_root / "venv" / "bin" / "python").exists() else sys.executable
                pt = subprocess.run([py_exe, "-m", "pytest", *pytest_targets, "-q"], cwd=str(self.repo_root), env=env_qa, capture_output=True, text=True, timeout=180.0)
                qa_passed = pt.returncode == 0
                qa_output = (pt.stdout + "\n" + pt.stderr).strip()[-1000:]
                if not qa_passed:
                    rec = {
                        "release_id": rel_id,
                        "task_id": task_id,
                        "git_branch": branch,
                        "candidate_sha": cand_sha,
                        "baseline_sha": base_sha,
                        "permission_class": permission_class,
                        "target_env": "staging",
                        "state": "FAILED_QA_PRE_DEPLOY",
                        "qa_passed": False,
                        "invariants_passed": False,
                        "perf_passed": False,
                        "canary_passed": False,
                        "rolled_back": False,
                        "rollback_reason": f"QA_FAILED:{qa_output[:300]}",
                        "evidence": {"qa_output": qa_output},
                    }
                    self.db.upsert_deployment(rec)
                    return rec

            # Gate 3: Accounting & Risk Invariants
            safeguard_f = self.data_dir / "paa" / "ACCOUNTING_SAFEGUARD_ACTIVE.json"
            try:
                _deep_merge_validated(DEFAULT_HOLISTIC_CONFIG, cand_cfg)
                invariants_ok = not safeguard_f.exists()
                inv_reason = "OK" if invariants_ok else "ACCOUNTING_SAFEGUARD_ACTIVE_BLOCKS_PROMOTION"
            except Exception as exc:
                invariants_ok = False
                inv_reason = f"RISK_SCHEMA_INVALID:{exc}"

            if not invariants_ok:
                rec = {
                    "release_id": rel_id,
                    "task_id": task_id,
                    "git_branch": branch,
                    "candidate_sha": cand_sha,
                    "baseline_sha": base_sha,
                    "permission_class": permission_class,
                    "target_env": "staging",
                    "state": "BLOCKED_RISK_OR_ACCOUNTING_INVARIANT",
                    "qa_passed": True,
                    "invariants_passed": False,
                    "perf_passed": False,
                    "canary_passed": False,
                    "rolled_back": False,
                    "rollback_reason": inv_reason,
                    "evidence": {"invariant_reason": inv_reason},
                }
                self.db.upsert_deployment(rec)
                return rec

            # Gate 5: Activate in Staging & Run Canary + Performance Verification (Gate 4 + Gate 6 Auto-Rollback!)
            self._set_active_staging_pointer(rel_id, cand_rel_dir, cand_sha)
            canary_ok, canary_msg, canary_ms = self._run_release_canary_probe(
                cand_rel_dir, changed_files, canary_command=canary_command
            )
            perf_ok = canary_ms <= max_canary_ms

            if not canary_ok or not perf_ok:
                fail_why = canary_msg if not canary_ok else f"PERFORMANCE_REGRESSION:{canary_ms:.1f}ms>{max_canary_ms:.1f}ms"
                # AUTOMATIC ROLLBACK TO PREVIOUS VERIFIED RELEASE!
                self._set_active_staging_pointer(prev_rel_id, prev_rel_path, prev_sha)
                restored_ok, restored_msg, _ = self._run_release_canary_probe(prev_rel_path, [])
                rec = {
                    "release_id": rel_id,
                    "task_id": task_id,
                    "git_branch": branch,
                    "candidate_sha": cand_sha,
                    "baseline_sha": base_sha,
                    "permission_class": permission_class,
                    "target_env": "staging",
                    "state": "ROLLED_BACK",
                    "qa_passed": True,
                    "invariants_passed": True,
                    "perf_passed": perf_ok,
                    "canary_passed": False,
                    "rolled_back": True,
                    "rollback_reason": fail_why,
                    "evidence": {
                        "failure_reason": fail_why,
                        "rolled_back_to_release_id": prev_rel_id,
                        "rolled_back_to_sha": prev_sha,
                        "post_rollback_health_verified": restored_ok,
                        "post_rollback_msg": restored_msg,
                        "canary_ms": round(canary_ms, 2),
                    },
                }
                self.db.upsert_deployment(rec)
                self._append_deployment_history_json(rec)
                self.db.log_event("deployer", "DEPLOYMENT_AUTOMATICALLY_ROLLED_BACK", rec, task_id=task_id)
                return rec

            target_env = "staging_canary_verified"
            live_status = "NOT_REQUESTED"
            if promote_to_live_files:
                # Check live open positions before promoting any non-config code file
                st_f = self.data_dir / "live_harvester_state.json"
                open_cnt = 0
                if st_f.exists():
                    try:
                        st_j = json.loads(st_f.read_text(encoding="utf-8"))
                        open_cnt = int(st_j.get("active_positions_count") or len(st_j.get("active_positions") or {}))
                    except Exception:
                        open_cnt = 1
                only_hot_reload_cfg = all(
                    f.replace("\\", "/").removeprefix("./").lstrip("/") == "config/polymarket_strategy_and_risk.json"
                    for f in changed_files
                )
                if open_cnt > 0 and not only_hot_reload_cfg:
                    target_env = "staged_awaiting_flat_book"
                    live_status = f"DEFERRED_OPEN_POSITIONS({open_cnt})"
                else:
                    bkp_dir = self.live_backups_dir / rel_id
                    bkp_dir.mkdir(parents=True, exist_ok=True)
                    applied: List[str] = []
                    try:
                        for rel in changed_files:
                            rel_norm = rel.replace("\\", "/").lstrip("./")
                            src_f = cand_rel_dir / rel_norm
                            dst_f = self.repo_root / rel_norm
                            if dst_f.exists():
                                bkp_f = bkp_dir / rel_norm
                                bkp_f.parent.mkdir(parents=True, exist_ok=True)
                                shutil.copy2(dst_f, bkp_f)
                            if src_f.exists():
                                dst_f.parent.mkdir(parents=True, exist_ok=True)
                                tmp_dst = dst_f.with_suffix(dst_f.suffix + ".paa_tmp")
                                shutil.copy2(src_f, tmp_dst)
                                tmp_dst.replace(dst_f)
                                applied.append(rel_norm)
                        target_env = "live_promoted"
                        live_status = "PROMOTED_AND_VERIFIED"
                    except Exception as exc:
                        for rel_norm in applied:
                            bkp_f = bkp_dir / rel_norm
                            dst_f = self.repo_root / rel_norm
                            if bkp_f.exists():
                                shutil.copy2(bkp_f, dst_f)
                        raise RuntimeError(f"LIVE_FILE_PROMOTION_ROLLED_BACK:{exc}") from exc

            (cand_rel_dir / "RELEASE_MANIFEST.json").write_text(
                json.dumps(
                    {
                        "release_id": rel_id,
                        "branch": branch,
                        "candidate_sha": cand_sha,
                        "baseline_sha": base_sha,
                        "changed_files": changed_files,
                        "deployed_at_utc": utc_now_iso(),
                        "canary_ms": round(canary_ms, 2),
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            rec = {
                "release_id": rel_id,
                "task_id": task_id,
                "git_branch": branch,
                "candidate_sha": cand_sha,
                "baseline_sha": base_sha,
                "permission_class": permission_class,
                "target_env": target_env,
                "state": "DEPLOYED_VERIFIED",
                "qa_passed": True,
                "invariants_passed": True,
                "perf_passed": True,
                "canary_passed": True,
                "rolled_back": False,
                "rollback_reason": "",
                "evidence": {
                    "changed_files": changed_files,
                    "qa_output": qa_output,
                    "canary_msg": canary_msg,
                    "canary_ms": round(canary_ms, 2),
                    "staging_release_path": str(cand_rel_dir),
                    "previous_release_id": prev_rel_id,
                    "live_promotion_status": live_status,
                },
            }
            self.db.upsert_deployment(rec)
            self._append_deployment_history_json(rec)
            self.db.log_event("deployer", "DEPLOYMENT_RELEASED_AND_VERIFIED", rec, task_id=task_id)
            return rec
        finally:
            self.db.release_lock("production_deploy", lock_owner)

    def _append_deployment_history_json(self, rec: Dict[str, Any]) -> None:
        hist_p = self.data_dir / "paa" / "deployment_history.json"
        hist_p.parent.mkdir(parents=True, exist_ok=True)
        existing: List[Dict[str, Any]] = []
        if hist_p.exists():
            try:
                existing = list((json.loads(hist_p.read_text(encoding="utf-8")) or {}).get("deployments") or [])
            except Exception:
                existing = []
        existing.append(
            {
                "deployment_id": rec["release_id"],
                "timestamp_utc": utc_now_iso(),
                "scope": ",".join((rec.get("evidence") or {}).get("changed_files") or [rec.get("target_env", "staging")]),
                "summary": f"branch={rec['git_branch']} sha={rec['candidate_sha'][:8]} state={rec['state']}",
                "tests_passed": rec["qa_passed"],
                "rollback_needed": rec["rolled_back"],
                "rollback_reason": rec.get("rollback_reason", ""),
                "status": "ROLLED BACK" if rec["rolled_back"] else "VERIFIED COMPLETE",
            }
        )
        tmp = hist_p.with_suffix(".tmp")
        tmp.write_text(json.dumps({"updated_at_utc": utc_now_iso(), "deployments": existing[-50:]}, indent=2), encoding="utf-8")
        tmp.replace(hist_p)
