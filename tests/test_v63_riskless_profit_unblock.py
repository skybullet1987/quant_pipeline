import asyncio
import collections
import json
import sys
import tempfile
import threading
import time
import types
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.polymarket_research.alpha_124_shadow_daemon import Alpha124ShadowDaemon
from src.polymarket_research.full_throttle_pipeline import HarvesterCandidateBridge, InstrumentOrderBook
from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester
from src.polymarket_research.polymarket_terminal_recorder import PolymarketDualFeed1HRecorder
from src.polymarket_research.riskless_protocol_v2_expansion import (
    _set_preempt_event_threadsafe,
    build_c1_split_sell_overround_payload,
    evaluate_clinched_ws_book_snipe_impl,
    finish_protocol_v2_special_box_sync,
    is_slow_bond1_seed_slot_reserved,
    register_clinched_ws_watch_cand_impl,
    scan_shm_c1_pairs_impl,
    select_sll_velocity_preempt_target,
)
from src.polymarket_research.stage_c_zero_loss_velocity import check_strict_pure_riskless_candidate_gate


def _make_harvester(td: Path, *, unmocked_live: bool = False) -> PolymarketLiveHarvester:
    h = PolymarketLiveHarvester.__new__(PolymarketLiveHarvester)
    h.dry_run = not unmocked_live
    h.state_file = td / "state.json"
    h.trades_log = td / "trades.jsonl"
    h.active_positions = {}
    h.closed_positions = []
    h.pending_entry_intents = {}
    h._last_known_collateral = 49.26
    h.live_bankroll = 49.26
    h._inflight_d1_keys = set()
    h._inflight_maker_anchor_keys = set()
    h._inflight_maker_anchor_types = set()
    h._seen_d1_box_keys = set()
    h._seen_d1_box_ts = {}
    h._shm_dir = str(td)
    h._fast_d1_cand_lines = collections.deque()
    h._enqueue_fast_d1_cand = lambda c: (h._fast_d1_cand_lines.append(json.dumps(c)) or True)
    h.executor = types.SimpleNamespace(
        auth_mode="LIVE" if unmocked_live else "DRY_RUN",
        client=types.SimpleNamespace() if unmocked_live else None,
        signature_type=3,
    )
    return h


