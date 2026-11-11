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
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

PIPELINE_ROOT = Path(__file__).resolve().parent.parent
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))
from scripts.bundle_polymarket_all_in_one import transform_module

FULL_OUTPUT_PY = PIPELINE_ROOT / "polymarket_full_codebase_v4.py"
FULL_OUTPUT_TXT = PIPELINE_ROOT / "polymarket_full_codebase_v4.txt"

ALPHA124_OUTPUT_PY = PIPELINE_ROOT / "polymarket_alpha124_all_in_one.py"
ALPHA124_OUTPUT_TXT = PIPELINE_ROOT / "polymarket_alpha124_all_in_one.txt"

CORE_V393_MODULES: List[Tuple[str, str]] = [
    # 1. CENTRALIZED RISK & GOVERNANCE CONFIGS + ALL PRODUCTION/SHADOW SYSTEMD UNITS
    ("config/polymarket_risk_config.json", "Centralized Risk & Sizing Limits ($12 min, 15% dynamic, $110 slot-2 gate)"),
    ("config/polymarket_strategy_and_risk.json", "v5.3 Unified Hot-Reloadable Strategy, Routing & Dual-Budget Governance Config"),
    ("systemd/polymarket-live-harvester.service", "Live Harvester v5.3 systemd Unit"),
    ("systemd/polymarket-alpha124-shadow.service", "Alpha-124 Multi-Sleeve Unified Shadow Daemon systemd Unit"),
    ("systemd/polymarket-recorder.service", "Consolidated uvloop BTC+ETH+SOL+XAU Terminal Recorder systemd Unit"),
    ("systemd/polymarket-recorder-eth.service", "ETH Dual-Feed / Chainlink-TWAP Terminal Recorder systemd Unit"),
    ("systemd/polymarket-recorder-sol.service", "SOL Dual-Feed / Chainlink-TWAP Terminal Recorder systemd Unit"),
    ("systemd/polymarket-recorder-xrp.service", "XRP Dual-Feed / Chainlink-TWAP Terminal Recorder systemd Unit"),
    ("systemd/polymarket-trader.service", "Forward Paper Trader systemd Unit"),
    ("systemd/polymarket-exp316-shadow.service", "EXP-316 Macro Strike Convergence Shadow systemd Unit"),

    # 2. CORE v5.3 LIVE GOVERNANCE, EXECUTION, HARVESTING & STREAMING STACK
    ("src/polymarket_research/holistic_strategy_governance.py", "v5.3 HotReloadConfigManager, ev_terminal_twap_t5 Exit Supervisor & Velocity/Kelly Engine"),
    ("src/polymarket_research/polymarket_live_harvester.py", "v5.3 Live Harvester: Authoritative Chainlink Open, Dual-Budget Risk, Phase-4 Book Walk, Unified Exit Supervisor"),
    ("src/polymarket_research/polymarket_live_executor.py", "CLOB L2 + R01 Multi-Wallet (EOA/PolyProxy/GnosisSafe/DepositWallet sig_type=3) + NegRiskAdapter Redeemer"),
    ("src/polymarket_research/riskless_machine_gun_engine.py", "v5.5.0 Riskless Machine-Gun Engine (Relayer V2 Batch Merge, Verified m=1 Convert, Multi-Leg & Overround)"),
    ("src/polymarket_research/riskless_protocol_v2_expansion.py", "v5.5.0 Protocol V2 & Zero-Loss Frontier Expansion (NR_M1 Dead-Seed, RT_MONO1 Scalar Ladders, Velocity Scorer)"),
    ("src/polymarket_research/polymarket_ws_streams.py", "Sub-ms CLOB Market, Perps Lead-Lag & Authenticated User L2 WebSocket Trackers"),
    ("src/polymarket_research/polymarket_direct_feeds.py", "Official NBA/NHL/MLB Direct LiveData Push Adapters & Dual-Source Reconcilers"),
    ("src/polymarket_research/latency_trace.py", "Zero-Allocation Hot-Path Microsecond Latency Tracer & Stage Breakdown Telemetry"),
    ("src/polymarket_research/economic_attribution_ledger.py", "Stage B Opportunity Funnel, Sub-ms Competitor Decay Curve & Reconciled Attribution Engine"),
    ("src/polymarket_research/stage_c_zero_loss_velocity.py", "Stage C Pure-Riskless Velocity Recycler, Pre-Split Quarantine & Clinched Dead-Leg Split-to-Sell"),
    ("src/polymarket_research/synthetic_maker_quoter.py", "Stage D v5.9.0 Continuous #1 FIFO Synthetic Maker Quoter, Sub-50ms WS Shield & $0.50 Unwind Breaker"),
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
    ("src/polymarket_research/directional_wfo_shadow_sleeves.py", "v3.9.5 WFO Graduation Shadow Sleeves (SLEEVE_HYBRID_ZSPLIT_SHADOW & SLEEVE_BTC_5M_SNIPER_SHADOW)"),
    ("src/polymarket_research/orderflow_wfo_simulators.py", "v4.0 100ms Micro-Clip 4-Step Cascade Replay, D1 Latency-Skew WFO & Legging-Drag Parity Engine"),
    ("src/polymarket_research/net_alpha_opportunity_engine.py", "v4.0 Quote-Survival, Adaptive Maker/Taker Router, C1 Complete-Set & Capital-Efficiency Auction Engine"),
    ("src/polymarket_research/weather_metar_engine.py", "Option #1: 68-City Aviation METAR/SPECI + TAF Prior + 10s Sync Poll + W3 Weather Slate Arb"),
    ("src/polymarket_research/barrier_onetouch_svi_engine.py", "Option #2: Reflection-Principle Jump-SVI First-Passage One-Touch Barrier Pricer (Finalized 1m Wick Rule)"),
    ("src/polymarket_research/multistrike_svi_scalper.py", "Option #4: Deribit SVI Digital Pricer + Multi-Strike Ladder Monotonicity Box Scanner"),
    ("src/polymarket_research/same_oracle_dominance_box.py", "Option #7 (D1): Same-Oracle 15m vs 5m Chainlink 60s-TWAP Structural Dominance Box Engine"),
    ("src/polymarket_research/exact_twap_lock_engine.py", "Option #8 (S2): Final-45s 5m/15m Chainlink 60s-TWAP Kemna-Vorst Asian Variance + Student-t(df=5) Integral Lock"),
    ("src/polymarket_research/tradfi_sports_zero_fee_engine.py", "Zero-Fee Pyth Commodities/Metals/Equities (CM_B3/B2/U1), B4 Wick Lock, NBA Polish-Middle (SP1) & NegRisk (NR0)"),
    ("src/polymarket_research/macro_counting_ctf_engine.py", "Phase-2 Multi-Vertical Structural & Oracle Engine (TW1 xtracker, FED1 125-State LP, COND1 Oil-Senate, CTF Overround, AAA Gas, D2 12PM)"),
    ("src/polymarket_research/uma_nba_endgame_engine.py", "Evergreen On-Chain UMA Resolution Bond Harvester (BOND1) & 0%-Fee Live NBA Final-2m/Post-Buzzer Sniper (SP2)"),
    ("src/polymarket_research/riskless_frontier_v2_engine.py", "Riskless Frontier v2 Engine (NR2 Subset Convert + Free Tail, SP4 NBA Props, BOND2 Whitelisted MOOv2, SOC1 3-Way Soccer, LP1 Implication Matrix, API1 BO3 Esports)"),
    ("src/polymarket_research/riskless_frontier_v3_engine.py", "Riskless Frontier v3 Engine (NFL Exact Margin/Spread, Subperiod Clinch, Deadline Ladder, Tennis Retirement-Safe Corridor, Multi-Sport Post-Review Clinch)"),
    ("src/polymarket_research/riskless_frontier_v4_engine.py", "Riskless Frontier v4 Evergreen Engine (AFF1 Subperiod Collapse, SOC2 83-State Lattice, NFL_PRP1 Locks, SUM1 Frechet Triangles, CRY_INC1 Binance Inclusion, MKR_LOCK1)"),
    ("src/polymarket_research/alpha_124_shadow_daemon.py", "Unified Multi-Vertical Shadow Daemon (Crypto, Weather METAR/HKO, Pyth Commodities/Metals/Equities, Sports, UMA Bonds, Frontier v2/v3/v4)"),
    # EXP-316 (isolated separate service) is bundled only in the full codebase (see EXP316_MODULES) to keep
    # the Alpha-124 companion bundle strictly < 1,000,000 bytes.

    # 6. BACKTESTING, LIVE DAY-BY-DAY PROJECTIONS & TELEMETRY SCORECARDS
    ("scripts/backtest_alpha_124.py", "Zero-Lookahead Walk-Forward Calibration & Empirical Backtester for Alpha-124"),
    ("scripts/polymarket_daily_projections.py", "Live-Anchored Day-by-Day (D1..D30) Compounding & Sleeve Graduation Tracker"),
    ("scripts/alpha124_status.py", "Live Alpha-124 Multi-Sleeve Scorecard & Orderbook Opportunity Inspector"),
    ("scripts/polymarket_scorecard_snapshot.py", "Unified 8-Service Health, Live Equity & Shadow Graduation Snapshot"),
]

