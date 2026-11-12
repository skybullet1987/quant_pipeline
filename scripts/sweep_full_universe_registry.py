#!/usr/bin/env python3
"""
CLI Runner for 100% Observable Polymarket Universe Enumeration & Two-Layer Surveillance
(`scripts/sweep_full_universe_registry.py`).

Enumerates 100% of active unclosed events & markets from public Gamma (`/events/keyset`)
and CLOB (`/sampling-markets`) endpoints with zero arbitrary volume, liquidity, category,
fee-regime, or top-N exclusions, persists incremental state to `data/universe/market_registry.sqlite3`
and `data/universe/coverage_snapshot.json`, and executes initial Layer B + Layer A batched
`POST https://clob.polymarket.com/books` surveillance cycles.

Strictly Mode 1 / Mode 2 public read-only (`D-001`, `D-002`, `D-003`, `D-010`).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from src.polymarket_research.full_universe_discovery import (  # noqa: E402
    CLOB_BOOKS_DEFAULT_BATCH_SIZE,
    DEFAULT_COVERAGE_SNAPSHOT_PATH,
    DEFAULT_REGISTRY_DB_PATH,
    DEFAULT_UNIVERSE_DIR,
    FullUniverseRegistry,
    PersistentJsonHttpClient,
    TwoLayerSurveillanceScheduler,
    get_process_rss_mib,
)


def parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sweep 100% of the observable Polymarket Gamma + CLOB universe into SQLite + JSON."
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DEFAULT_REGISTRY_DB_PATH,
        help="Path to SQLite registry database (default: data/universe/market_registry.sqlite3).",
    )
    parser.add_argument(
        "--snapshot-path",
        type=Path,
        default=DEFAULT_COVERAGE_SNAPSHOT_PATH,
        help="Path to JSON coverage snapshot (default: data/universe/coverage_snapshot.json).",
    )
    parser.add_argument(
        "--surveillance-snapshot-path",
        type=Path,
        default=DEFAULT_UNIVERSE_DIR / "surveillance_snapshot.json",
        help="Path to JSON two-layer surveillance cycle report.",
    )
    parser.add_argument(
        "--max-gamma-pages",
        type=int,
        default=None,
        help="Optional page cap for smoke testing (omit for 100%% untruncated full-universe sweep).",
    )
    parser.add_argument(
        "--skip-clob-sampling",
        action="store_true",
        help="Skip CLOB /sampling-markets pagination overlay.",
    )
    parser.add_argument(
        "--surveillance-cycles",
        type=int,
        default=2,
        help="Number of live Layer B + Layer A batched POST /books cycles to run after discovery (default: 2).",
    )
    parser.add_argument(
        "--layer-b-tokens",
        type=int,
        default=1800,
        help="Layer B high-priority adaptive token budget per surveillance cycle (default: 1800).",
    )
    parser.add_argument(
        "--layer-a-tokens",
        type=int,
        default=1350,
        help="Layer A full-universe round-robin token budget per surveillance cycle (default: 1350).",
    )
    parser.add_argument(
        "--clob-batch-size",
        type=int,
        default=CLOB_BOOKS_DEFAULT_BATCH_SIZE,
        help="Tokens per POST /books batch (max 500, default: 450).",
    )
    return parser.parse_args(argv)


def _write_atomic_lf_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".tmp.{os.getpid()}")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def main(argv: List[str] | None = None) -> int:
    args = parse_args(argv)
    t_start = time.time()
    print(
        f"[Dominus Discovery] Starting observable Polymarket universe sweep "
        f"(db={args.db_path}, max_gamma_pages={args.max_gamma_pages or 'UNLIMITED_100PCT'})...",
        flush=True,
    )

    registry = FullUniverseRegistry(db_path=args.db_path, snapshot_path=args.snapshot_path)
    client = PersistentJsonHttpClient()

    def _on_progress(pages: int, events_seen: int, rss_mib: float) -> None:
        if pages == 1 or pages % 100 == 0:
            elapsed = time.time() - t_start
            print(
                f"  [Gamma Keyset] page={pages:3d} | active_events={events_seen:6d} | "
                f"elapsed={elapsed:6.1f}s | peak_rss={rss_mib:5.1f} MiB",
                flush=True,
            )

    try:
        snapshot = registry.sweep_full_universe(
            http_client=client,
            max_gamma_pages=args.max_gamma_pages,
            include_clob_sampling=not args.skip_clob_sampling,
            include_boundary_probes=True,
            progress_callback=_on_progress,
        )

        surveillance_cycles: List[Dict[str, Any]] = []
        if args.surveillance_cycles > 0:
            scheduler = TwoLayerSurveillanceScheduler(
                registry,
                layer_a_tokens_per_cycle=args.layer_a_tokens,
                layer_b_tokens_per_cycle=args.layer_b_tokens,
                clob_batch_size=args.clob_batch_size,
                max_hot_books_cached=2500,
            )
            for cyc in range(args.surveillance_cycles):
                cyc_res = scheduler.execute_poll_cycle(http_client=client)
                surveillance_cycles.append(cyc_res)
                pm = cyc_res["poll_meta"]
                up = cyc_res["registry_updates"]
                print(
                    f"  [Surveillance Cycle {cyc + 1}/{args.surveillance_cycles}] "
                    f"polled={pm['tokens_requested']} tokens in {pm['batches_sent']} batches ({pm['wall_time_sec']:.2f}s) | "
                    f"two_sided={up['two_sided_healthy']} one_sided={up['one_sided_marked']} empty={up['zero_depth_marked']} | "
                    f"rss={cyc_res['rss_mib']:.1f} MiB",
                    flush=True,
                )

            surv_doc = {
                "run_id": snapshot["run_id"],
                "generated_at_utc": snapshot["generated_at_utc"],
                "layer_a_tokens_per_cycle": args.layer_a_tokens,
                "layer_b_tokens_per_cycle": args.layer_b_tokens,
                "clob_batch_size": args.clob_batch_size,
                "cycles": surveillance_cycles,
                "final_staleness_report": surveillance_cycles[-1]["staleness_report"],
                "peak_rss_mib": max(
                    float(snapshot["diff_stats"]["peak_rss_mib"]),
                    max((float(c["rss_mib"]) for c in surveillance_cycles), default=0.0),
                    get_process_rss_mib(),
                ),
            }
            _write_atomic_lf_json(args.surveillance_snapshot_path, surv_doc)
            snapshot["live_surveillance_sample"] = surv_doc
            snapshot["diff_stats"]["peak_rss_mib"] = round(surv_doc["peak_rss_mib"], 2)
            _write_atomic_lf_json(args.snapshot_path, snapshot)

        totals = snapshot["universe_totals"]
        proto = snapshot["protocol_and_instrument_breakdown"]
        v51 = snapshot["existing_dominus_v51_coverage_comparison"]["alpha124_shadow_and_live_harvester_bridge"]
        print("\n=== DOMINUS 100% OBSERVABLE UNIVERSE COVERAGE SUMMARY ===", flush=True)
        print(f"  Active Unclosed Events:           {totals['active_unclosed_events']:,}", flush=True)
        print(f"    - Single Binary Events:         {totals['single_market_binary_events']:,}", flush=True)
        print(f"    - Multi-Market Events:          {totals['multi_market_events']:,}", flush=True)
        print(f"    - NegRisk Events Total:         {proto['negrisk_events_total']:,} "
              f"(Standard={proto['negrisk_standard_closed_slate_events']:,}, "
              f"Augmented/Other/Placeholder={proto['negrisk_augmented_or_other_or_placeholder_events']:,})", flush=True)
        print(f"  All Child Markets in Active Evts: {totals['all_child_markets_in_active_events']:,}", flush=True)
        print(f"  Active Unclosed Markets:          {totals['active_unclosed_markets']:,}", flush=True)
        print(f"  Execution-Eligible Markets:       {totals['execution_eligible_markets']:,} "
              f"(Ineligible retained w/ skip codes={totals['ineligible_active_markets_retained_with_skip_codes']:,})", flush=True)
        print(f"  Tradable Outcome Token IDs:       {totals['tradable_outcome_token_ids']:,}", flush=True)
        print(f"  Fee-Enabled Active Markets:       {proto['fees_enabled_true_active_markets']:,} "
              f"vs Zero-Fee={proto['fees_enabled_false_active_markets']:,}", flush=True)
        print(f"  enableOrderBook=True vs False:    {proto['enable_order_book_true_active_markets']:,} "
              f"vs {proto['enable_order_book_false_active_markets']:,}", flush=True)
        print(f"  CLOB /sampling-markets Active:    {totals['clob_sampling_markets_active']:,}", flush=True)
        print(f"  v5.1 General Discovered Markets:  {v51['general_discovered_markets']:,} "
              f"({v51['general_discovered_markets_pct']:.3f}%)", flush=True)
        print(f"  v5.1 Strategy-Evaluated Markets:  {v51['strategy_evaluated_markets']:,} "
              f"({v51['strategy_evaluated_markets_pct_of_active']:.3f}% of active)", flush=True)
        print(f"  v5.1 Blind/Unmonitored Markets:   {v51['blind_unmonitored_active_markets']:,} "
              f"({v51['blind_unmonitored_active_markets_pct']:.3f}%)", flush=True)
        print(f"  Peak Process RSS:                 {snapshot['diff_stats']['peak_rss_mib']:.2f} MiB (< 120 MiB target)", flush=True)
        print(f"  Total Wall Time:                  {time.time() - t_start:.2f}s", flush=True)
        return 0
    finally:
        client.close()
        registry.close()


if __name__ == "__main__":
    raise SystemExit(main())
