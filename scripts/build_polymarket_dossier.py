#!/usr/bin/env python3
"""
POLYMARKET MASTER DOSSIER & CODEBASE AGGREGATOR (COMPACT < 1MB EDITION)
=======================================================================
Compiles the Polymarket quantitative architecture, live vs paper vs shadow stats,
forensic bug post-mortem, and all core production source modules into a single
authoritative master review dossier with total file size strictly under 1 MB.
"""

import os
import sys
import json
import re
from datetime import datetime, timezone
from pathlib import Path

PIPELINE_ROOT = Path(__file__).resolve().parent.parent

SUBSYSTEMS = [
    # Subsystem 1: Production Daemons & Live Execution
    ("1. Core Production Daemons & Live Execution", [
        ("src/polymarket_research/polymarket_live_harvester.py", "Production real-time execution harvester implementing Policy B2, sweet-spot gating, dynamic Kelly sizing, opposite-trend salvage, and fail-closed risk controls."),
        ("src/polymarket_research/polymarket_live_executor.py", "Polymarket CLOB L2 EIP-712 execution adapter, OrderArgsV2 validation, fee calculation, durable inventory reservations, and on-chain reconciliation."),
        ("src/polymarket_research/polymarket_paper_trader.py", "Zero-latency paper trading daemon with 100ms trigger stream polling, piecewise MILP execution simulation, and parity ledger logging."),
        ("src/polymarket_research/polymarket_terminal_recorder.py", "Institutional 250ms multi-slice orderbook & trades recorder with cross-venue synchronized telemetry stream."),
        ("src/polymarket_research/check_polymarket_balance.py", "CLOB L2 collateral balance, POL gas balance, and funder deposit wallet inspector."),
        ("src/polymarket_research/setup_polymarket_account.py", "Polymarket CLOB API credentials onboarding, L1/L2 wallet derivation, and HMAC key generator."),
        ("src/polymarket_research/execute_approvals.py", "Polygon mainnet ERC-20 (USDC.e) and ERC-1155 (CTF Exchange) maximum allowance approvals."),
        ("src/polymarket_research/redeem_settled_positions.py", "Automated CTF exchange token redemption daemon for binary payout collection."),
        ("src/polymarket_research/verify_onchain_allowances.py", "On-chain verification script ensuring CTF Exchange and NegRisk adapters hold valid infinite allowances."),
        ("src/polymarket_research/monitor_live_trades.py", "Real-time CLI live monitor tailing live orders, execution latency, and position reconciliation.")
    ]),
    
    # Subsystem 2: Shadow Engines & Quantitative Sleeves
    ("2. Quantitative Alpha Sleeves & Shadow Research", [
        ("src/polymarket_research/exp303_fast_unwind_shadow.py", "EXP-303 fast-unwind shadow engine comparing Policy A (hold to expiry), Policy B1 (taker unwind), and Policy B2 (maker scalp)."),
        ("src/polymarket_research/exp303b_crypto_market_registry.py", "Canonical registry indexing Polymarket BTC/ETH 1h/15m strikes, token IDs, condition IDs, and Gamma metadata."),
        ("src/polymarket_research/exp304_multi_asset_latency_engine.py", "Sleeve 2 multi-asset cross-venue latency engine exploiting BTC/ETH lead-lag across Binance and Polymarket."),
        ("src/polymarket_research/exp306_expiry_boundary_engine.py", "Expiry boundary sniper trading ultra-late mispriced options under terminal probability decay."),
        ("src/polymarket_research/exp308_queue_persistence_profiler.py", "Queue persistence profiler measuring fill probabilities and maker order queue decay on Polymarket CLOB."),
        ("src/polymarket_research/pm_hwr_001/audit_and_baseline.py", "PM-HWR-001 research campaign baseline audit and accounting invariants verification."),
        ("src/polymarket_research/pm_hwr_001/audit_exp303_simulation.py", "Adversarial simulation audit stress-testing EXP-303 execution assumptions under adverse selection."),
        ("src/polymarket_research/pm_hwr_001/backtest_engine.py", "Comprehensive backtesting engine simulating Polymarket CLOB microstructure, fee drag, and fill probabilities."),
        ("src/polymarket_research/pm_hwr_001/shock_grid_sweep.py", "Parameter grid sweep optimizing shock distance thresholds, TTE filters, and Kelly sizing multipliers."),
        ("src/polymarket_research/pm_hwr_001/statistical_evaluation.py", "Statistical evaluation suite generating Sharpe, Sortino, Calmar, and trade distribution metrics.")
    ]),
    
    # Subsystem 3: Operational Automation Scripts
    ("3. Operational Automation Scripts", [
        ("scripts/backtest_opposite_breakout_salvage.py", "Backtesting script evaluating opposite-side structural breakout salvage stops to cut binary tail losses."),
        ("scripts/watch_and_reload_post_settlement.py", "Automated watchdog recycling capital post-settlement and restarting execution daemons."),
        ("scripts/reload_production_daemons.py", "Zero-downtime daemon reloader applying configuration updates and prewarming market caches."),
        ("scripts/generate_hourly_trade_report.py", "Automated hourly trade report generator summarizing fills, PnL, fees, and telemetry across sleeves."),
        ("scripts/run_polymarket_harvester.sh", "Production bash wrapper configuring environment variables, CPU affinity, and systemd execution.")
    ]),
    
    # Subsystem 4: Full Invariant & Production Test Suites
    ("4. Full Invariant & Production Test Suites", [
        ("tests/test_polymarket_executor.py", "Master executor test suite verifying EIP-712 signing, order routing, fee math, and reconciliation invariants."),
        ("tests/test_polymarket_execution_parity.py", "Execution parity suite testing identical fill logic between live CLOB and paper trading engines."),
        ("tests/test_polymarket_refinements_production.py", "Production refinements suite validating sweet-spot price bands, depth ratios, and slippage guards."),
        ("tests/test_opposite_breakout_salvage.py", "Opposite breakout salvage stop invariant tests validating early loss cutting under violent trend moves."),
        ("tests/test_polymarket_sleeve2_mutual_exclusion.py", "Mutual exclusion suite ensuring Sleeve 1 and Sleeve 2 cannot submit conflicting positions on identical markets."),
        ("tests/test_polymarket_post_loss_sizing_and_purge.py", "Post-loss sizing recovery and stale order purging test suite."),
        ("tests/test_sleeve_2_trend_guard_and_reversals.py", "Trend guard and multi-hour trend alignment verification suite for Sleeve 2.")
    ]),
    
    # Subsystem 5: Systemd Service Units
    ("5. Systemd Service Units", [
        ("systemd/polymarket-live-harvester.service", "Production systemd unit for Polymarket live harvester daemon with automatic restart on failure."),
        ("systemd/polymarket-trader.service", "Systemd unit managing paper trading daemon with continuous telemetry logging."),
        ("systemd/polymarket-recorder.service", "Systemd unit maintaining real-time orderbook and trades websocket recording.")
    ])
]

