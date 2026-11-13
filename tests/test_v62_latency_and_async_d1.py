import asyncio
import collections
import datetime
import json
import sys
import tempfile
import threading
import time
import types
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import src.polymarket_research.polymarket_live_executor as exec_mod
import src.polymarket_research.polymarket_live_harvester as harv_mod
from src.polymarket_research.polymarket_live_executor import (
    FastV2OrderSigner,
    PolymarketLiveExecutor,
)
from src.polymarket_research.polymarket_live_harvester import PolymarketLiveHarvester
from src.polymarket_research.riskless_fast_feeds import FROZEN_KMIA_MARKET_IDS


def _sample_d1_cand(
    box_id="BOX_T1",
    m_a="1001",
    m_b=None,
    tok_a="1" * 24,
    tok_b="2" * 24,
    ts=None,
):
    now = time.time() if ts is None else ts
    m_b_eff = m_a if m_b is None else m_b
    return {
        "box_id": box_id,
        "box_type": "COMPLETE_SET",
        "sleeve_source": "C1_BINARY_COMPLETE_SET",
        "asset": "BTC",
        "dedupe_key": f"dk_{box_id}",
        "ts_unix": now,
        "expiry_ts": now + 300.0,
        "leg_a_market_id": m_a,
        "leg_b_market_id": m_b_eff,
        "leg_a_token_id": tok_a,
        "leg_b_token_id": tok_b,
        "leg_a_opp_token_id": tok_b,
        "leg_b_opp_token_id": tok_a,
        "leg_a_condition_id": f"cid_{m_a}",
        "leg_b_condition_id": f"cid_{m_b_eff}",
        "leg_a_side": "YES",
        "leg_b_side": "NO",
        "leg_a_price": 0.45,
        "leg_b_price": 0.50,
        "leg_a_limit_price": 0.45,
        "leg_b_limit_price": 0.50,
        "leg_a_avail": 20.0,
        "leg_b_avail": 20.0,
        "box_cost": 0.95,
        "shares": 10.0,
        "neg_risk": False,
        "fee_rate": 0.0,
        "fee_rate_a": 0.0,
        "fee_rate_b": 0.0,
        "fee_exponent_a": 1.0,
        "fee_exponent_b": 1.0,
        "expiry_unix": now + 300.0,
        "oracle_match_verified": True,
        "title": "BTC 15m test",
    }


def _make_mock_live_executor() -> PolymarketLiveExecutor:
    ex = PolymarketLiveExecutor(dry_run=True)
    ex.dry_run = False
    ex.auth_mode = "AUTHENTICATED_L2"
    ex.is_authenticated = True
    ex.client = mock.MagicMock()
    ex.client.host = "https://clob.polymarket.com"
    ex.client._mock_children = None
    return ex


def _make_dry_harvester(tmp_dir: Path, **kwargs) -> PolymarketLiveHarvester:
    state_fp = tmp_dir / "state.json"
    with mock.patch.object(harv_mod, "DATA_DIR", tmp_dir), \
         mock.patch.object(harv_mod, "STATE_FILE", state_fp):
        hv = PolymarketLiveHarvester(dry_run=True, **kwargs)
    return hv


