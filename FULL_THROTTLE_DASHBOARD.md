# DOMINUS — RISKLESS FULL THROTTLE: Live Universe, Shadow & Economic Dashboard

- **Generated At (UTC):** `2026-11-12T22:07:31Z`
- **Active Operating Mode:** `MODE_2_SHADOW` (`Jurisdiction Gate = CA-ON`, `MODE_3_LIVE Hard-Locked = True`, `0` private keys read, `0` live orders placed)
- **Campaign Execution Telemetry:** `17` cycles (`FAST_CYCLE, DISCOVERY_CYCLE, FAST_CYCLE, DISCOVERY_CYCLE, FAST_CYCLE, DISCOVERY_CYCLE, FAST_CYCLE, DISCOVERY_CYCLE, FAST_CYCLE, DISCOVERY_CYCLE, FAST_CYCLE, DISCOVERY_CYCLE, FAST_CYCLE, DISCOVERY_CYCLE, FAST_CYCLE, DISCOVERY_CYCLE, FAST_CYCLE`), Campaign Wall Time `313.20s`, Full-Universe Gamma `/events/keyset` Sweep `204.41s`, Avg `FAST_CYCLE` `30.29s`, In-Memory Listing-to-Eval Latency `37973.8 ms`
- **Swapless Host Safety (`D-010`):** Peak RSS **`174.04 MiB`** (`<= 180.0 MiB` budget OK: `True`)
- **Integrated Peer Tracks:** `discovery=True`, `math_verifier=True`, `proposition_graph=True`, `complete_negrisk=True`, `logical_specialized=True`, `micro_portfolio=True`

## 1. Universe, Order-Book & Relationship Graph Coverage (`Section 12.1`)

| Coverage Dimension | Live Empirical Value | Notes / Protocol Detail |
| :--- | ---: | :--- |
| **Total Observable Active Events** | **`19,630`** | Untruncated Gamma `/events/keyset?active=true&closed=false&after_cursor=...` |
| **Total Child Markets in Active Events / Active Unclosed** | **`372,681` / `200,449`** | 100% retained in discovery census (`CLOSED_OR_ARCHIVED` sibling slots accounted explicitly) |
| **Order-Book Enabled Markets (`enableOrderBook=true`)** | **`200,395`** | `54` markets skipped with explicit `ORDERBOOK_DISABLED` code |
| **Tradable CLOB Outcome Token IDs** | **`400,702`** | Distinct ERC-1155 CTF `YES` / `NO` token IDs |
| **Standard `negRisk` vs `negRiskAugmented` Events** | **`6,342` / `1,858`** | Augmented placeholder/`Other` slates strictly guarded against false partition proofs |
| **Fee-Curve Enabled Markets (`feesEnabled=true`)** | **`199,316`** | Priced via exact Protocol V2 `p*(1-p)` share-haircut schedule (`feeSchedule.{rate,exponent}`) |
| **Proposition Graph Edges (`Total` / `Cross-Market`)** | **`6,079` / `3,495`** | `OFFICIAL_CONTRACTUAL=3,154`, `VERIFIED_MATHEMATICAL=368`, `SUSPECTED=2,463`, `STATISTICAL=94` |
| **Verified Multi-Market Connected Components** | **`124`** | Pruned `O(m log m)` components preventing blind `O(N^2)` combinatorial scans |
| **Fresh L2 Order-Book Markets / Tokens (Latest Cycle)** | **`544` / `1,086`** | Total batched `/books` token polls across campaign: `23,219` |
| **Portfolio Holdings (`Recyclable` / `D-001 Frozen KMIA`)** | **`0` / `4`** | 4 disputed Nov 7 `KMIA` positions (`6707503`, `6707502`, `$50.51`) 100% quarantined |

### Explicit Machine-Readable Eligibility & Skip Accounting

