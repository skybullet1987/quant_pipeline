# DOMINUS — RISKLESS FULL THROTTLE: Live Universe, Shadow & Economic Dashboard

- **Generated At (UTC):** `2026-11-13T14:52:05Z`
- **Active Operating Mode:** `MODE_2_SHADOW` (`Jurisdiction Gate = CA-ON`, `MODE_3_LIVE Hard-Locked = True`, `0` private keys read, `0` live orders placed)
- **Campaign Execution Telemetry:** `17` cycles (`FAST_CYCLE, DISCOVERY_CYCLE, FAST_CYCLE, DISCOVERY_CYCLE, FAST_CYCLE, DISCOVERY_CYCLE, FAST_CYCLE, DISCOVERY_CYCLE, FAST_CYCLE, DISCOVERY_CYCLE, FAST_CYCLE, DISCOVERY_CYCLE, FAST_CYCLE, DISCOVERY_CYCLE, FAST_CYCLE, DISCOVERY_CYCLE, FAST_CYCLE`), Campaign Wall Time `288.85s`, Full-Universe Gamma `/events/keyset` Sweep `201.75s`, Avg `FAST_CYCLE` `28.12s`, In-Memory Listing-to-Eval Latency `30061.9 ms`
- **Swapless Host Safety (`D-010`):** Peak RSS **`171.75 MiB`** (`<= 180.0 MiB` budget OK: `True`)
- **Integrated Peer Tracks:** `discovery=True`, `math_verifier=True`, `proposition_graph=True`, `complete_negrisk=True`, `logical_specialized=True`, `micro_portfolio=True`

## 1. Universe, Order-Book & Relationship Graph Coverage (`Section 12.1`)

| Coverage Dimension | Live Empirical Value | Notes / Protocol Detail |
| :--- | ---: | :--- |
| **Total Observable Active Events** | **`19,256`** | Untruncated Gamma `/events/keyset?active=true&closed=false&after_cursor=...` |
| **Total Child Markets in Active Events / Active Unclosed** | **`365,242` / `200,164`** | 100% retained in discovery census (`CLOSED_OR_ARCHIVED` sibling slots accounted explicitly) |
| **Order-Book Enabled Markets (`enableOrderBook=true`)** | **`200,110`** | `54` markets skipped with explicit `ORDERBOOK_DISABLED` code |
| **Tradable CLOB Outcome Token IDs** | **`400,132`** | Distinct ERC-1155 CTF `YES` / `NO` token IDs |
| **Standard `negRisk` vs `negRiskAugmented` Events** | **`6,360` / `1,876`** | Augmented placeholder/`Other` slates strictly guarded against false partition proofs |
| **Fee-Curve Enabled Markets (`feesEnabled=true`)** | **`199,043`** | Priced via exact Protocol V2 `p*(1-p)` share-haircut schedule (`feeSchedule.{rate,exponent}`) |
| **Proposition Graph Edges (`Total` / `Cross-Market`)** | **`5,761` / `3,212`** | `OFFICIAL_CONTRACTUAL=3,026`, `VERIFIED_MATHEMATICAL=324`, `SUSPECTED=2,385`, `STATISTICAL=26` |
| **Verified Multi-Market Connected Components** | **`91`** | Pruned `O(m log m)` components preventing blind `O(N^2)` combinatorial scans |
| **Fresh L2 Order-Book Markets / Tokens (Latest Cycle)** | **`544` / `1,086`** | Total batched `/books` token polls across campaign: `23,270` |
| **Portfolio Holdings (`Recyclable` / `D-001 Frozen KMIA`)** | **`0` / `4`** | 4 disputed Nov 7 `KMIA` positions (`6707503`, `6707502`, `$50.51`) 100% quarantined |

### Explicit Machine-Readable Eligibility & Skip Accounting

