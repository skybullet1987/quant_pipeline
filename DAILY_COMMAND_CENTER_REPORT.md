# Dominus Daily Command Center Report — Live `v6.2` Reconciled Snapshot

**Generated:** `2026-11-13 16:31 UTC` | **Host:** `kraken-finland` (`europe-north1-b`, `3,907 MiB` RAM, `MemorySwapMax=0B`)  
**Engine & Governance:** [`scripts/polymarket_daily_projections.py`](scripts/polymarket_daily_projections.py) | [`config/polymarket_strategy_and_risk.json`](config/polymarket_strategy_and_risk.json) | [`AGENTS.md`](AGENTS.md) | **Full Schedule:** [`FULL_THROTTLE_STRATEGY_AND_PROJECTIONS_REPORT.md`](FULL_THROTTLE_STRATEGY_AND_PROJECTIONS_REPORT.md)

---

## 1. Live Wallet, NAV Triad & Open State (`D-001` / `D-009`)

- **Beacon Proxy Wallet (`sig_type=3`):** `0x013A2474454fBd8738cff6a7f204eF1bc377F4e9`
- **Free Working Cash (`pUSD`):** **`$42.12`** (`liquid_working_cash_usd`)
- **Reconciled Guaranteed-Floor NAV (Compounding Anchor):** **`$49.12`** (`$42.12` cash + `$7.00` `MKR_LOCK1` floor + **`$0.00`** assumed on 4 disputed `KMIA`)
- **Mark-to-Bid Liquidation NAV:** **`$49.09`**
- **Persisted Book Equity (`total_account_equity`):** **`$99.67`** (`$42.12` cash + `$57.55` cost basis across 5 open records; **never used for sizing**)
- **Untouched Open Positions (`5`):**
  - `4` disputed Nov 7 `KMIA` (`$50.51` cost basis: `6707503` `35 NO`, `6707502` `17 YES`) — **100% locked under `D-001` non-interference**
  - `1` active `MKR_LOCK1` (`mkt 7000344`, `7.0 sh @ $0.995 = $6.965`, resting SELL `@ $0.998`)
- **Live Strategy Firewall (`v6.2`):** `riskless_only_mode = true`, `BOND1 = true`, `S2_TWAP = false`, directional/lattice strategies hard-disabled.

---

## 2. Empirical Realized Run-Rate vs. `$0.8223/day` VM Cost

- **VM Hurdle (`$24.67/month`):** **`$0.8223/day`** (`+6.98 bps/hr` required on `$49.12` floor)
- **Trailing 24h Pure-Riskless Live:** `7W / 0L` (`+$0.2100`, `$43.08` notional, `+$0.2100/d`, `+1.78 bps/hr` -> **`-$0.6123/d` net after VM**)
- **Trailing 72h Pure-Riskless Live:** `19W / 0L` (`+$0.7000`, `$132.42` notional, `+$0.2333/d`, `+1.98 bps/hr` -> **`-$0.5890/d` net after VM**)
- **Trailing 7d Pure-Riskless Live (`Pre-v6.2` Status Quo):** `58W / 0L` (`+$3.0841`, `$430.85` notional, `$0.05` fees, **`+$0.4406/d`**, `+3.74 bps/hr` -> **`-$0.3817/d` net after VM**)
  - *30d Linear Status-Quo Carry-Only Projection:* `$62.34` gross equity (`+$13.22` gross vs `$24.67` VM -> **`-$11.45` net after VM**)
- **Key Takeaway:** Pre-`v6.2` carry-only wins `100%` of settled trades (`58/58` over 7d) but needs live `v6.2` multi-leg / `C1` / `D1` / `Full-Throttle` `CLASS_A/B` fills to cross `+6.98 bps/hr` and cover VM overhead.

---

## 3. Modeled `v6.2` Target-Capacity Checkpoints (`$49.12` Anchor)

| Horizon | Date (UTC) | Status-Quo (`+$0.44/d`) | P25 Cons ($) | **P50 Base ($)** | P75 LowLat ($) | Cum VM ($) | **P50 Net-VM ($)** | Milestone / Note |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Day 1** | 2026-11-13 | `$49.56` (`-$0.38`) | `$50.17` | **`$50.98`** (`+$1.86/d`) | `$52.17` | `$0.82` | **`+$1.04`** | `v6.2` seed velocity |
| **Day 7** | 2026-11-19 | `$52.20` (`-$2.68`) | `$56.94` | **`$63.71`** (`+$2.31/d`) | `$74.65` | `$5.76` | **`+$8.83`** | Clears VM in all 3 bands |
| **Day 14** | 2026-11-26 | `$55.29` (`-$5.34`) | `$65.94` | **`$82.32`** (`+$2.93/d`) | `$112.04` | `$11.51` | **`+$21.69`** | P75 crosses `$100` on D13 |
| **Day 30** | 2026-12-12 | `$62.34` (`-$11.45`) | `$91.74` | **`$146.23`** (`+$5.43/d`) | `$293.10` | `$24.67` | **`+$72.44`** | P50 unlocks `$140` Pre-Split Gun |
| **Day 60** | 2027-01-11 | — | `$170.22` | **`$443.54`** (`+$14.65/d`) | `$1,118.51` | `$49.34` | **`+$345.08`** | Above `$253` Stage G gate |
| **Day 90** | 2027-02-10 | — | `$323.20` | **`$975.97`** (`+$19.36/d`) | `$2,188.44` | `$74.01` | **`+$852.84`** | Approaching `$1,000` (D92) |

- **Favorable `+$52` `KMIA` UMA Resolution (`$101.12` starting cash):** `D01 P50 $104.78 (+$3.66/d)`, `D07 P50 $129.75`, `D14 P50 $168.26`, `D30 P50 $308.01 (+$182.22 net VM)`, `D60 P50 $781.69`, `D90 P50 $1,389.04`; cuts `$150` ETA from `31d` -> `11d`, `$253` from `45d` -> `25d`, and `$500` from `64d` -> `44d`.
- **Non-Cash Shadow Universe (`D-009` Segregated):** Full-Throttle tracks `19,603` events / `365,654` markets / `5,689` graph edges / `1,227` rule-trap blocks / `1,200` dormant arbs / `+$541.25` Family L shadow PnL; `16` open shadow positions and `115` resting shadow maker bids (non-cash).

---

## 4. Full Daily Schedule Link & Engineering Notes

- Full **Days 1–30** table, **Day 180 / Day 365** trajectories, and complete milestone table: [`FULL_THROTTLE_STRATEGY_AND_PROJECTIONS_REPORT.md`](FULL_THROTTLE_STRATEGY_AND_PROJECTIONS_REPORT.md)
- Reconciled projection code & shadow NAV alignment: [`scripts/polymarket_daily_projections.py`](scripts/polymarket_daily_projections.py) and [`src/polymarket_research/alpha_124_shadow_daemon.py`](src/polymarket_research/alpha_124_shadow_daemon.py)
