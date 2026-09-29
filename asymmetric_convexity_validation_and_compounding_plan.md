# Asymmetric Convexity Validation & Compounding Plan: Tri-Engine Blueprint (v2.9 Tri-Engine Sovereign Production State)

---

## Executive Status & Tri-Engine Architecture

```
========================================================================================================
                     TRI-ENGINE SOVEREIGN PRODUCTION PIPELINE (v2.9)
========================================================================================================
[ENGINE 1: CORE COMPOUNDING PERPETUAL] ──> 85% Capital Allocation ($620.51 NAV, $610.92 Cash)
  ├── Live Daemon : production_apex_daemon.py (PID 16797, systemd active, 0-Mutation Invariant)
  ├── Micro Cycle : Bar 7/18 Complete -> Bar 8/18 at 20:00:14 UTC (4H Micro Risk Audit)
  ├── Macro Cycle : Bar 18/18 at 2026-10-01 12:00:00 UTC (72H Macro Rebalance, 240s ALO Window)
  └── Shadow Engine: exp104_macro_hedge_shadow.py (PID 2851516, Dynamic Ratchet Floor $577.89)

[ENGINE 2: ROUTE 2 HL RATCHET MOMENTUM] ──> Isolated Subaccount ($20-$50 Sandbox)
  ├── Shadow Daemon : hl_isolated_ratchet_shadow.py (PID 2885020, Phase B1 Active)
  ├── Asset Universe: SOL (20x), HYPE (10x), SUI (10x), DOGE (10x)
  ├── Order Flow    : Binance USD-M aggTrade (>= $1.5M/100ms) + Tokyo Hyperliquid L2 WebSocket
  └── Enhancements  : Dynamic OFI Routing, +0.70% Early Net-BE Lock, +1.50% Pyramid Sizing

[ENGINE 3: ROUTE 3 POLYMARKET DATA LAB] ──> Read-Only Paper Sandbox ($1,000 Paper NAV)
  ├── Paper Trader : polymarket_paper_trader.py (PID 2851129, Late-Candle TTE <= 15m Sweet Spot)
  ├── Data Recorder: polymarket_terminal_recorder.py (PID 2037196, Dual-Feed Telemetry Antenna)
  └── Live Ledger  : 15 Settled Trades | 9 Wins / 6 Losses (60.0% WR) | +$113.79 PnL ($1,113.79 Equity)

[TRACK 1: DERIVE 0DTE OPTIONS] ──> [FALSIFIED & PERMANENTLY TERMINATED]
  ├── Verdict: Insufficient Terminal Depth (<$9k) & Systematic MM Bid Withdrawal ($0.00 Bids)
  └── Action : Background probes terminated, sockets closed, data archived to data/archive/
========================================================================================================
```

