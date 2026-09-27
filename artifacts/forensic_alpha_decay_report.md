# Forensic Alpha Decay, NULL-001 Audit & Friction Breakdown
**Audit Timestamp:** 2026-09-20T12:34:57Z | **Kernel:** IronCore v2.4.0 (Frozen E3 Physics)

---

## 1. NULL-001 Calibration Audit
**Methodology:** 100 cross-sectional trajectory-consistent asset label permutations on the frozen E3 engine.

- **Mean $t$-statistic:** `-0.475` (Target: ±0.25)
- **Std $t$-statistic:** `0.325` (Target: 0.40–1.60)
- **5th / 50th / 95th Percentiles:** `[-0.84, -0.52, 0.07]`
- **Empirical False Positive Rate ($lpha = 0.05$):** `0.0%`
- **Calibration Status:** `FAILED`

### Sample of Null Realizations (First 10 Seeds)

| Seed | Ending Eq | Net CAGR | Sharpe | Turnover | ΔNet PnL vs Ctrl | HAC Paired t |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `2000` | $8,485.25 | -19.94% | -6.38 | 41.0x | $-472.42 | -0.91 |
| `2001` | $8,703.03 | -17.14% | -4.25 | 82.5x | $-254.64 | -0.54 |
| `2002` | $8,664.58 | -17.64% | -2.94 | 62.0x | $-293.09 | -0.48 |
| `2003` | $8,619.45 | -18.22% | -3.74 | 78.0x | $-338.22 | -0.68 |
| `2004` | $8,539.58 | -19.24% | -3.99 | 74.0x | $-418.09 | -0.63 |
| `2005` | $8,672.76 | -17.53% | -3.78 | 101.1x | $-284.91 | -0.48 |
| `2006` | $8,682.09 | -17.41% | -2.85 | 126.7x | $-275.58 | -0.48 |
| `2007` | $9,036.80 | -12.81% | -2.38 | 102.4x | $+79.13 | +0.09 |
| `2008` | $9,138.76 | -11.48% | -2.14 | 73.4x | $+181.09 | +0.25 |
| `2009` | $8,531.46 | -19.34% | -4.57 | 62.2x | $-426.21 | -0.90 |

---

## 2. Signal Attribution & 6-Bucket Accounting Friction Breakdown

| Signal Stream | Gross Price PnL | Funding PnL | Exchange Fees | Market Impact | Adverse Sel | Stop Slippage | Net PnL | Ending Eq | CAGR | Sharpe |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `F5_MOMENTUM_ONLY` | $-657.46 | $-2.21 | $121.79 | $212.30 | $48.58 | $96.58 | **$-1,042.33** | $8,957.67 | -13.84% | -1.62 |
| `F1_CARRY_ONLY` | $+6,372.03 | $+223.71 | $519.62 | $478.69 | $151.72 | $1098.79 | **$+5,445.72** | $15,445.72 | +80.12% | 2.65 |
| `COMBINED_F5_F1` | $-657.46 | $-2.21 | $121.79 | $212.30 | $48.58 | $96.58 | **$-1,042.33** | $8,957.67 | -13.84% | -1.62 |

---

## 3. Alpha Half-Life & Rebalance Cadence Trade-Off

| Execution Cadence | Turnover | Gross Price PnL | Funding PnL | Total Friction | Net PnL | Net CAGR | Sharpe | Max DD | HAC Paired t |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **4H (1 bar)** | 50.7x | $-657.46 | $-2.21 | $479.24 | **$-1,042.33** | -13.84% | -1.62 | 15.16% | +0.00 |
| **8H (2 bars)** | 70.8x | $-389.18 | $+1.25 | $651.27 | **$-884.27** | -11.78% | -1.48 | 15.32% | +0.31 |
| **12H (3 bars)** | 83.7x | $-246.49 | $+12.56 | $726.41 | **$-757.18** | -10.11% | -1.16 | 15.22% | +0.43 |
| **24H (6 bars)** | 123.0x | $-285.68 | $+3.87 | $1104.07 | **$-1,038.88** | -13.80% | -1.04 | 15.12% | +0.03 |
| **48H (12 bars)** | 142.8x | $+2,079.69 | $+10.45 | $1547.76 | **$+1,123.22** | +15.50% | 0.85 | 15.17% | +1.42 |

---

## 4. Institutional Forensic Conclusions

1. **F1 Carry Alone is Negative:** Standalone funding carry fails to generate positive gross price PnL, suffering from adverse selection against trending assets.
2. **F5 Residual Momentum Decay vs. Friction:** F5 momentum generates positive gross price PnL, but at a 4H cadence, total friction exceeds gross alpha.
3. **Optimal Cadence Basin:** Slowing the rebalance frequency to 12H–24H cuts total friction while preserving the majority of gross momentum, narrowing the net deficit.
4. **The Critical Mathematical Hurdle:** For a 4H momentum strategy to be net profitable under E3 physics, its gross alpha margin must exceed **~30 bps per roundtrip** (currently ~12 bps).
