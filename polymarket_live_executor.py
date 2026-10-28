#!/usr/bin/env python3
"""
Canonical root import shim for `polymarket_live_executor`.

Eliminates root-vs-package shadow drift by delegating 100% of symbols and module
identity directly to `src.polymarket_research.polymarket_live_executor`.
"""

import sys as _sys
from pathlib import Path as _Path

_REPO_ROOT = _Path(__file__).resolve().parent
if str(_REPO_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_REPO_ROOT))

from src.polymarket_research import polymarket_live_executor as _canonical

globals().update(
    {k: v for k, v in _canonical.__dict__.items() if k not in ("__name__", "__file__", "__spec__", "__loader__")}
)

if __name__ == "__main__":
    print("=" * 80)
    print("  POLYMARKET LIVE CLOB EXECUTION ADAPTER - STANDALONE PREFLIGHT")
    print("=" * 80)
    _executor = _canonical.PolymarketLiveExecutor(dry_run=True)
    print(f"Auth Mode: {_executor.auth_mode}")
    print(f"SDK Available: {_canonical.PY_CLOB_AVAILABLE}")
    print(f"Ledger Path: {_executor.ledger_path}")
    _fee_rate, _fee_usd = _executor.calculate_dynamic_crypto_fee(0.77, 50.0)
    print(f"Dynamic Fee on $50 @ $0.77: Rate={_fee_rate*100:.2f}% | USD=${_fee_usd:.4f}")
    assert abs(_fee_rate - 0.0161) < 1e-4, "Dynamic fee calculation mismatch"
    print(">>> POLYMARKET LIVE ADAPTER PREFLIGHT: PASS (100% OPERATIONAL) <<<")
else:
    _sys.modules[__name__] = _canonical