| Skip / Quarantine Code | Market Count | Handling Rule |
| :--- | ---: | :--- |
| `COLD_LAYER_AWAITING_ROTATION` | `199,566` | Retained in discovery registry; excluded from `CLASS_A/B` live promotion |
| `CLOSED_OR_ARCHIVED` | `165,078` | Retained in discovery registry; excluded from `CLASS_A/B` live promotion |
| `AUGMENTED_PLACEHOLDER_OUTCOME` | `2,037` | Retained in discovery registry; excluded from `CLASS_A/B` live promotion |
| `UMA_DISPUTED_QUARANTINED` | `122` | Retained in discovery registry; excluded from `CLASS_A/B` live promotion |
| `ORDERBOOK_DISABLED` | `54` | Retained in discovery registry; excluded from `CLASS_A/B` live promotion |
| `MISSING_TOKEN_IDS` | `44` | Retained in discovery registry; excluded from `CLASS_A/B` live promotion |
| `ZERO_RESTING_DEPTH` | `8` | Retained in discovery registry; excluded from `CLASS_A/B` live promotion |

## 2. Opportunity Families `A..N` Coverage & 5-Tier Proof Breakdown (`Section 12.2`)

- **Total Candidates Structured & Verified (Latest Cycle):** `1,088` (`Mathematically Proven CLASS A + B = 3`, `CLASS_A = 0`, `CLASS_B = 3`, `CLASS_C = 13`, `CLASS_D Rule-Rejected = 197`, `CLASS_E No-Arb/Shallow = 875`)
- **Rule-Mismatch Traps Prevented (`90m vs OT`, `Timezone`, `Touch vs Close`, `Converse`):** **`1,511`**
- **`D-007` `< $500` NAV Sequential `>= 3`-Leg Quarantined Bundles:** **`28`**

| Family | Opportunity Family Description | Structures / Markets Inspected | Emitted | `CLASS_A` | `CLASS_B` | `CLASS_C` | `CLASS_D` | `CLASS_E` | Dormant Near-Miss |
| :---: | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **`A`** | Binary YES/NO Complete-Set Arbitrage (Buy-Merge & Split-Sell) | `691` | `266` | `0` | `0` | `0` | `0` | `266` | `266` |
| **`B`** | Multi-Outcome Exhaustive Set Arbitrage | `42` | `7` | `0` | `1` | `0` | `6` | `0` | `0` |
| **`C`** | Negative-Risk Adapter Conversion & Slate Arbitrage | `29` | `24` | `0` | `1` | `0` | `20` | `3` | `2` |
| **`D`** | Cross-Market Logical Implication & Subset Arbitrage | `107` | `6` | `0` | `0` | `1` | `0` | `5` | `0` |
| **`E`** | Temporal & Deadline Monotonicity Arbitrage | `17` | `15` | `0` | `0` | `5` | `8` | `2` | `0` |
| **`F`** | Price-Threshold & Strike-Ladder Dominance Arbitrage | `300` | `300` | `0` | `0` | `4` | `67` | `229` | `1` |
| **`G`** | Sports Outcome Structure & Advancement Arbitrage | `244` | `244` | `0` | `0` | `0` | `49` | `195` | `0` |
| **`H`** | Weather & Measurable-Event Bracket Arbitrage | `0` | `0` | `0` | `0` | `0` | `0` | `0` | `0` |
| **`I`** | Duplicated & Near-Duplicated Cross-Event Market Arbitrage | `217` | `217` | `0` | `0` | `0` | `47` | `170` | `0` |
| **`J`** | Portfolio Inventory Completion & Split/Merge Recycling | `4` | `0` | `0` | `0` | `0` | `0` | `0` | `0` |
| **`K`** | Near-Resolution & UMA Optimistic Oracle Carry | `544` | `7` | `0` | `0` | `3` | `0` | `4` | `4` |
| **`L`** | Maker/Taker Fee Asymmetry & Passive Box Completion | `544` | `0` | `0` | `0` | `0` | `0` | `0` | `0` |
| **`M`** | Multi-Leg Constrained Component & Portfolio Arbitrage | `220` | `2` | `0` | `1` | `0` | `0` | `1` | `1` |
| **`N`** | Newly Discovered Structures & Protocol Edge Scanner | `1,612` | `0` | `0` | `0` | `0` | `0` | `0` | `0` |

