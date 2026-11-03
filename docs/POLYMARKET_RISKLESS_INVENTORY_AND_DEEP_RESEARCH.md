# Dominus Polymarket Riskless & Structural Arbitrage Inventory + Deep Research Brief

**Generated:** 2026-10-30 UTC  
**Repository:** `Dominus` (`polymarket_live_harvester.py` + `alpha_124_shadow_daemon.py` + `polymarket_live_executor.py`)  
**Current Live Capital Profile:** `$76.53` USDC liquid seed bankroll on Polygon (`Full-Throttle Unlimited-Slot` execution active; `$20.00` daily-loss breaker; `$48.00` emergency seed floor)

---

## How to Use This File

1. **Attach this entire Markdown file** (`POLYMARKET_RISKLESS_INVENTORY_AND_DEEP_RESEARCH.md`) to your Deep Research session (Gemini Deep Research, OpenAI Deep Research, or Claude Research).
2. **Copy and paste the Master Prompt in Part II** into the chat box.
3. Because Part I contains our **complete 42-sleeve inventory, exact fee equations, CLOB/Polygon execution constraints, and post-mortems of every strategy that already failed**, the Deep Research agent will skip generic textbook arbitrage ideas and focus 100% on **net-new, mathematically riskless or super-replicating strategies** that fit our exact execution engine and high-velocity compounding goal.

---

# PART I — Ground-Truth Inventory: What We Have, What Works, and What Failed

## 1. Execution & Smart-Contract Stack Already Built

- **Compute & Colocation:** Dedicated `kraken-finland` Linux VM (`~35–45 ms` RTT to `clob.polymarket.com`), persistent HTTP/2 keep-alive pools, `FastV2OrderSigner` (`py_clob_client_v2`), `PreSignedOrderLadderCache`, and sub-millisecond `/dev/shm` shared-memory tick bus + `/tmp/pm_d1_live_bridge.sock` Unix domain socket IPC (`< 2 ms` shadow-to-live handoff).
- **Real-Time Feeds:**
  - `BTC`, `ETH`, `SOL`, `XRP` Binance + Coinbase spot/perp WebSockets + Chainlink Data Streams / on-chain oracle trackers + Pyth Hermes SSE stream (`SPY`, `QQQ`, `NVDA`, `TSLA`, `AAPL`, `GLD`, `USO`).
  - Polymarket CLOB Market WebSocket (`PolymarketMarketWsCache`) + Authenticated L2 User WebSocket (`PolymarketUserWsCache`).
  - Gamma Markets API event-tree scanner (`alpha_124_shadow_daemon.py` scanning active binary, multi-strike, sports, weather, macro, counting, and `NegRisk` slate events).
- **Order Routing Modes Implemented:**
  1. **Atomic Dual-Leg `FOK` Dominance Box (`hybrid_auto`):** Parallel 2-leg dispatch when `box_cost_net <= $0.975` & symmetric depth `>= 2.0x`; sequential **fragile-leg-first `FOK`** when `$0.975 < box_cost_net <= $0.985` or depth ratio `> 1.20x` (eliminates leg-out slippage when thin leg rejects cleanly at `$0.00` cost).
  2. **Maker-Anchor + Atomic Taker Hedge (`D1_MAKER_ANCHOR_BOX`):** Posts `0%`-fee `post_only=True` GTC BUY on Leg 1; upon User-WS fill event, immediately fires Taker `FOK`/`FAK` BUY on Leg 2 (with `2.5 bps` adverse spot cancel and hedge-ask drift cancel while resting).
  3. **Overround Early Box Exit & Gasless Redemption:** Automatically exits riskless boxes *before* expiry if `bid(Leg_A) + bid(Leg_B) > $1.005` or if either leg's `0%`-fee `$0.99` GTC Maker TP fills; otherwise redeems `15s` post-resolution via gasless Polymarket Relayer V2 (`mergePositions` for `C1` complete sets also implemented).
