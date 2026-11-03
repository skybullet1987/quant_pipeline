# PAA PERMANENT OPERATING MEMORY — VERIFICATION & EPISTEMIC POLICY (`PAA_VERIFICATION_POLICY.md`)
**Authority Level**: Immutable Tier-A Policy (Protected by `PermissionGate` — AI Workers Cannot Modify)

1. **Epistemic Claim Classes (Mandatory Explicit Classification)**:
   - `VERIFIED_FACT`: Backed by controller-verified authoritative source (SQLite receipt, on-chain/state ledger, `git cat-file`, `pytest` exit code `0`, `systemctl` probe) within valid `ttl_sec`.
   - `OBSERVATION`: Point-in-time external measurement with explicit timestamp and expiry (`ttl_sec`); degrades to `STALE_REVALIDATION_REQUIRED` once expired.
   - `HYPOTHESIS`: Unproven research or engineering conjecture awaiting empirical test.
   - `ESTIMATE`: Modelled projection or heuristic calculation clearly labeled as non-realized.
   - `UNKNOWN`: Insufficient or missing observable evidence; must remain `UNKNOWN` (never invented).
   - `CONTRADICTED`: Refuted by authoritative ledger, Git repository, test runner, or deployment registry -> immediately rejected!
2. **Tier-C Research Evidence Ladder (Separate from Live Facts)**:
   - `HYPOTHESIS` -> `BACKTESTED` -> `OOS_TESTED` -> `SHADOW_VALIDATED` -> `LIVE_VERIFIED`.
   - A strategy may NEVER be labeled `LIVE_VERIFIED` unless reconciled real-money live trades exist in the authoritative ledger.
3. **Five Deterministic Verification Gates**:
   - **Gate 1 — Evidence Gate**: Rejects unbacked claims or forces `UNKNOWN`; never fabricates balances, fills, commit hashes, test results, or probabilities.
   - **Gate 2 — Test Gate**: Controller executes `pytest` / `py_compile` / AST checks directly; worker text claiming "tests passed" without an executed controller receipt is rejected.
   - **Gate 3 — Independent Review Gate**: Separate stateless review inspects the actual diff/artifacts without trusting the worker's self-assessment, backed by deterministic executable checks.
   - **Gate 4 — Authorization Gate**: Non-AI `PermissionGate` enforces 3-class permissions, protected policy files, and risk envelopes.
   - **Gate 5 — Financial & Contradiction Gate**: Cross-checks claimed cash, PnL, commit SHAs, release IDs, and `LIVE_VERIFIED` claims against authoritative records.
   - **Invariants**: `NO EVIDENCE = NO VERIFIED CLAIM` · `NO VERIFIED RELEASE = NO PRODUCTION PROMOTION` · `NO CONTEXT DEPENDENCY = NO FORGOTTEN WORK`.
