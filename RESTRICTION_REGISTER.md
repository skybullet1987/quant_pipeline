# DOMINUS v5.0 — Comprehensive Internal & External Restriction Register (`RESTRICTION_REGISTER.md`)

**Campaign:** DOMINUS v5.0 Supreme Profit & Operational Freedom (Phase 1 / Requirement R2)  
**Auditor:** Agent G (`@policy-auditor`)  
**Audit Timestamp:** 2026-11-11 UTC  
**Capital Reference Frame:** `$47.38` liquid `USDC.e` cash | `$47.52` mark-to-bid NAV | `$97.89` persisted book equity (`$50.51` frozen in 4 disputed `KMIA` Nov 7 positions) | `~$24.67/mo` (`$0.82/day`) GCP VM burn.

---

## 1. Mandatory 10-Category Taxonomy & Summary Counts

Every discovered internal and external restriction across trading, data ingestion, venue onboarding, owner control, capital sizing, and OS infrastructure is classified into the **exact 10 mandatory campaign categories**:

| Mandatory Category | Count | Restriction IDs | Actionability Summary |
| :--- | :---: | :--- | :--- |
| **`TECHNICAL_FIXABLE`** | **10** | `R-01` .. `R-10` | **100% internally fixable in code/config** (high-priority bugs, cliffs, dead-code allowlist blocks, and owner-control obstructions) |
| **`LEGACY_UNNECESSARY`** | **4** | `R-11` .. `R-14` | **100% removable/cleanable** legacy config flags, shadow-config drift, and eliminated Stage G internal data gates |
| **`RESOURCE_LIMITATION`** | **3** | `R-15` .. `R-17` | Physical `$47.38` liquid cash scale, `2 vCPU / 4 GB RAM` Finland VM ceiling, and Finland-to-Polymarket network RTT |
| **`AUTHENTICATION_CONFIGURATION`** | **4** | `R-18` .. `R-21` | Missing/optional external API credentials or gateway sessions (`SX_BET_API_KEY`, `STX_API_KEY_ID`, `IBKR_GATEWAY_URL`, `POLY_BUILDER_API_KEY`) |
| **`PROVIDER_CONTRACTUAL`** | **4** | `R-22` .. `R-25` | Exchange-enforced API rate limits, minimum lot sizes (`5 sh` / `$1.00`), taker fee curves, and non-atomic CLOB order matching |
| **`JURISDICTIONAL`** | **5** | `R-26` .. `R-30` | Statutory/geofenced `CA-ON` & server-region restrictions on **live order placement** (`Polymarket`, `Limitless`, `Predict.fun`, `SX Bet`, `STX Ontario` from `FI`) |
| **`KYC_KYB`** | **2** | `R-31` .. `R-32` | Non-restricted corporate entity KYB onboarding & `STX` institutional `apps.stxapp.io` `Data` partner approval |
| **`ESSENTIAL_SAFETY`** | **6** | `R-33` .. `R-38` | **Permanent non-overridable protections** (anti-self-approval, secret/key stripping, `<UNTRUSTED_DATA_ONLY>`, Double-Zero 5-gate verifier, `$1.50` / `0.75`-share accounting safeguard, `0`-key shadow `.env`) |
| **`JUSTIFIED_RISK_LIMIT`** | **5** | `R-39` .. `R-43` | Mathematically sound EV/ruin protections (`riskless_only_mode < $150`, `<$500` sequential `>=3`-leg bundle block, `15%` event concentration cap, `168h` cross-venue certification, seed velocity hurdle) |
| **`UNKNOWN`** | **1** | `R-44` | Unresolved UMA DVM final outcome & exact payout timestamp on the 4 disputed `KMIA` Nov 7 weather positions (`$50.51` cost basis) |

**Total Restrictions Registered & Audited:** **44** (`0` uncategorized, `0` conflated between read-only market data and live order execution).

---

## 2. Full Restriction Register (`R-01` through `R-44`)

### Category 1: `TECHNICAL_FIXABLE` (10 Restrictions — Immediate Internal Code/Config Remediations)