EXP316_MODULES: List[Tuple[str, str]] = [
    ("src/polymarket_research/exp316_macro_strike_shadow.py", "EXP-316 Isolated Multi-Strike Convergence Shadow Engine"),
    ("src/polymarket_research/honest_riskless_backtester.py", "v6.0 Honest CLOB L2 Execution Kernel, Zero-Lookahead Harness & CompactCandidateL2Recorder"),
    ("src/polymarket_research/riskless_expansion_v6_engines.py", "v6.0 8-Sleeve Riskless Expansion Engine (XV Subset-NO, 0.001 Tail, BOND3, CAD/USD FX, Deribit USDC, Halftime, PreConv NR3, Yield Box)"),
]

HARVESTER_TEST_MODULES: List[Tuple[str, str]] = [
    ("tests/test_alpha_124_oracles.py", "Unit Tests: Weather METAR/HKO, Jump-SVI Barrier, Pyth Session/Boxes, NBA Boxes, D1, S2 & Wallet"),
    ("tests/test_polymarket_wfo_5fixes.py", "Unit Tests: WFO 5-Fixes, 95c/98c Two-Tranche Supervisor, Phase-3A/Phase-4 Book Walk & Graduation"),
    ("tests/test_zero_trust_forensic_audit.py", "Unit Tests: Zero-Trust Forensics, Centralized Risk Config, Deterministic Replay & <1MB Bundle Sync"),
    ("tests/test_riskless_frontier_v4.py", "Unit Tests: Dynamic-Fee Unblinding & Riskless Frontier v4 Evergreen Sleeves"),
    ("tests/test_v530_forensic_plumbing_fixes.py", "Unit Tests: v5.3.0 Forensic Plumbing & Execution State Machine"),
    ("tests/test_v531_qa_audit_fixes.py", "Unit Tests: v5.3.1 Share-Deducted Fee Parity, Frontier v4 Safety Guards & WS/Recorder Plumbing"),
    ("tests/test_v550_zero_loss_frontier_and_velocity.py", "Unit Tests: v5.5.0 Zero-Loss Frontier, Relayer V2 Batch Merge, Verified m=1 Convert & Velocity"),
    ("tests/test_v560_fill_rate_and_profit_growth.py", "Unit Tests: v5.6.0 Fill-Rate, Profit-Growth, NR_M1 Bridge, WS Clinch Sniper & Sticky FIFO Queue"),
    ("tests/test_v570_ms_velocity_and_ws_sniper.py", "Unit Tests: v5.7.0 Sub-ms Hot-Path Velocity, 450-Token WS Sniper, 2h UMA Recycle & Dynamic Scaling"),
    ("tests/test_v580_sharded_ws_d1fast_pusd_and_direct_feeds.py", "Unit Tests: v5.8.0 4-Shard WS, D1FAST IPC, V2 pUSD Redemption/Wrap & Direct Feeds"),
    ("tests/test_stage_b_economic_attribution.py", "Unit Tests: Stage B Opportunity Funnel, Competitor Decay, Markouts & 10 Institutional KPIs"),
    ("tests/test_stage_c_zero_loss_velocity.py", "Unit Tests: Stage C Zero-Loss Velocity Recycler, Pre-Split Lock & Clinched Split-to-Sell"),
    ("tests/test_priority0_live_leak_fixes.py", "Unit Tests: Priority 0 Live Leaks (Unified Event Cap, UNWRESID Guard, 0%-Fee Plumbing, Stage B & Fast D1 Loop)"),
    ("tests/test_v590_fast_cancel_ws_hedge_and_synthetic_maker.py", "Unit Tests: v5.9.0 1-RTT Fast Cancel, 0-REST WS Fill-to-Hedge, Synthetic Maker Shield & AFF1 Settled Locks"),
    ("tests/test_riskless_remediation_and_8_new_engines.py", "Unit Tests: v6.0 Riskless Remediation, Honest Backtester, CompactCandidateL2Recorder & All 8 New Engines"),
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
    compact_ast: bool = False,
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
            body = transform_module(rel_p, code) if compact_ast else format_unstripped_module(rel_p, code)
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

    a124_mods = [("systemd/polymarket-alpha124-shadow.service", "Alpha-124 Unified Shadow systemd Unit")] + ALPHA124_EXPANSION_MODULES
    a124_text, a124_toc = assemble_bundle(
        title="DOMINUS POLYMARKET ALPHA-124 EXPANSION + PROJECTIONS + TESTS (<1 MB COMPANION BUNDLE)",
        subtitle="Pairs with polymarket_all_in_one.txt (<1 MB) for tools enforcing a 1 MB per-file upload cap",
        modules=a124_mods,
    )
    if len(a124_text.encode("utf-8")) >= 995_000:
        a124_text, a124_toc = assemble_bundle(
            title="DOMINUS POLYMARKET ALPHA-124 EXPANSION + PROJECTIONS + TESTS (<1 MB AST-INVARIANT COMPANION BUNDLE)",
            subtitle="Pairs with polymarket_all_in_one.txt (<1 MB) for tools enforcing a 1 MB per-file upload cap",
            modules=a124_mods,
            compact_ast=True,
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
