"""
Reproducible CLI Runner for Dominus v6.0 Order Sizing & Execution Experiments.
==============================================================================

Usage:
  "C:\\Program Files\\LibreOffice\\program\\python.exe" scripts/run_sizing_experiments.py
"""

from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.polymarket_research.order_sizing_experiments import (
    BANKROLL_SCALES_USD,
    run_full_experiment_suite,
)


def format_12col_markdown_table(summary_rows: list[dict]) -> str:
    headers = [
        "Model / Sleeve",
        "Status",
        "Fee Schedule",
        "Best Sizing Method",
        "Optimal Exec Route",
        "IS EV (bps)",
        "WFO OOS EV (bps)",
        "MC p50 ($48.81)",
        "MC p95 MaxDD (%)",
        "Ruin Prob ($30)",
        "$500 / $5000 OOS EV",
        "Classification",
    ]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for r in summary_rows:
        row = [
            str(r["sleeve_id"]),
            str(r["status"]),
            str(r["fee_schedule"]),
            str(r["best_sizing_method"]),
            str(r["optimal_exec_route"]),
            f"{r['is_net_ev_bps']:.1f}",
            f"{r['wfo_oos_net_ev_bps']:.1f}",
            f"${r['mc_p50_eq_48_81']:.2f}",
            f"{r['mc_p95_max_dd_pct']:.2f}%",
            f"{r['ruin_prob']:.3f}",
            str(r["scaled_500_5000_oos_ev_bps"]),
            str(r["classification"]),
        ]
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Dominus v6.0 order sizing experiments.")
    parser.add_argument("--mc-paths", type=int, default=200, help="Monte Carlo bootstrap paths per experiment")
    parser.add_argument("--seed", type=int, default=20261112, help="Deterministic PRNG seed")
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "data" / "polymarket" / "v6_sizing_experiments_report.json",
        help="Output JSON report path",
    )
    args = parser.parse_args()

    payload = run_full_experiment_suite(
        bankrolls=BANKROLL_SCALES_USD,
        mc_paths=args.mc_paths,
        seed=args.seed,
        output_json_path=args.out,
    )

    print(f"Executed {payload['total_experiments']} experiments across {payload['sleeves_count']} sleeves.")
    print(f"Report written to: {args.out}")
    print("\n=== 12-COLUMN SIZING & EXECUTION SUMMARY TABLE ===")
    print(format_12col_markdown_table(payload["summary_table"]))

    det = payload["detailed_metrics"]
    rl_ids = {
        "C1_BINARY_COMPLETE_SET",
        "D1_SAME_ORACLE_DOMINANCE_BOX",
        "BOND1_UMA_RESOLUTION_CARRY",
        "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",
        "CAL1_CALENDAR_SPREAD_BOX",
        "COND1_CONDITIONAL_MONOTONICITY_BOX",
        "NR_M1_NEGRISK_DEAD_SEED_FANOUT",
        "S2_RTDS_EXACT_TWAP_INTEGRATOR",
    }
    for label, is_rl in [("RISKLESS SLEEVES ($48.81)", True), ("DIRECTIONAL / SHADOW SLEEVES ($48.81)", False)]:
        print(f"\n=== 13-METHOD COMPARISON: {label} ===")
        for m in payload["methods"]:
            items = [d for d in det if d["bankroll_usd"] == 48.81 and d["method"] == m and ((d["sleeve_id"] in rl_ids) == is_rl)]
            if not items:
                continue
            print(
                f"  {m:26s} | wfo_ev={statistics.fmean(x['wfo_net_ev_bps'] for x in items):7.1f} bps "
                f"| p50=${statistics.fmean(x['mc_p50_equity_usd'] for x in items):6.2f} "
                f"| p95_dd={statistics.fmean(x['mc_p95_max_dd_pct'] for x in items):5.2f}% "
                f"| ruin={statistics.fmean(x['ruin_prob'] for x in items):.3f} "
                f"| corr_dd={statistics.fmean(x['corr_stress_max_dd_pct'] for x in items):5.2f}%"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
