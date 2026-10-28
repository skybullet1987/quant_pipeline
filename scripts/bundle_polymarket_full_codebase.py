#!/usr/bin/env python3
"""
bundle_polymarket_full_codebase.py
==================================
Generates the complete, UN-TRUNCATED (full docstrings, mathematical formulas, comments,
systemd units, risk config, live v3.9.3 stack, Alpha-124 11-sleeve ecosystem, WFO/backtesters,
live daily projections engine, and unit test suites) Polymarket codebase review bundles:

  1. `polymarket_full_codebase_v4.py` & `polymarket_full_codebase_v4.txt`
     -> Complete 100% un-stripped single-file master codebase (~1.9 MB) with exact 1-based TOC.
  2. `polymarket_alpha124_all_in_one.py` & `polymarket_alpha124_all_in_one.txt`
     -> Strictly < 1,000,000 bytes (~420 KB) companion bundle of the Alpha-124 11-Sleeve
        Expansion + Live Projections + Tests (pairs with `polymarket_all_in_one.txt` < 1 MB
        for any LLM tool with a 1 MB per-file upload limit).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

PIPELINE_ROOT = Path(__file__).resolve().parent.parent

FULL_OUTPUT_PY = PIPELINE_ROOT / "polymarket_full_codebase_v4.py"
FULL_OUTPUT_TXT = PIPELINE_ROOT / "polymarket_full_codebase_v4.txt"

ALPHA124_OUTPUT_PY = PIPELINE_ROOT / "polymarket_alpha124_all_in_one.py"
ALPHA124_OUTPUT_TXT = PIPELINE_ROOT / "polymarket_alpha124_all_in_one.txt"

CORE_V393_MODULES: List[Tuple[str, str]] = [
    # 1. CENTRALIZED RISK CONFIG & ALL 8 PRODUCTION/SHADOW SYSTEMD UNITS
    ("config/polymarket_risk_config.json", "Centralized Risk & Sizing Limits ($12 min, 15% dynamic, $110 slot-2 gate)"),
    ("systemd/polymarket-live-harvester.service", "Live Harvester v3.9.3 systemd Unit"),
    ("systemd/polymarket-alpha124-shadow.service", "Alpha-124 11-Sleeve Unified Shadow Daemon systemd Unit"),
    ("systemd/polymarket-recorder.service", "BTC Dual-Feed / Chainlink-TWAP Terminal Recorder systemd Unit"),
    ("systemd/polymarket-recorder-eth.service", "ETH Dual-Feed / Chainlink-TWAP Terminal Recorder systemd Unit"),
    ("systemd/polymarket-recorder-sol.service", "SOL Dual-Feed / Chainlink-TWAP Terminal Recorder systemd Unit"),
    ("systemd/polymarket-recorder-xrp.service", "XRP Dual-Feed / Chainlink-TWAP Terminal Recorder systemd Unit"),
    ("systemd/polymarket-trader.service", "Forward Paper Trader systemd Unit"),
    ("systemd/polymarket-exp316-shadow.service", "EXP-316 Macro Strike Convergence Shadow systemd Unit"),

    # 2. CORE v3.9.3 LIVE EXECUTION, HARVESTING & STREAMING STACK
    ("src/polymarket_research/polymarket_live_harvester.py", "v3.9.3 Live Harvester: Authoritative 14-digit Chainlink Open, <$110 Guard, Phase-4 Book Walk, 95c/98c TP"),
    ("src/polymarket_research/polymarket_live_executor.py", "CLOB L2 + R01 Multi-Wallet (EOA/PolyProxy/GnosisSafe/DepositWallet sig_type=3) + NegRiskAdapter Redeemer"),
    ("src/polymarket_research/polymarket_ws_streams.py", "Sub-ms CLOB Market & Authenticated User L2 WebSocket Trackers (Monotonic Order & Maker-Leg Fill Cache)"),
    ("src/polymarket_research/latency_trace.py", "Zero-Allocation Hot-Path Microsecond Latency Tracer & Stage Breakdown Telemetry"),
    ("src/polymarket_research/polymarket_terminal_recorder.py", "Sub-ms Binance/Coinbase/Chainlink-TWAP Shock & Authoritative openPrice SHM Recorder"),
    ("src/polymarket_research/deribit_svi_surface.py", "Deribit SVI Options Volatility Surface & Breeden-Litzenberger Density Engine"),
    ("src/polymarket_research/polymarket_paper_trader.py", "Forward Paper Trader & Production-Parity Simulation Engine"),

    # 3. ON-CHAIN COLLATERAL, ALLOWANCES & ACCOUNT TOOLS
    ("src/polymarket_research/check_polymarket_balance.py", "Polygon pUSD + USDC.e Collateral Balance Checker"),
    ("src/polymarket_research/verify_onchain_allowances.py", "ERC-20/ERC-1155 Proxy & Exchange Allowance Verifier"),
    ("src/polymarket_research/redeem_settled_positions.py", "CTF Settled Position Redemption CLI"),
    ("src/polymarket_research/setup_polymarket_account.py", "CLOB L2 API Key & Proxy Credential Generator"),

    # 4. AUTONOMOUS POST-TRADE FORENSICS & PURGED WALK-FORWARD OPTIMIZER
    ("audit_losing_trades.py", "Autonomous Post-Trade Forensic Auditor & Daemon Health Verifier"),
    ("scripts/honest_purged_wfo_optimizer.py", "Zero-Lookahead Purged WFO & Genuine Refit CPCV(6,2) Optimizer"),
]

ALPHA124_EXPANSION_MODULES: List[Tuple[str, str]] = [
    # 5. ALPHA-124 14-SLEEVE MATHEMATICAL ORACLES, v4.0 NET-ALPHA ENGINE & UNIFIED SHADOW DAEMON
    ("src/polymarket_research/orderflow_wfo_simulators.py", "v4.0 100ms Micro-Clip 4-Step Cascade Replay, D1 Latency-Skew WFO & Legging-Drag Parity Engine"),
    ("src/polymarket_research/net_alpha_opportunity_engine.py", "v4.0 Quote-Survival, Adaptive Maker/Taker Router, C1 Complete-Set & Capital-Efficiency Auction Engine"),
    ("src/polymarket_research/weather_metar_engine.py", "Option #1: 68-City Aviation METAR/SPECI + TAF Prior + 10s Sync Poll + W3 Weather Slate Arb"),
    ("src/polymarket_research/barrier_onetouch_svi_engine.py", "Option #2: Reflection-Principle Jump-SVI First-Passage One-Touch Barrier Pricer (Finalized 1m Wick Rule)"),
    ("src/polymarket_research/multistrike_svi_scalper.py", "Option #4: Deribit SVI Digital Pricer + Multi-Strike Ladder Monotonicity Box Scanner"),
    ("src/polymarket_research/same_oracle_dominance_box.py", "Option #7 (D1): Same-Oracle 15m vs 5m Chainlink 60s-TWAP Structural Dominance Box Engine"),
    ("src/polymarket_research/exact_twap_lock_engine.py", "Option #8 (S2): Final-45s 5m/15m Chainlink 60s-TWAP Kemna-Vorst Asian Variance + Student-t(df=5) Integral Lock"),
    ("src/polymarket_research/tradfi_sports_zero_fee_engine.py", "Zero-Fee Pyth Commodities/Metals/Equities (CM_B3/B2/U1), B4 Wick Lock, NBA Polish-Middle (SP1) & NegRisk (NR0)"),
    ("src/polymarket_research/macro_counting_ctf_engine.py", "Phase-2 Multi-Vertical Structural & Oracle Engine (TW1 xtracker, FED1 125-State LP, COND1 Oil-Senate, CTF Overround, AAA Gas, D2 12PM)"),
    ("src/polymarket_research/alpha_124_shadow_daemon.py", "Unified Multi-Vertical Shadow Daemon (Crypto, Weather METAR/HKO, Pyth Commodities/Metals/Equities, NBA, FOMC/Oil-Senate/Counting/AAA)"),
    # EXP-316 (isolated separate service) is bundled only in the full codebase (see EXP316_MODULES) to keep
    # the Alpha-124 companion bundle strictly < 1,000,000 bytes.

    # 6. BACKTESTING, LIVE DAY-BY-DAY PROJECTIONS & TELEMETRY SCORECARDS
    ("scripts/backtest_alpha_124.py", "Zero-Lookahead Walk-Forward Calibration & Empirical Backtester for Alpha-124"),
    ("scripts/polymarket_daily_projections.py", "Live-Anchored Day-by-Day (D1..D30) Compounding & Sleeve Graduation Tracker"),
    ("scripts/alpha124_status.py", "Live Alpha-124 11-Sleeve Scorecard & Orderbook Opportunity Inspector"),
    ("scripts/polymarket_scorecard_snapshot.py", "Unified 8-Service Health, Live Equity & Shadow Graduation Snapshot"),

    # 7. ALPHA-124 & MULTI-VERTICAL ORACLE UNIT TEST SUITE
    ("tests/test_alpha_124_oracles.py", "Unit Tests: Weather METAR/HKO, Jump-SVI Barrier, Pyth Session/Boxes, NBA Boxes, D1, S2 & Wallet"),
]

EXP316_MODULES: List[Tuple[str, str]] = [
    ("src/polymarket_research/exp316_macro_strike_shadow.py", "EXP-316 Isolated Multi-Strike Convergence Shadow Engine"),
]

HARVESTER_TEST_MODULES: List[Tuple[str, str]] = [
    ("tests/test_polymarket_wfo_5fixes.py", "Unit Tests: WFO 5-Fixes, 95c/98c Two-Tranche Supervisor, Phase-3A/Phase-4 Book Walk & Graduation"),
    ("tests/test_zero_trust_forensic_audit.py", "Unit Tests: Zero-Trust Forensics, Centralized Risk Config, Deterministic Replay & <1MB Bundle Sync"),
]

_FUTURE_RE = re.compile(r"^(from\s+__future__\s+import\s+[^\n]+)$", flags=re.MULTILINE)


def format_unstripped_module(rel_path: str, code: str) -> str:
    """Preserves 100% of docstrings, formulas, and comments while keeping valid Python syntax."""
    if not rel_path.endswith(".py"):
        var_name = re.sub(r"[^0-9A-Za-z]", "_", Path(rel_path).name).upper()
        safe_code = code.replace("'''", "''' + \"'''\" + r'''")
        return f"# Non-Python configuration / systemd unit embedded verbatim:\n{var_name} = r'''\n{safe_code}\n'''\n\n"
    clean_code = _FUTURE_RE.sub(r"# \1  # (Lifted to top of consolidated bundle)", code)
    if not clean_code.endswith("\n"):
        clean_code += "\n"
    return clean_code + "\n"


def assemble_bundle(
    title: str,
    subtitle: str,
    modules: List[Tuple[str, str]],
) -> Tuple[str, List[str]]:
    module_data: List[Tuple[str, str, str]] = []
    for rel_path, desc in modules:
        full_p = PIPELINE_ROOT / rel_path
        if not full_p.exists():
            raise FileNotFoundError(f"Missing required module for bundle: {full_p}")
        raw = full_p.read_text(encoding="utf-8", errors="replace")
        module_data.append((rel_path, desc, raw))

    def _pass(toc_lines: List[str]) -> Tuple[str, List[str]]:
        hdr = (
            '"""\n'
            f"{'=' * 88}\n"
            f"{title}\n"
            f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            f"{subtitle}\n"
            f"Repository: {PIPELINE_ROOT.as_posix()}\n"
            f"{'=' * 88}\n\n"
            "TABLE OF CONTENTS (Exact 1-Based Line Ranges & Raw Module Sizes):\n"
        )
        chunks = [hdr]
        for t_ln in toc_lines:
            chunks.append(t_ln + "\n")
        chunks.append('"""\n\nfrom __future__ import annotations\n\n')

        cur_line = sum(c.count("\n") for c in chunks)
        out_toc: List[str] = []
        for idx, (rel_p, desc, code) in enumerate(module_data, 1):
            banner = (
                f"# {'=' * 86}\n"
                f"# [{idx:02d}/{len(module_data):02d}] MODULE: {rel_p}\n"
                f"# PURPOSE: {desc}\n"
                f"# {'=' * 86}\n\n"
            )
            body = format_unstripped_module(rel_p, code)
            start_ln = cur_line + 1
            end_ln = cur_line + banner.count("\n") + body.count("\n")
            raw_bytes = len(code.encode("utf-8"))
            out_toc.append(
                f"  [{idx:02d}] {rel_p} (Lines {start_ln:,} - {end_ln:,} | {raw_bytes:,} B) :: {desc}"
            )
            chunks.append(banner)
            chunks.append(body)
            cur_line = end_ln
        return "".join(chunks), out_toc

    placeholder = [f"  [{i:02d}] {r} :: {d}" for i, (r, d, _) in enumerate(module_data, 1)]
    _, toc1 = _pass(placeholder)
    final_text, toc2 = _pass(toc1)
    assert toc1 == toc2, "TOC line numbers shifted between passes!"
    return final_text, toc2


