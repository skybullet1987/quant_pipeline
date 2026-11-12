# DOMINUS v6.0 — Capital Efficiency, Balance-Sheet & Dynamic Allocator Reassessment (`CAPITAL_EFFICIENCY_REASSESSMENT.md`)

**Campaign:** DOMINUS Restriction Register v6.0 Reassessment  
**Timestamp:** `2026-11-11 UTC`  
**Core Engine:** [`DynamicMarginalCapitalAllocator`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L1261-L1626) & [`run_v6_counterfactual_opportunity_audit.py`](file:///C:/Users/Anton/source/repos/Dominus/scripts/run_v6_counterfactual_opportunity_audit.py)

---

## 1. Authoritative Balance-Sheet Decomposition (`Zero Frozen-Collateral Illusion`)

v5.0 [RESTRICTION_REGISTER.md](file:///C:/Users/Anton/source/repos/Dominus/RESTRICTION_REGISTER.md) used stale `$47.38` cash / `$97.89` book figures and allowed multiple modules to pass `$99.21` (`$97.89`) persisted book equity into sizing and velocity formulas (`R-01`, `R-04`, `R-09`, `R-15`). Reconciled `2026-11-11 UTC` production ground truth separates **four distinct capital numbers** with zero overlap:

| Capital Metric | Exact Value (`USD`) | Composition | Authorized v6.0 Usage |
| :--- | :---: | :--- | :--- |
| **1. Deployable Liquid `pUSD` (`C_liq`)** | **`$48.695132`** (`$48.70`) | On-chain `pUSD` (`0xC0B1...806E`) in Funder Beacon Proxy `0x013A...F4e9` (`$0.000000` ledger drift) | **100% sole cash pool** for order sizing & `DynamicMarginalCapitalAllocator` (`$0.00` assumed from frozen `KMIA`!). |
| **2. Worst-Case Guaranteed-Floor NAV** | **`$48.695132`** (`$48.70`) | `$48.695132` cash + `$0.00` worst-case payout on 4 disputed `KMIA` positions | Floor solvency & `LossCauseAwareCapitalController` (`R-01`). |
| **3. Mark-to-Bid Liquidation NAV (`NAV_bid`)** | **`$48.834132`** (`$48.83`) | `$48.695132` cash + `$0.1390` live CLOB bid across `52.0` disputed `KMIA` shares | Correlated Worst-Case Exposure cap (`15% * $48.8341 = $7.3251` per cluster, `R-04`/`R-41`). |
| **4. Persisted Book Equity (`E_book`)** | **`$99.205132`** (`$99.21`) | `$48.695132` cash + `$50.5100` historical cost basis on markets `6707503` & `6707502` | **Historical accounting display ONLY — NEVER used to size clips, relax maturity hurdles, or mask execution losses!** |

*(Untracked Signer EOA `0x9703...50a5` reserve: `41.81376003 POL` `~$3.70` gas buffer + `$1.000000 USDC.e`.)*

---

## 2. Infrastructure Expense Reconciliation & Elimination of Sunk-Cost Double Counting (`R-10`)

Using [`reconcile_infrastructure_expenses`](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/v6_restriction_and_capital_allocator.py#L1156-L1204) over the `14.0`-day (`336.0h`) post-lock riskless operating window (`79W / 0L`, `+$18.246110` realized net P&L after `$0.5825` CLOB fees):

| Metric | Value | Quantitative Audit Finding |
| :--- | :---: | :--- |
| **Fixed Monthly GCP VM (`kraken-finland`)** | **`$24.67 / mo`** | `$0.822333 / day` = **`$0.034264 / hr`** (`100%` sunk fixed cost while VM runs). |
| **Marginal AI Cost (`subscription_flat`)** | **`$0.00 / trade`** | Zero metered LLM API spend (`ai_billing_mode = "subscription_flat"`). |
| **Marginal Relayer V2 Gas Cost (`sig_type=3`)** | **`$0.00 / trade`** | Gasless Builder Relayer V2 sponsors Polygon `splitPosition`/`mergePositions`/`redeemPositions` (`<= 24 tx/min`). |
| **True Marginal Trading Profit (`14d`, `79` clips)** | **`+$18.246110`** | Every trade with `MRNV > $0.00` strictly increases terminal wallet cash! |
| **Sunk Fixed VM Burn (`336.0h` exact window)** | **`-$11.512704`** | Requires **`+7.0364 bps/hr`** (`+168.87 bps/day`) portfolio-wide on `$48.70` cash (`+3.45 bps/hr` at `$99.21`; `+0.69 bps/hr` at `$500.00`). |
| **Full-Cost Net Economic Profit (`14d`)** | **`+$6.733406`** | **Net profitable even after `100%` of cloud infrastructure burn** despite `$50.51` frozen in `KMIA`! |
| **Legacy `accountant.py` Intraday-Mismatch Report** | `+$17.997011` | Subtracted only `7.27h` (`$0.2491`) intraday UTC VM burn from `336h` cumulative P&L (`$11.2636` horizon error). |
| **Scorecard Per-Clip Double-Counting Eliminated** | **`$11.366974`** | Eliminated charging `$0.034264/hr` sunk VM burn simultaneously to each of `79` clips AND to the portfolio! |

---

## 3. Mathematical Formulation of `DynamicMarginalCapitalAllocator` (`R-09`, `R-43`, `R-15`, `R-21`, `R-24`)

For every candidate structure $i$ with required per-share capital $c_i$, executable L2 depth $Q_i^{\max}$, exact V2 fee-and-conversion-adjusted worst-case payoff $w_i$, partial-fill probability $p_i^{\text{part}}$, unwind loss $L_i^{\text{unw}}$, and realistic effective lockup $T_i^{\text{eff}}$:

1. **Construction-Adjusted Unit Realizable Net Edge (`R-24`):**
   $$e_i = w_i - p_i^{\text{part}} \cdot L_i^{\text{unw}}$$
   *(Nominally riskless terminal payoffs with `e_i <= 0` after partial-fill construction risk are rejected before capital allocation!)*

2. **Protocol-Verified Effective Lockup (`R-21`):**
   $$T_i^{\text{eff}} = \begin{cases} \max(0.005\text{ h},\; T_i^{\text{merge}}) & \text{if } \texttt{merge\_supported} \text{ verified (`18s` on `sig\_type=3 + CTF\_V1\_PUSD`)} \\ T_i^{\text{maturity}} + T_i^{\text{settle}} & \text{otherwise (`24h+` fallback on `PositionManager V2` / unmergeable legs)} \end{cases}$$

3. **Convex Utilization & Displaced-Competitor Capital Shadow Price (`R-09` / `R-43`):**
   $$\lambda_{\text{cap}}(u_i, r_i^{\text{disp}}) = \max\!\left(\lambda_0 + (\lambda_1 - \lambda_0)\,u_i^2,\;\; 0.50 \, r_i^{\text{disp}} \, u_i\right)$$
   where $\lambda_0 = 0.50\text{ bps/hr}$ (idle-cash floor), $\lambda_1 = 18.0\text{ bps/hr}$ (full-utilization reserve curve), $u_i \in [0,1]$ is midpoint portfolio cash utilization, and $r_i^{\text{disp}}$ is the highest `bps/hr` among **subsequent unallocated positive-EV candidates actually crowded out** by clip $K_i = q_i c_i$ (`0` if $K_i$ does not crowd out remaining candidates!).

4. **Marginal Realizable Net Value (`MRNV`):**
   $$\text{MRNV}_i(q_i) = \underbrace{q_i e_i - C_i^{\text{marg\_infra}}}_{\text{Realizable Net Value (RNV)}} + \underbrace{K_i \frac{r_{\text{reinv}}}{10^4} \min(H - T_i^{\text{eff}}, 6\text{h})\,\mathbf{1}_{\text{recycle}}}_{\text{Capital-Recycling Benefit}} - \underbrace{K_i \frac{\lambda_{\text{cap}}(u_i, r_i^{\text{disp}})}{10^4} T_i^{\text{eff}}}_{\text{Endogenous Opportunity Cost}}$$

---

## 4. Reproducible Counterfactual Benchmark: Legacy v5 Cliffs vs. v6.0 Allocator

Executed deterministically via `python scripts/run_v6_counterfactual_opportunity_audit.py` across a 6-candidate mixed arrival batch (`CAND_0` `720h` `0.04 bps/hr` `DOMINANCE` trap, `CAND_1` `18s` gasless `C1` merge, `CAND_2` `6h` fee-bearing proven `CAL1`, `CAND_3` `8h` proven `FT_I` duplicate equivalence, `CAND_4` `25.5h` `COND1` idle carry, and `CAND_5` `4h` `3`-leg sequential slate):

| NAV Tier | Legacy v5 Accepted (`LIVE`) | Legacy v5 RNV | v6.0 Accepted (`LIVE`) | v6.0 RNV | Net `LIVE` RNV Uplift | `SHADOW` / `RESEARCH` Admitted |
| :--- | :--- | :---: | :--- | :---: | :---: | :---: |
| **`$48.70` (Current Cash)** | `CAND_0` *(30d trap!)*, `CAND_1` | `$0.1635` | `CAND_1`, `CAND_2`, `CAND_3`, `CAND_4` | **`$0.5392`** | **`+$0.3757` (`+229.8%` / `3.30x`)** | **`6 / 6` (`100%`)** |
| **`$99.21` (Post-`KMIA` Par)** | `CAND_0` *(30d trap!)*, `CAND_1` | `$0.1848` | `CAND_1`, `CAND_2`, `CAND_3`, `CAND_4` | **`$0.9401`** | **`+$0.7553` (`+408.8%` / `5.09x`)** | **`6 / 6` (`100%`)** |
| **`$253.00` (Stage G Tier)** | `CAND_0` *(30d trap!)*, `CAND_1` | `$0.2496` | `CAND_1`, `CAND_2`, `CAND_3`, `CAND_4` | **`$0.9401`** | **`+$0.6905` (`+276.7%` / `3.77x`)** | **`6 / 6` (`100%`)** |
| **`$500.00` (Multi-Leg Tier)** | `CAND_0` *(30d trap!)*, `CAND_1` | `$0.2690` | `CAND_1`, `CAND_5`, `CAND_2`, `CAND_3`, `CAND_4` | **`$1.1761`** | **`+$0.9071` (`+337.2%` / `4.37x`)** | **`6 / 6` (`100%`)** |

---

## 5. Quantitative Recovery Evaluation of Disputed `KMIA` Inventory (`R-44` / `D-001`)

Across the `52.0` disputed `KMIA` shares (`35.0 NO` in `6707503` + `17.0 YES` in `6707502`, `$50.51` sunk cost basis):
- **Option B (Distressed CLOB Sale — Prohibited by `D-001`):** Current bid salvage `$0.1390`, compounded at `15.0 bps/hr` for `168h` (`7` days) = **`$0.1788`**.
- **Option A (Hold Untouched for UMA DVM / Official Case — `D-001`):** Terminal payout = `$52.00` with probability $p_{\text{DVM}}$, `$0.00` otherwise.
- **Exact Breakeven Probability:**
  $$p^* = \frac{\$0.1788}{\$52.00} = 0.003439 \;\; (\mathbf{0.344\%})$$
- **Conclusion:** Holding untouched (`D-001`) strictly dominates distressed liquidation whenever $P(\text{favorable resolution}) > 0.344\%$. At $p_{\text{DVM}} = 35\%$, $\mathbb{E}[\text{Hold}] = \$18.2000$ vs $\$0.1788$ (**`+$18.0212` net EV advantage**), while valuing `KMIA` at `$0.00` in deployable cash guarantees zero over-sizing on the active `$48.70` liquid bankroll.
