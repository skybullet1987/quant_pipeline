# DOMINUS v5.0 — Quantitative Policy Profit, Velocity & Risk Attribution (`POLICY_PROFIT_IMPACT.md`)

**Campaign:** DOMINUS v5.0 Supreme Profit & Operational Freedom (Phase 1 / Requirement R2)  
**Auditor:** Agent G (`@policy-auditor`)  
**Audit Timestamp:** 2026-11-11 UTC  
**Economic Baseline (Verified Reality — Zero Shadow/Realized Mixing):**
- **Liquid Deployable Cash (`pUSD`):** `$47.38`
- **Frozen Disputed `KMIA` Receivable:** `$50.51` cost basis (`$0.14` mark-to-bid across 4 Nov 7 positions; UMA DVM outcome pending)
- **Mark-to-Bid Reconciled NAV:** `$47.52` (`$97.89` book equity)
- **Fixed Infrastructure Burn (`quant-pipeline-finland`):** **`$24.67/month` = `$0.822/day` = `$0.0343/hour`**
  - **Crucial Breakeven Hurdle at `$47.38` Cash:** Earning `$0.822/day` on `$47.38` liquid capital requires **`+173.5 bps/day` (`+1.735%/day` = `+52.0%/month` gross return on liquid cash)** just to reach **`$0.00` net economic profit after VM overhead!**
  - If `KMIA` recovers `$50.51` (`$97.89` liquid cash), the infra breakeven hurdle drops by more than half to **`+84.0 bps/day` (`+25.2%/month`)**.
  - At `$500.00` NAV, the infra breakeven hurdle drops to **`+16.4 bps/day` (`+4.9%/month`)**.

---

## 1. Policy Profit Impact Classification: EV Protectors vs. EV Bottlenecks

Every policy in Dominus either **(A) Protects Realized Principal & Net EV** (by preventing `-50%` lockups, `-100%` Double-Zero settlement wipeouts, or `UNWRESID` legging losses) or **(B) Bottlenecks / Distorts Realized Net EV** (through technical cliff bugs, dead-code allowlist blocks, unmergeable lockup exemptions, or stale accounting drag).

### Table 1 — Ranked Profit-Destroying / Bottlenecking Policy Bugs (Fix / Replace Immediately)

