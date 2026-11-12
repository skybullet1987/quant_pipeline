# DOMINUS — Daily Command Center & Live Trajectory Report (v5.2 Full-Throttle Edition)

**Generated:** `2026-11-11 22:51 UTC` | **Operating Mode:** `RISKLESS_PAA` (`directional.riskless_only_mode = true`, `proposal_only_live_promotion = true`)  
**Production Host:** `kraken-finland` (`europe-north1-b`, `2` vCPU / `3,907 MiB` physical RAM, **`MemorySwapMax=0B`**, `$24.67/mo` = `$0.8223/day`)  
**Companion Deep-Dive:** [FULL_THROTTLE_STRATEGY_AND_PROJECTIONS_REPORT.md](FULL_THROTTLE_STRATEGY_AND_PROJECTIONS_REPORT.md) | **Projection JSON:** `data/polymarket/live_daily_projections.json`

---

## 1. Reconciled Live Wallet, Three Distinct NAVs & Active Orders (`D-001` / `D-009`)

Realized on-chain `pUSD`, frozen disputed `KMIA` cost basis, and simulated shadow ledgers are strictly segregated:

| Metric | Authoritative Value | Operational Rule / Verification |
| :--- | :--- | :--- |
| **True Worst-Case Guaranteed-Floor NAV (`locked_floor_equity`)** | **`$48.70`** (`$48.6951`) | `$41.7441` free `pUSD` + `$6.9510` resting `BOND1` CLOB maker (`6947122`, `7 sh @ $0.9930`, `36.42 bps/hr`) + `$0.00` worst-case on 4 disputed `KMIA` positions. **Primary sizing & compounding anchor (`D-009`).** |
| **Mark-to-Bid Liquidation NAV (`reconciled_nav_usd`)** | **`$48.83`** | `$48.6951` cash/maker + `$0.1390` live CLOB bid across `52.0` disputed `KMIA` shares. |
| **Persisted Harvester Book Equity (`total_account_equity`)** | **`$99.21`** | Includes `$50.51` frozen `KMIA` cost basis (`6707503` `35.0 NO` sh + `6707502` `17.0 YES` sh — `4/4` untouched per `D-001`). **Never used for clip sizing or milestone ETAs.** |
| **Pure-Riskless Live Realized Record** | **`79W / 0L` (`100.0%` WR), `+$19.25` net** | `77W/0L` (`+$17.93`) baseline + `2` recent `BOND1` fills (`+$1.32`); `sign=0.56–1.04ms`, `post=73–81ms`. |
| **Infrastructure Breakeven Hurdle** | **`$0.8223/day` (`+7.04 bps/hr` @ `$48.70`)** | Cleared at Day 1 across P25 (`+8.90 bps/hr`), P50 (`+15.83 bps/hr`), and P75 (`+25.84 bps/hr`). |

---

## 2. `kraken-finland` 6-Service Production Fleet & Full-Throttle Telemetry

