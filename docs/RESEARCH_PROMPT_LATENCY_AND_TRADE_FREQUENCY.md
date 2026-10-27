# Deep Research Prompt: Millisecond Reduction → Higher Trade Frequency & Profit (Polymarket)

> Paste everything below the line into your research agent (Gemini Deep Research / ChatGPT Deep Research / Claude research).
> **Attach the codebase** (pick one, in order of preference):
> 1. `polymarket_complete_codebase_dossier.md` (~1 MB, markdown bundle, best for LLM upload)
> 2. `polymarket_full_codebase_v4.py` (~2 MB single-file bundle)
> 3. Core files only: `src/polymarket_research/polymarket_live_executor.py`, `alpha_124_shadow_daemon.py`, `polymarket_live_harvester.py`, `polymarket_terminal_recorder.py`, `exp316_macro_strike_shadow.py`, `weather_metar_engine.py`, `config/polymarket_risk_config.json`, `docs/POLYMARKET_EXPERIMENT_GRAVEYARD_AND_LEDGER.md`
>
> Regenerate bundles first if stale: `python scripts/bundle_polymarket_full_codebase.py`

---

## ROLE
You are a senior low-latency trading-systems engineer and prediction-market quant. You have deep expertise in Polymarket's CLOB (Polygon, EIP-712 signed orders, py-clob-client / CLOB v2), Python asyncio performance, network/TLS/HTTP/WebSocket tuning, cloud region selection, and market microstructure (adverse selection, queue priority, fee-aware edge).

## OBJECTIVE
Produce an **evidence-backed, prioritized, implementable plan** to (1) reduce end-to-end latency (signal → order acknowledged/matched) in milliseconds, and (2) convert that latency gain into **higher trade frequency and higher net PnL** on Polymarket, **without** resurrecting strategies already proven dead (see "Do-Not-Retry" below).

The deliverable must quantify: *"If we cut X ms from stage Y, which strategies gain Z more fills / W more edge, and what is the expected USDC impact?"*

## CONTEXT: THE SYSTEM (attached codebase)
Python (asyncio + `aiohttp` + threaded `requests.Session` for the sync CLOB client) trading stack for Polymarket short-dated crypto (BTC/ETH/XRP 15m/1h candles, daily/weekly multi-strike "Above $X" rungs) and weather (METAR-based) markets. Runs as systemd daemons on a Linux host (shadow + live).

Key components:
| File | Role |
|---|---|
| `src/polymarket_research/polymarket_live_executor.py` (~285 KB) | Live order execution. Has pre-signed order ladder, "v3.3 Single-Hop Sign + Post" (`sign_ms`, `post_ms`, `thread_hop_ms` instrumentation), `post_order(..., defer_exec=True)`, per-thread `requests.Session`, HTTP keepalive warmer, `_safe_create_order`, directional "latency snipe" executor |
| `src/polymarket_research/alpha_124_shadow_daemon.py` (~207 KB) | Main multi-sleeve shadow/live daemon; `fetch_book_after_latency` simulates a 50 ms latency; `aiohttp.TCPConnector(limit=40)`; parallel single-RTT book gather; quarantined sleeves list `QUARANTINED_SHADOW_SLEEVES` |
| `src/polymarket_research/polymarket_live_harvester.py` (~517 KB) | Live harvester / shock detection |
| `src/polymarket_research/polymarket_terminal_recorder.py` | L2 book + aggTrade recorder (data for latency studies) |
| `src/polymarket_research/exp316_macro_strike_shadow.py` | Multi-strike engine; Track A `exp316_late_lock` (7W/0L, active) |
| `src/polymarket_research/weather_metar_engine.py` | METAR `T`-group lock engine (`W1_SOLAR_PEAK_LOCK`, 4/4 WR) |
| `deribit_svi_surface.py`, `barrier_onetouch_svi_engine.py`, `multistrike_svi_scalper.py` | Fair-value / SVI vol-surface models |
| `config/polymarket_risk_config.json` | Risk limits |
| `docs/POLYMARKET_EXPERIMENT_GRAVEYARD_AND_LEDGER.md` | Every retired strategy, root cause, and "do not retry unless…" gate |
| `tests/test_polymarket_execution_parity.py`, `test_v33_microstructure.py` | Execution/microstructure test harness |
| `scripts/honest_purged_wfo_optimizer.py` | Purged walk-forward optimizer (use its methodology for any backtest claim) |