- **Exact Polymarket Fee Law Implemented:**
  - **Intraday Crypto (`5m`, `15m`, `1h`, `4h`):** `crypto_fees_v2` Taker fee per share $= r \cdot (p \cdot (1 - p))^e$ with $r = 0.07, e = 1.0$ (peaks at `$0.0175/sh` at $p = 0.50$; `$0.0108/sh` at $p = 0.81$). **Maker (`post_only=True` GTC) fee = `0.00%` + `20%` fee rebate.**
  - **Non-Crypto Markets (Sports, Politics, Macro, Fed, Weather, Tweets/Counting, Daily Crypto Up/Down, Equities/Pyth, `NegRisk` Slates):** **`0.00%` Taker fee AND `0.00%` Maker fee** (`feeRateBps = 0`).
- **Hard Exchange Friction Constraints Discovered in Production:**
  - Polymarket CLOB matches off-chain in `< 15 ms`, **but Polygon ERC-1155 settlement takes `2–8 seconds` across split batches**. You *cannot* sell or `mergePositions` newly bought shares until `balanceOf(wallet, token_id) - pre_balance >= shares` settles on-chain.
  - Minimum CLOB limit order size is **`5` shares** (`min_order_size = 5` on most markets, `15` shares on select rewards markets), tick size is `$0.01` (or `$0.001` at extreme tails `< $0.04` / `> $0.96`).

---

## 2. Category A — Proven Live & Positive-Expectancy Sleeves (Currently Active or Validated)