class TestV62ExecutorLatencyAndAsync(unittest.IsolatedAsyncioTestCase):
    def test_fast_signer_buffered_salt_and_amt_cache_parity(self):
        signer = FastV2OrderSigner.__new__(FastV2OrderSigner)
        signer._salt_lock = threading.Lock()
        signer._salt_pool = []
        signer._amt_cache = {}
        signer._amt_cache_lock = threading.Lock()
        signer._rounding_config = {"0.01": types.SimpleNamespace(price=2, size=2, amount=4)}
        signer._tick_sizes_dict = {"12345": "0.01"}
        signer._neg_risk_dict = {"12345": False}
        signer._Side = types.SimpleNamespace(BUY=0, SELL=1)
        signer._round_normal = lambda x, dec: round(float(x), dec)
        signer._default_builder_hex = "0x" + "00" * 32
        signer._bytes32_zero_hex = "0x" + "00" * 32
        signer._orig_create_order = mock.MagicMock()
        signer._order_builder = mock.MagicMock()
        signer._order_builder.get_order_amounts.return_value = (0, 4800000, 10000000)

        salts = [signer._next_buffered_salt() for _ in range(300)]
        self.assertTrue(all(1 <= s < (1 << 53) for s in salts))
        self.assertEqual(len(set(salts)), 300)

        signer.sign_v2_order_data = lambda **kw: {"order": kw}
        order_args = types.SimpleNamespace(token_id="12345", price=0.48, size=10.0, side="BUY")
        opts = types.SimpleNamespace(tick_size="0.01", neg_risk=False)

        o1 = signer.create_order(order_args, opts)
        o2 = signer.create_order(order_args, opts)

        self.assertEqual(signer._order_builder.get_order_amounts.call_count, 1)
        self.assertEqual(len(signer._amt_cache), 1)
        self.assertEqual(o1["order"]["maker_amount"], o2["order"]["maker_amount"])
        self.assertEqual(o1["order"]["taker_amount"], o2["order"]["taker_amount"])
        self.assertNotEqual(o1["order"]["salt"], o2["order"]["salt"])

    async def test_get_async_client_http11_keepalive(self):
        ex = PolymarketLiveExecutor(dry_run=True)
        seen_transport = {}
        seen_client = {}

        class _FakeAsyncClient:
            def __init__(self, **kw):
                seen_client.update(kw)
                self.is_closed = False
                self._transport = types.SimpleNamespace(
                    _pool=types.SimpleNamespace(_http2=kw.get("http2", False), _keepalive_expiry=45.0)
                )

            async def aclose(self):
                self.is_closed = True

        fake_httpx = types.SimpleNamespace(
            Limits=lambda **kw: kw,
            AsyncHTTPTransport=lambda **kw: (seen_transport.update(kw) or kw),
            AsyncClient=_FakeAsyncClient,
        )
        with mock.patch.object(exec_mod, "httpx", fake_httpx):
            cli = ex.get_async_client()
            try:
                self.assertIs(cli, ex.get_async_client())
                self.assertFalse(seen_transport["http2"])
                self.assertEqual(seen_transport["limits"]["keepalive_expiry"], 45.0)
                self.assertFalse(seen_client["http2"])
            finally:
                await cli.aclose()

    async def test_get_market_books_batch_async_orjson(self):
        ex = _make_mock_live_executor()
        payload = [
            {"asset_id": "tok1", "bids": [{"price": "0.49", "size": "10"}], "asks": [{"price": "0.51", "size": "15"}]},
            {"asset_id": "tok2", "bids": [{"price": "0.45", "size": "20"}], "asks": [{"price": "0.47", "size": "25"}]},
        ]
        mock_resp = mock.MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = json.dumps(payload).encode("utf-8")
        mock_resp.json.return_value = payload
        mock_cli = mock.AsyncMock()
        mock_cli.post.return_value = mock_resp

        fake_oj = types.SimpleNamespace(loads=json.loads, dumps=lambda obj: json.dumps(obj).encode("utf-8"))
        with mock.patch.object(ex, "get_async_client", return_value=mock_cli), \
             mock.patch.object(exec_mod, "_orjson", fake_oj):
            res = await ex.get_market_books_batch_async(["tok1", "tok2", "tok1"])

        mock_cli.post.assert_awaited_once()
        self.assertEqual(set(res.keys()), {"tok1", "tok2"})
        self.assertEqual(res["tok1"]["asks"][0]["price"], "0.51")

    async def test_get_token_metadata_async_parallel_and_boundary_recheck(self):
        ex = _make_mock_live_executor()

        async def _fake_get(url, timeout=None):
            r = mock.MagicMock()
            r.status_code = 200
            if "tick-size" in url:
                r.content = b'{"minimum_tick_size": 0.001}'
                r.json.return_value = {"minimum_tick_size": 0.001}
            else:
                r.content = b'{"neg_risk": true}'
                r.json.return_value = {"neg_risk": True}
            return r

        mock_cli = mock.MagicMock()
        mock_cli.get = mock.AsyncMock(side_effect=_fake_get)
        ex._tick_size_cache["tok_bnd"] = 0.01
        ex._boundary_tick_recheck_ts = {"tok_bnd": time.monotonic() - 3.0}

        with mock.patch.object(ex, "get_async_client", return_value=mock_cli):
            tk, nr = await ex.get_token_metadata_async("tok_bnd", price_hint=0.97)
        self.assertAlmostEqual(tk, 0.001, places=6)
        self.assertTrue(nr)
        self.assertEqual(mock_cli.get.await_count, 2)

        ex._tick_size_cache["tok_bnd"] = 0.01
        mock_cli.get.reset_mock()
        with mock.patch.object(ex, "get_async_client", return_value=mock_cli):
            tk2, nr2 = await ex.get_token_metadata_async("tok_bnd", price_hint=0.97)
        self.assertAlmostEqual(tk2, 0.01, places=6)
        self.assertTrue(nr2)
        self.assertEqual(mock_cli.get.await_count, 0)

    async def test_resolve_deferred_fok_gross_uses_user_ws_first(self):
        ex = _make_mock_live_executor()
        uws = mock.MagicMock()
        uws.is_healthy.return_value = True
        uws.wait_for_order_terminal.return_value = {"status": "MATCHED", "size_matched": "12.5"}
        uws.get_order_snapshot.return_value = {"status": "MATCHED", "size_matched": "12.5"}
        ex._user_ws_cache = uws
        ex.get_order_fill_summary = mock.MagicMock(side_effect=AssertionError("Should not poll REST when WS has terminal fill"))

        g_sync = ex._resolve_deferred_fok_gross("ord_1", "tok_1", {"status": "DELAYED"})
        g_async = await ex._resolve_deferred_fok_gross_async("ord_1", "tok_1", {"status": "DELAYED"})
        self.assertAlmostEqual(g_sync, 12.5)
        self.assertAlmostEqual(g_async, 12.5)
        ex.get_order_fill_summary.assert_not_called()

    async def test_execute_atomic_dominance_box_async_native_batch_and_fallback(self):
        ex = _make_mock_live_executor()
        ex.client.creds = object()
        ex._async_http_client = object()
        ex._can_use_native_async_post_order = mock.MagicMock(return_value=True)
        ex._tick_size_cache.update({"t1": 0.01, "t2": 0.01})
        ex._neg_risk_cache.update({"t1": False, "t2": False})
        ex._encode_fast_l2_request = mock.MagicMock(return_value=({"H": "1"}, b"{}"))
        ex._serialize_signed_order_payload = mock.MagicMock(return_value={"order": {}})
        ex._sign_atomic_dominance_box_legs = mock.MagicMock(return_value=("s1", "s2"))
        ex._exec_hot_async_post = mock.AsyncMock(
            return_value=(
                [
                    {"success": True, "orderID": "o1", "status": "MATCHED", "takingAmount": "10", "makingAmount": "4.5"},
                    {"success": True, "orderID": "o2", "status": "MATCHED", "takingAmount": "10", "makingAmount": "5.0"},
                ],
                None,
                1.0,
            )
        )
        with mock.patch.object(exec_mod, "OrderArgsV2", object()), \
             mock.patch.object(exec_mod, "OrderType", types.SimpleNamespace(FOK="FOK")), \
             mock.patch.object(ex, "_can_batch_post_dominance_box", return_value=True):
            res_batch = await ex.execute_atomic_dominance_box_async(
                "bx1", "t1", "YES", 0.45, "t2", "NO", 0.50, 10.0,
                max_box_cost_net=0.99, fee_rate=0.0, fee_rate_a=0.0, fee_rate_b=0.0,
                parallel_dispatch=True, leg_a_pre_balance=0.0, leg_b_pre_balance=0.0,
            )
        self.assertTrue(res_batch.get("success"), f"Batch async failed: {res_batch}")
        self.assertEqual(ex._exec_hot_async_post.await_count, 1)
        self.assertEqual(ex._exec_hot_async_post.await_args.args[0], "/orders")

        ex._exec_hot_async_post.reset_mock()
        ex._exec_hot_async_post.side_effect = [
            ({"success": True, "orderID": "o1", "status": "MATCHED", "takingAmount": "10", "makingAmount": "4.5"}, None, 1.0),
            ({"success": True, "orderID": "o2", "status": "MATCHED", "takingAmount": "10", "makingAmount": "5.0"}, None, 1.0),
        ]
        with mock.patch.object(exec_mod, "OrderArgsV2", object()), \
             mock.patch.object(exec_mod, "OrderType", types.SimpleNamespace(FOK="FOK")), \
             mock.patch.object(ex, "_can_batch_post_dominance_box", return_value=False):
            res_par = await ex.execute_atomic_dominance_box_async(
                "bx2", "t1", "YES", 0.45, "t2", "NO", 0.50, 10.0,
                max_box_cost_net=0.99, fee_rate=0.0, fee_rate_a=0.0, fee_rate_b=0.0,
                parallel_dispatch=True, leg_a_pre_balance=0.0, leg_b_pre_balance=0.0,
            )
        self.assertTrue(res_par.get("success"))
        self.assertEqual(ex._exec_hot_async_post.await_count, 2)
        self.assertTrue(all(c.args[0] == "/order" for c in ex._exec_hot_async_post.await_args_list))


