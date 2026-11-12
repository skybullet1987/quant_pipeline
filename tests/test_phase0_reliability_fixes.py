"""
Dedicated Regression Suite for DOMINUS v5.0 Phase 0 Reliability & Accounting Remediations
(`tests/test_phase0_reliability_fixes.py`).

Covers:
  - `F-01` (HIGH): Bounded memory, Gamma payload slimming, L2 depth caps, TTL eviction,
    and glibc `malloc_trim` hooks in `Alpha124ShadowDaemon` and `PolymarketDualFeed1HRecorder`.
  - `F-02` (MEDIUM): Worst-case guaranteed redemption floor (`$0.00` valuation) for
    UMA-disputed single-leg locks (`WS_SNIPE_*` / `SINGLE_LEG_LOCK`) and unhedged residuals
    in both `scripts/polymarket_daily_projections.py` and `scripts/dominus_command_center.py`,
    while keeping book equity (`$97.89`) and mark-to-bid NAV (`$47.52`) distinct.
  - `F-06` (LOW): Scoped `pytest.ini` discovery (`testpaths = tests`, `norecursedirs` isolation).
"""

from __future__ import annotations

import ast
import asyncio
import configparser
import json
import sys
import unittest
from pathlib import Path
from typing import Any, Callable, Dict

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import scripts.dominus_command_center as dcc
import scripts.polymarket_daily_projections as dp
import src.polymarket_research.alpha_124_shadow_daemon as a124_mod
import src.polymarket_research.polymarket_terminal_recorder as rec_mod


def _load_cc_valuations_fn() -> Callable[..., Any]:
    """Extracts and compiles the exact `_compute_cc_valuations` AST node from `REMOTE_PROBE_PY`."""
    tree = ast.parse(dcc.REMOTE_PROBE_PY, filename="<REMOTE_PROBE_PY>")
    target_fn = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_compute_cc_valuations":
            target_fn = node
            break
    if target_fn is None:
        raise AssertionError("_compute_cc_valuations not found in dominus_command_center.REMOTE_PROBE_PY")
    mod = ast.Module(body=[target_fn], type_ignores=[])
    ast.fix_missing_locations(mod)
    ns: Dict[str, Any] = {}
    exec(compile(mod, "<REMOTE_PROBE_PY:_compute_cc_valuations>", "exec"), ns)
    return ns["_compute_cc_valuations"]


def _build_kmia_disputed_state() -> Dict[str, Any]:
    """Constructs the exact 4-position disputed `KMIA` live state snapshot (`$47.38` cash, `$50.51` cost)."""
    return {
        "bankroll": 47.377122,
        "live_bankroll": 47.377122,
        "total_account_equity": 97.887122,
        "high_water_mark_equity": 161.3413,
        "pending_entry_intents": {},
        "active_positions": {
            "WS_SNIPE_Miami_KMIA_242960": {
                "trade_id": "WS_SNIPE_Miami_KMIA_242960",
                "market_id": "6707503",
                "box_type": "SINGLE_LEG_LOCK",
                "is_single_leg_lock": True,
                "is_dominance_box": False,
                "notional_usd": 19.54,
                "remaining_cost_basis": 19.54,
                "entry_shares": 20.0,
                "remaining_shares": 20.0,
                "umaResolutionStatus": "disputed",
                "exit_order_id": None,
                "unwind_order_id": None,
            },
            "MULTI_LEG_BUNDLE_LIVE_KMIA_1794113999_318559_UNWRESID_20116898_1794111898": {
                "trade_id": "MULTI_LEG_BUNDLE_LIVE_KMIA_1794113999_318559_UNWRESID_20116898_1794111898",
                "market_id": "6707502",
                "box_type": "MULTI_LEG_RESIDUAL",
                "is_legged_out_residual": True,
                "is_dominance_box": False,
                "notional_usd": 16.32,
                "remaining_cost_basis": 16.32,
                "entry_shares": 17.0,
                "remaining_shares": 17.0,
                "umaResolutionStatus": "disputed",
                "exit_order_id": None,
                "unwind_order_id": None,
            },
            "WS_SNIPE_Miami_KMIA_688670": {
                "trade_id": "WS_SNIPE_Miami_KMIA_688670",
                "market_id": "6707503",
                "box_type": "SINGLE_LEG_LOCK",
                "is_single_leg_lock": True,
                "is_dominance_box": False,
                "notional_usd": 9.77,
                "remaining_cost_basis": 9.77,
                "entry_shares": 10.0,
                "remaining_shares": 10.0,
                "umaResolutionStatus": "disputed",
                "exit_order_id": None,
                "unwind_order_id": None,
            },
            "WS_SNIPE_Miami_KMIA_837595": {
                "trade_id": "WS_SNIPE_Miami_KMIA_837595",
                "market_id": "6707503",
                "box_type": "SINGLE_LEG_LOCK",
                "is_single_leg_lock": True,
                "is_dominance_box": False,
                "notional_usd": 4.88,
                "remaining_cost_basis": 4.88,
                "entry_shares": 5.0,
                "remaining_shares": 5.0,
                "umaResolutionStatus": "disputed",
                "exit_order_id": None,
                "unwind_order_id": None,
            },
        },
        "closed_positions": [],
    }


