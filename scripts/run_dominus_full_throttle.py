"""
DOMINUS — RISKLESS FULL THROTTLE
Multi-Cycle Live Shadow & Research Runner (`scripts/run_dominus_full_throttle.py`)

Owned exclusively by `@pipeline-shadow`.

Executes the 10-Stage Full-Throttle Opportunity Pipeline across `DISCOVERY_CYCLE`,
`FAST_CYCLE`, and `RESEARCH_CYCLE` against live public Polymarket Gamma `/events/keyset`
and batched CLOB `POST /books` endpoints (`< 180 MiB` RSS swapless-host safe),
updating `data/full_throttle/pipeline/*` and rendering `FULL_THROTTLE_DASHBOARD.md`.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.generate_full_throttle_dashboard import generate_dashboard_files
from src.polymarket_research.full_throttle_pipeline import (
    DEFAULT_LIVE_RECONCILED_NAV_USD,
    ExecutionMode,
    ExecutionModeGateConfig,
    FullThrottlePipeline,
    PipelineConfig,
)


def parse_mode(raw: str) -> ExecutionMode:
    s = str(raw or "shadow").strip().upper()
    if s in ("RESEARCH", "MODE_1", "MODE_1_RESEARCH"):
        return ExecutionMode.MODE_1_RESEARCH
    if s in ("SHADOW", "MODE_2", "MODE_2_SHADOW"):
        return ExecutionMode.MODE_2_SHADOW
    if s in ("LIVE", "MODE_3", "MODE_3_LIVE"):
        return ExecutionMode.MODE_3_LIVE
    raise ValueError(f"Unsupported mode: {raw}")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run DOMINUS Full-Throttle 10-Stage Opportunity Pipeline.")
    parser.add_argument("--mode", default="shadow", help="research | shadow (default) | live (hard-locked)")
    parser.add_argument("--jurisdiction", default="CA-ON", help="Jurisdiction gate code (default: CA-ON)")
    parser.add_argument(
        "--cycles",
        type=int,
        default=None,
        help="Total operating cycles to run in timer/oneshot mode (1 DISCOVERY_CYCLE + max(0, N-1) FAST_CYCLEs)",
    )
    parser.add_argument("--discovery-sweeps", type=int, default=1, help="Number of full Gamma keyset discovery sweeps")
    parser.add_argument("--fast-cycles", type=int, default=2, help="Number of FAST_CYCLE book refreshes per sweep")
    parser.add_argument("--no-research-cycle", action="store_true", help="Skip trailing RESEARCH_CYCLE")
    parser.add_argument("--inter-cycle-pause", type=float, default=1.5, help="Pause in seconds between fast cycles")
    parser.add_argument("--max-book-tokens-discovery", type=int, default=1800)
    parser.add_argument("--max-book-tokens-fast", type=int, default=1100)
    parser.add_argument("--cold-rotation-tokens", type=int, default=350)
    parser.add_argument("--max-gamma-pages", type=int, default=950)
    parser.add_argument("--resume-checkpoint", action="store_true", help="Load prior checkpoint_state.json before running")
    parser.add_argument(
        "--emit-harvester-candidates",
        action="store_true",
        help="Emit verified CLASS_A and <=2-leg CLASS_B opportunities to d1_live_box_candidates.jsonl",
    )
    parser.add_argument(
        "--harvester-candidates-path",
        type=Path,
        default=REPO_ROOT / "data" / "polymarket" / "d1_live_box_candidates.jsonl",
    )
    parser.add_argument("--harvester-dedupe-ttl-sec", type=float, default=45.0)
    parser.add_argument("--harvester-min-velocity-bps-hr", type=float, default=7.5)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "data" / "full_throttle" / "pipeline",
    )
    parser.add_argument(
        "--dashboard-md",
        type=Path,
        default=REPO_ROOT / "FULL_THROTTLE_DASHBOARD.md",
    )
    args = parser.parse_args(argv)

    exec_mode = parse_mode(args.mode)
    gate_cfg = ExecutionModeGateConfig(
        mode=exec_mode,
        jurisdiction_code=args.jurisdiction,
        reconciled_nav_usd=DEFAULT_LIVE_RECONCILED_NAV_USD,
    )
    pipe_cfg = PipelineConfig(
        output_dir=args.output_dir,
        mode_gate=gate_cfg,
        reconciled_nav_usd=DEFAULT_LIVE_RECONCILED_NAV_USD,
        available_liquid_pusd=DEFAULT_LIVE_RECONCILED_NAV_USD,
        max_book_tokens_discovery=args.max_book_tokens_discovery,
        max_book_tokens_fast_cycle=args.max_book_tokens_fast,
        cold_layer_rotation_tokens=args.cold_rotation_tokens,
        max_gamma_pages=args.max_gamma_pages,
        emit_harvester_candidates=bool(args.emit_harvester_candidates),
        harvester_candidates_path=args.harvester_candidates_path,
        harvester_candidate_dedupe_ttl_sec=args.harvester_dedupe_ttl_sec,
        harvester_min_velocity_bps_per_hr=args.harvester_min_velocity_bps_hr,
    )

    if args.cycles is not None:
        eff_sweeps = 1
        eff_fast = max(0, int(args.cycles) - 1)
        eff_research = False
        should_resume = True
    else:
        eff_sweeps = args.discovery_sweeps
        eff_fast = args.fast_cycles
        eff_research = not args.no_research_cycle
        should_resume = bool(args.resume_checkpoint)

    pipeline = FullThrottlePipeline(config=pipe_cfg)
    if should_resume:
        pipeline.load_checkpoint()

    payload = pipeline.run_multi_cycle_campaign(
        discovery_sweeps=eff_sweeps,
        fast_cycles_per_sweep=eff_fast,
        include_research_cycle=eff_research,
        inter_cycle_pause_sec=args.inter_cycle_pause,
    )

    md_path = generate_dashboard_files(
        dashboard_json_path=pipeline.dashboard_json_path,
        markdown_out_path=args.dashboard_md,
    )

    camp = payload["campaign_summary"]
    ucov = payload["section_1_universe_coverage"]
    oppm = payload["section_2_opportunity_metrics"]
    dorm = payload["section_2c_dormant_opportunity_store"]
    mkr = payload.get("section_2d_hedged_maker_shadow_quoter") or {}
    brg = payload.get("section_2e_harvester_candidate_bridge") or {}
    print(
        json.dumps(
            {
                "status": "OK",
                "execution_mode": payload["execution_mode"],
                "cycles_executed": camp["total_cycles_executed"],
                "campaign_wall_time_sec": camp["campaign_wall_time_sec"],
                "peak_rss_mib": camp["peak_rss_mib"],
                "swapless_180mib_budget_ok": camp["swapless_180mib_budget_ok"],
                "observable_events": ucov.get("total_observable_events", 0),
                "observable_markets": ucov.get("total_observable_markets", 0),
                "class_counts": oppm.get("class_counts", {}),
                "active_dormant_opportunities": dorm.get("active_dormant_count", 0),
                "hedged_maker_resting_quotes": mkr.get("resting_passive_quotes_count", 0),
                "harvester_bridge_enabled": bool(brg.get("enabled", False)),
                "harvester_candidates_emitted": brg.get("total_emitted_across_campaign", 0),
                "dashboard_json": str(pipeline.dashboard_json_path),
                "dashboard_markdown": str(md_path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