def _fake_grad_maps(*_a, **_kw):
    rec = {"closed": 12, "win_rate_pct": 100.0, "realized_pnl_t1000_usd": 5.0, "legging_adjusted_pnl_t1000_usd": 5.0}
    return (
        {
            "C1_BINARY_COMPLETE_SET": rec,
            "D1_SAME_ORACLE_DOMINANCE_BOX": rec,
            "BOND1_UMA_RESOLUTION_CARRY": rec,
        },
        {"BTC": rec},
        None,
    )


class TestV62HarvesterAsyncD1AndLifecycle(unittest.IsolatedAsyncioTestCase):
    async def test_maybe_execute_graduated_d1_box_async_ws_book_and_event_preempt(self):
        with tempfile.TemporaryDirectory() as td:
            hv = _make_dry_harvester(Path(td))
            hv.dry_run = False
            hv.executor.dry_run = False
            hv.executor.auth_mode = "AUTHENTICATED_L2"
            hv.executor.is_authenticated = True
            hv.executor.client = mock.MagicMock()
            hv.executor.client._mock_children = None
            hv._startup_reconciled = True
            hv._is_d1_box_halted = lambda: False
            hv._global_halt_reasons = lambda: []
            hv._last_known_collateral = 100.0
            hv.executor.get_collateral_balance = mock.MagicMock(return_value=100.0)
            hv.executor.get_token_balance = mock.MagicMock(return_value=0.0)
            hv.executor.execute_atomic_dominance_box_async = mock.AsyncMock(
                return_value={
                    "success": True,
                    "shares_filled": 16,
                    "box_cost_per_share": 0.90,
                    "total_cost_usd": 14.40,
                    "locked_profit_usd": 1.60,
                    "edge_pct": 0.10,
                    "dispatch_mode": "BATCH_POST_ORDERS_FOK",
                    "leg_1": {"orderID": "oa", "token_id": "1" * 24, "label": "YES", "matched_shares": 16.0, "gross_shares": 16.0, "price": 0.42},
                    "leg_2": {"orderID": "ob", "token_id": "2" * 24, "label": "NO", "matched_shares": 16.0, "gross_shares": 16.0, "price": 0.48},
                }
            )
            ws_tracker = mock.MagicMock()
            ws_tracker.get_book.side_effect = lambda tok, max_age_sec=0.65: {
                "asks": [{"price": "0.42" if tok == ("1" * 24) else "0.48", "size": "25"}],
                "bids": [{"price": "0.41" if tok == ("1" * 24) else "0.47", "size": "25"}],
            }
            hv._pos_market_ws = ws_tracker
            hv.save_state = mock.MagicMock()

            ev = asyncio.Event()
            hv._maker_anchor_preempt_ev = ev
            hv.pending_entry_intents["mkr_1"] = {"market_id": "1001", "live_maker_anchor_inflight": True}

            async def _release_soon():
                await asyncio.sleep(0.02)
                hv.pending_entry_intents.pop("mkr_1", None)
                ev.set()

            cand = _sample_d1_cand()
            with mock.patch.object(hv, "_preempt_resting_maker_anchors", return_value=1), \
                 mock.patch.object(type(hv.executor), "get_market_book", side_effect=AssertionError("REST book should not run on WS hit")) as rest_spy, \
                 mock.patch("src.polymarket_research.stage_c_zero_loss_velocity.load_alpha124_graduation_maps_with_lkg_cache", side_effect=_fake_grad_maps), \
                 mock.patch.object(harv_mod.time, "sleep", side_effect=AssertionError("async path must not call time.sleep")):
                t_rel = asyncio.create_task(_release_soon())
                out = await hv.maybe_execute_graduated_d1_box_async(cand)
                await t_rel

            self.assertTrue(out.get("executed"), f"Unexpected D1 async output: {out}")
            rest_spy.assert_not_called()
            hv.executor.execute_atomic_dominance_box_async.assert_awaited_once()
            self.assertEqual(getattr(hv, "_d1_async_reserved_usd", 0.0), 0.0)

    async def test_sync_maybe_execute_graduated_d1_box_backward_compat(self):
        with tempfile.TemporaryDirectory() as td:
            hv = _make_dry_harvester(Path(td))
            hv.save_state = mock.MagicMock()
            with mock.patch("src.polymarket_research.stage_c_zero_loss_velocity.load_alpha124_graduation_maps_with_lkg_cache", side_effect=_fake_grad_maps):
                out = hv.maybe_execute_graduated_d1_box(_sample_d1_cand(box_id="BOX_SYNC"))
            self.assertTrue(out.get("executed"), f"Unexpected D1 sync output: {out}")

    async def test_poll_d1_live_box_candidates_concurrent_disjoint_and_reserved_budget(self):
        with tempfile.TemporaryDirectory() as td:
            td_p = Path(td)
            hv = _make_dry_harvester(td_p)
            cand_fp = td_p / "d1_live_box_candidates.jsonl"
            cand_fp.write_text("", encoding="utf-8")
            hv._d1_cand_initialized = True
            hv._last_d1_cand_offset = 0
            c1 = _sample_d1_cand(box_id="BX_C1", m_a="2001", m_b="2002", tok_a="ta1", tok_b="tb1")
            c2 = _sample_d1_cand(box_id="BX_C2", m_a="3001", m_b="3002", tok_a="ta2", tok_b="tb2")
            hv._fast_d1_cand_lines = collections.deque([json.dumps(c1), json.dumps(c2)])

            active_now = 0
            max_concurrent = 0
            seen_ids = []

            async def _fake_async_d1(cand, concurrent_ok=False):
                nonlocal active_now, max_concurrent
                self.assertTrue(concurrent_ok)
                active_now += 1
                max_concurrent = max(max_concurrent, active_now)
                seen_ids.append(cand["box_id"])
                await asyncio.sleep(0.03)
                active_now -= 1
                return {"executed": True}

            hv.maybe_execute_graduated_d1_box_async = _fake_async_d1
            loop = asyncio.get_running_loop()
            with mock.patch.object(harv_mod, "DATA_DIR", td_p):
                cnt = await hv._poll_d1_live_box_candidates_unlocked(time.time(), loop)
            self.assertEqual(cnt, 2)
            self.assertEqual(set(seen_ids), {"BX_C1", "BX_C2"})
            self.assertGreaterEqual(max_concurrent, 2)

            hv.dry_run = False
            hv.executor.dry_run = False
            hv.executor.auth_mode = "AUTHENTICATED_L2"
            hv.executor.is_authenticated = True
            hv.executor.client = mock.MagicMock()
            hv.executor.client._mock_children = None
            hv._startup_reconciled = True
            hv._is_d1_box_halted = lambda: False
            hv._global_halt_reasons = lambda: []
            hv._last_known_collateral = 12.0
            with mock.patch("src.polymarket_research.stage_c_zero_loss_velocity.load_alpha124_graduation_maps_with_lkg_cache", side_effect=_fake_grad_maps):
                s1 = hv._d1_step1_gate_and_preempt(_sample_d1_cand(box_id="B_RES1", m_a="4001"), concurrent_ok=True)
            s2 = hv._d1_step2_budget_and_bal_prep(s1, 12.0, 12.0, async_reserved_usd=10.5)
            self.assertFalse(s2.get("_s2_ok"), f"Expected budget veto with async_reserved_usd=10.5, got: {s2}")
            self.assertIn(s2.get("reason"), {"INSUFFICIENT_FREE_BANKROLL", "INSUFFICIENT_BOX_COLLATERAL_HEADROOM"})

    async def test_prewarm_next_candle_markets_concurrent_async(self):
        with tempfile.TemporaryDirectory() as td:
            hv = _make_dry_harvester(Path(td))
            mock_resp = mock.MagicMock()
            mock_resp.status_code = 200
            future_iso = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=30)).isoformat()
            payload = [{"markets": [{"id": "m1", "conditionId": "0xc1", "endDate": future_iso, "clobTokenIds": '["tok_w1","tok_w2"]'}]}]
            mock_resp.content = json.dumps(payload).encode("utf-8")
            mock_resp.json.return_value = payload
            mock_cli = mock.MagicMock()
            mock_cli.get = mock.AsyncMock(return_value=mock_resp)
            hv.executor.get_async_client = mock.MagicMock(return_value=mock_cli)
            hv.executor.prewarm_token_market_cache = mock.MagicMock()
            hv._pos_market_ws = mock.MagicMock()
            hv._desired_market_ws_tokens = mock.MagicMock(return_value=["tok_w1", "tok_w2"])

            await hv._prewarm_next_candle_markets()
            self.assertEqual(mock_cli.get.await_count, 11)
            self.assertEqual(hv.executor.prewarm_token_market_cache.call_count, 22)

    async def test_single_leg_maker_lock_uses_batch_books_and_async_meta(self):
        with tempfile.TemporaryDirectory() as td:
            hv = _make_dry_harvester(Path(td))
            hv.dry_run = False
            hv.executor.dry_run = False
            hv.executor.auth_mode = "AUTHENTICATED_L2"
            hv.executor.is_authenticated = True
            hv.executor.client = mock.MagicMock()
            hv.executor.client._mock_children = None
            hv._startup_reconciled = True
            hv._is_d1_box_halted = lambda: False
            hv._global_halt_reasons = lambda: []
            hv._last_known_collateral = 50.0
            hv.executor.get_collateral_balance = mock.MagicMock(return_value=50.0)
            hv.executor.get_market_books_batch_async = mock.AsyncMock(
                return_value={
                    ("3" * 24): {"asks": [{"price": "0.990", "size": "50"}], "bids": [{"price": "0.984", "size": "50"}]},
                    ("4" * 24): {"asks": [{"price": "0.010", "size": "50"}], "bids": [{"price": "0.001", "size": "50"}]},
                }
            )
            hv.executor.get_token_metadata_async = mock.AsyncMock(return_value=(0.001, False))
            hv.executor.get_token_balance = mock.MagicMock(return_value=0.0)
            hv.executor._can_use_native_async_post_order = mock.MagicMock(return_value=True)
            hv.executor.post_maker_entry_order_async = mock.AsyncMock(return_value={"status": "REJECTED_TEST"})
            hv.executor.cancel_order_by_id = mock.MagicMock(return_value=True)
            hv.save_state = mock.MagicMock()

            cand = {
                "box_id": "SLL_T1",
                "box_type": "SINGLE_LEG_MAKER_LOCK",
                "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
                "asset": "BTC",
                "leg_a_market_id": "9901",
                "leg_a_condition_id": "0xcid9901",
                "leg_a_token_id": "3" * 24,
                "leg_a_opp_token_id": "4" * 24,
                "leg_a_side": "YES",
                "leg_a_price": 0.985,
                "leg_a_limit_price": 0.985,
                "anchor_bid_px": 0.985,
                "p_model": 0.9995,
                "tte_sec": 300.0,
                "expiry_ts": time.time() + 300.0,
                "shares": 10.0,
                "maker_bid_price": 0.996,
                "ts_unix": time.time(),
            }
            with mock.patch("src.polymarket_research.stage_c_zero_loss_velocity.load_alpha124_graduation_maps_with_lkg_cache", side_effect=_fake_grad_maps), \
                 mock.patch("src.polymarket_research.stage_c_zero_loss_velocity.check_strict_pure_riskless_candidate_gate", return_value=None):
                res = await hv.maybe_execute_graduated_single_leg_maker_lock(cand)
            self.assertEqual(res.get("executed"), False, f"Unexpected result: {res}")
            self.assertGreaterEqual(hv.executor.get_market_books_batch_async.await_count, 1, f"Did not reach batch books, got: {res}")
            hv.executor.get_token_metadata_async.assert_awaited()

    def test_desired_tokens_includes_dormant_fast_rescan_and_o1_recycle_map(self):
        with tempfile.TemporaryDirectory() as td:
            hv = _make_dry_harvester(Path(td))
            with mock.patch(
                "src.polymarket_research.full_throttle_pipeline.load_dormant_fast_rescan_tokens",
                return_value=["dorm_tok_1", "dorm_tok_2"],
            ):
                toks = hv._desired_market_ws_tokens()
            self.assertIn("dorm_tok_1", toks)
            self.assertIn("dorm_tok_2", toks)

            hv.active_positions["pos1"] = {"token_id": "tok_dom", "is_dominance_box": True, "hold_to_maturity_lock": False}
            hv.active_positions["pos2"] = {"token_id": "tok_htm", "is_dominance_box": False, "hold_to_maturity_lock": True}
            rmap = hv._rebuild_active_recycle_tok_map()
            self.assertEqual(rmap["tok_dom"], (True, False))
            self.assertEqual(rmap["tok_htm"], (False, True))

    def test_drain_lifecycle_events_enforces_d001_kmia_quarantine(self):
        with tempfile.TemporaryDirectory() as td:
            hv = _make_dry_harvester(Path(td))
            kmia_mid = next(iter(sorted(FROZEN_KMIA_MARKET_IDS)))
            hv.active_positions["kmia"] = {
                "market_id": kmia_mid,
                "condition_id": "0xkmia_cid",
                "token_id": "kmia_tok",
            }
            mkt_ws = mock.MagicMock()
            poly_ws = mock.MagicMock()

            mkt_ws.drain_lifecycle_events.return_value = [
                {"event_type": "market_resolved", "market_id": kmia_mid},
                {"event_type": "market_resolved", "token_id": "kmia_tok"},
            ]
            poly_ws.drain_events.return_value = [
                {"event_type": "ctf_condition_resolution", "condition_id": "0xkmia_cid"},
                {"event_type": "oo_settle", "market_ids": [kmia_mid], "quarantined_d001": True},
            ]
            hv._pos_market_ws = mkt_ws
            self.assertFalse(hv._drain_and_handle_lifecycle_events(poly_ws))
            mkt_ws.set_desired_tokens.assert_not_called()

            mkt_ws.drain_lifecycle_events.return_value = [
                {"event_type": "market_resolved", "market_id": "999999", "assets_ids": ["t_other"]}
            ]
            poly_ws.drain_events.return_value = []
            self.assertTrue(hv._drain_and_handle_lifecycle_events(poly_ws))
            mkt_ws.set_desired_tokens.assert_called_once()

    async def test_fast_d1_consumer_loop_inotify_dirty_wakes_poll(self):
        with tempfile.TemporaryDirectory() as td:
            hv = _make_dry_harvester(Path(td))
            hv._last_d1_cand_poll = time.time() + 100.0
            hv._d1_inotify_dirty = True
            poll_calls = 0

            async def _fake_poll(now_ts, loop):
                nonlocal poll_calls
                poll_calls += 1
                hv._shutdown_requested = True
                return 0

            hv._poll_d1_live_box_candidates_unlocked = _fake_poll
            ev = asyncio.Event()
            await asyncio.wait_for(hv._fast_d1_consumer_loop(ev), timeout=1.0)
            self.assertEqual(poll_calls, 1)
            self.assertFalse(hv._d1_inotify_dirty)


