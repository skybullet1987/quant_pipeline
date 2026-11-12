# DOMINUS — RISKLESS FULL THROTTLE: Phase I Holistic System Audit Baseline (`SYSTEM_AUDIT_BASELINE.md`)

**Campaign:** DOMINUS — RISKLESS FULL THROTTLE (Phase I / Section 2 Holistic Baseline Audit)  
**Author:** `@pipeline-shadow` (Agents 1, 8 & 10 Integration Lead)  
**Audit Timestamp (UTC):** `2026-11-11T17:49:00Z`  
**Operating Mode:** `MODE_2_SHADOW` Default Active (`RISKLESS_PAA`, `directional.riskless_only_mode = true`, `proposal_only_live_promotion = true`, Jurisdiction Gate = `CA-ON`)  
**Audited Codebase & Live Telemetry:** [polymarket_live_harvester.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py), [alpha_124_shadow_daemon.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/alpha_124_shadow_daemon.py), [polymarket_terminal_recorder.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_terminal_recorder.py), [cross_venue_riskless_shadow.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_riskless_shadow.py), [riskless_protocol_v2_expansion.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/riskless_protocol_v2_expansion.py), [riskless_machine_gun_engine.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/riskless_machine_gun_engine.py), [riskless_expansion_v6_engines.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/riskless_expansion_v6_engines.py), `src/paa_os/*`, [PROJECT_STATE.md](file:///C:/Users/Anton/source/repos/Dominus/PROJECT_STATE.md), and [DEPLOYMENT_STATUS.md](file:///C:/Users/Anton/source/repos/Dominus/DEPLOYMENT_STATUS.md).

---

## Executive Summary & Headline Empirical Findings

1. **Massive Universe Coverage Gap Quantified (`96.8%` of Active Events & `>99.4%` of Active Markets Omitted):**
   - Full untruncated live pagination of `https://gamma-api.polymarket.com/events/keyset?active=true&closed=false&limit=200&after_cursor=...` (`190` keyset pages in `73.07s` over gzipped TLS keep-alive, independently cross-verified by `@pipeline-shadow` and `@qa-auditor`) enumerates **`18,937–18,940` active unclosed events**, **`199,138–199,146` active sub-markets** (`199,084–199,092` with `enableOrderBook=true`), and **`398,096–398,188` tradable CLOB outcome token IDs** (`6,214–6,215` `negRisk` events, `1,822–1,912` `negRiskAugmented` events, `309–316` UMA `proposed` markets, and `123` UMA `disputed` markets).
   - By contrast, DOMINUS v5.1's primary discovery scanner ([`discover_all_markets`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/alpha_124_shadow_daemon.py#L2620-L3152)) fetches only `range(0, 600, 100)` (`600` top-volume events = **`3.17%` of active events**) plus ~45 hardcoded tag/series queries, truncates general `0%`-fee binaries at `max_markets=340` (`0.17%` of markets), caps `negrisk_convert_slates` at `[:40]` (`0.64%` of `6,215` `negRisk` events), and watches `<= 600` WS tokens (`0.15%` of `398,188` tokens).
2. **Three Critical Gamma API Pagination Traps Identified:**
   - **Trap 1 (`limit > 100` Silent Server Clamp):** `GET /events?limit=500` is silently clamped server-side to `100` events; loops checking `if len(batch) < requested_limit: break` terminate after page 1 (`100` events = `0.53%` of universe).
   - **Trap 2 (`offset >= 2200..3000` Hard HTTP 422 Wall):** Offset pagination fails with `HTTP 422 {"type":"validation error","error":"offset too large, use /events/keyset for deeper pagination"}` past `offset=2100` (`11.1%` of active events).
   - **Trap 3 (`after_cursor` Parameter Specificity):** On `/events/keyset`, passing `cursor=` or `next_cursor=` is silently ignored and returns page 1 (`100%` duplicate loop); **only `after_cursor=<next_cursor>` advances through all `190` pages**.
3. **Authoritative Live Production Host & Segregated Cash Baseline Verified (`2026-11-11T17:47Z`):**
   - All 4 user-scope systemd daemons on `kraken-finland` (`3,907 MiB` physical RAM, `1,341 MiB` available, `0 B` swap used under `MemorySwapMax=0B`) are **`active/running` with `NRestarts=0`**: `polymarket-live-harvester.service` (`263.3 MiB`), `polymarket-recorder.service` (`164.8 MiB`), `polymarket-alpha124-shadow.service` (`1,077.6 MiB`), and `polymarket-cross-venue-shadow.service` (`424.2 MiB`).
   - **Realized Live Wallet Cash (`0x013A2474454fBd8738cff6a7f204eF1bc377F4e9`):** **`$48.695132` (`$48.70`) liquid `pUSD`** (`$48.83` mark-to-bid NAV; `$48.70` worst-case floor NAV; `$99.21` book equity including `$50.51` across the `4` untouched disputed `KMIA` Nov 7 positions; `77W/0L` `+$17.9281` historical pure-riskless + `+$0.318010` today's live riskless wins = `+$18.2461` cumulative pure-riskless cash net PnL, strictly segregated from shadow!).

---

## Section 2 — Complete 12-Point Repository & Runtime Audit

### 1. Markets Discovered vs. Omitted Across Existing Daemons

| Subsystem / Daemon | Actual Discovery Scope in Code | Live Universe Share Covered | What Is Silently Omitted |
| :--- | :--- | :--- | :--- |
| **`alpha_124_shadow_daemon.py`** ([`discover_all_markets`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/alpha_124_shadow_daemon.py#L2620-L3152)) | Top `600` events by `volume24hr` (`L2643`) + `500` weather tag events (`L2633`) + curated `HIT_SERIES`, `STRIKE_SERIES`, `NBA_SERIES_SLUGS`, `SOC1` (`limit=100`), `TEN1` (`limit=45`), `midterms/politics/geopolitics/oil/ukraine/world` (`limit=45..80`) | **`~5.8%` of `18,940` events** (`~1,100` unique events) and **`<1.2%` of `199,146` active sub-markets** | Long-tail sports leagues, corporate/earnings/AI/tech timelines outside curated slugs, state/municipal/international elections, entertainment/culture, non-top-600 macro/rate brackets, and >`98%` of multi-market slates. |
| **`polymarket_live_harvester.py`** ([`PolymarketLiveHarvester`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L2285)) | Consumes `alpha124` bridge candidates + direct `series_slug` polls (`limit=3` on sub-hourly crypto/metals candles) + UMA `proposed` Carry poll | **`<0.6%` of active markets** directly polled | Relies entirely on `alpha124`'s truncated subset for `D1`, `CAL1`, `COND1`, `NR_M1`, `NR2`, and `C1` candidates; zero independent full-universe sweep. |
| **`polymarket_terminal_recorder.py`** ([`PolymarketDualFeed1HRecorder`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_terminal_recorder.py#L164-L180)) | Strictly `10` hardcoded crypto/metal co-assets (`BTC, ETH, SOL, XAU, XAG, XRP, BNB, DOGE, HYPE, ZEC`) across `5m/15m/1h/4h` candles | **`~40–80` active candle markets (`0.04%` of universe)** | All non-candle markets (`99.96%` of Polymarket). |
| **`cross_venue_riskless_shadow.py`** ([`Stage G Shadow`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_riskless_shadow.py#L67-L88)) | Cross-venue overlap matcher (`Predict.fun`, `SX Bet`, `Limitless`, `Probable`, `Derive`, `ForecastEx`, `STX`) | **`~200–600` cross-venue matched pairs** | Single-venue intra-Polymarket complete sets, NegRisk conversions, logical implications, and cross-event duplicate markets without external venue twins. |

### 2. Hardcoded Limits, Top-N Truncations & Volume/Liquidity Filters

Direct source inspection reveals **14 hardcoded truncation ceilings** that discard valid zero-loss opportunities before mathematical evaluation:
- **`top_vol_events_raw` Cap (`600` events):** `for offset in range(0, 600, 100)` in [`alpha_124_shadow_daemon.py`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/alpha_124_shadow_daemon.py#L2643).
- **`zerofee_general_binaries` Cap (`340` markets + `$500` Volume/Liquidity Floor):** `max_markets=340` (`L3111`) and `if max(liq, vol24) < 500.0: continue` (`L3236`) in [`extract_zerofee_general_binaries`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/alpha_124_shadow_daemon.py#L3196-L3261) — drops thin/newly-listed `0%`-fee binaries where wide retail stale quotes (`ask_YES + ask_NO < $0.98`) most frequently appear!
- **`negrisk_convert_slates` Cap (`40` slates & `<=45` brackets):** `[:40]` truncation (`L2863`) and `len(sp_nrc.brackets) <= 45` (`L2854`) in [`alpha_124_shadow_daemon.py`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/alpha_124_shadow_daemon.py#L2854-L2864), plus `len(sp_nrc.brackets) > 15` skipped on WS (`L2000`).
- **Sibling Market Expansion Caps (`10–16` games):** `missing_em_slugs[:10]` (`L2777`), `nba_base_slugs[:12]` (`L3031`), `nfl_cfb_base_slugs < 12` (`L3038`), `soc_exact_targets[:16]` (`L3045`), and `missing_pairs[:24]` on XTracker (`L3175`).
- **Tag-Specific Single-Page Caps (`limit=25..100` with zero pagination):** `NBA limit=40` (`L2757`), `non_nba limit=25` (`L2799`), `sports limit=40` (`L2800`), `soccer/esports limit=100` (`L2923-L2926`), `tennis limit=45` (`L2956`), `politics/midterms/world limit=60` (`L2957-L2962`).
- **Near-ATM Strike & UMA WS Caps:** Only `ranked_r[:4]` strikes per ladder (`L1980`), `uma_proposed_markets[:85]` (`L2012`), and `_ws_reactive_bin_metas[:110]` (`L2024`) enter the WS subscription set.

### 3. Pagination Gaps & Cursor Defects

- **No Keyset Cursor Usage Anywhere in Existing Repo:** Every Gamma query in `alpha_124_shadow_daemon.py`, `polymarket_live_harvester.py`, and `cross_venue_connectors.py` uses either unpaginated `limit=K` (`K <= 100`) or shallow `offset` loops (`offset <= 500`). Because Gamma enforces an `offset` ceiling (`HTTP 422` at `offset >= 2200..3000`) and clamps `limit > 100` on `/events` to `100`, existing code cannot reach the remaining `~16,800+` active events without `/events/keyset?after_cursor=...`.
- **Fallback REST Book Chunk Truncation:** In [`fetch_books_batch`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/alpha_124_shadow_daemon.py#L2518-L2535), `POST /books` batches by `50` tokens (`L2535`), and on transient batch failure falls back to `chunk[:6]`, silently dropping `44` tokens in that chunk for the cycle.

### 4. Unsupported or Partially Supported Protocol & Market Mechanics

- **Fee-Enabled Binary & Multi-Outcome Markets (`198,018` of `199,138` active markets have `feesEnabled=true`):** `extract_zerofee_general_binaries` (`L3221-L3225`) explicitly rejects `bool(mkt.get("feesEnabled"))` or `mkt_fr > 0`! While `7%` parabolic fees kill `50/50` `C1` boxes, near-tail prices (`p >= 0.96` or `p <= 0.04` on the `0.001` tick grid) collapse parabolic fees `rate * p * (1 - p)` by **`6.5x–25x`** (`<= 11–27 bps`), leaving `198,018` fee-curve markets unscanned for tail-boundary complete sets and split-and-sell overrounds!
- **Split-and-Sell Binary Overrounds (`bid(YES) + bid(NO) - fees > $1.00`):** `enable_pre_split_overround_gun` is `False` below `$140` NAV ([`POLYMARKET_ONCHAIN_MOF_AUDIT.md`](file:///C:/Users/Anton/source/repos/Dominus/POLYMARKET_ONCHAIN_MOF_AUDIT.md#L77)), and general universe-wide `Split-and-Sell` (`Family A(ii)`) is not continuously measured in shadow across all binary markets.
- **Augmented NegRisk Subset `NO` Dominance (`Family C` / `P2.1`):** When `negRiskAugmented=True` (`1,822–1,912` active events), buying all `YES` is unsafe (`Other`/placeholder risk), and calling `convertPositions` requires the full protocol slot count `N_total`. However, holding `m=2` mutually-exclusive `NO` shares directly (without `convertPositions`) pays `>= $1.00` in every named state, `$1.00` (`0.50 + 0.50`) on `50-50` cancellation, and **`$2.00` jackpot if `Other`/outsider wins** — implemented in [riskless_expansion_v6_engines.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/riskless_expansion_v6_engines.py#L125-L303) (`detect_cross_venue_subset_no_boxes`) but **never wired into live/shadow scanning**!
- **Emerging Gamma/CLOB Fields (`Family N`):** Maker-rebate rate curves on sports/crypto fee-enabled tokens, scalar/range settlements, RFQ/combo metadata, and `PositionManager V2` (`0x006F...`) markets lack a systematic field-discovery scanner and research backlog.

### 5. Stale Quote, Midpoint & Top-of-Book Dependencies

- **Gamma `outcomePrices` / `bestBid` / `bestAsk` Pre-Filtering Hazard:** Gamma event payloads cache indicative prices that lag real CLOB books by seconds to minutes. Pre-filtering candidates on Gamma `outcomePrices` misses transient CLOB L2 dislocations and creates phantom signals on already-crossed books.
- **Top-of-Book vs. Multi-Rung Optimal Sizing (`q*`):** Existing `walk_l2_book_asks` in `alpha_124_shadow_daemon.py` (`L3326-L3337`) tests fixed reference tickets (`T1000` / `T100` in `BANKROLL_TICKETS`) and rejects the entire candidate (`if not w_ref.get("filled"): return False`) whenever L1/L2 depth is `$12` instead of `$25`–`$50` — discarding profitable micro-clips (`$5–$12`) that fit `$48.70` live cash! Conversely, evaluating only `L1` top-of-book without marginal rung-by-rung `ΔNetPayoff_min / Δq` overstates executable capacity on multi-leg bundles.
- **Silent Rejection of Near-Arb Structures:** Candidates failing `min_req_edge` (`L3371`) by even `1 bps` or temporarily lacking ask depth are silently dropped (`return False`) and forgotten until the next slow discovery poll, rather than indexed in a `DormantOpportunityStore` triggered on book shifts.

### 6. Unmonitored Mathematical Arbitrage Families Across the Full Universe

Mapping existing DOMINUS v5.1 against the **14 Canonical Opportunity Families (`A..N`)**:
- **Partially Monitored on Truncated Subsets (`<3%` of Universe):** `A` (`C1` buy-merge on `340` zero-fee binaries + daily crypto), `C` (`NR_M1`/`NR2` on `<=40` slates), `D` (`LP1`/`LP2` curated election/BOP slugs), `E` (`CAL1` on `74` ladders), `F` (`D1` on 10 crypto/metal tickers), `G` (`NBA/NFL/SOC1/TEN1/API1` top-volume), `H` (`W_PRUNE1` METAR), `K` (`BOND1`/`BOND2` UMA carry), `L` (`MKR_LOCK1` post-clinch maker).
- **Largely or Completely Unmonitored Across Full Universe:**
  - **`Family A(ii)`:** Universal Binary `Split-and-Sell` (`bid_YES + bid_NO > $1.00 + fees`) across all `199k` markets.
  - **`Family B`:** Exhaustive vs. non-exhaustive proof-gated Multi-Outcome Complete Sets across all `11,317` multi-market events.
  - **`Family D/E/F` (General Categories):** Cross-market logical implications (`A => B`, `A ⊥ B`), deadline containment (`by T1 => by T2`), and strike/FDV/rate monotonicity across **all** corporate, AI, macro, legal, geopolitics, and pop-culture events (not just hardcoded slugs).
  - **`Family I`:** Cross-event Duplicated & Near-Duplicated Market Equivalence Scanner across all `18,940` active events (with strict rule-divergence downgrade to `CLASS_C/D`).
  - **`Family J`:** Portfolio-wide Inventory, Split/Merge & Conversion Capital-Recycling Optimizer (`ΔWealth_min`).
  - **`Family M`:** Global Constrained Portfolio LP/Marginal-Dollar-Hour Allocator across all simultaneous `A..N` candidates.
  - **`Family N`:** Automated New-Mechanism & Schema Anomaly Scanner + ranked `ResearchBacklog`.

### 7. API, CPU, Memory & Serialization Bottlenecks

Cross-referencing [LATENCY_BASELINE.md](file:///C:/Users/Anton/source/repos/Dominus/LATENCY_BASELINE.md) and [PROJECT_STATE.md](file:///C:/Users/Anton/source/repos/Dominus/PROJECT_STATE.md):
- **Uncompressed Gamma Pagination Bandwidth/Heap Spike:** Without `Accept-Encoding: gzip` + immediate field slimming (`_slim_raw_gamma_event`), `190` pages of Gamma `/events/keyset` exceed `~150–250 MiB` of raw JSON text and fragment glibc malloc arenas (`F-01` root cause where `alpha124-shadow` climbed past `1,209 MiB` HWM on a `3,907 MiB` `MemorySwapMax=0B` VM). With `gzip` + streaming slim-on-ingest + bounded top-25 L2 books, full-universe metadata fits comfortably inside `<120–180 MiB` RSS.
- **1-Core / 2-vCPU Contention on `kraken-finland`:** Four long-running Python daemons share 1 physical Xeon core (`loadavg 2.16–3.51`), causing `thread_hop_ms` `p99 = 44.98 ms` and `trigger_to_consume_wall_ms` `p99 = 337.27 ms` if shadow scanners burn unbounded CPU.
- **Exchange Server-Side Taker Speedbump (`~200 ms`):** Live CLOB Maker ACKs average `p50 = 69.82 ms` (`50.4 ms` Finland->Stockholm->London RTT + `~19 ms` matching engine), whereas Taker FOK/FAK ACKs average `p50 = 252.21 ms` due to Polymarket's server-side `~200 ms` Taker delay (`itode=True`). Forward shadow simulation MUST apply realistic post-latency price/depth decay (`70 ms` Maker / `252 ms` Taker) rather than assuming `0 ms` instant fills!

### 8. WebSocket Subscription Sharding & Lifecycle Gaps

- **`alpha_124_shadow_daemon.py` Hard `600`-Token WS Cap:** [`_partition_ws_shards`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/alpha_124_shadow_daemon.py#L2042-L2044) hardcodes `max_shards=3, per_shard=200` (`600` tokens total = `0.15%` of active tokens). Any market outside those `600` tokens falls back to slow periodic REST polling or goes unpriced.
- **`polymarket_live_harvester.py` Position-Only WS Scope:** [`_pos_market_ws`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L10908-L10924) (`4` shards x `485` = `1,940` max tokens) watches primarily already-open positions and clinched watchlists (`recycle_bid_trigger=0.985`), not universe-wide discovery candidates.
- **Lifecycle Gap Between Layer A & Layer B:** Neither daemon implements a **Two-Layer Surveillance Scheduler** where Layer A guarantees bounded-time full-universe rotation (so low-priority markets never vanish permanently) while Layer B dynamically promotes connected components and `DormantOpportunityStore` near-arbs onto high-frequency batched `POST /books` (`50–200` tokens/request) polling.

### 9. Unused or Underutilized Existing Codebase Capabilities

Our audit of `src/polymarket_research/` (`45` Python modules, `5.98 MB` source) identified substantial high-value code already written in the repo that is **unused or disconnected from full-universe scanning**:
1. **[riskless_expansion_v6_engines.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/riskless_expansion_v6_engines.py) (`119.9 KB`, `8` verified pure-riskless engines):** Implements `XV_SUBSET_NO_BOX` (augmented-safe `m=2` subset `NO` boxes with `50-50` cancellation proof!), `TAIL_BOUNDARY_001_ARB` (`0.001`-tick parabolic fee collapse scanner), `BOND3_MULTISOURCE_DEAD_SPLIT`, `HEDGED_PRESPLIT_CONV_GUN`, and `YIELD_STACKED_CARRY_BOX` — **untracked/disconnected from the live/shadow daemon loop**!
2. **[riskless_machine_gun_engine.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/riskless_machine_gun_engine.py) (`154.3 KB`):** Implements `batch_post_fok_orders` (`PostOrdersV2` simultaneous `/orders` up to 15 legs), `evaluate_cross_condition_complement_merge`, `detect_nr3_synthetic_all_yes_overround`, and `PreSplitInventoryGun` — largely gated or restricted to narrow candle subsets.
3. **[same_oracle_dominance_box.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/same_oracle_dominance_box.py) (`45.7 KB`) & [honest_riskless_backtester.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/honest_riskless_backtester.py) (`42.5 KB`):** Standalone state-payoff and causal L2 fee/walk backtesting primitives ready to cross-verify forward shadow simulations.
4. **[economic_attribution_ledger.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/economic_attribution_ledger.py) (`68.1 KB`):** Competitor quote-decay bucket classification (`classify_decay_bucket`) that is underused outside Stage B/G probes.

### 10. Duplicate Work Across the 4 Active Production Daemons

On `kraken-finland`, 4 separate Python processes perform redundant network, TLS, JSON, and orderbook work on 1 physical core:
1. **Triple Gamma `/events` Polling:** `alpha_124_shadow_daemon.py`, `polymarket_live_harvester.py`, `polymarket_terminal_recorder.py` (10 co-asset loops), and `cross_venue_riskless_shadow.py` each open independent TLS pools and re-download overlapping Gamma event metadata instead of reading a shared incremental `FullUniverseRegistry` (`market_registry.sqlite3`).
2. **Duplicate CLOB WS & REST `/book` Polling:** `polymarket-recorder`, `alpha124-shadow`, `live-harvester`, and `cross-venue-shadow` maintain separate CLOB WebSocket connections and separate `_rest_books_cache` dictionaries for overlapping BTC/ETH/SOL/sports tokens.
3. **Duplicate External Spot Polling:** Both `recorder` (WS) and `alpha124-shadow` (`update_crypto_spots` REST `api.binance.com` + `coinbase.com` every cycle at `L2553-L2599`) poll crypto spots concurrently even though `recorder` already publishes `/dev/shm/pm_fast_tick_{ASSET}.json` every `25ms`!

### 11. Accounting, Governance & Safety Strengths vs. Remaining Gaps

- **Core Strengths (Retain 100% Unweakened):**
  - **On-Chain Truth Reconciliation ([`PAAAccountant`](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/accountant.py#L206-L358)):** Reconciles Funder Proxy `0x013A...` `pUSD` (`$0.000000` drift) and ERC-1155 balances every `60s`, engaging `ACCOUNTING_SAFEGUARD_ACTIVE.json` if cash drift `> $1.50` or share drift `> 0.75`.
  - **Zero-Trust Code & Credential Isolation ([`PermissionGate`](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L178-L405)):** Enforces `16` `protected_files`, `build_isolated_worker_env` secret stripping (`PAA_SIGNING_DISABLED=1`), non-overridable anti-self-approval on `data/polymarket/paa/approvals/`, and `proposal_only_live_promotion` below `$5,000` NAV (`D-002`, `D-003`).
  - **Gasless Atomic Primitives (`Relayer V2`):** `mergePositions`, `splitPosition`, `redeemPositions`, and `NegRiskAdapterV2.convertPositions` execute at `$0.00` POL gas via `sig_type=3` EIP-1967 Funder Proxy (`POLYMARKET_ONCHAIN_MOF_AUDIT.md`).
  - **Section 7 Risk Invariants (`v5.0/v5.1`):** `compute_reconciled_concentration_nav_usd()` (`<=15%` reconciled NAV cap per correlated event/weather station `D-007`), `< $500` NAV sequential `>=3`-leg CLOB quarantine (`D-007`), `$30.00` `riskless_hard_ruin_floor_usd` decoupled from `$62.00` directional floor (`POL-13`), and `D-001` non-interference lock on the 4 disputed `KMIA` positions.
- **Remaining Gaps Addressed by RISKLESS FULL THROTTLE:**
  1. **Stale Local Windows Dev Fixture Hazard:** On the local Windows workspace, `data/polymarket/live_harvester_state.json` (`5,232 B`) is an old synthetic fixture (`live_bankroll=$69.048`, `reconciled_nav_usd=$75.0`), whereas `data/polymarket/paa/authoritative_financial_ledger.json` is from `2026-11-03` (`$21.68` cash). Any local dashboard or allocator that naively reads local `live_harvester_state.json` without checking timestamp/origin against reconciled `PROJECT_STATE.md` (`2026-11-11` `$48.70` `pUSD`) will misreport live capital! **Remediation:** `FullThrottlePipeline` anchors live wallet reference metrics strictly to verified `2026-11-11` `kraken-finland` wallet reality (`$48.695132` `pUSD`) and labels all Modes 1 & 2 outputs as `MODE_2_SHADOW` (`realized_live_cash_usd = $0.0000`).
  2. **Lack of Unified 5-Class Proof Taxonomy (`CLASS_A..E`):** Existing shadow sleeves mix true atomic locks (`CLASS_A`), sequential 2-leg CLOB boxes (`CLASS_B`), and post-event/UMA `proposed` carries (`CLASS_C` — exposed to `KMIA`-style UMA disputes!) under a single `"zero_loss"` label. **Remediation:** Enforce strict `CLASS_A..E` proof verification (`universal_arb_verifier`) where `CLASS_B`, `CLASS_C`, and `CLASS_D` are **never** promoted into `CLASS_A`.

### 12. Authoritative Live Cash, NAV & Realized P&L Baseline (Strictly Segregated From Shadow)

Verified directly against `kraken-finland` (`2026-11-11T17:47Z` SSH read-only audit `#10` + [PROJECT_STATE.md](file:///C:/Users/Anton/source/repos/Dominus/PROJECT_STATE.md#L8-L80) + [polymarket_external_cashflows.json](file:///C:/Users/Anton/source/repos/Dominus/config/polymarket_external_cashflows.json)):

| Accounting Metric | Verified Production Value | Basis & Segregation Rule |
| :--- | ---: | :--- |
| **Liquid Wallet Collateral (`live_bankroll` / `pUSD`)** | **`$48.695132` (`$48.70`)** | Funder Proxy `0x013A2474454fBd8738cff6a7f204eF1bc377F4e9` (`$47.377122` baseline + `+$1.000000` EOA `USDC.e -> pUSD` sweep + `+$0.318010` today's live riskless wins; `$0.000000` discrepancy). |
| **True Worst-Case Guaranteed-Floor NAV** | **`$48.695132` (`$48.70`)** | `$48.695132` `pUSD` cash + **`$0.00`** conservative floor on all 4 UMA-disputed `KMIA` positions (`D-009`). |
| **Mark-to-Bid Liquidation NAV** | **`$48.834132` (`$48.83`)** | `$48.695132` `pUSD` cash + `$0.1390` live CLOB best-bid liquidation value across `52.0` disputed `KMIA` shares. |
| **Persisted Harvester Book Equity (`total_account_equity`)** | **`$99.205132` (`$99.21`)** | `$48.695132` cash + `$50.510000` frozen `KMIA` cost basis (**strictly forbidden for sizing or concentration caps**; Harvester uses `reconciled_nav_usd = $48.6951`). |
| **4 Disputed `KMIA` Nov 7 Positions (`6707503` & `6707502`)** | **`$50.51` Cost Basis (`52.0` sh)** | `umaResolutionStatus == "disputed"`, `exit_order_id = None`, `unwind_order_id = None`, `is_liquidating = False` (**100% untouched per `D-001`**). |
| **Verified Pure-Riskless Realized Live Cash PnL** | **`+$18.2461` (`77W / 0L` + Today)** | `77W / 0L` (`100.0%` WR) `+$17.9281` historical pure-riskless ledger + `+$0.318010` today's live riskless wins (`143` total closed records on host). |
| **Retired Legacy Directional / Lattice Realized PnL** | **`-$73.3385` (`30W / 11L`)** | `41` historical trades across `SLEEVE_1_SUBHOURLY_15M`, `SLEEVE_1_CORE_302`, and `SOC2` — **permanently hard-disabled in `RISKLESS_PAA`**. |
| **Fixed Monthly VM Infrastructure Hurdle (`kraken-finland`)** | **`$24.67 / mo` (`$0.8223 / day`)** | `$0.03426 / hr` = **`+7.04 bps/hr` (`+168.9 bps/day`)** portfolio-wide hurdle on `$48.70` liquid `pUSD` (`+0.69 bps/hr` at `$500` NAV). |
| **Forward Shadow Simulated PnL (`MODE_2_SHADOW`)** | **`$0.0000` Realized Cash** | Tracked strictly in isolated shadow ledgers (`data/full_throttle/pipeline/`), **never** added to `live_bankroll` or realized wallet cash! |