| Sleeve ID | Payoff Structure | Oracle / Domain | Fee Regime | Empirical Track Record (Live / Shadow / Purged WFO) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`D1_SAME_ORACLE_DOMINANCE_BOX`** | Buy `UP(K_low)` (e.g. `15m` or `1h`) + `DOWN(K_high)` (e.g. `5m` or `15m`) sharing **exact same terminal Chainlink timestamp `T`** when `K_low < K_high` and `net_cost <= $0.985`. Payoff $= \$1.00$ outside `(K_low, K_high)` and **`$2.00` (`+103%` jackpot)** inside `(K_low, K_high)`! | Chainlink (`BTC`, `ETH`, `SOL`, `XRP`) | `crypto_fees_v2` (`r=0.07`) | **Shadow:** `30W / 0L` (`100%` WR, `+$122.48` T1000)<br>**Purged WFO Holdout:** `240` boxes, `+$1,991.42`, **`0.0%` leg-out** at `<= $0.985` `hybrid_auto` | **LIVE** (Graduated `30/8`) |
| **`D1_QUIET_BOOK_BOX`** | Same mathematical super-replicating payoff (`UP(K_low) + DOWN(K_high)`, `K_low < K_high`, same expiry `T`), captured passively during low-volatility periods when stale retail/MM asks overlap across horizons. | Chainlink (`BTC`, `ETH`, `SOL`, `XRP`) | `crypto_fees_v2` (`r=0.07`) | **Shadow:** `13W / 0L` (`100%` WR, `+$42.18` T1000) | **LIVE** (Graduated `13/8`) |
| **`D1_MAKER_ANCHOR_BOX`** | Posts `0%`-fee `post_only` Maker BUY on Leg 1 of a `D1` box (`UP(K_low)` or `DOWN(K_high)`), then fires atomic Taker `FOK`/`FAK` on Leg 2 within `50 ms` of Maker fill (`net_cost <= $0.988`, saving `~1.75c/sh` fee on Leg 1). | Chainlink (`BTC`, `ETH`, `SOL`, `XRP`) | Leg 1 `0%` + rebate; Leg 2 `r=0.07` | **Shadow:** `1W / 0L` (`100%` WR, `+$15.37` T1000) | **LIVE BRIDGED** |
| **`CM_B3_PYTH_BARRIER_BOX`** | Cross-strike barrier monotonicity on equities/commodities (`YES(High Barrier)` vs `NO(Low Barrier)` or `UP(Open)` vs `NO(Barrier)` on identical Pyth feed). | Pyth (`SPY`, `QQQ`, `NVDA`, `TSLA`, `GLD`, `USO`) | **`0%` Fee** | **Shadow:** `3` open, `2W / 0L` (`100%` WR, `+$2.05` T1000) | **LIVE BRIDGED** |
| **`COND1_MACRO_PARTITION_BOX`** | Calendar cumulative deadline dominance: Event occurring *"by Date $T_1$"* $\implies$ Event occurs *"by Date $T_2$"* ($T_1 < T_2$). Buys `YES(T_2) + NO(T_1)` for `< $0.985` (`$1.00` floor, `$2.00` middle corridor if event happens in $(T_1, T_2]$). | UMA / Official Gov | **`0%` Fee** | **Shadow:** `3` open, `1W / 0L` (`100%` WR, `+$1.92` T1000) | **LIVE BRIDGED** (`TTE <= 24h`) |
| **`FED1_CENTRAL_BANK_LP_BOX`** | FOMC / ECB / BoJ mutually-exclusive rate-bps partition (`50+ cut`, `25 cut`, `0 hold`, `25+ hike`) cross-box and CME FedWatch / SOFR lock. | Official Fed / ECB Statement | **`0%` Fee** | **Shadow:** `1W / 0L` (`100%` WR, `+$0.50` T1000) | **LIVE BRIDGED** |
| **`SP1_NBA_ZERO_FEE_BOX`** | NBA game-tree dominance: Team Moneyline `WIN` + Opponent Spread `+X.5` (`X >= 1`), or Team Spread `-X.5` + Opponent Moneyline, where `ask_1 + ask_2 < $0.988` (`$1.00` floor, `$2.00` middle corridor if favorite wins by `1..X` pts!). | Official NBA Box Score | **`0%` Fee** | Scanner live; awaiting evening tipoff liquidity | **LIVE BRIDGED** |
| **`SP3_SPORTS_CORRIDOR_DOMINANCE_BOX`** | Multi-sport (`NBA` `1H`/`2H`/`Q1..Q4`/`TeamTotals`, `NFL`, `CFB`, `NHL`, `Soccer`, `Tennis`, `Esports`) half-integer (`*.5`) Alternate Spread (`Favorite -X.5` + `Dog +Y.5`, $X < Y$) & Alternate Total (`Over X.5` + `Under Y.5`, $X < Y$) dominance boxes (`$1.00` floor, `$2.00` middle corridor, zero push/tie risk). | Official League Box Score | `0%` (`NBA`) / `0.03` (`NFL`/`CFB`) / `0.05` (`NHL`/`Soccer`) | Scanner + `SPORTS_CORRIDOR` bridge active (`0%` NBA bridged; fee leagues `_grad8`-gated) | **LIVE BRIDGED** |
| **`NR_CONV_NO_BASKET_ARB`** | (1) Universal 2-leg `NO_i + NO_j < $1.00` mutual-exclusion dominance box across all `NegRisk` slates (`$1.00` floor, `$2.00` on any 3rd outcome); (2) Closed-partition (`negRiskAugmented=False`) `NegRiskAdapter.convertPositions` (`0xc64748c4`) $m$-leg `NO` conversion into $(m-1)$ USDC + residual `YES` bid liquidation. | `NegRiskAdapter` | **`0%` Fee** | Scanner + `NEGRISK_2LEG` bridge + `convertPositions` calldata/Relayer V2 active (`_grad8`-gated) | **LIVE BRIDGED** (`_grad8`) |
| **`U1_DAILY_UPDOWN_LOCK`** | Daily `0%`-fee "Up or Down" candle lock once spot is deep out-of-range near daily close + cross-strike daily barrier dominance. | Binance / Chainlink Daily | **`0%` Fee** | **Shadow:** `1W / 0L` (`100%` WR, `+$12.49` T1000) | **LIVE BRIDGED** (`SINGLE_LEG_LOCK`, `1/8`) |
| **`BOND1_UMA_RESOLUTION_CARRY`** | Buys `$0.95–$0.995` `0%`-fee shares on events where the real-world outcome has **already deterministically occurred** and awaits UMA Optimistic Oracle `2h` liveness finality (`DETERMINISTIC_TERMINAL_HOLD` -> `$1.00` Relayer V2 redeem). | UMA Optimistic Oracle | **`0%` Fee** | **Shadow:** `7W / 0L` (`100%` WR, `7/8` — **1 win from auto-live!**) | **LIVE BRIDGED** (`SINGLE_LEG_LOCK`, `7/8`) |
| **`N1_NEGRISK_CROSS_BOX` & `NR0_ZERO_FEE_SLATE_ARB`** | Complete-set sum-of-asks `< $0.99` across `N`-outcome `NegRisk` mutually-exclusive slates (`sum(YES_i) < $1.00` or `YES_i + YES_j` vs `NO` conversion). | `NegRiskAdapter` | **`0%` Fee** | **Shadow:** `N1` `1W / 0L` (`+$0.25`); `NR0` `2` open, `0` closed | **SHADOW** |
| **Directional WFO Crypto Sniper (`<= $0.81` Taker / `<= $0.82` Maker)** | Lead-lag spot shock (`min_z >= 0.78`, Coinbase divergence veto, `/dev/shm` `85ms` retracement shield, `hold_98` GTC exit). | Chainlink (`BTC`, `ETH` `15m`/`1h`) | Taker `<= $0.81`; Maker `<= $0.82` (`0%` fee) | **Live `<= $0.81` band:** `+$7.05` net (`3W / 1L`; pre-shield loss fixed)<br>**Purged WFO Holdout:** `+$71.19`, `PF = 1.38` | **LIVE** (Full-Throttle) |