class TestV63RisklessProfitUnblock(unittest.IsolatedAsyncioTestCase):
    def test_01_nested_shm_c1_and_overround_with_live_2p5x_depth_guard(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            td_p = Path(td)
            hv = _make_harvester(td_p)
            now_f = time.time()

            # 1. Nested recorder SHM schema for zero-fee XAU overround + fee-bearing BTC skipped
            (td_p / "pm_fast_tick_BTC.json").write_text(
                json.dumps(
                    {
                        "timestamp_unix": now_f,
                        "asset": "BTC",
                        "m5": {
                            "market_id": "mid_btc_5m",
                            "condition_id": "0x" + "1" * 64,
                            "expiry_ts": now_f + 240.0,
                            "neg_risk": False,
                            "fee_rate_market": 0.07,
                            "UP": {"token_id": "101" * 9, "raw_top_bids": [[0.60, 50.0]], "raw_top_asks": [[0.61, 50.0]]},
                            "DOWN": {"token_id": "102" * 9, "raw_top_bids": [[0.45, 50.0]], "raw_top_asks": [[0.46, 50.0]]},
                        },
                    }
                ),
                encoding="utf-8",
            )
            (td_p / "pm_fast_tick_XAU.json").write_text(
                json.dumps(
                    {
                        "timestamp_unix": now_f,
                        "asset": "XAU",
                        "markets": {
                            "9001001": {
                                "market_id": "9001001",
                                "condition_id": "0x" + "2" * 64,
                                "asset": "XAU",
                                "horizon": "15m",
                                "expiry_ts": now_f + 600.0,
                                "neg_risk": False,
                                "fee_rate_market": 0.0,
                                "UP": {
                                    "token_id": "201" * 9,
                                    "age_book_ms": 40.0,
                                    "raw_top_bids": [[0.52, 20.0]],
                                    "raw_top_asks": [[0.53, 20.0]],
                                },
                                "DOWN": {
                                    "token_id": "202" * 9,
                                    "age_book_ms": 40.0,
                                    "raw_top_bids": [[0.49, 20.0]],
                                    "raw_top_asks": [[0.50, 20.0]],
                                },
                            },
                            "9001002": {
                                "market_id": "9001002",
                                "condition_id": "0x" + "3" * 64,
                                "asset": "XAU",
                                "horizon": "1h",
                                "expiry_ts": now_f + 1800.0,
                                "neg_risk": False,
                                "fee_rate_market": 0.0,
                                "UP": {
                                    "token_id": "301" * 9,
                                    "age_book_ms": 40.0,
                                    "raw_top_bids": [[0.47, 25.0]],
                                    "raw_top_asks": [[0.49, 25.0]],
                                },
                                "DOWN": {
                                    "token_id": "302" * 9,
                                    "age_book_ms": 40.0,
                                    "raw_top_bids": [[0.47, 25.0]],
                                    "raw_top_asks": [[0.495, 25.0]],
                                },
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )

            emitted = scan_shm_c1_pairs_impl(hv, now_ts=now_f)
            self.assertEqual(emitted, 2)
            cands = [json.loads(x) for x in hv._fast_d1_cand_lines]
            by_bt = {c["box_type"]: c for c in cands}
            self.assertIn("CTF_OVERROUND", by_bt)
            self.assertIn("C1_BINARY_COMPLETE_SET", by_bt)

            ov = by_bt["CTF_OVERROUND"]
            self.assertEqual(ov["sleeve_source"], "C1_SPLIT_AND_SELL_OVERROUND")
            self.assertTrue(ov["rule_verified"])
            self.assertTrue(ov["atomic_split_sell_rollback_verified"])
            self.assertEqual(len(ov["legs"]), 2)
            self.assertIsNone(check_strict_pure_riskless_candidate_gate(hv, ov, {"strict_pure_riskless_mode": True}))

            # Shallow <15 share bid depth must be rejected so live 2.5x cushion stays >=5 shares
            self.assertIsNone(
                build_c1_split_sell_overround_payload(
                    market_id="9001099",
                    condition_id="0x" + "9" * 64,
                    yes_token_id="901" * 9,
                    no_token_id="902" * 9,
                    yes_bid=0.52,
                    no_bid=0.49,
                    yes_bid_sz=10.0,
                    no_bid_sz=10.0,
                    fee_rate=0.0,
                    fee_exponent=1.0,
                    neg_risk=False,
                    net_revenue_per_share=1.01,
                )
            )

            # Verify live unmocked 2.5x bid depth cushion rejects 10sh bids (10/2.5=4 < 5 min)
            hv_live = _make_harvester(td_p, unmocked_live=True)
            hv_live.executor.get_collateral_balance = lambda: 49.26
            hv_live.executor.get_market_books_batch = lambda toks: {
                "201" * 9: {"bids": [{"price": 0.52, "size": 10.0}], "asks": [{"price": 0.54, "size": 10.0}]},
                "202" * 9: {"bids": [{"price": 0.49, "size": 10.0}], "asks": [{"price": 0.51, "size": 10.0}]},
            }
            hv_live.executor.get_fee_rate = lambda cid, tok=None: (0.0, 1.0)
            out_thin = finish_protocol_v2_special_box_sync(
                hv_live,
                {**ov, "yes_token_id": "201" * 9, "no_token_id": "202" * 9},
                "OVR_THIN",
                {},
                now_f,
                {},
                own_grad=True,
            )
            self.assertFalse(out_thin["executed"])
            self.assertEqual(out_thin["reason"], "OVERROUND_MIN_SHARES")

            # Live WS C1 complete-set tag ZEROFEE1_C1_COMPLETE_SET must pass strict pure-riskless gate
            # on unmocked live harvester when condition_id & market_id match and tokens are distinct.
            cs_ws_cand = {
                **by_bt["C1_BINARY_COMPLETE_SET"],
                "sleeve_source": "ZEROFEE1_C1_COMPLETE_SET",
            }
            self.assertIsNone(
                check_strict_pure_riskless_candidate_gate(hv_live, cs_ws_cand, {"strict_pure_riskless_mode": True})
            )
            cs_ws_bad = {
                **cs_ws_cand,
                "leg_b_condition_id": "0x" + "f" * 64,
            }
            self.assertEqual(
                check_strict_pure_riskless_candidate_gate(hv_live, cs_ws_bad, {"strict_pure_riskless_mode": True}),
                "PURE_RISKLESS_C1_CONDITION_MISMATCH",
            )

    def test_02_two_leg_seed_budget_fallback_20_10_7p25(self) -> None:
        # Thin level-1 ($7.00 @ 0.97) followed by expensive level-2 ($0.52+$0.52=1.04).
        # At $20 or $10 target budgets, blended box cost exceeds max_cap=0.985; at $7.25 fallback it fills cleanly!
        bk_a = {"asks": [{"price": 0.485, "size": 7.5}, {"price": 0.52, "size": 50.0}]}
        bk_b = {"asks": [{"price": 0.485, "size": 7.5}, {"price": 0.52, "size": 50.0}]}
        leg = {"fee_rate": 0.0, "fee_exponent": 1.0}
        w_seed = Alpha124ShadowDaemon._walk_2l_live_clip(bk_a, bk_b, leg, leg, 0.985)
        self.assertTrue(w_seed["filled"])
        self.assertEqual(w_seed["shares"], 7)
        self.assertAlmostEqual(float(w_seed["box_cost_net"]), 0.97, places=4)

        dm = Alpha124ShadowDaemon.__new__(Alpha124ShadowDaemon)
        w_d1 = dm._walk_d1_live_clip_with_fallback(
            bk_a, bk_b, leg, leg, primary_budget_usd=20.0, max_box_cost_net=0.985, is_4h_mixed=False
        )
        self.assertTrue(w_d1["filled"])
        self.assertEqual(w_d1["shares"], 7)

    async def test_03_ws_clinch_snipe_preempts_resting_maker_and_threadsafe_event(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            td_p = Path(td)
            hv = _make_harvester(td_p)
            now_f = time.time()
            tok_w = "401" * 9
            tok_o = "402" * 9
            reg = register_clinched_ws_watch_cand_impl(
                hv,
                {
                    "box_type": "CLINCH_WATCHLIST_REG",
                    "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
                    "asset": "SPORTS",
                    "event_id": "evt_ws_1",
                    "dedupe_key": "WS_1",
                    "expiry_ts": now_f + 1800.0,
                    "p_model": 1.0,
                    "leg_a_market_id": "mkt_ws_1",
                    "leg_a_condition_id": "0x" + "4" * 64,
                    "leg_a_token_id": tok_w,
                    "leg_a_opp_token_id": tok_o,
                    "leg_a_fee_rate": 0.0,
                    "max_lock_eff_px": 0.992,
                },
                now_ts=now_f,
            )
            self.assertTrue(reg)

            # Resting unfilled maker on mkt_ws_1 should NOT block clinched WS snipe!
            hv.pending_entry_intents["IK_MKR_1"] = {
                "inflight_key": "IK_MKR_1",
                "live_maker_anchor_inflight": True,
                "market_id": "mkt_ws_1",
                "event_id": "evt_ws_1",
                "notional_usd": 45.0,
            }
            snipe = evaluate_clinched_ws_book_snipe_impl(
                hv,
                tok_w,
                bk_win={"asks": [{"price": 0.985, "size": 25.0}], "bids": [{"price": 0.980, "size": 25.0}]},
                now_ts=now_f + 1.0,
            )
            self.assertIsNotNone(snipe)
            assert snipe is not None
            self.assertEqual(snipe.get("_preempt_resting_maker_intent_ids"), ["IK_MKR_1"])
            self.assertEqual(hv._ws_clinch_snipe_preempt_emitted_count, 1)

            # Actual open position on mkt_ws_1 MUST still block
            hv.active_positions["POS_1"] = {
                "market_id": "mkt_ws_1",
                "token_id": tok_w,
                "hold_to_maturity_lock": False,
                "inventory_reconciled": True,
                "notional_usd": 7.0,
            }
            self.assertIsNone(
                evaluate_clinched_ws_book_snipe_impl(
                    hv,
                    tok_w,
                    bk_win={"asks": [{"price": 0.985, "size": 25.0}], "bids": [{"price": 0.980, "size": 25.0}]},
                    now_ts=now_f + 10.0,
                )
            )

            # Cross-thread asyncio.Event wake via _set_preempt_event_threadsafe
            loop = asyncio.get_running_loop()
            hv._main_loop = loop
            ev = asyncio.Event()
            t = threading.Thread(target=lambda: _set_preempt_event_threadsafe(hv, ev))
            t.start()
            t.join(timeout=2.0)
            await asyncio.wait_for(ev.wait(), timeout=1.0)
            self.assertTrue(ev.is_set())

    def test_04_slow_bond1_seed_slot_reserve_and_live_35s_velocity_preempt(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            td_p = Path(td)
            hv_live = _make_harvester(td_p, unmocked_live=True)
            now_f = time.time()
            for idx in (1, 2):
                ik = f"IK_SLOW_{idx}"
                hv_live.pending_entry_intents[ik] = {
                    "inflight_key": ik,
                    "live_maker_anchor_inflight": True,
                    "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
                    "anchor_bid_px": 0.996,
                    "expiry_ts": now_f + 5400.0,
                    "notional_usd": 7.30,
                    "fifo_rank1_verified": False,
                    "ts": now_f - 40.0,
                }
            hv_live._maker_anchor_preempt_events = {"IK_SLOW_1": threading.Event(), "IK_SLOW_2": threading.Event()}
            hv_live._claimed_velocity_preempts = set()

            slow_bond_cand = {"sleeve_source": "BOND1_UMA_RESOLUTION_CARRY", "anchor_bid_px": 0.996, "expiry_ts": now_f + 5400.0}
            fast_bond_cand = {"sleeve_source": "BOND1_UMA_RESOLUTION_CARRY", "anchor_bid_px": 0.985, "expiry_ts": now_f + 3600.0}
            mlk1_cand = {"sleeve_source": "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER", "anchor_bid_px": 0.985, "expiry_ts": now_f + 1200.0}
            self.assertTrue(is_slow_bond1_seed_slot_reserved(hv_live, "BOND1_UMA_RESOLUTION_CARRY", slow_bond_cand))
            self.assertFalse(is_slow_bond1_seed_slot_reserved(hv_live, "BOND1_UMA_RESOLUTION_CARRY", fast_bond_cand))
            self.assertFalse(is_slow_bond1_seed_slot_reserved(hv_live, "MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER", mlk1_cand))

            # Even with vel_mult=3.0, live unmocked 40s-old <=75bps/hr BOND1 is evicted by 110bps/hr (>=1.8x, +60bps/hr)
            sv, sk = select_sll_velocity_preempt_target(
                hv_live, 110.0, is_s2_mkr=False, vel_mult=3.0, now_pe=now_f, cand_sleeve="MKR_LOCK1_POST_CLINCH_REBATE_SWEEPER"
            )
            self.assertIn(sk, {"IK_SLOW_1", "IK_SLOW_2"})
            self.assertGreater(sv, 0.0)

    def test_05_full_throttle_seed_bond1_ghost_yield_and_occupied_event_filters(self) -> None:
        now_v = 1_795_000_000.0
        with tempfile.TemporaryDirectory() as tmp:
            tp = Path(tmp)
            st_p = tp / "live_harvester_state.json"
            st_p.write_text(
                json.dumps(
                    {
                        "active_positions": {
                            "p_occ": {"market_id": "m_occ_1", "event_id": "ev_occupied", "status": "OPEN"}
                        },
                        "pending_entry_intents": {},
                    }
                ),
                encoding="utf-8",
            )
            end_iso = (datetime.fromtimestamp(now_v + 7200.0, tz=timezone.utc)).isoformat()

            def _mk_mkt(mid: str, yt: str, nt: str, vol: float) -> dict:
                return {
                    "id": mid,
                    "question": f"Will asset {mid} exceed $180 on pyth.network at expiry?",
                    "description": "Resolves via pyth.network official price feed at expiry.",
                    "conditionId": f"0x{mid}",
                    "questionID": "0x" + f"{int(mid):064x}",
                    "resolvedBy": "0x65070be91477460d8a7aeeb94ef92fe056c2f2a7",
                    "outcomes": '["Yes", "No"]',
                    "clobTokenIds": json.dumps([yt, nt]),
                    "active": True,
                    "closed": False,
                    "archived": False,
                    "acceptingOrders": True,
                    "enableOrderBook": True,
                    "feesEnabled": False,
                    "umaResolutionStatus": "proposed",
                    "customLiveness": 7200,
                    "endDate": end_iso,
                    "orderPriceMinTickSize": 0.001,
                    "volume24hr": vol,
                }

            events = [
                {"id": "ev_occupied", "slug": "occ", "title": "Occupied Event", "markets": [_mk_mkt("7300001", "ty1", "tn1", 1000.0)]},
                {"id": "ev_ghost", "slug": "ghost", "title": "Ghost Event", "markets": [_mk_mkt("7300002", "ty2", "tn2", 5.0)]},
                {"id": "ev_penny", "slug": "penny", "title": "Penny Event", "markets": [_mk_mkt("7300003", "ty3", "tn3", 500.0)]},
                {"id": "ev_good", "slug": "good", "title": "Good Event", "markets": [_mk_mkt("7300004", "ty4", "tn4", 500.0)]},
            ]
            raw_books = {
                "ty1": {"market": "7300001", "bids": [{"price": "0.991", "size": "100"}], "asks": [{"price": "0.996", "size": "50"}], "tick_size": "0.001"},
                "tn1": {"market": "7300001", "bids": [{"price": "0.004", "size": "100"}], "asks": [{"price": "0.009", "size": "50"}], "tick_size": "0.001"},
                "ty2": {"market": "7300002", "bids": [{"price": "0.991", "size": "100"}], "asks": [], "tick_size": "0.001"},
                "tn2": {"market": "7300002", "bids": [{"price": "0.004", "size": "100"}], "asks": [{"price": "0.009", "size": "50"}], "tick_size": "0.001"},
                "ty3": {"market": "7300003", "bids": [{"price": "0.996", "size": "100"}], "asks": [{"price": "0.999", "size": "50"}], "tick_size": "0.001"},
                "tn3": {"market": "7300003", "bids": [{"price": "0.001", "size": "100"}], "asks": [{"price": "0.004", "size": "50"}], "tick_size": "0.001"},
                "ty4": {"market": "7300004", "bids": [{"price": "0.991", "size": "100"}], "asks": [{"price": "0.996", "size": "50"}], "tick_size": "0.001"},
                "tn4": {"market": "7300004", "bids": [{"price": "0.004", "size": "100"}], "asks": [{"price": "0.009", "size": "50"}], "tick_size": "0.001"},
            }
            books = {
                tid: InstrumentOrderBook.from_raw(tid, b, market_id=b["market"], tick_size=0.001, book_timestamp_sec=now_v)
                for tid, b in raw_books.items()
            }
            cand_jsonl = tp / "d1.jsonl"
            bridge = HarvesterCandidateBridge(
                candidates_jsonl_path=cand_jsonl,
                dedupe_state_path=tp / "dedupe.json",
                live_harvester_state_path=st_p,
                min_velocity_bps_per_hr=7.5,
            )
            res = bridge.emit_verified_candidates(
                [],
                books,
                events=events,
                jit_book_fetcher=lambda tids: ({k: raw_books[k] for k in tids}, {"fetch_timestamp_sec": now_v + 0.05}),
                enable_passive_maker_bridge=True,
                max_maker_locks_per_cycle=5,
                fallback_reconciled_nav_usd=49.26,
                now_ts=now_v,
            )
            self.assertEqual(res["maker_locks_emitted_this_cycle"], 1)
            self.assertEqual(res["skipped_by_reason"].get("BOND1_GHOST_LOW_VOL_NO_ASKS"), 1)
            self.assertGreaterEqual(res["skipped_by_reason"].get("MAKER_EVENT_CONCENTRATION_CAP_D007", 0), 1)
            emitted = [json.loads(x) for x in cand_jsonl.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([c["leg_a_market_id"] for c in emitted], ["7300004"])

    async def test_06_recorder_snapshot_fee_and_binance_idle_ping_and_cross_venue_gc(self) -> None:
        import src.polymarket_research.cross_venue_riskless_shadow as cv_mod
        import src.polymarket_research.polymarket_terminal_recorder as rec_mod

        self.assertTrue(hasattr(cv_mod, "gc"))
        tr = PolymarketDualFeed1HRecorder.__new__(PolymarketDualFeed1HRecorder)
        tr.asset = "XAU"
        tr.fee_enabled = False
        tr.fee_rate_market = 0.0
        tr.spot_price = 2600.0
        tr.futures_price = 2600.0
        tr.spot_price_ts = time.time()
        tr.futures_price_ts = time.time()
        tr.last_clob_ws_msg_ts = time.time()
        tr.clob_ws_connected = True
        tr.basis_bps = 0.0
        tr.finalized_1h_open = 2595.0
        tr.chainlink_stream = None
        tr.get_chainlink_proxy_spot = lambda now=None: 2600.0
        tr._get_live_cl_spot = lambda now=None: None
        tr.get_coinbase_spot = lambda now=None: 1.0
        tr.get_chainlink_twap_60s = lambda now=None: 2600.0
        tr.is_chainlink_basis_anchored = lambda now=None: True
        tr.get_venue_divergence_bps = lambda now=None: 0.0
        tr.get_venue_divergence_centered_bps = lambda now=None: 0.0
        tr.get_coinbase_move_bps = lambda w, now=None: 0.0
        tr.get_settlement_twap_slice = lambda exp, now=None: (0.0, 0.0)
        end_dt = datetime.now(timezone.utc) + timedelta(minutes=30)
        tr.current_market = {
            "market_id": "999",
            "condition_id": "0x" + "a" * 64,
            "neg_risk": False,
            "tokens": {"UP": "tok_u", "DOWN": "tok_d"},
            "end_dt": end_dt,
        }
        dummy_bk = types.SimpleNamespace(
            top_of_book=lambda now: {"best_bid": 0.51, "best_ask": 0.53, "raw_top_bids": [[0.51, 20.0]], "raw_top_asks": [[0.53, 20.0]], "age_book_ms": 10.0}
        )
        tr.books = {"UP": dummy_bk, "DOWN": dummy_bk}
        snap = tr.build_fast_tick_snapshot(time.time())
        mkt_snap = snap["markets"]["999"]
        self.assertEqual(mkt_snap["fee_rate_market"], 0.0)
        self.assertFalse(mkt_snap["neg_risk"])
        self.assertEqual(mkt_snap["condition_id"], "0x" + "a" * 64)
        self.assertGreater(mkt_snap["expiry_ts"], 0.0)

        # Binance futures WS timeout keepalive pings twice without reconnecting on quiet feed
        tr.running = True
        tr.binance_futures_ws = "wss://example.invalid/ws"
        tr.binance_symbol = "xauusdt"
        tr.shock_threshold_usd = 1000.0
        tr.riskless_bus_only = True
        tr.futures_only_ref = True
        tr.coinbase_product = "USDT-USD"
        tr.coinbase_spot = 1.0
        tr.coinbase_spot_ts = time.time()
        tr.coinbase_history = collections.deque(maxlen=64)
        tr._update_rolling_sigma = lambda px: None
        tr.update_basis = lambda: None
        tr._maybe_write_fast_tick = lambda: (setattr(tr, "running", False) or False)

        pings = []
        connect_cnt = [0]

        class _FakeWs:
            def __init__(self):
                self._n = 0

            async def recv(self):
                self._n += 1
                if self._n <= 2:
                    await asyncio.sleep(0.02)
                    raise asyncio.TimeoutError()
                return json.dumps({"p": "2601.0", "q": "1.0", "m": False, "E": 1, "T": 1})

            async def ping(self):
                pings.append(1)

        class _FakeConn:
            async def __aenter__(self):
                connect_cnt[0] += 1
                return _FakeWs()

            async def __aexit__(self, *args):
                return False

        async def _fake_drain(ws, s, max_batch=64):
            return [s]

        with mock.patch.object(rec_mod, "websockets", types.SimpleNamespace(connect=lambda *a, **kw: _FakeConn())), mock.patch.object(
            rec_mod, "_enable_ws_nodelay", lambda ws: None
        ), mock.patch.object(rec_mod, "_drain_ws_frames", new=_fake_drain):
            await tr.stream_binance_futures()

        self.assertEqual(connect_cnt[0], 1)
        self.assertEqual(len(pings), 2)
        self.assertEqual(tr.futures_price, 2601.0)


if __name__ == "__main__":
    unittest.main()
