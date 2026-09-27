# Antigravity Workspace Invariants

## Environment Execution
- Environment: Always run Python via `/home/skybullet1987/quant_pipeline/venv/bin/python3`.
- Environment Variable: Always set `PYTHONUNBUFFERED=1`.
- Shell Safety: Never run interactive commands or pagers (e.g., use `git --no-pager log`).

## Architecture Standards
- Timeframe Hierarchy:
  - 4H (Macro): Universe selection, Causal HMM regimes, target allocations, and 5% deadband run exclusively on 4-hour boundaries (00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC).
  - 1H (Micro Risk): S2 Cash Choke ($\Delta \sigma$) and catastrophic stops run hourly at :00:15 UTC.
- Single Source of Truth: All execution scripts MUST import models from `src/models/` and `src/portfolio/` (`HMMRegimeGovernor`, `CrossSectionalAlphaRanker`, `DollarNeutralRiskParityAllocator`). Do NOT maintain inline duplicate heuristic logic.
- Execution Target: Testnet / Paper only (`IS_PAPER = True`). Do NOT execute live mainnet orders without explicit confirmation.

## Quality Gate
- Run `pytest tests/` and `python3 cli.py --help` after modifying any strategy or execution code.