---

## 3. Category B — Built in `alpha_124_shadow_daemon.py` with `0` Closed Trades So Far (Low Trigger Rate or Tight HFT Competition)

Do **not** re-propose these exact scanners unless you have a concrete structural modification that unlocks `10x` higher fill frequency:

1. `C1_BINARY_COMPLETE_SET` — Single binary market `ask(YES) + ask(NO) < $1.00 - fees` + `mergePositions` (`0` fills: HFT bots arbitrage single-market `YES + NO < $1.00` in `< 5 ms`).
2. `D1_4H_DOMINANCE_BOX` — `4h` vs `1h`/`15m` Chainlink overlap box (`0` fills so far; `4h` books are thinner).
3. `D2_12PM_BINANCE_BOX` — Daily 12:00 PM ET Binance `BTCUSDT` `1m` close strike vs `Up/Down` dominance box (`0` fills; fires once per 24h).
4. `M3_LADDER_MONO_BOX` — Same-expiry multi-strike ladder monotonicity `YES(Strike K_2) + NO(Strike K_1)` where `K_1 < K_2` (`0` fills; multi-strike books tightly arbitraged by single-event MMs).
5. `B2_BARRIER_NO_LOCK`, `B3_BARRIER_MONO_BOX`, `B4_TOUCHED_BARRIER_WICK_LOCK`, `CM_B2_PYTH_SESSION_NO_LOCK`, `CM_U1_PYTH_CLOSE_LOCK` — One-touch barrier (`Will BTC dip to $X?`) lock after `1m` high/low already breached barrier, or session close lock.
6. `TW1_COUNTING_TRUNCATION_AND_BOX` — Monotone irreversible counters (Elon Musk X/Twitter post count brackets: once confirmed count $= C$, all brackets `< C` are mathematically `$0.00`, i.e., `NO = $1.00`).
7. `W1_SOLAR_PEAK_LOCK`, `W1_LOW_TROUGH_LOCK`, `W3_WEATHER_SLATE_ARB` — METAR airport temperature lock after daily solar peak / overnight trough has passed, plus weather NegRisk slate sum `< $1.00`.
8. `GAS1_AAA_GASOLINE_LOCK` — AAA national daily gasoline average published prior to Polymarket market close.
9. `SP2_NBA_ENDGAME_LOCK` — Late-4Q NBA mathematical/near-certainty score margin lock (`> 99.5%` win probability at `<= $0.985`).
10. `MKR_REWARD_LOCKED_CARRY` — Resting symmetric bids inside `max_incentive_spread` on a market where we already hold a locked `$1.00` box.

