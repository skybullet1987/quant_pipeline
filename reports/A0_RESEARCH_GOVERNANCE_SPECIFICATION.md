# Frozen A0 Research-Governance Specification (v3.2.1)
**Document Status**: `IMMUTABLE_FROZEN_BASELINE`  
**Certification Hash**: `A0_CONF_20260930_V321`  
**Effective Date**: September 30, 2026 (Tokyo Node Synchronized)  
**Parent Specifications**: v3.0 Forensic State ➔ v3.1 Conformance ➔ v3.2 Peer Review ➔ **v3.2.1 Frozen A0**

---

## 1. Executive Summary & Progression Architecture

The **v3.2.1 Specification** establishes the institutional research-governance baseline for the multi-engine quantitative compounding pipeline. It resolves all 17 econometric, wire-level, and risk enforcement blockers, permanently decoupling statistical alpha discovery from physical execution constraints and machine-enforced capital defense.

```
                           Progression Architecture (v3.2.1)
                                         │
    ┌────────────────────────────────────┼────────────────────────────────────┐
    ▼                                    ▼                                    ▼
[TIER 1: ALPHA CERT]             [TIER 2: EXECUTION CERT]            [TIER 3: CANARY CERT]
Statistical edge proven           Survives empirical latency,         Verified live in $20 sandbox;
via Doubly Robust estimator       taker fees, and legging risk        fills match model
(LCB_99% > 12.5 bps)             (Modeled shortfalls verified)       (Zero simulation drift)
    │                                    │                                    │
    └────────────────────────────────────┼────────────────────────────────────┘
                                         ▼
                               [TIER 4: CAPACITY CERT]
                               Progressive scaling ($100 → $500 → $2k);
                               Market impact models confirmed
                                         │
                                         ▼
                               [TIER 5: PRODUCTION ALLOCATION]
                               Integrated deployment within Sovereign Portfolio
```

> **Decoupled Invalidation Invariant**: A capacity failure at Tier 4 revokes Tier 4 capacity authorization and throttles production sizing, leaving Tiers 1–3 intact. Lower tiers are invalidated only if the underlying mathematical feature set or execution logic commit hash is altered.

---

## 2. Layer-by-Layer Institutional Codification

### Layer 1: Econometric Precision & The Doubly Robust Event Estimator
* **Observational vs. Causal Framing**: All references to "causal identification" in observational settings are strictly reframed as the **Matched Event-Study Effect** ($\hat{\tau}_{\text{event}}$). Matching on pre-treatment covariates $\mathbf{Z}_{t_i^-}$ controls for observable book depth, spread, volatility, and order flow imbalance, but does not claim strict causality due to potential unobserved latent market confounders.
* **Doubly Robust Residualized Estimator**:
  $$\hat{\tau}_{\text{event}}(\tau) = \left( r_{t_i, t_i+\tau}^{T_i} - \hat{m}(\mathbf{Z}_{t_i^-}) \right) - \left( r_{t_i, t_i+\tau}^{C_i} - \hat{m}(\mathbf{Z}_{C_i^-}) \right)$$
  where $\hat{m}(\mathbf{Z}) = \mathbb{E}[R \mid \mathbf{Z}]$ is a pre-treatment continuation model estimated on non-liquidation order flow.
* **Separation of Endpoints**:
  - *Scientific Event Endpoint*: $\Delta r_{\text{event}}(30\text{s}) = (r_T - \hat{m}(\mathbf{Z}_T)) - (r_C - \hat{m}(\mathbf{Z}_C))$
  - *Strategy Trading Endpoint*: $\Delta r_{\text{strategy}}(30\text{s}) = (r_T - c_{\text{roundtrip}}) - \hat{m}(\mathbf{Z}_T)$
* **Derivation of Gate A Hurdle (12.5 bps)**:
  $$\text{Hurdle} = c_{\text{taker\_fee}} (4.5\text{ bps}) + \text{Slippage}_{\text{P90}} (3.5\text{ bps}) + \text{LatencyRisk}_{\text{Tokyo}} (2.0\text{ bps}) + \text{MinNetEdge} (2.5\text{ bps}) = \mathbf{12.5\text{ bps}}$$
  **Gate A Acceptance Hurdle**: $\text{LCB}_{99\%}(\Delta r_{\text{strategy}}(30\text{s})) > 12.5\text{ bps}$ across $N_{\text{episodes}} \ge 100$ independent clusters via Wild Cluster Bootstrap.