| Skip / Quarantine Code | Market Count | Handling Rule |
| :--- | ---: | :--- |
| `COLD_LAYER_AWAITING_ROTATION` | `199,851` | Retained in discovery registry; excluded from `CLASS_A/B` live promotion |
| `CLOSED_OR_ARCHIVED` | `172,232` | Retained in discovery registry; excluded from `CLASS_A/B` live promotion |
| `AUGMENTED_PLACEHOLDER_OUTCOME` | `2,052` | Retained in discovery registry; excluded from `CLASS_A/B` live promotion |
| `UMA_DISPUTED_QUARANTINED` | `125` | Retained in discovery registry; excluded from `CLASS_A/B` live promotion |
| `ORDERBOOK_DISABLED` | `54` | Retained in discovery registry; excluded from `CLASS_A/B` live promotion |
| `MISSING_TOKEN_IDS` | `44` | Retained in discovery registry; excluded from `CLASS_A/B` live promotion |
| `ZERO_RESTING_DEPTH` | `2` | Retained in discovery registry; excluded from `CLASS_A/B` live promotion |

## 2. Opportunity Families `A..N` Coverage & 5-Tier Proof Breakdown (`Section 12.2`)

- **Total Candidates Structured & Verified (Latest Cycle):** `1,134` (`Mathematically Proven CLASS A + B = 2`, `CLASS_A = 0`, `CLASS_B = 2`, `CLASS_C = 58`, `CLASS_D Rule-Rejected = 365`, `CLASS_E No-Arb/Shallow = 709`)
- **Rule-Mismatch Traps Prevented (`90m vs OT`, `Timezone`, `Touch vs Close`, `Converse`):** **`1,595`**
- **`D-007` `< $500` NAV Sequential `>= 3`-Leg Quarantined Bundles:** **`43`**

| Family | Opportunity Family Description | Structures / Markets Inspected | Emitted | `CLASS_A` | `CLASS_B` | `CLASS_C` | `CLASS_D` | `CLASS_E` | Dormant Near-Miss |
| :---: | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **`A`** | Binary YES/NO Complete-Set Arbitrage (Buy-Merge & Split-Sell) | `611` | `374` | `0` | `0` | `0` | `8` | `366` | `366` |
| **`B`** | Multi-Outcome Exhaustive Set Arbitrage | `37` | `10` | `0` | `0` | `0` | `8` | `2` | `2` |
| **`C`** | Negative-Risk Adapter Conversion & Slate Arbitrage | `23` | `22` | `0` | `0` | `0` | `16` | `6` | `6` |
| **`D`** | Cross-Market Logical Implication & Subset Arbitrage | `107` | `6` | `0` | `0` | `1` | `0` | `5` | `0` |
| **`E`** | Temporal & Deadline Monotonicity Arbitrage | `15` | `14` | `0` | `0` | `5` | `7` | `2` | `0` |
| **`F`** | Price-Threshold & Strike-Ladder Dominance Arbitrage | `301` | `301` | `0` | `0` | `51` | `220` | `30` | `48` |
| **`G`** | Sports Outcome Structure & Advancement Arbitrage | `254` | `254` | `0` | `0` | `0` | `53` | `201` | `0` |
| **`H`** | Weather & Measurable-Event Bracket Arbitrage | `0` | `0` | `0` | `0` | `0` | `0` | `0` | `0` |
| **`I`** | Duplicated & Near-Duplicated Cross-Event Market Arbitrage | `144` | `144` | `0` | `1` | `0` | `50` | `93` | `0` |
| **`J`** | Portfolio Inventory Completion & Split/Merge Recycling | `4` | `0` | `0` | `0` | `0` | `0` | `0` | `0` |
| **`K`** | Near-Resolution & UMA Optimistic Oracle Carry | `544` | `4` | `0` | `0` | `1` | `1` | `2` | `2` |
| **`L`** | Maker/Taker Fee Asymmetry & Passive Box Completion | `544` | `0` | `0` | `0` | `0` | `0` | `0` | `0` |
| **`M`** | Multi-Leg Constrained Component & Portfolio Arbitrage | `220` | `5` | `0` | `1` | `0` | `2` | `2` | `2` |
| **`N`** | Newly Discovered Structures & Protocol Edge Scanner | `1,576` | `0` | `0` | `0` | `0` | `0` | `0` | `0` |