| Rank | Policy / Restriction ID | Exact Defect Mechanism | Impact at `$47.38` Cash (`$/mo`) | Impact at `$500` NAV (`$/mo`) | Infra Cost Delta | Action |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: |
| **1** | **`POL-13` / `R-01`** (`hard_ruin_floor_usd: $62.00` coupled to `is_riskless_box_halted`) | If `KMIA` settles at `$0.00`, `tot_equity` drops from `$97.89` to `$47.38 < $62.00`, triggering `"equity"` halt in [polymarket_live_harvester.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L1266) and **100% freezing all riskless boxes** while `$0.82/d` VM burn continues! | **`-$30` to `-$75/mo`** *(100% trading blackout if `KMIA` loses)* | `$0/mo` *(above `$62`)* | `$0.00` | **`OPTIMIZE` (P0)** — Set `riskless_hard_ruin_floor_usd: 38.0` |
| **2** | **`POL-18` / `R-04`** (`check_per_event_concentration_cap` computing `$27.41` = `57.7%` NAV + bypasses) | `max(20.0, 0.28 * $97.89) = $27.41` allows locking **`57.9%` of remaining `$47.38` cash** into a single correlated UMA event (plus skips `AWAITING_ONCHAIN_SETTLEMENT` & `FAST_GUN_S2`), risking a second `KMIA`-style multi-week capital freeze! | **`-$18` to `-$45/mo`** *(expected lockup + dispute tail drag)* | **`-$75` to `-$160/mo`** | `$0.00` | **`OPTIMIZE` (P0)** — Enforce `15%` of reconciled NAV (`$7.13` at `$47.52`, `$75` at `$500`) |
| **3** | **`POL-15` / `R-02`** (`check_strict_pure_riskless_candidate_gate` blocking graduated `CAL1` & `COND1` + allowing WU sensor `W1`/`W_PRUNE1`) | Dead-code bug at [stage_c_zero_loss_velocity.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/stage_c_zero_loss_velocity.py#L296-L305) blocks owner-approved `CAL1` (`12/8` 100% WR) & `COND1` (`11/8` 100% WR) 2-leg boxes, while leaving single-leg Weather Underground proxy sensor snipes active! | **`-$8` to `-$22/mo`** *(missed `CAL1`/`COND1` + sensor dispute drag)* | **`-$65` to `-$185/mo`** | `$0.00` | **`REPLACE` (P1)** — Unblock `CAL1`/`COND1` structural 2-leg boxes; gate WU weather on dual-source consensus |
| **4** | **`POL-20` / `R-09` + `R-21`** (`passes_capital_velocity_hurdle` exempting unmergeable 24h `C1` + `$97.89` book basis) | Line `812` of [holistic_strategy_governance.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/holistic_strategy_governance.py#L812) lets unmergeable `24h` `45 bps` (`1.9 bps/hr`) `COMPLETE_SET` tie up cash for a full day instead of recycling every `<15s` via on-chain merge or reserving cash for `15–60 bps/hr` `D1`/`BOND1`! | **`-$6` to `-$18/mo`** *(opportunity-cost turnover loss)* | **`-$45` to `-$120/mo`** | `$0.00` | **`OPTIMIZE` (P1)** — Require verified instant merge (`_merge_wallet_ok`) for `C1` velocity exemption; anchor to `$47.52` NAV |
| **5** | **`POL-16` / `R-03`** (`ALPHA124_STATE_STALE` `> 300s` killing live graduated `D1`/`C1` boxes) | Any 5-minute restart/OOM hiccup in `polymarket-alpha124-shadow.service` (`MemoryMax=1550M`) halts **all** live `D1`/`C1`/`BOND1` fills in [polymarket_live_harvester.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py#L5622-L5623), especially during volatility spikes when book churn peaks! | **`-$3` to `-$12/mo`** *(missed spike fills)* | **`-$25` to `-$90/mo`** | `$0.00` | **`REPLACE` (P1)** — Cache graduated sleeve state for `24h` on live harvester |
| **6** | **`POL-07` / `R-06` + `POL-05` / `R-05` + `POL-08` / `R-07`** (Deployer UMA deadlock + approval scope bug + `polymarket_all_in_one.py` `<1 MB` canary cap at `910.7 KB`) | Delays deploying validated latency & arbitrage upgrades by `2–5+` days whenever passive post-expiry UMA disputes (`KMIA`) are open or single-scope owner approvals fail conjunction checks (`builder_and_deployer.py:326-335` checks only `polymarket_all_in_one.py < 1,000,000 B`, leaving `89.3 KB` headroom). | **`-$3` to `-$10/mo`** *(delayed upgrade compounding)* | **`-$20` to `-$60/mo`** | `$0.00` | **`OPTIMIZE` (P0/P1)** — Unify `_is_restart_safe_frozen_uma_lock`, fix scope mapping & binary-diff hygiene |
| **7** | **`POL-10` / `R-10`** (`prorated_vm_hourly_cost_usd: 0.0730` stale config) | Over-deducts `$52.56/mo` (`$1.752/d`) instead of actual `$24.67/mo` (`$0.822/d`) in `BudgetManager` / `PAAAccountant` reports (**`+$27.89/mo` phantom accounting loss**, distorting autonomous EV gating!). | **`$0` cash / `+$27.89/mo` accounting distortion** | **`+$27.89/mo` accounting distortion** | `$0.00` | **`OPTIMIZE` (P1)** — Set `0.0343` (`$24.67/mo`) |

---

### Table 2 — High-Value EV-Protecting Policies (Retain & Harden — Never Remove)

| Policy / Gate ID | Risk Prevented | Quantified Loss Avoided at `$47.38` Cash | Quantified Loss Avoided at `$500` NAV | Verdict |
| :--- | :--- | :---: | :---: | :---: |
| **`POL-19` / `R-40`** (`MULTI_LEG_BUNDLE` `>=3`-leg sequential CLOB block `< $500` NAV) | Partial-basket `UNWRESID` legging wipeouts (`-$2` to `-$8` per failed 3–6 leg FOK race) | **`+$10` to `+$35/mo` saved** | **`+$40` to `+$120/mo` saved** *(unlock only atomic / inventory-backed or `>= $500` with strict L2 cushion)* | **`RETAIN` + raise `nr0` default `$150 -> $500`** |
| **`POL-14` / `R-39`** (`riskless_only_mode: true` below `$150` undisputed NAV) | Sub-Kelly lot-size ruin (`$8` directional minimum lot = `16.9%` of `$47.38` cash; 3 consecutive stops = `-28.5%` drawdown) | **Prevents `~22%–35%` seed ruin probability** | At `$500` NAV (`> $150`), Half-Kelly (`$10–$22` lot = `2%–4.4%` NAV) becomes viable *if* shadow WFO passes (`PF >= 1.45, PBO <= 0.20`) | **`RETAIN` below `$150` undisputed NAV** |
| **`POL-22` / `R-36`** (`CrossVenueRuleVerifier` Double-Zero 5-Gate Verifier) | Cross-venue settlement rule divergence (buying YES on Venue A + NO on Venue B when strike/oracle/overtime mismatch settles **both** legs to `$0.00`!) | **Prevents `-50%` (`-$25`) single-trade catastrophe** | **Prevents `-$50` to `-$150` per mismatched pair** | **`RETAIN` permanently** |
| **`POL-22` / `R-42`** (Stage G `168h` Cross-Venue Shadow Certification + `$253` Min NAV) | Prematurely splitting `$47.38` across 2 venues (`~$23/venue`), incurring bridge gas + dual minimum-lot starvation + unverified API downtime | **`+$3` to `+$8/mo` saved** *(avoids bridge drag + capital fragmentation at `$47.38`)* | Unlocks validated second-venue (`ForecastEx/IBKR` or `STX Ontario` in `CA-ON`) once `168h` net post-delay PnL `> 0` | **`RETAIN`** |
| **`POL-11` / `R-38`** (`PAAAccountant` `> $1.50` cash / `> 0.75` share Wallet-to-Ledger Discrepancy Safeguard) | Unrecorded fee bleed, double-reservation spend, or orphaned conditional tokens | **Prevents silent principal bleed (`100%` wallet truth)** | **Prevents `$10–$100+` silent accounting drift** | **`RETAIN` permanently** |
| **`POL-01`..`04` / `R-33`..`35`** (Zero-Trust Anti-Self-Approval, Secret Stripping, Worktrees, `<UNTRUSTED_DATA_ONLY>`) | Autonomous privilege escalation, prompt injection from permissionless market text, or live-repo corruption | **Prevents `100%` (`$47.38`–`$97.89`) catastrophic loss** | **Prevents `100%` (`$500+`) catastrophic loss** | **`RETAIN` permanently (Non-Overridable)** |

---

## 2. Capital-Velocity & Net-After-Infra Math Across Capital Tiers

### Why Capital Velocity (`bps/hr`) Matters More Than Raw Spread (`bps`) at `$47.38`
Let $C$ be deployable liquid capital, $u \in [0, 1]$ average utilization, $v$ net realized velocity in $\text{bps/hr}$ on deployed capital, and $I = \$0.822/\text{day}$ fixed VM infrastructure burn:

$$\text{Net Daily Profit (USD)} = C \times u \times \left(\frac{24 \cdot v}{10{,}000}\right) - \$0.822$$

| Capital Scenario | Deployable Cash ($C$) | Required Portfolio Velocity ($u \cdot v$) to Break Even on `$0.822/d` VM | Realistic Post-Remediation Gross Trading (`u = 0.55`, `v = 16 bps/hr` avg across `C1` merge + `D1` + `2h BOND1` + `CAL1`/`COND1`) | Net Profit After `$24.67/mo` VM (`$/month`) | Honest Economic Assessment |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Current Liquid Cash (`KMIA` unresolved / `$0`)** | **`$47.38`** | **`7.23 bps/hr`** (`173.5 bps/day`) | **`+$1.00/day` (`+$30.00/mo` gross)** | **`+$5.33/mo` (`+$0.18/day`)** | **Razor-thin positive margin:** Every single policy bug (`R-01` `$62` halt, `R-04` `58%` station lockup, `R-09` unmergeable `24h` `C1` tie-up) flips net profit from `+$5/mo` to **`-$20/mo` net loss**! |
| **Post-`KMIA` Full Recovery (`+$50.51` won)** | **`$97.89`** | **`3.50 bps/hr`** (`84.0 bps/day`) | **`+$2.07/day` (`+$62.02/mo` gross)** | **`+$37.35/mo` (`+$1.25/day`)** | **Solid self-funding seed growth:** Infra overhead drops below `40%` of gross trading yield, accelerating compounding toward `$150` Milestone `M3.2`. |
| **Milestone `$253` (Stage G Micro-Threshold)** | **`$253.00`** | **`1.35 bps/hr`** (`32.5 bps/day`) | **`+$4.60/day` (`+$138.00/mo` gross)** *(at conservative `13.8 bps/hr` blended)* | **`+$113.33/mo` (`+$3.78/day`)** | Infra drag falls to `< 18%` of gross profit; directional WFO canary (`>= $150`) & `CA-ON`-legal second-venue staging become viable. |
| **Target Scale `$500` NAV** | **`$500.00`** | **`0.69 bps/hr`** (`16.4 bps/day`) | **`+$8.40/day` (`+$252.00/mo` gross)** *(at conservative `12.7 bps/hr` blended)* | **`+$227.33/mo` (`+$7.58/day`)** | Infra drag is `< 10%` of gross yield; regulated multi-venue (`ForecastEx/IBKR` + `STX Ontario` in `CA-ON`) and atomic/deep-L2 multi-leg partitions scale cleanly. |

---

## 3. Summary of Highest-EV Policy Unlocks (`$0.00` Extra Infra Cost)

1. **Eliminate the `$62.00` Post-`KMIA` Riskless Halt Cliff (`POL-13` / `R-01`):** Protects `100%` continuity of `~$30/mo` gross riskless arbitrage on `$47.38` cash if `KMIA` resolves unfavorably (`+$30` to `+$75/mo` tail-outage prevention at `$0` cost).
2. **Fix the Correlated-Event Cap from `$27.41` (`57.7%` NAV) to True `15%` Reconciled NAV (`$7.13` at `$47.52` NAV) (`POL-18` / `R-04`) + Quarantine Single-Leg WU Proxy Weather Locks (`POL-15` / `R-02`):** Prevents another `$27–$50` multi-day UMA dispute from cutting deployable velocity in half (`+$18` to `+$45/mo` preserved compounding velocity).
3. **Unblock Dead-Code Graduated `CAL1` & `COND1` 2-Leg Payoff-Dominant Boxes (`POL-15` / `R-02`):** Activates already-built, already-owner-approved `0%`-fee / low-fee calendar monotonicity and macro binary partition boxes (`+$8` to `+$22/mo` at `$47.38`; `+$65` to `+$185/mo` at `$500`).
4. **Enforce Instant On-Chain Merge Requirement on `C1` Velocity Exemption (`POL-20` / `R-09` & `R-21`):** Stops unmergeable `24h` low-yield complete sets from hogging `$47.38` seed cash while multiplying turnover on gasless/on-chain mergeable `C1` boxes (`+$6` to `+$18/mo` velocity gain).
5. **Decouple Live Graduated Arbitrage from `300s` `alpha124_shadow_state.json` Mtime (`POL-16` / `R-03`):** Eliminates shadow-daemon-induced live blind spots during high-volatility crypto spikes (`+$3` to `+$12/mo`).
