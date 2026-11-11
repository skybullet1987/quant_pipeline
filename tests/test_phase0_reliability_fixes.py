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


if __name__ == "__main__":
    unittest.main()
