# Dominus Polymarket — Reconciled Day-by-Day Projections & Strategy Report (`v6.2` Live Deployment)

**Report Reconciled:** `2026-11-13 16:31 UTC` (Live Host: `kraken-finland`, `europe-north1-b`)  
**Projection Engine:** [`scripts/polymarket_daily_projections.py`](scripts/polymarket_daily_projections.py) (`model_version: v5.2_full_throttle_riskless_velocity`, `riskless_only_mode: true`, `strict_pure_riskless_mode: false`)  
**Strategy Governance:** [`config/polymarket_strategy_and_risk.json`](config/polymarket_strategy_and_risk.json) | **Manual:** [`AGENTS.md`](AGENTS.md) | **State & Decisions:** [`PROJECT_STATE.md`](PROJECT_STATE.md), [`DECISIONS.md`](DECISIONS.md) | **Operator Brief:** [`DAILY_COMMAND_CENTER_REPORT.md`](DAILY_COMMAND_CENTER_REPORT.md)

---

## 1. Authoritative Reconciled Capital & NAV Baseline (`D-001` / `D-009` Compliant)

Per [`AGENTS.md`](AGENTS.md) (`D-001`, `D-009`), live projections anchor strictly to **reconciled worst-case floor NAV** — never to persisted book equity (`$99.67`, which still carries the `$50.51` cost basis of the 4 disputed `KMIA` positions) and never to non-cash simulated shadow PnL:

| Metric | Live Value (`2026-11-13 16:31 UTC`) | Notes & Accounting Scope |
| :--- | :--- | :--- |
| **Funder Beacon Proxy (`sig_type=3`)** | `0x013A2474454fBd8738cff6a7f204eF1bc377F4e9` | Polygon `pUSD` wallet |
| **Free Liquid `pUSD` (`live_bankroll`)** | **`$42.12`** | Immediately deployable trading cash |
| **Worst-Case Guaranteed-Floor NAV (Anchor)** | **`$49.12`** | `$42.12` free `pUSD` + `$7.00` par floor on active `MKR_LOCK1` (`$6.965` cost basis on `7000344`) + **`$0.00`** assumed on 4 disputed `KMIA` (`$50.51` frozen cost basis) |
| **Mark-to-Bid Liquidation NAV** | **`$49.09`** | Excludes optimistic UMA win recovery; reflects live CLOB bid |
| **Persisted Harvester Book Equity (`total_account_equity`)** | **`$99.67`** | Book value including `$50.51` frozen `KMIA` + `$6.965` open `MKR_LOCK1` (`frozen_single_leg_cost_usd: $57.55`) — **never used for sizing** |
| **High Water Mark (`HWM`)** | `$99.67` | Persisted book equity reference |
| **Disputed `KMIA` Positions (`D-001` Protected)** | `4` positions (`$50.51` cost basis) | `6707503` (`35 NO`) & `6707502` (`17 YES`); kept **100% untouched** (`umaResolutionStatus == "disputed"`) |
| **Infrastructure Cost Hurdle (`kraken-finland`)** | **`$0.8223/day` (`$24.67/month`)** | Requires **`+6.98 bps/hr`** (`+167.4 bps/day`) net edge on `$49.12` floor just to break even on VM cost |
| **Active Live `v6.2` Config Toggles** | `BOND1=True`, `S2_TWAP=False`, `cancel_on_arb max=$43.23` | `Row 1` pure-riskless live + `Row 2` `BOND1` carry enabled; `S2` TWAP paused; directional/lattice hard-disabled |

---

## 2. Empirical Pre-`v6.2` Run-Rate vs. `$0.8223/d` VM Hurdle (Strict Non-Conflation)

Before projecting `v6.2` modeled target capacity forward, [`compute_empirical_realized_runrate`](scripts/polymarket_daily_projections.py) measures actual realized pure-riskless cash closes from `live_harvester_state.json` (excluding retired directional/lattice losses and `NOT_EXECUTED` records):

