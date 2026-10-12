# Research Report: PM-HWR-001 — High-Confidence Polymarket Trading
## Addendum: Full Research-Accounting Reconciliation & Adversarial Audit

**Campaign Identifier**: `PM-HWR-001` (incorporating `PM-HWR-001A` & `PM-HWR-001B`)  
**Execution Timestamp**: `2026-10-12T14:47:00Z`  
**Git Commit**: [`53c8c0f`](https://github.com/skybullet1987/quant_pipeline/commit/53c8c0f)  
**Safety Invariant**: READ-ONLY RESEARCH. Live production configuration maintained strictly unchanged.  

---

## 1. Executive Summary & Audited Verdict

| Metric / Gate | Pre-Registered Standard | Empirical Outcome | Reconciliation Status |
| :--- | :--- | :--- | :--- |
| **Held-Out Observed Win Rate** | $\ge 95.0\%$ | **100.0%** (CAND_B1) / **77.27%** (Baseline) | **Inconclusive (sample constrained)** |
| **Held-Out Sample Size ($N$)** | $\ge 300$ qualifying trades | **$N = 1$ to $22$ qualifying trades** | ❌ **FAIL (Severe Sample Deficit)** |
| **Statistical Confidence (95% CI)** | Lower Bound $> 90.0\%$ | **Lower Bound: 20.65%** ($N=1$) / **56.56%** ($N=22$) | ❌ **FAIL (Confidence band too wide)** |
| **Net Expected Value ($\mathbb{E}$)** | $>\$0.00$ after fees | **+$4.92** ($N=1$) / **-$1.20** ($N=22$) | **Conditional on early stop loss** |
| **Late-Candle Orderbook Pricing** | Executable ask $\le 0.94$ | Asks at $z \ge 2.0$ trade at **$0.9993$** | ❌ **Path 1 Refuted by Microstructure** |
| **EXP-302 Baseline PnL Arithmetic** | $N_{\text{win}} \cdot W - N_{\text{loss}} \cdot L = \text{PnL}$ | $226(\$16.92) - 46(\$50.77) = \mathbf{+\$1,488.36}$ | ✅ **100% Reconciled to exact cent** |
| **Polymarket Fee Formula** | $C \cdot 0.07 \cdot p \cdot (1 - p)$ | Confirmed Quadratic in Executor & Tests | ✅ **100% Reconciled** |
| **EXP-303 Policy B2 Audit** | Adversarial fill simulation | 100% claim debunked; realistic WR is **83.1%** | ✅ **Flaw Uncovered & Fixed** |
| **Regression Test Pass Rate** | 100% Pass Rate | **5 / 5 passed** in `test_pm_hwr_001_invariants.py` | ✅ **PASS** |

### **FINAL CAMPAIGN VERDICT: `INSUFFICIENT EVIDENCE`**

---

## 2. Issue A: EXP-302 Baseline PnL Arithmetic Reconciliation

The apparent discrepancy between the reported average win/loss and net PnL was resolved by auditing the trade records in [`data/polymarket/paper_trading_validation_ledger.jsonl`](file:///home/skybullet1987/quant_pipeline/data/polymarket/paper_trading_validation_ledger.jsonl):

* **Total Validation Trades**: **272**
* **Settled Wins**: **226** (83.09%)
* **Settled Losses**: **46** (16.91%)
* **Sum of Winning PnLs**: **+$3,823.65**
  $$\text{Actual Average Win } (W) = \frac{+\$3,823.65}{226} = \mathbf{+\$16.9188 \approx +\$16.92}$$
* **Sum of Losing PnLs**: **-$2,335.29**
  $$\text{Actual Average Loss } (|L|) = \frac{-\$2,335.29}{46} = \mathbf{-\$50.7672 \approx -\$50.77}$$
* **Net PnL Tie-Out**:
  $$\text{Net PnL} = 226 \times (+\$16.9188) - 46 \times (\$50.7672) = \$3,823.65 - \$2,335.29 = \mathbf{+\$1,488.36}$$

> [!NOTE]
> The machine-readable JSON report ([`stage1_2_audit_baseline_report.json`](file:///home/skybullet1987/quant_pipeline/data/pm_hwr_001/stage1_2_audit_baseline_report.json)) recorded `avg_win_usd: 16.92` and `avg_loss_usd: -50.77` correctly. The earlier markdown draft contained an inadvertent copy-paste of `$10.22` and `-$34.80` from an earlier normalized per-share scratchpad. The arithmetic ties out to the exact cent.

---

## 3. Issue B: Live Fill-Level Ledger Reconciliation

The 20 live real-money trades were reconciled directly against all 77 raw execution fills in [`data/polymarket/clob_raw_trades.json`](file:///home/skybullet1987/quant_pipeline/data/polymarket/clob_raw_trades.json).

### **Root Cause of the 12.80 / 12.90 Share Discrepancy**
* In the Round 2 auditor table, the **sum of listed rows** totaled **756.33 buy shares** and **697.65 sell shares**.
* The **summary row** listed **769.13 buy shares** and **710.55 sell shares**.
* **Origin**: The summary row included unrounded internal precision from multi-leg sweep dust and a pre-quantization sizing estimate on Trade #15 (`5483810`, 16.05 shares vs 12.80 initial limit quote) before the rest was rejected.
* **Current Authoritative CLOB Match**: Every closed position in `live_harvester_state.json` now maps to CLOB fills with $\Delta = 0.0000$ share difference:
  * Sum of matched CLOB buy fills (first 20 positions): **788.53 shares** ($586.17 cash deployed).
  * Sum of matched CLOB sell fills (first 20 positions): **729.84 shares** ($564.73 proceeds returned).
* **Live Verified Collateral**: Following Trade #20's scalp win (+**$3.03 net profit** on Market `5502249` at 14:36 UTC), live liquid collateral stands at **$248.587050 USD**, with 0 open positions and 0 resting orders.

---

## 4. Issue C: Polymarket Crypto Fee Schedule Formulation

* **Documented Polymarket Crypto Fee Schedule**:
  $$\text{Fee} = C \times \text{FeeRate} \times p \times (1 - p)$$
  where $C$ is share size, $\text{FeeRate} = 0.07$, and $p$ is execution price. Makers pay 0% fee.
* **Audit Finding**:
  * Production code ([`polymarket_live_executor.py:119`](file:///home/skybullet1987/quant_pipeline/src/polymarket_research/polymarket_live_executor.py#L119)) has **always used the canonical quadratic formula**:
    ```python
    per_share_fee = fee_rate * ((clamped_p * (1.0 - clamped_p)) ** fee_exponent)
    ```
  * In the research experiment scripts ([`backtest_engine.py`](file:///home/skybullet1987/quant_pipeline/src/polymarket_research/pm_hwr_001/backtest_engine.py#L38) and [`shock_grid_sweep.py`](file:///home/skybullet1987/quant_pipeline/src/polymarket_research/pm_hwr_001/shock_grid_sweep.py#L32)), a simplified linear approximation `0.07 * min(p, 1 - p)` was written.
* **Remediation**:
  * Replaced `min(p, 1 - p)` with `p * (1.0 - p)` across all research files.
  * Updated [`tests/test_pm_hwr_001_invariants.py`](file:///home/skybullet1987/quant_pipeline/tests/test_pm_hwr_001_invariants.py) with explicit unit test cases:
    * At $p = 0.50$: fee is $0.07 \times 0.50 \times 0.50 = \mathbf{0.0175}$ USDC/share.
    * At $p = 0.30$: fee is $0.07 \times 0.30 \times 0.70 = \mathbf{0.0147}$ USDC/share.
    * Symmetry: $\text{fee}(0.20) == \text{fee}(0.80) == \mathbf{0.0112}$ USDC/share.
  * All unit tests passed.

---

## 5. Issue D: Adversarial Audit of EXP-303 Policy B2 (100% Win Rate Debunked)

A forensic audit of [`src/polymarket_research/exp303_fast_unwind_shadow.py`](file:///home/skybullet1987/quant_pipeline/src/polymarket_research/exp303_fast_unwind_shadow.py#L168-L177) uncovered the reason for the simulated 100% win rate:

```python
# Lines 168-177 in exp303_fast_unwind_shadow.py:
target_exit_px = min(entry_px + self.theta, 0.98)
exit_notional_b1 = shares * target_exit_px
net_pnl_b2 = round(exit_notional_b1 - notional - entry_fee, 2)
```

### **The Simulation Flaw**
The script unconditionally assigned `exit_price = min(entry_px + self.theta, 0.98)` to **every single trade**, even when the underlying market resolved against the trade (`won == False`, expiring at $0.00). It assumed passive maker orders fill at $+10¢$ on 100% of trades with zero adverse movements.

### **Adversarial Simulation Results**
We replayed the 272 trades across three realistic execution models in [`audit_exp303_simulation.py`](file:///home/skybullet1987/quant_pipeline/src/polymarket_research/pm_hwr_001/audit_exp303_simulation.py):

| Simulation Model | Win Rate | Wins | Losses | Net PnL ($) | EV / Trade ($) | Flaw / Mechanism |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Original EXP-303 Policy B2** | **100.0%** | 272 | 0 | +$1,653.49 | +$6.08 | **Flawed**: Unconditional target fill on all candles |
| **Model 1: Loss Expiry Wipeout** | **83.1%** | 226 | 46 | **-$988.63** | **-$3.63** | 46 losing candles expire at $0.00 without stop |
| **Model 2: With Spot-Delta Stop** | **83.1%** | 226 | 46 | **+$995.20** | **+$3.66** | Losing candles stopped out @ 0.58 on CLOB |
| **Model 3: Queue Miss + Stop Loss** | **83.1%** | 226 | 46 | **+$985.55** | **+$3.62** | 14% missed maker fills fallback to taker + stop |

### **Key Takeaway**
1. The 100% win rate was a **simulation artifact**.
2. When realistic adverse price trajectories and stop-losses are applied, **Policy B2 achieves an 83.1% win rate and +$3.62 EV/trade**.
3. This aligns with live production, where Policy B2 produces a **65%–80% win rate** with controlled -$7.50 stop-losses.

---

## 6. Research Governance Roadmap

1. **Keep Live Execution Frozen**: Production service `polymarket-live-harvester.service` remains active and untouched on its current calibrated Half-Kelly sizing and spot-delta stop-loss rules.
2. **Reject Late-Candle Sniper**: Reconfirmed that market orderbooks price late-candle high-$z$ events at $0.98–$0.999, which destroys positive expectancy.
3. **Advance to PM-HWR-002**: Focus prospective research on **sub-second Binance-to-Polymarket lead-lag orderbook latency**, measuring the actual lifetime of stale quotes and real executable book depth.
