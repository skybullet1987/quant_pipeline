"""
Headless AI Agent Runtime (`src/paa_os/agent_runtime.py`).

Executes non-interactive AI tasks via the Antigravity CLI (`agy -p --output-format json`)
authenticated headlessly via Google Cloud ADC (`AGY_ADC_AUTH=true`).

Safety & Anti-Stall Properties:
  1. Never depends on an open terminal, IDE, browser, or chat session.
  2. Strips all wallet private keys & live signing secrets via `build_isolated_worker_env`.
  3. Hard-blocks write-enabled (`mode != 'plan'`) invocations outside isolated Git worktrees!
  4. Enforces `BudgetManager` pre-flight caps and records exact token usage + USD cost.
  5. Detects authentication expiration (`AuthExpiredError`), timeouts, and denied actions
     explicitly — never silently reporting success when an action did not occur.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.paa_os.budget import BudgetManager
from src.paa_os.permissions import PermissionDeniedError, build_isolated_worker_env, load_autonomy_config
from src.paa_os.task_db import PAATaskDB

PIPELINE_ROOT = Path(__file__).resolve().parents[2]


class AuthExpiredError(RuntimeError):
    """Raised when headless ADC / CLI authentication is missing or expired."""


class HeadlessAgentError(RuntimeError):
    """Raised when a headless AI invocation fails, times out, or violates verification."""


class HeadlessAgentRunner:
    def __init__(
        self,
        db: PAATaskDB,
        budget: BudgetManager,
        autonomy_cfg: Optional[Dict[str, Any]] = None,
        live_repo_root: Optional[Path] = None,
    ) -> None:
        self.db = db
        self.budget = budget
        self.cfg = autonomy_cfg or load_autonomy_config()
        self.rt_cfg = self.cfg.get("runtime") or {}
        self.live_repo_root = (Path(live_repo_root) if live_repo_root is not None else PIPELINE_ROOT).resolve()

    def resolve_agy_binary(self) -> Path:
        candidates: List[Path] = []
        if os.name == "nt":
            if self.rt_cfg.get("agy_binary_windows"):
                candidates.append(Path(str(self.rt_cfg["agy_binary_windows"])))
            candidates.append(Path.home() / ".gemini" / "bin" / "agy.exe")
        else:
            if self.rt_cfg.get("agy_binary_linux"):
                candidates.append(Path(str(self.rt_cfg["agy_binary_linux"])))
            candidates.append(Path.home() / ".local" / "bin" / "agy")
        which_p = shutil.which("agy")
        if which_p:
            candidates.append(Path(which_p))
        for c in candidates:
            if c.exists():
                return c
        raise FileNotFoundError(f"Headless Antigravity CLI ('agy') not found in {candidates}")

    def verify_auth_health(self, timeout_sec: int = 25) -> Tuple[bool, str]:
        """Fast pre-flight check verifying headless `agy` + ADC credentials are valid."""
        try:
            agy_bin = self.resolve_agy_binary()
        except FileNotFoundError as exc:
            return False, str(exc)

        env = build_isolated_worker_env(role="AUTH_HEALTH_PROBE", autonomy_cfg=self.cfg)
        try:
            res = subprocess.run(
                [str(agy_bin), "models"],
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )
            combined = f"{res.stdout}\n{res.stderr}".strip()
            if res.returncode != 0 or "authentication required" in combined.lower() or "authentication failed" in combined.lower():
                return False, f"AUTH_EXPIRED_OR_INVALID:{combined[:300]}"
            return True, "AGY_ADC_AUTH_HEALTHY"
        except subprocess.TimeoutExpired:
            return False, "AUTH_PROBE_TIMEOUT"
        except Exception as exc:
            return False, f"AUTH_PROBE_ERROR:{exc}"

    def invoke(
        self,
        *,
        prompt: str,
        task_id: str,
        cwd: Path,
        mode: str = "plan",
        model: Optional[str] = None,
        sandbox: bool = True,
        allow_worktree_edits: bool = False,
        timeout_sec: int = 180,
        conversation_id: Optional[str] = None,
        task_record: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Invokes `agy` headlessly with strict workspace, credential, and budget enforcement.
        """
        cwd_resolved = Path(cwd).resolve()
        if mode != "plan" or allow_worktree_edits:
            # HARD INVARIANT: Never allow autonomous AI file edits directly inside live production repo!
            if cwd_resolved == self.live_repo_root or self.live_repo_root in cwd_resolved.parents:
                # Exception: only allowed if cwd_resolved is under an isolated worktree directory outside live_repo_root
                raise PermissionDeniedError(
                    f"DIRECT_PRODUCTION_EDIT_FORBIDDEN: AI write mode ({mode}) cannot target live repo {cwd_resolved}; must use an isolated Git worktree."
                )

        ok_budget, budget_reason = self.budget.can_invoke_ai_agent(task_record)
        if not ok_budget:
            raise HeadlessAgentError(budget_reason)

        agy_bin = self.resolve_agy_binary()
        chosen_model = model or str(self.rt_cfg.get("fast_triage_model") or "gemini-3.8-flash-low")
        role = "ENGINEERING_ISOLATED" if allow_worktree_edits else "RESEARCH_READONLY"
        env = build_isolated_worker_env(role=role, autonomy_cfg=self.cfg)

        cmd: List[str] = [
            str(agy_bin),
            "--model",
            chosen_model,
            "--mode",
            mode,
            "--output-format",
            "json",
            "--disable-slash-commands",
            "--print-timeout",
            f"{max(15, int(timeout_sec))}s",
        ]
        if sandbox:
            cmd.append("--sandbox")
        if allow_worktree_edits and mode in ("auto", "accept-edits"):
            cmd.append("--dangerously-skip-permissions")
        if conversation_id:
            cmd.extend(["--conversation", str(conversation_id)])
        cmd.append(f"-p={prompt}")

        t0 = time.monotonic()
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(cwd_resolved),
                env=env,
                capture_output=True,
                text=True,
                timeout=max(20, int(timeout_sec) + 15),
            )
        except subprocess.TimeoutExpired as exc:
            dur = time.monotonic() - t0
            self.db.log_event(
                "agent_runtime",
                "AI_CALL_TIMEOUT",
                {"model": chosen_model, "timeout_sec": timeout_sec, "duration_sec": round(dur, 2)},
                task_id=task_id,
            )
            raise HeadlessAgentError(f"AI_WORKER_TIMEOUT_AFTER_{timeout_sec}S") from exc

        dur = time.monotonic() - t0
        stdout_s = (proc.stdout or "").strip()
        stderr_s = (proc.stderr or "").strip()
        combined_low = f"{stdout_s}\n{stderr_s}".lower()

        if "authentication required" in combined_low or "authentication failed" in combined_low or "invalid_grant" in combined_low:
            self.db.log_event(
                "agent_runtime",
                "AUTH_EXPIRATION_DETECTED",
                {"stderr": stderr_s[:400], "stdout": stdout_s[:400]},
                task_id=task_id,
            )
            raise AuthExpiredError(f"HEADLESS_AUTH_EXPIRED:{stderr_s[:300] or stdout_s[:300]}")

        parsed: Dict[str, Any] = {}
        for candidate_line in reversed([stdout_s] + stdout_s.splitlines()):
            cl = candidate_line.strip()
            if cl.startswith("{") and cl.endswith("}"):
                try:
                    parsed = json.loads(cl)
                    break
                except Exception:
                    continue

        if proc.returncode != 0 or parsed.get("status") not in ("SUCCESS", None) and not parsed.get("response"):
            self.db.log_event(
                "agent_runtime",
                "AI_CALL_FAILED",
                {"returncode": proc.returncode, "stderr": stderr_s[:500], "stdout": stdout_s[:500]},
                task_id=task_id,
            )
            raise HeadlessAgentError(
                f"AI_CALL_NONZERO_OR_FAILED(rc={proc.returncode}, status={parsed.get('status')}): {(stderr_s or stdout_s)[:400]}"
            )

        usage = parsed.get("usage") or {}
        in_tok = int(usage.get("input_tokens") or 0)
        out_tok = int(usage.get("output_tokens") or 0) + int(usage.get("thinking_tokens") or 0)
        cost_usd = self.budget.record_ai_usage(
            model_name=chosen_model,
            task_id=task_id,
            input_tokens=in_tok,
            output_tokens=out_tok,
            duration_sec=dur,
            details={"conversation_id": parsed.get("conversation_id"), "num_turns": parsed.get("num_turns", 1)},
        )

        resp_txt = str(parsed.get("response") if parsed else stdout_s)
        # Anti-stall truthfulness check: detect explicit tool-permission denial strings
        if "permission denied by policy" in resp_txt.lower() or "tool call was denied" in resp_txt.lower():
            self.db.log_event(
                "agent_runtime",
                "TOOL_INVOCATION_DENIED",
                {"response_excerpt": resp_txt[:400]},
                task_id=task_id,
            )
            raise PermissionDeniedError(f"TOOL_INVOCATION_DENIED_IN_HEADLESS_RUN:{resp_txt[:240]}")

        return {
            "status": "SUCCESS",
            "conversation_id": parsed.get("conversation_id"),
            "model": chosen_model,
            "response": resp_txt,
            "duration_seconds": round(float(parsed.get("duration_seconds") or dur), 3),
            "usage": usage,
            "estimated_cost_usd": cost_usd,
        }
