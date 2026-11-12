# DOMINUS v5.2 — Riskless Full-Throttle Strategy, Attribution & Empirical Projections Report

**Campaign Standard:** DOMINUS v5.2 Riskless Full-Throttle (`RISKLESS_PAA`)  
**Projection Model:** `v5.2_full_throttle_riskless_velocity` ([scripts/polymarket_daily_projections.py](scripts/polymarket_daily_projections.py))  
**Reconciled Baseline Timestamp:** `2026-11-11 22:51 UTC`  
**Operating Invariants:** `directional.riskless_only_mode = true` | `proposal_only_live_promotion = true` (`< $5,000` NAV, `D-002`) | `CA-ON` Jurisdiction Gate (`D-008`) | `MemorySwapMax=0B` (`D-010`)

---

## 1. Full-Universe Architecture & New 14-Family (`A..N`) Riskless Engine

Prior to the Full-Throttle campaign, DOMINUS v5.1 discovered only `~3,530` active markets (`1.75%` of the observable Polymarket universe) due to hardcoded top-volume binary caps (`340` -> `1,200`), category-only pagination, and single-shard WebSocket limits. Waves 1–3 replace heuristic sub-sampling with exhaustive, fee-exact, rule-verified full-universe surveillance:

### 1.1 Exhaustive Universe Discovery & Two-Layer Surveillance
- **[`FullUniverseRegistry`](src/polymarket_research/full_universe_discovery.py)** (`data/universe/market_registry.sqlite3` & `data/universe/coverage_snapshot.json`):
  - Enumerates **`100.0%` of observable public Gamma & CLOB markets**: **`19,257` events**, **`375,963` total markets**, **`201,218` active orderbook-enabled markets**, **`402,240` outcome token IDs**, **`34,428` dynamic taker-fee markets**, and **`549–606` UMA proposed markets**.
  - Separates **Discovery Completeness** (`100%` retained with normalized metadata) from **Execution Eligibility** via machine-readable skip codes (`ORDERBOOK_DISABLED`, `MISSING_TOKEN_IDS`, `CLOSED_OR_ARCHIVED`, `AUGMENTED_PLACEHOLDER_OUTCOME`, `ZERO_RESTING_DEPTH`).
  - Operates under **`<120 MiB` peak RSS** using streaming SQLite batch commits and `indicative_prices_json` `bestBid`/`bestAsk` seeding.
- **[`TwoLayerSurveillanceScheduler`](src/polymarket_research/full_universe_discovery.py)**:
  - **Layer A (Full-Universe Background Sweep):** Guarantees zero active market starvation across all `201,218` orderbook markets via bounded rotating sweeps.
  - **Layer B (High-Priority Adaptive Book Polling):** Batches `POST https://clob.polymarket.com/books` (`400` tokens/batch, `sock_read` timeout isolation, `1,000`-book inline LRU cap) + `5 x 250 = 1,250` sharded WebSocket subscriptions.

### 1.2 Proposition Graph, Rule-Equivalence Veto & 14 Structural Arbitrage Families (`A..N`)
- **[`MarketPropositionGraph`](src/polymarket_research/market_proposition_graph.py) & [`universal_arb_verifier`](src/polymarket_research/universal_arb_verifier.py):**
  - Builds **`6,097` verified logical edges** (`EQUIVALENT`, `COMPLEMENT`, `IMPLIES`, `MUTUALLY_EXCLUSIVE`, `EXHAUSTIVE_PARTITION`, `CUMULATIVE_TIME_LADDER`, `MONOTONIC_STRIKE_LADDER`) across binary, scalar, calendar, and `NegRisk` markets.
  - Enforces **fail-closed semantic trap vetoes** (`514` cataloged rule mismatches; **`313` pseudo-arbitrage rule traps blocked** in the latest full sweep, preventing source-authority, timezone, `Other`-bucket, or overtime/regulation mismatches from ever reaching live execution).
