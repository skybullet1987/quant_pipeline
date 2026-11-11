# DOMINUS v5.0 — Exhaustive Internal Policy, Gate, Freeze & Governance Audit (`POLICY_AUDIT.md`)

**Campaign:** DOMINUS v5.0 Supreme Profit & Operational Freedom (Phase 1 / Requirement R2)  
**Auditor:** Agent G (`@policy-auditor` — Policy, Permissions & Owner-Control Auditor)  
**Audit Timestamp:** 2026-11-11 UTC  
**Production Baseline Context:**
- **Liquid Trading Cash (`pUSD`):** `$47.38`
- **Disputed Open Positions:** `$50.51` cost basis across 4 `KMIA` Nov 7 weather positions (`markets 6707502 & 6707503`, `~2c` bid = `$0.14` mark-to-bid value)
- **Mark-to-Bid Reconciled NAV:** `$47.52` (`$47.38` cash + `$0.14` bid value)
- **Persisted Harvester Book Equity (`total_account_equity`):** `$97.89` (`$47.38` cash + `$50.51` cost-basis frozen UMA receivable)
- **Infrastructure Burn (`quant-pipeline-finland`, `e2-custom-2-4096`, `4 GB` RAM, `europe-north1-b`):** `~$24.67/mo` (`~$0.82/day`) actual vs. `$52.56/mo` (`$1.752/day`) stale config rate in [paa_autonomy_config.json](file:///C:/Users/Anton/source/repos/Dominus/config/paa_autonomy_config.json#L67)

---

## 1. Executive Summary & Audit Methodology

Every internal policy, permission boundary, numerical freeze, graduation gate, bankroll/NAV tier gate, concentration cap, shadow/live firewall, resource fence, and emergency halt across the Dominus repository was inspected directly from source code and read-only production state on `kraken-finland`.

### Mandatory 10-Question Audit Schema
For every policy `POL-01` through `POL-26` below, all 10 mandatory audit questions are explicitly answered:
- **`Q1`** Why was this policy created?
- **`Q2`** Which specific risk did it address?
- **`Q3`** Does that risk still exist today?
- **`Q4`** Is it externally mandatory (legal/provider) or an internal design choice?
- **`Q5`** Does it block valid, mathematically profitable opportunities?
- **`Q6`** Can the same protection be achieved more efficiently?
- **`Q7`** Is the rule overly broad or misaligned with current `$47.38` liquid / `$97.89` book capital?
- **`Q8`** Can it be safely automated without weakening security?
- **`Q9`** What empirical/code evidence supports keeping, modifying, or removing it?
- **`Q10`** Who is authorized to approve changing it?

### High-Level Verdict Distribution (26 Policies Audited)
| Verdict | Count | Policy IDs | Core Theme |
| :--- | :---: | :--- | :--- |
| **`RETAIN` (Immutable Safety)** | **9** | `POL-01`, `POL-02`, `POL-03`, `POL-04`, `POL-11`, `POL-12`, `POL-14`, `POL-22`, `POL-25` | Zero-trust anti-tampering, secret stripping, isolated Git worktrees, `<UNTRUSTED_DATA_ONLY>` prompt-injection wall, accounting-discrepancy safeguard (`>$1.50` / `0.75` shares), Double-Zero 5-gate cross-venue verifier, 0-signing-key shadow `.env` fence |
| **`OPTIMIZE` (Fix Bug / Recalibrate)** | **12** | `POL-05`, `POL-06`, `POL-07`, `POL-08`, `POL-09`, `POL-10`, `POL-13`, `POL-17`, `POL-18`, `POL-20`, `POL-23`, `POL-26` | Owner-approval scope mismatch & wildcard-TTL bug, `proposal_only_live_promotion` friction, flat-book restart gate blocking UMA-frozen code deploys, `polymarket_all_in_one.py` `<1 MB` canary bundle headroom & binary-diff hygiene, emergency-stop gaps, `$62.00` ruin-floor cliff on `$47.38` cash, `$97.89` book vs `$47.52` NAV tier/concentration distortion, `15%` station cap exemptions, stale `$0.0730/hr` VM cost drag |
| **`REPLACE` (Surgical Upgrade)** | **3** | `POL-15`, `POL-16`, `POL-19` | Replace conflicting 3-way graduation & `strict_pure_riskless_mode` allowlist (which blocks graduated `CAL1`/`COND1` while permitting single-leg `W1`/`W_PRUNE1` weather locks) with unified payoff-structure gating; replace `<$500` sequential bundle ambiguity with explicit NAV-gated atomic/2-leg enforcement |
| **`REMOVE` (Legacy / Dead)** | **2** | `POL-21`, `POL-24` | Remove stale `enable_ungraduated_v3_math_live: true` contradiction in `polymarket_strategy_and_risk.json` and obsolete legacy `polymarket_risk_config.json` (`$48` floor / `$24` exposure) shadow-config drift |

---

## 2. Exhaustive 26-Policy Audit (All 10 Mandatory Questions Answered Per Policy)

### Group A — PAA OS Zero-Trust Security, Permissions & Release Governance

#### `POL-01`: Non-Overridable Anti-Self-Approval, Credential & Transfer Tampering Firewall
- **Locations:** [permissions.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L43-L52) (`SENSITIVE_SIGNING_ENV_KEYS`), [permissions.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L161-L170) (`self.forbidden_patterns`), [`PermissionGate.inspect_candidate_diff`](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L316-L363), [paa_autonomy_config.json](file:///C:/Users/Anton/source/repos/Dominus/config/paa_autonomy_config.json#L116-L122) (`forbidden_diff_patterns`), [PAA_AUTONOMY_POLICY.md](file:///C:/Users/Anton/source/repos/Dominus/config/policies/PAA_AUTONOMY_POLICY.md#L1-L15)
- **`Q1` Why created:** Prevent autonomous coding agents (`PAADirector` / `HeadlessAgentRunner`) from forging human approvals in `data/polymarket/paa/approvals/`, editing `.env`/`.key`/`.pem` files, or injecting raw signing-key references and on-chain transfer calls into candidate diffs.
- **`Q2` Risk addressed:** Autonomous privilege escalation, credential exfiltration, and unauthorized on-chain fund transfers.
- **`Q3` Still exists:** **Yes (permanent existential risk)** whenever LLM-based autonomous workers generate code diffs.
- **`Q4` Mandatory vs. internal:** Internal security invariant (strictly non-overridable campaign boundary).
- **`Q5` Blocks valid profit:** **No (`$0.00/mo` lost EV).** Legitimate trading code never needs to forge approval JSONs or inject `safeTransferFrom(` / `eth_sendRawTransaction` calls.
- **`Q6` More efficient alternative:** Keep the non-overridable path + substring hard-veto before any scope-override check (`SELF_APPROVAL_TAMPERING_FORBIDDEN` and `FORBIDDEN_CREDENTIAL_OR_TRANSFER_PATTERN` return `False` immediately at [permissions.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L354-L359)), and optionally expand `forbidden_diff_patterns` (`["POLYGON_PRIVATE_KEY", "HYPERLIQUID_PRIVATE_KEY", "POLY_BUILDER_SECRET", "safeTransferFrom(", "eth_sendRawTransaction"]` at [paa_autonomy_config.json](file:///C:/Users/Anton/source/repos/Dominus/config/paa_autonomy_config.json#L116-L122)) to also cover `MNEMONIC`, `eth_sendTransaction`, and ERC-20 `.transfer(` / `withdraw(`.
- **`Q7` Overly broad:** **No.** Current substring checks in `self.forbidden_patterns` ([permissions.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L161-L170) & [#L344-L346](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L344-L346)) inspect only `+` added diff lines and have caused zero false blocks in production.
- **`Q8` Safe automation:** Already 100% automated and deterministic in `PermissionGate.inspect_candidate_diff`.
- **`Q9` Evidence:** Verified in [permissions.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L332-L359) and unit-tested in `tests/test_qa_boost_audit_remediation.py`.
- **`Q10` Approval authority:** **Human Owner ONLY (Never weaken — Strict Campaign Safety Boundary).**
- **Verdict:** **`RETAIN`**

---

#### `POL-02`: Worker Environment Secret Stripping & Ephemeral Git Worktree Isolation
- **Locations:** [`SENSITIVE_SIGNING_ENV_KEYS` & `build_isolated_worker_env`](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L43-L94), [`GitWorktreeBuilder`](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/builder_and_deployer.py#L65-L225), [`HeadlessAgentRunner.invoke`](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/agent_runtime.py#L99-L210)
- **`Q1` Why created:** Ensure headless `agy` worker subprocesses run in isolated Git worktrees (`/home/skybullet1987/paa_worktrees`) with all `SENSITIVE_SIGNING_ENV_KEYS` (`POLYGON_PRIVATE_KEY`, `HYPERLIQUID_PRIVATE_KEY`, `POLY_BUILDER_SECRET`, `POLY_BUILDER_PASSPHRASE`, `POLY_BUILDER_API_KEY`, `EXECUTION_LIVE_CONFIRMED`, `PRIVATE_KEY`, `MNEMONIC`) and any `*PRIVATE_KEY*`/`*SECRET*`/`*PASSPHRASE*` env vars stripped, while marking `PAA_WORKER_ROLE` and `PAA_SIGNING_DISABLED="1"`.
- **`Q2` Risk addressed:** Accidental live-tree file corruption during mid-edit crashes and subprocess secret leakage.
- **`Q3` Still exists:** **Yes.** Running live daemons execute directly out of `/home/skybullet1987/quant_pipeline`.
- **`Q4` Mandatory vs. internal:** Internal defence-in-depth engineering architecture.
- **`Q5` Blocks valid profit:** **No.** Worktrees add `<150ms` overhead per engineering task.
- **`Q6` More efficient alternative:** None needed; `git worktree add --detach` shares the Git object store with near-zero disk cost.
- **`Q7` Overly broad:** **No.** Any non-protected repo path outside `protected_files` ([paa_autonomy_config.json](file:///C:/Users/Anton/source/repos/Dominus/config/paa_autonomy_config.json#L98-L115)), `config/policies/*`, `.env`/`.key`/`.pem`, and `data/polymarket/paa/approvals` ([permissions.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L332-L336)) remains editable inside worktrees for legitimate engineering tasks.
- **`Q8` Safe automation:** Fully automated with `finally:` worktree cleanup ([zero_trust.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/zero_trust.py#L975-L982)).
- **`Q9` Evidence:** [permissions.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L62-L94) strips `SENSITIVE_SIGNING_ENV_KEYS` plus `PRIVATE_KEY`/`SECRET`/`PASSPHRASE` substrings while setting `PAA_SIGNING_DISABLED="1"` and preserving `PATH`/`PYTHONPATH`/`HOME`.
- **`Q10` Approval authority:** **Human Owner ONLY (Never weaken).**
- **Verdict:** **`RETAIN`**

---

#### `POL-03`: Protected Governance & Core PAA Control-Plane File Lock
- **Locations:** [paa_autonomy_config.json](file:///C:/Users/Anton/source/repos/Dominus/config/paa_autonomy_config.json#L98-L115), [`PermissionGate.__init__`](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L137-L160), [`PermissionGate.inspect_candidate_diff`](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L332-L334)
- **`Q1` Why created:** Prevent autonomous tasks from rewriting their own governance, deployment, verification, accounting, or account-setup gates (`.env`, `src/paa_os/permissions.py`, `src/paa_os/zero_trust.py`, `src/paa_os/builder_and_deployer.py`, `src/paa_os/accountant.py`, `src/polymarket_research/cross_venue_shadow_deployment_gates.py`, `src/polymarket_research/cross_venue_unblock_and_certification.py`, `src/polymarket_research/execute_approvals.py`, `src/polymarket_research/setup_polymarket_account.py`, `config/paa_master_mandate.md`, `config/paa_autonomy_config.json`, and `config/policies/*`).
- **`Q2` Risk addressed:** Goodhart's Law / reward-hacking (an agent modifying `accountant.py`, `builder_and_deployer.py`, `cross_venue_shadow_deployment_gates.py`, or `permissions.py` to fake profit or bypass deployment/compliance gates).
- **`Q3` Still exists:** **Yes.**
- **`Q4` Mandatory vs. internal:** Internal governance boundary.
- **`Q5` Blocks valid profit:** **No (`$0.00/mo` lost EV).** Core execution & strategy modules (`polymarket_live_harvester.py`, `polymarket_executor.py`, `riskless_protocol_v2_expansion.py`) are intentionally **not** in `protected_files`, while changes to protected control-plane/Stage-G gate files rightly require human owner commits or explicit `CREDENTIAL_OR_PERMISSION_EXPANSION` approval.
- **`Q6` More efficient alternative:** Keep the 16 `protected_files` entries locked for unattended cron workers, and consider adding `src/polymarket_research/polymarket_executor.py` (which signs EIP-712 orders and CTF transactions) if unattended autonomous cron builds are ever re-enabled above `$5,000` NAV.
- **`Q7` Overly broad:** Note `src/polymarket_research/execute_approvals.py` ([paa_autonomy_config.json](file:///C:/Users/Anton/source/repos/Dominus/config/paa_autonomy_config.json#L106)) is listed defensively (protecting the on-chain token allowance setup script path), while human PAA approval helpers belong in `scripts/paa_cli.py`.
- **`Q8` Safe automation:** Already automated in `inspect_candidate_diff`.
- **`Q9` Evidence:** [paa_autonomy_config.json](file:///C:/Users/Anton/source/repos/Dominus/config/paa_autonomy_config.json#L98-L115) & [permissions.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L140-L159) & [#L333-L334](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L333-L334).
- **`Q10` Approval authority:** **Human Owner (`CREDENTIAL_OR_PERMISSION_EXPANSION` scope or direct owner Git commit).**
- **Verdict:** **`RETAIN`**

---

#### `POL-04`: Zero-Trust Untrusted Input Sanitizer & Independent Verifier Gate
- **Locations:** [`sanitize_untrusted_external_text`](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/zero_trust.py#L38-L82), [`ZeroTrustVerifier.verify_and_finalize_task`](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/zero_trust.py#L593-L774), [PAA_VERIFICATION_POLICY.md](file:///C:/Users/Anton/source/repos/Dominus/config/policies/PAA_VERIFICATION_POLICY.md#L1-L20)
- **`Q1` Why created:** Strip prompt-injection directives from external Gamma/UMA market descriptions (`<UNTRUSTED_DATA_ONLY>`) and force independent `py_compile`, `pytest`, claim-citation checks, and `<30s` canary probes before any autonomous commit is staged.
- **`Q2` Risk addressed:** Indirect prompt injection via malicious Polymarket market titles/descriptions and hallucinated/untested agent code edits.
- **`Q3` Still exists:** **Yes.** Anyone can create permissionless markets or UMA ancillary text containing adversarial instructions.
- **`Q4` Mandatory vs. internal:** Internal security & QA invariant.
- **`Q5` Blocks valid profit:** **No.** Protects live uptime from broken autonomous commits.
- **`Q6` More efficient alternative:** Current design is fast (`py_compile` + targeted `pytest` + credential-stripped `_run_release_canary_probe` in [builder_and_deployer.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/builder_and_deployer.py#L311-L360)).
- **`Q7` Overly broad:** **No.** Separate `polymarket_all_in_one.py < 1,000,000` byte canary ceiling (`builder_and_deployer.py:326-335`) is audited in `POL-08`.
- **`Q8` Safe automation:** Already automated.
- **`Q9` Evidence:** [zero_trust.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/zero_trust.py#L38-L82) & [zero_trust.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/zero_trust.py#L593-L774).
- **`Q10` Approval authority:** **Human Owner.**
- **Verdict:** **`RETAIN`**

---

#### `POL-05`: Operator Approval JSON Flow & Scope-Matching Envelope (`data/polymarket/paa/approvals/`)
- **Locations:** [`has_explicit_operator_approval`](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L97-L123), [`PermissionGate.inspect_config_envelope`](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L199-L314), [`PermissionGate.inspect_candidate_diff`](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L348-L363), [`DeploymentController._is_live_promotion_blocked_by_proposal_only`](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/builder_and_deployer.py#L419-L428)
- **`Q1` Why created:** Require explicit human sign-off (Class C) before raising risk caps, unpausing sleeves, lowering ruin floors, or promoting staged changes to live production.
- **`Q2` Risk addressed:** Unapproved autonomous risk escalation.
- **`Q3` Still exists:** **Yes.**
- **`Q4` Mandatory vs. internal:** Internal owner-control mechanism.
- **`Q5` Blocks valid profit:** **YES — due to 4 concrete technical bugs in the approval implementation:**
  1. **Conjoined AND-Scope Bug ([permissions.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L308-L313)):** `inspect_config_envelope` clears config violations ONLY if **BOTH** `ok_exp` (`INCREASE_CAPITAL_EXPOSURE`) **AND** `ok_live` (`NEW_LIVE_TRADING_ACTIVATION`) are `True` (`if ok_exp and ok_live: return True, []`). If the owner approves `NEW_LIVE_TRADING_ACTIVATION` alone to unpause `CAL1` without changing exposure caps, `inspect_config_envelope` **REJECTS** the owner's approval!
  2. **Scope Conflation Bug in Diff Gate ([permissions.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L360-L362)):** When `inspect_config_envelope` fails inside `inspect_candidate_diff`, line `360` checks `has_explicit_operator_approval("CREDENTIAL_OR_PERMISSION_EXPANSION", release_id)`—a completely different scope!
  3. **Undocumented Scope Outside `explicit_scopes` ([builder_and_deployer.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/builder_and_deployer.py#L419-L428)):** Live promotion under `proposal_only_live_promotion` requires `"LIVE_PRODUCTION_PROMOTION"`, which is absent from `explicit_scopes` in [permissions.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L180-L188) and undocumented in [paa_autonomy_config.json](file:///C:/Users/Anton/source/repos/Dominus/config/paa_autonomy_config.json#L90-L122).
  4. **Missing Expiry (`expires_at_utc`) & Missing One-Shot Consumption ([permissions.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L109-L123)):** Verified live on `kraken-finland`: `data/polymarket/paa/approvals/operator_approval_20261103_zero_loss_seed_focus.json` has `"target_id": "*"` from Nov 3, 2026 and **never expires**. Any `"target_id": "*"` approval file stays active forever across all future releases! Also, `paa_cli.py` has zero subcommand (`approve` / `list-approvals` / `revoke-approval`) for the owner.
- **`Q6` More efficient alternative:** Map each violation prefix (`RISK_CAP_EXCEEDED`/`RISK_FLOOR_WEAKENED` -> `INCREASE_CAPITAL_EXPOSURE`; `NEW_LIVE_*` -> `NEW_LIVE_TRADING_ACTIVATION`; `PROTECTED_FILE_MODIFIED` -> `CREDENTIAL_OR_PERMISSION_EXPANSION`), enforce `expires_at_utc` + `consumed_by_release_id` on approval records, and add human-only `paa_cli.py` approval management commands (guarded against `PAA_SIGNING_DISABLED == "1"` / `PAA_WORKER_ROLE` subprocesses).
- **`Q7` Overly broad:** Both **over-obstructive** to legitimate single-scope owner approvals AND **under-scoped** on wildcard TTL!
- **`Q8` Safe automation:** Validation & consumption tracking can be 100% automated while keeping approval *creation* strictly human-only.
- **`Q9` Evidence:** Exact code at [permissions.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L97-L123), [permissions.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L308-L313), [permissions.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L360-L362), [builder_and_deployer.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/builder_and_deployer.py#L419-L428), plus live file `operator_approval_20261103_zero_loss_seed_focus.json`.
- **`Q10` Approval authority:** **Human Owner.**
- **Verdict:** **`OPTIMIZE` (P0 Owner-Control Bugfix)**

---

#### `POL-06`: Proposal-Only Live Promotion Below `$5,000` NAV (`proposal_only_live_promotion`)
- **Locations:** [paa_autonomy_config.json](file:///C:/Users/Anton/source/repos/Dominus/config/paa_autonomy_config.json#L95-L96), [`DeploymentController._is_live_promotion_blocked_by_proposal_only`](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/builder_and_deployer.py#L387-L429), [PAA_DEPLOYMENT_POLICY.md](file:///C:/Users/Anton/source/repos/Dominus/config/policies/PAA_DEPLOYMENT_POLICY.md#L1-L15)
- **`Q1` Why created:** Prevent unattended background LLM cron loops (`hourly-opt`, `director-cycle`) from overwriting live production files and restarting `polymarket-live-harvester.service` while bankroll is in seed rebuild (`<$5,000` NAV).
- **`Q2` Risk addressed:** Unattended autonomous regressions wiping out micro-capital (`$47.38`) or interrupting live arbitrage fills.
- **`Q3` Still exists:** **Yes** for *unattended LLM-generated code mutations*.
- **`Q4` Mandatory vs. internal:** Internal governance choice (`proposal_only_live_promotion: true`, `proposal_only_below_nav_usd: 5000.0`).
- **`Q5` Blocks valid profit:** Blocks unattended auto-promotion of PAA worker drafts (`staged_proposal_awaiting_operator_approval`), which is **safe and intended**, EXCEPT when the owner wants a 1-command CLI promotion of a staged release (`release_id`)—currently there is no `paa_cli.py promote-release <release_id>` command, forcing manual JSON file creation + manual file copy.
- **`Q6` More efficient alternative:** Keep `proposal_only_live_promotion: true` below `$500`–`$5,000` NAV for unattended LLM cron tasks, AND add an interactive owner CLI command (`paa_cli.py approve-and-promote <release_id>`) so owner sign-off takes 5 seconds instead of manual JSON crafting. Also note: [`_is_live_promotion_blocked_by_proposal_only`](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/builder_and_deployer.py#L408-L413) reads `live_harvester_state.json` `total_account_equity` (book `$97.89`) rather than mark-to-bid NAV (`$47.52`), which should use reconciled mark-to-bid NAV.
- **`Q7` Overly broad:** Safe default for autonomous agents; only obstructive due to missing owner CLI promotion workflow.
- **`Q8` Safe automation:** Staging + canary verification is automated; final live flip stays 1-click owner-approved below `$5,000` NAV.
- **`Q9` Evidence:** [builder_and_deployer.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/builder_and_deployer.py#L387-L429) & `test_paa_proposal_only_mode_stages_draft_and_blocks_live_overwrite_until_human_approval` in [test_qa_boost_audit_remediation.py](file:///C:/Users/Anton/source/repos/Dominus/tests/test_qa_boost_audit_remediation.py#L485-L567).
- **`Q10` Approval authority:** **Human Owner.**
- **Verdict:** **`OPTIMIZE` (Keep gate; add 1-command owner CLI promotion + reconciled NAV read)**

---

#### `POL-07`: Open-Position Restart Lock (`active_positions_count == 0`) Across Deployers
- **Locations:** [`DeploymentController.release_candidate`](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/builder_and_deployer.py#L658-L675), [`redeploy_daemon`](file:///C:/Users/Anton/source/repos/Dominus/audit_losing_trades.py#L420-L433), [`_is_restart_safe_frozen_uma_lock`](file:///C:/Users/Anton/source/repos/Dominus/scripts/paa_flat_harvester_redeploy_once.py#L36-L70)
- **`Q1` Why created:** Avoid restarting `polymarket-live-harvester.service` mid-candle while an active directional position needs `hold_98` / MFE-ratchet stop supervision or a 2-leg box unwind is in flight.
- **`Q2` Risk addressed:** Unmonitored stop-loss breach or orphaned partial-leg unwind during a 3–8s daemon restart.
- **`Q3` Still exists:** **Yes** for *actively managed pre-expiry or unwinding positions*; **NO** for *post-expiry frozen UMA disputed positions* (`KMIA` Nov 7, expired >72h ago, `0` resting orders, `hold_to_maturity_lock=True`).
- **`Q4` Mandatory vs. internal:** Internal operational safety gate.
- **`Q5` Blocks valid profit:** **YES!** Right now `active_positions_count == 4` due to the 4 disputed `KMIA` positions (`$50.51`). While [`paa_flat_harvester_redeploy_once.py`](file:///C:/Users/Anton/source/repos/Dominus/scripts/paa_flat_harvester_redeploy_once.py#L36-L70) was patched with `_is_restart_safe_frozen_uma_lock()`, **BOTH** [`builder_and_deployer.py`](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/builder_and_deployer.py#L663-L675) **AND** [`audit_losing_trades.py`](file:///C:/Users/Anton/source/repos/Dominus/audit_losing_trades.py#L423-L429) still check raw `open_cnt > 0` (`DEFERRED_OPEN_POSITIONS`), blocking legitimate owner-approved releases for days during multi-day UMA DVM disputes!
- **`Q6` More efficient alternative:** Extract `_is_restart_safe_frozen_uma_lock(pos, now_ts)` + `pending_entry_intents == 0` into a shared helper and use it in `builder_and_deployer.py` and `audit_losing_trades.py` so restarts block ONLY when non-frozen/in-flight positions or resting Maker intents exist.
- **`Q7` Overly broad:** **Yes** in `builder_and_deployer.py` and `audit_losing_trades.py` (treats multi-day passive UMA settlement receivables identically to live 15m directional positions).
- **`Q8` Safe automation:** 100% deterministically automatable via `is_post_expiry_uma_frozen_lock` + `pending_entry_intents` check.
- **`Q9` Evidence:** Contrast [paa_flat_harvester_redeploy_once.py](file:///C:/Users/Anton/source/repos/Dominus/scripts/paa_flat_harvester_redeploy_once.py#L36-L70) (smart check) vs. [builder_and_deployer.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/builder_and_deployer.py#L663-L675) & [audit_losing_trades.py](file:///C:/Users/Anton/source/repos/Dominus/audit_losing_trades.py#L423-L429) (raw count check).
- **`Q10` Approval authority:** **Human Owner.**
- **Verdict:** **`OPTIMIZE` (Unify UMA-frozen restart-safety predicate across all 3 deployers)**

---

#### `POL-08`: `polymarket_all_in_one.py` `< 1,000,000`-Byte Canary Ceiling, CRLF Guard & `30s` Canary Probe
- **Locations:** [`DeploymentController._run_release_canary_probe`](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/builder_and_deployer.py#L311-L360) (specifically `#L326-L335`), [PAA_DEPLOYMENT_POLICY.md](file:///C:/Users/Anton/source/repos/Dominus/config/policies/PAA_DEPLOYMENT_POLICY.md#L11)
- **`Q1` Why created:** Prevent the legacy single-file bundle `polymarket_all_in_one.py` from exceeding `1,000,000` bytes (`BUNDLE_SIZE_CEILING_EXCEEDED`) or acquiring Windows `\r\n` line endings (`BUNDLE_CRLF_DETECTED`), while `py_compile`-checking every `.py` file in `release_dir` and running optional canary commands inside a `30.0s` credential-stripped subprocess.
- **`Q2` Risk addressed:** Single-file bundle bloat, CRLF shebang/script corruption on Linux, and broken syntax/config invariants before promotion.
- **`Q3` Still exists:** **Yes.**
- **`Q4` Mandatory vs. internal:** Internal engineering hygiene gate.
- **`Q5` Blocks valid profit:** **No immediate block on modular edits** (modifying `riskless_protocol_v2_expansion.py` and `polymarket_live_harvester.py` does **not** trigger `L326-335` because `_run_release_canary_probe` checks **only** `if pyf.name == "polymarket_all_in_one.py"`). However, two forward-looking gaps exist: (1) root `polymarket_all_in_one.py` is already **`910,713` bytes (`91.1%` of the `1,000,000`-byte cap — only `89,287` bytes remaining)**, and (2) non-`.py` artifacts (`.sqlite3`, `.jsonl`, `.parquet`) have no file-size or extension check in `inspect_candidate_diff` / `_run_release_canary_probe`.
- **`Q6` More efficient alternative:** Keep the `polymarket_all_in_one.py` LF check (`b"\r\n"` block) and `py_compile` pass, deprecate/freeze growth of `polymarket_all_in_one.py` in favor of modular `src/polymarket_research/*` packages, and add a binary/data-extension block (`.sqlite3`, `.jsonl`, `.parquet`, `.pkl`) in `inspect_candidate_diff`.
- **`Q7` Overly broad:** Narrowly scoped to `polymarket_all_in_one.py` (`< 1,000,000` bytes), which is `89.3 KB` away from its ceiling while non-`.py` data dumps are unchecked.
- **`Q8` Safe automation:** 100% automated in `DeploymentController._run_release_canary_probe`.
- **`Q9` Evidence:** [builder_and_deployer.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/builder_and_deployer.py#L326-L335) vs. current `polymarket_all_in_one.py` size (`910,713` bytes).
- **`Q10` Approval authority:** **Human Owner.**
- **Verdict:** **`OPTIMIZE`**

---

#### `POL-09`: Trade-Forensics 3-Verdict Wall & WFO Numerical Parameter Freeze
- **Locations:** [SKILL.md](file:///C:/Users/Anton/source/repos/Dominus/.agents/skills/trade-forensics/SKILL.md#L27-L69), [`mark_audited`](file:///C:/Users/Anton/source/repos/Dominus/audit_losing_trades.py#L342-L418), [`append_wfo_hypothesis_queue`](file:///C:/Users/Anton/source/repos/Dominus/audit_losing_trades.py#L156-L160)
- **`Q1` Why created:** Stop reactive sample-size-1 (`N=1`) overfitting after single losing trades (e.g., tweaking `Z`, `OFI`, `ask_cap`, or stop ticks ad hoc after one loss, which historically caused negative OOS expectancy).
- **`Q2` Risk addressed:** Sample-of-one parameter thrashing / backtest overfitting.
- **`Q3` Still exists:** **Yes** for *statistical signal thresholds* (`Z`, `OFI`, `cushion`, `TP/SL` prices).
- **`Q4` Mandatory vs. internal:** Internal quantitative research governance.
- **`Q5` Blocks valid profit:** Does **not** block deterministic infrastructure/execution bugfixes (`VERDICT 1: DETERMINISTIC_INFRA_BUG` allows immediate code patches for race conditions, fee math, stale quotes, concentration/unwind bugs). However, it freezes **non-directional operational config parameters** (like `hard_ruin_floor_usd: 62.0` or `seed_max_lockup_hours`) if misclassified as "strategy thresholds" instead of accounting/capital-tier settings.
- **`Q6` More efficient alternative:** Explicitly scope the WFO numerical parameter freeze to *probabilistic alpha/signal & TP/SL thresholds*, while allowing deterministic risk-envelope & accounting-alignment fixes (with owner approval) without waiting for `N >= 50` directional trades (which never accumulate while `riskless_only_mode: true`!).
- **`Q7` Overly broad:** **Deadlock nuance:** While `riskless_only_mode: true` is active, live directional trades accumulate at `0/week`, and only shadow directional ledgers accumulate `N >= 50` for [`weekly_wfo_governance.py`](file:///C:/Users/Anton/source/repos/Dominus/scripts/weekly_wfo_governance.py#L83-L119). Clarifying that riskless structural parameters (`min_net_edge_bps`, `seed_max_lockup_hours`, `hard_ruin_floor_usd`) are governed by fee/fill math + owner approval rather than directional WFO resolves this ambiguity.
- **`Q8` Safe automation:** Already automated via `audit_losing_trades.py --mark-audited` enforcing `{"VARIANCE_WITHIN_SPEC", "DETERMINISTIC_INFRA_BUG", "HYPOTHESIS_QUEUED_FOR_WFO"}` ([audit_losing_trades.py](file:///C:/Users/Anton/source/repos/Dominus/audit_losing_trades.py#L351-L361)).
- **`Q9` Evidence:** [SKILL.md](file:///C:/Users/Anton/source/repos/Dominus/.agents/skills/trade-forensics/SKILL.md#L27-L69) & [audit_losing_trades.py](file:///C:/Users/Anton/source/repos/Dominus/audit_losing_trades.py#L342-L418).
- **`Q10` Approval authority:** **Human Owner.**
- **Verdict:** **`OPTIMIZE` (Retain 3-Verdict Wall for directional thresholds; explicitly exempt deterministic riskless/accounting envelope calibration)**

---

#### `POL-10`: PAA AI Budget, Concurrency & Stale VM Infrastructure Cost Hurdle
- **Locations:** [paa_autonomy_config.json](file:///C:/Users/Anton/source/repos/Dominus/config/paa_autonomy_config.json#L59-L76), [`BudgetManager.get_usage_summary`](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/budget.py#L81-L147), [`BudgetManager.can_invoke_ai_agent`](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/budget.py#L149-L170), [`BudgetManager.check_engineering_concurrency`](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/budget.py#L171-L177)
- **`Q1` Why created:** Cap autonomous AI invocations (`max_daily_ai_invocations: 96`, `max_hourly_ai_invocations: 8`, `max_daily_ai_cost_usd: $2.50` with a `1.5x` emergency cap multiplier for `P0` tasks, `max_simultaneous_engineering_jobs: 1`, `min_expected_daily_ev_for_ai_build_usd: $0.25` for non-`P0`/`P1` optimization/discovery) and deduct VM infra burn from net economic profit.
- **`Q2` Risk addressed:** Runaway autonomous API spend exceeding trading profits on a micro-bankroll.
- **`Q3` Still exists:** **Yes.** At `$47.38` liquid cash, every `$1/day` of fixed overhead is `770%/yr` annualized drag!
- **`Q4` Mandatory vs. internal:** Internal cost-control policy.
- **`Q5` Blocks valid profit:** **Config drift bug found:** [paa_autonomy_config.json](file:///C:/Users/Anton/source/repos/Dominus/config/paa_autonomy_config.json#L67) and fallback [budget.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/budget.py#L116) hardcode `"prorated_vm_hourly_cost_usd": 0.0730` (**`$1.752/day` = `$52.56/month`**), which is **2.13x higher** than the actual rightsized `e2-custom-2-4096` VM cost (`~$24.67/month` = **`$0.0343/hr` = `$0.822/day`**)! This overstates `daily_infra_vm_cost_usd` (`budget.py:140`) by **`+$0.93/day` (`+$27.89/mo`)**, distorting `PAAAccountant` net-after-infra profitability reports (`net_profit_after_ai_and_infra_usd`).
- **`Q6` More efficient alternative:** Update `prorated_vm_hourly_cost_usd` from `0.0730` to `0.0343` (`$24.67 / 720h`) and tighten `max_daily_ai_cost_usd` from `$2.50` to `$1.00` while NAV `< $250` if metered token billing is ever used instead of flat-rate subscription `agy` quota.
- **`Q7` Overly broad:** `prorated_vm_hourly_cost_usd: 0.0730` is stale pre-downsize metadata; `96/day` / `8/hr` / `$2.50/day` (`1.5x` on `P0`) and `$0.25/day` minimum expected EV gate (`budget.py:165-168`) are otherwise well-calibrated.
- **`Q8` Safe automation:** Automated in `BudgetManager`.
- **`Q9` Evidence:** [paa_autonomy_config.json](file:///C:/Users/Anton/source/repos/Dominus/config/paa_autonomy_config.json#L60-L75) & [budget.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/budget.py#L116-L169) vs. verified GCP billing rate `$24.67/mo`.
- **`Q10` Approval authority:** **Human Owner.**
- **Verdict:** **`OPTIMIZE` (Fix stale `$0.0730/hr` -> `$0.0343/hr` VM cost rate)**

---

#### `POL-11`: Accounting Integrity Safeguard (`> $1.50` Cash / `> 0.75` Share Discrepancy Freeze)
- **Locations:** [`PAAAccountant.verify_accounting_integrity`](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/accountant.py#L206-L331) (thresholds at `#L217-L218`), [`PAAAccountant.enforce_accounting_safeguard`](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/accountant.py#L333-L358), [paa_autonomy_config.json](file:///C:/Users/Anton/source/repos/Dominus/config/paa_autonomy_config.json#L84-L85), [PAA_RISK_POLICY.md](file:///C:/Users/Anton/source/repos/Dominus/config/policies/PAA_RISK_POLICY.md#L22-L23)
- **`Q1` Why created:** Detect phantom fills, orphaned ERC-1155 tokens, or unrecorded fees by reconciling authoritative on-chain `free_cash_pusd` vs. `live_bankroll` (adjusted for in-flight/matched Maker intents) within `accounting_discrepancy_threshold_usd = $1.50` and active ERC-1155 balances within `accounting_share_tolerance = 0.75` shares, writing `ACCOUNTING_SAFEGUARD_ACTIVE.json` on breach.
- **`Q2` Risk addressed:** Silent capital bleed, double-spend reservation bugs, or hallucinated ledger PnL.
- **`Q3` Still exists:** **Yes.** Essential on-chain truth anchor.
- **`Q4` Mandatory vs. internal:** Internal financial-control invariant.
- **`Q5` Blocks valid profit:** **No.** `ACCOUNTING_SAFEGUARD_ACTIVE.json` freezes *autonomous code deployments* (`DeploymentController`) and wakes `PAADirector` for reconciliation without killing in-flight riskless redemptions; auto-clears via `clear_accounting_safeguard_if_resolved` once cash diff `<= $1.50` and share diff `<= 0.75`.
- **`Q6` More efficient alternative:** Current implementation already handles residual floor valuation (`_UNWRESID_`) and resting EIP-712 Maker escrow timing cleanly (verified in [accountant.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/accountant.py#L239-L246) and [test_qa_boost_audit_remediation.py](file:///C:/Users/Anton/source/repos/Dominus/tests/test_qa_boost_audit_remediation.py#L381-L482)).
- **`Q7` Overly broad:** **No** (`$1.50` cash / `0.75` share tolerance avoids false alarms from transient RPC indexing lag or rounding dust while catching real fill/redemption mismatches).
- **`Q8` Safe automation:** Already 100% automated with auto-clear on verified reconciliation.
- **`Q9` Evidence:** [accountant.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/accountant.py#L217-L218), [paa_autonomy_config.json](file:///C:/Users/Anton/source/repos/Dominus/config/paa_autonomy_config.json#L84-L85), [PAA_RISK_POLICY.md](file:///C:/Users/Anton/source/repos/Dominus/config/policies/PAA_RISK_POLICY.md#L23); current production discrepancy `$0.0000`.
- **`Q10` Approval authority:** **Human Owner (Protected File — Retain).**
- **Verdict:** **`RETAIN`**

---

#### `POL-12`: PID-1 System Supervisor & User-Timer Self-Healing Watchdog (`PAA_MASTER_STOP` Aware)
- **Locations:** [`PAAMonitor`](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/monitor.py#L59-L545), [`PAAIndependentSupervisor`](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/monitor.py#L548-L660), [paa-system-supervisor.service](file:///C:/Users/Anton/source/repos/Dominus/systemd/paa-system-supervisor.service#L1-L20)
- **`Q1` Why created:** Ensure `loginctl enable-linger`, `user@1001.service`, and PAA monitoring timers survive Linux reboots or `dbus` drops, while strictly respecting `PAA_MASTER_STOP`.
- **`Q2` Risk addressed:** Silent daemon death after cloud host maintenance or OOM kills.
- **`Q3` Still exists:** **Yes.**
- **`Q4` Mandatory vs. internal:** Internal reliability architecture.
- **`Q5` Blocks valid profit:** **No** — protects uptime (`Nice=15`, `CPUWeight=50`, `MemoryMax=512M`).
- **`Q6` More efficient alternative:** Keep as-is; ensure emergency-stop scripts cleanly coordinate `PAA_MASTER_STOP` + trading order cancellation (`POL-26`).
- **`Q7` Overly broad:** **No** — `PAAIndependentSupervisor.run_supervision_check` ([monitor.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/monitor.py#L575-L580)) immediately returns `PAUSED_BY_MASTER_STOP` when `data/polymarket/paa/PAA_MASTER_STOP` exists, never fighting the owner's kill switch.
- **`Q8` Safe automation:** Fully automated.
- **`Q9` Evidence:** [monitor.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/monitor.py#L570-L610).
- **`Q10` Approval authority:** **Human Owner.**
- **Verdict:** **`RETAIN`**

---

### Group B — Polymarket Capital, Risk, Ruin-Floor, Tier & Velocity Policies

#### `POL-13`: Hard Ruin Floor (`hard_ruin_floor_usd: $62.00`) & Dual-Budget Riskless Halt Coupling
- **Locations:** [polymarket_strategy_and_risk.json](file:///C:/Users/Anton/source/repos/Dominus/config/polymarket_strategy_and_risk.json#L76), [paa_autonomy_config.json](file:///C:/Users/Anton/source/repos/Dominus/config/paa_autonomy_config.json#L124), [`PermissionGate.inspect_config_envelope`](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L213-L217), [`EmergencyRiskController.check_equity_drawdown`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L1162-L1188), [`EmergencyRiskController.is_riskless_box_halted`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L1260-L1268)
- **`Q1` Why created:** Preserve a "2-loss directional variance buffer" when directional BTC/ETH/SOL Taker sniping was active on a `~$95–$100` bankroll.
- **`Q2` Risk addressed:** Total bankroll ruin from consecutive directional losses.
- **`Q3` Still exists:** Directional ruin risk is **currently `$0.00`** (`riskless_only_mode: true` at [polymarket_strategy_and_risk.json](file:///C:/Users/Anton/source/repos/Dominus/config/polymarket_strategy_and_risk.json#L20)), YET a **CRITICAL CLIFF BUG** exists right now!
- **`Q4` Mandatory vs. internal:** 100% internal parameter choice.
- **`Q5` Blocks valid profit:** **CRITICAL P0 CLIFF HAZARD:**
  - Right now, liquid cash is **`$47.38`** and mark-to-bid NAV is **`$47.52`**, which is **ALREADY BELOW `$62.00`**!
  - The *only* reason the live harvester is not halted today is that `get_position_market_value` values the 4 disputed `KMIA` positions at par/cost (`$50.51`), inflating `tot_equity` to **`$97.89` (`>= $62.00`)** ([polymarket_live_harvester.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L2560-L2570)).
  - **The instant UMA resolves `KMIA` to `$0.00` (`-$50.51`), `tot_equity` will drop to `$47.38 < $62.00`!** `check_equity_drawdown` (`L1168-1174`) will set `self.halted = True` with `"Account equity $47.38 < $62.00..."`, and `is_riskless_box_halted()` ([polymarket_live_harvester.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L1266)) checks `if any(k in rs for k in (..., "equity")): return True` — **INSTANTLY FREEZING ALL 100% ZERO-LOSS RISKLESS ARBITRAGE (`D1`, `C1`, `BOND1`, `CLINCH_SPLIT`)** on the remaining `$47.38` cash!
  - Worse, `PermissionGate.inspect_config_envelope` ([permissions.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L213-L217)) locks `hard_ruin_floor_usd >= max(42.0, baseline[62.0]) = 62.0` unless the owner explicitly approves lowering it!
- **`Q6` More efficient alternative:**
  1. Separate `directional_min_equity_floor_usd: 150.0` (already enforced via `min_live_equity_for_unhedged_directional_usd: 150.0`) from `riskless_hard_ruin_floor_usd: 35.0` (or `$40.00`, below `$47.38` liquid cash, halting riskless boxes ONLY if reconciled cash+undisputed equity drops by `> $7.38` from current `$47.38` liquid floor, which would signal an execution/unwind bug!).
  2. Fix `PermissionGate.inspect_config_envelope` (`L214`) to allow owner-approved recalibration to the true `paa_autonomy_config.json` floor (`$35.00–$42.00`).
- **`Q7` Overly broad:** **Severely misaligned** with post-`KMIA` `$47.38` liquid reality and conflates directional variance ruin with zero-loss arbitrage capital.
- **`Q8` Safe automation:** Deterministic dual-floor (`directional_ruin_floor_usd` vs. `riskless_anomaly_floor_usd` anchored to reconciled liquid+undisputed NAV).
- **`Q9` Evidence:** Verified line-by-line at [polymarket_strategy_and_risk.json](file:///C:/Users/Anton/source/repos/Dominus/config/polymarket_strategy_and_risk.json#L76) and [polymarket_live_harvester.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L1168-L1268).
- **`Q10` Approval authority:** **Human Owner (`INCREASE_CAPITAL_EXPOSURE` scope or direct owner config edit).**
- **Verdict:** **`OPTIMIZE` (URGENT P0 FIX before `KMIA` UMA resolution lands!)**

---

#### `POL-14`: Directional Live Suspension (`riskless_only_mode: true` & `$150.00` Directional Floor)
- **Locations:** [polymarket_strategy_and_risk.json](file:///C:/Users/Anton/source/repos/Dominus/config/polymarket_strategy_and_risk.json#L20-L24), [`PermissionGate.inspect_config_envelope`](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L252-L265), `operator_approval_20261103_zero_loss_seed_focus.json`
- **`Q1` Why created:** Human operator mandate on Nov 3, 2026 (`ZERO_LOSS_SEED_REBUILD_FOCUS`) after directional variance drew down seed equity, dedicating 100% of sub-`$150` live capital to structural/clinch zero-loss arbitrage while directional strategies run in shadow.
- **`Q2` Risk addressed:** Gambler's ruin on a `$47.38` micro-bankroll where Polymarket's `$8–$12` practical lot sizes represent `17%–25%` of liquid capital per directional bet.
- **`Q3` Still exists:** **Yes — acutely!** At `$47.38` cash, 3 directional stop-outs (`-$4.50` each) would destroy `28.5%` of liquid capital.
- **`Q4` Mandatory vs. internal:** Internal owner-mandated risk policy.
- **`Q5` Blocks valid profit:** Blocks positive-EV *high-variance* directional trades below `$150` while preserving 100% of cash for zero-variance `D1`/`C1`/`BOND1` compounding; directional alpha continues accumulating OOS proof in shadow (`weekly_wfo_governance.py`).
- **`Q6` More efficient alternative:** Keep `riskless_only_mode: true` until **reconciled undisputed NAV** (NOT disputed book equity!) reaches `>= $150.00` AND shadow WFO passes `POL-16` (`N >= 50, PF >= 1.45, CI95_lo > 0, PBO <= 0.20`).
- **`Q7` Overly broad:** Appropriately scoped for `$47.38` seed survival.
- **`Q8` Safe automation:** Enforced in `polymarket_live_harvester.py` and locked against autonomous disablement in `permissions.py:253-260`.
- **`Q9` Evidence:** Fractional Kelly math (`compute_stop_risk_fractional_kelly_ticket` at [holistic_strategy_governance.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/holistic_strategy_governance.py#L850-L937)) returns `0.0` whenever `sized < $5.00` (`min_lot_usd * 0.625` at `L935`), confirming `$47.38` cannot safely Fractional-Kelly size directional bets anyway!
- **`Q10` Approval authority:** **Human Owner (`NEW_LIVE_TRADING_ACTIVATION`).**
- **Verdict:** **`RETAIN`**

---

#### `POL-15`: Live Strategy Firewall (`strict_pure_riskless_mode`, `paused_riskless_sleeves` & 50-Sleeve Expansion Freeze)
- **Locations:** [polymarket_strategy_and_risk.json](file:///C:/Users/Anton/source/repos/Dominus/config/polymarket_strategy_and_risk.json#L115-L135) & [#L217-L221](file:///C:/Users/Anton/source/repos/Dominus/config/polymarket_strategy_and_risk.json#L217-L221), [`check_strict_pure_riskless_candidate_gate`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/stage_c_zero_loss_velocity.py#L53-L118) & [#L209-L327](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/stage_c_zero_loss_velocity.py#L209-L327), [DOMINUS_MASTER_ROADMAP.md](file:///C:/Users/Anton/source/repos/Dominus/docs/DOMINUS_MASTER_ROADMAP.md#L431-L515)
- **`Q1` Why created:** Quarantine sleeves that caused historical legging losses (`NR0`, `LP_COMP1`, `DC1`, `CTF_OVERROUND`, `B4`, `S2` pre-expiry, `MKR_REWARD` midbook) and freeze ungraduated Class B sleeves in shadow.
- **`Q2` Risk addressed:** Multi-leg sequential FOK/FAK legging (`UNWRESID`), unclinched physical sensor misreads (`KMIA` ASOS `$` maintenance flag), and cross-question rule divergence.
- **`Q3` Still exists:** **Yes** — AND **two severe internal policy contradictions** currently exist in code:
  1. **Graduated Payoff-Dominant Sleeves Blocked by Allowlist Omission:** Roadmap §16 ([DOMINUS_MASTER_ROADMAP.md](file:///C:/Users/Anton/source/repos/Dominus/docs/DOMINUS_MASTER_ROADMAP.md#L435-L441)) and human approval `operator_approval_20261103_zero_loss_seed_focus.json` explicitly approved **`CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX`** (`12/8` settled, `100%` WR) and **`COND1_MACRO_PARTITION_BOX`** (`11/8` settled, `100%` WR), and `polymarket_live_harvester.py:5715-5718` has custom `cond1_short_ok` bridge code for `COND1`. **HOWEVER**, [`check_strict_pure_riskless_candidate_gate`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/stage_c_zero_loss_velocity.py#L296-L305) runs *earlier* at `polymarket_live_harvester.py:5467` and **HARD-REJECTS BOTH `CAL1` AND `COND1`** (`PURE_RISKLESS_SLEEVE_NOT_ALLOWLISTED` / `PURE_RISKLESS_BOX_TYPE_NOT_ALLOWLISTED` because neither `CAL1` nor `COND1` is in lines `296-302`, and `LADDER_MONO` / `MACRO_DOMINANCE` are not in line `304`!), making `polymarket_live_harvester.py:5715-5718` **100% unreachable dead code**!
  2. **Single-Leg Physical Sensor Snipes Still Allowlisted as "Pure Riskless":** Conversely, `POST_CLINCH_SINGLE_LEG_SLEEVES` ([stage_c_zero_loss_velocity.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/stage_c_zero_loss_velocity.py#L80-L93)) still allowlists `W1_SOLAR_PEAK_LOCK` and `W_PRUNE1_DEAD_NO_BOND` — single-leg weather sensor bets whose oracle is Weather Underground (`wunderground.com`), NOT raw METAR ASOS, which is the exact class of oracle-basis hazard that locked **`$50.51` (`51.6%` of account equity)** in `KMIA`!
- **`Q4` Mandatory vs. internal:** 100% internal strategy-governance design.
- **`Q5` Blocks valid profit:** **YES!** Hard-blocks 2-leg same-oracle calendar monotonicity (`CAL1`: `YES(by T1) <= YES(by T2)` on exact same event/oracle, `12/8` 100% WR) and 2-leg closed binary macro partitions (`COND1`, `11/8` 100% WR), while leaving single-leg Weather Underground vs. METAR basis exposure open!
- **`Q6` More efficient alternative:** Replace ad-hoc sleeve-name lists with a **3-Tier Payoff-Structure Classification**:
  - **Tier 1 (True Mathematical Payoff Dominance — Live Allowed at `$47.38`):** 2-leg `C1_BINARY_COMPLETE_SET` (`same condition_id`), `D1_SAME_ORACLE_DOMINANCE_BOX` (`same oracle, K_low <= K_high`), `CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX` (`same oracle, T_early <= T_late` with identical resolution clause), `NR_M1_DEAD_SEED_OVERROUND` (`1` leg), `NR2_PURE_CASH_CONVERT` (`2` legs), `CLINCH_DEAD_SPLIT_LOCK` (atomic on-chain `splitPosition` + dead-leg sell / instant merge-back).
  - **Tier 2 (UMA Post-Proposal Liveness Carry — Live Allowed with Strict Per-Event Cap `<= 15%` Liquid NAV):** `BOND1_UMA_RESOLUTION_CARRY`, `UMA_READY1_LIVENESS_PRIORITY`, `MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER` (only after official final settlement event + `0` dispute).
  - **Tier 3 (External Sensor / Proxy Oracle Single-Leg Snipes — Quarantine Until Multi-Source Consensus):** Demote `W1_SOLAR_PEAK_LOCK` & `W_PRUNE1_DEAD_NO_BOND` unless WU API + METAR dual-source consensus is verified or bankroll `>= $250` with `<= $5` micro-cap.
- **`Q7` Overly broad:** Simultaneously **over-broad** against `CAL1`/`COND1` (dead-code blocking owner-approved 2-leg boxes) and **under-protective** against WU/METAR proxy-oracle divergence! Also, running 50+ shadow sleeves inside `polymarket-alpha124-shadow.service` consumes up to `1.30–1.55 GB` RAM (`MemoryMax=1550M`) on a 4 GB VM.
- **`Q8` Safe automation:** Deterministic structural validator in `stage_c_zero_loss_velocity.py`.
- **`Q9` Evidence:** Compare [stage_c_zero_loss_velocity.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/stage_c_zero_loss_velocity.py#L296-L305) against [polymarket_live_harvester.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L5715-L5718) and `operator_approval_20261103_zero_loss_seed_focus.json`.
- **`Q10` Approval authority:** **Human Owner (`NEW_LIVE_TRADING_ACTIVATION`).**
- **Verdict:** **`REPLACE` (High-EV Structural Alignment + Dead-Code Unblock)**

---

#### `POL-16`: Three-System Strategy Graduation Gates (`_grad8` 8/8 Shadow vs. `alpha124` Staleness vs. Weekly WFO `N>=50`)
- **Locations:** [`_grad8`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L5614-L5645), [`evaluate_ledger_file`](file:///C:/Users/Anton/source/repos/Dominus/scripts/weekly_wfo_governance.py#L83-L119), [polymarket_strategy_and_risk.json](file:///C:/Users/Anton/source/repos/Dominus/config/polymarket_strategy_and_risk.json#L194-L205)
- **`Q1` Why created:** Require statistical proof before risking real money: `8/8` settled `100%` WR + `legging_adjusted_pnl_t1000_usd > 0` for riskless sleeves (`_grad8`), and `N >= 50, PF >= 1.45, CI95_lo > 0, PBO <= 0.20` for directional WFO (`weekly_wfo_governance.py`).
- **`Q2` Risk addressed:** Deploying broken parsers, inverted strikes, or negative-after-legging sleeves live.
- **`Q3` Still exists:** **Yes** for sleeves with semantic/parsing or 2-leg execution risk.
- **`Q4` Mandatory vs. internal:** Internal quality gate.
- **`Q5` Blocks valid profit:** **YES — two operational bottlenecks:**
  1. **Hard Dependency on `alpha124_shadow_state.json` `< 300s` mtime ([polymarket_live_harvester.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L5619-L5623)):** If `polymarket-alpha124-shadow.service` restarts, stalls for 5 minutes, or gets OOM-throttled (`MemoryMax=1550M`), `maybe_execute_graduated_d1_box` returns **`ALPHA124_STATE_STALE`**, **blocking EVEN ALREADY-GRADUATED `C1_BINARY_COMPLETE_SET` and `D1_SAME_ORACLE_DOMINANCE_BOX` live trades**! Once a sleeve is graduated, a temporary shadow-daemon hiccup should NEVER blind or halt live `C1`/`D1` execution!
  2. **Slow Rare-Event Accumulation for Pure Math Identity Sleeves:** Requiring `8` settled shadow expiries for rare macro/calendar complete sets delays obvious `1 YES + 1 NO < $1.00` opportunities for weeks, whereas structural invariants (`same condition_id`, `ask_yes + ask_no + fees < $1.00`) are mathematical identities, not statistical forecasts.
- **`Q6` More efficient alternative:**
  1. Cache graduated sleeve status in durable governance state (do **not** fail closed on `ALPHA124_STATE_STALE` `> 300s` for sleeves that already achieved graduation or are pure single-condition `C1_BINARY_COMPLETE_SET` / atomic `CLINCH_DEAD_SPLIT_LOCK`; fall back to last-known valid graduation map up to `24h` with a warning log).
  2. Keep `8/8` (`0` losses, `legging_adjusted_pnl_t1000_usd > 0`) for cross-market/2-leg sleeves (to prove parser rule-matching!) and `N >= 50, PF >= 1.45, PBO <= 0.20` strictly for directional alpha.
- **`Q7` Overly broad:** `300s` shadow-mtime kill switch on live graduated arbitrage creates an unnecessary single point of failure coupling shadow daemon health to live revenue.
- **`Q8` Safe automation:** Persist last-verified graduation snapshot and decouple live `C1`/`D1` execution from `300s` shadow file writes.
- **`Q9` Evidence:** [polymarket_live_harvester.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L5619-L5623) (`if (time.time() - st_info.st_mtime) > 300.0: return {"executed": False, "reason": "ALPHA124_STATE_STALE"}`).
- **`Q10` Approval authority:** **Human Owner.**
- **Verdict:** **`REPLACE` (Decouple live graduated execution from 300s shadow-daemon mtime; unify Tier-1/2/3 graduation criteria)**

---

#### `POL-17`: Bankroll / Equity Tier Gates (`$88`, `$98`, `$110`, `$125`, `$140`, `$150`, `$253`, `$450`, `$500`, `$525`, `$1,003`, `$5,000`) & Book-vs-Liquid NAV Distortion
- **Locations:** [`get_equity_tier_limits`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L1039-L1130), [`get_unleashed_v5_tier_profile`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/holistic_strategy_governance.py#L690-L794), [`compute_dynamic_riskless_tier_caps`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/riskless_protocol_v2_expansion.py#L1781-L1815), [`BankrollMilestoneVerifier`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_unblock_and_certification.py#L1227-L1377)
- **`Q1` Why created:** Scale concurrency slots, single-clip caps, lockup horizons, and multi-venue staging smoothly as bankroll compounds, without risking oversized clips at micro-equity.
- **`Q2` Risk addressed:** Over-allocation and liquidity starvation on small bankrolls.
- **`Q3` Still exists:** **Yes — AND a major accounting-basis distortion exists right now!**
- **`Q4` Mandatory vs. internal:** Internal risk/capital-allocation design.
- **`Q5` Blocks valid profit / distorts risk:**
  - **Four Overlapping Tier Tables:** The codebase simultaneously maintains (a) `get_equity_tier_limits` (`$88`, `$91-$108`, `$140`, `$300`), (b) `get_unleashed_v5_tier_profile` (`$95` + `$3` hysteresis = `$98`, `$150`, `$300`, `$600`, `$1,000`), (c) `compute_dynamic_riskless_tier_caps` (`$125` reward, `$140` pre-split, `$150` event slots), and (d) `BANKROLL_MILESTONE_SPECS` (`$88`, `$98`, `$110`, `$125`, `$140`, `$253`, `$450`, `$525`) plus `$500` bundle gate and `$5,000` PAA proposal gate!
  - **Disputed Book-Equity Illusion (`$97.89` vs. `$47.38` Liquid Cash):** Because `tot_equity` includes `$50.51` of illiquid, disputed `KMIA` positions (`~2c` bid = `$0.14` market value), `get_equity_tier_limits($97.89)` places the bot in **`RECOVERY` (`$97.89 >= $88.00`)** with `max_exposure = $53.84` (`> 100%` of `$47.38` liquid cash!) and `BankrollMilestoneVerifier` reports `M2.1 ($88)` unlocked, even though **usable deployable capital is `$47.38` (`SEED_SURVIVAL`)**!
- **`Q6` More efficient alternative:** Compute all tier, clip-sizing, concentration, and velocity hurdles off **`deployable_reconciled_nav_usd = free_cash_usd + undisputed_redeemable_or_mark_to_bid_value_usd`** (`$47.52` today), NOT disputed cost-basis receivables (`$97.89`), and consolidate the 4 tier tables into one canonical `holistic_strategy_governance.py` schedule.
- **`Q7` Overly broad:** Fragmented across 4 modules and distorted by disputed UMA cost-basis valuation.
- **`Q8` Safe automation:** 100% automatable by discounting `disputed == True` positions to mark-to-bid (`$0.14`) in `deployable_nav_usd`.
- **`Q9` Evidence:** [polymarket_live_harvester.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L2551-L2563) & [riskless_protocol_v2_expansion.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/riskless_protocol_v2_expansion.py#L2060-L2068).
- **`Q10` Approval authority:** **Human Owner.**
- **Verdict:** **`OPTIMIZE` (Anchor all sizing/tier gates to undisputed mark-to-bid NAV `$47.52` and unify tier table)**

---

#### `POL-18`: Correlated-Event / Weather-Station Concentration Cap (`check_per_event_concentration_cap`)
- **Locations:** [`extract_canonical_event_keys`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/riskless_protocol_v2_expansion.py#L1971-L1986), [`check_per_event_concentration_cap`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/riskless_protocol_v2_expansion.py#L2004-L2134), [`compute_dynamic_riskless_tier_caps`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/riskless_protocol_v2_expansion.py#L1798-L1815)
- **`Q1` Why created:** Created after 4 separate positions on the same `KMIA` Nov 7 weather event accumulated `$50.51` (`51.6%` of total equity), locking half the bankroll in a single correlated UMA station dispute.
- **`Q2` Risk addressed:** Single-oracle / single-station / single-event correlated dispute or sensor failure locking or wiping out a large fraction of NAV.
- **`Q3` Still exists:** **Yes — primary tail risk for any single-leg or UMA-settled sleeve!**
- **`Q4` Mandatory vs. internal:** Internal risk limit (`JUSTIFIED_RISK_LIMIT` in principle, `TECHNICAL_FIXABLE` in current parameterization).
- **`Q5` Blocks valid profit:** Does **not** block diversified opportunities, **BUT** our code audit uncovered **3 critical gaps** where the actual implementation falls short of the stated *"15% of reconciled NAV across all sleeves"* invariant:
  1. **Cap Formula Is `max($20.00, 28% * Book_Equity)` Instead of `15% * Reconciled_NAV` ([riskless_protocol_v2_expansion.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/riskless_protocol_v2_expansion.py#L1799-L1807)):** In `polymarket_strategy_and_risk.json`, `max_event_notional_usd` is **unset (`0.0`)**. Consequently, `compute_dynamic_riskless_tier_caps($97.89)` computes `max(20.0, 97.89 * 0.28)` = **`$27.41`**, which is **`57.7%` of actual `$47.52` reconciled NAV** (nearly **4x** the intended `15%` cap = `$7.13`, or `$10.00` practical 1-clip cap)!
  2. **Explicit Bypass for `FAST_GUN_S2_SLEEVES` & Short-TTE `D1` ([riskless_protocol_v2_expansion.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/riskless_protocol_v2_expansion.py#L2025-L2026)):** `if sl_src in FAST_GUN_S2_SLEEVES or (btype == "DOMINANCE" and rem_s <= 960.0 and sl_src == "D1_SAME_ORACLE_DOMINANCE_BOX"): return True, "", 9999.0, evt_k` — those sleeves neither get capped NOR have their open notional checked when they enter!
  3. **Excludes `AWAITING_ONCHAIN_SETTLEMENT` Positions ([riskless_protocol_v2_expansion.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/riskless_protocol_v2_expansion.py#L2065) & [#L2084](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/riskless_protocol_v2_expansion.py#L2084)):** Positions awaiting on-chain UMA settlement (which can still be disputed during the 2h liveness window!) are skipped when summing `used_evt_usd`!
- **`Q6` More efficient alternative:**
  1. Base `tot_eq` on **reconciled mark-to-bid NAV** (`$47.52`), include `AWAITING_ONCHAIN_SETTLEMENT` (until `redeemed` on-chain) in `used_evt_usd`, and enforce `15%` of reconciled NAV (`max($6.00, round(0.15 * reconciled_nav, 2))` = **`$7.13`** at `$47.52` NAV, or `1` minimum `$5–$7` Polymarket lot) on all single-leg / UMA-disputable events while allowing `25%` (`~$12.00`) ONLY for 2-leg Chainlink-automated/atomic-mergeable `C1`/`D1` boxes with zero UMA dispute surface.
  2. Remove the `FAST_GUN_S2_SLEEVES` bypass (`L2025`).
- **`Q7` Overly broad:** Actually **under-strict (`$27.41` = `57.7%` of liquid NAV!)** due to the `$20.00` floor + `28%` book-equity formula!
- **`Q8` Safe automation:** Deterministic 10-line fix in `compute_dynamic_riskless_tier_caps` and `check_per_event_concentration_cap`.
- **`Q9` Evidence:** Exact lines [riskless_protocol_v2_expansion.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/riskless_protocol_v2_expansion.py#L1799-L1807), [#L2025-L2026](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/riskless_protocol_v2_expansion.py#L2025-L2026), [#L2062-L2088](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/riskless_protocol_v2_expansion.py#L2062-L2088).
- **`Q10` Approval authority:** **Human Owner.**
- **Verdict:** **`OPTIMIZE` (Critical Risk-Integrity Fix: enforce true `15%` reconciled-NAV cap without `28%/$20` or `AWAITING_ONCHAIN_SETTLEMENT` bypasses)**

---

#### `POL-19`: Sequential `>= 3`-Leg `MULTI_LEG_BUNDLE` & `NR0` Quarantine Below `$500` NAV
- **Locations:** [polymarket_strategy_and_risk.json](file:///C:/Users/Anton/source/repos/Dominus/config/polymarket_strategy_and_risk.json#L115-L137), [`is_nr0_closed_partition_graduated_unlock`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/stage_c_zero_loss_velocity.py#L120-L151), [`check_strict_pure_riskless_candidate_gate`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/stage_c_zero_loss_velocity.py#L250-L272), [`finish_protocol_v2_special_box_sync`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/riskless_protocol_v2_expansion.py#L6376-L6450)
- **`Q1` Why created:** Sequential CLOB FOK/FAK execution across 3–12 legs is **not atomic**: if legs 1–2 fill and leg 3 misses due to a 50ms quote race, emergency unwind crosses `N-1` bid-ask spreads (`UNWRESID`), turning a `150 bps` arb into a `-$2` to `-$8` realized loss.
- **`Q2` Risk addressed:** Non-atomic multi-leg partial-basket execution (`UNWRESID` legging wipeouts).
- **`Q3` Still exists:** **Yes** — Polymarket CLOB has no atomic multi-market FOK basket order endpoint.
- **`Q4` Mandatory vs. internal:** Internal execution-safety gate (`JUSTIFIED_RISK_LIMIT`, addressing external CLOB non-atomicity).
- **`Q5` Blocks valid profit:** Blocks sequential `>= 3`-leg Taker bundles (which have **negative net EV after legging** at `$47.38` cash), while **preserving** `1`-leg NegRisk `convertPositions` (`NR_M1_DEAD_SEED_OVERROUND`), `2`-leg `NR2_PURE_CASH_CONVERT`, and atomic on-chain `CLINCH_DEAD_SPLIT_LOCK`.
- **`Q6` More efficient alternative:** **Config threshold discrepancy found!** While the Roadmap/QA policy specifies `< $500` NAV quarantine for sequential `>= 3`-leg bundles, [`is_nr0_closed_partition_graduated_unlock`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/stage_c_zero_loss_velocity.py#L137) defaults `nr0_dynamic_unlock_equity_usd` to **`$150.00`** (`max(100.0, ... 150.0)`)! Currently `allow_nr0_multileg_dynamic_unpause` is `False` (`polymarket_strategy_and_risk.json:137`), so `MULTI_LEG_BUNDLE` IS blocked today (`PURE_RISKLESS_SPECIAL_BOX_BLOCKED:MULTI_LEG_BUNDLE` at `L259-260`), **but** if `allow_nr0_multileg_dynamic_unpause` were ever flipped `True`, it would unlock at **`$150` instead of `$500`**, AND `polymarket_live_harvester.py:5456` passes `_nav_est = _last_known_collateral` (`$47.38`) while `finish_protocol_v2_special_box_sync` checks no `$500` floor directly!
- **`Q7` Overly broad:** Not overly broad—actually needs `nr0_dynamic_unlock_equity_usd` raised from `$150.0` to **`$500.0`** (measured on reconciled undisputed NAV) so code matches the `$500` policy invariant.
- **`Q8` Safe automation:** Set `nr0_dynamic_unlock_equity_usd: 500.0` in both code default (`stage_c_zero_loss_velocity.py:137`) and `polymarket_strategy_and_risk.json`.
- **`Q9` Evidence:** [stage_c_zero_loss_velocity.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/stage_c_zero_loss_velocity.py#L132-L151) & [#L250-L261](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/stage_c_zero_loss_velocity.py#L250-L261).
- **`Q10` Approval authority:** **Human Owner.**
- **Verdict:** **`REPLACE` (Keep `MULTI_LEG_BUNDLE` blocked; harden `nr0_dynamic_unlock_equity_usd` from `$150` -> `$500` reconciled NAV)**

---

#### `POL-20`: Bankroll-Tiered Capital-Velocity Hurdle (`seed_max_lockup_hours: 8.0h`, `seed_min_bps_per_hour: 15.0`)
- **Locations:** [polymarket_strategy_and_risk.json](file:///C:/Users/Anton/source/repos/Dominus/config/polymarket_strategy_and_risk.json#L162-L166), [`passes_capital_velocity_hurdle`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/holistic_strategy_governance.py#L796-L848)
- **`Q1` Why created:** Prevent locking scarce seed cash for 48–168 hours for a tiny `40 bps` return (`< 1 bps/hr`), which starves high-turnover intraday `D1`/`C1`/`BOND1` opportunities and cannot cover `$0.82/day` VM overhead.
- **`Q2` Risk addressed:** Opportunity-cost capital starvation (dead-money lockup).
- **`Q3` Still exists:** **Yes — critical at `$47.38` liquid cash!** To cover `$0.82/day` infra on `$47.38` (`173 bps/day` = `7.2 bps/hr` across the *entire* cash balance), deployed clips must earn `>= 12–15 bps/hr`.
- **`Q4` Mandatory vs. internal:** Internal capital-efficiency optimization.
- **`Q5` Blocks valid profit:** Two subtle defects in [`passes_capital_velocity_hurdle`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/holistic_strategy_governance.py#L812-L847):
  1. **Unconditional Exemption on Line 812 (`DOMINANCE`, `COMPLETE_SET`, `NEGRISK_CONVERT`):** Line `812` immediately returns `True, "OK"` for `COMPLETE_SET` and `NEGRISK_CONVERT` **regardless of `rem_tte_sec` or whether gasless/on-chain merge is actually available!** Look at `polymarket_live_harvester.py:5677`: if `_merge_wallet_ok` is `False` (e.g., Safe `signature_type == 3` without `POLY_BUILDER_API_KEY`), `_zf_c1_merge_ok` is still `True` for `TTE <= 86,400s` (`24h`), meaning a `23.9h` `45 bps` (`1.9 bps/hr`!) unmergeable `COMPLETE_SET` bypasses `passes_capital_velocity_hurdle` completely!
  2. **Uses `collat_usd = collat_f + cur_exp` (`$97.89` book equity) at Call Sites:** At `$97.89 >= $98.00` (`RECOVERY`), `max_lockup_hours` jumps from `8.0h` to `36.0h` and `min_bps_per_hour` drops from `15.0` to `8.0` ([polymarket_strategy_and_risk.json](file:///C:/Users/Anton/source/repos/Dominus/config/polymarket_strategy_and_risk.json#L163-L166)), even though real free cash is only `$47.38`!
- **`Q6` More efficient alternative:** Exempt `COMPLETE_SET` / `NEGRISK_CONVERT` from `eff_hrs` lockup ONLY when **instant on-chain/gasless merge (`eff_hrs = 0.10h`) is verified active**; otherwise evaluate against actual `rem_tte_sec` and **undisputed liquid NAV (`$47.52`)**! Also allow idle-cash dynamic relaxation (`min_bps_hr = 10.0` up to `12h` when `> 75%` of liquid cash has sat idle for `> 4h` and `$15+` instant-arb reserve remains free).
- **`Q7` Overly broad / narrow:** Line `812` is **too permissive** for unmergeable 24h `C1` holds, while `8.0h` fixed cap can reject a `10h` overnight `250 bps` (`25 bps/hr`) box only if misclassified as `_seed_sports_box`.
- **`Q8` Safe automation:** Deterministic in `passes_capital_velocity_hurdle`.
- **`Q9` Evidence:** [holistic_strategy_governance.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/holistic_strategy_governance.py#L812-L847) & [polymarket_live_harvester.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L5669-L5678).
- **`Q10` Approval authority:** **Human Owner.**
- **Verdict:** **`OPTIMIZE`**

---

#### `POL-21`: Legacy Config Flags (`enable_ungraduated_v3_math_live: true` & Stale `config/polymarket_risk_config.json`)
- **Locations:** [polymarket_strategy_and_risk.json](file:///C:/Users/Anton/source/repos/Dominus/config/polymarket_strategy_and_risk.json#L188), [permissions.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L290-L292), [polymarket_risk_config.json](file:///C:/Users/Anton/source/repos/Dominus/config/polymarket_risk_config.json#L1-L49)
- **`Q1` Why created:** `polymarket_risk_config.json` was the v3.x risk config (`min_equity_floor: 48.0`, `max_exposure: 24.0`, `seed_survival_equity_threshold: 88.0`) before v5.4 `polymarket_strategy_and_risk.json` (`hard_ruin_floor_usd: 62.0`, `seed_max_usd: 95.0`); `enable_ungraduated_v3_math_live: true` was enabled before `strict_pure_riskless_mode: true` superseded it.
- **`Q2` Risk addressed:** Legacy bootstrap sizing and v3 bridge testing.
- **`Q3` Still exists:** **No** — superseded by `holistic_strategy_governance.py` and `stage_c_zero_loss_velocity.py`, **yet both legacy artifacts still get read as fallbacks** in `polymarket_live_harvester.py` (`RISK_CONFIG` at `L583, 1070-1080, 5733`), creating dangerous silent fallback divergences whenever `_is_v5_unleashed_active()` is `False` in tests or CLI invocations!
- **`Q4` Mandatory vs. internal:** Internal legacy debt (`LEGACY_UNNECESSARY`).
- **`Q5` Blocks valid profit:** Creates confusing audit/test discrepancies (`$48` vs `$62` floor, `$88` vs `$95` tier, `enable_ungraduated_v3_math_live: true` bypassed only because `strict_pure_riskless_mode` overrides it upstream).
- **`Q6` More efficient alternative:** Set `enable_ungraduated_v3_math_live: false` in `polymarket_strategy_and_risk.json` (matching Zero-Trust policy) and make `polymarket_risk_config.json` a thin deprecated shim or sync its values from `polymarket_strategy_and_risk.json`.
- **`Q7` Overly broad:** Obsolete dual-source-of-truth config drift.
- **`Q8` Safe automation:** Automated schema check in `holistic_strategy_governance.py`.
- **`Q9` Evidence:** [polymarket_strategy_and_risk.json](file:///C:/Users/Anton/source/repos/Dominus/config/polymarket_strategy_and_risk.json#L188) vs. [polymarket_risk_config.json](file:///C:/Users/Anton/source/repos/Dominus/config/polymarket_risk_config.json#L1-L49).
- **`Q10` Approval authority:** **Human Owner.**
- **Verdict:** **`REMOVE` (Clean up legacy flag & dual-config drift)**

---

### Group C — Stage G Cross-Venue, Compliance, Resource & Emergency Policies

#### `POL-22`: Stage G Zero-Signing-Key Shadow `.env` Fence, P0 Gate 0 & Double-Zero 5-Gate Settlement Verifier
- **Locations:** [`validate_shadow_env_dict`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_shadow_deployment_gates.py#L1632-L1730), [`evaluate_venue_authorization`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_shadow_deployment_gates.py#L618-L1475), `CrossVenueRuleVerifier` (`Gates 1–5`), [`VenueCertificationTracker`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_unblock_and_certification.py#L795-L1220)
- **`Q1` Why created:** Enforce strict separation between **permitted read-only public/content market-data shadow research** and **restricted live trading/account execution** under `CA-ON` / venue ToS, forbid wallet private keys in `/etc/polymarket-shadow.env`, and prevent cross-venue "Double-Zero" wipeouts (buying YES on Venue A and NO on Venue B when differing oracle/overtime/tie/strike rules settle BOTH legs to `$0.00`!).
- **`Q2` Risk addressed:** Jurisdictional/contractual violations, shadow credential exposure, and catastrophic `-100%` cross-venue settlement mismatches.
- **`Q3` Still exists:** **Yes — 100% real external legal & settlement risk!**
- **`Q4` Mandatory vs. internal:** External legal/contractual (`P0 Gate 0` trading blocks in `CA-ON`) + Essential Settlement Safety (`Double-Zero Gates 1–5` and `0`-private-key shadow fence).
- **`Q5` Blocks valid profit:**
  - Read-only public data & shadow research were **already cleanly unblocked** (`5` legacy internal false blocks eliminated in [`RestrictionRegistry`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_unblock_and_certification.py#L1470-L1545)).
  - At **`$47.38` liquid cash**, splitting capital across 2 venues (`~$23/venue`) is **economically suboptimal anyway** compared to compounding `$47.38` inside single-venue Polymarket `0%`-fee boxes without cross-chain bridge drag (`bridge_drag_bps`). Requiring `168h` shadow certification + `P0 Gate 0` entity eligibility before `$253+` cross-venue live capital protects `100%` of principal at `$0.00` lost realistic EV today!
- **`Q6` More efficient alternative:** Keep `0`-signing-key shadow `.env`, `Double-Zero Gates 1–5`, and `P0 Gate 0` intact; fix only the minor cgroup metadata drift noted in `POL-23`/`POL-24`.
- **`Q7` Overly broad:** **No** — after the 7-scope capability separation (`PUBLIC_REST`, `PUBLIC_WEBSOCKET`, `AUTHENTICATED_READONLY`, `ACCOUNT_PRIVATE`, `TRADING`, `INSTITUTIONAL_DATA_LICENSE`, `SERVER_HOSTING`), zero read-only feeds are falsely blocked by trading restrictions.
- **`Q8` Safe automation:** Already automated with fail-closed `ExitStatus=78` (`RestartPreventExitStatus=78`).
- **`Q9` Evidence:** [cross_venue_shadow_deployment_gates.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_shadow_deployment_gates.py#L618-L1778) & [KYB_AND_API_ONBOARDING_DOSSIERS.md](file:///C:/Users/Anton/source/repos/Dominus/docs/KYB_AND_API_ONBOARDING_DOSSIERS.md#L9-L17).
- **`Q10` Approval authority:** **Human Owner + External Venue/Regulatory Compliance (`P0 Gate 0` non-overridable without legal eligibility).**
- **Verdict:** **`RETAIN`**

---

#### `POL-23`: Systemd 2-vCPU / 4 GB RAM Resource Fences & Harvester Scheduling Priority
- **Locations:** [polymarket-live-harvester.service](file:///C:/Users/Anton/source/repos/Dominus/systemd/polymarket-live-harvester.service#L22-L28), [polymarket-alpha124-shadow.service](file:///C:/Users/Anton/source/repos/Dominus/systemd/polymarket-alpha124-shadow.service#L15-L20), [polymarket-cross-venue-shadow.service](file:///C:/Users/Anton/source/repos/Dominus/systemd/polymarket-cross-venue-shadow.service#L14-L28), [`validate_systemd_unit_text`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_shadow_deployment_gates.py#L1792-L1823)
- **`Q1` Why created:** Protect `polymarket-live-harvester.service` (`CPUWeight=1000, OOMScoreAdjust=-900`) from CPU steal and Linux OOM kills on the rightsized `4 GB` RAM / `2 vCPU` Finland VM (`~$24.67/mo`) by fencing `alpha124-shadow` (`Nice=10, CPUWeight=200, MemoryMax=1550M`) and `cross-venue-shadow` (`Nice=19, CPUQuota=35%, MemoryMax=512M, ProtectSystem=strict`).
- **`Q2` Risk addressed:** Shadow Orderbook/SQLite scans starving live CLOB WebSocket heartbeats or triggering kernel OOM-killer against the live trading daemon.
- **`Q3` Still exists:** **Yes** — physical `4,096 MB` RAM / `2 vCPU` ceiling on `quant-pipeline-finland`.
- **`Q4` Mandatory vs. internal:** Internal OS scheduling fence matching physical `RESOURCE_LIMITATION`.
- **`Q5` Blocks valid profit:** Does not block live trades; **however**, `polymarket-live-harvester.service` itself has **NO `MemoryHigh` leak warning** (if state grows unbounded, kernel kills `alpha124-shadow` first, which then triggers `ALPHA124_STATE_STALE` after `300s` via `POL-16`, halting live `D1`/`C1` boxes!), and `alpha124-shadow` (`1550M`) + `cross-venue-shadow` (`512M`) + `paa-supervisor` (`512M`) + 7 `polymarket-recorder-*` units + OS/live-harvester can exceed `4,096 MB` peak RSS if all burst concurrently!
- **`Q6` More efficient alternative:** Keep `Nice=19` / `CPUQuota=35%` / `MemoryMax=512M` on `cross-venue-shadow`, decouple live graduated boxes from `300s` `alpha124` mtime (`POL-16`), and cap `alpha124-shadow` in-memory closed-history retention so its steady RSS stays `< 700 MB`.
- **`Q7` Overly broad:** Minor check naming drift in `validate_systemd_unit_text` (`enforces_memory_max_180m` regex actually accepts `180|240|256|320|384|450|512M` at [cross_venue_shadow_deployment_gates.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_shadow_deployment_gates.py#L1799-L1804)).
- **`Q8` Safe automation:** Enforced natively by Linux cgroups v2 (`systemd`).
- **`Q9` Evidence:** [polymarket-live-harvester.service](file:///C:/Users/Anton/source/repos/Dominus/systemd/polymarket-live-harvester.service#L22-L28), [polymarket-alpha124-shadow.service](file:///C:/Users/Anton/source/repos/Dominus/systemd/polymarket-alpha124-shadow.service#L15-L20), [polymarket-cross-venue-shadow.service](file:///C:/Users/Anton/source/repos/Dominus/systemd/polymarket-cross-venue-shadow.service#L14-L28).
- **`Q10` Approval authority:** **Human Owner.**
- **Verdict:** **`OPTIMIZE`**

---

#### `POL-24`: Stale Restriction-Registry Text (`INT_ADMIN::RSS_180MB_CGROUP_MISMATCH` Claiming `320M` vs Actual `512M`)
- **Locations:** [`VenueCertificationTracker.build_certification_report`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_unblock_and_certification.py#L1113-L1130), [`RestrictionRegistry.build_entries`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_unblock_and_certification.py#L1517-L1530)
- **`Q1` Why created:** Track alignment between `VenueCertificationTracker` RSS gates and `polymarket-cross-venue-shadow.service` `MemoryMax`.
- **`Q2` Risk addressed:** False certification failure when Python RSS exceeded an old `180 MB` check inside a larger cgroup.
- **`Q3` Still exists:** Partially — `core_gates_passed` (`L1129`) now checks `rss_within_512mb_cgroup` (`<= 512.0`), matching `MemoryMax=512M`, **but** `RestrictionEntry` `INT_ADMIN::RSS_180MB_CGROUP_MISMATCH` (`L1523, L1529`) still emits stale prose claiming `MemoryHigh=280M, MemoryMax=320M` and `320.0 MB`!
- **`Q4` Mandatory vs. internal:** Internal telemetry hygiene (`LEGACY_UNNECESSARY` stale assertion).
- **`Q5` Blocks valid profit:** `$0.00` direct trade block, but misleads operator/auditor diagnostics when RSS sits between `321 MB` and `450 MB`.
- **`Q6` More efficient alternative:** Update `RestrictionRegistry` entry `L1523-1529` to reflect `MemoryHigh=450M, MemoryMax=512M` and remove obsolete `rss_within_180mb_cgroup` / `rss_within_320mb_cgroup` confusion from gate summaries.
- **`Q7` Overly broad:** Stale documentation string in live JSON registry.
- **`Q8` Safe automation:** Trivial constant sync.
- **`Q9` Evidence:** [cross_venue_unblock_and_certification.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_unblock_and_certification.py#L1120-L1130) & [#L1517-L1530](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_unblock_and_certification.py#L1517-L1530) vs. [polymarket-cross-venue-shadow.service](file:///C:/Users/Anton/source/repos/Dominus/systemd/polymarket-cross-venue-shadow.service#L15-L16).
- **`Q10` Approval authority:** **Human Owner.**
- **Verdict:** **`REMOVE` (Clean up obsolete 180M/320M gate remnants)**

---

#### `POL-25`: Localhost-Only & Custom-Header CSRF Gate on Dashboard Shutdown (`POST /api/shutdown`)
- **Locations:** [`_is_allowed_local` & `do_POST`](file:///C:/Users/Anton/source/repos/Dominus/scripts/dominus_command_center.py#L4411-L4440)
- **`Q1` Why created:** Allow a new `dominus_command_center.py` launch on `127.0.0.1` to gracefully reclaim its local dashboard port without allowing browser-tab DNS-rebinding or cross-site `POST` requests to kill the operator's local UI.
- **`Q2` Risk addressed:** Localhost DNS rebinding / CSRF against local HTTP server.
- **`Q3` Still exists:** **Yes** whenever an operator runs a local HTTP dashboard alongside a web browser.
- **`Q4` Mandatory vs. internal:** Internal security best practice (`ESSENTIAL_SAFETY`).
- **`Q5` Blocks valid profit:** **No (`$0.00` impact; affects local UI server only, never live trading).**
- **`Q6` More efficient alternative:** Already zero-cost (`Host` check + `client_address in ("127.0.0.1", "::1")` + `X-Dominus-Shutdown: 1` custom header triggering CORS preflight block in browsers).
- **`Q7` Overly broad:** **No.**
- **`Q8` Safe automation:** Already automated in `_reclaim_existing_dashboard_port` ([dominus_command_center.py](file:///C:/Users/Anton/source/repos/Dominus/scripts/dominus_command_center.py#L4306-L4323)).
- **`Q9` Evidence:** [dominus_command_center.py](file:///C:/Users/Anton/source/repos/Dominus/scripts/dominus_command_center.py#L4411-L4440).
- **`Q10` Approval authority:** **Human Owner.**
- **Verdict:** **`RETAIN`**

---

#### `POL-26`: Emergency Kill-Switch & Master-Stop Workflows (`KILL_SWITCH`, `PAA_MASTER_STOP`, `emergency-stop`, `resume`)
- **Locations:** [`cmd_emergency_stop`](file:///C:/Users/Anton/source/repos/Dominus/scripts/paa_cli.py#L390-L416), [`cmd_resume`](file:///C:/Users/Anton/source/repos/Dominus/scripts/paa_cli.py#L435-L449), [paa_emergency_stop.sh](file:///C:/Users/Anton/source/repos/Dominus/scripts/paa_emergency_stop.sh#L1-L27), [`EmergencyRiskController._kill_file_active`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L1156-L1161), [`SIGTERM` `cancel_all_orders`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L10799-L10825)
- **`Q1` Why created:** Provide the human owner immediate deterministic commands to freeze autonomous PAA agents (`PAA_MASTER_STOP`) and/or halt live trading (`KILL_SWITCH` / `--include-trading`).
- **`Q2` Risk addressed:** Runaway orders, exchange API malfunction, or autonomous loop misbehavior.
- **`Q3` Still exists:** **Yes — non-negotiable owner control requirement.**
- **`Q4` Mandatory vs. internal:** Internal owner-control safety mechanism.
- **`Q5` Blocks valid profit:** Does not block normal profit, **BUT 4 dangerous operational gaps** exist in the emergency-stop/resume implementation:
  1. **No Direct CLOB `cancel_all_orders()` Fallback When `--include-trading` Runs:** `paa_cli.py emergency-stop --include-trading` ([paa_cli.py](file:///C:/Users/Anton/source/repos/Dominus/scripts/paa_cli.py#L408-L411)) only calls `systemctl --user stop polymarket-live-harvester.service`. While the harvester's `SIGTERM` handler calls `self.executor.cancel_all_orders()` (`polymarket_live_harvester.py:10822`), if the harvester was already crashed, hung (>20s `TimeoutStopSec` -> `SIGKILL`), or stopped earlier, **resting GTC Maker orders (`BOND1` / `MKR_LOCK1` / `$0.98` TP) remain LIVE on the Polymarket CLOB**! Furthermore, `cmd_emergency_stop --include-trading` does **not** touch `data/polymarket/KILL_SWITCH` (`EmergencyRiskController.kill_file`), so if `polymarket-live-harvester.service` is manually started later, it doesn't know a trading halt was engaged!
  2. **Incomplete Service Coverage on `--include-trading`:** `paa_cli.py:409` stops only `polymarket-live-harvester.service` and `polymarket-alpha124-shadow.service`, omitting `polymarket-cross-venue-shadow.service`, `polymarket-cross-venue-shadow-watchdog.timer`, and `polymarket-telemetry-compactor.timer`.
  3. **Divergence Between `paa_emergency_stop.sh` and `paa_cli.py`:** `paa_emergency_stop.sh` ([paa_emergency_stop.sh](file:///C:/Users/Anton/source/repos/Dominus/scripts/paa_emergency_stop.sh#L23)) stops PID-1 `paa-system-supervisor.timer` via `sudo`, whereas `paa_cli.py` does not (relying on `PAA_MASTER_STOP` file check), and `paa_emergency_stop.sh` has **no `--include-trading` option** at all.
  4. **Asymmetric `paa_cli.py resume` ([paa_cli.py](file:///C:/Users/Anton/source/repos/Dominus/scripts/paa_cli.py#L435-L449)):** `resume` restarts the 9 PAA timers and deletes `PAA_MASTER_STOP`, **silently leaving `polymarket-live-harvester.service` and `polymarket-alpha124-shadow.service` stopped** if `emergency-stop --include-trading` was used, without printing a warning or offering `--include-trading`!
- **`Q6` More efficient alternative:** Upgrade `cmd_emergency_stop --include-trading` to (a) atomically write `data/polymarket/KILL_SWITCH`, (b) stop all shadow/live units cleanly, AND (c) run an independent out-of-band `PolymarketExecutor.cancel_all_orders()` verification pass to guarantee `0` resting CLOB bids remain open even if the harvester hung; upgrade `cmd_resume` to explicitly report live-harvester status and support `--include-trading` (removing `KILL_SWITCH` after reconciliation check).
- **`Q7` Overly broad:** Under-complete on CLOB order cancellation and asymmetric on `resume`.
- **`Q8` Safe automation:** 100% deterministic owner CLI improvement.
- **`Q9` Evidence:** [paa_cli.py](file:///C:/Users/Anton/source/repos/Dominus/scripts/paa_cli.py#L390-L449), [paa_emergency_stop.sh](file:///C:/Users/Anton/source/repos/Dominus/scripts/paa_emergency_stop.sh#L1-L27), [polymarket_live_harvester.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L1153-L1160) & [#L10820-L10825](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L10820-L10825).
- **`Q10` Approval authority:** **Human Owner.**
- **Verdict:** **`OPTIMIZE` (P0 Owner Emergency-Control Hardening)**

---

## 3. Master Summary Matrix of All 26 Audited Policies

| Policy ID | Policy / Gate Name | Primary Code Location | External vs Internal | Blocks Valid Profit Today? | Verdict |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **`POL-01`** | Anti-Self-Approval, Credential & Transfer Firewall | [permissions.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L316-L363) | Internal (Hard Invariant) | No | **`RETAIN`** |
| **`POL-02`** | Subprocess Secret Stripping & Git Worktree Isolation | [permissions.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L62-L94), [builder_and_deployer.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/builder_and_deployer.py#L65-L225) | Internal (Hard Invariant) | No | **`RETAIN`** |
| **`POL-03`** | Protected Control-Plane File Lock | [paa_autonomy_config.json](file:///C:/Users/Anton/source/repos/Dominus/config/paa_autonomy_config.json#L98-L115) | Internal | No (for cron; human can commit) | **`RETAIN`** |
| **`POL-04`** | `<UNTRUSTED_DATA_ONLY>` Sanitizer & Independent QA Gate | [zero_trust.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/zero_trust.py#L38-L82) | Internal | No | **`RETAIN`** |
| **`POL-05`** | Operator Approval JSON Envelope & Scope Matching | [permissions.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L97-L123), [#L308-L362](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L308-L362) | Internal | **Yes (AND-scope bug + wildcard no-TTL)** | **`OPTIMIZE`** |
| **`POL-06`** | `proposal_only_live_promotion` (`< $5,000` NAV) | [builder_and_deployer.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/builder_and_deployer.py#L387-L429) | Internal | Minor friction (missing 1-click CLI promote) | **`OPTIMIZE`** |
| **`POL-07`** | `active_positions_count == 0` Harvester Restart Gate | [builder_and_deployer.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/builder_and_deployer.py#L663-L675), [audit_losing_trades.py](file:///C:/Users/Anton/source/repos/Dominus/audit_losing_trades.py#L423-L429) | Internal | **Yes (`KMIA` UMA dispute blocks deploys)** | **`OPTIMIZE`** |
| **`POL-08`** | `polymarket_all_in_one.py` `< 1 MB` Canary Cap & CRLF Guard | [builder_and_deployer.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/builder_and_deployer.py#L326-L335) | Internal | No today (`910.7 KB / 1,000 KB` on `all_in_one`; add binary-diff block) | **`OPTIMIZE`** |
| **`POL-09`** | 3-Verdict Forensics Wall & WFO Parameter Freeze | [SKILL.md](file:///C:/Users/Anton/source/repos/Dominus/.agents/skills/trade-forensics/SKILL.md#L27-L69), [audit_losing_trades.py](file:///C:/Users/Anton/source/repos/Dominus/audit_losing_trades.py#L342-L418) | Internal | Ambiguous on riskless config calibration | **`OPTIMIZE`** |
| **`POL-10`** | PAA AI Spend Caps & Stale `$0.0730/hr` VM Cost Rate | [paa_autonomy_config.json](file:///C:/Users/Anton/source/repos/Dominus/config/paa_autonomy_config.json#L59-L76), [budget.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/budget.py#L116) | Internal | Distorts net-after-infra EV by `+$0.93/d` | **`OPTIMIZE`** |
| **`POL-11`** | `> $1.50` / `0.75`-Share Accounting Discrepancy Safeguard | [accountant.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/accountant.py#L217-L218), [paa_autonomy_config.json](file:///C:/Users/Anton/source/repos/Dominus/config/paa_autonomy_config.json#L84-L85) | Internal | No | **`RETAIN`** |
| **`POL-12`** | PID-1 Supervisor & User-Timer Self-Healing | [monitor.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/monitor.py#L548-L660) | Internal | No | **`RETAIN`** |
| **`POL-13`** | `hard_ruin_floor_usd: $62.00` & Riskless Box Halt | [polymarket_strategy_and_risk.json](file:///C:/Users/Anton/source/repos/Dominus/config/polymarket_strategy_and_risk.json#L76), [polymarket_live_harvester.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L1260-L1268) | Internal | **CRITICAL (`$47.38 < $62` post-`KMIA` halt!)** | **`OPTIMIZE`** |
| **`POL-14`** | `riskless_only_mode: true` (`< $150` Directional Lock) | [polymarket_strategy_and_risk.json](file:///C:/Users/Anton/source/repos/Dominus/config/polymarket_strategy_and_risk.json#L20-L24) | Internal | No (protects `$47.38` seed from variance ruin) | **`RETAIN`** |
| **`POL-15`** | `strict_pure_riskless_mode` Allowlist & Sleeve Pauses | [stage_c_zero_loss_velocity.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/stage_c_zero_loss_velocity.py#L53-L118), [#L209-L327](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/stage_c_zero_loss_velocity.py#L209-L327) | Internal | **Yes (blocks graduated `CAL1`/`COND1`; leaves `W1`/`W_PRUNE1` WU basis open)** | **`REPLACE`** |
| **`POL-16`** | `_grad8` (`8/8` + `<300s` `alpha124` mtime) & WFO Gates | [polymarket_live_harvester.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L5619-L5645), [weekly_wfo_governance.py](file:///C:/Users/Anton/source/repos/Dominus/scripts/weekly_wfo_governance.py#L83-L119) | Internal | **Yes (`300s` shadow mtime kills live `D1`/`C1`)** | **`REPLACE`** |
| **`POL-17`** | Multi-Table Bankroll Tiers (`$88..$5,000`) & Book Basis | [polymarket_live_harvester.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L1039-L1130), [holistic_strategy_governance.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/holistic_strategy_governance.py#L690-L794) | Internal | **Distorts risk (`$97.89` book vs `$47.52` NAV)** | **`OPTIMIZE`** |
| **`POL-18`** | Per-Event / Weather-Station Concentration Cap | [riskless_protocol_v2_expansion.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/riskless_protocol_v2_expansion.py#L1799-L1807), [#L2004-L2134](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/riskless_protocol_v2_expansion.py#L2004-L2134) | Internal | **Cap bug (`$27.41` = `57.7%` NAV vs `15%`!)** | **`OPTIMIZE`** |
| **`POL-19`** | Sequential `>= 3`-Leg `MULTI_LEG_BUNDLE` Quarantine | [stage_c_zero_loss_velocity.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/stage_c_zero_loss_velocity.py#L120-L151), [#L250-L261](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/stage_c_zero_loss_velocity.py#L250-L261) | Internal | Protects EV; default unlock is `$150` vs `$500` | **`REPLACE`** |
| **`POL-20`** | Seed Capital-Velocity Hurdle (`8.0h` / `15.0 bps/hr`) | [holistic_strategy_governance.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/holistic_strategy_governance.py#L796-L848) | Internal | **Exempts unmergeable 24h `C1`; uses `$97.89` book** | **`OPTIMIZE`** |
| **`POL-21`** | `enable_ungraduated_v3_math_live: true` & `risk_config.json` | [polymarket_strategy_and_risk.json](file:///C:/Users/Anton/source/repos/Dominus/config/polymarket_strategy_and_risk.json#L188), [polymarket_risk_config.json](file:///C:/Users/Anton/source/repos/Dominus/config/polymarket_risk_config.json#L1-L49) | Internal | Legacy config drift hazard | **`REMOVE`** |
| **`POL-22`** | Stage G `0`-Key Shadow `.env`, P0 Gate 0 & Double-Zero 5-Gate | [cross_venue_shadow_deployment_gates.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_shadow_deployment_gates.py#L618-L1778) | External + Safety | No (`$0` lost realistic EV at `$47.38`) | **`RETAIN`** |
| **`POL-23`** | Systemd 2-vCPU / 4 GB RAM Cgroup Fences | [polymarket-cross-venue-shadow.service](file:///C:/Users/Anton/source/repos/Dominus/systemd/polymarket-cross-venue-shadow.service#L14-L28), [polymarket-alpha124-shadow.service](file:///C:/Users/Anton/source/repos/Dominus/systemd/polymarket-alpha124-shadow.service#L15-L20) | Internal (Infra) | Combined RSS burst risk (`alpha124` `1550M`) | **`OPTIMIZE`** |
| **`POL-24`** | Stale `180MB`/`320MB` Restriction Registry Prose | [cross_venue_unblock_and_certification.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_unblock_and_certification.py#L1517-L1530) | Internal | Diagnostic drift only (`320M` vs `512M`) | **`REMOVE`** |
| **`POL-25`** | Dashboard `POST /api/shutdown` Localhost + CSRF Gate | [dominus_command_center.py](file:///C:/Users/Anton/source/repos/Dominus/scripts/dominus_command_center.py#L4411-L4440) | Internal | No | **`RETAIN`** |
| **`POL-26`** | Emergency Stop (`KILL_SWITCH` / `PAA_MASTER_STOP`) & Resume | [paa_cli.py](file:///C:/Users/Anton/source/repos/Dominus/scripts/paa_cli.py#L390-L449), [paa_emergency_stop.sh](file:///C:/Users/Anton/source/repos/Dominus/scripts/paa_emergency_stop.sh#L1-L27) | Internal | **Emergency gap (no out-of-band CLOB `cancel_all`)** | **`OPTIMIZE`** |
