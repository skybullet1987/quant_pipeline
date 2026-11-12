# DOMINUS v6.0 — Adversarial QA, Regression & Zero-Trust Verification Report (`RESTRICTION_CHANGE_QA_REPORT.md`)

**Campaign:** DOMINUS Restriction Register v6.0 Reassessment  
**Timestamp:** `2026-11-11 UTC`  
**Execution Environment:** Local Windows Python `3.12.14` (`"C:\Program Files\LibreOffice\program\python.exe" -m unittest`, **`0` compute/RAM load placed on swapless `kraken-finland` per `D-010`**)

---

## 1. Summary of Executed Regression & Adversarial Suites (`41 / 41 PASS`)

Command executed:
```powershell
& "C:\Program Files\LibreOffice\program\python.exe" -m unittest `
  tests/test_v60_restriction_reassessment_and_allocator.py `
  tests/test_stage_c_zero_loss_velocity.py `
  tests/test_v50_paa_emergency_and_governance.py `
  tests/test_v5_section7_risk_invariants.py `
  tests/test_full_throttle_pipeline_and_dashboard.py -v
```

| Test Suite | Tests | Result | Runtime / Peak RSS | Core Invariants Proven |
| :--- | :---: | :---: | :---: | :--- |
| [test_v60_restriction_reassessment_and_allocator.py](file:///C:/Users/Anton/source/repos/Dominus/tests/test_v60_restriction_reassessment_and_allocator.py) | **10** | **`OK`** | `<0.4s` | Mode separation (`RESEARCH`/`SHADOW`/`LIVE`), **`D-011` Owner Sovereignty (`R-26`..`R-32` verified vs assumed separation, single-pass Owner override of internal AI thresholds, `ExternalBlockerReport` + lawful remedies with `silent_disable_permitted=False`, `--all-owner-scopes` single-pass CLI)**, `R-01` loss-cause controller, `R-44` `0.344%` `KMIA` proof, `R-02` fee-bearing `CAL1` & inverted-deadline/proxy blocks, `R-03` `84`-key cold-boot LKG merge, `R-04`/`R-41` `CWCE`, `R-05`/`R-08` `paa_cli`, `R-09`/`R-43`/`R-10` `DynamicMarginalCapitalAllocator`, `R-21`/`R-23` V2 fees/ABIs, `R-42` 5-pillar readiness, and `PermissionGate` `(True, [])` + LF hygiene. |
| [test_stage_c_zero_loss_velocity.py](file:///C:/Users/Anton/source/repos/Dominus/tests/test_stage_c_zero_loss_velocity.py) | **7** | **`OK`** | `<0.3s` | Pre-split quarantine, tick ceil rounding, Stage C zero-loss open-carry velocity recycler (`+$0.020` real-time recycle), clinched dead-leg split/merge, pure-riskless firewall against probabilistic/multileg loopholes, and `KMIA` frozen UMA isolation. |
| [test_v50_paa_emergency_and_governance.py](file:///C:/Users/Anton/source/repos/Dominus/tests/test_v50_paa_emergency_and_governance.py) | **8** | **`OK`** | `<0.4s` | Autonomy-only vs `--include-trading` emergency stop, fallback protection of exit orders on minimal stubs, `resume` warnings, `16` protected-files integrity, and `R-06` 4-`KMIA`-position restart safety. |
| [test_v5_section7_risk_invariants.py](file:///C:/Users/Anton/source/repos/Dominus/tests/test_v5_section7_risk_invariants.py) | **6** | **`OK`** | `<0.4s` | `$48.83`/`$47.52` reconciled NAV `15%` concentration cap, `<$500` `>=3`-leg quarantine (`D-007`), passive Maker blind-book fail-closed cancel, canonical event deduplication, and `C1` merge velocity. |
| [test_full_throttle_pipeline_and_dashboard.py](file:///C:/Users/Anton/source/repos/Dominus/tests/test_full_throttle_pipeline_and_dashboard.py) | **10** | **`OK`** | `0.307s` / `54.98 MiB` RSS | `MODE_3_LIVE` unattended hard-lock fail-closed, `180 MiB` swapless RSS budget (`54.98 MiB` peak), 10-stage dormant wakeup, shared L2 orderbook depth non-double-counting, ambiguous hit-barrier guard, `HarvesterCandidateBridge`, and `HedgedMakerShadowQuoter`. |
| **TOTAL** | **41** | **`41 / 41 OK`** | **`~2.1s` total** | **`0` failures, `0` errors, `0` regressions.** |

---

## 2. Bugs Caught & Fixed During Adversarial QA Verification

1. **`R-03` `alpha124` Cold-Boot `84`-Key LKG Wipeout (`stage_c_zero_loss_velocity.py:754-795`):**
   - *Discovery:* Local `data/polymarket/alpha124_shadow_state.json` had `cycles == 0` with `84` initialized keys (`closed: 0, losses: 0`), causing `bool(by_sl_map) == True` to overwrite `alpha124_graduation_lkg_cache.json` with zeros!
   - *Fix & Proof:* Merged LKG records strictly into `{closed == 0, losses == 0}` slots and gated sidecar overwrite on `has_nonzero_grad`, while `test_03` proved a fresh `losses == 1` still revokes graduation instantaneously.
2. **`R-08` Emergency-Stop Uncancelled Entry Anchors + Premature `KILL_SWITCH` Resume (`scripts/paa_cli.py:470-508, 610-627`):**
   - *Discovery:* Having 1 protective `exit_order_id` caused `_cancel_open_clob_orders_out_of_band` to skip cancelling resting `BUY` entry orders; `cmd_resume --include-trading` ignored `ACCOUNTING_SAFEGUARD_ACTIVE.json`.
   - *Fix & Proof:* Selective per-order `cancel_order(oid)` cancels `OID_ENTRY_ANCHOR_1/2` while preserving `OID_EXIT_PROTECTED`, and `cmd_resume --include-trading` exits `rc=2` with `KILL_SWITCH` intact when `ACCOUNTING_SAFEGUARD_ACTIVE.json` is active (`test_05`).
3. **`R-09` Inframarginal Instant-Merge Shadow-Price Distortion (`v6_restriction_and_capital_allocator.py:1505-1535`):**
   - *Discovery:* Initial counterfactual run showed an already-filled `18s` `C1` merge (`13,085 bps/hr`) inflating `competing_top_bps` for remaining idle cash (`$26.84`) even though `CAND_1`'s L2 book depth (`22` shares) was `100%` exhausted!
   - *Fix & Proof:* Computed `displaced_best_bps` strictly across **subsequent unallocated positive-EV candidates actually crowded out** by `alloc_cap`, raising `$48.70` batch RNV from `$0.1635` (legacy v5) to **`$0.5392` (`+229.8%`)** (`test_06`).
4. **Tuple Unpack in Fee Helper Calls (`v6_restriction_and_capital_allocator.py:555, 580, 989`):**
   - *Discovery:* Adversarial `test_03` & `test_07` caught `compute_net_buy_cost_per_delivered_share` returning `(eff_px, fee_per_sh)` tuples.
   - *Fix & Proof:* Unpacked float `eff_px` cleanly across all call sites; verified penny-and-5-decimal exact against `crypto_15_min` (`rate=0.25, exp=2` -> `$0.3125` on `20 sh @ $0.50`) and `0%` `takerBaseFee=1000` ceiling markets (`test_07`).

---

## 3. Zero-Trust Security, Legal & Protected-Files Attestation

| Non-Overridable Invariant | Verification Method | Verified Result |
| :--- | :--- | :---: |
| **`PermissionGate.inspect_candidate_diff` Across All 12 v6.0 Code/Test/Doc Files** | `test_09_zero_trust_permission_gate_and_lf_hygiene_all_v6_deliverables` | **`(True, [])` (`0` violations)** |
| **16 Zero-Trust `protected_files` Untouched in Working Tree (`D-003`)** | `TestStagedOwnerControlPackageAndPermissionGate.test_07` | **`PASS` (`0` protected files modified)** |
| **4 Disputed `KMIA` Nov 7 Positions Untouched (`D-001` / `R-44`)** | `test_01`, `test_02`, `TestStageCZeroLossVelocity.test_07`, zero SSH writes | **`PASS` (`100%` untouched)** |
| **External `LIVE` Legal Eligibility (`CA-ON`, `US`, `UK` — `R-26`..`R-32`)** | `test_01` (`claims_incorporation_or_remote_host_bypass=True` rejected) + `TestFullThrottlePipelineAndDashboard.test_01` & `test_05` | **`PASS` (`LIVE` hard-locked)** |
| **Swapless `kraken-finland` Host Protection (`D-010` / `R-16`)** | All unit tests & counterfactual sims executed locally on Windows; `peak_rss_mib == 54.98 MiB <= 180 MiB` | **`PASS` (`0` remote load)** |
| **LF (`\n`) Line-Ending & Non-Zero-Byte Hygiene** | `test_09` byte-level scan across all 12 v6.0 files | **`PASS` (`0` `\r\n` bytes, `0` empty files)** |
