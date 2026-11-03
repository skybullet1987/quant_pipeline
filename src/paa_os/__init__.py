"""
PAA Autonomous Operating System (`src/paa_os`)
==============================================
Persistent, zero-trust, self-operating autonomous infrastructure for Profit Above All (PAA):
  - `task_db`: SQLite WAL durable task transactions, Tier-B `verified_facts` (with TTL), `session_runs`, & registries
  - `zero_trust`: Stateless context packets (60% cap), `<UNTRUSTED_DATA_ONLY>` sanitizer & 5-Gate `DeterministicVerificationController`
  - `permissions`: 3-class permission model, Tier-A policy immutability, credential isolation & diff/config compliance gates
  - `budget`: AI token/API spend limits, compute cost accounting, rate limiters & EV prioritization
  - `agent_runtime`: Stateless headless Antigravity CLI (`agy`) JSON runner with ADC auth & context-budget tracking
  - `accountant`: Authoritative financial intelligence, live-vs-sim separation & discrepancy safeguards
  - `researcher`: Full-universe Polymarket scanner with 5-stage Tier-C evidence ladder (`HYPOTHESIS`..`LIVE_VERIFIED`)
  - `builder_and_deployer`: Isolated Git worktree builder, automated QA & versioned release/rollback controller
  - `monitor`: Two-tier independent operations watchdog & PID-1/user supervisor
  - `director`: Persistent PAA Autonomous Director (B1-B8 decision policy & Zero-Trust verification orchestration)
"""

from __future__ import annotations

__version__ = "2.0.0"
