---
name: trade-forensics
description: Autonomous post-trade forensic auditor and self-healing workflow for Dominus Polymarket trading daemons. Activate this skill whenever auditing trade logs, investigating losing trades, checking daemon health, or running scheduled post-trade forensic checks.
---

# Autonomous Trade Forensics & Self-Healing Skill (Real-Money Live Harvester Only)

This skill governs the autonomous post-trade inspection, root-cause classification, bug fixing, and redeployment loop for the **real-money Polymarket Live Harvester on `kraken-finland`** (`/home/skybullet1987/quant_pipeline/src/polymarket_research/polymarket_live_harvester.py`).

## 1. Core Operating Rule (Real Positions & Code Bugs Only)

Every real-money settled trade in `kraken-finland:/home/skybullet1987/quant_pipeline/data/polymarket/live_harvester_state.json` follows a strict 2-branch decision tree:

1. **PROFIT (`won == True`)**:
   - Winning trades are automatically cleared as `PROFIT_OK` by `audit_losing_trades.py --check`. Do not modify code for winning trades.
2. **LOSS (`won == False`)**:
   - Inspect the trade's entry & exit telemetry on `kraken-finland` (`live_harvester_state.json`, `live_harvester.log`, `live_shock_triggers.jsonl`).
   - Classify each loss into **one of two verdicts**:
     - **`EXPECTED_LOSS` (Normal Market Variance)**:
       - Entry math, orderbook walk, fee deduction, and stop-loss/settlement worked as intended, and the underlying price simply reversed before expiry.
       - **Action**: Do NOT change strategy parameters to overfit a normal market reversal. Mark the trade audited with `--verdict EXPECTED_LOSS`.
     - **`BUG_FIXED` (Verifiable Code Bug Only)**:
       - The loss was caused by a verifiable code bug, pricing discrepancy, or execution defect in `polymarket_live_harvester.py`.
       - **Action**:
         1. Fix the bug in `/home/skybullet1987/quant_pipeline/src/polymarket_research/polymarket_live_harvester.py` on `kraken-finland` (and sync `polymarket_all_in_one.py` locally).
         2. Record the verdict using `audit_losing_trades.py --mark-audited <trade_id> --verdict BUG_FIXED --notes "<root cause & fix>"`.
         3. Redeploy the live harvester (only when `open_positions_count == 0`) using `audit_losing_trades.py --redeploy`.

---

## 2. Step-by-Step Execution Procedure

### Step 1: Run the Fast Forensic Pre-Check
Run:
```powershell
& "C:\Program Files\LibreOffice\program\python.exe" C:\Users\Anton\source\repos\Dominus\audit_losing_trades.py --check
```
- If `"status": "ALL_GOOD"` (`uninspected_losses_count == 0` and `daemon_health.healthy == true`), output a 1-line summary confirming real-money live harvester health (`open_positions_count`, `live_bankroll_usd`) and **stop immediately**.
- If `daemon_health.healthy == false`, inspect `kraken-finland` and run `--redeploy` to restore service health.

### Step 2: Diagnose Each Uninspected Real-Money Loss
For each trade in `uninspected_losses`:
1. Inspect the trade fields and corresponding `live_harvester.log` entries on `kraken-finland`.
2. Decide whether the loss is `EXPECTED_LOSS` (normal market variance — do not touch code) or `BUG_FIXED` (verifiable code bug).

### Step 3: Record Verdicts & Redeploy (Only If a Code Bug Was Fixed)
- For expected variance losses:
  ```powershell
  & "C:\Program Files\LibreOffice\program\python.exe" C:\Users\Anton\source\repos\Dominus\audit_losing_trades.py --mark-audited <TRADE_ID> --verdict EXPECTED_LOSS --notes "<concise reason>"
  ```
- If you fixed a real code bug on `kraken-finland`:
  1. Mark each affected trade:
     ```powershell
     & "C:\Program Files\LibreOffice\program\python.exe" C:\Users\Anton\source\repos\Dominus\audit_losing_trades.py --mark-audited <TRADE_ID> --verdict BUG_FIXED --notes "<what bug was fixed>"
     ```
  2. Compile-check and restart `polymarket-live-harvester.service`:
     ```powershell
     & "C:\Program Files\LibreOffice\program\python.exe" C:\Users\Anton\source\repos\Dominus\audit_losing_trades.py --redeploy
     ```