- **[`FullThrottlePipeline`](src/polymarket_research/full_throttle_pipeline.py) & [`NetAlphaOpportunityEngine`](src/polymarket_research/net_alpha_opportunity_engine.py) (`14` Families `A..N`):**
  - **Class A (`SINGLE_MARKET_COMPLETE_SET`):** `Family A` Binary YES+NO Complete Set (`C1`/`ZEROFEE1`), `Family B` Closed Exhaustive `NegRisk` All-YES Complete Set (`NR1`), `Family C` `NegRisk` `m=2` NO-Subset Convert (`NR2`), `Family D` Atomic Overround Split/Sell (`PreSplitGun` @ `>=$140`).
  - **Class B (`TWO_LEG_CROSS_MARKET_DOMINANCE`):** `Family E` Monotonic Strike Ladder Dominance (`FT_STRIKE1` / `M3` / `B3`), `Family F` Calendar / Deadline Survival Monotonicity (`CAL1`), `Family G` Same-Event Cross-Market Duplicate / Implication Dominance (`FT_DUP1` / `COND1` / `LP1`), `Family H` Same-Oracle Multi-Horizon Crypto/Metals Dominance (`D1` / `D1_4H` / `D1_QUIET`).
  - **Class C (`POST_CLINCH_DETERMINISTIC_CARRY`):** `Family I` Objective UMA Proposed / Liveness Bond Carry (`BOND1` / `UMA_READY1`), `Family J` Official-Source Pre-Proposal Clinch (`BOND2` / `W_PRUNE1` routine METAR dead-NO / `WS_CLINCH_SNIPER`).
  - **Class D (`HEDGED_MAKER_AND_TIER_GATED`):** `Family K` `>=3`-Leg Atomic `NegRisk` Partition Bundles (quarantined `< $500` NAV per `D-007`), `Family L` `0 bps` `postOnly` Hedged Maker & Fee-Rebate Capture ([`HedgedMakerShadowQuoter`](src/polymarket_research/full_throttle_pipeline.py)), `Family M` Regulated `CA-ON` Cross-Venue Equivalence (`Stage G` @ `>=$253` NAV), `Family N` Dormant Near-Arb Stalking ([`DormantOpportunityStore`](src/polymarket_research/full_throttle_pipeline.py) — **`1,200` `<=50 bps` near-arbs** with **`1,165` hot tokens** dynamically pinned to live WebSockets).

---

## 2. Wave 1–3 Upgrades to Live & Shadow Execution Sleeves

