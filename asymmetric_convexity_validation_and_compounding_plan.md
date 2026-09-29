# Asymmetric Convexity Validation & Compounding Plan: Tri-Engine Blueprint (v3.1 Forensic Institutional Gold Standard)

---

## Section 0: Executive Status & The 6-State Institutional Progression Architecture

### 1. The 6-State Lifecycle Progression Model
To eliminate observer bias, multiple-testing contamination, and retroactive parameter drift, all pipeline components operate strictly within a formal 6-state progression model:

```
[STAGE 1: DEVELOPMENT]
  └── Exploratory research, parameter discovery, and plumbing construction.
         │
         ▼ (Freeze Code & Architecture)
[STAGE 2: FROZEN VALIDATION]
  └── Immutable code; zero parameter tuning; pre-registered primary endpoint.
         │
         ▼ (Pass Engineering Screen: 30–50 Shocks)
[STAGE 3: STATISTICAL CERTIFICATION]
  └── Pre-registered sample (N >= 100 independent episodes across >= 14 days).
  └── Hard Hurdle: LCB_95%,cluster(E[R_net]) > 0 AND p_placebo < 0.01 under 25 bps.
         │
         ▼ (Pass Certification Gate)
[STAGE 4: CANARY DEPLOYMENT]
  └── Live execution in firewalled sandbox ($20 micro-capital outlay).
         │
         ▼ (Pass Slippage & Implementation Shortfall Verification)
[STAGE 5: CAPACITY VALIDATION]
  └── Progressive sizing expansion testing book depth and market impact.
         │
         ▼ (Demonstrated Invariance to Scale)
[STAGE 6: PRODUCTION ALLOCATION]
  └── Integrated capital allocation within the Sovereign Portfolio.
```

> **Governance Invariant**: Backward transitions require the assignment of a new, distinct Experiment ID. No production parameter may be modified retroactively based on observed validation data.

---

### 2. Capital Allocation Disambiguation: Strategic Target vs. Realized State
To maintain institutional clarity, portfolio allocation distinguishes between theoretical target architecture and live realized capital deployment:
* **Strategic Target Allocation**: $85\%$ Core Compounding Engine / $15\%$ Satellite Sprints.
* **Current Realized Allocation**: $\mathbf{100\% \text{ Core Allocation}}$ ($\mathbf{\$620.51\text{ USDC}}$ total NAV, $\mathbf{\$610.92\text{ USDC}}$ unallocated cash reserves).
* **Satellite Realized Capital**: $\mathbf{\$0.00\text{ USDC}}$ live wallet exposure. Phase B1 is running in isolated shadow simulation; zero real capital is at risk until formal Phase B2 statistical certification.

---

### 3. Current Operational State (v3.1 Sovereign Alignment)

