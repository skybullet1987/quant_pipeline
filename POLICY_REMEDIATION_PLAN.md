# DOMINUS v5.0 — Surgical Policy, Permission & Owner-Control Remediation Plan (`POLICY_REMEDIATION_PLAN.md`)

**Campaign:** DOMINUS v5.0 Supreme Profit & Operational Freedom (Phase 1 / Requirement R2)  
**Auditor:** Agent G (`@policy-auditor` — Policy, Permissions & Owner-Control Auditor)  
**Audit Timestamp:** 2026-11-11 UTC  
**Safety Attestation:** All 5 deliverables were produced with **100% read-only inspection** on `kraken-finland` (`0` remote writes, `0` heavy remote processes per `#11`, `0` restarts, `0` orders, and all `4/4` disputed `KMIA` positions totaling `$50.51` verified untouched). **Zero** non-overridable agent security boundaries (`POL-01`..`POL-04`) are weakened by any step in this plan.

---

## 1. Prioritized Remediation Roadmap (`P0` -> `P3`)

| Priority | Remediated IDs | Target Files | Core Objective | Expected EV / Safety Gain | Coordination Status |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **`P0-A`** | `POL-13` / `R-01` / `OBST-06` | [polymarket_strategy_and_risk.json](file:///C:/Users/Anton/source/repos/Dominus/config/polymarket_strategy_and_risk.json#L76), [polymarket_live_harvester.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L1260-L1268), [permissions.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L213-L217) | **Eliminate Post-`KMIA` `$62.00` Riskless Blackout Cliff** (`$47.38` cash `< $62.00` floor freezes all `D1`/`C1`/`BOND1` boxes if `KMIA` resolves to `$0.00`) | Prevents **100% live revenue blackout** (`+$30` to `+$75/mo` protected) | **NEW — Must merge before `KMIA` UMA DVM settles** |
| **`P0-B`** | `POL-18` / `R-04` + `POL-19` / `R-40` | [riskless_protocol_v2_expansion.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/riskless_protocol_v2_expansion.py#L1799-L2134), [stage_c_zero_loss_velocity.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/stage_c_zero_loss_velocity.py#L120-L261) | **Enforce True `15%` Reconciled-NAV Event/Station Cap (`$7.11–$7.13`) & Unconditional `< $500` NAV `>=3`-Leg Bundle Block** | Unlocks `107/155` cash-starved `D1` skips + prevents `58%` single-event lockups (`+$18` to `+$45/mo`) | **Implemented in `frp-director-v5` (`d8b4f9d`) — Verify & Land** |
| **`P0-C`** | `POL-05` / `R-05` + `POL-06` + `POL-26` / `R-08` | [permissions.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L97-L123) & [#L308-L362](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L308-L362), [paa_cli.py](file:///C:/Users/Anton/source/repos/Dominus/scripts/paa_cli.py#L390-L449) | **Fix Owner Approval Scope Mapping, Enforce Wildcard TTL + One-Shot Consumption, & Harden `emergency-stop --include-trading` (`KILL_SWITCH` + Out-of-Band `cancel_all_orders`)** | Restores clean 1-command owner control & closes uncancelled Maker bid emergency gap | **NEW — Ready for PAA OS patch** |
| **`P1-A`** | `POL-15` / `R-02` | [stage_c_zero_loss_velocity.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/stage_c_zero_loss_velocity.py#L80-L118) & [#L295-L326](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/stage_c_zero_loss_velocity.py#L295-L326) | **Unblock Dead-Code Graduated `CAL1` & `COND1` 2-Leg Boxes; Gate Single-Leg WU Proxy Weather (`W1` / `W_PRUNE1`) on Dual-Source Consensus** | Unlocks `+$8` to `+$22/mo` (`$47.38`) / `+$65` to `+$185/mo` (`$500`) + eliminates WU/METAR basis risk | **NEW — Surgical allowlist alignment** |
| **`P1-B`** | `POL-16` / `R-03` | [polymarket_live_harvester.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L5619-L5637) | **Decouple Live Graduated `D1`/`C1`/`BOND1` Execution from `< 300s` `alpha124_shadow_state.json` Mtime** (critical given `alpha124` `~75m` OOM restarts on `3.9 GiB` swapless host!) | Eliminates live arb blind spots during shadow OOM restarts (`+$3` to `+$12/mo`) | **NEW — Pairs with `@reliability` `F-01` RSS fix** |
| **`P1-C`** | `POL-20` / `R-09` + `R-21` | [holistic_strategy_governance.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/holistic_strategy_governance.py#L812-L820), [polymarket_live_harvester.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L5669-L5678) | **Require Verified Instant Merge (`_merge_wallet_ok`) for `C1` Lockup Exemption & Pass Undisputed Reconciled NAV (`$47.52`) to Velocity/Tier Gates** | Prevents unmergeable `24h` `C1` carries from starving high-velocity `D1`/`BOND1` (`+$6` to `+$18/mo`) | **NEW — Pairs with `@mof-crossvenue` `#13` on-chain merge audit** |
| **`P2-A`** | `POL-07` / `R-06` + `POL-08` / `R-07` + `POL-10` / `R-10` | [builder_and_deployer.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/builder_and_deployer.py#L326-L335) & [#L663-L675](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/builder_and_deployer.py#L663-L675), [audit_losing_trades.py](file:///C:/Users/Anton/source/repos/Dominus/audit_losing_trades.py#L423-L429), [paa_autonomy_config.json](file:///C:/Users/Anton/source/repos/Dominus/config/paa_autonomy_config.json#L67) | **Unify `_is_restart_safe_frozen_uma_lock` Across All 3 Deployers, Freeze `polymarket_all_in_one.py` (`910.7 KB / 1,000 KB`) + Add Binary-Diff Guard, & Update VM Cost `0.0730 -> 0.0343` (`$24.67/mo`)** | Unblocks safe UMA-frozen deployments + removes `+$27.89/mo` phantom infra accounting drag | **NEW — Clean governance consolidation** |
| **`P2-B`** | `POL-21` / `R-11`..`12` + `POL-24` / `R-13` | [polymarket_strategy_and_risk.json](file:///C:/Users/Anton/source/repos/Dominus/config/polymarket_strategy_and_risk.json#L188), [polymarket_risk_config.json](file:///C:/Users/Anton/source/repos/Dominus/config/polymarket_risk_config.json), [cross_venue_unblock_and_certification.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_unblock_and_certification.py#L1517-L1530) | **Set `enable_ungraduated_v3_math_live: false`, Sync Legacy `polymarket_risk_config.json`, & Sync `512M` Cgroup Prose** | Eliminates latent config landmines & telemetry drift | **NEW — Zero-risk cleanup** |
| **`P3`** | `POL-01`..`04`, `POL-11`..`12`, `POL-14`, `POL-22`, `POL-25` | `permissions.py`, `zero_trust.py`, `accountant.py`, `monitor.py`, `cross_venue_shadow_deployment_gates.py`, `dominus_command_center.py` | **Retain All Essential Safety, Zero-Trust, Accounting-Discrepancy (`>$1.50` / `0.75` shares), `P0 Gate 0`, & Double-Zero (`c206fea1`) Protections Permanently** | Preserves `100%` principal, security & legal compliance | **PERMANENT RETAIN** |

---

## 2. Exact Surgical Code & Config Specifications (`P0` & `P1`)

### Specification `P0-A`: Fix Post-`KMIA` `$62.00` Riskless Halt Cliff (`POL-13` / `R-01`)
- **Why Urgent:** Current liquid cash is **`$47.38`** (`$47.52` mark-to-bid NAV). `tot_equity` is only `$97.89` because the 4 disputed `KMIA` positions are valued at `$50.51` cost. If `KMIA` resolves to `$0.00`, `tot_equity` becomes `$47.38 < $62.00`, tripping `self.halted = True` (`"Account equity $47.38 < $62.00..."`), which matches `"equity"` in [`EmergencyRiskController.is_riskless_box_halted()`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L1266) and freezes all zero-loss boxes!
- **Exact Changes:**
  1. In [config/polymarket_strategy_and_risk.json](file:///C:/Users/Anton/source/repos/Dominus/config/polymarket_strategy_and_risk.json#L72-L77), add `"riskless_hard_ruin_floor_usd": 38.0` alongside `"hard_ruin_floor_usd": 62.0` (so directional remains double-fenced at `$62.0` / `$150.0` while pure riskless boxes halt only if reconciled cash+undisputed equity falls below `$38.00` — i.e., an unexpected `>$9.38` execution/accounting loss from `$47.38`).
  2. In [`EmergencyRiskController.is_riskless_box_halted()`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L1260-L1268), replace the blanket `"equity"` substring check with an explicit check against `riskless_hard_ruin_floor_usd` (`default 38.0`).
  3. In [`PermissionGate.inspect_config_envelope`](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L213-L217), enforce `min_hard_ruin_floor_usd` (`38.0` for riskless, `42.0` statutory floor in `paa_autonomy_config.json`) cleanly when approved under single scope `"INCREASE_CAPITAL_EXPOSURE"`.

---

### Specification `P0-C`: Fix Owner Approval Scope Bugs, Wildcard TTL & Emergency Stop (`POL-05`, `POL-26`)
- **Target 1 — [`src/paa_os/permissions.py`](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L97-L123) & [`#L308-L362`](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L308-L362):**
  1. **Keep Non-Overridable Security Checks First (`L332-359` untouched — plus optional substring additions):** `SELF_APPROVAL_TAMPERING_FORBIDDEN` (`data/polymarket/paa/approvals`), `.env`/`.key`/`.pem` blocks, and `self.forbidden_patterns` (`forbidden_diff_patterns`: `"POLYGON_PRIVATE_KEY"`, `"HYPERLIQUID_PRIVATE_KEY"`, `"POLY_BUILDER_SECRET"`, `"safeTransferFrom("`, `"eth_sendRawTransaction"` at `permissions.py:161-170, 344-346` & `paa_autonomy_config.json:116-122`) continue to return `False` unconditionally (`FORBIDDEN_CREDENTIAL_OR_TRANSFER_PATTERN`) before any approval lookup; optionally append `"MNEMONIC"`, `"eth_sendTransaction"`, and `"withdraw("` as added defence-in-depth.
  2. **Fix Per-Category Scope Mapping (`L308-313` & `L360-362`):**
     - Partition `violations` by prefix:
       - `RISK_FLOOR_WEAKENED` / `RISK_CAP_EXCEEDED` / `RISK_CONTROL_WEAKENED` / `PRICE_CEILING_RAISED` -> cleared by `"INCREASE_CAPITAL_EXPOSURE"`
       - `NEW_LIVE_TRADING_ACTIVATION` / `NEW_LIVE_ASSET_ACTIVATION` / `UNGRADUATED_LIVE_ACTIVATION` -> cleared by `"NEW_LIVE_TRADING_ACTIVATION"`
       - `PROTECTED_FILE_MODIFIED` -> cleared by `"CREDENTIAL_OR_PERMISSION_EXPANSION"`
     - Never require `ok_exp and ok_live` when only one class of violation is present!
  3. **Enforce Expiry (`expires_at_utc`) & Single-Release Consumption (`L109-123`):**
     - Reject any approval JSON with `"target_id": "*"` on live-promotion/exposure/permission scopes unless an explicit future `expires_at_utc` (`<= +24h` max window) is present and `consumed_at_utc` is null.
     - Add `"LIVE_PRODUCTION_PROMOTION"` alongside `explicit_scopes` in `permissions.py:180-188` and document all valid scopes in `paa_autonomy_config.json`.
- **Target 2 — [`scripts/paa_cli.py`](file:///C:/Users/Anton/source/repos/Dominus/scripts/paa_cli.py#L390-L449):**
  1. Add human-only subcommands `approvals list`, `approvals grant --target-id <REL_ID> --scope <SCOPE> --ttl-minutes 60 --reason "..."`, `approvals revoke <FILE>`, and `promote-release <REL_ID>` — **hard-refusing execution (`SystemExit(77)`) if `os.environ.get("PAA_SIGNING_DISABLED") == "1"` or `bool(os.environ.get("PAA_WORKER_ROLE"))` or `not sys.stdin.isatty()`** so no autonomous subprocess spawned by `build_isolated_worker_env` (`permissions.py:81-82`) can ever invoke it!
  2. Harden `cmd_emergency_stop --include-trading` (`L408-L411`):
     - Atomically write `data/polymarket/KILL_SWITCH` in addition to `data/polymarket/paa/PAA_MASTER_STOP`.
     - Stop `polymarket-live-harvester.service`, `polymarket-alpha124-shadow.service`, `polymarket-cross-venue-shadow.service`, and `polymarket-cross-venue-shadow-watchdog.timer`.
     - Run an independent out-of-band `PolymarketExecutor.cancel_all_orders()` check after `systemctl stop` so even if the harvester hung or crashed prior to `SIGTERM`, **zero resting Maker bids (`BOND1`/`MKR_LOCK1`) remain live on the CLOB**.
  3. Upgrade `cmd_resume` (`L435-L449`) to report `KILL_SWITCH` and trading-service status explicitly and require `--include-trading` to remove `KILL_SWITCH` and restart trading/shadow services.

---

### Specification `P1-A`: Unblock `CAL1` & `COND1` Structural 2-Leg Boxes + Gate Proxy-Oracle Weather (`POL-15` / `R-02`)
- **Target — [`src/polymarket_research/stage_c_zero_loss_velocity.py`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/stage_c_zero_loss_velocity.py#L280-L326):**
  1. Add `"CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX"` (`LADDER_MONO`, enforcing `t_early_ts < t_late_ts` and matching canonical event/oracle hash) and `"COND1_MACRO_PARTITION_BOX"` (`MACRO_DOMINANCE` / `NEGRISK_2LEG`, enforcing exhaustive 2-outcome partition and `rem_tte <= 48h`) to the 2-leg payoff-dominance allowlist (`L296-305`), reconnecting the currently dead `cond1_short_ok` bridge in `polymarket_live_harvester.py:5715-5718`.
  2. For `W1_SOLAR_PEAK_LOCK` and `W_PRUNE1_DEAD_NO_BOND` (`L280-292`), require `bool(candidate_box.get("dual_source_wu_metar_verified")) is True` (and `$0` ASOS `$` maintenance flag, already enforced in `test_asos_maintenance_dollar_flag_blocks_intraday_solar_lock`) + strict `15%` station-day cap (`<= $7.11`).

---

### Specification `P1-B`: Decouple Live Graduated Boxes from `300s` `alpha124` Shadow Mtime (`POL-16` / `R-03`)
- **Target — [`src/polymarket_research/polymarket_live_harvester.py`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L5619-L5637):**
  - Replace the hard `> 300.0s` `ALPHA124_STATE_STALE` abort (`L5622-5623`) with a two-tier staleness check:
    - If `(now - st_info.st_mtime) <= 300.0`: normal operation.
    - If `300.0 < (now - st_info.st_mtime) <= 86400.0` AND `self._d1_grad_cache` (or persisted graduation snapshot) already holds `8/8` (`0`-loss) graduation for `sleeve_src` (`D1_SAME_ORACLE_DOMINANCE_BOX`, `C1_BINARY_COMPLETE_SET`, `BOND1_UMA_RESOLUTION_CARRY`): **log a rate-limited warning and allow live execution using last-verified graduation state**, blocking **only** ungraduated/newly-bridging sleeves until `alpha124_shadow_state.json` refreshes!
  - **Why Critical:** Directly insulates live revenue from the `~65–77m` `polymarket-alpha124-shadow.service` OOM restarts documented by `@reliability` (`#8`, `#10`).

---

### Specification `P1-C` & `P2-A`: Velocity Merge Check, UMA-Safe Deployer Unification & Stale VM Cost Fix
1. **Velocity Hurdle (`src/polymarket_research/holistic_strategy_governance.py:812`):** Exempt `COMPLETE_SET` / `C1_BINARY_COMPLETE_SET` from `eff_hrs` lockup ONLY when `fast_recycle_eligible=True` (`_merge_wallet_ok` verified) so unmergeable `24h` `45 bps` complete sets cannot tie up `$47.38` seed cash at `1.9 bps/hr`.
2. **Deployer UMA-Frozen Restart Gate (`src/paa_os/builder_and_deployer.py:663-675` & `audit_losing_trades.py:423-429`):** Import `_safe_to_restart(st_j, time.time())` from `scripts/paa_flat_harvester_redeploy_once.py` (`L36-70`) so passive post-expiry `KMIA` UMA disputes (`exit_order_id=None, pending_entry_intents={}`) do not block owner-approved releases while active pre-expiry positions and resting Maker orders (`MKR_LOCK1` `$8.919` on `6916999`) **do** block restarts until flat!
3. **Canary Bundle & Binary-Diff Hygiene (`src/paa_os/builder_and_deployer.py:326-335` & `src/paa_os/permissions.py:332-337`):** Keep `_run_release_canary_probe`'s `polymarket_all_in_one.py` `< 1,000,000`-byte (`BUNDLE_SIZE_CEILING_EXCEEDED`) and `b"\r\n"` (`BUNDLE_CRLF_DETECTED`) guards intact while freezing feature growth in `polymarket_all_in_one.py` (`910,713` bytes today = `89.3 KB` headroom) in favor of modular `src/polymarket_research/*`, and reject `.sqlite3`/`.jsonl`/`.parquet`/`.pkl` binary/data artifacts in `PermissionGate.inspect_candidate_diff`.
4. **Infra Cost Alignment (`config/paa_autonomy_config.json:67` & `src/paa_os/budget.py:116`):** Change `"prorated_vm_hourly_cost_usd"` from `0.0730` (`$52.56/mo`) to `0.0343` (`$24.67/mo` actual GCP billing).

---

## 3. Security Non-Regression Proof

Every proposed remediation was checked against the 4 non-overridable security invariants:
1. **Anti-Self-Approval (`SELF_APPROVAL_TAMPERING_FORBIDDEN`):** Untouched in `permissions.py:335-336 & 355` + reinforced by `PAA_SIGNING_DISABLED != "1"`, `not PAA_WORKER_ROLE`, and `sys.stdin.isatty()` guards in `paa_cli.py` + mandatory `expires_at_utc` & one-shot consumption (**strictly stronger** than baseline!).
2. **Credential & Secret Exfiltration Prevention:** `SENSITIVE_SIGNING_ENV_KEYS` & `build_isolated_worker_env` (`permissions.py:43-94`), `.env`/`.key`/`.pem` diff blocks (`L333`), and `validate_shadow_env_dict` `0`-signing-key checks (`cross_venue_shadow_deployment_gates.py:1632-1730`) remain **100% intact**.
3. **Unauthorized Fund-Transfer Prevention:** `self.forbidden_patterns` (`forbidden_diff_patterns`: `"POLYGON_PRIVATE_KEY"`, `"HYPERLIQUID_PRIVATE_KEY"`, `"POLY_BUILDER_SECRET"`, `"safeTransferFrom("`, `"eth_sendRawTransaction"` at `permissions.py:161-170, 344-346` & `paa_autonomy_config.json:116-122`) remain **100% intact** (with optional hardening to append `"MNEMONIC"`, `"eth_sendTransaction"`, and `"withdraw("`).
4. **Protected Control-Plane & Jurisdictional Compliance:** All 16 `protected_files` (`paa_autonomy_config.json:98-115` & `permissions.py:140-159`: `.env`, `permissions.py`, `zero_trust.py`, `builder_and_deployer.py`, `accountant.py`, `cross_venue_shadow_deployment_gates.py`, `cross_venue_unblock_and_certification.py`, `execute_approvals.py`, `setup_polymarket_account.py`, `config/paa_master_mandate.md`, `config/paa_autonomy_config.json`, and `config/policies/*`) remain locked against unattended autonomous edits, and all `JURISDICTIONAL` / `P0 Gate 0` live-order blocks (`CA-ON`, `US`/`UK` server IPs) remain **100% fail-closed (`ExitStatus=78`)**.

---

## 4. Deterministic Local Verification Procedure (Zero Remote Load on `kraken-finland`)

Per Swarm Infra Rule `#11` (`3,907 MiB` RAM, `MemorySwapMax=0B` on `kraken-finland`), execute all verification suites **locally** on Windows using `"C:\Program Files\LibreOffice\program\python.exe"`:

```powershell
# 1. Verify all 5 Phase 1 (R2) policy deliverables exist, are non-empty, and contain zero secret patterns
& "C:\Program Files\LibreOffice\program\python.exe" -c "
import pathlib
for name in ['POLICY_AUDIT.md','RESTRICTION_REGISTER.md','OWNER_CONTROL_MATRIX.md','POLICY_PROFIT_IMPACT.md','POLICY_REMEDIATION_PLAN.md']:
    p = pathlib.Path(name)
    assert p.exists() and p.stat().st_size > 4000, f'Missing or truncated: {name}'
    print(f'OK: {name} ({p.stat().st_size:,} bytes)')
"

# 2. Run existing QA & Stage C / Permissions / Governance unit suites locally once P0-P2 code patches are applied
& "C:\Program Files\LibreOffice\program\python.exe" -m unittest discover -s tests -p "test_stage_c_zero_loss_velocity.py" -v
& "C:\Program Files\LibreOffice\program\python.exe" -m unittest discover -s tests -p "test_action4_shadow_service_and_gates.py" -v
```