| Trailing Window | Filled Riskless Record | Realized Net PnL | Filled Notional | Fees Paid | Avg Daily Rate | Implied Edge (`bps/hr`) | Net After VM (`$0.8223/d`) | Clears VM Hurdle? |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Trailing 24h** | `7W / 0L` (`100.0%`) | `+$0.2100` | `$43.08` | `$0.0000` | `+$0.2100/d` | `+1.78 bps/hr` | **`-$0.6123/d`** | **NO** |
| **Trailing 72h** | `19W / 0L` (`100.0%`) | `+$0.7000` | `$132.42` | `$0.0092` | `+$0.2333/d` | `+1.98 bps/hr` | **`-$0.5890/d`** | **NO** |
| **Trailing 7d (Pre-`v6.2` Status Quo)** | `58W / 0L` (`100.0%`) | **`+$3.0841`** | `$430.85` | `$0.0500` | **`+$0.4406/d`** | `+3.74 bps/hr` | **`-$0.3817/d`** | **NO** |

- **What `Status-Quo Carry-Only (+$0.4406/d)` Looks Like Over 30 Days (`$0.8223/d` VM Hurdle):**
  - Day 1: `$49.56` gross equity (`+$0.44` profit vs `$0.82` VM -> **`-$0.38` net after VM**)
  - Day 7: `$52.20` gross equity (`+$3.08` profit vs `$5.76` VM -> **`-$2.68` net after VM**)
  - Day 14: `$55.29` gross equity (`+$6.17` profit vs `$11.51` VM -> **`-$5.34` net after VM**)
  - Day 30: **`$62.34` gross equity** (`+$13.22` gross profit vs `$24.67` VM -> **`-$11.45` net after VM**)
- **Strategic Implication:** The `+$0.4406/day` carry-only baseline (predominantly `BOND1` / `BOND2` / `MKR_LOCK1`) is `100%` win rate over `58` trailing 7d closes (`+3.74 bps/hr`), but covers only `53.6%` of the `$0.8223/day` VM burn. Clearing the VM hurdle requires **`v6.2` multi-leg / `C1` / `D1` / Full-Throttle `CLASS_A/B` merges** (`ft_bridge` live conversion + sub-millisecond EIP-712 signing) to sustain `>= +6.98 bps/hr` (`+$0.83/day` gross on `$49.12`).
- **Non-Cash Shadow Universe Context (`D-009` Segregated):** The Full-Throttle shadow engine monitors `19,603` events / `365,654` markets (`200,613` orderbook markets, `401,138` tokens, `5,689` proposition graph edges, `1,227` rule-trap blocks, `1,200` dormant near-arbs), with Family L Hedged Maker at `+$541.2506` shadow PnL (`sol_shadow_settled=138` @ `81.88%` WR, `phase3a_maker_settled=15`, `xrp_shadow_settled=3`). **These shadow figures are NOT real money** and do not enter NAV compounding.

---

## 3. `v6.2` Day-by-Day Compounding Schedule — Days 1 to 30 (`$49.12` Reconciled Floor)

Modeled `v6.2` curves reflect depth-capped pure-riskless turnover across **P25 Conservative**, **P50 Base Finland**, and **P75 Low-Latency Upside**, juxtaposed with cumulative VM cost (`$0.8223/day`) and the **Empirical Status-Quo (`+$0.4406/d`)** linear baseline:

