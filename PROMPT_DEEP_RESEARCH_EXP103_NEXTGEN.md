# INSTITUTIONAL QUANTITATIVE RESEARCH DIRECTIVE: NEXT-GENERATION EXP-103 (EXP-104 SOVEREIGN FRONTIER)

**Document Type:** Deep Research Directive & Algorithmic Architecture RFP  
**Target Venue:** Hyperliquid Layer 1 Derivatives Protocol (CLOB Perpetuals, USDC Margin)  
**Execution Kernel Standard:** IronCore v2.4.0 Frozen $E_3$ Causal Physics Standard  
**Accounting Standard:** Exact 6-Bucket Mark-to-Market Ledger ($0.000000000000 Discrepancy)  
**Core Reference Strategy:** EXP-103 (The 10x+ Convex Compounding Architecture)  
**Accompanying Research Attachment:** `MASTER_RESEARCH_AND_BACKTESTS_COMPENDIUM.md`  

---

## 1. Executive Mission Brief & Research Mandate

### 1.1 The Quantitative Mission
The objective of this research directive is to advance the production-certified **EXP-103 Convex Compounding Architecture** into its next-generation evolutionary standard (**EXP-104 / Sovereign Frontier**). 

The mission is to solve the classic frontier dilemma in high-geared systematic crypto perpetuals:
$$\max_{\mathbf{w}_t, \mathcal{M}, \mathcal{R}} \mathbb{E}\left[ \ln\left(\frac{W_T}{W_0}\right) \right] \quad \text{subject to} \quad \max_{t \in [0,T]} \text{DD}_t \le 20.0\% \text{ to } 25.0\%, \quad \text{Sharpe} \ge 3.00, \quad \frac{W_T}{W_0} \ge 10.0\times$$
evaluated under strictly causal, hostile execution physics (IronCore v2.4.0 $E_3$).

### 1.2 Baseline Ground Truth: EXP-103 Certified Empirical Realization
In audited 365-calendar-day backtests across 2,190 consecutive 4-hour bars (177 Hyperliquid perpetual assets, September 4, 2025 – September 4, 2026 UTC), **EXP-103 achieved historic headline compounding**:
- **Initial Capital Base:** $10,000.00 USDC
- **Terminal Portfolio Equity:** **$113,596.45 USDC** (+1,035.96% Net Cumulative Return, **11.36x Equity Multiple**)
- **Annualized Net CAGR:** **+1,035.96%**
- **Annualized Sharpe Ratio:** **2.42** (Sortino: **3.48**)
- **Calmar Ratio:** **13.44**
- **Peak Portfolio Equity:** **$230,546.63 USDC (23.05x Peak Multiple)**
- **Accounting Discrepancy:** **$0.000000000044** (Certified Zero Numerical Leakage across all 6 balance sheet buckets)
- **Hyperliquid L1 Consensus Invariants:** 0 violations ($\le 5$ sig figs, $\le 6-\text{szDecimals}$ price precision, $\ge \$10.00$ notional).

### 1.3 The 4 Critical Pathologies of EXP-103 Requiring Deep Research

Despite hitting the 10x net target, forensic decomposition of EXP-103 reveals four major vulnerabilities:

1. **Catastrophic Max Drawdown & Peak Giveback (The 49.3% Collapse):**
   - After surging to **$230,546.63 (23.05x)**, the portfolio suffered a brutal **-49.3% peak-to-trough giveback** (-$116,950.18 USDC), resulting in a realized **Max Drawdown of 77.08%**.
   - *The Research Objective:* Cut Max Drawdown from **77.08% down to $\le 20.0\% - 25.0\%$** and compress peak giveback to $< 10.0\%$, while capturing the run to $23x+$. Preventing the $117k drawdown cliff alone would yield an ending equity of **$\ge \$200,000.00+ (20x+)$** without taking additional risk.

