# PAA PERMANENT OPERATING MEMORY — MISSION POLICY (`PAA_MISSION.md`)
**Authority Level**: Immutable Tier-A Policy (Protected by `PermissionGate` — AI Workers Cannot Modify)

1. **Core Objective**: Maximize sustainable, independently verified net economic profit (`Verified On-Chain Realized Cash PnL - Exchange Fees - Slippage - Research AI Spend - Prorated Infrastructure Cost`) across eligible Polymarket categories.
2. **Foundational Principle**: **Never trust the AI agent's memory, conclusions, or claims of completion without independent verification.**
3. **Separation of Intelligence and Memory**:
   - The persistent SQLite WAL database (`paa_tasks.db`), authoritative on-chain/state ledgers, and Git history are the **only** System of Record.
   - Short-lived stateless AI workers reason over bounded context packets and propose evidence or isolated Git branch changes.
   - Only the deterministic non-AI `DeterministicVerificationController` owns verification verdicts (`VERIFIED_COMPLETE`), permission enforcement, and release promotion.
4. **Production Continuity**: Live execution and risk management (`polymarket-live-harvester.service`) remain 100% independent of AI research, coding, or verification sessions.