| Day | Date (UTC) | Status-Quo (`+$0.44/d`) Eq / Net-VM | P25 Eq ($) | **P50 Base Eq ($)** | **P50 Day PnL** | P75 Upside Eq ($) | Cum VM ($) | P25 Net-VM | **P50 Net-VM** | P75 Net-VM | Active Regime / Graduation Milestone |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| D01 | 2026-11-13 | `$49.56` (`-$0.38`) | `$50.17` | **`$50.98`** | `+$1.86` | `$52.17` | `$0.82` | `+$0.23` | **`+$1.04`** | `+$2.23` | `SEED_FULL_THROTTLE_RISKLESS` (`<$125`) |
| D02 | 2026-11-14 | `$50.00` (`-$0.76`) | `$51.25` | **`$52.91`** | `+$1.93` | `$55.39` | `$1.64` | `+$0.49` | **`+$2.15`** | `+$4.63` | `SEED_FULL_THROTTLE_RISKLESS` (`<$125`) |
| D03 | 2026-11-15 | `$50.44` (`-$1.15`) | `$52.34` | **`$54.92`** | `+$2.01` | `$58.82` | `$2.47` | `+$0.75` | **`+$3.33`** | `+$7.23` | `SEED_FULL_THROTTLE_RISKLESS` (`<$125`) |
| D04 | 2026-11-16 | `$50.88` (`-$1.53`) | `$53.45` | **`$57.01`** | `+$2.09` | `$62.45` | `$3.29` | `+$1.04` | **`+$4.60`** | `+$10.04` | `SEED_FULL_THROTTLE_RISKLESS` (`<$125`) |
| D05 | 2026-11-17 | `$51.32` (`-$1.91`) | `$54.59` | **`$59.16`** | `+$2.15` | `$66.30` | `$4.11` | `+$1.36` | **`+$5.93`** | `+$13.07` | `SEED_FULL_THROTTLE_RISKLESS` (`<$125`) |
| D06 | 2026-11-18 | `$51.76` (`-$2.29`) | `$55.76` | **`$61.40`** | `+$2.24` | `$70.35` | `$4.93` | `+$1.71` | **`+$7.35`** | `+$16.30` | `SEED_FULL_THROTTLE_RISKLESS` (`<$125`) |
| D07 | 2026-11-19 | `$52.20` (`-$2.68`) | `$56.94` | **`$63.71`** | `+$2.31` | `$74.65` | `$5.76` | `+$2.06` | **`+$8.83`** | `+$19.77` | `SEED_FULL_THROTTLE_RISKLESS` (`<$125`) |
| D08 | 2026-11-20 | `$52.64` (`-$3.05`) | `$58.14` | **`$66.10`** | `+$2.39` | `$79.18` | `$6.58` | `+$2.44` | **`+$10.40`** | `+$23.48` | `SEED_FULL_THROTTLE_RISKLESS` (`<$125`) |
| D09 | 2026-11-21 | `$53.09` (`-$3.44`) | `$59.38` | **`$68.58`** | `+$2.48` | `$83.96` | `$7.40` | `+$2.86` | **`+$12.06`** | `+$27.44` | `SEED_FULL_THROTTLE_RISKLESS` (`<$125`) |
| D10 | 2026-11-22 | `$53.53` (`-$3.82`) | `$60.64` | **`$71.15`** | `+$2.57` | `$89.01` | `$8.22` | `+$3.30` | **`+$13.81`** | `+$31.67` | `SEED_FULL_THROTTLE_RISKLESS` (`<$125`) |
| D11 | 2026-11-23 | `$53.97` (`-$4.20`) | `$61.93` | **`$73.80`** | `+$2.65` | `$94.31` | `$9.05` | `+$3.76` | **`+$15.63`** | `+$36.14` | `SEED_FULL_THROTTLE_RISKLESS` (`<$125`) |
| D12 | 2026-11-24 | `$54.41` (`-$4.58`) | `$63.24` | **`$76.55`** | `+$2.75` | `$99.90` | `$9.87` | `+$4.25` | **`+$17.56`** | `+$40.91` | `SEED_FULL_THROTTLE_RISKLESS` (`<$125`) |
| D13 | 2026-11-25 | `$54.85` (`-$4.96`) | `$64.58` | **`$79.39`** | `+$2.84` | `$105.80` | `$10.69` | `+$4.77` | **`+$19.58`** | `+$45.99` | P75 crosses **`$100`** |
| D14 | 2026-11-26 | `$55.29` (`-$5.34`) | `$65.94` | **`$82.32`** | `+$2.93` | `$112.04` | `$11.51` | `+$5.31` | **`+$21.69`** | `+$51.41` | `SEED_FULL_THROTTLE_RISKLESS` (`<$125`) |
| D15 | 2026-11-27 | `$55.73` (`-$5.73`) | `$67.32` | **`$85.35`** | `+$3.03` | `$118.66` | `$12.33` | `+$5.87` | **`+$23.90`** | `+$57.21` | `SEED_FULL_THROTTLE_RISKLESS` (`<$125`) |
| D16 | 2026-11-28 | `$56.17` (`-$6.11`) | `$68.74` | **`$88.48`** | `+$3.13` | `$125.65` | `$13.16` | `+$6.46` | **`+$26.20`** | `+$63.37` | P75 unlocks `$125` Reward Tier |
| D17 | 2026-11-29 | `$56.61` (`-$6.49`) | `$70.19` | **`$91.72`** | `+$3.24` | `$133.19` | `$13.98` | `+$7.09` | **`+$28.62`** | `+$70.09` | `SEED_FULL_THROTTLE_RISKLESS` (`<$125`) |
| D18 | 2026-11-30 | `$57.05` (`-$6.87`) | `$71.66` | **`$95.07`** | `+$3.35` | `$141.18` | `$14.80` | `+$7.74` | **`+$31.15`** | `+$77.26` | P75 unlocks `$140` Pre-Split Tier |
| D19 | 2026-12-01 | `$57.49` (`-$7.25`) | `$73.16` | **`$98.53`** | `+$3.46` | `$150.07` | `$15.62` | `+$8.42` | **`+$33.79`** | `+$85.33` | P75 crosses **`$150`** (`M3.2`) |
| D20 | 2026-12-02 | `$57.93` (`-$7.63`) | `$74.69` | **`$102.09`** | `+$3.56` | `$159.52` | `$16.45` | `+$9.12` | **`+$36.52`** | `+$93.95` | P50 crosses **`$100`** |
| D21 | 2026-12-03 | `$58.37` (`-$8.02`) | `$76.26` | **`$105.79`** | `+$3.70` | `$169.55` | `$17.27` | `+$9.87` | **`+$39.40`** | `+$103.16` | `SEED_FULL_THROTTLE_RISKLESS` (`<$125`) |
| D22 | 2026-12-04 | `$58.81` (`-$8.40`) | `$77.86` | **`$109.62`** | `+$3.83` | `$180.20` | `$18.09` | `+$10.65` | **`+$42.41`** | `+$112.99` | `SEED_FULL_THROTTLE_RISKLESS` (`<$125`) |
| D23 | 2026-12-05 | `$59.25` (`-$8.78`) | `$79.48` | **`$113.58`** | `+$3.96` | `$191.51` | `$18.91` | `+$11.45` | **`+$45.55`** | `+$123.48` | `SEED_FULL_THROTTLE_RISKLESS` (`<$125`) |
| D24 | 2026-12-06 | `$59.69` (`-$9.16`) | `$81.14` | **`$117.69`** | `+$4.11` | `$203.49` | `$19.74` | `+$12.28` | **`+$48.83`** | `+$134.63` | `SEED_FULL_THROTTLE_RISKLESS` (`<$125`) |
| D25 | 2026-12-07 | `$60.13` (`-$9.54`) | `$82.82` | **`$121.94`** | `+$4.25` | `$216.20` | `$20.56` | `+$13.14` | **`+$52.26`** | `+$146.52` | Approaching `$125` Reward Unlock |
| D26 | 2026-12-08 | `$60.58` (`-$9.92`) | `$84.53` | **`$126.34`** | `+$4.40` | `$229.68` | `$21.38` | `+$14.03` | **`+$55.84`** | `+$159.18` | P50 crosses **`$125`** |
| D27 | 2026-12-09 | `$61.02` (`-$10.31`) | `$86.29` | **`$130.99`** | `+$4.65` | `$243.98` | `$22.20` | `+$14.97` | **`+$59.67`** | `+$172.66` | `TIER_1_UNLOCKED` (`MKR_REWARD_LOCKED_CARRY` + Family L) |
| D28 | 2026-12-10 | `$61.46` (`-$10.69`) | `$88.07` | **`$135.81`** | `+$4.82` | `$259.13` | `$23.02` | `+$15.93` | **`+$63.67`** | `+$186.99` | P75 crosses **`$253`** (`TIER_1` for P50) |
| D29 | 2026-12-11 | `$61.90` (`-$11.07`) | `$89.89` | **`$140.80`** | `+$4.99` | `$275.69` | `$23.85` | `+$16.92` | **`+$67.83`** | `+$202.72` | P50 crosses **`$140`** |
| D30 | 2026-12-12 | `$62.34` (`-$11.45`) | `$91.74` | **`$146.23`** | `+$5.43` | `$293.10` | `$24.67` | `+$17.95` | **`+$72.44`** | `+$219.31` | **`TIER_2_UNLOCKED` (`>=$140`): Pre-Split Overround Gun** |