* **Core/Satellite Structural Separation**: Preserved and formalized. Core engine ([`production_apex_daemon.py`](file:///home/skybullet1987/quant_pipeline/src/execution/production_apex_daemon.py)) remains strictly unmutated.
  * $\text{NAV}_{\text{core, current}} = \mathbf{\$620.51\text{ USDC}}$ (Holding 1 position: ETH 10x @ $2,685.70, +$1.21 ROE, +$3.13 funding carry earned)
  * $\text{Cash}_{\text{core}} = \mathbf{\$610.92\text{ USDC}}$ (Unallocated capital earning margin safety, waiting for Oct 1 Bar 18/18 rebalance)
  * $\text{HWM}_{\text{core}} = \mathbf{\$642.10\text{ USDC}}$ (Drawdown from peak is $-3.36\%$, well within expected 4H rebalancing drift)
  * $\text{NAV}_{\text{satellite}} = \mathbf{\$0.00\text{ USDC}}$ (Phase B1 is running in isolated shadow simulation; zero live capital allocated)
  * $\text{NAV}_{\text{combined}} = \mathbf{\$620.51\text{ USDC}}$
* **Accounting Model**: Strictly canonical fill-level accounting. Realized PnL is separated from execution shortfall attribution; slippage is never double-counted.
* **Gate Hierarchy**:
  * **Phase A (Derive Options)**: **FALSIFIED & PERMANENTLY TERMINATED**. Consecutive empirical probes confirmed that market makers withdraw bids ($0.00 bid) and book depth falls below $9k in terminal 0DTE (<1h to expiry). All background probe processes stopped, `data/derive/` archived, and sockets closed. Capital preserved; zero funds deployed.
  * **Phase B1 (Hyperliquid Engineering Shadow)**: **ACTIVE SHADOW** under PID `2885020`. 4 live sprints logged; calibrated with Early Micro-Breakeven at $+0.70\%$ and expanded to 4 liquid altcoins (`SOL`, `HYPE`, `SUI`, `DOGE`) with dynamic OFI book imbalance routing.
  * **Phase B2 (Pre-Registered Block Alpha Certification)**: **LOCKED** pending B1 pass (targeting 30–50 shocks).
  * **Phase C (Live Micro-Canary)**: **LOCKED** pending B2 certification.
  * **Engine 3 (Polymarket Forward Paper Trader)**: **ACTIVE SHADOW** under PID `2851129`. 15 settled hourly trades, yielding **9 Wins / 6 Losses (60.0% WR)** and **+$113.79 net PnL** on $1,000 paper capital ($1,113.79 equity).
  * **Engine 1 Shadow Tracker (EXP-104 Macro Hedge)**: **ACTIVE SHADOW** under PID `2851516`. Tracking side-by-side forward performance leading into October 1 rebalance.

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

#### Hyperliquid Protocol Constraints & Asset Universe
* **SOL**: Max $20\times$ leverage ($5.0\%$ initial margin requirement, $2.5\%$ maintenance margin rate). Sizing: $N_1 = \$400.00$, $N_2 = \$100.00$.
* **HYPE**: Max $10\times$ leverage ($10.0\%$ initial margin, $5.0\%$ maintenance margin). Sizing: $N_1 = \$200.00$, $N_2 = \$50.00$.
* **SUI**: Max $10\times$ leverage ($10.0\%$ initial margin, $5.0\%$ maintenance margin). Sizing: $N_1 = \$200.00$, $N_2 = \$50.00$.
* **DOGE**: Max $10\times$ leverage ($10.0\%$ initial margin, $5.0\%$ maintenance margin). Sizing: $N_1 = \$200.00$, $N_2 = \$50.00$.
* **BTC**: Reference lead instrument (Max $40\times$ leverage). Used strictly as macro antenna for $\ge \$1.5\text{M}$ volume sweeps.

#### Dynamic Order Book Imbalance (OFI) Routing
On detecting a qualifying institutional BTC sweep ($\ge \$1.5\text{M}$ in $100\text{ms}, Z_{\text{OFI}} \ge 2.58$), the shadow engine polls resting L2 books across all 4 candidate altcoins and computes instantaneous top-of-book imbalance:
$$\text{OBI}_{\text{top}} = \frac{Q_{\text{bid}} - Q_{\text{ask}}}{Q_{\text{bid}} + Q_{\text{ask}}}$$
The sprint is dispatched directly into the asset exhibiting the strongest positive resting bid support, maximizing initial momentum transmission and minimizing adverse execution slippage.

#### All-In Sizing Equation Including Frictions
To ensure dollar risk targets reflect true net execution:
$$N_1 = \min \left( \frac{L_{\text{target}}}{d_{\text{stop}} + c_{\text{all-in}}}, \ C_{\text{available}} \cdot \text{Leverage}_{\max} \right)$$
where $c_{\text{all-in}} = d_{\text{slip}} + d_{\text{entry\_fee}} + d_{\text{exit\_fee}} + d_{\text{funding}}$.
* For $d_{\text{stop}} = 180\text{ bps}$, $d_{\text{slip}} = 7\text{ bps}$, $d_{\text{fees}} = 9\text{ bps}$, $d_{\text{funding}} = 0.5\text{ bps} \implies c_{\text{all-in}} = 16.5\text{ bps}$:
  $$N_1 = \min \left( \frac{18.00}{0.0180 + 0.00165}, \ 50 \times 20 \right) = \min(\$916.03, \ \$1,000.00) = \mathbf{\$916.03 \text{ notional}}$$

#### Operational Margin Headroom ($N_1 = \$380.00–\$400.00$ on SOL):
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
* **Transfer & NAV Accounting (Point 13 Reconciliation)**:
  * Current Live Paper Accounting:
    $$\text{NAV}_{\text{core, current}} = \mathbf{\$620.51\text{ USDC}}$$
    $$\text{Cash}_{\text{core}} = \mathbf{\$610.92\text{ USDC}}$$
    $$\text{HWM}_{\text{core}} = \mathbf{\$642.10\text{ USDC}}$$
    $$\text{NAV}_{\text{satellite}} = \mathbf{\$0.00\text{ USDC}} \quad (\text{Phase B1 is running in isolated shadow simulation; zero live capital allocated})$$
    $$\text{NAV}_{\text{combined}} = \mathbf{\$620.51\text{ USDC}}$$
  * Prospective Phase C Live Funding Accounting (if authorized):
    $$\text{NAV}_{\text{core}} = \text{NAV}_{\text{core, current}} - C_{\text{satellite}} = \$620.51 - \$20.00 = \mathbf{\$600.51\text{ USDC}}$$
    $$\text{NAV}_{\text{satellite}} = \mathbf{\$20.00\text{ USDC}}$$
    $$\text{NAV}_{\text{combined}} = \mathbf{\$620.51\text{ USDC}}$$

---

### 5. Multi-Level Bankroll Survival Reality
1. **One-Sprint Survival**: An initial $\$20.00$ sandbox allocation supports **ONE full-size $\$400$ sprint**. After one $-\$7.80$ loss, the remaining $\$12.20$ cannot reopen another $\$400$ position (which requires $\$20.00$ initial margin) without replenishment.
2. **Satellite-Series Bankroll**:
   * A $\$50.00$ series bankroll supports **FOUR consecutive full-size $\$400$ attempts** ($50 - 4 \times 7.80 = \$18.80$, below the $\$20.00$ required for attempt #5).
   * To support **SIX consecutive full-size attempts**, the required minimum bankroll is:
     $$C_{\min} = \$20.00 + 5 \times \$7.80 = \mathbf{\$59.00 \text{ (before operational buffer)}}$$
   * Sizing policy: $C_{\text{series}} = \$60.00$ fixed, with zero replenishment until formal review.
3. **Combined-Account Stress Test**: 20 hypothetical modeled full-stop losses ($20 \times -\$7.80 = -\$156.00$) from peak HWM would reduce combined NAV from $\$642.10$ to $\$486.10$, **assuming an external replenishment mechanism permits all 20 attempts**. Core NAV itself remains protected in its own isolated account.

---

## Section 3: Phase B Statistical Testing Protocol

### 1. Pre-Registered Primary B2 Endpoint & Frozen Outcome Function
To prevent multiple-testing data dredging, Phase B2 freezes **both the trigger and the full outcome function**:

> **Pre-Registered Primary Endpoint**:
> * **Asset**: SOL
> * **Trigger**: Binance Volume Sweep $\ge \$1.5\text{M}$ in $100\text{ms}$ with directional $Z_{\text{OFI}} \ge 2.58$.
> * **Primary Sizing**: $N_1 = \$400.00$ exactly ($N_1 = \$380.00$ is designated strictly as operational canary sensitivity).
> * **Primary Friction Hurdle**: $C_{\text{friction}} = 25\text{ bps}$ exactly ($40\text{ bps}$ and $60\text{ bps}$ are robustness checks).
> * **Initial Stop**: Nominal $-1.80\%$ mark-triggered order.
> * **Pyramid Rule**: $+1.50\%$ spot move triggers $N_2 = \$100.00$ secondary fill.
> * **Breakeven Rule**: Stop updated to dynamic $P_{\text{net\_BE}} = \text{VWAE} + \text{costs}$.
> * **Profit Lock Rule**: $+3.50\%$ spot move locks $+1.80\%$ above entry.
> * **Trailing Rule**: $1.0\%$ dynamic trailing stop distance from HWM.
> * **Max Holding Horizon**: $45\text{ minutes}$ hard time exit.
> * **Conjunctive Certification Gate (Mandatory Pass Condition)**:
>   $$\mathbf{LCB_{95\%,\text{cluster}}\left(\mathbb{E}[R_{\text{net}}]\right) > 0 \quad \land \quad p_{\text{placebo}} < 0.01}$$
>   Both conditions must be met simultaneously; failure on either aborts live Phase C authorization. Resampling grouped via shock-episode block bootstrap.

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
[ENGINE 1: CORE COMPOUNDING PERPETUAL (EXP-103 & EXP-104 SHADOW)]
  ├── Status: ACTIVE & HEALTHY on Tokyo GCP (PID 16797, production_apex_daemon.py)
  ├── Capital: Initial $559.31 -> Current $620.51 NAV ($610.92 cash balance, 1 ETH 10x position)
  ├── Funding Carry: +$3.13 earned holding ETH inventory (paid to hold positive trend carry)
  ├── Micro Cycle: 4H Risk Audits (Bar 7/18 passed; Next: Bar 8/18 at 20:00:14 UTC)
  ├── Macro Cycle: 72H Macro Rebalance Bar 18/18 (Next: 2026-10-01 12:00:00 UTC)
  └── Shadow Overlay: EXP-104 active (PID 2851516, logging 60s side-by-side forward equity against EXP-103)

[ENGINE 2: ROUTE 2 HYPERLIQUID RATCHET SHADOW (PHASE B1)]
  ├── Status: ACTIVE & HEALTHY on Tokyo GCP (PID 2885020, hl_isolated_ratchet_shadow.py)
  ├── Streams: Tokyo Binance Futures aggTrade (routed /market) + Tokyo Hyperliquid L2 WebSocket
  ├── 4-Asset Universe: SOL (20x), HYPE (10x), SUI (10x), DOGE (10x)
  ├── Routing Mechanism: Dynamic OFI selection (dispatches to asset with highest positive book imbalance)
  ├── Upgrades: Early Dynamic Net-BE Lock (+0.70%) + Stage 1 Pyramid (+1.50%) + Profit Lock (+3.50%)
  └── Target Sample: 30-50 institutional volatility shocks ($1.5M/100ms) for Phase B1 Pass

[ENGINE 3: ROUTE 3 POLYMARKET DATA LAB & FORWARD PAPER TRADER]
  ├── Status: ACTIVE & HEALTHY on Tokyo GCP (Recorder: PID 2037196 | Paper Trader: PID 2851129)
  ├── Telemetry: 7,500+ records, 490+ shock bursts, 20 finalized hourly candle resolutions
  ├── Strategy: Late-Candle Filter (TTE <= 15m, Spot-to-Open Candle Distance Congruence)
  ├── Paper Ledger: $1,000 Initial -> $1,113.79 NAV (+$113.79 Net PnL, +11.38% Return)
  ├── Track Record: 15 Settled Contracts | 9 Wins / 6 Losses (60.00% Win Rate) | $11.68 Taker Fees Paid
  └── Compliance Boundary: Strictly Read-Only telemetry & forward paper simulation; zero geo-breach

[TRACK 1: ROUTE 1 DERIVE 0DTE OPTIONS (EXPERIMENT D) — DECOMMISSIONED & ARCHIVED]
  ├── Status: FALSIFIED & PERMANENTLY TERMINATED
  ├── Falsification Evidence:
  │     ├── Day 1 Probe (Sep 28 07:00 UTC): Depth $21.8k < $25k hurdle, Bid continuity 33.3% < 70%
  │     ├── Day 2 Probe (Sep 29 07:00 UTC): Depth $21.8k < $25k hurdle, Bid continuity 33.3% < 70%
  │     └── Sep 29 17:31 UTC Probe: BTC Quoted Depth $8,857.31 < $25k hurdle, MM bids withdrawn to $0.00
  ├── Forensic Autopsy: AMMs/CLOBs on L2 face toxic gamma adverse selection; quote withdrawal is structural
  └── Decommissioning: Harvester & scheduler stopped, sockets closed, data archived to data/archive/
```

---

## Section 6: Route 3 — Futures/Spot $\to$ Polymarket Information-Flow Experiment (v2.7 Forensic Specification)

### 1. The Dual-Feed Information Transmission Hypothesis (Point 16 & Point 2)
Polymarket's hourly BTC market explicitly resolves against the finalized **Binance Spot BTC/USDT** 1-hour candle. However, aggressive institutional order flow and price discovery in crypto markets frequently originate in the **USDⓈ-M perpetual futures market**.

Rather than treating futures/spot basis as an error or baking in an unproven causal sequence, Route 3 structures this as an empirical **Information-Flow Experiment**:

$$\boxed{ \text{Hypothesis: } X^{\text{futures}}_t \longrightarrow X^{\text{spot}}_{t+\Delta} \longrightarrow q_{\text{Poly}, t+\Delta} \quad \text{vs.} \quad X^{\text{spot}}_t \longrightarrow q_{\text{Poly}, t+\Delta} }$$

#### Active Data Antennas
* **Binance Spot**: `wss://stream.binance.com:443/ws/btcusdt@aggTrade` (Polymarket settlement reference).
* **Binance Futures**: `wss://fstream.binance.com:443/market/ws/btcusdt@aggTrade` (Routed 2026 `/market` order flow antenna).
* **Polymarket CLOB WebSocket L2**: `wss://ws-subscriptions-clob.polymarket.com/ws/market` (Continuous binary probability book).

#### Flow Innovations & Null Hypothesis Testing (Point 2)
High-frequency flow variables exhibit significant autocorrelation and shared market volatility. Therefore, lead/lag estimation is conducted on **de-autocorrelated flow innovations** ($\epsilon_t = \Delta \text{flow}_t$ or AR(1) residuals), not raw price levels:
$$\text{Corr}(\epsilon_F(t), \epsilon_S(t + \Delta)) \quad \text{and} \quad \text{Corr}(\epsilon_F(t), \Delta q(t + \Delta))$$
across the pre-registered millisecond lag grid:
$$\Delta \in \{-1000, -500, -250, -100, -50, 0, +50, +100, +250, +500, +1000\}\text{ ms}$$
$$\boxed{ \text{Pre-Registered Null Hypothesis: } H_0: \text{no stable lead/lag structure across grid} }$$
*Telemetry Standard*: Individual five-minute rolling cross-correlations are classified as **illustrative live telemetry, not evidence of persistent lead/lag**, until pooled across shock episodes with block/permutation testing.

---

### 2. Multi-Clock Latency & Calibrated Clock Offsets (Points 11, 12, & 3)
To avoid conflating exchange matching latency, network transit, and unmeasured clock skew between remote Binance servers and local Tokyo infrastructure:
1. $t_{\text{binance\_event}}$ ($E$, Binance matching engine event timestamp in microsecond/millisecond units)
2. $t_{\text{binance\_trade}}$ ($T$, Binance trade execution timestamp)
3. $t_{\text{receive\_local}}$ (Tokyo GCP local monotonic nanosecond and unix timestamp)
4. $t_{\text{polymarket\_event}}$ (Polymarket CLOB message timestamp)
5. $t_{\text{receive\_polymarket}}$ (Tokyo GCP local receive timestamp of Polymarket L2 update)

#### Cristian's Algorithm Clock Synchronization
The recorder runs periodic clock calibration against Binance REST server time (`/api/v3/time`):
$$\widehat{\text{Offset}} = \frac{t_{\text{req}} + t_{\text{resp}}}{2} - t_{\text{server}}, \quad \text{Uncertainty} = \pm \frac{\text{RTT}}{2}$$
$$\text{Latency}_{\text{calibrated}} = t_{\text{local\_receive}} - (t_{\text{exchange}} + \widehat{\text{Offset}})$$
* **Empirical Live Calibration**: $\widehat{\text{Offset}} = -17.62\text{ ms} \pm 21.59\text{ ms}$ ($\text{RTT} = 43.19\text{ ms}$).
* **Standard Terminology**: Raw differences without offset calibration are strictly designated as **"exchange-to-local timestamp delta"** rather than "network latency."

---

### 3. Mathematical Reconciliation of OBI and Microprice (Point 1 & Point 13)

#### Reconciled Mathematical Formulation
Route 3 explicitly decouples Level 1 OBI from Depth OBI:
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
* Mandatory logged metadata: `obi_depth_levels = 5`, `microprice_formula`, `book_sequence_id`, `book_timestamp`.

---

### 4. Tripartite Quote Age Decomposition (Point 6)
To identify genuine stale executable quotes versus general depth churn, quote age is decomposed into three distinct durations:
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

### 7. Four Pre-Registered Econometric Models & Strict OOS Training Invariant (Points 4 & 12)
Route 3 pre-registers four nested models to test for incremental futures information:
* **Model A (Spot Baseline)**: $Y = f(q_{\text{mid}, t_0}, X^{\text{spot}}_{t_0}, \text{TTE}, \text{dist}_{\text{open}})$
* **Model B (Futures Baseline)**: $Y = f(q_{\text{mid}, t_0}, X^{\text{futures}}_{t_0}, \text{TTE}, \text{dist}_{\text{open}})$
* **Model C (Joint Lead/Lag Specification)**: $Y = f(q_{\text{mid}, t_0}, X^{\text{spot}}_{t_0}, X^{\text{futures}}_{t_0}, \text{Basis}_{t_0}, \Delta \text{Basis}_{100\text{ms}}, \text{TTE}, \text{dist}_{\text{open}})$
* **Model D (Futures Incremental Information Model)**:
  $$Y = f(q_{\text{mid}, t_0}, X^{\text{spot}}_{t_0}, \text{TTE}, \text{dist}_{\text{open}}) + g(X^{\text{futures}}_{t_0} \mid X^{\text{spot}}_{t_0})$$
  $$\boxed{ \text{Primary Null Hypothesis: } H_0: \beta_{F|S} = 0 }$$

#### Hard Model Training Invariant (Point 12)
$$\boxed{ T_{\text{train\_end}} < t_0 }$$
Every probability model $p_{\text{model}}$ predicting resolution $Y$ must be trained strictly on **completed prior markets**, strictly time-ordered, frozen before the test event, walk-forward. Training on data from the currently active market hour is an econometric violation.

---

### 8. Dynamic Contract Fee Architecture & Fill-Level Fees (Points 8 & 1)
Polymarket's fee structure is dynamically queried from contract metadata:
* `fee_rate_market`: Dynamically parsed from Gamma API `feeSchedule.rate` ($0.07 = 7.0\%$).
* `fee_source`: Source identifier (`gamma_feeSchedule_crypto_fees_v2`).
* `fee_enabled`: Boolean flag.
* `fee_formula_version`: `crypto_fees_v2` ($C \times \text{feeRate} \times p(1 - p)$).
* `takerOnly`: `true` (makers pay zero).

#### Exact Fill-Level Fee Accumulation (Point 8)
Because $f(\bar{p}) \neq \overline{f(p)}$ in nonlinear fee schedules, fees are accumulated across each individual book level $i$ consumed:
$$\text{Fee}(C) = \sum_i Q_i \cdot \text{feeRate} \cdot p_i(1 - p_i)$$
$$\text{TotalCost}(C) = \sum_i Q_i p_i + \text{Fee}(C), \quad \text{EffectivePrice}(C) = \frac{\text{TotalCost}(C)}{\sum_i Q_i}$$

---

### 9. Decoupling Crossing Cost from Expected Terminal Value (Point 1)
To prevent mathematical conflation of immediate execution markup with terminal expected value:
* **Crossing Cost (Immediate Execution Markup over Midpoint)**:
  $$\boxed{ \text{CrossingCost}(C) = \text{EffectivePrice}(C) - q_{\text{mid}} }$$
  Measures the cost to cross the spread and sweep depth for notional $C$.
* **Expected Terminal Value (Reserved for Out-of-Sample Models)**:
  $$\boxed{ \text{EV}_{\text{terminal}}(C) = p_{\text{OOS}} - \text{EffectivePrice}(C) }$$
  Evaluated strictly using an out-of-sample conditioned statistical probability $p_{\text{OOS}}$, never $q_{\text{mid}}$.

---

### 10. Strategy Dichotomy: Terminal Hold vs. Momentum Repricing (Point 9)
Two distinct economic strategies are separated in the analysis:
* **Strategy R3-A — Terminal Hold (Primary Scientific Experiment)**:
  $$\text{Buy}(q_t) \longrightarrow Y \in \{0, 1\}, \quad \text{EV}_{\text{terminal}} = p_{\text{OOS}} - \text{EffectivePrice}(C)$$
  Single execution leg, held to Binance 1H candle settlement.
* **Strategy R3-B — Momentum Repricing Capture (Secondary Execution Study)**:
  $$\text{Buy}(q_t) \longrightarrow \text{Sell}(q_{t+\Delta t}), \quad \mathbb{E}[\text{PnL}] = \mathbb{E}[q_{\text{sell}} - q_{\text{buy}} - \text{Fee}_{\text{buy}} - \text{Fee}_{\text{sell}} - \text{Spread/Slippage}]$$
  Two execution legs and double taker fees.

---

### 11. Finalized Candle Ground Truth Verification (Point 10)
Polymarket hourly contracts resolve strictly against the finalized open and close of the specified Binance Spot BTC/USDT 1-hour candle:
$$Y = \mathbf{1}[C_{\text{1H}} \ge O_{\text{1H}}]$$
At candle expiry ($T_{\text{expiry}}$), the recorder automatically queries Binance Spot REST API (`/api/v3/klines?symbol=BTCUSDT&interval=1h`), verifies the finalized Open and Close, evaluates $Y$, and appends the ground truth record to `data/polymarket/finalized_market_resolutions.jsonl`.

---

### 12. Statistical Inference, Clustering, and Cautious Wording (Points 14, 15, & 5)

#### Variance Estimator Specification (Point 10)
Because shock episodes are nested inside market hours:
1. **For Cross-Sectional Regressions (Models A, B, C, D)**: **Market-hour cluster-robust standard errors** (hierarchical clustering at the market-hour level to conservatively account for within-hour shock correlations).
2. **For Impulse-Response Curves ($\text{IRF}(\tau)$)**: **Shock-episode block bootstrap** across the entire response curve $\text{IRF}(\tau) = \mathbb{E}[\Delta q(\tau)]$.

#### Forensic Episode Phrasing Standard (Point 5)
* **Standard Phrasing**:
  *"This episode exhibited no measured Polymarket ask repricing through 1 second, followed by a +8¢ repricing at 5 seconds. Structural repricing lag $\mathbb{P}(\Delta q(\tau) > 0)$ and $\mathbb{E}[\Delta q(\tau)]$ will be established only after pooling hundreds of shock events with shock-episode block bootstrap confidence bands."*

---

### 13. Operational State & Telemetry Log
* **Dual-Feed Recorder Daemon**: Running under PID `2037196` on Tokyo GCP node (`kraken-execution-worker-tyo`).
* **Active Stream Files**:
  * Telemetry: `data/polymarket/polymarket_hourly_telemetry.jsonl` (7,500+ records)
  * Shocks: `data/polymarket/shock_responses.jsonl` (490+ shock bursts)
  * Resolutions: `data/polymarket/finalized_market_resolutions.jsonl` (19 verified hourly markets)
  * Cross-Correlations: `data/polymarket/leadlag_cross_correlations.jsonl` (1,040+ records)
* **Operational Boundary**: Strictly read-only public data collection.

---

### 14. Autonomous Forward Paper Trading Engine (`polymarket_paper_trader.py`)
To test real monetization without risking capital or violating jurisdictional boundaries, a dedicated forward paper-trading daemon runs under PID `2851129`:
* **Filter Rule (The Late-Candle Sweet Spot)**:
  * $\text{TTE} \le 15\text{ minutes}$ (eliminating early-hour mean-reverting noise).
  * Direction congruent with distance from candle open ($P_{\text{spot}} > P_{\text{open}}$ for UP, $P_{\text{spot}} < P_{\text{open}}$ for DOWN).
  * Effective price bounds: $\$0.15 \le P_{\text{eff}} \le \$0.85$.
  * Size: $\$50.00$ notional per ticket; max 2 concurrent tickets per market.
* **Empirical Replay Results (Past 20 Hourly Markets)**:
  * **Starting Paper Capital**: $\$1,000.00\text{ USDC}$
  * **Settled Trades**: $15$
  * **Wins**: $9 / 15$ ($\mathbf{60.00\% \text{ Win Rate}}$)
  * **Total Fees Paid**: $\$11.68\text{ USDC}$ (7% crypto taker schedule)
  * **Net Realized PnL**: $\mathbf{+\$113.79\text{ USDC}}$ ($\mathbf{+11.38\%}$ return in 19 hours)
  * **Current Paper Equity**: $\mathbf{\$1,113.79\text{ USDC}}$
  * **Output Ledger**: `data/polymarket/paper_trading_ledger.jsonl` and `data/polymarket/paper_trader_state.json`.

---

## Section 7: October 1 Compounding Upgrade Protocol

### 1. EXP-104 Macro Hedge Shadow Daemon (`exp104_macro_hedge_shadow.py`)
* **Process Status**: Active under PID `2851516`.
* **Mechanism**: Reads unmutated `data/papertrade_state.json` every 60s. When BTC 1H momentum drops $\le -0.75\%$, it opens a simulated short BTC/ETH perpetual overlay hedge matching portfolio delta, enforcing the $0.90 \times \text{HWM}^*$ ratchet floor ($F_t = \$577.89$).
* **Decision Gate for October 1 Bar 18/18 Rebalance**: If EXP-104 synthetic equity demonstrates superior Sortino/drawdown performance across the 60-hour pre-rebalance window, promote the macro hedge directly to `production_apex_daemon.py`.

### 2. Hyperliquid Gate 2 ALO Rebalance Optimization
* **Offline Audit**: The 180s ALO convergence window forced less liquid altcoins (SUI, GRAM) into aggressive IOC taker fills, dipping the maker ratio to $58.6\%$.
* **Bar 18/18 Optimization Rule**:
  * Expand ALO convergence window: $180\text{s} \longrightarrow 240\text{s}$.
  * Deepen Avellaneda-Stoikov quote offset: $0.5\text{ bps} \longrightarrow 1.0\text{ bps}$.
  * Projected Impact: Lifts maker fill ratio to $>72\%$, saving $\sim 15\text{ bps}$ in turnover fees.

### 3. Route 2 Ratchet Calibration & Universe Expansion
* **Live Sprint Audit**: 4 live sprints exited at 45m with minor scratches (avg $-\$1.40$) because breakouts peaked at $+0.75\%$ without reaching $+1.50\%$.
* **Micro-Breakeven Implemented**: Added early dynamic Net-Breakeven lock at $+0.70\%$ to prevent profitable runner decay. Sizing trigger retained at $+1.50\%$ for secondary $N_2 = \$100$.
* **Universe Expansion**: Expanded ingestion universe to 4 liquid, high-beta altcoins (`SOL`, `HYPE`, `SUI`, `DOGE`) under PID `2885020`.
* **Dynamic OFI Dispatch**: On institutional BTC volume sweeps ($\ge \$1.5\text{M}$ in $100\text{ms}$), the engine dispatches to the altcoin with the strongest positive order book imbalance ($(\text{bid\_sz} - \text{ask\_sz})/(\text{bid\_sz} + \text{ask\_sz})$).

### 4. Decommissioning & Archival of Track 1 (Derive 0DTE Options)
* **Status**: **FALSIFIED & TERMINATED** (Insufficient Terminal Depth & Market Maker Quote Withdrawal).
* **Execution**: Stopped all background probe schedulers, closed network sockets, and archived `data/derive/` into `data/archive/derive_experiment_d_falsified_*.tar.gz`. Zero real capital allocated. Concentration shifted 100% to Track 2 (HL Ratchet) and Track 4 (Polymarket Data Lab).

### 5. Autonomous Milestones & Production Chronology

| Checkpoint (UTC) | Horizon | Target Module | Objective & Metric to Inspect |
| :--- | :--- | :--- | :--- |
| **2026-09-29 19:00:00 UTC** | ~50 min | Engine 3 (Polymarket) | 1-Hour contract resolution (2PM ET candle close against Binance Spot). |
| **2026-09-29 20:00:14 UTC** | ~1.9 hrs | Engine 1 (EXP-103 Apex) | **Bar 8 of 18 Micro Risk Audit**: Reconcile NAV ($620.51), ETH 10x carry (+>$3.13), and stop buffer. |
| **2026-09-29 23:15:00 UTC** | ~5.1 hrs | Engine 3 (Polymarket) | **First Full 24-Hour Paper Ledger Report**: 24 consecutive contracts, net PnL, fee drag, Brier score. |
| **2026-09-30 08:00:00 UTC** | ~14 hrs | Engine 1 (EXP-103 Apex) | Bar 11 of 18 Micro Risk Audit. |
| **2026-10-01 12:00:00 UTC** | ~42 hrs | **Core Macro Rebalance** | **Bar 18 of 18 Macro Cycle**: Redeploy $610+ cash into 16-asset basket, activate 240s ALO window, and evaluate EXP-104 hedge overlay. |