| Subsystem | Bottleneck Diagnosed (`#60` / `#64`) | Wave 1–3 Production Remediation | Verified Impact |
| :--- | :--- | :--- | :--- |
| **`alpha_124_shadow_daemon.py` UMA Bond Loop** | `scan_uma_resolution_bonds` was serialized behind `283` `NegRisk` slates (`~7,000` tokens) inside `_bg_tradfi_task`, causing `7.5m` `BOND1` emission droughts. | Extracted independent **`18.0s` `_run_bg_uma_bonds` task**, expanded objective UMA discovery to **`606` markets** (`60` `1M`-boosted hot bonds), and extended on-chain verification cache (`90s–240s`). | Continuous `18s` `BOND1` maker/taker emission with `0` head-of-line blocking from `NegRisk` sweeps. |
| **`alpha_124_shadow_daemon.py` `/books` & Swapless RAM** | `MemoryCurrent` hit `1,073.7 / 1,100.0 MiB` due to `7,000`-token `active_nrc` bursts, `rest_cache` growth, and raw Gamma `events`/`chats` dict bloat. | Added `36` hot + `36` rotating `active_nrc` window (`<60s` full rotation), inline `rest_cache <= 800` trim inside `fetch_books_batch`, `sock_read >= 6.5s` timeout isolation, and `UMA` dict slimming + `malloc_trim(0)`. | Eliminates `/books` semaphore timeouts and bounds steady-state RSS safely below the `1,100 MiB` swapless ceiling (`D-010`). |
| **`alpha_124_shadow_daemon.py` Zero-Fee Binary & WS Matrix** | `340`-binary top-volume cap and `15 bps` clamp starved `C1`/`ZEROFEE1` mergeable candidates; `alpha124_shadow_state.json` went `360s` stale during long scans. | Expanded `zerofee_general_binaries` to **`1,200` markets** (`>= 15.0 bps` net floor), upgraded sharded WS to **`5 x 250 = 1,250` tokens**, and tightened `_run_bg_state_heartbeat` to **`45s`** with `catalog_counts` + `live_bridge_telemetry` in both state & mirror files. | `3.5x` binary book coverage, `<45s` Command Center telemetry freshness, and live IPC emit attribution per sleeve. |
| **`stage_c_zero_loss_velocity.py` & `polymarket_live_harvester.py`** | `Stage C` `15 bps/hr` / `<=8h` lockup rejected `18–24h` `BOND1`/`C1`/`CAL1` carries (`8–14 bps/hr`); missing `opp_token_id` caused avoidable single-leg skips; `120s` re-peg churned FIFO #1 priority. | Tuned seed gate to **`>= 7.5 bps/hr` & `<= 24.0h`** (`Stage C`), wired `opp_token_id` resolution, raised sticky FIFO #1 hold to **`900s` (`15m`)**, and bridged certified 2-leg `CLASS_A/B` (`FT_DUP1`, `FT_STRIKE1`) into live `RISKLESS_PAA`. | Preserves FIFO #1 queue priority (`sign=0.56–1.04ms`, `post=73–81ms`) while doubling eligible high-certainty daily turns. |

---

## 3. Highest-Conviction Profit Drivers Ranked by Velocity, Capacity & Readiness

At the current **`$48.70` True Worst-Case Guaranteed-Floor NAV** (`<= $7.30` per correlated event under the `15%` `D-006` concentration cap), capital velocity (`bps/hr`) dominates raw per-ticket margin:

| Rank | Profit Driver / Sleeve Family | Status at `$48.70` NAV | Empirical Net Edge & Velocity | Est. Daily CLOB Capacity | Unlock / Scaling Gate |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **1** | **`D1` Same-Oracle & Quiet-Book Boxes** (`9` Crypto + `XAU/XAG`, `<70ms` Batch Cancel-on-Arb) | **LIVE (`RISKLESS_PAA`)** | `150–260 bps` net/box (`5m–4h` hold = **`40–300+ bps/hr`**) | `$60–$220` clip; `$15–$52/day` | Active now; preempts slowest non-FIFO-#1 `BOND1` makers only on `>=200 bps` arbs. |
| **2** | **`Full-Throttle CLASS_A/B` 2-Leg Bridge + `1,200`-Bin `C1` Relayer V2 Merge** (`FT_DUP1`, `FT_STRIKE1`, `CAL1`, `COND1`, `NR2 m=2`, `ZEROFEE1`) | **LIVE (`RISKLESS_PAA`)** | `15–185 bps` net; `$0`-gas Relayer V2 merge (`~2.5s`) or `<=24h` (`>=7.5 bps/hr`) | `$55–$165` clip; `$12–$38/day` | Active now across `71` `CAL1` ladders, `283` `NegRisk` slates (`m=2`), and `1,200` `0%`-fee binaries. |
| **3** | **`606`-Market `BOND1` (`18s` Loop) + `BOND2` + `W_PRUNE1` Carry** (`0%` Maker + `<1h` `0.9975` Taker) | **LIVE (`RISKLESS_PAA`)** | `35–95 bps` net (`18–45 bps/hr`; active `6947122` = **`36.42 bps/hr`**) | `$220+` across `<=6` uncorrelated events (`$7.5–$22/day`) | Active now (`<=15%` NAV per event; `0` disputed/ambiguous subjective markets). |
| **4** | **`WS_CLINCH_SNIPER` (`MKR_LOCK1` / `SP2` / `CL1`)** (`1,250`-Token Sharded WS) | **LIVE (`RISKLESS_PAA`)** | `65–140 bps` net (`<=1h` post-clinch = **`65–200+ bps/hr`**) | `$12–$65` clip; `$6.5–$21/day` | Active now (`S2` TWAP remains paused until explicit WFO re-certification). |
| **5** | **`MKR_REWARD_LOCKED_CARRY` + `Family L` `0 bps` `postOnly` Hedged Maker** | **SHADOW (`+$0.17` `0`-Dir Fills)** | `0 bps` maker + `15%–25%` fee rebate / LP reward (`~135 bps/day` on locked pair) | `$18–$75` pool; `$2.5–$10/day` | Auto-unlocks at **`>= $125` Undisputed Floor NAV** + owner approval for `Family L` live promotion. |
| **6** | **`PreSplitOverroundGunEngine` (`Family D`)** (`CTF.splitPosition` -> Dual Overround Sell) | **GATED (`>=$140` NAV)** | `80–160 bps` per `<3s` atomic split/recycle (`>200 bps/hr`) | `$15–$60` lot; `$8–$25/day` | Unlocks at **`>= $140`–`$150` Undisputed Floor NAV** (`M3.2`). |
| **7** | **Regulated `CA-ON` Cross-Venue Riskless (`Stage G` — `ForecastEx / IBKR` + `STX Ontario`)** | **SHADOW CERTIFYING** | `90–220 bps` cross-exchange lock (`0%` proxy/VPN spoofing, `D-008`) | `$25–$110` lot; `$5.5–$18/day` | Unlocks at **`>= $253` Undisputed Floor NAV** + `168.0h` uncontaminated `0`-Double-Zero certification. |
| **8** | **Atomic `>=3`-Leg `NegRiskAdapter` Partition Bundles (`Family K`)** | **QUARANTINED `< $500`** | `110–190 bps` full-slate partition edge | `$35–$140` lot; `$6.5–$22/day` | Strictly quarantined until **`>= $500` Undisputed Floor NAV** (`D-007`). |

