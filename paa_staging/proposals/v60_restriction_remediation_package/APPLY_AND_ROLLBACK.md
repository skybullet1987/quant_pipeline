# DOMINUS v6.0 — Staged Protected-File Remediation Package (`R-05`, `R-10`, `R-13`, `R-42`)

**Governance Invariant (`D-002`, `D-003`):** The four target files below are locked in `config/paa_autonomy_config.json` (`protected_files`). Per Zero-Trust policy, autonomous agents MUST NOT modify `protected_files` directly in the working tree; all changes are staged here for explicit human-owner review and execution.

---

## 1. Staged Remediations Included

### Patch A — `R-05`: One-Shot Approval Consumption Writeback (`src/paa_os/permissions.py` & `src/paa_os/builder_and_deployer.py`)
- **Defect Identified in v6.0 Audit:** `PermissionGate._validate_approval_record` (`src/paa_os/permissions.py:155-158`) checks `consumed_at_utc` and `consumed_by_release_id`, **but `DeploymentController` (`src/paa_os/builder_and_deployer.py`) never writes those fields back** when promoting a release. Thus an unrevoked `24h`-TTL approval JSON could be replayed across multiple releases within its TTL window.
- **Remediation:**
  1. Add `PermissionGate.consume_owner_approval(scope: str, release_id: str)` in `src/paa_os/permissions.py` (restricted strictly to interactive human-owner / `DeploymentController.promote_approved_release` context where `PAA_SIGNING_DISABLED != "1"`).
  2. Invoke `self.permissions.consume_owner_approval("LIVE_PROMOTION_GATE", release_id)` atomically immediately upon live promotion in `src/paa_os/builder_and_deployer.py` (or manually via the new `python scripts/paa_cli.py approvals consume --scope LIVE_PROMOTION_GATE --release-id <REL_ID>` command already shipped in `scripts/paa_cli.py`).

### Patch B — `R-10`: Time-Horizon Alignment in `PAAAccountant` (`src/paa_os/accountant.py:541-544`)
- **Defect Identified in v6.0 Audit:** `src/paa_os/accountant.py:541-544` computes:
  ```python
  realized_pnl = float(ledger.get("verified_realized_net_profit_usd") or 0.0)
  ai_cost = float(budget_m.get("all_time_ai_cost_usd") or 0.0)
  infra_today = float(budget_m.get("daily_infra_vm_cost_usd") or 0.0)
  net_econ = round(realized_pnl - ai_cost - infra_today, 4)
  ```
  This subtracts **intraday `0..24h` UTC VM cost** (`$0.00..$0.8223`, resetting to `$0.00` every midnight UTC) from **all-time cumulative realized P&L**, creating artificial `+$0.82` jumps at `00:00 UTC` while omitting prior days' sunk VM burn.
- **Remediation:** Delegate economic reconciliation to `src.polymarket_research.v6_restriction_and_capital_allocator.reconcile_infrastructure_expenses()`, reporting two strictly separated metrics:
  - `true_marginal_trading_profit_usd` (net of trading fees & gas, `$0.00` marginal `agy` subscription cost — used for per-trade marginal capital allocation).
  - `full_cost_net_economic_profit_usd` (aligning cumulative elapsed campaign hours * `$0.034264/hr` against cumulative realized P&L, plus rolling `24h` P&L against `$0.8223/day` VM cost).

### Patch C — `R-13` & `R-42`: Swapless Cgroup Prose Parity & 5-Pillar Evidence Readiness (`src/polymarket_research/cross_venue_unblock_and_certification.py`)
- **Defects Identified in v6.0 Audit:**
  1. Lines `1523, 1529` still print `MemoryMax=320M` in operator setup guidance whereas deployed `systemd` cgroup limits enforce `MemoryMax=512M` / `MemoryHigh=400M` (`MemorySwapMax=0B`).
  2. Certification reports rely on wall-clock `certified_live_hours >= 168.0` even if `matched_opportunities == 0` (`ForecastEx` had `600` hydrated books and `0` matched arbs), or conversely block a venue that has already accumulated `>= 2,000` uncontaminated L2 snapshots, `>= 3` liquidity regimes, `>= 25` post-delay simulated executions, and full settlement verification in `48h-96h`.
- **Remediation:** Update strings `320M` -> `512M (MemoryHigh=400M, MemorySwapMax=0B)` and attach `evaluate_evidence_based_venue_readiness()` from `v6_restriction_and_capital_allocator.py` to every venue record in `certification_report.json` (`proposal_only_live_promotion` remains strictly active).

---

## 2. Human-Owner Verification & Rollback Commands

1. **Dry-run Zero-Trust verification (safe anytime):**
   ```powershell
   & "C:\Program Files\LibreOffice\program\python.exe" -m unittest tests/test_v60_restriction_reassessment_and_allocator.py -v
   ```
2. **Manage one-shot approvals & consumption today via non-protected `paa_cli.py`:**
   ```bash
   python scripts/paa_cli.py approvals list
   python scripts/paa_cli.py approvals grant --scope LIVE_PROMOTION_GATE --ttl-hours 12 --release-id REL_V60_01 --reason "Owner reviewed v6.0 package"
   python scripts/paa_cli.py approvals consume --scope LIVE_PROMOTION_GATE --release-id REL_V60_01
   python scripts/paa_cli.py approvals revoke --scope LIVE_PROMOTION_GATE --reason "Manual revocation"
   ```
3. **Rollback:** Restore pre-apply backup from `data/polymarket/paa/owner_package_backups/` or `git checkout -- <protected_file>`.
