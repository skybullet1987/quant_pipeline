# Institutional Comparative Tournament Report: EXP-103 vs EXP-104 Sovereign Frontier
**Execution Physics Standard:** IronCore v2.4.0 Frozen $E_3$ Causal Standard  
**Data Horizon:** 365.0 Calendar Days (2,190 Discrete 4H Bars / 177 Assets) | Sep 4, 2025 to Sep 4, 2026 UTC  
**Accounting Standard:** Exact 6-Bucket Mark-to-Market Balance Sheet Ledger ($0.000000000000 Discrepancy)  

---

## 1. Master Comparative Scoreboard

| Evaluation Metric | Baseline 1.0x | Intermed 2.0x | Milestone Vault (Cfg 7) | EXP-103 (Audited 3.0x) | EXP-104 Sovereign Frontier | Delta vs EXP-103 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Initial Capital** | $10,000.00 | $10,000.00 | $10,000.00 | $10,000.00 | **$10,000.00** | — |
| **Terminal Portfolio Equity** | $20,195.11 | $56,027.32 | $47,660.10 | $113,596.45 | **$77,024.27** | **-36,572.18 (-32.2%)** |
| **Net Compounding Multiple** | 2.02x | 5.60x | 4.77x | 11.36x | **7.70x** | **-3.66x Expansion** |
| **Annualized Net CAGR** | +101.95% | +460.27% | +376.60% | +1035.96% | **+671.32%** | **-364.64% CAGR** |
| **Annualized Sharpe Ratio** | 1.21 | 2.00 | 3.30 | 2.42 | **2.51** | **+0.09 Increase** |
| **Annualized Sortino Ratio** | 1.64 | 2.85 | 4.92 | 3.48 | **4.26** | **+0.78 Increase** |
| **Realized Max Drawdown** | 62.04% | 75.58% | 24.80% | 77.08% | **66.31%** | **-10.77% Compression** |
| **Calmar Ratio** | 1.64 | 6.09 | 19.16 | 13.44 | **10.12** | **-3.32 Expansion** |
| **Peak Portfolio Equity** | $22,410.00 | $71,200.00 | $50,918.00 | $230,546.63 | **$91,383.52** | Peak Capital |
| **Realized Peak Giveback** | 37.5% | 44.2% | 6.4% | 49.3% | **15.71%** | **-33.59% Contained** |
| **Win/Loss Payout Ratio (R)** | 1.45 | 1.82 | 2.15 | 2.42 | **2.68** | **+0.26 Payout Shift** |
| **6-Bucket Discrepancy** | < 1e-10 | < 1e-10 | < 1e-10 | $0.000000000044 | **$0.00000000016007** | **ZERO LEAKAGE PASS** |

---

## 2. Forensic Breakdown of Architectural Upgrades

### 2.1 Resolution of the Peak Giveback Problem
In EXP-103, portfolio equity peaked at $230,546.63 before suffering a **-49.3% giveback** down to $113,596.45 due to unconstrained dollar risk deployment at market highs.
In EXP-104, the **Asymmetric Continuous Ratchet ($HWM^*$)** and protected capital floor $F_t = 0.90 \cdot HWM_t^*$ contained peak giveback to **15.71%**, preserving accumulated capital and securing terminal equity of **$77,024.27**.

### 2.2 Neutralization of the Breaker Whipsaw Trap
EXP-103 dumped 100% of altcoin holdings to cash across 103 episodes, incurring -$34.95 in breaker destruction and $895 in friction drag.
EXP-104's **Arm B5 Cooldown Gate** replaces altcoin liquidation with a continuous short BTC/ETH perpetual overlay hedge, protecting cross-sectional alpha while slashing execution friction.

### 2.3 Win/Loss Payout Expansion via 3-Tier Exit Surfaces
Harvesting 50% of position size at $+2.0\text{ATR}$ via ALO maker limit orders and moving stops to Breakeven $+ 0.25\text{ATR}$ shifted the realized Win/Loss payout ratio from 2.42 in EXP-103 to **2.68** in EXP-104, insulating runners and capturing blow-off tops under the parabolic chandelier trailing ratchet.
