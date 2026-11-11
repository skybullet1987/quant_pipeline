# Dominus Deployment Status & Runtime Reality Reconciliation

**Reconciled At:** Initial Baseline `2026-11-11 00:26 UTC` | Post-OOM Audit `00:51 UTC` | v5.0 Deploy `04:15 UTC` | 6-Venue Shadow `05:25 UTC` | **v5.1 Riskless Catalog Expansion & Full-Repo QA Deploy `2026-11-11 07:16 UTC`**  
**Author:** Agent F (`@reliability`) & Principal Orchestrator (Post-Deploy Update)  
**Production Host:** `kraken-finland` (`quant-pipeline-finland.europe-north1-b.c.parnasa-498503.internal`, `/home/skybullet1987/quant_pipeline`)  
**Local Workspace:** `C:/Users/Anton/source/repos/Dominus`  
**Post-Deploy Parity (`07:16 UTC`):** **`203/203` `DEPLOY_MANIFEST` files (`0` diffs)** + `polymarket_full_codebase_v4.{py,txt}` synced (`SWAPLESS_SAFE_STAGE_GATE_OK`, `<40 MiB` RSS); `alpha124-shadow` monitoring `CAL1=74` ladders (`+236%`), `UMA=66..155` proposed markets (`+200%+`), `NRC=128` closed NegRisk slates, and `340` volume-ranked `0%`-fee binaries; **`4/4` disputed `KMIA` positions `100%` untouched** (`reconciled_nav_usd=$48.6951`, `current_equity_tier="UNLEASHED_LAUNCH"`).

### 0. Live Post-v5.1 Production Fleet (`systemctl --user show` at `2026-11-11 07:16 UTC` — `1,686 MiB` Available RAM, `0 B` Swap Used)

| Service Unit | `ActiveState` | `MainPID` (`07:16Z`) | `NRestarts` | `MemoryCurrent` | `CPUWeight` | `MemoryMax` | Rollback Backup |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`polymarket-live-harvester.service`** | `active` (`running`) | **`330785`** | **`0`** | `230.7 MiB` | **`400`** | `infinity` | `backups/polymarket_predeploy_20261111_071346.tar.gz` |
| **`polymarket-recorder.service`** | `active` (`running`) | **`307221`** | **`0`** | `217.6 MiB` | **`80`** | **`750.0 MiB`** | `data/backups/live_harvester_state_pre_v51.json` |
| **`polymarket-alpha124-shadow.service`** | `active` (`running`) | **`330779`** | **`0`** | `884.0 MiB` | **`50`** | **`1,100.0 MiB`** | `data/polymarket/paa/live_backups/v50_owner_control_package/` |
| **`polymarket-cross-venue-shadow.service`** | `active` (`running`) | **`330775`** | **`0`** | `182.5 MiB` | **`50`** | **`450.0 MiB`** | `backups/stage_g_shadow_20261111T051929Z.tar.gz` (`6/6` intl venues `HEALTHY`) |

---

## 1. Systemd Service Runtime Reality (`kraken-finland`)

> [!IMPORTANT]
> **User-Scope Systemd Architecture:** All Dominus daemons and timers run under **user-scope systemd** (`/home/skybullet1987/.config/systemd/user/`, queried via `XDG_RUNTIME_DIR=/run/user/1001 systemctl --user`). Querying system-scope `systemctl` without `--user` returns `Unit ... could not be found` (`ActiveState=inactive`, `MainPID=0`).

### 1.1 Core Trading, Shadow & Telemetry Services (`systemctl --user show` at `00:51 UTC`)