2. **The Circuit Breaker Whipsaw Trap (Negative Breaker Convexity):**
   - The baseline deterministic circuit breaker tripped on **747 out of 2,190 bars (34.1% occupancy)** across 103 discrete events (median duration: 6 bars).
   - Dumping 100% risk to cash at the open of cascade bars and rebuying unhedged 1–2 bars later caused **-$34.95 net breaker destruction** and incurred **$895.18 in unnecessary execution friction**.
   - *The Research Objective:* Replace binary cash liquidation with an continuous **Adaptive Beta Hedge & Asymmetric Basis Buffer (Arm B5)** that dampens systemic drawdown without paying roundtrip crossing friction.

3. **Outer Holdout Alpha Decay in Walk-Forward Optimization (WFO):**
   - In Combinatorial Purged Cross-Validation (CPCV) and Nested Walk-Forward Optimization, the in-sample Sharpe of 2.42 decayed to an **outer holdout fold Sharpe of 0.28** (worst fold: -2.28, median fold: 0.94).
   - *The Research Objective:* Elevate outer holdout Sharpe to $\ge 1.50+$ across all cross-validation splits through robust spectral factor regularizers (Marchenko-Pastur RMT, Ledoit-Wolf shrinkage, and rank hysteresis).

4. **Sizing Inefficiency & Vaulting Tradeoff:**
   - In Milestone Vaulting (Configuration 7), locking profits capped Max Drawdown at **24.8%** and lifted Sharpe to **3.30** (Calmar 19.16), but capped terminal equity at **$47,660.10 (4.77x)**.
   - In Unconstrained Gearing (EXP-103), compounding at 3.0x produced **$113,596.45 (11.36x)** but endured a **77.08% drawdown**.
   - *The Research Objective:* Bridge this gap. Develop an **Anti-Martingale Active Reserve Compounding Architecture** that achieves the **>10x–20x compounding** of EXP-103 with the **<25% drawdown and >3.3 Sharpe** of Milestone Vaulting.

---

## 2. Updated Backtest Methodology & IronCore v2.4.0 Physics Standard

All proposed models, equations, and strategies **must strictly comply** with the audited IronCore v2.4.0 $E_3$ causal execution physics documented in the attached `MASTER_RESEARCH_AND_BACKTESTS_COMPENDIUM.md`:

### 2.1 The 6 Physical Laws of IronCore v2.4.0 ($E_3$)
1. **Next-Subbar Execution:** Signals calculated on bar $t$ close (timestamp $T_t$) are strictly routed and filled at the opening subbar of bar $t+1$. **Zero current-bar lookahead**.
2. **4-Phase OHLC Subbar Dissection:** Each 4-hour bar is decomposed into 4 discrete subbar segments:
   $$\text{Open} \longrightarrow \text{Extremum}_1 \longrightarrow \text{Extremum}_2 \longrightarrow \text{Close}$$
   where $\text{Extremum}_1$ is High (if Bullish bar) or Low (if Bearish bar). Intra-bar wicks are simulated causally.
3. **Worst-Case Intra-Bar Stop Gap Slippage:** Intra-bar stops do NOT receive the trigger price. If an asset's subbar Low breaches the stop level, it executes at the worst-case price of the subbar wick penalized by an adverse gap:
   $$P_{\text{fill}} = \min(P_{\text{stop}}, P_{\text{low}}) \times (1 - \text{Slippage Gap}), \quad \text{where } \text{Slippage Gap} \sim 10\text{ to } 25\text{ bps}$$
   (All historical lookahead stop-immunity is permanently banned).
4. **Take-Profit Penetration Invariant:** Limit TP orders are only filled if the market price penetrates the TP limit price by at least **$+1.5\text{ bps}$**, verifying queue seniority.
5. **Hyperliquid Fee & Market Impact Drag:**
   - Maker (Post-Only ALO): $-1.18\text{ bps}$ rebate to $+1.5\text{ bps}$ fee.
   - Taker (IOC / Stop-loss / Spread crossing): $+2.5\text{ bps}$ to $+4.5\text{ bps}$.
   - Square-root market impact: $\Delta P_{\text{impact}} = \eta \cdot \sigma_i \cdot \sqrt{\frac{\text{Notional}}{\text{24h ADV}_i}}$.
   - Effective roundtrip friction: **$\approx 30.0\text{ bps}$** per position turnover.