*(Note: Status-quo `Net-VM` at `D07`/`D14`/`D30` matches `status_quo_linear_30d_baseline` in [`scripts/polymarket_daily_projections.py`](scripts/polymarket_daily_projections.py) (`-$2.68`, `-$5.34`, `-$11.45`).)*

---

## 4. Long-Horizon Growth, Milestone ETAs & `KMIA` Settlement Sensitivity

### 4.1 60-Day to 365-Day Depth-Capped Horizons (`$49.12` Base vs. Favorable `+$52` `KMIA` -> `$101.12`)

| Horizon | Date (UTC) | Cum VM ($) | Base `$49.12` (`$0` `KMIA`): P25 / **P50** / P75 (`P50 Net-VM`) | Favorable `+$52` `KMIA` (`$101.12`): P25 / **P50** / P75 (`P50 Net-VM`) |
| :---: | :---: | :---: | :--- | :--- |
| **Day 1** | 2026-11-13 | `$0.82` | `$50.17` / **`$50.98`** / `$52.17` (`+$1.04`) | `$103.18` / **`$104.78`** / `$107.09` (`+$2.84`) |
| **Day 7** | 2026-11-19 | `$5.76` | `$56.94` / **`$63.71`** / `$74.65` (`+$8.83`) | `$116.44` / **`$129.75`** / `$151.89` (`+$22.87`) |
| **Day 14** | 2026-11-26 | `$11.51` | `$65.94` / **`$82.32`** / `$112.04` (`+$21.69`) | `$134.20` / **`$168.26`** / `$232.44` (`+$55.63`) |
| **Day 30** | 2026-12-12 | `$24.67` | `$91.74` / **`$146.23`** / `$293.10` (`+$72.44`) | `$188.60` / **`$308.01`** / `$572.44` (`+$182.22`) |
| **Day 60** | 2027-01-11 | `$49.34` | `$170.22` / **`$443.54`** / `$1,118.51` (`+$345.08`) | `$356.84` / **`$781.69`** / `$1,541.57` (`+$631.23`) |
| **Day 90** | 2027-02-10 | `$74.01` | `$323.20` / **`$975.97`** / `$2,188.44` (`+$852.84`) | `$619.06` / **`$1,389.04`** / `$2,648.71` (`+$1,213.91`) |
| **Day 180** | 2027-05-11 | `$148.01` | `$1,219.62` / **`$2,986.07`** / `$5,720.44` (`+$2,788.94`) | `$1,639.65` / **`$3,463.63`** / `$6,201.42` (`+$3,214.50`) |
| **Day 365** | 2027-11-12 | `$300.14` | `$3,606.95` / **`$7,459.34`** / `$13,033.49` (`+$7,110.08`) | `$4,079.66` / **`$7,936.93`** / `$13,514.47` (`+$7,535.67`) |

