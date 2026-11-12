# DOMINUS v6.0 — Restriction Remediation & Execution Roadmap (`RESTRICTION_REMEDIATION_ROADMAP.md`)

**Campaign:** DOMINUS Restriction Register v6.0 Reassessment  
**Timestamp:** `2026-11-11 UTC`  
**Authoritative Companion Register:** [RESTRICTION_REGISTER_V6.md](file:///C:/Users/Anton/source/repos/Dominus/RESTRICTION_REGISTER_V6.md) (`R-01`..`R-44`)

---

## 1. Guiding Engineering Principles

1. **Mode-Specific Decoupling (`RESEARCH` vs. `SHADOW` vs. `LIVE`):**
   - `RESEARCH` (`ExecutionMode.RESEARCH`): `100%` universe discovery (`375,355` observable / `201,012` active Polymarket markets + `6` Stage G venues) with **zero** capital-tier (`$150`/`$500`), maturity (`24h`), or trading-jurisdiction exclusions — constrained only by provider data licenses & API rate limits (`R-25`).
   - `SHADOW` (`ExecutionMode.SHADOW`): Full-universe orderbook depth walking, 13-schedule Protocol V2 fee & 2-decimal lot quantization (`R-23`), partial-fill construction penalty (`R-24`), and portfolio-level `DynamicMarginalCapitalAllocator` (`MRNV`) accounting (`R-09`/`R-43`), while enforcing `D-001` non-interference (`R-44`) and key-free `.env` isolation (`R-37`).
   - `LIVE` (`ExecutionMode.LIVE` under **`D-011` Owner Sovereignty**): Unattended background workers enforce default safeguards (`D-001` `KMIA` lock, `D-007` `<$500` non-atomic `>=3`-leg default, `CWCE <= 15%` reconciled NAV `R-04`/`R-41`, `$1.50` accounting safeguard `R-38`, and `proposal_only_live_promotion` default). **When the Owner explicitly authorizes trading, sizing, venue activation, or deployment (`owner_explicitly_authorized=True` or `paa_cli.py approvals grant --all-owner-scopes`), all technically feasible and permitted actions execute in a single pass without repeated prompts**, while any verified external platform/regulatory/KYB restriction (`R-26`..`R-32`) emits an explicit `ExternalBlockerReport` + lawful remedies (`0` silent disabling).
2. **Zero-Trust Protected-File Compliance (`D-003`):**
   - Non-protected modules are implemented and regression-tested directly in the repository working tree (`41/41` unit tests passing).
   - Modifications to any of the `16` Zero-Trust `protected_files` (`permissions.py`, `builder_and_deployer.py`, `accountant.py`, `cross_venue_unblock_and_certification.py`) are staged cleanly under [APPLY_AND_ROLLBACK.md](file:///C:/Users/Anton/source/repos/Dominus/paa_staging/proposals/v60_restriction_remediation_package/APPLY_AND_ROLLBACK.md) for explicit human-owner apply.

---

## 2. Phased Remediation Wave Matrix

| Wave | Scope & Restriction IDs | Key Modules / Staged Files | Status (`2026-11-11 UTC`) | Owner Activation / Prerequisites |
| :--- | :--- | :--- | :---: | :--- |
| **Wave 1 (Landed in Working Tree — Non-Protected Code)** | `R-01`..`R-05`, `R-08`, `R-09`/`R-43`, `R-10`, `R-15`, `R-21`, `R-23`, `R-26`..`R-32` (`D-011` Owner Sovereignty), `R-39`/`R-40`, `R-42`, `R-44` | [v6_restriction_and_capital_allocator.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py), [stage_c_zero_loss_velocity.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/stage_c_zero_loss_velocity.py), [holistic_strategy_governance.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/holistic_strategy_governance.py), [paa_cli.py](file:///C:/Users/Anton/source/repos/Dominus/scripts/paa_cli.py), [run_v6_counterfactual_opportunity_audit.py](file:///C:/Users/Anton/source/repos/Dominus/scripts/run_v6_counterfactual_opportunity_audit.py), [test_v60_restriction_reassessment_and_allocator.py](file:///C:/Users/Anton/source/repos/Dominus/tests/test_v60_restriction_reassessment_and_allocator.py) | **IMPLEMENTED & VERIFIED (`41/41` Tests OK, `PermissionGate == (True, [])`)** | Single-pass Owner command (`paa_cli.py approvals grant --all-owner-scopes` + `paa_flat_harvester_redeploy_once.py`, `R-06` safe across passive `KMIA` UMA locks). |
| **Wave 2A (Staged Protected-File Owner Package)** | `R-05` (Atomic post-deploy `consume_owner_approval`), `R-06` (`builder_and_deployer.py` frozen-UMA check), `R-10` (`accountant.py` window-aligned VM deduction), `R-13` & `R-42` (`cross_venue_unblock_and_certification.py` `512M` prose + 5-pillar readiness hook) | [v60 APPLY_AND_ROLLBACK.md](file:///C:/Users/Anton/source/repos/Dominus/paa_staging/proposals/v60_restriction_remediation_package/APPLY_AND_ROLLBACK.md) + [v50 APPLY_AND_ROLLBACK.md](file:///C:/Users/Anton/source/repos/Dominus/paa_staging/proposals/v50_owner_control_package/APPLY_AND_ROLLBACK.md) | **STAGED & VERIFIED** (`0` protected files touched in candidate diff) | Direct Owner execution on `kraken-finland` at Owner's discretion. |
| **Wave 2B (Executor Protocol V2 Adapter Polish)** | `R-21` (`CTF_V1_LEGACY_USDCE` direct `CTF.mergePositions` + inline `pUSD` wrap when `appr_v2 == True`, plus optional `PositionManager V2` `0x006F54...` ERC-6909 split/merge ABI when V2 markets launch) | [polymarket_live_executor.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_executor.py#L4326-L4330) (modeled accurately in `validate_wallet_split_merge_capabilities` as `24h+` settlement until ABI is wired) | **ACCURATELY MODELED IN ALLOCATOR** | Read-only Polygon `eth_call` verification against a live V2 `PositionManager` market prior to enabling V2 instant merges. |
| **Wave 3A (Bounded-Risk `CLASS_C` & Directional Activation — Advisory `$150` NAV)** | `R-39` (`CLASS_C` bounded-risk carries & Half-Kelly directional sleeves) | [polymarket_strategy_and_risk.json](file:///C:/Users/Anton/source/repos/Dominus/config/polymarket_strategy_and_risk.json#L20-L24) | **SHADOW ACCUMULATING AT `$48.70` (`+756` `CLASS_C` candidates tracked)** | Advisory recommendation: Purged `CPCV(6,2)` WFO pass (`N >= 50`, `PF >= 1.45`) + `~$150` NAV; **Owner retains full sovereignty (`owner_explicitly_authorized=True`) to activate at any time**. |
| **Wave 3B (Regulated `CA-ON` Cross-Venue & Multi-Leg — Advisory `$250–$500+` NAV)** | `R-17` (`europe-west4` `~7–9ms` RTT move), `R-19`/`R-20` (`STX` Ed25519 + `IBKR_GATEWAY_URL` CPAPI), `R-30` (`CA-ON` native `ForecastEx` + `STX Ontario` execution), `R-40` (`>=3`-leg sequential), `R-42` (`100%` 5-pillar readiness) | Stage G connectors & `CA-ON` workstation execution runner | **PUBLIC CSV + PHOENIX WS ACTIVE (`ForecastEx` 5-pillar score `40.0%`)** | External prerequisites: authenticated `IBKR_GATEWAY_URL` (`ForecastEx`) or Owner STX credentials on a physical `CA-ON` host (`R-30`). `$500` NAV is advisory only, never an AI block. |
| **Wave 4 (Corporate / Institutional KYB — Advisory `$10,000+` ROI Break-Even)** | `R-26`..`R-29`, `R-31` | Pre-incorporation compliance dossiers ([KYB_AND_API_ONBOARDING_DOSSIERS.md](file:///C:/Users/Anton/source/repos/Dominus/docs/KYB_AND_API_ONBOARDING_DOSSIERS.md)) & venue KYB onboarding | **ADVISORY BREAK-EVEN (`$1,500–$5,000/yr` fee vs bankroll) — OWNER SOVEREIGN** | Zero AI-imposed deferral: `$0`-cost written compliance inquiries can be sent at any time at Owner's direction; external live execution awaits issued venue KYB credentials. |

---

## 3. Misguided v5.0 Proposals Explicitly Cancelled in v6.0

To protect live profitability and test-suite integrity, v6.0 **cancels** two erroneous v5.0 remediation items:
1. **Cancelled (`R-11`):** Setting `"enable_ungraduated_v3_math_live": false` in [polymarket_strategy_and_risk.json](file:///C:/Users/Anton/source/repos/Dominus/config/polymarket_strategy_and_risk.json#L204) — proven to break the active `CAL1`/`COND1`/`MKR_LOCK1`/`W_PRUNE1` execution bridge ([polymarket_live_harvester.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L5835)) while `check_strict_pure_riskless_candidate_gate` (`L5571`) already enforces mathematical proof safety upstream.
2. **Cancelled (`R-12`):** Deleting/mutating [polymarket_risk_config.json](file:///C:/Users/Anton/source/repos/Dominus/config/polymarket_risk_config.json) — proven to have zero runtime effect on v5.5/v6.0 governance (`GLOBAL_GOVERNANCE_MANAGER`) while breaking legacy unit tests (`test_orderflow_hardening.py`, `test_zero_trust_forensic_audit.py`).

---

## 4. Single-Pass Owner Promotion Commands (`D-011` Zero Repeated Approvals)

```bash
# Single-pass Owner authorization & flat-book redeploy on kraken-finland (safe across passive KMIA UMA locks, R-06):
python3 scripts/paa_cli.py approvals grant \
  --all-owner-scopes \
  --approved-by Anton \
  --ttl-hours 4 \
  --release-id v60_remediation_20261111 \
  --reason "Single-pass Owner authorization for v6.0 verified improvements" && \
python3 scripts/paa_flat_harvester_redeploy_once.py
```