---

## 4. Strict Non-Conflated Real-Trading vs Shadow Attribution (`D-009` & `Principle 8`)

Realized on-chain wallet `pUSD`, frozen disputed `KMIA` cost basis, and simulated shadow ledgers are **never summed or conflated**:

### 4.1 Authoritative On-Chain Wallet & Three Distinct Live NAVs (`kraken-finland`, `2026-11-11 UTC`)
1. **True Worst-Case Guaranteed-Floor NAV (`locked_floor_equity`):** **`$48.70`** (`$48.6951` = `$41.7441` free `pUSD` + `$6.9510` resting `BOND1` CLOB maker order on market `6947122`, `7 sh @ $0.9930`, plus **`$0.00` worst-case payout** on the 4 disputed `KMIA` positions). **All `v5.2` position sizing, `15%` concentration caps, and compounding projections anchor strictly to this floor.**
2. **Mark-to-Bid Liquidation NAV (`reconciled_nav_usd`):** **`$48.83`** (`$48.6951` cash/maker + `$0.1390` live CLOB bid across the `52.0` disputed `KMIA` shares).
3. **Persisted Harvester Book Equity (`total_account_equity`):** **`$99.21`** (`$48.6951` cash/maker + **`$50.51` cost-basis frozen `KMIA` UMA receivable** across markets `6707503` `35.0 NO` sh and `6707502` `17.0 YES` sh — `4/4` untouched per `D-001`).
4. **Signer EOA Gas Reserve:** `41.81 POL` (`~$3.70` gas reserve) + `$1.00 USDC.e` untracked EOA cash.