## 3. Multi-Cycle Persistence, Forward `t -> t+1` Validation & Dormant Store

- **Persistence Across Cycles:** `444` unique candidates tracked, `3` unique proven `CLASS_A/B` arbs, `3` persisted `>= 2` cycles (avg observed lifetime `44.25s`).
- **Non-Hindsight Forward Snapshot Validation (`Cycle t -> Cycle t+1`):** `3` tickets re-evaluated on next live `/books` poll, `3` survived (`100.0%`), post-delay validated net PnL **`$0.3740`**.
- **`DormantOpportunityStore` (`dormant_opportunities.json`):** **`1200`** active near-miss / shallow-depth structures retained (`<= 50 bps`: `1200`, `<= 150 bps`: `1200`, book-shift rescans triggered: `3404`, promoted to executable: `2`).
- **`HedgedMakerShadowQuoter` (`Family L` `0 bps` `postOnly` + `15%–25%` Rebate Shadow, Strictly Segregated from Locked Cash):** `3` active resting quotes (`2151` posted, `1458` hedged fills, `9` adverse-jump unwinds, ex-rebate net shadow PnL `$523.4913`, est. maker rebate `$10.9151`).
- **`HarvesterCandidateBridge` (`d1_live_box_candidates.jsonl` Single-Authority Bridge + JIT `/books` Re-Verify):** `Enabled=True`, `EmittedThisCycle=0` (`TakerBoxes=0`, `MakerLocks=0`), `JITReverified=0`, `JITDecayedBlocked=0`, `CampaignTotalEmitted=0`, `DedupeSuppressed=0`.

### Top Monitored Dormant Near-Arbitrage Structures (Awaiting Book Shift)

| Candidate ID | Fam | Summary | Gap to Breakeven | Reason | Obs / Shift Rescans |
| :--- | :---: | :--- | ---: | :--- | ---: |
| `FAM_C_SYNTH_NO_548858_2412745` | `C` | Anthropic IPO Closing Market Cap | `0.0 bps` | `ZERO_OR_SHALLOW_L2_DEPTH` | `2 / 15` |
| `FAM_C_SYNTH_NO_74788_668333` | `C` | Guinea-Bissau Presidential Election | `0.0 bps` | `ZERO_OR_SHALLOW_L2_DEPTH` | `262 / 2` |
| `FT_D_MUTUAL_EXCLUSION_6fddfb5c7e89` | `D` | [D] Will Hayden Johnson win by KO or TKO? <-> Wi | `0.0 bps` | `ZERO_OR_SHALLOW_L2_DEPTH` | `16 / 0` |
| `FT_E_TEMPORAL_DEADLINE_IMPLICATION` | `E` | [E] Jensen Huang announced resignation or remo < | `0.0 bps` | `ZERO_OR_SHALLOW_L2_DEPTH` | `16 / 0` |
| `FT_E_TEMPORAL_DEADLINE_IMPLICATION` | `E` | [E] Will Michael Carrick be out as Manchester  < | `0.0 bps` | `ZERO_OR_SHALLOW_L2_DEPTH` | `2 / 14` |
| `FT_E_TEMPORAL_DEADLINE_IMPLICATION` | `E` | [E] Next Astra Model (6.1+) released by Novemb < | `0.0 bps` | `ZERO_OR_SHALLOW_L2_DEPTH` | `2 / 14` |
| `FT_E_TEMPORAL_DEADLINE_IMPLICATION` | `E` | [E] Will Michael Carrick be out as Manchester  < | `0.0 bps` | `ZERO_OR_SHALLOW_L2_DEPTH` | `2 / 14` |
| `FT_E_TEMPORAL_DEADLINE_IMPLICATION` | `E` | [E] Will Michael Carrick be out as Manchester  < | `0.0 bps` | `ZERO_OR_SHALLOW_L2_DEPTH` | `2 / 14` |
| `FT_E_TEMPORAL_DEADLINE_IMPLICATION` | `E` | [E] Jensen Huang announced resignation or remo < | `0.0 bps` | `ZERO_OR_SHALLOW_L2_DEPTH` | `2 / 21` |
| `FT_E_TEMPORAL_DEADLINE_IMPLICATION` | `E` | [E] Jensen Huang announced resignation or remo < | `0.0 bps` | `ZERO_OR_SHALLOW_L2_DEPTH` | `16 / 0` |