Data available: `data/polymarket/*.json` (WFO results, forensic audit state, shadow expansion state, daily projections).

### Known facts from the ledger (treat as ground truth)
- Polymarket crypto taker fee ≈ **7.0–7.2% quadratic (~1.75¢/share near 50¢)**; **maker = 0% fee**. Fee drag kills reactive taker strategies where true fair-value shift is only 1–2¢.
- **Latency is the explicit "Do Not Retry Unless" gate** for several quarantined sleeves:
  - `M4_SHOCK_STRIKE_CATCHUP` (0W/7L): needs <250 ms reaction; retry only if fees <1.5% or TTE <30m at z≥2.0
  - `P1_PREOPEN_MAKER_STRADDLE` (7W/20L, 85% one-leg fills): retry only with **sub-50 ms cancel-replace websocket maker engine** proving <15% one-leg adverse fill rate
  - `W2_MAKER_OVERROUND`: needs **sub-second METAR push → cancel resting quotes** before :53/:00 release
  - `M1_SVI_MAKER_SCALP`: needs **live Deribit L2 surface + automated delta-cancel <100 ms**
- Active winners: `exp316_late_lock` (Track A), `W1_SOLAR_PEAK_LOCK`, plus Alpha-124 live sleeves (see ledger section 2).
- Trade frequency today is low; the goal is to raise it **only via edge that survives fees and adverse selection**.

## RESEARCH QUESTIONS

### A. Latency budget decomposition (measure before optimizing)
1. From the code, map the **full hot path** for each live sleeve: external signal arrival (Binance WS / Deribit / METAR / Chainlink-style oracle) → parse → decision → risk check → book fetch → sign (EIP-712) → HTTP POST → exchange ack → fill confirmation → exit/cancel path. Produce a table of every stage with **current estimated ms**, where the number comes from (code instrumentation vs. assumption), and what's missing instrumentation.
2. Identify every place a **blocking call, thread hop, `asyncio.sleep`, fresh TCP/TLS handshake, REST poll, JSON re-parse, GC pause, or lock contention** sits on the hot path (cite file + function + approximate line). Rank by ms saved per fix.
3. Define a precise **timestamping scheme** (exchange timestamp vs. local monotonic vs. wall clock, NTP/chrony drift) to produce trustworthy per-stage latency histograms (p50/p95/p99/p99.9), and what to log to the existing recorder.

### B. Network & infrastructure
4. Where is Polymarket's CLOB/API/WebSocket actually hosted (cloud provider/region, CDN/Cloudflare edge, anycast behavior)? What is the **best region/provider/instance type** to colocate for minimum RTT to `clob.polymarket.com` and `ws-subscriptions-clob.polymarket.com`? Include published measurements or community reports; if none, give a concrete **A/B region benchmark protocol** (script design, sample size, metrics).
5. Also locate the upstream signal sources (Binance spot/futures WS endpoints, Deribit, Coinbase, Polymarket RTDS/Chainlink streams, AWC/FAA METAR) – what regions minimize the **sum** of signal RTT + order RTT? Is there a single best location or should signal ingestion and order routing be split?
6. TCP/TLS/HTTP tuning: HTTP/2 vs HTTP/1.1 for order POST, connection pooling & pre-warmed sockets, TLS 1.3 session resumption/0-RTT applicability, `TCP_NODELAY`, keepalive intervals vs. server idle timeouts, DNS caching/pinning, IPv4 vs IPv6, kernel sysctls, and whether the existing keepalive warmer (`[KEEPALIVE]` in executor) is configured optimally.
7. Cloudflare/rate-limit behavior: documented and observed **rate limits** (orders/sec, burst, per-key vs per-IP), `429` handling, and how batching (`POST /orders` batch endpoint, up to N orders) changes effective latency and throughput.