*(Note: `Day 180` JSON `summary_horizons_usd` rounds `p50_net_after_vm_usd` to `+$2,788.93` vs `+$2,788.94` in `day_by_day_schedule` due to independent sub-cent subtraction rounding.)*

### 4.2 Milestone ETAs (Base `$49.12` Floor vs. `+$52` `KMIA` Recovery)

| Target NAV | Base `$49.12` (`P75 / P50 / P25` Days) | Base P50 Date (UTC) | `+$52` `KMIA` (`P75 / P50 / P25` Days) | `+$52` P50 Date (UTC) | Unlocked Capability |
| :---: | :---: | :---: | :---: | :---: | :--- |
| **`$100`** | `13d / 20d / 35d` | `2026-12-02` | `1d / 1d / 1d` | `2026-11-13` | `3x` seed capital milestone |
| **`$150` (`M3.2`)** | `19d / 31d / 55d` | `2026-12-13` | `7d / 11d / 20d` | `2026-11-23` | Unlocks `$125` Reward + `$140` Pre-Split Overround Gun |
| **`$253`** | `28d / 45d / 79d` | `2026-12-27` | `16d / 25d / 44d` | `2026-12-07` | Stage G (`CA-ON`-legal `ForecastEx` + `STX`) evaluation gate |
| **`$500`** | `40d / 64d / 113d` | `2027-01-15` | `28d / 44d / 78d` | `2026-12-26` | Full multi-leg depth & multi-venue scaling threshold |
| **`$1,000`** | `57d / 92d / 162d` | `2027-02-12` | `45d / 72d / 127d` | `2027-01-23` | Institutional Polymarket book depth cap phase |
| **`$2,500`** | `99d / 160d / 283d` | `2027-04-21` | `87d / 140d / 248d` | `2027-04-01` | High-liquidity depth saturation scaling |
| **`$5,000`** | `162d / 264d / 468d` | `2027-08-03` | `150d / 244d / 433d` | `2027-07-14` | Below `$5k`: `proposal_only_live_promotion: true` (`D-002`) |
| **`$10,000`** | `289d / 471d / >540d` | `2028-02-26` | `277d / 451d / >540d` | `2028-02-06` | Corporate/KYB expansion gate (`R-31`) |