class TestV62Phase3ExecutionAndSchemaUnblock(unittest.IsolatedAsyncioTestCase):
    async def test_d1_short_tte_and_quiet_cap_apply_to_feebearing_dominance_box(self):
        with tempfile.TemporaryDirectory() as td:
            hv = _make_dry_harvester(Path(td))
            hv.dry_run = False
            hv.executor.dry_run = False
            hv.executor.auth_mode = "AUTHENTICATED_L2"
            hv.executor.is_authenticated = True
            hv.executor.client = mock.MagicMock()
            hv.executor.client._mock_children = None
            hv._startup_reconciled = True
            hv._is_d1_box_halted = lambda: False
            hv._global_halt_reasons = lambda: []
            hv._last_known_collateral = 50.0
            hv.live_bankroll = 50.0
            hv.executor.get_collateral_balance = mock.MagicMock(return_value=50.0)
            hv.executor.get_token_balance = mock.MagicMock(return_value=0.0)
            hv.executor.peek_cached_fee_params = lambda cid="", tok=None: (0.015, 1.0)
            hv.executor.execute_atomic_dominance_box_async = mock.AsyncMock(
                return_value={"executed": False, "reason": "MOCK_STOP"}
            )
            hv._pos_market_ws = mock.MagicMock()
            hv._pos_market_ws.get_book = mock.MagicMock(
                side_effect=lambda tid, max_age_sec=0.65: (
                    {
                        "asks": [{"price": 0.515, "size": 50.0}],
                        "bids": [{"price": 0.500, "size": 50.0}],
                    }
                    if str(tid).startswith("2")
                    else {
                        "asks": [{"price": 0.489 if str(tid).endswith(("5", "6")) else 0.491, "size": 50.0}],
                        "bids": [{"price": 0.480, "size": 50.0}],
                    }
                )
            )
            hv.executor.get_market_books_batch_async = mock.AsyncMock(return_value={})
            now_f = time.time()

            def _mk_cand(dk, eid, exp_delta, depth, ta, tb):
                px_q = 0.489 if str(ta).endswith("5") else 0.491
                return {
                    "box_id": dk,
                    "dedupe_key": dk,
                    "ts_unix": now_f,
                    "oracle_match_verified": True,
                    "force_parallel_batch": True,
                    "box_type": "DOMINANCE",
                    "sleeve_source": "D1_SAME_ORACLE_DOMINANCE_BOX",
                    "asset": "BTC",
                    "event_id": eid,
                    "expiry_ts": now_f + exp_delta,
                    "corridor_bps": 12.0,
                    "p_model": 0.999,
                    "k_low": 90000.0,
                    "k_high": 90100.0,
                    "leg_a_strike": 90000.0,
                    "leg_b_strike": 90100.0,
                    "leg_a_side": "UP",
                    "leg_b_side": "DOWN",
                    "leg_a_limit_price": px_q,
                    "leg_b_limit_price": px_q,
                    "leg_a_token_id": ta,
                    "leg_b_token_id": tb,
                    "leg_a_opp_token_id": ("2" * 23) + ta[-1:],
                    "leg_b_opp_token_id": ("2" * 23) + tb[-1:],
                    "leg_a_market_id": f"m_{ta[-4:]}",
                    "leg_b_market_id": f"m_{tb[-4:]}",
                    "leg_a_condition_id": f"c_{ta[-4:]}",
                    "leg_b_condition_id": f"c_{tb[-4:]}",
                    "leg_a_fee_rate": 0.015,
                    "leg_b_fee_rate": 0.015,
                    "ask_depth_usd": depth,
                    "is_quiet_book": depth <= 35.0,
                }

            with mock.patch(
                "src.polymarket_research.stage_c_zero_loss_velocity.load_alpha124_graduation_maps_with_lkg_cache",
                side_effect=_fake_grad_maps,
            ):
                # 1) Normal >180s non-quiet BTC DOMINANCE at 0.495+0.495 (>0.985 cap) is rejected
                res_norm = await hv.maybe_execute_graduated_d1_box_async(
                    _mk_cand("D1_NORM", "evt_norm", 260.0, 120.0, ("1" * 23) + "1", ("1" * 23) + "2")
                )
                self.assertFalse(res_norm.get("executed"))
                self.assertIn("FRESH_BOOK_WALK_REJECT:", str(res_norm.get("reason")))
                hv.executor.execute_atomic_dominance_box_async.assert_not_called()

                # 2) Short-TTE <=180s fee-bearing DOMINANCE unlocks 0.9925 cap
                await hv.maybe_execute_graduated_d1_box_async(
                    _mk_cand("D1_SHORT", "evt_short", 90.0, 120.0, ("1" * 23) + "3", ("1" * 23) + "4")
                )
                self.assertGreaterEqual(hv.executor.execute_atomic_dominance_box_async.await_count, 1)
                self.assertAlmostEqual(
                    hv.executor.execute_atomic_dominance_box_async.call_args.kwargs.get("max_box_cost_net"),
                    0.9925,
                    places=4,
                )

                # 3) Quiet-book (ask_depth_usd <= 35) D1_SAME_ORACLE_DOMINANCE_BOX (>180s) unlocks 0.989 cap
                hv.executor.execute_atomic_dominance_box_async.reset_mock()
                await hv.maybe_execute_graduated_d1_box_async(
                    _mk_cand("D1_QUIET", "evt_quiet", 260.0, 20.0, ("1" * 23) + "5", ("1" * 23) + "6")
                )
                self.assertGreaterEqual(hv.executor.execute_atomic_dominance_box_async.await_count, 1)
                self.assertAlmostEqual(
                    hv.executor.execute_atomic_dominance_box_async.call_args.kwargs.get("max_box_cost_net"),
                    0.989,
                    places=4,
                )

    async def test_schema_normalization_and_exact_equivalence_fee_resolution(self):
        with tempfile.TemporaryDirectory() as td:
            hv = _make_dry_harvester(Path(td))
            hv.live_bankroll = 50.0
            hv._last_known_collateral = 50.0
            hv._is_d1_box_halted = lambda: False
            hv._global_halt_reasons = lambda: []
            hv.executor.dry_run = False
            hv.executor.client = types.SimpleNamespace(host="https://clob.polymarket.com")
            now_f = time.time()

            # Executor resolve_token_fee_rate_async caches 0.0 from /fee-rate endpoint
            fake_resp = mock.MagicMock()
            fake_resp.status_code = 200
            fake_resp.json.return_value = {"base_fee": 0}
            fake_client = mock.MagicMock()
            fake_client.get = mock.AsyncMock(return_value=fake_resp)
            hv.executor._async_http_client = fake_client
            hv.executor._fee_cache = {}
            hv.executor.get_async_client = lambda: fake_client

            resolved = await hv.executor.resolve_token_fee_rate_async("tok_eq_a", condition_id="mid_eq_1")
            self.assertEqual(resolved, (0.0, 1.0))
            self.assertEqual(hv.executor.peek_cached_fee_params("mid_eq_1", "tok_eq_a"), (0.0, 1.0))

            # Nested 2-leg EXACT_EQUIVALENCE payload without flat leg_a_*/leg_b_* or fee_rate
            cand_eq = {
                "box_id": "EQ_1",
                "dedupe_key": "EQ_1_DK",
                "box_type": "EXACT_EQUIVALENCE",
                "sleeve_source": "CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX",
                "asset": "SP500",
                "event_id": "evt_eq_1",
                "expiry_ts": now_f + 1200.0,
                "legs": [
                    {"token_id": "tok_eq_a", "market_id": "mid_eq_1", "side": "YES", "label": "June"},
                    {"token_id": "tok_eq_b", "market_id": "mid_eq_2", "side": "NO", "label": "Dec"},
                ],
                "ws_books": {
                    "tok_eq_a": {"asks": [{"price": 0.490, "size": 50.0}], "bids": [{"price": 0.480, "size": 50.0}]},
                    "tok_eq_b": {"asks": [{"price": 0.490, "size": 50.0}], "bids": [{"price": 0.480, "size": 50.0}]},
                },
            }
            hv.executor._fee_cache["tok_eq_b"] = (0.0, 1.0)
            with mock.patch(
                "src.polymarket_research.stage_c_zero_loss_velocity.load_alpha124_graduation_maps_with_lkg_cache",
                side_effect=lambda *_a, **_kw: (
                    {"CAL1_DEADLINE_SURVIVAL_AND_SCALAR_LADDER_BOX": {"closed": 12, "win_rate_pct": 100.0, "realized_pnl_t1000_usd": 5.0, "legging_adjusted_pnl_t1000_usd": 5.0}},
                    {"SP500": {"closed": 12, "win_rate_pct": 100.0, "realized_pnl_t1000_usd": 5.0, "legging_adjusted_pnl_t1000_usd": 5.0}},
                    None,
                ),
            ):
                res_eq = hv._d1_step1_gate_and_preempt(cand_eq, concurrent_ok=True)
            norm_eq = hv._normalize_2leg_candidate_schema(cand_eq)
            self.assertNotIn("reason", res_eq)
            self.assertEqual(norm_eq["leg_a_token_id"], "tok_eq_a")
            self.assertEqual(norm_eq["leg_b_token_id"], "tok_eq_b")
            self.assertEqual(norm_eq["leg_a_condition_id"], "mid_eq_1")
            self.assertTrue(res_eq["zero_fee_box"])
            self.assertEqual(res_eq["box_type"], "EXACT_EQUIVALENCE")

            from src.polymarket_research.stage_c_zero_loss_velocity import is_verified_full_throttle_2leg_box
            norm_c1 = hv._normalize_2leg_candidate_schema({
                "box_type": "C1_BINARY_COMPLETE_SET",
                "sleeve_source": "C1_BINARY_COMPLETE_SET",
                "condition_id": "0xc1",
                "leg_a_market_id": "m1",
                "leg_a_condition_id": "",
                "leg_b_condition_id": "0xc1",
                "leg_a_token_id": "tok_c1_y",
                "leg_b_token_id": "tok_c1_n",
                "leg_a_side": "YES",
                "leg_b_side": "NO",
                "leg_a_limit_price": 0.49,
                "leg_b_limit_price": 0.49,
                "leg_a_fee_rate": 0.0,
                "leg_b_fee_rate": 0.0,
                "box_cost_net": 0.985,
                "min_state_net_payoff_usd": 0.05,
                "expiry_ts": now_f + 3600.0,
                "rule_verified": True,
            })
            self.assertEqual(norm_c1["leg_a_condition_id"], "0xc1")
            self.assertEqual(norm_c1["leg_b_condition_id"], "0xc1")
            self.assertEqual(norm_c1["leg_b_market_id"], "m1")
            self.assertTrue(is_verified_full_throttle_2leg_box(norm_c1))

    async def test_internal_c1_ws_scanner_and_d001_and_fee_guard(self):
        with tempfile.TemporaryDirectory() as td:
            hv = _make_dry_harvester(Path(td))
            hv.live_bankroll = 50.0
            now_f = time.time()
            hv._shm_dir = td

            # Disputed KMIA D-001 must be rejected
            self.assertFalse(hv._register_c1_ws_pair({
                "leg_a_token_id": "kmia_y", "leg_b_token_id": "kmia_n",
                "leg_a_market_id": "6707503", "leg_b_market_id": "6707503",
                "asset": "XAU", "expiry_ts": now_f + 600.0,
            }, now_ts=now_f))

            # Unverified BTC pair with unknown fee must NOT assume zero fee
            self.assertFalse(hv._register_c1_ws_pair({
                "leg_a_token_id": "btc_y", "leg_b_token_id": "btc_n",
                "leg_a_market_id": "mid_btc_1", "leg_b_market_id": "mid_btc_1",
                "asset": "BTC", "expiry_ts": now_f + 600.0,
            }, now_ts=now_f))

            # Fee-bearing BTC pair must be rejected
            self.assertFalse(hv._register_c1_ws_pair({
                "leg_a_token_id": "btc_y2", "leg_b_token_id": "btc_n2",
                "leg_a_market_id": "mid_btc_2", "leg_b_market_id": "mid_btc_2",
                "asset": "BTC", "expiry_ts": now_f + 600.0,
                "leg_a_fee_rate": 0.05, "leg_b_fee_rate": 0.05,
            }, now_ts=now_f))

            # Verified zero-fee XAU tick in SHM emits canonical C1_BINARY_COMPLETE_SET
            shm_tick = {
                "ts_unix": now_f,
                "asset": "XAU",
                "market_id": "mid_xau_1",
                "condition_id": "cid_xau_1",
                "event_id": "evt_xau_1",
                "expiry_ts": now_f + 3600.0,
                "fee_rate_market": 0.0,
                "yes_token_id": "xau_y",
                "no_token_id": "xau_n",
                "yes_ask": 0.492,
                "yes_ask_sz": 25.0,
                "no_ask": 0.492,
                "no_ask_sz": 25.0,
            }
            (Path(td) / "pm_fast_tick_XAU.json").write_text(json.dumps(shm_tick), encoding="utf-8")
            hv._fast_d1_cand_lines = collections.deque()
            emitted = hv._scan_shm_c1_pairs(now_ts=now_f)
            self.assertEqual(emitted, 1)
            self.assertIn("xau_y", hv._c1_pair_by_tok)
            cand_out = json.loads(hv._fast_d1_cand_lines.popleft())
            self.assertEqual(cand_out["box_type"], "C1_BINARY_COMPLETE_SET")
            self.assertEqual(cand_out["sleeve_source"], "ZEROFEE1_C1_COMPLETE_SET")
            self.assertEqual(cand_out["leg_a_fee_rate"], 0.0)
            self.assertEqual(cand_out["leg_b_fee_rate"], 0.0)

    async def test_clinched_ws_opp_token_reverse_index_and_fee_hydration(self):
        with tempfile.TemporaryDirectory() as td:
            hv = _make_dry_harvester(Path(td))
            now_f = time.time()
            hv.executor.peek_cached_fee_params = lambda cid="", tok=None: (0.0, 1.0)
            cand = {
                "box_type": "CLINCH_WATCHLIST_REG",
                "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
                "dedupe_key": "CLINCH_1",
                "event_id": "evt_clinch_1",
                "asset": "POLITICS",
                "expiry_ts": now_f + 3600.0,
                "p_model": 1.0,
                "leg_a_token_id": "tok_win_c1",
                "leg_a_opp_token_id": "tok_opp_c1",
                "leg_a_market_id": "mid_clinch_1",
                "leg_a_condition_id": "cid_clinch_1",
                "leg_a_fee_rate": 0.05,  # stale emitted fee rate
            }
            self.assertTrue(hv._index_clinched_ws_cand(cand, now_ts=now_f))
            self.assertIn("tok_win_c1", hv._clinched_ws_by_opp.get("tok_opp_c1", set()))
            self.assertEqual(hv._clinched_ws_watchlist["tok_win_c1"]["leg_a_fee_rate"], 0.0)

    async def test_sll_three_slots_and_ws_outbid_cooldown(self):
        with tempfile.TemporaryDirectory() as td:
            hv = _make_dry_harvester(Path(td))
            hv.dry_run = False
            hv.executor.dry_run = False
            hv.executor.auth_mode = "AUTHENTICATED_L2"
            hv.executor.is_authenticated = True
            hv.executor.client = mock.MagicMock()
            hv.executor.client._mock_children = None
            hv._startup_reconciled = True
            hv._is_d1_box_halted = lambda: False
            hv._global_halt_reasons = lambda: []
            hv._last_known_collateral = 50.0
            hv.live_bankroll = 50.0
            hv.executor.get_collateral_balance = mock.MagicMock(return_value=50.0)
            now_f = time.time()
            hv.active_positions = {
                "pos_b1": {"market_id": "m_b1", "single_leg_lock": True, "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY", "notional_usd": 5.0},
                "pos_b2": {"market_id": "m_b2", "single_leg_lock": True, "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY", "notional_usd": 5.0},
            }
            fake_ws = mock.MagicMock()
            fake_ws.get_book = mock.MagicMock(return_value={
                "bids": [{"price": 0.999, "size": 200.0}],
                "asks": [],
            })
            hv._pos_market_ws = fake_ws
            hv.executor.get_market_books_batch_async = mock.AsyncMock()
            cand_b3 = {
                "box_id": "B3",
                "dedupe_key": "B3_DK",
                "box_type": "SINGLE_LEG_MAKER_LOCK",
                "sleeve_source": "BOND1_UMA_RESOLUTION_CARRY",
                "event_id": "evt_b3",
                "asset": "BOND",
                "expiry_ts": now_f + 1800.0,
                "p_model": 1.0,
                "max_box_cost_net": 0.997,
                "anchor_bid_px": 0.996,
                "leg_a_token_id": "tok_b3",
                "leg_a_opp_token_id": "opp_b3",
                "leg_a_market_id": "m_b3",
                "leg_a_condition_id": "c_b3",
                "leg_a_fee_rate": 0.0,
                "leg_a_tick_size": 0.001,
            }
            with mock.patch(
                "src.polymarket_research.stage_c_zero_loss_velocity.load_alpha124_graduation_maps_with_lkg_cache",
                side_effect=_fake_grad_maps,
            ):
                res = await hv.maybe_execute_graduated_single_leg_maker_lock(cand_b3)
            self.assertFalse(res.get("executed"))
            self.assertNotEqual(res.get("reason"), "SINGLE_LEG_LOCK_MAX_SLOTS")
            self.assertIn("BOND1_OUTBID_ABOVE_CAP", str(res.get("reason")))
            hv.executor.get_market_books_batch_async.assert_not_called()
            self.assertGreater(hv._d1_retry_cooldown_until.get("B3_DK", 0.0), now_f + 30.0)


if __name__ == "__main__":
    unittest.main()