class TestPhase0AccountingFloorFixes(unittest.TestCase):
    """Verifies `F-02`: UMA-disputed positions value at `$0.00` in worst-case floor calculations."""

    def test_daily_projections_kmia_disputed_floor_is_47_38_not_82_38(self) -> None:
        st = _build_kmia_disputed_state()
        recon = dp.compute_live_equity_and_rates(st, fallback_equity=97.89)
        self.assertAlmostEqual(round(recon["live_equity"], 2), 97.89)
        self.assertAlmostEqual(round(recon["locked_floor_equity"], 2), 47.38)
        self.assertAlmostEqual(recon["frozen_single_leg_cost_usd"], 50.51, places=2)

    def test_daily_projections_disputed_single_leg_without_unwresid_still_haircuts_floor(self) -> None:
        st = _build_kmia_disputed_state()
        st["active_positions"].pop(
            "MULTI_LEG_BUNDLE_LIVE_KMIA_1794113999_318559_UNWRESID_20116898_1794111898"
        )
        st["total_account_equity"] = 47.377122 + 34.19
        recon = dp.compute_live_equity_and_rates(st, fallback_equity=81.57)
        # Book equity reflects cash + $34.19 cost basis ($81.57), while worst-case floor stays $47.38
        self.assertAlmostEqual(round(recon["live_equity"], 2), 81.57)
        self.assertAlmostEqual(round(recon["locked_floor_equity"], 2), 47.38)

    def test_daily_projections_undisputed_single_leg_lock_retains_par_redemption_floor(self) -> None:
        st = {
            "bankroll": 50.0,
            "total_account_equity": 69.54,
            "pending_entry_intents": {},
            "active_positions": {
                "WS_SNIPE_OK_1": {
                    "trade_id": "WS_SNIPE_OK_1",
                    "box_type": "SINGLE_LEG_LOCK",
                    "is_single_leg_lock": True,
                    "notional_usd": 19.54,
                    "remaining_cost_basis": 19.54,
                    "entry_shares": 20.0,
                    "remaining_shares": 20.0,
                    "umaResolutionStatus": "proposed",
                }
            },
            "closed_positions": [],
        }
        recon = dp.compute_live_equity_and_rates(st, fallback_equity=69.54)
        self.assertAlmostEqual(recon["live_equity"], 69.54, places=2)
        self.assertAlmostEqual(recon["locked_floor_equity"], 70.00, places=2)

    def test_command_center_remote_probe_compiles_and_floors_kmia_at_47_38(self) -> None:
        compile(dcc.REMOTE_PROBE_PY, "<REMOTE_PROBE_PY>", "exec")
        cc_fn = _load_cc_valuations_fn()

        st = _build_kmia_disputed_state()
        _, active_book_u, live_eq_u, guar_floor_u = cc_fn(st, 47.377122, 47.377122)
        self.assertEqual(active_book_u, 50.51)
        self.assertEqual(live_eq_u, 97.89)
        self.assertEqual(guar_floor_u, 47.38)

        # Even if only disputed WS_SNIPE legs remain (no _UNWRESID_), floor is $47.38 (not $81.57)
        st_snipe_only = _build_kmia_disputed_state()
        st_snipe_only["active_positions"].pop(
            "MULTI_LEG_BUNDLE_LIVE_KMIA_1794113999_318559_UNWRESID_20116898_1794111898"
        )
        _, active_book_s, live_eq_s, guar_floor_s = cc_fn(st_snipe_only, 47.377122, 47.377122)
        self.assertEqual(active_book_s, 34.19)
        self.assertEqual(live_eq_s, 81.57)
        self.assertEqual(guar_floor_s, 47.38)

    def test_command_center_paired_box_vs_disputed_box_leg(self) -> None:
        cc_fn = _load_cc_valuations_fn()
        healthy_box_state = {
            "active_positions": {
                "BOX_A": {
                    "trade_id": "BOX_A",
                    "is_dominance_box": True,
                    "box_id": "B1",
                    "remaining_cost_basis": 4.80,
                    "remaining_shares": 10.0,
                    "custom_maker_exit_price": 0.99,
                },
                "BOX_B": {
                    "trade_id": "BOX_B",
                    "is_dominance_box": True,
                    "box_id": "B1",
                    "remaining_cost_basis": 4.90,
                    "remaining_shares": 10.0,
                    "custom_maker_exit_price": 0.99,
                },
            }
        }
        _, book_ok, eq_ok, floor_ok = cc_fn(healthy_box_state, 40.0, 40.0)
        self.assertEqual(book_ok, 9.70)
        self.assertEqual(eq_ok, 49.70)
        self.assertEqual(floor_ok, 50.00)

        # Mark one leg UMA-disputed: box pairing breaks and disputed leg contributes $0.00 to floor
        healthy_box_state["active_positions"]["BOX_B"]["umaResolutionStatus"] = "disputed"
        _, book_disp, eq_disp, floor_disp = cc_fn(healthy_box_state, 40.0, 40.0)
        self.assertEqual(book_disp, 9.70)
        self.assertEqual(eq_disp, 49.70)
        self.assertEqual(floor_disp, 44.80)