6. **Strict 6-Bucket Balance Sheet Ledger Conservation:**
   $$\Delta\text{NAV}_t = \text{Gross Price PnL}_t + \text{Funding PnL}_t - \text{Exchange Fees}_t - \text{Market Impact}_t - \text{Adverse Selection}_t - \text{Realized Stop Slippage}_t$$
   Audited to exact zero discrepancy: $|\epsilon| < 10^{-10}\text{ USDC}$.

### 2.2 Hyperliquid L1 Consensus Quantization Invariants
- Price precision: $\le 5$ significant figures AND $\le (6 - \text{szDecimals})$ decimal places.
- Base size precision: Floored strictly to $\text{szDecimals}$ (no upward rounding).
- Minimum order notional: $\ge \$10.00\text{ USDC}$ (strictly rejected by L1 Tendermint node if $<\$10.00$).

---

## 3. Structural Pillars of Baseline EXP-103 (Starting Architecture)

Deep research must build directly upon the validated mathematical modules of EXP-103:

1. **Signal Stationarity & Memory:** Rate-of-change Fractional Differentiation ($d^* = 0.38$, Memory $H=18$ bars) preserves multi-day price memory while enforcing Augmented Dickey-Fuller stationarity ($p < 0.01$).
2. **Orthogonal Residual Momentum:** Multi-beta OLS Ridge regularizer orthogonalizes token returns against BTC and ETH benchmarks; filtered by Asymmetric Frog-in-the-Pan (FIP) to penalize jump-driven spikes.
3. **Microstructure Gate & Jump Disentanglement:** Continuous Bipower Variation ($BV_t$) isolates continuous Gaussian diffusion $\sigma_{\text{cont}}$ from Poisson jumps $J_t$; filters out assets with Hurst exponent $H < 0.50$ or Variance Ratio $VR(6) < 1.0$.
4. **Cadence Decoupling & Turnover Compression:**
   - **Macro Allocation Grid:** Target weights update on a **72-hour cycle (18 4H bars)**.
   - **Micro Risk Grid:** Intra-bar stops, funding carry, and PnL settle every **4 hours**.
   - **Leland Turnover Deadband:** Rebalancing shifts $|\Delta w_i| < \tau_0 = 300\text{ bps}$ are suppressed.
   - **Dual-Barrier Rank Hysteresis:** Entry when rank $R_i \le K_{\text{in}} = 8$; retention while $R_i \le K_{\text{out}} = 14$.
   - **Dynamic Holding Lock:** 48H to 72H minimum dwell time to prevent intra-cycle churn.
5. **Grossman-Zhou (GZ) Dynamic Gearing:** Operating leverage $L_t \in [1.0x, 3.5x]$ scales with cushion $C_t = \frac{\text{NAV}_t - 0.80 \cdot \text{HWM}_t}{0.20 \cdot \text{HWM}_t}$.
6. **Two-Tranche Vaulting:** Tranche A (60% NAV: carry & preservation) and Tranche B (40% NAV: unconstrained runner with milestone profit sweeps).

---

## 4. Key Empirical Scoreboard Comparison (To Exceed & Refine)

Your proposals must benchmark against the audited factorial scoreboard from the Master Backtest File:

| Architectural Configuration | Operating Leverage | Terminal Equity ($10k Base) | Net Multiple | Net CAGR | Sharpe Ratio | Max Drawdown | Calmar Ratio | Peak Giveback | Core Failure / Advantage |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Unlevered Baseline 1X** | 1.0x | $20,195.11 | 2.02x | +101.95% | 1.21 | 62.04% | 1.64 | 37.5% | No gearing; high baseline drawdown |
| **Compounding Intermediate** | 2.0x | $56,027.32 | 5.60x | +460.27% | 2.00 | 75.58% | 6.09 | 44.2% | High convexity; unhedged cascade drag |
| **EXP-103 Benchmark (Baseline)** | **3.0x** | **$113,596.45** | **11.36x** | **+1,035.96%** | **2.42** | **77.08%** | **13.44** | **49.3%** | **Peak $230k; brutal 49.3% giveback** |
| **Milestone Vaulting Core (Config 7)**| Dynamic | $47,660.10 | 4.77x | +376.60% | **3.30** | **24.80%** | **19.16** | **6.4%** | **Floor preserved (<25% DD), but capped at 4.77x** |
| **EXP-104 Research Target** | **Dynamic [1.5x–3.5x]** | **$\ge \$150,000+$** | **$\ge 15.0\times$** | **$\ge +1,400\%$** | **$\ge 3.00$** | **$\le 20.0\%–25.0\%$** | **$\ge 25.0$** | **$\le 10.0\%$** | **Convex 15x+ run with <25% DD floor** |