#### `R-01` — Post-`KMIA` Hard Ruin Floor Cliff (`$62.00` vs. `$47.38` Liquid Cash) Freezing Riskless Arbitrage
- **Category:** `TECHNICAL_FIXABLE`
- **Exact Locations:** [polymarket_strategy_and_risk.json](file:///C:/Users/Anton/source/repos/Dominus/config/polymarket_strategy_and_risk.json#L76), [polymarket_live_harvester.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L1168-L1175), [polymarket_live_harvester.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L1260-L1268), [permissions.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L213-L217)
- **Enforcement Behavior:** `hard_ruin_floor_usd` is set to `$62.00`. `EmergencyRiskController.check_equity_drawdown` sets `self.halted = True` with `"Account equity $X < $62.00..."` whenever `tot_equity < 62.0`, and `is_riskless_box_halted()` (`L1266`) returns `True` whenever `"equity"` appears in `self.halt_reason`, halting **all** live `D1`/`C1`/`BOND1` riskless boxes. Today `tot_equity` is artificially `$97.89` only because the 4 disputed `KMIA` positions are booked at `$50.51` par/cost.
- **Economic Impact at `$47.38` Liquid (`$97.89` Book):** **100% revenue blackout (`-$1.50` to `-$4.00/day` gross arb EV + `-$0.82/day` unrecovered VM burn)** the instant `KMIA` resolves to `$0.00` and `tot_equity` drops to `$47.38 < $62.00`!
- **Safe Remediation:** Split `directional_min_equity_floor_usd: 150.0` from `riskless_hard_ruin_floor_usd: 38.0` (halting zero-loss boxes only if reconciled liquid+undisputed equity drops `> $9.38` below `$47.38`, signaling an execution anomaly) and allow `permissions.py:213-217` to respect `min_hard_ruin_floor_usd` (`$38.00–$42.00`) with owner approval.
- **Verification Procedure:** Unit test simulating `KMIA` settlement at `$0.00` (`bal = 47.38`, `active_positions = {}`) asserting `harvester._is_d1_box_halted() is False` while `bal = 37.50` asserts `harvester._is_d1_box_halted() is True`.

#### `R-02` — Dead-Code Firewall Blocking Graduated `CAL1` & `COND1` 2-Leg Riskless Boxes
- **Category:** `TECHNICAL_FIXABLE`
- **Exact Locations:** [stage_c_zero_loss_velocity.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/stage_c_zero_loss_velocity.py#L219) & [#L296-L305](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/stage_c_zero_loss_velocity.py#L296-L305) vs. [polymarket_live_harvester.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L5467-L5471) & [#L5715-L5718](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L5715-L5718)
- **Enforcement Behavior:** `check_strict_pure_riskless_candidate_gate` runs at `polymarket_live_harvester.py:5467` and rejects any 2-leg box not in `{"D1_SAME_ORACLE_DOMINANCE_BOX", "D1_4H_DOMINANCE_BOX", "D1_QUIET_BOOK_BOX", "C1_BINARY_COMPLETE_SET", "SP4_SUBPERIOD_CLINCH_AND_PROP_EXPANSION"}` (`L296-305`), returning `PURE_RISKLESS_SLEEVE_NOT_ALLOWLISTED` before `cond1_short_ok` (`L5715`) or `CAL1` (`L5682`) can ever execute—directly contradicting `operator_approval_20261103_zero_loss_seed_focus.json` and Roadmap §16 (`12/8` & `11/8` 100% WR graduated engines).
- **Economic Impact at `$47.38` Liquid:** Blocks valid `0%`-fee / low-fee calendar monotonicity (`CAL1`) and closed binary macro partition (`COND1`) arbs worth an estimated **`+$6` to `+$18/month`** at `$47.38` (`+$60` to `+$180/month` at `$500`).
- **Safe Remediation:** Add `CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX` (`LADDER_MONO` with verified `T_early <= T_late` & identical oracle clause) and `COND1_MACRO_PARTITION_BOX` (`MACRO_DOMINANCE` / `NEGRISK_2LEG` with verified exhaustive 2-way partition & `TTE <= 48h`) to `check_strict_pure_riskless_candidate_gate` (`L296-326`), while quarantining single-leg WU proxy sensor sleeves (`W1_SOLAR_PEAK_LOCK`, `W_PRUNE1_DEAD_NO_BOND`) unless dual-source WU+METAR agreement holds.
- **Verification Procedure:** Call `evaluate_strict_pure_riskless_candidate` on recorded `CAL1` (`T1 < T2`) and `COND1` fixtures (`strict_pure_riskless_mode=True`) and verify `(True, "OK")`, while inverted `T1 > T2` returns `(False, "PURE_RISKLESS_INVERTED_CALENDAR_DEADLINE")`.

#### `R-03` — Live Graduated `D1`/`C1` Box Execution Hard-Coupled to `< 300s` `alpha124_shadow_state.json` Mtime
- **Category:** `TECHNICAL_FIXABLE`
- **Exact Locations:** [polymarket_live_harvester.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L5619-L5623)
- **Enforcement Behavior:** `if (time.time() - st_info.st_mtime) > 300.0: return {"executed": False, "reason": "ALPHA124_STATE_STALE"}` inside `maybe_execute_graduated_d1_box` blocks **every** live riskless box (`C1`, `D1`, `BOND1`, `NR_M1`) if `polymarket-alpha124-shadow.service` stalls, restarts, or hits its `1550M` cgroup limit for `>5` minutes.
- **Economic Impact at `$47.38` Liquid:** Unnecessary live arbitrage outage window during any shadow-daemon hiccup (`-$1` to `-$5` per volatility spike missed).
- **Safe Remediation:** Persist last-verified graduation map in memory/disk up to `86,400s` (`24h`) with degraded-shadow warning telemetry for **already-graduated** sleeves (`D1`, `C1`, `BOND1`), failing closed on `> 300s` staleness **only** for newly graduating sleeves.
- **Verification Procedure:** Unit test setting `alpha124_shadow_state.json` `st_mtime = now - 900` with cached `D1`/`C1` `8/8` graduation and asserting `maybe_execute_graduated_d1_box` still executes `C1_BINARY_COMPLETE_SET`.

#### `R-04` — Correlated-Event Concentration Cap Computing `max($20, 28% * Book_Equity)` (`$27.41` = `57.7%` Liquid NAV!) + Bypass Gaps
- **Category:** `TECHNICAL_FIXABLE`
- **Exact Locations:** [riskless_protocol_v2_expansion.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/riskless_protocol_v2_expansion.py#L1799-L1807), [#L2025-L2026](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/riskless_protocol_v2_expansion.py#L2025-L2026), [#L2062-L2085](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/riskless_protocol_v2_expansion.py#L2062-L2085)
- **Enforcement Behavior:** Because `max_event_notional_usd` is unset (`0.0`) in `polymarket_strategy_and_risk.json`, `compute_dynamic_riskless_tier_caps` sets `max_evt_usd = max(20.0, eq * 0.28)` using book equity (`$97.89`) = **`$27.41`** (`57.7%` of `$47.52` mark-to-bid NAV!), exempts `FAST_GUN_S2_SLEEVES` and `D1` (`rem_s <= 960s`) at `L2025`, and ignores `AWAITING_ONCHAIN_SETTLEMENT` positions (`L2065, L2084`).
- **Economic Impact at `$47.38` Liquid:** Exposes up to **`$27.41` (`57.9%` of remaining cash)** to a single correlated UMA dispute—risking a repeat of the `$50.51` `KMIA` capital freeze!
- **Safe Remediation:** Compute `reconciled_nav_usd` discounting `disputed` positions to bid (`$47.52`), enforce `max_evt_usd = max(6.0, round(0.15 * reconciled_nav_usd, 2))` (`$7.13` today) on all UMA-disputable / single-leg events (`25%` = `$11.88` max only on atomic-mergeable/Chainlink 2-leg `C1`/`D1`), include `AWAITING_ONCHAIN_SETTLEMENT` until on-chain redemption completes, and remove the `L2025` bypass.
- **Verification Procedure:** Extend `test_canonical_event_keys_strip_unwresid_and_group_weather_stations` at `$47.38` cash + `$50.51` disputed `KMIA` to assert a `$15.00` new weather/UMA clip is capped/rejected at `$7.13` (`15%` of `$47.52` NAV), not `$27.41`.

#### `R-05` — Owner-Approval Scope Conjunction Bug & Permanent Non-Expiring `"*"` Wildcard Hazard
- **Category:** `TECHNICAL_FIXABLE`
- **Exact Locations:** [permissions.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L97-L123), [#L308-L313](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L308-L313), [#L360-L362](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L360-L362), [builder_and_deployer.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/builder_and_deployer.py#L419-L428)
- **Enforcement Behavior:** `inspect_config_envelope` (`L308-313`) requires **BOTH** `INCREASE_CAPITAL_EXPOSURE` AND `NEW_LIVE_TRADING_ACTIVATION` simultaneously even when only one applies; `inspect_candidate_diff` (`L360`) checks `CREDENTIAL_OR_PERMISSION_EXPANSION` instead; `builder_and_deployer.py` (`L420`) requires undocumented `LIVE_PRODUCTION_PROMOTION`; and `has_explicit_operator_approval` (`L109-123`) enforces **no `expires_at_utc` TTL** and **no one-shot consumption** on `"target_id": "*"` JSON files.
- **Economic Impact at `$47.38` Liquid:** Obstructs legitimate single-scope owner overrides while leaving stale `"target_id": "*"` files active indefinitely.
- **Safe Remediation:** Match each violation category to its exact scope, enforce mandatory `expires_at_utc` + `consumed_at_utc` single-use binding, and add human-only `paa_cli.py approve` / `promote-release` / `revoke-approval` commands (blocked when `PAA_SIGNING_DISABLED == "1"` or `PAA_WORKER_ROLE` is set).
- **Verification Procedure:** Unit test verifying single-scope `NEW_LIVE_TRADING_ACTIVATION` passes sleeve unpausing, fails risk-floor lowering, expires after `expires_at_utc`, and rejects creation when `PAA_SIGNING_DISABLED=1`.

#### `R-06` — `active_positions_count > 0` Blocking Safe Code Promotions During Multi-Day UMA Disputes
- **Category:** `TECHNICAL_FIXABLE`
- **Exact Locations:** [builder_and_deployer.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/builder_and_deployer.py#L663-L675), [audit_losing_trades.py](file:///C:/Users/Anton/source/repos/Dominus/audit_losing_trades.py#L423-L429)
- **Enforcement Behavior:** Checks raw `open_cnt > 0` without calling `_is_restart_safe_frozen_uma_lock` (unlike [paa_flat_harvester_redeploy_once.py](file:///C:/Users/Anton/source/repos/Dominus/scripts/paa_flat_harvester_redeploy_once.py#L36-L70)), deferring owner-approved releases for days while the 4 `KMIA` UMA disputed positions (`active_positions_count == 4`) sit passively awaiting DVM resolution.
- **Economic Impact at `$47.38` Liquid:** Delays deployment of latency/arbitrage improvements by 48–120+ hours whenever any UMA dispute is pending.
- **Safe Remediation:** Share `_safe_to_restart(state_dict, now_ts)` across `builder_and_deployer.py`, `audit_losing_trades.py`, and `paa_flat_harvester_redeploy_once.py` (blocking restart ONLY when non-frozen positions or `pending_entry_intents` exist).
- **Verification Procedure:** Unit test with 4 post-expiry `disputed=True` `KMIA` positions (`pending_entry_intents={}`) asserting `DeploymentController.release_candidate` does not return `DEFERRED_OPEN_POSITIONS`.

#### `R-07` — `polymarket_all_in_one.py` `< 1,000,000`-Byte Canary Ceiling (`91.1%` Full) & Missing Non-`.py` Binary/Data Diff Guard
- **Category:** `TECHNICAL_FIXABLE`
- **Exact Locations:** [`DeploymentController._run_release_canary_probe`](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/builder_and_deployer.py#L326-L335), [PAA_DEPLOYMENT_POLICY.md](file:///C:/Users/Anton/source/repos/Dominus/config/policies/PAA_DEPLOYMENT_POLICY.md#L11)
- **Enforcement Behavior:** `_run_release_canary_probe` checks **only** `if pyf.name == "polymarket_all_in_one.py"`, returning `BUNDLE_SIZE_CEILING_EXCEEDED:{len(raw_aio)}_bytes` when `len(raw_aio) >= 1,000,000` (`L328-333`) and `BUNDLE_CRLF_DETECTED:polymarket_all_in_one.py` on `b"\r\n"` (`L334-335`). Modifying modular files (`riskless_protocol_v2_expansion.py` + `polymarket_live_harvester.py`) does **not** sum those files or fail this check; however, root `polymarket_all_in_one.py` is already **`910,713` bytes (`89,287` bytes remaining headroom)**, while non-`.py` artifacts (`.sqlite3`, `.jsonl`, `.parquet`) have no size/extension block in `inspect_candidate_diff`.
- **Economic Impact at `$47.38` Liquid:** `$0.00` immediate block on modular `src/` commits; latent release-failure cliff if `polymarket_all_in_one.py` grows by `>= 89.3 KB` and unprotected against accidental `.sqlite3`/`.jsonl` staging bloat.
- **Safe Remediation:** Freeze/deprecate feature additions into `polymarket_all_in_one.py` in favor of modular `src/polymarket_research/*` imports (keeping its `< 1,000,000 B` + LF guard intact) and add a binary/data-extension block (`.sqlite3`, `.jsonl`, `.parquet`, `.pkl`) in `PermissionGate.inspect_candidate_diff`.
- **Verification Procedure:** Unit test verifying `polymarket_all_in_one.py` at `1,000,000` bytes triggers `BUNDLE_SIZE_CEILING_EXCEEDED:1000000_bytes`, modular `src/` edits pass `_run_release_canary_probe`, and `.sqlite3`/`.jsonl` candidate paths are rejected.

#### `R-08` — Emergency Stop Missing Out-of-Band CLOB Order Cancellation & Asymmetric `resume`
- **Category:** `TECHNICAL_FIXABLE`
- **Exact Locations:** [paa_cli.py](file:///C:/Users/Anton/source/repos/Dominus/scripts/paa_cli.py#L390-L449), [paa_emergency_stop.sh](file:///C:/Users/Anton/source/repos/Dominus/scripts/paa_emergency_stop.sh#L1-L27)
- **Enforcement Behavior:** `paa_cli.py emergency-stop --include-trading` neither writes `data/polymarket/KILL_SWITCH` nor executes an independent `cancel_all_orders()` if the harvester process was already dead/hung, omits `polymarket-cross-venue-shadow.service`, and `paa_cli.py resume` silently leaves trading services down without warning.
- **Economic Impact at `$47.38` Liquid:** Uncancelled resting Maker orders could fill unmonitored during an emergency halt (`up to $47.38` cash exposure).
- **Safe Remediation:** Write `KILL_SWITCH`, invoke standalone `cancel_all_orders()` verification, stop all shadow/recorder/trading units cleanly on `--include-trading`, and add explicit status + `--include-trading` support to `paa_cli.py resume`.
- **Verification Procedure:** Dry-run CLI test verifying `emergency-stop --include-trading` creates `PAA_MASTER_STOP` + `KILL_SWITCH` and invokes `cancel_all_orders()`.

#### `R-09` — Capital-Velocity Hurdle Unconditionally Exempting Unmergeable 24h `COMPLETE_SET` & Using `$97.89` Book Equity
- **Category:** `TECHNICAL_FIXABLE`
- **Exact Locations:** [holistic_strategy_governance.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/holistic_strategy_governance.py#L812-L820), [polymarket_live_harvester.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L5669-L5678)
- **Enforcement Behavior:** `passes_capital_velocity_hurdle` (`L812`) returns `True` unconditionally for `COMPLETE_SET` even when on-chain merge is unavailable (`_merge_wallet_ok == False` on `TTE <= 24h`), and callers pass `$97.89` book equity instead of `$47.52` deployable NAV (relaxing lockup from `8h/15 bps_hr` toward `36h/8 bps_hr` at `$98`).
- **Economic Impact at `$47.38` Liquid:** Can tie up `$15–$25` (`32%–53%` of liquid cash) for 24 hours at `< 2 bps/hr`, starving 15m/1h/2h `D1` & `BOND1` opportunities (`15–60 bps/hr`).
- **Safe Remediation:** Exempt `COMPLETE_SET` / `NEGRISK_CONVERT` from `eff_hrs` ONLY when `merge_available=True` (`eff_hrs = 0.10h`), and pass undisputed deployable NAV (`$47.52`) as `collat_usd`.
- **Verification Procedure:** Unit test calling `passes_capital_velocity_hurdle(box_type="COMPLETE_SET", rem_tte_sec=72000, box_cost_net=0.995, merge_available=False, collat_usd=47.38)` and asserting `(False, "LOW_CAPITAL_VELOCITY_LONG_TTE...")`.

#### `R-10` — Stale Prorated VM Cost (`$0.0730/hr` = `$52.56/mo` vs. Actual `$0.0343/hr` = `$24.67/mo`)
- **Category:** `TECHNICAL_FIXABLE`
- **Exact Locations:** [paa_autonomy_config.json](file:///C:/Users/Anton/source/repos/Dominus/config/paa_autonomy_config.json#L67), [budget.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/budget.py#L116)
- **Enforcement Behavior:** Deducts `$1.752/day` instead of `$0.822/day` in `BudgetManager.get_usage_summary` and `PAAAccountant` net-after-infra PnL reports.
- **Economic Impact at `$47.38` Liquid:** Overstates fixed infra drag by **`+$0.93/day` (`+$27.89/mo`)**, making net-profitable days (`+$1.10/day` trading = `+$0.28/day` true net) appear net-negative (`-$0.65/day` reported)!
- **Safe Remediation:** Update `prorated_vm_hourly_cost_usd` to `0.0343` (`$24.67 / 720h`).
- **Verification Procedure:** Assert `BudgetManager.get_usage_summary()["daily_infra_vm_cost_usd"]` uses `0.0343 * hours_elapsed_today` (`~$0.8232/24h` instead of `$1.7520/24h`).

---

### Category 2: `LEGACY_UNNECESSARY` (4 Restrictions — Obsolete Flags & Eliminated Legacy Gates)

#### `R-11` — Contradictory `enable_ungraduated_v3_math_live: true` Flag in Strategy Config
- **Category:** `LEGACY_UNNECESSARY`
- **Exact Locations:** [polymarket_strategy_and_risk.json](file:///C:/Users/Anton/source/repos/Dominus/config/polymarket_strategy_and_risk.json#L188), [polymarket_live_harvester.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L5733)
- **Enforcement Behavior:** Remains `true` from pre-Nov-4 testing, currently masked only because `strict_pure_riskless_mode: true` blocks ungraduated sleeves earlier (`L5467`). If `strict_pure_riskless_mode` were ever toggled off, dozens of ungraduated v3 sleeves would silently go live!
- **Economic Impact:** Latent tail-risk landmine (`$0` benefit).
- **Safe Remediation:** Set `"enable_ungraduated_v3_math_live": false` in `config/polymarket_strategy_and_risk.json`.
- **Verification Procedure:** Verify JSON config value is `false` and `pytest` graduation suite passes.

#### `R-12` — Dual Risk Config File Drift (`config/polymarket_risk_config.json` vs. `config/polymarket_strategy_and_risk.json`)
- **Category:** `LEGACY_UNNECESSARY`
- **Exact Locations:** [polymarket_risk_config.json](file:///C:/Users/Anton/source/repos/Dominus/config/polymarket_risk_config.json#L1-L49), [polymarket_live_harvester.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L583) & [#L1070-L1080](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L1070-L1080)
- **Enforcement Behavior:** `polymarket_risk_config.json` still defines legacy v3 values (`min_equity_floor: 48.0`, `max_exposure: 24.0`, `seed_survival_equity_threshold: 88.0`) read via `RISK_CONFIG` whenever v5 governance overrides aren't active.
- **Economic Impact:** Config confusion & fallback inconsistency across scripts/tests.
- **Safe Remediation:** Derive `RISK_CONFIG` fallback values directly from `polymarket_strategy_and_risk.json` (`GLOBAL_GOVERNANCE_MANAGER.snapshot`) so a single source of truth governs all modes.
- **Verification Procedure:** Assert `CIRCUIT_BREAKER_EQUITY_FLOOR` and tier limits match `polymarket_strategy_and_risk.json` with zero divergence.

#### `R-13` — Stale `320 MB` / `180 MB` Cgroup Prose in `RestrictionRegistry` (`INT_ADMIN::RSS_180MB_CGROUP_MISMATCH`)
- **Category:** `LEGACY_UNNECESSARY`
- **Exact Locations:** [cross_venue_unblock_and_certification.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_unblock_and_certification.py#L1120-L1122) & [#L1517-L1530](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_unblock_and_certification.py#L1517-L1530)
- **Enforcement Behavior:** Emits `MemoryHigh=280M, MemoryMax=320M` in `restriction_registry.json` even though `polymarket-cross-venue-shadow.service:15-16` was upgraded to `MemoryHigh=450M, MemoryMax=512M`.
- **Economic Impact:** `$0.00` (telemetry accuracy cleanup).
- **Safe Remediation:** Sync description and gate keys to `512M`.
- **Verification Procedure:** Run `RestrictionRegistry.build_entries` and assert `512M` is reported accurately.

#### `R-14` — Five Previously Eliminated Stage G Internal Administrative Gates (Already Unlocked — Retain Unlocked State)
- **Category:** `LEGACY_UNNECESSARY` *(Historical — Already Eliminated)*
- **Exact Locations:** [cross_venue_unblock_and_certification.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_unblock_and_certification.py#L1471-L1545) (`PREDICT_FUN_DATA_LICENSE_ID`, `SX_BET_DATA_APPROVAL_ID` on public REST, `FORECASTEX_PUBLIC_PORTAL_AUTHORIZED`, `STX_ONTARIO` FI public Phoenix WS gate)
- **Enforcement Behavior:** `current_status = "ELIMINATED_UNLOCKED"`; none of these block REST, WS, or shadow research today.
- **Economic Impact:** `$0.00` (unlocked 6-venue shadow telemetry).
- **Safe Remediation:** Keep eliminated; never re-introduce imaginary internal data-license env flags.
- **Verification Procedure:** Covered by existing Stage G gate unit tests (`current_status == "ELIMINATED_UNLOCKED"`).

---

### Category 3: `RESOURCE_LIMITATION` (3 Restrictions — Physical Capital, Compute & Geography)

#### `R-15` — Liquid Capital Scale (`$47.38` Cash vs. `$50.51` Locked in `KMIA` UMA Dispute)
- **Category:** `RESOURCE_LIMITATION`
- **Exact Locations:** On-chain Polygon wallet / `live_harvester_state.json` (`$47.38` free `USDC.e`, `$50.51` in `markets 6707502 & 6707503`)
- **Enforcement Behavior:** Limits maximum concurrent Polymarket positions to `2–4` clips (`$8–$20` each), makes `$0.82/day` VM burn equal to `52%/month` hurdle on liquid cash (`25%/month` if `KMIA` recovers `$50.51`), and precludes splitting capital across multiple exchanges.
- **Economic Impact:** Primary ceiling on absolute `$/day` dollar PnL (`200 bps/day` on `$47.38` = `+$0.95/day` gross vs. `+$10.00/day` at `$500`).
- **Safe Remediation:** Maximize `bps/hr` velocity on `$47.38` (`D1`, mergeable `C1`, fast `<=2h` `BOND1`, `CLINCH_DEAD_SPLIT`), keep 100% of capital consolidated on Polygon `USDC.e` until `> $253–$500`, and await `KMIA` UMA resolution without touching the 4 open positions.
- **Verification Procedure:** Reconcile wallet `USDC.e` + active positions via `dominus_command_center.py --once`.

#### `R-16` — `quant-pipeline-finland` `2 vCPU / 4,096 MB RAM` Hardware Ceiling
- **Category:** `RESOURCE_LIMITATION`
- **Exact Locations:** [polymarket-alpha124-shadow.service](file:///C:/Users/Anton/source/repos/Dominus/systemd/polymarket-alpha124-shadow.service#L15-L20) (`MemoryMax=1550M`), [polymarket-cross-venue-shadow.service](file:///C:/Users/Anton/source/repos/Dominus/systemd/polymarket-cross-venue-shadow.service#L15-L19) (`MemoryMax=512M, CPUQuota=35%`)
- **Enforcement Behavior:** Constrains concurrent Python daemons (`live-harvester` + `alpha124-shadow` + `cross-venue-shadow` + 7 `recorder` services + `paa` timers) within `4 GB` RAM to keep VM cost at `~$24.67/mo`.
- **Economic Impact:** Upgrading VM would destroy net EV at `$47.38` cash; any unthrottled memory growth in shadow daemons causes swap/CPU contention on the live harvester.
- **Safe Remediation:** Keep `$24.67/mo` VM (`$0` infra spend increase), enforce streaming state hydration (`test_alpha124_streaming_hydrate_state_slims_historical_closed_records`), and consolidate duplicate recorder processes if memory pressure exceeds `80%`.
- **Verification Procedure:** `ssh kraken-finland "free -m && uptime"` verifying `available > 800 MB` and `0` OOM kills in `journalctl -k`.

#### `R-17` — `europe-north1-b` (Finland) Physical Speed-of-Light RTT to Polymarket CLOB (`eu-west-2` London / Cloudflare)
- **Category:** `RESOURCE_LIMITATION`
- **Exact Locations:** [honest_purged_wfo_optimizer.py](file:///C:/Users/Anton/source/repos/Dominus/scripts/honest_purged_wfo_optimizer.py#L8) (`~35–45ms` network RTT floor + TLS/CLOB matching engine latency; `~120–424ms` full HTTP POST round-trip without warm keep-alive)
- **Enforcement Behavior:** Physical fiber distance between Hamina, Finland (`FI`) and London (`eu-west-2`, where Polymarket CLOB servers run; note UK *server IPs* are geoblocked on `POST /order` per `bad_server_region` in [cross_venue_shadow_deployment_gates.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_shadow_deployment_gates.py#L989), so Amsterdam `europe-west4` or Frankfurt `europe-west3` is the closest EU non-UK region!).
- **Economic Impact:** Loses ultra-contested `<25ms` HFT races against `eu-west-1` (Dublin) / `eu-central-1` (Frankfurt) Rust bots, while still winning `BOND1` FIFO Maker queue, `D1` quiet-book / 4h dominance, `C1` complete sets, and `CLINCH_DEAD_SPLIT` locks.
- **Safe Remediation:** Zero-cost Python hot-path optimizations first (persistent HTTP/2 or HTTP/1.1 keep-alive connection pool + pre-warmed EIP-712 signer + async state journaling); evaluate `$0`-delta GCP region move (`europe-north1` Finland -> `europe-west4` Netherlands, `~7–9ms` RTT to London vs `~32ms` from Finland) ONLY during a flat-book maintenance window once NAV `>= $250`.
- **Verification Procedure:** Measure `clob_post_p50_ms` / `p90_ms` in `dominus_command_center.py` (`L2345-2346`).

---

### Category 4: `AUTHENTICATION_CONFIGURATION` (4 Restrictions — Optional Credentials / Sessions Not Yet Provisioned)

#### `R-18` — `SX_BET_API_KEY` Unset in `/etc/polymarket-shadow.env` (Blocks SX Bet L2 Snapshot & Centrifugo WS Only)
- **Category:** `AUTHENTICATION_CONFIGURATION`
- **Exact Locations:** [cross_venue_shadow_deployment_gates.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_shadow_deployment_gates.py#L1399-L1463), [cross_venue_unblock_and_certification.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_unblock_and_certification.py#L1548-L1561)
- **Enforcement Behavior:** `api.sx.bet` returns `HTTP 401 BAD_AUTH` without `x-sx-api-key` on `/orderbook-v3/snapshot/market` and `/user/realtime-token-v3/api-key` (`wss://realtime.sx.bet`). Keyless public REST (`365+` active markets via `/summary-v3/*`, `/markets/active`) is **already live**.
- **Economic Impact at `$47.38` Liquid:** `$0.00` immediate live impact (SX Bet trading is `CA-ON` restricted); limits SX Bet shadow depth simulation to top-of-book summary odds instead of full L2 depth.
- **Safe Remediation:** Request read-only `SX_BET_API_KEY` via [KYB_AND_API_ONBOARDING_DOSSIERS.md](file:///C:/Users/Anton/source/repos/Dominus/docs/KYB_AND_API_ONBOARDING_DOSSIERS.md#L50-L66) and hot-reload via `deploy_cross_venue_shadow.py --provision-secret SX_BET_API_KEY`.
- **Verification Procedure:** Verify `shadow_service_health.json` transitions `sx_bet.readonly_api_state` to `READONLY_API_AUTHORIZED`.

#### `R-19` — `STX_API_KEY_ID` + `STX_ED25519_KEY_FILE` (or `STX_APPS_DATA_TOKEN`) Unset (Blocks STX Signed REST `/api/v1/markets` Only)
- **Category:** `AUTHENTICATION_CONFIGURATION`
- **Exact Locations:** [cross_venue_shadow_deployment_gates.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_shadow_deployment_gates.py#L820-L849), [cross_venue_unblock_and_certification.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_unblock_and_certification.py#L1593-L1606)
- **Enforcement Behavior:** `api.on.stxapp.ca/api/v1/markets` returns `HTTP 403` without Ed25519 `X-STX-ACCESS-*` or OAuth Bearer headers. Unsigned public Phoenix WebSocket (`wss://api.on.stxapp.ca/socket/websocket?vsn=2.0.0`) is **already live**.
- **Economic Impact at `$47.38` Liquid:** `$0.00` immediate live impact; Phoenix WS already streams live STX L2 books.
- **Safe Remediation:** Optional self-service Ed25519 Read-Only keypair generation on `CA-ON` host ([KYB_AND_API_ONBOARDING_DOSSIERS.md](file:///C:/Users/Anton/source/repos/Dominus/docs/KYB_AND_API_ONBOARDING_DOSSIERS.md#L23-L33)).
- **Verification Procedure:** Check `stx_ontario.scope_permissions["AUTHENTICATED_READONLY"] == "AUTHORIZED_LIVE"`.

#### `R-20` — `IBKR_GATEWAY_URL` Local Client Portal Session Not Running (Blocks Realtime ForecastEx IBKR CPAPI WS Only)
- **Category:** `AUTHENTICATION_CONFIGURATION`
- **Exact Locations:** [cross_venue_shadow_deployment_gates.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_shadow_deployment_gates.py#L887-L954), [cross_venue_unblock_and_certification.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_unblock_and_certification.py#L1578-L1591)
- **Enforcement Behavior:** Public CFTC DCM CSV feed (`forecastex.com/api/download`, ~600 contracts) is **active**; streaming L1 `smd+{conid}` quotes require an authenticated local IBKR Client Portal Gateway (`IBKR_GATEWAY_URL`) with `FORECASTX` `OPT` permissions on the `CA-ON` host.
- **Economic Impact at `$47.38` Liquid:** `$0.00` at `$47.38` cash (capital too small to split across IBKR CAD/USD brokerage + Polygon `USDC.e`); unlocks regulated `CA-ON`-legal second-venue trading once NAV `>= $500`.
- **Safe Remediation:** Authenticate IBKR Client Portal Gateway on `CA-ON` workstation when bankroll approaches `$250–$500` ([KYB_AND_API_ONBOARDING_DOSSIERS.md](file:///C:/Users/Anton/source/repos/Dominus/docs/KYB_AND_API_ONBOARDING_DOSSIERS.md#L38-L44)).
- **Verification Procedure:** `GET https://localhost:5000/v1/api/iserver/auth/status` returns `authenticated: true`.

#### `R-21` — `POLY_BUILDER_API_KEY` / Relayer Gasless Merge Configuration Check on Safe (`signature_type == 3`) Wallets
- **Category:** `AUTHENTICATION_CONFIGURATION`
- **Exact Locations:** [polymarket_live_harvester.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L5661-L5678) & [#L2590-L2600](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L2590-L2600)
- **Enforcement Behavior:** For `signature_type == 3` proxy/Safe wallets, gasless batch CTF `mergePositions` / `splitPosition` requires `POLY_BUILDER_API_KEY` (`BUILDER_API_KEY`) or explicit `PM_ENABLE_ONCHAIN_MERGE=1` with `POL` gas balance. Without instant merge, `C1_BINARY_COMPLETE_SET` boxes must wait until market expiry (`TTE`) to recycle cash instead of recycling in `<15s`!
- **Economic Impact at `$47.38` Liquid:** **High velocity multiplier!** Instant CTF merge turns a `12h` `60 bps` `C1` complete set (`5 bps/hr`) into a `15-second` cash recycle (`>1,000 bps/hr`!), multiplying `$47.38` daily turnover without increasing risk!
- **Safe Remediation:** Verify `PM_ENABLE_ONCHAIN_MERGE=1` (with `$1–$2` native `POL` gas) or `POLY_BUILDER_API_KEY` relayer credentials on `kraken-finland`.
- **Verification Procedure:** Check `_merge_wallet_ok is True` in read-only harvester startup diagnostics.

---

### Category 5: `PROVIDER_CONTRACTUAL` (4 Restrictions — Exchange Rules, Fees & Matching Mechanics)

#### `R-22` — Polymarket CLOB Minimum Order Size (`5` Shares & `$1.00` Minimum Notional Per Leg)
- **Category:** `PROVIDER_CONTRACTUAL`
- **Exact Locations:** [riskless_protocol_v2_expansion.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/riskless_protocol_v2_expansion.py#L6436-L6442), [stage_c_zero_loss_velocity.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/stage_c_zero_loss_velocity.py#L770-L795)
- **Enforcement Behavior:** `clob.polymarket.com` rejects limit/market orders below the market's `minimum_order_size` (typically `5` shares) or `< $1.00` leg notional (`HTTP 400`).
- **Economic Impact at `$47.38` Liquid:** Prevents micro-sizing `< $5.00` complete-set clips and forces multi-leg bundles with a `$0.08` tail leg to buy `>= 13` shares (`>= $13` total basket), increasing per-clip concentration at `$47.38` cash.
- **Safe Remediation:** Cannot change exchange rule; prioritize 2-leg `D1`/`C1` and `1`-leg `BOND1` where `5–10` shares cost `$4.95–$9.95` (`10%–21%` of liquid cash).
- **Verification Procedure:** Enforced pre-flight (`sh >= 5.0` and `sh * px >= 1.00`) to avoid `HTTP 400` round-trip waste.

#### `R-23` — Polymarket Taker Fee Curves (`crypto_fees_v2` up to `7% * p * (1-p)`, `sports_fees_v2`, `weather_fees_v2`)
- **Category:** `PROVIDER_CONTRACTUAL`
- **Exact Locations:** [riskless_protocol_v2_expansion.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/riskless_protocol_v2_expansion.py#L1988-L2002), [polymarket_live_harvester.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L888)
- **Enforcement Behavior:** Polymarket charges dynamic parabolic taker fees on 15m/1h crypto (`~1.75c/sh` at `$0.50` = `350 bps` per leg = **`700 bps` on a 2-leg taker box!**), eliminating sub-7% gross spreads on fee-bearing crypto markets while keeping `Maker` (`0%` fee + rebate) and `zero_fees` markets (`0 bps`) fee-free.
- **Economic Impact at `$47.38` Liquid:** Eliminates `~85%` of naive gross Taker spreads on fee-bearing 15m crypto; shifts highest net EV to `0%`-fee markets (`C1` `zero_fees`, `BOND1` `0%` Maker, `CLINCH_DEAD_SPLIT` `0%` split/merge) and deep `>750 bps` shock dislocations.
- **Safe Remediation:** Always deduct `compute_exact_taker_fee_per_share` pre-trade (already enforced) and favor `0%`-fee Maker / `zero_fees` markets.
- **Verification Procedure:** Verified by penny-exact fee reconciliation in `PAAAccountant`.

#### `R-24` — Non-Atomic Multi-Market CLOB Order Execution on Polymarket
- **Category:** `PROVIDER_CONTRACTUAL`
- **Exact Locations:** [polymarket_live_harvester.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L5598-L5613), [riskless_protocol_v2_expansion.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/riskless_protocol_v2_expansion.py#L6376-L6540)
- **Enforcement Behavior:** Polymarket CLOB processes separate `condition_id` orders independently; Leg A can fill while Leg B races/rejects, creating an unhedged residual (`UNWRESID`). (Only single-condition `splitPosition`/`mergePositions` and NegRisk `convertPositions` on-chain are atomic.)
- **Economic Impact at `$47.38` Liquid:** Major source of historical legging drag on `>= 3`-leg sequential baskets.
- **Safe Remediation:** Quarantine sequential `>= 3`-leg CLOB baskets below `$500` NAV (`R-40`), walk deeper L2 book levels with cushion on 2-leg `D1`/`C1`, and use atomic on-chain `splitPosition`/`convertPositions` (`CLINCH_DEAD_SPLIT`, `NR_M1`, `NR2`) wherever available.
- **Verification Procedure:** Monitor `ASSET_LEGGING_COOLDOWN` and `_UNWRESID_` incidence (`target = 0` on allowlisted sleeves).

#### `R-25` — Provider Public & Authenticated API Rate Limits (`Polymarket`, `SX Bet` `500/60s`, `Predict.fun`, `Limitless`)
- **Category:** `PROVIDER_CONTRACTUAL`
- **Exact Locations:** [paa_autonomy_config.json](file:///C:/Users/Anton/source/repos/Dominus/config/paa_autonomy_config.json#L72-L77), [cross_venue_shadow_deployment_gates.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_shadow_deployment_gates.py#L1397)
- **Enforcement Behavior:** External Cloudflare / API gateways return `HTTP 429` or temporary IP bans if REST polling exceeds published ceilings.
- **Economic Impact:** Negligible when WebSocket push feeds (`ws-subscriptions-clob.polymarket.com`, `ws.limitless.exchange`, `ws.predict.fun`, `api.on.stxapp.ca`) are primary and REST is used only for catalog pagination / top-N hydration.
- **Safe Remediation:** Prefer WebSocket event streams over REST polling; keep `BudgetManager.check_api_rate_limit` exponential backoff active.
- **Verification Procedure:** Verify `api_error_rate_pct <= 2.0%` in `VenueCertificationTracker` (`certification_report.json`).

---

### Category 6: `JURISDICTIONAL` (5 Restrictions — Statutory & Geoblocked Live Order Placement Boundaries)

> **STRICT COMPLIANCE INVARIANT:** None of `R-26`..`R-30` may ever be bypassed via proxy/VPN spoofing. All 5 are **strictly isolated to `LIVE_ORDER_EXECUTION` / `ACCOUNT_PRIVATE`** and block **zero** authorized public read-only market-data feeds.

#### `R-26` — Polymarket International `CA-ON` Geoblock & April 2025 OSC Settlement (`POST /order`)
- **Category:** `JURISDICTIONAL`
- **Exact Locations:** [cross_venue_shadow_deployment_gates.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_shadow_deployment_gates.py#L988-L1068), [KYB_AND_API_ONBOARDING_DOSSIERS.md](file:///C:/Users/Anton/source/repos/Dominus/docs/KYB_AND_API_ONBOARDING_DOSSIERS.md#L11)
- **Enforcement Behavior:** `CA-ON` operator location and `US`/`UK` server regions (`bad_server_region = {"GB","UK","US","USA"}`) are restricted from `POST /order` unless operated by an independently eligible non-restricted entity (`blocked: false`). Keyless public `gamma-api` + CLOB L2 `/book` & WS remain `PUBLIC_DATA_AUTHORIZED`.
- **Economic Impact:** Governs legal entity/location structure for live Polymarket trading; `0` impact on public L2 data.
- **Safe Remediation:** Operate strictly within eligible jurisdiction/entity rules (`R-31`); never deploy to `US`/`UK` cloud regions.
- **Verification Procedure:** `evaluate_venue_authorization("polymarket")` unit & `--enforce-venue-auth` startup gate.

#### `R-27` — Limitless Exchange `CA-ON` / `CA-AB` / `US` Trading Prohibition (Street Chow Inc. ToS §1)
- **Category:** `JURISDICTIONAL`
- **Exact Locations:** [cross_venue_shadow_deployment_gates.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_shadow_deployment_gates.py#L1102-L1209)
- **Enforcement Behavior:** Street Chow Inc. ToS §1 bars `TRADING` & `ACCOUNT_PRIVATE` in `CA-ON`, `CA-AB`, `US`, `ROC`, while keyless public REST (`/markets/active`, `/orderbook`) and Socket.IO `/markets` WS remain `AUTHORIZED_LIVE`.
- **Economic Impact at `$47.38` Liquid:** `$0.00` at `$47.38` (insufficient capital for multi-venue split); blocks live Limitless leg execution from `CA-ON` without an eligible non-restricted corporate entity (`R-31`).
- **Safe Remediation:** Keep Limitless in keyless read-only Stage G `168h` shadow certification; evaluate legal corporate entity (`R-31`) only if 168h shadow proves `> $150/mo` net post-delay cross-venue edge at `$500+` NAV.
- **Verification Procedure:** Confirm `limitless.trading_state == "RESTRICTED"` and `public_data_state == "PUBLIC_DATA_AUTHORIZED"`.

#### `R-28` — Predict.fun `CA-ON` `Technology Features` / BNB Chain Wallet & Order Prohibition (PDF Labs ToS §1)
- **Category:** `JURISDICTIONAL`
- **Exact Locations:** [cross_venue_shadow_deployment_gates.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_shadow_deployment_gates.py#L1243-L1360)
- **Enforcement Behavior:** PDF Labs Limited ToS §1 permits `Content Features` (Mainnet REST + WS market data via `PREDICT_FUN_API_KEY`, currently **ACTIVE**) in Restricted Jurisdictions (`CA-ON`), while prohibiting `Technology Features` (`POST /v1/auth` wallet JWT & `POST /v1/orders`).
- **Economic Impact at `$47.38` Liquid:** `$0.00` at `$47.38` cash; blocks live Predict.fun order execution under `CA-ON`.
- **Safe Remediation:** Keep Mainnet `Content Features` shadow feed running (`0` wallet keys); require eligible non-restricted entity (`R-31`) before any future live execution.
- **Verification Procedure:** Confirm `predict_fun.status_code == "AUTHORIZED_MAINNET_CONTENT_DATA_TRADING_RESTRICTED"`.

#### `R-29` — SX Bet `CA-ON` Wagering & Account Prohibition (`sx.bet` Terms)
- **Category:** `JURISDICTIONAL`
- **Exact Locations:** [cross_venue_shadow_deployment_gates.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_shadow_deployment_gates.py#L1365-L1474)
- **Enforcement Behavior:** Prohibits `ACCOUNT_PRIVATE` & `TRADING` (`POST /orders-v3`) for `CA-ON` residents and blocks `US`/`UK` server IPs; keyless OBv3 public REST remains `AUTHORIZED_LIVE` from `FI`.
- **Economic Impact at `$47.38` Liquid:** `$0.00` at `$47.38` cash; blocks live SX Bet leg execution under `CA-ON`.
- **Safe Remediation:** Keep read-only OBv3 shadow feed active; require eligible non-restricted entity (`R-31`) for future trading.
- **Verification Procedure:** Confirm `sx_bet.trading_state == "RESTRICTED"` under `CA-ON`.

#### `R-30` — STX Ontario (`AGCO` / `iGaming Ontario`) Physical Ontario Geolocation Requirement for Personal Trading
- **Category:** `JURISDICTIONAL`
- **Exact Locations:** [cross_venue_shadow_deployment_gates.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_shadow_deployment_gates.py#L760-L849), [KYB_AND_API_ONBOARDING_DOSSIERS.md](file:///C:/Users/Anton/source/repos/Dominus/docs/KYB_AND_API_ONBOARDING_DOSSIERS.md#L16)
- **Enforcement Behavior:** Personal STX Ontario accounts (`on.stxapp.ca`) are **legally eligible for `CA-ON` residents**, **BUT** iGaming Ontario (`iGO`) mandates that authenticated personal account/order calls originate physically inside Ontario (`CA-ON`), NOT from the Finland (`FI`) cloud VM (`srv_reg == "FI"` is restricted for Path A trading, though unsigned public Phoenix WS is accessible).
- **Economic Impact at `$47.38` Liquid:** `$0.00` at `$47.38` cash; at `$500+` NAV, STX Ontario + ForecastEx/IBKR Canada are the **two regulated venues legally tradeable directly from `CA-ON` without offshore entity structuring**!
- **Safe Remediation:** Keep STX Phoenix WS streaming in Stage G shadow; when NAV `>= $500` and `168h` shadow proves net positive CAD/USD arb edge, execute STX Ontario / IBKR Canada legs directly from a `CA-ON` workstation/VPS (never proxied through `FI`).
- **Verification Procedure:** Verify `evaluate_venue_authorization("stx_ontario", operator_jurisdiction="CA-ON", server_region="FI").trading_state == "RESTRICTED"`.

---

### Category 7: `KYC_KYB` (2 Restrictions — Entity & Institutional Partner Onboarding)

#### `R-31` — Non-Restricted Corporate Entity Incorporation & Institutional KYB (`DOMINUS_KYB_REFERENCE_ID`)
- **Category:** `KYC_KYB`
- **Exact Locations:** [cross_venue_shadow_deployment_gates.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_shadow_deployment_gates.py#L990-L1007) & [#L1115-L1126](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_shadow_deployment_gates.py#L1115-L1126)
- **Enforcement Behavior:** Required to legally onboard institutional trading accounts on offshore prediction venues (`Polymarket`, `Limitless`, `Predict.fun`, `SX Bet`) outside `CA-ON` retail restrictions.
- **Economic Impact at `$47.38` Liquid:** Incorporating/maintaining an offshore entity costs `$1,500–$5,000+/yr`, which is **strictly negative EV (`-3,000%+` ROI)** at `$47.38` or `$500` NAV, and only becomes positive-EV above **`$10,000–$25,000+` NAV**!
- **Safe Remediation:** **Defer corporate KYB outlay until NAV `>= $10,000`**; at `$500–$5,000` NAV, prioritize `CA-ON`-eligible regulated venues (`ForecastEx / IBKR Canada` + `STX Ontario` direct in `CA-ON`).
- **Verification Procedure:** Track `168h` shadow `execution_adjusted_post_delay_pnl_usd` in `certification_report.json` before spending `$1` on entity formation.

#### `R-32` — STX Institutional Partner `Data` Track Approval (`apps.stxapp.io` `STX_APPS_DATA_TOKEN`)
- **Category:** `KYC_KYB`
- **Exact Locations:** [KYB_AND_API_ONBOARDING_DOSSIERS.md](file:///C:/Users/Anton/source/repos/Dominus/docs/KYB_AND_API_ONBOARDING_DOSSIERS.md#L34-L37)
- **Enforcement Behavior:** Server-to-server cloud REST access from outside Ontario (`FI`) to `api.on.stxapp.ca/api/v1/*` requires institutional partner approval (`STX_APPS_DATA_TOKEN`), though unsigned Phoenix WS already streams live public L2 books without it.
- **Economic Impact at `$47.38` Liquid:** `$0.00` (Phoenix WS already provides live STX market + L2 book telemetry).
- **Safe Remediation:** Optional zero-cost partner inquiry at `https://apps.stxapp.io` if REST historical/catalog metadata from `FI` is desired later.
- **Verification Procedure:** Optional `STX_APPS_DATA_TOKEN` check in `validate_shadow_env_dict`.

---

### Category 8: `ESSENTIAL_SAFETY` (6 Restrictions — Permanent Non-Overridable Safeguards)

#### `R-33` — Anti-Self-Approval, Credential Access & Wallet-Transfer Injection Hard Block
- **Category:** `ESSENTIAL_SAFETY`
- **Exact Locations:** [permissions.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L161-L170) & [#L332-L359](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L332-L359), [paa_autonomy_config.json](file:///C:/Users/Anton/source/repos/Dominus/config/paa_autonomy_config.json#L116-L122)
- **Enforcement Behavior:** Unconditionally rejects any candidate diff touching `data/polymarket/paa/approvals` (`SELF_APPROVAL_TAMPERING_FORBIDDEN`), `.env`/`.key`/`.pem` files, or introducing `self.forbidden_patterns` (`POLYGON_PRIVATE_KEY`, `HYPERLIQUID_PRIVATE_KEY`, `POLY_BUILDER_SECRET`, `safeTransferFrom(`, `eth_sendRawTransaction` -> `FORBIDDEN_CREDENTIAL_OR_TRANSFER_PATTERN`) in added diff lines—never overridable by any approval scope (`L354-359`).
- **Economic Impact:** `$0.00` opportunity cost; prevents `100%` principal theft/tampering.
- **Safe Remediation:** **Retain permanently (`0` weakening permitted); optionally append `MNEMONIC`, `eth_sendTransaction`, and `withdraw(` to `forbidden_diff_patterns`.**
- **Verification Procedure:** `pytest` security assertions on `PermissionGate.inspect_candidate_diff`.

#### `R-34` — Subprocess Secret Stripping & Detached Git Worktree Sandboxing
- **Category:** `ESSENTIAL_SAFETY`
- **Exact Locations:** [permissions.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L43-L94), [builder_and_deployer.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/builder_and_deployer.py#L101-L225)
- **Enforcement Behavior:** Strips `SENSITIVE_SIGNING_ENV_KEYS` (`L43-52`) plus any `*PRIVATE_KEY*`/`*SECRET*`/`*PASSPHRASE*` env vars and sets `PAA_WORKER_ROLE` + `PAA_SIGNING_DISABLED="1"` before invoking headless `agy` workers inside detached Git worktrees.
- **Economic Impact:** `$0.00` opportunity cost.
- **Safe Remediation:** **Retain permanently.**
- **Verification Procedure:** Assert `build_isolated_worker_env` removes `POLYGON_PRIVATE_KEY`, `POLY_BUILDER_SECRET`, `MNEMONIC`, and sets `PAA_SIGNING_DISABLED == "1"`.

#### `R-35` — `<UNTRUSTED_DATA_ONLY>` Prompt-Injection Sanitizer & Independent Test/Canary Verifier
- **Category:** `ESSENTIAL_SAFETY`
- **Exact Locations:** [zero_trust.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/zero_trust.py#L38-L82) & [#L593-L774](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/zero_trust.py#L593-L774)
- **Enforcement Behavior:** Neutralizes adversarial prompt text in external market feeds and runs independent `py_compile` + `pytest` + canary import checks outside the worker's control.
- **Economic Impact:** `$0.00` opportunity cost; prevents broken deployments and prompt hijack.
- **Safe Remediation:** **Retain permanently.**
- **Verification Procedure:** `ZeroTrustVerifier` unit tests.

#### `R-36` — Cross-Venue Double-Zero 5-Gate Settlement Equivalence Verifier (`CrossVenueRuleVerifier`)
- **Category:** `ESSENTIAL_SAFETY`
- **Exact Locations:** [cross_venue_shadow_deployment_gates.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_shadow_deployment_gates.py#L1852-L2053), [test_qa_boost_audit_remediation.py](file:///C:/Users/Anton/source/repos/Dominus/tests/test_qa_boost_audit_remediation.py#L249-L310)
- **Enforcement Behavior:** Rejects any cross-venue pair with mismatched oracle family, inverted `ABOVE`/`BELOW` strike direction, negative strike corridor (`YES > K_high` + `NO < K_low`), mismatched overtime/tie/walkover sports rules (`Gate 3 <= $0.48`), or settlement window divergence.
- **Economic Impact:** Prevents `-100%` Double-Zero settlement wipeouts where apparent `300 bps` cross-venue spreads are actually incompatible contracts!
- **Safe Remediation:** **Retain permanently.**
- **Verification Procedure:** `pytest tests/test_qa_boost_audit_remediation.py -k cross_venue_rule_verifier`.

#### `R-37` — Zero-Signing-Key Shadow `.env` Structural Validator (`0600` POSIX + Revoked Key SHA-256 Blocklist)
- **Category:** `ESSENTIAL_SAFETY`
- **Exact Locations:** [cross_venue_shadow_deployment_gates.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_shadow_deployment_gates.py#L1632-L1778)
- **Enforcement Behavior:** Hard-blocks private keys, mnemonics, `0x` 64-hex keys, PEM blocks, insecure `!= 0600` permissions, and revoked SHA-256 key digests in `/etc/polymarket-shadow.env` without ever echoing secret values.
- **Economic Impact:** `$0.00` opportunity cost.
- **Safe Remediation:** **Retain permanently.**
- **Verification Procedure:** `validate_shadow_env_dict` unit tests.

#### `R-38` — On-Chain Wallet-to-Ledger Accounting Integrity Safeguard (`> $1.50` Cash / `> 0.75` Share Discrepancy Halt)
- **Category:** `ESSENTIAL_SAFETY`
- **Exact Locations:** [accountant.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/accountant.py#L206-L365) (thresholds at `#L217-L218`), [paa_autonomy_config.json](file:///C:/Users/Anton/source/repos/Dominus/config/paa_autonomy_config.json#L84-L85), [PAA_RISK_POLICY.md](file:///C:/Users/Anton/source/repos/Dominus/config/policies/PAA_RISK_POLICY.md#L22-L23)
- **Enforcement Behavior:** Engages `ACCOUNTING_SAFEGUARD_ACTIVE.json` if authoritative on-chain `free_cash_pusd` vs. `live_bankroll` diverges by `> $1.50` (`accounting_discrepancy_threshold_usd = 1.50`) or any active ERC-1155 position balance diverges by `> 0.75` shares (`accounting_share_tolerance = 0.75`), auto-clearing once reconciled.
- **Economic Impact:** `$0.00` opportunity cost when healthy; halts runaway accounting/reservation bugs immediately.
- **Safe Remediation:** **Retain permanently.**
- **Verification Procedure:** `test_group3_residual_floor_valuation_accountant_isolation_lock_timeout_and_permissions`.

---

### Category 9: `JUSTIFIED_RISK_LIMIT` (5 Restrictions — Sound Risk & Capital-Efficiency Limits)

#### `R-39` — Unhedged Directional Suspension Below `$150` Undisputed NAV (`riskless_only_mode: true`)
- **Category:** `JUSTIFIED_RISK_LIMIT`
- **Exact Locations:** [polymarket_strategy_and_risk.json](file:///C:/Users/Anton/source/repos/Dominus/config/polymarket_strategy_and_risk.json#L20-L24)
- **Enforcement Behavior:** Keeps directional crypto Taker/Maker strategies in shadow until bankroll `>= $150.00` (and WFO `N >= 50, PF >= 1.45, PBO <= 0.20`), dedicating 100% of `$47.38` cash to zero-loss arbitrage.
- **Economic Impact at `$47.38` Liquid:** Positive risk-adjusted survival EV: eliminates ~`28%` 50-trade drawdown tail while `$8` minimum directional lots exceed optimal Half-Kelly fraction (`< $5.00`) at `$47.38` cash!
- **Safe Remediation:** **Retain** until **undisputed reconciled NAV** `>= $150.00` + shadow WFO pass + owner approval.
- **Verification Procedure:** Confirm `directional.riskless_only_mode == true` and Fractional Kelly sizing test returns `0.0` at `$47.38` when edge `< Half-Kelly lot floor`.

#### `R-40` — Sequential `>= 3`-Leg `MULTI_LEG_BUNDLE` Quarantine Below `$500` Reconciled NAV
- **Category:** `JUSTIFIED_RISK_LIMIT`
- **Exact Locations:** [stage_c_zero_loss_velocity.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/stage_c_zero_loss_velocity.py#L120-L151) & [#L258-L261](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/stage_c_zero_loss_velocity.py#L258-L261)
- **Enforcement Behavior:** Blocks non-atomic `3..12`-leg sequential CLOB FOK/FAK baskets on live production while permitting `1`-leg `NR_M1`, `2`-leg `NR2` / `D1` / `C1`, and atomic `CLINCH_DEAD_SPLIT_LOCK`.
- **Economic Impact at `$47.38` Liquid:** **Saves `+$10` to `+$35/month`** in avoided `UNWRESID` partial-fill unwind losses!
- **Safe Remediation:** **Retain** and align `nr0_dynamic_unlock_equity_usd` default from `$150.0` -> **`$500.0`** reconciled NAV (`POL-19`).
- **Verification Procedure:** Assert `check_strict_pure_riskless_candidate_gate` rejects `MULTI_LEG_BUNDLE` below `$500` NAV while allowing `CLINCH_DEAD_SPLIT_LOCK` and `NR_M1_DEAD_SEED_OVERROUND`.

#### `R-41` — `15%` Reconciled-NAV Correlated-Event / Station Concentration Cap (Once Parameter Bug `R-04` Is Fixed)
- **Category:** `JUSTIFIED_RISK_LIMIT`
- **Exact Locations:** [riskless_protocol_v2_expansion.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/riskless_protocol_v2_expansion.py#L2004-L2134)
- **Enforcement Behavior:** Caps single-event/station exposure (`max 1 slot` below `$150`) so a single sensor anomaly or UMA dispute can never freeze `51.6%` of equity again.
- **Economic Impact at `$47.38` Liquid:** Caps worst-case single-event lockup to `~$7.13` (`15%` of `$47.52` NAV), leaving `85%` (`$40.25`) liquid to keep compounding!
- **Safe Remediation:** **Retain** with `R-04` fix (`15%` of reconciled NAV instead of `max($20, 28% * book_equity)`).
- **Verification Procedure:** `pytest tests/test_qa_boost_audit_remediation.py -k concentration`.

#### `R-42` — Stage G `168-Hour` Continuous Live Shadow Certification Gate (`VenueCertificationTracker`)
- **Category:** `JUSTIFIED_RISK_LIMIT`
- **Exact Locations:** [cross_venue_unblock_and_certification.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_unblock_and_certification.py#L1109-L1136) & [#L1264-L1283](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_unblock_and_certification.py#L1264-L1283)
- **Enforcement Behavior:** Requires `168h` (`7` days) of `>= 99%` uptime, `<= 2%` API error rate, `0` Double-Zero settlement incidents, and post-delay positive L2 net PnL (` plus $253+` NAV & P0 legal eligibility) before allocating live capital to a second venue.
- **Economic Impact at `$47.38` Liquid:** `$0.00` lost EV today (at `$47.38` liquid cash, splitting capital across 2 venues is suboptimal vs single-venue Polygon compounding).
- **Safe Remediation:** **Retain** while `polymarket-cross-venue-shadow.service` accumulates continuous live hours passively in the background.
- **Verification Procedure:** Inspect `certification_report.json` (`progress_168h_pct`, `gates`).

#### `R-43` — Seed Bankroll Capital-Velocity Hurdle (`<= 8h` Lockup & `>= 15 bps/hr`, Once `R-09` Is Fixed)
- **Category:** `JUSTIFIED_RISK_LIMIT`
- **Exact Locations:** [holistic_strategy_governance.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/holistic_strategy_governance.py#L796-L848)
- **Enforcement Behavior:** Rejects long-dated low-yield carries (`eff_hrs > 8.0h` unless `>= 30 bps/hr` intraday, or `< 15 bps/hr`) while allowing `2h` UMA liveness recycle on `BOND1`.
- **Economic Impact at `$47.38` Liquid:** **Positive EV:** prevents multi-day lockups below the `7.2 bps/hr` infrastructure breakeven hurdle.
- **Safe Remediation:** **Retain** with `R-09` refinement (use `$47.52` deployable NAV + require actual mergeability for `C1` lockup exemption).
- **Verification Procedure:** `pytest tests/test_qa_boost_audit_remediation.py -k velocity_hurdle`.

---

### Category 10: `UNKNOWN` (1 Restriction — External Oracle Dispute Outcome Pending)

#### `R-44` — Pending UMA Optimistic Oracle / DVM Dispute Resolution on 4 `KMIA` Nov 7 Weather Positions (`$50.51` Cost Basis)
- **Category:** `UNKNOWN`
- **Exact Locations:** Live production `live_harvester_state.json` on `kraken-finland` (`markets 6707502 & 6707503`, 4 positions totaling `$50.51` cost basis, current CLOB bid `~2c` = `$0.14` mark-to-bid)
- **Enforcement Behavior:** External decentralized UMA token-holder vote / ancillary-rule interpretation (Weather Underground historical station report vs. NWS/METAR ASOS `$` sensor-maintenance temperature discrepancy on Nov 7, 2026 at Miami International Airport `KMIA`). Neither recovery amount (`$0.00` vs. `$50.51+`) nor exact final settlement block timestamp is deterministically knowable prior to on-chain UMA resolution.
- **Economic Impact at `$47.38` Liquid:** Binary `+$50.51` (`+106.6%` jump in liquid trading cash from `$47.38` to `$97.89+`) vs. `$0.00` recovery (`-$50.51` realized write-off from book equity, which **triggers `R-01` `$62.00` ruin-floor halt unless `R-01` is fixed first!**).
- **Safe Remediation:** **Do NOT sell/dump into `2c` bids (`$0.14` salvage forfeits `$50.37` free legal option value)**; leave all 4 positions **100% untouched**, treat deployable NAV conservatively as **`$47.52`** (`$47.38` cash + `$0.14` bid), and fix `R-01` (`hard_ruin_floor_usd`) immediately so a `$0.00` `KMIA` settlement cannot halt live riskless arbitrage on the `$47.38` cash!
- **Verification Procedure:** Read-only check on `live_harvester_state.json` confirming all 4 `KMIA` positions remain untouched with `exit_order_id == None`.