### 4.2 Closed Live Ledger vs Segregated Shadow Benchmarks
| Ledger / Environment | Execution Mode | Trade Count & Win Rate | Realized / Simulated Net P&L | Conflation Firewall |
| :--- | :--- | :--- | :--- | :--- |
| **Pure-Riskless Live Sleeves (`C1`, `D1`, `BOND1`, `CAL1`, `NR_M1`)** | **REAL ON-CHAIN `pUSD`** | **`79W / 0L` (`100.0%` WR)** (`77` baseline + `2` recent `BOND1` turns) | **`+$19.25`** (`+$17.93` baseline + `+$1.32` recent `BOND1` net) | Verified 1:1 against Polygon `pUSD` (`$0.0000` drift). |
| **Retired Directional / Lattice Historical Trades** | **HARD-DISABLED (`RISKLESS_PAA`)** | `30W / 11L` (`41` historical trades) | `-$73.34` (historical sunk cost) | Permanently disabled (`riskless_only_mode = true`). |
| **4 Disputed `KMIA` Nov 7 Positions (`6707502` / `6707503`)** | **FROZEN UMA DISPUTE (`D-001`)** | `4` open positions (`52.0` sh, `$50.51` cost) | `$0.00` floor / `+$1.49` if `$52.00` payout | Zero sell/unwind/merge/mutation (`D-001`). |
| **`alpha124` Shadow Daemon (`T1000` Reference Bankroll)** | **SIMULATED L2 SHADOW** | Multi-sleeve `T1000` paper book (`CAL1` `12W/0L +$40.80`, `D1` `51W/0L +$256.88` historical) | Non-cash `T1000` graduation telemetry only | Never added to wallet `pUSD` or live NAV. |
| **`Full-Throttle` Pipeline (`Family L` `HedgedMakerShadowQuoter`)** | **SIMULATED L2 SHADOW** | `0` unhedged directional fills (`postOnly` + instant hedge check) | **`+$0.17` shadow net P&L** | Segregated in `data/full_throttle/pipeline/dashboard_latest.json`. |

---

## 5. Empirical `v5.2` Compounding Projections & Milestone ETAs (`7d / 30d / 60d / 90d`)

> **Strict Non-Cash Disclaimer:** All figures below are **model-projected trajectories** from [scripts/polymarket_daily_projections.py](scripts/polymarket_daily_projections.py) (`v5.2_full_throttle_riskless_velocity`), enforcing `<= 92%` working-capital conservation, `<= 15%` per-event concentration (`D-006`), L2 orderbook slippage decay (`_depth_decay`), hard daily CLOB depth caps, and `0` quarantined/directional sleeves. Fixed `kraken-finland` VM cost (`$24.67/mo = $0.8223/day`, `+7.04 bps/hr` hurdle at `$48.70`) is explicitly deducted in the Post-VM Net columns.

### 5.1 Day-1 Velocity Decomposition at `$48.70` Reconciled Floor NAV
- **P25 Conservative (`~295ms` Finland RTT + queue/competition haircut):** **`+$1.04/day`** gross wallet (`+8.90 bps/hr`, **`+$0.22/day` net after `$0.8223/day` VM**) — `D1 $0.35` + `FT/C1 Merge $0.34` + `606-UMA BOND1/2 $0.24` + `WS Clinch $0.11`.
- **P50 Base (`kraken-finland` Full-Throttle Wave 3):** **`+$1.85/day`** gross wallet (`+15.83 bps/hr`, **`+$1.03/day` net after `$0.8223/day` VM**) — `D1 $0.64` + `FT/C1 Merge $0.60` + `606-UMA BOND1/2 $0.41` + `WS Clinch $0.20`.
- **P75 Upside (High-dispersion regime / `<12ms` Group-2 EU API-open execution):** **`+$3.02/day`** gross wallet (`+25.84 bps/hr`, **`+$2.20/day` net after `$0.8223/day` VM**) — `D1 $1.09` + `FT/C1 Merge $0.98` + `606-UMA BOND1/2 $0.62` + `WS Clinch $0.33`.