def main() -> None:
    all_modules = CORE_V393_MODULES + ALPHA124_EXPANSION_MODULES + EXP316_MODULES + HARVESTER_TEST_MODULES
    full_text, full_toc = assemble_bundle(
        title="DOMINUS POLYMARKET COMPLETE UNIFIED CODEBASE (v4.0 FULL LIVE + ALPHA-124 11-SLEEVE EDITION)",
        subtitle="100% Un-Truncated Source Code, Mathematical Oracles, Execution Stack, Systemd Units & Unit Tests",
        modules=all_modules,
    )
    compile(full_text, "polymarket_full_codebase_v4.py", "exec")
    FULL_OUTPUT_PY.write_text(full_text, encoding="utf-8", newline="\n")
    FULL_OUTPUT_TXT.write_text(full_text, encoding="utf-8", newline="\n")

    a124_text, a124_toc = assemble_bundle(
        title="DOMINUS POLYMARKET ALPHA-124 11-SLEEVE EXPANSION + PROJECTIONS + TESTS (<1 MB COMPANION BUNDLE)",
        subtitle="Pairs with polymarket_all_in_one.txt (<1 MB) for tools enforcing a 1 MB per-file upload cap",
        modules=[("systemd/polymarket-alpha124-shadow.service", "Alpha-124 Unified Shadow systemd Unit")] + ALPHA124_EXPANSION_MODULES,
    )
    compile(a124_text, "polymarket_alpha124_all_in_one.py", "exec")
    a124_bytes = len(a124_text.encode("utf-8"))
    assert a124_bytes < 1_000_000, f"Alpha-124 bundle {a124_bytes:,} B exceeds 1 MB!"
    ALPHA124_OUTPUT_PY.write_text(a124_text, encoding="utf-8", newline="\n")
    ALPHA124_OUTPUT_TXT.write_text(a124_text, encoding="utf-8", newline="\n")

    full_bytes = FULL_OUTPUT_PY.stat().st_size
    print(f"SUCCESS [1/2]: {FULL_OUTPUT_PY.name} & {FULL_OUTPUT_TXT.name}")
    print(f"  - Modules: {len(all_modules)} | Lines: {len(full_text.splitlines()):,} | Size: {full_bytes:,} B ({full_bytes / 1_000_000:.3f} MB)")
    print(f"SUCCESS [2/2]: {ALPHA124_OUTPUT_PY.name} & {ALPHA124_OUTPUT_TXT.name}")
    print(f"  - Modules: {len(a124_toc)} | Lines: {len(a124_text.splitlines()):,} | Size: {a124_bytes:,} B ({a124_bytes / 1_000_000:.3f} MB)")


if __name__ == "__main__":
    main()
