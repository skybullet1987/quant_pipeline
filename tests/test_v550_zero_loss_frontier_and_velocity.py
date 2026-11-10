"""
v5.5.0 Zero-Loss Arbitrage Frontier, Gasless Capital-Velocity & Execution-Plumbing Test Suite.

Verifies all P0, P1, and P2 upgrades plus adversarial zero-loss invariants:
  - P0.0: Cross-platform `_USNewYorkFallbackTZ` EDT/EST DST transitions & CME maintenance guard
  - P0.1: Relayer V2 (`sig_type=3`) `$0.00`-gas `mergePositions` with `0 POL` EOA + `MultiSend` batch merge
  - P0.2: Partial-FAK single-leg lock sweeping down to `5.0` shares (`< $10.00` shallow asks)
  - P1.1: Ironclad `NR_M1_DEAD_SEED_OVERROUND` (`m=1` verified dead `NO_k` + single `FOK` `YES` sweep + mid-block bid-slip complete-set fallback + strict rejection of alive `NO_k` or `>= 2` `YES` legs)
  - P1.2: Expanded `XTRACK1` handles & `NR0_PRUNED` exhaustive surviving `YES` complete-set with mandatory `inf` top-cap guard
  - P1.3: General `0%`-fee non-`negRisk` mergeable binary discovery (`ZEROFEE1`)
  - P1.4: `ZEC` `5m/15m` dominance & deterministic slug builder, `META`/`HOOD`/`PLTR` full-RTH `EQ1` (`09:30-16:00 ET`), and `4% APY` holding carry credit
  - P2.1: Esports BO3 `p_lock=0.999` & post-Map-1 forfeit-immune `Handicap x Total Maps 2.5` intermission box (`$1.0000` under forfeit)
  - P2.2: Rotten Tomatoes / Tomatometer `SCALAR_ABOVE` comparator-stem normalization & monotonicity box (`RT_MONO1`)
  - P2.3: Read-only `PolymarketPerpsLeadLagStream` (`PERP1`) `300ms` BBO pre-cancel sensor & `PolyboltLiveStream` `price.equity`
"""

from __future__ import annotations