## 4. Strictly Segregated Economic Accounting & `$24.67/mo` VM Hurdle (`Section 12.3 & 19`)

> **Non-Conflation Invariant:** Simulated paper top-of-book numbers and forward shadow estimates are **strictly segregated** from realized on-chain `pUSD` wallet cash on `kraken-finland`.

| Metric | Column 1: Paper Theoretical (Unallocated L1) | Column 2: Realistic Forward Shadow (Depth-Walked, Post-Fee, Post-Latency) | Column 3: Verified Live Wallet Reality (`kraken-finland`) |
| :--- | ---: | ---: | ---: |
| **Liquid `pUSD` Wallet Cash** | `N/A (Paper)` | `$48.70` (Shadow Ref Budget) | **`$48.695132` (`$48.70`)** |
| **True Worst-Case Floor / Mark-to-Bid NAV** | `N/A` | `$48.70` | **`$48.70` / `$48.83`** |
| **Book Equity (incl. Frozen Disputed `KMIA`)** | `N/A` | `Forbidden for sizing (D-007)` | **`$99.21` (`$50.51` frozen `KMIA`)** |
| **Proven `CLASS A + B` Value (Unallocated Sum)** | `$0.4406` | `$0.3740` L2 / `$0.0000` Post-Latency | `N/A` |
| **Constrained Portfolio Net Value (`$48.70` Cap)** | `Unconstrained` | **`$0.0000` L2 / `$0.0000` Risk-Adj** | `0` new orders in Shadow Mode |
| **Verified Realized Pure-Riskless Cash P&L** | `$0.00` | `$0.00` (`Shadow != Cash`) | **`+$18.2461` (`79W / 0L`, `100.0%` WR)** |
| **Modeled Taker Fees / L2 Slippage / Unwind Bleed** | `$0.00` (Ignored in L1) | `$0.0000` / `$0.0666` / `$0.7548` | `$0.5825` historical realized fees |
| **Capital Efficiency (Non-Guaranteed Estimate)** | `N/A` | `0.00 bps/hr` (Est. `$0.0000/day`) | Hurdle: **`+7.04 bps/hr` (`$0.8223/day`)** |

### Infrastructure Breakeven Hurdle (`$24.67/month` = `$0.8223/day` = `$0.0343/hr`)

- At **`$48.70`** liquid `pUSD`, covering the `$24.67/month` Finland VM requires **`+7.04 bps/hr`** (`+168.87 bps/day`) continuously deployed; at **`$500.00`** NAV, the hurdle drops `10.3x` to **`+0.69 bps/hr`**.
- Current snapshot constrained shadow portfolio velocity estimate: **`0.00 bps/hr`** (`Covers VM hurdle on this snapshot = False`, daily delta vs `$0.8223/day` hurdle: `$-0.8223/day`).

## 5. Top Verified Executable Opportunities (`CLASS_A` & `CLASS_B`)