| Pipeline Track | Current Lifecycle State | Operational Mandate & Running Status |
| :--- | :--- | :--- |
| **Engine 1 (EXP-103 Apex)** | **STAGE 6: PRODUCTION ALLOCATION** | **Frozen Core Daemon** ([`production_apex_daemon.py`](file:///home/skybullet1987/quant_pipeline/src/execution/production_apex_daemon.py), PID `16797`). Realized NAV: **$620.51 USDC**, Cash: **$610.92 USDC**, Peak HWM: **$642.10 USDC**. Holding 1 ETH 10x position (+$3.13 funding carry earned). Bar 7/18 complete; Bar 8/18 audit at **20:00:14 UTC**. |
| **Engine 1 Shadow (EXP-104)** | **STAGE 1: DEVELOPMENT (Shadow)** | Shadow Daemon ([`src/execution/exp104_macro_hedge_shadow.py`](file:///home/skybullet1987/quant_pipeline/src/execution/exp104_macro_hedge_shadow.py), PID `2851516`). Logging 60s comparative forward equity against EXP-103; designated strictly as a **performance measurement checkpoint** on October 1 (requires minimum 30 calendar days + multi-regime coverage before live consideration). |
| **Engine 2 (HL Ratchet)** | **STAGE 2: FROZEN VALIDATION** | Shadow Daemon ([`src/hl_leadlag/execution/hl_isolated_ratchet_shadow.py`](file:///home/skybullet1987/quant_pipeline/src/hl_leadlag/execution/hl_isolated_ratchet_shadow.py), PID `2894894`). Phase B1 engineering screen across 4 assets (`SOL`, `HYPE`, `SUI`, `DOGE`) with counterfactual policy benchmarking, dynamic OFI routing, +0.70% Net-BE lock, and per-asset slippage logging. |
| **Engine 3 (Polymarket Lab)** | **STAGE 1: DEVELOPMENT (Data Lab)** | Recorder ([`src/polymarket_research/polymarket_terminal_recorder.py`](file:///home/skybullet1987/quant_pipeline/src/polymarket_research/polymarket_terminal_recorder.py), PID `2037196`) & Paper Trader ([`src/polymarket_research/polymarket_paper_trader.py`](file:///home/skybullet1987/quant_pipeline/src/polymarket_research/polymarket_paper_trader.py), PID `2894914`). Retrospective development set (`R3_DEV`): 7 settled trades (85.71% WR, +$113.44 PnL). Frozen out-of-sample ledger (`R3_VALIDATION_START_UTC`) active. |
| **Track 1 (Derive Options)** | **PERMANENTLY TERMINATED & ARCHIVED** | Falsified at Gate 1 (depth <$9k, MM bids $0.00). Sockets closed, background processes killed, data archived to `data/archive/derive_experiment_d_falsified_20260929.tar.gz`. |

```
========================================================================================================
                     TRI-ENGINE SOVEREIGN PRODUCTION PIPELINE (v3.1)
========================================================================================================
[ENGINE 1: CORE COMPOUNDING PERPETUAL] ──> 100% Realized Capital Allocation ($620.51 NAV, $610.92 Cash)
  ├── Live Daemon : production_apex_daemon.py (PID 16797, systemd active, 0-Mutation Invariant)
  ├── Strategic Target: 85% Core / 15% Satellites (Enforced upon Phase C authorization)
  ├── Micro Cycle : Bar 7/18 Complete -> Bar 8/18 at 20:00:14 UTC (4H Micro Risk Audit)
  ├── Macro Cycle : Bar 18/18 at 2026-10-01 12:00:00 UTC (72H Macro Rebalance, 240s ALO Window)
  └── Shadow Engine: exp104_macro_hedge_shadow.py (PID 2851516, Dynamic Ratchet Floor $577.89)

[ENGINE 2: ROUTE 2 HL RATCHET MOMENTUM] ──> Isolated Subaccount ($20-$50 Sandbox, $0.00 Real Capital)
  ├── Shadow Daemon : hl_isolated_ratchet_shadow.py (PID 2894894, Stage 2 Frozen Validation)
  ├── Asset Universe: SOL (20x), HYPE (10x), SUI (10x), DOGE (10x)
  ├── Order Flow    : Binance USD-M aggTrade (>= $1.5M/100ms) + Tokyo Hyperliquid L2 WebSocket
  └── Enhancements  : Counterfactual Policy Benchmarking, Dynamic OFI Routing, +0.70% Early Net-BE Lock

[ENGINE 3: ROUTE 3 POLYMARKET DATA LAB] ──> Read-Only Paper Sandbox ($1,000 Paper NAV)
  ├── Paper Trader : polymarket_paper_trader.py (PID 2894914, Late-Candle TTE <= 15m Sweet Spot)
  ├── Data Recorder: polymarket_terminal_recorder.py (PID 2037196, Dual-Feed Telemetry Antenna)
  └── Development Ledger: 7 Settled Trades | 6 Wins / 1 Loss (85.71% WR) | +$113.44 PnL ($1,113.44 Equity)

[TRACK 1: DERIVE 0DTE OPTIONS] ──> [FALSIFIED & PERMANENTLY TERMINATED]
  ├── Verdict: Insufficient Terminal Depth (<$9k) & Systematic MM Bid Withdrawal ($0.00 Bids)
  └── Action : Background probes terminated, sockets closed, data archived to data/archive/
========================================================================================================
```

---

## Section 1: Canonical Accounting Model, Arithmetic, and Mechanical Precision

### 1. Friction Recalibration & Series Bankroll ($C_{\text{series}} = \$60.00$)
Under the stated friction parameters for the $20\times$ SOL model ($N_1 = \$400$, nominal stop $d_{\text{stop}} = 0.0180$, slippage $d_{\text{slip}} = 0.0007$, fees $d_{\text{fees}} = 0.0009$, funding $d_{\text{funding}} = 0.00005$, yielding total friction $c_{\text{all-in}} = 0.00165$ or $16.5\text{ bps}$):

$$\text{Loss}_{\text{modeled}} = N_1 \cdot (d_{\text{stop}} + c_{\text{all-in}}) = 400 \cdot (0.0180 + 0.00165) = \mathbf{\$7.86 \text{ per full-stop execution}}$$

#### Impact on Series Bankroll:
Supporting six consecutive modeled full-stop executions requires:
$$C_{\min, 6} = \$20.00 + 5 \cdot \$7.86 = \mathbf{\$59.30}$$

> **Accounting Reserve / Residual Cash Allowance**: The series bankroll is locked at **$C_{\text{series}} = \$60.00$**. The $+\$0.70$ difference above $\$59.30$ is formally designated strictly as an **accounting reserve / residual cash allowance**, not an operational market safety margin. Real market safety is governed exclusively by P95/P99 execution loss modeling and the programmatic hard loss budget guard ($B_{\text{remaining}} \le 0$).

---

### 2. Disambiguating Entry Notional vs. Marked Notional
To prevent margin and liquidation calculation errors, position notional is formally decoupled into four distinct state variables:
1. **$N_{\text{entry, total}}$**: $\sum_i Q_i \cdot P_{\text{entry}, i}$ (Cumulative initial cash commitment basis = $\$500.00$ at nominal SOL sizing).
2. **$N_{\text{marked, total}}$**: $Q_{\text{total}} \cdot P_{\text{mark}}$ (Current mark-to-market position size = $\$506.00$ after a $+1.50\%$ move on leg 1).
3. **$Q_{\text{total}}$**: $\sum_i Q_i$ (Total contracts held).
4. **$\text{VWAE}$**: $\frac{\sum_i Q_i \cdot P_{\text{entry}, i}}{Q_{\text{total}}}$.

The liquidation formula dynamically ingests $Q_{\text{total}}$ and live account equity, strictly avoiding static notional approximations:
$$P_{\text{liq}} = P_{\text{entry}} - \text{side} \cdot \frac{\text{Margin Available}}{Q_{\text{total}}} \cdot \frac{1}{1 - l \cdot \text{side}}$$

---

### 3. Explicit Four-Tier Breakeven Nomenclature
The ambiguous "+0.390% net BE" label is split into four distinct mathematical definitions:
* **$P_{\text{BE}}^{\text{gross}}$**: $\text{VWAE}$ (Price where gross trading PnL is zero $= +0.300\%$).
* **$P_{\text{BE}}^{\text{fee-only}}$**: $\text{VWAE} + \frac{\sum \text{Fees}_{\text{entry}} + \mathbb{E}[\text{Fee}_{\text{exit}}]}{Q_{\text{total}}}$ (Pure fee breakeven $= +0.390\%$).
* **$P_{\text{BE}}^{\text{expected}}$**: $\text{VWAE} + \frac{\text{Fees}_{\text{past}} + \mathbb{E}[\text{Fee}_{\text{exit}}] + \mathbb{E}[\text{Slippage}_{\text{exit}}] + \mathbb{E}[\text{Funding}]}{Q_{\text{total}}}$ (Expected all-in net breakeven $\approx +0.465\%$).
* **$P_{\text{BE}}^{\text{P95}}$**: Expected breakeven evaluated using 95th-percentile adverse exit slippage ($\approx +0.580\%$).

---

### 4. Standardized Funding Sign Convention
The cash-flow identity matches Hyperliquid's protocol mechanics (where positive funding rates mean longs pay shorts, and negative rates mean longs receive cash):

$$\text{PnL}_{\text{realized}} = \text{PricePnL} - \text{Fees} + \text{FundingCashflow}$$

where **$\text{FundingCashflow} > 0$ denotes net cash received by the account**. Statements such as "+$3.13 funding carry earned" directly reflect positive net cash added to portfolio equity.

---

### 5. Dynamic Fee Architecture
Hardcoded assumptions of $4.5\text{ bps}$ taker and $1.5\text{ bps}$ maker fees are removed from production invariants. The engine dynamically queries the account's fee tier:

$$\text{FeeRate}_{\text{effective}} = f(\text{account\_tier}, \ \text{order\_type}, \ \text{maker\_rebate})$$

Realized fees are recorded directly from transaction receipts (`observed_fee_rate(fill)`).

---

## Section 2: Route 2 (Hyperliquid Ratchet Momentum): Scientific De-Biasing & Statistical Certification

### 1. Two-Tier Hypothesis Hierarchy: Signal Alpha vs. Routing Increment
To eliminate circularity and false attribution, Route 2 explicitly bifurcates into two distinct, ordered scientific hypotheses:

#### A. Route 2A — Shock Alpha (Primary Null Hypothesis)
$$\boxed{ H_{0, A}: \mathbb{E}[R_{\text{SOL}}] \le 0 \quad \text{vs.} \quad H_{1, A}: \mathbb{E}[R_{\text{SOL}}] > 0 }$$
* **Objective**: Tests whether the high-value aggressive-flow episode predicts directional continuation on the pre-specified primary baseline asset (SOL).
* **Singular Primary Gate**: If Route 2A fails, **Phase C live deployment is unconditionally aborted**. Positive secondary metrics cannot override a primary failure.

#### B. Route 2B — Routing Increment (Secondary Confirmatory Null Hypothesis)
$$\boxed{ H_{0, B}: \Delta_{\text{MOS}} \le 0 \quad \lor \quad \Delta_{\text{MOR}} \le 0 }$$
where:
$$\Delta_{\text{MOS}} \equiv \mathbb{E}[R_{\text{Max-OBI}}] - \mathbb{E}[R_{\text{SOL}}]$$
$$\Delta_{\text{MOR}} \equiv \mathbb{E}[R_{\text{Max-OBI}}] - \mathbb{E}[R_{\text{Random}}]$$

#### Joint Intersection-Union Confirmatory Test:
The routing test is defined as a single joint confirmatory test:
$$p_{\text{routing}} = \max(p_{\text{MOS}}, \ p_{\text{MOR}})$$
under the pre-registered market-hour clustered/permutation procedure.
$$\mathbf{p_{\text{routing}} < 0.01}$$

#### Governance Decision Matrix:
1. **If Route 2A Fails**: Zero capital authorization. No Phase C deployment.
2. **If Route 2A Passes but Route 2B Fails**: SOL-only remains an eligible research candidate; the Max-OBI router is rejected as non-additive.
3. **If Both Route 2A and Route 2B Pass**: The Max-OBI multi-asset routing policy is certified and may proceed to Phase C canary deployment.

---

### 2. Counterfactual Policy Benchmarking & Deterministic Randomness
To eliminate winner's selection bias, the shadow engine evaluates **four concurrent routing policies** on every qualifying shock episode:

| Policy Identifier | Policy Description | Scientific Purpose | Deterministic Invariant |
| :--- | :--- | :--- | :--- |
| **Policy 1: SOL-Only** | Always dispatches to SOL regardless of other books | Pre-specified primary baseline | Fixed ticker: `SOL` |
| **Policy 2: Random Eligible** | Dispatches to a randomly chosen eligible asset | Null hypothesis for asset selection | `random_policy_seed = hash(episode_id, salt)`, logged deterministically |
| **Policy 3: Round-Robin** | Cycles deterministically across SOL $\to$ HYPE $\to$ SUI $\to$ DOGE | Exposure-control baseline | Deterministic counter modulo eligible count |
| **Policy 4: Max-OBI Router** | Dispatches to highest positive $\text{OBI}_{\text{top}}$ | Candidate active strategy | $\text{argmax}_{c} \text{OBI}_c$ |

---

### 3. Machine-Enforced "Independent Episode" Linking Rule
To prevent double-counting liquidation cascades as multiple independent statistical observations, the event detector enforces an immutable episode-linking rule:
* An episode initiates at qualifying shock timestamp $t_0$.
* Any subsequent qualifying sweep occurring within a cooldown window of **$\tau_{\text{cooldown}} = 300\text{ seconds}$ (5 minutes)** or while a sprint is actively open belongs to the **SAME episode**:
  $$\text{EpisodeID}_{t+1} = \text{EpisodeID}_t \quad \text{if } (t_{k+1} - t_k < 300\text{s}) \lor (\text{ActiveSprint} = \text{True})$$
* **Statistical Reporting Requirements for $N \ge 100$**:
  1. Count of independent episodes $N_{\text{episodes}}$
  2. Distinct UTC trading days ($\ge 14$)
  3. Maximum episodes per day (capping cluster density)
  4. Volatility-regime coverage (high-vol vs. low-vol distribution)
  5. BTC macro trend-state coverage (bull, bear, range-bound)

---

### 4. Decoupled B2 Freeze Boundary: Timestamps vs. Code SHAs
To prevent forensic ambiguity between data windows and code commits, the Phase B2 boundary explicitly separates data time from implementation hashes:
* **`B2_START_UTC`**: `2026-09-29T17:32:15.000Z` (The immutable data start boundary).
* **`B2_CODE_SHA`**: [`723db2c`](https://github.com/skybullet1987/quant_pipeline/commit/723db2c) (The core protocol freeze implementation boundary).
* **`B2_SCHEMA_SHA`**: [`08d50e8`](https://github.com/skybullet1987/quant_pipeline/commit/08d50e8) (The schema and operational guard boundary).

> **Enforcement Rule**: All sprints observed prior to `B2_START_UTC` (including the 4 exploratory runs) are permanently classified as development data and are excluded from the Phase B2 statistical certification ledger.

---

### 5. Empirical Liquidation Safety & Stop Integrity (Factual Protocol Correction)
Hyperliquid's official documentation explicitly confirms that **there is no clearance fee on liquidations**; liquidations are executed via market orders on the order book and backstop liquidator vault. The wider buffer on $10\times$ assets (`HYPE`, `SUI`, `DOGE`) is properly designated as **providing additional distance from forced liquidation and backstop-liquidation risk during fast adverse moves**.

#### Signed Liquidation Distance Metric:
For long positions, the shadow engine logs the signed normalized distance:
$$B_{\text{liq}} = \frac{P_{\text{stop\_fill}} - P_{\text{liq}}}{P_{\text{entry}}}$$

#### Independent Stop Integrity Tripartite Distribution:
Rather than relying on a scalar P05 distance, the engine independently logs:
1. $P(\text{stop fully filled before liquidation})$
2. $P(\text{partial stop fill before liquidation})$
3. $P(\text{liquidation triggered before stop completion})$

---

### 6. Hard Machine-Enforced Loss Budget Guard
A fifth invariant is added to the pre-trade validation gate:
$$B_{\text{remaining}} = C_{\text{series}} - \sum \text{Loss}_{\text{realized}} - \text{Loss}_{\text{P95, new}}$$
The execution gateway rejects order generation if $B_{\text{remaining}} \le 0$, making the capital-preservation ceiling a programmatic invariant rather than an operational guideline.

---

## Section 3: Engine 1 Governance & Execution Optimization (EXP-103 & EXP-104)

### 1. Capital Carrying Value & Grossman-Zhou Drawdown Control
* **Current Core NAV**: **$620.51 USDC** ($610.92 cash balance earning baseline margin safety).
* **Grossman-Zhou (1993) Optimal Drawdown Control Cushion**:
  Under the Grossman-Zhou optimal portfolio drawdown framework, the safe floor parameter $\alpha = 0.8255$ defines the dynamic capital floor $F_t = \alpha \cdot \text{HWM}_t = 0.8255 \times \$642.10 = \$530.05$.
  Current portfolio cushion is:
  $$C_t = \frac{\text{NAV}_t - F_t}{\text{NAV}_t} = \frac{620.51 - 530.05}{620.51} = \mathbf{14.58\% > 0}$$
  Drawdown from peak is $-3.36\%$, well within the acceptable cushion.
* **Positive Carry**: Single active 10x ETH position has accumulated **+$3.13 in net funding carry**.

---

### 2. October 1 Milestone: Measurement Checkpoint Only
The 60-hour pre-rebalance shadow window of EXP-104 is recognized as statistically insufficient for production authorization.

> **Governance Rule**: October 1 is designated strictly as a **performance measurement checkpoint**, not a promotion gate. EXP-104 will continue logging forward performance in shadow mode across a **minimum 30 calendar days AND multi-regime coverage** (at least 1 bear regime with BTC 7D return $\le -5\%$, 1 bull regime, and 1 range-bound regime) before any live parameter promotion is considered.

---

### 3. ALO Window Optimization: Paired Net Execution Cost Function
Expanding the Post-Only (ALO) window from 180 seconds to 240 seconds is evaluated strictly on paired identical rebalance snapshots:
$$\Delta \text{Cost}_{\text{net}} = \text{Cost}_{\text{net}}(240\text{s}) - \text{Cost}_{\text{net}}(180\text{s}) < 0$$
where:
$$\text{Cost}_{\text{net}} = \text{Fees} + \text{Slippage} + \text{AdverseSelection} + \text{OpportunityCost}$$
Both configurations must be evaluated from the same signal, book state, inventory, and decision timestamp.

---

## Section 4: Engine 3 (Polymarket Data Lab): Econometrics, Information Flow, and Cost Decoupling

### 1. Evidence Realism & Primary Evaluation Metrics
Win rate is retired as the primary evaluation metric and replaced with:
* **Mean Net Return**: $\mathbb{E}[R_{\text{net}}]$
* **Brier Score Calibration**: $\frac{1}{N} \sum (p_{\text{model}} - Y)^2$
* **Log-Loss Residuals**: $-\sum [Y \ln(p_{\text{model}}) + (1 - Y) \ln(1 - p_{\text{model}})]$
* **Expected Value Margin**: $\mathbb{E}[p_{\text{model}} - P_{\text{effective\_all\_in}}]$

---

### 2. Non-Linear Fee Clarification
The fee schedule is explicitly defined by the non-linear contract formula with parameter $\text{feeRate} = 0.07$:

$$\text{Fee} = C \cdot 0.07 \cdot p(1 - p) \implies \frac{\text{Fee}}{C \cdot p} = 0.07(1 - p)$$

This distinguishes the formula's 7% parameter from a flat 7% fee on invested capital.

---

### 3. Decoupling Execution Crossing Cost from Fee Cost
To isolate spread impact from exchange fees, transaction friction is decomposed into separate components:
$$\text{CrossingCost}_{\text{execution}} = \text{VWAP}_{\text{book}} - q_{\text{mid}}$$
$$\text{FeeCost} = \frac{\text{Fee}(C)}{Q_{\text{shares}}}$$
$$\text{AllInCost} = \text{CrossingCost}_{\text{execution}} + \text{FeeCost}$$
$$\text{EV}_{\text{terminal}} = p_{\text{OOS}} - (\text{VWAP}_{\text{book}} + \text{FeeCost})$$

---

### 4. Deterministic Timestamp Logging & Clock Uncertainty Tiers
* **Source Timestamp Field**: The shock detector logs strictly from Binance WebSocket field `T` (`transaction_time`) for 100ms aggregation, distinguishing it from `E` (`event_time`).
* **Clock Uncertainty Tiers**:
  * $\Delta t \le \pm 50\text{ ms}$: **Exploratory** (within measurement uncertainty).
  * $\pm 50\text{ ms} < \Delta t \le \pm 100\text{ ms}$: **Provisional**.
  * $|\Delta t| \ge 250\text{ ms}$: **Identifiable**.

---

### 5. Econometric Inference: Wild Cluster Bootstrap
Because the historical sample consists of approximately 20 finalized market hours, asymptotic cluster-robust standard errors can be sensitive to small cluster counts. Regression inference across Models A through D implements a **Wild Cluster Bootstrap** clustered at the market-hour level, while impulse-response curves maintain the **shock-episode block bootstrap**.

---

### 6. Explicit Out-of-Sample Freeze Boundary
* **`R3_DEV`**: Everything observed prior to **`2026-09-29T18:11:34.000Z`** (commit [`08d50e8`](https://github.com/skybullet1987/quant_pipeline/commit/08d50e8)). The 7 settled trades (6W / 1L, +$113.44 PnL) are classified strictly as **internal development calibration data**.
* **`R3_VALIDATION_START_UTC = 2026-09-29T18:11:34.000Z`**: Begins the clean, frozen forward out-of-sample ledger.

---

### 7. Executable Depth Ratio Guard ($K_{\text{depth}} \ge 1.50$)
The arbitrary $\$50.00$ dollar threshold is upgraded to an **Executable Depth Ratio**:
$$\text{DepthRatio} = \frac{D_{\text{executable}}(P_{\text{eff}} \le 0.85)}{C_{\text{ticket}}} \ge K_{\text{depth}} \quad (K_{\text{depth}} = 1.50)$$
Requiring at least $\$75.00$ in resting executable depth inside the price boundary for a $\$50.00$ ticket.

---

## Section 5: Permanent Decommissioning & Archival of Track 1 (Derive Options)

### 1. Forensic Falsification Autopsy
The real-time telemetry across three separate empirical probes confirmed that decentralized options CLOBs cannot support terminal 0DTE algorithmic execution:
1. **Day 1 Probe (Sep 28 07:00 UTC)**: Quoted depth within $\pm\$1,000$ of spot was $\$21,800$ ($<\$25,000$ hurdle). MM bid continuity was $33.3\%$ ($<70\%$ hurdle).
2. **Day 2 Probe (Sep 29 07:00 UTC)**: Quoted depth was $\$21,800$ ($<\$25,000$ hurdle). MM bid continuity was $33.3\%$ ($<70\%$ hurdle).
3. **Real-Time BTC Probe (Sep 29 17:31 UTC)**: Quoted depth within $\pm\$1,000$ of spot dropped to **$\$8,857.31$** ($<\$25,000$ hurdle). Market makers pulled bids ($0.00 bid) on all near-the-money terminal strikes.

### 2. Decommissioning & Archival Execution
* Terminated background processes (`kill -9 770000`).
* Closed WebSocket and REST polling sockets.
* Archived raw telemetry into `data/archive/derive_experiment_d_falsified_20260929.tar.gz`.
* Wrote permanent tombstone manifest `data/archive/EXPERIMENT_D_FALSIFIED.json`.
* **Capital Allocation**: Permanently set to **$\$0.00$**.

---

## Section 6: Autonomous Milestones & Chronological Production Schedule

| Checkpoint (UTC) | Horizon | Target Module | Objective & Metric to Inspect |
| :--- | :--- | :--- | :--- |
| **2026-09-29 19:00:00 UTC** | ~10 min | Engine 3 (Polymarket) | 1-Hour contract resolution (2PM ET candle close against Binance Spot). |
| **2026-09-29 20:00:14 UTC** | ~1.2 hrs | Engine 1 (EXP-103 Apex) | **Bar 8 of 18 Micro Risk Audit**: Reconcile NAV ($620.51), ETH 10x carry (+>$3.13), and stop buffer. |
| **2026-09-29 23:15:00 UTC** | ~4.5 hrs | Engine 3 (Polymarket) | **First Full 24-Hour Paper Ledger Report**: 24 consecutive contracts, net PnL, fee drag, Brier score. |
| **2026-09-30 08:00:00 UTC** | ~13.25 hrs | Engine 1 (EXP-103 Apex) | Bar 11 of 18 Micro Risk Audit. |
| **2026-10-01 12:00:00 UTC** | ~41.25 hrs | **Core Macro Rebalance** | **Bar 18 of 18 Macro Cycle & EXP-104 Measurement Checkpoint**: Redeploy $610+ cash into 16-asset basket, test paired 240s vs. 180s ALO window, and record 60H baseline comparison for EXP-104. |
