# Staged Owner-Control Proposal Package (`v50_owner_control_package`)

**Status:** `STAGED_AWAITING_HUMAN_OWNER_APPROVAL`  
**Author:** `@policy-auditor` (DOMINUS v5.0 Governance & Continuity Slice)  
**Zero-Trust Invariant:** `src/paa_os/permissions.py`, `src/paa_os/builder_and_deployer.py`, and `config/paa_autonomy_config.json` belong to `PermissionGate.protected_files` ([permissions.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py#L140-L159)). Per Zero-Trust governance, none of those protected files were modified in the working tree (`PermissionGate().inspect_candidate_diff() == (True, [])`); instead, deterministic unified patches and an atomic apply/rollback utility are staged in this directory for explicit human owner execution.

---

## 1. Contents of This Proposal Package

| Artifact | Target Protected / Paired File(s) | Remediated Findings |
| :--- | :--- | :--- |
| [proposal_manifest.json](file:///C:/Users/Anton/source/repos/Dominus/paa_staging/proposals/v50_owner_control_package/proposal_manifest.json) | Package metadata | Records baseline & post-patch LF SHA-256 digests and required operator scopes (`CREDENTIAL_OR_PERMISSION_EXPANSION`, `LIVE_PRODUCTION_PROMOTION`). |
| [01_permissions_pol05_scope_ttl_and_binary_guard.patch](file:///C:/Users/Anton/source/repos/Dominus/paa_staging/proposals/v50_owner_control_package/01_permissions_pol05_scope_ttl_and_binary_guard.patch) | [src/paa_os/permissions.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/permissions.py) | **`POL-05` / `R-05` + `POL-08` / `R-07`:** Fixes the conjoined `ok_exp and ok_live` AND-scope bug via per-violation scope mapping (`_map_violation_to_required_scope`), enforces `expires_at_utc` TTL on wildcard `"*"` privileged scopes + one-shot `consumed_at_utc` replay protection, adds `LIVE_PRODUCTION_PROMOTION` to `explicit_scopes`, and blocks non-test `.sqlite3`/`.db`/`.jsonl`/`.parquet`/`.pkl` artifacts while keeping all non-overridable anti-tampering & credential/transfer blocks untouched. |
| [02_builder_and_deployer_pol07_uma_restart.patch](file:///C:/Users/Anton/source/repos/Dominus/paa_staging/proposals/v50_owner_control_package/02_builder_and_deployer_pol07_uma_restart.patch) | [src/paa_os/builder_and_deployer.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/builder_and_deployer.py) | **`POL-07` / `R-06`:** Replaces raw `open_cnt > 0` check (`L663-665`) with `is_harvester_state_restart_safe(st_j)` so passive post-expiry `KMIA` UMA-disputed locks (`exit_order_id=None`, `unwind_order_id=None`) do not trigger `DEFERRED_OPEN_POSITIONS(4)`, while active pre-expiry trades, `pre_split_inventory_state.active`, and non-maker pending intents remain blocked until flat. |
| [03_autonomy_config_and_budget_pol10_vm_cost.patch](file:///C:/Users/Anton/source/repos/Dominus/paa_staging/proposals/v50_owner_control_package/03_autonomy_config_and_budget_pol10_vm_cost.patch) | [config/paa_autonomy_config.json](file:///C:/Users/Anton/source/repos/Dominus/config/paa_autonomy_config.json), [src/paa_os/budget.py](file:///C:/Users/Anton/source/repos/Dominus/src/paa_os/budget.py) | **`POL-10` / `R-10`:** Updates stale `"prorated_vm_hourly_cost_usd"` from `0.0730` (`$52.56/mo`) to `0.0343` (`$24.67/mo` = `$0.8232/day` actual `quant-pipeline-finland` GCP rate), removing `+$27.89/mo` phantom accounting drag. |
| [apply_or_rollback_owner_package.py](file:///C:/Users/Anton/source/repos/Dominus/paa_staging/proposals/v50_owner_control_package/apply_or_rollback_owner_package.py) | Verification / Apply / Rollback CLI | Verifies baseline SHA-256 digests, AST compilation, and JSON validity in memory (`--verify-dry-run`), atomically backs up & applies (`--apply`), or restores backups (`--rollback`). Hard-refuses `--apply`/`--rollback` (`SystemExit(77)`) inside isolated worker subprocesses (`PAA_SIGNING_DISABLED=1` / `PAA_WORKER_ROLE`). |

---

## 2. Exact Owner Commands (Dry-Run, Apply & Rollback)

### Step 1 — Dry-Run In-Memory Verification (Zero File Writes)
```powershell
& "C:\Program Files\LibreOffice\program\python.exe" paa_staging/proposals/v50_owner_control_package/apply_or_rollback_owner_package.py --verify-dry-run
```

### Step 2 — Atomic Owner Apply (Creates Backups in `data/polymarket/paa/live_backups/v50_owner_control_package/`)
```powershell
# Local Windows workspace:
& "C:\Program Files\LibreOffice\program\python.exe" paa_staging/proposals/v50_owner_control_package/apply_or_rollback_owner_package.py --apply

# Remote host (interactive human SSH session only, after syncing repo):
ssh kraken-finland "cd /home/skybullet1987/quant_pipeline && ./venv/bin/python paa_staging/proposals/v50_owner_control_package/apply_or_rollback_owner_package.py --verify-dry-run && ./venv/bin/python paa_staging/proposals/v50_owner_control_package/apply_or_rollback_owner_package.py --apply"
```

### Step 3 — Deterministic 1-Command Rollback
```powershell
# Local Windows workspace:
& "C:\Program Files\LibreOffice\program\python.exe" paa_staging/proposals/v50_owner_control_package/apply_or_rollback_owner_package.py --rollback

# Remote host:
ssh kraken-finland "cd /home/skybullet1987/quant_pipeline && ./venv/bin/python paa_staging/proposals/v50_owner_control_package/apply_or_rollback_owner_package.py --rollback"
```
