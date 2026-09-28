# Asymmetric Convexity Validation & Compounding Plan: Multi-Track Blueprint (v2.6 Forensic-Grade Specification Complete)

---

## Executive Status & Gate Classification

```
[PHASE A: Reconnaissance] ──> [PHASE B1: Engineering] ──> [PHASE B2: Alpha Gate] ──> [PHASE C: Micro-Canary]
    (Tonight: D2 & D3)           (Tomorrow: 30-50 setups)    (Frozen: Several Hundred)    (1 Active Sprint: $20-$60)
       [APPROVED]                      [APPROVED]                     [LOCKED]                   [LOCKED]
```

* **Core/Satellite Structural Separation**: Preserved and formalized. Core engine ([`production_apex_daemon.py`](file:///home/skybullet1987/quant_pipeline/src/execution/production_apex_daemon.py), $\$642.10\text{ USDC NAV}$) remains strictly unmutated.
* **Accounting Model**: Strictly canonical fill-level accounting. Realized PnL is separated from execution shortfall attribution; slippage is never double-counted.
* **Gate Hierarchy**:
  * **Phase A (Derive Options)**: **APPROVED** for *Market Microstructure Reconnaissance* (04:00 and 07:00 UTC probes).
  * **Phase B1 (Hyperliquid Engineering Shadow)**: **APPROVED TO BUILD** using the corrected $N_1 = \$380–\$400 / N_2 = \$100$ architecture.
  * **Phase B2 (Pre-Registered Block Alpha Certification)**: **LOCKED** pending B1 pass.
  * **Phase C (Live Micro-Canary)**: **LOCKED** pending B2 certification.

---

## Section 1: Canonical Accounting Model & Invariants

### 1. Separation of Realized PnL from Execution Shortfall
To eliminate double-counting of slippage, the accounting engine strictly decouples economic cash flow from execution-quality attribution:

#### A. Canonical Realized PnL (Cash-Flow Ledger)
For a long position composed of matched entry and exit fills:
$$\text{PnL}_{\text{realized}} = \sum_{j \in \text{matched}} Q_j \cdot (P_{\text{exit}, j} - P_{\text{entry}, j}) - \sum_k \text{Fees}_k - \sum_m \text{Funding}_m$$
where:
* $P_{\text{entry}, j}$ and $P_{\text{exit}, j}$ are the **actual executed fill prices** reported by the exchange. Execution slippage is already embedded in these prices.
* $\text{Fees}_k$ is the exact fee deducted by the exchange ($4.5\text{ bps}$ taker, $1.5\text{ bps}$ maker).
* $\text{Funding}_m$ is the net funding cash flow accrued across the position life (Hyperliquid periodic hourly rate: $0.00125\%$ interest component + premium component).

#### B. Execution Shortfall (Attribution Ledger)
Slippage is logged separately for econometric benchmarking:
$$\text{Shortfall}_k = Q_k \cdot (P_{\text{actual}, k} - P_{\text{benchmark}, k}) \quad (\text{signed positive for adverse slip})$$
where $P_{\text{benchmark}}$ is the top-of-book BBO price at decision timestamp $t_{\text{decision}}$.

---

### 2. Dimensionally Consistent Net Breakeven Equations
The strategy distinguishes between dollar breakeven price ($P_{\text{BE}}$) and percentage breakeven return ($r_{\text{BE}}$).

For a multi-fill long position with total filled quantity $Q_{\text{total}} = \sum_i Q_i$, Volume-Weighted Average Entry ($\text{VWAE}$), and estimated future exit costs $C_{\text{exit}}$ (exit taker fee + expected adverse exit slippage):

$$P_{\text{gross\_BE}} = \text{VWAE} = \frac{\sum_i Q_i \cdot P_i}{Q_{\text{total}}}$$

$$P_{\text{expected\_BE}} = \text{VWAE} + \frac{\text{Fees}_{\text{past}} + \mathbb{E}[\text{Fee}_{\text{exit}}] + \mathbb{E}[\text{Slippage}_{\text{exit}}] + \mathbb{E}[\text{Funding}]}{Q_{\text{total}}}$$

$$P_{\text{P95\_BE}} = \text{VWAE} + \frac{\text{Fees}_{\text{past}} + \text{Fee}_{\text{exit}} + \text{Slippage}_{\text{P95}} + \text{Funding}}{Q_{\text{total}}}$$

$$r_{\text{net\_BE}} = \frac{P_{\text{expected\_BE}}}{P_0} - 1$$

---

### 3. Hyperliquid Documented Cross-Margin Liquidation Formula
The static approximation ($2.5\% - 1.8\% = 0.70\%$) is strictly replaced with Hyperliquid's published cross-margin liquidation formula:

$$P_{\text{liq}} = P_{\text{entry}} - \text{side} \cdot \frac{\text{Margin Available}}{Q_{\text{total}}} \cdot \frac{1}{1 - l \cdot \text{side}}$$

where:
* $\text{Margin Available} = \text{Account Value} - \text{Total Maintenance Margin Required}$
* $l$ is the tier maintenance margin rate ($0.025 = 2.5\%$ for SOL $20\times$).
* For a long position ($\text{side} = +1$):
  $$P_{\text{liq}} = P_0 \cdot \left[ 1 - \frac{\text{Margin Available} / N_{\text{total}}}{1 - l} \right]$$

#### Numerical Validation on $C = \$20.00 / N_1 = \$400.00$ SOL Setup:
* $\text{Fee}_{\text{entry}} = \$400.00 \times 0.045\% = \$0.18 \implies \text{Account Value} = \$19.82$.
* $\text{Maintenance Margin Required} = \$400.00 \times 2.5\% = \$10.00$.
* $\text{Margin Available} = \$19.82 - \$10.00 = \$9.82$.
* Normalizing entry $P_0 = 1$:
  $$P_{\text{liq}} = 1 - \frac{9.82 / 400}{0.975} = 1 - \frac{0.02455}{0.975} \approx \mathbf{0.97482 P_0 \ (-2.52\%)}$$
* **Stop-to-Liquidation Buffer**:
  $$d_{\text{stop}\to\text{liq}} = |-2.52\%| - 1.80\% = \mathbf{0.72\% \text{ buffer from stop}}$$

> **Multi-Fill Invariant**: After the $+1.50\%$ pyramid, the liquidation price must immediately be re-evaluated using the aggregate position quantity $Q_{\text{total}}$, updated account equity, and aggregate maintenance margin.

---

### 4. Mandatory Position Transition Invariant
> **Machine-Enforced Rule**: Every fill that alters position size $Q$ (initial fill, partial fill, pyramid fill) synchronously recomputes:
> 1. $\text{VWAE}$ and total position notional $N_{\text{total}}$
> 2. Account equity and free usable margin
> 3. Dynamic liquidation price $P_{\text{liq}}$ and distance $d_{\text{stop}\to\text{liq}}$
> 4. Gross breakeven price $P_{\text{gross\_BE}}$, expected net breakeven $P_{\text{expected\_BE}}$, and P95 net breakeven $P_{\text{P95\_BE}}$
> 5. Modeled maximum dollar loss $L_{\text{modeled}}$ under stop execution

---

## Section 2: Route 2 — Ratcheted Event Momentum Specification

### 1. Leverage Reality & Operational Headroom

#### Hyperliquid Protocol Constraints
* **SOL**: Max $20\times$ leverage ($5.0\%$ initial margin requirement, $2.5\%$ maintenance margin rate).
* **HYPE**: Max $10\times$ leverage ($10.0\%$ initial margin, $5.0\%$ maintenance margin).
* **BTC**: Max $40\times$ leverage ($2.5\%$ initial margin, $1.25\%$ maintenance margin).

#### All-In Sizing Equation Including Frictions
To ensure dollar risk targets reflect true net execution:
$$N_1 = \min \left( \frac{L_{\text{target}}}{d_{\text{stop}} + c_{\text{all-in}}}, \ C_{\text{available}} \cdot \text{Leverage}_{\max} \right)$$
where $c_{\text{all-in}} = d_{\text{slip}} + d_{\text{entry\_fee}} + d_{\text{exit\_fee}} + d_{\text{funding}}$.
* For $d_{\text{stop}} = 180\text{ bps}$, $d_{\text{slip}} = 7\text{ bps}$, $d_{\text{fees}} = 9\text{ bps}$, $d_{\text{funding}} = 0.5\text{ bps} \implies c_{\text{all-in}} = 16.5\text{ bps}$:
  $$N_1 = \min \left( \frac{18.00}{0.0180 + 0.00165}, \ 50 \times 20 \right) = \min(\$916.03, \ \$1,000.00) = \mathbf{\$916.03 \text{ notional}}$$

#### Operational Margin Headroom ($N_1 = \$380.00–\$400.00$):
* Operating at $100\%$ margin utilization ($N_1 = \$400$ on $C = \$20$) is a theoretical boundary that risks exchange margin rejection (`perpMarginRejected` / `marginCanceled`) after the $\$0.18$ entry fee.
* **Canary Recommendation**:
  * **Simulation Boundary**: $N_1 = \$400.00$ (consumed margin: $\$20.00$).
  * **Live Canary Headroom**: $N_1 = \$380.00$ (consumed margin: $\$19.00$, leaving $\$1.00$ free margin buffer).

---

### 2. Sizing Model ($N_1 = \$400 / N_2 = \$100$)

```
[COLLATERAL: $20.00 USDC] ──> Initial Entry: N1 = $400.00 Notional (20x Leverage)
                               ├── Initial Taker Fee: $400 * 0.045% = $0.18
                               └── Nominal Stop: -1.80% (Loss: -$7.20)
                                            │
                                            ▼ (Spot advances +1.50%)
                               Unrealized PnL: +$6.00
                               Account Equity: $20.00 - $0.18 + $6.00 = $25.82
                               Marked Notional: $400 * 1.015 = $406.00
                               Initial Margin Held (5%): $20.30
                               Free Usable Margin: $25.82 - $20.30 = $5.52
                               Theoretical Max Add (20x): $110.40 (less fee = $109.40)
                                            │
                                            ▼
                               [CONSERVATIVE B1 PYRAMID CAP]
                               Secondary Pyramid Size: N2 = $100.00 Notional
                               Pyramid Initial Margin (5%): $5.00 | Taker Fee: $0.045
                               Total Position: N_total = $500.00 Notional
                               Residual Free-Margin Buffer: $5.52 - $5.00 - $0.045 = $0.475
```

#### Exact Causal VWAE after Pyramid:
$$\text{VWAE} = \frac{400(0.0\%) + 100(+1.50\%)}{500} = \mathbf{+0.300\%}$$

* If price pulls back to original entry ($0.0\%$):
  $$\text{PnL}_{\text{gross}}(0.0\%) = 400(0.0\%) + 100(0.0\% - 1.50\%) = 0 - \$1.50 = \mathbf{-\$1.50 \text{ (Gross Loss)}}$$
* Therefore, the **Gross Breakeven Stop** is placed at **$+0.300\%$**.
* The **Expected Net Breakeven Stop** sits at:
  $$P_{\text{net\_BE}} = +0.300\% + 0.090\% = \mathbf{+0.390\%}$$

#### Profit Lock at $+3.50\%$ Spot Move:
$$\text{PnL}_{\text{gross}}(+3.50\%) = 400(+3.50\%) + 100(+3.50\% - 1.50\%) = \$14.00 + \$2.00 = \mathbf{+\$16.00}$$
Moving the stop to lock profit at $+1.80\%$ above initial entry:
$$\text{PnL}_{\text{locked\_gross}} = 400(+1.80\%) + 100(+1.80\% - 1.50\%) = \$7.20 + \$0.30 = \mathbf{+\$7.50}$$

---

### 3. Stop Execution Telemetry Invariant
Rather than assuming deterministic fills, the shadow engine records:
* $P(\text{full fill} \mid \text{trigger})$
* $P(\text{partial fill} \mid \text{trigger})$
* $P(\text{no fill / gap} \mid \text{trigger})$
* $\mathbb{E}[\text{slippage} \mid \text{trigger}]$ and P95/P99 slippage.

---

### 4. Single-Sprint Concurrency & Subaccount Sandbox Isolation

* **Single-Sprint Invariant**: `MAX_CONCURRENT_SPRINTS = 1`. Multiple concurrent sprints are strictly prohibited inside the same cross-margin subaccount to prevent cross-position collateral contagion.
* **Sandbox Modes**:
  1. **Native Subaccount Sandbox**: Account/margin isolation under master authority (requires $\$100,000$ historical volume).
  2. **Independent Wallet Sandbox**: Complete cryptographic key firewall (separate EVM address).
* **Transfer & NAV Accounting**:
  Transferring capital from master to satellite explicitly updates core NAV:
  $$\text{NAV}_{\text{core}} = C_{\text{master}} - C_{\text{satellite}} = \$642.10 - \$20.00 = \mathbf{\$622.10}$$
  $$\text{NAV}_{\text{satellite}} = \mathbf{\$20.00}$$
  $$\text{NAV}_{\text{combined}} = \text{NAV}_{\text{core}} + \text{NAV}_{\text{satellite}} = \mathbf{\$642.10}$$

---

### 5. Multi-Level Bankroll Survival Reality
1. **One-Sprint Survival**: An initial $\$20.00$ sandbox allocation supports **ONE full-size $\$400$ sprint**. After one $-\$7.80$ loss, the remaining $\$12.20$ cannot reopen another $\$400$ position (which requires $\$20.00$ initial margin) without replenishment.
2. **Satellite-Series Bankroll**:
   * A $\$50.00$ series bankroll supports **FOUR consecutive full-size $\$400$ attempts** ($50 - 4 \times 7.80 = \$18.80$, below the $\$20.00$ required for attempt #5).
   * To support **SIX consecutive full-size attempts**, the required minimum bankroll is:
     $$C_{\min} = \$20.00 + 5 \times \$7.80 = \mathbf{\$59.00 \text{ (before operational buffer)}}$$
   * Sizing policy: $C_{\text{series}} = \$60.00$ fixed, with zero replenishment until formal review.
3. **Combined-Account Stress Test**: 20 hypothetical modeled full-stop losses ($20 \times -\$7.80 = -\$156.00$) reduce combined NAV from $\$642.10$ to $\$486.10$, **assuming an external replenishment mechanism permits all 20 attempts**. Core NAV itself remains $\$622.10$ if no additional capital is transferred from Core.

---

## Section 3: Phase B Statistical Testing Protocol

### 1. Pre-Registered Primary B2 Endpoint & Frozen Outcome Function
To prevent multiple-testing data dredging, Phase B2 freezes **both the trigger and the full outcome function**:

> **Pre-Registered Primary Endpoint**:
> * **Asset**: SOL
> * **Trigger**: Binance Volume Sweep $\ge \$1.5\text{M}$ in $100\text{ms}$ with directional $Z_{\text{OFI}} \ge 2.58$.
> * **Initial Sizing**: $N_1 = \$400.00$ (or $\$380.00$ canary).
> * **Initial Stop**: Nominal $-1.80\%$ mark-triggered order.
> * **Pyramid Rule**: $+1.50\%$ spot move triggers $N_2 = \$100.00$ secondary fill.
> * **Breakeven Rule**: Stop updated to dynamic $P_{\text{net\_BE}} = \text{VWAE} + \text{costs}$.
> * **Profit Lock Rule**: $+3.50\%$ spot move locks $+1.80\%$ above entry.
> * **Trailing Rule**: $1.0\%$ dynamic trailing stop distance from HWM.
> * **Max Holding Horizon**: $45\text{ minutes}$ hard time exit.
> * **Cost Stress**: Evaluated under $\ge 25\text{ bps}$ round-trip execution friction.
> * **Primary Gate Hurdle**:
>   $$\mathbf{LCB_{95\%,\text{cluster}}\left(\mathbb{E}[R_{\text{net}}]\right) > 0}$$
>   evaluated via cluster/block bootstrap resampling grouped at the shock episode/day level.

---

### 2. Paired Cluster/Block Permutation Test for Placebos
Every qualifying shock is paired with a counterfactual matched control:
* Matched on identical UTC hour bucket.
* Matched on rolling 1-hour BTC realized volatility ($\pm 10\%$).
* Matched on BTC volume percentile.
* Matched on SOL local volatility state.
* **Matched on BTC Trend State**: Directional trending (ADX $> 25$) vs. range-bound consolidation.
* **Statistical Test**:
  $$\text{Paired Cluster/Block Permutation Test: } \mathbb{E}[R_{\text{real shock}}] - \mathbb{E}[R_{\text{matched placebo}}] > 0 \quad (p < 0.01)$$

---

### 3. Dual Leverage-Invariance Tests
1. **Test A (Signal Invariance)**: Hold notional constant ($N = \$400$), vary leverage ($1\times, 2\times, 5\times, 10\times, 20\times$), measure return in basis points ($\mathbb{E}[R_{\text{bps}}]$). Confirms positive underlying edge prior to leverage scaling.
2. **Test B (Capital Efficiency)**: Allow leverage to scale notional per margin tiers, measure return on allocated margin ($\mathbb{E}[\text{PnL} / C]$).

---

### 4. High-Resolution Latency Telemetry
Every event records six distinct monotonic timestamps and derived execution intervals:
$$t_{\text{source}} \longrightarrow t_{\text{receive}} \longrightarrow t_{\text{decision}} \longrightarrow t_{\text{submit}} \longrightarrow t_{\text{ack}} \longrightarrow t_{\text{fill}}$$

* $\Delta t_{\text{marketable}} = t_{\text{fill}} - t_{\text{source}}$
* $\Delta t_{\text{decision}} = t_{\text{decision}} - t_{\text{source}}$
* $\Delta t_{\text{network}} = t_{\text{ack}} - t_{\text{submit}}$
* $\Delta t_{\text{matching}} = t_{\text{fill}} - t_{\text{ack}}$

---

## Section 4: Phase C — Machine-Enforced Pre-Trade Guards (Fail-Closed)

Before any live order payload can be generated or signed, the execution gateway runs synchronous, deterministic invariant checks:

```python
def verify_pre_trade_invariants(order: OrderRequest, context: AccountContext) -> bool:
    """
    Synchronous pre-trade gate.
    Behavior: FAIL-CLOSED. Any False condition aborts execution without retry.
    """
    if order.destination_address != EXPECTED_SANDBOX_ADDRESS:
        return False  # Master account physical firewall
    if context.sandbox_balance > HARD_COLLATERAL_CAP:
        return False  # Collateral breach
    if order.notional_usd > MAX_PERMISSIBLE_NOTIONAL:
        return False  # Sizing violation
    if order.asset not in ALLOWED_SPRINT_ASSETS:
        return False  # Unauthorized ticker
    if context.margin_mode != "CROSS":
        return False  # Margin configuration error
    if context.active_sprint_count >= 1:
        return False  # Single-sprint concurrency invariant
    return True
```

* **Rate-Limit Throttling**: Trailing stop updates are throttled to execute only when:
  $$\Delta P_{\text{HWM}} > 10\text{ bps} \quad \text{OR} \quad \Delta t > 1,000\text{ ms}$$
  preserving Hyperliquid address-based action-rate limits. Stop amendments per sprint are logged as part of B1 engineering telemetry.

---

## Section 5: Implementation Roadmap & Live Deployment State

```
[TRACK 1: CORE COMPOUNDING ENGINE (EXP-103)]
  ├── Status: ACTIVE & HEALTHY on Tokyo GCP (PID 16797, production_apex_daemon.py)
  ├── Equity: Started $559.31 -> Current $622.72 -> Peak HWM $642.10 (0.00% Leakage)
  ├── Micro Cycle: 4H Risk Audits (Next: Bar 3/18 at 00:00:14 UTC)
  └── Macro Cycle: 72H Macro Rebalance Bar 18/18 (Next: Oct 1, 12:00:00 UTC)

[TRACK 2: ROUTE 2 HYPERLIQUID RATCHET SHADOW (PHASE B1)]
  ├── Status: ACTIVE & HEALTHY on Tokyo GCP (PID 1998153, hl_isolated_ratchet_shadow.py)
  ├── Streams: Tokyo Binance Futures aggTrade (routed /market) + Hyperliquid L2 WebSocket (SOL, HYPE)
  ├── Accounting: Multi-Fill Canonical Ledger with Runtime VWAE and Dynamic Breakeven
  └── Target Sample: 30-50 institutional volatility shocks ($1.5M/100ms) for Phase B1 Pass

[TRACK 3: ROUTE 1 DERIVE 0DTE OPTIONS RECONNAISSANCE (PHASE A)]
  ├── Status: PROBES EXECUTED & AUDITED (04:00 & 07:00 UTC)
  ├── Finding: Severe liquidity withdrawal by MMs in final 1-4 hours (OTM bids $0.00, spreads 999%)
  └── Follow-up: Automated re-probe scheduled for Sep 29 04:00/07:00 UTC to confirm cross-session persistence

[TRACK 4: ROUTE 3 POLYMARKET 1-HOUR DUAL-FEED DATA LAB (PASSIVE READ-ONLY BENCHMARK)]
  ├── Status: ACTIVE & HEALTHY on Tokyo GCP (PID 1995992, polymarket_terminal_recorder.py v2.6)
  ├── Dual Feeds: Binance Spot (Settlement Ref) + Binance Futures (Routed /market Flow Antenna)
  ├── Invariants: OBI & q_micro Reconciled + Assertions Enforced + Book Consistency Checks
  ├── Quote Ages: Tripartite Decomposition (Age_book, Age_bid, Age_ask)
  ├── Real-Time Metrics: Basis_t0 (signed USD & bps), |Basis|, Delta_Basis_100ms, Cross-Correlation Grid
  ├── Causal Boundary: Strict t0 anchor at shock window end (predictors t <= t0, response t > t0)
  ├── Models: 4 Pre-Registered Econometric Models (A: Spot, B: Fut, C: Joint, D: Incremental H0: beta_{F|S}=0)
  ├── Capacity Surface: EV(C) across [$1, $5, $20, $50, $100]
  ├── Ground Truth: Binance Spot 1H Candle Finalized Open & Close (Y = 1[Close >= Open])
  └── Compliance: Read-Only (Does not attempt to circumvent geographic restrictions)
```

---

## Section 6: Route 3 — Futures/Spot $\to$ Polymarket Information-Flow Experiment (v2.6 Forensic Specification)

### 1. The Dual-Feed Information Transmission Hypothesis (Point 16 & Point 2)
Polymarket's hourly BTC market explicitly resolves against the finalized **Binance Spot BTC/USDT** 1-hour candle. However, aggressive institutional order flow and price discovery in crypto markets frequently originate in the **USDⓈ-M perpetual futures market**.

Rather than treating futures/spot basis as an error or baking in an unproven causal sequence, Route 3 structures this as an empirical **Information-Flow Experiment**:

$$\boxed{ \text{Hypothesis: } X^{\text{futures}}_t \longrightarrow X^{\text{spot}}_{t+\Delta} \longrightarrow q_{\text{Poly}, t+\Delta} \quad \text{vs.} \quad X^{\text{spot}}_t \longrightarrow q_{\text{Poly}, t+\Delta} }$$

#### Active Data Antennas
* **Binance Spot**: `wss://stream.binance.com:443/ws/btcusdt@aggTrade` (Polymarket settlement reference).
* **Binance Futures**: `wss://fstream.binance.com:443/market/ws/btcusdt@aggTrade` (Routed 2026 `/market` order flow antenna).
* **Polymarket CLOB WebSocket L2**: `wss://ws-subscriptions-clob.polymarket.com/ws/market` (Continuous binary probability book).

#### Pre-Registered Lead/Lag Cross-Correlation Grid (Point 2)
The daemon estimates the empirical cross-correlation between Futures flow $X_F(t)$ and Spot flow $X_S(t + \Delta)$:
$$\text{Corr}(X_F(t), X_S(t + \Delta)) \quad \text{and} \quad \text{Corr}(X_F(t), \Delta q(t + \Delta))$$
across the pre-registered millisecond lag grid:
$$\Delta \in \{-1000, -500, -250, -100, -50, 0, +50, +100, +250, +500, +1000\}\text{ ms}$$
Logged continuously to `data/polymarket/leadlag_cross_correlations.jsonl` to establish whether Futures lead Spot, Spot leads Futures, or flow is contemporaneous before making causal claims.

---

### 2. Multi-Clock Latency & Microsecond-Resolution Timestamps (Points 11 & 12)
To avoid conflating exchange matching latency, network transit, and local CPU scheduling, every observation stores five distinct clocks:
1. $t_{\text{binance\_event}}$ ($E$, Binance matching engine event timestamp in microsecond/millisecond units)
2. $t_{\text{binance\_trade}}$ ($T$, Binance trade execution timestamp)
3. $t_{\text{receive\_local}}$ (Tokyo GCP local monotonic nanosecond and unix timestamp)
4. $t_{\text{polymarket\_event}}$ (Polymarket CLOB message timestamp)
5. $t_{\text{receive\_polymarket}}$ (Tokyo GCP local receive timestamp of Polymarket L2 update)

This enables empirical decomposition of:
$$\Delta t_{\text{exchange}} = E - T, \quad \Delta t_{\text{network}} = t_{\text{receive\_local}} - E, \quad \Delta t_{\text{processing}} = t_{\text{record}} - t_{\text{receive\_local}}$$
*Standard Terminology*: Re-phrased as **microsecond-resolution timestamps** rather than proof of end-to-end causal precision.

---

### 3. Mathematical Reconciliation of OBI and Microprice (Point 1 & Point 13)

#### The Root Cause of the Snapshot Discrepancy
The previous apparent contradiction ($q_{\text{mid}} = 0.014$, $q_{\text{micro}} = 0.0117$, $\text{OBI} = +0.160$) arose from an aggregation mismatch:
* $q_{\text{micro}}$ was computed strictly at **Level 1** where ask size exceeded bid size ($Q_{\text{ask}, 1} = 62.89 \gg Q_{\text{bid}, 1} = 8.98$), pulling Level 1 microprice down toward the bid ($0.0117 < 0.014$).
* $\text{OBI}$ was summed across **Top 5 levels**, where deep bids at $0.010$ created net positive aggregate depth.

#### Reconciled Mathematical Formulation
Route 3 v2.6 explicitly decouples Level 1 OBI from Depth OBI:
$$\text{OBI}_{\text{L1}} = \frac{Q_{\text{bid}, 1} - Q_{\text{ask}, 1}}{Q_{\text{bid}, 1} + Q_{\text{ask}, 1}} \in [-1, +1]$$
$$q_{\text{micro}} = \frac{P_{\text{ask}, 1} \cdot Q_{\text{bid}, 1} + P_{\text{bid}, 1} \cdot Q_{\text{ask}, 1}}{Q_{\text{bid}, 1} + Q_{\text{ask}, 1}} = q_{\text{mid}} + \frac{1}{2}(P_{\text{ask}, 1} - P_{\text{bid}, 1}) \cdot \text{OBI}_{\text{L1}}$$
$$\text{OBI}_{\text{depth}} = \frac{\sum_{i=1}^5 Q_{\text{bid}, i} - \sum_{i=1}^5 Q_{\text{ask}, i}}{\sum_{i=1}^5 Q_{\text{bid}, i} + \sum_{i=1}^5 Q_{\text{ask}, i}}$$

#### Runtime Invariant Assertions
```python
# Exact mathematical invariant: sign(q_micro - q_mid) MUST match sign(OBI_L1)
if obi_l1 > 1e-4:
    assert q_micro >= q_mid - 1e-4, f"Violation: OBI_L1={obi_l1} > 0 but q_micro={q_micro} < q_mid={q_mid}"
elif obi_l1 < -1e-4:
    assert q_micro <= q_mid + 1e-4, f"Violation: OBI_L1={obi_l1} < 0 but q_micro={q_micro} > q_mid={q_mid}"
```

#### Order Book Consistency Invariants (Point 13)
* $P_{\text{best\_bid}} < P_{\text{best\_ask}}$ (strictly asserted on every clean L2 book state; transient crossed books explicitly flagged)
* Depth $Q_i \ge 0$ for all levels
* $q_{\text{mid}} = \frac{P_{\text{best\_bid}} + P_{\text{best\_ask}}}{2}$
* $\text{VWAP}(C) \ge P_{\text{best\_ask}}$ for any buy sweep

#### Mandatory Metadata Logged Per Observation
`obi_depth_levels = 5`, `microprice_formula`, `book_sequence_id`, `book_timestamp`.

---

### 4. Tripartite Quote Age Decomposition (Point 6)
To identify genuine stale executable quotes versus general depth churn, the quote age is decomposed into three distinct durations:
* $\text{Age}_{\text{book}} = t_{\text{obs}} - t_{\text{last\_l2\_message}}$ (Elapsed time since any L2 update: snapshot or depth amendment).
* $\text{Age}_{\text{bid}} = t_{\text{obs}} - t_{\text{last\_best\_bid\_change}}$ (Elapsed time since best bid price or size changed).
* $\text{Age}_{\text{ask}} = t_{\text{obs}} - t_{\text{last\_best\_ask\_change}}$ (Elapsed time since best ask price or size changed).

> **Microstructure Insight**: If $\text{Age}_{\text{book}} = 20\text{ms}$ while $\text{Age}_{\text{ask}} = 6,600\text{ms}$, liquidity providers are active in the book but have left a stale resting ask untouched for $6.6\text{s}$—the exact footprint of an exploitable stale quote.

---

### 5. Signed Basis & Delta Basis Decomposition (Point 5)
Every observation and shock event records:
* $\text{Basis}_{\text{signed\_usd}} = P^{\text{futures}}_t - P^{\text{spot}}_t$
* $\text{Basis}_{\text{signed\_bps}} = \frac{P^{\text{futures}}_t - P^{\text{spot}}_t}{P^{\text{spot}}_t} \times 10,000$
* $\text{Basis}_{\text{abs\_bps}} = |\text{Basis}_{\text{signed\_bps}}|$ (Magnitude)
* $\Delta \text{Basis}_{100\text{ms}} = \text{Basis}_t - \text{Basis}_{t - 100\text{ms}}$ (Signed basis velocity across the shock window)

---

### 6. Strict Causal Information Boundary ($t_0$ Anchor) (Point 3)
To prevent contemporaneous trade leakage into predictive features:
$$\boxed{ t_0 \equiv \text{exact timestamp at the end of the qualifying 100-ms shock window} }$$
* **Predictor Invariant**: Every feature $X_t$ (Spot volume, Futures volume, OFI, Basis, $\Delta \text{Basis}_{100\text{ms}}$, L2 metrics) must strictly satisfy:
  $$t_{\text{feature}} \le t_0$$
* **Response Invariant**: All impulse-response measurements $\Delta q(\Delta t)$ start strictly after $t_0 + \epsilon$:
  $$\Delta q(\Delta t) = q(t_0 + \Delta t) - q(t_0), \quad \Delta t \in \{100\text{ms}, 250\text{ms}, 500\text{ms}, 1\text{s}, 5\text{s}, 30\text{s}\}$$

---

### 7. Four Pre-Registered Econometric Models (Point 4)
Rather than simply showing Model C fits better, Route 3 pre-registers four nested models to test for incremental futures information:
* **Model A (Spot Baseline)**:
  $$Y = f(q_{\text{mid}, t_0}, X^{\text{spot}}_{t_0}, \text{TTE}, \text{dist}_{\text{open}})$$
* **Model B (Futures Baseline)**:
  $$Y = f(q_{\text{mid}, t_0}, X^{\text{futures}}_{t_0}, \text{TTE}, \text{dist}_{\text{open}})$$
* **Model C (Joint Lead/Lag Specification)**:
  $$Y = f(q_{\text{mid}, t_0}, X^{\text{spot}}_{t_0}, X^{\text{futures}}_{t_0}, \text{Basis}_{t_0}, \Delta \text{Basis}_{100\text{ms}}, \text{TTE}, \text{dist}_{\text{open}})$$
* **Model D (Futures Incremental Information Model)**:
  $$Y = f(q_{\text{mid}, t_0}, X^{\text{spot}}_{t_0}, \text{TTE}, \text{dist}_{\text{open}}) + g(X^{\text{futures}}_{t_0} \mid X^{\text{spot}}_{t_0})$$

$$\boxed{ \text{Primary Null Hypothesis: } H_0: \beta_{F|S} = 0 }$$
Testing whether Futures order flow provides statistically significant incremental predictive power after conditioning on Spot flow and existing Polymarket implied probability.

---

### 8. Dynamic Contract Fee Architecture (Point 8)
Polymarket's fee structure is dynamically queried from contract metadata rather than permanently hardcoded:
* **Metadata Fields Logged Per Market**:
  * `fee_rate_market`: Dynamically parsed from Gamma API `feeSchedule.rate` (currently $0.07 = 7.0\%$).
  * `fee_source`: Source identifier (`gamma_feeSchedule_crypto_fees_v2`).
  * `fee_enabled`: Boolean flag.
  * `fee_formula_version`: `crypto_fees_v2` ($C \times \text{feeRate} \times p(1 - p)$).
* **Makers Pay Zero**: Confirmed by `takerOnly: true`.

---

### 9. Strategy Dichotomy: Terminal Hold vs. Momentum Repricing (Point 9)
Two distinct economic strategies are separated in the analysis:
* **Strategy R3-A — Terminal Hold (Primary Scientific Experiment)**:
  $$\text{Buy}(q_t) \longrightarrow Y \in \{0, 1\}$$
  $$\text{EV}_{\text{terminal}} = p_{\text{model}} - q_{\text{ask}} - \text{Fee}(q_{\text{ask}})$$
  Single execution leg, held to Binance 1H candle settlement.
* **Strategy R3-B — Momentum Repricing Capture (Secondary Execution Study)**:
  $$\text{Buy}(q_t) \longrightarrow \text{Sell}(q_{t+\Delta t})$$
  $$\mathbb{E}[\text{PnL}_{\text{repricing}}] = \mathbb{E}[q_{\text{sell}} - q_{\text{buy}} - \text{Fee}_{\text{buy}} - \text{Fee}_{\text{sell}} - \text{Spread/Slippage}]$$
  Two execution legs and double taker fees.

---

### 10. Executable Capacity Surface (Point 7)
Order book sweeps are evaluated across multiple ticket sizes:
$$\text{EV}(C) = p - \text{VWAP}(C) - \text{Fee}(\text{VWAP}(C)) \quad \text{for } C \in \{\$1, \$5, \$20, \$50, \$100\}$$
> **Capacity Insight**: Finding positive EV at $\$1$ but negative EV at $\$50$ represents an empirical **capacity constraint**, not a failure of the predictive signal.

---

### 11. Finalized Candle Ground Truth Verification (Point 10)
Polymarket hourly contracts resolve strictly against the finalized open and close of the specified Binance Spot BTC/USDT 1-hour candle:
$$Y = \mathbf{1}[C_{\text{1H}} \ge O_{\text{1H}}]$$
At candle expiry ($T_{\text{expiry}}$), the recorder automatically queries Binance Spot REST API (`/api/v3/klines?symbol=BTCUSDT&interval=1h`), verifies the finalized Open and Close, evaluates $Y$, and appends the ground truth record to `data/polymarket/finalized_market_resolutions.jsonl`.

---

### 12. Statistical Inference, Clustering, and Impulse Curves (Points 14 & 15)

#### Cluster-Robust Standard Errors (Point 14)
Because thousands of snapshots and multiple ladder steps are recorded per hour ($N_{\text{rows}} \gg N_{\text{events}}$), ordinary regression standard errors would be severely downward biased. Standard errors are pre-registered to cluster at:
1. **Market-Hour Level**: $\text{Cluster}_{\text{market}} = \text{market\_id}$
2. **Shock-Episode Level**: $\text{Cluster}_{\text{episode}} = \text{market\_id} \times \text{shock\_id}$

#### Single Microstructure Object (Point 15)
The response ladder ($\Delta q_{100\text{ms}}, \dots, \Delta q_{30\text{s}}$) is treated as a **single impulse-response function**:
$$\text{IRF}(\tau) = \mathbb{E}[\Delta q(\tau)]$$
Standard error confidence bands are generated via **block bootstrap at the shock-event level**, avoiding multiple hypothesis testing inflation across individual ladder delays.

---

### 13. Operational State & Telemetry Log
* **Daemon Status**: Running under PID `1995992` on Tokyo GCP node (`kraken-execution-worker-tyo`).
* **Active Stream Files**:
  * Telemetry: `data/polymarket/polymarket_hourly_telemetry.jsonl`
  * Shocks: `data/polymarket/shock_responses.jsonl`
  * Resolutions: `data/polymarket/finalized_market_resolutions.jsonl`
  * Cross-Correlations: `data/polymarket/leadlag_cross_correlations.jsonl`
* **Operational Boundary**: Strictly read-only; zero orders, zero private keys, zero geo-restriction circumvention.




