# Dominus v5.0 Architecture, Governance & Risk Decisions Log

**Last Updated:** `2026-11-11 00:52 UTC`  
**Maintainer:** Agent F (`@reliability`)

---

## Active Binding Decisions

### `D-001` — Absolute Non-Interference With Disputed `KMIA` Nov 7 Positions
- **Status:** `LOCKED SAFETY BOUNDARY` (Active)
- **Context:** Four live positions (`$50.51` cost basis: `35.0 NO` shares on market `6707503` across `WS_SNIPE_Miami_KMIA_242960`, `688670`, `837595` + `17.0 YES` shares on market `6707502` in `MULTI_LEG_BUNDLE_LIVE_KMIA_1794113999_318559_UNWRESID_20116898_1794111898`) are in `umaResolutionStatus="disputed"` following the Nov 7 `KMIA` ASOS `$` sensor maintenance outage. The owner has an active official case open with Polymarket.
- **Decision:** Zero shares may be sold, unwound, merged, redeemed, or modified (`exit_order_id=None`, `unwind_order_id=None`), and no automated recovery routine may liquidate post-expiry UMA-disputed locks at distressed `0.2c–0.3c` bids.
- **Code Enforcement:** [`is_post_expiry_uma_frozen_lock`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L5549) and [`_is_restart_safe_frozen_uma_lock`](file:///C:/Users/Anton/source/repos/Dominus/scripts/paa_flat_harvester_redeploy_once.py#L36-L53).

### `D-002` — PAA Autonomous Code Promotion Locked to `Proposal-Only` Below `$5,000` NAV (`Action 2A`)
- **Status:** `ENFORCED` (`2026-11-10 21:32 UTC`)
- **Context:** At `$97.89` book equity (`$47.38` liquid cash), autonomous unattended live code/config promotion carries asymmetric negative EV if an edge-case defect reaches live capital.
- **Decision:** Keep PAA Monitor (`60s`), Supervisor (`120s`), Accountant, and Researcher automated, but block unattended live file promotion unless an explicit human approval JSON (`scopes: ["LIVE_PRODUCTION_PROMOTION"]`) is placed in `data/polymarket/paa/approvals/`.
- **Code Enforcement:** [config/paa_autonomy_config.json](file:///C:/Users/Anton/source/repos/Dominus/config/paa_autonomy_config.json#L93-L97) (`proposal_only_live_promotion=true`, `proposal_only_below_nav_usd=5000.0`, `allow_auto_plumbing_bugfix_deploy=false`, `allow_auto_risk_tightening_hot_reload=false`) and [`DeploymentController._is_live_promotion_blocked_by_proposal_only`](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/builder_and_deployer.py#L387-L430).

### `D-003` — Non-Overridable Zero-Trust Permission Envelope
- **Status:** `ENFORCED` (`2026-11-10 21:32 UTC`)
- **Decision:** `SELF_APPROVAL_TAMPERING_FORBIDDEN` (writing to `approvals/`) and `FORBIDDEN_CREDENTIAL_OR_TRANSFER_PATTERN` (`POLYGON_PRIVATE_KEY`, `safeTransferFrom(`, `eth_sendRawTransaction`) are unconditionally non-overridable even when a human approval file exists; `inspect_config_envelope()` fails closed on deleted risk keys (`RISK_KEY_DELETED`), and Session C diff review inspects up to `24,000` characters (rejecting truncated diffs).
- **Code Enforcement:** [src/paa_os/permissions.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L199-L360) and [src/paa_os/zero_trust.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/zero_trust.py#L945-L965).

### `D-004` — 3-Verdict Forensic Wall Against `N=1` Parameter Overfitting
- **Status:** `ENFORCED`
- **Decision:** Every settled loss must be classified via [audit_losing_trades.py](file:///C:/Users/Anton/source/repos/Dominus/audit_losing_trades.py) as `EXPECTED_LOSS` (`0` code changes), `BUG_FIXED` (`PLUMBING_0_PARAM` deterministic software bug only, `0` tunable parameters), or `PARAM_WFO_REQUIRED` (queued to Purged Walk-Forward Optimization + `CPCV(6,2)` in [honest_purged_wfo_optimizer.py](file:///C:/Users/Anton/source/repos/Dominus/scripts/honest_purged_wfo_optimizer.py); never auto-tweaked live).
- **Code Enforcement:** [SKILL.md](file:///C:/Users/Anton/source/repos/Dominus/.agents/skills/trade-forensics/SKILL.md) and [audit_losing_trades.py](file:///C:/Users/Anton/source/repos/Dominus/audit_losing_trades.py).

### `D-005` — Pure-Riskless Live Firewall (`RISKLESS_PAA`)
- **Status:** `ENFORCED` (`77W / 0L` all-time pure-riskless filled trades, `+$17.9281` net P&L; `72W / 0L` post-lock)
- **Decision:** Directional crypto/sports sleeves (`SLEEVE_1_SUBHOURLY_15M`, `SLEEVE_1_CORE_302`, `SOC2_EXACT_SCORE_2D_LATTICE`, which caused `-$73.3385` historical net losses across `41` filled trades) are hard-blocked in live production (`directional.riskless_only_mode = true`, verified in [`verify_local_manifest`](file:///C:/Users/Anton/source/repos/Dominus/scripts/deploy_polymarket_live.py#L237-L239)). Only `Grad-8` zero-loss sleeves (`D1_SAME_ORACLE_DOMINANCE_BOX`, `D1_QUIET_BOOK_BOX`, `BOND1_UMA_RESOLUTION_CARRY`) and certified structural boxes may deploy capital.

### `D-006` — ASOS `$` Hardware Maintenance Block & `±0.55°C` Unverified Sensor Cushion
- **Status:** `ENFORCED` (`2026-11-10 22:54 UTC`)
- **Decision:** Any routine/SPECI METAR carrying the FMH-1 trailing `$` maintenance indicator sets `has_maintenance_indicator=True` / `has_maintenance_obs=True` and blocks intraday (`rem_hours_count > 0`) `is_solar_lock` and `W_PRUNE1_DEAD_NO_BOND` snipes; stations without verified `T`-group tenth-degree remarks require a conservative `±0.55°C` rounding interval.
- **Code Enforcement:** [weather_metar_engine.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/weather_metar_engine.py#L381-L1190) and [riskless_protocol_v2_expansion.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/riskless_protocol_v2_expansion.py#L3767-L4055).

### `D-007` — Unified Correlated-Event Concentration Cap & `< $500` Multi-Leg Quarantine
- **Status:** `ACTIVE — UNDER PHASE 2 ADVERSARIAL AUDIT (@frp-director / @adv-auditor)`
- **Decision:** Canonical event grouping strips `_UNWRESID_` / `_LEG_INLINE_UNWIND_` suffixes and keys weather events by `WXSTATION:{icao}` across dates/sleeves (`SINGLE_LEG_LOCK` included). Campaign v5.0 mandates a strict **`<= 15%` reconciled NAV cap** per correlated weather station/day or non-box oracle event across all sleeves combined, and hard-disables sequential `>= 3`-leg CLOB bundles below `$500` NAV unless atomic (`NegRiskAdapter.convertPositions`) or inventory-backed.
- **Code Enforcement:** [`extract_canonical_event_keys`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/riskless_protocol_v2_expansion.py#L1906-L2020) and [`check_per_event_concentration_cap`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/riskless_protocol_v2_expansion.py#L2025-L2135).

### `D-008` — Ontario (`CA-ON`) Jurisdiction Advisory & Stage G Evidence-Based Cross-Venue Readiness
- **Status:** `UPDATED IN v6.0 (GOVERNED BY D-011 OWNER SOVEREIGNTY)`
- **Decision:** Unattended default configuration keeps `CROSS_VENUE_LIVE_EXECUTION_ENABLED=false` while capital is consolidated single-venue; however, per **`D-011`**, capital milestones (`$253`, `$500`, `$525`, `$10,000`) and venue selection are **advisory defaults, NEVER vetoes over explicit Owner authorization**. Verified external platform/geofence gates (`R-26`..`R-32`) are reported transparently with exact blockers and lawful remedies rather than silently disabling operations.
- **Code Enforcement:** [`assess_r26_to_r32_venue_restrictions`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L140-L315) and [`evaluate_mode_specific_eligibility`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L318-L492).

### `D-009` — Conservative Guaranteed-Floor Valuation Standard (`F-02`)
- **Status:** `PATCHED LOCALLY & UNIT-TESTED (2026-11-11 00:51 UTC — READY FOR DEPLOY)`
- **Decision:** Any position (`SINGLE_LEG_LOCK`, `WS_SNIPE_*`, or box leg) with `umaResolutionStatus == "disputed"` MUST be valued at **`$0.00`** in worst-case guaranteed-floor metrics (`$47.38` / `$48.70`), matching `_UNWRESID_` residuals, while keeping Book Equity (`$97.89` / `$99.21`) and Mark-to-Bid Liquidation NAV (`$47.52` / `$48.83`) distinct and explicitly reported.
- **Code Enforcement:** [`compute_live_equity_and_rates`](file:///C:/Users/Anton/source/repos/Dominus/scripts/polymarket_daily_projections.py#L1135-L1190), [`_compute_cc_valuations`](file:///C:/Users/Anton/source/repos/Dominus/scripts/dominus_command_center.py#L474-L558), and [test_phase0_reliability_fixes.py](file:///C:/Users/Anton/source/repos/Dominus/tests/test_phase0_reliability_fixes.py).

### `D-010` — `kraken-finland` `3.9 GiB` Swapless RAM Envelope & Zero-Remote-Pytest Rule (`#11` / `F-01`)
- **Status:** `ENFORCED` (`2026-11-11 00:45 UTC`)
- **Decision:** Because `kraken-finland` has `3,907 MiB` physical RAM with `MemorySwapMax=0B` drop-ins, running heavy test suites (`pytest`, `~650 MiB` RSS) or unbounded caches on the live host is prohibited; all regression suites must execute locally or in CI, and long-running Python daemons must bound retained Gamma/L2 caches and invoke periodic `libc.malloc_trim(0)`.
- **Code Enforcement:** [alpha_124_shadow_daemon.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/alpha_124_shadow_daemon.py#L1084-L1314), [polymarket_terminal_recorder.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_terminal_recorder.py#L700-L760), and [pytest.ini](file:///C:/Users/Anton/source/repos/Dominus/pytest.ini).

### `D-011` — Owner Sovereignty, Advisory Clarity & Single-Pass Execution Authority (`R-26`–`R-32`)
- **Status:** `LOCKED GOVERNANCE PRINCIPLE` (`2026-11-11 UTC`)
- **Decision:**
  1. **Exclusive Owner Authority:** The AI is an execution and advisory agent, **not** the final decision-maker regarding where, when, or how the Owner trades. The Owner retains exclusive authority over trading decisions, venue selection, capital allocation, activation, and deployment.
  2. **Verified Restrictions vs. Assumptions & AI Preferences:** For `R-26`–`R-32` and all portfolio controls, the system must distinguish **verified external restrictions** (actual platform HTTP/API gates, published ToS clauses, statutory geofences such as `iGO` physical-Ontario IP rules on `on.stxapp.ca`, or missing provider KYC/KYB credentials) from **unverified assumptions** and **non-binding AI economic heuristics** (`$150`, `$500`, `$5,000`, `$10,000` NAV tiers, `15%`/`25%` cluster defaults). AI risk preferences apply only as unattended defaults and never bind the Owner.
  3. **Single-Pass Execution & Zero Silent Disabling:** When the Owner explicitly authorizes trading or deployment (`owner_explicitly_authorized=True` or `paa_cli.py approvals grant --all-owner-scopes`), execute all technically feasible and permitted actions immediately without unnecessary delays or repeated approvals. If an external restriction prevents execution, emit an explicit `ExternalBlockerReport` (`silent_disable_permitted=False`) stating the exact blocker and available lawful remedies rather than silently disabling the operation.
- **Code Enforcement:** [`ExternalBlockerReport`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L112-L128), [`assess_r26_to_r32_venue_restrictions`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L140-L315), [`evaluate_mode_specific_eligibility`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L318-L492), [`DynamicMarginalCapitalAllocator.allocate`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L1617-L1730), and [`cmd_approvals --all-owner-scopes`](file:///C:/Users/Anton/source/repos/Dominus/scripts/paa_cli.py#L726-L775).
