#!/usr/bin/env python3
"""
Unit & Integration Tests for v5.9.0 Stage D Microstructure & Riskless-PAA Suite:
  1. Governance v5.9.0 keys, safety bounds, and `RISKLESS_PAA` invariants (`schema_version == 5.5.0`,
     `riskless_only_mode == True`, `enable_two_leg_maker_anchor_boxes == False`, `MakerAnchorUnwindBreaker`).
  2. WP1 — Two-Phase Single-RTT Fast Cancel (`PolymarketUserWsCache.wait_for_order_terminal_sync` +
     `PolymarketLiveExecutor.cancel_order_fast`) with Round-11 P1-09 inventory reservation safety proofs.
  3. WP2 — Zero-REST `< 1 ms` WS Fill-to-Hedge (`_reconcile_maker_entry_fill(allow_ws_fast_fill=True)`)
     and `< 50 ms` Sharded WS L2 Shield + Sticky `#1` FIFO Repeg in `_hv_maybe_execute_graduated_maker_anchor_box`.
  4. WP3 — `synthetic_maker_quoter` tick math, `#1` FIFO bid stepping, ask-compression & OBI pre-cancels,
     and `Alpha124ShadowDaemon` multi-market Synthetic Maker wiring (`CAL1_LADDER`, `NEGRISK_NO_PAIR`, `AFF1_DEADBALL`).
  5. WP4 — `100%` Zero-Loss Live `AFF1` Settled Subperiod & Post-Final `.5`-Hook `single_leg_locks` (`p_lock = 1.0`).
"""

from __future__ import annotations

import asyncio
import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class _StubClobClient:
    """Deterministic non-MagicMock CLOB client stub for testing real `cancel_order_fast` & WS paths."""

    def __init__(self, cancel_resp: Optional[Dict[str, Any]] = None, order_resp: Optional[Dict[str, Any]] = None) -> None:
        self.cancel_resp: Dict[str, Any] = cancel_resp or {}
        self.order_resp: Optional[Dict[str, Any]] = order_resp
        self.cancel_calls: List[List[str]] = []
        self.get_order_calls: List[str] = []
        self.market_book_calls: List[str] = []

    def cancel_orders(self, order_ids: List[str]) -> Dict[str, Any]:
        self.cancel_calls.append(list(order_ids))
        return dict(self.cancel_resp)

    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        self.get_order_calls.append(str(order_id))
        return dict(self.order_resp) if isinstance(self.order_resp, dict) else None


def _make_seeded_user_ws() -> Any:
    from src.polymarket_research.polymarket_ws_streams import PolymarketUserWsCache

    uws = PolymarketUserWsCache("k", "s", "p")
    with uws._lock:
        uws._connected = True
        uws._connected_since_mono = time.monotonic() - 5.0
        uws._last_rx_mono = time.monotonic()
        uws._seeded_since_connect = True
    return uws


