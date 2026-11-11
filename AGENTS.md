# DOMINUS v5.0 — Autonomous & Multi-Agent Continuity Manual (`AGENTS.md`)

**Campaign Standard:** DOMINUS v5.0 Supreme Profit & Operational Freedom (Section 15 Continuity Deliverable)  
**Last Reconciled:** `2026-11-11 UTC`  
**Operating Mode:** `RISKLESS_PAA` (`directional.riskless_only_mode = true`, `proposal_only_live_promotion = true`, Jurisdiction Gate = `CA-ON`)  
**Local Workspace:** `C:\Users\Anton\source\repos\Dominus` (Local Python: `"C:\Program Files\LibreOffice\program\python.exe"`)  
**Production Host:** `ssh kraken-finland` (`/home/skybullet1987/quant_pipeline`, GCP `europe-north1-b` Finland, `2` vCPU / `3,907 MiB` physical RAM, **`MemorySwapMax=0B`**, `~$24.67/month` = `$0.822/day`)

---

## 1. Purpose & Immediate Session Bootstrap Protocol

Any future human-paired coding agent, swarm worker, forensic auditor, or PAA OS session MUST reconstruct ground truth in `<60` seconds before touching a single line of code or issuing any SSH command:

1. **Read Reconciled State First (Zero Guessing):**
   - [PROJECT_STATE.md](file:///C:/Users/Anton/source/repos/Dominus/PROJECT_STATE.md) — Exact wallet cash, NAV definitions, 4 disputed `KMIA` positions, 136-record closed ledger decomposition, and memory/SQLite forensics.
   - [DECISIONS.md](file:///C:/Users/Anton/source/repos/Dominus/DECISIONS.md) — Active binding architectural & safety decisions (`D-001`..`D-010`).
   - [DEPLOYMENT_STATUS.md](file:///C:/Users/Anton/source/repos/Dominus/DEPLOYMENT_STATUS.md) & [TASK_LEDGER.md](file:///C:/Users/Anton/source/repos/Dominus/TASK_LEDGER.md) — Live `systemd` unit PIDs, restart counts, and open work items.
   - [POLICY_AUDIT.md](file:///C:/Users/Anton/source/repos/Dominus/POLICY_AUDIT.md), [RESTRICTION_REGISTER.md](file:///C:/Users/Anton/source/repos/Dominus/RESTRICTION_REGISTER.md), [OWNER_CONTROL_MATRIX.md](file:///C:/Users/Anton/source/repos/Dominus/OWNER_CONTROL_MATRIX.md), [POLICY_PROFIT_IMPACT.md](file:///C:/Users/Anton/source/repos/Dominus/POLICY_PROFIT_IMPACT.md), [POLICY_REMEDIATION_PLAN.md](file:///C:/Users/Anton/source/repos/Dominus/POLICY_REMEDIATION_PLAN.md) — Complete 26-policy & 44-restriction governance register.
2. **Verify Zero-Trust Diff Gate Before Any Commit or Promotion:**
   - Every candidate change MUST pass [`PermissionGate.inspect_candidate_diff`](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L316-L363) == `(True, [])` unless accompanied by a human-owner approval JSON in `data/polymarket/paa/approvals/`.

---

## 2. v5.0 Multi-Agent Swarm & PAA OS Architecture

### 2.1 Campaign Swarm Roles & File Ownership Separation
To prevent concurrent edit collisions and Goodhart self-certification, Dominus v5.0 separates authoring domains from independent verification:

| Role / Domain | Core Responsibility | Canonical Deliverables & Owned Modules |
| :--- | :--- | :--- |
| **`@coordinator`** | Campaign orchestration, cross-branch merge sequencing, owner alignment | Swarm board coordination & branch landing |
| **`@reliability` (Agent F — Phase 0)** | On-chain/ledger truth reconciliation, `F-01` swapless RAM bounds, `F-02` disputed floor haircut | [PROJECT_STATE.md](file:///C:/Users/Anton/source/repos/Dominus/PROJECT_STATE.md), [DEPLOYMENT_STATUS.md](file:///C:/Users/Anton/source/repos/Dominus/DEPLOYMENT_STATUS.md), [DECISIONS.md](file:///C:/Users/Anton/source/repos/Dominus/DECISIONS.md), [alpha_124_shadow_daemon.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/alpha_124_shadow_daemon.py), [polymarket_terminal_recorder.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_terminal_recorder.py), [test_phase0_reliability_fixes.py](file:///C:/Users/Anton/source/repos/Dominus/tests/test_phase0_reliability_fixes.py) |
| **`@policy-auditor` (Agent G — R2 & Continuity)** | 26-policy / 44-restriction audit, owner emergency CLI hardening, staged protected-file proposals, continuity manual | [AGENTS.md](file:///C:/Users/Anton/source/repos/Dominus/AGENTS.md), [POLICY_AUDIT.md](file:///C:/Users/Anton/source/repos/Dominus/POLICY_AUDIT.md), [RESTRICTION_REGISTER.md](file:///C:/Users/Anton/source/repos/Dominus/RESTRICTION_REGISTER.md), [OWNER_CONTROL_MATRIX.md](file:///C:/Users/Anton/source/repos/Dominus/OWNER_CONTROL_MATRIX.md), [paa_cli.py](file:///C:/Users/Anton/source/repos/Dominus/scripts/paa_cli.py), [audit_losing_trades.py](file:///C:/Users/Anton/source/repos/Dominus/audit_losing_trades.py), [APPLY_AND_ROLLBACK.md](file:///C:/Users/Anton/source/repos/Dominus/paa_staging/proposals/v50_owner_control_package/APPLY_AND_ROLLBACK.md) |
| **`@frp-director` (Risk, Sizing & Velocity)** | `15%` reconciled-NAV event concentration cap, `<$500` `>=3`-leg bundle gate, `$30` riskless ruin floor, `CAL1`/`COND1` allowlist, `24h` graduation cache | [riskless_protocol_v2_expansion.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/riskless_protocol_v2_expansion.py), [stage_c_zero_loss_velocity.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/stage_c_zero_loss_velocity.py), [holistic_strategy_governance.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/holistic_strategy_governance.py) |
| **`@mof-crossvenue` (Stage G & On-Chain MOF)** | 6-venue Stage G shadow certification, Double-Zero 5-gate verifier, SQLite compaction, Polygon CTF/Relayer audit | [cross_venue_riskless_shadow.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_riskless_shadow.py), [cross_venue_telemetry_and_watchdog.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_telemetry_and_watchdog.py), [cross_venue_shadow_deployment_gates.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_shadow_deployment_gates.py) |
| **`@latency-arch` (Phase 4 Hot Path)** | 13-stage deterministic latency benchmark, `orjson` atomic state journaling, HTTP keep-alive & pre-warmed EIP-712 signing | [polymarket_live_harvester.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py), [net_alpha_opportunity_engine.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/net_alpha_opportunity_engine.py) |
| **`@adv-auditor` (Independent Verifier)** | Read-only adversarial reproduction of math, diffs, tests, digests, and live host invariants | Signs off `VERIFIED` only after zero-defect reproduction (`Session C` separation of duties) |

### 2.2 Runtime PAA Autonomous Operating System (`src/paa_os/`)
On `kraken-finland`, scheduled `systemd --user` timers invoke [paa_cli.py](file:///C:/Users/Anton/source/repos/Dominus/scripts/paa_cli.py) across isolated components:
- [`PAADirector`](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/director.py) (`15m` + `.path` event trigger) — Task queue orchestration & dashboard synthesis.
- [`PAAMonitor`](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/monitor.py) (`1m`) & [`PAAIndependentSupervisor`](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/monitor.py#L548-L660) (`2m`) — Heartbeat/accounting reconciliation and self-healing (strictly honoring `PAA_MASTER_STOP`).
- [`PAAAccountant`](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/accountant.py) — Reconciles on-chain `pUSD` + ERC-1155 shares against `live_harvester_state.json`; engages `ACCOUNTING_SAFEGUARD_ACTIVE.json` if discrepancy exceeds `$1.50` or `0.75` shares.
- [`PermissionGate`](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L126-L363), [`ZeroTrustVerifier`](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/zero_trust.py#L593-L774) & [`DeploymentController`](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/builder_and_deployer.py#L228-L774) — Enforce detached credential-stripped worktrees, protected-file locks, canary checks, and `< $5,000` NAV `proposal_only_live_promotion`.

---

## 3. Authoritative Financial, Wallet & Ledger Baseline (`2026-11-11 UTC`)

Never mix simulated shadow benchmarks (`alpha124_shadow_state.json`, `shadow_telemetry.sqlite3`) with realized on-chain cash:

- **Funder Beacon Proxy (`sig_type=3`, `POLY_1271`):** `0x013A2474454fBd8738cff6a7f204eF1bc377F4e9` — holds **`$47.377122` (`$47.38`) liquid `pUSD`** (`$0.000000` discrepancy vs `live_bankroll`).
- **Signer EOA:** `0x9703b71686219d34869e8fb89a93263f9e0d50a5` — holds **`41.81376003 POL`** (`~$3.70` gas reserve) plus **`$1.000000 USDC.e`** untracked EOA cash.
- **Three Distinct NAV Definitions (Always Report Explicitly):**
  1. **True Worst-Case Guaranteed-Floor NAV:** **`$47.38`** (`$47.377122` cash + `$0.00` worst-case payout on the 4 disputed `KMIA` positions).
  2. **Mark-to-Bid Liquidation NAV:** **`$47.52`** (`$47.377122` cash + `$0.1390` live CLOB bid across the `52.0` disputed `KMIA` shares).
  3. **Persisted Harvester Book Equity (`total_account_equity`):** **`$97.89`** (`$47.377122` cash + `$50.51` cost-basis frozen UMA receivable). **Never size clips or concentration caps off `$97.89` book equity while `KMIA` is disputed!**
- **Closed-Ledger Decomposition (`136` Total Records = `118 + 8 + 10`):**
  - **`77` Pure-Riskless Real Filled Trades:** `77W / 0L` (`100.0%` WR), **`+$17.9281`** verified net P&L (`$0.5825` fees, `$867.79` notional).
  - **`41` Retired Directional / Lattice Real Filled Trades:** `30W / 11L`, **`-$73.3385`** net P&L (`SLEEVE_1_SUBHOURLY_15M`, `SLEEVE_1_CORE_302`, `SOC2_EXACT_SCORE_2D_LATTICE` — all hard-disabled in `RISKLESS_PAA`).
  - **Combined `118` Real Filled Trades:** **`-$55.4104`** exact on-chain wallet cash P&L (`$0.0000` drift), plus `8` flat `$0.00` merges and `10` zero-fill/cancelled records.
- **Infrastructure Breakeven Hurdle:** `$24.67/month` (`$0.822/day`) requires **`+7.23 bps/hr` (`+173.5 bps/day`)** portfolio-wide on `$47.38` liquid cash (`+3.50 bps/hr` at `$97.89`; `+0.69 bps/hr` at `$500`).

---

## 4. Mandatory Non-Overridable Safety & Operational Rules

### Rule 1 — Absolute Non-Interference With the 4 Disputed `KMIA` Nov 7 Positions (`D-001`)
- Markets `6707503` (`35.0 NO` shares across `WS_SNIPE_Miami_KMIA_242960`, `688670`, `837595`) and `6707502` (`17.0 YES` shares in `MULTI_LEG_BUNDLE_LIVE_KMIA_1794113999_318559_UNWRESID_20116898_1794111898`), totaling **`$50.51` cost basis**, are in `umaResolutionStatus == "disputed"` with an active official Polymarket case opened by the owner.
- **STRICT PROHIBITION:** Never sell into `0.2c–0.3c` distressed bids, never place `exit_order_id` or `unwind_order_id` orders on them, never merge/burn them, and never mutate their state entries.

### Rule 2 — `3,907 MiB` Swapless `kraken-finland` Host Protection (`D-010`)
- `kraken-finland` enforces `MemorySwapMax=0B` (`0` bytes of usable cgroup swap) across trading, recorder, and shadow units.
- **NEVER run `pytest`, heavy backtests, or multi-hundred-MB Python scripts on `kraken-finland`** — a single `~650 MiB` `pytest` run triggers kernel `oom-kill` against live/shadow daemons!
- Run all unit tests locally on Windows using:
  ```powershell
  & "C:\Program Files\LibreOffice\program\python.exe" -m unittest discover -s tests -p "test_v50_*.py" -v
  ```
  *(Note: Local LibreOffice Python `3.12` uses stdlib `unittest` — write all new test suites with `unittest.TestCase` so they run with zero external test-runner dependencies.)*

### Rule 3 — Zero-Trust Agent Security & `protected_files` Boundary (`D-002`, `D-003`)
- **Never weaken** anti-self-approval (`SELF_APPROVAL_TAMPERING_FORBIDDEN` on `data/polymarket/paa/approvals/`), subprocess credential stripping ([`SENSITIVE_SIGNING_ENV_KEYS` & `build_isolated_worker_env`](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L43-L94)), or `forbidden_diff_patterns` ([permissions.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L161-L170)).
- **16 Protected Files ([paa_autonomy_config.json](file:///C:/Users/Anton/source/repos/Dominus/config/paa_autonomy_config.json#L98-L115)):** Autonomous workers MUST NOT edit `.env`, `src/paa_os/{permissions,zero_trust,builder_and_deployer,accountant}.py`, `src/polymarket_research/{cross_venue_shadow_deployment_gates,cross_venue_unblock_and_certification,execute_approvals,setup_polymarket_account}.py`, `config/paa_master_mandate.md`, `config/paa_autonomy_config.json`, or `config/policies/*` directly in candidate commits. Stage proposed changes under `paa_staging/proposals/` for explicit human owner execution (see [APPLY_AND_ROLLBACK.md](file:///C:/Users/Anton/source/repos/Dominus/paa_staging/proposals/v50_owner_control_package/APPLY_AND_ROLLBACK.md)).

### Rule 4 — Risk, Forensics & Jurisdictional Compliance Invariants (`D-004`..`D-008`)
- **3-Verdict Forensic Wall ([SKILL.md](file:///C:/Users/Anton/source/repos/Dominus/.agents/skills/trade-forensics/SKILL.md), [audit_losing_trades.py](file:///C:/Users/Anton/source/repos/Dominus/audit_losing_trades.py)):** Never tune statistical thresholds (`Z`, `OFI`, `cushion`, `TP/SL`) after `N=1` trade; route threshold hypotheses to Purged WFO (`CPCV(6,2)`, `N >= 50`, `PF >= 1.45`, `PBO <= 0.20`).
- **Concentration & Legging Limits:** Enforce `<= 15%` reconciled NAV (`~$7.11` at `$47.38`) per correlated event/weather station across all sleeves, and keep sequential `>= 3`-leg CLOB bundles quarantined below `$500` reconciled NAV unless atomic on-chain (`NegRiskAdapter.convertPositions` / `splitPosition`) or verified wallet-inventory-backed.
- **Jurisdiction Gate (`CA-ON` / `P0 Gate 0`):** Never spoof geolocation, use proxies/VPNs, or deploy live order placement to restricted regions (`CA-ON`, `US`, `UK`). Keep read-only public/content market data (`PUBLIC_REST`, `PUBLIC_WEBSOCKET`) cleanly separated from `TRADING` / `ACCOUNT_PRIVATE`.

---

## 5. Canonical Repository Module & Command Map

| Subsystem | Key Files | Standard Verification / Operator Command |
| :--- | :--- | :--- |
| **Live Harvester & Riskless Engine** | [polymarket_live_harvester.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py), [polymarket_live_executor.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_executor.py), [riskless_protocol_v2_expansion.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/riskless_protocol_v2_expansion.py), [stage_c_zero_loss_velocity.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/stage_c_zero_loss_velocity.py), [holistic_strategy_governance.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/holistic_strategy_governance.py) | `python scripts/deploy_polymarket_live.py --dry-run` (verifies `166` manifest files + `riskless_only_mode == True`) |
| **Shadow Daemons & Stage G Cross-Venue** | [alpha_124_shadow_daemon.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/alpha_124_shadow_daemon.py), [polymarket_terminal_recorder.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_terminal_recorder.py), [cross_venue_riskless_shadow.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_riskless_shadow.py), [cross_venue_telemetry_and_watchdog.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_telemetry_and_watchdog.py) | `python -m unittest tests/test_phase0_reliability_fixes.py -v` |
| **PAA OS, Forensics & Owner Emergency CLI** | [paa_cli.py](file:///C:/Users/Anton/source/repos/Dominus/scripts/paa_cli.py), [audit_losing_trades.py](file:///C:/Users/Anton/source/repos/Dominus/audit_losing_trades.py), [paa_flat_harvester_redeploy_once.py](file:///C:/Users/Anton/source/repos/Dominus/scripts/paa_flat_harvester_redeploy_once.py), [dominus_command_center.py](file:///C:/Users/Anton/source/repos/Dominus/scripts/dominus_command_center.py) | Pause autonomy only: `python scripts/paa_cli.py emergency-stop --reason "..."`<br>Full trading halt + CLOB cancel: `python scripts/paa_cli.py emergency-stop --include-trading --reason "..."`<br>Resume: `python scripts/paa_cli.py resume [--include-trading]` |
| **Staged Owner-Control Protected Package** | [APPLY_AND_ROLLBACK.md](file:///C:/Users/Anton/source/repos/Dominus/paa_staging/proposals/v50_owner_control_package/APPLY_AND_ROLLBACK.md), [apply_or_rollback_owner_package.py](file:///C:/Users/Anton/source/repos/Dominus/paa_staging/proposals/v50_owner_control_package/apply_or_rollback_owner_package.py) | `python paa_staging/proposals/v50_owner_control_package/apply_or_rollback_owner_package.py --verify-dry-run` |

---

## 6. Milestone Progression & Handoff Checklist

1. **Current Tier — Seed Compounding (`$47.38` Cash / `$47.52` Reconciled NAV):**
   - Keep `100%` of capital consolidated in single-venue Polygon `pUSD` (`$0/mo` paid infra additions); maximize high-turnover `0%`-fee / mergeable `C1`, `D1`, `CAL1`, `COND1`, `NR_M1`/`NR2`, and `<=2h` `BOND1` velocity (`>= 15 bps/hr`).
   - Ensure `riskless_hard_ruin_floor_usd` (`$30.00–$38.00`) is live **before** `KMIA` UMA DVM settlement so a `$0.00` `KMIA` outcome (`tot_equity = $47.38 < $62.00`) cannot freeze zero-loss arbitrage (`POL-13` / `R-01`).
   - Safe redeploy during `KMIA` dispute: both [paa_flat_harvester_redeploy_once.py](file:///C:/Users/Anton/source/repos/Dominus/scripts/paa_flat_harvester_redeploy_once.py#L36-L70) and [`is_harvester_state_restart_safe`](file:///C:/Users/Anton/source/repos/Dominus/audit_losing_trades.py#L457-L492) recognize passive post-expiry `KMIA` UMA locks as safe to restart across whenever `0` non-frozen positions and `0` non-maker in-flight intents exist.
2. **Milestone `$150` Undisputed Reconciled NAV (`M3.2`):**
   - Re-evaluate `pre_split` inventory recycling (`>= $140`) and Half-Kelly directional canary *only* if shadow WFO passes (`N >= 50, PF >= 1.45, CI95_lo > 0, PBO <= 0.20`) and human owner approves `NEW_LIVE_TRADING_ACTIVATION`.
3. **Milestones `$253` -> `$500+` Undisputed Reconciled NAV (`Stage G` & Multi-Leg):**
   - Review `168.0h` uncontaminated Stage G `certification_report.json` (`0` Double-Zero incidents, post-delay L2 net PnL `> 0`); prioritize `CA-ON`-legal regulated venues (`ForecastEx / IBKR Canada` + `STX Ontario` executed from `CA-ON`, never proxied through `FI`).
   - Keep corporate offshore KYB outlays deferred until `>= $10,000` NAV (`R-31`), and keep `proposal_only_live_promotion: true` active below `$5,000` NAV (`D-002`).
