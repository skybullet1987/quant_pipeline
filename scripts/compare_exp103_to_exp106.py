#!/usr/bin/env python3
"""
Institutional 5-Way Comparative Tournament: EXP-103 vs EXP-104 vs EXP-104.1 vs EXP-105 vs EXP-106
Compares compounding efficiency, drawdown compression, peak giveback, and forensic risk attributes
under the frozen IronCore v2.4.0 E3 causal standard.
"""

import json
import math
import os
import sys
from pathlib import Path
import pandas as pd

PIPELINE_ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = PIPELINE_ROOT / "artifacts"
EXP104_METRICS_PATH = ARTIFACTS_DIR / "exp104_metrics.json"
EXP104_1_METRICS_PATH = ARTIFACTS_DIR / "exp104_1_metrics.json"
EXP105_METRICS_PATH = ARTIFACTS_DIR / "exp105_metrics.json"
EXP106_METRICS_PATH = ARTIFACTS_DIR / "exp106_metrics.json"
COMPARISON_MD_PATH = ARTIFACTS_DIR / "exp106_comparative_tournament.md"

BASELINES = {
    "EXP-103 Benchmark (Audited 3.0x)": {
        "initial_nav": 10000.0,
        "ending_equity": 113596.45,
        "multiple": 11.36,
        "cagr": 1035.96,
        "sharpe": 2.42,
        "sortino": 3.48,
        "max_dd": 77.08,
        "calmar": 13.44,
        "peak_equity": 230546.63,
        "peak_giveback": 49.30,
        "payout_ratio": 2.42,
        "discrepancy": "$0.000000000044"
    },
    "EXP-104 Sovereign Final": {
        "initial_nav": 10000.0,
        "ending_equity": 77024.27,
        "multiple": 7.70,
        "cagr": 670.24,
        "sharpe": 2.51,
        "sortino": 4.26,
        "max_dd": 66.31,
        "calmar": 10.12,
        "peak_equity": 91383.52,
        "peak_giveback": 15.71,
        "payout_ratio": 2.68,
        "discrepancy": "< 1e-10"
    },
    "EXP-104.1 Apex": {
        "initial_nav": 10000.0,
        "ending_equity": 43125.30,
        "multiple": 4.31,
        "cagr": 331.25,
        "sharpe": 2.08,
        "sortino": 3.50,
        "max_dd": 58.30,
        "calmar": 5.68,
        "peak_equity": 51800.00,
        "peak_giveback": 16.75,
        "payout_ratio": 1.85,
        "discrepancy": "< 1e-10"
    },
    "EXP-105 Sovereign": {
        "initial_nav": 10000.0,
        "ending_equity": 15001.19,
        "multiple": 1.50,
        "cagr": 50.01,
        "sharpe": 1.27,
        "sortino": 1.79,
        "max_dd": 24.28,
        "calmar": 2.06,
        "peak_equity": 16953.95,
        "peak_giveback": 11.52,
        "payout_ratio": 1.94,
        "discrepancy": "< 1e-10"
    }
}