---

## 5. Pending Operational Items & Risk Controls

1. **Disputed `KMIA` Settlement (`D-001`):** Do not sell into distressed bids or unwind the `4` disputed Nov 7 `KMIA` trades (`$50.51` cost basis). Both floor equity (`$49.12`) and `riskless_hard_ruin_floor_usd` protect pure-riskless live operation regardless of a `$0` or `+$52` settlement.
2. **Active `MKR_LOCK1` Position:** `mkt 7000344` (`7.0 sh @ $0.995 = $6.965`) holds a resting SELL `@ $0.998`; once filled/settled it recycles `~$7.00` back into free `pUSD`.
3. **Observing `v6.2` Live Fill Lift (`>$0.8223/d` Hurdle):** Track `24h` / `72h` live fills over the next 2–7 days as `Full-Throttle` bridge opportunities (`ft_bridge`) and sub-millisecond `D1`/`C1`/`BOND1` fills compound to confirm live PnL crosses the `+6.98 bps/hr` VM breakeven line cleanly.
4. **Shadow Telemetry Wiring Fixed:** [`scripts/polymarket_daily_projections.py`](scripts/polymarket_daily_projections.py) now reads `dominus_full_throttle_dashboard_v1` sections accurately, and [`Alpha124ShadowDaemon._resolve_gatling_starting_nav_usd`](src/polymarket_research/alpha_124_shadow_daemon.py) dynamically resolves live reconciled NAV (`$49.12`) instead of stale hardcoded `$60.92`.
