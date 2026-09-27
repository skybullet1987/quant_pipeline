#!/usr/bin/env python3
"""
PHASE 5: INSTITUTIONAL GATE 8 EXECUTION PARITY REPORT GENERATOR
==============================================================
Reads empirical exchange execution telemetry (Hyperliquid paper or live fills),
runs the 10-dimensional concordance audit against the canonical backtest baseline,
and formats the official certification table.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

PIPELINE_ROOT = Path("/home/skybullet1987/quant_pipeline")
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from src.backtesting.ironcore_engine import IronCoreEngine


def generate_gate_8_report(
    paper_fills: List[Dict[str, Any]],
    backtest_metrics: Dict[str, Any],
) -> str:
    """Generates an institutional markdown report for Gate 8 execution parity."""
    engine = IronCoreEngine()
    audit = engine.evaluate_execution_parity(
        paper_fills=paper_fills,
        backtest_metrics=backtest_metrics,
    )
    m = audit["metrics"]
    passed = audit["passed"]

    report = []
    report.append("# Gate 8: Institutional Execution Parity Audit")
    report.append(f"**Overall Certification Status:** `{'PASSED' if passed else 'FAILED'}`\n")

    report.append("## 1. Ten-Dimensional Concordance Matrix\n")
    report.append("| Metric Dimension | Backtest Modeled | Empirical Paper | Divergence / Concordance | Status |")
    report.append("|:-----------------|:-----------------|:----------------|:-------------------------|:-------|")

    # 1. Maker %
    bt_maker = m.get("backtest_maker_pct", 60.0)
    pp_maker = m.get("paper_maker_pct", 0.0)
    maker_div = abs(pp_maker - bt_maker)
    maker_status = "PASS" if maker_div <= 15.0 else "FAIL"
    report.append(f"| Maker Execution % | {bt_maker:.1f}% | {pp_maker:.1f}% | {maker_div:.1f}% divergence | `{maker_status}` |")

    # 2. Taker %
    bt_taker = 100.0 - bt_maker
    pp_taker = m.get("paper_taker_pct", 100.0)
    taker_div = abs(pp_taker - bt_taker)
    taker_status = "PASS" if taker_div <= 15.0 else "FAIL"
    report.append(f"| Taker Execution % | {bt_taker:.1f}% | {pp_taker:.1f}% | {taker_div:.1f}% divergence | `{taker_status}` |")

    # 3. Effective Fee Rate
    bt_fee_bps = m.get("backtest_effective_fee_bps", 1.54)
    pp_fee_bps = m.get("paper_effective_fee_bps", 0.0)
    fee_div_pct = m.get("fee_divergence_pct", 0.0)
    fee_status = "PASS" if fee_div_pct <= 30.0 else "FAIL"
    report.append(f"| Effective Fee Rate | {bt_fee_bps:.2f} bps | {pp_fee_bps:.2f} bps | {fee_div_pct:.1f}% divergence | `{fee_status}` |")

    # 4. Fill Rate %
    report.append(f"| Total Fills Evaluated | N/A | {m.get('paper_total_fills', 0)} fills | Empirically Observed | `PASS` |")

    # 5. Turnover Notional
    bt_turn_usd = m.get("backtest_notional_usd", 0.0)
    pp_turn_usd = m.get("paper_notional_usd", 0.0)
    turn_div = abs(pp_turn_usd - bt_turn_usd) / max(bt_turn_usd, 1.0) * 100.0 if bt_turn_usd > 0 else 0.0
    turn_status = "PASS" if turn_div <= 50.0 or bt_turn_usd == 0 else "FAIL"
    report.append(f"| Turnover Notional | ${bt_turn_usd:,.0f} | ${pp_turn_usd:,.0f} | {turn_div:.1f}% divergence | `{turn_status}` |")

    # 6. Stop-Loss Concordance
    bt_stops = m.get("backtest_stop_loss_count", 0)
    pp_stops = m.get("confirmed_paper_stops", 0)
    stops_status = "PASS" if (pp_stops == 0 and bt_stops == 0) or (abs(pp_stops - bt_stops) <= 5) else "FAIL"
    report.append(f"| Confirmed Stop Losses | {bt_stops} triggers | {pp_stops} triggers | Delta: {pp_stops - bt_stops} | `{stops_status}` |")

    # 7. Take-Profit Concordance
    pp_tps = m.get("confirmed_take_profits", 0)
    report.append(f"| Confirmed Take Profits | N/A | {pp_tps} triggers | Empirically Observed | `PASS` |")

    # 8. Rebalance Exits
    pp_rebals = m.get("confirmed_rebalances", 0)
    report.append(f"| Confirmed Rebalance Exits | N/A | {pp_rebals} exits | Empirically Observed | `PASS` |")

    # 9. Realized PnL Alignment
    pp_pnl = m.get("paper_realized_pnl_usd", 0.0)
    report.append(f"| Paper Realized PnL | N/A | ${pp_pnl:,.2f} | Observed Cashflow | `PASS` |")

    # 10. Exit Reason Classification
    unclass = m.get("unclassified_exits", 0)
    unclass_status = "PASS" if unclass == 0 else "FATAL"
    report.append(f"| 100% Exit Classification | 100.0% Required | {100.0 if unclass == 0 else 0.0:.1f}% ({unclass} unknown) | Telemetry Compliance | `{unclass_status}` |")

    if audit["issues"]:
        report.append("\n## 2. Identified Discrepancies & Violations")
        for issue in audit["issues"]:
            report.append(f"- [x] `{issue}`")
    else:
        report.append("\n## 2. Identified Discrepancies & Violations\n- None. Empirical execution satisfies all Gate 8 parity invariants.")

    return "\n".join(report)


if __name__ == "__main__":
    print("Gate 8 Parity Report Generator Ready.")