---

## 5. Five Deep Research Vectors & Technical Inquiries

We require a rigorous, code-level mathematical deep dive across the following five quantitative vectors:

### VECTOR 1: Anti-Giveback Architecture & Asymmetric Peak-Profit Vaulting
- **The Problem:** EXP-103 reached $230,546.63 before shedding $117k in the subsequent crypto correction. The Grossman-Zhou cushion collapsed because leverage did not de-gear fast enough from the historical high-water mark.
- **Deep Research Mandate:**
  1. Formulate a **Continuous Ratcheted High-Water Mark ($HWM^*_t$)** with asymmetrical lookback decay:
     $$HWM^*_t = \max\left( \text{NAV}_t, \; (1 - \delta) HWM^*_{t-1} + \delta \text{NAV}_t \right)$$
  2. Design an **Anti-Martingale Profit Sweeping Protocol** that dynamically splits compounding gains into:
     - *Risk Reserve (Vaulted, Zero-Beta)*: Deposited into an untouchable synthetic cash or basis-carry yield sleeve.
     - *Active Compounder*: Scaled to maintain constant dollar-risk rather than constant leverage-percentage risk as NAV increases.
  3. Formulate the mathematical conditions under which Peak Giveback is strictly bounded by $\le 10.0\%$ while keeping compounding velocity open to exponential right-tail surges.

### VECTOR 2: Arm B5 Cooldown Gate & Dynamic Beta-Hedging (Eliminating the Whipsaw Trap)
- **The Problem:** Binary circuit breakers dumping 100% risk to cash suffered 103 false trips, -$34.95 net destruction, and $895 friction drag.
- **Deep Research Mandate:**
  1. Formulate **Arm B5: Cooldown Gate + Continuous Beta Overlay**:
     - When Open Interest Velocity $V_{OI} < -10\%$ or Basis Dispersion $D_{\text{basis}} > 2.5\sigma$, instead of closing altcoin longs, immediately enter a short BTC/ETH perpetual overlay:
       $$w_{\text{hedge}, \text{BTC}}(t) = -\sum_{i=1}^N \beta_i(t) \cdot w_i(t)$$
     - Model the transaction cost differential: closing 10 illiquid altcoins (paying 5–10 bps taker spread + impact) versus executing 1 liquid BTC perp hedge (paying 1.5 bps maker / 2.5 bps taker).
  2. Derive an **Asymmetric Volatility Expansion Trigger**: Distinguish between healthy market trend flushes (where longs should be held) and toxic structural liquidations (where hedging is mandatory).

### VECTOR 3: Precision Position Exit Surfaces & Parabolic Volatility Ratchets
- **The Problem:** EXP-103 held winning positions for 72H fixed windows. High-flying tokens frequently ran +35% in 24 hours, only to retrace to +5% by the 72H macro boundary.
- **Deep Research Mandate:**
  1. Formulate a **Multi-Tiered Dynamic Exit Surface**:
     - *Tier 1: Bipower Variation Diffusion Stop*: $\text{Stop}_i = P_{\text{entry}} - \max(2.5 \sigma_{\text{cont}, i}, 2.0\text{ATR})$.
     - *Tier 2: Asymmetric Profit-Harvesting Split*: When unrealized gain reaches $+2.0\text{ATR}$, automatically harvest 50% of the position as maker liquidity (`Alo`), moving the stop on the remaining 50% to Breakeven $+ 0.25\text{ATR}$.
     - *Tier 3: Parabolic Acceleration Runner*: On the remaining tranche, trail with an accelerating Chandelier ratchet:
       $$k(t) = k_0 \cdot \exp\left(-\alpha \frac{P_{\text{high}} - P_{\text{entry}}}{\text{ATR}}\right) + k_{\min}, \quad k_{\min} = 0.50$$
  2. Prove mathematically that this increases the realized Win/Loss payout ratio $\bar{W}/\bar{L}$ from 2.42 to $\ge 3.50+$, and calculate the exact trade expectancy net of 30 bps roundtrip friction.