| Service Unit | `ActiveState` / `SubState` | `MainPID` (`00:51Z`) | `ActiveEnterTimestamp` (UTC) | `NRestarts` (`00:51Z`) | `MemoryCurrent` (`00:51Z`) | `MemoryMax` (`MemorySwapMax`) | Prior `00:26Z` `MainPID` / `NRestarts` | Command / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`polymarket-live-harvester.service`** | `active` (`running`) | **`264354`** | **`Tue 2026-11-10 22:54:37 UTC`** | **`0`** | `360.8 MiB` (`344.2 MiB` RSS) | `infinity` (`0 B` swap) | `264354` / `0` *(100% uninterrupted)* | [polymarket_live_harvester.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py) (`--dynamic-sizing --no-hold-to-maturity --exit-policy hold_98`) |
| **`polymarket-alpha124-shadow.service`** | `active` (`running`) | **`277745`** | `Wed 2026-11-11 00:31:59 UTC` | **`3`** | `1,069.5 MiB` (`1,048 MiB` RSS, `1,209 MiB` HWM) | `1,550.0 MiB` (`0 B` swap) | `273561` (`00:12:02Z`) / `1` | [alpha_124_shadow_daemon.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/alpha_124_shadow_daemon.py) (`--riskless-bridge-only`, `OOMScoreAdjust=500`) |
| **`polymarket-cross-venue-shadow.service`** | `active` (`running`) | **`277659`** | `Wed 2026-11-11 00:31:20 UTC` | **`1`** | `295.4–317.0 MiB` (`450.2 MiB` peak) | `512.0 MiB` (`0 B` swap) | `264689` (`22:55:51Z`) / `0` | [shadow_cross_venue_riskless_probe.py](file:///C:/Users/Anton/source/repos/Dominus/scripts/shadow_cross_venue_riskless_probe.py) (`--interval-sec 15 --clip-usd 25`) |
| **`polymarket-recorder.service`** *(supporting)* | `active` (`running`) | **`277732`** | `Wed 2026-11-11 00:31:52 UTC` | **`1`** | `367.1 MiB` RSS (`20m` post-restart; prior peak **`1,007.1 MiB`**) | `1,150.0 MiB` (`0 B` swap) | `145488` (`Nov 09 23:06:45Z`) / `0` | [polymarket_terminal_recorder.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_terminal_recorder.py) (`10` assets `--riskless-bus-only`) |

Also active on host:
- **Active User Timers (`10` loaded & `waiting`):** `polymarket-paa-monitor.timer` (`60s`), `polymarket-cross-venue-shadow-watchdog.timer` (`60s`), `polymarket-paa-supervisor.timer` (`120s`), **`polymarket-paa-watchdog.timer` (`300s` at `*:00/5:30`, `MemoryMax=1536M`, spikes `355–457 MiB` RSS per run)**, `polymarket-paa-director.timer` (`900s`), `polymarket-paa-hourly-opt.timer` (`1h`), `polymarket-telemetry-compactor.timer` (`2h`), `polymarket-paa-6h-eval.timer` (`6h`), `polymarket-paa-daily-report.timer` (`00:15 UTC`), and `polymarket-paa-weekly-review.timer` (`Sun 01:00 UTC`).
- **Auxiliary SSH Telemetry Stream (`PID 265402`):** Started `Tue Nov 10 22:59:46 UTC` (`88.5 MiB` RSS) via non-TTY `sshd` session (`PID 265401`) running `REMOTE_PROBE_PY` from [dominus_command_center.py](file:///C:/Users/Anton/source/repos/Dominus/scripts/dominus_command_center.py).

### 1.2 Complete `journalctl` OOM Timeline & `F-01` Root-Cause / Local Fix

> [!WARNING]
> **Host RAM Contention & `00:30:48–00:31:59 UTC` Multi-Service OOM Cascade (`F-01`):**
> - **Pre-existing Autonomous OOM Loop (`65–77 min` cycle):** `polymarket-alpha124-shadow.service` suffered recurring Linux kernel OOM kills (`Result=oom-kill`, `status=9/KILL`) every time `recorder` (`~963–1,007 MiB`) + `alpha124` (`~1,150–1,209 MiB`) coincided with the 5-minute `polymarket-paa-watchdog.service` (`paa_cli.py scan-cycle`, `355–457 MiB` RSS) spike on the `3,907 MiB` `MemorySwapMax=0B` VM (`22:39:38 UTC`, `00:11:51 UTC`).
> - **`00:30:48–00:31:59 UTC` Cascade During Initial Phase 0 Remote `pytest`:** Running the mandated Phase 0 remote `pytest` suite (`~620–676 MiB` RSS) alongside the `00:30:30Z` `paa-watchdog` spike pushed physical RAM to exhaustion, causing kernel OOM kills of `alpha124-shadow` (`00:30:48Z` & `00:31:49Z` -> `MainPID=277745`, `NRestarts=3`), `cross-venue-shadow` (`00:31:05Z` -> `MainPID=277659`, `NRestarts=1`), and `polymarket-recorder` (`00:31:42Z` -> `MainPID=277732`, `NRestarts=1`, dropping recorder RSS from `1,007.1 MiB` back to `367.1 MiB`). **`polymarket-live-harvester.service` (`MainPID=264354`, `NRestarts=0`) survived 100% untouched.**
> - **Binding Infra Safety Rule (`#11`) & Local `F-01` Patch:** Remote `pytest` and heavy >`150 MiB` processes are now strictly banned on `kraken-finland`. Locally, [alpha_124_shadow_daemon.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/alpha_124_shadow_daemon.py) and [polymarket_terminal_recorder.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_terminal_recorder.py) have been patched with raw Gamma event slimming (`>85%` payload reduction), bounded REST/WS L2 depth (`<=25` / `<=50` / `<=40` levels), `riskless_bus_only` suppression of 30-min resolution-polling tasks, bounded `TCPConnector` pools (`24` / `8`), `60s`/`120s` TTL cache eviction, and Linux `libc.malloc_trim(0)` arena reclamation.

---

## 2. Git Revision, Dirty Working Tree & SHA-256 File Parity

### 2.1 Git Repository & Working Tree State

| Environment | Path | Git Metadata / `HEAD` | Dirty / Untracked Status |
| :--- | :--- | :--- | :--- |
| **Local Workspace** | `C:\Users\Anton\source\repos\Dominus` | Root working copy (`166/166` manifest files pass `verify_local_manifest()`; branch workers run in isolated git worktrees) | Baseline matched remote `166/166` (`00:26Z`); **now contains Agent F's `6` local Phase 0 remediation + test files** (`4` modified Python + `2` new files `pytest.ini`, `tests/test_phase0_reliability_fixes.py`) |
| **Remote Production** | `kraken-finland:/home/skybullet1987/quant_pipeline` | `HEAD = 4fdb21985c5f15d26065e5c57f50bbd4771386aa` (`feat(cross-venue,qa): unlock 6-venue live shadow collection...`) | **Dirty (`55` uncommitted entries in `git status --porcelain`):** **`51` modified tracked files (`M`) + `4` untracked files (`??`)** |
| **PAA Staging Pointer** | `kraken-finland:/home/skybullet1987/paa_staging/CURRENT_RELEASE.json` | `REL_BASELINE_4fdb2198` (`commit_sha = 4fdb21985c5f15d26065e5c57f50bbd4771386aa`, activated `2026-11-10T18:13:32Z`) | Points to committed `HEAD`, **prior** to the `55` uncommitted Nov 10 QA working-tree entries (`F-03`) |

**Untracked files (`??`, `4` total) on `kraken-finland`:**
- [src/polymarket_research/honest_riskless_backtester.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/honest_riskless_backtester.py)
- [src/polymarket_research/riskless_expansion_v6_engines.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/riskless_expansion_v6_engines.py)
- [tests/test_qa_boost_audit_remediation.py](file:///C:/Users/Anton/source/repos/Dominus/tests/test_qa_boost_audit_remediation.py)
- [tests/test_riskless_remediation_and_8_new_engines.py](file:///C:/Users/Anton/source/repos/Dominus/tests/test_riskless_remediation_and_8_new_engines.py)

### 2.2 Key Deployed Files (`100%` Parity) & Locally Staged Phase 0 Remediations

All **7 required key production files** remain **100% byte-for-byte identical** between local Windows and `kraken-finland` (untouched by Agent F per scope boundary):

| Key Deployed File | SHA-256 Digest (Local == Remote `kraken-finland`) | Bytes | Local `mtime` (UTC) | Remote `mtime` (UTC) | Loaded in Active Daemon? |
| :--- | :--- | :--- | :--- | :--- | :--- |
| [src/polymarket_research/polymarket_live_harvester.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_live_harvester.py) | `d65e0de7fab86aef21c0bf97dbe3a7e38fc1aef95b5bf8fd7355b60e90c93b76` | `686,649` | `2026-11-10T20:09:47Z` | `2026-11-10T20:09:47Z` | **YES** (`mtime < 22:54:37Z` start of `PID 264354`) |
| [src/polymarket_research/riskless_protocol_v2_expansion.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/riskless_protocol_v2_expansion.py) | `1785c58f8274c6dcacaeb03f12b8c1662c93bc4304822df5d024b7a378ff1a28` | `914,077` | `2026-11-10T22:45:44Z` | `2026-11-10T22:45:44Z` | **YES** (`mtime < 22:54:37Z` start of `PID 264354`) |
| [src/polymarket_research/cross_venue_connectors.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/cross_venue_connectors.py) | `7533f4f5c6116afec9eff5d1d0ba090790da6249aa79f438e873f38f4b72b46d` | `233,958` | `2026-11-10T21:05:56Z` | `2026-11-10T22:55:45Z` | **YES** (`mtime < 00:31:20Z` start of `PID 277659`) |
| [src/paa_os/builder_and_deployer.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/builder_and_deployer.py) | `823d2910ca899013375d08716ffbc8b796f9e91f304126b2c7e6800ac34dce16` | `37,360` | `2026-11-10T21:32:46Z` | `2026-11-10T21:32:46Z` | **YES** (invoked per-timer execution) |
| [config/paa_autonomy_config.json](file:///C:/Users/Anton/source/repos/Dominus/config/paa_autonomy_config.json) | `60077a315810f1975fb4c221d557b2c859e604d71c429b3077ece5e84b680302` | `5,062` | `2026-11-10T21:32:31Z` | `2026-11-10T21:32:31Z` | **YES** (loaded dynamically by PAA jobs) |
| [polymarket_all_in_one.py](file:///C:/Users/Anton/source/repos/Dominus/polymarket_all_in_one.py) | `39d1a9d66661fe3733837a3936b05fe802646d1e58f29aa4029b17c3e2e0d8af` | `910,713` | `2026-11-10T22:46:38Z` | `2026-11-10T22:46:38Z` | `< 1 MB` bundle (`0` CRLF bytes) |
| [polymarket_alpha124_all_in_one.py](file:///C:/Users/Anton/source/repos/Dominus/polymarket_alpha124_all_in_one.py) | `709396d426417f0f8f0e94823243c9534ba782fef7afadfca202cdb0cbf3f764` | `934,928` | `2026-11-10T22:48:56Z` | `2026-11-10T22:48:56Z` | `< 1 MB` bundle (`0` CRLF bytes) |

**Locally Staged Phase 0 Remediation Files (Not Yet Deployed to `kraken-finland` per Read-Only Safety Boundary):**

| Local Remediation File | Issue | Local Patched SHA-256 (`Bytes`) | Deployment State |
| :--- | :--- | :--- | :--- |
| [src/polymarket_research/alpha_124_shadow_daemon.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/alpha_124_shadow_daemon.py) | `F-01` | `4a3aedbafc8577aac851e77094c9f6edd2db4fa1a6749c46ed23409dddd31aa9` (`841,051 B`) | Staged locally; remote untouched |
| [src/polymarket_research/polymarket_terminal_recorder.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/polymarket_terminal_recorder.py) | `F-01` | `9a97305ab20b57a425106625b6568bb1567790f8c1aaba6adb6e8b31eeac8f78` (`199,667 B`) | Staged locally; remote untouched |
| [scripts/polymarket_daily_projections.py](file:///C:/Users/Anton/source/repos/Dominus/scripts/polymarket_daily_projections.py) | `F-02` | `b53902f77fee9e8f2791405e0dbf205fa2d5afcb1b36717a2c7502d504689440` (`65,555 B`) | Staged locally; remote untouched |
| [scripts/dominus_command_center.py](file:///C:/Users/Anton/source/repos/Dominus/scripts/dominus_command_center.py) | `F-02` | `1d71d73e8a652066645054a4023d7f75172374883a70fd02ca7f79509e309349` (`238,841 B`) | Staged locally; remote untouched |
| [pytest.ini](file:///C:/Users/Anton/source/repos/Dominus/pytest.ini) | `F-06` | `92738c5419ea27d3e42348663e647485396645d733ff81a276873a9f2fc3b8cc` (`217 B`) | New local config |
| [tests/test_phase0_reliability_fixes.py](file:///C:/Users/Anton/source/repos/Dominus/tests/test_phase0_reliability_fixes.py) | `F-01`/`F-02`/`F-06` | `c346609134710fb844b862870244efce2c1ef6741546caa2f71027b94c76827e` (`18,331 B`) | New local regression suite (`10/10` pass) |

---

## 3. Resolution of the Nov 10 Review Deployment Discrepancy

### 3.1 The Apparent Contradiction in `dominus_audit_and_masterplan_review.md`
In the Nov 10 review artifact (`dominus_audit_and_masterplan_review.md`):
- **Lines 8 & 20** stated: ``polymarket-live-harvester.service` (`ActiveEnterTimestamp=Tue 2026-11-10 03:31:45 UTC`, `open_positions_count == 4` on `KMIA` Nov 7 markets) was **never restarted or interrupted** ... The live harvester will pick up the staged Python fixes automatically upon flat-book redeploy (`open_positions_count == 0`).``
- **Line 125 (Section II.5, Action `1A`)** stated: ``✅ COMPLETED (`1A`): Safe Harvester Restart Executed While Preserving Open `KMIA` Case: `polymarket-live-harvester.service` (`MainPID=253443`) was safely restarted onto the patched codebase via `paa_flat_harvester_redeploy_once.py` with **zero** shares sold/unwound across all 4 disputed `KMIA` Nov 7 positions...``

### 3.2 Direct Forensic Timeline Resolving the Discrepancy

Cross-referencing `journalctl --user`, `data/paa_os/flat_redeploy_watcher.log`, `data/backups/`, and `backups/` establishes the exact sequence of events on `2026-11-10`:

1. **`2026-11-10 03:31:45 UTC` — Pre-Review Harvester Start:**  
   `polymarket-live-harvester.service` started after `backups/polymarket_predeploy_20261110_032751.tar.gz` (`03:31:21 UTC`) and ran continuously for `18h 03m 21s` (`987.9 MiB` peak RSS).
2. **`2026-11-10 21:10:44 – 21:16:00 UTC` — Initial QA Review Sync (No Harvester Restart Yet):**  
   `data/backups/pre_boost_qa_sync.tar.gz` (`21:10:44 UTC`) and `data/backups/shadow_telemetry_pre_compact.sqlite3.gz` (`21:12:18 UTC`) were created; shadow daemons were restarted (`21:12:14 UTC` and `21:10:52 UTC`). When Part I of `dominus_audit_and_masterplan_review.md` was stamped at `21:16 UTC`, the live harvester was indeed still on its `03:31:45 UTC` process.
3. **`2026-11-10 21:32:31 – 21:32:46 UTC` — Action `2A` (PAA Proposal-Only Lock Applied):**  
   [config/paa_autonomy_config.json](file:///C:/Users/Anton/source/repos/Dominus/config/paa_autonomy_config.json#L93-L97) (`mtime 21:32:31Z`) and [`DeploymentController._is_live_promotion_blocked_by_proposal_only`](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/builder_and_deployer.py#L387-L430) (`mtime 21:32:46Z`) were deployed, setting `"proposal_only_live_promotion": true`, `"proposal_only_below_nav_usd": 5000.0`, `"allow_auto_plumbing_bugfix_deploy": false`, and `"allow_auto_risk_tightening_hot_reload": false`.
4. **`2026-11-10 21:34:56 – 21:35:06 UTC` — Action `1A` Safe Harvester Restart (`MainPID=253443`):**  
   Eighteen minutes after drafting Part I, `data/backups/live_harvester_state_pre_1a_restart.json` (`651,811 B`, `mtime 2026-11-10 21:34:56.755 UTC`) was saved, [`_is_restart_safe_frozen_uma_lock`](file:///C:/Users/Anton/source/repos/Dominus/scripts/paa_flat_harvester_redeploy_once.py#L36-L53) was updated, and `paa_flat_harvester_redeploy_once.py` restarted `polymarket-live-harvester.service` onto `MainPID=253443` at `21:35:06 UTC`. Line 125 of the review artifact was appended to record `1A` completion without updating the earlier `03:31:45 UTC` banner on Lines 8 & 20.
5. **`2026-11-10 22:45:44 – 22:55:51 UTC` — Final Post-Review Bundle Sync & Restart (`MainPID=264354`):**  
   Following final edits to [riskless_protocol_v2_expansion.py](file:///C:/Users/Anton/source/repos/Dominus/src/polymarket_research/riskless_protocol_v2_expansion.py) (`22:45:44Z`) and bundle rebuilds (`22:46:38Z` / `22:48:56Z`), `deploy_polymarket_live.py` created `backups/polymarket_predeploy_20261110_224958.tar.gz` (`22:54:11 UTC`) and restarted `polymarket-live-harvester.service` at **`22:54:37 UTC`** (`MainPID=264354`, `NRestarts=0`).

**Bottom-Line Verdict:** All Nov 10 code patches are actively loaded in memory inside `polymarket-live-harvester.service` (`PID 264354`, uninterrupted since `22:54:37 UTC`), and comparing `live_harvester_state_pre_1a_restart.json` (`21:34:56 UTC`) against current `live_harvester_state.json` proves **zero shares, cost basis, or KMIA position fields changed**.