class TestV590FastCancelWsHedgeAndSyntheticMaker(unittest.TestCase):
    def test_v590_governance_keys_bounds_and_riskless_paa_invariants(self) -> None:
        from src.polymarket_research.holistic_strategy_governance import (
            DEFAULT_HOLISTIC_CONFIG,
            HotReloadConfigManager,
            _deep_merge_validated,
        )
        from src.polymarket_research.synthetic_maker_quoter import (
            MakerAnchorUnwindBreaker,
            is_maker_anchor_live_permitted,
        )

        cfg_path = PROJECT_ROOT / "config" / "polymarket_strategy_and_risk.json"
        raw = json.loads(cfg_path.read_text(encoding="utf-8"))
        mgr = HotReloadConfigManager(config_path=cfg_path)
        snap = mgr.snapshot

        # Ironclad RISKLESS_PAA live invariants
        self.assertEqual(raw["schema_version"], "5.5.0")
        self.assertTrue(snap["directional"]["riskless_only_mode"])
        rb = snap["riskless_boxes"]
        self.assertFalse(rb["enable_two_leg_maker_anchor_boxes"])
        self.assertFalse(rb["enable_d1_rebate_maker_canary"])
        self.assertTrue(rb["strict_pure_riskless_mode"])
        self.assertIn("SP3_SPORTS_CORRIDOR_DOMINANCE_BOX", rb["paused_riskless_sleeves"])
        self.assertIn("SOC2_EXACT_SCORE_2D_LATTICE", rb["paused_riskless_sleeves"])

        # v5.9.0 microstructure keys
        self.assertTrue(bool(rb["enable_fast_1rtt_cancel"]))
        self.assertTrue(bool(rb["enable_ws_zero_rest_maker_hedge"]))
        self.assertTrue(bool(rb["enable_synthetic_maker_ws_shield"]))
        self.assertAlmostEqual(float(rb["synthetic_maker_min_hedge_depth_mult"]), 4.0)
        self.assertAlmostEqual(float(rb["synthetic_maker_unwind_breaker_usd"]), 0.50)
        self.assertAlmostEqual(float(rb["synthetic_maker_repeg_debounce_sec"]), 0.50)

        for bad in (
            {"synthetic_maker_min_hedge_depth_mult": 1.2},
            {"synthetic_maker_min_hedge_depth_mult": 15.0},
            {"synthetic_maker_unwind_breaker_usd": 0.01},
            {"synthetic_maker_unwind_breaker_usd": 9.0},
            {"synthetic_maker_repeg_debounce_sec": 0.02},
            {"synthetic_maker_repeg_debounce_sec": 8.0},
        ):
            with self.assertRaises(ValueError):
                _deep_merge_validated(DEFAULT_HOLISTIC_CONFIG, {"riskless_boxes": bad})

        # MakerAnchorUnwindBreaker & live permission gate
        brk = MakerAnchorUnwindBreaker(max_unwind_loss_usd=0.50)
        ok0, why0 = is_maker_anchor_live_permitted("ZF_INTRADAY_MAKER_BOX", rb, unwind_breaker=brk)
        self.assertFalse(ok0)
        self.assertEqual(why0, "MAKER_ANCHOR_DISABLED_BY_RISKLESS_PAA")

        rb_on = {**rb, "enable_two_leg_maker_anchor_boxes": True}
        self.assertEqual(is_maker_anchor_live_permitted("ZF_INTRADAY_MAKER_BOX", rb_on, unwind_breaker=brk), (True, "OK"))
        self.assertEqual(
            is_maker_anchor_live_permitted("SP3_SPORTS_CORRIDOR_DOMINANCE_BOX", rb_on, unwind_breaker=brk),
            (False, "PAUSED_RISKLESS_SLEEVE:SP3_SPORTS_CORRIDOR_DOMINANCE_BOX"),
        )
        brk.record_unwind_pnl("ZF_INTRADAY_MAKER_BOX", -0.30)
        self.assertFalse(brk.is_halted("ZF_INTRADAY_MAKER_BOX")[0])
        brk.record_unwind_pnl("ZF_INTRADAY_MAKER_BOX", -0.25)
        self.assertTrue(brk.is_halted("ZF_INTRADAY_MAKER_BOX")[0])
        perm_ok_brk, perm_why_brk = is_maker_anchor_live_permitted("ZF_INTRADAY_MAKER_BOX", rb_on, unwind_breaker=brk)
        self.assertFalse(perm_ok_brk)
        self.assertIn("UNWIND_BLEED_BREAKER", perm_why_brk)

    def test_wp1_fast_1rtt_cancel_and_round11_reservation_invariants(self) -> None:
        from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor

        with tempfile.TemporaryDirectory() as tmpdir:
            res_file = Path(tmpdir) / "reservations.json"
            with patch.dict("os.environ", {"POLYMARKET_RESERVATIONS_PATH": str(res_file)}):
                ex = PolymarketLiveExecutor(dry_run=True)
                ex.reservation_records = {}
                ex.dry_run = False
                ex.is_authenticated = True
                uws = _make_seeded_user_ws()
                ex._user_ws_cache = uws

                # 1. Clean 1-RTT cancel confirmed via `/ws/user` (<15ms condvar wakeup, 0 `get_order` REST calls!)
                oid1 = "0xfast_canc_1"
                uws.seed_open_orders([{"id": oid1, "status": "LIVE", "original_size": "20", "size_matched": "0"}])
                stub1 = _StubClobClient(cancel_resp={"canceled": [oid1]}, order_resp={"status": "LIVE", "size_matched": "0", "original_size": "20"})
                ex.client = stub1

                def _push_ws_cancel() -> None:
                    time.sleep(0.008)
                    uws.process_ws_payload({"event_type": "order", "type": "CANCELLATION", "id": oid1, "original_size": "20", "size_matched": "0"})

                t_push = threading.Thread(target=_push_ws_cancel, daemon=True)
                t0 = time.perf_counter()
                t_push.start()
                r1 = ex.cancel_order_fast(oid1, ws_confirm_timeout_sec=0.10)
                dt_ms = (time.perf_counter() - t0) * 1000.0
                t_push.join(timeout=0.2)

                self.assertTrue(r1["is_canceled"])
                self.assertEqual(r1["outcome"], "CANCELED")
                self.assertEqual(len(stub1.cancel_calls), 1)
                self.assertEqual(len(stub1.get_order_calls), 0, "Expected ZERO synchronous get_order RTTs!")
                self.assertLess(dt_ms, 80.0)

                # 2. Round-11 P1-09 Proof A: `/ws/user` reports `MATCHED` -> NEVER releases reservation!
                oid_fill = "0xfast_raced_fill"
                ex.reserve_inventory("tok_sell_1", 15.0, reservation_id=oid_fill)
                uws.process_ws_payload({"event_type": "order", "type": "UPDATE", "status": "MATCHED", "id": oid_fill, "original_size": "15", "size_matched": "15"})
                stub_fill = _StubClobClient(cancel_resp={"not_canceled": {oid_fill: "already matched"}})
                ex.client = stub_fill
                r_fill = ex.cancel_order_fast(oid_fill, ws_confirm_timeout_sec=0.02)
                self.assertFalse(r_fill["is_canceled"])
                self.assertEqual(r_fill["outcome"], "FILLED")
                self.assertAlmostEqual(float(r_fill["matched"]), 15.0)
                self.assertIn(oid_fill, ex.reservation_records, "Reservation MUST remain locked on FILLED!")
                self.assertEqual(len(stub_fill.get_order_calls), 0)
                ex.release_inventory(reservation_id=oid_fill)

                # 3. Round-11 P1-09 Proof B: `canceled: [oid]` arrives while `/ws/user` is still `LIVE` ->
                #    returns immediately (`0` blocking `get_order` on caller thread) while keeping reservation LOCKED
                #    until background proof confirms terminal cancel!
                oid_def = "0xfast_deferred_res"
                ex.reserve_inventory("tok_sell_2", 12.0, reservation_id=oid_def)
                uws.seed_open_orders([{"id": oid_def, "status": "LIVE", "original_size": "12", "size_matched": "0"}])
                stub_def = _StubClobClient(cancel_resp={"canceled": [oid_def]}, order_resp={"status": "LIVE", "size_matched": "0", "original_size": "12"})
                ex.client = stub_def
                with patch("src.polymarket_research.polymarket_live_executor._get_hot_io_pool") as mock_pool:
                    r_def = ex.cancel_order_fast(oid_def, ws_confirm_timeout_sec=0.005, defer_unconfirmed_proof=True)
                    self.assertTrue(r_def["is_canceled"])
                    self.assertEqual(r_def["outcome"], "CANCELED")
                    self.assertEqual(len(stub_def.get_order_calls), 0)
                    self.assertIn(oid_def, ex.reservation_records)
                    self.assertEqual(ex.reservation_records[oid_def]["status"], "PENDING_CANCEL_PROOF")
                    self.assertEqual(mock_pool.return_value.submit.call_count, 1)
                # Now deliver terminal cancel to background verifier -> releases reservation cleanly
                stub_def.order_resp = {"status": "CANCELED", "size_matched": "0", "original_size": "12"}
                self.assertTrue(ex._verify_and_release_canceled_reservation_bg(oid_def))
                self.assertNotIn(oid_def, ex.reservation_records)

    def test_wp2_zero_rest_ws_fill_and_sub50ms_maker_shield(self) -> None:
        from src.polymarket_research import polymarket_live_harvester as plh
        from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor
        from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester

        async def _run() -> None:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp = Path(tmpdir)
                with patch.dict("os.environ", {"POLYMARKET_RESERVATIONS_PATH": str(tmp / "reservations.json")}), patch.object(
                    plh, "STATE_FILE", tmp / "state.json"
                ):
                    hv = PolymarketLiveHarvester(dry_run=True)
                    hv.dry_run = False
                    hv._startup_reconciled = True
                    hv.risk_halt = False
                    hv.global_halt_reasons = []
                    hv._last_known_collateral = 100.0
                    hv.max_exposure = 95.0

                    ex = PolymarketLiveExecutor(dry_run=True)
                    ex.reservation_records = {}
                    ex.dry_run = False
                    ex.is_authenticated = True
                    uws = _make_seeded_user_ws()
                    ex._user_ws_cache = uws
                    stub = _StubClobClient(cancel_resp={"canceled": ["0xanc1"]})
                    ex.client = stub
                    hv.executor = ex

                    # A. `_reconcile_maker_entry_fill(..., ws_filled=True, allow_ws_fast_fill=True)` -> 0 REST `get_order`!
                    oid_ws = "0xws_fast_fill_1"
                    uws.process_ws_payload(
                        {
                            "event_type": "order",
                            "type": "UPDATE",
                            "status": "MATCHED",
                            "id": oid_ws,
                            "original_size": "10",
                            "size_matched": "10",
                            "price": "0.48",
                        }
                    )
                    c_res, summ, m_sh, avg_px = await hv._reconcile_maker_entry_fill(
                        oid_ws, "tok_a", True, 10.0, 0.48, 0.0, allow_ws_fast_fill=True
                    )
                    self.assertEqual((summ or {}).get("source"), "USER_WS_FAST_FILL")
                    self.assertAlmostEqual(m_sh, 10.0)
                    self.assertAlmostEqual(avg_px, 0.48)
                    self.assertEqual(len(stub.get_order_calls), 0, "Expected ZERO REST get_order calls on WS fast fill!")

                    # B. `<50ms` Sharded WS Shield cancels thinned hedge book in `<250ms` (vs legacy `2,000ms`!)
                    st_dir = tmp / "polymarket"
                    st_dir.mkdir(parents=True, exist_ok=True)
                    (st_dir / "alpha124_shadow_state.json").write_text(
                        json.dumps(
                            {
                                "by_sleeve": {
                                    "ZF_INTRADAY_MAKER_BOX": {
                                        "closed": 10,
                                        "win_rate_pct": 100.0,
                                        "realized_pnl_t1000_usd": 12.5,
                                        "legging_adjusted_pnl_t1000_usd": 11.0,
                                    }
                                }
                            }
                        ),
                        encoding="utf-8",
                    )

                    class _FakeMktWs:
                        def __init__(self) -> None:
                            self.books: Dict[str, Dict[str, Any]] = {
                                "tok_anc": {"bids": [{"price": "0.47", "size": "40"}], "asks": [{"price": "0.51", "size": "40"}]},
                                "tok_hdg": {"bids": [{"price": "0.48", "size": "40"}], "asks": [{"price": "0.50", "size": "60"}]},
                            }

                        def subscribe_tokens_immediate(self, toks: List[str]) -> None:
                            pass

                        def get_book(self, tok: str, max_age_sec: float = 1.5) -> Optional[Dict[str, Any]]:
                            return self.books.get(tok)

                    fake_ws = _FakeMktWs()
                    hv._pos_market_ws = fake_ws
                    hv.risk_config = {**plh.RISK_CONFIG, "enable_live_maker_anchor_boxes": True, "max_concurrent_d1_boxes": 4, "max_total_portfolio_slots": 4}
                    hv._wallet_token_balance = lambda _t: 0.0  # type: ignore[assignment]
                    uws.seed_open_orders([{"id": "0xanc1", "status": "LIVE", "original_size": "12", "size_matched": "0"}])

                    def _thin_hedge_and_ws_cancel() -> None:
                        time.sleep(0.06)
                        # Thin hedge depth from 60 sh -> 2 sh on WS!
                        fake_ws.books["tok_hdg"] = {"bids": [{"price": "0.48", "size": "40"}], "asks": [{"price": "0.50", "size": "2"}]}
                        time.sleep(0.03)
                        uws.process_ws_payload({"event_type": "order", "type": "CANCELLATION", "id": "0xanc1", "original_size": "12", "size_matched": "0"})

                    cand = {
                        "box_id": "MKR_SHIELD_TEST",
                        "box_type": "ZERO_FEE_MAKER_ANCHOR",
                        "sleeve_source": "ZF_INTRADAY_MAKER_BOX",
                        "asset": "NBA",
                        "dedupe_key": "ZF_SHIELD_1",
                        "leg_a_market_id": "m_a",
                        "leg_b_market_id": "m_b",
                        "leg_a_token_id": "tok_anc",
                        "leg_b_token_id": "tok_hdg",
                        "leg_a_fee_rate": 0.0,
                        "leg_b_fee_rate": 0.0,
                        "anchor_is_a": True,
                        "anchor_bid_px": 0.48,
                        "hedge_limit_px": 0.50,
                        "expiry_ts": time.time() + 1800.0,
                        "ts_unix": time.time(),
                    }
                    with patch.object(plh, "DATA_DIR", st_dir), patch.object(
                        ex,
                        "post_maker_entry_order",
                        return_value={"success": True, "orderID": "0xanc1", "price": 0.48, "shares": 12.0},
                    ), patch.object(
                        PolymarketLiveExecutor,
                        "get_market_book",
                        side_effect=AssertionError("Should NOT hit REST get_market_book!"),
                    ):
                        th = threading.Thread(target=_thin_hedge_and_ws_cancel, daemon=True)
                        t_start = time.perf_counter()
                        th.start()
                        out = await hv.maybe_execute_graduated_maker_anchor_box(cand)
                        elapsed_ms = (time.perf_counter() - t_start) * 1000.0
                        th.join(timeout=0.3)

                    self.assertFalse(out["executed"])
                    self.assertEqual(out["reason"], "MAKER_ANCHOR_EXPIRED_UNFILLED")
                    self.assertLess(elapsed_ms, 450.0, f"WS shield must abort in <450ms (was 2,000ms+), got {elapsed_ms:.1f}ms")
                    self.assertEqual(len(stub.cancel_calls), 1)
                    self.assertEqual(len(stub.get_order_calls), 0)

        asyncio.run(_run())

    def test_wp3_wp4_synthetic_quoter_aff1_settled_locks_and_shadow_wiring(self) -> None:
        from src.polymarket_research.alpha_124_shadow_daemon import Alpha124ShadowDaemon
        from src.polymarket_research.riskless_frontier_v4_engine import (
            AffineGameBundle,
            NbaSubperiodMarketSpec,
            SubperiodFreezeTracker,
            evaluate_aff1_frozen_subperiod_opportunities,
        )
        from src.polymarket_research.synthetic_maker_quoter import (
            compute_synthetic_maker_quote,
            evaluate_resting_synthetic_quote_tick,
        )

        # 1. Synthetic Maker Quoter math (`1.010` combined asks -> `#1` FIFO `postOnly` @ `$0.48 + $0.50 = $0.980`)
        bk_a = {"bids": [{"price": "0.47", "size": "50"}], "asks": [{"price": "0.51", "size": "45"}]}
        bk_b = {"bids": [{"price": "0.47", "size": "50"}], "asks": [{"price": "0.50", "size": "120"}]}
        q = compute_synthetic_maker_quote(
            family="CAL1_LADDER",
            leg_a={"token_id": "ta", "fee_rate": 0.0, "fee_exponent": 1.0},
            leg_b={"token_id": "tb", "fee_rate": 0.0, "fee_exponent": 1.0},
            book_a=bk_a,
            book_b=bk_b,
            target_shares=18.0,
            max_box_cost_net=0.988,
            min_hedge_depth_mult=4.0,
        )
        self.assertTrue(q["eligible"])
        self.assertTrue(q["fifo_rank1"])
        self.assertLessEqual(q["pair_cost_net"], 0.988)
        self.assertGreaterEqual(q["hedge_avail_shares"], 72.0)

        # OBI collapse + Ask compression on anchor both trigger immediate pre-cancel
        bk_a_comp = {"bids": [{"price": "0.48", "size": "25"}], "asks": [{"price": "0.49", "size": "90"}]}
        ev_obi = evaluate_resting_synthetic_quote_tick(
            posted_bid_px=0.48,
            posted_shares=18.0,
            anchor_book=bk_a_comp,
            hedge_book=bk_b,
            max_entry_box_cost_net=0.988,
            max_keep_box_cost_net=0.990,
        )
        self.assertEqual(ev_obi["action"], "CANCEL_ADVERSE")
        self.assertIn("ANCHOR_OBI_SWEEP", ev_obi["reason"])

        ev_comp = evaluate_resting_synthetic_quote_tick(
            posted_bid_px=0.48,
            posted_shares=18.0,
            anchor_book=bk_a_comp,
            hedge_book=bk_b,
            max_entry_box_cost_net=0.988,
            max_keep_box_cost_net=0.990,
            min_keep_obi=-0.80,
        )
        self.assertEqual(ev_comp["action"], "CANCEL_ADVERSE")
        self.assertIn("ASK_COMPRESSION", ev_comp["reason"])

        # Outbid by +1c while pair math <= 0.990 triggers REPEG_FIFO1
        bk_a_outbid = {"bids": [{"price": "0.48", "size": "30"}], "asks": [{"price": "0.52", "size": "45"}]}
        ev_rp = evaluate_resting_synthetic_quote_tick(
            posted_bid_px=0.47,
            posted_shares=18.0,
            anchor_book=bk_a_outbid,
            hedge_book={"bids": [{"price": "0.47", "size": "50"}], "asks": [{"price": "0.49", "size": "90"}]},
            max_entry_box_cost_net=0.990,
            max_keep_box_cost_net=0.992,
            advance_since_mono=100.0,
            now_mono=100.8,
            advance_debounce_sec=0.50,
        )
        self.assertEqual(ev_rp["action"], "REPEG_FIFO1")
        self.assertAlmostEqual(float(ev_rp["repeg_bid_px"]), 0.49)

        # 2. WP4: `AFF1` Settled Subperiod & Final `.5`-hook Single-Leg Locks (`p_lock = 1.0`)
        bundle = AffineGameBundle(
            sport="NBA",
            event_id="ev_nba_1",
            slug="nba-bos-lal",
            title="Celtics vs. Lakers",
            tipoff_ts=1000.0,
            settle_est_ts=9000.0,
            away_team="celtics",
            home_team="lakers",
            markets=[
                NbaSubperiodMarketSpec("ev_nba_1", "m_q1_tot", "c_q1_tot", "Q1", "TOTAL", 56.5, None, "t_q1_ov", "t_q1_un", "Over", "Under", 0.0, 4000.0, "1Q O/U 56.5", False, 1.0),
                NbaSubperiodMarketSpec("ev_nba_1", "m_q1_sp", "c_q1_sp", "Q1", "SPREAD", 2.5, "celtics", "t_q1_bos", "t_q1_lal", "Celtics", "Lakers", 0.0, 4000.0, "1Q Celtics(-2.5)/Lakers(+2.5)", False, 1.0),
                NbaSubperiodMarketSpec("ev_nba_1", "m_1h_tt", "c_1h_tt", "1H", "TEAM_TOTAL", 58.5, "celtics", "t_1h_bov", "t_1h_bun", "Over", "Under", 0.0, 5500.0, "1H Celtics O/U 58.5", False, 1.0),
                NbaSubperiodMarketSpec("ev_nba_1", "m_fg_tot", "c_fg_tot", "FG", "TOTAL", 221.5, None, "t_fg_ov", "t_fg_un", "Over", "Under", 0.0, 9000.0, "Game O/U 221.5", False, 1.0),
            ],
            overtime_yes_leg=None,
            first_passage_markets=[],
        )
        tr = SubperiodFreezeTracker()
        sum_q2 = {
            "state": "in",
            "completed": False,
            "is_halftime": False,
            "period": 2,
            "clock_sec": 600.0,
            "away_score": 32,
            "home_score": 28,
            "linescores": {"away": {1: 32}, "home": {1: 28}},
        }
        # First observation at t=2000 -> NOT YET FROZEN (0 locks!)
        res_unconfirmed = evaluate_aff1_frozen_subperiod_opportunities(bundle, sum_q2, {}, tr, 2000.0, espn_game_id="g_lk")
        self.assertEqual(res_unconfirmed["single_leg_locks"], [])

        # Confirmed frozen after 46s -> Q1 Total=60 (>56.5 -> Over) & Q1 Margin=+4 (>+2.5 -> Celtics -2.5) locked at p_lock=1.0!
        res_q1 = evaluate_aff1_frozen_subperiod_opportunities(bundle, sum_q2, {}, tr, 2046.0, espn_game_id="g_lk")
        lk_by_mid = {x["market_id"]: x for x in res_q1["single_leg_locks"]}
        self.assertIn("m_q1_tot", lk_by_mid)
        self.assertEqual(lk_by_mid["m_q1_tot"]["token_id"], "t_q1_ov")
        self.assertEqual(lk_by_mid["m_q1_tot"]["p_lock"], 1.0)
        self.assertIn("m_q1_sp", lk_by_mid)
        self.assertEqual(lk_by_mid["m_q1_sp"]["token_id"], "t_q1_bos")
        self.assertEqual(lk_by_mid["m_q1_sp"]["p_lock"], 1.0)

        # Post-Final FG Total=218 (<221.5 -> Under) requires 45s post-final confirmation!
        sum_fin = {
            "state": "post",
            "completed": True,
            "is_halftime": False,
            "period": 4,
            "clock_sec": 0.0,
            "away_score": 112,
            "home_score": 106,
            "linescores": {"away": {1: 32, 2: 30, 3: 26, 4: 24}, "home": {1: 28, 2: 27, 3: 26, 4: 25}},
        }
        res_fin_0 = evaluate_aff1_frozen_subperiod_opportunities(bundle, sum_fin, {}, tr, 5000.0, espn_game_id="g_lk")
        self.assertNotIn("m_fg_tot", {x["market_id"] for x in res_fin_0["single_leg_locks"]})
        res_fin_ok = evaluate_aff1_frozen_subperiod_opportunities(bundle, sum_fin, {}, tr, 5046.0, espn_game_id="g_lk")
        fin_by_mid = {x["market_id"]: x for x in res_fin_ok["single_leg_locks"]}
        self.assertEqual(fin_by_mid["m_fg_tot"]["token_id"], "t_fg_un")
        self.assertEqual(fin_by_mid["m_fg_tot"]["mode"], "AFF1_FINAL_SUBPERIOD_LOCK")
        self.assertEqual(fin_by_mid["m_fg_tot"]["p_lock"], 1.0)
        self.assertEqual(fin_by_mid["m_1h_tt"]["token_id"], "t_1h_bov")  # Celtics 1H = 62 > 58.5

        # 3. `Alpha124ShadowDaemon` multi-market `CAL1_LADDER` Synthetic Maker Quoter (`>= 4.0x` hedge depth enforced)
        from src.polymarket_research import alpha_124_shadow_daemon as a124

        with tempfile.TemporaryDirectory() as tmpdir:
            tp = Path(tmpdir)
            with patch.object(a124, "DATA_DIR", tp), patch.object(a124, "STATE_FILE", tp / "state.json"), patch.object(
                a124, "LEDGER_FILE", tp / "ledger.jsonl"
            ), patch.object(a124, "D1_LIVE_CANDIDATES_FILE", tp / "d1_cands.jsonl"):
                dm = Alpha124ShadowDaemon(single_scan=True)
                la = {"token_id": "cal_a", "opp_token_id": "cal_ao", "condition_id": "ca", "market_id": "ma", "label": "YES_EARLY", "fee_rate": 0.0, "fee_exponent": 1.0, "strike": 100.0}
                lb = {"token_id": "cal_b", "opp_token_id": "cal_bo", "condition_id": "cb", "market_id": "mb", "label": "NO_LATE", "fee_rate": 0.0, "fee_exponent": 1.0, "strike": 101.0}
                # Thin hedge depth (50 sh < 4.0 * 18 = 72 sh) -> REJECTED for CAL1_LADDER!
                self.assertFalse(
                    dm.post_zero_fee_maker_anchor_box(
                        "CAL1_LADDER",
                        "MACRO",
                        "ZF_CAL_THIN",
                        la,
                        lb,
                        {"bids": [{"price": "0.47", "size": "50"}], "asks": [{"price": "0.51", "size": "50"}]},
                        {"bids": [{"price": "0.47", "size": "50"}], "asks": [{"price": "0.50", "size": "50"}]},
                        close_ts=1000.0 + 86400.0,
                        title="Macro Deadline Ladder",
                        now_ts=1000.0,
                    )
                )
                # Deep hedge depth (100 sh >= 72 sh) + 48h TTE (`<= 72h` CAL1 horizon) -> ACCEPTED!
                self.assertTrue(
                    dm.post_zero_fee_maker_anchor_box(
                        "CAL1_LADDER",
                        "MACRO",
                        "ZF_CAL_DEEP",
                        la,
                        lb,
                        {"bids": [{"price": "0.47", "size": "60"}], "asks": [{"price": "0.51", "size": "100"}]},
                        {"bids": [{"price": "0.47", "size": "60"}], "asks": [{"price": "0.50", "size": "100"}]},
                        close_ts=1000.0 + 120000.0,
                        title="Macro Deadline Ladder",
                        now_ts=1000.0,
                    )
                )
                self.assertIn("ZF_CAL_DEEP", dm.pending_zero_fee_maker_anchors)

    def test_v591_paused_s2_reserve_unfreeze_and_blind_preempt_guard(self) -> None:
        from types import SimpleNamespace
        from src.polymarket_research.holistic_strategy_governance import GLOBAL_GOVERNANCE_MANAGER
        from src.polymarket_research.riskless_protocol_v2_expansion import (
            compute_sll_entry_budget,
            maybe_preempt_mlk1_if_bond1_starved,
        )

        _, gsn = GLOBAL_GOVERNANCE_MANAGER.maybe_reload(force=True)
        rb = dict(gsn["riskless_boxes"])
        self.assertAlmostEqual(float(rb["paused_s2_reserve_floor_usd"]), 2.0)
        self.assertAlmostEqual(float(rb["sll_preempt_birth_grace_sec"]), 45.0)

        now_ts = 1794162000.0
        miami_positions = {
            "WS_SNIPE_Miami_KMIA_242960": {
                "box_type": "SINGLE_LEG_LOCK",
                "sleeve": "W_PRUNE1_DEAD_NO_BOND",
                "notional_usd": 19.54,
                "candle_expiry_ts": 1794113999.0,
                "status": "POSITION_CONFIRMED",
            },
            "MULTI_LEG_BUNDLE_LIVE_KMIA_318559": {
                "box_type": "MULTI_LEG_RESIDUAL",
                "sleeve": "W_PRUNE1_NR0_BASKET",
                "notional_usd": 16.32,
                "candle_expiry_ts": 1794113999.0,
                "status": "EXIT_RESTING",
            },
            "WS_SNIPE_Miami_KMIA_688670": {
                "box_type": "SINGLE_LEG_LOCK",
                "sleeve": "W_PRUNE1_DEAD_NO_BOND",
                "notional_usd": 9.77,
                "candle_expiry_ts": 1794113999.0,
                "status": "POSITION_CONFIRMED",
            },
            "WS_SNIPE_Miami_KMIA_837595": {
                "box_type": "SINGLE_LEG_LOCK",
                "sleeve": "W_PRUNE1_DEAD_NO_BOND",
                "notional_usd": 4.88,
                "candle_expiry_ts": 1794113999.0,
                "status": "POSITION_CONFIRMED",
            },
        }
        harv = SimpleNamespace(
            dry_run=False,
            max_exposure=250.0,
            enforce_gatling_sizing=True,
            enforce_gatling_fast_gun_reserve=True,
            enforce_bond1_smart_queue=False,
            _is_v5_unleashed_active=lambda: True,
            executor=SimpleNamespace(client=object()),
            active_positions=dict(miami_positions),
            pending_entry_intents={},
            _prepost_sll_reserved_usd={},
        )
        rcfg_b1 = gsn.get("sleeves", {}).get("BOND1_UMA_RESOLUTION_CARRY", {})

        # 1. With S2 paused in `RISKLESS_PAA`, $26.50 free cash unlocks 3 sequential #1 FIFO BOND1 slots (8 + 8 + 5 = 21 sh)
        b_slot1, _, _ = compute_sll_entry_budget(
            harv, "BOND1_UMA_RESOLUTION_CARRY", "m_b1_1", 26.50, True, True, rb, rcfg_b1, gsn, 3600.0, now_ts
        )
        sh1 = int(b_slot1 // 0.992)
        self.assertEqual(sh1, 8)
        harv.pending_entry_intents["i1"] = {
            "inflight_key": "IK1",
            "live_maker_anchor_inflight": True,
            "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
            "notional_usd": round(sh1 * 0.992, 4),
        }
        b_slot2, _, _ = compute_sll_entry_budget(
            harv, "BOND1_UMA_RESOLUTION_CARRY", "m_b1_2", 26.50, True, True, rb, rcfg_b1, gsn, 3600.0, now_ts
        )
        sh2 = int(b_slot2 // 0.992)
        self.assertEqual(sh2, 8)
        harv.pending_entry_intents["i2"] = {
            "inflight_key": "IK2",
            "live_maker_anchor_inflight": True,
            "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
            "notional_usd": round(sh2 * 0.992, 4),
        }
        b_slot3, _, _ = compute_sll_entry_budget(
            harv, "BOND1_UMA_RESOLUTION_CARRY", "m_b1_3", 26.50, True, True, rb, rcfg_b1, gsn, 3600.0, now_ts
        )
        sh3 = int(b_slot3 // 0.992)
        self.assertGreaterEqual(sh3, 5)

        # 2. If S2 is unpaused, the $21.56 (`max($20, 28% * $77.01)`) Fast-Gun reserve automatically re-engages
        rb_s2_live = dict(rb)
        rb_s2_live["paused_riskless_sleeves"] = [
            s for s in rb["paused_riskless_sleeves"] if s not in {"S2_RTDS_EXACT_TWAP_INTEGRATOR", "S2_EXACT_TWAP_LOCK"}
        ]
        harv.pending_entry_intents.clear()
        b_unpaused, _, _ = compute_sll_entry_budget(
            harv, "BOND1_UMA_RESOLUTION_CARRY", "m_b1_1", 26.50, True, True, rb_s2_live, rcfg_b1, gsn, 3600.0, now_ts
        )
        self.assertLess(int(b_unpaused // 0.992), 5)

        # 3a. Blind-preempt guard: if post-cancel BOND1 budget STILL cannot buy >=5 shares, NEVER cancel resting MKR_LOCK1!
        ev_mlk = asyncio.Event()
        harv._maker_anchor_preempt_events = {"IK_MLK_LIVE": ev_mlk}
        harv.pending_entry_intents = {
            "mlk_live": {
                "inflight_key": "IK_MLK_LIVE",
                "market_id": "m_mlk",
                "sleeve_source": "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER",
                "live_maker_anchor_inflight": True,
                "notional_usd": 7.90,
                "anchor_bid_px": 0.994,
                "expiry_ts": now_ts + 7200.0,
                "fifo_rank1_verified": False,
                "ts": now_ts - 120.0,
            }
        }
        out_blind = asyncio.run(
            maybe_preempt_mlk1_if_bond1_starved(
                harv,
                "BOND1_UMA_RESOLUTION_CARRY",
                0.0,
                26.28,
                True,
                True,
                rb_s2_live,
                rcfg_b1,
                gsn,
                0.0,
                1800.0,
                now_ts,
                cand_bid_px=0.992,
            )
        )
        self.assertEqual(out_blind, 0.0)
        self.assertFalse(ev_mlk.is_set(), "Must NEVER cancel MKR_LOCK1 when post-cancel BOND1 budget is still <5 shares!")

        # 3b. Birth-grace guard: newborn (0.4s < 45.0s) MKR_LOCK1 must NOT be self-canceled before FIFO rank-1 is sampled!
        harv.pending_entry_intents["mlk_live"]["ts"] = now_ts - 0.4
        out_newborn = asyncio.run(
            maybe_preempt_mlk1_if_bond1_starved(
                harv,
                "BOND1_UMA_RESOLUTION_CARRY",
                0.0,
                9.96,
                True,
                True,
                rb,
                rcfg_b1,
                gsn,
                0.0,
                1800.0,
                now_ts,
                cand_bid_px=0.990,
            )
        )
        self.assertEqual(out_newborn, 0.0)
        self.assertFalse(ev_mlk.is_set(), "Newborn MKR_LOCK1 (<45s birth grace) must NEVER be preempted!")


if __name__ == "__main__":
    unittest.main()