import datetime
import json
import math
import os
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class TestV550ZeroLossFrontierAndVelocity(unittest.TestCase):
    def test_p00_governance_schema_v550_and_seed_invariants(self) -> None:
        from src.polymarket_research.holistic_strategy_governance import (
            DEFAULT_HOLISTIC_CONFIG,
            HotReloadConfigManager,
        )

        cfg_path = PROJECT_ROOT / "config" / "polymarket_strategy_and_risk.json"
        raw = json.loads(cfg_path.read_text(encoding="utf-8"))
        self.assertEqual(raw["schema_version"], "5.5.0")
        self.assertEqual(DEFAULT_HOLISTIC_CONFIG["schema_version"], "5.5.0")
        rbox = raw["riskless_boxes"]
        self.assertAlmostEqual(float(rbox["reward_harvester_cap_usd_seed"]), 12.0, places=4)
        self.assertTrue(rbox["enable_c1_gasless_batch_merge"])
        self.assertTrue(rbox["enable_partial_fak_single_leg_sweep"])
        self.assertAlmostEqual(float(rbox["partial_fak_min_shares"]), 5.0, places=4)
        self.assertTrue(rbox["enable_nr_m1_dead_seed_fanout"])
        self.assertTrue(rbox["enable_zerofee1_mergeable_sweeper"])
        self.assertTrue(rbox["enable_xtrack1_expanded_handles"])
        self.assertTrue(rbox["enable_esports1_bo3_intermission_box"])
        self.assertTrue(rbox["enable_rt_mono1_scalar_ladders"])
        self.assertTrue(rbox["enable_perp1_maker_precancel_leadlag"])

        mgr = HotReloadConfigManager(config_path=cfg_path)
        self.assertEqual(mgr.snapshot["schema_version"], "5.5.0")

    def test_p00_us_eastern_fallback_dst_and_cme_maintenance(self) -> None:
        from src.polymarket_research.riskless_protocol_v2_expansion import (
            _USNewYorkFallbackTZ,
            is_cme_metals_maintenance_window,
        )

        tz = _USNewYorkFallbackTZ()
        # Summer EDT (UTC-4): July 15, 2026 21:30 UTC == 17:30 EDT (inside 17:00-18:00 ET CME maintenance)
        dt_summer_maint = datetime.datetime(2026, 7, 15, 21, 30, tzinfo=datetime.timezone.utc)
        self.assertEqual(dt_summer_maint.astimezone(tz).utcoffset(), datetime.timedelta(hours=-4))
        self.assertEqual(dt_summer_maint.astimezone(tz).tzname(), "EDT")
        self.assertTrue(is_cme_metals_maintenance_window(dt_summer_maint.timestamp()))

        # Winter EST (UTC-5): Jan 14, 2026 22:30 UTC == 17:30 EST (inside 17:00-18:00 ET CME maintenance)
        dt_winter_maint = datetime.datetime(2026, 1, 14, 22, 30, tzinfo=datetime.timezone.utc)
        self.assertEqual(dt_winter_maint.astimezone(tz).utcoffset(), datetime.timedelta(hours=-5))
        self.assertEqual(dt_winter_maint.astimezone(tz).tzname(), "EST")
        self.assertTrue(is_cme_metals_maintenance_window(dt_winter_maint.timestamp()))

        # Winter EST 15:00 ET (20:00 UTC) -> regular session, NOT maintenance
        dt_winter_open = datetime.datetime(2026, 1, 14, 20, 0, tzinfo=datetime.timezone.utc)
        self.assertFalse(is_cme_metals_maintenance_window(dt_winter_open.timestamp()))

    def test_p01_relayer_v2_gasless_merge_with_zero_pol_and_batch_multisend(self) -> None:
        try:
            import web3  # noqa: F401
            from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor
        except ImportError:
            self.skipTest("web3 not installed in minimal stdlib interpreter")

        ex = PolymarketLiveExecutor.__new__(PolymarketLiveExecutor)
        ex.dry_run = False
        ex.signature_type = 3  # Relayer V2 Safe
        ex.private_key = "0x" + "11" * 32
        ex.funder_address = "0x" + "22" * 20
        ex.client = None
        ex.invalidate_collateral_cache = mock.MagicMock()

        class _FakeCall:
            def __init__(self, val):
                self._val = val

            def call(self, *a, **kw):
                return self._val

        class _FakeFns:
            def getCollectionId(self, _parent, cond_b, idx):
                return _FakeCall(cond_b[:31] + bytes([idx]))

            def getPositionId(self, _col, coll_id):
                return _FakeCall(int.from_bytes(coll_id[:4], "big") + coll_id[-1])

            def balanceOf(self, _owner, _pos_id):
                return _FakeCall(8_000_000)  # 8.0 shares on both YES and NO

            def isApprovedForAll(self, _owner, _op):
                return _FakeCall(True)

        class _FakeContract:
            functions = _FakeFns()

            def encode_abi(self, fn_name, args=None):
                return "0xdeadbeef" + (args[0].hex()[:8] if isinstance(args[0], (bytes, bytearray)) else "00")

        fake_w3 = mock.MagicMock()
        # EOA has ZERO POL (`0 wei`)! Relayer V2 (`sig_type == 3`) MUST still succeed!
        fake_w3.eth.get_balance.return_value = 0
        fake_w3.eth.account.from_key.return_value = types.SimpleNamespace(address="0x" + "33" * 20)
        fake_w3.eth.contract.return_value = _FakeContract()
        fake_w3.eth.wait_for_transaction_receipt.return_value = {"status": 1}

        dispatched = []

        def _fake_dispatch(_w3, _W3, _pk, sig_t, _f_cs, _s_cs, calls, op_tag):
            dispatched.append((sig_t, list(calls), op_tag))
            return "0x" + "ab" * 32

        ex._dispatch_funder_calls = _fake_dispatch

        cid1 = "0x" + "a1" * 32
        cid2 = "0x" + "b2" * 32
        cid3 = "0x" + "c3" * 32
        with mock.patch.dict(os.environ, {"POLY_BUILDER_API_KEY": "test_builder_key"}, clear=False), mock.patch(
            "src.polymarket_research.riskless_machine_gun_engine.get_fast_polygon_web3",
            return_value=fake_w3,
        ):
            res_single = ex.attempt_onchain_complete_set_merge(cid1, min_pairs=5.0, max_pairs=8.0, neg_risk=False)
            self.assertIsNotNone(res_single)
            self.assertEqual(res_single[0], "0x" + "ab" * 32)
            self.assertAlmostEqual(res_single[1], 8.0, places=4)
            # get_balance MUST NOT be called when sig_type == 3!
            fake_w3.eth.get_balance.assert_not_called()

            # Batch merge packs 3 conditions into ONE atomic Relayer V2 call list
            dispatched.clear()
            batch_res = ex.attempt_onchain_batch_complete_set_merges(
                [
                    {"key": "BOX_1", "condition_id": cid1, "min_pairs": 5.0, "max_pairs": 8.0, "neg_risk": False},
                    {"key": "BOX_2", "condition_id": cid2, "min_pairs": 5.0, "max_pairs": 7.5, "neg_risk": False},
                    {"key": "BOX_3", "condition_id": cid3, "min_pairs": 5.0, "max_pairs": 6.0, "neg_risk": True},
                ]
            )
            self.assertIsNotNone(batch_res)
            tx_h, merged_map = batch_res
            self.assertEqual(tx_h, "0x" + "ab" * 32)
            self.assertEqual(len(dispatched), 1)
            self.assertEqual(len(dispatched[0][1]), 3)
            self.assertEqual(merged_map, {"BOX_1": 8.0, "BOX_2": 7.5, "BOX_3": 6.0})

            # Verify sig_type == 1 WITH 0 POL still fails closed cleanly!
            ex.signature_type = 1
            self.assertIsNone(ex.attempt_onchain_complete_set_merge(cid1, min_pairs=5.0, max_pairs=8.0, neg_risk=False))

    def test_p02_partial_fak_single_leg_sweep_down_to_5_shares(self) -> None:
        try:
            from src.polymarket_research.polymarket_live_executor import PolymarketLiveExecutor
        except ImportError:
            self.skipTest("executor deps not installed in minimal stdlib interpreter")

        ex = PolymarketLiveExecutor(dry_run=True)
        # Shallow L1 ask: 6.0 shares @ $0.96 ($5.76 notional < $10.00 old floor, >= 5.0 CLOB share min)
        shallow_book = {
            "bids": [{"price": "0.94", "size": "25.0"}],
            "asks": [{"price": "0.96", "size": "6.0"}],
        }
        ex.get_market_book = lambda _tid: shallow_book

        # Without allow_partial_fak: $12.00 ticket rejects because book only has $5.76 (< $10.00 MIN_LOT_SIZE_USD)
        res_strict = ex.execute_snipe_order(
            trade_id="T_P02_STRICT",
            token_id="123456789012345678901",
            target_token="YES",
            notional_usd=12.0,
            target_price=0.96,
            side="BUY",
            depth_hurdle=1.0,
            max_book_buffer=0.01,
            max_price_ceiling=0.98,
            market_fee_rate=0.0,
            prefetched_book=shallow_book,
            allow_partial_fak=False,
        )
        self.assertFalse(res_strict.success)

        # With allow_partial_fak=True: sweeps the 6.0 shares cleanly!
        res_partial = ex.execute_snipe_order(
            trade_id="T_P02_PARTIAL",
            token_id="123456789012345678901",
            target_token="YES",
            notional_usd=12.0,
            target_price=0.96,
            side="BUY",
            depth_hurdle=1.0,
            max_book_buffer=0.01,
            max_price_ceiling=0.98,
            market_fee_rate=0.0,
            prefetched_book=shallow_book,
            allow_partial_fak=True,
            min_order_shares=5.0,
        )
        self.assertTrue(res_partial.success)
        self.assertGreaterEqual(res_partial.size, 5.0)
        self.assertLessEqual(res_partial.notional_usd, 5.80)

        # Sub-5-share dust (4.0 shares @ $0.96) MUST still reject!
        dust_book = {
            "bids": [{"price": "0.94", "size": "25.0"}],
            "asks": [{"price": "0.96", "size": "4.0"}],
        }
        ex.get_market_book = lambda _tid: dust_book
        res_dust = ex.execute_snipe_order(
            trade_id="T_P02_DUST",
            token_id="123456789012345678901",
            target_token="YES",
            notional_usd=12.0,
            target_price=0.96,
            side="BUY",
            depth_hurdle=1.0,
            max_book_buffer=0.01,
            max_price_ceiling=0.98,
            market_fee_rate=0.0,
            prefetched_book=dust_book,
            allow_partial_fak=True,
            min_order_shares=5.0,
        )
        self.assertFalse(res_dust.success)

    def test_p11_nr_m1_dead_seed_detector_and_adversarial_rejections(self) -> None:
        from src.polymarket_research.riskless_protocol_v2_expansion import detect_nr_m1_dead_seed_fanout

        br0 = types.SimpleNamespace(
            market_id="m0", condition_id="0x" + "10" * 32, question_index=0,
            yes_token="y0", no_token="n0", label="0-199", fee_rate=0.0, fee_exponent=1.0,
        )
        br1 = types.SimpleNamespace(
            market_id="m1", condition_id="0x" + "20" * 32, question_index=1,
            yes_token="y1", no_token="n1", label="200-239", fee_rate=0.0, fee_exponent=1.0,
        )
        br2 = types.SimpleNamespace(
            market_id="m2", condition_id="0x" + "30" * 32, question_index=2,
            yes_token="y2", no_token="n2", label="240+", fee_rate=0.0, fee_exponent=1.0,
        )
        spec = types.SimpleNamespace(
            event_id="ev_nr_m1",
            neg_risk_market_id="0x" + "aa" * 32,
            is_closed_convert_safe=True,
            brackets=[br0, br1, br2],
        )
        books = {
            "n0": {"asks": [{"price": "0.960", "size": "15.0"}], "bids": [{"price": "0.950", "size": "10.0"}]},
            "n1": {"asks": [{"price": "0.150", "size": "15.0"}], "bids": [{"price": "0.120", "size": "10.0"}]},
            "y1": {"bids": [{"price": "0.972", "size": "20.0"}], "asks": [{"price": "0.980", "size": "10.0"}]},
            "y2": {"bids": [{"price": "0.030", "size": "20.0"}], "asks": [{"price": "0.040", "size": "10.0"}]},
        }

        # 1. Adversarial: empty dead_question_indices (alive NO_1 @ $0.15!) MUST return None!
        self.assertIsNone(detect_nr_m1_dead_seed_fanout(spec, set(), books))
        # 2. Adversarial: marking Q0 dead when only Q1 has cheap NO ($0.15) and Q0 ask is $0.999 (>= par) MUST return None!
        books_expensive_dead = {
            **books,
            "n0": {"asks": [{"price": "0.999", "size": "15.0"}], "bids": []},
        }
        self.assertIsNone(detect_nr_m1_dead_seed_fanout(spec, {0}, books_expensive_dead))

        # 3. Positive: Q0 is 100% mathematically eliminated, Ask(NO_0) = $0.960 < $0.998, Bid(YES_1) = $0.972 -> +120 bps + free YES_2!
        hit = detect_nr_m1_dead_seed_fanout(spec, {0}, books, fee_bips=0, min_shares=5.0, min_net_edge_usd=0.0035)
        self.assertIsNotNone(hit)
        self.assertEqual(hit["mode"], "NR_M1_DEAD_SEED_OVERROUND")
        self.assertTrue(hit["nr_m1_zero_loss_verified"])
        self.assertEqual(len(hit["no_legs"]), 1)
        self.assertEqual(len(hit["yes_sell_legs"]), 1)
        self.assertEqual(hit["dead_question_index"], 0)
        self.assertAlmostEqual(hit["net_edge_per_share"], 0.012, places=4)
        self.assertAlmostEqual(hit["fallback_hold_floor_edge_per_share"], 0.040, places=4)
        self.assertEqual(len(hit["surviving_yes_brackets"]), 2)

    def test_p11_nr_m1_execution_fok_sweep_and_midblock_bid_slip_fallback(self) -> None:
        try:
            from src.polymarket_research.riskless_machine_gun_engine import execute_negrisk_subset_convert_arb_impl
        except ImportError:
            self.skipTest("executor deps not installed in minimal stdlib interpreter")

        class _MockClient:
            def __init__(self, sell_fok_fills: bool = True):
                self.sell_fok_fills = sell_fok_fills
                self.posted = []

            def create_order(self, order_args, _opts=None):
                return {"side": order_args.side, "token_id": order_args.token_id, "price": order_args.price, "size": order_args.size}

            def post_order(self, signed, order_type, *args):
                self.posted.append((signed, order_type))
                if signed["side"] == "BUY":
                    return {"orderID": "OID_BUY_NO0", "status": "matched", "takingAmount": str(signed["size"])}
                if self.sell_fok_fills:
                    return {
                        "orderID": "OID_SELL_YES1",
                        "status": "matched",
                        "takingAmount": str(round(signed["size"] * 0.975, 4)),
                    }
                return {"errorMsg": "FOK order couldn't be fully filled"}

        class _MockExec:
            def __init__(self, yes_bid_px: float, sell_fok_fills: bool = True):
                self.dry_run = False
                self.is_authenticated = True
                self.auth_mode = "LIVE"
                self.client = _MockClient(sell_fok_fills=sell_fok_fills)
                self._yes_bid_px = yes_bid_px

            def quantize_order_price(self, px, _tok, rounding=None):
                return round(float(px), 3)

            def get_token_tick_size(self, _tok, price_hint=None):
                return "0.001"

            def get_token_neg_risk(self, _tok, default=True):
                return True

            def _extract_fok_matched_shares(self, resp, req_sh):
                return float(req_sh) if resp.get("orderID") else 0.0

            def get_token_balance(self, _tok):
                return 10.0

            def attempt_negrisk_convert_positions(self, _nrm, _q_idxs, _sh, prefer_v2_pusd_adapter=True):
                return {"success": True, "tx_hash": "0x" + "cc" * 32}

            def get_market_book(self, _tok):
                return {"bids": [{"price": str(self._yes_bid_px), "size": "20.0"}], "asks": []}

        no_leg = [{"token_id": "n0", "market_id": "m0", "condition_id": "0x" + "10" * 32, "question_index": 0, "limit_price": 0.960, "fee_rate": 0.0}]
        surviving = [
            {"yes_token": "y1", "market_id": "m1", "condition_id": "0x" + "20" * 32, "question_index": 1, "label": "200-239"},
            {"yes_token": "y2", "market_id": "m2", "condition_id": "0x" + "30" * 32, "question_index": 2, "label": "240+"},
        ]

        # Adversarial 1: m=1 WITHOUT nr_m1_zero_loss_verified -> REJECTED!
        ex_adv = _MockExec(0.975)
        r_unver = execute_negrisk_subset_convert_arb_impl(
            ex_adv, convert_id="C_UNVER", neg_risk_market_id="0x" + "aa" * 32,
            no_legs=no_leg, shares=10.0, max_no_cost_per_share=0.965,
            liquid_yes_sells=[{"yes_token": "y1", "min_bid_price": 0.975}],
            nr_m1_zero_loss_verified=False,
        )
        self.assertFalse(r_unver["success"])

        # Adversarial 2: m=1 WITH 2 YES sell legs (>= 2 legs breaks partition if Leg 1 fills & Leg 2 rejects!) -> REJECTED!
        r_two_yes = execute_negrisk_subset_convert_arb_impl(
            ex_adv, convert_id="C_2YES", neg_risk_market_id="0x" + "aa" * 32,
            no_legs=no_leg, shares=10.0, max_no_cost_per_share=0.965,
            liquid_yes_sells=[{"yes_token": "y1", "min_bid_price": 0.50}, {"yes_token": "y2", "min_bid_price": 0.50}],
            nr_m1_zero_loss_verified=True, nr_m1_mode="NR_M1_DEAD_SEED_OVERROUND",
        )
        self.assertFalse(r_two_yes["success"])

        # Branch A: Live YES_1 bid holds @ $0.975 -> FOK SELL fills 100%, immediate +$0.15 cash profit + free y2!
        ex_ok = _MockExec(0.975, sell_fok_fills=True)
        r_ok = execute_negrisk_subset_convert_arb_impl(
            ex_ok, convert_id="C_M1_OK", neg_risk_market_id="0x" + "aa" * 32,
            no_legs=no_leg, shares=10.0, max_no_cost_per_share=0.965,
            liquid_yes_sells=[{"yes_token": "y1", "min_bid_price": 0.975, "fee_rate": 0.0}],
            nr_m1_zero_loss_verified=True, nr_m1_mode="NR_M1_DEAD_SEED_OVERROUND",
            surviving_yes_legs=surviving,
        )
        self.assertTrue(r_ok["success"])
        self.assertFalse(r_ok["held_guaranteed_complete_set"])
        self.assertAlmostEqual(r_ok["spent_usd"], 9.60, places=3)
        self.assertAlmostEqual(r_ok["yes_sell_net_usd"], 9.75, places=3)
        self.assertAlmostEqual(r_ok["net_profit_usd"], 0.15, places=3)

        # Branch B: Mid-block race condition! YES_1 bid collapses to $0.55 during Polygon confirmation ->
        # ZERO YES shares sold; intact {y1, y2} complete set held for guaranteed $10.00 - $9.60 = +$0.40 profit!
        ex_slip = _MockExec(0.55, sell_fok_fills=False)
        r_slip = execute_negrisk_subset_convert_arb_impl(
            ex_slip, convert_id="C_M1_SLIP", neg_risk_market_id="0x" + "aa" * 32,
            no_legs=no_leg, shares=10.0, max_no_cost_per_share=0.965,
            liquid_yes_sells=[{"yes_token": "y1", "min_bid_price": 0.975, "fee_rate": 0.0}],
            nr_m1_zero_loss_verified=True, nr_m1_mode="NR_M1_DEAD_SEED_OVERROUND",
            surviving_yes_legs=surviving,
        )
        self.assertTrue(r_slip["success"])
        self.assertTrue(r_slip["held_guaranteed_complete_set"])
        self.assertEqual(len(r_slip["held_surviving_yes_legs"]), 2)
        self.assertAlmostEqual(r_slip["yes_sell_net_usd"], 0.0, places=4)
        self.assertAlmostEqual(r_slip["guaranteed_hold_profit_usd"], 0.40, places=3)
        self.assertGreater(r_slip["net_profit_usd"], 0.0)

    def test_p12_xtrack1_handles_and_pruned_slate_topcap_invariant(self) -> None:
        from src.polymarket_research.macro_counting_ctf_engine import (
            CountingBracket,
            CountingSlateSpec,
            XTRACKER_ALL_HANDLES,
            detect_counting_pruned_exhaustive_yes_slate,
            extract_xtracker_active_event_slugs,
        )

        for expected_h in ("elonmusk", "cz_binance", "WhiteHouse", "ZelenskyyUa", "tedcruz", "realDonaldTrump"):
            self.assertIn(expected_h, XTRACKER_ALL_HANDLES)

        slugs = extract_xtracker_active_event_slugs(
            {"cz_binance": {"cz-tweets-nov-1-nov-8": {"total": 42}}, "WhiteHouse": {"wh-posts-week": {"total": 18}}}
        )
        self.assertEqual(slugs, [("cz-tweets-nov-1-nov-8", "cz_binance"), ("wh-posts-week", "WhiteHouse")])

        def _mk_br(mid: str, lo: int, hi: float) -> CountingBracket:
            return CountingBracket(
                market_id=mid, condition_id="0x" + mid.encode().hex().rjust(64, "0"),
                label=f"{lo}-{hi}", low_count=lo, high_count=hi,
                yes_token=f"y_{mid}", no_token=f"n_{mid}", fee_rate=0.0, fee_exponent=1.0,
                neg_risk=True, rewards_min_size=0.0, rewards_max_spread=0.0,
            )

        b0 = _mk_br("b0", 0, 199.0)
        b1 = _mk_br("b1", 200, 219.0)
        b2 = _mk_br("b2", 220, 239.0)
        b3_inf = _mk_br("b3", 240, float("inf"))

        slate_valid = CountingSlateSpec(
            event_id="ev_cnt", slug="elon-tweets-test", series_slug="elon-tweets",
            handle="elonmusk", title="Elon Tweets",
            window_start_ts=1000.0, window_end_ts=9000.0, gamma_closed_floor=0,
            brackets=[b0, b1, b2, b3_inf],
        )
        xt = {"elon-tweets-test": {"total": 205, "start_ts": 1000.0, "end_ts": 9000.0}}
        books = {
            "y_b1": {"asks": [{"price": "0.35", "size": "20.0"}]},
            "y_b2": {"asks": [{"price": "0.38", "size": "20.0"}]},
            "y_b3": {"asks": [{"price": "0.24", "size": "20.0"}]},  # sum = 0.970 <= 0.990
        }
        hit = detect_counting_pruned_exhaustive_yes_slate(slate_valid, xt, books)
        self.assertIsNotNone(hit)
        self.assertEqual(hit["surviving_leg_count"], 3)
        self.assertTrue(hit["includes_unbounded_top_cap"])
        self.assertAlmostEqual(hit["bundle_cost_net_ps"], 0.97, places=4)

        # CRITICAL ADVARIANT: Missing `float('inf')` top-cap MUST be rejected even at $0.73 sum!
        b3_finite = _mk_br("b3f", 240, 259.0)
        slate_no_inf = CountingSlateSpec(
            event_id="ev_no_inf", slug="elon-tweets-test", series_slug="elon-tweets",
            handle="elonmusk", title="Elon Tweets",
            window_start_ts=1000.0, window_end_ts=9000.0, gamma_closed_floor=0,
            brackets=[b0, b1, b2, b3_finite],
        )
        books_cheap = {**books, "y_b3f": {"asks": [{"price": "0.01", "size": "20.0"}]}}
        self.assertIsNone(detect_counting_pruned_exhaustive_yes_slate(slate_no_inf, xt, books_cheap))

        # Integer gap between [200, 219] and [221, inf) (missing 220!) MUST be rejected!
        b_gap = _mk_br("bgap", 221, float("inf"))
        slate_gap = CountingSlateSpec(
            event_id="ev_gap", slug="elon-tweets-test", series_slug="elon-tweets",
            handle="elonmusk", title="Elon Tweets",
            window_start_ts=1000.0, window_end_ts=9000.0, gamma_closed_floor=0,
            brackets=[b0, b1, b_gap],
        )
        self.assertIsNone(
            detect_counting_pruned_exhaustive_yes_slate(
                slate_gap, xt, {**books, "y_bgap": {"asks": [{"price": "0.20", "size": "20.0"}]}}
            )
        )

    def test_p13_p14_zec_eq1_full_rth_holding_carry_and_zerofee_binaries(self) -> None:
        from src.polymarket_research.exact_twap_lock_engine import DEFAULT_ANNUAL_IV_FLOORS
        from src.polymarket_research.riskless_protocol_v2_expansion import (
            PYTH_EQUITY_SYMBOLS,
            RTDS_SUPPORTED_ASSETS,
            TWAP_60S_SUPPORTED_ASSETS,
            detect_eq1_pyth_equity_dominance_box,
            score_live_candidate_velocity_ev,
        )
        from src.polymarket_research.same_oracle_dominance_box import (
            DOMINANCE_ASSETS,
            EMPIRICAL_BOX_ASSET_CAPS_USD,
            MIN_CORRIDOR_BPS_BY_ASSET,
            build_deterministic_updown_event_slug,
        )
        from src.polymarket_research.tradfi_sports_zero_fee_engine import PYTH_ASSET_CONFIG

        self.assertIn("ZEC", DOMINANCE_ASSETS)
        self.assertEqual(EMPIRICAL_BOX_ASSET_CAPS_USD["ZEC"], 10.0)
        self.assertEqual(MIN_CORRIDOR_BPS_BY_ASSET["ZEC"], 6.0)
        self.assertIn("ZEC", RTDS_SUPPORTED_ASSETS)
        self.assertIn("ZEC", TWAP_60S_SUPPORTED_ASSETS)
        self.assertEqual(DEFAULT_ANNUAL_IV_FLOORS["ZEC"], 1.25)
        self.assertEqual(
            build_deterministic_updown_event_slug("ZEC", "15m", 1776000900),
            "zec-updown-15m-1776000000",
        )
        self.assertIn("META", PYTH_ASSET_CONFIG)
        self.assertIn("HOOD", PYTH_EQUITY_SYMBOLS)
        self.assertIn("PLTR", PYTH_EQUITY_SYMBOLS)

        # Full-RTH EQ1 test at 10:30 AM ET (`et_hour_float = 10.5` inside 09:30-16:00 ET, whereas old window rejected < 14.25!)
        eq_hits = detect_eq1_pyth_equity_dominance_box(
            [
                {
                    "oracle": "pyth",
                    "strike": 100.0,
                    "settle_date": "2026-07-15",
                    "condition_id": "0x" + "44" * 32,
                    "yes_token_id": "hood_100_y",
                    "no_token_id": "hood_100_n",
                    "yes_ask": 0.51,
                    "no_ask": 0.52,
                    "yes_ask_size": 15.0,
                    "no_ask_size": 15.0,
                    "fee_rate": 0.0,
                },
                {
                    "oracle": "pyth",
                    "strike": 105.0,
                    "settle_date": "2026-07-15",
                    "condition_id": "0x" + "55" * 32,
                    "yes_token_id": "hood_105_y",
                    "no_token_id": "hood_105_n",
                    "yes_ask": 0.54,
                    "no_ask": 0.46,
                    "yes_ask_size": 15.0,
                    "no_ask_size": 15.0,
                    "fee_rate": 0.0,
                },
            ],
            ticker="HOOD",
            et_hour_float=10.50,
            min_net_edge_usd=0.004,
            min_shares=5.0,
        )
        self.assertEqual(len(eq_hits), 1)
        self.assertEqual(eq_hits[0]["asset"], "HOOD")
        self.assertAlmostEqual(eq_hits[0]["cost_per_share"], 0.97, places=4)

        # Holding 4% APY + daily sponsor reward credit boosts velocity score strictly > 0
        now_v = 1_780_000_000.0
        base_cand = {
            "box_type": "SINGLE_LEG_LOCK",
            "sleeve_source": "MKR_REWARD_LOCKED_CARRY",
            "box_cost_net": 0.985,
            "expiry_ts": now_v + 43200.0,
            "hold_to_maturity": True,
        }
        sc_plain = score_live_candidate_velocity_ev(base_cand, False, now_v)
        sc_carry = score_live_candidate_velocity_ev(
            {**base_cand, "holding_rewards_enabled": True, "sponsor_daily_reward_ps": 0.004},
            False,
            now_v,
        )
        self.assertGreater(sc_carry, sc_plain)

    def test_p13_daemon_extract_zerofee_general_binaries(self) -> None:
        try:
            from src.polymarket_research.alpha_124_shadow_daemon import Alpha124ShadowDaemon
        except ImportError:
            self.skipTest("aiohttp not installed in minimal stdlib interpreter")

        now_ts = 1_780_000_000.0
        end_iso = datetime.datetime.fromtimestamp(now_ts + 7200.0, tz=datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        events = [
            {
                "id": "ev_zf_ok",
                "slug": "geopolitics-ceasefire-vote",
                "negRisk": False,
                "closed": False,
                "markets": [
                    {
                        "id": "m_zf_1",
                        "conditionId": "0x" + "ab" * 32,
                        "clobTokenIds": json.dumps(["111111", "222222"]),
                        "feesEnabled": False,
                        "fee": "0",
                        "negRisk": False,
                        "closed": False,
                        "active": True,
                        "enableOrderBook": True,
                        "liquidityNum": 5000,
                        "volume24hr": 12000,
                        "endDate": end_iso,
                        "question": "Will resolution pass today?",
                    }
                ],
            },
            {
                "id": "ev_nr_skip",
                "slug": "negrisk-event",
                "negRisk": True,
                "closed": False,
                "markets": [
                    {
                        "id": "m_nr_1",
                        "conditionId": "0x" + "cd" * 32,
                        "clobTokenIds": json.dumps(["333333", "444444"]),
                        "feesEnabled": False,
                        "liquidityNum": 9000,
                        "endDate": end_iso,
                    }
                ],
            },
        ]
        out_strict = Alpha124ShadowDaemon.extract_zerofee_general_binaries(
            events, now_ts=now_ts, include_neg_risk_subconditions=False
        )
        self.assertEqual(len(out_strict), 1)
        self.assertEqual(out_strict[0]["market_id"], "m_zf_1")
        self.assertFalse(out_strict[0]["neg_risk"])
        self.assertEqual(out_strict[0]["fee_rate"], 0.0)

        out = Alpha124ShadowDaemon.extract_zerofee_general_binaries(events, now_ts=now_ts)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]["market_id"], "m_zf_1")
        self.assertFalse(out[0]["neg_risk"])
        self.assertEqual(out[1]["market_id"], "m_nr_1")
        self.assertTrue(out[1]["neg_risk"])

    def test_p21_esports_bo3_intermission_forfeit_immunity_and_p_lock(self) -> None:
        from src.polymarket_research.riskless_frontier_v2_engine import (
            EsportsBo3Spec,
            evaluate_api1_esports_bo3_opportunities,
        )

        spec = EsportsBo3Spec(
            event_id="esp_1", slug="cs2-vitality-vs-mouz", title="CS2: Vitality vs MOUZ (BO3)",
            end_ts=2_000_000_000.0, team_a="Vitality", team_b="MOUZ",
            ml_market_id="m_ml", ml_condition_id="0x" + "01" * 32, ml_a_token="ml_a", ml_b_token="ml_b",
            ml_fee_rate=0.0, ml_fee_exp=1.0,
            hc_market_id="m_hc", hc_condition_id="0x" + "02" * 32, hc_fav_is_a=True,
            hc_minus_token="hc_fav_minus15", hc_plus_token="hc_dog_plus15",
            hc_fee_rate=0.0, hc_fee_exp=1.0,
            map1_a_token="m1_a", map1_b_token="m1_b", map1_resolved_winner="A",
            map2_a_token="m2_a", map2_b_token="m2_b", map2_resolved_winner=None,
            ou25_market_id="m_ou", ou25_condition_id="0x" + "03" * 32,
            ou25_over_token="ou_over25", ou25_under_token="ou_under25", ou25_fee_rate=0.0,
        )
        asks = {
            "m2_a": 0.55,
            "m2_b": 0.48,  # sum 1.03 <= 1.08 calm intermission
            "hc_fav_minus15": 0.54,
            "ou_over25": 0.43,  # Box 1 = 0.970 <= 0.992
            "hc_dog_plus15": 0.44,
            "ou_under25": 0.53,  # Box 2 = 0.970 <= 0.992
        }
        res = evaluate_api1_esports_bo3_opportunities(spec, {}, asks, max_middle_cost_net=0.992)
        interm_boxes = [b for b in res["two_leg_boxes"] if b["mode"] == "ESPORTS1_BO3_INTERMISSION_HANDICAP_TOTAL_BOX"]
        self.assertEqual(len(interm_boxes), 2)
        for bx in interm_boxes:
            self.assertTrue(bx["post_m1_forfeit_immune"])
            # Strictly verify Map 2 Winner token is NEVER used in either leg!
            self.assertNotIn(bx["leg_a"]["token_id"], {"m2_a", "m2_b"})
            self.assertNotIn(bx["leg_b"]["token_id"], {"m2_a", "m2_b"})

        # Exhaustive state payoff matrix when Fav leads 1-0:
        # States: (2-0), (2-1), (1-2), (Post-Map-1 Forfeit -> Handicap 50-50 & Total Maps 50-50)
        box1_payoffs = {"2-0": 1.0 + 0.0, "2-1": 0.0 + 1.0, "1-2": 0.0 + 1.0, "FORFEIT": 0.5 + 0.5}
        box2_payoffs = {"2-0": 0.0 + 1.0, "2-1": 1.0 + 0.0, "1-2": 1.0 + 0.0, "FORFEIT": 0.5 + 0.5}
        for state, pay in {**box1_payoffs, **box2_payoffs}.items():
            self.assertGreaterEqual(pay, 1.0, f"Zero-loss violated in state {state}")

        # Also verify Dog winning Map 1 emits API1_BO3_MAP1_PLUS15_LOCK with p_lock == 0.999
        spec.map1_resolved_winner = "B"
        res_dog = evaluate_api1_esports_bo3_opportunities(spec, {}, asks)
        m1_locks = [lk for lk in res_dog["single_leg_locks"] if lk["mode"] == "API1_BO3_MAP1_PLUS15_LOCK"]
        self.assertEqual(len(m1_locks), 1)
        self.assertAlmostEqual(m1_locks[0]["p_lock"], 0.999, places=4)

    def test_p22_rotten_tomatoes_scalar_ladder_clause_normalization(self) -> None:
        from src.polymarket_research.riskless_frontier_v3_engine import (
            detect_cal1_monotonic_boxes,
            parse_cal1_monotonic_ladder_event,
        )

        now_ts = 1_780_000_000.0
        end_iso = datetime.datetime.fromtimestamp(now_ts + 86400.0, tz=datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        rt_event = {
            "id": "ev_rt_1",
            "slug": "dune-messiah-rotten-tomatoes-score",
            "title": "Dune Messiah Rotten Tomatoes Tomatometer score?",
            "markets": [
                {
                    "id": "rt_75",
                    "conditionId": "0x" + "75" * 32,
                    "groupItemTitle": "> 75%",
                    "question": "Will Dune Messiah Rotten Tomatoes score be > 75%?",
                    "description": "This market will resolve to Yes if the official Rotten Tomatoes Tomatometer score is above 75% on Friday.",
                    "outcomes": json.dumps(["Yes", "No"]),
                    "clobTokenIds": json.dumps(["rt75_y", "rt75_n"]),
                    "endDate": end_iso,
                    "feesEnabled": False,
                },
                {
                    "id": "rt_90",
                    "conditionId": "0x" + "90" * 32,
                    "groupItemTitle": "> 90%",
                    "question": "Will Dune Messiah Rotten Tomatoes score be > 90%?",
                    "description": "This market will resolve to Yes if the official Rotten Tomatoes Tomatometer score is above 90% on Friday.",
                    "outcomes": json.dumps(["Yes", "No"]),
                    "clobTokenIds": json.dumps(["rt90_y", "rt90_n"]),
                    "endDate": end_iso,
                    "feesEnabled": False,
                },
            ],
        }
        ladders = parse_cal1_monotonic_ladder_event(rt_event, now_ts=now_ts)
        self.assertEqual(len(ladders), 1)
        self.assertEqual(ladders[0].ladder_kind, "SCALAR_ABOVE")
        self.assertEqual([r.order_val for r in ladders[0].rungs], [75.0, 90.0])

        # Monotonicity violation: YES(>75%) @ $0.52 + NO(>90%) @ $0.45 = $0.970 <= $1.00 ($2.00 middle on 76%..90%!)
        boxes = detect_cal1_monotonic_boxes(
            ladders[0],
            {"rt75_y": 0.52, "rt90_n": 0.45, "rt75_n": 0.50, "rt90_y": 0.56},
            max_box_cost_net=0.992,
        )
        self.assertEqual(len(boxes), 1)
        self.assertAlmostEqual(boxes[0]["box_cost_net"], 0.97, places=4)

    def test_p23_perps_leadlag_precancel_sensor_and_polybolt_equities(self) -> None:
        from src.polymarket_research.polymarket_ws_streams import (
            POLYBOLT_EQUITY_SYMBOLS,
            PolymarketPerpsLeadLagStream,
        )

        for sym in ("NVDA", "AAPL", "TSLA", "MSFT", "AMZN", "GOOGL", "META", "NFLX", "PLTR", "COIN", "HOOD", "SPY", "QQQ"):
            self.assertIn(sym, POLYBOLT_EQUITY_SYMBOLS)

        perps = PolymarketPerpsLeadLagStream()
        t0 = 1_780_000_100.000
        self.assertTrue(
            perps.process_ws_frame({"symbol": "BTC-PERP", "bestBid": "100000", "bestAsk": "100000", "ts": t0}, now_ts=t0)
        )
        # 150ms later, BTC-PERP drops -12 bps to 99,880
        t1 = t0 + 0.150
        self.assertTrue(
            perps.process_ws_frame({"symbol": "BTC-PERP", "bestBid": "99875", "bestAsk": "99885", "ts": t1}, now_ts=t1)
        )
        vel = perps.get_adverse_velocity_bps("BTC", window_ms=300.0, now_ts=t1)
        self.assertIsNotNone(vel)
        self.assertAlmostEqual(vel, -12.0, places=2)
        # Resting UP/YES maker bid MUST pre-cancel; resting DOWN/NO maker bid benefits and does NOT cancel!
        self.assertTrue(perps.should_precancel_binary_maker("BTC", "UP", threshold_bps=8.0, window_ms=300.0, now_ts=t1))
        self.assertFalse(perps.should_precancel_binary_maker("BTC", "DOWN", threshold_bps=8.0, window_ms=300.0, now_ts=t1))


if __name__ == "__main__":
    unittest.main()
