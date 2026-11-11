"""
Regression & Integration Suite for the 5 Priority 0 Live Production Leaks:
  1. Leak #1 — Canonical `event_group_key` & Unified Per-Event Exposure / Slot Cap (`$21.50` on `$76.79` equity)
  2. Leak #2 — `MULTI_LEG_RESIDUAL` (`UNWRESID`) Pre-Flight Sub-Dollar Veto, Settlement-Wait & Residual Supervision
  3. Leak #3 — Authoritative Fee Rate & Canonical `fee_source` Plumbing (`zero_fees` vs `crypto_fees_v2`, watchlist fee preservation)
  4. Leak #4 — Complete Stage B Opportunity Funnel (`GROSS_ARB_SEEN`, `ORDER_SUBMITTED`, `COMPLETE_BASKET_LOCKED`),
               In-Process `CompetitorDecayTracker`, & `MakerMarkoutSampler` Real-Sleeve Wiring
  5. Leak #5 — Dedicated `_fast_d1_consumer_loop` Head-of-Line Decoupling & Async Cold-Tick Thread Offload
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import threading
import time
import types
import unittest
from collections import deque
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Stdlib-only local test runner fallback (no-op inside full virtualenv with dotenv/requests/httpx/urllib3)
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


class TestPriority0LiveLeakFixes(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp_dir = tempfile.TemporaryDirectory()
        self._env_patch = mock.patch.dict(os.environ, {"PM_TELEMETRY_DIR": self._tmp_dir.name})
        self._env_patch.start()

    def tearDown(self) -> None:
        try:
            from src.polymarket_research.economic_attribution_ledger import GLOBAL_DECAY_TRACKER
            with GLOBAL_DECAY_TRACKER._lock:
                GLOBAL_DECAY_TRACKER._watches.clear()
                GLOBAL_DECAY_TRACKER._by_token.clear()
        except Exception:
            pass
        self._env_patch.stop()
        self._tmp_dir.cleanup()

    def test_01_leak1_canonical_event_keys_and_unified_event_concentration_cap(self) -> None:
        from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester
        from src.polymarket_research.riskless_protocol_v2_expansion import (
            check_per_event_concentration_cap,
            compute_d1_per_market_notional_cap,
            compute_dynamic_riskless_tier_caps,
            evaluate_clinched_ws_book_snipe_impl,
            extract_canonical_event_keys,
            extract_sll_event_group_key,
            register_clinched_ws_watch_cand_impl,
        )

        exp_ts = 1_794_113_999.0
        now_ts = exp_ts - 3600.0

        # 1. Nov 7 Miami KMIA shapes across WS_SNIPE, W_PRUNE1_NR0_BASKET, SLL Maker, and legacy MULTI_LEG_BUNDLE_LIVE
        pos_ws_legacy = {
            "trade_id": "WS_SNIPE_Miami_KMIA_242960",
            "event_id": "WS_SNIPE_Miami_KMIA_242960",
            "asset": "Miami_KMIA",
            "market_id": "MKT_KMIA_86_87",
            "candle_expiry_ts": exp_ts,
            "notional_usd": 17.50,
            "status": "POSITION_CONFIRMED",
        }
        cand_bundle = {
            "box_id": "WPRUNE_BSK_KMIA_1794113999_318559",
            "box_type": "MULTI_LEG_BUNDLE",
            "sleeve_source": "W_PRUNE1_NR0_BASKET",
            "event_id": "318559",
            "asset": "KMIA",
            "expiry_ts": exp_ts,
            "legs": [{"market_id": "MKT_KMIA_88_89", "token_id": "101" * 9}],
        }
        cand_sll_mkr = {
            "box_id": "MKR_KMIA_90",
            "box_type": "SINGLE_LEG_MAKER_LOCK",
            "sleeve_source": "W_PRUNE1_DEAD_NO_BOND",
            "event_id": "318559",
            "asset": "Miami_KMIA",
            "leg_a_market_id": "MKT_KMIA_90_PLUS",
            "expiry_ts": exp_ts,
        }
        pos_legacy_bundle = {
            "trade_id": "MULTI_LEG_BUNDLE_LIVE_KMIA_1794113999_318559_L0",
            "event_id": "MULTI_LEG_BUNDLE_LIVE_KMIA_1794113999_318559",
            "asset": "KMIA",
            "candle_expiry_ts": exp_ts,
        }

        keys_ws = extract_canonical_event_keys(pos_ws_legacy)
        keys_bundle = extract_canonical_event_keys(cand_bundle)
        keys_mkr = extract_canonical_event_keys(cand_sll_mkr)
        keys_legacy_b = extract_canonical_event_keys(pos_legacy_bundle)

        wx_bucket_key = f"EVTWX:KMIA:{int(exp_ts) // 43200}"
        self.assertIn(wx_bucket_key, keys_ws)
        self.assertIn(wx_bucket_key, keys_bundle)
        self.assertIn("EVT:318559", keys_bundle)
        self.assertIn("EVT:318559", keys_legacy_b)
        self.assertTrue(bool(keys_ws & keys_bundle))
        self.assertTrue(bool(keys_bundle & keys_mkr))
        # Synthetic WS_SNIPE_ prefix must NEVER become EVT:ws_snipe_...
        self.assertFalse(any(k.startswith("EVT:ws_snipe") for k in keys_ws))
        self.assertEqual(extract_sll_event_group_key(pos_ws_legacy), wx_bucket_key)

        # 2. Tier cap on $76.79 equity: max_concurrent_intents_per_event == 1 and max_event_notional_usd == $21.50
        caps = compute_dynamic_riskless_tier_caps(76.79, {})
        self.assertEqual(int(caps["max_concurrent_intents_per_event"]), 1)
        self.assertAlmostEqual(float(caps["max_event_notional_usd"]), 21.50, places=2)

        h = PolymarketLiveHarvester.__new__(PolymarketLiveHarvester)
        h.dry_run = False
        h.enforce_event_concentration_cap = True
        h.max_exposure = 100.0
        h._last_known_collateral = 59.29
        h.active_positions = {"WS_SNIPE_Miami_KMIA_242960": dict(pos_ws_legacy)}
        h.pending_entry_intents = {}
        h.closed_positions = []
        h._is_v5_unleashed_active = lambda: True
        h.executor = types.SimpleNamespace(auth_mode="LIVE", client=object())
        h.config_manager = types.SimpleNamespace(
            snapshot=types.SimpleNamespace(riskless_boxes=types.SimpleNamespace(paused_riskless_sleeves=()))
        )

        # compute_d1_per_market_notional_cap uses real $76.79 NAV ($35.32 = 76.79 * 0.46), NOT max_exposure ($100 -> $45.00)!
        self.assertAlmostEqual(compute_d1_per_market_notional_cap(h), 35.32, places=2)

        # Second slot on same KMIA event (even via W_PRUNE1_NR0_BASKET or SLL Maker on a different bracket market) is BLOCKED!
        ok_b, rsn_b, _, _ = check_per_event_concentration_cap(h, cand_bundle, market_ids=["MKT_KMIA_88_89"], now_ts=now_ts)
        self.assertFalse(ok_b)
        self.assertEqual(rsn_b, "MAX_CONCURRENT_PER_EVENT_REACHED")

        ok_m, rsn_m, _, _ = check_per_event_concentration_cap(h, cand_sll_mkr, market_ids=["MKT_KMIA_90_PLUS"], now_ts=now_ts)
        self.assertFalse(ok_m)
        self.assertEqual(rsn_m, "MAX_CONCURRENT_PER_EVENT_REACHED")

        # Pre-settlement W1_LOW_TROUGH_LOCK single-leg snipe is strictly quarantined under P0.1 zero-loss invariance,
        # while verified W_PRUNE1_DEAD_NO_BOND watchlist registration succeeds (`p_model=1.0`) and slot-1 event
        # concentration cap immediately blocks any second KMIA entry until KMIA is flat!
        tok_other = "202" * 9
        ws_cand_trough_quarantined = {
            "leg_a_token_id": tok_other,
            "leg_a_opp_token_id": "303" * 9,
            "leg_a_market_id": "MKT_KMIA_84_85",
            "leg_a_condition_id": "0xabc",
            "leg_a_side": "NO",
            "leg_a_fee_rate": 0.0,
            "p_model": 1.0,
            "sleeve_source": "W1_LOW_TROUGH_LOCK",
            "asset": "Miami_KMIA",
            "event_id": "318559",
            "expiry_ts": exp_ts,
            "max_lock_eff_px": 0.995,
        }
        self.assertFalse(register_clinched_ws_watch_cand_impl(h, dict(ws_cand_trough_quarantined), now_ts=now_ts))

        ws_cand_kmia = dict(ws_cand_trough_quarantined, sleeve_source="W_PRUNE1_DEAD_NO_BOND")
        reg_ok = register_clinched_ws_watch_cand_impl(h, dict(ws_cand_kmia), now_ts=now_ts)
        self.assertTrue(reg_ok)
        snipe_blocked = evaluate_clinched_ws_book_snipe_impl(
            h,
            tok_other,
            bk_win={"asks": [{"price": "0.985", "size": "25"}], "bids": [{"price": "0.980", "size": "25"}]},
            now_ts=now_ts + 1.0,
        )
        self.assertIsNone(snipe_blocked)

        # Once KMIA is flat (and 5s snipe cooldown elapses), WS_SNIPE succeeds, propagates event_id, and clips budget!
        h.active_positions.clear()
        h._last_known_collateral = 76.79
        snipe_ok = evaluate_clinched_ws_book_snipe_impl(
            h,
            tok_other,
            bk_win={"asks": [{"price": "0.980", "size": "100"}], "bids": [{"price": "0.975", "size": "25"}]},
            now_ts=now_ts + 7.0,
        )
        self.assertIsNotNone(snipe_ok)
        assert snipe_ok is not None
        self.assertEqual(snipe_ok["event_id"], "318559")
        self.assertIn("EVT:318559", extract_canonical_event_keys(snipe_ok))
        self.assertLessEqual(float(snipe_ok["shares"]) * float(snipe_ok["leg_a_limit_price"]), 21.50 + 0.98)

    def test_02_leak2_multi_leg_bundle_sub_dollar_veto_and_residual_supervision(self) -> None:
        from src.polymarket_research.economic_attribution_ledger import is_partial_basket_unwind_record
        from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester
        from src.polymarket_research.riskless_protocol_v2_expansion import (
            _execute_multi_leg_bundle_sync,
            finish_protocol_v2_special_box_sync,
        )

        now_ts = 1_794_110_000.0
        exp_ts = now_ts + 3600.0
        tok_big = "401" * 9
        tok_mid = "403" * 9
        tok_tiny = "402" * 9
        snipe_calls = []
        unwind_calls = []
        wait_calls = []

        class _LiveBundleExec:
            auth_mode = "LIVE"
            client = object()  # real-mode (no _mock_children)

            def get_collateral_balance(self) -> float:
                return 76.79

            def invalidate_collateral_cache(self) -> None:
                return None

            def get_market_book(self, tid: str) -> dict:
                if tid == tok_big:
                    return {"asks": [{"price": "0.64", "size": "50"}], "bids": [{"price": "0.63", "size": "50"}]}
                if tid == tok_mid:
                    return {"asks": [{"price": "0.30", "size": "50"}], "bids": [{"price": "0.29", "size": "50"}]}
                return {"asks": [{"price": "0.04", "size": "50"}], "bids": [{"price": "0.03", "size": "50"}]}

            def execute_snipe_order(self, **kw) -> dict:
                snipe_calls.append(kw)
                if kw["token_id"] == tok_tiny:
                    return {"success": True, "orderID": "OID_TINY", "matched_shares": kw.get("min_order_shares", 14.0), "price": 0.04}
                return {"success": False, "error": "FAK_KILLED"}

            def execute_unwind_order(self, **kw) -> dict:
                unwind_calls.append(kw)
                # Simulate partial unwind (10 of 15 shares sold, 5 residual shares left!)
                return {
                    "success": True,
                    "orderID": "OID_UNW_1",
                    "matched_shares": 10.0,
                    "taking_amount": 0.30,
                    "fee_usd": 0.0,
                }

        h = PolymarketLiveHarvester.__new__(PolymarketLiveHarvester)
        h.dry_run = False
        h.max_exposure = 100.0
        h._last_known_collateral = 76.79
        h.active_positions = {}
        h.pending_entry_intents = {}
        h.closed_positions = []
        h._state_save_lock = threading.Lock()
        h.risk_controller = types.SimpleNamespace(record_trade_outcome=lambda pnl: None)
        saved_count = [0]
        h.save_state = lambda: saved_count.__setitem__(0, saved_count[0] + 1)
        h._refresh_global_halt = lambda *a, **kw: None
        h._is_v5_unleashed_active = lambda: True
        h.executor = _LiveBundleExec()

        # Case A1: On unmocked live CLOB with strict_pure_riskless_mode=True, Stage C blocks MULTI_LEG_BUNDLE upfront!
        cand_sub_dollar = {
            "box_id": "WPRUNE_SUB_DOLLAR_KMIA",
            "box_type": "MULTI_LEG_BUNDLE",
            "sleeve_source": "W_PRUNE1_NR0_BASKET",
            "asset": "KMIA",
            "event_id": "318559",
            "is_exhaustive_partition": True,
            "ts_unix": now_ts,
            "expiry_ts": exp_ts,
            "box_cost_net": 0.980,
            "max_box_cost_net": 0.992,
            "legs": [
                {"token_id": tok_big, "market_id": "M1", "condition_id": "C1", "side": "YES", "ask_px": 0.64, "ask_size": 50.0, "fee_rate": 0.0},
                {"token_id": tok_mid, "market_id": "M3", "condition_id": "C3", "side": "YES", "ask_px": 0.30, "ask_size": 50.0, "fee_rate": 0.0},
                {"token_id": tok_tiny, "market_id": "M2", "condition_id": "C2", "side": "YES", "ask_px": 0.04, "ask_size": 50.0, "fee_rate": 0.0},
            ],
        }
        out_stage_c = finish_protocol_v2_special_box_sync(
            h, cand_sub_dollar, "DK_SUB0", {}, now_ts, {"d1_box_max_budget_usd": 20.0}, own_grad=True
        )
        self.assertFalse(out_stage_c["executed"])
        self.assertIn("PURE_RISKLESS", str(out_stage_c["reason"]))

        # Case A2: Even when MULTI_LEG_BUNDLE is explicitly un-gated, pre-flight veto catches sub-$1.00 tail leg
        # ($0.04 * 20 sh = $0.80 < $1.00) BEFORE Leg 0 submits!
        h.executor.get_market_book = h.executor.get_market_book  # bind on instance to bypass Stage C firewall
        h.enforce_bundle_unwind_guard = True
        out_veto = finish_protocol_v2_special_box_sync(
            h, cand_sub_dollar, "DK_SUB", {}, now_ts, {"d1_box_max_budget_usd": 20.0}, own_grad=True
        )
        self.assertFalse(out_veto["executed"])
        self.assertTrue(str(out_veto["reason"]).startswith("BUNDLE_SUB_DOLLAR_LEG_LOT"))
        self.assertEqual(len(snipe_calls), 0)

        # Case B: Valid 3 legs (>= $1.00), tightest USD leg executes first with allow_partial_fak=True,
        # Leg 2 fails -> waits for ERC-1155 settlement, unwinds 10 sh inline into closed_positions, and
        # supervises remaining 5 sh UNWRESID with UNWIND_RETRY_REQUIRED & is_single_leg_lock=False!
        legs_valid = [
            {"token_id": tok_big, "market_id": "M1", "condition_id": "C1", "side": "YES", "ask_px": 0.50, "ask_size": 50.0, "fee_rate": 0.0},
            {"token_id": tok_mid, "market_id": "M3", "condition_id": "C3", "side": "YES", "ask_px": 0.28, "ask_size": 50.0, "fee_rate": 0.0},
            {"token_id": tok_tiny, "market_id": "M2", "condition_id": "C2", "side": "YES", "ask_px": 0.20, "ask_size": 18.0, "fee_rate": 0.0},
        ]
        snipe_calls.clear()

        def _snipe_leg_out(**kw) -> dict:
            snipe_calls.append(kw)
            if kw["token_id"] == tok_tiny:
                return {"success": True, "orderID": "OID_L0", "matched_shares": 15.0, "price": 0.20}
            return {"success": False, "error": "LEG2_NO_FILL"}

        h.executor.execute_snipe_order = _snipe_leg_out
        with mock.patch(
            "src.polymarket_research.riskless_protocol_v2_expansion.wait_for_erc1155_delivery",
            side_effect=lambda ex, toks, min_sh, timeout_sec=3.5: (wait_calls.append((toks, min_sh)) or True),
        ):
            res_lo = _execute_multi_leg_bundle_sync(
                h.executor, legs_valid, shares=15.0, bundle_id="MLB_KMIA_TEST", harvester=h,
                exp_ts=exp_ts, sleeve_src="W_PRUNE1_NR0_BASKET", cand_asset="KMIA", event_id="318559",
            )
        self.assertFalse(res_lo["success"])
        self.assertTrue(res_lo["legged_out"])
        # Tightest USD depth leg (tok_tiny: 18 * $0.20 = $3.60 vs tok_mid $14.00 / tok_big $25.00) executed FIRST!
        self.assertEqual(snipe_calls[0]["token_id"], tok_tiny)
        self.assertTrue(bool(snipe_calls[0].get("allow_partial_fak")))
        # Waited for ERC-1155 settlement BEFORE firing unwind!
        self.assertEqual(len(wait_calls), 1)
        self.assertEqual(wait_calls[0][0], [tok_tiny])
        self.assertEqual(len(unwind_calls), 1)
        self.assertAlmostEqual(float(unwind_calls[0]["min_price"]), 0.001, places=4)

        # 10 unwound shares booked to closed_positions and recognized by Stage B KPI #4:
        self.assertEqual(len(h.closed_positions), 1)
        self.assertAlmostEqual(float(h.closed_positions[0]["filled_exit_shares"]), 10.0, places=3)
        self.assertTrue(is_partial_basket_unwind_record(h.closed_positions[0]))
        # 5 remaining shares registered in active_positions as supervised residual (NOT terminal hold!),
        # and f_not_sold ($2.00) + resid_pos.notional_usd ($1.00) == $3.00 exact cost conservation!
        self.assertEqual(len(h.active_positions), 1)
        resid_tid, resid_pos = next(iter(h.active_positions.items()))
        self.assertIn("_UNWRESID_", resid_tid)
        self.assertAlmostEqual(float(resid_pos["remaining_shares"]), 5.0, places=3)
        self.assertAlmostEqual(
            float(h.closed_positions[0]["notional_usd"]) + float(resid_pos["notional_usd"]),
            3.0,
            places=4,
        )
        self.assertTrue(bool(resid_pos["is_legged_out_residual"]))
        self.assertFalse(bool(resid_pos["is_single_leg_lock"]))
        self.assertFalse(bool(resid_pos["is_dominance_box"]))
        self.assertFalse(bool(resid_pos["hold_to_maturity_lock"]))
        self.assertEqual(resid_pos["exit_order_status"], "UNWIND_RETRY_REQUIRED")
        self.assertEqual(resid_pos["fee_source"], "zero_fees")
        self.assertTrue(is_partial_basket_unwind_record(resid_pos))
        self.assertGreaterEqual(saved_count[0], 1)

        # Re-submitting the same bundle while UNWRESID is open is blocked by MARKET_ALREADY_OCCUPIED:
        cand_valid = {
            "box_id": "MLB_KMIA_TEST",
            "box_type": "MULTI_LEG_BUNDLE",
            "sleeve_source": "W_PRUNE1_NR0_BASKET",
            "asset": "KMIA",
            "event_id": "318559",
            "is_exhaustive_partition": True,
            "ts_unix": now_ts,
            "expiry_ts": exp_ts,
            "box_cost_net": 0.980,
            "max_box_cost_net": 0.992,
            "legs": legs_valid,
        }
        out_occ = finish_protocol_v2_special_box_sync(
            h, cand_valid, "DK_VALID", {}, now_ts, {"d1_box_max_budget_usd": 20.0}, own_grad=True
        )
        self.assertFalse(out_occ["executed"])
        self.assertEqual(out_occ["reason"], "MARKET_ALREADY_OCCUPIED")

    def test_03_leak3_authoritative_fee_rate_and_canonical_fee_source(self) -> None:
        from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester
        from src.polymarket_research.riskless_machine_gun_engine import resolve_authoritative_exit_fee_rate
        from src.polymarket_research.riskless_protocol_v2_expansion import (
            register_clinched_ws_watch_cand_impl,
            resolve_canonical_fee_source,
        )

        # 1. Canonical fee_source stamps "zero_fees" on 0%-fee weather/macro sleeves instead of "crypto_fees_v2"
        self.assertEqual(resolve_canonical_fee_source(0.0, "W_PRUNE1_DEAD_NO_BOND", "crypto_fees_v2"), "zero_fees")
        self.assertEqual(resolve_canonical_fee_source(0.0, "BOND1_UMA_RESOLUTION_CARRY", ""), "zero_fees")
        self.assertEqual(resolve_canonical_fee_source(0.07, "S2_RTDS_EXACT_TWAP_INTEGRATOR", ""), "crypto_fees_v2")
        self.assertEqual(resolve_canonical_fee_source(0.02, "CL1_MULTISPORT_POST_REVIEW_SCORE_CLINCH", ""), "sports_fees_v2")

        h = PolymarketLiveHarvester.__new__(PolymarketLiveHarvester)
        h.dry_run = True
        pos_zf = h._make_single_leg_lock_pos(
            "WS_SNIPE_KMIA_1", "SINGLE_LEG_LOCK", "W_PRUNE1_DEAD_NO_BOND", "KMIA", "lock_1leg",
            "M_KMIA", "0xcid", "501" * 9, "NO", True, 20.0, 19.70, 0.0, 0.0, 1.0,
            "crypto_fees_v2", 1_794_113_999.0, 1_794_110_000.0, 0.0, "OID1", True,
        )
        self.assertEqual(pos_zf["fee_source"], "zero_fees")

        pos_mkr = h._make_single_leg_lock_pos(
            "MKR_S2_1", "SINGLE_LEG_MAKER_LOCK", "S2_RTDS_EXACT_TWAP_INTEGRATOR", "BTC", "maker_lock_1leg",
            "M_BTC", "0xcid2", "502" * 9, "YES", False, 20.0, 19.60, 0.0, 0.0, 1.0,
            "maker_post_only_0pct", 1_794_110_300.0, 1_794_110_000.0, 0.0, "OID2", True,
        )
        self.assertEqual(pos_mkr["fee_source"], "maker_post_only_0pct")

        # 2. Maker 0.0 fee candidate MUST NOT clobber non-zero taker leg_a_fee_rate in _clinched_ws_watchlist!
        tok_crypto = "503" * 9
        now_u = time.time()
        register_clinched_ws_watch_cand_impl(
            h,
            {
                "box_type": "CLINCH_WATCHLIST_REG",
                "leg_a_token_id": tok_crypto,
                "leg_a_opp_token_id": "504" * 9,
                "leg_a_market_id": "M_CRYPTO_1",
                "leg_a_fee_rate": 0.07,
                "p_model": 0.9995,
                "sleeve_source": "S2_RTDS_EXACT_TWAP_INTEGRATOR",
                "asset": "BTC",
                "expiry_ts": now_u + 180.0,
            },
            now_ts=now_u,
        )
        register_clinched_ws_watch_cand_impl(
            h,
            {
                "box_type": "SINGLE_LEG_MAKER_LOCK",
                "leg_a_token_id": tok_crypto,
                "leg_a_opp_token_id": "504" * 9,
                "leg_a_market_id": "M_CRYPTO_1",
                "leg_a_fee_rate": 0.0,
                "p_model": 0.9996,
                "sleeve_source": "S2_RTDS_EXACT_TWAP_INTEGRATOR",
                "asset": "BTC",
                "expiry_ts": now_u + 180.0,
            },
            now_ts=now_u + 0.5,
        )
        self.assertAlmostEqual(float(h._clinched_ws_watchlist[tok_crypto]["leg_a_fee_rate"]), 0.07, places=4)

        # 3. resolve_authoritative_exit_fee_rate queries real PolymarketLiveExecutor.get_market_fee_params
        class _RealFeeExec:
            dry_run = False

            def get_market_fee_params(self, market_id: str, token_id: str = None) -> tuple:
                return (0.07, 1.0, "crypto_fees_v2") if token_id == tok_crypto else (0.0, 1.0, "zero_fees")

        fr_c = resolve_authoritative_exit_fee_rate(
            _RealFeeExec(),
            {"token_id": tok_crypto, "condition_id": "0xcond_btc", "fee_rate_applied": 0.0, "fee_source": "maker_post_only_0pct"},
        )
        self.assertAlmostEqual(fr_c, 0.07, places=4)

    def test_04_leak4_stage_b_funnel_inprocess_decay_and_markout_sleeve_wiring(self) -> None:
        from src.polymarket_research.economic_attribution_ledger import (
            CompetitorDecayTracker,
            MakerMarkoutSampler,
            compute_stage_b_attribution_report,
            flush_stage_b_telemetry,
            register_candidate_funnel_and_decay_watch,
        )
        from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester

        telem_dir = Path(self._tmp_dir.name)
        tracker = CompetitorDecayTracker()
        tok_watch = "601" * 9

        # 1. Shadow emits GROSS_ARB_SEEN + EXECUTABLE_NET_L2; Harvester registers decay watch with emit_funnel=False
        cand_sll = {
            "box_id": "SLL_KMIA_DECAY_1",
            "dedupe_key": "DK_KMIA_DECAY_1",
            "box_type": "SINGLE_LEG_LOCK",
            "sleeve_source": "W_PRUNE1_DEAD_NO_BOND",
            "asset": "KMIA",
            "leg_a_token_id": tok_watch,
            "leg_a_limit_price": 0.985,
            "leg_a_avail_shares": 30.0,
            "shares": 20.0,
            "box_cost_gross": 0.985,
            "box_cost_net": 0.985,
            "max_box_cost_net": 0.994,
        }
        register_candidate_funnel_and_decay_watch(cand_sll, emit_funnel=True, tracker=CompetitorDecayTracker())
        register_candidate_funnel_and_decay_watch(cand_sll, emit_funnel=False, tracker=tracker)
        self.assertIn(tok_watch, tracker.watched_token_ids())

        # Competitor sweeps ask from 0.985 -> 0.998 on Harvester Market WS -> emits COMPETITOR_DECAY_OBSERVED!
        ev_decay = tracker.on_top_of_book_tick(tok_watch, 0.998, 5.0)
        self.assertEqual(len(ev_decay), 1)
        self.assertAlmostEqual(float(ev_decay[0]["post_sum_ask"]), 0.998, places=3)

        # 2. Nested details.latency_telemetry.clob_http_post_ms & funnel backfill in compute_stage_b_attribution_report
        (telem_dir / "live_orders.jsonl").write_text(
            json.dumps({
                "timestamp": "2026-11-08T05:00:00Z",
                "action": "SUBMIT",
                "details": {"latency_telemetry": {"clob_http_post_ms": 41.5}},
            }) + "\n",
            encoding="utf-8",
        )
        state_obj = {
            "live_bankroll": 58.0,
            "active_positions": {},
            "closed_positions": [
                {
                    "trade_id": "SLL_KMIA_DECAY_1",
                    "sleeve": "W_PRUNE1_DEAD_NO_BOND",
                    "box_type": "SINGLE_LEG_LOCK",
                    "notional_usd": 19.70,
                    "payout_usd": 20.00,
                    "net_pnl_usd": 0.30,
                    "entry_ts": 1_794_110_000.0,
                    "closed_at_ts": 1_794_111_800.0,
                }
            ],
        }
        flush_stage_b_telemetry()
        rpt = compute_stage_b_attribution_report(
            grouped_closed=state_obj["closed_positions"],
            active_positions=state_obj["active_positions"],
            reconciled_equity_usd=77.70,
            data_dir=telem_dir,
        )
        stages = rpt["opportunity_funnel"]["stages"]
        self.assertGreaterEqual(stages["GROSS_ARB_SEEN"], 1)
        self.assertGreaterEqual(stages["EXECUTABLE_NET_L2"], 1)
        self.assertGreaterEqual(stages["ORDER_SUBMITTED"], 1)
        self.assertGreaterEqual(stages["COMPLETE_BASKET_LOCKED"], 1)
        self.assertEqual(rpt["north_star_kpis"]["kpi_9_decay_samples"], 1)
        self.assertAlmostEqual(float(rpt["north_star_kpis"]["kpi_6_http_post_p50_ms"]), 41.5, places=1)
        self.assertAlmostEqual(float(rpt["north_star_kpis"]["kpi_6_signal_to_ack_p50_ms"]), 41.5, places=1)

        # 3. _reconcile_maker_entry_fill records real sleeve_source (BOND1_UMA_RESOLUTION_CARRY) via WS-first book lookup!
        real_sampler = MakerMarkoutSampler()
        sampler = types.SimpleNamespace(
            schedule_maker_fill=lambda **kw: real_sampler.schedule_maker_fill(horizons_sec=(0.01,), **kw)
        )
        tok_mkr = "602" * 9
        ws_called = [0]
        rest_called = [0]

        h = PolymarketLiveHarvester.__new__(PolymarketLiveHarvester)
        h.dry_run = False
        h.pending_entry_intents = {
            "INT_B1": {
                "entry_order_id": "OID_MKR_B1",
                "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
                "token_id": tok_mkr,
            }
        }
        h._pos_market_ws = types.SimpleNamespace(
            get_book=lambda tid, max_age_sec=5.0: (
                ws_called.__setitem__(0, ws_called[0] + 1)
                or {"bids": [{"price": "0.992", "size": "20"}], "asks": [{"price": "0.994", "size": "20"}]}
            )
        )
        h.executor = types.SimpleNamespace(
            _user_ws_cache=None,
            cancel_order_and_verify=lambda oid, tid: {"is_canceled": False, "outcome": "FILLED", "matched": 20.0},
            get_order_fill_summary=lambda oid, tid: {"matched": 20.0, "avg_price": 0.991, "cash": 19.82, "terminal": True},
            get_market_book=lambda tid: (rest_called.__setitem__(0, rest_called[0] + 1) or {}),
        )
        with mock.patch("src.polymarket_research.polymarket_live_harvester._STAGE_B_MARKOUT_SAMPLER", sampler):
            _, _, m_sh, a_px = asyncio.run(
                h._reconcile_maker_entry_fill("OID_MKR_B1", tok_mkr, True, 20.0, 0.991, 0.0)
            )
            time.sleep(0.06)
        flush_stage_b_telemetry()
        self.assertAlmostEqual(m_sh, 20.0, places=2)
        self.assertAlmostEqual(a_px, 0.991, places=3)
        self.assertGreaterEqual(ws_called[0], 1)
        self.assertEqual(rest_called[0], 0)
        mk_lines = [
            json.loads(ln)
            for ln in (telem_dir / "maker_markouts.jsonl").read_text(encoding="utf-8").splitlines()
            if ln.strip()
        ]
        self.assertEqual(len(mk_lines), 1)
        self.assertEqual(mk_lines[0]["sleeve"], "BOND1_UMA_RESOLUTION_CARRY")

    def test_05_leak5_fast_d1_consumer_decoupling_and_async_tick_thread_offload(self) -> None:
        import src.polymarket_research.polymarket_live_executor as exec_mod
        from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor
        from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester

        if getattr(exec_mod, "OrderType", None) is None:
            exec_mod.OrderType = types.SimpleNamespace(GTC="GTC")

        # 1. Fast D1 consumer drains candidate in <50ms even while supervision sleeps 250ms!
        h = PolymarketLiveHarvester.__new__(PolymarketLiveHarvester)
        h.dry_run = True
        h._shutdown_requested = False
        h._fast_d1_cand_lines = deque()
        h._last_d1_cand_poll = time.time()
        h._is_d1_box_halted = lambda: False
        dispatched_at: list[float] = []

        async def _fake_poll_unlocked(now_ts: float, loop: object) -> int:
            cnt = 0
            while h._fast_d1_cand_lines:
                h._fast_d1_cand_lines.popleft()
                dispatched_at.append(time.perf_counter())
                cnt += 1
            return cnt

        h._poll_d1_live_box_candidates_unlocked = _fake_poll_unlocked  # type: ignore[method-assign]

        async def _run_concurrent_test() -> float:
            ev = asyncio.Event()
            wake = asyncio.Event()
            consumer = asyncio.create_task(h._fast_d1_consumer_loop(ev, wake))
            try:
                await asyncio.sleep(0.01)
                t0 = time.perf_counter()

                async def _slow_supervision() -> None:
                    await asyncio.sleep(0.25)

                sup_task = asyncio.create_task(_slow_supervision())
                await asyncio.sleep(0.01)
                t_enq = time.perf_counter()
                h._fast_d1_cand_lines.append('{"box_id":"FAST_1"}')
                ev.set()
                await sup_task
                _ = t0
                return (dispatched_at[0] - t_enq) * 1000.0
            finally:
                h._shutdown_requested = True
                ev.set()
                await consumer

        dispatch_ms = asyncio.run(_run_concurrent_test())
        self.assertEqual(len(dispatched_at), 1)
        self.assertLess(dispatch_ms, 50.0)

        # 2. post_maker_entry_order_async offloads cold/uncached tick & neg_risk lookups to worker thread,
        #    while keeping warm-cache path on the event loop thread with 0 thread hops!
        ex = PolymarketLiveExecutor.__new__(PolymarketLiveExecutor)
        ex.dry_run = False
        ex.client = object()
        ex._can_use_native_async_post_order = lambda: True  # type: ignore[method-assign]
        ex._maybe_schedule_maker_repeg_presign = lambda *a, **kw: None  # type: ignore[method-assign]
        ex._log_order = lambda *a, **kw: None  # type: ignore[method-assign]
        ex._tick_size_cache = {}
        ex._tick_size_checked_at = {}
        ex._ws_tick_size_at = {}
        ex._clob_400_tick_until = {}
        ex._neg_risk_cache = {}

        async def _fake_zero_hop(*a, **kw):
            return {"post_resp": {"orderID": "OID_ASYNC_1", "status": "live"}, "post_ms": 12.3, "sign_ms": 1.1}

        ex._sign_and_post_async_zero_hop = _fake_zero_hop  # type: ignore[method-assign]
        call_threads: list[tuple[str, int]] = []

        def _slow_tick(tid: str, price_hint: float = None) -> float:
            call_threads.append(("tick", threading.get_ident()))
            ex._tick_size_cache[tid] = 0.001
            ex._tick_size_checked_at[tid] = time.monotonic()
            return 0.001

        def _slow_nr(tid: str, explicit_neg_risk=None) -> bool:
            call_threads.append(("nr", threading.get_ident()))
            ex._neg_risk_cache[tid] = False
            return False

        ex.get_token_tick_size = _slow_tick  # type: ignore[method-assign]
        ex.get_token_neg_risk = _slow_nr  # type: ignore[method-assign]

        async def _exercise_maker_async() -> tuple[int, dict, dict]:
            loop_tid = threading.get_ident()
            r_cold = await ex.post_maker_entry_order_async("701" * 9, 0.991, 15.0, side="BUY")
            r_warm = await ex.post_maker_entry_order_async("701" * 9, 0.991, 15.0, side="BUY")
            return loop_tid, r_cold, r_warm

        main_tid, res_cold, res_warm = asyncio.run(_exercise_maker_async())
        self.assertTrue(res_cold["success"])
        self.assertTrue(res_warm["success"])
        # Cold call offloaded both SDK lookups onto worker thread; subsequent warm call ran on loop thread!
        self.assertEqual(call_threads[0][1] != main_tid, True)
        self.assertEqual(call_threads[1][1] != main_tid, True)

    def test_07_kmia_nov7_asos_quantization_synoptic_contradiction_and_paused_wprune1_guard(self) -> None:
        from datetime import date, datetime, timezone
        from pathlib import Path
        import json
        from unittest import mock
        import src.polymarket_research.alpha_124_shadow_daemon as a124_mod
        from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester
        from src.polymarket_research.riskless_protocol_v2_expansion import (
            compute_running_metar_extrema,
            detect_w_prune1_metar_slate_arb,
            evaluate_clinched_ws_book_snipe_impl,
            extract_canonical_event_keys,
            parse_routine_metar_temp_c,
            register_clinched_ws_watch_cand_impl,
        )
        from src.polymarket_research.weather_metar_engine import (
            WeatherBucket,
            WeatherEventSpec,
            compute_weather_probabilities,
            has_metar_oracle_contradiction,
            parse_metar_line,
        )

        # 1. Exact Nov 7, 2026 KMIA corrupted METAR sequence:
        #    070853Z reported `T02240211 $` (22.4C = impossible whole-F ASOS code; 72F=22.2C, 73F=22.8C),
        #    followed by 071153Z `20233` (6h min = 23.3C = 74F) and 080453Z `403060233` (24h min = 23.3C = 74F).
        kmia_0753 = "METAR KMIA 070753Z 07006KT 10SM FEW025 23/21 A3001 RMK AO2 SLP160 T02330211"
        kmia_0853_bad = "METAR KMIA 070853Z 06005KT 10SM FEW025 22/21 A3002 RMK AO2 SLP162 T02240211 $"
        kmia_1153_syn = "METAR KMIA 071153Z 07007KT 10SM FEW028 24/21 A3004 RMK AO2 SLP169 10256 20233 53014 T02390211"
        kmia_0453_24h = "METAR KMIA 080453Z 08008KT 10SM SCT030 25/22 A3004 RMK AO2 SLP168 T02500217 403060233"

        self.assertIsNotNone(parse_routine_metar_temp_c(kmia_0753, station_icao="KMIA", unit="F"))
        self.assertIsNone(parse_routine_metar_temp_c(kmia_0853_bad, station_icao="KMIA", unit="F"))
        # Station-date series MUST return None (tainted) rather than silently dropping 0853Z and pruning the opposite bracket!
        self.assertIsNone(
            compute_running_metar_extrema([kmia_0753, kmia_0853_bad, kmia_1153_syn], station_icao="KMIA", unit="F")
        )
        kmia_brackets = [
            {"low": -99, "high": 71, "condition_id": "c1", "yes_token_id": "y1", "no_token_id": "n1", "yes_ask": 0.01, "yes_ask_size": 50, "no_ask": 0.99, "no_ask_size": 50},
            {"low": 72, "high": 73, "condition_id": "c2", "yes_token_id": "y2", "no_token_id": "n2", "yes_ask": 0.84, "yes_ask_size": 50, "no_ask": 0.17, "no_ask_size": 50},
            {"low": 74, "high": 75, "condition_id": "c3", "yes_token_id": "y3", "no_token_id": "n3", "yes_ask": 0.16, "yes_ask_size": 50, "no_ask": 0.977, "no_ask_size": 50},
            {"low": 76, "high": 199, "condition_id": "c4", "yes_token_id": "y4", "no_token_id": "n4", "yes_ask": 0.01, "yes_ask_size": 50, "no_ask": 0.99, "no_ask_size": 50},
        ]
        self.assertEqual(
            detect_w_prune1_metar_slate_arb(
                kmia_brackets,
                [kmia_0753, kmia_0853_bad, kmia_1153_syn, kmia_0453_24h],
                station_icao="KMIA",
                unit="F",
                metric="LOW",
            ),
            [],
        )

        # 2. Synoptic 6h (`20233` / `10256`) & 24h (`403060233`) contradiction catches glitches EVEN WHEN T-group is on valid ASOS lattice (`T0222` = 72.0F)
        kmia_0853_lattice_glitch = "METAR KMIA 070853Z 06005KT 10SM FEW025 22/21 A3002 RMK AO2 SLP162 T02220211"
        self.assertIsNotNone(parse_routine_metar_temp_c(kmia_0853_lattice_glitch, station_icao="KMIA", unit="F"))
        self.assertIsNone(
            compute_running_metar_extrema([kmia_0753, kmia_0853_lattice_glitch, kmia_1153_syn], station_icao="KMIA", unit="F")
        )
        self.assertIsNone(
            compute_running_metar_extrema([kmia_0753, kmia_0853_lattice_glitch, kmia_0453_24h], station_icao="KMIA", unit="F")
        )
        # Body-vs-T internal bit-flip mismatch (`24/21` vs `T01440211` = 14.4C) is also rejected
        self.assertIsNone(
            parse_routine_metar_temp_c(
                "METAR KMIA 070853Z 06005KT 10SM FEW025 24/21 A3002 RMK AO2 T01440211",
                station_icao="KMIA",
                unit="F",
            )
        )

        # 3. Path B (`weather_metar_engine` + `Alpha124ShadowDaemon`) flags `is_anomalous` + `has_oracle_contradiction` and blocks Dead-NO / Solar locks
        ref_dt = datetime(2026, 11, 7, 12, 0, tzinfo=timezone.utc)
        obs_bad = parse_metar_line(kmia_0853_bad, "KMIA", ref_dt, "America/New_York")
        obs_syn = parse_metar_line(kmia_1153_syn, "KMIA", ref_dt, "America/New_York")
        obs_lat = parse_metar_line(kmia_0853_lattice_glitch, "KMIA", ref_dt, "America/New_York")
        assert obs_bad is not None and obs_syn is not None and obs_lat is not None
        self.assertTrue(obs_bad.is_anomalous)
        self.assertFalse(obs_lat.is_anomalous)
        self.assertAlmostEqual(float(obs_syn.rmk_6h_min_c or 0.0), 23.3, places=2)
        self.assertAlmostEqual(float(obs_syn.rmk_6h_max_c or 0.0), 25.6, places=2)
        self.assertTrue(has_metar_oracle_contradiction([obs_bad]))
        self.assertTrue(has_metar_oracle_contradiction([obs_lat, obs_syn]))

        sp_mia = WeatherEventSpec(
            event_id="318559",
            slug="miami-low-nov-7",
            series_slug="miami-daily-lowest-temperature",
            title="Lowest temperature in Miami on November 7?",
            icao="KMIA",
            city="Miami",
            lat=25.7959,
            lon=-80.2870,
            tz_name="America/New_York",
            obs_date=date(2026, 11, 7),
            metric="LOW",
            unit="F",
            fee_type="zero_fees",
            end_date_iso="2026-11-08T04:59:59Z",
            buckets=[
                WeatherBucket("6707501", "0xc1", "71°F or below", "71F-", "ty1", "tn1", "F", -99.0, 71.0, neg_risk=True, question_index=0),
                WeatherBucket("6707502", "0xc2", "72-73°F", "72-73F", "ty2", "tn2", "F", 72.0, 73.0, neg_risk=True, question_index=1),
                WeatherBucket("6707503", "0xc3", "74-75°F", "74-75F", "ty3", "tn3", "F", 74.0, 75.0, neg_risk=True, question_index=2),
                WeatherBucket("6707504", "0xc4", "76°F or higher", "76F+", "ty4", "tn4", "F", 76.0, 199.0, neg_risk=True, question_index=3),
            ],
        )
        eval_late = datetime(2026, 11, 8, 3, 30, tzinfo=timezone.utc)
        res_mia = compute_weather_probabilities(sp_mia, eval_late, [obs_lat, obs_syn], {})
        self.assertTrue(res_mia["has_oracle_contradiction"])
        self.assertFalse(res_mia["is_solar_lock"])

        cand_tmp = Path(self._tmp_dir.name) / "kmia_contradicted_cands.jsonl"
        with mock.patch.object(a124_mod, "D1_LIVE_CANDIDATES_FILE", cand_tmp):
            dm = a124_mod.Alpha124ShadowDaemon(single_scan=False)
            dm.weather_events = {"318559": sp_mia}
            dm.metar_cache["KMIA_2026-11-07"] = (eval_late.timestamp(), [obs_lat, obs_syn])
            dm.taf_cache["KMIA_2026-11-07"] = (eval_late.timestamp(), {})
            dm.ensemble_cache["KMIA"] = (eval_late.timestamp(), {"ok": True})
            with (
                mock.patch.object(a124_mod, "compute_weather_probabilities", return_value=res_mia),
                mock.patch.object(
                    dm,
                    "fetch_books_batch",
                    return_value={
                        t: {"bids": [{"price": "0.97", "size": "40"}], "asks": [{"price": "0.98", "size": "40"}]}
                        if t.startswith("tn")
                        else {"bids": [{"price": "0.01", "size": "40"}], "asks": [{"price": "0.02", "size": "40"}]}
                        for t in ("ty1", "tn1", "ty2", "tn2", "ty3", "tn3", "ty4", "tn4")
                    },
                ),
            ):
                asyncio.run(dm.scan_weather_markets([]))
                self.assertEqual(getattr(dm, "_ws_dead_q_by_event", {}).get("318559", set()), set())
                self.assertFalse(cand_tmp.exists())

        # 4. All valid FMH-1 whole-F -> 0.1C ASOS conversions (-30F..120F) pass cleanly, AND international 0.1C stations (RJTT) allow arbitrary tenths (22.4C)
        for f_val in range(-30, 121):
            c_tenths = int(round(((f_val - 32) * 50.0) / 9.0))
            sgn_d = "1" if c_tenths < 0 else "0"
            t_grp = f"T{sgn_d}{abs(c_tenths):03d}0000"
            body_int = int(round(c_tenths / 10.0))
            body_s = f"M{abs(body_int):02d}" if body_int < 0 else f"{body_int:02d}"
            ln_valid = f"METAR KLGA 071251Z 18008KT 10SM CLR {body_s}/{body_s} A3000 RMK AO2 {t_grp}"
            self.assertIsNotNone(parse_routine_metar_temp_c(ln_valid, station_icao="KLGA", unit="F"))
            obs_v = parse_metar_line(ln_valid, "KLGA", ref_dt, "America/New_York")
            assert obs_v is not None
            self.assertFalse(obs_v.is_anomalous)

        obs_intl = parse_metar_line(
            "METAR RJTT 070853Z 06005KT 9999 FEW025 22/21 Q1015 RMK T02240211",
            "RJTT",
            ref_dt,
            "Asia/Tokyo",
        )
        assert obs_intl is not None
        self.assertFalse(obs_intl.is_anomalous)

        # 5. Canonical EVTWX keys cover all international prefixes (WSSS, HKO, UUWW, FACT, MMMX, NZWN),
        #    production config keeps W_PRUNE1_DEAD_NO_BOND unpaused (protected by METAR contradiction guard + 1-slot cap)
        #    while keeping multi-leg W_PRUNE1_NR0_BASKET paused, AND dynamic paused_riskless_sleeves is honored if set!
        for city_ast, code_exp in (
            ("New York City_KLGA", "KLGA"),
            ("Singapore_WSSS", "WSSS"),
            ("Hong Kong_HKO", "HKO"),
            ("Moscow_UUWW", "UUWW"),
            ("Cape Town_FACT", "FACT"),
            ("Mexico City_MMMX", "MMMX"),
            ("Wellington_NZWN", "NZWN"),
        ):
            ks = extract_canonical_event_keys({"asset": city_ast, "expiry_ts": 1_794_113_999.0, "sleeve_source": "W_PRUNE1_DEAD_NO_BOND"})
            self.assertIn(f"EVTWX:{code_exp}:{1_794_113_999 // 43200}", ks)

        prod_cfg = json.loads((Path(__file__).resolve().parents[1] / "config" / "polymarket_strategy_and_risk.json").read_text(encoding="utf-8"))
        self.assertNotIn("W_PRUNE1_DEAD_NO_BOND", prod_cfg["riskless_boxes"]["paused_riskless_sleeves"])
        self.assertIn("W_PRUNE1_NR0_BASKET", prod_cfg["riskless_boxes"]["paused_riskless_sleeves"])
        h_live = PolymarketLiveHarvester.__new__(PolymarketLiveHarvester)
        h_live.dry_run = False
        h_live.enforce_paused_riskless_sleeves = True
        h_live.executor = types.SimpleNamespace(auth_mode="LIVE", dry_run=False, client=object())
        h_live._clinched_ws_watchlist = {
            "909" * 9: {
                "sleeve_source": "W_PRUNE1_DEAD_NO_BOND",
                "p_model": 1.0,
                "expiry_ts": time.time() + 3600.0,
                "max_box_cost_net": 0.994,
                "leg_a_token_id": "909" * 9,
                "leg_a_opp_token_id": "808" * 9,
            }
        }
        from src.polymarket_research.holistic_strategy_governance import GLOBAL_GOVERNANCE_MANAGER

        snap_paused = json.loads(json.dumps(GLOBAL_GOVERNANCE_MANAGER.snapshot))
        snap_paused["riskless_boxes"]["paused_riskless_sleeves"] = list(
            snap_paused["riskless_boxes"].get("paused_riskless_sleeves") or []
        ) + ["W_PRUNE1_DEAD_NO_BOND"]
        with mock.patch.object(type(GLOBAL_GOVERNANCE_MANAGER), "snapshot", new_callable=mock.PropertyMock, return_value=snap_paused):
            self.assertFalse(
                register_clinched_ws_watch_cand_impl(
                    h_live,
                    {
                        "sleeve_source": "W_PRUNE1_DEAD_NO_BOND",
                        "p_model": 1.0,
                        "expiry_ts": time.time() + 3600.0,
                        "leg_a_token_id": "909" * 9,
                        "leg_a_opp_token_id": "808" * 9,
                        "leg_a_market_id": "6707503",
                    },
                )
            )
            self.assertIsNone(
                evaluate_clinched_ws_book_snipe_impl(
                    h_live,
                    "909" * 9,
                    bk_win={"asks": [{"price": "0.977", "size": "20"}]},
                )
            )


if __name__ == "__main__":
    unittest.main()
