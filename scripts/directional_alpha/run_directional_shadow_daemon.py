#!/usr/bin/env python3
"""
Polymarket Directional Alpha — Forward Shadow Testing Daemon (`Phase 2`)
========================================================================
Runs continuously on `kraken-finland` (`/home/skybullet1987/quant_pipeline`) or in bounded
`--max-cycles N` CLI check mode, evaluating the 7 locked directional alpha sleeves (`#33`)
against real live Polymarket two-sided L2 order books over Finland's native `~48ms` link.

Hard Operational & Safety Invariants (`AGENTS.md` / `D-001` / `D-009` / `D-010`):
  - STRICT RESEARCH ONLY: Zero live orders, zero `.env` loading, `PAA_SIGNING_DISABLED=1`.
  - `PERM_KMIA_D001_PROTECTED_LOCK`: Markets `6707502` & `6707503` are 100% excluded.
  - Swapless Memory Fence (`MemoryHigh=110M`, `MemoryMax=140M`, `MemorySwapMax=0`):
    Bounded SQLite cache (`4 MiB`), bounded `LiveDirectionalSignalSuite` ring-buffers,
    periodic `shadow_book_observations` pruning, and `libc.malloc_trim(0)` every cycle.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import sys
import time
from typing import Any, Dict, List, Optional, Set
import urllib.request

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from directional_alpha.execution_microstructure import resolve_fee_schedule
from directional_alpha.live_shadow_signals import (
    LOCKED_SLEEVE_IDS,
    LiveDirectionalSignalSuite,
    LiveSignalConfig,
)
from directional_alpha.shadow_runner import (
    DEFAULT_SHADOW_DB_PATH,
    DirectionalShadowRunner,
    FROZEN_KMIA_MARKET_IDS,
    OPEN_METEO_HOST,
    ShadowConfig,
    assert_public_readonly_request,
    assert_safe_shadow_db_path,
    measure_process_rss_mib,
    reclaim_unused_heap,
    utc_now_iso,
)

DEFAULT_STATUS_JSON_PATH = REPO_ROOT / "data" / "directional_alpha" / "directional_shadow_status.json"
DEFAULT_PERSISTENT_RUN_ID = "DAEMON_FINLAND_DIRECTIONAL_V1"

# Common Polymarket weather-station coordinates for optional read-only Open-Meteo `forecast_high_c` (`HYP_023`)
# Note: `KMIA` Nov 7 markets (`6707502`, `6707503`) remain strictly blocked by `FROZEN_KMIA_MARKET_IDS` (`D-001`).
WEATHER_STATION_COORDS: Dict[str, tuple[float, float]] = {
    "KLGA": (40.7769, -73.8740),
    "KNYC": (40.7829, -73.9654),
    "KORD": (41.9742, -87.9073),
    "KLAX": (33.9416, -118.4085),
    "KDFW": (32.8998, -97.0403),
    "KATL": (33.6407, -84.4277),
    "KDAL": (32.8471, -96.8518),
    "KSEA": (47.4502, -122.3088),
    "EGLL": (51.4700, -0.4543),
    "EGLC": (51.5048, 0.0495),
    "LFPG": (49.0097, 2.5479),
    "RKSI": (37.4602, 126.4407),
    "RJTT": (35.5494, 139.7798),
    "CYYZ": (43.6777, -79.6248),
    "SAEZ": (-34.8222, -58.5358),
}


def atomic_write_json(target_path: Path, payload: Dict[str, Any]) -> None:
    """Writes JSON atomically via sibling `.tmp` + `os.replace` inside `data/directional_alpha/`."""
    assert_safe_shadow_db_path(target_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target_path.with_suffix(target_path.suffix + f".{os.getpid()}.tmp")
    encoded = (json.dumps(payload, indent=2, sort_keys=False) + "\n").encode("utf-8")
    with open(tmp_path, "wb") as fh:
        fh.write(encoded)
        fh.flush()
    os.replace(tmp_path, target_path)


def _fetch_open_meteo_high_c(lat: float, lon: float) -> Optional[float]:
    url = (
        f"https://{OPEN_METEO_HOST}/v1/forecast"
        f"?latitude={lat:.4f}&longitude={lon:.4f}"
        f"&daily=temperature_2m_max&temperature_unit=celsius&forecast_days=2&timezone=UTC"
    )
    assert_public_readonly_request("GET", url)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "DominusDirectionalShadow/1.0", "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=6.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        maxes = (data.get("daily") or {}).get("temperature_2m_max") or []
        if maxes and maxes[0] is not None:
            return float(maxes[0])
    except Exception:
        return None
    return None


async def refresh_weather_station_forecasts_if_needed(
    suite: LiveDirectionalSignalSuite,
    watchlist: List[Dict[str, Any]],
) -> int:
    """Refreshes read-only Open-Meteo `forecast_high_c` for active weather ICAO stations on watchlist."""
    stations_seen: Set[str] = set()
    for m in watchlist:
        mid = str(m.get("market_id") or "")
        if mid in FROZEN_KMIA_MARKET_IDS:
            continue
        blob = f"{m.get('question', '')} {m.get('slug', '')}".upper()
        for code in WEATHER_STATION_COORDS:
            if code in blob or code.lower() in str(m.get("slug", "")).lower():
                stations_seen.add(code)
    updated = 0
    for code in sorted(stations_seen)[:8]:
        lat, lon = WEATHER_STATION_COORDS[code]
        fc_c = await asyncio.to_thread(_fetch_open_meteo_high_c, lat, lon)
        if fc_c is not None:
            suite.set_weather_forecast(code, fc_c)
            updated += 1
    return updated


def _build_offline_fixture(cycle_offset: int, now_epoch: float) -> tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]], Dict[str, Any]]:
    """Deterministic multi-sleeve offline fixture exercising `LiveDirectionalSignalSuite` + `DirectionalShadowRunner`."""
    end_iso = datetime.fromtimestamp(now_epoch + 86400.0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    watchlist = [
        {
            "market_id": "OFF_POL_NEG_89",
            "condition_id": "0xoff_pol_neg",
            "slug": "will-central-bank-not-cut-rates-in-q4",
            "question": "Will the Central Bank NOT cut rates at the next meeting?",
            "event_id": "EV_OFF_MACRO_1",
            "event_title": "Central Bank Rate Decision",
            "event_market_count": 2,
            "category": "economics",
            "yes_token_id": "tok_off_yes_1",
            "no_token_id": "tok_off_no_1",
            "fee_schedule": resolve_fee_schedule({"feesEnabled": False, "category": "economics"}),
            "fees_enabled": False,
            "fee_type": "zero_fees",
            "neg_risk": False,
            "neg_risk_augmented": False,
            "tick_size": 0.01,
            "liquidity_usd": 85000.0,
            "volume_usd": 240000.0,
            "volume_24h_usd": 35000.0,
            "end_date_iso": end_iso,
            "uma_resolution_status": "open",
            "closed": False,
        },
        {
            "market_id": "OFF_GEO_OBI_ZERO",
            "condition_id": "0xoff_geo_obi",
            "slug": "ceasefire-agreement-signed-before-december",
            "question": "Will a ceasefire framework be signed before December 31?",
            "event_id": "EV_OFF_GEO_2",
            "event_title": "Diplomatic Framework",
            "event_market_count": 1,
            "category": "geopolitics",
            "yes_token_id": "tok_off_yes_2",
            "no_token_id": "tok_off_no_2",
            "fee_schedule": resolve_fee_schedule({"feesEnabled": False, "category": "geopolitics"}),
            "fees_enabled": False,
            "fee_type": "zero_fees",
            "neg_risk": False,
            "neg_risk_augmented": False,
            "tick_size": 0.01,
            "liquidity_usd": 62000.0,
            "volume_usd": 180000.0,
            "volume_24h_usd": 28000.0,
            "end_date_iso": end_iso,
            "uma_resolution_status": "open",
            "closed": False,
        },
        {
            "market_id": "OFF_AUG_CONTENDER",
            "condition_id": "0xoff_aug_cont",
            "slug": "who-will-be-named-next-envoy-candidate-d",
            "question": "Will Candidate D be named the next Special Envoy?",
            "group_item_title": "Candidate D",
            "event_id": "EV_OFF_AUG_3",
            "event_title": "Who will be named the next Special Envoy?",
            "event_market_count": 7,
            "category": "politics",
            "yes_token_id": "tok_off_yes_3",
            "no_token_id": "tok_off_no_3",
            "fee_schedule": resolve_fee_schedule({"feesEnabled": True, "feeType": "politics_fees", "category": "politics"}),
            "fees_enabled": True,
            "fee_type": "politics_fees",
            "neg_risk": True,
            "neg_risk_augmented": True,
            "tick_size": 0.01,
            "liquidity_usd": 45000.0,
            "volume_usd": 95000.0,
            "volume_24h_usd": 14000.0,
            "end_date_iso": end_iso,
            "uma_resolution_status": "open",
            "closed": False,
        },
        {
            # Frozen KMIA market included deliberately to verify strict `D-001` skip invariant
            "market_id": sorted(FROZEN_KMIA_MARKET_IDS)[0],
            "condition_id": "0xkmia_frozen",
            "slug": "highest-temperature-in-miami-on-november-7",
            "question": "Highest temperature in Miami (KMIA) on November 7?",
            "event_id": "EV_KMIA_FROZEN",
            "category": "weather",
            "yes_token_id": "tok_kmia_y",
            "no_token_id": "tok_kmia_n",
            "fee_schedule": resolve_fee_schedule({"feesEnabled": False, "category": "weather"}),
            "fees_enabled": False,
            "tick_size": 0.01,
            "liquidity_usd": 20000.0,
            "volume_usd": 50000.0,
            "uma_resolution_status": "disputed",
            "closed": False,
        },
    ]
    dip = -0.05 if cycle_offset == 0 else 0.01
    books = {
        "OFF_POL_NEG_89": {
            "bids": [{"price": 0.89, "size": 300.0}, {"price": 0.88, "size": 400.0}],
            "asks": [{"price": 0.90, "size": 250.0}, {"price": 0.91, "size": 400.0}],
            "tick_size": 0.01,
        },
        "OFF_GEO_OBI_ZERO": {
            "bids": [
                {"price": round(0.50 + dip, 2), "size": 450.0},
                {"price": round(0.49 + dip, 2), "size": 300.0},
            ],
            "asks": [
                {"price": round(0.51 + dip, 2), "size": 80.0},
                {"price": round(0.52 + dip, 2), "size": 90.0},
            ],
            "tick_size": 0.01,
        },
        "OFF_AUG_CONTENDER": {
            "bids": [{"price": 0.14, "size": 350.0}, {"price": 0.13, "size": 400.0}],
            "asks": [{"price": 0.15, "size": 350.0}, {"price": 0.16, "size": 400.0}],
            "tick_size": 0.01,
        },
    }
    bootstrap_payloads = {
        "OFF_GEO_OBI_ZERO": {
            "history": [
                {"t": now_epoch - 7200.0 + i * 900.0, "p": 0.51}
                for i in range(7)
            ]
        }
    }
    return watchlist, books, bootstrap_payloads


async def run_daemon(args: argparse.Namespace) -> Dict[str, Any]:
    # Enforce zero-signing environment fence
    os.environ["PAA_SIGNING_DISABLED"] = "1"

    db_path = assert_safe_shadow_db_path(Path(args.db_path))
    status_path = assert_safe_shadow_db_path(Path(args.status_path))
    started_utc = utc_now_iso()
    started_mono = time.monotonic()

    continuous_mode = int(args.max_cycles) <= 0 and not bool(args.offline)
    run_id = (
        str(args.run_id).strip()
        if args.run_id
        else (DEFAULT_PERSISTENT_RUN_ID if continuous_mode else None)
    )

    sig_cfg = LiveSignalConfig(
        virtual_bankroll_usd=float(args.bankroll_usd),
        kelly_multiplier=0.25,
        max_event_concentration_pct=0.15,
        min_volume_usd=5000.0,
        max_markets=max(160, int(args.max_markets) * 3),
        max_obs_per_market=64,
        max_events_tracked=250,
        assumed_cycle_interval_sec=max(1.0, float(args.interval_sec)),
    )
    suite = LiveDirectionalSignalSuite(config=sig_cfg)

    runner_cfg = ShadowConfig(
        db_path=db_path,
        starting_virtual_bankroll_usd=float(args.bankroll_usd),
        max_tracked_markets=int(args.max_markets),
        max_l2_levels_per_side=12,
        max_event_concentration_pct=0.15,
        max_open_positions=35,
        max_rss_mib_budget=float(args.max_rss_mib),
        resume_existing=bool(continuous_mode or args.resume),
        persistent_run_id=run_id,
        max_raw_book_obs_rows=180_000,
    )
    runner = DirectionalShadowRunner(config=runner_cfg, strategies=suite.as_strategy_functions())

    stop_event = asyncio.Event()
    stop_signal_name: List[str] = []

    def _handle_stop(sig_num: int, _frame: Any = None) -> None:
        try:
            sname = signal.Signals(sig_num).name
        except Exception:
            sname = str(sig_num)
        stop_signal_name.append(sname)
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handle_stop, int(sig), None)
        except (NotImplementedError, RuntimeError, ValueError):
            # Windows ProactorEventLoop uses `signal.signal` fallback
            try:
                signal.signal(sig, _handle_stop)
            except Exception:
                pass

    bootstrapped_mids: Set[str] = set()
    bootstrap_summary: Dict[str, Any] = {"seeded_markets": 0, "requested_markets": 0, "elapsed_ms": 0.0}
    last_weather_refresh_mono = -99999.0
    weather_stations_updated = 0
    watchlist: List[Dict[str, Any]] = []
    latest_status: Dict[str, Any] = {}
    local_cycles_run = 0

    try:
        if not args.offline:
            watchlist = await runner.discover_live_watchlist(limit=int(args.max_markets))
            bootstrap_summary = await suite.bootstrap_from_clob_prices_history(
                watchlist,
                interval="1d",
                fidelity_min=15,
                concurrency=8,
            )
            bootstrapped_mids.update(str(m["market_id"]) for m in watchlist)
            weather_stations_updated = await refresh_weather_station_forecasts_if_needed(suite, watchlist)
            last_weather_refresh_mono = time.monotonic()
            print(
                f"[{utc_now_iso()}] DirectionalShadowDaemon START run_id={runner.run_id} "
                f"watchlist={len(watchlist)} bootstrapped={bootstrap_summary.get('seeded_markets', 0)} "
                f"weather_stations={weather_stations_updated} rss={measure_process_rss_mib():.2f}MiB",
                flush=True,
            )

        while not stop_event.is_set():
            t_cycle_start = time.monotonic()
            cycle_idx = runner.cycles_completed_offset + local_cycles_run
            cur_epoch = time.time()

            if args.offline:
                base_ep = 1_794_500_000.0 + local_cycles_run * float(args.interval_sec)
                suite.set_clock_epoch(base_ep)
                watchlist, books, off_payloads = _build_offline_fixture(local_cycles_run, base_ep)
                if local_cycles_run == 0:
                    seeded = suite.bootstrap_from_payloads(off_payloads, now_epoch=base_ep - 60.0)
                    bootstrap_summary = {"seeded_markets": seeded, "requested_markets": len(off_payloads), "elapsed_ms": 0.1}
                rtt_ms: Optional[float] = 0.0
                cur_epoch = base_ep
            else:
                refresh_every = max(1, int(args.watchlist_refresh_cycles))
                if local_cycles_run > 0 and (local_cycles_run % refresh_every == 0 or not watchlist):
                    try:
                        watchlist = await runner.discover_live_watchlist(
                            limit=int(args.max_markets),
                            retain_existing=watchlist,
                        )
                        unseeded = [m for m in watchlist if str(m.get("market_id") or "") not in bootstrapped_mids]
                        if unseeded:
                            add_boot = await suite.bootstrap_from_clob_prices_history(
                                unseeded,
                                interval="1d",
                                fidelity_min=15,
                                concurrency=6,
                            )
                            bootstrapped_mids.update(str(m["market_id"]) for m in unseeded)
                            bootstrap_summary["seeded_markets"] = int(bootstrap_summary.get("seeded_markets", 0)) + int(
                                add_boot.get("seeded_markets", 0)
                            )
                    except Exception as exc:
                        print(f"[{utc_now_iso()}] WARN watchlist refresh transient error: {exc!r}", flush=True)

                if (time.monotonic() - last_weather_refresh_mono) >= 1800.0 and watchlist:
                    try:
                        weather_stations_updated = await refresh_weather_station_forecasts_if_needed(suite, watchlist)
                        last_weather_refresh_mono = time.monotonic()
                    except Exception:
                        pass

                try:
                    books, rtt_ms = await runner.fetch_live_books_for_watchlist(watchlist)
                except Exception as exc:
                    print(f"[{utc_now_iso()}] WARN live book fetch transient error: {exc!r}", flush=True)
                    books, rtt_ms = {}, None

            suite.ingest_watchlist_context(watchlist, books_by_market_id=books, now_epoch=cur_epoch)
            summary = runner.step_cycle(cycle_idx, watchlist, books, http_rtt_ms=rtt_ms, now_epoch=cur_epoch)

            # Synchronize UPK bankroll reference with reconciled undisputed mark-to-bid NAV (`D-009`)
            suite.config.virtual_bankroll_usd = max(10.0, float(summary.get("mark_to_bid_nav_usd") or args.bankroll_usd))

            suite_telem = suite.get_sleeve_telemetry()
            latest_status = runner.build_daemon_status_payload(
                summary,
                registered_sleeves=LOCKED_SLEEVE_IDS,
                extra_meta={
                    "daemon_state": "RUNNING",
                    "pid": os.getpid(),
                    "started_at_utc": started_utc,
                    "uptime_sec": round(time.monotonic() - started_mono, 2),
                    "session_cycles_run": local_cycles_run + 1,
                    "poll_interval_sec": float(args.interval_sec),
                    "offline_mode": bool(args.offline),
                    "bootstrap": bootstrap_summary,
                    "weather_stations_forecast_cached": weather_stations_updated,
                    "signal_suite_ring_buffers": {
                        "ring_buffer_markets": suite_telem["ring_buffer_markets"],
                        "total_buffered_observations": suite_telem["total_buffered_observations"],
                        "cold_bootstrapped_markets": suite_telem["cold_bootstrapped_markets"],
                        "tracked_events": suite_telem["tracked_events"],
                        "estimated_suite_buffer_kib": suite_telem["estimated_suite_buffer_kib"],
                    },
                },
            )
            # Enrich `per_sleeve` with evaluation & rejection counters from `LiveDirectionalSignalSuite`
            for sid, s_stats in suite_telem.get("per_sleeve", {}).items():
                entry = latest_status["per_sleeve"].setdefault(sid, {})
                entry["markets_evaluated"] = int(s_stats.get("evaluated", 0))
                entry["rejected_safety_or_liquidity"] = int(s_stats.get("rejected_safety_or_liquidity", 0))
                entry["rejected_edge_or_lot"] = int(s_stats.get("rejected_edge_or_lot", 0))
                entry["signals_emitted"] = max(
                    int(entry.get("signals_emitted", 0)),
                    int(s_stats.get("signals_emitted", 0)),
                )
                entry["last_signal_utc"] = s_stats.get("last_signal_utc")
                entry["last_market_id"] = s_stats.get("last_market_id")

            atomic_write_json(status_path, latest_status)
            reclaim_unused_heap()
            local_cycles_run += 1

            print(
                f"[{utc_now_iso()}] cycle={cycle_idx} books={summary['valid_two_sided_books']}/{summary['markets_polled']} "
                f"orders={summary['orders_submitted']} fills={summary['fills_recorded']} "
                f"open={summary['open_positions']} resting={summary['resting_maker_orders']} "
                f"mtb_nav=${summary['mark_to_bid_nav_usd']:.2f} floor_nav=${summary['guaranteed_floor_nav_usd']:.2f} "
                f"rtt={summary['http_rtt_ms']}ms rss={summary['rss_mib']:.2f}MiB",
                flush=True,
            )

            if int(args.max_cycles) > 0 and local_cycles_run >= int(args.max_cycles):
                break

            elapsed = time.monotonic() - t_cycle_start
            sleep_sec = max(0.2, float(args.interval_sec) - elapsed)
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=sleep_sec)
            except asyncio.TimeoutError:
                pass
    finally:
        if latest_status:
            latest_status["daemon_state"] = (
                f"STOPPED_SIGNAL_{stop_signal_name[-1]}" if stop_signal_name else "COMPLETED_BOUNDED_RUN"
            )
            latest_status["stopped_at_utc"] = utc_now_iso()
            atomic_write_json(status_path, latest_status)
        try:
            runner._conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
            runner._conn.commit()
        except Exception:
            pass
        runner.close(mark_completed=(not continuous_mode))
        reclaim_unused_heap()

    return latest_status


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Polymarket Directional Alpha Read-Only Forward Shadow Daemon")
    ap.add_argument("--bankroll-usd", type=float, default=500.0, help="Starting virtual bankroll USD (default: 500.0)")
    ap.add_argument("--interval-sec", type=float, default=60.0, help="Seconds between live L2 polling cycles (default: 60.0)")
    ap.add_argument("--max-markets", type=int, default=96, help="Max live markets tracked per cycle (default: 96)")
    ap.add_argument("--max-cycles", type=int, default=0, help="0 = run continuously; >0 = run N cycles and exit")
    ap.add_argument("--watchlist-refresh-cycles", type=int, default=10, help="Refresh Gamma watchlist every N cycles")
    ap.add_argument("--max-rss-mib", type=float, default=75.0, help="Target swapless RSS ceiling in MiB (default: 75.0)")
    ap.add_argument("--db-path", type=str, default=str(DEFAULT_SHADOW_DB_PATH), help="SQLite WAL journal path")
    ap.add_argument("--status-path", type=str, default=str(DEFAULT_STATUS_JSON_PATH), help="Atomic JSON status output path")
    ap.add_argument("--run-id", type=str, default="", help="Optional explicit run_id override")
    ap.add_argument("--resume", action="store_true", help="Resume existing persistent run_id if present")
    ap.add_argument("--offline", action="store_true", help="Run deterministic offline multi-sleeve check without network")
    return ap.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    status = asyncio.run(run_daemon(args))
    if args.max_cycles and int(args.max_cycles) > 0:
        print(json.dumps({
            "run_id": status.get("run_id"),
            "cycles_completed": status.get("cycles_completed"),
            "three_nav_d009_metrics": status.get("three_nav_d009_metrics"),
            "memory_fence": status.get("memory_fence"),
            "status_path": str(args.status_path),
        }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