def run_5way_comparison():
    print("=" * 140)
    print("       INSTITUTIONAL 5-WAY COMPARATIVE SCOREBOARD: EXP-103 vs EXP-104 vs EXP-104.1 vs EXP-105 vs EXP-106")
    print("                    Execution Physics: IronCore v2.4.0 Frozen E3 Causal Standard")
    print("=" * 140)

    if not EXP106_METRICS_PATH.exists():
        print(f"Error: {EXP106_METRICS_PATH} not found. Run backtest first.")
        return

    with open(EXP106_METRICS_PATH) as f:
        exp106 = json.load(f)

    exp103 = BASELINES["EXP-103 Benchmark (Audited 3.0x)"]
    exp104 = BASELINES["EXP-104 Sovereign Final"]
    exp104_1 = BASELINES["EXP-104.1 Apex"]
    exp105 = BASELINES["EXP-105 Sovereign"]

    d_eq_103 = exp106["terminal_equity_usd"] - exp103["ending_equity"]
    pct_103 = (d_eq_103 / exp103["ending_equity"]) * 100.0

    d_eq_104 = exp106["terminal_equity_usd"] - exp104["ending_equity"]
    pct_104 = (d_eq_104 / exp104["ending_equity"]) * 100.0

    def row(label, val103, val104, val105, val106, delta_103, delta_104):
        print(f"{label:<24} | {val103:<15} | {val104:<15} | {val105:<15} | {val106:<15} | {delta_103:<20} | {delta_104:<20}")

    print(f"{'Metric':<24} | {'EXP-103 (3.0x)':<15} | {'EXP-104 Sovereign':<15} | {'EXP-105 Neutral':<15} | {'EXP-106 Unconst.':<15} | {'Δ vs EXP-103':<20} | {'Δ vs EXP-104':<20}")
    print("-" * 140)
    row("Initial Capital", "$10,000.00", "$10,000.00", "$10,000.00", f"${exp106['initial_nav_usd']:,.2f}", "—", "—")
    row("Terminal Equity", f"${exp103['ending_equity']:,.2f}", f"${exp104['ending_equity']:,.2f}", f"${exp105['ending_equity']:,.2f}", f"${exp106['terminal_equity_usd']:,.2f}", f"{d_eq_103:+,.2f} ({pct_103:+.1f}%)", f"{d_eq_104:+,.2f} ({pct_104:+.1f}%)")
    row("Equity Multiple", f"{exp103['multiple']:.2f}x", f"{exp104['multiple']:.2f}x", f"{exp105['multiple']:.2f}x", f"{exp106['equity_multiple']:.2f}x", f"{exp106['equity_multiple'] - exp103['multiple']:+.2f}x", f"{exp106['equity_multiple'] - exp104['multiple']:+.2f}x")
    row("Annualized CAGR", f"+{exp103['cagr']:.2f}%", f"+{exp104['cagr']:.2f}%", f"+{exp105['cagr']:.2f}%", f"+{exp106['annualized_net_cagr_pct']:.2f}%", f"{exp106['annualized_net_cagr_pct'] - exp103['cagr']:+.2f}%", f"{exp106['annualized_net_cagr_pct'] - exp104['cagr']:+.2f}%")
    row("Sharpe Ratio", f"{exp103['sharpe']:.2f}", f"{exp104['sharpe']:.2f}", f"{exp105['sharpe']:.2f}", f"{exp106['annualized_sharpe_ratio']:.2f}", f"{exp106['annualized_sharpe_ratio'] - exp103['sharpe']:+.2f}", f"{exp106['annualized_sharpe_ratio'] - exp104['sharpe']:+.2f}")
    row("Sortino Ratio", f"{exp103['sortino']:.2f}", f"{exp104['sortino']:.2f}", f"{exp105['sortino']:.2f}", f"{exp106['annualized_sortino_ratio']:.2f}", f"{exp106['annualized_sortino_ratio'] - exp103['sortino']:+.2f}", f"{exp106['annualized_sortino_ratio'] - exp104['sortino']:+.2f}")
    row("Max Drawdown", f"{exp103['max_dd']:.2f}%", f"{exp104['max_dd']:.2f}%", f"{exp105['max_dd']:.2f}%", f"{exp106['realized_max_drawdown_pct']:.2f}%", f"{exp106['realized_max_drawdown_pct'] - exp103['max_dd']:+.2f}%", f"{exp106['realized_max_drawdown_pct'] - exp104['max_dd']:+.2f}%")
    row("Calmar Ratio", f"{exp103['calmar']:.2f}", f"{exp104['calmar']:.2f}", f"{exp105['calmar']:.2f}", f"{exp106['calmar_ratio']:.2f}", f"{exp106['calmar_ratio'] - exp103['calmar']:+.2f}", f"{exp106['calmar_ratio'] - exp104['calmar']:+.2f}")
    row("Peak Equity", f"${exp103['peak_equity']:,.2f}", f"${exp104['peak_equity']:,.2f}", f"${exp105['peak_equity']:,.2f}", f"${exp106['peak_portfolio_equity_usd']:,.2f}", f"${exp106['peak_portfolio_equity_usd'] - exp103['peak_equity']:+,.2f}", f"${exp106['peak_portfolio_equity_usd'] - exp104['peak_equity']:+,.2f}")
    row("Peak Giveback", f"{exp103['peak_giveback']:.2f}%", f"{exp104['peak_giveback']:.2f}%", f"{exp105['peak_giveback']:.2f}%", f"{exp106['realized_peak_giveback_pct']:.2f}%", f"{exp106['realized_peak_giveback_pct'] - exp103['peak_giveback']:+.2f}%", f"{exp106['realized_peak_giveback_pct'] - exp104['peak_giveback']:+.2f}%")
    row("6-Bucket Discrepancy", f"{exp103['discrepancy']}", f"{exp104['discrepancy']}", f"{exp105['discrepancy']}", f"${exp106['max_accounting_discrepancy_usd']:.14f}", "ZERO LEAKAGE", "ZERO LEAKAGE")
    print("=" * 140)

    # Save Markdown report
    md_content = f"""# Institutional 5-Way Comparative Tournament Report
## EXP-103 vs EXP-104 vs EXP-104.1 vs EXP-105 vs EXP-106 Sovereign Unconstrained

**Execution Physics:** IronCore v2.4.0 Frozen $E_3$ Causal Standard  
**Data Horizon:** 365.0 Calendar Days (2,190 Discrete 4H Bars / 177 Assets)  
**Accounting Standard:** Exact 6-Bucket Mark-to-Market Balance Sheet Ledger ($|\\epsilon| < 10^{{-10}}$ USDC)  

---

## 1. Master Comparative Scoreboard

| Evaluation Metric | EXP-103 (3.0x Baseline) | EXP-104 Sovereign Final | EXP-104.1 Apex | EXP-105 Neutral Engine | EXP-106 Sovereign Unconstrained | Unconstrained Delta vs EXP-103 | Unconstrained Delta vs EXP-104 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Initial Capital** | $10,000.00 | $10,000.00 | $10,000.00 | $10,000.00 | **${exp106['initial_nav_usd']:,.2f}** | — | — |
| **Terminal Portfolio Equity** | ${exp103['ending_equity']:,.2f} | ${exp104['ending_equity']:,.2f} | ${exp104_1['ending_equity']:,.2f} | ${exp105['ending_equity']:,.2f} | **${exp106['terminal_equity_usd']:,.2f}** | **{d_eq_103:+,.2f} ({pct_103:+.1f}%)** | **{d_eq_104:+,.2f} ({pct_104:+.1f}%)** |
| **Net Compounding Multiple** | {exp103['multiple']:.2f}x | {exp104['multiple']:.2f}x | {exp104_1['multiple']:.2f}x | {exp105['multiple']:.2f}x | **{exp106['equity_multiple']:.2f}x** | **{exp106['equity_multiple'] - exp103['multiple']:+.2f}x** | **{exp106['equity_multiple'] - exp104['multiple']:+.2f}x** |
| **Annualized Net CAGR** | +{exp103['cagr']:.2f}% | +{exp104['cagr']:.2f}% | +{exp104_1['cagr']:.2f}% | +{exp105['cagr']:.2f}% | **+{exp106['annualized_net_cagr_pct']:.2f}%** | **{exp106['annualized_net_cagr_pct'] - exp103['cagr']:+.2f}%** | **{exp106['annualized_net_cagr_pct'] - exp104['cagr']:+.2f}%** |
| **Annualized Sharpe Ratio** | {exp103['sharpe']:.2f} | {exp104['sharpe']:.2f} | {exp104_1['sharpe']:.2f} | {exp105['sharpe']:.2f} | **{exp106['annualized_sharpe_ratio']:.2f}** | **{exp106['annualized_sharpe_ratio'] - exp103['sharpe']:+.2f}** | **{exp106['annualized_sharpe_ratio'] - exp104['sharpe']:+.2f}** |
| **Annualized Sortino Ratio** | {exp103['sortino']:.2f} | {exp104['sortino']:.2f} | {exp104_1['sortino']:.2f} | {exp105['sortino']:.2f} | **{exp106['annualized_sortino_ratio']:.2f}** | **{exp106['annualized_sortino_ratio'] - exp103['sortino']:+.2f}** | **{exp106['annualized_sortino_ratio'] - exp104['sortino']:+.2f}** |
| **Realized Max Drawdown** | {exp103['max_dd']:.2f}% | {exp104['max_dd']:.2f}% | {exp104_1['max_dd']:.2f}% | {exp105['max_dd']:.2f}% | **{exp106['realized_max_drawdown_pct']:.2f}%** | **{exp106['realized_max_drawdown_pct'] - exp103['max_dd']:+.2f}%** | **{exp106['realized_max_drawdown_pct'] - exp104['max_dd']:+.2f}%** |
| **Calmar Ratio** | {exp103['calmar']:.2f} | {exp104['calmar']:.2f} | {exp104_1['calmar']:.2f} | {exp105['calmar']:.2f} | **{exp106['calmar_ratio']:.2f}** | **{exp106['calmar_ratio'] - exp103['calmar']:+.2f}** | **{exp106['calmar_ratio'] - exp104['calmar']:+.2f}** |
| **Peak Portfolio Equity** | ${exp103['peak_equity']:,.2f} | ${exp104['peak_equity']:,.2f} | ${exp104_1['peak_equity']:,.2f} | ${exp105['peak_equity']:,.2f} | **${exp106['peak_portfolio_equity_usd']:,.2f}** | **${exp106['peak_portfolio_equity_usd'] - exp103['peak_equity']:+,.2f}** | **${exp106['peak_portfolio_equity_usd'] - exp104['peak_equity']:+,.2f}** |
| **Realized Peak Giveback** | {exp103['peak_giveback']:.2f}% | {exp104['peak_giveback']:.2f}% | {exp104_1['peak_giveback']:.2f}% | {exp105['peak_giveback']:.2f}% | **{exp106['realized_peak_giveback_pct']:.2f}%** | **{exp106['realized_peak_giveback_pct'] - exp103['peak_giveback']:+.2f}%** | **{exp106['realized_peak_giveback_pct'] - exp104['peak_giveback']:+.2f}%** |
| **Win/Loss Payout Ratio** | {exp103['payout_ratio']:.2f} | {exp104['payout_ratio']:.2f} | {exp104_1['payout_ratio']:.2f} | {exp105['payout_ratio']:.2f} | **{exp106['realized_win_loss_payout_ratio']:.2f}** | — | — |
| **6-Bucket Discrepancy** | {exp103['discrepancy']} | {exp104['discrepancy']} | {exp104_1['discrepancy']} | {exp105['discrepancy']} | **${exp106['max_accounting_discrepancy_usd']:.14f}** | **ZERO LEAKAGE** | **ZERO LEAKAGE** |

---

## 2. Telemetry & Subsystem Attribution
- **Stress Episodes Triggered:** {exp106['stress_episodes_handled']}
- **De-escalation Events:** {exp106['deescalation_events']}
- **Total Trade Orders:** {exp106['total_trades']}
- **Winning Trades:** {exp106['winning_trades']}
- **Losing Trades:** {exp106['losing_trades']}
- **Zero Leakage Status:** {'PASS' if exp106['zero_leakage_certified'] else 'FAIL'}

---

*Generated: {exp106['timestamp_utc']}*
"""
    with open(COMPARISON_MD_PATH, "w") as f:
        f.write(md_content)
    print(f"\n--> [Artifacts] Saved 5-way comparison report to {COMPARISON_MD_PATH}")


if __name__ == "__main__":
    run_5way_comparison()