| Service Unit | Role & Wave 3 Full-Throttle Upgrade | Swapless `MemoryMax` (`D-010`) | Key Telemetry Surface (Command Center v6.3) |
| :--- | :--- | :---: | :--- |
| **`polymarket-live-harvester.service`** | Live `RISKLESS_PAA` execution (`opp_token_id` lookup, `900s` sticky FIFO #1 hold, `7.5 bps/hr` `<=24h` Stage C gate, `CLASS_A/B` 2-leg bridge) | `650 MiB` (`MemorySwapMax=0B`) | `data/polymarket/live_harvester_state.json` (`live_riskless_funnel`, `reconciled_nav_usd`) |
| **`polymarket-alpha124-shadow.service`** | `18.0s` independent `606`-market `UMA` bond loop, `1,200` `0%`-fee binaries (`>=15 bps`), `283` `NegRisk` slates (`36+36` rotation), `5x250=1,250` WS tokens, `45s` state heartbeat | `1,100 MiB` (`rest_cache <= 800`, `UMA` slimming) | `data/alpha124/alpha124_shadow_state.json` & mirror (`updated_ts`, `catalog_counts`, `live_bridge_telemetry`) |
| **`polymarket-full-throttle-sweep.service` / `.timer`** | `19,257` events / `375,963` total (`201,218` active) registry, `6,097` `MarketPropositionGraph` edges, `514` rule-trap vetoes, `1,200` dormant near-arbs, `Family L` shadow (`+$0.17`) | `512 MiB` (`<150 MiB` actual RSS) | `data/full_throttle/pipeline/dashboard_latest.json` & `data/universe/coverage_snapshot.json` |
| **`polymarket-recorder.service`** | Sub-second L2 orderbook & fast `D1` IPC feed (`sqlite3` WAL bounded) | `600 MiB` (`MemorySwapMax=0B`) | `data/polymarket/fast_d1_ipc.jsonl` |
| **`polymarket-cross-venue-shadow.service`** | `Stage G` 6-venue shadow certification (`CA-ON`-legal `ForecastEx` / `STX` priority for `$253` gate) | `550 MiB` (`MemorySwapMax=0B`) | `data/cross_venue_shadow/certification_report.json` |
| **`paa-monitor.timer` / `paa-supervisor.timer` / `paa-director.timer`** | `1m` heartbeat & on-chain `pUSD`/ERC-1155 reconciliation (`$1.50` / `0.75` sh safeguard), `2m` supervisor, `15m` director | One-shot bounded timers | `data/polymarket/paa/dashboard_state.json` |

---

## 3. Reconciled `v5.2` Compounding Schedule (`$48.70` Guaranteed-Floor Anchor)

Model: `v5.2_full_throttle_riskless_velocity` (`<=92%` working capital, `<=15%` per-event `D-006` cap, `0` directional/quarantined sleeves, **non-cash projection**):

| Horizon | Date (`UTC`) | P25 Conservative | P50 Base (`kraken-finland`) | P75 Low-Latency Upside | P50 Daily Rate | P25 Net (Post-VM) | P50 Net (Post-VM) | P75 Net (Post-VM) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Day 1** | `2026-11-11` | `$49.74` | **`$50.55`** | `$51.72` | `+$1.85/d` | `+$0.22` | **`+$1.03`** | `+$2.20` |
| **Day 7** | `2026-11-17` | `$56.44` | **`$63.19`** | `$74.04` | `+$2.30/d` | `+$1.98` | **`+$8.73`** | `+$19.58` |
| **Day 14** | `2026-11-24` | `$65.37` | **`$81.67`** | `$111.17` | `+$2.92/d` | `+$5.16` | **`+$21.46`** | `+$50.96` |
| **Day 30** | `2026-12-10` | `$90.89` | **`$144.88`** | `$289.76` | `+$5.14/d` | `+$17.52` | **`+$71.51`** | `+$216.39` |
| **Day 60** | `2027-01-09` | `$168.56` | **`$439.94`** | `$1,112.73` | `+$14.60/d` | `+$70.52` | **`+$341.90`** | `+$1,014.69` |
| **Day 90** | `2027-02-08` | `$320.03` | **`$971.45`** | `$2,182.11` | `+$19.33/d` | `+$197.32` | **`+$848.74`** | `+$2,059.40` |

### Key Undisputed Floor Milestone ETAs
- **`$150` (`M3.2` `PreSplitOverroundGun` + `MKR_REWARD`/`Family L`):** `P75 Day 20` | **`P50 Day 31` (`2026-12-11`)** | `P25 Day 55` *(or **`P50 Day 12`** if `KMIA` resolves `+$52` -> `$100.70`)*
- **`$253` (`Stage G` Regulated `CA-ON` Cross-Venue Review):** `P75 Day 28` | **`P50 Day 45` (`2026-12-25`)** | `P25 Day 80` *(or **`P50 Day 25`** on favorable `KMIA`)*
- **`$500` (`>=3`-Leg Atomic `NegRiskAdapter` Unlock, `D-007`):** `P75 Day 40` | **`P50 Day 64` (`2027-01-13`)** | `P25 Day 113` *(or **`P50 Day 45`** on favorable `KMIA`)*
- **`$5,000` (`proposal_only_live_promotion` Graduation Gate, `D-002`):** `P75 Day 162` | **`P50 Day 264` (`2027-08-01`)** | `P25 Day 469` *(or **`P50 Day 244`** on favorable `KMIA`)*

---

## 4. Operator Quick-Reference Commands

- **Launch Live HTML Command Center (Local Windows -> `kraken-finland` SSH Probe):**
  ```powershell
  & "C:\Program Files\LibreOffice\program\python.exe" scripts/dominus_command_center.py --port 8765
  ```
- **Refresh 90-Day Reconciled Projections JSON Atomically:**
  ```powershell
  & "C:\Program Files\LibreOffice\program\python.exe" scripts/polymarket_daily_projections.py --days 90
  ```
- **Emergency Controls (`kraken-finland`):**
  - Pause PAA autonomy only: `python3 scripts/paa_cli.py emergency-stop --reason "owner_review"`
  - Full live trading halt + CLOB cancel: `python3 scripts/paa_cli.py emergency-stop --include-trading --reason "owner_halt"`
  - Resume: `python3 scripts/paa_cli.py resume [--include-trading]`
