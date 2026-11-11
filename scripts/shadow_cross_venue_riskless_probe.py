#!/usr/bin/env python3
"""
CLI Runner for Dominus Stage G Read-Only Multi-Venue Pure-Riskless Shadow Probe
(`scripts/shadow_cross_venue_riskless_probe.py`).

Strictly READ-ONLY (`0` private keys, `0` order-submission endpoints).
Probes live `Polymarket` + `Predict.fun` + `SX Bet` (`OBv3`) + `Limitless Exchange` (`Base`)
ONLY when authorized under `P0 Gate 0`, supports 100% network-disabled offline integration
verification (`--network-disabled` / `DOMINUS_NETWORK_MODE=offline`), enforces all 5 Programmatic
Double-Zero Verification Gates, simulates post-latency (`RTT + takerDelayMs`) and queue-ahead
fills honestly, and writes:
  - `data/cross_venue_shadow/cross_venue_funnel.jsonl`
  - `data/cross_venue_shadow/shadow_graduation_report.json`
  - `data/cross_venue_shadow/shadow_service_health.json`
"""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import asdict
import json
import logging
import os
from pathlib import Path
import signal
import sys
import time
from typing import Any, Dict, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.polymarket_research.cross_venue_connectors import (
    EXTENDED_SHADOW_VENUES,
    evaluate_extended_venues_authorization,
    hot_reload_extended_venue_collector,
)
from src.polymarket_research.cross_venue_riskless_shadow import (
    DEFAULT_RELAY_BRIDGE_DRAG_BPS,
    HonestCrossVenueShadowEngine,
    LiveCrossVenueShadowCollector,
)
from src.polymarket_research.cross_venue_shadow_deployment_gates import (
    ALLOWED_SHADOW_ENV_KEYS,
    EX_CONFIG,
    ShadowEnvValidationReport,
    run_offline_shadow_cycle,
    validate_python_runtime_dependencies,
    validate_shadow_env_dict,
    validate_shadow_env_file,
    validate_systemd_unit_text,
    write_shadow_health_snapshot,
)