## 3. Multi-Cycle Persistence, Forward `t -> t+1` Validation & Dormant Store

- **Persistence Across Cycles:** `846` unique candidates tracked, `3` unique proven `CLASS_A/B` arbs, `2` persisted `>= 2` cycles (avg observed lifetime `56.22s`).
- **Non-Hindsight Forward Snapshot Validation (`Cycle t -> Cycle t+1`):** `3` tickets re-evaluated on next live `/books` poll, `2` survived (`66.7%`), post-delay validated net PnL **`$16.9444`**.
- **`DormantOpportunityStore` (`dormant_opportunities.json`):** **`1200`** active near-miss / shallow-depth structures retained (`<= 50 bps`: `1200`, `<= 150 bps`: `1200`, book-shift rescans triggered: `1904`, promoted to executable: `2`).
- **`HedgedMakerShadowQuoter` (`Family L` `0 bps` `postOnly` + `15%–25%` Rebate Shadow, Strictly Segregated from Locked Cash):** `16` active resting quotes (`961` posted, `619` hedged fills, `7` adverse-jump unwinds, ex-rebate net shadow PnL `$264.6515`, est. maker rebate `$5.1017`).
- **`HarvesterCandidateBridge` (`d1_live_box_candidates.jsonl` Single-Authority Bridge + JIT `/books` Re-Verify):** `Enabled=True`, `EmittedThisCycle=0` (`TakerBoxes=0`, `MakerLocks=0`), `JITReverified=0`, `JITDecayedBlocked=2`, `CampaignTotalEmitted=0`, `DedupeSuppressed=0`.

### Top Monitored Dormant Near-Arbitrage Structures (Awaiting Book Shift)

| Candidate ID | Fam | Summary | Gap to Breakeven | Reason | Obs / Shift Rescans |
| :--- | :---: | :--- | ---: | :--- | ---: |
| `FAM_C_SYNTH_NO_638396_2698826` | `C` | Discord IPO Closing Market Cap | `0.0 bps` | `ZERO_OR_SHALLOW_L2_DEPTH` | `153 / 3` |
| `FAM_C_SYNTH_NO_74788_668333` | `C` | Guinea-Bissau Presidential Election | `0.0 bps` | `ZERO_OR_SHALLOW_L2_DEPTH` | `140 / 2` |
| `FT_D_MUTUAL_EXCLUSION_6fddfb5c7e89` | `D` | [D] Will Hayden Johnson win by KO or TKO? <-> Wi | `0.0 bps` | `ZERO_OR_SHALLOW_L2_DEPTH` | `9 / 0` |
| `FT_E_TEMPORAL_DEADLINE_IMPLICATION` | `E` | [E] Jensen Huang announced resignation or remo < | `0.0 bps` | `ZERO_OR_SHALLOW_L2_DEPTH` | `16 / 0` |
| `FT_E_TEMPORAL_DEADLINE_IMPLICATION` | `E` | [E] Will Michael Carrick be out as Manchester  < | `0.0 bps` | `ZERO_OR_SHALLOW_L2_DEPTH` | `2 / 14` |
| `FT_E_TEMPORAL_DEADLINE_IMPLICATION` | `E` | [E] Will Michael Carrick be out as Manchester  < | `0.0 bps` | `ZERO_OR_SHALLOW_L2_DEPTH` | `2 / 14` |
| `FT_E_TEMPORAL_DEADLINE_IMPLICATION` | `E` | [E] Will Michael Carrick be out as Manchester  < | `0.0 bps` | `ZERO_OR_SHALLOW_L2_DEPTH` | `2 / 14` |
| `FT_E_TEMPORAL_DEADLINE_IMPLICATION` | `E` | [E] Jensen Huang announced resignation or remo < | `0.0 bps` | `ZERO_OR_SHALLOW_L2_DEPTH` | `2 / 21` |
| `FT_E_TEMPORAL_DEADLINE_IMPLICATION` | `E` | [E] Jensen Huang announced resignation or remo < | `0.0 bps` | `ZERO_OR_SHALLOW_L2_DEPTH` | `16 / 0` |
| `FT_E_TEMPORAL_DEADLINE_IMPLICATION` | `E` | [E] Jensen Huang announced resignation or remo < | `0.0 bps` | `ZERO_OR_SHALLOW_L2_DEPTH` | `16 / 0` |

