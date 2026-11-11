# DOMINUS v5.0 — Daily Command Center & Campaign Executive Consolidation (`DAILY_COMMAND_CENTER_REPORT.md`)

**Campaign:** DOMINUS v5.0 Supreme Profit & Operational Freedom (Sections 16 & 19 Consolidated Executive Deliverable)  
**Consolidated Timestamp:** `2026-11-11 02:55 UTC`  
**Operating Mode:** `RISKLESS_PAA` (`directional.riskless_only_mode = true`, `strict_pure_riskless_mode = true`, `proposal_only_live_promotion = true`, Jurisdiction = `CA-ON`)  
**Production Host Integrity (`kraken-finland`):** **100% UNTOUCHED** (`polymarket-live-harvester.service` `MainPID=264354`, `NRestarts=0`; `0` remote writes, `0` service restarts, `0` orders placed/cancelled; all `4` disputed `KMIA` Nov 7 positions strictly untouched)

---

## (a) FINANCIAL — Authoritative Wallet, NAV & P&L Reconciliation

> **Strict Separation Rule:** On-chain wallet cash (`0x013A...`) and simulated shadow benchmarks (`alpha124` `T1000`, `shadow_telemetry.sqlite3`) are never summed or co-mingled. All figures below reconcile to **`$0.000000`** against Polygon PoS mainnet (`Block 97,103,765+`), [`authoritative_financial_ledger.json`](file:///C:/Users/Anton/source/repos/Dominus/PROJECT_STATE.md), and `live_harvester_state.json`.

### 1. Reconciled On-Chain Balance Sheet & Three Explicit NAV Definitions

| Metric / Account | Verified Value | Exact On-Chain / Ledger Basis |
| :--- | ---: | :--- |
| **Funder Beacon Proxy (`sig_type=3`, `POLY_1271`)** | **`$47.377122` (`$47.38`)** | `0x013A2474454fBd8738cff6a7f204eF1bc377F4e9` wrapped `pUSD` (`0xC011...2DFB`); **`$0.000000` drift** vs `live_bankroll`; `accounting_ok = true`. |
| **Embedded Signer EOA (`0x9703...d50a5`)** | **`41.8138 POL` + `$1.0000 USDC.e`** | `~$3.70` emergency gas reserve (`~1,400–2,000` Polygon txs) + **`$1.000000` untracked recoverable `USDC.e`** (see Approval Package 3). |
| **SettledCTF Micro-Dust (`19` `<0.018 sh` IDs)** | `$0.101072` | Intentionally below `<0.01–0.02 sh` Relayer redemption dust filter; **`0` material (`>= $0.02`) unredeemed winners** across `136` token IDs (`41` winners swept at `$0.00` gas). |
| **4 Untouched Disputed `KMIA` Nov 7 Positions** | `$50.5100` *(cost basis)* | `3x W_PRUNE1_DEAD_NO_BOND` (`6707503`, `35.0 NO` sh, `$34.19`) + `1x W_PRUNE1_NR0_BASKET` `_UNWRESID_` (`6707502`, `17.0 YES` sh, `$16.32`); `umaResolutionStatus == "disputed"`, `exit_order_id = None`, `unwind_order_id = None`. |
| **NAV #1 — True Worst-Case Guaranteed-Floor NAV** | **`$47.38`** (`$47.377122`) | `$47.377122` cash + **`$0.00`** worst-case UMA DVM payout on all `4` disputed `KMIA` lots (enforced via `F-02` in [polymarket_daily_projections.py](file:///C:/Users/Anton/source/repos/Dominus/scripts/polymarket_daily_projections.py) & [dominus_command_center.py](file:///C:/Users/Anton/source/repos/Dominus/scripts/dominus_command_center.py)). |
| **NAV #2 — Mark-to-Bid Liquidation NAV (`reconciled_nav_usd`)** | **`$47.52`** (`$47.516122`) | `$47.377122` cash + `$0.1390` live CLOB best-bid value (`35 sh @ $0.003` + `17 sh @ $0.002`; Gamma midpoint MTM `= $48.44`). **Authoritative denominator for `15%` event concentration (`<= $7.13`).** |
| **NAV #3 — Persisted Harvester Book Equity (`total_account_equity`)** | `$97.89` (`$97.887122`) | `$47.377122` cash + `$50.51` frozen UMA receivable. **Forbidden for clip sizing, tier promotion, or concentration caps while disputed.** |

### 2. Closed-Ledger Decomposition (`136` Total Records) & Fixed-Cost Hurdle

| Regime Cohort (`136 = 118 Filled + 8 Merges + 10 Cancels`) | Record Count | Win / Loss | Verified Cash Net P&L | Trading Fees | Notional | Governance Status |
| :--- | ---: | :---: | ---: | ---: | ---: | :--- |
| **Active Pure-Riskless & Post-Clinch Sleeves** (`D1` `+$12.72`, `BOND1` `+$3.62`, `S2` `+$0.47`, `MKR_LOCK1` `+$0.40`, `CM_B3` `+$0.32`, `SP2/SP4/BOND2/W_PRUNE1` `+$0.40`) | **`77`** | **`77W / 0L` (`100.0%`)** | **`+$17.9281`** | `$0.5825` | `$867.79` | **ACTIVE (`D1`, `BOND1`, `MKR_LOCK1`, `BOND2`) / CAPPED (`<=15%` NAV)** |
| **Retired Directional & Non-Atomic Lattice Sleeves** (`SUBHOURLY_15M` `-$55.24`, `CORE_302` `-$9.43`, `SOC2` `-$8.67`) | **`41`** | `30W / 11L` | **`-$73.3385`** | `$12.7432` | `$873.11` | **PERMANENTLY HARD-DISABLED (`riskless_only_mode = true`)** |
| **Flat Pre-Split Merges (`8`) + Zero-Fill Cancels (`10`)** | `18` | `0W / 0L` | `$0.0000` | `$0.0000` | `$95.98` *(unfilled)* | Reconciled `$0.00` cash impact |
| **TOTAL WALLET-RECONCILED LEDGER** | **`136` (`118` filled)** | **`107W / 11L`** | **`-$55.4104`** | **`$13.3257`** | **`$1,740.90`** | **`+$17.9281 + (-$73.3385) = -$55.4104` (`$0.0000` drift)** |

- **Fixed Infrastructure Burn:** **`$24.67/month` (`$0.8223/day` = `$0.03426/hr`)** on GCP `europe-north1-b` (`$0.00/mo` runtime LLM API spend).
- **Portfolio Net Breakeven Hurdle:** **`+7.23 bps/hr` (`+173.5 bps/day`)** on `$47.38` liquid cash (`+3.50 bps/hr` at `$97.89` post-`KMIA` recovery; `+1.35 bps/hr` at `$253`; `+0.69 bps/hr` at `$500`).

---

## (b) FRP — Ranked Riskless Engines, Risk Invariants & Velocity Unlocks

Full strategy attribution and strict post-infra net economics are documented in [PROFIT_SCORECARD.md](file:///C:/Users/Anton/source/repos/Dominus/PROFIT_SCORECARD.md) and [EXPERIMENT_REGISTRY.md](file:///C:/Users/Anton/source/repos/Dominus/EXPERIMENT_REGISTRY.md).

### 1. Ranked Active FRP Portfolio (`$47.38` Survival Tier — `$0` Directional Risk)

| Rank & Engine | Class | Live Cash Record | `T1000` Shadow *(Separate)* | Strict Net Velocity *(After Fees, Slip & `$0.034/hr` Infra)* | Active Cap & Key v5.0 Unlock |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **#1 `D1` Same-Oracle Dominance** (`5m/15m/4h` Chainlink `60s` TWAP + `15m/1h` `XAU/XAG` Forex; **`1h` Binance crypto excluded**) | `R1 -> R0` | `3W / 0L` **`+$12.7200`** | `43W/0L +$200.61` (`D1_QUIET` `15W/0L +$74.03`) | **`+743 bps/hr`** (`+$0.144–$0.225` / `$10` box, `12.6m` hold) | `<= 25%` box cap (`$11.84`); **cured `107` `INSUFFICIENT_BOX_COLLATERAL_HEADROOM` skips** by stopping `BOND1` `$97.89`-equity over-allocation. |
| **#2 `BOND1` / `MKR_LOCK1` / `BOND2` / `UMA_READY1` Post-Clinch Carry** (`$0.998–$0.999` `HTM` Maker Recycle) | `R2` | `66W / 0L` **`+$4.1281`** | `BOND1 +$186.11`, `MKR_LOCK1 +$205.62` | **`+423 bps/hr`** recycled (`7.1m`) / `+19 bps/hr` full `2.2h` UMA | **Hard `<= 15%` reconciled NAV (`$7.11–$7.13`) per event/station across all sleeves** (`4 × $7.11` concurrent slots). |
| **#3 `Stage C` Clinched Dead-Leg Split-to-Sell & Carry Velocity Recycler** | `R1` | `0W / 0L` *(Newly active)* | Replay & `7/7` unit verified | **`+373 bps/hr`** (`$0.00` Relayer split/merge gas) | Mints `$1.00 -> YES+NO` on `0%`-fee clinches to sweep `>=0.8c` dead bids (`mergePositions` fallback if raced); recycles `<45 bps/hr` carries into `>=200 bps` `D1`. |
| **#4 `NR_M1` (`m=1` Dead-Seed) & `NR2` (`m=2` Pure Cash Convert)** | `R1 -> R0` | `0W / 0L` | `0W / 0L` (`m>=3` blocked) | **`+650 bps/hr`** when firing (`72s` Relayer convert) | `<= 2` legs + gasless `NegRiskAdapterV2.convertPositions`; `verify_closed_negrisk_partition()` blocks `negRiskAugmented = true` principal traps. |
| **#5 `C1` `0%`-Fee Binary Complete Sets + `2`-Leg `0%`-Fee `CAL1` & `COND1`** | `R1 -> R0` | `0W / 0L` | `CAL1`: `10W / 0L` (`100%` WR) | **`+1,100 bps/hr`** (`30s` Relayer `mergePositions`) | Unblocked `2`-leg `0%`-fee `CAL1` & `COND1` (`POL-15`); gated `COMPLETE_SET` velocity exemption on verified `merge_wallet_ok = True` (`POL-20`). |

### 2. Eight Enforced Section 7 & Policy-Unlock Risk Invariants ([test_v5_section7_risk_invariants.py](file:///C:/Users/Anton/source/repos/Dominus/tests/test_v5_section7_risk_invariants.py))
1. **Fail-Closed Reconciled Concentration NAV (`§7.1a`):** [`compute_reconciled_concentration_nav_usd`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/riskless_protocol_v2_expansion.py) values disputed/frozen/residual lots at `min(notional, shares × best_bid)` (`$47.52` vs `$97.89`), fails closed to `$0.00` if `_last_known_collateral is None`, and credits synced escrowed maker intents (`collat_drop_usd > 0`) without double-counting.
2. **Multi-Key Cross-Sleeve Event & Weather Station Cap (`<= 15%` = `$7.11–$7.13`):** [`extract_canonical_event_keys`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/riskless_protocol_v2_expansion.py) emits `EVT:*`, `MKT:*`, `COND:*`, `EVTMATCH:*`, `EVTWX:*`, `WSTAT:*`, and `WXSTATION:*` simultaneously across all sleeves (`KMIA` currently at `$0.00` headroom; ASOS `$` maintenance flag auto-quarantines intraday solar locks).
3. **`<$500` NAV `>=3`-Leg Hard Block & `>$500` Certification Gate (`§7.1b`):** [`check_multileg_3plus_nav_and_certification_gate`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/stage_c_zero_loss_velocity.py) blocks all `>=3`-leg sequential CLOB bundles below `$500` (`PURE_RISKLESS_MULTILEG_3PLUS_BLOCKED_BELOW_500_NAV`) unless executor-verified Safe-router atomicity or ERC-1155 inventory covers `N-1` legs, and keeps `>=3`-leg bundles gated above `$500` until `certified_multileg_3plus_live_enabled = True`.
4. **Decoupled `$30.00` Riskless Ruin Floor (`POL-13` / `R-01`):** Preserves monotonic directional `hard_ruin_floor_usd: 62.0` while adding `riskless_hard_ruin_floor_usd: 30.0` in [`polymarket_live_harvester.py`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py) & [`polymarket_strategy_and_risk.json`](file:///C:/Users/Anton/source/repos/Dominus/config/polymarket_strategy_and_risk.json), preventing a `100%` riskless-arb blackout (`-$30` to `-$75/mo`) if `KMIA` settles at `$0.00` (`tot_equity -> $47.38 < $62.00`).
5. **`24h` Last-Known-Good Graduation Cache (`POL-16` / `R-03`):** [`load_alpha124_graduation_maps_with_lkg_cache`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/stage_c_zero_loss_velocity.py) keeps graduated live sleeves active across transient `>300s` `alpha124` restarts while failing closed after `24h`.
6. **Tightened `5.0s` WS Book Staleness, `3`-Poll Blind Cancel, Mid-Rest UMA Dispute Cancel & Fail-Closed Accounting Halt (`§7.1c`):** Immediate `"ADVERSE"` maker cancel on `umaResolutionStatus == "disputed"`, book inversion, or `>5.0s` (`1.0s` `S2`) WS staleness, plus immediate order halt on `ACCOUNTING_SAFEGUARD_ACTIVE.json`.
- **Projected Post-Remediation Run-Rate at `$47.38` Cash:** **`+$0.92 to +$1.42/day` gross -> `+$0.10 to +$0.60/day` (`+$3.00 to +$18.00/mo`) net AFTER `$0.822/day` VM burn** (`112%–173%` infra coverage with zero directional risk; scales to **`+$37/mo` net** if `KMIA` recovers `$50.51`, and **`+$227–$455/mo` net** at `$500` NAV).

---

## (c) MOF — Venue Eligibility, Stage G Forensics & On-Chain Primitives

Full cross-venue and on-chain audits are in [VENUE_CAPABILITY_MATRIX.md](file:///C:/Users/Anton/source/repos/Dominus/VENUE_CAPABILITY_MATRIX.md) and [POLYMARKET_ONCHAIN_MOF_AUDIT.md](file:///C:/Users/Anton/source/repos/Dominus/POLYMARKET_ONCHAIN_MOF_AUDIT.md).

1. **Public Data `HTTP 200` != Legal Trading Eligibility (`CA-ON` + `FI`):**
   - All 6 Stage G connectors (`polymarket`, `limitless`, `predict_fun`, `sx_bet`, `stx_ontario`, `forecastex`) + `hyperliquid` stream read-only public data (`5.58h–11.53h` of `168.0h` Gate `M4.2` collected), **but `0` cross-venue pairs are simultaneously legal in `CA-ON`, credentialed, and post-delay net-profitable today**:
     - `Polymarket`, `Limitless`, `Predict.fun`, `SX Bet`, and `Hyperliquid` perps restrict `CA-ON` retail accounts.
     - `STX Ontario` (`AGCO/iGO`, `CAD` fiat sports) and `ForecastEx / IBKR Canada` (`CIRO`, `3.38%` APY macro/climate) are **100% legal in `CA-ON`**, have **`0` overlapping contract categories** with each other, and require Ontario session/IP residency (never routed through `FI`).
2. **Stage G Shadow Forensic Cleansing (`544 / 803` Contaminated Rows Quarantined):**
   - Exposed that `shadow_graduation_report.json`'s apparent `+$1,542.42` profit (`G5 = True`) was driven by **`427` Dota 2 `-game1`/`-game2` sub-game vs BO3 series Double-Zero pairs (`+$4,081.09`)** and **`544 / 567` fabricated `100.0`-share keyless `sx_bet` summary rows**, while real-L2 `polymarket <-> limitless` Taker-Taker (`240` signals) lost **`-$1,224.78`** post-delay due to Limitless's `takerDelayMs = 250–500ms` crypto (`1,500ms` sports) speedbump.
   - Remediated all **7** Stage G Double-Zero, `5m`-vs-`15m` horizon, relative-vs-fixed strike, `+24h` Limitless vs back-to-back NBA timestamp, leg-scoped synthetic quarantine, startup/30s watchdog heartbeat, and SQLite compaction defects in [`cross_venue_riskless_shadow.py`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_riskless_shadow.py), [`cross_venue_l2_and_baskets.py`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_l2_and_baskets.py), [`cross_venue_telemetry_and_watchdog.py`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_telemetry_and_watchdog.py), and [`shadow_cross_venue_riskless_probe.py`](file:///C:/Users/Anton/source/repos/Dominus/scripts/shadow_cross_venue_riskless_probe.py).
3. **Capital Consolidation & Gasless On-Chain Primitives (`$0.00` Gas):**
   - **Keep `100%` of active capital (`$47.38`) in single-venue Polygon `pUSD` below `$525` NAV (`Gate M5.2`)** — splitting `$47.38` leaves `$23.69/venue` (`< 1` standard `$25` clip).
   - All 4 Polymarket on-chain primitives (`mergePositions`, `splitPosition`, `redeemPositions`, `NegRiskAdapterV2.convertPositions`) execute at **`$0.0000` (`0.0 bps`) POL gas** via Builder Relayer V2 (`MAX` `pUSD` & `isApprovedForAll` verified on `0x013A...`), saving **`+20 to +200 bps`** vs crossing CLOB spreads + taker fees.

---

## (d) ENGINEERING — Reliability, 13-Stage Latency, Governance & QA Gate

1. **Phase 0 Swapless `3,907 MiB` Host RAM & SQLite Stabilization (`F-01`, `F-02`, `F-04`, `F-06`):**
   - `kraken-finland` runs with **`MemorySwapMax=0B`** (`0` swap). Remediated `alpha124`'s ~75-min `1.21 GiB` glibc-arena OOM loop and `recorder`'s `1,007 MiB` footprint via `_slim_raw_gamma_event` (`>85%` payload cut), `_slim_rest_book` (`<=25` levels), WS book level caps (`<=40`/`<=50`), `riskless_bus_only` skip of 30-min `verify_and_log_resolution` tasks, `TCPConnector` pool limits (`24`/`8`), and `60s`/`120s` cache eviction + `libc.malloc_trim(0)` ([alpha_124_shadow_daemon.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/alpha_124_shadow_daemon.py), [polymarket_terminal_recorder.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_terminal_recorder.py)).
   - Cut Stage G `shadow_telemetry.sqlite3` (`518.88 MiB`, `+620 MiB/day` pre-fix) write amplification by **`85–95%`** via `600s` unchanged-BBO/spread dedup, `300s` rejection bucketing, and `48h` `l2_json='{}'` compaction.
2. **Phase 4 13-Stage Hot-Path Latency Optimization (`$0/mo` Infra Verdict — [LATENCY_BASELINE.md](file:///C:/Users/Anton/source/repos/Dominus/LATENCY_BASELINE.md)):**
   - Local hot-path Python compute (Stages 3–9) already runs in **`0.56 ms` `p50`** (`3.12 µs` `PreSignedOrderLadderCache` / `226.6 µs` `FastV2OrderSigner` `coincurve` Safe); network/exchange time (`51.3 ms` warm HTTP RTT; `69.8 ms` Maker ACK; `252.2 ms` Taker ACK incl. **`~200 ms` server-side `itode=True` speedbump**) accounts for `96–99%` of wall time.
   - Upgraded `PolymarketLiveHarvester.save_state()` (`104` call sites) and `/dev/shm` JSON helpers to `orjson` bytes I/O + PID+TID `.tmp` atomic rename ([polymarket_live_harvester.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py), [net_alpha_opportunity_engine.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/net_alpha_opportunity_engine.py)), slashing `ext4` `save_state()` event-loop blocking **`4.10x` (`53.20 -> 12.97 ms` at `n=136`) to `8.25x` (`171.82 -> 20.83 ms` at `n=500`, `-150.99 ms` `p50`)**.
   - **Strict Infra Decision:** **`$0/mo` paid VM changes at `$47.38` cash** (`+$15–$45/mo` London migration yields `-$13.80` to `-$43.80/mo` net EV). Re-evaluate `$0–$5/mo` delta migration to `2-core / 4–8 GB` `eu-west-2` (London) only at **`>= $500` liquid NAV**.
3. **Governance, Emergency CLI & Integrated QA Gate ([POLICY_AUDIT.md](file:///C:/Users/Anton/source/repos/Dominus/POLICY_AUDIT.md), [AGENTS.md](file:///C:/Users/Anton/source/repos/Dominus/AGENTS.md), [QA_EVIDENCE.md](file:///C:/Users/Anton/source/repos/Dominus/QA_EVIDENCE.md)):**
   - Audited `26` policies & `44` restrictions; hardened [`paa_cli.py`](file:///C:/Users/Anton/source/repos/Dominus/scripts/paa_cli.py) (`emergency-stop [--include-trading]` / `resume`) and [`audit_losing_trades.py`](file:///C:/Users/Anton/source/repos/Dominus/audit_losing_trades.py) (`is_harvester_state_restart_safe` across passive post-expiry `KMIA` UMA locks); staged 3 protected-file patches under [`v50_owner_control_package`](file:///C:/Users/Anton/source/repos/Dominus/paa_staging/proposals/v50_owner_control_package/APPLY_AND_ROLLBACK.md).
   - **Integrated Local QA Gate:** `166/166` `DEPLOY_MANIFEST` files verified, `PermissionGate.inspect_candidate_diff() == (True, [])`, `PermissionGate.inspect_config_envelope() == (True, [])`, `crlf=0` across all campaign files & bundles (`polymarket_all_in_one.py` `< 1 MB`, `polymarket_alpha124_all_in_one.py` `< 1 MB`), and **100% pass rate** across all v5.0 & core regression suites.

---

## (e) TOP 3 IMMEDIATE PRIORITIES

1. **Priority 1 (`P0` — Before `KMIA` UMA DVM Settlement): Promote Integrated v5.0 Release & Systemd Resource Weights to `kraken-finland` (Approval Package 1)**
   - Activates `riskless_hard_ruin_floor_usd = $30.00` (preventing a `$47.38 < $62.00` live riskless blackout if `KMIA` settles at `$0.00`), enforces the `$7.11–$7.13` (`15%` reconciled NAV) multi-key event cap (fixing `D1` cash starvation & `$8.92` `MKR_LOCK1` over-sizing), deploys `orjson` `save_state()` (`-40 to -151 ms` stall), stabilizes swapless RAM (`F-01`), and quarantines the `544` contaminated Stage G rows.
2. **Priority 2 (`P0` — Governance & Accounting Hygiene): Apply Staged Protected-Files Owner Package (`v50_owner_control_package` — Approval Package 2)**
   - Atomically applies the 3 human-gated patches to `permissions.py` (`POL-05` per-violation scope check + TTL/replay guard + `POL-08` binary-diff block), `builder_and_deployer.py` (`POL-07` UMA-disputed safe-restart parity), and `paa_autonomy_config.json` / `budget.py` (`POL-10` `$0.0730 -> $0.0343/hr` true GCP VM cost, removing `+$27.89/mo` phantom accounting loss).
3. **Priority 3 (`P1` — Zero-Risk Cash Recovery & `KMIA` Case Tracking): Monitor Official Polymarket `KMIA` Case (`$50.51` Cost Basis) & Optionally Sweep `$1.00 USDC.e` Signer EOA Cash (Approval Package 3)**
   - Keep the `4` `KMIA` Nov 7 positions `100%` untouched until official UMA/Polymarket resolution; optionally transfer & wrap the orphaned `$1.000000 USDC.e` from `0x9703...` -> `0x013A...` `pUSD` (`+2.11%` instant risk-free bankroll boost to `$48.38` for `~$0.001` POL gas).

---

## (f) CONCENTRATED 30-DAY MILESTONE PLAN (`Day 1..30`)

| Window | Milestone & Concrete Actions | Owner | Dependencies | Acceptance Criteria | Quantified Net EV / Risk Impact |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Days 1–2** | **v5.0 Production Sync, Controlled Flat/Frozen Restart, Systemd `CPUWeight`/`MemoryMax` Tuning & Owner Protected Package Apply** | Human Operator (via Packages 1 & 2) | Local integrated QA gate (`100%` green) & flat non-`KMIA` book (`is_harvester_state_restart_safe == True`) | `166/166` remote SHA-256 parity; `live-harvester` `CPUWeight=400`; `alpha124` RSS `< 800 MiB` (`0` OOMs over `24h`); `shadow_graduation_report.json` recomputed (`544` contaminated rows quarantined); `4` `KMIA` lots untouched. | **`+$30 to +$75/mo`** blackout avoided (`POL-13`) + **`+$18 to +$45/mo`** lockup avoided (`§7.1a`) at **`$0.00/mo`** extra infra. |
| **Days 3–5** | **Post-Deploy Live Funnel & Velocity Verification (`D1` + `Stage C` + `CAL1`/`COND1` + Optional `$1.00` EOA `USDC.e` Sweep)** | Operator + `PAAMonitor` | Days 1–2 live sync | `[D1 LIVE BOX SKIP] INSUFFICIENT_BOX_COLLATERAL_HEADROOM` reduced `>= 75%`; `max_single_event_exposure <= 0.15 × reconciled_nav_usd` (`<= $7.13`); `save_state` `p95 < 25 ms`; `live_bankroll` reconciled `$0.00` drift (`$48.38` if Package 3 run). | Unlocks **`+$0.92–$1.42/day` gross (`+$0.10–$0.60/day` net after `$0.822/d` VM)** + **`+$1.00`** instant cash. |
| **Days 6–10** | **Read-Only Stage G Shadow Hydration (`SX_BET_API_KEY` + `STX_API_KEY_ID`) & Clean `168h` Clock Progression** | Operator (self-service keys in `/etc/polymarket-shadow.env`) | Days 1–2 Stage G Double-Zero & SQLite patch | `polymarket-cross-venue-shadow-watchdog.service` `0` false staleness failures; `shadow_telemetry.sqlite3` growth `< 35 MiB/day`; `0` unquarantined Double-Zero or synthetic `LIVE_VERIFIED` signals. | Truthful L2 cross-venue discovery at **`$0.00`** capital fragmentation risk. |
| **Days 11–15** | **`KMIA` Nov 7 UMA / Polymarket Case Settlement Reconciliation & Automatic Tier Re-Anchoring** | `PAAAccountant` + Operator review | Official UMA DVM / Polymarket support resolution on `6707502` & `6707503` | Whether `KMIA` pays `$0.00` (`NAV = $47.38+`) or `$35.00–$50.51` (`NAV = $82–$99+`), `PAAAccountant` reconciles `pUSD` within `$0.01`, `0` ruin-floor freeze occurs, and `15%` event cap auto-scales (`$7.11 -> $12.35–$14.85` on win). | **`$0` downtime on `$0` outcome**; **`+$37.35/mo` net post-infra run-rate** on full `$50.51` recovery. |
| **Days 16–22** | **Stage G `168.0h` Clean Shadow Audit & V2 Executor Hygiene Staged Proposal (`USDC.e` Merge + `NEG_RISK_ADAPTER_V2` Fallback)** | `PAADirector` (staged proposal) + Operator | `>= 168.0h` post-quarantine Stage G runtime | `certification_report.json` audited (`0` Double-Zero); staged unit-tested patch for legacy `USDC.e` `CTF_V1.mergePositions` + `NEG_RISK_ADAPTER_V2` self-redemption fallback verified in detached worktree. | Hardens `100%` first-try self-redemption & merge across legacy + V2 conditions; keeps cross-venue capital split at **`0%` while NAV `< $525`**. |
| **Days 23–30** | **Month-1 Compounding Checkpoint, Git Baseline Advance (`F-03`) & Milestone `$150` (`M3.2`) Readiness Gate** | Operator | 30-day verified cash ledger (`0` `RISKLESS_PAA` principal losses) | Clean Git commit baseline (`REL_BASELINE_*` advanced past `4fdb2198`); realized 30d riskless WR `= 100%` (ex-retired legacy); net cash growth positive after `$24.67` VM cost; `$150` `pre_split` / WFO gates evaluated strictly on undisputed cash. | Establishes self-funding compounding trajectory toward **`$150 -> $253 -> $500` NAV** without adding `$1` of fixed burn. |

---

## (g) CONCISE OWNER APPROVAL PACKAGES

> **Safety Guarantee:** Nothing below has been executed on `kraken-finland`. Every package includes a read-only pre-check, exact apply command, post-check, and 1-command rollback, and **strictly preserves the 4 disputed `KMIA` Nov 7 positions**.

### Package 1 — Production Sync, Systemd Resource Tuning & Safe Controlled Restart
- **Scope:** Syncs the `166` verified manifest files + v5.0 bundles (`F-01`, `F-02`, `F-04`, `§7.1a–c`, `POL-13/15/16/20`, `orjson` `save_state`, Stage G 7 fixes), sets `CPUWeight=400` on `polymarket-live-harvester.service` vs `CPUWeight=50` / bounded `MemoryMax` on shadow/recorder units, runs `ShadowTelemetryStore.quarantine_contaminated_sports_and_recompute()`, and restarts daemons **only when `is_harvester_state_restart_safe()` confirms `0` non-`KMIA` active trades**.
- **Pre-Check (Local Dry-Run + Remote Flat/KMIA Safety Check):**
  ```powershell
  & "C:\Program Files\LibreOffice\program\python.exe" scripts/deploy_polymarket_live.py --dry-run
  ssh kraken-finland "cd /home/skybullet1987/quant_pipeline && ./venv/bin/python audit_losing_trades.py --check"
  ```
- **Apply (Interactive Owner Terminal Only):**
  ```powershell
  # 1. Snapshot live state backup before sync:
  ssh kraken-finland "cp -p /home/skybullet1987/quant_pipeline/data/polymarket/live_harvester_state.json /home/skybullet1987/quant_pipeline/data/backups/live_harvester_state_pre_v50_$(date -u +%Y%m%dT%H%M%SZ).json"

  # 2. Deploy verified manifest & restart safely across frozen KMIA locks once flat:
  & "C:\Program Files\LibreOffice\program\python.exe" scripts/deploy_polymarket_live.py
  ssh kraken-finland "cd /home/skybullet1987/quant_pipeline && ./venv/bin/python -c 'from pathlib import Path; from src.polymarket_research.cross_venue_telemetry_and_watchdog import ShadowTelemetryStore; print(ShadowTelemetryStore(Path(\"data/cross_venue_shadow\")).quarantine_contaminated_sports_and_recompute())'"

  # 3. Apply zero-cost systemd CPU/RAM contention priorities (swapless 3,907 MiB host protection):
  ssh kraken-finland "systemctl --user set-property polymarket-live-harvester.service CPUWeight=400 && systemctl --user set-property polymarket-recorder.service CPUWeight=80 MemoryMax=750M && systemctl --user set-property polymarket-alpha124-shadow.service CPUWeight=50 MemoryMax=900M && systemctl --user set-property polymarket-cross-venue-shadow.service CPUWeight=50 MemoryMax=450M && systemctl --user restart polymarket-recorder.service polymarket-alpha124-shadow.service polymarket-cross-venue-shadow.service && python3 /home/skybullet1987/quant_pipeline/scripts/paa_flat_harvester_redeploy_once.py"
  ```
- **Rollback:** Restore pre-v5.0 backup tarball / `git checkout -- src/ scripts/ config/polymarket_strategy_and_risk.json` on `kraken-finland` and run `python3 scripts/paa_flat_harvester_redeploy_once.py`.

---

### Package 2 — Staged Protected-Files Owner Governance Package (`v50_owner_control_package`)
- **Scope:** Applies the 3 audited human-only patches ([APPLY_AND_ROLLBACK.md](file:///C:/Users/Anton/source/repos/Dominus/paa_staging/proposals/v50_owner_control_package/APPLY_AND_ROLLBACK.md)) to `src/paa_os/permissions.py` (`POL-05`, `POL-08`), `src/paa_os/builder_and_deployer.py` (`POL-07`), and `config/paa_autonomy_config.json` + `src/paa_os/budget.py` (`POL-10` `$24.67/mo` VM rate), creating automatic backups in `data/polymarket/paa/live_backups/v50_owner_control_package/`.
- **Dry-Run Verification (Zero Writes):**
  ```powershell
  & "C:\Program Files\LibreOffice\program\python.exe" paa_staging/proposals/v50_owner_control_package/apply_or_rollback_owner_package.py --verify-dry-run
  ```
- **Apply (Local + Remote Interactive SSH After Syncing `paa_staging/proposals/v50_owner_control_package/`):**
  ```powershell
  & "C:\Program Files\LibreOffice\program\python.exe" paa_staging/proposals/v50_owner_control_package/apply_or_rollback_owner_package.py --apply
  ssh kraken-finland "cd /home/skybullet1987/quant_pipeline && ./venv/bin/python paa_staging/proposals/v50_owner_control_package/apply_or_rollback_owner_package.py --verify-dry-run && ./venv/bin/python paa_staging/proposals/v50_owner_control_package/apply_or_rollback_owner_package.py --apply"
  ```
- **1-Command Rollback:**
  ```powershell
  & "C:\Program Files\LibreOffice\program\python.exe" paa_staging/proposals/v50_owner_control_package/apply_or_rollback_owner_package.py --rollback
  ssh kraken-finland "cd /home/skybullet1987/quant_pipeline && ./venv/bin/python paa_staging/proposals/v50_owner_control_package/apply_or_rollback_owner_package.py --rollback"
  ```

---

### Package 3 — Optional `$1.000000 USDC.e` Signer EOA (`0x9703...`) -> Funder `pUSD` (`0x013A...`) Sweep
- **Scope:** Transfers the untracked `1.000000 USDC.e` (`0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174`) sitting on Signer EOA `0x9703b71686219d34869e8fb89a93263f9e0d50a5` into Funder Deposit Proxy `0x013A2474454fBd8738cff6a7f204eF1bc377F4e9` and wraps 1:1 into `pUSD` (`0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB`), leaving `~41.81 POL` (`~$3.70`) untouched on `0x9703...` as emergency gas reserve.
- **Economic Impact:** **`+$1.0000` (`+2.11%`) instant risk-free liquid `pUSD` bankroll increase** (`$47.38 -> $48.38`) for `~$0.001` POL gas (`> 1.2 days` of VM overhead recovered immediately).
- **Read-Only Balance Pre-Check:**
  ```powershell
  ssh kraken-finland "cd /home/skybullet1987/quant_pipeline && ./venv/bin/python src/polymarket_research/check_polymarket_balance.py"
  ```
- **Execution Note:** Because autonomous agents are strictly forbidden from constructing raw `ERC20.transfer` calls (`FORBIDDEN_CREDENTIAL_OR_TRANSFER_PATTERN` in [`permissions.py`](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L161-L170)), execute only from an interactive human operator session (or Polymarket UI deposit flow to `0x013A2474454fBd8738cff6a7f204eF1bc377F4e9`) when convenient, then verify `check_polymarket_balance.py` reports `48.377122 pUSD` before the next `PAAAccountant` cycle.
