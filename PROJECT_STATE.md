# Dominus v5.0 Reconciled Project, Financial & Infrastructure State

**Snapshot Timestamps:** Initial Baseline `2026-11-11 00:25:57 UTC` | Post-Audit `00:51:00 UTC` | v5.0 Deploy & `$1.00` Sweep `04:15:00 UTC` | **Post-v5.1 Catalog Expansion & QA Deploy `2026-11-11 07:16:00 UTC`**  
**Author:** Agent F (`@reliability`) & Principal Orchestrator (Post-Deploy Update)  
**On-Chain Wallet (`Funder`):** `0x013A2474454fBd8738cff6a7f204eF1bc377F4e9` (Polygon Mainnet `chain_id=137`)  
**Operating Mode:** `RISKLESS_PAA` (`directional.riskless_only_mode = true`, `proposal_only_live_promotion = true`, Jurisdiction Gate = `CA-ON`)

> [!NOTE]
> **Post-v5.1 Live Update (`2026-11-11 07:16 UTC`):** Following Owner Approval Packages 1–3 (`04:15 UTC`) and the `v5.1` Riskless Catalog Expansion + Full-Repo QA deploy (`07:14 UTC`, `203/203` manifest parity):
> - **Liquid Wallet Collateral (`live_bankroll` / `pUSD`):** **`$48.695132` (`$48.70`)** (`$47.377122` baseline + `+$1.000000` EOA `USDC.e -> pUSD` sweep + **`+$0.318010`** cumulative new live riskless realized cash wins today; `$0.000000` discrepancy vs on-chain `pUSD`).
> - **Three Updated NAV Definitions (`07:16 UTC`):** True Worst-Case Guaranteed-Floor NAV = **`$48.70`** (`$48.695132` cash + `$0.00` disputed `KMIA`); Mark-to-Bid Liquidation NAV = **`$48.83`** (`$48.695132` + `$0.1390` CLOB bid); Persisted Book Equity (`total_account_equity`) = **`$99.21`** (`$99.205132`). Live Harvester persists `reconciled_nav_usd = $48.6951` and `current_equity_tier = "UNLEASHED_LAUNCH"` (sizing strictly off reconciled NAV rather than `$99.21` book equity).
> - **Signer EOA (`0x9703b71686219d34869e8fb89a93263f9e0d50a5`):** **`41.77932547 POL`** gas reserve (`0.000000 USDC.e`; transfer tx `0xf932614cc293f2065764207cfce2a1f8454a4675dc13a05216d58851fc8b26fc`, Relayer V2 1:1 `pUSD` wrap tx `0x614436cb4c02e6d6330ce174afafec3a1f767a7848726b66f9519c3a0a13f1d9`).
> - **4 Disputed `KMIA` Nov 7 Positions (`$50.51` cost basis):** `100%` untouched (`exit_order_id = None`, `unwind_order_id = None`, excluded from active non-frozen `cur_open_exp`).

---

## 1. Authoritative Financial & NAV Reconciliation (`kraken-finland`)