### VECTOR 4: Dynamic Capital Reallocation & Funding Carry Squeeze Optimization
- **The Problem:** Crypto perpetual markets display extreme cross-sectional funding dislocations ($F_t < -100\%\text{ APR}$ during short-crowded bottoms, $F_t > +100\%\text{ APR}$ during retail mania).
- **Deep Research Mandate:**
  1. Formulate a **True Layer 1 Funding Carry & Squeeze Sizing Model**:
     - Dynamic carry tilt: adjust asset weight $w_i^*$ proportional to $-F_{\text{hourly}, i} / \sigma_i$.
     - Negative funding squeeze booster: when $F_{\text{hourly}} < -0.0008$ and $\Delta\text{OI}_{24\text{h}} > +15\%$, allocate a high-conviction convex kicker to capture the squeeze while collecting $+100\%\text{ APR}$ carry.
     - Crowded long veto: strictly prohibit entering long positions on assets with $F_{\text{hourly}} > +0.0012$ (+105% APR) regardless of momentum rank.
  2. Reconcile funding settlements with Hyperliquid’s actual 1-hour periodic funding cycle.

### VECTOR 5: Out-of-Sample Overfitting Immunization & Walk-Forward Stability
- **The Problem:** WFO outer-fold Sharpe collapsed to 0.28 due to factor rank instability and parameter hypersensitivity.
- **Deep Research Mandate:**
  1. Propose advanced factor regularizers:
     - **Marchenko-Pastur Spectral Denoising (RMT)**: Filter eigenvalue spectrum of the correlation matrix, stripping out noise eigenvalues below $\lambda_{\max} = \sigma^2(1 + \sqrt{N/T})^2$.
     - **Hierarchical Tree Clustering / Equal Risk Contribution (ERC)**: Replace naive inverse-volatility sizing with risk parity over denoised hierarchical clusters.
  2. Formulate **Adversarial Hyperparameter Sensitivity Bounds**: Verify that perturbations of $\pm 20\%$ to parameters ($d^*$, $K_{\text{in}}$, $K_{\text{out}}$, $\tau_0$, $M$, $L_{\max}$) produce $<10\%$ variance in ending Sharpe.

---

## 6. Deliverable Format & Specifications

Your final research output must be structured as an **Institutional Implementation Blueprint** containing:

1. **Executive Summary & Mathematical Formulations:** Explicit LaTeX equations for all new signals, regularizers, exit surfaces, and leverage governors.
2. **Step-by-Step State Machine Pseudocode & Architecture:** Complete Python dataclasses and execution state transitions (`IDLE`, `ENTER_PENDING`, `OPEN_ACTIVE`, `HARVESTED_RUNNER`, `HEDGED_PROTECTED`, `EXIT_PENDING`).
3. **Hyperparameter Pre-Registration Table:** Clear parameter boundaries, defaults, and physical rationale.
4. **Projected Comparative Scoreboard:** Estimated performance metrics (CAGR, Sharpe, Max DD, Calmar, Turnover, Peak Giveback) under IronCore v2.4.0 $E_3$ causal physics.
5. **Code Migration Roadmap:** Concrete file-by-file modifications required across `src/strategy/convex_10x_engine.py`, `backtest_10x_convex_compounding.py`, and `src/execution/production_apex_daemon.py`.

*Note: You may cross-reference any empirical findings, factor formulas, or benchmark scoreboards directly from the attached `MASTER_RESEARCH_AND_BACKTESTS_COMPENDIUM.md`.*
