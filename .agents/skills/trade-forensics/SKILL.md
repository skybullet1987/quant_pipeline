---
name: trade-forensics
description: Autonomous post-trade forensic auditor and self-healing workflow for Dominus Polymarket trading daemons. Activate this skill whenever auditing trade logs, investigating losing trades, checking daemon health, or running scheduled post-trade forensic checks.
---

# Autonomous Trade Forensics & Self-Healing Skill (Real-Money Live Harvester Only)

This skill governs the autonomous post-trade inspection, root-cause classification, deterministic bug fixing, and redeployment loop for the **real-money Polymarket Live Harvester on `kraken-finland`** (`/home/skybullet1987/quant_pipeline/src/polymarket_research/polymarket_live_harvester.py`).

## 1. Strict Quantitative Governance Rule (3-Verdict Wall Against N=1 Overfitting)

Every real-money settled trade in `kraken-finland:/home/skybullet1987/quant_pipeline/data/polymarket/live_harvester_state.json` follows a strict decision tree:

1. **PROFIT (`won == True`)**:
   - Winning trades are automatically cleared as `PROFIT_OK` by `audit_losing_trades.py --check`. Do not modify code for winning trades.
2. **LOSS (`won == False`)**:
   - Inspect the trade's entry & exit telemetry on `kraken-finland` (`live_harvester_state.json`, `live_harvester.log`, `live_shock_triggers.jsonl`, `live_orders.jsonl`).
   - Classify each loss into **strictly one of three verdicts**:
     - **`EXPECTED_LOSS` (Normal Market Variance — Touch ZERO Code)**:
       - Entry math, orderbook walk, fee deduction, and stop-loss/settlement worked as designed, and the underlying price simply reversed before expiry.
       - **Action**: Do NOT change code or strategy parameters. Record `--verdict EXPECTED_LOSS`.
     - **`BUG_FIXED` (Deterministic Plumbing / Execution / State-Machine Bug ONLY — `0` Free Parameters)**:
       - The loss was caused or worsened by a **verifiable deterministic software defect** with zero tunable strategy degrees of freedom (e.g., HTTP/thread race condition, stale cancel-order state snapshot, uncaught exception, API retry bug, decimal/fee calculation bug, or oracle data parsing bug).
       - **Action**:
         1. Patch the deterministic defect cleanly in `src/polymarket_research/polymarket_live_harvester.py` and/or `polymarket_live_executor.py`.
         2. Rebuild the `<1 MB` bundle via `scripts/bundle_polymarket_all_in_one.py`.
         3. Sync to `kraken-finland` and run `venv/bin/pytest tests/test_polymarket_wfo_5fixes.py tests/test_zero_trust_forensic_audit.py -q` — **100% of tests MUST pass**.
         4. Record `--verdict BUG_FIXED` and run `audit_losing_trades.py --redeploy` (which enforces `open_positions_count == 0`).
     - **`PARAM_WFO_REQUIRED` (Numerical Strategy / Alpha / Risk Threshold Hypothesis — NEVER Auto-Tweak Live!)**:
       - If preventing the loss would require changing **any numerical strategy parameter** (`dist_pct` / `min_cushion`, `sigma_1h` floor, `z_strike`, `TTE` bounds, `p_max`, price bands, Kelly sizing, or TP/ratchet/salvage thresholds):
       - **HARD PROHIBITION**: NEVER modify numerical strategy parameters in live production based on `N=1` losing trade without Purged Walk-Forward Optimization (`scripts/honest_purged_wfo_optimizer.py`: Purged Train -> 2h Embargo -> Validation -> 2h Embargo -> Sealed Holdout + `CPCV(6,2)`).
       - **Action**:
         1. Run a read-only Purged WFO / OOS check against `/home/skybullet1987/quant_pipeline/scripts/honest_purged_wfo_optimizer.py` on `kraken-finland` to measure whether a parameter adjustment improves Purged Train + Val + Sealed Holdout (`Profit Factor`, `Net PnL`, `Sharpe`, `Bootstrap 95% CI`) vs destroying winning trade volume.
         2. Do **NOT** auto-edit live thresholds unattended. Record `--verdict PARAM_WFO_REQUIRED --notes "<Purged WFO grid result & recommendation>"` so the user can review and approve (or stage in Shadow first).

---

## 2. Step-by-Step Execution Procedure

### Step 1: Run the Fast Forensic Pre-Check
Run:
```powershell
& "C:\Program Files\LibreOffice\program\python.exe" C:\Users\Anton\source\repos\Dominus\audit_losing_trades.py --check
```
- If `"status": "ALL_GOOD"` (`uninspected_losses_count == 0` and `daemon_health.healthy == true`), output a 1-line summary confirming real-money live harvester health (`open_positions_count`, `live_bankroll_usd`) and **stop immediately**.
- If `daemon_health.healthy == false` and `open_positions_count == 0`, inspect `kraken-finland` and run `--redeploy` to restore service health.

### Step 2: Diagnose Each Uninspected Real-Money Loss
For each trade in `uninspected_losses`:
1. Inspect the trade fields and corresponding `live_harvester.log` + `live_shock_triggers.jsonl` entries on `kraken-finland`.
2. Classify strictly as `EXPECTED_LOSS` (normal market variance), `BUG_FIXED` (deterministic `0`-parameter plumbing/execution bug), or `PARAM_WFO_REQUIRED` (strategy parameter hypothesis requiring Purged WFO grid search + human approval).

### Step 3: Record Verdicts & Redeploy (Only for Verified Deterministic Plumbing Bugs)
- For expected variance losses:
  ```powershell
  & "C:\Program Files\LibreOffice\program\python.exe" C:\Users\Anton\source\repos\Dominus\audit_losing_trades.py --mark-audited <TRADE_ID> --verdict EXPECTED_LOSS --notes "<concise reason>"
  ```
- For strategy threshold or execution-sequence hypotheses (automatically queued to `data/polymarket/wfo_hypothesis_queue.jsonl` without modifying live thresholds):
  ```powershell
  & "C:\Program Files\LibreOffice\program\python.exe" C:\Users\Anton\source\repos\Dominus\audit_losing_trades.py --mark-audited <TRADE_ID> --verdict PARAM_WFO_REQUIRED --classification PARAM_WFO_REQUIRED --wfo-grid "<grid spec>" --notes "<Purged WFO grid metrics & recommendation>"
  ```
- Only if you fixed and `pytest`-verified a deterministic code/execution bug (`0` free strategy parameters — `--classification PLUMBING_0_PARAM` is enforced by `audit_losing_trades.py` and blocks any `Type 2` threshold tweaks):
  1. Mark each affected trade:
     ```powershell
     & "C:\Program Files\LibreOffice\program\python.exe" C:\Users\Anton\source\repos\Dominus\audit_losing_trades.py --mark-audited <TRADE_ID> --verdict BUG_FIXED --classification PLUMBING_0_PARAM --notes "<what deterministic bug was fixed>"
     ```
  2. Compile-check and restart `polymarket-live-harvester.service` when flat (`open_positions_count == 0` is enforced automatically):
     ```powershell
     & "C:\Program Files\LibreOffice\program\python.exe" C:\Users\Anton\source\repos\Dominus\audit_losing_trades.py --redeploy
     ```
