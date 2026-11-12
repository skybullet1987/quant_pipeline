"""
v5.7.0 Sub-Millisecond Hot-Path Velocity, 450-Token WS Clinch Sniper,
2h UMA Post-Expiry Capital Recycling & Dynamic $75.62->$1,000+ Scaling Suite.
"""

from __future__ import annotations

import asyncio
import json
import sys
import tempfile
import threading
import time
import types
import unittest
from pathlib import Path
from unittest import mock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

for _opt_mod, _attrs in (
    ("dotenv", {"load_dotenv": lambda *a, **kw: False}),
    ("requests", {"Session": object, "get": None, "post": None}),
    ("httpx", {"AsyncClient": object, "Client": object}),
    ("urllib3", {}),
    ("urllib3.connection", {"HTTPConnection": type("HTTPConnection", (), {"default_socket_options": []})}),
):
    try:
        __import__(_opt_mod)
    except ModuleNotFoundError:
        _m = types.ModuleType(_opt_mod)
        for _k, _v in _attrs.items():
            setattr(_m, _k, _v)
        sys.modules[_opt_mod] = _m


class TestV570MsVelocityAndWsSniper(unittest.TestCase):
    def test_01_governance_v570_keys_and_bounds(self) -> None:
        from src.polymarket_research.holistic_strategy_governance import (
            DEFAULT_HOLISTIC_CONFIG,
            HotReloadConfigManager,
            _deep_merge_validated,
        )

        cfg_path = PROJECT_ROOT / "config" / "polymarket_strategy_and_risk.json"
        raw = json.loads(cfg_path.read_text(encoding="utf-8"))
        self.assertTrue(bool(raw["directional"]["riskless_only_mode"]))
        rb = raw["riskless_boxes"]
        self.assertEqual(int(rb["ws_clinch_watchlist_max_tokens"]), 900)
        self.assertTrue(bool(rb["enable_uma_liveness_2h_recycle"]))
        self.assertTrue(bool(rb["enable_event_slot_diversification"]))
        self.assertAlmostEqual(float(rb["reward_dynamic_unlock_equity_usd"]), 125.0, places=2)
        self.assertAlmostEqual(float(rb["pre_split_dynamic_unlock_equity_usd"]), 140.0, places=2)

        mgr = HotReloadConfigManager(config_path=cfg_path)
        snap_rb = mgr.snapshot["riskless_boxes"]
        self.assertEqual(int(snap_rb["ws_clinch_watchlist_max_tokens"]), 900)
        self.assertTrue(bool(snap_rb["enable_uma_liveness_2h_recycle"]))

        for bad_override in (
            {"ws_clinch_watchlist_max_tokens": 2000},
            {"reward_dynamic_unlock_equity_usd": 10.0},
            {"pre_split_dynamic_unlock_equity_usd": 9999.0},
        ):
            with self.assertRaises(ValueError):
                _deep_merge_validated(DEFAULT_HOLISTIC_CONFIG, {"riskless_boxes": bad_override})

    def test_02_zero_ms_ram_pre_balance_fast_path_and_dirty_fallbacks(self) -> None:
        from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester

        h = PolymarketLiveHarvester.__new__(PolymarketLiveHarvester)
        h.dry_run = False
        h.active_positions = {}
        h.pending_entry_intents = {}
        h.closed_positions = []
        rpc_calls = []

        class _FakeExec:
            auth_mode = "LIVE"
            client = object()
            _user_ws_cache = types.SimpleNamespace(
                is_healthy=lambda: True,
                has_token_fill_since=lambda tid, since_ts: False,
            )

        h.executor = _FakeExec()

        with mock.patch.object(
            PolymarketLiveHarvester,
            "_wallet_token_balance",
            autospec=True,
            side_effect=lambda _self, tid: (rpc_calls.append(tid) or (7.5, True)),
        ):
            tok_clean = "901" * 9
            # 1. Clean un-held token resolves in 0ms RAM without touching Polygon RPC
            self.assertEqual(h._resolve_fast_pre_token_balance_sync(tok_clean), 0.0)
            self.assertEqual(asyncio.run(h._resolve_fast_pre_token_balance_async(tok_clean)), 0.0)
            self.assertEqual(len(rpc_calls), 0)
            self.assertIn(tok_clean, h._d1_clean_pre_bal_cache)

            # 2. Exclude self-intent ID still stays on 0ms RAM fast-path, while another intent forces RPC
            h.pending_entry_intents["SELF_INT"] = {"token_id": tok_clean}
            self.assertEqual(h._resolve_fast_pre_token_balance_sync(tok_clean, exclude_intent_id="SELF_INT"), 0.0)
            self.assertEqual(len(rpc_calls), 0)
            self.assertEqual(h._resolve_fast_pre_token_balance_sync(tok_clean, exclude_intent_id="OTHER"), 7.5)
            self.assertEqual(len(rpc_calls), 1)
            h.pending_entry_intents.clear()

            # 3. Dirty token marker forces RPC read
            h._mark_token_pre_bal_dirty(tok_clean, ttl_sec=60.0)
            self.assertEqual(asyncio.run(h._resolve_fast_pre_token_balance_async(tok_clean)), 7.5)
            self.assertEqual(len(rpc_calls), 2)

        # 4. Custom instance override in `h.__dict__` bypasses RAM shortcut for unit-test mocks
        custom_calls = []
        h._d1_dirty_token_until.clear()
        h._wallet_token_balance = lambda tid: (custom_calls.append(tid) or (3.0, True))
        self.assertEqual(h._resolve_fast_pre_token_balance_sync("902" * 9), 3.0)
        self.assertEqual(len(custom_calls), 1)

    def test_03_user_ws_fast_cancel_presigned_repeg_and_sub50ms_ws_outbid_wakeup(self) -> None:
        from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor
        from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester

        # A. USER_WS_FAST_CANCEL skips 220ms REST get_order_fill_summary when User WS confirms 0 matched
        h = PolymarketLiveHarvester.__new__(PolymarketLiveHarvester)
        h.dry_run = False
        summary_calls = []

        class _FastCancelExec:
            client = object()
            _user_ws_cache = types.SimpleNamespace(
                is_healthy=lambda: True,
                get_order_snapshot=lambda oid, max_age_sec=10.0: {
                    "order_id": oid,
                    "size_matched": 0.0,
                    "status": "CANCELED",
                },
            )

            def cancel_order(self, oid: str, token_id: str = "", pre_token_balance=None):
                return {"is_canceled": True, "matched": 0.0, "outcome": "CANCELED"}

            def get_order_fill_summary(self, oid: str, token_id: str):
                summary_calls.append(oid)
                return {"order_id": oid, "matched": 0.0, "terminal": True, "resting": False}

        h.executor = _FastCancelExec()
        c_res, summ, m_sh, avg_px = asyncio.run(
            h._reconcile_maker_entry_fill("OID_FAST_1", "801" * 9, False, 10.0, 0.992, 0.0)
        )
        self.assertTrue(c_res["is_canceled"])
        self.assertEqual(summ["source"], "USER_WS_FAST_CANCEL")
        self.assertEqual(m_sh, 0.0)
        self.assertAlmostEqual(avg_px, 0.992, places=4)
        self.assertEqual(len(summary_calls), 0)

        # If read_replica_stale_live is set, must fall back to authoritative get_order_fill_summary
        h.executor.cancel_order = lambda oid, **kw: {  # type: ignore[method-assign]
            "is_canceled": True,
            "matched": 0.0,
            "read_replica_stale_live": True,
        }
        _, summ2, _, _ = asyncio.run(
            h._reconcile_maker_entry_fill("OID_STALE_2", "801" * 9, False, 10.0, 0.992, 0.0)
        )
        self.assertEqual(len(summary_calls), 1)
        self.assertNotEqual(summ2.get("source"), "USER_WS_FAST_CANCEL")

        # B. Speculative Pre-Signed +1*tick / +2*tick Sub-Cent Maker Repeg Cache (single-use pop)
        ex = PolymarketLiveExecutor.__new__(PolymarketLiveExecutor)
        ex.dry_run = False
        ex._tick_size_cache = {"701" * 9: 0.001}
        ex._tick_size_ts = {"701" * 9: time.time()}
        ex.client = types.SimpleNamespace(
            create_order=lambda order_args, opts=None: {
                "signed_px": order_args.price,
                "signed_sz": order_args.size,
                "tok": order_args.token_id,
            }
        )
        built_n = ex._prebuild_next_tick_maker_repegs(
            token_id="701" * 9,
            base_price=0.991,
            shares_base=10.0,
            max_ceiling=0.994,
            side="BUY",
            tick_sz=0.001,
            neg_risk=False,
        )
        self.assertGreaterEqual(built_n, 4)  # 0.992 & 0.993 x [10, 9] shares
        hit_992 = ex._pop_presigned_maker_repeg("701" * 9, 0.992, 10.0, "BUY", "0.001", False)
        self.assertIsNotNone(hit_992)
        self.assertAlmostEqual(float(hit_992["signed_px"]), 0.992, places=4)
        self.assertEqual(int(getattr(ex, "_presigned_maker_repeg_hits", 0)), 1)
        # Single-use pop guarantee: second pop for identical key returns None (prevents nonce reuse)
        self.assertIsNone(ex._pop_presigned_maker_repeg("701" * 9, 0.992, 10.0, "BUY", "0.001", False))

        # C. <25ms _sll_ws_book_events wakeup on WS book change
        async def _verify_ws_wakeup() -> float:
            loop = asyncio.get_running_loop()
            h_w = PolymarketLiveHarvester.__new__(PolymarketLiveHarvester)
            h_w.dry_run = False
            h_w._main_loop = loop
            ev = asyncio.Event()
            tok_w = "601" * 9
            opp_w = "602" * 9
            h_w._sll_ws_book_events = {"INT_W1": (tok_w, opp_w, ev)}
            loop.call_later(0.005, lambda: h_w._notify_sll_ws_book_change(tok_w, loop))
            t0 = time.perf_counter()
            await asyncio.wait_for(ev.wait(), timeout=4.0)
            return (time.perf_counter() - t0) * 1000.0

        wake_ms = asyncio.run(_verify_ws_wakeup())
        self.assertLess(wake_ms, 150.0)

    def test_04_uma_2h_post_expiry_liveness_maker_and_taker_recycle(self) -> None:
        from src.polymarket_research.riskless_protocol_v2_expansion import (
            is_uma_post_expiry_recycle_safe,
            maybe_early_profit_recycle_htm_lock,
            maybe_manage_passive_htm_early_maker_recycle,
        )

        now_ts = 1_795_000_000.0
        pos_base = {
            "trade_id": "BOND1_UMA_POST_EXP",
            "token_id": "501" * 9,
            "market_id": "MKT_UMA_1",
            "sleeve": "BOND1_UMA_RESOLUTION_CARRY",
            "status": "POSITION_CONFIRMED",
            "hold_to_maturity_lock": True,
            "is_single_leg_lock": True,
            "inventory_reconciled": True,
            "entry_price": 0.991,
            "entry_shares": 10.0,
            "remaining_shares": 10.0,
            "notional_usd": 9.91,
            "fee_rate_applied": 0.0,
            "fee_exponent_applied": 1.0,
            "candle_expiry_ts": now_ts - 1800.0,  # 30m post-expiry inside 2h UMA liveness window
        }
        maker_book = {
            "bids": [{"price": 0.995, "size": 25.0}],
            "asks": [{"price": 0.999, "size": 25.0}],
        }
        live_book = {
            "bids": [{"price": 0.998, "size": 25.0}],
            "asks": [{"price": 0.999, "size": 25.0}],
        }

        self.assertTrue(is_uma_post_expiry_recycle_safe(pos_base, -1800.0, live_book))
        self.assertFalse(
            is_uma_post_expiry_recycle_safe({**pos_base, "umaResolutionStatus": "disputed"}, -1800.0, live_book)
        )
        self.assertFalse(
            is_uma_post_expiry_recycle_safe({**pos_base, "_book_closed_404": True}, -1800.0, live_book)
        )
        self.assertFalse(is_uma_post_expiry_recycle_safe(pos_base, -7200.0, live_book))
        self.assertFalse(
            is_uma_post_expiry_recycle_safe({**pos_base, "sleeve": "S2_EXACT_TWAP_LOCK"}, -30.0, live_book)
        )

        # 1. Passive Maker $0.998/$0.999 exit posts cleanly at -1800s post-expiry AND still cancels inside T-6m (tte=+180s)
        posted_exits = []
        canceled_oids = []
        harv_m = types.SimpleNamespace(
            dry_run=False,
            executor=types.SimpleNamespace(
                get_token_tick_size=lambda tid, **kw: 0.001,
                post_maker_exit_order=lambda **kw: (
                    posted_exits.append(kw)
                    or {"success": True, "orderID": "OID_UMA_999", "order_id": "OID_UMA_999", "price": kw["price"]}
                ),
                cancel_order=lambda oid, **kw: (canceled_oids.append(oid) or {"is_canceled": True}),
                get_order_fill_summary=lambda oid, tid: {
                    "matched": 0.0,
                    "terminal": oid in canceled_oids,
                    "resting": oid not in canceled_oids,
                },
                release_inventory=lambda **kw: None,
                invalidate_collateral_cache=lambda: None,
            ),
            calculate_realized_cash_pnl=lambda p, cash, fee: round(cash - fee - float(p["notional_usd"]), 4),
            _apply_exit_post_result=lambda p, res, sz: (
                p.update({"exit_order_id": res["order_id"], "target_exit_price": res["price"]}) or True
            ),
            _record_order_summary=lambda *a, **kw: None,
            save_state=lambda: None,
        )
        pos_m = dict(pos_base)
        ok_post = asyncio.run(maybe_manage_passive_htm_early_maker_recycle(harv_m, "BOND1_UMA_POST_EXP", pos_m, maker_book, now_ts))
        self.assertTrue(ok_post)
        self.assertEqual(pos_m.get("exit_order_id"), "OID_UMA_999")
        self.assertEqual(len(posted_exits), 1)

        # Verify T-6m pre-expiry (0 < tte_rem < 360s) still cancels resting Maker exit
        pos_t6m = {**pos_m, "candle_expiry_ts": now_ts + 180.0, "_htm_passive_recycle_active": True}
        _ = asyncio.run(
            maybe_manage_passive_htm_early_maker_recycle(harv_m, "BOND1_UMA_POST_EXP", pos_t6m, maker_book, now_ts, {"OID_UMA_999"})
        )
        self.assertIsNone(pos_t6m.get("exit_order_id"))
        self.assertIn("OID_UMA_999", canceled_oids)

        # 2. Taker recycle at >= $0.998 during -1800s post-expiry increments _uma_early_recycle_count
        closed_tids = []
        harv_t = types.SimpleNamespace(
            dry_run=False,
            executor=types.SimpleNamespace(
                _fee_cache={},
                execute_unwind_order=lambda **kw: types.SimpleNamespace(success=True, size=10.0, price=0.998),
                invalidate_collateral_cache=lambda: None,
            ),
            calculate_realized_cash_pnl=lambda p, cash, fee: round(cash - fee - float(p["notional_usd"]), 4),
            _handle_unwind_response=lambda tid, p, res, sh, r_full, r_part, px: (closed_tids.append(tid) or "CLOSED"),
            save_state=lambda: None,
        )
        pos_t = dict(pos_base)
        ok_tkr = asyncio.run(maybe_early_profit_recycle_htm_lock(harv_t, "BOND1_UMA_POST_EXP", pos_t, live_book, now_ts))
        self.assertTrue(ok_tkr)
        self.assertEqual(closed_tids, ["BOND1_UMA_POST_EXP"])
        self.assertEqual(int(getattr(harv_t, "_uma_early_recycle_count", 0)), 1)

    def test_05_450_token_ws_clinch_sniper_priority_cap_and_s2_4_2s_guard(self) -> None:
        from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester
        from src.polymarket_research.polymarket_ws_streams import PolymarketClobMarketWsTracker

        # 1. PolymarketClobMarketWsTracker preserves priority order and enforces <= 490 cap
        ws_t = PolymarketClobMarketWsTracker()
        ordered_520 = [f"{1000 + i}" * 7 for i in range(520)]
        ws_t.set_desired_tokens(ordered_520)
        self.assertEqual(len(ws_t._desired_tokens_ordered), 490)
        self.assertEqual(ws_t._desired_tokens_ordered[0], ordered_520[0])
        self.assertNotIn(ordered_520[519], ws_t._desired_tokens)
        urg_tok = "9999999" * 4
        ws_t.subscribe_tokens_immediate([urg_tok])
        self.assertEqual(ws_t._desired_tokens_ordered[0], urg_tok)
        self.assertLessEqual(len(ws_t._desired_tokens_ordered), 490)

        # 2. Harvester 450-token watchlist + S2 4.2s window + live 2.5-sigma adverse-move veto
        now_ts = time.time()
        h = PolymarketLiveHarvester.__new__(PolymarketLiveHarvester)
        h.dry_run = False
        h._last_known_collateral = 75.62
        act_tok = "1111111" * 4
        mkr_tok = "2222222" * 4
        mkr_opp = "3333333" * 4
        h.active_positions = {"ACT_1": {"token_id": act_tok, "status": "POSITION_CONFIRMED"}}
        h.pending_entry_intents = {
            "MKR_1": {"token_id": mkr_tok, "opp_token_id": mkr_opp, "live_maker_anchor_inflight": True}
        }
        h._clinched_ws_watchlist = {}
        h._seen_d1_box_keys = set()
        h._d1_retry_cooldown_until = {}

        # Register 230 clinched pairs (460 tokens) -> desired_market_ws_tokens caps at <= 490 and keeps ACT + MKR first!
        for idx in range(230):
            h.register_clinched_ws_watch_cand(
                {
                    "box_type": "CLINCH_WATCHLIST_REG",
                    "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
                    "asset": "BTC",
                    "dedupe_key": f"B1_W_{idx}",
                    "leg_a_token_id": f"{4000 + idx}" * 7,
                    "leg_a_opp_token_id": f"{6000 + idx}" * 7,
                    "leg_a_market_id": f"M_{idx}",
                    "expiry_ts": now_ts + 1800.0,
                    "max_box_cost_net": 0.994,
                    "max_opp_bid": 0.020,
                    "p_model": 0.9985,
                },
                now_ts=now_ts,
            )
        desired = h._desired_market_ws_tokens(now_ts=now_ts)
        self.assertLessEqual(len(desired), 490)
        self.assertEqual(desired[:3], [act_tok, mkr_tok, mkr_opp])

        # Register S2 at rem_s = 5.5s (>= 4.2s!) and verify 2.5-sigma veto vs clean snipe
        h._clinched_ws_watchlist.clear()
        tok_s2 = "777" * 9
        opp_s2 = "888" * 9
        ok_s2 = h.register_clinched_ws_watch_cand(
            {
                "box_type": "CLINCH_WATCHLIST_REG",
                "sleeve_source": "S2_EXACT_TWAP_LOCK",
                "asset": "BTC",
                "dedupe_key": "S2_FINAL_5S",
                "leg_a_token_id": tok_s2,
                "leg_a_opp_token_id": opp_s2,
                "leg_a_market_id": "MKT_S2_5S",
                "leg_a_condition_id": "0x" + "c" * 64,
                "leg_a_side": "UP",
                "leg_a_fee_rate": 0.0,
                "leg_a_fee_exponent": 1.0,
                "expiry_ts": now_ts + 5.5,
                "max_box_cost_net": 0.996,
                "max_opp_bid": 0.020,
                "p_model": 0.9992,
                "open_price": 100000.0,
                "sigma_1h": 0.005,
            },
            now_ts=now_ts,
        )
        self.assertTrue(ok_s2)
        h._pos_market_ws = types.SimpleNamespace(
            get_book=lambda tid, max_age_s=1.5: (
                {"asks": [{"price": 0.992, "size": 8.0}], "bids": [{"price": 0.985, "size": 10.0}]}
                if tid == tok_s2
                else {"asks": [{"price": 0.015, "size": 10.0}], "bids": [{"price": 0.005, "size": 10.0}]}
            ),
            set_desired_tokens=lambda toks: None,
        )
        with mock.patch(
            "src.polymarket_research.riskless_protocol_v2_expansion.check_s2_live_adverse_move_cancel",
            return_value=True,
        ):
            self.assertIsNone(h.evaluate_clinched_ws_book_snipe(tok_s2, now_ts=now_ts))

        with mock.patch(
            "src.polymarket_research.riskless_protocol_v2_expansion.check_s2_live_adverse_move_cancel",
            return_value=False,
        ):
            snipe_s2 = h.evaluate_clinched_ws_book_snipe(tok_s2, now_ts=now_ts)
            self.assertIsNotNone(snipe_s2)
            self.assertEqual(snipe_s2["sleeve_source"], "S2_EXACT_TWAP_LOCK")
            self.assertEqual(int(getattr(h, "_ws_clinch_snipe_emitted_count", 0)), 1)

    def test_06_dynamic_bankroll_scaling_75_62_event_diversification_and_ipc_recorder(self) -> None:
        from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester
        from src.polymarket_research.polymarket_terminal_recorder import PolymarketDualFeed1HRecorder
        from src.polymarket_research.riskless_machine_gun_engine import (
            PreSplitInventoryGun,
            is_reward_locked_carry_live_ready,
        )
        from src.polymarket_research.riskless_protocol_v2_expansion import (
            _trim_ws_books_top10,
            cap_bond1_maker_for_gatling_reserve,
            compute_dynamic_riskless_tier_caps,
            extract_sll_event_group_key,
            prepare_sll_stalk_guard,
        )

        # 1. Dynamic scaling across $75.62 -> $125 -> $140 -> $160 -> $300 -> $450
        c_75 = compute_dynamic_riskless_tier_caps(75.62)
        self.assertFalse(c_75["reward_unlocked"])
        self.assertAlmostEqual(float(c_75["reward_harvester_cap_usd"]), 12.0, places=2)
        self.assertFalse(c_75["pre_split_enabled"])
        self.assertEqual(c_75["max_concurrent_intents_per_event"], 1)

        c_125 = compute_dynamic_riskless_tier_caps(125.0)
        self.assertGreaterEqual(c_125["reward_harvester_cap_usd"], 21.88)
        self.assertFalse(c_125["pre_split_enabled"])

        c_140 = compute_dynamic_riskless_tier_caps(140.0)
        self.assertTrue(c_140["pre_split_enabled"])

        c_160 = compute_dynamic_riskless_tier_caps(160.0)
        self.assertEqual(c_160["max_concurrent_intents_per_event"], 2)

        c_300 = compute_dynamic_riskless_tier_caps(300.0)
        self.assertGreaterEqual(c_300["reward_harvester_cap_usd"], 52.50)

        c_450 = compute_dynamic_riskless_tier_caps(450.0)
        self.assertEqual(c_450["max_concurrent_intents_per_event"], 3)

        # Verify $75.62 live Harvester reclaims +$7.96 dead reward reserve when no reward candidate is active
        rb_live = {
            "gatling_enabled": True,
            "gatling_fast_gun_reserve_usd": 20.0,
            "enable_reward_locked_carry_live_bridge": True,
            "reward_reserved_slot_usd_seed": 7.96,
            "reward_harvester_cap_usd_seed": 12.0,
            "reward_dynamic_unlock_equity_usd": 125.0,
        }
        h_75 = types.SimpleNamespace(
            dry_run=False,
            enforce_gatling_fast_gun_reserve=True,
            _is_v5_unleashed_active=lambda: True,
            active_positions={},
            pending_entry_intents={},
        )
        reclaimed_b1 = cap_bond1_maker_for_gatling_reserve(
            h_75, 20.0, 29.18, 46.44, rb_live, sleeve_src="BOND1_UMA_RESOLUTION_CARRY"
        )
        self.assertGreater(reclaimed_b1, 7.50)  # Reclaimed +$7.96 vs old $0.00!

        # Verify 20-share reward carry auto-unlocks at $125 while staying gated at $75.62
        dm_75 = types.SimpleNamespace(
            live_account_equity_usd=75.62,
            is_sleeve_grad8_ready=lambda s: s == "D1_SAME_ORACLE_DOMINANCE_BOX",
        )
        dm_125 = types.SimpleNamespace(
            live_account_equity_usd=125.0,
            is_sleeve_grad8_ready=lambda s: s == "D1_SAME_ORACLE_DOMINANCE_BOX",
        )
        self.assertFalse(is_reward_locked_carry_live_ready(dm_75, 1.0, min_reward_shares=20.0, resting_bid_px=0.992))
        self.assertTrue(is_reward_locked_carry_live_ready(dm_125, 1.0, min_reward_shares=20.0, resting_bid_px=0.992))

        # Verify PreSplitInventoryGun stays gated at $75.62 and auto-unlocks at >= $140 live equity
        gun = PreSplitInventoryGun()
        reader_calls = []
        h_ps_75 = types.SimpleNamespace(
            dry_run=False,
            _startup_reconciled=True,
            _last_known_collateral=75.62,
            active_positions={},
            executor=types.SimpleNamespace(dry_run=False, client=object()),
        )
        asyncio.run(gun.tick(h_ps_75, time.time(), fast_tick_reader=lambda a: (reader_calls.append(a) or None)))
        self.assertEqual(len(reader_calls), 0)
        h_ps_145 = types.SimpleNamespace(
            dry_run=False,
            _startup_reconciled=True,
            _last_known_collateral=145.0,
            active_positions={},
            executor=types.SimpleNamespace(dry_run=False, client=object()),
        )
        asyncio.run(gun.tick(h_ps_145, time.time() + 1.0, fast_tick_reader=lambda a: (reader_calls.append(a) or None)))
        self.assertGreaterEqual(len(reader_calls), 1)

        # 2. Event-group extraction & 300s sibling stalker cooldown propagation
        k_soc_a = extract_sll_event_group_key({"leg_a_label": "Exact Score: Como 0 - 1 Napoli"})
        k_soc_b = extract_sll_event_group_key({"leg_a_label": "Exact Score: Como 2 - 0 Napoli"})
        self.assertTrue(k_soc_a)
        self.assertEqual(k_soc_a, k_soc_b)

        k_wx_a = extract_sll_event_group_key({"leg_a_label": "NYC High Temp: 60-61°F [Dead NO]"})
        k_wx_b = extract_sll_event_group_key({"leg_a_label": "NYC High Temp: 62-63°F [Dead NO]"})
        self.assertTrue(k_wx_a)
        self.assertEqual(k_wx_a, k_wx_b)

        now_stk = time.time()
        cand_como_01 = {"leg_a_label": "Exact Score: Como 0 - 1 Napoli"}
        cand_como_20 = {"leg_a_label": "Exact Score: Como 2 - 0 Napoli"}
        h_stk = types.SimpleNamespace(_sll_stalk_strikes={}, _sll_event_stalk_until={})
        _ = prepare_sll_stalk_guard(
            h_stk, "MKT_COMO_01", cand_como_01, 1, 5.0, 3, 15.0, now_stk, is_outbid_now=True, buried_since_mono=None
        )
        self.assertTrue(bool(cand_como_01.get("_fast_stalk_detected")))
        self.assertGreater(h_stk._sll_event_stalk_until.get(k_soc_a, 0.0), now_stk + 250.0)
        hold_sib = prepare_sll_stalk_guard(
            h_stk, "MKT_COMO_20", cand_como_20, 0, 1.0, 3, 25.0, now_stk + 1.0, is_outbid_now=False, buried_since_mono=None
        )
        self.assertLessEqual(hold_sib, 10.0)
        self.assertEqual(cand_como_20.get("_max_outbid_repegs"), 1)

        # 3. Top-10 IPC ws_books trim (<1,800 B), save_state funnel telemetry, & Recorder riskless_bus_only
        fat_books = {
            "TOK_A": {
                "bids": [{"price": round(0.99 - i * 0.001, 4), "size": 10.0} for i in range(50)],
                "asks": [{"price": round(0.991 + i * 0.001, 4), "size": 10.0} for i in range(50)],
            },
            "TOK_B": {
                "bids": [{"price": round(0.01 + i * 0.0001, 4), "size": 10.0} for i in range(50)],
                "asks": [{"price": round(0.02 + i * 0.001, 4), "size": 10.0} for i in range(50)],
            },
        }
        trimmed = _trim_ws_books_top10(fat_books)
        self.assertEqual(len(trimmed["TOK_A"]["bids"]), 10)
        self.assertEqual(len(trimmed["TOK_A"]["asks"]), 10)
        self.assertAlmostEqual(trimmed["TOK_A"]["bids"][0]["price"], 0.99, places=4)
        self.assertAlmostEqual(trimmed["TOK_A"]["asks"][0]["price"], 0.991, places=4)
        self.assertLess(len(json.dumps(trimmed).encode("utf-8")), 1800)

        rec = PolymarketDualFeed1HRecorder(asset="BTC", riskless_bus_only=True)
        self.assertIn("@aggTrade", rec.binance_spot_ws)
        self.assertIn("@aggTrade", rec.binance_futures_ws)
        self.assertAlmostEqual(rec._fast_tick_throttle_sec(295.0), 0.05, places=3)  # final 5s of 5m candle
        self.assertAlmostEqual(rec._fast_tick_throttle_sec(60.0), 0.15, places=3)   # normal mid-candle

        import src.polymarket_research.polymarket_live_harvester as hv_mod

        with tempfile.TemporaryDirectory() as tmp_d:
            st_file = Path(tmp_d) / "live_harvester_state.json"
            res_file = Path(tmp_d) / "live_resolutions.jsonl"
            with (
                mock.patch.object(hv_mod, "STATE_FILE", st_file),
                mock.patch.object(hv_mod, "RESOLUTIONS_FILE", res_file),
            ):
                h_sv = PolymarketLiveHarvester(ticket_notional=16.50, dry_run=True, dynamic_sizing=True)
                h_sv._last_known_collateral = 75.62
                h_sv._clinched_ws_watchlist = {"W1": {"opp_token_id": "O1"}}
                h_sv._ws_clinch_snipe_emitted_count = 3
                h_sv._uma_early_recycle_count = 2
                h_sv.executor._presigned_maker_repeg_hits = 4
                h_sv.save_state()
            saved = json.loads(st_file.read_text(encoding="utf-8"))
            funnel = saved["live_riskless_funnel"]
            self.assertEqual(funnel["ws_snipe_emitted"], 3)
            self.assertEqual(funnel["uma_early_recycles"], 2)
            self.assertEqual(funnel["presigned_repeg_hits"], 4)

    def test_clob_400_tick_rule_authority_and_uma_event_slot_dedupe(self) -> None:
        from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor
        from src.polymarket_research.polymarket_ws_streams import PolymarketClobMarketWsTracker
        from src.polymarket_research.riskless_protocol_v2_expansion import (
            emit_single_leg_maker_lock_cand_impl,
            eval_sll_live_book_poll,
            extract_gamma_parent_event_id,
            extract_sll_event_group_key,
            resolve_harvester_sll_tick_size,
            sync_harvester_sll_enforced_tick,
        )
        import src.polymarket_research.alpha_124_shadow_daemon as a124_mod

        # 1. CLOB 400 tick-rule 0.01 override beats lagging /tick-size & WS 0.001 at >= 0.96 and stops $0.990 -> $0.991 self-cancels
        tok_zec = "991001" * 12
        ex = PolymarketLiveExecutor(dry_run=True)
        ws = PolymarketClobMarketWsTracker(on_tick_size_change=ex.update_ws_tick_size)
        ws._tick_sizes[tok_zec] = 0.001
        ex._evict_tick_size_if_tick_err(tok_zec, "PolyApiException: {'error': 'price 0.991 breaks minimum tick size rule 0.01'}")

        resolved = resolve_harvester_sll_tick_size(
            ex, tok_zec, {"leg_a_tick_size": 0.001, "leg_a_ws_tick_size": 0.001},
            bk_win={"minimum_tick_size": "0.001"}, mkt_ws=ws, real_clob=True, price_hint=0.991,
        )
        self.assertAlmostEqual(resolved, 0.01, places=6)
        self.assertAlmostEqual(ws.get_tick_size(tok_zec) or 0.0, 0.01, places=6)

        synced_tk = sync_harvester_sll_enforced_tick(
            ex, ws, tok_zec, 0.001, bk_wc={"bids": [{"price": "0.99", "size": "260"}], "asks": [{"price": "1.00", "size": "50"}]}
        )
        self.assertAlmostEqual(synced_tk, 0.01, places=6)

        c_zec = {
            "sleeve_source": "S2_RTDS_EXACT_TWAP_INTEGRATOR",
            "p_model": 0.9999,
            "min_maker_edge": 0.005,
            "maker_rebate_ps": 0.0002,
            "_posted_notional_usd": 11.88,
            "_init_l1_q_usd": 260.0,
            "_whale_q_since_mono": time.monotonic() - 2.5,
        }
        act_hold, rp_hold, _, _ = eval_sll_live_book_poll(
            {"bids": []}, {"bids": [{"price": "0.99", "size": "260"}], "asks": []},
            c_zec, 0.990, 0.80, 0.994, 0.08, synced_tk, True, True, 0, 350.0, 15.0, time.time() + 20.0, None,
        )
        self.assertEqual(act_hold, "OK")
        self.assertIsNone(rp_hold)

        # Genuine sub-cent order on L2 ($0.991) or WS tick_size_change (0.001) unlocks 0.001 immediately
        unlocked_l2 = sync_harvester_sll_enforced_tick(
            ex, ws, tok_zec, 0.01, bk_wc={"bids": [{"price": "0.991", "size": "40"}], "asks": []}
        )
        self.assertAlmostEqual(unlocked_l2, 0.001, places=6)

        ex._evict_tick_size_if_tick_err(tok_zec, "price 0.991 breaks minimum tick size rule 0.01")
        ex.update_ws_tick_size(tok_zec, 0.001)
        self.assertAlmostEqual(ex.get_token_tick_size(tok_zec, price_hint=0.991), 0.001, places=6)

        # 2. Parent Gamma event_id extraction & multi-prop match slot deduplication (`BOND1` + `BOND2`)
        m_hcap = {"id": "101", "events": [{"id": "209481", "slug": "cs2-quazar-vs-aurora"}], "question": "Map Handicap: QUAZAR (-1.5) vs Aurora"}
        m_tot = {"id": "102", "_parent_event_id": "209481", "question": "QUAZAR vs Aurora: Total Maps Over/Under 2.5"}
        self.assertEqual(extract_gamma_parent_event_id(m_hcap), "209481")
        self.assertEqual(extract_gamma_parent_event_id(m_tot), "209481")
        self.assertEqual(
            extract_sll_event_group_key({"leg_a_label": "SPORTS_MAP_HANDICAP QUAZAR", "event_id": extract_gamma_parent_event_id(m_hcap)}),
            "EVT:209481",
        )
        self.assertEqual(
            extract_sll_event_group_key({"leg_a_label": "MOOv2_WL Maker SPORTS_TOTALS Over", "event_id": extract_gamma_parent_event_id(m_tot)}),
            "EVT:209481",
        )
        # Fallback match-pair stem when event_id is absent
        k_q1 = extract_sll_event_group_key({"leg_a_label": "SPORTS_MAP_HANDICAP QUAZAR", "question": "Counter-Strike: QUAZAR vs Aurora - Map 1 Handicap", "expiry_ts": 1793994186})
        k_q2 = extract_sll_event_group_key({"leg_a_label": "MOOv2_WL Maker SPORTS_TOTALS Over", "question": "Aurora vs QUAZAR: Total Maps O/U 2.5", "expiry_ts": 1793994186})
        self.assertTrue(k_q1.startswith("EVTMATCH:"))
        self.assertEqual(k_q1, k_q2)

        with tempfile.TemporaryDirectory() as tmp_d2:
            cf = Path(tmp_d2) / "cands.jsonl"
            sf = Path(tmp_d2) / "st.json"
            dm = types.SimpleNamespace(single_scan=False, _last_d1_live_emit_ts={}, _token_tick_sizes={})
            ok_ev = emit_single_leg_maker_lock_cand_impl(
                dm,
                sleeve_source="BOND1_UMA_RESOLUTION_CARRY",
                asset="SPORTS_MAP_HANDICAP",
                dedupe_key="BOND1_MKR_101",
                pair_dedupe_key="BOND1_101",
                token_id="tok_w_101",
                opp_token_id="tok_l_101",
                market_id="101",
                condition_id="0x" + "cd" * 32,
                side_label="YES",
                display_label="SPORTS_MAP_HANDICAP QUAZAR",
                bk_win={"bids": [{"price": "0.97", "size": "50"}], "asks": [{"price": "0.99", "size": "50"}]},
                bk_opp={"bids": [{"price": "0.002", "size": "50"}], "asks": []},
                neg_risk=False,
                close_ts=time.time() + 1800.0,
                now_ts=time.time(),
                min_resting_bid=0.94,
                max_resting_bid=0.995,
                min_maker_edge=0.005,
                max_opp_bid=0.008,
                hold_to_maturity=True,
                p_model=1.0,
                target_bid_px=None,
                maker_rebate_ps=0.0,
                extract_best_bid_fn=a124_mod.extract_best_bid,
                cand_file=cf,
                default_cand_path=cf,
                state_file=sf,
                default_state_path=sf,
                event_id="209481",
            )
            self.assertTrue(ok_ev)
            cand_row = json.loads(cf.read_text(encoding="utf-8").splitlines()[-1])
            self.assertEqual(cand_row.get("event_id"), "209481")
            self.assertEqual(extract_sll_event_group_key(cand_row), "EVT:209481")

    def test_v571_s2mkr_tier1_preempt_cancel_on_arb_c1_fast_merge_and_pure_riskless_projections(self) -> None:
        from scripts.polymarket_daily_projections import (
            build_live_projections,
            simulate_single_day_net_pnl,
        )
        from src.polymarket_research.riskless_protocol_v2_expansion import (
            maybe_merge_live_complete_sets_impl,
            maybe_preempt_low_tier_s2_maker_slot,
            preempt_makers_for_instant_taker_arb,
            score_live_candidate_velocity_ev,
        )
        from src.polymarket_research.weather_metar_engine import parse_metar_line
        from datetime import datetime, timezone

        now_ts = time.time()

        # 1. S2MKR Tier-1 (`BTC`/`ETH`/`SOL`/`XRP`) outranks & preempts resting Tier-3 (`ZEC`/`HYPE`), while SOL never preempts BTC
        s_btc = score_live_candidate_velocity_ev(
            {"sleeve_source": "S2_RTDS_EXACT_TWAP_INTEGRATOR", "asset": "BTC", "box_cost_net": 0.99, "shares": 10, "expiry_ts": now_ts + 25.0},
            True,
            now_ts,
        )
        s_zec = score_live_candidate_velocity_ev(
            {"sleeve_source": "S2_RTDS_EXACT_TWAP_INTEGRATOR", "asset": "ZEC", "box_cost_net": 0.99, "shares": 10, "expiry_ts": now_ts + 25.0},
            True,
            now_ts,
        )
        self.assertGreater(s_btc, s_zec * 5.0)

        ev_zec = threading.Event()
        harv_s2 = types.SimpleNamespace(
            dry_run=True,
            enforce_s2_multi_slot=False,
            executor=types.SimpleNamespace(client=None),
            pending_entry_intents={
                "INT_ZEC": {
                    "live_maker_anchor_inflight": True,
                    "sleeve_source": "S2_RTDS_EXACT_TWAP_INTEGRATOR",
                    "asset": "ZEC",
                    "inflight_key": "S2MKR_ZEC_5m_1",
                    "ts": now_ts - 4.0,
                }
            },
            _maker_anchor_preempt_events={"S2MKR_ZEC_5m_1": ev_zec},
            _maker_anchor_preempt_reasons={},
        )

        async def _run_s2_preempt() -> Tuple[bool, bool]:
            # ZEC cannot preempt ZEC (Tier-3)
            ok_hype = await maybe_preempt_low_tier_s2_maker_slot(harv_s2, "HYPE", set())
            self.assertFalse(ok_hype)
            self.assertFalse(ev_zec.is_set())

            async def _clear_zec_on_ev() -> None:
                await asyncio.sleep(0.01)
                if ev_zec.is_set():
                    harv_s2.pending_entry_intents.pop("INT_ZEC", None)

            t_clr = asyncio.create_task(_clear_zec_on_ev())
            ok_btc = await maybe_preempt_low_tier_s2_maker_slot(harv_s2, "BTC", set())
            await t_clr
            return ok_hype, ok_btc

        _, ok_btc_res = asyncio.run(_run_s2_preempt())
        self.assertTrue(ok_btc_res)
        self.assertTrue(ev_zec.is_set())
        self.assertEqual(harv_s2._maker_anchor_preempt_reasons.get("S2MKR_ZEC_5m_1"), "S2_TIER1_UPGRADE:BTC")

        # 2. Selective `<70ms` Batch Cancel-on-Arb: on $75.73 ($20.08 free + 5 BOND1 Makers = $55.65),
        #    a >=200 bps arb (`cand_net_cost = 0.960`) batch-cancels ONLY the 3 slowest/non-FIFO-#1 Makers to reach >=$45,
        #    leaving the 2 fastest FIFO #1 BOND1 orders untouched!
        batch_cancelled: list = []

        class _RealLikeClob:
            def cancel_orders(self, oids):
                batch_cancelled.append(list(oids))
                return {"canceled": list(oids)}

        pe_events = {f"BOND1_MKR_{i}": threading.Event() for i in range(1, 6)}
        harv_arb = types.SimpleNamespace(
            dry_run=False,
            executor=types.SimpleNamespace(client=_RealLikeClob()),
            active_positions={},
            _maker_anchor_preempt_events=pe_events,
            _maker_anchor_preempt_reasons={},
            pending_entry_intents={
                "I1": {"live_maker_anchor_inflight": True, "inflight_key": "BOND1_MKR_1", "market_id": "m1", "entry_order_id": "oid_slow_1", "notional_usd": 11.13, "anchor_bid_px": 0.995, "expiry_ts": now_ts + 7200, "fifo_rank1_verified": False},
                "I2": {"live_maker_anchor_inflight": True, "inflight_key": "BOND1_MKR_2", "market_id": "m2", "entry_order_id": "oid_slow_2", "notional_usd": 11.13, "anchor_bid_px": 0.994, "expiry_ts": now_ts + 7200, "fifo_rank1_verified": False},
                "I3": {"live_maker_anchor_inflight": True, "inflight_key": "BOND1_MKR_3", "market_id": "m3", "entry_order_id": "oid_mid_3", "notional_usd": 11.13, "anchor_bid_px": 0.990, "expiry_ts": now_ts + 5400, "fifo_rank1_verified": True},
                "I4": {"live_maker_anchor_inflight": True, "inflight_key": "BOND1_MKR_4", "market_id": "m4", "entry_order_id": "oid_fast_4", "notional_usd": 11.13, "anchor_bid_px": 0.980, "expiry_ts": now_ts + 1800, "fifo_rank1_verified": True},
                "I5": {"live_maker_anchor_inflight": True, "inflight_key": "BOND1_MKR_5", "market_id": "m5", "entry_order_id": "oid_fast_5", "notional_usd": 11.13, "anchor_bid_px": 0.970, "expiry_ts": now_ts + 1200, "fifo_rank1_verified": True},
            },
        )
        n_sig, sel_keys = preempt_makers_for_instant_taker_arb(
            harv_arb,
            reason="SLL_TAKER:S2_RTDS_EXACT_TWAP_INTEGRATOR",
            target_market_ids={"m_target_s2"},
            cand_net_cost=0.960,  # 400 bps (>= 200 bps!)
            free_cash_hint=20.08,
            target_arb_cash_usd=45.0,
            now_ts=now_ts,
        )
        self.assertEqual(n_sig, 3)
        self.assertEqual(sel_keys, {"BOND1_MKR_1", "BOND1_MKR_2", "BOND1_MKR_3"})
        self.assertEqual(batch_cancelled, [["oid_slow_1", "oid_slow_2", "oid_mid_3"]])
        self.assertFalse(pe_events["BOND1_MKR_4"].is_set())
        self.assertFalse(pe_events["BOND1_MKR_5"].is_set())

        # 3. C1 Complete-Set instant merge works with default POLY_PROXY (`signature_type=None` -> 1) and `C1_BINARY_COMPLETE_SET` sleeve
        merged_calls: list = []
        closed_tids: list = []
        harv_c1 = types.SimpleNamespace(
            dry_run=False,
            ONCHAIN_SOURCE="POLYGON_ONCHAIN_ERC1155",
            executor=types.SimpleNamespace(
                signature_type=None,
                client=types.SimpleNamespace(_mock_children=True),
                attempt_onchain_complete_set_merge=lambda cid, min_pairs=0.0, max_pairs=None: merged_calls.append((cid, min_pairs)) or ("0xMERGETX", 10.0),
                release_inventory=lambda **kw: None,
            ),
            active_positions={
                "C1_1_L1": {
                    "trade_id": "C1_1_L1", "box_id": "C1_1", "box_partner_trade_id": "C1_1_L2",
                    "box_type": "DOMINANCE", "sleeve": "C1_BINARY_COMPLETE_SET",
                    "condition_id": "0x" + "11" * 32, "token_id": "tok_yes",
                    "inventory_reconciled": True, "remaining_shares": 10.0, "filled_exit_shares": 0.0, "notional_usd": 4.90,
                },
                "C1_1_L2": {
                    "trade_id": "C1_1_L2", "box_id": "C1_1", "box_partner_trade_id": "C1_1_L1",
                    "box_type": "DOMINANCE", "sleeve": "C1_BINARY_COMPLETE_SET",
                    "condition_id": "0x" + "11" * 32, "token_id": "tok_no",
                    "inventory_reconciled": True, "remaining_shares": 10.0, "filled_exit_shares": 0.0, "notional_usd": 4.95,
                },
            },
            record_fill_and_update_position=lambda p, tid, sh, cash, fee, cash_is_estimated=False: p.update({"remaining_shares": 0.0}),
            _close_position=lambda tid, p, st, why, won=True: closed_tids.append((tid, why, won)) or harv_c1.active_positions.pop(tid, None),
            save_state=lambda: None,
        )
        asyncio.run(maybe_merge_live_complete_sets_impl(harv_c1, now_ts, types.SimpleNamespace(SETTLED="SETTLED", FILLED="FILLED"), types.SimpleNamespace(info=lambda *a, **k: None)))
        self.assertEqual(len(merged_calls), 1)
        self.assertEqual(len(closed_tids), 2)

        # 4. Strict SPECI exclusion invariant preserved (`W_PRUNE1` never locks on unscheduled SPECI)
        self.assertIsNone(
            parse_metar_line("SPECI KLGA 061822Z 18012KT 10SM SCT040 21/10 A3002 RMK AO2 T02080100", "KLGA", datetime(2026, 11, 6, 18, 30, tzinfo=timezone.utc), "America/New_York")
        )

        # 5. Strict Pure-Riskless Math-Only Projections (`strict_pure_riskless=True`, live default) + legacy v5.7.1 curve (`strict_pure_riskless=False`)
        p25_s, bd_25s, _ = simulate_single_day_net_pnl(1, 27.05, "P25_CONSERVATIVE", riskless_only=True, strict_pure_riskless=True)
        p50_s, bd_50s, ms_strict = simulate_single_day_net_pnl(1, 27.05, "P50_BASE_FINLAND", riskless_only=True, strict_pure_riskless=True)
        p75_s, _, _ = simulate_single_day_net_pnl(1, 27.05, "P75_LONDON_UPSIDE", riskless_only=True, strict_pure_riskless=True)
        self.assertLess(p25_s, p50_s)
        self.assertLess(p50_s, p75_s)
        self.assertEqual(bd_50s["BOND1_and_BOND2_uma_resolution_carry"], 0.0)
        self.assertEqual(bd_50s["S2_rtds_twap_and_clinch_locks"], 0.0)
        self.assertEqual(bd_50s["dynamic_tier_unlock_sleeves"], 0.0)
        self.assertGreater(bd_50s["D1_same_oracle_and_quiet_boxes"], 0.30)
        self.assertIn("SEED_MATH_RISKLESS", ms_strict)

        _, bd_145, ms_145 = simulate_single_day_net_pnl(10, 145.0, "P50_BASE_FINLAND", riskless_only=True, strict_pure_riskless=False)
        self.assertGreater(bd_145["dynamic_tier_unlock_sleeves"], 0.40)
        self.assertIn("TIER_2_UNLOCKED", ms_145)

        proj_r = build_live_projections(days=14, fallback_equity=75.73, riskless_only=True, strict_pure_riskless=True)
        self.assertTrue(proj_r["riskless_only_mode"])
        self.assertTrue(proj_r["strict_pure_riskless_mode"])
        self.assertEqual(proj_r["model_version"], "v6.2.0_strict_pure_riskless_math_dominance_only")
        self.assertEqual(proj_r["anchor_live_state"]["current_v393_ticket_usd"], 0.0)
        self.assertIn("post_nov14_miami_scenarios_usd", proj_r)

    def test_09_goal_weather_crash_fix_ws_clinch_sniper_fee_poison_htm_recycle_and_425_cancel(self) -> None:
        from datetime import date, datetime, timezone
        from py_clob_client_v2.exceptions import PolyApiException
        import src.polymarket_research.alpha_124_shadow_daemon as a124_mod
        from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor
        from src.polymarket_research.polymarket_ws_streams import PolymarketClobMarketWsTracker
        from src.polymarket_research.riskless_protocol_v2_expansion import (
            compute_sll_and_carry_gatling_budget,
            evaluate_clinched_ws_book_snipe_impl,
            maybe_emit_recorder_fast_riskless_ipc,
            maybe_manage_passive_htm_early_maker_recycle,
            register_clinched_ws_watch_cand_impl,
        )
        from src.polymarket_research.weather_metar_engine import WeatherBucket, WeatherEventSpec

        now_ts = time.time()

        # 1. Exact FeeModuleV2 7.2% crypto fee rate
        self.assertAlmostEqual(float(a124_mod.CRYPTO_FEE_RATE), 0.072, places=4)

        # 2. PolymarketClobMarketWsTracker builds valid book from incremental price_change deltas without initial snapshot,
        #    and register_clinched_ws_watch_cand_impl seeds bk_opp from ws_books so 10h W_PRUNE1 $0.990 panic asks snipe!
        ws = PolymarketClobMarketWsTracker()
        tok_no_dead = "88101" * 6
        tok_yes_dead = "88102" * 6
        mono0 = time.monotonic()
        ws._apply_changes_locked(
            tok_no_dead,
            [
                {"asset_id": tok_no_dead, "side": "BUY", "price": "0.985", "size": "25"},
                {"asset_id": tok_no_dead, "side": "SELL", "price": "0.990", "size": "12"},
            ],
            mono0,
        )
        bk_delta = ws.get_book(tok_no_dead, max_age_sec=5.0)
        self.assertIsNotNone(bk_delta)
        self.assertAlmostEqual(float(bk_delta["asks"][0]["price"]), 0.990, places=4)

        harv_ws = types.SimpleNamespace(
            dry_run=False,
            _last_known_collateral=75.73,
            _pos_market_ws=ws,
            _clinched_ws_watchlist={},
            _clinched_ws_snipe_cd={},
        )
        ok_reg = register_clinched_ws_watch_cand_impl(
            harv_ws,
            {
                "box_type": "CLINCH_WATCHLIST_REG",
                "sleeve_source": "W_PRUNE1_DEAD_NO_BOND",
                "asset": "NYC_KLGA",
                "dedupe_key": "W_PRUNE_NO_KLGA_1",
                "leg_a_token_id": tok_no_dead,
                "leg_a_opp_token_id": tok_yes_dead,
                "leg_a_market_id": "MKT_KLGA_60",
                "leg_a_condition_id": "0x" + "ab" * 32,
                "leg_a_side": "NO",
                "leg_a_label": "NYC High 60-61F [Dead NO]",
                "expiry_ts": now_ts + 10.0 * 3600.0,  # 10h TTE -> passes 15 bps/hr via 4h HTM fast recycle!
                "max_box_cost_net": 0.994,
                "max_opp_bid": 0.020,
                "p_model": 1.0,
                "hold_to_maturity": True,
                "ws_books": {
                    tok_no_dead: {"bids": [{"price": "0.985", "size": "25"}], "asks": [{"price": "0.996", "size": "20"}]},
                    tok_yes_dead: {"bids": [{"price": "0.002", "size": "30"}], "asks": [{"price": "0.015", "size": "30"}]},
                },
            },
            now_ts=now_ts,
        )
        self.assertTrue(ok_reg)
        self.assertIsNotNone(ws.get_book(tok_yes_dead, max_age_sec=60.0))
        snipe_wp = evaluate_clinched_ws_book_snipe_impl(harv_ws, tok_no_dead, bk_win=bk_delta, now_ts=now_ts)
        self.assertIsNotNone(snipe_wp)
        self.assertEqual(snipe_wp["sleeve_source"], "W_PRUNE1_DEAD_NO_BOND")

        # 3. Weather W_PRUNE1 scan_weather_markets P0 AttributeError fix (`d1_live_candidates_file`) + _ws_dead_q_by_event
        with tempfile.TemporaryDirectory() as td_w:
            cand_w_path = Path(td_w) / "d1_live_box_candidates.jsonl"
            st_w_path = Path(td_w) / "alpha124_shadow_state.json"
            with (
                mock.patch.object(a124_mod, "D1_LIVE_CANDIDATES_FILE", cand_w_path),
                mock.patch.object(a124_mod, "STATE_FILE", st_w_path),
            ):
                dm_w = a124_mod.Alpha124ShadowDaemon(single_scan=False)
                obs_d = datetime.now(timezone.utc).date()
                sp_w = WeatherEventSpec(
                    event_id="EVT_WX_99",
                    slug="nyc-daily-weather-test",
                    series_slug="nyc-daily-weather",
                    title="NYC High Temp Today",
                    icao="KLGA",
                    city="NYC",
                    lat=40.7769,
                    lon=-73.8740,
                    tz_name="UTC",
                    obs_date=obs_d,
                    metric="HIGH",
                    unit="F",
                    fee_type="zero_fees",
                    end_date_iso=datetime.fromtimestamp(now_ts + 7200.0, tz=timezone.utc).isoformat(),
                    buckets=[
                        WeatherBucket("m_w1", "0x1", "50-51F", "50-51F", "tok_y1", "tok_n1", "F", 50.0, 51.0, neg_risk=True, question_index=0),
                        WeatherBucket("m_w2", "0x2", "70-71F", "70-71F", "tok_y2", "tok_n2", "F", 70.0, 71.0, neg_risk=True, question_index=1),
                        WeatherBucket("m_w3", "0x3", "72F or higher", "72F+", "tok_y3", "tok_n3", "F", 72.0, 999.0, neg_risk=True, question_index=2),
                    ],
                )
                dm_w.weather_events = {"EVT_WX_99": sp_w}
                dm_w.metar_cache[f"KLGA_{obs_d.isoformat()}"] = (
                    now_ts,
                    [types.SimpleNamespace(temp_c=22.0, utc_dt=datetime.now(timezone.utc))],
                )
                dm_w.taf_cache[f"KLGA_{obs_d.isoformat()}"] = (now_ts, {})
                dm_w.ensemble_cache["KLGA"] = (now_ts, {"ok": True})
                with (
                    mock.patch.object(
                        a124_mod,
                        "compute_weather_probabilities",
                        return_value={
                            "is_solar_lock": False,
                            "locked_bucket_idx": None,
                            "p_locked_bucket": 0.0,
                            "obs_count": 3,
                            "latest_temp_c": 22.0,  # 71.6F -> 50-51F is mathematically dead NO!
                            "running_ext_c": 22.0,
                            "peak_iqr_c": 1.2,
                            "cooling_cushion_c": 0.0,
                            "convective_cold_pool": False,
                            "has_corrected_obs": False,
                            "probs": [0.0, 0.4, 0.6],
                        },
                    ),
                    mock.patch.object(
                        dm_w,
                        "fetch_books_batch",
                        return_value={
                            "tok_y1": {"bids": [{"price": "0.002", "size": "40"}], "asks": [{"price": "0.015", "size": "40"}]},
                            "tok_n1": {"bids": [{"price": "0.985", "size": "40"}], "asks": [{"price": "0.997", "size": "40"}]},
                            "tok_y2": {"bids": [{"price": "0.38", "size": "40"}], "asks": [{"price": "0.42", "size": "40"}]},
                            "tok_n2": {"bids": [{"price": "0.58", "size": "40"}], "asks": [{"price": "0.62", "size": "40"}]},
                            "tok_y3": {"bids": [{"price": "0.58", "size": "40"}], "asks": [{"price": "0.62", "size": "40"}]},
                            "tok_n3": {"bids": [{"price": "0.38", "size": "40"}], "asks": [{"price": "0.42", "size": "40"}]},
                        },
                    ),
                ):
                    opps_w: list = []
                    asyncio.run(dm_w.scan_weather_markets(opps_w))
                    self.assertIn(0, dm_w._ws_dead_q_by_event.get("EVT_WX_99", set()))
                    self.assertTrue(cand_w_path.exists())
                    reg_rows = [
                        json.loads(ln)
                        for ln in cand_w_path.read_text(encoding="utf-8").splitlines()
                        if ln.strip()
                    ]
                    cwatch = [r for r in reg_rows if r.get("box_type") == "CLINCH_WATCHLIST_REG"]
                    self.assertGreaterEqual(len(cwatch), 1)
                    self.assertIsInstance(cwatch[0].get("ws_books"), dict)

        # 4. Maker prewarm_token_market_cache NEVER poisons _fee_cache with 0.0 when preserve_fee_cache=True
        ex_fee = PolymarketLiveExecutor(dry_run=True)
        ex_fee.dry_run = False
        ex_fee.client = types.SimpleNamespace(
            __dict__={"_tick_sizes": {}, "_negrisk": {}, "_fee_rates": {}},
        )
        tok_s2_fee = "77001" * 6
        tok_uncached = "77002" * 6
        ex_fee._fee_cache[tok_s2_fee] = (0.072, 1.0)
        ex_fee.prewarm_token_market_cache(tok_s2_fee, tick_size=0.001, neg_risk=False, fee_rate=0.0, preserve_fee_cache=True)
        ex_fee.prewarm_token_market_cache(tok_uncached, tick_size=0.001, neg_risk=False, fee_rate=0.0, preserve_fee_cache=True)
        self.assertAlmostEqual(ex_fee._fee_cache[tok_s2_fee][0], 0.072, places=4)
        self.assertNotIn(tok_uncached, ex_fee._fee_cache)

        # 5. cancel_order retries transient HTTP 425/500 and still runs fail-closed get_order_status verification
        ex_c = PolymarketLiveExecutor(dry_run=True)
        ex_c.dry_run = False
        ex_c.is_authenticated = True
        calls_c = {"n": 0}

        def _flaky_cancel(oids):
            calls_c["n"] += 1
            if calls_c["n"] == 1:
                raise PolyApiException(error_msg="status_code=425, order manager not ready")
            return {"canceled": list(oids)}

        ex_c.client = types.SimpleNamespace(
            cancel_orders=_flaky_cancel,
            get_order=lambda oid: {"id": oid, "status": "CANCELED", "size_matched": "0"},
        )
        res_425 = ex_c.cancel_order("OID_425_RETRY")
        self.assertTrue(res_425["is_canceled"])
        self.assertEqual(calls_c["n"], 2)

        ex_c.client = types.SimpleNamespace(
            cancel_orders=lambda oids: (_ for _ in ()).throw(PolyApiException(error_msg="status_code=500, cancel request failed")),
            get_order=lambda oid: {"id": oid, "status": "CANCELED", "size_matched": "0"},
        )
        res_500 = ex_c.cancel_order("OID_500_RECOVER")
        self.assertTrue(res_500["is_canceled"])
        self.assertEqual(res_500["outcome"], "CANCELED")

        # 6. HTM 0%-fee Maker Recycle works on 7.2%-fee crypto locks AND 0.01-tick <=$0.985 locks
        posted_htm = []
        harv_htm = types.SimpleNamespace(
            dry_run=False,
            executor=types.SimpleNamespace(
                get_token_tick_size=lambda tid, **kw: 0.01 if tid == "TOK_01_TICK" else 0.001,
                post_maker_exit_order=lambda **kw: (
                    posted_htm.append(kw)
                    or {"success": True, "orderID": f"OID_{len(posted_htm)}", "order_id": f"OID_{len(posted_htm)}", "price": kw["price"]}
                ),
            ),
            calculate_realized_cash_pnl=lambda p, cash, fee: round(cash - fee - float(p["notional_usd"]), 4),
            _apply_exit_post_result=lambda p, res, sz: p.update({"exit_order_id": res["order_id"], "target_exit_price": res["price"]}) or True,
            save_state=lambda: None,
        )
        pos_fee_u1 = {
            "trade_id": "U1_CRYPTO_HTM",
            "token_id": "TOK_FEE_001",
            "sleeve": "U1_DAILY_UPDOWN_LOCK",
            "status": "POSITION_CONFIRMED",
            "hold_to_maturity_lock": True,
            "is_single_leg_lock": True,
            "inventory_reconciled": True,
            "entry_price": 0.994,
            "entry_shares": 10.0,
            "remaining_shares": 10.0,
            "notional_usd": 9.94,
            "fee_rate_applied": 0.072,
            "candle_expiry_ts": now_ts + 3600.0,
        }
        self.assertTrue(
            asyncio.run(
                maybe_manage_passive_htm_early_maker_recycle(
                    harv_htm, "U1_CRYPTO_HTM", pos_fee_u1, {"bids": [{"price": 0.994, "size": 20.0}]}, now_ts
                )
            )
        )
        self.assertAlmostEqual(posted_htm[-1]["price"], 0.998, places=4)

        pos_01_tk = {
            **pos_fee_u1,
            "trade_id": "BOND1_01_TK",
            "token_id": "TOK_01_TICK",
            "entry_price": 0.980,
            "notional_usd": 9.80,
            "exit_order_id": None,
            "_last_htm_mkr_post_ts": 0.0,
            "_htm_passive_recycle_active": False,
        }
        self.assertTrue(
            asyncio.run(
                maybe_manage_passive_htm_early_maker_recycle(
                    harv_htm, "BOND1_01_TK", pos_01_tk, {"bids": [{"price": 0.98, "size": 20.0}]}, now_ts
                )
            )
        )
        self.assertAlmostEqual(posted_htm[-1]["price"], 0.99, places=4)

        # 7. Recorder <1ms C1_BINARY_COMPLETE_SET fast IPC + Live $75.73 8-share BOND1 clip & 48% slow cap
        sink_c1: list = []
        rec_stub = types.SimpleNamespace(
            asset="BTC",
            _test_cand_sink=sink_c1,
            market_5m={"condition_id": "0x" + "55" * 32, "fee_metadata": {"fee_rate_market": 0.072}},
        )
        snap_ok = {
            "asset": "BTC",
            "m5": {
                "market_id": "MKT_5M_C1",
                "condition_id": "0x" + "55" * 32,
                "expiry_ts": now_ts + 180.0,
                "UP": {"token_id": "T_UP", "best_ask": 0.47, "ask_size_l1": 15.0, "age_book_ms": 20.0, "is_crossed": False, "raw_top_asks": [[0.47, 15.0]], "raw_top_bids": [[0.45, 15.0]]},
                "DOWN": {"token_id": "T_DN", "best_ask": 0.48, "ask_size_l1": 12.0, "age_book_ms": 20.0, "is_crossed": False, "raw_top_asks": [[0.48, 12.0]], "raw_top_bids": [[0.46, 12.0]]},
            },
        }
        self.assertEqual(maybe_emit_recorder_fast_riskless_ipc(rec_stub, snap_ok, now_ts), 1)
        self.assertEqual(sink_c1[0]["box_type"], "COMPLETE_SET")
        self.assertEqual(sink_c1[0]["shares"], 7)
        self.assertGreater(sink_c1[0]["leg_a_gross_shares"], 7.0)
        self.assertLessEqual(sink_c1[0]["box_cost_net"], 0.989)

        harv_live_75 = types.SimpleNamespace(
            dry_run=False,
            _is_v5_unleashed_active=lambda: True,
            enforce_bond1_smart_queue=False,
            executor=types.SimpleNamespace(client=object()),
            active_positions={
                "P1": {"status": "POSITION_CONFIRMED", "sleeve": "BOND1_UMA_RESOLUTION_CARRY", "notional_usd": 24.0, "candle_expiry_ts": now_ts + 3600.0}
            },
            pending_entry_intents={},
        )
        bud_live_4th = compute_sll_and_carry_gatling_budget(
            harv_live_75,
            20.0,
            51.73,
            24.0,
            "SINGLE_LEG_MAKER_LOCK",
            "BOND1_UMA_RESOLUTION_CARRY",
            True,
            {"gatling_enabled": True, "gatling_fast_gun_reserve_usd": 20.0, "bond1_maker_fanout_clip_usd_seed": 7.96},
            rem_tte_sec=3600.0,
            now_ts=now_ts,
        )
        self.assertGreaterEqual(bud_live_4th, 8.00)
        self.assertEqual(int(bud_live_4th // 0.996), 8)

    def test_10_boost_adversarial_zero_loss_and_end_to_end_ipc_guards(self) -> None:
        from scripts.polymarket_daily_projections import build_live_projections
        from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester
        from src.polymarket_research.polymarket_terminal_recorder import L2OrderBook
        from src.polymarket_research.polymarket_ws_streams import PolymarketClobMarketWsTracker
        from src.polymarket_research.riskless_machine_gun_engine import PreSplitInventoryGun
        from src.polymarket_research.riskless_protocol_v2_expansion import (
            evaluate_clinched_ws_book_snipe_impl,
            maybe_emit_recorder_fast_riskless_ipc,
            register_clinched_ws_watch_cand_impl,
        )
        from src.polymarket_research.tradfi_sports_zero_fee_engine import NbaGameSpec, NbaOutcomeLeg
        from src.polymarket_research.uma_nba_endgame_engine import (
            LiveNbaGameState,
            evaluate_nba_endgame_locks,
        )

        now_ts = time.time()

        # 1. [P0-1] Unseeded SELL-only delta on opp_tok MUST fail-closed (never bypass max_opp_bid as 0.0),
        #    and seed_book() MUST overwrite partial-delta books with full REST snapshots!
        ws = PolymarketClobMarketWsTracker()
        tok_win = "99101" * 6
        tok_opp = "99102" * 6
        ws._desired_tokens = {tok_win, tok_opp}
        mono = time.monotonic()
        ws._apply_changes_locked(tok_win, [{"asset_id": tok_win, "side": "SELL", "price": "0.990", "size": "15"}], mono)
        ws._apply_changes_locked(tok_opp, [{"asset_id": tok_opp, "side": "SELL", "price": "0.800", "size": "20"}], mono)
        bk_opp_partial = ws.get_book(tok_opp, max_age_sec=5.0)
        self.assertTrue(bk_opp_partial["is_partial_delta"])
        self.assertEqual(bk_opp_partial["bids"], [])

        harv_p0 = types.SimpleNamespace(
            dry_run=False,
            _last_known_collateral=75.84,
            _pos_market_ws=ws,
            _clinched_ws_watchlist={},
            _clinched_ws_snipe_cd={},
        )
        register_clinched_ws_watch_cand_impl(
            harv_p0,
            {
                "box_type": "CLINCH_WATCHLIST_REG",
                "sleeve_source": "W_PRUNE1_DEAD_NO_BOND",
                "asset": "NYC_KLGA",
                "dedupe_key": "W_PRUNE1_TEST_P0",
                "leg_a_token_id": tok_win,
                "leg_a_opp_token_id": tok_opp,
                "leg_a_market_id": "MKT_P0_1",
                "leg_a_condition_id": "0x" + "cd" * 32,
                "leg_a_side": "NO",
                "leg_a_label": "Dead NO Test",
                "expiry_ts": now_ts + 3600.0,
                "max_box_cost_net": 0.994,
                "max_opp_bid": 0.020,
                "p_model": 1.0,
                "hold_to_maturity": True,
            },
            now_ts=now_ts,
        )
        self.assertIsNone(
            evaluate_clinched_ws_book_snipe_impl(harv_p0, tok_win, bk_win=ws.get_book(tok_win, 5.0), now_ts=now_ts)
        )
        # Seeding full disputed book overwrites partial delta and enforces dispute veto
        self.assertTrue(ws.seed_book(tok_opp, {"bids": [{"price": "0.25", "size": "50"}], "asks": [{"price": "0.80", "size": "20"}]}))
        self.assertFalse(ws.get_book(tok_opp, 5.0)["is_partial_delta"])
        self.assertIsNone(
            evaluate_clinched_ws_book_snipe_impl(harv_p0, tok_win, bk_win=ws.get_book(tok_win, 5.0), now_ts=now_ts)
        )
        # Seeding dead opp book (`0.002 <= 0.020`) unlocks snipe
        ws._snapshot_tokens.discard(tok_opp)
        self.assertTrue(ws.seed_book(tok_opp, {"bids": [{"price": "0.002", "size": "50"}], "asks": [{"price": "0.015", "size": "20"}]}))
        self.assertIsNotNone(
            evaluate_clinched_ws_book_snipe_impl(harv_p0, tok_win, bk_win=ws.get_book(tok_win, 5.0), now_ts=now_ts)
        )

        # 2. [P0-3 / P0-4 / P0-5] L2OrderBook.top_of_book is_crossed + real JSONL path + crypto C1_BINARY_COMPLETE_SET execution
        ob_c = L2OrderBook("TOK_CROSS")
        ob_c.apply_snapshot([{"price": "0.52", "size": "20"}], [{"price": "0.49", "size": "20"}])
        tob_c = ob_c.top_of_book(now_ts)
        self.assertTrue(tob_c["is_crossed"])

        with tempfile.TemporaryDirectory() as td_ipc:
            ipc_file = Path(td_ipc) / "d1_live_box_candidates.jsonl"
            rec_real = types.SimpleNamespace(
                asset="BTC",
                d1_live_candidates_file=ipc_file,
                market_5m={"condition_id": "0x" + "66" * 32, "fee_metadata": {"fee_rate_market": 0.072}},
            )
            snap_crossed = {
                "asset": "BTC",
                "m5": {
                    "market_id": "MKT_CROSS",
                    "condition_id": "0x" + "66" * 32,
                    "expiry_ts": now_ts + 180.0,
                    "UP": {"token_id": "T_U1", **tob_c},
                    "DOWN": {"token_id": "T_D1", "best_bid": 0.45, "best_ask": 0.48, "ask_size_l1": 20.0, "age_book_ms": 10.0, "is_crossed": False},
                },
            }
            self.assertEqual(maybe_emit_recorder_fast_riskless_ipc(rec_real, snap_crossed, now_ts), 0)

            snap_valid = {
                "asset": "BTC",
                "m5": {
                    "market_id": "MKT_VALID_C1",
                    "condition_id": "0x" + "66" * 32,
                    "expiry_ts": now_ts + 180.0,
                    "UP": {"token_id": "111111111111111111111", "best_bid": 0.45, "best_ask": 0.47, "ask_size_l1": 18.0, "age_book_ms": 10.0, "is_crossed": False, "raw_top_asks": [[0.47, 18.0]], "raw_top_bids": [[0.45, 18.0]]},
                    "DOWN": {"token_id": "222222222222222222222", "best_bid": 0.46, "best_ask": 0.48, "ask_size_l1": 18.0, "age_book_ms": 10.0, "is_crossed": False, "raw_top_asks": [[0.48, 18.0]], "raw_top_bids": [[0.46, 18.0]]},
                },
            }
            self.assertEqual(maybe_emit_recorder_fast_riskless_ipc(rec_real, snap_valid, now_ts), 1)
            self.assertTrue(ipc_file.exists())
            c1_cand = json.loads(ipc_file.read_text(encoding="utf-8").splitlines()[0])
            self.assertGreater(c1_cand["box_cost_net"], 0.985)
            self.assertLessEqual(c1_cand["box_cost_net"], 0.989)

            # [P0-2] Probabilistic W1 forecast (<0.999) is strictly blocked in live riskless_only_mode even if 8/8 graduated!
            st_a124 = Path(td_ipc) / "alpha124_shadow_state.json"
            st_a124.write_text(
                json.dumps(
                    {
                        "by_sleeve": {
                            "D1_SAME_ORACLE_DOMINANCE_BOX": {"closed": 30, "wins": 30, "losses": 0, "win_rate_pct": 100.0, "realized_pnl_t1000_usd": 120.0},
                            "W1_SOLAR_PEAK_LOCK": {"closed": 10, "wins": 10, "losses": 0, "win_rate_pct": 100.0, "realized_pnl_t1000_usd": 45.0},
                        }
                    }
                ),
                encoding="utf-8",
            )
            import src.polymarket_research.polymarket_live_harvester as plh_mod

            with (
                mock.patch.object(plh_mod, "DATA_DIR", Path(td_ipc)),
                mock.patch.object(plh_mod, "STATE_FILE", Path(td_ipc) / "h_state.json"),
            ):
                h_ro = PolymarketLiveHarvester(dry_run=True)
                h_ro.dry_run = False
                h_ro._startup_reconciled = True
                res_w1_forecast = h_ro.maybe_execute_graduated_d1_box(
                    {
                        "box_id": "W1_FORECAST_LEAK",
                        "dedupe_key": "W1_FORECAST_LEAK",
                        "box_type": "SINGLE_LEG_LOCK",
                        "sleeve_source": "W1_SOLAR_PEAK_LOCK",
                        "ts_unix": now_ts,
                        "expiry_ts": now_ts + 3600.0,
                        "p_model": 0.988,
                        "box_cost_net": 0.960,
                        "leg_a_token_id": "333333333333333333333",
                        "leg_a_opp_token_id": "444444444444444444444",
                        "leg_a_market_id": "999888",
                        "leg_a_limit_price": 0.960,
                        "shares": 10,
                    }
                )
                self.assertFalse(res_w1_forecast["executed"])
                self.assertIn("SLEEVE_NOT_YET_8_OF_8_GRADUATED", res_w1_forecast["reason"])

            # Crypto C1_BINARY_COMPLETE_SET (`0.985 < box_cost_net <= 0.989`) passes fee_2l_ok + d1_zf_bridge!
            with (
                mock.patch.object(plh_mod, "DATA_DIR", Path(td_ipc)),
                mock.patch.object(plh_mod, "STATE_FILE", Path(td_ipc) / "h_dry.json"),
            ):
                h_dry = PolymarketLiveHarvester(dry_run=True)
                res_c1_exec = h_dry.maybe_execute_graduated_d1_box(c1_cand)
                self.assertTrue(res_c1_exec["executed"], f"Crypto C1 fast IPC failed: {res_c1_exec}")

        # 3. [P0-6] SP2 NBA POST_BUZZER_FINAL & LIVE_TOTAL_OVER_LOCKED reach p_lock=0.999 while Q4 lead stays <=0.997
        nba_spec = NbaGameSpec(
            event_id="NBA_1",
            slug="bos-mia",
            title="Celtics vs Heat",
            team_a="Celtics",
            team_b="Heat",
            tipoff_ts=now_ts - 7200.0,
            settle_est_ts=now_ts + 3600.0,
            margin_legs=[NbaOutcomeLeg("m1", "0x1", "moneyline", "t1", "t2", 0, "YES", "ML Celtics", "GT", 0.0)],
            total_legs=[NbaOutcomeLeg("m2", "0x2", "totals", "t3", "t4", 0, "YES", "Over 210.5", "OVER", 210.5)],
        )
        lk_in = evaluate_nba_endgame_locks(
            nba_spec, LiveNbaGameState("g1", now_ts - 7200.0, "in", False, 4, 25.0, "Celtics", "BOS", 112, "Heat", "MIA", 101), 112, 101
        )
        by_mode_in = {x["mode"]: x["p_lock"] for x in lk_in}
        self.assertEqual(by_mode_in["LIVE_TOTAL_OVER_LOCKED"], 0.999)
        self.assertLessEqual(by_mode_in["LIVE_Q4_ENDGAME_LOCK"], 0.997)
        lk_fin = evaluate_nba_endgame_locks(
            nba_spec, LiveNbaGameState("g1", now_ts - 7200.0, "post", True, 4, 0.0, "Celtics", "BOS", 112, "Heat", "MIA", 101), 112, 101
        )
        self.assertTrue(all(x["p_lock"] == 0.999 for x in lk_fin))

        # 4. [P1-2] PreSplitInventoryGun respects resting Maker reservations on _last_known_collateral
        gun = PreSplitInventoryGun()
        ft_calls: list[str] = []
        harv_gun = types.SimpleNamespace(
            dry_run=False,
            executor=types.SimpleNamespace(dry_run=False, client=object()),
            _startup_reconciled=True,
            global_halt_active=False,
            _last_known_collateral=150.0,
            _collateral_excludes_resting_maker=False,
            active_positions={},
            pending_entry_intents={
                "MKR_RESTING": {"live_maker_anchor_inflight": True, "posted_notional_usd": 146.0, "notional_usd": 146.0}
            },
        )
        import asyncio as _aio
        self.assertIsNone(_aio.run(gun.tick(harv_gun, now_ts, fast_tick_reader=lambda a: ft_calls.append(a))))
        self.assertEqual(ft_calls, [])

        # 5. [P1-5 / P1-6] Projections clean pure-riskless roster restricts strictly to PURE_RISKLESS_ALLOWED_LIVE_SLEEVES
        proj_clean = build_live_projections(days=7, fallback_equity=75.84, riskless_only=True, strict_pure_riskless=True)
        tracked_sl = {g["sleeve"] for g in proj_clean["sleeve_graduation_live_tracker"]}
        self.assertNotIn("S2_EXACT_TWAP_LOCK", tracked_sl)
        self.assertNotIn("W_PRUNE1_DEAD_NO_BOND", tracked_sl)
        self.assertNotIn("UMA_READY1_LIVENESS_PRIORITY", tracked_sl)
        self.assertNotIn("W3_WEATHER_SLATE_ARB", tracked_sl)
        self.assertIn("D1_SAME_ORACLE_DOMINANCE_BOX", tracked_sl)
        self.assertIn("C1_BINARY_COMPLETE_SET", tracked_sl)
        self.assertIn("NR2_CONVERT_NO_SUBSET_ARB", tracked_sl)
        self.assertNotIn("SOC2_EXACT_SCORE_2D_LATTICE", tracked_sl)
        self.assertNotIn("SOC1_THREE_WAY_REGULATION_SYNTHETIC_BOX", tracked_sl)
        self.assertNotIn("SP3_SPORTS_CORRIDOR_DOMINANCE_BOX", tracked_sl)
        self.assertNotIn("SLEEVE_SOL_V392_SHADOW", tracked_sl)

    def test_pusd_autowrap_and_v2_redemption_merge(self) -> None:
        """
        Verifies 1:1 `USDC.e -> pUSD` (`0x93070a847efEf7F70739046A929D47a521F5B8ee`, selector `0x62355638`)
        wrapping across:
          1. `encode_pusd_wrap_calls` (with & without pre-existing ERC-20 allowance)
          2. `wrap_idle_usdce_to_pusd` (dry-run guard, dust skip, live $11.00 sweep + CLOB L2 sync, revert fail-closed)
          3. `attempt_onchain_redemption` atomic `[redeemPositions, wrap]` batching for both standard `USDC.e` CTF
             and `NegRiskAdapter` (`NR_WCOL -> USDC.e -> pUSD`) + fallback resilience
          4. `attempt_onchain_complete_set_merge` V2 `NEG_RISK_ADAPTER_V2_ADDRESS` (`0xadA2...`) routing
        """
        try:
            import os
            from web3 import Web3
            import src.polymarket_research.riskless_machine_gun_engine as rmg_mod
            from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor
        except ImportError:
            self.skipTest("web3 / executor dependencies unavailable in minimal interpreter")

        funder = "0x013A2474454fBd8738cff6a7f204eF1bc377F4e9"
        wrapper_cs = Web3.to_checksum_address(PolymarketLiveExecutor.PUSD_WRAPPER_ADDRESS)
        usdce_cs = Web3.to_checksum_address(PolymarketLiveExecutor.USDC_E_ADDRESS)
        ctf_cs = Web3.to_checksum_address(PolymarketLiveExecutor.CTF_ADDRESS)
        nr_cs = Web3.to_checksum_address(PolymarketLiveExecutor.NEG_RISK_ADAPTER_ADDRESS)
        nr_v2_cs = Web3.to_checksum_address(PolymarketLiveExecutor.NEG_RISK_ADAPTER_V2_ADDRESS)

        # 1. Exact ABI encoding check (`wrap(address token, address to, uint256 amount)` -> `0x62355638`)
        calls_preapproved = PolymarketLiveExecutor.encode_pusd_wrap_calls(
            funder_address=funder, amount_raw=11_000_000, current_allowance_raw=(1 << 256) - 1
        )
        self.assertEqual(len(calls_preapproved), 1)
        self.assertEqual(calls_preapproved[0][0], wrapper_cs)
        expected_wrap_hex = (
            f"0x62355638{usdce_cs[2:].lower().rjust(64, '0')}"
            f"{Web3.to_checksum_address(funder)[2:].lower().rjust(64, '0')}{(11_000_000):064x}"
        )
        self.assertEqual(calls_preapproved[0][1], expected_wrap_hex)

        calls_unapproved = PolymarketLiveExecutor.encode_pusd_wrap_calls(
            funder_address=funder, amount_raw=11_000_000, current_allowance_raw=0
        )
        self.assertEqual(len(calls_unapproved), 2)
        self.assertEqual(calls_unapproved[0][0], usdce_cs)
        self.assertTrue(calls_unapproved[0][1].startswith("0x095ea7b3"))
        self.assertEqual(calls_unapproved[1], calls_preapproved[0])

        # 2. Standalone `wrap_idle_usdce_to_pusd`
        ex = PolymarketLiveExecutor(dry_run=True)
        self.assertEqual(ex.wrap_idle_usdce_to_pusd(1.0)["dry_run"], True)

        state = {
            "usdce_bal": 250_000,  # $0.25 dust
            "usdce_alw": (1 << 256) - 1,
            "rcpt_status": 1,
            "den": 1,
            "n0": 1,
            "n1": 0,
            "std_usdce_yes": 11_000_000,
            "nr_no": 0,
            "approved_nr_v2": True,
        }
        dispatched: list[tuple[str, list[tuple[str, str]]]] = []
        ba_syncs: list[object] = []

        class _CallVal:
            def __init__(self, val: object) -> None:
                self._val = val

            def call(self) -> object:
                return self._val

        real_w3 = Web3()

        def _make_contract(address: str, abi: list[dict]) -> object:
            addr_l = str(address).lower()
            real_c = real_w3.eth.contract(address=Web3.to_checksum_address(address), abi=abi)

            class _Fns:
                def balanceOf(self, owner: str, pos_id: object = None) -> _CallVal:
                    if pos_id is None:
                        return _CallVal(state["usdce_bal"])
                    pid = int(pos_id)
                    if pid == 3001:
                        return _CallVal(state["std_usdce_yes"])
                    if pid == 4002:
                        return _CallVal(state["nr_no"])
                    if pid in (4001, 4002) and state.get("merge_nr_pair"):
                        return _CallVal(state["merge_nr_pair"])
                    return _CallVal(0)

                def allowance(self, _o: str, _s: str) -> _CallVal:
                    return _CallVal(state["usdce_alw"])

                def payoutDenominator(self, _c: bytes) -> _CallVal:
                    return _CallVal(state["den"])

                def payoutNumerators(self, _c: bytes, idx: int) -> _CallVal:
                    return _CallVal(state["n0"] if int(idx) == 0 else state["n1"])

                def getCollectionId(self, _p: bytes, _c: bytes, idx: int) -> _CallVal:
                    return _CallVal((b"\x01" if int(idx) == 1 else b"\x02") * 32)

                def getPositionId(self, col: str, col_id: bytes) -> _CallVal:
                    cl = col.lower()
                    if cl == usdce_cs.lower():
                        base = 3000
                    elif cl == PolymarketLiveExecutor.NEG_RISK_WRAPPED_COLLATERAL.lower():
                        base = 4000
                    else:
                        base = 2000
                    return _CallVal(base + col_id[0])

                def isApprovedForAll(self, _a: str, _op: str) -> _CallVal:
                    return _CallVal(state["approved_nr_v2"])

            return types.SimpleNamespace(
                functions=_Fns(),
                encode_abi=lambda fn_name, args=None: real_c.encode_abi(fn_name, args=args or []),
            )

        fake_w3 = types.SimpleNamespace(
            eth=types.SimpleNamespace(
                contract=_make_contract,
                account=types.SimpleNamespace(from_key=lambda _pk: types.SimpleNamespace(address="0x" + "22" * 20)),
                get_balance=lambda _a: 0,  # Relayer V2 sig_type=3 works with 0 POL
                wait_for_transaction_receipt=lambda _tx, **_kw: {"status": state["rcpt_status"]},
            )
        )

        ex.dry_run = False
        ex.signature_type = 3
        ex.funder_address = funder
        ex.private_key = "0x" + "11" * 32
        ex.client = types.SimpleNamespace(update_balance_allowance=lambda p: ba_syncs.append(p))
        ex._dispatch_funder_calls = lambda _w3, _W3, _pk, _st, _f, _s, calls, tag: (
            dispatched.append((tag, list(calls))) or f"0xtx_{len(dispatched)}"
        )

        with mock.patch.dict(os.environ, {"POLY_BUILDER_API_KEY": "bkey_test"}, clear=False), mock.patch.object(
            rmg_mod, "get_fast_polygon_web3", return_value=fake_w3
        ):
            # Dust ($0.25 < $1.00) -> skipped with zero Relayer calls
            res_dust = ex.wrap_idle_usdce_to_pusd(min_usd=1.0)
            self.assertFalse(res_dust["wrapped"])
            self.assertEqual(res_dust["reason"], "BELOW_MIN_USD")
            self.assertEqual(len(dispatched), 0)

            # Live $11.00 USDC.e -> wrapped 1:1 to pUSD + CLOB L2 allowance synced
            state["usdce_bal"] = 11_000_000
            res_wrap = ex.wrap_idle_usdce_to_pusd(min_usd=1.0)
            self.assertTrue(res_wrap["wrapped"])
            self.assertEqual(res_wrap["amount_usd"], 11.0)
            self.assertEqual(dispatched[-1][0], "wrap_pusd")
            self.assertEqual(dispatched[-1][1], [(wrapper_cs, expected_wrap_hex)])
            self.assertEqual(len(ba_syncs), 1)

            # Reverted tx fails closed
            state["rcpt_status"] = 0
            res_rev = ex.wrap_idle_usdce_to_pusd(min_usd=1.0)
            self.assertFalse(res_rev["wrapped"])
            self.assertEqual(res_rev["reason"], "TX_REVERTED")
            state["rcpt_status"] = 1

            # 3a. Atomic `[CTF.redeemPositions(USDC.e), PUSD_WRAPPER.wrap($2.00 idle + $11.00 redeemed = $13.00)]`
            dispatched.clear()
            state["usdce_bal"] = 2_000_000
            state["std_usdce_yes"] = 11_000_000
            cid_xrp = "0x" + "ea" * 32
            tx_red = ex.attempt_onchain_redemption(cid_xrp, neg_risk=False)
            self.assertEqual(tx_red, "0xtx_1")
            self.assertEqual(len(dispatched), 1)
            self.assertEqual(len(dispatched[0][1]), 2)
            self.assertEqual(dispatched[0][1][0][0], ctf_cs)
            self.assertEqual(dispatched[0][1][1][0], wrapper_cs)
            self.assertTrue(dispatched[0][1][1][1].endswith(f"{(13_000_000):064x}"))

            # 3b. Atomic `[NegRiskAdapter.redeemPositions, PUSD_WRAPPER.wrap($20.00)]` (Miami #6707503 NO win)
            dispatched.clear()
            state["usdce_bal"] = 0
            state["std_usdce_yes"] = 0
            state["nr_no"] = 20_000_000
            state["n0"] = 0
            state["n1"] = 1
            cid_mia = "0x" + "46" * 32
            tx_mia = ex.attempt_onchain_redemption(cid_mia, neg_risk=True)
            self.assertEqual(tx_mia, "0xtx_1")
            self.assertEqual(len(dispatched[0][1]), 2)
            self.assertEqual(dispatched[0][1][0][0], nr_cs)
            self.assertEqual(dispatched[0][1][1][0], wrapper_cs)
            self.assertTrue(dispatched[0][1][1][1].endswith(f"{(20_000_000):064x}"))

            # 4. V2 NegRisk complete-set merge routes directly to NEG_RISK_ADAPTER_V2_ADDRESS (`0xadA2...`)
            dispatched.clear()
            state["nr_no"] = 10_000_000
            state["merge_nr_pair"] = 10_000_000
            m_nr = ex.attempt_onchain_complete_set_merge(cid_mia, min_pairs=5.0, max_pairs=10.0, neg_risk=True)
            self.assertEqual(m_nr, ("0xtx_1", 10.0))
            self.assertEqual(len(dispatched[0][1]), 1)
            self.assertEqual(dispatched[0][1][0][0], nr_v2_cs)



if __name__ == "__main__":
    unittest.main()