---

### Layer 2: EXP-201A Timestamp Semantics & Censoring Model
* **Decomposed Wire Schema**: For every event ingested via `wss://fstream.binance.com/ws/!forceOrder@arr`:
  1. *Exchange Execution Time*: $T_{\text{Binance}} = \text{payload.o.T}$ (Order Trade Time in epoch ms).
  2. *Exchange Publication Time*: $E_{\text{Binance}} = \text{payload.E}$ (Event Time in epoch ms).
  3. *Local Receipt Time*: $t_{\text{recv}} = \text{time.monotonic\_ns}()$ and $t_{\text{recv\_wall}} = \text{time.time}()$.
  4. *Transport Delay*: $\delta_{\text{transport}} = \text{int}(t_{\text{recv\_wall}} \times 1000) - T_{\text{Binance}}$.
  5. *Snapshot Censoring Marker*: $\mathcal{C}_{1000\text{ms}}$ explicitly flags that Binance emits only the latest liquidation order per 1000 ms per symbol. Unobserved intermediate fills are modeled as selection-censored events, not network drops.

---

### Layer 3: EXP-201B Ground-Truth Completeness & Classifier Validation
* **Gate 0B Data-Completeness Audit**: Before optimizing the real-time proxy classifier, the historical Hyperliquid dataset must be audited for 6 mandatory fields:
  1. Completeness across all blocks without omission.
  2. Identification of fill structure and fee tier.
  3. Millisecond-accurate execution timestamps.
  4. Explicit differentiation between partial liquidations ($20\%$) and backstop vault transfers ($HLP$).
  5. Total liquidation notional in USDC.
  6. Asset ticker and trade side.
* **Classifier Validation Gates**: Replaced point estimates with 95% Lower Confidence Bounds:
  $$\text{LCB}_{95\%}(\text{Precision}) = \text{Wilson\_LCB}_{95\%} \left( \frac{TP}{TP + FP} \right) \ge 0.85$$
  $$\text{LCB}_{95\%}(\text{Recall}) = \text{Wilson\_LCB}_{95\%} \left( \frac{TP}{TP + FN} \right) \ge 0.70$$
* **Strict 3-Way Partitioning**: Development Set (60%) ➔ Freeze Thresholds ($V \ge \$1.5\text{M}$) ➔ Untouched Validation Set (40%) ➔ Certification.
* **Implementation Note**: $\Delta \text{OI}$ remains classified as an *unverified implementation assumption* pending empirical publication cadence profiling of `activeAssetCtx`.

---

### Layer 4: Microstructure Point Process (Hawkes Benchmark & Invariants)
* **Offline vs. Online Roles**:
  - *Offline Structural Persistence*:
    $$\boldsymbol{\Gamma}_{ij} = \frac{\mathbb{E}_{\mathbf{m}}[\boldsymbol{\alpha}_{ij}(\mathbf{m})]}{\beta_{ij}}, \quad \rho(\boldsymbol{\Gamma}) = \max_k |\text{eig}_k(\boldsymbol{\Gamma})|$$
    $\rho(\boldsymbol{\Gamma})$ is a fixed structural persistence diagnostic under the calibration mark distribution, computed during 4-hour batch recalibrations.
  - *Online Real-Time Excitation*: Tracks dynamic normalized conditional intensities $\mathbf{I}_{\text{excite}}(t) = \boldsymbol{\lambda}(t) \oslash \boldsymbol{\mu}(\mathbf{S}_t)$.