logger = logging.getLogger("DominusCrossVenueShadow")


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Dominus Stage G Read-Only Multi-Venue Pure-Riskless Shadow Probe (Predict.fun + SX Bet + Limitless <-> Polymarket)"
    )
    ap.add_argument("--once", action="store_true", help="Run a single read-only scan cycle and exit.")
    ap.add_argument("--cycles", type=int, default=0, help="Stop after N cycles (0 = run continuously until SIGINT/SIGTERM).")
    ap.add_argument("--interval-sec", type=float, default=15.0, help="Seconds between scan cycles (default: 15.0).")
    ap.add_argument("--clip-usd", type=float, default=25.0, help="Virtual arbitrage clip notional in USD (default: 25.0).")
    ap.add_argument(
        "--bridge-drag-bps",
        type=float,
        default=DEFAULT_RELAY_BRIDGE_DRAG_BPS,
        help="Amortized Relay.link cross-L2 rebalance drag in bps (default: 2.75).",
    )
    ap.add_argument(
        "--limitless-pages",
        type=int,
        default=12,
        help="Number of Limitless `/markets/active?limit=25` pages to scan per cycle (default: 12 = up to 300 markets).",
    )
    ap.add_argument(
        "--limitless-orderbook-top-n",
        type=int,
        default=48,
        help="Number of prioritized Limitless CLOB markets to hydrate/stream L2 orderbooks for (default: 48).",
    )
    ap.add_argument(
        "--predict-testnet-smoke",
        action="store_true",
        help="Also smoke-test Predict.fun schema against public `api-testnet.predict.fun` when PREDICT_FUN_API_KEY is unset.",
    )
    ap.add_argument(
        "--data-dir",
        type=str,
        default=str(REPO_ROOT / "data" / "cross_venue_shadow"),
        help="Telemetry output directory for JSONL funnel, graduation report & health snapshot.",
    )
    ap.add_argument(
        "--env-file",
        type=str,
        default="",
        help="Optional `.env` file path (e.g. `/etc/polymarket-shadow.env`) validated before startup.",
    )
    ap.add_argument(
        "--allow-missing-env-file",
        action="store_true",
        help="Continue using process environment if `--env-file` does not exist on disk.",
    )
    ap.add_argument(
        "--enforce-venue-auth",
        action="store_true",
        help="Enforce per-venue P0 Gate 0 authorization gates before any outbound network poll.",
    )
    ap.add_argument(
        "--network-disabled",
        action="store_true",
        help="Run in 100%% network-disabled offline mode using recorded-schema multi-venue L2 fixtures.",
    )
    ap.add_argument(
        "--validate-config-only",
        action="store_true",
        help="Validate systemd unit, Python runtime dependencies, env schema, and P0 Gate 0 matrix, then exit.",
    )
    ap.add_argument(
        "--watchdog-check",
        action="store_true",
        help="Verify health snapshot freshness, SQLite WAL store integrity, and resource state, then exit.",
    )
    ap.add_argument(
        "--campaign-summary",
        action="store_true",
        help="Print 1h/24h/7d/14d continuous campaign telemetry summaries from SQLite WAL and exit.",
    )
    ap.add_argument(
        "--certification-status",
        action="store_true",
        help="Print per-venue 168-hour live shadow certification status from SQLite WAL and exit.",
    )
    ap.add_argument(
        "--blocker-registry",
        action="store_true",
        help="Print persistent blocker registry JSON state from SQLite WAL and exit.",
    )
    ap.add_argument(
        "--restriction-registry",
        action="store_true",
        help="Sync and print machine-readable restriction transparency registry JSON and exit.",
    )
    ap.add_argument(
        "--verify-bankroll-gates",
        action="store_true",
        help="Verify all 8 roadmap bankroll gates ($88..$525) against observed equity & settlements and exit.",
    )
    ap.add_argument("--live-equity-usd", type=float, default=77.559031, help="Observed live account equity USD for gate audit.")
    ap.add_argument("--settled-trades", type=int, default=0, help="Observed live settled trade count for gate audit.")
    ap.add_argument("--json", action="store_true", help="Print full cycle/validation JSON summary to stdout.")
    return ap.parse_args(argv)


def _load_and_validate_env(args: argparse.Namespace) -> tuple[Dict[str, str], ShadowEnvValidationReport]:
    merged_env: Dict[str, str] = {
        k: v for k, v in os.environ.items()
        if k.startswith("DOMINUS_") or k in ALLOWED_SHADOW_ENV_KEYS
    }
    if args.env_file:
        env_path = Path(args.env_file)
        if env_path.exists() or not args.allow_missing_env_file:
            file_map, rep = validate_shadow_env_file(env_path)
            if rep.valid:
                merged_env.update(file_map)
                for k, v in file_map.items():
                    os.environ.setdefault(k, v)
            return merged_env, rep
    rep = validate_shadow_env_dict(merged_env, checked_path=args.env_file or None)
    return merged_env, rep


