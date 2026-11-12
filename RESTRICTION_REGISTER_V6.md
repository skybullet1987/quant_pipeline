# DOMINUS v6.0 — Independent Quantitative Restriction Reassessment Register (`RESTRICTION_REGISTER_V6.md`)

**Campaign:** DOMINUS Restriction Register v6.0 Reassessment & Dynamic Capital Optimization  
**Principal Auditor & Risk Architect:** Antigravity (`@principal-auditor`)  
**Reassessment Timestamp:** `2026-11-11 UTC`  
**Primary Source Challenged:** [RESTRICTION_REGISTER.md](file:///C:/Users/Anton/source/repos/Dominus/RESTRICTION_REGISTER.md) (`R-01` through `R-44`)  
**Reconciled Balance-Sheet Baseline (`2026-11-11 UTC`):**
- **Liquid Deployable `pUSD` (`sig_type=3` Beacon `0x013A...F4e9`):** **`$48.695132` (`$48.70`)** *(note: v5.0 `RESTRICTION_REGISTER.md` cited stale `$47.38` cash / `$97.89` book equity prior to `+2` riskless wins)*
- **True Worst-Case Guaranteed-Floor NAV:** **`$48.70`** (`$48.695132` cash + `$0.00` worst-case on 4 disputed `KMIA` positions)
- **Mark-to-Bid Liquidation NAV:** **`$48.83`** (`$48.695132` cash + `$0.1390` live CLOB bid on `52.0` disputed `KMIA` shares)
- **Persisted Book Equity (`total_account_equity`):** **`$99.21`** (`$48.695132` cash + `$50.51` frozen `KMIA` cost basis across markets `6707503` & `6707502`)
- **Post-Lock Pure-Riskless Live Realized Record:** **`79W / 0L` (`100.0%` WR), `+$18.246110` net realized P&L** (vs `41` retired directional/lattice trades `-$73.3385`)
- **Sunk Fixed GCP VM Burn:** **`$24.67/month`** (`$0.822333/day` = **`$0.034264/hr`**, `7.04 bps/hr` portfolio hurdle on `$48.70` cash; `$0.00` marginal compute/AI/Relayer cost per trade)

---

## 1. Executive Summary of v6.0 Classification Challenges

Out of the `44` restrictions in v5.0 [RESTRICTION_REGISTER.md](file:///C:/Users/Anton/source/repos/Dominus/RESTRICTION_REGISTER.md), our independent source-code, on-chain ABI, and full-universe (`375,355` observable markets / `201,012` active unclosed markets) audit **overturned or materially refined `28` v5.0 classifications (`63.6%`)**:

| v6.0 Revised Classification | Count | Restriction IDs | Core v6.0 Determination |
| :--- | :---: | :--- | :--- |
| **`ARBITRARY_STATIC_THRESHOLD_REPLACED_DYNAMIC`** | **8** | `R-01`, `R-02`, `R-03`, `R-04`, `R-09`, `R-41`, `R-42`, `R-43` | Replaced blind static dollar floors (`$62`/`$30`), sleeve-name allowlists, `300s` cold-boot cache wipeouts, `28% * book_equity`, `24h` maturity cliffs, the `DOMINANCE` `720h` capital-starvation loophole, and time-only `168h` waiting with exact mathematical/dynamic controls. |
| **`MODE_COUPLED_OVERBROAD_SPLIT_BY_MODE`** | **2** | `R-39`, `R-40` | Overturned blanket suppression in `RESEARCH` & `SHADOW`: `$150` directional and `$500` `>=3`-leg defaults apply only to unattended `LIVE` workers (`owner_explicitly_authorized=False`), while `RESEARCH` & `SHADOW` evaluate `100%` of the universe and explicit Owner authorization overrides internal thresholds in a single pass. |
| **`DEFECTIVE_IMPLEMENTATION_REPAIRED_OR_STAGED`** | **9** | `R-05`, `R-06`, `R-07`, `R-08`, `R-10`, `R-13`, `R-21`, `R-23`, `R-44` | Repaired single-pass approval CLI (`R-05`), selective non-exit emergency CLOB cancel + safeguard pre-resume block (`R-08`), infra double-counting (`R-10`), 13-schedule Protocol V2 fee & 2-decimal lot rounding (`R-23`), wallet split/merge ABI matrix (`R-21`), and `KMIA` `0.344%` breakeven EV proof (`R-44`). |
| **`MISDIAGNOSED_IN_V5_RETAINED_INTENTIONAL_INVARIANT`** | **2** | `R-11`, `R-12` | **Caught two v5.0 auditor errors:** setting `enable_ungraduated_v3_math_live: false` (`R-11`) breaks `CAL1`/`MKR_LOCK1`/`W_PRUNE1` live bridge (`polymarket_live_harvester.py:5835`) and fails unit tests; `polymarket_risk_config.json` (`R-12`) is an intentional backward-compatibility test fixture. |
| **`ALREADY_ELIMINATED_HISTORICAL`** | **1** | `R-14` | Five legacy Stage G internal env gates remain `ELIMINATED_UNLOCKED`; retained unlocked. |
| **`PHYSICAL_OR_EXCHANGE_CONSTRAINT_OPTIMIZED_AROUND`** | **9** | `R-15`..`R-20`, `R-22`, `R-24`, `R-25` | Physical capital (`$48.70`), swapless `3,907 MiB` RAM, `FI->London` RTT, optional read-only keys, `5`-share/`$1` CLOB lot floor, non-atomic CLOB matching, and public rate limits; optimized around via `DynamicMarginalCapitalAllocator` & Relayer V2 `18s` merges. |
| **`OWNER_SOVEREIGN_EXTERNAL_CONSTRAINT_ADVISORY`** | **7** | `R-26`..`R-32` | **Owner Sovereignty (`D-011`):** The Owner holds exclusive final authority over trading, venue selection, sizing, activation, and deployment. Separates verified external platform/regulatory/KYB gates from unverified assumptions & non-binding AI NAV heuristics (`$500`, `$10,000`), executes permitted Owner-authorized actions in a single pass, and emits explicit `ExternalBlockerReport` + lawful remedies (`0` silent disabling). |
| **`ESSENTIAL_INTEGRITY_PROTECTION_RETAINED`** | **6** | `R-33`..`R-38` | Anti-self-approval against unattended workers, secret stripping, `<UNTRUSTED_DATA_ONLY>`, Double-Zero 5-gate verifier, `0600` key-free shadow `.env`, and `$1.50`/`0.75`-share accounting safeguard preserved at `100%` strength. |

*(Exact count check: `8` dynamic + `2` mode-split + `9` repaired/staged + `2` misdiagnosed-in-v5 + `1` historical + `9` physical/exchange [`R-15`..`R-20`, `R-22`, `R-24`, `R-25`] + `7` Owner-sovereign external advisory [`R-26`..`R-32`] + `6` essential integrity [`R-33`..`R-38`] = **`44` restrictions**, `R-01`..`R-44`.)*

---

## 2. Revised Restriction Register (`R-01` through `R-44`)

### `R-01` — Fixed Dollar Ruin Floor (`$62.00` / `$30.00`) vs. Loss-Cause-Aware Reconciled Capital Control
- **Original Restriction & Rationale:** v5.0 `TECHNICAL_FIXABLE` — `hard_ruin_floor_usd: 62.0` (partially patched in v5.1 to `riskless_hard_ruin_floor_usd: 30.0`) halted all trading whenever `tot_equity` fell below a fixed dollar threshold, intending to preserve a survival reserve.
- **Verified Current Behavior:** In [polymarket_strategy_and_risk.json](file:///C:/Users/Anton/source/repos/Dominus/config/polymarket_strategy_and_risk.json#L76-L77), `hard_ruin_floor_usd` is `62.0` and `riskless_hard_ruin_floor_usd` is `30.0`. However, [polymarket_live_harvester.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L1278-L1296) still appends `last_checked_equity` into `eq_candidates` and evaluates a blind static `$30.00` floor: (a) `$30.00` is completely arbitrary and fails to halt if a new execution bug loses `-$1.65` on a supposedly riskless box (`$48.70 -> $47.05 > $30.00`!), while (b) unattributed equity drops conflate historical `KMIA` `$50.51` UMA write-offs and external cashflows with live execution losses.
- **Revised Classification:** `ARBITRARY_STATIC_THRESHOLD_REPLACED_DYNAMIC`
- **Research / Shadow / Live Impact:** `RESEARCH`: None (`0%` blocked). `SHADOW`: Tracks loss attribution without halting discovery. `LIVE`: Eliminates the post-`KMIA` false-positive blackout while catching real riskless execution bleed **`12x` faster** (`$0.75` single-box / `$1.50` cumulative vs `$18.70` drop to `$30.00`).
- **Real vs. Estimated Opportunity Cost:** **Measured Realized Loss to Date:** `$0.00` (because `KMIA` is still booked at `$50.51`, keeping `tot_equity = $99.21 > $62.00`). **Counterfactual Simulated Opportunity Loss:** `100%` live revenue blackout (`-$1.30` to `-$3.80/day` simulated net arb EV + `-$0.822/day` unrecovered VM burn) if `$62.00` floor fires upon `$0.00` `KMIA` resolution, or up to `-$18.70` (`38.4%` of liquid cash) undetected bleed before a static `$30.00` floor trips.
- **Recommended Modification:** Replace static equity floors with [`LossCauseAwareCapitalController`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L292-L403) decomposing every balance delta into: (1) quarantined historical dispute write-off (`$0` halt sensitivity), (2) verified external cashflows/wraps, (3) post-baseline new riskless loss (`<= $0.75` single-box, `<= $1.50` cumulative), (4) unexplained wallet-vs-state drift (`<= $1.50`), and (5) minimum exchange executable lot (`$6.50` = `5` shares + `$1.50` reserve).
- **Replacement Safety Control:** [`LossCauseAwareCapitalController.evaluate`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L322-L403) + `PAAAccountant` `$1.50` on-chain reconciliation (`R-38`).
- **Source-Code References:** [polymarket_live_harvester.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L1260-L1301), [v6_restriction_and_capital_allocator.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L292-L403), [permissions.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L213-L217).
- **Tests & Proof:** `TestV60RestrictionReassessmentAndAllocator.test_02_r01_loss_cause_controller_and_r44_kmia_dominance_proof` in [test_v60_restriction_reassessment_and_allocator.py](file:///C:/Users/Anton/source/repos/Dominus/tests/test_v60_restriction_reassessment_and_allocator.py#L112-L144) (`KMIA` `$50.51 -> $0` write-off `halted == False`; `-$1.65` new bleed at `$47.05` cash `halted == True`).
- **Operational Status:** **IMPLEMENTED & VERIFIED** in v6.0 allocator/controller (`$30.00` fallback also active in live config).
- **Remaining External Dependencies:** None (pure internal risk-accounting logic).

---

### `R-02` — String Sleeve-Name Allowlist & Blanket Dynamic-Fee Ban vs. Independent Mathematical Payoff Proof
- **Original Restriction & Rationale:** v5.0 `TECHNICAL_FIXABLE` — `check_strict_pure_riskless_candidate_gate` blocked `CAL1`/`COND1` via hardcoded sleeve-name strings to prevent unverified directional sleeves from leaking into `RISKLESS_PAA`.
- **Verified Current Behavior:** Even after v5.1 added `CAL1`/`COND1` names, [stage_c_zero_loss_velocity.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/stage_c_zero_loss_velocity.py#L604-L645) still: (a) banned **all** `fee_rate > 0` `CAL1`/`COND1` boxes (`99.4%` of active Polymarket markets — `199,841 / 201,012` — have `feesEnabled == True`!), (b) rejected valid mathematically proven duplicate-equivalence / cross-market implication pairs (`FT_I`, `FT_F`) whenever their sleeve string wasn't in a hardcoded set, (c) lacked an explicit `t_early_ts <= t_late_ts` inverted-deadline check on `CAL1` when `k_low/k_high == 0`, and (d) allowed single-source weather proxy claims unless `dual_source_wu_metar_verified is False` was checked.
- **Revised Classification:** `ARBITRARY_STATIC_THRESHOLD_REPLACED_DYNAMIC`
- **Research / Shadow / Live Impact:** `RESEARCH` & `SHADOW`: Unlocks `199,841` fee-enabled markets (`99.4%` of universe) previously skipped by binary zero-fee filters. `LIVE`: Admits fee-bearing `CAL1`/`COND1` and proven 2-leg equivalence boxes whenever exact V2 fee-adjusted `min_state_net_payoff_usd > 0`, while closing inverted-calendar and single-source weather proxy loopholes.
- **Real vs. Estimated Opportunity Cost:** **Measured Realized Impact:** `0` `CAL1`/`COND1`/`FT_I` live fills in 136-trade ledger (`100%` suppressed on fee-enabled markets); `3` live `CLASS_B` proven duplicate/strike arbs (`FT_I_DUP_EXACT_YES1_NO2_7a31ee13bbe9d7`, `FT_F_STRIKE_UP_DOM_5b58630442dc4c`) observed in [scans_d_to_i/scan_summary.json](file:///C:/Users/Anton/source/repos/Dominus/data/full_throttle/scans_d_to_i/scan_summary.json). **Counterfactual Simulated Opportunity Loss:** `+$0.1872/batch` RNV at `$48.70` NAV (`CAND_2` + `CAND_3` in `run_v6_counterfactual_opportunity_audit.py`).
- **Recommended Modification:** Admit candidates based on independent mathematical state-space proof (`rule_verified == True`, `min_state_net_payoff_usd > 0` net of V2 share-haircut fees, `neg_risk_augmented == False`, `t_early_ts <= t_late_ts`, and `dual_source_wu_metar_verified != False`).
- **Replacement Safety Control:** [`verify_independent_payoff_admission`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L463-L666) + updated [`check_strict_pure_riskless_candidate_gate`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/stage_c_zero_loss_velocity.py#L540-L686) (`78,696` rule-mismatch false arbs rejected empirically).
- **Source-Code References:** [stage_c_zero_loss_velocity.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/stage_c_zero_loss_velocity.py#L241-L295) & [#L540-L686](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/stage_c_zero_loss_velocity.py#L540-L686), [v6_restriction_and_capital_allocator.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L463-L666).
- **Tests & Proof:** `test_03_r02_independent_payoff_proof_and_r03_cold_boot_lkg_protection` (`PASS`) + `TestStageCZeroLossVelocity` (`7/7 PASS`).
- **Operational Status:** **IMPLEMENTED & VERIFIED** in working tree (`stage_c_zero_loss_velocity.py` + `v6_restriction_and_capital_allocator.py`).
- **Remaining External Dependencies:** Owner flat-book promotion (`LIVE_SERVICE_REDEPLOY`) to roll updated `stage_c_zero_loss_velocity.py` onto `kraken-finland`.

---

### `R-03` — Cached `alpha124` Graduation Coupling & Cold-Boot `84`-Key Zeroed LKG Wipeout Bug
- **Original Restriction & Rationale:** v5.0 `TECHNICAL_FIXABLE` — `maybe_execute_graduated_d1_box` blocked all live `C1`/`D1` boxes whenever `alpha124_shadow_state.json` `mtime` exceeded `300s`.
- **Verified Current Behavior:** Although v5.1 added `load_alpha124_graduation_maps_with_lkg_cache` (`24h` TTL), inspecting local [alpha124_shadow_state.json](file:///C:/Users/Anton/source/repos/Dominus/data/polymarket/alpha124_shadow_state.json) exposed a **critical cold-boot wipeout bug**: when `alpha124` restarts (`cycles == 0`), `by_sleeve` contains **`84` initialized keys** with `closed: 0, losses: 0` (`len(by_sl_map) == 84`), so `bool(by_sl_map)` was `True` and **overwrote `alpha124_graduation_lkg_cache.json` with all zeros**, revoking `d1_g8` ([polymarket_live_harvester.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L5804-L5835)) and blocking even contractual `C1_BINARY_COMPLETE_SET` identities! Conversely, cached historical graduation was conflated with millisecond-fresh market/account checks.
- **Revised Classification:** `ARBITRARY_STATIC_THRESHOLD_REPLACED_DYNAMIC`
- **Research / Shadow / Live Impact:** `RESEARCH` & `SHADOW`: Unaffected. `LIVE`: Prevents multi-hour `d1_g8` live arbitrage outages after any `alpha124` daemon restart while strictly enforcing fresh L2 book age (`<= 6.5s`), `umaResolutionStatus != 'disputed'`, `acceptingOrders == True`, and reconciled liquid cash on every live order.
- **Real vs. Estimated Opportunity Cost:** **Measured Realized Impact:** Verified cold-boot state (`cycles == 0`, `84` zeroed keys) observed in `data/polymarket/alpha124_shadow_state.json`. **Counterfactual Simulated Opportunity Loss:** `$0.50`–`$3.50` missed riskless EV per `alpha124` restart recovery window (`2–12h` to re-accumulate `8` closed shadow boxes).
- **Recommended Modification:** (1) Repair [`load_alpha124_graduation_maps_with_lkg_cache`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/stage_c_zero_loss_velocity.py#L754-L795) to merge LKG records ONLY into `{closed == 0, losses == 0}` cold-boot slots (`has_nonzero_grad` guard before overwriting sidecar) while immediately propagating any fresh `losses > 0`; (2) Decouple structural certification from fresh market/account checks via [`evaluate_decoupled_certification_and_fresh_state`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L692-L758).
- **Replacement Safety Control:** Slot-level `losses > 0` instant revocation + millisecond-fresh book/UMA/cash gates (`evaluate_decoupled_certification_and_fresh_state`).
- **Source-Code References:** [stage_c_zero_loss_velocity.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/stage_c_zero_loss_velocity.py#L665-L802), [polymarket_live_harvester.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L5804-L5835), [v6_restriction_and_capital_allocator.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L692-L758).
- **Tests & Proof:** `test_03_r02_independent_payoff_proof_and_r03_cold_boot_lkg_protection` (`84`-key cold-boot preserves `closed == 12`; `losses == 1` revokes immediately; stale `12s` book fails fresh gate even on `C1`).
- **Operational Status:** **IMPLEMENTED & VERIFIED** in [stage_c_zero_loss_velocity.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/stage_c_zero_loss_velocity.py#L754-L795).
- **Remaining External Dependencies:** None (ready for next flat-book harvester redeploy).

---

### `R-04` — Event Concentration Formula Flaws vs. Correlated Worst-Case Exposure (`CWCE`)
- **Original Restriction & Rationale:** v5.0 `TECHNICAL_FIXABLE` — `max($20, 28% * book_equity)` allowed `$27.41` (`57.7%` of liquid cash) per event; v5.1 patched `riskless_protocol_v2_expansion.py` to `15% * reconciled_nav_usd`.
- **Verified Current Behavior:** While [riskless_protocol_v2_expansion.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/riskless_protocol_v2_expansion.py#L1808-L1854) now computes `15%` of mark-to-bid NAV (`$7.33` at `$48.83`), two deeper quantitative flaws remained: (1) [polymarket_strategy_and_risk.json](file:///C:/Users/Anton/source/repos/Dominus/config/polymarket_strategy_and_risk.json#L41-L45) still carries conflicting `$45` / `65%` `BOND1` sleeve caps, and (2) notional-based concentration treats a same-condition mergeable `C1` complete set (`1 YES + 1 NO == $1.00` on identical `condition_id`, `$0.00` oracle directional risk!) identically to an unhedged single-station weather `BOND1` carry (`100%` UMA dispute freeze risk), while missing regional weather-front correlation (`KORD` + `KMDW` same storm system).
- **Revised Classification:** `ARBITRARY_STATIC_THRESHOLD_REPLACED_DYNAMIC`
- **Research / Shadow / Live Impact:** `RESEARCH`: Unrestricted. `SHADOW` & `LIVE`: Caps true correlated oracle/dispute worst-case exposure at `<= 15%` of reconciled mark-to-bid NAV (`$7.33` at `$48.83`) across multi-key clusters (station, regional weather front, UMA ancillary clause, fixture), while allowing mergeable same-condition `C1` boxes (`$0` oracle exposure, bounded only by transient legging slippage `partial_leg_unwind_risk_usd`) to utilize up to full liquid cash (`$21.86+`).
- **Real vs. Estimated Opportunity Cost:** **Measured Realized Loss Prior to Cap:** `$50.51` (`50.9%` of `$99.21` equity) frozen in 4 correlated `KMIA` Nov 7 positions. **Counterfactual Simulated Uplift of `CWCE` over Crude Notional Cap:** Unlocks `$21.86` `C1` gasless merge (`+$0.1430` vs `$0.0476` under a naive `$7.33` notional cap = **`+200.4%` more `C1` profit**) without adding `$0.01` of oracle risk!
- **Recommended Modification:** Measure exposure via [`evaluate_correlated_worst_case_exposure`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L806-L880) (`CWCE`).
- **Replacement Safety Control:** Multi-cluster `CWCE <= 15% * reconciled_mark_to_bid_nav_usd` (`$7.33` today) on all oracle/rule-exposed positions.
- **Source-Code References:** [riskless_protocol_v2_expansion.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/riskless_protocol_v2_expansion.py#L1808-L1854) & [#L2055-L2165](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/riskless_protocol_v2_expansion.py#L2055-L2165), [v6_restriction_and_capital_allocator.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L766-L880).
- **Tests & Proof:** `test_04_r04_r41_correlated_worst_case_exposure_cwce` (`KORD` `$5` + `KMDW` `$3` on `FRONT:MIDWEST` rejected at `$8.00 > $7.33`; `$15` mergeable `C1` allowed) + `TestV5Section7RiskInvariants.test_01`.
- **Operational Status:** **IMPLEMENTED & VERIFIED** (`15%` cap live in `riskless_protocol_v2_expansion.py`; full `CWCE` active in `DynamicMarginalCapitalAllocator`).
- **Remaining External Dependencies:** None.

---

### `R-05` — Approval Scope Mismatches, Missing Single-Use Consumption & Missing Human CLI
- **Original Restriction & Rationale:** v5.0 `TECHNICAL_FIXABLE` — `PermissionGate` had conjunction/scope mismatches, non-expiring `"*"` wildcards, and no CLI lifecycle commands.
- **Verified Current Behavior:** Live [permissions.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py) and [builder_and_deployer.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/builder_and_deployer.py) are among the 16 Zero-Trust `protected_files`. Auditing them alongside `paa_staging/proposals/v50_owner_control_package/` revealed two remaining gaps even in the v5.0 staged proposal: (1) `DeploymentController.promote_to_production` checked `has_owner_approval` (`consumed_at_utc is None`) but **never wrote `consumed_at_utc` back to disk** after promotion, leaving a 24-hour multi-use replay window, and (2) [paa_cli.py](file:///C:/Users/Anton/source/repos/Dominus/scripts/paa_cli.py) still had **zero `approvals` subcommands** (`list`, `grant`, `revoke`, `consume`).
- **Revised Classification:** `DEFECTIVE_IMPLEMENTATION_REPAIRED_OR_STAGED`
- **Research / Shadow / Live Impact:** `RESEARCH` & `SHADOW`: Unaffected (`AUTOMATICALLY_PERMITTED`). `LIVE`: Streamlines legitimate owner-authorized promotions while eliminating stale/replayed approval tokens.
- **Real vs. Estimated Opportunity Cost:** **Measured Realized Impact:** `$0.00` direct wallet loss; operational friction requiring manual JSON editing for owner promotions.
- **Recommended Modification:** (1) Land human-only `paa_cli.py approvals {list,grant,revoke,consume}` directly in [paa_cli.py](file:///C:/Users/Anton/source/repos/Dominus/scripts/paa_cli.py#L681-L790), hard-gated by `_verify_human_owner_cli_session` (`PAA_SIGNING_DISABLED != "1"`, empty `PAA_WORKER_ROLE`, interactive TTY); (2) Stage atomic post-promotion `consume_owner_approval(scope, release_id)` in [APPLY_AND_ROLLBACK.md](file:///C:/Users/Anton/source/repos/Dominus/paa_staging/proposals/v60_restriction_remediation_package/APPLY_AND_ROLLBACK.md) for human owner execution on protected `permissions.py` & `builder_and_deployer.py`.
- **Replacement Safety Control:** Interactive TTY + worker-env rejection (`rc=3`) + mandatory `expires_at_utc` (`<=168h`) + `consumed_at_utc` single-use binding + `revoked` flag + `SELF_APPROVAL_TAMPERING_FORBIDDEN` (`R-33`).
- **Source-Code References:** [paa_cli.py](file:///C:/Users/Anton/source/repos/Dominus/scripts/paa_cli.py#L681-L790) & [#L868-L889](file:///C:/Users/Anton/source/repos/Dominus/scripts/paa_cli.py#L868-L889), [permissions.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L97-L123), [APPLY_AND_ROLLBACK.md](file:///C:/Users/Anton/source/repos/Dominus/paa_staging/proposals/v60_restriction_remediation_package/APPLY_AND_ROLLBACK.md).
- **Tests & Proof:** `test_05_r05_r08_paa_cli_approvals_selective_cancel_and_safeguard_resume` (worker `PAA_SIGNING_DISABLED=1` rejected with `rc=3`; human TTY `grant -> consume -> revoke` verified).
- **Operational Status:** **CLI IMPLEMENTED & VERIFIED** in `scripts/paa_cli.py`; protected `permissions.py`/`builder_and_deployer.py` patch **STAGED FOR OWNER APPLY**.
- **Remaining External Dependencies:** Human owner execution of staged protected-file package (`D-003`).

---

### `R-06` — `active_positions_count > 0` Blocking Safe Deployments Across Passive Frozen `KMIA` UMA Locks
- **Original Restriction & Rationale:** v5.0 `TECHNICAL_FIXABLE` — `DeploymentController` blocked code promotions whenever `open_cnt > 0`, deferring improvements for days while the 4 `KMIA` positions sat passively in `umaResolutionStatus == "disputed"`.
- **Verified Current Behavior:** Both [paa_flat_harvester_redeploy_once.py](file:///C:/Users/Anton/source/repos/Dominus/scripts/paa_flat_harvester_redeploy_once.py#L36-L70) and [`is_harvester_state_restart_safe`](file:///C:/Users/Anton/source/repos/Dominus/audit_losing_trades.py#L457-L492) ALREADY recognize passive post-expiry `disputed` `KMIA` positions (`exit_order_id == None`, `0` non-frozen active positions, `0` non-maker in-flight entry intents) as 100% restart-safe! Only protected [builder_and_deployer.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/builder_and_deployer.py#L663-L675) awaits the staged owner apply (`v50_owner_control_package`).
- **Revised Classification:** `DEFECTIVE_IMPLEMENTATION_REPAIRED_OR_STAGED`
- **Research / Shadow / Live Impact:** `RESEARCH` & `SHADOW`: None (`shadow` daemons restart independently). `LIVE`: Enables immediate safe flat-book harvester redeploys via `paa_flat_harvester_redeploy_once.py` without touching the 4 disputed `KMIA` positions (`D-001`).
- **Real vs. Estimated Opportunity Cost:** **Measured Realized Impact:** `$0.00` today when using `paa_flat_harvester_redeploy_once.py`. **Counterfactual Delay Avoided:** Eliminates `48–168h` deployment freeze during UMA DVM voting windows.
- **Recommended Modification:** Use `is_harvester_state_restart_safe` across all deployment entrypoints and apply staged `builder_and_deployer.py` patch when convenient.
- **Replacement Safety Control:** Strict `is_harvester_state_restart_safe` check blocking restart if ANY non-frozen position, pre-expiry position, `exit_order_id`, or `pending_entry_intents` exists.
- **Source-Code References:** [paa_flat_harvester_redeploy_once.py](file:///C:/Users/Anton/source/repos/Dominus/scripts/paa_flat_harvester_redeploy_once.py#L36-L70), [audit_losing_trades.py](file:///C:/Users/Anton/source/repos/Dominus/audit_losing_trades.py#L457-L492), [builder_and_deployer.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/builder_and_deployer.py#L663-L675).
- **Tests & Proof:** `TestUMAFrozenRestartSafetyAlignment.test_05` & `test_06` (`2/2 PASS`).
- **Operational Status:** **IMPLEMENTED & LIVE** in `paa_flat_harvester_redeploy_once.py` & `audit_losing_trades.py`; **STAGED** for protected `builder_and_deployer.py`.
- **Remaining External Dependencies:** Human owner apply on `builder_and_deployer.py` (`D-003`).

---

### `R-07` — `polymarket_all_in_one.py` `1,000,000`-Byte Canary Ceiling & Binary/Data Artifact Diff Guard
- **Original Restriction & Rationale:** v5.0 `TECHNICAL_FIXABLE` — `_run_release_canary_probe` enforces `< 1,000,000` bytes and `0` CRLF on `polymarket_all_in_one.py` (`910,713 B`), while `permissions.py` originally lacked binary/data extension blocks.
- **Verified Current Behavior:** Live [permissions.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L341-L351) ALREADY enforces `DISALLOWED_BINARY_OR_DATA_ARTIFACT_DIFF` on `.sqlite3`, `.db`, `.jsonl`, `.parquet`, `.pkl`, and `.feather` outside `tests/`, and modular `src/polymarket_research/*.py` modules (`v6_restriction_and_capital_allocator.py`, `full_throttle_pipeline.py`) bypass bloating `polymarket_all_in_one.py`.
- **Revised Classification:** `DEFECTIVE_IMPLEMENTATION_REPAIRED_OR_STAGED`
- **Research / Shadow / Live Impact:** `0%` friction on modular `src/polymarket_research/` development across all 3 modes.
- **Real vs. Estimated Opportunity Cost:** **Measured & Estimated:** **`$0.00`**.
- **Recommended Modification:** Keep `polymarket_all_in_one.py` frozen at `910,713 B` and author all new logic in modular `src/polymarket_research/` packages with strict LF (`\n`) normalization.
- **Replacement Safety Control:** `PermissionGate.inspect_candidate_diff` binary/data artifact guard + `test_09` LF/non-zero-byte test assertion.
- **Source-Code References:** [permissions.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L341-L351), [builder_and_deployer.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/builder_and_deployer.py#L326-L335).
- **Tests & Proof:** `test_09_zero_trust_permission_gate_and_lf_hygiene_all_v6_deliverables` (`PASS`).
- **Operational Status:** **IMPLEMENTED & ACTIVE**.
- **Remaining External Dependencies:** None.

---

### `R-08` — Emergency Stop Selective Entry-Order Cancellation & Pre-Resume Safeguard Gate
- **Original Restriction & Rationale:** v5.0 `TECHNICAL_FIXABLE` — `paa_cli.py emergency-stop` lacked out-of-band CLOB cancellation and `KILL_SWITCH` creation.
- **Verified Current Behavior:** While v5.1 added `_cancel_open_clob_orders_out_of_band` and `KILL_SWITCH` to [paa_cli.py](file:///C:/Users/Anton/source/repos/Dominus/scripts/paa_cli.py#L430-L670), our independent v6.0 audit found **two residual safety defects**: (1) if **any** active position had a protective `exit_order_id`, `_cancel_open_clob_orders_out_of_band` skipped `cancel_all_orders()` and **left ALL resting `BUY` entry orders live on the CLOB** during an emergency stop, and (2) `paa_cli.py resume --include-trading` unlinked `KILL_SWITCH` **without checking whether `ACCOUNTING_SAFEGUARD_ACTIVE.json` was latched**!
- **Revised Classification:** `DEFECTIVE_IMPLEMENTATION_REPAIRED_OR_STAGED`
- **Research / Shadow / Live Impact:** `RESEARCH` & `SHADOW`: Cleanly stops/resumes shadow daemons when `--include-trading` is passed. `LIVE`: Cancels all resting unhedged `BUY` entry anchors out-of-band while preserving active protective `exit_order_id`s, and prevents accidental `KILL_SWITCH` clearance while an accounting discrepancy is active.
- **Real vs. Estimated Opportunity Cost:** **Measured Realized Loss:** `$0.00` to date. **Counterfactual Risk Prevented:** Up to **`$48.70` (`100%` of liquid cash)** protected from unmonitored resting `BUY` fills during a daemon halt with an open protective exit order.
- **Recommended Modification:** Repaired in [paa_cli.py](file:///C:/Users/Anton/source/repos/Dominus/scripts/paa_cli.py#L470-L508) & [#L610-L627](file:///C:/Users/Anton/source/repos/Dominus/scripts/paa_cli.py#L610-L627): iterate `get_open_orders()` and call `cancel_order(oid)` on every order NOT in `protected_exit_oids`; block `cmd_resume --include-trading` (`rc=2`) if `ACCOUNTING_SAFEGUARD_ACTIVE.json` is active unless `--force-override-safeguard` is passed.
- **Replacement Safety Control:** Selective non-exit CLOB order cancellation + `ACCOUNTING_SAFEGUARD_ACTIVE.json` pre-resume interlock.
- **Source-Code References:** [paa_cli.py](file:///C:/Users/Anton/source/repos/Dominus/scripts/paa_cli.py#L430-L514) & [#L602-L678](file:///C:/Users/Anton/source/repos/Dominus/scripts/paa_cli.py#L602-L678).
- **Tests & Proof:** `test_05_r05_r08_paa_cli_approvals_selective_cancel_and_safeguard_resume` + `TestPAAEmergencyStopAndResume` (`5/5 PASS`).
- **Operational Status:** **IMPLEMENTED & VERIFIED** in `scripts/paa_cli.py`.
- **Remaining External Dependencies:** None.

---

### `R-09` — Capital-Velocity Step Cliffs & `DOMINANCE` `720h` Starvation Loophole vs. Endogenous Opportunity-Cost Allocator
- **Original Restriction & Rationale:** v5.0 `TECHNICAL_FIXABLE` — `passes_capital_velocity_hurdle` used `$97.89` book equity and exempted unmergeable `COMPLETE_SET` boxes; v5.1 patched `merge_wallet_ok=True` on `COMPLETE_SET`.
- **Verified Current Behavior:** Auditing [holistic_strategy_governance.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/holistic_strategy_governance.py#L860-L895) uncovered a **much larger bidirectional flaw** missed by v5.0: (1) line `860` (`if btype_u in {"DOMINANCE", ...}: return True, "OK"`) **unconditionally exempted `DOMINANCE` boxes regardless of maturity**, allowing a `30-day` (`720h`) `30 bps` `DOMINANCE` box (`0.04 bps/hr`!) to lock cash for a month — directly explaining the **`107` `INSUFFICIENT_BOX_COLLATERAL_HEADROOM` skips** recorded in `PROFIT_SCORECARD.md`! Meanwhile, (2) when `100%` of `$48.70` cash sat idle (`utilization == 0%`) with zero competing spikes, a `25.5h` `280 bps` (`11.0 bps/hr`) `COND1` carry was rejected by a hard `24.0h` step cliff!
- **Revised Classification:** `ARBITRARY_STATIC_THRESHOLD_REPLACED_DYNAMIC`
- **Research / Shadow / Live Impact:** `RESEARCH`: Zero maturity cutoff (`0.0 bps/hr` hurdle). `SHADOW`: Zero maturity suppression; records full `MRNV` across all horizons. `LIVE`: Replaces arbitrary `8h`/`24h` cliffs and closes the `720h` `DOMINANCE` loophole via convex endogenous capital shadow price $\lambda_{\text{cap}}(u, r_{\text{disp}}) = \max(0.50 + 17.50 u^2,\; 0.50 \cdot r_{\text{disp}} \cdot u)$ `bps/hr`.
- **Real vs. Estimated Opportunity Cost:** **Measured Realized Impact:** `107` live `INSUFFICIENT_BOX_COLLATERAL_HEADROOM` candidate skips in `PROFIT_SCORECARD.md` while capital was tied up in lower-velocity carries. **Counterfactual Simulated Uplift (`run_v6_counterfactual_opportunity_audit.py`):** Increases single-batch `LIVE` Realizable Net Value at `$48.70` cash from **`$0.1635` -> `$0.5392` (`+229.8%` / `3.30x` RNV)** and at `$500.00` NAV from **`$0.2690` -> `$1.1761` (`+337.2%` / `4.37x` RNV)** while preventing `720h` `DOMINANCE` lockups!
- **Recommended Modification:** Rank and size portfolios via [`DynamicMarginalCapitalAllocator`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L1261-L1626) and opt-in `use_dynamic_opportunity_cost=True` in [`passes_capital_velocity_hurdle`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/holistic_strategy_governance.py#L818-L859).
- **Replacement Safety Control:** Endogenous utilization-dependent opportunity-cost charge `opp_cost_usd = alloc_cap * (lambda_bps_hr / 10000) * eff_lockup_hours` (`mrnv_usd > 0` required in `LIVE`).
- **Source-Code References:** [v6_restriction_and_capital_allocator.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L1261-L1626), [holistic_strategy_governance.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/holistic_strategy_governance.py#L818-L898).
- **Tests & Proof:** `test_06_r09_r43_r10_r15_dynamic_allocator_and_infra_reconciliation` (`PASS`).
- **Operational Status:** **IMPLEMENTED & VERIFIED** in `v6_restriction_and_capital_allocator.py` & `holistic_strategy_governance.py`.
- **Remaining External Dependencies:** None.

---

### `R-10` — Infrastructure Expense Horizon Mismatch & Per-Clip VM Overhead Double Counting
- **Original Restriction & Rationale:** v5.0 `TECHNICAL_FIXABLE` — `paa_autonomy_config.json` had `$0.0730/hr` instead of `$0.0343/hr` (`$24.67/mo` GCP VM).
- **Verified Current Behavior:** Even after `prorated_vm_hourly_cost_usd` was set to `0.0343` in [paa_autonomy_config.json](file:///C:/Users/Anton/source/repos/Dominus/config/paa_autonomy_config.json#L67) (`ai_billing_mode: "subscription_flat"` -> `$0.00` marginal AI cost in [budget.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/budget.py#L106-L135)), **two accounting bugs remained**: (1) [accountant.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/accountant.py#L541-L544) subtracts **only today's intraday `0..24h` UTC VM cost (`$0.00..$0.82`)** from **all-time multi-week cumulative P&L (`-$55.41` / `+$18.25`)**, causing `net_profit_after_ai_and_infra_usd` to jump artificially by `+$0.82` every UTC midnight, and (2) `PROFIT_SCORECARD.md` charged `$0.03426/hr` both per concurrent trade clip AND as daily portfolio overhead (double-counting **`$11.37`** across `79` riskless clips over `14d`!), treating a **sunk fixed VM cost** as if it were a marginal per-trade execution fee!
- **Revised Classification:** `DEFECTIVE_IMPLEMENTATION_REPAIRED_OR_STAGED`
- **Research / Shadow / Live Impact:** `RESEARCH` & `SHADOW`: Prevents false rejection of positive-MRNV clips (`$0.00` marginal VM/Relayer/AI cost per trade). `LIVE`: Separates **True Marginal Trading Profit** (`+$18.2461` over `79` riskless trades) from **Full-Cost Net Economic Profit** (`+$18.2461 - $11.5127` 14d VM = **`+$6.7334`**) on identical `window_hours`.
- **Real vs. Estimated Opportunity Cost:** **Measured Accounting Error Eliminated:** **`$11.3670`** per-clip double-count + **`$11.2636`** 14d-vs-intraday horizon distortion (`run_v6_counterfactual_opportunity_audit.py`).
- **Recommended Modification:** Reconcile via [`reconcile_infrastructure_expenses`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L1156-L1204) and apply staged horizon-alignment patch to protected [accountant.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/accountant.py#L541-L544) ([APPLY_AND_ROLLBACK.md](file:///C:/Users/Anton/source/repos/Dominus/paa_staging/proposals/v60_restriction_remediation_package/APPLY_AND_ROLLBACK.md)).
- **Replacement Safety Control:** Exact window-matched `(window_hours * $0.034264/hr)` portfolio hurdle reporting (`7.04 bps/hr` on `$48.70` cash) with `$0.00` artificial per-clip tax on gasless Relayer V2 trades.
- **Source-Code References:** [accountant.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/accountant.py#L541-L544), [budget.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/budget.py#L106-L135), [v6_restriction_and_capital_allocator.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L1156-L1204).
- **Tests & Proof:** `test_06_r09_r43_r10_r15_dynamic_allocator_and_infra_reconciliation` (`PASS`).
- **Operational Status:** **IMPLEMENTED & VERIFIED** in `v6_restriction_and_capital_allocator.py`; protected `accountant.py` patch **STAGED**.
- **Remaining External Dependencies:** Human owner apply on `src/paa_os/accountant.py`.

---

### `R-11` — `enable_ungraduated_v3_math_live: true` Flag *(v5.0 Misclassification Overturned)*
- **Original Restriction & Rationale:** v5.0 `LEGACY_UNNECESSARY` — Agent G claimed `enable_ungraduated_v3_math_live: true` in `polymarket_strategy_and_risk.json` was an obsolete pre-Nov-4 landmine that should be set to `false`.
- **Verified Current Behavior:** **v5.0 Auditor Claim Disproven by Source Inspection:** At [polymarket_live_harvester.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L5835-L5855), `v3_math_live` is the **active execution bridge** for `MKR_LOCK1`, `W_PRUNE1`, `CAL1`, and `COND1` boxes after they pass `check_strict_pure_riskless_candidate_gate` (`L5571`)! Furthermore, [test_stage_c_zero_loss_velocity.py](file:///C:/Users/Anton/source/repos/Dominus/tests/test_stage_c_zero_loss_velocity.py#L428) explicitly asserts this bridge remains enabled while `check_strict_pure_riskless_candidate_gate` blocks all unallowlisted/unproven sleeves upstream. Flipping it blindly to `false` would **silently kill live `CAL1`/`MKR_LOCK1`/`W_PRUNE1` execution**!
- **Revised Classification:** `MISDIAGNOSED_IN_V5_RETAINED_INTENTIONAL_INVARIANT`
- **Research / Shadow / Live Impact:** Preserves live `CAL1`/`COND1`/`W_PRUNE1`/`MKR_LOCK1` execution bridge while `strict_pure_riskless_mode: true` + `R-02` independent proof gate enforce mathematical zero-loss safety upstream.
- **Real vs. Estimated Opportunity Cost:** **`$0.00`** today; avoiding the erroneous v5.0 flip **prevents `-$6` to `-$18/mo` self-inflicted `CAL1`/`W_PRUNE1` blackout**!
- **Recommended Modification:** **Do NOT set `enable_ungraduated_v3_math_live: false`** until `polymarket_live_harvester.py:5835` is refactored to rename the flag to `enable_proof_verified_v6_bridge_live`.
- **Replacement Safety Control:** Upstream `check_strict_pure_riskless_candidate_gate` (`L5571`, tested by `test_06_pure_riskless_lockdown_blocks_all_probabilistic_and_multileg_loopholes`).
- **Source-Code References:** [polymarket_strategy_and_risk.json](file:///C:/Users/Anton/source/repos/Dominus/config/polymarket_strategy_and_risk.json#L204), [polymarket_live_harvester.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L5571) & [#L5835-L5855](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L5835-L5855), [test_stage_c_zero_loss_velocity.py](file:///C:/Users/Anton/source/repos/Dominus/tests/test_stage_c_zero_loss_velocity.py#L428).
- **Tests & Proof:** `TestStageCZeroLossVelocity.test_06` (`PASS`).
- **Operational Status:** **VERIFIED & RETAINED AS-IS** (prevented destructive v5.0 recommendation).
- **Remaining External Dependencies:** None.

---

### `R-12` — `config/polymarket_risk_config.json` Legacy Fallback File *(v5.0 Misclassification Overturned)*
- **Original Restriction & Rationale:** v5.0 `LEGACY_UNNECESSARY` — Claimed `polymarket_risk_config.json` caused runtime config drift against `polymarket_strategy_and_risk.json`.
- **Verified Current Behavior:** Live runtime governance in [polymarket_live_harvester.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L583) & [holistic_strategy_governance.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/holistic_strategy_governance.py#L755) is governed 100% by `GLOBAL_GOVERNANCE_MANAGER.snapshot` (`polymarket_strategy_and_risk.json` v5.5.0), whereas [polymarket_risk_config.json](file:///C:/Users/Anton/source/repos/Dominus/config/polymarket_risk_config.json) (`66.67`, `99`) is explicitly asserted by legacy regression suites (`tests/test_orderflow_hardening.py:1544`, `tests/test_zero_trust_forensic_audit.py:438`).
- **Revised Classification:** `MISDIAGNOSED_IN_V5_RETAINED_INTENTIONAL_INVARIANT`
- **Research / Shadow / Live Impact:** **`0%`** impact on `RESEARCH`, `SHADOW`, or `LIVE`.
- **Real vs. Estimated Opportunity Cost:** **`$0.00`**.
- **Recommended Modification:** Retain `polymarket_risk_config.json` untouched as a legacy test fixture; treat `polymarket_strategy_and_risk.json` as the sole live runtime authority.
- **Replacement Safety Control:** Hot-reload schema validation (`[CONFIG_HOT_RELOAD] Applied validated snapshot 5.5.0`).
- **Source-Code References:** [polymarket_risk_config.json](file:///C:/Users/Anton/source/repos/Dominus/config/polymarket_risk_config.json#L1-L49), [holistic_strategy_governance.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/holistic_strategy_governance.py#L745-L790).
- **Tests & Proof:** `TestStageCZeroLossVelocity.test_01` & `TestV5Section7RiskInvariants.test_04` (`PASS`).
- **Operational Status:** **VERIFIED & RETAINED**.
- **Remaining External Dependencies:** None.

---

### `R-13` — Stale `280M` / `320M` Cgroup Prose in Protected `cross_venue_unblock_and_certification.py`
- **Original Restriction & Rationale:** v5.0 `LEGACY_UNNECESSARY` — `RestrictionRegistry` prose reported `MemoryHigh=280M, MemoryMax=320M` after `polymarket-cross-venue-shadow.service` was raised to `450M` / `512M`.
- **Verified Current Behavior:** Confirmed at [cross_venue_unblock_and_certification.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_unblock_and_certification.py#L1120-L1122) & [#L1517-L1530](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_unblock_and_certification.py#L1517-L1530) (one of the 16 Zero-Trust `protected_files`); purely cosmetic JSON telemetry text (`0` runtime cgroup enforcement impact, since systemd enforces [polymarket-cross-venue-shadow.service](file:///C:/Users/Anton/source/repos/Dominus/systemd/polymarket-cross-venue-shadow.service#L15-L16) `450M`/`512M` directly).
- **Revised Classification:** `DEFECTIVE_IMPLEMENTATION_REPAIRED_OR_STAGED`
- **Research / Shadow / Live Impact:** **`0%`** runtime impact across all modes.
- **Real vs. Estimated Opportunity Cost:** **`$0.00`**.
- **Recommended Modification:** Staged exact text sync (`450M`/`512M`) in [APPLY_AND_ROLLBACK.md](file:///C:/Users/Anton/source/repos/Dominus/paa_staging/proposals/v60_restriction_remediation_package/APPLY_AND_ROLLBACK.md).
- **Replacement Safety Control:** Actual `systemd` `MemoryHigh=450M`, `MemoryMax=512M`, `MemorySwapMax=0B` unit enforcement (`D-010`).
- **Source-Code References:** [cross_venue_unblock_and_certification.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_unblock_and_certification.py#L1120-L1122), [polymarket-cross-venue-shadow.service](file:///C:/Users/Anton/source/repos/Dominus/systemd/polymarket-cross-venue-shadow.service#L15-L19).
- **Tests & Proof:** `test_09_zero_trust_permission_gate_and_lf_hygiene_all_v6_deliverables` (`PASS` — protected file untouched in working tree).
- **Operational Status:** **STAGED FOR OWNER APPLY**.
- **Remaining External Dependencies:** Human owner apply (`D-003`).

---

### `R-14` — Five Previously Eliminated Stage G Internal Administrative Env Gates
- **Original Restriction & Rationale:** v5.0 `LEGACY_UNNECESSARY` — Historical imaginary env vars (`PREDICT_FUN_DATA_LICENSE_ID`, `SX_BET_DATA_APPROVAL_ID`, `FORECASTEX_PUBLIC_PORTAL_AUTHORIZED`, etc.) already marked `ELIMINATED_UNLOCKED`.
- **Verified Current Behavior:** Confirmed `current_status == "ELIMINATED_UNLOCKED"` in [cross_venue_unblock_and_certification.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_unblock_and_certification.py#L1471-L1545); zero blocking effect on any mode.
- **Revised Classification:** `ALREADY_ELIMINATED_HISTORICAL`
- **Research / Shadow / Live Impact:** **`0%`** blocked (`6/6` Stage G venues stream authorized public/content telemetry).
- **Real vs. Estimated Opportunity Cost:** **`$0.00`**.
- **Recommended Modification:** Retain unlocked; never re-introduce synthetic internal env gates for public APIs.
- **Replacement Safety Control:** Provider API rate-limit & ToS compliance (`R-25`).
- **Source-Code References:** [cross_venue_unblock_and_certification.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_unblock_and_certification.py#L1471-L1545).
- **Tests & Proof:** Verified unlocked in Stage G telemetry & `evaluate_mode_specific_eligibility(ExecutionMode.RESEARCH)`.
- **Operational Status:** **ELIMINATED / NO ACTION NEEDED**.
- **Remaining External Dependencies:** None.

---

### `R-15` — Deployable Liquid Capital Scale (`$48.70` Cash vs. `$50.51` Frozen `KMIA`)
- **Original Restriction & Rationale:** v5.0 `RESOURCE_LIMITATION` — Small liquid cash (`$47.38`, now `$48.70`) limits absolute `$/day` P&L and multi-venue splitting while `$50.51` sits frozen in `KMIA`.
- **Verified Current Behavior:** Reconciled on-chain `pUSD` is **`$48.695132`** (`$48.83` mark-to-bid NAV; `$99.21` book equity). Previously, `$48.70` was further choked by: (a) counting frozen `KMIA` cost in legacy headroom denominators or starving behind `720h` `DOMINANCE` locks (`107` `INSUFFICIENT_BOX_COLLATERAL_HEADROOM` skips), and (b) treating `18s` gasless `C1` merges as full-cycle cash consumption.
- **Revised Classification:** `PHYSICAL_OR_EXCHANGE_CONSTRAINT_OPTIMIZED_AROUND`
- **Research / Shadow / Live Impact:** `RESEARCH`: Completely decoupled from `$48.70` wallet balance (`alloc_sh = max_executable_shares`). `SHADOW`: Tracks both `$48.70`-scaled and `$1,000` reference portfolios. `LIVE`: Optimizes `100%` of `$48.70` liquid `pUSD` (`$0.00` assumed from frozen `KMIA`!) via `18s` Relayer V2 merges (`5%` transient buffer) + zero-loss open-carry recycling (`maybe_recycle_open_bond_for_velocity_spike`).
- **Real vs. Estimated Opportunity Cost:** **Measured Realized Impact:** `79W / 0L` earned `+$18.2461` (`+37.5%` cumulative return on current liquid cash); `$50.51` `KMIA` freeze halves deployable single-clip scale (`$48.70` vs `$99.21`). **Counterfactual Simulated Uplift (`$48.70` -> `$99.21`):** `+$0.4009/batch` (`$0.5392` -> `$0.9401`, `+74.4%` RNV upon `KMIA` par recovery).
- **Recommended Modification:** Deploy [`DynamicMarginalCapitalAllocator`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L1261-L1626) + keep `100%` of `$48.70` consolidated in Polygon `pUSD` until undisputed NAV `>= $253–$500`.
- **Replacement Safety Control:** `reconciled_liquid_pusd_usd` sizing (`0%` credit for frozen `KMIA` cost basis) + `CWCE <= 15%` cluster cap (`$7.33`).
- **Source-Code References:** [stage_c_zero_loss_velocity.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/stage_c_zero_loss_velocity.py#L1215-L1335), [v6_restriction_and_capital_allocator.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L1468-L1578).
- **Tests & Proof:** `TestStageCZeroLossVelocity.test_03` & `test_07` + `TestV60RestrictionReassessmentAndAllocator.test_06` (`PASS`).
- **Operational Status:** **OPTIMIZED & VERIFIED**.
- **Remaining External Dependencies:** UMA DVM resolution of `$50.51` `KMIA` (`R-44`) or organic compounding of `$48.70`.

---

### `R-16` — `kraken-finland` `2 vCPU / 3,907 MiB` Physical RAM & `MemorySwapMax=0B` Swapless Ceiling
- **Original Restriction & Rationale:** v5.0 `RESOURCE_LIMITATION` — `$24.67/mo` GCP VM (`3,907 MiB` physical RAM, `0 B` cgroup swap) requires strict per-daemon memory bounds (`D-010`).
- **Verified Current Behavior:** Streaming state hydration in `alpha_124_shadow_daemon.py` (`MemoryMax=1550M`), `polymarket_terminal_recorder.py`, `cross_venue_riskless_shadow.py` (`MemoryMax=512M`), and `full_throttle_pipeline.py` (`peak_rss_mib == 54.98 MiB <= 180 MiB` budget!) keeps `~1,800 MiB` free RAM on `kraken-finland` with `0` OOM kills. Upgrading the VM would double fixed burn (`+$25/mo`), destroying net EV at `$48.70` cash.
- **Revised Classification:** `PHYSICAL_OR_EXCHANGE_CONSTRAINT_OPTIMIZED_AROUND`
- **Research / Shadow / Live Impact:** Heavy unit tests/WFO run locally on Windows (`D-010`), while `180 MiB`-bounded streaming scanners run `24/7` on `kraken-finland` in `SHADOW` & `LIVE` without OOM risk.
- **Real vs. Estimated Opportunity Cost:** **`$0.00`** marginal opportunity loss (saves `~$300/yr` in unnecessary cloud spend).
- **Recommended Modification:** Retain `$24.67/mo` VM and `180 MiB` streaming RSS discipline until NAV `>= $1,000`.
- **Replacement Safety Control:** `systemd` `MemoryHigh`/`MemoryMax` + `RSSGuard` (`180 MiB` soft ceiling) + Windows-only test execution (`D-010`).
- **Source-Code References:** [polymarket-alpha124-shadow.service](file:///C:/Users/Anton/source/repos/Dominus/systemd/polymarket-alpha124-shadow.service#L15-L20), [full_throttle_pipeline.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/full_throttle_pipeline.py#L140-L185).
- **Tests & Proof:** `TestFullThrottlePipelineAndDashboard.test_02_family_normalization_and_rss_guard` (`peak_rss_mib = 54.98 MiB`, `PASS`).
- **Operational Status:** **OPTIMIZED & ACTIVE**.
- **Remaining External Dependencies:** Physical VM SKU (`e2-medium` Finland).

---

### `R-17` — `europe-north1-b` (Finland) Network RTT (`~32–45ms`) to Polymarket CLOB (`eu-west-2` London)
- **Original Restriction & Rationale:** v5.0 `RESOURCE_LIMITATION` — Fiber distance between Hamina (`FI`) and London (`eu-west-2`, where UK *server IPs* are geoblocked on `POST /order`, making Amsterdam `europe-west4` / Dublin `eu-west-1` the closest non-UK regions).
- **Verified Current Behavior:** Persistent HTTP keep-alive connection pooling, `orjson` serialization, and pre-warmed EIP-712 signing are active in `polymarket_live_harvester.py` / `polymarket_live_executor.py`. `79W / 0L` live execution record confirms `FI` wins `C1`, `D1` quiet-book/4h, `BOND1` FIFO Maker, and `CLINCH_DEAD_SPLIT` cleanly, losing only `<25ms` sub-second crypto taker races.
- **Revised Classification:** `PHYSICAL_OR_EXCHANGE_CONSTRAINT_OPTIMIZED_AROUND`
- **Research / Shadow / Live Impact:** `RESEARCH` & `SHADOW`: Zero impact (shadow models `takerDelayMs` explicitly). `LIVE`: `~25ms` RTT delta vs Amsterdam `europe-west4`.
- **Real vs. Estimated Opportunity Cost:** **Measured Realized Loss:** `$0.00` principal loss (`0` unhedged taker race losses in `79` pure-riskless trades). **Estimated Counterfactual:** `$0`–`$4/mo` missed sub-25ms contested taker snipes at `$48.70` cash.
- **Recommended Modification:** Keep zero-cost Finland host until undisputed NAV `>= $250`, then evaluate a `$0`-cost-delta migration to `europe-west4` (Netherlands, `~7–9ms` RTT to London) during a scheduled flat window.
- **Replacement Safety Control:** L2 depth cushion + FOK/FAK execution + `UNWRESID` immediate unwind shield (`R-24`).
- **Source-Code References:** [polymarket_live_executor.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_executor.py#L850-L940), [cross_venue_shadow_deployment_gates.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_shadow_deployment_gates.py#L989).
- **Tests & Proof:** Verified `79W / 0L` live fill record in `PROJECT_STATE.md`.
- **Operational Status:** **OPTIMIZED AROUND / DEFERRED TO `$250` NAV**.
- **Remaining External Dependencies:** GCP region placement (`europe-north1-b` vs `europe-west4`).

---

### `R-18` — Optional `SX_BET_API_KEY` Unset in `/etc/polymarket-shadow.env`
- **Original Restriction & Rationale:** v5.0 `AUTHENTICATION_CONFIGURATION` — Keyless `api.sx.bet` serves `365+` active markets and summary odds, while full L2 `/orderbook-v3/snapshot` & Centrifugo WS return `HTTP 401` without `x-sx-api-key`.
- **Verified Current Behavior:** Verified in [cross_venue_shadow_deployment_gates.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_shadow_deployment_gates.py#L1399-L1463): keyless public REST is `AUTHORIZED_LIVE`, while `SX_BET_API_KEY` is optional read-only enrichment; live SX Bet trading is prohibited in `CA-ON` (`R-29`).
- **Revised Classification:** `PHYSICAL_OR_EXCHANGE_CONSTRAINT_OPTIMIZED_AROUND`
- **Research / Shadow / Live Impact:** `RESEARCH` & `SHADOW`: Top-of-book summary active; multi-rung L2 depth awaits free read-only API key. `LIVE`: Blocked by `R-29` (`CA-ON`).
- **Real vs. Estimated Opportunity Cost:** **Measured & Estimated at `$48.70` Cash:** **`$0.00`**.
- **Recommended Modification:** Defer optional read-only key request until `CA-ON`-legal venues (`ForecastEx`/`STX`) are scaled past `$500` NAV.
- **Replacement Safety Control:** Zero-signing-key shadow `.env` validator (`R-37`).
- **Source-Code References:** [cross_venue_shadow_deployment_gates.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_shadow_deployment_gates.py#L1399-L1463).
- **Tests & Proof:** Covered by Stage G venue authorization matrix tests.
- **Operational Status:** **KEYLESS PUBLIC FEED ACTIVE**.
- **Remaining External Dependencies:** External SX Bet read-only API key issuance.

---

### `R-19` — Optional `STX_API_KEY_ID` / `STX_ED25519_KEY_FILE` Unset for STX Signed REST
- **Original Restriction & Rationale:** v5.0 `AUTHENTICATION_CONFIGURATION` — Signed REST `/api/v1/markets` returns `HTTP 403` without Ed25519 headers, while unsigned public Phoenix WebSocket (`wss://api.on.stxapp.ca/socket/websocket?vsn=2.0.0`) already streams live STX L2 orderbooks.
- **Verified Current Behavior:** Confirmed in [cross_venue_shadow_deployment_gates.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_shadow_deployment_gates.py#L820-L849): Phoenix WS provides full live STX Ontario L2 book depth without credentials.
- **Revised Classification:** `PHYSICAL_OR_EXCHANGE_CONSTRAINT_OPTIMIZED_AROUND`
- **Research / Shadow / Live Impact:** `RESEARCH` & `SHADOW`: Live L2 orderbooks already streaming via Phoenix WS (`0%` blocked). `LIVE`: Requires physical `CA-ON` execution host (`R-30`) + `$500+` NAV.
- **Real vs. Estimated Opportunity Cost:** **`$0.00`** at `$48.70` cash.
- **Recommended Modification:** Generate Ed25519 keypair on `CA-ON` workstation only when preparing `$500+` NAV `CA-ON` regulated cross-venue canary.
- **Replacement Safety Control:** Strict separation of read-only Phoenix WS (`FI`) from personal `CA-ON` trading credentials (`R-30`, `R-37`).
- **Source-Code References:** [cross_venue_shadow_deployment_gates.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_shadow_deployment_gates.py#L820-L849).
- **Tests & Proof:** Verified in Stage G health telemetry.
- **Operational Status:** **UNSIGNED PHOENIX L2 WS ACTIVE**.
- **Remaining External Dependencies:** Owner STX Ontario account Ed25519 key generation at `$500+` NAV.

---

### `R-20` — Optional `IBKR_GATEWAY_URL` Local Client Portal Session Not Running
- **Original Restriction & Rationale:** v5.0 `AUTHENTICATION_CONFIGURATION` — Public CFTC DCM CSV (`forecastex.com/api/download`, `~600` contracts) is active, while streaming CPAPI `smd+{conid}` quotes require an authenticated IBKR Client Portal Gateway.
- **Verified Current Behavior:** Confirmed in [cross_venue_shadow_deployment_gates.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_shadow_deployment_gates.py#L887-L954); at `$48.70` cash, splitting capital across IBKR CAD/USD brokerage + Polygon `pUSD` is suboptimal due to `$1` minimum clip floors and currency conversion drag.
- **Revised Classification:** `PHYSICAL_OR_EXCHANGE_CONSTRAINT_OPTIMIZED_AROUND`
- **Research / Shadow / Live Impact:** `RESEARCH` & `SHADOW`: Daily/periodic CFTC contract discovery active; sub-second streaming L1 awaits local IBKR Gateway session. `LIVE`: Legally eligible in `CA-ON` via IBKR Canada (`ForecastEx`), deferred on capital scale until `NAV >= $253–$500`.
- **Real vs. Estimated Opportunity Cost:** **`$0.00`** at `$48.70` cash; primary regulated cross-venue expansion target at `$500+` NAV.
- **Recommended Modification:** Stand up IBKR Client Portal Gateway on `CA-ON` host once undisputed NAV reaches `$250` so `R-42` 5-pillar evidence readiness completes ahead of `$500` NAV.
- **Replacement Safety Control:** `evaluate_evidence_based_venue_readiness` (`R-42`) — currently scores `40.0%` (`P1`, `P4`, `P5` pending live L1/L2 quote depth).
- **Source-Code References:** [cross_venue_shadow_deployment_gates.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_shadow_deployment_gates.py#L887-L954), [v6_restriction_and_capital_allocator.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L1722-L1780).
- **Tests & Proof:** `run_v6_counterfactual_opportunity_audit.py` (`forecastex_current.score_pct == 40.0%`).
- **Operational Status:** **PUBLIC CSV FEED ACTIVE / CPAPI GATEWAY DEFERRED TO `$250` NAV**.
- **Remaining External Dependencies:** Authenticated IBKR Canada Client Portal session (`FORECASTX` permissions).

---

### `R-21` — Wallet Split/Merge & Collateral-Recycling Capability Validation Across `sig_type` `0..3` & Protocol V1/V2
- **Original Restriction & Rationale:** v5.0 `AUTHENTICATION_CONFIGURATION` — Checked only `bool(os.getenv("POLY_BUILDER_API_KEY"))` (`polymarket_live_harvester.py:5764`) to decide whether `sig_type == 3` could merge `C1` complete sets.
- **Verified Current Behavior:** Independent on-chain ABI & executor audit ([POLYMARKET_ONCHAIN_MOF_AUDIT.md](file:///C:/Users/Anton/source/repos/Dominus/POLYMARKET_ONCHAIN_MOF_AUDIT.md) + [polymarket_live_executor.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_executor.py#L4320-L4345)) revealed **three critical protocol facts missed by v5.0**: (1) Live production `sig_type=3` Beacon wallet (`0x013A...F4e9`) on `CTF_V1_PUSD` (`0x4D97...6045` + `pUSD` `0xC0B1...806E`) **DOES support `18s` (`0.005h`) gasless batch `splitPosition`/`mergePositions` via Relayer V2 (`24 tx/min` quota)**, turning a `120h` `C1` box into an `18s` cash recycle (`13,085 bps/hr`!); (2) **Executor Defect Uncovered (`L4326-4330`):** When `collateral == USDC_E_ADDRESS` (`0x2791...4174`) and `ctf_is_approved_for_adapter_v2 == True`, `polymarket_live_executor.py` encodes 5-arg `CTF.mergePositions(pUSD, ...)` to `CTF_ADAPTER_V2` (`0x6926...c395`), which reverts on legacy `USDC.e` tokens; and (3) **Protocol V2 `PositionManager` (`0x006F54...`)** ERC-6909 split/merge ABI is NOT yet wired in `polymarket_live_executor.py`!
- **Revised Classification:** `DEFECTIVE_IMPLEMENTATION_REPAIRED_OR_STAGED`
- **Research / Shadow / Live Impact:** `RESEARCH` & `SHADOW`: Models exact `0.005h` (`18s`) merge lockup on `CTF_V1_PUSD` vs `24h+` TTE lockup on unsupported `PROTOCOL_V2_POSITION_MANAGER` / unpatched `CTF_V1_LEGACY_USDCE` (`never confusing nominal riskless payoff with instant settlement!`). `LIVE`: Prevents reverted Relayer merges and unlocks `18s` `C1` capital recycling on `pUSD` markets.
- **Real vs. Estimated Opportunity Cost:** **Measured Realized Impact:** `8` flat `$0.00` on-chain merges executed cleanly on `CTF_V1_PUSD`. **Counterfactual Velocity Gain:** `18s` (`0.005h`) merge increases `C1` capital velocity by **`6,000x`–`24,000x`** over waiting `30h–120h` to expiry!
- **Recommended Modification:** Implemented [`validate_wallet_split_merge_capabilities`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L1033-L1134) across all `12` `(sig_type 0..3) x (CTF_V1_PUSD, CTF_V1_LEGACY_USDCE, PROTOCOL_V2_POSITION_MANAGER)` combinations, enforcing Relayer `24 tx/min` headroom, `POL >= 0.05` gas check on `sig_type 0/2`, and fail-closed `24h` lockup fallback whenever merge ABI is unsupported.
- **Replacement Safety Control:** Protocol-generation + signature-architecture + Relayer-quota capability validator (`validate_wallet_split_merge_capabilities`).
- **Source-Code References:** [polymarket_live_executor.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_executor.py#L4320-L4345), [polymarket_live_harvester.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L5760-L5778), [v6_restriction_and_capital_allocator.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L1017-L1134).
- **Tests & Proof:** `test_07_r21_wallet_capabilities_and_r23_protocol_v2_fees_and_rounding` (`sig_type=3 + CTF_V1_PUSD` `merge_supported=True, effective_recycle_lockup_hours=0.005`; `PROTOCOL_V2_POSITION_MANAGER` `merge_supported=False` with explicit ABI defect tag).
- **Operational Status:** **IMPLEMENTED & VERIFIED** in `v6_restriction_and_capital_allocator.py` (executor `L4326` legacy `USDC.e` routing documented in roadmap Wave 2).
- **Remaining External Dependencies:** Polymarket Relayer V2 service availability (`24 tx/min` provider cap).

---

### `R-22` — Polymarket CLOB Minimum Order Size (`5` Shares & `$1.00` Marketable BUY Notional)
- **Original Restriction & Rationale:** v5.0 `PROVIDER_CONTRACTUAL` — `clob.polymarket.com` rejects limit orders `< minimum_order_size` (`5` shares) and marketable `BUY` orders `< $1.00` USDC notional (`HTTP 400`).
- **Verified Current Behavior:** Confirmed external matching-engine rule enforced pre-flight in [stage_c_zero_loss_velocity.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/stage_c_zero_loss_velocity.py#L810-L835) and [v6_restriction_and_capital_allocator.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L1491). On V2 fee-bearing markets where `BUY` fees are deducted in **delivered shares** (`R-23`), buying exactly `5.00` gross shares at `p=0.50` (`weather_fees` `5%` -> `1.25%` share haircut) delivers **`4.9375` net shares** (`< 5.0` shares required to pair or sell on a `5`-share minimum leg!), requiring gross lot gross-up `ceil(5.0 / (1 - haircut))`!
- **Revised Classification:** `PHYSICAL_OR_EXCHANGE_CONSTRAINT_OPTIMIZED_AROUND`
- **Research / Shadow / Live Impact:** `RESEARCH`: Tracks exact minimum executable lot without discarding sub-lot theoretical spreads (`dormant` watchlist). `SHADOW` & `LIVE`: Enforces `alloc_sh >= min_order_shares` (`5.0`) and `alloc_cap >= $1.00` plus V2 share-haircut gross-up so paired legs match penny-and-share exact.
- **Real vs. Estimated Opportunity Cost:** **Measured Realized Impact:** Eliminates `< $5` micro-sizing on `$48.70` cash; requires `>= 13` shares (`>= $13`) if pairing a `$0.08` tail leg.
- **Recommended Modification:** Retain pre-flight `5`-share / `$1.00` lot gate and pair with V2 share-haircut gross-up (`R-23`).
- **Replacement Safety Control:** Pre-flight lot & 2-decimal `makerAmount` quantization (`verify_exact_polymarket_fee_and_rounding`).
- **Source-Code References:** [v6_restriction_and_capital_allocator.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L975-L1014) & [#L1491](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L1491).
- **Tests & Proof:** `test_07_r21_wallet_capabilities_and_r23_protocol_v2_fees_and_rounding` (`PASS`).
- **Operational Status:** **IMPLEMENTED & ACTIVE**.
- **Remaining External Dependencies:** External Polymarket CLOB exchange lot specification.

---

### `R-23` — Source-Verified Protocol V2 13-Schedule Taker Fees, Share-Haircut Pricing & 2-Decimal Lot Rounding
- **Original Restriction & Rationale:** v5.0 `PROVIDER_CONTRACTUAL` — Treated Polymarket taker fees broadly as `crypto_fees_v2` (`7% * p * (1 - p)`) and assumed `compute_exact_taker_fee_per_share` was already complete.
- **Verified Current Behavior:** Independent inspection of live Gamma API metadata across `201,012` active markets (`199,841` with `feesEnabled == True`, `1,171` / `1,144` `zero_fees`) and `universal_arb_verifier.py` / `polymarket_live_harvester.py` uncovered **four material pricing & rounding bugs** in legacy v5 assumptions:
  1. **`takerBaseFee=1000` Ceiling Trap:** Gamma returns `takerBaseFee: 1000` (`10%` smart-contract ceiling) even on **`0%`-fee** markets (`feesEnabled: false`) and `3%–5%` markets; naive readers mistook `1000 bps` for a `10%` active fee!
  2. **13 Distinct Live `feeSchedule` Curves (Incl. Quadratic `exp = 2`):** Live Polymarket runs 13 schedules (`zero_fees` `0%`, `esports_fees` `3%`, `sports_fees_v2` `3%`, `politics_fees` `4%`, `finance_prices_fees` `4%`, `macro_econ_fees` `4%`, `pop_culture_fees` `5%`, `sports_fees_v3` `5%`, `weather_fees`/`v2` `5%`, `crypto_fees_v2` `7%`, `crypto_hourly_fees` `10%`, and **`crypto_15_min` with `rate = 0.25, exponent = 2.0`**, i.e., `0.25 * (p * (1 - p))^2 = $0.015625/sh` at `p = 0.50`!).
  3. **Asymmetric Protocol V2 `BUY` Share-Haircut vs. `SELL` Cash-Deduction:** On V2 `BUY` taker fills, the fee is deducted in **outcome shares** (`net_delivered_shares = gross_shares * (1 - fee_per_sh / p)`), increasing effective buy cost per delivered share to $p_{\text{eff}}^{\text{buy}} = \frac{p}{1 - r [p(1-p)]^e / p}$, whereas `SELL` deducts USDC cash ($p_{\text{eff}}^{\text{sell}} = p - r [p(1-p)]^e$), and resting `Maker` fills pay **`0.0%` fee** (+ `15%–25%` maker rebate).
  4. **CLOB `<= 2`-Decimal USDC `makerAmount` Precision Rule:** On marketable `BUY` orders, `makerAmount = shares * price` MUST terminate in `<= 2` decimal places (`$0.01` cents), or `clob.polymarket.com` rejects the EIP-712 order with `HTTP 400` (`0.37 * 10.13 = 3.7481` -> rejected unless quantized to `10.00` shares = `$3.70`!).
- **Revised Classification:** `DEFECTIVE_IMPLEMENTATION_REPAIRED_OR_STAGED`
- **Research / Shadow / Live Impact:** `RESEARCH` & `SHADOW`: Evaluates all `199,841` fee-enabled markets accurately without false `takerBaseFee=1000` rejections or understated `BUY` share-haircuts. `LIVE`: Guarantees exact V2 net share pairing and zero `HTTP 400` precision rejections.
- **Real vs. Estimated Opportunity Cost:** **Measured Realized Impact:** `$0.5825` total realized fees across `79` pure-riskless live trades (`0.067%` of `$867.79` notional by prioritizing `0%` Maker / `zero_fees`). **Counterfactual Simulated Uplift:** Unlocks fee-bearing `CAL1` (`CAND_2`, `+$0.1009/batch` at `$48.70` NAV) and `99.4%` of active markets previously skipped by zero-fee-only scanners.
- **Recommended Modification:** Enforce [`verify_exact_polymarket_fee_and_rounding`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L923-L1014) (`Decimal` `ROUND_HALF_UP` to `5` decimals on fee USD, `0.001` tick at `p <= 0.04` or `p >= 0.96`, `gcd`-exact `<= 2`-decimal USDC share lot quantization).
- **Replacement Safety Control:** Source-verified `ExactFeeAndLotSpec` (`two_decimal_usdc_invariant_ok == True` + exact `net_delivered_shares_on_buy`).
- **Source-Code References:** [v6_restriction_and_capital_allocator.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L888-L1014), [universal_arb_verifier.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/universal_arb_verifier.py#L145-L235).
- **Tests & Proof:** `test_07_r21_wallet_capabilities_and_r23_protocol_v2_fees_and_rounding` (`takerBaseFee=1000` with `feesEnabled=False` -> `$0.00`; `crypto_15_min` `20 sh @ $0.50` -> `$0.3125` fee; `10.13 sh @ $0.37` -> quantized `10.00 sh`, `two_decimal_usdc_invariant_ok == True`).
- **Operational Status:** **IMPLEMENTED & VERIFIED** in `v6_restriction_and_capital_allocator.py` & `universal_arb_verifier.py`.
- **Remaining External Dependencies:** External Polymarket `feeSchedule` parameters (read dynamically per market from Gamma).

---

### `R-24` — Non-Atomic Multi-Market CLOB Matching & Partial-Fill Construction Risk
- **Original Restriction & Rationale:** v5.0 `PROVIDER_CONTRACTUAL` — Separate `condition_id` orders on `clob.polymarket.com` match sequentially, creating partial-fill legging risk (`UNWRESID`) when one leg races.
- **Verified Current Behavior:** Confirmed external matching architecture. Crucially, v6.0 enforces Prompt §3's rule: **never confuse a nominally riskless terminal payoff (`CLASS_B`) with riskless order construction (`CLASS_A`)**! [`DynamicMarginalCapitalAllocator._unit_realizable_net_edge`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L1327-L1336) explicitly deducts `partial_fill_prob * unwind_loss_per_share_if_partial_usd` from `worst_case_net_payoff_per_share_usd` before ranking or admitting any non-atomic multi-leg box, and `HedgedMakerShadowQuoter` simulates forward-fill & adverse-jump dynamics in `SHADOW`.
- **Revised Classification:** `PHYSICAL_OR_EXCHANGE_CONSTRAINT_OPTIMIZED_AROUND`
- **Research / Shadow / Live Impact:** `RESEARCH`: Classifies atomic (`CLASS_A`) vs sequential (`CLASS_B`) explicitly. `SHADOW`: Deducts empirical partial-fill unwind EV (`CAND_5`: `$0.0190 - 0.18 * $0.040 = +$0.0118/sh`). `LIVE`: Quarantines `>=3` sequential legs below `$500` NAV (`R-40` / `D-007`), walks multi-rung L2 depth with cushion on 2-leg `CLASS_B`, and prioritizes atomic on-chain `splitPosition` / `mergePositions` / `convertPositions` (`CLASS_A`).
- **Real vs. Estimated Opportunity Cost:** **Measured Realized Impact:** `$0.00` loss across `79` post-lock 1- and 2-leg riskless trades (`100.0%` WR), whereas one pre-lock `KMIA` `>=3`-leg `UNWRESID` (`17.0 YES` shares in `6707502`) froze `$16.83` inside the `$50.51` dispute.
- **Recommended Modification:** Retain explicit construction-risk haircut `p_partial * L_unwind` in `DynamicMarginalCapitalAllocator` + atomic on-chain preference.
- **Replacement Safety Control:** `CLASS_A` vs `CLASS_B` separation + `partial_fill_prob * unwind_loss_per_share_if_partial_usd` deduction + `D-007` `<$500` `>=3`-leg live quarantine.
- **Source-Code References:** [v6_restriction_and_capital_allocator.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L1327-L1336), [stage_c_zero_loss_velocity.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/stage_c_zero_loss_velocity.py#L369-L478).
- **Tests & Proof:** `TestFullThrottlePipelineAndDashboard.test_10` + `TestV60RestrictionReassessmentAndAllocator.test_06` (`PASS`).
- **Operational Status:** **IMPLEMENTED & ACTIVE**.
- **Remaining External Dependencies:** External CLOB per-market orderbook engine.

---

### `R-25` — Provider Public & Authenticated API Rate Limits & Data-License Conditions
- **Original Restriction & Rationale:** v5.0 `PROVIDER_CONTRACTUAL` — Cloudflare/API gateways (`gamma-api`, `clob.polymarket.com`, `api.sx.bet` `500/60s`, `predict.fun`, `limitless`) enforce rate limits (`HTTP 429`) and market-data usage terms.
- **Verified Current Behavior:** Prompt §4 explicitly mandates: *"Research automation must also respect applicable market-data licenses, API conditions and rate limits."* Verified enforced in ALL 3 modes (`RESEARCH`, `SHADOW`, `LIVE`) via [`evaluate_mode_specific_eligibility`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L144-L150), token-bucket / batch `/books` pagination (`500` tokens/call -> `22,000` books in `44` HTTP calls with `0` `429`s in `scans_ab_c_j`!), WebSocket push subscriptions, and hot/warm/cold rotation (`200,279` cold tokens rotated without hammering REST).
- **Revised Classification:** `PHYSICAL_OR_EXCHANGE_CONSTRAINT_OPTIMIZED_AROUND`
- **Research / Shadow / Live Impact:** Enforced across **all 3 modes** (`RESEARCH`, `SHADOW`, `LIVE`); tiered WebSocket + batch `/books` achieves `100%` `201,012`-market discovery with `0.0%` `HTTP 429` errors.
- **Real vs. Estimated Opportunity Cost:** **`$0.00`** when batch `/books` + `DormantOpportunityStore` event-driven wakeup (`9,139` events -> `254` targeted rescans) is used instead of brute-force polling.
- **Recommended Modification:** Retain `api_license_and_rate_limit_ok` hard check across all modes + `DormantOpportunityStore` near-arb wakeup architecture.
- **Replacement Safety Control:** `BudgetManager.check_api_rate_limit` + `evaluate_mode_specific_eligibility(api_license_and_rate_limit_ok=...)`.
- **Source-Code References:** [v6_restriction_and_capital_allocator.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L144-L150), [paa_autonomy_config.json](file:///C:/Users/Anton/source/repos/Dominus/config/paa_autonomy_config.json#L72-L77).
- **Tests & Proof:** `test_01_mode_specific_separation_and_non_overridable_legal_gates` (`api_license_and_rate_limit_ok=False` rejected in `SHADOW`/`RESEARCH`).
- **Operational Status:** **ENFORCED ACROSS ALL MODES**.
- **Remaining External Dependencies:** Provider API terms of service.

---

### `R-26` — Polymarket International `CA-ON` / Server-IP Eligibility (`D-011` Owner Sovereignty & Verified External Scope)
- **Original Restriction & Rationale:** v5.0 `JURISDICTIONAL` — Polymarket ToS & April 2025 Ontario Securities Commission settlement restrict retail `CA-ON` persons and `US`/`UK`/`FR` order-originating server IPs from `POST /order`, while public `gamma-api` & CLOB `/book` / WS remain open.
- **Verified Current Behavior:** **Distinguishing Verified External Restriction vs. Assumption (`D-011`):** (1) **Verified External Facts:** Polymarket's edge HTTP gateway geoblocks `US`/`UK`/`FR` order-originating server IPs (`HTTP 403`), leaves public `gamma-api`/CLOB `/books`/WS open globally, and on `kraken-finland` (`FI`) currently accepts authenticated `sig_type=3` CLOB & Relayer V2 requests from Funder Beacon `0x013A...F4e9` (`79W / 0L` filled riskless trades). (2) **Prior Unverified Assumptions Removed:** Blanket AI assumptions about the Owner's personal/entity compliance posture — or AI-imposed discretionary delays on Owner-authorized `0x013A...F4e9` operations — are eliminated (`assess_r26_to_r32_venue_restrictions["R-26"]`).
- **Revised Classification:** `OWNER_SOVEREIGN_EXTERNAL_CONSTRAINT_ADVISORY`
- **Research / Shadow / Live Impact:** `RESEARCH` & `SHADOW`: `100%` open across all `375,355` markets. `LIVE`: **Owner retains exclusive final authority** (`owner_explicitly_authorized=True` executes technically feasible & permitted actions in a single pass). If Polymarket's external API or compliance gate rejects an order/account (`venue_live_authorized_for_jurisdiction=False`), the engine **never silently disables** — it emits `ExternalBlockerReport("R-26")` with exact blocker + lawful remedies.
- **Real vs. Estimated Opportunity Cost:** **`$0.00`** internal friction on `RESEARCH`, `SHADOW`, or Owner-authorized `LIVE` execution.
- **Recommended Modification:** Enforce `D-011` via [`assess_r26_to_r32_venue_restrictions`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L140-L315) and [`evaluate_mode_specific_eligibility`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L318-L492): execute Owner-authorized `0x013A...F4e9` operations without repeated prompts; surface explicit external blockers and lawful remedies (`Polymarket institutional/compliance clearance`, `ForecastEx / IBKR Canada`, `STX Ontario`) whenever an external gate applies.
- **Replacement Safety Control:** `ExternalBlockerReport(silent_disable_permitted=False)` + unattended-worker safeguard (`owner_explicitly_authorized=False` default for background cron tasks).
- **Source-Code References:** [v6_restriction_and_capital_allocator.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L140-L185) & [#L318-L492](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L318-L492), [cross_venue_shadow_deployment_gates.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_shadow_deployment_gates.py#L988-L1068).
- **Tests & Proof:** `test_01` + `test_10_owner_sovereignty_r26_to_r32_verified_vs_assumed_and_single_pass_execution` (`PASS`).
- **Operational Status:** **IMPLEMENTED & VERIFIED (`D-011` OWNER SOVEREIGNTY ACTIVE)**.
- **Remaining External Dependencies:** External Polymarket API acceptance & provider account/compliance terms (`Owner-governed`).

---

### `R-27` — Limitless Exchange (`Street Chow Inc.` ToS §1) External Trading Onboarding & Lawful Remedies
- **Original Restriction & Rationale:** v5.0 `JURISDICTIONAL` — Street Chow Inc. ToS §1 restricts `TRADING` & `ACCOUNT_PRIVATE` endpoints for `CA-ON`, `CA-AB`, and `US` persons without institutional onboarding, while keyless public REST & Socket.IO WS are open.
- **Verified Current Behavior:** **Verified External Gate vs. AI Heuristic:** Keyless public REST (`api.limitless.exchange`) and Socket.IO L2 streams are verified open (`PUBLIC_DATA_AUTHORIZED`); authenticated trading requires an EIP-712 session + ToS §1 eligibility. Any `$10,000` NAV deferral cited in v5.0 is reclassified strictly as a **non-binding economic advisory estimate**, NEVER a binding restriction on the Owner.
- **Revised Classification:** `OWNER_SOVEREIGN_EXTERNAL_CONSTRAINT_ADVISORY`
- **Research / Shadow / Live Impact:** `RESEARCH` & `SHADOW`: `100%` unlocked keyless L2 data. `LIVE`: Executes immediately upon Owner provisioning an onboarded Limitless session; if unprovisioned or externally restricted, emits `ExternalBlockerReport("R-27")` (`silent_disable_permitted=False`) with lawful onboarding remedies.
- **Real vs. Estimated Opportunity Cost:** **`$0.00`** internal AI drag (`0` silent suppression).
- **Recommended Modification:** Keep keyless `RESEARCH`/`SHADOW` active; present lawful remedies (written institutional compliance onboarding with Street Chow Inc., or routing regulated legs via `ForecastEx / IBKR Canada` & `STX Ontario`) for Owner decision.
- **Replacement Safety Control:** `ExternalBlockerReport("R-27", silent_disable_permitted=False)` + zero-key shadow isolation (`R-37`) until Owner provisions live credentials.
- **Source-Code References:** [v6_restriction_and_capital_allocator.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L186-L209), [cross_venue_shadow_deployment_gates.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_shadow_deployment_gates.py#L1102-L1209).
- **Tests & Proof:** `test_10_owner_sovereignty_r26_to_r32_verified_vs_assumed_and_single_pass_execution` (`PASS`).
- **Operational Status:** **IMPLEMENTED & VERIFIED (`D-011`)**.
- **Remaining External Dependencies:** Street Chow Inc. account/institutional onboarding if Owner selects Limitless for live execution.

---

### `R-28` — Predict.fun (`PDF Labs Limited` ToS §1) `Content` vs. `Technology Features` API Gate
- **Original Restriction & Rationale:** v5.0 `JURISDICTIONAL` — PDF Labs Limited ToS §1 explicitly authorizes `Content Features` (Mainnet REST + WS market data) in Restricted Jurisdictions (`CA-ON`) while restricting `Technology Features` (`POST /v1/auth` & `POST /v1/orders`) without provider clearance and `X-API-Key`.
- **Verified Current Behavior:** **Verified External Gate vs. AI Heuristic:** Mainnet `Content Features` shadow feed is verified `AUTHORIZED_LIVE` with `0` wallet keys; `POST /v1/orders` requires an issued `X-API-Key` + JWT wallet auth under `Technology Features`. Prior `$253`/`$10,000` NAV gates are strictly advisory and non-binding on the Owner.
- **Revised Classification:** `OWNER_SOVEREIGN_EXTERNAL_CONSTRAINT_ADVISORY`
- **Research / Shadow / Live Impact:** `RESEARCH` & `SHADOW`: `100%` authorized `Content Features`. `LIVE`: Never silently disabled — reports exact `Technology Features` / `X-API-Key` external blocker and lawful remedy (`PDF Labs Limited` institutional clearance + API key) until Owner provisions credentials.
- **Real vs. Estimated Opportunity Cost:** **`$0.00`** internal friction.
- **Recommended Modification:** Maintain continuous `Content Features` `RESEARCH`/`SHADOW` ingestion; execute live `predict.fun` orders immediately in a single pass if and when Owner supplies authorized `X-API-Key` + wallet session.
- **Replacement Safety Control:** `ExternalBlockerReport("R-28", silent_disable_permitted=False)` + `validate_shadow_env_dict` (`R-37`).
- **Source-Code References:** [v6_restriction_and_capital_allocator.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L210-L231), [cross_venue_shadow_deployment_gates.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_shadow_deployment_gates.py#L1243-L1360).
- **Tests & Proof:** `test_10_owner_sovereignty_r26_to_r32_verified_vs_assumed_and_single_pass_execution` (`PASS`).
- **Operational Status:** **IMPLEMENTED & VERIFIED (`D-011`)**.
- **Remaining External Dependencies:** PDF Labs Limited `X-API-Key` & `Technology Features` onboarding if selected by Owner.

---

### `R-29` — SX Bet (`sx.bet` Terms & IP Geofence) External Wagering Gate & Lawful Alternatives
- **Original Restriction & Rationale:** v5.0 `JURISDICTIONAL` — `sx.bet` restricts `CA-ON` residents and `US`/`UK` IPs on `POST /orders-v3`, while OBv3 public REST is open.
- **Verified Current Behavior:** **Verified External Gate vs. Assumption:** Unauthenticated OBv3 REST orderbooks poll cleanly from `FI`; `POST /orders-v3` enforces external account/IP eligibility. AI capital-tier preferences impose zero discretionary block on Owner venue choice.
- **Revised Classification:** `OWNER_SOVEREIGN_EXTERNAL_CONSTRAINT_ADVISORY`
- **Research / Shadow / Live Impact:** `RESEARCH` & `SHADOW`: Public OBv3 feed active (`500/60s` rate limit respected). `LIVE`: Reports `ExternalBlockerReport("R-29")` + lawful remedies (`SX Bet` institutional compliance onboarding or regulated Ontario sports/event execution on `STX Ontario`) rather than silently disabling.
- **Real vs. Estimated Opportunity Cost:** **`$0.00`** internal friction.
- **Recommended Modification:** Retain OBv3 `RESEARCH`/`SHADOW` feed and report exact external blocker + regulated `STX Ontario` alternative whenever `sx_bet` live execution is queried without an onboarded account.
- **Replacement Safety Control:** `ExternalBlockerReport("R-29", silent_disable_permitted=False)`.
- **Source-Code References:** [v6_restriction_and_capital_allocator.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L232-L250), [cross_venue_shadow_deployment_gates.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_shadow_deployment_gates.py#L1365-L1474).
- **Tests & Proof:** `test_10_owner_sovereignty_r26_to_r32_verified_vs_assumed_and_single_pass_execution` (`PASS`).
- **Operational Status:** **IMPLEMENTED & VERIFIED (`D-011`)**.
- **Remaining External Dependencies:** SX Bet compliance onboarding if selected by Owner.

---

### `R-30` — STX Ontario (`AGCO` / `iGaming Ontario`) Physical Ontario Execution Endpoint Requirement
- **Original Restriction & Rationale:** v5.0 `JURISDICTIONAL` — Personal `on.stxapp.ca` trading IS **legally authorized for `CA-ON` residents**, while `iGaming Ontario` (`iGO`) geolocation rules require authenticated personal orders to originate physically inside Ontario (`CA-ON`), rejecting live personal orders sent from the Finland (`FI`) VM.
- **Verified Current Behavior:** **Challenged & Refined under `D-011`:** (1) **Verified External Geofence:** `on.stxapp.ca` rejects personal live orders from `server_region == "FI"` due to `iGO` physical-Ontario geolocation rules, while unsigned Phoenix WS streams live L2 orderbooks to `FI` cleanly. (2) **Discretionary AI Cap Removed:** Prior v5.0/v6.0 prose tied STX Ontario activation to a `$500` NAV threshold — that `$500` figure is purely a **non-binding advisory efficiency estimate**, NOT a gate! The Owner has full authority to execute STX Ontario live trades from a physical `CA-ON` workstation at **any** bankroll size whenever desired.
- **Revised Classification:** `OWNER_SOVEREIGN_EXTERNAL_CONSTRAINT_ADVISORY`
- **Research / Shadow / Live Impact:** `RESEARCH` & `SHADOW`: Live STX L2 orderbook streaming active on `FI` (`0%` blocked). `LIVE`: **Permitted & legally authorized in `CA-ON`** — executes in a single pass from a physical `CA-ON` host once Owner supplies STX credentials; if invoked on `FI`, explicitly reports the `iGO` `FI`-IP geofence blocker and the native `CA-ON` execution remedy (`0` silent disabling).
- **Real vs. Estimated Opportunity Cost:** **`$0.00`** internal AI friction; direct regulated `CA-ON` live venue available at Owner's discretion.
- **Recommended Modification:** Remove any binding `$500` NAV lock on STX Ontario; support native `CA-ON` endpoint execution whenever authorized by the Owner while keeping `FI` read-only on Phoenix WS.
- **Replacement Safety Control:** `ExternalBlockerReport("R-30", verification_basis=VERIFIED_REGULATORY_GEOFENCE, silent_disable_permitted=False)` when `server_region != "CA-ON"`.
- **Source-Code References:** [v6_restriction_and_capital_allocator.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L251-L276), [cross_venue_shadow_deployment_gates.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_shadow_deployment_gates.py#L760-L849).
- **Tests & Proof:** `test_10_owner_sovereignty_r26_to_r32_verified_vs_assumed_and_single_pass_execution` (`PASS`).
- **Operational Status:** **IMPLEMENTED & VERIFIED (`CA-ON` NATIVE EXECUTION AUTHORIZED AT OWNER DISCRETION)**.
- **Remaining External Dependencies:** Physical `CA-ON` execution host + Owner's STX Ontario account credentials (`R-19`).

---

### `R-31` — Corporate Entity Incorporation & Institutional KYB (`DOMINUS_KYB_REFERENCE_ID`) — Advisory Economics vs. Owner Authority
- **Original Restriction & Rationale:** v5.0 `KYC_KYB` — Institutional KYB (`DOMINUS_KYB_REFERENCE_ID`) is required by external venues to onboard corporate trading accounts; legal formation + annual KYB maintenance typically costs `$1,500–$5,000+/yr`.
- **Verified Current Behavior:** **Overturned AI-Imposed "Hard-Deferral" (`D-011`):**
  1. **Verified External Requirement:** External venues require completed institutional KYB review and issued corporate credentials before a corporate entity can trade live, and evaluate beneficial ownership, control (`mind and management`), and trader location during that review.
  2. **Eliminated AI Assumptions & Paternalistic Locks:** (a) The `$10,000` NAV threshold is **strictly an advisory ROI break-even calculation** (`$1,500–$5,000/yr` fee vs portfolio size), **NOT** a binding rule — the Owner holds sole authority over whether and when to form an entity or submit KYB inquiries! (b) Neither blanket "incorporation automatically bypasses everything" NOR blanket "incorporation can never qualify" is assumed — actual eligibility is determined by transparent written inquiry to each venue's compliance team (`docs/KYB_AND_API_ONBOARDING_DOSSIERS.md`).
- **Revised Classification:** `OWNER_SOVEREIGN_EXTERNAL_CONSTRAINT_ADVISORY`
- **Research / Shadow / Live Impact:** `RESEARCH` & `SHADOW`: `$0` cost and `0%` blockage. `LIVE`: Zero AI-imposed NAV lock; if a corporate venue path lacks `DOMINUS_KYB_REFERENCE_ID` / venue credentials, reports exact KYB credential blocker + `$0`-cost pre-incorporation compliance inquiry dossier (`0` silent disabling).
- **Real vs. Estimated Opportunity Cost:** Advisory insight highlights `$1,500–$5,000/yr` fixed legal outlay vs `$48.70` current cash while leaving timing `100%` in the Owner's hands.
- **Recommended Modification:** Replace `"HARD-DEFERRED TO $10,000+ NAV"` with advisory break-even guidance + ready-to-send pre-incorporation compliance inquiry templates ([KYB_AND_API_ONBOARDING_DOSSIERS.md](file:///C:/Users/Anton/source/repos/Dominus/docs/KYB_AND_API_ONBOARDING_DOSSIERS.md)) + zero-overhead `CA-ON`-regulated alternatives (`ForecastEx / IBKR Canada`, `STX Ontario`).
- **Replacement Safety Control:** `ExternalBlockerReport("R-31", verification_basis=VERIFIED_EXTERNAL_CREDENTIAL_OR_KYB_GATE, silent_disable_permitted=False)`.
- **Source-Code References:** [v6_restriction_and_capital_allocator.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L277-L299), [KYB_AND_API_ONBOARDING_DOSSIERS.md](file:///C:/Users/Anton/source/repos/Dominus/docs/KYB_AND_API_ONBOARDING_DOSSIERS.md).
- **Tests & Proof:** `test_10_owner_sovereignty_r26_to_r32_verified_vs_assumed_and_single_pass_execution` (`PASS`).
- **Operational Status:** **IMPLEMENTED & VERIFIED (`ADVISORY ONLY — OWNER SOVEREIGN`)**.
- **Remaining External Dependencies:** External venue KYB review if and when initiated by the Owner.

---

### `R-32` — STX Partner Portal `Data` Track Token (`apps.stxapp.io` `STX_APPS_DATA_TOKEN`)
- **Original Restriction & Rationale:** v5.0 `KYC_KYB` — Cloud-hosted REST calls from `FI` to `api.on.stxapp.ca/api/v1/*` return HTTP `401`/`403` without an institutional `Data` partner token (`STX_APPS_DATA_TOKEN`), whereas unsigned Phoenix WS already streams live public L2 books.
- **Verified Current Behavior:** **Verified External API Credential Gate:** Verified in [KYB_AND_API_ONBOARDING_DOSSIERS.md](file:///C:/Users/Anton/source/repos/Dominus/docs/KYB_AND_API_ONBOARDING_DOSSIERS.md#L34-L37) that `api.on.stxapp.ca` cloud REST requires `STX_APPS_DATA_TOKEN` (`Data` scope: market-data reads, distinct from `Trading` scope), while unsigned Phoenix WS streams live STX orderbooks today without any token. Zero internal AI restriction applies: if the Owner provisions `STX_APPS_DATA_TOKEN`, cloud REST activates immediately.
- **Revised Classification:** `OWNER_SOVEREIGN_EXTERNAL_CONSTRAINT_ADVISORY`
- **Research / Shadow / Live Impact:** `RESEARCH` & `SHADOW`: Phoenix WS active today (`0%` blocked); cloud REST activates automatically upon `STX_APPS_DATA_TOKEN` provisioning. `LIVE`: Governed by `R-30` (`CA-ON` native host or `Trading` partner track).
- **Real vs. Estimated Opportunity Cost:** **`$0.00`**.
- **Recommended Modification:** Keep Phoenix WS active; surface explicit `ExternalBlockerReport("R-32")` pointing to free `https://apps.stxapp.io` `Data` token registration whenever cloud REST catalog endpoints are requested without a token.
- **Replacement Safety Control:** `ExternalBlockerReport("R-32", silent_disable_permitted=False)` + scope distinction (`Data` read vs `Trading` order placement).
- **Source-Code References:** [v6_restriction_and_capital_allocator.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L300-L315), [cross_venue_shadow_deployment_gates.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_shadow_deployment_gates.py#L785-L849).
- **Tests & Proof:** `test_10_owner_sovereignty_r26_to_r32_verified_vs_assumed_and_single_pass_execution` (`PASS`).
- **Operational Status:** **IMPLEMENTED & VERIFIED (`OPTIONAL EXTERNAL TOKEN — ZERO AI FRICTION`)**.
- **Remaining External Dependencies:** STX Partner Portal (`apps.stxapp.io`) token issuance if requested by Owner.

---

### `R-33` — Anti-Self-Approval, Protected-File Lock & Credential/Transfer Injection Hard Block
- **Original Restriction & Rationale:** v5.0 `ESSENTIAL_SAFETY` — Blocks autonomous diffs touching `data/polymarket/paa/approvals/`, the 16 `protected_files`, `.env`/`.key`/`.pem`, or forbidden credential/transfer substrings.
- **Verified Current Behavior:** Verified intact at [permissions.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L161-L210) & [#L316-L410](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L316-L410). Zero false positives on legitimate modular strategy/allocator code (`src/polymarket_research/v6_restriction_and_capital_allocator.py` passes `(True, [])`).
- **Revised Classification:** `ESSENTIAL_INTEGRITY_PROTECTION_RETAINED`
- **Research / Shadow / Live Impact:** `0%` suppression of legitimate `RESEARCH`, `SHADOW`, or owner-approved `LIVE` strategies; `100%` prevention of autonomous self-approval or key exfiltration.
- **Real vs. Estimated Opportunity Cost:** **`$0.00`**.
- **Recommended Modification:** **Retain permanently at `100%` strength** (`0` weakening).
- **Replacement Safety Control:** Retained as primary control (`PermissionGate.inspect_candidate_diff`).
- **Source-Code References:** [permissions.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L161-L410), [paa_autonomy_config.json](file:///C:/Users/Anton/source/repos/Dominus/config/paa_autonomy_config.json#L98-L122).
- **Tests & Proof:** `test_09_zero_trust_permission_gate_and_lf_hygiene_all_v6_deliverables` (`(True, [])`, `PASS`).
- **Operational Status:** **RETAINED PERMANENTLY**.
- **Remaining External Dependencies:** None.

---

### `R-34` — Subprocess Secret Stripping & Detached Git Worktree Sandboxing
- **Original Restriction & Rationale:** v5.0 `ESSENTIAL_SAFETY` — `build_isolated_worker_env` strips all signing keys/secrets and sets `PAA_SIGNING_DISABLED="1"` + `PAA_WORKER_ROLE` inside detached worktrees.
- **Verified Current Behavior:** Verified intact in [permissions.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L43-L94) and extended in [paa_cli.py](file:///C:/Users/Anton/source/repos/Dominus/scripts/paa_cli.py#L686-L695) so isolated workers are also hard-blocked (`rc=3`) from invoking `paa_cli.py approvals {grant,revoke,consume}`.
- **Revised Classification:** `ESSENTIAL_INTEGRITY_PROTECTION_RETAINED`
- **Research / Shadow / Live Impact:** Zero friction on `RESEARCH`/`SHADOW`; prevents compromised worker prompts from signing orders or minting approvals.
- **Real vs. Estimated Opportunity Cost:** **`$0.00`**.
- **Recommended Modification:** **Retain permanently** (reinforced with `paa_cli.py` worker block).
- **Replacement Safety Control:** `build_isolated_worker_env` + `_verify_human_owner_cli_session`.
- **Source-Code References:** [permissions.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L43-L94), [paa_cli.py](file:///C:/Users/Anton/source/repos/Dominus/scripts/paa_cli.py#L686-L695).
- **Tests & Proof:** `test_05_r05_r08_paa_cli_approvals_selective_cancel_and_safeguard_resume` (`rc_worker == 3`, `PASS`).
- **Operational Status:** **RETAINED & REINFORCED**.
- **Remaining External Dependencies:** None.

---

### `R-35` — `<UNTRUSTED_DATA_ONLY>` Prompt-Injection Sanitizer & Independent QA/Canary Verifier
- **Original Restriction & Rationale:** v5.0 `ESSENTIAL_SAFETY` — Wraps external market text in `<UNTRUSTED_DATA_ONLY>` sanitizers and runs independent `ZeroTrustVerifier` QA outside worker control.
- **Verified Current Behavior:** Verified active in [zero_trust.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/zero_trust.py#L38-L82) & [#L593-L774](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/zero_trust.py#L593-L774); Polymarket market descriptions (`375,355` user/creator-authored strings) routinely contain adversarial or ambiguous phrasing, making prompt sanitization essential.
- **Revised Classification:** `ESSENTIAL_INTEGRITY_PROTECTION_RETAINED`
- **Research / Shadow / Live Impact:** `0%` economic drag; protects LLM research agents and candidate promotion integrity.
- **Real vs. Estimated Opportunity Cost:** **`$0.00`**.
- **Recommended Modification:** **Retain permanently.**
- **Replacement Safety Control:** `ZeroTrustVerifier` + `<UNTRUSTED_DATA_ONLY>` sanitizer.
- **Source-Code References:** [zero_trust.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/zero_trust.py#L38-L82) & [#L593-L774](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/zero_trust.py#L593-L774).
- **Tests & Proof:** Covered by `ZeroTrustVerifier` & `TestStageCZeroLossVelocity.test_05` suites.
- **Operational Status:** **RETAINED PERMANENTLY**.
- **Remaining External Dependencies:** None.

---

### `R-36` — Cross-Venue & Cross-Market Double-Zero Settlement Equivalence Verifier
- **Original Restriction & Rationale:** v5.0 `ESSENTIAL_SAFETY` — `CrossVenueRuleVerifier` 5-gate check blocks pairs with mismatched oracle families, inverted strike directions, overtime/tie divergence, or deadline mismatches.
- **Verified Current Behavior:** Verified in [cross_venue_shadow_deployment_gates.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_shadow_deployment_gates.py#L1852-L2053) and intra-Polymarket `universal_arb_verifier.py`. Empirical proof from our full-universe scan ([scans_d_to_i/scan_summary.json](file:///C:/Users/Anton/source/repos/Dominus/data/full_throttle/scans_d_to_i/scan_summary.json)): **`78,696` apparent cross-market spreads were rule-mismatched false arbs** (e.g., `2025` vs `2026` deadlines, `regular time` vs `incl. OT`, `intraday touch` vs `closing settle`, `negRiskAugmented` placeholders) where both legs can resolve `$0.00`!
- **Revised Classification:** `ESSENTIAL_INTEGRITY_PROTECTION_RETAINED`
- **Research / Shadow / Live Impact:** `RESEARCH`: Classifies rule-mismatched pairs transparently as `CLASS_D` (`Rule-Mismatched / Ambiguous`) instead of silently dropping them, preserving full visibility while preventing `-100%` Double-Zero losses in `SHADOW` (`CLASS_A/B`) and `LIVE`.
- **Real vs. Estimated Opportunity Cost:** **`$0.00` lost true arb EV**; **prevents `-100%` principal wipeout** across `78,696` false-arb traps!
- **Recommended Modification:** **Retain permanently** across all intra-venue and cross-venue multi-contract detectors.
- **Replacement Safety Control:** 5-gate `CrossVenueRuleVerifier` + `verify_independent_payoff_admission` (`R-02`).
- **Source-Code References:** [cross_venue_shadow_deployment_gates.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_shadow_deployment_gates.py#L1852-L2053), [universal_arb_verifier.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/universal_arb_verifier.py#L240-L420).
- **Tests & Proof:** `TestFullThrottlePipelineAndDashboard.test_08_ambiguous_hit_barrier_guard_and_negative_shadow_ev_rejection` (`PASS`).
- **Operational Status:** **RETAINED PERMANENTLY**.
- **Remaining External Dependencies:** None.

---

### `R-37` — Zero-Signing-Key Shadow `.env` Validator (`0600` POSIX + Revoked Key SHA-256 Blocklist)
- **Original Restriction & Rationale:** v5.0 `ESSENTIAL_SAFETY` — `validate_shadow_env_dict` ensures `/etc/polymarket-shadow.env` holds zero signing keys/mnemonics and `0600` POSIX permissions.
- **Verified Current Behavior:** Verified intact in [cross_venue_shadow_deployment_gates.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_shadow_deployment_gates.py#L1632-L1778). Guarantees mathematically that `SHADOW` and `RESEARCH` daemons are physically incapable of signing or transmitting live orders.
- **Revised Classification:** `ESSENTIAL_INTEGRITY_PROTECTION_RETAINED`
- **Research / Shadow / Live Impact:** Enforces physical air-gap between `RESEARCH`/`SHADOW` and `LIVE` (`0%` opportunity loss).
- **Real vs. Estimated Opportunity Cost:** **`$0.00`**.
- **Recommended Modification:** **Retain permanently.**
- **Replacement Safety Control:** `validate_shadow_env_dict`.
- **Source-Code References:** [cross_venue_shadow_deployment_gates.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_shadow_deployment_gates.py#L1632-L1778).
- **Tests & Proof:** Verified in Stage G security unit tests.
- **Operational Status:** **RETAINED PERMANENTLY**.
- **Remaining External Dependencies:** None.

---

### `R-38` — On-Chain Wallet-to-Ledger Accounting Integrity Safeguard (`> $1.50` Cash / `> 0.75` Share Drift Halt)
- **Original Restriction & Rationale:** v5.0 `ESSENTIAL_SAFETY` — `PAAAccountant` engages `ACCOUNTING_SAFEGUARD_ACTIVE.json` if on-chain `pUSD` diverges from `live_bankroll` by `> $1.50` or ERC-1155 shares diverge by `> 0.75`.
- **Verified Current Behavior:** Verified intact at [accountant.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/accountant.py#L206-L365) (`$0.000000` current drift on `$48.695132` `pUSD`), and **strengthened in v6.0** by wiring `paa_cli.py resume --include-trading` (`R-08`) to check `ACCOUNTING_SAFEGUARD_ACTIVE.json` before clearing `KILL_SWITCH`!
- **Revised Classification:** `ESSENTIAL_INTEGRITY_PROTECTION_RETAINED`
- **Research / Shadow / Live Impact:** `0%` false-positive drag when reconciled; catches state corruption or unrecorded fills immediately in `LIVE`.
- **Real vs. Estimated Opportunity Cost:** **`$0.00`**.
- **Recommended Modification:** **Retain permanently** (now coupled with `paa_cli.py resume` safeguard check).
- **Replacement Safety Control:** `PAAAccountant` + `LossCauseAwareCapitalController` + `paa_cli.cmd_resume`.
- **Source-Code References:** [accountant.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/accountant.py#L206-L365), [paa_cli.py](file:///C:/Users/Anton/source/repos/Dominus/scripts/paa_cli.py#L610-L627).
- **Tests & Proof:** `test_05_r05_r08_paa_cli_approvals_selective_cancel_and_safeguard_resume` (`PASS`).
- **Operational Status:** **RETAINED & STRENGTHENED**.
- **Remaining External Dependencies:** Polygon RPC read availability.

---

### `R-39` — Unhedged Directional Suspension Below `$150` NAV (`riskless_only_mode: true`) — Split by Mode
- **Original Restriction & Rationale:** v5.0 `JUSTIFIED_RISK_LIMIT` — Suspended unhedged directional trading below `$150` NAV (`riskless_only_mode: true`).
- **Verified Current Behavior:** **Challenged & Refined in v6.0:** In `LIVE` execution at `$48.70` cash, `$5`–`$8` minimum CLOB directional clips represent `10.3%`–`16.4%` of total bankroll per bet (`3x`–`5x` above optimal Half-Kelly sizing!), and the empirical closed ledger proves `41` retired directional/lattice trades lost **`-$73.3385`** (`30W / 11L`) whereas `79` pure-riskless trades made **`+$18.2461`** (`79W / 0L`). **HOWEVER**, applying `$150` capital-only gates inside `RESEARCH` or `SHADOW` modes suppresses WFO sample accumulation (`N >= 50` across `CPCV(6,2)`), creating a chicken-and-egg deadlock where strategies can never prove readiness before `$150` NAV!
- **Revised Classification:** `MODE_COUPLED_OVERBROAD_SPLIT_BY_MODE`
- **Research / Shadow / Live Impact:** `RESEARCH` & `SHADOW`: **100% UNLOCKED** at any wallet NAV (`$48.70` included) — `CLASS_C` bounded-risk carries and directional WFO candidates are scored and logged continuously (`test_01`, `test_06`). `LIVE`: **STRICTLY RETAINED** until undisputed reconciled NAV `>= $150.00` **AND** Purged WFO passes (`N >= 50`, `PF >= 1.45`, `CI95_lo > 0`, `PBO <= 0.20`) **AND** owner grants `NEW_LIVE_TRADING_ACTIVATION`.
- **Real vs. Estimated Opportunity Cost:** **Measured Realized Savings in `LIVE`:** Avoided repeating **`-$73.3385`** historical directional drawdown (`+$18.25` pure-riskless realized since lock). **Shadow Coverage Gain:** `+756` `CLASS_C` structured carries tracked in `scans_d_to_i` instead of dropped!
- **Recommended Modification:** Enforce [`evaluate_mode_specific_eligibility`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L183-L255): admit `CLASS_C` in `RESEARCH` & `SHADOW` unconditionally on bankroll; enforce `$150` NAV + `directional_wfo_certified` + owner approval in `LIVE`.
- **Replacement Safety Control:** Mode-split `LIVE_DIRECTIONAL_OR_CARRY_CERTIFICATION_GATE` (`LIVE` only) + Purged `CPCV(6,2)` WFO gate.
- **Source-Code References:** [polymarket_strategy_and_risk.json](file:///C:/Users/Anton/source/repos/Dominus/config/polymarket_strategy_and_risk.json#L20-L24), [v6_restriction_and_capital_allocator.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L183-L255).
- **Tests & Proof:** `test_01_mode_specific_separation_and_non_overridable_legal_gates` (`CLASS_C` allowed at `$48.70` in `RESEARCH` & `SHADOW`, blocked in `LIVE`).
- **Operational Status:** **IMPLEMENTED & VERIFIED**.
- **Remaining External Dependencies:** Undisputed NAV `>= $150` + WFO empirical proof + human owner approval for `LIVE`.

---

### `R-40` — Sequential `>= 3`-Leg Bundle Quarantine Below `$500` NAV (`D-007`) — Split by Mode & Atomicity
- **Original Restriction & Rationale:** v5.0 `JUSTIFIED_RISK_LIMIT` — Blocked sequential `>= 3`-leg `MULTI_LEG_BUNDLE` orders below `$500` NAV (`D-007`).
- **Verified Current Behavior:** **Challenged & Refined in v6.0:** On `LIVE` sequential CLOB execution at `$48.70` cash, buying `>= 3` legs (including `$0.05`–`$0.08` tail outcomes requiring `13–20` shares to clear the `$1.00` CLOB notional floor, `R-22`) commits `$13–$20` (`27%–41%` of cash) with compounding partial-fill probability $1 - (1 - p_{\text{miss}})^k$ (`18%+` on 3 legs), directly causing historical `UNWRESID` bleed (`6707502`). **HOWEVER**, suppressing `>= 3`-leg slates in `RESEARCH` or `SHADOW` (`67` `>=3`-leg candidates in `dashboard_latest.json`!) hides genuine multi-outcome opportunities and prevents measuring exact partial-fill survival rates! Furthermore, demonstrably **atomic on-chain** `splitPosition`/`convertPositions` (`NR_M1`, `NR2`, `CLINCH_DEAD_SPLIT`) or verified-inventory-covered baskets have **`0.0%` naked legging risk** even below `$500` NAV!
- **Revised Classification:** `MODE_COUPLED_OVERBROAD_SPLIT_BY_MODE`
- **Research / Shadow / Live Impact:** `RESEARCH` & `SHADOW`: **100% UNLOCKED** at all NAVs (`CAND_5_SUB500_3LEG_SEQ` admitted in `RESEARCH` & `SHADOW` at `$48.70`, deducting `0.18 * $0.040 = $0.0072/sh` partial-fill penalty transparently). `LIVE`: Sequential `>=3`-leg CLOB bundles remain **hard-blocked below `$500` reconciled NAV** (`D-007`), while atomic on-chain / verified-inventory-backed conversions are permitted at `$48.70`, and `>= $500` `LIVE` unlocks ONLY with `certified_multileg_3plus_live_enabled == True`.
- **Real vs. Estimated Opportunity Cost:** **Measured Realized Protection in `LIVE`:** Prevents `$5`–`$17` `UNWRESID` unwind losses on `$48.70` cash. **Counterfactual Simulated Value at `$500` NAV:** Unlocks `+$0.2360/batch` net RNV (`CAND_5` at `$500.00` NAV in `run_v6_counterfactual_opportunity_audit.py`).
- **Recommended Modification:** Enforce mode- and atomicity-aware gating via [`evaluate_mode_specific_eligibility`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L196-L245) & [`check_multileg_3plus_nav_and_certification_gate`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/stage_c_zero_loss_velocity.py#L443-L479).
- **Replacement Safety Control:** `LIVE` `<$500` `D-007` quarantine on non-atomic `>=3`-leg CLOB loops + `verify_multileg_atomicity_or_inventory_cover` + `SHADOW` partial-fill EV haircut.
- **Source-Code References:** [stage_c_zero_loss_velocity.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/stage_c_zero_loss_velocity.py#L369-L479), [v6_restriction_and_capital_allocator.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L196-L245).
- **Tests & Proof:** `TestV5Section7RiskInvariants.test_02` + `TestV60RestrictionReassessmentAndAllocator.test_01` & `test_06` (`PASS`).
- **Operational Status:** **IMPLEMENTED & VERIFIED**.
- **Remaining External Dependencies:** Reconciled NAV `>= $500` + shadow execution certification + owner approval for sequential `>=3`-leg `LIVE`.

---

### `R-41` — `15%` Reconciled-NAV Correlated Concentration Cap (`CWCE` Refinement of `R-04`)
- **Original Restriction & Rationale:** v5.0 `JUSTIFIED_RISK_LIMIT` — Retained a `15%` single-event concentration cap once `R-04`'s `book_equity` denominator bug was fixed.
- **Verified Current Behavior:** Challenged in v6.0 alongside `R-04`: a `15%` cap on **oracle/dispute-exposed** capital (`$7.33` at `$48.83` mark-to-bid NAV) is mathematically justified (prevents a repeat of `$50.51` `KMIA` freezing `50.9%` of equity), **provided** it measures **Correlated Worst-Case Exposure (`CWCE`)** across shared correlation clusters (station + regional weather front + UMA event + sports fixture) and **exempts same-condition mergeable `C1` complete sets (`$0.00` oracle exposure)** up to their transient legging risk!
- **Revised Classification:** `ARBITRARY_STATIC_THRESHOLD_REPLACED_DYNAMIC`
- **Research / Shadow / Live Impact:** `RESEARCH`: Unrestricted. `SHADOW` & `LIVE`: Enforces `CWCE <= 15% * reconciled_mark_to_bid_nav_usd` (`$7.33` at `$48.83` NAV) on correlated oracle/UMA risk while freeing same-condition `C1` gasless merges to scale up to full liquid cash (`$21.86+`).
- **Real vs. Estimated Opportunity Cost:** **Measured Risk Reduction:** Limits worst-case future single-cluster UMA freeze to `$7.33` (`15%`) vs `$50.51` (`50.9%` historical `KMIA`). **Simulated Efficiency Gain:** Zero artificial cap drag on mergeable `C1` boxes (`+$0.0954/clip` vs crude `$7.33` notional cap).
- **Recommended Modification:** Pair `check_per_event_concentration_cap` with [`evaluate_correlated_worst_case_exposure`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L806-L880).
- **Replacement Safety Control:** Multi-key `CWCE <= 15%` reconciled mark-to-bid NAV.
- **Source-Code References:** [v6_restriction_and_capital_allocator.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L787-L880), [riskless_protocol_v2_expansion.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/riskless_protocol_v2_expansion.py#L2055-L2165).
- **Tests & Proof:** `test_04_r04_r41_correlated_worst_case_exposure_cwce` (`PASS`).
- **Operational Status:** **IMPLEMENTED & VERIFIED**.
- **Remaining External Dependencies:** None.

---

### `R-42` — Stage G `168-Hour` Wall-Clock Timer vs. 5-Pillar Evidence-Based Venue Readiness
- **Original Restriction & Rationale:** v5.0 `JUSTIFIED_RISK_LIMIT` — Required `168.0` continuous wall-clock hours (`7` days) in `VenueCertificationTracker` before considering cross-venue deployment.
- **Verified Current Behavior:** **Challenged & Overturned in v6.0:** Wall-clock duration alone is **neither sufficient nor optimal**! In [cross_venue_unblock_and_certification.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_unblock_and_certification.py#L1264-L1283), a dead or illiquid feed ticking `168h` with **`0` executable simulated trades and `0` settlement lifecycle tests** advances `progress_168h_pct` to `100%` without proving execution edge or redemption mechanics, whereas a high-volume venue proving `>= 2,000` uncontaminated L2 snapshots across `>= 3` market regimes (`>= 48h` span), `>= 99%` uptime / `<= 2%` errors / `<= 1000ms` p99 latency, `0` Double-Zero incidents, `>= 25` positive-EV post-delay L2 walks, and verified deposit/cancel/redeem mechanics was arbitrarily forced to sit idle waiting out a static `168h` clock!
- **Revised Classification:** `ARBITRARY_STATIC_THRESHOLD_REPLACED_DYNAMIC`
- **Research / Shadow / Live Impact:** `RESEARCH` & `SHADOW`: Continuously scores all 5 evidence pillars per venue (`ForecastEx` currently `40.0%` — failing `P1`, `P4`, `P5` honestly!). `LIVE`: Requires `100%` (`5/5` pillars) + legal eligibility (`R-26`..`R-30`) + human owner canary approval.
- **Real vs. Estimated Opportunity Cost:** **Measured Impact Today:** `$0.00` at `$48.70` cash. **Simulated Uplift at `$500+` NAV:** Accelerates validated `CA-ON`-legal venue onboarding by `~96–120h` (`48–72h` high-evidence proof vs `168h` arbitrary clock) while **blocking** `200h` zero-trade false certifications!
- **Recommended Modification:** Enforce 5-pillar [`evaluate_evidence_based_venue_readiness`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L1722-L1780) (and stage helper hook for protected `cross_venue_unblock_and_certification.py` in [APPLY_AND_ROLLBACK.md](file:///C:/Users/Anton/source/repos/Dominus/paa_staging/proposals/v60_restriction_remediation_package/APPLY_AND_ROLLBACK.md)).
- **Replacement Safety Control:** 5-pillar `EvidenceBasedReadinessReport` (`P1` sample/regime diversity, `P2` SLOs, `P3` zero Double-Zero incidents, `P4` `>=25` positive post-delay L2 trades, `P5` settlement/custody lifecycle proof).
- **Source-Code References:** [v6_restriction_and_capital_allocator.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L1713-L1780), [cross_venue_unblock_and_certification.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_unblock_and_certification.py#L1109-L1283).
- **Tests & Proof:** `test_08_r42_evidence_based_venue_readiness_vs_empty_wall_clock` (`200h` `0`-trade run -> `False`; `72h` `52`-trade 4-regime verified run -> `True`, `100.0%`).
- **Operational Status:** **IMPLEMENTED & VERIFIED** in `v6_restriction_and_capital_allocator.py`; Stage G integration **STAGED**.
- **Remaining External Dependencies:** Authenticated `IBKR_GATEWAY_URL` (`R-20`) + `$500+` NAV for `CA-ON` regulated canary.

---

### `R-43` — Seed Bankroll Capital-Velocity Cliff (`<= 8h`/`24h` & `>= 15 bps/hr`) vs. Portfolio Opportunity-Cost Optimization
- **Original Restriction & Rationale:** v5.0 `JUSTIFIED_RISK_LIMIT` — Defended static `<= 8h` (`<= 24h` intraday `2x` yield) lockup and `15 bps/hr` step hurdles for seed bankroll.
- **Verified Current Behavior:** **Challenged & Replaced in v6.0 (Paired with `R-09`):** Static per-trade maturity/velocity cliffs fail in BOTH directions: (1) When `100%` of `$48.70` cash is sitting idle (`u = 0%`) earning **`0.00 bps/hr`**, rejecting a mathematically proven `25.5h` `280 bps` (`11.0 bps/hr`) `COND1` lockup (`CAND_4`) sacrifices `+$0.2088` guaranteed net profit for zero gain! (2) Conversely, when `u = 50%+` or `DOMINANCE` bypassed the check (`R-09`), locking `$7.30` for `720h` at `0.04 bps/hr` (`CAND_0`) starved fast arrivals (`107` headroom skips).
- **Revised Classification:** `ARBITRARY_STATIC_THRESHOLD_REPLACED_DYNAMIC`
- **Research / Shadow / Live Impact:** `RESEARCH` & `SHADOW`: **Zero maturity cliff** — every horizon (`15m` to `720h+`) is discovered and simulated. `LIVE`: Ranked and gated by portfolio-level `DynamicMarginalCapitalAllocator` (`mrnv_usd = rnv_usd + recycle_bonus_usd - opp_cost_usd > 0`), where $\lambda_{\text{cap}}(u, r_{\text{disp}})$ scales smoothly from `0.50 bps/hr` on idle cash up to `18.0+ bps/hr` at full utilization + displaced competitor yield!
- **Real vs. Estimated Opportunity Cost:** **Counterfactual Simulated Opportunity Loss of Legacy Cliff (`CAND_4` alone):** `-$0.2088/batch` at `$48.70` NAV (`-$0.4170/batch` at `$99.21+` NAV); total portfolio uplift **`+$0.3757/batch` (`+229.8%`)** at `$48.70` and **`+$0.9071/batch` (`+337.2%`)** at `$500.00` NAV!
- **Recommended Modification:** Use [`DynamicMarginalCapitalAllocator`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L1261-L1626) + `use_dynamic_opportunity_cost=True` in [`passes_capital_velocity_hurdle`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/holistic_strategy_governance.py#L818-L859).
- **Replacement Safety Control:** Convex utilization shadow-price curve + Stage C zero-loss open-carry recycler (`maybe_recycle_open_bond_for_velocity_spike`).
- **Source-Code References:** [v6_restriction_and_capital_allocator.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L1300-L1598), [holistic_strategy_governance.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/holistic_strategy_governance.py#L818-L859).
- **Tests & Proof:** `test_06_r09_r43_r10_r15_dynamic_allocator_and_infra_reconciliation` (`26h` `11.0 bps/hr` accepted at `u=0.0`; `720h` `0.04 bps/hr` rejected at `u=0.5`, `PASS`).
- **Operational Status:** **IMPLEMENTED & VERIFIED**.
- **Remaining External Dependencies:** None.

---

### `R-44` — Disputed `KMIA` Nov 7 Positions (`$50.51` Cost Basis / `52.0` Shares): Conservative Accounting & Quantitative Recovery Proof
- **Original Restriction & Rationale:** v5.0 `UNKNOWN` — 4 positions on Miami `KMIA` Nov 7 temperature markets (`6707503`: `35.0 NO` shares across `WS_SNIPE_Miami_KMIA_242960`, `688670`, `837595`; `6707502`: `17.0 YES` shares in `MULTI_LEG_BUNDLE_LIVE_KMIA_..._UNWRESID_...`), `$50.51` cost basis, sit in `umaResolutionStatus == "disputed"` with an official Polymarket dispute case opened by the owner (`D-001`).
- **Verified Current Behavior:** Reconciled live state (`PROJECT_STATE.md`): `52.0` total shares (`$52.00` par payout if UMA DVM resolves favorably; `$0.00` if unfavorably), current distressed CLOB bid **`$0.1390` total** (`~0.2c–0.3c/sh`). Using [`evaluate_disputed_inventory_recovery_options`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L406-L445), we solved the exact compounding dominance equation over a `168h` (`7`-day) DVM horizon at `15.0 bps/hr` reinvestment yield:
  - Immediate distressed sale salvage compounded for `168h`: $\$0.1390 \times (1 + 0.0015)^{168} = \$0.1788$.
  - **Exact Breakeven UMA DVM Win Probability:** $p^* = \frac{\$0.1788}{\$52.00} = 0.003439$ (**`0.344%`**)!
  - At a conservative `35%` favorable DVM/case resolution probability, holding yields **`$18.20` EV** vs **`$0.1788`** compounded salvage (**`+$18.0212` EV advantage of holding untouched!**).
- **Revised Classification:** `DEFECTIVE_IMPLEMENTATION_REPAIRED_OR_STAGED` *(Upgraded from `UNKNOWN` to Quantified Conservative Quarantine & Proven Optimal Hold Policy)*
- **Research / Shadow / Live Impact:** `RESEARCH`: Reads public `6707502`/`6707503` UMA status without interference. `SHADOW` & `LIVE`: **Hard-blocked from placing any order, merge, burn, or state mutation on all 4 `KMIA` positions (`D-001`)**; valued at **`$0.00` guaranteed floor** (`$48.70` deployable cash) and **`$0.1390` mark-to-bid** (`$48.83` concentration NAV), NEVER `$50.51` cost basis!
- **Real vs. Estimated Opportunity Cost:** **Measured Frozen Principal:** `$50.51` historical sunk cost (`$0.1390` current salvageable bid = `~$0.04/wk` compounding opportunity cost, vs `$52.00` par option value).
- **Recommended Modification:** Maintain `D-001` absolute non-interference (`HOLD_TOUCH_NOTHING_D001`), value at `$0.00` deployable / `$0.1390` mark-to-bid across all sizing & ruin controllers (`R-01`, `R-04`, `R-15`), and redeem via Relayer V2 `redeemPositions` only *after* final on-chain UMA DVM `payoutDenominator > 0` settlement.
- **Replacement Safety Control:** `check_d001_disputed_kmia_guard` (`stage_c_zero_loss_velocity.py:205-228`) + `evaluate_mode_specific_eligibility(touches_d001_disputed_kmia=True)` + `LossCauseAwareCapitalController` `$0` write-off immunity (`R-01`).
- **Source-Code References:** [stage_c_zero_loss_velocity.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/stage_c_zero_loss_velocity.py#L205-L228), [v6_restriction_and_capital_allocator.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L406-L445).
- **Tests & Proof:** `test_01_mode_specific_separation_and_non_overridable_legal_gates` + `test_02_r01_loss_cause_controller_and_r44_kmia_dominance_proof` (`p* == 0.003439`, `recommended_policy == "HOLD_TOUCH_NOTHING_D001"`, `PASS`).
- **Operational Status:** **MATHEMATICALLY PROVEN & ENFORCED (`D-001` LOCKED)**.
- **Remaining External Dependencies:** External UMA DVM token-holder vote & official Polymarket support ticket resolution on markets `6707502` & `6707503`.