### C. Order construction & execution
8. **EIP-712 signing cost**: measure/estimate Python `eth_account` signing time; evaluate faster alternatives (`coincurve`/libsecp256k1 bindings, Rust/C extension, `py-clob-client` internals, pre-computed domain separators, pre-signed order ladders with expiry/nonce/salt management). Quantify the ms saved and the **risks of pre-signing** (stale price, nonce/salt reuse, expiry, cancel semantics).
9. Evaluate **FOK / FAK / GTC / GTD / post-only** semantics for latency vs. fill-quality; `defer_exec` meaning; whether matching is delayed for marketable orders (documented "matching delay" for crypto/short-dated markets, if any) and how that changes the optimal strategy.
10. Order **cancel/replace latency**: cancel endpoints (single, batch, cancel-all, cancel-by-market), WS-based order management if any, and what **achievable cancel-replace p99** is realistic. Directly assess whether the ledger's "sub-50 ms cancel-replace" gate for `P1_PREOPEN_MAKER_STRADDLE` and "<100 ms delta-cancel" for `M1_SVI_MAKER_SCALP` are physically attainable from the best colo option.
11. Python vs. other runtimes: given measured hot-path breakdown, is the bottleneck Python at all? Compare staying in Python (uvloop, orjson, `httpx`/`aiohttp` tuning, `msgspec`, avoiding `asyncio.to_thread`, process isolation, CPU pinning) vs. a Rust/Go/C++ sidecar for **only** signing+POST. Give a break-even analysis (ms saved vs. engineering cost/risk).
12. On-chain side: any path advantages (e.g., Polygon RPC latency for balances/allowances, proxy-wallet/Safe vs EOA, negRisk adapters) that slow order placement or redemption; and capital-lockup/redeem latency (`redeem_settled_positions.py`) that limits trade frequency.

### D. Data feed latency
13. Compare **WebSocket vs. REST** for Polymarket books/prices (`market` channel, `user` channel, price_change vs. book snapshots, sequencing/gap detection, heartbeat). Is the daemon relying on REST polling (`fetch_book_after_latency`, 50 ms sleeps) where a WS-maintained local L2 book would remove ~1 RTT per decision?
14. Fastest information sources for each sleeve: Binance `aggTrade`/`bookTicker`/`depth@100ms` vs. futures streams; Polymarket's own "crypto prices" RTDS feed (Chainlink/Binance-sourced) and **how the market's resolution oracle (open/close price source) updates** relative to Binance; METAR/SPECI release times and faster raw sources (AWC, NOAA, direct feeds); Deribit WS book/ticker channels. Estimate the **information half-life** (how many ms until Polymarket MMs reprice) for each signal type using public evidence and our recorder data.
15. Clock/Timing edge: for 15m candle markets, how does `openPrice` fixing, market creation timing, and resolution timestamping work, and where does a few-ms edge matter vs. where it is irrelevant?

### E. Converting latency into trade frequency & profit (the core question)
16. For **each live and quarantined sleeve** (use the ledger), build a table: *latency sensitivity* (how edge decays vs. ms of delay), *current realized latency*, *latency required for positive net EV after fees*, and *verdict* (worth pursuing / not latency-limited / structurally dead). Use a simple model: edge(t) = edge₀·exp(−t/τ) minus fee minus spread, with τ estimated from data.
17. Identify **new or under-exploited opportunity classes** that become viable at lower latency and are **fee-favorable** (maker 0% fee focus): maker rebates/liquidity rewards programs, quote-and-cancel around oracle updates, cross-market/cross-venue lag (Polymarket vs. Binance/Deribit/Kalshi/others), complement-sum arbitrage (UP+DOWN < $1 after fees), negRisk arbitrage, resolution-boundary lock strategies, stale-quote sniping on others' resting orders. For each: required latency, estimated frequency (trades/day), edge per trade, capacity, and competition level (who else is doing it, evidence).
18. **Frequency scaling**: what limits our trades/day today (signal scarcity, risk gates, TTE filters, capital, single-position mutual exclusion, rate limits, latency)? Rank blockers and show which are latency-solvable vs. policy-solvable. Suggest safe relaxations to `polymarket_risk_config.json` if supported by evidence.
19. Quantify **adverse selection vs. latency** for maker strategies: how fast must we cancel to keep one-leg fill rate <15% (P1) etc. Use queue-position and Poisson/Hawkes-style arrival modeling, calibrated to our recorded books.
20. Competitor landscape: public information on other Polymarket bots/MMs (open-source repos, blogs, Dune dashboards, Polymarket "builder"/MM programs), their observed latency tier, and where retail-grade infra can still win. Cite sources.