## 4. Strictly Segregated Economic Accounting & `$24.67/mo` VM Hurdle (`Section 12.3 & 19`)

> **Non-Conflation Invariant:** Simulated paper top-of-book numbers and forward shadow estimates are **strictly segregated** from realized on-chain `pUSD` wallet cash on `kraken-finland`.

| Metric | Column 1: Paper Theoretical (Unallocated L1) | Column 2: Realistic Forward Shadow (Depth-Walked, Post-Fee, Post-Latency) | Column 3: Verified Live Wallet Reality (`kraken-finland`) |
| :--- | ---: | ---: | ---: |
| **Liquid `pUSD` Wallet Cash** | `N/A (Paper)` | `$48.70` (Shadow Ref Budget) | **`$48.695132` (`$48.70`)** |
| **True Worst-Case Floor / Mark-to-Bid NAV** | `N/A` | `$48.70` | **`$48.70` / `$48.83`** |
| **Book Equity (incl. Frozen Disputed `KMIA`)** | `N/A` | `Forbidden for sizing (D-007)` | **`$99.21` (`$50.51` frozen `KMIA`)** |
| **Proven `CLASS A + B` Value (Unallocated Sum)** | `$16.9444` | `$16.9444` L2 / `$13.6515` Post-Latency | `N/A` |
| **Constrained Portfolio Net Value (`$48.70` Cap)** | `Unconstrained` | **`$10.2364` L2 / `$8.2924` Risk-Adj** | `0` new orders in Shadow Mode |
| **Verified Realized Pure-Riskless Cash P&L** | `$0.00` | `$0.00` (`Shadow != Cash`) | **`+$18.2461` (`79W / 0L`, `100.0%` WR)** |
| **Modeled Taker Fees / L2 Slippage / Unwind Bleed** | `$0.00` (Ignored in L1) | `$0.7361` / `$0.0000` / `$0.2264` | `$0.5825` historical realized fees |
| **Capital Efficiency (Non-Guaranteed Estimate)** | `N/A` | `9.58 bps/hr` (Est. `$1.1200/day`) | Hurdle: **`+7.04 bps/hr` (`$0.8223/day`)** |

### Infrastructure Breakeven Hurdle (`$24.67/month` = `$0.8223/day` = `$0.0343/hr`)

- At **`$48.70`** liquid `pUSD`, covering the `$24.67/month` Finland VM requires **`+7.04 bps/hr`** (`+168.87 bps/day`) continuously deployed; at **`$500.00`** NAV, the hurdle drops `10.3x` to **`+0.69 bps/hr`**.
- Current snapshot constrained shadow portfolio velocity estimate: **`9.58 bps/hr`** (`Covers VM hurdle on this snapshot = True`, daily delta vs `$0.8223/day` hurdle: `$+0.2977/day`).

## 5. Top Verified Executable Opportunities (`CLASS_A` & `CLASS_B`)

| Rank | Class | Fam | Candidate ID | Title | Opt `q*` | Cap Req (`$`) | Gross/u | Net L2 (`$`) | Risk-Adj (`$`) | Lockup (`h`) | Efficiency (`bps/hr`) |
| ---: | :---: | :---: | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `1` | `CLASS_B` | `I` | `FT_I_DUP_EXACT_NO1_YES2_4565` | [I] Fernando: 1+ shots on target <-> Ferna | `28.80` | `$12.00` | `+0.5833` | `$16.8000` | `$13.6198` | `2.50h` | `583.3` |
| `2` | `CLASS_B` | `M` | `FAM_M3_CHAIN_690594_690593` | [M] Hyperbeat FDV above $400M one day afte | `100.14` | `$100.00` | `+0.0014` | `$0.1444` | `$0.0317` | `1182.89h` | `0.0` |