---

## 4. Category C — Tried & FAILED / Quarantined Strategies (DO NOT PROPOSE THESE)

Every strategy below **lost money in live or shadow forward-testing** and is hard-quarantined. Any new research proposal **must avoid these exact failure mechanisms**:

| Quarantined / Failed Strategy | Shadow / Live Result | Root-Cause Post-Mortem (Why It Failed) |
| :--- | :--- | :--- |
| **1. `M4_SHOCK_STRIKE_CATCHUP`** | `81` closed, `21.0%` WR, **`-$3,353.61`** (Shadow T1000) | Buying "lagging" multi-strike options after a spot shock suffers severe **adverse selection**: when a strike hasn't moved on Polymarket, it is usually because spot is already mean-reverting or Deribit implied vol collapsed. |
| **2. `W2_ENSEMBLE_VALUE` & `W2_MAKER_OVERROUND`** | `38` closed combined, **`-$1,036.32`** (`8.3%` & `35.7%` WR) | Weather NWP ensemble probabilities (`GFS`/`ECMWF`) miss local airport METAR microclimates (sea breeze, cloud deck) by `2–4°F`; local informed weather bettors pick off only the mispriced side of maker quotes. |
| **3. `S2_EXACT_TWAP_LOCK`** | `2` closed, `50.0%` WR, **`-$93.89`** | Attempted to snipe final-60s settlement assuming Binance `BTCUSDT` TWAP equals Chainlink `BTC/USD`. Failed because **oracle basis (`USDT/USD` premium + Chainlink aggregator update cadence)** can differ by `5–15 bps` right at the strike boundary! **Lesson:** Never assume two *different* oracles (Binance vs Chainlink) settle identically near the strike! |
| **4. `M1_SVI_MAKER_SCALP` & `P1_PREOPEN_MAKER_STRADDLE`** | `33` closed combined, **`-$163.44`** (`40.0%` & `28.6%` WR) | Unhedged passive market-making / pre-open straddles suffer **toxic one-sided fills**: informed flow sweeps the winning leg and leaves us holding only the losing inventory. |
| **5. Unprotected Non-Crypto Maker-Anchor (`ZERO_FEE_MAKER_ANCHOR_BOX` / `ZF_INTRADAY_MAKER_BOX`)** | `3` closed, `0.0%` WR, **`-$18.37`** (`-$12.82` & `-$5.55`) | Posting passive Leg 1 on thin non-crypto books without continuousspot/fair-value anchor: when Leg 1 gets hit, a news headline or whale sweep simultaneously lifts Leg 2's ask above `$1.00 - p_1`, forcing an immediate scratch/legging loss! |
| **6. `CTF_OVERROUND_MINT_SELL` (Split `$1.00` USDC -> Sell `YES + NO > $1.00`)** | Quarantined (`0` net edge at retail latency) | Requires locking `$1.00` on-chain `splitPosition` gas/relayer roundtrip (`3–8s` Polygon block latency) *before* selling into `bid_A + bid_B > $1.00`, by which time sub-5ms pre-funded inventory bots have already hit the bids. |
| **7. Directional Crypto Taker Entries `> $0.81` (`$0.82–$0.86`)** | Live: `18W / 5L` (`78.3%` WR), **`-$56.59` net** | At `$0.85` entry + `crypto_fees_v2` fee, net win is `+$1.62` while a single late-candle reversal loses `-$12.50` (`1 : 7.7` negative payoff skew, requiring `> 88.5%` WR just to break even). Hard-banned in production (`<= $0.81` Taker / `<= $0.82` `0%`-fee Maker). |