- **`0` strictly positive post-fee L2 `CLASS_A/B` opportunities** at the exact polled millisecond snapshot (all tight spreads after Polymarket's V2 `p*(1-p)` dynamic taker fee curve were negative net or below `$1.00` marketable floor and were captured in `DormantOpportunityStore` rather than falsely promoted).

## 6. Multi-Cycle Operating Telemetry (`DISCOVERY_CYCLE` / `FAST_CYCLE` / `RESEARCH_CYCLE`)

| Cycle | Operating Cycle | UTC Timestamp | Wall (`s`) | RSS (`MiB`) | Fresh Books | Candidates | `A` | `B` | `C` | `D` | Active Dormant |
| ---: | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `302` | `FAST_CYCLE` | `2026-11-13T12:51:09Z` | `31.20s` | `176.4` | `1,010` | `1,186` | `0` | `2` | `89` | `502` | `1200` |
| `303` | `DISCOVERY_CYCLE` | `2026-11-13T13:02:16Z` | `244.31s` | `175.0` | `1,698` | `1,715` | `0` | `7` | `151` | `594` | `1200` |
| `304` | `FAST_CYCLE` | `2026-11-13T13:06:22Z` | `27.34s` | `175.5` | `1,078` | `1,118` | `0` | `0` | `58` | `192` | `1200` |
| `305` | `DISCOVERY_CYCLE` | `2026-11-13T13:17:16Z` | `254.07s` | `172.7` | `1,798` | `1,543` | `0` | `1` | `12` | `785` | `1200` |
| `306` | `FAST_CYCLE` | `2026-11-13T13:21:32Z` | `25.31s` | `172.8` | `1,084` | `1,124` | `0` | `0` | `12` | `213` | `1200` |
| `307` | `DISCOVERY_CYCLE` | `2026-11-13T13:32:16Z` | `221.92s` | `171.4` | `1,696` | `1,489` | `0` | `0` | `12` | `833` | `1200` |
| `308` | `FAST_CYCLE` | `2026-11-13T13:36:00Z` | `29.33s` | `171.6` | `1,074` | `1,154` | `0` | `0` | `10` | `250` | `1200` |
| `309` | `DISCOVERY_CYCLE` | `2026-11-13T13:47:17Z` | `265.69s` | `171.4` | `1,733` | `1,529` | `0` | `0` | `10` | `848` | `1200` |
| `310` | `FAST_CYCLE` | `2026-11-13T13:51:45Z` | `28.95s` | `171.7` | `1,084` | `1,164` | `0` | `0` | `10` | `230` | `1200` |
| `311` | `DISCOVERY_CYCLE` | `2026-11-13T14:02:16Z` | `243.49s` | `168.6` | `1,682` | `1,318` | `0` | `4` | `142` | `381` | `1200` |
| `312` | `FAST_CYCLE` | `2026-11-13T14:06:22Z` | `31.19s` | `169.6` | `978` | `950` | `0` | `3` | `54` | `173` | `1200` |
| `313` | `DISCOVERY_CYCLE` | `2026-11-13T14:17:16Z` | `247.01s` | `168.5` | `1,704` | `1,268` | `0` | `3` | `14` | `558` | `1200` |
| `314` | `FAST_CYCLE` | `2026-11-13T14:21:26Z` | `26.73s` | `171.0` | `1,063` | `1,073` | `0` | `3` | `11` | `233` | `1200` |
| `315` | `DISCOVERY_CYCLE` | `2026-11-13T14:32:21Z` | `249.62s` | `169.0` | `1,760` | `1,288` | `0` | `4` | `90` | `381` | `1200` |
| `316` | `FAST_CYCLE` | `2026-11-13T14:36:32Z` | `21.59s` | `171.6` | `1,086` | `1,050` | `0` | `0` | `37` | `201` | `1200` |
| `317` | `DISCOVERY_CYCLE` | `2026-11-13T14:47:16Z` | `254.53s` | `168.8` | `1,642` | `1,265` | `0` | `3` | `21` | `460` | `1200` |
| `318` | `FAST_CYCLE` | `2026-11-13T14:51:33Z` | `31.41s` | `171.8` | `1,086` | `1,088` | `0` | `3` | `13` | `197` | `1200` |

