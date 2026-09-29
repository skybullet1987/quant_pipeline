# Asymmetric Convexity Validation & Compounding Plan: Tri-Engine Blueprint (v3.0 Forensic Institutional State)

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

### 2. Current Operational State (v3.0 Sovereign Alignment)

| Pipeline Track | Current Lifecycle State | Operational Mandate & Running Status |
| :--- | :--- | :--- |
| **Engine 1 (EXP-103 Apex)** | **STAGE 6: PRODUCTION ALLOCATION** | **Frozen Core Daemon** ([`production_apex_daemon.py`](file:///home/skybullet1987/quant_pipeline/src/execution/production_apex_daemon.py), PID `16797`). NAV: **$620.51 USDC**, Cash: **$610.92 USDC**, Peak HWM: **$642.10 USDC**. Holding 1 ETH 10x position (+$3.13 funding carry earned). Bar 7/18 complete; Bar 8/18 audit at **20:00:14 UTC**. |
| **Engine 1 Shadow (EXP-104)** | **STAGE 1: DEVELOPMENT (Shadow)** | Shadow Daemon ([`src/execution/exp104_macro_hedge_shadow.py`](file:///home/skybullet1987/quant_pipeline/src/execution/exp104_macro_hedge_shadow.py), PID `2851516`). Logging 60s comparative forward equity against EXP-103; designated strictly as a **performance measurement checkpoint** on October 1 (minimum 30-day forward window required before live consideration). |
| **Engine 2 (HL Ratchet)** | **STAGE 2: FROZEN VALIDATION** | Shadow Daemon ([`src/hl_leadlag/execution/hl_isolated_ratchet_shadow.py`](file:///home/skybullet1987/quant_pipeline/src/hl_leadlag/execution/hl_isolated_ratchet_shadow.py), PID `2894894`). Phase B1 engineering screen across 4 assets (`SOL`, `HYPE`, `SUI`, `DOGE`) with dynamic OFI routing, +0.70% Net-BE lock, and per-asset slippage logging. |
| **Engine 3 (Polymarket Lab)** | **STAGE 1: DEVELOPMENT (Data Lab)** | Recorder ([`src/polymarket_research/polymarket_terminal_recorder.py`](file:///home/skybullet1987/quant_pipeline/src/polymarket_research/polymarket_terminal_recorder.py), PID `2037196`) & Paper Trader ([`src/polymarket_research/polymarket_paper_trader.py`](file:///home/skybullet1987/quant_pipeline/src/polymarket_research/polymarket_paper_trader.py), PID `2894914`). 7 settled trades: **6 Wins / 1 Loss (85.71% WR)**, **+$113.44 net PnL**, **$1,113.44 paper equity**. |
| **Track 1 (Derive Options)** | **PERMANENTLY TERMINATED & ARCHIVED** | Falsified at Gate 1 (depth <$9k, MM bids $0.00). Sockets closed, background processes killed, data archived to `data/archive/derive_experiment_d_falsified_20260929.tar.gz`. |

```
========================================================================================================
                     TRI-ENGINE SOVEREIGN PRODUCTION PIPELINE (v3.0)
========================================================================================================
[ENGINE 1: CORE COMPOUNDING PERPETUAL] ──> 85% Capital Allocation ($620.51 NAV, $610.92 Cash)
  ├── Live Daemon : production_apex_daemon.py (PID 16797, systemd active, 0-Mutation Invariant)
  ├── Micro Cycle : Bar 7/18 Complete -> Bar 8/18 at 20:00:14 UTC (4H Micro Risk Audit)
  ├── Macro Cycle : Bar 18/18 at 2026-10-01 12:00:00 UTC (72H Macro Rebalance, 240s ALO Window)
  └── Shadow Engine: exp104_macro_hedge_shadow.py (PID 2851516, Dynamic Ratchet Floor $577.89)

[ENGINE 2: ROUTE 2 HL RATCHET MOMENTUM] ──> Isolated Subaccount ($20-$50 Sandbox)
  ├── Shadow Daemon : hl_isolated_ratchet_shadow.py (PID 2894894, Stage 2 Frozen Validation)
  ├── Asset Universe: SOL (20x), HYPE (10x), SUI (10x), DOGE (10x)
  ├── Order Flow    : Binance USD-M aggTrade (>= $1.5M/100ms) + Tokyo Hyperliquid L2 WebSocket
  └── Enhancements  : Counterfactual Policy Benchmarking, Dynamic OFI Routing, +0.70% Early Net-BE Lock

[ENGINE 3: ROUTE 3 POLYMARKET DATA LAB] ──> Read-Only Paper Sandbox ($1,000 Paper NAV)
  ├── Paper Trader : polymarket_paper_trader.py (PID 2894914, Late-Candle TTE <= 15m Sweet Spot)
  ├── Data Recorder: polymarket_terminal_recorder.py (PID 2037196, Dual-Feed Telemetry Antenna)
  └── Live Ledger  : 7 Settled Trades | 6 Wins / 1 Loss (85.71% WR) | +$113.44 PnL ($1,113.44 Equity)

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

> **Codified Policy**: The nominal $\$7.80$ estimate is permanently retired. The series bankroll is locked at **$C_{\text{series}} = \$60.00$**, leaving an operational cash buffer of **$+\$0.70$** above the theoretical six-run requirement of $\$59.30$.

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

### 1. 4-Asset Multi-Tier Leverage Architecture
The candidate universe spans 4 high-beta altcoins with tier-specific protocol constraints:
* **SOL ($20\times$)**: $N_1 = \$400.00$, $N_2 = \$100.00$ ($5.0\%$ IMR, $2.5\%$ MMR). Stop-to-liquidation buffer: $0.72\%$.
* **HYPE ($10\times$)**: $N_1 = \$200.00$, $N_2 = \$50.00$ ($10.0\%$ IMR, $5.0\%$ MMR). Stop-to-liquidation buffer: $3.42\%$.
* **SUI ($10\times$)**: $N_1 = \$200.00$, $N_2 = \$50.00$ ($10.0\%$ IMR, $5.0\%$ MMR). Stop-to-liquidation buffer: $3.42\%$.
* **DOGE ($10\times$)**: $N_1 = \$200.00$, $N_2 = \$50.00$ ($10.0\%$ IMR, $5.0\%$ MMR). Stop-to-liquidation buffer: $3.42\%$.

#### Liquidation Gap Verification on 10x Tiers:
At $10\times$ leverage with $C = \$20.00$ and $N_1 = \$200.00$:
$$\text{Maintenance Margin Required} = \$200.00 \times 5.0\% = \$10.00$$
$$\text{Margin Available} = \$19.91 - \$10.00 = \$9.91$$
$$P_{\text{liq}} = P_0 \cdot \left[ 1 - \frac{9.91 / 200}{0.95} \right] \approx 0.9478 P_0 \ (-5.22\%)$$
With the hard stop placed at $-1.80\%$, the stop-to-liquidation buffer expands to:
$$d_{\text{stop}\to\text{liq}} = |-5.22\%| - 1.80\% = \mathbf{3.42\% \text{ of spot}}$$
This buffer is more than four times wider than SOL's $0.72\%$ buffer, providing strong protection against Hyperliquid's protocol liquidation fees during fast wicks.

---

### 2. Counterfactual Policy Benchmarking (Eliminating Selection Bias)
Selecting $\max(\text{OBI}_{\text{SOL}}, \text{OBI}_{\text{HYPE}}, \text{OBI}_{\text{SUI}}, \text{OBI}_{\text{DOGE}})$ creates an inherent winner's selection bias. To prove that dynamic routing generates true incremental alpha rather than mechanical selection skew, the shadow engine evaluates **four concurrent routing policies** on every qualifying shock episode:

| Policy Identifier | Policy Description | Scientific Purpose |
| :--- | :--- | :--- |
| **Policy 1: SOL-Only** | Always dispatches to SOL regardless of other books | Primary pre-specified baseline asset |
| **Policy 2: Random Eligible** | Dispatches to a randomly selected asset among the 4 | Null hypothesis for asset selection |
| **Policy 3: Round-Robin** | Cycles deterministically across SOL $\to$ HYPE $\to$ SUI $\to$ DOGE | Exposure-control baseline |
| **Policy 4: Max-OBI Router** | Dispatches to the highest positive $\text{OBI}_{\text{top}}$ | Candidate active strategy |

> **Certification Rule**: The routing hypothesis is supported if and only if:
> $$\mathbb{E}[R_{\text{Max-OBI}}] - \mathbb{E}[R_{\text{SOL}}] > 0 \quad \text{and} \quad \mathbb{E}[R_{\text{Max-OBI}}] - \mathbb{E}[R_{\text{Random}}] > 0 \quad (p < 0.01)$$

---

### 3. Descriptive Terminology Standardization
* The term "institutional sweep" is replaced with **"high-value aggressive-flow episode"** or **"large BTC sweep"**.
* $Z_{\text{OFI}} \ge 2.58$ is designated strictly as a **pre-registered parameter threshold**, not an assumption of Gaussian tail significance.

---

### 4. Sample Size & The Frozen B1 $\to$ B2 Boundary
* **Phase B1 (Feasibility / Engineering Screen)**: 30 to 50 raw shock events. Its purpose is plumbing verification: API stability, latency timestamps, state-machine transitions, and zero accounting leakage.
* **Phase B2 (Statistical Alpha Certification)**: Requires $\ge 100$ independent shock episodes across a minimum of 14 distinct UTC trading days and multiple volatility regimes.
* **Immutable Timestamp Boundary**: All sprints observed prior to commit [`723db2c`](https://github.com/skybullet1987/quant_pipeline/commit/723db2c) (including the four exploratory runs that informed the +0.70% breakeven adjustment) are classified as development data. The Phase B2 certification dataset enforces:
  $$\text{Timestamp}_{\text{event}} \ge \text{B2\_START\_TIMESTAMP}$$
  No development-phase observation may enter the Phase B2 certification ledger.

---

### 5. Pre-Registered Singular Primary Endpoint
To eliminate data dredging across robustness permutations (25 bps, 40 bps, 60 bps, leverage ladders), the certification decision is anchored to a single frozen primary endpoint:
* **Asset**: SOL
* **Trigger**: Binance BTC sweep $\ge \$1.5\text{M} / 100\text{ms}$ with directional $Z_{\text{OFI}} \ge 2.58$.
* **Sizing**: $N_1 = \$400.00$ exactly, $N_2 = \$100.00$.
* **Cost Stress**: $C_{\text{friction}} = 25\text{ bps}$ exactly.
* **Hurdle**: $\text{LCB}_{95\%, \text{cluster}}(\mathbb{E}[R_{\text{net}}]) > 0$ and $p_{\text{placebo}} < 0.01$.
* **Rule**: If this singular primary endpoint fails, Phase C deployment is aborted. Positive results on secondary robustness checks cannot override a primary failure.

---

### 6. Leverage Invariance: Gross vs. Net Execution
Reports two distinct metrics across leverage tiers ($1\times, 2\times, 5\times, 10\times, 20\times$):
* **$R_{\text{bps}}^{\text{gross}}$**: Price displacement of the underlying asset (verifying signal invariance).
* **$R_{\text{bps}}^{\text{net\_execution}}$**: Net return after accounting for tier-specific margin utilization, liquidation proximity, and execution drag.

---

### 7. Empirical Liquidation Safety
Rather than relying solely on the theoretical $0.72\%$ stop-to-liquidation buffer, the shadow engine logs:
$$\text{Buffer}_{\text{empirical}} = P_{05}\left(d(P_{\text{stop\_fill}}, \ P_{\text{liq}})\right)$$
This measures the realized 5th-percentile worst-case distance between the actual fill price of the stop-loss and the account's liquidation threshold under live book conditions.

---

### 8. Hard Machine-Enforced Loss Budget Guard
A fifth invariant is added to the pre-trade validation gate:
$$B_{\text{remaining}} = C_{\text{series}} - \sum \text{Loss}_{\text{realized}} - \text{Loss}_{\text{P95, new}}$$
The execution gateway rejects order generation if $B_{\text{remaining}} \le 0$, making the capital-preservation ceiling a programmatic invariant rather than an operational guideline.

---

## Section 3: Engine 1 Governance & Execution Optimization (EXP-103 & EXP-104)

### 1. Capital Carrying Value & Safety
* **Current Core NAV**: **$620.51 USDC** ($610.92 cash balance earning baseline margin safety).
* **Drawdown**: $-3.36\%$ from peak HWM ($642.10 USDC), well inside the Grossman-Zhou cushion ($0.8255$).
* **Positive Carry**: Single active 10x ETH position has accumulated **+$3.13 in net funding carry**.

---

### 2. October 1 Milestone: Measurement Checkpoint Only
The 60-hour pre-rebalance shadow window of EXP-104 (representing approximately 15 4-hour macro bars) is recognized as statistically insufficient to authorize production modifications.

> **Governance Rule**: October 1 is designated strictly as a **performance measurement checkpoint**, not a promotion gate. EXP-104 will continue logging forward performance in shadow mode across a **minimum 30-day evaluation window** before any live parameter promotion is considered.

---

### 3. ALO Window Optimization: Net Execution Cost Function
Expanding the Post-Only (ALO) window from 180 seconds to 240 seconds must not be evaluated on maker fill ratio alone. The optimization is evaluated against total net execution cost:

$$\text{Cost}_{\text{net}} = \text{Fees} + \text{Slippage} + \text{AdverseSelection} + \text{OpportunityCost}$$

where $\text{OpportunityCost}$ captures price drift on orders that fail to fill within the 240-second window. The 240-second configuration will be adopted only if:
$$\text{Cost}_{\text{net}}(240\text{s}) < \text{Cost}_{\text{net}}(180\text{s})$$
across identical forward rebalance observations.

---

## Section 4: Engine 3 (Polymarket Data Lab): Econometrics, Information Flow, and Cost Decoupling

### 1. Evidence Realism & Primary Evaluation Metrics
The initial 15-contract paper ledger (9W / 6L, 60.0% win rate) represents an early engineering sanity check (95% Wilson score interval: 35.7% to 80.2%). Win rate is retired as the primary evaluation metric and replaced with:
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

### 4. Clock Uncertainty & Terminology Standardization
Lead-lag observations relative to the Cristian's algorithm calibration ($\widehat{\text{Offset}} = -17.62\text{ ms} \pm 21.59\text{ ms}$) are categorized by confidence tier:
* $\Delta t \le \pm 50\text{ ms}$: **Exploratory** (within measurement uncertainty).
* $\pm 50\text{ ms} < \Delta t \le \pm 100\text{ ms}$: **Provisional**.
* $|\Delta t| \ge 250\text{ ms}$: **Identifiable**.

Binance timestamps are labeled strictly by their API field names: `event_time` ($E$) and `transaction_time` ($T$), avoiding premature claims of "matching engine event time."

---

### 5. Econometric Inference: Wild Cluster Bootstrap
Because the historical sample consists of approximately 20 finalized market hours, asymptotic cluster-robust standard errors can be sensitive to small cluster counts. Regression inference across Models A through D implements a **Wild Cluster Bootstrap** clustered at the market-hour level, while impulse-response curves maintain the **shock-episode block bootstrap**.

---

### 6. Scientific Framing
The relationship between Binance Futures and Polymarket hourly markets is classified strictly as **incremental predictive information** ($\beta_{F|S} \ne 0$), avoiding unverified claims of physical causality.

---

### 7. Late-Candle Sweet Spot & Operational Guards
* **Filter Rule**: $\text{TTE} \le 15\text{ minutes}$ (eliminating early-hour mean-reverting noise).
* **Noise Whipsaw Buffer**: Minimum distance buffer $|\text{dist}| \ge 0.05\%$ from candle open to prevent whipsaw losses near the open.
* **Book Depth Assertion**: Resting depth must have at least $\$50.00$ cumulative notional before generating an entry ticket.
* **Current Forward Ledger**: 7 Settled Contracts | **6 Wins / 1 Loss (85.71% WR)** | **+$113.44 Net Realized PnL** | **$1,113.44 Paper Equity** | **$5.27 Taker Fees Paid**.

---

## Section 5: Permanent Decommissioning & Archival of Track 1 (Derive Options)

### 1. Forensic Falsification Autopsy
The real-time telemetry across three separate empirical probes confirmed that decentralized options CLOBs cannot support terminal 0DTE algorithmic execution:
1. **Day 1 Probe (Sep 28 07:00 UTC)**: Quoted depth within $\pm\$1,000$ of spot was $\$21,800$ ($<\$25,000$ hurdle). MM bid continuity was $33.3\%$ ($<70\%$ hurdle).
2. **Day 2 Probe (Sep 29 07:00 UTC)**: Quoted depth was $\$21,800$ ($<\$25,000$ hurdle). MM bid continuity was $33.3\%$ ($<70\%$ hurdle).
3. **Real-Time BTC Probe (Sep 29 17:31 UTC)**: Quoted depth within $\pm\$1,000$ of spot dropped to **$\$8,857.31$** ($<\$25,000$ hurdle). Market makers pulled bids ($0.00 bid) on all near-the-money terminal strikes.

### 2. Microstructure Mechanisms
* **Adverse Selection on L2 Rollups**: Market makers cannot hedge dynamic gamma without sequencer latency and bridge risk.
* **Pin-Risk Quote Defense**: In the final $1$ to $4$ hours before settlement ($T < 4\text{h}$), extreme delta swings force rational market makers to withdraw bids to $\$0.00$ and blow spreads out to $999\%$.
* **Execution Spread Tax**: Crossing an $18\%$ to $50\%$ spread tax creates an insurmountable negative expected value hurdle.

### 3. Decommissioning & Archival Execution
* Terminated background processes (`kill -9 770000`).
* Closed WebSocket and REST polling sockets.
* Archived raw telemetry into `data/archive/derive_experiment_d_falsified_20260929.tar.gz`.
* Wrote permanent tombstone manifest `data/archive/EXPERIMENT_D_FALSIFIED.json`.
* **Capital Allocation**: Permanently set to **$\$0.00$**.

---

## Section 6: Autonomous Milestones & Chronological Production Schedule

| Checkpoint (UTC) | Horizon | Target Module | Objective & Metric to Inspect |
| :--- | :--- | :--- | :--- |
| **2026-09-29 19:00:00 UTC** | ~25 min | Engine 3 (Polymarket) | 1-Hour contract resolution (2PM ET candle close against Binance Spot). |
| **2026-09-29 20:00:14 UTC** | ~1.5 hrs | Engine 1 (EXP-103 Apex) | **Bar 8 of 18 Micro Risk Audit**: Reconcile NAV ($620.51), ETH 10x carry (+>$3.13), and stop buffer. |
| **2026-09-29 23:15:00 UTC** | ~4.75 hrs | Engine 3 (Polymarket) | **First Full 24-Hour Paper Ledger Report**: 24 consecutive contracts, net PnL, fee drag, Brier score. |
| **2026-09-30 08:00:00 UTC** | ~13.5 hrs | Engine 1 (EXP-103 Apex) | Bar 11 of 18 Micro Risk Audit. |
| **2026-10-01 12:00:00 UTC** | ~41.5 hrs | **Core Macro Rebalance** | **Bar 18 of 18 Macro Cycle & EXP-104 Measurement Checkpoint**: Redeploy $610+ cash into 16-asset basket, test 240s ALO window, and record 60H baseline comparison for EXP-104. |