def _print_cycle_summary(summary: Dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(summary, indent=2))
        return
    rep = summary["graduation_report"]
    vh = rep["venue_health"]
    mode_tag = summary.get("network_mode", "live")
    print(
        f"[Cycle {summary['cycle']} | mode={mode_tag}] "
        f"Poly={vh.get('polymarket', {}).get('markets_parsed', 0)} "
        f"({vh.get('polymarket', {}).get('status', 'NA')}) | "
        f"Limitless={vh.get('limitless', {}).get('markets_parsed', 0)} "
        f"({vh.get('limitless', {}).get('status', 'NA')}) | "
        f"SXBet={vh.get('sx_bet', {}).get('markets_parsed', 0)} "
        f"({vh.get('sx_bet', {}).get('status', 'NA')}) | "
        f"PredictFun={vh.get('predict_fun', {}).get('status', 'NA')} "
        f"({vh.get('predict_fun', {}).get('markets_parsed', 0)}) | "
        f"Derive={vh.get('derive_xyz', {}).get('markets_parsed', 0)} "
        f"({vh.get('derive_xyz', {}).get('status', 'NA')}) | "
        f"Probable={vh.get('probable_markets', {}).get('markets_parsed', 0)} "
        f"({vh.get('probable_markets', {}).get('status', 'NA')}) | "
        f"ForecastEx={vh.get('forecastex', {}).get('markets_parsed', 0)} "
        f"({vh.get('forecastex', {}).get('status', 'NA')}) | "
        f"STX={vh.get('stx_ontario', {}).get('markets_parsed', 0)} "
        f"({vh.get('stx_ontario', {}).get('status', 'NA')}) | "
        f"MatchedPairs={summary['matched_cross_venue_pairs']} | "
        f"MultiLeg={summary.get('multi_leg_complete_baskets_found', 0)} | "
        f"GrossSeen={rep['gross_candidates_seen']} | "
        f"RuleRejects={rep['rule_gate_rejections']} | "
        f"ExecL2={rep['executable_net_l2_count']} | "
        f"Locked={rep['locked_complete_baskets']} | "
        f"NetShadowPnL=${rep['total_realized_shadow_net_pnl_usd']:.4f}"
    )
    for p in summary.get("matched_pair_Previews", [])[:5]:
        pa = p["poly_yes_ask"]
        na = p["poly_no_ask"]
        eya = p["ext_yes_ask"]
        ena = p["ext_no_ask"]
        box_1 = round(pa + ena, 4) if (pa is not None and ena is not None) else None
        box_2 = round(na + eya, 4) if (na is not None and eya is not None) else None
        print(
            f"   -> Pair [{p['external_venue']}] {p['polymarket']} <-> {p['external_slug']} "
            f"(oracles={p['oracle_a']}/{p['oracle_b']}) | "
            f"PolyYES+ExtNO={box_1} | PolyNO+ExtYES={box_2}"
        )


