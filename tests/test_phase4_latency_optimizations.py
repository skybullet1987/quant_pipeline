#!/usr/bin/env python3
"""
Unit & Regression Tests for Phase 4 (Requirement R4 & Section 8) Latency Optimizations.
Compatible with both `python -m unittest` (stdlib-only) and `pytest`.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Install minimal offline module stubs ONLY when running on a stdlib-only Python interpreter.
from scripts.benchmark_polymarket_13stage_latency import (  # noqa: E402
    _install_minimal_offline_stubs_if_needed,
    run_benchmark,
)

_install_minimal_offline_stubs_if_needed()

from src.polymarket_research import net_alpha_opportunity_engine as naoe  # noqa: E402
from src.polymarket_research import polymarket_live_harvester as plh  # noqa: E402


def _make_minimal_harvester(state_path: Path) -> plh.PolymarketLiveHarvester:
    """Constructs a lightweight, side-effect-free harvester instance via `__new__` for isolated unit tests."""
    h = plh.PolymarketLiveHarvester.__new__(plh.PolymarketLiveHarvester)
    h._state_save_lock = threading.RLock()
    h.state_file = state_path
    h.ticket_notional = 12.0
    h.dynamic_sizing = True
    h.max_exposure = 45.0
    h.max_concurrent_positions = 1
    h.risk_config = dict(plh.RISK_CONFIG)
    h.dry_run = True
    h.last_event_id = "EVT_TEST_1"
    h._last_known_collateral = 47.38
    h.high_water_mark_equity = 97.89
    h._current_equity_tier = "RECOVERY"
    h.dynamic_bankroll_pct = 0.22
    h.active_positions = {}
    h.closed_positions = [
        {
            "trade_id": f"T_{i}",
            "asset": "BTC",
            "market_id": "6280100",
            "notional_usd": 12.0,
            "net_pnl_usd": 0.25,
        }
        for i in range(15)
    ]
    h.trades_this_hour = 1
    h.current_hour_window = "2026-11-11T00"
    h.pending_entry_intents = {}
    h.risk_halt = False
    h.reconciliation_required = False
    h.global_halt_reasons = []
    h.redeemed_tx_hashes = []
    h.redeemed_tx_consumed_usd = {}
    h.pre_split_inventory_state = {}
    h.seen_shock_ids = {"SHK_1", "SHK_2"}
    h._seen_shock_order = {"SHK_1": None, "SHK_2": None}
    h._seen_d1_box_order = {"BOX_1": None}
    h._seen_d1_box_ts = {"BOX_1": 1762819200.0}
    h.traded_market_ids = ["6280100"]
    h.trades_per_market = {"6280100": 1}
    h.trades_per_market_direction = {("6280100", "UP"): 1}
    rc = plh.EmergencyRiskController()
    rc.kill_file = state_path.parent / "NO_KILL_SWITCH"
    h.risk_controller = rc
    return h


class _MockOrjson:
    """Deterministic in-memory mock emulating `orjson.dumps` / `orjson.loads` C-extension API."""

    OPT_INDENT_2 = 1

    def __init__(self, fail_dumps: bool = False) -> None:
        self.fail_dumps = fail_dumps
        self.dumps_calls = 0
        self.loads_calls = 0

    def dumps(self, obj: Any, option: int = 0) -> bytes:
        self.dumps_calls += 1
        if self.fail_dumps:
            raise TypeError("Simulated unsupported type for orjson fallback verification")
        if option & self.OPT_INDENT_2:
            return json.dumps(obj, indent=2).encode("utf-8")
        return json.dumps(obj, separators=(",", ":")).encode("utf-8")

    def loads(self, raw: bytes | str) -> Any:
        self.loads_calls += 1
        if isinstance(raw, bytes):
            return json.loads(raw.decode("utf-8"))
        return json.loads(raw)


class TestPhase4LatencyOptimizations(unittest.TestCase):
    def test_save_state_orjson_and_stdlib_fallback_parity(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pm_p4_save_") as tmp:
            tmp_p = Path(tmp)
            st_fast = tmp_p / "state_orjson.json"
            st_std = tmp_p / "state_stdlib.json"

            h_fast = _make_minimal_harvester(st_fast)
            h_std = _make_minimal_harvester(st_std)
            plh.PolymarketLiveHarvester._RISKLESS_SAVE_HELPERS = None

            mock_oj = _MockOrjson(fail_dumps=False)
            with mock.patch.object(plh, "_orjson", mock_oj):
                h_fast.save_state()
                h_fast.save_state()  # exercises cached _RISKLESS_SAVE_HELPERS on 2nd call

            self.assertEqual(mock_oj.dumps_calls, 2)
            self.assertIsNotNone(plh.PolymarketLiveHarvester._RISKLESS_SAVE_HELPERS)

            with mock.patch.object(plh, "_orjson", None):
                h_std.save_state()

            parsed_fast = json.loads(st_fast.read_text(encoding="utf-8"))
            parsed_std = json.loads(st_std.read_text(encoding="utf-8"))
            for doc in (parsed_fast, parsed_std):
                doc.pop("updated_at_utc", None)
                if isinstance(doc.get("ft_live_funnel"), dict):
                    doc["ft_live_funnel"].pop("updated_at_utc", None)
                if isinstance(doc.get("live_riskless_funnel"), dict) and isinstance(
                    doc["live_riskless_funnel"].get("ft_bridge_stats"), dict
                ):
                    doc["live_riskless_funnel"]["ft_bridge_stats"].pop("updated_at_utc", None)
            self.assertEqual(parsed_fast, parsed_std)
            self.assertEqual(parsed_fast["closed_positions_count"], 15)
            self.assertEqual(parsed_fast["live_bankroll"], 47.38)

    def test_save_state_typeerror_graceful_fallback_and_tmp_cleanup(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pm_p4_fb_") as tmp:
            tmp_p = Path(tmp)
            st_file = tmp_p / "state_fb.json"
            h = _make_minimal_harvester(st_file)

            # 1. If _orjson.dumps raises TypeError, save_state must seamlessly fall back to stdlib json.dump
            failing_oj = _MockOrjson(fail_dumps=True)
            with mock.patch.object(plh, "_orjson", failing_oj):
                h.save_state()
            self.assertEqual(failing_oj.dumps_calls, 1)
            self.assertTrue(st_file.exists())
            self.assertEqual(json.loads(st_file.read_text(encoding="utf-8"))["state_version"], "2.0.0")

            # 2. If os.replace fails, PID+TID temp file must be unlinked and StatePersistenceError raised
            with mock.patch("os.replace", side_effect=OSError("simulated_disk_error")):
                with self.assertRaises(plh.StatePersistenceError):
                    h.save_state()
            leftover_tmps = list(tmp_p.glob("*.tmp.*"))
            self.assertEqual(leftover_tmps, [])

    def test_get_verified_shm_book_fast_bytes_and_safety_guards(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pm_p4_shm_") as tmp:
            tmp_p = Path(tmp)
            h = _make_minimal_harvester(tmp_p / "state.json")
            tok_id = "71321045679252212594626385532706912750332728571942532289631379312455583992563"
            shm_file = tmp_p / "pm_fast_tick_BTC.json"
            now_ts = time.time()
            payload = {
                "markets": {
                    "6280100": {
                        "market_id": "6280100",
                        "timestamp_unix": now_ts,
                        "UP": {
                            "token_id": tok_id,
                            "raw_top_bids": [[0.65, 120.0]],
                            "raw_top_asks": [[0.66, 110.0]],
                        },
                    }
                }
            }
            shm_file.write_bytes(json.dumps(payload).encode("utf-8"))

            mock_oj = _MockOrjson()
            with (
                mock.patch.dict(os.environ, {"PM_FAST_TICK_DIR": str(tmp_p)}),
                mock.patch.object(plh, "_json_loads", mock_oj.loads),
            ):
                good_pos = {
                    "asset": "BTC",
                    "market_id": "6280100",
                    "token_id": tok_id,
                    "target_token": "UP",
                }
                bk = h._get_verified_shm_book(good_pos)
                self.assertIsNotNone(bk)
                assert bk is not None
                self.assertEqual(bk["bids"][0]["price"], "0.65")
                self.assertEqual(mock_oj.loads_calls, 1)

                # Token mismatch must fail closed
                bad_tok_pos = dict(good_pos, token_id="99999999999999999999999")
                self.assertIsNone(h._get_verified_shm_book(bad_tok_pos))

                # Stale (>1.5s) snapshot must fail closed
                payload["markets"]["6280100"]["timestamp_unix"] = now_ts - 5.0
                shm_file.write_bytes(json.dumps(payload).encode("utf-8"))
                self.assertIsNone(h._get_verified_shm_book(good_pos))

    def test_global_positions_shm_multithread_and_orjson_parity(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pm_p4_bus_") as tmp:
            tmp_p = Path(tmp)
            mock_oj = _MockOrjson()
            with mock.patch.dict(os.environ, {"PM_FAST_TICK_DIR": str(tmp_p)}):
                # 1. Test with mock _orjson enabled
                with mock.patch.object(naoe, "_orjson", mock_oj):
                    ok = naoe.publish_global_positions_shm(
                        "live_harvester",
                        [
                            {
                                "trade_id": "P1",
                                "sleeve": "SINGLE_LEG_LOCK",
                                "asset": "BTC",
                                "target_token": "UP",
                                "candle_open_spot": 95000.0,
                                "candle_expiry_ts": time.time() + 300,
                                "notional_usd": 12.0,
                            }
                        ],
                    )
                    self.assertTrue(ok)
                    snap = naoe.read_global_positions_shm(max_age_sec=60.0)
                    self.assertIn("live_harvester", snap["daemons"])
                    self.assertEqual(snap["daemons"]["live_harvester"]["positions"][0]["id"], "P1")
                    self.assertGreaterEqual(mock_oj.dumps_calls, 1)
                    self.assertGreaterEqual(mock_oj.loads_calls, 1)

                # 2. Test concurrent multi-thread safety (PID+TID temp path) with stdlib fallback
                errors: List[Exception] = []

                def _worker(tid_idx: int) -> None:
                    try:
                        for j in range(15):
                            naoe.publish_global_positions_shm(
                                f"daemon_{tid_idx}",
                                [{"trade_id": f"T_{tid_idx}_{j}", "asset": "ETH", "notional_usd": 10.0}],
                            )
                            _ = naoe.read_global_positions_shm(max_age_sec=60.0)
                    except Exception as exc:  # pragma: no cover
                        errors.append(exc)

                with mock.patch.object(naoe, "_orjson", None):
                    threads = [threading.Thread(target=_worker, args=(i,)) for i in range(6)]
                    for t in threads:
                        t.start()
                    for t in threads:
                        t.join()

                self.assertEqual(errors, [])
                self.assertEqual(list(tmp_p.glob("*.tmp")), [])
                final_snap = naoe.read_global_positions_shm(max_age_sec=60.0)
                self.assertGreaterEqual(len(final_snap["daemons"]), 1)

    def test_13stage_benchmark_offline_smoke_and_telemetry_parser(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pm_p4_bench_") as tmp:
            ddir = Path(tmp)
            # Populate synthetic historical telemetry fixtures
            (ddir / "live_shock_triggers.jsonl").write_text(
                json.dumps({"t0_unix": 1762819200.125, "exchange_event_ts_ms": 1762819200124.0}) + "\n",
                encoding="utf-8",
            )
            (ddir / "latency_trace.jsonl").write_text(
                json.dumps(
                    {
                        "clob_http_post_ms": 262.3,
                        "sign_ms": 0.27,
                        "thread_hop_ms": 0.0,
                        "qualify_ms": 0.37,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (ddir / "shock_attempt_forensics.jsonl").write_text(
                json.dumps({"http_ms": 71.5, "e2e_ms": 72.1, "ttl_ms": 12000.0}) + "\n",
                encoding="utf-8",
            )
            (ddir / "live_orders.jsonl").write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "mode": "LIVE_MAKER_ENTRY",
                                "latency_ms": 69.8,
                                "details": {"post_ms": 69.1, "sign_ms": 0.65},
                            }
                        ),
                        json.dumps(
                            {
                                "mode": "LIVE_CLOB",
                                "latency_ms": 270.5,
                                "details": {
                                    "latency_telemetry": {
                                        "clob_http_post_ms": 261.0,
                                        "sign_ms": 0.25,
                                        "thread_hop_ms": 1.2,
                                    }
                                },
                            }
                        ),
                        json.dumps({"mode": "FAK_KILLED_NO_MATCH", "latency_ms": 310.0, "details": {}}),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            res: Dict[str, Any] = run_benchmark(iters=15, skip_network=True, data_dir=ddir)
            for key in (
                "stage3_json_us",
                "stage4_book_us",
                "stage5_signal_us",
                "stage6_strategy_us",
                "stage7_risk_cpu_us",
                "stage8_payload_us",
                "stage9_signing_us",
                "stage10_network_ms",
                "stage13_save_state",
            ):
                self.assertIn(key, res)
            self.assertTrue(res["stage10_network_ms"]["skipped"])
            ack = res["historical"]["live_orders_ack_ms"]
            self.assertEqual(ack["maker_post_only_ack_ms"]["n"], 1)
            self.assertEqual(ack["taker_clob_http_post_ack_ms"]["n"], 1)
            self.assertEqual(ack["taker_post_ack_fill_confirm_ms"]["n"], 1)
            self.assertAlmostEqual(ack["taker_post_ack_fill_confirm_ms"]["p50"], 9.25, places=2)


if __name__ == "__main__":
    unittest.main()