## 6. Multi-Cycle Operating Telemetry (`DISCOVERY_CYCLE` / `FAST_CYCLE` / `RESEARCH_CYCLE`)

| Cycle | Operating Cycle | UTC Timestamp | Wall (`s`) | RSS (`MiB`) | Fresh Books | Candidates | `A` | `B` | `C` | `D` | Active Dormant |
| ---: | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `168` | `FAST_CYCLE` | `2026-11-12T20:06:38Z` | `32.56s` | `172.7` | `1,060` | `1,142` | `0` | `0` | `9` | `263` | `1200` |
| `169` | `DISCOVERY_CYCLE` | `2026-11-12T20:17:17Z` | `268.68s` | `171.9` | `1,711` | `1,548` | `0` | `0` | `11` | `637` | `1200` |
| `170` | `FAST_CYCLE` | `2026-11-12T20:21:48Z` | `32.28s` | `173.2` | `1,088` | `1,172` | `0` | `0` | `12` | `250` | `1200` |
| `171` | `DISCOVERY_CYCLE` | `2026-11-12T20:32:21Z` | `253.26s` | `172.3` | `1,746` | `1,551` | `0` | `1` | `59` | `590` | `1200` |
| `172` | `FAST_CYCLE` | `2026-11-12T20:36:36Z` | `32.54s` | `174.6` | `1,066` | `1,215` | `0` | `0` | `30` | `282` | `1200` |
| `173` | `DISCOVERY_CYCLE` | `2026-11-12T20:47:18Z` | `244.09s` | `171.7` | `1,703` | `1,424` | `0` | `2` | `11` | `604` | `1200` |
| `174` | `FAST_CYCLE` | `2026-11-12T20:51:24Z` | `21.39s` | `172.6` | `1,044` | `1,103` | `0` | `1` | `7` | `263` | `1200` |
| `175` | `DISCOVERY_CYCLE` | `2026-11-12T21:02:17Z` | `224.32s` | `170.3` | `1,744` | `1,212` | `0` | `1` | `91` | `329` | `1200` |
| `176` | `FAST_CYCLE` | `2026-11-12T21:06:03Z` | `24.95s` | `171.5` | `1,096` | `916` | `0` | `1` | `38` | `141` | `1200` |
| `177` | `DISCOVERY_CYCLE` | `2026-11-12T21:17:16Z` | `209.87s` | `169.6` | `1,659` | `1,253` | `0` | `2` | `16` | `456` | `1200` |
| `178` | `FAST_CYCLE` | `2026-11-12T21:20:48Z` | `23.79s` | `171.3` | `1,072` | `1,032` | `0` | `1` | `11` | `199` | `1200` |
| `179` | `DISCOVERY_CYCLE` | `2026-11-12T21:32:16Z` | `244.25s` | `169.3` | `1,620` | `1,276` | `0` | `1` | `17` | `449` | `1200` |
| `180` | `FAST_CYCLE` | `2026-11-12T21:36:22Z` | `28.10s` | `171.1` | `1,086` | `1,073` | `0` | `1` | `9` | `177` | `1200` |
| `181` | `DISCOVERY_CYCLE` | `2026-11-12T21:47:16Z` | `255.89s` | `169.2` | `1,704` | `1,320` | `0` | `2` | `26` | `599` | `1200` |
| `182` | `FAST_CYCLE` | `2026-11-12T21:51:34Z` | `37.10s` | `173.1` | `1,034` | `1,130` | `0` | `1` | `20` | `435` | `1200` |
| `183` | `DISCOVERY_CYCLE` | `2026-11-12T22:02:18Z` | `269.90s` | `171.8` | `1,690` | `1,463` | `0` | `3` | `161` | `511` | `1200` |
| `184` | `FAST_CYCLE` | `2026-11-12T22:06:50Z` | `39.86s` | `174.0` | `1,086` | `1,134` | `0` | `2` | `58` | `365` | `1200` |