### 5.2 Primary Baseline — Worst-Case `$48.70` Guaranteed-Floor Schedule (`$0.00` `KMIA` Outcome)
| Horizon | Target Date (`UTC`) | P25 Wallet Equity | P50 Wallet Equity | P75 Wallet Equity | P50 Day Rate | Cum. VM Cost (`$0.8223/d`) | P25 Net After VM | P50 Net After VM | P75 Net After VM |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Day 1** | `2026-11-11` | `$49.74` | **`$50.55`** | `$51.72` | `+$1.85/d` | `$0.82` | `+$0.22` | **`+$1.03`** | `+$2.20` |
| **Day 7** | `2026-11-17` | `$56.44` | **`$63.19`** | `$74.04` | `+$2.30/d` | `$5.76` | `+$1.98` | **`+$8.73`** | `+$19.58` |
| **Day 14** | `2026-11-24` | `$65.37` | **`$81.67`** | `$111.17` | `+$2.92/d` | `$11.51` | `+$5.16` | **`+$21.46`** | `+$50.96` |
| **Day 30** | `2026-12-10` | `$90.89` | **`$144.88`** | `$289.76` | `+$5.14/d` | `$24.67` | `+$17.52` | **`+$71.51`** | `+$216.39` |
| **Day 60** | `2027-01-09` | `$168.56` | **`$439.94`** | `$1,112.73` | `+$14.60/d` | `$49.34` | `+$70.52` | **`+$341.90`** | `+$1,014.69` |
| **Day 90** | `2027-02-08` | `$320.03` | **`$971.45`** | `$2,182.11` | `+$19.33/d` | `$74.01` | `+$197.32` | **`+$848.74`** | `+$2,059.40` |
| **Day 180** | `2027-05-09` | `$1,214.81` | **`$2,980.75`** | `$5,713.73` | `+$24.10/d` | `$148.01` | `+$1,018.10` | **`+$2,784.04`** | `+$5,517.02` |
| **Day 365** | `2027-11-10` | `$3,601.50` | **`$7,454.01`** | `$13,026.78` | `+$24.18/d` | `$300.14` | `+$3,252.66` | **`+$7,105.17`** | `+$12,677.94` |

### 5.3 Milestone Unlock ETAs — Adverse `$48.70` Floor vs Favorable `$100.70` (`+$52` `KMIA` Recovery)
| Undisputed Floor Milestone & Strategic Unlock | From `$48.70` Floor (`$0` `KMIA`) — **P75 / P50 / P25** | From `$100.70` Floor (`+$52` `KMIA`) — **P75 / P50 / P25** |
| :--- | :---: | :---: |
| **`$100` Seed Consolidation** (`D1`/`C1` `$110–$120` box cap expansion) | **Day `13` / Day `20` (`Nov 30`) / Day `35`** | **Immediate (`Day 0` = `$100.70`)** |
| **`$150` Milestone `M3.2`** (`$140` `PreSplitOverroundGun` + `MKR_REWARD`/`Family L` + WFO review) | **Day `20` / Day `31` (`Dec 11`) / Day `55`** | **Day `7` / Day `12` (`Nov 22`) / Day `20`** |
| **`$253` `Stage G` Cross-Venue Gate** (`CA-ON`-legal `ForecastEx / IBKR` + `STX Ontario` after `168h` cert) | **Day `28` / Day `45` (`Dec 25`) / Day `80`** | **Day `16` / Day `25` (`Dec 05`) / Day `44`** |
| **`$500` Multi-Leg Atomic Tier (`D-007`)** (`>=3`-leg `NegRiskAdapter` partition bundles unlocked) | **Day `40` / Day `64` (`Jan 13`) / Day `113`** | **Day `28` / Day `45` (`Dec 25`) / Day `78`** |
| **`$1,000` Institutional Depth Tier** (`$165–$220` L1/L2 depth-capped multi-engine velocity) | **Day `57` / Day `92` (`Feb 10`) / Day `162`** | **Day `45` / Day `72` / Day `127`** |
| **`$5,000` Autonomy Promotion Gate (`D-002`)** (`proposal_only_live_promotion` graduation review) | **Day `162` / Day `264` (`Aug 01`) / Day `469`** | **Day `150` / Day `244` (`Jul 12`) / Day `433`** |
