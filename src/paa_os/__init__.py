"""
PAA Autonomous Operating System (`src/paa_os`)
==============================================
Persistent, self-operating autonomous infrastructure for Profit Above All (PAA):
  - `task_db`: SQLite WAL durable task queue, checkpoints, leases, research & deployment registries
  - `permissions`: 3-class permission model, credential isolation, and diff/config compliance gates
  - `budget`: AI token/API spend limits, compute cost accounting, rate limiters & EV prioritization
  - `agent_runtime`: Headless Antigravity CLI (`agy`) non-interactive JSON runner with ADC auth
  - `accountant`: Authoritative financial intelligence, live-vs-sim separation & discrepancy safeguards
  - `researcher`: Full-universe Polymarket scanner & experimental hypothesis validator
  - `builder_and_deployer`: Isolated Git worktree builder, automated QA & versioned release/rollback controller
  - `monitor`: Two-tier independent operations watchdog & PID-1/user supervisor
  - `director`: Persistent PAA Autonomous Director (B1-B8 decision policy & checkpoint resumption)
"""

from __future__ import annotations

__version__ = "1.0.0"
