# DOMINUS — Exhaustive Polymarket Universe Coverage Audit & Two-Layer Surveillance Report (`UNIVERSE_COVERAGE_AUDIT.md`)

**Campaign:** DOMINUS — RISKLESS FULL THROTTLE (Agents 2 & 10: Universe Discovery, Coverage Audit & Two-Layer Surveillance)  
**Operating Boundary:** Strictly `MODE 1` (Research) / `MODE 2` (Shadow) public read-only (`https://gamma-api.polymarket.com` & `https://clob.polymarket.com`; `D-001`, `D-002`, `D-003`, `D-010` enforced)  
**Canonical Implementation:** [full_universe_discovery.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/full_universe_discovery.py), [sweep_full_universe_registry.py](file:///C:/Users/Anton/source/repos/Dominus/scripts/sweep_full_universe_registry.py), [test_full_universe_discovery.py](file:///C:/Users/Anton/source/repos/Dominus/tests/test_full_universe_discovery.py)  
**Persisted Registry & Snapshot Artifacts:** `data/universe/market_registry.sqlite3`, `data/universe/coverage_snapshot.json` (`run_id = SWEEP_20261111T191118Z`), `data/universe/surveillance_snapshot.json`

---

## 1. Executive Summary & Headline Empirical Findings

Using [`FullUniverseRegistry.sweep_full_universe`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/full_universe_discovery.py#L2493-L2941) against live public Gamma keyset pagination (`/events/keyset?active=true&closed=false&limit=25&after_cursor=...`, `757` pages to `next_cursor = None`) and CLOB cursor pagination (`/sampling-markets?next_cursor=...`, `11` pages to `LTE=`) with **zero** volume, liquidity, fee-regime, category, or top-$N$ exclusions (`SWEEP_20261111T191118Z`), we measured the exact real-time observable Polymarket universe and audited every discovery path in DOMINUS v5.1:

| Metric | Live Observable Universe (`100.0%`) | DOMINUS v5.1 Discovered | DOMINUS v5.1 Strategy-Evaluated | Blind / Unmonitored Gap |
| :--- | ---: | ---: | ---: | ---: |
| **Active Unclosed Events** | **`18,905`** (`18,902` w/ `>=1` active market) | `4,881` (`25.823%` general)<br>`5,508` (`29.140%` incl. UMA-only) | `<= 4,881` (`<= 25.823%`) | **`13,394`–`14,021` (`70.86%`–`74.18%`)** |
| **All Child Markets in Active Events** | **`374,314`** *(incl. `174,642` closed/resolved siblings)* | — | — | Retained `100%` in SQLite w/ `CLOSED_OR_ARCHIVED` |
| **Active Unclosed Markets** | **`199,672`** | `31,944` (`15.998%` general)<br>`40,181` (`20.124%` incl. UMA-only) | **`29,795` (`14.922%`)** | **`169,877` (`85.078%` BLIND)** |
| **Execution-Eligible Markets** | **`199,393`** (`279` ineligible retained w/ skip codes) | — | **`29,795` (`14.943%`)** | **`169,598` (`85.057%` BLIND)** |
| **Tradable Outcome Token IDs** | **`398,786`** (`399,148` orderbook tokens) | — | **`600` realtime WS cap (`0.150%`)** | **`398,186` (`99.850%` off-WS)** |
| **Zero-Fee General Binaries Evaluated** | **`1,118`** zero-fee active markets (`0.560%` of universe) | — | **`340` (`max_markets=340`)** | `198,554` fee-enabled binaries hard-skipped by `extract_zerofee_general_binaries` |
| **Terminal Recorder Markets** | **`199,672`** | `3,715` (`1.8606%`, `10` co-assets) | `0` (telemetry only) | `98.139%` outside `10` crypto/metal co-assets |
| **Cross-Venue Connector (`PolymarketConnector`)** | **`199,672`** | `220` (`0.110%`) | **`30` L2-hydrated (`0.0150%`)** | `99.985%` unhydrated in default connector |

### Three Root Structural Causes of the `85.078%` v5.1 Blindness Gap
1. **Gamma Offset Pagination Hard Wall (`HTTP 422` above `offset=2100`) & Silent `limit=100` Clamp:**
   - Gamma silently clamps `GET /events?limit=500` and `GET /markets?limit=200` to **`100` records per response**, and `GET /events?active=true&closed=false&limit=100&offset=3000` fails with **`HTTP 422: {"type": "validation error", "error": "offset too large, use /events/keyset for deeper pagination"}`**. Any scanner relying on `/events?offset=...` cannot physically reach past `~2,200` events (`~11.6%` of the `18,905` active events).
   - Worse, [`Alpha124ShadowDaemon.discover_uma_proposed_markets`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/alpha_124_shadow_daemon.py#L13867-L13884) requests `/markets?...&limit=200&offset=0` and `limit=200&offset=200`; because Gamma clamps `limit=200` to `100`, **ranks `100..199` are skipped every single cycle**!
2. **Polymarket's `99.440%` Fee-Enabled Structural Shift (`198,554` vs `1,118` Markets):**
   - Out of `199,672` active unclosed Gamma markets, **`198,554` (`99.440%`)** now have `feesEnabled = true` (`takerBaseFee = 1000`, `feeSchedule = {"exponent": 1, "rate": 0.04, "takerOnly": true, "rebateRate": 0.25}` across `sports_fees_v3`, `politics_fees`, `crypto_fees_v2`, `weather_fees`, `finance_prices_fees`, `culture_fees`, `tech_fees`, and `economics_fees`), leaving only **`1,118` (`0.560%`)** zero-fee markets.
   - [`extract_zerofee_general_binaries`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/alpha_124_shadow_daemon.py#L3196-L3261) hard-skips `if m.get("feesEnabled") is True: continue` (`L3221`), requires `max(liq, vol24) >= $500` (`L3236`), and truncates at `max_markets = 340` (`L3199`) — discarding virtually the entire non-series binary universe before fee-adjusted L2 complete-set / maker-rebate math can even inspect it.
3. **`600`-Token WebSocket Ceiling (`0.150%`) & `50`-Token `/books` Batch Fragmentation (`9x–10x` Excess Round-Trips):**
   - [`_partition_ws_shards`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/alpha_124_shadow_daemon.py#L2335-L2343) hard-caps CLOB WebSocket subscriptions at `max_shards=3` $\times$ `max_tokens_per_shard=200` = **`600` tokens** (`0.150%` of `399,148` orderbook tokens), while [`fetch_books_batch`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/alpha_124_shadow_daemon.py#L2535-L2540) chunks `POST /books` into `50`-token slices despite CLOB supporting **`500` tokens per `POST /books` (`HTTP 200`)** (`550` returns `HTTP 400`).

---

## 2. Phase I Forensic Audit of Existing DOMINUS v5.1 Discovery & Polling

Read-only inspection across all five production/shadow discovery and connector modules identified **23 concrete discovery caps, exclusions, pagination defects, and duplicate polling paths**:

### 2.1 [`alpha_124_shadow_daemon.py`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/alpha_124_shadow_daemon.py) (Primary Shadow & Live Candidate Bridge)
| Symbol & Line Range | Hardcoded Cap / Filter / Defect | Empirical Impact |
| :--- | :--- | :--- |
| [`discover_all_markets`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/alpha_124_shadow_daemon.py#L2643-L2645) | `for off in range(0, 600, 100)` on `/events?active=true&closed=false&limit=100&order=volume24hr` | Fetches only the top **`600`** events by 24h volume (`3.17%` of `18,905` active events); quiet/mispriced tail events with stale quotes (`volume24hr == 0`) are never discovered unless matched by a hardcoded tag/slug. |
| [`discover_all_markets` (Tag Slices)](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/alpha_124_shadow_daemon.py#L2633-L2965) | `weather` `offset in (0..400)` (`<=500`, `L2633`), `sports` `limit=40` (`L2800`), `soccer` `tag_id=100350&limit=100` (`L2923`), `esports` `tag_id=64&limit=100` (`L2925`), `tennis` `limit=45` (`L2956`), `midterms` `60`, `politics` `60`, `geopolitics` `80`, `oil` `50`, `ukraine` `45`, `world` `60` (`L2957-2962`) | Sports alone has **`11,316` active events (`171,090` active markets)**, Politics has **`1,799` events (`10,824` markets)**, and Crypto has **`3,990` events (`6,036` markets)**. Fixed `40–100` tag limits miss `>80%` of sports, politics, macro, tech/AI (`259` events), and culture (`285` events). |
| [`HIT_SERIES` .. `HOURLY_BINANCE_SERIES`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/alpha_124_shadow_daemon.py#L72-L260) | Hardcoded series slug tuples (`HIT_SERIES` `limit=5`, `STRIKE_SERIES` `limit=5`, `NEGRISK_SERIES` `limit=4`, `NBA_SERIES_SLUGS` `limit=40`, `MULTI_SPORT_CORRIDOR_SERIES` `limit=25`, `HOURLY_BINANCE_SERIES` `limit=6`) | Any newly launched Polymarket series slug, commodity barrier, election primary, or non-US league outside hardcoded tuples is invisible. |
| [`extract_zerofee_general_binaries`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/alpha_124_shadow_daemon.py#L3196-L3261) | `max_markets: int = 340` (`L3199`), `if m.get("feesEnabled") is True: continue` (`L3221`), `if max(liq, vol24) < 500.0: continue` (`L3236`), `rem_days < (2.0 / 1440.0)` (`L3239`) | Excludes **`198,554` (`99.440%`)** fee-enabled active markets outright, drops low-volume resting-depth arbs (`< $500` 24h vol/liq), and caps output to `340` binaries. |
| [`negrisk_convert_slates` & WS Reactive NegRisk](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/alpha_124_shadow_daemon.py#L2854-L2998) | `2 <= len(brackets) <= 45` (`L2864`, `L2992`), `ranked_nrc[:40]` (`L2885`), and `len(brackets) > 15` skipped in [`_scan_ws_reactive_negrisk_arbs`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/alpha_124_shadow_daemon.py#L2000-L2202) | Polymarket currently has **`6,217` active NegRisk events** (`3,350` closed-slate standard + `2,867` augmented/Other/placeholder). Capping general slates at `40` (`~128` w/ tags) and WS reactive scan at `<= 15` brackets misses `>95%` of multi-outcome NegRisk events and large Golf/PGA/Soccer/Election slates (`46–150+` outcomes). |
| [`discover_uma_proposed_markets`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/alpha_124_shadow_daemon.py#L13867-L13978) | Requests `/markets?...&limit=200&offset=0` and `limit=200&offset=200` (`L13867-13870`), `/events` `range(0, 1500, 100)` (`L13874`), and `uncached_batch[:32]` RPC checks (`L13978`) | Gamma clamps `limit=200` to `100`, creating a permanent **blind hole at ranks `100..199`** on `/markets`, and misses `201` of the **`702` live `umaResolutionStatus == "proposed"` active markets** (`501/702` reached). |
| [`_refresh_ws_subscriptions` & `_partition_ws_shards`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/alpha_124_shadow_daemon.py#L2012-L2343) | `uma_proposed_markets[:85]` (`L2012`), `zerofee_general_binaries[:110]` (`L2024`), `max_shards=3, max_tokens_per_shard=200` -> **`600` token cap** (`L2042`, `L2335`), `120s` refresh interval | Subscribes to at most `600 / 399,148` = **`0.150%`** of orderbook outcome tokens; no round-robin sweep layer exists for the remaining `99.850%`. |
| [`fetch_books_batch`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/alpha_124_shadow_daemon.py#L2535-L2540) | `chunk_size: int = 50` on `POST /books` | Sends `9x–10x` more HTTP POST requests than necessary (`CLOB_BOOKS_MAX_BATCH_SIZE = 500`, default `450`). |

### 2.2 [`polymarket_live_harvester.py`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py) (Live Execution Engine)
- **Zero Independent Universe Discovery:** [`_prewarm_upcoming_markets`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L2270-L2350) only polls `11` hardcoded short-horizon crypto series (`btc/eth/sol/xrp` `5m/15m/1h`, `limit=3`, `secs_left <= 7200`).
- **100% Downstream Coupling to `alpha124` Blind Spots:** [`_ingest_stage_c_live_box_candidates`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L7975-L8042) tails `data/polymarket/d1_live_box_candidates.jsonl` written by `alpha_124_shadow_daemon.py`, inheriting every pagination cap and exclusion above.

### 2.3 [`polymarket_terminal_recorder.py`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_terminal_recorder.py) (Dual-Feed Recorder)
- **Hardcoded `10`-Asset Scope (`1.8606%` of Active Markets):** [`ASSET_CONFIGS`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_terminal_recorder.py#L343-L435) and `--co-assets` (`L3703`) cover only `BTC, ETH, SOL, XAU, XAG, XRP, BNB, DOGE, HYPE, ZEC` (`limit=10`/`limit=20`, `secs_left <= 7200`, `L1598-1835` — `3,715` markets out of `199,672`).
- **Duplicate Cross-Daemon Polling:** Independently re-polls the exact same Gamma crypto candle slugs and Binance spot tickers already polled by `alpha_124_shadow_daemon.py` and `polymarket_live_harvester.py` on the `3,907 MiB` swapless host.

### 2.4 [`riskless_protocol_v2_expansion.py`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/riskless_protocol_v2_expansion.py) & [`cross_venue_connectors.py`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_connectors.py)
- [`scan_full_universe_c1_and_ctf_overround`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/riskless_protocol_v2_expansion.py#L5435-L5488) skips `negRisk` sub-markets on binary C1 and blocks `fee_rate > 0` from `CTF_OVERROUND_MINT_SELL` rather than computing exact net-of-fee mint-and-sell proceeds; [`augment_uma_proposed_from_universe_and_polygon`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/riskless_protocol_v2_expansion.py#L11472) caps `need_mids[:120]`.
- [`PolymarketConnector.__init__`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_connectors.py#L2898-L2916) defaults to `max_pages = 2`, `page_limit = 60` (`120` general markets + `100` sports markets = `0.110%` of universe) and **`max_hydrated_markets = 30`** (`L3091` = **`0.0150%`** of active markets hydrated on L2!), using `50`-token `/books` chunks (`L3118`) and `[:16]` `/fee-rate` lookups (`L3136`).

---

## 3. Exact Real-Time Observable Polymarket Universe Census (`SWEEP_20261111T191118Z`)

Measured via [`scripts/sweep_full_universe_registry.py`](file:///C:/Users/Anton/source/repos/Dominus/scripts/sweep_full_universe_registry.py) (`757` Gamma `/events/keyset` pages at `limit=25` + `11` CLOB `/sampling-markets` pages + boundary probes; persisted in `data/universe/coverage_snapshot.json`):

### 3.1 Event, Market & Token Totals
- **Total Active Unclosed Events (`/events/keyset?active=true&closed=false`):** **`18,905`** (+ `1` standalone active CLOB market reconciled = `18,906` events seen this sweep)
  - **Single-Market Binary Events:** **`7,584`** (`6,396` pure `SINGLE_BINARY` + `1,179` `SINGLE_ACTIVE_BINARY_IN_SERIES` where earlier series siblings resolved + `9` zero-active-child shells)
  - **Multi-Market Events (`>= 2` active child markets):** **`11,321`** (`59.88%` of all active events)
    - `MULTI_MARKET_INDEPENDENT_OR_LADDER`: **`5,113`** events (includes **`355`** strike/threshold ladder events and **`728`** temporal deadline `"by <Date>"` ladder events)
    - `MULTI_OUTCOME_NEGRISK` (Standard Closed Complete-Set Slates): **`3,350`** events
    - `MULTI_OUTCOME_AUGMENTED_NEGRISK` (Augmented / `"Other"` / Unnamed Placeholder Slates): **`2,867`** events (`2,814` events carry an explicit `"Other"` / `negRiskOther` catch-all market)
- **All Child Markets Attached to Active Events:** **`374,314`**
  - **Closed / Archived / Inactive Sibling Markets inside Active Events:** **`174,642`** (`100%` retained in `market_registry.sqlite3` with `CLOSED_OR_ARCHIVED` / `INACTIVE_OR_PAUSED` so historical slate completeness & partial settlements are never lost)
  - **Active Unclosed Markets:** **`199,672`**
    - **Execution-Eligible Active Markets:** **`199,393`** (`99.860%` of active markets)
    - **Ineligible Active Markets Retained with Hard-Block Skip Codes:** **`279`** (`0.140%`)
- **Outcome Token IDs:** **`748,520`** instruments seen this sweep (`399,256` tokens in active markets; **`398,786` tradable outcome token IDs**)
- **CLOB `/sampling-markets` Active Universe (`11` cursor pages to `LTE=`):** **`10,796`** active sampling markets (`10,237` at `1000 bps` `taker_base_fee`, `559` at `0 bps`; `1` standalone active CLOB market absent from Gamma active events reconciled automatically).

### 3.2 Protocol, Fee-Regime & Microstructure Breakdown (Active Unclosed Markets = `199,672`)
| Dimension | Sub-Classification | Active Market Count | Share of Active Universe |
| :--- | :--- | ---: | ---: |
| **Order Book Status** | `enableOrderBook == True` | `199,618` | `99.973%` |
| | `enableOrderBook == False` (`ORDERBOOK_DISABLED`) | `54` | `0.027%` |
| **Order Acceptance** | `acceptingOrders == True` | `199,665` | `99.996%` |
| | `acceptingOrders == False` (`NOT_ACCEPTING_ORDERS`) | `7` | `0.004%` |
| **Fee Regime** | `feesEnabled == True` (`feeRateBps == 1000` curve) | `198,554` | **`99.440%`** |
| | `feesEnabled == False` (`feeRateBps == 0`, Zero-Fee) | `1,118` | **`0.560%`** |
| **Fee Schedule Types** | `sports_fees_v3` (`164,997`), `politics_fees` (`9,646`), `crypto_fees_v2` (`6,067`), `sports_fees_nfl_cfb_oct26` (`3,959`), `culture_fees` (`3,397`), `weather_fees` (`2,998`), `finance_prices_fees` (`2,483`), `tech_fees` (`1,925`), `sports_fees_v2` (`1,886`), `economics_fees` (`939`), `general_fees` (`116`), `mentions_fees` (`114`), `crypto_15_min` (`1`) | `198,554` | `99.440%` |
| **NegRisk Protocol** | Active `negRisk == True` child markets | `74,463` | `37.293%` |
| | Augmented Placeholder markets (`Person A`, `Option X`, etc., all child markets) | `20,933` | Retained w/ `AUGMENTED_PLACEHOLDER_OUTCOME` |
| | Augmented `"Other"` / `negRiskOther` markets | `2,814` | Retained w/ `AUGMENTED_OTHER_MUTABLE_OUTCOME` |
| **RFQ & Rewards** | `rfqEnabled == True` | `380` | `0.190%` |
| | `holdingRewardsEnabled == True` | `347` | `0.174%` |
| **UMA Resolution State** | `none` (normal live trading) | `198,845` | `99.586%` |
| | `proposed` (`UMA_PROPOSED_SETTLEMENT_STAGE`) | `702` | `0.352%` |
| | `disputed` (`UMA_DISPUTED_FROZEN`, incl. `2` `KMIA` `D-001` locks) | `123` | `0.062%` |
| | `resolved` (awaiting Gamma close sweep) | `2` | `0.001%` |

### 3.3 Domain Category & Tag Distribution
| Primary Category | Active Events | Active Unclosed Markets | Share of Active Markets |
| :--- | ---: | ---: | ---: |
| `sports` | `11,316` | `171,090` | `85.686%` |
| `politics` | `1,799` | `10,824` | `5.421%` |
| `crypto` | `3,990` | `6,036` | `3.023%` |
| `macro_finance` | `677` | `3,259` | `1.632%` |
| `weather` | `320` | `3,029` | `1.517%` |
| `culture_media` | `285` | `2,219` | `1.111%` |
| `tech_ai` | `259` | `2,066` | `1.035%` |
| `geopolitics` | `198` | `833` | `0.417%` |
| Long-tail macro/regional (`parcl`, `economy`, `jobs`, `ecb`, `canada`, `brazil`, `snb`, `boe`, `pce`, `rbi`, `ppi`, `ism`, etc.) | `61` | `316` | `0.158%` |
| **Total** | **`18,905`** | **`199,672`** | **`100.000%`** |

---

## 4. Separation of Discovery Completeness (`100%`) vs. Execution Eligibility (`SkipReason`)

[`FullUniverseRegistry`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/full_universe_discovery.py#L1780-L3363) never silently drops an event, market, or token at discovery time (`discovery_complete == True` on 100% of retained markets). Instead, every market and instrument carries machine-readable [`SkipReason`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/full_universe_discovery.py#L94-L128) codes separating **Hard Execution Blockers** (`execution_eligible == False`) from **Caution / Microstructure State Flags**:

| `SkipReason` Code | Gate Type | Empirical Count (Across `374,315` Seen Markets) | Meaning & Safety Role |
| :--- | :--- | ---: | :--- |
| `NOT_ACCEPTING_ORDERS` | Hard Block | `166,840` (`7` on active unclosed) | CLOB `acceptingOrders == False` |
| `CLOSED_OR_ARCHIVED` | Hard Block | `148,994` | Resolved/closed sibling or archived market |
| `INACTIVE_OR_PAUSED` | Hard Block | `25,881` | Inactive, paused, or `deploying`/`pendingDeployment` |
| `AUGMENTED_PLACEHOLDER_OUTCOME` | Hard Block | `20,933` (`96` on active unclosed) | Unnamed augmented NegRisk slot (`Person A`, `Option X`, `Placeholder`) — blocks invalid complete-set sums |
| `UMA_DISPUTED_FROZEN` | Hard Block | `127` (`123` on active unclosed) | Active UMA dispute (`umaResolutionStatus == "disputed"`) |
| `ORDERBOOK_DISABLED` | Hard Block | `54` | `enableOrderBook == False` |
| `MISSING_TOKEN_IDS` | Hard Block | `54` | Empty or `<2` `clobTokenIds` |
| `MISSING_CONDITION_ID` | Hard Block | `54` | Missing or non-66-char hex `conditionId` |
| `KMIA_D001_PROTECTED_LOCK` | **Non-Overridable `D-001` Lock** | **`2`** (`6707502`, `6707503`) | Frozen Nov 7 Miami `KMIA` disputed markets — retained in discovery, strictly locked out of any execution/unwind/merge |
| `PAST_END_DATE_UNRESOLVED` | Caution Flag | `32,866` | Past nominal `endDate` awaiting oracle/UMA finalization |
| `AUGMENTED_OTHER_MUTABLE_OUTCOME` | Caution Flag | `2,814` | Mutable catch-all `"Other"` (`negRiskOther`) — prevents naive closed-slate NO conversion (`Class E` hazard) |
| `UMA_PROPOSED_SETTLEMENT_STAGE` | Caution Flag | `708` (`702` active) | In UMA optimistic liveness window (routed exclusively to settlement/bond verifiers with challenge-risk gates) |
| `ZERO_RESTING_DEPTH` / `ONE_SIDED_BOOK` | Dynamic Book Flag | Refined per `/books` cycle (`1,245` empty, `6,355` two-sided observed across cumulative polls) | Updated live by [`update_books_from_snapshots`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/full_universe_discovery.py#L3231-L3348) and automatically cleared as soon as two-sided depth returns |

---

## 5. Phase II Architecture: SQLite Registry & Two-Layer Surveillance Benchmarks

### 5.1 Swapless-Safe Memory Footprint (`114.03 MiB < 120 MiB` Target, `D-010`)
- [`FullUniverseRegistry`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/full_universe_discovery.py#L1780-L2491) streams `/events/keyset` at `limit=25` events/page, pops and frees raw JSON event dicts immediately upon normalization, uses bounded `heapq` top-$K$ structures (`< 4 MiB` RAM) in [`ExistingDominusV51CoverageTracker`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/full_universe_discovery.py#L1435-L1740), and persists into SQLite (`WAL` mode, `PRAGMA cache_size=-3000` = `<= 3 MiB` SQLite page cache, `PRAGMA mmap_size=0`, `PRAGMA temp_store=FILE`, `@dataclass(slots=True)` models, periodic `gc.collect()` + Linux `libc.malloc_trim(0)`).
- **Verified Live Peak Process RSS:** **`114.03 MiB`** (`< 120.00 MiB` envelope) across all `757` Gamma pages + `11` CLOB pages + `2` batched `POST /books` surveillance cycles (`104.57 MiB`–`106.30 MiB` during surveillance).
- **Verified Live Incremental Diff Accounting (`SWEEP_20261111T191118Z`):**
  - `unchanged_events = 18,798`, `added_events = 31`, `updated_events = 77`
  - `unchanged_markets = 373,950`, `added_markets = 206`, `updated_markets = 159`, `newly_closed_or_missing_markets = 71` (transitioned cleanly to `CLOSED_OR_ARCHIVED` via [`_mark_disappeared_markets_closed`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/full_universe_discovery.py#L2325-L2363)).

### 5.2 [`TwoLayerSurveillanceScheduler`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/full_universe_discovery.py#L3472-L3768) Empirical Performance
- **Layer B (High-Priority Adaptive Polling, default `1,800` tokens/cycle):** Prioritizes pinned dormant/near-arb watch tokens (`register_priority_tokens`), zero-fee markets (`1,118` markets = `~2,236` tokens), `umaResolutionStatus == "proposed"` markets (`702` markets), near-expiry (`<= 24h`) ladders, and high-turnover slates.
- **Layer A (Exhaustive Non-Starvation Round-Robin Sweep, default `1,350` tokens/cycle):** Advances a durable cursor (`surveillance_state.layer_a_cursor`) across all `398,786` tradable tokens in lexicographic `token_id` order and wraps around automatically (`296` cycles per `100%` full-universe book pass — zero permanent blind spots).
- **Batched `POST /books` Keep-Alive Throughput (`clob_batch_size = 450`, max `500`):**
  - Cycle 1 polled **`3,150` tokens in `7` HTTP POST batches in `2.93s`** (`2,400` two-sided books, `546` one-sided, `204` empty; `rss = 104.57 MiB`).
  - Cycle 2 polled **`3,150` tokens in `7` HTTP POST batches in `2.62s`** (`1,105` two-sided, `1,809` one-sided, `236` empty; `rss = 106.30 MiB`; **`6,295` fresh hot tokens refreshed in `5.55s`**, `~1,134` live L2 books/second over a single keep-alive TLS socket).

---

## 6. Verification & Reproducibility Commands

Run locally on Windows (`D-010` — never run test suites or heavy sweeps on `kraken-finland`):

```powershell
# 1. Unit & integration test suite (6 tests: normalization, skip codes, SQLite diffs, keyset sweep, 2-layer surveillance, rate budget)
& "C:\Program Files\LibreOffice\program\python.exe" -m unittest tests/test_full_universe_discovery.py -v

# 2. Full live 100% observable Polymarket sweep + 2 batched Layer B/A /books surveillance cycles
& "C:\Program Files\LibreOffice\program\python.exe" -u scripts/sweep_full_universe_registry.py
```
