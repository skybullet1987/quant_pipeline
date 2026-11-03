# PAA PERMANENT OPERATING MEMORY — DEPLOYMENT POLICY (`PAA_DEPLOYMENT_POLICY.md`)
**Authority Level**: Immutable Tier-A Policy (Protected by `PermissionGate` — AI Workers Cannot Modify)

1. **No Direct Live Edits**:
   - AI coding workers are hard-blocked (`PermissionDeniedError`) from executing write modes inside the live repository. All code modifications must occur inside credential-stripped Git worktrees (`/home/skybullet1987/paa_worktrees/`).
2. **Separation of Duties**:
   - A coding agent (`Session B`) cannot certify its own commit.
   - An independent review (`Session C`) + deterministic `DeploymentController` must verify every candidate release before staging or promotion.
3. **Mandatory Release Gates & Rollback**:
   - **Gate 1 (Authorization & Diff Audit)**: `PermissionGate.inspect_candidate_diff` blocks protected policy/security files, `.env` secrets, approval-directory tampering, transfer calls, and exposure increases.
   - **Gate 2 (Executed QA Suite)**: Controller independently runs `py_compile`, `pytest`, and `<1 MiB` bundle checks (`returncode == 0`).
   - **Gate 3 (Accounting & Risk Invariants)**: Schema & risk floor validation (`_deep_merge_validated`) + `ACCOUNTING_SAFEGUARD_ACTIVE` clear.
   - **Gate 4 (Performance Non-Regression)**: Module load & hot-path latency bounds verified.
   - **Gate 5 (Staging & Canary Verification)**: Atomic staging symlink switch + operational canary probe.
   - **Gate 6 (Flat-Book Live Promotion & Auto-Rollback)**: Live restarts blocked while `open_positions_count > 0`; any gate/canary failure automatically rolls back to the verified baseline release and logs forensic evidence.