class TestPhase0MemoryBoundsFixes(unittest.TestCase):
    """Verifies `F-01`: bounded memory structures in `Alpha124ShadowDaemon` and `PolymarketDualFeed1HRecorder`."""

    def test_alpha124_slim_raw_gamma_event_strips_bloat_and_preserves_trading_keys(self) -> None:
        DaemonCls = a124_mod.Alpha124ShadowDaemon
        heavy_ev = {
            "id": "991122",
            "slug": "which-party-will-win-the-house-in-2026",
            "title": "Which party will win the House in 2026?",
            "negRisk": True,
            "negRiskAugmented": False,
            "negRiskMarketID": "0xabc123",
            "startTime": "2026-11-03T12:00:00Z",
            "endDate": "2026-11-15T12:00:00Z",
            "closed": False,
            "description": "X" * 16384,
            "image": "https://example.com/img.png",
            "tags": [{"id": str(i), "label": "politics" * 20} for i in range(40)],
            "chats": [{"id": "c1", "body": "Y" * 4096}],
            "markets": [
                {
                    "id": "m1",
                    "question": "Will the Republican Party win the House?",
                    "groupItemTitle": "Republican Party",
                    "sportsMarketType": "moneyline",
                    "line": -3.5,
                    "outcomes": '["Yes", "No"]',
                    "clobTokenIds": '["tok_yes", "tok_no"]',
                    "feesEnabled": False,
                    "umaResolutionStatus": "",
                    "closed": False,
                    "description": "Z" * 16384,
                    "image": "https://example.com/m1.png",
                }
            ],
        }
        slim = DaemonCls._slim_raw_gamma_event(heavy_ev)
        raw_bytes = len(json.dumps(heavy_ev))
        slim_bytes = len(json.dumps(slim))
        self.assertLess(slim_bytes, raw_bytes * 0.15)
        self.assertNotIn("description", slim)
        self.assertNotIn("tags", slim)
        self.assertNotIn("description", slim["markets"][0])
        for req_k in ("id", "slug", "title", "negRisk", "negRiskAugmented", "negRiskMarketID", "endDate"):
            self.assertEqual(slim[req_k], heavy_ev[req_k])
        for req_mk in ("id", "question", "groupItemTitle", "sportsMarketType", "line", "clobTokenIds"):
            self.assertEqual(slim["markets"][0][req_mk], heavy_ev["markets"][0][req_mk])

    def test_alpha124_slim_rest_book_and_ws_depth_cap_preserve_best_levels(self) -> None:
        daemon = a124_mod.Alpha124ShadowDaemon(single_scan=True, riskless_bridge_only=True)
        deep_bk = {
            "asset_id": "tok_deep",
            "minimum_tick_size": "0.001",
            "bids": [{"price": f"{0.01 + i * 0.005:.4f}", "size": "10.0"} for i in range(120)],
            "asks": [{"price": f"{0.99 - i * 0.002:.4f}", "size": "12.0"} for i in range(120)],
        }
        slim_bk = daemon._slim_rest_book(deep_bk, max_levels=25)
        self.assertEqual(len(slim_bk["bids"]), 25)
        self.assertEqual(len(slim_bk["asks"]), 25)
        self.assertEqual(slim_bk["minimum_tick_size"], "0.001")
        # Highest bid is 0.01 + 119*0.005 = 0.6050; lowest ask is 0.99 - 119*0.002 = 0.7520
        self.assertAlmostEqual(float(slim_bk["bids"][0]["price"]), 0.6050, places=4)
        self.assertAlmostEqual(float(slim_bk["asks"][0]["price"]), 0.7520, places=4)

        # Verify _apply_ws_price_changes prunes >80 levels to <=50 while preserving best bid/ask
        seed_bids = [{"price": f"{0.10 + i * 0.005:.4f}", "size": "5.0"} for i in range(85)]
        seed_asks = [{"price": f"{0.60 + i * 0.004:.4f}", "size": "5.0"} for i in range(85)]
        daemon._apply_ws_book_snapshot("tok_ws", seed_bids, seed_asks, now_ts=1000.0)
        changed = daemon._apply_ws_price_changes(
            "tok_ws",
            [{"price": "0.5300", "size": "9.0", "side": "BUY", "best_bid": "0.5300", "best_ask": "0.6000"}],
            now_ts=1001.0,
        )
        self.assertTrue(changed)
        b_map, a_map = daemon._ws_raw_levels["tok_ws"]
        self.assertLessEqual(len(b_map), 50)
        self.assertLessEqual(len(a_map), 50)
        self.assertAlmostEqual(max(b_map.keys()), 0.5300, places=4)
        self.assertAlmostEqual(min(a_map.keys()), 0.6000, places=4)

    def test_alpha124_evict_stale_caches_bounds_rest_books_and_tick_maps(self) -> None:
        daemon = a124_mod.Alpha124ShadowDaemon(single_scan=True, riskless_bridge_only=True)
        now = 10_000.0
        daemon._ws_subscribed_tokens = {"tok_keep"}
        daemon._rest_books_cache = {
            f"tok_rb_{i}": (now - 10.0 - (i * 0.01), {"asset_id": f"tok_rb_{i}", "bids": [], "asks": []})
            for i in range(1250)
        }
        daemon._token_tick_sizes = {f"tok_tk_{i}": "0.01" for i in range(2800)}
        daemon._token_tick_sizes["tok_keep"] = "0.001"
        daemon._token_tick_boundary_ts = {"tok_stale": now - 3600.0, "tok_keep": now - 3600.0}
        daemon._zf_maker_cooldown_until = {"cd_old": now - 2500.0, "cd_fresh": now - 30.0}
        daemon._ws_dead_q_by_event = {"ev_dead_old": {"q1"}, "ev_live": {"q2"}}
        daemon.negrisk_convert_slates = {"ev_live": object()}  # type: ignore[assignment]

        stats = daemon._evict_stale_caches(now_ts=now)
        self.assertGreater(stats["evicted_cache_entries"], 400)
        self.assertLessEqual(len(daemon._rest_books_cache), 1000)
        self.assertLessEqual(len(daemon._token_tick_sizes), 2500)
        self.assertEqual(daemon._token_tick_sizes.get("tok_keep"), "0.001")
        self.assertNotIn("tok_stale", daemon._token_tick_boundary_ts)
        self.assertIn("tok_keep", daemon._token_tick_boundary_ts)
        self.assertNotIn("cd_old", daemon._zf_maker_cooldown_until)
        self.assertIn("cd_fresh", daemon._zf_maker_cooldown_until)
        self.assertEqual(set(daemon._ws_dead_q_by_event.keys()), {"ev_live"})
        self.assertIsInstance(daemon._release_unused_heap_memory(), bool)

    def test_recorder_l2_book_depth_cap_and_riskless_bus_resolution_skip(self) -> None:
        book = rec_mod.L2OrderBook("tok_rec_1")
        snap_bids = [{"price": f"{0.01 + i * 0.004:.4f}", "size": "25.0"} for i in range(100)]
        snap_asks = [{"price": f"{0.55 + i * 0.004:.4f}", "size": "30.0"} for i in range(100)]
        book.apply_snapshot(snap_bids, snap_asks)
        self.assertLessEqual(len(book.bids), 40)
        self.assertLessEqual(len(book.asks), 40)
        self.assertEqual(len(book._bid_birth_ts), len(book.bids))
        self.assertEqual(len(book._ask_birth_ts), len(book.asks))

        tob = book.top_of_book(obs_ts=book.last_book_update_ts + 0.05)
        self.assertAlmostEqual(tob["best_bid"], 0.4060, places=4)
        self.assertAlmostEqual(tob["best_ask"], 0.5500, places=4)
        self.assertFalse(tob["is_crossed"])

        rec = rec_mod.PolymarketDualFeed1HRecorder(asset="BTC", riskless_bus_only=True)
        rec.books["UP"] = book
        asyncio.run(
            rec.verify_and_log_resolution(
                {"market_id": "999888", "title": "BTC Up or Down", "candle_open_ts": 1000, "candle_close_ts": 1300},
                max_polls=2,
                poll_interval_sec=0.01,
            )
        )
        # In riskless_bus_only mode, verify_and_log_resolution returns immediately without tracking/polling
        self.assertFalse(getattr(rec, "_logged_resolution_market_ids", set()))

        rec._logged_resolution_market_ids = {f"m_{i:04d}" for i in range(620)}
        rec._boundary_lock_cooldowns = {"old_m": 100.0, "fresh_m": 9950.0}
        ev_res = rec._evict_recorder_memory(now_ts=10_000.0, trim_heap=True)
        self.assertGreater(ev_res["evicted_entries"], 300)
        self.assertLessEqual(len(rec._logged_resolution_market_ids), 256)
        self.assertEqual(set(rec._boundary_lock_cooldowns.keys()), {"fresh_m"})