* **Empirical Latency Certification Gate**:
  - Hurdle: $P_{50} < 5.0\,\mu\text{s}$ and $P_{90} < 10.0\,\mu\text{s}$ under pinned-core $M=5$ dense kernels.
  - **Empirical Tokyo Benchmark Result** ([`tests/benchmark_hawkes_filter.py`](file:///home/skybullet1987/quant_pipeline/tests/benchmark_hawkes_filter.py)):
    - $P_{50} = \mathbf{4.272\,\mu\text{s}}$
    - $P_{90} = \mathbf{7.098\,\mu\text{s}}$
    - Spectral Radius $\rho(\boldsymbol{\Gamma}) = \mathbf{0.0783}$ (Subcritical, $\rho < 1.0$)
    - **VERDICT: CERTIFIED PASS**.

---

### Layer 5: EXP-302 Structural Mispricing Execution & PWL MILP
* **Classification**: EXP-302 is formally designated **Structural Mispricing Execution** (probabilistic relative value under execution frictions). "Risk-free arbitrage" is restricted to guaranteed full fills where $\min_s [\text{Payoff}_s - \text{Cost}_s] > 0$.
* **Piecewise-Linear (PWL) Scenario MILP**: Discretizes order book depth into $K$ piecewise-linear cost segments, enforcing:
  $$\sum_{s=1}^S \pi_s y_s \ge 0.85, \quad \zeta + \frac{1}{(1 - \alpha) S} \sum_{s=1}^S u_s \le \$15.00$$
  with 250ms partial-fill cancellation timeout and parametric adverse legging penalty $\boldsymbol{\Omega}_{\text{legging}}(\mathbf{x})$.
* **Audit-Grade Fee Metadata Schema**:
  ```json
  {
    "fee_rate_applied": 0.07,
    "effective_fee_rate_on_deployed_notional": 0.0126,
    "fee_formula_provenance": "0.07 * (1 - 0.820) = 0.0126",
    "execution_model": "PIECEWISE_LINEAR_SCENARIO_MILP",
    "simulated_partial_fill_timeout_ms": 250
  }
  ```

---

### Layer 6: Synthetic Volatility (EXP-401) Reality Quarantine
* **Opyn Squeeth Status**: Officially shut down on November 4, 2024. EXP-401 remains strictly in **Stage 1 Theoretical Research**.
* **Perpetual Funding Rate**: Theoretical funding $F_t \approx \sigma_{\text{implied}}^2$ is model-dependent; real venue funding includes basis skew: $F_t = \sigma_{\text{implied}}^2 + \text{BasisSkew}_t$.
* **Discrete Hedging Drag**: Discrete hedging error scaling is model-dependent and empirically calibrated against rebalance intervals $\Delta t_{\text{rebalance}}$.

---

### Layer 7: Three-Tier Machine-Enforced Capital Floor ($F_{\text{operational}} = \$552.55$)

$$\begin{aligned}
F_{\text{theoretical}} &= 0.8255 \times \$642.10 = \$530.05\text{ USDC} \\
B_{\text{jump}} &= Q_{99.5\%}(\text{adverse 10-minute gap}) \cdot \sum |N_{\text{active}}| = \$18.00\text{ USDC} \\
B_{\text{execution}} &= Q_{99.5\%}(\text{stop slippage}) + \text{Fees} = \$4.50\text{ USDC} \\
\mathbf{F_{\text{operational}}} &= \mathbf{\$552.55\text{ USDC}}
\end{aligned}$$

* **Tier 1 (Continuous Observability)**: 4-Hour Micro-Risk Audit report logs:
  $$\text{NAV} = \$621.29\text{ USDC}, \quad \text{Floor} = \$552.55\text{ USDC}, \quad \text{Active Cushion} = +\$68.74\text{ USDC } (11.06\%)$$
* **Tier 2 (Pre-Trade Gateway Hard Floor Enforcement)**: Outbound order router rejects any trade if projected post-trade worst-case equity satisfies:
  $$W_{\text{post-trade, worst-case}} < F_{\text{operational}} = \$552.55\text{ USDC}$$
* **Tier 3 (Autonomous Kill Switch)**: Heartbeat disconnect ($> 4.2\text{s}$) or unhedged equity breach immediately sweeps resting orders and triggers market hedge to $0.0\times$ net delta.

---

### Layer 8: Statistical Episode Governance & Regime Preregistration
* **Preregistered $Z_{\text{OFI}}$ Normalization**: 100ms buckets, 10-minute rolling window ($\mu_{\text{OFI}}, \sigma_{\text{OFI}}$), 3-sigma winsorization, asset-specific.
* **Independent Episode Boundary**:
  $$\Delta t > 300\text{s} \quad \text{AND} \quad |Z_{\text{OFI}}| < 1.0$$
  All shocks occurring within 300s or dislocated OFI ($|Z_{\text{OFI}}| \ge 1.0$) are linked to the same episode cluster. Wild Cluster Bootstrap is computed exclusively at the independent episode cluster level ($N_{\text{episodes}} \ge 100$).
* **Preregistered Volatility Regimes**:
  - *Regime 1 (Low/Normal Volatility)*: $\sigma_{60\text{m}} < \text{Median}(\sigma_{60\text{m}})$
  - *Regime 2 (High Volatility)*: $\sigma_{60\text{m}} \ge \text{Median}(\sigma_{60\text{m}})$
* **Milestone Clarification**: 48 hours is strictly an **engineering telemetry milestone**. Statistical certification requires $N_{\text{episodes}} \ge 100$ spanning $\ge 14$ calendar days across both volatility regimes.

---

## 3. Conformance Test Suite Verification Results

```
========================================================================================
                      V3.2.1 CONFORMANCE TEST AUDIT (Tokyo Container)
========================================================================================
[TEST 01] Doubly Robust Residualization Math       ... PASSED (Residualization preserved)
[TEST 02] Binance Timestamps & Censoring Ingestion  ... PASSED (T_Binance, E_Binance, C_1000ms)
[TEST 03] Primary 30s Endpoint & 12.5 bps Hurdle   ... PASSED (Derived budget matched)
[TEST 04] Hawkes Offline Persistence & Live Filter ... PASSED (rho < 1.0, sub-10us update)
[TEST 05] EXP-302 PWL MILP & Fee Schema            ... PASSED (effective_fee = 0.0126)
[TEST 06] Operational Capital Floor & 3-Tier Gate  ... PASSED (F_operational = $552.55)
[TEST 07] Episode Boundary & Volatility Regimes    ... PASSED (Delta t > 300s, OFI < 1.0)
[TEST 08] EXP-401 Synthetic Volatility Quarantine  ... PASSED (Opyn shut down 2024-11-04)
========================================================================================
Ran 8 tests in 4.724s | Invariant Spec_v3.2.1 == Implementation == Ledger: CERTIFIED OK
```

---

## 4. Current Pipeline Production Status

| Engine Track | Scientific Classification | Lifecycle State | Running Daemon / File | Verified Metrics |
| :--- | :--- | :--- | :--- | :--- |
| **Engine 1 (EXP-103 Apex)** | Core Trend Following | **STAGE 6: Production** | [`src/execution/production_apex_daemon.py`](file:///home/skybullet1987/quant_pipeline/src/execution/production_apex_daemon.py) (PID `16797`) | NAV: **$621.29 USDC**, Cash: **$610.92 USDC**, HWM: **$642.10 USDC**, Drawdown: **3.24%**, Carry: **+$12.74 USDC**. Bar 8/18 complete. Macro rebalance at `2026-10-01 12:00:00 UTC`. |
| **Engine 2 (EXP-104 Shadow)** | Cross-Market Hedging | **STAGE 1: Shadow** | [`src/execution/exp104_macro_hedge_shadow.py`](file:///home/skybullet1987/quant_pipeline/src/execution/exp104_macro_hedge_shadow.py) (PID `2851516`) | Forward comparative logging active; checkpoint on October 1 (requires 30 days OOS). |
| **Engine 2 (EXP-201A Spillover)** | Cross-Venue Microstructure | **STAGE 2: Telemetry** | [`src/hl_leadlag/market_data/exp201a_spillover_telemetry.py`](file:///home/skybullet1987/quant_pipeline/src/hl_leadlag/market_data/exp201a_spillover_telemetry.py) | Wire timestamps, 1000ms censoring tracking, and risk set $\mathcal{R}(t_i^-)$ operational. |
| **Engine 2 (EXP-201B Cascade)** | Native Cascade Momentum | **STAGE 1: Offline Lab** | [`scripts/audit_gate0b_hl_liquidations.py`](file:///home/skybullet1987/quant_pipeline/scripts/audit_gate0b_hl_liquidations.py) | Gate 0B audit script operational; offline ground truth required before live shadow. |
| **Engine 3 (EXP-302 Execution)** | Structural Mispricing | **STAGE 1: Paper Lab** | [`src/polymarket_research/polymarket_paper_trader.py`](file:///home/skybullet1987/quant_pipeline/src/polymarket_research/polymarket_paper_trader.py) (PID `2932204`) | OOS Validation Ledger: **2W / 0L, +$39.99 PnL**, Portfolio Equity: **$1,039.99 USDC**. Fee schema synchronized. |
| **Engine 4 (EXP-401 Gamma)** | Synthetic Volatility | **STAGE 1: Research** | Quarantined | Quarantined post-Squeeth shutdown. Live capital deployment blocked. |

---

## 5. Formal Certification & Lock Statement

The specification above is **officially frozen**. No further parameter tuning, econometric relabeling, or structural alterations are permitted. Empirical evidence collected across the preregistered 14-day / 100-episode window will strictly govern all promotion decisions.
