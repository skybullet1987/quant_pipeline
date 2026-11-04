# RISKLESS PAA PERMANENT OPERATING MEMORY — MISSION POLICY (`PAA_MISSION.md`)
**Authority Level**: Immutable Tier-A Policy (Protected by `PermissionGate` — AI Workers Cannot Modify)

1. **Core Objective (`RISKLESS_PAA`)**: Maximize sustainable, independently verified **100% riskless** net economic profit (`Verified On-Chain Zero-Loss Cash PnL - Exchange Fees - Slippage - Research AI Spend - Prorated Infrastructure Cost`) and capital velocity (`bps/hr`) across eligible Polymarket categories (`BOND1`/`BOND2` UMA Carry, `MKR_LOCK1` Post-Clinch Sweeper, `MKR_REWARD_LOCKED_CARRY`, `NR0`/`NR2`/`C1` Complete-Set & Convert Arbs, `D1`/`CAL1`/`COND1`/`CM_B3` Dominance Boxes, and Machine-Gun Riskless). Unhedged directional live bets are strictly prohibited while `riskless_only_mode=true`.
2. **Foundational Principle**: **Never trust the AI agent's memory, conclusions, or claims of completion without independent verification.**
3. **Separation of Intelligence and Memory**:
   - The persistent SQLite WAL database (`paa_tasks.db`), authoritative on-chain/state ledgers, and Git history are the **only** System of Record.
   - Short-lived stateless AI workers reason over bounded context packets and propose evidence or isolated Git branch changes.
   - Only the deterministic non-AI `DeterministicVerificationController` owns verification verdicts (`VERIFIED_COMPLETE`), permission enforcement, and release promotion.
4. **Production Continuity**: Live execution and risk management (`polymarket-live-harvester.service`) remain 100% independent of AI research, coding, or verification sessions.