Cross-verified across `data/polymarket/live_harvester_state.json`, `data/backups/live_harvester_state_pre_1a_restart.json`, `data/polymarket/paa/authoritative_financial_ledger.json`, [audit_losing_trades.py](file:///C:/Users/Anton/source/repos/Dominus/audit_losing_trades.py), [polymarket_daily_projections.py](file:///C:/Users/Anton/source/repos/Dominus/scripts/polymarket_daily_projections.py), and [dominus_command_center.py](file:///C:/Users/Anton/source/repos/Dominus/scripts/dominus_command_center.py):

| Metric | Exact Value (USD) | Source / Formula | Verification Status |
| :--- | :--- | :--- | :--- |
| **Liquid Wallet Collateral (`live_bankroll` / `pUSD`)** | **`$47.377122`** (`$47.38`) | On-chain wrapped `pUSD` (`$47.377122`) + unwrapped `USDC.e` (`$0.00`) | **VERIFIED** (`accounting_ok = true`, `0` discrepancy) |
| **Open CLOB Orders (`clob_open_orders_count`)** | **`0` at `00:25:57Z`** -> **`1` at `00:47:52Z`** (`$8.919` quoting) | At `00:25:57Z`: `0` orders (`$0.00` locked). At `00:47:52Z`: `1` normal live `MKR_LOCK1` Dota2 `BOND1` bid (`$8.919` on `market_id=6916999`, `$38.458` free + `$8.919` quoting = `$47.377`); **`0` orders on `KMIA`** | **VERIFIED** (`0` orphan orders) |
| **Open Positions Cost Basis (`open_cost_basis_usd`)** | **`$50.510000`** (`51.6%` of book) | `4` disputed `KMIA` Nov 7 legs (`$19.54 + $16.32 + $9.77 + $4.88`; entry fees `$0.07224`; `$50.56` incl. tracked cash fees) | **VERIFIED** (`100%` match vs. `pre_1a` backup) |
| **Book Equity (`total_account_equity`)** | **`$97.887122`** (`$97.89`) | `$47.377122` liquid collateral + `$50.51` open cost basis (`$97.959362` incl. `$0.07224` entry fees) | **VERIFIED** |
| **Mark-to-Bid Liquidation NAV (`portfolio_nav_mark_to_bid_usd`)** | **`$47.516100`** (`$47.52`) | `$47.377122` collateral + `$0.1390` best-bid value (`35 sh @ $0.003 = $0.105` + `17 sh @ $0.002 = $0.034`) | **VERIFIED** (`-$50.371` unrealized mark-to-bid drawdown) |
| **True Worst-Case Guaranteed-Floor NAV** | **`$47.377122`** (`$47.38`) | `$47.377122` collateral + **`$0.00`** worst-case UMA DVM payout across all 4 disputed non-box `KMIA` legs | **AUTHORITATIVE CONSERVATIVE FLOOR** |
| **Code-Computed Floor (`locked_floor_equity` / `_guaranteed_redeem_equity_usd`)** | **Patched Locally -> `$47.38`** *(Remote unpatched: `$82.38` / `$81.57`)* | Unpatched remote valued `35 sh` disputed `WS_SNIPE` `SINGLE_LEG_LOCK` at `$35.00` par / `$34.19` cost (`F-02`); **local patch in [`compute_live_equity_and_rates`](file:///C:/Users/Anton/source/repos/Dominus/scripts/polymarket_daily_projections.py#L1135-L1190) & [`_compute_cc_valuations`](file:///C:/Users/Anton/source/repos/Dominus/scripts/dominus_command_center.py#L474-L558) now returns exact `$47.38`** | **FIXED LOCALLY & UNIT-TESTED (`F-02`)** |
| **Resting-Maker Theoretical Target NAV** | `$99.152100` (`$99.15`) | Assumes all `52` disputed shares resolve/exit at `$0.990–$1.000` (`clob_order_live = false`) | Theoretical upper bound only |

### 1.1 Conservative Guaranteed-Floor Valuation Audit & Local Remediation (`F-02`)
On Nov 10, QA Group 3 patched [`polymarket_daily_projections.py`](file:///C:/Users/Anton/source/repos/Dominus/scripts/polymarket_daily_projections.py) and [`dominus_command_center.py`](file:///C:/Users/Anton/source/repos/Dominus/scripts/dominus_command_center.py) so unhedged `_UNWRESID_` / `MULTI_LEG_RESIDUAL` positions (`17.0 sh` on market `6707502`) carried `$0.00` guaranteed floor instead of `$17.00`, but left disputed `SINGLE_LEG_LOCK` (`WS_SNIPE_Miami_KMIA_*`) valued at `$35.00` par (`$82.38`) and `$34.19` cost (`$81.57`) — and relied on `has_unhedged_residual` to bypass `max(live_equity, raw_floor_sum)`.
- **Local Remediation Applied (`F-02`):** Both [`compute_live_equity_and_rates`](file:///C:/Users/Anton/source/repos/Dominus/scripts/polymarket_daily_projections.py#L1135-L1190) (`_is_uma_disputed_position` + `has_floor_haircut`) and [`_compute_cc_valuations`](file:///C:/Users/Anton/source/repos/Dominus/scripts/dominus_command_center.py#L474-L558) (`_is_uma_disputed_cc` + `_is_floor_zero_cc`) now assign **`$0.00`** worst-case guaranteed redemption value to any position with `umaResolutionStatus == "disputed"` (whether or not an `_UNWRESID_` leg is also present), yielding **`$47.38`** guaranteed floor while preserving Book Equity (`$97.89`) and Mark-to-Bid NAV (`$47.52`) intact. Verified in [test_phase0_reliability_fixes.py](file:///C:/Users/Anton/source/repos/Dominus/tests/test_phase0_reliability_fixes.py).

---

## 2. Disputed Miami (`KMIA` Nov 7) Open Positions — 100% Untouched Verification

All 4 open positions stem from the Nov 7 `KMIA` ASOS `$` maintenance sensor incident across Polymarket markets `6707503` and `6707502` (owner has an official open case with Polymarket). Verified again at `00:51 UTC` on-chain (`ERC-1155`) and in `live_harvester_state.json` with **zero exit orders, zero unwind orders, and zero mutations** relative to `live_harvester_state_pre_1a_restart.json`:

| `trade_id` | Sleeve / `box_type` | `market_id` | Side & Shares (`Ledger` / `On-Chain Token Total`) | Entry Px | Cost Basis (`Fee`) | Best Bid / Ask | `umaResolutionStatus` | `exit_order_id` | `unwind_order_id` | `is_liquidating` / `clob_order_live` |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `WS_SNIPE_Miami_KMIA_242960` | `W_PRUNE1_DEAD_NO_BOND` (`SINGLE_LEG_LOCK`) | `6707503` | `NO` — `20.0` sh (`35.0` sh total on token `66521461...`) | `$0.977` | `$19.54` (`$0.0225`) | `$0.003` / `$0.049` | `"disputed"` | `None` | `None` | `False` / `False` |
| `MULTI_LEG_BUNDLE_LIVE_KMIA_1794113999_318559_UNWRESID_20116898_1794111898` | `W_PRUNE1_NR0_BASKET` (`MULTI_LEG_RESIDUAL`) | `6707502` | `YES` — `17.0` sh (`17.0` sh on token `20116898...`) | `$0.960` | `$16.32` (`$0.03264`) | `$0.002` / `$0.020` | `"disputed"` | `None` | `None` | `False` / `False` |
| `WS_SNIPE_Miami_KMIA_688670` | `W_PRUNE1_DEAD_NO_BOND` (`SINGLE_LEG_LOCK`) | `6707503` | `NO` — `10.0` sh (`35.0` sh total on token `66521461...`) | `$0.977` | `$9.77` (`$0.0112`) | `$0.003` / `$0.049` | `"disputed"` | `None` | `None` | `False` / `False` |
| `WS_SNIPE_Miami_KMIA_837595` | `W_PRUNE1_DEAD_NO_BOND` (`SINGLE_LEG_LOCK`) | `6707503` | `NO` — `5.0` sh (`35.0` sh total on token `66521461...`) | `$0.976` | `$4.88` (`$0.0059`) | `$0.003` / `$0.049` | `"disputed"` | `None` | `None` | `False` / `False` |
| **TOTAL (`4` Positions)** | **2 Markets (`6707503`, `6707502`)** | — | **`52.0` shares (`35.0 NO` + `17.0 YES`)** | — | **`$50.51`** (`$0.07224`) | **`$0.139` Bid Value** | **All `"disputed"`** | **All `None`** | **All `None`** | **100% Untouched** |

---

## 3. Historical Realized P&L & Exact Record Decomposition (`136` Closed Records)

### 3.1 Aggregate Realized P&L & Closed-Record Decomposition
- **`audit_losing_trades.py --check` Status:** `"ALL_GOOD"` (`healthy = true`, `risk_halt = false`, `uninspected_losses_count = 0`, `profits_skipped = 160`, `expected_losses_ok = 8`, `bugs_fixed_and_redeployed = 26`, `param_wfo_queued = 1`).
- **Exact Decomposition of All `136` `closed_positions` Records (`118 + 8 + 10 = 136`):**
  1. **`118` Real Filled Economic Trades:** `77` pure-riskless filled trades (`77W / 0L`, **`+$17.9281`**) + `41` retired directional/lattice filled trades (`30W / 11L`, **`-$73.3385`**) = **`118` real filled trades** netting **`-$55.4104`** exact wallet cash P&L (`+$17.9281 + (-$73.3385) = -$55.4104`, **`$0.0000` discrepancy**).
  2. **`8` Flat Pre-Split Complete-Set Merges:** `$0.0000` net P&L impact.
  3. **`10` Zero-Fill / Cancelled / Phantom Records (`$0.0000` cash impact):** `8` zero-fill post-only Maker records in `phantom_unfilled_records` (`3` `BOND1`, `2` `D1`, `3` `S2`) + `2` zero-fill/cancelled `SOC2_EXACT_SCORE_2D_LATTICE` records (`4` total `SOC2` rows in raw `closed_positions` minus `2` real filled `SOC2` trades).
- **Raw vs. Wallet-Reconciled Totals:**
  - **Raw State Ledger Net P&L:** **`-$55.9704`** (`+$108.4881` gross wins, `-$164.4585` gross losses across `$1,836.884` raw notional and `$13.3257` fees).
  - **Reconciled Wallet Cash Realized Net P&L:** **`-$55.4104`** (`+$0.5600` non-cash unfilled leg adjustment on `CM_B3_PYTH_BARRIER_BOX`: `-$55.9704 + $0.5600 = -$55.4104`).
  - **Net Economic Profit After Recorded PAA Ops (`$0.1313` AI + `$0.0305` daily VM slice):** **`-$55.5722`** *(Full `kraken-finland` GCP VM run-rate is **`$24.67/month` = `~$0.822/day`**, a `633%/yr` fixed hurdle against `$47.38` liquid cash).*

### 3.2 Realized Performance by Regime & Sleeve (`authoritative_financial_ledger.json`)

| Regime / Sleeve | Real Filled Trades | Wins / Losses | Verified Net P&L (USD) | Fees Paid (USD) | Notional (USD) | Current Live Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Pure-Riskless Mandate Sleeves (All-Time Combined)** | **`77`** | **`77W / 0L` (`100.0%`)** | **`+$17.9281`** *(Post-Lock subset: `72` trades, `+$17.1381`)* | **`$0.5825`** | **`$867.79`** | **ACTIVE (`Grad-8` gated)** |
| ↳ `D1_SAME_ORACLE_DOMINANCE_BOX` | `3` | `3W / 0L` | `+$12.7200` | `$0.1890` | `$32.30` | `grad8_live_authorized` |
| ↳ `BOND1_UMA_RESOLUTION_CARRY` | `60` | `60W / 0L` | `+$3.6181` | `$0.0569` | `$701.27` | `grad8_live_authorized` |
| ↳ `S2_RTDS_EXACT_TWAP_INTEGRATOR` | `4` | `4W / 0L` | `+$0.4700` | `$0.0276` | `$35.51` | Paused (`legging/tail gate`) |
| ↳ `MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER` | `3` | `3W / 0L` | `+$0.4000` | `$0.0054` | `$26.57` | Active post-clinch |
| ↳ `CM_B3_PYTH_BARRIER_BOX` | `1` | `1W / 0L` | `+$0.3200` | `$0.2772` | `$15.84` | Paused (`legging-risk`) |
| ↳ `SP2_NBA_ENDGAME_LOCK` / `SP4` / `BOND2` / `W_PRUNE1` | `6` | `6W / 0L` | `+$0.4000` | `$0.0264` | `$56.30` | Gated / capped |
| **Retired Legacy Directional / Multi-Leg Sleeves** | **`41`** | **`30W / 11L`** | **`-$73.3385`** | **`$12.7432`** | **`$873.11`** | **HARD-DISABLED** |
| ↳ `SLEEVE_1_SUBHOURLY_15M` | `32` | `24W / 8L` | `-$55.2400` | `$8.8467` | `$676.08` | Forbidden in `RISKLESS_PAA` |
| ↳ `SLEEVE_1_CORE_302` | `7` | `6W / 1L` | `-$9.4300` | `$1.5558` | `$132.45` | Forbidden in `RISKLESS_PAA` |
| ↳ `SOC2_EXACT_SCORE_2D_LATTICE` | `2` | `0W / 2L` | `-$8.6685` | `$2.3407` | `$64.58` | Paused (`non-atomic lattice`) |
| **ALL REAL FILLED TRADES (`77 + 41`)** | **`118`** | **`107W / 11L`** | **`-$55.4104`** | **`$13.3257`** | **`$1,740.90`** | **Exact Wallet Cash Match** |

---

## 4. Infrastructure, Memory Root-Cause (`F-01`) & SQLite Forensics (`F-04`)

### 4.1 Compute, Memory Envelope & `F-01` Root-Cause Diagnosis (`kraken-finland`)
- **CPU (`2` vCPUs, `europe-north1-b` Finland):** Uptime `2 days, 20h+`; load average `2.27–3.22 / 2.55–2.75 / 2.65–2.71`.
- **Host & Cgroup Memory Envelope (`3,907 MiB` Physical RAM, `MemorySwapMax=0B`):** Although `4,095 MiB` swap exists on disk (`free -m`), `.config/systemd/user.control/*.service.d/50-MemorySwapMax.conf` enforces **`MemorySwapMax=0`** on `polymarket-alpha124-shadow.service` (`MemoryMax=1550M`), `polymarket-recorder.service` (`MemoryMax=1150M`), and `polymarket-live-harvester.service`. With `live-harvester` (`344 MiB`), `cross-venue-shadow` (`295–317 MiB`), SSH dashboard probe `PID 265402` (`88 MiB`), and OS/kernel/journald (`~550 MiB`) consuming `~1,290 MiB`, only **`~2,615 MiB` physical RAM** remains for `recorder + alpha124-shadow + periodic timers` — less than their `1,150M + 1,550M = 2,700M` unit sum!
- **Exact `F-01` Three-Way OOM Mechanism:**
  1. **`polymarket-alpha124-shadow.service` (`--riskless-bridge-only`):** Climbs to `1,048 MiB` `VmRSS` / `1,209 MiB` `VmHWM` (`RssAnon=1,012 MiB`, `Threads=14`) within 20 min because `discover_all_markets()` retains multi-KB Gamma descriptions across `~140` `lp2_events_by_slug` + all `multisport_raw_events`, holds `~400–500 MiB` of raw Gamma JSON pages simultaneously across 14 glibc malloc arenas without `malloc_trim(0)`, and caches untrimmed deep L2 books in `_rest_books_cache` / `_ws_raw_levels`.
  2. **`polymarket-recorder.service` (`--asset BTC --co-assets ETH,SOL,XAU,XAG,XRP,BNB,DOGE,HYPE,ZEC --riskless-bus-only`):** Runs 10 `PolymarketDualFeed1HRecorder` instances in one process and climbed from `367 MiB` (`20m` post-restart) to **`1,007.1 MiB`** over `25h 25m` because even in `--riskless-bus-only` mode it spawned 30-minute `verify_and_log_resolution()` Gamma-polling tasks on every `5m/15m/1h/4h` rollover (`~170` tasks/hr across 10 assets), opened `10 x TCPConnector(limit=100) = 1,000` OpenSSL pool slots, hammered Gamma `/events` every `10s` on co-assets without `1h/5m` markets, and never trimmed L2 dust levels or glibc arenas.
  3. **Triggering 5-Minute Spike (`polymarket-paa-watchdog.timer`):** Every 5 minutes (`*:00/5:30`), `scripts/paa_cli.py scan-cycle` (`MemoryMax=1536M`) spikes **`355–457 MiB` RSS**, pushing host RAM past `3,907 MiB` whenever `recorder + alpha124 > ~2,160 MiB` and invoking the kernel OOM killer (`OOMScoreAdjust=500` kills `alpha124-shadow` first).
- **Disk & `/dev/shm`:** `33 GiB` used / **`64 GiB` available (`34%`)** on `96 GiB` `/dev/root`; `/dev/shm` uses `128 KiB` (`1%`). CLOB HTTP `p50 = 65.99 ms`, `p99 = 143.17 ms`.

### 4.2 SQLite & JSONL Storage Footprint (`F-04` Read-Only `dbstat` Audit at `00:51 UTC`)

| Database / Ledger Path | Size (`00:51 UTC`) | Exact `dbstat` Space & Hourly Growth Breakdown |
| :--- | :--- | :--- |
| `data/cross_venue_shadow/shadow_telemetry.sqlite3` | **`518.88 MiB`** (`544,088,064 B`, `132,834` pages @ `4,096 B`, `freelist=0`, `WAL`, `auto_vacuum=0`) | **`38` objects (`13` user tables + `23` indexes):**<br>1. **`orderbook_snapshots` + 4 indexes = `298.39 MiB` (`57.5%`)** across `518,959` rows (`24,217` rows/last 1h; `27,364` rows/hr 3h avg): table `201.81 MiB` (`l2_json` payload: Polymarket `6,384/h @ 475.7 B = 2.90 MiB/h`, Predict.fun `3,893/h = 0.66 MiB/h`, Limitless `2,758/h = 0.60 MiB/h`, ForecastEx `6,000/h = 0.44 MiB/h`, SX Bet `5,138/h = 0.44 MiB/h`) + indexes `96.58 MiB` (`UNIQUE(event_uid)` `36.05 MiB`, `idx_ob_venue_origin_depth` `23.12 MiB`, duplicate pair `idx_ob_ts_origin` `18.71 MiB` & `idx_ob_origin_ts` `18.70 MiB`).<br>2. **`rejected_opportunities` + 4 indexes = `137.51 MiB` (`26.5%`)** across `225,489` rows (`4,099` rows/last 1h; `5,035` rows/hr 3h avg; `78.6%` is `REJECTED_INSUFFICIENT_L2_DEPTH` at `3,222/h`): table `62.36 MiB` + indexes **`75.15 MiB`** (`UNIQUE(reject_uid)` `30.93 MiB`, `idx_rej_stage_reason` `20.73 MiB`, `idx_rej_origin_reason_ts` `16.47 MiB`, `idx_rej_ts_origin` `7.02 MiB`).<br>3. **`arbitrage_signals` + 2 indexes = `78.88 MiB` (`15.2%`)** across `19,393` rows (`42.7` rows/hr; `19,438` pages = `75.93 MiB` table, ~1 row/page due to 4 large JSON columns).<br>4. **Remaining 10 tables + indexes = `4.10 MiB` (`0.8%`)** (`market_catalog` `2.59 MiB`, `pairing_candidates` `0.96 MiB`, `venue_freshness_samples` `0.46 MiB`). *(Remediation committed on `@mof-crossvenue` branch `c206fea1`.)* |
| `data/backups/shadow_telemetry_pre_compact.sqlite3.gz` | `138.59 MiB` (`145,324,038 B`) | Lossless gzip archive created `2026-11-10 21:12:18 UTC`. |
| `data/alpha124/alpha124_shadow_ledger.jsonl` | **`138.4 MiB`** (`145,133,355 B`) | Stream-hydrated in two passes (`421` active/recent closed records retained in slimmed memory). |
| `data/polymarket/paa/paa_tasks.db` | **`42.0 MiB`** | Durable PAA SQLite store (`445` `COMPLETED`, `2` `VERIFIED_COMPLETE`, `39` `ESCALATED`, `0` active/pending). |
| `data/cross_venue_shadow/cross_venue_funnel.jsonl` | `31.0 MiB` | Stage G cross-venue funnel JSONL log. |
| Legacy root/experiment DBs | `~14.5 MiB` combined | Cold historical SQLite artifacts from Aug–Oct (`0 B` on `live_trades.db` & `paa_autonomy.db`). |