class TestPytestIniConfiguration(unittest.TestCase):
    """Verifies `F-06`: `pytest.ini` restricts collection to `tests/` and excludes legacy/staging dirs."""

    def test_pytest_ini_scopes_tests_and_ignores_non_test_trees(self) -> None:
        ini_path = REPO_ROOT / "pytest.ini"
        self.assertTrue(ini_path.is_file(), "pytest.ini must exist at repository root")
        cp = configparser.ConfigParser()
        cp.read(ini_path, encoding="utf-8")
        self.assertIn("pytest", cp)
        self.assertEqual(cp["pytest"].get("testpaths", "").strip(), "tests")
        norec = set(cp["pytest"].get("norecursedirs", "").split())
        for excluded in ("archive_legacy", "paa_staging", ".agents", "data", "backups", "research", "scratch", "scripts"):
            self.assertIn(excluded, norec)


class TestCommandCenterV63FullThrottle(unittest.TestCase):
    """Verifies Wave 3 (`v6.3.0`) Full-Throttle Command Center schema, 3-NAV Triad, non-conflation, HTTP/CLI, and <20 MiB SSH probe RSS."""

    @staticmethod
    def _build_offline_fixture_snapshot() -> Dict[str, Any]:
        import io
        import os
        import tempfile
        import time
        from contextlib import redirect_stdout

        now_u = time.time()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "config").mkdir(parents=True, exist_ok=True)
            (root / "data/polymarket/paa").mkdir(parents=True, exist_ok=True)
            (root / "data/full_throttle/pipeline").mkdir(parents=True, exist_ok=True)

            (root / "config/polymarket_strategy_and_risk.json").write_text(
                json.dumps(
                    {
                        "schema_version": "5.4.2",
                        "directional": {"riskless_only_mode": True},
                        "risk_controller": {"hard_ruin_floor_usd": 62.0, "riskless_hard_ruin_floor_usd": 30.0},
                        "riskless_boxes": {"strict_pure_riskless_mode": True},
                    }
                ),
                encoding="utf-8",
            )

            harvester_state = {
                "live_bankroll": 48.70,
                "total_account_equity": 99.21,
                "high_water_mark_equity": 104.50,
                "risk_halt": False,
                "active_positions": {
                    "WS_SNIPE_Miami_KMIA_242960": {
                        "trade_id": "WS_SNIPE_Miami_KMIA_242960",
                        "market_id": "6707503",
                        "sleeve": "W_PRUNE1_DEAD_NO_SWEEPER",
                        "target_token": "NO",
                        "token_id": "tok_kmia_no",
                        "entry_shares": 12.0,
                        "remaining_shares": 12.0,
                        "notional_usd": 12.04,
                        "remaining_cost_basis": 12.04,
                        "last_observed_bid": 0.004,
                        "umaResolutionStatus": "disputed",
                        "uma_disputed": True,
                    },
                    "WS_SNIPE_Miami_KMIA_688670": {
                        "trade_id": "WS_SNIPE_Miami_KMIA_688670",
                        "market_id": "6707503",
                        "sleeve": "W_PRUNE1_DEAD_NO_SWEEPER",
                        "target_token": "NO",
                        "token_id": "tok_kmia_no",
                        "entry_shares": 12.0,
                        "remaining_shares": 12.0,
                        "notional_usd": 12.03,
                        "remaining_cost_basis": 12.03,
                        "last_observed_bid": 0.004,
                        "umaResolutionStatus": "disputed",
                        "uma_disputed": True,
                    },
                    "WS_SNIPE_Miami_KMIA_837595": {
                        "trade_id": "WS_SNIPE_Miami_KMIA_837595",
                        "market_id": "6707503",
                        "sleeve": "W_PRUNE1_DEAD_NO_SWEEPER",
                        "target_token": "NO",
                        "token_id": "tok_kmia_no",
                        "entry_shares": 11.0,
                        "remaining_shares": 11.0,
                        "notional_usd": 11.03,
                        "remaining_cost_basis": 11.03,
                        "last_observed_bid": 0.004,
                        "umaResolutionStatus": "disputed",
                        "uma_disputed": True,
                    },
                    "MULTI_LEG_BUNDLE_LIVE_KMIA_1794113999_318559_UNWRESID_20116898_1794111898": {
                        "trade_id": "MULTI_LEG_BUNDLE_LIVE_KMIA_1794113999_318559_UNWRESID_20116898_1794111898",
                        "market_id": "6707502",
                        "box_type": "MULTI_LEG_RESIDUAL",
                        "sleeve": "NR_M1_NEGRISK_SLATE_SWEEP",
                        "target_token": "YES",
                        "token_id": "tok_kmia_yes",
                        "entry_shares": 17.0,
                        "remaining_shares": 17.0,
                        "notional_usd": 15.41,
                        "remaining_cost_basis": 15.41,
                        "last_observed_bid": 0.003,
                        "is_legged_out_residual": True,
                        "umaResolutionStatus": "disputed",
                    },
                },
                "pending_entry_intents": {
                    "oid_cs2_1": {
                        "entry_order_id": "oid_cs2_1",
                        "token_id": "tok_cs2_yes",
                        "market_id": "900101",
                        "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
                        "title": "Counter-Strike: Tulpar vs DNK - Map 2 Winner",
                        "outcome": "YES",
                        "anchor_bid_px": 0.995,
                        "posted_shares": 7.0,
                        "posted_notional_usd": 6.965,
                        "fifo_rank1_verified": True,
                        "effective_velocity_bps_hr": 38.0,
                        "heartbeat_ts": now_u,
                    },
                    "oid_ncaa_2": {
                        "entry_order_id": "oid_ncaa_2",
                        "token_id": "tok_ncaa_no",
                        "market_id": "900102",
                        "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
                        "title": "Games Total: O/U 2.5",
                        "outcome": "NO",
                        "anchor_bid_px": 0.995,
                        "posted_shares": 7.0,
                        "posted_notional_usd": 6.965,
                        "fifo_rank1_verified": True,
                        "effective_velocity_bps_hr": 46.0,
                        "heartbeat_ts": now_u,
                    },
                },
                "ft_live_funnel": {
                    "updated_at_utc": "2026-11-11T23:10:00Z",
                    "candidates_received": 26,
                    "ft_bridge_received": 5,
                    "clinch_watchlist_registered": 3,
                    "taker_evaluated": 11,
                    "taker_executed": 2,
                    "maker_spawned": 7,
                    "maker_posted": 5,
                    "maker_filled": 3,
                    "rejected_total": 7,
                    "resting_maker_slots": 2,
                    "by_sleeve": {
                        "FT_B_EXHAUSTIVE_SLATE": {
                            "received": 5,
                            "ft_bridge": 5,
                            "taker_evaluated": 5,
                            "taker_executed": 1,
                            "maker_posted": 0,
                            "maker_filled": 0,
                            "rejected": 4,
                        },
                        "FT_E_CALENDAR_BOX": {
                            "received": 3,
                            "ft_bridge": 3,
                            "taker_evaluated": 3,
                            "taker_executed": 1,
                            "maker_posted": 0,
                            "maker_filled": 0,
                            "rejected": 2,
                        },
                        "BOND1_UMA_RESOLUTION_CARRY": {
                            "received": 14,
                            "ft_bridge": 0,
                            "taker_evaluated": 3,
                            "taker_executed": 0,
                            "maker_posted": 4,
                            "maker_filled": 2,
                            "rejected": 0,
                        },
                        "BOND2_MOOV2_WHITELIST_FINAL_HOUR_CARRY": {
                            "received": 4,
                            "ft_bridge": 0,
                            "taker_evaluated": 0,
                            "taker_executed": 0,
                            "maker_posted": 1,
                            "maker_filled": 1,
                            "rejected": 1,
                        },
                    },
                    "reject_reasons": {"WORST_LIMIT_COST_ABOVE_CAP": 7},
                    "recent_candidates": [{"ts_unix": now_u, "box_id": "FT_BOX_1", "sleeve": "FT_B_EXHAUSTIVE_SLATE", "ft_bridge": True, "stage": "TAKER_EXECUTED"}],
                },
                "closed_positions": [
                    {
                        "trade_id": "BOND1_WIN_1",
                        "sleeve": "BOND1_UMA_RESOLUTION_CARRY",
                        "market_id": "888001",
                        "title": "Resolved UMA Bond Carry",
                        "target_token": "YES",
                        "entry_shares": 25.0,
                        "entry_price": 0.98,
                        "exit_price": 1.0,
                        "notional_usd": 24.50,
                        "net_pnl_usd": 0.50,
                        "fee_usd": 0.0,
                        "won": True,
                        "exit_ts": now_u - 600.0,
                        "exit_time_utc": "2026-11-11T22:00:00Z",
                    }
                ],
            }
            (root / "data/polymarket/live_harvester_state.json").write_text(json.dumps(harvester_state), encoding="utf-8")

            fam_cov = {}
            for idx, fc in enumerate(("A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N")):
                fam_cov[fc] = {
                    "family_name": f"Family {fc} Structural Detector",
                    "owner_track": "WAVE_1",
                    "structures_or_markets_inspected": 100 + idx * 10,
                    "candidates_emitted": 2,
                    "CLASS_A": 1 if fc in ("A", "B") else 0,
                    "CLASS_B": 1 if fc in ("E", "F") else 0,
                    "CLASS_C": 2 if fc == "F" else 0,
                    "CLASS_D": 15 if fc == "G" else 3,
                    "CLASS_E": 0,
                    "dormant_near_misses": 8,
                    "mathematically_proven_arbs": 1 if fc in ("A", "B", "E", "F") else 0,
                }
            ft_dash = {
                "schema_version": "1.0",
                "generated_at_utc": "2026-11-11T23:05:00Z",
                "execution_mode": "SHADOW_PLUS_BRIDGE",
                "jurisdiction_gate": "CA-ON",
                "campaign_summary": {
                    "total_cycles_executed": 12,
                    "avg_fast_cycle_wall_sec": 3.4,
                    "full_universe_discovery_sweep_sec": 41.2,
                    "peak_rss_mib": 168.4,
                    "swapless_180mib_budget_ok": True,
                },
                "section_1_universe_coverage": {
                    "total_observable_events": 19258,
                    "total_observable_markets": 376670,
                    "active_unclosed_markets": 201950,
                    "orderbook_enabled_markets": 201800,
                    "total_tradable_outcome_tokens": 403704,
                    "negrisk_events": 6306,
                    "augmented_negrisk_events": 1859,
                    "unresolved_or_ineligible_skip_counts": {"closed_archived": 174720},
                    "d001_frozen_kmia_holdings_quarantined": 4,
                },
                "section_1b_proposition_graph": {"total_edges": 3189, "cross_market_edges": 840, "verified_multi_market_components": 214},
                "section_1c_detector_coverage_by_family": fam_cov,
                "section_2_opportunity_metrics": {
                    "total_candidates_evaluated": 508,
                    "mathematically_valid_proofs": 4,
                    "rule_mismatch_rejections_prevented": 239,
                    "d007_quarantined_3plus_leg_count": 6,
                },
                "section_2b_persistence_and_forward_validation": {
                    "forward_validations_completed": 4,
                    "forward_validations_survived": 3,
                    "forward_survival_rate": 0.75,
                    "forward_validated_net_pnl_usd": 1.85,
                },
                "section_2c_dormant_opportunity_store": {
                    "active_dormant_count": 1200,
                    "within_50_bps_count": 572,
                    "within_150_bps_count": 940,
                    "total_rescans_triggered": 34,
                    "by_family": {"A": 510, "F": 36, "K": 26},
                    "closest_near_misses": [
                        {"candidate_id": "DORM_1", "family_code": "A", "title_summary": "BTC Complete Set Near-Arb", "gap_to_breakeven_bps": 8.5, "dormant_reason": "SUM_ASK_1.0008", "times_observed": 4}
                    ],
                },
                "section_2d_hedged_maker_shadow_quoter": {
                    "resting_passive_quotes_count": 16,
                    "total_quotes_posted": 140,
                    "filled_hedged_locks_count": 99,
                    "adverse_selected_fills_count": 0,
                    "net_post_adverse_shadow_pnl_ex_rebate_usd": 43.32,
                    "estimated_maker_rebate_15_to_25pct_usd": 0.437,
                    "top_resting_quotes": [
                        {"quote_id": "Q1", "source_family": "A", "title_summary": "ETH Intraday Box Quote", "quote_bid_px": 0.48, "initial_hedge_ask_net_px": 0.505, "locked_edge_bps_if_filled": 150.0, "shares": 10.0}
                    ],
                },
                "section_2e_harvester_candidate_bridge": {
                    "enabled": True,
                    "candidates_emitted_this_cycle": 2,
                    "total_emitted_across_campaign": 5,
                    "reconciled_nav_used_usd": 48.70,
                    "d007_15pct_concentration_cap_usd": 7.30,
                    "skipped_by_reason": {"D001_KMIA_QUARANTINED": 2},
                },
                "section_3_segregated_economics": {
                    "column_1_paper_theoretical": {"proven_class_a_b_paper_usd": 6.40},
                    "column_2_realistic_forward_shadow": {"unallocated_l2_executable_sum_usd": 2.90, "unallocated_post_latency_sum_usd": 1.85},
                    "column_3_verified_live_wallet_cash": {"liquid_pusd_cash_usd": 48.70},
                },
            }
            (root / "data/full_throttle/pipeline/dashboard_latest.json").write_text(json.dumps(ft_dash), encoding="utf-8")

            a124_state = {
                "updated_ts": now_u - 4.0,
                "cycle_count": 39,
                "catalog_counts": {
                    "zerofee_binaries": 1118,
                    "uma_proposed": 263,
                    "uma_hot_bonds": 4,
                    "negrisk_convert_slates": 6,
                    "cal1_ladders": 20,
                    "ws_subscribed_tokens": 512,
                    "ws_shards_active": 2,
                    "dormant_ws_pinned_tokens": 48,
                    "maker_pending": 78,
                },
                "live_bridge_telemetry": {
                    "emitted_total": 141,
                    "emitted_by_sleeve": {"BOND1_UMA_RESOLUTION_CARRY": 90},
                    "last_emit_ts": now_u - 10.0,
                    "pending_maker_orders_count": 78,
                },
                "by_sleeve": {
                    "BOND1_UMA_RESOLUTION_CARRY": {"closed": 43, "wins": 43, "losses": 0, "open": 1, "realized_pnl_t1000_usd": 23.88, "grad8_live_promoted": True},
                    "CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX": {"closed": 12, "wins": 12, "losses": 0, "open": 0, "realized_pnl_t1000_usd": 40.85, "grad8_live_promoted": True},
                },
            }
            (root / "data/polymarket/alpha124_shadow_state.json").write_text(json.dumps(a124_state), encoding="utf-8")

            proj_doc = {
                "model_version": "v5.2_full_throttle_riskless_velocity",
                "generated_at_utc": "2026-11-11T23:00:00Z",
                "anchor_live_state": {"reconciled_floor_nav_usd": 48.70},
                "summary_horizons_usd": {
                    "day_1": {"date_utc": "2026-11-12", "p25_equity": 50.60, "p50_equity": 51.80, "p75_equity": 53.90, "p50_daily_pnl": 3.10, "p50_net_profit": 3.10, "vm_cost_cum_usd": 0.82, "p25_net_after_vm_usd": 1.08, "p50_net_after_vm_usd": 2.28, "p75_net_after_vm_usd": 4.38},
                    "day_30": {"date_utc": "2026-12-11", "p25_equity": 135.96, "p50_equity": 183.60, "p75_equity": 313.23, "p50_daily_pnl": 7.80, "p50_net_profit": 134.90, "vm_cost_cum_usd": 24.67, "p25_net_after_vm_usd": 62.59, "p50_net_after_vm_usd": 110.23, "p75_net_after_vm_usd": 239.86},
                    "day_90": {"date_utc": "2027-02-09", "p25_equity": 304.32, "p50_equity": 740.59, "p75_equity": 1531.15, "p50_daily_pnl": 18.40, "p50_net_profit": 691.89, "vm_cost_cum_usd": 74.01, "p25_net_after_vm_usd": 181.61, "p50_net_after_vm_usd": 617.88, "p75_net_after_vm_usd": 1408.44},
                    "day_365": {"date_utc": "2027-11-11", "p25_equity": 1850.00, "p50_equity": 6200.00, "p75_equity": 14800.00, "p50_daily_pnl": 42.0, "p50_net_profit": 6151.30, "vm_cost_cum_usd": 300.15, "p25_net_after_vm_usd": 1501.15, "p50_net_after_vm_usd": 5851.15, "p75_net_after_vm_usd": 14451.15},
                },
                "production_reconciled_48_70_floor_reference_usd": {"anchor_floor_nav_usd": 48.70, "vm_breakeven_bps_per_hr": 7.04},
                "day_by_day_schedule": [
                    {"day": 1, "date_utc": "2026-11-12", "p25_daily_pnl_usd": 1.90, "p50_daily_pnl_usd": 3.10, "p75_daily_pnl_usd": 5.20, "p25_end_equity_usd": 50.60, "p50_end_equity_usd": 51.80, "p75_end_equity_usd": 53.90}
                ],
            }
            (root / "data/polymarket/live_daily_projections.json").write_text(json.dumps(proj_doc), encoding="utf-8")

            old_root = os.environ.get("DOMINUS_QUANT_ROOT")
            old_off = os.environ.get("DOMINUS_OFFLINE_PROBE")
            os.environ["DOMINUS_QUANT_ROOT"] = str(root)
            os.environ["DOMINUS_OFFLINE_PROBE"] = "1"
            buf = io.StringIO()
            try:
                with redirect_stdout(buf):
                    exec(compile(dcc.REMOTE_PROBE_PY, "<REMOTE_PROBE_PY>", "exec"), {"__name__": "__main__", "_PERSIST": {}})
            finally:
                if old_root is None:
                    os.environ.pop("DOMINUS_QUANT_ROOT", None)
                else:
                    os.environ["DOMINUS_QUANT_ROOT"] = old_root
                if old_off is None:
                    os.environ.pop("DOMINUS_OFFLINE_PROBE", None)
                else:
                    os.environ["DOMINUS_OFFLINE_PROBE"] = old_off

            lines = [ln.strip() for ln in buf.getvalue().splitlines() if ln.strip().startswith("{")]
            assert lines, "REMOTE_PROBE_PY must emit a valid JSON line"
            return json.loads(lines[-1])

    def test_v63_remote_probe_offline_schema_nav_triad_and_non_conflation(self) -> None:
        snap = self._build_offline_fixture_snapshot()
        self.assertEqual(snap["dashboard_version"], "6.3.0")

        pm = snap["polymarket_live"]
        nt = pm["nav_triad"]
        self.assertAlmostEqual(nt["reconciled_floor_nav_usd"], 48.70, places=2)
        self.assertAlmostEqual(nt["mtm_liquidation_nav_usd"], 48.89, places=2)
        self.assertAlmostEqual(nt["persisted_book_equity_usd"], 99.21, places=2)
        self.assertEqual(nt["sizing_nav_basis"], "reconciled_floor_nav_usd")
        self.assertTrue(nt["book_equity_sizing_forbidden"])
        self.assertEqual(nt["kmia_disputed_count"], 4)
        self.assertAlmostEqual(nt["kmia_frozen_cost_usd"], 50.51, places=2)
        self.assertTrue(nt["kmia_untouched_ok"])
        self.assertEqual(nt["kmia_exit_or_unwind_orders"], 0)
        self.assertAlmostEqual(nt["vm_breakeven_bps_per_hr"], 7.04, places=2)

        self.assertEqual(len(pm["resting_orders"]), 2)
        hf = pm["harvester_funnel"]
        self.assertEqual(hf["candidates_received_total"], 26)
        self.assertEqual(hf["ft_received"], 5)
        self.assertEqual(hf["ft_executed"], 2)
        self.assertEqual(hf["maker_posted"], 5)
        self.assertEqual(hf["maker_filled"], 3)
        self.assertEqual(hf["ft_rejected"], 6)
        self.assertEqual(hf["rejected_total"], 7)
        self.assertEqual(hf["fifo_rank1_slots"], 2)

        live_slv_ids = {s["sleeve"] for s in (pm.get("live_strategies") or [])}
        # BUG-W3-LS-1B: canonical active sleeves must appear in live_strategies
        for req_slv in ("C1_BINARY_COMPLETE_SET", "W_PRUNE1_DEAD_NO_BOND", "NR_M1_DEAD_SEED_OVERROUND"):
            self.assertIn(req_slv, live_slv_ids)

        v52 = snap["alpha124"]["v52_catalog"]
        self.assertEqual(v52["binaries_monitored"], 1118)
        self.assertEqual(v52["uma_proposed_count"], 263)
        self.assertEqual(v52["uma_hot_bonds_count"], 4)
        self.assertEqual(v52["ws_shards_active"], 2)
        self.assertEqual(v52["dormant_ws_pinned_tokens"], 48)
        self.assertEqual(v52["bridge_emitted_total"], 141)

        ft = snap["full_throttle"]
        self.assertTrue(ft["available"])
        # BUG-W3-LS-1C: cgroup MemoryMax reported dynamically (220.0 MiB default / systemd show)
        self.assertAlmostEqual(float(ft["systemd"]["memory_max_mib"]), 220.0, places=1)
        self.assertTrue(ft["systemd"]["cgroup_memory_ok"])
        self.assertEqual(len(ft["family_matrix"]), 14)
        self.assertEqual([r["family_code"] for r in ft["family_matrix"]], list("ABCDEFGHIJKLMN"))
        self.assertTrue(ft["family_l_maker_shadow"]["strictly_segregated_from_locked_cash"])
        self.assertAlmostEqual(ft["family_l_maker_shadow"]["net_post_adverse_shadow_pnl_ex_rebate_usd"], 43.32, places=2)

        scm = snap["strategy_comparison_matrix"]
        self.assertTrue(scm["strictly_non_conflated"])
        by_key = {r["strategy_key"]: r for r in scm["rows"]}
        for req_k in (
            "FT_LIVE_BRIDGE",
            "FAMILY_L_MAKER",
            "BOND1_CARRY",
            "MKR_LOCK1_CLINCH",
            "CAL1_TEMPORAL",
            "COND1_LOGICAL",
            "C1_COMPLETE_SET",
            "D1_STRIKE_ORACLE",
            "NR_M1_NR2_SLATE",
            "STAGE_G_CROSS_VENUE",
        ):
            self.assertIn(req_k, by_key)
        # Principle 8: Family L shadow PnL (+$43.32) must NEVER bleed into real_trading wallet PnL ($0.00)
        self.assertEqual(by_key["FAMILY_L_MAKER"]["real_trading"]["realized_wallet_pnl_usd"], 0.0)
        self.assertAlmostEqual(by_key["FAMILY_L_MAKER"]["realistic_shadow"]["shadow_net_pnl_usd"], 43.32, places=2)
        # BUG-W3-LS-1A: multi-sleeve FT_* sum (5 + 3 = 8 received, 1 + 1 = 2 executed, 4 + 2 = 6 FT rejected)
        self.assertEqual(by_key["FT_LIVE_BRIDGE"]["real_trading"]["candidates_received"], 8)
        self.assertEqual(by_key["FT_LIVE_BRIDGE"]["real_trading"]["executed"], 2)
        self.assertEqual(by_key["FT_LIVE_BRIDGE"]["real_trading"]["rejected"], 6)
        # BUG-W3-LS-1A: multi-sleeve BOND1 + BOND2 sum (14 + 4 = 18 received, 2 + 1 = 3 executed, 0 + 1 = 1 rejected)
        self.assertEqual(by_key["BOND1_CARRY"]["real_trading"]["candidates_received"], 18)
        self.assertEqual(by_key["BOND1_CARRY"]["real_trading"]["executed"], 3)
        self.assertEqual(by_key["BOND1_CARRY"]["real_trading"]["rejected"], 1)
        # BUG-W3-LS-1B: C1_COMPLETE_SET must report LIVE ACTIVE (via C1_BINARY_COMPLETE_SET), never GATED/PAUSED
        self.assertEqual(by_key["C1_COMPLETE_SET"]["real_trading"]["gate"], "LIVE ACTIVE")

        proj = snap["daily_projections"]
        self.assertTrue(proj["available"])
        self.assertTrue(proj["strictly_projected_non_cash"])
        self.assertAlmostEqual(proj["horizons"]["day_30"]["p50_net_after_vm_usd"], 110.23, places=2)
        self.assertIsNotNone(proj["milestones"]["usd_150"]["p50_day"])
        self.assertIsNotNone(proj["milestones"]["usd_253"]["p50_day"])
        self.assertIsNotNone(proj["milestones"]["usd_500"]["p50_day"])
        self.assertIsNotNone(proj["milestones"]["usd_5000"]["p50_day"])
        self.assertIsNone(proj["milestones"]["usd_5000"]["p25_day"])

    def test_v63_cli_once_formatter_renders_all_required_sections(self) -> None:
        import io
        from contextlib import redirect_stdout

        snap = self._build_offline_fixture_snapshot()
        cli_txt = dcc.format_cli_summary(snap)
        for token in (
            "DOMINUS RISKLESS PAA COMMAND CENTER v6.3 (FULL-THROTTLE)",
            "3-NAV Triad (Auth) : [1] Guaranteed Floor NAV=$48.70",
            "[2] Mark-to-Bid NAV=$48.89",
            "[3] Persisted Book Equity=$99.21 (Incl. $50.51 Frozen KMIA",
            "KMIA Disputed=4/4 Untouched=True",
            "VM Hurdle=7.04 bps/hr",
            "polymarket-full-throttle-sweep.service",
            "MemoryPeak=168.4 MiB/220MiB",
            "C1_COMPLETE_SET      | REAL[LIVE ACTIVE",
            "[Fam A]",
            "[Fam N]",
            "Family L Maker Sim : Resting=16 | HedgedFills=99",
            "REAL TRADING (WALLET pUSD) vs REALISTIC SHADOW (NON-CASH SIMULATED) — STRICTLY NON-CONFLATED:",
            "Daily Projections  : Model=v5.2_full_throttle_riskless_velocity",
            "NetPostVM=+110.23",
            "Milestone ETAs     :",
            "P25=>365d",
        ):
            self.assertIn(token, cli_txt)
        self.assertNotIn("Noned", cli_txt)
        self.assertNotIn("Nones", cli_txt)

        out_buf = io.StringIO()
        with redirect_stdout(out_buf):
            dcc.print_cli_summary(snap)
        self.assertEqual(out_buf.getvalue().strip(), cli_txt.strip())

    def test_v63_html_template_and_local_http_endpoints(self) -> None:
        import gzip
        import threading
        import urllib.error
        import urllib.request
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

        for dom_token in (
            "DOMINUS — RISKLESS PAA COMMAND CENTER v6.3",
            "sec_nav_triad",
            "sec_full_throttle",
            "ft_comp_rows",
            "ft_family_rows",
            "proj_horizon_rows",
            "renderNavTriadAndFullThrottle",
        ):
            self.assertIn(dom_token, dcc.HTML_PAGE)

        snap = self._build_offline_fixture_snapshot()

        class _TestHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                host_hdr = (self.headers.get("Host") or "").split(":")[0].strip().lower()
                if host_hdr and host_hdr not in ("127.0.0.1", "localhost"):
                    self.send_error(403, "Forbidden Host")
                    return
                use_gz = "gzip" in (self.headers.get("Accept-Encoding") or "").lower()
                if self.path.startswith("/api/snapshot") or self.path.startswith("/api/state"):
                    raw = json.dumps(snap).encode("utf-8")
                    body = gzip.compress(raw, 5) if use_gz else raw
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    if use_gz:
                        self.send_header("Content-Encoding", "gzip")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                else:
                    raw = dcc.HTML_PAGE.encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(raw)))
                    self.end_headers()
                    self.wfile.write(raw)

            def log_message(self, fmt: str, *a: Any) -> None:
                return

        srv = ThreadingHTTPServer(("127.0.0.1", 0), _TestHandler)
        port = srv.server_address[1]
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=3.0) as r_html:
                self.assertEqual(r_html.status, 200)
                self.assertIn("sec_full_throttle", r_html.read().decode("utf-8"))

            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/state", timeout=3.0) as r_st:
                self.assertEqual(r_st.status, 200)
                st_j = json.loads(r_st.read().decode("utf-8"))
                self.assertEqual(st_j["dashboard_version"], "6.3.0")

            req_gz = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/snapshot",
                headers={"Accept-Encoding": "gzip", "Host": f"127.0.0.1:{port}"},
            )
            with urllib.request.urlopen(req_gz, timeout=3.0) as r_gz:
                self.assertEqual(r_gz.headers.get("Content-Encoding"), "gzip")
                gz_j = json.loads(gzip.decompress(r_gz.read()).decode("utf-8"))
                self.assertEqual(len(gz_j["full_throttle"]["family_matrix"]), 14)

            req_bad = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/state",
                headers={"Host": "evil.example.com"},
            )
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(req_bad, timeout=3.0)
            self.assertEqual(ctx.exception.code, 403)
        finally:
            srv.shutdown()
            srv.server_close()

    def test_v63_live_ssh_probe_once_and_rss_under_20mib(self) -> None:
        cache = dcc.SnapshotCache(host="kraken-finland", start_bg=False)
        snap = cache.get(force=True)
        if snap.get("error"):
            self.skipTest(f"SSH kraken-finland unreachable in this environment: {snap['error']}")
        self.assertEqual(snap.get("dashboard_version"), "6.3.0")
        self.assertIsNotNone(snap.get("probe_rss_mib"))
        self.assertLess(float(snap["probe_rss_mib"]), 20.0, f"Probe RSS {snap['probe_rss_mib']} MiB must stay strictly < 20.0 MiB")
        nt = (snap.get("polymarket_live") or {}).get("nav_triad") or {}
        self.assertEqual(nt.get("kmia_disputed_count"), 4)
        self.assertTrue(nt.get("kmia_untouched_ok"))
        ft = snap.get("full_throttle") or {}
        self.assertEqual(len(ft.get("family_matrix") or []), 14)
        self.assertEqual((ft.get("systemd") or {}).get("service_unit"), "polymarket-full-throttle-sweep.service")
        self.assertGreaterEqual(float((ft.get("systemd") or {}).get("memory_max_mib") or 0.0), 200.0)
        scm_rows = {r["strategy_key"]: r for r in ((snap.get("strategy_comparison_matrix") or {}).get("rows") or [])}
        self.assertEqual(((scm_rows.get("C1_COMPLETE_SET") or {}).get("real_trading") or {}).get("gate"), "LIVE ACTIVE")


if __name__ == "__main__":
    unittest.main()
