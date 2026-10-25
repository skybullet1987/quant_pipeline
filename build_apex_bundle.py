#!/usr/bin/env python3
"""Builds apex_all_in_one.py (<1 MB bundle) for Deep Research."""
from pathlib import Path

ROOT = Path("/home/skybullet1987/quant_pipeline")
FILES = [
    "src/execution/production_apex_daemon.py",
    "src/execution/exchange_gateway.py",
    "src/execution/as_quoting.py",
    "src/strategy/convex_10x_engine.py",
    "src/alpha/fracdiff_orthogonal_engine.py",
    "src/signals/asym_fip.py",
    "scripts/run_unified_full_stack_ablation.py",
    "backtest_10x_convex_compounding.py",
    "data/full_stack_ablation_results.json",
    "tests/test_apex_v382_review_fixes.py",
]

out = ROOT / "apex_all_in_one.py"
with out.open("w", encoding="utf-8") as w:
    w.write("# ==============================================================================\n")
    w.write("# HYPERLIQUID APEX UNIFIED CODEBASE BUNDLE (v3.8.2-unified-mainnet-paper)\n")
    w.write("# Contains: Production Daemon, Gateway, AS Quoting, Convex 10x Engine,\n")
    w.write("#           FracDiff + Multi-Beta Residual Momentum, Asymmetric FIP,\n")
    w.write("#           Full-Stack Ablation Runner, Canonical Backtester, & Ablation Results\n")
    w.write("# ==============================================================================\n\n")
    for rel in FILES:
        p = ROOT / rel
        if p.exists():
            txt = p.read_text(encoding="utf-8")
            w.write(f"\n# ==================== FILE: {rel} ({len(txt.encode('utf-8'))} bytes) ====================\n")
            w.write(txt)
            w.write("\n")

print(f"Created {out} ({out.stat().st_size:,} bytes)")