def clean_source(code: str) -> str:
    lines = [l.rstrip() for l in code.splitlines()]
    text = "\n".join(lines)
    # Collapse 3 or more blank lines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def generate_dossier():
    out_path = PIPELINE_ROOT / "polymarket_complete_codebase_dossier.md"
    print(f"Generating Compact Master Dossier (< 1MB) at {out_path}...")
    
    lines = []
    
    # Header
    lines.append("# Polymarket Quantitative Alpha Architecture & Master Single-File Codebase Dossier")
    lines.append("")
    lines.append("**Document Classification**: Institutional Algorithmic Trading Architecture, Comparative Performance Review & Master Codebase Dossier  ")
    lines.append(f"**Snapshot Date**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}  ")
    lines.append("**Release Version**: Production Hardened Release 2.5.2 (Curated < 1MB Master Review Edition)  ")
    lines.append(f"**Repository Root**: `{PIPELINE_ROOT}`  ")
    lines.append("**Execution Node**: `quant-pipeline-finland` (`europe-north1-b`)  ")
    lines.append("**Network**: Polygon Mainnet (Chain ID: 137) | **CLOB Gateway**: `https://clob.polymarket.com`  ")
    lines.append("**Funder Deposit Wallet**: `0x013A2474454fBd8738cff6a7f204eF1bc377F4e9`  ")
    lines.append("**Verified On-Chain CLOB Collateral**: **$91.67 USD** (L2 Verified Liquid Cash, 0 Open Positions)  ")
    lines.append("**Current Operational State**: Circuit Breaker Active at $95.00 Equity Floor ($91.67 < $95.00)  ")
    lines.append("**Target File Size**: **< 1.0 MB Strict Target** (Compliant for single-file LLM/ide review)  ")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Table of Contents
    lines.append("## Table of Contents")
    lines.append("1. [Executive Summary & Strategic Architecture](#1-executive-summary--strategic-architecture)")
    lines.append("2. [Comprehensive Performance Audit: Live vs Paper vs Shadow Trading](#2-comprehensive-performance-audit-live-vs-paper-vs-shadow-trading)")
    lines.append("3. [Forensic Post-Mortem & Bug Inventory: Why Live Has Been Flawed](#3-forensic-post-mortem--bug-inventory-why-live-has-been-flawed)")
    lines.append("4. [Mathematical Microstructure, Fee Dynamics & Execution Mechanics](#4-mathematical-microstructure-fee-dynamics--execution-mechanics)")
    lines.append("5. [Master Codebase Index & Subsystem Manifest](#5-master-codebase-index--subsystem-manifest)")
    lines.append("6. [Complete Source Code Bundle (All 35 Modules)](#6-complete-source-code-bundle-all-35-modules)")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Section 1
    lines.append("## 1. Executive Summary & Strategic Architecture")
    lines.append("")
    lines.append("This document serves as the **authoritative, single-file master review artifact** for the entire Polymarket algorithmic trading infrastructure within the `quant_pipeline` repository, curated to remain strictly **under 1 MB**.")
    lines.append("")
    lines.append("### System Purpose & Alpha Vectors")
    lines.append("The system operates on **Polymarket (Polygon CLOB)** and executes high-probability statistical arbitrage and latency-directed shock harvesting on crypto prediction markets (primarily 1-hour and 15-minute Bitcoin and Ethereum Up/Down contracts).")
    lines.append("")
    lines.append("The infrastructure encompasses three production sleeves and two shadow engines:")
    lines.append("- **Sleeve 1 (Subhourly 15m Scalper & Policy B2 Fast Unwind)**: Captures sudden Binance/Polymarket lead-lag price shocks via FOK taker snipes in late-cycle candles (TTE 60s to 1350s), then instantly places a 0%-fee Maker take-profit scalp order (+8¢ to +10¢ target) to capture fast unwind repricing.")
    lines.append("- **Sleeve 2 (Multi-Asset Latency Engine - EXP-304/315)**: Trades early-to-mid candle horizons (1350s < TTE <= 3300s) on BTC and ETH contracts, exploiting cross-asset volatility spillover with a resting 0.99 maker limit exit or hold-to-maturity.")
    lines.append("- **Sleeve 3 (Macro Strike Shadow - EXP-316)**: Evaluates daily and weekly prediction markets, identifying structural underpricing in tail outcomes.")
    lines.append("")
    lines.append("### Current System State (Oct 19, 2026)")
    lines.append("- **On-Chain L2 Balance**: **$91.67 USD** liquid collateral on Polymarket CLOB.")
    lines.append("- **Live Trades Executed**: 18 closed live positions (14 wins, 4 losses, 77.78% win rate).")
    lines.append("- **Financial Result**: Realized PnL of **-$95.55 USD** from peak bankroll.")
    lines.append("- **Circuit Breaker Status**: **HALTED**. At 05:00:10 UTC on Oct 19, 2026, total equity reached $91.67, which breached the `CIRCUIT_BREAKER_EQUITY_FLOOR` of $95.00. The automated kill-switch cancelled all resting orders and refused new order entries.")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Section 2
    lines.append("## 2. Comprehensive Performance Audit: Live vs Paper vs Shadow Trading")
    lines.append("")
    lines.append("A rigorous audit was performed across all historical execution ledgers. The data reveals an enormous divergence between theoretical simulations, paper trading, and real-money live execution:")
    lines.append("")
    lines.append("### Master Comparative Performance Table")
    lines.append("")
    lines.append("| Metric | Live Trading (Real Money CLOB) | Paper Trading (Validation Ledger) | Shadow Sleeve 2 (EXP-304/315) | Shadow EXP-303 (Policy A: Hold) | Shadow EXP-303 (Policy B2: Scalp) |")
    lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
    lines.append("| **Environment** | Polygon Mainnet Real Cash | Zero-Latency Sim (Parity) | Shadow Orderbook Paper | Telemetry Replay Sim | Microstructure Scalp Sim |")
    lines.append("| **Total Trades** | **18** | **509** | **24** | **450** | **450** |")
    lines.append("| **Wins / Losses** | 14 / 4 | 406 / 103 | 18 / 6 | 364 / 86 | 450 / 0 |")
    lines.append("| **Win Rate** | **77.78%** | **79.76%** | **75.00%** | **80.89%** | **100.00%** *(Simulated)* |")
    lines.append("| **Gross Profit** | +$95.73 | +$6,193.65 | +$251.58 | +$5,593.93 | +$2,783.25 |")
    lines.append("| **Gross Loss** | -$191.28 | -$5,122.43 | -$303.92 | -$4,678.34 | $0.00 |")
    lines.append("| **Net PnL** | **-$95.55** | **+$1,071.22** | **-$52.34** | **+$915.59** | **+$2,783.25** |")
    lines.append("| **Profit Factor** | **0.50** | **1.21** | **0.83** | **1.20** | **Infinity** |")
    lines.append("| **Average Win** | **+$6.84** | **+$15.26** | **+$13.98** | **+$15.37** | **+$6.18** |")
    lines.append("| **Average Loss** | **-$47.82** | **-$49.73** | **-$50.65** | **-$54.40** | **$0.00** |")
    lines.append("| **Payoff Ratio (Win/Loss)** | **0.143** *(1 : 7.0)* | **0.307** *(1 : 3.2)* | **0.276** *(1 : 3.6)* | **0.282** *(1 : 3.5)* | N/A |")
    lines.append("| **Mathematical Expectancy** | **-$5.31 / trade** | **+$2.10 / trade** | **-$2.18 / trade** | **+$2.03 / trade** | **+$6.18 / trade** |")
    lines.append("| **Breakeven Win Rate Required**| **87.50%** | **76.52%** | **78.38%** | **77.97%** | N/A |")
    lines.append("| **Max Drawdown** | **$133.92** | **$1,086.23** | **$290.99** | **$998.30** | **$0.00** |")
    lines.append("| **Active Risk State** | **HALTED (< $95 floor)** | Active | Monitored | Benchmark | Deprecated (Flawed) |")
    lines.append("")
    lines.append("### Key Statistical Takeaways")
    lines.append("1. **The Asymmetric Binary Trap (The 1 : 7 Payoff Problem)**: In live trading, successful trades generated an average profit of **+$6.84** (+8¢ to +10¢ scalps). When an adverse move occurred, holding to binary expiry caused a 100% notional loss (**-$47.82 average loss**). This 1 : 7 payoff ratio requires an **87.5% win rate** to break even, causing negative drift (-$5.31/trade).")
    lines.append("2. **Simulation Distortion in EXP-303 (100% Win Rate Mirage)**: EXP-303 Shadow assumed every trade could exit after 90 seconds at a +10¢ higher maker price. In reality, during violent adverse spot trends, maker bids vanish and resting sell orders never fill, dragging positions to binary expiry at $0.00.")
    lines.append("3. **Paper vs Live Divergence**: Paper trading averaged **+$15.26** per win (payoff ratio 0.307, achieving +$2.10/trade expectancy at 79.76% win rate). Live trading win size collapsed to **+$6.84** due to live taker fees and conservative +8¢ scalping, while losses remained near -$50.")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Section 3
    lines.append("## 3. Forensic Post-Mortem & Bug Inventory: Why Live Has Been Flawed")
    lines.append("")
    lines.append("An exhaustive forensic analysis of `live_orders.jsonl`, `live_harvester_state.json`, and `live_harvester.log` reveals **7 distinct classes of catastrophic bugs and architectural defects** that degraded real-money execution:")
    lines.append("")
    lines.append("### Bug 1: The Phantom Loss Bug (`MARKET_RESOLVED_NO_INVENTORY`)")
    lines.append("- **Severity**: CRITICAL / SEVERE ACCOUNTING DEFECT")
    lines.append("- **Affected Trade**: `LIVE_5775868_1792336757_UP` (2026-10-18 15:19:18 UTC)")
    lines.append("- **Financial Impact**: **-$41.59 USD phantom loss deducted from internal bankroll**")
    lines.append("- **Mechanism**: The CLOB rejected the entry order with `400 Bad Request` (`invalid amounts`). `polymarket_live_executor.py` flagged `outcome_unknown: true`. The harvester tracked it in `active_positions` despite `entry_order_id=None` and `remaining_shares=0.0`. When the market resolved (UP won!), the settlement code concluded that because 0 shares were held, the trade was lost (`close_reason: MARKET_RESOLVED_NO_INVENTORY`, `net_pnl_usd: -41.59`), deducting $41.59 even though no tokens were ever bought on-chain.")
    lines.append("")
    lines.append("### Bug 2: Missing Hard Salvage Stops on Violent Trend Moves (Binary Blowout)")
    lines.append("- **Severity**: CRITICAL ALPHA RISK DEFECT")
    lines.append("- **Affected Trades**: `LIVE_5790523` (-$56.44), `LIVE_5791402` (-$57.08), `LIVE_5794280` (-$36.17)")
    lines.append("- **Financial Impact**: **-$149.69 USD total real capital wiped out**")
    lines.append("- **Mechanism**: The model initiated DOWN positions during late-candle shocks. Underlying spot reversed into sharp upward trends. Resting maker sell orders at 0.99 never filled. The bot lacked an aggressive market-sell stop or structural trend salvage, holding positions directly into binary expiry ($0.00 payout), losing 100% of invested capital.")
    lines.append("")
    lines.append("### Bug 3: CLOB Client Decimal Precision & Version Compatibility (115 API Rejections)")
    lines.append("- **Severity**: HIGH OPERATIONAL DEFECT")
    lines.append("- **Mechanism**: Polymarket CLOB enforces strict decimal precision: market buy maker amounts support max 2 decimals, and taker amounts support max 4 decimals. Floating point notionals (e.g. `$41.499997` or share counts with 14 decimal digits) triggered 115 immediate 400 Bad Request rejections before OrderArgsV2 quantization was deployed.")
    lines.append("")
    lines.append("### Bug 4: Hot-Path On-Chain RPC Snapshot Latency (58 Resets, 29 Timeouts)")
    lines.append("- **Severity**: HIGH LATENCY & RELIABILITY DEFECT")
    lines.append("- **Mechanism**: In `polymarket_live_executor.py`, taking synchronous `eth_call` queries to Polygon RPC prior to urgent order placement stalled the asyncio event loop by 500ms–2000ms, causing stale pricing or dropped connections.")
    lines.append("")
    lines.append("### Bug 5: NameError Crash Hazards in Production Hot Path")
    lines.append("- **Severity**: MEDIUM CODE HYGIENE DEFECT")
    lines.append("- **Mechanism**: In two separate production events, the harvester crashed with `NameError: name 'prefetched_pre_balance' is not defined` inside `execute_order()` when exception handling referenced uninitialized state.")
    lines.append("")
    lines.append("### Bug 6: Liquidity Crisis & Settlement Deadlock (`SETTLEMENT_BLOCKED`)")
    lines.append("- **Severity**: HIGH SYSTEMIC RISK DEFECT")
    lines.append("- **Mechanism**: On trade `LIVE_5790523`, adverse bid evaporation marked `LIQUIDITY_CRISIS` with `exit_cash_estimated: true`. Settlement logic refused to settle with estimated cash, initiating a persistent `[GLOBAL HALT]` that blocked profitable entries in subsequent hours.")
    lines.append("")
    lines.append("### Bug 7: Aggressive Ticket Sizing & Circuit Breaker Trip ($91.67 < $95.00)")
    lines.append("- **Severity**: CAPITAL CONSERVATION TRIGGER")
    lines.append("- **Mechanism**: Sizing tickets at 25%-30% of bankroll ($35 to $56) on a small account ($160-$217) allowed 3 adverse trend blowouts to breach the $95.00 equity floor at 05:00 UTC on Oct 19, triggering `DELETE /cancel-all` and halting the harvester.")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Section 4
    lines.append("## 4. Mathematical Microstructure, Fee Dynamics & Execution Mechanics")
    lines.append("")
    lines.append("### Dynamic Crypto Taker Fee Formula")
    lines.append("$$\\text{Fee Rate}(p) = \\text{base\\_rate} \\times \\left(1 - |2p - 1|\\right)$$")
    lines.append("- At $p = 0.50$, taker fee peaks at $7.00\\%$ of notional.")
    lines.append("- At $p = 0.85$ (sweet spot entry), the fee rate drops to $0.07 \\times (1 - |1.70 - 1|) = 2.10\\%$.")
    lines.append("- For maker limit orders (e.g. resting $0.99$ take-profit sell), **Polymarket charges $0.00\\%$ maker fees**.")
    lines.append("")
    lines.append("### Policy B2 Mathematical Formulation")
    lines.append("1. **Entry**: Immediate FOK aggressive buy at ask $p_{\\text{entry}} \\in [0.65, 0.88]$. Paid taker fee $F_{\\text{entry}}$.")
    lines.append("2. **Delivered Cost Basis**: $C_{\\text{delivered}} = p_{\\text{entry}} + \\frac{F_{\\text{entry}}}{N_{\\text{shares}}}$.")
    lines.append("3. **Resting Exit**: Post-only limit sell placed at $p_{\\text{exit}} = \\min(0.99, C_{\\text{delivered}} + \\theta)$, where $\\theta = 0.08$ to $0.10$.")
    lines.append("4. **Maker Fee**: $0.00\\%$. Preserves net scalp margin without paying an exit fee.")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Section 5: Manifest
    lines.append("## 5. Master Codebase Index & Subsystem Manifest")
    lines.append("")
    lines.append("Below is the manifest of all 35 core production modules bundled in full within Section 6:")
    lines.append("")
    
    file_idx = 1
    total_loc = 0
    manifest_rows = []
    
    for sub_title, files in SUBSYSTEMS:
        lines.append(f"### {sub_title}")
        lines.append("")
        lines.append("| # | File Path | Lines | Size | Anchor Link | Description |")
        lines.append("| :-: | :--- | :-: | :-: | :--- | :--- |")
        
        for rel_path, desc in files:
            full_path = PIPELINE_ROOT / rel_path
            loc = 0
            sz_str = "0 KB"
            cleaned_text = ""
            if full_path.exists():
                raw = full_path.read_text(errors="ignore")
                cleaned_text = clean_source(raw)
                loc = len(cleaned_text.splitlines())
                total_loc += loc
                sz_str = f"{len(cleaned_text.encode('utf-8')) / 1024:.1f} KB"
            
            anchor = "module-" + re.sub(r"[^a-zA-Z0-9_-]", "-", rel_path.lower())
            lines.append(f"| {file_idx} | `{rel_path}` | {loc} | {sz_str} | [View Source](#{anchor}) | {desc} |")
            manifest_rows.append((file_idx, rel_path, loc, sz_str, anchor, desc, cleaned_text))
            file_idx += 1
        lines.append("")
        
    lines.append(f"**Total Curated Codebase Volume**: **{total_loc:,} lines of code** across **{file_idx - 1} core modules**.")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Section 6: Source Bundle
    lines.append(f"## 6. Complete Source Code Bundle (All {file_idx - 1} Modules)")
    lines.append("")
    lines.append("The following section contains the complete source code for all modules in the Polymarket trading architecture, formatted in markdown syntax-highlighted blocks:")
    lines.append("")
    
    for f_num, rel_path, loc, sz_str, anchor, desc, cleaned_text in manifest_rows:
        full_path = PIPELINE_ROOT / rel_path
        ext = full_path.suffix.lower()
        lang = "python"
        if ext == ".sh": lang = "bash"
        elif ext == ".service": lang = "ini"
        elif ext in (".json", ".jsonl"): lang = "json"
        elif ext == ".md": lang = "markdown"
        
        lines.append(f"<a id=\"{anchor}\"></a>")
        lines.append(f"### Module {f_num:02d}: `{rel_path}`")
        lines.append(f"- **File Location**: `file://{full_path}`  ")
        lines.append(f"- **Volume**: {loc} lines | {sz_str}  ")
        lines.append(f"- **Description**: {desc}  ")
        lines.append("")
        lines.append(f"```{lang}")
        lines.append(cleaned_text)
        lines.append("```")
        lines.append("")
        lines.append("---")
        lines.append("")
        
    final_content = "\n".join(lines)
    out_path.write_text(final_content, encoding="utf-8")
    sz_bytes = out_path.stat().st_size
    print(f"Master Dossier successfully written: {out_path}")
    print(f"Final Size: {sz_bytes} bytes ({sz_bytes / 1024:.1f} KB / {sz_bytes / 1024 / 1024:.3f} MB)")
    if sz_bytes < 1000000:
        print("SUCCESS: File size is strictly UNDER 1 MB (both decimal 1,000,000 bytes and binary 1,048,576 bytes)!")
    elif sz_bytes < 1048576:
        print("SUCCESS: File size is strictly under 1 MiB (1,048,576 bytes)!")
    else:
        print("WARNING: File size exceeds 1 MB!")

if __name__ == "__main__":
    generate_dossier()