### F. Validation methodology
21. Specify how to validate every proposed change **honestly**: latency simulator that replays recorded L2 books with injected delay (replace the hardcoded `50 ms` with measured distribution), purged walk-forward CV (reuse `honest_purged_wfo_optimizer.py` conventions), fee-exact fills, queue-position-aware maker fills, no look-ahead, and minimum sample sizes/confidence thresholds before going live. Include a **shadow A/B plan** (old vs. new latency path running in parallel) and kill-switch criteria.
22. Safety: how to avoid new failure modes from speed (duplicate orders, stale pre-signed orders, runaway loops, double-spend of allowance, partial fills, 429 bans). Recommend invariants/tests (extend `tests/test_polymarket_execution_parity.py`).

## DO-NOT-RETRY CONSTRAINTS
Do **not** recommend re-running any strategy in the ledger's Graveyard unless you show, with numbers, that its explicit "Do Not Retry Unless…" gate is now met by the proposed latency/infra changes. Do not propose strategies that rely on taker trades at the ~7% quadratic fee with <3¢ edge. Read `docs/POLYMARKET_EXPERIMENT_GRAVEYARD_AND_LEDGER.md` fully before proposing anything.

## REQUIRED RESEARCH METHOD
- Read the attached codebase first; **cite file names, functions and approximate line numbers** for every claim about current behavior. Do not assume—if the code doesn't show it, say "unknown, needs instrumentation".
- Then research externally: Polymarket official docs (CLOB API, rate limits, order types, WebSocket, fees, maker rewards, RTDS), `py-clob-client` / `rs-clob-client` source, GitHub bots, Dune/Polymarket analytics, Cloudflare/AWS region docs, Python perf literature. **Cite URLs and dates**; flag anything older than ~6 months as possibly outdated (Polymarket changes fees/matching rules often, including the V2 client).
- Clearly separate: **(Verified fact) / (Documented claim) / (Community anecdote) / (Your inference)**.
- Provide numeric estimates with ranges and confidence levels, not adjectives.

## REQUIRED OUTPUT FORMAT
1. **Executive summary** (≤ 10 bullets): biggest ms wins, biggest profit levers, what NOT to do.
2. **Current latency budget table** (stage, current ms, source, confidence, instrumentation gap).
3. **Ranked optimization backlog**: `# | change | files touched | ms saved (range) | effort (hrs) | risk | strategies helped | expected Δ trades/day | expected Δ net USDC/day | confidence`. Sort by (value ÷ effort).
4. **Infrastructure recommendation**: provider/region/instance, network settings, with a benchmark script outline and acceptance thresholds.
5. **Strategy-by-strategy latency sensitivity table** (live + quarantined), with verdicts and revived/not-revived decisions tied to ledger gates.
6. **New opportunity shortlist** (maker-fee-favorable first) with required latency, frequency, edge/trade, capacity, competition.
7. **Implementation roadmap**: Phase 0 (instrumentation, 1–2 days), Phase 1 (quick wins, <1 week), Phase 2 (structural, 1–4 weeks), Phase 3 (optional language/colo investment). Each phase has exit criteria and shadow-validation requirements.
8. **Code-level patch sketches** for the top 5 changes (diff-style or pseudocode against the real functions).
9. **Validation & risk plan** (backtest/replay design, shadow A/B, kill-switches, tests to add).
10. **Open questions / data I need to collect** (and exact log fields to add to `polymarket_terminal_recorder.py`).
11. **Source list** with URL, date, and reliability grade.

## QUALITY BAR
- Prioritize **net-of-fee, net-of-adverse-selection** profit over raw trade count. More trades with zero/negative edge is a failure.
- Be skeptical: if latency is *not* the binding constraint for a sleeve, say so and redirect effort.
- Where evidence is thin, propose the cheapest experiment that would resolve it rather than speculating.
- Keep recommendations compatible with the current architecture (Python/asyncio/systemd) unless the break-even analysis justifies a change.