---

# PART II — Copy-Paste Master Deep Research Prompt

Copy everything inside the code block below and paste it into **Gemini Deep Research / OpenAI Deep Research / Claude Research** with **this file attached**:

```markdown
You are the Principal Quantitative Researcher and Smart-Contract Microstructure Architect for **Dominus**, an automated real-money Polymarket CLOB + Polygon CTF trading system running 24/7 on a low-latency Linux VM (`~35ms` RTT to `clob.polymarket.com`).

I have attached `POLYMARKET_RISKLESS_INVENTORY_AND_DEEP_RESEARCH.md`, which contains:
1. Our exact live infrastructure (Python asyncio + `/dev/shm` tick bus + `py_clob_client_v2` `FOK`/`FAK`/`GTC post_only` + Polygon `CTF` `mergePositions` + `NegRiskAdapter` + 15s gasless Relayer V2 redemption).
2. Exact Polymarket fee equations (`crypto_fees_v2` `r=0.07` on intraday crypto vs `0.00%` fee on Sports, Politics, Macro, Equities, Counting, and `NegRisk` markets, plus Maker `0%` fee + `20%` crypto rebate + Polymarket Liquidity Rewards / Holding Rewards).
3. All **42 sleeves we already built** (Live, Shadow-Positive, Zero-Fill Scanners, and Quarantined Failures) and **why the failed ones lost money**.

### YOUR MISSION
Conduct an exhaustive, institutional-grade Deep Research investigation (searching Polymarket's latest 2025–2026 CLOB docs, `NegRiskAdapter` / `CTFExchange` smart contracts on Polygon, UMA `OptimisticOracleV3` / Managed Oracle dispute logs, Polymarket Liquidity Rewards & Maker Rebate formulas, academic prediction-market arbitrage literature, and public post-mortems of top Polymarket arbitrage bots) to discover **5 to 8 NET-NEW, mathematically riskless (or state-by-state super-replicating $\min_{\omega \in \Omega} V_T(\omega) \ge \$1.00$) strategies** that we have **NOT** yet built.

### HARD CONSTRAINTS (READ CAREFULLY — ZERO GENERIC FLUFF)
1. **NO DUPLICATES OF EXISTING OR QUARANTINED SLEEVES:**
   - Do NOT propose basic single-market `YES + NO < $1.00` (`C1`), same-oracle crypto `UP(K_low) + DOWN(K_high)` (`D1`), basic `NegRisk` `sum(YES_i) < $1.00` (`NR0`), basic NBA Moneyline+Spread (`SP1`), calendar deadline dominance (`COND1`), or any of the 7 quarantined failure modes in Category C (no cross-oracle basis assumptions like Binance == Chainlink, no unhedged weather NWP models, no naked passive market-making, no `splitPosition` race against pre-funded HFTs).
2. **HIGH CAPITAL VELOCITY FOR A `$76 -> $500` FULL-THROTTLE BANKROLL:**
   - Every proposed strategy MUST either:
     (a) Resolve in **`<= 24 hours`** (intraday sports, esports, tennis, soccer, daily macro/counting/equities, or near-resolution UMA carry), **OR**
     (b) Have a **provable structural early-exit / conversion mechanism** (e.g., `NegRiskAdapter.convertPositions` instant minting of complementary `YES` shares + immediate `0%`-fee CLOB sale, or Locked-Box + Liquidity Reward farming that can be unwound at `>= $1.00` at any time).
   - Minimum order size on Polymarket CLOB is `5` shares; strategies must work cleanly with **`$6–$25` per box/ticket** while scaling to `$100–$500+`.
3. **POLYGON MULTI-BLOCK SETTLEMENT AWARENESS:**
   - Account for the `2–8 second` Polygon ERC-1155 batch settlement delay after a CLOB match before shares can be sold or converted on-chain, and explain how each strategy eliminates or bounds **leg-out risk (IToDE)** to near zero (e.g., fragile-leg-first `FOK`, single-leg `NegRisk` `NO` conversion, or deterministic post-event finality).

### PRIORITY FRONTIER VECTORS TO INVESTIGATE DEEPLY
Investigate these specific structural arenas (plus any superior mechanisms you uncover):

1. **`NegRiskAdapter` (`0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296`) `convertPositions` Asymmetric `NO`-Basket Arbitrage:**
   - How does `convertPositions(marketId, indexSet, amount)` mathematically map $m$ distinct `NO_i` tokens inside an $N$-outcome `NegRisk` event into $(m - 1) \times \$1.00$ USDC **plus** $\sum_{j \notin S} \text{YES}_j$ tokens on-chain?
   - Notice that Polymarket routinely has *"Other"* / *"Placeholder"* / named-only `NegRisk` slates! **CRITICAL:** Check the exact smart-contract behavior of `NegRiskAdapter` when a new candidate/outcome is dynamically added (`augmented NegRisk` / `Other` bucket) — when is `convertPositions` 100% riskless vs when can an unnamed outcome create a trap?
   - Can buying $k$ cheap `NO` tokens (or `1` `NO` token + selling converted `YES` tokens) extract arbitrage across subsets of `2` or `3` liquid candidates **without** having to sweep all `20–30` illiquid tail `YES` books (`NR0`'s bottleneck)?

2. **High-Density US & Global Sports Multi-Market Trees (`300–535` `0%`-Fee Sub-Markets per NBA / NFL / Soccer / Tennis Match):**
   - Single NBA and NFL games on Polymarket currently trade **`$3M–$5M` per game across `300 to 535` `0%`-fee sub-markets** (1Q / 1H / Full-Game Moneylines, Alternate Spread ladders `-1.5, -2.5, ..., -14.5`, Alternate Team Totals & Game Totals, Player Points/Rebounds/Assists milestone ladders `15+, 20+, 25+, 30+`, Halftime/Fulltime, Both Teams to Score, Soccer Draw-No-Bet / Asian Handicap / Over-Under `0.5, 1.5, 2.5, 3.5` goals, Tennis Set 1 Winner vs Match Winner).
   - Enumerate **all exact algebraic dominance & Fréchet-Hoeffding super-replicating inequalities** inside these 500-market sports trees (beyond simple ML + Spread), including **3-leg partitions** (e.g., Soccer `Home Win + Draw + Away Win`, Regulation vs OT rules traps!), **Alternate Spread / Alternate Total corridor boxes** (`Over X.5 + Under Y.5` where `X < Y` -> `$1.00` floor + `$2.00` middle jackpot!), **Player Milestone Monotonicity + Irreversible In-Game Locks** (once a player hits `25` points in Q3 on live NBA API, `25+ PTS YES` is deterministically `$1.00` — unless voided? Check exact Polymarket sports void/DNP/OT settlement rules!).

3. **Zero-Risk Locked-Box + Polymarket Daily Liquidity Rewards (`Q-Score`) Stacking:**
   - Verify Polymarket's exact **2025–2026 Liquidity Rewards formula** (`max_incentive_spread`, `min_incentive_size`, quadratic distance weighting, two-sided `Q_min` multiplier vs single-sided penalty, `1-minute` random book sampling, daily midnight UTC USDC payout).
   - Can a bot hold a locked `$1.00` riskless box (or post offsetting bids on `YES_A` and `NO_A` / cross-market equivalents) to harvest **two-sided `Q_min` Maker Liquidity Rewards** with **zero directional inventory risk**, or use `post_only` quotes that auto-hedge on fill? Quantify realistic APY / daily `$` reward per `$50` deployed.

4. **UMA `OptimisticOracleV3` / Managed Oracle Deterministic Carry & Dispute-Window Microstructure (`BOND1` v2):**
   - What are the exact on-chain events on Polygon (`QuestionInitialized`, `PriceProposed`, `PriceDisputed`, `QuestionResolved` on Polymarket's `UmaCtfAdapter` — provide exact contract addresses & ABIs) that signal when the `2-hour` (`7,200s`) liveness countdown starts?
   - Why do some `"99c UMA bonds"` blow up (e.g., March 2025 / 2026 UMA whale governance attacks, clarification amendments, `P4` "Too Early" proposals)? Design a **100% machine-verifiable smart-contract + ancillary-data filter** that captures `$0.975–$0.994` final-hour UMA liveness carry (`15–60 min` lockup -> `300%+` annualized velocity) while mathematically excluding ambiguous/disputable resolutions.

5. **Cross-Market Logical Implication, Subset/Superset & Linear-Programming (Frank-Wolfe / IP) Combinatorial Arbitrage:**
   - Examples: `Balance of Power` (`GOP Senate + Dem House`, etc.) vs individual `House Winner` + `Senate Winner` markets (`$7.5M+` volume); `Team wins Championship` vs `Team wins Conference` vs `Team makes Playoffs`; `BTC hits $X in October` vs `BTC above $X on Oct 31`.
   - How can a lightweight integer-program / directed-implication graph scanner run in `< 10 ms` in Python across Polymarket's Gamma tag trees without manual market hardcoding, and how do you avoid **resolution-text divergence risk** (where two seemingly implied markets have subtly different UMA ancillary wording)?

6. **Deterministic Public-API "Already Happened" Locks (Sub-Second Official Source vs Retail Book Lag):**
   - Similar in spirit to METAR solar peak or Musk tweet count, what **other recurring daily/weekly `0%`-fee Polymarket categories** depend on a deterministic, machine-readable public feed (e.g., Box OfficeMojo / Rotten Tomatoes lock, Billboard / Spotify daily stream count, TSA checkpoint numbers, App Store rank, YouTube view count at deadline, Chess/Esports API game-end packet, Congressional roll-call vote tally once `218` / `51` votes are mathematically clinched on clerk livestream/JSON)?

### REQUIRED OUTPUT FORMAT FOR EACH STRATEGY (5–8 STRATEGIES RANKED BY CAPITAL-VELOCITY EV)
For each proposed strategy, provide:
1. **Strategy Name & Exact Payoff Proof:** Explicit state-space table showing payoff $V_T(\omega)$ in **every** possible real-world state $\omega \in \Omega$, proving $\min_{\omega} V_T(\omega) \ge \$1.00$ (plus any `$2.00` jackpot corridor).
2. **Resolution-Rule & Smart-Contract Trap Audit:** Every edge case that could break risklessness (OT vs Regulation, DNP/voids, `NegRisk` `Other`/augmented outcomes, UMA `Too Early` / clarifications, oracle denomination mismatch) and the **exact programmatic filter** to block every trap.
3. **Execution Blueprint for Dominus (`$76.53` Seed -> `$500` Scale):**
   - Exact Polymarket Gamma API / CLOB / Polygon RPC endpoints, contract addresses, function selectors, and external free APIs needed.
   - Exact order routing (`FOK` fragile-first, `NegRiskAdapter.convertPositions`, `post_only` Maker + Taker hedge, etc.) respecting `min_order_size = 5` and Polygon `2–8s` settlement delay.
4. **Realistic Frequency, Net Margin per Box (after exact fees/gas), Capital Lockup Duration, and Expected Daily Return on `$76` vs `$500`:** Be brutally honest and empirical — cite real market volumes, spreads, and competition levels on Polymarket in 2025–2026.
5. **Shadow-to-Live Implementation Spec:** Concrete Python data structures and invariants ready to drop directly into `alpha_124_shadow_daemon.py` (`_grad8` `8/8` `100%`-WR gate) and `polymarket_live_harvester.py`.
```