async def main_async(args: argparse.Namespace) -> int:
    env_map, env_report = _load_and_validate_env(args)
    unit_path = REPO_ROOT / "systemd" / "polymarket-cross-venue-shadow.service"
    unit_report = (
        validate_systemd_unit_text(unit_path.read_text(encoding="utf-8"), str(unit_path))
        if unit_path.exists()
        else None
    )
    dep_report = validate_python_runtime_dependencies()

    effective_mode = (
        "offline"
        if (args.network_disabled or env_map.get("DOMINUS_NETWORK_MODE", "").strip().lower() == "offline")
        else (env_map.get("DOMINUS_NETWORK_MODE", "live_public").strip().lower() or "live_public")
    )
    auth_decisions = evaluate_extended_venues_authorization(env_map, network_mode_override=effective_mode)

    if args.validate_config_only:
        all_ok = bool(env_report.valid and dep_report["stdlib_ready"] and (unit_report is None or unit_report.valid))
        payload = {
            "config_valid": all_ok,
            "effective_network_mode": effective_mode,
            "python_dependencies": dep_report,
            "systemd_unit": asdict(unit_report) if unit_report is not None else None,
            "env_validation": asdict(env_report),
            "venue_authorization": {k: asdict(v) for k, v in auth_decisions.items()},
        }
        print(json.dumps(payload, indent=2))
        return 0 if all_ok else EX_CONFIG

    if not env_report.valid:
        logger.error("Shadow environment validation failed (aborting fail-closed): %s", env_report.errors)
        return EX_CONFIG

    data_dir = Path(args.data_dir)
    if args.certification_status:
        from src.polymarket_research.cross_venue_unblock_and_certification import VenueCertificationTracker

        tracker = VenueCertificationTracker(data_dir)
        print(json.dumps(tracker.build_certification_report(auth_decisions=auth_decisions), indent=2))
        return 0

    if args.blocker_registry:
        from src.polymarket_research.cross_venue_unblock_and_certification import PersistentBlockerRegistry

        reg = PersistentBlockerRegistry(data_dir)
        print(json.dumps(reg.sync_from_runtime_state(env=env_map, auth_decisions=auth_decisions), indent=2))
        return 0

    if args.restriction_registry:
        from src.polymarket_research.cross_venue_unblock_and_certification import RestrictionRegistry

        rreg = RestrictionRegistry(data_dir)
        print(json.dumps(rreg.sync_and_persist(env=env_map, auth_decisions=auth_decisions), indent=2))
        return 0

    if args.verify_bankroll_gates:
        from src.polymarket_research.cross_venue_unblock_and_certification import (
            BankrollMilestoneVerifier,
            VenueCertificationTracker,
        )

        tracker = VenueCertificationTracker(data_dir)
        cert_rep = tracker.build_certification_report(auth_decisions=auth_decisions)
        auth_live = [v for v, d in auth_decisions.items() if d.effective_authorized and effective_mode != "offline"]
        res = BankrollMilestoneVerifier.verify_gates(
            total_account_equity_usd=float(args.live_equity_usd),
            settled_live_trades=int(args.settled_trades),
            accounting_discrepancy_usd=0.0,
            riskless_only_mode=True,
            certified_168h_venues=cert_rep.get("certified_venues", []),
            p0_authorized_live_venues=auth_live,
            output_path=data_dir / "bankroll_gate_verification.json",
        )
        print(json.dumps(res, indent=2))
        return 0

    if args.campaign_summary:
        from src.polymarket_research.cross_venue_telemetry_and_watchdog import ShadowTelemetryStore

        store = ShadowTelemetryStore(data_dir)
        try:
            print(json.dumps(store.build_campaign_window_summaries(), indent=2))
        finally:
            store.close()
        return 0

    if args.watchdog_check:
        from src.polymarket_research.cross_venue_telemetry_and_watchdog import ShadowTelemetryStore, get_process_rss_mb

        health_path = data_dir / "shadow_service_health.json"
        store = ShadowTelemetryStore(data_dir)
        try:
            _, reconciled = store.load_or_reconcile_engine_checkpoint()
            fresh_ok = False
            service_ok = False
            age_sec: Optional[float] = None
            if health_path.exists():
                hdata = json.loads(health_path.read_text(encoding="utf-8"))
                age_sec = round(max(0.0, time.time() - float(hdata.get("checked_at_unix", 0.0))), 2)
                fresh_ok = age_sec <= max(180.0, float(args.interval_sec) * 8.0)
                service_ok = bool(hdata.get("service_healthy", False))
            ok = bool(fresh_ok and service_ok)
            if not ok:
                store.emit_alert(
                    "EXTERNAL_WATCHDOG_CHECK_FAILED",
                    "WARNING",
                    f"fresh_ok={fresh_ok} service_ok={service_ok} age_sec={age_sec}",
                )
            out_wd = {
                "watchdog_ok": ok,
                "health_file_exists": health_path.exists(),
                "snapshot_age_sec": age_sec,
                "reconciled_corrupt_checkpoint": reconciled,
                "probe_rss_mb": get_process_rss_mb(),
            }
            print(json.dumps(out_wd, indent=2))
            return 0 if ok else 1
        finally:
            store.close()

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    added_loop_sigs: list[Any] = []
    prev_sig_handlers: Dict[Any, Any] = {}

    def _request_stop(*_: Any) -> None:
        try:
            loop.call_soon_threadsafe(stop_event.set)
        except RuntimeError:
            stop_event.set()

    for sig_name in ("SIGINT", "SIGTERM"):
        sig = getattr(signal, sig_name, None)
        if sig is not None:
            try:
                loop.add_signal_handler(sig, stop_event.set)
                added_loop_sigs.append(sig)
            except (NotImplementedError, RuntimeError, ValueError):
                try:
                    prev_sig_handlers[sig] = signal.getsignal(sig)
                    signal.signal(sig, _request_stop)
                except (ValueError, OSError):
                    pass

    engine = HonestCrossVenueShadowEngine(
        clip_notional_usd=args.clip_usd,
        bridge_drag_bps=args.bridge_drag_bps,
        data_dir=data_dir,
    )
    collector: Optional[LiveCrossVenueShadowCollector] = None

    try:
        authorized_live_venues: Optional[set[str]] = None
        blocked_reasons: Dict[str, str] = {}
        if effective_mode != "offline" and args.enforce_venue_auth:
            authorized_live_venues = {
                v for v in EXTENDED_SHADOW_VENUES if auth_decisions[v].effective_authorized
            }
            blocked_reasons = {
                v: auth_decisions[v].status_code
                for v in EXTENDED_SHADOW_VENUES
                if not auth_decisions[v].effective_authorized
            }
            if not authorized_live_venues:
                for v_blk, code in blocked_reasons.items():
                    engine.venue_health[v_blk] = {"status": "AUTH_BLOCKED", "markets_parsed": 0, "reason": code}
                rep = engine.build_graduation_report()
                write_shadow_health_snapshot(
                    engine.data_dir,
                    network_mode=effective_mode,
                    report=rep,
                    auth_decisions=auth_decisions,
                    env_report=env_report,
                )
                logger.error(
                    "P0 Gate 0 fail-closed halt: 0 live shadow venues authorized (%s). Exiting %d.",
                    blocked_reasons,
                    EX_CONFIG,
                )
                return EX_CONFIG

        collector = LiveCrossVenueShadowCollector(
            engine,
            limitless_pages=args.limitless_pages,
            limitless_orderbook_top_n=args.limitless_orderbook_top_n,
            predict_testnet_smoke=args.predict_testnet_smoke,
            authorized_venues=authorized_live_venues,
            blocked_venue_reasons=blocked_reasons,
            env=env_map,
        )

        target_cycles = 1 if args.once else max(0, int(args.cycles))
        cycle_idx = 0
        consecutive_errors = 0
        last_env_mtime: Optional[float] = (
            Path(args.env_file).stat().st_mtime
            if (args.env_file and Path(args.env_file).exists())
            else None
        )

        if effective_mode != "offline":
            write_shadow_health_snapshot(
                engine.data_dir,
                network_mode=effective_mode,
                report=engine.build_graduation_report(),
                auth_decisions=auth_decisions,
                env_report=env_report,
            )

        while not stop_event.is_set():
            cycle_idx += 1
            try:
                # Single-collector hot-reload when `/etc/polymarket-shadow.env` mtime changes on disk
                if args.env_file and Path(args.env_file).exists():
                    cur_mtime = Path(args.env_file).stat().st_mtime
                    if last_env_mtime is not None and cur_mtime > last_env_mtime:
                        new_map, new_rep = _load_and_validate_env(args)
                        if new_rep.valid:
                            last_env_mtime = cur_mtime
                            new_auth = evaluate_extended_venues_authorization(new_map, network_mode_override=effective_mode)
                            for v_chk in EXTENDED_SHADOW_VENUES:
                                if new_auth[v_chk] != auth_decisions.get(v_chk):
                                    hot_reload_extended_venue_collector(collector, v_chk, new_map)
                            env_map = new_map
                            env_report = new_rep
                            auth_decisions = new_auth
                if effective_mode == "offline":
                    summary = run_offline_shadow_cycle(
                        engine,
                        auth_decisions=auth_decisions,
                        env_report=env_report,
                    )
                    try:
                        from src.polymarket_research.riskless_expansion_v6_engines import write_v6_offline_telemetry_snapshot

                        summary["v6_expansion"] = write_v6_offline_telemetry_snapshot(
                            engine.data_dir, cycles_completed=engine.cycles_completed
                        )
                    except Exception:
                        pass
                    collector.certification_tracker.record_cycle_observation(
                        connector_snapshots=engine.venue_health,
                        network_mode="offline",
                        cycle_interval_sec=float(args.interval_sec),
                    )
                    summary["certification"] = collector.certification_tracker.build_certification_report(
                        auth_decisions=auth_decisions
                    )
                    summary["blocker_registry"] = collector.blocker_registry.sync_from_runtime_state(
                        env=env_map,
                        auth_decisions=auth_decisions,
                    )
                else:
                    async def _mid_cycle_heartbeat() -> None:
                        # Refresh `shadow_service_health.json` every 30s during long multi-venue HTTP/SQLite cycles
                        # (capped at 10 heartbeats = 300s so genuinely hung event-loop/IO tasks still trigger watchdog!)
                        for _ in range(10):
                            await asyncio.sleep(30.0)
                            op_snaps = {v: collector.connectors[v].snapshot for v in collector.ALL_VENUES}
                            write_shadow_health_snapshot(
                                engine.data_dir,
                                network_mode=effective_mode,
                                report=engine.build_graduation_report(),
                                auth_decisions=auth_decisions,
                                env_report=env_report,
                                connector_snapshots=op_snaps,
                            )

                    cycle_task = asyncio.create_task(
                        asyncio.wait_for(collector.run_single_cycle(), timeout=600.0),
                        name=f"shadow-cycle-{cycle_idx}",
                    )
                    hb_task = asyncio.create_task(_mid_cycle_heartbeat(), name=f"shadow-hb-{cycle_idx}")
                    stop_task = asyncio.create_task(stop_event.wait(), name="shadow-stop-wait")
                    done, pending = await asyncio.wait({cycle_task, stop_task}, return_when=asyncio.FIRST_COMPLETED)
                    hb_task.cancel()
                    for p_t in pending:
                        p_t.cancel()
                    await asyncio.gather(hb_task, return_exceptions=True)
                    if stop_task in done and cycle_task not in done:
                        try:
                            await asyncio.wait_for(cycle_task, timeout=2.0)
                        except (asyncio.CancelledError, asyncio.TimeoutError, Exception):
                            pass
                        break
                    await asyncio.gather(*pending, return_exceptions=True)
                    summary = cycle_task.result()
                    summary["network_mode"] = effective_mode
                    rep_obj = engine.build_graduation_report()
                    hp = write_shadow_health_snapshot(
                        engine.data_dir,
                        network_mode=effective_mode,
                        report=rep_obj,
                        auth_decisions=auth_decisions,
                        env_report=env_report,
                        watchdog_status=summary.get("watchdog"),
                        campaign_windows=summary.get("campaign_windows"),
                        connector_snapshots=summary.get("connector_states"),
                    )
                    summary["health_snapshot_path"] = str(hp)
                consecutive_errors = 0
                _print_cycle_summary(summary, as_json=bool(args.json))
            except Exception as exc:
                consecutive_errors += 1
                logger.exception("Shadow scan cycle %d error (#%d consecutive): %s", cycle_idx, consecutive_errors, exc)
                if args.once:
                    return 1

            if target_cycles > 0 and cycle_idx >= target_cycles:
                break

            try:
                await asyncio.wait_for(stop_event.wait(), timeout=max(2.0, float(args.interval_sec)))
            except asyncio.TimeoutError:
                pass

        return 0
    finally:
        for sig_added in added_loop_sigs:
            try:
                loop.remove_signal_handler(sig_added)
            except (NotImplementedError, RuntimeError, ValueError):
                pass
        for sig_obj, prev_h in prev_sig_handlers.items():
            try:
                signal.signal(sig_obj, prev_h)
            except (ValueError, OSError, TypeError):
                pass
        if collector is not None:
            await collector.aclose()
        if engine.telemetry_store is not None:
            engine.telemetry_store.close()


def main(argv: Optional[list[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = parse_args(argv)
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
